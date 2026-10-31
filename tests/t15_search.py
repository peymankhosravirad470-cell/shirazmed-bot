# -*- coding: utf-8 -*-
"""T15 — جست‌وجوی هوشمند جامع (مأموریت مکمل — بخش ۱ و ۵)

پوشش الزامات دستور محصول:
- جست‌وجوی فارسی، عربی و انگلیسی
- جست‌وجوی عبارت ناقص و غلط املایی (فارسی/انگلیسی)
- نتایج دسته‌بندی‌شده + پرش به نتیجه (کارت جزئیات)
- جست‌وجوی اسامی پزشکان و تخصص‌ها
- نتیجه‌ندادن کوئری‌های بی‌معنی (ضدنویز)
- یکپارچگی منو: دکمهٔ جست‌وجو در منوی اصلی + مسیر متن آزاد + ریست با ناوبری
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_rows, make_cb_update, make_start_update, make_text_update, process,
)

from app.services import search_engine as se  # noqa: E402


async def main() -> int:
    r = Result()
    app = await build_app()
    uid = 1501

    # ── ۱) موتور جست‌وجو — سه‌زبانه ──
    r.check("جست‌وجوی فارسی «قلب» → تخصص قلب", any("قلب" in x["title"] for g in se.search("قلب") for x in g["results"]))
    r.check("جست‌وجوی انگلیسی «hospital» → بیمارستان", any("hospital" in (g["id"]) for g in se.search("hospital")) or any("بیمارستان" in x["title"] for g in se.search("hospital") for x in g["results"]))
    r.check("جست‌وجوی عربی «فندق» → هتل", any(g["id"] in ("hotels", "motels") for g in se.search("فندق")))

    # ── ۲) غلط املایی و عبارت ناقص ──
    r.check("غلط املایی «قلو» → تخصص قلب", any("قلب" in x["title"] for g in se.search("قلو") for x in g["results"] if g["id"] == "doctors"))
    r.check("غلط انگلیسی «hotal» → هتل", any(g["id"] == "hotels" for g in se.search("hotal")))
    r.check("عبارت ناقص «کوسر» → بیمارستان کوثر", any("کوثر" in x["title"] for g in se.search("کوسر") for x in g["results"] if g["id"] == "hospitals"))
    r.check("غلط املایی عربی «المستشفي» (ي عربی) → بیمارستان", any(g["id"] == "hospitals" for g in se.search("المستشفي")))

    # ── ۳) اسامی پزشکان و تخصص‌ها ──
    r.check("نام پزشک «دکتر آرش» → حداقل یک پزشک", any("آرش" in x["title"] for g in se.search("دکتر آرش") for x in g["results"] if g["id"] == "doctors"))
    r.check("«دکتر قلبی» → تخصص قلب (subset fallback)", any(g["id"] == "doctors" for g in se.search("دکتر قلبی")))

    # ── ۴) ضدنویز: کوئری بی‌معنی نتیجه نمی‌دهد ──
    r.check("کوئری بی‌معنی «xyzzy qqq» → خالی", se.search("xyzzy qqq") == [])
    r.check("کوئری تک‌حرفی «a» → خالی", se.search("a") == [])
    r.check("کوئری خالی → خالی", se.search("   ") == [])

    # ── ۵) نتایج دسته‌بندی‌شده با callback معتبر ──
    groups = se.search("هتل")
    ok_cb = all(x["callback"].startswith(("srchgo_", "med_spec_", "start_", "non_")) for g in groups for x in g["results"])
    r.check("همهٔ نتایج callback معتبر دارند", ok_cb and bool(groups))
    labels = [g["label"] for g in se.search("هتل")]
    r.check("گروه‌ها برچسب فارسی دارند", all(bool(l) for l in labels), str(labels[:2]))

    # ── ۶) آیتم‌های یافت‌شده واقعاً در داده هستند (ضدجعل) ──
    item = se.get_item("hospitals", 0)
    r.check("get_item آیتم واقعی برمی‌گرداند", isinstance(item, dict) and bool(item.get("name_fa")))

    # ── ۷) یکپارچگی ربات: منو → جست‌وجو → متن → نتیجه ──
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))
    REC.reset()
    await process(make_cb_update(uid, "search"))
    texts = REC.sent_texts()
    r.check("دکمهٔ جست‌وجو در منو → پیام راهنما", any("جست‌وجو" in t for t in texts), texts[-1][:40] if texts else "NO")
    kb = kb_rows(REC.keyboards()[-1])
    r.check("صفحهٔ جست‌وجو دکمهٔ بازگشت دارد", any(cb == "back_main" for row in kb for _, cb in row))

    REC.reset()
    await process(make_text_update(uid, "کوثر"))
    texts = REC.sent_texts()
    r.check("متن «کوثر» → نتیجهٔ دسته‌بندی‌شده", any("کوثر" in t for t in texts), texts[-1][:60] if texts else "NO")
    kb = kb_rows(REC.keyboards()[-1])
    srchgo = [cb for row in kb for _, cb in row if cb.startswith("srchgo_")]
    r.check("دکمهٔ نتیجه با srchgo ارائه شده", bool(srchgo), str(srchgo[:3]))

    REC.reset()
    await process(make_cb_update(uid, srchgo[0]))
    texts = REC.sent_texts()
    r.check("کارت جزئیات نتیجه باز می‌شود", any("کوثر" in t for t in texts), texts[-1][:60] if texts else "NO")

    # ── ۸) نتیجهٔ خالی → پیام صادقانه ──
    REC.reset()
    await process(make_text_update(uid, "xyzzy qqq"))
    texts = REC.sent_texts()
    r.check("نتیجهٔ خالی → پیام صادقانه", any("نتیجه‌ای پیدا نشد" in t for t in texts), texts[-1][:50] if texts else "NO")

    # ── ۹) ریست پرچم با ناوبری منو (الگوی امنیتی) ──
    await process(make_cb_update(uid, "back_main"))
    await process(make_text_update(uid, "کوثر"))
    # بعد از back_main پرچم پاک شده؛ متن باید به مسیر دیگر برود (نه جست‌وجو)
    texts_after = REC.sent_texts()
    r.check("پرچم جست‌وجو با ناوبری پاک می‌شود", not any("نتایج جست‌وجوی" in t for t in texts_after))

    # ── ۱۰) جست‌وجو در زبان‌های دیگر ──
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "lang_en"))
    REC.reset()
    await process(make_cb_update(uid, "search"))
    texts = REC.sent_texts()
    r.check("صفحهٔ جست‌وجو به انگلیسی", any("Smart Search" in t for t in texts))
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "lang_ar"))
    REC.reset()
    await process(make_cb_update(uid, "search"))
    texts = REC.sent_texts()
    r.check("صفحهٔ جست‌وجو به عربی", any("البحث الذكي" in t for t in texts))

    # ── ۱۱) دکمهٔ «جست‌وجوی جدید» (srchback) ──
    REC.reset()
    await process(make_cb_update(uid, "srchback"))
    texts = REC.sent_texts()
    r.check("srchback → پیام راهنمای جست‌وجو", any("البحث" in t or "جست‌وجو" in t for t in texts))

    print()
    return r.finish("T15 جست‌وجوی هوشمند")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
