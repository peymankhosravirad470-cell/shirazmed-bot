import json, os, re, telebot, requests
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
        "welcome": "🌟 به شیراز مدیکال خوش آمدید!\n\nهمراه شما در مسیر درمان و اقامت در شیراز؛ با هدفی روشن و خدماتی کامل.\n\n🔹 معرفی پزشکان متخصص و بیمارستان‌های مجهز\n🔹 اقامتگاه‌های مناسب و حمل‌ونقل آسان\n🔹 گشت‌وگذار در جاذبه‌های دیدنی شیراز\n🔹 پشتیبانی و راهنمایی در تمام مراحل\n\nخواسته‌ی خود را بنویسید؛ ما در کنار شما هستیم.\nمثلاً: دکتر قلب",
        "more": "سؤال دیگری دارید؟ (بله / نه)",
        "go": "بفرمایید، سؤالتان را بنویسید.",
        "rate": "🙏 از خدمات ما راضی بودید؟ (بله / خیر)",
        "thanks": "سپاسگزاریم. 🙏 هر زمان سؤالی داشتید بنویسید.",
        "why": "متأسفیم. لطفاً بنویسید چه چیزی باعث نارضایتی شد تا بهتر شویم.",
        "thanks_fb": "ممنون از نظرتان. 🙏",
        "retry": "متأسفم، الان نتوانستم جواب بدهم. دوباره تلاش کنید.",
        "text_only": "لطفاً سؤال خود را به صورت متن بنویسید.",
        "apt_ask": "📅 برای گرفتن نوبت با این پزشک، شماره ۱ را بزنید.\n📞 برای تماس مستقیم، شماره ۲ را بزنید.",
        "apt_pick_title": "👨‍⚕️ پزشکان بالا:",
        "apt_pick_footer": "\n📅 برای گرفتن نوبت، شماره‌ی پزشک مورد نظرت رو بنویس:",
        "apt_date": "🗓 تاریخ نوبت را انتخاب کنید:\n1. امروز\n2. فردا\n3. پس‌فردا\n4. انصراف",
        "apt_time": "⏰ ساعت نوبت را انتخاب کنید:\n1. ۱۰:۰۰ صبح\n2. ۱۲:۰۰ ظهر\n3. ۱۶:۰۰ عصر\n4. ۱۸:۰۰ عصر\n5. ۲۰:۰۰ شب\n6. انصراف",
        "apt_name": "👤 لطفاً نام و نام خانوادگی خود را بنویسید:",
        "apt_phone": "📞 لطفاً شماره تماس خود را بنویسید (مثال: 09123456789):",
        "apt_confirmed": "✅ نوبت شما با موفقیت ثبت شد!\n\n📋 کد پیگیری: {id}\n👨‍⚕️ پزشک: {doctor}\n📅 تاریخ: {date}\n⏰ ساعت: {time}\n📍 آدرس: {address}\n\nلطفاً کد پیگیری را نزد خود نگه دارید.",
        "apt_cancelled": "❌ ثبت نوبت لغو شد.",
        "apt_invalid": "لطفاً یکی از شماره‌های داده شده را بزنید.",
        "apt_error": "❌ متأسفانه در ثبت نوبت مشکلی پیش آمد. لطفاً دوباره تلاش کنید.",
        "apt_my": "📋 نوبت‌های ثبت‌شده‌ی شما:",
        "apt_none": "شما هنوز هیچ نوبتی ثبت نکرده‌اید.",
        "apt_confirm_final": "آیا نوبت با این اطلاعات تایید می‌شود؟ (بله / نه)\n\n👤 نام: {name}\n📞 تلفن: {phone}\n📅 تاریخ: {date}\n⏰ ساعت: {time}",
    },
    "ar": {
        "welcome": "🌟 أهلاً بكم في شيراز ميديكال!\n\nرفيقكم في رحلة العلاج والإقامة في شيراز؛ بهدف واضح وخدمات متكاملة.\n\n🔹 التعريف بالأطباء المتخصصين والمستشفيات المجهزة\n🔹 أماكن الإقامة المناسبة والمواصلات السهلة\n🔹 جولات في معالم شيراز السياحية\n🔹 الدعم والإرشاد في جميع المراحل\n\nاكتبوا طلبكم؛ نحن إلى جانبكم.\nمثلاً: طبيب قلب",
        "more": "هل لديكم سؤال آخر؟ (نعم / لا)",
        "go": "تفضلوا، اكتبوا سؤالكم.",
        "rate": "🙏 هل أنتم راضون عن خدماتنا؟ (نعم / لا)",
        "thanks": "شكراً لكم. 🙏 اكتبوا لنا في أي وقت.",
        "why": "نأسف لذلك. يرجى كتابة سبب عدم رضاكم لنتحسن.",
        "thanks_fb": "شكراً لملاحظاتكم. 🙏",
        "retry": "عذراً، لم أستطع الرد الآن. حاولوا مرة أخرى.",
        "text_only": "يرجى كتابة سؤالكم نصاً.",
        "apt_ask": "📅 لحجز موعد مع هذا الطبيب، اضغط ١.\n📞 للاتصال المباشر، اضغط ٢.",
        "apt_pick_title": "👨‍⚕️ الأطباء أعلاه:",
        "apt_pick_footer": "\n📅 لحجز موعد، اكتب رقم الطبيب:",
        "apt_date": "🗓 اختر تاريخ الموعد:\n١. اليوم\n٢. غداً\n٣. بعد الغد\n٤. إلغاء",
        "apt_time": "⏰ اختر وقت الموعد:\n١. ١٠:٠٠ صباحاً\n٢. ١٢:٠٠ ظهراً\n٣. ٤:٠٠ عصراً\n٤. ٦:٠٠ مساءً\n٥. ٨:٠٠ مساءً\n٦. إلغاء",
        "apt_name": "👤 يرجى كتابة الاسم الكامل:",
        "apt_phone": "📞 يرجى كتابة رقم الهاتف (مثال: 09123456789):",
        "apt_confirmed": "✅ تم تسجيل موعدكم بنجاح!\n\n📋 رقم المتابعة: {id}\n👨‍⚕️ الطبيب: {doctor}\n📅 التاريخ: {date}\n⏰ الوقت: {time}\n📍 العنوان: {address}\n\nيرجى الاحتفاظ برقم المتابعة.",
        "apt_cancelled": "❌ تم إلغاء تسجيل الموعد.",
        "apt_invalid": "يرجى الضغط على أحد الأرقام المعطاة.",
        "apt_error": "❌ عذراً، حدثت مشكلة في تسجيل الموعد. حاولوا مرة أخرى.",
        "apt_my": "📋 مواعيدكم المسجلة:",
        "apt_none": "لم تسجلوا أي موعد بعد.",
        "apt_confirm_final": "هل تؤكدون الموعد بهذه المعلومات؟ (نعم / لا)\n\n👤 الاسم: {name}\n📞 الهاتف: {phone}\n📅 التاريخ: {date}\n⏰ الوقت: {time}",
    },
    "en": {
        "welcome": "🌟 Welcome to Shiraz Medical!\n\nYour companion on the path of treatment and stay in Shiraz; with a clear purpose and complete services.\n\n🔹 Find specialized doctors and well-equipped hospitals\n🔹 Suitable accommodations and easy transportation\n🔹 Explore Shiraz tourist attractions\n🔹 Support and guidance at every step\n\nWrite your request; we are by your side.\nFor example: heart doctor",
        "more": "Do you have any other question? (Yes / No)",
        "go": "Sure, please go ahead.",
        "rate": "🙏 Were you satisfied with our service? (Yes / No)",
        "thanks": "Thank you. 🙏 Write to us any time.",
        "why": "We're sorry. Please tell us what went wrong so we can improve.",
        "thanks_fb": "Thank you for your feedback. 🙏",
        "retry": "Sorry, I couldn't answer right now. Please try again.",
        "text_only": "Please write your question as text.",
        "apt_ask": "📅 To book an appointment with this doctor, press 1.\n📞 For direct call, press 2.",
        "apt_pick_title": "👨‍⚕️ Doctors above:",
        "apt_pick_footer": "\n📅 To book, write the doctor number:",
        "apt_date": "🗓 Choose appointment date:\n1. Today\n2. Tomorrow\n3. Day after tomorrow\n4. Cancel",
        "apt_time": "⏰ Choose appointment time:\n1. 10:00 AM\n2. 12:00 PM\n3. 4:00 PM\n4. 6:00 PM\n5. 8:00 PM\n6. Cancel",
        "apt_name": "👤 Please write your full name:",
        "apt_phone": "📞 Please write your phone number (e.g., 09123456789):",
        "apt_confirmed": "✅ Your appointment has been booked successfully!\n\n📋 Tracking code: {id}\n👨‍⚕️ Doctor: {doctor}\n📅 Date: {date}\n⏰ Time: {time}\n📍 Address: {address}\n\nPlease keep your tracking code.",
        "apt_cancelled": "❌ Appointment booking cancelled.",
        "apt_invalid": "Please press one of the given numbers.",
        "apt_error": "❌ Sorry, there was a problem booking. Please try again.",
        "apt_my": "📋 Your booked appointments:",
        "apt_none": "You have not booked any appointment yet.",
        "apt_confirm_final": "Do you confirm this appointment? (Yes / No)\n\n👤 Name: {name}\n📞 Phone: {phone}\n📅 Date: {date}\n⏰ Time: {time}",
    },
}
# ============ FIELD NAMES ============
FIELD_NAMES = {
    "fa": {
        "name": "نام", "category": "دسته", "star_rating": "ستاره", "quality_grade": "کیفیت",
        "address": "آدرس", "district": "منطقه", "phone": "تلفن", "amenities": "امکانات",
        "distance_to_hospitals": "فاصله تا بیمارستان‌ها", "distance_to_city_center": "فاصله تا مرکز شهر",
        "has_translator": "مترجم", "languages_spoken": "زبان‌ها", "patient_satisfaction_score": "امتیاز",
        "reviews_summary": "نظر مسافران", "specialty": "تخصص", "medical_code": "کد پزشکی",
        "office_address": "آدرس مطب", "working_hours": "ساعت کاری", "surgeries_done_at": "بیمارستان‌ها",
        "price_range_toman": "محدوده قیمت", "consultation_fee_toman": "هزینه ویزیت",
        "visiting_hours": "ساعت بازدید", "ticket_price_toman": "قیمت بلیط",
        "duration_of_visit": "مدت بازدید", "best_season": "بهترین فصل", "accessibility": "دسترسی",
        "suitable_for": "مناسب برای", "unesco_registered": "ثبت یونسکو", "historical_era": "دوره تاریخی",
        "climate": "آب و هوا", "ethnicity": "قومیت", "is_purely_natural": "طبیعی محض",
        "nearest_city": "نزدیک‌ترین شهر", "distance_from_shiraz_km": "فاصله از شیراز",
        "type": "نوع", "service_area": "محدوده خدمات", "pricing_method": "نحوه قیمت‌گذاری",
        "special_hospital_tourism_service": "خدمات بیمارستانی/گردشگری",
        "languages_supported": "زبان‌های پشتیبانی", "description": "توضیحات", "services": "خدمات",
        "emergency_contact": "شماره اضطراری", "notes": "توضیحات", "email": "ایمیل",
        "response_time": "زمان پاسخ‌دهی", "process": "مراحل",
        "medical_visa_documents": "مدارک ویزای درمانی", "hospital_admission_documents": "مدارک پذیرش بیمارستان",
        "translator_requirement": "مترجم", "administrative_steps": "مراحل اداری",
        "costs_and_payment": "هزینه‌ها و پرداخت", "official_authorities": "مراجع رسمی",
        "official_system_links": "لینک‌های رسمی", "city": "شهر", "topic": "موضوع",
        "location_type": "موقعیت", "unesco_status": "وضعیت یونسکو", "ownership": "مالکیت",
        "ipd_status": "وضعیت IPD", "specialties": "تخصص‌ها", "location": "موقعیت", "contact": "تماس",
        "license_status": "وضعیت مجوز", "pharmacy_code": "کد داروخانه", "services_offered": "خدمات ارائه‌شده",
        "is_24h": "شبانه‌روزی", "ipd_code": "کد IPD", "translator_languages": "زبان‌های مترجم",
    },
    "ar": {
        "name": "الاسم", "category": "الفئة", "star_rating": "التصنيف", "quality_grade": "الجودة",
        "address": "العنوان", "district": "المنطقة", "phone": "الهاتف", "amenities": "المرافق",
        "distance_to_hospitals": "المسافة إلى المستشفيات", "distance_to_city_center": "المسافة إلى وسط المدينة",
        "has_translator": "مترجم", "languages_spoken": "اللغات", "patient_satisfaction_score": "التقييم",
        "reviews_summary": "آراء الزوار", "specialty": "التخصص", "medical_code": "الرمز الطبي",
        "office_address": "عنوان العيادة", "working_hours": "ساعات العمل", "surgeries_done_at": "المستشفيات",
        "price_range_toman": "نطاق السعر", "consultation_fee_toman": "رسوم الاستشارة",
        "visiting_hours": "ساعات الزيارة", "ticket_price_toman": "سعر التذكرة",
        "duration_of_visit": "مدة الزيارة", "best_season": "أفضل موسم", "accessibility": "الوصول",
        "suitable_for": "مناسب لـ", "unesco_registered": "مسجل في اليونسكو", "historical_era": "الحقبة التاريخية",
        "climate": "المناخ", "ethnicity": "الإثنية", "is_purely_natural": "طبيعي بحت",
        "nearest_city": "أقرب مدينة", "distance_from_shiraz_km": "المسافة من شيراز",
        "type": "النوع", "service_area": "منطقة الخدمة", "pricing_method": "طريقة التسعير",
        "special_hospital_tourism_service": "خدمات المستشفى/السياحة",
        "languages_supported": "اللغات المدعومة", "description": "الوصف", "services": "الخدمات",
        "emergency_contact": "رقم الطوارئ", "notes": "ملاحظات", "email": "البريد الإلكتروني",
        "response_time": "وقت الاستجابة", "process": "الخطوات",
        "medical_visa_documents": "وثائق التأشيرة الطبية", "hospital_admission_documents": "وثائق القبول في المستشفى",
        "translator_requirement": "مترجم", "administrative_steps": "الخطوات الإدارية",
        "costs_and_payment": "التكاليف والدفع", "official_authorities": "الجهات الرسمية",
        "official_system_links": "الروابط الرسمية", "city": "المدينة", "topic": "الموضوع",
        "location_type": "الموقع", "unesco_status": "حالة اليونسكو", "ownership": "الملكية",
        "ipd_status": "حالة IPD", "specialties": "التخصصات", "location": "الموقع", "contact": "التواصل",
        "license_status": "حالة الترخيص", "pharmacy_code": "رمز الصيدلية", "services_offered": "الخدمات المقدمة",
        "is_24h": "على مدار الساعة", "ipd_code": "رمز IPD", "translator_languages": "لغات المترجم",
    },
    "en": {
        "name": "Name", "category": "Category", "star_rating": "Star Rating", "quality_grade": "Quality Grade",
        "address": "Address", "district": "District", "phone": "Phone", "amenities": "Amenities",
        "distance_to_hospitals": "Distance to Hospitals", "distance_to_city_center": "Distance to City Center",
        "has_translator": "Has Translator", "languages_spoken": "Languages Spoken", "patient_satisfaction_score": "Rating",
        "reviews_summary": "Reviews Summary", "specialty": "Specialty", "medical_code": "Medical Code",
        "office_address": "Office Address", "working_hours": "Working Hours", "surgeries_done_at": "Hospitals",
        "price_range_toman": "Price Range", "consultation_fee_toman": "Consultation Fee",
        "visiting_hours": "Visiting Hours", "ticket_price_toman": "Ticket Price",
        "duration_of_visit": "Duration of Visit", "best_season": "Best Season", "accessibility": "Accessibility",
        "suitable_for": "Suitable For", "unesco_registered": "UNESCO Registered", "historical_era": "Historical Era",
        "climate": "Climate", "ethnicity": "Ethnicity", "is_purely_natural": "Purely Natural",
        "nearest_city": "Nearest City", "distance_from_shiraz_km": "Distance from Shiraz",
        "type": "Type", "service_area": "Service Area", "pricing_method": "Pricing Method",
        "special_hospital_tourism_service": "Hospital/Tourism Service",
        "languages_supported": "Languages Supported", "description": "Description", "services": "Services",
        "emergency_contact": "Emergency Contact", "notes": "Notes", "email": "Email",
        "response_time": "Response Time", "process": "Process",
        "medical_visa_documents": "Medical Visa Documents", "hospital_admission_documents": "Hospital Admission Documents",
        "translator_requirement": "Translator Requirement", "administrative_steps": "Administrative Steps",
        "costs_and_payment": "Costs and Payment", "official_authorities": "Official Authorities",
        "official_system_links": "Official System Links", "city": "City", "topic": "Topic",
        "location_type": "Location Type", "unesco_status": "UNESCO Status", "ownership": "Ownership",
        "ipd_status": "IPD Status", "specialties": "Specialties", "location": "Location", "contact": "Contact",
        "license_status": "License Status", "pharmacy_code": "Pharmacy Code", "services_offered": "Services Offered",
        "is_24h": "24 Hours", "ipd_code": "IPD Code", "translator_languages": "Translator Languages",
    },
}

