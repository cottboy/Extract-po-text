"""服务层：把编解码、槽位计划、文档读写收口成 CLI 与 GUI 共用的动作。

每次操作都重新读一遍 PO，避免像旧版那样把可变状态常驻在界面对象里，
导致第二次导入时用到上一次已被改写的内容。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .apply import apply_translations
from .plural import PluralRule, rule_for_language
from .po import POCatalog
from .workbook import (
    ApplyReport,
    ExtractReport,
    Options,
    build_plan,
    decode_lines,
    read_workbook,
    write_workbook,
)

_UTF8_ALIASES = {"utf-8", "utf8", "utf-8-sig"}


@dataclass
class Stats:
    path: str
    entries: int = 0
    translatable: int = 0
    translated: int = 0
    untranslated: int = 0
    plural_entries: int = 0
    fuzzy: int = 0
    obsolete: int = 0
    language: str = ""
    rule: PluralRule | None = None
    rule_source: str = ""
    encoding: str = "utf-8"
    notes: list[str] = field(default_factory=list)

    def summary(self) -> list[str]:
        return [
            f"文件：{self.path}（编码 {self.encoding}）",
            f"条目：共 {self.entries}，可翻译 {self.translatable}，已翻译 {self.translated}，待翻译 {self.untranslated}",
            f"复数条目 {self.plural_entries}，fuzzy {self.fuzzy}，obsolete {self.obsolete}",
            f"语言：{self.language or '（头部未声明）'}；复数规则 nplurals={self.rule.nplurals}（{self.rule_source}）",
            *self.notes,
        ]


class Session:
    """针对一个 PO/POT 文件的工作会话。"""

    def __init__(self, po_path: str | Path):
        self.po_path = Path(po_path)

    def load(self) -> POCatalog:
        return POCatalog.load(self.po_path)

    def resolve_rule(self, catalog: POCatalog, options: Options) -> tuple[PluralRule, str, list[str]]:
        """优先级：显式声明 > 目标语言预设 > PO 头部 > 英语默认。"""
        notes: list[str] = []
        if options.plural_forms:
            return PluralRule.parse(options.plural_forms), "显式 --plural-forms", notes
        if options.target_lang:
            rule = rule_for_language(options.target_lang)
            if rule:
                return rule, f"目标语言 {options.target_lang} 预设", notes
            notes.append(f"未内置 {options.target_lang} 的复数规则，改用 PO 头部声明；必要时用 --plural-forms 指定")
        header = catalog.header
        if not header.get("Plural-Forms"):
            notes.append("PO 头部没有 Plural-Forms，按英语 nplurals=2 处理")
        return header.plural_rule, "PO 头部", notes

    def stats(self) -> Stats:
        catalog = self.load()
        rule, source, notes = self.resolve_rule(catalog, Options())
        stats = Stats(
            path=str(self.po_path),
            entries=len(catalog.entries),
            language=catalog.header.language,
            rule=rule,
            rule_source=source,
            encoding=catalog.source_encoding,
            notes=notes,
        )
        for entry in catalog.entries:
            if entry.obsolete:
                stats.obsolete += 1
                continue
            if entry.is_header or entry.msgid == "":
                continue
            stats.translatable += 1
            if entry.is_plural:
                stats.plural_entries += 1
                done = all(entry.msgstr_plural.get(form, "") != "" for form in rule.forms)
            else:
                done = entry.has_msgstr()
            if entry.fuzzy:
                stats.fuzzy += 1
            if done:
                stats.translated += 1
            else:
                stats.untranslated += 1
        return stats

    def export(self, out_path: str | Path, options: Options) -> ExtractReport:
        catalog = self.load()
        rule, source, notes = self.resolve_rule(catalog, options)
        slots, report = build_plan(catalog, rule, options)
        report.rule_source = source
        report.notes = notes
        write_workbook(out_path, slots)
        return report

    def apply(self, translations_path: str | Path, out_path: str | Path | None, options: Options) -> ApplyReport:
        """回填并写出；out_path 为 None 时只做校验不写文件。"""
        catalog = self.load()
        rule, source, notes = self.resolve_rule(catalog, options)
        slots, _ = build_plan(catalog, rule, options)
        texts = decode_lines(read_workbook(translations_path, slots))
        report = apply_translations(catalog, slots, texts, rule, options, rule_source=source)
        report.notes = list(notes)
        if catalog.source_encoding.lower() not in _UTF8_ALIASES:
            report.notes.append(f"输入按 {catalog.source_encoding} 读取，输出统一写为 UTF-8 并同步 charset 声明")
        if out_path is not None:
            report.notes.append(f"已写出：{Path(out_path)}")
            catalog.save(out_path)
        return report