# -*- coding: utf-8 -*-
"""
سیستم معرفی کاربران و پاداش ارجاع (مأموریت: آیتم ۱۹).

منطق صادقانهٔ پاداش:
- کاربرِ معرفی‌شده با لینک دعوت وارد می‌شود → ردیف ارجاع با reward_status="pending" ثبت می‌شود.
- فقط وقتی آن کاربر «اولین پرداخت موفق» نوبتش انجام شد → پاداش معرف "available" می‌شود.
- پاداشِ available = ۱۰٪ تخفیف واقعی روی نوبت بعدیِ معرف (همان وعدهٔ موجود در ربات)
  و در لحظهٔ ثبت نوبتِ معرف مصرف می‌شود (مصرفِ اتمیک؛ پرداخت با همان مبلغ تخفیف‌خورده
  درخواست و verify می‌شود تا تطبیق مبلغِ درگاه هرگز نشکند).

ذخیره‌سازی: DATA_DIR/referrals.json — نوشتن اتمیک با mkstemp + os.replace
(همان الگوی سخت‌گیرانهٔ meds/booking) + مسیر پشتیبان در صورت شکست دیسک اصلی.

سازگاری پس‌رونده: لینک‌های قدیمی `https://ble.ir/ShirazMedBot?start=<user_id>`
که قبلاً پخش شده‌اند، عیناً به‌عنوان کد ارجاع عددی پذیرفته می‌شوند.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from typing import Any

from config import DATA_DIR, settings

logger = logging.getLogger(__name__)

_REFERRAL_FILE = os.path.join(DATA_DIR, "referrals.json")
_FALLBACK_DIR = os.getenv("MEDS_FALLBACK_DIR", "")  # همان متغیر مسیر پشتیبانِ پروژه

_REWARD_DISCOUNT_PCT = 10
_LOCK = threading.Lock()


# ─────────────────────────── ابزار کد ───────────────────────────

def referral_code(user_id: int) -> str:
    """کد قابل‌خواندن و دوسویه: SM + هگز user_id (مثال: SM1A2B3C)."""
    try:
        return f"SM{int(user_id):X}"
    except (TypeError, ValueError):
        return ""


def parse_referral_code(raw: str) -> int | None:
    """کد یا لینک دعوت → user_id معرف؛ نامعتبر → None.

    قالب‌های پذیرفته‌شده: "SM1A2B3C"، "sm1a2b3c"، "123456" (لینک‌های قدیمی).
    """
    token = (raw or "").strip()
    if token.lower().startswith("docreg"):  # لینک پزشکان هرگز ارجاع نیست
        return None
    if token.upper().startswith("SM"):
        hex_part = token[2:]
        try:
            value = int(hex_part, 16)
        except ValueError:
            return None
        return value if value > 0 else None
    if token.isdigit():
        value = int(token)
        return value if value > 0 else None
    return None


# ─────────────────────────── ذخیره‌سازی اتمیک ───────────────────────────

def _fallback_paths() -> list[str]:
    paths = [_REFERRAL_FILE]
    if _FALLBACK_DIR:
        paths.append(os.path.join(_FALLBACK_DIR, "referrals.json"))
    return paths


def _atomic_write(path: str, payload: str) -> None:
    """نوشتن اتمیک: فایل موقت یکتا + os.replace (هرگز نام tmp ثابت — درس لیارا)."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".referrals-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


def _load() -> dict[str, Any]:
    """خواندن مقاوم: فایل سالم هر مسیر (اصلی/پشتیبان)؛ خراب → ساختار خالی."""
    for path in _fallback_paths():
        try:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and isinstance(data.get("referrals"), list):
                return data
            if isinstance(data, list):  # سازگاری با ساختار سادهٔ قدیمی
                return {"referrals": data}
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("referrals load failed for %s: %s", path, exc)
    return {"referrals": []}


def _save(data: dict[str, Any]) -> bool:
    """نوشتن روی همهٔ مسیرها؛ حداقل یکی کافی است. هر دو شکست → False (صادقانه)."""
    payload = json.dumps(data, ensure_ascii=False, indent=1)
    ok = False
    last_error: Exception | None = None
    for path in _fallback_paths():
        try:
            _atomic_write(path, payload)
            ok = True
        except OSError as exc:
            last_error = exc
            logger.error("referrals save failed on %s: %s", path, exc)
    if not ok and last_error:
        logger.error("referrals save failed on ALL paths")
    return ok


# ─────────────────────────── منطق اصلی ───────────────────────────

def record_referral(referrer_id: int, invited_id: int, invited_username: str = "") -> bool:
    """ثبت ورودِ کاربر معرفی‌شده. خودارجاعی/تکراری/نامعتبر → False."""
    try:
        referrer_id = int(referrer_id)
        invited_id = int(invited_id)
    except (TypeError, ValueError):
        return False
    if referrer_id <= 0 or invited_id <= 0 or referrer_id == invited_id:
        return False
    with _LOCK:
        data = _load()
        rows = data.get("referrals", [])
        for row in rows:
            if isinstance(row, dict) and row.get("invited_id") == invited_id:
                return False  # هر کاربر فقط یک بار می‌تواند «معرفی‌شده» باشد
        rows.append(
            {
                "referrer_id": referrer_id,
                "invited_id": invited_id,
                "invited_username": (invited_username or "")[:64],
                "invited_at": datetime.now().isoformat(timespec="seconds"),
                "status": "joined",          # joined → paid
                "reward_status": "pending",  # pending → available → used
            }
        )
        data["referrals"] = rows
        return _save(data)


