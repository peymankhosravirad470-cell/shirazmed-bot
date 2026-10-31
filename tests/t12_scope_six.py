# -*- coding: utf-8 -*-
"""T12 — شش موردِ محدوده‌ی نهایی کاربر (۱۴۰۴/۰۸/۰۸) — هر مورد با جریان واقعی handler:

۱. نوبت‌دهی: ذخیره‌ی واقعی + پیام موفقیت فقط بعد از ثبت + تفکیک «اسلات اشغال» از
   «شکست ذخیره‌سازی» + مقاومت دیسک (tmp یکتا، مسیر پشتیبان، تازه‌ترین سالم برنده)
۲. منوی قدیمی: /start دوباره → منوی قبلی حذف می‌شود؛ فقط یک منوی زنده می‌ماند
۳. تالار گفتگو: برچسب جدید + لینک از تنظیمات + بدون لینک ساختگی
۴. بیمارستان‌ها: هر ۷ بیمارستانِ یکتای مخزن (هر دو فایل) با فیلدهای کامل
۵. داروخانه‌ها: فایل داده در مخزن «وجود ندارد» → تست صرفاً این واقعیت را قفل می‌کند
۶. اتصال داده‌های غیرپزشکی: راهنمای بیمار (کامل)، مراکز پشتیبانی (کامل)، فیلدهای اقامتی
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_buttons, make_cb_update, make_start_update,
    make_text_update, process, tmp_dir, write_json,
)

from app.services import booking as bs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID_CODE = "2300365383"  # کد معتبر استاندارد (همان اسکرین‌شات کاربر)


def appt(user_id, doctor_key, status="pending", date="2030-01-10", time="09:00"):
    return {
        "user_id": user_id, "full_name": f"U{user_id}", "national_code": VALID_CODE,
        "spec_key": doctor_key.split(":")[0], "doctor_key": doctor_key,
        "doctor_id": doctor_key.split(":")[1], "doctor_name": "دکتر تست",
        "date": date, "time": time, "amount": 100_000,
        "commission_rate": 0.0, "commission_amount": 0, "doctor_share": 100_000,
        "status": status,
    }


def load_data(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


async def drive_booking_until_time(app, user_id: int):
    """جریان واقعی رزرو تا «انتخاب ساعت» (بدون confirm). خروجی: (date, time)."""
    cid = user_id
    await process(make_cb_update(user_id, "start_booking", chat_id=cid))
    await process(make_text_update(user_id, "پیمان تستی", chat_id=cid))
    await process(make_text_update(user_id, VALID_CODE, chat_id=cid))
    await process(make_cb_update(user_id, "bk_id_ok", chat_id=cid))
    await process(make_cb_update(user_id, "bk_specpick_cardio", chat_id=cid))
    await process(make_cb_update(user_id, "bk_doc_cardio_0", chat_id=cid))
    from app.services.booking import get_next_14_days
    date_iso = get_next_14_days(include_today=False)[0]
    await process(make_cb_update(user_id, f"bk_date_{date_iso}", chat_id=cid))
    await process(make_cb_update(user_id, "bk_time_09:00", chat_id=cid))
    return date_iso, "09:00"


async def main() -> int:
    r = Result()
    app = await build_app()
    base = tmp_dir()
    data_dir = bs._get_data_dir()

    # ═══════════ مورد ۱ — سیستم نوبت‌دهی ═══════════

    # ۱-الف: تله‌ی tmp با نام ثابت — فایل leftover بی‌مجوز نباید ثبت را بشکند
    bs.save_appointments([])
    leftover = os.path.join(data_dir, "appointments.json.tmp")
    with open(leftover, "w") as f:
        f.write("x")
    os.chmod(leftover, 0o444)  # فقط-خواندنی — دقیقاً تله‌ی لیارا
    ok = bs.add_appointment(appt(201, "cardio:doc_001"))
    os.chmod(leftover, 0o644)
    r.check("۱-الف ثبت نوبت با leftover tmp فقط-خواندنی موفق است (تله برداشته شد)", ok is True)
    r.check("۱-الف نوبت واقعاً روی دیسک ذخیره شد", any(a["user_id"] == 201 for a in bs.load_appointments()))

    # ۱-ب: مسیر اصلی نویسشنی → ذخیره روی مسیر پشتیبان + خواندن از پشتیبان
    bs.save_appointments([])
    os.chmod(data_dir, 0o555)  # مسیر اصلی فقط-خواندنی
    try:
        ok2 = bs.add_appointment(appt(202, "cardio:doc_002"))
    finally:
        os.chmod(data_dir, 0o755)
    r.check("۱-ب ثبت نوبت وقتی مسیر اصلی نویسشنی است موفق است (مسیر پشتیبان)", ok2 is True)
    r.check("۱-ب فایل پشتیبان ساخته شد", os.path.isfile(bs.FALLBACK_APPOINTMENTS_FILE))
    rows = bs.load_appointments()
    r.check("۱-ب نوبت پشتیبان در خواندن دیده می‌شود (تازه‌ترین سالم برنده)", any(a["user_id"] == 202 for a in rows))

    # ۱-پ: فایل dict‌شکل نمونه گیت — به‌جای خالی، لیست واقعی خوانده می‌شود.
    # saved_at آینده‌نگر → این نوشته‌ی دستی «آخرین‌نویسنده» است (قطعی، مستقل از mtime)
    write_json(os.path.join(data_dir, "appointments.json"), {
        "saved_at": "9999-12-31T23:59:59.999999|999999",
        "appointments": [appt(203, "dental:doc_003")],
        "note": "شکل نمونه‌ی گیت",
    })
    rows = bs.load_appointments()
    r.check("۱-پ ساختار dict‌شکل فایل نوبت خوانده می‌شود (داده گم نمی‌شود)", any(a["user_id"] == 203 for a in rows))

    # ۱-ت: تفکیک صادقانه — اسلات واقعاً اشغال است
    r.check("۱-ت اسلات اشغال واقعی شناسایی می‌شود", bs.is_slot_taken_by_real_booking("2030-01-10", "09:00", "dental:doc_003") is True)
    r.check("۱-ت اسلات آزاد واقعی اشغال نیست", bs.is_slot_taken_by_real_booking("2030-01-10", "16:00", "dental:doc_003") is False)

    # ── ماک درگاه پرداخت (شبکه‌ی واقعی در تست ممنوع است) ──
    import app.handlers.booking as bh
    real_request_payment = bh.request_payment

    def fake_payment_success(**kw):
        return {"success": True, "url": "https://sandbox.zarinpal.com/Payment/Gate/TST123"}

    bh.request_payment = fake_payment_success

    # ۱-ث: جریان کامل واقعی رزرو → نوبت واقعاً ذخیره + پیام موفقیت فقط بعد از ثبت
    bs.save_appointments([])
    REC.reset()
    await process(make_cb_update(4100, "lang_fa", chat_id=4100))
    date_iso, time_slot = await drive_booking_until_time(app, 4100)
    await process(make_cb_update(4100, "booking_confirm", chat_id=4100))
    saved = [a for a in bs.load_appointments() if a.get("user_id") == 4100]
    r.check("۱-ث نوبت واقعاً در فایل ذخیره شد (نه فقط پیام)", len(saved) == 1)
    if saved:
        r.check("۱-ث نوبت ذخیره‌شده کامل است (نام/کد/پزشک/تاریخ/ساعت)",
                all([saved[0].get("full_name"), saved[0].get("national_code"),
                     saved[0].get("doctor_key"), saved[0].get("date"), saved[0].get("time")]))
    success_msgs = [t for t in REC.sent_texts() if "موقتاً رزرو شد" in t]
    r.check("۱-ث پیام موفقیت فقط بعد از ثبت واقعی نمایش داده شد", len(success_msgs) == 1)

    # ۱-ج: رقابت واقعی — بین انتخاب ساعت و تایید، اسلات توسط دیگری پُر می‌شود
    bs.save_appointments([])  # اسلات ۰۹:۰۰ باید آزاد باشد تا کاربر تا تایید برود
    REC.reset()
    await process(make_cb_update(4101, "lang_fa", chat_id=4101))
    d2, t2 = await drive_booking_until_time(app, 4101)
    bs.save_appointments([appt(999, "cardio:doc_001", status="paid", date=d2, time=t2)])
    await process(make_cb_update(4101, "booking_confirm", chat_id=4101))
    r.check("۱-ج اسلات واقعاً اشغال → پیام درست «پر شد» نمایش داده شد",
            any("پر شد" in t for t in REC.sent_texts()))
    r.check("۱-ج نوبت دوم ثبت نشد", not any(a.get("user_id") == 4101 for a in bs.load_appointments()))

    # ۱-چ: شکست کامل ذخیره‌سازی (اصلی + پشتیبان هر دو نویسشنی) → پیام صادقانه، نه «پر شد»
    bs.save_appointments([])  # اسلات آزاد تا کاربر تا تایید برود
    REC.reset()
    await process(make_cb_update(4102, "lang_fa", chat_id=4102))
    d3, t3 = await drive_booking_until_time(app, 4102)
    os.chmod(data_dir, 0o555)
    fb_dir = os.path.dirname(bs.FALLBACK_APPOINTMENTS_FILE)
    os.makedirs(fb_dir, exist_ok=True)
    os.chmod(fb_dir, 0o555)
    try:
        await process(make_cb_update(4102, "booking_confirm", chat_id=4102))
    finally:
        os.chmod(data_dir, 0o755)
        os.chmod(fb_dir, 0o755)
    r.check("۱-چ شکست ذخیره‌سازی → پیام صادقانه «ثبت نوبت انجام نشد»",
            any("ثبت نوبت انجام نشد" in t for t in REC.sent_texts()))
    r.check("۱-چ در شکست ذخیره‌سازی پیام دروغین «پر شد» نمایش داده نشد",
            not any("پر شد" in t for t in REC.sent_texts()))
    bh.request_payment = real_request_payment

    # ═══════════ مورد ۲ — منوی قدیمی ═══════════

    REC.reset()
    await process(make_cb_update(4200, "lang_fa", chat_id=4200))  # زبان → منو (edit درجا)
    REC.reset()
    await process(make_start_update(4200, "/start", chat_id=4200))
    menus1 = [d for ep, d in REC.calls if ep == "sendMessage" and "خوش آمدید" in str(d.get("text", ""))]
    r.check("۲ /start اول → دقیقاً یک منو ارسال شد", len(menus1) == 1)
    REC.reset()
    await process(make_start_update(4200, "/start", chat_id=4200))
    deletes = [d for ep, d in REC.calls if ep == "deleteMessage"]
    menus2 = [d for ep, d in REC.calls if ep == "sendMessage" and "خوش آمدید" in str(d.get("text", ""))]
    r.check("۲ /start دوم → منوی قدیمی حذف شد", len(deletes) == 1)
    r.check("۲ /start دوم → منوی جدید فقط یک‌بار", len(menus2) == 1)

    # بعد از بازگشت به منو، منوی «اضافه» ساخته نمی‌شود (ویرایش درجا)
    REC.reset()
    await process(make_start_update(4201, "/start", chat_id=4201))
    await process(make_start_update(4201, "/start", chat_id=4201))
    await process(make_cb_update(4201, "non_medical", chat_id=4201))  # منوی فعلی → زیرمنو
    await process(make_start_update(4201, "/start", chat_id=4201))    # منوی تازه؛ پیام قبلی حذف
    REC.reset()
    await process(make_cb_update(4201, "back_main", chat_id=4201, message_text="m"))
    sends = [d for ep, d in REC.calls if ep == "sendMessage" and "خوش آمدید" in str(d.get("text", ""))]
    edits = [d for ep, d in REC.calls if ep == "editMessageText" and "خوش آمدید" in str(d.get("text", ""))]
    r.check("۲ بازگشت به منو فقط ویرایش می‌کند (منوی اضافه نمی‌سازد)", len(sends) == 0 and len(edits) == 1)

    # ═══════════ مورد ۳ — تالار گفتگو ═══════════

    from app.locales import get_msg_btn
    from config import settings as cfg
    r.check("۳ برچسب فارسی = «💬 تالار گفتگو»", get_msg_btn("fa", "channel") == "💬 تالار گفتگو")
    r.check("۳ برچسب انگلیسی درست است", get_msg_btn("en", "channel") == "💬 Discussion Forum")
    r.check("۳ برچسب عربی درست است", get_msg_btn("ar", "channel") == "💬 غرفة النقاش")
    r.check("۳ لینک از تنظیمات خوانده می‌شود", cfg.forum_url == "https://ble.ir/shiraz_medical")
    REC.reset()
    await process(make_cb_update(4300, "channel", chat_id=4300))
    url_btns = [(t, u) for t, u in kb_buttons(REC.keyboards()[-1]) if u.startswith("http")]
    r.check("۳ دکمه تالار با لینک تنظیمات کار می‌کند",
            any(u == cfg.forum_url for _, u in url_btns))

    # ═══════════ مورد ۴ — بیمارستان‌ها ═══════════

    REC.reset()
    await process(make_cb_update(4400, "lang_fa", chat_id=4400))
    REC.reset()
    await process(make_cb_update(4400, "non_hospitals", chat_id=4400))
    texts = REC.sent_texts()
    h1 = load_data("hospitals.json")
    h2 = load_data("hospitals2.json")
    all_names = {h["name_fa"] for h in h1} | {h["name_fa"] for h in h2}
    joined = "\n".join(texts)
    shown = sum(1 for n in all_names if n in joined)
    r.check(f"۴ هر {len(all_names)} بیمارستانِ یکتای مخزن نمایش داده می‌شود (بدون حذف)", shown == len(all_names))
    r.check("۴ فیلد نوع مالکیت نمایش داده می‌شود", "نوع مالکیت" in joined)
    r.check("۴ فیلد تخصص‌ها نمایش داده می‌شود", "تخصص‌ها:" in joined)
    r.check("۴ فیلد IPD نمایش داده می‌شود", "IPD" in joined)
    r.check("۴ فیلد زبان‌های مترجم نمایش داده می‌شود", "زبان‌های مترجم" in joined)

    # ═══════════ مورد ۵ — داروخانه‌ها (واقعیت مخزن) ═══════════

    pharm_exists = os.path.isfile(os.path.join(ROOT, "data", "doctors", "pharmacies.json"))
    r.check("۵ واقعیت مستند: data/doctors/pharmacies.json در مخزن وجود ندارد (هیچ داده‌ای جعل نشد)",
            pharm_exists is False)

    # ═══════════ مورد ۶ — اتصال داده‌های غیرپزشکی ═══════════

    from app.keyboards.main import get_main_menu_keyboard
    from app.keyboards.categories import CATEGORY_KEYBOARDS
    cbs = [b.callback_data for row in get_main_menu_keyboard("fa").inline_keyboard for b in row]
    cat_cbs = {cb for cat in CATEGORY_KEYBOARDS.values() for row in cat("fa").inline_keyboard for b in row for cb in [b.callback_data]}
    # 🆕 بازطراحی منو (مأموریت مکمل): راهنمای بیمار → دستهٔ «درمان و پزشکان»،
    # مراکز پشتیبانی → دستهٔ «پشتیبانی و خدمات» — یک‌کلیکه از منوی اصلی.
    r.check("۶ دکمه «راهنمای بیمار» از منوی اصلی در دسترس است", "patient_guide" in cbs or ("cat_medical" in cbs and "patient_guide" in cat_cbs))
    r.check("۶ دکمه «مراکز پشتیبانی» از منوی اصلی در دسترس است", "support" in cbs or ("cat_support" in cbs and "support" in cat_cbs))

    REC.reset()
    await process(make_cb_update(4500, "lang_fa", chat_id=4500))
    REC.reset()
    await process(make_cb_update(4500, "patient_guide", chat_id=4500))
    joined_pg = "\n".join(REC.sent_texts())
    r.check("۶ راهنمای بیمار: مدارک ویزا نمایش داده می‌شود", "مدارک ویزای پزشکی" in joined_pg)
    r.check("۶ راهنمای بیمار: مدارک پذیرش نمایش داده می‌شود", "مدارک پذیرش بیمارستان" in joined_pg)
    r.check("۶ راهنمای بیمار: مراحل اداری نمایش داده می‌شود", "مراحل اداری" in joined_pg)
    r.check("۶ راهنمای بیمار: هزینه‌ها نمایش داده می‌شود", "هزینه‌ها و پرداخت" in joined_pg)
    r.check("۶ راهنمای بیمار: مراجع رسمی نمایش داده می‌شود", "مراجع رسمی" in joined_pg)
    r.check("۶ راهنمای بیمار: سامانه‌های رسمی نمایش داده می‌شود", "سامانه‌های رسمی" in joined_pg)
    r.check("۶ راهنمای بیمار: لینک واقعی سامانه روادید هست", "evisa.mfa.ir" in joined_pg)

    REC.reset()
    await process(make_cb_update(4600, "support", chat_id=4600))
    sp = load_data("support.json")
    joined_sp = "\n".join(REC.sent_texts())
    shown_sp = sum(1 for v in sp if v.get("name_fa") and v["name_fa"] in joined_sp)
    r.check(f"۶ هر {len(sp)} مرکز پشتیبانی نمایش داده می‌شود", shown_sp == len(sp))
    r.check("۶ فیلد خدمات پشتیبانی نمایش داده می‌شود", "خدمات:" in joined_sp)
    r.check("۶ فیلد ایمیل پشتیبانی نمایش داده می‌شود", "ایمیل" in joined_sp)

    REC.reset()
    await process(make_cb_update(4700, "lang_fa", chat_id=4700))
    REC.reset()
    await process(make_cb_update(4700, "non_hotels", chat_id=4700))
    joined_h = "\n".join(REC.sent_texts())
    r.check("۶ فیلد درجه هتل نمایش داده می‌شود", "درجه هتل" in joined_h)
    r.check("۶ فیلد فاصله تا بیمارستان‌ها نمایش داده می‌شود", "فاصله تا بیمارستان‌ها" in joined_h)
    r.check("۶ فیلد مترجم هتل نمایش داده می‌شود", "مترجم دارد" in joined_h)
    r.check("۶ فیلد خلاصه نظرات نمایش داده می‌شود", "خلاصه نظرات" in joined_h)

    # گردشگری / پایانه‌ها / موتل‌ها / خانه مسافر — متصل می‌مانند (بدون رگرسیون)
    REC.reset()
    await process(make_cb_update(4800, "lang_fa", chat_id=4800))
    REC.reset()
    await process(make_cb_update(4800, "tour_city", chat_id=4800))
    lc = load_data("leisure_city.json")
    joined_lc = "\n".join(REC.sent_texts())
    shown_lc = sum(1 for v in lc if v.get("name_fa") and v["name_fa"] in joined_lc)
    r.check(f"۶ جاذبه‌های شهری ({len(lc)} مورد) متصل مانده‌اند", shown_lc == len(lc))

    REC.reset()
    await process(make_cb_update(4900, "hubs", chat_id=4900))
    from app.handlers.callbacks import _transport_hub_items
    hub_items = _transport_hub_items()
    joined_hub = "\n".join(REC.sent_texts())
    shown_hub = sum(1 for v in hub_items if v.get("official_name_fa") and v["official_name_fa"] in joined_hub)
    r.check(f"۶ فرودگاه/راه‌آهن/پایانه‌ها ({len(hub_items)} مرکز) متصل مانده‌اند", shown_hub == len(hub_items))

    REC.reset()
    await process(make_cb_update(4950, "non_motels", chat_id=4950))
    mo = load_data("motels.json")
    joined_mo = "\n".join(REC.sent_texts())
    shown_mo = sum(1 for v in mo if v.get("name_fa") and v["name_fa"] in joined_mo)
    r.check(f"۶ مهمان‌پذیرها ({len(mo)} مورد) متصل مانده‌اند", shown_mo == len(mo))

    REC.reset()
    await process(make_cb_update(4951, "non_tourist_houses", chat_id=4951))
    thouses = load_data("tourist_houses.json")
    joined_th = "\n".join(REC.sent_texts())
    shown_th = sum(1 for v in thouses if v.get("name_fa") and v["name_fa"] in joined_th)
    r.check(f"۶ خانه‌های مسافر ({len(thouses)} مورد) متصل مانده‌اند", shown_th == len(thouses))

    return r.finish("T12")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
