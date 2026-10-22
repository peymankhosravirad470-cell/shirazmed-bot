# app/keyboards/non_medical.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.locales import get_msg_btn

def get_non_medical_keyboard(lang: str) -> InlineKeyboardMarkup:
    keys = ["non_hospitals", "non_hotels", "non_motels", "non_tourist_houses"]
    rows = [[InlineKeyboardButton(get_msg_btn(lang, key), callback_data=key)] for key in keys]
    rows.append([InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")])
    return InlineKeyboardMarkup(rows)