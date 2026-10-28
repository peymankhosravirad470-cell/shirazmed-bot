# -*- coding: utf-8 -*-
"""
پنل ثبت‌نام پزشک — کاملاً مخفی برای بیمارها 🩺

طراحی امنیتی (درخواست صریح کاربر):
  ۱) هیچ دکمه یا منویی برای بیمارها اضافه نمی‌شود؛ ورود فقط از دو راه مخفی:
     - دستور پنهان  /doctor  یا  /docreg
     - لینک اختصاصی  ble.ir/<BOT_USERNAME>?start=docreg  (start.py برای این
       payload منوی بیمارانه نمی‌فرستد)
  ۲) رمز عبور ثبت‌نام (متغیر محیطی DOCTOR_REG_CODE) — ۳ تلاش اشتباه = مسدود.
  ۳) هیچ اطلاعاتی مستقیم وارد لیست پزشکان نمی‌شود؛ همه‌چیز در صف انتظار
     (data/doctor_registrations.json) ذخیره و برای ادمین ارسال می‌شود.
  ۴) ادمین با دکمه «تایید» اضافه‌شدن را نهایی می‌کند؛ در صورت تنظیم
     GITHUB_TOKEN و GITHUB_REPO، همان لحظه روی گیت‌هاب هم کامیت می‌شود و
     دیپلوی خودکار لیارا شروع می‌شود (داده دائمی می‌ماند).
  ۵) هر حساب تلگرام/بله فقط «یک» درخواست در انتظار تایید می‌تواند داشته باشد.

جریان فرم: رمز ← نام ← درجه ← تخصص ← مطب/آدرس ← تلفن ← ساعات کار ←
شماره نظام پزشکی (اختیاری) ← جمع‌بندی و ارسال.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import settings
from app.locales import get_msg_btn
from app.services.doctor_loader import DOCTORS_DIR

logger = logging.getLogger(__name__)

# ─── ثابت‌ها ───────────────────────────────────────────────────────────────

QUEUE_PATH = os.path.join("data", "doctor_registrations.json")
_QUEUE_LOCK = asyncio.Lock()

MAX_CODE_ATTEMPTS = 3          # حداکثر تلاش اشتباه برای رمز
MAX_PENDING_PER_CHAT = 1       # هر حساب فقط یک درخواست در انتظار
PAGE_SIZE = 12                 # تعداد تخصص در هر صفحه (۳ ردیف × ۴ ستون)
MAX_QUEUE_RECORDS = 500        # سقف آرشیو صف (قدیمی‌ترین‌ها حذف می‌شوند)

# 🆕 نام فارسی همه ۵۰ تخصص — هم برای دکمه‌های فرم و هم ذخیره specialty_fa
SPEC_FA: dict[str, str] = {
    "acupuncture": "طب سوزنی",
    "allergy": "آلرژی و ایمونولوژی",
    "anesth": "بیهوشی",
    "audio": "شنوایی‌سنجی",
    "cardio": "قلب و عروق",
    "cardsurg": "جراحی قلب و عروق",
    "chiro": "کایروپراکتیک",
    "complementary": "طب مکمل",
    "dental": "دندانپزشکی",
    "derma": "پوست و مو",
    "emergency": "طب اورژانس",
    "endocrine": "غدد و متابولیسم",
    "ent": "گوش، حلق و بینی",
    "forensic": "طب قانونی",
    "gastro": "گوارش و کبد",
    "genetics": "ژنتیک پزشکی",
    "gensurg": "جراحی عمومی",
    "hemonc": "خون و انکولوژی",
    "infectious": "بیماری‌های عفونی",
    "internal": "داخلی",
    "ivf": "ناباروری و نازایی",
    "maxillofacial": "جراحی فک و صورت",
    "midwifery": "مامایی",
    "nephro": "کلیه و فشار خون",
    "neuro": "مغز و اعصاب",
    "neurosurg": "جراحی مغز و اعصاب",
    "nuclear": "پزشکی هسته‌ای",
    "nutrition": "تغذیه",
    "obgyn": "زنان، زایمان و نازایی",
    "occupmed": "طب کار",
    "ophtha": "چشم‌پزشکی",
    "optom": "اپتومتری",
    "ortho": "ارتوپدی",
    "orthotic": "ارتوز و پروتز",
    "ot": "کاردرمانی",
    "patho": "آسیب‌شناسی (پاتولوژی)",
    "pediatric": "اطفال",
    "physio": "فیزیوتراپی",
    "physmed": "طب فیزیکی و توانبخشی",
    "plastics": "جراحی پلاستیک و زیبایی",
    "psy": "روانشناسی",
    "psychiatry": "روانپزشکی",
    "pulmo": "ریه",
    "radiology": "رادیولوژی",
    "rheuma": "روماتولوژی",
    "sonography": "سونوگرافی",
    "speech": "گفتاردرمانی",
    "sportsmed": "طب ورزشی",
    "tradmed": "طب سنتی",
    "urology": "ارولوژی",
}

DEGREES: list[str] = [
    "متخصص",
    "فوق تخصص",
    "فلوشیپ",
    "پزشک عمومی",
    "دندانپزشک",
    "داروساز",
    "پیراپزشک / درمانگر",
    "سایر",
]

# مراحل گفتگو
(
    ASK_CODE,
    ASK_NAME,
    ASK_DEGREE,
    ASK_SPEC,
    ASK_ADDRESS,
    ASK_PHONE,
    ASK_HOURS,
    ASK_LICENSE,
    ASK_CONFIRM,
) = range(9)

# ─── ابزارهای کمکی ─────────────────────────────────────────────────────────

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _latin_digits(text: str) -> str:
    """تبدیل ارقام فارسی/عربی به لاتین."""
    return (text or "").translate(_DIGITS)


def _normalize_phone(raw: str) -> str | None:
    """نرمال‌سازی شماره تلفن؛ خروجی فقط رقم، ۸ تا ۱۳ رقم."""
    cleaned = re.sub(r"[\s\-()+.]", "", _latin_digits(raw or ""))
    cleaned = cleaned.lstrip("+")
    if not cleaned.isdigit() or not (8 <= len(cleaned) <= 13):
        return None
    return cleaned


def _now_local() -> datetime:
    """زمان فعلی با آفست منطقه‌ای تنظیم‌شده (پیش‌فرض ایران)."""
    tz = timezone(timedelta(hours=settings.timezone_offset_hours))
    return datetime.now(tz)


def _now_str() -> str:
    """زمان محلی به شکل خوانا (میلادی + شمسی اگر jdatetime موجود بود)."""
    now = _now_local()
    base = now.strftime("%Y-%m-%d %H:%M")
    try:
        import jdatetime  # noqa: PLC0415 (import داخل تابع برای تست‌پذیری)

        j = jdatetime.datetime.fromgregorian(datetime=now)
        return f"{base} ({j.strftime('%Y/%m/%d')})"
    except Exception:  # pragma: no cover
        return base


def _doctor_display_name(raw: str, degree: str) -> str:
    """نام را برای نمایش در لیست بیمارها یکدست می‌کند (پیشوند «دکتر»)."""
    name = (raw or "").strip()
    if not name:
        return name
    if degree in ("پیراپزشک / درمانگر", "سایر", "روانشناس"):
        return name
    if not name.startswith("دکتر") and not name.startswith("دکتر "):
        return f"دکتر {name}"
    return name


# ─── صف درخواست‌ها (خواندن/نوشتن فایل) ────────────────────────────────────

def _load_queue() -> dict[str, Any]:
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            data.setdefault("next_id", 1)
            return data
    except FileNotFoundError:
        pass
    except Exception as error:  # noqa: BLE001
        logger.error("خطا در خواندن صف ثبت‌نام پزشک: %s", error)
    return {"next_id": 1, "records": []}


def _save_queue(queue: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    tmp = f"{QUEUE_PATH}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(queue, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, QUEUE_PATH)  # نوشتن اتمیک؛ نیمه‌کاره ذخیره نمی‌شود


def _has_pending(chat_id: int) -> bool:
    queue = _load_queue()
    return any(
        r.get("chat_id") == chat_id and r.get("status") == "pending"
        for r in queue["records"]
    )


def _get_record(record_id: int) -> dict[str, Any] | None:
    for r in _load_queue()["records"]:
        if r.get("id") == record_id:
            return r
    return None


def _update_record(record_id: int, **fields: Any) -> dict[str, Any] | None:
    queue = _load_queue()
    target = None
    for r in queue["records"]:
        if r.get("id") == record_id:
            r.update(fields)
            target = r
            break
    if target is not None:
        _save_queue(queue)
    return target


# ─── افزودن پزشک تاییدشده به data/doctors/<spec>.json ─────────────────────

def _append_doctor(record: dict[str, Any]) -> tuple[str, str] | tuple[str, None]:
    """پزشک را به فایل تخصص اضافه می‌کند؛ خروجی: (شناسه دکتر, خطا یا None)."""
    spec_key = str(record.get("spec_key", "")).strip()
    if spec_key not in SPEC_FA:
        return "", "تخصص نامعتبر است"

    path = os.path.join(DOCTORS_DIR, f"{spec_key}.json")
    doctors: list[dict[str, Any]] = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, list):
                doctors = loaded
        except Exception as error:  # noqa: BLE001
            return "", f"فایل تخصص خراب است: {error}"

    # شناسه بعدی: بزرگ‌ترین عدد موجود doc_XXX + ۱
    max_index = 0
    for d in doctors:
        m = re.match(r"^doc_(\d+)$", str(d.get("id", "")))
        if m:
            max_index = max(max_index, int(m.group(1)))
    doc_id = f"doc_{max_index + 1:03d}"

    entry: dict[str, Any] = {
        "id": doc_id,
        "name_fa": _doctor_display_name(
            str(record.get("name", "")), str(record.get("degree", ""))
        ),
        "specialty_fa": SPEC_FA[spec_key],
        "status": "active",
        # 🆕 فیلدهای تکمیلی — لودر فعلی نادیده می‌گیرد ولی برای آینده ذخیره می‌شود
        "degree_fa": record.get("degree", ""),
        "clinic_fa": record.get("clinic", ""),
        "phone_fa": record.get("phone", ""),
        "hours_fa": record.get("hours", ""),
        "license": record.get("license", ""),
        "added_at": _now_str(),
        "source": "doctor_registration",
    }
    doctors.append(entry)

    try:
        os.makedirs(DOCTORS_DIR, exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doctors, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as error:  # noqa: BLE001
        return "", f"خطا در نوشتن فایل: {error}"

    return doc_id, None


# ─── کامیت خودکار روی گیت‌هاب (اختیاری — با GITHUB_TOKEN و GITHUB_REPO) ───

def _github_commit_doctor(record: dict[str, Any], doc_id: str) -> tuple[bool, str]:
    """فایل تخصص را روی گیت‌هاب آپدیت می‌کند تا دیپلوی خودکار لیارا داده را دائمی کند.

    اگر GITHUB_TOKEN یا GITHUB_REPO تنظیم نشده باشد، بی‌صدا رد می‌شود
    (ذخیره فقط روی دیسک سرور انجام شده است).
    """
    import base64  # noqa: PLC0415

    import requests  # noqa: PLC0415

    token = (getattr(settings, "github_token", "") or "").strip()
    repo = (getattr(settings, "github_repo", "") or "").strip()
    branch = (getattr(settings, "github_branch", "main") or "main").strip()
    if not token or not repo:
        return False, "GITHUB_TOKEN/GITHUB_REPO تنظیم نشده؛ ذخیره فقط روی سرور"

    spec_key = str(record.get("spec_key", ""))
    path = f"data/doctors/{spec_key}.json"
    api = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        # ۱) آخرین نسخه فایل از گیت‌هاب (منبع حقیقت برای دیپلوی)
        get_resp = requests.get(api, headers=headers, params={"ref": branch}, timeout=20)
        if get_resp.status_code == 200:
            payload = get_resp.json()
            sha = payload.get("sha")
            doctors = json.loads(base64.b64decode(payload.get("content", b"")).decode("utf-8"))
            if not isinstance(doctors, list):
                doctors = []
        elif get_resp.status_code == 404:
            sha = None
            doctors = []
        else:
            return False, f"خطای خواندن گیت‌هاب: HTTP {get_resp.status_code}"

        # ۲) حذف تکراری (اگر همان doc_id قبلاً بود) و افزودن پزشک تازه
        doctors = [d for d in doctors if str(d.get("id")) != doc_id]
        name = _doctor_display_name(str(record.get("name", "")), str(record.get("degree", "")))
        doctors.append({
            "id": doc_id,
            "name_fa": name,
            "specialty_fa": SPEC_FA.get(spec_key, spec_key),
            "status": "active",
            "degree_fa": record.get("degree", ""),
            "clinic_fa": record.get("clinic", ""),
            "phone_fa": record.get("phone", ""),
            "hours_fa": record.get("hours", ""),
            "license": record.get("license", ""),
            "added_at": _now_str(),
            "source": "doctor_registration",
        })

        content = base64.b64encode(
            json.dumps(doctors, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii")

        # ۳) کامیت — این push دیپلوی خودکار لیارا را راه می‌اندازد
        put_resp = requests.put(
            api,
            headers=headers,
            json={
                "message": f"🩺 افزودن پزشک تاییدشده: {name} ← {SPEC_FA.get(spec_key, spec_key)}",
                "content": content,
                "sha": sha,
                "branch": branch,
            },
            timeout=30,
        )
        if put_resp.status_code in (200, 201):
            return True, "روی گیت‌هاب ثبت شد و دیپلوی خودکار شروع شد"
        return False, f"خطای کامیت گیت‌هاب: HTTP {put_resp.status_code}"
    except Exception as error:  # noqa: BLE001
        logger.error("خطای کامیت گیت‌هاب پزشک: %s", error)
        return False, f"خطا: {error}"


# ─── کیبوردها ──────────────────────────────────────────────────────────────

def _cancel_button_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("❌ لغو", callback_data="dreg_cancel")]


def _end_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    """🆕 پایان جریان ثبت‌نام: بازگشت به منو + پیشنهادات (الگوی استاندارد کل ربات).

    این فلو برای دکترهای ایرانی است و فارسی است؛ اما اگر کاربر زبان دیگری
    انتخاب کرده باشد، برچسب‌ها از locale سه‌زبانه خوانده می‌شود (fallback: فارسی).
    """
    lang = context.user_data.get("lang", "fa") if context.user_data else "fa"
    if lang not in ("fa", "en", "ar"):
        lang = "fa"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main"),
        InlineKeyboardButton(get_msg_btn(lang, "btn_feedback"), callback_data="start_feedback"),
    ]])


def _degree_keyboard() -> InlineKeyboardMarkup:
    rows = []
    pair: list[InlineKeyboardButton] = []
    for index, degree in enumerate(DEGREES):
        pair.append(InlineKeyboardButton(degree, callback_data=f"dreg_deg_{index}"))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append(_cancel_button_row())
    return InlineKeyboardMarkup(rows)


def _spec_page_count() -> int:
    return max(1, (len(SPEC_FA) + PAGE_SIZE - 1) // PAGE_SIZE)


def _spec_keyboard(page: int) -> InlineKeyboardMarkup:
    page = max(0, min(page, _spec_page_count() - 1))
    keys = sorted(SPEC_FA.keys())
    start = page * PAGE_SIZE
    chunk = keys[start:start + PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for key in chunk:
        row.append(InlineKeyboardButton(SPEC_FA[key], callback_data=f"dreg_spec_{key}_{page}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"dreg_pg_{page - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{_spec_page_count()}", callback_data="dreg_noop"))
    if page < _spec_page_count() - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"dreg_pg_{page + 1}"))
    rows.append(nav)
    rows.append(_cancel_button_row())
    return InlineKeyboardMarkup(rows)


def _license_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ ندارم / بعداً وارد می‌کنم", callback_data="dreg_skip")],
        _cancel_button_row(),
    ])


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید و ارسال", callback_data="dreg_confirm"),
            InlineKeyboardButton("❌ لغو", callback_data="dreg_cancel"),
        ]
    ])


def _summary_text(data: dict[str, Any]) -> str:
    return (
        "📋 جمع‌بندی اطلاعات شما:\n\n"
        f"👤 نام: {data.get('name', '—')}\n"
        f"🎓 درجه: {data.get('degree', '—')}\n"
        f"🏥 تخصص: {data.get('spec_fa', '—')}\n"
        f"📍 مطب/کلینیک: {data.get('clinic', '—')}\n"
        f"📞 تلفن: {data.get('phone', '—')}\n"
        f"🕐 ساعات کار: {data.get('hours', '—')}\n"
        f"🔢 شماره نظام پزشکی: {data.get('license') or '—'}\n\n"
        "اگر همه‌چیز درست است، «تایید و ارسال» را بزنید."
    )


# ─── مراحل گفتگو ───────────────────────────────────────────────────────────

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ورود مخفی: /doctor، /docreg یا لینک اختصاصی (?start=docreg)."""
    context.user_data.pop("dreg", None)
    await update.effective_message.reply_text(
        "🩺 ثبت‌نام پزشکان\n\n"
        "برای شروع، رمز ثبت‌نام را بفرستید.\n"
        "(رمز را مدیر کلینیک به بیمارستان/مطب شما داده است)"
    )
    return ASK_CODE


