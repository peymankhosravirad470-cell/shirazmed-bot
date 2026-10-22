# -*- coding: utf-8 -*-
"""هندلر دکمه‌های منوی اصلی و مسیریابی بخش‌های مختلف ربات."""

from __future__ import annotations

import json
import os
import traceback
from typing import Any, Union

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_keyboard
from app.keyboards.non_medical import get_non_medical_keyboard
from app.keyboards.tourism import get_tourism_keyboard
from app.keyboards.paramedical import get_paramedical_keyboard
from app.keyboards.elderly import get_elderly_keyboard


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
    """نمایش لیست هتل‌ها از فایل hotels.json."""
    await _show_items(
        update, context, lang, "hotels.json", empty_message="هتلی یافت نشد."
    )


async def show_motels(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست مهمان‌پذیرها از فایل motels.json."""
    await _show_items(
        update, context, lang, "motels.json", empty_message="مهمان‌پذیری یافت نشد."
    )


async def show_tourist_houses(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست خانه‌های مسافر از فایل tourist_houses.json."""
    await _show_items(
        update,
        context,
        lang,
        "tourist_houses.json",
        empty_message="خانه مسافری یافت نشد.",
    )


async def show_transport(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش لیست وسایل نقلیه از فایل transport.json."""
    await _show_items(
        update,
        context,
        lang,
        "transport.json",
        empty_message="وسیله نقلیه‌ای یافت نشد.",
    )


async def show_patient_guide(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش راهنمای بیمار از فایل patient_guide.json."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    try:
        data = load_json("patient_guide.json")

        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            items = []

        if not items:
            await context.bot.send_message(
                chat_id=chat_id,
                text="اطلاعاتی یافت نشد.",
                reply_markup=get_back_keyboard(lang),
            )
            return

        sent_any = False

        for item in items:
            if not isinstance(item, dict):
                continue

            message_lines = []

            # عنوان (Topic)
            topic = _get_localized_field(item, "topic", lang)
            if topic:
                message_lines.append(f"📌 {topic}\n")

            # مدارک ویزای پزشکی
            visa_docs = _get_localized_list(item, "medical_visa_documents", lang)
            if visa_docs:
                message_lines.append("🛂 مدارک ویزای پزشکی:")
                for i, doc in enumerate(visa_docs, 1):
                    message_lines.append(f"{i}. {doc}")
                message_lines.append("")

            # مدارک پذیرش بیمارستان
            admission_docs = _get_localized_list(
                item, "hospital_admission_documents", lang
            )
            if admission_docs:
                message_lines.append("🏥 مدارک پذیرش بیمارستان:")
                for i, doc in enumerate(admission_docs, 1):
                    message_lines.append(f"{i}. {doc}")
                message_lines.append("")

            # الزام مترجم
            translator = _get_localized_field(item, "translator_requirement", lang)
            if translator:
                message_lines.append(f"🗣 الزام مترجم: {translator}\n")

            # مراحل اداری (اصلاح ایراد 1)
            steps = _get_localized_list(item, "administrative_steps", lang)
            if steps:
                message_lines.append("📋 مراحل اداری:")
                for step in steps:
                    if isinstance(step, dict):
                        step_num = step.get("step", "")
                        title = step.get("title", "")
                        description = step.get("description", "")
                        if title and description:
                            message_lines.append(
                                f"مرحله {step_num}: {title} - {description}"
                            )
                        elif title:
                            message_lines.append(f"مرحله {step_num}: {title}")
                        elif description:
                            message_lines.append(f"مرحله {step_num}: {description}")
                        else:
                            message_lines.append(f"مرحله {step_num}: {step}")
                    else:
                        message_lines.append(f"- {step}")
                message_lines.append("")

            # هزینه‌ها
            costs = _get_localized_field(item, "costs_and_payment", lang)
            if costs:
                message_lines.append(f"💰 هزینه‌ها و پرداخت: {costs}\n")

            # مراجع رسمی (اصلاح ایراد 2)
            authorities = _get_localized_list(item, "official_authorities", lang)
            if authorities:
                message_lines.append("🏛 مراجع رسمی:")
                for auth in authorities:
                    if isinstance(auth, dict):
                        organization = auth.get("organization", "")
                        role = auth.get("role", "")
                        if organization and role:
                            message_lines.append(f"- {organization}: {role}")
                        elif organization:
                            message_lines.append(f"- {organization}")
                        elif role:
                            message_lines.append(f"- {role}")
                        else:
                            message_lines.append(f"- {auth}")
                    else:
                        message_lines.append(f"- {auth}")
                message_lines.append("")

            # لینک‌های سامانه‌های رسمی (اصلاح ایراد 3)
            links = item.get("official_system_links", []) or []
            if links and isinstance(links, list):
                message_lines.append("🔗 لینک سامانه‌های رسمی:")
                for link in links:
                    if isinstance(link, dict):
                        link_name = _get_localized_field(link, "name", lang)
                        url = link.get("url", "")
                        if link_name and url:
                            message_lines.append(f"- {link_name}: {url}")
                        elif link_name:
                            message_lines.append(f"- {link_name}")
                        elif url:
                            message_lines.append(f"- {url}")
                        else:
                            message_lines.append(f"- {link}")
                    else:
                        message_lines.append(f"- {link}")

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
        print(f"Error showing patient guide: {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard(lang),
        )


async def show_complaints(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش مراجع شکایات از فایل complaints.json."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    try:
        items = load_json("complaints.json")

        if not isinstance(items, list):
            items = []

        if not items:
            await context.bot.send_message(
                chat_id=chat_id,
                text="اطلاعاتی یافت نشد.",
                reply_markup=get_back_keyboard(lang),
            )
            return

        sent_any = False

        for item in items:
            if not isinstance(item, dict):
                continue

            category = _get_localized_field(item, "category", lang)
            department = _get_localized_field(item, "department", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""
            email = str(item.get("email", "")) if item.get("email") else ""
            working_hours = _get_localized_field(item, "working_hours", lang)
            response_time = _get_localized_field(item, "response_time", lang)
            process = _get_localized_list(item, "process", lang)
            notes = _get_localized_field(item, "notes", lang)

            message_lines = []

            if category:
                message_lines.append(f"📂 دسته: {category}")

            if department:
                message_lines.append(f"🏢 مرجع: {department}")

            if phone:
                message_lines.append(f"📞 تلفن: {phone}")

            if email:
                message_lines.append(f"📧 ایمیل: {email}")

            if working_hours:
                message_lines.append(f"⏰ ساعات کاری: {working_hours}")

            if response_time:
                message_lines.append(f"⏱ زمان پاسخ: {response_time}")

            # (اصلاح ایراد 5)
            if process:
                message_lines.append("📋 مراحل ثبت شکایت:")
                for i, step in enumerate(process, 1):
                    if isinstance(step, dict):
                        step_title = step.get("title", "")
                        step_description = step.get("description", "")
                        if step_title and step_description:
                            message_lines.append(
                                f"{i}. {step_title} - {step_description}"
                            )
                        elif step_title:
                            message_lines.append(f"{i}. {step_title}")
                        elif step_description:
                            message_lines.append(f"{i}. {step_description}")
                        else:
                            message_lines.append(f"{i}. {step}")
                    else:
                        message_lines.append(f"{i}. {step}")

            if notes:
                message_lines.append(f"📝 توضیحات: {notes}")

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
        print(f"Error showing complaints: {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard(lang),
        )


async def show_support(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str
) -> None:
    """نمایش مراکز پشتیبانی از فایل support.json."""
    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    try:
        items = load_json("support.json")

        if not isinstance(items, list):
            items = []

        if not items:
            await context.bot.send_message(
                chat_id=chat_id,
                text="اطلاعاتی یافت نشد.",
                reply_markup=get_back_keyboard(lang),
            )
            return

        sent_any = False

        for item in items:
            if not isinstance(item, dict):
                continue

            support_type = _get_localized_field(item, "type", lang)
            center_name = _get_localized_field(item, "name", lang)
            phone = str(item.get("phone", "")) if item.get("phone") else ""
            emergency = (
                str(item.get("emergency_contact", ""))
                if item.get("emergency_contact")
                else ""
            )
            email = str(item.get("email", "")) if item.get("email") else ""
            working_hours = _get_localized_field(item, "working_hours", lang)
            services = _get_localized_list(item, "services", lang)
            notes = _get_localized_field(item, "notes", lang)

            message_lines = []

            if support_type:
                message_lines.append(f"📌 نوع: {support_type}")

            if center_name:
                message_lines.append(f"🏢 مرکز: {center_name}")

            if phone:
                message_lines.append(f"📞 تلفن: {phone}")

            if emergency:
                message_lines.append(f"🚨 شماره اضطراری: {emergency}")

            if email:
                message_lines.append(f"📧 ایمیل: {email}")

            if working_hours:
                message_lines.append(f"⏰ ساعات کاری: {working_hours}")

            # (اصلاح ایراد 4)
            if services:
                message_lines.append("🛠 خدمات:")
                for i, srv in enumerate(services, 1):
                    if isinstance(srv, dict):
                        srv_name = srv.get("name", "")
                        srv_description = srv.get("description", "")
                        if srv_name and srv_description:
                            message_lines.append(
                                f"{i}. {srv_name} - {srv_description}"
                            )
                        elif srv_name:
                            message_lines.append(f"{i}. {srv_name}")
                        elif srv_description:
                            message_lines.append(f"{i}. {srv_description}")
                        else:
                            message_lines.append(f"{i}. {srv}")
                    else:
                        message_lines.append(f"{i}. {srv}")

            if notes:
                message_lines.append(f"📝 توضیحات: {notes}")

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
        print(f"Error showing support centers: {error}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard(lang),
        )


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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="منوی خدمات غیرپزشکی:",
            reply_markup=get_non_medical_keyboard(lang),
        )
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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="منوی گردشگری:",
            reply_markup=get_tourism_keyboard(lang),
        )
        return

    if data == "tour_city":
        await _show_items(update, context, lang, "leisure_city.json")
        return

    if data == "tour_outside":
        await _show_items(update, context, lang, "leisure_outside.json")
        return

    if data == "paramedical":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="منوی پیراپزشکی:",
            reply_markup=get_paramedical_keyboard(lang),
        )
        return

    if data in (
        "para_physio",
        "para_lab",
        "para_radiology",
        "para_nursing",
        "para_injection",
        "para_trad_med",
        "para_occupational",
        "para_speech",
        "para_orthotics",
    ):
        await _show_items(update, context, lang, "paramedical.json")
        return

    if data == "elderly":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="منوی خانه سالمندان:",
            reply_markup=get_elderly_keyboard(lang),
        )
        return

    if data == "elderly_all":
        await _show_items(update, context, lang, "elderly_homes.json")
        return

    if data == "hubs":
        await _show_items(update, context, lang, "transport_hubs.json")
        return

    if data == "insurance":
        await _show_items(update, context, lang, "insurances.json")
        return

    if data == "patient_guide":
        await show_patient_guide(update, context, lang)
        return

    if data == "complaints":
        await show_complaints(update, context, lang)
        return

    if data == "support":
        await show_support(update, context, lang)
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="این بخش در نسخه‌های بعدی فعال می‌شود.",
        reply_markup=get_back_keyboard(lang),
    )