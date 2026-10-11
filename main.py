import json
import os
import re
import telebot
import requests
from datetime import datetime, timedelta

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

SYSTEM_PROMPT = "دستیار گردشگری سلامت شیراز. کوتاه و با همدلی جواب بده، بدون قیمت دقیق و بدون تضمین پزشکی. در پایان سؤال نپرس."

START_MSG = """🌟 سلام و خوش آمدید! از اینکه شیراز مدیکال را انتخاب کردید سپاسگزاریم.
🌟 Welcome! Thank you for choosing Shiraz Medical.
🌟 مرحباً بكم! نشكركم لاختياركم شيراز ميديكال.

زبان خود را انتخاب کنید / Choose your language / اختاروا لغتكم:
1 - فارسی
2 - العربية
3 - English"""

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
        "apt_invalid": "لطفاً یکی از شماره‌های داده شده را بزنید.",
        "apt_error": "❌ متأسفانه در ثبت نوبت مشکلی پیش آمد.",
        "apt_my": "📋 نوبت‌های شما:",
        "apt_none": "شما هنوز هیچ نوبتی ثبت نکرده‌اید.",
        "apt_confirm_final": "آیا درخواست با این اطلاعات ثبت شود؟ (بله / نه)\n\n👤 نام: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}",
        "apt_admin_new": "📥 درخواست نوبت جدید\n\n📋 کد: {id}\n👤 بیمار: {name}\n📞 تلفن: {phone}\n👨‍⚕️ پزشک: {doctor}\n📞 تلفن مطب: {dphone}\n\n⏳ در انتظار تأیید شما.\nبرای ثبت تاریخ قطعی:\n/confirm {id} 1405/09/20 10:30",
        "apt_admin_confirm_ok": "✅ نوبت {id} تأیید شد و به بیمار اطلاع داده شد.",
        "apt_admin_confirm_bad": "❌ نوبت {id} پیدا نشد یا فرمت اشتباه است.\nفرمت: /confirm APT-1001 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 نوبت شما تأیید شد!\n\n📋 کد: {id}\n👨‍⚕️ پزشک: {doctor}\n📅 تاریخ: {date}\n⏰ ساعت: {time}\n📍 آدرس: {address}\n\nلطفاً ۱۵ دقیقه قبل در مطب باشید.",
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
        "apt_invalid": "يرجى الضغط على أحد الأرقام المعطاة.",
        "apt_error": "❌ عذراً، حدثت مشكلة في تسجيل الموعد.",
        "apt_my": "📋 مواعيدكم:",
        "apt_none": "لم تسجلوا أي موعد بعد.",
        "apt_confirm_final": "هل نسجل الطلب بهذه المعلومات؟ (نعم / لا)\n\n👤 الاسم: {name}\n📞 الهاتف: {phone}\n👨‍⚕️ الطبيب: {doctor}",
        "apt_admin_new": "📥 طلب موعد جديد\n\n📋 الرقم: {id}\n👤 المريض: {name}\n📞 الهاتف: {phone}\n👨‍⚕️ الطبيب: {doctor}\n📞 هاتف العيادة: {dphone}\n\n⏳ في انتظار تأكيدكم.\nلتسجيل التاريخ النهائي:\n/confirm {id} 1405/09/20 10:30",
        "apt_admin_confirm_ok": "✅ تم تأكيد الموعد {id} وإبلاغ المريض.",
        "apt_admin_confirm_bad": "❌ الموعد {id} غير موجود أو الصيغة خاطئة.\nالصيغة: /confirm APT-1001 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 تم تأكيد موعدكم!\n\n📋 الرقم: {id}\n👨‍⚕️ الطبيب: {doctor}\n📅 التاريخ: {date}\n⏰ الوقت: {time}\n📍 العنوان: {address}\n\nيرجى الحضور قبل ١٥ دقيقة.",
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
        "apt_invalid": "Please press one of the given numbers.",
        "apt_error": "❌ Sorry, there was a problem booking.",
        "apt_my": "📋 Your appointments:",
        "apt_none": "You have no appointments yet.",
        "apt_confirm_final": "Submit this request? (Yes / No)\n\n👤 Name: {name}\n📞 Phone: {phone}\n👨‍⚕️ Doctor: {doctor}",
        "apt_admin_new": "📥 New appointment request\n\n📋 Code: {id}\n👤 Patient: {name}\n📞 Phone: {phone}\n👨‍⚕️ Doctor: {doctor}\n📞 Clinic phone: {dphone}\n\n⏳ Awaiting your confirmation.\nTo set the final date:\n/confirm {id} 1405/09/20 10:30",
        "apt_admin_confirm_ok": "✅ Appointment {id} confirmed and patient notified.",
        "apt_admin_confirm_bad": "❌ Appointment {id} not found or format invalid.\nFormat: /confirm APT-1001 1405/09/20 10:30",
        "apt_patient_confirmed": "🎉 Your appointment is confirmed!\n\n📋 Code: {id}\n👨‍⚕️ Doctor: {doctor}\n📅 Date: {date}\n⏰ Time: {time}\n📍 Address: {address}\n\nPlease arrive 15 minutes early.",
    },
}

