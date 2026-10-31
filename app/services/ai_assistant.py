# -*- coding: utf-8 -*-
"""
دستیار هوشمند امن شیراز مدیکال (مأموریت: آیتم ۱ از ۲۰ قابلیت).

قواعد سختِ ایمنی (غیرقابل‌گذر):
۱) هیچ تشخیص یا تجویز پزشکی مستقلی انجام نمی‌دهد — فقط راهنمایی عمومی و معرفی خدمات.
۲) «پرچم‌های سرخ» (علائم اورژانسی) همیشه پاسخ اورژانس می‌گیرند، حتی وقتی LLM فعال است.
۳) در هر پاسخ پزشکی، ارجاع به پزشک/مرکز درمانی درج می‌شود.
۴) بدون کلید API → «حالت راهنما» (تطبیق نیت روی سرویس‌های خود ربات) با یادداشت
   صادقانه؛ هیچ پاسخ جعلیِ «هوش مصنوعی» تولید نمی‌شود.

سرویس خالص (بدون وابستگی تلگرام) — قابل تست واحد.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 25
_MAX_REPLY_CHARS = 1200

# ─────────────────────────── پرچم‌های سرخ (اورژانس) ───────────────────────────
# کلیدواژه‌ها به‌صورت رشته‌های کوچک‌شده؛ تطبیق روی متن نرمال‌شدهٔ کاربر.
_RED_FLAG_KEYWORDS: tuple[str, ...] = (
    # فارسی
    "درد قفسه سینه", "درد سینه", "قفسه سینه‌ام", "سینه‌ام درد",
    "تنگی نفس", "نفس نمی‌کشم", "نفسم نمی‌رسد", "خفگی",
    "سکته", "فلج", "بدنم بی‌حس", "بی‌حس شد", "لبم کج", "حرف زدن نمی‌توانم",
    "خونریزی شدید", "خونریزی نمی‌بندد", "خون زیاد",
    "بیهوش", "غش کرد", "فوت", "ضربان نمی‌زند",
    "تشنج", "تشنگ‌", "صرع گرفت",
    "خودکشی", "خودم را بکشم", "زندگی را تمام کنم",
    # English
    "chest pain", "can't breathe", "cannot breathe", "shortness of breath",
    "severe bleeding", "unconscious", "stroke", "sudden weakness",
    "seizure", "suicide", "kill myself", "end my life",
    # عربی
    "ألم في الصدر", "ضيق في التنفس", "نزيف شديد", "فقدان الوعي", "سكتة",
    "تشنج", "الانتحار",
)

_EMERGENCY_TEXTS: dict[str, str] = {
    "fa": (
        "🚨 وضعیت شما می‌تواند اورژانسی باشد؛ لطفاً همین حالا اقدام کنید:\n\n"
        "• ambulance اورژانس کشور: ۱۱۵\n"
        "• اورژانس تماس اجتماعی: ۱۲۳\n"
        "• اگر نزدیک هستید، مستقیم به اورژانس نزدیک‌ترین بیمارستان بروید.\n\n"
        "⏱ منتظر پاسخ من نمانید — این دستیار جای پزشک و اورژانس را نمی‌گیرد.\n"
        "💙 شماره مستقیم IPD بیمارستان‌ها در بخش «غیرپزشکی ← بیمارستان‌ها» موجود است."
    ),
    "en": (
        "🚨 Your situation may be an emergency — please act now:\n\n"
        "• National emergency ambulance: 115\n"
        "• Social emergency: 123\n"
        "• Or go straight to the nearest hospital ER.\n\n"
        "⏱ Do not wait for this assistant — it can never replace a doctor or EMS.\n"
        "💙 Direct IPD phone numbers are listed under Non-medical → Hospitals."
    ),
    "ar": (
        "🚨 قد تكون حالتك طارئة — يرجى التصرف فوراً:\n\n"
        "• إسعاف الطوارئ: 115\n"
        "• الطوارئ الاجتماعية: 123\n"
        "• أو توجّه مباشرة إلى أقرب طوارئ مستشفى.\n\n"
        "⏱ لا تنتظر هذا المساعد — لا يُغني عن الطبيب أو الإسعاف.\n"
        "💙 أرقام IPD المباشرة في: غير الطبي ← المستشفيات."
    ),
}

# ─────────────────────────── نیت‌ها (حالت راهنما) ───────────────────────────
# هر نیت: کلیدواژه‌ها (سه‌زبانه) + پاسخ راهنما که کاربر را به بخش درست منو وصل می‌کند.
_INTENTS: tuple[dict[str, Any], ...] = (
    {
        "key": "booking",
        "kw": ("نوبت", "وقت دکتر", "رزرو", " appointment", "booking", "book", "موعد", "حجز"),
        "text": {
            "fa": "برای نوبت‌دهی، دکمهٔ «📅 نوبت بگیر» را بزنید؛ تخصص ← پزشک ← روز ← ساعت را انتخاب می‌کنید و نوبت شما همان لحظه ثبت می‌شود.",
            "en": "Tap «📅 Book Appointment»; choose specialty → doctor → day → time. Your slot is confirmed on the spot.",
            "ar": "اضغط «📅 احجز موعداً»؛ اختر التخصص ← الطبيب ← اليوم ← الوقت، وسيُثبَّت موعدك فوراً.",
        },
    },
    {
        "key": "costs",
        "kw": ("هزینه", "قیمت", "تعرفه", "چند", "cost", "price", "fee", "تكلفة", "سعر"),
        "text": {
            "fa": "هزینهٔ ویزیت پایه در ربات ۱۰۰٬۰۰۰ تومان است و در پرداخت آنلاین نمایش داده می‌شود. سایر هزینه‌های درمانی را فقط پزشک/بیمارستان طبق تعرفه رسمی اعلام می‌کند — ما عدد جعلی نمی‌گوییم. لیست بیمه‌ها: دکمهٔ «🏥 بیمه».",
            "en": "The base visit fee in this bot is 100,000 Toman, shown at online payment. Any other treatment cost is quoted only by the doctor/hospital per official tariffs — we never guess numbers. Insurance list: the «🏥 Insurance» button.",
            "ar": "أجرة الكشف الأساسية في هذا البوت 100,000 تومان وتظهر عند الدفع. أي تكاليف علاجية أخرى يحددها الطبيب/المستشفى حسب التعريفة الرسمية — لا نخمّن الأرقام. قائمة التأمين: زر «🏥 التأمين».",
        },
    },
    {
        "key": "insurance",
        "kw": ("بیمه", "insurance", "تأمين", "پوشش بیمه"),
        "text": {
            "fa": "لیست ۳۳ بیمهٔ تحت پوشش با تلفن و دفاتر شیراز در دکمهٔ «🏥 بیمه» منوی اصلی است. برای سهم بیمه در پرداخت، گزینهٔ «سهم بیمه» را انتخاب کنید.",
            "en": "All 33 supported insurers (with Shiraz offices) are under the «🏥 Insurance» button. For insurance share, choose the insurance-share option at payment.",
            "ar": "قائمة 33 شركة تأمين مدعومة (مع مكاتب شيراز) تحت زر «🏥 التأمين». لحصة التأمين اختر الخيار عند الدفع.",
        },
    },
    {
        "key": "hotel",
        "kw": ("هتل", "اقامت", "مهمانپذیر", "hotel", "stay", "accommodation", "فندق", "إقامة"),
        "text": {
            "fa": "۲۰ هتل، ۱۴ مهمان‌پذیر و ۱۰ خانهٔ مسافر با فیلدهای کامل در بخش «غیرپزشکی» هستند؛ برای هر مورد دکمهٔ نقشه (گوگل/نشان/بلد/وِیز) هم داریم.",
            "en": "20 hotels, 14 motels and 10 guest houses with full details live in the Non-medical section; each has map buttons (Google/Neshan/Balad/Waze).",
            "ar": "20 فندقاً و 14 موتيلاً و 10 بيوت للرحّل بتفاصيل كاملة في قسم «غير الطبي»، ولكل منها أزرار الخريطة.",
        },
    },
    {
        "key": "visa",
        "kw": ("ویزا", "روادید", "مدارک", "visa", "documents", "تأشيرة", "جواز سفر"),
        "text": {
            "fa": "مدارک ویزای درمانی و مراحل پذیرش بیمار خارجی، کامل در دکمهٔ «📖 راهنمای بیمار» آمده است.",
            "en": "Medical-visa documents and the foreign-patient admission steps are fully listed under «📖 Patient Guide».",
            "ar": "مستندات التأشيرة العلاجية وخطوات قبول المريض الأجنبي مذكورة كاملة في «📖 دليل المريض».",
        },
    },
    {
        "key": "transport",
        "kw": ("ترانسفر", "فرودگاه", "تاکسی", "پایانه", "transport", "airport", "taxi", "transfer", "نقل", "مطار"),
        "text": {
            "fa": "پایانه‌ها (فرودگاه/راه‌آهن/ترمینال‌ها) در دکمهٔ «🚏 پایانه‌ها»، اسنپ/تپسی در «🚕 تاکسی» و ثبت همراه بیمار برای ترانسفر در منو هست.",
            "en": "Terminals (airport/rail/bus) under «🚏 Hubs», Snapp/Tapsi under «🚕 Taxi», and the patient-companion signup for transfers is in the menu.",
            "ar": "المحطات (مطار/سكة حديد/حافلات) في «🚏 المحطات»، سناب/تапسي في «🚕 تاكسي»، وتسجيل مرافق المريض في القائمة.",
        },
    },
    {
        "key": "translator",
        "kw": ("مترجم", "ترجمه", "زبان", "translator", "translate", "interpreter", "مترجم", "لغة"),
        "text": {
            "fa": "مراکز پشتیبانی بیماران خارجی با زبان‌های پشتیبانی‌شده در دکمهٔ «🛟 پشتیبانی» است؛ مترجم آنلاین فوری هم در «🗣 مترجم» و «🤖 دستیار هوشمند».",
            "en": "Foreign-patient support centers (with languages) are under «🛟 Support»; instant translation via «🗣 Translator» or this AI assistant.",
            "ar": "مراكز دعم المرضى الأجانب (باللغات) في «🛟 الدعم»؛ والترجمة الفورية عبر «🗣 المترجم» أو هذا المساعد.",
        },
    },
    {
        "key": "tourism",
        "kw": ("گردش", "جاذبه", "باغ", "حافظیه", "توریست", "tourism", "attraction", "visit shiraz", "سياحة", "معالم"),
        "text": {
            "fa": "جاذبه‌های داخل شهر (۱۰ مورد) و اطراف فارس (۱۲ مورد) با بلیت/فصل/دسترس‌پذیری در دکمهٔ «🎡 گردشگری» است.",
            "en": "City attractions (10) and Fars surroundings (12) with tickets/season/accessibility are under «🎡 Tourism».",
            "ar": "معالم المدينة (10) ومحيط فارس (12) مع التذاكر/الموسم/الوصول في «🎡 السياحة».",
        },
    },
    {
        "key": "packages",
        "kw": ("پکیج", "بسته", "package", "bundle", "باقة", "حزمة"),
        "text": {
            "fa": "بسته‌های گردشگری سلامت (ویزیت + بیمارستان + اقامت + گشت) در دکمهٔ «💎 پکیج» منو قابل مشاهده‌اند.",
            "en": "Health-tourism packages (visit + hospital + stay + tour) are listed under the «💎 Package» button.",
            "ar": "باقات السياحة العلاجية (كشف + مستشفى + إقامة + جولة) في زر «💎 باقة».",
        },
    },
    {
        "key": "meds",
        "kw": ("یادآور", "دارو", "قرص", "medication", "reminder", "pill", "medicine", "دواء", "تذكير"),
        "text": {
            "fa": "برای یادآور دارو، دکمهٔ «💊 یادآور دارو» را بزنید و ساعت‌ها را بنویسید (حتی بدون دونقطه، مثل 2323).",
            "en": "Use the «💊 Medication Reminder» button and type your times — flexible input like 2323 works.",
            "ar": "استخدم زر «💊 تذكير الدواء» واكتب الأوقات — حتى بدون نقطتين مثل 2323.",
        },
    },
    {
        "key": "doctors",
        "kw": ("پزشک", "دکتر", "متخصص", "doctor", "specialist", "surgeon", "طبيب", "أخصائي"),
        "text": {
            "fa": "پزشکان تاییدشدهٔ هر تخصص با صفحه‌بندی در دکمهٔ «🩺 خدمات پزشکی» هستند؛ اگر تخصص موردنظر را نیافتید، همان‌جا تخصص دیگری را باز کنید یا با پشتیبانی در تماس باشید.",
            "en": "Verified doctors per specialty (paginated) are under «🩺 Medical Services»; if your specialty isn't listed, open another one or contact support.",
            "ar": "الأطباء المعتمدون لكل تخصص (مقسّم صفحات) في «🩺 الخدمات الطبية»؛ إن لم تجد تخصصك افتح تخصصاً آخر أو تواصل مع الدعم.",
        },
    },
)

_INTENT_MEDICAL_HINT = {
    "fa": "🩺 برای هر مشکل پزشکی، تشخیص فقط با پزشک است — از «🩺 خدمات پزشکی» پزشک مناسب را پیدا کنید یا «📅 نوبت بگیر».",
    "en": "🩺 For any medical problem, diagnosis belongs to a doctor — find one under «🩺 Medical Services» or tap «📅 Book Appointment».",
    "ar": "🩺 أي مشكلة طبية تشخيصها للطبيب — اعثر على طبيب من «🩺 الخدمات الطبية» أو اضغط «📅 احجز موعداً».",
}

_GENERIC_TEXTS: dict[str, str] = {
    "fa": (
        "من راهنمای شیراز مدیکال هستم و می‌توانم شما را به این‌ها برسانم:\n"
        "📅 نوبت‌دهی | 🩺 پزشکان و بیمارستان‌ها | 🏨 اقامت | 🚏 ترانسفر | 🗣 مترجم | "
        "🏥 بیمه | 💎 پکیج‌ها | 🎡 گردشگری | 💊 یادآور دارو | 🚨 اورژانس\n\n"
        "سؤالتان را روشن‌تر بنویسید (مثلاً «نوبت قلب» یا «هتل نزدیک بیمارستان») یا از دکمه‌های منو استفاده کنید.\n"
        "📞 پشتیبانی انسانی: 190"
    ),
    "en": (
        "I'm the Shiraz Medical guide and can point you to:\n"
        "📅 Booking | 🩺 Doctors & hospitals | 🏨 Stay | 🚏 Transfer | 🗣 Translator | "
        "🏥 Insurance | 💎 Packages | 🎡 Tourism | 💊 Med reminders | 🚨 Emergency\n\n"
        "Rephrase your question (e.g. “heart appointment” or “hotel near hospital”) or use the menu buttons.\n"
        "📞 Human support: 190"
    ),
    "ar": (
        "أنا مرشد شيراز ميديكال وأوجّهك إلى:\n"
        "📅 الحجز | 🩺 الأطباء والمستشفيات | 🏨 الإقامة | 🚏 النقل | 🗣 المترجم | "
        "🏥 التأمين | 💎 الباقات | 🎡 السياحة | 💊 تذكير الدواء | 🚨 الطوارئ\n\n"
        "أعد صياغة سؤالك (مثل «موعد قلب» أو «فندق قريب من المستشفى») أو استخدم أزرار القائمة.\n"
        "📞 الدعم البشري: 190"
    ),
}

_GUIDE_NOTE: dict[str, str] = {
    "fa": "\n\n💡 این پاسخ در «حالت راهنما» تولید شد (سرویس هوش مصنوعی فعال نیست).",
    "en": "\n\n💡 This is a guide-mode answer (AI service is not configured).",
    "ar": "\n\n💡 هذه إجابة «وضع الإرشاد» (خدمة الذكاء الاصطناعي غير مُفعّلة).",
}

_DISCLAIMER: dict[str, str] = {
    "fa": "\n\n⚠️ این دستیار تشخیص و تجویز نمی‌کند؛ برای مسائل پزشکی به پزشک مراجعه کنید.",
    "en": "\n\n⚠️ This assistant does not diagnose or prescribe; see a doctor for medical matters.",
    "ar": "\n\n⚠️ هذا المساعد لا يشخّص ولا يصف الدواء؛ راجع الطبيب للأمور الطبية.",
}

# ─────────────────────────── پرامپت سیستم (وقتی LLM فعال است) ───────────────────────────
_SYSTEM_PROMPT = (
    "You are the official assistant of 'Shiraz Medical', a health-tourism service in Shiraz, Iran "
    "(doctors, hospitals, accommodation, airport transfer, translators, insurance, tourism). "
    "HARD RULES: Never diagnose, never prescribe, never suggest doses or stop/continue medication. "
    "For any symptom or medical question: advise seeing a doctor, and mention emergency number 115 for urgent cases. "
    "Only give general information and guide users to the bot services. Never invent prices, doctors, or availability. "
    "Answer in the user's language (fa/en/ar). Keep answers under 120 words, warm and practical."
)


def _normalize(text: str) -> str:
    """نرمال‌سازی سبک برای تطبیق کلیدواژه (بدون دست‌زدن به معنا)."""
    text = (text or "").lower().strip()
    text = text.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    text = re.sub(r"\s+", " ", text)
    return text


# کلیدواژه‌ها هم با همان تابع نرمال می‌شوند تا تطبیق عربی/فارسی (ي/ی، ك/ک) نشکند
_RED_FLAG_NORM: tuple[str, ...] = tuple(_normalize(kw) for kw in _RED_FLAG_KEYWORDS)
_INTENTS_NORM: tuple[dict[str, Any], ...] = tuple(
    {**intent, "kw": tuple(_normalize(kw) for kw in intent["kw"])} for intent in _INTENTS
)


def detect_red_flags(text: str) -> bool:
    """True اگر متن کاربر نشانهٔ اورژانس دارد — هم اولویت بر LLM دارد."""
    norm = _normalize(text)
    return any(kw in norm for kw in _RED_FLAG_NORM)


def emergency_answer(lang: str) -> str:
    return _EMERGENCY_TEXTS.get(lang, _EMERGENCY_TEXTS["fa"])


def fallback_answer(user_text: str, lang: str) -> str:
    """حالت راهنما: تطبیق نیت روی سرویس‌های ربات — بدون هیچ ادعای هوشمندی."""
    norm = _normalize(user_text)
    if norm:
        best: tuple[int, str] | None = None
        for intent in _INTENTS_NORM:
            score = sum(1 for kw in intent["kw"] if kw and kw in norm)
            if score > 0 and (best is None or score > best[0]):
                best = (score, intent["key"])
        if best is not None:
            key = best[1]
            for intent in _INTENTS:
                if intent["key"] == key:
                    return intent["text"].get(lang) or intent["text"]["fa"]
    if detect_red_flags(user_text):
        return emergency_answer(lang)
    return (_GENERIC_TEXTS.get(lang) or _GENERIC_TEXTS["fa"]) + "\n\n" + _INTENT_MEDICAL_HINT.get(lang, _INTENT_MEDICAL_HINT["fa"])


def is_configured() -> bool:
    """آیا سرویس LLM تنظیم شده؟ (AI_API_KEY یا AVALAI_API_KEY در env)"""
    return bool(_api_key())


def _api_key() -> str:
    return (os.getenv("AI_API_KEY") or os.getenv("AVALAI_API_KEY") or "").strip()


def _base_url() -> str:
    return (os.getenv("AI_BASE_URL") or "https://api.avalai.ir/v1").strip().rstrip("/")


def _model() -> str:
    return (os.getenv("AI_MODEL") or "gpt-4o-mini").strip()


def ask_llm(user_text: str, lang: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """فراخوانی OpenAI-Compatible؛ خروجی: {"ok": bool, "text"/"error": str}."""
    key = _api_key()
    if not key:
        return {"ok": False, "error": "ai_not_configured"}
    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for item in (history or [])[-6:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and item.get("content"):
            messages.append({"role": item["role"], "content": str(item["content"])[:800]})
    messages.append({"role": "user", "content": user_text[:1500]})
    try:
        response = requests.post(
            f"{_base_url()}/chat/completions",
            json={"model": _model(), "messages": messages, "temperature": 0.3, "max_tokens": 500},
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=_REQUEST_TIMEOUT,
        )
        body = response.json() if response.content else {}
    except (requests.RequestException, ValueError) as exc:
        logger.warning("ask_llm network failure: %s", exc)
        return {"ok": False, "error": "network"}
    if response.status_code != 200:
        logger.warning("ask_llm http %s", response.status_code)
        return {"ok": False, "error": f"http_{response.status_code}"}
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {"ok": False, "error": "bad_response"}
    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "error": "empty"}
    return {"ok": True, "text": text.strip()[:_MAX_REPLY_CHARS]}


def smart_answer(user_text: str, lang: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """نقطهٔ ورود واحد هندلر: پرچم سرخ ← اورژانس؛ LLM ← پاسخ هوشمند؛ وگرنه حالت راهنما.

    خروجی: {"ok": True, "text": str, "mode": "emergency"|"ai"|"fallback"}
    """
    # ۱) پرچم سرخ همیشه بر همه چیز مقدم است (حتی وقتی LLM فعال است).
    if detect_red_flags(user_text):
        return {"ok": True, "text": emergency_answer(lang), "mode": "emergency"}
    # ۲) سرویس تنظیم‌شده → LLM؛ شکست → حالت راهنما با یادداشت صادقانه.
    if is_configured():
        result = ask_llm(user_text, lang, history)
        if result.get("ok"):
            text = str(result.get("text", ""))
            if detect_red_flags(text):
                # هیچ پاسخ مدلِ تحت‌پرامپت هم نباید اورژانس را دور بزند
                return {"ok": True, "text": emergency_answer(lang), "mode": "emergency"}
            return {"ok": True, "text": text + _DISCLAIMER.get(lang, _DISCLAIMER["fa"]), "mode": "ai"}
        logger.info("AI fallback engaged (reason=%s)", result.get("error"))
    # ۳) حالت راهنما (صادقانه برچسب می‌خورد).
    return {"ok": True, "text": fallback_answer(user_text, lang) + _GUIDE_NOTE.get(lang, _GUIDE_NOTE["fa"]), "mode": "fallback"}
