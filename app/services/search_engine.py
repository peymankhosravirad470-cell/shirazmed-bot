# -*- coding: utf-8 -*-
"""
🔍 موتور جست‌وجوی جامع شیراز مدیکال (مأموریت مکمل — بخش ۱)

جست‌وجوی یکپارچه در «همهٔ» بخش‌های ربات با یک ورودی:
پزشکان و تخصص‌ها، بیمارستان‌ها و کلینیک‌ها، خدمات پاراکلینیکی، بیمه‌ها،
نوبت‌دهی و خدمات ربات، هتل و اقامتگاه، ترانسفر و حمل‌ونقل، مترجم،
گردشگری، بسته‌های درمانی، سالمندان، راهنماها و پرسش‌های متداول و دارو.

اصول:
- سه‌زبانه (fa/ar/en): در «هر سه» نسخهٔ زبانیِ هر فیلد جست‌وجو می‌شود؛
  یعنی کاربر فارسی هم می‌تواند با «Cardiology» پزشک قلب را پیدا کند.
- تحمل غلط املایی: نرمال‌سازی حروف عربی/فارسی + تطبیق پیشوند + فاصلهٔ
  ویرایشی محدود (بدون وابستگی به کتابخانهٔ بیرونی — لیارا فقط requirements).
- نتایج دسته‌بندی‌شده با دکمهٔ پرش مستقیم به همان بخش ربات.
- اصل ضدجعل: فقط روی دادهٔ واقعی مخزن ایندکس می‌زنیم؛ چیزی از خودمان
  نمی‌سازیم. برای «دارو» دادهٔ دارویی عمومی در مخزن وجود ندارد → فقط
  یادآور داروی خود کاربر + مسیر دستیار هوشمند پیشنهاد می‌شود (صادقانه).
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR_REPO = os.path.join(_BASE_DIR, "data")

# ── نرمال‌سازی متن ──────────────────────────────────────────────────────────

# حروف عربی → فارسی (تا «ی» و «ک» در هر دو املای عربی/فارسی یکی شوند)
_CHAR_MAP = str.maketrans({
    "ي": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه", "أ": "ا", "إ": "ا", "ؤ": "و", "ئ": "ی",
    "ٱ": "ا", "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
})
# اعراب و نیم‌فاصله و کاراکترهای شفاف
_STRIP_RE = re.compile(r"[\u064B-\u065F\u0670\u0640\u200c\u200e\u200f]")
_NONWORD_RE = re.compile(r"[^\w\s]")


def normalize(text: Any) -> str:
    """نرمال‌سازی چندزبانه: حروف هم‌شکل عربی/فارسی + اعراب + نیم‌فاصله + اعداد."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).translate(_CHAR_MAP)
    s = _STRIP_RE.sub(" ", s)
    s = s.lower()
    s = _NONWORD_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(text: Any) -> list[str]:
    s = normalize(text)
    return s.split() if s else []


def _edit_distance_at_most(a: str, b: str, max_d: int) -> int:
    """فاصلهٔ ویرایشی با خروج زودهنگام (فقط برای مقایسهٔ کوچک)."""
    if abs(len(a) - len(b)) > max_d:
        return max_d + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            cur.append(v)
            row_min = min(row_min, v)
        if row_min > max_d:
            return max_d + 1
        prev = cur
    return prev[-1]


def _fuzzy_hit(q_tok: str, d_tok: str) -> bool:
    """تطبیق متّاهم یک توکن: پیشوند / زیررشته / فاصلهٔ ویرایشی محدود.

    - طول ۴+ با خطای ۱ حرف، طول ۷+ با خطای ۲ حرف (تقریب سبک fuzzy برای
      غلط املایی رایج فارسی/عربی/انگلیسی).
    - توکن‌های کوتاه (۱-۲ حرف) فقط تطبیق دقیق یا پیشوندی — تا نویز نشویم.
    """
    if not q_tok or not d_tok:
        return False
    if q_tok == d_tok:
        return True
    if len(q_tok) >= 3 and d_tok.startswith(q_tok):
        return True
    if len(q_tok) >= 4 and len(d_tok) >= 4 and q_tok in d_tok:
        return True
    if len(q_tok) == len(d_tok) == 1:
        return False
    if len(q_tok) >= 7:
        max_d = 2
    elif len(q_tok) >= 4:
        max_d = 1
    elif len(q_tok) == 3 and q_tok[:2] == d_tok[:2]:
        # غلط تایپی تک‌حرفی در واژهٔ کوتاه — فقط وقتی دو حرف اول یکسان است
        # (مثلاً «قلو» → «قلب») تا نویز بی‌ربط تولید نشود.
        max_d = 1
    else:
        max_d = 0
    if max_d == 0:
        return False
    return _edit_distance_at_most(q_tok, d_tok, max_d) <= max_d


