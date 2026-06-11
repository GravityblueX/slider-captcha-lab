from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
    t: float


def _segments(points: list[Point]):
    for a, b in zip(points, points[1:]):
        dt = max((b.t - a.t) / 1000.0, 1e-6)
        dx = b.x - a.x
        dy = b.y - a.y
        dist = math.hypot(dx, dy)
        yield a, b, dt, dx, dy, dist


def analyze(points: list[Point]) -> dict[str, float | str]:
    """Analyze a drag trajectory for local QA and defensive research.

    The scoring is intentionally heuristic. It helps compare generated/local
    trajectories and identify obviously mechanical patterns in authorized tests.
    """
    if len(points) < 3:
        return {"verdict": "insufficient_data", "score": 0.0}

    speeds = []
    angles = []
    dts = []
    distances = []
    for _, _, dt, dx, dy, dist in _segments(points):
        speeds.append(dist / dt)
        dts.append(dt * 1000)
        distances.append(dist)
        if dist > 1e-6:
            angles.append(math.atan2(dy, dx))

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

    # Heuristic defensive quality score. Penalizes overly straight, perfectly
    # uniform, or physically implausible traces; rewards moderate variation.
    score = 100.0
    if duration < 250 or duration > 3500:
        score -= 20
    if path_ratio < 1.002:
        score -= 20
    if y_range < 1.2:
        score -= 15
    if interval_std < 1.0:
        score -= 15
    if speed_std < 20:
        score -= 15
    if max(speeds) > 5000:
        score -= 15
    if pause_count == 0 and duration > 700:
        score -= 5
    if jerk_std == 0:
        score -= 10
    score = max(0.0, min(100.0, score))

    if score >= 75:
        verdict = "natural_like_for_local_lab"
    elif score >= 45:
        verdict = "mixed_or_needs_review"
    else:
        verdict = "mechanical_or_anomalous"

    return {
        "verdict": verdict,
        "score": round(score, 2),
        "points": len(points),
        "duration_ms": round(duration, 3),
        "x_span": round(x_span, 3),
        "path_length": round(path_len, 3),
        "path_ratio": round(path_ratio, 5),
        "y_range": round(y_range, 3),
        "avg_speed_px_s": round(statistics.mean(speeds), 3),
        "max_speed_px_s": round(max(speeds), 3),
        "speed_std": round(speed_std, 3),
        "accel_std": round(accel_std, 3),
        "jerk_std": round(jerk_std, 3),
        "interval_std_ms": round(interval_std, 3),
        "pause_count": pause_count,
    }
