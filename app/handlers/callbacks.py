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

# ایمن‌سازی: تضمین می‌کند MSG همیشه dict باشد تا .get هرگز خطا ندهد
if not isinstance(MSG, dict):
    MSG = {}


def load_json(filename: str) -> Union[list, dict]:
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

        if isinstance(data, (list, dict)):
            return data

        return []

    except (json.JSONDecodeError, OSError) as error:
        print(f"Error loading JSON file '{filename}': {error}")
        return []


def _get_localized_field(item: dict, base_key: str, lang: str) -> str:
    """دریافت مقدار فیلد چندزبانه با استفاده از زبان کاربر و کلیدهای جایگزین."""
    keys = [
        f"{base_key}_{lang}",
        f"{base_key}_fa",
        f"{base_key}_en",
        f"{base_key}_ar",
        base_key,
    ]

    for key in keys:
        value = item.get(key)
        if value:
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            if isinstance(value, dict):
                return ", ".join(f"{k}: {v}" for k, v in value.items())
            return str(value)

    return ""


def _get_localized_list(item: dict, base_key: str, lang: str) -> list:
    """دریافت فیلد چندزبانه که مقدار آن لیست است."""
    keys = [
        f"{base_key}_{lang}",
        f"{base_key}_fa",
        f"{base_key}_en",
        f"{base_key}_ar",
        base_key,
    ]
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            return value
    return []


def _safe_msg(key: str, default: str = "") -> str:
    """دریافت امن یک کلید از MSG با fallback."""
    try:
        value = MSG.get(key, default)
        if value is None:
            return default
        return str(value)
    except Exception:
        return default


def _safe_btn(lang: str, key: str, default: str = "") -> str:
    """دریافت امن یک دکمه/عنوان از get_msg_btn با fallback."""
    try:
        value = get_msg_btn(lang, key)
        if value is None:
            return default
        return str(value)
    except Exception as error:
        print(f"Error getting msg btn '{key}' for lang '{lang}': {error}")
        return default


async def _send_chunked(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    texts: list[str],
    back_markup: InlineKeyboardMarkup,
    max_chars: int = 2800,
) -> int:
    """🆕 فیکس flood: چند آیتم را در پیام‌های چندتایی (تا max_chars) ادغام می‌کند.

    قبلاً برای هر بیمارستان/آیتم یک پیام جدا ارسال می‌شد که با لیست‌های بزرگ،
    ده‌ها پیام پشت‌سرهم می‌فرستاد و ربات به محدودیت flood می‌خورد.
    Returns: تعداد پیام‌های ارسال‌شده.
    """
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for text in texts:
        if current and current_len + len(text) + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(text)
        current_len += len(text) + 2
    if current:
        chunks.append("\n\n".join(current))

    sent = 0
    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            reply_markup=back_markup if is_last else None,
        )
        sent += 1
        if not is_last:
            await asyncio.sleep(0.35)  # جلوگیری از محدودیت flood بله
    return sent


