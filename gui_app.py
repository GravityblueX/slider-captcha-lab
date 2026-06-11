"""Desktop GUI for local slider trajectory analysis.

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
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:  # matplotlib is optional until plotting is used
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


def metrics(points: list[Point]) -> dict[str, float]:
    if len(points) < 2:
        return {}
    speeds = []
    accels = []
    for a, b in zip(points, points[1:]):
        dt = max((b.t - a.t) / 1000.0, 1e-6)
        dist = math.hypot(b.x - a.x, b.y - a.y)
        speeds.append(dist / dt)
    for a, b in zip(speeds, speeds[1:]):
        accels.append(b - a)
    total_distance = sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(points, points[1:]))
    straight = abs(points[-1].x - points[0].x)
    return {
        "points": len(points),
        "duration_ms": points[-1].t - points[0].t,
        "x_distance": straight,
        "path_length": total_distance,
        "path_ratio": total_distance / max(straight, 1),
        "avg_speed_px_s": statistics.mean(speeds),
        "max_speed_px_s": max(speeds),
        "speed_std": statistics.pstdev(speeds),
        "accel_std": statistics.pstdev(accels) if accels else 0.0,
        "y_range": max(p.y for p in points) - min(p.y for p in points),
    }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Slider Trajectory Lab")
        self.geometry("980x680")
        self.points: list[Point] = []
        self._build_ui()
        self.generate()

    def _build_ui(self):
        left = ttk.Frame(self, padding=12)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = ttk.Frame(self, padding=12)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="参数", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        self.distance = tk.IntVar(value=320)
        self.duration = tk.IntVar(value=900)
        self.steps = tk.IntVar(value=80)
        self.jitter = tk.DoubleVar(value=1.5)
        for text, var, frm, to in [
            ("滑动距离 px", self.distance, 80, 800),
            ("持续时间 ms", self.duration, 200, 2500),
            ("轨迹点数量", self.steps, 10, 200),
        ]:
            ttk.Label(left, text=text).pack(anchor="w")
            ttk.Spinbox(left, from_=frm, to=to, textvariable=var, width=16).pack(anchor="w", pady=(0, 8))
        ttk.Label(left, text="抖动强度").pack(anchor="w")
        ttk.Spinbox(left, from_=0.0, to=8.0, increment=0.1, textvariable=self.jitter, width=16).pack(anchor="w", pady=(0, 12))

        ttk.Button(left, text="生成轨迹", command=self.generate).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="分析轨迹", command=self.analyze).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="导出 CSV", command=self.export_csv).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="导出 PNG 图", command=self.export_png).pack(fill=tk.X, pady=4)
        ttk.Separator(left).pack(fill=tk.X, pady=12)
        ttk.Label(left, text="说明：本工具用于本地轨迹生成、可视化和交互分析。", wraplength=210).pack(anchor="w")

        self.output = tk.Text(left, width=32, height=20)
        self.output.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        if plt and FigureCanvasTkAgg:
            self.fig, self.axes = plt.subplots(2, 1, figsize=(7.2, 5.8), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.fig, master=right)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(right, text="未安装 matplotlib，无法显示图表。请运行：pip install matplotlib").pack()

    def generate(self):
        self.points = generate_trajectory(self.distance.get(), self.duration.get(), self.steps.get(), self.jitter.get())
        self.plot()
        self.analyze()

    def analyze(self):
        m = metrics(self.points)
        self.output.delete("1.0", tk.END)
        for k, v in m.items():
            self.output.insert(tk.END, f"{k}: {v:.3f}\n" if isinstance(v, float) else f"{k}: {v}\n")

    def plot(self):
        if not (plt and FigureCanvasTkAgg):
            return
        ax1, ax2 = self.axes
        ax1.clear(); ax2.clear()
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        ts = [p.t for p in self.points]
        speeds = [0]
        for a, b in zip(self.points, self.points[1:]):
            dt = max((b.t - a.t) / 1000.0, 1e-6)
            speeds.append(math.hypot(b.x - a.x, b.y - a.y) / dt)
        ax1.plot(xs, ys, marker="o", markersize=2)
        ax1.set_title("Trajectory path")
        ax1.set_xlabel("x / px"); ax1.set_ylabel("y / px")
        ax1.grid(True, alpha=.25)
        ax2.plot(ts, speeds)
        ax2.set_title("Speed curve")
        ax2.set_xlabel("time / ms"); ax2.set_ylabel("px/s")
        ax2.grid(True, alpha=.25)
        self.fig.tight_layout()
        self.canvas.draw()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["x", "y", "t_ms"])
            for p in self.points:
                writer.writerow([round(p.x, 3), round(p.y, 3), round(p.t, 3)])
        messagebox.showinfo("完成", f"已导出：{path}")

    def export_png(self):
        if not hasattr(self, "fig"):
            messagebox.showerror("缺少依赖", "需要安装 matplotlib")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            self.fig.savefig(path, dpi=160)
            messagebox.showinfo("完成", f"已导出：{path}")


if __name__ == "__main__":
    App().mainloop()