# ============ FIELD NAMES ============
FIELD_NAMES = {
    "fa": {
        "name": "نام", "address": "آدرس", "phone": "تلفن", "specialty": "تخصص",
        "office_address": "آدرس مطب", "working_hours": "ساعت کاری",
        "price_range_toman": "قیمت", "patient_satisfaction_score": "امتیاز",
        "reviews_summary": "نظر مسافران", "surgeries_done_at": "بیمارستان‌ها",
        "category": "دسته", "star_rating": "ستاره", "quality_grade": "کیفیت",
        "district": "منطقه", "amenities": "امکانات", "distance_to_hospitals": "فاصله تا بیمارستان",
        "has_translator": "مترجم", "languages_spoken": "زبان‌ها",
        "description": "توضیحات", "services": "خدمات",
        "pharmacy_code": "کد داروخانه", "services_offered": "خدمات ارائه‌شده",
        "is_24h": "شبانه‌روزی", "ipd_code": "کد IPD",
        "ownership": "مالکیت", "specialties": "تخصص‌ها",
    },
    "ar": {
        "name": "الاسم", "address": "العنوان", "phone": "الهاتف", "specialty": "التخصص",
        "office_address": "عنوان العيادة", "working_hours": "ساعات العمل",
        "price_range_toman": "السعر", "patient_satisfaction_score": "التقييم",
        "reviews_summary": "آراء الزوار", "surgeries_done_at": "المستشفيات",
        "category": "الفئة", "star_rating": "التصنيف", "quality_grade": "الجودة",
        "district": "المنطقة", "amenities": "المرافق", "distance_to_hospitals": "المسافة إلى المستشفيات",
        "has_translator": "مترجم", "languages_spoken": "اللغات",
        "description": "الوصف", "services": "الخدمات",
        "pharmacy_code": "رمز الصيدلية", "services_offered": "الخدمات المقدمة",
        "is_24h": "على مدار الساعة", "ipd_code": "رمز IPD",
        "ownership": "الملكية", "specialties": "التخصصات",
    },
    "en": {
        "name": "Name", "address": "Address", "phone": "Phone", "specialty": "Specialty",
        "office_address": "Office Address", "working_hours": "Working Hours",
        "price_range_toman": "Price", "patient_satisfaction_score": "Rating",
        "reviews_summary": "Reviews", "surgeries_done_at": "Hospitals",
        "category": "Category", "star_rating": "Star Rating", "quality_grade": "Quality",
        "district": "District", "amenities": "Amenities", "distance_to_hospitals": "Distance to Hospitals",
        "has_translator": "Has Translator", "languages_spoken": "Languages",
        "description": "Description", "services": "Services",
        "pharmacy_code": "Pharmacy Code", "services_offered": "Services Offered",
        "is_24h": "24 Hours", "ipd_code": "IPD Code",
        "ownership": "Ownership", "specialties": "Specialties",
    },
}

