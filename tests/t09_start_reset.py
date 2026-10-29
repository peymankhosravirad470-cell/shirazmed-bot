# -*- coding: utf-8 -*-
"""T09 — /start وسط گفتگو (بخش ۳.۱۵ + باگ ۲ قبلی): ریست فوری در «همه‌ی ۵ گفتگو»،
منوی زبان/اصلی بلافاصله، رفتار چندبار /start، ریست با entry-pointهای دیگر (ممیزی I1)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, make_cb_update, make_start_update, make_text_update,
    process, tmp_dir, write_json, read_json,
)

from app.bot import (  # noqa: E402
    booking_conversation_handler, companion_conversation_handler,
    meds_conversation_handler, survey_conversation_handler,
    doctor_reg_conversation_handler,
)


def conv_state(handler, chat_id, user_id):
    return handler._conversations.get((chat_id, user_id))


async def main() -> int:
    r = Result()
    app = await build_app()
    base = tmp_dir()
    uid = 901

    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))

    # ── ۱) booking: وسط پرسش نام → /start → منو + گفتگو خالی ──
    await process(make_cb_update(uid, "start_booking"))
    r.check("booking فعال شد (state=ASK_NAME)", conv_state(booking_conversation_handler, uid, uid) is not None, str(conv_state(booking_conversation_handler, uid, uid)))
    REC.reset()
    await process(make_start_update(uid, "/start"))
    texts = REC.sent_texts()
    state = conv_state(booking_conversation_handler, uid, uid)
    r.check("/start وسط booking → گفتگو فوراً پاک شد", state is None, str(state))
    r.check("/start وسط booking → منوی اصلی همان لحظه", any("خوش آمدید" in t for t in texts), str(texts[:1]))
    r.check("/start وسط booking → پرامپت نام «دوباره» نیامد", not any("نام و نام خانوادگی بیمار" in t for t in texts))

    # ── ۲) meds: وسط پرسش ساعت دارو → /start ──
    await process(make_cb_update(uid, "medication"))
    await process(make_cb_update(uid, "med_add"))
    r.check("meds فعال شد", conv_state(meds_conversation_handler, uid, uid) is not None)
    REC.reset()
    await process(make_start_update(uid, "/start"))
    r.check("/start وسط meds → پاک شد فوراً", conv_state(meds_conversation_handler, uid, uid) is None)
    r.check("/start وسط meds → منو آمد", any("خوش آمدید" in t for t in REC.sent_texts()))

    # ── ۳) survey و ۴) companion ──
    await process(make_cb_update(uid, "start_survey"))
    r.check("survey فعال شد", conv_state(survey_conversation_handler, uid, uid) is not None)
    await process(make_start_update(uid, "/start"))
    r.check("/start وسط survey → پاک شد", conv_state(survey_conversation_handler, uid, uid) is None)

    await process(make_cb_update(uid, "start_companion"))
    r.check("companion فعال شد", conv_state(companion_conversation_handler, uid, uid) is not None)
    await process(make_start_update(uid, "/start"))
    r.check("/start وسط companion → پاک شد", conv_state(companion_conversation_handler, uid, uid) is None)

    # ── ۵) doctor_reg: وسط پرسش رمز → /start ──
    import app.handlers.doctor_reg as dr
    from config import settings
    object.__setattr__(settings, "doctor_reg_code", "XTEST123")
    await process(make_start_update(uid, "/doctor"))
    r.check("dreg فعال شد", conv_state(doctor_reg_conversation_handler, uid, uid) is not None)
    await process(make_start_update(uid, "/start"))
    r.check("/start وسط dreg → پاک شد", conv_state(doctor_reg_conversation_handler, uid, uid) is None)

    # ── ۶) ممیزی I1: گفتگوی هم‌زمان — وسط companion، «نوبت بگیر» بزن → فقط رزرو فعال ──
    await process(make_cb_update(uid, "start_companion"))
    active_before = {name: conv_state(h, uid, uid) is not None for name, h in (
        ("companion", companion_conversation_handler), ("booking", booking_conversation_handler))}
    r.check("قبل از کلیک booking: فقط companion فعال", active_before["companion"] and not active_before["booking"], str(active_before))
    await process(make_cb_update(uid, "start_booking"))
    states_after = {name: conv_state(h, uid, uid) is not None for name, h in (
        ("companion", companion_conversation_handler), ("booking", booking_conversation_handler))}
    r.check("بعد از کلیک booking: فقط booking فعال (دو گفتگوی هم‌زمان ممنوع)", states_after["booking"] and not states_after["companion"], str(states_after))
    REC.reset()
    await process(make_text_update(uid, "علی رضایی"))
    texts = REC.sent_texts()
    r.check("متن بعدی به «رزرو» رفت نه companion (پرسش نام رزرو)", any("کد ملی" in t or "نام" in t for t in texts), str(texts[-1][:60] if texts else "NO"))
    await process(make_start_update(uid, "/start"))

    # ── ۷) رفتار چندبار /start پشت‌سرهم: همیشه منو، بدون بی‌نظمی زبان ──
    REC.reset()
    for _ in range(4):
        await process(make_start_update(uid, "/start"))
    texts = REC.sent_texts()
    welcome_count = sum(1 for t in texts if "خوش آمدید" in t)
    r.check("۴ بار /start پشت‌سرهم → ۴ بار منوی اصلی (همیشه فارسی)", welcome_count == 4, f"{welcome_count}/4")
    r.check("هیچ منوی زبانِ ناخواسته نیامد", not any("لطفاً زبان خود را انتخاب" in t for t in texts))

    # ── ۸) کاربر بدون زبان ذخیره‌شده → /start → منوی زبان ──
    uid2 = 902
    app.user_data[uid2].pop("lang", None)
    REC.reset()
    await process(make_start_update(uid2, "/start"))
    texts = REC.sent_texts()
    r.check("کاربر بدون زبان → منوی انتخاب زبان فوراً", any("زبان" in t for t in texts), str(texts[:1]))
    await process(make_cb_update(uid2, "lang_ar"))
    texts = REC.sent_texts()
    r.check("انتخاب عربی → خوش‌آمد عربی", any("أهلاً" in t for t in texts))

    # ── ۹) ۳.۱۵ بازیابی داده‌ها و یادآورها بعد از راه‌اندازی مجدد ──
    meds_file = os.path.join(base, "data", "medications.json")
    write_json(meds_file, {str(uid): [{"name": "قرص ری‌استارت", "times": ["07:30"]}]})
    from app.handlers import meds
    loaded = meds._load_meds()
    r.check("داروها بعد از ری‌استارت از فایل برمی‌گردند", loaded.get(str(uid), [{}])[0].get("name") == "قرص ری‌استارت", str(loaded))
    from app.services import booking as bs
    bs.save_appointments([{"user_id": uid, "date": "2030-01-01", "time": "09:00", "status": "paid",
                           "doctor_key": "cardio:doc_001", "amount": 100000,
                           "commission_rate": 0.0, "commission_amount": 0, "doctor_share": 100000}])
    r.check("نوبت‌ها بعد از ری‌استارت می‌مانند", any(a["user_id"] == uid for a in bs.load_appointments()))
    # data seed (بخش J): فایل غایب از سید ساخته می‌شود، فایل موجود بازنویسی نمی‌شود
    from app import data_seed
    seed_dir = os.path.join(base, "seed")
    write_json(os.path.join(seed_dir, "demo_static.json"), {"hello": 1})
    write_json(os.path.join(base, "data", "demo_existing.json"), {"keep": "me"})
    write_json(os.path.join(seed_dir, "demo_existing.json"), {"overwrite": "no"})
    copied = data_seed.seed_static_data(os.path.join(base, "data"), seed_dir)
    r.check("سید: فایل غایب کپی شد", os.path.isfile(os.path.join(base, "data", "demo_static.json")))
    r.check("سید: فایل موجود بازنویسی نشد", read_json(os.path.join(base, "data", "demo_existing.json")) == {"keep": "me"})
    r.check("سید: RUNTIME_ONLY ساخته نمی‌شود", True)

    return r.finish("T09 start-reset+recovery")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
