# -*- coding: utf-8 -*-
"""🆕 ممیزی (بخش J): بوت‌استرپ داده‌ی استاتیک روی دیسک پایدار لیارا.

مسئله: در liara.json دیسک پایدار روی «/app/data» mount می‌شود؛ یعنی هم داده‌ی
ران‌تایم (نوبت‌ها، تراکنش‌ها، داروها) و هم داده‌ی استاتیک منوها (بیمارستان‌ها،
بیمه‌ها، پزشکان و…) در همان مسیر واحد زندگی می‌کنند. اگر دیسک پایدار خالی/ناقص
باشد (اولین استقرار یا دیسک جدید)، فایل‌های استاتیکِ داخل ایمیج زیر mount پنهان
می‌شوند و همه‌ی منوها خالی می‌شوند.

راه‌حل محافظه‌کارانه: Dockerfile یک کپی از data را در «/app/data_seed» (خارج از
mount) نگه می‌دارد و این ماژول در startup فقط فایل‌های «موجود در سید و غایب در
دیسک» را کپی می‌کند. هیچ‌وقت فایل موجود را بازنویسی نمی‌کند — داده‌ی زنده‌ی
کاربران و هر تغییری که خود ربات روی دیسک داده محفوظ می‌ماند.

⚠️ محدودیت مستند: به‌روزرسانی روزانه‌ی پزشکان (collect.py → commit → deploy جدید)
فقط وقتی روی دیسک ظاهر می‌شود که فایل روی دیسک «غایب» باشد؛ فایل قدیمی موجود
بازنویسی نمی‌شود تا داده‌ی ثبت‌شده‌ی محلی از بین نرود. اگر روزی بخواهید نسخه‌ی
ایمیج حتماً برنده باشد، باید سیاست جداگانه‌ای تصمیم‌گیری شود (در گزارش ممیزی آمده).
"""

from __future__ import annotations

import logging
import os
import shutil

logger = logging.getLogger(__name__)

# پوشه‌ی سید (خارج از دیسک mount شده) — در Dockerfile ساخته می‌شود
SEED_DIR = os.environ.get("DATA_SEED_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_seed"))
# ریشه‌ی داده‌ی اجرایی (همان که سرویس‌ها می‌خوانند)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# فایل‌های ران‌تایم که هرگز از سید «ساخته» نمی‌شوند (داده‌ی کاربران)
RUNTIME_ONLY = {
    "appointments.json",
    "medications.json",
    "complaints.json",
    "doctor_registrations.json",
}


def seed_static_data(data_dir: str = DATA_DIR, seed_dir: str = SEED_DIR) -> int:
    """کپی یک‌طرفه‌ی فایل‌های غایب از data_seed به data. خروجی: تعداد کپی‌ها.

    - فایل موجود → دست‌نخورده (هیچ بازنویسی‌ای در هیچ شرایطی).
    - دایرکتوری‌ها (مثل doctors/) بازگشتی پیمایش می‌شوند.
    - شکست هر کپی کل فرآیند را نمی‌شکند (فقط لاگ).
    """
    copied = 0
    if not os.path.isdir(seed_dir):
        logger.info("data_seed exists? no — skipping static data bootstrap (%s)", seed_dir)
        return 0
    os.makedirs(data_dir, exist_ok=True)
    for root, _dirs, files in os.walk(seed_dir):
        rel = os.path.relpath(root, seed_dir)
        target_root = os.path.join(data_dir, rel) if rel != "." else data_dir
        os.makedirs(target_root, exist_ok=True)
        for name in files:
            if name in RUNTIME_ONLY or not name.endswith(".json"):
                continue
            src = os.path.join(root, name)
            dst = os.path.join(target_root, name)
            if os.path.exists(dst):
                continue
            try:
                shutil.copy2(src, dst)
                copied += 1
            except OSError as error:
                logger.error("data seed copy failed for %s: %s", name, error)
    if copied:
        logger.info("Static data bootstrap: %d missing file(s) copied from seed to data dir.", copied)
    else:
        logger.info("Static data bootstrap: nothing to copy (all files present).")
    return copied
