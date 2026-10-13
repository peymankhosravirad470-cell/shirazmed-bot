import json
import os
import re
import random
import telebot
import requests
import threading
import time as time_module
from datetime import datetime, timedelta
from urllib.parse import quote

try:
    import jdatetime
except ImportError:
    jdatetime = None

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AVALAI_API_KEY = os.environ.get("AVALAI_API_KEY", "")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
AI_MODEL = "gpt-4o-mini"
AVALAI_URL = "https://api.avalai.ir/v1/chat/completions"
CHANNEL_LINK = "https://ble.ir/shiraz_medical"
CHANNEL_DISCOUNT = 5
TIMEZONE_OFFSET_HOURS = float(os.environ.get("TIMEZONE_OFFSET_HOURS", "3.5"))
SNAPP_URL = "https://app.snapp.taxi/"
TAP30_URL = "https://app.tap30.ir/"
AVALAI_STT_URL = "https://api.avalai.ir/v1/audio/transcriptions"
STT_MODEL = "whisper-1"
MAX_VOICE_SECONDS = 60
GOOGLE_TRANSLATE_URL = "https://translate.google.com/"
DEEPSEEK_URL = "https://chat.deepseek.com/"

if BALE_BOT_TOKEN:
    telebot.apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"
    telebot.apihelper.FILE_URL = "https://tapi.bale.ai/file/bot{0}/{1}"
    bot = telebot.TeleBot(BALE_BOT_TOKEN)
else:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

LANG_NAMES = {"fa": "فارسی", "ar": "العربية", "en": "English"}

SYSTEM_PROMPT = "شما دستیار گردشگری سلامت شیراز هستید. کوتاه و با همدلی جواب بده. هرگز تشخیص پزشکی نده، دارو تجویز نکن و قیمت دقیق نگو."

AI_DISCLAIMER = {
    "fa": "\n\n⚠️ این راهنمای اولیه‌ست، نه تشخیص پزشکی.",
    "ar": "\n\n⚠️ هذا توجيه أولي وليس تشخيصاً طبياً.",
    "en": "\n\n⚠️ This is a preliminary guide, not a medical diagnosis."
}

START_MSG = """🌟 سلام و خوش آمدید! از اینکه شیراز مدیکال را انتخاب کردید سپاسگزاریم.
🌟 Welcome! Thank you for choosing Shiraz Medical.
🌟 مرحباً بكم! نشكركم لاختياركم شيراز ميديكال.

زبان خود را انتخاب کنید / Choose your language / اختاروا لغتكم:
1 - فارسی
2 - العربية
3 - English"""

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

user_state = {}
user_lang = {}
user_temp = {}
satisfaction_counter = {"count": 0, "positive": 0, "negative": 0}

MSG = {
    "fa": {
        "welcome": "🌟 یه پیام بدی، همه‌چیز رو آماده می‌کنیم.\n\nاز پزشک تا هتل، از ترانسفر تا مترجم، از نوبت تا گشت گردشگری — همه‌چیز یکجا.\n\nبدون دغدغه، بدون هزینه اضافه 💙\n\n👇 از دکمه‌های زیر انتخاب کن:",
        "welcome_text": "یا خواسته‌ت رو بنویس:\nمثلاً «دکتر قلب» یا «پکیج درمان»",
        "more": "سؤال دیگری دارید؟ (بله / نه)",
        "go": "بفرمایید، سؤالتان را بنویسید.",
        "thanks": "🙏 سپاسگزاریم!\n\nاگر از خدمات ما راضی بودید، لطفاً ما را به دوستان و آشنایان خود معرفی کنید. 🌹",
        "thanks_fb": "ممنون از نظرتان. 🙏",
        "retry": "متأسفم، الان نتوانستم جواب بدهم. دوباره تلاش کنید.",
        "text_only": "لطفاً سؤال خود را به صورت متن بنویسید.",
        "apt_ask": "📅 برای گرفتن نوبت با این پزشک، شماره ۱ را بزنید.\n📞 برای تماس مستقیم، شماره ۲ را بزنید.",
        "apt_pick_title": "👨‍⚕️ پزشکان بالا:",
        "apt_pick_footer": "\n📅 برای گرفتن نوبت، شماره‌ی پزشک مورد نظرت رو بنویس:",
        "apt_name": "👤 لطفاً نام و نام خانوادگی خود را بنویسید:",
        "apt_phone": "📞 لطفاً شماره تماس خود را بنویسید (مثال: 09123456789):",
        "apt_submitted": "✅ درخواست نوبت شما ثبت شد!\n\n📋 کد پیگیری: {id}\n👨‍⚕️ پزشک: {doctor}\n\n⏳ ما با مطب تماس می‌گیریم و سریع‌ترین نوبت موجود رو براتون هماهنگ می‌کنیم.",
        "apt_cancelled": "❌ ثبت نوبت لغو شد.",
        "apt_invalid": "لطفاً یکی از شماره‌های داده شده را بزنید.\n\n🚪 برای خروج: منو",
        "apt_error": "❌ متأسفانه در ثبت نوبت مشکلی پیش آمد.",
        "apt_my": "📋 نوبت‌های شما:",
        "apt_none": "شما هنوز هیچ نوبتی ثبت نکرده‌اید.",
        "apt_confirm_final": "آیا درخواست با این اطلاعات ثبت شود؟ (بله / نه)\n\n👤 نام: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}",
        "apt_admin_new": "📥 درخواست نوبت جدید\n\n📋 کد: {id}\n👤 بیمار: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}\n📞 تلفن مطب: {dphone}\n\n⏳ تأیید:\n/confirm {id} 1405/09/20 10:30\n✅ انجام ویزیت:\n/done {id}",
        "apt_patient_confirmed": "🎉 نوبت شما تأیید شد!\n\n📋 کد: {id}\n👨‍⚕️ پزشک: {doctor}\n📅 تاریخ: {date}\n⏰ ساعت: {time}\n📍 آدرس: {address}",
        "apt_done_admin_ok": "✅ ویزیت {id} علامت خورد. نظرخواهی از بیمار ارسال شد.",
        "apt_done_admin_bad": "❌ نوبت {id} پیدا نشد.",
        "apt_done_patient": "🎊 امیدواریم ویزیت خوب پیش رفته باشه!\n\nلطفاً به ما بگو از خدمات چقدر راضی بودی:",
    },
        "pt_created": "🎫 پرونده‌ی شما ساخته شد\n\n📋 کد پرونده: {code}\n\nهر وقت خواستی ببینی کجای کاریم، بنویس: پرونده",
        "pt_title": "🎫 پرونده‌ی سلامت شما\n━━━━━━━━━━━━━━━",
        "pt_code": "📋 کد پرونده: {code}",
        "pt_name": "👤 نام: {name}",
        "pt_progress": "\n🌟 مسیر شما تا درمان:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "درخواست شما ثبت شد",
        "pt_stages_doctor": "پزشک مشخص شد",
        "pt_stages_date": "تاریخ نوبت نهایی شد",
        "pt_stages_accommodation": "اقامت هماهنگ شد",
        "pt_stages_transport": "حمل‌ونقل هماهنگ شد",
        "pt_stages_treatment": "درمان انجام شد",
        "pt_stages_followup": "پیگیری سلامت",
        "pt_appointments": "\n📅 نوبت‌های شما:",
        "pt_apt_line_pending": "⏳ {id} — {doctor} — در انتظار تعیین تاریخ",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} ساعت {time}",
        "pt_apt_line_done": "🎊 {id} — {doctor} — انجام شده",
        "pt_not_found": "شما هنوز پرونده‌ای ندارید. با اولین نوبت، پرونده‌ی شما ساخته می‌شه 💙",
        "delete_ask": "⚠️ مطمئنی؟ برای تأیید بنویس: بله حذف کن",
        "delete_done": "✅ همه‌ی اطلاعات شما پاک شد.",
        "delete_cancel": "باشه، اطلاعاتت دست‌نخورده موند.",
        "rate_thanks_5": "🌟 وای، ۵ ستاره! خیلی خوشحال شدیم 💙\n\nاگه دوستی داری که به پزشک نیاز داره، لطفاً ما رو بهش معرفی کن. پاداش داری 🎁",
        "rate_thanks_4": "😊 ممنون از امتیاز ۴ ستاره!\n\nاگه دوستی داری که به پزشک نیاز داره، ما رو بهش معرفی کن 🎁",
        "rate_thanks_3": "🙏 ممنون از نظرت.\n\nسعی می‌کنیم دفعه بعد بهتر باشیم 💙",
        "rate_thanks_low": "😔 متأسفیم که راضی نبودی.\n\nلطفاً به ما بگو چه چیزی باعث نارضایتی شد تا بهتر بشیم:",
        "rate_thanks_low_admin": "❌ عدم رضایت جدید\n\n📋 نوبت: {id}\n⭐ امتیاز: {stars}\n👤 بیمار: {name}\nChatID: {cid}\n\n💬 نظر:\n{text}",
        "rate_feedback_thanks": "🙏 ممنون که نظرت رو گفتی.\n\nما حتماً پیگیری می‌کنیم 💙",
        "remind_apt_1d": "⏰ یادآوری نوبت\n\n📅 فردا ساعت {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nلطفاً ۱۵ دقیقه قبل حاضر باش. 💙",
        "remind_apt_2h": "⏰ یادآوری نوبت\n\n🕐 ۲ ساعت دیگه\n👨‍⚕️ {doctor}\n⏰ ساعت {time}\n📍 {address}\n\nما منتظرتیم 🌷",
        "remind_med": "💊 یادآوری دارو\n\nوقت مصرف {med} هست.\n\nسلامتت مهمه 💙",
        "taxi_title": "🚕 درخواست تاکسی\n\nبرای رفتن به مقصد، یکی از اپ‌های زیر رو باز کن و مقصد رو توی اپ وارد کن:",
        "hub_not_found": "❌ اطلاعات این پایانه موجود نیست.",
        "insurance_title": "🏥 بیمه‌های تحت پوشش\n\n👇 بیمه‌ات رو انتخاب کن:",
        "insurance_not_found": "❌ اطلاعات این بیمه موجود نیست.",
        "translator_title": "🗣️ مترجم همراه\n\nزبان مبدأ و مقصد رو انتخاب کن:",
        "translator_processing": "⏳ در حال ترجمه...",
        "translator_result": "📝 متن اصلی:\n{original}\n\n🌍 ترجمه:\n{translated}",
        "translator_error": "❌ متأسفانه ترجمه انجام نشد.\n\nدوباره تلاش کن.",
        "translator_too_long": "❌ ویس بیشتر از ۱ دقیقه‌ست.\n\nلطفاً کوتاه‌تر بفرست.",
        "translator_active": "✅ مترجم فعال شد\n\nویس بفرست (حداکثر ۱ دقیقه).\n\nبرای خروج: منو",
        "translator_listen": "🔊 شنیدن در گوگل ترنسلیت",
        "charter_title": "📜 منشور اخلاقی شیراز مدیکال",
        "charter_body": """ما در شیراز مدیکال، خود را متعهد می‌دانیم به:

۱. احترام و کرامت انسانی
با هر بیمار، فارغ از ملیت، زبان، مذهب یا توانایی مالی، با احترام کامل رفتار می‌کنیم.

۲. شفافیت کامل قیمت
هیچ هزینه‌ای پنهان نمی‌ماند. قبل از هر خدمت، قیمت دقیق و شفاف اعلام می‌شود.

۳. محرمانگی اطلاعات
اطلاعات پزشکی و شخصی شما نزد ما امانت است و بدون اجازه‌ی شما با هیچ کس به اشتراک گذاشته نمی‌شود.

۴. انتخاب آزاد پزشک
شما حق دارید پزشک، بیمارستان و مرکز درمانی خود را آزادانه انتخاب کنید.

۵. رضایت آگاهانه
قبل از هر اقدام درمانی، تمام جوانب، خطرات و مزایا برای شما توضیح داده می‌شود.

۶. پیگیری و مسئولیت‌پذیری
ما تا پایان مسیر درمان، حتی بعد از بازگشت به کشورتان، همراه شما هستیم.

۷. عدم تبعیض
هیچ بیماری به دلیل ملیت، جنسیت، مذهب یا ناتوانی از خدمات ما محروم نمی‌شود.

۸. صداقت پزشکی
هیچ خدمت غیرضروری به شما تحمیل نمی‌شود. فقط آنچه برای سلامت شما لازم است ارائه می‌شود.

۹. حق اعتراض
شما همیشه حق دارید شکایت کنید، نظر بدهید و پاسخ بگیرید.

۱۰. حفظ کرامت انسانی
بدن، حریم خصوصی و اعتقادات شما همیشه محترم شمرده می‌شود.

━━━━━━━━━━━━━━━
💙 شیراز مدیکال
سلامت شما، تعهد ما""",
        "deepseek_title": "🤖 دستیار هوشمند DeepSeek\n\nهر سؤالی داری بپرس: پزشکی، ترجمه، مشاوره، هر چیزی.\n\nرایگان و بدون محدودیت 🚀",
    },
   "ar": {
         "welcome": "🌟 رسالة واحدة، ونجهز كل شيء.\n\n👇 اختاروا من الأزرار:",
        "welcome_text": "أو اكتبوا طلبكم",
        "more": "سؤال آخر؟ (نعم / لا)",
        "go": "اكتبوا سؤالكم.",
        "thanks": "🙏 شكراً!",
        "thanks_fb": "شكراً. 🙏",
        "retry": "عذراً.",
        "text_only": "اكتبوا نصاً.",
        "apt_ask": "📅 اضغط ١.\n📞 اضغط ٢.",
        "apt_pick_title": "👨‍⚕️:",
        "apt_pick_footer": "📅 اكتب رقم:",
        "apt_name": "👤 الاسم:",
        "apt_phone": "📞 الهاتف:",
        "apt_submitted": "✅ تم التسجيل!\n\n📋 {id}\n👨‍⚕️ {doctor}",
        "apt_cancelled": "❌ إلغاء.",
        "apt_invalid": "اكتبوا: قائمة",
        "apt_error": "❌ خطأ.",
        "apt_my": "📋 مواعيدكم:",
        "apt_none": "لا مواعيد.",
        "apt_confirm_final": "تأكيد؟\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}",
        "apt_admin_new": "📥 طلب جديد\n\n📋 {id}\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}\n\n/confirm {id} 1405/09/20 10:30\n/done {id}",
        "apt_patient_confirmed": "🎉 تم التأكيد!\n\n📋 {id}\n👨‍⚕️ {doctor}\n📅 {date}\n⏰ {time}\n📍 {address}",
        "apt_done_admin_ok": "✅ تم / استبيان أرسل.",
        "apt_done_admin_bad": "❌ غير موجود.",
        "apt_done_patient": "🎊 كيف كانت الخدمة؟",
        "pt_created": "🎫 الملف: {code}",
        "pt_title": "🎫 ملفكم",
        "pt_code": "📋 {code}",
        "pt_name": "👤 {name}",
        "pt_progress": "🌟:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "الطلب",
        "pt_stages_doctor": "الطبيب",
        "pt_stages_date": "التاريخ",
        "pt_stages_accommodation": "الإقامة",
        "pt_stages_transport": "المواصلات",
        "pt_stages_treatment": "العلاج",
        "pt_stages_followup": "المتابعة",
        "pt_appointments": "📅:",
        "pt_apt_line_pending": "⏳ {id} — {doctor}",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date}",
        "pt_apt_line_done": "🎊 {id} — {doctor}",
        "pt_not_found": "لا ملف 💙",
        "delete_ask": "⚠️ اكتبوا: نعم احذف",
        "delete_done": "✅ تم الحذف.",
        "delete_cancel": "حسناً.",
        "rate_thanks_5": "🌟 ٥ نجوم! شكراً 💙\n\nادعوا أصدقاءكم 🎁",
        "rate_thanks_4": "😊 شكراً 🎁",
        "rate_thanks_3": "🙏 شكراً 💙",
        "rate_thanks_low": "😔 أخبرونا بالسبب:",
        "rate_thanks_low_admin": "❌ عدم رضا\n\n{id} — {stars}⭐\n{name} — {cid}\n\n{text}",
        "rate_feedback_thanks": "🙏 شكراً 💙",
        "remind_apt_1d": "⏰ تذكير بالموعد\n\n📅 غداً الساعة {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nيرجى الحضور قبل ١٥ دقيقة. 💙",
        "remind_apt_2h": "⏰ تذكير بالموعد\n\n🕐 بعد ساعتين\n👨‍⚕️ {doctor}\n⏰ {time}\n📍 {address}\n\nنحن في انتظارك 🌷",
        "remind_med": "💊 تذكير بالدواء\n\nموعد تناول {med}.\n\nصحتك تهمنا 💙",
        "taxi_title": "🚕 طلب تاكسي\n\nافتح أحد التطبيقات التالية وأدخل الوجهة:",
        "hub_not_found": "❌ معلومات هذه المحطة غير متوفرة.",
        "insurance_title": "🏥 التأمينات المدعومة\n\n👇 اختر تأمينك:",
        "insurance_not_found": "❌ معلومات هذا التأمين غير متوفرة.",
        "translator_title": "🗣️ المترجم المرافق\n\nاختر اللغة المصدر والهدف:",
        "translator_processing": "⏳ جاري الترجمة...",
        "translator_result": "📝 النص الأصلي:\n{original}\n\n🌍 الترجمة:\n{translated}",
        "translator_error": "❌ فشلت الترجمة.\n\nحاول مرة أخرى.",
        "translator_too_long": "❌ الرسالة أطول من دقيقة.\n\nأرسل مقطعاً أقصر.",
        "translator_active": "✅ تم تفعيل المترجم\n\nأرسل رسالة صوتية (حتى دقيقة).\n\nللخروج: القائمة",
        "translator_listen": "🔊 الاستماع في ترجمة جوجل",
        "charter_title": "📜 ميثاق شيراز ميديكال الأخلاقي",
        "charter_body": """نحن في شيراز ميديكال، نلتزم بـ:

١. احترام الكرامة الإنسانية
نتعامل مع كل مريض باحترام كامل، بغض النظر عن الجنسية أو اللغة أو الدين أو القدرة المالية.

٢. الشفافية الكاملة في الأسعار
لا توجد تكاليف خفية. تُعلن الأسعار الدقيقة بوضوح قبل كل خدمة.

٣. سرية المعلومات
معلوماتك الطبية والشخصية أمانة لدينا، ولا تُشارك مع أي شخص دون إذنك.

٤. حرية اختيار الطبيب
يحق لك اختيار طبيبك ومستشفاك ومركزك العلاجي بحرية.

٥. الموافقة المستنيرة
قبل كل إجراء علاجي، تُشرح لك جميع الجوانب والمخاطر والفوائد.

٦. المتابعة والمسؤولية
نرافقك حتى نهاية رحلة العلاج، حتى بعد عودتك إلى بلدك.

٧. عدم التمييز
لا يُحرم أي مريض من خدماتنا بسبب الجنسية أو الجنس أو الدين أو الإعاقة.

٨. الصدق الطبي
لا تُفرض عليك أي خدمة غير ضرورية. يُقدم فقط ما يلزم لصحتك.

٩. حق الاعتراض
يحق لك دائماً تقديم شكوى وإبداء رأيك والحصول على رد.

١٠. الحفاظ على الكرامة الإنسانية
يُحترم جسدك وخصوصيتك ومعتقداتك دائماً.

━━━━━━━━━━━━━━━
💙 شيراز ميديكال
صحتك، التزامنا""",
        "deepseek_title": "🤖 مساعد DeepSeek الذكي\n\nاسأل أي شيء: طب، ترجمة، استشارة، أي شيء.\n\nمجاني وبدون قيود 🚀",
    },
    "en": {
         "welcome": "🌟 One message, we prepare everything.\n\n👇 Choose:",
        "welcome_text": "Or write your request",
        "more": "Any other question? (Yes / No)",
        "go": "Please go ahead.",
        "thanks": "🙏 Thank you!",
        "thanks_fb": "Thanks. 🙏",
        "retry": "Sorry.",
        "text_only": "Write text only.",
        "apt_ask": "📅 Press 1.\n📞 Press 2.",
        "apt_pick_title": "👨‍⚕️:",
        "apt_pick_footer": "📅 Write number:",
        "apt_name": "👤 Full name:",
        "apt_phone": "📞 Phone:",
        "apt_submitted": "✅ Submitted!\n\n📋 {id}\n👨‍⚕️ {doctor}",
        "apt_cancelled": "❌ Cancelled.",
        "apt_invalid": "Write: menu",
        "apt_error": "❌ Error.",
        "apt_my": "📋 Appointments:",
        "apt_none": "No appointments.",
        "apt_confirm_final": "Confirm?\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}",
        "apt_admin_new": "📥 New request\n\n📋 {id}\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}\n\n/confirm {id} 1405/09/20 10:30\n/done {id}",
        "apt_patient_confirmed": "🎉 Confirmed!\n\n📋 {id}\n👨‍⚕️ {doctor}\n📅 {date}\n⏰ {time}\n📍 {address}",
        "apt_done_admin_ok": "✅ Visit marked. Survey sent.",
        "apt_done_admin_bad": "❌ Not found.",
        "apt_done_patient": "🎊 How was your visit?",
        "pt_created": "🎫 File: {code}",
        "pt_title": "🎫 Your File",
        "pt_code": "📋 {code}",
        "pt_name": "👤 {name}",
        "pt_progress": "🌟:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "Request",
        "pt_stages_doctor": "Doctor",
        "pt_stages_date": "Date",
        "pt_stages_accommodation": "Accommodation",
        "pt_stages_transport": "Transport",
        "pt_stages_treatment": "Treatment",
        "pt_stages_followup": "Follow-up",
        "pt_appointments": "📅:",
        "pt_apt_line_pending": "⏳ {id} — {doctor}",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date}",
        "pt_apt_line_done": "🎊 {id} — {doctor}",
        "pt_not_found": "No file 💙",
        "delete_ask": "⚠️ Write: yes delete",
        "delete_done": "✅ Deleted.",
        "delete_cancel": "Okay.",
        "rate_thanks_5": "🌟 5 stars! Thanks 💙\n\nInvite friends 🎁",
        "rate_thanks_4": "😊 Thanks 🎁",
        "rate_thanks_3": "🙏 Thanks 💙",
        "rate_thanks_low": "😔 Tell us why:",
        "rate_thanks_low_admin": "❌ Dissatisfied\n\n{id} — {stars}⭐\n{name} — {cid}\n\n{text}",
        "rate_feedback_thanks": "🙏 Thanks 💙",
        "remind_apt_1d": "⏰ Appointment reminder\n\n📅 Tomorrow at {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nPlease arrive 15 minutes early. 💙",
        "remind_apt_2h": "⏰ Reminder\n\n🕐 In 2 hours\n👨‍⚕️ {doctor}\n⏰ {time}\n📍 {address}\n\nWe're waiting for you 🌷",
        "remind_med": "💊 Medication reminder\n\nTime to take {med}.\n\nYour health matters 💙",
        "taxi_title": "🚕 Request Taxi\n\nOpen one of the apps below and enter your destination:",
        "hub_not_found": "❌ Hub information not available.",
        "insurance_title": "🏥 Supported Insurances\n\n👇 Choose your insurance:",
        "insurance_not_found": "❌ Insurance information not available.",
        "translator_title": "🗣️ Companion Translator\n\nChoose source and target languages:",
        "translator_processing": "⏳ Translating...",
        "translator_result": "📝 Original:\n{original}\n\n🌍 Translation:\n{translated}",
        "translator_error": "❌ Translation failed.\n\nTry again.",
        "translator_too_long": "❌ Voice longer than 1 minute.\n\nSend a shorter one.",
        "translator_active": "✅ Translator active\n\nSend a voice message (max 1 minute).\n\nTo exit: menu",
        "translator_listen": "🔊 Listen on Google Translate",
        "charter_title": "📜 Shiraz Medical Ethical Charter",
        "charter_body": """At Shiraz Medical, we are committed to:

1. Respect for Human Dignity
We treat every patient with full respect, regardless of nationality, language, religion, or financial ability.

2. Full Price Transparency
No hidden costs. The exact price is clearly announced before every service.

3. Confidentiality
Your medical and personal information is a trust with us and will not be shared with anyone without your consent.

4. Freedom to Choose Your Doctor
You have the right to freely choose your doctor, hospital, and medical center.

5. Informed Consent
Before any medical procedure, all aspects, risks, and benefits are explained to you.

6. Follow-up and Responsibility
We stay with you until the end of your treatment journey, even after you return home.

7. Non-Discrimination
No patient is denied our services due to nationality, gender, religion, or disability.

8. Medical Honesty
No unnecessary service is imposed on you. Only what is needed for your health is offered.

9. Right to Complain
You always have the right to complain, give feedback, and receive a response.

10. Preservation of Human Dignity
Your body, privacy, and beliefs are always respected.

━━━━━━━━━━━━━━━
💙 Shiraz Medical
Your Health, Our Commitment""",
        "deepseek_title": "🤖 DeepSeek Smart Assistant\n\nAsk anything: medical, translation, consultation, anything.\n\nFree and unlimited 🚀",
    },
}

