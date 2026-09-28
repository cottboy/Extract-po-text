"""potext —— PO 文件批量翻译工作台。

对外只暴露服务层与少数数据结构，CLI 和 GUI 都建立在它之上。
"""

from __future__ import annotations

from .exceptions import (
    PluralRuleError,
    PoSyntaxError,
    PoTextError,
    WorkbookError,
)
from .plural import (
    DEFAULT_PLURAL_RULE,
    PluralRule,
    known_languages,
    rule_for_language,
)
from .po import POEntry, POCatalog, POHeader
from .service import Session, Stats
from .workbook import ApplyReport, ExtractReport, Options, PlaceholderIssue, Slot

__all__ = [
    "ApplyReport",
    "DEFAULT_PLURAL_RULE",
    "ExtractReport",
    "Options",
    "POCatalog",
    "POEntry",
    "POHeader",
    "PluralRule",
    "PluralRuleError",
    "PoSyntaxError",
    "PoTextError",
    "PlaceholderIssue",
    "Session",
    "Slot",
    "Stats",
    "WorkbookError",
    "known_languages",
    "rule_for_language",
]

__version__ = "2.0.0"
