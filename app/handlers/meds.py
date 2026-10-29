# -*- coding: utf-8 -*-
"""یادآور دارو — نسخه کامل و فعال.

قابلیت‌ها:
- افزودن دارو با نام و یک یا چند ساعت مصرف
- لیست داروهای ثبت‌شده و حذف آن‌ها
- یادآوری خودکار روزانه با JobQueue ربات (به وقت ایران)
- ذخیره‌سازی روی دیسک (data/medications.json) → پس از دیپلوی مجدد هم باقی می‌ماند
- کاملاً سه‌زبانه (فارسی/انگلیسی/عربی)

🆕 قبلاً این بخش فقط یک پیام راهنمای بی‌اثر نشان می‌داد («به‌زودی فعال می‌شود»)
و هیچ یادآوری واقعی وجود نداشت؛ حتی در نسخه لایو، الگوی {med} بدون جایگذاری
نمایش داده می‌شد.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time as _time_mod
import traceback
from datetime import timedelta, timezone as _dt_timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import DATA_DIR, settings

logger = logging.getLogger(__name__)

# مراحل گفتگوی افزودن دارو
ASK_MED_NAME, ASK_MED_TIMES = range(2)

# 🆕 ممیزی (بخش J): مسیر فایل داروها از config.DATA_DIR (env: DATA_DIR)
MEDS_FILE = os.path.join(DATA_DIR, "medications.json")

# الگوی ساعت مجاز:
#   «8» / «08» فقط ساعت  |  «8:00» / «8.00» ساعت:دقیقه  |  «0830» فشرده ۴رقمی
# نکته: «85» یا «999» عمداً رد می‌شوند (بدون دو نقطه فقط ۱-۲ رقم ساعت یا ۴ رقم کامل).
_TIME_BARE = re.compile(r"^([01]?\d|2[0-3])$")
_TIME_COLON = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")
_TIME_COMPACT = re.compile(r"^([01]\d|2[0-3])([0-5]\d)$")

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# ---------------------------------------------------------------------------
# متن‌های سه‌زبانه
# ---------------------------------------------------------------------------

_TEXTS: dict[str, dict[str, str]] = {
        "menu_title": {
            "fa": "💊 یادآور دارو\n\nداروهای خود را ثبت کنید تا هر روز سر ساعتِ مقرر به شما یادآوری کنیم.",
            "en": "💊 Medication Reminder\n\nRegister your medications and we will remind you every day at the scheduled time.",
            "ar": "💊 تذكير بالدواء\n\nسجّل أدويتك وسنذكّرك كل يوم في الوقت المحدد.",
        },
        "menu_btn_add": {"fa": "➕ افزودن دارو", "en": "➕ Add Medication", "ar": "➕ إضافة دواء"},
        "menu_btn_list": {"fa": "📋 داروهای من", "en": "📋 My Medications", "ar": "📋 أدويتي"},
        "menu_btn_del": {"fa": "🗑 حذف دارو", "en": "🗑 Delete Medication", "ar": "🗑 حذف الدواء"},
        "btn_back": {"fa": "🔙 بازگشت به منو", "en": "🔙 Back to Menu", "ar": "🔙 العودة إلى القائمة"},
        "btn_feedback": {"fa": "💬 پیشنهادات", "en": "💬 Feedback", "ar": "💬 ملاحظات"},
        "ask_name": {
            "fa": "💊 نام دارو را بنویسید:\n\nمثال: «قرص فشار»",
            "en": "💊 Please write the medication name:\n\nExample: \"Blood pressure pill\"",
            "ar": "💊 يرجى كتابة اسم الدواء:\n\nمثال: «حبة ضغط»",
        },
        "ask_times": {
            "fa": "⏰ حالا ساعت یا ساعت‌های مصرف را بفرستید (با فاصله یا ویرگول جدا کنید):\n\nمثال: «8:00، 21:30»",
            "en": "⏰ Now send the time(s) of use (separate with space or comma):\n\nExample: \"8:00, 21:30\"",
            "ar": "⏰ الآن أرسل وقت أو أوقات التناول (افصل بينها بمسافة أو فاصلة):\n\nمثال: «8:00، 21:30»",
        },
        "invalid_time": {
            "fa": "⚠️ ساعت وارد شده معتبر نیست.\n\nاین قالب‌ها کافی‌ست: «8» یا «8:00» یا «0830» — با فاصله یا ویرگول جدا کنید.\n\nمثال: 8، 14:30، 21:00",
            "en": "⚠️ The time isn't valid.\n\nAny of these formats works: «8» or «8:00» or «0830» — separate multiple times with spaces or commas.\n\nExample: 8, 14:30, 21:00",
            "ar": "⚠️ الوقت المُدخل غير صالح.\n\nأي من هذه الصيغ تكفي: «8» أو «8:00» أو «0830» — افصل بين الأوقات بمسافة أو فاصلة.\n\nمثال: 8، 14:30، 21:00",
        },
        "saved": {
            "fa": "✅ تمام! یادآور «{name}» فعال شد.\n\n⏰ ساعت‌ها: {times}\n\nاز این به بعد هر روز سر این ساعت‌ها بهت یادآوری می‌کنیم — دیگه هیچ دوزی از قلم نمی‌افته 💙",
            "en": "✅ All set! Your reminder for \"{name}\" is active.\n\n⏰ Times: {times}\n\nWe'll nudge you every day at these times — no dose will slip through again 💙",
            "ar": "✅ تم! تم تفعيل تذكير «{name}».\n\n⏰ الأوقات: {times}\n\nسنذكّرك كل يوم في هذه الأوقات — لن يفوتك أي جرعة بعد اليوم 💙",
        },
        # 🆕 ممیزی (بخش H): وقتی JobQueue در دسترس نیست، به کاربر «صریح» گفته
        # می‌شود که دارو ذخیره شده ولی یادآوری فعال نیست (قبلاً فقط در لاگ بود).
        "saved_no_jobqueue": {
            "fa": "✅ داروی «{name}» ذخیره شد، اما ⚠️ یادآور خودکار در این لحظه فعال نشد.\nلطفاً سر ساعت به یاد داشته باشید یا با پشتیبانی تماس بگیرید.",
            "en": "✅ \"{name}\" was saved, but ⚠️ the automatic reminder is currently unavailable.\nPlease keep track of the time yourself or contact support.",
            "ar": "✅ تم حفظ «{name}»، لكن ⚠️ التذكير التلقائي غير متاح حالياً.\nيرجى الانتباه إلى الوقت أو التواصل مع الدعم.",
        },
        "list_title": {
            "fa": "📋 داروهای ثبت‌شده شما:\n\n",
            "en": "📋 Your registered medications:\n\n",
            "ar": "📋 الأدوية المسجّلة لديك:\n\n",
        },
        "list_empty": {
            "fa": "📋 هنوز دارویی ثبت نکرده‌اید.\n\nبا دکمه «➕ افزودن دارو» اولین یادآور خود را بسازید.",
            "en": "📋 You haven't registered any medications yet.\n\nUse \"➕ Add Medication\" to create your first reminder.",
            "ar": "📋 لم تسجّل أي دواء بعد.\n\nاستخدم «➕ إضافة دواء» لإنشاء أول تذكير.",
        },
        "list_back": {"fa": "🔙 بازگشت", "en": "🔙 Back", "ar": "🔙 رجوع"},
        "del_title": {
            "fa": "🗑 کدام دارو حذف شود؟",
            "en": "🗑 Which medication should be deleted?",
            "ar": "🗑 أي دواء تريد حذفه؟",
        },
        "del_empty": {
            "fa": "📋 دارویی برای حذف وجود ندارد.",
            "en": "📋 There are no medications to delete.",
            "ar": "📋 لا توجد أدوية للحذف.",
        },
        "deleted": {
            "fa": "🗑 «{name}» حذف شد و یادآوری‌هایش متوقف شد.\nهر وقت خواستی، دوباره اضافه‌اش کن 💙",
            "en": "🗑 \"{name}\" was deleted and its reminders stopped.\nAdd it back anytime you like 💙",
            "ar": "🗑 تم حذف «{name}» وتوقّف تذكيراته.\nأضفه من جديد متى ما أردت 💙",
        },
        "too_long": {
            "fa": "⚠️ نام دارو بسیار طولانی است (حداکثر ۶۰ کاراکتر). لطفاً دوباره بنویسید:",
            "en": "⚠️ The medication name is too long (max 60 characters). Please write it again:",
            "ar": "⚠️ اسم الدواء طويل جداً (٦٠ حرفاً كحد أقصى). يرجى الكتابة مرة أخرى:",
        },
        "cancelled": {
            "fa": "باشه، افزودن دارو لغو شد. هر وقت خواستی از اول شروع کن 💙",
            "en": "Alright, adding the medication was cancelled. Start over whenever you like 💙",
            "ar": "حسناً، تم إلغاء إضافة الدواء. ابدأ من جديد متى ما أردت 💙",
        },
        "limit": {
            "fa": "⚠️ حداکثر ۱۰ دارو می‌توانید ثبت کنید. ابتدا یکی را حذف کنید.",
            "en": "⚠️ You can register up to 10 medications. Please delete one first.",
            "ar": "⚠️ يمكنك تسجيل ١٠ أدوية كحد أقصى. يرجى حذف واحد أولاً.",
        },
        "reminder": {
            "fa": "💊 یادآور دارو\n\n⏰ زمان مصرف «{name}» رسیده است.\n\nسلامتی شما برای ما مهم است 💙",
            "en": "💊 Medication Reminder\n\n⏰ It's time to take \"{name}\".\n\nYour health matters to us 💙",
            "ar": "💊 تذكير بالدواء\n\n⏰ حان وقت تناول «{name}\".\n\nصحتك مهمة لنا 💙",
        },
    }



def _t(lang: str, key: str) -> str:
    return _TEXTS.get(key, {}).get(lang) or _TEXTS.get(key, {}).get("fa", key)


def _kb(lang: str, rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for (t, d) in row] for row in rows])


def _back_feedback_kb(lang: str, back_callback: str = "back_main") -> InlineKeyboardMarkup:
    """🆕 الگوی استاندارد پایان اکشن: بازگشت + پیشنهادات کنار هم."""
    return _kb(lang, [[
        (_t(lang, "btn_back"), back_callback),
        (_t(lang, "btn_feedback"), "start_feedback"),
    ]])


def _get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang", "fa")
    return lang if lang in ("fa", "en", "ar") else "fa"


# ---------------------------------------------------------------------------
# ذخیره‌سازی
# ---------------------------------------------------------------------------

def _load_meds() -> dict[str, list[dict[str, Any]]]:
    """خواندن داروها.

    🆕 ممیزی (بخش H): اگر فایل موجود ولی خراب باشد، دیگر بی‌صدا {} برنمی‌گردیم —
    چون اولین نوشتن بعدی «همه‌ی داروهای بقیه‌ی کاربران را پاک می‌کرد». فایل خراب
    به‌نام با پسوند .corrupt-<timestamp> قرنطینه می‌شود تا دست‌نخورده بماند و
    در لاگ امن ثبت شود.
    """
    if not os.path.isfile(MEDS_FILE):
        return {}
    try:
        with open(MEDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as error:
        quarantine = f"{MEDS_FILE}.corrupt-{int(_time_mod.time())}"
        try:
            os.replace(MEDS_FILE, quarantine)
            logger.error(
                "فایل داروها خراب بود و برای جلوگیری از از دست رفتن داده‌ها قرنطینه شد: %s (خطا: %s)",
                quarantine, error,
            )
        except OSError:
            logger.error("فایل داروها خراب است و حتی قرنطینه هم ممکن نشد: %s", error)
        return {}


def _save_meds(data: dict[str, list[dict[str, Any]]]) -> None:
    os.makedirs(os.path.dirname(MEDS_FILE), exist_ok=True)
    tmp = MEDS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MEDS_FILE)


def get_chat_meds(chat_id: int | str) -> list[dict[str, Any]]:
    return _load_meds().get(str(chat_id), [])


def _set_chat_meds(chat_id: int | str, items: list[dict[str, Any]]) -> None:
    data = _load_meds()
    if items:
        data[str(chat_id)] = items
    else:
        data.pop(str(chat_id), None)
    _save_meds(data)


def _normalize_time(raw: str) -> str | None:
    """ورودی آزاد ساعت → «HH:MM»؛ فقط ساعت (مثل «8» یا «۹») هم پذیرفته می‌شود.

    🆕 ممیزی (بخش H): «8 pm» دیگر به «08:00» تبدیل نمی‌شود — پسوند صبح/عصر/شب/
    am/pm حالا واقعاً در محاسبه لحاظ می‌شود:
      «8 pm» و «۸ شب» → 20:00 | «8 am» و «۸ صبح» → 08:00 | «12 pm» → 12:00
      «12 am» → 00:00 | «8» بدون پسوند → 08:00 (رفتار پیش‌بینی‌پذیر مستند)
    """
    t = raw.strip().translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)

    # 🆕 پسوند صبح/عصر/شب/am/pm — قبل از تطبیق الگو استخراج و اعمال می‌شود
    period: str | None = None  # None | am | pm
    lowered = t.lower()
    if re.search(r"pm|بعدازظهر|بعد الظهر|عصر", lowered):
        period = "pm"
    elif re.search(r"\bam\b|صبح|بامداد", lowered):
        period = "am"
    elif re.search(r"شب", lowered):
        period = "pm"
    elif re.search(r"ظهر", lowered):
        period = "pm"
    if period is not None:
        # پسوند را از متن حذف کن تا الگوهای ساعت تمیز تطبیق کنند
        t = re.sub(r"(?i)(pm|am|بعدازظهر|بعد الظهر|عصر|صبح|بامداد|شب|ظهر)", "", t).strip()

    m = _TIME_COLON.match(t) or _TIME_BARE.match(t) or _TIME_COMPACT.match(t)
    if not m:
        return None
    hour = int(m.group(1))
    minute = m.group(2) if m.lastindex and m.lastindex >= 2 else "00"
    if period == "pm" and hour < 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"


_PERIOD_WORD_RE = re.compile(r"(?i)(am|pm|بعدازظهر|بعد الظهر|صبح|بامداد|ظهر|عصر|شب)")

def parse_times(text: str) -> list[str]:
    """ورودی آزاد کاربر → لیست ساعت یکتا و مرتب‌شده.

    🆕 ممیزی (بخش H): پسوندهای صبح/عصر/شب/am/pm واقعاً در تبدیل لحاظ می‌شوند:
      «8 pm» → 20:00 | «۸ صبح» → 08:00 | «۱۰ شب و ۶ صبح» → [06:00, 22:00]
      «8» بدون پسوند → 08:00 (رفتار پیش‌بینی‌پذیر و مستند)
    استراتژی: پسوندها با فاصله از عدد جدا می‌شوند، سپس توکن‌ها به‌ترتیب پیمایش
    می‌شوند و هر پسوند به «نزدیک‌ترین ساعت قبلی» خودش می‌چسبد.
    """
    text = text.strip().translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)
    text = text.replace("بعد الظهر", "بعدازظهر")
    # پسوندها را با فاصله از اطراف جدا کن تا توکن مستقل شوند («8pm» → «8 pm»)
    text = _PERIOD_WORD_RE.sub(r" \1 ", text)
    parts = [p for p in re.split(r"[،,؛;\s]+", text.strip()) if p]

    out: list[str] = []
    pending: str | None = None  # آخرین ساعتِ بدون پسوند
    for p in parts:
        t = _normalize_time(p)
        if t is not None:
            # ساعت جدید؛ اگر ساعتِ بدون پسوندِ قبلی مانده، همین‌جا ثبتش کن
            if pending is not None and pending not in out:
                out.append(pending)
            pending = t
            continue
        # ساعت نیست؛ اگر پسوند صبح/شب/am/pm است، به ساعتِ در انتظار بچسبان
        t2 = _normalize_time(f"{pending or ''} {p}".strip()) if pending else None
        if t2 is not None:
            if t2 in out and pending in out:
                out.remove(pending)
            pending = t2
    if pending is not None and pending not in out:
        out.append(pending)
    return sorted(out)


# ---------------------------------------------------------------------------
# زمان‌بند (JobQueue)
# ---------------------------------------------------------------------------

TEHRAN_TZ = "Asia/Tehran"


def _configured_tzinfo():
    """🆕 ممیزی (بخش H): منطقه‌ی زمانی از پیکربندی (TIMEZONE_OFFSET_HOURS).

    مقدار پیش‌فرض ۳.۵ → نام منطقه‌ای Asia/Tehran (پشتیبانی از تغییرات تاریخی
    قانونی). هر مقدار دیگر → منطقه‌ی ثابت با همان آفست، تا زمان‌بندی همیشه با
    پیکربندی سرور سازگار باشد، نه صرفاً تهران.
    """
    from zoneinfo import ZoneInfo
    raw_offset = getattr(settings, "timezone_offset_hours", 3.5)
    # ⚠️ توجه: `raw or 3.5` غلط است چون 0.0 هم falsy است — ممیزی T08 این را گرفت
    offset = float(raw_offset) if raw_offset is not None else 3.5
    if abs(offset - 3.5) < 1e-9:
        return ZoneInfo(TEHRAN_TZ)
    return _dt_timezone(timedelta(hours=offset))


def _job_prefix(chat_id: int | str) -> str:
    return f"medrem_{chat_id}_"


def unschedule_chat(job_queue: Any, chat_id: int | str) -> None:
    if job_queue is None:
        return
    prefix = _job_prefix(chat_id)
    try:
        for job in list(job_queue.jobs()):
            if job.name and job.name.startswith(prefix):
                job.schedule_removal()
    except Exception as error:
        logger.warning("unschedule_chat failed: %s", error)


def schedule_chat_jobs(job_queue: Any, chat_id: int | str, items: list[dict[str, Any]]) -> int:
    """همه ساعت‌های یک کاربر را (پس از حذف قبلی‌ها) زمان‌بندی می‌کند.

    🆕 v49 (الزام مأموریت): تعداد jobهای «واقعاً ساخته‌شده» برمی‌گردد تا
    فراخواننده بتواند شکستِ بی‌صدای زمان‌بندی را تشخیص دهد و به کاربر پیام
    موفقیت کاذب ندهد. انتظار: مجموع همه ساعت‌های همه داروها.
    """
    if job_queue is None:
        logger.warning("JobQueue در دسترس نیست؛ یادآوری دارو غیرفعال ماند.")
        return 0
    unschedule_chat(job_queue, chat_id)
    try:
        tz = _configured_tzinfo()
    except Exception as error:
        logger.warning("timezone load failed: %s", error)
        return 0
    scheduled = 0
    expected = 0
    for idx, med in enumerate(items):
        for hhmm in med.get("times", []):
            expected += 1
            try:
                hh, mm = hhmm.split(":")
                from datetime import time as dtime
                job_queue.run_daily(
                    _send_reminder,
                    time=dtime(hour=int(hh), minute=int(mm), tzinfo=tz),
                    days=tuple(range(7)),
                    chat_id=int(chat_id),
                    name=f"{_job_prefix(chat_id)}{idx}_{hhmm}",
                    data={"chat_id": int(chat_id), "name": med.get("name", "")},
                )
                scheduled += 1
            except Exception as error:
                logger.warning("scheduling %s %s failed: %s", chat_id, hhmm, error)
    return scheduled


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    if job is None:
        return
    data = job.data or {}
    chat_id = data.get("chat_id")
    name = data.get("name", "")
    lang = context.application.bot_data.get("user_langs", {}).get(str(chat_id), "fa")
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=_t(lang, "reminder").format(name=name),
        )
    except Exception as error:
        logger.warning("reminder send failed (%s): %s", chat_id, error)


def schedule_all(application: Any) -> None:
    """در post_init: همه یادآورهای ذخیره‌شده را دوباره زمان‌بندی می‌کند.

    همچنین نگاشت chat_id → زبان را در bot_data می‌سازد تا پیام یادآوری
    به زبان خود کاربر ارسال شود (user_data در زمان job در دسترس نیست).
    """
    job_queue = getattr(application, "job_queue", None)
    mapping: dict[str, str] = {}
    data = _load_meds()
    for chat_id, items in data.items():
        lang = "fa"
        # زبان ذخیره‌شده در persistence (user_data پس از initialize لود شده است)
        try:
            ud = application.user_data.get(int(chat_id), {})
            if isinstance(ud, dict):
                lang = ud.get("lang", "fa")
        except Exception:
            pass
        mapping[chat_id] = lang if lang in ("fa", "en", "ar") else "fa"
        schedule_chat_jobs(job_queue, chat_id, items)
    application.bot_data.setdefault("user_langs", {}).update(mapping)
    total = sum(len(v) for v in data.values())
    logger.info("Medication reminders scheduled: %d users, %d meds.", len(data), total)


def remember_lang(context: ContextTypes.DEFAULT_TYPE, chat_id: int | str) -> None:
    """زبان کاربر را برای استفاده در job یادآوری ذخیره می‌کند."""
    try:
        lang = _get_lang(context)
        context.application.bot_data.setdefault("user_langs", {})[str(chat_id)] = lang
    except Exception:
        pass


# ---------------------------------------------------------------------------
# منو و اکشن‌ها
# ---------------------------------------------------------------------------

async def show_med_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """منوی اصلی یادآور دارو (از callbacks.py با دکمه medication صدا زده می‌شود)."""
    query = update.callback_query
    if query is not None:
        try:
            await query.answer()
        except Exception:
            pass
    remember_lang(context, update.effective_chat.id if update.effective_chat else 0)
    kb = _kb(lang, [
        [( _t(lang, "menu_btn_add"), "med_add")],
        [(_t(lang, "menu_btn_list"), "med_list"), (_t(lang, "menu_btn_del"), "med_del")],
        [(_t(lang, "btn_back"), "back_main"), (_t(lang, "btn_feedback"), "start_feedback")],
    ])
    await _display(update, context, _t(lang, "menu_title"), kb)


async def _display(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, kb: InlineKeyboardMarkup) -> None:
    """نمایش با ویرایش پیام فعلی؛ در صورت شکست، ارسال پیام جدید."""
    query = update.callback_query
    if query is not None and query.message is not None:
        try:
            await query.edit_message_text(text=text, reply_markup=kb)
            return
        except Exception as exc:
            if "not modified" in str(exc).lower():
                return
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is not None:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)
        except Exception as error:
            logger.warning("med display failed: %s", error)


async def med_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لیست / حذف داروها (خارج از ConversationHandler)."""
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    try:
        await query.answer()
    except Exception:
        pass
    lang = _get_lang(context)
    chat_id = update.effective_chat.id
    remember_lang(context, chat_id)
    data = query.data or ""

    if data == "med_list":
        items = get_chat_meds(chat_id)
        if not items:
            await _display(update, context, _t(lang, "list_empty"),
                           _back_feedback_kb(lang, "med_home"))
            return
        lines = [_t(lang, "list_title")]
        for i, med in enumerate(items, 1):
            times = "، ".join(med.get("times", []))
            lines.append(f"{i}. 💊 {med.get('name', '')}\n   ⏰ {times}")
        kb = _kb(lang, [
            [(_t(lang, "menu_btn_add"), "med_add")],
            [(_t(lang, "list_back"), "med_home"), (_t(lang, "btn_feedback"), "start_feedback")],
        ])
        await _display(update, context, "\n".join(lines), kb)
        return

    if data == "med_del":
        items = get_chat_meds(chat_id)
        if not items:
            await _display(update, context, _t(lang, "del_empty"),
                           _back_feedback_kb(lang, "med_home"))
            return
        rows = [[(f"💊 {med.get('name', '')} ({'، '.join(med.get('times', []))})", f"med_del_{i}")]
                for i, med in enumerate(items)]
        rows.append([(_t(lang, "list_back"), "med_home"), (_t(lang, "btn_feedback"), "start_feedback")])
        await _display(update, context, _t(lang, "del_title"), _kb(lang, rows))
        return

    if data.startswith("med_del_"):
        try:
            idx = int(data.replace("med_del_", "", 1))
        except ValueError:
            idx = -1
        items = get_chat_meds(chat_id)
        if 0 <= idx < len(items):
            removed = items.pop(idx)
            _set_chat_meds(chat_id, items)
            unschedule_chat(context.job_queue, chat_id)
            schedule_chat_jobs(context.job_queue, chat_id, items)
            await _display(update, context, _t(lang, "deleted").format(name=removed.get("name", "")),
                           _back_feedback_kb(lang, "med_home"))
        else:
            await _display(update, context, _t(lang, "del_empty"),
                           _back_feedback_kb(lang, "med_home"))
        return

    if data == "med_home":
        kb = _kb(lang, [
            [(_t(lang, "menu_btn_add"), "med_add")],
            [(_t(lang, "menu_btn_list"), "med_list"), (_t(lang, "menu_btn_del"), "med_del")],
            [(_t(lang, "btn_back"), "back_main"), (_t(lang, "btn_feedback"), "start_feedback")],
        ])
        await _display(update, context, _t(lang, "menu_title"), kb)
        return


