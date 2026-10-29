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
        "fa": "از اینکه همراه ما بودی، صمیمانه ممنونیم 🌸\nهر وقت نیاز داشتی، همین‌جاییم. سلامت و شاد باشی! 💙",
        "en": "Thank you sincerely for being with us 🌸\nWe're right here whenever you need us. Stay healthy and happy! 💙",
        "ar": "شكراً جزيلاً لمرافقتك 🌸\nنحن هنا متى ما احتجتنا. دم بصحة وسعادة! 💙",
    },
    "ask_reason": {
        "fa": "از اینکه تجربه‌ات خوب نبود، واقعاً متأسفیم. 🙏\n\nلطفاً کوتاه بنویس چه چیزی ناراضیت کرد — باور کن هر حرفت مستقیم می‌رسه به تیم ما و باعث می‌شه بهتر بشیم 💙",
        "en": "We're truly sorry your experience wasn't good. 🙏\n\nPlease write briefly what went wrong — every word reaches our team directly and helps us do better 💙",
        "ar": "نأسف حقاً لأن تجربتك لم تكن جيدة. 🙏\n\nيرجى كتابة سبب عدم رضاك باختصار — كل كلمة تصل مباشرة إلى فريقنا وتساعدنا على التحسن 💙",
    },
    "thanks_feedback": {
        "fa": "🙏 ممنون که بهمون گفتی.\n\nتیم ما به‌زودی بررسی‌اش می‌کنه و پیگیری می‌شه — قول می‌دیم 💙",
        "en": "🙏 Thank you for telling us.\n\nOur team will review it soon and follow up — we promise 💙",
        "ar": "🙏 شكراً لإخبارنا.\n\nسيراجعها فريقنا قريباً وسنتابع الأمر — نعدك بذلك 💙",
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
    # 🆕 الگوی استاندارد پایان هر اکشن: بازگشت به منو + دعوت به ثبت نظر کنار هم
    "btn_back_menu": {"fa": "🔙 بازگشت به منو", "en": "🔙 Back to Menu", "ar": "🔙 العودة إلى القائمة"},
    "btn_feedback": {"fa": "💬 پیشنهادات", "en": "💬 Feedback", "ar": "💬 ملاحظات"},
}


def _t(lang: str, key: str) -> str:
    return _T.get(key, {}).get(lang) or _T.get(key, {}).get("fa", key)


def _back_feedback_keyboard(lang: str = "fa") -> InlineKeyboardMarkup:
    """🆕 کیبورد پایان جریان: بازگشت به منو + پیشنهادات (دو دکمه کنار هم).

    قبلاً بعد از ثبت نارضایتی و بعد از پاسخ «راضی بودم» هیچ دکمه‌ای
    ارسال نمی‌شد (reply_markup=None) و کاربر گیر می‌کرد.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(_t(lang, "btn_back_menu"), callback_data="back_main"),
        InlineKeyboardButton(_t(lang, "btn_feedback"), callback_data="start_feedback"),
    ]])


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
        # 🆕 فیکس: قبلاً reply_markup=None بود و کاربر بعد از «راضی بودم» گیر می‌کرد
        await query.edit_message_text(_t(lang, "thanks_happy"), reply_markup=_back_feedback_keyboard(lang))
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
        await update.message.reply_text(_t(lang, "thanks_feedback"), reply_markup=_back_feedback_keyboard(lang))
        return ConversationHandler.END

    try:
        await context.bot.send_message(
            chat_id=settings.admin_chat_id,
            text=admin_message,
            parse_mode="HTML",
        )
        await update.message.reply_text(_t(lang, "thanks_feedback"), reply_markup=_back_feedback_keyboard(lang))
    except Exception as error:
        logger.error(f"Error sending survey to admin: {error}")
        await update.message.reply_text(_t(lang, "send_error"), reply_markup=_back_feedback_keyboard(lang))

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