import json, os, re, telebot, requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AVALAI_API_KEY = os.environ.get("AVALAI_API_KEY", "")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "")
AI_MODEL = "gpt-4o-mini"
AVALAI_URL = "https://api.avalai.ir/v1/chat/completions"

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
    },
}

FIELD_NAMES = {
    "fa": {
        "name": "نام", "category": "دسته", "star_rating": "ستاره", "quality_grade": "کیفیت",
        "address": "آدرس", "district": "منطقه", "phone": "تلفن", "amenities": "امکانات",
        "distance_to_major_hospitals": "فاصله تا بیمارستان‌ها", "distance_to_city_center": "فاصله تا مرکز شهر",
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
        "name_fa": "نام (فارسی)", "name_en": "نام (انگلیسی)",
        "medical_visa_documents": "مدارک ویزای درمانی",
    },
    "ar": {
        "name": "الاسم", "category": "الفئة", "star_rating": "التصنيف", "quality_grade": "الجودة",
        "address": "العنوان", "district": "المنطقة", "phone": "الهاتف", "amenities": "المرافق",
        "distance_to_major_hospitals": "المسافة إلى المستشفيات", "distance_to_city_center": "المسافة إلى وسط المدينة",
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
        "name_fa": "الاسم (الفارسية)", "name_en": "الاسم (الإنجليزية)",
    },
    "en": {
        "name": "Name", "category": "Category", "star_rating": "Star Rating", "quality_grade": "Quality Grade",
        "address": "Address", "district": "District", "phone": "Phone", "amenities": "Amenities",
        "distance_to_major_hospitals": "Distance to Hospitals", "distance_to_city_center": "Distance to City Center",
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
        "name_fa": "Name (Persian)", "name_en": "Name (English)",
    },
}

YES_WORDS = {"بله", "بلی", "آره", "اره", "yes", "yeah", "y", "نعم", "ايوه", "أيوه"}
NO_WORDS = {"نه", "نخیر", "خیر", "نه ممنون", "نه، ممنون", "نه مرسی", "سوالی ندارم", "سؤالی ندارم", "ندارم", "no", "nope", "n", "no thanks", "لا", "لا شكرا", "لا شكراً"}

SPECIALTY_MAP = {}

def add_specialty(filename, *words):
    for w in words:
        SPECIALTY_MAP[w] = filename

add_specialty("cardiology.json", "قلب", "cardio", "heart")
add_specialty("dermatology.json", "پوست", "derma", "skin")
add_specialty("dentistry.json", "دندان", "dental", "dentist")
add_specialty("kids_dentistry.json", "دندان کودکان", "دندانپزشکی کودکان", "kids dental")
add_specialty("ophthalmology.json", "چشم", "eye")
add_specialty("ent.json", "گوش", "بینی", "nose", "ent")
add_specialty("orthopedics.json", "ارتوپدی", "ortho", "bone")
add_specialty("gynecology.json", "زنان", "نازایی", "ivf")
add_specialty("pediatrics.json", "کودک", "اطفال", "pediatric")
add_specialty("psychiatry.json", "روان", "psych")
add_specialty("internal_medicine.json", "داخلی", "internal")
add_specialty("urology.json", "اورولوژی", "urology")
add_specialty("general_surgery.json", "جراح", "surgery")
add_specialty("rhinoplasty.json", "رینوپلاستی", "rhino")
add_specialty("gastroenterology.json", "گوارش", "معده", "gastro", "کبد", "روده")
add_specialty("emergency_medicine.json", "اورژانس", "emergency", "طب اورژانس")
add_specialty("traditional_medicine.json", "طب سنتی", "traditional", "گیاهی")
add_specialty("pharmacies.json", "داروخانه", "دارو", "pharmacy")
add_specialty("allergy.json", "آلرژی", "allergy", "حساسیت")
add_specialty("hematology_oncology.json", "خون", "آنکولوژی", "سرطان", "hematology", "oncology")
add_specialty("endocrinology.json", "غدد", "تیروئید", "دیابت", "endocrinology")
add_specialty("neurosurgery.json", "مغز و اعصاب", "جراحی مغز", "neurosurgery", "نورولوژی")

NON_MEDICAL_MAP = {
    "hospitals.json": ["بیمارستان", "hospital", "مستشفى"],
    "hotels.json": ["هتل", "hotel", "فندق"],
    "motels.json": ["مهمان‌پذیر", "مهمان پذیر", "مسافرخانه", "motel"],
    "tourist_houses.json": ["خانه مسافر", "اقامتگاه", "منزل مبله", "tourist house"],
    "leisure_city.json": ["جاذبه", "داخل شهر", "حافظیه", "سعدیه", "ارگ", "نصیرالملک", "شاهچراغ", "باغ ارم", "بازار وکیل"],
    "leisure_outside.json": ["تخت جمشید", "پاسارگاد", "نقش رستم", "آبشار", "بیرون شهر", "persepolis", "pasargad"],
    "transport.json": ["حمل‌ونقل", "مترو", "تاکسی", "اتوبوس", "اسنپ", "تپسی", "فرودگاه", "راه‌آهن", "transport", "metro", "taxi"],
    "support.json": ["پشتیبانی", "هلال احمر", "شماره اضطراری", "support"],
    "complaints.json": ["شکایت", "شکایات", "complaint"],
    "patient_guide.json": ["راهنمای بیمار", "پذیرش بیمار خارجی", "ویزای درمانی", "patient guide", "medical visa", "قبول مريض"],
}

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

