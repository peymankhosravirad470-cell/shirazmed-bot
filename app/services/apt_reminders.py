# -*- coding: utf-8 -*-
"""
یادآور نوبت (مأموریت: آیتم ۱۴ — نیمهٔ غایب آن؛ یادآور دارو از قبل فعال است).

رفتار:
- برای هر نوبت «پرداخت‌شده»، دو یادآور زمان‌بندی می‌شود: ۲۴ ساعت و ۲ ساعت قبل.
- زمان‌بندی از محل ثبت پرداخت (verify زرین‌پال) و همچنین از دیسک در post_init
  (بازیابی پس از ری‌استارت) انجام می‌شود — همان الگوی meds.
- متن یادآور از کلیدهای موجود locale (remind_apt_1d / remind_apt_2h) با زبانِ
  ثبت‌شده در خود نوبت ساخته می‌شود؛ زبان ثبت‌نشده → فارسی.
- هیچ یادآوری برای نوبت past یا pending ساخته نمی‌شود.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

try:  # zoneinfo در پایتون ≥3.9 استاندارد است؛ لیارا 3.11 دارد
    from zoneinfo import ZoneInfo
    _TEHRAN = ZoneInfo("Asia/Tehran")
except Exception:  # pragma: no cover — fallback ایمن
    from datetime import timezone as _tz
    _TEHRAN = _tz(timedelta(hours=3, minutes=30))

from app.locales import get_msg

logger = logging.getLogger(__name__)

_REMIND_BEFORE = {"1d": timedelta(hours=24), "2h": timedelta(hours=2)}
_JOB_PREFIX = "apt_rem"


def _appointment_datetime(appointment: dict[str, Any]) -> datetime | None:
    """ترکیب date (ISO) + time (HH:MM) → datetime منطقه‌بندی‌شدهٔ تهران."""
    date_iso = str(appointment.get("date", "")).strip()
    time_str = str(appointment.get("time", "")).strip()
    try:
        naive = datetime.strptime(f"{date_iso} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    try:
        return naive.replace(tzinfo=_TEHRAN)
    except Exception:  # pragma: no cover
        return None


def _reminder_text(appointment: dict[str, Any], which: str) -> str:
    lang = str(appointment.get("lang") or "fa")
    key = "remind_apt_1d" if which == "1d" else "remind_apt_2h"
    try:
        template = str(get_msg(lang, key))
    except Exception:  # pragma: no cover
        template = str(get_msg("fa", key))
    try:
        return template.format(
            time=str(appointment.get("time", "")),
            doctor=str(appointment.get("doctor_name", "")),
            address=str(appointment.get("office", "") or "—"),
        )
    except Exception:
        return template


async def _send_reminder(context: Any) -> None:
    """کال‌بک JobQueue — پیام یادآور به صاحب نوبت."""
    job = context.job
    data = getattr(job, "data", None) or {}
    chat_id = data.get("chat_id")
    text = data.get("text", "")
    if not chat_id or not text:
        return
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        logger.info("appointment reminder sent chat=%s kind=%s", chat_id, data.get("kind"))
    except Exception as error:  # pragma: no cover — شکست ارسال مسیر را نمی‌شکند
        logger.error("appointment reminder send failed chat=%s: %s", chat_id, error)


def schedule_appointment_reminders(application: Any, appointment: dict[str, Any], chat_id: int) -> int:
    """زمان‌بندی دو یادآور برای یک نوبت پرداخت‌شدهٔ آینده. تعدادِ ساخته‌شده برمی‌گردد."""
    job_queue = getattr(application, "job_queue", None)
    if job_queue is None:
        logger.warning("apt_reminders: job_queue unavailable — skipped")
        return 0
    if str(appointment.get("status", "")) != "paid":
        return 0
    when_base = _appointment_datetime(appointment)
    if when_base is None:
        logger.warning("apt_reminders: bad date/time, skipped: %s %s", appointment.get("date"), appointment.get("time"))
        return 0
    now = datetime.now(tz=when_base.tzinfo)
    scheduled = 0
    for kind, delta in _REMIND_BEFORE.items():
        when = when_base - delta
        if when <= now:
            continue  # گذشته → یادآور بی‌معناست
        job_queue.run_once(
            _send_reminder,
            when=when,
            chat_id=chat_id,
            data={
                "chat_id": chat_id,
                "text": _reminder_text(appointment, kind),
                "kind": kind,
            },
            name=f"{_JOB_PREFIX}_{kind}_{appointment.get('date', '')}_{appointment.get('time', '')}_{chat_id}",
        )
        scheduled += 1
    if scheduled:
        logger.info(
            "apt_reminders: %d scheduled for chat=%s date=%s time=%s",
            scheduled, chat_id, appointment.get("date"), appointment.get("time"),
        )
    return scheduled


def reschedule_from_disk(application: Any) -> int:
    """بازیابی یادآورها پس از ری‌استارت — فقط نوبت‌های پرداخت‌شدهٔ آینده."""
    try:
        from app.services.booking import load_appointments
        rows = [row for row in load_appointments() if isinstance(row, dict)]
    except Exception as error:
        logger.warning("apt_reminders: reschedule load failed: %s", error)
        return 0
    total = 0
    for appointment in rows:
        if str(appointment.get("status", "")) != "paid":
            continue
        try:
            chat_id = int(appointment.get("user_id") or 0)
        except (TypeError, ValueError):
            continue
        if chat_id <= 0:
            continue
        try:
            total += schedule_appointment_reminders(application, appointment, chat_id)
        except Exception as error:  # هر ردیف مستقل است
            logger.error("apt_reminders: reschedule row failed: %s", error)
    if total:
        logger.info("apt_reminders: restored %d reminder(s) from disk.", total)
    return total
