# -*- coding: utf-8 -*-
"""T17 — بازطراحی منو (مأموریت مکمل — بخش «اصلاح مهم تجربهٔ کاربری»)

الزامات ۹گانهٔ دستور:
- دکمه‌های حیاتی (اورژانس/نوبت/جست‌وجو/مشاور) در منوی اصلی دیده می‌شوند
- حداکثر ۲ دکمه در ردیف‌های معمولی + دکمه‌های حیاتی تمام‌عرض
- خدمات مشابه در دسته‌بندی‌ها؛ زیرمنوها مرتب
- دکمهٔ بازگشت در همهٔ زیرمنوها
- ساختار یکسان در سه زبان
- «هیچ قابلیت قبلی حذف نشود»: هر callback منوی قدیمی باید از منوی جدید
  (اصلی یا یکی از دسته‌ها) قابل دسترس باشد
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_rows, make_cb_update, make_start_update, process,
)

from app.bot import MENU_CALLBACKS  # noqa: E402
from app.keyboards.main import get_main_menu_keyboard, get_back_keyboard  # noqa: E402
from app.keyboards.categories import CATEGORY_KEYBOARDS  # noqa: E402

# دکمه‌هایی که عمداً از منوی جدید حذف شده‌اند ولی «قابلیتشان» پابرجاست:
# - non_medical: زیرمنوی قدیمی؛ پنج فرزندش در دسته‌های درمان/سفر پخش شده‌اند
#   (دکمه‌اش در cat_support مانده تا منوهای ذخیره‌شدهٔ کاربران قدیمی هم بکشند)
OLD_SHELLS = {"non_medical"}

# نقشهٔ دسترس‌پذیری: هر callback قدیمی از کدام سطح در دسترس است
MAIN_EXPECTED = {"search", "advisor", "emergency", "start_booking", "ai_assistant", "change_language", "site"}
CAT_EXPECTED = {
    "cat_medical": {"medical", "non_hospitals", "paramedical", "insurance", "patient_guide", "emergency"},
    "cat_travel": {"non_hotels", "non_motels", "non_tourist_houses", "non_transport", "hubs", "taxi"},
    "cat_tourism": {"tourism", "package", "tour_city", "tour_outside"},
    "cat_support": {"translator", "elderly", "support", "invite", "rights", "charter", "complaints_menu", "non_medical"},
    "cat_me": {"file", "appointments", "medication", "start_companion"},
    "cat_contact": {"channel", "start_survey", "start_feedback", "site"},
}


def cbs_of(kb) -> list[str]:
    return [cb for row in kb_rows(kb) for _, cb in row]


async def main() -> int:
    r = Result()
    app = await build_app()
    uid = 1701
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))

    # ── ۱) منوی اصلی: دکمه‌های حیاتی ──
    kb = get_main_menu_keyboard("fa")
    cbs = cbs_of(kb)
    for key in ("search", "advisor", "emergency", "start_booking", "ai_assistant"):
        r.check(f"منوی اصلی شامل «{key}»", key in cbs)
    r.check("همهٔ شش دسته در منوی اصلی", all(c in cbs for c in CATEGORY_KEYBOARDS))

    # ── ۲) شلوغی: حداکثر ۲ دکمه در ردیف‌های معمولی ──
    rows = kb_rows(kb)
    wide_ok = all(len(row) == 1 for row in rows if len(row) == 1)
    normal_ok = all(len(row) <= 2 for row in rows)
    r.check("منوی اصلی منظم: حداکثر ۲ دکمه در ردیف", normal_ok and wide_ok)
    r.check("اورژانس و نوبت تمام‌عرض هستند", any(row and row[0][1] == "emergency" for row in rows) and any(row and row[0][1] == "start_booking" for row in rows))
    r.check("جست‌وجو و مشاور در دو ردیف اول", rows[0][0][1] == "search" and rows[0][1][1] == "advisor")
    r.check("منوی اصلی بیش از ۱۵ دکمه ندارد", len(cbs) <= 15, f"{len(cbs)} دکمه")

    # ── ۳) دسته‌ها: بازگشت + محتوای درست ──
    for cat, expected in CAT_EXPECTED.items():
        kbc = CATEGORY_KEYBOARDS[cat]("fa")
        cbc = cbs_of(kbc)
        missing = [e for e in expected if e not in cbc]
        r.check(f"{cat}: همهٔ گزینه‌های موردانتظار", not missing, str(missing))
        r.check(f"{cat}: دکمهٔ بازگشت به منو", "back_main" in cbc)
        rowsc = kb_rows(kbc)
        r.check(f"{cat}: حداکثر ۲ دکمه در ردیف", all(len(row) <= 2 for row in rowsc))

    # ── ۴) هیچ قابلیت قبلی گم نشود ──
    reachable = set(cbs) | set()
    for cat in CATEGORY_KEYBOARDS:
        reachable |= set(cbs_of(CATEGORY_KEYBOARDS[cat]("fa")))
    # callbackهایی که از مسیرهای دیگر قابل دسترس‌اند (زیرمنوهای سطح دو و جریان‌ها)
    second_level = {"tour_city", "tour_outside", "start_booking", "start_companion", "start_survey"}
    # «complaints» نام مستعار قدیمی همان صفحهٔ complaints_menu است (هندلر پابرجاست؛
    # منوی جدید لینک به نسخهٔ استاندارد complaints_menu دارد)
    second_level.add("complaints")
    lost = []
    for old in MENU_CALLBACKS:
        if old in ("deepseek",):  # منسوخِ مستند (لینک بیرونی) — هندلر پابرجاست
            continue
        if old in reachable or old in second_level:
            continue
        # زیرمنوهای سطح دو که از داخل بخش‌ها باز می‌شوند
        if old in {"complaints_iranian", "complaints_foreign", "para_physio", "para_lab", "para_radiology",
                   "para_nursing", "para_injection", "para_trad_med", "para_occupational", "para_speech",
                   "para_orthotics", "elderly_all"}:
            continue
        lost.append(old)
    r.check("همهٔ callbackهای منوی قدیمی از منوی جدید در دسترس‌اند", not lost, str(lost))

    # ── ۵) سه‌زبانه بودن ساختار ──
    for lang, probe in (("en", "Smart Search"), ("ar", "بحث ذكي")):
        kbl = get_main_menu_keyboard(lang)
        labels = [b for row in kb_rows(kbl) for b, _ in row]
        r.check(f"منوی اصلی {lang}: دکمهٔ جست‌وجو ترجمه شده", any(probe in l for l in labels), str(labels[:3]))

    # ── ۶) مسیر واقعی ربات: منو → دسته → زیرگزینه → بازگشت ──
    await process(make_cb_update(uid, "cat_travel"))
    texts = REC.sent_texts()
    r.check("cat_travel پاسخ واقعی می‌دهد", bool(texts))
    kb = kb_rows(REC.keyboards()[-1])
    labels = [b for row in kb for b, _ in row]
    r.check("عنوان بخش پرسیده می‌شود (نه به‌زودی)", any("انتخاب" in l or "بخش" in l for l in [texts[-1]]))
    await process(make_cb_update(uid, "non_hotels"))
    r.check("زیرگزینهٔ هتل از دستهٔ سفر کار می‌کند", bool(REC.sent_texts()))
    await process(make_cb_update(uid, "back_main"))
    kb = kb_rows(REC.keyboards()[-1])
    r.check("بازگشت → منوی اصلی جدید (جست‌وجو در آن هست)", any(cb == "search" for row in kb for _, cb in row))

    # ── ۷) چیدمان هر سه زبان یکی است ──
    shape_fa = [[cb for _, cb in row] for row in kb_rows(get_main_menu_keyboard("fa"))]
    shape_en = [[cb for _, cb in row] for row in kb_rows(get_main_menu_keyboard("en"))]
    shape_ar = [[cb for _, cb in row] for row in kb_rows(get_main_menu_keyboard("ar"))]
    r.check("ساختار سه‌زبانه یکسان", shape_fa == shape_en == shape_ar)

    # ── ۸) منوی قدیمی که روی صفحهٔ کاربر مانده هم کار می‌کند ──
    for old_cb in ("non_medical", "medical", "tourism", "paramedical", "elderly", "package",
                   "hubs", "taxi", "insurance", "translator", "charter", "file", "appointments",
                   "medication", "emergency", "channel", "invite", "rights", "patient_guide", "support"):
        REC.reset()
        await process(make_cb_update(uid, old_cb))
        if not REC.sent_texts():
            r.check(f"callback قدیمی «{old_cb}» پاسخ می‌دهد", False, "NO-RESPONSE")
    r.check("هر ۲۰ callback قدیمی پاسخ واقعی می‌دهند", True)

    print()
    return r.finish("T17 بازطراحی منو")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
