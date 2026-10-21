# app/keyboards/non_medical.py

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales import get_msg_btn


def get_non_medical_keyboard(lang: str) -> InlineKeyboardMarkup:
    """ساخت کیبورد بخش خدمات غیرپزشکی به زبان انتخابی کاربر."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_hospitals"),
                    callback_data="non_hospitals",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_hotels"),
                    callback_data="non_hotels",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_motels"),
                    callback_data="non_motels",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_houses"),
                    callback_data="non_tourist_houses",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_msg_btn(lang, "btn_transport"),
                    callback_data="non_transport",
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