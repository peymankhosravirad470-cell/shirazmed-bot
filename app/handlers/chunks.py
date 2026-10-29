# app/handlers/chunks.py
"""🧹 ردیابی و پاک‌سازی سراسری پیام‌های لیست‌های چندپیامی (_send_chunked).

🐛 باگ: وقتی یک لیست طولانی (بیمارستان‌ها/گردشگری/هتل‌ها/پیراپزشکی/بیمه/…)
به چند پیام جدا شکسته می‌شود، فقط آخرین پیام (که دکمه بازگشت دارد) با
کلیک بعدی ویرایش می‌شود و تکه‌های قبلی در چت باقی می‌مانند — کاربر هم
لیست قدیمی را می‌بیند هم منوی جدید.

✅ راه‌حل ریشه‌ای: هر تکه «غیر از آخرین» با message_id آن در user_data
ثبت می‌شود (track) و در نخستین ناوبری بعدی — بازگشت به منو، کلیک هر بخش
دیگر، تغییر زبان یا شروع پیشنهادات — همه آن‌ها حذف می‌شوند (cleanup).
آخرین تکه (نشانگرِ دارای کیبورد) هرگز ثبت نمی‌شود چون خودش با کلیک بعدی
ویرایش می‌شود؛ بنابراین هیچ‌وقت پیامی که باید بماند حذف نمی‌شود.

این ماژول عمداً هیچ وابستگی به callbacks/start ندارد تا از هر دو سمت
بدون import دورانی قابل استفاده باشد.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

_KEY = "chunk_msg_ids"


def _ud(context: ContextTypes.DEFAULT_TYPE):
    """دسترسی دفاعی به user_data — در تست‌ها context ساختگی ممکن است user_data نداشته باشد."""
    return getattr(context, "user_data", None)


def reset_tracked(context: ContextTypes.DEFAULT_TYPE) -> None:
    """خالی کردن فهرست ردیابی (شروع یک لیست جدید)."""
    ud = _ud(context)
    if ud is not None:
        ud.pop(_KEY, None)


def track(context: ContextTypes.DEFAULT_TYPE, message_id: Optional[int]) -> None:
    """ثبت message_id یک تکه «غیر آخر» برای حذف بعدی (بدون تکرار)."""
    ud = _ud(context)
    if ud is None or not message_id:
        return
    ids = ud.setdefault(_KEY, [])
    if isinstance(ids, list) and message_id not in ids:
        ids.append(int(message_id))


async def cleanup(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """حذف همه پیام‌های ثبت‌شده از چت + خالی کردن فهرست ردیابی.

    🚀 فیکس کندی: حذف‌ها «موازی» با asyncio.gather انجام می‌شوند نه ترتیبی —
    هر delete_message یک رفت‌وبرگشت کامل شبکه است و با RTT واقعی بله (~۲۵۰ms)
    حذف ترتیبی ۴ تکه ≈ ۱ ثانیه تأخیر اضافه قبل از نمایش منو ایجاد می‌کرد؛
    حالا کل حذف‌ها هم‌زمان ارسال می‌شوند و کل هزینه ≈ یک RTT است.
    نتیجه هر حذف مستقل بررسی می‌شود: شکست حذف پیام قدیمی/حذف‌شده‌ی قبلی
    نباید پاک‌سازی یا جریان کاربر را بشکند. مسیر سریع (لیست خالی) بدون
    هیچ کار اضافه‌ای خارج می‌شود تا هزینه‌ای به ناوبری عادی اضافه نشود.
    """
    ud = _ud(context)
    ids = (ud.get(_KEY) if ud is not None else None) or []
    if not ids:
        return
    results = await asyncio.gather(
        *(context.bot.delete_message(chat_id=chat_id, message_id=int(mid)) for mid in ids),
        return_exceptions=True,
    )
    for mid, result in zip(ids, results):
        if isinstance(result, Exception):  # noqa: BLE001 — حذف ناموفق نباید مسیر را بشکند
            logger.debug("chunk delete skipped (%s): %s", mid, result)
    if ud is not None:
        ud.pop(_KEY, None)
