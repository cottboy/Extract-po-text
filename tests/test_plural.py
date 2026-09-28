"""复数规则解析与求值测试。"""

from __future__ import annotations

import unittest

from potext.exceptions import PluralRuleError
from potext.plural import PluralRule, known_languages, rule_for_language
from potext.po import POCatalog

RUSSIAN = "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"


class ParseTest(unittest.TestCase):
    def test_basic(self):
        rule = PluralRule.parse("nplurals=2; plural=(n != 1);")
        self.assertEqual(rule.nplurals, 2)
        self.assertEqual(rule.expression, "(n != 1)")
        self.assertEqual(rule.header_value, "nplurals=2; plural=(n != 1);")

    def test_no_space_and_trailing_semicolon(self):
        rule = PluralRule.parse("nplurals=1;plural=0;")
        self.assertEqual((rule.nplurals, rule.expression), (1, "0"))

    def test_legacy_variable_name(self):
        self.assertEqual(PluralRule.parse("nplurals=2; plural=(pluraln != 1);").index_for(1), 0)

    def test_invalid_inputs(self):
        for text in ["", "nplurals=2", "plural=(n!=1)", "nplurals=abc; plural=(n!=1);", "nplurals=0; plural=0;", "nplurals=2; plural=(n!=1;"]:
            with self.subTest(text=text):
                with self.assertRaises(PluralRuleError):
                    PluralRule.parse(text)


class EvalTest(unittest.TestCase):
    def test_english(self):
        rule = PluralRule.parse("nplurals=2; plural=(n != 1);")
        self.assertEqual([rule.index_for(n) for n in (0, 1, 2, 15)], [1, 0, 1, 1])

    def test_russian_boundaries(self):
        rule = PluralRule.parse(RUSSIAN)
        # 11/12/13 这类 teens 归入"多"形态，112 同理
        cases = {1: 0, 2: 1, 4: 1, 5: 2, 11: 2, 21: 0, 22: 1, 24: 1, 25: 2, 101: 0, 111: 2, 112: 2, 122: 1}
        for n, expected in cases.items():
            with self.subTest(n=n):
                self.assertEqual(rule.index_for(n), expected)

    def test_chinese_single_form(self):
        rule = PluralRule.parse("nplurals=1; plural=0;")
        self.assertEqual({rule.index_for(n) for n in range(0, 50)}, {0})

    def test_arabic_six_forms(self):
        rule = rule_for_language("ar")
        self.assertEqual(rule.nplurals, 6)
        self.assertEqual([rule.index_for(n) for n in (0, 1, 2, 3, 10, 11, 100)], [0, 1, 2, 3, 3, 4, 5])

    def test_index_clamped_into_range(self):
        # 表达式越界时收敛到合法下标，绝不让调用方拿到非法形态号
        rule = PluralRule.parse("nplurals=2; plural=(n > 5 ? 7 : 0);")
        self.assertEqual(rule.index_for(10), 1)

    def test_division_by_zero_rejected(self):
        rule = PluralRule.parse("nplurals=2; plural=(n / (n - 1) > 1);")
        with self.assertRaises(PluralRuleError):
            rule.index_for(1)

    def test_unsafe_expression_rejected(self):
        for expression in ["__import__('os').system('dir')", "(n != 1)();", "[0][0]"]:
            with self.subTest(expression=expression):
                with self.assertRaises(PluralRuleError):
                    PluralRule.parse(f"nplurals=2; plural={expression};").index_for(2)


class LanguageTableTest(unittest.TestCase):
    def test_full_code_and_bare_language(self):
        for code in ("zh_CN", "zh-CN", "ZH_cn", "zh"):
            with self.subTest(code=code):
                self.assertEqual(rule_for_language(code).nplurals, 1)

    def test_regional_variant_wins(self):
        self.assertEqual(rule_for_language("pt_BR").expression, "(n > 1)")
        self.assertEqual(rule_for_language("pt").expression, "(n != 1)")

    def test_unknown_language(self):
        self.assertIsNone(rule_for_language("xx_YY"))
        self.assertIsNone(rule_for_language(""))

    def test_every_preset_is_parseable(self):
        for code in known_languages():
            rule = rule_for_language(code)
            self.assertEqual(rule.nplurals, len(list(rule.forms)), code)
            rule.index_for(3)

    def test_catalog_falls_back_when_header_broken(self):
        catalog = POCatalog.loads('msgid ""\nmsgstr "Plural-Forms: 坏掉的声明\\n"\n')
        self.assertEqual(catalog.plural_rule.nplurals, 2)


if __name__ == "__main__":
    unittest.main()