user_state = {}
user_lang = {}

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

def search_specialty(text):
    low = text.lower()
    words = english_words(text)
    for k, fn in SPECIALTY_MAP.items():
        if k.isascii():
            found = k in words or (k + "s") in words
        else:
            found = k in low
        if found:
            data = load_json("data/doctors/" + fn)
            if data:
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
    return None

def search_non_medical(text):
    low = text.lower()
    for fn, keywords in NON_MEDICAL_MAP.items():
        for kw in keywords:
            if kw.lower() in low:
                return fn
    return None

def translate_value(v, lang):
    """ترجمه‌ی برخی مقادیر خاص به زبان انتخابی"""
    if not isinstance(v, str):
        return v
    translations = {
        "fa": {
            "هتل": "هتل", "مهمان‌پذیر": "مهمان‌پذیر", "خانه مسافر": "خانه مسافر",
            "۵ ستاره": "۵ ستاره", "۴ ستاره": "۴ ستاره", "۳ ستاره": "۳ ستاره", "۲ ستاره": "۲ ستاره", "۱ ستاره": "۱ ستاره",
            "ممتاز": "ممتاز", "درجه یک": "درجه یک", "درجه دو": "درجه دو", "خوب": "خوب", "متوسط": "متوسط", "اقتصادی": "اقتصادی",
            "بله": "بله", "خیر": "خیر",
            "تاریخی": "تاریخی", "طبیعی": "طبیعی", "فرهنگی و تاریخی": "فرهنگی و تاریخی",
            "مذهبی و تاریخی": "مذهبی و تاریخی", "تاریخی و تفریحی": "تاریخی و تفریحی",
            "داخل شهر": "داخل شهر", "خارج شهر": "خارج شهر",
            "معتدل": "معتدل", "نیمه‌خشک": "نیمه‌خشک", "کوهستانی": "کوهستانی",
            "فارس": "فارس", "لر": "لر", "قشقایی": "قشقایی", "فارس و لر": "فارس و لر",
            "مترو": "مترو", "اتوبوس": "اتوبوس", "تاکسی": "تاکسی", "تاکسی اینترنتی": "تاکسی اینترنتی",
            "آژانس": "آژانس", "فرودگاه": "فرودگاه", "راه‌آهن": "راه‌آهن", "ون بیمارستانی": "ون بیمارستانی",
        },
        "ar": {
            "هتل": "فندق", "مهمان‌پذیر": "بيت ضيافة", "خانه مسافر": "بيت مسافر",
            "۵ ستاره": "٥ نجوم", "۴ ستاره": "٤ نجوم", "۳ ستاره": "٣ نجوم", "۲ ستاره": "٢ نجوم", "۱ ستاره": "١ نجمة",
            "ممتاز": "ممتاز", "درجه یک": "درجة أولى", "درجه دو": "درجة ثانية", "خوب": "جيد", "متوسط": "متوسط", "اقتصادی": "اقتصادي",
            "بله": "نعم", "خیر": "لا",
            "تاریخی": "تاريخي", "طبیعی": "طبيعي", "فرهنگی و تاریخی": "ثقافي وتاريخي",
            "مذهبی و تاریخی": "ديني وتاريخي", "تاریخی و تفریحی": "تاريخي وترفيهي",
            "داخل شهر": "داخل المدينة", "خارج شهر": "خارج المدينة",
            "معتدل": "معتدل", "نیمه‌خشک": "شبه جاف", "کوهستانی": "جبلي",
            "فارس": "فارس", "لر": "لر", "قشقایی": "قشقايي", "فارس و لر": "فارس ولر",
            "مترو": "مترو", "اتوبوس": "حافلة", "تاکسی": "تاكسي", "تاکسی اینترنتی": "تاكسي عبر الإنترنت",
            "آژانس": "وكالة", "فرودگاه": "مطار", "راه‌آهن": "سكة حديد", "ون بیمارستانی": "فان المستشفى",
        },
        "en": {
            "هتل": "Hotel", "مهمان‌پذیر": "Guesthouse", "خانه مسافر": "Tourist House",
            "۵ ستاره": "5 Star", "۴ ستاره": "4 Star", "۳ ستاره": "3 Star", "۲ ستاره": "2 Star", "۱ ستاره": "1 Star",
            "ممتاز": "Excellent", "درجه یک": "First Class", "درجه دو": "Second Class", "خوب": "Good", "متوسط": "Average", "اقتصادی": "Economy",
            "بله": "Yes", "خیر": "No",
            "تاریخی": "Historical", "طبیعی": "Natural", "فرهنگی و تاریخی": "Cultural & Historical",
            "مذهبی و تاریخی": "Religious & Historical", "تاریخی و تفریحی": "Historical & Recreational",
            "داخل شهر": "In City", "خارج شهر": "Out of City",
            "معتدل": "Moderate", "نیمه‌خشک": "Semi-Arid", "کوهستانی": "Mountainous",
            "فارس": "Fars", "لر": "Lur", "قشقایی": "Qashqai", "فارس و لر": "Fars & Lur",
            "مترو": "Metro", "اتوبوس": "Bus", "تاکسی": "Taxi", "تاکسی اینترنتی": "Online Taxi",
            "آژانس": "Agency", "فرودگاه": "Airport", "راه‌آهن": "Railway", "ون بیمارستانی": "Hospital Van",
        },
    }
    lang_trans = translations.get(lang, {})
    return lang_trans.get(v, v)

