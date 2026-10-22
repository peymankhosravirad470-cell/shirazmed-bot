# app/services/booking.py

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


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

# مدت اعتبار نوبت pending (به دقیقه) — بعد از این مدت اسلات آزاد می‌شود
PENDING_TTL_MINUTES: int = 15

# قفل درون‌فرآیندی برای جلوگیری از race در محیط multi-coroutine
_BOOKING_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# مسیرها
# ---------------------------------------------------------------------------

def _get_data_dir() -> str:
    """مسیر پوشه data در روت پروژه را برمی‌گرداند."""
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base_dir, "data")


def _get_appointments_path() -> str:
    """مسیر کامل فایل appointments.json را برمی‌گرداند."""
    return os.path.join(_get_data_dir(), APPOINTMENTS_FILE)


# ---------------------------------------------------------------------------
# ابزارهای زمان
# ---------------------------------------------------------------------------

def _now() -> datetime:
    """زمان فعلی (قابل monkey-patch در تست)."""
    return datetime.now()


def _parse_expires_at(appointment: dict[str, Any]) -> Optional[datetime]:
    """تاریخ expires_at را به datetime تبدیل می‌کند یا None برمی‌گرداند."""
    raw = appointment.get("expires_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def _is_expired(appointment: dict[str, Any]) -> bool:
    """آیا نوبت pending منقضی شده است؟"""
    expires_at = _parse_expires_at(appointment)
    if expires_at is None:
        return False
    return _now() > expires_at


# ---------------------------------------------------------------------------
# اعتبارسنجی و پاکسازی آیتم‌ها
# ---------------------------------------------------------------------------

def _sanitize_item(item: Any) -> Optional[dict[str, Any]]:
    """اگر آیتم dict معتبر بود، آن را برمی‌گرداند، وگرنه None."""
    if not isinstance(item, dict):
        return None
    if not item.get("date") or not item.get("time"):
        return None
    return item


def _sanitize_items(items: Any) -> list[dict[str, Any]]:
    """فیلتر و پاکسازی لیست آیتم‌ها."""
    if not isinstance(items, list):
        return []
    return [sanitized for item in items if (sanitized := _sanitize_item(item))]


def _is_slot_booked(item: dict[str, Any], date: str, time: str) -> bool:
    """آیا این آیتم، اسلات (date, time) را در وضعیت booked گرفته است؟"""
    if item.get("date") != date or item.get("time") != time:
        return False
    if item.get("status") not in VALID_BOOKED_STATUSES:
        return False
    # نوبت‌های pending منقضی، اسلات را آزاد می‌کنند
    if item.get("status") == "pending" and _is_expired(item):
        return False
    return True


def _purge_expired(appointments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """حذف نوبت‌های pending منقضی از لیست.

    این کار هنگام خواندن انجام می‌شود تا فایل به مرور تمیز شود و
    اسلات‌هایی که کاربر پرداخت را رها کرده، خودکار آزاد شوند.
    """
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
    """خواندن امن نوبت‌ها از فایل appointments.json.

    - فقط آیتم‌های dict معتبر (با date/time) برگردانده می‌شوند.
    - نوبت‌های pending منقضی فیلتر می‌شوند تا اسلات آزاد شود.
    """
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
    """خواندن خام بدون purge (برای عملیات نوشتن که نباید آیتم‌ها را قربانی کند)."""
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
    """ذخیره اتمیک نوبت‌ها در فایل appointments.json.

    از نوشتن در فایل موقت + fsync + os.replace استفاده می‌کند تا در
    صورت crash وسط نوشتن، فایل اصلی خراب نشود.
    """
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
# عملیات دامنه
# ---------------------------------------------------------------------------

def add_appointment(appointment: dict[str, Any]) -> bool:
    """افزودن یک نوبت جدید با چک مجدد اسلات.

    - قبل از ذخیره، دوباره بررسی می‌کند که آن اسلات توسط نوبت
      pending/paid دیگری (غیر منقضی) گرفته نشده باشد.
    - از قفل درون‌فرآیندی برای جلوگیری از race بین coroutineها استفاده می‌کند.
    - status را با "pending" پر می‌کند و expires_at را در صورت نبود ست می‌کند.
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

    # ست کردن expires_at اگر pending است و از قبل ست نشده
    if appointment.get("status") == "pending" and not appointment.get("expires_at"):
        appointment["expires_at"] = (
            _now() + timedelta(minutes=PENDING_TTL_MINUTES)
        ).isoformat()

    with _BOOKING_LOCK:
        appointments = _read_raw()

        for existing in appointments:
            if _is_slot_booked(existing, date, time):
                logger.info(
                    "add_appointment: slot already taken date=%s time=%s",
                    date, time,
                )
                return False

        appointments.append(appointment)
        return save_appointments(appointments)


def cancel_appointment(date: str, time: str, user_id: int) -> bool:
    """لغو یک نوبت pending متعلق به همان کاربر (مثلاً در صورت خطای پرداخت).

    فقط نوبت pending همان کاربر حذف می‌شود تا اسلات آزاد شود.
    """
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
    """علامت‌گذاری نوبت pending به paid (برای فراخوانی از callback درگاه)."""
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
    """تولید تاریخ‌های ۱۴ روز آینده با فرمت YYYY-MM-DD.

    اگر include_today=True باشد، امروز هم در لیست قرار می‌گیرد.
    """
    today = _now().date()
    start = 0 if include_today else 1
    return [
        (today + timedelta(days=start + i)).isoformat()
        for i in range(14)
    ]


def get_available_times(date: str) -> list[str]:
    """دریافت ساعت‌های خالی برای تاریخ مشخص‌شده."""
    if not date:
        return list(AVAILABLE_TIMES)

    try:
        appointments = load_appointments()  # purge خودکار انجام می‌شود
        booked = {
            appt.get("time")
            for appt in appointments
            if _is_slot_booked(appt, date, appt.get("time"))
        }
        return [slot for slot in AVAILABLE_TIMES if slot not in booked]
    except Exception as error:
        logger.error("Error getting available times for '%s': %s", date, error)
        return list(AVAILABLE_TIMES)


def is_time_available(date: str, time: str) -> bool:
    """بررسی آزاد بودن یک ساعت مشخص در تاریخ داده‌شده.

    توجه: این تابع فقط برای نمایش/اعتبارسنجی اولیه است. برای تأیید
    نهایی رزرو باید از add_appointment استفاده کرد (که خودش دوباره
    اسلات را چک می‌کند).
    """
    return time in get_available_times(date)


def get_user_appointments(user_id: int) -> list[dict[str, Any]]:
    """دریافت نوبت‌های یک کاربر (برای نمایش در پرونده)."""
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