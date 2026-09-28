"""单行转义编解码测试。"""

from __future__ import annotations

import unittest

from potext.escaping import decode_line, encode_line, escape_po, decode_escapes


class EncodeDecodeTest(unittest.TestCase):
    def assert_roundtrip(self, value: str) -> None:
        self.assertEqual(decode_line(encode_line(value)), value, f"往返失败: {value!r}")

    def test_roundtrip_samples(self):
        for value in [
            "",
            "Hello",
            "第一行\n第二行",
            "\n前置换行",
            "尾随换行\n",
            "\n\n多个空行\n\n",
            "行首空格",
            "行尾空格 ",
            "  两端都有空格  ",
            "   ",
            "制表\t分隔",
            "反斜杠 C:\\path\\to",
            "混合 \\n 字面量与真换行\n下一行",
            '引号 "quoted"',
            "回车\r换行",
            "%s 与 {name} 和 %1$d",
            "\u3000全角空格",
        ]:
            with self.subTest(value=value):
                self.assert_roundtrip(value)

    def test_line_never_contains_real_newline(self):
        self.assertNotIn("\n", encode_line("a\nb\nc"))
        self.assertNotIn("\n", encode_line("\n\n"))

    def test_boundary_spaces_escaped(self):
        self.assertEqual(encode_line(" x "), "\\x20x\\x20")

    def test_po_escape(self):
        self.assertEqual(escape_po('a"b\\c\nd'), 'a\\"b\\\\c\\nd')
        self.assertEqual(decode_escapes('a\\"b\\\\c\\nd'), 'a"b\\c\nd')

    def test_unknown_escape_kept_verbatim(self):
        # 用户在译文里手写的未知转义原样保留，不吞字符（\\p 不是合法转义）
        self.assertEqual(decode_line("路径 \\path"), "路径 \\path")
        self.assertEqual(decode_line("结尾孤立反杠\\"), "结尾孤立反杠\\")

    def test_valid_escape_follows_gettext(self):
        # 与 gettext 一致：\f 是换页符。自己导出的行会把真反斜杠写成 \\，因此不会歧义
        self.assertEqual(decode_line("a\\fb"), "a\x0cb")
        self.assertEqual(decode_line("a\\\\fb"), "a\\fb")


if __name__ == "__main__":
    unittest.main()
