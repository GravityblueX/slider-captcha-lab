from __future__ import annotations

import json
import tkinter as tk
from html import escape
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.risk_analyzer import analyze_export

class RiskGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("留痕 - 风险分析中心")
        self.geometry("1120x760")
        self.result = None
        self.source_path = ""
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        top = ttk.LabelFrame(root, text="诊断数据", padding=10)
        top.pack(fill=tk.X)
        self.path_var = tk.StringVar(value="")
        ttk.Label(top, text="诊断 JSON").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.path_var, width=92).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="选择文件", command=self.pick).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="开始分析", command=self.analyze).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="导出HTML报告", command=self.export_html).pack(side=tk.LEFT, padx=4)

        summary = ttk.LabelFrame(root, text="评分摘要", padding=10)
        summary.pack(fill=tk.X, pady=10)
        self.fp_score = tk.StringVar(value="环境评分：-")
        self.ev_score = tk.StringVar(value="事件评分：-")
        self.verdict = tk.StringVar(value="结论：-")
        ttk.Label(summary, textvariable=self.fp_score, font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT, padx=12)
        ttk.Label(summary, textvariable=self.ev_score, font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT, padx=12)
        ttk.Label(summary, textvariable=self.verdict, font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT, padx=12)

        mid = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        mid.pack(fill=tk.BOTH, expand=True)
        left = ttk.LabelFrame(mid, text="风险项", padding=8)
        right = ttk.LabelFrame(mid, text="详细 JSON", padding=8)
        mid.add(left, weight=1)
        mid.add(right, weight=1)

        self.tree = ttk.Treeview(left, columns=("level", "category", "field", "message", "suggestion"), show="headings")
        for col, name, width in [("level","等级",70),("category","类别",100),("field","字段",160),("message","问题",330),("suggestion","建议",360)]:
            self.tree.heading(col, text=name)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.detail = tk.Text(right, wrap=tk.WORD)
        self.detail.pack(fill=tk.BOTH, expand=True)

        bottom = ttk.LabelFrame(root, text="说明", padding=10)
        bottom.pack(fill=tk.X, pady=10)
        ttk.Label(bottom, text="本工具用于本地/自有/授权测试中的环境一致性、事件链完整性和自动化风险观察；不会伪装、修改或绕过任何风控。", foreground="#555").pack(anchor="w")

    def pick(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if path:
            self.path_var.set(path)

    def analyze(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("缺少文件", "请选择浏览器诊断页导出的 JSON。")
            return
        try:
            self.result = analyze_export(path)
            self.source_path = path
            self.render()
        except Exception as e:
            messagebox.showerror("分析失败", str(e))

    def render(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        fp = self.result.get("fingerprint", {})
        ev = self.result.get("events") or {}
        self.fp_score.set(f"环境评分：{fp.get('score', '-')}/100")
        self.ev_score.set(f"事件评分：{ev.get('score', '-')}/100" if ev else "事件评分：无事件数据")
        self.verdict.set(f"结论：{fp.get('verdict', '-')}")
        for r in fp.get("risks", []):
            self.tree.insert("", tk.END, values=(r.get("level"), r.get("category"), r.get("field"), r.get("message"), r.get("suggestion")))
        for r in ev.get("risks", []):
            self.tree.insert("", tk.END, values=(r.get("level"), r.get("category"), r.get("field"), r.get("message"), r.get("suggestion")))
        self.detail.delete("1.0", tk.END)
        self.detail.insert(tk.END, json.dumps(self.result, ensure_ascii=False, indent=2))
        messagebox.showinfo("分析完成", f"环境评分：{fp.get('score', '-')}/100\n风险项：{len(fp.get('risks', [])) + len(ev.get('risks', []) if ev else [])}")

    def export_html(self):
        if not self.result:
            messagebox.showwarning("没有结果", "请先分析。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not path:
            return
        Path(path).write_text(self.make_html(), encoding="utf-8")
        messagebox.showinfo("完成", f"已导出：{path}")

    def make_html(self):
        fp = self.result.get("fingerprint", {})
        ev = self.result.get("events") or {}
        risks = fp.get("risks", []) + ev.get("risks", [])
        rows = "".join(
            "<tr>"
            f"<td>{escape(str(r.get('level','')))}</td>"
            f"<td>{escape(str(r.get('category','')))}</td>"
            f"<td>{escape(str(r.get('field','')))}</td>"
            f"<td>{escape(str(r.get('message','')))}</td>"
            f"<td>{escape(str(r.get('suggestion','')))}</td>"
            "</tr>"
            for r in risks
        )
        raw = escape(json.dumps(self.result, ensure_ascii=False, indent=2))
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>留痕风险分析报告</title><style>body{{font-family:system-ui,sans-serif;padding:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top}}pre{{background:#f6f8fa;padding:12px;border-radius:8px;white-space:pre-wrap}}</style></head><body><h1>留痕风险分析报告</h1><p>来源文件：{escape(self.source_path)}</p><h2>摘要</h2><ul><li>环境评分：{escape(str(fp.get('score','-')))}/100</li><li>环境结论：{escape(str(fp.get('verdict','-')))}</li><li>事件评分：{escape(str(ev.get('score','无')))}</li></ul><h2>风险项</h2><table><tr><th>等级</th><th>类别</th><th>字段</th><th>问题</th><th>建议</th></tr>{rows}</table><h2>原始分析JSON</h2><pre>{raw}</pre><p>说明：本报告仅用于本地/自有/授权测试中的防御评估与质量检查。</p></body></html>"""

if __name__ == "__main__":
    RiskGui().mainloop()
