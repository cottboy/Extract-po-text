#!/usr/bin/env python3
"""程序入口：带参数走命令行，直接双击（无参数）启动图形界面。"""

from __future__ import annotations

import sys

from potext.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["gui"]))
