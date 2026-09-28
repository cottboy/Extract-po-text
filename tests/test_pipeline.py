"""提取 → 翻译 → 回填 全链路测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from potext.apply import align_newlines
from potext.exceptions import WorkbookError
from potext.plural import PluralRule, rule_for_language
from potext.po import POCatalog
from potext.service import Session
from potext.workbook import Options, build_plan, decode_lines, read_workbook, write_workbook

HEADER = (
    'msgid ""\n'
    'msgstr ""\n'
    '"Language: zh_CN\\n"\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '"Plural-Forms: nplurals=1; plural=0;\\n"\n'
    "\n"
)

SAMPLE = HEADER + """\
#: a.php:1
msgid "Apple"
msgstr "苹果"

#: a.php:2
msgid "Banana"
msgstr ""

#: a.php:3
msgid "%d comment"
msgid_plural "%d comments"
msgstr[0] ""

#, fuzzy
#: a.php:4
msgid "Stale"
msgstr "旧的"

#: a.php:5
msgid "Line one\\nLine two"
msgstr ""
"""


def make_session(sample: str) -> tuple[Session, Path, tempfile.TemporaryDirectory]:
    folder = tempfile.TemporaryDirectory()
    po_path = Path(folder.name) / "demo.po"
    po_path.write_text(sample, encoding="utf-8", newline="\n")
    return Session(po_path), po_path, folder


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.catalog = POCatalog.loads(SAMPLE)

    def plan(self, **kwargs):
        options = Options(**kwargs)
        rule = self.catalog.plural_rule
        return build_plan(self.catalog, rule, options)[0]

    def test_default_only_untranslated(self):
        slots = self.plan()
        self.assertEqual([s.source for s in slots], ["Banana", "%d comment", "Line one\nLine two"])
        self.assertEqual([s.form for s in slots], [None, 0, None])

    def test_all_includes_translated_and_fuzzy(self):
        slots = self.plan(include_translated=True)
        # 头部声明 nplurals=1，复数条目只占一行
        self.assertEqual([s.source for s in slots], ["Apple", "Banana", "%d comment", "Stale", "Line one\nLine two"])

    def test_include_fuzzy_only_adds_fuzzy_entries(self):
        slots = self.plan(include_fuzzy=True)
        self.assertIn("Stale", [s.source for s in slots])
        self.assertNotIn("Apple", [s.source for s in slots])

    def test_plural_forms_expand_per_target_rule(self):
        rule = rule_for_language("ru")
        slots, _ = build_plan(self.catalog, rule, Options())
        plural = [s for s in slots if s.entry_index == 3]
        self.assertEqual([s.source for s in plural], ["%d comment", "%d comments", "%d comments"])
        self.assertEqual([s.form for s in plural], [0, 1, 2])

    def test_context_and_duplicate_msgid_keep_separate_indices(self):
        catalog = POCatalog.loads(HEADER + 'msgctxt "button"\nmsgid "Open"\nmsgstr ""\n\nmsgctxt "menu"\nmsgid "Open"\nmsgstr ""\n')
        slots, _ = build_plan(catalog, catalog.plural_rule, Options())
        self.assertEqual([s.entry_index for s in slots], [1, 2])
        self.assertEqual([s.hint for s in slots], ["Open", "Open"])


class WorkbookIOTest(unittest.TestCase):
    def setUp(self):
        self.catalog = POCatalog.loads(SAMPLE)
        self.slots, _ = build_plan(self.catalog, self.catalog.plural_rule, Options())

    def test_written_lines_match_slot_count(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.txt"
            write_workbook(path, self.slots)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), len(self.slots))
            self.assertEqual(decode_lines(read_workbook(path, self.slots)), [s.source for s in self.slots])

    def test_multiline_source_stays_on_one_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.txt"
            write_workbook(path, self.slots)
            self.assertIn("Line one\\nLine two", path.read_text(encoding="utf-8"))

    def test_missing_lines_raise_with_location(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.txt"
            path.write_text("香蕉\n", encoding="utf-8")
            with self.assertRaises(WorkbookError) as ctx:
                read_workbook(path, self.slots)
            self.assertIn("从第 2 行开始缺少 2 行", str(ctx.exception))
            self.assertIn("条目 4", str(ctx.exception))

    def test_extra_lines_raise(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.txt"
            path.write_text("香蕉\n评论\n第二行\n多出来的一行\n", encoding="utf-8")
            with self.assertRaises(WorkbookError) as ctx:
                read_workbook(path, self.slots)
            self.assertIn("不能增删行", str(ctx.exception))

    def test_trailing_blank_lines_tolerated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.txt"
            write_workbook(path, self.slots)
            body = path.read_text(encoding="utf-8") + "\n  \n"
            path.write_text(body, encoding="utf-8")
            self.assertEqual(len(read_workbook(path, self.slots)), len(self.slots))


class SessionEndToEndTest(unittest.TestCase):
    def setUp(self):
        self.session, self.po_path, self.folder = make_session(SAMPLE)
        self.addCleanup(self.folder.cleanup)
        self.txt_path = self.session.po_path.with_suffix(".txt")
        self.out_path = Path(self.folder.name) / "out.po"

    def translate_all(self, mapping: dict[str, str]) -> None:
        self.session.export(self.txt_path, Options())
        lines = self.txt_path.read_text(encoding="utf-8").splitlines()
        self.txt_path.write_text("".join(mapping.get(line, line) + "\n" for line in lines), encoding="utf-8")

    def test_stats(self):
        stats = self.session.stats()
        self.assertEqual((stats.translatable, stats.translated, stats.untranslated), (5, 2, 3))
        self.assertEqual(stats.language, "zh_CN")

    def test_export_then_apply_fills_only_untranslated(self):
        self.translate_all({"Banana": "香蕉", "%d comment": "%d 条评论", "Line one\\nLine two": "第一行\\n第二行"})
        report = self.session.apply(self.txt_path, self.out_path, Options())
        self.assertEqual(report.filled, 3)
        catalog = POCatalog.load(self.out_path)
        by_id = {e.msgid: e for e in catalog.entries}
        self.assertEqual(by_id["Apple"].msgstr, "苹果")
        self.assertEqual(by_id["Banana"].msgstr, "香蕉")
        self.assertEqual(by_id["Line one\nLine two"].msgstr, "第一行\n第二行")
        self.assertEqual(by_id["%d comment"].msgstr_plural, {0: "%d 条评论"})
        self.assertEqual(by_id["%d comment"].msgstr, None)
        # 未被本次导出覆盖的条目保持原样，包括 fuzzy
        self.assertEqual(by_id["Stale"].msgstr, "旧的")
        self.assertTrue(by_id["Stale"].fuzzy)

    def test_blank_translation_keeps_original(self):
        self.session.export(self.txt_path, Options(include_translated=True))
        lines = self.txt_path.read_text(encoding="utf-8").splitlines()
        self.txt_path.write_text("\n".join("" if line == "Apple" else line for line in lines) + "\n", encoding="utf-8")
        report = self.session.apply(self.txt_path, self.out_path, Options(include_translated=True))
        self.assertEqual(report.skipped_empty, 1)
        by_id = {e.msgid: e for e in POCatalog.load(self.out_path).entries}
        self.assertEqual(by_id["Apple"].msgstr, "苹果")

    def test_fuzzy_cleared_after_retranslation(self):
        options = Options(include_fuzzy=True)
        self.session.export(self.txt_path, options)
        lines = self.txt_path.read_text(encoding="utf-8").splitlines()
        body = "".join(("过时的" if line == "Stale" else line) + "\n" for line in lines)
        self.txt_path.write_text(body, encoding="utf-8")
        report = self.session.apply(self.txt_path, self.out_path, options)
        self.assertEqual(report.fuzzy_cleared, 1)
        by_id = {e.msgid: e for e in POCatalog.load(self.out_path).entries}
        self.assertFalse(by_id["Stale"].fuzzy)
        self.assertEqual(by_id["Stale"].msgstr, "过时的")

    def test_target_language_rewrites_plural_header(self):
        options = Options(target_lang="ru")
        self.session.export(self.txt_path, options)
        lines = self.txt_path.read_text(encoding="utf-8").splitlines()
        self.txt_path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        report = self.session.apply(self.txt_path, self.out_path, options)
        catalog = POCatalog.load(self.out_path)
        self.assertEqual(catalog.header.plural_rule.nplurals, 3)
        self.assertEqual(catalog.header.language, "ru")
        entry = next(e for e in catalog.entries if e.msgid == "%d comment")
        self.assertEqual(sorted(entry.msgstr_plural), [0, 1, 2])
        self.assertTrue(any("Plural-Forms" in change for change in report.header_changes))

    def test_stale_plural_forms_dropped_for_single_form_language(self):
        po = HEADER + 'msgid "%d file"\nmsgid_plural "%d files"\nmsgstr[0] "旧单数"\nmsgstr[1] "旧复数"\n'
        session, po_path, folder = make_session(po.replace('msgstr[0] "旧单数"\nmsgstr[1] "旧复数"\n', 'msgstr[0] ""\nmsgstr[1] ""\n'))
        self.addCleanup(folder.cleanup)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        self.assertEqual(len(txt.read_text(encoding="utf-8").splitlines()), 1)
        txt.write_text("%d 个文件\n", encoding="utf-8")
        report = session.apply(txt, out, Options())
        catalog = POCatalog.load(out)
        entry = next(e for e in catalog.entries if e.is_plural)
        self.assertEqual(entry.msgstr_plural, {0: "%d 个文件"})
        self.assertEqual(report.plural_normalized, 1)
        self.assertNotIn("msgstr[1]", out.read_text(encoding="utf-8"))

    def test_apply_without_output_path_only_validates(self):
        self.translate_all({"Banana": "香蕉", "%d comment": "%d 条评论", "Line one\\nLine two": "第一行"})
        report = self.session.apply(self.txt_path, None, Options())
        self.assertFalse(self.out_path.exists())
        self.assertEqual(report.filled, 3)

    def test_dry_run_reports_count_error(self):
        self.txt_path.write_text("只有一行\n", encoding="utf-8")
        with self.assertRaises(WorkbookError):
            self.session.apply(self.txt_path, self.out_path, Options())
        self.assertFalse(self.out_path.exists())

    def test_export_is_idempotent_for_same_po(self):
        first = self.session.export(self.txt_path, Options())
        body = self.txt_path.read_text(encoding="utf-8")
        second = self.session.export(self.txt_path, Options())
        self.assertEqual(first.exported_slots, second.exported_slots)
        self.assertEqual(body, self.txt_path.read_text(encoding="utf-8"))

    def test_apply_twice_is_stable(self):
        self.translate_all({"Banana": "香蕉", "%d comment": "%d 条评论", "Line one\\nLine two": "第一行\\n第二行"})
        self.session.apply(self.txt_path, self.out_path, Options())
        once = self.out_path.read_text(encoding="utf-8")
        # 第二次回填后所有条目都已翻译，默认模式下没有待翻译行，文档为空
        empty_txt = Path(self.folder.name) / "empty.txt"
        empty_txt.write_text("", encoding="utf-8")
        Session(self.out_path).apply(empty_txt, self.out_path, Options())
        self.assertEqual(once, self.out_path.read_text(encoding="utf-8"))


class PlaceholderTest(unittest.TestCase):
    def run_apply(self, source: str, translated: str, **kwargs):
        po = f"{HEADER}msgid \"{source}\"\nmsgstr \"\"\n"
        session, po_path, folder = make_session(po)
        self.addCleanup(folder.cleanup)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        txt.write_text(translated + "\n", encoding="utf-8")
        report = session.apply(txt, out, Options(**kwargs))
        entry = POCatalog.load(out).entries[1]
        return report, entry.msgstr

    def test_missing_placeholder_reported_not_injected(self):
        report, msgstr = self.run_apply("Hi %s, you have %d mail", "你好，你有邮件")
        self.assertEqual(len(report.issues), 1)
        self.assertEqual(report.issues[0].missing, ("%s", "%d"))
        self.assertEqual(msgstr, "你好，你有邮件")
        self.assertIn("缺少 %s %d", report.issues[0].describe())

    def test_repair_appends_missing(self):
        report, msgstr = self.run_apply("Hi %s", "你好", repair_placeholders=True)
        self.assertEqual(msgstr, "你好 %s")
        self.assertEqual(report.repaired_lines, 1)
        self.assertEqual(report.issues, [])

    def test_extra_placeholder_reported(self):
        report, _ = self.run_apply("Hello", "你好 %s")
        self.assertEqual(report.issues[0].extra, ("%s",))

    def test_brace_and_qt_styles(self):
        report, _ = self.run_apply("{name} 和 %1$d", "名字")
        self.assertEqual(report.issues[0].missing, ("%1$d", "{name}"))
        report, _ = self.run_apply("Qt 风格 %1 与 %2", "译文")
        self.assertEqual(report.issues[0].missing, ("%1", "%2"))


class NewlineAlignTest(unittest.TestCase):
    def test_align_helper(self):
        self.assertEqual(align_newlines("你好", "Hi\n"), "你好\n")
        self.assertEqual(align_newlines("你好\n\n", "Hi\n"), "你好\n")
        self.assertEqual(align_newlines("\n你好", "Hi"), "你好")
        self.assertEqual(align_newlines("", "Hi\n"), "")

    def test_applied_to_translation(self):
        po = f'{HEADER}msgid "Title\\n"\nmsgstr ""\n'
        session, po_path, folder = make_session(po)
        self.addCleanup(folder.cleanup)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        txt.write_text("标题\n", encoding="utf-8")
        report = session.apply(txt, out, Options())
        self.assertEqual(report.newline_aligned, 1)
        self.assertEqual(POCatalog.load(out).entries[1].msgstr, "标题\n")

    def test_can_be_disabled(self):
        po = f'{HEADER}msgid "Title\\n"\nmsgstr ""\n'
        session, po_path, folder = make_session(po)
        self.addCleanup(folder.cleanup)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        txt.write_text("标题\n", encoding="utf-8")
        session.apply(txt, out, Options(align_newlines=False))
        self.assertEqual(POCatalog.load(out).entries[1].msgstr, "标题")


class EncodingTest(unittest.TestCase):
    def test_latin1_input_becomes_utf8(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        po = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=iso-8859-1\\n"\n\nmsgid "caf\xe9"\nmsgstr ""\n'
        po_path = Path(folder.name) / "l.po"
        po_path.write_bytes(po.encode("latin-1"))
        session = Session(po_path)
        self.assertEqual(session.stats().encoding, "iso-8859-1")
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        txt.write_text("咖啡馆\n", encoding="utf-8")
        report = session.apply(txt, out, Options())
        catalog = POCatalog.load(out)
        self.assertEqual(catalog.entries[1].msgid, "café")
        self.assertEqual(catalog.entries[1].msgstr, "咖啡馆")
        self.assertEqual(catalog.header.charset, "UTF-8")
        self.assertTrue(any("UTF-8" in note for note in report.notes))

    def test_bom_preserved(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        po_path = Path(folder.name) / "b.po"
        po_path.write_bytes(("\ufeff" + HEADER + 'msgid "a"\nmsgstr ""\n').encode("utf-8"))
        session = Session(po_path)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        txt.write_text("甲\n", encoding="utf-8")
        session.apply(txt, out, Options())
        self.assertTrue(out.read_bytes().startswith(b"\xef\xbb\xbf"))


class ObsoletePreserveTest(unittest.TestCase):
    def test_obsolete_block_survives_round_trip(self):
        po = HEADER + 'msgid "keep"\nmsgstr ""\n\n#~ msgid "gone"\n#~ msgstr "过去"\n\n#| msgid "old"\nmsgid "cur"\nmsgstr ""\n'
        session, po_path, folder = make_session(po)
        self.addCleanup(folder.cleanup)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        session.export(txt, Options())
        self.assertEqual(txt.read_text(encoding="utf-8").splitlines(), ["keep", "cur"])
        txt.write_text("保留\n当前\n", encoding="utf-8")
        session.apply(txt, out, Options())
        body = out.read_text(encoding="utf-8")
        self.assertIn("#~ msgid \"gone\"", body)
        self.assertIn("#~ msgstr \"过去\"", body)
        self.assertIn("#| msgid \"old\"", body)


class PluralRuleParseFromCliStringTest(unittest.TestCase):
    def test_explicit_plural_forms_option(self):
        session, po_path, folder = make_session(SAMPLE)
        self.addCleanup(folder.cleanup)
        txt = po_path.with_suffix(".txt")
        out = Path(folder.name) / "o.po"
        options = Options(plural_forms="nplurals=2; plural=(n > 1);")
        report = session.export(txt, options)
        self.assertEqual(report.rule_source, "显式 --plural-forms")
        self.assertEqual(report.rule, PluralRule.parse("nplurals=2; plural=(n > 1);"))
        self.assertEqual(len(txt.read_text(encoding="utf-8").splitlines()), 4)
        txt.write_text("香蕉\n一条评论\n%d 条评论\n第一行\\n第二行\n", encoding="utf-8")
        report = session.apply(txt, out, options)
        catalog = POCatalog.load(out)
        self.assertEqual(catalog.header.plural_rule.nplurals, 2)
        entry = next(e for e in catalog.entries if e.msgid == "%d comment")
        self.assertEqual(entry.msgstr_plural, {0: "一条评论", 1: "%d 条评论"})


if __name__ == "__main__":
    unittest.main()
