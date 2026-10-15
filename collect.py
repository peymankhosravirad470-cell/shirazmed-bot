# -*- coding: utf-8 -*-
"""
Shiraz Medical — Doctor Collector v2
ذخیره HTML + استخراج اسم
"""

import requests
import json
import os
import time
import re

DATA_DIR = "data"
DOCTORS_DIR = os.path.join(DATA_DIR, "doctors")
CACHE_DIR = "cache"
DEBUG_DIR = "cache/html"

os.makedirs(DOCTORS_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

# فقط قلب برای تست
SPECIALTIES = [
    ("cardio.json", "قلب و عروق", "cardiology"),
    ("derma.json",  "پوست و مو",  "dermatology"),
    ("dental.json", "دندانپزشکی", "dentistry"),
]


def fetch(url: str, cache_name: str) -> str:
    """Download URL with caching."""
    cache_path = os.path.join(CACHE_DIR, cache_name)
    if os.path.isfile(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < 86400:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        print(f"      HTTP {r.status_code}, len={len(r.text)}")
        if r.status_code == 200:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(r.text)
            return r.text
        return ""
    except Exception as e:
        print(f"      ERR: {e}")
        return ""


def extract_names(html: str) -> list:
    """استخراج اسم دکتر از HTML — چند الگو"""
    if not html:
        return []

    names = set()

    # الگو ۱: "دکتر XXX" داخل هر تگی
    for m in re.finditer(r'(دکتر\s+[\u0600-\u06FF]{2,}(?:\s+[\u0600-\u06FF]{2,}){0,3})', html):
        name = m.group(1).strip()
        name = re.sub(r'\s+', ' ', name)
        if 5 < len(name) < 50:
            names.add(name)

    return sorted(names)


def process_specialty(row):
    out_file, name_fa, slug = row

    print(f"\n{'='*60}")
    print(f"🔍 {name_fa} → {out_file}")
    print(f"{'='*60}")

    all_names = set()

    # salamati24
    url1 = f"https://salamati24.com/doctors/{slug}/shiraz"
    print(f"  [1] {url1}")
    html1 = fetch(url1, f"sal24_{slug}.html")
    names1 = extract_names(html1)
    print(f"      → {len(names1)} اسم")
    all_names.update(names1)

    # exiryab
    url2 = f"https://exiryab.com/doctors/{slug}/shiraz"
    print(f"  [2] {url2}")
    html2 = fetch(url2, f"exiryab_{slug}.html")
    names2 = extract_names(html2)
    print(f"      → {len(names2)} اسم")
    all_names.update(names2)

    # ساخت نتیجه
    result = []
    for i, name in enumerate(sorted(all_names), 1):
        result.append({
            "id": f"doc_{i:03d}",
            "name_fa": name,
            "specialty_fa": name_fa,
            "status": "active",
        })

    out_path = os.path.join(DOCTORS_DIR, out_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {out_path} — {len(result)} پزشک")
    return len(result)


def main():
    print("═" * 60)
    print("  Doctor Collector v2")
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


if __name__ == "__main__":
    main()