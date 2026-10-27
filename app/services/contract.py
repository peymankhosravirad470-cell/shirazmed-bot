# app/services/contract.py
from __future__ import annotations

import os
import urllib.request
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 🆕 فیکس PDF فارسی: بدون arabic_reshaper + python-bidi حروف فارسی جدا و معکوس
# رسم می‌شوند (همان باگی که در receipt.py رفع شد).
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def _reshape(text: str) -> str:
        try:
            return get_display(arabic_reshaper.reshape(str(text)))
        except Exception:
            return str(text)
except ImportError:  # pragma: no cover
    def _reshape(text: str) -> str:
        return str(text)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(_BASE_DIR, "assets", "fonts")
FONT_PATH = os.path.join(FONT_DIR, "Vazir.ttf")
FONT_URL = "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/Vazirmatn-Regular.ttf"
FONT_NAME = "Vazir"
_font_registered = False

def _ensure_font() -> bool:
    global _font_registered
    if _font_registered:
        return True
    os.makedirs(FONT_DIR, exist_ok=True)
    if not os.path.exists(FONT_PATH):
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        except Exception:
            return False
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
        _font_registered = True
        return True
    except Exception:
        return False

def _safe(value: Any, default: str = "-") -> str:
    if value is None: return default
    s = str(value).strip()
    return s if s else default

def _rtl(c: canvas.Canvas, text: str, x_right: float, y: float, size: int = 11):
    if _font_registered: c.setFont(FONT_NAME, size)
    else: c.setFont("Helvetica", size)
    c.drawRightString(x_right, y, _reshape(text))

def generate_doctor_contract_pdf(doctor_data: Dict[str, Any], output_path: str = None) -> str:
    _ensure_font()
    if output_path is None:
        doc_id = _safe(doctor_data.get("id"), "doctor")
        output_path = os.path.join(_BASE_DIR, "data", "contracts", f"contract_{doc_id}.pdf")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    name = _safe(doctor_data.get("name"))
    specialty = _safe(doctor_data.get("specialty"))
    rate = _safe(doctor_data.get("commission_rate"), "0")
    ncode = _safe(doctor_data.get("national_code"))
    phone = _safe(doctor_data.get("phone"))

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    right = width - 20 * mm
    left = 20 * mm

    c.setFillColor(colors.HexColor("#0E7490"))
    c.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    _rtl(c, "شیراز مدیکال", width/2, height - 16 * mm, 16)
    _rtl(c, "قرارداد همکاری پزشک", width/2, height - 22 * mm, 10)

    y = height - 45 * mm
    c.setFillColor(colors.black)
    _rtl(c, "مشخصات پزشک", right, y, 14)
    y -= 9 * mm

    for label, value in [("نام پزشک", name), ("تخصص", specialty), ("کد ملی", ncode), ("تلفن", phone), ("درصد کمیسیون", f"{rate}%")]:
        _rtl(c, f"{label}: {value}", right, y, 11)
        y -= 7 * mm

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#0E7490"))
    c.line(left, y, right, y)
    y -= 9 * mm

    _rtl(c, "شرایط همکاری", right, y, 14)
    y -= 9 * mm

    terms = [
        "۱. شیراز مدیکال متعهد به معرفی بیمار و مدیریت نوبت‌دهی است.",
        f"۲. کمیسیون شیراز مدیکال از هر ویزیت {rate} درصد مبلغ ویزیت است.",
        "۳. پرداخت سهم پزشک حداکثر تا ۷ روز کاری پس از هر ویزیت انجام می‌شود.",
        "۴. پزشک متعهد به رعایت اخلاق حرفه‌ای و محرمانگی اطلاعات بیماران است.",
        "۵. لغو یا تغییر نوبت باید حداقل ۲۴ ساعت قبل اطلاع داده شود.",
        "۶. این قرارداد از تاریخ امضا لازم‌الاجرا و تا پایان همکاری معتبر است.",
    ]
    for t in terms:
        _rtl(c, t, right, y, 10)
        y -= 7 * mm

    y = 45 * mm
    c.line(left, y, left + 60 * mm, y)
    c.line(right - 60 * mm, y, right, y)
    _rtl(c, "امضای پزشک", right, y - 6 * mm, 10)
    _rtl(c, "امضای شیراز مدیکال", left + 60 * mm, y - 6 * mm, 10)

    c.showPage()
    c.save()
    return output_path