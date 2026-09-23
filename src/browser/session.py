"""Browser lifecycle."""

from __future__ import annotations

from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from src.config import LOCALE, USER_AGENT, VIEWPORT


@contextmanager
def browser_session(headed: bool = False):
    """Yield (context, page) and always close the browser afterwards."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        try:
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale=LOCALE,
                viewport=VIEWPORT,
            )
            page = context.new_page()
            yield context, page
        finally:
            browser.close()
