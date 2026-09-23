"""Apply the AI analysis to listings (cache-first) and run it over a batch."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from src.ai.cache import load_ai_cache, save_ai_cache
from src.ai.client import analyze_with_gemini, make_gemini_client
from src.models import Listing
from src.storage.outputs import save_outputs
from src.utils.logger import human_delay, log
from src.utils.text import parse_zloty


def apply_ai_overview(listing: Listing, ai_cache: dict, client, model: str) -> bool:
    """Fill in listing.ai_* from the cache, or from a fresh Gemini call if
    this listing (by id) has never been analyzed before. Returns True if a
    new API call was actually made (so callers can rate-limit only those)."""
    key = listing.id or listing.url

    cached = ai_cache.get(key)
    if cached:
        listing.ai_hidden_catches = cached.get("hidden_catches", [])
        listing.ai_extra_monthly_cost = cached.get("extra_monthly_recurring_cost_pln")
        listing.ai_extra_cost_note = cached.get("extra_cost_explanation", "")
        listing.ai_summary = cached.get("summary_pl", "")
        listing.ai_total_monthly_price = cached.get("total_monthly_pln")
        listing.source.append("ai_cache")
        log(f"    AI: cached result reused for {key}")
        return False

    if not listing.description:
        listing.ai_summary = "(skipped: no description to analyze)"
        return False

    try:
        result = analyze_with_gemini(client, model, listing)
    except Exception as exc:
        log(f"    AI analysis failed for {listing.url}: {exc}")
        listing.ai_summary = f"(AI analysis failed: {exc})"
        listing.error = listing.error or f"AI error: {exc}"
        return True  # an API call was attempted; still rate-limit the next one

    base_price = parse_zloty(listing.price)
    czynsz = parse_zloty(listing.rent)
    extra = result.get("extra_monthly_recurring_cost_pln")
    extra_val = float(extra) if isinstance(extra, (int, float)) else None

    known = [v for v in (base_price, czynsz, extra_val) if v is not None]
    total = sum(known) if known else None

    listing.ai_hidden_catches = result.get("hidden_catches", []) or []
    listing.ai_extra_monthly_cost = extra_val
    listing.ai_extra_cost_note = result.get("extra_cost_explanation", "")
    listing.ai_summary = result.get("summary_pl", "")
    listing.ai_total_monthly_price = total
    listing.source.append("ai")

    ai_cache[key] = {
        "url": listing.url,
        "hidden_catches": listing.ai_hidden_catches,
        "extra_monthly_recurring_cost_pln": extra_val,
        "extra_cost_explanation": listing.ai_extra_cost_note,
        "summary_pl": listing.ai_summary,
        "total_monthly_pln": total,
        "model": model,
        "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return True


def run_ai_pass(listings: list, out_dir: Path, model: str, api_key: Optional[str]) -> None:
    client = make_gemini_client(api_key)  # raises a clear error if key/pkg missing
    cache_path = out_dir / "ai_cache.json"
    ai_cache = load_ai_cache(cache_path)
    log(f"AI overview: {len(ai_cache)} listing(s) already cached in {cache_path}")

    for i, listing in enumerate(listings, start=1):
        log(f"[AI {i}/{len(listings)}] {listing.url}")
        made_call = apply_ai_overview(listing, ai_cache, client, model)
        save_ai_cache(cache_path, ai_cache)   # persist the cache after every listing
        save_outputs(listings, out_dir)       # and the merged listings too
        if made_call:
            human_delay(1.0, 2.5)  # only throttle actual API calls, not cache hits
