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

logger = logging.getLogger(__name__)

# مراحل گفتگو
ASK_SATISFACTION, ASK_REASON = range(2)

# آیدی ادمین (طبق دستور پرامپت)
ADMIN_CHAT_ID = 1967087863


def _get_survey_keyboard() -> InlineKeyboardMarkup:
    """کیبورد سوال رضایت‌سنجی."""
    keyboard = [
        [
            InlineKeyboardButton("بله، ادامه می‌دهم", callback_data="survey_yes"),
            InlineKeyboardButton("خیر، کافی است", callback_data="survey_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع نظرسنجی (این تابع می‌تواند از هر جایی صدا زده شود)."""
    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(
            "از اینکه با ما همراه بودید سپاسگزاریم.\n\nآیا مایل به ادامه استفاده از خدمات هستید؟",
            reply_markup=_get_survey_keyboard(),
        )
    elif update.message is not None:
        await update.message.reply_text(
            "از اینکه با ما همراه بودید سپاسگزاریم.\n\nآیا مایل به ادامه استفاده از خدمات هستید؟",
            reply_markup=_get_survey_keyboard(),
        )
    
    return ASK_SATISFACTION


async def handle_satisfaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پردازش پاسخ بله یا خیر."""
    query = update.callback_query
    if query is None:
        return ASK_SATISFACTION

    await query.answer()
    data = query.data

    if data == "survey_yes":
        await query.edit_message_text(
            "از همراهی شما صمیمانه سپاسگزاریم. روز خوبی داشته باشید! 🌸",
            reply_markup=None,
        )
        return ConversationHandler.END

    elif data == "survey_no":
        await query.edit_message_text(
            "متأسفیم که تجربه خوبی نداشتید. لطفاً در یک پیام کوتاه بنویسید چه چیزی باعث نارضایتی شما شد تا ما بهتر شویم:",
            reply_markup=None,
        )
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
        f"🚨 **نارضایتی کاربر**\n\n"
        f"👤 نام: {full_name}\n"
        f"🆔 آیدی عددی: `{user_id}`\n"
        f"🌐 یوزرنیم: {username}\n\n"
        f"📝 علت نارضایتی:\n{reason}"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="Markdown",
        )
        await update.message.reply_text(
            "از اینکه نظر خود را با ما در میان گذاشتید سپاسگزاریم. تیم پشتیبانی ما به زودی بررسی می‌کند.",
            reply_markup=None,
        )
    except Exception as error:
        logger.error(f"Error sending survey to admin: {error}")
        await update.message.reply_text(
            "متأسفانه در ارسال پیام خطایی رخ داد، اما نظر شما ثبت شد. سپاسگزاریم.",
            reply_markup=None,
        )

    return ConversationHandler.END


async def cancel_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لغو نظرسنجی (در صورت نیاز)."""
    if update.message is not None:
        await update.message.reply_text("نظرسنجی لغو شد.")
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
    fallbacks=[
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reason)
    ],
    allow_reentry=True,
)