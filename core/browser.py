from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


class BrowserManager:
    """Manage Playwright lifecycle, context pooling, and shared cookies."""

    def __init__(
        self,
        headless: bool = True,
        max_contexts: int = 10,
        download_path: Optional[str] = None,
    ) -> None:
        self.headless = headless
        self.max_contexts = max_contexts
        self.download_path = download_path

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._shared_cookies: List[Dict] = []
        self._context_semaphore = asyncio.Semaphore(max_contexts)

    async def start(self) -> None:
        """Start Playwright and launch a browser instance."""
        if self._playwright or self._browser:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        logging.info("Playwright browser started (headless=%s)", self.headless)

    async def stop(self) -> None:
        """Close browser and stop Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logging.info("Playwright browser stopped")

    async def __aenter__(self) -> "BrowserManager":
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.stop()

    def set_cookies(self, cookies: List[Dict]) -> None:
        """Store cookies for reuse across contexts."""
        self._shared_cookies = cookies

    def get_cookies(self) -> List[Dict]:
        """Return a copy of the shared cookies."""
        return list(self._shared_cookies)

    @asynccontextmanager
    async def new_context(self, with_cookies: bool = True) -> AsyncIterator[BrowserContext]:
        """Create a new context guarded by the semaphore."""
        if not self._browser:
            raise RuntimeError("Browser is not started")
        async with self._context_semaphore:
            context = await self._create_context()
            if with_cookies and self._shared_cookies:
                await context.add_cookies(self._shared_cookies)
            try:
                yield context
            finally:
                await context.close()

    async def _create_context(self) -> BrowserContext:
        """Create a browser context with defaults configured."""
        if not self._browser:
            raise RuntimeError("Browser is not started")
        options: Dict[str, object] = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if self.download_path:
            options["accept_downloads"] = True
            options["downloads_path"] = self.download_path
        context = await self._browser.new_context(**options)
        context.set_default_timeout(30000)
        return context

    async def new_page(self, url: Optional[str] = None) -> Page:
        """Create a standalone page and optionally navigate to a URL."""
        context = await self._create_context()
        if self._shared_cookies:
            await context.add_cookies(self._shared_cookies)
        page = await context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded")
        return page
