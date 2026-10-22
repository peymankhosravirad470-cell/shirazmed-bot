# -*- coding: utf-8 -*-
"""هندلر دکمه‌های منوی اصلی و مسیریابی بخش‌های مختلف ربات."""

from __future__ import annotations

import json
import os
import traceback
from typing import Any, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_keyboard, get_main_menu_keyboard
from app.keyboards.non_medical import get_non_medical_keyboard
from app.keyboards.tourism import get_tourism_keyboard
from app.keyboards.paramedical import get_paramedical_keyboard
from app.keyboards.elderly import get_elderly_keyboard
from app.locales import get_msg_btn
from app.locales.fa import MSG

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


async def _show_items(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    filename: str,
    empty_message: str = "اطلاعاتی یافت نشد.",
) -> None:
    """نمایش عمومی آیتم‌های یک فایل JSON به صورت پیام‌های جداگانه."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    try:
        items = load_json(filename)

        if not isinstance(items, list):
            items = []

        if not items:
            await context.bot.send_message(
                chat_id=chat_id,
                text=empty_message,
                reply_markup=get_back_keyboard(lang),
            )
            return

        sent_any = False

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
                text=empty_message,
                reply_markup=get_back_keyboard(lang),
            )

    except Exception as error:
        traceback.print_exc()
        print(f"Error showing items from '{filename}': {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard(lang),
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
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    await _show_items(update, context, lang, "complaints.json", empty_message="اطلاعاتی یافت نشد.")


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
    """نمایش اطلاعات مترجم (به زودی)."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    try:
        title = _safe_btn(lang, "translator_title", "مترجم پزشکی")
        info = "این بخش به زودی فعال می‌شود. برای هماهنگی با مترجم، با پشتیبانی تماس بگیرید: 07132122000"
        message_text = f"{title}\n\n{info}" if title else info
        await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=get_back_keyboard(lang))
    except Exception as error:
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="خطا در دریافت اطلاعات.", reply_markup=get_back_keyboard(lang))


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
        # فعلاً خالی است. در آینده از appointments.json خوانده می‌شود.
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
            f"لینک اختصاصی شما:\n`{invite_link}`"
        )
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=get_back_keyboard(lang))
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
            # فیلتر کردن اسنپ و تپسی از لیست transport
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
    if data == "rights":
        await show_patient_guide(update, context, lang)
        return
    if data == "complaints":
        await show_complaints(update, context, lang)
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
    if data == "charter":
        await show_charter(update, context, lang)
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

    # فال‌بک (اگر دکمه‌ای هندل نشد)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="این بخش در نسخه‌های بعدی فعال می‌شود.",
        reply_markup=get_back_keyboard(lang),
    )