# app/handlers/booking.py

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
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
from app.services import doctor_loader
from app.services.booking import (
    _now,
    add_appointment,
    calculate_commission,
    cancel_appointment,
    format_jalali,
    get_available_times,
    get_next_14_days_display,
    is_time_available,
)
from app.services.payment import request_payment
from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ثابت‌ها
# ---------------------------------------------------------------------------

ASK_NAME, ASK_NATIONAL_CODE, SELECT_SPEC, SELECT_DOCTOR, SELECT_DATE, SELECT_TIME, CONFIRM_BOOKING = range(7)

SUPPORTED_LANGS: tuple[str, ...] = ("fa", "en", "ar")
DEFAULT_LANG: str = "fa"

APPOINTMENT_AMOUNT: int = 100_000
PENDING_TIMEOUT_MINUTES: int = 15
PAYMENT_TIMEOUT_SECONDS: float = 15.0
NATIONAL_CODE_LENGTH: int = 10
MIN_NAME_LENGTH: int = 2

# صفحه‌بندی
SPEC_PER_PAGE: int = 8     # تخصص در هر صفحه
DOC_PER_PAGE: int = 6      # پزشک در هر صفحه
DATE_PER_PAGE: int = 7     # تاریخ در هر صفحه (۲ صفحه)

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
# داده‌های رزرو
# ---------------------------------------------------------------------------

@dataclass
class BookingData:
    name: str = ""
    national_code: str = ""
    spec_key: str = ""
    doctor_key: str = ""       # مثل cardio:doc_001
    doctor_id: str = ""        # مثل doc_001
    doctor_name: str = ""
    date: str = ""             # ISO میلادی (2026-10-25)
    time: str = ""
    confirmed: bool = False

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE) -> "BookingData":
        return cls(
            name=context.user_data.get("booking_name", ""),
            national_code=context.user_data.get("booking_national_code", ""),
            spec_key=context.user_data.get("booking_spec_key", ""),
            doctor_key=context.user_data.get("booking_doctor_key", ""),
            doctor_id=context.user_data.get("booking_doctor_id", ""),
            doctor_name=context.user_data.get("booking_doctor_name", ""),
            date=context.user_data.get("booking_date", ""),
            time=context.user_data.get("booking_time", ""),
            confirmed=bool(context.user_data.get("booking_confirmed")),
        )

    def save_to(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data["booking_name"] = self.name
        context.user_data["booking_national_code"] = self.national_code
        context.user_data["booking_spec_key"] = self.spec_key
        context.user_data["booking_doctor_key"] = self.doctor_key
        context.user_data["booking_doctor_id"] = self.doctor_id
        context.user_data["booking_doctor_name"] = self.doctor_name
        context.user_data["booking_date"] = self.date
        context.user_data["booking_time"] = self.time
        if self.confirmed:
            context.user_data["booking_confirmed"] = True

    def clear_from(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        for key in (
            "booking_name", "booking_national_code", "booking_spec_key",
            "booking_doctor_key", "booking_doctor_id", "booking_doctor_name",
            "booking_date", "booking_time", "booking_confirmed",
        ):
            context.user_data.pop(key, None)

    def is_complete(self) -> bool:
        return all([self.name, self.national_code, self.doctor_key, self.date, self.time])


# ---------------------------------------------------------------------------
# توابع کمکی
# ---------------------------------------------------------------------------

def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang", DEFAULT_LANG)
    if lang not in SUPPORTED_LANGS:
        return DEFAULT_LANG
    return lang


def _safe_btn(lang: str, key: str, default: str = "بازگشت") -> str:
    try:
        value = get_msg_btn(lang, key)
        if value is None: return default
        text = str(value).strip()
        return text if text else default
    except Exception:
        return default


def _cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(_safe_btn(lang, "btn_back", "بازگشت"), callback_data="booking_cancel")]])


