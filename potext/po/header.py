"""PO 头部（msgid 为空的元数据条目）。

字段顺序与未知字段都要保留，因此内部用普通 dict（Python 3.7+ 保序）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..exceptions import PluralRuleError
from ..plural import PluralRule, DEFAULT_PLURAL_RULE

_CHARSET_RE = re.compile(r"charset\s*=\s*([\w:.+-]+)", re.IGNORECASE)


@dataclass
class POHeader:
    fields: dict[str, str] = field(default_factory=dict)

    @classmethod
    def parse(cls, msgstr: str) -> "POHeader":
        fields: dict[str, str] = {}
        for line in (msgstr or "").split("\n"):
            line = line.strip()
            if not line:
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            fields[key.strip()] = value.strip()
        return cls(fields)

    def as_msgstr(self) -> str:
        return "".join(f"{key}: {value}\n" for key, value in self.fields.items())

    def get(self, key: str, default: str = "") -> str:
        return self.fields.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.fields[key] = value

    @property
    def language(self) -> str:
        return self.get("Language")

    @property
    def charset(self) -> str | None:
        content_type = self.get("Content-Type")
        match = _CHARSET_RE.search(content_type)
        if match:
            return match.group(1)
        match = _CHARSET_RE.search(self.as_msgstr())
        return match.group(1) if match else None

    @property
    def plural_rule(self) -> PluralRule:
        raw = self.get("Plural-Forms")
        if not raw:
            return DEFAULT_PLURAL_RULE
        try:
            return PluralRule.parse(raw)
        except PluralRuleError:
            return DEFAULT_PLURAL_RULE

    def ensure_utf8(self) -> None:
        """文件按 UTF-8 写出时头部声明必须同步，否则 gettext 会按错误编码解析。"""
        content_type = self.get("Content-Type")
        if _CHARSET_RE.search(content_type):
            content_type = _CHARSET_RE.sub("charset=UTF-8", content_type)
        else:
            content_type = f"{'text/plain; charset=UTF-8' if not content_type else content_type + '; charset=UTF-8'}"
        self.set("Content-Type", content_type)
        self.set("Content-Transfer-Encoding", "8bit")
