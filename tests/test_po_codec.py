"""PO 编解码测试，重点是往返保真。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from potext.exceptions import PoSyntaxError
from potext.po import POCatalog

SAMPLE = """\
# Translation of theme in Chinese
# Copyright (C) 2024 Someone
# This file is distributed under the same license.
msgid ""
msgstr ""
"Project-Id-Version: demo 1.0\\n"
"Report-Msgid-Bugs-To: https://example.test\\n"
"POT-Creation-Date: 2024-01-01 00:00+00:00\\n"
"Language: zh_CN\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=1; plural=0;\\n"

#: inc/header.php:12
msgid "Hello world"
msgstr "你好，世界"

#. translators: %s is the user name
#: inc/user.php:30
msgid "Hi %s"
msgstr "嗨 %s"

#: inc/cart.php:8
msgid "%d item"
msgid_plural "%d items"
msgstr[0] "%d 件商品"

msgctxt "button"
msgid "Open"
msgstr "打开"

msgctxt "menu"
msgid "Open"
msgstr "开启"

#: legacy.php:1
#, fuzzy
msgid "Draft"
msgstr "草稿"

#~ msgid "Removed"
#~ msgstr ""
#~ "已删除\\n"
#~ "第二行\\n"
"""


class CatalogParseTest(unittest.TestCase):
    def setUp(self):
        self.catalog = POCatalog.loads(SAMPLE)

    def test_entry_count_including_obsolete(self):
        self.assertEqual(len(self.catalog.entries), 8)

    def test_header(self):
        header = self.catalog.header
        self.assertEqual(header.language, "zh_CN")
        self.assertEqual(header.charset, "UTF-8")
        self.assertEqual(header.plural_rule.nplurals, 1)

    def test_translatable_excludes_header_and_obsolete(self):
        self.assertEqual(len(self.catalog.translatable_entries), 6)

    def test_context_entries_kept_separately(self):
        opens = [e for e in self.catalog.entries if e.msgid == "Open"]
        self.assertEqual([e.msgctxt for e in opens], ["button", "menu"])

    def test_plural_forms(self):
        entry = next(e for e in self.catalog.entries if e.msgid == "%d item")
        self.assertTrue(entry.is_plural)
        self.assertEqual(entry.msgstr_plural, {0: "%d 件商品"})
        self.assertIsNone(entry.msgstr)

    def test_flags_and_references(self):
        entry = next(e for e in self.catalog.entries if e.msgid == "Draft")
        self.assertTrue(entry.fuzzy)
        self.assertEqual(entry.references, "legacy.php:1")
        note = next(e for e in self.catalog.entries if e.msgid == "Hi %s")
        self.assertIn("%s is the user name", note.translator_notes)

    def test_obsolete_kept_raw(self):
        obsolete = [e for e in self.catalog.entries if e.obsolete]
        self.assertEqual(len(obsolete), 1)
        self.assertTrue(all(line.startswith("#~") for line in obsolete[0].obsolete_lines))


class CatalogRoundTripTest(unittest.TestCase):
    def assert_semantics_equal(self, first: POCatalog, second: POCatalog) -> None:
        self.assertEqual(len(first.entries), len(second.entries))
        for a, b in zip(first.entries, second.entries):
            self.assertEqual(a.identity(), b.identity())
            self.assertEqual(a.msgctxt, b.msgctxt)
            self.assertEqual(a.msgstr, b.msgstr)
            self.assertEqual(a.msgstr_plural, b.msgstr_plural)
            self.assertEqual(a.comments, b.comments)
            self.assertEqual(a.obsolete_lines, b.obsolete_lines)

    def test_roundtrip_stable(self):
        first = POCatalog.loads(SAMPLE)
        second = POCatalog.loads(first.dumps())
        self.assert_semantics_equal(first, second)
        # 第二次写出必须完全一致，否则说明排版不稳定
        self.assertEqual(second.dumps(), POCatalog.loads(second.dumps()).dumps())

    def test_multiline_value_preserved(self):
        text = 'msgid "a\\nb\\nc"\nmsgstr ""\n'
        catalog = POCatalog.loads("msgid \"\"\nmsgstr \"\"\n\n" + text)
        entry = catalog.entries[1]
        self.assertEqual(entry.msgid, "a\nb\nc")
        self.assertEqual(POCatalog.loads(catalog.dumps()).entries[1].msgid, "a\nb\nc")

    def test_continuation_lines_joined(self):
        catalog = POCatalog.loads(
            'msgid ""\nmsgstr ""\n\nmsgid ""\n"line1\\n"\n"line2"\nmsgstr "ok"\n'
        )
        self.assertEqual(catalog.entries[1].msgid, "line1\nline2")

    def test_missing_blank_line_between_entries(self):
        catalog = POCatalog.loads(
            'msgid ""\nmsgstr ""\n\nmsgid "a"\nmsgstr "1"\nmsgid "b"\nmsgstr "2"\n'
        )
        self.assertEqual([e.msgid for e in catalog.entries[1:]], ["a", "b"])

    def test_crlf_style_preserved_on_save(self):
        catalog = POCatalog.loads('msgid ""\r\nmsgstr ""\r\n\r\nmsgid "a"\r\nmsgstr "1"\r\n')
        self.assertEqual(catalog.newline, "\r\n")
        self.assertEqual(catalog.dumps().count("\r"), 0)
        with tempfile.TemporaryDirectory() as folder:
            saved = catalog.save(Path(folder) / "out.po")
            data = saved.read_bytes()
        self.assertEqual(data.count(b"\r\n"), data.count(b"\n"))
        self.assertEqual(POCatalog.loads(data.decode("utf-8")).entries[1].msgid, "a")

    def test_junk_line_raises(self):
        with self.assertRaises(PoSyntaxError):
            POCatalog.loads('msgid ""\nmsgstr ""\n\n这不是 PO 内容\n')


class HeaderTest(unittest.TestCase):
    def test_ensure_utf8_replaces_charset(self):
        catalog = POCatalog.loads(
            'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=ISO-8859-1\\n"\n'
        )
        header = catalog.ensure_header()
        header.ensure_utf8()
        catalog.apply_header(header)
        self.assertEqual(catalog.header.charset, "UTF-8")

    def test_ensure_utf8_appends_when_absent(self):
        catalog = POCatalog.loads('msgid ""\nmsgstr "Language: zh_CN\\n"\n')
        header = catalog.ensure_header()
        header.ensure_utf8()
        self.assertEqual(header.charset, "UTF-8")
        self.assertEqual(header.get("Language"), "zh_CN")

    def test_missing_header_created_on_demand(self):
        catalog = POCatalog.loads('msgid "a"\nmsgstr "1"\n')
        self.assertIsNone(catalog.header_entry)
        catalog.ensure_header()
        self.assertIsNotNone(catalog.header_entry)
        self.assertEqual([e.msgid for e in catalog.entries], ["", "a"])


if __name__ == "__main__":
    unittest.main()
