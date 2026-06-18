from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from playwright.sync_api import sync_playwright

from src.browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms

try:
    from src.trajectory import generate_trajectory
except Exception:
    from trajectory import generate_trajectory

ROOT = Path(__file__).resolve().parent

@dataclass
class Attempt:
    strategy: str
    ok: bool
    reason: str
    elapsed_ms: float
    url: str


def _resolve_url(url: str) -> str:
    if url.startswith(("http://", "https://", "file://")):
        return url
    return (ROOT / url).resolve().as_uri()


class AuthorizedTester(tk.Tk):
    """Authorized page testing console.

    Scope: local, owned, or explicitly authorized pages only.
    It does not perform stealth, fingerprint spoofing, CAPTCHA solving, or access-control bypass.
    """

    def __init__(self):
        super().__init__()
        self.title("留痕 - 授权页面测试台")
        self.geometry("1120x760")
        self.results: list[Attempt] = []
        self._build()

    def _build(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)
        form = ttk.LabelFrame(main, text="测试目标与选择器", padding=10)
        form.pack(fill=tk.X)

        self.url = tk.StringVar(value="https://")
        self.slider = tk.StringVar(value="")
        self.knob = tk.StringVar(value="")
        self.success = tk.StringVar(value="")
        self.success_text = tk.StringVar(value="")
        self.distance = tk.IntVar(value=320)
        self.duration = tk.IntVar(value=900)
        self.steps = tk.IntVar(value=90)
        self.jitter = tk.DoubleVar(value=1.6)
        self.headless = tk.BooleanVar(value=False)
        self.authorized = tk.BooleanVar(value=False)
        self.user_data_dir = tk.StringVar(value=".liuhen/profiles/default")
        self.extension_paths = tk.StringVar(value="")
        self.manual_navigation = tk.BooleanVar(value=False)
        self.manual_wait_seconds = tk.IntVar(value=60)

        rows = [
            ("URL", self.url, 72),
            ("滑块轨道 selector", self.slider, 34),
            ("滑块按钮 selector", self.knob, 34),
            ("成功判断 selector", self.success, 34),
            ("成功文本包含", self.success_text, 34),
        ]
        for i, (label, var, width) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=var, width=width).grid(row=i, column=1, columnspan=5, sticky="we", pady=4)

        ttk.Label(form, text="距离").grid(row=5, column=0, sticky="w")
        ttk.Spinbox(form, from_=60, to=1200, textvariable=self.distance, width=10).grid(row=5, column=1, sticky="w")
        ttk.Label(form, text="耗时ms").grid(row=5, column=2, sticky="w")
        ttk.Spinbox(form, from_=200, to=4000, textvariable=self.duration, width=10).grid(row=5, column=3, sticky="w")
        ttk.Label(form, text="点数").grid(row=5, column=4, sticky="w")
        ttk.Spinbox(form, from_=10, to=400, textvariable=self.steps, width=10).grid(row=5, column=5, sticky="w")
        ttk.Label(form, text="抖动").grid(row=6, column=0, sticky="w")
        ttk.Spinbox(form, from_=0, to=8, increment=.1, textvariable=self.jitter, width=10).grid(row=6, column=1, sticky="w")
        ttk.Checkbutton(form, text="显示浏览器窗口", variable=self.headless, onvalue=False, offvalue=True).grid(row=6, column=2, sticky="w")
        ttk.Checkbutton(form, text="我确认该 URL 属于本地/自有/已授权测试范围", variable=self.authorized).grid(row=6, column=3, columnspan=3, sticky="w")
        ttk.Label(form, text="Profile目录").grid(row=7, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.user_data_dir, width=34).grid(row=7, column=1, columnspan=2, sticky="we", pady=4)
        ttk.Label(form, text="扩展目录(;分隔)").grid(row=7, column=3, sticky="w")
        ttk.Entry(form, textvariable=self.extension_paths, width=34).grid(row=7, column=4, columnspan=2, sticky="we", pady=4)
        ttk.Checkbutton(form, text="手动深层页面模式", variable=self.manual_navigation).grid(row=8, column=1, sticky="w")
        ttk.Label(form, text="等待秒").grid(row=8, column=2, sticky="e")
        ttk.Spinbox(form, from_=0, to=600, textvariable=self.manual_wait_seconds, width=8).grid(row=8, column=3, sticky="w")

        btns = ttk.Frame(main)
        btns.pack(fill=tk.X, pady=10)
        ttk.Button(btns, text="运行四种策略", command=self.run_async).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="导入配置JSON", command=self.load_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="导出配置JSON", command=self.save_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="导出结果JSON", command=self.export_results).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="清空结果", command=self.clear).pack(side=tk.LEFT, padx=4)

        self.status = ttk.Label(main, text="就绪。填写授权测试页面 URL 与 selector 后运行。")
        self.status.pack(fill=tk.X)

        table_frame = ttk.LabelFrame(main, text="结果", padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.table = ttk.Treeview(table_frame, columns=("strategy", "ok", "elapsed", "reason"), show="headings")
        for col, text, width in [("strategy", "策略", 110), ("ok", "结果", 80), ("elapsed", "耗时ms", 90), ("reason", "原因/证据", 760)]:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="w")
        self.table.pack(fill=tk.BOTH, expand=True)

        help_text = (
            "专业测试建议：先确认授权范围；用开发者工具复制准确 selector；"
            "success_selector 应选择验证成功后会变化的元素；测试后导出 JSON 留证。"
        )
        ttk.Label(main, text=help_text, foreground="#555").pack(fill=tk.X)

    def profile_dict(self):
        return {
            "name": "custom-authorized-target",
            "url": self.url.get().strip(),
            "slider_selector": self.slider.get().strip(),
            "knob_selector": self.knob.get().strip(),
            "success_selector": self.success.get().strip(),
            "success_text_contains": self.success_text.get().strip(),
            "distance": self.distance.get(),
            "duration_ms": self.duration.get(),
            "steps": self.steps.get(),
            "jitter": self.jitter.get(),
            "modes": ["normal", "careful", "fast", "hesitant"],
            "browser": {
                "user_data_dir": self.user_data_dir.get().strip(),
                "extension_paths": [x.strip() for x in self.extension_paths.get().split(";") if x.strip()],
                "manual_navigation": self.manual_navigation.get(),
                "manual_wait_ms": self.manual_wait_seconds.get() * 1000,
            },
            "authorized_only": True,
        }

    def load_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.url.set(data.get("url", ""))
        self.slider.set(data.get("slider_selector", ""))
        self.knob.set(data.get("knob_selector", ""))
        self.success.set(data.get("success_selector", ""))
        self.success_text.set(data.get("success_text_contains", ""))
        self.distance.set(int(data.get("distance", 320)))
        self.duration.set(int(data.get("duration_ms", 900)))
        self.steps.set(int(data.get("steps", 90)))
        self.jitter.set(float(data.get("jitter", 1.6)))
        browser = data.get("browser", {}) if isinstance(data.get("browser", {}), dict) else {}
        self.user_data_dir.set(browser.get("user_data_dir", ".liuhen/profiles/default"))
        ext = browser.get("extension_paths", [])
        self.extension_paths.set(";".join(ext) if isinstance(ext, list) else str(ext or ""))
        self.manual_navigation.set(bool(browser.get("manual_navigation", False)))
        self.manual_wait_seconds.set(int(browser.get("manual_wait_ms", 60000)) // 1000)
        self.authorized.set(bool(data.get("authorized_only", False)))

    def save_profile(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            Path(path).write_text(json.dumps(self.profile_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("完成", f"已保存配置：{path}")

    def clear(self):
        self.results.clear()
        for i in self.table.get_children():
            self.table.delete(i)
        self.status.config(text="结果已清空。")

    def run_async(self):
        if not self.authorized.get():
            messagebox.showwarning("需要确认授权", "请先勾选：我确认该 URL 属于本地/自有/已授权测试范围。")
            return
        if not self.url.get().strip() or not self.slider.get().strip() or not self.knob.get().strip():
            messagebox.showwarning("参数不足", "URL、滑块轨道 selector、滑块按钮 selector 必填。")
            return
        if self.manual_navigation.get():
            messagebox.showinfo("手动深层页面模式", f"浏览器打开后，请在 {self.manual_wait_seconds.get()} 秒内手动完成登录、跳转或进入授权深层页面。等待结束后会从当前页面继续测试。")
        self.clear()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        profile = self.profile_dict()
        modes = profile["modes"]
        self._status("测试运行中，请等待...")
        try:
            with sync_playwright() as p:
                context, browser = launch_browser_context(p, profile, headless=self.headless.get(), viewport={"width": 1200, "height": 800})
                try:
                    manual_page = None
                    if manual_navigation_enabled(profile):
                        manual_page = context.pages[-1] if context.pages else context.new_page()
                        manual_page.goto(_resolve_url(profile["url"]), wait_until="domcontentloaded", timeout=20000)
                        wait = manual_wait_ms(profile)
                        self._status(f"手动深层页面模式：请在 {wait // 1000} 秒内进入授权目标页面...")
                        if wait > 0:
                            manual_page.wait_for_timeout(wait)
                        if context.pages:
                            manual_page = context.pages[-1]
                    for mode in modes:
                        result = self._attempt(context, profile, mode, manual_page)
                        self.results.append(result)
                        self.after(0, lambda r=result: self.table.insert("", tk.END, values=(r.strategy, "通过" if r.ok else "失败", r.elapsed_ms, r.reason)))
                finally:
                    close_browser_context(context, browser)
            passed = sum(1 for r in self.results if r.ok)
            total = len(self.results)
            self._status(f"测试完成：通过 {passed}/{total}")
            self.after(0, lambda: messagebox.showinfo("测试完成", f"共 {total} 组策略\n通过 {passed} 组\n失败 {total-passed} 组"))
        except Exception as e:
            self._status(f"运行失败：{e}")
            self.after(0, lambda: messagebox.showerror("运行失败", str(e)))

    def _attempt(self, context, profile, mode: str, manual_page=None) -> Attempt:
        page = manual_page or context.new_page()
        t0 = time.perf_counter()
        try:
            url = _resolve_url(profile["url"])
            if manual_page is None:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_selector(profile["slider_selector"], timeout=10000)
            page.wait_for_selector(profile["knob_selector"], timeout=10000)
            slider = page.locator(profile["slider_selector"]).bounding_box()
            knob = page.locator(profile["knob_selector"]).bounding_box()
            if not slider or not knob:
                raise RuntimeError("无法获取滑块或按钮位置，请检查 selector 是否正确。")
            start = (knob["x"] + knob["width"] / 2, knob["y"] + knob["height"] / 2)
            end = (start[0] + float(profile["distance"]), start[1])
            path = generate_trajectory(start=start, end=end, duration_ms=int(profile["duration_ms"]), steps=int(profile["steps"]), jitter=float(profile["jitter"]), mode=mode, overshoot=True, micro_pause=True)
            page.mouse.move(path[0].x, path[0].y)
            page.mouse.down()
            last = 0
            for pt in path[1:]:
                page.wait_for_timeout(max(1, int(pt.t - last)))
                page.mouse.move(pt.x, pt.y)
                last = pt.t
            page.mouse.up()
            page.wait_for_timeout(700)
            reason = "拖动序列已完成。"
            ok = True
            if profile.get("success_selector"):
                txt = page.locator(profile["success_selector"]).inner_text(timeout=3000)
                expected = profile.get("success_text_contains") or ""
                ok = expected.lower() in txt.lower() if expected else bool(txt)
                reason = f"success_selector文本: {txt!r}"
            return Attempt(mode, ok, reason, round((time.perf_counter() - t0) * 1000, 2), profile["url"])
        except Exception as e:
            return Attempt(mode, False, str(e), round((time.perf_counter() - t0) * 1000, 2), profile.get("url", ""))
        finally:
            if manual_page is None:
                page.close()

    def _status(self, text):
        self.after(0, lambda: self.status.config(text=text))

    def export_results(self):
        if not self.results:
            messagebox.showwarning("没有结果", "请先运行测试。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {
            "profile": self.profile_dict(),
            "results": [asdict(r) for r in self.results],
            "summary": {"total": len(self.results), "passed": sum(1 for r in self.results if r.ok), "failed": sum(1 for r in self.results if not r.ok)},
            "scope": "local_owned_or_explicitly_authorized_pages_only",
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("完成", f"已导出结果：{path}")


if __name__ == "__main__":
    AuthorizedTester().mainloop()
