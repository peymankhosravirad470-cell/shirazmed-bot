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


def _back_to_menu_keyboard():
    """✅ دکمه بازگشت به منو."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")]
    ])


async def start_companion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند ثبت همراه بیمار."""
    query = update.callback_query
    if query is not None:
        await query.answer()

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("بله، مایل هستم", callback_data="comp_yes")],
            [InlineKeyboardButton("خیر، نیازی نیست", callback_data="comp_no")],
            [InlineKeyboardButton("لغو", callback_data="comp_cancel")],
        ])

        await query.edit_message_text(
            "🤝 همراه بیمار\n\n"
            "آیا مایل هستید شخص دیگری (مثلاً یکی از اعضای خانواده یا دوستان) "
            "در جریان روند درمان شما قرار بگیرد و ما اطلاعات را با او به اشتراک بگذاریم؟",
            reply_markup=keyboard,
        )
        return ASK_IS_COMPANION
    return ConversationHandler.END


async def receive_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت پاسخ بله یا خیر از کاربر."""
    query = update.callback_query
    if query is None: return ASK_IS_COMPANION
    await query.answer()

    if query.data == "comp_no":
        await query.edit_message_text(
            "بسیار خب. در صورت نیاز در آینده می‌توانید از این بخش استفاده کنید.",
            reply_markup=_back_to_menu_keyboard(),
        )
        context.user_data.pop("companion_name", None)
        return ConversationHandler.END

    if query.data == "comp_cancel":
        context.user_data.pop("companion_name", None)
        await query.edit_message_text(
            "فرآیند ثبت همراه بیمار لغو شد.",
            reply_markup=_back_to_menu_keyboard(),
        )
        return ConversationHandler.END
    
    # اگر بله را زد، نام همراه را می‌پرسیم
    await query.edit_message_text(
        "لطفاً نام و نام خانوادگی همراه خود را وارد کنید:\n\n"
        "🚪 برای لغو، دستور /cancel را بفرستید.",
        reply_markup=None
    )
    return ASK_NAME


async def receive_companion_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت نام همراه."""
    if update.message is None or update.message.text is None:
        return ASK_NAME
    
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("نام وارد شده بسیار کوتاه است. لطفاً نام کامل را وارد کنید:")
        return ASK_NAME
        
    context.user_data["companion_name"] = name
    
    await update.message.reply_text("لطفاً شماره تماس همراه خود را وارد کنید (مثال: 09123456789):\n\n🚪 برای لغو، دستور /cancel را بفرستید:")
    return ASK_PHONE


async def receive_companion_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت شماره تماس همراه و ارسال پیام (شبیه‌سازی SMS)."""
    if update.message is None or update.message.text is None:
        return ASK_PHONE
    
    phone = update.message.text.strip()
    if not phone.replace("+", "").replace("-", "").isdigit() or len(phone) < 10:
        await update.message.reply_text("شماره وارد شده معتبر نیست. لطفاً دوباره وارد کنید:")
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
    await update.message.reply_text(
        "✅ اطلاعات همراه شما با موفقیت ثبت شد.\n"
        f"در صورت نیاز، پیام اطلاع‌رسانی برای شماره {phone} ارسال خواهد شد.",
        reply_markup=_back_to_menu_keyboard(),
    )
    
    # پاکسازی داده‌های موقت
    context.user_data.pop("companion_name", None)
    return ConversationHandler.END


async def cancel_companion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لغو فرآیند (دستور /cancel یا هر دستور دیگر)."""
    context.user_data.pop("companion_name", None)
    if update.message is not None:
        await update.message.reply_text(
            "فرآیند ثبت همراه بیمار لغو شد.",
            reply_markup=_back_to_menu_keyboard(),
        )
    if update.callback_query is not None:
        try:
            await update.callback_query.edit_message_text(
                "فرآیند ثبت همراه بیمار لغو شد.",
                reply_markup=_back_to_menu_keyboard(),
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