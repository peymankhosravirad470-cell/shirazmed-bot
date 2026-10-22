# app/handlers/booking.py

from __future__ import annotations

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from app.services.booking import (
    add_appointment,
    get_available_times,
    get_next_14_days,
    is_time_available,
)
from app.services.payment import create_payment_link
from app.locales import get_msg_btn


# مراحل گفتگو
ASK_NAME, ASK_NATIONAL_CODE, SELECT_DOCTOR, SELECT_DATE, SELECT_TIME, CONFIRM_BOOKING = range(6)

# وضعیت موقت پزشکان
TEMP_DOCTORS = [
    {"id": "doc_1", "name": "دکتر علی رضایی"},
    {"id": "doc_2", "name": "دکتر مریم احمدی"},
    {"id": "doc_3", "name": "دکتر حسین کریمی"},
]

# مبلغ ثابت نوبت
APPOINTMENT_AMOUNT = 100000

# کلیدهای user_data مربوط به رزرو (برای پاکسازی در شروع)
_BOOKING_KEYS = (
    "booking_name",
    "booking_national_code",
    "booking_doctor_id",
    "booking_doctor_name",
    "booking_date",
    "booking_time",
)


def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """دریافت زبان کاربر با مقدار پیش‌فرض فارسی."""
    lang = context.user_data.get("lang", "fa")
    if lang not in ("fa", "en", "ar"):
        return "fa"
    return lang


def _safe_btn(lang: str, key: str, default: str = "بازگشت") -> str:
    """دریافت امن یک دکمه از get_msg_btn با fallback."""
    try:
        value = get_msg_btn(lang, key)
        if value is None:
            return default
        return str(value)
    except Exception as error:
        print(f"Error getting msg btn '{key}' for lang '{lang}': {error}")
        return default


