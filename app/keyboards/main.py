# -*- coding: utf-8 -*-
"""
کیبورد منوی اصلی ربات شیراز مدیکال (v46).
فقط تعریف کیبورد — بدون هیچ هندلر یا منطق دیتابیس.
متن دکمه‌ها از app.locales.fa.MSG_BTN خوانده می‌شود، نه هاردکد.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.locales.fa import MSG_BTN

_MAIN_MENU_ITEMS: list[tuple[str, str]] = [
    ("medical", "main:medical"),
    ("non_medical", "main:non_medical"),
    ("tourism", "main:tourism"),
    ("paramedical", "main:paramedical"),
    ("elderly", "main:elderly"),
    ("package", "main:package"),
    ("hubs", "main:hubs"),
    ("taxi", "main:taxi"),
    ("insurance", "main:insurance"),
    ("translator", "main:translator"),
    ("charter", "main:charter"),
    ("deepseek", "main:deepseek"),
    ("file", "main:file"),
    ("appointments", "main:appointments"),
    ("medication", "main:medication"),
    ("emergency", "main:emergency"),
    ("channel", "main:channel"),
    ("invite", "main:invite"),
    ("rights", "main:rights"),
]

_MAX_COLUMNS = 3
_BACK_BUTTON_KEY = "btn_back"
_BACK_CALLBACK_DATA = "main:home"


def get_main_menu() -> InlineKeyboardMarkup:
    """کیبورد اینلاین منوی اصلی را می‌سازد؛ حداکثر ۳ ستون در هر ردیف."""
    buttons = [
        InlineKeyboardButton(text=MSG_BTN[key], callback_data=callback_data)
        for key, callback_data in _MAIN_MENU_ITEMS
    ]
    rows = [
        buttons[i : i + _MAX_COLUMNS]
        for i in range(0, len(buttons), _MAX_COLUMNS)
    ]
    return InlineKeyboardMarkup(rows)


def get_back_button() -> InlineKeyboardMarkup:
    """کیبورد تک‌دکمه‌ای «بازگشت به منوی اصلی»."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=MSG_BTN[_BACK_BUTTON_KEY], callback_data=_BACK_CALLBACK_DATA)]]
    )