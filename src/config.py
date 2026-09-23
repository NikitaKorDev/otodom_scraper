"""Central configuration: constants and environment-driven defaults."""

from __future__ import annotations

import os

try:  # python-dotenv is a convenience, not a hard requirement
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_URL = "https://www.otodom.pl"

DEFAULT_SEARCH_URL = (
    "https://www.otodom.pl/pl/wyniki/wynajem/mieszkanie/slaskie/"
    "czestochowa/czestochowa/czestochowa"
    "?ownerTypeSingleSelect=ALL&priceMax=1000"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

LOCALE = "pl-PL"
VIEWPORT = {"width": 1366, "height": 900}
PAGE_LOAD_TIMEOUT_MS = 45_000

DEFAULT_OUTPUT_DIR = "otodom_output"
DEFAULT_MAX_PAGES = 50

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
