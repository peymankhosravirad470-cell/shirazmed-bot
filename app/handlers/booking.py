# app/handlers/booking.py

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.locales import get_msg_btn
from app.services.booking import (
    add_appointment,
    cancel_appointment,
    get_available_times,
    get_next_14_days,
    is_time_available,
)
from app.services.payment import request_payment
from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ثابت‌ها
# ---------------------------------------------------------------------------

ASK_NAME, ASK_NATIONAL_CODE, SELECT_DOCTOR, SELECT_DATE, SELECT_TIME, CONFIRM_BOOKING = range(6)

SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en", "ar")
DEFAULT_LANG: str = "fa"

APPOINTMENT_AMOUNT: int = 100_000
PENDING_TIMEOUT_MINUTES: int = 15
PAYMENT_TIMEOUT_SECONDS: float = 15.0
NATIONAL_CODE_LENGTH: int = 10
MIN_NAME_LENGTH: int = 2

TEMP_DOCTORS: tuple[dict[str, str], ...] = (
    {"id": "doc_1", "name": "دکتر علی رضایی"},
    {"id": "doc_2", "name": "دکتر مریم احمدی"},
    {"id": "doc_3", "name": "دکتر حسین کریمی"},
)

MSG_BOOKING_CANCELLED = "فرآیند رزرو نوبت لغو شد."
MSG_PAYMENT_FAILED = (
    "خطا در ایجاد لینک پرداخت. نوبت شما لغو شد.\n"
    "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
)
MSG_SLOT_TAKEN = (
    "خطا در ثبت نوبت رخ داد.\n"
    "احتمالاً این ساعت همین الان توسط کاربر دیگری رزرو شده است.\n"
    "لطفاً دوباره از منو نوبت بگیرید."
)
MSG_ALREADY_CONFIRMED = "این نوبت قبلاً ثبت شده است."


# ---------------------------------------------------------------------------
# داده‌های رزرو (برای مدیریت متمرکز user_data)
# ---------------------------------------------------------------------------

@dataclass
class BookingData:
    """نگه‌دارنده داده‌های رزرو در طول گفتگو.

    به جای دسترسی مستقیم به user_data با کلیدهای پراکنده، از این
    dataclass استفاده می‌کنیم تا:
    - نام‌ها متمرکز و type-safe باشند.
    - پاکسازی ساده باشد.
    - افزودن فیلد جدید آسان باشد.
    """

    name: str = ""
    national_code: str = ""
    doctor_id: str = ""
    doctor_name: str = ""
    date: str = ""
    time: str = ""
    confirmed: bool = False

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE) -> "BookingData":
        return cls(
            name=context.user_data.get("booking_name", ""),
            national_code=context.user_data.get("booking_national_code", ""),
            doctor_id=context.user_data.get("booking_doctor_id", ""),
            doctor_name=context.user_data.get("booking_doctor_name", ""),
            date=context.user_data.get("booking_date", ""),
            time=context.user_data.get("booking_time", ""),
            confirmed=bool(context.user_data.get("booking_confirmed")),
        )

    def save_to(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data["booking_name"] = self.name
        context.user_data["booking_national_code"] = self.national_code
        context.user_data["booking_doctor_id"] = self.doctor_id
        context.user_data["booking_doctor_name"] = self.doctor_name
        context.user_data["booking_date"] = self.date
        context.user_data["booking_time"] = self.time
        if self.confirmed:
            context.user_data["booking_confirmed"] = True

    def clear_from(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        for key in (
            "booking_name",
            "booking_national_code",
            "booking_doctor_id",
            "booking_doctor_name",
            "booking_date",
            "booking_time",
            "booking_confirmed",
        ):
            context.user_data.pop(key, None)

    def is_complete(self) -> bool:
        return all(
            [self.name, self.national_code, self.doctor_id, self.date, self.time]
        )


# ---------------------------------------------------------------------------
# توابع کمکی
# ---------------------------------------------------------------------------

def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang", DEFAULT_LANG)
    if lang not in SUPPORTED_LANGS:
        return DEFAULT_LANG
    return lang


def _safe_btn(lang: str, key: str, default: str = "بازگشت") -> str:
    """دریافت امن برچسب دکمه از get_msg_btn با fallback."""
    try:
        value = get_msg_btn(lang, key)
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default
    except Exception as error:
        logger.warning("Error getting msg btn '%s' for lang '%s': %s", key, lang, error)
        return default


def _cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _safe_btn(lang, "btn_back", "بازگشت"),
                    callback_data="booking_cancel",
                )
            ]
        ]
    )


