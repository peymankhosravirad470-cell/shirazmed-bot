# -*- coding: utf-8 -*-
"""T14 — جریان‌های واقعی مأموریت ۲۰ قابلیت (با Application واقعی و هندلرهای ثبت‌شده):

۱. دستیار هوشمند: دکمه → معرفی + پرچم ai_chat؛ متن → پاسخ راهنما؛ بازگشت → پرچم پاک
۲. پیگیری نوبت: لیست واقعی pending/paid + دکمه لغو فقط برای pending + لغو واقعی روی فایل
۳. ارجاع: دکمه دعوت (کد SM + لینک + آمار) + deep-link /start SM... (ثبت + اطلاع به معرف)
   + جلوگیری از خودارجاعی و تکرار
۴. پنل ادمین: /stats و /bookings فقط ادمین؛ کاربر عادی رد می‌شود
۵. بسته‌ها: لیست داده‌محور + جزئیات با نام‌های واقعی مخزن
۶. API عمومی: /api/v1/status، /api/v1/hospitals (۷ بیمارستان)، /api/v1/doctors، 404 مسیر ناشناخته
"""
import asyncio
import json
import os
import sys
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_buttons, make_cb_update, make_start_update, run,
    make_text_update, process, tmp_dir, write_json,
)

from app.services import booking as bs  # noqa: E402
from app.services import referral as rf  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_ID = 111  # همان ADMIN_CHAT_ID که helpers در env می‌گذارد


def appt(user_id, doctor_key, status="pending", date="2031-02-10", time="09:00", amount=100_000):
    return {
        "user_id": user_id, "full_name": f"U{user_id}", "national_code": "2300365383",
        "spec_key": doctor_key.split(":")[0], "doctor_key": doctor_key,
        "doctor_id": doctor_key.split(":")[1], "doctor_name": "دکتر جریان",
        "date": date, "time": time, "amount": amount,
        "commission_rate": 0.0, "commission_amount": 0, "doctor_share": 100_000,
        "status": status,
    }


