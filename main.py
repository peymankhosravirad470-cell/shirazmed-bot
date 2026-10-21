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
    """راه‌اندازی و اجرای ربات با polling (آپدیت‌های قدیمی دور ریخته می‌شوند)."""
    os.makedirs("data", exist_ok=True)
    try:
        start_health_server()
        application = build_application()
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    except Exception as exc:
        logger.critical("خطای کشنده در راه‌اندازی ربات: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