def _build_specialty_keyboard(page: int) -> InlineKeyboardMarkup:
    """کیبورد صفحه‌بندی‌شده‌ی تخصص‌ها — از ۱۱۴ پزشک واقعی data/doctors."""
    specialties = doctor_loader.load_specialties()
    total_pages = max(1, (len(specialties) + SPEC_PER_PAGE - 1) // SPEC_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = specialties[page * SPEC_PER_PAGE:(page + 1) * SPEC_PER_PAGE]

    rows = [
        [InlineKeyboardButton(f"{item['label']} ({item['count']})", callback_data=f"bk_specpick_{item['key']}")]
        for item in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("▶️ قبلی", callback_data=f"bk_spec_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("◀️ بعدی", callback_data=f"bk_spec_{page + 1}"))
    if nav:
        rows.append(nav)
    if total_pages > 1:
        rows.append([InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="noop_page")])
    rows.append([InlineKeyboardButton(_safe_btn(DEFAULT_LANG, "btn_back", "بازگشت"), callback_data="booking_cancel")])
    return InlineKeyboardMarkup(rows)


def _build_doctor_keyboard(spec_key: str, page: int) -> tuple[InlineKeyboardMarkup, int]:
    """کیبورد صفحه‌بندی‌شده‌ی پزشکان یک تخصص واقعی."""
    doctors = doctor_loader.load_doctors(spec_key)
    total_pages = max(1, (len(doctors) + DOC_PER_PAGE - 1) // DOC_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = doctors[page * DOC_PER_PAGE:(page + 1) * DOC_PER_PAGE]

    rows = [
        [InlineKeyboardButton(doc["name_fa"], callback_data=f"bk_doc_{spec_key}_{page * DOC_PER_PAGE + index}")]
        for index, doc in enumerate(chunk)
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("▶️ قبلی", callback_data=f"bk_docpage_{spec_key}_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("◀️ بعدی", callback_data=f"bk_docpage_{spec_key}_{page + 1}"))
    if nav:
        rows.append(nav)
    if total_pages > 1:
        rows.append([InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="noop_page")])
    rows.append([InlineKeyboardButton(_safe_btn(DEFAULT_LANG, "btn_back", "بازگشت"), callback_data="bk_reselect_spec")])
    return InlineKeyboardMarkup(rows), len(doctors)


def _build_date_keyboard(lang: str, page: int) -> InlineKeyboardMarkup:
    """کیبورد تاریخ با نمایش شمسی (دو صفحه‌ی ۷ روزه)."""
    days = get_next_14_days_display(include_today=False)
    total_pages = (len(days) + DATE_PER_PAGE - 1) // DATE_PER_PAGE
    page = max(0, min(page, total_pages - 1))
    chunk = days[page * DATE_PER_PAGE:(page + 1) * DATE_PER_PAGE]

    rows = [[InlineKeyboardButton(label, callback_data=f"bk_date_{iso}")] for iso, label in chunk]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("▶️ روزهای قبل", callback_data=f"bk_datepage_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("روزهای بعد ◀️", callback_data=f"bk_datepage_{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(_safe_btn(lang, "btn_back", "بازگشت"), callback_data="booking_cancel")])
    return InlineKeyboardMarkup(rows)


def _build_time_keyboard(lang: str, available_times: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(slot, callback_data=f"bk_time_{slot}")] for slot in available_times]
    rows.append([InlineKeyboardButton(_safe_btn(lang, "btn_back", "بازگشت"), callback_data="booking_cancel")])
    return InlineKeyboardMarkup(rows)


def _build_summary(data: BookingData, lang: str) -> str:
    return "\n".join([
        "خلاصه نوبت:",
        f"نام بیمار: {data.name}",
        f"کد ملی: {data.national_code}",
        f"پزشک: {data.doctor_name}",
        f"تاریخ: {format_jalali(data.date)}",
        f"ساعت: {data.time}",
        f"مبلغ: {APPOINTMENT_AMOUNT:,} تومان",
        "",
        "آیا از ثبت این نوبت مطمئن هستید؟",
    ])


def _build_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("تأیید و پرداخت", callback_data="booking_confirm")],
        [InlineKeyboardButton(_safe_btn(lang, "btn_back", "بازگشت"), callback_data="booking_cancel")],
    ])


