"""
Shared Playwright helpers: Chromium launch, realistic browser context, goto helper.
Comments in English per project convention.
"""

from contextlib import contextmanager
from typing import Generator

from playwright.sync_api import Page, sync_playwright


@contextmanager
def browser_page(
    headless: bool = True,
    *,
    locale: str = "vi-VN",
    timezone_id: str = "Asia/Ho_Chi_Minh",
) -> Generator[Page, None, None]:
    """Yields a Page; navigate to the target site before API calls that need cookies."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale=locale,
            timezone_id=timezone_id,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()


def goto_ready(page: Page, url: str, wait_until: str = "domcontentloaded") -> None:
    page.goto(url, wait_until=wait_until, timeout=60_000)
