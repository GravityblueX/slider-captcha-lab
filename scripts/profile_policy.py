from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "profile-policy-report.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "profile-policy-report.md"


@dataclass(frozen=True)
class PolicyIssue:
    profile: str
    severity: str
    message: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_local_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return (
        lowered.startswith("demo/")
        or lowered.startswith("./demo/")
        or lowered.startswith("file:")
        or lowered.startswith("http://127.0.0.1")
        or lowered.startswith("http://localhost")
    )


def is_local_cdp_endpoint(endpoint: str) -> bool:
    lowered = endpoint.lower()
    return lowered.startswith("http://127.0.0.1:") or lowered.startswith("http://localhost:")


def contains_cookie_values(profile: dict[str, Any]) -> bool:
    raw = json.dumps(profile, ensure_ascii=False).lower()
    suspicious_keys = ["cookie_value", "cookievalue", "\"cookies\"", "\"cookie\""]
    return any(key in raw for key in suspicious_keys)


def check_profile(path: Path, profile: dict[str, Any]) -> list[PolicyIssue]:
    label = str(path.relative_to(ROOT))
    issues: list[PolicyIssue] = []
    if profile.get("authorized_only") is not True:
        issues.append(PolicyIssue(label, "error", "authorized_only must be true"))

    url = str(profile.get("url", ""))
    if not is_local_url(url):
        issues.append(PolicyIssue(label, "error", f"default url must be local demo or localhost, got {url!r}"))

    browser = profile.get("browser", {}) if isinstance(profile.get("browser"), dict) else {}
    if browser.get("connect_existing_chrome"):
        endpoint = str(browser.get("cdp_endpoint") or browser.get("cdp", {}).get("endpoint") or "")
        if not is_local_cdp_endpoint(endpoint):
            issues.append(PolicyIssue(label, "error", f"cdp endpoint must be localhost, got {endpoint!r}"))
        if not browser.get("reuse_current_page"):
            issues.append(PolicyIssue(label, "warning", "attach profiles should reuse the current authorized page"))

    if contains_cookie_values(profile):
        issues.append(PolicyIssue(label, "error", "profile must not store cookie values"))

    return issues


def discover_profiles(paths: list[Path]) -> list[Path]:
    profiles: list[Path] = []
    for path in paths:
        resolved = path if path.is_absolute() else ROOT / path
        if resolved.is_file():
            profiles.append(resolved)
        elif resolved.is_dir():
            profiles.extend(sorted(resolved.glob("*.json")))
    return sorted(set(profiles))


def build_report(paths: list[Path]) -> dict[str, Any]:
    profiles = discover_profiles(paths)
    all_issues: list[PolicyIssue] = []
    checked = []
    for path in profiles:
        profile = load_json(path)
        issues = check_profile(path, profile)
        all_issues.extend(issues)
        checked.append({
            "path": str(path.relative_to(ROOT)),
            "name": profile.get("name"),
            "url": profile.get("url"),
            "authorized_only": profile.get("authorized_only"),
            "issues": [issue.__dict__ for issue in issues],
        })
    errors = [issue for issue in all_issues if issue.severity == "error"]
    return {
        "report_type": "profile_policy_report",
        "ok": len(errors) == 0 and len(checked) > 0,
        "checked": checked,
        "issues": [issue.__dict__ for issue in all_issues],
        "policy": {
            "scope": "local_owned_or_explicitly_authorized_pages_only",
            "no_third_party_default_urls": True,
            "no_cookie_values_in_profiles": True,
            "local_cdp_only": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Profile Policy Report",
        "",
        f"Status: `{'OK' if report['ok'] else 'FAIL'}`",
        f"Profiles checked: `{len(report['checked'])}`",
        "",
        "## Policy",
        "",
        "- Profiles must set `authorized_only: true`.",
        "- Default URLs must be bundled demo files or localhost.",
        "- CDP attach endpoints must be localhost.",
        "- Profiles must not store cookie values.",
        "",
        "## Profiles",
        "",
        "| Profile | Authorized | URL | Issues |",
        "|---|---|---|---|",
    ]
    for profile in report["checked"]:
        issues = "; ".join(issue["message"] for issue in profile["issues"]) or "none"
        lines.append(f"| `{profile['path']}` | `{profile['authorized_only']}` | `{profile['url']}` | {issues} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit authorized profile JSON policy.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("examples")], help="Profile files or directories.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(args.paths)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
