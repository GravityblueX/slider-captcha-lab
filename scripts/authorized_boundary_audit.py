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

from scripts.safety_contract import build_contract
from scripts.target_surface_registry import build_registry

DEFAULT_JSON = ROOT / "docs" / "authorized-boundary-audit.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "authorized-boundary-audit.md"
SCOPE = "local_owned_or_explicitly_authorized_pages_only"
BLOCKED_DEFAULT_TARGET_MARKERS = (
    "cnki",
    "geetest",
    "captcha",
    "recaptcha",
    "hcaptcha",
    "turnstile",
    "aliyun",
    "tencent",
)


def gate(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def blocked_markers_in_profiles(profiles: list[dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for profile in profiles:
        haystack = " ".join(
            str(profile.get(key, ""))
            for key in ("name", "url", "cdpEndpoint", "path")
        ).lower()
        for marker in BLOCKED_DEFAULT_TARGET_MARKERS:
            if marker in haystack:
                hits.append(f"{profile.get('path')}: {marker}")
    return hits


def build_audit(paths: list[Path]) -> dict[str, Any]:
    registry = build_registry(paths)
    safety = build_contract()
    profiles = registry.get("profiles", [])
    blocked_hits = blocked_markers_in_profiles(profiles)
    cdp_profiles = [profile for profile in profiles if profile.get("connectExistingChrome")]
    persistent_profiles = [profile for profile in profiles if profile.get("persistentProfile")]
    extension_profiles = [profile for profile in profiles if int(profile.get("extensionPathCount", 0)) > 0]
    docs_text = "\n".join(read_text(ROOT / name) for name in ("README.md", "DISCLAIMER.md"))

    gates = [
        gate("scope recorded", registry.get("scope") == SCOPE and safety.get("scope") == SCOPE, SCOPE),
        gate("target surface registry ok", registry.get("ok") is True, str(registry.get("ok"))),
        gate("safety contract ok", safety.get("ok") is True, str(safety.get("ok"))),
        gate("all profiles authorized only", all(profile.get("authorizedOnly") is True for profile in profiles), f"{len(profiles)} profile(s)"),
        gate("all default URLs local", all(profile.get("localDefaultUrl") is True for profile in profiles), f"{len(profiles)} profile(s)"),
        gate("all CDP endpoints local", all(profile.get("localCdpEndpoint") is True for profile in profiles), f"{len(profiles)} profile(s)"),
        gate("CDP attach uses existing local browser only", all(profile.get("reuseCurrentPage") is True for profile in cdp_profiles), f"{len(cdp_profiles)} CDP profile(s)"),
        gate("default profiles do not load extensions", len(extension_profiles) == 0, f"{len(extension_profiles)} extension profile(s)"),
        gate("blocked real-site markers absent from profile defaults", len(blocked_hits) == 0, "; ".join(blocked_hits) or "none"),
        gate("no cookie values in generated audit inputs", all(profile.get("storesCookieValues") is False for profile in profiles), "profile registry storesCookieValues=false"),
        gate("README and disclaimer keep non-bypass language", "请勿用于" in docs_text and "验证码" in docs_text and "风控" in docs_text, "README.md + DISCLAIMER.md"),
    ]
    failures = [item for item in gates if not item["ok"]]
    return {
        "report_type": "authorized_boundary_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "ok": len(failures) == 0,
        "summary": {
            "profileCount": len(profiles),
            "cdpAttachProfileCount": len(cdp_profiles),
            "persistentProfileCount": len(persistent_profiles),
            "extensionProfileCount": len(extension_profiles),
            "blockedMarkerCount": len(blocked_hits),
        },
        "gates": gates,
        "failures": failures,
        "profiles": profiles,
        "reference_patterns": [
            "Treat browser automation targets as an explicit allowlist",
            "Keep default CDP attach endpoints bound to localhost",
            "Store browser diagnostics evidence without cookie values",
        ],
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Authorized Boundary Audit",
        "",
        f"Generated: {audit['generated_at']}",
        f"Scope: `{audit['scope']}`",
        f"Status: `{'OK' if audit['ok'] else 'FAIL'}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Profiles | {audit['summary']['profileCount']} |",
        f"| CDP attach profiles | {audit['summary']['cdpAttachProfileCount']} |",
        f"| Persistent profiles | {audit['summary']['persistentProfileCount']} |",
        f"| Extension profiles | {audit['summary']['extensionProfileCount']} |",
        f"| Blocked default-target markers | {audit['summary']['blockedMarkerCount']} |",
        "",
        "## Gates",
        "",
        "| Gate | Result | Detail |",
        "|---|---|---|",
    ]
    for item in audit["gates"]:
        lines.append(f"| {item['name']} | {'OK' if item['ok'] else 'FAIL'} | {item['detail']} |")
    lines.extend(["", "## Boundary", ""])
    lines.append("- Defaults must remain local, owned, or explicitly authorized.")
    lines.append("- Real third-party challenge providers and site-specific bypass targets are not allowed as defaults.")
    lines.append("- CDP attach is limited to local browser diagnostics and must not store cookie values.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local/authorized boundary for bundled browser profiles.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("examples")], help="Profile files or directories.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    audit = build_audit(args.paths)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"ok": audit["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if audit["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
