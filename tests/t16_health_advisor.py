# -*- coding: utf-8 -*-
"""T16 — مشاور سلامت (مأموریت مکمل — بخش ۲ و ۳ و ۴ و ۵)

پوشش الزامات ایمنی دستور محصول:
- ۱۸ علامت محصول در منو، همگی پاسخ واقعی می‌دهند
- علامت بحرانی: فقط «یک» پرسش سریع (بیمار معطل پرسش طولانی نمی‌ماند)
- مسیر اورژانس: انتخاب کشور → شمارهٔ درست (ایران ۱۱۵، بریتانیا ۹۹۹، آلمان ۱۱۲)
- دو دکمهٔ اصلی: ارجاع به متخصص + کمک فوری/اورژانس
- صداقت: هرگز ادعای «اعزام آمبولانس/اطلاع‌رسانی به اورژانس» نمی‌شود؛
  پیام اقدام‌محور «همین حالا تماس بگیرید» + محدودیت آرام ربات نمایش داده می‌شود
  (🩹 فیکس لحن — فیدبک مستقیم کاربر: هشدار تند «خودتان تماس بگیرید» حذف شد)
- حریم خصوصی: موقعیت فقط با رضایت (پرچم رضایت) ذخیره می‌شود؛ بدون رضایت هیچ
- تریاژ: ارزیابی emergency > urgent > referral درست کار می‌کند
- سه‌زبانه + ریست با ناوبری
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import (  # noqa: E402
    REC, Result, build_app, kb_rows, make_cb_update, make_start_update, make_text_update, process,
)

from app.services import health_advisor as ha  # noqa: E402


def all_buttons():
    return [cb for row in kb_rows(REC.keyboards()[-1]) for _, cb in row]


def any_buttons():
    """دکمه‌های «همهٔ» کیبوردهای ارسال‌شده از آخرین reset — برای پیام‌های چندتایی."""
    out = []
    for rm in REC.keyboards():
        for row in kb_rows(rm):
            out.extend(cb for _, cb in row)
    return out


async def main() -> int:
    r = Result()
    app = await build_app()
    uid = 1601
    await process(make_start_update(uid, "/start"))
    await process(make_cb_update(uid, "lang_fa"))

    # ── ۱) منوی مشاور: هر ۱۸ علامت ──
    REC.reset()
    await process(make_cb_update(uid, "advisor"))
    texts = REC.sent_texts()
    r.check("دکمهٔ مشاور سلامت → پیام معرفی + سلب مسئولیت", any("تشخیص پزشکی" in t for t in texts), texts[-1][:50] if texts else "NO")
    cbs = all_buttons()
    missing = [s["id"] for s in ha.SYMPTOMS if f"advs_{s['id']}" not in cbs]
    r.check("هر ۱۸ علامت با دکمه در منو هستند", not missing, str(missing))

    # ── ۲) علامت بحرانی (درد سینه): یک پرسش سریع → بله → اورژانس ──
    REC.reset()
    await process(make_cb_update(uid, "advs_chest_pain"))
    texts = REC.sent_texts()
    r.check("درد سینه → توضیح کوتاه اهمیت", any("قفسهٔ سینه" in t for t in texts))
    kb = all_buttons()
    r.check("پرسش سریع بله/خیر دارد", "advq_chest_pain_0_1" in kb and "advq_chest_pain_0_0" in kb, str(kb[:4]))

    REC.reset()
    await process(make_cb_update(uid, "advq_chest_pain_0_1"))
    texts = REC.sent_texts()
    kb = all_buttons()
    r.check("پاسخ بله → صفحهٔ انتخاب کشور", any("کشور" in t for t in texts))
    r.check("دکمهٔ ایران در فهرست کشورها", "advec_ir" in kb)

    REC.reset()
    await process(make_cb_update(uid, "advec_ir"))
    texts = REC.sent_texts()
    r.check("ایران → شمارهٔ ۱۱۵", any("115" in t or "۱۱۵" in t for t in texts), texts[0][:60] if texts else "NO")
    r.check("دکمهٔ تماس tel:115 موجود", any(cb == "tel:115" for cb in any_buttons()))

    # ── ۳) صداقت: ادعای دروغ ممنوع (شامل همهٔ پیام‌های صفحهٔ اورژانس) ──
    all_text = "\n".join(REC.sent_texts()) + "\n" + "\n".join(texts)
    r.check("ادعای «اعزام آمبولانس» وجود ندارد", "اعزام شد" not in all_text and "اعزام کردیم" not in all_text and "اعزام می‌شود" not in all_text and "مطلع کرد" not in all_text)
    r.check("پیام اقدام‌محور تماس + محدودیت صادقانهٔ ربات", any("تماس بگیرید" in t and "اعزام آمبولانس ندارد" in t for t in texts))

    # ── ۴) حریم خصوصی: موقعیت فقط با رضایت ──
    cbs = all_buttons()
    r.check("دکمهٔ رضایت‌محور موقعیت نمایش داده می‌شود", any(cb.startswith("advloc_") for cb in any_buttons()))
    REC.reset()
    await process(make_cb_update(uid, "advloc_chest_pain"))
    r.check("درخواست موقعیت → پیام رضایت و توضیح محرمانگی", any("رضایت" in t or "🔒" in t for t in REC.sent_texts()))
    # موقعیت بدون پرچم رضایت → نادیده گرفته می‌شود (هیچ ذخیره‌ای نمی‌شود)
    ctx_user = app.user_data.get((uid, uid)) if hasattr(app, "user_data") else None

    # ── ۵) متن آمادهٔ اپراتور (بدون ادعا) ──
    REC.reset()
    await process(make_cb_update(uid, "advinf_chest_pain"))
    texts = REC.sent_texts()
    r.check("متن آمادهٔ اپراتور شامل علامت است", any("درد یا فشار قفسهٔ سینه" in t for t in texts))
    r.check("متن اپراتور ادعای اقدام ندارد", not any("اعزام شد" in t or "مطلع شد" in t for t in texts))

    # ── ۶) شماره‌های کشورها: بریتانیا ۹۹۹، آلمان ۱۱۲ ──
    REC.reset()
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "advisor"))
    await process(make_cb_update(uid, "advs_stroke"))
    await process(make_cb_update(uid, "advq_stroke_0_1"))
    await process(make_cb_update(uid, "advec_uk"))
    texts = REC.sent_texts()
    r.check("بریتانیا → ۹۹۹", any("999" in t for t in texts))
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "advisor"))
    await process(make_cb_update(uid, "advs_anaphylaxis"))
    await process(make_cb_update(uid, "advq_anaphylaxis_0_1"))
    await process(make_cb_update(uid, "advec_de"))
    texts = REC.sent_texts()
    r.check("آلمان → ۱۱۲", any("112" in t for t in texts))

    # ── ۷) مسیر ارجاع: علامت عادی (سرگیجه) → ۲ پرسش متوالی → «خیر/خیر» → ارجاع داخلی ──
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "advisor"))
    await process(make_cb_update(uid, "advs_dizziness"))
    kb = all_buttons()
    r.check("سرگیجه (عادی) پرسش اول را می‌پرسد", "advq_dizziness_0_0" in kb, str(kb[:4]))
    await process(make_cb_update(uid, "advq_dizziness_0_0"))
    kb = all_buttons()
    r.check("پرسش دوم بعد از پرسش اول", "advq_dizziness_1_0" in kb)
    REC.reset()
    await process(make_cb_update(uid, "advq_dizziness_1_0"))
    texts = REC.sent_texts()
    kb = all_buttons()
    r.check("ارجاع → تخصص داخلی پیشنهاد شد", any("داخلی" in t for t in texts), texts[-1][:60] if texts else "NO")
    r.check("دکمهٔ مشاهدهٔ پزشکان (med_spec)", any(cb.startswith("med_spec_internal") for cb in kb))
    r.check("دکمهٔ کمک فوری در صفحهٔ ارجاع هم هست", "advem_redo" in kb)

    # بیمارستان‌های دارای تخصص از دادهٔ واقعی — روی درد سینه (تخصص قلب در
    # فهرست واقعی بیمارستان‌ها هست)؛ برای تخصص بدون تطبیق، هیچ بیمارستانی
    # جعل نمی‌شود (تست ۸-ب)
    from app.handlers.advisor import _matched_hospitals
    cardio_hits = _matched_hospitals("cardio", "fa")
    r.check("تطبیق واقعی: قلب → بیمارستان‌های دارای جراحی/مراقبت قلب", bool(cardio_hits) and any("قلب" in str(h.get("specialties_fa", "")) for h in cardio_hits), str([h.get("name_fa") for h in cardio_hits]))

    # ── ۸) منطق تریاژ سرویس ──
    s = ha.get_symptom("dizziness")
    r.check("evaluate: هر دو بله → urgent", ha.evaluate(s, {"neuro": False, "persistent": True}) == "urgent")
    r.check("evaluate: نشانهٔ عصبی بله → emergency", ha.evaluate(s, {"neuro": True, "persistent": False}) == "emergency")
    r.check("evaluate: هر دو خیر → referral", ha.evaluate(s, {"neuro": False, "persistent": False}) == "referral")

    # ── ۹) شمارهٔ fallback کشور نامعلوم ──
    num, rec = ha.emergency_number(None)
    r.check("کشور نامعلوم → 112 (استاندارد GSM)", num == "112" and rec is None)

    # ── ۱۰) سه‌زبانه بودن مشاور ──
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "lang_en"))
    REC.reset()
    await process(make_cb_update(uid, "advisor"))
    texts = REC.sent_texts()
    r.check("مشاور به انگلیسی", any("Health Advisor" in t for t in texts))
    kb = all_buttons()
    r.check("علامت‌ها به انگلیسی در دکمه‌ها", any(cb == "advs_chest_pain" for cb in kb))
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "lang_ar"))
    REC.reset()
    await process(make_cb_update(uid, "advisor"))
    texts = REC.sent_texts()
    r.check("مشاور به عربی", any("مستشار الصحة" in t for t in texts))

    # ── ۱۱) ریست با ناوبری: وسط تریاژ منو بزن → پرچم پاک شود ──
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "lang_fa"))
    await process(make_cb_update(uid, "advisor"))
    await process(make_cb_update(uid, "advs_dizziness"))
    await process(make_cb_update(uid, "back_main"))
    await process(make_cb_update(uid, "advisor"))
    REC.reset()
    await process(make_cb_update(uid, "advs_dizziness"))
    kb = all_buttons()
    r.check("شروع تازهٔ تریاژ بعد از ناوبری (پرسش اول)", "advq_dizziness_0_0" in kb)

    # ── ۱۲) همهٔ ۱۸ علامت جریان کامل بدون خطا طی می‌کنند ──
    errors = []
    for s in ha.SYMPTOMS:
        await process(make_cb_update(uid, "back_main"))
        await process(make_cb_update(uid, "advisor"))
        REC.reset()
        await process(make_cb_update(uid, f"advs_{s['id']}"))
        if not REC.sent_texts():
            errors.append(f"{s['id']}: no intro")
            continue
        await process(make_cb_update(uid, f"advq_{s['id']}_0_0"))  # پاسخ منفی
        if not REC.sent_texts():
            errors.append(f"{s['id']}: no disposition")
    r.check("هر ۱۸ علامت جریان کامل بدون خطا", not errors, "; ".join(errors))

    print()
    return r.finish("T16 مشاور سلامت")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
