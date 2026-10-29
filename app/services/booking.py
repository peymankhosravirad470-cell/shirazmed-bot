# app/services/booking.py

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta
from itertools import count
from typing import Any, Optional

import jdatetime

from config import DATA_DIR, settings

logger = logging.getLogger(__name__)

# ─── نام روزهای هفته شمسی (شنبه = ایندکس 0) ───
WEEKDAYS_FA: tuple[str, ...] = (
    "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه",
)


# ---------------------------------------------------------------------------
# ثابت‌ها
# ---------------------------------------------------------------------------

APPOINTMENTS_FILE = "appointments.json"

# 🆕 فیکس ثبت نوبت (مطابق الگوی اثبات‌شده‌ی meds): مسیر پشتیبان با env
# قابل تغییر است (همان MEDS_FALLBACK_DIR — یک متغیر برای کل سیستم).
# اگر مسیر اصلی نویسشنی بود (مجوز/سهمیه/فقط-خواندنی — مشکل واقعی لیارا)،
# نوبت روی مسیر پشتیبان ذخیره می‌شود و گم نمی‌شود.
FALLBACK_DIR = os.path.abspath(
    os.getenv("MEDS_FALLBACK_DIR", os.path.join(tempfile.gettempdir(), "shirazmed_data"))
)
FALLBACK_APPOINTMENTS_FILE = os.path.join(FALLBACK_DIR, APPOINTMENTS_FILE)

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

# 🆕 فیکس: شمارنده‌ی «ترتیب نوشتن» — saved_at در خود فایل ذخیره می‌شود تا
# «آخرین‌نویسنده برنده است» مستقل از دقت mtime فایل‌سیستم (تساوی mtime دو
# نوشته‌ی پشت‌سرهم دیگر معنا‌گذار نیست).
_SAVE_SEQ = count(1)


class AppointmentsReadError(RuntimeError):
    """🆕 ممیزی (بخش D): خواندن فایل نوبت‌ها شکست خورده (خراب/دسترس‌ناپذیر).

    ⚠️ اصل fail-closed: در این حالت «هیچ» اسلاتی آزاد فرض نمی‌شود و هیچ نوشتنی
    روی فایل خراب انجام نمی‌شود. قبلاً خطای خواندن → لیست خالی → همه‌ی ساعت‌ها
    «آزاد» نمایش داده می‌شد و ثبت نوبت می‌توانست فایل خراب را بازنویسی کند.
    """


# ---------------------------------------------------------------------------
# مسیرها
# ---------------------------------------------------------------------------

def _get_data_dir() -> str:
    """🆕 ممیزی (بخش J): ریشه‌ی داده از config.DATA_DIR (env: DATA_DIR) می‌آید
    تا دیسک پایدار لیارا (/app/data) و محیط تست با یک مکانیزم کنترل شوند."""
    return DATA_DIR


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

def _normalize_appt_file(data: Any) -> list[dict[str, Any]]:
    """🆕 فیکس: ساختار dict‌شکل {"appointments": [...]} هم پذیرفته می‌شود.

    فایل نمونه‌ی گیت (data/appointments.json) همین شکل را دارد؛ اگر روزی روی
    دیسک سرور هم چنین فایلی باشد، به‌جای «خالی فرض کردن»، لیست واقعی خوانده
    می‌شود و داده‌ی نوبت‌های موجود از دست نمی‌رود.
    """
    if isinstance(data, dict):
        data = data.get("appointments", [])
    return data if isinstance(data, list) else []


