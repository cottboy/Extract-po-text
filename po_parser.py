#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO文件解析模块
用于解析.po文件，提取待翻译文本和生成翻译后的PO文件
"""

import polib
import os
import re
from typing import List, Tuple, Optional, Dict
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
        self.plural_entries_map = {}  # 存储复数条目的映射关系
    
    def _get_plural_count_from_po(self) -> int:
        """
        从PO文件头部信息获取复数形式数量
        
        Returns:
            int: 复数形式数量
        """
        if self.po_file and self.po_file.metadata:
            plural_forms = self.po_file.metadata.get('Plural-Forms', '')
            if plural_forms:
                # 从Plural-Forms中提取nplurals的值
                match = re.search(r'nplurals=(\d+)', plural_forms)
                if match:
                    return int(match.group(1))
        
        # 默认返回2（英语规则）
        return 2
    
    def _get_plural_count(self, language_code: str = None) -> int:
        """
        根据语言代码获取复数形式数量
        
        Args:
            language_code: 语言代码（如zh_CN, en_US等）
            
        Returns:
            int: 复数形式数量
        """
        if language_code and language_code in LANGUAGE_CONFIG:
            plural_forms = LANGUAGE_CONFIG[language_code]['plural_forms']
            # 从plural_forms中提取nplurals的值
            match = re.search(r'nplurals=(\d+)', plural_forms)
            if match:
                return int(match.group(1))
        
        # 默认返回2（英语规则）
        return 2
    
    def _normalize_plural_entries(self, language_code: str = None):
        """
        根据目标语言的复数规则，规范化所有复数条目，使其msgstr_plural的键数量与目标nplurals一致。
        - 如果当前条目的复数形式数量少于目标数量，则补齐，优先复用索引1（多数形式），否则复用索引0。
        - 如果多于目标数量，则截断多余的索引。
        - 同时确保复数条目不使用 entry.msgstr（置空）。
        - 特别处理 nplurals=1 的语言：若源文/复数形式包含格式化占位符(如 %s、%1$s、%d)，则确保 msgstr[0]
          也包含至少一个对应占位符。若 msgstr[0] 没有而 msgstr[1] 有，则用 msgstr[1] 覆盖 msgstr[0]。
        """
        if not self.po_file:
            return
        # 目标复数数量：优先使用language_code，否则从PO头读取
        target_plural_count = self._get_plural_count(language_code) if language_code else self._get_plural_count_from_po()
        # 防御：最少为1
        target_plural_count = max(1, target_plural_count)

        # 占位符检测（简化的printf风格：%s、%d，含或不含位置 %1$s/%2$d）
        placeholder_re = re.compile(r"%(?:\d+\$)?[sd]")
        def has_placeholder(s: str) -> bool:
            return bool(placeholder_re.search(s or ""))

        for entry in self.po_file:
            if entry.msgid_plural:
                # 确保是dict
                if not isinstance(entry.msgstr_plural, dict):
                    entry.msgstr_plural = {}
                # 置空单数msgstr
                entry.msgstr = ""

                if target_plural_count == 1:
                    # 对于仅一个复数形态的语言，确保最终 msgstr[0] 能满足参数占位符需求
                    s0 = (entry.msgstr_plural.get(0, "") or "").strip()
                    s1 = (entry.msgstr_plural.get(1, "") or "").strip()

                    # 源文是否需要占位符：看任一原文形态是否包含占位符
                    need_placeholder = has_placeholder(entry.msgid) or has_placeholder(entry.msgid_plural)

                    # 如果需要占位符而 s0 没有且 s1 有，占用 s1
                    if need_placeholder and not has_placeholder(s0) and has_placeholder(s1):
                        s0 = s1
                    # 如果 s0 为空但 s1 有内容，也用 s1 兜底
                    if not s0 and s1:
                        s0 = s1

                    entry.msgstr_plural = {0: s0}
                    continue

                # 其余 nplurals>=2 的情况维持补齐/截断逻辑
                base_zero = entry.msgstr_plural.get(0, '').strip()
                base_one = entry.msgstr_plural.get(1, base_zero).strip()
                for i in range(target_plural_count):
                    if i not in entry.msgstr_plural:
                        fill_val = base_one if base_one else base_zero
                        entry.msgstr_plural[i] = fill_val
                to_delete = [k for k in entry.msgstr_plural.keys() if k >= target_plural_count]
                for k in to_delete:
                    del entry.msgstr_plural[k]

    # ------- 通用占位符检测与修复 -------
    def _extract_placeholders(self, text: str) -> list:
        """提取各类占位符，覆盖以下家族：
        - printf/C: %s, %d, %1$s, %0.2f, %ld, %(name)s 等（排除 %%）
        - Qt: %1, %2, ...（排除 %%）
        - Python-brace/format: {0}, {name}, {0:.2f}
        返回占位符的原样token列表（去重保持顺序）。
        """
        if not text:
            return []
        tokens = []
        seen = set()
        # 1) printf/positional/named （排除 %%）
        printf_re = re.compile(r"%(?!%)(?:\d+\$|\([^)]+\))?[#0\- +]*(?:\*|\d+)?(?:\.(?:\*|\d+))?(?:hh|h|l|ll|j|z|t|L)?[diuoxXfFeEgGaAcspn]")
        # 2) Qt 风格 %1 %2 ... （排除 %%）
        qt_re = re.compile(r"%(?!%)(\d+)\b")
        # 3) Python brace
        brace_re = re.compile(r"\{(?:\w+|\d+)(?:[^{}]*)\}")
        for m in printf_re.finditer(text):
            tok = m.group(0)
            if tok not in seen:
                seen.add(tok)
                tokens.append(tok)
        for m in qt_re.finditer(text):
            tok = '%' + m.group(1)
            if tok not in seen:
                seen.add(tok)
                tokens.append(tok)
        for m in brace_re.finditer(text):
            tok = m.group(0)
            if tok not in seen:
                seen.add(tok)
                tokens.append(tok)
        return tokens

    def _ensure_placeholders_by_set(self, text: str, src_placeholders: list) -> str:
        """确保 text 中至少包含 src_placeholders 中的全部占位符；
        若缺失，则将缺失占位符以空格拼接的方式追加到文本末尾，尽量通过校验且不改变已有译文结构。
        """
        if text is None:
            text = ""
        tgt_tokens = set(self._extract_placeholders(text))
        src_tokens = [t for t in src_placeholders if t] if src_placeholders else []
        missing = [t for t in src_tokens if t not in tgt_tokens]
        if not missing:
            return text
        # 尽量与文本保持一个空格分隔
        sep = '' if (len(text) == 0 or text.endswith((' ', '\u3000'))) else ' '
        return f"{text}{sep}{' '.join(missing)}".rstrip()

    def _ensure_placeholders_all_entries(self):
        """对所有条目（含复数与非复数）执行占位符一致性修复。"""
        if not self.po_file:
            return
        for entry in self.po_file:
            # 源占位符合并：msgid 与 msgid_plural（若有）
            src_tokens = []
            src_tokens += self._extract_placeholders(entry.msgid or "")
            if getattr(entry, 'msgid_plural', None):
                src_tokens += self._extract_placeholders(entry.msgid_plural or "")
            # 去重，保持顺序
            seen = set()
            dedup_src = []
            for t in src_tokens:
                if t not in seen:
                    seen.add(t)
                    dedup_src.append(t)
            if getattr(entry, 'msgid_plural', None):
                # 针对每个复数形态修复（即便为空也不强制添加，以免把未翻译条目标为含占位符）
                if not isinstance(entry.msgstr_plural, dict):
                    entry.msgstr_plural = {}
                for idx in list(entry.msgstr_plural.keys()):
                    val = entry.msgstr_plural.get(idx, "")
                    if val.strip():
                        entry.msgstr_plural[idx] = self._ensure_placeholders_by_set(val, dedup_src)
            else:
                if entry.msgstr and entry.msgstr.strip():
                    entry.msgstr = self._ensure_placeholders_by_set(entry.msgstr, dedup_src)
    
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
            
            # 建立复数条目的映射关系
            self.plural_entries_map = {}
            for i, entry in enumerate(self.untranslated_entries):
                if hasattr(entry, 'msgid_plural') and entry.msgid_plural:
                    self.plural_entries_map[i] = {
                        'msgid': entry.msgid,
                        'msgid_plural': entry.msgid_plural,
                        'is_plural': True
                    }
                else:
                    self.plural_entries_map[i] = {
                        'msgid': entry.msgid,
                        'msgid_plural': None,
                        'is_plural': False
                    }
            
            return True
            
        except Exception as e:
            print(f"加载PO/POT文件失败: {e}")
            return False
    
    def get_untranslated_texts(self) -> List[str]:
        """
        获取所有待翻译的文本（包括复数形式，不带标记）
        
        Returns:
            List[str]: 待翻译文本列表
        """
        if not self.untranslated_entries:
            return []
        
        # 将条目内容序列化为单行：把内部换行替换为特殊占位符，避免导出后多行导致错位
        def _one_line(s: str) -> str:
            if s is None:
                return ""
            s = s.replace("\r\n", "\n").replace("\r", "\n")
            # 使用不容易被翻译的特殊占位符：<NEWLINE_PLACEHOLDER_114514>
            return s.replace("\n", "<NEWLINE_PLACEHOLDER_114514>")
        
        texts = []
        for i, entry in enumerate(self.untranslated_entries):
            if self.plural_entries_map[i]['is_plural']:
                # 复数条目：根据PO文件头部信息确定复数形式数量
                plural_count = self._get_plural_count_from_po()
                texts.append(_one_line(entry.msgid))  # 单数形式
                texts.append(_one_line(entry.msgid_plural))  # 复数形式
                
                # 如果需要更多复数形式，重复添加复数形式
                for _ in range(2, plural_count):
                    texts.append(_one_line(entry.msgid_plural))
            else:
                # 普通条目
                texts.append(_one_line(entry.msgid))
        
        return texts
    
    def get_translation_info(self) -> dict:
        """
        获取翻译信息统计
        
        Returns:
            dict: 包含总条目数、已翻译数、未翻译数的字典
        """
        if not self.po_file:
            return {"total": 0, "translated": 0, "untranslated": 0}
        
        total = 0
        translated = 0
        untranslated = 0
        
        for entry in self.po_file:
            if not entry.msgid.strip():  # 跳过空的header条目
                continue
            
            total += 1
            
            # 检查条目是否已翻译
            if hasattr(entry, 'msgid_plural') and entry.msgid_plural:
                # 复数条目：检查所有复数形式是否都有翻译
                if entry.msgstr_plural and any(msgstr.strip() for msgstr in entry.msgstr_plural.values()):
                    translated += 1
                else:
                    untranslated += 1
            else:
                # 普通条目：检查msgstr是否有翻译
                if entry.msgstr.strip():
                    translated += 1
                else:
                    untranslated += 1
        
        return {
            "total": total,
            "translated": translated,
            "untranslated": untranslated
        }
    
    def export_untranslated_to_txt(self, output_path: str) -> bool:
        """
        将待翻译文本导出到TXT文件（支持动态复数形式，不带标记）
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 导出成功返回True，失败返回False
        """
        try:
            if not self.untranslated_entries:
                print("没有待翻译的文本")
                return False
            
            # 将条目内容序列化为单行：把内部换行替换为可见的\n，避免导出后多行导致错位
            def _one_line(s: str) -> str:
                if s is None:
                    return ""
                s = s.replace("\r\n", "\n").replace("\r", "\n")
                return s.replace("\n", "\\n")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                line_number = 1
                for i, entry in enumerate(self.untranslated_entries):
                    if self.plural_entries_map[i]['is_plural']:
                        # 复数条目：根据PO文件头部信息确定复数形式数量
                        plural_count = self._get_plural_count_from_po()
                        
                        # 导出单数形式
                        f.write(f"{line_number}. {_one_line(entry.msgid)}\n")
                        line_number += 1
                        
                        # 导出复数形式
                        f.write(f"{line_number}. {_one_line(entry.msgid_plural)}\n")
                        line_number += 1
                        
                        # 如果需要更多复数形式，重复导出复数形式
                        for _ in range(2, plural_count):
                            f.write(f"{line_number}. {_one_line(entry.msgid_plural)}\n")
                            line_number += 1
                    else:
                        # 普通条目
                        f.write(f"{line_number}. {_one_line(entry.msgid)}\n")
                        line_number += 1
            
            total_lines = line_number - 1
            print(f"成功导出 {len(self.untranslated_entries)} 条待翻译条目（共 {total_lines} 行文本）到: {output_path}")
            return True
            
        except Exception as e:
            print(f"导出文本失败: {e}")
            return False
    
    def _parse_translations(self, translations: list) -> list:
        """
        解析翻译文本，根据位置识别复数形式
        
        Args:
            translations: 翻译文本行列表
            
        Returns:
            list: 解析后的翻译数据列表
        """
        parsed_data = []
        translation_index = 0
        
        for entry_index, entry in enumerate(self.untranslated_entries):
            # 去掉行号前缀，并将可视化换行(\\n)还原为真实换行
            def clean_line(line):
                line_number_match = re.match(r'^\s*(\d+)\. ', line)
                if line_number_match:
                    line = line[len(line_number_match.group(0)):]
                # 还原导出时的可视化换行
                return line.replace('\\n', '\n')
            
            if self.plural_entries_map[entry_index]['is_plural']:
                # 复数条目：需要读取多行
                plural_count = self._get_plural_count_from_po()
                
                if translation_index + plural_count > len(translations):
                    print(f"[DEBUG _parse_translations] plural need {plural_count}, have from {translation_index} to {len(translations)} for entry {entry_index+1}")
                    raise ValueError(f"复数条目 {entry_index+1} 需要 {plural_count} 行翻译，但剩余翻译行数不足")
                
                # 读取所有复数形式
                plural_forms = {}
                for i in range(plural_count):
                    form_text = clean_line(translations[translation_index + i])
                    plural_forms[i] = form_text
                
                # 为了保持向后兼容，仍然提供singular和plural字段
                parsed_data.append({
                    'singular': plural_forms.get(0, ''),
                    'plural': plural_forms.get(1, plural_forms.get(0, '')),
                    'plural_forms': plural_forms
                })
                
                translation_index += plural_count
            else:
                # 普通条目：读取一行
                if translation_index >= len(translations):
                    print(f"[DEBUG _parse_translations] ordinary entry_index={entry_index+1}, translation_index={translation_index}, len(translations)={len(translations)}")
                    raise ValueError(f"普通条目 {entry_index+1} 缺少翻译文本")
                
                text = clean_line(translations[translation_index])
                parsed_data.append({
                    'text': text
                })
                
                translation_index += 1
        
        return parsed_data
    
    def import_translations_from_txt(self, txt_path: str, language_code: str = None) -> bool:
        """
        从TXT文件导入翻译结果（支持动态复数形式）
        
        Args:
            txt_path: 翻译文本文件路径
            language_code: 目标语言代码，用于确定复数形式数量
            
        Returns:
            bool: 导入成功返回True，失败返回False
        """
        try:
            if not os.path.exists(txt_path):
                raise FileNotFoundError(f"翻译文件不存在: {txt_path}")
            
            with open(txt_path, 'r', encoding='utf-8') as f:
                # 使用splitlines()仅去掉行尾换行，保留前后空白，避免丢失前导\n语义
                lines = f.read().splitlines()
            print(f"[import] read {len(lines)} lines from {txt_path}")
            if lines:
                print(f"[import] first line preview: {lines[0][:60]}")
            
            # 先尝试按“导出格式（带行号）”解析
            numbered_translations = [line for line in lines if re.match(r'^\s*\d+\. ', line)]
            print(f"[import] numbered_translations count = {len(numbered_translations)}")
            parsed_translations = None
            
            if len(numbered_translations) > 0:
                print("[import] mode = numbered")
                # 使用导出格式解析（支持可视化换行的还原）
                parsed_translations = self._parse_translations(numbered_translations)
            else:
                # 兼容“每行一条”的简单格式（无行号、无可视化换行）
                simple_lines = lines[:]  # 保留原始顺序
                # 优先尝试保留空行（某些翻译可能允许为空）
                parsed_simple = []
                idx = 0
                plural_count = self._get_plural_count(language_code) if language_code else self._get_plural_count_from_po()
                print(f"[import] entries={len(self.untranslated_entries)}, plural_count={plural_count}, simple_lines={len(simple_lines)}")
                for i, entry in enumerate(self.untranslated_entries):
                    if self.plural_entries_map[i]['is_plural']:
                        # 需要 plural_count 行
                        if idx + plural_count > len(simple_lines):
                            print(f"[DEBUG simple] plural entry {i+1} need {plural_count}, idx={idx}, simple_lines={len(simple_lines)}")
                            raise ValueError(f"复数条目 {i+1} 需要 {plural_count} 行翻译，但剩余翻译行数不足")
                        plural_forms = {}
                        for j in range(plural_count):
                            plural_forms[j] = simple_lines[idx + j]
                        parsed_simple.append({
                            'singular': plural_forms.get(0, ''),
                            'plural': plural_forms.get(1, plural_forms.get(0, '')),
                            'plural_forms': plural_forms
                        })
                        idx += plural_count
                    else:
                        if idx >= len(simple_lines):
                            # 尝试过滤掉完全空白的行再重试一次
                            filtered_lines = [ln for ln in simple_lines if ln.strip() != '']
                            print(f"[DEBUG simple] ordinary i={i+1}, idx={idx}, len(simple_lines)={len(simple_lines)}, len(filtered_lines)={len(filtered_lines)}")
                            if len(filtered_lines) != len(simple_lines):
                                # 重新用过滤后的行进行一次整体解析
                                simple_lines = filtered_lines
                                if idx >= len(simple_lines):
                                    raise ValueError(f"普通条目 {i+1} 缺少翻译文本")
                            else:
                                raise ValueError(f"普通条目 {i+1} 缺少翻译文本")
                        parsed_simple.append({'text': simple_lines[idx]})
                        idx += 1
                parsed_translations = parsed_simple
            
            # 验证翻译条目数量
            if len(parsed_translations) != len(self.untranslated_entries):
                print(f"翻译条目数量不匹配: 期望 {len(self.untranslated_entries)} 条，实际 {len(parsed_translations)} 条。建议使用程序导出的TXT格式进行翻译（带编号），以确保复杂多行/复数条目能够被正确解析。）")
                return False
            
            # 获取目标语言的复数形式数量（优先使用语言代码，其次使用PO文件头部信息）
            plural_count = self._get_plural_count(language_code) if language_code else self._get_plural_count_from_po()
            
            # 将翻译结果应用到PO条目
            for i, translation_data in enumerate(parsed_translations):
                entry = self.untranslated_entries[i]
                
                if self.plural_entries_map[i]['is_plural']:
                    # 复数条目处理
                    if 'plural_forms' in translation_data:
                        # 使用新的plural_forms数据结构
                        entry.msgstr_plural = {}
                        for form_index, form_text in translation_data['plural_forms'].items():
                            entry.msgstr_plural[form_index] = form_text
                        
                        # 清空单数msgstr（复数条目不使用msgstr）
                        entry.msgstr = ''
                    else:
                        # 兼容旧结构
                        entry.msgstr_plural = {
                            0: translation_data.get('singular', ''),
                            1: translation_data.get('plural', translation_data.get('singular', ''))
                        }
                        entry.msgstr = ''
                else:
                    # 普通条目
                    entry.msgstr = translation_data.get('text', '')
            
            # 对齐首尾换行数量以避免Poedit错误
            self._align_newline_parity()
            
            # 规范化复数形式等
            self._normalize_plural_entries(language_code)
            
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
            
            # 规范化复数形式（根据目标语言）
            self._normalize_plural_entries(language_code)
            
            # 占位符一致性修复（所有语言、所有占位符家族）
            self._ensure_placeholders_all_entries()

            # 对齐换行：确保msgid与msgstr(含复数)在首尾\n数量一致，避免Poedit报错
            self._align_newline_parity()
            
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

    def _align_newline_parity(self):
        """确保所有条目在首尾换行数量上与源文本一致，避免Poedit关于\n不一致的报错。"""
        def count_leading_newlines(s: str) -> int:
            if not s:
                return 0
            c = 0
            for ch in s:
                if ch == '\n':
                    c += 1
                else:
                    break
            return c
        
        def count_trailing_newlines(s: str) -> int:
            if not s:
                return 0
            c = 0
            for ch in reversed(s):
                if ch == '\n':
                    c += 1
                else:
                    break
            return c
        
        def align(target: str, base: str) -> str:
            if target is None or target == "":
                return target
            # 领先换行
            tl, bl = count_leading_newlines(target), count_leading_newlines(base)
            if tl < bl:
                target = ('\n' * (bl - tl)) + target
            elif tl > bl:
                # 去掉多余的前导\n
                target = target[tl - bl:]
            # 结尾换行
            tt, bt = count_trailing_newlines(target), count_trailing_newlines(base)
            if tt < bt:
                target = target + ('\n' * (bt - tt))
            elif tt > bt:
                # 去掉多余的尾部\n
                target = target[:len(target) - (tt - bt)]
            return target
        
        for entry in self.po_file:
            if getattr(entry, 'obsolete', False):
                continue
            # 普通
            if not getattr(entry, 'msgid_plural', None):
                if entry.msgstr:
                    entry.msgstr = align(entry.msgstr, entry.msgid)
            else:
                # 复数：与对应的msgid/msgid_plural对齐
                if entry.msgstr_plural:
                    new_plural = {}
                    for idx, val in entry.msgstr_plural.items():
                        base = entry.msgid if int(idx) == 0 else entry.msgid_plural
                        new_plural[idx] = align(val, base)
                    entry.msgstr_plural = new_plural


    def _update_metadata(self, language_code: str = None):
        """更新PO文件元数据：语言、Plural-Forms、编码、修订时间等。"""
        if not getattr(self, 'po_file', None):
            return
        try:
            po = self.po_file
            md = dict(po.metadata or {})

            # 语言与复数规则
            if language_code:
                md['Language'] = language_code
                cfg = LANGUAGE_CONFIG.get(language_code)
                if cfg and cfg.get('plural_forms'):
                    md['Plural-Forms'] = cfg['plural_forms']

            # 编码与MIME
            content_type = md.get('Content-Type', '')
            if 'charset=' not in content_type.lower():
                md['Content-Type'] = 'text/plain; charset=UTF-8'
            md['Content-Transfer-Encoding'] = '8bit'
            md['MIME-Version'] = '1.0'

            # 修订时间（UTC）
            md['PO-Revision-Date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M%z')

            po.metadata = md
        except Exception as e:
            print(f"更新元数据失败: {e}")

    # 清理保存后第一行可能出现的孤立"#"行，避免某些工具不兼容
    def _remove_single_hash_line(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if lines and lines[0].strip() == '#':
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    f.writelines(lines[1:])
                print('已移除文件首行孤立的 # 符号')
        except Exception as e:
            print(f"清理文件首行#失败: {e}")


if __name__ == "__main__":
    # 测试代码
    parser = POParser()
    print("PO文件解析模块测试")
    print("使用方法:")
    print("1. parser.load_po_file('input.po')")
    print("2. parser.export_untranslated_to_txt('untranslated.txt')")
    print("3. parser.import_translations_from_txt('translated.txt')")
    print("4. parser.save_translated_po('output.po', 'zh_CN')")