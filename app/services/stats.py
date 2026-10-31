# -*- coding: utf-8 -*-
"""
گزارش‌گیری و آمار مدیریتی (مأموریت: آیتم ۱۸).

همهٔ اعداد «فقط» از دادهٔ واقعی همان فایل‌های runtime محاسبه می‌شوند؛
هیچ عددی ساختگی درج نمی‌شود. خروجی برای پیام ادمین فارسی است (سطح ادمین
در این ربات فارسی است — مستند در ممیزی).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from config import DATA_DIR

logger = logging.getLogger(__name__)


def _load_appointments_safe() -> list[dict[str, Any]]:
    try:
        from app.services.booking import load_appointments
        rows = load_appointments()
        return [row for row in rows if isinstance(row, dict)]
    except Exception as error:  # آمار هرگز نباید کرش کند
        logger.warning("stats: appointments load failed: %s", error)
        return []


def _transactions_summary() -> dict[str, Any]:
    """اسکن data/transactions/<user_id>.json — فقط شمارنده و جمع مبلغ."""
    tx_dir = os.path.join(DATA_DIR, "transactions")
    verified_count = pending_count = 0
    verified_amount = 0
    user_ids: set[int] = set()
    try:
        if os.path.isdir(tx_dir):
            for name in os.listdir(tx_dir):
                if not name.endswith(".json"):
                    continue
                try:
                    user_ids.add(int(name[:-5]))
                except ValueError:
                    continue
                try:
                    with open(os.path.join(tx_dir, name), "r", encoding="utf-8") as handle:
                        rows = json.load(handle)
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    status = str(row.get("status", ""))
                    if status == "verified":
                        verified_count += 1
                        try:
                            verified_amount += int(row.get("amount", 0))
                        except (TypeError, ValueError):
                            pass
                    elif status == "pending":
                        pending_count += 1
    except OSError as error:
        logger.warning("stats: transactions scan failed: %s", error)
    return {
        "verified_count": verified_count,
        "pending_count": pending_count,
        "verified_amount": verified_amount,
        "user_ids": user_ids,
    }


def _meds_count() -> int:
    path = os.path.join(DATA_DIR, "meds.json")
    try:
        if not os.path.isfile(path):
            return 0
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return 0
        return sum(len(v) for v in data.values() if isinstance(v, list))
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("stats: meds load failed: %s", error)
        return 0


def _doctors_summary() -> dict[str, int]:
    try:
        from app.services import doctor_loader
        specs = doctor_loader.load_specialties()
        total = 0
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            count = spec.get("count")
            if count is None:
                key = spec.get("key") or spec.get("id")
                try:
                    count = len(doctor_loader.load_doctors(key)) if key else 0
                except Exception:
                    count = 0
            try:
                total += int(count)
            except (TypeError, ValueError):
                pass
        return {"approved": total}
    except Exception as error:
        logger.warning("stats: doctors load failed: %s", error)
        return {"approved": 0}


def collect_stats() -> dict[str, Any]:
    """جمع‌آوری کامل آمار از دادهٔ واقعی (بدون هیچ حدس)."""
    appointments = _load_appointments_safe()
    pending_apts = [a for a in appointments if a.get("status") == "pending"]
    paid_apts = [a for a in appointments if a.get("status") == "paid"]
    today_iso = datetime.now().strftime("%Y-%m-%d")
    upcoming = [
        a for a in paid_apts
        if str(a.get("date", "")) >= today_iso
    ]

    try:
        from app.services import referral
        referral_counts = referral.count_referrals()
    except Exception as error:
        logger.warning("stats: referral load failed: %s", error)
        referral_counts = {"total": 0, "joined": 0, "paid": 0, "available_rewards": 0, "used_rewards": 0}

    tx = _transactions_summary()
    known_users: set[int] = set(tx["user_ids"])
    for row in appointments:
        try:
            known_users.add(int(row.get("user_id") or 0))
        except (TypeError, ValueError):
            pass
    known_users.discard(0)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "appointments": {
            "pending": len(pending_apts),
            "paid": len(paid_apts),
            "upcoming_paid": len(upcoming),
        },
        "payments": {
            "verified_count": tx["verified_count"],
            "pending_count": tx["pending_count"],
            "verified_amount": tx["verified_amount"],
        },
        "med_reminders": _meds_count(),
        "referrals": referral_counts,
        "doctors": _doctors_summary(),
        "known_users": len(known_users),
    }


def format_stats(stats: dict[str, Any]) -> str:
    """قالب‌بندی فارسی برای پیام ادمین."""
    apts = stats.get("appointments", {})
    pay = stats.get("payments", {})
    ref = stats.get("referrals", {})
    doc = stats.get("doctors", {})
    lines = [
        "📊 آمار شیراز مدیکال",
        f"🕒 {stats.get('generated_at', '—')}",
        "",
        "📅 نوبت‌ها:",
        f"  • در انتظار پرداخت: {apts.get('pending', 0)}",
        f"  • پرداخت‌شده: {apts.get('paid', 0)}",
        f"  • پیش‌رو (پرداخت‌شده): {apts.get('upcoming_paid', 0)}",
        "",
        "💳 پرداخت‌ها (زرین‌پال):",
        f"  • تأییدشده: {pay.get('verified_count', 0)}",
        f"  • در انتظار: {pay.get('pending_count', 0)}",
        f"  • مجموع مبلغ تأییدشده: {int(pay.get('verified_amount', 0)):,} تومان",
        "",
        f"💊 یادآورهای داروی فعال: {stats.get('med_reminders', 0)}",
        "",
        "🔗 ارجاع‌ها:",
        f"  • کل: {ref.get('total', 0)} | عضو: {ref.get('joined', 0)} | پرداخت‌شده: {ref.get('paid', 0)}",
        f"  • پاداش فعال: {ref.get('available_rewards', 0)} | مصرف‌شده: {ref.get('used_rewards', 0)}",
        "",
        f"🩺 پزشکان تاییدشده: {doc.get('approved', 0)}",
        f"👥 کاربران شناخته‌شده (تراکنش/نوبت): {stats.get('known_users', 0)}",
        "",
        "ℹ️ اعداد فقط از فایل‌های واقعی runtime محاسبه شده‌اند.",
    ]
    return "\n".join(lines)
