# -*- coding: utf-8 -*-
"""هندلر دکمه‌های منوی اصلی و مسیریابی بخش‌های مختلف ربات."""

from __future__ import annotations

import json
import os
from typing import Any, Union

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_keyboard
from app.keyboards.non_medical import get_non_medical_keyboard
from app.locales import get_msg_btn


def load_json(filename: str) -> Union[list, dict]:
    """خواندن امن فایل JSON از پوشه data در روت پروژه."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, filename)

        if not os.path.isfile(file_path):
            print(f"JSON file not found: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

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


async def show_hospitals(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست بیمارستان‌ها از فایل‌های hospitals.json و hospitals2.json."""
    chat_id = update.effective_chat.id

    try:
        hospitals: list[dict[str, Any]] = []
        hospitals.extend(load_json("data/hospitals.json"))
        hospitals.extend(load_json("data/hospitals2.json"))

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

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="این بخش در نسخه‌های بعدی فعال می‌شود.",
        reply_markup=get_back_keyboard(lang),
    )