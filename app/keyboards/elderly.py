# app/keyboards/elderly.py

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


# ---------------------------------------------------------------------------
# ثابت‌های ماژول
# ---------------------------------------------------------------------------

SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en", "ar")
DEFAULT_LANG: str = "fa"

# آیتم‌های زیرمنوی خانه سالمندان: (کلید زبان، callback_data)
ELDERLY_ITEMS: tuple[tuple[str, str], ...] = (
    ("btn_elder_all", "elderly_all"),
)

BACK_ITEM: tuple[str, str] = ("btn_back", "back_main")

# برچسب‌های پیش‌فرض فارسی برای هر دکمه (در صورت نبود کلید در دیکشنری زبان)
DEFAULT_LABELS: dict[str, str] = {
    "btn_elder_all": "لیست خانه‌های سالمندان",
    "btn_back": "بازگشت",
}


# ---------------------------------------------------------------------------
# توابع کمکی داخلی
# ---------------------------------------------------------------------------

def _normalize_lang(lang: str) -> str:
    """اگر زبان پشتیبانی نشود، به فارسی برمی‌گردد."""
    if isinstance(lang, str) and lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def _safe_label(lang: str, key: str) -> str:
    """دریافت امن برچسب دکمه از get_msg_btn با fallback فارسی.

    هرگز رشته خالی یا None برنمی‌گرداند تا InlineKeyboardButton کرش نکند.
    """
    fallback = DEFAULT_LABELS.get(key, key)
    try:
        value = get_msg_btn(lang, key)
    except Exception as error:
        print(f"Error getting msg btn '{key}' for lang '{lang}': {error}")
        return fallback

    if value is None:
        return fallback
    if not isinstance(value, str):
        return fallback

    text = value.strip()
    return text if text else fallback


def _build_button(lang: str, key: str, callback_data: str) -> InlineKeyboardButton:
    """ساخت یک InlineKeyboardButton با برچسب امن."""
    return InlineKeyboardButton(
        _safe_label(lang, key),
        callback_data=callback_data,
    )


# ---------------------------------------------------------------------------
# API عمومی
# ---------------------------------------------------------------------------

def get_elderly_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی خانه سالمندان.

    شامل دکمه‌های لیست خانه‌های سالمندان و بازگشت به منوی اصلی.
    دکمه‌ها به صورت تک‌ستونه چیده می‌شوند تا برچسب‌های فارسی طولانی
    در موبایل به‌درستی نمایش داده شوند. دکمه بازگشت همیشه در آخرین
    ردیف و به صورت تنها قرار می‌گیرد.
    """
    safe_lang = _normalize_lang(lang)

    rows: list[list[InlineKeyboardButton]] = [
        [_build_button(safe_lang, key, callback_data)]
        for key, callback_data in ELDERLY_ITEMS
    ]

    back_key, back_callback = BACK_ITEM
    rows.append([_build_button(safe_lang, back_key, back_callback)])

    return InlineKeyboardMarkup(rows)


__all__ = ["get_elderly_keyboard"]