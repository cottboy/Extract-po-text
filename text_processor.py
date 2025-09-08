#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理模块
提供文本导出和导入的高级功能
"""

import os
import re
from typing import List, Dict, Tuple, Optional


class TextProcessor:
    """文本处理器"""
    
    def __init__(self):
        self.export_format = "numbered"  # numbered, plain, json
        self.import_format = "auto"      # auto, numbered, plain
    
    def set_export_format(self, format_type: str):
        """
        设置导出格式
        
        Args:
            format_type: 格式类型 (numbered, plain, json)
        """
        if format_type in ["numbered", "plain", "json"]:
            self.export_format = format_type
        else:
            raise ValueError("不支持的导出格式")
    
    def export_texts_to_file(self, texts: List[str], output_path: str, 
                           add_context: bool = False) -> bool:
        """
        将文本列表导出到文件
        
        Args:
            texts: 文本列表
            output_path: 输出文件路径
            add_context: 是否添加上下文信息
            
        Returns:
            bool: 导出成功返回True
        """
        try:
            if not texts:
                print("没有文本需要导出")
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                if self.export_format == "numbered":
                    self._export_numbered_format(f, texts, add_context)
                elif self.export_format == "plain":
                    self._export_plain_format(f, texts)
                elif self.export_format == "json":
                    self._export_json_format(f, texts)
            
            print(f"成功导出 {len(texts)} 条文本到: {output_path}")
            return True
            
        except Exception as e:
            print(f"导出文本失败: {e}")
            return False
    
    def _export_numbered_format(self, file, texts: List[str], add_context: bool):
        """导出带编号格式"""
        if add_context:
            file.write("# PO文件待翻译文本\n")
            file.write("# 请保持编号格式，只翻译文本内容\n")
            file.write("# 格式: 编号. 原文\n\n")
        
        for i, text in enumerate(texts, 1):
            file.write(f"{i}. {text}\n")
    
    def _export_plain_format(self, file, texts: List[str]):
        """导出纯文本格式"""
        for i, text in enumerate(texts):
            if i == len(texts) - 1:  # 最后一行不加换行符
                file.write(text)
            else:
                file.write(f"{text}\n")
    
    def _export_json_format(self, file, texts: List[str]):
        """导出JSON格式"""
        import json
        data = {
            "texts": texts,
            "count": len(texts),
            "format": "po_translation"
        }
        json.dump(data, file, ensure_ascii=False, indent=2)
    
    def import_texts_from_file(self, file_path: str) -> List[str]:
        """
        从文件导入翻译文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[str]: 翻译文本列表
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 自动检测格式
            if self.import_format == "auto":
                return self._auto_detect_and_parse(content)
            elif self.import_format == "numbered":
                return self._parse_numbered_format(content)
            elif self.import_format == "plain":
                return self._parse_plain_format(content)
            
        except Exception as e:
            print(f"导入文本失败: {e}")
            return []
    
    def _auto_detect_and_parse(self, content: str) -> List[str]:
        """自动检测格式并解析"""
        # 检测是否为JSON格式
        if content.strip().startswith('{'):
            try:
                import json
                data = json.loads(content)
                if isinstance(data, dict) and 'texts' in data:
                    return data['texts']
            except:
                pass
        
        # 检测是否为编号格式
        lines = content.strip().split('\n')
        numbered_pattern = re.compile(r'^\d+\.\s*(.+)$')
        
        numbered_matches = 0
        for line in lines:
            if line.strip() and not line.startswith('#'):
                if numbered_pattern.match(line.strip()):
                    numbered_matches += 1
        
        # 如果大部分行都是编号格式，则按编号格式解析
        non_comment_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        if non_comment_lines and numbered_matches / len(non_comment_lines) > 0.7:
            return self._parse_numbered_format(content)
        else:
            return self._parse_plain_format(content)
    
    def _parse_numbered_format(self, content: str) -> List[str]:
        """解析编号格式"""
        lines = content.strip().split('\n')
        texts = []
        numbered_pattern = re.compile(r'^\d+\.\s*(.+)$')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = numbered_pattern.match(line)
            if match:
                texts.append(match.group(1))
            else:
                # 如果不匹配编号格式，可能是多行文本的续行
                if texts:
                    texts[-1] += ' ' + line
        
        return texts
    
    def _parse_plain_format(self, content: str) -> List[str]:
        """解析纯文本格式"""
        lines = content.strip().split('\n')
        texts = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                texts.append(line)
        
        return texts
    
    def validate_translation_count(self, original_count: int, 
                                 translated_texts: List[str]) -> Tuple[bool, str]:
        """
        验证翻译文本数量
        
        Args:
            original_count: 原文数量
            translated_texts: 翻译文本列表
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if len(translated_texts) == original_count:
            return True, "验证通过"
        elif len(translated_texts) < original_count:
            return False, f"翻译文本不足: 需要 {original_count} 条，实际 {len(translated_texts)} 条"
        else:
            return False, f"翻译文本过多: 需要 {original_count} 条，实际 {len(translated_texts)} 条"
    
    def clean_text(self, text: str) -> str:
        """
        清理文本，去除多余的空白字符
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        # 去除首尾空白
        text = text.strip()
        
        # 将多个连续空白字符替换为单个空格
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def split_long_texts(self, texts: List[str], max_length: int = 1000) -> List[str]:
        """
        分割过长的文本
        
        Args:
            texts: 文本列表
            max_length: 最大长度
            
        Returns:
            List[str]: 分割后的文本列表
        """
        result = []
        
        for text in texts:
            if len(text) <= max_length:
                result.append(text)
            else:
                # 按句子分割长文本
                sentences = re.split(r'[.!?。！？]', text)
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk + sentence) <= max_length:
                        current_chunk += sentence
                    else:
                        if current_chunk:
                            result.append(current_chunk.strip())
                        current_chunk = sentence
                
                if current_chunk:
                    result.append(current_chunk.strip())
        
        return result


if __name__ == "__main__":
    # 测试代码
    processor = TextProcessor()
    print("文本处理模块测试")
    
    # 测试文本
    test_texts = [
        "Hello, world!",
        "This is a test message.",
        "Welcome to the application."
    ]
    
    # 测试导出
    processor.export_texts_to_file(test_texts, "test_export.txt", add_context=True)
    
    # 测试导入
    imported_texts = processor.import_texts_from_file("test_export.txt")
    print(f"导入的文本: {imported_texts}")
    
    # 清理测试文件
    if os.path.exists("test_export.txt"):
        os.remove("test_export.txt")