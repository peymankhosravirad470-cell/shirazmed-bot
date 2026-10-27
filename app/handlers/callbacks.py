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


async def _display(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None: return
    query = update.callback_query
    if query is not None and query.message is not None:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
            return
        except Exception as exc:
            if "not modified" in str(exc).lower(): return
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
            except Exception:
                pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


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
    for index, chunk in enumerate(chunks):
        is_last = index == total - 1
        markup = back_markup if is_last else None
        if index == 0:
            await _display(update, context, chunk, markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=chunk, reply_markup=markup)
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

            # استخراج نام (پشتیبانی از ساختار تودرتو و مسطح)
            name = ""
            name_obj = item.get("name")
            if isinstance(name_obj, dict):
                name = name_obj.get(lang) or name_obj.get("fa") or ""
            else:
                name = _get_localized_field(item, "name_fa", lang) or _get_localized_field(item, "name", lang)

            # استخراج آدرس
            address = ""
            addr_obj = item.get("address")
            if isinstance(addr_obj, dict):
                address = addr_obj.get(lang) or addr_obj.get("fa") or ""
            else:
                address = _get_localized_field(item, "address_fa", lang) or _get_localized_field(item, "address", lang)

            # استخراج بقیه فیلدها (برای گردشگری و هر بخش دیگر)
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