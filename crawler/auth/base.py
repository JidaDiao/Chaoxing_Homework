from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from playwright.async_api import Page


class LoginStrategy(ABC):
    """Base login strategy interface."""

    @abstractmethod
    async def login(self, page: Page, login_url: str) -> bool:
        """Perform login on the given page."""
        raise NotImplementedError

    async def get_cookies(self, page: Page) -> List[Dict]:
        """Return cookies after login."""
        return await page.context.cookies()
