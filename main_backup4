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

SYSTEM_PROMPT = "شما دستیار گردشگری سلامت شیراز هستید. کوتاه و با همدلی جواب بده. هرگز تشخیص پزشکی نده، دارو تجویز نکن و قیمت دقیق نگو. فقط راهنمای اولیه‌ست، نه تشخیص. در پایان سؤال نپرس."

AI_DISCLAIMER = {
    "fa": "\n\n⚠️ این راهنمای اولیه‌ست، نه تشخیص پزشکی. برای معاینه دقیق به پزشک مراجعه کنید.",
    "ar": "\n\n⚠️ هذا توجيه أولي وليس تشخيصاً طبياً. يرجى مراجعة الطبيب.",
    "en": "\n\n⚠️ This is a preliminary guide, not a medical diagnosis. Please consult a doctor."
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
        "welcome": "🌟 به شیراز مدیکال خوش آمدید!\n\nهمراه شما در مسیر درمان و اقامت در شیراز.\n\n🔹 معرفی پزشکان متخصص\n🔹 اقامتگاه و حمل‌ونقل\n🔹 گشت‌وگذار در جاذبه‌های شیراز\n🔹 پشتیبانی در تمام مراحل\n\nخواسته‌ی خود را بنویسید.\nمثلاً: دکتر قلب",
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
        "apt_submitted": "✅ درخواست نوبت شما ثبت شد!\n\n📋 کد پیگیری: {id}\n👨‍⚕️ پزشک: {doctor}\n\n⏳ ما با مطب تماس می‌گیریم و سریع‌ترین نوبت موجود رو براتون هماهنگ می‌کنیم.\nنتیجه از طریق همین ربات اطلاع داده می‌شه.",
        "apt_cancelled": "❌ ثبت نوبت لغو شد.",
        "apt_invalid": "لطفاً یکی از شماره‌های داده شده را بزنید.\n\n🚪 برای خروج از این مرحله، بنویسید: منو",
        "apt_error": "❌ متأسفانه در ثبت نوبت مشکلی پیش آمد.",
        "apt_my": "📋 نوبت‌های شما:",
        "apt_none": "شما هنوز هیچ نوبتی ثبت نکرده‌اید.",
        "apt_confirm_final": "آیا درخواست با این اطلاعات ثبت شود؟ (بله / نه)\n\n👤 نام: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}",
        "apt_admin_new": "📥 درخواست نوبت جدید\n\n📋 کد: {id}\n👤 بیمار: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}\n📞 تلفن مطب: {dphone}\n\n⏳ در انتظار تأیید شما.\nبرای ثبت تاریخ قطعی:\n/confirm {id} 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 نوبت شما تأیید شد!\n\n📋 کد: {id}\n👨‍⚕️ پزشک: {doctor}\n📅 تاریخ: {date}\n⏰ ساعت: {time}\n📍 آدرس: {address}\n\nلطفاً ۱۵ دقیقه قبل در مطب باشید.",
        "pt_created": "🎫 پرونده‌ی شما ساخته شد\n\n📋 کد پرونده: {code}\n\nاین کد رو یه جای امن نگه دار 💙\nهر وقت خواستی ببینی کجای کاریم، فقط بنویس: پرونده",
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
        "delete_ask": "⚠️ آیا مطمئنی می‌خوای همه‌ی اطلاعاتت پاک بشه؟\n\nاین کار قابل بازگشت نیست.\nبرای تأیید بنویس: بله حذف کن\nبرای انصراف بنویس: نه",
        "delete_done": "✅ همه‌ی اطلاعات شما پاک شد.\n\nاگه بازم به ما نیاز داشتی، در خدمتیم 💙",
        "delete_cancel": "باشه، اطلاعاتت دست‌نخورده موند.",
    },
    "ar": {
        "welcome": "🌟 أهلاً بكم في شيراز ميديكال!\n\nرفيقكم في رحلة العلاج والإقامة في شيراز.\n\n🔹 التعريف بالأطباء المتخصصين\n🔹 أماكن الإقامة والمواصلات\n🔹 جولات في معالم شيراز\n🔹 الدعم في جميع المراحل\n\nاكتبوا طلبكم.\nمثلاً: طبيب قلب",
        "more": "هل لديكم سؤال آخر؟ (نعم / لا)",
        "go": "تفضلوا، اكتبوا سؤالكم.",
        "rate": "🙏 هل أنتم راضون عن خدماتنا؟ (نعم / لا)",
        "thanks": "🙏 شكراً لكم!\n\nإذا كنتم راضين عن خدماتنا، يرجى تعريفنا لأصدقائكم ومعارفكم. 🌹",
        "why": "نأسف. يرجى كتابة سبب عدم رضاكم.",
        "thanks_fb": "شكراً لملاحظاتكم. 🙏",
        "retry": "عذراً، لم أستطع الرد الآن.",
        "text_only": "يرجى كتابة سؤالكم نصاً.",
        "apt_ask": "📅 لحجز موعد مع هذا الطبيب، اضغط ١.\n📞 للاتصال المباشر، اضغط ٢.",
        "apt_pick_title": "👨‍⚕️ الأطباء أعلاه:",
        "apt_pick_footer": "\n📅 لحجز موعد، اكتب رقم الطبيب:",
        "apt_name": "👤 يرجى كتابة الاسم الكامل:",
        "apt_phone": "📞 يرجى كتابة رقم الهاتف:",
        "apt_submitted": "✅ تم تسجيل طلب الموعد!\n\n📋 رقم المتابعة: {id}\n👨‍⚕️ الطبيب: {doctor}\n\n⏳ سنتصل بالعيادة وننسق أسرع موعد متاح.\nسنبلغكم بالنتيجة عبر هذا الروبوت.",
        "apt_cancelled": "❌ تم إلغاء تسجيل الموعد.",
        "apt_invalid": "يرجى الضغط على أحد الأرقام المعطاة.\n\n🚪 للخروج، اكتبوا: قائمة",
        "apt_error": "❌ عذراً، حدثت مشكلة في تسجيل الموعد.",
        "apt_my": "📋 مواعيدكم:",
        "apt_none": "لم تسجلوا أي موعد بعد.",
        "apt_confirm_final": "هل نسجل الطلب بهذه المعلومات؟ (نعم / لا)\n\n👤 الاسم: {name}\n📞 الهاتف: {phone}\n👨‍⚕️ الطبيب: {doctor}",
        "apt_admin_new": "📥 طلب موعد جديد\n\n📋 الرقم: {id}\n👤 المريض: {name}\n📞 الهاتف: {phone}\n👨‍⚕️ الطبيب: {doctor}\n📞 هاتف العيادة: {dphone}\n\n⏳ في انتظار تأكيدكم.\nلتسجيل التاريخ النهائي:\n/confirm {id} 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 تم تأكيد موعدكم!\n\n📋 الرقم: {id}\n👨‍⚕️ الطبيب: {doctor}\n📅 التاريخ: {date}\n⏰ الوقت: {time}\n📍 العنوان: {address}\n\nيرجى الحضور قبل ١٥ دقيقة.",
        "pt_created": "🎫 تم إنشاء ملفكم\n\n📋 رقم الملف: {code}\n\nاحفظوا هذا الرقم في مكان آمن 💙\nمتى أردتم معرفة مرحلة علاجكم، اكتبوا: ملف",
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
        "pt_apt_line_pending": "⏳ {id} — {doctor} — في انتظار تحديد التاريخ",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} الساعة {time}",
        "pt_not_found": "ليس لديكم ملف بعد. مع أول موعد، سيتم إنشاء ملفكم 💙",
        "delete_ask": "⚠️ هل أنتم متأكدون من حذف كل معلوماتكم؟\n\nهذا الإجراء لا يمكن التراجع عنه.\nللتأكيد اكتبوا: نعم احذف\nللإلغاء اكتبوا: لا",
        "delete_done": "✅ تم حذف كل معلوماتكم.\n\nإذا احتجتم إلينا مجدداً، نحن في خدمتكم 💙",
        "delete_cancel": "حسناً، معلوماتكم محفوظة.",
    },
    "en": {
        "welcome": "🌟 Welcome to Shiraz Medical!\n\nYour companion for treatment and stay in Shiraz.\n\n🔹 Find specialized doctors\n🔹 Accommodation & transportation\n🔹 Explore Shiraz attractions\n🔹 Support at every step\n\nWrite your request.\nE.g.: heart doctor",
        "more": "Any other question? (Yes / No)",
        "go": "Please go ahead.",
        "rate": "🙏 Were you satisfied? (Yes / No)",
        "thanks": "🙏 Thank you!\n\nIf you were satisfied with our services, please recommend us to your friends and acquaintances. 🌹",
        "why": "We're sorry. Please tell us what went wrong.",
        "thanks_fb": "Thank you for your feedback. 🙏",
        "retry": "Sorry, I couldn't answer. Please try again.",
        "text_only": "Please write your question as text.",
        "apt_ask": "📅 To book with this doctor, press 1.\n📞 For direct call, press 2.",
        "apt_pick_title": "👨‍⚕️ Doctors above:",
        "apt_pick_footer": "\n📅 To book, write the doctor number:",
        "apt_name": "👤 Please write your full name:",
        "apt_phone": "📞 Please write your phone number (e.g., 09123456789):",
        "apt_submitted": "✅ Your appointment request has been submitted!\n\n📋 Tracking code: {id}\n👨‍⚕️ Doctor: {doctor}\n\n⏳ We'll contact the clinic and arrange the earliest available appointment.\nYou'll be notified through this bot.",
        "apt_cancelled": "❌ Booking cancelled.",
        "apt_invalid": "Please press one of the given numbers.\n\n🚪 To exit, write: menu",
        "apt_error": "❌ Sorry, there was a problem booking.",
        "apt_my": "📋 Your appointments:",
        "apt_none": "You have no appointments yet.",
        "apt_confirm_final": "Submit this request? (Yes / No)\n\n👤 Name: {name}\n📞 Phone: {phone}\n👨‍⚕️ Doctor: {doctor}",
        "apt_admin_new": "📥 New appointment request\n\n📋 Code: {id}\n👤 Patient: {name}\n📞 Phone: {phone}\n👨‍⚕️ Doctor: {doctor}\n📞 Clinic phone: {dphone}\n\n⏳ Awaiting your confirmation.\nTo set the final date:\n/confirm {id} 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 Your appointment is confirmed!\n\n📋 Code: {id}\n👨‍⚕️ Doctor: {doctor}\n📅 Date: {date}\n⏰ Time: {time}\n📍 Address: {address}\n\nPlease arrive 15 minutes early.",
        "pt_created": "🎫 Your file has been created\n\n📋 File code: {code}\n\nKeep this code safe 💙\nWhenever you want to see your progress, just write: file",
        "pt_title": "🎫 Your Health File\n━━━━━━━━━━━━━━━",
        "pt_code": "📋 File code: {code}",
        "pt_name": "👤 Name: {name}",
        "pt_progress": "\n🌟 Your journey to recovery:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "Your request was received",
        "pt_stages_doctor": "Doctor assigned",
        "pt_stages_date": "Final appointment date confirmed",
        "pt_stages_accommodation": "Accommodation arranged",
        "pt_stages_transport": "Transport arranged",
        "pt_stages_treatment": "Treatment completed",
        "pt_stages_followup": "Health follow-up",
        "pt_appointments": "\n📅 Your appointments:",
        "pt_apt_line_pending": "⏳ {id} — {doctor} — awaiting date assignment",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} at {time}",
        "pt_not_found": "You don't have a file yet. Your file will be created with the first appointment 💙",
        "delete_ask": "⚠️ Are you sure you want to delete all your data?\n\nThis cannot be undone.\nTo confirm, write: yes delete\nTo cancel, write: no",
        "delete_done": "✅ All your data has been deleted.\n\nIf you ever need us again, we're here 💙",
        "delete_cancel": "Okay, your data remains intact.",
    },
}
# ============ MSG2 ============
MSG2 = {
    "fa": {
        "ref_your_code": "🔗 کد معرف شما: {code}\n\nهر کسی رو که به شیراز مدیکال دعوت کنی، هم تو پاداش می‌گیری هم اون 💙\n\nلینک اختصاصی:\n{link}",
        "ref_your_stats": "👥 تعداد دعوت‌شده‌ها: {count}\n🎁 پاداش‌های شما: {rewards}",
        "ref_your_code_short": "🎁 کد معرف شما: {code}",
        "ref_new_from": "🎉 یکی از دوستان شما با کد {code} به شیراز مدیکال پیوست!\n\nپاداش شما ثبت شد: ۱۰٪ تخفیف ویزیت بعدی 🌹",
        "ref_welcome_new": "🎉 خوش آمدید!\n\nشما با کد معرف {code} وارد شدید.\n🎁 پاداش شما: ۵٪ تخفیف اولین ویزیت",
        "ref_invite_msg": "🌟 دوستت رو به شیراز مدیکال دعوت کن\n\nکد معرفت: {code}\n\nلینک:\n{link}\n\nاگه دوستت با این کد بیاد:\n🎁 تو: ۱۰٪ تخفیف ویزیت بعدی\n🎁 دوستت: ۵٪ تخفیف اولین ویزیت",
        "ref_none_yet": "هنوز کسی رو معرفی نکردی. کدت رو با دوستانت به اشتراک بذار 💙",
        "hope_morning": "🌹 صبح بخیر!\n\nامیدواریم امروز یه روز پر از آرامش و بهبودی باشه.",
        "hope_night": "🌙 شب بخیر\n\nامیدواریم امروزتون آروم گذشته باشه.\n\n💊 یادتون نره داروهاتون رو مصرف کنید.\n🌷 ما کنارتونیم تا سلامتی‌تون برگرده.",
        "hope_stage_request": "🌟 اولین قدمت رو برداشتی!\n\nما با تمام وجود تلاش می‌کنیم که مسیر درمانت راحت و امیدبخش باشه.",
        "hope_stage_doctor": "👨‍⚕️ پزشک متخصص شما مشخص شد\n\nخوشحالیم که تونستیم بهت کمک کنیم. حالا مرحله‌ی بعدی، تعیین نوبته 🌷",
        "hope_stage_date": "🎉 تاریخ نوبتت نهایی شد!\n\nیه قدم دیگه به سلامتی نزدیک‌تر شدی 💙",
        "hope_stage_accommodation": "🏨 اقامت شما هماهنگ شد\n\nمی‌تونی با خیال راحت به درمانت فکر کنی 🌷",
        "hope_stage_transport": "🚗 حمل‌ونقل شما آماده شد\n\nمسیرت به سمت سلامتی هموار شد 💙",
        "hope_stage_treatment": "🌸 درمان شما انجام شد\n\nآرزو می‌کنیم هر روز حالت بهتر از دیروز باشه.",
        "hope_stage_followup": "🌷 مرحله‌ی پیگیری\n\nما همچنان کنارتونیم. اگه سؤالی داشتید، بپرسید 💙",
        "hope_general_1": "💙 «سلامتی بزرگ‌ترین ثروته.»",
        "hope_general_2": "🌷 «هر روز، فرصتی برای بهبوده.»",
        "hope_general_3": "✨ «امید، نصف درمانه.»",
        "hope_general_4": "🌸 «تو تنها نیستی. ما کنارتیم.»",
        "comp_ask": "👥 آیا همراه دارید؟ (بله / نه)\n\nاگه داشته باشید، می‌تونیم در مواقع مهم بهشون اطلاع بدیم 💙",
        "comp_ask_phone": "📞 لطفاً شماره‌ی همراهتون رو بنویسید:\n(مثال: 09123456789)",
        "comp_ask_name": "👤 اسم همراهتون چیه؟",
        "comp_saved": "✅ همراه شما ثبت شد\n\n👤 نام: {name}\n📞 تلفن: {phone}\n\nدر مواقع مهم بهشون اطلاع می‌دیم 💙",
        "comp_skip": "باشه، هر وقت خواستید همراه اضافه کنید، فقط بنویسید: همراه",
        "sos_menu": "🚨 وضعیت اضطراری\n\nلطفاً یکی از شماره‌ها رو بزنید:\n\n1️⃣ اورژانس ۱۱۵\n2️⃣ نزدیک‌ترین بیمارستان\n3️⃣ راهنمای کمک‌های اولیه\n4️⃣ اطلاع به همراه من\n5️⃣ انصراف\n\n🚪 برای خروج، بنویسید: منو",
        "sos_115": "🚑 شماره اورژانس: ۱۱۵\n\nلطفاً تماس بگیرید و آدرس دقیقتون رو بگید.\n\nاگه با کسی هستید، بهش بگید بهم کمک کنه.",
        "sos_first_aid": "🩺 کمک‌های اولیه\n\n🔹 درد قفسه سینه:\n- بشین و استراحت کن\n- قرص زیر زبانی اگه داری مصرف کن\n- فوراً ۱۱۵\n\n🔹 خونریزی:\n- فشار مستقیم روی زخم\n- بالا نگه دار اندام رو\n- ۱۱۵\n\n🔹 تنگی نفس:\n- بشین، صاف\n- لباس رو شل کن\n- ۱۱۵\n\n⚠️ این راهنما فقط کمک اولیه‌ست، جایگزین پزشک نیست.",
        "sos_alert_companion": "⚠️ پیام اضطراری\n\nبیمار {name} (کد: {code}) الان اضطراری داره.\n\nلطفاً فوراً تماس بگیرید.\n📞 {phone}",
        "sos_no_companion": "❌ شما همراه ثبت نکردید. اگه می‌خواید، بنویسید: همراه",
        "comp_voice_menu": "📩 صدای شما\n\nما به نظر شما اهمیت می‌دیم. لطفاً انتخاب کنید:\n\n1️⃣ انتقاد از پزشک\n2️⃣ انتقاد از مرکز درمانی\n3️⃣ انتقاد از اقامت\n4️⃣ انتقاد از حمل‌ونقل\n5️⃣ شکایت کلی\n6️⃣ انصراف\n\n🚪 برای خروج، بنویسید: منو",
        "comp_voice_text": "📝 لطفاً نظرتون رو بنویسید:\n\nمی‌تونید اسم بگید یا ناشناس بمونید. (اختیاری)\n\nاگه ناشناس می‌خواید، فقط «ناشناس» بنویسید.\n\n🚪 برای خروج، بنویسید: منو",
        "comp_voice_saved": "✅ پیام شما ثبت شد\n\n📋 کد پیگیری: {id}\n\nما در اسرع وقت پیگیری می‌کنیم و از طریق همین ربات بهتون خبر می‌دیم 💙\n\nممنون که بهمون اعتماد کردید.",
        "comp_voice_skip": "باشه، هر وقت خواستید، فقط بنویسید: شکایت",
        "comp_voice_admin": "📩 شکایت جدید\n\n📋 کد: {id}\nدسته: {category}\nنام: {name}\nChatID: {cid}\n\nمتن:\n{text}",
        "rights_title": "⚖️ حقوق شما به عنوان بیمار\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ دریافت اطلاعات کامل درباره بیماری و درمان\n2️⃣ حق انتخاب پزشک و مرکز درمانی\n3️⃣ محرمانه بودن اطلاعات پزشکی\n4️⃣ رضایت آگاهانه قبل از هر اقدام\n5️⃣ دریافت نسخه و مدارک درمانی\n6️⃣ حق شکایت و پیگیری\n7️⃣ احترام بدون تبعیض\n8️⃣ دسترسی به پرونده‌ی پزشکی خود\n\n📞 در صورت نقض هرکدوم:\n- با ما: @ShirazMedBot\n- سازمان نظام پزشکی\n- وزارت بهداشت: 190",
        "med_menu": "⏰ یادآور دارو\n\nمی‌تونیم یادت بندازیم که داروهات رو سر وقت مصرف کنی 💙\n\n1️⃣ افزودن یادآور جدید\n2️⃣ مشاهده‌ی یادآورهای من\n3️⃣ انصراف\n\n🚪 برای خروج، بنویسید: منو",
        "med_ask_name": "💊 اسم دارو چیه؟",
        "med_ask_time": "⏰ چه ساعتی یادآوری کنم؟\n\nمثال: 08:00 یا 20:30",
        "med_saved": "✅ یادآور ثبت شد\n\n💊 دارو: {name}\n⏰ ساعت: {time}\n\nما سر وقت بهت اطلاع می‌دیم 💙",
        "med_reminder": "⏰ یادآور دارو\n\n💊 {name}\n\n1️⃣ مصرف شد\n2️⃣ تأخیر\n3️⃣ امروز مصرف نمی‌کنم",
        "med_reminder_ok": "🌷 آفرین! ادامه بده 💙",
        "med_reminder_late": "باشه، ولی سعی کن هر چه زودتر مصرف کنی 🌷",
        "med_reminder_skip": "باشه، ولی اگه ادامه پیدا کرد، به پزشکت بگو.",
        "med_none": "هنوز یادآوری ثبت نکردی. هر وقت خواستی، بنویس: دارو",
        "food_title": "🍏 راهنمای تغذیه و تداخلات\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 تداخل‌های مهم دارویی:\n\n• آنتی‌بیوتیک + لبنیات (۲ ساعت فاصله)\n• آهن + چای/قهوه (۱ ساعت فاصله)\n• وارفارین + کلم و اسفناج (احتیاط)\n• تیروئید + صبح ناشتا\n• مسکن + معده خالی (ممنوع)\n\n💧 در طول درمان آب زیاد بنوش\n🥗 میوه و سبزیجات تازه مصرف کن\n🚫 از خوددرمانی پرهیز کن\n\n⚠️ این راهنمای کلیه، نه جایگزین پزشک.",
        "menu_main": "📋 منوی شیراز مدیکال\n\n💬 خواسته‌ت رو بنویس (مثلاً: دکتر قلب)\n\n🔹 پرونده — مشاهده‌ی پرونده\n🔹 نوبت — نوبت‌های من\n🔹 همراه — افزودن همراه\n🔹 شکایت — ارسال نظر\n🔹 دارو — یادآور دارو\n🔹 حقوق — حقوق بیمار\n🔹 چی بخورم — تغذیه\n🔹 گل — جمله‌ی امیدبخش\n🔹 اضطراری — کمک فوری\n🔹 دعوت — کد معرفی من\n🔹 شب‌بخیر — پیام شب\n\n🏥 سرویس‌های ویژه:\n🔹 پیراپزشکی — فیزیوتراپی، آزمایشگاه\n🔹 سالمندان — خانه سالمندان شیراز\n\n🚪 هر جا گیر کردی، بنویس: منو",
        "cmd_help": "برای دیدن منو، بنویسید: منو",
        "ai_unavailable": "🙏 الان نمی‌تونم پاسخ بدم.\n\nلطفاً دوباره تلاش کنید یا از منو استفاده کنید:\nبنویسید: منو",
        "para_menu": "🏥 خدمات پیراپزشکی\n\nچه نوع خدماتی می‌خواید؟\n\n🔹 فیزیوتراپی — بنویسید: فیزیوتراپی\n🔹 آزمایشگاه — بنویسید: آزمایشگاه\n🔹 رادیولوژی — بنویسید: رادیولوژی\n🔹 پرستاری در منزل — بنویسید: پرستاری\n🔹 تزریق — بنویسید: تزریق\n🔹 طب سنتی — بنویسید: طب سنتی\n🔹 کاردرمانی — بنویسید: کاردرمانی\n🔹 گفتاردرمانی — بنویسید: گفتاردرمانی\n🔹 پروتز و ارتوپدی فنی — بنویسید: پروتز",
        "elderly_menu": "🏡 خانه‌های سالمندان شیراز\n\nبرای دیدن لیست کامل، بنویسید: همه خانه سالمندان\n\n🚪 برای خروج، بنویسید: منو",
        "elderly_all_title": "🏡 خانه‌های سالمندان شیراز:",
    },
    "ar": {
        "ref_your_code": "🔗 رمز الإحالة: {code}\n\nكل من تدعوه إلى شيراز ميديكال، كلاكما تحصلان على مكافأة 💙\n\nالرابط الخاص:\n{link}",
        "ref_your_stats": "👥 عدد المدعوين: {count}\n🎁 مكافآتكم: {rewards}",
        "ref_your_code_short": "🎁 رمز الإحالة: {code}",
        "ref_new_from": "🎉 أحد أصدقائكم انضم بكود {code}!\n\nتم تسجيل مكافأتكم: خصم ١٠٪ على الزيارة القادمة 🌹",
        "ref_welcome_new": "🎉 أهلاً بكم!\n\nدخلتم بكود {code}.\n🎁 مكافأتكم: خصم ٥٪ على أول زيارة",
        "ref_invite_msg": "🌟 ادعوا أصدقاءكم إلى شيراز ميديكال\n\nرمزكم: {code}\n\nالرابط:\n{link}\n\nإذا انضم صديقكم بهذا الرمز:\n🎁 أنتم: خصم ١٠٪\n🎁 صديقكم: خصم ٥٪",
        "ref_none_yet": "لم تدعوا أحداً بعد. شاركوا رمزكم مع أصدقائكم 💙",
        "hope_morning": "🌹 صباح الخير!\n\nنتمنى لكم يوماً مليئاً بالسلام والشفاء.",
        "hope_night": "🌙 مساء الخير\n\nنتمنى أن يكون يومكم هادئاً.\n\n💊 لا تنسوا تناول أدويتكم.\n🌷 نحن معكم حتى تستعيدوا صحتكم.",
        "hope_stage_request": "🌟 خطوتم الخطوة الأولى!\n\nنبذل قصارى جهدنا ليكون مسار علاجكم سهلاً ومليئاً بالأمل.",
        "hope_stage_doctor": "👨‍⚕️ تم تحديد طبيبكم المتخصص\n\nسعداء بمساعدتكم. الآن المرحلة التالية: تحديد الموعد 🌷",
        "hope_stage_date": "🎉 تم تحديد موعدكم النهائي!\n\nخطوة أخرى نحو الشفاء 💙",
        "hope_stage_accommodation": "🏨 تم تنسيق الإقامة\n\nيمكنكم التركيز على علاجكم بكل راحة 🌷",
        "hope_stage_transport": "🚗 المواصلات جاهزة\n\nطريقكم نحو الشفاء سالك 💙",
        "hope_stage_treatment": "🌸 تم العلاج\n\nنتمنى أن تتحسنوا يوماً بعد يوم.",
        "hope_stage_followup": "🌷 مرحلة المتابعة\n\nما زلنا معكم. إن كان لديكم سؤال، اسألوا 💙",
        "hope_general_1": "💙 «الصحة أعظم ثروة.»",
        "hope_general_2": "🌷 «كل يوم فرصة للتحسن.»",
        "hope_general_3": "✨ «الأمل نصف الشفاء.»",
        "hope_general_4": "🌸 «لستم وحدكم. نحن معكم.»",
        "comp_ask": "👥 هل لديكم مرافق؟ (نعم / لا)\n\nإذا كان لديكم، يمكننا إبلاغه في الأوقات المهمة 💙",
        "comp_ask_phone": "📞 يرجى كتابة رقم المرافق:\n(مثال: 09123456789)",
        "comp_ask_name": "👤 ما اسم المرافق؟",
        "comp_saved": "✅ تم تسجيل المرافق\n\n👤 الاسم: {name}\n📞 الهاتف: {phone}\n\nسنبلغه في الأوقات المهمة 💙",
        "comp_skip": "حسناً، متى أردتم إضافة مرافق، اكتبوا: مرافق",
        "sos_menu": "🚨 حالة طارئة\n\nيرجى الضغط على أحد الأرقام:\n\n1️⃣ الإسعاف ١١٥\n2️⃣ أقرب مستشفى\n3️⃣ الإسعافات الأولية\n4️⃣ إبلاغ مرافقي\n5️⃣ إلغاء\n\n🚪 للخروج، اكتبوا: قائمة",
        "sos_115": "🚑 رقم الإسعاف: ١١٥\n\nيرجى الاتصال وإعطاء عنوانكم بدقة.",
        "sos_first_aid": "🩺 الإسعافات الأولية\n\n🔹 ألم الصدر:\n- اجلس واسترح\n- حبة تحت اللسان إن وجدت\n- اتصل ١١٥\n\n🔹 نزيف:\n- ضغط مباشر\n- ارفع الطرف\n- اتصل ١١٥\n\n🔹 ضيق التنفس:\n- اجلس مستقيماً\n- فك الملابس\n- اتصل ١١٥\n\n⚠️ هذا إسعاف أولي فقط، وليس بديلاً عن الطبيب.",
        "sos_alert_companion": "⚠️ رسالة طارئة\n\nالمريض {name} (كود: {code}) في حالة طارئة.\n\nيرجى الاتصال فوراً.\n📞 {phone}",
        "sos_no_companion": "❌ لم تسجلوا مرافقاً. إن أردتم، اكتبوا: مرافق",
        "comp_voice_menu": "📩 صوتكم\n\nنهتم برأيكم. يرجى الاختيار:\n\n1️⃣ انتقاد الطبيب\n2️⃣ انتقاد المركز الطبي\n3️⃣ انتقاد الإقامة\n4️⃣ انتقاد المواصلات\n5️⃣ شكوى عامة\n6️⃣ إلغاء\n\n🚪 للخروج، اكتبوا: قائمة",
        "comp_voice_text": "📝 يرجى كتابة رأيكم:\n\nيمكنكم ذكر الاسم أو البقاء مجهولين. (اختياري)\n\nإن أردتم المجهول، اكتبوا: مجهول",
        "comp_voice_saved": "✅ تم تسجيل رسالتكم\n\n📋 رقم المتابعة: {id}\n\nسنتابع في أقرب وقت ونبلغكم عبر هذا الروبوت 💙\n\nشكراً لثقتكم.",
        "comp_voice_skip": "حسناً، متى أردتم، اكتبوا: شكوى",
        "comp_voice_admin": "📩 شكوى جديدة\n\n📋 الرقم: {id}\nالفئة: {category}\nالاسم: {name}\nChatID: {cid}\n\nالنص:\n{text}",
        "rights_title": "⚖️ حقوقكم كمريض\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ الحصول على معلومات كاملة\n2️⃣ حق اختيار الطبيب والمركز\n3️⃣ سرية المعلومات الطبية\n4️⃣ الموافقة قبل أي إجراء\n5️⃣ الحصول على الوصفة والمستندات\n6️⃣ حق الشكوى والمتابعة\n7️⃣ الاحترام دون تمييز\n8️⃣ الوصول إلى ملفكم الطبي\n\n📞 في حال انتهاك أي منها:\n- معنا: @ShirazMedBot\n- نقابة الأطباء\n- وزارة الصحة: 190",
        "med_menu": "⏰ تذكير الدواء\n\nيمكننا تذكيركم بتناول أدويتكم 💙\n\n1️⃣ إضافة تذكير جديد\n2️⃣ عرض تذكيراتي\n3️⃣ إلغاء\n\n🚪 للخروج، اكتبوا: قائمة",
        "med_ask_name": "💊 ما اسم الدواء؟",
        "med_ask_time": "⏰ في أي ساعة نذكركم؟\n\nمثال: 08:00 أو 20:30",
        "med_saved": "✅ تم حفظ التذكير\n\n💊 الدواء: {name}\n⏰ الساعة: {time}\n\nسنذكركم في الوقت المحدد 💙",
        "med_reminder": "⏰ تذكير الدواء\n\n💊 {name}\n\n1️⃣ تم الاستخدام\n2️⃣ تأخير\n3️⃣ لن أستخدمه اليوم",
        "med_reminder_ok": "🌷 أحسنتم! استمروا 💙",
        "med_reminder_late": "حسناً، لكن حاولوا الإسراع 🌷",
        "med_reminder_skip": "حسناً، لكن إن استمر، أخبروا طبيبكم.",
        "med_none": "لم تسجلوا تذكيراً بعد. متى أردتم، اكتبوا: دواء",
        "food_title": "🍏 دليل التغذية والتداخلات\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 تداخلات مهمة:\n\n• مضاد حيوي + ألبان (ساعتان)\n• حديد + شاي/قهوة (ساعة)\n• وارفارين + ملفوف وسبانخ (حذر)\n• الغدة الدرقية + صباحاً على الريق\n• مسكن + معدة فارغة (ممنوع)\n\n💧 اشربوا ماء كثيراً\n🥗 فواكه وخضروات طازجة\n🚫 تجنبوا العلاج الذاتي\n\n⚠️ هذا دليل عام، وليس بديلاً عن الطبيب.",
        "menu_main": "📋 قائمة شيراز ميديكال\n\n💬 اكتبوا طلبكم (مثلاً: طبيب قلب)\n\n🔹 ملف — عرض الملف\n🔹 موعد — مواعيدي\n🔹 مرافق — إضافة مرافق\n🔹 شكوى — إرسال رأي\n🔹 دواء — تذكير الدواء\n🔹 حقوق — حقوق المريض\n🔹 طعام — التغذية\n🔹 زهرة — جملة أمل\n🔹 طوارئ — مساعدة عاجلة\n🔹 دعوة — رمز الإحالة\n🔹 مساء الخير — رسالة المساء\n\n🏥 خدمات خاصة:\n🔹 مساعد طبي — علاج طبيعي، مختبر\n🔹 مسنين — دور رعاية المسنين\n\n🚪 في أي مكان، اكتبوا: قائمة",
        "cmd_help": "لعرض القائمة، اكتبوا: قائمة",
        "ai_unavailable": "🙏 لا أستطيع الرد الآن.\n\nحاولوا مجدداً أو استخدموا القائمة:\nاكتبوا: قائمة",
        "para_menu": "🏥 الخدمات الطبية المساعدة\n\nماذا تريدون؟\n\n🔹 علاج طبيعي — اكتبوا: علاج طبيعي\n🔹 مختبر — اكتبوا: مختبر\n🔹 أشعة — اكتبوا: أشعة\n🔹 تمريض منزلي — اكتبوا: تمريض\n🔹 حقن — اكتبوا: حقن\n🔹 طب تقليدي — اكتبوا: طب تقليدي\n🔹 علاج وظيفي — اكتبوا: علاج وظيفي\n🔹 علاج النطق — اكتبوا: علاج النطق\n🔹 أطراف صناعية — اكتبوا: أطراف",
        "elderly_menu": "🏡 دور رعاية المسنين في شيراز\n\nلعرض القائمة الكاملة، اكتبوا: كل دور المسنين\n\n🚪 للخروج، اكتبوا: قائمة",
        "elderly_all_title": "🏡 دور رعاية المسنين في شيراز:",
    },
    "en": {
        "ref_your_code": "🔗 Your referral code: {code}\n\nEveryone you invite to Shiraz Medical, both get rewards 💙\n\nYour link:\n{link}",
        "ref_your_stats": "👥 Invited: {count}\n🎁 Your rewards: {rewards}",
        "ref_your_code_short": "🎁 Your referral code: {code}",
        "ref_new_from": "🎉 A friend joined using code {code}!\n\nYour reward is recorded: 10% off next visit 🌹",
        "ref_welcome_new": "🎉 Welcome!\n\nYou joined with referral code {code}.\n🎁 Your reward: 5% off your first visit",
        "ref_invite_msg": "🌟 Invite friends to Shiraz Medical\n\nYour code: {code}\n\nLink:\n{link}\n\nIf a friend joins with this code:\n🎁 You: 10% off next visit\n🎁 Friend: 5% off first visit",
        "ref_none_yet": "You haven't invited anyone yet. Share your code with friends 💙",
        "hope_morning": "🌹 Good morning!\n\nWishing you a peaceful, healing day.",
        "hope_night": "🌙 Good night\n\nHope your day was calm.\n\n💊 Don't forget your medications.\n🌷 We're with you until you're well.",
        "hope_stage_request": "🌟 You took the first step!\n\nWe'll do our best to make your treatment journey smooth and hopeful.",
        "hope_stage_doctor": "👨‍⚕️ Your specialist is assigned\n\nGlad we could help. Next step: confirming your appointment 🌷",
        "hope_stage_date": "🎉 Your appointment date is confirmed!\n\nOne more step closer to recovery 💙",
        "hope_stage_accommodation": "🏨 Accommodation arranged\n\nNow you can focus on your treatment 🌷",
        "hope_stage_transport": "🚗 Transport is ready\n\nYour path to recovery is smooth 💙",
        "hope_stage_treatment": "🌸 Treatment completed\n\nWishing you improvement day by day.",
        "hope_stage_followup": "🌷 Follow-up phase\n\nWe're still with you. Ask if you have questions 💙",
        "hope_general_1": "💙 \"Health is the greatest wealth.\"",
        "hope_general_2": "🌷 \"Every day is a chance to heal.\"",
        "hope_general_3": "✨ \"Hope is half the cure.\"",
        "hope_general_4": "🌸 \"You are not alone. We are with you.\"",
        "comp_ask": "👥 Do you have a companion? (Yes / No)\n\nIf yes, we can inform them at important moments 💙",
        "comp_ask_phone": "📞 Please write your companion's phone number:\n(e.g., 09123456789)",
        "comp_ask_name": "👤 What is the companion's name?",
        "comp_saved": "✅ Companion saved\n\n👤 Name: {name}\n📞 Phone: {phone}\n\nWe'll inform them at important moments 💙",
        "comp_skip": "Okay, whenever you want to add a companion, just write: companion",
        "sos_menu": "🚨 Emergency\n\nPlease press one:\n\n1️⃣ Emergency 115\n2️⃣ Nearest hospital\n3️⃣ First aid guide\n4️⃣ Alert my companion\n5️⃣ Cancel\n\n🚪 To exit, write: menu",
        "sos_115": "🚑 Emergency number: 115\n\nPlease call and give your exact address.",
        "sos_first_aid": "🩺 First Aid\n\n🔹 Chest pain:\n- Sit and rest\n- Sublingual pill if available\n- Call 115\n\n🔹 Bleeding:\n- Direct pressure\n- Elevate the limb\n- Call 115\n\n🔹 Shortness of breath:\n- Sit upright\n- Loosen clothing\n- Call 115\n\n⚠️ This is first aid only, not a substitute for a doctor.",
        "sos_alert_companion": "⚠️ EMERGENCY\n\nPatient {name} (code: {code}) has an emergency.\n\nPlease call immediately.\n📞 {phone}",
        "sos_no_companion": "❌ No companion registered. If you want, write: companion",
        "comp_voice_menu": "📩 Your Voice\n\nWe value your opinion. Please choose:\n\n1️⃣ Complaint about doctor\n2️⃣ Complaint about medical center\n3️⃣ Complaint about accommodation\n4️⃣ Complaint about transport\n5️⃣ General complaint\n6️⃣ Cancel\n\n🚪 To exit, write: menu",
        "comp_voice_text": "📝 Please write your feedback:\n\nYou can give your name or stay anonymous. (Optional)\n\nFor anonymous, write: anonymous",
        "comp_voice_saved": "✅ Your message was recorded\n\n📋 Tracking code: {id}\n\nWe'll follow up soon and notify you through this bot 💙\n\nThank you for trusting us.",
        "comp_voice_skip": "Okay, whenever you want, write: complaint",
        "comp_voice_admin": "📩 New Complaint\n\n📋 Code: {id}\nCategory: {category}\nName: {name}\nChatID: {cid}\n\nText:\n{text}",
        "rights_title": "⚖️ Your Rights as a Patient\n━━━━━━━━━━━━━━━",
        "rights_body": "1️⃣ Right to full information\n2️⃣ Right to choose doctor & center\n3️⃣ Confidentiality of medical info\n4️⃣ Informed consent before any procedure\n5️⃣ Right to prescriptions & documents\n6️⃣ Right to complain & follow up\n7️⃣ Respect without discrimination\n8️⃣ Access to your own medical file\n\n📞 If any is violated:\n- With us: @ShirazMedBot\n- Medical Council\n- Ministry of Health: 190",
        "med_menu": "⏰ Medication Reminder\n\nWe can remind you to take your meds 💙\n\n1️⃣ Add new reminder\n2️⃣ View my reminders\n3️⃣ Cancel\n\n🚪 To exit, write: menu",
        "med_ask_name": "💊 What's the medication name?",
        "med_ask_time": "⏰ What time should we remind?\n\nExample: 08:00 or 20:30",
        "med_saved": "✅ Reminder saved\n\n💊 Medication: {name}\n⏰ Time: {time}\n\nWe'll remind you on time 💙",
        "med_reminder": "⏰ Medication Reminder\n\n💊 {name}\n\n1️⃣ Taken\n2️⃣ Delayed\n3️⃣ Skipping today",
        "med_reminder_ok": "🌷 Well done! Keep going 💙",
        "med_reminder_late": "Okay, but try to take it soon 🌷",
        "med_reminder_skip": "Okay, but if it continues, tell your doctor.",
        "med_none": "No reminders yet. Whenever you want, write: med",
        "food_title": "🍏 Nutrition & Interactions Guide\n━━━━━━━━━━━━━━━",
        "food_body": "🔴 Important interactions:\n\n• Antibiotics + dairy (2h gap)\n• Iron + tea/coffee (1h gap)\n• Warfarin + cabbage/spinach (caution)\n• Thyroid + empty stomach in morning\n• Painkillers + empty stomach (avoid)\n\n💧 Drink plenty of water\n🥗 Fresh fruits & vegetables\n🚫 Avoid self-medication\n\n⚠️ This is general info, not a substitute for a doctor.",
        "menu_main": "📋 Shiraz Medical Menu\n\n💬 Write your request (e.g., heart doctor)\n\n🔹 file — view your file\n🔹 appointment — my appointments\n🔹 companion — add companion\n🔹 complaint — send feedback\n🔹 med — medication reminder\n🔹 rights — patient rights\n🔹 food — nutrition\n🔹 flower — hope message\n🔹 emergency — urgent help\n🔹 invite — my referral code\n🔹 goodnight — evening message\n\n🏥 Special services:\n🔹 paramedical — physiotherapy, lab\n🔹 elderly — Shiraz nursing homes\n\n🚪 If stuck anywhere, write: menu",
        "cmd_help": "To see menu, write: menu",
        "ai_unavailable": "🙏 I can't answer right now.\n\nPlease try again or use the menu:\nwrite: menu",
        "para_menu": "🏥 Paramedical Services\n\nWhat service do you need?\n\n🔹 Physiotherapy — write: physiotherapy\n🔹 Lab — write: lab\n🔹 Radiology — write: radiology\n🔹 Home nursing — write: nursing\n🔹 Injection — write: injection\n🔹 Traditional medicine — write: traditional\n🔹 Occupational therapy — write: occupational\n🔹 Speech therapy — write: speech\n🔹 Orthotics — write: orthotics",
        "elderly_menu": "🏡 Nursing Homes in Shiraz\n\nFor full list, write: all nursing homes\n\n🚪 To exit, write: menu",
        "elderly_all_title": "🏡 Nursing Homes in Shiraz:",
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
        "district": "المنطقة", "amenities": "المرافق", "distance_to_hospitals": "المسافة إلى المستشفيات",
        "has_translator": "مترجم", "languages_spoken": "اللغات",
        "description": "الوصف", "services": "الخدمات", "type": "النوع",
        "pharmacy_code": "رمز الصيدلية", "services_offered": "الخدمات المقدمة",
        "is_24h": "على مدار الساعة", "ipd_code": "رمز IPD",
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
        "district": "District", "amenities": "Amenities", "distance_to_hospitals": "Distance to Hospitals",
        "has_translator": "Has Translator", "languages_spoken": "Languages",
        "description": "Description", "services": "Services", "type": "Type",
        "pharmacy_code": "Pharmacy Code", "services_offered": "Services Offered",
        "is_24h": "24 Hours", "ipd_code": "IPD Code",
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
    "fa": "🚨 فوراً به اورژانس مراجعه کن. تلفن: ۱۱۵\n\nاگه می‌خوای راهنمای بیشتر بگیری، بنویس: اضطراری",
    "ar": "🚨 توجه فوراً إلى الطوارئ. هاتف: ١١٥\n\nللمزيد اكتب: طوارئ",
    "en": "🚨 Go to emergency. Phone: 115\n\nFor more help, write: emergency"
}

# ============ SIMPLE COMMANDS ============
CMD_FILE = {"پرونده", "پرونده من", "ملف", "ملفي", "file", "my file", "پرونده‌ام"}
CMD_APT = {"نوبت", "نوبت‌ها", "نوبت‌هام", "نوبت های من", "موعد", "مواعيد", "مواعيدي", "appointment", "appointments", "my appointments", "my apt"}
CMD_COMPANION = {"همراه", "همراهم", "مرافق", "companion", "my companion"}
CMD_COMPLAINT = {"شکایت", "شکایات", "انتقاد", "نظر", "شكوى", "شكاوي", "complaint", "feedback"}
CMD_MED = {"دارو", "یادآور", "یادآور دارو", "دواء", "تذكير", "med", "medication", "reminder"}
CMD_RIGHTS = {"حقوق", "حق من", "حقوق بیمار", "حقوقي", "حقوق المريض", "rights", "my rights", "patient rights"}
CMD_FOOD = {"چی بخورم", "غذا", "تغذیه", "تداخل", "طعام", "تغذية", "food", "nutrition", "diet"}
CMD_FLOWER = {"گل", "امید", "دلگرمی", "زهرة", "أمل", "flower", "hope", "encouragement"}
CMD_SOS = {"اضطراری", "کمک", "فوری", "حالم خوب نیست", "حالم بده", "طوارئ", "مساعدة", "عاجل", "emergency", "help", "urgent", "sos"}
CMD_INVITE = {"دعوت", "معرفی", "کد معرف", "دعوة", "إحالة", "invite", "referral", "invite friends"}
CMD_MENU = {"منو", "راهنما", "کمک منو", "قائمة", "مساعدة", "menu", "help", "guide"}
CMD_NIGHT = {"شب بخیر", "شب‌بخیر", "مساء الخير", "good night", "goodnight"}
CMD_DELETE = {"حذف اطلاعات", "پاک کردن", "delete my data", "احذف معلوماتي"}
CMD_PARA = {"پیراپزشکی", "پارامدیکال", "paramedical", "مساعد طبي"}
CMD_ELDERLY = {"خانه سالمندان", "خانه‌ی سالمندان", "آسایشگاه", "سرای سالمندان", "nursing home", "elderly", "دار المسنين"}
CMD_ELDERLY_ALL = {"همه خانه سالمندان", "کل خانه سالمندان", "all nursing homes", "كل دور المسنين"}

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
        if p.get('chat_id') == str(chat_id):
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
        if p.get('chat_id') == str(chat_id):
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
        if p.get('chat_id') == str(chat_id):
            if 'stages' not in p:
                p['stages'] = {}
            p['stages'][stage] = value
            save_patients(data)
            return True
    return False

def add_appointment_to_patient(chat_id, apt_id):
    data = load_patients()
    for p in data['patients']:
        if p.get('chat_id') == str(chat_id):
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
    stage_order = ["request", "doctor", "date", "accommodation", "transport", "treatment", "followup"]
    for s in stage_order:
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
        MSG2[lang]["hope_general_1"],
        MSG2[lang]["hope_general_2"],
        MSG2[lang]["hope_general_3"],
        MSG2[lang]["hope_general_4"],
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
    return {
        "code": u.get('code', ''),
        "count": u.get('count', 0),
        "rewards": u.get('rewards', [])
    }

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
        bot.reply_to(message, MSG2[lang]["ref_welcome_new"].format(code=code))
        try:
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
            "first_seen": today,
            "last_seen": today,
            "lang": lang,
            "interactions": 1,
            "appointments": 0
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
    dau = 0
    wau = 0
    mau = 0
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
    conv = 0
    if starts > 0:
        conv = round((apts / starts) * 100, 1)
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
        "id": cid,
        "chat_id": str(chat_id),
        "category": category,
        "name": name,
        "text": text,
        "status": "new",
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
        "chat_id": str(chat_id),
        "name": name,
        "time": time_str,
        "active": True,
        "last_sent_date": "",
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
    msg = MSG2[lang].get(hope_key, MSG2[lang]["hope_general_1"])
    try:
        bot.send_message(chat_id, "🌹\n\n" + msg)
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

# ============ SOS ============
def handle_sos_menu(message, lang):
    bot.reply_to(message, MSG2[lang]["sos_menu"])
    user_state[message.chat.id] = "awaiting_sos_choice"

def handle_sos_choice(message, t, lang):
    cid = message.chat.id
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
        else:
            bot.reply_to(message, "❌ لیست بیمارستان‌ها در دسترس نیست.")
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
            user_state[cid] = "active"
            return
        bot.reply_to(message, "✅ اطلاعات به همراه شما اطلاع داده شد.\n\n👤 " + str(comp.get('name', '')) + "\n📞 " + str(comp.get('phone', '')))
        user_state[cid] = "active"
        return
    if t in ("5", "۵"):
        user_state[cid] = "active"
        bot.reply_to(message, MSG[lang]["apt_cancelled"])
        return
    bot.reply_to(message, MSG[lang]["apt_invalid"])

# ============ RIGHTS / FOOD ============
def show_patient_rights(message, lang):
    bot.reply_to(message, MSG2[lang]["rights_title"] + "\n\n" + MSG2[lang]["rights_body"])

def show_food_guide(message, lang):
    bot.reply_to(message, MSG2[lang]["food_title"] + "\n\n" + MSG2[lang]["food_body"])

# ============ AI ============
def get_ai(text, lang):
    prompt = SYSTEM_PROMPT + " پاسخ را به زبان " + LANG_NAMES[lang] + " بنویس."
    if not AVALAI_API_KEY:
        print("AI_ERR: key empty")
        return None
    try:
        r = requests.post(AVALAI_URL,
            headers={"Authorization": "Bearer " + AVALAI_API_KEY, "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]},
            timeout=20)
        print("AI_STATUS: " + str(r.status_code))
        if r.status_code != 200:
            print("AI_BODY: " + r.text[:400])
            return None
        result = r.json()['choices'][0]['message']['content']
        print("AI_OK_LEN: " + str(len(result)))
        if result and len(result.strip()) > 5:
            return result
        return None
    except Exception as e:
        print("AI_EXC: " + str(e))
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
        v = x.get('patient_satisfaction_score', x.get('rating', 0))
        return v
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
    skip_keys = ('id', 'status', 'lat', 'lng', 'created_at', 'updated_at')
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

# ============ ADMIN: deactivate/activate ============
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
    bot.reply_to(message, MSG[user_lang.get(cid, "fa")]["more"])

def get_meta_info():
    try:
        with open("data/meta.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def show_main_menu(message, lang):
    bot.reply_to(message, MSG2[lang]["menu_main"])

# ============ QUERY PROCESSOR ============
def process_query(message, text, lang):
    cid = message.chat.id

    if is_simple_cmd(text, CMD_MENU):
        show_main_menu(message, lang)
        return True
    if is_simple_cmd(text, CMD_FILE):
        p = get_patient_by_chat(cid)
        bot.reply_to(message, format_patient_file(p, lang))
        return True
    if is_simple_cmd(text, CMD_APT):
        apts = get_patient_appointments(cid)
        if not apts:
            bot.reply_to(message, MSG[lang]["apt_none"])
            return True
        lines = [MSG[lang]["apt_my"]]
        for a in apts[-5:]:
            dn = a.get("doctor_name_" + lang) or a.get("doctor_name_fa", "")
            if a.get('status') == 'confirmed' and a.get('date'):
                lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                    id=a['id'], doctor=dn, date=a['date'], time=a.get('time', '')))
            else:
                lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a['id'], doctor=dn))
        bot.reply_to(message, "\n\n".join(lines))
        return True
    if is_simple_cmd(text, CMD_COMPANION):
        user_state[cid] = "awaiting_comp_ask"
        bot.reply_to(message, MSG2[lang]["comp_ask"])
        return True
    if is_simple_cmd(text, CMD_COMPLAINT):
        user_state[cid] = "awaiting_complaint_menu"
        bot.reply_to(message, MSG2[lang]["comp_voice_menu"])
        return True
    if is_simple_cmd(text, CMD_MED):
        user_state[cid] = "awaiting_med_menu"
        bot.reply_to(message, MSG2[lang]["med_menu"])
        return True
    if is_simple_cmd(text, CMD_RIGHTS):
        show_patient_rights(message, lang)
        return True
    if is_simple_cmd(text, CMD_FOOD):
        show_food_guide(message, lang)
        return True
    if is_simple_cmd(text, CMD_FLOWER):
        send_hope_flower(cid, lang)
        return True
    if is_simple_cmd(text, CMD_SOS):
        handle_sos_menu(message, lang)
        return True
    if is_simple_cmd(text, CMD_INVITE):
        code = get_or_create_referral_code(cid)
        link = build_referral_link(code)
        bot.reply_to(message, MSG2[lang]["ref_invite_msg"].format(code=code, link=link))
        return True
    if is_simple_cmd(text, CMD_NIGHT):
        bot.reply_to(message, MSG2[lang]["hope_night"])
        return True
    if is_simple_cmd(text, CMD_DELETE):
        user_state[cid] = "awaiting_delete_confirm"
        bot.reply_to(message, MSG[lang]["delete_ask"])
        return True
    if is_simple_cmd(text, CMD_PARA):
        bot.reply_to(message, MSG2[lang]["para_menu"])
        return True
    if is_simple_cmd(text, CMD_ELDERLY_ALL):
        data = load_json("data/elderly_homes.json")
        if data:
            bot.reply_to(message, MSG2[lang]["elderly_all_title"])
            for item in data[:10]:
                bot.reply_to(message, format_generic(item, lang))
        return True
    if is_simple_cmd(text, CMD_ELDERLY):
        bot.reply_to(message, MSG2[lang]["elderly_menu"])
        return True

    doc = search_by_doctor_name(text)
    if doc:
        bot.reply_to(message, format_doctor(doc, lang))
        user_temp[cid] = {"doctor": doc}
        user_state[cid] = "awaiting_apt_choice"
        bot.reply_to(message, MSG[lang]["apt_ask"])
        return True

    docs = search_specialty(text)
    if docs:
        if is_all_request(text):
            limit = len(docs)
        elif is_best_request(text):
            limit = 1
        else:
            limit = 3
        shown = docs[:limit]
        for d in shown:
            bot.reply_to(message, format_doctor(d, lang))
        if len(shown) == 1:
            user_temp[cid] = {"doctor": shown[0]}
            user_state[cid] = "awaiting_apt_choice"
            bot.reply_to(message, MSG[lang]["apt_ask"])
        elif len(shown) > 1:
            user_temp[cid] = {"doctors": shown}
            user_state[cid] = "awaiting_apt_pick"
            lines = [MSG[lang]["apt_pick_title"]]
            for i, d in enumerate(shown, 1):
                nm = get_value(d, 'name', lang) or get_value(d, 'name', 'fa') or ''
                lines.append(str(i) + ". " + str(nm))
            lines.append(MSG[lang]["apt_pick_footer"])
            bot.reply_to(message, "\n".join(lines))
        return True

    fn = search_non_medical(text)
    if fn:
        data = load_json("data/" + fn)
        if data:
            if is_all_request(text):
                items = data[:10]
            else:
                items = data[:5]
            for item in items:
                bot.reply_to(message, format_generic(item, lang))
            return True

    ai = get_ai(text, lang)
    if ai:
        bot.reply_to(message, ai + AI_DISCLAIMER[lang])
        return True
    bot.reply_to(message, MSG2[lang]["ai_unavailable"])
    return True