def _cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد لغو گفتگوی نوبت‌دهی."""
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


def _dates_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد انتخاب تاریخ (۱۴ روز آینده) + دکمه بازگشت."""
    rows = [
        [
            InlineKeyboardButton(
                date_item,
                callback_data=f"booking_date_{date_item}",
            )
        ]
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


def _times_keyboard(lang: str, available_times: list[str]) -> InlineKeyboardMarkup:
    """کیبورد انتخاب ساعت + دکمه بازگشت."""
    rows = [
        [
            InlineKeyboardButton(
                slot,
                callback_data=f"booking_time_{slot}",
            )
        ]
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


def _clear_booking_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """پاکسازی داده‌های رزرو از user_data."""
    for key in _BOOKING_KEYS:
        context.user_data.pop(key, None)


async def start_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """شروع فرآیند رزرو نوبت و دریافت نام بیمار."""
    if update.effective_chat is None:
        return ConversationHandler.END

    # اگر ورودی از callback است
    if update.callback_query is not None:
        try:
            await update.callback_query.answer()
        except Exception:
            pass

    lang = _get_lang(context)

    # پاکسازی داده‌های قبلی برای جلوگیری از قاطی شدن
    _clear_booking_data(context)

    if update.message is not None:
        await update.message.reply_text(
            "لطفاً نام و نام خانوادگی بیمار را وارد کنید:",
            reply_markup=_cancel_keyboard(lang),
        )
    elif update.callback_query is not None:
        await update.callback_query.edit_message_text(
            "لطفاً نام و نام خانوادگی بیمار را وارد کنید:",
            reply_markup=_cancel_keyboard(lang),
        )
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

    if len(name) < 2:
        await update.message.reply_text(
            "نام وارد شده خیلی کوتاه است.\nلطفاً نام و نام خانوادگی کامل وارد کنید:",
            reply_markup=_cancel_keyboard(lang),
        )
        return ASK_NAME

    context.user_data["booking_name"] = name
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

    if not national_code.isdigit() or len(national_code) != 10:
        await update.message.reply_text(
            "کد ملی وارد شده معتبر نیست.\nلطفاً یک کد ملی ۱۰ رقمی وارد کنید:",
            reply_markup=_cancel_keyboard(lang),
        )
        return ASK_NATIONAL_CODE

    context.user_data["booking_national_code"] = national_code

    keyboard = InlineKeyboardMarkup(
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
    await update.message.reply_text(
        "لطفاً پزشک مورد نظر را انتخاب کنید:",
        reply_markup=keyboard,
    )
    return SELECT_DOCTOR


async def select_doctor(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت پزشک انتخاب‌شده و نمایش تاریخ‌های ۱۴ روز آینده."""
    query = update.callback_query

    if query is None:
        return SELECT_DOCTOR

    await query.answer()

    lang = _get_lang(context)
    doctor_id = query.data.replace("booking_doctor_", "")
    doctor = next((item for item in TEMP_DOCTORS if item["id"] == doctor_id), None)

    if doctor is None:
        await query.edit_message_text(
            "پزشک انتخاب‌شده معتبر نیست. لطفاً دوباره تلاش کنید.",
            reply_markup=_cancel_keyboard(lang),
        )
        return SELECT_DOCTOR

    context.user_data["booking_doctor_id"] = doctor["id"]
    context.user_data["booking_doctor_name"] = doctor["name"]

    await query.edit_message_text(
        "لطفاً تاریخ نوبت را انتخاب کنید:",
        reply_markup=_dates_keyboard(lang),
    )
    return SELECT_DATE


async def select_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت تاریخ انتخاب‌شده و نمایش ساعت‌های خالی."""
    query = update.callback_query

    if query is None:
        return SELECT_DATE

    await query.answer()

    lang = _get_lang(context)
    date = query.data.replace("booking_date_", "")
    available_times = get_available_times(date)

    if not available_times:
        # کیبورد تاریخ را دوباره می‌فرستیم تا کاربر گیر نکند
        await query.edit_message_text(
            "برای این تاریخ ساعت خالی وجود ندارد.\nلطفاً تاریخ دیگری انتخاب کنید:",
            reply_markup=_dates_keyboard(lang),
        )
        return SELECT_DATE

    context.user_data["booking_date"] = date

    await query.edit_message_text(
        "لطفاً ساعت نوبت را انتخاب کنید:",
        reply_markup=_times_keyboard(lang, available_times),
    )
    return SELECT_TIME


async def select_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """دریافت ساعت انتخاب‌شده و نمایش خلاصه نوبت برای تأیید."""
    query = update.callback_query

    if query is None:
        return SELECT_TIME

    await query.answer()

    lang = _get_lang(context)
    slot = query.data.replace("booking_time_", "")
    date = context.user_data.get("booking_date", "")

    if not is_time_available(date, slot):
        # شاید کاربر دیگری همان لحظه رزرو کرده باشد
        available_times = get_available_times(date)

        if not available_times:
            await query.edit_message_text(
                "این ساعت دیگر در دسترس نیست و ساعت خالی دیگری هم برای این تاریخ وجود ندارد.\n"
                "لطفاً تاریخ دیگری انتخاب کنید:",
                reply_markup=_dates_keyboard(lang),
            )
            return SELECT_DATE

        await query.edit_message_text(
            "این ساعت دیگر در دسترس نیست.\nلطفاً ساعت دیگری انتخاب کنید:",
            reply_markup=_times_keyboard(lang, available_times),
        )
        return SELECT_TIME

    context.user_data["booking_time"] = slot

    summary = "\n".join(
        [
            "خلاصه نوبت:",
            f"نام بیمار: {context.user_data.get('booking_name', '')}",
            f"کد ملی: {context.user_data.get('booking_national_code', '')}",
            f"پزشک: {context.user_data.get('booking_doctor_name', '')}",
            f"تاریخ: {date}",
            f"ساعت: {slot}",
            f"مبلغ: {APPOINTMENT_AMOUNT} تومان",
            "",
            "آیا از ثبت این نوبت مطمئن هستید؟",
        ]
    )

    keyboard = InlineKeyboardMarkup(
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

    await query.edit_message_text(summary, reply_markup=keyboard)
    return CONFIRM_BOOKING


async def confirm_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """ثبت نوبت، ایجاد لینک پرداخت و پایان گفتگو."""
    query = update.callback_query

    if query is None:
        return CONFIRM_BOOKING

    await query.answer()

    lang = _get_lang(context)
    user = update.effective_user

    appointment = {
        "user_id": user.id if user else None,
        "full_name": context.user_data.get("booking_name", ""),
        "national_code": context.user_data.get("booking_national_code", ""),
        "doctor_id": context.user_data.get("booking_doctor_id", ""),
        "doctor_name": context.user_data.get("booking_doctor_name", ""),
        "date": context.user_data.get("booking_date", ""),
        "time": context.user_data.get("booking_time", ""),
        "amount": APPOINTMENT_AMOUNT,
        "status": "pending",
    }

    saved = add_appointment(appointment)

    if not saved:
        # ممکن است اسلات همین لحظه توسط کاربر دیگری رزرو شده باشد
        await query.edit_message_text(
            "خطا در ثبت نوبت رخ داد.\n"
            "احتمالاً این ساعت همین الان توسط کاربر دیگری رزرو شده است.\n"
            "لطفاً دوباره از منو نوبت بگیرید.",
            reply_markup=None,
        )
        _clear_booking_data(context)
        return ConversationHandler.END

    try:
        payment_link = create_payment_link(
            user_id=user.id if user else 0,
            amount=APPOINTMENT_AMOUNT,
            description=(
                f"نوبت {appointment['doctor_name']} - "
                f"{appointment['date']} {appointment['time']}"
            ),
        )

        if not payment_link:
            raise ValueError("empty payment link")

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
        print(f"Error creating payment link: {error}")
        await query.edit_message_text(
            "نوبت ثبت شد، اما ایجاد لینک پرداخت با خطا مواجه شد.\n"
            "لطفاً بعداً با پشتیبانی تماس بگیرید.",
            reply_markup=None,
        )

    _clear_booking_data(context)
    return ConversationHandler.END


async def cancel_booking(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """لغو فرآیند رزرو نوبت."""
    query = update.callback_query

    if query is not None:
        try:
            await query.answer()
        except Exception:
            pass

        try:
            await query.edit_message_text(
                "فرآیند رزرو نوبت لغو شد.",
                reply_markup=None,
            )
        except Exception as error:
            print(f"Error editing cancel message: {error}")

        _clear_booking_data(context)
        return ConversationHandler.END

    if update.message is not None:
        await update.message.reply_text(
            "فرآیند رزرو نوبت لغو شد.",
            reply_markup=None,
        )
        _clear_booking_data(context)
        return ConversationHandler.END

    _clear_booking_data(context)
    return ConversationHandler.END


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