def mark_referral_paid(invited_id: int) -> bool:
    """اولین پرداخت موفقِ کاربر معرفی‌شده → پاداش معرف فعال می‌شود.

    از مسیر verify زرین‌پال صدا زده می‌شود؛ شکستش هرگز جریان پرداخت را نمی‌شکند.
    """
    try:
        invited_id = int(invited_id)
    except (TypeError, ValueError):
        return False
    with _LOCK:
        data = _load()
        changed = False
        for row in data.get("referrals", []):
            if (
                isinstance(row, dict)
                and row.get("invited_id") == invited_id
                and row.get("status") == "joined"
            ):
                row["status"] = "paid"
                row["reward_status"] = "available"
                row["paid_at"] = datetime.now().isoformat(timespec="seconds")
                changed = True
        if not changed:
            return False
        return _save(data)


def get_available_discount_pct(user_id: int) -> int:
    """درصد تخفیف قابل‌استفادهٔ کاربر (۰ یا ۱۰) — پاداشِ فقط «پرداخت‌شده»."""
    with _LOCK:
        data = _load()
        for row in data.get("referrals", []):
            if (
                isinstance(row, dict)
                and row.get("referrer_id") == int(user_id or 0)
                and row.get("reward_status") == "available"
            ):
                return _REWARD_DISCOUNT_PCT
    return 0


def consume_reward(user_id: int) -> bool:
    """مصرف یک پاداش available در لحظهٔ ثبت موفق نوبت معرف (اتمیک زیر قفل)."""
    with _LOCK:
        data = _load()
        for row in data.get("referrals", []):
            if (
                isinstance(row, dict)
                and row.get("referrer_id") == int(user_id or 0)
                and row.get("reward_status") == "available"
            ):
                row["reward_status"] = "used"
                row["used_at"] = datetime.now().isoformat(timespec="seconds")
                return _save(data)
    return False


def get_referral_stats(user_id: int) -> dict[str, Any]:
    """آمار شخصی معرف: کد + شمارنده‌ها."""
    with _LOCK:
        rows = _load().get("referrals", [])
        mine = [r for r in rows if isinstance(r, dict) and r.get("referrer_id") == int(user_id or 0)]
    return {
        "code": referral_code(user_id),
        "joined": sum(1 for r in mine if r.get("status") in ("joined", "paid")),
        "paid": sum(1 for r in mine if r.get("status") == "paid"),
        "available_rewards": sum(1 for r in mine if r.get("reward_status") == "available"),
        "used_rewards": sum(1 for r in mine if r.get("reward_status") == "used"),
    }


def top_referrers(limit: int = 10) -> list[dict[str, Any]]:
    """برترین معرف‌ها برای پنل ادمین (بر اساس پرداخت‌شده، سپس عضو)."""
    with _LOCK:
        rows = [r for r in _load().get("referrals", []) if isinstance(r, dict)]
    agg: dict[int, dict[str, int]] = {}
    for row in rows:
        rid = int(row.get("referrer_id") or 0)
        if rid <= 0:
            continue
        bucket = agg.setdefault(rid, {"joined": 0, "paid": 0, "available": 0, "used": 0})
        if row.get("status") in ("joined", "paid"):
            bucket["joined"] += 1
        if row.get("status") == "paid":
            bucket["paid"] += 1
        if row.get("reward_status") == "available":
            bucket["available"] += 1
        if row.get("reward_status") == "used":
            bucket["used"] += 1
    ranked = sorted(agg.items(), key=lambda kv: (kv[1]["paid"], kv[1]["joined"]), reverse=True)
    return [{"referrer_id": rid, **counts} for rid, counts in ranked[: max(1, int(limit))]]


def count_referrals() -> dict[str, int]:
    """شمار کلی برای آمار مدیریتی."""
    with _LOCK:
        rows = [r for r in _load().get("referrals", []) if isinstance(r, dict)]
    return {
        "total": len(rows),
        "joined": sum(1 for r in rows if r.get("status") == "joined"),
        "paid": sum(1 for r in rows if r.get("status") == "paid"),
        "available_rewards": sum(1 for r in rows if r.get("reward_status") == "available"),
        "used_rewards": sum(1 for r in rows if r.get("reward_status") == "used"),
    }


def notify_text(lang: str) -> str:
    """پیام صادقانهٔ پاداش برای نمایش به معرف (سه‌زبانه)."""
    texts = {
        "fa": "🎁 پاداش معرفی: با اولین پرداختِ هر کسی که با لینک شما وارد شود، ۱۰٪ تخفیف واقعی روی نوبت بعدیِ خودتان فعال می‌شود.",
        "en": "🎁 Referral reward: once someone who joined via your link completes their first payment, you get a real 10% discount on your next booking.",
        "ar": "🎁 مكافأة الإحالة: عند إتمام أول دفعة لمن انضم عبر رابطك، تحصل على خصم حقيقي 10% على حجزك القادم.",
    }
    return texts.get(lang, texts["fa"])


def admin_text() -> str:
    """توضیح فارسی برای پنل ادمین (سطح ادمین فارسی است — مستند در ممیزی)."""
    return (
        "🔗 سیستم ارجاع (پاداش واقعی، بدون وعدهٔ بی‌پشتوانه)\n"
        f"• پاداش: {_REWARD_DISCOUNT_PCT}٪ تخفیف روی نوبت بعدی معرف\n"
        "• فعال‌سازی پاداش: فقط بعد از اولین پرداخت موفقِ معرفی‌شده\n"
        "• ذخیره‌سازی: data/referrals.json (اتمیک + مسیر پشتیبان)\n"
        "• سازگار با لینک‌های قدیمی ble.ir?start=<user_id>\n"
        f"• آدرس پنل ادمین: ADMIN_CHAT_ID={settings.admin_chat_id or '—'}"
    )