# ============ HANDLERS ============
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
    stats = get_user_stats()
    lines = ["📊 وضعیت ربات"]
    if meta:
        lines.append("آخرین آپدیت: " + str(meta.get("last_update", "نامشخص")))
        lines.append("آپدیت بعدی: " + str(meta.get("next_update", "نامشخص")))
    lines.append("")
    lines.append("👥 کاربران:")
    lines.append("• کل: " + str(stats['total']))
    lines.append("• فعال امروز: " + str(stats['dau']))
    lines.append("• فعال ۷ روز: " + str(stats['wau']))
    lines.append("• فعال ۳۰ روز: " + str(stats['mau']))
    lines.append("")
    lines.append("📈 نرخ تبدیل start → نوبت: " + str(stats['conv']) + "%")
    lines.append("")
    lines.append("📅 نوبت‌ها:")
    lines.append("در انتظار تأیید: " + str(len(pending)))
    lines.append("تأیید شده: " + str(len(confirmed)))
    if pending:
        lines.append("")
        lines.append("⏳ در انتظار تأیید:")
        for a in pending[-5:]:
            dn = a.get("doctor_name_fa", "")
            lines.append("• " + a['id'] + " — " + a.get('patient_name', '') + " — " + str(dn))
    lines.append("")
    lines.append("📩 شکایت جدید: " + str(len(new_complaints)))
    lines.append("")
    lines.append("📈 نظرسنجی:")
    lines.append("رضایت: " + str(satisfaction_counter['positive']))
    lines.append("عدم رضایت: " + str(satisfaction_counter['negative']))
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['confirm'])
def confirm_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 4:
        bot.reply_to(message, "❌ فرمت اشتباه.\nمثال:\n/confirm APT-1001 1405/09/20 10:30")
        return
    apt_id = parts[1].upper()
    date_str = validate_date_shamsi(parts[2])
    time_str = validate_time(parts[3])
    if not date_str:
        bot.reply_to(message, "❌ تاریخ نامعتبر. فرمت: 1405/09/20")
        return
    if not time_str:
        bot.reply_to(message, "❌ ساعت نامعتبر. فرمت: 10:30")
        return
    apt = confirm_appointment(apt_id, date_str, time_str)
    if not apt:
        bot.reply_to(message, "❌ نوبت " + apt_id + " پیدا نشد.")
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
    lang = p.get('lang', 'fa')
    bot.reply_to(message, format_patient_file(p, lang))

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
        bot.reply_to(message, "✅ پزشک " + doc_id + " غیرفعال شد.")
    else:
        bot.reply_to(message, "❌ پزشک با شناسه " + doc_id + " پیدا نشد.")

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
        bot.reply_to(message, "✅ پزشک " + doc_id + " فعال شد.")
    else:
        bot.reply_to(message, "❌ پزشک با شناسه " + doc_id + " پیدا نشد.")

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

