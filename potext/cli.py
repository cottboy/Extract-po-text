"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exceptions import PoTextError
from .plural import known_languages, rule_for_language
from .service import Session
from .workbook import Options

EXIT_OK = 0
EXIT_ERROR = 1
#: 报告里最多列出的占位符异常条数，超出部分给出总数
MAX_LISTED_ISSUES = 30


def _emit(message: str = "") -> None:
    print(message)


def _print_summary(title: str, lines: list[str]) -> None:
    _emit(f"[{title}]")
    for line in lines:
        _emit(f"  {line}")


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("po", type=Path, help="PO 或 POT 文件")
    parser.add_argument("--all", dest="include_translated", action="store_true", help="连已翻译的条目一起导出（回填时会覆盖原译文）")
    parser.add_argument("--include-fuzzy", action="store_true", help="把标记为 fuzzy（需复核）的条目也当作待翻译")
    parser.add_argument("--lang", dest="target_lang", metavar="CODE", help="目标语言代码，决定复数形态数并写入头部，如 zh_CN、ru")
    parser.add_argument("--plural-forms", metavar="DECL", help='显式指定复数声明，如 "nplurals=2; plural=(n != 1);"，优先级高于 --lang 与文件头部')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="potext",
        description="PO 文件批量翻译工作台：导出全部待翻译文本，翻译后整体回填",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""工作流示例：
  potext stats themes/demo_zh.po
  potext extract themes/demo_zh.po -o demo.txt      # 得到一行一条的待翻译文本
  # 把 demo.txt 交给翻译工具，逐行填好译文（不增删行）
  potext apply themes/demo_zh.po demo.txt -o demo_new.po --lang zh_CN

导出文档里换行以 \\n 形式转义，因此一条记录严格占一行。""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    stats = sub.add_parser("stats", help="查看 PO 文件的翻译进度")
    stats.add_argument("po", type=Path)
    stats.set_defaults(func=_cmd_stats)

    extract = sub.add_parser("extract", help="导出待翻译文本")
    _add_common(extract)
    extract.add_argument("-o", "--output", type=Path, required=True, help="输出的一行一条文本文件")
    extract.set_defaults(func=_cmd_extract)

    apply = sub.add_parser("apply", help="把翻译好的文本回填成 PO")
    _add_common(apply)
    apply.add_argument("translations", type=Path, help="翻译完成的文本文件")
    apply.add_argument("-o", "--output", type=Path, help="输出的 PO 文件；省略时只校验不写出")
    apply.add_argument("--no-align-newlines", dest="align_newlines", action="store_false", help="不自动对齐译文首尾换行数量")
    apply.add_argument("--repair-placeholders", action="store_true", help="把译文丢失的占位符补到行尾")
    apply.set_defaults(func=_cmd_apply)

    langs = sub.add_parser("langs", help="列出内置复数规则的语言代码")
    langs.set_defaults(func=_cmd_langs)

    gui = sub.add_parser("gui", help="启动图形界面")
    gui.set_defaults(func=_cmd_gui)
    return parser


def _options(args: argparse.Namespace) -> Options:
    return Options(
        include_translated=getattr(args, "include_translated", False),
        include_fuzzy=getattr(args, "include_fuzzy", False),
        target_lang=getattr(args, "target_lang", None),
        plural_forms=getattr(args, "plural_forms", None),
        align_newlines=getattr(args, "align_newlines", True),
        repair_placeholders=getattr(args, "repair_placeholders", False),
    )


def _cmd_stats(args: argparse.Namespace) -> int:
    _print_summary("进度", Session(args.po).stats().summary())
    return EXIT_OK


def _cmd_extract(args: argparse.Namespace) -> int:
    report = Session(args.po).export(args.output, _options(args))
    _print_summary("导出", [*report.summary(), f"已写出：{args.output}"])
    if report.exported_slots == 0:
        _emit("  没有需要翻译的条目，文档为空")
    return EXIT_OK


def _cmd_apply(args: argparse.Namespace) -> int:
    report = Session(args.po).apply(args.translations, args.output, _options(args))
    title = "生成" if args.output else "校验"
    _print_summary(title, report.summary())
    if report.issues:
        _emit("  占位符问题：")
        for issue in report.issues[:MAX_LISTED_ISSUES]:
            _emit(f"    - {issue.describe()}")
        if len(report.issues) > MAX_LISTED_ISSUES:
            _emit(f"    ……另有 {len(report.issues) - MAX_LISTED_ISSUES} 条未列出")
    if not args.output:
        _emit("  未指定 -o/--output，只做了校验没有写出文件")
    return EXIT_OK


def _cmd_langs(args: argparse.Namespace) -> int:
    groups: dict[str, list[str]] = {}
    for code in known_languages():
        rule = rule_for_language(code)
        groups.setdefault(rule.header_value, []).append(code)
    _emit("内置复数规则（--lang 可用）：")
    for formula, codes in groups.items():
        _emit(f"  {formula}")
        _emit(f"    {', '.join(codes)}")
    return EXIT_OK


def _cmd_gui(args: argparse.Namespace) -> int:
    from .gui import main as gui_main

    return gui_main()


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台默认是 GBK，含俄语/阿拉伯语等字符的报告会让 print 崩掉
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (PoTextError, FileNotFoundError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as error:
        print(f"文件读写失败：{error}", file=sys.stderr)
        return EXIT_ERROR