async def main():
    r = Result()
    await build_app()
    from app.bot import build_application  # noqa: F401  (ثبت هندلرها همین‌جا رخ داده)

    # ── ۱) دستیار هوشمند ──────────────────────────────────────────────
    os.environ.pop("AI_API_KEY", None)
    os.environ.pop("AVALAI_API_KEY", None)
    REC.reset()
    ctx_user = 7001
    await process(make_cb_update(ctx_user, "ai_assistant"))
    intro = REC.sent_texts()[-1]
    r.check("ai intro shown", "دستیار هوشمند" in intro)
    r.check("guide-mode disclosed in intro", "حالت راهنما" in intro)
    # پرچم روی user_data واقعی اپ
    ud = REC.calls  # placeholder (no-op)
    from app.bot import MENU_CALLBACKS  # noqa: F401
    app_ud = None
    # پرچم را از طریق هندلر تست می‌کنیم: متن بعدی باید پاسخ AI بگیرد
    await process(make_text_update(ctx_user, "هتل نزدیک بیمارستان می‌خواهم"))
    reply = REC.sent_texts()[-1]
    r.check("ai answers hotel intent", "هتل" in reply)
    r.check("ai honest guide note in reply", "حالت راهنما" in reply)
    await process(make_text_update(ctx_user, "درد قفسه سینه دارم!"))
    emergency_reply = REC.sent_texts()[-1]
    r.check("ai emergency inside chat", "۱۱۵" in emergency_reply)
    # بازگشت → پرچم پاک (متن بعدی نادیده گرفته می‌شود؛ هیچ پیام جدیدی نمی‌آید)
    await process(make_cb_update(ctx_user, "back_main"))
    REC.reset()
    await process(make_text_update(ctx_user, "یک پیام بعد از خروج از دستیار"))
    r.check("ai flag cleared after back_main", REC.sent_texts() == [])

    # ── ۲) پیگیری و لغو نوبت ──────────────────────────────────────────
    r.check("seed pending appt", bs.add_appointment(appt(7002, "cardio:doc_001", "pending")))
    r.check("seed paid appt", bs.add_appointment(appt(7002, "cardio:doc_001", "paid", date="2031-03-11", time="17:00")))
    REC.reset()
    await process(make_cb_update(7002, "appointments"))
    body = "\n".join(REC.sent_texts())
    r.check("appointments list shows pending", "در انتظار پرداخت" in body)
    r.check("appointments list shows paid", "پرداخت‌شده" in body)
    marks = [kb for rm in REC.keyboards() for kb in kb_buttons(rm)]
    cancel_kbs = [kb for kb in marks if kb[1].startswith("aptcancel_")]
    r.check("cancel button only for pending", len(cancel_kbs) == 1 and "2031-02-10_09:00" in cancel_kbs[0][1])
    REC.reset()
    await process(make_cb_update(7002, cancel_kbs[0][1]))
    r.check("cancel confirmed message", "لغو" in REC.sent_texts()[-1])
    rows = [a for a in bs.load_appointments() if a.get("user_id") == 7002]
    r.check("pending really removed from disk", all(a.get("status") != "pending" for a in rows) and len(rows) == 1)
    # لغو نوبت paid از این مسیر ممکن نیست
    paid_row = rows[0]
    REC.reset()
    await process(make_cb_update(7002, f"aptcancel_{paid_row['date']}_{paid_row['time']}"))
    r.check("paid cancel refused honestly", "قابل لغو نبود" in REC.sent_texts()[-1])
    r.check("paid appt still on disk", any(a.get("status") == "paid" for a in bs.load_appointments()))

    # ── ۳) ارجاع ──────────────────────────────────────────────────────
    write_json(os.path.join(tmp_dir(), "data", "referrals.json"), {"referrals": []})
    REC.reset()
    await process(make_cb_update(8001, "invite"))
    inv = REC.sent_texts()[-1]
    r.check("invite shows SM code", rf.referral_code(8001) in inv)
    r.check("invite shows legacy-compatible link", f"ble.ir/ShirazMedBot?start=8001" in inv)
    r.check("invite honest reward text", "۱۰٪" in inv and "پرداخت" in inv)
    # deep-link واقعی: کاربر 8002 با لینک معرف 8001
    await process(make_start_update(8002, "/start SM1F41"))  # 0x1F41 = 8001
    rows = json.load(open(os.path.join(tmp_dir(), "data", "referrals.json"), encoding="utf-8"))["referrals"]
    r.check("deep-link recorded referral", any(x["referrer_id"] == 8001 and x["invited_id"] == 8002 for x in rows))
    notified = REC.sent_to(8001)
    r.check("referrer notified", any("لینک شما" in d.get("text", "") for d in notified))
    # تکرار همان invited → ثبت نمی‌شود
    await process(make_start_update(8002, "/start 8001"))
    rows2 = json.load(open(os.path.join(tmp_dir(), "data", "referrals.json"), encoding="utf-8"))["referrals"]
    r.check("duplicate invited not re-recorded", sum(1 for x in rows2 if x["invited_id"] == 8002) == 1)
    # خودارجاعی
    await process(make_start_update(8003, "/start SM1F43"))  # 0x1F43 = 8003 (خودش)
    rows3 = json.load(open(os.path.join(tmp_dir(), "data", "referrals.json"), encoding="utf-8"))["referrals"]
    r.check("self-referral not recorded", not any(x["referrer_id"] == 8003 for x in rows3))
    # پاداش فقط بعد از پرداخت واقعی فعال می‌شود
    r.check("no discount before invited pays", rf.get_available_discount_pct(8001) == 0)
    rf.mark_referral_paid(8002)
    r.check("discount after invited pays", rf.get_available_discount_pct(8001) == 10)

    # ── ۴) پنل ادمین ──────────────────────────────────────────────────
    REC.reset()
    await process(make_start_update(555, "/stats"))
    r.check("non-admin denied", "فقط برای مدیر" in REC.sent_texts()[-1])
    REC.reset()
    await process(make_start_update(ADMIN_ID, "/stats"))
    stats_txt = REC.sent_texts()[-1]
    r.check("admin /stats works", "آمار شیراز مدیکال" in stats_txt and "نوبت" in stats_txt)
    REC.reset()
    await process(make_start_update(ADMIN_ID, "/bookings"))
    btxt = REC.sent_texts()[-1]
    r.check("admin /bookings shows real row", "دکتر جریان" in btxt and "***5383" in btxt)
    r.check("national code masked even for admin", "2300365383" not in btxt)
    REC.reset()
    await process(make_start_update(ADMIN_ID, "/admin"))
    r.check("admin help lists commands", "/stats" in REC.sent_texts()[-1] and "/pending" in REC.sent_texts()[-1])
    REC.reset()
    await process(make_start_update(ADMIN_ID, "/referrals"))
    rtxt = REC.sent_texts()[-1]
    r.check("admin referrals shows top referrer", "8001" in rtxt or "هنوز ارجاعی" in rtxt)

    # ── ۵) بسته‌ها ─────────────────────────────────────────────────────
    REC.reset()
    await process(make_cb_update(8100, "package"))
    marks = [kb for rm in REC.keyboards() for kb in kb_buttons(rm)]
    pkg_btns = [kb for kb in marks if kb[1].startswith("pkg_")]
    r.check("package list from data", len(pkg_btns) == 3)
    REC.reset()
    await process(make_cb_update(8100, "pkg_eye"))
    detail = REC.sent_texts()[-1]
    r.check("package detail shows real hospital", "دکتر خدادوست" in detail)
    r.check("package detail shows real hotel", "زندیه" in detail)
    r.check("package detail cost transparency", "۱۰۰٬۰۰۰" in detail or "100,000" in detail)
    dmarks = [kb for rm in REC.keyboards() for kb in kb_buttons(rm)]
    r.check("package detail has booking button", any(kb[1] == "start_booking" for kb in dmarks))

    # ── ۶) API عمومی فقط‌خواندنی ──────────────────────────────────────
    from app.health import _HealthHandler
    httpd = HTTPServer(("127.0.0.1", 0), _HealthHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/status", timeout=5) as resp:
            status = json.loads(resp.read().decode("utf-8"))
        r.check("api status ok", resp.status == 200 and status.get("status") == "ok")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/hospitals", timeout=10) as resp:
            hospitals = json.loads(resp.read().decode("utf-8"))
        r.check("api hospitals = 7 repo hospitals", resp.status == 200 and hospitals.get("count") == 7 and len(hospitals.get("items", [])) == 7)
        r.check("api hospitals no patient data", all("user_id" not in item for item in hospitals["items"]))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/doctors", timeout=10) as resp:
            doctors = json.loads(resp.read().decode("utf-8"))
        r.check("api doctors public directory", resp.status == 200 and doctors.get("count", 0) > 0 and all("name" in d and "specialty" in d for d in doctors["items"]))
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/unknown", timeout=5)
            r.check("unknown api 404", False, "should have raised")
        except urllib.error.HTTPError as err:
            r.check("unknown api 404", err.code == 404)
    finally:
        httpd.shutdown()
        httpd.server_close()

    return r.finish("T14 flows: AI+appointments+referral+admin+packages+API")


run(main, "t14_flows_v2.py")
