"""占位符检查：机器翻译最爱吃掉 ``%s``、``{0}``、``%1`` 这类变量。

只做提取与比对，修复是显式的可选动作，绝不静默改写译文。
"""

from __future__ import annotations

import re

_PRINTF_RE = re.compile(
    r"%(?!%)(?:\d+\$|\([^)]+\))?[#0\- +]*(?:\*|\d+)?(?:\.(?:\*|\d+))?(?:hh|h|ll|l|j|z|t|L)?[diuoxXfFeEgGaAcspn]"
)
_QT_RE = re.compile(r"%(?!%)(\d+)\b")
_BRACE_RE = re.compile(r"\{(?:\w+|\d+)(?:[^{}]*)\}")
# 已经在 printf 家族里出现的位置式记号，避免 %1$s 又被 Qt 规则拆成 %1
_POSITIONAL_PREFIX = re.compile(r"%\d+\$")


def extract(text: str) -> list[str]:
    """按出现顺序去重返回全部占位符。"""
    if not text:
        return []
    tokens: list[str] = []
    seen: set[str] = set()

    def push(token: str) -> None:
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)

    for match in _PRINTF_RE.finditer(text):
        push(match.group(0))
    positional = {match.group(0) for match in _POSITIONAL_PREFIX.finditer(text)}
    for match in _QT_RE.finditer(text):
        token = "%" + match.group(1)
        if not any(token in p for p in positional):
            push(token)
    for match in _BRACE_RE.finditer(text):
        push(match.group(0))
    return tokens


def diff(source: str, translation: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """返回译文中缺失与多出的占位符。"""
    src = extract(source)
    tgt = set(extract(translation))
    missing = tuple(t for t in src if t not in tgt)
    extra = tuple(t for t in sorted(tgt) if t not in set(src))
    return missing, extra


def repair(translation: str, missing: tuple[str, ...]) -> str:
    """把缺失的占位符补到译文末尾，让 gettext 运行时不至于因缺参崩溃。"""
    if not missing:
        return translation
    text = translation or ""
    separator = "" if not text or text.endswith((" ", "\u3000")) else " "
    return f"{text}{separator}{' '.join(missing)}".rstrip()
