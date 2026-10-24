# 🏥 شیراز مدیکال — ربات گردشگری سلامت (بله / تلگرام)

پلتفرم جامع گردشگری سلامت شیراز: رزرو نوبت پزشک از بین **۱۱۴ پزشک واقعی در ۵۰ تخصص**، پرداخت آنلاین زرین‌پال با تأیید خودکار، رسید PDF فارسی، همراه بیمار، نظرسنجی، اطلاعات بیمارستان‌ها/هتل‌ها/بیمه‌ها/پایانه‌ها و بخش گردشگری — با پشتیبانی سه‌زبانه (فارسی/انگلیسی/عربی).

## 🏗️ معماری

~~~
main.py                    → نقطه‌ی ورود (polling بله)
config.py                  → تنظیمات از env (بدون هاردکد توکن)
app/
  bot.py                   → ساخت اپلیکیشن + post_init (پل runtime)
  runtime.py               → 🆕 پل event loop بین سرور health و ربات
  health.py                → سرور HTTP لیارا: health-check + callback زرین‌پال
  handlers/
    start.py               → /start، انتخاب زبان، منوی اصلی
    booking.py             → 🆕 رزرو واقعی: تخصص ← پزشک ← تاریخ شمسی ← ساعت ← پرداخت
    callbacks.py           → دکمه‌های منو + مرور پزشکان + نمایش داده‌ها
    companion.py           → ثبت همراه بیمار
    survey.py              → نظرسنجی رضایت
  services/
    doctor_loader.py       → 🆕 لود ۵۰ تخصص و ۱۱۴ پزشک از data/doctors (کش mtime)
    booking.py             → اسلات‌ها (per-doctor) + تاریخ شمسی + ذخیره‌ی اتمیک
    payment.py             → زرین‌پال request/verify
    receipt.py             → رسید متن + PDF فارسی (arabic_reshaper + bidi)
app/locales/               → fa / en / ar
data/
  doctors/*.json           → ۵۰ فایل تخصص (روزانه با GitHub Actions آپدیت می‌شود)
  ...
~~~

## 🚀 راه‌اندازی محلی

~~~bash
pip install -r requirements.txt
export BALE_BOT_TOKEN="توکن-ربات-بله"        # یا TELEGRAM_BOT_TOKEN
export ZARINPAL_MERCHANT_ID="..."            # مرچنت زرین‌پال
export ZARINPAL_SANDBOX="true"               # برای تست true
export ADMIN_CHAT_ID="1967087863"            # آیدی عددی ادمین
export PUBLIC_BASE_URL="https://shirazmedical.iran.liara.run"  # دامنه‌ی عمومی اپ
python main.py
~~~

## 💳 جریان پرداخت (تأیید کامل خودکار)

1. کاربر نوبت را رزرو می‌کند → نوبت `pending` (۱۵ دقیقه اعتبار)
2. لینک زرین‌پال ساخته می‌شود با `callback_url = {PUBLIC_BASE_URL}/payment/callback?user_id=X`
3. کاربر پرداخت می‌کند → زرین‌پال کاربر را به همان آدرس برمی‌گرداند
4. سرور `health.py`:
   - `Status=OK` → **verify نزد زرین‌پال** → نوبت `paid` → پیام موفقیت + رسید متن + PDF به کاربر
   - `Status=NOK` → آزادسازی اسلات + پیام «پرداخت ناموفق»
5. صفحه‌ی HTML فارسی (راست‌به‌چپ) نتیجه را به کاربر نشان می‌دهد

> ⚠️ مهم: متغیر `PUBLIC_BASE_URL` باید دامنه‌ی عمومی اپ روی لیارا باشد تا callback کار کند. دامنه‌ی پیش‌فرض `https://shirazmedical.iran.liara.run` است.

## ⚙️ متغیرهای محیطی

| متغیر | الزامی | توضیح |
|---|---|---|
| `BALE_BOT_TOKEN` | یکی از دو توکن | توکن ربات بله (اولویت‌دار) |
| `TELEGRAM_BOT_TOKEN` | یکی از دو توکن | توکن ربات تلگرام |
| `ZARINPAL_MERCHANT_ID` | برای پرداخت | مرچنت آی‌دی زرین‌پال |
| `ZARINPAL_SANDBOX` | خیر | پیش‌فرض `true` (محیط تست) |
| `ADMIN_CHAT_ID` | توصیه‌شده | آیدی عددی ادمین برای دریافت نارضایتی‌ها |
| `PUBLIC_BASE_URL` | برای پرداخت | دامنه‌ی عمومی اپ (لیارا) |
| `BOT_USERNAME` | خیر | پیش‌فرض `ShirazMedBot` |
| `TIMEZONE_OFFSET_HOURS` | خیر | پیش‌فرض `3.5` (ایران) |

## 🩺 دیپلوی روی لیارا

- `liara.json`: اپ `shirazmedical` + دیسک `data` روی `/app/data`
- با هر push به `main`، GitHub Actions خودکار دیپلوی می‌کند (`.github/workflows/liara.yml`)
- هر روز ساعت ۶:۳۰ صبح تهران، `collect.py` داده‌ی پزشکان را آپدیت می‌کند (`.github/workflows/collect.yml`)

## 📋 تاریخچه فیکس‌ها (v47)

| # | فیکس | فایل |
|---|---|---|
| ۱ | دکمه‌ی مرده‌ی «راهنمای ثبت شکایت» (`complaints_menu` هندل نمی‌شد) | bot.py |
| ۲ | Markdown نامعتبر `**bold**` → بخش «همراه بیمار»، «مترجم» و پیام ادمین کار نمی‌کرد | companion.py, callbacks.py, survey.py |
| ۳ | **پرداخت بدون verify** — کاربر پول می‌داد و نوبتش بعد از ۱۵ دقیقه حذف می‌شد؛ حالا callback کامل زرین‌پال | health.py, runtime.py, bot.py |
| ۴ | رسید PDF قبل از پرداخت ارسال می‌شد → حالا فقط بعد از verify | booking.py, health.py |
| ۵ | حروف فارسی PDF جدا و معکوس بود → arabic_reshaper + python-bidi | receipt.py |
| ۶ | همه‌ی PDFها با نام `receipt_receipt.pdf` روی هم ذخیره می‌شدند | receipt.py |
| ۷ | رزرو فقط ۳ پزشک ساختگی بود → حالا ۱۱۴ پزشک واقعی با تخصص‌ها | booking.py, doctor_loader.py |
| ۸ | تاریخ‌های میلادی → شمسی با نام روز | booking.py (service) |
| ۹ | رزرو یک پزشک، همان ساعت را برای بقیه می‌بست → اسلات per-doctor | booking.py (service) |
| ۱۰ | ساعت سرور UTC بود → اختلاف نیم‌روزی در اسلات‌ها | booking.py (service) |
| ۱۱ | هاردکد `ADMIN_CHAT_ID` در survey | survey.py |
| ۱۲ | `getattr(settings, "BOT_USERNAME")` غلط املایی | booking.py |
| ۱۳ | fallback نظرسنجی هر متنی را علت نارضایتی ثبت می‌کرد | survey.py |
| ۱۴ | ارسال ده‌ها پیام جدا (flood) → ادغام پیام‌ها + مکث بین ارسال | callbacks.py |
| ۱۵ | دکمه‌های «پزشکی» و «پکیج کامل» مرده بودند | callbacks.py |
| ۱۶ | فرآیند همراه دکمه‌ی لغو نداشت | companion.py |
| ۱۷ | فایل placeholder `assets` جلوی ساخت پوشه‌ی فونت را می‌گرفت | receipt.py |