def format_doctor(doc, lang):
    n = doc.get('name', '')
    s = doc.get('specialty', '')
    contact = doc.get('contact', {}) if isinstance(doc.get('contact'), dict) else {}
    service = doc.get('service_details', {}) if isinstance(doc.get('service_details'), dict) else {}
    ratings = doc.get('ratings', {}) if isinstance(doc.get('ratings'), dict) else {}
    p = contact.get('phone') or doc.get('phone', '')
    a = contact.get('office_address') or doc.get('office_address', '')
    hospitals = service.get('hospitals') or doc.get('surgeries_done_at') or doc.get('hospitals') or []
    if isinstance(hospitals, str):
        hospitals = [hospitals]
    h = "، ".join(hospitals)
    pr = service.get('price_range_toman') or doc.get('price_range_toman', '')
    r = ratings.get('patient_satisfaction_score') or doc.get('patient_satisfaction_score', '')

    if lang == "en":
        return f"Doctor: {n}\nSpecialty: {s}\nAddress: {a}\nHospitals: {h}\nPhone: {p}\nPrice: {pr}\nRating: {r}/5"
    if lang == "ar":
        return f"الطبيب: {n}\nالتخصص: {s}\nالعنوان: {a}\nالمستشفيات: {h}\nالهاتف: {p}\nالتكلفة: {pr}\nالتقييم: {r}/5"
    return f"دکتر: {n}\nتخصص: {s}\nآدرس: {a}\nبیمارستان: {h}\nتلفن: {p}\nقیمت: {pr}\nامتیاز: {r}/5"

def format_generic(item, lang):
    lines = []
    field_names = FIELD_NAMES.get(lang, {})
    for k, v in item.items():
        if k in ('id',):
            continue
        label = field_names.get(k, k)
        if isinstance(v, list):
            translated = [translate_value(str(x), lang) for x in v]
            v = "، ".join(translated)
        elif isinstance(v, dict):
            parts = []
            for kk, vv in v.items():
                if isinstance(vv, list):
                    vv = "، ".join(str(x) for x in vv)
                parts.append(f"{kk}: {vv}")
            v = "، ".join(parts)
        elif isinstance(v, str):
            v = translate_value(v, lang)
        if v and str(v).strip() and str(v) != 'None':
            lines.append(f"{label}: {v}")
    return "\n".join(lines)

def get_ai(text, lang):
    prompt = SYSTEM_PROMPT + " پاسخ را به زبان " + LANG_NAMES[lang] + " بنویس."
    try:
        r = requests.post(AVALAI_URL,
            headers={"Authorization": "Bearer " + AVALAI_API_KEY, "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]},
            timeout=15)
        return r.json()['choices'][0]['message']['content']
    except: return None

def ask_more(message):
    cid = message.chat.id
    user_state[cid] = "awaiting_more"
    bot.reply_to(message, MSG[user_lang.get(cid, "fa")]["more"])

def process_query(message, text, lang):
    docs = search_specialty(text)
    if docs:
        words = english_words(text)
        if "همه" in text or "all" in words or "كل" in text: limit = len(docs)
        elif "بهترین" in text or "best" in words or "أفضل" in text: limit = 1
        else: limit = 3
        for d in docs[:limit]:
            bot.reply_to(message, format_doctor(d, lang))
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

@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.chat.id] = "choose_lang"
    bot.reply_to(message, START_MSG)

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

    elif state == "awaiting_rating":
        if t in YES_WORDS:
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["thanks"])
            return
        if t in NO_WORDS:
            user_state[cid] = "awaiting_feedback"
            bot.reply_to(message, MSG[lang]["why"])
            return
        user_state[cid] = "active"

    elif state == "awaiting_feedback":
        print("FEEDBACK:", text)
        user_state[cid] = "active"
        bot.reply_to(message, MSG[lang]["thanks_fb"])
        return

    if any(k in text.lower() for ks in EMERGENCY.values() for k in ks):
        bot.reply_to(message, EMERGENCY_RESP[lang])
        ask_more(message)
        return

    answered = process_query(message, text, lang)
    if not answered:
        bot.reply_to(message, MSG[lang]["retry"])
    ask_more(message)

print("ربات روشن شد... v7")
bot.polling()