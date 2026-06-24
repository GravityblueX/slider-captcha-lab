from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs" / "dependency-inventory.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "dependency-inventory.md"


def parse_requirements(path: Path) -> list[dict[str, str]]:
    dependencies: list[dict[str, str]] = []
    if not path.exists():
        return dependencies
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*([<>=!~].*)?$", line)
        if not match:
            dependencies.append({"name": line, "specifier": "", "source": str(path.relative_to(ROOT))})
            continue
        dependencies.append({
            "name": match.group(1),
            "specifier": (match.group(2) or "").strip(),
            "source": str(path.relative_to(ROOT)),
        })
    return dependencies


def parse_pyproject(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    result: dict[str, str] = {}
    for key in ["name", "version", "requires-python"]:
        match = re.search(rf'^{re.escape(key)}\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if match:
            result[key] = match.group(1)
    return result


def gate(name: str, ok: bool, detail: str) -> dict[str, object]:
    return {"name": name, "ok": ok, "detail": detail}


def build_inventory() -> dict[str, object]:
    requirements = parse_requirements(ROOT / "requirements.txt")
    pyproject = parse_pyproject(ROOT / "pyproject.toml")
    names = {dependency["name"].lower() for dependency in requirements}
    gates = [
        gate("requirements.txt exists", (ROOT / "requirements.txt").exists(), "requirements.txt"),
        gate("pyproject.toml exists", (ROOT / "pyproject.toml").exists(), "pyproject.toml"),
        gate("dependencies discovered", len(requirements) >= 3, f"{len(requirements)} requirement(s)"),
        gate("Playwright dependency recorded", "playwright" in names, "playwright"),
        gate("GUI dependency recorded", "pyside6" in names or "pyqt6" in names or "pandas" in names, "GUI/reporting runtime"),
        gate("project metadata recorded", bool(pyproject.get("name")), pyproject.get("name", "")),
    ]
    failures = [item for item in gates if not item["ok"]]
    return {
        "report_type": "slider_dependency_inventory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": len(failures) == 0,
        "project": pyproject,
        "dependencies": requirements,
        "gates": gates,
        "failures": failures,
        "reference_patterns": [
            "Python dependency inventory from requirements and pyproject metadata",
            "OWASP SCVS style component visibility before packaging",
            "Local dependency evidence without installing or probing third-party services",
        ],
    }


def render_markdown(inventory: dict[str, object]) -> str:
    lines = [
        "# Dependency Inventory",
        "",
        f"Generated: {inventory['generated_at']}",
        f"Status: `{'OK' if inventory['ok'] else 'FAIL'}`",
        f"Project: `{inventory['project'].get('name', '')}`",
        "",
        "## Gates",
        "",
        "| Gate | Result | Detail |",
        "|---|---|---|",
    ]
    for item in inventory["gates"]:
        lines.append(f"| {item['name']} | {'OK' if item['ok'] else 'FAIL'} | {item['detail']} |")
    lines.extend(["", "## Dependencies", "", "| Name | Specifier | Source |", "|---|---|---|"])
    for dependency in inventory["dependencies"]:
        lines.append(f"| `{dependency['name']}` | `{dependency['specifier']}` | `{dependency['source']}` |")
    lines.extend(["", "## Boundary", ""])
    lines.append("- This inventory records local project dependencies only.")
    lines.append("- It does not fetch, execute, or probe third-party websites.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the slider lab dependency inventory.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    inventory = build_inventory()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(render_markdown(inventory), encoding="utf-8")
    print(json.dumps({"ok": inventory["ok"], "json": str(args.json_out), "markdown": str(args.markdown_out)}, indent=2))
    return 0 if inventory["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
