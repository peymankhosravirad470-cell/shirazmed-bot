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


WELCOME_TEXTS = {
    "fa": (
        "🌟 یه پیام بدی، همه‌چیز رو آماده می‌کنیم.\n\n"
        "از پزشک تا هتل، از ترانسفر تا مترجم،\n"
        "از نوبت تا گشت گردشگری — همه‌چیز یکجا.\n\n"
        "💙 بدون دغدغه، بدون هزینه اضافه\n\n"
        "👇 از دکمه‌های زیر انتخاب کن:"
    ),
    "en": (
        "🌟 Send us a message, we'll prepare everything.\n\n"
        "From doctor to hotel, from transfer to translator,\n"
        "from appointment to city tour — all in one place.\n\n"
        "💙 Without worry, without extra cost\n\n"
        "👇 Choose from the buttons below:"
    ),
    "ar": (
        "🌟 أرسل لنا رسالة، وسنجهز كل شيء.\n\n"
        "من الطبيب إلى الفندق، من النقل إلى المترجم،\n"
        "من الموعد إلى الجولة السياحية — كل شيء في مكان واحد.\n\n"
        "💙 بدون قلق، بدون تكلفة إضافية\n\n"
        "👇 اختر من الأزرار أدناه:"
    ),
}


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
    """نمایش منو روی همان پیام فعلی و پاک کردن پیام‌های قبلی."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    query = update.callback_query
    if query is not None and query.message is not None:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
            return
        except Exception as exc:
            if "not modified" in str(exc).lower():
                return
            logger.debug(f"Could not edit message, will replace it: {exc}")
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

    if not lang:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🌐 لطفاً زبان خود را انتخاب کنید:\nPlease choose your language:\nالرجاء اختيار اللغة:",
                reply_markup=get_language_keyboard(),
            )
        except Exception as e:
            logger.error(f"Error sending language selection: {e}")
        return

    welcome_text = WELCOME_TEXTS.get(lang, WELCOME_TEXTS["fa"])
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(lang),
        )
    except Exception as e:
        logger.error(f"Error sending main menu: {e}")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /help: نمایش راهنمای مختصر."""
    if update.effective_chat is None:
        return

    lang = _get_lang(context)
    help_texts = {
        "fa": "راهنمای ربات شیراز مدیکال:\n\nاز منوی اصلی استفاده کنید.",
        "en": "Shiraz Medical Bot Guide:\n\nUse the main menu.",
        "ar": "دليل روبوت شيراز الطبي:\n\nاستخدم القائمة الرئيسية.",
    }
    text = help_texts.get(lang, help_texts["fa"])
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
    data = query.data
    lang = data.replace("lang_", "")

    if lang not in ("fa", "en", "ar"):
        lang = "fa"

    context.user_data["lang"] = lang

    welcome_text = WELCOME_TEXTS.get(lang, WELCOME_TEXTS["fa"])
    await _edit_menu_message(update, context, welcome_text, get_main_menu_keyboard(lang))


async def change_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی انتخاب زبان."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    await _edit_menu_message(
        update,
        context,
        "🌐 لطفاً زبان خود را انتخاب کنید:\nPlease choose your language:\nالرجاء اختيار اللغة:",
        get_language_keyboard(),
    )


async def back_to_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اصلی با حفظ زبان کاربر."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    lang = _get_lang(context)
    welcome_text = WELCOME_TEXTS.get(lang, WELCOME_TEXTS["fa"])
    await _edit_menu_message(update, context, welcome_text, get_main_menu_keyboard(lang))