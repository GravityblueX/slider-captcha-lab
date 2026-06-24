from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs" / "safety-contract.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "safety-contract.md"
SCOPE = "local_owned_or_explicitly_authorized_pages_only"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def contains_cookie_values(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in {"cookie", "cookies", "cookie_value", "cookievalue"}:
                return True
            if contains_cookie_values(nested):
                return True
    if isinstance(value, list):
        return any(contains_cookie_values(item) for item in value)
    return False


def gate(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def build_contract() -> dict[str, Any]:
    readme = read_text(ROOT / "README.md")
    disclaimer = read_text(ROOT / "DISCLAIMER.md")
    profile_policy = load_json(ROOT / "docs" / "profile-policy-report.json")
    target_surface = load_json(ROOT / "docs" / "target-surface-registry.json")
    evidence_manifest = load_json(ROOT / "docs" / "evidence-manifest.json")
    evidence_pack = load_json(ROOT / "docs" / "authorized-evidence-pack-local-demo.json")

    profiles = target_surface.get("profiles", [])
    combined_text = f"{readme}\n{disclaimer}"
    gates = [
        gate("README states non-bypass boundary", "请勿用于" in combined_text and "验证码" in combined_text and "风控" in combined_text, "README.md + DISCLAIMER.md"),
        gate("profile policy ok", profile_policy.get("ok") is True, str(profile_policy.get("ok"))),
        gate("target surface registry ok", target_surface.get("ok") is True, str(target_surface.get("ok"))),
        gate("evidence manifest ok", evidence_manifest.get("ok") is True, str(evidence_manifest.get("ok"))),
        gate("evidence pack does not solve CAPTCHA", evidence_pack.get("safety", {}).get("does_not_solve_captcha") is True, str(evidence_pack.get("safety", {}).get("does_not_solve_captcha"))),
        gate("all default targets local", all(profile.get("localDefaultUrl") is True for profile in profiles), f"{len(profiles)} profile(s)"),
        gate("all profiles authorized only", all(profile.get("authorizedOnly") is True for profile in profiles), f"{len(profiles)} profile(s)"),
        gate("all CDP endpoints local", all(profile.get("localCdpEndpoint") is True for profile in profiles), f"{len(profiles)} profile(s)"),
        gate("no cookie values in generated evidence", not any(contains_cookie_values(item) for item in [profile_policy, target_surface, evidence_manifest, evidence_pack]), "cookie keys absent"),
    ]
    failures = [item for item in gates if not item["ok"]]
    return {
        "report_type": "slider_safety_contract",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "ok": len(failures) == 0,
        "gates": gates,
        "failures": failures,
        "reference_patterns": [
            "Authorization boundary as an executable local contract",
            "Browser diagnostics evidence must avoid cookie values",
            "Default targets must remain local demo, owned, or explicitly authorized",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    lines = [
        "# Safety Contract",
        "",
        f"Generated: {contract['generated_at']}",
        f"Scope: `{contract['scope']}`",
        f"Status: `{'OK' if contract['ok'] else 'FAIL'}`",
        "",
        "## Gates",
        "",
        "| Gate | Result | Detail |",
        "|---|---|---|",
    ]
    for item in contract["gates"]:
        lines.append(f"| {item['name']} | {'OK' if item['ok'] else 'FAIL'} | {item['detail']} |")
    lines.extend(["", "## Boundary", ""])
    lines.append("- This contract is for local, owned, or explicitly authorized browser diagnostics.")
    lines.append("- It rejects third-party default targets, CAPTCHA solving claims, and stored cookie values.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the slider lab safety contract.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    contract = build_contract()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(json.dumps({"ok": contract["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if contract["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
