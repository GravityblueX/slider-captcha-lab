from __future__ import annotations

import subprocess
import sys
import tkinter as tk
import runpy
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
PY = sys.executable

TOOLS = {
    "轨迹实验室": {
        "script": "slider_lab.py",
        "desc": "生成、记录、分析滑动轨迹；本地滑块模拟；环境诊断。",
    },
    "授权滑块测试": {
        "script": "authorized_gui_tester.py",
        "desc": "输入授权测试页面 URL 与 selector，运行多种滑动轨迹策略并展示结果。",
    },
    "风险分析中心": {
        "script": "risk_gui.py",
        "desc": "导入浏览器诊断JSON，自动评分环境一致性、事件链和自动化风险，导出HTML报告。",
    },
    "综合报告中心": {
        "script": "report_center.py",
        "desc": "汇总行为会话、授权滑块测试、风险分析和环境体检 JSON，生成统一 HTML 报告。",
    },
    "行为会话测试": {
        "script": "behavior_gui.py",
        "desc": "编排停留、鼠标游走、滚动、点击、输入、等待等完整人类行为会话。",
    },
}

TOOL_SCRIPT_BY_NAME = {name: info["script"] for name, info in TOOLS.items()}


def run_tool(name: str) -> int:
    script_name = TOOL_SCRIPT_BY_NAME.get(name)
    if not script_name:
        messagebox.showerror("未知工具", name)
        return 1
    script = ROOT / script_name
    if not script.exists():
        messagebox.showerror("文件不存在", f"找不到：{script}")
        return 1
    sys.path.insert(0, str(ROOT))
    runpy.run_path(str(script), run_name="__main__")
    return 0


def smoke_check() -> int:
    missing = [script for script in TOOL_SCRIPT_BY_NAME.values() if not (ROOT / script).exists()]
    missing.extend(name for name in ["demo/event_diagnostics.html", "src/trajectory.py"] if not (ROOT / name).exists())
    return 1 if missing else 0


class LiuHenLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("留痕")
        self.geometry("980x600")
        self.resizable(False, False)
        self._build()

    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        root = ttk.Frame(self, padding=24)
        root.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(root, text="留痕", font=("Microsoft YaHei UI", 28, "bold"))
        title.pack(anchor="w")
        subtitle = ttk.Label(root, text="滑动轨迹、授权页面行为测试与环境诊断工具", font=("Microsoft YaHei UI", 12))
        subtitle.pack(anchor="w", pady=(4, 18))

        cards = ttk.Frame(root)
        cards.pack(fill=tk.X)
        for name, info in TOOLS.items():
            frame = ttk.LabelFrame(cards, text=name, padding=14)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
            ttk.Label(frame, text=info["desc"], wraplength=220, justify="left").pack(anchor="w", pady=(0, 16))
            ttk.Button(frame, text=f"打开{name}", command=lambda n=name: self.open_tool(n)).pack(fill=tk.X)

        quick = ttk.LabelFrame(root, text="推荐使用流程", padding=14)
        quick.pack(fill=tk.BOTH, expand=True, pady=18)
        text = tk.Text(quick, height=11, wrap=tk.WORD, font=("Microsoft YaHei UI", 10))
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, "1. 先打开【轨迹实验室】：生成轨迹、记录人工轨迹、观察速度/加速度/抖动指标。\n")
        text.insert(tk.END, "2. 如果要测试授权页面的滑块，打开【授权滑块测试】：填写 URL、滑块轨道 selector、按钮 selector、成功判断 selector，然后运行四种策略。\n")
        text.insert(tk.END, "3. 如果要模拟更完整的人类浏览行为，打开【行为会话测试】：编排停留、鼠标游走、滚动、点击、输入、等待，并导出 HTML 报告。\n")
        text.insert(tk.END, "4. 所有测试仅限本地、自有或明确授权范围；建议导出 JSON/HTML 结果留档。\n")
        text.config(state=tk.DISABLED)

        bottom = ttk.Frame(root)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="检查依赖", command=self.check_deps).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="打开项目目录", command=self.open_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="退出", command=self.destroy).pack(side=tk.RIGHT, padx=4)

    def open_tool(self, name: str):
        script = ROOT / TOOLS[name]["script"]
        if not script.exists():
            messagebox.showerror("文件不存在", f"找不到：{script}")
            return
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([PY, "--open-tool", name], cwd=str(ROOT))
            else:
                subprocess.Popen([PY, str(script)], cwd=str(ROOT))
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def check_deps(self):
        missing = []
        try:
            import matplotlib  # noqa
        except Exception:
            missing.append("matplotlib")
        try:
            import playwright  # noqa
        except Exception:
            missing.append("playwright")
        if missing:
            messagebox.showwarning("缺少依赖", "缺少：" + ", ".join(missing) + "\n\n建议运行：\npip install matplotlib playwright\nplaywright install chromium")
        else:
            messagebox.showinfo("依赖检查", "Python 依赖看起来已安装。若浏览器测试失败，请运行：playwright install chromium")

    def open_folder(self):
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(ROOT)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(ROOT)])
            else:
                subprocess.Popen(["xdg-open", str(ROOT)])
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

if __name__ == "__main__":
    if "--smoke-check" in sys.argv:
        raise SystemExit(smoke_check())
    if len(sys.argv) >= 3 and sys.argv[1] == "--open-tool":
        raise SystemExit(run_tool(sys.argv[2]))
    LiuHenLauncher().mainloop()