MSG2 = {
    "fa": {
        "ref_your_code": "🔗 کد معرف شما: {code}\n\nلینک:\n{link}",
        "ref_your_stats": "👥 دعوت‌شده‌ها: {count}\n🎁 پاداش‌ها: {rewards}",
        "ref_new_from": "🎉 یکی با کد {code} پیوست!\n\nپاداش: ۱۰٪ تخفیف 🌹",
        "ref_welcome_new": "🎉 خوش آمدید!\n\nبا کد {code}.\n🎁 ۵٪ تخفیف اولین ویزیت",
        "ref_invite_msg": "🌟 دوستت رو دعوت کن\n\nکد: {code}\n\n{link}\n\n🎁 تو: ۱۰٪ تخفیف\n🎁 دوستت: ۵٪ تخفیف",
        "hope_night": "🌙 شب بخیر\n\n💊 یادتون نره داروهاتون رو مصرف کنید.\n🌷 ما کنارتونیم.",
        "hope_stage_request": "🌟 اولین قدمت رو برداشتی!\n\nما کنارتیم تا مسیر درمانت راحت باشه.",
        "hope_stage_doctor": "👨‍⚕️ پزشک متخصص شما مشخص شد 🌷",
        "hope_stage_date": "🎉 تاریخ نوبتت نهایی شد!\n\nیه قدم دیگه به سلامتی نزدیک‌تر شدی 💙",
        "hope_stage_accommodation": "🏨 اقامت شما هماهنگ شد 🌷",
        "hope_stage_transport": "🚗 حمل‌ونقل شما آماده شد 💙",
        "hope_stage_treatment": "🌸 درمان شما انجام شد. هر روز بهتر از دیروز باشی.",
        "hope_stage_followup": "🌷 ما همچنان کنارتونیم 💙",
        "hope_general_1": "💙 «سلامتی بزرگ‌ترین ثروته.»",
        "hope_general_2": "🌷 «هر روز، فرصتی برای بهبوده.»",
        "hope_general_3": "✨ «امید، نصف درمانه.»",
        "hope_general_4": "🌸 «تو تنها نیستی. ما کنارتیم.»",
        "comp_ask": "👥 آیا همراه دارید؟ (بله / نه)",
        "comp_ask_name": "👤 اسم همراهتون چیه؟",
        "comp_ask_phone": "📞 شماره‌ی همراهتون:",
        "comp_saved": "✅ همراه ثبت شد\n\n👤 {name}\n📞 {phone}",
        "comp_skip": "باشه، بنویسید: همراه",
        "sos_menu": "🚨 وضعیت اضطراری\n\n1️⃣ اورژانس ۱۱۵\n2️⃣ نزدیک‌ترین بیمارستان\n3️⃣ راهنمای کمک‌های اولیه\n4️⃣ اطلاع به همراه من\n5️⃣ انصراف",
        "sos_115": "🚑 اورژانس: ۱۱۵\n\nلطفاً تماس بگیرید و آدرس دقیق بگید.",
        "sos_first_aid": "🩺 کمک‌های اولیه\n\n🔹 درد قفسه سینه:\n- بشین و استراحت\n- قرص زیر زبانی\n- فوراً ۱۱۵\n\n🔹 خونریزی:\n- فشار مستقیم\n- ۱۱۵\n\n🔹 تنگی نفس:\n- بشین صاف\n- ۱۱۵\n\n⚠️ این راهنما جایگزین پزشک نیست.",
        "sos_no_companion": "❌ همراه ثبت نکردی. بنویسید: همراه",
        "comp_voice_menu": "📩 صدای شما\n\n1️⃣ انتقاد از پزشک\n2️⃣ انتقاد از مرکز درمانی\n3️⃣ انتقاد از اقامت\n4️⃣ انتقاد از حمل‌ونقل\n5️⃣ شکایت کلی\n6️⃣ انصراف",
        "comp_voice_text": "📝 نظرتون رو بنویسید:\n\nمی‌تونید اسم بگید یا «ناشناس» بنویسید.",
        "comp_voice_saved": "✅ پیام شما ثبت شد\n\n📋 کد: {id}\n\nما پیگیری می‌کنیم 💙",
        "comp_voice_skip": "باشه، بنویسید: شکایت",
        "comp_voice_admin": "📩 شکایت جدید\n\n📋 {id}\nدسته: {category}\nنام: {name}\nChatID: {cid}\n\n{text}",
        "rights_title": "⚖️ حقوق شما به عنوان بیمار\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ دریافت اطلاعات کامل\n2️⃣ حق انتخاب پزشک\n3️⃣ محرمانه بودن اطلاعات\n4️⃣ رضایت آگاهانه\n5️⃣ دریافت نسخه\n6️⃣ حق شکایت\n7️⃣ احترام بدون تبعیض\n8️⃣ دسترسی به پرونده\n\n📞 @ShirazMedBot\n- نظام پزشکی\n- وزارت بهداشت: 190",
        "med_menu": "⏰ یادآور دارو\n\n1️⃣ افزودن یادآور جدید\n2️⃣ مشاهده‌ی یادآورها\n3️⃣ انصراف",
        "med_ask_name": "💊 اسم دارو:",
        "med_ask_time": "⏰ ساعت؟ (مثال: 08:00)",
        "med_saved": "✅ یادآور ثبت شد\n\n💊 {name}\n⏰ {time}",
        "med_none": "هنوز یادآوری ثبت نکردی. بنویس: دارو",
        "food_title": "🍏 راهنمای تغذیه و تداخلات\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 تداخل‌های مهم:\n\n• آنتی‌بیوتیک + لبنیات (۲ ساعت)\n• آهن + چای/قهوه (۱ ساعت)\n• وارفارین + کلم و اسفناج\n• تیروئید + صبح ناشتا\n• مسکن + معده خالی (ممنوع)\n\n💧 آب زیاد\n🥗 میوه و سبزیجات\n🚫 خوددرمانی نکن\n\n⚠️ راهنمای کلیه، نه جایگزین پزشک.",
        "menu_main": "📋 منوی شیراز مدیکال\n\n👇 یکی رو انتخاب کن:",
        "ai_unavailable": "🙏 الان نمی‌تونم پاسخ بدم.\n\nبنویسید: منو",
        "para_list_title": "🏥 خدمات پیراپزشکی\n\n👇 انتخاب کن:",
        "elderly_list_title": "🏡 خانه‌های سالمندان شیراز",
        "elderly_all_title": "🏡 خانه‌های سالمندان شیراز:",
        "package_title": "💎 پکیج کامل درمان و اقامت\n━━━━━━━━━━━━━━━",
        "package_pitch": "🎯 یه پیام بده، همه‌چیز رو آماده می‌کنیم.\n\nاز لحظه‌ای که وارد شیراز می‌شی تا لحظه‌ای که با سلامتی برمی‌گردی، ما کنارتیم.",
        "package_value": "📦 چی توی این پکیج هست:\n\n👨‍⚕️ ویزیت پزشک متخصص\n🏨 اقامت در هتل\n🚗 ترانسفر فرودگاه و شهر\n🗣️ مترجم همراه\n🏛️ گشت گردشگری شیراز\n📋 پرونده‌ی سلامت شخصی\n💊 یادآور دارو و پیگیری\n🤝 همراه اختصاصی\n💙 پشتیبانی ۲۴ ساعته",
        "package_cta": "🎁 همه‌ی این‌ها با یک پیام.\n\n👇 برای دریافت قیمت:",
        "package_ask_name": "👤 نام و نام خانوادگی:",
        "package_ask_phone": "📞 شماره تماس:",
        "package_saved": "✅ درخواست پکیج ثبت شد\n\n📋 کد: {id}\n\nتیم ما در کمتر از ۲۴ ساعت تماس می‌گیره.\n\n💙 با آرزوی سلامتی",
        "package_admin_new": "💎 درخواست پکیج جدید\n\n📋 {id}\n👤 {name}\n📞 {phone}\nChatID: {cid}",
        "docs_list_title": "👨‍⚕️ کدام تخصص؟\n\n👇 انتخاب کن:",
        "nonmed_list_title": "🏥 کدام خدمت؟\n\n👇 انتخاب کن:",
        "tourist_list_title": "🏛️ کدام بخش گردشگری؟\n\n👇 انتخاب کن:",
        "pkg_ask_title": "💎 پکیج کامل",
        "hubs_title": "🚉 پایانه‌ها و فرودگاه‌های شیراز\n\n👇 کدوم رو می‌خوای ببینی؟",
    },
    "ar": {
        "ref_your_code": "🔗 {code}\n\n{link}",
        "ref_your_stats": "👥 {count}\n🎁 {rewards}",
        "ref_new_from": "🎉 {code} 🌹",
        "ref_welcome_new": "🎉 {code}\n🎁 ٥٪",
        "ref_invite_msg": "🌟 {code}\n\n{link}\n\n🎁 ١٠٪\n🎁 ٥٪",
        "hope_night": "🌙",
        "hope_stage_request": "🌟",
        "hope_stage_doctor": "👨‍⚕️",
        "hope_stage_date": "🎉",
        "hope_stage_accommodation": "🏨",
        "hope_stage_transport": "🚗",
        "hope_stage_treatment": "🌸",
        "hope_stage_followup": "🌷",
        "hope_general_1": "💙",
        "hope_general_2": "🌷",
        "hope_general_3": "✨",
        "hope_general_4": "🌸",
        "comp_ask": "👥 (نعم / لا)",
        "comp_ask_name": "👤:",
        "comp_ask_phone": "📞:",
        "comp_saved": "✅ {name} — {phone}",
        "comp_skip": "اكتبوا: مرافق",
        "sos_menu": "🚨\n\n1️⃣ ١١٥\n2️⃣\n3️⃣\n4️⃣\n5️⃣ إلغاء",
        "sos_115": "🚑 ١١٥",
        "sos_first_aid": "🩺\n\n⚠️ ليس بديلاً عن الطبيب.",
        "sos_no_companion": "❌ اكتبوا: مرافق",
        "comp_voice_menu": "📩\n\n1️⃣\n2️⃣\n3️⃣\n4️⃣\n5️⃣\n6️⃣",
        "comp_voice_text": "📝:",
        "comp_voice_saved": "✅ {id}",
        "comp_voice_skip": "اكتبوا: شكوى",
        "comp_voice_admin": "📩 {id}\n{category}\n{name}\n{cid}\n\n{text}",
        "rights_title": "⚖️ حقوق المريض\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣\n2️⃣\n3️⃣\n4️⃣\n5️⃣\n6️⃣\n7️⃣\n8️⃣\n\n📞 @ShirazMedBot\n190",
        "med_menu": "⏰\n\n1️⃣\n2️⃣\n3️⃣",
        "med_ask_name": "💊:",
        "med_ask_time": "⏰:",
        "med_saved": "✅ {name} — {time}",
        "med_none": "اكتبوا: دواء",
        "food_title": "🍏\n━━━━━━━━━━━━━━━",
        "food_body": "🔴\n\n⚠️",
        "menu_main": "📋\n\n👇",
        "ai_unavailable": "🙏 اكتبوا: قائمة",
        "para_list_title": "🏥\n\n👇",
        "elderly_list_title": "🏡",
        "elderly_all_title": "🏡:",
        "package_title": "💎 الباكج\n━━━━━━━━━━━━━━━",
        "package_pitch": "🎯",
        "package_value": "📦",
        "package_cta": "🎁\n\n👇",
        "package_ask_name": "👤:",
        "package_ask_phone": "📞:",
        "package_saved": "✅ {id}",
        "package_admin_new": "💎 {id}\n{name}\n{phone}\n{cid}",
        "docs_list_title": "👨‍⚕️\n\n👇",
        "nonmed_list_title": "🏥\n\n👇",
        "tourist_list_title": "🏛️\n\n👇",
        "pkg_ask_title": "💎",
        "hubs_title": "🚉 المحطات والمطارات في شيراز\n\n👇 اختر:",
    },
    "en": {
        "ref_your_code": "🔗 {code}\n\n{link}",
        "ref_your_stats": "👥 {count}\n🎁 {rewards}",
        "ref_new_from": "🎉 {code} 🌹",
        "ref_welcome_new": "🎉 {code}\n🎁 5%",
        "ref_invite_msg": "🌟 {code}\n\n{link}\n\n🎁 10%\n🎁 5%",
        "hope_night": "🌙",
        "hope_stage_request": "🌟",
        "hope_stage_doctor": "👨‍⚕️",
        "hope_stage_date": "🎉",
        "hope_stage_accommodation": "🏨",
        "hope_stage_transport": "🚗",
        "hope_stage_treatment": "🌸",
        "hope_stage_followup": "🌷",
        "hope_general_1": "💙",
        "hope_general_2": "🌷",
        "hope_general_3": "✨",
        "hope_general_4": "🌸",
        "comp_ask": "👥 (Yes / No)",
        "comp_ask_name": "👤:",
        "comp_ask_phone": "📞:",
        "comp_saved": "✅ {name} — {phone}",
        "comp_skip": "Write: companion",
        "sos_menu": "🚨\n\n1️⃣ 115\n2️⃣\n3️⃣\n4️⃣\n5️⃣ Cancel",
        "sos_115": "🚑 115",
        "sos_first_aid": "🩺\n\n⚠️",
        "sos_no_companion": "❌ Write: companion",
        "comp_voice_menu": "📩\n\n1️⃣\n2️⃣\n3️⃣\n4️⃣\n5️⃣\n6️⃣",
        "comp_voice_text": "📝:",
        "comp_voice_saved": "✅ {id}",
        "comp_voice_skip": "Write: complaint",
        "comp_voice_admin": "📩 {id}\n{category}\n{name}\n{cid}\n\n{text}",
        "rights_title": "⚖️ Patient Rights\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣\n2️⃣\n3️⃣\n4️⃣\n5️⃣\n6️⃣\n7️⃣\n8️⃣\n\n📞 @ShirazMedBot\n190",
        "med_menu": "⏰\n\n1️⃣\n2️⃣\n3️⃣",
        "med_ask_name": "💊:",
        "med_ask_time": "⏰:",
        "med_saved": "✅ {name} — {time}",
        "med_none": "Write: med",
        "food_title": "🍏\n━━━━━━━━━━━━━━━",
        "food_body": "🔴\n\n⚠️",
        "menu_main": "📋\n\n👇",
        "ai_unavailable": "🙏 Write: menu",
        "para_list_title": "🏥\n\n👇",
        "elderly_list_title": "🏡",
        "elderly_all_title": "🏡:",
        "package_title": "💎 Package\n━━━━━━━━━━━━━━━",
        "package_pitch": "🎯",
        "package_value": "📦",
        "package_cta": "🎁\n\n👇",
        "package_ask_name": "👤:",
        "package_ask_phone": "📞:",
        "package_saved": "✅ {id}",
        "package_admin_new": "💎 {id}\n{name}\n{phone}\n{cid}",
        "docs_list_title": "👨‍⚕️\n\n👇",
        "nonmed_list_title": "🏥\n\n👇",
        "tourist_list_title": "🏛️\n\n👇",
        "pkg_ask_title": "💎",
        "hubs_title": "🚉 Shiraz Transport Hubs\n\n👇 Choose:",
    },
}