# ============ YES/NO/ALL WORDS ============
YES_WORDS = {"بله", "بلی", "آره", "اره", "yes", "yeah", "y", "نعم", "ايوه", "أيوه"}
NO_WORDS = {"نه", "نخیر", "خیر", "نه ممنون", "نه، ممنون", "نه مرسی", "سوالی ندارم", "سؤالی ندارم", "ندارم", "no", "nope", "n", "no thanks", "لا", "لا شكرا", "لا شكراً"}
ALL_WORDS = ["همه", "تمام", "کل", "همگی", "all", "كل", "جميع"]

# ============================================================
#  SPECIALTY MAP
# ============================================================
SPECIALTY_MAP = {}

def add_specialty(filename, *words):
    for w in words:
        SPECIALTY_MAP[w.lower()] = filename

add_specialty("cardiology.json",
    "قلب", "قلبی", "کاردیو", "cardio", "heart", "قلبية", "قلب و عروق", "عروق", "سکته قلبی", "فشار خون")
add_specialty("dermatology.json",
    "پوست", "درماتولوژی", "derma", "skin", "جلد", "جلدية", "زیبایی پوست", "آکنه", "جوش")
add_specialty("dentistry.json",
    "دندان", "دندانپزشک", "دندانپزشکی", "dental", "dentist", "أسنان", "اسنان", "طبيب أسنان")
