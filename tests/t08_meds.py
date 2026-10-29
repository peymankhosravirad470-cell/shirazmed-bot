# -*- coding: utf-8 -*-
"""T08 — یادآور دارو (بخش H): «8 pm»→20:00، قرنطینه فایل خراب، حذف فقط همان دارو،
بازسازی بعد از ری‌استارت، نبود JobQueue → پیام صریح به کاربر، منطقه زمانی."""
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, make_cb_update, make_start_update, make_text_update,
    process, tmp_dir, write_json, read_json,
)

from app.handlers import meds  # noqa: E402


def times_for(lang, text):
    return meds.parse_times(text)


class FakeJobQueue:
    def __init__(self) -> None:
        self.jobs_list: list[Any] = []

    def jobs(self):
        return list(self.jobs_list)

    def run_daily(self, callback, time=None, days=None, chat_id=None, name=None, data=None, **kw):
        job = {"name": name, "time": str(time), "chat_id": chat_id, "data": data}
        self.jobs_list.append(_Job(job))
        return self.jobs_list[-1]


class _Job:
    def __init__(self, d):
        self.d = d
        self.name = d["name"]
        self.removed = False

    def schedule_removal(self):
        self.removed = True


async def main() -> int:
    r = Result()
    app = await build_app()

    # ── ساعت‌ها: دقیق و پیش‌بینی‌پذیر (بخش H — مثال صریح دستور) ──
    r.check("«8 pm» → 20:00 (نه 08:00!)", times_for("fa", "8 pm") == ["20:00"], str(times_for("fa", "8 pm")))
    r.check("«8pm» → 20:00", times_for("fa", "8pm") == ["20:00"])
    r.check("«8 am» → 08:00", times_for("fa", "8 am") == ["08:00"])
    r.check("«۸ صبح» → 08:00", times_for("fa", "۸ صبح") == ["08:00"])
    r.check("«۸ شب» → 20:00", times_for("fa", "۸ شب") == ["20:00"])
    r.check("«10 عصر» → 22:00", times_for("fa", "۱۰ عصر") == ["22:00"], str(times_for("fa", "۱۰ عصر")))
    r.check("«12 pm» → 12:00 و «12 am» → 00:00", times_for("fa", "12 pm 12 am") == ["00:00", "12:00"])
    r.check("«8» بدون پسوند → 08:00 (پیش‌بینی‌پذیر)", times_for("fa", "8") == ["08:00"])
    r.check("«8:00، 21:30» → [08:00, 21:30]", times_for("fa", "8:00، 21:30") == ["08:00", "21:30"])
    r.check("«0830» → 08:30", times_for("fa", "0830") == ["08:30"])
    r.check("ورودی نامعتبر «85» رد می‌شود", times_for("fa", "85") == [])
    r.check("خارج از محدوده «25:00» رد می‌شود", times_for("fa", "25:00") == [])
    r.check("تکراری حذف می‌شود", times_for("fa", "8 8:00 08:00") == ["08:00"])
    r.check("ترکیبی: «ساعت ۸ صبح و ۱۰ شب» → [08:00, 22:00]", times_for("fa", "ساعت ۸ صبح و ۱۰ شب") == ["08:00", "22:00"], str(times_for("fa", "ساعت ۸ صبح و ۱۰ شب")))

    # ── منطقه زمانی از پیکربندی ──
    tz = meds._configured_tzinfo()
    r.check("پیش‌فرض ۳.۵ → Asia/Tehran", str(tz) == "Asia/Tehran", str(tz))
    object.__setattr__(meds.settings, "timezone_offset_hours", 0.0)
    try:
        tz2 = meds._configured_tzinfo()
    finally:
        object.__setattr__(meds.settings, "timezone_offset_hours", 3.5)
    r.check("آفست ۰ → منطقه ثابت UTC", "UTC" in str(tz2) or "+00:00" in str(tz2), str(tz2))

    # ── افزودن دارو در جریان واقعی + زمان‌بندی ──
    meds_file = meds.MEDS_FILE
    if os.path.isfile(meds_file):
        os.remove(meds_file)
    uid = 801
    REC.reset()
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))
    await process(make_cb_update(uid, "medication"))
    await process(make_cb_update(uid, "med_add"))
    await process(make_text_update(uid, "قرص فشار"))
    await process(make_text_update(uid, "8 pm، 6 am"))
    texts = REC.sent_texts()
    r.check("ذخیره موفق با ساعت درست", any("20:00" in t and "06:00" in t for t in texts), str(texts[-1][:70] if texts else "NO"))
    data = read_json(meds_file)
    r.check("فایل دارو درست نوشته شد", data[str(uid)][0]["times"] == ["06:00", "20:00"], str(data))

    # ── 🆕 v49: سناریوهای اجباری مأموریت (قرص کمر / 15:00 و مشتقات) ──
    async def flow_add_med(user, med_name, time_text):
        REC.reset()
        await process(make_start_update(user, "/start"))
        await process(make_cb_update(user, "lang_fa"))
        await process(make_cb_update(user, "medication"))
        await process(make_cb_update(user, "med_add"))
        await process(make_text_update(user, med_name))
        await process(make_text_update(user, time_text))
        return REC.sent_texts()

    # ۱) نام «قرص کمر» + ساعت «15:00» → ثبت موفق یک یادآور (سناریوی اصلی گزارش)
    texts = await flow_add_med(811, "قرص کمر", "15:00")
    r.check("قرص کمر + 15:00 → ثبت موفق یک یادآور", any("قرص کمر" in t and "15:00" in t for t in texts), str(texts[-1][:80] if texts else "NO"))
    data = read_json(meds_file)
    r.check("قرص کمر با ساعت 15:00 در فایل ذخیره شد", {"name": "قرص کمر", "times": ["15:00"]} in data.get("811", []), str(data.get("811")))

    # ۲) «08:00, 15:00» → دو ساعت (پشتیبانی چندساعت حفظ شود)
    texts = await flow_add_med(812, "قرص کمر", "08:00, 15:00")
    r.check("قرص کمر + 08:00, 15:00 → دو ساعت", any("08:00" in t and "15:00" in t for t in texts), str(texts[-1][:80] if texts else "NO"))
    data = read_json(meds_file)
    r.check("دو ساعت در فایل ذخیره شد", data.get("812", [{}])[0].get("times") == ["08:00", "15:00"], str(data.get("812")))

    # ۳) «25:90» → رد ورودی + پیام اعتبارسنجی روشن (بدون crash)
    texts = await flow_add_med(813, "قرص کمر", "25:90")
    r.check("25:90 → رد با پیام روشن (نه خطای غیرمنتظره)", any("ساعت" in t for t in texts) and not any("غیرمنتظره" in t for t in texts), str(texts[-1][:80] if texts else "NO"))
    # بعد از رد، ورودی معتبر پذیرفته می‌شود (حالت گفتگو حفظ شده)
    REC.reset()
    await process(make_text_update(813, "15:00"))
    texts = REC.sent_texts()
    r.check("پس از رد، 15:00 پذیرفته می‌شود", any("15:00" in t for t in texts), str(texts[-1][:60] if texts else "NO"))

    # ۴) ساعت خالی/فاصله → راهنما، بدون crash
    texts = await flow_add_med(814, "قرص کمر", "   ")
    r.check("ورودی خالی → پیام راهنما بدون crash", any("ساعت" in t for t in texts) and not any("غیرمنتظره" in t for t in texts), str(texts[-1][:80] if texts else "NO"))

    # ۵) شکست زمان‌بندی/ذخیره → بدون پیام موفقیت کاذب (پوشش پایین‌تر هم هست)

    # حذف فقط همان دارو (بخش H)
    write_json(meds_file, {str(uid): [
        {"name": "قرص فشار", "times": ["06:00", "20:00"]},
        {"name": "قرص آهن", "times": ["13:00"]},
    ]})
    REC.reset()
    await process(make_cb_update(uid, "med_del_0"))
    data = read_json(meds_file)
    remaining = data.get(str(uid), [])
    r.check("حذف index 0 → فقط قرص فشار حذف شد", len(remaining) == 1 and remaining[0]["name"] == "قرص آهن", str(remaining))

    # بازسازی بعد از ری‌استارت (schedule_all از فایل)
    jq = FakeJobQueue()
    meds.schedule_all(type("A", (), {"job_queue": jq, "user_data": {}, "bot_data": {}})())
    names = [j.d["name"] for j in jq.jobs_list]
    r.check("بازسازی پس از ری‌استارت: یادآورهای همه کاربران زمان‌بندی شد", len(names) >= 1, str(names))
    times_seen = {j.d["time"] for j in jq.jobs_list}
    r.check("ساعت job شامل 13:00", any("13:00" in t for t in times_seen), str(times_seen))

    # حذف دارو → فقط jobهای همان کاربر حذف می‌شود
    jq2 = FakeJobQueue()
    meds.schedule_chat_jobs(jq2, uid, [{"name": "قرص آهن", "times": ["13:00"]}])
    meds.schedule_chat_jobs(jq2, 999, [{"name": "دارو کاربر دیگر", "times": ["14:00"]}])
    before = len(jq2.jobs_list)
    meds.unschedule_chat(jq2, uid)
    remaining_jobs = [j for j in jq2.jobs_list if not j.removed]
    r.check("unschedule فقط jobهای همان chat را حذف می‌کند", before == 2 and len(remaining_jobs) == 1 and remaining_jobs[0].d["chat_id"] == 999, f"before={before} remaining={len(remaining_jobs)}")

    # ── نبود JobQueue → پیام صریح به کاربر (بخش H) ──
    # (اپ واقعی PTB[job-queue] دارد؛ برای شبیه‌سازی نبودِ JobQueue، زمان‌بند را خراب می‌کنیم —
    #  همان مسیر «شکست زمان‌بندی» است که باید به کاربر صریح گفته شود)
    if os.path.isfile(meds_file):
        os.remove(meds_file)
    orig_sched = meds.schedule_chat_jobs
    def _boom(*a, **k):
        raise RuntimeError("simulated: no JobQueue")
    meds.schedule_chat_jobs = _boom
    uid = 802
    try:
        REC.reset()
        await process(make_start_update(uid, "/start"))
        await process(make_cb_update(uid, "lang_fa"))
        await process(make_cb_update(uid, "medication"))
        await process(make_cb_update(uid, "med_add"))
        await process(make_text_update(uid, "قرص تست"))
        await process(make_text_update(uid, "9:00"))
    finally:
        meds.schedule_chat_jobs = orig_sched
    texts = REC.sent_texts()
    r.check("شکست زمان‌بندی → پیام «ذخیره شد ولی یادآور فعال نشد» به کاربر", any("یادآور خودکار" in t and "فعال نشد" in t for t in texts), str(texts[-1][:80] if texts else "NO"))
    data = read_json(meds_file)
    r.check("با این حال دارو ذخیره شده", data[str(uid)][0]["name"] == "قرص تست")

    # ── فایل خراب → قرنطینه، نه پاک‌سازی ──
    with open(meds_file, "w", encoding="utf-8") as fh:
        fh.write("{corrupted")
    loaded = meds._load_meds()
    r.check("فایل خراب → {} برمی‌گردد", loaded == {})
    quarantined = [f for f in os.listdir(os.path.dirname(meds_file)) if f.startswith("medications.json.corrupt-")]
    r.check("فایل خراب قرنطینه شد (حفظ برای بازیابی دستی)", len(quarantined) >= 1, str(quarantined))
    for f in quarantined:
        os.remove(os.path.join(os.path.dirname(meds_file), f))

    # ── ۳.۱۸: سه‌زبانه بودن پیام یادآور ──
    for lang, word in (("fa", "زمان مصرف"), ("en", "time to take"), ("ar", "حان وقت")):
        txt = meds._t(lang, "reminder").format(name="X")
        r.check(f"پیام یادآور {lang}", word in txt, txt[:50])

    # ── 🐛 رگرسیون v49 (کرش واقعی لیارا ۱۴۰۴/۰۸/۰۸): داده‌ی قدیمی روی دیسک
    # پایدار باعث «یه خطای غیرمنتظره» هنگام ثبت ساعت می‌شد. سه حالت اثبات‌شده
    # با ردگیری کامل: مقدار چت=dict، لیست رشته‌ای، بایت غیر UTF-8. ──
    async def flow_add_med_direct(user, med_name, time_text):
        REC.reset()
        await process(make_cb_update(user, "medication"))
        await process(make_cb_update(user, "med_add"))
        await process(make_text_update(user, med_name))
        await process(make_text_update(user, time_text))
        return REC.sent_texts()

    # ۱) مقدار چت = دیکشنری تکی‌دارو (اسکیمای قدیمی) → باید بازیابی و ثبت موفق شود
    write_json(meds_file, {"871": {"name": "داروی قدیمی", "time": "08:00"}})
    texts = await flow_add_med_direct(871, "قرص کمر", "21:43")
    r.check("داده قدیمی dict → ثبت 21:43 موفق بدون خطای غیرمنتظره",
            any("21:43" in t for t in texts) and not any("غیرمنتظره" in t for t in texts),
            str(texts[-1][:70] if texts else "NO"))
    data = read_json(meds_file)
    names = [m.get("name") for m in data.get("871", [])]
    r.check("داده قدیمی dict بازیابی شد (حفظ داروی کاربر)", "داروی قدیمی" in names, str(names))
    r.check("فایل بعد از نوشتن خودترمیم شد (اسکیمای استاندارد)",
            all(isinstance(m, dict) and isinstance(m.get("times"), list) for m in data.get("871", [])),
            str(data.get("871"))[:120])

    # ۲) مقدار چت = لیست رشته‌های ساده → ثبت موفق، عضو خراب با لاگ امن حذف
    write_json(meds_file, {"872": ["رشته قدیمی بی‌ساختار"]})
    texts = await flow_add_med_direct(872, "قرص کمر", "21:45")
    r.check("داده قدیمی لیست رشته‌ای → ثبت 21:45 موفق بدون خطای غیرمنتظره",
            any("21:45" in t for t in texts) and not any("غیرمنتظره" in t for t in texts),
            str(texts[-1][:70] if texts else "NO"))
    data = read_json(meds_file)
    r.check("عضو رشته‌ای حذف و فقط داروی معتبر ماند",
            data.get("872") == [{"name": "قرص کمر", "times": ["21:45"]}], str(data.get("872")))

    # ۳) فایل با بایت غیر UTF-8 → قرنطینه + ثبت موفق (قبلاً حتی منو کرش می‌کرد)
    with open(meds_file, "wb") as f:
        f.write(b'{"873": [{"name": "\xf9\x84", "times": ["08:00"]}]}')
    texts = await flow_add_med_direct(873, "قرص کمر", "15:00")
    r.check("بایت غیر UTF-8 → قرنطینه + ثبت موفق بدون خطای غیرمنتظره",
            any("15:00" in t for t in texts) and not any("غیرمنتظره" in t for t in texts),
            str(texts[-1][:70] if texts else "NO"))
    quar = [f for f in os.listdir(os.path.dirname(meds_file)) if f.startswith("medications.json.corrupt-")]
    r.check("فایل UTF-8 خراب قرنطینه شد", len(quar) >= 1, str(quar))
    for f in quar:
        os.remove(os.path.join(os.path.dirname(meds_file), f))

    # ۴) شکست واقعی ذخیره‌سازی → پیام صادقانه «ذخیره نشد»، نه موفقیت کاذب
    write_json(meds_file, {"874": []})
    orig_save = meds._save_meds

    def _boom(_data):
        raise OSError("simulated disk failure")
    meds._save_meds = _boom
    try:
        texts = await flow_add_med_direct(874, "قرص کمر", "15:00")
    finally:
        meds._save_meds = orig_save
    r.check("شکست دیسک → پیام صریح «ذخیره نشد» (بدون موفقیت کاذب)",
            any("ذخیره" in t and "نش" in t for t in texts) and not any("فعال شد" in t for t in texts),
            str(texts[-1][:70] if texts else "NO"))

    # ۵) تک‌ساعت واقعی کاربر مثل 21:43 و 21:45 معتبر است (سناریوی گزارش)
    r.check("parse_times('21:43') == ['21:43']", meds.parse_times("21:43") == ["21:43"])
    r.check("parse_times('21:45') == ['21:45']", meds.parse_times("21:45") == ["21:45"])
    r.check("parse_times('15:00') == ['15:00']", meds.parse_times("15:00") == ["15:00"])

    # ۶) حریم خصوصی لاگ: در شکست ذخیره، نام دارو در لاگ نمی‌رود
    import io as _io
    import logging as _logging
    _buf = _io.StringIO()
    _h = _logging.StreamHandler(_buf)
    _meds_logger = _logging.getLogger("app.handlers.meds")
    _meds_logger.addHandler(_h)
    meds._save_meds = _boom
    try:
        await flow_add_med_direct(875, "قرص محرمانه تست", "15:00")
    finally:
        meds._save_meds = orig_save
        _meds_logger.removeHandler(_h)
    _logtext = _buf.getvalue()
    r.check("لاگ شکست ذخیره بدون نام دارو (حریم خصوصی داده سلامتی)",
            "قرص محرمانه تست" not in _logtext and "meds save failed" in _logtext,
            _logtext[:150])

    return r.finish("T08 meds")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