# ── استخراج متن قابل‌جست‌وجو از آیتم‌های JSON (ساختار تودرتو یا *_fa) ────────

_TEXT_KEYS_SKIP = {"id", "lat", "lng", "phone", "ipd_phone", "ipd_code", "emergency_contact",
                   "support_phone", "website", "email", "patient_satisfaction_score", "score"}


def _field_text(item: dict, base: str) -> str:
    """متن یک فیلد با همهٔ زبان‌هاش — برای ایندکس جست‌وجو."""
    parts: list[str] = []
    obj = item.get(base)
    if isinstance(obj, dict):
        parts.extend(str(v) for v in obj.values() if v)
    elif obj is not None and base not in _TEXT_KEYS_SKIP:
        parts.append(str(obj))
    # شکل تخت: name_fa / name_en / name_ar
    for suffix in ("fa", "en", "ar"):
        v = item.get(f"{base}_{suffix}")
        if v:
            parts.append(str(v))
    return " ".join(parts)


def corpus_text(item: dict) -> str:
    """همهٔ متن‌های متنیِ آیتم (نام، آدرس، توضیح، خدمات، ...) برای ایندکس."""
    out: list[str] = []
    for key, val in item.items():
        if key in _TEXT_KEYS_SKIP:
            continue
        if isinstance(val, dict):
            out.extend(str(v) for v in val.values() if isinstance(v, (str, int, float)))
        elif isinstance(val, list):
            for el in val:
                if isinstance(el, dict):
                    out.extend(str(v) for v in el.values() if isinstance(v, (str, int, float)))
                elif isinstance(el, (str, int, float)):
                    out.append(str(el))
        elif isinstance(val, (str, int, float)):
            out.append(str(val))
    return " ".join(out)


def _display_name(item: dict) -> str:
    """نام نمایشی آیتم: اولین موجود از name{,_fa,_en,_ar} یا title{,...}"""
    for base in ("name", "title"):
        obj = item.get(base)
        if isinstance(obj, dict):
            for l in ("fa", "en", "ar"):
                if obj.get(l):
                    return str(obj[l])
        elif obj:
            return str(obj)
        for suffix in ("_fa", "_en", "_ar", ""):
            v = item.get(f"{base}{suffix}")
            if v and not isinstance(v, dict):
                return str(v)
    return "?"


def _subtitle(item: dict) -> str:
    """زیرنویس نتیجه: نوع/تخصص/دسته یا آدرس کوتاه."""
    for base in ("type", "specialty", "category", "district", "city"):
        obj = item.get(base)
        if isinstance(obj, dict):
            for l in ("fa", "en", "ar"):
                if obj.get(l):
                    return str(obj[l])
        else:
            for suffix in ("_fa", "_en", "_ar", ""):
                v = item.get(f"{base}{suffix}")
                if v:
                    return str(v)
    addr = item.get("address")
    if isinstance(addr, dict):
        for l in ("fa", "en", "ar"):
            if addr.get(l):
                return str(addr[l])
    return ""


# ── بارگذاری فایل‌های داده با کش mtime ──────────────────────────────────────

_file_cache: dict[str, Any] = {}


def load_repo_json(filename: str) -> list | dict:
    """خواندن فایل data/<filename> با کش mtime (دادهٔ مخزن، نه DATA_DIR کاربر)."""
    path = os.path.join(DATA_DIR_REPO, filename)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    cached = _file_cache.get(filename)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("search_engine: خطا در خواندن %s: %s", filename, error)
        data = []
    _file_cache[filename] = (mtime, data)
    return data


# ── تعریف دسته‌های جست‌وجو (فقط دادهٔ واقعی مخزن) ─────────────────────────────

