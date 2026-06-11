from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

try:
    from trajectory import generate_trajectory, Point
except Exception:
    from src.trajectory import generate_trajectory, Point

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class ActionLog:
    action: str
    ok: bool
    elapsed_ms: float
    detail: str


def _resolve_url(url: str) -> str:
    if url.startswith(("http://", "https://", "file://")):
        return url
    return (ROOT / url).resolve().as_uri()


def _sleep_ms(page, ms: int, jitter: float = 0.18):
    real = max(1, int(ms * random.uniform(1 - jitter, 1 + jitter)))
    page.wait_for_timeout(real)


def _move_path(page, path: list[Point]):
    if not path:
        return
    page.mouse.move(path[0].x, path[0].y)
    last = path[0].t
    for p in path[1:]:
        page.wait_for_timeout(max(1, int(p.t - last)))
        page.mouse.move(p.x, p.y)
        last = p.t


def mouse_wander(page, duration_ms: int = 1200, box: dict[str, float] | None = None):
    vp = page.viewport_size or {"width": 1200, "height": 800}
    if box is None:
        box = {"x": 40, "y": 80, "width": vp["width"] - 80, "height": vp["height"] - 140}
    start = (random.uniform(box["x"], box["x"] + box["width"]), random.uniform(box["y"], box["y"] + box["height"]))
    hops = random.randint(2, 5)
    remain = duration_ms
    page.mouse.move(start[0], start[1])
    cur = start
    for i in range(hops):
        end = (random.uniform(box["x"], box["x"] + box["width"]), random.uniform(box["y"], box["y"] + box["height"]))
        seg_ms = max(120, int(remain / (hops - i) * random.uniform(0.75, 1.2)))
        remain -= seg_ms
        path = generate_trajectory(cur, end, duration_ms=seg_ms, steps=random.randint(24, 55), jitter=random.uniform(0.6, 1.7), mode=random.choice(["normal", "careful", "hesitant"]), overshoot=False, micro_pause=True)
        _move_path(page, path)
        cur = end


def human_scroll(page, amount: int = 600, steps: int | None = None):
    steps = steps or random.randint(5, 12)
    remaining = amount
    for i in range(steps):
        delta = int(remaining / (steps - i) * random.uniform(0.55, 1.35))
        remaining -= delta
        page.mouse.wheel(0, delta)
        page.wait_for_timeout(random.randint(45, 180))


def human_click(page, selector: str):
    loc = page.locator(selector)
    loc.wait_for(state="visible", timeout=10000)
    box = loc.bounding_box()
    if not box:
        raise RuntimeError(f"Cannot get bounding box for selector: {selector}")
    target = (box["x"] + random.uniform(box["width"] * 0.25, box["width"] * 0.75), box["y"] + random.uniform(box["height"] * 0.25, box["height"] * 0.75))
    vp = page.viewport_size or {"width": 1200, "height": 800}
    start = (random.uniform(20, vp["width"] - 20), random.uniform(80, vp["height"] - 40))
    path = generate_trajectory(start, target, duration_ms=random.randint(350, 950), steps=random.randint(35, 85), jitter=random.uniform(0.7, 1.8), mode=random.choice(["normal", "careful", "hesitant"]), overshoot=random.random() < 0.35, micro_pause=True)
    _move_path(page, path)
    page.wait_for_timeout(random.randint(80, 260))
    page.mouse.down()
    page.wait_for_timeout(random.randint(35, 120))
    page.mouse.up()


def human_fill(page, selector: str, text: str):
    human_click(page, selector)
    for ch in text:
        page.keyboard.type(ch)
        page.wait_for_timeout(random.randint(35, 180))
        if random.random() < 0.035:
            page.wait_for_timeout(random.randint(180, 520))


def run_session(profile_path: str, headless: bool = False) -> dict[str, Any]:
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    if profile.get("authorized_only") is not True:
        raise ValueError("Profile must set authorized_only=true. Only local/owned/authorized pages are supported.")
    url = _resolve_url(profile["url"])
    actions = profile.get("actions", [])
    logs: list[ActionLog] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport=profile.get("viewport", {"width": 1280, "height": 850}))
        t0 = time.perf_counter()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            logs.append(ActionLog("goto", True, round((time.perf_counter() - t0) * 1000, 2), url))
            for action in actions:
                at = time.perf_counter()
                typ = action.get("type")
                try:
                    if typ == "dwell":
                        _sleep_ms(page, int(action.get("ms", 1000)))
                    elif typ == "mouse_wander":
                        mouse_wander(page, int(action.get("duration_ms", 1200)), action.get("box"))
                    elif typ == "scroll":
                        human_scroll(page, int(action.get("amount", 600)), action.get("steps"))
                    elif typ == "click":
                        human_click(page, action["selector"])
                    elif typ == "fill":
                        human_fill(page, action["selector"], action.get("text", ""))
                    elif typ == "wait_for":
                        page.wait_for_selector(action["selector"], timeout=int(action.get("timeout", 10000)))
                    else:
                        raise ValueError(f"Unknown action type: {typ}")
                    logs.append(ActionLog(str(typ), True, round((time.perf_counter() - at) * 1000, 2), json.dumps(action, ensure_ascii=False)))
                except Exception as e:
                    logs.append(ActionLog(str(typ), False, round((time.perf_counter() - at) * 1000, 2), str(e)))
                    if action.get("required", True):
                        break
        finally:
            browser.close()
    return {
        "profile": profile.get("name", profile_path),
        "url": profile.get("url"),
        "summary": {"total": len(logs), "ok": sum(1 for x in logs if x.ok), "failed": sum(1 for x in logs if not x.ok)},
        "logs": [asdict(x) for x in logs],
        "scope": "local_owned_or_explicitly_authorized_pages_only",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run authorized human-like browsing session profile")
    parser.add_argument("profile", help="Path to authorized session profile JSON")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_session(args.profile, headless=args.headless), ensure_ascii=False, indent=2))
