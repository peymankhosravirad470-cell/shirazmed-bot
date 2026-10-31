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

import json
import logging
import os
import tempfile
import threading
import traceback
from datetime import datetime
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

# 🌐 متن‌های سه‌زبانه صفحه پرداخت و پیام‌های بعد پرداخت.
# قبلاً همه فارسی هاردکد بود؛ حالا زبان کاربر از user_data خوانده می‌شود
# (همان که در ربات انتخاب کرده) و اگر در دسترس نبود، فارسی (رفتار مستند).
_HT: dict[str, dict[str, str]] = {
    "page_invalid_title": {"fa": "درخواست نامعتبر", "en": "Invalid Request", "ar": "طلب غير صالح"},
    "page_invalid_user": {"fa": "شناسه کاربر معتبر نیست.", "en": "The user ID is not valid.", "ar": "معرّف المستخدم غير صالح."},
    "page_invalid_authority": {"fa": "شناسه تراکنش (Authority) یافت نشد.", "en": "Transaction authority not found.", "ar": "لم يتم العثور على معرّف المعاملة."},
    "page_nok_title": {"fa": "پرداخت ناموفق", "en": "Payment Failed", "ar": "فشل الدفع"},
    "page_nok_body": {"fa": "پرداخت انجام نشد یا لغو شد. می‌توانید دوباره تلاش کنید.", "en": "Payment was not completed or was cancelled. You can try again.", "ar": "لم يتم الدفع أو تم إلغاؤه. يمكنك المحاولة مرة أخرى."},
    "page_notfound_title": {"fa": "تراکنش یافت نشد", "en": "Transaction Not Found", "ar": "لم يتم العثور على المعاملة"},
    "page_notfound_body": {"fa": "تراکنشی با این شناسه ثبت نشده است.", "en": "No transaction registered with this ID.", "ar": "لم يتم تسجيل أي معاملة بهذا المعرّف."},
    "page_already_title": {"fa": "قبلاً تأیید شده", "en": "Already Verified", "ar": "تم التحقق مسبقاً"},
    "page_already_body": {"fa": "این پرداخت قبلاً تأیید و ثبت شده بود.", "en": "This payment had already been verified and recorded.", "ar": "كان هذا الدفع قد تم التحقق منه وتسجيله مسبقاً."},
    "page_verifyfail_title": {"fa": "تأیید ناموفق", "en": "Verification Failed", "ar": "فشل التحقق"},
    "page_verifyfail_body": {"fa": "تأیید پرداخت نزد درگاه ناموفق بود.", "en": "Payment verification with the gateway failed.", "ar": "فشل التحقق من الدفع لدى بوابة الدفع."},
    "page_ok_title": {"fa": "پرداخت موفق", "en": "Payment Successful", "ar": "تم الدفع بنجاح"},
    "page_ok_body": {"fa": "پرداخت شما تأیید شد و نوبت شما قطعی گردید.\nرسید کامل در ربات برای شما ارسال شد.", "en": "Your payment was verified and your appointment is confirmed.\nThe full receipt has been sent to you in the bot.", "ar": "تم التحقق من دفعتك وتأكيد موعدك.\nتم إرسال الإيصال الكامل لك في البوت."},
    "page_ref": {"fa": "کد رهگیری", "en": "Tracking code", "ar": "رمز التتبع"},
    "page_error_title": {"fa": "خطای سرور", "en": "Server Error", "ar": "خطأ في الخادم"},
    "page_error_body": {"fa": "خطایی در پردازش پرداخت رخ داد.", "en": "An error occurred while processing the payment.", "ar": "حدث خطأ أثناء معالجة الدفع."},
    # 🆕 ممیزی (بخش C.6): پرداخت موفق ولی نهایی‌سازی نوبت شکست خورد — دیگر
    # «نوبت قطعی شد» به کاربر نمی‌گوییم؛ پیام صادقانه + پیگیری ادمین.
    "msg_paid_but_notbooked": {
        "fa": "✅ پرداخت شما تأیید شد، ولی در قطعی‌کردن نوبت خطایی پیش آمد.\nلطفاً نگران نباشید — مبلغ و نوبت شما ثبت شده و پشتیبانی به‌سرعت پیگیری می‌کند. 💙",
        "en": "✅ Your payment was verified, but finalizing the appointment hit an error.\nDon't worry — your payment and slot are recorded and support will follow up shortly. 💙",
        "ar": "✅ تم التحقق من دفعتك، لكن حدث خطأ أثناء تأكيد الموعد.\nلا تقلق — تم تسجيل دفعتك وموعدك وسيتابع الدعم الأمر قريباً. 💙",
    },
    "admin_paid_but_notbooked": {
        "fa": "⚠️ هشدار عملیاتی: پرداخت کاربر {user} تأیید شد (کد رهگیری {ref}) ولی تغییر وضعیت نوبت به paid شکست خورد (date={date} time={time}). نیازمند بررسی دستی است.",
        "en": "⚠️ Ops alert: payment of user {user} was verified (ref {ref}) but marking the appointment paid failed (date={date} time={time}). Manual follow-up needed.",
        "ar": "⚠️ تنبيه تشغيلي: تم التحقق من دفعة المستخدم {user} (رمز {ref}) لكن فشل تحديث حالة الموعد (date={date} time={time}). يلزم متابعة يدوية.",
    },
    "msg_nok": {"fa": "❌ پرداخت ناموفق یا لغو شد.\n\nنوبت شما آزاد شد. اگر مایل باشید می‌توانید دوباره از منوی اصلی رزرو کنید.", "en": "❌ Payment failed or was cancelled.\n\nYour appointment slot has been released. You can book again from the main menu.", "ar": "❌ فشل الدفع أو تم إلغاؤه.\n\nتم تحرير موعدك. يمكنك الحجز مرة أخرى من القائمة الرئيسية."},
    "msg_verify_failed": {"fa": "❌ تأیید پرداخت ناموفق بود.\n\nجزئیات: {error}\nدر صورت کسر وجه، مبلغ حداکثر تا ۷۲ ساعت به حساب شما بازمی‌گردد.\nبرای پیگیری با پشتیبانی تماس بگیرید.", "en": "❌ Payment verification failed.\n\nDetails: {error}\nIf the amount was deducted, it will be refunded within 72 hours at the latest.\nContact support for follow-up.", "ar": "❌ فشل التحقق من الدفع.\n\nالتفاصيل: {error}\nفي حال خصم المبلغ، سيُعاد إليك خلال 72 ساعة كحد أقصى.\nتواصل مع الدعم للمتابعة."},
    "msg_success_head": {"fa": "✅ پرداخت شما با موفقیت تأیید شد!", "en": "✅ Your payment was successfully verified!", "ar": "✅ تم التحقق من دفعتك بنجاح!"},
    "msg_ref": {"fa": "💳 کد رهگیری بانکی", "en": "💳 Bank tracking code", "ar": "💳 رمز التتبع البنكي"},
    "msg_doctor": {"fa": "👨‍⚕️ پزشک", "en": "👨‍⚕️ Doctor", "ar": "👨‍⚕️ الطبيب"},
    "msg_date": {"fa": "📅 تاریخ", "en": "📅 Date", "ar": "📅 التاريخ"},
    "msg_time": {"fa": "⏰ ساعت", "en": "⏰ Time", "ar": "⏰ الوقت"},
    "msg_amount": {"fa": "💰 مبلغ", "en": "💰 Amount", "ar": "💰 المبلغ"},
    "msg_arrive": {"fa": "لطفاً ۱۵ دقیقه قبل از نوبت در مطب حاضر باشید.", "en": "Please arrive at the clinic 15 minutes before your appointment.", "ar": "يرجى الحضور إلى العيادة قبل موعدك بـ 15 دقيقة."},
    "msg_brand": {"fa": "💙 شیراز مدیکال", "en": "💙 Shiraz Medical", "ar": "💙 شيراز الطبية"},
    "msg_toman": {"fa": "تومان", "en": "Toman", "ar": "تومان"},
    "pdf_caption": {"fa": "🧾 رسید نهایی نوبت شما", "en": "🧾 Your final appointment receipt", "ar": "🧾 إيصال موعدك النهائي"},
}