add_specialty("kids_dentistry.json",
    "دندان کودکان", "دندانپزشکی کودکان", "kids dental", "دندان شیری", "أسنان أطفال", "أطفال أسنان")
add_specialty("ophthalmology.json",
    "چشم", "چشم‌پزشک", "چشم پزشکی", "eye", "ophthal", "عيون", "عين", "بصري", "آب مروارید", "لیزیک")
add_specialty("ent.json",
    "گوش", "بینی", "گلو", "حلق", "ent", "nose", "throat", "أنف", "أذن", "حنجرة", "سینوس")
add_specialty("orthopedics.json",
    "ارتوپدی", "استخوان", "مفصل", "ortho", "bone", "joint", "عظام", "عظمي", "مفاصل", "زانو", "کمر")
add_specialty("gynecology.json",
    "زنان", "زایمان", "نازایی", "ivf", "gyneco", "obgyn", "نساء", "ولادة", "توليد", "ناباروری", "بارداری")
add_specialty("pediatrics.json",
    "کودک", "اطفال", "نوزاد", "pediatric", "child", "أطفال", "طفل", "رضع")
add_specialty("psychiatry.json",
    "روان", "روانپزشک", "روان‌پزشکی", "اعصاب و روان", "psych", "mental", "نفسي", "طب نفسي", "افسردگی", "اضطراب")
