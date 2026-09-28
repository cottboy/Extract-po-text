#!/usr/bin/env python3
"""打包脚本：用 PyInstaller 把 potext 打成单文件可执行程序。

程序本身零第三方依赖，只需要 Python 自带的 tkinter，因此打包很轻。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXE_NAME = "Extract-po-text"
BUILD_DIRS = ("build", "dist")


def _clean(root: Path) -> None:
    import shutil

    for name in (*BUILD_DIRS, f"{EXE_NAME}.spec"):
        target = root / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        print(f"已清理: {target}")


def _command(main_file: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",  # 图形界面程序，不附带控制台
        f"--name={EXE_NAME}",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.scrolledtext",
        "--noconfirm",
        str(main_file),
    ]


def build() -> bool:
    root = Path(__file__).parent
    main_file = root / "main.py"
    if not main_file.is_file():
        print(f"错误: 找不到入口文件 {main_file}")
        return False

    print(f"=== {EXE_NAME} 打包 ===")
    print(f"工作目录: {root}")
    _clean(root)

    command = _command(main_file)
    print("\n开始打包...")
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print("打包失败：")
        print(result.stdout)
        print(result.stderr)
        return False

    exe = root / "dist" / f"{EXE_NAME}.exe"
    if not exe.is_file():
        print(f"打包结束但没有找到 {exe}")
        return False

    print(f"打包成功: {exe}（{exe.stat().st_size / 1024 / 1024:.1f} MB）")
    return True


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