def _ht(lang: str, key: str, **kw: object) -> str:
    text = _HT.get(key, {}).get(lang) or _HT.get(key, {}).get("fa", key)
    if kw:
        try:
            text = text.format(**kw)
        except Exception:
            pass
    return text


def _user_lang(user_id: int) -> str:
    """زبان کاربر از user_data ربات (همان که در ربات انتخاب کرده).

    اگر Application هنوز bind نشده یا زبان ثبت نشده باشد → فارسی.
    """
    try:
        app = runtime.get_application()
        if app is not None:
            ud = app.user_data.get(int(user_id), {})
            if isinstance(ud, dict):
                lang = ud.get("lang", "fa")
                return lang if lang in ("fa", "en", "ar") else "fa"
    except Exception:
        pass
    return "fa"

PAGE_TMPL = """<!DOCTYPE html>
<html lang="{lang}" dir="{dir}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:Tahoma,Vazirmatn,sans-serif;background:#f1f5f9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:16px;padding:32px;max-width:420px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
.icon{{font-size:52px;margin-bottom:8px}} h1{{font-size:20px;color:{color};margin:8px 0}} p{{color:#475569;font-size:14px;line-height:2}}
.ref{{background:#f8fafc;border:1px dashed #94a3b8;border-radius:8px;padding:8px 12px;font-weight:bold;color:#0e7490}}
</style></head>
<body><div class="card"><div class="icon">{icon}</div><h1>{title}</h1><p>{body}</p>{extra}</div></body></html>"""


