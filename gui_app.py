"""Slider Trajectory Lab - desktop GUI.

Run:
    python gui_app.py

Build EXE on Windows:
    pip install pyinstaller matplotlib
    pyinstaller --onefile --windowed --name SliderTrajectoryLab gui_app.py
"""
from __future__ import annotations

import csv
import math
import random
import statistics
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    plt = None
    FigureCanvasTkAgg = None


@dataclass
class Point:
    x: float
    y: float
    t: float


def bezier(p0: float, p1: float, p2: float, p3: float, u: float) -> float:
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u ** 2 * p2 + u ** 3 * p3


def generate_trajectory(distance: int = 320, duration_ms: int = 900, steps: int = 80, jitter: float = 1.5) -> list[Point]:
    sx, sy = 0.0, 0.0
    ex, ey = float(distance), random.uniform(-3, 3)
    c1 = (distance * 0.25, random.uniform(-22, 22))
    c2 = (distance * 0.75, random.uniform(-22, 22))
    pts: list[Point] = []
    for i in range(max(3, steps)):
        u = i / (steps - 1)
        eased = 0.5 - 0.5 * math.cos(math.pi * u)
        x = bezier(sx, c1[0], c2[0], ex, eased) + random.gauss(0, jitter)
        y = bezier(sy, c1[1], c2[1], ey, eased) + random.gauss(0, jitter)
        t = max(0.0, duration_ms * eased + random.uniform(-4, 4))
        pts.append(Point(x, y, t))
    pts[0] = Point(0.0, pts[0].y, 0.0)
    pts[-1] = Point(float(distance), pts[-1].y, float(duration_ms))
    return pts


def analyze(points: list[Point]) -> dict[str, float | str]:
    if len(points) < 3:
        return {"verdict": "insufficient_data", "score": 0.0}
    speeds, dts, distances = [], [], []
    for a, b in zip(points, points[1:]):
        dt = max((b.t - a.t) / 1000.0, 1e-6)
        dist = math.hypot(b.x - a.x, b.y - a.y)
        speeds.append(dist / dt)
        dts.append(dt * 1000)
        distances.append(dist)
    accels = [(b - a) for a, b in zip(speeds, speeds[1:])]
    jerks = [(b - a) for a, b in zip(accels, accels[1:])]
    x_span = abs(points[-1].x - points[0].x)
    path_len = sum(distances)
    y_values = [p.y for p in points]
    y_range = max(y_values) - min(y_values)
    duration = points[-1].t - points[0].t
    pause_count = sum(1 for dt in dts if dt > 45)
    speed_std = statistics.pstdev(speeds) if len(speeds) > 1 else 0.0
    accel_std = statistics.pstdev(accels) if len(accels) > 1 else 0.0
    jerk_std = statistics.pstdev(jerks) if len(jerks) > 1 else 0.0
    interval_std = statistics.pstdev(dts) if len(dts) > 1 else 0.0
    path_ratio = path_len / max(x_span, 1.0)

    score = 100.0
    if duration < 250 or duration > 3500: score -= 20
    if path_ratio < 1.002: score -= 20
    if y_range < 1.2: score -= 15
    if interval_std < 1.0: score -= 15
    if speed_std < 20: score -= 15
    if max(speeds) > 5000: score -= 15
    if pause_count == 0 and duration > 700: score -= 5
    if jerk_std == 0: score -= 10
    score = max(0.0, min(100.0, score))
    verdict = "natural_like_for_local_lab" if score >= 75 else "mixed_or_needs_review" if score >= 45 else "mechanical_or_anomalous"
    return {
        "verdict": verdict, "score": round(score, 2), "points": len(points),
        "duration_ms": round(duration, 3), "x_span": round(x_span, 3),
        "path_length": round(path_len, 3), "path_ratio": round(path_ratio, 5),
        "y_range": round(y_range, 3), "avg_speed_px_s": round(statistics.mean(speeds), 3),
        "max_speed_px_s": round(max(speeds), 3), "speed_std": round(speed_std, 3),
        "accel_std": round(accel_std, 3), "jerk_std": round(jerk_std, 3),
        "interval_std_ms": round(interval_std, 3), "pause_count": pause_count,
    }


