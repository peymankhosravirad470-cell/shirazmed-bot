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
    for k, v in item.items():
        if k in ('id',):
            continue
        if isinstance(v, list):
            v = "، ".join(str(x) for x in v)
        elif isinstance(v, dict):
            v = "، ".join(f"{kk}: {vv}" for kk, vv in v.items())
        if v and str(v).strip() and str(v) != 'None':
            lines.append(f"{k}: {v}")
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
        if t in NO_WORDS:
            user_state[cid] = "awaiting_rating"
            bot.reply_to(message, MSG[lang]["rate"])
            return
        if t in YES_WORDS:
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["go"])
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

    docs = search_specialty(text)
    if docs:
        words = english_words(text)
        if "همه" in text or "all" in words or "كل" in text: limit = len(docs)
        elif "بهترین" in text or "best" in words or "أفضل" in text: limit = 1
        else: limit = 3
        for d in docs[:limit]:
            bot.reply_to(message, format_doctor(d, lang))
        ask_more(message)
        return

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
            ask_more(message)
            return

    ai = get_ai(text, lang)
    if ai: bot.reply_to(message, ai)
    else: bot.reply_to(message, MSG[lang]["retry"])
    ask_more(message)

print("ربات روشن شد... v4")
bot.polling()