def _page(icon: str, title: str, body: str, color: str = "#0e7490", extra: str = "", lang: str = "fa") -> str:
    direction = "ltr" if lang == "en" else "rtl"
    return PAGE_TMPL.format(icon=icon, title=title, body=body, color=color, extra=extra, lang=lang, dir=direction)


def _handle_payment_callback(query: dict) -> tuple[int, str]:
    """هندل کامل callback زرین‌پال؛ خروجی: (http_status, html_page)."""
    user_id_raw = (query.get("user_id") or ["0"])[0]
    authority = (query.get("Authority") or [""])[0]
    status = (query.get("Status") or [""])[0].upper()

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return 400, _page("❓", _ht("fa", "page_invalid_title"), _ht("fa", "page_invalid_user"), "#dc2626", lang="fa")

    # 🌐 زبان کاربر (برای صفحه و پیام‌ها) — در صورت نبود → فارسی
    lang = _user_lang(user_id)

    if not authority:
        return 400, _page("❓", _ht(lang, "page_invalid_title"), _ht(lang, "page_invalid_authority"), "#dc2626", lang=lang)

    # ─── پرداخت ناموفق / لغو شده توسط کاربر ───
    if status != "OK":
        logger.info("Payment NOK for user %s authority=%s", user_id, authority)
        _release_pending_slot(user_id, authority)
        runtime.schedule_coroutine(_notify_user(user_id, _ht(lang, "msg_nok")))
        return 200, _page("⚠️", _ht(lang, "page_nok_title"), _ht(lang, "page_nok_body"), "#dc2626", lang=lang)

    # ─── پرداخت موفق: verify نزد زرین‌پال ───
    tx_amount = _get_tx_amount(user_id, authority)
    if tx_amount is None:
        return 400, _page("❓", _ht(lang, "page_notfound_title"), _ht(lang, "page_notfound_body"), "#dc2626", lang=lang)

    result = verify_payment(user_id, authority, tx_amount)

    if not result.get("success"):
        error = str(result.get("error", ""))
        if "قبلاً تایید" in error or "قبلاً تأیید" in error:
            # code 101 — قبلاً verify شده؛ بی‌ضرر است
            logger.info("Payment already verified user=%s authority=%s", user_id, authority)
            return 200, _page("ℹ️", _ht(lang, "page_already_title"), _ht(lang, "page_already_body"), "#0e7490", lang=lang)
        logger.warning("verify failed user=%s authority=%s error=%s", user_id, authority, error)
        runtime.schedule_coroutine(_notify_user(user_id, _ht(lang, "msg_verify_failed", error=error)))
        return 200, _page("⚠️", _ht(lang, "page_verifyfail_title"), _ht(lang, "page_verifyfail_body"), "#dc2626", lang=lang)

    ref_id = str(result.get("ref_id", ""))

    # ─── ثبت نوبت به‌عنوان پرداخت‌شده ───
    tx = _find_tx(user_id, authority)
    date = tx.get("date", "") if tx else ""
    time = tx.get("time", "") if tx else ""
    doctor_name = tx.get("doctor_name", "") if tx else ""
    full_name = str(tx.get("full_name", "") or "") if tx else ""
    paid_ok = False
    if date and time:
        paid_ok = mark_appointment_paid(user_id, date, time)
        if not paid_ok:
            # 🆕 ممیزی (C.6): یک تلاش مجدد — اگر callback هم‌زمان دیگری لحظه‌ای
            # قبل همان نوبت را دست‌کاری کرده باشد، خواندن تازه فایل ممکن است مشکل را حل کند.
            paid_ok = mark_appointment_paid(user_id, date, time)
    logger.info("Payment verified user=%s ref=%s appointment_paid=%s", user_id, ref_id, paid_ok)

    # ─── اطلاع‌رسانی به کاربر (پیام موفقیت + رسید متن + PDF) ───
    jalali = format_jalali(date) if date else ""
    if paid_ok:
        runtime.schedule_coroutine(_send_success_package(
            user_id, ref_id=ref_id, doctor_name=doctor_name, jalali=jalali, time=time,
            amount=tx_amount, authority=authority, lang=lang, full_name=full_name,
        ))
        # 🆕 مأموریت آیتم ۱۹: اولین پرداخت موفقِ معرفی‌شده → پاداش معرف فعال می‌شود
        # (ایزوله — هر شکستی جریان پرداخت را نمی‌شکند)
        try:
            from app.services import referral as _referral
            _referral.mark_referral_paid(user_id)
        except Exception as referral_error:
            logger.warning("referral mark_paid failed user=%s: %s", user_id, referral_error)
        # 🆕 مأموریت آیتم ۱۴: زمان‌بندی یادآور نوبت (۲۴ و ۲ ساعت قبل) — ایزوله
        try:
            from app.services import apt_reminders as _apt_reminders
            app_obj = runtime.get_application()
            if app_obj is not None and date and time:
                _apt_reminders.schedule_appointment_reminders(
                    app_obj,
                    {"status": "paid", "date": date, "time": time,
                     "doctor_name": doctor_name, "lang": lang, "user_id": user_id},
                    user_id,
                )
        except Exception as reminder_error:
            logger.warning("apt reminder scheduling failed user=%s: %s", user_id, reminder_error)
    else:
        # 🆕 ممیزی (C.6): پول تایید شده ولی قطعی‌سازی نوبت شکست خورده → هرگز
        # «نوبت قطعی شد» نمی‌گوییم؛ پیام صادقانه + هشدار عملیاتی برای ادمین.
        runtime.schedule_coroutine(_notify_user(user_id, _ht(lang, "msg_paid_but_notbooked")))
        runtime.schedule_coroutine(_notify_admin_paid_but_notbooked(
            user_id=user_id, ref_id=ref_id, date=date, time=time,
        ))
        logger.error(
            "Payment verified but appointment NOT finalized: user=%s authority=%s date=%s time=%s",
            user_id, authority, date, time,
        )

    extra_html = f'<div class="ref">{_ht(lang, "page_ref")}: {ref_id}</div>' if ref_id else ""
    return 200, _page(
        "✅", _ht(lang, "page_ok_title"), _ht(lang, "page_ok_body"),
        "#16a34a", extra_html, lang=lang,
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


async def _notify_admin_paid_but_notbooked(*, user_id: int, ref_id: str, date: str, time: str) -> None:
    """🆕 ممیزی (C.6): هشدار عملیاتی برای ادمین وقتی پرداخت تایید شده ولی نوبت قطعی نشده."""
    from config import settings as _settings
    admin_id = getattr(_settings, "admin_chat_id", None)
    if not admin_id:
        logger.error("ADMIN_CHAT_ID تنظیم نشده؛ هشدار paid-but-not-booked برای ادمین ارسال نشد.")
        return
    app = runtime.get_application()
    if app is None:
        return
    try:
        from app.services.booking import format_jalali as _fj
        await app.bot.send_message(
            chat_id=admin_id,
            text=_ht("fa", "admin_paid_but_notbooked", user=user_id, ref=ref_id or "—",
                     date=_fj(date) if date else "—", time=time or "—"),
        )
    except Exception as error:  # pragma: no cover
        logger.error("خطا در ارسال هشدار ادمین: %s", error)


async def _send_success_package(
    user_id: int, *, ref_id: str, doctor_name: str, jalali: str, time: str,
    amount: int, authority: str, lang: str = "fa", full_name: str = "",
) -> None:
    """پیام موفقیت + رسید متن + رسید PDF (پس از verify — نه قبل از پرداخت!).

    🌐 پیام‌ها به زبان کاربر؛ رسید PDF فعلاً فارسی است (مستند در گزارش بازبینی).
    🆕 ممیزی (E): نام واقعی بیمار از تراکنش به رسید می‌رود (قبلاً رشته‌ی خالی
    هاردکد بود). اگر شکست ساخت PDF رخ دهد، وضعیت پرداخت «موفق» دست‌نخورده
    می‌ماند و فقط در لاگ امن ثبت می‌شود.
    """
    app = runtime.get_application()
    if app is None:
        return
    try:
        lines = [_ht(lang, "msg_success_head"), ""]
        lines.append(f"{_ht(lang, 'msg_ref')}: {ref_id}")
        if doctor_name:
            lines.append(f"{_ht(lang, 'msg_doctor')}: {doctor_name}")
        if jalali:
            lines.append(f"{_ht(lang, 'msg_date')}: {jalali}")
        if time:
            lines.append(f"{_ht(lang, 'msg_time')}: {time}")
        if amount:
            lines.append(f"{_ht(lang, 'msg_amount')}: {amount:,} {_ht(lang, 'msg_toman')}")
        lines += ["", _ht(lang, "msg_arrive"), _ht(lang, "msg_brand")]
        await app.bot.send_message(chat_id=user_id, text="\n".join(lines))

        appointment = {
            # 🆕 ممیزی (E): فیلدهای واقعی تراکنش؛ هیچ داده‌ی ساختگی — فیلد ناموجود
            # در رسید به‌صورت «-» نمایش داده می‌شود (رفتار receipt.py).
            "full_name": full_name, "doctor_name": doctor_name,
            "date": jalali, "time": time, "amount": amount,
            "tracking_code": ref_id or authority[:12],
            "user_id": user_id,
        }
        receipt_text = generate_receipt_text(appointment, {})
        await app.bot.send_message(chat_id=user_id, text=receipt_text, parse_mode="HTML")

        import asyncio
        try:
            pdf_path = await asyncio.to_thread(generate_receipt_pdf, appointment, {})
        except Exception as pdf_error:
            # 🆕 ممیزی (E): شکست PDF وضعیت پرداخت را تغییر نمی‌دهد؛ فقط لاگ امن.
            logger.error("PDF generation failed for user=%s (payment stays verified): %s", user_id, pdf_error)
            return
        with open(pdf_path, "rb") as pdf_file:
            await app.bot.send_document(
                chat_id=user_id, document=pdf_file,
                filename=os.path.basename(pdf_path), caption=_ht(lang, "pdf_caption"),
            )
    except Exception as error:  # pragma: no cover
        logger.error("خطا در ارسال بسته‌ی موفقیت به %s: %s", user_id, error)
        traceback.print_exc()


class _HealthHandler(BaseHTTPRequestHandler):
    """روتر ساده: /health و /payment/callback."""

    def do_GET(self) -> None:  # noqa: N802 (امضای الزامی http.server)
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/health"):
            # 🐛 رگرسیون کرش لیارا (۱۴۰۴/۰۸/۰۸): «ذخیره‌سازی یادآور انجام نشد» ریشه
            # دیسکی داشت که از بیرون دیده نمی‌شد. حالا /health وضعیت واقعی
            # نوشتنِ دیسک را گزارش می‌کند (بدون هیچ داده‌ی کاربر — فقط مجوز/اندازه).
            try:
                body = json.dumps(
                    {"status": "ok", "storage": storage_diagnostics()},
                    ensure_ascii=False,
                )
                self._respond(200, body, content_type="application/json; charset=utf-8")
            except Exception as error:  # pragma: no cover — سلامت هرگز نباید ۵۰۰ بدهد
                logger.error("storage diagnostics failed: %s", error)
                self._respond(200, "OK")
            return
        if parsed.path == "/payment/callback":
            try:
                http_status, html = _handle_payment_callback(parse_qs(parsed.query))
                self._respond(http_status, html, content_type="text/html; charset=utf-8")
            except Exception as error:  # pragma: no cover
                logger.error("خطای هندل callback پرداخت: %s", error)
                traceback.print_exc()
                self._respond(500, _page("⚠️", _ht("fa", "page_error_title"), _ht("fa", "page_error_body"), "#dc2626", lang="fa"))
            return
        # 🆕 مأموریت آیتم ۲۰: API عمومی فقط‌خواندنی برای وب‌سایت/اپ‌های آینده.
        # فقط دادهٔ عمومی (بیمارستان‌ها/نام پزشکان) — هیچ دادهٔ بیمار؛ POST ندارد.
        if parsed.path == "/api/v1/status":
            self._respond(200, json.dumps(
                {"status": "ok", "service": "shirazmed-bot",
                 "time": datetime.now().isoformat(timespec="seconds")},
                ensure_ascii=False,
            ), content_type="application/json; charset=utf-8")
            return
        if parsed.path in ("/api/v1/hospitals", "/api/v1/doctors"):
            try:
                if parsed.path.endswith("hospitals"):
                    from app.handlers.callbacks import load_json as _load_json
                    items = _load_json("hospitals.json")
                    if not isinstance(items, list):
                        items = []
                else:
                    from app.services import doctor_loader as _dl
                    items = []
                    for spec in _dl.load_specialties():
                        key = spec.get("key") if isinstance(spec, dict) else None
                        if not key:
                            continue
                        for doc in _dl.load_doctors(key):
                            if isinstance(doc, dict):
                                items.append({
                                    "name": doc.get("name_fa", ""),
                                    "specialty": doc.get("specialty_fa", ""),
                                })
                self._respond(200, json.dumps(
                    {"count": len(items), "items": items}, ensure_ascii=False,
                ), content_type="application/json; charset=utf-8")
            except Exception as error:  # pragma: no cover
                logger.error("api endpoint failed: %s", error)
                self._respond(500, json.dumps({"error": "internal"}), content_type="application/json; charset=utf-8")
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


def _probe_writable(directory: str) -> tuple[bool, str | None]:
    """آزمون واقعی نوشتن در یک پوشه (ساخت + حذف فایل موقت) — بدون هیچ داده‌ی کاربر."""
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".probe-", suffix=".tmp")
        try:
            os.write(fd, b"probe")
        finally:
            os.close(fd)
        os.unlink(tmp)
        return True, None
    except OSError as error:
        return False, f"{type(error).__name__}: {error.strerror or error}"


