# -*- coding: utf-8 -*-
"""
جمع‌آوری اسامی پزشکان شیراز به تفکیک تخصص.

منابع (تأیید شده، واقعاً وجود دارند و HTML سمت سرور رندر می‌شود):
  - doctoreto.com
  - darmankade.com

توجه مهم: دامنه‌های salamati24.com و exiryab.com که در نسخه‌ی قبلی استفاده
می‌شدند، در جستجوی وب هیچ ردی نداشتند و به‌احتمال زیاد الگوی URL آن‌ها
حدسی/اشتباه بوده — به همین دلیل همه‌ی فایل‌های JSON خالی می‌ماندند.
این نسخه آن دو را با منابعی که واقعاً پاسخ می‌دهند جایگزین کرده است.
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

# (نام فایل خروجی, نام فارسی تخصص, اسلاگ doctoreto, اسلاگ darmankade)
# برای رسیدن به ۵۰ تخصص، همین الگو را برای بقیه تخصص‌ها تکرار کنید —
# اسلاگ هر سایت را از آدرس واقعی صفحه‌ی همان تخصص در همان سایت کپی کنید،
# چون اسلاگ doctoreto و darmankade همیشه یکسان نیستند.
SPECIALTIES = [
    ("cardio.json", "قلب و عروق",  "cardiac-surgeon", "cardiologist"),
    ("derma.json",  "پوست و مو",   "dermatologist",   "dermatologist"),
    ("dental.json", "دندانپزشکی",  "dentist",         "dentist"),
]


def fetch(url, cache_name):
    """دانلود صفحه؛ خروجی را همیشه (حتی روی خطا) در cache/ ذخیره می‌کند
    تا بعداً با دانلود artifact بشود ساختار واقعی HTML را دید."""
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


# کلماتی که اگر بلافاصله بعد از «دکتر» بیایند، یعنی این یک لینک منو/دسته‌بندی
# است (مثل «دکتر آنلاین ارتوپدی»، «مشاوره آنلاین دکتر بیماری‌های عفونی»)
# نه اسم یک پزشک واقعی.
NON_NAME_WORDS = {
    "آنلاین", "بیماری", "بیماریهای", "بیماری‌های", "های", "عفونی",
    "متخصص", "فوق", "تخصص", "تخصصی", "مشاوره", "کلینیک", "نوبت",
    "عمومی", "داخلی", "جراحی", "خدمات", "درمان", "درمانی", "مطب",
}


def extract_names(html):
    """اسامی به‌فرم «دکتر نام خانوادگی» را از متن HTML استخراج می‌کند و
    لینک‌های منو/دسته‌بندی مثل «دکتر آنلاین ارتوپدی» را فیلتر می‌کند."""
    if not html:
        return []
    names = set()
    for m in re.finditer(
        r'(دکتر\s+[\u0600-\u06FF]{2,}(?:\s+[\u0600-\u06FF]{2,}){0,3})',
        html,
    ):
        name = re.sub(r'\s+', ' ', m.group(1).strip())
        if not (5 < len(name) < 50):
            continue
        words = name.split()
        # اگر هر کدام از کلمات بعد از «دکتر» در لیست ممنوعه باشد، رد کن
        if any(w in NON_NAME_WORDS for w in words[1:]):
            continue
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
    print(f"      → {len(names1)} اسم")
    all_names.update(names1)

    url2 = f"https://www.darmankade.com/b/Shiraz/{slug_darmankade}"
    print(f"  [2] {url2}")
    names2 = extract_names(fetch(url2, f"darmankade_{slug_darmankade}.html"))
    print(f"      → {len(names2)} اسم")
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
    for fname, cnt in stats.items():
        print(f"  {fname:20s} {cnt:4d}")
    print("═" * 60)
    print("\nℹ️  فایل‌های HTML خام هر درخواست در cache/ ذخیره شدند — ")
    print("   اگر عدد پزشک‌ها صفر بود، آن‌ها را از artifact دانلود و باز کنید")
    print("   تا ببینید سایت چه چیزی واقعاً برگردانده (404، Cloudflare، و...).")


if __name__ == "__main__":
    main()
