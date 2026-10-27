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

from app.keyboards.main import get_back_keyboard, get_main_menu_keyboard
from app.keyboards.non_medical import get_non_medical_keyboard
from app.keyboards.tourism import (
    get_tourism_keyboard,
    get_patient_rights_keyboard,
    get_complaints_menu_keyboard,
)
from app.keyboards.paramedical import get_paramedical_keyboard
from app.keyboards.elderly import get_elderly_keyboard
from app.locales import get_msg_btn
from app.locales.fa import MSG
from app.services import doctor_loader

if not isinstance(MSG, dict):
    MSG = {}

_sent_messages = {}


def load_json(filename: str) -> Union[list, dict]:
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, "data", filename)
        if not os.path.isfile(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, (list, dict)) else []
    except Exception:
        return []


def _get_localized_field(item: dict, base_key: str, lang: str) -> str:
    keys = [f"{base_key}_{lang}", f"{base_key}_fa", f"{base_key}_en", f"{base_key}_ar", base_key]
    for key in keys:
        value = item.get(key)
        if value:
            if isinstance(value, str): return value
            if isinstance(value, list): return ", ".join(str(v) for v in value)
            if isinstance(value, dict): return ", ".join(f"{k}: {v}" for k, v in value.items())
            return str(value)
    return ""


def _get_localized_list(item: dict, base_key: str, lang: str) -> list:
    keys = [f"{base_key}_{lang}", f"{base_key}_fa", f"{base_key}_en", f"{base_key}_ar", base_key]
    for key in keys:
        value = item.get(key)
        if isinstance(value, list): return value
    return []


def _safe_msg(key: str, default: str = "") -> str:
    try:
        value = MSG.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def _safe_btn(lang: str, key: str, default: str = "") -> str:
    try:
        value = get_msg_btn(lang, key)
        return str(value) if value is not None else default
    except Exception:
        return default


