# -*- coding: utf-8 -*-
"""
Shiraz Medical — Multi-Specialty Doctor Collector
جمع‌آوری پزشکان شیراز از چند منبع برای ۵۰ تخصص
"""

import requests
import json
import os
import time
import re

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

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
    "Connection": "keep-alive",
}

# ─────────────────────────────────────────────
# SPECIALTIES — slug سایت‌ها + نام فارسی
# ─────────────────────────────────────────────

SPECIALTIES = [
    # (فایل خروجی,        نام فارسی,           salamati24,          exiryab,           nobat)
    ("cardio.json",       "قلب و عروق",        "cardiology",        "cardiology",       "cardiology"),
    ("derma.json",        "پوست و مو",         "dermatology",       "dermatology",      "dermatology"),
    ("dental.json",       "دندانپزشکی",        "dentistry",         "dentistry",        "dentistry"),
    ("obgyn.json",        "زنان و زایمان",     "gynecology",        "gynecology",       "gynecology"),
    ("pediatric.json",    "کودکان",            "pediatrics",        "pediatrics",       "pediatrics"),
    ("ophtha.json",       "چشم‌پزشکی",         "ophthalmology",     "ophthalmology",    "ophthalmology"),
    ("ent.json",          "گوش حلق بینی",      "ent",               "ent",              "ent"),
    ("ortho.json",        "ارتوپدی",           "orthopedics",       "orthopedics",      "orthopedics"),
    ("internal.json",     "داخلی",             "internal-medicine", "internal",         "internal"),
    ("psychiatry.json",   "روان‌پزشکی",        "psychiatry",        "psychiatry",       "psychiatry"),
    ("gastro.json",       "گوارش",             "gastroenterology",  "gastroenterology", "gastroenterology"),
    ("endocrine.json",    "غدد",               "endocrinology",     "endocrinology",    "endocrinology"),
    ("urology.json",      "اورولوژی",          "urology",           "urology",          "urology"),
    ("gensurg.json",      "جراحی عمومی",       "general-surgery",   "general-surgery",  "general-surgery"),
    ("neurosurg.json",    "جراحی مغز",         "neurosurgery",      "neurosurgery",     "neurosurgery"),
    ("plastics.json",     "جراحی پلاستیک",     "plastic-surgery",   "plastic-surgery",  "plastic-surgery"),
    ("physmed.json",      "طب فیزیکی",         "physical-medicine", "physical-medicine","physical-medicine"),
    ("nuclear.json",      "پزشکی هسته‌ای",     "nuclear-medicine",  "nuclear-medicine", "nuclear-medicine"),
    ("rheuma.json",       "روماتولوژی",        "rheumatology",      "rheumatology",     "rheumatology"),
    ("hemonc.json",       "خون و سرطان",       "hematology-oncology","hematology",      "hematology"),
    ("pulmo.json",        "ریه",               "pulmonology",       "pulmonology",      "pulmonology"),
    ("cardsurg.json",     "جراحی قلب",         "cardiac-surgery",   "cardiac-surgery",  "cardiac-surgery"),
    ("maxillofacial.json","فک و صورت",         "maxillofacial",     "maxillofacial",    "maxillofacial"),
    ("infectious.json",   "عفونی",             "infectious-disease","infectious",       "infectious"),
    ("nephro.json",       "نفرولوژی",          "nephrology",        "nephrology",       "nephrology"),
    ("allergy.json",      "آلرژی",             "allergy",           "allergy",          "allergy"),
    ("tradmed.json",      "طب سنتی",           "traditional-medicine","traditional",    "traditional"),
    ("radiology.json",    "رادیولوژی",         "radiology",         "radiology",        "radiology"),
    ("emergency.json",    "اورژانس",           "emergency-medicine","emergency",        "emergency"),
    ("sportsmed.json",    "طب ورزشی",          "sports-medicine",   "sports-medicine",  "sports-medicine"),
    ("occupmed.json",     "طب کار",            "occupational-medicine","occupational", "occupational"),
    ("genetics.json",     "ژنتیک",             "genetics",          "genetics",         "genetics"),
    ("complementary.json","پزشکی مکمل",        "complementary",     "complementary",    "complementary"),
    ("forensic.json",     "پزشکی قانونی",      "forensic-medicine", "forensic",         "forensic"),
    ("acupuncture.json",  "سوزن‌درمانی",       "acupuncture",       "acupuncture",      "acupuncture"),
    ("nutrition.json",    "تغذیه",             "nutrition",         "nutrition",        "nutrition"),
    ("midwifery.json",    "مامایی",            "midwifery",         "midwifery",        "midwifery"),
    ("speech.json",       "گفتاردرمانی",       "speech-therapy",    "speech-therapy",   "speech-therapy"),
    ("ivf.json",          "نازایی",            "fertility",         "ivf",              "ivf"),
    ("neuro.json",        "مغز و اعصاب",       "neurology",         "neurology",        "neurology"),
    ("psy.json",          "روان‌شناسی",        "psychology",        "psychology",       "psychology"),
    ("physio.json",       "فیزیوتراپی",        "physiotherapy",     "physiotherapy",    "physiotherapy"),
    ("ot.json",           "کاردرمانی",         "occupational-therapy","occupational-therapy","occupational-therapy"),
    ("optom.json",        "بینایی‌سنجی",       "optometry",         "optometry",        "optometry"),
    ("audio.json",        "شنوایی‌سنجی",       "audiology",         "audiology",        "audiology"),
    ("anesth.json",       "بی‌هوشی",           "anesthesiology",    "anesthesiology",   "anesthesiology"),
    ("patho.json",        "آسیب‌شناسی",        "pathology",         "pathology",        "pathology"),
    ("chiro.json",        "کایروپراکتیک",      "chiropractic",      "chiropractic",     "chiropractic"),
    ("orthotic.json",     "ارتوپدی فنی",       "orthotics",         "orthotics",        "orthotics"),
    ("sonography.json",   "سونوگرافی",         "sonography",        "sonography",       "sonography"),
]