# هر دسته: id، آیکون، برچسب سه‌زبانه، منبع داده، و نگاشت دکمهٔ نتیجه.
# callback نتیجه: «srchgo_<cat>_<idx>» (کارت جزئیات در خود جست‌وجو) یا
# callback موجود ربات (پرش مستقیم به همان بخش).
JSON_CATS: list[dict[str, Any]] = [
    {"id": "hospitals", "icon": "🏥", "file": "hospitals.json",
     "label": {"fa": "بیمارستان‌ها و کلینیک‌ها", "en": "Hospitals & Clinics", "ar": "المستشفيات والعيادات"}},
    {"id": "paramedical", "icon": "🩺", "file": "paramedical.json",
     "label": {"fa": "خدمات پاراکلینیکی", "en": "Paramedical Services", "ar": "الخدمات المساندة"}},
    {"id": "hotels", "icon": "🏨", "file": "hotels.json",
     "label": {"fa": "هتل‌ها", "en": "Hotels", "ar": "الفنادق"}},
    {"id": "motels", "icon": "🛏️", "file": "motels.json",
     "label": {"fa": "مهمان‌پذیرها", "en": "Guest Houses", "ar": "بيوت الضيافة"}},
    {"id": "tourist_houses", "icon": "🏠", "file": "tourist_houses.json",
     "label": {"fa": "خانه‌های مسافر", "en": "Traveler Houses", "ar": "بيوت المسافرين"}},
    {"id": "transport", "icon": "🚐", "file": "transport.json",
     "label": {"fa": "ترانسفر و حمل‌ونقل", "en": "Transfer & Transport", "ar": "النقل والانتقالات"}},
    {"id": "hubs", "icon": "🚉", "file": "transport_hubs.json",
     "label": {"fa": "پایانه‌ها و فرودگاه", "en": "Terminals & Airport", "ar": "المحطات والمطار"}},
    {"id": "insurance", "icon": "🛡️", "file": "insurances.json",
     "label": {"fa": "بیمه‌ها", "en": "Insurances", "ar": "التأمينات"}},
    {"id": "elderly", "icon": "🏡", "file": "elderly_homes.json",
     "label": {"fa": "خدمات سالمندان", "en": "Elderly Care", "ar": "خدمات المسنين"}},
    {"id": "attractions", "icon": "🏛️", "file": "leisure_city.json", "extra_file": "leisure_outside.json",
     "label": {"fa": "جاذبه‌های گردشگری", "en": "Tourist Attractions", "ar": "المعالم السياحية"}},
    {"id": "packages", "icon": "💎", "file": "packages.json",
     "label": {"fa": "بسته‌های درمانی", "en": "Treatment Packages", "ar": "الباقات العلاجية"}},
    {"id": "guide", "icon": "📖", "file": "patient_guide.json",
     "label": {"fa": "راهنماها و پرسش‌های متداول", "en": "Guides & FAQ", "ar": "الأدلة والأسئلة الشائعة"}},
    {"id": "support", "icon": "🤝", "file": "support.json",
     "label": {"fa": "مراکز پشتیبانی و اورژانس", "en": "Support Centers", "ar": "مراكز الدعم"}},
]

CAT_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in JSON_CATS}

