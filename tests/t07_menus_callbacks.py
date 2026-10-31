# -*- coding: utf-8 -*-
"""T07 — منوها و callbackها (بخش ۳.۱۴ و بخش I): هیچ دکمه‌ای بدون هندلر،
بخش‌های گردشگری/پیراپزشکی/سالمندان/شکایات/بیمه/راهنما/پزشکان/رزرو/بازگشت، سه‌زبانه."""
import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_rows, make_cb_update, make_start_update, make_text_update, process,
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
    # 🔧 CI-FIX: تعداد پزشکان هر شب با «Collect Doctors» تغییر می‌کند (مثلاً
    # پوست‌ومو 50→51)؛ پس زیررشتهٔ عددی هاردکد نشود — فقط الگوی «نام (تعداد)»:
    spec_btns = [l for l in labels if re.search(r"\(\d+\)\s*$", l)]
    r.check("منوی پزشکی ۳ تخصص فعال دارد", len(spec_btns) >= 3, str(labels))

    # ── مرور پزشکان: spec → لیست پزشکان واقعی ──
    REC.reset()
    await process(make_cb_update(uid, "med_spec_cardio_0"))
    texts = REC.sent_texts()
    r.check("مرور تخصص cardio → لیست پزشکان", any("پزشک" in t for t in texts), str(texts[-1][:60] if texts else "NO"))
    await process(make_cb_update(uid, "med_back"))
    r.check("med_back → بازگشت به تخصص‌ها", True)

    # ── بیمارستان‌ها (v49): هر مکان پیام مستقل + یک ردیف ۴ دکمه (گوگل/نشان/بلد/ویز) ──
    REC.reset()
    await process(make_cb_update(uid, "non_hospitals"))
    import json as _json
    from urllib.parse import quote as _q, quote_plus as _qp, unquote as _uq, unquote_plus as _uqp
    _DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    hospitals = _json.load(open(os.path.join(_DATA, "hospitals.json"), encoding="utf-8"))

    def nav_rows_of(markup):
        return [row for row in kb_rows(markup)
                if any(("گوگل" in t or "نشان" in t or "بلد" in t or "Waze" in t) for (t, u) in row)]

    hosp_msgs = [m for m in REC.sent_to(uid) if "🏥" in str(m.get("text") or "")]
    r.check("هر بیمارستان در پیام مستقل خودش (v49)", len(hosp_msgs) >= len(hospitals), f"{len(hosp_msgs)}/{len(hospitals)}")

    def verify_places(msgs, names, label):
        """برای هر پیام: دقیقاً یک ردیف ۴ دکمه، عنوان فقط آیکون+نام اپ،
        و مقصد هر ۴ لینک از «همان مکانِ همان پیام"."""
        problems = []
        for m in msgs:
            rows = nav_rows_of(m.get("reply_markup"))
            if len(rows) != 1 or len(rows[0]) != 4:
                problems.append(f"چیدمان {len(rows)}×{[len(x) for x in rows]}")
                continue
            titles = [t for (t, u) in rows[0]]
            apps = [any(a in t for a in ("گوگل", "Google")) for t in titles].count(True)
            if apps != 1 or not any("نشان" in t for t in titles) or not any("بلد" in t for t in titles) or not any("Waze" in t for t in titles):
                problems.append(f"عنوان‌ها: {titles}")
            # عنوان نباید نام مکان را تکرار کند
            text = str(m.get("text") or "")
            name_line = [ln for ln in text.splitlines() if ("🏥" in ln or "🏨" in ln or "🏛️" in ln or "📍" in ln)][0] if [ln for ln in text.splitlines() if ("🏥" in ln or "🏨" in ln or "🏛️" in ln or "📍" in ln)] else ""
            place_hint = name_line.replace("🏥", "").replace("🏨", "").replace("🏛️", "").replace("📍", "").strip()
            if place_hint and any(place_hint[:10] in t for t in titles):
                problems.append(f"نام مکان در عنوان دکمه: {titles[0]}")
        return problems

    probs = verify_places(hosp_msgs, [h.get("name_fa", "") for h in hospitals], "hospitals")
    r.check("دقیقاً یک ردیف ۴ دکمه + عنوان فقط نام اپ (بدون نام مکان)", not probs, "; ".join(probs[:3]))

    # مقصد هر ۴ لینک = همان بیمارستانِ همان پیام (نام در کوئری هر ۴ لینک)
    dest_bad = []
    for m in hosp_msgs:
        text = str(m.get("text") or "")
        name_line = [ln for ln in text.splitlines() if "🏥" in ln]
        hosp_name = name_line[0].replace("🏥", "").strip() if name_line else ""
        if not hosp_name:
            continue
        expected_q = f"{hosp_name} شیراز"
        for row in nav_rows_of(m.get("reply_markup")):
            if len(row) != 4:
                continue
            for (t, u) in row:
                uq = _uqp(u)  # هم %XX و هم + را به فاصله برمی‌گرداند
                if not (hosp_name in uq or expected_q in uq):
                    dest_bad.append(f"{hosp_name[:14]} ← {u[:55]}")
    r.check("مقصد هر ۴ دکمه همان بیمارستانِ همان پیام", not dest_bad, "; ".join(dest_bad[:3]))

    # فرمت استاندارد هر ۴ لینک
    fmt_bad = []
    for m in hosp_msgs:
        for row in nav_rows_of(m.get("reply_markup")):
            if len(row) != 4:
                continue
            ug, un, ub, uw = row[0][1], row[1][1], row[2][1], row[3][1]
            if not ug.startswith("https://www.google.com/maps/search/?api=1&query="): fmt_bad.append(ug[:45])
            if not (un.startswith("https://neshan.org/maps/search/") or un.startswith("https://neshan.org/maps/@")): fmt_bad.append(un[:45])
            if not (ub.startswith("https://balad.ir/search?query=") or ub.startswith("https://balad.ir/location?")): fmt_bad.append(ub[:45])
            if not (uw.startswith("https://waze.com/ul?q=") and uw.endswith("&navigate=yes")): fmt_bad.append(uw[:45])
    r.check("فرمت استاندارد هر ۴ لینک (گوگل/نشان/بلد/ویز)", not fmt_bad, str(fmt_bad[:3]))

    # ── هتل‌ها (تست پذیرش مأموریت): همان قواعد چهاراپ ──
    REC.reset()
    await process(make_cb_update(uid, "non_hotels"))
    hotel_msgs = [m for m in REC.sent_to(uid) if "🏛️" in str(m.get("text") or "")]
    r.check("هتل‌ها هم پیام مستقل با ۴ دکمه دارند", len(hotel_msgs) >= 5, str(len(hotel_msgs)))
    hprobs = verify_places(hotel_msgs, [], "hotels")
    r.check("هتل‌ها: چیدمان و عنوان درست", not hprobs, "; ".join(hprobs[:3]))

    # ── جاذبه گردشگری (تست پذیرش مأموریت): tour_city → leisure_city.json ──
    REC.reset()
    await process(make_cb_update(uid, "tour_city"))
    city_msgs = [m for m in REC.sent_to(uid) if "🏛️" in str(m.get("text") or "")]
    r.check("جاذبه‌های گردشگری پیام مستقل با ۴ دکمه دارند", len(city_msgs) >= 5, str(len(city_msgs)))
    cprobs = verify_places(city_msgs, [], "tour_city")
    r.check("جاذبه‌ها: چیدمان و عنوان درست", not cprobs, "; ".join(cprobs[:3]))

    # ── مراکز حمل‌ونقل (hubs) — قبلاً هرگز فرودگاه را نشان نمی‌داد (بخش G) ──
    REC.reset()
    await process(make_cb_update(uid, "hubs"))
    texts = REC.sent_texts()
    joined = " ".join(texts)
    r.check("فرودگاه شیراز نمایش داده می‌شود", "دستغیب" in joined or "فرودگاه" in joined, joined[:120])
    r.check("راه‌آهن شیراز نمایش داده می‌شود", "راه‌آهن" in joined)
    r.check("پایانه‌ها نمایش داده می‌شوند", "کرندیش" in joined or "امیرکبیر" in joined)
    hub_nav_rows = [row for kb in REC.keyboards() for row in kb_rows(kb) if len(row) == 4 and any("Waze" in t for (t, u) in row)]
    r.check("ردیف ۴ دکمه مسیریاب برای مراکز حمل‌ونقل", len(hub_nav_rows) >= 4, f"{len(hub_nav_rows)}")

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

    # ── سه‌زبانه: کل منو در عربی و انگلیسی (متن خوش‌آمد جدید v49) ──
    for lang_code, sample in (("lang_en", "Welcome to Shiraz Medical"), ("lang_ar", "أهلاً بك في شيراز ميديكال")):
        REC.reset()
        await process(make_cb_update(uid, "change_language"))
        await process(make_cb_update(uid, lang_code))
        texts = REC.sent_texts()
        r.check(f"زبان {lang_code} → خوش‌آمد به همان زبان", any(sample in t for t in texts), str(texts[-1][:60] if texts else "NO"))
        REC.reset()
        await process(make_cb_update(uid, "non_hospitals"))
        texts = REC.sent_texts()
        r.check(f"بخش بیمارستان‌ها در {lang_code} با برچسب {lang_code}", any(("Address" if lang_code == "lang_en" else "العنوان") in t for t in texts), str(texts[-1][:50] if texts else ""))

    # ── 🆕 v49: ثبت همراه بیمار — پیام نهایی باید دکمه بازگشت داشته باشد ──
    # (بازگشت به فارسی — بخش سه‌زبانه قبلی زبان را عربی کرده بود)
    REC.reset()
    await process(make_cb_update(uid, "change_language"))
    await process(make_cb_update(uid, "lang_fa"))
    REC.reset()
    await process(make_cb_update(uid, "start_companion"))
    await process(make_cb_update(uid, "comp_yes"))
    await process(make_text_update(uid, "علی رضایی"))
    await process(make_text_update(uid, "09123456789"))
    texts = REC.sent_texts()
    r.check("همراه بیمار: پیام موفقیت نمایش داده شد", any("ثبت شد" in t for t in texts), str(texts[-1][:60] if texts else "NO"))
    last_kb = REC.keyboards()[-1] if REC.keyboards() else None
    last_labels = [b[0] for row in kb_rows(last_kb) for b in row]
    r.check("همراه بیمار: پیام نهایی دکمه «بازگشت به منو» دارد", any("بازگشت به منو" in l for l in last_labels), str(last_labels))
    r.check("همراه بیمار: ثبت فقط یک‌بار (یک پیام موفقیت)", sum(1 for t in texts if "ثبت شد" in t) == 1, str([t[:40] for t in texts if "ثبت شد" in t]))
    # کلیک بازگشت → منوی اصلی
    REC.reset()
    await process(make_cb_update(uid, "back_main"))
    texts = REC.sent_texts()
    r.check("همراه بیمار: بازگشت → منوی اصلی", any("خوش آمدید" in t for t in texts), str(texts[-1][:50] if texts else "NO"))

    # ── 🆕 v49: نظرسنجی — مسیر لغو در مرحله «نوشتن علت» کار می‌کند ──
    REC.reset()
    await process(make_cb_update(uid, "start_survey"))
    await process(make_cb_update(uid, "survey_no"))
    kb = REC.keyboards()[-1] if REC.keyboards() else None
    labels = [b[1] for row in kb_rows(kb) for b in row]
    r.check("نظرسنجی: مرحله علت، دکمه لغو دارد (callback survey_cancel)", "survey_cancel" in labels, str(labels))
    await process(make_cb_update(uid, "survey_cancel"))
    texts = REC.sent_texts()
    last_kb = REC.keyboards()[-1] if REC.keyboards() else None
    last_labels = [b[0] for row in kb_rows(last_kb) for b in row]
    r.check("نظرسنجی: پیام لغو دکمه بازگشت دارد", any("بازگشت به منو" in l for l in last_labels), str(last_labels))

    return r.finish("T07 menus+callbacks")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
