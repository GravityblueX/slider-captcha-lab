from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

try:
    from chrome_session import close_chrome_session, open_chrome_session
    from profile_utils import load_profile
except Exception:
    from src.chrome_session import close_chrome_session, open_chrome_session
    from src.profile_utils import load_profile


def probe_profile(profile_path: str, headless: bool = False) -> dict[str, Any]:
    profile = load_profile(profile_path)
    with sync_playwright() as p:
        session = open_chrome_session(p, profile, headless=headless, viewport=profile.get("viewport", {"width": 1280, "height": 850}))
        try:
            page = session.page
            frame_indexes = {id(frame): index for index, frame in enumerate(page.frames)}
            frames = []
            for index, frame in enumerate(page.frames):
                frames.append(_probe_frame(frame, index, frame_indexes))
            summary = _summarize_frames(frames)
            return {
                "profile": profile.get("name", profile_path),
                "url": page.url,
                "title": page.title(),
                "created_at_ms": round(time.time() * 1000),
                "summary": summary,
                "frames": frames,
                "scope": "local_owned_or_explicitly_authorized_pages_only",
                "browser_session": {
                    "attached_to_existing_chrome": session.attached,
                    "endpoint": session.endpoint,
                    "selected_by": session.selected_by,
                },
            }
        finally:
            close_chrome_session(session)


def _probe_frame(frame, index: int, frame_indexes: dict[int, int]) -> dict[str, Any]:
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
    candidates = _rank_candidates(data)
    return {
        "index": index,
        "name": frame.name,
        "url": frame.url,
        "depth": _frame_depth(frame),
        "parent_index": _parent_index(frame, frame_indexes),
        "frame_chain": _frame_chain(frame, frame_indexes),
        "target_hint": _frame_target_hint(frame),
        "candidates": candidates,
    }


def _summarize_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    all_candidates = [
        candidate
        for frame in frames
        for candidate in frame.get("candidates", [])
        if "error" not in candidate
    ]
    visible = [candidate for candidate in all_candidates if candidate.get("visible")]
    best_candidates = sorted(
        (
            {
                "frame_index": frame.get("index"),
                "frame_depth": frame.get("depth"),
                "frame_url": frame.get("url"),
                "selector": candidate.get("selector"),
                "score": candidate.get("score", 0),
                "reasons": candidate.get("reasons", []),
                "text": candidate.get("text", ""),
                "box": candidate.get("box", {}),
            }
            for frame in frames
            for candidate in frame.get("candidates", [])
            if "error" not in candidate and candidate.get("visible")
        ),
        key=lambda item: (-int(item.get("score", 0)), int(item.get("frame_depth", 0))),
    )[:12]
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
        "deep_frame_count": len([frame for frame in frames if int(frame.get("depth", 0)) > 0]),
        "candidate_count": len(all_candidates),
        "visible_candidate_count": len(visible),
        "best_candidates": best_candidates,
        "suggested_slider_selectors": slider_like,
        "suggested_button_selectors": button_like,
    }


def _contains_any(candidate: dict[str, Any], words: list[str]) -> bool:
    haystack = " ".join(
        str(candidate.get(key, "")).lower()
        for key in ["id", "className", "role", "type", "text", "selector"]
    )
    return any(word in haystack for word in words)


def _rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        if "error" in candidate:
            ranked.append(candidate)
            continue
        score, reasons = _candidate_score(candidate)
        item = dict(candidate)
        item["score"] = score
        item["reasons"] = reasons
        ranked.append(item)
    return sorted(ranked, key=lambda item: int(item.get("score", 0)), reverse=True)


def _candidate_score(candidate: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    haystack = " ".join(
        str(candidate.get(key, "")).lower()
        for key in ["id", "className", "role", "type", "text", "selector"]
    )
    box = candidate.get("box") or {}
    width = int(box.get("width") or 0)
    height = int(box.get("height") or 0)

    if candidate.get("visible"):
        score += 30
        reasons.append("visible")
    if any(word in haystack for word in ["slider", "drag", "captcha", "verify", "knob"]):
        score += 35
        reasons.append("slider_or_drag_named")
    if candidate.get("role") == "button" or candidate.get("tag") == "button":
        score += 12
        reasons.append("button_like")
    if candidate.get("tag") == "input":
        score += 8
        reasons.append("input")
    if width >= 120 and 20 <= height <= 120:
        score += 10
        reasons.append("track_shaped")
    if 20 <= width <= 90 and 20 <= height <= 90:
        score += 8
        reasons.append("knob_shaped")
    if candidate.get("text"):
        score += 4
        reasons.append("has_label")

    return score, reasons


def _frame_depth(frame) -> int:
    depth = 0
    current = frame.parent_frame
    while current is not None:
        depth += 1
        current = current.parent_frame
    return depth


def _parent_index(frame, frame_indexes: dict[int, int]) -> int | None:
    parent = frame.parent_frame
    if parent is None:
        return None
    return frame_indexes.get(id(parent))


def _frame_chain(frame, frame_indexes: dict[int, int]) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    current = frame
    while current is not None:
        chain.append(
            {
                "index": frame_indexes.get(id(current)),
                "name": current.name,
                "url": current.url,
                "target_hint": _frame_target_hint(current),
            }
        )
        current = current.parent_frame
    chain.reverse()
    return chain


def _frame_target_hint(frame) -> dict[str, str]:
    if frame.name:
        return {"name": frame.name}
    url = frame.url or ""
    if url and url != "about:blank":
        return {"url_contains": _short_url_hint(url)}
    return {}


def _short_url_hint(url: str) -> str:
    for marker in ["/captcha", "/verify", "/login", "/passport", "/iframe", "/embed"]:
        if marker in url:
            return marker
    return url[:80]


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