MSG_CH = {
    "fa": {
        "btn_channel_go": "🔗 رفتن به کانال",
        "btn_channel_ok": "✅ عضو شدم",
        "msg_channel": "🎁 یه هدیه کوچیک برات داریم\n\nعضو کانال ما بشو → ۵٪ تخفیف\nروی همه سرویس‌ها (پزشک، هتل، ترانسفر)\n\nبعد از عضویت، برگرد و بزن [✅ عضو شدم]",
        "msg_channel_done": "✅ خوش اومدی!\n\n۵٪ تخفیف روی اولین سرویست فعال شد.\n\nالان می‌تونی نوبت پزشک بگیری یا هتل رزرو کنی.\nاز /menu شروع کن 🚀",
        "msg_channel_already": "😊 قبلاً عضو شدی و ۵٪ تخفیفت فعاله.\nبزن /menu و ازش استفاده کن.",
    },
    "ar": {
        "btn_channel_go": "🔗 الذهاب للقناة",
        "btn_channel_ok": "✅ انضممت",
        "msg_channel": "🎁 لدينا هدية صغيرة لك\n\nانضم إلى قناتنا → خصم ٥٪\nعلى جميع الخدمات (طبيب، فندق، نقل)\n\nبعد الانضمام، ارجع واضغط [✅ انضممت]",
        "msg_channel_done": "✅ أهلاً بك!\n\nتم تفعيل خصم ٥٪ على خدمتك الأولى.\n\nيمكنك الآن حجز طبيب أو فندق.\nابدأ بـ /menu 🚀",
        "msg_channel_already": "😊 أنت مشترك بالفعل وخصم ٥٪ مفعّل.\nاضغط /menu للاستفادة منه.",
    },
    "en": {
        "btn_channel_go": "🔗 Go to Channel",
        "btn_channel_ok": "✅ I joined",
        "msg_channel": "🎁 A small gift for you\n\nJoin our channel → 5% OFF\non all services (doctor, hotel, transfer)\n\nAfter joining, come back and tap [✅ I joined]",
        "msg_channel_done": "✅ Welcome aboard!\n\nYour 5% discount is now active.\n\nBook a doctor or hotel now.\nStart with /menu 🚀",
        "msg_channel_already": "😊 You already joined and your 5% discount is active.\nTap /menu to use it.",
    },
}
HUB_LABELS = {
    "shiraz_airport": {"fa": "✈️ فرودگاه شهید دستغیب", "ar": "✈️ مطار الشهيد دستغيب", "en": "✈️ Shahid Dastgheib Airport"},
    "shiraz_railway": {"fa": "🚂 ایستگاه راه‌آهن شیراز", "ar": "🚂 محطة قطار شيراز", "en": "🚂 Shiraz Railway Station"},
    "karandish_terminal": {"fa": "🚌 پایانه کاراندیش", "ar": "🚌 محطة كارانديش", "en": "🚌 Karandish Terminal"},
    "amirkabir_terminal": {"fa": "🚌 پایانه امیرکبیر", "ar": "🚌 محطة أمير كبير", "en": "🚌 Amirkabir Terminal"},
}

HUB_FIELDS_ORDER = [
    "official_name", "city", "full_address", "iata_code", "icao_code",
    "main_phone", "emergency_phone", "website", "email",
    "latitude", "longitude", "distance_to_city_center",
    "working_hours", "metro", "city_bus", "taxis",
    "hotel_shuttle", "parking", "wheelchair_accessibility", "vip_lounge",
    "terminals", "airlines", "facilities",
    "nearby_hospitals", "nearby_hotels", "short_description", "important_tips",
]

INSURANCE_FIELDS_ORDER = [
    "type",
    "coverage_gp_visit", "coverage_specialist", "coverage_subspecialist",
    "coverage_hospitalization", "coverage_surgery",
    "coverage_medication_opd", "coverage_medication_ipd",
    "coverage_lab", "coverage_radiology", "coverage_mri_ct", "coverage_sonography",
    "coverage_physiotherapy", "coverage_occupational", "coverage_speech",
    "coverage_dentistry_restorative", "coverage_dentistry_cosmetic",
    "coverage_vision", "coverage_natural_birth", "coverage_csection",
    "coverage_dialysis", "coverage_chemotherapy", "coverage_radiotherapy",
    "coverage_psychiatry", "coverage_ambulance",
    "annual_cap", "per_admission_cap",
    "deductible_visit", "deductible_hospital", "deductible_medication",
    "annual_medication_cap",
    "waiting_period", "special_diseases", "exclusions", "age_limit",
    "foreign_patient_coverage", "installment_payment",
    "required_documents", "usage_summary",
    "contracted_centers", "claim_processing_time", "complaint_process",
    "main_phone", "support_phone_24h", "website", "mobile_app", "email",
    "shiraz_offices",
    "total_insured", "population_coverage_pct",
    "total_contracted_centers", "total_contracted_doctors",
]

INSURANCE_FIELD_LABELS = {
    "fa": {
        "type": "نوع بیمه",
        "coverage_gp_visit": "ویزیت پزشک عمومی",
        "coverage_specialist": "ویزیت پزشک متخصص",
        "coverage_subspecialist": "ویزیت فوق تخصص",
        "coverage_hospitalization": "بستری در بیمارستان",
        "coverage_surgery": "جراحی",
        "coverage_medication_opd": "دارو سرپایی",
        "coverage_medication_ipd": "دارو بستری",
        "coverage_lab": "آزمایشگاه",
        "coverage_radiology": "رادیولوژی",
        "coverage_mri_ct": "ام‌آر‌آی و سی‌تی‌اسکن",
        "coverage_sonography": "سونوگرافی",
        "coverage_physiotherapy": "فیزیوتراپی",
        "coverage_occupational": "کاردرمانی",
        "coverage_speech": "گفتاردرمانی",
        "coverage_dentistry_restorative": "دندانپزشکی ترمیمی",
        "coverage_dentistry_cosmetic": "دندانپزشکی زیبایی",
        "coverage_vision": "عینک و بینایی",
        "coverage_natural_birth": "زایمان طبیعی",
        "coverage_csection": "سزارین",
        "coverage_dialysis": "دیالیز",
        "coverage_chemotherapy": "شیمی‌درمانی",
        "coverage_radiotherapy": "پرتودرمانی",
        "coverage_psychiatry": "روان‌پزشکی",
        "coverage_ambulance": "آمبولانس",
        "annual_cap": "سقف سالانه",
        "per_admission_cap": "سقف هر بستری",
        "deductible_visit": "فرانشیز ویزیت",
        "deductible_hospital": "فرانشیز بستری",
        "deductible_medication": "فرانشیز دارو",
        "annual_medication_cap": "سقف دارو در سال",
        "waiting_period": "دوره انتظار",
        "special_diseases": "بیماری‌های خاص تحت پوشش",
        "exclusions": "بیماری‌های خارج از پوشش",
        "age_limit": "سن مجاز پوشش",
        "foreign_patient_coverage": "پوشش بیمار خارجی",
        "installment_payment": "امکان پرداخت قسطی",
        "required_documents": "مدارک لازم",
        "usage_summary": "نحوه استفاده",
        "contracted_centers": "مراکز طرف قرارداد",
        "claim_processing_time": "زمان رسیدگی به مطالبات",
        "complaint_process": "نحوه شکایت",
        "main_phone": "تلفن اصلی",
        "support_phone_24h": "پشتیبانی شبانه‌روزی",
        "website": "وب‌سایت",
        "mobile_app": "اپلیکیشن موبایل",
        "email": "ایمیل",
        "shiraz_offices": "دفاتر شیراز",
        "total_insured": "تعداد کل بیمه‌شده",
        "population_coverage_pct": "درصد جمعیت",
        "total_contracted_centers": "تعداد مراکز طرف قرارداد",
        "total_contracted_doctors": "تعداد پزشکان طرف قرارداد",
    },
    "ar": {
        "type": "نوع التأمين",
        "coverage_gp_visit": "زيارة طبيب عام",
        "coverage_specialist": "زيارة طبيب متخصص",
        "coverage_subspecialist": "زيارة طبيب أخصائي",
        "coverage_hospitalization": "الاستشفاء",
        "coverage_surgery": "الجراحة",
        "coverage_medication_opd": "أدوية العيادات الخارجية",
        "coverage_medication_ipd": "أدوية الاستشفاء",
        "coverage_lab": "المختبر",
        "coverage_radiology": "الأشعة",
        "coverage_mri_ct": "الرنين والأشعة المقطعية",
        "coverage_sonography": "التصوير بالموجات فوق الصوتية",
        "coverage_physiotherapy": "العلاج الطبيعي",
        "coverage_occupational": "العلاج الوظيفي",
        "coverage_speech": "علاج النطق",
        "coverage_dentistry_restorative": "طب الأسنان الترميمي",
        "coverage_dentistry_cosmetic": "تجميل الأسنان",
        "coverage_vision": "النظارات والبصر",
        "coverage_natural_birth": "الولادة الطبيعية",
        "coverage_csection": "العملية القيصرية",
        "coverage_dialysis": "غسيل الكلى",
        "coverage_chemotherapy": "العلاج الكيميائي",
        "coverage_radiotherapy": "العلاج الإشعاعي",
        "coverage_psychiatry": "الطب النفسي",
        "coverage_ambulance": "سيارة الإسعاف",
        "annual_cap": "السقف السنوي",
        "per_admission_cap": "سقف كل إدخال",
        "deductible_visit": "نسبة التحمل للزيارة",
        "deductible_hospital": "نسبة التحمل للاستشفاء",
        "deductible_medication": "نسبة التحمل للأدوية",
        "annual_medication_cap": "سقف الأدوية السنوي",
        "waiting_period": "فترة الانتظار",
        "special_diseases": "الأمراض الخاصة المشمولة",
        "exclusions": "الأمراض غير المشمولة",
        "age_limit": "حد السن للتغطية",
        "foreign_patient_coverage": "تغطية المريض الأجنبي",
        "installment_payment": "الدفع بالتقسيط",
        "required_documents": "المستندات المطلوبة",
        "usage_summary": "ملخص الاستخدام",
        "contracted_centers": "المراكز المتعاقدة",
        "claim_processing_time": "وقت معالجة المطالبات",
        "complaint_process": "طريقة تقديم الشكوى",
        "main_phone": "الهاتف الرئيسي",
        "support_phone_24h": "دعم 24 ساعة",
        "website": "الموقع الإلكتروني",
        "mobile_app": "تطبيق الجوال",
        "email": "البريد الإلكتروني",
        "shiraz_offices": "مكاتب شيراز",
        "total_insured": "إجمالي المؤمن عليهم",
        "population_coverage_pct": "نسبة تغطية السكان",
        "total_contracted_centers": "عدد المراكز المتعاقدة",
        "total_contracted_doctors": "عدد الأطباء المتعاقدين",
    },
    "en": {
        "type": "Insurance Type",
        "coverage_gp_visit": "GP Visit",
        "coverage_specialist": "Specialist Visit",
        "coverage_subspecialist": "Sub-specialist Visit",
        "coverage_hospitalization": "Hospitalization",
        "coverage_surgery": "Surgery",
        "coverage_medication_opd": "Outpatient Medication",
        "coverage_medication_ipd": "Inpatient Medication",
        "coverage_lab": "Laboratory",
        "coverage_radiology": "Radiology",
        "coverage_mri_ct": "MRI & CT",
        "coverage_sonography": "Sonography",
        "coverage_physiotherapy": "Physiotherapy",
        "coverage_occupational": "Occupational Therapy",
        "coverage_speech": "Speech Therapy",
        "coverage_dentistry_restorative": "Restorative Dentistry",
        "coverage_dentistry_cosmetic": "Cosmetic Dentistry",
        "coverage_vision": "Vision Care",
        "coverage_natural_birth": "Natural Birth",
        "coverage_csection": "C-Section",
        "coverage_dialysis": "Dialysis",
        "coverage_chemotherapy": "Chemotherapy",
        "coverage_radiotherapy": "Radiotherapy",
        "coverage_psychiatry": "Psychiatry",
        "coverage_ambulance": "Ambulance",
        "annual_cap": "Annual Cap",
        "per_admission_cap": "Per-admission Cap",
        "deductible_visit": "Visit Deductible",
        "deductible_hospital": "Hospital Deductible",
        "deductible_medication": "Medication Deductible",
        "annual_medication_cap": "Annual Medication Cap",
        "waiting_period": "Waiting Period",
        "special_diseases": "Special Diseases Covered",
        "exclusions": "Exclusions",
        "age_limit": "Age Limit",
        "foreign_patient_coverage": "Foreign Patient Coverage",
        "installment_payment": "Installment Payment",
        "required_documents": "Required Documents",
        "usage_summary": "How to Use",
        "contracted_centers": "Contracted Centers",
        "claim_processing_time": "Claim Processing Time",
        "complaint_process": "Complaint Process",
        "main_phone": "Main Phone",
        "support_phone_24h": "24/7 Support",
        "website": "Website",
        "mobile_app": "Mobile App",
        "email": "Email",
        "shiraz_offices": "Shiraz Offices",
        "total_insured": "Total Insured",
        "population_coverage_pct": "Population Coverage (%)",
        "total_contracted_centers": "Total Contracted Centers",
        "total_contracted_doctors": "Total Contracted Doctors",
    },
}

YES_WORDS = {"بله", "بلی", "آره", "اره", "yes", "yeah", "y", "نعم", "ايوه", "أيوه", "ها", "آری", "اری"}
NO_WORDS = {"نه", "نخیر", "خیر", "نه ممنون", "ندارم", "no", "nope", "n", "لا", "لا شكرا", "ليس"}

SPECIALTY_MAP = {}

def add_specialty(filename, *words):
    for w in words:
        SPECIALTY_MAP[w.lower()] = filename

add_specialty("cardiology.json", "قلب", "قلبی", "cardio", "heart", "قلبية", "عروق")
add_specialty("dermatology.json", "پوست", "derma", "skin", "جلد", "جلدية")
add_specialty("dentistry.json", "دندان", "dental", "dentist", "أسنان", "اسنان")
add_specialty("kids_dentistry.json", "دندان کودکان", "kids dental", "أسنان أطفال")
add_specialty("ophthalmology.json", "چشم", "eye", "عيون", "عين")
add_specialty("ent.json", "گوش", "بینی", "گلو", "ent", "nose", "أنف", "أذن")
add_specialty("orthopedics.json", "ارتوپدی", "استخوان", "ortho", "bone", "عظام", "عظمي")
add_specialty("gynecology.json", "زنان", "نازایی", "ivf", "gyneco", "نساء", "ولادة")
add_specialty("pediatrics.json", "کودک", "اطفال", "pediatric", "أطفال", "طفل")
add_specialty("psychiatry.json", "روان", "psych", "نفسي", "طب نفسي")
add_specialty("internal_medicine.json", "داخلی", "internal", "باطنية")
add_specialty("urology.json", "اورولوژی", "کلیه", "مثانه", "urology", "مسالك", "كلى")
add_specialty("general_surgery.json", "جراح عمومی", "surgery", "جراحة عامة", "جراح")
add_specialty("rhinoplasty.json", "رینوپلاستی", "جراحی بینی", "rhino", "تجميل الأنف")
add_specialty("gastroenterology.json", "گوارش", "معده", "روده", "کبد", "gastro", "هضمي", "معدة")
add_specialty("emergency_medicine.json", "اورژانس", "emergency", "طوارئ")
add_specialty("traditional_medicine.json", "طب سنتی", "گیاهی", "traditional", "طب تقليدي")
add_specialty("pharmacies.json", "داروخانه", "دارو", "pharmacy", "صيدلية", "دواء")
add_specialty("allergy.json", "آلرژی", "حساسیت", "allergy", "حساسية", "تحسس")
add_specialty("hematology_oncology.json", "خون", "آنکولوژی", "سرطان", "hematology", "oncology", "دم", "أورام")
add_specialty("endocrinology.json", "غدد", "تیروئید", "دیابت", "endocrinology", "غدة", "سكري", "درقية")
add_specialty("neurosurgery.json", "مغز و اعصاب", "نوروسرجری", "neurosurgery", "دماغ", "أعصاب", "صرع", "ms")

NON_MEDICAL_MAP = {
    "hospitals.json": ["بیمارستان", "hospital", "مستشفى", "کلینیک", "clinic"],
    "hotels.json": ["هتل", "hotel", "فندق", "فنادق", "اقامتگاه"],
    "motels.json": ["مهمان‌پذیر", "مسافرخانه", "motel", "نُزل", "نزل"],
    "tourist_houses.json": ["خانه مسافر", "اقامتگاه بومگردی", "tourist house", "guest house", "بيت مسافر"],
    "leisure_city.json": ["جاذبه", "حافظیه", "سعدیه", "ارگ", "نصیرالملک", "شاهچراغ", "باغ ارم", "بازار وکیل", "موزه", "مسجد"],
    "leisure_outside.json": ["تخت جمشید", "پاسارگاد", "نقش رستم", "آبشار", "persepolis", "pasargad"],
    "transport.json": ["حمل‌ونقل", "مترو", "اتوبوس", "فرودگاه", "transport", "metro", "مواصلات", "مطار"],
    "support.json": ["پشتیبانی", "هلال احمر", "شماره اضطراری", "support", "دعم", "مساعدة"],
    "complaints.json": ["شکایت", "شکایات", "complaint", "شكوى"],
    "patient_guide.json": ["راهنمای بیمار", "ویزای درمانی", "patient guide", "medical visa", "قبول مريض", "تأشيرة طبية"],
    "paramedical.json": [
        "فیزیوتراپی", "فیزیوتراپ", "physiotherapy", "physio", "علاج طبيعي",
        "آزمایشگاه", "آزمایش", "lab", "laboratory", "مختبر",
        "رادیولوژی", "تصویربرداری", "ام آر آی", "mri", "ct", "سونوگرافی", "radiology", "أشعة",
        "پرستاری", "پرستار", "nursing", "nurse", "تمريض",
        "تزریق", "سرم", "injection", "iv", "حقن",
        "حجامت", "cupping",
        "کاردرمانی", "occupational", "علاج وظيفي",
        "گفتاردرمانی", "speech", "علاج النطق",
        "پروتز", "ارتوپدی فنی", "بریس", "کفی", "orthotics", "prosthetics", "أطراف",
        "پیراپزشکی", "paramedical", "مساعد طبي"
    ],
    "elderly_homes.json": [
        "خانه سالمندان", "خانه‌ی سالمندان", "آسایشگاه", "سرای سالمندان", "سالمندان",
        "nursing home", "nursing homes", "elderly", "senior",
        "دار المسنين", "دار رعاية المسنين", "مسنين", "عجزة"
    ],
}

