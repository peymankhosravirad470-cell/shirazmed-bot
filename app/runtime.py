# -*- coding: utf-8 -*-
"""
پل ارتباطی بین سرور health (ترد جداگانه) و event loop ربات.

سرور health برای هندل کردن callback پرداخت زرین‌پال باید بتواند از داخل یک ترد
غیر async، کوروتین‌های ربات (مثل send_message) را اجرا کند. برای این کار، بعد از
راه‌اندازی اپلیکیشن، reference مربوط به application و running loop اینجا ذخیره
می‌شود (از طریق post_init) و سرور health با run_coroutine_threadsafe کار می‌کند.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine, Optional

logger = logging.getLogger(__name__)

_application: Optional[Any] = None
_loop: Optional[asyncio.AbstractEventLoop] = None


def bind_application(application: Any) -> None:
    """در post_init (داخل event loop) صدا زده می‌شود و ربات را به runtime وصل می‌کند."""
    global _application, _loop
    _application = application
    try:
        _loop = asyncio.get_running_loop()
    except RuntimeError:
        _loop = None
    logger.info("Runtime bridge bound: application + event loop captured.")


def get_application() -> Optional[Any]:
    """برگرداندن application فعال (یا None اگر هنوز bind نشده)."""
    return _application


def schedule_coroutine(coro: Coroutine) -> bool:
    """
    اجرای یک کوروتین روی event loop ربات از داخل ترد دیگر.

    Returns:
        True اگر زمان‌بندی شد، False اگر ربات هنوز آماده نیست.
    """
    if _loop is None or _loop.is_closed():
        logger.warning("Event loop در دسترس نیست؛ کوروتین اجرا نشد.")
        coro.close()  # جلوگیری از RuntimeWarning "was never awaited"
        return False
    try:
        asyncio.run_coroutine_threadsafe(coro, _loop)
        return True
    except Exception as error:  # pragma: no cover
        logger.error("خطا در زمان‌بندی کوروتین از ترد health: %s", error)
        coro.close()
        return False