# ============ WORDS ============
YES_WORDS = {"بله", "بلی", "آره", "اره", "yes", "yeah", "y", "نعم", "ايوه", "أيوه"}
NO_WORDS = {"نه", "نخیر", "خیر", "نه ممنون", "ندارم", "no", "nope", "n", "لا", "لا شكرا"}
ALL_WORDS = ["همه", "تمام", "کل", "همگی", "all", "كل", "جميع"]

# ============ DIGITS ============
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

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
}

CONTEXT_WORDS = ["بیمارستان", "hospital", "مستشفى", "شیراز", "shiraz", "شيراز", "doctor", "دکتر", "طبيب", "dr"]

# ============ EMERGENCY ============
EMERGENCY = {
    "fa": ["درد شدید", "تب", "خونریزی", "استفراغ", "ضعف", "غش"],
    "ar": ["ألم شديد", "حمى", "نزيف", "قيء", "ضعف", "إغماء"],
    "en": ["severe pain", "fever", "bleeding", "vomiting", "weakness", "fainting"]
}

EMERGENCY_RESP = {
    "fa": "🚨 فوراً به اورژانس مراجعه کن. تلفن: ۱۱۵",
    "ar": "🚨 توجه فوراً إلى الطوارئ. هاتف: ۱۱۵",
    "en": "🚨 Go to emergency. Phone: 115"
}

# ============ STATE ============
user_state = {}
user_lang = {}
user_temp = {}
satisfaction_counter = {"count": 0, "positive": 0, "negative": 0}

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

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        return data if isinstance(data, list) else None
    except:
        return None

def get_value(item, key, lang):
    if (key + "_" + lang) in item:
        return item[key + "_" + lang]
    if (key + "_fa") in item:
        return item[key + "_fa"]
    if key in item:
        return item[key]
    return None

def item_name_for_search(item):
    for k in ("name_fa", "name_ar", "name_en", "name"):
        if k in item:
            return str(item[k])
    return ""

def is_all_request(text):
    low = text.lower()
    words = re.findall(r"\w+", low)
    for w in ALL_WORDS:
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

def detect_text_language(text):
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

# ============ APPOINTMENTS ============
APPOINTMENTS_FILE = "/app/data/appointments.json"
APPOINTMENTS_FILE_FALLBACK = "data/appointments.json"

def _appt_path():
    d = os.path.dirname(APPOINTMENTS_FILE)
    if os.path.isdir(d):
        return APPOINTMENTS_FILE
    return APPOINTMENTS_FILE_FALLBACK

