"""Low-level page interactions."""

from __future__ import annotations

import json
from typing import Optional

from playwright.sync_api import Page


def accept_cookies(page: Page) -> None:
    for sel in (
        "#onetrust-accept-btn-handler",
        "button:has-text('Akceptuję')",
        "button:has-text('AKCEPTUJĘ')",
        "[data-cy='accept-consent-button']",
    ):
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible():
                btn.click(timeout=3000)
                page.wait_for_timeout(400)
                return
        except Exception:
            continue


def get_next_data(page: Page) -> Optional[dict]:
    try:
        raw = page.evaluate(
            "() => { const el = document.querySelector('script#__NEXT_DATA__'); "
            "return el ? el.textContent : null; }"
        )
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def get_json_ld_blocks(page: Page) -> list:
    try:
        raw_list = page.eval_on_selector_all(
            "script[type='application/ld+json']",
            "els => els.map(e => e.textContent)",
        )
    except Exception:
        return []
    blocks = []
    for raw in raw_list:
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        blocks.extend(parsed if isinstance(parsed, list) else [parsed])
    return blocks


def nudge_lazy_load(page: Page) -> None:
    try:
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(400)
        page.mouse.wheel(0, -2000)
        page.wait_for_timeout(300)
    except Exception:
        pass


def open_full_gallery(page: Page) -> None:
    """Best-effort click to expand the photo gallery so lazy-loaded
    images actually land in the DOM. Harmless if none of these match."""
    for sel in (
        "button:has-text('Zobacz')",
        "[data-cy='gallery-strip-thumbnail']",
        "[data-testid='gallery-strip']",
    ):
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=2000)
                page.wait_for_timeout(500)
                page.keyboard.press("Escape")
                break
        except Exception:
            continue


def collect_gallery_images(page: Page) -> list:
    try:
        srcs = page.eval_on_selector_all(
            "img",
            "els => els.map(e => e.getAttribute('src') || e.getAttribute('data-src'))"
            ".filter(Boolean)",
        )
    except Exception:
        return []
    # keep only otodom's real photo CDN, drop logos/icons/avatars
    return list(dict.fromkeys(s for s in srcs if "olxcdn.com" in s))
