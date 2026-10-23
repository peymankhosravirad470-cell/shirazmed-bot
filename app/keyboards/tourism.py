# app/keyboards/tourism.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.locales import get_msg_btn

def get_tourism_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد بخش گردشگری"""
    keys = ["tour_city", "tour_outside"]
    rows = [
        [InlineKeyboardButton(get_msg_btn(lang, key), callback_data=key)]
        for key in keys
    ]
    rows.append(
        [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
    )
    return InlineKeyboardMarkup(rows)

def get_patient_rights_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد جدید برای تفکیک حقوق بیمار و شکایات"""
    rows = [
        [InlineKeyboardButton("📋 منشور حقوق بیمار (ویژه خارجی‌ها)", callback_data="charter")],
        [InlineKeyboardButton("⚖️ راهنمای ثبت شکایت", callback_data="complaints_menu")],
        [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(rows)

def get_complaints_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی شکایات (ایرانی و خارجی)"""
    rows = [
        [InlineKeyboardButton("🇮🇷 شکایات اتباع ایرانی", callback_data="complaints_iranian")],
        [InlineKeyboardButton("🌍 شکایات اتباع خارجی", callback_data="complaints_foreign")],
        [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="rights")]
    ]
    return InlineKeyboardMarkup(rows)