def load_appointments():
    try:
        with open(_appt_path(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"next_id": 1001, "appointments": []}

def save_appointments(data):
    try:
        with open(_appt_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def create_appointment(doctor, pname, pphone, chat_id, lang):
    data = load_appointments()
    apt_id = "APT-" + str(data['next_id'])
    data['next_id'] += 1
    apt = {
        "id": apt_id,
        "doctor_id": doctor.get('id', ''),
        "doctor_name_fa": doctor.get('name_fa', ''),
        "doctor_name_ar": doctor.get('name_ar', ''),
        "doctor_name_en": doctor.get('name_en', ''),
        "doctor_phone": doctor.get('phone', ''),
        "doctor_address_fa": doctor.get('office_address_fa', ''),
        "doctor_address_ar": doctor.get('office_address_ar', ''),
        "doctor_address_en": doctor.get('office_address_en', ''),
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

# ============ SEARCH FUNCTIONS ============
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
    def sc(x):
        r = x.get('ratings', {})
        if isinstance(r, dict) and 'patient_satisfaction_score' in r:
            return r['patient_satisfaction_score']
        return x.get('patient_satisfaction_score', 0)
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
    p = get_value(doc, 'phone', lang) or ''
    a = get_value(doc, 'office_address', lang) or ''
    hs = get_value(doc, 'surgeries_done_at', lang) or []
    if isinstance(hs, str):
        hs = [hs]
    h = " - ".join(str(x) for x in hs)
    pr = get_value(doc, 'price_range_toman', lang) or ''
    r = doc.get('patient_satisfaction_score', '')
    if lang == "en":
        return "Doctor: " + str(n) + "\nSpecialty: " + str(s) + "\nAddress: " + str(a) + "\nHospitals: " + str(h) + "\nPhone: " + str(p) + "\nPrice: " + str(pr) + "\nRating: " + str(r) + "/5"
    if lang == "ar":
        return "الطبيب: " + str(n) + "\nالتخصص: " + str(s) + "\nالعنوان: " + str(a) + "\nالمستشفيات: " + str(h) + "\nالهاتف: " + str(p) + "\nالتكلفة: " + str(pr) + "\nالتقييم: " + str(r) + "/5"
    return "دکتر: " + str(n) + "\nتخصص: " + str(s) + "\nآدرس: " + str(a) + "\nبیمارستان: " + str(h) + "\nتلفن: " + str(p) + "\nقیمت: " + str(pr) + "\nامتیاز: " + str(r) + "/5"

def format_generic(item, lang):
    if not isinstance(item, dict):
        return str(item)
    fnames = FIELD_NAMES.get(lang, {})
    lines = []
    seen = set()
    for k, v in item.items():
        if k == 'id':
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
        if isinstance(val, list):
            val = " - ".join(str(x) for x in val)
        elif isinstance(val, dict):
            parts = []
            for kk, vv in val.items():
                if isinstance(vv, list):
                    vv = " - ".join(str(x) for x in vv)
                parts.append(str(kk) + ": " + str(vv))
            val = " - ".join(parts)
        sv = str(val).strip()
        if sv and sv != 'None':
            lines.append(str(label) + ": " + sv)
    return "\n".join(lines)

# ============ AI ============
def get_ai(text, lang):
    prompt = SYSTEM_PROMPT + " پاسخ را به زبان " + LANG_NAMES[lang] + " بنویس."
    try:
        r = requests.post(AVALAI_URL,
            headers={"Authorization": "Bearer " + AVALAI_API_KEY, "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]},
            timeout=15)
        return r.json()['choices'][0]['message']['content']
    except:
        return None

# ============ STATE HELPERS ============
def ask_more(message):
    cid = message.chat.id
    user_state[cid] = "awaiting_more"
    bot.reply_to(message, MSG[user_lang.get(cid, "fa")]["more"])

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

def get_meta_info():
    try:
        with open("data/meta.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# ============ QUERY PROCESSOR ============
def process_query(message, text, lang):
    cid = message.chat.id
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
                nm = d.get("name_" + lang) or d.get('name_fa', '')
                lines.append(str(i) + ". " + str(nm))
            lines.append(MSG[lang]["apt_pick_footer"])
            bot.reply_to(message, "\n".join(lines))
        return True
    fn = search_non_medical(text)
    if fn:
        data = load_json("data/" + fn)
        if data:
            if isinstance(data, dict):
                items = [data]
            else:
                items = data[:5]
            for item in items:
                bot.reply_to(message, format_generic(item, lang))
            return True
    ai = get_ai(text, lang)
    if ai:
        bot.reply_to(message, ai)
        return True
    return False
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
    lines = ["📊 وضعیت ربات"]
    if meta:
        lines.append("آخرین آپدیت: " + str(meta.get("last_update", "نامشخص")))
        lines.append("آپدیت بعدی: " + str(meta.get("next_update", "نامشخص")))
    lines.append("")
    lines.append("📈 نظرسنجی:")
    lines.append("رضایت: " + str(satisfaction_counter['positive']))
    lines.append("عدم رضایت: " + str(satisfaction_counter['negative']))
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
    date_str = parts[2]
    time_str = parts[3]
    apt = confirm_appointment(apt_id, date_str, time_str)
    if not apt:
        bot.reply_to(message, "❌ نوبت " + apt_id + " پیدا نشد.")
        return
    bot.reply_to(message, "✅ نوبت " + apt_id + " تأیید شد.")
    patient_cid = apt.get('patient_chat_id', '')
    p_lang = apt.get('patient_lang', 'fa')
    if patient_cid:
        dn = apt.get("doctor_name_" + p_lang) or apt.get("doctor_name_fa", "")
        ad = apt.get("doctor_address_" + p_lang) or apt.get("doctor_address_fa", "")
        try:
            bot.send_message(patient_cid, MSG[p_lang]["apt_patient_confirmed"].format(
                id=apt_id, doctor=dn, date=date_str, time=time_str, address=ad))
        except:
            pass

@bot.message_handler(commands=['lang'])
def lang_command(message):
    user_state[message.chat.id] = "choose_lang"
    bot.reply_to(message, START_MSG)

@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.chat.id] = "choose_lang"
    bot.reply_to(message, START_MSG)

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
        if st == 'pending':
            status_icon = "⏳"
        elif st == 'confirmed':
            status_icon = "✅"
        else:
            status_icon = "❌"
        line = status_icon + " " + a['id'] + "\n👨‍⚕️ " + str(dn)
        if a.get('date'):
            line += "\n📅 " + a['date'] + " — ⏰ " + a.get('time', '')
        else:
            line += "\n⏳ در انتظار تأیید"
        lines.append(line)
    bot.reply_to(message, "\n\n".join(lines))

@bot.message_handler(content_types=['photo', 'voice', 'audio', 'document', 'video', 'sticker'])
def other_types(message):
    cid = message.chat.id
    if cid in user_lang:
        bot.reply_to(message, MSG[user_lang[cid]]["text_only"])
    else:
        user_state[cid] = "choose_lang"
        bot.reply_to(message, START_MSG)

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
        bot.reply_to(message, MSG[lang]["welcome"])
        return

    lang = user_lang.get(cid, "fa")
    t = clean(text)
    user_name = get_user_name(message)

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
        user_temp[cid]["name"] = text.strip()
        user_state[cid] = "awaiting_apt_phone"
        bot.reply_to(message, MSG[lang]["apt_phone"])
        return

    if state == "awaiting_apt_phone":
        phone = re.sub(r'[^0-9+]', '', text.translate(DIGITS).strip())
        if len(phone) < 8:
            bot.reply_to(message, MSG[lang]["apt_phone"])
            return
        user_temp[cid]["phone"] = phone
        user_state[cid] = "awaiting_apt_confirm"
        doc = user_temp.get(cid, {}).get("doctor", {})
        dn = doc.get("name_" + lang) or doc.get("name_fa", "")
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
                dn = doc.get("name_" + lang) or doc.get("name_fa", "")
                bot.reply_to(message, MSG[lang]["apt_submitted"].format(
                    id=apt['id'], doctor=dn))
                if ADMIN_CHAT_ID:
                    try:
                        dphone = doc.get("phone", "")
                        bot.send_message(ADMIN_CHAT_ID,
                            MSG["fa"]["apt_admin_new"].format(
                                id=apt['id'], name=pname, phone=pphone,
                                doctor=dn, dphone=dphone))
                    except:
                        pass
            except Exception:
                bot.reply_to(message, MSG[lang]["apt_error"])
            user_temp.pop(cid, None)
            ask_more(message)
            return
        if t in NO_WORDS:
            user_temp.pop(cid, None)
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            ask_more(message)
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
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
            bot.reply_to(message, MSG[lang]["thanks"])
            satisfaction_counter["count"] += 1
            satisfaction_counter["positive"] += 1
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
    if new_state != old_state:
        return
    if not answered:
        bot.reply_to(message, MSG[lang]["retry"])
    ask_more(message)

# ============ START ============
print("ربات روشن شد... v30 (نوبت‌گیری pending + /confirm)")
bot.infinity_polling(timeout=30, long_polling_timeout=30)