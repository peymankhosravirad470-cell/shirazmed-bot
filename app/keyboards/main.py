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
    """منوی اصلی بازطراحی‌شده (مأموریت مکمل — تجربهٔ کاربری ساده و مرتب).

    مشکل قبلی: ~۲۵ دکمهٔ درهم → بیمار سردرگم می‌شد.
    چیدمان جدید (بالا → پایین، اهمیت نزولی؛ حداکثر ۲ دکمه در ردیف):
      ۱. 🔍 جست‌وجو + 🩺 مشاور سلامت (دو ابزار کلیدی، همیشه در دسترس)
      ۲. 🚨 اورژانس (تمام‌عرض — حیاتی)
      ۳. 📅 نوبت بگیر (تمام‌عرض — پرکاربردترین خدمت)
      ۴-۶. شش دستهٔ خدماتی (تفکیک مشابه‌ها در زیرمنو — app/keyboards/categories.py)
      ۷. 🤖 دستیار هوشمند + 🌐 تغییر زبان
      ۸. 🌐 آدرس سایت
    هیچ قابلیتی حذف نشده؛ فقط دسته‌بندی و مسیر دسترسی مرتب‌تر شده است.
    """
    keys = [
        "search", "advisor",
        "emergency",
        "start_booking",
        "cat_medical", "cat_travel",
        "cat_tourism", "cat_support",
        "cat_me", "cat_contact",
        "ai_assistant", "btn_change_lang",
        "btn_site",
    ]
    wide = {"emergency", "start_booking", "btn_site"}  # دکمه‌های تمام‌عرض
    rows: list[list[InlineKeyboardButton]] = []
    pending: list[InlineKeyboardButton] = []
    for key in keys:
        btn = InlineKeyboardButton(get_msg_btn(lang, key), callback_data=key)
        if key in wide:
            if pending:
                rows.append(pending)
                pending = []
            rows.append([btn])
        else:
            pending.append(btn)
            if len(pending) == 2:
                rows.append(pending)
                pending = []
    if pending:
        rows.append(pending)
    return InlineKeyboardMarkup(rows)


def get_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    """دکمه بازگشت به منو + دکمه پیشنهادات کنار هم (الگوی استاندارد کل ربات).

    ✅ این کیبورد در همه بخش‌هایی که کاربر به منوی اصلی برمی‌گردد استفاده
    می‌شود؛ طبق الگوی منوی غیرپزشکی، کنار هر دکمه بازگشت، دکمه «💬 پیشنهادات»
    هم قرار می‌گیرد. برچسب‌ها از locale سه‌زبانه خوانده می‌شوند (btn_back و
    btn_feedback در هر سه زبان تعریف شده‌اند).
    """
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main"),
            InlineKeyboardButton(get_msg_btn(lang, "btn_feedback"), callback_data="start_feedback"),
        ]]
    )