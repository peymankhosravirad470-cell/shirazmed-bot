# -*- coding: utf-8 -*-
"""نقطه‌ی ورود ربات شیراز مدیکال (v48)."""

import logging
import os
import sys

from telegram import Update

from app.bot import build_application
from app.health import start_health_server
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """راه‌اندازی و اجرای ربات با polling (آپدیت‌های تأییدنشده‌ی حین ری‌استارت هم پاسخ می‌گیرند)."""
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    try:
        # 🆕 ممیزی (بخش J): بوت‌استرپ داده‌ی استاتیک روی دیسک پایدار — فایل‌های
        # غایب از data_seed کپی می‌شوند (هیچ‌وقت بازنویسی نمی‌کند).
        from app.data_seed import seed_static_data
        seed_static_data()
        start_health_server()
        # 🆕 ممیزی (بخش A): پلتفرم اجرا «شفاف» انتخاب می‌شود — PLATFORM env اگر
        # تنظیم باشد (bale/telegram با اعتبارسنجی)، وگرنه رفتار خودکار مستند
        # (بله اولویت دارد). توکن ناموجود = خطای واضح، نه اجرای مبهم.
        application = build_application(settings.effective_platform)
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