# 🧭 خدمات خودِ ربات (نوبت‌دهی، مترجم، تاکسی، یادآور دارو و…) — هر نتیجه
# مستقیماً به همان دکمهٔ ربات می‌پرد. ایندکس از برچسب‌های سه‌زبانهٔ خود ربات
# ساخته می‌شود تا جست‌وجوی «appointment» یا «مترجم» هم جواب بدهد.
SERVICES: list[dict[str, Any]] = [
    {"id": "svc_booking", "cat": "services", "icon": "📅", "callback": "start_booking",
     "label": {"fa": "نوبت‌دهی و رزرو پزشک", "en": "Doctor Appointment Booking", "ar": "حجز موعد الطبيب"}},
    {"id": "svc_medical", "cat": "services", "icon": "👨‍⚕️", "callback": "medical",
     "label": {"fa": "پزشکان و تخصص‌ها", "en": "Doctors & Specialties", "ar": "الأطباء والتخصصات"}},
    {"id": "svc_emergency", "cat": "services", "icon": "🚨", "callback": "emergency",
     "label": {"fa": "اضطراری و تماس فوری", "en": "Emergency", "ar": "الطوارئ"}},
    {"id": "svc_advisor", "cat": "services", "icon": "🩺", "callback": "advisor",
     "label": {"fa": "مشاور سلامت و علائم خطر", "en": "Health Advisor", "ar": "مستشار الصحة"}},
    {"id": "svc_translator", "cat": "services", "icon": "🗣️", "callback": "translator",
     "label": {"fa": "مترجم همراه", "en": "Translator", "ar": "المترجم"}},
    {"id": "svc_taxi", "cat": "services", "icon": "🚕", "callback": "taxi",
     "label": {"fa": "تاکسی و درخواست سفر", "en": "Taxi", "ar": "سيارة الأجرة"}},
    {"id": "svc_medication", "cat": "services", "icon": "💊", "callback": "medication",
     "label": {"fa": "یادآور دارو", "en": "Medication Reminder", "ar": "منبه الدواء"}},
    {"id": "svc_file", "cat": "services", "icon": "📋", "callback": "file",
     "label": {"fa": "پروندهٔ من", "en": "My Medical File", "ar": "ملفي الطبي"}},
    {"id": "svc_appointments", "cat": "services", "icon": "🗓️", "callback": "appointments",
     "label": {"fa": "نوبت‌های من و پیگیری", "en": "My Appointments", "ar": "مواعيدي"}},
    {"id": "svc_ai", "cat": "services", "icon": "🤖", "callback": "ai_assistant",
     "label": {"fa": "دستیار هوشمند — هوش مصنوعی (سؤال دارویی و پزشکی)", "en": "AI Assistant (drug & medical Q&A)", "ar": "المساعد الذكي (أسئلة الأدوية والطبية)"}},
    {"id": "svc_advisor_kw", "cat": "services", "icon": "🩺", "callback": "advisor",
     "label": {"fa": "مشاور سلامت — علائم خطر (سوختگی، درد سینه، سکته، تشنج، خونریزی، آسم، بارداری، کودک)",
               "en": "Health Advisor — warning signs (burn, chest pain, stroke, seizure, bleeding, asthma, pregnancy, child)",
               "ar": "مستشار الصحة — علامات الخطر (حرق، ألم الصدر، سكتة، تشنج، نزيف، ربو، حمل، طفل)"}},
    {"id": "svc_invite", "cat": "services", "icon": "🎁", "callback": "invite",
     "label": {"fa": "دعوت دوستان و پاداش", "en": "Invite Friends & Rewards", "ar": "دعوة الأصدقاء"}},
    {"id": "svc_survey", "cat": "services", "icon": "📝", "callback": "start_survey",
     "label": {"fa": "نظرسنجی و شکایت", "en": "Survey & Complaints", "ar": "الاستبيان والشكاوى"}},
]

# 🩻 تخصص‌های پزشکی — از برچسب‌های سه‌زبانهٔ doctor_loader (دادهٔ واقعی)


def _specialty_results(query_toks: list[str]) -> list[dict[str, Any]]:
    """جست‌وجو در تخصص‌ها + اسامی پزشکان فعال (دادهٔ واقعی data/doctors)."""
    from app.services import doctor_loader
    out = []
    for spec in doctor_loader.load_specialties():
        key = spec["key"]
        names = {"fa": doctor_loader.get_label(key, "fa"), "en": doctor_loader.get_label(key, "en"),
                 "ar": doctor_loader.get_label(key, "ar")}
        docs = doctor_loader.load_doctors(key)
        # ۱) تطبیق نام تخصص (سه‌زبانه + کلید)
        spec_all = normalize(" ".join(names.values()) + " " + key)
        s = _score(query_toks, spec_all, normalize(" ".join(names.values())))
        if s > 0:
            out.append({
                "cat": "doctors", "idx": key, "score": s + 3,  # تخصص اولویت دارد
                "title": names["fa"],
                "subtitle": f"👨‍⚕️ {spec['count']}",
                "callback": f"med_spec_{key}_0",
            })
        # ۲) تطبیق نام هر پزشک فعال
        for d in docs:
            d_name = str(d.get("name_fa", ""))
            d_norm = normalize(d_name)
            ds = _score(query_toks, d_norm, d_norm)
            if ds > 0:
                out.append({
                    "cat": "doctors", "idx": key, "score": ds + 4,  # نام دقیق پزشک بالاترین اولویت
                    "title": d_name,
                    "subtitle": names["fa"],
                    "callback": f"med_spec_{key}_0",
                })
    return out


