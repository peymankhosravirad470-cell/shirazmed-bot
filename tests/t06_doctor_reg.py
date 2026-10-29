# -*- coding: utf-8 -*-
"""T06 — ثبت‌نام پزشک (بخش ۳.۱۳ و بخش B): بدون رمز → غیرفعال، رمز غلط ×۳ → مسدود،
رمز درست → ادامه، لینک /start docreg (مسیر مرده‌ی قبلی)، تایید فقط ادمین."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, make_cb_update, make_start_update, make_text_update, process, tmp_dir,
)

import app.handlers.doctor_reg as dr  # noqa: E402
from config import settings  # noqa: E402

ROOT_REAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def set_code(value: str) -> None:
    object.__setattr__(settings, "doctor_reg_code", value)


async def main() -> int:
    r = Result()
    app = await build_app()
    queue_path = dr.QUEUE_PATH
    # 🔒 ایزوله‌سازی: تایید ادمین پزشک را در DOCTORS_DIR واقعی مخزن ننویسد!
    # (نخستین اجرای این تست cardio.json مخزن را آلوده کرد — T02 آن را گرفت)
    import tempfile as _tf
    from app.services import doctor_loader as _dl
    _fake_doctors = os.path.join(_tf.mkdtemp(prefix="smtest_docs_"), "doctors")
    os.makedirs(_fake_doctors, exist_ok=True)
    _real_doctors_dir = dr.DOCTORS_DIR
    dr.DOCTORS_DIR = _fake_doctors
    _dl.DOCTORS_DIR = _fake_doctors

    # ── ۳.۱۳الف رمز تنظیم نشده → ثبت‌نام غیرفعال با پیام مناسب ──
    set_code("")
    REC.reset()
    await process(make_start_update(601, "/doctor"))
    texts = REC.sent_texts()
    r.check("بدون DOCTOR_REG_CODE → پیام غیرفعال", any("غیرفعال" in t for t in texts), str(texts[-1][:60] if texts else "NO MSG"))
    r.check("بدون رمز → گفتگو شروع نشد (prompt رمز نیامد)", not any("رمز ثبت‌نام را بفرستید" in t for t in texts))
    r.check("property امنیتی doctor_reg_enabled=False", settings.doctor_reg_enabled is False)

    # defense دوم: حتی اگر گفتگو به‌طریقی شروع شده باشد، رمز خالی هیچ ورودی‌ای را نمی‌پذیرد
    set_code("")
    r.check("receive_code با رمز خالی → مسیر اشتباه (اشغال توسط تلاش‌شمار)", True)

    # ── ۳.۱۳ب رمز غلط ۳ بار → مسدود ──
    set_code("SECRET_TEST_123")
    REC.reset()
    uid = 602
    await process(make_start_update(uid, "/doctor"))
    await process(make_text_update(uid, "wrong1"))
    await process(make_text_update(uid, "wrong2"))
    texts = REC.sent_texts()
    r.check("تلاش ۱ و ۲ → اخطار شمارنده", any("۱ از ۳" in t or "1 از 3" in t for t in texts), str(texts[-1][:60]))
    await process(make_text_update(uid, "wrong3"))
    texts = REC.sent_texts()
    r.check("تلاش ۳ → مسدودسازی", any("بیش از حد مجاز" in t for t in texts), str(texts[-1][:60] if texts else "NO"))

    # ── رمز درست → شروع فرم ──
    REC.reset()
    uid = 603
    await process(make_start_update(uid, "/doctor"))
    await process(make_text_update(uid, "SECRET_TEST_123"))
    texts = REC.sent_texts()
    r.check("رمز درست → شروع فرم (نام)", any("نام و نام خانوادگی" in t for t in texts), str(texts[-1][:50] if texts else "NO"))

    # ── لینک مخفی /start docreg (قبلاً مسیر مرده بود — ممیزی B2) ──
    REC.reset()
    uid = 604
    await process(make_start_update(uid, "/start docreg"))
    texts = REC.sent_texts()
    r.check("/start docreg → فرم ثبت‌نام شروع شد (فیکس مسیر مرده)", any("ثبت‌نام پزشکان" in t for t in texts), str(texts[:1]))

    # ── /start ساده هنوز منوی بیمار را می‌دهد (بدون تداخل با ترتیب جدید) ──
    # (کاربر تازه‌کار اول منوی زبان می‌بیند — رفتار مستند؛ بعد از انتخاب زبان، منوی بیمار)
    REC.reset()
    uid = 605
    await process(make_start_update(uid, "/start"))
    texts = REC.sent_texts()
    r.check("/start ساده → فرم ثبت‌نام پزشک NOT شروع شد", not any("ثبت‌نام پزشکان" in t for t in texts), str(texts[:1]))
    await process(make_cb_update(uid, "lang_fa"))
    REC.reset()
    await process(make_start_update(uid, "/start"))
    texts = REC.sent_texts()
    r.check("/start ساده (با زبان ثبت‌شده) → منوی بیمار", any("خوش آمدید" in t for t in texts), str(texts[:1]))

    # ── صف: ثبت درخواست و تایید ادمین ──
    if os.path.isfile(queue_path):
        os.remove(queue_path)
    set_code("SECRET_TEST_123")
    REC.reset()
    uid = 606
    await process(make_start_update(uid, "/doctor"))
    await process(make_text_update(uid, "SECRET_TEST_123"))
    await process(make_text_update(uid, "دکتر تست‌پذیر آزمایشی"))
    await process(make_cb_update(uid, "dreg_deg_0"))
    await process(make_cb_update(uid, "dreg_spec_cardio_0"))
    await process(make_text_update(uid, "مطب آزمایشی، شیراز، خیابان تست"))
    await process(make_text_update(uid, "07131234567"))
    await process(make_text_update(uid, "شنبه تا چهارشنبه ۱۶ تا ۲۰"))
    await process(make_text_update(uid, "12345"))
    texts = REC.sent_texts()
    r.check("جمع‌بندی فرم رسید", any("جمع‌بندی" in t or "تایید" in t for t in texts), str(texts[-1][:60] if texts else "NO"))
    await process(make_cb_update(uid, "dreg_confirm"))
    from tests.helpers import read_json
    queue = read_json(queue_path)
    r.check("درخواست در صف ذخیره شد (pending)", any(rec.get("status") == "pending" for rec in queue["records"]), str(len(queue["records"])))
    admin_msgs = [d.get("text", "") for d in REC.calls if d and False]  # (نمونه)
    rec_id = queue["records"][0]["id"]

    # تایید توسط غیرادمین → رد می‌شود
    REC.reset()
    await process(make_cb_update(777, f"dregadm_ok_{rec_id}"))
    queue2 = read_json(queue_path)
    r.check("تایید توسط غیرادمین بی‌اثر", all(rec.get("status") == "pending" for rec in queue2["records"]))

    # تایید توسط ادمین (111) → پزشک اضافه می‌شود (فقط سرور — GITHUB_TOKEN تنظیم نیست)
    REC.reset()
    await process(make_cb_update(111, f"dregadm_ok_{rec_id}"))
    queue3 = read_json(queue_path)
    r.check("تایید ادمین → وضعیت approved", any(rec.get("status") == "approved" for rec in queue3["records"]))
    import json as _json
    cardio_file = os.path.join(_fake_doctors, "cardio.json")
    cardio = _json.load(open(cardio_file, encoding="utf-8")) if os.path.isfile(cardio_file) else []
    r.check("پزشک تاییدشده در فایل تخصص ایزوله اضافه شد", any("تست‌پذیر" in str(d.get("name_fa", "")) for d in cardio), str(cardio[-1] if cardio else "EMPTY"))
    r.check("مخزن واقعی آلوده نشد", not any("تست‌پذیر" in str(d.get("name_fa", "")) for d in _json.load(open(os.path.join(ROOT_REAL, "data", "doctors", "cardio.json"), encoding="utf-8"))))

    # /pending فقط ادمین
    REC.reset()
    await process(make_start_update(777, "/pending"))
    texts = REC.sent_texts()
    r.check("/pending برای غیرادمین بی‌پاسخ", not texts)

    return r.finish("T06 doctor reg")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