# ---------------------------------------------------------------------------
# گفتگوی افزودن دارو
# ---------------------------------------------------------------------------

async def med_add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return ConversationHandler.END
    try:
        await query.answer()
    except Exception:
        pass
    lang = _get_lang(context)
    remember_lang(context, update.effective_chat.id if update.effective_chat else 0)
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if len(get_chat_meds(chat_id)) >= 10:
        await _display(update, context, _t(lang, "limit"),
                       _back_feedback_kb(lang, "med_home"))
        return ConversationHandler.END
    await _display(update, context, _t(lang, "ask_name"), None)
    return ASK_MED_NAME


async def receive_med_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or update.message.text is None:
        return ASK_MED_NAME
    lang = _get_lang(context)
    name = update.message.text.strip()
    if len(name) < 2:
        await _reply_tracked(update, context, _t(lang, "ask_name"))
        return ASK_MED_NAME
    if len(name) > 60:
        await _reply_tracked(update, context, _t(lang, "too_long"))
        return ASK_MED_NAME
    context.user_data["med_name"] = name
    await _reply_tracked(update, context, _t(lang, "ask_times"))
    return ASK_MED_TIMES


async def receive_med_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or update.message.text is None:
        return ASK_MED_TIMES
    lang = _get_lang(context)
    times = parse_times(update.message.text)
    if not times:
        await _reply_tracked(update, context, _t(lang, "invalid_time"))
        return ASK_MED_TIMES
    chat_id = update.effective_chat.id
    name = context.user_data.get("med_name", "💊")
    context.user_data.pop("med_name", None)

    items = get_chat_meds(chat_id)
    items.append({"name": name, "times": times})
    _set_chat_meds(chat_id, items)
    # 🩺 سخت‌سازی (تسک ۵ + ممیزی H + الزام مأموریت v49): هیچ خطای زمان‌بندی
    # نباید ثبت دارو را برای کاربر شکست بدهد؛ اما «موفقیت کاذب» هم ممنوع است —
    # اگر تعداد jobهای واقعاً ساخته‌شده کمتر از ساعت‌های ثبت‌شده بود، به خود
    # کاربر صریح گفته می‌شود که ذخیره انجام شده ولی یادآوری فعال نشده است.
    job_queue_ok = False
    expected_jobs = sum(len(m.get("times", [])) for m in items)
    try:
        jq = getattr(context, "job_queue", None)
        if jq is None:
            logger.error(
                "JobQueue در دسترس نیست (APScheduler نصب نیست یا job_queue به بیلدر داده نشده). "
                "دارو ذخیره شد ولی یادآوری زمان‌بندی نشد: chat=%s", chat_id,
            )
        else:
            scheduled = schedule_chat_jobs(jq, chat_id, items)
            if scheduled >= expected_jobs and expected_jobs > 0:
                job_queue_ok = True
            else:
                logger.error(
                    "زمان‌بندی ناقص: chat=%s انتظار=%d ساخته‌شده=%d — به کاربر صادقانه اعلام می‌شود.",
                    chat_id, expected_jobs, scheduled,
                )
    except Exception:
        logger.error("schedule_chat_jobs failed for chat=%s\n%s", chat_id, traceback.format_exc())

    if job_queue_ok:
        saved_text = _t(lang, "saved").format(name=name, times="، ".join(times))
    else:
        saved_text = _t(lang, "saved_no_jobqueue").format(name=name, times="، ".join(times))
    await _reply_tracked(update, context, saved_text, reply_markup=_back_feedback_kb(lang))
    return ConversationHandler.END


async def med_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("med_name", None)
    lang = _get_lang(context)
    if update.message is not None:
        # 🆕 فیکس: قبلاً بدون دکمه ارسال می‌شد و کاربر گیر می‌کرد
        await _reply_tracked(update, context, _t(lang, "cancelled"), reply_markup=_back_feedback_kb(lang))
    return ConversationHandler.END


async def _reply_tracked(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str,
                         reply_markup=None) -> None:
    """🆕 تسک ۳: پاسخ‌های متنی گفتگو ردیابی‌شده ارسال شوند تا با ناوبری پاک شوند."""
    from app.handlers import chunks as chunk_tracker
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None or update.message is None:
        return
    await chunk_tracker.send_tracked(context, chat_id, text, reply_markup)


meds_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(med_add_entry, pattern=r"^med_add$")],
    states={
        ASK_MED_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_med_name)],
        ASK_MED_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_med_times)],
    },
    fallbacks=[
        MessageHandler(filters.COMMAND, med_cancel),
        CallbackQueryHandler(med_cancel, pattern=r"^med_cancel$"),
    ],
    allow_reentry=True,
)
