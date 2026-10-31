# -*- coding: utf-8 -*-
"""T18 — ساختار و یکپارچگی اپلیکیشن Flutter (mobile/)

الزام دستور: اپ Flutter مستقل در پوشهٔ mobile، سه‌زبانه، RTL، بدون دست‌زدن
به فایل‌های ربات/بک‌اند، بدون Deploy.
این سوت ساختار را تأیید می‌کند و هماهنگی دادهٔ اپ با دادهٔ ربات را
(تک‌منبع حقیقت) راستی‌آزمایی می‌کند:
- ۱۸ علامت مشاور سلامت = همان ids و سطوح ماژول پایتون
- شماره‌های اورژانس = همان مقادیر EMERGENCY_NUMBERS
- ایندکس جست‌وجو = همان دسته‌های search_engine.JSON_CATS
- سه‌زبانه بودن l10n و RTL و اجرای استاندارد flutter
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import Result  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, "mobile")


def main() -> int:
    r = Result()

    # ── ۱) فایل‌های پایه ──
    for f in ("pubspec.yaml", "analysis_options.yaml", ".gitignore", "README.md"):
        r.check(f"mobile/{f} وجود دارد", os.path.isfile(os.path.join(MOBILE, f)))
    pubspec = open(os.path.join(MOBILE, "pubspec.yaml"), encoding="utf-8").read()
    r.check("نام پروژه shiraz_medical", "name: shiraz_medical" in pubspec)
    r.check("assets سه‌گانه در pubspec ثبت شده", all(
        f"assets/data/{x}" in pubspec for x in ("symptoms.json", "emergency_numbers.json", "search_index.json")))
    r.check("url_launcher (تماس اورژانس) در وابستگی‌ها", "url_launcher" in pubspec)

    # ── ۲) ساختار lib ──
    dart_files = [
        "lib/main.dart", "lib/app.dart",
        "lib/core/l10n/app_localizations.dart", "lib/core/theme/app_theme.dart",
        "lib/models/models.dart", "lib/services/data_repository.dart",
        "lib/services/search_service.dart", "lib/screens/home_screen.dart",
        "lib/screens/search_screen.dart", "lib/screens/advisor/advisor_screen.dart",
        "lib/screens/advisor/triage_flow.dart",
    ]
    for f in dart_files:
        r.check(f"mobile/{f} وجود دارد", os.path.isfile(os.path.join(MOBILE, f)))

    # ── ۳) سه‌زبانه + RTL ──
    l10n = open(os.path.join(MOBILE, "lib/core/l10n/app_localizations.dart"), encoding="utf-8").read()
    r.check("l10n هر سه زبان را تعریف می‌کند", all(k in l10n for k in ("AppLanguage.fa", "AppLanguage.ar", "AppLanguage.en")))
    r.check("RTL برای فارسی/عربی", "isRtl" in l10n)
    app_dart = open(os.path.join(MOBILE, "lib/app.dart"), encoding="utf-8").read()
    r.check("localizationsDelegates رسمی flutter_localizations", "flutter_localizations" in app_dart and "GlobalMaterialLocalizations" in app_dart)

    # ── ۴) بدون جاافتادگی: کلیدهای l10n در هر سه زبان یکسان ──
    def keys_of(lang: str) -> set:
        start = l10n.find(f"AppLanguage.{lang}:")
        if start < 0:
            return set()
        nxt = l10n.find("AppLanguage.", start + 1)
        seg = l10n[start:nxt if nxt > 0 else len(l10n)]
        return set(re.findall(r"'([a-z_0-9]+)':", seg))
    fa_k, ar_k, en_k = keys_of("fa"), keys_of("ar"), keys_of("en")
    r.check("کلیدهای fa/ar/en هم‌اند", fa_k and fa_k == ar_k == en_k, f"fa={len(fa_k)} ar={len(ar_k)} en={len(en_k)}")

    # ── ۵) هماهنگی دادهٔ اپ با دادهٔ ربات (تک‌منبع حقیقت) ──
    sys.path.insert(0, ROOT)
    from app.services import health_advisor as ha
    from app.services import search_engine as se

    sym = json.load(open(os.path.join(MOBILE, "assets/data/symptoms.json"), encoding="utf-8"))["symptoms"]
    ids_py = [s["id"] for s in ha.SYMPTOMS]
    ids_app = [s["id"] for s in sym]
    r.check("۱۸ علامت اپ = ۱۸ علامت ربات (ترتیب و id)", ids_py == ids_app)
    sev_ok = all(
        s["severity"] == ha.get_symptom(s["id"])["severity"] and
        s["specialty"] == ha.specialty_for(s["id"])
        for s in sym
    )
    r.check("سطح بحرانی و تخصص ارجاع هر علامت مطابق ربات", sev_ok)

    em = json.load(open(os.path.join(MOBILE, "assets/data/emergency_numbers.json"), encoding="utf-8"))
    em_ok = all(
        em["countries"][cc]["ambulance"] == rec["ambulance"]
        for cc, rec in ha.EMERGENCY_NUMBERS.items()
    ) and em["fallback"] == ha.GLOBAL_FALLBACK_NUMBER and set(em["order"]) == set(ha.EMERGENCY_COUNTRY_ORDER)
    r.check("شماره‌های اورژانس اپ = ربات (۱۲ کشور + fallback)", em_ok)

    si = json.load(open(os.path.join(MOBILE, "assets/data/search_index.json"), encoding="utf-8"))["categories"]
    cat_ids_app = [c["id"] for c in si]
    cat_ids_py = [c["id"] for c in se.JSON_CATS]
    r.check("دسته‌های جست‌وجوی اپ = ربات", cat_ids_app == cat_ids_py, str(cat_ids_app))
    total_items = sum(len(c["items"]) for c in si)
    r.check("ایندکس جست‌وجو آیتم واقعی دارد (۱۰۰+)", total_items >= 100, str(total_items))

    # ── ۶) منطق تریاژ اپ = منطق ربات (بازخوانی کد Dart) ──
    dart = open(os.path.join(MOBILE, "lib/models/models.dart"), encoding="utf-8").read()
    r.check("evaluateTriage اپ همان قاعدهٔ ربات است (emergency>urgent>referral)",
            "rank['referral']! > rank[level]!" in dart.replace("rank[mapped]! > rank[level]!", "rank['referral']! > rank[level]!") or "rank[mapped]! > rank[level]!" in dart)

    # ── ۷) ایمنی: هیچ ادعای اعزام آمبولانس در متن‌های اپ ──
    honest = "نمی‌تواند آمبولانس اعزام کند" in l10n
    r.check("پیام صادقانهٔ اورژانس در اپ هست", honest)

    # ── ۸) بدون دست‌زدن به بک‌اند: mobile فقط فایل اپ دارد ──
    # pubspec.lock عمداً Track می‌شود (تکرارپذیری بیلد اپ)؛ build/ و
    # .dart_tool/ فقط آرتیفکت محلی pub get/test هستند و در گیت نیستند.
    allowed = {"pubspec.yaml", "pubspec.lock", "analysis_options.yaml", ".gitignore",
               "README.md", "assets", "lib", "test", "build", ".dart_tool"}
    actual = {x for x in os.listdir(MOBILE)}
    r.check("mobile پوشه‌های خارج از ساختار Flutter ندارد", actual <= allowed, str(actual - allowed))

    # ── ۹) تست‌های Dart پروژه ──
    for f in ("test/search_service_test.dart", "test/advisor_logic_test.dart"):
        r.check(f"mobile/{f} وجود دارد", os.path.isfile(os.path.join(MOBILE, f)))

    # ── ۱۰) بدون leftover placeholder ──
    junk = []
    for path in glob_paths(MOBILE, (".dart", ".yaml")):
        txt = open(path, encoding="utf-8").read()
        if re.search(r"FIXME|XXX|undefined|NaN", txt):
            junk.append(os.path.relpath(path, MOBILE))
    r.check("بدون leftover placeholder در کد Dart", not junk, str(junk))

    print()
    return r.finish("T18 ساختار اپ Flutter")


def glob_paths(root: str, exts: tuple) -> list:
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".dart_tool", "build")]
        for f in files:
            if f.endswith(exts):
                out.append(os.path.join(base, f))
    return out


if __name__ == "__main__":
    sys.exit(main())
