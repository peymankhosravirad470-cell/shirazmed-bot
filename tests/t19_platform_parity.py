# -*- coding: utf-8 -*-
"""T19 — پاریتی Bale↔Telegram + الزامات ۸گانهٔ بازطراحی منو (مأموریت تکمیلی)

الزامات دستور:
۱. منوی اصلی خلوت، منظم و دسته‌بندی‌شده        ۲. جست‌وجو همیشه در دسترس
۳. «مشاور سلامت» در منوی اصلی                 ۴. خدمات مشابه در زیرمنوهای مشخص
۵. بازگشت/منوی اصلی در همهٔ مراحل             ۶. هیچ قابلیتی حذف نشده
۷. قابل استفاده در fa/ar/en                   ۸. ساختار منوها در Bale و Telegram هماهنگ

روش پاریتی (الزام ۸): هر دو Application واقعی (بله + تلگرام با پل جعلی)
ساخته و /start روی هر دو اجرا می‌شود؛ سپس کیبورد ثبت‌شده در پاسخ API دو
پلتفرم (برچسب‌ها + callbackها) دکمه‌به‌دکمه مقایسه می‌شود. علاوه بر آن
ثبت‌نام هندلرها و الگوهای callback دو پلتفرم نیز برابر اثبات می‌شود.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⚠️ قبل از هر import ماژول‌های پروژه (تا config.settings توکن تلگرام را ببیند)
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "TEST:TELE_FAKE_TOKEN_FOR_TESTS")
os.environ.setdefault("TELEGRAM_BRIDGE_URL", "https://bridge.example/bot")
os.environ.setdefault("TELEGRAM_BRIDGE_FILE_URL", "https://bridge.example/file/bot")

from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_rows, make_cb_update, make_start_update, process,
)

from app.bot import MENU_CALLBACKS, MENU_PATTERN, build_application  # noqa: E402
from app.keyboards.categories import CATEGORY_KEYBOARDS  # noqa: E402
from app.keyboards.main import (  # noqa: E402
    get_back_keyboard, get_language_keyboard, get_main_menu_keyboard,
)

LANGS = ("fa", "ar", "en")
MAIN_EXPECTED = {"search", "advisor", "emergency", "start_booking",
                 "ai_assistant", "btn_change_lang", "btn_site"}
WIDE = ("emergency", "start_booking", "btn_site")
CAT_EXPECTED = {
    "cat_medical": {"medical", "non_hospitals", "paramedical", "insurance", "patient_guide", "emergency"},
    "cat_travel": {"non_hotels", "non_motels", "non_tourist_houses", "non_transport", "hubs", "taxi"},
    "cat_tourism": {"tourism", "package", "tour_city", "tour_outside"},
    "cat_support": {"translator", "elderly", "support", "invite", "rights", "charter", "complaints_menu", "non_medical"},
    "cat_me": {"file", "appointments", "medication", "start_companion"},
    "cat_contact": {"channel", "start_survey", "start_feedback", "site"},
}
LEGACY_SERVICES = (
    "medical", "non_medical", "non_hospitals", "non_hotels", "non_motels",
    "non_tourist_houses", "non_transport", "tourism", "tour_city", "tour_outside",
    "paramedical", "para_physio", "para_lab", "para_radiology", "para_nursing",
    "para_injection", "para_trad_med", "para_occupational", "para_speech",
    "para_orthotics", "elderly", "elderly_all", "hubs", "insurance", "package",
    "taxi", "translator", "charter", "deepseek", "file", "appointments",
    "medication", "emergency", "channel", "invite", "rights", "patient_guide",
    "start_booking", "start_companion", "start_survey",
)


def cbs_of(kb) -> list[str]:
    return [cb for row in kb_rows(kb) for _, cb in row]


def layout(kb) -> list[list[str]]:
    """فقط ساختار callback (بدون برچسب) — برای مقایسهٔ ساختاری بین زبان‌ها/پلتفرم‌ها."""
    return [[cb for _, cb in row] for row in kb_rows(kb)]


def handler_fingerprint(app) -> dict:
    """اثر انگشت ثبت‌نام هندلر: گروه‌ها + انواع هندلر + الگوهای callback."""
    groups = {}
    for gi, group in sorted(app.handlers.items()):
        groups[gi] = sorted(type(h).__name__ for h in group)
    patterns = sorted(
        (h.pattern.pattern if getattr(h, "pattern", None) else "*")
        for g in app.handlers.values() for h in g
        if type(h).__name__ == "CallbackQueryHandler"
    )
    return {"groups": groups, "cb_patterns": patterns}


def last_markup_rows() -> list:
    """آخرین reply_markup ثبت‌شده در fake_post (پاسخ منوی /start)."""
    for endpoint, data in reversed(REC.calls):
        rm = (data or {}).get("reply_markup")
        if rm is not None:
            return kb_rows(rm)
    return []


async def main() -> int:
    r = Result()

    # ══ بخش A) ساخت هر دو پلتفرم + زیرساخت ═══════════════════════════════
    bale_app = build_application("bale")
    tele_app = build_application("telegram")
    r.check("build_application('bale') موفق", bale_app is not None)
    r.check("build_application('telegram') موفق", tele_app is not None)
    r.check("بله: base_url = tapi.bale.ai", bale_app.bot.base_url.startswith("https://tapi.bale.ai/bot"),
            bale_app.bot.base_url)
    r.check("تلگرام: base_url = پل پیکربندی‌شده", tele_app.bot.base_url.startswith("https://bridge.example/bot"),
            tele_app.bot.base_url)
    src_bot = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "app", "bot.py"), encoding="utf-8").read()
    r.check("فایل persistence جدا برای هر پلتفرم",
            bale_app.persistence is not tele_app.persistence
            and "bot_persistence_{platform}.pkl" in src_bot)

    # ══ بخش B) پاریتی ثبت‌نام هندلرها (الزام ۸ — سطح هندلر) ═══════════════
    fp_b, fp_t = handler_fingerprint(bale_app), handler_fingerprint(tele_app)
    r.check("گروه‌های هندلر دو پلتفرم یکسان", fp_b["groups"] == fp_t["groups"])
    r.check("الگوهای callback دو پلتفرم یکسان", fp_b["cb_patterns"] == fp_t["cb_patterns"])
    r.check("MENU_PATTERN همهٔ callbackهای منو را می‌پذیرد",
            all(MENU_PATTERN_MATCH(cb) for cb in MENU_CALLBACKS))

    # ══ بخش C) الزامات ۱-۴ و ۶-۷ روی هر سه زبان ═══════════════════════════
    for lang in LANGS:
        kb = get_main_menu_keyboard(lang)
        cbs = cbs_of(kb)
        rows = kb_rows(kb)
        r.check(f"[{lang}] جست‌وجو در منوی اصلی (الزام ۲)", "search" in cbs)
        r.check(f"[{lang}] مشاور سلامت در منوی اصلی (الزام ۳)", "advisor" in cbs)
        r.check(f"[{lang}] شش دستهٔ خدماتی (الزام ۴)", all(c in cbs for c in CATEGORY_KEYBOARDS))
        r.check(f"[{lang}] حیاتی‌ها تمام‌عرض (الزام ۱)",
                all(any(len(row) == 1 and row[0][1] == c for row in rows) for c in WIDE))
        r.check(f"[{lang}] حداکثر ۲ دکمه در هر ردیف (الزام ۱)", all(len(row) <= 2 for row in rows))
        r.check(f"[{lang}] بدون callback تکراری (الزام ۱)", len(cbs) == len(set(cbs)))
        r.check(f"[{lang}] همهٔ دکمه‌های اصلی پوشیده (الزام ۶)", all(c in cbs for c in MAIN_EXPECTED))
        r.check(f"[{lang}] همهٔ خدمات قدیمی در دسترس (الزام ۶)",
                all(c in MENU_CALLBACKS for c in LEGACY_SERVICES))
        for name, expected in CAT_EXPECTED.items():
            cat_cbs = set(cbs_of(CATEGORY_KEYBOARDS[name](lang)))
            r.check(f"[{lang}] {name}: گروه‌بندی درست (الزام ۴)", expected <= cat_cbs,
                    str(expected - cat_cbs))
        back_kb = get_back_keyboard(lang)
        r.check(f"[{lang}] بازگشت واقعی back_main + پیشنهادات (الزام ۵)",
                cbs_of(back_kb) == ["back_main", "start_feedback"])
        lang_kb = get_language_keyboard()
        r.check(f"[{lang}] کیبورد زبان: سه گزینه (الزام ۷)",
                cbs_of(lang_kb) == ["lang_fa", "lang_en", "lang_ar"])

    # ══ بخش D) پاریتی ساختاری سه‌زبانه (الزام ۷) ══════════════════════════
    r.check("ساختار منوی اصلی در fa/ar/en یکسان (الزام ۷)",
            layout(get_main_menu_keyboard("fa"))
            == layout(get_main_menu_keyboard("ar"))
            == layout(get_main_menu_keyboard("en")))
    for name in CATEGORY_KEYBOARDS:
        r.check(f"ساختار {name} در سه زبان یکسان (الزام ۷)",
                layout(CATEGORY_KEYBOARDS[name]("fa"))
                == layout(CATEGORY_KEYBOARDS[name]("ar"))
                == layout(CATEGORY_KEYBOARDS[name]("en")))
    fa_search, en_search = get_main_menu_keyboard("fa"), get_main_menu_keyboard("en")
    r.check("برچسب جست‌وجو در fa و en واقعاً متفاوت است (ترجمهٔ واقعی)",
            kb_rows(fa_search)[0][0][0] != kb_rows(en_search)[0][0][0])

    # ══ بخش E) پاریتی سرتاسری: /start + انتخاب زبان روی هر دو پلتفرم ═══════
    app = await build_app()  # پلتفرم بله (هارنس استاندارد)
    uid = 1901
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))  # کاربر تازه ابتدا زبان انتخاب می‌کند
    bale_menu = last_markup_rows()
    REC.calls.clear()

    tele_app.bot._post = REC.fake_post  # type: ignore[attr-defined]
    await tele_app.initialize()
    from app import runtime
    runtime.bind_application(tele_app)
    u = make_start_update(uid + 1, "/start")
    u._bot = tele_app.bot
    await tele_app.process_update(u)
    cq = make_cb_update(uid + 1, "lang_fa")
    cq._bot = tele_app.bot
    await tele_app.process_update(cq)
    tele_menu = last_markup_rows()

    r.check("پاریتی سرتاسری: کیبورد منوی اصلی بله = تلگرام (الزام ۸)", bale_menu == tele_menu)
    r.check("منوی اصلی بله ≥ ۱۰ دکمه در ۵ ردیف", len(bale_menu) >= 5 and sum(len(row) for row in bale_menu) >= 10)
    r.check("منوی اصلی تلگرام ≥ ۱۰ دکمه در ۵ ردیف", len(tele_menu) >= 5 and sum(len(row) for row in tele_menu) >= 10)
    r.check("منوی سرتاسری شامل جست‌وجو و مشاور (الزام ۲و۳)",
            {"search", "advisor"} <= {cb for row in bale_menu for _, cb in row})

    return r.finish("T19 پاریتی دو پلتفرم: bale↔telegram + الزامات ۸گانه")


def MENU_PATTERN_MATCH(cb: str) -> bool:
    import re
    return re.match(MENU_PATTERN, cb) is not None


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
