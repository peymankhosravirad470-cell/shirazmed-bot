# app/services/booking.py

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Optional

import jdatetime

from config import settings

logger = logging.getLogger(__name__)

# ─── نام روزهای هفته شمسی (شنبه = ایندکس 0) ───
WEEKDAYS_FA: tuple[str, ...] = (
    "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه",
)


# ---------------------------------------------------------------------------
# ثابت‌ها
# ---------------------------------------------------------------------------

APPOINTMENTS_FILE = "appointments.json"
TMP_SUFFIX = ".tmp"

AVAILABLE_TIMES: tuple[str, ...] = (
    "09:00", "10:00", "11:00", "12:00",
    "16:00", "17:00", "18:00",
)

# وضعیت‌هایی که اسلات را «رزروشده» حساب می‌کنند
VALID_BOOKED_STATUSES: tuple[str, ...] = ("pending", "paid")

# وضعیت پیش‌فرض نوبت جدید
DEFAULT_STATUS = "pending"

# مدت اعتبار نوبت pending (به دقیقه)
PENDING_TTL_MINUTES: int = 15

# قفل درون‌فرآیندی برای جلوگیری از race
_BOOKING_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# مسیرها
# ---------------------------------------------------------------------------

def _get_data_dir() -> str:
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base_dir, "data")


def _get_appointments_path() -> str:
    return os.path.join(_get_data_dir(), APPOINTMENTS_FILE)


# ---------------------------------------------------------------------------
# ابزارهای زمان
# ---------------------------------------------------------------------------

def _now() -> datetime:
    """زمان فعلی به وقت ایران (سرور لیارا UTC است؛ بدون آفست، اسلات‌ها نصف‌روز خطا می‌کردند)."""
    return datetime.utcnow() + timedelta(hours=settings.timezone_offset_hours)


def format_jalali(date_str: str) -> str:
    """تبدیل تاریخ ISO میلادی (2026-10-25) به نمایش شمسی (۱۴۰۵/۰۸/۰۳) با نام روز.

    ورودی نامعتبر → همان رشته ورودی برگردانده می‌شود.
    """
    try:
        g = datetime.strptime(date_str, "%Y-%m-%d").date()
        j = jdatetime.date.fromgregorian(date=g)
        weekday_fa = WEEKDAYS_FA[(g.weekday() + 2) % 7]
        return f"{weekday_fa} {j.strftime('%Y/%m/%d')}"
    except (ValueError, TypeError):
        return date_str


def get_next_14_days_display(include_today: bool = False) -> list[tuple[str, str]]:
    """۱۴ روز آینده: لیست (تاریخ ISO برای callback، برچسب شمسی برای نمایش دکمه)."""
    return [(iso, format_jalali(iso)) for iso in get_next_14_days(include_today=include_today)]


