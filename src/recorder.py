from __future__ import annotations

import csv
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

@dataclass
class Point:
    x: float
    y: float
    t: float

class Recorder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local Mouse Trajectory Recorder")
        self.geometry("760x420")
        self.points: list[Point] = []
        self.t0 = 0.0
        self.recording = False
        self.canvas = tk.Canvas(self, bg="#f8fafc")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(bar, text="开始记录", command=self.start).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="停止记录", command=self.stop).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="保存 CSV", command=self.save_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="清空", command=self.clear).pack(side=tk.LEFT, padx=4)
        self.status = ttk.Label(bar, text="点击开始记录，然后在白色区域内拖动鼠标。")
        self.status.pack(side=tk.LEFT, padx=16)
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)

    def start(self):
        self.points.clear()
        self.canvas.delete("all")
        self.t0 = time.perf_counter()
        self.recording = True
        self.status.config(text="记录中：移动或拖动鼠标。")

    def stop(self):
        self.recording = False
        self.status.config(text=f"已停止，记录点数：{len(self.points)}")

    def clear(self):
        self.points.clear()
        self.canvas.delete("all")
        self.status.config(text="已清空。")

    def on_down(self, event):
        if not self.recording:
            self.start()
        self._add(event.x, event.y)

    def on_up(self, event):
        self._add(event.x, event.y)
        self.stop()

    def on_move(self, event):
        if self.recording:
            self._add(event.x, event.y)

    def _add(self, x, y):
        t = (time.perf_counter() - self.t0) * 1000
        if self.points:
            p = self.points[-1]
            self.canvas.create_line(p.x, p.y, x, y, fill="#2563eb", width=2)
        self.points.append(Point(float(x), float(y), t))
        self.status.config(text=f"记录中，点数：{len(self.points)}")

    def save_csv(self):
        if not self.points:
            messagebox.showwarning("没有数据", "请先记录轨迹。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["x", "y", "t_ms"])
            for p in self.points:
                writer.writerow([round(p.x, 3), round(p.y, 3), round(p.t, 3)])
        messagebox.showinfo("完成", f"已保存：{path}")

if __name__ == "__main__":
    Recorder().mainloop()
