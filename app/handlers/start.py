# app/handlers/start.py

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.keyboards.main import (
    get_language_keyboard,
    get_main_menu_keyboard,
)
from config import settings

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

FEEDBACK_ASK = {
    "fa": "🌟 از خدمات ما راضی بودید؟\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
    "en": "🌟 Were you satisfied with our services?\n\nPlease choose one:",
    "ar": "🌟 هل كنت راضياً عن خدماتنا؟\n\nيرجى اختيار أحد الخيارات:",
}

FEEDBACK_YES = {
    "fa": (
        "🌹 چقدر خوشحالیم که از خدمات ما راضی بودید! 💙\n\n"
        "🌸 امیدواریم همیشه در سلامت، شادی و آرامش باشید.\n"
        "✨ حضور شما برای ما ارزشمند است و افتخار می‌کنیم که در مسیر سلامت همراهتان بودیم.\n\n"
        "🌷 از صمیم قلب آرزو می‌کنیم روزهایتان پر از لبخند و سلامتی باشد. 💫"
    ),
    "en": (
        "🌹 We're so happy you were satisfied with our services! 💙\n\n"
        "🌸 We wish you health, happiness, and peace always.\n"
        "✨ Your presence is valuable to us, and we're honored to have accompanied you on your health journey.\n\n"
        "🌷 From the bottom of our hearts, we wish your days to be full of smiles and health. 💫"
    ),
    "ar": (
        "🌹 نحن سعداء جداً لأنك كنت راضياً عن خدماتنا! 💙\n\n"
        "🌸 نتمنى لك الصحة والسعادة والسلام دائماً.\n"
        "✨ وجودك قيم بالنسبة لنا، ونحن فخورون بمرافقتك في رحلة صحتك.\n\n"
        "🌷 من أعماق قلوبنا، نتمنى أن تكون أيامك مليئة بالابتسامات والصحة. 💫"
    ),
}

FEEDBACK_NO = {
    "fa": (
        "😔 از اینکه تجربه‌تان خوب نبوده، صمیمانه عذرخواهی می‌کنیم.\n\n"
        "🙏 لطفاً ایراد یا نظر خود را بنویسید تا تیم ما در اسرع وقت بررسی و رفع کند.\n\n"
        "💙 نظر شما برای ما بسیار ارزشمند است و به ما کمک می‌کند بهتر شویم."
    ),
    "en": (
        "😔 We sincerely apologize that your experience wasn't good.\n\n"
        "🙏 Please write your feedback so our team can review and fix it as soon as possible.\n\n"
        "💙 Your feedback is very valuable to us and helps us improve."
    ),
    "ar": (
        "😔 نعتذر بصدق لأن تجربتك لم تكن جيدة.\n\n"
        "🙏 يرجى كتابة ملاحظاتك حتى يتمكن فريقنا من مراجعتها وإصلاحها في أقرب وقت ممكن.\n\n"
        "💙 ملاحظاتك قيمة جداً بالنسبة لنا وتساعدنا على التحسن."
    ),
}

FEEDBACK_THANKS = {
    "fa": (
        "🙏 از اینکه نظر خود را با ما به اشتراک گذاشتید، صمیمانه سپاسگزاریم.\n\n"
        "💙 قول می‌دهیم حتماً بررسی و رفع شود.\n\n"
        "🌟 سلامت و شاد باشید. 🌹"
    ),
    "en": (
        "🙏 Thank you sincerely for sharing your feedback with us.\n\n"
        "💙 We promise it will definitely be reviewed and fixed.\n\n"
        "🌟 Stay healthy and happy. 🌹"
    ),
    "ar": (
        "🙏 شكراً جزيلاً لمشاركتنا ملاحظاتك.\n\n"
        "💙 نعدك بأنه سيتم مراجعته وإصلاحه بالتأكيد.\n\n"
        "🌟 دم بصحة وسعادة. 🌹"
    ),
}


def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang", "fa")
    return lang if lang in ("fa", "en", "ar") else "fa"


def _feedback_keyboard(lang: str) -> InlineKeyboardMarkup:
    texts = {
        "fa": ("👍 بله، راضی بودم", "👎 نه، راضی نبودم"),
        "en": ("👍 Yes, I was satisfied", "👎 No, I wasn't satisfied"),
        "ar": ("👍 نعم، كنت راضياً", "👎 لا، لم أكن راضياً"),
    }
    yes, no = texts.get(lang, texts["fa"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(yes, callback_data="feedback_yes")],
        [InlineKeyboardButton(no, callback_data="feedback_no")],
    ])


async def _edit_menu_message(update, context, text, reply_markup):
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
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
            except Exception:
                pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    # 🩺 ثبت‌نام پزشک: لینک اختصاصی (?start=docreg) نباید منوی بیمار را بفرستد.
    # فرم ثبت‌نام توسط doctor_reg_conversation_handler شروع می‌شود (ورود مخفی —
    # بیمارها هیچ دکمه یا دستوری از آن نمی‌بینند).
    if (context.args or []) and str(context.args[0]).strip().lower() == "docreg":
        return
    lang = context.user_data.get("lang")
    if not lang:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🌐 لطفاً زبان خود را انتخاب کنید:\nPlease choose your language:\nالرجاء اختيار اللغة:",
            reply_markup=get_language_keyboard(),
        )
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=WELCOME_TEXTS.get(lang, WELCOME_TEXTS["fa"]),
        reply_markup=get_main_menu_keyboard(lang),
    )


