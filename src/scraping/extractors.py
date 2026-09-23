"""Fill a Listing from the three data sources on an offer page.

Order of preference (most to least stable):
  1. __NEXT_DATA__ JSON embedded by Next.js
  2. schema.org JSON-LD blocks
  3. Regexes over the rendered page text, matched against Polish UI labels
"""

from __future__ import annotations

import re

from playwright.sync_api import Page

from src.models import Listing
from src.utils.text import clean_text, walk_dicts

# Substring of the characteristic's key/label -> Listing field.
# Order matters: the first needle that matches wins.
CHARACTERISTIC_KEY_MAP = {
    "rent": "rent", "czynsz": "rent",
    "area": "area", "m2": "area", "powierzchnia": "area",
    "room": "rooms", "pok": "rooms",
    "floor": "floor", "pietro": "floor", "piętro": "floor",
    "heat": "heating", "ogrzew": "heating",
    "deposit": "deposit", "kaucj": "deposit",
    "avail": "available_from", "dostep": "available_from",
    "condition": "condition", "wykonczen": "condition",
    "price": "price", "cena": "price",
}

DOM_TEXT_PATTERNS = {
    "rooms": r"Liczba pok[oó]i:?\s*\n?\s*([^\n]+)",
    "area": r"Powierzchnia:?\s*\n?\s*([^\n]+)",
    "floor": r"Piętro:?\s*\n?\s*([^\n]+)",
    "heating": r"Ogrzewanie:?\s*\n?\s*([^\n]+)",
    "condition": r"Stan wyko[nń]czenia:?\s*\n?\s*([^\n]+)",
    "available_from": r"Dost[eę]pne od:?\s*\n?\s*([^\n]+)",
    "rent": r"Czynsz:?\s*\n?\s*([^\n]+)",
    "deposit": r"Kaucja:?\s*\n?\s*([^\n]+)",
    "advertiser_type": r"Typ og[lł]oszeniodawcy:?\s*\n?\s*([^\n]+)",
    "extra_info": r"Informacje dodatkowe:?\s*\n?\s*([^\n]+)",
}


# --- 1. __NEXT_DATA__ ------------------------------------------------------- #

def _find_ad_node(data: dict):
    for node in walk_dicts(data):
        keys = set(node.keys())
        if {"title", "description"} <= keys or {"title", "images"} <= keys:
            return node
    return None


def _fill_images_from_ad(listing: Listing, ad: dict) -> None:
    for im in ad.get("images") or ad.get("photos") or []:
        if isinstance(im, str):
            src = im
        elif isinstance(im, dict):
            src = im.get("large") or im.get("medium") or im.get("url") or im.get("small")
        else:
            src = None
        if src and src not in listing.images:
            listing.images.append(src)


def _fill_characteristics_from_ad(listing: Listing, ad: dict) -> None:
    for c in ad.get("characteristics") or []:
        if not isinstance(c, dict):
            continue
        key = (c.get("key") or c.get("label") or "").lower()
        val = str(c.get("localizedValue") or c.get("value") or "")
        if not val:
            continue
        for needle, field_name in CHARACTERISTIC_KEY_MAP.items():
            if needle in key and not getattr(listing, field_name):
                setattr(listing, field_name, val)
                break


def _fill_address_from_ad(listing: Listing, ad: dict) -> None:
    loc = ad.get("location")
    addr = loc.get("address") if isinstance(loc, dict) else None
    if not isinstance(addr, dict) or listing.address:
        return
    parts = []
    for k in ("street", "district", "city", "province"):
        p = addr.get(k)
        if isinstance(p, dict):
            p = p.get("name")
        if p:
            parts.append(p)
    if parts:
        listing.address = ", ".join(parts)


def fill_from_next_data(listing: Listing, data: dict) -> bool:
    ad = _find_ad_node(data)
    if not ad:
        return False

    listing.raw["next_data_ad"] = ad
    listing.title = listing.title or str(ad.get("title", ""))
    if ad.get("description"):
        listing.description = listing.description or clean_text(str(ad["description"]))

    _fill_images_from_ad(listing, ad)
    _fill_characteristics_from_ad(listing, ad)
    _fill_address_from_ad(listing, ad)

    owner = ad.get("owner") or ad.get("advertiser")
    if isinstance(owner, dict):
        listing.seller_name = listing.seller_name or str(owner.get("name", ""))
        listing.advertiser_type = listing.advertiser_type or str(owner.get("type", ""))

    listing.source.append("next_data")
    return True


# --- 2. JSON-LD ------------------------------------------------------------- #

def fill_from_json_ld(listing: Listing, blocks: list) -> None:
    for b in blocks:
        if not isinstance(b, dict):
            continue
        listing.title = listing.title or b.get("name", "")
        if b.get("description") and not listing.description:
            listing.description = clean_text(str(b["description"]))
        imgs = b.get("image")
        if imgs:
            imgs = [imgs] if isinstance(imgs, str) else imgs
            for im in imgs:
                if isinstance(im, str) and im not in listing.images:
                    listing.images.append(im)
        offers = b.get("offers")
        if isinstance(offers, dict) and offers.get("price") and not listing.price:
            listing.price = str(offers["price"])
        if b.get("name") or b.get("description") or b.get("image"):
            listing.source.append("json_ld")


# --- 3. DOM / rendered text ------------------------------------------------- #

def fill_from_dom(page: Page, listing: Listing) -> None:
    def text_of(selector: str) -> str:
        try:
            loc = page.locator(selector).first
            if loc.count():
                return clean_text(loc.inner_text(timeout=3000))
        except Exception:
            pass
        return ""

    if not listing.title:
        listing.title = text_of("h1") or clean_text(page.title())

    if not listing.price:
        listing.price = (
            text_of("[data-cy='adPageHeaderPrice']")
            or text_of("strong[data-cy='price']")
        )

    if not listing.address:
        listing.address = text_of("[data-cy='adPageAdLocation']")

    try:
        body_text = page.locator("body").inner_text(timeout=5000)
    except Exception:
        body_text = ""
    if body_text:
        listing.raw["dom_full_text"] = body_text[:20000]

    if not listing.description:
        for sel in ("[data-cy='adPageAdDescription']", "[data-testid='ad.description']"):
            desc = text_of(sel)
            if len(desc) > 40:
                listing.description = desc
                break
        if not listing.description and body_text:
            m = re.search(
                r"\nOpis\n+(.*?)\n(?:ID:|Chcesz mieć na oku|Nr w biurze:)",
                body_text,
                re.DOTALL,
            )
            if m:
                listing.description = clean_text(m.group(1))

    for field_name, pattern in DOM_TEXT_PATTERNS.items():
        if getattr(listing, field_name) or not body_text:
            continue
        m = re.search(pattern, body_text, re.IGNORECASE)
        if m:
            setattr(listing, field_name, clean_text(m.group(1)))

    listing.source.append("dom")
