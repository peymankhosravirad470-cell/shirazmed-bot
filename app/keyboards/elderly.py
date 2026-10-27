# app/keyboards/elderly.py

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en", "ar")
DEFAULT_LANG: str = "fa"

ELDERLY_ITEMS: tuple[tuple[str, str], ...] = (
    ("btn_elder_all", "elderly_all"),
)

BACK_ITEM: tuple[str, str] = ("btn_back", "back_main")

DEFAULT_LABELS: dict[str, str] = {
    "btn_elder_all": "لیست خانه‌های سالمندان",
    "btn_back": "بازگشت",
    "btn_feedback": "پیشنهادات",
}


def _normalize_lang(lang: str) -> str:
    if isinstance(lang, str) and lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def _safe_label(lang: str, key: str) -> str:
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
    return InlineKeyboardButton(
        _safe_label(lang, key),
        callback_data=callback_data,
    )


def get_elderly_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی خانه سالمندان با پشتیبانی از سه زبان و دکمه پیشنهادات."""
    safe_lang = _normalize_lang(lang)

    rows: list[list[InlineKeyboardButton]] = [
        [_build_button(safe_lang, key, callback_data)]
        for key, callback_data in ELDERLY_ITEMS
    ]

    back_key, back_callback = BACK_ITEM
    rows.append([
        _build_button(safe_lang, back_key, back_callback),
        _build_button(safe_lang, "btn_feedback", "start_feedback"),
    ])

    return InlineKeyboardMarkup(rows)


__all__ = ["get_elderly_keyboard"]