FIELD_NAMES = {
    "fa": {
        "name": "نام", "address": "آدرس", "phone": "تلفن", "specialty": "تخصص",
        "office_address": "آدرس مطب", "working_hours": "ساعت کاری",
        "price_range_toman": "قیمت", "price_range": "قیمت",
        "patient_satisfaction_score": "امتیاز", "rating": "امتیاز",
        "reviews_summary": "نظر مسافران", "surgeries_done_at": "بیمارستان‌ها",
        "category": "دسته", "star_rating": "ستاره", "quality_grade": "کیفیت",
        "district": "منطقه", "amenities": "امکانات", "distance_to_hospitals": "فاصله تا بیمارستان",
        "has_translator": "مترجم", "languages_spoken": "زبان‌ها",
        "description": "توضیحات", "services": "خدمات", "type": "نوع",
        "has_home_service": "خدمات در منزل", "capacity": "ظرفیت",
    },
    "ar": {
        "name": "الاسم", "address": "العنوان", "phone": "الهاتف", "specialty": "التخصص",
        "office_address": "عنوان العيادة", "working_hours": "ساعات العمل",
        "price_range_toman": "السعر", "price_range": "السعر",
        "patient_satisfaction_score": "التقييم", "rating": "التقييم",
        "reviews_summary": "آراء", "surgeries_done_at": "المستشفيات",
        "category": "الفئة", "star_rating": "التصنيف", "quality_grade": "الجودة",
        "district": "المنطقة", "amenities": "المرافق", "distance_to_hospitals": "المسافة",
        "has_translator": "مترجم", "languages_spoken": "اللغات",
        "description": "الوصف", "services": "الخدمات", "type": "النوع",
        "has_home_service": "خدمة منزلية", "capacity": "السعة",
    },
    "en": {
        "name": "Name", "address": "Address", "phone": "Phone", "specialty": "Specialty",
        "office_address": "Office Address", "working_hours": "Working Hours",
        "price_range_toman": "Price", "price_range": "Price",
        "patient_satisfaction_score": "Rating", "rating": "Rating",
        "reviews_summary": "Reviews", "surgeries_done_at": "Hospitals",
        "category": "Category", "star_rating": "Star Rating", "quality_grade": "Quality",
        "district": "District", "amenities": "Amenities", "distance_to_hospitals": "Distance",
        "has_translator": "Has Translator", "languages_spoken": "Languages",
        "description": "Description", "services": "Services", "type": "Type",
        "has_home_service": "Home Service", "capacity": "Capacity",
    },
}

PRICE_MAP = {
    "Low": {"fa": "اقتصادی", "ar": "اقتصادي", "en": "Low"},
    "Medium": {"fa": "متوسط", "ar": "متوسط", "en": "Medium"},
    "High": {"fa": "گران", "ar": "غالي", "en": "High"},
}

CONTEXT_WORDS = ["بیمارستان", "hospital", "مستشفى", "شیراز", "shiraz", "شيراز", "doctor", "دکتر", "طبيب", "dr"]

EMERGENCY = {
    "fa": ["درد شدید", "تب", "خونریزی", "استفراغ", "ضعف", "غش", "سکته", "تشنج", "خفگی"],
    "ar": ["ألم شديد", "حمى", "نزيف", "قيء", "ضعف", "إغماء", "جلطة"],
    "en": ["severe pain", "fever", "bleeding", "vomiting", "weakness", "fainting", "stroke"]
}

EMERGENCY_RESP = {
    "fa": "🚨 فوراً به اورژانس. تلفن: ۱۱۵",
    "ar": "🚨 توجه فوراً إلى الطوارئ. هاتف: ١١٥",
    "en": "🚨 Go to emergency. Phone: 115"
}

CMD_FILE = {"پرونده", "پرونده من", "ملف", "ملفي", "file", "my file"}
CMD_APT = {"نوبت", "نوبت‌ها", "نوبت‌هام", "موعد", "مواعيد", "appointment", "appointments"}
CMD_COMPANION = {"همراه", "همراهم", "مرافق", "companion"}
CMD_COMPLAINT = {"شکایت", "شکایات", "انتقاد", "نظر", "شكوى", "complaint", "feedback"}
CMD_MED = {"دارو", "یادآور", "یادآور دارو", "دواء", "تذكير", "med", "medication", "reminder"}
CMD_RIGHTS = {"حقوق", "حق من", "حقوق بیمار", "حقوقي", "rights", "patient rights"}
CMD_FOOD = {"چی بخورم", "غذا", "تغذیه", "تداخل", "طعام", "تغذية", "food", "nutrition"}
CMD_FLOWER = {"گل", "امید", "دلگرمی", "زهرة", "أمل", "flower", "hope"}
CMD_SOS = {"اضطراری", "کمک", "فوری", "حالم خوب نیست", "حالم بده", "طوارئ", "emergency", "help", "urgent", "sos"}
CMD_INVITE = {"دعوت", "معرفی", "کد معرف", "دعوة", "إحالة", "invite", "referral"}
CMD_MENU = {"منو", "راهنما", "قائمة", "menu", "help"}
CMD_NIGHT = {"شب بخیر", "شب‌بخیر", "مساء الخير", "good night", "goodnight"}
CMD_DELETE = {"حذف اطلاعات", "پاک کردن", "delete my data"}
CMD_PARA = {"پیراپزشکی", "پارامدیکال", "paramedical", "مساعد طبي"}
CMD_ELDERLY = {"خانه سالمندان", "خانه‌ی سالمندان", "آسایشگاه", "سرای سالمندان", "nursing home", "elderly", "دار المسنين"}
CMD_ELDERLY_ALL = {"همه خانه سالمندان", "کل خانه سالمندان", "all nursing homes", "كل دور المسنين"}
CMD_PACKAGE = {"پکیج", "پکیج درمان", "پکیج گردشگری", "پکیج سلامت", "باكج", "باكج علاج", "package"}
CMD_CHANNEL = {"عضویت در کانال", "عضویت کانال", "کانال", "channel", "join channel", "قناة", "انضمام"}
CMD_TAXI = {"تاکسی", "اسنپ", "تپسی", "snapp", "tap30", "tap 30", "taxi", "تكسي", "اسناب"}
CMD_HUBS = {"پایانه", "پایانه‌ها", "ترمینال", "فرودگاه", "راه‌آهن", "قطار", "اتوبوس", "hub", "hubs", "airport", "train", "bus", "terminal", "مطار", "محطة", "محطات"}
CMD_INSURANCE = {"بیمه", "بیمه‌ها", "بیمه من", "insurance", "تأمين", "تامين", "بیمه درمانی"}
CMD_TRANSLATOR = {"مترجم", "ترجمه", "مترجم همراه", "translator", "translate", "المترجم", "ترجمة"}
CMD_CHARTER = {"منشور", "منشور اخلاقی", "اخلاق", "charter", "ethics", "ميثاق", "أخلاق"}
CMD_DEEPSEEK = {"دیپ سیک", "دیپ‌سیک", "هوش مصنوعی", "deepseek", "deep seek", "ai", "ذكاء اصطناعي"}
def clean(text):
    return text.translate(DIGITS).strip().lower().strip(" .!؟?،,")

def pick_language(text):
    t = clean(text)
    if t in ("1", "۱") or "فارسی" in t or "persian" in t or "farsi" in t:
        return "fa"
    if t in ("2", "۲") or "عرب" in t or "arab" in t:
        return "ar"
    if t in ("3", "۳") or "english" in t or "انگلیس" in t:
        return "en"
    return None

def english_words(text):
    return re.findall(r"[a-zA-Z]+", text.lower())

def is_simple_cmd(text, cmd_set):
    return clean(text) in cmd_set

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []
    except:
        return []

def get_value(item, key, lang):
    if not isinstance(item, dict):
        return None
    if key in item:
        v = item[key]
        if isinstance(v, dict):
            if lang in v:
                return v[lang]
            if "fa" in v:
                return v["fa"]
            if "en" in v:
                return v["en"]
            if "ar" in v:
                return v["ar"]
            return None
        return v
    if (key + "_" + lang) in item:
        return item[key + "_" + lang]
    if (key + "_fa") in item:
        return item[key + "_fa"]
    return None

def get_price(item, lang):
    p = item.get('price_range', '') or item.get('price_range_toman', '')
    if not p:
        return ""
    if isinstance(p, dict):
        return p.get(lang, p.get('fa', ''))
    if p in PRICE_MAP:
        return PRICE_MAP[p].get(lang, p)
    return p

def item_name_for_search(item):
    for k in ("name_fa", "name_ar", "name_en", "name"):
        if k in item:
            v = item[k]
            if isinstance(v, dict):
                return v.get('fa', '') or v.get('en', '') or v.get('ar', '')
            return str(v)
    return ""

def is_all_request(text):
    low = text.lower()
    words = re.findall(r"\w+", low)
    for w in ["همه", "تمام", "کل", "همگی", "all", "كل", "جميع"]:
        if w.lower() in words:
            return True
    return False

def is_emergency(text):
    low = text.lower()
    words = re.findall(r"\w+", low)
    for ks in EMERGENCY.values():
        for k in ks:
            if " " in k:
                if k in low:
                    return True
            else:
                if k in words:
                    return True
    return False

def get_user_name(message):
    try:
        fn = message.from_user.first_name or ""
        ln = message.from_user.last_name or ""
        un = message.from_user.username or ""
        full = (fn + " " + ln).strip()
        if full:
            return full
        if un:
            return un
        return "ناشناس"
    except:
        return "ناشناس"

def validate_phone(text):
    phone = re.sub(r'[^0-9+]', '', text.translate(DIGITS).strip())
    if len(phone) < 8 or len(phone) > 15:
        return None
    return phone

def validate_time(text):
    t = re.sub(r'[^0-9:]', '', text.translate(DIGITS).strip())
    if ":" not in t:
        return None
    parts = t.split(":")
    if len(parts) != 2:
        return None
    try:
        h = int(parts[0])
        m = int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return str(h).zfill(2) + ":" + str(m).zfill(2)
    except:
        pass
    return None

def validate_date_shamsi(s):
    try:
        parts = re.sub(r'[^0-9/]', '', s.translate(DIGITS)).split("/")
        if len(parts) != 3:
            return None
        jy = int(parts[0])
        jm = int(parts[1])
        jd = int(parts[2])
        if jy < 1400 or jy > 1500 or jm < 1 or jm > 12 or jd < 1 or jd > 31:
            return None
        return str(jy) + "/" + str(jm).zfill(2) + "/" + str(jd).zfill(2)
    except:
        return None

def format_date_full(offset_days=0, lang="fa"):
    today = datetime.now() + timedelta(days=offset_days)
    miladi = today.strftime("%Y/%m/%d")
    return miladi

def local_now():
    return datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET_HOURS)

def shamsi_to_miladi(jy, jm, jd):
    if jdatetime is None:
        return None
    try:
        g = jdatetime.date(jy, jm, jd).togregorian()
        return datetime(g.year, g.month, g.day)
    except:
        return None

def parse_apt_datetime(apt):
    if not apt or not apt.get('date') or not apt.get('time'):
        return None
    try:
        dparts = apt['date'].split('/')
        tparts = apt['time'].split(':')
        if len(dparts) != 3 or len(tparts) != 2:
            return None
        jy, jm, jd = int(dparts[0]), int(dparts[1]), int(dparts[2])
        hh, mm = int(tparts[0]), int(tparts[1])
        g = shamsi_to_miladi(jy, jm, jd)
        if g is None:
            return None
        return datetime(g.year, g.month, g.day, hh, mm)
    except:
        return None

def main_menu_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_docs"], callback_data="menu_docs"),
        telebot.types.InlineKeyboardButton(text=b["btn_nonmed"], callback_data="menu_nonmed"),
        telebot.types.InlineKeyboardButton(text=b["btn_tourist"], callback_data="menu_tourist"),
        telebot.types.InlineKeyboardButton(text=b["btn_para"], callback_data="menu_para"),
        telebot.types.InlineKeyboardButton(text=b["btn_elder"], callback_data="menu_elder"),
        telebot.types.InlineKeyboardButton(text=b["btn_pkg"], callback_data="menu_pkg"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_hubs"], callback_data="do_hubs"),
        telebot.types.InlineKeyboardButton(text=b["btn_taxi"], callback_data="do_taxi"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_insurance"], callback_data="do_insurance"),
        telebot.types.InlineKeyboardButton(text=b["btn_translator"], callback_data="do_translator"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_charter"], callback_data="do_charter"),
        telebot.types.InlineKeyboardButton(text=b["btn_deepseek"], callback_data="do_deepseek"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_file"], callback_data="do_file"),
        telebot.types.InlineKeyboardButton(text=b["btn_apt"], callback_data="do_apt"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_med"], callback_data="do_med"),
        telebot.types.InlineKeyboardButton(text=b["btn_sos"], callback_data="do_sos"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_channel"], callback_data="do_channel"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_invite"], callback_data="do_invite"),
        telebot.types.InlineKeyboardButton(text=b["btn_help"], callback_data="do_help"),
    )
    return m

def hubs_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    for hub_id, labels in HUB_LABELS.items():
        label = labels.get(lang, labels.get("fa", hub_id))
        m.add(telebot.types.InlineKeyboardButton(text=label, callback_data="hub_" + hub_id))
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m

def insurance_kb(lang, page=0):
    all_ins = load_all_insurances()
    if not all_ins:
        return back_kb(lang)
    per_page = 10
    total = len(all_ins)
    start = page * per_page
    end = min(start + per_page, total)
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    for ins in all_ins[start:end]:
        name = ins.get("name_" + lang, "") or ins.get("name_fa", "") or ins.get("id", "")
        ins_id = ins.get("id", "")
        if name and ins_id:
            m.add(telebot.types.InlineKeyboardButton(
                text="🏥 " + name,
                callback_data="ins_" + ins_id
            ))
    nav = []
    if page > 0:
        nav.append(telebot.types.InlineKeyboardButton(text="◀️ قبلی", callback_data="ins_page_" + str(page - 1)))
    if end < total:
        nav.append(telebot.types.InlineKeyboardButton(text="بعدی ▶️", callback_data="ins_page_" + str(page + 1)))
    if nav:
        m.add(*nav)
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m

def insurance_action_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back_insurance"], callback_data="do_insurance"))
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m

def translator_lang_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_tr_fa_ar"], callback_data="tr_fa_ar"),
        telebot.types.InlineKeyboardButton(text=b["btn_tr_ar_fa"], callback_data="tr_ar_fa"),
        telebot.types.InlineKeyboardButton(text=b["btn_tr_fa_en"], callback_data="tr_fa_en"),
        telebot.types.InlineKeyboardButton(text=b["btn_tr_en_fa"], callback_data="tr_en_fa"),
    )
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def translator_result_kb(lang, translated_text, target_lang_code):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    encoded = quote(translated_text[:400])
    url = "https://translate.google.com/?sl=auto&tl=" + target_lang_code + "&text=" + encoded + "&op=translate"
    m.add(telebot.types.InlineKeyboardButton(text=MSG[lang]["translator_listen"], url=url))
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m

def deepseek_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_deepseek_go"], url=DEEPSEEK_URL))
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def specialties_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    items = [
        ("قلب", "cardiology", "قلبية", "Heart"),
        ("پوست", "dermatology", "جلدية", "Skin"),
        ("دندان", "dentistry", "أسنان", "Dental"),
        ("چشم", "ophthalmology", "عيون", "Eye"),
        ("گوش، بینی، گلو", "ent", "أنف", "ENT"),
        ("ارتوپدی", "orthopedics", "عظام", "Ortho"),
        ("زنان و زایمان", "gynecology", "نساء", "Gyneco"),
        ("کودکان", "pediatrics", "أطفال", "Pediatrics"),
        ("روان‌پزشکی", "psychiatry", "نفسي", "Psychiatry"),
        ("داخلی", "internal_medicine", "باطنية", "Internal"),
        ("اورولوژی", "urology", "مسالك", "Urology"),
        ("جراحی عمومی", "general_surgery", "جراحة", "Surgery"),
        ("گوارش", "gastroenterology", "هضمي", "Gastro"),
        ("غدد", "endocrinology", "غدة", "Endocrine"),
        ("خون و سرطان", "hematology_oncology", "أورام", "Hematology"),
        ("مغز و اعصاب", "neurosurgery", "أعصاب", "Neurosurgery"),
        ("آلرژی", "allergy", "حساسية", "Allergy"),
        ("طب سنتی", "traditional_medicine", "طب تقليدي", "Traditional"),
    ]
    btns = []
    for fa, fn, ar, en in items:
        label = fa if lang == "fa" else (ar if lang == "ar" else en)
        btns.append(telebot.types.InlineKeyboardButton(text=label, callback_data="spec_" + fn))
    m.add(*btns)
    b = MSG_BTN[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def nonmed_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_hospitals"], callback_data="non_hospitals"),
        telebot.types.InlineKeyboardButton(text=b["btn_hotels"], callback_data="non_hotels"),
        telebot.types.InlineKeyboardButton(text=b["btn_motels"], callback_data="non_motels"),
        telebot.types.InlineKeyboardButton(text=b["btn_houses"], callback_data="non_tourist_houses"),
        telebot.types.InlineKeyboardButton(text=b["btn_transport"], callback_data="non_transport"),
    )
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def tourist_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_city"], callback_data="non_leisure_city"),
        telebot.types.InlineKeyboardButton(text=b["btn_outside"], callback_data="non_leisure_outside"),
    )
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def para_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    items = [
        (b["btn_physio"], "فیزیوتراپی"),
        (b["btn_lab"], "آزمایشگاه"),
        (b["btn_radiology"], "رادیولوژی"),
        (b["btn_nursing"], "پرستاری"),
        (b["btn_injection"], "تزریق"),
        (b["btn_trad_med"], "طب سنتی"),
        (b["btn_occupational"], "کاردرمانی"),
        (b["btn_speech"], "گفتاردرمانی"),
        (b["btn_orthotics"], "پروتز"),
    ]
    btns = []
    for label, _ in items:
        btns.append(telebot.types.InlineKeyboardButton(text=label, callback_data="para_search"))
    m.add(*btns)
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def elderly_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_elder_all"], callback_data="elder_all"))
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def package_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_pkg_order"], callback_data="pkg_order"))
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def doctor_action_kb(lang, doc_id):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_book"], callback_data="book_" + doc_id),
        telebot.types.InlineKeyboardButton(text=b["btn_call"], callback_data="call_" + doc_id),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_taxi"], callback_data="do_taxi"),
    )
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def taxi_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_snapp"], url=SNAPP_URL),
        telebot.types.InlineKeyboardButton(text=b["btn_tap30"], url=TAP30_URL),
    )
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def hub_action_kb(lang, hub_id):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back_hubs"], callback_data="do_hubs"))
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m

def rate_kb(lang, apt_id):
    m = telebot.types.InlineKeyboardMarkup(row_width=5)
    m.add(
        telebot.types.InlineKeyboardButton(text="1⭐", callback_data="rate_1_" + apt_id),
        telebot.types.InlineKeyboardButton(text="2⭐", callback_data="rate_2_" + apt_id),
        telebot.types.InlineKeyboardButton(text="3⭐", callback_data="rate_3_" + apt_id),
        telebot.types.InlineKeyboardButton(text="4⭐", callback_data="rate_4_" + apt_id),
        telebot.types.InlineKeyboardButton(text="5⭐", callback_data="rate_5_" + apt_id),
    )
    return m

def back_kb(lang, cb="back_main"):
    m = telebot.types.InlineKeyboardMarkup()
    b = MSG_BTN[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data=cb))
    return m