async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text != (settings.doctor_reg_code or "").strip():
        attempts = int(context.user_data.get("dreg_attempts", 0)) + 1
        context.user_data["dreg_attempts"] = attempts
        if attempts >= MAX_CODE_ATTEMPTS:
            context.user_data.pop("dreg_attempts", None)
            await update.message.reply_text(
                "⛔ تعداد تلاش‌های اشتباه بیش از حد مجاز بود.\n"
                "دوباره با دستور /doctor شروع کنید و اگر رمز را نمی‌دانید با مدیر کلینیک تماس بگیرید.",
                reply_markup=_end_keyboard(context),
            )
            return ConversationHandler.END
        await update.message.reply_text(
            f"❌ رمز نادرست است. ({attempts} از {MAX_CODE_ATTEMPTS} تلاش)\n"
            "لطفاً دوباره رمز را بفرستید:"
        )
        return ASK_CODE

    context.user_data.pop("dreg_attempts", None)
    chat_id = update.effective_chat.id

    if _has_pending(chat_id):
        await update.message.reply_text(
            "ℹ️ شما قبلاً یک درخواست ثبت‌نام ارسال کرده‌اید که در انتظار تایید مدیر است.\n"
            "لطفاً صبور باشید؛ نتیجه از همین ربات به شما اعلام می‌شود.",
            reply_markup=_end_keyboard(context),
        )
        return ConversationHandler.END

    context.user_data["dreg"] = {}
    await update.message.reply_text(
        "✅ رمز درست است. خوش آمدید!\n\n"
        "۱ از ۷ — لطفاً نام و نام خانوادگی خود را بفرستید\n"
        "(مثال: علی رضایی)"
    )
    return ASK_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 3 or not any(ch.isalpha() for ch in name):
        await update.message.reply_text("❌ نام معتبر نیست. لطفاً نام و نام خانوادگی کامل را بنویسید:")
        return ASK_NAME
    if len(name) > 60:
        name = name[:60]

    context.user_data["dreg"]["name"] = name
    await update.message.reply_text(
        "۲ از ۷ — درجه تخصصی خود را انتخاب کنید:",
        reply_markup=_degree_keyboard(),
    )
    return ASK_DEGREE


