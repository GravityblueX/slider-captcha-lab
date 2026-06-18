from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

try:
    from browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms
    from trajectory import generate_trajectory
except Exception:
    from src.browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms
    from src.trajectory import generate_trajectory

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class AttemptResult:
    mode: str
    ok: bool
    reason: str
    duration_ms: float
    score_hint: str


def _resolve_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://") or url.startswith("file://"):
        return url
    p = (ROOT / url).resolve()
    return p.as_uri()


def run_profile(profile_path: str, headless: bool = False, require_authorized_flag: bool = True) -> dict[str, Any]:
    """Run a configurable test against a local/owned/authorized page.

    This helper is designed for QA and authorized testing. A profile must include
    `authorized_only: true` to make the intended scope explicit.
    """
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    if require_authorized_flag and profile.get("authorized_only") is not True:
        raise ValueError("Profile must set authorized_only=true. Only local/owned/authorized pages are supported.")

    url = _resolve_url(profile["url"])
    slider_selector = profile.get("slider_selector", "#slider")
    knob_selector = profile.get("knob_selector", "#knob")
    success_selector = profile.get("success_selector")
    success_text_contains = profile.get("success_text_contains", "")
    modes = profile.get("modes", [profile.get("mode", "normal")])
    results: list[AttemptResult] = []

    with sync_playwright() as p:
        context, browser = launch_browser_context(p, profile, headless=headless, viewport={"width": 1100, "height": 760})
        try:
            manual_page = None
            if manual_navigation_enabled(profile):
                manual_page = context.pages[-1] if context.pages else context.new_page()
                manual_page.goto(url, wait_until="domcontentloaded", timeout=15000)
                wait_ms = manual_wait_ms(profile)
                if wait_ms > 0:
                    manual_page.wait_for_timeout(wait_ms)
                if context.pages:
                    manual_page = context.pages[-1]
            for mode in modes:
                page = manual_page or context.new_page()
                start_time = time.perf_counter()
                ok = False
                reason = "unknown"
                try:
                    if manual_page is None:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_selector(knob_selector, timeout=8000)
                    page.wait_for_selector(slider_selector, timeout=8000)
                    knob = page.locator(knob_selector).bounding_box()
                    slider = page.locator(slider_selector).bounding_box()
                    if not knob or not slider:
                        raise RuntimeError("Cannot locate slider or knob bounding box")
                    start = (knob["x"] + knob["width"] / 2, knob["y"] + knob["height"] / 2)
                    distance = float(profile.get("distance") or (slider["width"] - knob["width"] - 10))
                    end = (start[0] + distance, start[1])
                    path = generate_trajectory(
                        start=start,
                        end=end,
                        duration_ms=int(profile.get("duration_ms", 900)),
                        steps=int(profile.get("steps", 90)),
                        jitter=float(profile.get("jitter", 1.6)),
                        mode=mode,
                        overshoot=bool(profile.get("overshoot", True)),
                        micro_pause=bool(profile.get("micro_pause", True)),
                    )
                    page.mouse.move(path[0].x, path[0].y)
                    page.mouse.down()
                    last_t = 0
                    for pt in path[1:]:
                        page.wait_for_timeout(max(1, int(pt.t - last_t)))
                        page.mouse.move(pt.x, pt.y)
                        last_t = pt.t
                    page.mouse.up()
                    page.wait_for_timeout(500)
                    if success_selector:
                        text = page.locator(success_selector).inner_text(timeout=2000)
                        ok = success_text_contains.lower() in text.lower() if success_text_contains else bool(text)
                        reason = f"success_selector text={text!r}"
                    else:
                        ok = True
                        reason = "no success selector configured; drag sequence completed"
                except Exception as e:
                    ok = False
                    reason = str(e)
                finally:
                    duration = (time.perf_counter() - start_time) * 1000
                    results.append(AttemptResult(mode, ok, reason, round(duration, 2), "local/authorized profile test"))
                    if manual_page is None:
                        page.close()
        finally:
            close_browser_context(context, browser)
    return {
        "profile": profile.get("name", profile_path),
        "url": profile.get("url"),
        "results": [r.__dict__ for r in results],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
        },
        "scope": "local_owned_or_authorized_pages_only",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run authorized configurable slider test profile")
    parser.add_argument("profile", help="Path to profile json")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_profile(args.profile, headless=args.headless), ensure_ascii=False, indent=2))
