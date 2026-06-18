from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_profile(profile_path: str | Path, require_authorized: bool = True) -> dict[str, Any]:
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    if require_authorized:
        require_authorized_scope(profile)
    return profile


def require_authorized_scope(profile: dict[str, Any]) -> None:
    if profile.get("authorized_only") is not True:
        raise ValueError("Profile must set authorized_only=true. Only local/owned/authorized pages are supported.")


def resolve_url(url: str) -> str:
    if url.startswith(("http://", "https://", "file://")):
        return url
    return (ROOT / url).resolve().as_uri()


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
