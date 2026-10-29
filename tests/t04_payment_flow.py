# -*- coding: utf-8 -*-
"""T04 — چرخه‌ی کامل پرداخت (بخش ۳.۷-۳.۱۱ و بخش C): مبلغ، ناموفق/لغو، callback تکراری،
شکست ذخیره تراکنش، شکست ثبت نوبت بعد از پرداخت موفق، خطای شبکه، قفل هم‌زمانی."""
import asyncio
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import REC, Result, build_app, process, tmp_dir  # noqa: E402

from app.services import booking as bs  # noqa: E402
from app.services import payment as pm  # noqa: E402

DATE = "2030-02-11"
AMOUNT = 100_000  # تومان


def tx_extra(user_id):
    return {"date": DATE, "time": "09:00", "doctor_key": "cardio:doc_001",
            "doctor_name": "دکتر تست", "full_name": "بیمار تست"}


class FakeGateway:
    """شبیه‌ساز زرین‌پال — request/verify با کدهای واقعی v4."""

    def __init__(self) -> None:
        self.request_fail = False
        self.verify_code = 100
        self.network_error = False
        self.authorities: set[str] = set()
        self.verify_calls = 0
        self.verify_payloads: list[dict] = []
        self.request_payloads: list[dict] = []

    def post(self, url, json=None, headers=None, timeout=None):  # noqa: A002
        class R:
            def __init__(self, body, status=200):
                self._body = body
                self.status_code = status
                self.content = b"1"

            def json(self):
                return self._body
        if self.network_error:
            raise pm.requests.ConnectionError("boom")
        if url.endswith("request.json"):
            self.request_payloads.append(dict(json or {}))
            if self.request_fail:
                return R({"errors": {"code": -9, "message": "invalid merchant"}})
            authority = f"A000{len(self.authorities) + 1}"
            self.authorities.add(authority)
            return R({"data": {"code": 100, "authority": authority}})
        # verify
        self.verify_calls += 1
        self.verify_payloads.append(dict(json or {}))
        authority = (json or {}).get("authority")
        if authority not in self.authorities:
            return R({"data": {}, "errors": {"code": -11}}, status=200)
        if self.verify_code in (100, 101):
            return R({"data": {"code": self.verify_code, "ref_id": 777777}})
        return R({"data": {}, "errors": {"code": self.verify_code}}, status=200)


def appt(user_id, status="pending"):
    return {"user_id": user_id, "full_name": "بیمار تست", "national_code": "0079345948",
            "spec_key": "cardio", "doctor_key": "cardio:doc_001", "doctor_id": "doc_001",
            "doctor_name": "دکتر تست", "date": DATE, "time": "09:00", "amount": AMOUNT,
            "commission_rate": 0.0, "commission_amount": 0, "doctor_share": AMOUNT,
            "status": status}


