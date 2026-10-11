import json
import os
import re
import random
import telebot
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

# ============ CONFIG ============
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AVALAI_API_KEY = os.environ.get("AVALAI_API_KEY", "")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
AI_MODEL = "gpt-4o-mini"
AVALAI_URL = "https://api.avalai.ir/v1/chat/completions"

# ============ BOT INIT ============
if BALE_BOT_TOKEN:
    telebot.apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"
    telebot.apihelper.FILE_URL = "https://tapi.bale.ai/file/bot{0}/{1}"
    bot = telebot.TeleBot(BALE_BOT_TOKEN)
else:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

LANG_NAMES = {"fa": "فارسی", "ar": "العربية", "en": "English"}

SYSTEM_PROMPT = "شما دستیار گردشگری سلامت شیراز هستید. کوتاه و با همدلی جواب بده. هرگز تشخیص پزشکی نده، دارو تجویز نکن و قیمت دقیق نگو. فقط راهنمای اولیه‌ست، نه تشخیص."

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

# ============ STATE ============
user_state = {}
user_lang = {}
user_temp = {}
satisfaction_counter = {"count": 0, "positive": 0, "negative": 0}

# ============ MSG ============
MSG = {
    "fa": {
        "welcome": "🌟 یه پیام بدی، همه‌چیز رو آماده می‌کنیم.\n\nاز پزشک تا هتل، از ترانسفر تا مترجم، از نوبت تا گشت گردشگری — همه‌چیز یکجا.\n\nبدون دغدغه، بدون هزینه اضافه 💙\n\n👇 از دکمه‌های زیر انتخاب کن:",
        "welcome_text": "یا خواسته‌ت رو بنویس:\nمثلاً «دکتر قلب» یا «پکیج درمان»",
        "more": "سؤال دیگری دارید؟ (بله / نه)",
        "go": "بفرمایید، سؤالتان را بنویسید.",
        "rate": "🙏 از خدمات ما راضی بودید؟ (بله / خیر)",
        "thanks": "🙏 سپاسگزاریم!\n\nاگر از خدمات ما راضی بودید، لطفاً ما را به دوستان و آشنایان خود معرفی کنید. 🌹",
        "why": "متأسفیم. لطفاً بنویسید چه چیزی باعث نارضایتی شد.",
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
        "apt_invalid": "لطفاً یکی از شماره‌های داده شده را بزنید.\n\n🚪 برای خروج از این مرحله، بنویسید: منو",
        "apt_error": "❌ متأسفانه در ثبت نوبت مشکلی پیش آمد.",
        "apt_my": "📋 نوبت‌های شما:",
        "apt_none": "شما هنوز هیچ نوبتی ثبت نکرده‌اید.",
        "apt_confirm_final": "آیا درخواست با این اطلاعات ثبت شود؟ (بله / نه)\n\n👤 نام: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}",
        "apt_admin_new": "📥 درخواست نوبت جدید\n\n📋 کد: {id}\n👤 بیمار: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}\n📞 تلفن مطب: {dphone}\n\n⏳ در انتظار تأیید شما.\n/confirm {id} 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 نوبت شما تأیید شد!\n\n📋 کد: {id}\n👨‍⚕️ پزشک: {doctor}\n📅 تاریخ: {date}\n⏰ ساعت: {time}\n📍 آدرس: {address}",
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
        "pt_not_found": "شما هنوز پرونده‌ای ندارید. با اولین نوبت، پرونده‌ی شما ساخته می‌شه 💙",
        "delete_ask": "⚠️ مطمئنی؟ برای تأیید بنویس: بله حذف کن",
        "delete_done": "✅ همه‌ی اطلاعات شما پاک شد.",
        "delete_cancel": "باشه، اطلاعاتت دست‌نخورده موند.",
    },
    "ar": {
        "welcome": "🌟 رسالة واحدة، ونجهز لكم كل شيء.\n\nمن الطبيب إلى الفندق، من المواصلات إلى المترجم — كل شيء في مكان واحد.\n\nبدون قلق، بدون تكاليف إضافية 💙\n\n👇 اختاروا من الأزرار:",
        "welcome_text": "أو اكتبوا طلبكم:\nمثلاً «طبيب قلب» أو «باكج علاج»",
        "more": "هل لديكم سؤال آخر؟ (نعم / لا)",
        "go": "تفضلوا، اكتبوا سؤالكم.",
        "rate": "🙏 هل أنتم راضون؟ (نعم / لا)",
        "thanks": "🙏 شكراً لكم!\n\nيرجى تعريفنا لأصدقائكم. 🌹",
        "why": "يرجى كتابة سبب عدم رضاكم.",
        "thanks_fb": "شكراً لملاحظاتكم. 🙏",
        "retry": "عذراً، لم أستطع الرد.",
        "text_only": "يرجى كتابة سؤالكم نصاً.",
        "apt_ask": "📅 لحجز موعد، اضغط ١.\n📞 للاتصال، اضغط ٢.",
        "apt_pick_title": "👨‍⚕️ الأطباء:",
        "apt_pick_footer": "\n📅 اكتب رقم الطبيب:",
        "apt_name": "👤 الاسم الكامل:",
        "apt_phone": "📞 رقم الهاتف:",
        "apt_submitted": "✅ تم تسجيل الطلب!\n\n📋 الرقم: {id}\n👨‍⚕️ الطبيب: {doctor}\n\n⏳ سنتصل بالعيادة.",
        "apt_cancelled": "❌ تم الإلغاء.",
        "apt_invalid": "يرجى الضغط على أحد الأرقام.\n\n🚪 للخروج: قائمة",
        "apt_error": "❌ حدثت مشكلة.",
        "apt_my": "📋 مواعيدكم:",
        "apt_none": "لم تسجلوا أي موعد بعد.",
        "apt_confirm_final": "تأكيد؟ (نعم / لا)\n\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}",
        "apt_admin_new": "📥 طلب موعد جديد\n\n📋 {id}\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}\n📞 هاتف العيادة: {dphone}\n\n/confirm {id} 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 تم تأكيد موعدكم!\n\n📋 {id}\n👨‍⚕️ {doctor}\n📅 {date}\n⏰ {time}\n📍 {address}",
        "pt_created": "🎫 تم إنشاء ملفكم\n\n📋 رقم الملف: {code}\n\nلمعرفة الحالة اكتبوا: ملف",
        "pt_title": "🎫 ملفكم الصحي\n━━━━━━━━━━━━━━━",
        "pt_code": "📋 رقم الملف: {code}",
        "pt_name": "👤 الاسم: {name}",
        "pt_progress": "\n🌟 رحلتكم نحو الشفاء:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "تم تسجيل طلبكم",
        "pt_stages_doctor": "تم تحديد الطبيب",
        "pt_stages_date": "تم تحديد موعدكم النهائي",
        "pt_stages_accommodation": "تم تنسيق الإقامة",
        "pt_stages_transport": "تم تنسيق المواصلات",
        "pt_stages_treatment": "تم العلاج",
        "pt_stages_followup": "متابعة الصحة",
        "pt_appointments": "\n📅 مواعيدكم:",
        "pt_apt_line_pending": "⏳ {id} — {doctor} — في انتظار التاريخ",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} الساعة {time}",
        "pt_not_found": "ليس لديكم ملف بعد 💙",
        "delete_ask": "⚠️ للتأكيد اكتبوا: نعم احذف",
        "delete_done": "✅ تم حذف كل معلوماتكم.",
        "delete_cancel": "حسناً.",
    },
    "en": {
        "welcome": "🌟 One message, and we prepare everything.\n\nFrom doctor to hotel, from transfer to translator — all in one place.\n\nNo worries, no hidden fees 💙\n\n👇 Choose from the buttons:",
        "welcome_text": "Or write your request:\nE.g. \"heart doctor\" or \"treatment package\"",
        "more": "Any other question? (Yes / No)",
        "go": "Please go ahead.",
        "rate": "🙏 Were you satisfied? (Yes / No)",
        "thanks": "🙏 Thank you!\n\nPlease recommend us. 🌹",
        "why": "Please tell us what went wrong.",
        "thanks_fb": "Thank you for your feedback. 🙏",
        "retry": "Sorry, I couldn't answer.",
        "text_only": "Please write your question as text.",
        "apt_ask": "📅 To book, press 1.\n📞 Direct call, press 2.",
        "apt_pick_title": "👨‍⚕️ Doctors:",
        "apt_pick_footer": "\n📅 Write the doctor number:",
        "apt_name": "👤 Full name:",
        "apt_phone": "📞 Phone number:",
        "apt_submitted": "✅ Request submitted!\n\n📋 Code: {id}\n👨‍⚕️ Doctor: {doctor}\n\n⏳ We'll contact the clinic.",
        "apt_cancelled": "❌ Cancelled.",
        "apt_invalid": "Please press one of the numbers.\n\n🚪 To exit: menu",
        "apt_error": "❌ There was a problem.",
        "apt_my": "📋 Your appointments:",
        "apt_none": "No appointments yet.",
        "apt_confirm_final": "Confirm? (Yes / No)\n\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}",
        "apt_admin_new": "📥 New appointment\n\n📋 {id}\n👤 {name}\n📞 {phone}\n👨‍⚕️ {doctor}\n📞 Clinic: {dphone}\n\n/confirm {id} 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 Confirmed!\n\n📋 {id}\n👨‍⚕️ {doctor}\n📅 {date}\n⏰ {time}\n📍 {address}",
        "pt_created": "🎫 Your file is ready\n\n📋 Code: {code}\n\nTo view, write: file",
        "pt_title": "🎫 Your Health File\n━━━━━━━━━━━━━━━",
        "pt_code": "📋 Code: {code}",
        "pt_name": "👤 Name: {name}",
        "pt_progress": "\n🌟 Your journey:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "Request received",
        "pt_stages_doctor": "Doctor assigned",
        "pt_stages_date": "Date confirmed",
        "pt_stages_accommodation": "Accommodation arranged",
        "pt_stages_transport": "Transport arranged",
        "pt_stages_treatment": "Treatment completed",
        "pt_stages_followup": "Follow-up",
        "pt_appointments": "\n📅 Appointments:",
        "pt_apt_line_pending": "⏳ {id} — {doctor} — awaiting date",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} at {time}",
        "pt_not_found": "No file yet 💙",
        "delete_ask": "⚠️ To confirm, write: yes delete",
        "delete_done": "✅ All data deleted.",
        "delete_cancel": "Okay.",
    },
}
# ============ MSG2 ============
MSG2 = {
    "fa": {
        "ref_your_code": "🔗 کد معرف شما: {code}\n\nلینک اختصاصی:\n{link}",
        "ref_your_stats": "👥 دعوت‌شده‌ها: {count}\n🎁 پاداش‌ها: {rewards}",
        "ref_new_from": "🎉 یکی از دوستان شما با کد {code} پیوست!\n\nپاداش: ۱۰٪ تخفیف ویزیت بعدی 🌹",
        "ref_welcome_new": "🎉 خوش آمدید!\n\nبا کد {code} وارد شدید.\n🎁 ۵٪ تخفیف اولین ویزیت",
        "ref_invite_msg": "🌟 دوستت رو دعوت کن\n\nکد: {code}\n\nلینک:\n{link}\n\n🎁 تو: ۱۰٪ تخفیف\n🎁 دوستت: ۵٪ تخفیف",
        "hope_night": "🌙 شب بخیر\n\nامیدواریم امروزتون آروم گذشته باشه.\n\n💊 یادتون نره داروهاتون رو مصرف کنید.\n🌷 ما کنارتونیم.",
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
        "comp_skip": "باشه، هر وقت خواستید بنویسید: همراه",
        "sos_menu": "🚨 وضعیت اضطراری\n\nلطفاً یکی از شماره‌ها رو بزنید:\n\n1️⃣ اورژانس ۱۱۵\n2️⃣ نزدیک‌ترین بیمارستان\n3️⃣ راهنمای کمک‌های اولیه\n4️⃣ اطلاع به همراه من\n5️⃣ انصراف",
        "sos_115": "🚑 اورژانس: ۱۱۵\n\nلطفاً تماس بگیرید و آدرس دقیقتون رو بگید.",
        "sos_first_aid": "🩺 کمک‌های اولیه\n\n🔹 درد قفسه سینه:\n- بشین و استراحت\n- قرص زیر زبانی اگه داری\n- فوراً ۱۱۵\n\n🔹 خونریزی:\n- فشار مستقیم\n- ۱۱۵\n\n🔹 تنگی نفس:\n- بشین صاف\n- لباس رو شل کن\n- ۱۱۵\n\n⚠️ این راهنما جایگزین پزشک نیست.",
        "sos_no_companion": "❌ شما همراه ثبت نکردید. بنویسید: همراه",
        "comp_voice_menu": "📩 صدای شما\n\nلطفاً انتخاب کنید:\n\n1️⃣ انتقاد از پزشک\n2️⃣ انتقاد از مرکز درمانی\n3️⃣ انتقاد از اقامت\n4️⃣ انتقاد از حمل‌ونقل\n5️⃣ شکایت کلی\n6️⃣ انصراف",
        "comp_voice_text": "📝 لطفاً نظرتون رو بنویسید:\n\nمی‌تونید اسم بگید یا «ناشناس» بنویسید.",
        "comp_voice_saved": "✅ پیام شما ثبت شد\n\n📋 کد: {id}\n\nما پیگیری می‌کنیم 💙",
        "comp_voice_skip": "باشه، هر وقت خواستید بنویسید: شکایت",
        "comp_voice_admin": "📩 شکایت جدید\n\n📋 {id}\nدسته: {category}\nنام: {name}\nChatID: {cid}\n\n{text}",
        "rights_title": "⚖️ حقوق شما به عنوان بیمار\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ دریافت اطلاعات کامل\n2️⃣ حق انتخاب پزشک\n3️⃣ محرمانه بودن اطلاعات\n4️⃣ رضایت آگاهانه\n5️⃣ دریافت نسخه\n6️⃣ حق شکایت\n7️⃣ احترام بدون تبعیض\n8️⃣ دسترسی به پرونده\n\n📞 در صورت نقض:\n- @ShirazMedBot\n- نظام پزشکی\n- وزارت بهداشت: 190",
        "med_menu": "⏰ یادآور دارو\n\n1️⃣ افزودن یادآور جدید\n2️⃣ مشاهده‌ی یادآورها\n3️⃣ انصراف",
        "med_ask_name": "💊 اسم دارو:",
        "med_ask_time": "⏰ ساعت یادآوری؟ (مثال: 08:00)",
        "med_saved": "✅ یادآور ثبت شد\n\n💊 {name}\n⏰ {time}",
        "med_none": "هنوز یادآوری ثبت نکردی. بنویس: دارو",
        "food_title": "🍏 راهنمای تغذیه و تداخلات\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 تداخل‌های مهم:\n\n• آنتی‌بیوتیک + لبنیات (۲ ساعت)\n• آهن + چای/قهوه (۱ ساعت)\n• وارفارین + کلم و اسفناج\n• تیروئید + صبح ناشتا\n• مسکن + معده خالی (ممنوع)\n\n💧 آب زیاد\n🥗 میوه و سبزیجات\n🚫 خوددرمانی نکن\n\n⚠️ راهنمای کلیه، نه جایگزین پزشک.",
        "menu_main": "📋 منوی شیراز مدیکال\n\n👇 یکی رو انتخاب کن:",
        "ai_unavailable": "🙏 الان نمی‌تونم پاسخ بدم.\n\nبنویسید: منو",
        "para_menu": "🏥 خدمات پیراپزشکی\n\n👇 انتخاب کن:",
        "elderly_menu": "🏡 خانه‌های سالمندان شیراز\n\n👇 انتخاب کن:",
        "elderly_all_title": "🏡 خانه‌های سالمندان شیراز:",
        "package_title": "💎 پکیج کامل درمان و اقامت\n━━━━━━━━━━━━━━━",
        "package_pitch": "🎯 یه پیام بده، ما همه‌چیز رو آماده می‌کنیم.\n\nبدون دغدغه، بدون هزینه اضافه.\nاز لحظه‌ای که وارد شیراز می‌شی تا لحظه‌ای که با سلامتی برمی‌گردی، ما کنارتیم.",
        "package_value": "📦 چی توی این پکیج هست:\n\n👨‍⚕️ ویزیت پزشک متخصص\n🏨 اقامت در هتل\n🚗 ترانسفر فرودگاه و شهر\n🗣️ مترجم همراه\n🏛️ گشت گردشگری شیراز\n📋 پرونده‌ی سلامت شخصی\n💊 یادآور دارو و پیگیری\n🤝 همراه اختصاصی\n💙 پشتیبانی ۲۴ ساعته",
        "package_cta": "🎁 همه‌ی این‌ها با یک پیام.\n\n👇 برای دریافت قیمت، یکی رو انتخاب کن:",
        "package_ask_name": "👤 لطفاً نام و نام خانوادگی‌ات رو بنویس:",
        "package_ask_phone": "📞 شماره تماس:",
        "package_saved": "✅ درخواست پکیج ثبت شد\n\n📋 کد: {id}\n\nتیم ما در کمتر از ۲۴ ساعت تماس می‌گیره.\n\n💙 با آرزوی سلامتی",
        "package_admin_new": "💎 درخواست پکیج جدید\n\n📋 {id}\n👤 {name}\n📞 {phone}\nChatID: {cid}",
        "docs_list_title": "👨‍⚕️ کدام تخصص؟\n\n👇 انتخاب کن:",
        "nonmed_list_title": "🏥 کدام خدمت؟\n\n👇 انتخاب کن:",
        "tourist_list_title": "🏛️ کدام بخش گردشگری؟\n\n👇 انتخاب کن:",
        "para_list_title": "🏥 کدام خدمت پیراپزشکی؟\n\n👇 انتخاب کن:",
        "elderly_list_title": "🏡 خانه سالمندان:",
        "pkg_ask_title": "💎 پکیج کامل",
        "sos_alert_comp": "⚠️ پیام اضطراری\n\nبیمار {name} (کد: {code}) اضطراری داره.\n📞 {phone}",
    },
    "ar": {
        "ref_your_code": "🔗 رمز الإحالة: {code}\n\n{link}",
        "ref_your_stats": "👥 المدعوون: {count}\n🎁 المكافآت: {rewards}",
        "ref_new_from": "🎉 انضم أحد أصدقائكم بكود {code}!\n\nمكافأة: خصم ١٠٪ 🌹",
        "ref_welcome_new": "🎉 أهلاً!\n\nبكود {code}.\n🎁 خصم ٥٪",
        "ref_invite_msg": "🌟 ادعوا أصدقاءكم\n\n{code}\n\n{link}\n\n🎁 أنتم: ١٠٪\n🎁 صديقكم: ٥٪",
        "hope_night": "🌙 مساء الخير\n\n💊 لا تنسوا أدويتكم.\n🌷 نحن معكم.",
        "hope_stage_request": "🌟 خطوتم الخطوة الأولى!",
        "hope_stage_doctor": "👨‍⚕️ تم تحديد الطبيب 🌷",
        "hope_stage_date": "🎉 تم تحديد الموعد! 💙",
        "hope_stage_accommodation": "🏨 تم تنسيق الإقامة 🌷",
        "hope_stage_transport": "🚗 المواصلات جاهزة 💙",
        "hope_stage_treatment": "🌸 تم العلاج",
        "hope_stage_followup": "🌷 ما زلنا معكم 💙",
        "hope_general_1": "💙 «الصحة أعظم ثروة.»",
        "hope_general_2": "🌷 «كل يوم فرصة.»",
        "hope_general_3": "✨ «الأمل نصف الشفاء.»",
        "hope_general_4": "🌸 «لستم وحدكم.»",
        "comp_ask": "👥 هل لديكم مرافق؟ (نعم / لا)",
        "comp_ask_name": "👤 اسم المرافق؟",
        "comp_ask_phone": "📞 رقم المرافق:",
        "comp_saved": "✅ تم التسجيل\n\n👤 {name}\n📞 {phone}",
        "comp_skip": "متى أردتم اكتبوا: مرافق",
        "sos_menu": "🚨 طارئة\n\n1️⃣ الإسعاف ١١٥\n2️⃣ أقرب مستشفى\n3️⃣ الإسعافات\n4️⃣ إبلاغ المرافق\n5️⃣ إلغاء",
        "sos_115": "🚑 ١١٥",
        "sos_first_aid": "🩺 الإسعافات الأولية\n\n⚠️ ليست بديلاً عن الطبيب.",
        "sos_no_companion": "❌ اكتبوا: مرافق",
        "comp_voice_menu": "📩 صوتكم\n\n1️⃣ الطبيب\n2️⃣ المركز\n3️⃣ الإقامة\n4️⃣ المواصلات\n5️⃣ شكوى\n6️⃣ إلغاء",
        "comp_voice_text": "📝 اكتبوا رأيكم:",
        "comp_voice_saved": "✅ تم التسجيل\n\n📋 {id}",
        "comp_voice_skip": "اكتبوا: شكوى",
        "comp_voice_admin": "📩 شكوى\n\n{id}\n{category}\n{name}\n{cid}\n\n{text}",
        "rights_title": "⚖️ حقوقكم\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ معلومات كاملة\n2️⃣ اختيار الطبيب\n3️⃣ سرية\n4️⃣ موافقة\n5️⃣ وصفة\n6️⃣ شكوى\n7️⃣ احترام\n8️⃣ ملف\n\n📞 @ShirazMedBot\n190",
        "med_menu": "⏰ تذكير الدواء\n\n1️⃣ إضافة\n2️⃣ عرض\n3️⃣ إلغاء",
        "med_ask_name": "💊 اسم الدواء:",
        "med_ask_time": "⏰ الساعة؟",
        "med_saved": "✅ {name} — {time}",
        "med_none": "اكتبوا: دواء",
        "food_title": "🍏 التغذية\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 تداخلات:\n\n• مضاد حيوي + ألبان\n• حديد + شاي\n• وارفارين + ملفوف\n• درقية + صباحاً\n• مسكن + معدة فارغة\n\n⚠️ ليس بديلاً عن الطبيب.",
        "menu_main": "📋 القائمة\n\n👇 اختاروا:",
        "ai_unavailable": "🙏 اكتبوا: قائمة",
        "para_menu": "🏥 خدمات مساعدة\n\n👇 اختاروا:",
        "elderly_menu": "🏡 دور المسنين\n\n👇 اختاروا:",
        "elderly_all_title": "🏡 دور المسنين في شيراز:",
        "package_title": "💎 باكج شامل العلاج والإقامة\n━━━━━━━━━━━━━━━",
        "package_pitch": "🎯 رسالة واحدة، نجهز كل شيء.\n\nبدون قلق، بدون تكاليف إضافية.",
        "package_value": "📦 المحتوى:\n\n👨‍⚕️ طبيب متخصص\n🏨 فندق\n🚗 مواصلات\n🗣️ مترجم\n🏛️ جولة\n📋 ملف\n💊 متابعة\n🤝 مرافق\n💙 دعم ٢٤ ساعة",
        "package_cta": "🎁 كل هذا برسالة.\n\n👇 اختاروا:",
        "package_ask_name": "👤 الاسم الكامل:",
        "package_ask_phone": "📞 الهاتف:",
        "package_saved": "✅ تم التسجيل\n\n📋 {id}\n\nسنتصل قريباً.",
        "package_admin_new": "💎 طلب باكج\n\n{id}\n{name}\n{phone}\n{cid}",
        "docs_list_title": "👨‍⚕️ أي تخصص؟\n\n👇",
        "nonmed_list_title": "🏥 أي خدمة؟\n\n👇",
        "tourist_list_title": "🏛️ السياحة:\n\n👇",
        "para_list_title": "🏥 خدمات مساعدة:\n\n👇",
        "elderly_list_title": "🏡 دور المسنين:",
        "pkg_ask_title": "💎 الباكج",
        "sos_alert_comp": "⚠️ طارئ\n\n{name} (كود {code})\n📞 {phone}",
    },
    "en": {
        "ref_your_code": "🔗 Your code: {code}\n\n{link}",
        "ref_your_stats": "👥 Invited: {count}\n🎁 Rewards: {rewards}",
        "ref_new_from": "🎉 A friend joined with code {code}!\n\nReward: 10% off 🌹",
        "ref_welcome_new": "🎉 Welcome!\n\nCode {code}.\n🎁 5% off",
        "ref_invite_msg": "🌟 Invite friends\n\n{code}\n\n{link}\n\n🎁 You: 10%\n🎁 Friend: 5%",
        "hope_night": "🌙 Good night\n\n💊 Take your meds.\n🌷 We're here.",
        "hope_stage_request": "🌟 First step done!",
        "hope_stage_doctor": "👨‍⚕️ Doctor assigned 🌷",
        "hope_stage_date": "🎉 Date confirmed! 💙",
        "hope_stage_accommodation": "🏨 Accommodation ready 🌷",
        "hope_stage_transport": "🚗 Transport ready 💙",
        "hope_stage_treatment": "🌸 Treatment completed",
        "hope_stage_followup": "🌷 Still here for you 💙",
        "hope_general_1": "💙 \"Health is the greatest wealth.\"",
        "hope_general_2": "🌷 \"Every day is a chance.\"",
        "hope_general_3": "✨ \"Hope is half the cure.\"",
        "hope_general_4": "🌸 \"You are not alone.\"",
        "comp_ask": "👥 Do you have a companion? (Yes / No)",
        "comp_ask_name": "👤 Companion's name?",
        "comp_ask_phone": "📞 Companion's phone:",
        "comp_saved": "✅ Saved\n\n👤 {name}\n📞 {phone}",
        "comp_skip": "Write: companion",
        "sos_menu": "🚨 Emergency\n\n1️⃣ 115\n2️⃣ Nearest hospital\n3️⃣ First aid\n4️⃣ Alert companion\n5️⃣ Cancel",
        "sos_115": "🚑 115",
        "sos_first_aid": "🩺 First Aid\n\n⚠️ Not a substitute for a doctor.",
        "sos_no_companion": "❌ Write: companion",
        "comp_voice_menu": "📩 Your Voice\n\n1️⃣ Doctor\n2️⃣ Center\n3️⃣ Accommodation\n4️⃣ Transport\n5️⃣ General\n6️⃣ Cancel",
        "comp_voice_text": "📝 Write your feedback:",
        "comp_voice_saved": "✅ Recorded\n\n📋 {id}",
        "comp_voice_skip": "Write: complaint",
        "comp_voice_admin": "📩 Complaint\n\n{id}\n{category}\n{name}\n{cid}\n\n{text}",
        "rights_title": "⚖️ Patient Rights\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ Full info\n2️⃣ Choose doctor\n3️⃣ Confidentiality\n4️⃣ Consent\n5️⃣ Prescriptions\n6️⃣ Complain\n7️⃣ Respect\n8️⃣ File access\n\n📞 @ShirazMedBot\n190",
        "med_menu": "⏰ Med Reminder\n\n1️⃣ Add\n2️⃣ View\n3️⃣ Cancel",
        "med_ask_name": "💊 Medication name:",
        "med_ask_time": "⏰ Time? (e.g. 08:00)",
        "med_saved": "✅ {name} — {time}",
        "med_none": "Write: med",
        "food_title": "🍏 Nutrition\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 Interactions:\n\n• Antibiotics + dairy\n• Iron + tea\n• Warfarin + cabbage\n• Thyroid + morning\n• Painkillers + empty\n\n⚠️ Not a substitute for a doctor.",
        "menu_main": "📋 Menu\n\n👇 Choose:",
        "ai_unavailable": "🙏 Write: menu",
        "para_menu": "🏥 Paramedical\n\n👇 Choose:",
        "elderly_menu": "🏡 Nursing Homes\n\n👇 Choose:",
        "elderly_all_title": "🏡 Nursing Homes in Shiraz:",
        "package_title": "💎 Complete Treatment & Stay\n━━━━━━━━━━━━━━━",
        "package_pitch": "🎯 One message, we prepare everything.\n\nNo worries, no hidden fees.",
        "package_value": "📦 Includes:\n\n👨‍⚕️ Specialist\n🏨 Hotel\n🚗 Transfer\n🗣️ Translator\n🏛️ Tour\n📋 File\n💊 Follow-up\n🤝 Companion\n💙 24/7 support",
        "package_cta": "🎁 All with one message.\n\n👇 Choose:",
        "package_ask_name": "👤 Full name:",
        "package_ask_phone": "📞 Phone:",
        "package_saved": "✅ Submitted\n\n📋 {id}\n\nWe'll call soon.",
        "package_admin_new": "💎 Package Request\n\n{id}\n{name}\n{phone}\n{cid}",
        "docs_list_title": "👨‍⚕️ Which specialty?\n\n👇",
        "nonmed_list_title": "🏥 Which service?\n\n👇",
        "tourist_list_title": "🏛️ Tourism:\n\n👇",
        "para_list_title": "🏥 Paramedical:\n\n👇",
        "elderly_list_title": "🏡 Nursing Homes:",
        "pkg_ask_title": "💎 Package",
        "sos_alert_comp": "⚠️ Emergency\n\n{name} (code {code})\n📞 {phone}",
    },
}
# ============ WORD LISTS ============
YES_WORDS = {"بله", "بلی", "آره", "اره", "yes", "yeah", "y", "نعم", "ايوه", "أيوه", "ها", "آری", "اری"}
NO_WORDS = {"نه", "نخیر", "خیر", "نه ممنون", "ندارم", "no", "nope", "n", "لا", "لا شكرا", "ليس"}

