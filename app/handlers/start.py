# app/handlers/start.py

from __future__ import annotations

import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.keyboards.main import (
    get_language_keyboard,
    get_main_menu_keyboard,
)

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


async def _edit_menu_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    """🎯 فیکس تکرار منو: نمایش منو روی «همان پیام فعلی» به‌جای پیام جدید.

    ۱) ابتدا پیام فعلی ویرایش می‌شود (edit_message_text)
    ۲) اگر ویرایش ممکن نبود، پیام قبلی حذف و پیام جدید ارسال می‌شود
    ۳) اگر آن هم نشد، فقط پیام جدید ارسال می‌شود

    نتیجه: با هر بار زدن «بازگشت»، منوی تکراری در چت ساخته نمی‌شود و
    همیشه فقط یک منوی اصلی روی صفحه است.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    query = update.callback_query
    if query is not None and query.message is not None:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
            return
        except Exception as exc:
            # «Message is not modified» یعنی همان محتوای فعلی درست است — خطا نیست
            if "not modified" in str(exc).lower():
                return
            logger.debug(f"Could not edit message, will replace it: {exc}")
            # ویرایش نشد → پیام قبلی حذف شود تا منوی تکراری در چت نماند
            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=query.message.message_id
                )
            except Exception:
                pass

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


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

    # 🎯 فیکس تکرار منو: همان پیام به منوی اصلی تبدیل می‌شود
    await _edit_menu_message(update, context, WELCOME_TEXT, get_main_menu_keyboard(lang))


async def change_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی انتخاب زبان (بدون پاک کردن پیام اصلی)."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    # 🎯 فیکس تکرار منو: همان پیام به منوی زبان تبدیل می‌شود
    await _edit_menu_message(
        update,
        context,
        "🌐 لطفاً زبان خود را انتخاب کنید:",
        get_language_keyboard(),
    )


async def back_to_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اصلی.

    🎯 فیکس تکرار منو: پیام فعلی به منوی اصلی «ویرایش» می‌شود؛ اگر ویرایش
    ممکن نباشد، پیام قبلی حذف و منوی اصلی جایگزین آن می‌شود. بنابراین
    دیگر با هر بار بازگشت، منوی تکراری جدیدی در چت ساخته نمی‌شود.
    """
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    lang = _get_lang(context)

    await _edit_menu_message(update, context, WELCOME_TEXT, get_main_menu_keyboard(lang)) 