def _build_date_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد انتخاب تاریخ (۱۴ روز آینده) + بازگشت."""
    rows = [
        [InlineKeyboardButton(date_item, callback_data=f"booking_date_{date_item}")]
        for date_item in get_next_14_days()
    ]
    rows.append(
        [
            InlineKeyboardButton(
                _safe_btn(lang, "btn_back", "بازگشت"),
                callback_data="booking_cancel",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def _build_time_keyboard(lang: str, available_times: list[str]) -> InlineKeyboardMarkup:
    """کیبورد انتخاب ساعت + بازگشت."""
    rows = [
        [InlineKeyboardButton(slot, callback_data=f"booking_time_{slot}")]
        for slot in available_times
    ]
    rows.append(
        [
            InlineKeyboardButton(
                _safe_btn(lang, "btn_back", "بازگشت"),
                callback_data="booking_cancel",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def _build_doctor_keyboard() -> InlineKeyboardMarkup:
    """کیبورد انتخاب پزشک (بدون دکمه بازگشت چون در این مرحله لغو معنا ندارد)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    doctor["name"],
                    callback_data=f"booking_doctor_{doctor['id']}",
                )
            ]
            for doctor in TEMP_DOCTORS
        ]
    )


def _build_summary(data: BookingData, lang: str) -> str:
    """ساخت متن خلاصه نوبت برای تأیید."""
    return "\n".join(
        [
            "خلاصه نوبت:",
            f"نام بیمار: {data.name}",
            f"کد ملی: {data.national_code}",
            f"پزشک: {data.doctor_name}",
            f"تاریخ: {data.date}",
            f"ساعت: {data.time}",
            f"مبلغ: {APPOINTMENT_AMOUNT:,} تومان",
            "",
            "آیا از ثبت این نوبت مطمئن هستید؟",
        ]
    )


def _build_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "تأیید و پرداخت", callback_data="booking_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    _safe_btn(lang, "btn_back", "بازگشت"),
                    callback_data="booking_cancel",
                )
            ],
        ]
    )


def _build_callback_url(context: ContextTypes.DEFAULT_TYPE) -> str:
    """ساخت callback_url قابل تنظیم (Bale/Telegram) از settings."""
    bot_username = getattr(context.bot, "username", None)
    if not bot_username:
        bot_username = getattr(settings, "BOT_USERNAME", "ShirazMedBot")
    base = getattr(settings, "PAYMENT_CALLBACK_BASE", "https://ble.ir")
    return f"{base}/{bot_username}"


async def _request_payment_safe(
    *,
    user_id: int,
    amount: int,
    description: str,
    callback_url: str,
) -> dict[str, Any]:
    """فراخوانی امن request_payment در thread جدا با timeout.

    با استفاده از asyncio.to_thread از بلاک شدن event loop جلوگیری
    می‌کند و با asyncio.wait_for زمان انتظار را محدود می‌کند.
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                request_payment,
                user_id=user_id,
                amount=amount,
                description=description,
                callback_url=callback_url,
            ),
            timeout=PAYMENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as error:
        raise ValueError("درگاه پرداخت پاسخ نداد (timeout)") from error

    if not isinstance(result, dict):
        raise ValueError("پاسخ درگاه پرداخت نامعتبر است")

    return result


async def _safe_answer(query) -> None:
    """پاسخ امن به callback_query (جلوگیری از BadRequest)."""
    try:
        await query.answer()
    except Exception as error:
        logger.debug("Failed to answer callback: %s", error)


# ---------------------------------------------------------------------------
# مراحل گفتگو
# ---------------------------------------------------------------------------

async def start_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """شروع فرآیند رزرو نوبت و دریافت نام بیمار."""
    if update.effective_chat is None:
        return ConversationHandler.END

    if update.callback_query is not None:
        await _safe_answer(update.callback_query)

    lang = _get_lang(context)

    # پاکسازی داده‌های قبلی
    BookingData().clear_from(context)

    prompt = "لطفاً نام و نام خانوادگی بیمار را وارد کنید:"
    keyboard = _cancel_keyboard(lang)

    if update.message is not None:
        await update.message.reply_text(prompt, reply_markup=keyboard)
    elif update.callback_query is not None:
        await update.callback_query.edit_message_text(prompt, reply_markup=keyboard)
    else:
        return ConversationHandler.END

    return ASK_NAME


async def receive_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت نام بیمار و درخواست کد ملی."""
    if update.message is None or update.message.text is None:
        return ASK_NAME

    lang = _get_lang(context)
    name = update.message.text.strip()

    if len(name) < MIN_NAME_LENGTH:
        await update.message.reply_text(
            "نام وارد شده خیلی کوتاه است.\nلطفاً نام و نام خانوادگی کامل وارد کنید:",
            reply_markup=_cancel_keyboard(lang),
        )
        return ASK_NAME

    data = BookingData.from_context(context)
    data.name = name
    data.save_to(context)

    await update.message.reply_text(
        "لطفاً کد ملی ۱۰ رقمی بیمار را وارد کنید:",
        reply_markup=_cancel_keyboard(lang),
    )
    return ASK_NATIONAL_CODE