@bot.message_handler(commands=['menu'])
def menu_command(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    show_main_menu(message, lang)

@bot.message_handler(content_types=['photo', 'voice', 'audio', 'document', 'video', 'sticker'])
def other_types(message):
    cid = message.chat.id
    if cid in user_lang:
        bot.reply_to(message, MSG[user_lang[cid]]["text_only"])
    else:
        user_state[cid] = "choose_lang"
        bot.reply_to(message, START_MSG)

# ============ MAIN HANDLER ============
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
        bot.reply_to(message, MSG[lang]["welcome"])
        try_apply_start_param(message, text, lang)
        return

    lang = user_lang.get(cid, "fa")
    t = clean(text)
    user_name = get_user_name(message)

    # ==== خروج فوری از هر state با کلمات منو/لغو/انصراف ====
    ESCAPE_WORDS = {"منو", "لغو", "انصراف", "قائمة", "menu", "cancel", "help"}
    if t in ESCAPE_WORDS:
        user_state[cid] = "active"
        user_temp.pop(cid, None)
        show_main_menu(message, lang)
        return

    if state == "awaiting_apt_pick":
        pm = {"1": 0, "۱": 0, "یک": 0, "2": 1, "۲": 1, "دو": 1, "3": 2, "۳": 2, "سه": 2}
        if t in pm:
            idx = pm[t]
            docs = user_temp.get(cid, {}).get("doctors", [])
            if idx < len(docs):
                user_temp[cid] = {"doctor": docs[idx]}
                user_state[cid] = "awaiting_apt_choice"
                bot.reply_to(message, MSG[lang]["apt_ask"])
                return
        user_state[cid] = "active"

    if state == "awaiting_apt_choice":
        if t in ("1", "۱", "یک"):
            user_state[cid] = "awaiting_apt_name"
            bot.reply_to(message, MSG[lang]["apt_name"])
            return
        if t in ("2", "۲", "دو"):
            doc = user_temp.get(cid, {}).get("doctor", {})
            user_state[cid] = "active"
            bot.reply_to(message, "📞 " + str(doc.get("phone", "")))
            ask_more(message)
            return
        user_state[cid] = "active"

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
            name=user_temp[cid].get("name", ""),
            phone=phone,
            doctor=dn
        ))
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
                bot.reply_to(message, MSG[lang]["apt_submitted"].format(
                    id=apt['id'], doctor=dn))
                bot.reply_to(message, MSG[lang]["pt_created"].format(code=patient['code']))
                send_hope_for_stage(cid, lang, "request")
                if ADMIN_CHAT_ID:
                    try:
                        dphone = doc.get("phone", "")
                        bot.send_message(ADMIN_CHAT_ID,
                            MSG["fa"]["apt_admin_new"].format(
                                id=apt['id'], name=pname, phone=pphone,
                                doctor=dn, dphone=dphone))
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

    if state == "awaiting_sos_choice":
        handle_sos_choice(message, t, lang)
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
        if t in NO_WORDS:
            user_state[cid] = "awaiting_rating"
            bot.reply_to(message, MSG[lang]["rate"])
            return
        user_state[cid] = "active"

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
                    "❌ عدم رضایت\nزبان: " + LANG_NAMES.get(lang, lang) +
                    "\nنام: " + user_name + "\nChatID: " + str(cid) +
                    "\nمتن: " + text)
            except:
                pass
        return

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


# ============ START ============
print("ربات روشن شد... v34 (خروج از هر state با منو + کامل)")
bot.infinity_polling(timeout=30, long_polling_timeout=30)