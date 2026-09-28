"""回填：按行序把译文写回 PO。

顺序对应是这个工作台的命门，所以这里坚持两条原则：
1. 行数对不上就在读取阶段报错，绝不"尽力猜测"后静默错位；
2. 译文留空表示跳过，保留 PO 里原有的翻译，不会被抹成空串。
"""

from __future__ import annotations

from . import placeholders
from .plural import PluralRule
from .po import POCatalog
from .workbook import ApplyReport, Options, PlaceholderIssue, Slot, RULE_SOURCE_HEADER


def _count_leading_newlines(text: str) -> int:
    return len(text) - len(text.lstrip("\n"))


def _count_trailing_newlines(text: str) -> int:
    return len(text) - len(text.rstrip("\n"))


def align_newlines(text: str, source: str) -> str:
    """让译文首尾换行数量与原文一致，避免 Poedit 报"前后空白不一致"。"""
    if not text:
        return text
    lead = _count_leading_newlines(text)
    want_lead = _count_leading_newlines(source)
    if lead < want_lead:
        text = "\n" * (want_lead - lead) + text
    elif lead > want_lead:
        text = text[lead - want_lead:]
    trail = _count_trailing_newlines(text)
    want_trail = _count_trailing_newlines(source)
    if trail < want_trail:
        text = text + "\n" * (want_trail - trail)
    elif trail > want_trail:
        text = text[: len(text) - (trail - want_trail)]
    return text


def apply_translations(
    catalog: POCatalog,
    slots: list[Slot],
    texts: list[str],
    rule: PluralRule,
    options: Options,
    *,
    rule_source: str = RULE_SOURCE_HEADER,
) -> ApplyReport:
    report = ApplyReport(rule=rule, slots=len(slots))
    updates: dict[int, list[tuple[int | None, str]]] = {}

    for number, (slot, text) in enumerate(zip(slots, texts), 1):
        if text == "":
            report.skipped_empty += 1
            continue
        value = align_newlines(text, slot.source) if options.align_newlines else text
        if value != text:
            report.newline_aligned += 1
        missing, extra = placeholders.diff(slot.source, value)
        if missing and options.repair_placeholders:
            value = placeholders.repair(value, missing)
            missing = ()
            report.repaired_lines += 1
        if missing or extra:
            report.issues.append(
                PlaceholderIssue(number, slot.entry_index, slot.form, missing, extra)
            )
        updates.setdefault(slot.entry_index, []).append((slot.form, value))

    for index, changed in updates.items():
        entry = catalog.entries[index]
        if entry.is_plural:
            for form, value in changed:
                entry.msgstr_plural[form if form is not None else 0] = value
            entry.msgstr = None
        else:
            entry.msgstr = changed[-1][1]

    # 形态键必须与头部 Plural-Forms 一致，否则 msgfmt 会报形态数不匹配
    for entry in catalog.entries:
        if entry.is_plural:
            forms = {form: entry.msgstr_plural.get(form, "") for form in rule.forms}
            if forms != entry.msgstr_plural:
                report.plural_normalized += 1
            entry.msgstr_plural = forms
            entry.msgstr = None
        elif entry.msgstr_plural:
            entry.msgstr_plural = {}
            report.plural_normalized += 1

    for index in updates:
        entry = catalog.entries[index]
        if not entry.fuzzy:
            continue
        done = (
            all(text != "" for text in entry.msgstr_plural.values())
            if entry.is_plural
            else bool(entry.msgstr)
        )
        if done:
            entry.fuzzy = False
            report.fuzzy_cleared += 1

    report.filled = sum(len(changed) for changed in updates.values())
    _update_header(catalog, rule, rule_source, options, report)
    return report


def _update_header(catalog: POCatalog, rule: PluralRule, rule_source: str, options: Options, report: ApplyReport) -> None:
    header = catalog.ensure_header()
    original = dict(header.fields)
    if options.target_lang and header.language != options.target_lang:
        header.set("Language", options.target_lang)
    if rule_source != RULE_SOURCE_HEADER:
        # 规则不是从头部来的（显式指定或按目标语言查表），必须写回头部，
        # 否则 gettext 运行时会用错形态数
        header.set("Plural-Forms", rule.header_value)
    header.ensure_utf8()
    catalog.apply_header(header)
    for key, value in header.fields.items():
        if original.get(key) != value:
            report.header_changes.append(f"{key}: {original.get(key, '(无)')} → {value}")
