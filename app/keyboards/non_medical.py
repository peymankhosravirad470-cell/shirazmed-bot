# app/keyboards/non_medical.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.locales import get_msg_btn


def get_non_medical_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی خدمات غیرپزشکی با پشتیبانی از هر سه زبان."""

    # برچسب‌های سه‌زبانه
    labels = {
        "fa": {
            "hospitals": "🏥 بیمارستان‌ها",
            "hotels": "🏨 هتل‌ها",
            "motels": "🛏️ مهمان‌پذیر",
            "houses": "🏠 خانه مسافر",
            "back": "🔙 بازگشت",
            "feedback": "💬 پیشنهادات",
        },
        "en": {
            "hospitals": "🏥 Hospitals",
            "hotels": "🏨 Hotels",
            "motels": "🛏️ Motels",
            "houses": "🏠 Guest Houses",
            "back": "🔙 Back",
            "feedback": "💬 Feedback",
        },
        "ar": {
            "hospitals": "🏥 المستشفيات",
            "hotels": "🏨 الفنادق",
            "motels": "🛏️ بيت ضيافة",
            "houses": "🏠 بيت المسافر",
            "back": "🔙 رجوع",
            "feedback": "💬 ملاحظات",
        },
    }
    L = labels.get(lang, labels["fa"])

    rows = [
        [InlineKeyboardButton(L["hospitals"], callback_data="non_hospitals")],
        [InlineKeyboardButton(L["hotels"], callback_data="non_hotels")],
        [InlineKeyboardButton(L["motels"], callback_data="non_motels")],
        [InlineKeyboardButton(L["houses"], callback_data="non_tourist_houses")],
        [
            InlineKeyboardButton(L["back"], callback_data="back_main"),
            InlineKeyboardButton(L["feedback"], callback_data="start_feedback"),
        ],
    ]
    return InlineKeyboardMarkup(rows)