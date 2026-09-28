"""PO/POT 编解码：零依赖、按位置保真。

设计取舍：
- 写出时规范化排版（注释、空行、含换行的值按 gettext 惯例拆多行），但**语义无损**：
  条目顺序、重复条目、全部注释行、flags、obsolete 块都原样保留。
- obsolete（``#~``）整块不解析结构，原样透传，避免为读不需要的内容引入解析风险。
- 编码自动嗅探（BOM / 头部 charset），一律按 UTF-8 写出并同步 charset 声明。
"""

from __future__ import annotations

import codecs
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from ..escaping import decode_escapes, escape_po
from ..exceptions import PoSyntaxError
from ..plural import PluralRule
from .entry import POEntry
from .header import POHeader

_KEYWORD_RE = re.compile(r'^(msgctxt|msgid_plural|msgid|msgstr)(?:\[(\d+)\])?[ \t]*"(.*)"$')
_CONTINUATION_RE = re.compile(r'^"(.*)"$')
_CHARSET_SNIFF_RE = re.compile(rb"charset\s*=\s*([\w:.+-]+)", re.IGNORECASE)
_BOMS = ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"))
_NEWLINE_ESCAPE = "\\n"


@dataclass
class _Partial:
    """解析过程中的半成品条目。"""

    comments: list[str] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)

    def add(self, key: str, value: str) -> None:
        self.fields[key] = self.fields.get(key, "") + value


class _Parser:
    def __init__(self, lines: list[str], source: str):
        self._lines = lines
        self._source = source
        self.entries: list[POEntry] = []
        self._comments: list[str] = []
        self._cur: _Partial | None = None
        self._last_key: str | None = None
        self._obsolete: list[str] = []
        self._number = 0

    def run(self) -> None:
        for number, line in enumerate(self._lines, 1):
            self._number = number
            text = line.strip()
            if text.startswith("#~"):
                self._close_entry()
                self._obsolete.append(text)
                continue
            if not text:
                self._close_entry()
                self._flush_obsolete()
                continue
            if text.startswith("#"):
                self._close_entry()
                self._flush_obsolete()
                self._comments.append(text[1:])
                continue
            keyword = _KEYWORD_RE.match(text)
            if keyword:
                self._on_keyword(keyword)
                continue
            if _CONTINUATION_RE.match(text):
                self._on_continuation(text)
                continue
            raise PoSyntaxError(number, f"无法解析的 {self._source} 行", text)
        self._close_entry()
        self._flush_obsolete()

    def _on_keyword(self, match: re.Match[str]) -> None:
        key, index, content = match.group(1), match.group(2), match.group(3)
        field_key = f"{key}[{index}]" if index is not None else key
        if key == "msgid" and self._cur is not None and "msgid" in self._cur.fields:
            # 条目之间漏了空行，按新条目开始
            self._close_entry()
        if self._cur is None:
            self._cur = _Partial(comments=self._comments)
            self._comments = []
        self._cur.add(field_key, decode_escapes(content))
        self._last_key = field_key

    def _on_continuation(self, text: str) -> None:
        if self._cur is None or self._last_key is None:
            raise PoSyntaxError(self._number, "字符串续行之前没有可归属的字段", text)
        self._cur.add(self._last_key, decode_escapes(_CONTINUATION_RE.match(text).group(1)))

    def _flush_obsolete(self) -> None:
        if not self._obsolete:
            return
        self.entries.append(POEntry(obsolete=True, comments=self._comments, obsolete_lines=self._obsolete))
        self._comments = []
        self._obsolete = []

    def _close_entry(self) -> None:
        if self._cur is None:
            return
        partial, self._cur, self._last_key = self._cur, None, None
        if "msgid" not in partial.fields:
            if partial.fields:
                raise PoSyntaxError(self._number, "条目缺少 msgid 字段", repr(sorted(partial.fields)))
            self._comments = partial.comments + self._comments
            return
        self.entries.append(_build_entry(partial))


def _build_entry(partial: _Partial) -> POEntry:
    entry = POEntry(comments=partial.comments, msgid=partial.fields["msgid"])
    entry.msgctxt = partial.fields.get("msgctxt")
    entry.msgid_plural = partial.fields.get("msgid_plural")
    entry.msgstr = partial.fields.get("msgstr")
    entry.msgstr_plural = {
        int(key[key.index("[") + 1 : -1]): value
        for key, value in partial.fields.items()
        if key.startswith("msgstr[")
    }
    return entry


