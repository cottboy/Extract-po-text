"""翻译工作台：PO ⇄ 纯文本一行一条。

文档格式刻意做到极简，方便整列复制给翻译软件或大模型：
- 一行 = 一个待翻译槽位；
- 槽位顺序由 PO 文件决定，回填时按同一顺序 1:1 对应，因此行序不能增删；
- 换行、制表符、反斜杠按 gettext 惯例转义，行首尾空格转义成 ``\\x20``。

复数条目按目标语言的 ``nplurals`` 展开成多行：形态 0 的原文是 msgid，其余形态是
msgid_plural（形态数多于 2 时 msgid_plural 会重复出现，这是 gettext 复数体系的要求）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .exceptions import WorkbookError
from .escaping import decode_line, encode_line
from .plural import PluralRule
from .po import POCatalog

_MAX_HINT = 60
#: 复数规则取自 PO 头部时无需回写声明，常量集中在这里避免各处硬编码字符串
RULE_SOURCE_HEADER = "PO 头部"


@dataclass(frozen=True)
class Slot:
    """一个待翻译槽位，对应文档里的一行。"""

    entry_index: int
    form: int | None
    source: str
    hint: str

    @property
    def key(self) -> str:
        return f"{self.entry_index}:{self.form if self.form is not None else '-'}"

    def describe(self, line_number: int) -> str:
        where = f"条目 {self.entry_index + 1}" + ("" if self.form is None else f" 复数形态[{self.form}]")
        return f"第 {line_number} 行 → {where}：{self.hint}"


@dataclass
class Options:
    """提取与回填共享的选项。"""

    include_translated: bool = False
    include_fuzzy: bool = False
    target_lang: str | None = None
    plural_forms: str | None = None
    align_newlines: bool = True
    repair_placeholders: bool = False


@dataclass
class ExtractReport:
    rule: PluralRule
    rule_source: str
    total_entries: int = 0
    exported_slots: int = 0
    exported_plural_slots: int = 0
    skipped_translated: int = 0
    skipped_obsolete: int = 0
    skipped_header: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> list[str]:
        return [
            f"PO 内条目 {self.total_entries} 个，导出 {self.exported_slots} 行待翻译",
            f"其中复数形态行 {self.exported_plural_slots} 行",
            f"跳过已翻译 {self.skipped_translated} 处、obsolete {self.skipped_obsolete} 个、头部 {self.skipped_header} 个",
            f"复数规则：nplurals={self.rule.nplurals}（来源：{self.rule_source}）",
            *self.notes,
        ]


@dataclass
class PlaceholderIssue:
    line_number: int
    entry_index: int
    form: int | None
    missing: tuple[str, ...]
    extra: tuple[str, ...]

    def describe(self) -> str:
        where = f"第 {self.line_number} 行（条目 {self.entry_index + 1}"
        where += "" if self.form is None else f" 形态[{self.form}]"
        where += "）"
        parts = []
        if self.missing:
            parts.append("缺少 " + " ".join(self.missing))
        if self.extra:
            parts.append("多出 " + " ".join(self.extra))
        return where + "：" + "，".join(parts)


@dataclass
class ApplyReport:
    rule: PluralRule
    slots: int = 0
    filled: int = 0
    skipped_empty: int = 0
    fuzzy_cleared: int = 0
    newline_aligned: int = 0
    plural_normalized: int = 0
    issues: list[PlaceholderIssue] = field(default_factory=list)
    repaired_lines: int = 0
    header_changes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> list[str]:
        lines = [
            f"共 {self.slots} 行，回填 {self.filled} 行，留空跳过 {self.skipped_empty} 行",
            f"清除 fuzzy 标记 {self.fuzzy_cleared} 处，复数形态规范化 {self.plural_normalized} 条",
            f"首尾换行对齐 {self.newline_aligned} 处",
        ]
        if self.issues:
            label = "已自动补齐" if self.repaired_lines else "待人工确认"
            lines.append(f"占位符异常 {len(self.issues)} 处（{label}）")
        if self.header_changes:
            lines.append("头部更新：" + "；".join(self.header_changes))
        lines.extend(self.notes)
        return lines


def _hint_for(entry) -> str:
    reference = entry.references
    if reference:
        return reference[:_MAX_HINT]
    return entry.msgid.replace("\n", " ")[:_MAX_HINT]


def build_plan(catalog: POCatalog, rule: PluralRule, options: Options) -> tuple[list[Slot], ExtractReport]:
    """按当前规则列出全部待翻译槽位，提取与回填都靠它对齐行序。"""
    report = ExtractReport(rule=rule, rule_source="", total_entries=len(catalog.entries))
    slots: list[Slot] = []
    for index, entry in enumerate(catalog.entries):
        if entry.obsolete:
            report.skipped_obsolete += 1
            continue
        if entry.is_header or entry.msgid == "":
            report.skipped_header += 1
            continue
        forms = rule.forms if entry.is_plural else (None,)
        if entry.is_plural:
            pending = [form for form in forms if entry.msgstr_plural.get(form, "") == ""]
        else:
            pending = [form for form in forms if not entry.has_msgstr()]
        # --include-fuzzy 的语义是"连标记为需要复核的译文也重译一遍"
        if not pending and not (options.include_translated or (entry.fuzzy and options.include_fuzzy)):
            report.skipped_translated += 1
            continue
        if not pending:
            pending = list(forms)
        for form in pending:
            slots.append(Slot(index, form, entry.source_for_form(form), _hint_for(entry)))
            if form is not None:
                report.exported_plural_slots += 1
    report.exported_slots = len(slots)
    return slots, report


def write_workbook(path: str | Path, slots: Sequence[Slot]) -> Path:
    target = Path(path)
    body = "".join(encode_line(slot.source) + "\n" for slot in slots)
    if str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8", newline="\n")
    return target


def read_workbook(path: str | Path, slots: Sequence[Slot]) -> list[str]:
    """读取翻译文档，行数必须与槽位数严格相等，否则带上下文报错。"""
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"翻译文档不存在: {target}")
    text = target.read_text(encoding="utf-8-sig")
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    expected = len(slots)
    if len(lines) > expected:
        surplus = lines[expected:]
        if all(line.strip() == "" for line in surplus):
            del lines[expected:]  # 编辑器在文件末尾补的空行，不影响对应关系
        else:
            first_extra = next((i for i, line in enumerate(surplus) if line.strip() != ""), 0)
            number = expected + first_extra + 1
            raise WorkbookError(
                f"翻译文档行数不匹配：应为 {expected} 行，实际 {len(lines)} 行。"
                f"第 {number} 行多出内容：{surplus[first_extra][:60]!r}。"
                "翻译时不能增删行，请检查是否把一条译文拆成了多行。"
            )
    if len(lines) < expected:
        missing_at = len(lines)
        tail = f"（{slots[missing_at].describe(missing_at + 1)}）" if missing_at < expected else ""
        raise WorkbookError(
            f"翻译文档行数不足：应为 {expected} 行，实际 {len(lines)} 行，"
            f"从第 {missing_at + 1} 行开始缺少 {expected - missing_at} 行{tail}。"
            "若原文里本来就有换行，请确认它们仍以 \\n 转义形式留在同一行内。"
        )
    return lines


def decode_lines(lines: Sequence[str]) -> list[str]:
    return [decode_line(line) for line in lines]