# ─────────────────────────────────────────────
# DOWNLOADER
# ─────────────────────────────────────────────

def fetch(url: str, cache_name: str) -> str:
    """Download URL with caching. Returns HTML or empty string."""
    cache_path = os.path.join(CACHE_DIR, cache_name)
    # اگه کمتر از 24 ساعت پیش دانلود شده، از cache بخون
    if os.path.isfile(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < 86400:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 200:
            html = r.text
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
            return html
        print(f"      ⚠️ HTTP {r.status_code}")
        return ""
    except Exception as e:
        print(f"      ⚠️ خطا: {e}")
        return ""


# ─────────────────────────────────────────────
# PARSER — استخراج اسم پزشکان از HTML
# ─────────────────────────────────────────────

def parse_doctors(html: str, source_name: str) -> list:
    """
    از HTML اسم‌های دکتر رو بیرون می‌کشه.
    الگوهای رایج: "دکتر XXX YYY" یا "دكتر XXX"
    """
    if not html:
        return []

    names = set()

    # الگوی ۱: داخل تگ‌های h1-h6، a، span، div با کلمه "دکتر"
    for m in re.finditer(r'>(دکتر\s+[^<>]{2,60})<', html):
        name = m.group(1).strip()
        name = re.sub(r'\s+', ' ', name)
        if 4 < len(name) < 60:
            names.add(name)

    # الگوی ۲: داخل JSON/script با name یا title
    for m in re.finditer(r'"(?:name|title|doctor_name)"\s*:\s*"(دکتر[^"]{2,60})"', html):
        name = m.group(1).strip()
        names.add(name)

    # الگوی ۳: عنوان صفحه (page title)
    for m in re.finditer(r'<title>([^<]*دکتر[^<]*)</title>', html):
        title = m.group(1)
        for nm in re.findall(r'دکتر\s+[^\-,|<]{2,40}', title):
            names.add(nm.strip())

    result = []
    for name in sorted(names):
        result.append({
            "name_fa": name,
            "specialty_fa": "",  # بعداً پر می‌شه
            "source": source_name,
            "status": "active"
        })
    return result


# ─────────────────────────────────────────────
# PROCESS ONE SPECIALTY
# ─────────────────────────────────────────────

def process_specialty(row):
    out_file, name_fa, sal_slug, exi_slug, nob_slug = row

    print(f"\n{'='*60}")
    print(f"🔍 {name_fa}  →  {out_file}")
    print(f"{'='*60}")

    all_doctors = []

    # منبع ۱: salamati24
    url1 = f"https://salamati24.com/doctors/{sal_slug}/shiraz"
    print(f"  [1] salamati24 ...")
    html1 = fetch(url1, f"sal24_{out_file}.html")
    d1 = parse_doctors(html1, "salamati24.com")
    print(f"      → {len(d1)} پزشک")
    all_doctors.extend(d1)
    time.sleep(1.5)

    # منبع ۲: exiryab
    url2 = f"https://exiryab.com/doctors/{exi_slug}/shiraz"
    print(f"  [2] exiryab ...")
    html2 = fetch(url2, f"exiryab_{out_file}.html")
    d2 = parse_doctors(html2, "exiryab.com")
    print(f"      → {len(d2)} پزشک")
    all_doctors.extend(d2)
    time.sleep(1.5)

    # منبع ۳: nobat.ir
    url3 = f"https://nobat.ir/doctors/city/shiraz/specialty/{nob_slug}"
    print(f"  [3] nobat.ir ...")
    html3 = fetch(url3, f"nobat_{out_file}.html")
    d3 = parse_doctors(html3, "nobat.ir")
    print(f"      → {len(d3)} پزشک")
    all_doctors.extend(d3)

    # ادغام و حذف تکراری
    merged = merge_doctors(all_doctors, name_fa)

    # ذخیره
    out_path = os.path.join(DOCTORS_DIR, out_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"  ✅ ذخیره شد: {out_path}  ({len(merged)} پزشک)")
    return len(merged)


# ─────────────────────────────────────────────
# MERGE & DEDUP
# ─────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """اسم رو برای مقایسه نرمال کن."""
    if not name:
        return ""
    n = name.replace("دکتر", "").replace("دكتر", "").strip()
    n = re.sub(r'[^\u0600-\u06FF\s]', '', n)   # فقط حروف فارسی
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def merge_doctors(doctors: list, specialty_fa: str) -> list:
    """اسم‌های تکراری رو ادغام کن."""
    by_key = {}

    for d in doctors:
        raw_name = d.get("name_fa", "")
        key = normalize_name(raw_name)
        if not key or len(key) < 3:
            continue

        if key not in by_key:
            by_key[key] = {
                "name_fa": raw_name,
                "specialty_fa": specialty_fa,
                "sources": [d.get("source", "")],
                "status": "active"
            }
        else:
            src = d.get("source", "")
            if src and src not in by_key[key]["sources"]:
                by_key[key]["sources"].append(src)

    # شماره‌گذاری id
    result = []
    for i, (_, d) in enumerate(by_key.items(), 1):
        d["id"] = "doc_" + str(i).zfill(3)
        result.append(d)
    return result


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("═" * 60)
    print("  Shiraz Medical — Doctor Collector")
    print(f"  Total specialties: {len(SPECIALTIES)}")
    print("═" * 60)

    stats = {}
    errors = []

    for i, row in enumerate(SPECIALTIES, 1):
        print(f"\n[{i}/{len(SPECIALTIES)}]")
        try:
            count = process_specialty(row)
            stats[row[0]] = count
        except Exception as e:
            print(f"  ❌ خطا در {row[0]}: {e}")
            errors.append((row[0], str(e)))
            # فایل خالی بساز
            out_path = os.path.join(DOCTORS_DIR, row[0])
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            stats[row[0]] = 0

    # خلاصه
    print("\n" + "═" * 60)
    print("  خلاصه نهایی")
    print("═" * 60)
    total = sum(stats.values())
    for fname, cnt in stats.items():
        marker = "✅" if cnt > 0 else "⚠️"
        print(f"  {marker} {fname:25s} {cnt:3d} پزشک")
    print(f"\n  📊 مجموع: {total} پزشک در {len(stats)} تخصص")

    if errors:
        print(f"\n  ⚠️ {len(errors)} خطا:")
        for f, e in errors:
            print(f"     - {f}: {e}")

    print("\n✅ کار تمام شد. فایل‌های JSON توی data/doctors/ هستن.")


if __name__ == "__main__":
    main()