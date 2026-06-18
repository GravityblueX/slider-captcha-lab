from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.authorized_page_tester import run_profile
from src.page_probe import probe_profile

PROFILE = ROOT / "examples" / "authorized_deep_page_profile.json"


def main() -> int:
    result = run_profile(str(PROFILE), headless=True)
    summary = result.get("summary", {})
    if summary.get("failed") != 0 or summary.get("passed", 0) < 1:
        print(json.dumps({"ok": False, "stage": "authorized_profile", "result": result}, ensure_ascii=False, indent=2))
        return 1

    probe = probe_profile(str(PROFILE), headless=True)
    probe_summary = probe.get("summary", {})
    if probe_summary.get("frame_count", 0) < 1 or probe_summary.get("visible_candidate_count", 0) < 1:
        print(json.dumps({"ok": False, "stage": "page_probe", "result": probe}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "ok": True,
        "authorized_profile": summary,
        "page_probe": probe_summary,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