# ============ SPECIALTY MAP ============
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

# ============ NON MEDICAL MAP ============
NON_MEDICAL_MAP = {
    "hospitals.json": ["بیمارستان", "hospital", "مستشفى", "کلینیک", "clinic"],
    "hotels.json": ["هتل", "hotel", "فندق", "فنادق", "اقامتگاه"],
    "motels.json": ["مهمان‌پذیر", "مسافرخانه", "motel", "نُزل", "نزل"],
    "tourist_houses.json": ["خانه مسافر", "اقامتگاه بومگردی", "tourist house", "guest house", "بيت مسافر"],
    "leisure_city.json": ["جاذبه", "حافظیه", "سعدیه", "ارگ", "نصیرالملک", "شاهچراغ", "باغ ارم", "بازار وکیل", "موزه", "مسجد"],
    "leisure_outside.json": ["تخت جمشید", "پاسارگاد", "نقش رستم", "آبشار", "persepolis", "pasargad"],
    "transport.json": ["حمل‌ونقل", "مترو", "تاکسی", "اتوبوس", "اسنپ", "تپسی", "فرودگاه", "transport", "metro", "taxi", "مواصلات", "مطار"],
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

# ============ FIELD_NAMES ============
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
        "pharmacy_code": "کد داروخانه", "services_offered": "خدمات ارائه‌شده",
        "is_24h": "شبانه‌روزی", "ipd_code": "کد IPD",
        "ownership": "مالکیت", "specialties": "تخصص‌ها",
        "has_home_service": "خدمات در منزل", "capacity": "ظرفیت",
    },
    "ar": {
        "name": "الاسم", "address": "العنوان", "phone": "الهاتف", "specialty": "التخصص",
        "office_address": "عنوان العيادة", "working_hours": "ساعات العمل",
        "price_range_toman": "السعر", "price_range": "السعر",
        "patient_satisfaction_score": "التقييم", "rating": "التقييم",
        "reviews_summary": "آراء الزوار", "surgeries_done_at": "المستشفيات",
        "category": "الفئة", "star_rating": "التصنيف", "quality_grade": "الجودة",
        "district": "المنطقة", "amenities": "المرافق", "distance_to_hospitals": "المسافة",
        "has_translator": "مترجم", "languages_spoken": "اللغات",
        "description": "الوصف", "services": "الخدمات", "type": "النوع",
        "pharmacy_code": "رمز الصيدلية", "services_offered": "الخدمات",
        "is_24h": "على مدار الساعة", "ipd_code": "IPD",
        "ownership": "الملكية", "specialties": "التخصصات",
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
        "pharmacy_code": "Pharmacy Code", "services_offered": "Services",
        "is_24h": "24 Hours", "ipd_code": "IPD",
        "ownership": "Ownership", "specialties": "Specialties",
        "has_home_service": "Home Service", "capacity": "Capacity",
    },
}

