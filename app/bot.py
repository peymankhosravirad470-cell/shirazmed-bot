# app/bot.py

from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from config import settings
from app.handlers.start import (
    start_handler,
    help_handler,
    select_language_handler,
    change_language_handler,
    back_to_main_handler,
)
from app.handlers.callbacks import main_menu_callback
from app.handlers.booking import booking_conversation_handler
from app.handlers.survey import survey_conversation_handler
from app.handlers.companion import companion_conversation_handler  # 🆕 اضافه شد

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# الگوهای callback
# ---------------------------------------------------------------------------

LANGUAGE_PATTERN = r"^lang_(fa|en|ar)$"
CHANGE_LANGUAGE_PATTERN = r"^change_language$"
BACK_TO_MAIN_PATTERN = r"^back_main$"

MENU_CALLBACKS: tuple[str, ...] = (
    "start_booking",    # دکمه رزرو نوبت
    "start_companion",  # 🆕 دکمه ثبت همراه بیمار
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
    "complaints_iranian",   # 🆕
    "complaints_foreign",   # 🆕
    "support",
    "start_survey",         # 🆕 دکمه شروع نظرسنجی
)

MENU_PATTERN = rf"^({'|'.join(MENU_CALLBACKS)})$"

PRIVATE_CHAT_ONLY = filters.ChatType.PRIVATE

USER_ERROR_MESSAGE = "خطایی رخ داد. لطفاً دوباره تلاش کنید."


# ---------------------------------------------------------------------------
# هندلر خطای سراسری
# ---------------------------------------------------------------------------

async def global_error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """هندلر خطای سراسری: لاگ کامل + تلاش برای اطلاع‌رسانی به کاربر."""
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


# ---------------------------------------------------------------------------
# ثبت هندلرها
# ---------------------------------------------------------------------------

def _register_handlers(application: Application) -> None:
    """ثبت همه handlerها روی اپلیکیشن.

    ترتیب ثبت مهم است:
    1) هندلر خطای سراسری
    2) دستورات پایه (start/help) — فقط در چت خصوصی
    3) زبان و بازگشت به منو
    4) ConversationHandlerها (قبل از main_menu_callback)
    5) main_menu_callback (پوشش همه دکمه‌های منو)
    """

    # 1) هندلر خطای سراسری
    application.add_error_handler(global_error_handler)

    # 2) دستورات پایه — فقط در چت خصوصی
    application.add_handler(
        CommandHandler("start", start_handler, filters=PRIVATE_CHAT_ONLY)
    )
    application.add_handler(
        CommandHandler("help", help_handler, filters=PRIVATE_CHAT_ONLY)
    )

    # 3) انتخاب/تغییر زبان و بازگشت به منوی اصلی
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

    # 4) ConversationHandlerها (باید قبل از main_menu_callback ثبت شوند)
    application.add_handler(survey_conversation_handler)
    application.add_handler(companion_conversation_handler)  # 🆕
    application.add_handler(booking_conversation_handler)

    # 5) همه دکمه‌های منو و زیرمنو
    application.add_handler(
        CallbackQueryHandler(main_menu_callback, pattern=MENU_PATTERN)
    )

    logger.info(
        "Handlers registered: start, help, language, back_main, "
        "survey_conversation, companion_conversation, booking_conversation, "
        "main_menu (%d callbacks).",
        len(MENU_CALLBACKS),
    )


# ---------------------------------------------------------------------------
# ساخت اپلیکیشن — حالا دو پلتفرمی: بله و تلگرام
# ---------------------------------------------------------------------------

def build_application(platform: str = "bale") -> Application:
    """ساخت اپلیکیشن برای بله یا تلگرام.

    Args:
        platform: "bale" (پیش‌فرض) یا "telegram".

    Raises:
        RuntimeError: اگر توکنِ پلتفرم مربوطه در env تنظیم نشده باشد،
            یا نام پلتفرم نامعتبر باشد.
    """
    token: Optional[str]
    base_url: Optional[str]
    base_file_url: Optional[str]

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

    builder = ApplicationBuilder().token(token)
    if base_url:
        builder.base_url(base_url)
    if base_file_url:
        builder.base_file_url(base_file_url)
    application = builder.build()

    _register_handlers(application)

    logger.info("Application built successfully for platform=%s.", platform)
    return application