add_specialty("internal_medicine.json",
    "داخلی", "internal", "باطنی", "باطنية", "general medicine", "طب داخلی")
add_specialty("urology.json",
    "اورولوژی", "کلیه", "مثانه", "urology", "urinary", "مسالك", "كلى", "مثانة", "پروستات", "prostate")
add_specialty("general_surgery.json",
    "جراح عمومی", "جراحی عمومی", "general surgery", "جراحة عامة", "جراح", "surgery")
add_specialty("rhinoplasty.json",
    "رینوپلاستی", "جراحی بینی", "rhino", "nose surgery", "تجميل الأنف", "عملية الأنف", "بینی")
add_specialty("gastroenterology.json",
    "گوارش", "معده", "روده", "کبد", "gastro", "digestive", "هضمي", "معدة", "أمعاء", "كبد", "کولون", "آندوسکوپی")
add_specialty("emergency_medicine.json",
    "اورژانس", "فوریت", "emergency", "طوارئ", "إسعاف", "طب اورژانس")
add_specialty("traditional_medicine.json",
    "طب سنتی", "سنتی", "گیاهی", "traditional", "herbal", "طب تقليدي", "أعشاب", "حجامت")
add_specialty("pharmacies.json",
    "داروخانه", "دارو", "pharmacy", "drugstore", "صيدلية", "صيدليه", "دواء", "أدوية")
add_specialty("allergy.json",
    "آلرژی", "حساسیت", "allergy", "aller", "حساسية", "تحسس")
add_specialty("hematology_oncology.json",
    "خون", "آنکولوژی", "سرطان", "hematology", "oncology", "cancer", "دم", "أورام", "سرطان", "كدمات")
add_specialty("endocrinology.json",
    "غدد", "تیروئید", "دیابت", "قند", "endocrinology", "غدة", "سكري", "درقية", "هرمون", "هورمون")
add_specialty("neurosurgery.json",
    "مغز و اعصاب", "جراحی مغز", "نوروسرجری", "neurosurgery", "neurology", "نورولوژی", "دماغ", "أعصاب", "دماغي", "صرع", "ام اس", "ms")