HELP_TEXTS = {
    "fa": "راهنمای ربات:\n\nاز دکمه‌های منوی اصلی استفاده کنید. برای تغییر زبان، دکمه «🌐 تغییر زبان» را بزنید.",
    "en": "Bot guide:\n\nUse the main menu buttons. To change the language, tap the \"🌐 Change Language\" button.",
    "ar": "دليل الروبوت:\n\nاستخدم أزرار القائمة الرئيسية. لتغيير اللغة، اضغط زر «🌐 تغيير اللغة».",
}


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _get_lang(context)
    await update.message.reply_text(
        text=HELP_TEXTS.get(lang, HELP_TEXTS["fa"]),
        reply_markup=get_main_menu_keyboard(lang),
    )


async def select_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    lang = query.data.replace("lang_", "")
    if lang not in ("fa", "en", "ar"):
        lang = "fa"
    context.user_data["lang"] = lang
    # 🎯 فیکس تکرار منو: همان پیام به منوی اصلی تبدیل می‌شود (با fallback)
    await _edit_menu_message(
        update,
        context,
        WELCOME_TEXTS.get(lang, WELCOME_TEXTS["fa"]),
        get_main_menu_keyboard(lang),
    )


async def change_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    # 🎯 فیکس تکرار منو: همان پیام به منوی زبان تبدیل می‌شود (با fallback)
    await _edit_menu_message(
        update,
        context,
        "🌐 لطفاً زبان خود را انتخاب کنید:\nPlease choose your language:\nالرجاء اختيار اللغة:",
        get_language_keyboard(),
    )


async def back_to_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اصلی.

    🎯 فیکس تکرار منو: پیام فعلی به منوی اصلی «ویرایش» می‌شود؛ اگر ویرایش
    ممکن نباشد، پیام قبلی حذف و منوی اصلی جایگزین می‌شود تا هیچ‌وقت منوی
    تکراری ساخته نشود.
    """
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    lang = _get_lang(context)
    await _edit_menu_message(
        update,
        context,
        WELCOME_TEXTS.get(lang, WELCOME_TEXTS["fa"]),
        get_main_menu_keyboard(lang),
    )


async def start_feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع نظرسنجی با کلیک روی دکمه پیشنهادات."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    lang = _get_lang(context)
    await _edit_menu_message(
        update,
        context,
        FEEDBACK_ASK.get(lang, FEEDBACK_ASK["fa"]),
        _feedback_keyboard(lang),
    )


async def feedback_yes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر راضی بود - نمایش پیام تشکر + دکمه بازگشت به منو."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    lang = _get_lang(context)
    back_labels = {
        "fa": "🔙 بازگشت به منو",
        "en": "🔙 Back to Menu",
        "ar": "🔙 العودة إلى القائمة",
    }
    await _edit_menu_message(
        update,
        context,
        text=FEEDBACK_YES.get(lang, FEEDBACK_YES["fa"]),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(back_labels.get(lang, back_labels["fa"]), callback_data="back_main")]
        ]),
    )


async def feedback_no_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر ناراضی بود - درخواست نوشتن نظر."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    lang = _get_lang(context)
    context.user_data["awaiting_feedback"] = True
    back_labels = {
        "fa": "🔙 بازگشت",
        "en": "🔙 Back",
        "ar": "🔙 رجوع",
    }
    await _edit_menu_message(
        update,
        context,
        text=FEEDBACK_NO.get(lang, FEEDBACK_NO["fa"]),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(back_labels.get(lang, back_labels["fa"]), callback_data="back_main")
        ]]),
    )


async def feedback_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت متن نظر ناراضی و ارسال برای ادمین.

    🎯 فیکس: قبلاً از متغیر محیطی ADMIN_ID خوانده می‌شد که هیچ‌جا مستند/تنظیم
    نشده بود — در نتیجه نظرات ناراضی هرگز به ادمین نمی‌رسید. حالا از
    settings.admin_chat_id (متغیر ADMIN_CHAT_ID، همان که survey.py استفاده می‌کند)
    خوانده می‌شود.
    """
    if not context.user_data.get("awaiting_feedback"):
        return
    context.user_data["awaiting_feedback"] = False
    lang = _get_lang(context)
    user = update.effective_user
    text = update.message.text
    first_name = user.first_name if user else "کاربر"
    username = f"@{user.username}" if user and user.username else "—"
    user_id = user.id if user else 0
    if settings.admin_chat_id:
        try:
            await context.bot.send_message(
                chat_id=settings.admin_chat_id,
                text=(
                    f"❌ نظر ناراضی جدید\n\n"
                    f"👤 کاربر: {first_name} ({username})\n"
                    f"🆔 Chat ID: {user_id}\n\n"
                    f"💬 متن نظر:\n{text}"
                ),
            )
        except Exception as e:
            logger.error(f"Error sending feedback: {e}")
    else:
        logger.warning("ADMIN_CHAT_ID تنظیم نشده است؛ نظر ناراضی برای ادمین ارسال نشد.")
    await update.message.reply_text(
        text=f"{FEEDBACK_THANKS.get(lang, FEEDBACK_THANKS['fa'])}\n\n{WELCOME_TEXTS.get(lang, WELCOME_TEXTS['fa'])}",
        reply_markup=get_main_menu_keyboard(lang),
    )