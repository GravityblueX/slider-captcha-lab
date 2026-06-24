from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.browser_context import close_browser_context, launch_browser_context

DEFAULT_PROFILE = ROOT / "examples" / "authorized_deep_page_profile.json"
DEFAULT_DIR = ROOT / "docs" / "trace-artifacts"
DEFAULT_JSON = DEFAULT_DIR / "local-demo-trace.json"
DEFAULT_MARKDOWN = DEFAULT_DIR / "local-demo-trace.md"
DEFAULT_SCREENSHOT = DEFAULT_DIR / "local-demo.png"
SCOPE = "local_owned_or_explicitly_authorized_pages_only"


def load_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_url(url: str) -> str:
    if url.startswith(("http://localhost", "http://127.0.0.1", "file:")):
        return url
    return (ROOT / url).resolve().as_uri()


def selector_boxes(page, selectors: list[str]) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            box = locator.bounding_box(timeout=1500)
        except Exception:
            box = None
        boxes.append({
            "selector": selector,
            "visible": bool(box),
            "box": box,
        })
    return boxes


def run_trace(profile_path: Path, screenshot_path: Path, headless: bool = True) -> dict[str, Any]:
    profile = load_profile(profile_path)
    if profile.get("authorized_only") is not True:
        raise ValueError("profile must set authorized_only=true")

    url = str(profile.get("url", ""))
    if url.startswith(("http://", "https://")) and not url.startswith(("http://localhost", "http://127.0.0.1")):
        raise ValueError("trace artifacts only support local demo or localhost targets")

    from playwright.sync_api import sync_playwright

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context, browser = launch_browser_context(
            playwright,
            profile,
            headless=headless,
            viewport={"width": 1280, "height": 820},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(resolve_url(url), wait_until="domcontentloaded")
            page.wait_for_timeout(250)
            page.screenshot(path=str(screenshot_path), full_page=True)
            boxes = selector_boxes(
                page,
                list(profile.get("knob_selectors", [])) + list(profile.get("slider_selectors", [])),
            )
            title = page.title()
        finally:
            close_browser_context(context, browser)

    failures = []
    if not screenshot_path.exists() or screenshot_path.stat().st_size == 0:
        failures.append("screenshot was not created")
    if not any(item["visible"] for item in boxes):
        failures.append("no configured slider or knob selector was visible")

    return {
        "report_type": "local_trace_artifacts",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "profile": {
            "path": str(profile_path.relative_to(ROOT)),
            "name": profile.get("name"),
            "url": profile.get("url"),
            "authorized_only": profile.get("authorized_only"),
        },
        "page": {
            "title": title,
            "resolved_url": resolve_url(url),
        },
        "artifacts": {
            "screenshot": str(screenshot_path.relative_to(ROOT)),
            "screenshot_bytes": screenshot_path.stat().st_size if screenshot_path.exists() else 0,
        },
        "selectors": boxes,
        "safety": {
            "does_not_solve_captcha": True,
            "does_not_drag_or_submit": True,
            "local_or_authorized_only": True,
        },
        "ok": len(failures) == 0,
        "failures": failures,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local Trace Artifacts",
        "",
        f"Generated: {report['generated_at']}",
        f"Scope: `{report['scope']}`",
        f"Status: `{'OK' if report['ok'] else 'FAIL'}`",
        f"Profile: `{report['profile']['path']}`",
        f"Screenshot: `{report['artifacts']['screenshot']}`",
        "",
        "## Selector Visibility",
        "",
        "| Selector | Visible | Box |",
        "|---|---|---|",
    ]
    for item in report["selectors"]:
        box = item["box"] or {}
        box_text = ", ".join(f"{key}={round(value, 2)}" for key, value in box.items()) if box else "-"
        lines.append(f"| `{item['selector']}` | `{item['visible']}` | {box_text} |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- Captures the bundled local demo page only by default.",
        "- Does not drag, submit, solve CAPTCHA, or evade bot defenses.",
        "- Stores screenshot evidence so visual regressions can be inspected later.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture local-only browser trace artifacts for the demo page.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--screenshot", type=Path, default=DEFAULT_SCREENSHOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    report = run_trace(args.profile, args.screenshot, headless=not args.headful)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