def read_csv_points(path: str) -> list[Point]:
    pts: list[Point] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pts.append(Point(float(row["x"]), float(row["y"]), float(row.get("t_ms", row.get("t", 0)))))
    if pts:
        t0 = pts[0].t
        x0 = pts[0].x
        y0 = pts[0].y
        pts = [Point(p.x - x0, p.y - y0, p.t - t0) for p in pts]
    return pts


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Slider Trajectory Lab")
        self.geometry("1100x740")
        self.points: list[Point] = []
        self.record_points: list[Point] = []
        self.recording = False
        self.record_t0 = 0.0
        self._build_ui()
        self.generate()

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        self.tab_gen = ttk.Frame(nb, padding=10)
        self.tab_rec = ttk.Frame(nb, padding=10)
        self.tab_about = ttk.Frame(nb, padding=10)
        nb.add(self.tab_gen, text="轨迹生成与分析")
        nb.add(self.tab_rec, text="人工轨迹记录")
        nb.add(self.tab_about, text="说明")
        self._build_gen_tab()
        self._build_record_tab()
        self._build_about_tab()

    def _build_gen_tab(self):
        left = ttk.Frame(self.tab_gen, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = ttk.Frame(self.tab_gen, padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="参数", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        self.distance = tk.IntVar(value=320)
        self.duration = tk.IntVar(value=900)
        self.steps = tk.IntVar(value=80)
        self.jitter = tk.DoubleVar(value=1.5)
        for text, var, frm, to in [("滑动距离 px", self.distance, 80, 800), ("持续时间 ms", self.duration, 200, 2500), ("轨迹点数量", self.steps, 10, 240)]:
            ttk.Label(left, text=text).pack(anchor="w")
            ttk.Spinbox(left, from_=frm, to=to, textvariable=var, width=18).pack(anchor="w", pady=(0, 8))
        ttk.Label(left, text="抖动强度").pack(anchor="w")
        ttk.Spinbox(left, from_=0.0, to=8.0, increment=0.1, textvariable=self.jitter, width=18).pack(anchor="w", pady=(0, 12))
        ttk.Button(left, text="生成轨迹", command=self.generate).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="导入 CSV 分析", command=self.import_csv).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="分析当前轨迹", command=self.show_analysis).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="导出 CSV", command=self.export_csv).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="导出 PNG 图", command=self.export_png).pack(fill=tk.X, pady=4)
        ttk.Separator(left).pack(fill=tk.X, pady=12)
        self.output = tk.Text(left, width=36, height=28)
        self.output.pack(fill=tk.BOTH, expand=True)

        if plt and FigureCanvasTkAgg:
            self.fig, self.axes = plt.subplots(3, 1, figsize=(7.8, 6.5), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.fig, master=right)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(right, text="未安装 matplotlib，无法显示图表。请运行：pip install matplotlib").pack()

    def _build_record_tab(self):
        top = ttk.Frame(self.tab_rec)
        top.pack(fill=tk.X)
        ttk.Button(top, text="开始记录", command=self.start_record).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="停止记录", command=self.stop_record).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="使用记录结果分析", command=self.use_recorded).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="保存记录 CSV", command=self.save_record_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="清空", command=self.clear_record).pack(side=tk.LEFT, padx=4)
        self.rec_status = ttk.Label(top, text="点击开始记录，然后在画布内拖动鼠标。")
        self.rec_status.pack(side=tk.LEFT, padx=16)
        self.rec_canvas = tk.Canvas(self.tab_rec, bg="#f8fafc")
        self.rec_canvas.pack(fill=tk.BOTH, expand=True, pady=10)
        self.rec_canvas.bind("<Motion>", self.on_record_move)
        self.rec_canvas.bind("<ButtonPress-1>", self.on_record_down)
        self.rec_canvas.bind("<ButtonRelease-1>", self.on_record_up)

    def _build_about_tab(self):
        text = tk.Text(self.tab_about, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, "Slider Trajectory Lab\n\n")
        text.insert(tk.END, "用途：本地滑块交互、鼠标轨迹生成、人工轨迹记录、轨迹可视化与防御型分析。\n\n")
        text.insert(tk.END, "参考方向：automation-detection、bot-detection、mouse-trajectory、FingerprintJS BotD 等公开项目/主题。\n\n")
        text.insert(tk.END, "建议流程：\n1. 在“人工轨迹记录”里手动拖动并保存 CSV。\n2. 回到“轨迹生成与分析”导入 CSV。\n3. 查看轨迹、速度、加速度和评分。\n4. 调整生成参数，与人工轨迹做本地对比。\n")
        text.config(state=tk.DISABLED)

    def generate(self):
        self.points = generate_trajectory(self.distance.get(), self.duration.get(), self.steps.get(), self.jitter.get())
        self.plot()
        self.show_analysis()

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if not path: return
        try:
            self.points = read_csv_points(path)
            self.plot(); self.show_analysis()
            messagebox.showinfo("完成", f"已导入：{path}")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def show_analysis(self):
        m = analyze(self.points)
        self.output.delete("1.0", tk.END)
        title = "分析结果\n" + "=" * 24 + "\n"
        self.output.insert(tk.END, title)
        for k, v in m.items():
            self.output.insert(tk.END, f"{k}: {v}\n")
        self.output.insert(tk.END, "\n评分说明：该分数只用于本地实验和防御研究，用来发现过直、过匀速、间隔过机械等轨迹特征。\n")

    def plot(self):
        if not (plt and FigureCanvasTkAgg): return
        ax1, ax2, ax3 = self.axes
        for ax in self.axes: ax.clear()
        if not self.points: return
        xs = [p.x for p in self.points]; ys = [p.y for p in self.points]; ts = [p.t for p in self.points]
        speeds = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            dt = max((b.t - a.t) / 1000.0, 1e-6)
            speeds.append(math.hypot(b.x - a.x, b.y - a.y) / dt)
        accels = [0.0] + [(b - a) for a, b in zip(speeds, speeds[1:])]
        ax1.plot(xs, ys, marker="o", markersize=2); ax1.set_title("Trajectory path"); ax1.set_xlabel("x / px"); ax1.set_ylabel("y / px"); ax1.grid(True, alpha=.25)
        ax2.plot(ts, speeds); ax2.set_title("Speed curve"); ax2.set_xlabel("time / ms"); ax2.set_ylabel("px/s"); ax2.grid(True, alpha=.25)
        ax3.plot(ts, accels); ax3.set_title("Acceleration delta curve"); ax3.set_xlabel("time / ms"); ax3.set_ylabel("delta px/s"); ax3.grid(True, alpha=.25)
        self.fig.tight_layout(); self.canvas.draw()

    def export_csv(self):
        if not self.points: return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path: self._write_points(path, self.points)

    def export_png(self):
        if not hasattr(self, "fig"):
            messagebox.showerror("缺少依赖", "需要安装 matplotlib"); return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            self.fig.savefig(path, dpi=160); messagebox.showinfo("完成", f"已导出：{path}")

    def _write_points(self, path: str, pts: list[Point]):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["x", "y", "t_ms"])
            for p in pts: writer.writerow([round(p.x, 3), round(p.y, 3), round(p.t, 3)])
        messagebox.showinfo("完成", f"已保存：{path}")

    def start_record(self):
        self.record_points.clear(); self.rec_canvas.delete("all")
        self.record_t0 = time.perf_counter(); self.recording = True
        self.rec_status.config(text="记录中：按住鼠标左键拖动。")

    def stop_record(self):
        self.recording = False
        self.rec_status.config(text=f"已停止，记录点数：{len(self.record_points)}")

    def clear_record(self):
        self.record_points.clear(); self.rec_canvas.delete("all")
        self.rec_status.config(text="已清空。")

    def on_record_down(self, event):
        if not self.recording: self.start_record()
        self._add_record(event.x, event.y)

    def on_record_up(self, event):
        if self.recording:
            self._add_record(event.x, event.y); self.stop_record()

    def on_record_move(self, event):
        if self.recording: self._add_record(event.x, event.y)

    def _add_record(self, x: float, y: float):
        t = (time.perf_counter() - self.record_t0) * 1000
        if self.record_points:
            p = self.record_points[-1]
            self.rec_canvas.create_line(p.x, p.y, x, y, fill="#2563eb", width=2)
        self.record_points.append(Point(float(x), float(y), t))
        self.rec_status.config(text=f"记录中，点数：{len(self.record_points)}")

    def use_recorded(self):
        if not self.record_points:
            messagebox.showwarning("没有数据", "请先记录轨迹。") ; return
        x0, y0, t0 = self.record_points[0].x, self.record_points[0].y, self.record_points[0].t
        self.points = [Point(p.x - x0, p.y - y0, p.t - t0) for p in self.record_points]
        self.plot(); self.show_analysis()
        messagebox.showinfo("完成", "已把人工记录轨迹载入分析页。")

    def save_record_csv(self):
        if not self.record_points:
            messagebox.showwarning("没有数据", "请先记录轨迹。") ; return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path: self._write_points(path, self.record_points)


if __name__ == "__main__":
    App().mainloop()