def _error_keyboard(lang: str) -> InlineKeyboardMarkup:
    """کیبورد خطا شامل دکمه بازگشت به منوی اصلی"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_main")]
    ])


async def _request_payment_safe(*, user_id: int, amount: int, description: str, callback_url: str, extra: dict) -> dict[str, Any]:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(request_payment, user_id=user_id, amount=amount, description=description, callback_url=callback_url, extra=extra),
            timeout=PAYMENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as error:
        raise ValueError("درگاه پرداخت پاسخ نداد (timeout)") from error
    if not isinstance(result, dict):
        raise ValueError("پاسخ درگاه پرداخت نامعتبر است")
    return result


async def _safe_answer(query) -> None:
    try:
        await query.answer()
    except Exception:
        pass


def _build_payment_callback_url(user_id: int) -> str:
    """آدرس callback زرین‌پال روی سرور لیارا (هندل verify در app/health.py).

    🆕 فیکس: قبلاً از getattr(settings, "BOT_USERNAME") استفاده می‌شد که غلط املایی
    داشت (فیلد واقعی bot_username است) و همیشه پیش‌فرض برمی‌گشت؛ callback هم به
    ble.ir می‌رفت که هیچ verify‌ای انجام نمی‌داد!
    """
    return f"{settings.public_base_url}/payment/callback?user_id={user_id}"


# ---------------------------------------------------------------------------
# مراحل گفتگو
# ---------------------------------------------------------------------------

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_chat is None: return ConversationHandler.END
    if update.callback_query is not None: await _safe_answer(update.callback_query)
    lang = _get_lang(context)
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


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or update.message.text is None: return ASK_NAME
    lang = _get_lang(context)
    name = update.message.text.strip()
    if len(name) < MIN_NAME_LENGTH:
        await update.message.reply_text("نام وارد شده خیلی کوتاه است.\nلطفاً نام و نام خانوادگی کامل وارد کنید:", reply_markup=_cancel_keyboard(lang))
        return ASK_NAME
    data = BookingData.from_context(context)
    data.name = name
    data.save_to(context)
    await update.message.reply_text("لطفاً کد ملی ۱۰ رقمی بیمار را وارد کنید:", reply_markup=_cancel_keyboard(lang))
    return ASK_NATIONAL_CODE


async def receive_national_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or update.message.text is None: return ASK_NATIONAL_CODE
    lang = _get_lang(context)
    national_code = update.message.text.strip()
    if not national_code.isdigit() or len(national_code) != NATIONAL_CODE_LENGTH:
        await update.message.reply_text(f"کد ملی وارد شده معتبر نیست.\nلطفاً یک کد ملی {NATIONAL_CODE_LENGTH} رقمی وارد کنید:", reply_markup=_cancel_keyboard(lang))
        return ASK_NATIONAL_CODE
    data = BookingData.from_context(context)
    data.national_code = national_code
    data.save_to(context)

    # 🆕 فیکس: به‌جای ۳ پزشک فیک، تخصص‌های واقعی از data/doctors نمایش داده می‌شوند
    count = len(doctor_loader.load_specialties())
    if count == 0:
        await update.message.reply_text(
            "متأسفانه لیست پزشکان در دسترس نیست.\nلطفاً بعداً تلاش کنید یا با پشتیبانی تماس بگیرید.",
            reply_markup=_error_keyboard(lang),
        )
        data.clear_from(context)
        return ConversationHandler.END
    await update.message.reply_text("لطفاً تخصص مورد نظر را انتخاب کنید:", reply_markup=_build_specialty_keyboard(0))
    return SELECT_SPEC


async def select_spec_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """صفحه‌بندی لیست تخصص‌ها."""
    query = update.callback_query
    if query is None: return SELECT_SPEC
    await _safe_answer(query)
    page = int(query.data.replace("bk_spec_", "")) if query.data.startswith("bk_spec_") else 0
    try:
        await query.edit_message_reply_markup(reply_markup=_build_specialty_keyboard(page))
    except Exception:
        pass
    return SELECT_SPEC


async def select_spec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """انتخاب تخصص → نمایش پزشکان واقعی آن تخصص."""
    query = update.callback_query
    if query is None: return SELECT_SPEC
    await _safe_answer(query)
    lang = _get_lang(context)
    spec_key = query.data.replace("bk_specpick_", "", 1)

    spec = doctor_loader.get_specialty(spec_key)
    if spec is None:
        await query.edit_message_text("تخصص انتخاب‌شده معتبر نیست. لطفاً دوباره تلاش کنید.", reply_markup=_cancel_keyboard(lang))
        return SELECT_SPEC

    data = BookingData.from_context(context)
    data.spec_key = spec_key
    data.doctor_key = ""
    data.doctor_id = ""
    data.doctor_name = ""
    data.save_to(context)

    keyboard, total = _build_doctor_keyboard(spec_key, 0)
    text = f"تخصص انتخابی: {spec['label']}\n\n{total} پزشک یافت شد. لطفاً پزشک مورد نظر را انتخاب کنید:"
    await query.edit_message_text(text, reply_markup=keyboard)
    return SELECT_DOCTOR


async def select_doctor_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """صفحه‌بندی لیست پزشکان."""
    query = update.callback_query
    if query is None: return SELECT_DOCTOR
    await _safe_answer(query)
    parts = query.data.replace("bk_docpage_", "", 1).rsplit("_", 1)
    spec_key, page = parts[0], int(parts[1]) if len(parts) == 2 else 0
    try:
        keyboard, _ = _build_doctor_keyboard(spec_key, page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    return SELECT_DOCTOR


async def reselect_spec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بازگشت به انتخاب تخصص."""
    query = update.callback_query
    if query is None: return SELECT_DOCTOR
    await _safe_answer(query)
    data = BookingData.from_context(context)
    data.spec_key = ""
    data.save_to(context)
    try:
        await query.edit_message_text("لطفاً تخصص مورد نظر را انتخاب کنید:", reply_markup=_build_specialty_keyboard(0))
    except Exception:
        pass
    return SELECT_SPEC


