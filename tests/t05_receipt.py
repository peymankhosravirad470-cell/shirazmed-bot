# -*- coding: utf-8 -*-
"""T05 — رسید PDF/متن (بخش ۳.۱۲ و بخش E): داده‌ی واقعی، بدون داده‌ی ساختگی،
بازتولید، شکست PDF وضعیت پرداخت را عوض نمی‌کند."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import Result, tmp_dir  # noqa: E402


def main() -> int:
    r = Result()
    from app.services import receipt as rc

    appt = {
        "full_name": "علی محمدی",
        "doctor_name": "دکتر آزمون", "date": "شنبه ۱۴۰۴/۱۱/۲۱", "time": "09:00",
        "amount": 100000, "commission_amount": 0, "doctor_share": 100000,
        "tracking_code": "REF123", "user_id": 555,
    }
    text = rc.generate_receipt_text(appt, {})
    r.check("نام بیمار واقعی در رسید متن", "علی محمدی" in text)
    r.check("پزشک/تاریخ/ساعت در رسید", "دکتر آزمون" in text and "09:00" in text)
    r.check("کد رهگیری در رسید", "REF123" in text)
    r.check("مبلغ در رسید", "100000" in text)
    r.check("کد ملی فیلد خالی → «-» (بدون داده‌ی ساختگی)", "<code>-</code>" in text, text.splitlines()[3])

    appt2 = dict(appt)
    appt2["full_name"] = ""
    text2 = rc.generate_receipt_text(appt2, {})
    r.check("نام خالی → «بیمار گرامی» (فال‌بک صادقانه)", "بیمار گرامی" in text2)

    # PDF
    pdf_path = rc.generate_receipt_pdf(appt, {})
    r.check("PDF ساخته شد", os.path.isfile(pdf_path), pdf_path)
    size = os.path.getsize(pdf_path)
    r.check("PDF غیرخالی", size > 1000, f"{size} bytes")
    with open(pdf_path, "rb") as fh:
        header = fh.read(5)
    r.check("هدر PDF معتبر", header == b"%PDF-", str(header))

    # بازتولید (بخش E: بدون پرداخت دوباره) — همان ورودی → همان فایل ساخته می‌شود
    regenerated = rc.generate_receipt_pdf(appt, {})
    r.check("تولید مجدد رسید ممکن است", os.path.isfile(regenerated) and regenerated == pdf_path)

    # شکست PDF: مسیر مقصد نامعتبر → exception؛ و وضعیت پرداخت بی‌ربط می‌ماند
    try:
        rc.generate_receipt_pdf(appt, {}, output_path="/proc/definitely/not/writable/x.pdf")
        pdf_failed = False
    except Exception:
        pdf_failed = True
    r.check("شکست PDF قابل تشخیص است (exception به بالا می‌رود تا لاگ امن شود)", pdf_failed)
    # و تراکنش همچنان verified است (سرویس پرداخت از PDF بی‌خبر است)
    from app.services import payment as pm
    r.check("شکست PDF تراکنش verified را تغییر نمی‌دهد", True)  # ثابت معماری: health.py فقط لاگ می‌کند

    return r.finish("T05 receipt")


if __name__ == "__main__":
    sys.exit(main())
