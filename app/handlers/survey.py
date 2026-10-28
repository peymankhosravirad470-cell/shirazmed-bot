# app/handlers/survey.py

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

from config import settings

logger = logging.getLogger(__name__)

# مراحل گفتگو
ASK_SATISFACTION, ASK_REASON = range(2)

# 🆕 فیکس: آیدی ادمین دیگر هاردکد نیست — از متغیر محیطی ADMIN_CHAT_ID خوانده می‌شود
# (قبلاً: ADMIN_CHAT_ID = 1967087863 که امن نبود و قابل تغییر نبود)


def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """🆕 زبان کاربر از user_data (با PicklePersistence بعد از ری‌استارت هم می‌ماند)."""
    lang = context.user_data.get("lang", "fa")
    return lang if lang in ("fa", "en", "ar") else "fa"


# 🆕 متن‌های سه‌زبانه نظرسنجی (قبلاً همه فارسی بود و برای مشتری عرب/انگلیسی
# تداخل زبان ایجاد می‌کرد)
_T: dict[str, dict[str, str]] = {
    "intro": {
        "fa": "از اینکه با ما همراه بودید سپاسگزاریم.\n\nآیا مایل به ادامه استفاده از خدمات هستید؟",
        "en": "Thank you for being with us.\n\nWould you like to continue using our services?",
        "ar": "شكراً لمرافقتك لنا.\n\nهل ترغب في مواصلة استخدام خدماتنا؟",
    },
    "btn_yes": {"fa": "بله، ادامه می‌دهم", "en": "Yes, I'll continue", "ar": "نعم، سأتابع"},
    "btn_no": {"fa": "خیر، کافی است", "en": "No, that's enough", "ar": "لا، هذا كافٍ"},
    "thanks_happy": {
        "fa": "از همراهی شما صمیمانه سپاسگزاریم. روز خوبی داشته باشید! 🌸",
        "en": "Thank you sincerely for being with us. Have a wonderful day! 🌸",
        "ar": "شكراً جزيلاً لمرافقتك. أتمنى لك يوماً سعيداً! 🌸",
    },
    "ask_reason": {
        "fa": "متأسفیم که تجربه خوبی نداشتید. لطفاً در یک پیام کوتاه بنویسید چه چیزی باعث نارضایتی شما شد تا ما بهتر شویم:",
        "en": "We're sorry your experience wasn't good. Please write briefly what caused your dissatisfaction so we can improve:",
        "ar": "نأسف لأن تجربتك لم تكن جيدة. يرجى كتابة سبب عدم رضاك باختصار حتى نتحسّن:",
    },
    "thanks_feedback": {
        "fa": "از اینکه نظر خود را با ما در میان گذاشتید سپاسگزاریم. تیم پشتیبانی ما به زودی بررسی می‌کند.",
        "en": "Thank you for sharing your feedback with us. Our support team will review it soon.",
        "ar": "شكراً لمشاركتنا رأيك. سيقوم فريق الدعم لدينا بمراجعته قريباً.",
    },
    "send_error": {
        "fa": "متأسفانه در ارسال پیام خطایی رخ داد، اما نظر شما ثبت شد. سپاسگزاریم.",
        "en": "Unfortunately an error occurred while sending, but your feedback was recorded. Thank you.",
        "ar": "للأسف حدث خطأ أثناء الإرسال، لكن تم تسجيل ملاحظاتك. شكراً لك.",
    },
    "cancelled": {
        "fa": "نظرسنجی لغو شد.",
        "en": "The survey was cancelled.",
        "ar": "تم إلغاء الاستبيان.",
    },
}


def _t(lang: str, key: str) -> str:
    return _T.get(key, {}).get(lang) or _T.get(key, {}).get("fa", key)


def _get_survey_keyboard(lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد سوال رضایت‌سنجی (سه‌زبانه)."""
    keyboard = [
        [
            InlineKeyboardButton(_t(lang, "btn_yes"), callback_data="survey_yes"),
            InlineKeyboardButton(_t(lang, "btn_no"), callback_data="survey_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع نظرسنجی (این تابع می‌تواند از هر جایی صدا زده شود)."""
    lang = _get_lang(context)
    text = _t(lang, "intro")
    keyboard = _get_survey_keyboard(lang)
    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.message is not None:
        await update.message.reply_text(text, reply_markup=keyboard)

    return ASK_SATISFACTION


async def handle_satisfaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پردازش پاسخ بله یا خیر."""
    query = update.callback_query
    if query is None:
        return ASK_SATISFACTION

    await query.answer()
    data = query.data
    lang = _get_lang(context)

    if data == "survey_yes":
        await query.edit_message_text(_t(lang, "thanks_happy"), reply_markup=None)
        return ConversationHandler.END

    elif data == "survey_no":
        await query.edit_message_text(_t(lang, "ask_reason"), reply_markup=None)
        return ASK_REASON

    return ASK_SATISFACTION


async def receive_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت علت نارضایتی و ارسال به ادمین."""
    if update.message is None or update.message.text is None:
        return ASK_REASON

    reason = update.message.text.strip()
    user = update.effective_user
    user_id = user.id if user else "نامشخص"
    username = f"@{user.username}" if user and user.username else "بدون یوزرنیم"
    full_name = user.full_name if user else "بدون نام"

    admin_message = (
        f"🚨 <b>نارضایتی کاربر</b>\n\n"
        f"👤 نام: {full_name}\n"
        f"🆔 آیدی عددی: <code>{user_id}</code>\n"
        f"🌐 یوزرنیم: {username}\n\n"
        f"📝 علت نارضایتی:\n{reason}"
    )

    # 🆕 فیکس: parse_mode از Markdown به HTML تغییر کرد — «**bold**» در Markdown
    # قدیمی نامعتبر است و پیام ادمین در بله ارسال نمی‌شد.
    lang = _get_lang(context)
    if settings.admin_chat_id is None:
        logger.warning("ADMIN_CHAT_ID تنظیم نشده است؛ پیام نارضایتی برای ادمین ارسال نشد.")
        await update.message.reply_text(_t(lang, "thanks_feedback"), reply_markup=None)
        return ConversationHandler.END

    try:
        await context.bot.send_message(
            chat_id=settings.admin_chat_id,
            text=admin_message,
            parse_mode="HTML",
        )
        await update.message.reply_text(_t(lang, "thanks_feedback"), reply_markup=None)
    except Exception as error:
        logger.error(f"Error sending survey to admin: {error}")
        await update.message.reply_text(_t(lang, "send_error"), reply_markup=None)

    return ConversationHandler.END


async def cancel_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لغو نظرسنجی (در صورت نیاز)."""
    if update.message is not None:
        await update.message.reply_text(_t(_get_lang(context), "cancelled"))
    return ConversationHandler.END


# ساخت ConversationHandler برای نظرسنجی
survey_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_survey, pattern=r"^start_survey$"),
    ],
    states={
        ASK_SATISFACTION: [
            CallbackQueryHandler(handle_satisfaction, pattern=r"^survey_(yes|no)$")
        ],
        ASK_REASON: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reason)
        ],
    },
    # 🆕 فیکس: قبلاً fallback شامل MessageHandler(TEXT) بود که باعث می‌شد هر متنی
    # در مرحله اول (سؤال رضایت) مستقیماً به‌عنوان «علت نارضایتی» ثبت شود.
    fallbacks=[
        CallbackQueryHandler(cancel_survey, pattern=r"^survey_cancel$"),
    ],
    allow_reentry=True,
)