async def select_doctor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """انتخاب پزشک واقعی از لیست تخصص."""
    query = update.callback_query
    if query is None: return SELECT_DOCTOR
    await _safe_answer(query)
    lang = _get_lang(context)

    payload = query.data.replace("bk_doc_", "", 1)
    spec_key, _, index_raw = payload.rpartition("_")
    try:
        index = int(index_raw)
    except ValueError:
        await query.edit_message_text("پزشک انتخاب‌شده معتبر نیست. لطفاً دوباره تلاش کنید.", reply_markup=_cancel_keyboard(lang))
        return SELECT_DOCTOR

    doctors = doctor_loader.load_doctors(spec_key)
    if not (0 <= index < len(doctors)):
        await query.edit_message_text("پزشک انتخاب‌شده معتبر نیست. لطفاً دوباره تلاش کنید.", reply_markup=_cancel_keyboard(lang))
        return SELECT_DOCTOR

    doctor = doctors[index]
    data = BookingData.from_context(context)
    data.spec_key = spec_key
    data.doctor_id = doctor["id"]
    data.doctor_key = f"{spec_key}:{doctor['id']}"
    data.doctor_name = doctor["name_fa"]
    data.date = ""
    data.time = ""
    data.save_to(context)

    await query.edit_message_text(
        f"پزشک انتخابی: {data.doctor_name}\n\nلطفاً تاریخ نوبت را انتخاب کنید (۱۴ روز آینده):",
        reply_markup=_build_date_keyboard(lang, 0),
    )
    return SELECT_DATE


