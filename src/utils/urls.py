"""URL helpers."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


def guess_ext(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.split(";")[0]
    return ext if ext and len(ext) <= 5 else ".jpg"


def upsize_image_url(url: str, target: str = "1280x1024") -> str:
    """otodom's apollo CDN URLs carry a ';s=WxH' size hint - ask for a
    bigger version than the search-card thumbnail where possible."""
    return re.sub(r"s=\d+x\d+", f"s={target}", url)


def build_page_url(base_search_url: str, page_num: int) -> str:
    """Return the search URL with the right ?page= parameter."""
    parsed = urlparse(base_search_url)
    qs = parse_qs(parsed.query)
    if page_num > 1:
        qs["page"] = [str(page_num)]
    else:
        qs.pop("page", None)
    return parsed._replace(query=urlencode(qs, doseq=True)).geturl()
