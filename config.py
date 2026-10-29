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
VERSION = "49"

# 🆕 ممیزی (بخش J): مسیر واحد داده — روی لیارا دیسک پایدار در /app/data mount
# شده و WORKDIR هم /app است؛ بنابراین همه‌ی مسیرهای ذخیره‌سازی باید از همین
# ریشه عبور کنند. DATA_DIR env اجازه می‌دهد در تست‌ها/استقرارهای دیگر مسیر جدا باشد.
DATA_DIR = os.path.abspath(os.getenv("DATA_DIR", "data"))
DOCTORS_PATH = os.path.join(DATA_DIR, "doctors")
NON_MEDICAL_PATH = os.path.join(DATA_DIR, "non_medical")
INSURANCE_PATH = os.path.join(DATA_DIR, "insurance")

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
    # 🆕 آدرس عمومی اپ (برای callback زرین‌پال). پیش‌فرض: دامنه استاندارد لیارا
    public_base_url: str = field(
        default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "https://shirazmedical.iran.liara.run").rstrip("/")
    )
    # 🆕 تالار گفتگو (درخواست کاربر ۱۴۰۴/۰۸/۰۸): دکمه‌ی «عضویت در کانال» به
    # «💬 تالار گفتگو» تغییر کرد. لینک از env خوانده می‌شود؛ پیش‌فرض همان لینکی
    # است که از قبل در پروژه وجود داشت (ble.ir/shiraz_medical) — هیچ لینک جدیدی
    # جعل نشده است. اگر آدرس تالار واقعی فرق دارد، با FORUM_URL تنظیم کنید.
    forum_url: str = field(
        default_factory=lambda: os.getenv("FORUM_URL", "https://ble.ir/shiraz_medical").strip()
    )
    # 🩺 ثبت‌نام پزشک: رمز ورود به فرم مخفی.
    # 🔒 امنیت (ممیزی ۱۴۰۴): هیچ پیش‌فرض قابل‌استفادی در کد عمومی وجود ندارد —
    # اگر DOCTOR_REG_CODE در env تنظیم نشده باشد، ثبت‌نام پزشک «غیرفعال» است و
    # کاربر پیام مناسب می‌گیرد. رمز واقعی فقط از محیط اجرا (لیارا) می‌آید.
    doctor_reg_code: str = field(
        default_factory=lambda: os.getenv("DOCTOR_REG_CODE", "")
    )
    # 🩺 کامیت خودکار پزشکان تاییدشده روی گیت‌هاب (اختیاری) — در صورت تنظیم،
    # تایید ادمین همزمان روی گیت‌هاب هم کامیت می‌شود و دیپلوی خودکار لیارا داده را دائمی می‌کند.
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", ""))
    github_branch: str = field(default_factory=lambda: os.getenv("GITHUB_BRANCH", "main"))
    # 🌉 پل تلگرام (اختیاری): آدرس سرویس واسط ارسال پیام/فایل به تلگرام
    telegram_bridge_url: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BRIDGE_URL", "")
    )
    telegram_bridge_file_url: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BRIDGE_FILE_URL", "")
    )
    # 🆕 ممیزی (بخش A): انتخاب صریح پلتفرم. مقادیر مجاز: bale / telegram / خالی.
    # خالی = رفتار خودکارِ مستند: بله اولویت دارد، وگرنه تلگرام.
    platform_choice: str = field(
        default_factory=lambda: os.getenv("PLATFORM", "").strip().lower()
    )

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

    @property
    def doctor_reg_enabled(self) -> bool:
        """🔒 ثبت‌نام پزشک فقط وقتی فعال است که رمز امن از env آمده باشد (بدون پیش‌فرض)."""
        return bool((self.doctor_reg_code or "").strip())

    @property
    def effective_platform(self) -> str:
        """🆕 ممیزی (بخش A): پلتفرم اجرایی «شفاف و اعتبارسنجی‌شده».

        - PLATFORM=bale|telegram → همان (و توکن متناظرش الزامی است؛ نبودش خطای
          واضح می‌دهد، نه اجرای مبهم).
        - PLATFORM خالی → رفتار خودکار مستند: بله اگر توکن داشت، وگرنه تلگرام.
        """
        choice = self.platform_choice
        if choice:
            if choice not in ("bale", "telegram"):
                raise ValueError(
                    f"PLATFORM نامعتبر است: '{choice}'. مقادیر مجاز: bale, telegram"
                )
            if choice == "bale" and not self.bale_bot_token:
                raise ValueError(
                    "PLATFORM=bale است ولی BALE_BOT_TOKEN در env تنظیم نشده است."
                )
            if choice == "telegram" and not self.telegram_bot_token:
                raise ValueError(
                    "PLATFORM=telegram است ولی TELEGRAM_BOT_TOKEN در env تنظیم نشده است."
                )
            return choice
        return self.platform

    def log_startup_summary(self) -> None:
        """مقادیر غیرحساس را کامل و مقادیر حساس را ماسک‌شده لاگ می‌کند."""
        logger.info("%s v%s — در حال راه‌اندازی", PROJECT_NAME, VERSION)
        logger.info("پلتفرم فعال: %s%s", self.effective_platform, " (از PLATFORM)" if self.platform_choice else " (خودکار)")
        logger.info("BOT_USERNAME: %s", self.bot_username)
        logger.info("ADMIN_CHAT_ID: %s", self.admin_chat_id if self.admin_chat_id else "(تنظیم نشده)")
        logger.info("ZARINPAL_SANDBOX: %s", self.zarinpal_sandbox)
        logger.info("TIMEZONE_OFFSET_HOURS: %s", self.timezone_offset_hours)
        logger.info("PUBLIC_BASE_URL: %s", self.public_base_url)
        logger.info("BALE_BOT_TOKEN: %s", _mask(self.bale_bot_token))
        logger.info("TELEGRAM_BOT_TOKEN: %s", _mask(self.telegram_bot_token))
        logger.info("AVALAI_API_KEY: %s", _mask(self.avalai_api_key))
        logger.info("ZARINPAL_MERCHANT_ID: %s", _mask(self.zarinpal_merchant_id))
        logger.info("DOCTOR_REG_CODE: %s", _mask(self.doctor_reg_code))
        logger.info("GITHUB_TOKEN: %s | GITHUB_REPO: %s", _mask(self.github_token), self.github_repo or "(تنظیم نشده)")


# ─── نمونه‌ی singleton — در کل پروژه از همین import شود ───
settings = Settings()