async def select_date_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """صفحه‌بندی تاریخ‌ها."""
    query = update.callback_query
    if query is None: return SELECT_DATE
    await _safe_answer(query)
    lang = _get_lang(context)
    try:
        page = int(query.data.replace("bk_datepage_", ""))
    except ValueError:
        page = 0
    try:
        await query.edit_message_reply_markup(reply_markup=_build_date_keyboard(lang, page))
    except Exception:
        pass
    return SELECT_DATE


async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None: return SELECT_DATE
    await _safe_answer(query)
    lang = _get_lang(context)
    date = query.data.replace("bk_date_", "")

    data = BookingData.from_context(context)
    available_times = get_available_times(date, data.doctor_key)
    if not available_times:
        await query.edit_message_text("برای این تاریخ ساعت خالی وجود ندارد.\nلطفاً تاریخ دیگری انتخاب کنید:", reply_markup=_build_date_keyboard(lang, 0))
        return SELECT_DATE
    data.date = date
    data.save_to(context)
    await query.edit_message_text(
        f"تاریخ انتخابی: {format_jalali(date)}\n\nلطفاً ساعت نوبت را انتخاب کنید:",
        reply_markup=_build_time_keyboard(lang, available_times),
    )
    return SELECT_TIME


async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None: return SELECT_TIME
    await _safe_answer(query)
    lang = _get_lang(context)
    slot = query.data.replace("bk_time_", "")
    data = BookingData.from_context(context)
    if not is_time_available(data.date, slot, data.doctor_key):
        available_times = get_available_times(data.date, data.doctor_key)
        if not available_times:
            await query.edit_message_text("این ساعت دیگر در دسترس نیست و ساعت خالی دیگری هم برای این تاریخ وجود ندارد.\nلطفاً تاریخ دیگری انتخاب کنید:", reply_markup=_build_date_keyboard(lang, 0))
            return SELECT_DATE
        await query.edit_message_text("این ساعت دیگر در دسترس نیست.\nلطفاً ساعت دیگری انتخاب کنید:", reply_markup=_build_time_keyboard(lang, available_times))
        return SELECT_TIME
    data.time = slot
    data.save_to(context)
    await query.edit_message_text(_build_summary(data, lang), reply_markup=_build_confirm_keyboard(lang))
    return CONFIRM_BOOKING


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None: return CONFIRM_BOOKING
    await _safe_answer(query)
    data = BookingData.from_context(context)
    lang = _get_lang(context)

    if data.confirmed:
        await query.edit_message_text(MSG_ALREADY_CONFIRMED, reply_markup=_error_keyboard(lang))
        return ConversationHandler.END

    if not data.is_complete():
        await query.edit_message_text("اطلاعات نوبت ناقص است. لطفاً دوباره از منو نوبت بگیرید.", reply_markup=_error_keyboard(lang))
        data.clear_from(context)
        return ConversationHandler.END

    user = update.effective_user
    user_id = user.id if user else 0

    appointment = {
        "user_id": user_id,
        "full_name": data.name,
        "national_code": data.national_code,
        "spec_key": data.spec_key,
        "doctor_key": data.doctor_key,
        "doctor_id": data.doctor_id,
        "doctor_name": data.doctor_name,
        "date": data.date,
        "time": data.time,
        "amount": APPOINTMENT_AMOUNT,
        "commission_rate": 0.0,
        "commission_amount": calculate_commission(APPOINTMENT_AMOUNT, 0.0),
        "doctor_share": APPOINTMENT_AMOUNT - calculate_commission(APPOINTMENT_AMOUNT, 0.0),
        "status": "pending",
        "expires_at": (_now() + timedelta(minutes=PENDING_TIMEOUT_MINUTES)).isoformat(),
    }

    if not add_appointment(appointment):
        await query.edit_message_text(MSG_SLOT_TAKEN, reply_markup=_error_keyboard(lang))
        data.clear_from(context)
        return ConversationHandler.END

    data.confirmed = True
    data.save_to(context)

    try:
        payment_response = await _request_payment_safe(
            user_id=user_id,
            amount=APPOINTMENT_AMOUNT,
            description=f"نوبت {data.doctor_name} - {data.date} {data.time}",
            callback_url=_build_payment_callback_url(user_id),
            extra={
                "date": data.date,
                "time": data.time,
                "doctor_key": data.doctor_key,
                "doctor_name": data.doctor_name,
                "full_name": data.name,
            },
        )

        if not payment_response.get("success"):
            raise ValueError(payment_response.get("error", "خطای نامشخص در درگاه پرداخت"))

        payment_link = payment_response.get("url")
        if not payment_link or not isinstance(payment_link, str):
            raise ValueError("لینک پرداخت خالی یا نامعتبر است")

        # 🆕 فیکس: رسید دیگر قبل از پرداخت ارسال نمی‌شود — بعد از verify در
        # app/health.py پیام موفقیت + رسید متن + PDF ارسال می‌شود.
        await query.edit_message_text(
            "\n".join([
                "نوبت شما موقتاً رزرو شد ✅",
                f"👨‍⚕️ پزشک: {data.doctor_name}",
                f"📅 تاریخ: {format_jalali(data.date)} — ساعت {data.time}",
                f"💰 مبلغ: {APPOINTMENT_AMOUNT:,} تومان",
                "",
                "برای قطعی شدن نوبت، در ۱۵ دقیقه آینده پرداخت را انجام دهید:",
                payment_link,
                "",
                "پس از پرداخت به‌صورت خودکار تأیید و رسید برای شما ارسال می‌شود. 💙",
            ]),
            reply_markup=None,
        )

    except Exception as error:
        logger.error("Error creating payment link: %s", error)
        try:
            cancel_appointment(date=data.date, time=data.time, user_id=user_id)
        except Exception as cancel_error:
            logger.error("Error cancelling pending appointment: %s", cancel_error)
        await query.edit_message_text(MSG_PAYMENT_FAILED, reply_markup=_error_keyboard(lang))

    data.clear_from(context)
    return ConversationHandler.END


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is not None:
        await _safe_answer(query)
        try:
            await query.edit_message_text(MSG_BOOKING_CANCELLED, reply_markup=None)
        except Exception:
            pass
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
    entry_points=[CallbackQueryHandler(start_booking, pattern=r"^start_booking$")],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        ASK_NATIONAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_national_code)],
        SELECT_SPEC: [
            CallbackQueryHandler(select_spec_page, pattern=r"^bk_spec_\d+$"),
            CallbackQueryHandler(select_spec, pattern=r"^bk_specpick_[a-z]+$"),
        ],
        SELECT_DOCTOR: [
            CallbackQueryHandler(select_doctor_page, pattern=r"^bk_docpage_[a-z]+_\d+$"),
            CallbackQueryHandler(select_doctor, pattern=r"^bk_doc_[a-z]+_\d+$"),
            CallbackQueryHandler(reselect_spec, pattern=r"^bk_reselect_spec$"),
        ],
        SELECT_DATE: [
            CallbackQueryHandler(select_date_page, pattern=r"^bk_datepage_\d+$"),
            CallbackQueryHandler(select_date, pattern=r"^bk_date_\d{4}-\d{2}-\d{2}$"),
        ],
        SELECT_TIME: [CallbackQueryHandler(select_time, pattern=r"^bk_time_\d{2}:\d{2}$")],
        CONFIRM_BOOKING: [CallbackQueryHandler(confirm_booking, pattern=r"^booking_confirm$")],
    },
    fallbacks=[CallbackQueryHandler(cancel_booking, pattern=r"^booking_cancel$")],
    allow_reentry=True,
)