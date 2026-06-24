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

from src.authorized_page_tester import run_profile
from src.cdp_diagnostics import run_cdp_diagnostics
from src.page_probe import probe_profile

DEFAULT_PROFILE = ROOT / "examples" / "authorized_deep_page_profile.json"
DEFAULT_JSON = ROOT / "docs" / "authorized-evidence-pack-local-demo.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "authorized-evidence-pack-local-demo.md"
SCOPE = "local_owned_or_explicitly_authorized_pages_only"


def load_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_candidates(probe: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    candidates = probe.get("summary", {}).get("best_candidates") or []
    output: list[dict[str, Any]] = []
    for candidate in candidates[:limit]:
        output.append({
            "selector": candidate.get("selector"),
            "frame_index": candidate.get("frame_index"),
            "frame_depth": candidate.get("frame_depth"),
            "score": candidate.get("score"),
            "reasons": candidate.get("reasons", []),
            "box": candidate.get("box"),
        })
    return output


def build_evidence_pack(
    profile_path: Path,
    profile: dict[str, Any],
    authorized_result: dict[str, Any],
    probe: dict[str, Any],
    cdp: dict[str, Any],
) -> dict[str, Any]:
    authorized_summary = authorized_result.get("summary", {})
    probe_summary = probe.get("summary", {})

    pack = {
        "report_type": "authorized_browser_evidence_pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "profile": {
            "path": str(profile_path),
            "name": profile.get("name"),
            "url": profile.get("url"),
            "authorized_only": bool(profile.get("authorized_only")),
            "manual_navigation": bool(profile.get("browser", {}).get("manual_navigation")),
            "connect_existing_chrome": bool(profile.get("browser", {}).get("connect_existing_chrome")),
        },
        "authorized_profile": {
            "passed": authorized_summary.get("passed", 0),
            "failed": authorized_summary.get("failed", 0),
            "total": authorized_summary.get("total", 0),
        },
        "page_probe": {
            "frame_count": probe_summary.get("frame_count", 0),
            "deep_frame_count": probe_summary.get("deep_frame_count", 0),
            "candidate_count": probe_summary.get("candidate_count", 0),
            "visible_candidate_count": probe_summary.get("visible_candidate_count", 0),
            "best_candidates": summarize_candidates(probe),
        },
        "cdp_diagnostics": {
            "target_count": cdp.get("cdp", {}).get("target_count", 0),
            "frame_count": cdp.get("page", {}).get("frame_count", 0),
            "scope": cdp.get("scope"),
        },
        "safety": {
            "no_third_party_defaults": not str(profile.get("url", "")).startswith(("http://", "https://")),
            "no_cookie_values_recorded": True,
            "does_not_solve_captcha": True,
        },
    }
    pack["ok"] = (
        pack["profile"]["authorized_only"]
        and pack["authorized_profile"]["failed"] == 0
        and pack["authorized_profile"]["passed"] >= 1
        and pack["page_probe"]["frame_count"] >= 1
        and pack["page_probe"]["visible_candidate_count"] >= 1
        and pack["cdp_diagnostics"]["frame_count"] >= 1
        and pack["safety"]["no_third_party_defaults"]
    )
    return pack


def render_markdown(pack: dict[str, Any]) -> str:
    profile = pack["profile"]
    lines = [
        "# Authorized Evidence Pack - Local Demo",
        "",
        f"Generated: {pack['generated_at']}",
        f"Scope: `{pack['scope']}`",
        f"Result: `{'OK' if pack['ok'] else 'FAIL'}`",
        "",
        "## Boundary",
        "",
        "- Local, owned, or explicitly authorized pages only.",
        "- Does not solve CAPTCHA challenges.",
        "- Does not record cookie values or third-party secrets.",
        "- Default profile stays on the bundled local demo page.",
        "",
        "## Profile",
        "",
        f"- Name: `{profile['name']}`",
        f"- URL: `{profile['url']}`",
        f"- Authorized only: `{profile['authorized_only']}`",
        f"- Manual navigation: `{profile['manual_navigation']}`",
        f"- Existing Chrome attach: `{profile['connect_existing_chrome']}`",
        "",
        "## Evidence Summary",
        "",
        f"- Authorized profile: passed `{pack['authorized_profile']['passed']}`, failed `{pack['authorized_profile']['failed']}`, total `{pack['authorized_profile']['total']}`",
        f"- Page probe: frames `{pack['page_probe']['frame_count']}`, visible candidates `{pack['page_probe']['visible_candidate_count']}`",
        f"- CDP diagnostics: targets `{pack['cdp_diagnostics']['target_count']}`, frames `{pack['cdp_diagnostics']['frame_count']}`",
        "",
        "## Best Selector Candidates",
        "",
        "| Selector | Frame | Score | Reasons |",
        "|---|---:|---:|---|",
    ]
    for candidate in pack["page_probe"]["best_candidates"]:
        reasons = ", ".join(candidate.get("reasons", []))
        lines.append(
            f"| `{candidate.get('selector')}` | {candidate.get('frame_index')} | {candidate.get('score')} | {reasons} |"
        )
    lines.append("")
    return "\n".join(lines)


def run_pack(profile_path: Path, headless: bool) -> dict[str, Any]:
    profile = load_profile(profile_path)
    authorized_result = run_profile(str(profile_path), headless=headless)
    probe = probe_profile(str(profile_path), headless=headless)
    cdp = run_cdp_diagnostics(str(profile_path), headless=headless)
    return build_evidence_pack(profile_path, profile, authorized_result, probe, cdp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local or authorized browser diagnostics evidence pack.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Authorized profile JSON.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON, help="JSON output path.")
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN, help="Markdown output path.")
    parser.add_argument("--headful", action="store_true", help="Run with a visible browser.")
    args = parser.parse_args()

    pack = run_pack(args.profile, headless=not args.headful)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(pack), encoding="utf-8")

    print(json.dumps({"ok": pack["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if pack["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
