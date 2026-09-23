"""Open one offer page and assemble a full Listing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PWTimeoutError

from src.browser.actions import (
    accept_cookies,
    collect_gallery_images,
    get_json_ld_blocks,
    get_next_data,
    nudge_lazy_load,
    open_full_gallery,
)
from src.config import PAGE_LOAD_TIMEOUT_MS
from src.models import Listing
from src.scraping.extractors import fill_from_dom, fill_from_json_ld, fill_from_next_data
from src.scraping.search import apply_prefill
from src.utils.logger import log


def scrape_listing(
    page: Page,
    url: str,
    prefill: dict,
    debug_dir: Optional[Path] = None,
) -> Listing:
    listing = Listing(url=url)
    m = re.search(r"-ID([A-Za-z0-9]+)$", url)
    if m:
        listing.id = m.group(1)
    apply_prefill(listing, prefill)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        accept_cookies(page)
        page.wait_for_timeout(500)
        try:
            page.wait_for_selector("h1", timeout=10000)
        except PWTimeoutError:
            pass

        open_full_gallery(page)
        nudge_lazy_load(page)

        if debug_dir:
            (debug_dir / f"{listing.id or 'unknown'}.html").write_text(
                page.content(), encoding="utf-8"
            )

        next_data = get_next_data(page)
        found_json = fill_from_next_data(listing, next_data) if next_data else False

        if not found_json or not listing.description:
            fill_from_json_ld(listing, get_json_ld_blocks(page))

        if not found_json or not listing.description or not listing.rooms:
            fill_from_dom(page, listing)

        for src in collect_gallery_images(page):
            if src not in listing.images:
                listing.images.append(src)

    except Exception as exc:
        listing.error = f"{type(exc).__name__}: {exc}"
        log(f"  ERROR scraping {url}: {listing.error}")

    return listing
