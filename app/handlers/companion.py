# app/handlers/companion.py

from __future__ import annotations

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

# مراحل گفتگو
ASK_IS_COMPANION, ASK_NAME, ASK_PHONE = range(3)


def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """🆕 زبان کاربر از user_data."""
    lang = context.user_data.get("lang", "fa")
    return lang if lang in ("fa", "en", "ar") else "fa"


# 🆕 متن‌های سه‌زبانه ثبت همراه بیمار (قبلاً همه فارسی بود)
_T: dict[str, dict[str, str]] = {
    "btn_back_menu": {"fa": "🔙 بازگشت به منو", "en": "🔙 Back to Menu", "ar": "🔙 العودة إلى القائمة"},
    "btn_yes": {"fa": "بله، مایل هستم", "en": "Yes, I would like that", "ar": "نعم، أرغب في ذلك"},
    "btn_no": {"fa": "خیر، نیازی نیست", "en": "No, not needed", "ar": "لا، ليس ضرورياً"},
    "btn_cancel": {"fa": "لغو", "en": "Cancel", "ar": "إلغاء"},
    "intro": {
        "fa": "🤝 همراه بیمار\n\nآیا مایل هستید شخص دیگری (مثلاً یکی از اعضای خانواده یا دوستان) در جریان روند درمان شما قرار بگیرد و ما اطلاعات را با او به اشتراک بگذاریم؟",
        "en": "🤝 Patient Companion\n\nWould you like another person (e.g., a family member or friend) to be informed about your treatment process, so we can share the information with them?",
        "ar": "🤝 مرافق المريض\n\nهل ترغب في أن يكون شخص آخر (مثل أحد أفراد العائلة أو الأصدقاء) على اطّلاع بمراحل علاجك، لنشاركه المعلومات؟",
    },
    "no_needed": {
        "fa": "بسیار خب. در صورت نیاز در آینده می‌توانید از این بخش استفاده کنید.",
        "en": "Very well. You can use this section later if needed.",
        "ar": "حسناً. يمكنك استخدام هذا القسم لاحقاً عند الحاجة.",
    },
    "cancelled": {
        "fa": "فرآیند ثبت همراه بیمار لغو شد.",
        "en": "The patient companion registration was cancelled.",
        "ar": "تم إلغاء عملية تسجيل مرافق المريض.",
    },
    "ask_name": {
        "fa": "لطفاً نام و نام خانوادگی همراه خود را وارد کنید:\n\n🚪 برای لغو، دستور /cancel را بفرستید.",
        "en": "Please enter your companion's full name:\n\n🚪 To cancel, send /cancel.",
        "ar": "يرجى إدخال الاسم الكامل لمرافقك:\n\n🚪 للإلغاء، أرسل الأمر /cancel.",
    },
    "name_too_short": {
        "fa": "نام وارد شده بسیار کوتاه است. لطفاً نام کامل را وارد کنید:",
        "en": "The name is too short. Please enter the full name:",
        "ar": "الاسم قصير جداً. يرجى إدخال الاسم الكامل:",
    },
    "ask_phone": {
        "fa": "لطفاً شماره تماس همراه خود را وارد کنید (مثال: 09123456789):\n\n🚪 برای لغو، دستور /cancel را بفرستید:",
        "en": "Please enter your companion's phone number (e.g., 09123456789):\n\n🚪 To cancel, send /cancel:",
        "ar": "يرجى إدخال رقم هاتف مرافقك (مثال: 09123456789):\n\n🚪 للإلغاء، أرسل الأمر /cancel:",
    },
    "invalid_phone": {
        "fa": "شماره وارد شده معتبر نیست. لطفاً دوباره وارد کنید:",
        "en": "The phone number is not valid. Please enter it again:",
        "ar": "رقم الهاتف المُدخل غير صالح. يرجى إدخاله مرة أخرى:",
    },
    "success": {
        "fa": "✅ اطلاعات همراه شما با موفقیت ثبت شد.\nدر صورت نیاز، پیام اطلاع‌رسانی برای شماره {phone} ارسال خواهد شد.",
        "en": "✅ Your companion's information was registered successfully.\nIf needed, a notification message will be sent to {phone}.",
        "ar": "✅ تم تسجيل معلومات مرافقك بنجاح.\nعند الحاجة، سيتم إرسال رسالة إشعار إلى {phone}.",
    },
}


def _t(lang: str, key: str, **kw: object) -> str:
    text = _T.get(key, {}).get(lang) or _T.get(key, {}).get("fa", key)
    if kw:
        try:
            text = text.format(**kw)
        except Exception:
            pass
    return text


