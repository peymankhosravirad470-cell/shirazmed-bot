# -*- coding: utf-8 -*-
"""🩺 هندلر «مشاور سلامت» (مأموریت مکمل — بخش ۲ و ۳ و ۴)

جریان (طبق مشخصات محصول):
  منوی اصلی → «🩺 مشاور سلامت» → ۱۸ علامت
  → پیام کوتاه درباره اهمیت علامت
  → علامت بحرانی: «یک» پرسش سریع نشانهٔ خطر (بیمار معطل پرسش طولانی نمی‌ماند)
    علامت عادی: ۲ پرسش کوتاه بله/خیر
  → تعیین فوریت:
      اورژانسی → انتخاب کشور (اگر نامعلوم) → شمارهٔ درست + دکمهٔ tel: +
      متن آماده برای اپراتور + افزودن موقعیت «فقط با رضایت» + متن برای همراه
      عادی/فوری → ارجاع: تخصص مرتبط + پزشکان فعال + بیمارستان‌های دارای
      آن تخصص با دکمه‌های مسیریاب + امکان نوبت‌دهی

⚠️ الزامات ایمنی که این هندلر تضمین می‌کند:
- هیچ‌وقت ادعا نمی‌شود «آمبولانس اعزام شد» یا «اورژانس مطلع شد».
- تشخیص و تجویز انجام نمی‌شود؛ فقط ارجاع.
- موقعیت مکانی فقط وقتی پردازش می‌شود که کاربر با دکمهٔ صریح رضایت داده باشد
  و صرفاً در «متن آماده» درج می‌شود؛ هیچ ارسال بیرونی انجام نمی‌شود.
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_keyboard
from app.services import doctor_loader, health_advisor as ha
from app.services.search_engine import load_repo_json, _unwrap
from app.handlers.callbacks import (
    _display,
    _map_row,
    _t,
)

logger = logging.getLogger(__name__)

ADVISOR_T: dict[str, dict[str, str]] = {
    "intro": {
        "fa": "🩺 مشاور سلامت\n\nعلامت مورد نظر را انتخاب کنید تا راهنمای فوریت ببینید.\n\n⚠️ توجه مهم:\n• این بخش «تشخیص پزشکی» یا «تجویز دارو» نیست — فقط کمک می‌کند بفهمید چقدر فوری است و کجا بروید.\n• در موارد تهدیدکنندهٔ حیات، «فوراً» با اورژانس تماس بگیرید: 🇮🇷 ۱۱۵",
        "en": "🩺 Health Advisor\n\nChoose a symptom to see how urgent it is.\n\n⚠️ Important:\n• This is NOT medical diagnosis or prescription — it only helps you know how urgent it is and where to go.\n• In life-threatening cases call emergency immediately: 🇮🇷 115",
        "ar": "🩺 مستشار الصحة\n\nاختر العرض لمعرفة مدى إلحاحه.\n\n⚠️ ملاحظة مهمة:\n• هذا ليس تشخيصاً طبياً ولا وصفة دواء — يساعدك فقط على معرفة درجة الإلحاح وإلى أين تذهب.\n• في الحالات المهددة للحياة اتصل بالإسعاف فوراً: 🇮🇷 115",
    },
    "ask_country": {
        "fa": "🌍 برای نمایش شمارهٔ اورژانس درست، کشور محل حضور شما کدام است؟",
        "en": "🌍 Which country are you in right now? (to show the correct emergency number)",
        "ar": "🌍 ما هو البلد الذي أنت فيه الآن؟ (لعرض رقم الإسعاف الصحيح)",
    },
    "emergency_title": {
        "fa": "🚨 وضعیت اورژانسی\n\nفوراً با اورژانس تماس بگیرید:",
        "en": "🚨 Emergency\n\nCall emergency services immediately:",
        "ar": "🚨 حالة طارئة\n\nاتصل بالإسعاف فوراً:",
    },
    "call_btn": {
        "fa": "📞 تماس با {num}",
        "en": "📞 Call {num}",
        "ar": "📞 الاتصال بـ {num}",
    },
    "honest_note": {
        "fa": "⚠️ این ربات نمی‌تواند آمبولانس اعزام کند یا اورژانس را مطلع کند — «خودتان» تماس بگیرید.",
        "en": "⚠️ This bot cannot dispatch an ambulance or notify EMS — you must call yourself.",
        "ar": "⚠️ لا يمكن لهذا البوت إرسال إسعاف أو إبلاغ الطوارئ — يجب عليك الاتصال بنفسك.",
    },
    "info_prep": {
        "fa": "📋 اطلاعات آماده برای گفتن به اپراتور:\n\n{info}\n\n👆 این متن را کپی/فوروارد کنید یا هنگام تماس بخوانید.",
        "en": "📋 Info ready to tell the operator:\n\n{info}\n\n👆 Copy/forward this text or read it on the call.",
        "ar": "📋 معلومات جاهزة لإبلاغ العامل:\n\n{info}\n\n👆 انسخ/أعد توجيه هذا النص أو اقرأه أثناء الاتصال.",
    },
    "btn_info": {
        "fa": "📋 متن آماده برای اپراتور",
        "en": "📋 Text for the operator",
        "ar": "📋 نص للمشغل",
    },
    "btn_location": {
        "fa": "📍 افزودن موقعیت من (با رضایت شما)",
        "en": "📍 Add my location (with your consent)",
        "ar": "📍 أضف موقعي (بموافقتك)",
    },
    "btn_companion": {
        "fa": "👥 متن برای همراه / فرد اضطراری",
        "en": "👥 Text for companion / emergency contact",
        "ar": "👥 نص للمرافق / جهة الطوارئ",
    },
    "companion_text": {
        "fa": "👥 این متن را برای همراه/فرد اضطراری خود بفرستید:\n\n{info}\n\n(ربات بدون اجازهٔ شما هیچ اطلاعاتی برای کسی نمی‌فرستد)",
        "en": "👥 Send this text to your companion/emergency contact:\n\n{info}\n\n(The bot sends nothing to anyone without your consent)",
        "ar": "👥 أرسل هذا النص لمرافقك/جهة الطوارئ:\n\n{info}\n\n(لا يرسل البوت أي معلومات لأحد دون موافقتك)",
    },
    "location_ask": {
        "fa": "📍 برای افزودن موقعیت به متن اضطراری، دکمهٔ ارسال موقعیت را بزنید یا پیام موقعیت بفرستید.\n\n🔒 موقعیت شما فقط در همین متن آماده درج می‌شود و «هیچ» داده‌ای برای کسی ارسال نمی‌شود. برای انصراف: منو",
        "en": "📍 To add your location to the emergency text, tap the location button or send a location message.\n\n🔒 Your location is only inserted into this prepared text; nothing is sent to anyone. To cancel: Menu",
        "ar": "📍 لإضافة موقعك إلى نص الطوارئ، اضغط زر الإرسال أو أرسل رسالة موقع.\n\n🔒 يُدرج موقعك فقط في هذا النص ولا يُرسل لأحد. للإلغاء: القائمة",
    },
    "location_saved": {
        "fa": "✅ موقعیت به متن آماده اضافه شد. برای دیدن متن، دکمهٔ «متن آماده» را بزنید.",
        "en": "✅ Location added to the prepared text. Tap \"Text for the operator\" to view it.",
        "ar": "✅ أُضيف الموقع إلى النص الجاهز. اضغط «نص للمشغل» لرؤيته.",
    },
    "location_cancelled": {
        "fa": "🔒 دریافت موقعیت لغو شد. هیچ موقعیتی ذخیره/ارسال نشد.",
        "en": "🔒 Location request cancelled. No location was stored or sent.",
        "ar": "🔒 أُلغي طلب الموقع. لم يُخزَّن أو يُرسل أي موقع.",
    },
    "referral_title": {
        "fa": "🏥 ارجاع پیشنهادی\n\nبر اساس علامت شما، مراجعه به این تخصص پیشنهاد می‌شود: «{spec}»\n\n(این ارجاع تشخیص نیست؛ تصمیم درمانی با پزشک است.)",
        "en": "🏥 Suggested Referral\n\nBased on your symptom, seeing this specialty is suggested: \"{spec}\"\n\n(This is not a diagnosis; treatment decisions belong to the physician.)",
        "ar": "🏥 إحالة مقترحة\n\nبناءً على عرضك، يُقترح مراجعة هذا التخصص: \"{spec}\"\n\n(هذه ليست تشخيصاً؛ قرار العلاج للطبيب.)",
    },
    "btn_doctors": {
        "fa": "👨‍⚕️ مشاهدهٔ پزشکان این تخصص",
        "en": "👨‍⚕️ See doctors of this specialty",
        "ar": "👨‍⚕️ أطباء هذا التخصص",
    },
    "matched_hospitals": {
        "fa": "🏥 بیمارستان‌های دارای این تخصص (شیراز):",
        "en": "🏥 Hospitals offering this specialty (Shiraz):",
        "ar": "🏥 المستشفيات التي بها هذا التخصص (شيراز):",
    },
    "urgent_note": {
        "fa": "⏳ وضعیت «فوری» تشخیص داده شد — بدون تأخیر (همین امروز) به پزشک مراجعه کنید. اگر علائم بدتر شد: اورژانس ۱۱۵.",
        "en": "⏳ Your case looks \"urgent\" — see a physician today without delay. If symptoms worsen: emergency 115.",
        "ar": "⏳ الحالة «عاجلة» — راجع الطبيب اليوم دون تأخير. إذا ازدادت الأعراض: الإسعاف 115.",
    },
    "emergency_still": {
        "fa": "🚨 اگر در هر لحظه نشانهٔ خطر ظاهر شد: تماس فوری با اورژانس",
        "en": "🚨 If any danger sign appears at any time: call emergency immediately",
        "ar": "🚨 إذا ظهرت علامة خطر في أي وقت: اتصل بالإسعاف فوراً",
    },
    "btn_emergency": {
        "fa": "🚑 کمک فوری — تماس با اورژانس",
        "en": "🚑 Urgent help — call emergency",
        "ar": "🚑 مساعدة عاجلة — اتصل بالإسعاف",
    },
    "btn_referral": {
        "fa": "🏥 ارجاع به متخصص",
        "en": "🏥 Referral to specialist",
        "ar": "🏥 إحالة إلى أخصائي",
    },
    "q_now": {
        "fa": "پرسش {i} از {n}:",
        "en": "Question {i} of {n}:",
        "ar": "سؤال {i} من {n}:",
    },
    "yes": {"fa": "✅ بله", "en": "✅ Yes", "ar": "✅ نعم"},
    "no": {"fa": "❌ خیر", "en": "❌ No", "ar": "❌ لا"},
    "red_flags_head": {
        "fa": "🚩 نشانه‌های خطر فوری:\nاگر «همین حالا» یکی از این‌ها را دارید، معطل سؤال نمانید — مستقیم اورژانس:",
        "en": "🚩 Immediate danger signs:\nIf you have any of these \"right now\", skip the questions — go straight to emergency:",
        "ar": "🚩 علامات الخطر الفوري:\nإذا كان لديك أحد هذه «الآن» فلا تنتظر الأسئلة — اذهب مباشرة للطوارئ:",
    },
    "selfcare_asthma": {
        "fa": "💊 یادآوری: در حملهٔ آسم از «برنامهٔ درمانی و داروی نجاتِ تجویزشدهٔ خودتان» مطابق آموزش پزشک استفاده کنید؛ اگر بهبود نیافتید یا علائم شدید بود، اورژانس را فعال کنید.",
        "en": "💊 Reminder: during an asthma attack use YOUR prescribed action plan and rescue medication as trained; if not improving or severe, activate EMS.",
        "ar": "💊 تذكير: أثناء نوبة الربو استخدم خطة علاجك ودواء الإنقاذ الموصوف كما تعلمت؛ إذا لم يتحسن أو اشتدت الأعراض ففعّل الإسعاف.",
    },
    "err": {
        "fa": "😔 خطایی پیش آمد؛ دوباره تلاش کنید یا با اورژانس تماس بگیرید (۱۱۵).",
        "en": "😔 An error occurred; try again or call emergency (115).",
        "ar": "😔 حدث خطأ؛ حاول مرة أخرى أو اتصل بالإسعاف (115).",
    },
    "fallback_num": {
        "fa": "کشور شما در فهرست نیست — روی اکثر گوش‌های موبایل، ۱۱۲ به اورژانس وصل می‌شود. از هتل/مترجم هم بپرسید.",
        "en": "Your country is not listed — on most mobile phones 112 connects to emergency. Ask your hotel/translator too.",
        "ar": "بلدك غير مدرج — على معظم الهواتف 112 يصل بالطوارئ. اسأل الفندق/المترجم أيضاً.",
    },
}


def _at(lang: str, key: str, **kw) -> str:
    tpl = ADVISOR_T.get(key, {}).get(lang) or ADVISOR_T.get(key, {}).get("fa", key)
    return tpl.format(**kw) if kw else tpl


def _symptom_title(symptom: dict, lang: str) -> str:
    return f"{symptom['icon']} {symptom['title'].get(lang) or symptom['title']['fa']}"


# ── صفحات اصلی ───────────────────────────────────────────────────────────────


async def show_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """منوی ۱۸ علامت — همه در یک صفحه، ۲ ستون؛ انتهای آن دکمهٔ بازگشت."""
    (context.user_data or {}).pop("advisor_state", None)
    rows: list[list[InlineKeyboardButton]] = []
    current: list[InlineKeyboardButton] = []
    for s in ha.SYMPTOMS:
        label = _symptom_title(s, lang)
        if len(label) > 64:
            label = label[:63] + "…"
        current.append(InlineKeyboardButton(label, callback_data=f"advs_{s['id']}"))
        if len(current) == 2:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    rows.append(get_back_keyboard(lang).inline_keyboard[0])
    await _display(update, context, _at(lang, "intro"), InlineKeyboardMarkup(rows))


def _brief_text(symptom: dict, lang: str) -> str:
    title = _symptom_title(symptom, lang)
    brief = symptom["brief"].get(lang) or symptom["brief"]["fa"]
    out = f"{title}\n\n{brief}"
    flags = symptom.get("red_flags") or []
    if flags:
        out += "\n\n" + _at(lang, "red_flags_head") + "\n"
        out += "\n".join(f"• {(f.get(lang) or f.get('fa', ''))}" for f in flags)
    if symptom["id"] == "asthma":
        out += "\n\n" + _at(lang, "selfcare_asthma")
    return out


def _question_keyboard(symptom: dict, q_idx: int, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    questions = symptom["questions"]
    q = questions[q_idx]
    qtext = q["text"].get(lang) or q["text"]["fa"]
    head = _at(lang, "q_now", i=q_idx + 1, n=len(questions))
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(_at(lang, "yes"), callback_data=f"advq_{symptom['id']}_{q_idx}_1"),
        InlineKeyboardButton(_at(lang, "no"), callback_data=f"advq_{symptom['id']}_{q_idx}_0"),
    ]])
    return f"{head}\n\n❓ {qtext}", kb


async def _finish_triage(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, symptom: dict, level: str) -> None:
    if level == "emergency":
        await _emergency_entry(update, context, lang, symptom)
    else:
        await referral_screen(update, context, lang, symptom, level)


async def symptom_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, symptom_id: str) -> None:
    query = update.callback_query
    lang = (context.user_data or {}).get("lang", "fa")
    symptom = ha.get_symptom(symptom_id)
    if not symptom:
        await _display(update, context, _at(lang, "err"), get_back_keyboard(lang))
        return
    (context.user_data or {})["advisor_state"] = {"sid": symptom_id, "answers": {}}
    text = _brief_text(symptom, lang)
    qtext, kb = _question_keyboard(symptom, 0, lang)
    rows = list(kb.inline_keyboard) + [get_back_keyboard(lang).inline_keyboard[0]]
    await _display(update, context, f"{text}\n\n{qtext}", InlineKeyboardMarkup(rows))


async def question_answered(update: Update, context: ContextTypes.DEFAULT_TYPE, symptom_id: str, q_idx: int, answer: bool) -> None:
    query = update.callback_query
    lang = (context.user_data or {}).get("lang", "fa")
    symptom = ha.get_symptom(symptom_id)
    state = (context.user_data or {}).get("advisor_state") or {}
    if not symptom or state.get("sid") != symptom_id:
        # گفتگو ریست شده (ناوبری منو) — از ابتدای همان علامت شروع کن
        await symptom_selected(update, context, symptom_id)
        return
    questions = symptom["questions"]
    if q_idx < len(questions):
        state["answers"][questions[q_idx]["key"]] = answer
    nxt = q_idx + 1
    if nxt < len(questions):
        context.user_data["advisor_state"] = state
        text, kb = _question_keyboard(symptom, nxt, lang)
        rows = list(kb.inline_keyboard) + [get_back_keyboard(lang).inline_keyboard[0]]
        await _display(update, context, text, InlineKeyboardMarkup(rows))
        return
    level = ha.evaluate(symptom, state.get("answers") or {})
    (context.user_data or {}).pop("advisor_state", None)
    await _finish_triage(update, context, lang, symptom, level)


# ── مسیر اورژانس ─────────────────────────────────────────────────────────────


async def _emergency_entry(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, symptom: dict) -> None:
    """ورود به مسیر اورژانس — اول کشور، بعد صفحهٔ شماره."""
    context.user_data["advisor_pending_symptom"] = symptom["id"]  # برای دکمهٔ کشور
    if (context.user_data or {}).get("country"):
        await _emergency_screen(update, context, lang, symptom)
        return
    rows: list[list[InlineKeyboardButton]] = []
    current: list[InlineKeyboardButton] = []
    for cc in ha.EMERGENCY_COUNTRY_ORDER:
        rec = ha.EMERGENCY_NUMBERS[cc]
        label = rec["label"].get(lang) or rec["label"]["fa"]
        current.append(InlineKeyboardButton(label, callback_data=f"advec_{cc}"))
        if len(current) == 3:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    rows.append(get_back_keyboard(lang).inline_keyboard[0])
    await _display(update, context, _at(lang, "ask_country"), InlineKeyboardMarkup(rows))


async def _emergency_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, symptom: dict) -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    cc = (context.user_data or {}).get("country")
    num, rec = ha.emergency_number(cc)
    country_name = rec["label"].get(lang) if rec else ""
    head = _at(lang, "emergency_title")
    if country_name:
        head += f"\n🌍 {country_name} — 📞 {num}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(_at(lang, "call_btn", num=num), url=f"tel:{num}")]])
    try:
        await _display(update, context, head, kb)
    except Exception:
        # اگر پلتفرم لینک tel: را نپذیرفت، متن ساده (شماره در متن هست)
        await _display(update, context, head, get_back_keyboard(lang))
        return
    honest = _at(lang, "honest_note")
    if not rec:
        honest += "\n\n" + _at(lang, "fallback_num")
    try:
        await context.bot.send_message(chat_id=chat_id, text=honest)
    except Exception as error:
        logger.warning("emergency honest note failed: %s", error)
    # دکمه‌های تکمیلی: متن اپراتور / موقعیت (رضایت‌محور) / متن همراه / ارجاع
    rows = [
        [InlineKeyboardButton(_at(lang, "btn_info"), callback_data=f"advinf_{symptom['id']}")],
        [InlineKeyboardButton(_at(lang, "btn_location"), callback_data=f"advloc_{symptom['id']}")],
        [InlineKeyboardButton(_at(lang, "btn_companion"), callback_data=f"advcmp_{symptom['id']}")],
        [InlineKeyboardButton(_at(lang, "btn_referral"), callback_data=f"advref_{symptom['id']}")],
        get_back_keyboard(lang).inline_keyboard[0],
    ]
    try:
        await context.bot.send_message(chat_id=chat_id, text=_symptom_title(symptom, lang), reply_markup=InlineKeyboardMarkup(rows))
    except Exception as error:
        logger.warning("emergency followup failed: %s", error)


def _prepared_info(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, symptom: dict) -> str:
    """متن آماده برای اپراتور — فقط داده‌های واقعاً در دسترس؛ هیچ ادعایی نه."""
    user = update.effective_user
    title = _symptom_title(symptom, lang)
    lines = [f"🚨 {title}"]
    if (context.user_data or {}).get("country"):
        cc = (context.user_data or {}).get("country")
        num, _rec = ha.emergency_number(cc)
        lines.append(f"🌍 {ha.EMERGENCY_NUMBERS.get(cc, {}).get('label', {}).get(lang, cc)} — 📞 {num}")
    if user:
        name = user.first_name or ""
        if name:
            lines.append(f"👤 {name}")
        uname = f"@{user.username}" if user.username else ""
        if uname:
            lines.append(f"💬 {uname}")
    loc = (context.user_data or {}).get("emergency_location")
    if loc:
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is not None and lng is not None:
            lines.append(f"📍 {float(lat):.5f}, {float(lng):.5f}")
            lines.append(f"🗺️ https://maps.google.com/?q={float(lat):.5f},{float(lng):.5f}")
    return "\n".join(lines)


async def info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, symptom_id: str) -> None:
    lang = (context.user_data or {}).get("lang", "fa")
    symptom = ha.get_symptom(symptom_id)
    if not symptom or update.effective_chat is None:
        return
    info = _prepared_info(update, context, lang, symptom)
    await _display(update, context, _at(lang, "info_prep", info=info), get_back_keyboard(lang))


async def location_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, symptom_id: str) -> None:
    """درخواست موقعیت — فقط با رضایت صریح این دکمه فعال می‌شود."""
    lang = (context.user_data or {}).get("lang", "fa")
    if update.effective_chat is None:
        return
    (context.user_data or {})["advisor_awaiting_location"] = {"sid": symptom_id, "lang": lang}
    await _display(update, context, _at(lang, "location_ask"), get_back_keyboard(lang))


async def handle_shared_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """MessageHandler(LOCATION): اگر کاربر با رضایت موقعیت فرستاده بود، در متن آماده ذخیره می‌شود."""
    flag = (context.user_data or {}).pop("advisor_awaiting_location", None)
    lang = (flag or {}).get("lang", (context.user_data or {}).get("lang", "fa"))
    message = update.message
    if message is None or update.effective_chat is None:
        return
    if not flag or message.location is None:
        return
    context.user_data["emergency_location"] = {
        "lat": message.location.latitude,
        "lng": message.location.longitude,
    }
    try:
        await message.reply_text(_at(lang, "location_saved"), reply_markup=get_back_keyboard(lang))
    except Exception as error:
        logger.warning("location ack failed: %s", error)


async def companion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, symptom_id: str) -> None:
    lang = (context.user_data or {}).get("lang", "fa")
    symptom = ha.get_symptom(symptom_id)
    if not symptom or update.effective_chat is None:
        return
    info = _prepared_info(update, context, lang, symptom)
    await _display(update, context, _at(lang, "companion_text", info=info), get_back_keyboard(lang))


async def emergency_redo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """از صفحهٔ ارجاع → «کمک فوری»: مسیر اورژانس با آخرین علامت دیده‌شده؛
    اگر علامتی در جریان نبود، منوی علامت‌ها."""
    lang = (context.user_data or {}).get("lang", "fa")
    sid = str((context.user_data or {}).get("advisor_pending_symptom") or "")
    symptom = ha.get_symptom(sid)
    if not symptom:
        await show_advisor(update, context, lang)
        return
    await _emergency_entry(update, context, lang, symptom)


def _matched_hospitals(spec_key: str, lang: str, limit: int = 3) -> list[dict]:
    """بیمارستان‌هایی که تخصص موردنظر را در فهرست واقعی خود دارند.

    تطبیق با کلیدواژهٔ برچسب تخصص در specialties_{fa,en} بیمارستان؛ هیچ حدس
    یا دادهٔ جعلی اضافه نمی‌شود؛ اگر تطبیقی نبود، لیست خالی برمی‌گردد.
    """
    spec_fa = doctor_loader.get_label(spec_key, "fa")
    spec_en = doctor_loader.get_label(spec_key, "en")
    # کلیدواژهٔ کوتاه معتبر: اولین واژهٔ ≥۳ حرف برچسب فارسی (مثل «قلب»)
    kw_fa = next((w for w in spec_fa.replace(" و ", " ").split() if len(w) >= 3), spec_fa)
    kw_en = next((w for w in spec_en.split() if len(w) >= 3), spec_en).lower()
    kw_en = kw_en.rstrip(",")
    out = []
    for item in _unwrap(load_repo_json("hospitals.json")):
        if not isinstance(item, dict):
            continue
        sp_fa = " ".join(str(x) for x in (item.get("specialties_fa") or []))
        sp_en = " ".join(str(x) for x in (item.get("specialties_en") or []))
        sp_ar = " ".join(str(x) for x in (item.get("specialties_ar") or []))
        hit = (kw_fa and kw_fa in sp_fa) or (kw_en and kw_en in sp_en.lower())
        # زبان عربی: تطبیق کل برچسب (کوتاه‌تر است) — صرفاً وقتی کلیدواژهٔ دیگری نبود
        if not hit:
            spec_ar = doctor_loader.get_label(spec_key, "ar")
            if len(spec_ar) <= 25 and spec_ar in sp_ar:
                hit = True
        if hit:
            out.append(item)
        if len(out) >= limit:
            break
    return out


async def referral_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, symptom: dict, level: str = "referral") -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    spec_key = ha.specialty_for(symptom["id"])
    spec_label = doctor_loader.get_label(spec_key, lang) or doctor_loader.get_label(spec_key, "fa")
    head = _at(lang, "referral_title", spec=spec_label)
    if level == "urgent":
        head += "\n\n" + _at(lang, "urgent_note")
    else:
        head += "\n\n" + _at(lang, "emergency_still")
    kb_rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(_at(lang, "btn_doctors"), callback_data=f"med_spec_{spec_key}_0")],
        [InlineKeyboardButton(_at(lang, "btn_emergency"), callback_data="advem_redo")],
        get_back_keyboard(lang).inline_keyboard[0],
    ]
    try:
        await _display(update, context, head, InlineKeyboardMarkup(kb_rows))
    except Exception as error:
        logger.warning("referral head failed: %s", error)
        return
    hospitals = _matched_hospitals(spec_key, lang)
    if hospitals:
        try:
            await context.bot.send_message(chat_id=chat_id, text=_at(lang, "matched_hospitals"))
        except Exception:
            pass
        for h in hospitals:
            lines = []
            for base in ("name", "title"):
                name = _hospital_name(h, base, lang)
                if name:
                    lines.append(f"🏥 {name}")
                    break
            addr = _hospital_flat(h, "address", lang)
            if addr:
                lines.append(f"📍 {addr}")
            phone = str(h.get("phone") or "")
            if phone:
                lines.append(f"📞 {phone}")
            ipd = str(h.get("ipd_direct_phone") or "")
            if h.get("has_ipd") and ipd:
                lines.append(f"🌍 IPD: {ipd}")
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="\n".join(lines) or "🏥",
                    reply_markup=InlineKeyboardMarkup(list(_map_row(h, lang))),
                )
            except Exception as error:
                logger.warning("hospital card failed: %s", error)


def _hospital_name(h: dict, base: str, lang: str) -> str:
    obj = h.get(base)
    if isinstance(obj, dict):
        for l in (lang, "fa", "en", "ar"):
            if obj.get(l):
                return str(obj[l])
    for suffix in (f"_{lang}", "_fa", "_en", "_ar"):
        v = h.get(f"{base}{suffix}")
        if v:
            return str(v)
    return ""


def _hospital_flat(h: dict, base: str, lang: str) -> str:
    obj = h.get(base)
    if isinstance(obj, dict):
        for l in (lang, "fa", "en", "ar"):
            if obj.get(l):
                return str(obj[l])
    for suffix in (f"_{lang}", "_fa", "_en", "_ar"):
        v = h.get(f"{base}{suffix}")
        if v:
            return str(v)
    return ""


async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, symptom_id: str, level: str = "referral") -> None:
    lang = (context.user_data or {}).get("lang", "fa")
    symptom = ha.get_symptom(symptom_id)
    if not symptom:
        await _display(update, context, _at(lang, "err"), get_back_keyboard(lang))
        return
    await referral_screen(update, context, lang, symptom, level)


# ── روتر callbackهای مشاور (الگو: adv*) ──────────────────────────────────────

ADVISOR_CB_PATTERN = r"^adv(s|q|em|ec|ref|inf|loc|cmp)_[a-z0-9_]+$"


async def advisor_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    try:
        await query.answer()
    except Exception:
        pass
    data = query.data or ""
    # ⚠️ شناسهٔ علامت‌ها زیرخط دارد (مثل chest_pain) — پارس با strip prefix، نه split ساده
    try:
        if data.startswith("advs_"):
            await symptom_selected(update, context, data[len("advs_"):])
        elif data.startswith("advq_"):
            sid, q_idx, ans = data[len("advq_"):].rsplit("_", 2)
            await question_answered(update, context, sid, int(q_idx), ans == "1")
        elif data.startswith("advec_"):
            cc = data[len("advec_"):]
            sid = str((context.user_data or {}).get("advisor_pending_symptom") or "chest_pain")
            context.user_data["country"] = cc
            symptom = ha.get_symptom(sid)
            await _emergency_screen(update, context, (context.user_data or {}).get("lang", "fa"), symptom or ha.SYMPTOMS[0])
        elif data.startswith("advinf_"):
            await info_callback(update, context, data[len("advinf_"):])
        elif data.startswith("advloc_"):
            await location_request_callback(update, context, data[len("advloc_"):])
        elif data.startswith("advcmp_"):
            await companion_callback(update, context, data[len("advcmp_"):])
        elif data.startswith("advref_"):
            await referral_callback(update, context, data[len("advref_"):], "referral")
        elif data.startswith("advem_"):
            await emergency_redo_callback(update, context)
        else:
            logger.warning("unknown advisor callback: %s", data)
    except Exception:
        logger.exception("advisor router failed for %s", data)
        lang = (context.user_data or {}).get("lang", "fa")
        await _display(update, context, _at(lang, "err"), get_back_keyboard(lang))
