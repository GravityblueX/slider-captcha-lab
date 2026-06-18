from __future__ import annotations

from typing import Any


def selector_candidates(profile: dict[str, Any], key: str, default: str = "") -> list[str]:
    plural = f"{key}s"
    raw = profile.get(plural)
    if raw is None:
        raw = profile.get(key, default)
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    return [str(item).strip() for item in raw if str(item).strip()]


def resolve_frame_scope(page, profile: dict[str, Any]):
    target = profile.get("target") or {}
    if not isinstance(target, dict):
        target = {}
    frame_chain = target.get("frame_chain") or profile.get("frame_chain") or []
    if isinstance(frame_chain, dict):
        frame_chain = [frame_chain]
    scope = page
    for frame_def in frame_chain:
        scope = _resolve_one_frame(scope, page, frame_def)
    return scope


def _resolve_one_frame(scope, page, frame_def: dict[str, Any]):
    selector = str(frame_def.get("selector", "")).strip()
    if selector:
        handle = scope.wait_for_selector(selector, timeout=int(frame_def.get("timeout", 10000)))
        frame = handle.content_frame() if handle else None
        if frame is None:
            raise RuntimeError(f"Selector is not an iframe or frame is unavailable: {selector}")
        return frame

    url_contains = str(frame_def.get("url_contains", "")).strip()
    name = str(frame_def.get("name", "")).strip()
    for frame in page.frames:
        if url_contains and url_contains not in frame.url:
            continue
        if name and name != frame.name:
            continue
        return frame
    raise RuntimeError(f"Cannot locate frame: {frame_def}")


def first_working_locator(scope, selectors: list[str], timeout: int = 10000):
    errors: list[str] = []
    for selector in selectors:
        try:
            loc = scope.locator(selector).first
            loc.wait_for(state="attached", timeout=timeout)
            return loc, selector
        except Exception as exc:
            errors.append(f"{selector}: {exc}")
    raise RuntimeError("No selector matched. Tried: " + " | ".join(errors))
