# app/keyboards/main.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("فارسی", callback_data="lang_fa"),
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("العربية", callback_data="lang_ar"),
        ]]
    )


def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    keys = [
        "medical", "non_medical", "tourism", "paramedical", "elderly", "package",
        "hubs", "taxi", "insurance", "translator", "charter", "deepseek",
        "file", "appointments", "medication", "emergency", "channel", "invite", "rights",
    ]
    rows = [
        [InlineKeyboardButton(get_msg_btn(lang, key), callback_data=key) for key in keys[i : i + 3]]
        for i in range(0, len(keys), 3)
    ]
    
    # دکمه رزرو نوبت
    rows.append([
        InlineKeyboardButton("📅 رزرو نوبت", callback_data="start_booking"),
    ])
    
    # دکمه ثبت همراه بیمار
    rows.append([
        InlineKeyboardButton("🤝 ثبت همراه بیمار", callback_data="start_companion"),
    ])
    
    # دکمه ثبت نظر و رضایت‌سنجی
    rows.append([
        InlineKeyboardButton("📝 ثبت نظر و رضایت‌سنجی", callback_data="start_survey"),
    ])
    
    # دکمه تغییر زبان
    rows.append([InlineKeyboardButton(get_msg_btn(lang, "btn_change_lang"), callback_data="change_language")])
    return InlineKeyboardMarkup(rows)


def get_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]]
    )