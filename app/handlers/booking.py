# app/services/booking.py

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any


APPOINTMENTS_FILE = "appointments.json"

AVAILABLE_TIMES = [
    "09:00", "10:00", "11:00", "12:00",
    "16:00", "17:00", "18:00",
]

VALID_BOOKED_STATUSES = ("pending", "paid")


def _get_data_dir() -> str:
    """مسیر پوشه data در روت پروژه را برمی‌گرداند."""
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base_dir, "data")


def _get_appointments_path() -> str:
    """مسیر کامل فایل appointments.json را برمی‌گرداند."""
    return os.path.join(_get_data_dir(), APPOINTMENTS_FILE)


def load_appointments() -> list[dict[str, Any]]:
    """خواندن امن نوبت‌ها از فایل appointments.json.

    فقط آیتم‌های dict برگردانده می‌شوند تا از خطا در توابع پایین‌دستی
    (مثل get_available_times) جلوگیری شود.
    """
    file_path = _get_appointments_path()
    try:
        if not os.path.isfile(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []
    except (json.JSONDecodeError, OSError) as error:
        print(f"Error loading appointments: {error}")
        return []


def save_appointments(appointments: list[dict[str, Any]]) -> bool:
    """ذخیره امن (اتمیک) نوبت‌ها در فایل appointments.json.

    از نوشتن در فایل موقت + os.replace استفاده می‌کند تا در صورت
    crash وسط نوشتن، فایل اصلی خراب نشود.
    """
    file_path = _get_appointments_path()
    tmp_path = file_path + ".tmp"
    try:
        os.makedirs(_get_data_dir(), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(appointments, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, file_path)
        return True
    except (OSError, TypeError) as error:
        print(f"Error saving appointments: {error}")
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def add_appointment(appointment: dict[str, Any]) -> bool:
    """افزودن یک نوبت جدید به فایل appointments.json با چک مجدد اسلات.

    قبل از افزودن، دوباره بررسی می‌کند که آن اسلات توسط نوبت
    pending/paid دیگری گرفته نشده باشد تا احتمال رزرو همزمان دو
    کاربر روی یک ساعت کاهش یابد.
    """
    if not isinstance(appointment, dict):
        print("add_appointment: appointment is not a dict")
        return False

    date = appointment.get("date")
    time = appointment.get("time")
    if not date or not time:
        print("add_appointment: date/time missing")
        return False

    appointment.setdefault("status", "pending")

    appointments = load_appointments()

    for existing in appointments:
        if (
            existing.get("date") == date
            and existing.get("time") == time
            and existing.get("status") in VALID_BOOKED_STATUSES
        ):
            print(f"add_appointment: slot already taken {date} {time}")
            return False

    appointments.append(appointment)
    return save_appointments(appointments)


def get_next_14_days(include_today: bool = False) -> list[str]:
    """تولید تاریخ‌های ۱۴ روز آینده با فرمت YYYY-MM-DD.

    اگر include_today=True باشد، امروز هم در لیست قرار می‌گیرد.
    """
    today = datetime.now().date()
    start = 0 if include_today else 1
    return [
        (today + timedelta(days=start + i)).isoformat()
        for i in range(14)
    ]


def get_available_times(date: str) -> list[str]:
    """دریافت ساعت‌های خالی برای تاریخ مشخص‌شده."""
    try:
        appointments = load_appointments()
        booked_times = [
            appointment.get("time")
            for appointment in appointments
            if appointment.get("date") == date
            and appointment.get("status") in VALID_BOOKED_STATUSES
        ]
        return [slot for slot in AVAILABLE_TIMES if slot not in booked_times]
    except Exception as error:
        print(f"Error getting available times for '{date}': {error}")
        return list(AVAILABLE_TIMES)


def is_time_available(date: str, time: str) -> bool:
    """بررسی آزاد بودن یک ساعت مشخص در تاریخ داده‌شده.

    توجه: این تابع فقط برای نمایش/اعتبارسنجی اولیه است. برای تأیید
    نهایی رزرو باید از add_appointment استفاده کرد (که خودش دوباره
    اسلات را چک می‌کند).
    """
    return time in get_available_times(date)