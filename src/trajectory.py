from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

@dataclass
class Point:
    x: float
    y: float
    t: float

Mode = Literal["normal", "careful", "fast", "hesitant"]

def _bezier(p0: float, p1: float, p2: float, p3: float, u: float) -> float:
    return (1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u**2*p2 + u**3*p3

def _ease(u: float, mode: Mode) -> float:
    # Human drags usually accelerate, stabilize, then decelerate.
    if mode == "fast":
        return 1 - (1 - u) ** 2.2
    if mode == "careful":
        return 0.5 - 0.5 * math.cos(math.pi * u)
    if mode == "hesitant":
        base = 0.5 - 0.5 * math.cos(math.pi * u)
        return max(0.0, min(1.0, base + 0.018 * math.sin(8 * math.pi * u)))
    return 0.5 - 0.5 * math.cos(math.pi * u)

def generate_trajectory(
    start=(0, 0),
    end=(300, 0),
    duration_ms: int = 900,
    steps: int = 80,
    jitter: float = 1.5,
    mode: Mode = "normal",
    overshoot: bool = True,
    micro_pause: bool = True,
) -> list[Point]:
    """Generate a human-like drag path for local/authorized UI testing.

    Features:
    - Bezier backbone
    - easing-based speed profile
    - hand tremor jitter
    - optional micro pauses
    - optional slight overshoot and correction

    This module is intended for local labs, accessibility testing, QA automation,
    and defensive behavior-analysis experiments.
    """
    sx, sy = map(float, start)
    ex, ey = map(float, end)
    dx = ex - sx
    dy = ey - sy

    if mode == "fast":
        duration_ms = int(duration_ms * random.uniform(0.72, 0.9))
        jitter *= 1.15
    elif mode == "careful":
        duration_ms = int(duration_ms * random.uniform(1.1, 1.35))
        jitter *= 0.85
    elif mode == "hesitant":
        duration_ms = int(duration_ms * random.uniform(1.2, 1.55))
        jitter *= 1.35

    # Target may slightly overshoot then come back, common in manual dragging.
    final_ex, final_ey = ex, ey
    if overshoot and abs(dx) > 120 and random.random() < 0.72:
        ex = ex + random.uniform(3, min(18, abs(dx) * 0.045)) * (1 if dx >= 0 else -1)
        ey = ey + random.uniform(-2.5, 2.5)

    c1 = (sx + dx * random.uniform(0.22, 0.35), sy + dy * 0.25 + random.uniform(-24, 24))
    c2 = (sx + dx * random.uniform(0.62, 0.82), sy + dy * 0.75 + random.uniform(-24, 24))

    pts: list[Point] = []
    steps = max(8, steps)
    pause_at = set()
    if micro_pause:
        pause_count = {"fast": 0, "normal": 1, "careful": 2, "hesitant": 3}.get(mode, 1)
        for _ in range(pause_count):
            pause_at.add(random.randint(max(2, steps // 5), max(3, steps - steps // 6)))

    time_offset = 0.0
    last_x, last_y = sx, sy
    for i in range(steps):
        u = i / (steps - 1)
        e = _ease(u, mode)
        x = _bezier(sx, c1[0], c2[0], ex, e)
        y = _bezier(sy, c1[1], c2[1], ey, e)

        # Fine motor tremor: stronger in the middle, weaker at endpoints.
        tremor = math.sin(math.pi * u)
        x += random.gauss(0, jitter * tremor)
        y += random.gauss(0, jitter * tremor)

        # Avoid perfectly uniform increments.
        if i > 0 and random.random() < 0.18:
            x = last_x + (x - last_x) * random.uniform(0.82, 1.08)
            y = last_y + (y - last_y) * random.uniform(0.82, 1.12)

        if i in pause_at:
            time_offset += random.uniform(35, 130)

        t = duration_ms * e + time_offset + random.uniform(-5, 5)
        pts.append(Point(x, y, max(0.0, t)))
        last_x, last_y = x, y

    # Correction segment after overshoot.
    if overshoot and (abs(ex - final_ex) > 0.5 or abs(ey - final_ey) > 0.5):
        correction_steps = random.randint(4, 9)
        base_t = pts[-1].t
        ox, oy = pts[-1].x, pts[-1].y
        for j in range(1, correction_steps + 1):
            u = j / correction_steps
            e = 0.5 - 0.5 * math.cos(math.pi * u)
            pts.append(Point(
                ox + (final_ex - ox) * e + random.gauss(0, jitter * 0.25),
                oy + (final_ey - oy) * e + random.gauss(0, jitter * 0.25),
                base_t + 35 * j + random.uniform(-4, 4),
            ))

    pts[0] = Point(sx, sy, 0.0)
    pts[-1] = Point(final_ex, final_ey, max(pts[-1].t, duration_ms))

    # Ensure monotonic timestamps.
    fixed: list[Point] = []
    last_t = -1.0
    for p in pts:
        t = max(p.t, last_t + random.uniform(4, 18))
        fixed.append(Point(p.x, p.y, t))
        last_t = t
    fixed[0] = Point(sx, sy, 0.0)
    return fixed
