from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from liuhen import TOOLS
from src.analyzer import analyze
from src.trajectory import generate_trajectory

REQUIRED_FILES = [
    "README.md",
    "DISCLAIMER.md",
    "requirements.txt",
    "demo/index.html",
    "demo/slider.js",
    "demo/event_diagnostics.html",
    "demo/event_diagnostics.js",
    "src/trajectory.py",
    "src/analyzer.py",
    "src/browser_context.py",
    "src/page_probe.py",
    "src/page_targets.py",
    "src/human_behavior.py",
    "src/risk_analyzer.py",
    "src/network_diagnostics.py",
]

OPTIONAL_MODULES = ["matplotlib", "playwright", "pandas", "PyInstaller"]


def module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    missing_files = [name for name in REQUIRED_FILES if not (ROOT / name).exists()]
    missing_tools = [
        f"{name}: {info['script']}"
        for name, info in TOOLS.items()
        if not (ROOT / info["script"]).exists()
    ]

    points = generate_trajectory((0, 0), (320, 0), duration_ms=900, steps=90)
    metrics = analyze(points)
    trajectory_ok = (
        len(points) >= 8
        and points[0].t == 0
        and points[-1].t >= 900
        and metrics.get("score", 0) > 0
    )

    result = {
        "ok": not missing_files and not missing_tools and trajectory_ok,
        "missing_files": missing_files,
        "missing_tools": missing_tools,
        "trajectory": {
            "ok": trajectory_ok,
            "points": len(points),
            "score": metrics.get("score"),
            "verdict": metrics.get("verdict"),
        },
        "optional_modules": {name: module_exists(name) for name in OPTIONAL_MODULES},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