PRICE_MAP = {
    "Low": {"fa": "اقتصادی", "ar": "اقتصادي", "en": "Low"},
    "Medium": {"fa": "متوسط", "ar": "متوسط", "en": "Medium"},
    "High": {"fa": "گران", "ar": "غالي", "en": "High"},
}

CONTEXT_WORDS = ["بیمارستان", "hospital", "مستشفى", "شیراز", "shiraz", "شيراز", "doctor", "دکتر", "طبيب", "dr"]

# ============ EMERGENCY ============
EMERGENCY = {
    "fa": ["درد شدید", "تب", "خونریزی", "استفراغ", "ضعف", "غش", "سکته", "تشنج", "خفگی", "حالم خوب نیست", "حالم بده"],
    "ar": ["ألم شديد", "حمى", "نزيف", "قيء", "ضعف", "إغماء", "جلطة", "تشنج", "اختناق"],
    "en": ["severe pain", "fever", "bleeding", "vomiting", "weakness", "fainting", "stroke", "seizure", "choking"]
}

EMERGENCY_RESP = {
    "fa": "🚨 فوراً به اورژانس مراجعه کن. تلفن: ۱۱۵",
    "ar": "🚨 توجه فوراً إلى الطوارئ. هاتف: ١١٥",
    "en": "🚨 Go to emergency. Phone: 115"
}

