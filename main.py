#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO文件翻译工具主程序
只支持GUI界面使用
"""

import sys


def print_banner():
    """打印程序横幅"""
    banner = """
╔════════════════════════════════════════════════════════════════╗
║                        PO文件翻译工具                          ║
║                                                                ║
║  功能：批量导出PO文件中的待翻译文本，翻译后重新导入生成新PO文件║
║  作者：cottboy                                                 ║
╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_gui():
    """运行GUI界面"""
    try:
        from gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"启动GUI失败: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"GUI运行错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    # 打印横幅
    print_banner()
    
    # 启动GUI界面
    print("启动GUI界面...")
    run_gui()


if __name__ == "__main__":
    main()