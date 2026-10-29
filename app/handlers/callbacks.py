# -*- coding: utf-8 -*-
"""هندلر دکمه‌های منوی اصلی و مسیریابی بخش‌های مختلف ربات."""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from typing import Any, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_keyboard
from app.keyboards.non_medical import get_non_medical_keyboard
from app.keyboards.tourism import (
    get_tourism_keyboard,
    get_patient_rights_keyboard,
    get_complaints_menu_keyboard,
)
from app.keyboards.paramedical import get_paramedical_keyboard
from app.keyboards.elderly import get_elderly_keyboard
from app.locales import get_msg, get_msg_btn
from app.services import doctor_loader
from app.handlers import meds
from app.handlers import chunks as chunk_tracker

# 🆕 برچسب‌های ناوبری مرور پزشکان (سه‌زبانه)
_BROWSE_T: dict[str, dict[str, str]] = {
    "prev": {"fa": "▶️ قبلی", "en": "▶️ Previous", "ar": "▶️ السابق"},
    "next": {"fa": "◀️ بعدی", "en": "◀️ Next", "ar": "◀️ التالي"},
}

# 🌐 متن‌های سه‌زبانه همه بخش‌ها — قبلاً تیتر منوها، برچسب فیلدها (نام/آدرس/تلفن و…)
# و پیام‌های خطا فارسی هاردکد بودند و برای کاربر عرب/انگلیسی تداخل زبان ایجاد می‌کرد.
_T: dict[str, dict[str, str]] = {
    # ── تیتر زیرمنوها ──
    "menu_non_medical": {"fa": "منوی خدمات غیرپزشکی:", "en": "Non-Medical Services:", "ar": "قائمة الخدمات غير الطبية:"},
    "menu_tourism": {"fa": "منوی گردشگری:", "en": "Tourism:", "ar": "قائمة السياحة:"},
    "menu_paramedical": {"fa": "منوی پیراپزشکی:", "en": "Paramedical Services:", "ar": "قائمة الخدمات المساندة:"},
    "menu_elderly": {"fa": "منوی خانه سالمندان:", "en": "Nursing Homes:", "ar": "قائمة دور المسنين:"},
    "prompt_rights": {"fa": "لطفاً بخش مورد نظر را انتخاب کنید:", "en": "Please choose a section:", "ar": "يرجى اختيار القسم المطلوب:"},
    "prompt_complaints": {"fa": "لطفاً نوع شکایت خود را انتخاب کنید:", "en": "Please choose your complaint type:", "ar": "يرجى اختيار نوع شكواك:"},
    "coming_soon": {"fa": "این بخش در نسخه‌های بعدی فعال می‌شود.", "en": "This section will be available in future versions.", "ar": "سيتم تفعيل هذا القسم في الإصدارات القادمة."},
    # ── 🌐 دکمه «آدرس سایت» (تنها دکمه جدید منو) ──
    # سایت آینده: https://medshiraz.ir (فعلاً بالا نیامده است)
    # 🎯 وقتی سایت راه‌اندازی شد فقط: در app/keyboards/main.py دکمه را به
    #    دکمه لینک‌دار (InlineKeyboardButton با پارامتر url) تبدیل کنید و
    #    شاخه "site" را از main_menu_callback حذف کنید.
    "site_soon": {
        "fa": "🚧 سایت به زودی فعال می‌شود",
        "en": "🚧 The website will be available soon",
        "ar": "🚧 سيتم تفعيل الموقع قريباً",
    },
    # ── برچسب فیلدهای داده ──
    "lbl_name": {"fa": "نام", "en": "Name", "ar": "الاسم"},
    "lbl_category": {"fa": "دسته‌بندی", "en": "Category", "ar": "الفئة"},
    "lbl_district": {"fa": "منطقه", "en": "District", "ar": "المنطقة"},
    "lbl_address": {"fa": "آدرس", "en": "Address", "ar": "العنوان"},
    "lbl_visiting_hours": {"fa": "ساعت بازدید", "en": "Visiting hours", "ar": "ساعات الزيارة"},
    "lbl_ticket": {"fa": "قیمت بلیط", "en": "Ticket price", "ar": "سعر التذكرة"},
    "lbl_duration": {"fa": "مدت بازدید", "en": "Visit duration", "ar": "مدة الزيارة"},
    "lbl_season": {"fa": "بهترین فصل", "en": "Best season", "ar": "أفضل موسم"},
    "lbl_phone": {"fa": "تلفن", "en": "Phone", "ar": "الهاتف"},
    "lbl_amenities": {"fa": "امکانات", "en": "Amenities", "ar": "المرافق"},
    "lbl_emergency": {"fa": "شماره اضطراری", "en": "Emergency number", "ar": "رقم الطوارئ"},
    # 🆕 برچسب‌های بیمه (تسک ۱ — نمایش کامل فیلدهای insurances.json)
    "lbl_type": {"fa": "نوع", "en": "Type", "ar": "النوع"},
    "lbl_coverage": {"fa": "پوشش ویزیت عمومی", "en": "GP visit coverage", "ar": "تغطية زيارة الطبيب العام"},
    "lbl_support_phone": {"fa": "پشتیبانی ۲۴ساعته", "en": "24h support", "ar": "الدعم على مدار الساعة"},
    "lbl_website": {"fa": "وبسایت", "en": "Website", "ar": "الموقع الإلكتروني"},
    "lbl_offices": {"fa": "دفاتر در شیراز", "en": "Offices in Shiraz", "ar": "المكاتب في شيراز"},
    # 🆕 دکمه مسیریاب (تسک ۴)
    "lbl_map": {"fa": "🗺️ مسیریاب (گوگل‌مپ)", "en": "🗺️ Directions (Google Maps)", "ar": "🗺️ الاتجاهات (خرائط جوجل)"},
    # ── راهنمای بیمار ──
    "guide_visa": {"fa": "مدارک ویزای پزشکی:", "en": "Medical visa documents:", "ar": "وثائق التأشيرة الطبية:"},
    "guide_admission": {"fa": "مدارک پذیرش بیمارستان:", "en": "Hospital admission documents:", "ar": "وثائق القبول في المستشفى:"},
    "guide_translator": {"fa": "الزام مترجم", "en": "Translator requirement", "ar": "اشتراط المترجم"},
    # ── پیام‌های خالی / خطا ──
    "empty_generic": {"fa": "اطلاعاتی یافت نشد.", "en": "No information found.", "ar": "لم يتم العثور على معلومات."},
    "empty_hotels": {"fa": "هتلی یافت نشد.", "en": "No hotels found.", "ar": "لم يتم العثور على فنادق."},
    "empty_motels": {"fa": "مهمان‌پذیری یافت نشد.", "en": "No motels found.", "ar": "لم يتم العثور على موتيلات."},
    "empty_houses": {"fa": "خانه مسافری یافت نشد.", "en": "No guest houses found.", "ar": "لم يتم العثور على بيوت ضيافة."},
    "empty_transport": {"fa": "وسیله نقلیه‌ای یافت نشد.", "en": "No transport found.", "ar": "لم يتم العثور على وسائل نقل."},
    "empty_section": {"fa": "اطلاعاتی برای این بخش یافت نشد.", "en": "No information found for this section.", "ar": "لا توجد معلومات لهذا القسم."},
    "err_generic": {
        "fa": "😔 الان نتونستیم این اطلاعات رو برات بیاریم.\n\nچند لحظه بعد دوباره امتحان کن — اگه نشد، از «💬 پیشنهادات» بهمون بگو تا سریع بررسی کنیم 💙",
        "en": "😔 We couldn't load this information right now.\n\nPlease try again in a moment — if it still doesn't work, let us know via \"💬 Feedback\" and we'll fix it fast 💙",
        "ar": "لم نتمكن من جلب هذه المعلومات الآن.\n\nيرجى المحاولة بعد قليل — وإذا استمرت المشكلة، فأخبرنا عبر «💬 الملاحظات» وسنعالجها بسرعة 💙",
    },
    "spec_unavailable": {"fa": "اطلاعات این تخصص در دسترس نیست.", "en": "Information for this specialty is unavailable.", "ar": "معلومات هذا التخصص غير متوفرة."},
    # ── تاکسی ──
    "taxi_text": {"fa": "برای درخواست خودرو، یکی از اپلیکیشن‌های زیر را انتخاب کنید:", "en": "To request a ride, choose one of the apps below:", "ar": "لطلب سيارة، اختر أحد التطبيقات التالية:"},
    # ── مترجم ──
    "translator_text": {"fa": "🌐 مترجم همراه هوشمند\n\nبرای ارتباط آسان با راننده تاکسی، فروشنده یا هر شخص دیگری، روی یکی از لینک‌های زیر کلیک کنید.", "en": "🌐 Smart Companion Translator\n\nTo communicate easily with a taxi driver, shopkeeper, or anyone else, tap one of the links below.", "ar": "🌐 المترجم المرافق الذكي\n\nللتواصل بسهولة مع سائق التاكسي أو البائع أو أي شخص آخر، اضغط على أحد الروابط التالية."},
    "translator_btn_web": {"fa": "🌐 ترجمه با Google Translate", "en": "🌐 Translate with Google Translate", "ar": "🌐 الترجمة عبر Google Translate"},
    "translator_btn_app": {"fa": "📱 اپلیکیشن Google Translate", "en": "📱 Google Translate app", "ar": "📱 تطبيق Google Translate"},
    # ── دعوت دوستان ──
    "invite_text": {"fa": "🎁 با دعوت دوستان، ۱۰٪ تخفیف در نوبت بعدی بگیرید!\n\nلینک اختصاصی شما:\n{link}", "en": "🎁 Invite friends and get 10% off your next appointment!\n\nYour personal link:\n{link}", "ar": "🎁 ادعُ أصدقاءك واحصل على خصم 10% في موعدك القادم!\n\nرابطك الخاص:\n{link}"},
    # ── کانال ──
    "channel_text": {"fa": "برای عضویت در کانال رسمی شیراز مدیکال، روی لینک زیر کلیک کنید:", "en": "To join the official Shiraz Medical channel, tap the link below:", "ar": "للانضمام إلى قناة شيراز الطبية الرسمية، اضغط على الرابط التالي:"},
    "channel_btn": {"fa": "📢 عضویت در کانال", "en": "📢 Join the Channel", "ar": "📢 الانضمام للقناة"},
    # ── نوبت‌ها / پکیج ──
    "apt_book_new": {"fa": "📅 رزرو نوبت جدید", "en": "📅 Book New Appointment", "ar": "📅 حجز موعد جديد"},
    "package_text": {"fa": "💎 پکیج کامل گردشگری سلامت\n\nپکیج کامل شامل همه‌ی خدمات به‌صورت یکجا است:\n• هماهنگی نوبت پزشک و بیمارستان\n• اقامت\n• ترانسفر\n• مترجم همراه\n\n📞 برای سفارش، با پشتیبانی تماس بگیرید: 190", "en": "💎 Complete Health Tourism Package\n\nThe full package includes all services in one place:\n• Doctor & hospital appointment coordination\n• Accommodation\n• Transfer\n• Companion translator\n\n📞 To order, contact support: 190", "ar": "💎 باقة السياحة العلاجية الكاملة\n\nتشمل الباقة الكاملة جميع الخدمات في مكان واحد:\n• تنسيق موعد الطبيب والمستشفى\n• الإقامة\n• النقل\n• مترجم مرافق\n\n📞 للطلب، تواصل مع الدعم: 190"},
    # ── تیترهای پیش‌فرض (fallback) ──
    "charter_title_fb": {"fa": "منشور حقوق بیمار", "en": "Patient Rights Charter", "ar": "ميثاق حقوق المريض"},
    "deepseek_title_fb": {"fa": "دستیار هوشمند DeepSeek", "en": "DeepSeek AI Assistant", "ar": "مساعد DeepSeek الذكي"},
}