# ============ SIMPLE COMMANDS ============
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

# ============ BASIC HELPERS ============
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
    if (key + "_en") in item:
        return item[key + "_en"]
    if (key + "_ar") in item:
        return item[key + "_ar"]
    return None

def get_price(item, lang):
    p = item.get('price_range', '')
    if not p:
        p = item.get('price_range_toman', '')
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
        if jy < 1400 or jy > 1500:
            return None
        if jm < 1 or jm > 12:
            return None
        if jd < 1 or jd > 31:
            return None
        return str(jy) + "/" + str(jm).zfill(2) + "/" + str(jd).zfill(2)
    except:
        return None

# ============ DATE HELPERS ============
def gregorian_to_shamsi(g_y, g_m, g_d):
    gdm = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    jdm = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy = g_y - 1600
    gm = g_m - 1
    gd = g_d - 1
    gdn = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm):
        gdn += gdm[i]
    if gm > 1 and ((g_y % 4 == 0 and g_y % 100 != 0) or (g_y % 400 == 0)):
        gdn += 1
    gdn += gd
    jdn = gdn - 79
    jnp = jdn // 12053
    jdn %= 12053
    jy = 979 + 33 * jnp + 4 * (jdn // 1461)
    jdn %= 1461
    if jdn >= 366:
        jy += (jdn - 1) // 365
        jdn = (jdn - 1) % 365
    i = 0
    for i in range(11):
        if jdn < jdm[i]:
            break
        jdn -= jdm[i]
    return jy, i + 1, jdn + 1

def format_date_full(offset_days=0, lang="fa"):
    today = datetime.now() + timedelta(days=offset_days)
    miladi = today.strftime("%Y/%m/%d")
    try:
        jy, jm, jd = gregorian_to_shamsi(today.year, today.month, today.day)
        shamsi = str(jy) + "/" + str(jm).zfill(2) + "/" + str(jd).zfill(2)
    except:
        shamsi = "---"
    if lang == "en":
        return miladi + " (Shamsi: " + shamsi + ")"
    if lang == "ar":
        return miladi + " - " + shamsi
    return shamsi + " - " + miladi

# ============ INLINE KEYBOARD BUILDERS ============
def kb(lang):
    return MSG_BTN[lang]

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
        telebot.types.InlineKeyboardButton(text=b["btn_file"], callback_data="do_file"),
        telebot.types.InlineKeyboardButton(text=b["btn_apt"], callback_data="do_apt"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_med"], callback_data="do_med"),
        telebot.types.InlineKeyboardButton(text=b["btn_sos"], callback_data="do_sos"),
    )
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_invite"], callback_data="do_invite"),
        telebot.types.InlineKeyboardButton(text=b["btn_help"], callback_data="do_help"),
    )
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
        if lang == "fa":
            label = fa
        elif lang == "ar":
            label = ar
        else:
            label = en
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
        (b["btn_trad_med"], "حطب سنتی"),
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
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_pkg_call"], callback_data="pkg_call"))
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def doctor_action_kb(lang, doc_id):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        telebot.types.InlineKeyboardButton(text=b["btn_book"], callback_data="book_" + doc_id),
        telebot.types.InlineKeyboardButton(text=b["btn_call"], callback_data="call_" + doc_id),
    )
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m

