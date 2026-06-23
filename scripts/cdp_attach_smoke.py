from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from src.chrome_session import close_chrome_session, open_chrome_session


def _free_port(start: int = 9333) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local CDP port found.")


def main() -> int:
    port = _free_port()
    demo_url = (ROOT / "demo" / "index.html").as_uri()
    profile = {
        "name": "cdp-attach-smoke",
        "url": demo_url,
        "browser": {
            "connect_existing_chrome": True,
            "cdp_endpoint": f"http://127.0.0.1:{port}",
            "reuse_current_page": True,
            "target_url_contains": "index.html",
            "cdp": {
                "enabled": True,
                "endpoint": f"http://127.0.0.1:{port}",
                "reuse_current_page": True,
            },
        },
        "authorized_only": True,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[f"--remote-debugging-port={port}"])
        page = browser.new_page()
        page.goto(demo_url, wait_until="domcontentloaded")
        session = open_chrome_session(p, profile, headless=True)
        try:
            result = {
                "ok": session.attached and "index.html" in session.page.url and len(session.page.frames) >= 1,
                "attached": session.attached,
                "selected_by": session.selected_by,
                "frames": len(session.page.frames),
                "port": port,
            }
        finally:
            close_chrome_session(session)
            browser.close()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
