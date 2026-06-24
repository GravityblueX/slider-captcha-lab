from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs" / "evidence-manifest.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "evidence-manifest.md"
SCOPE = "local_owned_or_explicitly_authorized_pages_only"


@dataclass(frozen=True)
class EvidenceItem:
    path: str
    kind: str
    purpose: str
    required_ok: bool = False


EVIDENCE_ITEMS = [
    EvidenceItem(
        "docs/authorized-evidence-pack-local-demo.json",
        "json",
        "local demo browser evidence pack",
        required_ok=True,
    ),
    EvidenceItem(
        "docs/authorized-evidence-pack-local-demo.md",
        "markdown",
        "human-readable authorized evidence summary",
    ),
    EvidenceItem(
        "docs/profile-policy-report.json",
        "json",
        "profile authorization and local-default policy",
        required_ok=True,
    ),
    EvidenceItem(
        "docs/profile-policy-report.md",
        "markdown",
        "human-readable profile policy report",
    ),
    EvidenceItem(
        "docs/target-surface-registry.json",
        "json",
        "authorized browser target and surface registry",
        required_ok=True,
    ),
    EvidenceItem(
        "docs/target-surface-registry.md",
        "markdown",
        "human-readable authorized target surface registry",
    ),
    EvidenceItem(
        "docs/cdp-authorized-diagnostics.md",
        "markdown",
        "authorized Chrome DevTools Protocol diagnostics notes",
    ),
    EvidenceItem(
        "docs/deep-page-map.md",
        "markdown",
        "deep page and frame mapping notes",
    ),
    EvidenceItem(
        "docs/trace-artifacts/local-demo-trace.json",
        "json",
        "local screenshot and selector visibility trace",
        required_ok=True,
    ),
    EvidenceItem(
        "docs/trace-artifacts/local-demo-trace.md",
        "markdown",
        "human-readable local trace artifact summary",
    ),
    EvidenceItem(
        "docs/trace-artifacts/local-demo.png",
        "image",
        "local demo screenshot evidence",
    ),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_stored_cookie_value(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in {"cookie", "cookies", "cookie_value", "cookievalue"}:
                return True
            if contains_stored_cookie_value(nested):
                return True
    elif isinstance(value, list):
        return any(contains_stored_cookie_value(item) for item in value)
    return False


def inspect_item(item: EvidenceItem) -> dict[str, Any]:
    path = ROOT / item.path
    result: dict[str, Any] = {
        "path": item.path,
        "kind": item.kind,
        "purpose": item.purpose,
        "exists": path.exists(),
        "ok": False,
        "checks": [],
    }
    if not path.exists():
        result["checks"].append({"name": "exists", "ok": False, "detail": item.path})
        return result

    result["checks"].append({"name": "exists", "ok": True, "detail": item.path})
    if item.kind == "image":
        result["checks"].append({"name": "not empty", "ok": path.stat().st_size > 0, "detail": f"{path.stat().st_size} bytes"})
    elif item.kind == "json":
        payload = load_json(path)
        if item.required_ok:
            result["checks"].append({"name": "ok flag", "ok": payload.get("ok") is True, "detail": str(payload.get("ok"))})
        raw = json.dumps(payload, ensure_ascii=False).lower()
        scope_ok = SCOPE in raw
        result["checks"].append({"name": "authorized scope", "ok": scope_ok, "detail": SCOPE})
        no_cookie_values = not contains_stored_cookie_value(payload)
        result["checks"].append({"name": "no cookie values", "ok": no_cookie_values, "detail": "no stored cookie values"})
        if item.path.endswith("authorized-evidence-pack-local-demo.json") or item.path.endswith("local-demo-trace.json"):
            no_solver = payload.get("safety", {}).get("does_not_solve_captcha") is True
            result["checks"].append({"name": "does not solve captcha", "ok": no_solver, "detail": str(no_solver)})
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        result["checks"].append({"name": "not empty", "ok": bool(text.strip()), "detail": f"{len(text)} chars"})
        if item.path.endswith(".md") and ("authorized" in text.lower() or "授权" in text or "local" in text.lower()):
            result["checks"].append({"name": "scope language", "ok": True, "detail": "authorized/local wording found"})

    result["ok"] = all(check["ok"] for check in result["checks"])
    return result


def build_manifest() -> dict[str, Any]:
    items = [inspect_item(item) for item in EVIDENCE_ITEMS]
    failures = [
        {"path": item["path"], "checks": [check for check in item["checks"] if not check["ok"]]}
        for item in items
        if not item["ok"]
    ]
    return {
        "report_type": "authorized_evidence_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "ok": len(failures) == 0,
        "items": items,
        "failures": failures,
        "reference_patterns": [
            "Playwright Trace Viewer: inspectable artifacts instead of opaque automation claims",
            "Chrome DevTools Protocol Page domain: frame/page state is explicit evidence",
            "OpenSSF Scorecard: local gates make project health reviewable",
        ],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Authorized Evidence Manifest",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Scope: `{manifest['scope']}`",
        f"Status: `{'OK' if manifest['ok'] else 'FAIL'}`",
        "",
        "## Evidence Items",
        "",
        "| Artifact | Result | Purpose |",
        "|---|---|---|",
    ]
    for item in manifest["items"]:
        lines.append(f"| `{item['path']}` | {'OK' if item['ok'] else 'FAIL'} | {item['purpose']} |")
    lines.extend(["", "## Reference Patterns", ""])
    for pattern in manifest["reference_patterns"]:
        lines.append(f"- {pattern}")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- This manifest is for local, owned, or explicitly authorized browser diagnostics.",
        "- It does not solve CAPTCHA challenges, evade bot defenses, or store cookie values.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an authorized diagnostics evidence manifest.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    manifest = build_manifest()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(manifest), encoding="utf-8")
    print(json.dumps({"ok": manifest["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
