from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

try:
    from browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms
except Exception:
    from src.browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms

ROOT = Path(__file__).resolve().parents[1]


def _resolve_url(url: str) -> str:
    if url.startswith(("http://", "https://", "file://")):
        return url
    return (ROOT / url).resolve().as_uri()


def probe_profile(profile_path: str, headless: bool = False) -> dict[str, Any]:
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    if profile.get("authorized_only") is not True:
        raise ValueError("Profile must set authorized_only=true. Only local/owned/authorized pages are supported.")
    url = _resolve_url(profile["url"])
    with sync_playwright() as p:
        context, browser = launch_browser_context(p, profile, headless=headless, viewport=profile.get("viewport", {"width": 1280, "height": 850}))
        try:
            page = context.pages[-1] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if manual_navigation_enabled(profile):
                wait_ms = manual_wait_ms(profile)
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                if context.pages:
                    page = context.pages[-1]
            frames = []
            for index, frame in enumerate(page.frames):
                frames.append(_probe_frame(frame, index))
            return {
                "profile": profile.get("name", profile_path),
                "url": page.url,
                "title": page.title(),
                "created_at_ms": round(time.time() * 1000),
                "frames": frames,
                "scope": "local_owned_or_explicitly_authorized_pages_only",
            }
        finally:
            close_browser_context(context, browser)


def _probe_frame(frame, index: int) -> dict[str, Any]:
    try:
        data = frame.evaluate(
            """() => {
              const cssPath = (el) => {
                if (el.id) return '#' + CSS.escape(el.id);
                const parts = [];
                let cur = el;
                while (cur && cur.nodeType === Node.ELEMENT_NODE && parts.length < 4) {
                  let name = cur.nodeName.toLowerCase();
                  if (cur.classList && cur.classList.length) {
                    name += '.' + [...cur.classList].slice(0, 2).map(x => CSS.escape(x)).join('.');
                  }
                  const parent = cur.parentElement;
                  if (parent) {
                    const same = [...parent.children].filter(x => x.nodeName === cur.nodeName);
                    if (same.length > 1) name += `:nth-of-type(${same.indexOf(cur) + 1})`;
                  }
                  parts.unshift(name);
                  cur = parent;
                }
                return parts.join(' > ');
              };
              const label = (el) => (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 120);
              const selector = 'button,input,textarea,select,[role="button"],[draggable="true"],[class*="slider"],[id*="slider"],[class*="drag"],[id*="drag"],[class*="captcha"],[id*="captcha"]';
              return [...document.querySelectorAll(selector)].slice(0, 80).map(el => {
                const r = el.getBoundingClientRect();
                return {
                  tag: el.tagName.toLowerCase(),
                  id: el.id || '',
                  className: typeof el.className === 'string' ? el.className : '',
                  role: el.getAttribute('role') || '',
                  type: el.getAttribute('type') || '',
                  text: label(el),
                  selector: cssPath(el),
                  visible: !!(r.width && r.height),
                  box: {x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height)}
                };
              });
            }"""
        )
    except Exception as exc:
        data = [{"error": str(exc)}]
    return {
        "index": index,
        "name": frame.name,
        "url": frame.url,
        "candidates": data,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probe local/owned/authorized page structure")
    parser.add_argument("profile", help="Path to authorized profile JSON")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--out", help="Optional output JSON path")
    args = parser.parse_args()
    result = probe_profile(args.profile, headless=args.headless)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
