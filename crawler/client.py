from __future__ import annotations

import logging
from typing import Dict, List, Optional

from playwright.async_api import Page, Response


class CrawlerClient:
    """Lightweight wrapper around Playwright page for common fetch helpers."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self._captured_urls: Dict[str, str] = {}
        self._captured_responses: Dict[str, Response] = {}

    async def setup_response_capture(self, patterns: List[str]) -> None:
        """Attach a response listener to capture URLs matching patterns."""
        def on_response(response: Response) -> None:
            for pattern in patterns:
                if pattern in response.url:
                    self._captured_urls[pattern] = response.url
                    self._captured_responses[pattern] = response
                    logging.debug("Captured response %s -> %s", pattern, response.url)

        self.page.on("response", on_response)

    def get_captured_url(self, pattern: str) -> Optional[str]:
        """Return the captured URL for a given pattern."""
        return self._captured_urls.get(pattern)

    async def get_captured_json(self, pattern: str) -> Optional[Dict]:
        """Return captured response JSON for a given pattern."""
        response = self._captured_responses.get(pattern)
        if not response:
            return None
        try:
            return await response.json()
        except Exception:
            return None

    def clear_captures(self) -> None:
        """Clear captured URLs and responses."""
        self._captured_urls.clear()
        self._captured_responses.clear()

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> None:
        """Navigate to a URL with the specified load state."""
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)

    async def wait_for_navigation(self, timeout: int = 30000) -> None:
        """Wait for the page to reach domcontentloaded."""
        await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)

    async def fetch_html(self, url: str) -> str:
        """Fetch HTML content via Playwright's request API."""
        response = await self.page.request.get(url)
        return await response.text()

    async def fetch_json(self, url: str) -> Optional[Dict]:
        """Fetch JSON content via Playwright's request API."""
        try:
            response = await self.page.request.get(url)
            if response.ok:
                return await response.json()
        except Exception as exc:
            logging.error("Failed to fetch JSON from %s: %s", url, exc)
        return None

    async def get_cookies_dict(self) -> Dict[str, str]:
        """Return cookies as a name/value mapping."""
        cookies = await self.page.context.cookies()
        return {cookie["name"]: cookie["value"] for cookie in cookies}

    async def download_file(self, url: str, save_path: str) -> bool:
        """Download a file to the given path."""
        try:
            response = await self.page.request.get(url)
            if response.ok:
                content = await response.body()
                with open(save_path, "wb") as handle:
                    handle.write(content)
                return True
        except Exception as exc:
            logging.error("Failed to download file %s: %s", url, exc)
        return False
