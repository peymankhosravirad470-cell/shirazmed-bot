# -*- coding: utf-8 -*-
"""ساخت Application اصلی ربات و ثبت هندلرها."""

from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import settings
from app.handlers.start import start_handler, help_handler
from app.handlers.callbacks import main_menu_callback

logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Application را می‌سازد و هندلرها را ثبت می‌کند."""
    logger.info("Building application for platform: %s", settings.platform)
    
    builder = Application.builder().token(settings.active_token)
    
    # تنظیم آدرس سرور برای بله
    if settings.platform == "bale":
        logger.info("Configuring Bale base URLs...")
        builder = builder.base_url("https://tapi.bale.ai/bot")
        builder = builder.base_file_url("https://tapi.bale.ai/file/bot")
    
    application = builder.build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CallbackQueryHandler(start_handler, pattern="^main:home$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main:"))

    logger.info("Handlers registered successfully.")
    return application