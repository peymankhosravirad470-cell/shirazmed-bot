# app/handlers/start.py

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.keyboards.main import (
    get_language_keyboard,
    get_main_menu_keyboard,
)
from app.handlers import chunks as chunk_tracker
from config import settings

logger = logging.getLogger(__name__)

# 🆕 v49 — متن خوشامدگویی رسمی جدید (سه‌زبانه). این متن در «همه» مسیرهای
# نمایش منوی اصلی استفاده می‌شود: /start، انتخاب زبان، بازگشت به منو و پایان
# ثبت نظر (جستجوی «WELCOME_TEXTS» در همین فایل).
WELCOME_TEXTS = {
    "fa": (
        "🌿 به شیراز مدیکال خوش آمدید\n\n"
        "در مسیر درمان، همراه شما هستیم.\n\n"
        "شیراز مدیکال به شما کمک می‌کند تا برای دریافت خدمات درمانی در شیراز، "
        "اطلاعات موردنیاز خود را پیدا کنید و مراحل درمان و سفر خود را با آرامش بیشتری پیگیری کنید.\n\n"
        "از راهنمایی برای انتخاب پزشک و آشنایی با مراکز درمانی تا هماهنگی نوبت، "
        "اقامت، رفت‌وآمد و خدمات ترجمه، می‌توانید از راهنمایی‌های ما استفاده کنید.\n\n"
        "چطور می‌توانیم به شما کمک کنیم؟\n\n"
        "🩺 معرفی پزشکان و مراکز درمانی\n"
        "📅 راهنمایی و هماهنگی نوبت\n"
        "🏨 معرفی هتل و محل اقامت\n"
        "🚗 راهنمایی درباره حمل‌ونقل و ترانسفر\n"
        "🌐 خدمات ترجمه و همراهی زبانی\n"
        "🧳 راهنمای سفر درمانی و گردشگری شیراز\n"
        "💬 راهنمایی و پاسخ‌گویی به پرسش‌های شما\n\n"
        "برای شروع، کافی است نیاز خود را برای ما بنویسید؛ برای مثال:\n\n"
        "• «به دنبال متخصص قلب هستم.»\n"
        "• «برای درمان به شیراز سفر می‌کنم.»\n"
        "• «به هتل و ترانسفر نیاز دارم.»\n"
        "• «برای گرفتن نوبت راهنمایی می‌خواهم.»\n\n"
        "تلاش می‌کنیم اطلاعات روشن و راهنمایی مناسبی در اختیارتان قرار دهیم "
        "تا بتوانید آگاهانه‌تر تصمیم بگیرید.\n\n"
        "شیراز مدیکال؛ همراه شما در مسیر درمان و سفر."
    ),
    "en": (
        "🌿 Welcome to Shiraz Medical\n\n"
        "We are by your side on the road to treatment.\n\n"
        "Shiraz Medical helps you find the information you need to receive healthcare "
        "services in Shiraz, and follow your treatment and travel steps with greater peace of mind.\n\n"
        "From guidance on choosing a doctor and getting to know medical centers, to "
        "appointment coordination, accommodation, transportation and interpretation services — our guidance is here for you.\n\n"
        "How can we help you?\n\n"
        "🩺 Doctors & Medical Centers\n"
        "📅 Appointment Guidance & Coordination\n"
        "🏨 Hotels & Accommodation\n"
        "🚗 Transportation & Transfer\n"
        "🌐 Interpretation & Language Assistance\n"
        "🧳 Medical Travel & Shiraz Tourism Guide\n"
        "💬 Guidance & Answers to Your Questions\n\n"
        "To get started, simply tell us what you need; for example:\n\n"
        "• \"I'm looking for a cardiologist.\"\n"
        "• \"I'm traveling to Shiraz for treatment.\"\n"
        "• \"I need a hotel and transfer.\"\n"
        "• \"I'd like help booking an appointment.\"\n\n"
        "We strive to provide clear information and helpful guidance so you can make "
        "more informed decisions.\n\n"
        "Shiraz Medical — your companion on the road to treatment and travel."
    ),
    "ar": (
        "🌿 أهلاً بك في شيراز ميديكال\n\n"
        "نحن معك في رحلة العلاج.\n\n"
        "يساعدك شيراز ميديكال في العثور على المعلومات التي تحتاجها للحصول على الخدمات "
        "الصحية في شيراز، ومتابعة خطوات علاجك وسفرك براحة أكبر.\n\n"
        "من الإرشاد لاختيار الطبيب والتعرف على المراكز الطبية، إلى تنسيق الموعد "
        "والإقامة والتنقل وخدمات الترجمة — يمكنك الاستعانة بإرشاداتنا.\n\n"
        "كيف يمكننا مساعدتك؟\n\n"
        "🩺 تعريف بالأطباء والمراكز الطبية\n"
        "📅 إرشاد وتنسيق الموعد\n"
        "🏨 تعريف بالفنادق وأماكن الإقامة\n"
        "🚗 إرشادات النقل والتنقل\n"
        "🌐 خدمات الترجمة والمرافقة اللغوية\n"
        "🧳 دليل السفر العلاجي والسياحة في شيراز\n"
        "💬 الإرشاد والإجابة عن أسئلتك\n\n"
        "للبدء، يكفي أن تكتب لنا احتياجك؛ على سبيل المثال:\n\n"
        "• «أبحث عن طبيب مختص في أمراض القلب.»\n"
        "• «أسافر إلى شيراز للعلاج.»\n"
        "• «أحتاج إلى فندق وخدمة نقل.»\n"
        "• «أريد المساعدة في حجز موعد.»\n\n"
        "نسعى لتوفير معلومات واضحة وإرشادات مناسبة لتتمكن من اتخاذ قرارك بوعي "
        "وثقة أكبر.\n\n"
        "شيراز ميديكال؛ رفيقك في رحلة العلاج والسفر."
    ),
}

