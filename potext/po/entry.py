"""PO 条目数据模型。

只保留本项目需要的能力：完整保存原始注释行、区分"字段缺失"和"字段为空"、以及
obsolete 条目的原样透传。gettext 允许同一 msgid 出现多次，因此条目一律按位置寻址，
不做去重。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class POEntry:
    msgid: str = ""
    msgctxt: str | None = None
    msgid_plural: str | None = None
    msgstr: str | None = None
    msgstr_plural: dict[int, str] = field(default_factory=dict)
    #: 原始注释行，不含前导 '#'，例如 '. 备注' / '#: file.c:12' / ', fuzzy'
    comments: list[str] = field(default_factory=list)
    obsolete: bool = False
    #: obsolete 条目不解析结构，整块原样写回
    obsolete_lines: list[str] = field(default_factory=list)

    @property
    def is_header(self) -> bool:
        return not self.obsolete and self.msgid == "" and self.msgctxt is None and self.msgid_plural is None

    @property
    def is_plural(self) -> bool:
        return self.msgid_plural is not None

    @property
    def flags(self) -> list[str]:
        result: list[str] = []
        for line in self.comments:
            if line.startswith(","):
                result.extend(part.strip() for part in line[1:].split(",") if part.strip())
        return result

    @property
    def fuzzy(self) -> bool:
        return "fuzzy" in self.flags

    @fuzzy.setter
    def fuzzy(self, value: bool) -> None:
        """增删 fuzzy 标记，其余注释与标记原样保留。"""
        flags = [f for f in self.flags if f != "fuzzy"]
        if value:
            flags.append("fuzzy")
        kept = [line for line in self.comments if not line.startswith(",")]
        if flags:
            kept.append(", " + ", ".join(flags))
        self.comments = kept

    @property
    def references(self) -> str:
        return " ".join(line[1:].strip() for line in self.comments if line.startswith(":"))

    @property
    def translator_notes(self) -> str:
        return "\n".join(line[1:].strip() for line in self.comments if line.startswith("."))

    def has_msgstr(self) -> bool:
        return self.msgstr is not None and self.msgstr != ""

    def source_for_form(self, form: int | None) -> str:
        """某个目标复数形态对应的源文本：形态 0 用单数原文，其余用复数原文。"""
        if form is None or form == 0:
            return self.msgid
        return self.msgid_plural or self.msgid

    def identity(self) -> tuple[str | None, str, str | None]:
        return (self.msgctxt, self.msgid, self.msgid_plural)
