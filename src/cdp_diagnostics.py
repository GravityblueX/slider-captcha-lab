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


def run_cdp_diagnostics(profile_path: str, headless: bool = False) -> dict[str, Any]:
    """Collect CDP/session diagnostics for local, owned, or explicitly authorized pages."""
    profile = load_profile(profile_path)
    url = resolve_url(profile["url"])

    with sync_playwright() as p:
        context, browser = launch_browser_context(
            p,
            profile,
            headless=headless,
            viewport=profile.get("viewport", {"width": 1280, "height": 850}),
        )
        try:
            page = context.pages[-1] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if manual_navigation_enabled(profile):
                wait_ms = manual_wait_ms(profile)
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                if context.pages:
                    page = context.pages[-1]

            session = context.new_cdp_session(page)
            browser_version = _safe_cdp(session, "Browser.getVersion")
            targets = _safe_cdp(session, "Target.getTargets").get("targetInfos", [])
            runtime = _safe_cdp(
                session,
                "Runtime.evaluate",
                {
                    "returnByValue": True,
                    "expression": """
                    (() => {
                      const storageKeys = (storage) => {
                        try { return Array.from({length: storage.length}, (_, i) => storage.key(i)).filter(Boolean); }
                        catch (_) { return []; }
                      };
                      return {
                        url: location.href,
                        title: document.title,
                        readyState: document.readyState,
                        visibilityState: document.visibilityState,
                        navigator: {
                          userAgent: navigator.userAgent,
                          platform: navigator.platform,
                          languages: navigator.languages,
                          webdriver: navigator.webdriver,
                          cookieEnabled: navigator.cookieEnabled,
                          hardwareConcurrency: navigator.hardwareConcurrency,
                          deviceMemory: navigator.deviceMemory || null,
                          maxTouchPoints: navigator.maxTouchPoints
                        },
                        screen: {
                          width: screen.width,
                          height: screen.height,
                          availWidth: screen.availWidth,
                          availHeight: screen.availHeight,
                          devicePixelRatio: window.devicePixelRatio,
                          innerWidth: window.innerWidth,
                          innerHeight: window.innerHeight
                        },
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        storage: {
                          localStorageKeys: storageKeys(localStorage),
                          sessionStorageKeys: storageKeys(sessionStorage)
                        }
                      };
                    })()
                    """,
                },
            )

            cookies = context.cookies()
            frames = [
                {
                    "index": index,
                    "name": frame.name,
                    "url": frame.url,
                    "is_main": frame == page.main_frame,
                }
                for index, frame in enumerate(page.frames)
            ]

            return {
                "report_type": "cdp_diagnostics",
                "scope": "local_owned_or_explicitly_authorized_pages_only",
                "safety": {
                    "captcha_solver": False,
                    "bypass_or_evasion": False,
                    "raw_cookie_values_recorded": False,
                },
                "profile": profile.get("name", profile_path),
                "created_at_ms": round(time.time() * 1000),
                "page": {
                    "url": page.url,
                    "title": page.title(),
                    "frame_count": len(page.frames),
                },
                "cdp": {
                    "browser_version": browser_version,
                    "target_count": len(targets),
                    "targets": [_target_summary(target) for target in targets[:40]],
                    "runtime": _runtime_value(runtime),
                },
                "context": {
                    "cookie_count": len(cookies),
                    "cookie_names": sorted({cookie.get("name", "") for cookie in cookies if cookie.get("name")})[:40],
                    "pages": [{"url": item.url, "title": _safe_title(item)} for item in context.pages],
                },
                "frames": frames,
                "recommendations": _recommendations(runtime, cookies, frames),
            }
        finally:
            close_browser_context(context, browser)


def _safe_cdp(session, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return session.send(method, params or {})
    except Exception as exc:
        return {"error": str(exc)}


def _runtime_value(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("result", {}).get("value") or {"error": result.get("error", "runtime value unavailable")}


def _target_summary(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": target.get("type"),
        "title": target.get("title"),
        "url": target.get("url"),
        "attached": target.get("attached"),
    }


def _safe_title(page) -> str:
    try:
        return page.title()
    except Exception:
        return ""


def _recommendations(runtime: dict[str, Any], cookies: list[dict[str, Any]], frames: list[dict[str, Any]]) -> list[str]:
    value = _runtime_value(runtime)
    navigator = value.get("navigator", {}) if isinstance(value, dict) else {}
    recommendations: list[str] = []
    if navigator.get("webdriver") is True:
        recommendations.append("navigator.webdriver is true; keep this result as a diagnostic signal for authorized QA.")
    if len(frames) > 1:
        recommendations.append("Multiple frames detected; use explicit frame_chain selectors in authorized profiles.")
    if cookies:
        recommendations.append("Cookies are present; report stores names only and intentionally omits values.")
    if not recommendations:
        recommendations.append("No immediate CDP/session diagnostics warning was detected.")
    return recommendations


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect CDP diagnostics for local/owned/authorized pages.")
    parser.add_argument("profile", help="Path to an authorized profile JSON")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--out", help="Optional output JSON path")
    args = parser.parse_args()

    result = run_cdp_diagnostics(args.profile, headless=args.headless)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
