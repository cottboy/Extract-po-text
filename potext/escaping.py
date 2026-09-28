"""单行编解码：把可能含换行的 PO 字符串压成一行，并能严格还原。

一条待翻译记录必须占一行，因此沿用 gettext 的转义惯例，把换行、制表符、反斜杠写成
字面量 ``\\n`` ``\\t`` ``\\\\``。另外行首行尾的空格编码成 ``\\x20``，因为多数编辑器
保存时会剥掉行尾空白，导致译文语义丢失。

解码一律采用宽松策略：无法识别的转义原样保留（用户在译文里手写 ``C:\\path`` 这种
单斜杠时不会被吞掉），保证任何输入都能得到确定的输出而不会中断整个文件的处理。
"""

from __future__ import annotations

_PO_ESCAPES: tuple[tuple[str, str], ...] = (
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
)

_LINE_ESCAPES: tuple[tuple[str, str], ...] = (
    ("\\", "\\\\"),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
)

_NAMED = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "\\": "\\",
    '"': '"',
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "v": "\v",
    "0": "\0",
    " ": " ",
}

# 转义后仍会留在行首尾的空白只有普通空格，其余空白都已被转义成字面量
_ESCAPED_SPACE = "\\x20"
_HEX_WIDTH = {"x": 2, "u": 4, "U": 8}


def _apply(text: str, table: tuple[tuple[str, str], ...]) -> str:
    # 反斜杠必须最先替换，否则会把随后生成的转义序列再转义一遍
    out = text
    for raw, enc in table:
        out = out.replace(raw, enc)
    return out


def escape_po(value: str) -> str:
    """转义成 PO 引号内的内容。"""
    return _apply(value, _PO_ESCAPES)


def decode_escapes(escaped: str) -> str:
    """还原 :func:`escape_po` / :func:`encode_line` 产生的转义，未知转义原样保留。"""
    out: list[str] = []
    i = 0
    length = len(escaped)
    while i < length:
        ch = escaped[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= length:
            out.append("\\")
            break
        nxt = escaped[i + 1]
        if nxt in _NAMED:
            out.append(_NAMED[nxt])
            i += 2
            continue
        width = _HEX_WIDTH.get(nxt)
        if width:
            digits = escaped[i + 2 : i + 2 + width]
            if len(digits) == width and all(c in "0123456789abcdefABCDEF" for c in digits):
                out.append(chr(int(digits, 16)))
                i += 2 + width
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def encode_line(value: str) -> str:
    """把任意 PO 字符串编码成一行可直接放进翻译文档的文本。"""
    escaped = _apply(value, _LINE_ESCAPES)
    if not escaped:
        return escaped
    if escaped.strip(" ") == "":
        # 整条只有空格，逐字节保护
        return _ESCAPED_SPACE * len(escaped)
    leading = len(escaped) - len(escaped.lstrip(" "))
    trailing = len(escaped) - len(escaped.rstrip(" "))
    body = escaped[leading : len(escaped) - trailing]
    return _ESCAPED_SPACE * leading + body + _ESCAPED_SPACE * trailing


def decode_line(line: str) -> str:
    """还原 :func:`encode_line`；对译文里的裸空格不做任何裁剪。"""
    return decode_escapes(line)