def _parse_expires_at(appointment: dict[str, Any]) -> Optional[datetime]:
    raw = appointment.get("expires_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def _is_expired(appointment: dict[str, Any]) -> bool:
    expires_at = _parse_expires_at(appointment)
    if expires_at is None:
        return False
    return _now() > expires_at


# ---------------------------------------------------------------------------
# اعتبارسنجی و پاکسازی آیتم‌ها
# ---------------------------------------------------------------------------

def _sanitize_item(item: Any) -> Optional[dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    if not item.get("date") or not item.get("time"):
        return None
    return item


def _sanitize_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return [sanitized for item in items if (sanitized := _sanitize_item(item))]


def _is_slot_booked(item: dict[str, Any], date: str, time: str, doctor_key: Optional[str] = None) -> bool:
    """بررسی رزروشدن اسلات.

    🆕 فیکس: اگر doctor_key داده شود، اسلات‌ها برای هر پزشک جداگانه چک می‌شوند —
    قبلاً رزرو یک پزشک، همان ساعت را برای بقیه پزشکان هم می‌بست!
    """
    if item.get("date") != date or item.get("time") != time:
        return False
    if doctor_key is not None and item.get("doctor_key") != doctor_key:
        return False
    if item.get("status") not in VALID_BOOKED_STATUSES:
        return False
    if item.get("status") == "pending" and _is_expired(item):
        return False
    return True


def _purge_expired(appointments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in appointments:
        if item.get("status") == "pending" and _is_expired(item):
            logger.info(
                "Purging expired pending appointment: date=%s time=%s user=%s",
                item.get("date"), item.get("time"), item.get("user_id"),
            )
            continue
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# I/O فایل
# ---------------------------------------------------------------------------

def load_appointments() -> list[dict[str, Any]]:
    file_path = _get_appointments_path()
    try:
        if not os.path.isfile(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        sanitized = _sanitize_items(data)
        return _purge_expired(sanitized)
    except (json.JSONDecodeError, OSError) as error:
        logger.error("Error loading appointments: %s", error)
        return []


def _read_raw() -> list[dict[str, Any]]:
    file_path = _get_appointments_path()
    try:
        if not os.path.isfile(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return _sanitize_items(data)
    except (json.JSONDecodeError, OSError) as error:
        logger.error("Error reading raw appointments: %s", error)
        return []


def save_appointments(appointments: list[dict[str, Any]]) -> bool:
    file_path = _get_appointments_path()
    tmp_path = file_path + TMP_SUFFIX
    try:
        os.makedirs(_get_data_dir(), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(appointments, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, file_path)
        return True
    except (OSError, TypeError) as error:
        logger.error("Error saving appointments: %s", error)
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


# ---------------------------------------------------------------------------
# 🆕 محاسبه کمیسیون
# ---------------------------------------------------------------------------

def calculate_commission(amount: int, rate: float) -> int:
    """محاسبه مبلغ کمیسیون شیراز مدیکال.

    Args:
        amount: مبلغ ویزیت (تومان)
        rate: درصد کمیسیون (مثلاً 2 یعنی ۲ درصد)

    Returns:
        مبلغ کمیسیون به تومان (integer). در صورت ورودی نامعتبر، 0.
    """
    try:
        amount = int(amount)
        rate = float(rate)
    except (TypeError, ValueError):
        return 0
    if amount <= 0 or rate < 0:
        return 0
    return int(round(amount * rate / 100.0))


# ---------------------------------------------------------------------------
# عملیات دامنه
# ---------------------------------------------------------------------------

def add_appointment(
    appointment: dict[str, Any],
    commission_rate: Optional[float] = None,
    doctor_chat_id: Optional[str] = None,
) -> bool:
    """افزودن یک نوبت جدید با چک مجدد اسلات.

    Args:
        appointment: دیکشنری نوبت (شامل date, time, user_id, ...)
        commission_rate: 🆕 درصد کمیسیون (اگر None باشد، از دیکشنری خوانده می‌شود)
        doctor_chat_id: 🆕 آیدی عددی دکتر (اگر None باشد، از دیکشنری خوانده می‌شود)

    Returns:
        True اگر نوبت ذخیره شد، False در غیر این صورت.
    """
    if not isinstance(appointment, dict):
        logger.warning("add_appointment: appointment is not a dict")
        return False

    date = appointment.get("date")
    time = appointment.get("time")
    if not date or not time:
        logger.warning("add_appointment: date/time missing")
        return False

    appointment.setdefault("status", DEFAULT_STATUS)

    # 🆕 ذخیره فیلدهای کمیسیون و آیدی دکتر
    if commission_rate is not None:
        appointment["commission_rate"] = float(commission_rate)
    elif "commission_rate" not in appointment:
        appointment["commission_rate"] = 0.0

    if doctor_chat_id is not None:
        appointment["doctor_chat_id"] = str(doctor_chat_id)
    elif "doctor_chat_id" not in appointment:
        appointment["doctor_chat_id"] = ""

    # محاسبه و ذخیره کمیسیون
    amount = appointment.get("amount", 0)
    rate = appointment.get("commission_rate", 0.0)
    appointment["commission_amount"] = calculate_commission(amount, rate)
    appointment["doctor_share"] = int(amount) - appointment["commission_amount"]

    if appointment.get("status") == "pending" and not appointment.get("expires_at"):
        appointment["expires_at"] = (
            _now() + timedelta(minutes=PENDING_TTL_MINUTES)
        ).isoformat()

    with _BOOKING_LOCK:
        appointments = _read_raw()

        for existing in appointments:
            if _is_slot_booked(existing, date, time, appointment.get("doctor_key")):
                logger.info(
                    "add_appointment: slot already taken date=%s time=%s doctor=%s",
                    date, time, appointment.get("doctor_key"),
                )
                return False

        appointments.append(appointment)
        return save_appointments(appointments)


def cancel_appointment(date: str, time: str, user_id: int) -> bool:
    if not date or not time:
        logger.warning("cancel_appointment: date/time missing")
        return False

    with _BOOKING_LOCK:
        appointments = _read_raw()

        for i, appointment in enumerate(appointments):
            if (
                appointment.get("date") == date
                and appointment.get("time") == time
                and appointment.get("user_id") == user_id
                and appointment.get("status") == "pending"
            ):
                appointments.pop(i)
                logger.info(
                    "cancel_appointment: removed pending slot date=%s time=%s user=%s",
                    date, time, user_id,
                )
                return save_appointments(appointments)

    logger.info(
        "cancel_appointment: no matching pending appointment date=%s time=%s user=%s",
        date, time, user_id,
    )
    return False


def mark_appointment_paid(user_id: int, date: str, time: str) -> bool:
    with _BOOKING_LOCK:
        appointments = _read_raw()
        for appointment in appointments:
            if (
                appointment.get("date") == date
                and appointment.get("time") == time
                and appointment.get("user_id") == user_id
                and appointment.get("status") == "pending"
            ):
                appointment["status"] = "paid"
                appointment.pop("expires_at", None)
                logger.info(
                    "mark_appointment_paid: date=%s time=%s user=%s",
                    date, time, user_id,
                )
                return save_appointments(appointments)
    logger.warning(
        "mark_appointment_paid: no matching pending date=%s time=%s user=%s",
        date, time, user_id,
    )
    return False


# ---------------------------------------------------------------------------
# کوئری‌ها
# ---------------------------------------------------------------------------

def get_next_14_days(include_today: bool = False) -> list[str]:
    today = _now().date()
    start = 0 if include_today else 1
    return [
        (today + timedelta(days=start + i)).isoformat()
        for i in range(14)
    ]


def get_available_times(date: str, doctor_key: Optional[str] = None) -> list[str]:
    """ساعت‌های خالی یک تاریخ (و در صورت ارسال، برای یک پزشک مشخص)."""
    if not date:
        return list(AVAILABLE_TIMES)

    try:
        appointments = load_appointments()
        booked = {
            appt.get("time")
            for appt in appointments
            if _is_slot_booked(appt, date, appt.get("time"), doctor_key)
        }
        return [slot for slot in AVAILABLE_TIMES if slot not in booked]
    except Exception as error:
        logger.error("Error getting available times for '%s': %s", date, error)
        return list(AVAILABLE_TIMES)


def is_time_available(date: str, time: str, doctor_key: Optional[str] = None) -> bool:
    return time in get_available_times(date, doctor_key)


def get_user_appointments(user_id: int) -> list[dict[str, Any]]:
    try:
        return [
            appt
            for appt in load_appointments()
            if appt.get("user_id") == user_id
            and appt.get("status") in VALID_BOOKED_STATUSES
        ]
    except Exception as error:
        logger.error("Error getting user appointments for %s: %s", user_id, error)
        return []