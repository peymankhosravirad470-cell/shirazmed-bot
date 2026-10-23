# app/handlers/start.py

from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main import (
    get_language_keyboard,
    get_main_menu_keyboard,
    get_back_keyboard,
)
from app.locales import get_msg_btn

logger = logging.getLogger(__name__)


# متن خوش‌آمدگویی که در منوی اصلی استفاده می‌شود
WELCOME_TEXT = (
    "🌟 یه پیام بدی، همه‌چیز رو آماده می‌کنیم.\n\n"
    "از پزشک تا هتل، از ترانسفر تا مترجم،\n"
    "از نوبت تا گشت گردشگری — همه‌چیز یکجا.\n\n"
    "💙 بدون دغدغه، بدون هزینه اضافه\n\n"
    "👇 از دکمه‌های زیر انتخاب کن:"
)


def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """دریافت زبان کاربر با پیش‌فرض فارسی."""
    lang = context.user_data.get("lang", "fa")
    if lang not in ("fa", "en", "ar"):
        return "fa"
    return lang


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /start: اگر زبان انتخاب نشده باشد، منوی زبان، وگرنه منوی اصلی."""
    if update.effective_chat is None:
        return

    lang = context.user_data.get("lang")

    # اگر زبان کاربر تنظیم نشده، ابتدا منوی انتخاب زبان را نمایش بده
    if not lang:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🌐 لطفاً زبان خود را انتخاب کنید:",
                reply_markup=get_language_keyboard(),
            )
        except Exception as e:
            logger.error(f"Error sending language selection: {e}")
        return

    # اگر زبان تنظیم شده، منوی اصلی را نمایش بده
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(lang),
        )
    except Exception as e:
        logger.error(f"Error sending main menu: {e}")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /help: نمایش راهنمای مختصر."""
    if update.effective_chat is None:
        return

    lang = _get_lang(context)
    text = (
        "راهنمای ربات شیراز مدیکال:\n\n"
        "• از منوی اصلی می‌توانید به بخش‌های مختلف دسترسی داشته باشید.\n"
        "• برای رزرو نوبت، دکمه «📅 رزرو نوبت» را بزنید.\n"
        "• برای تغییر زبان، دکمه «🌐 تغییر زبان» را بزنید.\n"
        "• برای بازگشت به این منو، هر زمان می‌توانید دکمه «🔙 بازگشت» را بزنید."
    )
    try:
        await update.message.reply_text(
            text=text,
            reply_markup=get_main_menu_keyboard(lang),
        )
    except Exception as e:
        logger.error(f"Error sending help: {e}")


async def select_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انتخاب زبان توسط کاربر و سپس نمایش منوی اصلی."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    data = query.data  # مثل: lang_fa, lang_en, lang_ar
    lang = data.replace("lang_", "")

    if lang not in ("fa", "en", "ar"):
        lang = "fa"

    context.user_data["lang"] = lang

    try:
        # ویرایش پیام قبلی به جای ارسال پیام جدید
        await query.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(lang),
        )
    except Exception as e:
        logger.error(f"Error editing message on language select: {e}")
        # اگر ویرایش ممکن نبود، پیام جدید بفرست (مثلاً پیام قبلی عکس بوده)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(lang),
        )


async def change_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی انتخاب زبان (بدون پاک کردن پیام اصلی)."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    try:
        # ویرایش پیام فعلی به منوی انتخاب زبان
        await query.edit_message_text(
            text="🌐 لطفاً زبان خود را انتخاب کنید:",
            reply_markup=get_language_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error editing message on change language: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🌐 لطفاً زبان خود را انتخاب کنید:",
            reply_markup=get_language_keyboard(),
        )


async def back_to_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اصلی (با ویرایش پیام فعلی به جای ارسال پیام جدید)."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    lang = _get_lang(context)

    try:
        # ویرایش پیام فعلی به منوی اصلی
        await query.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(lang),
        )
    except Exception as e:
        # اگر ویرایش ممکن نبود (مثلاً پیام قبلی عکس بوده)، پیام جدید بفرست
        logger.debug(f"Could not edit message: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(lang),
        )