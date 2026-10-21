# app/keyboards/tourism.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


def get_tourism_keyboard(lang: str) -> InlineKeyboardMarkup:
    """ساخت کیبورد بخش گردشگری به زبان انتخابی کاربر."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_city"),
                    callback_data="tour_city",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_outside"),
                    callback_data="tour_outside",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_back"),
                    callback_data="back_main",
                )
            ],
        ]
    )