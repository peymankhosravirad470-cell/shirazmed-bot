# app/services/receipt.py
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

from config import DATA_DIR

# 🆕 فیکس بحرانی PDF: بدون arabic_reshaper + python-bidi، حروف فارسی در PDF
# جدا و معکوس چاپ می‌شدند (مثلاً «شیراز» به‌صورت حروف بریده و از چپ به راست).
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def _rtl(text: str) -> str:
        """آماده‌سازی متن فارسی برای رسم صحیح در reportlab."""
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
except ImportError:  # pragma: no cover
    def _rtl(text: str) -> str:
        return text

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(_BASE_DIR, "assets", "fonts")
FONT_PATH = os.path.join(FONT_DIR, "Vazir.ttf")
FONT_URL = "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/Vazirmatn-Regular.ttf"
FONT_NAME = "Vazir"
# 🆕 ممیزی (بخش J): رسیدها در ریشه‌ی داده (دیسک پایدار) ذخیره شوند
RECEIPTS_DIR = os.path.join(DATA_DIR, "receipts")

_font_registered = False
_font_failed = False

def _ensure_font() -> bool:
    global _font_registered, _font_failed
    if _font_registered:
        return True
    if _font_failed:
        return False

    # 🆕 فیکس: در مخزن، «assets» یک فایل placeholder است نه پوشه —
    # makedirs خطای [Errno 20] Not a directory می‌داد و PDF کلاً ساخته نمی‌شد.
    try:
        if os.path.exists(FONT_DIR) and not os.path.isdir(FONT_DIR):
            os.remove(FONT_DIR)
        parent = os.path.dirname(FONT_DIR)
        if os.path.exists(parent) and not os.path.isdir(parent):
            os.remove(parent)
        os.makedirs(FONT_DIR, exist_ok=True)
    except OSError as error:
        print(f"Font dir error: {error}")
        _font_failed = True
        return False

    if not os.path.exists(FONT_PATH):
        try:
            # دانلود خودکار فونت از CDN (یک‌بار در اولین اجرا)
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        except Exception as e:
            print(f"Error downloading font: {e}")
            _font_failed = True
            return False

    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
        _font_registered = True
        return True
    except Exception:
        _font_failed = True
        return False

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
    if _font_registered:
        c.setFont(FONT_NAME, font_size)
    else:
        c.setFont("Helvetica", font_size)
    # 🆕 فیکس: reshape + bidi قبل از رسم — بدون این، متن فارسی بریده و معکوس می‌شود
    c.drawRightString(x_right, y, _rtl(text))

def generate_receipt_text(appointment_data: Dict[str, Any], user_data: Dict[str, Any]) -> str:
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

def generate_receipt_pdf(
    appointment_data: Dict[str, Any],
    user_data: Dict[str, Any],
    output_path: str = None,
) -> str:
    _ensure_font()

    if output_path is None:
        # 🆕 فیکس: نام فایل یکتا — قبلاً tracking_code/id وجود نداشت و همه رسیدها
        # با نام «receipt_receipt.pdf» روی هم overwrite می‌شدند!
        tracking = _safe(appointment_data.get("tracking_code") or appointment_data.get("id"))
        user_part = str(appointment_data.get("user_id") or user_data.get("user_id") or "anon")
        date_part = str(appointment_data.get("date") or "nodate").replace("-", "")
        time_part = str(appointment_data.get("time") or "").replace(":", "")
        suffix = tracking if tracking not in ("", "-") else f"{user_part}_{date_part}{time_part}"
        output_path = os.path.join(RECEIPTS_DIR, f"receipt_{suffix}.pdf")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    right = width - 20 * mm
    left = 20 * mm

    c.setFillColor(colors.HexColor("#0E7490"))
    c.rect(0, height - 30 * mm, width, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    _draw_rtl_line(c, "شیراز مدیکال", width/2, height - 18 * mm, 18) # drawRightString vs drawCentredString

    y = height - 45 * mm
    c.setFillColor(colors.black)
    _draw_rtl_line(c, "رسید رزرو نوبت", right, y, 15)
    y -= 10 * mm

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

    y -= 6 * mm
    c.setFillColor(colors.HexColor("#475569"))
    for line in POEM.split("\n"):
        _draw_rtl_line(c, line, right, y, 10)
        y -= 6 * mm

    c.setFillColor(colors.HexColor("#64748B"))
    _draw_rtl_line(c, "شیراز مدیکال — 07132122000", right, 25 * mm, 9)
    _draw_rtl_line(c, "https://ble.ir/shiraz_medical", right, 19 * mm, 9)

    c.showPage()
    c.save()
    return output_path