async def _show_items(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    filename: str,
    empty_message: str = "اطلاعاتی یافت نشد.",
) -> None:
    """نمایش آیتم‌های یک فایل JSON با پیام‌های ادغام‌شده (فیکس flood)."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id
    back_markup = get_back_keyboard(lang)

    try:
        items = load_json(filename)

        if not isinstance(items, list):
            items = []

        texts: list[str] = []
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

            if message_lines:
                texts.append("\n".join(message_lines))

        if not texts:
            await context.bot.send_message(chat_id=chat_id, text=empty_message, reply_markup=back_markup)
            return

        await _send_chunked(context, chat_id, texts, back_markup)

    except Exception as error:
        traceback.print_exc()
        print(f"Error showing items from '{filename}': {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.",
            reply_markup=back_markup,
        )


async def show_hospitals(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست بیمارستان‌ها از فایل‌های hospitals.json و hospitals2.json."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    try:
        hospitals: list[dict[str, Any]] = []
        for fname in ("hospitals.json", "hospitals2.json"):
            data = load_json(fname)
            if isinstance(data, list):
                hospitals.extend(i for i in data if isinstance(i, dict))

        if not hospitals:
            await context.bot.send_message(
                chat_id=chat_id,
                text="اطلاعاتی یافت نشد.",
                reply_markup=get_back_keyboard(lang),
            )
            return

        sent_any = False

        for hospital in hospitals:
            if not isinstance(hospital, dict):
                continue

            name = _get_localized_field(hospital, "name", lang)
            ownership = _get_localized_field(hospital, "ownership", lang)
            ipd_code = hospital.get("ipd_code", "")
            has_ipd = hospital.get("has_ipd", False)
            address = _get_localized_field(hospital, "address", lang)
            specialties_list = _get_localized_list(hospital, "specialties", lang)
            specialties = "، ".join(specialties_list) if specialties_list else ""
            languages_list = _get_localized_list(hospital, "translator_languages", lang)
            languages = "، ".join(languages_list) if languages_list else ""
            phone = str(hospital.get("phone", "")) if hospital.get("phone") else ""
            ipd_phone = str(hospital.get("ipd_direct_phone", "")) if hospital.get("ipd_direct_phone") else ""
            website = str(hospital.get("website", "")) if hospital.get("website") else ""

            message_lines = []

            if name:
                message_lines.append(f"🏥 نام: {name}")
            if ownership:
                message_lines.append(f"🏢 مالکیت: {ownership}")
            if has_ipd:
                message_lines.append(f"🩺 کد IPD: {ipd_code}")
            if address:
                message_lines.append(f"📍 آدرس: {address}")
            if specialties:
                message_lines.append(f"🔬 تخصص‌ها: {specialties}")
            if languages:
                message_lines.append(f"🗣 زبان‌های مترجم: {languages}")
            if phone:
                message_lines.append(f"📞 تلفن اصلی: {phone}")
            if ipd_phone:
                message_lines.append(f"📞 تلفن مستقیم IPD: {ipd_phone}")
            if website:
                message_lines.append(f"🌐 وب‌سایت: {website}")

            if not message_lines:
                continue

            await context.bot.send_message(
                chat_id=chat_id,
                text="\n".join(message_lines),
            )
            sent_any = True

        if sent_any:
            await context.bot.send_message(
                chat_id=chat_id,
                text="برای بازگشت کلیک کنید:",
                reply_markup=get_back_keyboard(lang),
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="اطلاعاتی یافت نشد.",
                reply_markup=get_back_keyboard(lang),
            )

    except Exception as error:
        traceback.print_exc()
        print(f"Error showing hospitals: {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard(lang),
        )


async def show_hotels(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    await _show_items(update, context, lang, "hotels.json", empty_message="هتلی یافت نشد.")


async def show_motels(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    await _show_items(update, context, lang, "motels.json", empty_message="مهمان‌پذیری یافت نشد.")


async def show_tourist_houses(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    await _show_items(update, context, lang, "tourist_houses.json", empty_message="خانه مسافری یافت نشد.")


async def show_transport(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    await _show_items(update, context, lang, "transport.json", empty_message="وسیله نقلیه‌ای یافت نشد.")


async def show_patient_guide(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش راهنمای بیمار از فایل patient_guide.json."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        data = load_json("patient_guide.json")
        items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        if not items:
            await context.bot.send_message(chat_id=chat_id, text="اطلاعاتی یافت نشد.", reply_markup=get_back_keyboard(lang))
            return
        sent_any = False
        for item in items:
            if not isinstance(item, dict):
                continue
            message_lines = []
            topic = _get_localized_field(item, "topic", lang)
            if topic:
                message_lines.append(f"📌 {topic}\n")
            visa_docs = _get_localized_list(item, "medical_visa_documents", lang)
            if visa_docs:
                message_lines.append("🛂 مدارک ویزای پزشکی:")
                for i, doc in enumerate(visa_docs, 1):
                    message_lines.append(f"{i}. {doc}")
                message_lines.append("")
            admission_docs = _get_localized_list(item, "hospital_admission_documents", lang)
            if admission_docs:
                message_lines.append("🏥 مدارک پذیرش بیمارستان:")
                for i, doc in enumerate(admission_docs, 1):
                    message_lines.append(f"{i}. {doc}")
                message_lines.append("")
            translator = _get_localized_field(item, "translator_requirement", lang)
            if translator:
                message_lines.append(f"🗣 الزام مترجم: {translator}\n")
            if not message_lines:
                continue
            await context.bot.send_message(chat_id=chat_id, text="\n".join(message_lines))
            sent_any = True
        if sent_any:
            await context.bot.send_message(chat_id=chat_id, text="برای بازگشت کلیک کنید:", reply_markup=get_back_keyboard(lang))
        else:
            await context.bot.send_message(chat_id=chat_id, text="اطلاعاتی یافت نشد.", reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        print(f"Error showing patient guide: {error}")
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_complaints(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, is_foreign: bool = False
) -> None:
    """نمایش شکایات (ایرانی یا خارجی) بر اساس انتخاب کاربر."""
    filename = "complaints_foreign.json" if is_foreign else "complaints_iranian.json"
    await _show_items(
        update, context, lang, filename,
        empty_message="اطلاعاتی برای این بخش یافت نشد."
    )


async def show_support(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    await _show_items(update, context, lang, "support.json", empty_message="اطلاعاتی یافت نشد.")


async def show_taxi(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش اپلیکیشن‌های درخواست خودرو (فقط اسنپ و تپسی)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        taxi_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("اسنپ (Snapp)", url="https://snapp.ir")],
            [InlineKeyboardButton("تپسی (Tapsi)", url="https://tapsi.ir")],
            [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
        ])
        await context.bot.send_message(
            chat_id=chat_id,
            text="برای درخواست خودرو، یکی از اپلیکیشن‌های زیر را انتخاب کنید:",
            reply_markup=taxi_keyboard,
        )
    except Exception as error:
        traceback.print_exc()
        print(f"Error showing taxi: {error}")
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_charter(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش متن منشور حقوق بیمار (تکه‌تکه شده)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        title = _safe_btn(lang, "charter_title", "منشور حقوق بیمار")
        body = _safe_msg("charter_body", "")
        if not body:
            await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=get_back_keyboard(lang))
            return
        full_text = f"{title}\n\n{body}" if title else body
        max_len = 3500
        chunks = []
        remaining = full_text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip("\n")
        if not chunks:
            chunks = [title]
        for idx, chunk in enumerate(chunks):
            is_last = idx == len(chunks) - 1
            await context.bot.send_message(
                chat_id=chat_id,
                text=chunk,
                reply_markup=get_back_keyboard(lang) if is_last else None,
            )
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_translator(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش گزینه‌های اتصال به اپلیکیشن مترجم گوشی."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id

    translator_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 ترجمه با Google Translate (وب)", url="https://translate.google.com/")],
        [InlineKeyboardButton("📱 اپلیکیشن Google Translate", url="https://play.google.com/store/apps/details?id=com.google.android.apps.translate")],
        [InlineKeyboardButton("🍎 اپلیکیشن Apple Translate (iOS)", url="https://apps.apple.com/us/app/translate/id1514844618")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ])

    text = (
        "🌐 مترجم همراه هوشمند\n\n"
        "برای ارتباط آسان با راننده تاکسی، فروشنده یا هر شخص دیگری، "
        "کافیست روی یکی از لینک‌های زیر کلیک کنید. "
        "این لینک‌ها شما را مستقیم به اپلیکیشن مترجم گوشی‌تان متصل می‌کنند.\n\n"
        "💡 نکته: اگر اپلیکیشن Google Translate را روی گوشی خود دارید، "
        "می‌توانید از دکمه «اپلیکیشن Google Translate» استفاده کنید تا سریع‌تر باز شود."
    )

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=translator_keyboard,
            # 🆕 فیکس: parse_mode="Markdown" حذف شد — «**bold**» در Markdown قدیمی
            # نامعتبر است و کل این بخش در بله خطای parse می‌داد.
        )
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات.",
            reply_markup=get_back_keyboard(lang),
        )


async def show_deepseek(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        title = _safe_btn(lang, "deepseek_title", "دستیار هوشمند DeepSeek")
        deepseek_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رفتن به DeepSeek", url="https://chat.deepseek.com")]])
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=deepseek_keyboard)
        await context.bot.send_message(chat_id=chat_id, text="برای بازگشت کلیک کنید:", reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        message_text = _safe_msg("pt_not_found", "پرونده‌ای یافت نشد.")
        await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_appointments(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش نوبت‌های بیمار (اگر نداشت، دکمه رزرو)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        message_text = _safe_msg("apt_none", "شما هنوز هیچ نوبتی ثبت نکرده‌اید.")
        book_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 رزرو نوبت جدید", callback_data="start_booking")],
            [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")]
        ])
        await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=book_keyboard)
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_medication(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        remind_text = _safe_msg("remind_med", "")
        info_text = "این بخش به زودی فعال می‌شود. برای یادآور دارو، فعلاً از پشتیبانی استفاده کنید: 190"
        parts = [remind_text, info_text] if remind_text else [info_text]
        await context.bot.send_message(chat_id=chat_id, text="\n\n".join(parts), reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_emergency(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش شماره‌های اضطراری از support.json."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        items = load_json("support.json")
        if not isinstance(items, list):
            items = []
        emergency_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            emergency_value = item.get("emergency_contact")
            if emergency_value is None:
                continue
            if isinstance(emergency_value, str) and not emergency_value.strip():
                continue
            emergency_items.append(item)
        if not emergency_items:
            await context.bot.send_message(chat_id=chat_id, text="اطلاعاتی یافت نشد.", reply_markup=get_back_keyboard(lang))
            return
        sent_any = False
        for item in emergency_items:
            center_name = _get_localized_field(item, "name", lang)
            emergency = str(item.get("emergency_contact", ""))
            if not center_name and not emergency:
                continue
            message_lines = []
            if center_name:
                message_lines.append(f"🏢 {center_name}")
            if emergency:
                message_lines.append(f"🚨 شماره اضطراری: {emergency}")
            if not message_lines:
                continue
            await context.bot.send_message(chat_id=chat_id, text="\n".join(message_lines))
            sent_any = True
        if sent_any:
            await context.bot.send_message(chat_id=chat_id, text="برای بازگشت کلیک کنید:", reply_markup=get_back_keyboard(lang))
        else:
            await context.bot.send_message(chat_id=chat_id, text="اطلاعاتی یافت نشد.", reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_channel(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لینک کانال رسمی (لینک جدید)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        channel_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("عضویت در کانال", url="https://ble.ir/shiraz_medical")]])
        await context.bot.send_message(chat_id=chat_id, text="برای عضویت در کانال رسمی شیراز مدیکال، روی لینک زیر کلیک کنید:", reply_markup=channel_keyboard)
        await context.bot.send_message(chat_id=chat_id, text="برای بازگشت کلیک کنید:", reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_invite(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لینک دعوت اختصاصی با user_id."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        user_id = update.effective_user.id if update.effective_user else 0
        invite_link = f"https://ble.ir/ShirazMedBot?start={user_id}"
        text = (
            "🎁 با دعوت دوستان، ۱۰٪ تخفیف در نوبت بعدی بگیرید!\n\n"
            f"لینک اختصاصی شما:\n{invite_link}"
        )
        # 🆕 فیکس: parse_mode حذف شد — بک‌تیک در برخی نسخه‌های API بله خطا می‌دهد
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def show_hubs(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش پایانه‌های حمل‌ونقل (ادغام transport.json و transport_hubs.json)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        hubs = load_json("transport_hubs.json")
        transport = load_json("transport.json")
        all_items = []
        if isinstance(hubs, list):
            all_items.extend(hubs)
        if isinstance(transport, list):
            for item in transport:
                if isinstance(item, dict):
                    name = str(item.get("name_fa", ""))
                    if "اسنپ" not in name and "تپسی" not in name:
                        all_items.append(item)

        if not all_items:
            await context.bot.send_message(chat_id=chat_id, text="اطلاعاتی یافت نشد.", reply_markup=get_back_keyboard(lang))
            return

        sent_any = False
        for item in all_items:
            if not isinstance(item, dict):
                continue
            name = _get_localized_field(item, "name", lang)
            address = _get_localized_field(item, "address", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""

            message_lines = []
            if name: message_lines.append(f"📍 {name}")
            if address: message_lines.append(f"🏠 آدرس: {address}")
            if phone: message_lines.append(f"📞 تلفن: {phone}")

            if message_lines:
                await context.bot.send_message(chat_id=chat_id, text="\n".join(message_lines))
                sent_any = True

        if sent_any:
            await context.bot.send_message(chat_id=chat_id, text="برای بازگشت کلیک کنید:", reply_markup=get_back_keyboard(lang))
        else:
            await context.bot.send_message(chat_id=chat_id, text="اطلاعاتی یافت نشد.", reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


async def main_menu_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """پاسخ به کلیک روی دکمه‌های منوی اصلی و نمایش بخش مربوطه."""
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    try:
        await query.answer()
    except Exception:
        pass

    lang = context.user_data.get("lang", "fa")
    data = query.data

    if data == "non_medical":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="منوی خدمات غیرپزشکی:", reply_markup=get_non_medical_keyboard(lang))
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
        await context.bot.send_message(chat_id=update.effective_chat.id, text="منوی گردشگری:", reply_markup=get_tourism_keyboard(lang))
        return
    if data == "tour_city":
        await _show_items(update, context, lang, "leisure_city.json")
        return
    if data == "tour_outside":
        await _show_items(update, context, lang, "leisure_outside.json")
        return
    if data == "paramedical":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="منوی پیراپزشکی:", reply_markup=get_paramedical_keyboard(lang))
        return
    if data in ("para_physio", "para_lab", "para_radiology", "para_nursing", "para_injection", "para_trad_med", "para_occupational", "para_speech", "para_orthotics"):
        await _show_items(update, context, lang, "paramedical.json")
        return
    if data == "elderly":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="منوی خانه سالمندان:", reply_markup=get_elderly_keyboard(lang))
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

    # بخش حقوق بیمار و شکایات (تفکیک شده)
    if data == "rights":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="لطفاً بخش مورد نظر را انتخاب کنید:",
            reply_markup=get_patient_rights_keyboard(lang)
        )
        return
    if data == "charter":
        await show_charter(update, context, lang)
        return
    if data == "complaints_menu":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="لطفاً نوع شکایت خود را انتخاب کنید:",
            reply_markup=get_complaints_menu_keyboard(lang)
        )
        return
    if data == "complaints_iranian":
        await show_complaints(update, context, lang, is_foreign=False)
        return
    if data == "complaints_foreign":
        await show_complaints(update, context, lang, is_foreign=True)
        return
    # پایان بخش حقوق بیمار

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
    # 🆕 فیکس: دکمه‌های «پزشکی» و «پکیج کامل» قبلاً مرده بودند (فقط پیام «به‌زودی»)
    if data == "medical":
        await show_medical_specialties(update, context, lang, page=0)
        return
    if data == "package":
        await show_package(update, context, lang)
        return

    # فال‌بک (اگر دکمه‌ای هندل نشد)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="این بخش در نسخه‌های بعدی فعال می‌شود.",
        reply_markup=get_back_keyboard(lang),
    )

# ---------------------------------------------------------------------------
# 🆕 مرور پزشکان واقعی (دکمه «👨‍⚕️ پزشکی» منوی اصلی)
# قبلاً این دکمه مرده بود و فقط پیام «به‌زودی» می‌داد — حالا تخصص‌ها و پزشکان
# واقعی از data/doctors (۱۱۴ پزشک) با صفحه‌بندی نمایش داده می‌شوند.
# ---------------------------------------------------------------------------

MED_SPEC_PER_PAGE = 8


def _medical_spec_keyboard(page: int) -> tuple[InlineKeyboardMarkup, int]:
    specialties = doctor_loader.load_specialties()
    total_pages = max(1, (len(specialties) + MED_SPEC_PER_PAGE - 1) // MED_SPEC_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = specialties[page * MED_SPEC_PER_PAGE:(page + 1) * MED_SPEC_PER_PAGE]

    rows = [
        [InlineKeyboardButton(f"{item['label']} ({item['count']})", callback_data=f"med_spec_{item['key']}_{page}")]
        for item in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("▶️ قبلی", callback_data=f"med_page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("◀️ بعدی", callback_data=f"med_page_{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(get_msg_btn("fa", "btn_back"), callback_data="back_main")])
    return InlineKeyboardMarkup(rows), len(specialties)


async def show_medical_specialties(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, page: int = 0
) -> None:
    if update.effective_chat is None:
        return
    try:
        keyboard, total = _medical_spec_keyboard(page)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👨‍⚕️ تخصص‌های پزشکی شیراز ({total} تخصص):\n\nیکی را انتخاب کنید تا پزشکان آن نمایش داده شود:",
            reply_markup=keyboard,
        )
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="خطا در دریافت اطلاعات.",
            reply_markup=get_back_keyboard(lang),
        )


async def medical_browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندل صفحات تخصص‌ها (med_page_N) و لیست پزشکان تخصص (med_spec_KEY_PAGE)."""
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    try:
        await query.answer()
    except Exception:
        pass

    lang = context.user_data.get("lang", "fa")
    data = query.data or ""

    if data.startswith("med_page_"):
        try:
            page = int(data.replace("med_page_", ""))
        except ValueError:
            page = 0
        try:
            keyboard, _ = _medical_spec_keyboard(page)
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        return

    if data.startswith("med_spec_"):
        payload = data.replace("med_spec_", "")
        spec_key, _, page_raw = payload.rpartition("_")
        try:
            page = int(page_raw)
        except ValueError:
            page = 0

        spec = doctor_loader.get_specialty(spec_key)
        doctors = doctor_loader.load_doctors(spec_key)
        if spec is None or not doctors:
            await query.edit_message_text(
                "اطلاعات این تخصص در دسترس نیست.",
                reply_markup=get_back_keyboard(lang),
            )
            return

        per_page = 12
        start = page * per_page
        chunk = doctors[start:start + per_page]

        lines = [f"👨‍⚕️ {spec['label']} — {len(doctors)} پزشک:\n"]
        for index, doc in enumerate(chunk, start=start + 1):
            lines.append(f"{index}. {doc['name_fa']}")
        lines.append(
            "\n💡 برای رزرو نوبت از دکمه «📅 رزرو نوبت» در منوی اصلی استفاده کنید."
        )

        rows = []
        nav = []
        total_pages = max(1, (len(doctors) + per_page - 1) // per_page)
        if page > 0:
            nav.append(InlineKeyboardButton("▶️ قبلی", callback_data=f"med_spec_{spec_key}_{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("◀️ بعدی", callback_data=f"med_spec_{spec_key}_{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([InlineKeyboardButton("🔙 بازگشت به تخصص‌ها", callback_data="med_back")])
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data == "med_back":
        try:
            await query.edit_message_text(
                "👨‍⚕️ تخصص‌های پزشکی شیراز:",
                reply_markup=_medical_spec_keyboard(0)[0],
            )
        except Exception:
            pass
        return


async def show_package(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """🆕 پیام مناسب برای دکمه «💎 پکیج کامل» (قبلاً مرده بود)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        package_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 رزرو نوبت", callback_data="start_booking")],
            [InlineKeyboardButton(get_msg_btn(lang, "btn_back"), callback_data="back_main")],
        ])
        text = (
            "💎 پکیج کامل گردشگری سلامت\n\n"
            "پکیج کامل شامل همه‌ی خدمات به‌صورت یکجا است:\n"
            "• هماهنگی نوبت پزشک و بیمارستان\n"
            "• اقامت (هتل / مهمان‌پذیر)\n"
            "• ترانسفر فرودگاه و بین مراکز درمانی\n"
            "• مترجم همراه\n\n"
            "📞 برای سفارش پکیج، با پشتیبانی تماس بگیرید: 190\n"
            "یا از دکمه زیر نوبت پزشک را رزرو کنید:"
        )
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=package_keyboard)
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))