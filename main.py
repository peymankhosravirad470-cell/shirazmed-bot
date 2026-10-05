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

START_MSG = """🌟 سلام و خوش آمدید! از اینکه شیراز مد را انتخاب کردید سپاسگزاریم.
🌟 Welcome! Thank you for choosing Shiraz Med.
🌟 مرحباً بكم! نشكركم لاختياركم شيراز ميد.

زبان خود را انتخاب کنید / Choose your language / اختاروا لغتكم:
1 - فارسی
2 - العربية
3 - English"""

MSG = {
    "fa": {
        "welcome": "🌟 خوش آمدید! من دستیار گردشگری سلامت شیراز هستم. چطور می‌توانم کمکتان کنم؟ (مثلاً بنویسید: دکتر قلب)",
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
        "welcome": "🌟 أهلاً بكم! أنا مساعدكم للسياحة العلاجية في شيراز. كيف أساعدكم؟ (مثلاً اكتبوا: طبيب قلب)",
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
        "welcome": "🌟 Welcome! I'm your Shiraz health-tourism assistant. How can I help you? (For example: heart doctor)",
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

def search_doctors(text):
    low = text.lower()
    words = english_words(text)
    for k, fn in SPECIALTY_MAP.items():
        if k.isascii():
            found = k in words or (k + "s") in words
        else:
            found = k in low
        if found:
            try:
                with open("data/doctors/" + fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data.sort(key=lambda x: x.get('ratings', {}).get('patient_satisfaction_score', 0), reverse=True)
                return data
            except: return None
    return None

def format_doctor(doc, lang):
    n, s = doc.get('name', ''), doc.get('specialty', '')
    p = doc.get('contact', {}).get('phone', '')
    a = doc.get('contact', {}).get('office_address', '')
    h = "، ".join(doc.get('service_details', {}).get('hospitals', []))
    pr = doc.get('service_details', {}).get('price_range_toman', '')
    r = doc.get('ratings', {}).get('patient_satisfaction_score', '')
    if lang == "en":
        return f"Doctor: {n}\nSpecialty: {s}\nAddress: {a}\nHospitals: {h}\nPhone: {p}\nPrice: {pr}\nRating: {r}/5"
    if lang == "ar":
        return f"الطبيب: {n}\nالتخصص: {s}\nالعنوان: {a}\nالمستشفيات: {h}\nالهاتف: {p}\nالتكلفة: {pr}\nالتقييم: {r}/5"
    return f"دکتر: {n}\nتخصص: {s}\nآدرس: {a}\nبیمارستان: {h}\nتلفن: {p}\nقیمت: {pr}\nامتیاز: {r}/5"

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

    docs = search_doctors(text)
    if docs:
        words = english_words(text)
        if "همه" in text or "all" in words or "كل" in text: limit = len(docs)
        elif "بهترین" in text or "best" in words or "أفضل" in text: limit = 1
        else: limit = 3
        for d in docs[:limit]:
            bot.reply_to(message, format_doctor(d, lang))
        ask_more(message)
        return

    ai = get_ai(text, lang)
    if ai: bot.reply_to(message, ai)
    else: bot.reply_to(message, MSG[lang]["retry"])
    ask_more(message)

print("ربات روشن شد...")
bot.polling()