def _t(lang: str, key: str, **kw: object) -> str:
    """متن سه‌زبانه از _T؛ اگر زبان موجود نبود → فارسی (رفتار مستند)."""
    text = _T.get(key, {}).get(lang) or _T.get(key, {}).get("fa", key)
    if kw:
        try:
            text = text.format(**kw)
        except Exception:
            pass
    return text


# 🚀 کش داده‌ها با اعتبارسنجی mtime (همان الگوی doctor_loader) — فایل فقط وقتی
# تغییر کرده باشد دوباره خوانده می‌شود. داده‌های برگشتی هرگز توسط تماس‌گیرنده‌ها
# mutate نمی‌شوند (بررسی‌شده: همه append/popها روی لیست‌های لوکال‌اند)، پس
# بازگرداندن شیء کش‌شده امن است. هزینه هر فراخوانی کش‌خورده: فقط یک stat().
_JSON_CACHE: dict[str, tuple[float, Union[list, dict]]] = {}


def load_json(filename: str) -> Union[list, dict]:
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, "data", filename)
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            # فایل وجود ندارد → کش قبلی هم باید پاک شود (مثل رفتار قبلی: [])
            _JSON_CACHE.pop(filename, None)
            return []
        cached = _JSON_CACHE.get(filename)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        data = data if isinstance(data, (list, dict)) else []
        _JSON_CACHE[filename] = (mtime, data)
        return data
    except Exception:
        return []


