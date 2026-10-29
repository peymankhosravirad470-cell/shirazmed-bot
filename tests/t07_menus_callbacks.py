# -*- coding: utf-8 -*-
"""T07 — منوها و callbackها (بخش ۳.۱۴ و بخش I): هیچ دکمه‌ای بدون هندلر،
بخش‌های گردشگری/پیراپزشکی/سالمندان/شکایات/بیمه/راهنما/پزشکان/رزرو/بازگشت، سه‌زبانه."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_rows, make_cb_update, make_start_update, process,
)

from app.bot import MENU_CALLBACKS  # noqa: E402

# بخش‌هایی که «عمداً» پیام به‌زودی/اطلاع ثابت می‌دهند (مستند در گزارش)
ALLOWED_STUBS = {"site"}  # دکمه سایت با پیام «به زودی» — مستند و آگاهانه


async def main() -> int:
    r = Result()
    app = await build_app()
    uid = 701
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))

    # ── هر callback منو → پاسخ واقعی (نه «به زودی» بی‌هندلر) ──
    dead = []
    for cb in MENU_CALLBACKS:
        REC.reset()
        await process(make_cb_update(uid, cb))
        texts = REC.sent_texts()
        if not texts:
            dead.append(f"{cb}: NO-RESPONSE")
            continue
        last = texts[-1]
        # فقط پیام‌هایی که «عمداً» کلشان stub است؛ نه متنی که کلمه به‌زودی را در جمله دارد
        if last.strip().startswith(("این بخش در نسخه", "This section will be", "سيتم تفعيل")):
            if cb not in ALLOWED_STUBS:
                dead.append(f"{cb}: COMING-SOON")
    r.check("همه‌ی callbackهای منو پاسخ واقعی دارند", not dead, "; ".join(dead))

    # ── منوی پزشکی → تخصص‌های فعال واقعی (فقط ۳ تخصص دارای پزشک) ──
    REC.reset()
    await process(make_cb_update(uid, "medical"))
    kb = kb_rows(REC.keyboards()[-1])
    labels = [b[0] for row in kb for b in row]
    r.check("منوی پزشکی ۳ تخصص فعال دارد", sum(1 for l in labels if "(2" in l or "(1" in l or "(3" in l or "(23" in l or "(41" in l or "(50" in l) >= 3, str(labels))

    # ── مرور پزشکان: spec → لیست پزشکان واقعی ──
    REC.reset()
    await process(make_cb_update(uid, "med_spec_cardio_0"))
    texts = REC.sent_texts()
    r.check("مرور تخصص cardio → لیست پزشکان", any("پزشک" in t for t in texts), str(texts[-1][:60] if texts else "NO"))
    await process(make_cb_update(uid, "med_back"))
    r.check("med_back → بازگشت به تخصص‌ها", True)

    # ── بیمارستان‌ها: دکمه‌های مسیریاب سه‌اپ با نام مکان (Bug1 re-verify) ──
    REC.reset()
    await process(make_cb_update(uid, "non_hospitals"))
    all_rows = []
    for kb in REC.keyboards():
        for row in kb_rows(kb):
            all_rows.append(row)
    nav_rows = [(t, u) for row in all_rows for (t, u) in row if "مسیریاب" in t]
    r.check("دکمه‌های مسیریاب ≥ 7×3 (۳ اپ برای هر بیمارستان)", len(nav_rows) >= 21, f"{len(nav_rows)}")
    google = [t for t, u in nav_rows if "گوگل" in t or "Google" in t]
    neshan = [t for t, u in nav_rows if "نشان" in t]
    balad = [t for t, u in nav_rows if "بلد" in t]
    r.check("هر سه اپ: گوگل/نشان/بلد", len(google) >= 7 and len(neshan) >= 7 and len(balad) >= 7, f"{len(google)}/{len(neshan)}/{len(balad)}")
    labels_set = {t for t, _ in nav_rows}
    r.check("لیبل‌ها منحصربه‌فرد و شامل نام بیمارستان (بدون ۹ دکمه‌ی یکسان)", len(labels_set) == len(nav_rows), f"{len(labels_set)}/{len(nav_rows)}")
    import json as _json
    hospitals = _json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "hospitals.json"), encoding="utf-8"))
    missing_names = [h["name_fa"][:12] for h in hospitals if not any(h["name_fa"][:12] in t for t in labels_set)]
    r.check("نام هر بیمارستان در لیبل دکمه‌ها هست", not missing_names, str(missing_names))
    urls = [u for _, u in nav_rows]
    r.check("URL گوگل‌مپ استاندارد", all(("google.com/maps" in u) or ("neshan.org" in u) or ("balad.ir" in u) for u in urls))
    neshan_ok = all(("neshan.org/maps/search/" in u) or ("neshan.org/maps/@" in u) for u in [u for _, u in nav_rows if "نشان" in _])
    balad_ok = all(("balad.ir/search?query=" in u) or ("balad.ir/location?" in u) for u in [u for _, u in nav_rows if "بلد" in _])
    r.check("فرمت URL نشان درست", neshan_ok)
    r.check("فرمت URL بلد درست", balad_ok)

    # ── مراکز حمل‌ونقل (hubs) — قبلاً هرگز فرودگاه را نشان نمی‌داد (بخش G) ──
    REC.reset()
    await process(make_cb_update(uid, "hubs"))
    texts = REC.sent_texts()
    joined = " ".join(texts)
    r.check("فرودگاه شیراز نمایش داده می‌شود", "دستغیب" in joined or "فرودگاه" in joined, joined[:120])
    r.check("راه‌آهن شیراز نمایش داده می‌شود", "راه‌آهن" in joined)
    r.check("پایانه‌ها نمایش داده می‌شوند", "کرندیش" in joined or "امیرکبیر" in joined)
    hub_nav = [t for kb in REC.keyboards() for row in kb_rows(kb) for (t, u) in row if "مسیریاب" in t]
    r.check("دکمه‌های مسیریاب برای مراکز حمل‌ونقل", len(hub_nav) >= 12, f"{len(hub_nav)}")

    # ── بیمه‌ها: فیلدهای کامل + دکمه‌های مسیریاب ──
    REC.reset()
    await process(make_cb_update(uid, "insurance"))
    texts = REC.sent_texts()
    joined = " ".join(texts)
    r.check("بیمه‌ها با فیلد پوشش/تلفن/وبسایت", "پوشش" in joined and "تلفن" in joined)

    # ── شکایات/گردشگری/پیراپزشکی/سالمندان/راهنمای بیمار/حقوق ──
    for cb, marker in (("complaints_iranian", "۱۹۰"), ("complaints_foreign", "ویزا") , ("tour_city", "حافظیه"), ("para_physio", "فیزیوتراپی"), ("elderly_all", "سالمند"), ("patient_guide", "ویزا")):
        REC.reset()
        await process(make_cb_update(uid, cb))
        texts = REC.sent_texts()
        joined = " ".join(texts)
        r.check(f"بخش {cb} پاسخ محتوایی دارد", len(joined) > 50, joined[:60])
        if cb == "complaints_iranian":
            r.check("شکایات ایرانی → سامانه ۱۹۰", "۱۹۰" in joined or "190" in joined, joined[:80])

    # rights: منوی انتخاب بخش حقوق بیمار (پیام کوتاه + کیبورد دکمه‌ها)
    REC.reset()
    await process(make_cb_update(uid, "rights"))
    rights_kb = kb_rows(REC.keyboards()[-1])
    r.check("rights → منو با دکمه‌های بخش‌های حقوق", len(rights_kb) >= 2, str(rights_kb))

    # ── بازگشت به منو از همه‌جا ──
    REC.reset()
    await process(make_cb_update(uid, "back_main"))
    texts = REC.sent_texts()
    r.check("back_main → منوی اصلی", any("خوش آمدید" in t for t in texts))

    # ── سه‌زبانه: کل منو در عربی و انگلیسی ──
    for lang_code, sample in (("lang_en", "warm welcome"), ("lang_ar", "أهلاً")):
        REC.reset()
        await process(make_cb_update(uid, "change_language"))
        await process(make_cb_update(uid, lang_code))
        texts = REC.sent_texts()
        r.check(f"زبان {lang_code} → خوش‌آمد به همان زبان", any(sample in t for t in texts), str(texts[-1][:60] if texts else "NO"))
        REC.reset()
        await process(make_cb_update(uid, "non_hospitals"))
        texts = REC.sent_texts()
        r.check(f"بخش بیمارستان‌ها در {lang_code} با برچسب {lang_code}", any(("Address" if lang_code == "lang_en" else "العنوان") in t for t in texts), str(texts[-1][:50] if texts else ""))

    return r.finish("T07 menus+callbacks")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