def back_kb(lang, cb="back_main"):
    m = telebot.types.InlineKeyboardMarkup()
    b = MSG_BTN[lang]
    m.add(telebot.types.InlineKeyboardButton(text=b["btn_back"], callback_data=cb))
    return m

# ============ MSG_BTN ============
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
        "btn_pkg_call": "📞 تماس با ما",
        "btn_book": "📅 نوبت بگیر",
        "btn_call": "📞 تماس",
    },
    "ar": {
        "btn_docs": "👨‍⚕️ طبي",
        "btn_nonmed": "🏥 غير طبي",
        "btn_tourist": "🏛️ سياحة",
        "btn_para": "🏥 مساعد طبي",
        "btn_elder": "🏡 دار المسنين",
        "btn_pkg": "💎 الباكج",
        "btn_file": "📋 الملف",
        "btn_apt": "📅 مواعيدي",
        "btn_med": "💊 تذكير",
        "btn_sos": "🚨 طوارئ",
        "btn_invite": "🎁 دعوة",
        "btn_help": "🆘 الحقوق",
        "btn_back": "🔙 رجوع",
        "btn_hospitals": "🏥 المستشفيات",
        "btn_hotels": "🏨 الفنادق",
        "btn_motels": "🛏️ النزل",
        "btn_houses": "🏠 بيوت المسافر",
        "btn_transport": "🚗 المواصلات",
        "btn_city": "🏛️ معالم المدينة",
        "btn_outside": "🏞️ خارج المدينة",
        "btn_physio": "🦴 علاج طبيعي",
        "btn_lab": "🔬 مختبر",
        "btn_radiology": "📷 أشعة",
        "btn_nursing": "👩‍⚕️ تمريض",
        "btn_injection": "💉 حقن",
        "btn_trad_med": "🌿 طب تقليدي",
        "btn_occupational": "🧩 علاج وظيفي",
        "btn_speech": "🗣️ علاج النطق",
        "btn_orthotics": "🦿 أطراف",
        "btn_elder_all": "🏡 كل دور المسنين",
        "btn_pkg_order": "💎 طلب الباكج",
        "btn_pkg_call": "📞 اتصل بنا",
        "btn_book": "📅 احجز",
        "btn_call": "📞 اتصل",
    },
    "en": {
        "btn_docs": "👨‍⚕️ Medical",
        "btn_nonmed": "🏥 Non-medical",
        "btn_tourist": "🏛️ Tourism",
        "btn_para": "🏥 Paramedical",
        "btn_elder": "🏡 Nursing Homes",
        "btn_pkg": "💎 Full Package",
        "btn_file": "📋 File",
        "btn_apt": "📅 Appointments",
        "btn_med": "💊 Med Reminder",
        "btn_sos": "🚨 Emergency",
        "btn_invite": "🎁 Invite Friends",
        "btn_help": "🆘 Patient Rights",
        "btn_back": "🔙 Back",
        "btn_hospitals": "🏥 Hospitals",
        "btn_hotels": "🏨 Hotels",
        "btn_motels": "🛏️ Motels",
        "btn_houses": "🏠 Guest Houses",
        "btn_transport": "🚗 Transport",
        "btn_city": "🏛️ City Attractions",
        "btn_outside": "🏞️ Outside City",
        "btn_physio": "🦴 Physiotherapy",
        "btn_lab": "🔬 Lab",
        "btn_radiology": "📷 Radiology",
        "btn_nursing": "👩‍⚕️ Nursing",
        "btn_injection": "💉 Injection",
        "btn_trad_med": "🌿 Traditional",
        "btn_occupational": "🧩 Occupational",
        "btn_speech": "🗣️ Speech Therapy",
        "btn_orthotics": "🦿 Orthotics",
        "btn_elder_all": "🏡 All Nursing Homes",
        "btn_pkg_order": "💎 Order Package",
        "btn_pkg_call": "📞 Call Us",
        "btn_book": "📅 Book",
        "btn_call": "📞 Call",
    },
}
# ============ DATA FILES ============
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

