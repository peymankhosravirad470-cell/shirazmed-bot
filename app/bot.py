# app/bot.py

from __future__ import annotations

import asyncio
import logging
import os
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
from config import DATA_DIR, settings
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
from app.handlers.callbacks import apt_cancel_callback  # 🆕 آیتم ۵: لغو نوبت توسط کاربر
from app.handlers import admin_panel  # 🆕 مأموریت آیتم‌های ۱۷/۱۸: پنل ادمین
from app.handlers import advisor  # 🆕 مأموریت مکمل: مشاور سلامت
from app.handlers import search as search_handler  # 🆕 مأموریت مکمل: جست‌وجوی هوشمند

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# 🚀 فیکس کندی (بخش ۳): httpx به‌ازای «هر» فراخوانی API بله/تلگرام یک خط لاگ INFO
# می‌نویسد (answerCallbackQuery، editMessageText، sendMessage و…) — یعنی ۳+ خط
# اضافه روی stdout کانتینر در هر کلیک کاربر. سطح آن به WARNING می‌رود تا فقط
# خطاهای واقعی شبکه لاگ شوند؛ لاگ‌های خود ربات (app.*) سر جای خود می‌مانند.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
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
    "ai_assistant",  # 🆕 مأموریت آیتم ۱: دستیار هوشمند اختصاصی
    # 🆕 مأموریت مکمل: جست‌وجوی هوشمند + مشاور سلامت + دسته‌بندی‌های منوی جدید
    "search",
    "advisor",
    "cat_medical",
    "cat_travel",
    "cat_tourism",
    "cat_support",
    "cat_me",
    "cat_contact",
)

MENU_PATTERN = rf"^({'|'.join(MENU_CALLBACKS)})$"

_MENU_NO_ENTRY = [c for c in MENU_CALLBACKS if c not in ("start_booking", "start_companion", "start_survey")]
# 🧹 ممیزی: entry-pointهای گفتگوها هم باید reset شوند وگرنه «دو گفتگوی فعال
# هم‌زمان» ممکن می‌شود: کاربر وسط گفتگوی همراه، «نوبت بگیر» را می‌زند؛ گفتگوی
# رزرو شروع می‌شود ولی گفتگوی قبلی هم فعال می‌ماند و متن بعدی او را «گفتگوی
# قدیمی» می‌بلعد (اولین ConversationHandler ثبت‌شده برنده می‌شود).
_RESET_EXTRA = (
    "back_main", "change_language", "start_feedback", "feedback_yes", "feedback_no",
    "med_home", "med_list", "med_del", "noop_page",
    "start_booking", "start_companion", "start_survey", "med_add",
    "srchback",  # 🆕 مأموریت مکمل: بازگشت به حالت جست‌وجو هم گفتگوهای نیمه‌کاره را ریست می‌کند
)
RESET_CONV_PATTERN = rf"^({'|'.join(_MENU_NO_ENTRY + list(_RESET_EXTRA))}|med_del_\d+|med_page_\d+|med_spec_[a-z]+_\d+|med_back|lang_(fa|en|ar))$"

# ⚠️ ثابت مرده — مسیر واقعی در build_application با DATA_DIR ساخته می‌شود.
# (برای جلوگیری از گمراهی نگه‌داری می‌شود و در نسخه‌ی بعدی حذف خواهد شد)
PERSISTENCE_FILE = "data/bot_persistence.pkl"

PRIVATE_CHAT_ONLY = filters.ChatType.PRIVATE

# 🎨 متن خطای کاربر — سه‌زبانه و گرم (قبلاً فقط فارسی و خشک بود).
# زبان از user_data خوانده می‌شود؛ اگر در دسترس نبود، نسخه سه‌خطی ترکیبی.
_USER_ERROR_T = {
    "fa": "😔 یه خطای غیرمنتظره پیش اومد. لطفاً چند لحظه بعد دوباره امتحان کنید — اگه تکرار شد، ما رو در جریان بذارید 💙",
    "en": "😔 Something unexpected came up. Please try again in a moment — if it repeats, let us know 💙",
    "ar": "😔 حدث خطأ غير متوقع. يرجى المحاولة بعد قليل — وإذا تكرر الأمر، فأخبرنا بذلك 💙",
}
_USER_ERROR_FALLBACK = (
    "😔 خطایی پیش اومد؛ لطفاً چند لحظه بعد دوباره امتحان کنید 💙\n"
    "Something went wrong; please try again in a moment 💙\n"
    "حدث خطأ ما؛ يرجى المحاولة بعد قليل 💙"
)


def _user_error_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        lang = (context.user_data or {}).get("lang")
        if lang in _USER_ERROR_T:
            return _USER_ERROR_T[lang]
    except Exception:
        pass
    return _USER_ERROR_FALLBACK