def _read_healthy_file() -> tuple[list[dict[str, Any]], str | None]:
    """🆕 فیکس: سالم‌ترین و تازه‌ترین نسخه برنده است (اصلی ↔ پشتیبان).

    هر دو فایل (اصلی/پشتیبان) خوانده می‌شوند؛ فایل خراب/نخواندنی نادیده گرفته
    می‌شود و برنده = «آخرین‌نویسنده»:
    - فایل‌های با فرمت جدید: مقایسه‌ی saved_at (داخل خود فایل — قطعی و مستقل
      از دقت mtime فایل‌سیستم)
    - فایل‌های قدیمی (لیست خام یا dict بدون saved_at): مقایسه‌ی mtime
    - فرمت جدید همیشه بر فرمت قدیمی اولویت دارد (نویسنده‌ی جدیدتر است)
    تساوی کامل → نسخه‌ی پرحجم‌تر؛ باز هم تساوی → ترتیب ثابت.
    اگر هیچ نسخه‌ی سالمی نبود ولی فایلِ خراب موجود بود → AppointmentsReadError
    (fail-closed: «خالی فرض کردن» ممنوع).

    Returns:
        (لیست نوبت‌ها، مسیری که واقعاً خوانده شد یا None اگر هیچ فایلی نبود)
    """
    primary = _get_appointments_path()
    parsed: list[tuple[int, str, float, int, list[dict[str, Any]], str]] = []
    corrupt: list[str] = []
    for path in (primary, FALLBACK_APPOINTMENTS_FILE):
        if not os.path.isfile(path):
            continue  # فایل غایب → مشکلی نیست
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            saved_at = ""
            if isinstance(data, dict):
                saved_at = str(data.get("saved_at") or "")
            items = _sanitize_items(_normalize_appt_file(data))
            # کلید برنده‌یابی: فرمت‌جدید اول، saved_at، mtime، تعداد آیتم
            parsed.append((
                1 if saved_at else 0,
                saved_at,
                os.path.getmtime(path),
                len(items),
                items,
                path,
            ))
        except (json.JSONDecodeError, OSError) as error:
            # فایل موجود ولی خراب/نخواندنی → ثبت می‌شود؛ اگر نسخه‌ی سالمی هم
            # پیدا نشود، fail-closed اعمال می‌شود (خطا، نه «خالی فرض کردن»)
            corrupt.append(f"{path}: {error}")
            continue
    if parsed:
        parsed.sort(key=lambda t: t[:4])  # آخرین‌نویسنده برنده است
        _, _, _, _, items, path = parsed[-1]
        return items, path
    if corrupt:
        raise AppointmentsReadError(" | ".join(corrupt))
    return [], None


def load_appointments() -> list[dict[str, Any]]:
    """خواندن نوبت‌ها؛ فایل غایب = لیست خالی، فایل خراب = AppointmentsReadError (fail-closed).

    🆕 فیکس: نسخه‌ی سالمِ مسیر پشتیبان هم دیده می‌شود (تازه‌ترین سالم برنده).
    """
    items, source = _read_healthy_file()
    if source is not None and source != _get_appointments_path():
        logger.error("نوبت‌ها از مسیر پشتیبان خوانده شد: %s", source)
    return _purge_expired(items)


def _read_raw() -> list[dict[str, Any]]:
    """خواندن خام برای مسیرهای نوشتنی؛ فایل خراب → AppointmentsReadError (fail-closed)."""
    items, _ = _read_healthy_file()
    return items


def _atomic_write(path: str, payload: str) -> None:
    """🆕 فیکس ثبت نوبت — نوشتن اتمی با نام tmp «یکتا» (mkstemp).

    تله‌ی واقعی لیارا (همان که meds را می‌شکست): نام ثابت appointments.json.tmp
    اگر از نوشتن نیمه‌کاره‌ای قبلی بدون مجوز باقی مانده بود، open(w) با
    PermissionError برای همیشه می‌مرد. نام یکتا این تله را از بین می‌برد.
    """
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".appt-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except OSError:
            pass


