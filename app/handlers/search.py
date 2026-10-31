# -*- coding: utf-8 -*-
"""🔍 هندلر جست‌وجوی هوشمند (مأموریت مکمل — بخش ۱)

جریان: دکمهٔ «🔍 جست‌وجوی هوشمند» در منوی اصلی → پیام راهنما → کاربر عبارت را
می‌نویسد → نتایج دسته‌بندی‌شده با دکمه → کارت جزئیات هر نتیجه با دکمه‌های
مسیریاب (گوگل/نشان/بلد/ویز) و پرش به بخش مربوطه ربات.

پرچم user_data:
- awaiting_search: متن بعدی کاربر به‌جای مسیرهای دیگر به جست‌وجو می‌رود؛
  با هر ناوبری منو (reset_conversations_callback) پاک می‌شود.
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.locales import get_msg_btn
from app.services import search_engine
from app.handlers.callbacks import (
    _display,
    _get_localized_field,
    _get_localized_list,
    _map_row,
    _send_chunked,
    _t,
)
from app.keyboards.main import get_back_keyboard

logger = logging.getLogger(__name__)

# برچسب‌های سه‌زبانهٔ خودِ جست‌وجو
SEARCH_T: dict[str, dict[str, str]] = {
    "intro": {
        "fa": "🔍 جست‌وجوی هوشمند شیراز مدیکال\n\nهر چه می‌خواهید بنویسید؛ مثلاً:\n• «دکتر قلب» یا نام پزشک\n• «کوثر» (بیمارستان)\n• «هتل» یا «اقامت»\n• «مترجم» یا «نوبت»\n\nهمه‌چیز یکجا: پزشک، بیمارستان، پاراکلینیک، بیمه، هتل، ترانسفر، گردشگری، پکیج، راهنما و…\n\n👆 عبارت مورد نظر را بنویسید:",
        "en": "🔍 Shiraz Medical Smart Search\n\nType anything, e.g.:\n• \"cardiologist\" or a doctor's name\n• \"Kowsar\" (hospital)\n• \"hotel\" or \"stay\"\n• \"translator\" or \"appointment\"\n\nDoctors, hospitals, clinics, insurance, hotels, transfer, tourism, packages, guides — all in one place.\n\n👆 Type your search:",
        "ar": "🔍 البحث الذكي في شيراز ميديكال\n\nاكتب أي شيء، مثلاً:\n• «طبيب قلب» أو اسم طبيب\n• «كوثر» (مستشفى)\n• «فندق» أو «إقامة»\n• «مترجم» أو «موعد»\n\nالأطباء والمستشفيات والعيادات والتأمين والفنادق والنقل والسياحة والباقات والأدلة — كل شيء في مكان واحد.\n\n👆 اكتب كلمة البحث:",
    },
    "no_result": {
        "fa": "متأسفانه نتیجه‌ای پیدا نشد. 🤔\n\nکلمات ساده‌تر امتحان کنید (مثلاً «قلب»، «هتل»، «بیمه») یا از دکمهٔ 🩺 مشاور سلامت برای علائم پزشکی استفاده کنید.",
        "en": "No results found. 🤔\n\nTry simpler words (e.g. \"heart\", \"hotel\", \"insurance\") or use 🩺 Health Advisor for medical symptoms.",
        "ar": "لم يتم العثور على نتائج. 🤔\n\nجرّب كلمات أبسط (مثل «قلب»، «فندق»، «تأمين») أو استخدم 🩺 مستشار الصحة للأعراض الطبية.",
    },
    "results_head": {
        "fa": "🔍 نتایج جست‌وجوی «{q}»:\n\nبرای دیدن جزئیات، روی نتیجه بزنید:",
        "en": "🔍 Results for \"{q}\":\n\nTap a result to see details:",
        "ar": "🔍 نتائج البحث عن «{q}»:\n\nاضغط على النتيجة لرؤية التفاصيل:",
    },
    "again": {
        "fa": "🔍 جست‌وجوی جدید",
        "en": "🔍 New Search",
        "ar": "🔍 بحث جديد",
    },
    "lbl_specialty": {"fa": "تخصص", "en": "Specialty", "ar": "التخصص"},
    "lbl_doctor": {"fa": "پزشک", "en": "Doctor", "ar": "الطبيب"},
    "lbl_book": {"fa": "📅 نوبت این تخصص", "en": "📅 Book this specialty", "ar": "📅 حجز هذا التخصص"},
    "lbl_type": {"fa": "نوع", "en": "Type", "ar": "النوع"},
    "lbl_hours": {"fa": "ساعات کاری", "en": "Working hours", "ar": "ساعات العمل"},
    "lbl_description": {"fa": "توضیحات", "en": "Description", "ar": "الوصف"},
    "lbl_services_list": {"fa": "خدمات", "en": "Services", "ar": "الخدمات"},
    "lbl_price": {"fa": "قیمت", "en": "Price", "ar": "السعر"},
    "lbl_capacity": {"fa": "ظرفیت", "en": "Capacity", "ar": "السعة"},
    "lbl_rating": {"fa": "امتیاز", "en": "Rating", "ar": "التقييم"},
    "lbl_notes": {"fa": "نکات", "en": "Notes", "ar": "ملاحظات"},
    "lbl_access": {"fa": "دسترسی", "en": "Access", "ar": "الوصول"},
    "lbl_pricing": {"fa": "روش قیمت‌گذاری", "en": "Pricing method", "ar": "طريقة التسعير"},
    "lbl_area": {"fa": "محدودهٔ خدمات", "en": "Service area", "ar": "نطاق الخدمة"},
    "lbl_langs": {"fa": "زبان‌ها", "en": "Languages", "ar": "اللغات"},
    "lbl_topic": {"fa": "موضوع", "en": "Topic", "ar": "الموضوع"},
    "lbl_summary": {"fa": "خلاصه", "en": "Summary", "ar": "الملخص"},
    "lbl_duration_pkg": {"fa": "مدت", "en": "Duration", "ar": "المدة"},
    "lbl_components": {"fa": "شامل", "en": "Includes", "ar": "يشمل"},
    "err": {
        "fa": "😔 در جست‌وجو خطایی پیش آمد؛ دوباره تلاش کنید.",
        "en": "😔 Search error; please try again.",
        "ar": "😔 حدث خطأ في البحث؛ حاول مرة أخرى.",
    },
}


def _st(lang: str, key: str, **kw) -> str:
    tpl = SEARCH_T.get(key, {}).get(lang) or SEARCH_T.get(key, {}).get("fa", key)
    return tpl.format(**kw) if kw else tpl


async def show_search(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """دکمهٔ منو → فعال‌سازی حالت جست‌وجو + پیام راهنما."""
    if context.user_data is not None:
        context.user_data["awaiting_search"] = True
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg_btn(lang, "ai_assistant"), callback_data="ai_assistant")],
        get_back_keyboard(lang).inline_keyboard[0],
    ])
    await _display(update, context, _st(lang, "intro"), kb)


async def run_search_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str) -> None:
    """اجرای جست‌وجو برای متن کاربر (فراخوانی از feedback_text_handler)."""
    if update.effective_chat is None or update.message is None:
        return
    lang = (context.user_data or {}).get("lang", "fa")
    try:
        results = search_engine.search(query_text, lang)
    except Exception:
        logger.exception("search failed")
        await update.message.reply_text(_st(lang, "err"), reply_markup=get_back_keyboard(lang))
        return

    if not results:
        await update.message.reply_text(_st(lang, "no_result"), reply_markup=get_back_keyboard(lang))
        return

    # متن خلاصه + دکمه‌های نتیجه (حداکثر ۵ دسته × ۲ نتیجه — منظم و کم‌شلوغ)
    rows: list[list[InlineKeyboardButton]] = []
    body_parts: list[str] = [_st(lang, "results_head", q=query_text[:40]), ""]
    shown = 0
    for group in results[:5]:
        if shown >= 10:
            break
        rows.append([InlineKeyboardButton(f"――― {group['icon']} {group['label']} ―――", callback_data="noop_page")])
        body_parts.append(f"{group['icon']} {group['label']}:")
        for res in group["results"][:2]:
            label = f"▫️ {res['title'][:48]}"
            rows.append([InlineKeyboardButton(label, callback_data=res["callback"])])
            body_parts.append(f"  • {res['title']}")
            shown += 1
        body_parts.append("")
    rows.append([InlineKeyboardButton(_st(lang, "again"), callback_data="search")])
    rows.append(get_back_keyboard(lang).inline_keyboard[0])
    kb = InlineKeyboardMarkup(rows)
    try:
        await update.message.reply_text("\n".join(body_parts), reply_markup=kb)
    except Exception:
        # اگر برچسب خیلی بلند بود (سقف سخت بله/تلگرام) برچسب‌ها را کوتاه کن
        for row in rows:
            for b in row:
                if len(b.text) > 64:
                    b.text = b.text[:63] + "…"
        await update.message.reply_text("\n".join(body_parts), reply_markup=InlineKeyboardMarkup(rows))


# ── کارت جزئیات نتیجه ────────────────────────────────────────────────────────

# فیلدهای متنی که در کارت جزئیات (به ترتیب) نمایش داده می‌شوند؛ «هیچ» مقدار
# جعل نمی‌شود — فقط فیلدهای واقعاً موجود در داده.
_CARD_FIELDS: list[tuple[str, str, str]] = [
    # (کلید داده، کلید برچسب SEARCH_T/_t، آیکون)
    ("type", "lbl_type", "📌"),
    ("category", "lbl_category", "📌"),
    ("specialty", "lbl_specialty", "🩺"),
    ("district", "lbl_district", "📍"),
    ("address", "lbl_address", "📍"),
    ("star_rating", "lbl_star", "⭐"),
    ("quality_grade", "lbl_quality", "🏅"),
    ("license_status", "lbl_license", "📄"),
    ("working_hours", "lbl_hours", "⏰"),
    ("visiting_hours", "lbl_visiting_hours", "⏰"),
    ("duration", "lbl_duration_pkg", "⏳"),
    ("duration_of_visit", "lbl_duration", "⏳"),
    ("best_season", "lbl_season", "🌤️"),
    ("ticket_price", "lbl_ticket", "🎫"),
    ("price_range", "lbl_price", "💰"),
    ("capacity", "lbl_capacity", "🛏️"),
    ("rating", "lbl_rating", "💙"),
    ("patient_satisfaction_score", "lbl_satisfaction", "💙"),
    ("has_translator", "lbl_has_translator", "🗣"),
    ("languages_spoken", "lbl_langs", "🌐"),
    ("languages_supported", "lbl_langs", "🌐"),
    ("distance_to_hospitals", "lbl_distance_hospitals", "🚑"),
    ("distance_to_city_center", "lbl_distance", "📏"),
    ("service_area", "lbl_area", "🗺"),
    ("pricing_method", "lbl_pricing", "💰"),
    ("accessibility", "lbl_access", "♿"),
    ("summary", "lbl_summary", "📝"),
    ("description", "lbl_description", "📝"),
    ("translator_requirement", "guide_translator", "🗣"),
    ("costs_and_payment", "guide_costs", "💰"),
    ("notes", "lbl_notes", "💡"),
]

_LIST_FIELDS = (
    ("components", "lbl_components", "📦"),
    ("services", "lbl_services_list", "✨"),
    ("amenities", "lbl_amenities", "✨"),
)


def _lf(item: dict, base: str, lang: str) -> str:
    """مقدار فیلد سه‌زبانه (تودرتو یا *_fa تخت) — الگوی data واقعی."""
    obj = item.get(base)
    if isinstance(obj, dict):
        for l in (lang, "fa", "en", "ar"):
            if obj.get(l):
                return str(obj[l])
        return ""
    for suffix in (f"_{lang}", "_fa", "_en", "_ar", ""):
        v = item.get(f"{base}{suffix}")
        if isinstance(v, (str, int, float)) and str(v).strip():
            return str(v)
    return ""


def _detail_card(item: dict, lang: str) -> str:
    lines: list[str] = []
    name = search_engine._display_name(item)
    if name and name != "?":
        lines.append(f"🏛️ {name}\n")
    for base, lbl, icon in _CARD_FIELDS:
        val = _lf(item, base, lang)
        if val:
            lines.append(f"{icon} {_t(lang, lbl)}: {val}")
    for base, lbl, icon in _LIST_FIELDS:
        vals = _get_localized_list(item, f"{base}_fa", lang)
        if not vals:
            obj = item.get(base)
            if isinstance(obj, dict):
                for l in (lang, "fa", "en", "ar"):
                    if isinstance(obj.get(l), list):
                        vals = [str(x) for x in obj[l]]
                        break
        if vals:
            lines.append(f"{icon} {_st(lang, lbl)}: {'، '.join(str(x) for x in vals)}")
    return "\n".join(lines) if lines else _t(lang, "empty_generic")


async def search_go_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش کارت جزئیات نتیجهٔ srchgo_<cat>_<idx>."""
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    try:
        await query.answer()
    except Exception:
        pass
    lang = (context.user_data or {}).get("lang", "fa")
    data = query.data or ""
    try:
        body = data[len("srchgo_"):]
        cat_id, idx_s = body.rsplit("_", 1)
        idx = int(idx_s)
    except ValueError:
        await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
        return
    item = search_engine.get_item(cat_id, idx)
    if not item:
        await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
        return

    text = _detail_card(item, lang)
    rows = _map_row(item, lang)
    kb_rows: list[list[InlineKeyboardButton]] = list(rows)
    phone = str(item.get("phone") or item.get("ipd_direct_phone") or "").strip()
    if phone:
        kb_rows.append([InlineKeyboardButton(f"📞 {_t(lang, 'lbl_phone')}: {phone[:24]}", callback_data="noop_page")])
    kb_rows.append([InlineKeyboardButton(_st(lang, "again"), callback_data="search")])
    kb_rows.append(get_back_keyboard(lang).inline_keyboard[0])
    await _display(update, context, text, InlineKeyboardMarkup(kb_rows))


async def search_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دکمهٔ «جست‌وجوی جدید» — دوباره به حالت جست‌وجو."""
    query = update.callback_query
    if query is None:
        return
    try:
        await query.answer()
    except Exception:
        pass
    lang = (context.user_data or {}).get("lang", "fa")
    await show_search(update, context, lang)