def _get_localized_field(item: dict, base_key: str, lang: str) -> str:
    """🌐 ترتیب fallback (مستند): زبان کاربر ← فارسی ← انگلیسی ← عربی ← مقدار خام.

    🆕 فیکس: قبلاً کلید پایه با پسوند _fa پاس داده می‌شد (مثل name_fa) و کلید
    زبانِ کاربر به شکل name_fa_en ساخته می‌شد که هرگز وجود نداشت — یعنی حتی
    اگر ترجمه انگلیسی/عربی در دیتا بود، همیشه فارسی نمایش داده می‌شد.
    حالا پسوند _fa از کلید پایه حذف و کلیدهای درست ساخته می‌شوند.
    """
    stem = base_key[:-3] if base_key.endswith("_fa") else base_key
    keys: list[str] = []
    for k in (f"{stem}_{lang}", f"{stem}_fa", f"{stem}_en", f"{stem}_ar", base_key, stem):
        if k not in keys:
            keys.append(k)
    for key in keys:
        value = item.get(key)
        if value:
            if isinstance(value, str): return value
            if isinstance(value, list): return ", ".join(str(v) for v in value)
            if isinstance(value, dict): return ", ".join(f"{k}: {v}" for k, v in value.items())
            return str(value)
    return ""


def _get_localized_list(item: dict, base_key: str, lang: str) -> list:
    """🌐 همان ترتیب fallback فیلد، برای لیست‌ها (با فیکس پسوند _fa)."""
    stem = base_key[:-3] if base_key.endswith("_fa") else base_key
    keys: list[str] = []
    for k in (f"{stem}_{lang}", f"{stem}_fa", f"{stem}_en", f"{stem}_ar", base_key, stem):
        if k not in keys:
            keys.append(k)
    for key in keys:
        value = item.get(key)
        if isinstance(value, list): return value
    return []


def _msg(lang: str, key: str, default: str = "") -> str:
    """🆕 خواندن پیام از locale «زبان خود کاربر» (قبلاً همیشه fa.MSG خوانده می‌شد
    و متن‌هایی مثل منشور اخلاقی و «پرونده» برای کاربر عرب/انگلیسی فارسی می‌ماند).
    اگر کلید در زبان کاربر نبود → فارسی → در غیر این صورت default."""
    try:
        value = get_msg(lang, key)
    except Exception:
        value = None
    if value is None or value == key or not str(value).strip():
        try:
            value = get_msg("fa", key)
        except Exception:
            value = None
    if value is None or value == key:
        return default
    return str(value)


def _safe_btn(lang: str, key: str, default: str = "") -> str:
    try:
        value = get_msg_btn(lang, key)
        return str(value) if value is not None else default
    except Exception:
        return default