def channel_kb(lang):
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    b = MSG_CH[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_channel_go"], url=CHANNEL_LINK))
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_channel_ok"], callback_data="channel_confirm"))
    m.add(telebot.types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m
MSG_BTN = {
    "fa": {
        "btn_docs": "👨‍⚕️ پزشکی",
        "btn_nonmed": "🏥 غیرپزشکی",
        "btn_tourist": "🏛️ گردشگری",
        "btn_para": "🏥 پیراپزشکی",
        "btn_elder": "🏡 خانه سالمندان",
        "btn_pkg": "💎 پکیج کامل",
        "btn_file": "📋 پرونده",
        "btn_apt": "📅 نوبت‌های من",
        "btn_med": "💊 یادآور دارو",
        "btn_sos": "🚨 اضطراری",
        "btn_invite": "🎁 دعوت دوستان",
        "btn_help": "🆘 حقوق بیمار",
        "btn_channel": "📢 عضویت در کانال",
        "btn_taxi": "🚕 درخواست تاکسی",
        "btn_snapp": "🚗 اسنپ",
        "btn_tap30": "🚕 تپسی",
        "btn_hubs": "🚉 پایانه‌ها و فرودگاه",
        "btn_insurance": "🏥 بیمه‌های تحت پوشش",
        "btn_back_insurance": "🔙 بازگشت به لیست بیمه‌ها",
        "btn_back_hubs": "🔙 بازگشت به لیست پایانه‌ها",
        "btn_translator": "🗣️ مترجم همراه",
        "btn_tr_fa_ar": "🇮🇷 فارسی → 🇸🇦 عربی",
        "btn_tr_ar_fa": "🇸🇦 عربی → 🇮🇷 فارسی",
        "btn_tr_fa_en": "🇮🇷 فارسی → 🇬🇧 انگلیسی",
        "btn_tr_en_fa": "🇬🇧 انگلیسی → 🇮🇷 فارسی",
        "btn_charter": "📜 منشور اخلاقی",
        "btn_deepseek": "🤖 هوش مصنوعی DeepSeek",
        "btn_deepseek_go": "🚀 رفتن به DeepSeek",
        "btn_back": "🔙 بازگشت",
        "btn_hospitals": "🏥 بیمارستان‌ها",
        "btn_hotels": "🏨 هتل‌ها",
        "btn_motels": "🛏️ مهمان‌پذیر",
        "btn_houses": "🏠 خانه مسافر",
        "btn_transport": "🚗 حمل‌ونقل",
        "btn_city": "🏛️ جاذبه‌های شهری",
        "btn_outside": "🏞️ خارج از شهر",
        "btn_physio": "🦴 فیزیوتراپی",
        "btn_lab": "🔬 آزمایشگاه",
        "btn_radiology": "📷 رادیولوژی",
        "btn_nursing": "👩‍⚕️ پرستاری",
        "btn_injection": "💉 تزریق",
        "btn_trad_med": "🌿 طب سنتی",
        "btn_occupational": "🧩 کاردرمانی",
        "btn_speech": "🗣️ گفتاردرمانی",
        "btn_orthotics": "🦿 پروتز",
        "btn_elder_all": "🏡 همه خانه‌های سالمندان",
        "btn_pkg_order": "💎 سفارش پکیج",
        "btn_book": "📅 نوبت بگیر",
        "btn_call": "📞 تماس",
    },
    "ar": {
        "btn_docs": "👨‍⚕️ طبي",
        "btn_nonmed": "🏥 غير طبي",
        "btn_tourist": "🏛️ سياحة",
        "btn_para": "🏥 مساعد طبي",
        "btn_elder": "🏡 المسنين",
        "btn_pkg": "💎 الباكج",
        "btn_file": "📋 الملف",
        "btn_apt": "📅 مواعيدي",
        "btn_med": "💊 تذكير",
        "btn_sos": "🚨 طوارئ",
        "btn_invite": "🎁 دعوة",
        "btn_help": "🆘 الحقوق",
        "btn_channel": "📢 الانضمام إلى القناة",
        "btn_taxi": "🚕 طلب تاكسي",
        "btn_snapp": "🚗 سناب",
        "btn_tap30": "🚕 تابسي",
        "btn_hubs": "🚉 المحطات والمطارات",
        "btn_insurance": "🏥 التأمينات المدعومة",
        "btn_back_insurance": "🔙 العودة إلى قائمة التأمينات",
        "btn_back_hubs": "🔙 العودة إلى قائمة المحطات",
        "btn_translator": "🗣️ المترجم المرافق",
        "btn_tr_fa_ar": "🇮🇷 الفارسية → 🇸🇦 العربية",
        "btn_tr_ar_fa": "🇸🇦 العربية → 🇮🇷 الفارسية",
        "btn_tr_fa_en": "🇮🇷 الفارسية → 🇬🇧 الإنجليزية",
        "btn_tr_en_fa": "🇬🇧 الإنجليزية → 🇮🇷 الفارسية",
        "btn_charter": "📜 الميثاق الأخلاقي",
        "btn_deepseek": "🤖 الذكاء الاصطناعي DeepSeek",
        "btn_deepseek_go": "🚀 الذهاب إلى DeepSeek",
        "btn_back": "🔙 رجوع",
        "btn_hospitals": "🏥 المستشفيات",
        "btn_hotels": "🏨 الفنادق",
        "btn_motels": "🛏️ النزل",
        "btn_houses": "🏠 بيوت",
        "btn_transport": "🚗 المواصلات",
        "btn_city": "🏛️ معالم",
        "btn_outside": "🏞️ خارج المدينة",
        "btn_physio": "🦴 طبيعي",
        "btn_lab": "🔬 مختبر",
        "btn_radiology": "📷 أشعة",
        "btn_nursing": "👩‍⚕️ تمريض",
        "btn_injection": "💉 حقن",
        "btn_trad_med": "🌿 تقليدي",
        "btn_occupational": "🧩 وظيفي",
        "btn_speech": "🗣️ النطق",
        "btn_orthotics": "🦿 أطراف",
        "btn_elder_all": "🏡 الكل",
        "btn_pkg_order": "💎 طلب",
        "btn_book": "📅 احجز",
        "btn_call": "📞 اتصل",
    },
    "en": {
        "btn_docs": "👨‍⚕️ Medical",
        "btn_nonmed": "🏥 Non-medical",
        "btn_tourist": "🏛️ Tourism",
        "btn_para": "🏥 Paramedical",
        "btn_elder": "🏡 Nursing",
        "btn_pkg": "💎 Package",
        "btn_file": "📋 File",
        "btn_apt": "📅 Appointments",
        "btn_med": "💊 Med",
        "btn_sos": "🚨 Emergency",
        "btn_invite": "🎁 Invite",
        "btn_help": "🆘 Rights",
        "btn_channel": "📢 Join Channel",
        "btn_taxi": "🚕 Request Taxi",
        "btn_snapp": "🚗 Snapp",
        "btn_tap30": "🚕 Tap30",
        "btn_hubs": "🚉 Transport Hubs",
        "btn_insurance": "🏥 Supported Insurances",
        "btn_back_insurance": "🔙 Back to Insurances List",
        "btn_back_hubs": "🔙 Back to Hubs List",
        "btn_translator": "🗣️ Translator",
        "btn_tr_fa_ar": "🇮🇷 Persian → 🇸🇦 Arabic",
        "btn_tr_ar_fa": "🇸🇦 Arabic → 🇮🇷 Persian",
        "btn_tr_fa_en": "🇮🇷 Persian → 🇬🇧 English",
        "btn_tr_en_fa": "🇬🇧 English → 🇮🇷 Persian",
        "btn_charter": "📜 Ethical Charter",
        "btn_deepseek": "🤖 DeepSeek AI",
        "btn_deepseek_go": "🚀 Go to DeepSeek",
        "btn_back": "🔙 Back",
        "btn_hospitals": "🏥 Hospitals",
        "btn_hotels": "🏨 Hotels",
        "btn_motels": "🛏️ Motels",
        "btn_houses": "🏠 Guest Houses",
        "btn_transport": "🚗 Transport",
        "btn_city": "🏛️ City",
        "btn_outside": "🏞️ Outside",
        "btn_physio": "🦴 Physio",
        "btn_lab": "🔬 Lab",
        "btn_radiology": "📷 Radiology",
        "btn_nursing": "👩‍⚕️ Nursing",
        "btn_injection": "💉 Injection",
        "btn_trad_med": "🌿 Traditional",
        "btn_occupational": "🧩 Occupational",
        "btn_speech": "🗣️ Speech",
        "btn_orthotics": "🦿 Orthotics",
        "btn_elder_all": "🏡 All",
        "btn_pkg_order": "💎 Order",
        "btn_book": "📅 Book",
        "btn_call": "📞 Call",
    },
}
DATA_DIR = "/app/data"
DATA_DIR_FALLBACK = "data"

def data_path(filename):
    if os.path.isdir(DATA_DIR):
        return os.path.join(DATA_DIR, filename)
    return os.path.join(DATA_DIR_FALLBACK, filename)

APPOINTMENTS_FILE = data_path("appointments.json")
PATIENTS_FILE = data_path("patients.json")
REFERRALS_FILE = data_path("referrals.json")
COMPANIONS_FILE = data_path("companions.json")
COMPLAINTS_FILE = data_path("complaints.json")
MEDS_FILE = data_path("meds.json")
USERS_FILE = data_path("users.json")
PACKAGES_FILE = data_path("packages.json")
RATINGS_FILE = data_path("ratings.json")

def _load_default(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def _save(path, data):
    try:
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_appointments():
    return _load_default(APPOINTMENTS_FILE, {"next_id": 1001, "appointments": []})

def save_appointments(data):
    return _save(APPOINTMENTS_FILE, data)

def create_appointment(doctor, pname, pphone, chat_id, lang):
    data = load_appointments()
    if "next_id" not in data:
        data["next_id"] = 1001
    apt_id = "APT-" + str(data['next_id'])
    data['next_id'] += 1
    apt = {
        "id": apt_id,
        "doctor_id": doctor.get('id', ''),
        "doctor_name_fa": get_value(doctor, 'name', 'fa') or '',
        "doctor_name_ar": get_value(doctor, 'name', 'ar') or '',
        "doctor_name_en": get_value(doctor, 'name', 'en') or '',
        "doctor_phone": doctor.get('phone', ''),
        "doctor_address_fa": get_value(doctor, 'office_address', 'fa') or get_value(doctor, 'address', 'fa') or '',
        "doctor_address_ar": get_value(doctor, 'office_address', 'ar') or get_value(doctor, 'address', 'ar') or '',
        "doctor_address_en": get_value(doctor, 'office_address', 'en') or get_value(doctor, 'address', 'en') or '',
        "patient_name": pname,
        "patient_phone": pphone,
        "patient_chat_id": str(chat_id),
        "patient_lang": lang,
        "date": "",
        "time": "",
        "status": "pending",
        "rating": 0,
        "reminded_1d": False,
        "reminded_2h": False,
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['appointments'].append(apt)
    save_appointments(data)
    return apt

def get_patient_appointments(chat_id):
    data = load_appointments()
    return [a for a in data['appointments'] if a['patient_chat_id'] == str(chat_id)]

def find_appointment(apt_id):
    data = load_appointments()
    for a in data['appointments']:
        if a['id'] == apt_id:
            return a
    return None

def confirm_appointment(apt_id, date_str, time_str):
    data = load_appointments()
    for a in data['appointments']:
        if a['id'] == apt_id:
            a['date'] = date_str
            a['time'] = time_str
            a['status'] = 'confirmed'
            a['confirmed_at'] = datetime.now().strftime("%Y/%m/%d %H:%M")
            a['reminded_1d'] = False
            a['reminded_2h'] = False
            save_appointments(data)
            return a
    return None

def mark_apt_done(apt_id):
    data = load_appointments()
    for a in data['appointments']:
        if a['id'] == apt_id:
            a['status'] = 'done'
            a['done_at'] = datetime.now().strftime("%Y/%m/%d %H:%M")
            save_appointments(data)
            return a
    return None

def set_apt_rating(apt_id, stars):
    data = load_appointments()
    for a in data['appointments']:
        if a['id'] == apt_id:
            a['rating'] = stars
            a['rated_at'] = datetime.now().strftime("%Y/%m/%d %H:%M")
            save_appointments(data)
            return a
    return None

def mark_reminded(apt_id, which):
    data = load_appointments()
    for a in data['appointments']:
        if a['id'] == apt_id:
            a[which] = True
            save_appointments(data)
            return True
    return False

def load_patients():
    return _load_default(PATIENTS_FILE, {"patients": []})

def save_patients(data):
    return _save(PATIENTS_FILE, data)

def get_patient_by_chat(chat_id):
    data = load_patients()
    for p in data['patients']:
        if p.get('chat_id') == str(chat_id) and p.get('type', 'patient') == 'patient':
            return p
    return None

def get_patient_by_code(code):
    data = load_patients()
    for p in data['patients']:
        if p.get('code') == code:
            return p
    return None

def next_patient_code():
    data = load_patients()
    max_num = 1000
    for p in data['patients']:
        code = p.get('code', '')
        m = re.match(r"PT-(\d+)", code)
        if m:
            try:
                n = int(m.group(1))
                if n > max_num:
                    max_num = n
            except:
                pass
    return "PT-" + str(max_num + 1)

def create_or_get_patient(chat_id, name, phone, lang):
    data = load_patients()
    for p in data['patients']:
        if p.get('chat_id') == str(chat_id) and p.get('type', 'patient') == 'patient':
            if name and not p.get('name'):
                p['name'] = name
            if phone and not p.get('phone'):
                p['phone'] = phone
            save_patients(data)
            return p
    code = next_patient_code()
    p = {
        "chat_id": str(chat_id),
        "name": name or "",
        "phone": phone or "",
        "code": code,
        "lang": lang,
        "type": "patient",
        "appointments": [],
        "status": "active",
        "stages": {
            "request": True, "doctor": False, "date": False,
            "accommodation": False, "transport": False, "treatment": False, "followup": False
        },
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['patients'].append(p)
    save_patients(data)
    return p

def update_patient_stage(chat_id, stage, value=True):
    data = load_patients()
    for p in data['patients']:
        if p.get('chat_id') == str(chat_id) and p.get('type', 'patient') == 'patient':
            if 'stages' not in p:
                p['stages'] = {}
            p['stages'][stage] = value
            save_patients(data)
            return True
    return False

def add_appointment_to_patient(chat_id, apt_id):
    data = load_patients()
    for p in data['patients']:
        if p.get('chat_id') == str(chat_id) and p.get('type', 'patient') == 'patient':
            if 'appointments' not in p:
                p['appointments'] = []
            if apt_id not in p['appointments']:
                p['appointments'].append(apt_id)
            save_patients(data)
            return True
    return False

def format_patient_file(patient, lang):
    if not patient:
        return MSG[lang]["pt_not_found"]
    m = MSG[lang]
    lines = [m["pt_title"]]
    lines.append(m["pt_code"].format(code=patient.get('code', '')))
    if patient.get('name'):
        lines.append(m["pt_name"].format(name=patient['name']))
    lines.append(m["pt_progress"])
    stages = patient.get('stages', {})
    for s in ["request", "doctor", "date", "accommodation", "transport", "treatment", "followup"]:
        stage_name = m.get("pt_stages_" + s, s)
        if stages.get(s):
            lines.append(m["pt_stage_done"].format(stage=stage_name))
        else:
            lines.append(m["pt_stage_wait"].format(stage=stage_name))
    apts = patient.get('appointments', [])
    if apts:
        lines.append(m["pt_appointments"])
        for aid in apts:
            apt = find_appointment(aid)
            if not apt:
                continue
            dn = apt.get("doctor_name_" + lang) or apt.get("doctor_name_fa", "")
            st = apt.get('status', 'pending')
            if st == 'done':
                lines.append(m["pt_apt_line_done"].format(id=apt['id'], doctor=dn))
            elif st == 'confirmed' and apt.get('date'):
                lines.append(m["pt_apt_line_confirmed"].format(
                    id=apt['id'], doctor=dn, date=apt['date'], time=apt.get('time', '')))
            else:
                lines.append(m["pt_apt_line_pending"].format(id=apt['id'], doctor=dn))
    hope = random.choice([
        MSG2[lang]["hope_general_1"], MSG2[lang]["hope_general_2"],
        MSG2[lang]["hope_general_3"], MSG2[lang]["hope_general_4"],
    ])
    lines.append(hope)
    return "\n".join(lines)

def delete_patient_data(chat_id):
    cid = str(chat_id)
    pats = load_patients()
    pats['patients'] = [p for p in pats['patients'] if p.get('chat_id') != cid]
    save_patients(pats)
    apts = load_appointments()
    apts['appointments'] = [a for a in apts['appointments'] if a.get('patient_chat_id') != cid]
    save_appointments(apts)
    comps = _load_default(COMPANIONS_FILE, {"companions": {}})
    if cid in comps.get('companions', {}):
        del comps['companions'][cid]
        _save(COMPANIONS_FILE, comps)
    meds = _load_default(MEDS_FILE, {"meds": []})
    meds['meds'] = [m for m in meds['meds'] if m.get('chat_id') != cid]
    _save(MEDS_FILE, meds)
    return True
def save_rating(apt_id, chat_id, stars, feedback=""):
    data = _load_default(RATINGS_FILE, {"ratings": []})
    item = {
        "apt_id": apt_id,
        "chat_id": str(chat_id),
        "stars": stars,
        "feedback": feedback,
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['ratings'].append(item)
    _save(RATINGS_FILE, data)
    return item

def load_packages():
    return _load_default(PACKAGES_FILE, {"next_id": 1001, "packages": []})

def save_packages(data):
    return _save(PACKAGES_FILE, data)

def create_package(chat_id, name, phone, lang):
    data = load_packages()
    if "next_id" not in data:
        data["next_id"] = 1001
    pkg_id = "PKG-" + str(data['next_id'])
    data['next_id'] += 1
    pkg = {
        "id": pkg_id, "chat_id": str(chat_id), "name": name, "phone": phone,
        "lang": lang, "status": "pending",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['packages'].append(pkg)
    save_packages(data)
    return pkg

def load_referrals():
    return _load_default(REFERRALS_FILE, {"users": {}, "codes": {}})

def save_referrals(data):
    return _save(REFERRALS_FILE, data)

def next_ref_code():
    data = load_referrals()
    max_num = 100
    for code in data.get('codes', {}).keys():
        m = re.match(r"REF-A?(\d+)", code)
        if m:
            try:
                n = int(m.group(1))
                if n > max_num:
                    max_num = n
            except:
                pass
    return "REF-A" + str(max_num + 1)

def get_or_create_referral_code(chat_id):
    data = load_referrals()
    cid = str(chat_id)
    if cid in data['users'] and data['users'][cid].get('code'):
        return data['users'][cid]['code']
    code = next_ref_code()
    if cid not in data['users']:
        data['users'][cid] = {}
    data['users'][cid]['code'] = code
    data['users'][cid]['count'] = data['users'][cid].get('count', 0)
    data['users'][cid]['rewards'] = data['users'][cid].get('rewards', [])
    data['codes'][code] = cid
    save_referrals(data)
    return code

def apply_referral(new_chat_id, ref_code):
    data = load_referrals()
    ncid = str(new_chat_id)
    if ncid in data['users'] and data['users'][ncid].get('referred_by'):
        return None
    inviter = data['codes'].get(ref_code)
    if not inviter or inviter == ncid:
        return None
    if ncid not in data['users']:
        data['users'][ncid] = {}
    data['users'][ncid]['referred_by'] = ref_code
    data['users'][ncid]['reward'] = "5%"
    if inviter not in data['users']:
        data['users'][inviter] = {}
    if 'count' not in data['users'][inviter]:
        data['users'][inviter]['count'] = 0
    data['users'][inviter]['count'] += 1
    if 'rewards' not in data['users'][inviter]:
        data['users'][inviter]['rewards'] = []
    data['users'][inviter]['rewards'].append("10%")
    save_referrals(data)
    return {"inviter": inviter, "inviter_code": ref_code}

def get_referral_stats(chat_id):
    data = load_referrals()
    cid = str(chat_id)
    if cid not in data['users']:
        return {"code": "", "count": 0, "rewards": []}
    u = data['users'][cid]
    return {"code": u.get('code', ''), "count": u.get('count', 0), "rewards": u.get('rewards', [])}

def build_referral_link(code):
    return "https://ble.ir/ShirazMedBot?start=" + code

def try_apply_start_param(message, text, lang):
    if not text:
        return None
    m = re.match(r"^/start\s+(REF-A?\d+)", text.strip(), re.IGNORECASE)
    if not m:
        return None
    code = m.group(1).upper()
    res = apply_referral(message.chat.id, code)
    if res:
        try:
            bot.send_message(message.chat.id, MSG2[lang]["ref_welcome_new"].format(code=code))
            bot.send_message(res["inviter"], MSG2[lang]["ref_new_from"].format(code=code))
        except:
            pass
    return res

def is_channel_joined(chat_id):
    data = load_referrals()
    cid = str(chat_id)
    u = data['users'].get(cid, {})
    return u.get('channel_reward', False)

def grant_channel_reward(chat_id):
    data = load_referrals()
    cid = str(chat_id)
    if cid not in data['users']:
        data['users'][cid] = {}
    if data['users'][cid].get('channel_reward'):
        return False
    data['users'][cid]['channel_reward'] = True
    data['users'][cid]['channel_discount'] = CHANNEL_DISCOUNT
    data['users'][cid]['channel_joined_at'] = datetime.now().strftime("%Y/%m/%d %H:%M")
    save_referrals(data)
    return True

def load_companions():
    return _load_default(COMPANIONS_FILE, {"companions": {}})

def save_companions(data):
    return _save(COMPANIONS_FILE, data)

def set_companion(chat_id, name, phone):
    data = load_companions()
    data['companions'][str(chat_id)] = {"name": name, "phone": phone}
    save_companions(data)
    return True

def get_companion(chat_id):
    data = load_companions()
    return data['companions'].get(str(chat_id))

def load_users():
    return _load_default(USERS_FILE, {"users": {}, "start_count": 0, "apt_count": 0})

def save_users(data):
    return _save(USERS_FILE, data)

def register_user(chat_id, lang):
    data = load_users()
    cid = str(chat_id)
    today = datetime.now().strftime("%Y/%m/%d")
    if cid not in data['users']:
        data['users'][cid] = {
            "first_seen": today, "last_seen": today, "lang": lang,
            "interactions": 1, "appointments": 0
        }
        data['start_count'] = data.get('start_count', 0) + 1
    else:
        data['users'][cid]['last_seen'] = today
        data['users'][cid]['lang'] = lang
        data['users'][cid]['interactions'] = data['users'][cid].get('interactions', 0) + 1
    save_users(data)

def register_appointment_for_stats(chat_id):
    data = load_users()
    cid = str(chat_id)
    if cid in data['users']:
        data['users'][cid]['appointments'] = data['users'][cid].get('appointments', 0) + 1
    data['apt_count'] = data.get('apt_count', 0) + 1
    save_users(data)

def get_user_stats():
    data = load_users()
    users = data.get('users', {})
    now = datetime.now()
    today_str = now.strftime("%Y/%m/%d")
    seven_days_ago = (now - timedelta(days=7)).strftime("%Y/%m/%d")
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y/%m/%d")
    total = len(users)
    dau = wau = mau = 0
    for u in users.values():
        ls = u.get('last_seen', '')
        if ls == today_str:
            dau += 1
        if ls >= seven_days_ago:
            wau += 1
        if ls >= thirty_days_ago:
            mau += 1
    starts = data.get('start_count', 0)
    apts = data.get('apt_count', 0)
    conv = round((apts / starts) * 100, 1) if starts > 0 else 0
    ref_data = load_referrals()
    channel_count = sum(1 for u in ref_data.get('users', {}).values() if u.get('channel_reward'))
    return {"total": total, "dau": dau, "wau": wau, "mau": mau, "conv": conv, "channel": channel_count}
def load_complaints():
    return _load_default(COMPLAINTS_FILE, {"next_id": 1001, "complaints": []})

def save_complaints(data):
    return _save(COMPLAINTS_FILE, data)

def create_complaint(chat_id, category, name, text):
    data = load_complaints()
    if "next_id" not in data:
        data["next_id"] = 1001
    cid = "CMP-" + str(data['next_id'])
    data['next_id'] += 1
    item = {
        "id": cid, "chat_id": str(chat_id), "category": category,
        "name": name, "text": text, "status": "new",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['complaints'].append(item)
    save_complaints(data)
    return item

def load_meds():
    return _load_default(MEDS_FILE, {"meds": []})

def save_meds(data):
    return _save(MEDS_FILE, data)

def create_med(chat_id, name, time_str, lang="fa"):
    data = load_meds()
    item = {
        "chat_id": str(chat_id), "name": name, "time": time_str,
        "lang": lang,
        "active": True, "last_reminded_date": "",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['meds'].append(item)
    save_meds(data)
    return item

def get_user_meds(chat_id):
    data = load_meds()
    return [m for m in data['meds'] if m['chat_id'] == str(chat_id) and m.get('active', True)]

def mark_med_reminded(chat_id, med_name, date_str):
    data = load_meds()
    for m in data['meds']:
        if m['chat_id'] == str(chat_id) and m['name'] == med_name and m.get('active', True):
            m['last_reminded_date'] = date_str
            save_meds(data)
            return True
    return False

def load_hubs():
    data = _load_default("data/transport_hubs.json", {})
    return data.get("shiraz_transport_hubs", [])

def find_hub_field(hubs, hub_key, field_key, lang):
    for f in hubs:
        if f.get("key") == field_key:
            hv = f.get(hub_key, {})
            return hv.get("value_" + lang, "") or hv.get("value_fa", "")
    return ""

def format_hub(hub_key, lang):
    hubs = load_hubs()
    if not hubs:
        return MSG[lang]["hub_not_found"]
    lines = []
    title = ""
    for f in hubs:
        if f.get("key") == "official_name":
            hv = f.get(hub_key, {})
            title = hv.get("value_" + lang, "") or hv.get("value_fa", "")
            break
    if title:
        lines.append("📍 " + title)
        lines.append("━━━━━━━━━━━━━━━")
    for field_key in HUB_FIELDS_ORDER:
        if field_key == "official_name":
            continue
        val = find_hub_field(hubs, hub_key, field_key, lang)
        if not val or val == "—":
            continue
        f_label = ""
        for f in hubs:
            if f.get("key") == field_key:
                f_label = f.get("field_" + lang, "") or f.get("field_fa", "")
                break
        if f_label:
            lines.append("• " + f_label + ": " + val)
    lat = ""
    lng = ""
    for f in hubs:
        if f.get("key") == "latitude":
            lat = f.get(hub_key, {}).get("value_fa", "")
        if f.get("key") == "longitude":
            lng = f.get(hub_key, {}).get("value_fa", "")
    if lat and lng and lat != "—" and lng != "—":
        lines.append("")
        lines.append("🗺 مسیریاب: https://www.google.com/maps/dir/?api=1&destination=" + str(lat) + "," + str(lng))
    return "\n".join(lines)

def load_all_insurances():
    all_ins = []
    for fn in ("data/ins_p1.json", "data/ins_p2.json", "data/ins_p3.json", "data/ins_p4.json"):
        data = _load_default(fn, {})
        items = data.get("insurances", [])
        if items:
            all_ins.extend(items)
    return all_ins

def find_insurance_by_id(ins_id):
    for ins in load_all_insurances():
        if ins.get("id") == ins_id:
            return ins
    return None

def format_insurance(ins, lang):
    if not ins:
        return MSG[lang]["insurance_not_found"]
    name = ins.get("name_" + lang, "") or ins.get("name_fa", "") or ins.get("id", "")
    fields = ins.get("fields", {})
    labels = INSURANCE_FIELD_LABELS.get(lang, {})
    lines = ["🏥 " + name]
    lines.append("━━━━━━━━━━━━━━━")
    for key in INSURANCE_FIELDS_ORDER:
        f = fields.get(key)
        if not f:
            continue
        val = f.get("value_" + lang, "") or f.get("value_fa", "")
        if not val or val == "—":
            continue
        label = labels.get(key, key)
        lines.append("• " + label + ": " + val)
    return "\n".join(lines)

def voice_to_text(file_url):
    try:
        r = requests.get(file_url, timeout=30)
        if r.status_code != 200:
            return None
        audio_data = r.content
        files = {"file": ("voice.ogg", audio_data, "audio/ogg")}
        headers = {"Authorization": "Bearer " + AVALAI_API_KEY}
        data = {"model": STT_MODEL}
        resp = requests.post(AVALAI_STT_URL, headers=headers, files=files, data=data, timeout=60)
        if resp.status_code != 200:
            print("STT_ERR_CODE: " + str(resp.status_code))
            return None
        result = resp.json()
        text = result.get("text", "").strip()
        return text if text else None
    except Exception as e:
        print("STT_ERR: " + str(e))
        return None

def translate_text(text, source_lang, target_lang):
    if not AVALAI_API_KEY:
        return None
    lang_names = {"fa": "فارسی", "ar": "العربية", "en": "English"}
    prompt = "Translate the following text from " + lang_names.get(source_lang, source_lang) + " to " + lang_names.get(target_lang, target_lang) + ". Output only the translation, nothing else. Text: " + text
    try:
        r = requests.post(AVALAI_URL,
            headers={"Authorization": "Bearer " + AVALAI_API_KEY, "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        if r.status_code != 200:
            return None
        result = r.json()['choices'][0]['message']['content']
        return result.strip() if result else None
    except Exception as e:
        print("TR_ERR: " + str(e))
        return None

def send_hope_flower(chat_id, lang):
    hope_key = random.choice(["hope_general_1", "hope_general_2", "hope_general_3", "hope_general_4"])
    msg = MSG2[lang].get(hope_key, "")
    try:
        bot.send_message(chat_id, "🌹\n\n" + msg, reply_markup=back_kb(lang))
    except:
        pass

def send_hope_for_stage(chat_id, lang, stage):
    key = "hope_stage_" + stage
    msg = MSG2[lang].get(key)
    if msg:
        try:
            bot.send_message(chat_id, msg)
        except:
            pass

def send_with_kb(chat_id, text, kb=None):
    try:
        if kb:
            bot.send_message(chat_id, text, reply_markup=kb)
        else:
            bot.send_message(chat_id, text)
    except Exception as e:
        print("SEND_ERR: " + str(e))

def reply_with_kb(message, text, kb=None):
    try:
        if kb:
            bot.reply_to(message, text, reply_markup=kb)
        else:
            bot.reply_to(message, text)
    except Exception as e:
        print("REPLY_ERR: " + str(e))

def get_ai(text, lang):
    prompt = SYSTEM_PROMPT + " پاسخ را به زبان " + LANG_NAMES[lang] + " بنویس."
    if not AVALAI_API_KEY:
        return None
    try:
        r = requests.post(AVALAI_URL,
            headers={"Authorization": "Bearer " + AVALAI_API_KEY, "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]},
            timeout=20)
        if r.status_code != 200:
            return None
        result = r.json()['choices'][0]['message']['content']
        if result and len(result.strip()) > 5:
            return result
        return None
    except:
        return None

def search_by_doctor_name(text):
    low = text.lower()
    st = low
    for w in ["دکتر", "doctor", "دكتور", "طبيب", "dr"]:
        st = st.replace(w, "")
    st = st.strip()
    if not st or len(st) < 3:
        return None
    for fn in set(SPECIALTY_MAP.values()):
        data = load_json("data/doctors/" + fn)
        if not data:
            continue
        for item in data:
            if item.get('status', 'active') == 'inactive':
                continue
            name = item_name_for_search(item).lower()
            if st in name or name in st:
                return item
    return None

def search_specialty(text):
    low = text.lower()
    words = english_words(text)
    scores = {}
    for k, fn in SPECIALTY_MAP.items():
        if k.isascii():
            matched = k in words or (k + "s") in words
        else:
            matched = k in low
        if matched:
            if fn not in scores:
                scores[fn] = 0
            w = len(k)
            if k in [cw.lower() for cw in CONTEXT_WORDS]:
                w = w * 0.3
            scores[fn] += w
    if not scores:
        return None
    best = max(scores, key=scores.get)
    data = load_json("data/doctors/" + best)
    if not data:
        return None
    data = [d for d in data if d.get('status', 'active') != 'inactive']
    if not data:
        return None
    def sc(x):
        r = x.get('ratings', {})
        if isinstance(r, dict) and 'patient_satisfaction_score' in r:
            return r['patient_satisfaction_score']
        return x.get('patient_satisfaction_score', x.get('rating', 0))
    try:
        data.sort(key=sc, reverse=True)
    except:
        pass
    return data

def search_non_medical(text):
    low = text.lower()
    words = english_words(text)
    scores = {}
    for fn, kws in NON_MEDICAL_MAP.items():
        s = 0
        for kw in kws:
            kl = kw.lower()
            if kl.isascii():
                matched = kl in words or (kl + "s") in words
            else:
                matched = kl in low
            if matched:
                w = len(kl)
                if kl in [cw.lower() for cw in CONTEXT_WORDS]:
                    w = w * 0.3
                s += w
        if s > 0:
            scores[fn] = s
    if not scores:
        return None
    return max(scores, key=scores.get)

def is_best_request(text):
    low = text.lower()
    words = english_words(text)
    if "بهترین" in low or "best" in words or "أفضل" in low:
        return True
    return False
def format_doctor(doc, lang):
    n = get_value(doc, 'name', lang) or ''
    s = get_value(doc, 'specialty', lang) or ''
    p = get_value(doc, 'phone', lang) or doc.get('phone', '')
    a = get_value(doc, 'office_address', lang) or get_value(doc, 'address', lang) or ''
    hs = get_value(doc, 'surgeries_done_at', lang) or []
    if isinstance(hs, str):
        hs = [hs]
    h = " - ".join(str(x) for x in hs)
    pr = get_value(doc, 'price_range_toman', lang) or get_value(doc, 'price_range', lang) or ''
    r = doc.get('patient_satisfaction_score', doc.get('rating', ''))
    lat = doc.get('lat', '')
    lng = doc.get('lng', '')
    lines = []
    if lang == "en":
        lines.append("Doctor: " + str(n))
        lines.append("Specialty: " + str(s))
        lines.append("Address: " + str(a))
        if h:
            lines.append("Hospitals: " + str(h))
        lines.append("Phone: " + str(p))
        if pr:
            lines.append("Price: " + str(pr))
        if r != '':
            lines.append("Rating: " + str(r) + "/5")
        if lat and lng:
            lines.append("Map: https://www.google.com/maps/dir/?api=1&destination=" + str(lat) + "," + str(lng))
        elif a and str(a) != 'None':
            lines.append("Map: https://www.google.com/maps/search/?api=1&query=" + quote(str(a)))
    elif lang == "ar":
        lines.append("الطبيب: " + str(n))
        lines.append("التخصص: " + str(s))
        lines.append("العنوان: " + str(a))
        if h:
            lines.append("المستشفيات: " + str(h))
        lines.append("الهاتف: " + str(p))
        if pr:
            lines.append("التكلفة: " + str(pr))
        if r != '':
            lines.append("التقييم: " + str(r) + "/5")
        if lat and lng:
            lines.append("الخريطة: https://www.google.com/maps/dir/?api=1&destination=" + str(lat) + "," + str(lng))
        elif a and str(a) != 'None':
            lines.append("الخريطة: https://www.google.com/maps/search/?api=1&query=" + quote(str(a)))
    else:
        lines.append("دکتر: " + str(n))
        lines.append("تخصص: " + str(s))
        lines.append("آدرس: " + str(a))
        if h:
            lines.append("بیمارستان: " + str(h))
        lines.append("تلفن: " + str(p))
        if pr:
            lines.append("قیمت: " + str(pr))
        if r != '':
            lines.append("امتیاز: " + str(r) + "/5")
        if lat and lng:
            lines.append("مسیریاب: https://www.google.com/maps/dir/?api=1&destination=" + str(lat) + "," + str(lng))
        elif a and str(a) != 'None':
            lines.append("مسیریاب: https://www.google.com/maps/search/?api=1&query=" + quote(str(a)))
    return "\n".join(lines)

def format_generic(item, lang):
    if not isinstance(item, dict):
        return str(item)
    fnames = FIELD_NAMES.get(lang, {})
    lines = []
    seen = set()
    skip_keys = ('id', 'status', 'lat', 'lng', 'created_at', 'updated_at', 'pkg_id', 'type')
    for k, v in item.items():
        if k in skip_keys:
            continue
        if k.endswith("_fa") or k.endswith("_ar") or k.endswith("_en"):
            bk = k[:-3]
            if bk in seen:
                continue
            val = None
            for p in [lang, "fa", "en", "ar"]:
                pk = bk + "_" + p
                if pk in item:
                    val = item[pk]
                    break
            if val is None:
                continue
            seen.add(bk)
            label = fnames.get(bk, bk)
        else:
            if k in seen:
                continue
            seen.add(k)
            val = v
            label = fnames.get(k, k)
        if val is None:
            continue
        if isinstance(val, dict):
            if lang in val:
                val = val[lang]
            elif "fa" in val:
                val = val["fa"]
            elif "en" in val:
                val = val["en"]
            else:
                continue
        if isinstance(val, list):
            val = " - ".join(str(x) for x in val)
        elif isinstance(val, bool):
            if k in ("has_home_service", "has_translator"):
                val = "✅" if val else "❌"
        sv = str(val).strip()
        if sv and sv != 'None':
            lines.append(str(label) + ": " + sv)
    lat = item.get('lat', '')
    lng = item.get('lng', '')
    addr = get_value(item, 'address', lang)
    if lat and lng:
        lines.append("مسیریاب: https://www.google.com/maps/dir/?api=1&destination=" + str(lat) + "," + str(lng))
    elif addr and str(addr) != 'None':
        lines.append("مسیریاب: https://www.google.com/maps/search/?api=1&query=" + quote(str(addr)))
    return "\n".join(lines)

def set_doctor_status(doc_id, new_status):
    for fn in set(SPECIALTY_MAP.values()):
        path = "data/doctors/" + fn
        data = load_json(path)
        if not data:
            continue
        found = False
        for item in data:
            if item.get('id', '') == doc_id:
                item['status'] = new_status
                item['updated_at'] = datetime.now().strftime("%Y/%m/%d %H:%M")
                found = True
                break
        if found:
            _save(path, data)
            return True
    return False

def get_pending_reminders(now_local):
    data = load_appointments()
    one_day = []
    two_hours = []
    for a in data['appointments']:
        if a.get('status') != 'confirmed':
            continue
        dt = parse_apt_datetime(a)
        if dt is None:
            continue
        diff = dt - now_local
        diff_min = diff.total_seconds() / 60.0
        if not a.get('reminded_1d'):
            if 23.5 * 60 <= diff_min <= 24.5 * 60:
                one_day.append(a)
        if not a.get('reminded_2h'):
            if 1.5 * 60 <= diff_min <= 2.5 * 60:
                two_hours.append(a)
    return one_day, two_hours

def get_pending_med_reminders(now_local):
    data = load_meds()
    result = []
    today_str = now_local.strftime("%Y/%m/%d")
    for m in data['meds']:
        if not m.get('active', True):
            continue
        if m.get('last_reminded_date') == today_str:
            continue
        mt = m.get('time', '')
        if not mt:
            continue
        try:
            hh, mm = int(mt.split(':')[0]), int(mt.split(':')[1])
        except:
            continue
        target_min = hh * 60 + mm
        now_min = now_local.hour * 60 + now_local.minute
        if 0 <= (target_min - now_min) <= 30:
            result.append(m)
    return result

def _send_apt_reminder(apt, kind):
    lang = apt.get('patient_lang', 'fa')
    cid = apt.get('patient_chat_id', '')
    if not cid:
        return
    dn = apt.get("doctor_name_" + lang) or apt.get("doctor_name_fa", "")
    ad = apt.get("doctor_address_" + lang) or apt.get("doctor_address_fa", "")
    try:
        if kind == "1d":
            txt = MSG[lang]["remind_apt_1d"].format(time=apt.get('time', ''), doctor=dn, address=ad)
        else:
            txt = MSG[lang]["remind_apt_2h"].format(time=apt.get('time', ''), doctor=dn, address=ad)
        bot.send_message(cid, txt, reply_markup=back_kb(lang))
    except Exception as e:
        print("APT_REMIND_ERR: " + str(e))

def _send_med_reminder(med, today_str):
    cid = med.get('chat_id', '')
    if not cid:
        return
    lang = med.get('lang', 'fa')
    try:
        bot.send_message(cid, MSG[lang]["remind_med"].format(med=med.get('name', '')))
        mark_med_reminded(cid, med.get('name', ''), today_str)
    except Exception as e:
        print("MED_REMIND_ERR: " + str(e))

def reminder_worker():
    print("REMINDER_WORKER: started (loop every 15 min)")
    time_module.sleep(30)
    while True:
        try:
            now_local = local_now()
            one_d, two_h = get_pending_reminders(now_local)
            for apt in one_d:
                _send_apt_reminder(apt, "1d")
                mark_reminded(apt['id'], 'reminded_1d')
            for apt in two_h:
                _send_apt_reminder(apt, "2h")
                mark_reminded(apt['id'], 'reminded_2h')
            today_str = now_local.strftime("%Y/%m/%d")
            meds_due = get_pending_med_reminders(now_local)
            for m in meds_due:
                _send_med_reminder(m, today_str)
        except Exception as e:
            print("REMINDER_LOOP_ERR: " + str(e))
        time_module.sleep(15 * 60)

def ask_more(message):
    cid = message.chat.id
    user_state[cid] = "awaiting_more"
    reply_with_kb(message, MSG[user_lang.get(cid, "fa")]["more"])

def get_meta_info():
    try:
        with open("data/meta.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def show_main_menu(message, lang):
    reply_with_kb(message, MSG2[lang]["menu_main"], main_menu_kb(lang))

def process_query(message, text, lang):
    cid = message.chat.id

    if is_simple_cmd(text, CMD_MENU):
        show_main_menu(message, lang)
        return True
    if is_simple_cmd(text, CMD_FILE):
        p = get_patient_by_chat(cid)
        reply_with_kb(message, format_patient_file(p, lang), back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_APT):
        apts = get_patient_appointments(cid)
        if not apts:
            reply_with_kb(message, MSG[lang]["apt_none"], back_kb(lang))
            return True
        lines = [MSG[lang]["apt_my"]]
        for a in apts[-5:]:
            dn = a.get("doctor_name_" + lang) or a.get("doctor_name_fa", "")
            st = a.get('status', 'pending')
            if st == 'done':
                lines.append(MSG[lang]["pt_apt_line_done"].format(id=a['id'], doctor=dn))
            elif st == 'confirmed' and a.get('date'):
                lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                    id=a['id'], doctor=dn, date=a['date'], time=a.get('time', '')))
            else:
                lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a['id'], doctor=dn))
        reply_with_kb(message, "\n\n".join(lines), back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_COMPANION):
        user_state[cid] = "awaiting_comp_ask"
        reply_with_kb(message, MSG2[lang]["comp_ask"])
        return True
    if is_simple_cmd(text, CMD_COMPLAINT):
        user_state[cid] = "awaiting_complaint_menu"
        reply_with_kb(message, MSG2[lang]["comp_voice_menu"])
        return True
    if is_simple_cmd(text, CMD_MED):
        user_state[cid] = "awaiting_med_menu"
        reply_with_kb(message, MSG2[lang]["med_menu"])
        return True
    if is_simple_cmd(text, CMD_RIGHTS):
        reply_with_kb(message, MSG2[lang]["rights_title"] + "\n\n" + MSG2[lang]["rights_body"], back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_FOOD):
        reply_with_kb(message, MSG2[lang]["food_title"] + "\n\n" + MSG2[lang]["food_body"], back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_FLOWER):
        send_hope_flower(cid, lang)
        return True
    if is_simple_cmd(text, CMD_SOS):
        reply_with_kb(message, MSG2[lang]["sos_menu"])
        user_state[cid] = "awaiting_sos_choice"
        return True
    if is_simple_cmd(text, CMD_INVITE):
        code = get_or_create_referral_code(cid)
        link = build_referral_link(code)
        reply_with_kb(message, MSG2[lang]["ref_invite_msg"].format(code=code, link=link), back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_NIGHT):
        reply_with_kb(message, MSG2[lang]["hope_night"], back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_DELETE):
        user_state[cid] = "awaiting_delete_confirm"
        reply_with_kb(message, MSG[lang]["delete_ask"])
        return True
    if is_simple_cmd(text, CMD_PACKAGE):
        reply_with_kb(message, MSG2[lang]["package_title"], None)
        reply_with_kb(message, MSG2[lang]["package_pitch"], None)
        reply_with_kb(message, MSG2[lang]["package_value"], package_kb(lang))
        return True
    if is_simple_cmd(text, CMD_PARA):
        reply_with_kb(message, MSG2[lang]["para_list_title"], para_kb(lang))
        return True
    if is_simple_cmd(text, CMD_ELDERLY_ALL):
        data = load_json("data/elderly_homes.json")
        if data:
            bot.reply_to(message, MSG2[lang]["elderly_all_title"])
            for item in data[:10]:
                reply_with_kb(message, format_generic(item, lang), back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_ELDERLY):
        reply_with_kb(message, MSG2[lang]["elderly_list_title"], elderly_kb(lang))
        return True
    if is_simple_cmd(text, CMD_CHANNEL):
        if is_channel_joined(cid):
            reply_with_kb(message, MSG_CH[lang]["msg_channel_already"], back_kb(lang))
            return True
        reply_with_kb(message, MSG_CH[lang]["msg_channel"], channel_kb(lang))
        return True
    if is_simple_cmd(text, CMD_TAXI):
        reply_with_kb(message, MSG[lang]["taxi_title"], taxi_kb(lang))
        return True
    if is_simple_cmd(text, CMD_HUBS):
        reply_with_kb(message, MSG2[lang]["hubs_title"], hubs_kb(lang))
        return True
    if is_simple_cmd(text, CMD_INSURANCE):
        reply_with_kb(message, MSG[lang]["insurance_title"], insurance_kb(lang, 0))
        return True
    if is_simple_cmd(text, CMD_TRANSLATOR):
        reply_with_kb(message, MSG[lang]["translator_title"], translator_lang_kb(lang))
        return True
    if is_simple_cmd(text, CMD_CHARTER):
        txt = MSG[lang]["charter_title"] + "\n\n" + MSG[lang]["charter_body"]
        reply_with_kb(message, txt, back_kb(lang))
        return True
    if is_simple_cmd(text, CMD_DEEPSEEK):
        reply_with_kb(message, MSG[lang]["deepseek_title"], deepseek_kb(lang))
        return True

    doc = search_by_doctor_name(text)
    if doc:
        doc_id = doc.get('id', '')
        reply_with_kb(message, format_doctor(doc, lang), doctor_action_kb(lang, doc_id))
        user_temp[cid] = {"doctor": doc}
        return True

    docs = search_specialty(text)
    if docs:
        if is_all_request(text):
            limit = min(len(docs), 10)
        elif is_best_request(text):
            limit = 1
        else:
            limit = 3
        shown = docs[:limit]
        for d in shown:
            did = d.get('id', '')
            reply_with_kb(message, format_doctor(d, lang), doctor_action_kb(lang, did))
        if len(shown) >= 1:
            user_temp[cid] = {"doctor": shown[0]}
        return True

    fn = search_non_medical(text)
    if fn:
        data = load_json("data/" + fn)
        if data:
            items = data[:10] if is_all_request(text) else data[:5]
            for item in items:
                reply_with_kb(message, format_generic(item, lang), back_kb(lang))
            return True

    ai = get_ai(text, lang)
    if ai:
        reply_with_kb(message, ai + AI_DISCLAIMER[lang], back_kb(lang))
        return True
    reply_with_kb(message, MSG2[lang]["ai_unavailable"], back_kb(lang))
    return True
@bot.message_handler(commands=['id'])
def id_command(message):
    bot.reply_to(message, str(message.chat.id))

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    meta = get_meta_info()
    apt_data = load_appointments()
    pending = [a for a in apt_data['appointments'] if a.get('status') == 'pending']
    confirmed = [a for a in apt_data['appointments'] if a.get('status') == 'confirmed']
    done = [a for a in apt_data['appointments'] if a.get('status') == 'done']
    rated = [a for a in apt_data['appointments'] if a.get('rating', 0) > 0]
    avg_rating = 0
    if rated:
        avg_rating = round(sum(a['rating'] for a in rated) / len(rated), 1)
    complaints = load_complaints().get('complaints', [])
    new_complaints = [c for c in complaints if c.get('status') == 'new']
    pkg_data = load_packages()
    pending_pkgs = [p for p in pkg_data['packages'] if p.get('status') == 'pending']
    stats = get_user_stats()
    lines = ["📊 وضعیت ربات"]
    if meta:
        lines.append("آخرین آپدیت: " + str(meta.get("last_update", "نامشخص")))
    lines.append("")
    lines.append("👥 کاربران:")
    lines.append("• کل: " + str(stats['total']))
    lines.append("• امروز: " + str(stats['dau']))
    lines.append("• ۷ روز: " + str(stats['wau']))
    lines.append("• ۳۰ روز: " + str(stats['mau']))
    lines.append("")
    lines.append("📈 نرخ تبدیل: " + str(stats['conv']) + "%")
    lines.append("📢 عضو کانال: " + str(stats.get('channel', 0)))
    lines.append("")
    lines.append("📅 نوبت‌ها:")
    lines.append("• در انتظار: " + str(len(pending)))
    lines.append("• تأیید شده: " + str(len(confirmed)))
    lines.append("• انجام شده: " + str(len(done)))
    if pending:
        for a in pending[-5:]:
            dn = a.get("doctor_name_fa", "")
            lines.append("• " + a['id'] + " — " + a.get('patient_name', '') + " — " + str(dn))
    lines.append("")
    lines.append("⭐ نظرسنجی:")
    lines.append("• تعداد نظر: " + str(len(rated)))
    lines.append("• میانگین: " + str(avg_rating) + "/5")
    lines.append("")
    lines.append("💎 پکیج‌های در انتظار: " + str(len(pending_pkgs)))
    if pending_pkgs:
        for p in pending_pkgs[-3:]:
            lines.append("• " + p['id'] + " — " + p.get('name', '') + " — " + p.get('phone', ''))
    lines.append("")
    lines.append("📩 شکایت جدید: " + str(len(new_complaints)))
    lines.append("")
    lines.append("⏰ زمان سرور (local): " + local_now().strftime("%Y/%m/%d %H:%M"))
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['confirm'])
def confirm_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 4:
        bot.reply_to(message, "فرمت: /confirm APT-1001 1405/09/20 10:30")
        return
    apt_id = parts[1].upper()
    date_str = validate_date_shamsi(parts[2])
    time_str = validate_time(parts[3])
    if not date_str or not time_str:
        bot.reply_to(message, "❌ تاریخ یا ساعت نامعتبر.")
        return
    apt = confirm_appointment(apt_id, date_str, time_str)
    if not apt:
        bot.reply_to(message, "❌ نوبت پیدا نشد.")
        return
    bot.reply_to(message, "✅ نوبت " + apt_id + " تأیید شد.")
    update_patient_stage(apt.get('patient_chat_id'), 'date', True)
    patient_cid = apt.get('patient_chat_id', '')
    p_lang = apt.get('patient_lang', 'fa')
    if patient_cid:
        dn = apt.get("doctor_name_" + p_lang) or apt.get("doctor_name_fa", "")
        ad = apt.get("doctor_address_" + p_lang) or apt.get("doctor_address_fa", "")
        try:
            bot.send_message(patient_cid, MSG[p_lang]["apt_patient_confirmed"].format(
                id=apt_id, doctor=dn, date=date_str, time=time_str, address=ad))
            send_hope_for_stage(patient_cid, p_lang, "date")
        except:
            pass

@bot.message_handler(commands=['done'])
def done_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "فرمت: /done APT-1001")
        return
    apt_id = parts[1].upper()
    apt = mark_apt_done(apt_id)
    if not apt:
        bot.reply_to(message, MSG["fa"]["apt_done_admin_bad"].format(id=apt_id))
        return
    bot.reply_to(message, MSG["fa"]["apt_done_admin_ok"].format(id=apt_id))
    patient_cid = apt.get('patient_chat_id', '')
    p_lang = apt.get('patient_lang', 'fa')
    update_patient_stage(patient_cid, 'treatment', True)
    if patient_cid:
        try:
            bot.send_message(patient_cid, MSG[p_lang]["apt_done_patient"],
                reply_markup=rate_kb(p_lang, apt_id))
        except:
            pass

@bot.message_handler(commands=['pt'])
def pt_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "فرمت: /pt PT-1001")
        return
    code = parts[1].upper()
    p = get_patient_by_code(code)
    if not p:
        bot.reply_to(message, "❌ پرونده پیدا نشد.")
        return
    bot.reply_to(message, format_patient_file(p, p.get('lang', 'fa')))

@bot.message_handler(commands=['deactivate'])
def deactivate_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "فرمت: /deactivate doc_001")
        return
    if set_doctor_status(parts[1], 'inactive'):
        bot.reply_to(message, "✅ غیرفعال شد.")
    else:
        bot.reply_to(message, "❌ پیدا نشد.")

@bot.message_handler(commands=['activate'])
def activate_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "فرمت: /activate doc_001")
        return
    if set_doctor_status(parts[1], 'active'):
        bot.reply_to(message, "✅ فعال شد.")
    else:
        bot.reply_to(message, "❌ پیدا نشد.")

@bot.message_handler(commands=['lang'])
def lang_command(message):
    user_state[message.chat.id] = "choose_lang"
    bot.reply_to(message, START_MSG)

@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    user_state[cid] = "choose_lang"
    if cid in user_lang:
        register_user(cid, user_lang[cid])
    bot.reply_to(message, START_MSG)
    try_apply_start_param(message, message.text or "", user_lang.get(cid, "fa"))

@bot.message_handler(commands=['menu'])
def menu_command(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    show_main_menu(message, lang)

@bot.message_handler(commands=['myapt'])
def myapt_command(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    apts = get_patient_appointments(cid)
    if not apts:
        bot.reply_to(message, MSG[lang]["apt_none"])
        return
    lines = [MSG[lang]["apt_my"]]
    for a in apts[-5:]:
        dn = a.get("doctor_name_" + lang) or a.get("doctor_name_fa", "")
        st = a.get('status', 'pending')
        if st == 'done':
            lines.append(MSG[lang]["pt_apt_line_done"].format(id=a['id'], doctor=dn))
        elif st == 'confirmed' and a.get('date'):
            lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                id=a['id'], doctor=dn, date=a['date'], time=a.get('time', '')))
        else:
            lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a['id'], doctor=dn))
    bot.reply_to(message, "\n\n".join(lines))

@bot.message_handler(commands=['myfile'])
def myfile_command(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    p = get_patient_by_chat(cid)
    bot.reply_to(message, format_patient_file(p, lang))

@bot.message_handler(commands=['mycode'])
def mycode_command(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    code = get_or_create_referral_code(cid)
    link = build_referral_link(code)
    bot.reply_to(message, MSG2[lang]["ref_your_code"].format(code=code, link=link))

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    state = user_state.get(cid)
    if state != "awaiting_voice_translate":
        if cid in user_lang:
            bot.reply_to(message, MSG[lang]["text_only"])
        else:
            user_state[cid] = "choose_lang"
            bot.reply_to(message, START_MSG)
        return
    try:
        duration = message.voice.duration or 0
        if duration > MAX_VOICE_SECONDS:
            bot.reply_to(message, MSG[lang]["translator_too_long"])
            return
        bot.reply_to(message, MSG[lang]["translator_processing"])
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file_url = "https://tapi.bale.ai/file/bot" + BALE_BOT_TOKEN + "/" + file_info.file_path
        text = voice_to_text(file_url)
        if not text:
            bot.reply_to(message, MSG[lang]["translator_error"], reply_markup=back_kb(lang))
            return
        tr = user_temp.get(cid, {})
        source = tr.get("tr_source", "fa")
        target = tr.get("tr_target", "ar")
        translated = translate_text(text, source, target)
        if not translated:
            bot.reply_to(message, MSG[lang]["translator_error"], reply_markup=back_kb(lang))
            return
        result_msg = MSG[lang]["translator_result"].format(original=text, translated=translated)
        bot.reply_to(message, result_msg, reply_markup=translator_result_kb(lang, translated, target))
    except Exception as e:
        print("VOICE_ERR: " + str(e))
        bot.reply_to(message, MSG[lang]["translator_error"], reply_markup=back_kb(lang))

@bot.message_handler(content_types=['photo', 'audio', 'document', 'video', 'sticker'])
def other_types(message):
    cid = message.chat.id
    if cid in user_lang:
        bot.reply_to(message, MSG[user_lang[cid]]["text_only"])
    else:
        user_state[cid] = "choose_lang"
        bot.reply_to(message, START_MSG)
@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    try:
        cid = call.message.chat.id
        lang = user_lang.get(cid, "fa")
        data = call.data

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        if data.startswith("rate_"):
            parts = data.split("_")
            stars = int(parts[1])
            apt_id = parts[2]
            set_apt_rating(apt_id, stars)
            save_rating(apt_id, cid, stars, "")
            satisfaction_counter["count"] += 1
            if stars >= 4:
                satisfaction_counter["positive"] += 1
                update_patient_stage(cid, 'followup', True)
                code = get_or_create_referral_code(cid)
                link = build_referral_link(code)
                if stars == 5:
                    bot.send_message(cid, MSG[lang]["rate_thanks_5"])
                else:
                    bot.send_message(cid, MSG[lang]["rate_thanks_4"])
                bot.send_message(cid, MSG2[lang]["ref_invite_msg"].format(code=code, link=link))
            elif stars == 3:
                bot.send_message(cid, MSG[lang]["rate_thanks_3"])
            else:
                satisfaction_counter["negative"] += 1
                user_state[cid] = "awaiting_rate_feedback_" + apt_id
                bot.send_message(cid, MSG[lang]["rate_thanks_low"])
            return

        if data == "do_channel":
            if is_channel_joined(cid):
                send_with_kb(cid, MSG_CH[lang]["msg_channel_already"], back_kb(lang))
                return
            send_with_kb(cid, MSG_CH[lang]["msg_channel"], channel_kb(lang))
            return

        if data == "channel_confirm":
            if is_channel_joined(cid):
                send_with_kb(cid, MSG_CH[lang]["msg_channel_already"], back_kb(lang))
                return
            ok = grant_channel_reward(cid)
            if ok:
                send_with_kb(cid, MSG_CH[lang]["msg_channel_done"], back_kb(lang))
                if ADMIN_CHAT_ID:
                    try:
                        bot.send_message(ADMIN_CHAT_ID, "📢 عضو جدید کانال: " + str(cid))
                    except:
                        pass
            else:
                send_with_kb(cid, MSG_CH[lang]["msg_channel_already"], back_kb(lang))
            return

        if data == "do_taxi":
            send_with_kb(cid, MSG[lang]["taxi_title"], taxi_kb(lang))
            return

        if data == "do_hubs":
            send_with_kb(cid, MSG2[lang]["hubs_title"], hubs_kb(lang))
            return

        if data.startswith("hub_"):
            hub_id = data[4:]
            txt = format_hub(hub_id, lang)
            send_with_kb(cid, txt, hub_action_kb(lang, hub_id))
            return

        if data == "do_insurance":
            send_with_kb(cid, MSG[lang]["insurance_title"], insurance_kb(lang, 0))
            return

        if data.startswith("ins_page_"):
            try:
                page = int(data.replace("ins_page_", ""))
            except:
                page = 0
            try:
                bot.edit_message_text(
                    chat_id=cid,
                    message_id=call.message.message_id,
                    text=MSG[lang]["insurance_title"],
                    reply_markup=insurance_kb(lang, page)
                )
            except:
                send_with_kb(cid, MSG[lang]["insurance_title"], insurance_kb(lang, page))
            return

        if data.startswith("ins_"):
            ins_id = data[4:]
            ins = find_insurance_by_id(ins_id)
            if not ins:
                send_with_kb(cid, MSG[lang]["insurance_not_found"], back_kb(lang))
                return
            txt = format_insurance(ins, lang)
            send_with_kb(cid, txt, insurance_action_kb(lang))
            return

        if data == "do_translator":
            send_with_kb(cid, MSG[lang]["translator_title"], translator_lang_kb(lang))
            return

        if data in ("tr_fa_ar", "tr_ar_fa", "tr_fa_en", "tr_en_fa"):
            parts = data.split("_")
            source = parts[1]
            target = parts[2]
            user_temp[cid] = {"tr_source": source, "tr_target": target}
            user_state[cid] = "awaiting_voice_translate"
            send_with_kb(cid, MSG[lang]["translator_active"], back_kb(lang))
            return

        if data == "do_charter":
            txt = MSG[lang]["charter_title"] + "\n\n" + MSG[lang]["charter_body"]
            send_with_kb(cid, txt, back_kb(lang))
            return

        if data == "do_deepseek":
            send_with_kb(cid, MSG[lang]["deepseek_title"], deepseek_kb(lang))
            return

        if data == "back_main":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["menu_main"], reply_markup=main_menu_kb(lang))
            except:
                show_main_menu(call.message, lang)
            return

        if data == "menu_docs":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["docs_list_title"], reply_markup=specialties_kb(lang))
            except:
                send_with_kb(cid, MSG2[lang]["docs_list_title"], specialties_kb(lang))
            return

        if data.startswith("spec_"):
            fn = data[5:] + ".json"
            docs = load_json("data/doctors/" + fn)
            if not docs:
                send_with_kb(cid, "❌ اطلاعاتی یافت نشد.")
                return
            docs = [d for d in docs if d.get('status', 'active') != 'inactive']
            if not docs:
                send_with_kb(cid, "❌ پزشکی نیست.")
                return
            def sc(x):
                r = x.get('ratings', {})
                if isinstance(r, dict) and 'patient_satisfaction_score' in r:
                    return r['patient_satisfaction_score']
                return x.get('patient_satisfaction_score', x.get('rating', 0))
            try:
                docs.sort(key=sc, reverse=True)
            except:
                pass
            for d in docs[:3]:
                did = d.get('id', '')
                send_with_kb(cid, format_doctor(d, lang), doctor_action_kb(lang, did))
            return

        if data == "menu_nonmed":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["nonmed_list_title"], reply_markup=nonmed_kb(lang))
            except:
                send_with_kb(cid, MSG2[lang]["nonmed_list_title"], nonmed_kb(lang))
            return

        if data.startswith("non_"):
            fn = data[4:] + ".json"
            items = load_json("data/" + fn)
            if not items:
                send_with_kb(cid, "❌ اطلاعاتی یافت نشد.")
                return
            for item in items[:5]:
                send_with_kb(cid, format_generic(item, lang), back_kb(lang))
            return

        if data == "menu_tourist":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["tourist_list_title"], reply_markup=tourist_kb(lang))
            except:
                send_with_kb(cid, MSG2[lang]["tourist_list_title"], tourist_kb(lang))
            return

        if data == "menu_para":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["para_list_title"], reply_markup=para_kb(lang))
            except:
                send_with_kb(cid, MSG2[lang]["para_list_title"], para_kb(lang))
            return

        if data == "para_search":
            send_with_kb(cid, MSG2[lang]["para_list_title"], para_kb(lang))
            return

        if data == "menu_elder":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["elderly_list_title"], reply_markup=elderly_kb(lang))
            except:
                send_with_kb(cid, MSG2[lang]["elderly_list_title"], elderly_kb(lang))
            return

        if data == "elder_all":
            data_e = load_json("data/elderly_homes.json")
            if data_e:
                send_with_kb(cid, MSG2[lang]["elderly_all_title"])
                for item in data_e[:10]:
                    send_with_kb(cid, format_generic(item, lang), back_kb(lang))
            return

        if data == "menu_pkg":
            try:
                bot.edit_message_text(chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["package_title"], reply_markup=package_kb(lang))
            except:
                send_with_kb(cid, MSG2[lang]["package_title"], package_kb(lang))
            return

        if data == "pkg_order":
            send_with_kb(cid, MSG2[lang]["package_pitch"])
            send_with_kb(cid, MSG2[lang]["package_value"])
            send_with_kb(cid, MSG2[lang]["package_cta"])
            user_state[cid] = "awaiting_pkg_name"
            send_with_kb(cid, MSG2[lang]["package_ask_name"])
            return

        if data.startswith("book_"):
            doc_id = data[5:]
            doc = None
            for fn in set(SPECIALTY_MAP.values()):
                items = load_json("data/doctors/" + fn)
                for d in items:
                    if d.get('id', '') == doc_id:
                        doc = d
                        break
                if doc:
                    break
            if not doc:
                send_with_kb(cid, "❌ پزشک پیدا نشد.")
                return
            user_temp[cid] = {"doctor": doc}
            user_state[cid] = "awaiting_apt_name"
            send_with_kb(cid, MSG[lang]["apt_name"])
            return

        if data.startswith("call_"):
            doc_id = data[5:]
            doc = None
            for fn in set(SPECIALTY_MAP.values()):
                items = load_json("data/doctors/" + fn)
                for d in items:
                    if d.get('id', '') == doc_id:
                        doc = d
                        break
                if doc:
                    break
            if not doc:
                send_with_kb(cid, "❌ پزشک پیدا نشد.")
                return
            send_with_kb(cid, "📞 تلفن:\n" + str(doc.get('phone', '')), back_kb(lang))
            return

        if data == "do_file":
            p = get_patient_by_chat(cid)
            send_with_kb(cid, format_patient_file(p, lang), back_kb(lang))
            return
        if data == "do_apt":
            apts = get_patient_appointments(cid)
            if not apts:
                send_with_kb(cid, MSG[lang]["apt_none"], back_kb(lang))
                return
            lines = [MSG[lang]["apt_my"]]
            for a in apts[-5:]:
                dn = a.get("doctor_name_" + lang) or a.get("doctor_name_fa", "")
                st = a.get('status', 'pending')
                if st == 'done':
                    lines.append(MSG[lang]["pt_apt_line_done"].format(id=a['id'], doctor=dn))
                elif st == 'confirmed' and a.get('date'):
                    lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                        id=a['id'], doctor=dn, date=a['date'], time=a.get('time', '')))
                else:
                    lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a['id'], doctor=dn))
            send_with_kb(cid, "\n\n".join(lines), back_kb(lang))
            return
        if data == "do_med":
            user_state[cid] = "awaiting_med_menu"
            send_with_kb(cid, MSG2[lang]["med_menu"])
            return
        if data == "do_sos":
            user_state[cid] = "awaiting_sos_choice"
            send_with_kb(cid, MSG2[lang]["sos_menu"])
            return
        if data == "do_invite":
            code = get_or_create_referral_code(cid)
            link = build_referral_link(code)
            send_with_kb(cid, MSG2[lang]["ref_invite_msg"].format(code=code, link=link), back_kb(lang))
            return
        if data == "do_help":
            send_with_kb(cid, MSG2[lang]["rights_title"] + "\n\n" + MSG2[lang]["rights_body"], back_kb(lang))
            return

    except Exception as e:
        print("CB_ERR: " + str(e))