# ============================================================
#  NON MEDICAL MAP
# ============================================================
NON_MEDICAL_MAP = {
    "hospitals.json": ["بیمارستان", "hospital", "مستشفى", "مستشفيات", "كلينيك", "کلینیک", "clinic"],
    "hotels.json": ["هتل", "hotel", "فندق", "فنادق", "اقامتگاه", "خوابگاه"],
    "motels.json": ["مهمان‌پذیر", "مهمان پذیر", "مسافرخانه", "motel", "نُزل", "نزل", "بيت ضيافة"],
    "tourist_houses.json": ["خانه مسافر", "اقامتگاه بومگردی", "منزل مبله", "tourist house", "guest house", "بيت مسافر", "دار ضيافة"],
    "leisure_city.json": ["جاذبه", "داخل شهر", "حافظیه", "سعدیه", "ارگ", "نصیرالملک", "شاهچراغ", "باغ ارم", "بازار وکیل", "شیراز گردی", "دیدنی", "موزه", "مسجد", "attraction", "hafez", "saadi"],
    "leisure_outside.json": ["تخت جمشید", "پاسارگاد", "نقش رستم", "آبشار", "بیرون شهر", "persepolis", "pasargad", "naqsh-e rostam", "تخت جمشيد"],
    "transport.json": ["حمل‌ونقل", "مترو", "تاکسی", "اتوبوس", "اسنپ", "تپسی", "فرودگاه", "راه‌آهن", "transport", "metro", "taxi", "bus", "snapp", "airport", "مواصلات", "نقل", "مطار", "قطار", "سفر"],
    "support.json": ["پشتیبانی", "هلال احمر", "شماره اضطراری", "support", "کمک", "دعم", "مساعدة", "إسعاف", "help"],
    "complaints.json": ["شکایت", "شکایات", "complaint", "گله", "شكوى", "شكاوى", "انتقاد"],
    "patient_guide.json": ["راهنمای بیمار", "پذیرش بیمار خارجی", "ویزای درمانی", "patient guide", "medical visa", "قبول مريض", "تأشيرة طبية", "دليل المريض", "پذیرش", "ترخیص"],
}

CONTEXT_WORDS = [
    "بیمارستان", "hospital", "مستشفى", "شیراز", "shiraz", "شيراز",
    "doctor", "دکتر", "طبيب", "طبیب", "dr", "دكتر"
]

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

# ============ HELPERS ============
def clean(text):
    return text.strip().lower().strip(" .!؟?،,")

def pick_language(text):
    t = clean(text)
    if t in ("1", "۱") or "فارسی" in t or "persian" in t or "farsi" in t: return "fa"
    if t in ("2", "۲") or "عرب" in t or "arab" in t: return "ar"
    if t in ("3", "۳") or "english" in t or "انگلیس" in t: return "en"
    return None

def english_words(text):
    return re.findall(r"[a-z]+", text.lower())

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
    key_lang = f"{key}_{lang}"
    if key_lang in item:
        return item[key_lang]
    if f"{key}_fa" in item:
        return item[f"{key}_fa"]
    if key in item:
        return item[key]
    return None

def item_name_for_search(item):
    for k in ("name_fa", "name_ar", "name_en", "name"):
        if k in item:
            return str(item[k])
    return ""

# ============ LANGUAGE DETECTION ============
def detect_text_language(text):
    text = text.strip()
    if not text:
        return None
    has_latin = bool(re.search(r'[a-zA-Z]', text))
    has_arabic_range = bool(re.search(r'[\u0600-\u06FF]', text))
    if has_latin and not has_arabic_range:
        return "en"
    if re.search(r'[پچژگ]', text):
        return "fa"
    if re.search(r'[يكةىأإآؤئ]', text):
        return "ar"
    if has_arabic_range:
        normalized = text.replace('\u200c', ' ').replace('\u200f', ' ').replace('\u200e', ' ')
        normalized = re.sub(r'[\u064B-\u0652]', '', normalized)
        words_list = re.findall(r'[\u0600-\u06FF]+', normalized)
        words_set = set(w.replace('\u200c', '').lower() for w in words_list)
        persian_markers = {
            "دنبال", "میگردم", "میخوام", "میخواهم", "هستم", "دارید", "دارم", "داریم",
            "نیاز", "لطفا", "لطفاً", "کجا", "چطور", "چگونه", "چرا", "چیه",
            "چند", "چقدر", "کدام", "کدوم", "چی", "چه", "آیا", "میشه", "میشود",
            "سلام", "ممنون", "مرسی", "خواهش", "ببخشید",
            "بیمار", "متخصص", "دکتر", "بیمارستان", "پزشک", "درمان", "ویزیت", "نوبت",
            "اقامت", "هتل", "مسافرخانه", "بلیط", "تور", "سفر", "جاذبه", "گردش",
            "شیراز", "فارسی", "خوب", "بله", "نه", "الان", "امروز", "فردا", "دیروز",
            "بیمه", "قیمت", "هزینه", "پول", "پرداخت", "کلینیک",
            "میکنم", "میکنید", "بگرد", "پیدا", "بهترین", "وقت"
        }
        arabic_markers = {
            "هل", "هناك", "أريد", "أحتاج", "أبحث", "أستطيع", "لدي", "عندي",
            "نحن", "أنتم", "أنا", "أنت", "يمكن",
            "أين", "متى", "لماذا", "كيف", "ما", "ماذا", "كم", "بكم", "أي",
            "مرحبا", "أهلا", "شكرا", "عفوا", "السلام",
            "مستشفى", "طبيب", "دكتور", "صيدلية", "مرض", "علاج", "دواء",
            "فندق", "نزل", "حجز", "سيارة", "مطار", "رحلة", "سياحة",
            "شيراز", "العربية", "جيد", "نعم", "لا", "الآن", "اليوم",
            "غدا", "أمس", "تأمين", "سعر", "تكلفة", "مال", "دفع", "أفضل", "قريب", "موعد"
        }
        persian_score = sum(1 for w in words_set if w in persian_markers)
        arabic_score = sum(1 for w in words_set if w in arabic_markers)
        if arabic_score > persian_score:
            return "ar"
        elif persian_score > arabic_score:
            return "fa"
    return None

