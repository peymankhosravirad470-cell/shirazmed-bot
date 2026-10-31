# -*- coding: utf-8 -*-
"""
🗂️ دسته‌بندی‌های منوی اصلی (مأموریت مکمل — بازطراحی تجربهٔ کاربری)

مشکل قبلی: منوی اصلی ~۲۵ دکمه درهم داشت و بیمار گم می‌شد.
راه‌حل (طبق ۹ اصل دستور محصول):
- دو دکمهٔ کلیدی «جست‌وجو» و «مشاور سلامت» + «اورژانس» و «نوبت بگیر»
  بالای منو و همیشه در دسترس.
- ۱۲ خدمت مشابه در ۶ دستهٔ مشخص با زیرمنوهای منظم (حداکثر ۶ دکمه در هر
  صفحه، ۲ ستون).
- «بازگشت به منوی اصلی» در انتهای همهٔ زیرمنوها (الگوی استاندارد ربات:
  بازگشت + پیشنهادات کنار هم).
- هیچ قابلیت قبلی حذف نشده — فقط دسته‌بندی و مسیر دسترسی مرتب‌تر شده؛
  callbackهای قدیمی (مثل non_medical) هم پابرجا هستند تا منوهای کهنهٔ
  روی صفحهٔ کاربران قدیمی هم کار کنند.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


def _row(lang: str, keys: list[str]) -> list[InlineKeyboardButton]:
    """یک ردیف دکمه از کلیدهای MSG_BTN."""
    return [InlineKeyboardButton(get_msg_btn(lang, k), callback_data=k) for k in keys]


def _back_row(lang: str) -> list[InlineKeyboardButton]:
    """ردیف استاندارد پایانی: بازگشت به منوی اصلی (callback واقعی back_main) + پیشنهادات.

    ⚠️ «btn_back» فقط «برچسب» است؛ callback درستِ بازگشت «back_main» است
    (باگ تست T17 گرفتنش کرد: قبلاً callback_data=btn_back می‌شد که هندلر ندارد).
    """
    return [
        InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main"),
        InlineKeyboardButton(get_msg_btn(lang, "btn_feedback"), callback_data="start_feedback"),
    ]


def get_category_medical_keyboard(lang: str) -> InlineKeyboardMarkup:
    """🏥 درمان و پزشکان: پزشکان/بیمارستان‌ها/پیراپزشکی/بیمه/راهنما."""
    rows = [
        _row(lang, ["medical", "non_hospitals"]),
        _row(lang, ["paramedical", "insurance"]),
        _row(lang, ["patient_guide", "emergency"]),
    ]
    rows.append(_back_row(lang))
    return InlineKeyboardMarkup(rows)


def get_category_travel_keyboard(lang: str) -> InlineKeyboardMarkup:
    """🧳 اقامت و حمل‌ونقل: هتل/مهمان‌پذیر/خانهٔ مسافر/ترانسفر/پایانه/تاکسی."""
    rows = [
        _row(lang, ["non_hotels", "non_motels"]),
        _row(lang, ["non_tourist_houses", "non_transport"]),
        _row(lang, ["hubs", "taxi"]),
    ]
    rows.append(_back_row(lang))
    return InlineKeyboardMarkup(rows)


def get_category_tourism_keyboard(lang: str) -> InlineKeyboardMarkup:
    """🏛️ گردشگری و پکیج: جاذبه‌ها + پکیج‌های درمانی."""
    rows = [
        _row(lang, ["tourism", "package"]),
        _row(lang, ["tour_city", "tour_outside"]),
    ]
    rows.append(_back_row(lang))
    return InlineKeyboardMarkup(rows)


def get_category_support_keyboard(lang: str) -> InlineKeyboardMarkup:
    """🤝 پشتیبانی و خدمات: مترجم/سالمندان/مراکز پشتیبانی/دعوت/حقوق/منشور/شکایت."""
    rows = [
        _row(lang, ["translator", "elderly"]),
        _row(lang, ["support", "invite"]),
        _row(lang, ["rights", "charter"]),
        _row(lang, ["complaints_menu", "non_medical"]),
    ]
    rows.append(_back_row(lang))
    return InlineKeyboardMarkup(rows)


def get_category_me_keyboard(lang: str) -> InlineKeyboardMarkup:
    """📋 پرونده و نوبت‌های من: پرونده/نوبت‌ها/یادآور دارو/همراه بیمار."""
    rows = [
        _row(lang, ["file", "appointments"]),
        _row(lang, ["medication", "start_companion"]),
    ]
    rows.append(_back_row(lang))
    return InlineKeyboardMarkup(rows)


def get_category_contact_keyboard(lang: str) -> InlineKeyboardMarkup:
    """💬 گفتگو و ارتباط: تالار گفتگو/رضایت‌سنجی/پیشنهادات/سایت."""
    rows = [
        _row(lang, ["channel", "start_survey"]),
        _row(lang, ["start_feedback", "site"]),
    ]
    rows.append(_back_row(lang))
    return InlineKeyboardMarkup(rows)


CATEGORY_KEYBOARDS = {
    "cat_medical": get_category_medical_keyboard,
    "cat_travel": get_category_travel_keyboard,
    "cat_tourism": get_category_tourism_keyboard,
    "cat_support": get_category_support_keyboard,
    "cat_me": get_category_me_keyboard,
    "cat_contact": get_category_contact_keyboard,
}
