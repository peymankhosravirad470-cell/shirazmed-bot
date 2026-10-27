# app/keyboards/paramedical.py

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en", "ar")
DEFAULT_LANG: str = "fa"

PARAMEDICAL_ITEMS: tuple[tuple[str, str], ...] = (
    ("btn_physio", "para_physio"),
    ("btn_lab", "para_lab"),
    ("btn_radiology", "para_radiology"),
    ("btn_nursing", "para_nursing"),
    ("btn_injection", "para_injection"),
    ("btn_trad_med", "para_trad_med"),
    ("btn_occupational", "para_occupational"),
    ("btn_speech", "para_speech"),
    ("btn_orthotics", "para_orthotics"),
)

BACK_ITEM: tuple[str, str] = ("btn_back", "back_main")

DEFAULT_LABELS: dict[str, str] = {
    "btn_physio": "فیزیوتراپی",
    "btn_lab": "آزمایشگاه",
    "btn_radiology": "رادیولوژی",
    "btn_nursing": "پرستاری",
    "btn_injection": "تزریقات",
    "btn_trad_med": "طب سنتی",
    "btn_occupational": "کاردرمانی",
    "btn_speech": "گفتاردرمانی",
    "btn_orthotics": "ارتز و پروتز",
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


def get_paramedical_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی پیراپزشکی با پشتیبانی از سه زبان و دکمه پیشنهادات."""
    safe_lang = _normalize_lang(lang)

    rows: list[list[InlineKeyboardButton]] = [
        [_build_button(safe_lang, key, callback_data)]
        for key, callback_data in PARAMEDICAL_ITEMS
    ]

    back_key, back_callback = BACK_ITEM
    rows.append([
        _build_button(safe_lang, back_key, back_callback),
        _build_button(safe_lang, "btn_feedback", "start_feedback"),
    ])

    return InlineKeyboardMarkup(rows)


__all__ = ["get_paramedical_keyboard"]