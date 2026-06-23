from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from browser_context import browser_settings, manual_navigation_enabled, manual_wait_ms
    from profile_utils import resolve_url
except Exception:
    from src.browser_context import browser_settings, manual_navigation_enabled, manual_wait_ms
    from src.profile_utils import resolve_url


DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"


@dataclass
class ChromeSession:
    context: Any
    browser: Any
    page: Any
    attached: bool
    endpoint: str | None
    selected_by: str


def cdp_connection_enabled(profile: dict[str, Any]) -> bool:
    settings = browser_settings(profile)
    cdp = _cdp_settings(profile)
    return bool(
        settings.get("connect_existing_chrome")
        or settings.get("cdp_endpoint")
        or cdp.get("enabled")
        or cdp.get("endpoint")
    )


def cdp_endpoint(profile: dict[str, Any]) -> str:
    settings = browser_settings(profile)
    cdp = _cdp_settings(profile)
    return str(cdp.get("endpoint") or settings.get("cdp_endpoint") or DEFAULT_CDP_ENDPOINT)


def open_chrome_session(playwright, profile: dict[str, Any], headless: bool, viewport: dict[str, int] | None = None) -> ChromeSession:
    """Open either an attached Chrome CDP session or a managed Playwright context.

    The attached mode is intentionally observational/QA-oriented: it reuses an
    explicitly authorized local Chrome debugging endpoint, can select an already
    open tab, and avoids closing the user's Chrome when cleanup runs.
    """
    if cdp_connection_enabled(profile):
        return _connect_existing_chrome(playwright, profile, viewport=viewport)
    return _launch_managed_chromium(playwright, profile, headless=headless, viewport=viewport)


def close_chrome_session(session: ChromeSession) -> None:
    if session.attached:
        return
    try:
        session.context.close()
    finally:
        if session.browser is not None:
            session.browser.close()


def _connect_existing_chrome(playwright, profile: dict[str, Any], viewport: dict[str, int] | None = None) -> ChromeSession:
    endpoint = cdp_endpoint(profile)
    timeout_ms = int(_cdp_settings(profile).get("timeout_ms") or browser_settings(profile).get("cdp_timeout_ms") or 10000)
    browser = playwright.chromium.connect_over_cdp(endpoint, timeout=timeout_ms)
    context = browser.contexts[0] if browser.contexts else browser.new_context(viewport=viewport)
    page, selected_by = _select_page(context, profile)
    if page is None:
        page = context.new_page()
        selected_by = "new_page"

    if _should_navigate(profile):
        page.goto(resolve_url(profile["url"]), wait_until="domcontentloaded", timeout=20000)
    elif manual_navigation_enabled(profile):
        wait_ms = manual_wait_ms(profile)
        if wait_ms > 0:
            page.wait_for_timeout(wait_ms)
        if context.pages:
            page = context.pages[-1]
            selected_by = "manual_navigation_last_page"

    return ChromeSession(
        context=context,
        browser=browser,
        page=page,
        attached=True,
        endpoint=endpoint,
        selected_by=selected_by,
    )


def _launch_managed_chromium(playwright, profile: dict[str, Any], headless: bool, viewport: dict[str, int] | None = None) -> ChromeSession:
    try:
        from browser_context import close_browser_context, launch_browser_context
    except Exception:
        from src.browser_context import close_browser_context, launch_browser_context

    context, browser = launch_browser_context(playwright, profile, headless=headless, viewport=viewport)
    page = context.pages[-1] if context.pages else context.new_page()
    page.goto(resolve_url(profile["url"]), wait_until="domcontentloaded", timeout=20000)
    if manual_navigation_enabled(profile):
        wait_ms = manual_wait_ms(profile)
        if wait_ms > 0:
            page.wait_for_timeout(wait_ms)
        if context.pages:
            page = context.pages[-1]
    return ChromeSession(
        context=context,
        browser=browser,
        page=page,
        attached=False,
        endpoint=None,
        selected_by="managed_context",
    )


def _select_page(context, profile: dict[str, Any]) -> tuple[Any | None, str]:
    cdp = _cdp_settings(profile)
    url_contains = str(cdp.get("target_url_contains") or browser_settings(profile).get("target_url_contains") or "").strip()
    title_contains = str(cdp.get("target_title_contains") or browser_settings(profile).get("target_title_contains") or "").strip()
    pages = list(context.pages)
    if url_contains:
        for page in reversed(pages):
            if url_contains in page.url:
                return page, "target_url_contains"
    if title_contains:
        for page in reversed(pages):
            try:
                if title_contains in page.title():
                    return page, "target_title_contains"
            except Exception:
                continue
    if pages:
        return pages[-1], "last_page"
    return None, "none"


def _should_navigate(profile: dict[str, Any]) -> bool:
    cdp = _cdp_settings(profile)
    settings = browser_settings(profile)
    reuse_current = bool(cdp.get("reuse_current_page") or settings.get("reuse_current_page"))
    return bool(profile.get("url")) and not reuse_current


def _cdp_settings(profile: dict[str, Any]) -> dict[str, Any]:
    settings = browser_settings(profile)
    cdp = settings.get("cdp") or {}
    return cdp if isinstance(cdp, dict) else {}
