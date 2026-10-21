from telegram import Update
from telegram.ext import ContextTypes
from app.locales import get_msg
from app.keyboards.main import get_language_keyboard, get_main_menu_keyboard, get_back_keyboard

DEFAULT_LANGUAGE = "fa"

def _get_user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang")
    if lang not in ("fa", "en", "ar"):
        return DEFAULT_LANGUAGE
    return lang

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang")
    if lang in ("fa", "en", "ar"):
        await update.message.reply_text(get_msg(lang, "welcome"), reply_markup=get_main_menu_keyboard(lang))
        return
    await update.message.reply_text(get_msg(DEFAULT_LANGUAGE, "welcome"), reply_markup=get_language_keyboard())

async def select_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    if lang not in ("fa", "en", "ar"):
        lang = DEFAULT_LANGUAGE
    context.user_data["lang"] = lang
    await query.edit_message_text(get_msg(lang, "welcome"), reply_markup=get_main_menu_keyboard(lang))

async def change_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = _get_user_lang(context)
    await query.edit_message_text(get_msg(lang, "welcome"), reply_markup=get_language_keyboard())

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_user_lang(context)
    await update.message.reply_text(get_msg(lang, "help"), reply_markup=get_back_keyboard(lang))

async def back_to_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = _get_user_lang(context)
    await query.edit_message_text(get_msg(lang, "welcome"), reply_markup=get_main_menu_keyboard(lang))