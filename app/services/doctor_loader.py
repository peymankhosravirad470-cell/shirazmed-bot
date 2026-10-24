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
            label = ""
            for doc in doctors:
                if isinstance(doc, dict) and doc.get("specialty_fa"):
                    label = str(doc["specialty_fa"]).strip()
                    break
            specialties.append({
                "key": key,
                "label": label or key,
                "count": len([d for d in doctors if isinstance(d, dict)]),
            })
    except OSError as error:
        logger.error("خطا در لیست‌کردن تخصص‌ها: %s", error)

    specialties.sort(key=lambda s: s["label"])
    _cache["mtime"] = mtime
    _cache["specialties"] = specialties
    return specialties


def load_specialties() -> list[dict[str, Any]]:
    """لیست تخصص‌ها: [{key, label, count}] مرتب بر اساس نام فارسی."""
    return _load_all()


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