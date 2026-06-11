from __future__ import annotations
import math, random
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
    t: float

def _bezier(p0, p1, p2, p3, u):
    return (1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u**2*p2 + u**3*p3

def generate_trajectory(start=(0, 0), end=(300, 0), duration_ms=900, steps=70, jitter=1.6):
    """Generate a human-like drag path for local UI testing only."""
    sx, sy = start; ex, ey = end; dx = ex - sx
    c1 = (sx + dx * 0.28, sy + random.uniform(-18, 18))
    c2 = (sx + dx * 0.72, ey + random.uniform(-18, 18))
    pts = []
    for i in range(steps):
        u = i / (steps - 1)
        eased = 0.5 - 0.5 * math.cos(math.pi * u)
        x = _bezier(sx, c1[0], c2[0], ex, eased) + random.gauss(0, jitter)
        y = _bezier(sy, c1[1], c2[1], ey, eased) + random.gauss(0, jitter)
        t = max(0, duration_ms * eased + random.uniform(-3, 3))
        pts.append(Point(x, y, t))
    return pts
