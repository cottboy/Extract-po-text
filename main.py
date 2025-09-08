#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO文件翻译工具主程序
支持GUI界面和命令行两种使用方式
"""

import sys
import argparse
import os
from po_parser import POParser
from text_processor import TextProcessor


def print_banner():
    """打印程序横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                        PO文件翻译工具                         ║
║                                                              ║
║  功能：批量导出PO文件中的待翻译文本，翻译后重新导入生成新PO文件    ║
║  作者：cottboy                                                ║
║  支持：GUI界面 / 命令行操作                                    ║
╚══════════════════════════════════════════════════════════════╝
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


def run_cli(args):
    """运行命令行模式"""
    parser = POParser()
    processor = TextProcessor()
    
    try:
        # 加载PO文件
        print(f"正在加载PO文件: {args.input}")
        if not parser.load_po_file(args.input):
            print("加载PO文件失败")
            return False
        
        # 显示文件信息
        info = parser.get_translation_info()
        print(f"文件信息:")
        print(f"  总条目数: {info['total']}")
        print(f"  已翻译: {info['translated']}")
        print(f"  待翻译: {info['untranslated']}")
        
        if info['untranslated'] == 0:
            print("没有待翻译的文本")
            return True
        
        # 导出待翻译文本
        if args.export:
            print(f"\n正在导出待翻译文本到: {args.export}")
            texts = parser.get_untranslated_texts()
            
            # 设置导出格式
            if args.format:
                processor.set_export_format(args.format)
            
            success = processor.export_texts_to_file(texts, args.export, add_context=True)
            if success:
                print(f"成功导出 {len(texts)} 条待翻译文本")
                print("\n请使用翻译工具翻译导出的文本文件，然后使用 --import 参数导入翻译结果")
            else:
                print("导出失败")
                return False
        
        # 导入翻译结果并生成新PO文件
        if args.import_file and args.output:
            print(f"\n正在从文件导入翻译: {args.import_file}")
            translations = processor.import_texts_from_file(args.import_file)
            
            if not translations:
                print("无法读取翻译文件")
                return False
            
            # 验证翻译数量
            is_valid, message = processor.validate_translation_count(info['untranslated'], translations)
            if not is_valid:
                print(f"验证失败: {message}")
                return False
            
            print(f"成功读取 {len(translations)} 条翻译")
            
            # 应用翻译
            for i, translation in enumerate(translations):
                if i < len(parser.untranslated_entries):
                    parser.untranslated_entries[i].msgstr = processor.clean_text(translation)
            
            # 保存翻译后的PO文件
            print(f"正在生成翻译后的PO文件: {args.output}")
            success = parser.save_translated_po(args.output, args.language)
            
            if success:
                print("翻译完成！")
                # 显示最终统计
                final_info = parser.get_translation_info()
                print(f"最终统计:")
                print(f"  总条目数: {final_info['total']}")
                print(f"  已翻译: {final_info['translated']}")
                print(f"  待翻译: {final_info['untranslated']}")
            else:
                print("生成PO文件失败")
                return False
        
        return True
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        return False


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="PO文件翻译工具 - 批量导出待翻译文本，翻译后重新导入",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  GUI模式:
    python main.py
    python main.py --gui
  
  命令行模式:
    # 导出待翻译文本
    python main.py -i input.po -e untranslated.txt
    
    # 导入翻译结果并生成新PO文件
    python main.py -i input.po --import translated.txt -o output.po -l zh_CN
    
    # 一步完成（需要手动翻译中间文件）
    python main.py -i input.po -e temp.txt --import temp_translated.txt -o output.po
        """
    )
    
    parser.add_argument('--gui', action='store_true', help='启动GUI界面（默认模式）')
    parser.add_argument('-i', '--input', help='输入的PO文件路径')
    parser.add_argument('-e', '--export', help='导出待翻译文本的文件路径')
    parser.add_argument('--import', dest='import_file', help='导入翻译结果的文件路径')
    parser.add_argument('-o', '--output', help='输出翻译后PO文件的路径')
    parser.add_argument('-l', '--language', default='zh_CN', help='目标语言代码（默认: zh_CN）')
    parser.add_argument('-f', '--format', choices=['numbered', 'plain', 'json'], 
                       default='numbered', help='导出文本格式（默认: numbered）')
    parser.add_argument('--version', action='version', version='PO翻译工具 v1.0')
    
    args = parser.parse_args()
    
    # 打印横幅
    print_banner()
    
    # 如果没有提供任何参数，或者明确指定GUI模式，则启动GUI
    if len(sys.argv) == 1 or args.gui:
        print("启动GUI界面...")
        run_gui()
    else:
        # 命令行模式
        if not args.input:
            print("错误: 命令行模式需要指定输入文件 (-i/--input)")
            parser.print_help()
            sys.exit(1)
        
        if not os.path.exists(args.input):
            print(f"错误: 输入文件不存在: {args.input}")
            sys.exit(1)
        
        # 检查参数组合
        if args.import_file and not args.output:
            print("错误: 使用 --import 时必须指定输出文件 (-o/--output)")
            sys.exit(1)
        
        if args.import_file and not os.path.exists(args.import_file):
            print(f"错误: 翻译文件不存在: {args.import_file}")
            sys.exit(1)
        
        print("运行命令行模式...")
        success = run_cli(args)
        
        if success:
            print("\n操作完成！")
            sys.exit(0)
        else:
            print("\n操作失败！")
            sys.exit(1)


if __name__ == "__main__":
    main()