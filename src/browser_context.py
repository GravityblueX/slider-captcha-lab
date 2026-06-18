from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def browser_settings(profile: dict[str, Any]) -> dict[str, Any]:
    settings = profile.get("browser") or {}
    if not isinstance(settings, dict):
        return {}
    return settings


def extension_paths(profile: dict[str, Any]) -> list[Path]:
    settings = browser_settings(profile)
    raw = settings.get("extension_paths") or []
    if isinstance(raw, str):
        raw = [x.strip() for x in raw.replace("\n", ";").split(";") if x.strip()]
    return [_resolve_path(str(x)) for x in raw if str(x).strip()]


def manual_navigation_enabled(profile: dict[str, Any]) -> bool:
    return bool(browser_settings(profile).get("manual_navigation"))


def manual_wait_ms(profile: dict[str, Any], default: int = 60000) -> int:
    return max(0, int(browser_settings(profile).get("manual_wait_ms", default)))


def launch_browser_context(playwright, profile: dict[str, Any], headless: bool, viewport: dict[str, int] | None = None):
    """Create a Playwright context for authorized local QA.

    Extensions require Chromium persistent contexts. Persistent contexts also keep
    cookies/localStorage for authorized deep-page test sessions.
    """
    settings = browser_settings(profile)
    extensions = extension_paths(profile)
    user_data_dir = str(settings.get("user_data_dir", "")).strip()
    needs_persistent = bool(user_data_dir or extensions)
    args: list[str] = []

    if extensions:
        missing = [str(path) for path in extensions if not path.exists()]
        if missing:
            raise FileNotFoundError("Extension path not found: " + ", ".join(missing))
        joined = ",".join(str(path) for path in extensions)
        args.extend([f"--disable-extensions-except={joined}", f"--load-extension={joined}"])
        needs_persistent = True

    if needs_persistent:
        data_dir = _resolve_path(user_data_dir or ".liuhen/profiles/default")
        data_dir.mkdir(parents=True, exist_ok=True)
        context = playwright.chromium.launch_persistent_context(
            str(data_dir),
            channel="chromium",
            headless=False if extensions else headless,
            viewport=viewport,
            args=args,
        )
        return context, None

    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(viewport=viewport)
    return context, browser


def close_browser_context(context, browser=None) -> None:
    try:
        context.close()
    finally:
        if browser is not None:
            browser.close()
