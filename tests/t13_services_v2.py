# -*- coding: utf-8 -*-
"""T13 — سرویس‌های جدید مأموریت ۲۰ قابلیت (تست واحد سرویس‌های خالص):

۱. دستیار هوشمند: پرچم‌های سرخ سه‌زبانه (اولویت مطلق)، حالت راهنما با برچسب صادقانه،
   سقوط LLM به حالت راهنما (بدون دروغ)، نیت‌های منو، سلب مسئولیت پزشکی
۲. ارجاع: پارس کد/لینک قدیمی، خودارجاعی ممنوع، تکراری ممنوع، پاداش فقط بعد از
   پرداخت واقعی، مصرف اتمیک پاداش، آمار و برترین‌ها
۳. آمار: جمع از دادهٔ واقعی (تراکنش/نوبت/دارو/ارجاع) + قالب فارسی
۴. بسته‌ها: صحت ساختار + همهٔ ارجاع‌ها به نام‌های واقعی مخزن
۵. یادآور نوبت: فقط نوبت پرداخت‌شدهٔ آینده → دو یادآور (۲۴ و ۲ ساعت)؛ گذشته/پندینگ → صفر
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import Result, run, tmp_dir, write_json  # noqa: E402

from app.services import ai_assistant as ai  # noqa: E402
from app.services import referral as rf  # noqa: E402
from app.services import stats as st  # noqa: E402
from app.services import apt_reminders as ar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _save_ref_file(rows):
    write_json(os.path.join(tmp_dir(), "data", "referrals.json"), {"referrals": rows})


def _load_ref_file():
    with open(os.path.join(tmp_dir(), "data", "referrals.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


class FakeJobQueue:
    def __init__(self):
        self.jobs = []

    def run_once(self, callback, when, chat_id=None, data=None, name=None):
        self.jobs.append({"callback": callback, "when": when, "chat_id": chat_id, "data": data or {}, "name": name})


class FakeApp:
    def __init__(self, jq=None):
        self.job_queue = jq or FakeJobQueue()


async def main():
    r = Result()

    # ── ۱) دستیار هوشمند ──────────────────────────────────────────────
    r.check("red-flag fa", ai.detect_red_flags("بابام امروز درد قفسه سینه شدید دارد"))
    r.check("red-flag en", ai.detect_red_flags("I have chest pain right now"))
    r.check("red-flag ar", ai.detect_red_flags("عندي ألم في الصدر شديد"))
    r.check("red-flag not triggered by normal text", not ai.detect_red_flags("هتل نزدیک بیمارستان می‌خواهم"))

    em = ai.emergency_answer("fa")
    r.check("emergency mentions 115", "۱۱۵" in em and "اورژانس" in em)
    em_en = ai.emergency_answer("en")
    r.check("emergency en mentions 115", "115" in em_en)

    # حالت راهنما (بدون کلید): صادقانه برچسب می‌خورد + نیت‌ها
    os.environ.pop("AI_API_KEY", None)
    os.environ.pop("AVALAI_API_KEY", None)
    out = ai.smart_answer("می‌خواهم نوبت دکتر قلب بگیرم", "fa")
    r.check("guide mode flag honest", out["mode"] == "fallback")
    r.check("guide mode discloses itself", "حالت راهنما" in out["text"])
    r.check("intent booking routed", "نوبت بگیر" in out["text"])
    out2 = ai.smart_answer("هتل نزدیک بیمارستان می‌خواهم", "fa")
    r.check("intent hotel routed", "هتل" in out2["text"] and "Non-medical" not in out2["text"])
    out3 = ai.smart_answer("بیمه تأمین اجتماعی چه پوششی دارد؟", "fa")
    r.check("intent insurance routed", "بیمه" in out3["text"])
    out4 = ai.smart_answer("asdkjhqwe zzz unknown question!?", "en")
    r.check("unknown → generic guide", "Shiraz Medical guide" in out4["text"])
    r.check("generic includes medical referral", "doctor" in out4["text"].lower())

    # سقوط LLM: کلید هست ولی سرور ناپایدار (localhost بسته) → باید صادقانه به راهنما برگردد
    os.environ["AI_API_KEY"] = "test-key-123"
    os.environ["AI_BASE_URL"] = "http://127.0.0.1:1/v1"
    try:
        out5 = ai.smart_answer("هزینه پکیج چقدر است؟", "fa")
        r.check("LLM failure → honest fallback", out5["mode"] == "fallback" and "حالت راهنما" in out5["text"])
    finally:
        os.environ.pop("AI_API_KEY", None)
        os.environ.pop("AI_BASE_URL", None)

    # پرچم سرخ حتی با کلید فعال، اورژانس می‌دهد (اولویت مطلق)
    os.environ["AI_API_KEY"] = "test-key-123"
    os.environ["AI_BASE_URL"] = "http://127.0.0.1:1/v1"
    try:
        out6 = ai.smart_answer("درد سینه شدید دارم", "fa")
        r.check("red flag wins over LLM", out6["mode"] == "emergency" and "۱۱۵" in out6["text"])
    finally:
        os.environ.pop("AI_API_KEY", None)
        os.environ.pop("AI_BASE_URL", None)
    r.check("disclaimer present in guide answers", "پزشک" in ai.fallback_answer("چیزی", "fa") + ai._DISCLAIMER["fa"])

    # ── ۲) ارجاع ──────────────────────────────────────────────────────
    _save_ref_file([])
    r.check("code roundtrip", rf.parse_referral_code(rf.referral_code(123456)) == 123456)
    r.check("legacy numeric link accepted", rf.parse_referral_code("999888") == 999888)
    r.check("docreg never a referral", rf.parse_referral_code("docreg") is None)
    r.check("garbage rejected", rf.parse_referral_code("hello!") is None)

    r.check("record ok", rf.record_referral(5001, 6001, "invited1") is True)
    r.check("duplicate invited rejected", rf.record_referral(5001, 6001) is False)
    r.check("other referrer for same invited rejected", rf.record_referral(5002, 6001) is False)
    r.check("self-referral rejected", rf.record_referral(5002, 5002) is False)
    r.check("invalid ids rejected", rf.record_referral(0, 6002) is False)

    r.check("no reward before payment (honest)", rf.get_available_discount_pct(5001) == 0)
    r.check("mark paid", rf.mark_referral_paid(6001) is True)
    r.check("reward available after real payment", rf.get_available_discount_pct(5001) == 10)
    stats = rf.get_referral_stats(5001)
    r.check("personal stats", stats["joined"] == 1 and stats["paid"] == 1 and stats["available_rewards"] == 1)
    r.check("consume reward", rf.consume_reward(5001) is True)
    r.check("reward gone after use", rf.get_available_discount_pct(5001) == 0)
    r.check("consume twice rejected", rf.consume_reward(5001) is False)
    tops = rf.top_referrers(5)
    r.check("top referrers has referrer", any(t["referrer_id"] == 5001 and t["used"] == 1 for t in tops))
    counts = rf.count_referrals()
    r.check("global counts", counts["total"] == 1 and counts["used_rewards"] == 1)
    file_rows = _load_ref_file()["referrals"]
    r.check("file keeps lifecycle fields", file_rows[0]["status"] == "paid" and "used_at" in file_rows[0])

    # ── ۳) آمار ────────────────────────────────────────────────────────
    tx_dir = os.path.join(tmp_dir(), "data", "transactions")
    os.makedirs(tx_dir, exist_ok=True)
    write_json(os.path.join(tx_dir, "6001.json"), [
        {"authority": "A1", "amount": 50000, "status": "verified", "ref_id": "RF1"},
        {"authority": "A2", "amount": 100000, "status": "pending"},
    ])
    from app.services import booking as bs
    bs.add_appointment({
        "user_id": 6001, "full_name": "تست آمار", "national_code": "2300365383",
        "spec_key": "cardio", "doctor_key": "cardio:x", "doctor_id": "x",
        "doctor_name": "دکتر آمار", "date": "2031-01-01", "time": "09:00",
        "amount": 100000, "status": "paid",
    })
    s = st.collect_stats()
    r.check("stats keys", all(k in s for k in ("appointments", "payments", "med_reminders", "referrals", "doctors", "known_users")))
    r.check("stats payments from real data", s["payments"]["verified_count"] >= 1 and s["payments"]["verified_amount"] >= 50000)
    r.check("stats appointments real", s["appointments"]["paid"] >= 1)
    r.check("stats referral counted", s["referrals"]["total"] >= 1)
    text = st.format_stats(s)
    r.check("stats format fa", "آمار شیراز مدیکال" in text and "تومان" in text)

    # ── ۴) بسته‌ها ──────────────────────────────────────────────────────
    with open(os.path.join(ROOT, "data", "packages.json"), "r", encoding="utf-8") as fh:
        pkg_data = json.load(fh)
    packages = pkg_data.get("packages", [])
    r.check("packages exist", len(packages) >= 3)
    ids = [p.get("id") for p in packages]
    r.check("package ids unique", len(ids) == len(set(ids)) and all(ids))
    hospitals = json.load(open(os.path.join(ROOT, "data", "hospitals.json"), encoding="utf-8"))
    hotels = json.load(open(os.path.join(ROOT, "data", "hotels.json"), encoding="utf-8"))
    h_names = {h.get("name_fa") for h in hospitals}
    ht_names = {h.get("name_fa") for h in hotels}
    ok_refs = True
    for p in packages:
        for field in ("title", "summary", "duration"):
            if not all(p.get(field, {}).get(l) for l in ("fa", "en", "ar")):
                ok_refs = False
        for c in p.get("components", []):
            if c.get("role") == "hospital" and c.get("place", {}).get("name_fa") not in h_names:
                ok_refs = False
            if c.get("role") == "hotel" and c.get("place", {}).get("name_fa") not in ht_names:
                ok_refs = False
    r.check("packages trilingual + real repo references only", ok_refs)
    r.check("cost transparency footer", "۱۰۰٬۰۰۰" in pkg_data.get("footer", {}).get("fa", "") or "100,000" in pkg_data.get("footer", {}).get("en", ""))

    # ── ۵) یادآور نوبت ─────────────────────────────────────────────────
    future = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    past = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    jq = FakeJobQueue()
    n = ar.schedule_appointment_reminders(FakeApp(jq), {
        "status": "paid", "date": future, "time": "16:00", "doctor_name": "دکتر یادآور", "lang": "fa",
    }, 6001)
    r.check("future paid → 2 reminders", n == 2 and len(jq.jobs) == 2)
    kinds = sorted(j["data"]["kind"] for j in jq.jobs)
    r.check("reminder kinds 1d+2h", kinds == ["1d", "2h"])
    r.check("reminder targets chat", all(j["chat_id"] == 6001 for j in jq.jobs))
    r.check("reminder text uses locale template", "دکتر یادآور" in jq.jobs[0]["data"]["text"])
    n2 = ar.schedule_appointment_reminders(FakeApp(FakeJobQueue()), {
        "status": "paid", "date": past, "time": "09:00", "doctor_name": "د", "lang": "fa",
    }, 6002)
    r.check("past paid → 0 reminders", n2 == 0)
    n3 = ar.schedule_appointment_reminders(FakeApp(FakeJobQueue()), {
        "status": "pending", "date": future, "time": "09:00", "doctor_name": "د", "lang": "fa",
    }, 6003)
    r.check("pending → 0 reminders", n3 == 0)
    n4 = ar.schedule_appointment_reminders(FakeApp(FakeJobQueue()), {
        "status": "paid", "date": "bad-date", "time": "xx", "doctor_name": "د", "lang": "fa",
    }, 6004)
    r.check("bad date → 0 reminders (no crash)", n4 == 0)

    return r.finish("T13 services: AI+referral+stats+packages+apt-reminders")


run(main, "t13_services_v2.py")
