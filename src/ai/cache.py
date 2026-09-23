"""On-disk cache so the same listing is never billed twice."""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.logger import log


def load_ai_cache(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            log(f"  could not read AI cache at {path}, starting fresh")
    return {}


def save_ai_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