# ============ APPOINTMENTS ============
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
        "doctor_lat": doctor.get('lat', ''),
        "doctor_lng": doctor.get('lng', ''),
        "patient_name": pname,
        "patient_phone": pphone,
        "patient_chat_id": str(chat_id),
        "patient_lang": lang,
        "date": "",
        "time": "",
        "status": "pending",
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
            save_appointments(data)
            return a
    return None

# ============ PATIENTS ============
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
            "request": True,
            "doctor": False,
            "date": False,
            "accommodation": False,
            "transport": False,
            "treatment": False,
            "followup": False
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
            if apt.get('status') == 'confirmed' and apt.get('date'):
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

# ============ PACKAGES ============
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
        "id": pkg_id,
        "chat_id": str(chat_id),
        "name": name,
        "phone": phone,
        "lang": lang,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['packages'].append(pkg)
    save_packages(data)
    return pkg

# ============ REFERRALS ============
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

# ============ COMPANIONS ============
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

# ============ USERS ============
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
    return {"total": total, "dau": dau, "wau": wau, "mau": mau, "conv": conv}

# ============ COMPLAINTS ============
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

# ============ MEDS ============
def load_meds():
    return _load_default(MEDS_FILE, {"meds": []})

def save_meds(data):
    return _save(MEDS_FILE, data)