async def _cleanup_previous_messages(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    if chat_id in _sent_messages:
        for msg_id in _sent_messages[chat_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
        _sent_messages[chat_id] = []


async def _display(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None: return
    await _cleanup_previous_messages(chat_id, context)
    query = update.callback_query
    if query is not None and query.message is not None:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
            if chat_id not in _sent_messages:
                _sent_messages[chat_id] = []
            _sent_messages[chat_id].append(query.message.message_id)
            return
        except Exception as exc:
            if "not modified" in str(exc).lower(): return
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
            except Exception:
                pass
    msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    if chat_id not in _sent_messages:
        _sent_messages[chat_id] = []
    _sent_messages[chat_id].append(msg.message_id)


async def _send_chunked(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, texts: list[str], back_markup: InlineKeyboardMarkup, max_chars: int = 2800) -> int:
    chunks = []
    current = []
    current_len = 0
    for text in texts:
        if current and current_len + len(text) + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(text)
        current_len += len(text) + 2
    if current: chunks.append("\n\n".join(current))
    sent = 0
    total = len(chunks)
    await _cleanup_previous_messages(chat_id, context)
    for index, chunk in enumerate(chunks):
        is_last = index == total - 1
        markup = back_markup if is_last else None
        if index == 0:
            await _display(update, context, chunk, markup)
        else:
            msg = await context.bot.send_message(chat_id=chat_id, text=chunk, reply_markup=markup)
            if chat_id not in _sent_messages:
                _sent_messages[chat_id] = []
            _sent_messages[chat_id].append(msg.message_id)
        sent += 1
        if not is_last: await asyncio.sleep(0.35)
    return sent


async def _show_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, filename: str, empty_message: str = "اطلاعاتی یافت نشد.") -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    back_markup = get_back_keyboard(lang)
    try:
        items = load_json(filename)
        if not isinstance(items, list): items = []
        texts = []
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
            if name: lines.append(f"🏛️ نام: {name}")
            if category: lines.append(f"📌 دسته‌بندی: {category}")
            if district: lines.append(f"📍 منطقه: {district}")
            if address: lines.append(f"📍 آدرس: {address}")
            if visiting_hours: lines.append(f"⏰ ساعت بازدید: {visiting_hours}")
            if ticket_price: lines.append(f"🎫 قیمت بلیط: {ticket_price}")
            if duration: lines.append(f"⏳ مدت بازدید: {duration}")
            if best_season: lines.append(f"🌤️ بهترین فصل: {best_season}")
            if phone: lines.append(f"📞 تلفن: {phone}")
            if amenities_str: lines.append(f"✨ امکانات: {amenities_str}")
            if lines:
                texts.append("\n".join(lines))
        if not texts:
            await _display(update, context, empty_message, back_markup)
            return
        await _send_chunked(update, context, chat_id, texts, back_markup)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", back_markup)
async def show_hospitals(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        hospitals = []
        for fname in ("hospitals.json", "hospitals2.json"):
            data = load_json(fname)
            if isinstance(data, list): hospitals.extend(i for i in data if isinstance(i, dict))
        if not hospitals:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
            return
        texts = []
        for h in hospitals:
            if not isinstance(h, dict): continue
            name = _get_localized_field(h, "name_fa", lang) or _get_localized_field(h, "name", lang)
            address = _get_localized_field(h, "address_fa", lang) or _get_localized_field(h, "address", lang)
            phone = str(h.get("phone", "")) if h.get("phone") else ""
            lines = []
            if name: lines.append(f"🏥 نام: {name}")
            if address: lines.append(f"📍 آدرس: {address}")
            if phone: lines.append(f"📞 تلفن: {phone}")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_hotels(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "hotels.json", "هتلی یافت نشد.")

async def show_motels(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "motels.json", "مهمان‌پذیری یافت نشد.")

async def show_tourist_houses(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "tourist_houses.json", "خانه مسافری یافت نشد.")

async def show_transport(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "transport.json", "وسیله نقلیه‌ای یافت نشد.")

async def show_patient_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        data = load_json("patient_guide.json")
        items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        if not items:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
            return
        texts = []
        for item in items:
            if not isinstance(item, dict): continue
            lines = []
            topic = _get_localized_field(item, "topic_fa", lang) or _get_localized_field(item, "topic", lang)
            if topic: lines.append(f"📌 {topic}\n")
            visa_docs = _get_localized_list(item, "medical_visa_documents_fa", lang)
            if visa_docs:
                lines.append("🛂 مدارک ویزای پزشکی:")
                for i, doc in enumerate(visa_docs, 1): lines.append(f"{i}. {doc}")
            admission_docs = _get_localized_list(item, "hospital_admission_documents_fa", lang)
            if admission_docs:
                lines.append("🏥 مدارک پذیرش بیمارستان:")
                for i, doc in enumerate(admission_docs, 1): lines.append(f"{i}. {doc}")
            translator = _get_localized_field(item, "translator_requirement_fa", lang)
            if translator: lines.append(f"🗣 الزام مترجم: {translator}\n")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, is_foreign: bool = False) -> None:
    filename = "complaints_foreign.json" if is_foreign else "complaints_iranian.json"
    await _show_items(update, context, lang, filename, "اطلاعاتی برای این بخش یافت نشد.")

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    await _show_items(update, context, lang, "support.json", "اطلاعاتی یافت نشد.")

async def show_taxi(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("اسنپ (Snapp)", url="https://snapp.ir")],
            [InlineKeyboardButton("تپسی (Tapsi)", url="https://tapsi.ir")],
            [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
        ])
        await _display(update, context, "برای درخواست خودرو، یکی از اپلیکیشن‌های زیر را انتخاب کنید:", kb)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_charter(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        title = _safe_btn(lang, "charter_title", "منشور حقوق بیمار")
        body = _safe_msg("charter_body", "")
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
                msg = await context.bot.send_message(chat_id=chat_id, text=chunk, reply_markup=markup)
                if chat_id not in _sent_messages: _sent_messages[chat_id] = []
                _sent_messages[chat_id].append(msg.message_id)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_translator(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 ترجمه با Google Translate", url="https://translate.google.com/")],
        [InlineKeyboardButton("📱 اپلیکیشن Google Translate", url="https://play.google.com/store/apps/details?id=com.google.android.apps.translate")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ])
    text = (
        "🌐 مترجم همراه هوشمند\n\n"
        "برای ارتباط آسان با راننده تاکسی، فروشنده یا هر شخص دیگری، "
        "روی یکی از لینک‌های زیر کلیک کنید."
    )
    await _display(update, context, text, kb)


async def show_deepseek(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        title = _safe_btn(lang, "deepseek_title", "دستیار هوشمند DeepSeek")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 رفتن به DeepSeek", url="https://chat.deepseek.com")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ])
        await _display(update, context, title, kb)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_file(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        msg = _safe_msg("pt_not_found", "پرونده‌ای یافت نشد.")
        await _display(update, context, msg, get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        msg = _safe_msg("apt_none", "شما هنوز هیچ نوبتی ثبت نکرده‌اید.")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 رزرو نوبت جدید", callback_data="start_booking")],
            [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
        ])
        await _display(update, context, msg, kb)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_medication(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """✅ اصلاح شد: حالا به جای پیام «به زودی»، فرم ثبت یادآور دارو نمایش می‌دهد."""
    if update.effective_chat is None: return
    try:
        texts = {
            "fa": "💊 یادآور دارو\n\nلطفاً نام دارو و ساعت مصرف را بنویسید تا برای شما یادآوری کنیم.\n\nمثال: «قرص فشار، ساعت ۸ صبح»",
            "en": "💊 Medication Reminder\n\nPlease write the medication name and time so we can remind you.\n\nExample: «Blood pressure pill, 8 AM»",
            "ar": "💊 تذكير بالدواء\n\nيرجى كتابة اسم الدواء ووقت تناوله حتى نذكرك.\n\nمثال: «حبة ضغط، الساعة 8 صباحاً»",
        }
        text = texts.get(lang, texts["fa"])
        await _display(update, context, text, get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    chat_id = update.effective_chat.id
    try:
        items = load_json("support.json")
        if not isinstance(items, list): items = []
        em_items = [i for i in items if isinstance(i, dict) and i.get("emergency_contact")]
        if not em_items:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
            return
        texts = []
        for item in em_items:
            name = _get_localized_field(item, "name_fa", lang)
            em = str(item.get("emergency_contact", ""))
            if not name and not em: continue
            lines = []
            if name: lines.append(f"🏢 {name}")
            if em: lines.append(f"🚨 شماره اضطراری: {em}")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url="https://ble.ir/shiraz_medical")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ])
        await _display(update, context, "برای عضویت در کانال رسمی شیراز مدیکال، روی لینک زیر کلیک کنید:", kb)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        user_id = update.effective_user.id if update.effective_user else 0
        link = f"https://ble.ir/ShirazMedBot?start={user_id}"
        text = (
            "🎁 با دعوت دوستان، ۱۰٪ تخفیف در نوبت بعدی بگیرید!\n\n"
            f"لینک اختصاصی شما:\n{link}"
        )
        await _display(update, context, text, get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


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
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
            return
        texts = []
        for item in all_items:
            if not isinstance(item, dict): continue
            name = _get_localized_field(item, "name_fa", lang)
            addr = _get_localized_field(item, "address_fa", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""
            lines = []
            if name: lines.append(f"📍 {name}")
            if addr: lines.append(f"🏠 آدرس: {addr}")
            if phone: lines.append(f"📞 تلفن: {phone}")
            if lines: texts.append("\n".join(lines))
        if texts:
            await _send_chunked(update, context, chat_id, texts, get_back_keyboard(lang))
        else:
            await _display(update, context, "اطلاعاتی یافت نشد.", get_back_keyboard(lang))
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_chat is None: return
    try: await query.answer()
    except Exception: pass

    lang = context.user_data.get("lang", "fa")
    data = query.data

    if data == "non_medical":
        await _display(update, context, "منوی خدمات غیرپزشکی:", get_non_medical_keyboard(lang))
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
        await _display(update, context, "منوی گردشگری:", get_tourism_keyboard(lang))
        return
    if data == "tour_city":
        await _show_items(update, context, lang, "leisure_city.json")
        return
    if data == "tour_outside":
        await _show_items(update, context, lang, "leisure_outside.json")
        return
    if data == "paramedical":
        await _display(update, context, "منوی پیراپزشکی:", get_paramedical_keyboard(lang))
        return
    if data in ("para_physio", "para_lab", "para_radiology", "para_nursing", "para_injection", "para_trad_med", "para_occupational", "para_speech", "para_orthotics"):
        await _show_items(update, context, lang, "paramedical.json")
        return
    if data == "elderly":
        await _display(update, context, "منوی خانه سالمندان:", get_elderly_keyboard(lang))
        return
    if data == "elderly_all":
        await _show_items(update, context, lang, "elderly_homes.json")
        return
    if data == "hubs":
        await show_hubs(update, context, lang)
        return
    if data == "insurance":
        await _show_items(update, context, lang, "insurances.json")
        return
    if data == "patient_guide":
        await show_patient_guide(update, context, lang)
        return
    if data == "rights":
        await _display(update, context, "لطفاً بخش مورد نظر را انتخاب کنید:", get_patient_rights_keyboard(lang))
        return
    if data == "charter":
        await show_charter(update, context, lang)
        return
    if data == "complaints_menu":
        await _display(update, context, "لطفاً نوع شکایت خود را انتخاب کنید:", get_complaints_menu_keyboard(lang))
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

    await _display(update, context, "این بخش در نسخه‌های بعدی فعال می‌شود.", get_back_keyboard(lang))


MED_SPEC_PER_PAGE = 8

def _medical_spec_keyboard(page: int, lang: str = "fa") -> tuple[InlineKeyboardMarkup, int]:
    """✅ اصلاح شد: حالا زبان کاربر را دریافت می‌کند و برچسب‌ها را از فایل ترجمه می‌خواند."""
    from app.services import doctor_loader
    specialties = doctor_loader.load_specialties()
    total_pages = max(1, (len(specialties) + MED_SPEC_PER_PAGE - 1) // MED_SPEC_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = specialties[page * MED_SPEC_PER_PAGE:(page + 1) * MED_SPEC_PER_PAGE]
    rows = [[InlineKeyboardButton(f"{item['label']} ({item['count']})", callback_data=f"med_spec_{item['key']}_{page}")] for item in chunk]
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("▶️ قبلی", callback_data=f"med_page_{page - 1}"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("◀️ بعدی", callback_data=f"med_page_{page + 1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")])
    return InlineKeyboardMarkup(rows), len(specialties)


async def show_medical_specialties(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, page: int = 0) -> None:
    if update.effective_chat is None: return
    try:
        kb, total = _medical_spec_keyboard(page, lang)
        texts = {
            "fa": f"👨‍⚕️ تخصص‌های پزشکی شیراز ({total} تخصص):\n\nیکی را انتخاب کنید:",
            "en": f"👨‍⚕️ Medical Specialties in Shiraz ({total} specialties):\n\nChoose one:",
            "ar": f"👨‍⚕️ التخصصات الطبية في شيراز ({total} تخصص):\n\nاختر واحداً:",
        }
        await _display(update, context, texts.get(lang, texts["fa"]), kb)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))


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
            await query.edit_message_text("اطلاعات این تخصص در دسترس نیست.", reply_markup=get_back_keyboard(lang))
            return
        per_page = 12
        start = page * per_page
        chunk = doctors[start:start + per_page]
        lines = [f"👨‍⚕️ {spec['label']} — {len(doctors)} پزشک:\n"]
        for i, doc in enumerate(chunk, start=start + 1): lines.append(f"{i}. {doc['name_fa']}")
        rows = []
        nav = []
        total_pages = max(1, (len(doctors) + per_page - 1) // per_page)
        if page > 0: nav.append(InlineKeyboardButton("▶️ قبلی", callback_data=f"med_spec_{spec_key}_{page - 1}"))
        if page < total_pages - 1: nav.append(InlineKeyboardButton("◀️ بعدی", callback_data=f"med_spec_{spec_key}_{page + 1}"))
        if nav: rows.append(nav)
        rows.append([InlineKeyboardButton("🔙 بازگشت به تخصص‌ها", callback_data="med_back")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "med_back":
        try:
            kb, _ = _medical_spec_keyboard(0, lang)
            await query.edit_message_text("👨‍⚕️ تخصص‌های پزشکی شیراز:", reply_markup=kb)
        except Exception: pass
        return


async def show_package(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None: return
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 رزرو نوبت", callback_data="start_booking")],
            [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
        ])
        text = (
            "💎 پکیج کامل گردشگری سلامت\n\n"
            "پکیج کامل شامل همه‌ی خدمات به‌صورت یکجا است:\n"
            "• هماهنگی نوبت پزشک و بیمارستان\n• اقامت\n• ترانسفر\n• مترجم همراه\n\n"
            "📞 برای سفارش، با پشتیبانی تماس بگیرید: 190"
        )
        await _display(update, context, text, kb)
    except Exception:
        await _display(update, context, "خطا در دریافت اطلاعات.", get_back_keyboard(lang))