def fetch(url, cache_name):
    cache_path = os.path.join(CACHE_DIR, cache_name)
    if os.path.isfile(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 1000:
            print(f"      from cache: {cache_name} ({len(content)} bytes)")
            return content
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        print(f"      HTTP {r.status_code}, len={len(r.text)}")
        # همیشه ذخیره کن، حتی روی خطا - برای دیباگ
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


SPECIALTIES = [
    ("cardio.json", "قلب و عروق", "cardiologist"),
    ("derma.json",  "پوست و مو",  "dermatologist"),
    ("dental.json", "دندانپزشکی", "dentist"),
]

def process_specialty(row):
    out_file, name_fa, slug = row
    all_names = set()

    # doctoreto.com
    url1 = f"https://doctoreto.com/doctors/speciality/{slug}/city/shiraz"
    html1 = fetch(url1, f"doctoreto_{slug}.html")
    all_names.update(extract_names(html1))

    # darmankade.com
    url2 = f"https://www.darmankade.com/b/Shiraz/{slug}"
    html2 = fetch(url2, f"darmankade_{slug}.html")
    all_names.update(extract_names(html2))
    ...