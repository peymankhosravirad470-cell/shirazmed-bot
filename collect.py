# -*- coding: utf-8 -*-

import requests
import json
import os
import time

# مسیر ذخیره
DATA_DIR = "data"
DOCTORS_DIR = os.path.join(DATA_DIR, "doctors")
os.makedirs(DOCTORS_DIR, exist_ok=True)

# سایت‌ها و آدرس‌های جمع‌آوری برای قلب شیراز
sources = [
    "https://salamati24.com/doctors/cardiology/shiraz",
    "https://exiryab.com/doctors/cardiology/shiraz",
    "https://nobat.ir/doctors/city/shiraz/specialty/cardiology",
]

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

os.makedirs("cache", exist_ok=True)

for i, url in enumerate(sources, 1):
    print(f"\n[{i}] دانلود از {url}")
    try:
        r = requests.get(url, headers=headers, timeout=25)
        print(f"    وضعیت: {r.status_code}")
        print(f"    طول محتوا: {len(r.text)} کاراکتر")

        # ذخیره برای بررسی
        domain = url.split("//")[1].split("/")[0].replace(".", "_")
        fname = f"cache/{domain}_cardio.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"    ذخیره شد: {fname}")
    except Exception as e:
        print(f"    خطا: {e}")
    time.sleep(2)

print("\n✅ تمام. فایل‌های HTML توی پوشه cache/ هستن.")
print("برو توشون دنبال کلمه 'دکتر' بگرد و نتیجه رو بگو.")