#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI界面模块
使用Tkinter创建用户友好的图形界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
from po_parser import POParser
from text_processor import TextProcessor


class POTranslatorGUI:
    """PO翻译工具GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("PO文件翻译工具")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # 初始化组件
        self.po_parser = POParser()
        self.text_processor = TextProcessor()
        
        # 状态变量
        self.current_po_file = ""
        self.current_export_file = ""
        self.current_import_file = ""
        
        # 创建界面
        self.create_widgets()
        
        # 设置样式
        self.setup_styles()
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        
        # 设置主题
        try:
            style.theme_use('clam')
        except:
            pass
        
        # 自定义样式
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 9))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="PO文件翻译工具", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 第一步：选择PO或POT文件
        step1_frame = ttk.LabelFrame(main_frame, text="第一步：选择PO或POT文件", padding="10")
        step1_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        step1_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step1_frame, text="PO/POT文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.po_file_var = tk.StringVar()
        self.po_file_entry = ttk.Entry(step1_frame, textvariable=self.po_file_var, state='readonly')
        self.po_file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(step1_frame, text="浏览", command=self.browse_po_file).grid(row=0, column=2)
        

        
        # 第二步：导出待翻译文本
        step2_frame = ttk.LabelFrame(main_frame, text="第二步：导出待翻译文本", padding="10")
        step2_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        step2_frame.columnconfigure(1, weight=1)
        
        ttk.Button(step2_frame, text="导出TXT", command=self.export_texts).grid(row=0, column=0)
        
        # 第三步：导入翻译结果
        step3_frame = ttk.LabelFrame(main_frame, text="第三步：导入翻译结果", padding="10")
        step3_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        step3_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step3_frame, text="翻译文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.import_file_var = tk.StringVar()
        self.import_file_entry = ttk.Entry(step3_frame, textvariable=self.import_file_var, state='readonly')
        self.import_file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(step3_frame, text="浏览", command=self.browse_import_file).grid(row=0, column=2)
        
        # 第四步：生成翻译后的PO文件
        step4_frame = ttk.LabelFrame(main_frame, text="第四步：生成翻译后的PO文件", padding="10")
        step4_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        step4_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step4_frame, text="语言代码:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.language_code_var = tk.StringVar(value="zh_CN")
        language_entry = ttk.Entry(step4_frame, textvariable=self.language_code_var, width=15)
        language_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Button(step4_frame, text="生成翻译后的PO文件", command=self.generate_translated_po).grid(row=0, column=2)
        

    
    def browse_po_file(self):
        """浏览选择PO或POT文件"""
        file_path = filedialog.askopenfilename(
            title="选择PO或POT文件",
            filetypes=[("PO/POT files", "*.po;*.pot"), ("PO files", "*.po"), ("POT files", "*.pot"), ("All files", "*.*")]
        )
        
        if file_path:
            self.po_file_var.set(file_path)
            self.current_po_file = file_path
            self.load_po_file(file_path)
    
    def load_po_file(self, file_path):
        """加载PO或POT文件"""
        def load_task():
            try:
                success = self.po_parser.load_po_file(file_path)
                
                if success:
                    messagebox.showinfo("成功", "PO/POT文件加载完成")
                else:
                    messagebox.showerror("错误", "加载PO/POT文件失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"加载PO/POT文件时发生错误: {str(e)}")
        
        # 在后台线程中执行
        threading.Thread(target=load_task, daemon=True).start()
    
    def export_texts(self):
        """导出待翻译文本"""
        if not self.current_po_file:
            messagebox.showwarning("警告", "请先选择PO文件")
            return
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            title="保存待翻译文本",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        def export_task():
            try:
                # 设置导出格式为plain
                self.text_processor.set_export_format("plain")
                
                # 获取待翻译文本
                texts = self.po_parser.get_untranslated_texts()
                
                if not texts:
                    messagebox.showinfo("信息", "没有待翻译的文本")
                    return
                
                # 导出文本
                success = self.text_processor.export_texts_to_file(texts, file_path, add_context=True)
                
                if success:
                    self.current_export_file = file_path
                    messagebox.showinfo("成功", f"成功导出 {len(texts)} 条待翻译文本到:\n{file_path}")
                else:
                    messagebox.showerror("错误", "导出文本失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"导出文本时发生错误: {str(e)}")
        
        threading.Thread(target=export_task, daemon=True).start()
    
    def browse_import_file(self):
        """浏览选择翻译文件"""
        file_path = filedialog.askopenfilename(
            title="选择翻译文件",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.import_file_var.set(file_path)
            self.current_import_file = file_path
    
    def generate_translated_po(self):
        """生成翻译后的PO文件"""
        if not self.current_po_file:
            messagebox.showwarning("警告", "请先选择PO文件")
            return
        
        if not self.current_import_file:
            messagebox.showwarning("警告", "请先选择翻译文件")
            return
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            title="保存翻译后的PO文件",
            defaultextension=".po",
            filetypes=[("PO files", "*.po"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        def generate_task():
            try:
                # 导入翻译文本
                translations = self.text_processor.import_texts_from_file(self.current_import_file)
                
                if not translations:
                    messagebox.showerror("错误", "无法读取翻译文件")
                    return
                
                # 验证翻译数量
                untranslated_count = len(self.po_parser.get_untranslated_texts())
                is_valid, message = self.text_processor.validate_translation_count(untranslated_count, translations)
                
                if not is_valid:
                    messagebox.showerror("错误", message)
                    return
                
                # 应用翻译
                for i, translation in enumerate(translations):
                    if i < len(self.po_parser.untranslated_entries):
                        self.po_parser.untranslated_entries[i].msgstr = self.text_processor.clean_text(translation)
                
                # 保存翻译后的PO文件
                language_code = self.language_code_var.get().strip()
                success = self.po_parser.save_translated_po(file_path, language_code)
                
                if success:
                    messagebox.showinfo("成功", f"成功生成翻译后的PO文件:\n{file_path}")
                else:
                    messagebox.showerror("错误", "生成PO文件失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"生成PO文件时发生错误: {str(e)}")
        
        threading.Thread(target=generate_task, daemon=True).start()


def main():
    """主函数"""
    root = tk.Tk()
    app = POTranslatorGUI(root)
    
    # 设置窗口图标（如果有的话）
    try:
        # root.iconbitmap('icon.ico')
        pass
    except:
        pass
    
    # 居中显示窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()