def storage_diagnostics() -> dict:
    """🩺 تشخیص دیسک برای خطای «ذخیره‌سازی یادآور انجام نشد».

    عمداً فقط متادیتا: مسیرها، مجوز نوشتن، errno، اندازه/زمان فایل داروها —
    هیچ محتوایی از داده‌ی کاربران (نام دارو/شناسه) در پاسخ نیست.
    """
    from config import DATA_DIR as data_dir
    from app.handlers import meds as meds_mod

    info: dict = {
        "cwd": os.getcwd(),
        "data_dir": data_dir,
    }
    ok, err = _probe_writable(data_dir)
    info["data_dir_writable"] = ok
    if err:
        info["data_dir_error"] = err

    fallback_dir = meds_mod.FALLBACK_DIR
    info["fallback_dir"] = fallback_dir
    ok, err = _probe_writable(fallback_dir)
    info["fallback_writable"] = ok
    if err:
        info["fallback_error"] = err

    meds_file = meds_mod.MEDS_FILE
    try:
        if os.path.isfile(meds_file):
            stat = os.stat(meds_file)
            info["meds_file_exists"] = True
            info["meds_file_size"] = stat.st_size
            info["meds_file_mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        else:
            info["meds_file_exists"] = False
    except OSError as error:
        info["meds_file_exists"] = None
        info["meds_file_error"] = f"{type(error).__name__}: {error.strerror or error}"
    return info


def start_health_server() -> None:
    """سرور HTTP روی پورت PORT (پیش‌فرض 8080) در یک ترد پس‌زمینه اجرا می‌کند."""
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health-server")
    thread.start()
    logger.info("سرور health + payment-callback روی پورت %s بالا آمد.", port)