def _has_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _score(query_toks: list[str], corpus_norm: str, title_norm: str) -> int:
    """امتیاز تطبیق: بالاتر = بهتر. صفر = نامرتبط."""
    if not query_toks:
        return 0
    score = 0
    title_toks = title_norm.split()
    corpus_toks = corpus_norm.split()
    for qt in query_toks:
        if len(qt) < 2:
            return 0  # کوئریِ تک‌حرفی — جست‌وجوی بی‌معنی و پرنویز
        best = 0
        # ۱) زیررشتهٔ مستقیم در عنوان (قوی‌ترین)
        if qt in title_norm:
            best = max(best, 8)
        # ۲) تطبیق توکن عنوان: دقیق/پیشوند/فازی
        for dt in title_toks:
            if dt == qt:
                best = max(best, 7)
            elif len(qt) >= 3 and dt.startswith(qt):
                best = max(best, 5)
            elif _fuzzy_hit(qt, dt):
                best = max(best, 3)
        # ۳) تطبیق در کل متن آیتم (ضعیف‌تر — فقط زیررشتهٔ دقیق یا فازی سخت‌گیرانه؛
        #    سقف فاصله ۱ و فقط واژه‌های ≥۴ حرفی تا کوئری‌های بی‌معنی نتیجهٔ تصادفی نگیرند)
        if best == 0 and len(qt) >= 3:
            if qt in corpus_norm:
                best = 4
            elif len(qt) >= 4:
                for dt in corpus_toks:
                    if len(dt) >= 4 and _edit_distance_at_most(qt, dt, 1) <= 1:
                        best = 2
                        break
        if best == 0:
            return 0  # هر توکن کوئری باید جایی دیده شود — نتیجهٔ بی‌ربط ممنوع
        score += best
    return score