# ============ DATE HELPERS ============
def gregorian_to_shamsi(g_y, g_m, g_d):
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy = g_y - 1600
    gm = g_m - 1
    gd = g_d - 1
    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm):
        g_day_no += g_days_in_month[i]
    if gm > 1 and ((g_y % 4 == 0 and g_y % 100 != 0) or (g_y % 400 == 0)):
        g_day_no += 1
    g_day_no += gd
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    i = 0
    for i in range(11):
        if j_day_no < j_days_in_month[i]:
            break
        j_day_no -= j_days_in_month[i]
    jm = i + 1
    jd = j_day_no + 1
    return jy, jm, jd

def format_date_full(offset_days=0, lang="fa"):
    today = datetime.now() + timedelta(days=offset_days)
    miladi = today.strftime("%Y/%m/%d")
    try:
        jy, jm, jd = gregorian_to_shamsi(today.year, today.month, today.day)
        shamsi = f"{jy}/{jm:02d}/{jd:02d}"
    except:
        shamsi = "—"
    if lang == "en":
        return f"{miladi} (Shamsi: {shamsi})"
    if lang == "ar":
        return f"{miladi} م  |  {shamsi} ش"
    return f"{shamsi} ش  |  {miladi} م"
# ============ APPOINTMENTS ============
APPOINTMENTS_FILE = "data/appointments.json"

def load_appointments():
    try:
        with open(APPOINTMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"next_id": 1001, "appointments": []}

