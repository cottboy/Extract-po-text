#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO文件解析模块
用于解析.po文件，提取待翻译文本和生成翻译后的PO文件
"""

import polib
import os
from typing import List, Tuple, Optional
from datetime import datetime, timezone


# 语言配置映射 - 包含复数形式规则
LANGUAGE_CONFIG = {
    'zh_CN': {
        'name': '简体中文',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'zh_TW': {
        'name': '繁体中文',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'en_US': {
        'name': 'English (United States)',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'en_GB': {
        'name': 'English (United Kingdom)',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'es_ES': {
        'name': 'Español (España)',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'fr_FR': {
        'name': 'Français (France)',
        'plural_forms': 'nplurals=2; plural=(n > 1);'
    },
    'de_DE': {
        'name': 'Deutsch (Deutschland)',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ja_JP': {
        'name': '日本語',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ko_KR': {
        'name': '한국어',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ru_RU': {
        'name': 'Русский',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'ar_SA': {
        'name': 'العربية',
        'plural_forms': 'nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);'
    },
    'pt_BR': {
        'name': 'Português (Brasil)',
        'plural_forms': 'nplurals=2; plural=(n > 1);'
    },
    'it_IT': {
        'name': 'Italiano',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'nl_NL': {
        'name': 'Nederlands',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'pl_PL': {
        'name': 'Polski',
        'plural_forms': 'nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'cs_CZ': {
        'name': 'Čeština',
        'plural_forms': 'nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;'
    },
    'sk_SK': {
        'name': 'Slovenčina',
        'plural_forms': 'nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;'
    },
    'hr_HR': {
        'name': 'Hrvatski',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'sr_RS': {
        'name': 'Српски',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'bg_BG': {
        'name': 'Български',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ro_RO': {
        'name': 'Română',
        'plural_forms': 'nplurals=3; plural=(n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2);'
    },
    'uk_UA': {
        'name': 'Українська',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'lt_LT': {
        'name': 'Lietuvių',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'lv_LV': {
        'name': 'Latviešu',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2);'
    },
    'fi_FI': {
        'name': 'Suomi',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'sv_SE': {
        'name': 'Svenska',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'no_NO': {
        'name': 'Norsk',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'da_DK': {
        'name': 'Dansk',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'hu_HU': {
        'name': 'Magyar',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'tr_TR': {
        'name': 'Türkçe',
        'plural_forms': 'nplurals=2; plural=(n > 1);'
    },
    'vi_VN': {
        'name': 'Tiếng Việt',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'he_IL': {
        'name': 'עברית',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'el_GR': {
        'name': 'Ελληνικά',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'et_EE': {
        'name': 'Eesti',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'sl_SI': {
        'name': 'Slovenščina',
        'plural_forms': 'nplurals=4; plural=(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3);'
    },
    'is_IS': {
        'name': 'Íslenska',
        'plural_forms': 'nplurals=2; plural=(n%10!=1 || n%100==11);'
    },
    'cy_GB': {
        'name': 'Cymraeg',
        'plural_forms': 'nplurals=4; plural=(n==1) ? 0 : (n==2) ? 1 : (n != 8 && n != 11) ? 2 : 3;'
    },
    'eu_ES': {
        'name': 'Euskera',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ca_ES': {
        'name': 'Català',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'gl_ES': {
        'name': 'Galego',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'th_TH': {
        'name': 'ไทย',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'id_ID': {
        'name': 'Bahasa Indonesia',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ms_MY': {
        'name': 'Bahasa Melayu',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'sw_KE': {
        'name': 'Kiswahili',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'am_ET': {
        'name': 'አማርኛ',
        'plural_forms': 'nplurals=2; plural=(n > 1);'
    },
    'hi_IN': {
        'name': 'हिन्दी',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'bn_BD': {
        'name': 'বাংলা',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ur_PK': {
        'name': 'اردو',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'fa_IR': {
        'name': 'فارسی',
        'plural_forms': 'nplurals=2; plural=(n > 1);'
    },
    'nn_NO': {
        'name': 'Nynorsk',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ga_IE': {
        'name': 'Gaeilge',
        'plural_forms': 'nplurals=5; plural=n==1 ? 0 : n==2 ? 1 : (n>2 && n<7) ? 2 :(n>6 && n<11) ? 3 : 4;'
    },
    'gd_GB': {
        'name': 'Gàidhlig',
        'plural_forms': 'nplurals=4; plural=(n==1 || n==11) ? 0 : (n==2 || n==12) ? 1 : (n > 2 && n < 20) ? 2 : 3;'
    },
    'mt_MT': {
        'name': 'Malti',
        'plural_forms': 'nplurals=4; plural=(n==1) ? 0 : (n==0 || (n%100 > 1 && n%100 < 11)) ? 1 : (n%100 > 10 && n%100 < 20) ? 2 : 3;'
    },
    'eo': {
        'name': 'Esperanto',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'af_ZA': {
        'name': 'Afrikaans',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ta_IN': {
        'name': 'தமிழ்',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'te_IN': {
        'name': 'తెలుగు',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'gu_IN': {
        'name': 'ગુજરાતી',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'pa_IN': {
        'name': 'ਪੰਜਾਬੀ',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'mr_IN': {
        'name': 'मराठी',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'kn_IN': {
        'name': 'ಕನ್ನಡ',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'ml_IN': {
        'name': 'മലയാളം',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'si_LK': {
        'name': 'සිංහල',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'my_MM': {
        'name': 'မြန်မာ',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'km_KH': {
        'name': 'ខ្មែរ',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'lo_LA': {
        'name': 'ລາວ',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ka_GE': {
        'name': 'ქართული',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'hy_AM': {
        'name': 'Հայերեն',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'az_AZ': {
        'name': 'Azərbaycan',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'kk_KZ': {
        'name': 'Қазақ',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'uz_UZ': {
        'name': 'Oʻzbek',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'mn_MN': {
        'name': 'Монгол',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'bo_CN': {
        'name': 'བོད་ཡིག',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ug_CN': {
        'name': 'ئۇيغۇرچە',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ne_NP': {
        'name': 'नेपाली',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'mg_MG': {
        'name': 'Malagasy',
        'plural_forms': 'nplurals=2; plural=(n > 1);'
    },
    'ha_NG': {
        'name': 'Hausa',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'yo_NG': {
        'name': 'Yorùbá',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'ig_NG': {
        'name': 'Igbo',
        'plural_forms': 'nplurals=1; plural=0;'
    },
    'zu_ZA': {
        'name': 'isiZulu',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'xh_ZA': {
        'name': 'isiXhosa',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'la': {
        'name': 'Latina',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'sa_IN': {
        'name': 'संस्कृतम्',
        'plural_forms': 'nplurals=3; plural=(n==1) ? 0 : (n==2) ? 1 : 2;'
    },
    'sr_Latn_RS': {
        'name': 'Srpski (latinica)',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'bs_BA': {
        'name': 'Bosanski',
        'plural_forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
    },
    'sq_AL': {
        'name': 'Shqip',
        'plural_forms': 'nplurals=2; plural=(n != 1);'
    },
    'mk_MK': {
        'name': 'Македонски',
        'plural_forms': 'nplurals=2; plural=(n==1 || n%10==1 ? 0 : 1);'
    }
}


class POParser:
    """PO文件解析器"""
    
    def __init__(self):
        self.po_file = None
        self.untranslated_entries = []
        self.all_entries = []
    
    def load_po_file(self, file_path: str) -> bool:
        """
        加载PO或POT文件
        
        Args:
            file_path: PO或POT文件路径
            
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            self.po_file = polib.pofile(file_path)
            self.all_entries = list(self.po_file)
            
            # 提取所有待翻译的条目（除了空的header条目）
            self.untranslated_entries = [
                entry for entry in self.po_file 
                if entry.msgid.strip()  # 只要msgid不为空就提取
            ]
            
            return True
            
        except Exception as e:
            print(f"加载PO/POT文件失败: {e}")
            return False
    
    def get_untranslated_texts(self) -> List[str]:
        """
        获取所有待翻译的文本
        
        Returns:
            List[str]: 待翻译文本列表
        """
        if not self.untranslated_entries:
            return []
        
        return [entry.msgid for entry in self.untranslated_entries]
    
    def get_translation_info(self) -> dict:
        """
        获取翻译信息统计
        
        Returns:
            dict: 包含总条目数、已翻译数、未翻译数的字典
        """
        if not self.po_file:
            return {"total": 0, "translated": 0, "untranslated": 0}
        
        total = len([entry for entry in self.po_file if entry.msgid.strip()])
        untranslated = len(self.untranslated_entries)
        translated = total - untranslated
        
        return {
            "total": total,
            "translated": translated,
            "untranslated": untranslated
        }
    
    def export_untranslated_to_txt(self, output_path: str) -> bool:
        """
        将待翻译文本导出到TXT文件
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 导出成功返回True，失败返回False
        """
        try:
            if not self.untranslated_entries:
                print("没有待翻译的文本")
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(self.untranslated_entries, 1):
                    # 写入行号和原文，方便后续匹配
                    f.write(f"{i}. {entry.msgid}\n")
            
            print(f"成功导出 {len(self.untranslated_entries)} 条待翻译文本到: {output_path}")
            return True
            
        except Exception as e:
            print(f"导出文本失败: {e}")
            return False
    
    def import_translations_from_txt(self, txt_path: str) -> bool:
        """
        从TXT文件导入翻译结果
        
        Args:
            txt_path: 翻译文本文件路径
            
        Returns:
            bool: 导入成功返回True，失败返回False
        """
        try:
            if not os.path.exists(txt_path):
                raise FileNotFoundError(f"翻译文件不存在: {txt_path}")
            
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 清理空行和去除换行符
            translations = [line.strip() for line in lines if line.strip()]
            
            if len(translations) != len(self.untranslated_entries):
                print(f"翻译条目数量不匹配: 期望 {len(self.untranslated_entries)} 条，实际 {len(translations)} 条")
                return False
            
            # 将翻译结果应用到PO条目
            for i, translation in enumerate(translations):
                # 去掉行号前缀（如果存在）
                if translation.startswith(f"{i+1}. "):
                    translation = translation[len(f"{i+1}. "):]
                
                self.untranslated_entries[i].msgstr = translation
            
            print(f"成功导入 {len(translations)} 条翻译")
            return True
            
        except Exception as e:
            print(f"导入翻译失败: {e}")
            return False
    
    def save_translated_po(self, output_path: str, language_code: str = None) -> bool:
        """
        保存翻译后的PO文件
        
        Args:
            output_path: 输出PO文件路径
            language_code: 语言代码（如zh_CN, en_US等）
            
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            if not self.po_file:
                print("没有加载PO文件")
                return False
            
            # 更新元数据
            self._update_metadata(language_code)
            
            # 保存文件
            self.po_file.save(output_path)
            
            # 后处理：删除第一行单独的"#"符号
            self._remove_single_hash_line(output_path)
            
            # 统计翻译信息
            info = self.get_translation_info()
            print(f"成功保存翻译后的PO文件到: {output_path}")
            print(f"翻译统计: 总计 {info['total']} 条，已翻译 {info['translated']} 条，未翻译 {info['untranslated']} 条")
            
            return True
            
        except Exception as e:
            print(f"保存PO文件失败: {e}")
            return False
    
    def _update_metadata(self, language_code: str = None):
        """
        更新PO文件元数据
        
        Args:
            language_code: 语言代码（如zh_CN, en_US等）
        """
        # 更新最后修改时间（使用当前时区）
        current_time = datetime.now().astimezone()
        self.po_file.metadata['PO-Revision-Date'] = current_time.strftime('%Y-%m-%d %H:%M%z')
        
        # 更新生成工具信息
        self.po_file.metadata['X-Generator'] = 'Extract-po-text'
        
        # 设置语言相关信息
        if language_code:
            self.po_file.metadata['Language'] = language_code
            
            # 从配置中获取语言信息
            if language_code in LANGUAGE_CONFIG:
                config = LANGUAGE_CONFIG[language_code]
                
                # 设置复数形式规则
                self.po_file.metadata['Plural-Forms'] = config['plural_forms']
                
                # 更新语言团队信息（如果不存在）
                if 'Language-Team' not in self.po_file.metadata:
                    self.po_file.metadata['Language-Team'] = f"{config['name']} <team@example.com>"
            else:
                # 如果语言代码不在配置中，使用默认设置
                if 'Language-Team' not in self.po_file.metadata:
                    self.po_file.metadata['Language-Team'] = f"{language_code} <team@example.com>"
                
                # 默认复数形式（英语规则）
                self.po_file.metadata['Plural-Forms'] = 'nplurals=2; plural=(n != 1);'
        
        # 确保必要的元数据存在（仅在不存在时添加，保留现有值）
        if 'MIME-Version' not in self.po_file.metadata:
            self.po_file.metadata['MIME-Version'] = '1.0'
        if 'Content-Type' not in self.po_file.metadata:
            self.po_file.metadata['Content-Type'] = 'text/plain; charset=UTF-8'
        if 'Content-Transfer-Encoding' not in self.po_file.metadata:
            self.po_file.metadata['Content-Transfer-Encoding'] = '8bit'
    
    def _remove_single_hash_line(self, file_path: str):
        """
        删除文件第一行单独的"#"符号
        
        Args:
            file_path: PO文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 检查第一行是否只有单独的"#"符号
            if lines and lines[0].strip() == '#':
                # 删除第一行
                lines = lines[1:]
                
                # 重写文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
                print(f"已删除文件第一行的单独'#'符号: {file_path}")
                
        except Exception as e:
            print(f"处理文件第一行'#'符号时出错: {e}")


if __name__ == "__main__":
    # 测试代码
    parser = POParser()
    print("PO文件解析模块测试")
    print("使用方法:")
    print("1. parser.load_po_file('input.po')")
    print("2. parser.export_untranslated_to_txt('untranslated.txt')")
    print("3. parser.import_translations_from_txt('translated.txt')")
    print("4. parser.save_translated_po('output.po', 'zh_CN')")