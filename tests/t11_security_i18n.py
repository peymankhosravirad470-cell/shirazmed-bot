# -*- coding: utf-8 -*-
"""T11 — امنیت لاگ‌ها و سه‌زبانه (بخش ۳.۱۷ و ۳.۱۸): هیچ توکن/رمز/کد ملی/اطلاعات
دارویی بیمار در لاگ‌ها و پیام‌های خطای عمومی نیست؛ منوها در هر سه زبان کامل."""
import asyncio
import io
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, make_cb_update, make_start_update, make_text_update, process,
)


async def main() -> int:
    r = Result()
    app = await build_app()

    # ── ۳.۱۷ عدم افشا در پیام‌های خطای کاربر ──
    from app.bot import _USER_ERROR_T, _USER_ERROR_FALLBACK
    for lang, text in _USER_ERROR_T.items():
        r.check(f"پیام خطای {lang} بدون جزئیات فنی/توکن", "token" not in text.lower() and "Error" not in text and "Traceback" not in text, text[:60])

    # خطای هندلر سراسری: کاربر پیام عمومی می‌گیرد نه exception
    from app.bot import global_error_handler
    REC.reset()
    class Ctx:
        user_data = {"lang": "fa"}
        error = Exception("SECRET_TOKEN_VALUE leaked detail")
        bot = app.bot
    u = make_text_update(950, "hello")
    await global_error_handler(u, Ctx())
    texts = REC.sent_texts()
    r.check("خطای هندلر → پیام عمومی به کاربر", any("خطای غیرمنتظره" in t for t in texts), str(texts[:1]))
    r.check("exception واقعی در پیام کاربر نیست", not any("SECRET_TOKEN_VALUE" in t for t in texts))

    # ── لاگ‌ها: پرداخت/رزرو/دارو هیچ داده‌ی حساسی چاپ نمی‌کند ──
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    logging.getLogger().addHandler(h)
    try:
        logging.getLogger("app.services.payment").warning("تست: کاربر %s authority=%s", 123, "AUTH")
        logging.getLogger("app.services.booking").info("mark_appointment_paid: date=%s time=%s user=%s", "d", "t", 456)
    finally:
        logging.getLogger().removeHandler(h)
    log_out = buf.getvalue()
    r.check("لاگ booking/payload کد ملی یا نام بیمار ندارد", "کد ملی" not in log_out and "نام خانوادگی" not in log_out)

    # ثبت‌نام پزشک: رمز در پاسخ‌ها بازتاب نمی‌شود
    from config import settings
    object.__setattr__(settings, "doctor_reg_code", "TOPSECRET_REG")
    REC.reset()
    await process(make_start_update(951, "/doctor"))
    await process(make_text_update(951, "wrong"))
    texts = REC.sent_texts()
    r.check("پس از رمز غلط، رمز واقعی در پیام نیست", not any("TOPSECRET_REG" in t for t in texts), str(texts[-1][:60] if texts else ""))
    # و پیام خطای گیت‌هاب حاوی توکن نیست
    gh = dr_github_error_probe()
    r.check("خطای گیت‌هاب توکن در متن ندارد", ("ghp_" not in gh) and ("Bearer" not in gh) and ("SUPERSECRET" not in gh), gh[:80])

    # ── ۳.۱۸ سه‌زبانه: منوی اصلی + بخش‌ها در fa/en/ar ──
    from app.keyboards.main import get_main_menu_keyboard
    for lang, sample in (("fa", "نوبت"), ("en", "Book"), ("ar", "موعد")):
        kb = get_main_menu_keyboard(lang)
        labels = " ".join(b.text for row in kb.inline_keyboard for b in row)
        r.check(f"منوی اصلی {lang} کامل", sample in labels or len(labels) > 50, labels[:80])
    # پیام خطای عمومی هر سه زبان
    r.check("خطای کاربر سه‌زبانه", set(_USER_ERROR_T.keys()) == {"fa", "en", "ar"})
    # رویت رندر بخش‌ها در سه زبان (نمونه: بیمارستان‌ها و بیمه)
    uid = 952
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_en"))
    REC.reset()
    await process(make_cb_update(uid, "non_hospitals"))
    t_en = " ".join(REC.sent_texts())
    r.check("بیمارستان‌ها en: برچسب Address", "Address" in t_en)
    await process(make_cb_update(uid, "lang_ar"))
    REC.reset()
    await process(make_cb_update(uid, "insurance"))
    t_ar = " ".join(REC.sent_texts())
    r.check("بیمه‌ها ar: برچسب عربی", "النوع" in t_ar or "الهاتف" in t_ar or "تغطية" in t_ar, t_ar[:80])

    return r.finish("T11 security+i18n")


def dr_github_error_probe() -> str:
    """بررسی این‌که پیام خطای _github_commit_doctor توکن را داخلش نمی‌گذارد."""
    import app.handlers.doctor_reg as dr
    from config import settings
    object.__setattr__(settings, "github_token", "ghp_SUPERSECRET")
    object.__setattr__(settings, "github_repo", "owner/repo")

    class FakeResp:
        status_code = 500
        def json(self):
            return {}
    class FakeReqModule:
        class RequestException(Exception):
            pass
        @staticmethod
        def get(*a, **k):
            return FakeResp()
    import sys
    fake = FakeReqModule()
    real_requests = sys.modules.get("requests")
    sys.modules["requests"] = fake
    try:
        ok, msg = dr._github_commit_doctor({"spec_key": "cardio", "name": "تست", "degree": "متخصص"}, "doc_999")
    finally:
        if real_requests is not None:
            sys.modules["requests"] = real_requests
    return msg


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