@bot.message_handler(func=lambda m: True)
def handle(message):
    cid = message.chat.id
    text = message.text or ""
    state = user_state.get(cid)

    if state is None or state == "choose_lang":
        lang = pick_language(text)
        if lang is None:
            user_state[cid] = "choose_lang"
            bot.reply_to(message, START_MSG)
            return
        user_lang[cid] = lang
        user_state[cid] = "active"
        register_user(cid, lang)
        try:
            bot.send_message(cid, MSG[lang]["welcome"], reply_markup=main_menu_kb(lang))
            bot.send_message(cid, MSG[lang]["welcome_text"])
        except:
            bot.reply_to(message, MSG[lang]["welcome"])
        try_apply_start_param(message, text, lang)
        return

    lang = user_lang.get(cid, "fa")
    t = clean(text)
    user_name = get_user_name(message)

    ESCAPE_WORDS = {"منو", "لغو", "انصراف", "menu", "cancel"}
    if t in ESCAPE_WORDS:
        user_state[cid] = "active"
        user_temp.pop(cid, None)
        show_main_menu(message, lang)
        return

    if state and state.startswith("awaiting_rate_feedback_"):
        apt_id = state.replace("awaiting_rate_feedback_", "")
        apt = find_appointment(apt_id)
        pname = apt.get('patient_name', '') if apt else ''
        try:
            bot.send_message(ADMIN_CHAT_ID, MSG["fa"]["rate_thanks_low_admin"].format(
                id=apt_id, stars=apt.get('rating', 0), name=pname, cid=cid, text=text))
        except:
            pass
        reply_with_kb(message, MSG[lang]["rate_feedback_thanks"], back_kb(lang))
        user_state[cid] = "active"
        return

    if state == "awaiting_voice_translate":
        bot.reply_to(message, MSG[lang]["translator_active"])
        return

    if state == "awaiting_pkg_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG2[lang]["package_ask_name"])
            return
        if cid not in user_temp:
            user_temp[cid] = {}
        user_temp[cid]["pkg_name"] = text.strip()
        user_state[cid] = "awaiting_pkg_phone"
        bot.reply_to(message, MSG2[lang]["package_ask_phone"])
        return

    if state == "awaiting_pkg_phone":
        phone = validate_phone(text)
        if not phone:
            bot.reply_to(message, MSG2[lang]["package_ask_phone"])
            return
        pkg_name = user_temp.get(cid, {}).get("pkg_name", "")
        try:
            pkg = create_package(cid, pkg_name, phone, lang)
            bot.reply_to(message, MSG2[lang]["package_saved"].format(id=pkg['id']))
            if ADMIN_CHAT_ID:
                try:
                    bot.send_message(ADMIN_CHAT_ID, MSG2["fa"]["package_admin_new"].format(
                        id=pkg['id'], name=pkg_name, phone=phone, cid=cid))
                except:
                    pass
        except Exception as e:
            print("PKG_ERR: " + str(e))
            bot.reply_to(message, MSG[lang]["apt_error"])
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    if state == "awaiting_apt_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG[lang]["apt_name"])
            return
        if cid not in user_temp:
            user_temp[cid] = {}
        user_temp[cid]["name"] = text.strip()
        user_state[cid] = "awaiting_apt_phone"
        bot.reply_to(message, MSG[lang]["apt_phone"])
        return

    if state == "awaiting_apt_phone":
        phone = validate_phone(text)
        if not phone:
            bot.reply_to(message, MSG[lang]["apt_phone"])
            return
        user_temp[cid]["phone"] = phone
        user_state[cid] = "awaiting_apt_confirm"
        doc = user_temp.get(cid, {}).get("doctor", {})
        dn = get_value(doc, 'name', lang) or get_value(doc, 'name', 'fa') or ''
        bot.reply_to(message, MSG[lang]["apt_confirm_final"].format(
            name=user_temp[cid].get("name", ""), phone=phone, doctor=dn))
        return

    if state == "awaiting_apt_confirm":
        if t in YES_WORDS:
            doc = user_temp.get(cid, {}).get("doctor", {})
            pname = user_temp.get(cid, {}).get("name", "")
            pphone = user_temp.get(cid, {}).get("phone", "")
            try:
                apt = create_appointment(doc, pname, pphone, cid, lang)
                patient = create_or_get_patient(cid, pname, pphone, lang)
                add_appointment_to_patient(cid, apt['id'])
                update_patient_stage(cid, 'doctor', True)
                register_appointment_for_stats(cid)
                dn = get_value(doc, 'name', lang) or get_value(doc, 'name', 'fa') or ''
                bot.reply_to(message, MSG[lang]["apt_submitted"].format(id=apt['id'], doctor=dn))
                bot.reply_to(message, MSG[lang]["pt_created"].format(code=patient['code']))
                send_hope_for_stage(cid, lang, "request")
                if ADMIN_CHAT_ID:
                    try:
                        dphone = doc.get("phone", "")
                        bot.send_message(ADMIN_CHAT_ID, MSG["fa"]["apt_admin_new"].format(
                            id=apt['id'], name=pname, phone=pphone, doctor=dn, dphone=dphone))
                    except:
                        pass
            except Exception as e:
                print("APT_ERR: " + str(e))
                bot.reply_to(message, MSG[lang]["apt_error"])
            user_temp.pop(cid, None)
            user_state[cid] = "awaiting_comp_ask"
            bot.reply_to(message, MSG2[lang]["comp_ask"])
            return
        if t in NO_WORDS:
            user_temp.pop(cid, None)
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            ask_more(message)
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
        return

    if state == "awaiting_comp_ask":
        if t in YES_WORDS:
            user_state[cid] = "awaiting_comp_name"
            bot.reply_to(message, MSG2[lang]["comp_ask_name"])
            return
        if t in NO_WORDS:
            user_state[cid] = "active"
            bot.reply_to(message, MSG2[lang]["comp_skip"])
            ask_more(message)
            return
        user_state[cid] = "active"

    if state == "awaiting_comp_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG2[lang]["comp_ask_name"])
            return
        if cid not in user_temp:
            user_temp[cid] = {}
        user_temp[cid]["comp_name"] = text.strip()
        user_state[cid] = "awaiting_comp_phone"
        bot.reply_to(message, MSG2[lang]["comp_ask_phone"])
        return

    if state == "awaiting_comp_phone":
        phone = validate_phone(text)
        if not phone:
            bot.reply_to(message, MSG2[lang]["comp_ask_phone"])
            return
        comp_name = user_temp.get(cid, {}).get("comp_name", "")
        set_companion(cid, comp_name, phone)
        bot.reply_to(message, MSG2[lang]["comp_saved"].format(name=comp_name, phone=phone))
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    if state == "awaiting_complaint_menu":
        cat_map = {"1": "doctor", "2": "center", "3": "accommodation", "4": "transport", "5": "general",
                   "۱": "doctor", "۲": "center", "۳": "accommodation", "۴": "transport", "۵": "general"}
        if t in ("6", "۶"):
            user_state[cid] = "active"
            bot.reply_to(message, MSG2[lang]["comp_voice_skip"])
            return
        if t in cat_map:
            if cid not in user_temp:
                user_temp[cid] = {}
            user_temp[cid]["comp_category"] = cat_map[t]
            user_state[cid] = "awaiting_complaint_text"
            bot.reply_to(message, MSG2[lang]["comp_voice_text"])
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
        return

    if state == "awaiting_complaint_text":
        category = user_temp.get(cid, {}).get("comp_category", "general")
        name = user_name
        if t in ("ناشناس", "مجهول", "anonymous", "anon"):
            name = "ناشناس"
        c = create_complaint(cid, category, name, text)
        bot.reply_to(message, MSG2[lang]["comp_voice_saved"].format(id=c['id']))
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(ADMIN_CHAT_ID, MSG2["fa"]["comp_voice_admin"].format(
                    id=c['id'], category=category, name=name, cid=cid, text=text))
            except:
                pass
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    if state == "awaiting_med_menu":
        if t in ("1", "۱"):
            user_state[cid] = "awaiting_med_name"
            bot.reply_to(message, MSG2[lang]["med_ask_name"])
            return
        if t in ("2", "۲"):
            meds = get_user_meds(cid)
            if not meds:
                bot.reply_to(message, MSG2[lang]["med_none"])
            else:
                lines = ["⏰:"]
                for m in meds:
                    lines.append("💊 " + m['name'] + " — " + m['time'])
                bot.reply_to(message, "\n".join(lines))
            user_state[cid] = "active"
            ask_more(message)
            return
        if t in ("3", "۳"):
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            return
        user_state[cid] = "active"

    if state == "awaiting_med_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG2[lang]["med_ask_name"])
            return
        if cid not in user_temp:
            user_temp[cid] = {}
        user_temp[cid]["med_name"] = text.strip()
        user_state[cid] = "awaiting_med_time"
        bot.reply_to(message, MSG2[lang]["med_ask_time"])
        return

    if state == "awaiting_med_time":
        tt = validate_time(text)
        if not tt:
            bot.reply_to(message, MSG2[lang]["med_ask_time"])
            return
        med_name = user_temp.get(cid, {}).get("med_name", "")
        create_med(cid, med_name, tt, lang)
        bot.reply_to(message, MSG2[lang]["med_saved"].format(name=med_name, time=tt))
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    if state == "awaiting_sos_choice":
        if t in ("1", "۱"):
            bot.reply_to(message, MSG2[lang]["sos_115"])
            user_state[cid] = "active"
            return
        if t in ("2", "۲"):
            data = load_json("data/hospitals.json")
            for h in data[:3]:
                n = get_value(h, 'name', lang) or ''
                a = get_value(h, 'address', lang) or ''
                p = get_value(h, 'phone', lang) or h.get('phone', '')
                bot.reply_to(message, "🏥 " + str(n) + "\n📍 " + str(a) + "\n📞 " + str(p))
            user_state[cid] = "active"
            return
        if t in ("3", "۳"):
            bot.reply_to(message, MSG2[lang]["sos_first_aid"])
            user_state[cid] = "active"
            return
        if t in ("4", "۴"):
            comp = get_companion(cid)
            if not comp:
                bot.reply_to(message, MSG2[lang]["sos_no_companion"])
            else:
                bot.reply_to(message, "✅ " + str(comp.get('name', '')) + " — " + str(comp.get('phone', '')))
            user_state[cid] = "active"
            return
        if t in ("5", "۵"):
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
        return

    if state == "awaiting_delete_confirm":
        if t in ("بله حذف کن", "نعم احذف", "yes delete"):
            delete_patient_data(cid)
            bot.reply_to(message, MSG[lang]["delete_done"])
            user_state[cid] = "active"
            return
        if t in NO_WORDS:
            bot.reply_to(message, MSG[lang]["delete_cancel"])
            user_state[cid] = "active"
            return
        bot.reply_to(message, MSG[lang]["delete_ask"])
        return

    if state == "awaiting_more":
        if t in YES_WORDS:
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["go"])
            return
        user_state[cid] = "active"

    if is_emergency(text):
        bot.reply_to(message, EMERGENCY_RESP[lang])
        ask_more(message)
        return

    old_state = user_state.get(cid)
    answered = process_query(message, text, lang)
    new_state = user_state.get(cid)
    if new_state != old_state and answered:
        return
    if not answered:
        bot.reply_to(message, MSG[lang]["retry"])
    if new_state == old_state or not answered:
        ask_more(message)


print("ربات روشن شد... v45 (بیمه + مترجم + منشور + DeepSeek + پایانه‌ها + تاکسی + یادآور + کانال)")
if jdatetime is None:
    print("⚠️ WARNING: jdatetime نصب نیست — یادآور نوبت کار نمی‌کنه!")
print("⏰ TIMEZONE_OFFSET_HOURS = " + str(TIMEZONE_OFFSET_HOURS))
try:
    reminder_thread = threading.Thread(target=reminder_worker, daemon=True)
    reminder_thread.start()
    print("✅ REMINDER_THREAD started")
except Exception as e:
    print("❌ REMINDER_THREAD fail: " + str(e))
try:
    from news_test import run_news_test
    run_news_test()
except Exception as e:
    print("NEWS_TEST_LOAD_ERR: " + str(e))
bot.infinity_polling(timeout=30, long_polling_timeout=30)