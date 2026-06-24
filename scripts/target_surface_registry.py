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

from scripts.profile_policy import contains_cookie_values, discover_profiles, is_local_cdp_endpoint, is_local_url, load_json

DEFAULT_JSON = ROOT / "docs" / "target-surface-registry.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "target-surface-registry.md"
SCOPE = "local_owned_or_explicitly_authorized_pages_only"


def listify(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def profile_surface(path: Path) -> dict[str, Any]:
    profile = load_json(path)
    browser = profile.get("browser", {}) if isinstance(profile.get("browser"), dict) else {}
    target = profile.get("target", {}) if isinstance(profile.get("target"), dict) else {}
    cdp = browser.get("cdp", {}) if isinstance(browser.get("cdp"), dict) else {}
    endpoint = str(browser.get("cdp_endpoint") or cdp.get("endpoint") or "")
    frame_chain = listify(target.get("frame_chain"))
    extension_paths = listify(browser.get("extension_paths"))

    return {
        "path": str(path.relative_to(ROOT)),
        "name": str(profile.get("name", "")),
        "url": str(profile.get("url", "")),
        "authorizedOnly": profile.get("authorized_only") is True,
        "localDefaultUrl": is_local_url(str(profile.get("url", ""))),
        "persistentProfile": bool(browser.get("user_data_dir")),
        "userDataDir": str(browser.get("user_data_dir", "")),
        "extensionPathCount": len(extension_paths),
        "manualNavigation": bool(browser.get("manual_navigation")),
        "manualWaitMs": int(browser.get("manual_wait_ms") or 0),
        "connectExistingChrome": bool(browser.get("connect_existing_chrome")),
        "reuseCurrentPage": bool(browser.get("reuse_current_page") or cdp.get("reuse_current_page")),
        "cdpEndpoint": endpoint,
        "localCdpEndpoint": (not endpoint) or is_local_cdp_endpoint(endpoint),
        "frameChainDepth": len(frame_chain),
        "selectorSets": {
            "slider": len(listify(profile.get("slider_selectors"))),
            "knob": len(listify(profile.get("knob_selectors"))),
            "success": len(listify(profile.get("success_selectors"))),
        },
        "storesCookieValues": contains_cookie_values(profile),
    }


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def gate(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def build_registry(paths: list[Path]) -> dict[str, Any]:
    profile_paths = discover_profiles(paths)
    profiles = [profile_surface(path) for path in profile_paths]
    profile_policy = load_optional_json(ROOT / "docs" / "profile-policy-report.json")
    evidence_manifest = load_optional_json(ROOT / "docs" / "evidence-manifest.json")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    disclaimer_text = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8", errors="replace")
    boundary_text = f"{readme_text}\n{disclaimer_text}".lower()

    cdp_profiles = [profile for profile in profiles if profile["connectExistingChrome"]]
    persistent_profiles = [profile for profile in profiles if profile["persistentProfile"]]
    local_profiles = [profile for profile in profiles if profile["localDefaultUrl"]]
    gates = [
        gate("profiles discovered", len(profiles) >= 2, f"{len(profiles)} profile(s)"),
        gate("all profiles authorized", all(profile["authorizedOnly"] for profile in profiles), "authorized_only=true"),
        gate("all default urls local", all(profile["localDefaultUrl"] for profile in profiles), "demo/file/localhost defaults only"),
        gate("all CDP endpoints local", all(profile["localCdpEndpoint"] for profile in profiles), "localhost CDP only"),
        gate("no profile cookie values", not any(profile["storesCookieValues"] for profile in profiles), "no stored cookie values"),
        gate("persistent profile surface documented", len(persistent_profiles) >= 1, f"{len(persistent_profiles)} profile(s)"),
        gate("CDP attach surface documented", len(cdp_profiles) >= 1, f"{len(cdp_profiles)} profile(s)"),
        gate("local demo target present", len(local_profiles) >= 1, f"{len(local_profiles)} local profile(s)"),
        gate("deep page map exists", (ROOT / "docs" / "deep-page-map.md").exists(), "docs/deep-page-map.md"),
        gate("local trace screenshot exists", (ROOT / "docs" / "trace-artifacts" / "local-demo.png").exists(), "docs/trace-artifacts/local-demo.png"),
        gate("profile policy report ok", profile_policy.get("ok") is True, str(profile_policy.get("ok"))),
        gate("evidence manifest ok", evidence_manifest.get("ok") is True, str(evidence_manifest.get("ok"))),
        gate("anti-abuse boundary documented", "验证码" in boundary_text and "请勿用于" in boundary_text, "README.md + DISCLAIMER.md"),
    ]
    failures = [item for item in gates if not item["ok"]]
    return {
        "report_type": "target_surface_registry",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "ok": len(failures) == 0,
        "summary": {
            "profileCount": len(profiles),
            "persistentProfileCount": len(persistent_profiles),
            "cdpAttachProfileCount": len(cdp_profiles),
            "extensionConfiguredProfileCount": len([profile for profile in profiles if profile["extensionPathCount"] > 0]),
            "manualNavigationProfileCount": len([profile for profile in profiles if profile["manualNavigation"]]),
        },
        "gates": gates,
        "failures": failures,
        "profiles": profiles,
        "reference_patterns": [
            "Chrome DevTools Protocol diagnostics should stay bound to localhost or explicitly authorized sessions",
            "Deep page and iframe mapping should be recorded as evidence before automated interaction",
            "Profile files should describe browser surfaces without storing cookie values",
        ],
    }


def render_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# Target Surface Registry",
        "",
        f"Generated: {registry['generated_at']}",
        f"Scope: `{registry['scope']}`",
        f"Status: `{'OK' if registry['ok'] else 'FAIL'}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Profiles | {registry['summary']['profileCount']} |",
        f"| Persistent profile surfaces | {registry['summary']['persistentProfileCount']} |",
        f"| CDP attach surfaces | {registry['summary']['cdpAttachProfileCount']} |",
        f"| Extension-configured profiles | {registry['summary']['extensionConfiguredProfileCount']} |",
        f"| Manual-navigation profiles | {registry['summary']['manualNavigationProfileCount']} |",
        "",
        "## Gates",
        "",
        "| Gate | Result | Detail |",
        "|---|---|---|",
    ]
    for item in registry["gates"]:
        lines.append(f"| {item['name']} | {'OK' if item['ok'] else 'FAIL'} | {item['detail']} |")

    lines.extend([
        "",
        "## Profiles",
        "",
        "| Profile | URL | Browser Surface | Selectors | Frame Depth |",
        "|---|---|---|---|---:|",
    ])
    for profile in registry["profiles"]:
        surface_bits = []
        if profile["persistentProfile"]:
            surface_bits.append("persistent-profile")
        if profile["connectExistingChrome"]:
            surface_bits.append("cdp-attach")
        if profile["manualNavigation"]:
            surface_bits.append("manual-navigation")
        if profile["extensionPathCount"]:
            surface_bits.append(f"{profile['extensionPathCount']} extension path(s)")
        surface = ", ".join(surface_bits) or "managed-local-context"
        selectors = (
            f"slider={profile['selectorSets']['slider']}; "
            f"knob={profile['selectorSets']['knob']}; "
            f"success={profile['selectorSets']['success']}"
        )
        lines.append(
            f"| `{profile['path']}` | `{profile['url']}` | {surface} | {selectors} | {profile['frameChainDepth']} |"
        )

    lines.extend(["", "## Boundary", ""])
    lines.append("- This registry is for local, owned, or explicitly authorized browser diagnostics.")
    lines.append("- It does not solve CAPTCHA challenges, evade bot defenses, or store cookie values.")
    lines.append("- Third-party sites must not be added as default targets.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an authorized browser target surface registry.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("examples")], help="Profile files or directories.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    registry = build_registry(args.paths)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(registry), encoding="utf-8")
    print(json.dumps({"ok": registry["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if registry["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