async def _display(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> int | None:
    """🎯 فیکس تکرار منو: نمایش محتوا روی «همان پیام فعلی» به‌جای پیام جدید.

    ۱) ابتدا پیام فعلی ویرایش می‌شود (edit_message_text)
    ۲) اگر ویرایش ممکن نبود، پیام قبلی حذف و پیام جدید ارسال می‌شود
    ۳) اگر آن هم نشد، فقط پیام جدید ارسال می‌شود

    ⚠️ نکته مهم: هیچ‌وقت پیام فعلی را «قبل از ویرایش» پاک نمی‌کنیم.
    (نسخه قبلی که پیام‌ها را در _sent_messages ردیابی و اول پاک می‌کرد، باعث
    می‌شد edit_message_text روی پیام حذف‌شده شکست بخورد و با هر کلیک یک
    پیام جدید ساخته شود — دقیقاً همان باگ تکثیر منو.)

    🧹 فیکس بقایای لیست چندپیامی: در ابتدای هر نمایش، تکه‌های «غیر آخرِ»
    لیست قبلی (که در chunk_tracker ثبت شده‌اند) از چت حذف می‌شوند تا
    کاربر هم‌زمان لیست قدیمی و منوی جدید را نبیند.

    Returns: message_id پیامی که متن نهایی روی آن است (برای ردیابی تکه‌ها)
    یا None اگر chat نامعلوم بود.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return None
    # 🧹 پاک‌سازی بقایای لیست‌های چندپیامی قبلی — قبل از هر نمایش
    await chunk_tracker.cleanup(context, chat_id)
    query = update.callback_query
    if query is not None and query.message is not None:
        try:
            edited = await query.edit_message_text(text=text, reply_markup=reply_markup)
            return getattr(edited, "message_id", None) or query.message.message_id
        except Exception as exc:
            if "not modified" in str(exc).lower():
                return query.message.message_id
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
            except Exception:
                pass
    sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    return getattr(sent, "message_id", None)


async def _send_chunked(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, texts: list[str], back_markup: InlineKeyboardMarkup, max_chars: int = 2800, item_buttons: list[list[InlineKeyboardButton]] | None = None) -> int:
    """ادغام آیتم‌ها در پیام‌های چندتایی (فیکس flood) + ویرایش تکه اول روی همان پیام.

    🧹 فیکس بقایای لیست چندپیامی: همه تکه‌های «غیر از آخرین» در chunk_tracker
    ثبت می‌شوند (message_id) تا در نخستین ناوبری بعدی — بازگشت به منو، کلیک
    بخش دیگر، تغییر زبان یا شروع پیشنهادات — از چت حذف شوند. آخرین تکه
    (نشانگرِ دارای کیبورد) ثبت نمی‌شود چون خودش با کلیک بعدی ویرایش می‌شود؛
    بنابراین هیچ‌وقت پیامی که باید بماند حذف نمی‌شود.

    🆕 تسک ۴: item_buttons هم‌طول texts است؛ هر آیتم می‌تواند دکمه‌های خودش را
    (مثل مسیریاب گوگل‌مپ) داشته باشد که به کیبوردِ «تکه‌ی حاوی همان آیتم»
    اضافه می‌شوند.
    """
    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    # نگاشت شماره آیتم → شماره تکه (برای چینش دکمه‌های هر تکه)
    item_chunk: list[int] = []
    for index, text in enumerate(texts):
        if current and current_len + len(text) + 2 > max_chars:
            parts.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(text)
        current_len += len(text) + 2
        item_chunk.append(len(parts))  # تا قبل از بستن تکه، شماره تکه فعلی
    if current: parts.append("\n\n".join(current))

    # دکمه‌های هر تکه از آیتم‌های همان تکه جمع می‌شود
    chunk_buttons: list[list[InlineKeyboardButton]] = [[] for _ in parts]
    if item_buttons:
        for idx, buttons in enumerate(item_buttons):
            if idx < len(item_chunk) and buttons:
                chunk_buttons[item_chunk[idx]].extend(buttons)

    # 🧹 ترتیب مهم است: reset را اینجا انجام نمی‌دهیم؛ تکه اول با _display
    # نمایش داده می‌شود که در ابتدای خودش cleanupِ لیست «قبلی» را انجام می‌دهد —
    # بعد از آن فهرست ردیابی نو شروع می‌شود.
    sent = 0
    total = len(parts)
    for index, chunk in enumerate(parts):
        is_last = index == total - 1
        rows = []
        if chunk_buttons[index]:
            # هر آیتم یک ردیف دکمه تا در موبایل شلوغ نشود
            rows.extend([[b] for b in chunk_buttons[index]])
        if is_last and back_markup is not None:
            rows.extend(back_markup.inline_keyboard)
        markup = InlineKeyboardMarkup(rows) if rows else None
        if index == 0:
            fallback_id = None
            q = update.callback_query
            if q is not None and q.message is not None:
                fallback_id = q.message.message_id
            mid = await _display(update, context, chunk, markup)
            # فهرست قبلی در _display پاک شد → از همین لحظه ردیابی نو
            chunk_tracker.reset_tracked(context)
            if not is_last:
                chunk_tracker.track(context, mid or fallback_id)
        else:
            msg = await context.bot.send_message(chat_id=chat_id, text=chunk, reply_markup=markup)
            if not is_last:
                chunk_tracker.track(context, getattr(msg, "message_id", None))
        sent += 1
        if not is_last: await asyncio.sleep(0.35)
    return sent


# 🆕 تسک ۴ — دکمه مسیریاب گوگل‌مپ (InlineKeyboardButton با url، نه callback_data)
_MAP_CITY = {"fa": "شیراز", "en": "Shiraz", "ar": "شيراز"}


def _maps_query(item: dict, lang: str) -> str:
    """کوئری مپ: مختصات اگر موجود (دقیق‌تر)، وگرنه نام + شهر."""
    lat, lng = item.get("lat"), item.get("lng")
    if lat is not None and lng is not None:
        try:
            return f"{float(lat)},{float(lng)}"
        except (TypeError, ValueError):
            pass
    name = _get_localized_field(item, "name_fa", lang) or _get_localized_field(item, "name", lang) or ""
    address = _get_localized_field(item, "address_fa", lang) or _get_localized_field(item, "address", lang) or ""
    base = name or address
    if not base:
        return ""
    return f"{base} {_MAP_CITY.get(lang, 'شیراز')}"


def _maps_button(item: dict, lang: str) -> list[InlineKeyboardButton]:
    """دکمه «مسیریاب» برای آیتم‌های دارای آدرس/نام؛ بدون آدرس → بدون دکمه."""
    query = _maps_query(item, lang)
    if not query:
        return []
    from urllib.parse import quote_plus
    url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
    return [InlineKeyboardButton(_t(lang, "lbl_map"), url=url)]


async def _show_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, filename: str, empty_message: str = "") -> None:
    """نمایش آیتم‌های JSON با برچسب‌های سه‌زبانه.

    🌐 رفتار fallback داده (مستند): برای هر فیلد (اسم/آدرس و…) به این ترتیب
    جستجو می‌شود: مقدار زبان کاربر ← فارسی ← انگلیسی ← عربی ← مقدار خام.
    دیتای فعلی (بیمارستان‌ها/هتل‌ها/…) فقط name_fa/address_fa دارد؛ در نتیجه
    برای کاربر انگلیسی/عربی «نام و آدرس به فارسی» نمایش داده می‌شود — این
    رفتار عمدی و مستند است؛ برچسب‌ها (نام:/آدرس:/تلفن:) اما همیشه به زبان
    خود کاربر هستند.
    """
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    back_markup = get_back_keyboard(lang)
    try:
        items = load_json(filename)
        if not isinstance(items, list): items = []
        texts = []
        btns: list[list[InlineKeyboardButton]] = []
        for item in items:
            if not isinstance(item, dict): continue
            name = ""
            name_obj = item.get("name")
            if isinstance(name_obj, dict):
                name = name_obj.get(lang) or name_obj.get("fa") or ""
            else:
                name = _get_localized_field(item, "name_fa", lang) or _get_localized_field(item, "name", lang)
            address = ""
            addr_obj = item.get("address")
            if isinstance(addr_obj, dict):
                address = addr_obj.get(lang) or addr_obj.get("fa") or ""
            else:
                address = _get_localized_field(item, "address_fa", lang) or _get_localized_field(item, "address", lang)
            category = _get_localized_field(item, "category_fa", lang)
            visiting_hours = _get_localized_field(item, "visiting_hours_fa", lang)
            ticket_price = _get_localized_field(item, "ticket_price_fa", lang)
            duration = _get_localized_field(item, "duration_of_visit_fa", lang)
            best_season = _get_localized_field(item, "best_season_fa", lang)
            district = _get_localized_field(item, "district_fa", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""
            amenities = _get_localized_list(item, "amenities_fa", lang)
            amenities_str = "، ".join(amenities) if amenities else ""
            lines = []
            if name: lines.append(f"🏛️ {_t(lang, 'lbl_name')}: {name}")
            if category: lines.append(f"📌 {_t(lang, 'lbl_category')}: {category}")
            if district: lines.append(f"📍 {_t(lang, 'lbl_district')}: {district}")
            if address: lines.append(f"📍 {_t(lang, 'lbl_address')}: {address}")
            if visiting_hours: lines.append(f"⏰ {_t(lang, 'lbl_visiting_hours')}: {visiting_hours}")
            if ticket_price: lines.append(f"🎫 {_t(lang, 'lbl_ticket')}: {ticket_price}")
            if duration: lines.append(f"⏳ {_t(lang, 'lbl_duration')}: {duration}")
            if best_season: lines.append(f"🌤️ {_t(lang, 'lbl_season')}: {best_season}")
            if phone: lines.append(f"📞 {_t(lang, 'lbl_phone')}: {phone}")
            if amenities_str: lines.append(f"✨ {_t(lang, 'lbl_amenities')}: {amenities_str}")
            if lines:
                texts.append("\n".join(lines))
                # 🆕 تسک ۴: دکمه مسیریاب برای آیتم‌های دارای نام/آدرس
                btns.append(_maps_button(item, lang))
            else:
                btns.append([])
        if not texts:
            await _display(update, context, empty_message or _t(lang, "empty_generic"), back_markup)
            return
        await _send_chunked(update, context, chat_id, texts, back_markup, item_buttons=btns)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), back_markup)
async def show_hospitals(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        hospitals = []
        for fname in ("hospitals.json", "hospitals2.json"):
            data = load_json(fname)
            if isinstance(data, list): hospitals.extend(i for i in data if isinstance(i, dict))
        if not hospitals:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
            return
        texts = []
        btns: list[list[InlineKeyboardButton]] = []
        for h in hospitals:
            if not isinstance(h, dict): continue
            name = _get_localized_field(h, "name_fa", lang) or _get_localized_field(h, "name", lang)
            address = _get_localized_field(h, "address_fa", lang) or _get_localized_field(h, "address", lang)
            phone = str(h.get("phone", "")) if h.get("phone") else ""
            lines = []
            if name: lines.append(f"🏥 {name}")
            if address: lines.append(f"📍 {_t(lang, 'lbl_address')}: {address}")
            if phone: lines.append(f"📞 {_t(lang, 'lbl_phone')}: {phone}")
            if lines: 
                texts.append("\n".join(lines))
                btns.append(_maps_button(h, lang))
            else:
                btns.append([])
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang), item_buttons=btns)
        else:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_hotels(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "hotels.json", _t(lang, "empty_hotels"))


async def show_insurances(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """🆕 تسک ۱ — نمایش «کامل» فیلدهای واقعی insurances.json.

    باگ قبلی: مسیر insurance به _show_items می‌رفت که فقط name/address/category/
    phone را می‌شناسد؛ فایل بیمه‌ها نه address دارد و نه phone (به‌جایش
    main_phone_fa است) → فقط «نام» نمایش داده می‌شد و پوشش/تلفن/وبسایت/نوع/
    دفاتر شیراز حذف می‌شدند. این تابع همه‌ی فیلدهای واقعی فایل را سه‌زبانه
    با fallback مستند (زبان کاربر ← فارسی) نمایش می‌دهد.
    """
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    back_markup = get_back_keyboard(lang)
    try:
        items = load_json("insurances.json")
        if not isinstance(items, list):
            items = []
        texts = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = _get_localized_field(item, "name_fa", lang)
            itype = _get_localized_field(item, "type_fa", lang)
            coverage = _get_localized_field(item, "coverage_gp_visit_fa", lang)
            main_phone = _get_localized_field(item, "main_phone_fa", lang)
            support = _get_localized_field(item, "support_phone_24h_fa", lang)
            website = _get_localized_field(item, "website_fa", lang)
            offices = _get_localized_field(item, "shiraz_offices_fa", lang)
            lines = []
            if name: lines.append(f"🏥 {_t(lang, 'lbl_name')}: {name}")
            if itype: lines.append(f"📌 {_t(lang, 'lbl_type')}: {itype}")
            if coverage: lines.append(f"💰 {_t(lang, 'lbl_coverage')}: {coverage}")
            if main_phone: lines.append(f"📞 {_t(lang, 'lbl_phone')}: {main_phone}")
            if support: lines.append(f"🆘 {_t(lang, 'lbl_support_phone')}: {support}")
            if website: lines.append(f"🌐 {_t(lang, 'lbl_website')}: {website}")
            if offices: lines.append(f"📍 {_t(lang, 'lbl_offices')}: {offices}")
            if lines:
                texts.append("\n".join(lines))
        if not texts:
            await _display(update, context, _t(lang, "empty_generic"), back_markup)
            return
        await _send_chunked(update, context, chat_id, texts, back_markup)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), back_markup)

async def show_motels(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "motels.json", _t(lang, "empty_motels"))

async def show_tourist_houses(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "tourist_houses.json", _t(lang, "empty_houses"))

async def show_transport(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "transport.json", _t(lang, "empty_transport"))

async def show_patient_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        data = load_json("patient_guide.json")
        items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        if not items:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
            return
        texts = []
        for item in items:
            if not isinstance(item, dict): continue
            lines = []
            topic = _get_localized_field(item, "topic_fa", lang) or _get_localized_field(item, "topic", lang)
            if topic: lines.append(f"📌 {topic}\n")
            visa_docs = _get_localized_list(item, "medical_visa_documents_fa", lang)
            if visa_docs:
                lines.append(f"🛂 {_t(lang, 'guide_visa')}")
                for i, doc in enumerate(visa_docs, 1): lines.append(f"{i}. {doc}")
            admission_docs = _get_localized_list(item, "hospital_admission_documents_fa", lang)
            if admission_docs:
                lines.append(f"🏥 {_t(lang, 'guide_admission')}")
                for i, doc in enumerate(admission_docs, 1): lines.append(f"{i}. {doc}")
            translator = _get_localized_field(item, "translator_requirement_fa", lang)
            if translator: lines.append(f"🗣 {_t(lang, 'guide_translator')}: {translator}\n")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, is_foreign: bool = False) -> None:
    filename = "complaints_foreign.json" if is_foreign else "complaints_iranian.json"
    await _show_items(update, context, lang, filename, _t(lang, "empty_section"))

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "support.json", _t(lang, "empty_generic"))

async def show_taxi(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("اسنپ (Snapp)", url="https://snapp.ir")],
            [InlineKeyboardButton("تپسی (Tapsi)", url="https://tapsi.ir")],
            *get_back_keyboard(lang).inline_keyboard,
        ])
        await _display(update, context, _t(lang, "taxi_text"), kb)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_charter(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        # 🌐 قبلاً title از MSG_BTN خوانده می‌شد (کلید در MSG است، نه MSG_BTN) و body
        # همیشه از fa.MSG — یعنی حتی برای کاربر عرب/انگلیسی فارسی نشان داده می‌شد.
        title = _msg(lang, "charter_title", "") or _t(lang, "charter_title_fb")
        body = _msg(lang, "charter_body", "")
        if not body:
            await _display(update, context, title, get_back_keyboard(lang))
            return
        full = f"{title}\n\n{body}"
        chunks = []
        rem = full
        while rem:
            if len(rem) <= 3500:
                chunks.append(rem)
                break
            split = rem.rfind("\n", 0, 3500)
            if split == -1: split = 3500
            chunks.append(rem[:split])
            rem = rem[split:].lstrip("\n")
        for idx, chunk in enumerate(chunks):
            markup = get_back_keyboard(lang) if idx == len(chunks) - 1 else None
            if idx == 0: await _display(update, context, chunk, markup)
            else: 
                await context.bot.send_message(chat_id=chat_id, text=chunk, reply_markup=markup)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_translator(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(lang, "translator_btn_web"), url="https://translate.google.com/")],
        [InlineKeyboardButton(_t(lang, "translator_btn_app"), url="https://play.google.com/store/apps/details?id=com.google.android.apps.translate")],
        *get_back_keyboard(lang).inline_keyboard,
    ])
    await _display(update, context, _t(lang, "translator_text"), kb)


async def show_deepseek(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        title = _msg(lang, "deepseek_title", "") or _t(lang, "deepseek_title_fb")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(_safe_btn(lang, "btn_deepseek_go", "🚀 DeepSeek"), url="https://chat.deepseek.com")],
            *get_back_keyboard(lang).inline_keyboard,
        ])
        await _display(update, context, title, kb)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_file(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        msg = _msg(lang, "pt_not_found", _t(lang, "empty_generic"))
        await _display(update, context, msg, get_back_keyboard(lang))
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        msg = _msg(lang, "apt_none", _t(lang, "empty_generic"))
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(_t(lang, "apt_book_new"), callback_data="start_booking")],
            *get_back_keyboard(lang).inline_keyboard,
        ])
        await _display(update, context, msg, kb)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_medication(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """✅ حالا منوی کامل یادآور دارو (افزودن/لیست/حذف + زمان‌بند واقعی) باز می‌شود.

    🆕 قبلاً فقط یک پیام راهنمای بی‌اثر نمایش داده می‌شد و هیچ یادآوری وجود نداشت.
    """
    if update.effective_chat is None:
        return
    await meds.show_med_menu(update, context, lang)


async def show_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        items = load_json("support.json")
        if not isinstance(items, list): items = []
        em_items = [i for i in items if isinstance(i, dict) and i.get("emergency_contact")]
        if not em_items:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
            return
        texts = []
        for item in em_items:
            name = _get_localized_field(item, "name_fa", lang)
            em = str(item.get("emergency_contact", ""))
            if not name and not em: continue
            lines = []
            if name: lines.append(f"🏢 {name}")
            if em: lines.append(f"🚨 {_t(lang, 'lbl_emergency')}: {em}")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(_t(lang, "channel_btn"), url="https://ble.ir/shiraz_medical")],
            *get_back_keyboard(lang).inline_keyboard,
        ])
        await _display(update, context, _t(lang, "channel_text"), kb)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        user_id = update.effective_user.id if update.effective_user else 0
        link = f"https://ble.ir/ShirazMedBot?start={user_id}"
        await _display(update, context, _t(lang, "invite_text", link=link), get_back_keyboard(lang))
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def show_hubs(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        hubs = load_json("transport_hubs.json")
        transport = load_json("transport.json")
        all_items = []
        if isinstance(hubs, list): all_items.extend(hubs)
        if isinstance(transport, list):
            for item in transport:
                if isinstance(item, dict) and "اسنپ" not in str(item.get("name_fa", "")) and "تپسی" not in str(item.get("name_fa", "")):
                    all_items.append(item)
        if not all_items:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
            return
        texts = []
        for item in all_items:
            if not isinstance(item, dict): continue
            name = _get_localized_field(item, "name_fa", lang)
            addr = _get_localized_field(item, "address_fa", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""
            lines = []
            if name: lines.append(f"📍 {name}")
            if addr: lines.append(f"🏠 {_t(lang, 'lbl_address')}: {addr}")
            if phone: lines.append(f"📞 {_t(lang, 'lbl_phone')}: {phone}")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, _t(lang, "empty_generic"), get_back_keyboard(lang))
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_chat is None: return
    try: await query.answer()
    except Exception: pass

    lang = context.user_data.get("lang", "fa")
    data = query.data

    # 🌐 دکمه «آدرس سایت» — تا راه‌اندازی https://medshiraz.ir فقط پیام «به زودی» می‌دهد.
    # هیچ دکمه دیگری تغییر نکرده است.
    if data == "site":
        await _display(update, context, _t(lang, "site_soon"), get_back_keyboard(lang))
        return

    if data == "non_medical":
        await _display(update, context, _t(lang, "menu_non_medical"), get_non_medical_keyboard(lang))
        return
    if data == "non_hospitals":
        await show_hospitals(update, context, lang)
        return
    if data == "non_hotels":
        await show_hotels(update, context, lang)
        return
    if data == "non_motels":
        await show_motels(update, context, lang)
        return
    if data == "non_tourist_houses":
        await show_tourist_houses(update, context, lang)
        return
    if data == "non_transport":
        await show_transport(update, context, lang)
        return
    if data == "tourism":
        await _display(update, context, _t(lang, "menu_tourism"), get_tourism_keyboard(lang))
        return
    if data == "tour_city":
        await _show_items(update, context, lang, "leisure_city.json")
        return
    if data == "tour_outside":
        await _show_items(update, context, lang, "leisure_outside.json")
        return
    if data == "paramedical":
        await _display(update, context, _t(lang, "menu_paramedical"), get_paramedical_keyboard(lang))
        return
    if data in ("para_physio", "para_lab", "para_radiology", "para_nursing", "para_injection", "para_trad_med", "para_occupational", "para_speech", "para_orthotics"):
        await _show_items(update, context, lang, "paramedical.json")
        return
    if data == "elderly":
        await _display(update, context, _t(lang, "menu_elderly"), get_elderly_keyboard(lang))
        return
    if data == "elderly_all":
        await _show_items(update, context, lang, "elderly_homes.json")
        return
    if data == "hubs":
        await show_hubs(update, context, lang)
        return
    if data == "insurance":
        await show_insurances(update, context, lang)
        return
    if data == "patient_guide":
        await show_patient_guide(update, context, lang)
        return
    if data == "rights":
        await _display(update, context, _t(lang, "prompt_rights"), get_patient_rights_keyboard(lang))
        return
    if data == "charter":
        await show_charter(update, context, lang)
        return
    if data == "complaints_menu":
        await _display(update, context, _t(lang, "prompt_complaints"), get_complaints_menu_keyboard(lang))
        return
    if data == "complaints_iranian":
        await show_complaints(update, context, lang, is_foreign=False)
        return
    if data == "complaints_foreign":
        await show_complaints(update, context, lang, is_foreign=True)
        return
    if data == "support":
        await show_support(update, context, lang)
        return
    if data == "taxi":
        await show_taxi(update, context, lang)
        return
    if data == "translator":
        await show_translator(update, context, lang)
        return
    if data == "deepseek":
        await show_deepseek(update, context, lang)
        return
    if data == "file":
        await show_file(update, context, lang)
        return
    if data == "appointments":
        await show_appointments(update, context, lang)
        return
    if data == "medication":
        await show_medication(update, context, lang)
        return
    if data == "emergency":
        await show_emergency(update, context, lang)
        return
    if data == "channel":
        await show_channel(update, context, lang)
        return
    if data == "invite":
        await show_invite(update, context, lang)
        return
    if data == "medical":
        await show_medical_specialties(update, context, lang, page=0)
        return
    if data == "package":
        await show_package(update, context, lang)
        return

    await _display(update, context, _t(lang, "coming_soon"), get_back_keyboard(lang))


MED_SPEC_PER_PAGE = 8

def _medical_spec_keyboard(page: int, lang: str = "fa") -> tuple[InlineKeyboardMarkup, int]:
    """✅ کیبورد مرور تخصص‌ها — فقط تخصص‌های دارای پزشک، با برچسب سه‌زبانه.

    🆕 فیکس: پیش‌تر همه ۵۰ تخصص (حتی ۴۷ تخصص خالی) با شمارنده (0) و برچسب
    کلید انگلیسی خام مثل «internal» نمایش داده می‌شدند.
    """
    from app.services import doctor_loader
    specialties = doctor_loader.load_specialties()
    total_pages = max(1, (len(specialties) + MED_SPEC_PER_PAGE - 1) // MED_SPEC_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = specialties[page * MED_SPEC_PER_PAGE:(page + 1) * MED_SPEC_PER_PAGE]
    rows = [[InlineKeyboardButton(f"{doctor_loader.get_label(item['key'], lang)} ({item['count']})", callback_data=f"med_spec_{item['key']}_{page}")] for item in chunk]
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(_BROWSE_T["prev"].get(lang) or _BROWSE_T["prev"]["fa"], callback_data=f"med_page_{page - 1}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton(_BROWSE_T["next"].get(lang) or _BROWSE_T["next"]["fa"], callback_data=f"med_page_{page + 1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")])
    return InlineKeyboardMarkup(rows), len(specialties)


async def show_medical_specialties(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, page: int = 0) -> None:
    if update.effective_chat is None: return
    try:
        kb, total = _medical_spec_keyboard(page, lang)
        texts = {
            "fa": f"👨‍⚕️ تخصص‌های فعال شیراز ({total} تخصص):\n\nیکی را انتخاب کنید:\n🔵 سایر تخصص‌ها به‌زودی اضافه می‌شوند.",
            "en": f"👨‍⚕️ Active specialties in Shiraz ({total}):\n\nChoose one:\n🔵 More specialties are coming soon.",
            "ar": f"👨‍⚕️ التخصصات النشطة في شيراز ({total}):\n\nاختر واحداً:\n🔵 سيتم إضافة المزيد قريباً.",
        }
        await _display(update, context, texts.get(lang, texts["fa"]), kb)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))


async def medical_browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.services import doctor_loader
    query = update.callback_query
    if query is None or update.effective_chat is None: return
    try: await query.answer()
    except Exception: pass
    lang = context.user_data.get("lang", "fa")
    data = query.data or ""

    if data.startswith("med_page_"):
        try: page = int(data.replace("med_page_", ""))
        except ValueError: page = 0
        try:
            kb, _ = _medical_spec_keyboard(page, lang)
            await query.edit_message_reply_markup(reply_markup=kb)
        except Exception: pass
        return

    if data.startswith("med_spec_"):
        payload = data.replace("med_spec_", "")
        spec_key, _, page_raw = payload.rpartition("_")
        try: page = int(page_raw)
        except ValueError: page = 0
        spec = doctor_loader.get_specialty(spec_key)
        doctors = doctor_loader.load_doctors(spec_key)
        if spec is None or not doctors:
            await query.edit_message_text(_t(lang, "spec_unavailable"), reply_markup=get_back_keyboard(lang))
            return
        per_page = 12
        start = page * per_page
        chunk = doctors[start:start + per_page]
        spec_label = doctor_loader.get_label(spec_key, lang)
        doc_count_text = {
            "fa": f"👨‍⚕️ {spec_label} — {len(doctors)} پزشک:\n",
            "en": f"👨‍⚕️ {spec_label} — {len(doctors)} doctors:\n",
            "ar": f"👨‍⚕️ {spec_label} — {len(doctors)} طبيب:\n",
        }
        lines = [doc_count_text.get(lang, doc_count_text["fa"])]
        for i, doc in enumerate(chunk, start=start + 1): lines.append(f"{i}. {doc['name_fa']}")
        rows = []
        nav = []
        total_pages = max(1, (len(doctors) + per_page - 1) // per_page)
        if page > 0: nav.append(InlineKeyboardButton(_BROWSE_T["prev"].get(lang) or _BROWSE_T["prev"]["fa"], callback_data=f"med_spec_{spec_key}_{page - 1}"))
        if page < total_pages - 1: nav.append(InlineKeyboardButton(_BROWSE_T["next"].get(lang) or _BROWSE_T["next"]["fa"], callback_data=f"med_spec_{spec_key}_{page + 1}"))
        if nav: rows.append(nav)
        back_labels = {"fa": "🔙 بازگشت به تخصص‌ها", "en": "🔙 Back to specialties", "ar": "🔙 رجوع إلى التخصصات"}
        rows.append([InlineKeyboardButton(back_labels.get(lang, back_labels["fa"]), callback_data="med_back")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "med_back":
        try:
            kb, _ = _medical_spec_keyboard(0, lang)
            back_titles = {"fa": "👨‍⚕️ تخصص‌های فعال شیراز:", "en": "👨‍⚕️ Active specialties in Shiraz:", "ar": "👨‍⚕️ التخصصات النشطة في شيراز:"}
            await query.edit_message_text(back_titles.get(lang, back_titles["fa"]), reply_markup=kb)
        except Exception: pass
        return


async def show_package(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_msg_btn(lang, "btn_book"), callback_data="start_booking")],
            *get_back_keyboard(lang).inline_keyboard,
        ])
        await _display(update, context, _t(lang, "package_text"), kb)
    except Exception:
        await _display(update, context, _t(lang, "err_generic"), get_back_keyboard(lang))