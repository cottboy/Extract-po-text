"""异常类型。"""

from __future__ import annotations


class PoTextError(Exception):
    """本项目的全部可预期错误基类。"""


class PoSyntaxError(PoTextError):
    """PO 文件语法错误。"""

    def __init__(self, line_number: int, detail: str, source: str):
        super().__init__(f"第 {line_number} 行解析失败: {detail}（内容: {source.strip()[:80]}）")
        self.line_number = line_number
        self.detail = detail


class PluralRuleError(PoTextError):
    """Plural-Forms 声明非法或求值失败。"""


class WorkbookError(PoTextError):
    """翻译文档与 PO 文件对不上。"""
