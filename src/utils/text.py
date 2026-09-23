"""Text and data-structure helpers."""

from __future__ import annotations

import re
from typing import Optional


def clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    return name or "listing"


def parse_zloty(text: Optional[str]) -> Optional[float]:
    """Pull the first PLN amount out of a string like '950 zł',
    '1 000 zł/miesiąc' or '31,25 zł/m²'. Returns None if nothing numeric
    is found."""
    if not text:
        return None
    t = text.replace("\xa0", " ")
    m = re.search(r"(\d[\d ]*(?:[.,]\d+)?)", t)
    if not m:
        return None
    num = m.group(1).replace(" ", "").replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None


def walk_dicts(obj):
    """Yield every dict found anywhere inside a nested dict/list structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_dicts(v)