async def reset_conversations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            return
        key = (chat.id, user.id)
        # 🧹 Bug2-hardening: پرچم کهنه‌ی «در انتظار ثبت نظر» هم پاک شود؛ وگرنه
        # بعد از ریست، اولین متن کاربر بی‌اجازه به‌عنوان نظر برای ادمین می‌رفت.
        try:
            context.user_data["awaiting_feedback"] = False
        except Exception:
            pass
        # 🆕 مأموریت آیتم ۱: پرچم گفتگوی دستیار هوشمند هم با هر ناوبری پاک شود
        # تا متن بعدی کاربر ناخواسته به AI نرود (الگوی awaiting_feedback).
        try:
            context.user_data["ai_chat"] = False
        except Exception:
            pass
        # 🆕 مأموریت مکمل: پرچم‌های جست‌وجوی هوشمند و مشاور سلامت هم با هر
        # ناوبری پاک شوند (حریم خصوصی: درخواست موقعیت معلق هم لغو می‌شود).
        try:
            context.user_data["awaiting_search"] = False
            context.user_data.pop("advisor_state", None)
            context.user_data.pop("advisor_awaiting_location", None)
        except Exception:
            pass
        # 🧹 تسک ۳: قبل از هر ناوبری، پرامپت‌های ردیابی‌شده‌ی گفتگوها (نام/
        # کد ملی/ساعت دارو/…) و تکه‌های لیست قبلی حذف شوند تا «پیام قدیمی
        # بالای منوی جدید» نماند. شکست پاک‌سازی نباید مسیر را بشکند.
        try:
            from app.handlers import chunks as chunk_tracker
            await chunk_tracker.cleanup(context, chat.id)
        except Exception:
            pass
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
                _user_error_text(context),
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
                text=_user_error_text(context),
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
    # 🧹 ممیزی: ورود مخفی ثبت‌نام پزشک هم باید گفتگوهای نیمه‌کاره را پاک کند
    # تا با «دو گفتگوی فعال» مواجه نشویم (/start docreg از طریق هندلر start بالا پوشش داده می‌شود).
    application.add_handler(
        CommandHandler(("doctor", "docreg"), reset_conversations_callback),
        group=-1,
    )

    # 🩺 ترتیب حیاتی (ممیزی): فرم مخفی ثبت‌نام پزشک «قبل از» هندلر عمومی /start
    # ثبت می‌شود. قبلاً CommandHandler("start", start_handler) زودتر ثبت شده بود و
    # چون در یک گروه اولین handler برنده است، ورودی لینک اختصاصی
    # (?start=docreg → /start docreg) «هرگز» اجرا نمی‌شد و کاربر پیام خالی می‌گرفت.
    # entry-pointهای این گفتگو فقط روی /start docreg (با Regex) و /doctor و /docreg
    # واکنش دارند؛ /start ساده از رویش رد می‌شود و به start_handler می‌رسد.
    application.add_handler(doctor_reg_conversation_handler)
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

    application.add_handler(
        CallbackQueryHandler(admin_registration_action, pattern=r"^dregadm_(ok|no)_\d+$")
    )
    application.add_handler(
        CommandHandler("pending", pending_command, filters=PRIVATE_CHAT_ONLY)
    )

    application.add_handler(
        CallbackQueryHandler(main_menu_callback, pattern=MENU_PATTERN)
    )

    # 🆕 مأموریت مکمل: مشاور سلامت + جست‌وجوی هوشمند (الگوهای مستقل، بدون تداخل با MENU_PATTERN)
    application.add_handler(
        CallbackQueryHandler(advisor.advisor_router, pattern=advisor.ADVISOR_CB_PATTERN)
    )
    application.add_handler(
        CallbackQueryHandler(search_handler.search_go_callback, pattern=r"^srchgo_")
    )
    application.add_handler(
        CallbackQueryHandler(search_handler.search_back_callback, pattern=r"^srchback$")
    )
    # 🆕 مأموریت مکمل: موقعیت مکانی — فقط وقتی کاربر در جریان مشاور سلامت با
    # دکمهٔ صریح رضایت داده باشد پردازش می‌شود (handle_shared_location خودش بررسی می‌کند).
    application.add_handler(MessageHandler(filters.LOCATION, advisor.handle_shared_location))

    # 🆕 مأموریت آیتم‌های ۵/۱۲/۱۹: لغو نوبتِ pending توسط کاربر + جزئیات بسته
    # (الگوی main_menu_callback؛ جدا از MENU_PATTERN تا callback_dataهای پارامتری کار کنند)
    application.add_handler(
        CallbackQueryHandler(apt_cancel_callback, pattern=r"^aptcancel_.+")
    )
    application.add_handler(
        CallbackQueryHandler(main_menu_callback, pattern=r"^pkg_[a-z0-9_]+$")
    )

    # 🆕 مأموریت آیتم‌های ۱۷/۱۸: پنل مدیریت (/admin /stats /bookings /referrals)
    application.add_handler(
        CommandHandler(("stats", "bookings", "referrals", "admin"), admin_panel.dispatch_admin_command, filters=PRIVATE_CHAT_ONLY)
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
        # 🆕 مأموریت آیتم ۱۴: بازیابی یادآورهای نوبت پس از ری‌استارت (الگوی meds)
        try:
            from app.services import apt_reminders
            apt_reminders.reschedule_from_disk(application)
        except Exception as reminder_error:
            logger.warning("apt reminders restore failed: %s", reminder_error)
        logger.info("Post-init (%s): runtime bridge bound + med reminders scheduled.", platform)

    # 🆕 پل persistence جدا برای هر پلتفرم تا داده‌ی کاربران بله و تلگرام قاطی نشود
    # 🆕 ممیزی (بخش J): فایل persistence در ریشه‌ی DATA_DIR (دیسک پایدار) ذخیره می‌شود
    persistence_file = os.path.join(DATA_DIR, f"bot_persistence_{platform}.pkl")
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