def create_med(chat_id, name, time_str):
    data = load_meds()
    item = {
        "chat_id": str(chat_id), "name": name, "time": time_str,
        "active": True, "last_sent_date": "",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['meds'].append(item)
    save_meds(data)
    return item

def get_user_meds(chat_id):
    data = load_meds()
    return [m for m in data['meds'] if m['chat_id'] == str(chat_id) and m.get('active', True)]

# ============ HOPE ============
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

# ============ SEND HELPERS ============
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

# ============ AI ============
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

# ============ SEARCH ============
def search_by_doctor_name(text):
    low = text.lower()
    st = low
    for w in ["دکتر", "doctor", "دكتور", "دكتورة", "طبيب", "طبیب", "dr"]:
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

# ============ FORMATTERS ============
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

# ============ ADMIN SET DOCTOR STATUS ============
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

# ============ STATE HELPERS ============
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

# ============ QUERY PROCESSOR ============
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
            if a.get('status') == 'confirmed' and a.get('date'):
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
# ============ ADMIN COMMANDS ============
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
    lines.append("")
    lines.append("📅 نوبت‌ها:")
    lines.append("• در انتظار: " + str(len(pending)))
    lines.append("• تأیید شده: " + str(len(confirmed)))
    if pending:
        for a in pending[-5:]:
            dn = a.get("doctor_name_fa", "")
            lines.append("• " + a['id'] + " — " + a.get('patient_name', '') + " — " + str(dn))
    lines.append("")
    lines.append("💎 پکیج‌های در انتظار: " + str(len(pending_pkgs)))
    if pending_pkgs:
        for p in pending_pkgs[-3:]:
            lines.append("• " + p['id'] + " — " + p.get('name', '') + " — " + p.get('phone', ''))
    lines.append("")
    lines.append("📩 شکایت جدید: " + str(len(new_complaints)))
    lines.append("")
    lines.append("📈 نظرسنجی:")
    lines.append("• رضایت: " + str(satisfaction_counter['positive']))
    lines.append("• عدم رضایت: " + str(satisfaction_counter['negative']))
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
    doc_id = parts[1]
    if set_doctor_status(doc_id, 'inactive'):
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
    doc_id = parts[1]
    if set_doctor_status(doc_id, 'active'):
        bot.reply_to(message, "✅ فعال شد.")
    else:
        bot.reply_to(message, "❌ پیدا نشد.")

# ============ USER COMMANDS ============
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
        if a.get('status') == 'confirmed' and a.get('date'):
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

@bot.message_handler(commands=['myrewards'])
def myrewards_command(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    st = get_referral_stats(cid)
    rewards_str = ", ".join(st['rewards']) if st['rewards'] else "—"
    bot.reply_to(message, MSG2[lang]["ref_your_stats"].format(count=st['count'], rewards=rewards_str))

# ============ MEDIA TYPES ============
@bot.message_handler(content_types=['photo', 'voice', 'audio', 'document', 'video', 'sticker'])
def other_types(message):
    cid = message.chat.id
    if cid in user_lang:
        bot.reply_to(message, MSG[user_lang[cid]]["text_only"])
    else:
        user_state[cid] = "choose_lang"
        bot.reply_to(message, START_MSG)

# ============ CALLBACK HANDLER (Inline Keyboard) ============
@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    try:
        cid = call.message.chat.id
        lang = user_lang.get(cid, "fa")
        data = call.data
        b = MSG_BTN[lang]

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        # ---- Back to main menu ----
        if data == "back_main":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["menu_main"], reply_markup=main_menu_kb(lang))
            except:
                show_main_menu(call.message, lang)
            return

        # ---- منوی پزشکی ----
        if data == "menu_docs":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["docs_list_title"], reply_markup=specialties_kb(lang))
            except:
                bot.send_message(cid, MSG2[lang]["docs_list_title"], reply_markup=specialties_kb(lang))
            return

        # ---- تخصص ----
        if data.startswith("spec_"):
            fn = data[5:] + ".json"
            docs = load_json("data/doctors/" + fn)
            if not docs:
                bot.send_message(cid, "❌ اطلاعاتی یافت نشد.")
                return
            docs = [d for d in docs if d.get('status', 'active') != 'inactive']
            if not docs:
                bot.send_message(cid, "❌ پزشکی در این تخصص یافت نشد.")
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
                bot.send_message(cid, format_doctor(d, lang), reply_markup=doctor_action_kb(lang, did))
            return

        # ---- منوی غیرپزشکی ----
        if data == "menu_nonmed":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["nonmed_list_title"], reply_markup=nonmed_kb(lang))
            except:
                bot.send_message(cid, MSG2[lang]["nonmed_list_title"], reply_markup=nonmed_kb(lang))
            return

        # ---- زیرمنو غیرپزشکی ----
        if data.startswith("non_"):
            fn = data[4:] + ".json"
            items = load_json("data/" + fn)
            if not items:
                bot.send_message(cid, "❌ اطلاعاتی یافت نشد.")
                return
            for item in items[:5]:
                bot.send_message(cid, format_generic(item, lang), reply_markup=back_kb(lang))
            return

        # ---- گردشگری ----
        if data == "menu_tourist":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["tourist_list_title"], reply_markup=tourist_kb(lang))
            except:
                bot.send_message(cid, MSG2[lang]["tourist_list_title"], reply_markup=tourist_kb(lang))
            return

        # ---- پیراپزشکی ----
        if data == "menu_para":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["para_list_title"], reply_markup=para_kb(lang))
            except:
                bot.send_message(cid, MSG2[lang]["para_list_title"], reply_markup=para_kb(lang))
            return

        if data == "para_search":
            bot.send_message(cid, MSG2[lang]["para_list_title"], reply_markup=para_kb(lang))
            return

        # ---- سالمندان ----
        if data == "menu_elder":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["elderly_list_title"], reply_markup=elderly_kb(lang))
            except:
                bot.send_message(cid, MSG2[lang]["elderly_list_title"], reply_markup=elderly_kb(lang))
            return

        if data == "elder_all":
            data_e = load_json("data/elderly_homes.json")
            if data_e:
                bot.send_message(cid, MSG2[lang]["elderly_all_title"])
                for item in data_e[:10]:
                    bot.send_message(cid, format_generic(item, lang), reply_markup=back_kb(lang))
            return

        # ---- پکیج ----
        if data == "menu_pkg":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["package_title"], reply_markup=package_kb(lang))
            except:
                bot.send_message(cid, MSG2[lang]["package_title"], reply_markup=package_kb(lang))
            return

        if data == "pkg_order":
            bot.send_message(cid, MSG2[lang]["package_pitch"])
            bot.send_message(cid, MSG2[lang]["package_value"])
            bot.send_message(cid, MSG2[lang]["package_cta"])
            user_state[cid] = "awaiting_pkg_name"
            bot.send_message(cid, MSG2[lang]["package_ask_name"])
            return

        if data == "pkg_call":
            bot.send_message(cid, "📞 برای تماس با ما:\n@ShirazMedBot", reply_markup=back_kb(lang))
            return

        # ---- پزشک: نوبت یا تماس ----
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
                bot.send_message(cid, "❌ پزشک پیدا نشد.")
                return
            user_temp[cid] = {"doctor": doc}
            user_state[cid] = "awaiting_apt_name"
            bot.send_message(cid, MSG[lang]["apt_name"])
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
                bot.send_message(cid, "❌ پزشک پیدا نشد.")
                return
            phone = doc.get('phone', '')
            bot.send_message(cid, "📞 تلفن مطب:\n" + str(phone), reply_markup=back_kb(lang))
            return

        # ---- منوی سریع ----
        if data == "do_file":
            p = get_patient_by_chat(cid)
            bot.send_message(cid, format_patient_file(p, lang), reply_markup=back_kb(lang))
            return

        if data == "do_apt":
            apts = get_patient_appointments(cid)
            if not apts:
                bot.send_message(cid, MSG[lang]["apt_none"], reply_markup=back_kb(lang))
                return
            lines = [MSG[lang]["apt_my"]]
            for a in apts[-5:]:
                dn = a.get("doctor_name_" + lang) or a.get("doctor_name_fa", "")
                if a.get('status') == 'confirmed' and a.get('date'):
                    lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                        id=a['id'], doctor=dn, date=a['date'], time=a.get('time', '')))
                else:
                    lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a['id'], doctor=dn))
            bot.send_message(cid, "\n\n".join(lines), reply_markup=back_kb(lang))
            return

        if data == "do_med":
            user_state[cid] = "awaiting_med_menu"
            bot.send_message(cid, MSG2[lang]["med_menu"])
            return

        if data == "do_sos":
            user_state[cid] = "awaiting_sos_choice"
            bot.send_message(cid, MSG2[lang]["sos_menu"])
            return

        if data == "do_invite":
            code = get_or_create_referral_code(cid)
            link = build_referral_link(code)
            bot.send_message(cid, MSG2[lang]["ref_invite_msg"].format(code=code, link=link), reply_markup=back_kb(lang))
            return

        if data == "do_help":
            bot.send_message(cid, MSG2[lang]["rights_title"] + "\n\n" + MSG2[lang]["rights_body"], reply_markup=back_kb(lang))
            return

    except Exception as e:
        print("CB_ERR: " + str(e))

