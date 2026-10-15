# -*- coding: utf-8 -*-
"""
Shiraz Medical — Doctor Collector v3
جمع‌آوری اسم پزشکان شیراز با فیلتر دقیق
"""

import requests
import json
import os
import re

DATA_DIR = "data"
DOCTORS_DIR = os.path.join(DATA_DIR, "doctors")
CACHE_DIR = "cache"

os.makedirs(DOCTORS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

SPECIALTIES = [
    ("cardio.json", "قلب و عروق",  "cardiac-surgeon",  "cardiologist"),
    ("derma.json",  "پوست و مو",   "dermatologist",    "dermatologist"),
    ("dental.json", "دندانپزشکی",  "dentist",          "dentist"),
]


# ─────────────────────────────────────────────
# کلمات ممنوعه (اگر بعد از «دکتر» بیان، اسم نیستن)
# ─────────────────────────────────────────────

FORBIDDEN_WORDS = {
    # تخصص‌ها
    "ارتوپدی", "ارتوپد", "پوست", "مو", "اعصاب", "روان", "روانپزشک",
    "روانشناس", "چشم", "گوش", "حلق", "بینی", "کلیه", "مغز", "زنان",
    "زایمان", "اطفال", "کودکان", "ریه", "گوارش", "ارولوژی", "اورولوژی",
    "تغذیه", "بیهوشی", "دندانپزشک", "دندانپزشکی", "قلب", "عروق",
    "روماتولوژی", "غدد", "خون", "سرطان", "عفونی", "نفرولوژی",
    "آلرژی", "طب", "سنتی", "رادیولوژی", "اورژانس", "ورزشی",
    "کار", "ژنتیک", "مکمل", "قانونی", "سوزنی", "مامایی",
    "گفتاردرمانی", "فیزیوتراپی", "کاردرمانی", "شنوایی", "بینایی",
    "پاتولوژی", "آسیب", "شناسی", "سونوگرافی", "جراح", "جراحی",
    "متخصص", "فوق", "تخصص", "تخصصی", "عمومی", "داخلی",
    # عمومی و اتصالی
    "آنلاین", "بیماری", "بیماریهای", "بیماری‌های", "های", "مشاوره",
    "کلینیک", "نوبت", "خدمات", "درمان", "درمانی", "مطب",
    "تو", "در", "شهرهای", "مختلف", "مورد", "نظر", "خود", "را",
    "هم", "پروفایل", "هر", "به", "روش", "برای", "شما",
    "هایتان", "خیلی", "بسیار", "همه", "لیست", "مشاهده",
    "پزشکان", "پزشک", "دکترها", "دکترهای", "دیگر", "دیگری",
    "بیشتر", "بیشترین", "بهترین", "برترین", "مناسب", "مناسبترین",
    # شهرها
    "تهران", "اصفهان", "تبریز", "شیراز", "ایران", "مشهد", "کرج",
    "اهواز", "قم", "کرمان", "کرمانشاه", "رشت", "یزد", "زاهدان",
    "اردبیل", "بندرعباس", "ساری", "گرگان", "سنندج", "ارومیه",
    "همدان", "بوشهر", "یاسوج", "سمنان", "زنجان", "قزوین",
    "خرم", "خرم‌آباد", "بیرجند", "شهرکرد", "ایلام", "بجنورد",
    "شهر", "استان", "کشور", "ایرانی", "خارج",
    # ضمایر و افعال
    "است", "هست", "هستند", "دارد", "دارند", "می", "نمی",
    "استاد", "دانشیار", "هیئت", "علمی", "دانشگاه",
    "کل", "تمام", "همگی", "چند", "چندین",
    # انگلیسی (اسم ایرانی نباید انگلیسی باشه)
    "doctor", "dr", "medical", "clinic",
}


# پسوندهای رایج فامیل ایرانی
COMMON_SUFFIXES = {
    "زاده", "پور", "نژاد", "نیا", "فر", "وند", "مند", "بخش",
    "خواه", "طلب", "پرور", "پیشه", "کار", "گر", "بان",
}


def is_valid_name(name: str) -> bool:
    """چک می‌کنه آیا اسم واقعاً به یه دکتر شبیه‌ست یا نه."""
    if not name:
        return False

    # حذف فاصله‌های اضافی
    name = re.sub(r'\s+', ' ', name.strip())

    # طول منطقی
    if len(name) < 7 or len(name) > 45:
        return False

    # باید با «دکتر » شروع بشه
    if not name.startswith("دکتر "):
        return False

    # جدا کردن کلمات
    parts = name.split()
    if len(parts) < 2 or len(parts) > 5:
        return False

    # کلمات بعد از «دکتر»
    after_dr = parts[1:]
    if not after_dr:
        return False

    # هیچ کدوم از کلمات نباید توی لیست ممنوعه باشه
    for word in after_dr:
        clean_word = word.strip("،.,:;!؟?()")
        if clean_word in FORBIDDEN_WORDS:
            return False

    # همه‌ی کلمات باید فقط حروف فارسی باشن (بدون عدد، بدون انگلیسی)
    for word in after_dr:
        if not re.match(r'^[\u0600-\u06FF‌]+$', word):
            return False

    # هر کلمه حداقل ۲ حرف
    for word in after_dr:
        if len(word) < 2:
            return False

    # کلمه‌ی اول نباید فقط یه حرف باشه
    if len(after_dr[0]) < 3:
        return False

    # فیلتر الگوهای آشکارا اشتباه
    blacklist_patterns = [
        r'^دکتر\s+(\S+)\s+(اصفهان|تهران|تبریز|شیراز|مشهد|ایران|کرج)$',  # «دکتر ارتوپدی اصفهان»
        r'^دکتر\s+(مورد|نظر|خود|شهر|های|هم|پروفایل|هر)\s',  # «دکتر مورد نظر خود»
        r'^دکتر\s+\S*\s*(را|است|هست|دارد|می)\s*$',  # افعال
    ]
    for pattern in blacklist_patterns:
        if re.match(pattern, name):
            return False

    return True


def fetch(url, cache_name):
    """دانلود صفحه با cache."""
    cache_path = os.path.join(CACHE_DIR, cache_name)

    if os.path.isfile(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 1000 and "<!-- STATUS: 200" in content[:60]:
            print(f"      from cache: {cache_name} ({len(content)} bytes)")
            return content.split("-->\n", 1)[-1]

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        print(f"      HTTP {r.status_code}, len={len(r.text)}")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- STATUS: {r.status_code} URL: {url} -->\n")
            f.write(r.text)
        if r.status_code == 200:
            return r.text
        return ""
    except Exception as e:
        print(f"      ERR: {e}")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- EXCEPTION: {e} URL: {url} -->")
        return ""


def extract_names(html):
    """استخراج اسم پزشکان با فیلتر دقیق."""
    if not html:
        return []

    raw = re.findall(
        r'(دکتر\s+[\u0600-\u06FF]{2,}(?:\s+[\u0600-\u06FF]{2,}){0,3})',
        html,
    )

    names = set()
    for r in raw:
        name = re.sub(r'\s+', ' ', r.strip())
        if is_valid_name(name):
            names.add(name)

    return sorted(names)


def process_specialty(row):
    out_file, name_fa, slug_doctoreto, slug_darmankade = row
    print(f"\n{'='*60}")
    print(f"🔍 {name_fa} → {out_file}")
    print(f"{'='*60}")

    all_names = set()

    url1 = f"https://doctoreto.com/doctors/speciality/{slug_doctoreto}/city/shiraz"
    print(f"  [1] {url1}")
    names1 = extract_names(fetch(url1, f"doctoreto_{slug_doctoreto}.html"))
    print(f"      → {len(names1)} اسم معتبر")
    all_names.update(names1)

    url2 = f"https://www.darmankade.com/b/Shiraz/{slug_darmankade}"
    print(f"  [2] {url2}")
    names2 = extract_names(fetch(url2, f"darmankade_{slug_darmankade}.html"))
    print(f"      → {len(names2)} اسم معتبر")
    all_names.update(names2)

    result = [
        {
            "id": f"doc_{i:03d}",
            "name_fa": name,
            "specialty_fa": name_fa,
            "status": "active",
        }
        for i, name in enumerate(sorted(all_names), 1)
    ]

    out_path = os.path.join(DOCTORS_DIR, out_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {out_path} — {len(result)} پزشک")
    return len(result)


def main():
    print("═" * 60)
    print(f"  Doctor Collector v3")
    print(f"  Specialties: {len(SPECIALTIES)}")
    print("═" * 60)

    stats = {}
    for i, row in enumerate(SPECIALTIES, 1):
        print(f"\n[{i}/{len(SPECIALTIES)}]")
        try:
            stats[row[0]] = process_specialty(row)
        except Exception as e:
            print(f"  ❌ {e}")
            stats[row[0]] = 0

    print("\n" + "═" * 60)
    print("  Summary")
    print("═" * 60)
    for fname, cnt in stats.items():
        print(f"  {fname:20s} {cnt:4d}")
    print("═" * 60)


if __name__ == "__main__":
    main()