from __future__ import annotations

from .base import LoginStrategy
from .password import PasswordLoginStrategy
from .qrcode import QRCodeLoginStrategy


def create_login_strategy(config) -> LoginStrategy:
    if getattr(config, "use_qr_code", False):
        return QRCodeLoginStrategy()
    return PasswordLoginStrategy(
        getattr(config, "phonenumber", ""),
        getattr(config, "password", ""),
    )


__all__ = ["LoginStrategy", "QRCodeLoginStrategy", "PasswordLoginStrategy", "create_login_strategy"]