# ============ MAIN HANDLER ============
@bot.message_handler(func=lambda m: True)
def handle(message):
    cid = message.chat.id
    text = message.text or ""
    state = user_state.get(cid)

    # ---- انتخاب زبان ----
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

    # ---- خروج با کلمات escape ----
    ESCAPE_WORDS = {"منو", "لغو", "انصراف", "menu", "cancel"}
    if t in ESCAPE_WORDS:
        user_state[cid] = "active"
        user_temp.pop(cid, None)
        show_main_menu(message, lang)
        return

    # ---- پکیج: نام ----
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

    # ---- پکیج: تلفن ----
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
                    bot.send_message(ADMIN_CHAT_ID,
                        MSG2["fa"]["package_admin_new"].format(
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

    # ---- اسم بیمار ----
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

    # ---- تلفن بیمار ----
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

    # ---- تأیید نهایی ----
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
                        bot.send_message(ADMIN_CHAT_ID,
                            MSG["fa"]["apt_admin_new"].format(
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

    # ---- همراه ----
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

    # ---- شکایت ----
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

    # ---- دارو ----
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
                lines = ["⏰ یادآورهای شما:"]
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
        create_med(cid, med_name, tt)
        bot.reply_to(message, MSG2[lang]["med_saved"].format(name=med_name, time=tt))
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    # ---- SOS ----
    if state == "awaiting_sos_choice":
        if t in ("1", "۱"):
            bot.reply_to(message, MSG2[lang]["sos_115"])
            user_state[cid] = "active"
            return
        if t in ("2", "۲"):
            data = load_json("data/hospitals.json")
            lines = []
            for h in data[:3]:
                n = get_value(h, 'name', lang) or ''
                a = get_value(h, 'address', lang) or ''
                p = get_value(h, 'phone', lang) or h.get('phone', '')
                lines.append("🏥 " + str(n) + "\n📍 " + str(a) + "\n📞 " + str(p))
            if lines:
                bot.reply_to(message, "\n\n".join(lines))
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
                bot.reply_to(message, "✅ همراه: " + str(comp.get('name', '')) + "\n📞 " + str(comp.get('phone', '')))
            user_state[cid] = "active"
            return
        if t in ("5", "۵"):
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
        return

    # ---- حذف داده ----
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

    # ---- سؤال دیگر ----
    if state == "awaiting_more":
        if t in YES_WORDS:
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["go"])
            return
        if t in NO_WORDS:
            user_state[cid] = "awaiting_rating"
            bot.reply_to(message, MSG[lang]["rate"])
            return
        user_state[cid] = "active"

    # ---- نظرسنجی ----
    if state == "awaiting_rating":
        if t in YES_WORDS:
            user_state[cid] = "active"
            satisfaction_counter["count"] += 1
            satisfaction_counter["positive"] += 1
            code = get_or_create_referral_code(cid)
            link = build_referral_link(code)
            bot.reply_to(message, MSG[lang]["thanks"])
            bot.reply_to(message, MSG2[lang]["ref_invite_msg"].format(code=code, link=link))
            return
        if t in NO_WORDS:
            user_state[cid] = "awaiting_feedback"
            bot.reply_to(message, MSG[lang]["why"])
            return
        user_state[cid] = "active"

    if state == "awaiting_feedback":
        user_state[cid] = "active"
        bot.reply_to(message, MSG[lang]["thanks_fb"])
        satisfaction_counter["count"] += 1
        satisfaction_counter["negative"] += 1
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(ADMIN_CHAT_ID,
                    "❌ عدم رضایت\n" + LANG_NAMES.get(lang, lang) +
                    "\nنام: " + user_name + "\nChatID: " + str(cid) + "\n" + text)
            except:
                pass
        return

    # ---- اضطراری ----
    if is_emergency(text):
        bot.reply_to(message, EMERGENCY_RESP[lang])
        ask_more(message)
        return

    # ---- پردازش عادی ----
    old_state = user_state.get(cid)
    answered = process_query(message, text, lang)
    new_state = user_state.get(cid)
    if new_state != old_state and answered:
        return
    if not answered:
        bot.reply_to(message, MSG[lang]["retry"])
    if new_state == old_state or not answered:
        ask_more(message)


# ============ START ============
print("ربات روشن شد... v37 (Inline Keyboard درختی + همه‌چیز کامل)")
bot.infinity_polling(timeout=30, long_polling_timeout=30)