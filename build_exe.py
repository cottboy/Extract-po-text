#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将Extract-po-text程序打包成可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_exe():
    """构建可执行文件"""
    print("=== Extract-po-text 打包工具 ===")
    
    # 获取当前目录
    current_dir = Path(__file__).parent
    print(f"当前目录: {current_dir}")
    
    # 检查主程序文件
    main_file = current_dir / "main.py"
    if not main_file.exists():
        print("错误: 找不到main.py文件")
        return False
    
    # 清理之前的构建文件
    build_dir = current_dir / "build"
    dist_dir = current_dir / "dist"
    spec_file = current_dir / "main.spec"
    
    print("\n清理之前的构建文件...")
    for dir_path in [build_dir, dist_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"已删除: {dir_path}")
    
    if spec_file.exists():
        spec_file.unlink()
        print(f"已删除: {spec_file}")
    
    # PyInstaller命令参数
    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",                    # 打包成单个exe文件
        "--windowed",                   # 不显示控制台窗口（GUI程序）
        "--name=Extract-po-text",       # 可执行文件名称
        "--icon=NONE",                  # 暂时不设置图标
        "--add-data=requirements.txt;.", # 包含requirements.txt
        "--hidden-import=tkinter",      # 确保tkinter被包含
        "--hidden-import=tkinter.ttk",  # 确保tkinter.ttk被包含
        "--hidden-import=tkinter.filedialog", # 确保文件对话框被包含
        "--hidden-import=tkinter.messagebox", # 确保消息框被包含
        "--hidden-import=polib",        # 确保polib被包含
        "--collect-all=polib",          # 收集polib的所有依赖
        "--noconfirm",                  # 不询问确认
        str(main_file)                   # 主程序文件
    ]
    
    print("\n开始打包...")
    print(f"执行命令: {' '.join(pyinstaller_args)}")
    
    try:
        # 执行PyInstaller
        result = subprocess.run(
            pyinstaller_args,
            cwd=current_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print("\n✓ 打包成功！")
            
            # 检查生成的exe文件
            exe_file = dist_dir / "Extract-po-text.exe"
            if exe_file.exists():
                file_size = exe_file.stat().st_size / (1024 * 1024)  # MB
                print(f"\n生成的可执行文件:")
                print(f"  路径: {exe_file}")
                print(f"  大小: {file_size:.1f} MB")
                
                return True
            else:
                print("\n✗ 错误: 未找到生成的exe文件")
                return False
        else:
            print("\n✗ 打包失败！")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"\n✗ 打包过程中出现异常: {e}")
        return False

def main():
    """主函数"""
    success = build_exe()
    
    if success:
        print("\n🎉 打包完成！可执行文件位于 dist 目录中。")
        print("\n提示: 您可以将 dist/Extract-po-text.exe 复制到任何地方使用。")
    else:
        print("\n❌ 打包失败，请检查错误信息。")

if __name__ == "__main__":
    main()