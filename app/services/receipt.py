# app/services/receipt.py
"""
تولید رسید نوبت (متن ساده + PDF) برای بیمار.

- generate_receipt_text  → متن ساده با ایموجی و شعر
- generate_receipt_pdf   → فایل PDF با فونت Vazir
"""

from __future__ import annotations

import os
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


# ---------------------------------------------------------------------------
# مسیر فونت (فرض: assets/fonts/Vazir.ttf در روت پروژه)
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_PATH = os.path.join(_BASE_DIR, "assets", "fonts", "Vazir.ttf")
FONT_NAME = "Vazir"

_font_registered = False


def _ensure_font() -> bool:
    """ثبت فونت Vazir در reportlab (فقط یک بار)."""
    global _font_registered
    if _font_registered:
        return True
    if os.path.exists(FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
            _font_registered = True
            return True
        except Exception:
            return False
    return False


# ---------------------------------------------------------------------------
# ابزارهای کمکی
# ---------------------------------------------------------------------------

POEM = (
    "در این سرای بی‌کسی، کسی به در نمی‌زند\n"
    "به دشتِ پرملالِ ما، بهار می‌رسد\n"
    "— از شعر معاصر"
)


def _safe(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _draw_rtl_line(c: canvas.Canvas, text: str, x_right: float, y: float, font_size: int = 11):
    """رسم یک خط راست‌به‌چپ (تک‌خطی)."""
    c.setFont(FONT_NAME, font_size)
    c.drawRightString(x_right, y, text)


# ---------------------------------------------------------------------------
# رسید متنی
# ---------------------------------------------------------------------------

def generate_receipt_text(appointment_data: Dict[str, Any], user_data: Dict[str, Any]) -> str:
    """تولید رسید متنی با ایموجی و شعر."""
    patient = _safe(appointment_data.get("full_name") or user_data.get("full_name"), "بیمار گرامی")
    ncode = _safe(appointment_data.get("national_code") or user_data.get("national_code"))
    doctor = _safe(appointment_data.get("doctor_name"))
    date = _safe(appointment_data.get("date"))
    time = _safe(appointment_data.get("time"))
    amount = _safe(appointment_data.get("amount"))
    commission = _safe(appointment_data.get("commission_amount"))
    doctor_share = _safe(appointment_data.get("doctor_share"))
    tracking = _safe(appointment_data.get("tracking_code") or appointment_data.get("id"))

    lines = [
        "🧾 <b>رسید رزرو نوبت — شیراز مدیکال</b>",
        "➖➖➖➖➖➖➖➖➖➖",
        f"👤 بیمار: <b>{patient}</b>",
        f"🆔 کد ملی: <code>{ncode}</code>",
        f"👨‍⚕️ پزشک: <b>{doctor}</b>",
        f"📅 تاریخ: <b>{date}</b>",
        f"⏰ ساعت: <b>{time}</b>",
        "➖➖➖➖➖➖➖➖➖➖",
        f"💰 مبلغ ویزیت: <b>{amount}</b> تومان",
        f"🏥 سهم شیراز مدیکال: <b>{commission}</b> تومان",
        f"🩺 سهم پزشک: <b>{doctor_share}</b> تومان",
        f"🔖 کد رهگیری: <code>{tracking}</code>",
        "➖➖➖➖➖➖➖➖➖➖",
        "🌸 <i>با آرزوی سلامتی برای شما</i>",
        f"📜 <i>{POEM}</i>",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# رسید PDF
# ---------------------------------------------------------------------------

def generate_receipt_pdf(
    appointment_data: Dict[str, Any],
    user_data: Dict[str, Any],
    output_path: str = None,
) -> str:
    """تولید PDF رسید. مسیر خروجی را برمی‌گرداند.

    Args:
        appointment_data: داده نوبت (full_name, doctor_name, date, ...)
        user_data: داده کاربر (full_name, national_code, ...)
        output_path: مسیر خروجی (پیش‌فرض: data/receipts/receipt_<tracking>.pdf)

    Raises:
        RuntimeError: اگر فونت Vazir موجود نباشد.
    """
    if not _ensure_font():
        raise RuntimeError(
            f"فونت Vazir یافت نشد: {FONT_PATH}\n"
            "لطفاً فایل Vazir.ttf را در assets/fonts/ قرار دهید."
        )

    if output_path is None:
        tracking = _safe(appointment_data.get("tracking_code") or appointment_data.get("id"), "receipt")
        output_path = os.path.join(_BASE_DIR, "data", "receipts", f"receipt_{tracking}.pdf")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    right = width - 20 * mm
    left = 20 * mm

    # هدر
    c.setFillColor(colors.HexColor("#0E7490"))
    c.rect(0, height - 30 * mm, width, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME, 18)
    c.drawCentredString(width / 2, height - 18 * mm, "شیراز مدیکال")
    c.setFont(FONT_NAME, 10)
    c.drawCentredString(width / 2, height - 24 * mm, "سامانه سلامت و گردشگری شهری شیراز")

    # عنوان رسید
    y = height - 45 * mm
    c.setFillColor(colors.black)
    _draw_rtl_line(c, "رسید رزرو نوبت", right, y, 15)
    y -= 10 * mm

    # خط جداکننده
    c.setStrokeColor(colors.HexColor("#0E7490"))
    c.setLineWidth(1)
    c.line(left, y, right, y)
    y -= 8 * mm

    rows = [
        ("بیمار", _safe(appointment_data.get("full_name") or user_data.get("full_name"))),
        ("کد ملی", _safe(appointment_data.get("national_code") or user_data.get("national_code"))),
        ("پزشک", _safe(appointment_data.get("doctor_name"))),
        ("تاریخ", _safe(appointment_data.get("date"))),
        ("ساعت", _safe(appointment_data.get("time"))),
    ]
    for label, value in rows:
        _draw_rtl_line(c, f"{label}: {value}", right, y, 11)
        y -= 7 * mm

    y -= 2 * mm
    c.line(left, y, right, y)
    y -= 8 * mm

    money_rows = [
        ("مبلغ ویزیت", f"{_safe(appointment_data.get('amount'))} تومان"),
        ("سهم شیراز مدیکال", f"{_safe(appointment_data.get('commission_amount'))} تومان"),
        ("سهم پزشک", f"{_safe(appointment_data.get('doctor_share'))} تومان"),
        ("کد رهگیری", _safe(appointment_data.get("tracking_code") or appointment_data.get("id"))),
    ]
    for label, value in money_rows:
        _draw_rtl_line(c, f"{label}: {value}", right, y, 11)
        y -= 7 * mm

    # شعر
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#475569"))
    for line in POEM.split("\n"):
        _draw_rtl_line(c, line, right, y, 10)
        y -= 6 * mm

    # فوتر
    c.setFillColor(colors.HexColor("#64748B"))
    _draw_rtl_line(c, "شیراز مدیکال — 07132122000", right, 25 * mm, 9)
    _draw_rtl_line(c, "https://ble.ir/shiraz_medical", right, 19 * mm, 9)

    c.showPage()
    c.save()
    return output_path