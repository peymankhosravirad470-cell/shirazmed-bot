# -*- coding: utf-8 -*-
"""هندلر دکمه‌های منوی اصلی و مسیریابی بخش‌های مختلف ربات."""

from __future__ import annotations

import json
import os
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_keyboard
from app.keyboards.non_medical import get_non_medical_keyboard
from app.locales import get_msg_btn


def load_json(filename: str) -> list[dict[str, Any]]:
    """خواندن امن فایل JSON از پوشه data در روت پروژه."""
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        file_path = os.path.join(base_dir, "data", filename)

        if not os.path.isfile(file_path):
            print(f"JSON file not found: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except (json.JSONDecodeError, OSError) as error:
        print(f"Error loading JSON file '{filename}': {error}")
        return []


def _get_localized_field(item: dict, base_key: str, lang: str) -> str:
    """دریافت مقدار فیلد چندزبانه با استفاده از زبان کاربر و کلیدهای جایگزین."""
    preferred_key = f"{base_key}_{lang}"
    fallback_keys = [f"{base_key}_fa", f"{base_key}_en", f"{base_key}_ar", base_key]

    if preferred_key in item and item[preferred_key]:
        return str(item[preferred_key])

    for key in fallback_keys:
        if key in item and item[key]:
            return str(item[key])

    return ""


async def _show_items(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    filename: str,
    empty_message: str = "اطلاعاتی یافت نشد.",
) -> None:
    """نمایش عمومی آیتم‌های یک فایل JSON به صورت پیام‌های جداگانه."""
    chat_id = update.effective_chat.id

    try:
        items = load_json(filename)

        if not items:
            await context.bot.send_message(
                chat_id=chat_id,
                text=empty_message,
                reply_markup=get_back_keyboard(lang),
            )
            return

        for item in items:
            if not isinstance(item, dict):
                continue

            name = _get_localized_field(item, "name", lang)
            address = _get_localized_field(item, "address", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""

            message_lines = []

            if name:
                message_lines.append(f"نام: {name}")

            if address:
                message_lines.append(f"آدرس: {address}")

            if phone:
                message_lines.append(f"تلفن: {phone}")

            if not message_lines:
                continue

            message_text = "\n".join(message_lines)

            await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
            )

        await context.bot.send_message(
            chat_id=chat_id,
            text="برای بازگشت کلیک کنید:",
            reply_markup=get_back_keyboard(lang),
        )

    except Exception as error:
        print(f"Error showing items from '{filename}': {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="اطلاعاتی یافت نشد.",
            reply_markup=get_back_keyboard(lang),
        )


async def show_hospitals(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست بیمارستان‌ها از فایل‌های hospitals.json و hospitals2.json."""
    chat_id = update.effective_chat.id

    try:
        hospitals: list[dict[str, Any]] = []
        hospitals.extend(load_json("hospitals.json"))
        hospitals.extend(load_json("hospitals2.json"))

        if not hospitals:
            await context.bot.send_message(
                chat_id=chat_id,
                text="اطلاعاتی یافت نشد.",
                reply_markup=get_back_keyboard(lang),
            )
            return

        for hospital in hospitals:
            if not isinstance(hospital, dict):
                continue

            name = _get_localized_field(hospital, "name", lang)
            address = _get_localized_field(hospital, "address", lang)
            specialties = _get_localized_field(hospital, "specialties", lang)
            phone = str(hospital.get("phone", "")) if hospital.get("phone") else ""

            message_lines = []

            if name:
                message_lines.append(f"نام: {name}")

            if address:
                message_lines.append(f"آدرس: {address}")

            if specialties:
                message_lines.append(f"تخصص‌ها: {specialties}")

            if phone:
                message_lines.append(f"تلفن: {phone}")

            if not message_lines:
                continue

            message_text = "\n".join(message_lines)

            await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
            )

        await context.bot.send_message(
            chat_id=chat_id,
            text="برای بازگشت کلیک کنید:",
            reply_markup=get_back_keyboard(lang),
        )

    except Exception as error:
        print(f"Error showing hospitals: {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="اطلاعاتی یافت نشد.",
            reply_markup=get_back_keyboard(lang),
        )


async def show_hotels(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست هتل‌ها از فایل hotels.json."""
    await _show_items(update, context, lang, "hotels.json")


async def show_motels(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست مهمان‌پذیرها از فایل motels.json."""
    await _show_items(update, context, lang, "motels.json")


async def show_tourist_houses(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست خانه‌های مسافر از فایل tourist_houses.json."""
    await _show_items(update, context, lang, "tourist_houses.json")


async def show_transport(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست وسایل نقلیه از فایل transport.json."""
    await _show_items(update, context, lang, "transport.json")


async def main_menu_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """پاسخ به کلیک روی دکمه‌های منوی اصلی و نمایش بخش مربوطه."""
    query = update.callback_query

    if query is None or update.effective_chat is None:
        return

    await query.answer()

    lang = context.user_data.get("lang", "fa")
    data = query.data

    if data == "non_medical":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="منوی خدمات غیرپزشکی:",
            reply_markup=get_non_medical_keyboard(lang),
        )
        return

    elif data == "non_hospitals":
        await show_hospitals(update, context, lang)
        return

    elif data == "non_hotels":
        await show_hotels(update, context, lang)
        return

    elif data == "non_motels":
        await show_motels(update, context, lang)
        return

    elif data == "non_tourist_houses":
        await show_tourist_houses(update, context, lang)
        return

    elif data == "non_transport":
        await show_transport(update, context, lang)
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="این بخش در نسخه‌های بعدی فعال می‌شود.",
        reply_markup=get_back_keyboard(lang),
    )