async def receive_degree(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    match = re.match(r"^dreg_deg_(\d+)$", query.data or "")
    if not match:
        return ASK_DEGREE
    index = int(match.group(1))
    if index >= len(DEGREES):
        return ASK_DEGREE
    context.user_data["dreg"]["degree"] = DEGREES[index]
    await query.edit_message_text(
        f"🎓 درجه: {DEGREES[index]}\n\n"
        "۳ از ۷ — تخصص خود را از فهرست زیر انتخاب کنید:",
        reply_markup=_spec_keyboard(0),
    )
    return ASK_SPEC


async def spec_navigate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    match = re.match(r"^dreg_pg_(\d+)$", query.data or "")
    if not match:
        return ASK_SPEC
    page = int(match.group(1))
    try:
        await query.edit_message_reply_markup(reply_markup=_spec_keyboard(page))
    except Exception:  # noqa: BLE001
        pass
    return ASK_SPEC


async def receive_specialty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    match = re.match(r"^dreg_spec_([a-z]+)_(\d+)$", query.data or "")
    if not match:
        return ASK_SPEC
    key = match.group(1)
    if key not in SPEC_FA:
        await query.answer("این تخصص معتبر نیست.", show_alert=True)
        return ASK_SPEC

    context.user_data["dreg"]["spec_key"] = key
    context.user_data["dreg"]["spec_fa"] = SPEC_FA[key]
    await query.edit_message_text(
        f"🏥 تخصص: {SPEC_FA[key]}\n\n"
        "۴ از ۷ — نام و آدرس مطب/کلینیک/بیمارستان خود را بنویسید\n"
        "(مثال: مطب شخصی، خیابان قصرالدشت، ساختمان پزشکان مهر، طبقه ۲)"
    )
    return ASK_ADDRESS


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clinic = (update.message.text or "").strip()
    if len(clinic) < 5:
        await update.message.reply_text("❌ آدرس خیلی کوتاه است. لطفاً کامل‌تر بنویسید:")
        return ASK_ADDRESS
    if len(clinic) > 200:
        clinic = clinic[:200]

    context.user_data["dreg"]["clinic"] = clinic
    await update.message.reply_text(
        "۵ از ۷ — شماره تلفن مطب یا موبایل برای ارتباط بیمارها را بفرستید\n"
        "(مثال: 07132345678)"
    )
    return ASK_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = _normalize_phone(update.message.text or "")
    if phone is None:
        await update.message.reply_text(
            "❌ شماره تلفن معتبر نیست (باید ۸ تا ۱۳ رقم باشد).\nلطفاً دوباره بفرستید:"
        )
        return ASK_PHONE

    context.user_data["dreg"]["phone"] = phone
    await update.message.reply_text(
        "۶ از ۷ — ساعات کار مطب را بنویسید\n"
        "(مثال: شنبه تا چهارشنبه، ۱۶ تا ۲۰ — جمعه تعطیل)"
    )
    return ASK_HOURS


async def receive_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hours = (update.message.text or "").strip()
    if len(hours) < 2:
        await update.message.reply_text("❌ لطفاً ساعات کار را کامل‌تر بنویسید:")
        return ASK_HOURS
    if len(hours) > 100:
        hours = hours[:100]

    context.user_data["dreg"]["hours"] = hours
    await update.message.reply_text(
        "۷ از ۷ — شماره نظام پزشکی خود را بفرستید\n"
        "(اختیاری — اگر می‌خواهید این مرحله رد شود، دکمه زیر را بزنید)",
        reply_markup=_license_keyboard(),
    )
    return ASK_LICENSE


async def receive_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    license_number = (update.message.text or "").strip()[:30]
    context.user_data["dreg"]["license"] = license_number
    await update.message.reply_text(
        _summary_text(context.user_data.get("dreg", {})),
        reply_markup=_confirm_keyboard(),
    )
    return ASK_CONFIRM


async def skip_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["dreg"]["license"] = ""
    await query.edit_message_text(
        _summary_text(context.user_data.get("dreg", {})),
        reply_markup=_confirm_keyboard(),
    )
    return ASK_CONFIRM


async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ذخیره درخواست در صف + ارسال به ادمین با دکمه تایید/رد."""
    query = update.callback_query
    await query.answer()

    data = dict(context.user_data.get("dreg", {}))
    if not data.get("name") or not data.get("spec_key"):
        await query.edit_message_text(
            "❌ اطلاعات کامل نیست. لطفاً دوباره با /doctor شروع کنید.",
            reply_markup=_end_keyboard(context),
        )
        return ConversationHandler.END

    user = update.effective_user
    chat_id = update.effective_chat.id

    queue = _load_queue()
    record_id = int(queue.get("next_id", 1))
    queue["next_id"] = record_id + 1
    record: dict[str, Any] = {
        "id": record_id,
        "chat_id": chat_id,
        "username": f"@{user.username}" if user and user.username else "—",
        "tg_name": user.full_name if user else "—",
        "name": data["name"],
        "degree": data.get("degree", ""),
        "spec_key": data["spec_key"],
        "spec_fa": data.get("spec_fa", ""),
        "clinic": data.get("clinic", ""),
        "phone": data.get("phone", ""),
        "hours": data.get("hours", ""),
        "license": data.get("license", ""),
        "status": "pending",
        "created_at": _now_str(),
        "decided_at": None,
        "doc_id": None,
    }
    queue["records"].append(record)
    if len(queue["records"]) > MAX_QUEUE_RECORDS:
        queue["records"] = queue["records"][-MAX_QUEUE_RECORDS:]
    _save_queue(queue)
    context.user_data.pop("dreg", None)

    if settings.admin_chat_id:
        try:
            await context.bot.send_message(
                chat_id=settings.admin_chat_id,
                text=_admin_text(record),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ تایید", callback_data=f"dregadm_ok_{record_id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"dregadm_no_{record_id}"),
                ]]),
            )
        except Exception as error:  # noqa: BLE001
            logger.error("ارسال درخواست ثبت‌نام به ادمین ناموفق بود: %s", error)
    else:
        logger.warning("ADMIN_CHAT_ID تنظیم نشده؛ درخواست #%s فقط در صف ذخیره شد.", record_id)

    await query.edit_message_text(
        "✅ درخواست شما ارسال شد!\n\n"
        "مدیر کلینیک اطلاعات شما را بررسی می‌کند و پس از تایید، نام شما در بخش "
        f"«{record['spec_fa']}» ربات نمایش داده می‌شود.\n\n"
        "سپاس از همکاری شما 🌷",
        reply_markup=_end_keyboard(context),
    )
    logger.info("درخواست ثبت‌نام پزشک #%s از chat %s ذخیره شد.", record_id, chat_id)
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("dreg", None)
    context.user_data.pop("dreg_attempts", None)
    message = getattr(update, "effective_message", None)
    if message is not None:
        if update.callback_query is not None:
            try:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    "ثبت‌نام لغو شد.", reply_markup=_end_keyboard(context),
                )
                return ConversationHandler.END
            except Exception:  # noqa: BLE001
                pass
        await message.reply_text("ثبت‌نام لغو شد.", reply_markup=_end_keyboard(context))
    return ConversationHandler.END


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دکمه شمارنده صفحه — هیچ کاری نمی‌کند."""
    query = update.callback_query
    if query is not None:
        await query.answer()


# ─── پیام ادمین و دکمه‌های تایید/رد ────────────────────────────────────────

def _admin_text(record: dict[str, Any]) -> str:
    esc = html.escape
    return (
        f"🩺 <b>درخواست ثبت‌نام پزشک جدید (#{record['id']})</b>\n\n"
        f"👤 نام: {esc(_doctor_display_name(str(record.get('name', '')), str(record.get('degree', ''))))}\n"
        f"🎓 درجه: {esc(str(record.get('degree', '—')))}\n"
        f"🏥 تخصص: {esc(str(record.get('spec_fa', '—')))}\n"
        f"📍 مطب/کلینیک: {esc(str(record.get('clinic', '—')))}\n"
        f"📞 تلفن: {esc(str(record.get('phone', '—')))}\n"
        f"🕐 ساعات کار: {esc(str(record.get('hours', '—')))}\n"
        f"🔢 نظام پزشکی: {esc(str(record.get('license') or '—'))}\n"
        "─────────────\n"
        f"👤 حساب: {esc(str(record.get('username', '—')))} | آیدی: <code>{record.get('chat_id', '—')}</code>\n"
        f"⏰ ارسال: {esc(str(record.get('created_at', '—')))}"
    )


async def admin_registration_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید یا رد درخواست توسط ادمین (dregadm_ok_<id> / dregadm_no_<id>)."""
    query = update.callback_query
    chat = update.effective_chat

    if settings.admin_chat_id is None or chat is None or chat.id != settings.admin_chat_id:
        if query is not None:
            await query.answer("فقط مدیر می‌تواند این دکمه را بزند.", show_alert=True)
        return
    if query is None:
        return

    match = re.match(r"^dregadm_(ok|no)_(\d+)$", query.data or "")
    if not match:
        return
    action, record_id = match.group(1), int(match.group(2))

    record = _get_record(record_id)
    if record is None:
        await query.answer("این درخواست پیدا نشد.", show_alert=True)
        return
    if record.get("status") != "pending":
        await query.answer("این درخواست قبلاً پردازش شده است.", show_alert=True)
        return

    if action == "no":
        _update_record(record_id, status="rejected", decided_at=_now_str())
        await query.answer()
        try:
            await query.edit_message_text(
                query.message.text + "\n\n❌ <b>رد شد.</b>",
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception:  # noqa: BLE001
            pass
        await _notify_doctor(context, record.get("chat_id"), (
            "ℹ️ درباره درخواست ثبت‌نام شما:\n\n"
            "متأسفانه اطلاعات ارسالی شما تایید نشد. در صورت نیاز با پشتیبانی کلینیک تماس بگیرید."
        ))
        logger.info("درخواست ثبت‌نام #%s رد شد.", record_id)
        return

    # ── تایید ──
    doc_id, error = _append_doctor(record)
    if error:
        await query.answer(f"خطا در افزودن: {error}", show_alert=True)
        logger.error("افزودن پزشک درخواست #%s ناموفق: %s", record_id, error)
        return

    _update_record(record_id, status="approved", decided_at=_now_str(), doc_id=doc_id)

    gh_ok, gh_msg = await asyncio.to_thread(_github_commit_doctor, record, doc_id)

    await query.answer()
    extra = (
        f"\n\n✅ <b>تایید شد</b> — با شناسه <code>{doc_id}</code> به تخصص "
        f"«{html.escape(str(record.get('spec_fa', '')))}» اضافه شد."
    )
    if gh_ok:
        extra += "\n🌐 روی گیت‌هاب کامیت شد و دیپلوی خودکار لیارا شروع شد (داده دائمی است)."
    else:
        extra += f"\n⚠️ {html.escape(gh_msg)}"
    try:
        await query.edit_message_text(
            query.message.text + extra,
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:  # noqa: BLE001
        pass

    await _notify_doctor(context, record.get("chat_id"), (
        "✅ خبر خوب!\n\n"
        "اطلاعات شما تایید شد و از این لحظه در بخش "
        f"«{record.get('spec_fa', '')}» ربات نمایش داده می‌شود.\n\n"
        "سپاس از همکاری شما 🌷"
    ))
    logger.info("درخواست ثبت‌نام #%s تایید شد (%s | گیت‌هاب: %s).", record_id, doc_id, gh_msg)


async def _notify_doctor(context: ContextTypes.DEFAULT_TYPE, chat_id: Any, text: str) -> None:
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        return
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as error:  # noqa: BLE001
        logger.warning("اطلاع‌رسانی به پزشک (%s) ناموفق بود: %s", chat_id, error)


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور مخفی ادمین: فهرست درخواست‌های در انتظار (فقط در چت ادمین)."""
    chat = update.effective_chat
    if settings.admin_chat_id is None or chat is None or chat.id != settings.admin_chat_id:
        return  # برای بقیه کاملاً بی‌صدا

    pending = [r for r in _load_queue()["records"] if r.get("status") == "pending"]
    if not pending:
        await update.message.reply_text("✅ هیچ درخواست در انتظاری وجود ندارد.")
        return

    await update.message.reply_text(f"📋 {len(pending)} درخواست در انتظار تایید:")
    for record in pending[:10]:  # بیش از ۱۰ تا در هر بار نفرستیم
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=_admin_text(record),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ تایید", callback_data=f"dregadm_ok_{record['id']}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"dregadm_no_{record['id']}"),
                ]]),
            )
        except Exception as error:  # noqa: BLE001
            logger.error("ارسال مجدد درخواست #%s به ادمین ناموفق: %s", record["id"], error)


