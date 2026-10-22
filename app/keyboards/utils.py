# app/keyboards/utils.py

from __future__ import annotations

from typing import Mapping, Optional

from telegram import InlineKeyboardButton

from app.locales import get_msg_btn


# ---------------------------------------------------------------------------
# ثابت‌های ماژول
# ---------------------------------------------------------------------------

SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en", "ar")
DEFAULT_LANG: str = "fa"
UNKNOWN_LABEL: str = "?"


# ---------------------------------------------------------------------------
# توابع کمکی
# ---------------------------------------------------------------------------

def normalize_lang(lang: str) -> str:
    """اگر زبان پشتیبانی نشود، به فارسی برمی‌گردد."""
    if isinstance(lang, str) and lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def safe_label(lang: str, key: str, fallback: str = "") -> str:
    """دریافت امن متن دکمه از فایل ترجمه با استفاده از fallback.

    این تابع تضمین می‌کند همیشه یک رشته غیرخالی برگرداند تا ساخت
    InlineKeyboardButton هرگز با مقدار نامعتبر (None، رشته خالی یا
    فقط فاصله) کرش نکند یا توسط API رد نشود.

    ترتیب fallback:
    1) مقدار برگشتی get_msg_btn (اگر str غیرخالی بود)
    2) پارامتر fallback (اگر str غیرخالی بود)
    3) خود key (اگر str غیرخالی بود)
    4) UNKNOWN_LABEL
    """
    value: Optional[str] = None

    try:
        raw = get_msg_btn(lang, key)
        if raw is not None:
            value = str(raw)
    except Exception as error:
        print(f"Error getting label '{key}' for lang '{lang}': {error}")

    if value is not None:
        text = value.strip()
        if text:
            return text

    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()

    if isinstance(key, str) and key.strip():
        return key.strip()

    return UNKNOWN_LABEL


def build_button(
    lang: str,
    key: str,
    callback_data: str,
    default_labels: Optional[Mapping[str, str]] = None,
) -> InlineKeyboardButton:
    """ساخت یک دکمه Inline با برچسب امن.

    Args:
        lang: زبان کاربر (fa/en/ar). اگر نامعتبر باشد، از fallback استفاده می‌شود.
        key: کلید دکمه در دیکشنری ترجمه.
        callback_data: داده callback که با کلیک روی دکمه ارسال می‌شود.
        default_labels: نگاشت اختیاری برچسب‌های پیش‌فرض (کلید -> متن)
            که در صورت نبود ترجمه استفاده می‌شود.

    Returns:
        InlineKeyboardButton با برچسب تضمین‌شده غیرخالی.
    """
    labels = default_labels or {}
    fallback = labels.get(key, key)
    return InlineKeyboardButton(
        safe_label(lang, key, fallback),
        callback_data=callback_data,
    )


# ---------------------------------------------------------------------------
# API عمومی ماژول
# ---------------------------------------------------------------------------

__all__ = ["safe_label", "build_button", "normalize_lang"]