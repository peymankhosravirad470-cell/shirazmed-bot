# app/keyboards/tourism.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.locales import get_msg_btn


def get_tourism_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد بخش گردشگری با پشتیبانی از هر سه زبان."""

    labels = {
        "fa": {
            "city": "🏛️ جاذبه‌های شهری",
            "outside": "🏞️ جاذبه‌های خارج از شهر",
            "back": "🔙 بازگشت",
            "feedback": "💬 پیشنهادات",
        },
        "en": {
            "city": "🏛️ City Attractions",
            "outside": "🏞️ Outside the City",
            "back": "🔙 Back",
            "feedback": "💬 Feedback",
        },
        "ar": {
            "city": "🏛️ المعالم الحضرية",
            "outside": "🏞️ خارج المدينة",
            "back": "🔙 رجوع",
            "feedback": "💬 ملاحظات",
        },
    }
    L = labels.get(lang, labels["fa"])

    rows = [
        [InlineKeyboardButton(L["city"], callback_data="tour_city")],
        [InlineKeyboardButton(L["outside"], callback_data="tour_outside")],
        [
            InlineKeyboardButton(L["back"], callback_data="back_main"),
            InlineKeyboardButton(L["feedback"], callback_data="start_feedback"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def get_patient_rights_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد تفکیک حقوق بیمار و شکایات با پشتیبانی از سه زبان."""

    labels = {
        "fa": {
            "charter": "📋 منشور حقوق بیمار (ویژه خارجی‌ها)",
            "complaints": "⚖️ راهنمای ثبت شکایت",
            "back": "🔙 بازگشت",
            "feedback": "💬 پیشنهادات",
        },
        "en": {
            "charter": "📋 Patient Rights Charter (For Foreigners)",
            "complaints": "⚖️ Complaint Filing Guide",
            "back": "🔙 Back",
            "feedback": "💬 Feedback",
        },
        "ar": {
            "charter": "📋 ميثاق حقوق المريض (للأجانب)",
            "complaints": "⚖️ دليل تقديم الشكوى",
            "back": "🔙 رجوع",
            "feedback": "💬 ملاحظات",
        },
    }
    L = labels.get(lang, labels["fa"])

    rows = [
        [InlineKeyboardButton(L["charter"], callback_data="charter")],
        [InlineKeyboardButton(L["complaints"], callback_data="complaints_menu")],
        [
            InlineKeyboardButton(L["back"], callback_data="back_main"),
            InlineKeyboardButton(L["feedback"], callback_data="start_feedback"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def get_complaints_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی شکایات با پشتیبانی از سه زبان."""

    labels = {
        "fa": {
            "iranian": "🇮🇷 شکایات اتباع ایرانی",
            "foreign": "🌍 شکایات اتباع خارجی",
            "back": "🔙 بازگشت",
            "feedback": "💬 پیشنهادات",
        },
        "en": {
            "iranian": "🇮🇷 Iranian Complaints",
            "foreign": "🌍 Foreign Complaints",
            "back": "🔙 Back",
            "feedback": "💬 Feedback",
        },
        "ar": {
            "iranian": "🇮🇷 شكاوى المواطنين الإيرانيين",
            "foreign": "🌍 شكاوى الأجانب",
            "back": "🔙 رجوع",
            "feedback": "💬 ملاحظات",
        },
    }
    L = labels.get(lang, labels["fa"])

    rows = [
        [InlineKeyboardButton(L["iranian"], callback_data="complaints_iranian")],
        [InlineKeyboardButton(L["foreign"], callback_data="complaints_foreign")],
        [
            InlineKeyboardButton(L["back"], callback_data="rights"),
            InlineKeyboardButton(L["feedback"], callback_data="start_feedback"),
        ],
    ]
    return InlineKeyboardMarkup(rows)