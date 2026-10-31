# -*- coding: utf-8 -*-
"""صادرکردن دادهٔ مشترک ربات ↔ اپ Flutter به assets/data (تک‌منبع حقیقت).

این اسکریپت ساختار ۱۸ علامت مشاور سلامت، شماره‌های اورژانس کشورها و
دسته‌بندی منو را از ماژول‌های پایتون می‌خواند و در mobile/assets/data
می‌نویسد تا محتوای اپلیکیشن دقیقاً با ربات هماهنگ بماند.
اجرا: python3 scripts/export_mobile_assets.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "mobile", "assets", "data")
os.makedirs(OUT, exist_ok=True)


def main() -> None:
    from app.services import health_advisor as ha

    symptoms = []
    for s in ha.SYMPTOMS:
        symptoms.append({
            "id": s["id"],
            "icon": s["icon"],
            "severity": s["severity"],
            "title": s["title"],
            "brief": s["brief"],
            "redFlags": [
                {"fa": f.get("fa", ""), "en": f.get("en", ""), "ar": f.get("ar", "")}
                for f in s.get("red_flags", [])
            ],
            "questions": [
                {
                    "key": q["key"],
                    "text": q["text"],
                    "yes": q["yes"],
                    "no": q.get("no", "referral"),
                }
                for q in s.get("questions", [])
            ],
            "specialty": ha.specialty_for(s["id"]),
        })
    with open(os.path.join(OUT, "symptoms.json"), "w", encoding="utf-8") as fh:
        json.dump({"symptoms": symptoms}, fh, ensure_ascii=False, indent=2)

    emergency = {
        "order": ha.EMERGENCY_COUNTRY_ORDER,
        "countries": {
            cc: {
                "label": rec["label"],
                "ambulance": rec["ambulance"],
                **({"alt": rec["alt"]} if rec.get("alt") else {}),
            }
            for cc, rec in ha.EMERGENCY_NUMBERS.items()
        },
        "fallback": ha.GLOBAL_FALLBACK_NUMBER,
    }
    with open(os.path.join(OUT, "emergency_numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(emergency, fh, ensure_ascii=False, indent=2)

    # ── ایندکس جست‌وجوی اپ (دسته‌های اصلی + آیتم‌ها با نام سه‌زبانه) ──
    from app.services import search_engine as se
    cats = []
    for cat in se.JSON_CATS:
        items = []
        for idx, item in se._iter_cat_items(cat):
            items.append({
                "i": idx,
                "n": {
                    "fa": se._display_name(item),
                    "en": _name_lang(item, "en"),
                    "ar": _name_lang(item, "ar"),
                },
                "c": se.normalize(se.corpus_text(item))[:600],
                "s": se._subtitle(item),
            })
        cats.append({"id": cat["id"], "icon": cat["icon"], "label": cat["label"], "items": items})
    with open(os.path.join(OUT, "search_index.json"), "w", encoding="utf-8") as fh:
        json.dump({"categories": cats}, fh, ensure_ascii=False, indent=2)

    print("exported:", os.listdir(OUT))


def _name_lang(item: dict, lang: str) -> str:
    for base in ("name", "title"):
        obj = item.get(base)
        if isinstance(obj, dict) and obj.get(lang):
            return str(obj[lang])
        for suffix in (f"_{lang}", ""):
            v = item.get(f"{base}{suffix}")
            if isinstance(v, str) and v:
                return v
    return ""


if __name__ == "__main__":
    main()
