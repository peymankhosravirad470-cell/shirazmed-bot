# app/keyboards/tourism.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.locales import get_msg_btn

def get_tourism_keyboard(lang: str) -> InlineKeyboardMarkup:
    keys = ["tour_city", "tour_outside"]
    rows = [
        [InlineKeyboardButton(get_msg_btn(lang, key), callback_data=key)]
        for key in keys
    ]
    rows.append(
        [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
    )
    return InlineKeyboardMarkup(rows)