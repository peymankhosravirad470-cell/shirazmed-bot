# -*- coding: utf-8 -*-
"""
سرور HTTP اپ روی پورت لیارا با دو وظیفه:

1) health-check: پاسخ 200 به پینگ‌های لیارا (GET /health)
2) callback پرداخت زرین‌پال (GET /payment/callback):
   بعد از پرداخت، زرین‌پال کاربر را به این آدرس برمی‌گرداند:
       {PUBLIC_BASE_URL}/payment/callback?user_id=X&Authority=A&Status=OK|NOK
   این سرور:
   - Status=NOK → لغو نوبت pending + پیام «پرداخت ناموفق» به کاربر
   - Status=OK  → verify نزد زرین‌پال → در صورت موفقیت: paid کردن نوبت
                  + ارسال پیام موفقیت + رسید متن + رسید PDF به کاربر

🆕 فیکس بحرانی: قبلاً verify_payment و mark_appointment_paid در هیچ‌جای کد فراخوانی
نمی‌شدند — یعنی کاربر پول پرداخت می‌کرد ولی نوبتش بعد از ۱۵ دقیقه منقضی می‌شد!
"""

from __future__ import annotations

import logging
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from app import runtime
from app.services.booking import (
    cancel_appointment,
    format_jalali,
    mark_appointment_paid,
)
from app.services.payment import verify_payment
from app.services.receipt import generate_receipt_pdf, generate_receipt_text

logger = logging.getLogger(__name__)

