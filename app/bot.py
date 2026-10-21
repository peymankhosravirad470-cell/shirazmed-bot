# -*- coding: utf-8 -*-
"""ساخت Application اصلی ربات (python-telegram-bot v21+) با اتصال صریح به سرور بله."""

from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import settings
from app.handlers.start import start_handler, help_handler
from app.handlers.callbacks import main_menu_callback

logger = logging.getLogger(__name__)

# نکته: بدون این دو مقدار، PTB به‌صورت پیش‌فرض به api.telegram.org وصل می‌شود، نه بله.
_BALE_BASE_URL = "https://tapi.bale.ai/bot"
_BALE_BASE_FILE_URL = "https://tapi.bale.ai/file/bot"


def build_application() -> Application:
    """Application را می‌سازد، به سرور صحیح (بله/تلگرام) وصل می‌کند و هندلرها را ثبت می‌کند."""
    builder = Application.builder().token(settings.active_token)

    if settings.platform == "bale":
        builder = builder.base_url(_BALE_BASE_URL).base_file_url(_BALE_BASE_FILE_URL)
        logger.info("اتصال به بله تنظیم شد: %s", _BALE_BASE_URL)

    application = builder.build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CallbackQueryHandler(start_handler, pattern="^main:home$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main:"))

    logger.info("هندلرها ثبت شدند: /start, /help, main:home, main:*")
    return application
