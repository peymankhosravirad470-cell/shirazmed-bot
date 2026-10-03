import json, os, telebot, requests

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

SYSTEM_PROMPT = "دستیار گردشگری سلامت شیراز. به زبان کاربر جواب بده. کوتاه، با همدلی، بدون قیمت دقیق، بدون تضمین، در پایان سوال بپرس."

WELCOME = """🌟 سلام و خوش آمدید!
از اینکه کانال شیراز مد را انتخاب کردید سپاسگزاریم.

🌟 Welcome!
Thank you for choosing Shiraz Med.

🌟 مرحباً بكم!
نشكركم جزيل الشكر لاختياركم قناة شيراز ميد.

اهل کدام کشور هستید؟ / Which country are you from? / من أي بلد أنتم؟"""

SATISFACTION = """🙏 از خدمات ما راضی بودید؟ (بله / خیر)
🙏 Are you satisfied? (Yes / No)
🙏 هل أنتم راضون؟ (نعم / لا)"""

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

def detect_language(text):
    if set(text) & set("پچژگ"): return "fa"
    if set(text) & set("ابتثجحخدذرزسشصضطظعغفقکلمنهویءآأإئؤ"): return "ar"
    return "en"

def search_doctors(text):
    for k, fn in SPECIALTY_MAP.items():
        if k in text.lower():
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

def get_ai(text):
    try:
        r = requests.post(AVALAI_URL,
            headers={"Authorization": "Bearer " + AVALAI_API_KEY, "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]},
            timeout=15)
        return r.json()['choices'][0]['message']['content']
    except: return None

user_state = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.chat.id] = "awaiting_country"
    bot.reply_to(message, WELCOME)

@bot.message_handler(func=lambda m: True)
def handle(message):
    cid = message.chat.id
    text = message.text
    lang = detect_language(text)

    if user_state.get(cid) == "awaiting_country":
        user_state[cid] = "active"
        if lang == "fa": reply = "از آشنایی خوشحالیم. چطور کمکتون کنم؟"
        elif lang == "ar": reply = "سعداء بمعرفتكم. كيف أساعدكم؟"
        else: reply = "Nice to meet you. How can I help you?"
        bot.reply_to(message, reply)
        return

    if any(k in text for k in EMERGENCY.get(lang, [])):
        bot.reply_to(message, EMERGENCY_RESP[lang])
        bot.reply_to(message, SATISFACTION)
        return

    docs = search_doctors(text)
    if docs:
        if "همه" in text or "all" in text.lower() or "كل" in text: limit = len(docs)
        elif "بهترین" in text or "best" in text.lower() or "أفضل" in text: limit = 1
        else: limit = 3
        for d in docs[:limit]:
            bot.reply_to(message, format_doctor(d, lang))
        bot.reply_to(message, SATISFACTION)
        return

    ai = get_ai(text)
    if ai: bot.reply_to(message, ai)
    else: bot.reply_to(message, "متأسفم، دوباره تلاش کن. / Sorry, try again.")
    bot.reply_to(message, SATISFACTION)

print("ربات روشن شد...")
bot.polling()