def save_appointments(data):
    try:
        with open(APPOINTMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def create_appointment(doctor, patient_name, patient_phone, chat_id, lang, date_str, time_str):
    data = load_appointments()
    apt_id = f"APT-{data['next_id']}"
    data['next_id'] += 1
    appointment = {
        "id": apt_id,
        "doctor_id": doctor.get('id', ''),
        "doctor_name_fa": doctor.get('name_fa', ''),
        "doctor_name_ar": doctor.get('name_ar', ''),
        "doctor_name_en": doctor.get('name_en', ''),
        "doctor_phone": doctor.get('phone', ''),
        "doctor_address_fa": doctor.get('office_address_fa', ''),
        "doctor_address_ar": doctor.get('office_address_ar', ''),
        "doctor_address_en": doctor.get('office_address_en', ''),
        "patient_name": patient_name,
        "patient_phone": patient_phone,
        "patient_chat_id": str(chat_id),
        "patient_lang": lang,
        "date": date_str,
        "time": time_str,
        "status": "confirmed",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
    }
    data['appointments'].append(appointment)
    save_appointments(data)
    return appointment

def get_patient_appointments(chat_id):
    data = load_appointments()
    return [a for a in data['appointments'] if a['patient_chat_id'] == str(chat_id)]

# ============ SEARCH: DOCTOR BY NAME ============
def search_by_doctor_name(text):
    low = text.lower()
    search_text = low
    for w in ["دکتر", "doctor", "دكتور", "دكتورة", "طبيب", "طبیب", "dr"]:
        search_text = search_text.replace(w, "")
    search_text = search_text.strip()
    if not search_text or len(search_text) < 3:
        return None
    for filename in set(SPECIALTY_MAP.values()):
        path = "data/doctors/" + filename
        data = load_json(path)
        if not data:
            continue
        for item in data:
            name = item_name_for_search(item).lower()
            if search_text in name or name in search_text:
                return item
    return None

# ============ SEARCH: SPECIALTY ============
def search_specialty(text):
    low = text.lower()
    words = english_words(text)
    scores = {}
    for k, fn in SPECIALTY_MAP.items():
        matched = False
        if k.isascii():
            if k in words or (k + "s") in words:
                matched = True
        else:
            if k in low:
                matched = True
        if matched:
            if fn not in scores:
                scores[fn] = 0
            weight = len(k)
            if k in [cw.lower() for cw in CONTEXT_WORDS]:
                weight = weight * 0.3
            scores[fn] += weight
    if not scores:
        return None
    best_fn = max(scores, key=scores.get)
    data = load_json("data/doctors/" + best_fn)
    if not data:
        return None
    def score(x):
        r = x.get('ratings', {})
        if isinstance(r, dict) and 'patient_satisfaction_score' in r:
            return r['patient_satisfaction_score']
        return x.get('patient_satisfaction_score', 0)
    try:
        data.sort(key=score, reverse=True)
    except:
        pass
    return data

# ============ SEARCH: NON-MEDICAL ============
def search_non_medical(text):
    low = text.lower()
    words = english_words(text)
    scores = {}
    for fn, keywords in NON_MEDICAL_MAP.items():
        score = 0
        for kw in keywords:
            kw_low = kw.lower()
            matched = False
            if kw_low.isascii():
                if kw_low in words or (kw_low + "s") in words:
                    matched = True
            else:
                if kw_low in low:
                    matched = True
            if matched:
                weight = len(kw_low)
                if kw_low in [cw.lower() for cw in CONTEXT_WORDS]:
                    weight = weight * 0.3
                score += weight
        if score > 0:
            scores[fn] = score
    if not scores:
        return None
    return max(scores, key=scores.get)

# ============ HELPERS ============
def is_all_request(text):
    low = text.lower()
    for w in ALL_WORDS:
        if w in low:
            return True
    return False

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
    hospitals = get_value(doc, 'surgeries_done_at', lang) or get_value(doc, 'hospitals', lang) or []
    if isinstance(hospitals, str):
        hospitals = [hospitals]
    h = "، ".join(str(x) for x in hospitals)
    pr = get_value(doc, 'price_range_toman', lang) or ''
    r = doc.get('patient_satisfaction_score', '')
    if not r:
        ratings = doc.get('ratings', {}) if isinstance(doc.get('ratings'), dict) else {}
        r = ratings.get('patient_satisfaction_score', '')
    if lang == "en":
        return f"Doctor: {n}\nSpecialty: {s}\nAddress: {a}\nHospitals: {h}\nPhone: {p}\nPrice: {pr}\nRating: {r}/5"
    if lang == "ar":
        return f"الطبيب: {n}\nالتخصص: {s}\nالعنوان: {a}\nالمستشفيات: {h}\nالهاتف: {p}\nالتكلفة: {pr}\nالتقييم: {r}/5"
    return f"دکتر: {n}\nتخصص: {s}\nآدرس: {a}\nبیمارستان: {h}\nتلفن: {p}\nقیمت: {pr}\nامتیاز: {r}/5"

def format_generic(item, lang):
    if not isinstance(item, dict):
        return str(item)
    field_names = FIELD_NAMES.get(lang, {})
    lines = []
    seen_keys = set()
    for k, v in item.items():
        if k == 'id':
            continue
        if any(k.endswith(f"_{l}") for l in ("fa", "ar", "en") if l != lang):
            base_key = None
            for l in ("fa", "ar", "en"):
                if k.endswith(f"_{l}"):
                    base_key = k[:-3]
                    break
            if base_key and base_key in seen_keys:
                continue
        display_key = k
        if k.endswith("_fa") or k.endswith("_ar") or k.endswith("_en"):
            base_key = k[:-3]
            if base_key in seen_keys:
                continue
            priority = [lang, "fa", "en", "ar"]
            value = None
            for p in priority:
                pk = f"{base_key}_{p}"
                if pk in item:
                    value = item[pk]
                    break
            if value is None:
                continue
            display_key = base_key
            seen_keys.add(base_key)
        else:
            if k in seen_keys:
                continue
            value = v
            seen_keys.add(k)
        label = field_names.get(display_key, display_key)
        if isinstance(value, list):
            value = "، ".join(str(x) for x in value)
        elif isinstance(value, dict):
            parts = []
            for kk, vv in value.items():
                if isinstance(vv, list):
                    vv = "، ".join(str(x) for x in vv)
                parts.append(f"{kk}: {vv}")
            value = "، ".join(parts)
        if value and str(value).strip() and str(value) != 'None':
            lines.append(f"{label}: {value}")
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
        username = message.from_user.username or ""
        full = (fn + " " + ln).strip()
        if not full:
            full = username if username else "ناشناس"
        return full
    except:
        return "ناشناس"

# ============ QUERY PROCESSOR ============
def process_query(message, text, lang):
    cid = message.chat.id
    # ۱. جستجو با نام پزشک
    doc = search_by_doctor_name(text)
    if doc:
        bot.reply_to(message, format_doctor(doc, lang))
        user_temp[cid] = {"doctor": doc}
        user_state[cid] = "awaiting_apt_choice"
        bot.reply_to(message, MSG[lang]["apt_ask"])
        return True
    # ۲. جستجو تخصص
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
                name = d.get(f"name_{lang}") or d.get('name_fa', '')
                lines.append(f"{i}. {name}")
            lines.append(MSG[lang]["apt_pick_footer"])
            bot.reply_to(message, "\n".join(lines))
        return True
    # ۳. جستجوی غیرپزشکی
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
    # ۴. AI fallback
    ai = get_ai(text, lang)
    if ai:
        bot.reply_to(message, ai)
        return True
    return False

# ============ META INFO ============
def get_meta_info():
    try:
        with open("data/meta.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# ============ HANDLERS ============
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    meta = get_meta_info()
    if not meta:
        bot.reply_to(message, "❌ فایل meta.json پیدا نشد.")
        return
    last_update = meta.get("last_update", "نامشخص")
    next_update = meta.get("next_update", "نامشخص")
    lines = [f"📊 وضعیت آپدیت:\n\nآخرین آپدیت: {last_update}\nآپدیت بعدی: {next_update}\n"]
    files = meta.get("files", {})
    if files:
        lines.append(f"\n📁 تعداد فایل‌ها: {len(files)}")
    lines.append(f"\n📈 آمار نظرسنجی این دوره:")
    lines.append(f"رضایت: {satisfaction_counter['positive']}")
    lines.append(f"عدم رضایت: {satisfaction_counter['negative']}")
    apt_data = load_appointments()
    lines.append(f"\n📅 کل نوبت‌های ثبت‌شده: {len(apt_data['appointments'])}")
    bot.reply_to(message, "\n".join(lines))

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
        doc_name = a.get(f"doctor_name_{lang}") or a.get("doctor_name_fa", "")
        lines.append(f"\n📋 {a['id']}\n👨‍⚕️ {doc_name}\n📅 {a['date']} — ⏰ {a['time']}")
    bot.reply_to(message, "\n".join(lines))

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

    # ===== انتخاب زبان =====
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

    # ===== تعویض خودکار زبان (فقط توی active) =====
    if cid in user_lang and state == "active":
        detected = detect_text_language(text)
        if detected and detected != user_lang.get(cid):
            user_lang[cid] = detected

    lang = user_lang.get(cid, "fa")
    t = clean(text)
    user_name = get_user_name(message)

    # ===== awaiting_apt_pick =====
    if state == "awaiting_apt_pick":
        pick_map = {"1": 0, "۱": 0, "یک": 0, "2": 1, "۲": 1, "دو": 1, "3": 2, "۳": 2, "سه": 2}
        if t in pick_map:
            idx = pick_map[t]
            doctors = user_temp.get(cid, {}).get("doctors", [])
            if idx < len(doctors):
                user_temp[cid] = {"doctor": doctors[idx]}
                user_state[cid] = "awaiting_apt_choice"
                bot.reply_to(message, MSG[lang]["apt_ask"])
                return
        user_state[cid] = "active"

    # ===== awaiting_apt_choice =====
    if state == "awaiting_apt_choice":
        if t in ("1", "۱", "یک"):
            user_state[cid] = "awaiting_apt_date"
            bot.reply_to(message, MSG[lang]["apt_date"])
            return
        if t in ("2", "۲", "دو"):
            doctor = user_temp.get(cid, {}).get("doctor", {})
            phone = doctor.get("phone", "")
            user_state[cid] = "active"
            bot.reply_to(message, f"📞 {phone}")
            ask_more(message)
            return
        user_state[cid] = "active"

    # ===== awaiting_apt_date =====
    elif state == "awaiting_apt_date":
        if t in ("1", "۱", "یک"):
            offset = 0
        elif t in ("2", "۲", "دو"):
            offset = 1
        elif t in ("3", "۳", "سه"):
            offset = 2
        elif t in ("4", "۴", "چهار"):
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            ask_more(message)
            return
        else:
            bot.reply_to(message, MSG[lang]["apt_invalid"])
            return
        date_str = format_date_full(offset, lang)
        if cid not in user_temp:
            user_temp[cid] = {}
        user_temp[cid]["date"] = date_str
        user_state[cid] = "awaiting_apt_time"
        bot.reply_to(message, MSG[lang]["apt_time"])
        return

    # ===== awaiting_apt_time =====
    elif state == "awaiting_apt_time":
        times = {"1": "10:00", "2": "12:00", "3": "16:00", "4": "18:00", "5": "20:00",
                 "۱": "10:00", "۲": "12:00", "۳": "16:00", "۴": "18:00", "۵": "20:00"}
        if t in ("6", "۶"):
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            ask_more(message)
            return
        if t not in times:
            bot.reply_to(message, MSG[lang]["apt_invalid"])
            return
        user_temp[cid]["time"] = times[t]
        user_state[cid] = "awaiting_apt_name"
        bot.reply_to(message, MSG[lang]["apt_name"])
        return

    # ===== awaiting_apt_name =====
    elif state == "awaiting_apt_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG[lang]["apt_name"])
            return
        user_temp[cid]["name"] = text.strip()
        user_state[cid] = "awaiting_apt_phone"
        bot.reply_to(message, MSG[lang]["apt_phone"])
        return

    # ===== awaiting_apt_phone =====
    elif state == "awaiting_apt_phone":
        phone = re.sub(r'[^0-9+]', '', text.strip())
        if len(phone) < 8:
            bot.reply_to(message, MSG[lang]["apt_phone"])
            return
        user_temp[cid]["phone"] = phone
        user_state[cid] = "awaiting_apt_confirm"
        bot.reply_to(message, MSG[lang]["apt_confirm_final"].format(
            name=user_temp[cid].get("name", ""),
            phone=phone,
            date=user_temp[cid].get("date", ""),
            time=user_temp[cid].get("time", "")
        ))
        return

    # ===== awaiting_apt_confirm =====
    elif state == "awaiting_apt_confirm":
        if t in YES_WORDS:
            doctor = user_temp.get(cid, {}).get("doctor", {})
            patient_name = user_temp.get(cid, {}).get("name", "")
            patient_phone = user_temp.get(cid, {}).get("phone", "")
            date_str = user_temp.get(cid, {}).get("date", "")
            time_str = user_temp.get(cid, {}).get("time", "")
            try:
                apt = create_appointment(doctor, patient_name, patient_phone, cid, lang, date_str, time_str)
                doc_name = doctor.get(f"name_{lang}") or doctor.get("name_fa", "")
                address = doctor.get(f"office_address_{lang}") or doctor.get("office_address_fa", "")
                msg = MSG[lang]["apt_confirmed"].format(
                    id=apt['id'], doctor=doc_name, date=date_str,
                    time=time_str, address=address
                )
                bot.reply_to(message, msg)
                if ADMIN_CHAT_ID:
                    try:
                        bot.send_message(ADMIN_CHAT_ID,
                            f"📅 نوبت جدید\nکد: {apt['id']}\nبیمار: {patient_name}\nتلفن: {patient_phone}\nپزشک: {doc_name}\nتاریخ: {date_str}\nساعت: {time_str}\nChatID: {cid}")
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

    # ===== awaiting_more =====
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

    # ===== awaiting_rating =====
    elif state == "awaiting_rating":
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

    # ===== awaiting_feedback =====
    elif state == "awaiting_feedback":
        user_state[cid] = "active"
        bot.reply_to(message, MSG[lang]["thanks_fb"])
        satisfaction_counter["count"] += 1
        satisfaction_counter["negative"] += 1
        if ADMIN_CHAT_ID:
            try:
                msg = f"❌ عدم رضایت\nزبان: {LANG_NAMES.get(lang, lang)}\nنام: {user_name}\nChatID: <code>{cid}</code>\nمتن: {text}"
                bot.send_message(ADMIN_CHAT_ID, msg, parse_mode="HTML")
            except:
                pass
        return

    # ===== Emergency =====
    if any(k in text.lower() for ks in EMERGENCY.values() for k in ks):
        bot.reply_to(message, EMERGENCY_RESP[lang])
        ask_more(message)
        return

    # ===== پردازش عادی =====
old_state = user_state.get(cid)
answered = process_query(message, text, lang)
new_state = user_state.get(cid)
if new_state != old_state:
 return 
if not answered:
    bot.reply_to(message, MSG[lang]["retry"])
ask_more(message)

# ============ START ============
print("ربات روشن شد... v20 (نوبت‌گیری چند پزشکی + تاریخ شمسی/میلادی)")
bot.polling()