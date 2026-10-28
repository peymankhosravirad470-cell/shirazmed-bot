# app/bot.py

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)

from app import runtime
from config import settings
from app.handlers.start import (
    start_handler,
    help_handler,
    select_language_handler,
    change_language_handler,
    back_to_main_handler,
    start_feedback_handler,
    feedback_yes_handler,
    feedback_no_handler,
    feedback_text_handler,
)
from app.handlers.callbacks import main_menu_callback, medical_browse_callback
from app.handlers.booking import booking_conversation_handler
from app.handlers.survey import survey_conversation_handler
from app.handlers.companion import companion_conversation_handler
from app.handlers import meds
from app.handlers.meds import meds_conversation_handler
from app.handlers.doctor_reg import (
    doctor_reg_conversation_handler,
    admin_registration_action,
    pending_command,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


LANGUAGE_PATTERN = r"^lang_(fa|en|ar)$"
CHANGE_LANGUAGE_PATTERN = r"^change_language$"
BACK_TO_MAIN_PATTERN = r"^back_main$"

FEEDBACK_START_PATTERN = r"^start_feedback$"
FEEDBACK_YES_PATTERN = r"^feedback_yes$"
FEEDBACK_NO_PATTERN = r"^feedback_no$"

MENU_CALLBACKS: tuple[str, ...] = (
    "start_booking",
    "start_companion",
    "medical",
    "non_medical",
    "non_hospitals",
    "non_hotels",
    "non_motels",
    "non_tourist_houses",
    "non_transport",
    "tourism",
    "tour_city",
    "tour_outside",
    "paramedical",
    "para_physio",
    "para_lab",
    "para_radiology",
    "para_nursing",
    "para_injection",
    "para_trad_med",
    "para_occupational",
    "para_speech",
    "para_orthotics",
    "elderly",
    "elderly_all",
    "hubs",
    "insurance",
    "package",
    "taxi",
    "translator",
    "charter",
    "deepseek",
    "file",
    "appointments",
    "medication",
    "emergency",
    "channel",
    "invite",
    "rights",
    "patient_guide",
    "complaints",
    "complaints_menu",
    "complaints_iranian",
    "complaints_foreign",
    "support",
    "start_survey",
)

MENU_PATTERN = rf"^({'|'.join(MENU_CALLBACKS)})$"

# 🆕 الگوی ریست گفتگو: هر کلیک روی منو/بازگشت/زبان، هر گفتگوی نیمه‌کاره را
# بی‌صدا تمام می‌کند تا کاربر داخل گفتگو گیر نکند و ربات «گیج» نشود.
# (entry pointهای گفتگوها عمداً مستثنی هستند تا رزرو/همراه/نظرسنجی/افزودن دارو
# همچنان شروع شوند.)
_MENU_NO_ENTRY = [c for c in MENU_CALLBACKS if c not in ("start_booking", "start_companion", "start_survey")]
_RESET_EXTRA = (
    "back_main", "change_language", "start_feedback", "feedback_yes", "feedback_no",
    "med_home", "med_list", "med_del", "noop_page",
)
RESET_CONV_PATTERN = rf"^({'|'.join(_MENU_NO_ENTRY + list(_RESET_EXTRA))}|med_del_\d+|med_page_\d+|med_spec_[a-z]+_\d+|med_back|lang_(fa|en|ar))$"

PERSISTENCE_FILE = "data/bot_persistence.pkl"

PRIVATE_CHAT_ONLY = filters.ChatType.PRIVATE

USER_ERROR_MESSAGE = "خطایی رخ داد. لطفاً دوباره تلاش کنید."


async def reset_conversations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🆕 پایان بی‌صدة گفتگوهای نیمه‌کاره هنگام ناوبری منو.

    در گروه ‎-1‎ ثبت می‌شود تا «قبل از» ConversationHandlerها اجرا شود؛ بدون
    این هندلر، اگر کاربر وسط رزرو نوبت منصرف می‌شد و به منو برمی‌گشت، گفتگوی
    رزرو همچنان فعال می‌ماند و بعداً هر متن ساده‌ای که می‌فرستاد به‌عنوان
    «نام بیمار» و... تفسیر می‌شد (رفتار گیج‌کننده‌ای که کاربر گزارش کرد).
    """
    try:
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            return
        key = (chat.id, user.id)
        for conv in (
            booking_conversation_handler,
            survey_conversation_handler,
            companion_conversation_handler,
            meds_conversation_handler,
            doctor_reg_conversation_handler,
        ):
            try:
                conv._conversations.pop(key, None)
            except Exception:
                pass
    except Exception:
        pass


async def global_error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    logger.error(
        "Unhandled exception while processing update:",
        exc_info=context.error,
    )

    if not isinstance(update, Update):
        return

    if update.callback_query is not None:
        try:
            await update.callback_query.answer(
                USER_ERROR_MESSAGE,
                show_alert=True,
            )
            return
        except Exception as error:
            logger.warning(
                "Failed to answer callback in error handler: %s", error
            )

    if update.effective_chat is not None:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=USER_ERROR_MESSAGE,
            )
        except Exception as error:
            logger.warning(
                "Failed to send error message to user: %s", error
            )


def _validate_settings() -> None:
    token: Optional[str] = getattr(settings, "active_token", None)
    if not token or not isinstance(token, str) or not token.strip():
        raise RuntimeError(
            "BOT_TOKEN (settings.active_token) is missing or empty. "
            "Cannot start the bot."
        )


def _register_handlers(application: Application) -> None:
    application.add_error_handler(global_error_handler)

    # 🆕 گروه ‎-1‎: ریست گفتگوهای نیمه‌کاره «قبل از» هر هندلر دیگر؛ چون
    # ApplicationHandlerStop پرتاب نمی‌کنیم، هندلرهای گروه 0 هم همان آپدیت را
    # به‌طور عادی پردازش می‌کنند (ناوبری منو سالم می‌ماند).
    application.add_handler(
        CallbackQueryHandler(reset_conversations_callback, pattern=RESET_CONV_PATTERN),
        group=-1,
    )
    application.add_handler(
        CommandHandler("start", reset_conversations_callback),
        group=-1,
    )

    application.add_handler(
        CommandHandler("start", start_handler, filters=PRIVATE_CHAT_ONLY)
    )
    application.add_handler(
        CommandHandler("help", help_handler, filters=PRIVATE_CHAT_ONLY)
    )

    application.add_handler(
        CallbackQueryHandler(
            select_language_handler,
            pattern=LANGUAGE_PATTERN,
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            change_language_handler,
            pattern=CHANGE_LANGUAGE_PATTERN,
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            back_to_main_handler,
            pattern=BACK_TO_MAIN_PATTERN,
        )
    )

    # هندلرهای نظرسنجی
    application.add_handler(
        CallbackQueryHandler(
            start_feedback_handler,
            pattern=FEEDBACK_START_PATTERN,
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            feedback_yes_handler,
            pattern=FEEDBACK_YES_PATTERN,
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            feedback_no_handler,
            pattern=FEEDBACK_NO_PATTERN,
        )
    )

    # 🆕 یادآور دارو — اکشن‌های ساده (لیست/حذف/خانه)
    application.add_handler(
        CallbackQueryHandler(
            meds.med_menu_callback,
            pattern=r"^med_(list|del|del_\d+|home)$",
        )
    )

    # ConversationHandlerها
    application.add_handler(survey_conversation_handler)
    application.add_handler(companion_conversation_handler)
    application.add_handler(booking_conversation_handler)
    application.add_handler(meds_conversation_handler)

    # 🩺 ثبت‌نام پزشک — کاملاً مخفی:
    #   ورود: فقط /doctor، /docreg یا لینک اختصاصی (?start=docreg)
    #   هیچ دکمه‌ای به منوهای بیمار اضافه نشده است.
    application.add_handler(doctor_reg_conversation_handler)
    # 🩺 دکمه تایید/رد ادمین + دستور مخفی /pending (فقط در چت ادمین پاسخ می‌دهد)
    application.add_handler(
        CallbackQueryHandler(admin_registration_action, pattern=r"^dregadm_(ok|no)_\d+$")
    )
    application.add_handler(
        CommandHandler("pending", pending_command, filters=PRIVATE_CHAT_ONLY)
    )

    # دکمه‌های منو
    application.add_handler(
        CallbackQueryHandler(main_menu_callback, pattern=MENU_PATTERN)
    )

    # مرور پزشکان
    application.add_handler(
        CallbackQueryHandler(
            medical_browse_callback,
            pattern=r"^med_(page_\d+|spec_[a-z]+_\d+|back)$|^noop_page$",
        )
    )

    # ✅ هندلر متن نظر ناراضی (باید در انتها باشد تا مزاحم ConversationHandlerها نشود)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            feedback_text_handler,
        )
    )

    logger.info(
        "Handlers registered: start, help, language, back_main, "
        "feedback_start/yes/no, survey_conversation, companion_conversation, "
        "booking_conversation, meds_conversation, med_menu, "
        "main_menu (%d callbacks), feedback_text, conv-reset(group -1), "
        "doctor_reg(hidden), dregadm, pending.",
        len(MENU_CALLBACKS),
    )


def build_application() -> Application:
    _validate_settings()

    async def _post_init(application: Application) -> None:
        runtime.bind_application(application)
        meds.schedule_all(application)
        logger.info("Post-init: runtime bridge bound + med reminders scheduled.")

    # 🆕 ماندگاری داده‌ها: زبان انتخابی کاربر و وضعیت گفتگوها اکنون روی دیسک
    # (data/ = دیسک لیارا) ذخیره می‌شود؛ پیش‌تر فقط در حافظه بود و با هر
    # ری‌استارت/دیپلوی پاک می‌شد → مشتریِ عرب/انگلیسی پس از اولین کلیک،
    # دوباره فارسی می‌دید. (رفع تداخل زبان)
    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)

    builder = ApplicationBuilder().token(settings.active_token)
    builder.base_url("https://tapi.bale.ai/bot")
    builder.base_file_url("https://tapi.bale.ai/file/bot")
    builder.persistence(persistence)
    builder.post_init(_post_init)
    application = builder.build()

    _register_handlers(application)

    logger.info("Application built successfully.")
    return application