FEEDBACK_ASK = {
    "fa": "🌟 نظر شما ما رو بهتر می‌کنه!\n\nاز خدمات ما راضی بودید؟ یکی از گزینه‌های زیر رو انتخاب کنید:",
    "en": "🌟 Your opinion helps us improve!\n\nWere you happy with our services? Pick one below:",
    "ar": "🌟 رأيك يساعدنا على التحسن!\n\nهل كنت سعيداً بخدماتنا؟ اختر أحد الخيارات أدناه:",
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
        "🙏 ممنون که وقت گذاشتید و بهمون گفتید.\n\n"
        "💙 قول می‌دیم جدی بررسی‌اش کنیم و خبرش رو بهتون بدیم.\n\n"
        "🌟 سلامت و شاد باشید. 🌹"
    ),
    "en": (
        "🙏 Thank you for taking the time to tell us.\n\n"
        "💙 We promise to look into it properly and get back to you.\n\n"
        "🌟 Stay healthy and happy. 🌹"
    ),
    "ar": (
        "🙏 شكراً لتخصيص الوقت لإخبارنا.\n\n"
        "💙 نعدك بأن ندرسه بجدية ونخبرك بالنتيجة.\n\n"
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
    # 🧹 فیکس بقایای لیست چندپیامی: قبل از ویرایش پیام فعلی (بازگشت به منو،
    # تغییر زبان، شروع پیشنهادات و…)، تکه‌های غیر آخرِ لیست قبلی حذف می‌شوند.
    await chunk_tracker.cleanup(context, chat_id)
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
    # 🎯 پاک‌سازی پرچم کهنه: بازگشت به منو یعنی کاربر از ثبت نظر منصرف شده؛
    # در غیر این صورت متن بعدی‌اش بی‌اجازه به‌عنوان نظر ارسال می‌شد.
    context.user_data["awaiting_feedback"] = False
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


def _back_feedback_keyboard(lang: str) -> InlineKeyboardMarkup:
    """🆕 الگوی استاندارد: بازگشت به منو + دعوت به ثبت نظر کنار هم."""
    back_labels = {
        "fa": "🔙 بازگشت به منو",
        "en": "🔙 Back to Menu",
        "ar": "🔙 العودة إلى القائمة",
    }
    feedback_labels = {
        "fa": "💬 پیشنهادات",
        "en": "💬 Feedback",
        "ar": "💬 ملاحظات",
    }
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(back_labels.get(lang, back_labels["fa"]), callback_data="back_main"),
        InlineKeyboardButton(feedback_labels.get(lang, feedback_labels["fa"]), callback_data="start_feedback"),
    ]])


async def feedback_yes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر راضی بود - نمایش پیام تشکر + دکمه بازگشت به منو."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    # 🎯 پاک‌سازی پرچم کهنه: اگر قبلاً «ناراضی» زده بود ولی متنی نفرستاده بود،
    # پرچم فعال می‌ماند و متن بعدی‌اش بی‌اجازه به‌عنوان نظر ثبت می‌شد.
    context.user_data["awaiting_feedback"] = False
    lang = _get_lang(context)
    await _edit_menu_message(
        update,
        context,
        text=FEEDBACK_YES.get(lang, FEEDBACK_YES["fa"]),
        reply_markup=_back_feedback_keyboard(lang),
    )


async def feedback_no_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر ناراضی بود - درخواست نوشتن نظر."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    lang = _get_lang(context)
    context.user_data["awaiting_feedback"] = True
    await _edit_menu_message(
        update,
        context,
        text=FEEDBACK_NO.get(lang, FEEDBACK_NO["fa"]),
        reply_markup=_back_feedback_keyboard(lang),
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