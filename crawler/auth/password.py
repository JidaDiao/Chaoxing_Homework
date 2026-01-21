from __future__ import annotations

import logging

from playwright.async_api import Page

from .base import LoginStrategy


class PasswordLoginStrategy(LoginStrategy):
    """Password-based login strategy."""

    def __init__(self, phonenumber: str, password: str) -> None:
        self.phonenumber = phonenumber
        self.password = password

    async def login(self, page: Page, login_url: str) -> bool:
        """Login with phone number and password."""
        try:
            logging.info("Starting password login")
            await page.goto(login_url, wait_until="domcontentloaded")
            await page.wait_for_selector("#phone", timeout=10000)
            await page.fill("#phone", self.phonenumber or "")
            await page.fill("#pwd", self.password or "")
            await page.click("#loginBtn")
            try:
                await page.wait_for_function(
                    "() => !location.href.includes('passport2.chaoxing.com')",
                    timeout=10000,
                )
                logging.info("Password login succeeded")
                return True
            except Exception:
                logging.error("Password login timeout or failure")
                return False
        except Exception as exc:
            logging.error("Password login failed: %s", exc)
            return False