async def main() -> int:
    r = Result()
    app = await build_app()
    gw = FakeGateway()

    with patch.object(pm.requests, "post", side_effect=lambda *a, **k: gw.post(*a, **k)):
        # ── ۳.۷ پرداخت موفق + تطبیق مبلغ (تومان → ریال ×10) ──
        res = pm.request_payment(501, AMOUNT, "نوبت تست", "https://x.example/cb", extra=tx_extra(501))
        r.check("request_payment موفق", res.get("success") is True, str(res))
        r.check("لینک StartPay", res.get("url", "").startswith("https://sandbox.zarinpal.com/pg/StartPay/"), res.get("url", ""))
        txs = pm._load_transactions(501)
        r.check("مبلغ ذخیره‌شده = تومان (100000)", txs[-1]["amount"] == AMOUNT, str(txs[-1]["amount"]))
        vres = pm.verify_payment(501, res["authority"], AMOUNT)
        r.check("verify موفق", vres.get("success") is True, str(vres))
        r.check("ref_id برگشت", str(vres.get("ref_id", "")) != "")

        # مبلغ به درگاه ریالی است — request و verify هر دو amount×10
        r.check("مبلغ request = amount×10 (ریال)", gw.request_payloads and gw.request_payloads[-1].get("amount") == AMOUNT * 10, str(gw.request_payloads[-1] if gw.request_payloads else None))
        r.check("مبلغ verify = amount×10 (ریال)", gw.verify_payloads and gw.verify_payloads[-1].get("amount") == AMOUNT * 10, str(gw.verify_payloads[-1] if gw.verify_payloads else None))

        # ── callback تکراری (بخش ۳.۹ / C.5) ──
        vres2 = pm.verify_payment(501, res["authority"], AMOUNT)
        r.check("verify تکراری رد می‌شود", vres2.get("success") is False and "قبلاً" in vres2.get("error", ""), str(vres2))

        # ── ۳.۸ پرداخت ناموفق (درگاه کد خطا بدهد) ──
        res2 = pm.request_payment(502, AMOUNT, "نوبت ۲", "https://x.example/cb", extra=tx_extra(502))
        gw.verify_code = -51  # failed at gateway
        vfail = pm.verify_payment(502, res2["authority"], AMOUNT)
        r.check("verify ناموفق گزارش می‌شود", vfail.get("success") is False, str(vfail))
        txs2 = pm._load_transactions(502)
        r.check("وضعیت تراکنش failed شد", txs2[-1]["status"] == "failed")
        gw.verify_code = 100
        vfail2 = pm.verify_payment(502, res2["authority"], AMOUNT)
        r.check("تراکنش failed دوباره verify نمی‌شود", vfail2.get("success") is False)

        # ── مبلغ نامنطبق (بخش C.11) ──
        res3 = pm.request_payment(503, AMOUNT, "نوبت ۳", "https://x.example/cb", extra=tx_extra(503))
        vmis = pm.verify_payment(503, res3["authority"], AMOUNT + 5)
        r.check("مبلغ نامنطبق رد می‌شود", vmis.get("success") is False and "مطابقت" in vmis.get("error", ""), str(vmis))
        r.check("تراکنشِ مبلغ نامنطبق failed شد", pm._load_transactions(503)[-1]["status"] == "failed")

        # ── تراکنش ناشناخته ──
        vunk = pm.verify_payment(999, "UNKNOWN_AUTH", AMOUNT)
        r.check("تراکنش ناشناخته → یافت نشد", vunk.get("success") is False and "یافت نشد" in vunk.get("error", ""), str(vunk))

        # ── خطای شبکه: وضعیت pending می‌ماند (قابل retry) ──
        res4 = pm.request_payment(504, AMOUNT, "نوبت ۴", "https://x.example/cb", extra=tx_extra(504))
        gw.network_error = True
        vnet = pm.verify_payment(504, res4["authority"], AMOUNT)
        r.check("خطای شبکه → شکست گزارش می‌شود", vnet.get("success") is False)
        r.check("خطای شبکه → وضعیت failed نمی‌شود (pending می‌ماند)", pm._load_transactions(504)[-1]["status"] == "pending")
        gw.network_error = False
        vnet2 = pm.verify_payment(504, res4["authority"], AMOUNT)
        r.check("retry بعد از رفع شبکه موفق", vnet2.get("success") is True, str(vnet2))

        # ── ۳.۱۱ شکست ذخیره‌ی تراکنش → لینک پرداخت صادر نمی‌شود (C.1/C.2) ──
        def failing_os_replace(src, dst):
            raise OSError("disk full")
        real_replace = os.replace
        authority_before = set(pm._load_transactions(505) and [t.get("authority") for t in pm._load_transactions(505)])
        try:
            os.replace = failing_os_replace  # type: ignore
            res5 = pm.request_payment(505, AMOUNT, "نوبت ۵", "https://x.example/cb", extra=tx_extra(505))
        finally:
            os.replace = real_replace  # type: ignore
        r.check("شکست ذخیره → success=False (لینک صادر نشد)", res5.get("success") is False, str(res5))
        txs5 = pm._load_transactions(505)
        new_authorities = [t.get("authority") for t in txs5 if t.get("authority") not in authority_before]
        r.check("تراکنشِ ذخیره‌نشده در فایل ثبت نشد (غایب است)", not new_authorities, str(new_authorities))

        # ── ۳.۱۰ پرداخت موفق + شکست ثبت نوبت (C.6) → پیام صادقانه ──
        bs.save_appointments([])  # نوبتی وجود ندارد → mark_appointment_paid شکست می‌خورد
        res6 = pm.request_payment(506, AMOUNT, "نوبت ۶", "https://x.example/cb", extra=tx_extra(506))
        REC.reset()
        from app import health
        status, html = health._handle_payment_callback({"user_id": ["506"], "Authority": [res6["authority"]], "Status": ["OK"]})
        r.check("callback OK → صفحه 200 موفق", status == 200)
        await asyncio.sleep(0.4)  # پیام‌ها async روی event loop ارسال می‌شوند
        user_msgs = [d.get("text", "") for d in REC.sent_to(506)]
        r.check("پیام «پرداخت تایید ولی نوبت قطعی نشد» به کاربر رفت", any("قطعی‌کردن نوبت" in t or "خطایی پیش آمد" in t for t in user_msgs), str([t[:60] for t in user_msgs]))
        admin_msgs = [d.get("text", "") for d in REC.sent_to(111)]
        r.check("هشدار عملیاتی به ادمین رفت", any("هشدار عملیاتی" in t for t in admin_msgs), str([t[:60] for t in admin_msgs]))
        # و پیام موفقیت کامل «نوبت قطعی گردید» نرفته باشد
        r.check("پیام دروغ «نوبت قطعی شد» ارسال نشد", not any("msg_success_head" in t and "قطعی" in t and "خطا" not in t for t in user_msgs))

        # ── چرخه‌ی کامل سالم: callback OK با نوبت واقعی → paid + رسید + PDF ──
        bs.save_appointments([appt(507)])
        res7 = pm.request_payment(507, AMOUNT, "نوبت ۷", "https://x.example/cb", extra=tx_extra(507))
        REC.reset()
        status, html = health._handle_payment_callback({"user_id": ["507"], "Authority": [res7["authority"]], "Status": ["OK"]})
        r.check("callback سالم → 200", status == 200)
        r.check("نوبت paid شد", all(a["status"] == "paid" for a in bs.load_appointments() if a["user_id"] == 507))
        # پیام‌های هم‌زمان: بعد از schedule_coroutine روی loop واقعی — اجرا داده شود
        await asyncio.sleep(0.3)
        user_msgs = [d.get("text", "") for d in REC.sent_to(507)]
        r.check("پیام موفقیت به کاربر رسید", any("تأیید شد" in t or "تایید شد" in t for t in user_msgs), str([t[:50] for t in user_msgs]))
        r.check("رسید متن با نام واقعی بیمار", any("بیمار تست" in t for t in user_msgs), str([t[:50] for t in user_msgs]))
        r.check("رسید PDF ارسال شد", len(REC.documents()) >= 1, str(len(REC.documents())))

        # ── Status=NOK → لغو نوبت pending + پیام ناموفق (بخش C.11) ──
        bs.save_appointments([appt(508)])
        res8 = pm.request_payment(508, AMOUNT, "نوبت ۸", "https://x.example/cb", extra=tx_extra(508))
        REC.reset()
        status, html = health._handle_payment_callback({"user_id": ["508"], "Authority": [res8["authority"]], "Status": ["NOK"]})
        r.check("NOK → 200 صفحه‌ی ناموفق", status == 200)
        rows = bs.load_appointments()
        r.check("NOK → نوبت pending آزاد شد", not any(a["user_id"] == 508 for a in rows), str(rows))
        await asyncio.sleep(0.2)
        user_msgs = [d.get("text", "") for d in REC.sent_to(508)]
        r.check("پیام پرداخت ناموفق به کاربر", any("ناموفق" in t for t in user_msgs), str(user_msgs))

        # ── callback تکراری در سطح health: پیام/رسید دوباره نمی‌رود (C.5) ──
        REC.reset()
        before_docs = 0
        status, html = health._handle_payment_callback({"user_id": ["507"], "Authority": [res7["authority"]], "Status": ["OK"]})
        await asyncio.sleep(0.2)
        r.check("callback تکراری → صفحه «قبلاً تأیید شده»", "قبلاً" in html or "Already" in html or "مسبقاً" in html, html[:100])
        r.check("callback تکراری → هیچ پیام/رسید جدیدی نرفت", len(REC.sent_to(507)) == 0 and len(REC.documents()) == 0, f"{len(REC.sent_to(507))} msgs")

        # ── رقابت هم‌زمان دو verify (C.8) → فقط یکی پیام می‌فرستد ──
        bs.save_appointments([appt(509)])
        res9 = pm.request_payment(509, AMOUNT, "نوبت ۹", "https://x.example/cb", extra=tx_extra(509))
        REC.reset()
        v1, v2 = await asyncio.gather(
            asyncio.to_thread(pm.verify_payment, 509, res9["authority"], AMOUNT),
            asyncio.to_thread(pm.verify_payment, 509, res9["authority"], AMOUNT),
        )
        successes = [v for v in (v1, v2) if v.get("success")]
        r.check("دو verify هم‌زمان → فقط یکی موفق", len(successes) == 1, f"{v1}|{v2}")

        # ── رقابت هم‌زمان دو request_payment → هر دو تراکنش حفظ شوند (C.2) ──
        REC.reset()
        rq1, rq2 = await asyncio.gather(
            asyncio.to_thread(pm.request_payment, 510, AMOUNT, "d1", "https://x.example/cb"),
            asyncio.to_thread(pm.request_payment, 510, AMOUNT, "d2", "https://x.example/cb"),
        )
        txs10 = pm._load_transactions(510)
        r.check("دو request هم‌زمان → هر دو تراکنش ذخیره شد (بدون گم‌شدن)", rq1.get("success") and rq2.get("success") and len(txs10) >= 2, str(len(txs10)))

    return r.finish("T04 payment")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
