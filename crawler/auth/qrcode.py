from __future__ import annotations

import logging

from playwright.async_api import Page

from .base import LoginStrategy


class QRCodeLoginStrategy(LoginStrategy):
    """QR code login strategy."""

    async def login(self, page: Page, login_url: str) -> bool:
        """Login by scanning a QR code."""
        try:
            logging.info("Starting QR code login")
            await page.goto(login_url, wait_until="domcontentloaded")
            await page.wait_for_selector("#quickCode", timeout=10000)
            logging.info("QR code is ready; waiting for scan")
            try:
                await page.wait_for_function(
                    "() => !location.href.includes('passport2.chaoxing.com')",
                    timeout=300000,
                )
                logging.info("QR code login succeeded")
                return True
            except Exception:
                logging.error("QR code login timed out")
                return False
        except Exception as exc:
            logging.error("QR code login failed: %s", exc)
            return False