def save_appointments(appointments: list[dict[str, Any]]) -> bool:
    """🆕 فیکس: ذخیره روی مسیر اصلی + همگام‌سازی مسیر پشتیبان.

    - مسیر اصلی نوشته می‌شود؛ اگر شکست خورد (مجوز/سهمیه/فقط-خواندنی — مشکل
      واقعی لیارا)، مسیر پشتیبان نجات‌دهنده است.
    - وقتی مسیر اصلی موفق است، «همان داده» روی پشتیبان هم بازنویسی می‌شود تا
      نسخه‌ی پشتیبان هرگز کهنه نشود؛ اگر بعداً مسیر اصلی از دسترس خارج شد،
      آخرین وضعیت دقیقاً روی پشتیبان موجود است.
    - True فقط وقتی برگردانده می‌شود که نوشتن «واقعاً» موفق بوده باشد؛ بنابراین
      پیام موفقیت رزرو هرگز برای ذخیره‌ی نشده نمایش داده نمی‌شود.
    """
    payload_obj = {
        # 🆕 saved_at داخل فایل → «آخرین‌نویسنده برنده است» قطعی می‌شود
        "saved_at": f"{_now().isoformat()}|{next(_SAVE_SEQ):06d}",
        "appointments": appointments,
    }
    payload = json.dumps(payload_obj, ensure_ascii=False, indent=2)
    errors: list[str] = []

    primary = _get_appointments_path()
    ok_primary = False
    ok_fallback = False
    try:
        os.makedirs(os.path.dirname(primary), exist_ok=True)
        _atomic_write(primary, payload)
        ok_primary = True
    except (OSError, TypeError) as error:
        errors.append(f"{primary}: {error}")
        logger.error("Error saving appointments at %s: %s", primary, error)

    try:
        os.makedirs(os.path.dirname(FALLBACK_APPOINTMENTS_FILE), exist_ok=True)
        _atomic_write(FALLBACK_APPOINTMENTS_FILE, payload)
        ok_fallback = True
        if not ok_primary:
            logger.error(
                "ذخیره‌سازی نوبت‌ها روی مسیر اصلی ممکن نشد — روی مسیر پشتیبان نوشته شد: %s | جزئیات: %s",
                FALLBACK_APPOINTMENTS_FILE, " | ".join(errors),
            )
    except (OSError, TypeError) as error:
        if not ok_primary:
            logger.error("Error saving appointments at %s: %s", FALLBACK_APPOINTMENTS_FILE, error)

    return ok_primary or ok_fallback


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

def is_slot_taken_by_real_booking(date: str, time: str, doctor_key: Optional[str] = None) -> bool:
    """🆕 فیکس: آیا این اسلات «واقعاً» توسط یک نوبت معتبر اشغال شده؟

    برای تفکیک «اسلات اشغال» از «شکست ذخیره‌سازی»: اگر add_appointment با False
    برگشت ولی این تابع هم False داد، علت False شدن ذخیره‌سازی بوده است نه اشغال —
    و کاربر باید پیام صادقانه‌ی خطای ذخیره‌سازی ببیند، نه پیام دروغین «اسلات پر شد».
    """
    try:
        return any(
            _is_slot_booked(item, date, time, doctor_key)
            for item in load_appointments()
        )
    except Exception:
        return False


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
        # 🆕 ممیزی (D): اگر خواندن شکست بخورد، «نوشتن» مطلقاً انجام نمی‌شود —
        # وگرنه فایل خراب با لیست ناقص بازنویسی و نوبت‌های موجود از بین می‌رفت.
        try:
            appointments = _read_raw()
        except AppointmentsReadError:
            logger.error(
                "add_appointment: read failed — refusing to write (fail-closed) date=%s time=%s",
                date, time,
            )
            return False

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
        try:
            appointments = _read_raw()
        except AppointmentsReadError:
            # 🆕 ممیزی (D): بدون خواندن معتبر، لغو/تغییر وضعیت انجام نمی‌شود.
            logger.error("cancel_appointment: read failed — refusing to modify (fail-closed)")
            return False

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
        try:
            appointments = _read_raw()
        except AppointmentsReadError:
            # 🆕 ممیزی (D/C.6): بدون خواندن معتبر، وضعیت paid ثبت نمی‌شود —
            # فراخواننده (health.py) پیام صادقانه‌ی «نیازمند پیگیری» می‌فرستد.
            logger.error("mark_appointment_paid: read failed — refusing to modify (fail-closed)")
            return False
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
    """ساعت‌های خالی یک تاریخ (و در صورت ارسال، برای یک پزشک مشخص).

    🆕 ممیزی (بخش D — fail-closed): اگر خواندن داده‌ی نوبت به هر دلیل شکست بخورد،
    خروجی «لیست خالی» است (نه همه‌ی ساعت‌ها!). UI رزرو برای لیست خالی پیام
    «امکان تایید ساعت نیست / ساعت دیگری انتخاب کنید» نشان می‌دهد — در نتیجه خطای
    سیستم هرگز به شکل «همه‌ی ساعت‌ها آزاد است» دیده نمی‌شود.
    """
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
    except AppointmentsReadError as error:
        # fail-closed: خواندن شکست خورد → هیچ اسلاتی «آزاد» فرض نمی‌شود
        logger.error("get_available_times: read failed — returning NO slots (fail-closed): %s", error)
        return []
    except Exception as error:
        logger.error("Error getting available times for '%s': %s", date, error)
        return []


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