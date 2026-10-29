# -*- coding: utf-8 -*-
"""T03 — جریان رزرو: موفق، رد اسلات اشغال، رقابت هم‌زمان، fail-closed (بخش ۳.۴-۳.۶ و بخش D)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_buttons, make_cb_update, make_start_update,
    make_text_update, next_id, process, tmp_dir, write_json,
)

from app.services import booking as bs  # noqa: E402

DATE = "2030-01-10"


def appt(user_id, doctor_key, status="pending"):
    return {
        "user_id": user_id, "full_name": f"U{user_id}", "national_code": "0079345948",
        "spec_key": doctor_key.split(":")[0], "doctor_key": doctor_key,
        "doctor_id": doctor_key.split(":")[1], "doctor_name": "دکتر تست",
        "date": DATE, "time": "09:00", "amount": 100_000,
        "commission_rate": 0.0, "commission_amount": 0, "doctor_share": 100_000,
        "status": status,
    }


async def main() -> int:
    r = Result()
    app = await build_app()
    base = tmp_dir()

    # ── ۳.۴ رزرو موفق یک نوبت ──
    ok = bs.add_appointment(appt(101, "cardio:doc_001"))
    r.check("رزرو موفق یک نوبت", ok is True)
    rows = bs.load_appointments()
    r.check("نوبت ذخیره شد", any(a["user_id"] == 101 and a["status"] == "pending" for a in rows))
    r.check("expires_at برای pending ست شده", bool(rows[0].get("expires_at")))

    # ── ۳.۵ رد رزرو زمان اشغال (بررسی نهایی در ثبت) ──
    r.check("اسلات اشغال در is_time_available رد می‌شود", bs.is_time_available(DATE, "09:00", "cardio:doc_001") is False)
    ok2 = bs.add_appointment(appt(102, "cardio:doc_001"))
    r.check("ثبت دوم همان اسلات رد می‌شود (چک نهایی در add_appointment)", ok2 is False)
    ok3 = bs.add_appointment(appt(102, "dental:doc_001"))
    r.check("همان ساعت برای پزشک دیگر آزاد است", ok3 is True)

    # ── ۳.۶ تلاش هم‌زمان دو کاربر برای یک نوبت → فقط یک ثبت ──
    bs.save_appointments([])
    async def race(user_id):
        return bs.add_appointment(appt(user_id, "cardio:doc_001"))
    results = await asyncio.gather(race(201), race(202), race(203))
    r.check("از ۳ رقابت هم‌زمان فقط یکی برنده شد", results.count(True) == 1, str(results))
    winners = [a for a in bs.load_appointments() if a["time"] == "09:00" and a["date"] == DATE]
    r.check("فقط یک رکورد در فایل", len(winners) == 1, str(len(winners)))

    # ── بخش D: fail-closed — فایل خراب نباید «همه آزاد» بدهد ──
    path = os.path.join(base, "data", "appointments.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{corrupt!!")
    times = bs.get_available_times(DATE, "cardio:doc_001")
    r.check("فایل خراب → هیچ ساعتی «آزاد» نشان داده نمی‌شود (fail-closed)", times == [], str(times))
    r.check("is_time_available روی فایل خراب False", bs.is_time_available(DATE, "09:00", "cardio:doc_001") is False)
    ok4 = bs.add_appointment(appt(301, "cardio:doc_001"))
    r.check("ثبت نوبت روی فایل خراب رد می‌شود (نوشتن انجام نمی‌شود)", ok4 is False)
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    r.check("فایل خراب بازنویسی نشد", "corrupt" in content)

    # ── انقضای pending (بخش D) ──
    good = appt(401, "cardio:doc_002")
    good["expires_at"] = "2020-01-01T00:00:00"
    bs.save_appointments([good])
    loaded = bs.load_appointments()
    r.check("pending منقضی‌شده پاک می‌شود", not any(a.get("user_id") == 401 for a in loaded))

    # ── mark_appointment_paid + cancel ──
    bs.save_appointments([appt(501, "cardio:doc_003")])
    r.check("mark_appointment_paid موفق", bs.mark_appointment_paid(501, DATE, "09:00") is True)
    r.check("وضعیت paid شد", all(a["status"] == "paid" for a in bs.load_appointments()))
    r.check("mark_appointment_paid دوباره → False (فقط pending)", bs.mark_appointment_paid(501, DATE, "09:00") is False)

    # ── جریان واقعی ConversationHandler رزرو: تا مرحله‌ی پرداخت ──
    # (درگاه واقعی mock می‌شود — آزمون نباید به شبکه زرین‌پال وابسته باشد)
    REC.reset()
    bs.save_appointments([])
    from unittest.mock import patch
    from app.services import payment as pm_mod
    class _R:
        status_code = 200
        content = b"1"
        def json(self):
            return {"data": {"code": 100, "authority": "TESTAUTH1"}}
    with patch.object(pm_mod.requests, "post", return_value=_R()):
        from app.services import doctor_loader
        specs = doctor_loader.load_specialties()
        uid = 777
        await process(make_start_update(uid, "/start"))
        await process(make_cb_update(uid, "lang_fa"))
        await process(make_cb_update(uid, "start_booking"))
        await process(make_text_update(uid, "علی رضایی"))
        await process(make_text_update(uid, "1234567891"))
        await process(make_cb_update(uid, "bk_id_ok"))
        texts = REC.sent_texts()
        r.check("پرامپت انتخاب تخصص بعد از تایید هویت", any("تخصص" in t for t in texts), str([t[:40] for t in texts[-2:]]))
        spec_key = specs[0]["key"]
        await process(make_cb_update(uid, f"bk_specpick_{spec_key}"))
        await process(make_cb_update(uid, f"bk_doc_{spec_key}_0"))
        await process(make_cb_update(uid, f"bk_date_{DATE}"))
        texts = REC.sent_texts()
        r.check("پرامپت انتخاب ساعت با ساعت‌های آزاد", any("ساعت" in t for t in texts))
        await process(make_cb_update(uid, "bk_time_10:00"))
        texts = REC.sent_texts()
        r.check("صفحه‌ی تایید نهایی با نام/کد/پزشک/مبلغ", any("کد ملی" in t and "مبلغ" in t for t in texts), str(texts[-1][:80] if texts else "NO"))
        await process(make_cb_update(uid, "booking_confirm"))
        texts = REC.sent_texts()
        r.check("لینک پرداخت صادر شد (authority جعلی درگاه)", any("StartPay" in t or "پرداخت" in t for t in texts), str(texts[-1][:80] if texts else "NO"))
    rows = bs.load_appointments()
    r.check("نوبت pending ثبت شد در جریان کامل", any(a["user_id"] == uid and a["status"] == "pending" for a in rows), str(rows))

    # ── رزرو روی اسلات گرفته‌شده در UI واقعی → پیام slot_taken ──
    REC.reset()
    uid2 = 778
    bs.save_appointments([dict(appt(999, f"{spec_key}:{doctor_loader.load_doctors(spec_key)[0]['id']}"), time="10:00", date=DATE)])
    with patch.object(pm_mod.requests, "post", return_value=_R()):
        await process(make_start_update(uid2, "/start"))
        await process(make_cb_update(uid2, "lang_fa"))
        await process(make_cb_update(uid2, "start_booking"))
        await process(make_text_update(uid2, "مریم احمدی"))
        await process(make_text_update(uid2, "0079345948"))
        await process(make_cb_update(uid2, "bk_id_ok"))
        await process(make_cb_update(uid2, f"bk_specpick_{spec_key}"))
        await process(make_cb_update(uid2, f"bk_doc_{spec_key}_0"))
        await process(make_cb_update(uid2, f"bk_date_{DATE}"))
        texts = REC.sent_texts()
        r.check("ساعت اشغال در کیبورد نیست", all("10:00" not in str(kb) for kb in REC.keyboards()[-1:]), "10:00 باید حذف می‌بود")
        await process(make_cb_update(uid2, "bk_time_11:00"))
        await process(make_cb_update(uid2, "booking_confirm"))
    rows = bs.load_appointments()
    r.check("نوبت دوم (پزشک یکسان ساعت متفاوت) ثبت شد", any(a["user_id"] == uid2 for a in rows))

    return r.finish("T03 booking")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
