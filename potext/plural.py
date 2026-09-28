"""复数规则：解析 PO 头部的 ``Plural-Forms`` 并按 n 求出复数形态下标。

gettext 的复数表达式是 C 语言子集（含三元运算符 ``?:``，Python 无法直接 eval），
所以这里自己做了个词法 + 递归下降求值器。表达式来自 PO 文件头，属于不可信输入，
求值全程不涉及 eval/exec，遇到语法外的字符直接报错。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .exceptions import PluralRuleError

_MAX_NPLURALS = 64
# 最常见的英语模板，PO/POT 头里缺失复数声明时按它处理
DEFAULT_RULE_TEXT = "nplurals=2; plural=(n != 1);"

_TOKEN_RE = re.compile(
    r"""(?P<num>\d+)
      | (?P<name>[A-Za-z_]\w*)
      | (?P<op>\|\||&&|==|!=|<=|>=|[-+*/%!?():<>])
      | (?P<skip>\s+)""",
    re.VERBOSE,
)


def _tokenize(src: str) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    pos = 0
    while pos < len(src):
        match = _TOKEN_RE.match(src, pos)
        if not match or match.start() != pos:
            raise PluralRuleError(f"复数表达式含非法字符 {src[pos]!r}: {src!r}")
        pos = match.end()
        if match.lastgroup == "skip":
            continue
        if match.lastgroup == "num":
            tokens.append(("num", int(match.group())))
        elif match.lastgroup == "name":
            tokens.append(("name", match.group()))
        else:
            tokens.append(("op", match.group()))
    return tokens


class _Evaluator:
    """对已 tokenize 的 C 子集表达式求值，变量 n 由外部传入。"""

    def __init__(self, tokens: list[tuple[str, object]], n: int):
        self._tokens = tokens
        self._n = n
        self._pos = 0

    def parse(self) -> int:
        value = self._ternary()
        if self._pos != len(self._tokens):
            raise PluralRuleError(f"复数表达式存在多余内容: {self._tokens[self._pos:]!r}")
        return value

    def _peek(self) -> str | None:
        if self._pos >= len(self._tokens):
            return None
        kind, value = self._tokens[self._pos]
        return value if kind == "op" else None

    def _eat(self, op: str) -> bool:
        if self._peek() == op:
            self._pos += 1
            return True
        return False

    def _ternary(self) -> int:
        cond = self._binary(0)
        if self._eat("?"):
            true_branch = self._ternary()
            if not self._eat(":"):
                raise PluralRuleError("三元表达式缺少 ':'")
            false_branch = self._ternary()
            return true_branch if cond != 0 else false_branch
        return cond

    # C 运算符优先级，数值越小结合越松
    _LEVELS: tuple[tuple[str, ...], ...] = (
        ("||",),
        ("&&",),
        ("==", "!="),
        ("<", "<=", ">", ">="),
        ("+", "-"),
        ("*", "/", "%"),
    )

    def _binary(self, level: int) -> int:
        if level >= len(self._LEVELS):
            return self._unary()
        left = self._binary(level + 1)
        while (op := self._peek()) in self._LEVELS[level]:
            self._pos += 1
            right = self._binary(level + 1)
            left = self._apply(op, left, right)
        return left

    def _unary(self) -> int:
        if self._eat("!"):
            return 0 if self._unary() != 0 else 1
        if self._eat("-"):
            return -self._unary()
        if self._eat("+"):
            return self._unary()
        return self._primary()

    def _primary(self) -> int:
        if self._pos >= len(self._tokens):
            raise PluralRuleError("复数表达式不完整")
        kind, value = self._tokens[self._pos]
        if kind == "num":
            self._pos += 1
            return int(value)
        if kind == "name":
            # 老式 PO 头用 pluraln，新式用 n
            if value not in ("n", "pluraln"):
                raise PluralRuleError(f"复数表达式含未知变量 {value!r}")
            self._pos += 1
            return self._n
        if self._eat("("):
            inner = self._ternary()
            if not self._eat(")"):
                raise PluralRuleError("复数表达式括号不匹配")
            return inner
        raise PluralRuleError(f"复数表达式出现意外记号 {value!r}")

    @staticmethod
    def _apply(op: str, left: int, right: int) -> int:
        match op:
            case "||":
                return 1 if (left != 0 or right != 0) else 0
            case "&&":
                return 1 if (left != 0 and right != 0) else 0
            case "==":
                return 1 if left == right else 0
            case "!=":
                return 1 if left != right else 0
            case "<":
                return 1 if left < right else 0
            case "<=":
                return 1 if left <= right else 0
            case ">":
                return 1 if left > right else 0
            case ">=":
                return 1 if left >= right else 0
            case "+":
                return left + right
            case "-":
                return left - right
            case "*":
                return left * right
            case "/":
                if right == 0:
                    raise PluralRuleError("复数表达式除数为 0")
                return _c_div(left, right)
            case "%":
                if right == 0:
                    raise PluralRuleError("复数表达式模数为 0")
                return left - _c_div(left, right) * right
        raise PluralRuleError(f"不支持的运算符 {op!r}")


def _c_div(left: int, right: int) -> int:
    """C 整数除法：向零取整。"""
    quotient = abs(left) // abs(right)
    return quotient if (left >= 0) == (right >= 0) else -quotient


@dataclass(frozen=True)
class PluralRule:
    nplurals: int
    expression: str

    @classmethod
    def parse(cls, text: str) -> "PluralRule":
        """解析 ``nplurals=3; plural=(n==1 ? 0 : ...);`` 形式的声明。"""
        nplurals: int | None = None
        expression: str | None = None
        for part in (text or "").split(";"):
            key, sep, raw_value = part.partition("=")
            if not sep:
                continue
            value = raw_value.strip()
            name = key.strip().lower().replace("-", "_")
            if name == "nplurals":
                if not value.isdigit():
                    raise PluralRuleError(f"nplurals 取值非法: {value!r}")
                nplurals = int(value)
            elif name in ("plural", "plural_expression"):
                expression = value
        if nplurals is None or expression is None:
            raise PluralRuleError(f"复数声明缺少 nplurals 或 plural: {text!r}")
        if not 1 <= nplurals <= _MAX_NPLURALS:
            raise PluralRuleError(f"nplurals 超出范围 1..{_MAX_NPLURALS}: {nplurals}")
        rule = cls(nplurals=nplurals, expression=expression)
        # 构造期完整走一遍语法（以 n=0 求值），括号不匹配之类的坏声明直接拒绝
        _Evaluator(_tokenize(expression), 0).parse()
        return rule

    @property
    def header_value(self) -> str:
        return f"nplurals={self.nplurals}; plural={self.expression};"

    @property
    def forms(self) -> range:
        return range(self.nplurals)

    def index_for(self, n: int) -> int:
        """返回数量 n 对应的复数形态下标，结果保证落在 [0, nplurals) 内。"""
        raw = _Evaluator(_tokenize(self.expression), int(n)).parse()
        return min(max(raw, 0), self.nplurals - 1)


DEFAULT_PLURAL_RULE = PluralRule.parse(DEFAULT_RULE_TEXT)


# 按公式分组，避免为每种语言重复一遍字符串
_FORMULA_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("nplurals=1; plural=0;", ("zh", "ja", "ko", "vi", "th", "id", "ms", "my", "km", "lo", "bo", "ug", "yo", "ig", "su")),
    ("nplurals=2; plural=(n != 1);", ("en", "es", "de", "nl", "pt", "sv", "da", "nb", "nn", "no", "fi", "el", "he", "it", "bg", "et", "ku", "ta", "te", "ml", "kn", "mr", "pa", "af", "sw", "ha", "az", "kk", "mn", "hy", "ka", "zu", "xh", "tr")),
    ("nplurals=2; plural=(n > 1);", ("fr", "tl", "pt_br", "mg", "fa", "am", "si")),
    ("nplurals=2; plural=(n % 10 != 1 || n % 100 >= 11);", ("is",)),
    ("nplurals=2; plural=(n == 1 || n % 10 == 1 ? 0 : 1);", ("mk",)),
    ("nplurals=2; plural=(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2);", ("lv",)),
    ("nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;", ("cs", "sk")),
    ("nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);", ("pl",)),
    (
        "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
        ("ru", "uk", "be", "hr", "sr", "bs", "sh", "mo"),
    ),
    ("nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2);", ("lt",)),
    ("nplurals=3; plural=(n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2);", ("ro",)),
    ("nplurals=3; plural=(n==1) ? 0 : (n==2) ? 1 : 2;", ("sa", "slo")),
    ("nplurals=4; plural=(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3);", ("sl",)),
    ("nplurals=4; plural=(n==1) ? 0 : (n==2) ? 1 : (n != 8 && n != 11) ? 2 : 3;", ("cy",)),
    ("nplurals=4; plural=(n==1 || n==11) ? 0 : (n==2 || n==12) ? 1 : (n > 2 && n < 20) ? 2 : 3;", ("gd",)),
    (
        "nplurals=4; plural=(n==1) ? 0 : (n==0 || (n%100 > 1 && n%100 < 11)) ? 1 : (n%100 > 10 && n%100 < 20) ? 2 : 3;",
        ("mt",),
    ),
    (
        "nplurals=5; plural=n==1 ? 0 : n==2 ? 1 : (n>2 && n<7) ? 2 :(n>6 && n<11) ? 3 : 4;",
        ("ga",),
    ),
    (
        "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);",
        ("ar",),
    ),
)

_LANGUAGE_RULES: dict[str, str] = {
    code: formula for formula, codes in _FORMULA_GROUPS for code in codes
}


def normalize_language(code: str) -> str:
    return code.strip().lower().replace("-", "_")


def rule_for_language(code: str) -> PluralRule | None:
    """按语言代码查复数规则，先匹配完整代码再退化到纯语言段。"""
    if not code:
        return None
    normalized = normalize_language(code)
    for candidate in (normalized, normalized.split("_")[0]):
        formula = _LANGUAGE_RULES.get(candidate)
        if formula:
            return PluralRule.parse(formula)
    return None


def known_languages() -> list[str]:
    return sorted(_LANGUAGE_RULES)
