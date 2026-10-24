# -*- coding: utf-8 -*-
"""نقطه‌ی ورود ربات شیراز مدیکال (v46) — اجرای هم‌زمان بله و (در صورت تنظیم) تلگرام."""

import asyncio
import logging
import os
import sys

from telegram import Update
from telegram.ext import Application

from app.bot import build_application
from app.health import start_health_server
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


async def _run_one(application: Application, label: str) -> None:
    """راه‌اندازی و نگه‌داشتن یک اپلیکیشن (بله یا تلگرام) با polling، تا زمان توقف."""
    async with application:
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        logger.info("پلتفرم '%s' با موفقیت روشن شد.", label)
        try:
            # تا وقتی برنامه کنسل نشده، زنده بمان
            await asyncio.Event().wait()
        finally:
            await application.updater.stop()
            await application.stop()


def _telegram_ready() -> bool:
    """بررسی اینکه آیا تنظیمات کافی برای روشن کردن تلگرام موجود است یا نه."""
    return bool(settings.telegram_bot_token.strip()) and bool(settings.telegram_bridge_url.strip())


async def _async_main() -> None:
    tasks = []

    # بله — همیشه روشن می‌شود (توکن آن اجباری است)
    bale_app = build_application("bale")
    tasks.append(asyncio.create_task(_run_one(bale_app, "bale")))

    # تلگرام — فقط اگر توکن و آدرس پل هر دو تنظیم شده باشند
    if _telegram_ready():
        telegram_app = build_application("telegram")
        tasks.append(asyncio.create_task(_run_one(telegram_app, "telegram")))
        logger.info("پلتفرم تلگرام فعال شد (توکن و پل هر دو تنظیم‌اند).")
    else:
        logger.info(
            "پلتفرم تلگرام غیرفعال است (TELEGRAM_BOT_TOKEN یا TELEGRAM_BRIDGE_URL تنظیم نشده). "
            "فقط بله اجرا می‌شود."
        )

    await asyncio.gather(*tasks)


def main() -> None:
    os.makedirs("data", exist_ok=True)
    try:
        start_health_server()
        asyncio.run(_async_main())
    except Exception as exc:
        logger.critical("خطای کشنده در راه‌اندازی ربات: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()