async def receive_national_code(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت و اعتبارسنجی کد ملی ۱۰ رقمی."""
    if update.message is None or update.message.text is None:
        return ASK_NATIONAL_CODE

    lang = _get_lang(context)
    national_code = update.message.text.strip()

    if not national_code.isdigit() or len(national_code) != NATIONAL_CODE_LENGTH:
        await update.message.reply_text(
            f"کد ملی وارد شده معتبر نیست.\nلطفاً یک کد ملی {NATIONAL_CODE_LENGTH} رقمی وارد کنید:",
            reply_markup=_cancel_keyboard(lang),
        )
        return ASK_NATIONAL_CODE

    data = BookingData.from_context(context)
    data.national_code = national_code
    data.save_to(context)

    await update.message.reply_text(
        "لطفاً پزشک مورد نظر را انتخاب کنید:",
        reply_markup=_build_doctor_keyboard(),
    )
    return SELECT_DOCTOR


async def select_doctor(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت پزشک انتخاب‌شده و نمایش تاریخ‌های ۱۴ روز آینده."""
    query = update.callback_query

    if query is None:
        return SELECT_DOCTOR

    await _safe_answer(query)

    lang = _get_lang(context)
    doctor_id = query.data.replace("booking_doctor_", "")
    doctor = next(
        (item for item in TEMP_DOCTORS if item["id"] == doctor_id), None
    )

    if doctor is None:
        await query.edit_message_text(
            "پزشک انتخاب‌شده معتبر نیست. لطفاً دوباره تلاش کنید.",
            reply_markup=_cancel_keyboard(lang),
        )
        return SELECT_DOCTOR

    data = BookingData.from_context(context)
    data.doctor_id = doctor["id"]
    data.doctor_name = doctor["name"]
    data.save_to(context)

    await query.edit_message_text(
        "لطفاً تاریخ نوبت را انتخاب کنید:",
        reply_markup=_build_date_keyboard(lang),
    )
    return SELECT_DATE


async def select_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت تاریخ انتخاب‌شده و نمایش ساعت‌های خالی."""
    query = update.callback_query

    if query is None:
        return SELECT_DATE

    await _safe_answer(query)

    lang = _get_lang(context)
    date = query.data.replace("booking_date_", "")
    available_times = get_available_times(date)

    if not available_times:
        await query.edit_message_text(
            "برای این تاریخ ساعت خالی وجود ندارد.\nلطفاً تاریخ دیگری انتخاب کنید:",
            reply_markup=_build_date_keyboard(lang),
        )
        return SELECT_DATE

    data = BookingData.from_context(context)
    data.date = date
    data.save_to(context)

    await query.edit_message_text(
        "لطفاً ساعت نوبت را انتخاب کنید:",
        reply_markup=_build_time_keyboard(lang, available_times),
    )
    return SELECT_TIME


async def select_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت ساعت انتخاب‌شده و نمایش خلاصه نوبت برای تأیید."""
    query = update.callback_query

    if query is None:
        return SELECT_TIME

    await _safe_answer(query)

    lang = _get_lang(context)
    slot = query.data.replace("booking_time_", "")
    data = BookingData.from_context(context)

    if not is_time_available(data.date, slot):
        available_times = get_available_times(data.date)

        if not available_times:
            await query.edit_message_text(
                "این ساعت دیگر در دسترس نیست و ساعت خالی دیگری هم برای این تاریخ وجود ندارد.\n"
                "لطفاً تاریخ دیگری انتخاب کنید:",
                reply_markup=_build_date_keyboard(lang),
            )
            return SELECT_DATE

        await query.edit_message_text(
            "این ساعت دیگر در دسترس نیست.\nلطفاً ساعت دیگری انتخاب کنید:",
            reply_markup=_build_time_keyboard(lang, available_times),
        )
        return SELECT_TIME

    data.time = slot
    data.save_to(context)

    await query.edit_message_text(
        _build_summary(data, lang),
        reply_markup=_build_confirm_keyboard(lang),
    )
    return CONFIRM_BOOKING


async def confirm_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """ثبت نوبت، ایجاد لینک پرداخت و پایان گفتگو."""
    query = update.callback_query

    if query is None:
        return CONFIRM_BOOKING

    await _safe_answer(query)

    data = BookingData.from_context(context)

    if data.confirmed:
        await query.edit_message_text(MSG_ALREADY_CONFIRMED, reply_markup=None)
        return ConversationHandler.END

    if not data.is_complete():
        await query.edit_message_text(
            "اطلاعات نوبت ناقص است. لطفاً دوباره از منو نوبت بگیرید.",
            reply_markup=None,
        )
        data.clear_from(context)
        return ConversationHandler.END

    user = update.effective_user
    user_id = user.id if user else 0

    appointment = {
        "user_id": user_id,
        "full_name": data.name,
        "national_code": data.national_code,
        "doctor_id": data.doctor_id,
        "doctor_name": data.doctor_name,
        "date": data.date,
        "time": data.time,
        "amount": APPOINTMENT_AMOUNT,
        "status": "pending",
        "expires_at": (
            datetime.now() + timedelta(minutes=PENDING_TIMEOUT_MINUTES)
        ).isoformat(),
    }

    if not add_appointment(appointment):
        await query.edit_message_text(MSG_SLOT_TAKEN, reply_markup=None)
        data.clear_from(context)
        return ConversationHandler.END

    data.confirmed = True
    data.save_to(context)

    try:
        callback_url = _build_callback_url(context)
        payment_response = await _request_payment_safe(
            user_id=user_id,
            amount=APPOINTMENT_AMOUNT,
            description=(
                f"نوبت {data.doctor_name} - {data.date} {data.time}"
            ),
            callback_url=callback_url,
        )

        if not payment_response.get("success"):
            raise ValueError(
                payment_response.get("error", "خطای نامشخص در درگاه پرداخت")
            )

        payment_link = payment_response.get("url")
        if not payment_link or not isinstance(payment_link, str):
            raise ValueError("لینک پرداخت خالی یا نامعتبر است")

        await query.edit_message_text(
            "\n".join(
                [
                    "نوبت شما با موفقیت ثبت شد.",
                    "",
                    "برای تکمیل رزرو، لطفاً پرداخت را انجام دهید:",
                    payment_link,
                ]
            ),
            reply_markup=None,
        )

    except Exception as error:
        logger.error("Error creating payment link: %s", error)

        try:
            cancel_appointment(
                date=data.date,
                time=data.time,
                user_id=user_id,
            )
        except Exception as cancel_error:
            logger.error("Error cancelling pending appointment: %s", cancel_error)

        await query.edit_message_text(MSG_PAYMENT_FAILED, reply_markup=None)

    data.clear_from(context)
    return ConversationHandler.END


async def cancel_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """لغو فرآیند رزرو نوبت."""
    query = update.callback_query

    if query is not None:
        await _safe_answer(query)

        try:
            await query.edit_message_text(MSG_BOOKING_CANCELLED, reply_markup=None)
        except Exception as error:
            logger.debug("Error editing cancel message: %s", error)

        BookingData().clear_from(context)
        return ConversationHandler.END

    if update.message is not None:
        await update.message.reply_text(MSG_BOOKING_CANCELLED, reply_markup=None)
        BookingData().clear_from(context)
        return ConversationHandler.END

    BookingData().clear_from(context)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ConversationHandler
# ---------------------------------------------------------------------------

booking_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_booking, pattern=r"^start_booking$")
    ],
    states={
        ASK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)
        ],
        ASK_NATIONAL_CODE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_national_code
            )
        ],
        SELECT_DOCTOR: [
            CallbackQueryHandler(
                select_doctor,
                pattern=r"^booking_doctor_[a-zA-Z0-9_]+$",
            )
        ],
        SELECT_DATE: [
            CallbackQueryHandler(
                select_date,
                pattern=r"^booking_date_\d{4}-\d{2}-\d{2}$",
            )
        ],
        SELECT_TIME: [
            CallbackQueryHandler(
                select_time,
                pattern=r"^booking_time_\d{2}:\d{2}$",
            )
        ],
        CONFIRM_BOOKING: [
            CallbackQueryHandler(
                confirm_booking,
                pattern=r"^booking_confirm$",
            )
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_booking, pattern=r"^booking_cancel$")
    ],
    allow_reentry=True,
)