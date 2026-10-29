# -*- coding: utf-8 -*-
"""نقطه‌ی ورود ربات شیراز مدیکال (v46)."""

import logging
import os
import sys

from telegram import Update

from app.bot import build_application
from app.health import start_health_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """راه‌اندازی و اجرای ربات با polling (آپدیت‌های تأییدنشده‌ی حین ری‌استارت هم پاسخ می‌گیرند)."""
    os.makedirs("data", exist_ok=True)
    try:
        start_health_server()
        application = build_application()
        # 🆕 Bug2: آپدیت‌های ارسال‌شده در فاصله‌ی ری‌استارت (مثلاً حین deploy
        # لایارا) دور ریخته نمی‌شوند — اگر کاربر حین ری‌استارت /start زده باشد،
        # بعد از بالا آمدن جواب می‌گیرد. PTB آفست را خودش تأیید می‌کند؛ فقط
        # آپدیت‌های «تأییدنشده» دوباره تحویل داده می‌شوند (بدون تکرار پاسخ).
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
    except Exception as exc:
        logger.critical("خطای کشنده در راه‌اندازی ربات: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()