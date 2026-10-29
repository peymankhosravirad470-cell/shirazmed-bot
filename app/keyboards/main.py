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
    keys = [
        "medical", "non_medical", "tourism", "paramedical", "elderly", "package",
        "hubs", "taxi", "insurance", "translator", "charter", "deepseek",
        "file", "appointments", "medication", "emergency", "channel", "invite", "rights",
        # 🆕 اتصال داده‌های موجود (درخواست کاربر ۱۴۰۴/۰۸/۰۸): راهنمای بیمار
        # (patient_guide.json با ۲۹ راهنما) و مراکز پشتیبانی (support.json با ۸
        # مرکز) از قبل هندلر داشتند ولی «هیچ دکمه‌ای» به آن‌ها وصل نبود.
        "patient_guide", "support",
    ]
    
    # چیدمان: ۲ دکمه در هر ردیف با استفاده از get_msg_btn (که زبان را در نظر می‌گیرد)
    rows = [
        [InlineKeyboardButton(get_msg_btn(lang, key), callback_data=key) for key in keys[i : i + 2]]
        for i in range(0, len(keys), 2)
    ]
    
    # ✅ استفاده از get_msg_btn برای دکمه‌های اصلی (با پشتیبانی از زبان‌های مختلف)
    book_text = get_msg_btn(lang, "btn_book") or "📅 نوبت بگیر"
    companion_text = get_msg_btn(lang, "btn_companion") or "🤝 ثبت همراه بیمار"
    survey_text = get_msg_btn(lang, "btn_survey") or "📝 ثبت نظر و رضایت‌سنجی"

    rows.append([InlineKeyboardButton(book_text, callback_data="start_booking")])
    rows.append([InlineKeyboardButton(companion_text, callback_data="start_companion")])
    rows.append([InlineKeyboardButton(survey_text, callback_data="start_survey")])
    
    # دکمه تغییر زبان
    rows.append([InlineKeyboardButton(get_msg_btn(lang, "btn_change_lang"), callback_data="change_language")])

    # 🌐 دکمه «آدرس سایت» — انتهای منو (تنها دکمه جدید؛ سایر دکمه‌ها دست‌نخورده‌اند)
    rows.append([InlineKeyboardButton(get_msg_btn(lang, "btn_site"), callback_data="site")])
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