def _unwrap(data: Any) -> list:
    """بازکردن ساختارهای بسته‌بندی‌شدهٔ واقعی فایل‌های داده:
    - packages.json → {"version", "footer", "packages": [...]}
    - transport_hubs.json → {"shiraz_transport_hubs": [...]}
    - patient_guide.json → یک dict تختِ راهنمای جامع (تک‌آیتم)
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("packages", "shiraz_transport_hubs"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return []


def _iter_cat_items(cat: dict[str, Any]) -> list[tuple[int, dict]]:
    """همهٔ آیتم‌های واقعیِ یک دسته (فایل اصلی + فایل اضافه)."""
    items: list[tuple[int, dict]] = []
    data = _unwrap(load_repo_json(cat["file"]))
    items.extend((i, it) for i, it in enumerate(data) if isinstance(it, dict))
    extra = cat.get("extra_file")
    if extra:
        data2 = _unwrap(load_repo_json(extra))
        base = len(items)
        items.extend((base + i, it) for i, it in enumerate(data2) if isinstance(it, dict))
    return items


def _query_token_variants(q_toks: list[str]) -> list[list[str]]:
    """نسخه‌های ساده‌شدهٔ کوئری برای «عبارت‌های مشابه»:

    جست‌وجوی چندکلمه‌ای اول با همهٔ توکن‌ها امتحان می‌شود؛ اگر دسته‌ای نتیجه
    نداد، با توکن‌های بلندتر (۳+ حرف) دوباره تلاش می‌شود تا «دکتر قلبی» یا
    «پکیج مادر» که کلیدواژه‌هایشان در داده یکی نیست هم نتیجه بدهد.
    توکن‌های خیلی کوتاه (۱-۲ حرف مثل «من») هرگز تنهامحک نمی‌شوند (نویز).
    """
    strong = [t for t in q_toks if len(t) >= 3]
    variants: list[list[str]] = []
    if strong and len(strong) < len(q_toks):
        variants.append(strong)
    if len(strong) > 1:
        # هر توکن بلند به‌تنهایی (مرتب بر اساس طول نزولی)
        for t in sorted(strong, key=len, reverse=True):
            variants.append([t])
    return variants


def search(query: str, lang: str = "fa", per_cat_limit: int = 3, max_groups: int = 8) -> list[dict[str, Any]]:
    """جست‌وجوی جامع. خروجی: گروه‌های دسته‌بندی‌شده.

    هر گروه: {id, icon, label, results: [{idx, title, subtitle, callback, score}]}
    - lang فقط برای «برچسب گروه» است؛ جست‌وجو همیشه سه‌زبانه است.
    - چندکلمه‌ای: اول تطبیق کامل همهٔ توکن‌ها؛ در نبود نتیجه، توکن‌های بلند
      به‌صورت تدریجی (subset fallback).
    """
    q = normalize(query)
    if not q:
        return []
    q_toks = q.split()
    groups: dict[str, dict[str, Any]] = {}

    # ۱) دسته‌های JSON واقعی
    for cat in JSON_CATS:
        scored = []
        tok_variants = [q_toks] + _query_token_variants(q_toks)
        for variant in tok_variants:
            if scored:
                break
            for idx, item in _iter_cat_items(cat):
                title = _display_name(item)
                if title == "?":
                    continue  # آیتم بدون نام نمایشی — قابل نشان‌دادن نیست، نتیجه نمی‌شود
                t_norm = normalize(title)
                c_norm = normalize(corpus_text(item))
                s = _score(variant, c_norm, t_norm)
                if s > 0:
                    scored.append({
                        "idx": idx, "score": s, "title": title,
                        "subtitle": _subtitle(item), "callback": f"srchgo_{cat['id']}_{idx}",
                    })
        if scored:
            scored.sort(key=lambda r: -r["score"])
            scored = scored[:per_cat_limit]
            groups[cat["id"]] = {
                "id": cat["id"], "icon": cat["icon"], "label": cat["label"][lang] if lang in cat["label"] else cat["label"]["fa"],
                "results": scored,
            }

    # ۲) تخصص‌ها و پزشکان
    spec_hits = []
    for variant in [q_toks] + _query_token_variants(q_toks):
        spec_hits = _specialty_results(variant)
        if spec_hits:
            break
    if spec_hits:
        spec_hits.sort(key=lambda r: -r["score"])
        groups["doctors"] = {
            "id": "doctors", "icon": "👨‍⚕️",
            "label": {"fa": "پزشکان و تخصص‌ها", "en": "Doctors & Specialties", "ar": "الأطباء والتخصصات"}[lang] if lang in ("fa", "en", "ar") else "پزشکان و تخصص‌ها",
            "results": spec_hits[:per_cat_limit],
        }

    # ۳) خدمات ربات
    svc_hits = []
    for variant in [q_toks] + _query_token_variants(q_toks):
        for svc in SERVICES:
            names = svc["label"]
            t_norm = normalize(" ".join(names.values()))
            s = _score(variant, t_norm, t_norm)
            if s > 0:
                svc_hits.append({"idx": svc["id"], "score": s + 2, "title": names.get(lang) or names["fa"],
                                 "subtitle": "", "callback": svc["callback"]})
        if svc_hits:
            break
    if svc_hits:
        svc_hits.sort(key=lambda r: -r["score"])
        groups["services"] = {
            "id": "services", "icon": "🧭",
            "label": {"fa": "خدمات ربات", "en": "Bot Services", "ar": "خدمات البوت"}[lang],
            "results": svc_hits[:per_cat_limit],
        }

    # مرتب‌سازی گروه‌ها بر اساس بهترین امتیاز هر گروه
    ordered = sorted(groups.values(), key=lambda g: -max(r["score"] for r in g["results"]))
    return ordered[:max_groups]


def get_item(cat_id: str, idx: int) -> dict | None:
    """آیتم خام برای نمایش کارت جزئیات نتیجه."""
    cat = CAT_BY_ID.get(cat_id)
    if not cat:
        return None
    for i, item in _iter_cat_items(cat):
        if i == idx:
            return item
    return None


def result_count() -> int:
    """آمار ایندکس (برای پیام راهنمای جست‌وجو — صادقانه از دادهٔ واقعی)."""
    total = 0
    for cat in JSON_CATS:
        total += len(_iter_cat_items(cat))
    try:
        from app.services import doctor_loader
        total += sum(s["count"] for s in doctor_loader.load_specialties())
    except Exception:
        pass
    return total
