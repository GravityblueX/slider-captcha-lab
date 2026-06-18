from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

try:
    from browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms
    from profile_utils import load_profile, resolve_url
except Exception:
    from src.browser_context import close_browser_context, launch_browser_context, manual_navigation_enabled, manual_wait_ms
    from src.profile_utils import load_profile, resolve_url


def probe_profile(profile_path: str, headless: bool = False) -> dict[str, Any]:
    profile = load_profile(profile_path)
    url = resolve_url(profile["url"])
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
            summary = _summarize_frames(frames)
            return {
                "profile": profile.get("name", profile_path),
                "url": page.url,
                "title": page.title(),
                "created_at_ms": round(time.time() * 1000),
                "summary": summary,
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


def _summarize_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    all_candidates = [
        candidate
        for frame in frames
        for candidate in frame.get("candidates", [])
        if "error" not in candidate
    ]
    visible = [candidate for candidate in all_candidates if candidate.get("visible")]
    slider_like = [
        c.get("selector")
        for c in visible
        if _contains_any(c, ["slider", "drag", "captcha"])
    ][:8]
    button_like = [
        c.get("selector")
        for c in visible
        if c.get("tag") == "button" or c.get("role") == "button"
    ][:8]
    return {
        "frame_count": len(frames),
        "candidate_count": len(all_candidates),
        "visible_candidate_count": len(visible),
        "suggested_slider_selectors": slider_like,
        "suggested_button_selectors": button_like,
    }


def _contains_any(candidate: dict[str, Any], words: list[str]) -> bool:
    haystack = " ".join(
        str(candidate.get(key, "")).lower()
        for key in ["id", "className", "role", "type", "text", "selector"]
    )
    return any(word in haystack for word in words)


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
