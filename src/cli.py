"""Command-line interface and top-level orchestration."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ai.overview import run_ai_pass
from src.browser.session import browser_session
from src.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SEARCH_URL,
)
from src.scraping.offer import scrape_listing
from src.scraping.search import collect_listing_urls
from src.storage.images import download_images
from src.storage.outputs import load_listings, save_outputs
from src.utils.logger import human_delay, log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape otodom.pl rental listings.")
    parser.add_argument("--url", default=DEFAULT_SEARCH_URL, help="otodom search-results URL")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="safety cap on result pages")
    parser.add_argument("--max-listings", type=int, default=None, help="stop after N listings (handy for testing)")
    parser.add_argument("--headed", action="store_true", help="show the browser window instead of headless")
    parser.add_argument("--download-images", action="store_true", help="also download every photo to disk")
    parser.add_argument("--debug", action="store_true", help="dump each offer page's raw HTML for inspection")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_DIR, help="output directory")
    parser.add_argument(
        "--ai-overview", action="store_true",
        help="after scraping, ask Gemini to flag hidden catches and work out the real total monthly price",
    )
    parser.add_argument(
        "--ai-only", action="store_true",
        help="skip scraping entirely; run the AI pass over an existing listings.json in --out",
    )
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL, help="Gemini model name")
    parser.add_argument("--gemini-api-key", default=None, help="overrides the GEMINI_API_KEY env var")
    return parser


def run_ai_only(args: argparse.Namespace, out_dir: Path) -> None:
    listings_path = out_dir / "listings.json"
    if not listings_path.exists():
        raise SystemExit(
            f"--ai-only needs an existing {listings_path} - run a normal scrape first."
        )
    listings = load_listings(listings_path)
    log(f"Loaded {len(listings)} listings from {listings_path} for the AI pass.")
    run_ai_pass(listings, out_dir, args.gemini_model, args.gemini_api_key)
    log(f"Done. AI overview updated for {len(listings)} listings in {out_dir}/listings.json")


def run_scrape(args: argparse.Namespace, out_dir: Path, debug_dir: Path | None) -> list:
    with browser_session(headed=args.headed) as (context, page):
        urls, prefill = collect_listing_urls(page, args.url, max_pages=args.max_pages)
        log(f"Found {len(urls)} unique listing URLs.")
        if args.max_listings:
            urls = urls[: args.max_listings]

        listings: list = []
        for i, url in enumerate(urls, start=1):
            log(f"[{i}/{len(urls)}] {url}")
            listing = scrape_listing(page, url, prefill.get(url, {}), debug_dir)
            listings.append(listing)
            save_outputs(listings, out_dir)  # persist after every listing
            human_delay()

        if args.download_images:
            log("Downloading images...")
            download_images(listings, out_dir / "images", context)

    return listings


def main() -> None:
    args = build_parser().parse_args()

    out_dir = Path(args.out)
    debug_dir = out_dir / "debug" if args.debug else None
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)

    if args.ai_only:
        run_ai_only(args, out_dir)
        return

    listings = run_scrape(args, out_dir, debug_dir)

    if args.ai_overview:
        run_ai_pass(listings, out_dir, args.gemini_model, args.gemini_api_key)

    log(f"Done. {len(listings)} listings saved to {out_dir}/listings.json and listings.csv")
