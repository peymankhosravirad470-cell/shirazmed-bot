# -*- coding: utf-8 -*-
"""
سرویس پرداخت زرین‌پال (خالص — بدون هیچ منطق تلگرامی).
ذخیره‌سازی: یک فایل JSON اتمیک برای هر کاربر در data/transactions/<user_id>.json
فیکس‌های بحرانی v45: بررسی پرداخت تکراری + تطبیق دقیق مبلغ قبل از verify.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any

import requests

from config import DATA_DIR, settings

logger = logging.getLogger(__name__)

# 🆕 ممیزی (بخش J): مسیر تراکنش‌ها از config.DATA_DIR (env: DATA_DIR) — قبلاً
# مسیر نسبیِ وابسته به cwd بود که با دیسک پایدار لیارا و تست‌ها ناسازگار بود.
_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "transactions")
_REQUEST_TIMEOUT = 20
_VERIFY_TIMEOUT = 20

# 🔒 ممیزی (بخش C): قفل درون‌فرآیندی تراکنش‌ها. تراکنش‌ها از دو مسیر هم‌زمان
# دست‌کاری می‌شوند: ترد health (verify_payment پس از callback زرین‌پال) و حلقه‌ی
# ربات (request_payment). بدون این قفل، خواندن-تغییر-نوشتنِ هم‌زمان می‌توانست
# رکورد را گم کند یا دو بار verify شود (دو پیام موفقیت/دو رسید). فراخوانی شبکه
# زرین‌پال داخل قفل است تا کل چرخه‌ی «بررسی وضعیت → verify → ذخیره» اتمیک باشد.
_TX_LOCK = threading.Lock()

_SANDBOX_REQUEST_URL = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
_PRODUCTION_REQUEST_URL = "https://payment.zarinpal.com/pg/v4/payment/request.json"
_SANDBOX_VERIFY_URL = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
_PRODUCTION_VERIFY_URL = "https://payment.zarinpal.com/pg/v4/payment/verify.json"
_SANDBOX_STARTPAY_BASE = "https://sandbox.zarinpal.com/pg/StartPay/"
_PRODUCTION_STARTPAY_BASE = "https://payment.zarinpal.com/pg/StartPay/"


def _request_url() -> str:
    """آدرس درخواست پرداخت را بر اساس حالت sandbox/production برمی‌گرداند."""
    return _SANDBOX_REQUEST_URL if settings.zarinpal_sandbox else _PRODUCTION_REQUEST_URL


def _verify_url() -> str:
    """آدرس تأیید پرداخت را بر اساس حالت sandbox/production برمی‌گرداند."""
    return _SANDBOX_VERIFY_URL if settings.zarinpal_sandbox else _PRODUCTION_VERIFY_URL


def _startpay_base() -> str:
    """آدرس پایه‌ی صفحه‌ی پرداخت را بر اساس حالت sandbox/production برمی‌گرداند."""
    return _SANDBOX_STARTPAY_BASE if settings.zarinpal_sandbox else _PRODUCTION_STARTPAY_BASE


def _get_user_file(user_id: int) -> str:
    """مسیر فایل تراکنش‌های کاربر را برمی‌گرداند و پوشه را در صورت نبود می‌سازد."""
    os.makedirs(_TRANSACTIONS_DIR, exist_ok=True)
    return os.path.join(_TRANSACTIONS_DIR, f"{user_id}.json")


def _load_transactions(user_id: int) -> list[dict[str, Any]]:
    """تراکنش‌های کاربر را می‌خواند؛ در صورت نبود یا خرابی فایل، لیست خالی برمی‌گرداند."""
    path = _get_user_file(user_id)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logger.warning("فایل تراکنش کاربر %s ساختار نامعتبر دارد.", user_id)
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("خطا در خواندن فایل تراکنش کاربر %s: %s", user_id, exc)
        return []


def _save_transactions(user_id: int, data: list[dict[str, Any]]) -> bool:
    """تراکنش‌های کاربر را به‌صورت اتمیک (temp file + os.replace) ذخیره می‌کند.

    🆕 ممیزی (بخش C.1): نتیجه‌ی ذخیره «به فراخواننده اعلام می‌شود» — قبلاً خطا
    بلعیده می‌شد و فراخواننده موفقیت فرض می‌کرد.
    """
    path = _get_user_file(user_id)
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError as exc:
        logger.error("خطا در ذخیره‌ی اتمیک تراکنش‌های کاربر %s: %s", user_id, exc)
        return False


def _find_transaction(transactions: list[dict[str, Any]], authority: str) -> dict[str, Any] | None:
    """تراکنش متناظر با یک authority را در لیست پیدا می‌کند."""
    for tx in transactions:
        if tx.get("authority") == authority:
            return tx
    return None


def request_payment(
    user_id: int,
    amount: int,
    description: str,
    callback_url: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """درخواست ایجاد یک پرداخت جدید از زرین‌پال؛ مبلغ به تومان دریافت و به ریال تبدیل می‌شود.

    🆕 extra: اطلاعات اضافی (date/time/doctor_key/doctor_name/full_name) که در تراکنش
    محلی ذخیره می‌شوند تا هندلر callback بعد از پرداخت بتواند نوبت متناظر را پیدا کند.
    """
    payload = {
        "merchant_id": settings.zarinpal_merchant_id,
        "amount": int(amount) * 10,  # زرین‌پال ریال می‌گیرد
        "description": description,
        "callback_url": callback_url,
        "metadata": {"user_id": str(user_id)},
    }

    try:
        response = requests.post(
            _request_url(),
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=_REQUEST_TIMEOUT,
        )
        body = response.json() if response.content else {}
    except (requests.RequestException, ValueError) as exc:
        logger.error("خطای شبکه در request_payment برای کاربر %s: %s", user_id, exc)
        return {"success": False, "error": "خطا در ارتباط با درگاه پرداخت"}

    data = body.get("data", {}) or {}
    if response.status_code == 200 and data.get("code") == 100:
        authority = data.get("authority", "")
        # 🔒 ممیزی (بخش C.1 و C.2): ثبت تراکنش اتمیک و «غیرشکست‌پذیر» است.
        # اگر ذخیره شکست بخورد، لینک پرداخت «صدور نمی‌شود» — چون verify بعدی
        # چنین تراکنشی را پیدا نمی‌کند و پول کاربر قابل‌تطبیق امن نخواهد بود.
        with _TX_LOCK:
            transactions = _load_transactions(user_id)
            transaction = {
                "authority": authority,
                "amount": int(amount),
                "description": description,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
            if extra:
                transaction.update(extra)
            transactions.append(transaction)
            saved = _save_transactions(user_id, transactions)
        if not saved:
            logger.error(
                "ذخیره‌ی تراکنش کاربر %s شکست خورد؛ لینک پرداخت صادر نشد (authority=%s).",
                user_id, authority,
            )
            return {
                "success": False,
                "error": "ثبت تراکنش روی سرور ممکن نشد؛ لطفاً چند لحظه بعد دوباره تلاش کنید",
            }
        return {
            "success": True,
            "url": _startpay_base() + authority,
            "authority": authority,
        }

    errors = body.get("errors", {})
    logger.warning("request_payment ناموفق برای کاربر %s: %s", user_id, errors or response.status_code)
    return {"success": False, "error": str(errors) if errors else f"خطای HTTP {response.status_code}"}


def verify_payment(user_id: int, authority: str, amount: int) -> dict[str, Any]:
    """تأیید پرداخت نزد زرین‌پال، با بررسی پرداخت تکراری و تطبیق مبلغ قبل از verify.

    🔒 ممیزی (بخش C.5 و C.8): کل چرخه «بررسی وضعیت → verify درگاه → ذخیره» داخل
    قفل است تا دو callback هم‌زمان برای یک authority نتوانند دو بار verify و دو
    رسید صادر کنند. callback دوم پس از اولی، وضعیت verified را می‌بیند و بی‌اثر
    برمی‌گردد (صفحه‌ی «قبلاً تأیید شده» در health.py).
    """
    with _TX_LOCK:
        transactions = _load_transactions(user_id)
        tx = _find_transaction(transactions, authority)

        if tx is None:
            return {"success": False, "error": "تراکنش یافت نشد"}

        if tx.get("status") == "verified":
            return {"success": False, "error": "این پرداخت قبلاً تایید شده است"}

        if tx.get("status") == "failed":
            return {"success": False, "error": "این پرداخت قبلاً ناموفق بوده است"}

        if int(tx.get("amount", 0)) != int(amount):
            tx["status"] = "failed"
            _save_transactions(user_id, transactions)
            logger.warning(
                "عدم تطابق مبلغ برای کاربر %s / authority %s: ثبت‌شده=%s، ورودی=%s",
                user_id, authority, tx.get("amount"), amount,
            )
            return {"success": False, "error": "مبلغ پرداختی با مبلغ ثبت‌شده مطابقت ندارد"}

        payload = {
            "merchant_id": settings.zarinpal_merchant_id,
            "amount": int(amount) * 10,  # زرین‌پال ریال می‌گیرد
            "authority": authority,
        }

        try:
            response = requests.post(
                _verify_url(),
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=_VERIFY_TIMEOUT,
            )
            body = response.json() if response.content else {}
        except (requests.RequestException, ValueError) as exc:
            # 🆕 ممیزی (بخش C.11): خطای شبکه وضعیت را failed «نمی‌کند» — تراکنش
            # در حالت pending می‌ماند تا callback تکراری/ری‌لود صفحه دوباره verify کند.
            logger.error("خطای شبکه در verify_payment برای کاربر %s: %s", user_id, exc)
            return {"success": False, "error": "خطا در ارتباط با درگاه پرداخت"}

        data = body.get("data", {}) or {}
        code = data.get("code")

        if response.status_code == 200 and code in (100, 101):
            ref_id = str(data.get("ref_id", ""))
            tx["status"] = "verified"
            tx["ref_id"] = ref_id
            tx["verified_at"] = datetime.now().isoformat()
            _save_transactions(user_id, transactions)
            return {"success": True, "ref_id": ref_id}

        errors = body.get("errors", {})
        tx["status"] = "failed"
        _save_transactions(user_id, transactions)
        logger.warning("verify_payment ناموفق برای کاربر %s: %s", user_id, errors or code)
        return {"success": False, "error": str(errors) if errors else f"کد خطا {code}"}