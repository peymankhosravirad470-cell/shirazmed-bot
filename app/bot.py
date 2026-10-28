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
    "site",
    "start_survey",
)

MENU_PATTERN = rf"^({'|'.join(MENU_CALLBACKS)})$"

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


def _register_handlers(application: Application) -> None:
    application.add_error_handler(global_error_handler)

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
        CallbackQueryHandler(select_language_handler, pattern=LANGUAGE_PATTERN)
    )
    application.add_handler(
        CallbackQueryHandler(change_language_handler, pattern=CHANGE_LANGUAGE_PATTERN)
    )
    application.add_handler(
        CallbackQueryHandler(back_to_main_handler, pattern=BACK_TO_MAIN_PATTERN)
    )

    application.add_handler(
        CallbackQueryHandler(start_feedback_handler, pattern=FEEDBACK_START_PATTERN)
    )
    application.add_handler(
        CallbackQueryHandler(feedback_yes_handler, pattern=FEEDBACK_YES_PATTERN)
    )
    application.add_handler(
        CallbackQueryHandler(feedback_no_handler, pattern=FEEDBACK_NO_PATTERN)
    )

    application.add_handler(
        CallbackQueryHandler(meds.med_menu_callback, pattern=r"^med_(list|del|del_\d+|home)$")
    )

    application.add_handler(survey_conversation_handler)
    application.add_handler(companion_conversation_handler)
    application.add_handler(booking_conversation_handler)
    application.add_handler(meds_conversation_handler)

    application.add_handler(doctor_reg_conversation_handler)
    application.add_handler(
        CallbackQueryHandler(admin_registration_action, pattern=r"^dregadm_(ok|no)_\d+$")
    )
    application.add_handler(
        CommandHandler("pending", pending_command, filters=PRIVATE_CHAT_ONLY)
    )

    application.add_handler(
        CallbackQueryHandler(main_menu_callback, pattern=MENU_PATTERN)
    )

    application.add_handler(
        CallbackQueryHandler(
            medical_browse_callback,
            pattern=r"^med_(page_\d+|spec_[a-z]+_\d+|back)$|^noop_page$",
        )
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text_handler)
    )

    logger.info(
        "Handlers registered: start, help, language, back_main, "
        "feedback_start/yes/no, survey_conversation, companion_conversation, "
        "booking_conversation, meds_conversation, med_menu, "
        "main_menu (%d callbacks), feedback_text, conv-reset(group -1), "
        "doctor_reg(hidden), dregadm, pending.",
        len(MENU_CALLBACKS),
    )


def build_application(platform: str = "bale") -> Application:
    """ساخت اپلیکیشن برای بله یا تلگرام.

    🆕 پشتیبانی دو-پلتفرمی: بله همیشه فعال است (توکن آن اجباری است)؛ تلگرام
    فقط وقتی فعال می‌شود که هم TELEGRAM_BOT_TOKEN و هم TELEGRAM_BRIDGE_URL در
    env تنظیم شده باشند (چون تلگرام از ایران فیلتر است و نیاز به پل خارجی دارد).
    """
    if platform == "bale":
        token = settings.bale_bot_token
        base_url = "https://tapi.bale.ai/bot"
        base_file_url = "https://tapi.bale.ai/file/bot"
    elif platform == "telegram":
        token = settings.telegram_bot_token
        base_url = settings.telegram_bridge_url or None
        base_file_url = settings.telegram_bridge_file_url or None
    else:
        raise RuntimeError(f"پلتفرم نامعتبر: {platform!r} (مقادیر مجاز: bale, telegram)")

    if not token or not token.strip():
        raise RuntimeError(
            f"توکن برای پلتفرم '{platform}' در env تنظیم نشده. "
            f"{'BALE_BOT_TOKEN' if platform == 'bale' else 'TELEGRAM_BOT_TOKEN'} را بررسی کنید."
        )

    async def _post_init(application: Application) -> None:
        runtime.bind_application(application)
        meds.schedule_all(application)
        logger.info("Post-init (%s): runtime bridge bound + med reminders scheduled.", platform)

    # 🆕 فایل persistence جدا برای هر پلتفرم تا داده‌ی کاربران بله و تلگرام قاطی نشود
    persistence_file = f"data/bot_persistence_{platform}.pkl"
    persistence = PicklePersistence(filepath=persistence_file)

    builder = ApplicationBuilder().token(token)
    if base_url:
        builder.base_url(base_url)
    if base_file_url:
        builder.base_file_url(base_file_url)
    builder.persistence(persistence)
    builder.post_init(_post_init)
    application = builder.build()

    _register_handlers(application)

    logger.info("Application built successfully for platform=%s.", platform)
    return application