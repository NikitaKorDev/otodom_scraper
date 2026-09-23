# otodom.pl rental scraper

Scrapes every listing matching an otodom.pl search URL (default: flats for rent
in Częstochowa, up to 1000 zł/month), follows pagination, then opens each offer
page to collect the description, photos and all published details. Optionally
runs a Gemini pass that flags hidden catches and works out the real monthly cost.

## Setup

    pip install -r requirements.txt
    playwright install chromium
    cp .env.example .env        # only needed for the AI pass

## Usage

    python main.py
    python main.py --headed --max-listings 5      # quick test run
    python main.py --download-images
    python main.py --url "https://www.otodom.pl/pl/wyniki/..."
    python main.py --ai-overview                  # scrape + AI pass
    python main.py --ai-only                      # AI pass over existing listings.json
    python main.py --debug                        # dump raw HTML per offer

## Project layout

    main.py                  entry point
    src/
      config.py              constants, env-driven defaults
      models.py              Listing dataclass
      cli.py                 argparse + orchestration
      utils/
        logger.py            log(), human_delay()
        text.py              clean_text, parse_zloty, walk_dicts, ...
        urls.py              build_page_url, upsize_image_url, guess_ext
      browser/
        session.py           browser_session() context manager
        actions.py           cookies, lazy-load, gallery, embedded JSON
      scraping/
        search.py            search cards, pagination, prefill
        extractors.py        __NEXT_DATA__ / JSON-LD / DOM extraction
        offer.py             scrape_listing() - one offer page
      ai/
        prompts.py           system prompt, response schema, prompt builder
        client.py            Gemini client + retry
        cache.py             ai_cache.json load/save
        overview.py          apply_ai_overview(), run_ai_pass()
      storage/
        outputs.py           listings.json / listings.csv read + write
        images.py            photo downloads

## Output (in ./otodom_output by default)

    listings.json     one record per listing, everything found
    listings.csv      flattened, spreadsheet-friendly version
    images/<id>/      photos (only with --download-images)
    debug/<id>.html   raw page HTML (only with --debug)
    ai_cache.json     one entry per listing ever sent to Gemini, so re-runs don't re-bill

## A note on reliability

otodom.pl is a Next.js app whose generated CSS class names change on most
deploys, so the extractors lean on stabler things, in this order:

1. `data-cy` / `data-testid` / `data-sentry-component` attributes
2. The `__NEXT_DATA__` JSON and schema.org JSON-LD blocks (`scraping/extractors.py`)
3. Regexes over rendered text, matched to Polish UI labels (`DOM_TEXT_PATTERNS`)

If markup changes break everything, run with `--debug` and adjust the selectors
in `scraping/search.py` and the patterns in `scraping/extractors.py`.
