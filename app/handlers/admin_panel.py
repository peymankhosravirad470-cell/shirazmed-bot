# -*- coding: utf-8 -*-
"""
پنل مدیریت (مأموریت: آیتم‌های ۱۷ و ۱۸ — تکمیل سطح ادمین).

دستورهای جدید (فقط ADMIN_CHAT_ID):
  /stats      → آمار کامل (آمار از دادهٔ واقعی — app/services/stats.py)
  /bookings   → ۲۰ نوبت آخر با وضعیت
  /referrals  → برترین معرف‌ها
  /admin      → راهنمای کامل سطح ادمین (شامل دستورهای قدیمی /pending و dregadm)

سطح ادمین در این ربات فارسی است (مستند در ممیزی) و این ماژول همان قاعده را دارد.
هیچ دادهٔ بیمار در لاگ نوشته نمی‌شود.
"""

from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)

_ADMIN_ONLY_TEXT = "⛔️ این دستور فقط برای مدیر مجاز است."


def is_admin(update: Update) -> bool:
    """ادمین = همان ADMIN_CHAT_ID (چت خصوصی → chat.id == user.id)."""
    admin_id = settings.admin_chat_id
    if not admin_id:
        return False
    chat = update.effective_chat
    user = update.effective_user
    return (chat is not None and chat.id == admin_id) or (user is not None and user.id == admin_id)


def _status_fa(status: str) -> str:
    return {"pending": "⏳ در انتظار پرداخت", "paid": "✅ پرداخت‌شده"}.get(status, status or "—")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    if not is_admin(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=_ADMIN_ONLY_TEXT)
        return
    try:
        from app.services.stats import collect_stats, format_stats
        text = format_stats(collect_stats())
    except Exception as error:
        logger.error("stats command failed: %s", error)
        text = "⚠️ محاسبهٔ آمار با خطا مواجه شد؛ لاگ سرور را بررسی کنید."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def bookings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    if not is_admin(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=_ADMIN_ONLY_TEXT)
        return
    try:
        from app.services.booking import load_appointments
        from app.services.booking import format_jalali
        rows = [row for row in load_appointments() if isinstance(row, dict)]
    except Exception as error:
        logger.error("bookings command failed: %s", error)
        rows = []
    if not rows:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📅 هیچ نوبتی ثبت نشده است.")
        return
    rows = rows[-20:][::-1]  # ۲۰ مورد آخر، تازه‌ترین اول
    lines = ["📅 ۲۰ نوبت آخر:"]
    for row in rows:
        amount = row.get("amount")
        amount_str = f"{int(amount):,}" if isinstance(amount, (int, float)) else "—"
        date_str = format_jalali(str(row.get("date", ""))) if row.get("date") else "—"
        name = str(row.get("full_name", "") or "—")
        # محرمانگی: کد ملی در پیام ادمین هم ماسک می‌شود
        nid = str(row.get("national_code", "") or "")
        nid_masked = ("***" + nid[-4:]) if len(nid) >= 4 else "—"
        lines.append(
            f"• {name} | کدملی {nid_masked} | {row.get('doctor_name', '—')} | "
            f"{date_str} {row.get('time', '')} | {amount_str} تومان | {_status_fa(str(row.get('status', '')))}"
        )
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(lines))


async def referrals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    if not is_admin(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=_ADMIN_ONLY_TEXT)
        return
    from app.services import referral  # ماژول سبک است؛ ایمپورت مستقیم امن
    try:
        tops = referral.top_referrers(10)
    except Exception as error:
        logger.error("referrals command failed: %s", error)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ خواندن دادهٔ ارجاع‌ها با خطا مواجه شد.")
        return
    if not tops:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🔗 هنوز ارجاعی ثبت نشده است.\n\n" + referral.admin_text())
        return
    lines = ["🏆 برترین معرف‌ها:"]
    for index, row in enumerate(tops, start=1):
        lines.append(
            f"{index}. کاربر {row['referrer_id']} ({referral.referral_code(row['referrer_id'])}) — "
            f"عضو: {row['joined']} | پرداخت‌شده: {row['paid']} | پاداش فعال: {row['available']} | مصرف‌شده: {row['used']}"
        )
    lines.append("")
    lines.append(referral.admin_text())
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(lines))


async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    if not is_admin(update):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=_ADMIN_ONLY_TEXT)
        return
    text = (
        "🛠 پنل مدیریت شیراز مدیکال\n\n"
        "📊 /stats — آمار کامل (نوبت، پرداخت، دارو، ارجاع، پزشک)\n"
        "📅 /bookings — ۲۰ نوبت آخر\n"
        "🏆 /referrals — برترین معرف‌ها + توضیح سیستم ارجاع\n"
        "🩺 /pending — درخواست‌های ثبت‌نام پزشک در انتظار تأیید\n"
        "✅❌ dregadm_ok_/dregadm_no_ — تأیید/رد پزشک (دکمه‌های پیام /pending)\n\n"
        "ℹ️ هشدارهای خودکار: نارضایتی جدید، شکایت نظرسنجی، «پرداخت شد ولی نوبت قطعی نشد»."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def dispatch_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مسیریاب یکپارچهٔ دستورهای ادمین: /stats /bookings /referrals /admin."""
    message = update.effective_message
    command = ""
    if message is not None and message.text:
        command = message.text.split()[0].lstrip("/").split("@")[0].strip().lower()
    if command == "stats":
        await stats_command(update, context)
    elif command == "bookings":
        await bookings_command(update, context)
    elif command == "referrals":
        await referrals_command(update, context)
    else:
        await admin_help_command(update, context)