def _back_to_menu_keyboard(lang: str = "fa"):
    """✅ دکمه بازگشت به منو (سه‌زبانه)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(lang, "btn_back_menu"), callback_data="back_main")]
    ])


async def start_companion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند ثبت همراه بیمار."""
    query = update.callback_query
    if query is None:
        return ConversationHandler.END
    await query.answer()
    lang = _get_lang(context)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(lang, "btn_yes"), callback_data="comp_yes")],
        [InlineKeyboardButton(_t(lang, "btn_no"), callback_data="comp_no")],
        [InlineKeyboardButton(_t(lang, "btn_cancel"), callback_data="comp_cancel")],
    ])

    await query.edit_message_text(_t(lang, "intro"), reply_markup=keyboard)
    return ASK_IS_COMPANION


async def receive_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت پاسخ بله یا خیر از کاربر."""
    query = update.callback_query
    if query is None: return ASK_IS_COMPANION
    await query.answer()
    lang = _get_lang(context)

    if query.data == "comp_no":
        await query.edit_message_text(
            _t(lang, "no_needed"),
            reply_markup=_back_to_menu_keyboard(lang),
        )
        context.user_data.pop("companion_name", None)
        return ConversationHandler.END

    if query.data == "comp_cancel":
        context.user_data.pop("companion_name", None)
        await query.edit_message_text(
            _t(lang, "cancelled"),
            reply_markup=_back_to_menu_keyboard(lang),
        )
        return ConversationHandler.END

    # اگر بله را زد، نام همراه را می‌پرسیم
    await query.edit_message_text(_t(lang, "ask_name"), reply_markup=None)
    return ASK_NAME


async def receive_companion_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت نام همراه."""
    if update.message is None or update.message.text is None:
        return ASK_NAME
    
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text(_t(_get_lang(context), "name_too_short"))
        return ASK_NAME

    context.user_data["companion_name"] = name

    await update.message.reply_text(_t(_get_lang(context), "ask_phone"))
    return ASK_PHONE


async def receive_companion_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت شماره تماس همراه و ارسال پیام (شبیه‌سازی SMS)."""
    if update.message is None or update.message.text is None:
        return ASK_PHONE
    
    phone = update.message.text.strip()
    if not phone.replace("+", "").replace("-", "").isdigit() or len(phone) < 10:
        await update.message.reply_text(_t(_get_lang(context), "invalid_phone"))
        return ASK_PHONE
        
    comp_name = context.user_data.get("companion_name", "همراه")
    patient_name = update.effective_user.full_name if update.effective_user else "بیمار"
    
    # متن پیامک طبق درخواست شما
    sms_text = (
        f"ما از شیراز مدیکال مرتبط با بیماری {patient_name}، "
        f"ملزم به اطلاع‌رسانی به شما ({comp_name}) هستیم. "
        "لطفاً در اولین فرصت با بیمار مدنظر تماس بگیرید. به امید سلامتی."
    )
    
    # شبیه‌سازی ارسال پیامک (فعلاً در کنسول چاپ می‌شود)
    logger.info(f"--- شبیه‌سازی ارسال پیامک به {phone} ---")
    logger.info(f"متن پیامک: {sms_text}")
    logger.info("----------------------------------------")
    
    # ✅ نمایش پیام موفقیت به کاربر + دکمه بازگشت به منو
    lang = _get_lang(context)
    await update.message.reply_text(
        _t(lang, "success", phone=phone),
        reply_markup=_back_to_menu_keyboard(lang),
    )
    
    # پاکسازی داده‌های موقت
    context.user_data.pop("companion_name", None)
    return ConversationHandler.END


async def cancel_companion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لغو فرآیند (دستور /cancel یا هر دستور دیگر)."""
    context.user_data.pop("companion_name", None)
    lang = _get_lang(context)
    if update.message is not None:
        await update.message.reply_text(
            _t(lang, "cancelled"),
            reply_markup=_back_to_menu_keyboard(lang),
        )
    if update.callback_query is not None:
        try:
            await update.callback_query.edit_message_text(
                _t(lang, "cancelled"),
                reply_markup=_back_to_menu_keyboard(lang),
            )
        except Exception:
            pass
    return ConversationHandler.END


# ساخت ConversationHandler
companion_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_companion, pattern=r"^start_companion$")],
    states={
        ASK_IS_COMPANION: [CallbackQueryHandler(receive_choice, pattern=r"^comp_(yes|no|cancel)$")],
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_companion_name)],
        ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_companion_phone)],
    },
    fallbacks=[
        MessageHandler(filters.COMMAND, cancel_companion),
        CallbackQueryHandler(cancel_companion, pattern=r"^comp_cancel$"),
    ],
    allow_reentry=True,
)