# -*- coding: utf-8 -*-
"""
لودر داده‌ی پزشکان واقعی از data/doctors/*.json

هر فایل JSON لیستی از پزشکان یک تخصص است، مثلاً:
    {"id": "doc_001", "name_fa": "دکتر آرش یزدان شناس", "specialty_fa": "قلب و عروق", "status": "active"}

باگ قبلی: ۱۱۴ پزشک واقعی جمع‌آوری شده بود ولی رزرو فقط ۳ پزشک ساختگی (TEMP_DOCTORS)
نشان می‌داد. این ماژول داده‌ی واقعی را با کش مبتنی بر mtime (چون داده‌ها روزانه با
GitHub Actions آپدیت می‌شوند) در اختیار رزرو و مرور پزشکی قرار می‌دهد.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCTORS_DIR = os.path.join(_BASE_DIR, "data", "doctors")

_cache: dict[str, Any] = {"mtime": 0.0, "specialties": []}

# 🆕 برچسب سه‌زبانه تخصص‌هایی که واقعاً پزشک دارند (بقیه با specialty_fa یا کلید نمایش داده می‌شوند)
SPEC_LABELS_I18N: dict[str, dict[str, str]] = {
    "cardio": {"fa": "قلب و عروق", "en": "Cardiology", "ar": "أمراض القلب والأوعية الدموية"},
    "derma": {"fa": "پوست و مو", "en": "Dermatology", "ar": "الجلدية"},
    "dental": {"fa": "دندانپزشکی", "en": "Dentistry", "ar": "طب الأسنان"},
    "internal": {"fa": "داخلی", "en": "Internal Medicine", "ar": "الباطنية"},
    "ortho": {"fa": "ارتوپدی", "en": "Orthopedics", "ar": "جراحة العظام"},
    "gastro": {"fa": "گوارش و کبد", "en": "Gastroenterology", "ar": "الجهاز الهضمي والكبد"},
    "neuro": {"fa": "مغز و اعصاب", "en": "Neurology", "ar": "الأعصاب"},
    "obgyn": {"fa": "زنان و زایمان", "en": "Obstetrics & Gynecology", "ar": "النساء والتوليد"},
    "pediatric": {"fa": "اطفال", "en": "Pediatrics", "ar": "طب الأطفال"},
    "psy": {"fa": "روانشناسی", "en": "Psychology", "ar": "علم النفس"},
    "psychiatry": {"fa": "روانپزشکی", "en": "Psychiatry", "ar": "الطب النفسي"},
    "urology": {"fa": "ارولوژی", "en": "Urology", "ar": "المسالك البولية"},
    "ent": {"fa": "گوش، حلق و بینی", "en": "ENT", "ar": "الأنف والأذن والحنجرة"},
    "ophtha": {"fa": "چشم‌پزشکی", "en": "Ophthalmology", "ar": "طب العيون"},
    "nutrition": {"fa": "تغذیه", "en": "Nutrition", "ar": "التغذية"},
    "physio": {"fa": "فیزیوتراپی", "en": "Physiotherapy", "ar": "العلاج الطبيعي"},
}


def _dir_mtime() -> float:
    """بزرگ‌ترین mtime فایل‌های تخصص را برمی‌گرداند (برای باطل‌کردن کش)."""
    try:
        return max(
            (os.path.getmtime(os.path.join(DOCTORS_DIR, f)) for f in os.listdir(DOCTORS_DIR) if f.endswith(".json")),
            default=0.0,
        )
    except OSError:
        return 0.0


def _load_all() -> list[dict[str, Any]]:
    """همه‌ی تخصص‌ها را می‌خواند و کش می‌کند. خروجی: [{key, label, count}] مرتب‌شده."""
    mtime = _dir_mtime()
    if _cache["mtime"] == mtime and _cache["specialties"]:
        return _cache["specialties"]

    specialties: list[dict[str, Any]] = []
    try:
        if not os.path.isdir(DOCTORS_DIR):
            logger.error("پوشه‌ی data/doctors وجود ندارد: %s", DOCTORS_DIR)
            return []
        for fname in sorted(os.listdir(DOCTORS_DIR)):
            if not fname.endswith(".json"):
                continue
            key = fname[:-5]  # مثل cardio
            path = os.path.join(DOCTORS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    doctors = json.load(fh)
            except (json.JSONDecodeError, OSError) as error:
                logger.warning("خطا در خواندن %s: %s", fname, error)
                continue
            if not isinstance(doctors, list):
                continue
            active = [
                d for d in doctors
                if isinstance(d, dict) and d.get("name_fa") and d.get("status", "active") == "active"
            ]
            label = ""
            for doc in active:
                if doc.get("specialty_fa"):
                    label = str(doc["specialty_fa"]).strip()
                    break
            specialties.append({
                "key": key,
                "label": label or key,
                "count": len(active),
            })
    except OSError as error:
        logger.error("خطا در لیست‌کردن تخصص‌ها: %s", error)

    specialties.sort(key=lambda s: s["label"])
    _cache["mtime"] = mtime
    _cache["specialties"] = specialties
    return specialties


def load_specialties() -> list[dict[str, Any]]:
    """لیست تخصص‌های «دارای پزشک فعال»: [{key, label, count}] مرتب بر اساس نام.

    🆕 فیکس: تخصص‌های بدون پزشک (۴۷ فایل خالی) حذف شدند؛ پیش‌تر همه ۵۰ تخصص
    با شمارندهٔ (0) نمایش داده می‌شدند و کاربر روی گزینه‌های مرده کلیک می‌کرد.
    """
    return [s for s in _load_all() if s["count"] > 0]


def get_label(key: str, lang: str = "fa") -> str:
    """🆕 برچسب تخصص به زبان کاربر؛ در نبود ترجمه، نام فارسی/کلید."""
    item = get_specialty(key)
    i18n = SPEC_LABELS_I18N.get(key, {})
    if i18n.get(lang):
        return i18n[lang]
    return (item or {}).get("label") or i18n.get("fa") or key


def get_specialty(key: str) -> dict[str, Any] | None:
    """اطلاعات یک تخصص با کلید (نام فایل)."""
    for item in _load_all():
        if item["key"] == key:
            return item
    return None


def load_doctors(key: str) -> list[dict[str, Any]]:
    """لیست پزشکان فعالِ یک تخصص. خروجی: [{id, name_fa, specialty_fa}]"""
    path = os.path.join(DOCTORS_DIR, f"{key}.json")
    if not os.path.isfile(path):
        logger.warning("فایل تخصص پیدا نشد: %s", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doctors = json.load(fh)
    except (json.JSONDecodeError, OSError) as error:
        logger.error("خطا در خواندن %s: %s", path, error)
        return []
    if not isinstance(doctors, list):
        return []
    return [
        {
            "id": str(d.get("id", f"idx{index}")),
            "name_fa": str(d.get("name_fa", "پزشک")).strip(),
            "specialty_fa": str(d.get("specialty_fa", "")).strip(),
        }
        for index, d in enumerate(doctors)
        if isinstance(d, dict) and d.get("name_fa") and d.get("status", "active") == "active"
    ]