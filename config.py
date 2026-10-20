# -*- coding: utf-8 -*-
"""
پیکربندی مرکزی ربات شیراز مدیکال (v46).
همه‌ی مقادیر حساس فقط از متغیرهای محیطی (env) خوانده می‌شوند — هیچ توکنی هاردکد نشده.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ─── ثابت‌های پروژه ───
PROJECT_NAME = "Shiraz Medical Bot"
VERSION = "46"

DB_PATH = "data/"
DOCTORS_PATH = "data/doctors/"
NON_MEDICAL_PATH = "data/non_medical/"
INSURANCE_PATH = "data/insurance/"

# پیش‌فرض‌های منطقه‌ای
DEFAULT_TIMEZONE_OFFSET_HOURS = 3.5  # ایران (UTC+3:30)


def _mask(value: str, keep: int = 4) -> str:
    """یک رشته‌ی حساس (توکن/کلید) را برای لاگ امن می‌کند: فقط چند کاراکتر اول و آخر نمایش داده می‌شود."""
    if not value:
        return "(تنظیم نشده)"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}{'*' * (len(value) - keep * 2)}{value[-keep:]}"


def _parse_bool(raw: str | None, default: bool) -> bool:
    """تبدیل رشته‌ی env به bool. مقادیر مجاز: true/false/1/0/yes/no (case-insensitive)."""
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in ("true", "1", "yes", "y", "on"):
        return True
    if normalized in ("false", "0", "no", "n", "off"):
        return False
    raise ValueError(
        f"مقدار bool نامعتبر: '{raw}'. مقادیر مجاز: true/false/1/0/yes/no."
    )


def _parse_admin_chat_id(raw: str | None) -> int | None:
    """ADMIN_CHAT_ID باید یک عدد صحیح باشد (شناسه‌ی چت بله/تلگرام) یا خالی باشد."""
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"ADMIN_CHAT_ID باید عدد صحیح باشد، مقدار دریافتی: '{raw}'"
        ) from exc


def _parse_timezone_offset(raw: str | None) -> float:
    """TIMEZONE_OFFSET_HOURS باید عدد اعشاری باشد؛ پیش‌فرض +3.5 (ایران)."""
    if raw is None or raw.strip() == "":
        return DEFAULT_TIMEZONE_OFFSET_HOURS
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"TIMEZONE_OFFSET_HOURS باید عدد باشد، مقدار دریافتی: '{raw}'"
        ) from exc


@dataclass(frozen=True)
class Settings:
    """تمام تنظیمات اجراییِ ربات، خوانده‌شده و اعتبارسنجی‌شده از متغیرهای محیطی."""

    bale_bot_token: str = field(default_factory=lambda: os.getenv("BALE_BOT_TOKEN", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    avalai_api_key: str = field(default_factory=lambda: os.getenv("AVALAI_API_KEY", ""))
    admin_chat_id: int | None = field(
        default_factory=lambda: _parse_admin_chat_id(os.getenv("ADMIN_CHAT_ID"))
    )
    zarinpal_merchant_id: str = field(
        default_factory=lambda: os.getenv("ZARINPAL_MERCHANT_ID", "")
    )
    zarinpal_sandbox: bool = field(
        default_factory=lambda: _parse_bool(os.getenv("ZARINPAL_SANDBOX"), default=True)
    )
    timezone_offset_hours: float = field(
        default_factory=lambda: _parse_timezone_offset(os.getenv("TIMEZONE_OFFSET_HOURS"))
    )
    bot_username: str = field(default_factory=lambda: os.getenv("BOT_USERNAME", "ShirazMedBot"))

    def __post_init__(self) -> None:
        """اعتبارسنجی نهاییِ ترکیب تنظیمات."""
        if not self.bale_bot_token and not self.telegram_bot_token:
            raise ValueError(
                "حداقل یکی از BALE_BOT_TOKEN یا TELEGRAM_BOT_TOKEN باید در env تنظیم شده باشد."
            )

    @property
    def active_token(self) -> str:
        """توکن فعال: در حال حاضر بله در اولویت است، در غیر این صورت تلگرام."""
        return self.bale_bot_token or self.telegram_bot_token

    @property
    def platform(self) -> str:
        """نام پلتفرم فعال بر اساس توکن موجود."""
        return "bale" if self.bale_bot_token else "telegram"

    def log_startup_summary(self) -> None:
        """مقادیر غیرحساس را کامل و مقادیر حساس را ماسک‌شده لاگ می‌کند."""
        logger.info("%s v%s — در حال راه‌اندازی", PROJECT_NAME, VERSION)
        logger.info("پلتفرم فعال: %s", self.platform)
        logger.info("BOT_USERNAME: %s", self.bot_username)
        logger.info("ADMIN_CHAT_ID: %s", self.admin_chat_id if self.admin_chat_id else "(تنظیم نشده)")
        logger.info("ZARINPAL_SANDBOX: %s", self.zarinpal_sandbox)
        logger.info("TIMEZONE_OFFSET_HOURS: %s", self.timezone_offset_hours)
        logger.info("BALE_BOT_TOKEN: %s", _mask(self.bale_bot_token))
        logger.info("TELEGRAM_BOT_TOKEN: %s", _mask(self.telegram_bot_token))
        logger.info("AVALAI_API_KEY: %s", _mask(self.avalai_api_key))
        logger.info("ZARINPAL_MERCHANT_ID: %s", _mask(self.zarinpal_merchant_id))


# ─── نمونه‌ی singleton — در کل پروژه از همین import شود ───
settings = Settings()
