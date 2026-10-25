# app/keyboards/non_medical.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_non_medical_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد زیرمنوی خدمات غیرپزشکی.

    🎯 فیکس دکمه‌های انگلیسی: قبلاً get_msg_btn با کلیدهای ناموجود
    (non_hospitals و…) صدا زده می‌شد؛ چون این کلیدها در فایل ترجمه
    (fa/en/ar) تعریف نشده بودند، get_msg_btn خودِ کلید انگلیسی را
    برمی‌گرداند و دکمه‌ها به‌صورت «non_hospitals» نمایش داده می‌شدند.
    حالا برچسب فارسی به‌صورت مستقیم نوشته می‌شود.
    """
    rows = [
        [InlineKeyboardButton("🏥 بیمارستان‌ها", callback_data="non_hospitals")],
        [InlineKeyboardButton("🏨 هتل‌ها", callback_data="non_hotels")],
        [InlineKeyboardButton("🛏️ مهمان‌پذیر", callback_data="non_motels")],
        [InlineKeyboardButton("🏠 خانه مسافر", callback_data="non_tourist_houses")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(rows) 