PAGE_TMPL = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:Tahoma,Vazirmatn,sans-serif;background:#f1f5f9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:16px;padding:32px;max-width:420px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
.icon{{font-size:52px;margin-bottom:8px}} h1{{font-size:20px;color:{color};margin:8px 0}} p{{color:#475569;font-size:14px;line-height:2}}
.ref{{background:#f8fafc;border:1px dashed #94a3b8;border-radius:8px;padding:8px 12px;font-weight:bold;color:#0e7490}}
</style></head>
<body><div class="card"><div class="icon">{icon}</div><h1>{title}</h1><p>{body}</p>{extra}</div></body></html>"""


def _page(icon: str, title: str, body: str, color: str = "#0e7490", extra: str = "") -> str:
    return PAGE_TMPL.format(icon=icon, title=title, body=body, color=color, extra=extra)


def _handle_payment_callback(query: dict) -> tuple[int, str]:
    """هندل کامل callback زرین‌پال؛ خروجی: (http_status, html_page)."""
    user_id_raw = (query.get("user_id") or ["0"])[0]
    authority = (query.get("Authority") or [""])[0]
    status = (query.get("Status") or [""])[0].upper()

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return 400, _page("❓", "درخواست نامعتبر", "شناسه کاربر معتبر نیست.", "#dc2626")

    if not authority:
        return 400, _page("❓", "درخواست نامعتبر", "شناسه تراکنش (Authority) یافت نشد.", "#dc2626")

    # ─── پرداخت ناموفق / لغو شده توسط کاربر ───
    if status != "OK":
        logger.info("Payment NOK for user %s authority=%s", user_id, authority)
        _release_pending_slot(user_id, authority)
        runtime.schedule_coroutine(_notify_user(user_id, (
            "❌ پرداخت ناموفق یا لغو شد.\n\n"
            "نوبت شما آزاد شد. اگر مایل باشید می‌توانید دوباره از منوی اصلی رزرو کنید."
        )))
        return 200, _page("⚠️", "پرداخت ناموفق", "پرداخت انجام نشد یا لغو شد. می‌توانید دوباره تلاش کنید.", "#dc2626")

    # ─── پرداخت موفق: verify نزد زرین‌پال ───
    tx_amount = _get_tx_amount(user_id, authority)
    if tx_amount is None:
        return 400, _page("❓", "تراکنش یافت نشد", "تراکنشی با این شناسه ثبت نشده است.", "#dc2626")

    result = verify_payment(user_id, authority, tx_amount)

    if not result.get("success"):
        error = str(result.get("error", ""))
        if "قبلاً تایید" in error or "قبلاً تأیید" in error:
            # code 101 — قبلاً verify شده؛ بی‌ضرر است
            logger.info("Payment already verified user=%s authority=%s", user_id, authority)
            return 200, _page("ℹ️", "قبلاً تأیید شده", "این پرداخت قبلاً تأیید و ثبت شده بود.", "#0e7490")
        logger.warning("verify failed user=%s authority=%s error=%s", user_id, authority, error)
        runtime.schedule_coroutine(_notify_user(user_id, (
            "❌ تأیید پرداخت ناموفق بود.\n\n"
            f"جزئیات: {error}\n"
            "در صورت کسر وجه، مبلغ حداکثر تا ۷۲ ساعت به حساب شما بازمی‌گردد.\n"
            "برای پیگیری با پشتیبانی تماس بگیرید."
        )))
        return 200, _page("⚠️", "تأیید ناموفق", "تأیید پرداخت نزد درگاه ناموفق بود.", "#dc2626")

    ref_id = str(result.get("ref_id", ""))

    # ─── ثبت نوبت به‌عنوان پرداخت‌شده ───
    tx = _find_tx(user_id, authority)
    date = tx.get("date", "") if tx else ""
    time = tx.get("time", "") if tx else ""
    doctor_name = tx.get("doctor_name", "") if tx else ""
    paid_ok = False
    if date and time:
        paid_ok = mark_appointment_paid(user_id, date, time)
    logger.info("Payment verified user=%s ref=%s appointment_paid=%s", user_id, ref_id, paid_ok)

    # ─── اطلاع‌رسانی به کاربر (پیام موفقیت + رسید متن + PDF) ───
    jalali = format_jalali(date) if date else ""
    runtime.schedule_coroutine(_send_success_package(
        user_id, ref_id=ref_id, doctor_name=doctor_name, jalali=jalali, time=time,
        amount=tx_amount, authority=authority,
    ))

    extra_html = f'<div class="ref">کد رهگیری: {ref_id}</div>' if ref_id else ""
    return 200, _page(
        "✅", "پرداخت موفق",
        "پرداخت شما تأیید شد و نوبت شما قطعی گردید.\nرسید کامل در ربات برای شما ارسال شد.",
        "#16a34a", extra_html,
    )


# ---------------------------------------------------------------------------
# ابزارهای کمکی (blocking — در ترد health اجرا می‌شوند)
# ---------------------------------------------------------------------------

def _find_tx(user_id: int, authority: str) -> dict | None:
    from app.services.payment import _load_transactions
    for tx in _load_transactions(user_id):
        if tx.get("authority") == authority:
            return tx
    return None


def _get_tx_amount(user_id: int, authority: str) -> int | None:
    tx = _find_tx(user_id, authority)
    if not tx:
        return None
    try:
        return int(tx.get("amount", 0))
    except (TypeError, ValueError):
        return None


def _release_pending_slot(user_id: int, authority: str) -> None:
    """در صورت پرداخت ناموفق، اسلات pending آزاد می‌شود."""
    try:
        tx = _find_tx(user_id, authority)
        if tx and tx.get("date") and tx.get("time"):
            cancel_appointment(date=tx["date"], time=tx["time"], user_id=user_id)
    except Exception as error:  # pragma: no cover
        logger.warning("خطا در آزادسازی اسلات: %s", error)


# ---------------------------------------------------------------------------
# کوروتین‌ها (روی event loop ربات اجرا می‌شوند)
# ---------------------------------------------------------------------------

async def _notify_user(user_id: int, text: str) -> None:
    app = runtime.get_application()
    if app is None:
        logger.warning("Application هنوز bind نشده؛ پیام به %s ارسال نشد.", user_id)
        return
    try:
        await app.bot.send_message(chat_id=user_id, text=text)
    except Exception as error:  # pragma: no cover
        logger.error("خطا در ارسال پیام به %s: %s", user_id, error)


async def _send_success_package(
    user_id: int, *, ref_id: str, doctor_name: str, jalali: str, time: str,
    amount: int, authority: str,
) -> None:
    """پیام موفقیت + رسید متن + رسید PDF (پس از verify — نه قبل از پرداخت!)."""
    app = runtime.get_application()
    if app is None:
        return
    try:
        lines = [
            "✅ پرداخت شما با موفقیت تأیید شد!",
            "",
            f"💳 کد رهگیری بانکی: {ref_id}",
        ]
        if doctor_name:
            lines.append(f"👨‍⚕️ پزشک: {doctor_name}")
        if jalali:
            lines.append(f"📅 تاریخ: {jalali}")
        if time:
            lines.append(f"⏰ ساعت: {time}")
        if amount:
            lines.append(f"💰 مبلغ: {amount:,} تومان")
        lines += ["", "لطفاً ۱۵ دقیقه قبل از نوبت در مطب حاضر باشید.", "💙 شیراز مدیکال"]
        await app.bot.send_message(chat_id=user_id, text="\n".join(lines))

        appointment = {
            "full_name": "", "doctor_name": doctor_name,
            "date": jalali, "time": time, "amount": amount,
            "tracking_code": ref_id or authority[:12],
            "user_id": user_id,
        }
        receipt_text = generate_receipt_text(appointment, {})
        await app.bot.send_message(chat_id=user_id, text=receipt_text, parse_mode="HTML")

        import asyncio
        pdf_path = await asyncio.to_thread(generate_receipt_pdf, appointment, {})
        with open(pdf_path, "rb") as pdf_file:
            await app.bot.send_document(
                chat_id=user_id, document=pdf_file,
                filename=os.path.basename(pdf_path), caption="🧾 رسید نهایی نوبت شما",
            )
    except Exception as error:  # pragma: no cover
        logger.error("خطا در ارسال بسته‌ی موفقیت به %s: %s", user_id, error)
        traceback.print_exc()


class _HealthHandler(BaseHTTPRequestHandler):
    """روتر ساده: /health و /payment/callback."""

    def do_GET(self) -> None:  # noqa: N802 (امضای الزامی http.server)
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/health"):
            self._respond(200, "OK")
            return
        if parsed.path == "/payment/callback":
            try:
                http_status, html = _handle_payment_callback(parse_qs(parsed.query))
                self._respond(http_status, html, content_type="text/html; charset=utf-8")
            except Exception as error:  # pragma: no cover
                logger.error("خطای هندل callback پرداخت: %s", error)
                traceback.print_exc()
                self._respond(500, _page("⚠️", "خطای سرور", "خطایی در پردازش پرداخت رخ داد.", "#dc2626"))
            return
        self._respond(404, "Not Found")

    def _respond(self, code: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def start_health_server() -> None:
    """سرور HTTP روی پورت PORT (پیش‌فرض 8080) در یک ترد پس‌زمینه اجرا می‌کند."""
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health-server")
    thread.start()
    logger.info("سرور health + payment-callback روی پورت %s بالا آمد.", port)