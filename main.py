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

SPECIALTY_MAP = {
    "قلب": "cardiology.json", "cardio": "cardiology.json", "heart": "cardiology.json",
    "پوست": "dermatology.json", "derma": "dermatology.json", "skin": "dermatology.json",
    "دندان": "dentistry.json", "dental": "dentistry.json", "dentist": "dentistry.json",
    "چشم": "ophthalmology.json", "eye": "ophthalmology.json",
    "گوش": "ent.json", "بینی": "ent.json", "nose": "ent.json", "ent": "ent.json",
    "ارتوپدی": "orthopedics.json", "ortho": "orthopedics.json", "bone": "orthopedics.json",
    "زنان": "gynecology.json", "نازایی":