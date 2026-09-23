"""Search-results pages -> offer URLs (+ whatever the cards already show)."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PWTimeoutError

from src.browser.actions import accept_cookies
from src.config import BASE_URL, PAGE_LOAD_TIMEOUT_MS
from src.models import Listing
from src.utils.logger import log
from src.utils.text import clean_text
from src.utils.urls import build_page_url

SEARCH_CARD_JS = r"""
() => {
    const out = {};
    document.querySelectorAll('article[data-sentry-component="AdvertCard"]').forEach(card => {
        const linkEl = card.querySelector("a[data-cy='listing-item-link']");
        if (!linkEl) return;
        const href = linkEl.getAttribute('href');
        if (!href || href.startsWith('/hpr/')) return;   // hidden duplicate card

        const titleEl = card.querySelector("[data-cy='listing-item-title']");
        const addrEl = card.querySelector("[data-cy='advert-card-address']");
        const priceWrap = card.querySelector("[data-cy='listing-item-price']");
        const priceSpans = priceWrap ? Array.from(priceWrap.querySelectorAll('span')) : [];

        const specs = [];
        card.querySelectorAll('dl dt').forEach(dt => {
            const dd = dt.nextElementSibling;
            if (dd) specs.push(dd.textContent.trim());
        });

        const sellerInfoEl = card.querySelector('[data-sentry-component="SellerInfo"]');
        let sellerName = '';
        if (sellerInfoEl) {
            const span = sellerInfoEl.querySelector('span');
            if (span) sellerName = span.textContent.trim();
        }
        const sellerTypeEl = card.querySelector('[data-sentry-component="ConnectedOwnerType"]');

        out[href] = {
            title: titleEl ? titleEl.textContent.trim() : '',
            address: addrEl ? addrEl.textContent.trim() : '',
            price_main: priceSpans[0] ? priceSpans[0].textContent.trim() : '',
            price_secondary: priceSpans[1] ? priceSpans[1].textContent.trim() : '',
            specs: specs,
            seller_name: sellerName,
            advertiser_type: sellerTypeEl ? sellerTypeEl.textContent.trim() : '',
        };
    });
    return out;
}
"""


# --- card parsing helpers --------------------------------------------------- #

def classify_spec_value(value: str):
    """otodom's search-card spec list mislabels its <dt>s (every sample we
    inspected had dt='Cena za metr kwadratowy' but a dd like '32 m²',
    which is obviously an area, not a price) so we classify by what the
    *value* looks like rather than trusting the label."""
    v = value.strip()
    if re.search(r"pok[oó]j|pokoje|pokoi", v, re.IGNORECASE):
        return "rooms", v
    if re.search(r"m²", v):
        return "area", v
    if re.search(r"piętro|pietro|parter|suteren", v, re.IGNORECASE):
        return "floor", v
    return None


def parse_price_secondary(value: str) -> dict:
    """The small line under the main price on a search card is either
    '+ czynsz: 250 zł/miesiąc' or a plain '31,25 zł/m²' - split it out."""
    out = {}
    v = clean_text(value)
    m = re.search(r"czynsz:?\s*([\d\s,.]+\s*zł(?:/miesi[aą]c)?)", v, re.IGNORECASE)
    if m:
        out["rent"] = clean_text(m.group(1))
    elif re.search(r"zł\s*/\s*m", v, re.IGNORECASE):
        out["price_per_m2"] = v
    return out


def apply_prefill(listing: Listing, prefill: dict) -> None:
    """Seed a Listing with whatever the search card already showed."""
    if not prefill:
        return
    listing.title = listing.title or prefill.get("title", "")
    listing.address = listing.address or prefill.get("address", "")
    listing.price = listing.price or prefill.get("price_main", "")
    listing.seller_name = listing.seller_name or prefill.get("seller_name", "")
    listing.advertiser_type = listing.advertiser_type or prefill.get("advertiser_type", "")

    secondary = prefill.get("price_secondary", "")
    if secondary:
        parsed = parse_price_secondary(secondary)
        listing.rent = listing.rent or parsed.get("rent", "")
        listing.price_per_m2 = listing.price_per_m2 or parsed.get("price_per_m2", "")

    for value in prefill.get("specs", []):
        classified = classify_spec_value(value)
        if not classified:
            continue
        field_name, val = classified
        if not getattr(listing, field_name):
            setattr(listing, field_name, val)

    listing.source.append("search_card")


# --- crawling --------------------------------------------------------------- #

def extract_search_cards(page: Page) -> dict:
    try:
        data = page.evaluate(SEARCH_CARD_JS)
    except Exception:
        data = {}
    return {urljoin(BASE_URL, href).split("?")[0]: v for href, v in data.items()}


def collect_listing_urls(page: Page, search_url: str, max_pages: int = 50):
    """Returns (ordered_url_list, {url: prefill_dict})."""
    urls: list = []
    seen: set = set()
    prefill: dict = {}

    for page_num in range(1, max_pages + 1):
        url = build_page_url(search_url, page_num)
        log(f"Loading search results page {page_num}: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        accept_cookies(page)
        try:
            page.wait_for_selector("a[data-cy='listing-item-link']", timeout=12000)
        except PWTimeoutError:
            log("  no listings found - end of results.")
            break
        page.wait_for_timeout(700)

        cards = extract_search_cards(page)
        new_urls = [u for u in cards if u not in seen]
        log(f"  -> {len(cards)} cards, {len(new_urls)} new")

        if not cards or not new_urls:
            # empty page, or otodom silently looped back to page 1
            break

        for u in new_urls:
            seen.add(u)
            urls.append(u)
            prefill[u] = cards[u]

    return urls, prefill