# ─── ConversationHandler ───────────────────────────────────────────────────

# ورود مخفی: دستور /doctor و /docreg + لینک اختصاصی (/start docreg)
_DOCTOR_COMMANDS = ["doctor", "docreg"]

doctor_reg_conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler(_DOCTOR_COMMANDS, start_registration, filters=filters.ChatType.PRIVATE),
        CommandHandler(
            "start",
            start_registration,
            filters=filters.ChatType.PRIVATE & filters.Regex(r"^/start(?:@\w+)?\s+docreg\s*$"),
        ),
    ],
    states={
        ASK_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code),
        ],
        ASK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
        ],
        ASK_DEGREE: [
            CallbackQueryHandler(receive_degree, pattern=r"^dreg_deg_\d+$"),
        ],
        ASK_SPEC: [
            CallbackQueryHandler(receive_specialty, pattern=r"^dreg_spec_[a-z]+_\d+$"),
            CallbackQueryHandler(spec_navigate, pattern=r"^dreg_pg_\d+$"),
            CallbackQueryHandler(noop, pattern=r"^dreg_noop$"),
        ],
        ASK_ADDRESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address),
        ],
        ASK_PHONE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone),
        ],
        ASK_HOURS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_hours),
        ],
        ASK_LICENSE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_license),
            CallbackQueryHandler(skip_license, pattern=r"^dreg_skip$"),
        ],
        ASK_CONFIRM: [
            CallbackQueryHandler(confirm_registration, pattern=r"^dreg_confirm$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_registration, filters=filters.ChatType.PRIVATE),
        CallbackQueryHandler(cancel_registration, pattern=r"^dreg_cancel$"),
    ],
    allow_reentry=True,
)