@dataclass
class POCatalog:
    entries: list[POEntry] = field(default_factory=list)
    #: 文件末尾没有归属的注释，写出时原样放回
    trailing_comments: list[str] = field(default_factory=list)
    path: Path | None = None
    source_encoding: str = "utf-8"
    #: 读取时观察到的换行风格与 BOM，写出时保持一致
    newline: str = "\n"
    bom: bool = False

    def __iter__(self) -> Iterator[POEntry]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    @property
    def header_entry(self) -> POEntry | None:
        first = self.entries[0] if self.entries else None
        return first if first is not None and first.is_header else None

    @property
    def header(self) -> POHeader:
        entry = self.header_entry
        return POHeader.parse(entry.msgstr or "") if entry else POHeader()

    def ensure_header(self) -> POHeader:
        """返回头部对象；文件没有头部时插入一个空头部条目。改动后需调用 apply_header。"""
        entry = self.header_entry
        if entry is None:
            entry = POEntry(msgid="", msgstr="")
            self.entries.insert(0, entry)
        return POHeader.parse(entry.msgstr or "")

    def apply_header(self, header: POHeader) -> None:
        entry = self.header_entry
        if entry is not None:
            entry.msgstr = header.as_msgstr()

    @property
    def plural_rule(self) -> PluralRule:
        return self.header.plural_rule

    @property
    def translatable_entries(self) -> list[POEntry]:
        """排除 obsolete 与头部；空 msgid 没有翻译价值。"""
        return [e for e in self.entries if not e.obsolete and not e.is_header and e.msgid != ""]

    # ------- IO -------

    @classmethod
    def loads(cls, text: str, *, source: str = "<memory>") -> "POCatalog":
        if "\r\n" in text:
            newline, body = "\r\n", text.replace("\r\n", "\n")
        elif "\r" in text:
            newline, body = "\r", text.replace("\r", "\n")
        else:
            newline, body = "\n", text
        lines = body.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        parser = _Parser(lines, source)
        parser.run()
        catalog = cls(entries=parser.entries, newline=newline)
        return catalog

    @classmethod
    def load(cls, path: str | Path) -> "POCatalog":
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"PO 文件不存在: {file_path}")
        data = file_path.read_bytes()
        text, encoding, bom = _decode(data, file_path)
        catalog = cls.loads(text, source=str(file_path))
        catalog.path = file_path
        catalog.source_encoding = encoding
        catalog.bom = bom
        return catalog

    def dumps(self) -> str:
        blocks = [_entry_lines(entry) for entry in self.entries]
        if self.trailing_comments:
            blocks.append(["#" + comment for comment in self.trailing_comments])
        text = "\n\n".join("\n".join(block) for block in blocks)
        return text + "\n" if text else ""

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("未指定输出路径")
        body = self.dumps()
        if self.newline != "\n":
            body = body.replace("\n", self.newline)
        data = body.encode("utf-8")
        if self.bom:
            data = codecs.BOM_UTF8 + data
        if str(target.parent) not in ("", "."):
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target


def _decode(data: bytes, path: Path) -> tuple[str, str, bool]:
    for bom, codec in _BOMS:
        if data.startswith(bom):
            return data.decode(codec), codec, codec == "utf-8-sig"
    sniffed = _CHARSET_SNIFF_RE.search(data[:4096])
    candidates = ["utf-8"]
    if sniffed:
        name = sniffed.group(1).decode("ascii", "ignore").strip().lower()
        if name and name.replace("-", "") != "utf8":
            candidates.append(name)
    candidates.append("cp1252")
    for candidate in candidates:
        try:
            return data.decode(candidate), candidate, False
        except (UnicodeDecodeError, LookupError):
            continue
    # latin-1 永不失败，最坏情况是显示乱码而不是中断整个文件
    return data.decode("latin-1"), "latin-1", False


def _string_lines(keyword: str, value: str) -> list[str]:
    """把字段值排版成 PO 行；含换行时按 gettext 惯例拆成多段。"""
    escaped = escape_po(value)
    if "\n" not in value:
        return [f'{keyword} "{escaped}"']
    parts = value.split("\n")
    lines = [f'{keyword} ""']
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        if is_last and part == "":
            break
        lines.append(f'"{escape_po(part)}{_NEWLINE_ESCAPE if not is_last else ""}"')
    return lines


def _entry_lines(entry: POEntry) -> list[str]:
    lines = ["#" + comment for comment in entry.comments]
    if entry.obsolete:
        return lines + entry.obsolete_lines
    if entry.msgctxt is not None:
        lines += _string_lines("msgctxt", entry.msgctxt)
    lines += _string_lines("msgid", entry.msgid)
    if entry.msgid_plural is not None:
        lines += _string_lines("msgid_plural", entry.msgid_plural)
    if entry.msgstr_plural:
        for index in sorted(entry.msgstr_plural):
            lines += _string_lines(f"msgstr[{index}]", entry.msgstr_plural[index])
    elif entry.msgid_plural is not None:
        lines += _string_lines("msgstr[0]", "")
    else:
        lines += _string_lines("msgstr", entry.msgstr or "")
    return lines
