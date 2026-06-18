from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from html import escape
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.human_behavior import run_session

@dataclass
class ActionItem:
    type: str
    selector: str = ""
    text: str = ""
    ms: int = 1000
    amount: int = 500
    timeout: int = 10000
    duration_ms: int = 1400
    required: bool = True

class BehaviorGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("留痕 - 行为会话测试台")
        self.geometry("1180x780")
        self.actions: list[ActionItem] = []
        self.last_result = None
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        top = ttk.LabelFrame(root, text="授权目标", padding=10)
        top.pack(fill=tk.X)
        self.url = tk.StringVar(value="https://")
        self.authorized = tk.BooleanVar(value=False)
        self.headless = tk.BooleanVar(value=False)
        self.viewport_w = tk.IntVar(value=1280)
        self.viewport_h = tk.IntVar(value=850)
        self.user_data_dir = tk.StringVar(value=".liuhen/profiles/default")
        self.extension_paths = tk.StringVar(value="")
        self.manual_navigation = tk.BooleanVar(value=False)
        self.manual_wait_seconds = tk.IntVar(value=60)
        self.frame_chain = tk.StringVar(value="")
        ttk.Label(top, text="URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.url, width=84).grid(row=0, column=1, columnspan=7, sticky="we", padx=6)
        ttk.Checkbutton(top, text="我确认该 URL 属于本地/自有/已授权测试范围", variable=self.authorized).grid(row=1, column=1, columnspan=3, sticky="w", pady=6)
        ttk.Checkbutton(top, text="显示浏览器窗口", variable=self.headless, onvalue=False, offvalue=True).grid(row=1, column=4, sticky="w")
        ttk.Label(top, text="视口").grid(row=1, column=5, sticky="e")
        ttk.Spinbox(top, from_=800, to=2560, textvariable=self.viewport_w, width=8).grid(row=1, column=6, sticky="w")
        ttk.Spinbox(top, from_=600, to=1600, textvariable=self.viewport_h, width=8).grid(row=1, column=7, sticky="w")
        ttk.Label(top, text="Profile目录").grid(row=2, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.user_data_dir, width=42).grid(row=2, column=1, columnspan=3, sticky="we", padx=6, pady=3)
        ttk.Label(top, text="扩展目录(;分隔)").grid(row=2, column=4, sticky="e")
        ttk.Entry(top, textvariable=self.extension_paths, width=36).grid(row=2, column=5, columnspan=3, sticky="we", padx=6, pady=3)
        ttk.Checkbutton(top, text="手动深层页面模式", variable=self.manual_navigation).grid(row=3, column=1, sticky="w", pady=3)
        ttk.Label(top, text="等待秒").grid(row=3, column=2, sticky="e")
        ttk.Spinbox(top, from_=0, to=600, textvariable=self.manual_wait_seconds, width=8).grid(row=3, column=3, sticky="w")
        ttk.Label(top, text="frame_chain JSON").grid(row=3, column=4, sticky="e")
        ttk.Entry(top, textvariable=self.frame_chain, width=36).grid(row=3, column=5, columnspan=3, sticky="we", padx=6, pady=3)

        mid = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        mid.pack(fill=tk.BOTH, expand=True, pady=10)
        left = ttk.LabelFrame(mid, text="动作编排", padding=8)
        right = ttk.LabelFrame(mid, text="执行日志", padding=8)
        mid.add(left, weight=1)
        mid.add(right, weight=1)

        form = ttk.Frame(left)
        form.pack(fill=tk.X)
        self.action_type = tk.StringVar(value="dwell")
        self.selector = tk.StringVar(value="")
        self.text = tk.StringVar(value="")
        self.ms = tk.IntVar(value=1000)
        self.amount = tk.IntVar(value=500)
        self.timeout = tk.IntVar(value=10000)
        self.duration_ms = tk.IntVar(value=1400)
        self.required = tk.BooleanVar(value=True)
        ttk.Label(form, text="动作").grid(row=0, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.action_type, values=["dwell", "mouse_wander", "scroll", "click", "fill", "wait_for"], state="readonly", width=16).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="selector").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.selector, width=46).grid(row=1, column=1, columnspan=4, sticky="we", pady=3)
        ttk.Label(form, text="输入文本").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.text, width=46).grid(row=2, column=1, columnspan=4, sticky="we", pady=3)
        for i, (lab, var) in enumerate([("停留ms", self.ms), ("滚动量", self.amount), ("超时ms", self.timeout), ("游走ms", self.duration_ms)]):
            ttk.Label(form, text=lab).grid(row=3, column=i, sticky="w")
            ttk.Spinbox(form, from_=1, to=60000, textvariable=var, width=9).grid(row=4, column=i, sticky="w")
        ttk.Checkbutton(form, text="失败时中止", variable=self.required).grid(row=4, column=4, sticky="w")

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=8)
        for txt, cmd in [("添加动作", self.add_action), ("删除选中", self.remove_action), ("上移", lambda:self.move(-1)), ("下移", lambda:self.move(1)), ("加载模板", self.load_template)]:
            ttk.Button(buttons, text=txt, command=cmd).pack(side=tk.LEFT, padx=3)

        self.tree = ttk.Treeview(left, columns=("type", "selector", "detail", "required"), show="headings", height=17)
        for col, name, width in [("type", "动作", 100), ("selector", "selector", 220), ("detail", "参数", 260), ("required", "必需", 60)]:
            self.tree.heading(col, text=name); self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)

        runbar = ttk.Frame(left)
        runbar.pack(fill=tk.X, pady=8)
        for txt, cmd in [("运行会话", self.run_async), ("导入Profile", self.import_profile), ("导出Profile", self.export_profile), ("导出HTML报告", self.export_html)]:
            ttk.Button(runbar, text=txt, command=cmd).pack(side=tk.LEFT, padx=3)

        self.log = tk.Text(right)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.status = ttk.Label(root, text="就绪。建议使用授权测试站点，先编排动作，再运行会话。")
        self.status.pack(fill=tk.X)

    def add_action(self):
        item = ActionItem(self.action_type.get(), self.selector.get(), self.text.get(), self.ms.get(), self.amount.get(), self.timeout.get(), self.duration_ms.get(), self.required.get())
        self.actions.append(item)
        self.refresh()

    def remove_action(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        self.actions.pop(idx)
        self.refresh()

    def move(self, delta):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0]); ni = idx + delta
        if 0 <= ni < len(self.actions):
            self.actions[idx], self.actions[ni] = self.actions[ni], self.actions[idx]
            self.refresh(); self.tree.selection_set(self.tree.get_children()[ni])

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for a in self.actions:
            detail = json.dumps(self.action_to_dict(a), ensure_ascii=False)
            self.tree.insert("", tk.END, values=(a.type, a.selector, detail, "是" if a.required else "否"))

    def action_to_dict(self, a: ActionItem):
        d = {"type": a.type, "required": a.required}
        if a.type in ["click", "fill", "wait_for"]: d["selector"] = a.selector
        if a.type == "fill": d["text"] = a.text
        if a.type == "dwell": d["ms"] = a.ms
        if a.type == "scroll": d["amount"] = a.amount
        if a.type == "wait_for": d["timeout"] = a.timeout
        if a.type == "mouse_wander": d["duration_ms"] = a.duration_ms
        return d

    def profile(self):
        return {
            "name": "留痕行为会话",
            "url": self.url.get().strip(),
            "authorized_only": True,
            "viewport": {"width": self.viewport_w.get(), "height": self.viewport_h.get()},
            "browser": {
                "user_data_dir": self.user_data_dir.get().strip(),
                "extension_paths": [x.strip() for x in self.extension_paths.get().split(";") if x.strip()],
                "manual_navigation": self.manual_navigation.get(),
                "manual_wait_ms": self.manual_wait_seconds.get() * 1000,
            },
            "target": self.target_dict(),
            "actions": [self.action_to_dict(a) for a in self.actions],
        }

    def target_dict(self):
        text = self.frame_chain.get().strip()
        if not text:
            return {}
        try:
            return {"frame_chain": json.loads(text)}
        except Exception:
            return {"frame_chain": [{"selector": text}]}

    def load_template(self):
        self.actions = [
            ActionItem("dwell", ms=1200),
            ActionItem("mouse_wander", duration_ms=1600),
            ActionItem("scroll", amount=450, required=False),
            ActionItem("dwell", ms=800),
        ]
        self.refresh()

    def import_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not path: return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.url.set(data.get("url", "")); self.authorized.set(bool(data.get("authorized_only", False)))
        vp = data.get("viewport", {}); self.viewport_w.set(vp.get("width", 1280)); self.viewport_h.set(vp.get("height", 850))
        browser = data.get("browser", {}) if isinstance(data.get("browser", {}), dict) else {}
        self.user_data_dir.set(browser.get("user_data_dir", ".liuhen/profiles/default"))
        ext = browser.get("extension_paths", [])
        self.extension_paths.set(";".join(ext) if isinstance(ext, list) else str(ext or ""))
        self.manual_navigation.set(bool(browser.get("manual_navigation", False)))
        self.manual_wait_seconds.set(int(browser.get("manual_wait_ms", 60000)) // 1000)
        target = data.get("target", {}) if isinstance(data.get("target", {}), dict) else {}
        self.frame_chain.set(json.dumps(target.get("frame_chain", ""), ensure_ascii=False) if target.get("frame_chain") else "")
        self.actions=[]
        for d in data.get("actions", []):
            self.actions.append(ActionItem(d.get("type","dwell"), d.get("selector",""), d.get("text",""), int(d.get("ms",1000)), int(d.get("amount",500)), int(d.get("timeout",10000)), int(d.get("duration_ms",1400)), bool(d.get("required", True))))
        self.refresh()

    def export_profile(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            Path(path).write_text(json.dumps(self.profile(), ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("完成", f"已保存：{path}")

    def run_async(self):
        if not self.authorized.get():
            messagebox.showwarning("需要授权确认", "请先确认该 URL 属于本地/自有/已授权测试范围。")
            return
        if not self.actions:
            messagebox.showwarning("没有动作", "请先添加或加载动作模板。")
            return
        if self.manual_navigation.get():
            messagebox.showinfo("手动深层页面模式", f"浏览器打开后，请在 {self.manual_wait_seconds.get()} 秒内手动完成登录、跳转或进入授权深层页面。等待结束后会从当前页面继续执行动作链。")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        tmp = Path("_tmp_behavior_profile.json")
        tmp.write_text(json.dumps(self.profile(), ensure_ascii=False, indent=2), encoding="utf-8")
        self.after(0, lambda: self.status.config(text="会话运行中..."))
        try:
            result = run_session(str(tmp), headless=self.headless.get())
            self.last_result = result
            self.after(0, lambda: self.show_result(result))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("运行失败", str(e)))
        finally:
            try: tmp.unlink()
            except Exception: pass

    def show_result(self, result):
        self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2))
        s = result.get("summary", {})
        self.status.config(text=f"完成：成功 {s.get('ok',0)}/{s.get('total',0)}，失败 {s.get('failed',0)}")
        messagebox.showinfo("会话完成", f"动作总数：{s.get('total',0)}\n成功：{s.get('ok',0)}\n失败：{s.get('failed',0)}")

    def export_html(self):
        if not self.last_result:
            messagebox.showwarning("没有结果", "请先运行会话。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not path: return
        html = self.make_html(self.last_result)
        Path(path).write_text(html, encoding="utf-8")
        messagebox.showinfo("完成", f"已导出报告：{path}")

    def make_html(self, r):
        rows = "".join(
            f"<tr><td>{escape(str(x['action']))}</td><td>{'OK' if x['ok'] else 'FAIL'}</td>"
            f"<td>{escape(str(x['elapsed_ms']))}</td><td><pre>{escape(str(x['detail']))}</pre></td></tr>"
            for x in r.get("logs", [])
        )
        summary = escape(json.dumps(r.get('summary'), ensure_ascii=False, indent=2))
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>留痕行为会话报告</title><style>body{{font-family:system-ui,sans-serif;padding:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top}}pre{{white-space:pre-wrap;margin:0}}.ok{{color:#059669}}</style></head><body><h1>留痕行为会话报告</h1><p>URL: {escape(str(r.get('url','')))}</p><p>Scope: {escape(str(r.get('scope','')))}</p><h2>摘要</h2><pre>{summary}</pre><h2>动作日志</h2><table><tr><th>动作</th><th>结果</th><th>耗时ms</th><th>详情</th></tr>{rows}</table><p>说明：本报告用于本地/自有/授权测试范围内的行为会话评估。</p></body></html>"""

if __name__ == "__main__":
    BehaviorGui().mainloop()
