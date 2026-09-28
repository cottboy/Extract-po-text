"""Tkinter 图形界面。

外观走 Windows 原生的 ttk vista 主题，非 Windows 平台保持各系统默认主题。
所有耗时操作都在工作线程里跑，结果经队列回传，主线程轮询后再弹窗与刷新日志——
Tk 的组件与对话框都不能从子线程调用。
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable

from .exceptions import PoTextError
from .service import Session
from .workbook import ApplyReport, ExtractReport, Options

PO_TYPES = [("PO/POT 文件", "*.po *.pot"), ("PO 文件", "*.po"), ("POT 文件", "*.pot"), ("所有文件", "*.*")]
TXT_TYPES = [("文本文件", "*.txt"), ("所有文件", "*.*")]
POLL_MS = 120
UI_FONT = "Microsoft YaHei UI"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PO 文件批量翻译工具")
        self.minsize(560, 520)
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._busy = False
        self._build()
        # vista 主题的控件比 clam 高，写死尺寸会把日志区挤出窗口，改为按布局实际请求的大小开窗
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{min(self.winfo_reqheight(), self.winfo_screenheight() - 60)}")
        self.after(POLL_MS, self._poll)

    # ------- 界面 -------

    def _build(self) -> None:
        style = ttk.Style(self)
        # vista 是 Windows 的原生外观；clam 是跨平台的复古扁平主题，在这上面显旧
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure(".", font=(UI_FONT, 9))
        style.configure("Title.TLabel", font=(UI_FONT, 11, "bold"))

        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        for row in (2, 3, 4, 5):
            root.rowconfigure(row, weight=0)
        root.rowconfigure(6, weight=1)

        ttk.Label(root, text="导出全部待翻译文本，翻译完再整体回填", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(root, text="提示：翻译文档一行对应一条待翻译内容，翻译时不要增删行；原文里的换行以 \\n 形式保留。").grid(row=1, column=0, sticky="w", pady=(2, 10))

        source = ttk.LabelFrame(root, text="第一步：选择 PO / POT 文件", padding=8)
        source.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        source.columnconfigure(1, weight=1)
        self.po_path = tk.StringVar()
        ttk.Entry(source, textvariable=self.po_path, state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(source, text="浏览…", command=self._browse_po).grid(row=0, column=2)

        export = ttk.LabelFrame(root, text="第二步：导出待翻译文本", padding=8)
        export.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        export.columnconfigure(1, weight=1)
        self.export_path = tk.StringVar()
        ttk.Label(export, text="输出文件:").grid(row=0, column=0, sticky="w")
        ttk.Entry(export, textvariable=self.export_path).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(export, text="另存为…", command=self._browse_export).grid(row=0, column=2)
        self.include_all = tk.BooleanVar(value=False)
        self.include_fuzzy = tk.BooleanVar(value=False)
        ttk.Checkbutton(export, text="导出全部条目（会覆盖已有译文）", variable=self.include_all).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Checkbutton(export, text="把 fuzzy（需复核）条目也当作待翻译", variable=self.include_fuzzy).grid(row=2, column=0, columnspan=3, sticky="w")

        options = ttk.LabelFrame(root, text="目标语言与复数形式", padding=8)
        options.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        options.columnconfigure(1, weight=1)
        self.target_lang = tk.StringVar(value="zh_CN")
        self.plural_forms = tk.StringVar()
        ttk.Label(options, text="语言代码:").grid(row=0, column=0, sticky="w")
        ttk.Entry(options, textvariable=self.target_lang, width=14).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(options, text="复数声明(可留空):").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(options, textvariable=self.plural_forms).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=(6, 0))
        ttk.Label(options, text="留空则按语言代码查内置规则，再退回 PO 头部的 Plural-Forms").grid(row=2, column=0, columnspan=3, sticky="w")

        back = ttk.LabelFrame(root, text="第三步：回填并生成 PO", padding=8)
        back.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        back.columnconfigure(1, weight=1)
        self.import_path = tk.StringVar()
        self.output_path = tk.StringVar()
        ttk.Label(back, text="翻译文档:").grid(row=0, column=0, sticky="w")
        ttk.Entry(back, textvariable=self.import_path, state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(back, text="浏览…", command=self._browse_import).grid(row=0, column=2)
        ttk.Label(back, text="输出 PO:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(back, textvariable=self.output_path).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(6, 0))
        ttk.Button(back, text="另存为…", command=self._browse_output).grid(row=1, column=2, pady=(6, 0))
        self.align_newlines = tk.BooleanVar(value=True)
        self.repair_placeholders = tk.BooleanVar(value=False)
        ttk.Checkbutton(back, text="对齐译文首尾换行", variable=self.align_newlines).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Checkbutton(back, text="自动补齐丢失的占位符", variable=self.repair_placeholders).grid(row=2, column=2, columnspan=2, sticky="w", pady=(6, 0))
        actions = ttk.Frame(back)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.verify_button = ttk.Button(actions, text="只校验不写出", command=self._verify)
        self.verify_button.grid(row=0, column=0)
        self.generate_button = ttk.Button(actions, text="生成翻译后的 PO", command=self._generate)
        self.generate_button.grid(row=0, column=1, padx=(8, 0))
        self.export_button = ttk.Button(export, text="导出待翻译文本", command=self._export)
        self.export_button.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        log = ttk.LabelFrame(root, text="日志", padding=4)
        log.grid(row=6, column=0, sticky="nsew", pady=(8, 0))
        log.columnconfigure(0, weight=1)
        log.rowconfigure(0, weight=1)
        self.log_view = scrolledtext.ScrolledText(log, height=10, state="disabled", font=(UI_FONT, 9))
        self.log_view.grid(row=0, column=0, sticky="nsew")

    # ------- 路径选择 -------

    def _browse_po(self) -> None:
        path = filedialog.askopenfilename(title="选择 PO 或 POT 文件", filetypes=PO_TYPES)
        if not path:
            return
        self.po_path.set(path)
        suggested = Path(path).with_suffix(".txt")
        if not self.export_path.get():
            self.export_path.set(str(suggested))
        if not self.output_path.get():
            self.output_path.set(str(Path(path).with_name(Path(path).stem + "_翻译后.po")))
        self._submit(lambda: Session(path).stats(), self._on_stats)

    def _browse_export(self) -> None:
        path = filedialog.asksaveasfilename(title="保存待翻译文本", defaultextension=".txt", filetypes=TXT_TYPES)
        if path:
            self.export_path.set(path)

    def _browse_import(self) -> None:
        path = filedialog.askopenfilename(title="选择翻译完成的文本", filetypes=TXT_TYPES)
        if path:
            self.import_path.set(path)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(title="保存翻译后的 PO", defaultextension=".po", filetypes=PO_TYPES)
        if path:
            self.output_path.set(path)

    # ------- 动作 -------

    def _export(self) -> None:
        po, out = self._require(self.po_path, "请先选择 PO / POT 文件"), self._require(self.export_path, "请指定导出文件路径")
        if not (po and out):
            return
        self._submit(lambda: Session(po).export(out, self._options()), self._on_extract)

    def _verify(self) -> None:
        self._apply(write=False)

    def _generate(self) -> None:
        self._apply(write=True)

    def _apply(self, *, write: bool) -> None:
        po = self._require(self.po_path, "请先选择 PO / POT 文件")
        txt = self._require(self.import_path, "请先选择翻译完成的文本")
        out = self._require(self.output_path, "请指定输出 PO 路径") if write else None
        if not po or not txt or (write and not out):
            return
        self._submit(lambda: Session(po).apply(txt, out, self._options()), self._on_apply)

    def _options(self) -> Options:
        lang = self.target_lang.get().strip() or None
        forms = self.plural_forms.get().strip() or None
        return Options(
            include_translated=self.include_all.get(),
            include_fuzzy=self.include_fuzzy.get(),
            target_lang=lang,
            plural_forms=forms,
            align_newlines=self.align_newlines.get(),
            repair_placeholders=self.repair_placeholders.get(),
        )

    def _require(self, var: tk.StringVar, message: str) -> str | None:
        value = var.get().strip()
        if not value:
            messagebox.showwarning("缺少输入", message, parent=self)
            return None
        return value

    # ------- 线程与结果 -------

    def _submit(self, task: Callable[[], object], done: Callable[[object], None]) -> None:
        if self._busy:
            messagebox.showinfo("请稍候", "上一个任务还没结束", parent=self)
            return
        self._busy = True
        self._task_done = done
        for button in (self.export_button, self.verify_button, self.generate_button):
            button.state(["disabled"])

        def runner() -> None:
            try:
                self._events.put(("ok", task()))
            except (PoTextError, OSError, ValueError) as error:
                self._events.put(("error", str(error)))
            except Exception as error:  # 兜底：任何意外都要让界面恢复可点
                self._events.put(("error", f"未预期的错误：{error}"))

        self._worker = threading.Thread(target=runner, daemon=True)
        self._worker.start()

    def _poll(self) -> None:
        try:
            kind, payload = self._events.get_nowait()
        except queue.Empty:
            self.after(POLL_MS, self._poll)
            return
        self._busy = False
        for button in (self.export_button, self.verify_button, self.generate_button):
            button.state(["!disabled"])
        if kind == "error":
            self._log([f"失败：{payload}"])
            messagebox.showerror("操作失败", str(payload), parent=self)
        else:
            self._task_done(payload)
        self.after(POLL_MS, self._poll)

    def _on_stats(self, result: object) -> None:
        summary = getattr(result, "summary", lambda: [str(result)])()
        self._log(summary)

    def _on_extract(self, result: ExtractReport) -> None:
        self._log(result.summary())
        if result.exported_slots == 0:
            messagebox.showinfo("没有待翻译内容", "这个 PO 文件里没有需要翻译的条目", parent=self)
            return
        messagebox.showinfo("导出完成", f"已导出 {result.exported_slots} 行待翻译文本", parent=self)

    def _on_apply(self, result: ApplyReport) -> None:
        lines = result.summary()
        lines += [f"  - {issue.describe()}" for issue in result.issues[:30]]
        if len(result.issues) > 30:
            lines.append(f"  ……另有 {len(result.issues) - 30} 条占位符问题未列出")
        self._log(lines)
        detail = "\n".join(line for line in lines if "占位符" in line or "已写出" in line)
        messagebox.showinfo("处理完成", detail or "完成", parent=self)

    def _log(self, lines: list[str]) -> None:
        self.log_view.configure(state="normal")
        self.log_view.insert(tk.END, "\n".join(lines) + "\n")
        self.log_view.see(tk.END)
        self.log_view.configure(state="disabled")


def main() -> int:
    App().mainloop()
    return 0
