# -*- coding: utf-8 -*-
"""
Shiraz Medical Bot - v46 (Full Featured)
Platform: Bale (tapi.bale.ai)
Author: Owner of Shiraz Medical
Python: 3.11
"""
   
import json
import os
import re
import io
import random
import base64
import hashlib
import threading
import time as time_module
from datetime import datetime, timedelta
from urllib.parse import quote
from typing import Optional, Dict, Any, List

import requests
import telebot
from telebot import types

# ─── Optional imports with graceful fallback ───
try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    jdatetime = None
    HAS_JDATETIME = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# ═══════════════════════════════════════════════
# ENVIRONMENT / CONFIG
# ═══════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "")
AVALAI_API_KEY = os.environ.get("AVALAI_API_KEY", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# Zarinpal
ZARINPAL_MERCHANT_ID = os.environ.get("ZARINPAL_MERCHANT_ID", "00000000-0000-0000-0000-000000000000")
ZARINPAL_SANDBOX = os.environ.get("ZARINPAL_SANDBOX", "true").lower() == "true"
ZARINPAL_REQUEST_URL = (
    "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
    if ZARINPAL_SANDBOX
    else "https://payment.zarinpal.com/pg/v4/payment/request.json"
)
ZARINPAL_VERIFY_URL = (
    "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
    if ZARINPAL_SANDBOX
    else "https://payment.zarinpal.com/pg/v4/payment/verify.json"
)
ZARINPAL_STARTPAY = (
    "https://sandbox.zarinpal.com/pg/StartPay/"
    if ZARINPAL_SANDBOX
    else "https://payment.zarinpal.com/pg/StartPay/"
)

# AvalAI
AI_MODEL = "gpt-4o-mini"
STT_MODEL = "whisper-1"
AVALAI_URL = "https://api.avalai.ir/v1/chat/completions"
AVALAI_STT_URL = "https://api.avalai.ir/v1/audio/transcriptions"

# Bot
CHANNEL_LINK = "https://ble.ir/shiraz_medical"
CHANNEL_DISCOUNT = 5
TIMEZONE_OFFSET_HOURS = float(os.environ.get("TIMEZONE_OFFSET_HOURS", "3.5"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "ShirazMedBot")
MAX_VOICE_SECONDS = 60

# External
SNAPP_URL = "https://app.snapp.taxi/"
TAP30_URL = "https://app.tap30.ir/"
GOOGLE_TRANSLATE_URL = "https://translate.google.com/"
DEEPSEEK_URL = "https://chat.deepseek.com/"
GOOGLE_MAPS_DIR = "https://www.google.com/maps/dir/?api=1&destination="
GOOGLE_MAPS_SEARCH = "https://www.google.com/maps/search/?api=1&query="

# Paths
DATA_DIR = "/app/data" if os.path.isdir("/app/data") else "data"
FONTS_DIR = os.path.join(DATA_DIR, "fonts")

# ═══════════════════════════════════════════════
# BOT INIT
# ═══════════════════════════════════════════════

if BALE_BOT_TOKEN:
    telebot.apihelper.API_URL = "https://tapi.bale.ai/bot{0}/{1}"
    telebot.apihelper.FILE_URL = "https://tapi.bale.ai/file/bot{0}/{1}"
    bot = telebot.TeleBot(BALE_BOT_TOKEN)
    ACTIVE_TOKEN = BALE_BOT_TOKEN
    PLATFORM = "bale"
else:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    ACTIVE_TOKEN = TELEGRAM_BOT_TOKEN
    PLATFORM = "telegram"

# ═══════════════════════════════════════════════
# LANGUAGE CONSTANTS
# ═══════════════════════════════════════════════

LANG_NAMES = {"fa": "فارسی", "ar": "العربية", "en": "English"}
LANGS = ("fa", "ar", "en")

START_MSG = """🌟 سلام و خوش آمدید! از اینکه شیراز مدیکال را انتخاب کردید سپاسگزاریم.
🌟 Welcome! Thank you for choosing Shiraz Medical.
🌟 مرحباً بكم! نشكركم لاختياركم شيراز ميديكال.

زبان خود را انتخاب کنید / Choose your language / اختاروا لغتكم:
1 - فارسی
2 - العربية
3 - English"""

SYSTEM_PROMPT = (
    "شما دستیار گردشگری سلامت شیراز هستید. کوتاه و با همدلی جواب بده. "
    "هرگز تشخیص پزشکی نده، دارو تجویز نکن و قیمت دقیق نگو."
)

AI_DISCLAIMER = {
    "fa": "\n\n⚠️ این راهنمای اولیه‌ست، نه تشخیص پزشکی.",
    "ar": "\n\n⚠️ هذا توجيه أولي وليس تشخيصاً طبياً.",
    "en": "\n\n⚠️ This is a preliminary guide, not a medical diagnosis.",
}

# ═══════════════════════════════════════════════
# IN-MEMORY STATE
# ═══════════════════════════════════════════════

user_state: Dict[int, str] = {}
user_lang: Dict[int, str] = {}
user_temp: Dict[int, Dict[str, Any]] = {}
satisfaction_counter = {"count": 0, "positive": 0, "negative": 0}
STATE_LOCK = threading.Lock()

# ═══════════════════════════════════════════════
# DIGIT TRANSLATION
# ═══════════════════════════════════════════════

DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

# ═══════════════════════════════════════════════
# YES / NO WORDS
# ═══════════════════════════════════════════════

YES_WORDS = {
    "بله", "بلی", "آره", "اره", "آری", "اری", "ها", "بله حذف کن",
    "نعم", "ايوه", "أيوه", "نعم احذف",
    "yes", "yeah", "y", "yep", "sure", "ok", "yes delete",
}

NO_WORDS = {
    "نه", "نخیر", "خیر", "نه ممنون", "ندارم", "لغو",
    "لا", "لا شكرا", "ليس",
    "no", "nope", "n", "cancel",
}

# ═══════════════════════════════════════════════
# EMERGENCY KEYWORDS
# ═══════════════════════════════════════════════

EMERGENCY = {
    "fa": ["درد شدید", "تب", "خونریزی", "استفراغ", "ضعف", "غش", "سکته", "تشنج", "خفگی", "سکته قلبی", "ایست قلبی"],
    "ar": ["ألم شديد", "حمى", "نزيف", "قيء", "ضعف", "إغماء", "جلطة", "تشنج"],
    "en": ["severe pain", "fever", "bleeding", "vomiting", "weakness", "fainting", "stroke", "seizure"],
}

EMERGENCY_RESP = {
    "fa": "🚨 فوراً به اورژانس مراجعه کنید یا با ۱۱۵ تماس بگیرید.",
    "ar": "🚨 توجه فوراً إلى الطوارئ أو اتصل بالرقم ١١٥.",
    "en": "🚨 Go to emergency immediately or call 115.",
}

# ═══════════════════════════════════════════════
# CONTEXT WORDS (for search scoring)
# ═══════════════════════════════════════════════

CONTEXT_WORDS = ["بیمارستان", "hospital", "مستشفى", "شیراز", "shiraz", "شيراز", "doctor", "دکتر", "طبيب", "dr"]

# ═══════════════════════════════════════════════
# PRICE MAP
# ═══════════════════════════════════════════════

PRICE_MAP = {
    "Low":    {"fa": "اقتصادی", "ar": "اقتصادي", "en": "Low"},
    "Medium": {"fa": "متوسط", "ar": "متوسط", "en": "Medium"},
    "High":   {"fa": "گران", "ar": "غالي", "en": "High"},
}

# ═══════════════════════════════════════════════
# COMMAND SETS
# ═══════════════════════════════════════════════

CMD_FILE        = {"پرونده", "پرونده من", "ملف", "ملفي", "file", "my file"}
CMD_APT         = {"نوبت", "نوبت‌ها", "نوبت‌هام", "موعد", "مواعيد", "appointment", "appointments"}
CMD_COMPANION   = {"همراه", "همراهم", "مرافق", "companion"}
CMD_COMPLAINT   = {"شکایت", "شکایات", "انتقاد", "نظر", "شكوى", "complaint", "feedback"}
CMD_MED         = {"دارو", "یادآور", "یادآور دارو", "دواء", "تذكير", "med", "medication", "reminder"}
CMD_RIGHTS      = {"حقوق", "حق من", "حقوق بیمار", "حقوقي", "rights", "patient rights"}
CMD_FOOD        = {"چی بخورم", "غذا", "تغذیه", "تداخل", "طعام", "تغذية", "food", "nutrition"}
CMD_FLOWER      = {"گل", "امید", "دلگرمی", "زهرة", "أمل", "flower", "hope"}
CMD_SOS         = {"اضطراری", "کمک", "فوری", "حالم خوب نیست", "حالم بده", "طوارئ", "emergency", "help", "urgent", "sos"}
CMD_INVITE      = {"دعوت", "معرفی", "کد معرف", "دعوة", "إحالة", "invite", "referral"}
CMD_MENU        = {"منو", "راهنما", "قائمة", "menu", "help"}
CMD_NIGHT       = {"شب بخیر", "شب‌بخیر", "مساء الخير", "good night", "goodnight"}
CMD_DELETE      = {"حذف اطلاعات", "پاک کردن", "delete my data"}
CMD_PARA        = {"پیراپزشکی", "پارامدیکال", "paramedical", "مساعد طبي"}
CMD_ELDERLY     = {"خانه سالمندان", "خانه‌ی سالمندان", "آسایشگاه", "سرای سالمندان", "nursing home", "elderly", "دار المسنين"}
CMD_ELDERLY_ALL = {"همه خانه سالمندان", "کل خانه سالمندان", "all nursing homes", "كل دور المسنين"}
CMD_PACKAGE     = {"پکیج", "پکیج درمان", "پکیج گردشگری", "پکیج سلامت", "باكج", "باكج علاج", "package"}
CMD_CHANNEL     = {"عضویت در کانال", "عضویت کانال", "کانال", "channel", "join channel", "قناة", "انضمام"}
CMD_TAXI        = {"تاکسی", "اسنپ", "تپسی", "snapp", "tap30", "tap 30", "taxi", "تكسي", "اسناب"}
CMD_HUBS        = {"پایانه", "پایانه‌ها", "ترمینال", "فرودگاه", "راه‌آهن", "قطار", "اتوبوس", "hub", "hubs", "airport", "train", "bus", "terminal", "مطار", "محطة", "محطات"}
CMD_INSURANCE   = {"بیمه", "بیمه‌ها", "بیمه من", "insurance", "تأمين", "تامين", "بیمه درمانی"}
CMD_TRANSLATOR  = {"مترجم", "ترجمه", "مترجم همراه", "translator", "translate", "المترجم", "ترجمة"}
CMD_CHARTER     = {"منشور", "منشور اخلاقی", "اخلاق", "charter", "ethics", "ميثاق", "أخلاق"}
CMD_DEEPSEEK    = {"دیپ سیک", "دیپ‌سیک", "هوش مصنوعی", "deepseek", "deep seek", "ai", "ذكاء اصطناعي"}

# ═══════════════════════════════════════════════
# SPECIALTY MAP (built after part 1; keys assigned in part 4)
# ═══════════════════════════════════════════════

SPECIALTY_MAP: Dict[str, str] = {}

SPECIALTY_LIST = [
    # (filename, persian, arabic, english, keyword1, keyword2, ...)
    ("cardiology.json",              "قلب و عروق",        "القلب",            "Cardiology",          "قلب", "قلبی", "cardio", "heart", "قلبية", "عروق"),
    ("dermatology.json",             "پوست و مو",         "الجلدية",          "Dermatology",         "پوست", "derma", "skin", "جلد", "جلدية"),
    ("dentistry.json",               "دندانپزشکی",        "طب الأسنان",       "Dentistry",           "دندان", "dental", "dentist", "أسنان", "اسنان"),
    ("kids_dentistry.json",          "دندانپزشکی کودکان", "أسنان الأطفال",    "Kids Dentistry",      "دندان کودکان", "kids dental", "أسنان أطفال"),
    ("ophthalmology.json",           "چشم‌پزشکی",         "طب العيون",        "Ophthalmology",       "چشم", "eye", "عيون", "عين"),
    ("ent.json",                     "گوش، حلق، بینی",    "الأنف والأذن",     "ENT",                 "گوش", "بینی", "گلو", "ent", "nose", "أنف", "أذن"),
    ("orthopedics.json",             "ارتوپدی",           "العظام",           "Orthopedics",         "ارتوپدی", "استخوان", "ortho", "bone", "عظام", "عظمي"),
    ("gynecology.json",              "زنان و زایمان",     "النساء والولادة",  "Gynecology",          "زنان", "نازایی", "ivf", "gyneco", "نساء", "ولادة"),
    ("pediatrics.json",              "کودکان",            "الأطفال",          "Pediatrics",          "کودک", "اطفال", "pediatric", "أطفال", "طفل"),
    ("psychiatry.json",              "روان‌پزشکی",        "الطب النفسي",      "Psychiatry",          "روان", "psych", "نفسي", "طب نفسي"),
    ("internal_medicine.json",       "داخلی",             "الباطنية",         "Internal Medicine",   "داخلی", "internal", "باطنية"),
    ("urology.json",                 "اورولوژی",          "المسالك",          "Urology",             "اورولوژی", "کلیه", "مثانه", "urology", "مسالك", "كلى"),
    ("general_surgery.json",         "جراحی عمومی",       "الجراحة العامة",   "General Surgery",     "جراح عمومی", "surgery", "جراحة عامة", "جراح"),
    ("rhinoplasty.json",             "جراحی بینی",        "تجميل الأنف",      "Rhinoplasty",         "رینوپلاستی", "جراحی بینی", "rhino", "تجميل الأنف"),
    ("gastroenterology.json",        "گوارش",             "الجهاز الهضمي",    "Gastroenterology",    "گوارش", "معده", "روده", "کبد", "gastro", "هضمي", "معدة"),
    ("emergency_medicine.json",      "اورژانس",           "الطوارئ",          "Emergency Medicine",  "اورژانس", "emergency", "طوارئ"),
    ("traditional_medicine.json",    "طب سنتی",           "الطب التقليدي",    "Traditional Medicine","طب سنتی", "گیاهی", "traditional", "طب تقليدي"),
    ("pharmacies.json",              "داروخانه",          "الصيدلية",         "Pharmacies",          "داروخانه", "دارو", "pharmacy", "صيدلية", "دواء"),
    ("allergy.json",                 "آلرژی",             "الحساسية",         "Allergy",             "آلرژی", "حساسیت", "allergy", "حساسية", "تحسس"),
    ("hematology_oncology.json",     "خون و سرطان",       "الدم والأورام",    "Hematology-Oncology", "خون", "آنکولوژی", "سرطان", "hematology", "oncology", "دم", "أورام"),
    ("endocrinology.json",           "غدد",               "الغدد",            "Endocrinology",       "غدد", "تیروئید", "دیابت", "endocrinology", "غدة", "سكري", "درقية"),
    ("neurosurgery.json",            "مغز و اعصاب",       "الأعصاب",          "Neurosurgery",        "مغز و اعصاب", "نوروسرجری", "neurosurgery", "دماغ", "أعصاب", "صرع", "ms"),
    # Add more as needed — the code auto-discovers any *.json in data/doctors/
]

# ═══════════════════════════════════════════════
# NON-MEDICAL MAP
# ═══════════════════════════════════════════════

NON_MEDICAL_MAP = {
    "hospitals.json":       ["بیمارستان", "hospital", "مستشفى", "کلینیک", "clinic"],
    "hotels.json":          ["هتل", "hotel", "فندق", "فنادق", "اقامتگاه"],
    "motels.json":          ["مهمان‌پذیر", "مسافرخانه", "motel", "نُزل", "نزل"],
    "tourist_houses.json":  ["خانه مسافر", "اقامتگاه بومگردی", "tourist house", "guest house", "بيت مسافر"],
    "leisure_city.json":    ["جاذبه", "حافظیه", "سعدیه", "ارگ", "نصیرالملک", "شاهچراغ", "باغ ارم", "بازار وکیل", "موزه", "مسجد"],
    "leisure_outside.json": ["تخت جمشید", "پاسارگاد", "نقش رستم", "آبشار", "persepolis", "pasargad"],
    "transport.json":       ["حمل‌ونقل", "مترو", "اتوبوس", "فرودگاه", "transport", "metro", "مواصلات", "مطار"],
    "support.json":         ["پشتیبانی", "هلال احمر", "شماره اضطراری", "support", "دعم", "مساعدة"],
    "complaints.json":      ["شکایت", "شکایات", "complaint", "شكوى"],
    "patient_guide.json":   ["راهنمای بیمار", "ویزای درمانی", "patient guide", "medical visa", "قبول مريض", "تأشيرة طبية"],
    "paramedical.json":     [
        "فیزیوتراپی", "فیزیوتراپ", "physiotherapy", "physio", "علاج طبيعي",
        "آزمایشگاه", "آزمایش", "lab", "laboratory", "مختبر",
        "رادیولوژی", "تصویربرداری", "ام آر آی", "mri", "ct", "سونوگرافی", "radiology", "أشعة",
        "پرستاری", "پرستار", "nursing", "nurse", "تمريض",
        "تزریق", "سرم", "injection", "iv", "حقن",
        "حجامت", "cupping",
        "کاردرمانی", "occupational", "علاج وظيفي",
        "گفتاردرمانی", "speech", "علاج النطق",
        "پروتز", "ارتوپدی فنی", "بریس", "کفی", "orthotics", "prosthetics", "أطراف",
        "پیراپزشکی", "paramedical", "مساعد طبي",
    ],
    "elderly_homes.json": [
        "خانه سالمندان", "خانه‌ی سالمندان", "آسایشگاه", "سرای سالمندان", "سالمندان",
        "nursing home", "nursing homes", "elderly", "senior",
        "دار المسنين", "دار رعاية المسنين", "مسنين", "عجزة",
    ],
}

# ═══════════════════════════════════════════════
# HUB LABELS
# ═══════════════════════════════════════════════

HUB_LABELS = {
    "shiraz_airport":     {"fa": "✈️ فرودگاه شهید دستغیب", "ar": "✈️ مطار الشهيد دستغيب", "en": "✈️ Shahid Dastgheib Airport"},
    "shiraz_railway":     {"fa": "🚂 ایستگاه راه‌آهن شیراز", "ar": "🚂 محطة قطار شيراز", "en": "🚂 Shiraz Railway Station"},
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

# ═══════════════════════════════════════════════
# DATA FILES
# ═══════════════════════════════════════════════

def data_path(name: str) -> str:
    return os.path.join(DATA_DIR, name)

APPOINTMENTS_FILE = data_path("appointments.json")
PATIENTS_FILE     = data_path("patients.json")
REFERRALS_FILE    = data_path("referrals.json")
COMPANIONS_FILE   = data_path("companions.json")
COMPLAINTS_FILE   = data_path("complaints.json")
MEDS_FILE         = data_path("meds.json")
USERS_FILE        = data_path("users.json")
PACKAGES_FILE     = data_path("packages.json")
RATINGS_FILE      = data_path("ratings.json")
PAYMENTS_FILE     = data_path("payments.json")
META_FILE         = data_path("meta.json")

print("═══ PART 1/6 LOADED ═══")
print("Platform:", PLATFORM)
print("DATA_DIR:", DATA_DIR)
print("jdatetime:", HAS_JDATETIME)
print("reportlab:", HAS_REPORTLAB)
print("qrcode:", HAS_QRCODE)
print("Zarinpal Sandbox:", ZARINPAL_SANDBOX)
# ═══════════════════════════════════════════════
# MSG — Main message dictionary (fa / ar / en)
# ═══════════════════════════════════════════════

MSG = {
    "fa": {
        # ─── Welcome & Main menu ───
        "welcome": (
            "🌟 یه پیام بدی، همه‌چیز رو آماده می‌کنیم.\n\n"
            "از پزشک تا هتل، از ترانسفر تا مترجم، از نوبت تا گشت گردشگری — همه‌چیز یکجا.\n\n"
            "بدون دغدغه، بدون هزینه اضافه 💙\n\n"
            "👇 از دکمه‌های زیر انتخاب کن:"
        ),
        "welcome_text": "یا خواسته‌ت رو بنویس:\nمثلاً «دکتر قلب» یا «پکیج درمان»",
        "more": "سؤال دیگری دارید؟ (بله / نه)",
        "go": "بفرمایید، سؤالتان را بنویسید.",
        "thanks": "🙏 سپاسگزاریم!\n\nاگر از خدمات ما راضی بودید، لطفاً ما را به دوستان و آشنایان خود معرفی کنید. 🌹",
        "thanks_fb": "ممنون از نظرتان. 🙏",
        "retry": "متأسفم، الان نتوانستم جواب بدهم. دوباره تلاش کنید.",
        "text_only": "لطفاً سؤال خود را به صورت متن بنویسید.",

        # ─── Appointment flow ───
        "apt_ask": "📅 برای گرفتن نوبت با این پزشک، شماره ۱ را بزنید.\n📞 برای تماس مستقیم، شماره ۲ را بزنید.",
        "apt_pick_title": "👨‍⚕️ پزشکان بالا:",
        "apt_pick_footer": "\n📅 برای گرفتن نوبت، شماره‌ی پزشک مورد نظرت رو بنویس:",
        "apt_choose_office": "🏥 لطفاً مطب مورد نظر خود را انتخاب کنید:",
        "apt_choose_date": "📅 لطفاً تاریخ نوبت را انتخاب کنید (۱۴ روز آینده):",
        "apt_choose_time": "⏰ لطفاً ساعت نوبت را انتخاب کنید:",
        "apt_ask_national_id": "🆔 لطفاً کد ملی ۱۰ رقمی خود را وارد کنید:",
        "apt_invalid_national_id": "❌ کد ملی نامعتبر است. لطفاً یک کد ملی صحیح ۱۰ رقمی وارد کنید.",
        "apt_ask_insurance": "🏥 آیا بیمه دارید؟",
        "apt_choose_insurance": "🏥 لطفاً بیمه خود را انتخاب کنید:",
        "apt_choose_payment_type": "💰 نحوه پرداخت را انتخاب کنید:\n\n1️⃣ مبلغ کامل پزشک\n2️⃣ سهم بیمه (پس از کسر)",
        "apt_ask_priority": "⚡ اولویت نوبت:\n\n1️⃣ عادی\n2️⃣ فوری (هزینه اضافه)",
        "apt_name": "👤 لطفاً نام و نام خانوادگی خود را بنویسید:",
        "apt_phone": "📞 لطفاً شماره تماس خود را بنویسید (مثال: 09123456789):",
        "apt_confirm_final": (
            "آیا درخواست با این اطلاعات ثبت شود؟ (بله / نه)\n\n"
            "👤 نام: {name}\n"
            "📞 تلفن: {phone}\n"
            "🆔 کد ملی: {nid}\n"
            "👨‍⚕️ پزشک: {doctor}\n"
            "🏥 مطب: {office}\n"
            "📅 تاریخ: {date}\n"
            "⏰ ساعت: {time}\n"
            "🏥 بیمه: {insurance}\n"
            "💰 مبلغ: {amount} تومان\n"
            "⚡ اولویت: {priority}"
        ),
        "apt_submitted": (
            "✅ درخواست نوبت شما ثبت شد!\n\n"
            "📋 کد پیگیری: {id}\n"
            "👨‍⚕️ پزشک: {doctor}\n\n"
            "⏳ ما با مطب تماس می‌گیریم و سریع‌ترین نوبت موجود رو براتون هماهنگ می‌کنیم."
        ),
        "apt_cancelled": "❌ ثبت نوبت لغو شد.",
        "apt_invalid": "لطفاً یکی از شماره‌های داده شده را بزنید.\n\n🚪 برای خروج: منو",
        "apt_error": "❌ متأسفانه در ثبت نوبت مشکلی پیش آمد.",
        "apt_my": "📋 نوبت‌های شما:",
        "apt_none": "شما هنوز هیچ نوبتی ثبت نکرده‌اید.",
        "apt_confirm_yes_no": "آیا تأیید می‌کنید؟ (بله / نه)",

        # ─── Admin ───
        "apt_admin_new": (
            "📥 درخواست نوبت جدید\n\n"
            "📋 کد: {id}\n"
            "👤 بیمار: {name}\n"
            "📞 تلفن: {phone}\n"
            "🆔 کد ملی: {nid}\n"
            "👨‍⚕️ پزشک: {doctor}\n"
            "📞 تلفن مطب: {dphone}\n"
            "🏥 مطب: {office}\n"
            "📅 تاریخ: {date}\n"
            "⏰ ساعت: {time}\n"
            "🏥 بیمه: {insurance}\n"
            "💰 مبلغ: {amount} تومان\n"
            "⚡ اولویت: {priority}\n\n"
            "⏳ تأیید:\n/confirm {id} 1405/09/20 10:30\n"
            "✅ انجام ویزیت:\n/done {id}"
        ),
        "apt_patient_confirmed": (
            "🎉 نوبت شما تأیید شد!\n\n"
            "📋 کد: {id}\n"
            "👨‍⚕️ پزشک: {doctor}\n"
            "📅 تاریخ: {date}\n"
            "⏰ ساعت: {time}\n"
            "📍 آدرس: {address}"
        ),
        "apt_done_admin_ok": "✅ ویزیت {id} علامت خورد. نظرخواهی از بیمار ارسال شد.",
        "apt_done_admin_bad": "❌ نوبت {id} پیدا نشد.",
        "apt_done_patient": "🎊 امیدواریم ویزیت خوب پیش رفته باشه!\n\nلطفاً به ما بگو از خدمات چقدر راضی بودی:",

        # ─── Patient file ───
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

        # ─── GDPR delete ───
        "delete_ask": "⚠️ مطمئنی؟ برای تأیید بنویس: بله حذف کن",
        "delete_done": "✅ همه‌ی اطلاعات شما پاک شد.",
        "delete_cancel": "باشه، اطلاعاتت دست‌نخورده موند.",

        # ─── Rating ───
        "rate_thanks_5": "🌟 وای، ۵ ستاره! خیلی خوشحال شدیم 💙\n\nاگه دوستی داری که به پزشک نیاز داره، لطفاً ما رو بهش معرفی کن. پاداش داری 🎁",
        "rate_thanks_4": "😊 ممنون از امتیاز ۴ ستاره!\n\nاگه دوستی داری که به پزشک نیاز داره، ما رو بهش معرفی کن 🎁",
        "rate_thanks_3": "🙏 ممنون از نظرت.\n\nسعی می‌کنیم دفعه بعد بهتر باشیم 💙",
        "rate_thanks_low": "😔 متأسفیم که راضی نبودی.\n\nلطفاً به ما بگو چه چیزی باعث نارضایتی شد تا بهتر بشیم:",
        "rate_thanks_low_admin": "❌ عدم رضایت جدید\n\n📋 نوبت: {id}\n⭐ امتیاز: {stars}\n👤 بیمار: {name}\nChatID: {cid}\n\n💬 نظر:\n{text}",
        "rate_feedback_thanks": "🙏 ممنون که نظرت رو گفتی.\n\nما حتماً پیگیری می‌کنیم 💙",

        # ─── Reminders ───
        "remind_apt_1d": "⏰ یادآوری نوبت\n\n📅 فردا ساعت {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nلطفاً ۱۵ دقیقه قبل حاضر باش. 💙",
        "remind_apt_2h": "⏰ یادآوری نوبت\n\n🕐 ۲ ساعت دیگه\n👨‍⚕️ {doctor}\n⏰ ساعت {time}\n📍 {address}\n\nما منتظرتیم 🌷",
        "remind_med": "💊 یادآوری دارو\n\nوقت مصرف {med} هست.\n\nسلامتت مهمه 💙",

        # ─── Taxi ───
        "taxi_title": "🚕 درخواست تاکسی\n\nبرای رفتن به مقصد، یکی از اپ‌های زیر رو باز کن و مقصد رو توی اپ وارد کن:",

        # ─── Hub / Insurance / Translator ───
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

        # ─── Charter ───
        "charter_title": "📜 منشور اخلاقی شیراز مدیکال",
        "charter_body": (
            "ما در شیراز مدیکال، خود را متعهد می‌دانیم به:\n\n"
            "۱. احترام و کرامت انسانی\n"
            "با هر بیمار، فارغ از ملیت، زبان، مذهب یا توانایی مالی، با احترام کامل رفتار می‌کنیم.\n\n"
            "۲. شفافیت کامل قیمت\n"
            "هیچ هزینه‌ای پنهان نمی‌ماند. قبل از هر خدمت، قیمت دقیق و شفاف اعلام می‌شود.\n\n"
            "۳. محرمانگی اطلاعات\n"
            "اطلاعات پزشکی و شخصی شما نزد ما امانت است و بدون اجازه‌ی شما با هیچ کس به اشتراک گذاشته نمی‌شود.\n\n"
            "۴. انتخاب آزاد پزشک\n"
            "شما حق دارید پزشک، بیمارستان و مرکز درمانی خود را آزادانه انتخاب کنید.\n\n"
            "۵. رضایت آگاهانه\n"
            "قبل از هر اقدام درمانی، تمام جوانب، خطرات و مزایا برای شما توضیح داده می‌شود.\n\n"
            "۶. پیگیری و مسئولیت‌پذیری\n"
            "ما تا پایان مسیر درمان، حتی بعد از بازگشت به کشورتان، همراه شما هستیم.\n\n"
            "۷. عدم تبعیض\n"
            "هیچ بیماری به دلیل ملیت، جنسیت، مذهب یا ناتوانی از خدمات ما محروم نمی‌شود.\n\n"
            "۸. صداقت پزشکی\n"
            "هیچ خدمت غیرضروری به شما تحمیل نمی‌شود. فقط آنچه برای سلامت شما لازم است ارائه می‌شود.\n\n"
            "۹. حق اعتراض\n"
            "شما همیشه حق دارید شکایت کنید، نظر بدهید و پاسخ بگیرید.\n\n"
            "۱۰. حفظ کرامت انسانی\n"
            "بدن، حریم خصوصی و اعتقادات شما همیشه محترم شمرده می‌شود.\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💙 شیراز مدیکال\n"
            "سلامت شما، تعهد ما"
        ),

        # ─── DeepSeek ───
        "deepseek_title": "🤖 دستیار هوشمند DeepSeek\n\nهر سؤالی داری بپرس: پزشکی، ترجمه، مشاوره، هر چیزی.\n\nرایگان و بدون محدودیت 🚀",

        # ─── Payment / Invoice ───
        "pay_creating": "⏳ در حال ایجاد لینک پرداخت...",
        "pay_link": (
            "💳 لینک پرداخت شما آماده است:\n\n"
            "📋 کد پرداخت: {pid}\n"
            "💰 مبلغ: {amount} تومان\n"
            "📅 نوبت: {apt_id}\n\n"
            "👇 روی دکمه زیر بزن و پرداخت کن:"
        ),
        "pay_button": "💳 پرداخت {amount} تومان",
        "pay_pending": "⏳ پرداخت شما در انتظار تأیید است.\n\nپس از پرداخت، کد پیگیری را اینجا بنویس یا روی «بررسی پرداخت» بزن.",
        "pay_check_button": "🔄 بررسی پرداخت",
        "pay_success": "✅ پرداخت شما با موفقیت انجام شد!\n\n📋 کد رهگیری بانکی: {ref}\n💳 کد پرداخت: {pid}",
        "pay_failed": "❌ پرداخت ناموفق بود.\n\nلطفاً دوباره تلاش کن یا با پشتیبانی تماس بگیر.",
        "pay_not_found": "❌ پرداختی با این کد پیدا نشد.",
        "pay_error": "❌ خطا در ایجاد پرداخت. لطفاً بعداً تلاش کن.",
        "invoice_button": "📄 دریافت فیش رسمی",
        "invoice_generating": "⏳ در حال ساخت فیش...",
        "invoice_caption": "📄 فیش رسمی نوبت {apt_id}\n\n💰 مبلغ: {amount} تومان\n🆔 کد رهگیری: {ref}",

        # ─── Payment type & Priority ───
        "payment_full": "پرداخت کامل",
        "payment_insurance": "سهم بیمه",
        "priority_normal": "عادی",
        "priority_urgent": "فوری",
    },

    "ar": {
        # ─── Welcome ───
        "welcome": (
            "🌟 رسالة واحدة، ونجهز كل شيء.\n\n"
            "من الطبيب إلى الفندق، من النقل إلى المترجم، من الموعد إلى الجولة السياحية — كل شيء في مكان واحد.\n\n"
            "بدون قلق، بدون تكاليف إضافية 💙\n\n"
            "👇 اختاروا من الأزرار:"
        ),
        "welcome_text": "أو اكتبوا طلبكم:\nمثلاً «طبيب قلب» أو «باكج العلاج»",
        "more": "سؤال آخر؟ (نعم / لا)",
        "go": "اكتبوا سؤالكم.",
        "thanks": "🙏 شكراً!\n\nإذا كنتم راضين عن خدماتنا، نرجو تعريفنا لأصدقائكم. 🌹",
        "thanks_fb": "شكراً لرأيكم. 🙏",
        "retry": "عذراً، لم أتمكن من الرد. حاولوا مرة أخرى.",
        "text_only": "اكتبوا سؤالكم كنص.",

        # ─── Appointment ───
        "apt_ask": "📅 لطلب موعد اضغط ١.\n📞 للاتصال المباشر اضغط ٢.",
        "apt_pick_title": "👨‍⚕️ الأطباء:",
        "apt_pick_footer": "\n📅 اكتبوا رقم الطبيب:",
        "apt_choose_office": "🏥 اختاروا العيادة:",
        "apt_choose_date": "📅 اختاروا التاريخ (١٤ يوماً قادمة):",
        "apt_choose_time": "⏰ اختاروا الساعة:",
        "apt_ask_national_id": "🆔 أدخلوا رقم الهوية الوطنية (١٠ أرقام):",
        "apt_invalid_national_id": "❌ رقم الهوية غير صحيح. أدخلوا رقماً صحيحاً.",
        "apt_ask_insurance": "🏥 هل لديكم تأمين؟",
        "apt_choose_insurance": "🏥 اختاروا التأمين:",
        "apt_choose_payment_type": "💰 طريقة الدفع:\n\n1️⃣ المبلغ الكامل\n2️⃣ حصة التأمين",
        "apt_ask_priority": "⚡ الأولوية:\n\n1️⃣ عادي\n2️⃣ عاجل (رسوم إضافية)",
        "apt_name": "👤 الاسم الكامل:",
        "apt_phone": "📞 رقم الهاتف:",
        "apt_confirm_final": (
            "تأكيد الطلب؟ (نعم / لا)\n\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "🆔 {nid}\n"
            "👨‍⚕️ {doctor}\n"
            "🏥 {office}\n"
            "📅 {date}\n"
            "⏰ {time}\n"
            "🏥 {insurance}\n"
            "💰 {amount} تومان\n"
            "⚡ {priority}"
        ),
        "apt_submitted": "✅ تم تسجيل طلبكم!\n\n📋 {id}\n👨‍⚕️ {doctor}\n\nسنتصل بالعيادة لتأكيد الموعد.",
        "apt_cancelled": "❌ تم الإلغاء.",
        "apt_invalid": "اكتبوا رقماً صحيحاً.\n\n🚪 للخروج: القائمة",
        "apt_error": "❌ خطأ في التسجيل.",
        "apt_my": "📋 مواعيدكم:",
        "apt_none": "لا مواعيد بعد.",
        "apt_confirm_yes_no": "تأكيد؟ (نعم / لا)",

        # ─── Admin ───
        "apt_admin_new": (
            "📥 طلب جديد\n\n"
            "📋 {id}\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "🆔 {nid}\n"
            "👨‍⚕️ {doctor}\n"
            "📞 {dphone}\n"
            "🏥 {office}\n"
            "📅 {date}\n"
            "⏰ {time}\n"
            "🏥 {insurance}\n"
            "💰 {amount}\n"
            "⚡ {priority}\n\n"
            "/confirm {id} 1405/09/20 10:30\n"
            "/done {id}"
        ),
        "apt_patient_confirmed": (
            "🎉 تم التأكيد!\n\n"
            "📋 {id}\n"
            "👨‍⚕️ {doctor}\n"
            "📅 {date}\n"
            "⏰ {time}\n"
            "📍 {address}"
        ),
        "apt_done_admin_ok": "✅ تم / استبيان أرسل.",
        "apt_done_admin_bad": "❌ غير موجود.",
        "apt_done_patient": "🎊 كيف كانت الخدمة؟",

        # ─── Patient file ───
        "pt_created": "🎫 الملف: {code}",
        "pt_title": "🎫 ملفكم\n━━━━━━━━━━━━━━━",
        "pt_code": "📋 {code}",
        "pt_name": "👤 {name}",
        "pt_progress": "\n🌟 المسار:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "الطلب",
        "pt_stages_doctor": "الطبيب",
        "pt_stages_date": "التاريخ",
        "pt_stages_accommodation": "الإقامة",
        "pt_stages_transport": "المواصلات",
        "pt_stages_treatment": "العلاج",
        "pt_stages_followup": "المتابعة",
        "pt_appointments": "\n📅:",
        "pt_apt_line_pending": "⏳ {id} — {doctor}",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date}",
        "pt_apt_line_done": "🎊 {id} — {doctor}",
        "pt_not_found": "لا ملف 💙",

        # ─── GDPR ───
        "delete_ask": "⚠️ اكتبوا: نعم احذف",
        "delete_done": "✅ تم الحذف.",
        "delete_cancel": "حسناً.",

        # ─── Rating ───
        "rate_thanks_5": "🌟 ٥ نجوم! شكراً 💙\n\nادعوا أصدقاءكم 🎁",
        "rate_thanks_4": "😊 شكراً 🎁",
        "rate_thanks_3": "🙏 شكراً 💙",
        "rate_thanks_low": "😔 أخبرونا بالسبب:",
        "rate_thanks_low_admin": "❌ عدم رضا\n\n{id} — {stars}⭐\n{name} — {cid}\n\n{text}",
        "rate_feedback_thanks": "🙏 شكراً 💙",

        # ─── Reminders ───
        "remind_apt_1d": "⏰ تذكير بالموعد\n\n📅 غداً الساعة {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nيرجى الحضور قبل ١٥ دقيقة. 💙",
        "remind_apt_2h": "⏰ تذكير بالموعد\n\n🕐 بعد ساعتين\n👨‍⚕️ {doctor}\n⏰ {time}\n📍 {address}\n\nنحن في انتظارك 🌷",
        "remind_med": "💊 تذكير بالدواء\n\nموعد تناول {med}.\n\nصحتك تهمنا 💙",

        # ─── Taxi ───
        "taxi_title": "🚕 طلب تاكسي\n\nافتح أحد التطبيقات التالية وأدخل الوجهة:",

        # ─── Hub / Insurance / Translator ───
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

        # ─── Charter ───
        "charter_title": "📜 ميثاق شيراز ميديكال الأخلاقي",
        "charter_body": (
            "نحن في شيراز ميديكال، نلتزم بـ:\n\n"
            "١. احترام الكرامة الإنسانية\n"
            "نتعامل مع كل مريض باحترام كامل، بغض النظر عن الجنسية أو اللغة أو الدين أو القدرة المالية.\n\n"
            "٢. الشفافية الكاملة في الأسعار\n"
            "لا توجد تكاليف خفية. تُعلن الأسعار الدقيقة بوضوح قبل كل خدمة.\n\n"
            "٣. سرية المعلومات\n"
            "معلوماتك الطبية والشخصية أمانة لدينا، ولا تُشارك مع أي شخص دون إذنك.\n\n"
            "٤. حرية اختيار الطبيب\n"
            "يحق لك اختيار طبيبك ومستشفاك ومركزك العلاجي بحرية.\n\n"
            "٥. الموافقة المستنيرة\n"
            "قبل كل إجراء علاجي، تُشرح لك جميع الجوانب والمخاطر والفوائد.\n\n"
            "٦. المتابعة والمسؤولية\n"
            "نرافقك حتى نهاية رحلة العلاج، حتى بعد عودتك إلى بلدك.\n\n"
            "٧. عدم التمييز\n"
            "لا يُحرم أي مريض من خدماتنا بسبب الجنسية أو الجنس أو الدين أو الإعاقة.\n\n"
            "٨. الصدق الطبي\n"
            "لا تُفرض عليك أي خدمة غير ضرورية. يُقدم فقط ما يلزم لصحتك.\n\n"
            "٩. حق الاعتراض\n"
            "يحق لك دائماً تقديم شكوى وإبداء رأيك والحصول على رد.\n\n"
            "١٠. الحفاظ على الكرامة الإنسانية\n"
            "يُحترم جسدك وخصوصيتك ومعتقداتك دائماً.\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💙 شيراز ميديكال\n"
            "صحتك، التزامنا"
        ),

        # ─── DeepSeek ───
        "deepseek_title": "🤖 مساعد DeepSeek الذكي\n\nاسأل أي شيء: طب، ترجمة، استشارة.\n\nمجاني وبدون قيود 🚀",

        # ─── Payment ───
        "pay_creating": "⏳ جاري إنشاء رابط الدفع...",
        "pay_link": "💳 رابط الدفع:\n\n📋 {pid}\n💰 {amount} تومان\n📅 {apt_id}\n\n👇 اضغط للدفع:",
        "pay_button": "💳 ادفع {amount} تومان",
        "pay_pending": "⏳ الدفع في انتظار التأكيد.",
        "pay_check_button": "🔄 تحقق من الدفع",
        "pay_success": "✅ تم الدفع بنجاح!\n\n📋 {ref}\n💳 {pid}",
        "pay_failed": "❌ فشل الدفع.",
        "pay_not_found": "❌ لم يتم العثور على الدفع.",
        "pay_error": "❌ خطأ في الدفع.",
        "invoice_button": "📄 الفاتورة الرسمية",
        "invoice_generating": "⏳ جاري الإنشاء...",
        "invoice_caption": "📄 فاتورة {apt_id}\n\n💰 {amount} تومان\n🆔 {ref}",

        # ─── Payment type & Priority ───
        "payment_full": "الدفع الكامل",
        "payment_insurance": "حصة التأمين",
        "priority_normal": "عادي",
        "priority_urgent": "عاجل",
    },

    "en": {
        # ─── Welcome ───
        "welcome": (
            "🌟 One message, we prepare everything.\n\n"
            "From doctor to hotel, from transfer to translator, from appointment to tour — all in one place.\n\n"
            "No worries, no hidden costs 💙\n\n"
            "👇 Choose from the buttons:"
        ),
        "welcome_text": "Or write your request:\ne.g. \"heart doctor\" or \"treatment package\"",
        "more": "Any other question? (Yes / No)",
        "go": "Please go ahead.",
        "thanks": "🙏 Thank you!\n\nIf you liked our services, please recommend us to friends. 🌹",
        "thanks_fb": "Thanks for your feedback. 🙏",
        "retry": "Sorry, I couldn't respond. Please try again.",
        "text_only": "Please write your question as text.",

        # ─── Appointment ───
        "apt_ask": "📅 Press 1 to book this doctor.\n📞 Press 2 to call directly.",
        "apt_pick_title": "👨‍⚕️ Doctors above:",
        "apt_pick_footer": "\n📅 Enter doctor's number:",
        "apt_choose_office": "🏥 Choose the office:",
        "apt_choose_date": "📅 Choose a date (next 14 days):",
        "apt_choose_time": "⏰ Choose a time:",
        "apt_ask_national_id": "🆔 Enter your 10-digit national ID:",
        "apt_invalid_national_id": "❌ Invalid national ID. Please enter a valid 10-digit ID.",
        "apt_ask_insurance": "🏥 Do you have insurance?",
        "apt_choose_insurance": "🏥 Choose your insurance:",
        "apt_choose_payment_type": "💰 Payment type:\n\n1️⃣ Full price\n2️⃣ Insurance share",
        "apt_ask_priority": "⚡ Priority:\n\n1️⃣ Normal\n2️⃣ Urgent (extra fee)",
        "apt_name": "👤 Full name:",
        "apt_phone": "📞 Phone number:",
        "apt_confirm_final": (
            "Confirm this request? (Yes / No)\n\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "🆔 {nid}\n"
            "👨‍⚕️ {doctor}\n"
            "🏥 {office}\n"
            "📅 {date}\n"
            "⏰ {time}\n"
            "🏥 {insurance}\n"
            "💰 {amount} Toman\n"
            "⚡ {priority}"
        ),
        "apt_submitted": "✅ Your request was submitted!\n\n📋 ID: {id}\n👨‍⚕️ {doctor}\n\nWe will contact the clinic to arrange the appointment.",
        "apt_cancelled": "❌ Cancelled.",
        "apt_invalid": "Enter a valid number.\n\n🚪 To exit: menu",
        "apt_error": "❌ Error submitting.",
        "apt_my": "📋 Your appointments:",
        "apt_none": "No appointments yet.",
        "apt_confirm_yes_no": "Confirm? (Yes / No)",

        # ─── Admin ───
        "apt_admin_new": (
            "📥 New request\n\n"
            "📋 {id}\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "🆔 {nid}\n"
            "👨‍⚕️ {doctor}\n"
            "📞 {dphone}\n"
            "🏥 {office}\n"
            "📅 {date}\n"
            "⏰ {time}\n"
            "🏥 {insurance}\n"
            "💰 {amount}\n"
            "⚡ {priority}\n\n"
            "/confirm {id} 1405/09/20 10:30\n"
            "/done {id}"
        ),
        "apt_patient_confirmed": (
            "🎉 Confirmed!\n\n"
            "📋 {id}\n"
            "👨‍⚕️ {doctor}\n"
            "📅 {date}\n"
            "⏰ {time}\n"
            "📍 {address}"
        ),
        "apt_done_admin_ok": "✅ Visit marked. Survey sent.",
        "apt_done_admin_bad": "❌ Not found.",
        "apt_done_patient": "🎊 How was your visit?",

        # ─── Patient file ───
        "pt_created": "🎫 Your file: {code}",
        "pt_title": "🎫 Your Health File\n━━━━━━━━━━━━━━━",
        "pt_code": "📋 {code}",
        "pt_name": "👤 {name}",
        "pt_progress": "\n🌟 Progress:",
        "pt_stage_done": "✅ {stage}",
        "pt_stage_wait": "⏳ {stage}",
        "pt_stages_request": "Request received",
        "pt_stages_doctor": "Doctor assigned",
        "pt_stages_date": "Date confirmed",
        "pt_stages_accommodation": "Accommodation arranged",
        "pt_stages_transport": "Transport arranged",
        "pt_stages_treatment": "Treatment done",
        "pt_stages_followup": "Follow-up",
        "pt_appointments": "\n📅 Appointments:",
        "pt_apt_line_pending": "⏳ {id} — {doctor} — awaiting date",
        "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} at {time}",
        "pt_apt_line_done": "🎊 {id} — {doctor} — completed",
        "pt_not_found": "No file yet. Book your first appointment 💙",

        # ─── GDPR ───
        "delete_ask": "⚠️ Are you sure? Type: yes delete",
        "delete_done": "✅ Your data was deleted.",
        "delete_cancel": "Okay, your data is safe.",

        # ─── Rating ───
        "rate_thanks_5": "🌟 5 stars! We're thrilled 💙\n\nInvite friends and earn rewards 🎁",
        "rate_thanks_4": "😊 Thanks for 4 stars! Invite friends 🎁",
        "rate_thanks_3": "🙏 Thanks for your feedback. We'll do better 💙",
        "rate_thanks_low": "😔 We're sorry. Please tell us why:",
        "rate_thanks_low_admin": "❌ Dissatisfied\n\n{id} — {stars}⭐\n{name} — {cid}\n\n{text}",
        "rate_feedback_thanks": "🙏 Thanks for your feedback 💙",

        # ─── Reminders ───
        "remind_apt_1d": "⏰ Appointment reminder\n\n📅 Tomorrow at {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nPlease arrive 15 minutes early. 💙",
        "remind_apt_2h": "⏰ Reminder\n\n🕐 In 2 hours\n👨‍⚕️ {doctor}\n⏰ {time}\n📍 {address}\n\nWe're waiting for you 🌷",
        "remind_med": "💊 Medication reminder\n\nTime to take {med}.\n\nYour health matters 💙",

        # ─── Taxi ───
        "taxi_title": "🚕 Request Taxi\n\nOpen one of the apps below and enter your destination:",

        # ─── Hub / Insurance / Translator ───
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

        # ─── Charter ───
        "charter_title": "📜 Shiraz Medical Ethical Charter",
        "charter_body": (
            "At Shiraz Medical, we are committed to:\n\n"
            "1. Respect for Human Dignity\n"
            "We treat every patient with full respect, regardless of nationality, language, religion, or financial ability.\n\n"
            "2. Full Price Transparency\n"
            "No hidden costs. The exact price is clearly announced before every service.\n\n"
            "3. Confidentiality\n"
            "Your medical and personal information is a trust with us and will not be shared without your consent.\n\n"
            "4. Freedom to Choose Your Doctor\n"
            "You have the right to freely choose your doctor, hospital, and medical center.\n\n"
            "5. Informed Consent\n"
            "Before any medical procedure, all aspects, risks, and benefits are explained to you.\n\n"
            "6. Follow-up and Responsibility\n"
            "We stay with you until the end of your treatment journey, even after you return home.\n\n"
            "7. Non-Discrimination\n"
            "No patient is denied our services due to nationality, gender, religion, or disability.\n\n"
            "8. Medical Honesty\n"
            "No unnecessary service is imposed on you. Only what is needed for your health is offered.\n\n"
            "9. Right to Complain\n"
            "You always have the right to complain, give feedback, and receive a response.\n\n"
            "10. Preservation of Human Dignity\n"
            "Your body, privacy, and beliefs are always respected.\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💙 Shiraz Medical\n"
            "Your Health, Our Commitment"
        ),

        # ─── DeepSeek ───
        "deepseek_title": "🤖 DeepSeek Smart Assistant\n\nAsk anything: medical, translation, consultation.\n\nFree and unlimited 🚀",

        # ─── Payment ───
        "pay_creating": "⏳ Creating payment link...",
        "pay_link": "💳 Payment link:\n\n📋 {pid}\n💰 {amount} Toman\n📅 {apt_id}\n\n👇 Tap to pay:",
        "pay_button": "💳 Pay {amount} Toman",
        "pay_pending": "⏳ Payment pending confirmation.",
        "pay_check_button": "🔄 Check payment",
        "pay_success": "✅ Payment successful!\n\n📋 {ref}\n💳 {pid}",
        "pay_failed": "❌ Payment failed.",
        "pay_not_found": "❌ Payment not found.",
        "pay_error": "❌ Payment error.",
        "invoice_button": "📄 Official invoice",
        "invoice_generating": "⏳ Generating...",
        "invoice_caption": "📄 Invoice {apt_id}\n\n💰 {amount} Toman\n🆔 {ref}",

        # ─── Payment type & Priority ───
        "payment_full": "Full payment",
        "payment_insurance": "Insurance share",
        "priority_normal": "Normal",
        "priority_urgent": "Urgent",
    },
}

print("═══ PART 2/6 LOADED ═══ MSG ready (fa/ar/en)")
# ═══════════════════════════════════════════════
# MSG_CH — Channel reward messages
# ═══════════════════════════════════════════════

MSG_CH = {
    "fa": {
        "btn_channel_go": "🔗 رفتن به کانال",
        "btn_channel_ok": "✅ عضو شدم",
        "msg_channel": (
            "🎁 یه هدیه کوچیک برات داریم\n\n"
            "عضو کانال ما بشو → ۵٪ تخفیف\n"
            "روی همه سرویس‌ها (پزشک، هتل، ترانسفر)\n\n"
            "بعد از عضویت، برگرد و بزن [✅ عضو شدم]"
        ),
        "msg_channel_done": (
            "✅ خوش اومدی!\n\n"
            "۵٪ تخفیف روی اولین سرویست فعال شد.\n\n"
            "الان می‌تونی نوبت پزشک بگیری یا هتل رزرو کنی.\n"
            "از /menu شروع کن 🚀"
        ),
        "msg_channel_already": (
            "😊 قبلاً عضو شدی و ۵٪ تخفیفت فعاله.\n"
            "بزن /menu و ازش استفاده کن."
        ),
    },
    "ar": {
        "btn_channel_go": "🔗 الذهاب للقناة",
        "btn_channel_ok": "✅ انضممت",
        "msg_channel": (
            "🎁 لدينا هدية صغيرة لك\n\n"
            "انضم إلى قناتنا → خصم ٥٪\n"
            "على جميع الخدمات (طبيب، فندق، نقل)\n\n"
            "بعد الانضمام، ارجع واضغط [✅ انضممت]"
        ),
        "msg_channel_done": (
            "✅ أهلاً بك!\n\n"
            "تم تفعيل خصم ٥٪ على خدمتك الأولى.\n\n"
            "يمكنك الآن حجز طبيب أو فندق.\n"
            "ابدأ بـ /menu 🚀"
        ),
        "msg_channel_already": (
            "😊 أنت مشترك بالفعل وخصم ٥٪ مفعّل.\n"
            "اضغط /menu للاستفادة منه."
        ),
    },
    "en": {
        "btn_channel_go": "🔗 Go to Channel",
        "btn_channel_ok": "✅ I joined",
        "msg_channel": (
            "🎁 A small gift for you\n\n"
            "Join our channel → 5% OFF\n"
            "on all services (doctor, hotel, transfer)\n\n"
            "After joining, come back and tap [✅ I joined]"
        ),
        "msg_channel_done": (
            "✅ Welcome aboard!\n\n"
            "Your 5% discount is now active.\n\n"
            "Book a doctor or hotel now.\n"
            "Start with /menu 🚀"
        ),
        "msg_channel_already": (
            "😊 You already joined and your 5% discount is active.\n"
            "Tap /menu to use it."
        ),
    },
}

# ═══════════════════════════════════════════════
# MSG2 — Secondary messages (patient file, hope, companion, SOS, rights, meds, food, package)
# ═══════════════════════════════════════════════

MSG2 = {
    "fa": {
        # ─── Referral ───
        "ref_your_code": "🔗 کد معرف شما: {code}\n\nلینک:\n{link}",
        "ref_your_stats": "👥 دعوت‌شده‌ها: {count}\n🎁 پاداش‌ها: {rewards}",
        "ref_new_from": "🎉 یکی با کد {code} پیوست!\n\nپاداش: ۱۰٪ تخفیف 🌹",
        "ref_welcome_new": "🎉 خوش آمدید!\n\nبا کد {code}.\n🎁 ۵٪ تخفیف اولین ویزیت",
        "ref_invite_msg": (
            "🌟 دوستت رو دعوت کن\n\n"
            "کد: {code}\n\n"
            "{link}\n\n"
            "🎁 تو: ۱۰٪ تخفیف\n"
            "🎁 دوستت: ۵٪ تخفیف"
        ),

        # ─── Hope / Encouragement ───
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

        # ─── Companion ───
        "comp_ask": "👥 آیا همراه دارید؟ (بله / نه)",
        "comp_ask_name": "👤 اسم همراهتون چیه؟",
        "comp_ask_phone": "📞 شماره‌ی همراهتون:",
        "comp_saved": "✅ همراه ثبت شد\n\n👤 {name}\n📞 {phone}",
        "comp_skip": "باشه، هر وقت خواستی بنویس: همراه",

        # ─── SOS ───
        "sos_menu": (
            "🚨 وضعیت اضطراری\n\n"
            "1️⃣ اورژانس ۱۱۵\n"
            "2️⃣ نزدیک‌ترین بیمارستان\n"
            "3️⃣ راهنمای کمک‌های اولیه\n"
            "4️⃣ اطلاع به همراه من\n"
            "5️⃣ انصراف"
        ),
        "sos_115": "🚑 اورژانس: ۱۱۵\n\nلطفاً تماس بگیرید و آدرس دقیق بگید.",
        "sos_first_aid": (
            "🩺 کمک‌های اولیه\n\n"
            "🔹 درد قفسه سینه:\n"
            "- بشین و استراحت\n"
            "- قرص زیر زبانی\n"
            "- فوراً ۱۱۵\n\n"
            "🔹 خونریزی:\n"
            "- فشار مستقیم\n"
            "- ۱۱۵\n\n"
            "🔹 تنگی نفس:\n"
            "- بشین صاف\n"
            "- ۱۱۵\n\n"
            "⚠️ این راهنما جایگزین پزشک نیست."
        ),
        "sos_no_companion": "❌ همراه ثبت نکردی. بنویس: همراه",

        # ─── Complaint ───
        "comp_voice_menu": (
            "📩 صدای شما\n\n"
            "1️⃣ انتقاد از پزشک\n"
            "2️⃣ انتقاد از مرکز درمانی\n"
            "3️⃣ انتقاد از اقامت\n"
            "4️⃣ انتقاد از حمل‌ونقل\n"
            "5️⃣ شکایت کلی\n"
            "6️⃣ انصراف"
        ),
        "comp_voice_text": "📝 متن پیامت رو بنویس:",
        "comp_voice_saved": "✅ پیام شما ثبت شد\n\n📋 کد: {id}\n\nما پیگیری می‌کنیم 💙",
        "comp_voice_skip": "باشه، هر وقت خواستی بنویس: شکایت",
        "comp_voice_admin": (
            "📩 شکایت جدید\n\n"
            "📋 {id}\n"
            "دسته: {category}\n"
            "نام: {name}\n"
            "ChatID: {cid}\n\n"
            "{text}"
        ),

        # ─── Patient Rights ───
        "rights_title": "⚖️ حقوق شما به عنوان بیمار\n━━━━━━━━━━━━━━━",
        "rights_body": (
            "1️⃣ دریافت اطلاعات کامل\n"
            "2️⃣ حق انتخاب پزشک\n"
            "3️⃣ محرمانه بودن اطلاعات\n"
            "4️⃣ رضایت آگاهانه\n"
            "5️⃣ دریافت نسخه\n"
            "6️⃣ حق شکایت\n"
            "7️⃣ احترام بدون تبعیض\n"
            "8️⃣ دسترسی به پرونده\n\n"
            "📞 @ShirazMedBot\n"
            "- نظام پزشکی\n"
            "- وزارت بهداشت: 190"
        ),

        # ─── Medication reminder ───
        "med_menu": (
            "⏰ یادآور دارو\n\n"
            "1️⃣ افزودن یادآور جدید\n"
            "2️⃣ مشاهده‌ی یادآورها\n"
            "3️⃣ انصراف"
        ),
        "med_ask_name": "💊 اسم دارو:",
        "med_ask_time": "⏰ ساعت؟ (مثال: 08:00)",
        "med_saved": "✅ یادآور ثبت شد\n\n💊 {name}\n⏰ {time}",
        "med_none": "هنوز یادآوری ثبت نکردی. بنویس: دارو",

        # ─── Food guide ───
        "food_title": "🍏 راهنمای تغذیه و تداخلات\n━━━━━━━━━━━━━━━",
        "food_body": (
            "🔴 تداخل‌های مهم:\n\n"
            "• آنتی‌بیوتیک + لبنیات (۲ ساعت)\n"
            "• آهن + چای/قهوه (۱ ساعت)\n"
            "• وارفارین + کلم و اسفناج\n"
            "• تیروئید + صبح ناشتا\n"
            "• مسکن + معده خالی (ممنوع)\n\n"
            "💧 آب زیاد\n"
            "🥗 میوه و سبزیجات\n"
            "🚫 خوددرمانی نکن\n\n"
            "⚠️ راهنمای کلیه، نه جایگزین پزشک."
        ),

        # ─── Menu ───
        "menu_main": "📋 منوی شیراز مدیکال\n\n👇 یکی رو انتخاب کن:",
        "ai_unavailable": "🙏 الان نمی‌تونم پاسخ بدم.\n\nبنویسید: منو",

        # ─── Paramedical / Elderly / Package ───
        "para_list_title": "🏥 خدمات پیراپزشکی\n\n👇 انتخاب کن:",
        "elderly_list_title": "🏡 خانه‌های سالمندان شیراز",
        "elderly_all_title": "🏡 خانه‌های سالمندان شیراز:",
        "package_title": "💎 پکیج کامل درمان و اقامت\n━━━━━━━━━━━━━━━",
        "package_pitch": (
            "🎯 یه پیام بده، همه‌چیز رو آماده می‌کنیم.\n\n"
            "از لحظه‌ای که وارد شیراز می‌شی تا لحظه‌ای که با سلامتی برمی‌گردی، ما کنارتیم."
        ),
        "package_value": (
            "📦 چی توی این پکیج هست:\n\n"
            "👨‍⚕️ ویزیت پزشک متخصص\n"
            "🏨 اقامت در هتل\n"
            "🚗 ترانسفر فرودگاه و شهر\n"
            "🗣️ مترجم همراه\n"
            "🏛️ گشت گردشگری شیراز\n"
            "📋 پرونده‌ی سلامت شخصی\n"
            "💊 یادآور دارو و پیگیری\n"
            "🤝 همراه اختصاصی\n"
            "💙 پشتیبانی ۲۴ ساعته"
        ),
        "package_cta": "🎁 همه‌ی این‌ها با یک پیام.\n\n👇 برای دریافت قیمت:",
        "package_ask_name": "👤 نام و نام خانوادگی:",
        "package_ask_phone": "📞 شماره تماس:",
        "package_saved": (
            "✅ درخواست پکیج ثبت شد\n\n"
            "📋 کد: {id}\n\n"
            "تیم ما در کمتر از ۲۴ ساعت تماس می‌گیره.\n\n"
            "💙 با آرزوی سلامتی"
        ),
        "package_admin_new": (
            "💎 درخواست پکیج جدید\n\n"
            "📋 {id}\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "ChatID: {cid}"
        ),

        # ─── Section titles ───
        "docs_list_title": "👨‍⚕️ کدام تخصص؟\n\n👇 انتخاب کن:",
        "nonmed_list_title": "🏥 کدام خدمت؟\n\n👇 انتخاب کن:",
        "tourist_list_title": "🏛️ کدام بخش گردشگری؟\n\n👇 انتخاب کن:",
        "pkg_ask_title": "💎 پکیج کامل",
        "hubs_title": "🚉 پایانه‌ها و فرودگاه‌های شیراز\n\n👇 کدوم رو می‌خوای ببینی؟",
    },

    "ar": {
        # ─── Referral ───
        "ref_your_code": "🔗 كود الإحالة: {code}\n\n{link}",
        "ref_your_stats": "👥 المدعوون: {count}\n🎁 المكافآت: {rewards}",
        "ref_new_from": "🎉 انضم أحد بكود {code}!\n\nمكافأة: خصم ١٠٪ 🌹",
        "ref_welcome_new": "🎉 أهلاً بك!\n\nبكود {code}.\n🎁 خصم ٥٪ على أول زيارة",
        "ref_invite_msg": (
            "🌟 ادعُ صديقك\n\n"
            "الكود: {code}\n\n"
            "{link}\n\n"
            "🎁 لك: خصم ١٠٪\n"
            "🎁 لصديقك: خصم ٥٪"
        ),

        # ─── Hope ───
        "hope_night": "🌙 مساء الخير\n\n💊 لا تنسوا تناول أدويتكم.\n🌷 نحن معكم.",
        "hope_stage_request": "🌟 خطوتك الأولى!\n\nنحن بجانبك.",
        "hope_stage_doctor": "👨‍⚕️ تم تعيين طبيبك المتخصص 🌷",
        "hope_stage_date": "🎉 تم تأكيد تاريخ موعدك!\n\nخطوة أخرى نحو الشفاء 💙",
        "hope_stage_accommodation": "🏨 تم ترتيب إقامتك 🌷",
        "hope_stage_transport": "🚗 تم ترتيب مواصلاتك 💙",
        "hope_stage_treatment": "🌸 تم علاجك. نتمنى لك الشفاء العاجل.",
        "hope_stage_followup": "🌷 ما زلنا معكم 💙",
        "hope_general_1": "💙 «الصحة أكبر ثروة.»",
        "hope_general_2": "🌷 «كل يوم فرصة للتحسن.»",
        "hope_general_3": "✨ «الأمل نصف العلاج.»",
        "hope_general_4": "🌸 «لست وحدك. نحن معك.»",

        # ─── Companion ───
        "comp_ask": "👥 هل لديكم مرافق؟ (نعم / لا)",
        "comp_ask_name": "👤 اسم المرافق:",
        "comp_ask_phone": "📞 رقم المرافق:",
        "comp_saved": "✅ تم تسجيل المرافق\n\n👤 {name}\n📞 {phone}",
        "comp_skip": "حسناً، اكتبوا: مرافق",

        # ─── SOS ───
        "sos_menu": (
            "🚨 حالة طارئة\n\n"
            "1️⃣ الطوارئ ١١٥\n"
            "2️⃣ أقرب مستشفى\n"
            "3️⃣ الإسعافات الأولية\n"
            "4️⃣ إبلاغ مرافقي\n"
            "5️⃣ إلغاء"
        ),
        "sos_115": "🚑 الطوارئ: ١١٥\n\nاتصلوا وأخبروا بالعنوان.",
        "sos_first_aid": (
            "🩺 الإسعافات الأولية\n\n"
            "🔹 ألم الصدر:\n"
            "- اجلس واسترح\n"
            "- حبة تحت اللسان\n"
            "- اتصل بـ ١١٥\n\n"
            "🔹 نزيف:\n"
            "- ضغط مباشر\n"
            "- ١١٥\n\n"
            "🔹 ضيق التنفس:\n"
            "- اجلس مستقيماً\n"
            "- ١١٥\n\n"
            "⚠️ هذا ليس بديلاً عن الطبيب."
        ),
        "sos_no_companion": "❌ لم تسجل مرافقاً. اكتبوا: مرافق",

        # ─── Complaint ───
        "comp_voice_menu": (
            "📩 صوتك\n\n"
            "1️⃣ شكوى من الطبيب\n"
            "2️⃣ شكوى من المركز الطبي\n"
            "3️⃣ شكوى من الإقامة\n"
            "4️⃣ شكوى من النقل\n"
            "5️⃣ شكوى عامة\n"
            "6️⃣ إلغاء"
        ),
        "comp_voice_text": "📝 اكتبوا رسالتكم:",
        "comp_voice_saved": "✅ تم تسجيل رسالتكم\n\n📋 {id}\n\nسنتابع 💙",
        "comp_voice_skip": "حسناً، اكتبوا: شكوى",
        "comp_voice_admin": (
            "📩 شكوى جديدة\n\n"
            "📋 {id}\n"
            "الفئة: {category}\n"
            "الاسم: {name}\n"
            "ChatID: {cid}\n\n"
            "{text}"
        ),

        # ─── Patient Rights ───
        "rights_title": "⚖️ حقوق المريض\n━━━━━━━━━━━━━━━",
        "rights_body": (
            "1️⃣ الحصول على معلومات كاملة\n"
            "2️⃣ حق اختيار الطبيب\n"
            "3️⃣ سرية المعلومات\n"
            "4️⃣ الموافقة المستنيرة\n"
            "5️⃣ استلام الوصفة\n"
            "6️⃣ حق الشكوى\n"
            "7️⃣ احترام بدون تمييز\n"
            "8️⃣ الوصول إلى الملف\n\n"
            "📞 @ShirazMedBot\n"
            "- النقابة الطبية\n"
            "- وزارة الصحة: 190"
        ),

        # ─── Medication ───
        "med_menu": (
            "⏰ تذكير الدواء\n\n"
            "1️⃣ إضافة تذكير جديد\n"
            "2️⃣ عرض التذكيرات\n"
            "3️⃣ إلغاء"
        ),
        "med_ask_name": "💊 اسم الدواء:",
        "med_ask_time": "⏰ الساعة؟ (مثال: 08:00)",
        "med_saved": "✅ تم التسجيل\n\n💊 {name}\n⏰ {time}",
        "med_none": "لا تذكيرات. اكتبوا: دواء",

        # ─── Food ───
        "food_title": "🍏 دليل التغذية والتداخلات\n━━━━━━━━━━━━━━━",
        "food_body": (
            "🔴 تداخلات مهمة:\n\n"
            "• مضاد حيوي + حليب (ساعتان)\n"
            "• حديد + شاي/قهوة (ساعة)\n"
            "• وارفارين + ملفوف وسبانخ\n"
            "• الغدة الدرقية + صباحاً على الريق\n"
            "• مسكن + معدة فارغة (ممنوع)\n\n"
            "💧 ماء كثير\n"
            "🥗 فواكه وخضروات\n"
            "🚫 لا تعالج نفسك\n\n"
            "⚠️ إرشاد عام، ليس بديلاً عن الطبيب."
        ),

        # ─── Menu ───
        "menu_main": "📋 قائمة شيراز ميديكال\n\n👇 اختر:",
        "ai_unavailable": "🙏 لا أستطيع الرد الآن.\n\nاكتبوا: قائمة",

        # ─── Paramedical / Elderly / Package ───
        "para_list_title": "🏥 الخدمات المساعدة\n\n👇 اختر:",
        "elderly_list_title": "🏡 دور المسنين في شيراز",
        "elderly_all_title": "🏡 دور المسنين:",
        "package_title": "💎 الباكج الكامل\n━━━━━━━━━━━━━━━",
        "package_pitch": (
            "🎯 رسالة واحدة ونجهز كل شيء.\n\n"
            "من لحظة وصولك حتى مغادرتك بسلامة، نحن معك."
        ),
        "package_value": (
            "📦 يشمل:\n\n"
            "👨‍⚕️ زيارة طبيب متخصص\n"
            "🏨 الإقامة في فندق\n"
            "🚗 نقل المطار والمدينة\n"
            "🗣️ مترجم مرافق\n"
            "🏛️ جولة سياحية في شيراز\n"
            "📋 ملف صحي شخصي\n"
            "💊 تذكير بالأدوية والمتابعة\n"
            "🤝 مرافق مخصص\n"
            "💙 دعم على مدار ٢٤ ساعة"
        ),
        "package_cta": "🎁 كل هذا برسالة واحدة.\n\n👇 لاستلام السعر:",
        "package_ask_name": "👤 الاسم الكامل:",
        "package_ask_phone": "📞 رقم الهاتف:",
        "package_saved": (
            "✅ تم تسجيل الطلب\n\n"
            "📋 {id}\n\n"
            "سنتصل بك خلال ٢٤ ساعة.\n\n"
            "💙 مع تمنياتنا بالشفاء"
        ),
        "package_admin_new": (
            "💎 طلب باكج جديد\n\n"
            "📋 {id}\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "ChatID: {cid}"
        ),

        # ─── Section titles ───
        "docs_list_title": "👨‍⚕️ أي تخصص؟\n\n👇 اختر:",
        "nonmed_list_title": "🏥 أي خدمة؟\n\n👇 اختر:",
        "tourist_list_title": "🏛️ أي قسم سياحي؟\n\n👇 اختر:",
        "pkg_ask_title": "💎 الباكج الكامل",
        "hubs_title": "🚉 محطات ومطارات شيراز\n\n👇 اختر:",
    },

    "en": {
        # ─── Referral ───
        "ref_your_code": "🔗 Your referral code: {code}\n\nLink:\n{link}",
        "ref_your_stats": "👥 Invited: {count}\n🎁 Rewards: {rewards}",
        "ref_new_from": "🎉 Someone joined with code {code}!\n\nReward: 10% discount 🌹",
        "ref_welcome_new": "🎉 Welcome!\n\nWith code {code}.\n🎁 5% off your first visit",
        "ref_invite_msg": (
            "🌟 Invite a friend\n\n"
            "Code: {code}\n\n"
            "{link}\n\n"
            "🎁 You: 10% off\n"
            "🎁 Your friend: 5% off"
        ),

        # ─── Hope ───
        "hope_night": "🌙 Good night\n\n💊 Don't forget your medication.\n🌷 We're here with you.",
        "hope_stage_request": "🌟 You took your first step!\n\nWe're with you to make your journey easier.",
        "hope_stage_doctor": "👨‍⚕️ Your specialist was assigned 🌷",
        "hope_stage_date": "🎉 Your appointment date is confirmed!\n\nOne step closer to health 💙",
        "hope_stage_accommodation": "🏨 Your accommodation is arranged 🌷",
        "hope_stage_transport": "🚗 Your transport is ready 💙",
        "hope_stage_treatment": "🌸 Your treatment is done. Get better every day.",
        "hope_stage_followup": "🌷 We're still with you 💙",
        "hope_general_1": "💙 \"Health is the greatest wealth.\"",
        "hope_general_2": "🌷 \"Every day is a chance to improve.\"",
        "hope_general_3": "✨ \"Hope is half the cure.\"",
        "hope_general_4": "🌸 \"You're not alone. We're with you.\"",

        # ─── Companion ───
        "comp_ask": "👥 Do you have a companion? (Yes / No)",
        "comp_ask_name": "👤 Companion's name:",
        "comp_ask_phone": "📞 Companion's phone:",
        "comp_saved": "✅ Companion saved\n\n👤 {name}\n📞 {phone}",
        "comp_skip": "Okay, write: companion",

        # ─── SOS ───
        "sos_menu": (
            "🚨 Emergency\n\n"
            "1️⃣ Ambulance 115\n"
            "2️⃣ Nearest hospital\n"
            "3️⃣ First aid guide\n"
            "4️⃣ Notify my companion\n"
            "5️⃣ Cancel"
        ),
        "sos_115": "🚑 Emergency: 115\n\nPlease call and give your exact address.",
        "sos_first_aid": (
            "🩺 First Aid\n\n"
            "🔹 Chest pain:\n"
            "- Sit and rest\n"
            "- Sublingual tablet\n"
            "- Call 115\n\n"
            "🔹 Bleeding:\n"
            "- Direct pressure\n"
            "- 115\n\n"
            "🔹 Shortness of breath:\n"
            "- Sit upright\n"
            "- 115\n\n"
            "⚠️ Not a substitute for a doctor."
        ),
        "sos_no_companion": "❌ No companion registered. Write: companion",

        # ─── Complaint ───
        "comp_voice_menu": (
            "📩 Your Voice\n\n"
            "1️⃣ Doctor complaint\n"
            "2️⃣ Center complaint\n"
            "3️⃣ Accommodation complaint\n"
            "4️⃣ Transport complaint\n"
            "5️⃣ General complaint\n"
            "6️⃣ Cancel"
        ),
        "comp_voice_text": "📝 Write your message:",
        "comp_voice_saved": "✅ Message saved\n\n📋 {id}\n\nWe'll follow up 💙",
        "comp_voice_skip": "Okay, write: complaint",
        "comp_voice_admin": (
            "📩 New complaint\n\n"
            "📋 {id}\n"
            "Category: {category}\n"
            "Name: {name}\n"
            "ChatID: {cid}\n\n"
            "{text}"
        ),

        # ─── Patient Rights ───
        "rights_title": "⚖️ Patient Rights\n━━━━━━━━━━━━━━━",
        "rights_body": (
            "1️⃣ Receive full information\n"
            "2️⃣ Right to choose doctor\n"
            "3️⃣ Confidentiality\n"
            "4️⃣ Informed consent\n"
            "5️⃣ Receive prescription\n"
            "6️⃣ Right to complain\n"
            "7️⃣ Respect without discrimination\n"
            "8️⃣ Access to your file\n\n"
            "📞 @ShirazMedBot\n"
            "- Medical Council\n"
            "- Health Ministry: 190"
        ),

        # ─── Medication ───
        "med_menu": (
            "⏰ Medication reminder\n\n"
            "1️⃣ Add new reminder\n"
            "2️⃣ View reminders\n"
            "3️⃣ Cancel"
        ),
        "med_ask_name": "💊 Medication name:",
        "med_ask_time": "⏰ Time? (e.g. 08:00)",
        "med_saved": "✅ Reminder saved\n\n💊 {name}\n⏰ {time}",
        "med_none": "No reminders yet. Write: med",

        # ─── Food ───
        "food_title": "🍏 Nutrition & Interactions Guide\n━━━━━━━━━━━━━━━",
        "food_body": (
            "🔴 Key interactions:\n\n"
            "• Antibiotic + dairy (2 hours)\n"
            "• Iron + tea/coffee (1 hour)\n"
            "• Warfarin + cabbage and spinach\n"
            "• Thyroid + morning empty stomach\n"
            "• Painkiller + empty stomach (avoid)\n\n"
            "💧 Drink water\n"
            "🥗 Fruits and vegetables\n"
            "🚫 Don't self-medicate\n\n"
            "⚠️ General guide, not a substitute for a doctor."
        ),

        # ─── Menu ───
        "menu_main": "📋 Shiraz Medical Menu\n\n👇 Choose one:",
        "ai_unavailable": "🙏 Can't respond now.\n\nWrite: menu",

        # ─── Paramedical / Elderly / Package ───
        "para_list_title": "🏥 Paramedical Services\n\n👇 Choose:",
        "elderly_list_title": "🏡 Nursing Homes in Shiraz",
        "elderly_all_title": "🏡 Nursing Homes:",
        "package_title": "💎 Complete Package\n━━━━━━━━━━━━━━━",
        "package_pitch": (
            "🎯 One message, we prepare everything.\n\n"
            "From the moment you arrive until you leave in good health, we're with you."
        ),
        "package_value": (
            "📦 Package includes:\n\n"
            "👨‍⚕️ Specialist consultation\n"
            "🏨 Hotel accommodation\n"
            "🚗 Airport and city transfer\n"
            "🗣️ Companion translator\n"
            "🏛️ Shiraz city tour\n"
            "📋 Personal health file\n"
            "💊 Medication reminders and follow-up\n"
            "🤝 Dedicated companion\n"
            "💙 24/7 support"
        ),
        "package_cta": "🎁 All this with one message.\n\n👇 To get the price:",
        "package_ask_name": "👤 Full name:",
        "package_ask_phone": "📞 Phone number:",
        "package_saved": (
            "✅ Package request saved\n\n"
            "📋 {id}\n\n"
            "Our team will contact you within 24 hours.\n\n"
            "💙 Wishing you good health"
        ),
        "package_admin_new": (
            "💎 New package request\n\n"
            "📋 {id}\n"
            "👤 {name}\n"
            "📞 {phone}\n"
            "ChatID: {cid}"
        ),

        # ─── Section titles ───
        "docs_list_title": "👨‍⚕️ Which specialty?\n\n👇 Choose:",
        "nonmed_list_title": "🏥 Which service?\n\n👇 Choose:",
        "tourist_list_title": "🏛️ Which tourist section?\n\n👇 Choose:",
        "pkg_ask_title": "💎 Complete Package",
        "hubs_title": "🚉 Shiraz Transport Hubs\n\n👇 Choose:",
    },
}

# ═══════════════════════════════════════════════
# MSG_BTN — Inline keyboard buttons
# ═══════════════════════════════════════════════

MSG_BTN = {
    "fa": {
        # Main menu
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

        # Taxi
        "btn_taxi": "🚕 درخواست تاکسی",
        "btn_snapp": "🚗 اسنپ",
        "btn_tap30": "🚕 تپسی",

        # Hubs
        "btn_hubs": "🚉 پایانه‌ها و فرودگاه",
        "btn_back_hubs": "🔙 بازگشت به لیست پایانه‌ها",

        # Insurance
        "btn_insurance": "🏥 بیمه‌های تحت پوشش",
        "btn_back_insurance": "🔙 بازگشت به لیست بیمه‌ها",

        # Translator
        "btn_translator": "🗣️ مترجم همراه",
        "btn_tr_fa_ar": "🇮🇷 فارسی → 🇸🇦 عربی",
        "btn_tr_ar_fa": "🇸🇦 عربی → 🇮🇷 فارسی",
        "btn_tr_fa_en": "🇮🇷 فارسی → 🇬🇧 انگلیسی",
        "btn_tr_en_fa": "🇬🇧 انگلیسی → 🇮🇷 فارسی",

        # Charter / DeepSeek
        "btn_charter": "📜 منشور اخلاقی",
        "btn_deepseek": "🤖 هوش مصنوعی DeepSeek",
        "btn_deepseek_go": "🚀 رفتن به DeepSeek",

        # Back
        "btn_back": "🔙 بازگشت",

        # Non-medical
        "btn_hospitals": "🏥 بیمارستان‌ها",
        "btn_hotels": "🏨 هتل‌ها",
        "btn_motels": "🛏️ مهمان‌پذیر",
        "btn_houses": "🏠 خانه مسافر",
        "btn_transport": "🚗 حمل‌ونقل",

        # Tourism
        "btn_city": "🏛️ جاذبه‌های شهری",
        "btn_outside": "🏞️ خارج از شهر",

        # Paramedical
        "btn_physio": "🦴 فیزیوتراپی",
        "btn_lab": "🔬 آزمایشگاه",
        "btn_radiology": "📷 رادیولوژی",
        "btn_nursing": "👩‍⚕️ پرستاری",
        "btn_injection": "💉 تزریق",
        "btn_trad_med": "🌿 طب سنتی",
        "btn_occupational": "🧩 کاردرمانی",
        "btn_speech": "🗣️ گفتاردرمانی",
        "btn_orthotics": "🦿 پروتز",

        # Elderly
        "btn_elder_all": "🏡 همه خانه‌های سالمندان",

        # Package
        "btn_pkg_order": "💎 سفارش پکیج",

        # Doctor actions
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
        "btn_back_hubs": "🔙 العودة إلى قائمة المحطات",

        "btn_insurance": "🏥 التأمينات المدعومة",
        "btn_back_insurance": "🔙 العودة إلى قائمة التأمينات",

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
        "btn_houses": "🏠 بيوت مسافر",
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
        "btn_back_hubs": "🔙 Back to Hubs List",

        "btn_insurance": "🏥 Supported Insurances",
        "btn_back_insurance": "🔙 Back to Insurances List",

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

# ═══════════════════════════════════════════════
# INSURANCE FIELDS ORDER + LABELS
# ═══════════════════════════════════════════════

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

# ═══════════════════════════════════════════════
# FIELD NAMES (generic item formatting)
# ═══════════════════════════════════════════════

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

print("═══ PART 3/6 LOADED ═══ MSG_BTN + MSG_CH + MSG2 + Labels ready")
# ═══════════════════════════════════════════════
# GENERIC JSON HELPERS
# ═══════════════════════════════════════════════

def load_json(path: str):
    """Load a JSON file. Returns list (if top-level is list or dict with first list value) or {}."""
    try:
        full = path if os.path.isabs(path) else os.path.join(DATA_DIR, path)
        with open(full, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []
    except Exception as e:
        print("LOAD_JSON_ERR:", path, str(e))
        return []


def _load_default(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path: str, data) -> bool:
    try:
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print("SAVE_ERR:", path, str(e))
        return False


# ═══════════════════════════════════════════════
# UNIVERSAL GETTERS (i18n fields)
# ═══════════════════════════════════════════════

def get_value(item: dict, key: str, lang: str):
    """Fetch field with multilingual fallback: lang -> fa -> en -> ar."""
    if not isinstance(item, dict):
        return None
    if key in item:
        v = item[key]
        if isinstance(v, dict):
            for L in (lang, "fa", "en", "ar"):
                if L in v and v[L]:
                    return v[L]
            return None
        return v
    alt = key + "_" + lang
    if alt in item:
        return item[alt]
    if key + "_fa" in item:
        return item[key + "_fa"]
    return None


def get_price(item: dict, lang: str) -> str:
    p = item.get("price_range", "") or item.get("price_range_toman", "")
    if not p:
        return ""
    if isinstance(p, dict):
        return p.get(lang, p.get("fa", "")) or ""
    if p in PRICE_MAP:
        return PRICE_MAP[p].get(lang, p)
    return str(p)


def item_name_for_search(item: dict) -> str:
    for k in ("name_fa", "name_ar", "name_en", "name"):
        if k in item:
            v = item[k]
            if isinstance(v, dict):
                return v.get("fa", "") or v.get("en", "") or v.get("ar", "") or ""
            if v:
                return str(v)
    return ""


# ═══════════════════════════════════════════════
# SPECIALTY MAP BUILDER (from SPECIALTY_LIST)
# ═══════════════════════════════════════════════

def _build_specialty_map():
    for row in SPECIALTY_LIST:
        fn = row[0]
        keywords = row[1:]
        # skip the 3 descriptive labels (fa/ar/en) — they are row[1], row[2], row[3]
        for kw in row[4:]:
            if kw:
                SPECIALTY_MAP[str(kw).lower()] = fn


_build_specialty_map()
print("SPECIALTY_MAP built:", len(SPECIALTY_MAP), "keys")


# ═══════════════════════════════════════════════
# APPOINTMENTS
# ═══════════════════════════════════════════════

def load_appointments():
    return _load_default(APPOINTMENTS_FILE, {"next_id": 1001, "appointments": []})


def save_appointments(data) -> bool:
    return _save(APPOINTMENTS_FILE, data)


def create_appointment(doctor: dict, pname: str, pphone: str, chat_id: int, lang: str,
                       national_id: str = "", office: str = "",
                       insurance_id: str = "", insurance_name: str = "",
                       amount: int = 0, payment_type: str = "full",
                       priority: str = "normal",
                       date: str = "", time_str: str = "") -> dict:
    data = load_appointments()
    data.setdefault("next_id", 1001)
    apt_id = "APT-" + str(data["next_id"])
    data["next_id"] += 1

    apt = {
        "id": apt_id,
        "doctor_id": doctor.get("id", ""),
        "doctor_name_fa": get_value(doctor, "name", "fa") or "",
        "doctor_name_ar": get_value(doctor, "name", "ar") or "",
        "doctor_name_en": get_value(doctor, "name", "en") or "",
        "doctor_phone": doctor.get("phone", ""),
        "doctor_address_fa": get_value(doctor, "office_address", "fa") or get_value(doctor, "address", "fa") or "",
        "doctor_address_ar": get_value(doctor, "office_address", "ar") or get_value(doctor, "address", "ar") or "",
        "doctor_address_en": get_value(doctor, "office_address", "en") or get_value(doctor, "address", "en") or "",

        "patient_name": pname,
        "patient_phone": pphone,
        "patient_national_id": national_id,
        "patient_chat_id": str(chat_id),
        "patient_lang": lang,

        "office": office,
        "insurance_id": insurance_id,
        "insurance_name": insurance_name,
        "amount": int(amount or 0),
        "payment_type": payment_type,   # "full" | "insurance"
        "priority": priority,            # "normal" | "urgent"

        "date": date or "",
        "time": time_str or "",
        "status": "pending",             # pending | confirmed | done | cancelled
        "payment_status": "unpaid",      # unpaid | paid | refunded
        "payment_ref": "",
        "payment_id": "",

        "rating": 0,
        "reminded_1d": False,
        "reminded_2h": False,
        "invoice_sent": False,

        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }
    data["appointments"].append(apt)
    save_appointments(data)
    return apt


def get_patient_appointments(chat_id: int):
    data = load_appointments()
    return [a for a in data["appointments"] if a.get("patient_chat_id") == str(chat_id)]


def find_appointment(apt_id: str):
    data = load_appointments()
    for a in data["appointments"]:
        if a.get("id") == apt_id:
            return a
    return None


def update_appointment(apt_id: str, updates: dict):
    data = load_appointments()
    for a in data["appointments"]:
        if a.get("id") == apt_id:
            a.update(updates)
            save_appointments(data)
            return a
    return None


def confirm_appointment(apt_id: str, date_str: str, time_str: str):
    return update_appointment(apt_id, {
        "date": date_str,
        "time": time_str,
        "status": "confirmed",
        "confirmed_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "reminded_1d": False,
        "reminded_2h": False,
    })


def mark_apt_done(apt_id: str):
    return update_appointment(apt_id, {
        "status": "done",
        "done_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    })


def set_apt_rating(apt_id: str, stars: int):
    return update_appointment(apt_id, {
        "rating": int(stars),
        "rated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    })


def mark_reminded(apt_id: str, which: str) -> bool:
    a = update_appointment(apt_id, {which: True})
    return a is not None


def mark_apt_paid(apt_id: str, payment_ref: str, payment_id: str):
    return update_appointment(apt_id, {
        "payment_status": "paid",
        "payment_ref": payment_ref,
        "payment_id": payment_id,
        "paid_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    })


# ═══════════════════════════════════════════════
# PATIENTS (health file PT-XXXX)
# ═══════════════════════════════════════════════

def load_patients():
    return _load_default(PATIENTS_FILE, {"patients": []})


def save_patients(data) -> bool:
    return _save(PATIENTS_FILE, data)


def get_patient_by_chat(chat_id: int):
    data = load_patients()
    for p in data["patients"]:
        if p.get("chat_id") == str(chat_id) and p.get("type", "patient") == "patient":
            return p
    return None


def get_patient_by_code(code: str):
    data = load_patients()
    for p in data["patients"]:
        if p.get("code") == code:
            return p
    return None


def next_patient_code() -> str:
    data = load_patients()
    max_num = 1000
    for p in data["patients"]:
        m = re.match(r"PT-(\d+)", p.get("code", ""))
        if m:
            try:
                n = int(m.group(1))
                if n > max_num:
                    max_num = n
            except Exception:
                pass
    return "PT-" + str(max_num + 1)


def create_or_get_patient(chat_id: int, name: str, phone: str, lang: str) -> dict:
    data = load_patients()
    for p in data["patients"]:
        if p.get("chat_id") == str(chat_id) and p.get("type", "patient") == "patient":
            changed = False
            if name and not p.get("name"):
                p["name"] = name
                changed = True
            if phone and not p.get("phone"):
                p["phone"] = phone
                changed = True
            if lang and not p.get("lang"):
                p["lang"] = lang
                changed = True
            if changed:
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
            "accommodation": False, "transport": False,
            "treatment": False, "followup": False,
        },
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }
    data["patients"].append(p)
    save_patients(data)
    return p


def update_patient_stage(chat_id, stage: str, value: bool = True) -> bool:
    data = load_patients()
    for p in data["patients"]:
        if p.get("chat_id") == str(chat_id) and p.get("type", "patient") == "patient":
            p.setdefault("stages", {})
            p["stages"][stage] = value
            save_patients(data)
            return True
    return False


def add_appointment_to_patient(chat_id, apt_id: str) -> bool:
    data = load_patients()
    for p in data["patients"]:
        if p.get("chat_id") == str(chat_id) and p.get("type", "patient") == "patient":
            p.setdefault("appointments", [])
            if apt_id not in p["appointments"]:
                p["appointments"].append(apt_id)
            save_patients(data)
            return True
    return False


def format_patient_file(patient, lang: str) -> str:
    if not patient:
        return MSG[lang]["pt_not_found"]
    m = MSG[lang]
    lines = [m["pt_title"]]
    lines.append(m["pt_code"].format(code=patient.get("code", "")))
    if patient.get("name"):
        lines.append(m["pt_name"].format(name=patient["name"]))
    lines.append(m["pt_progress"])

    stages = patient.get("stages", {})
    for s in ["request", "doctor", "date", "accommodation", "transport", "treatment", "followup"]:
        stage_name = m.get("pt_stages_" + s, s)
        if stages.get(s):
            lines.append(m["pt_stage_done"].format(stage=stage_name))
        else:
            lines.append(m["pt_stage_wait"].format(stage=stage_name))

    apts = patient.get("appointments", [])
    if apts:
        lines.append(m["pt_appointments"])
        for aid in apts:
            apt = find_appointment(aid)
            if not apt:
                continue
            dn = apt.get("doctor_name_" + lang) or apt.get("doctor_name_fa", "")
            st = apt.get("status", "pending")
            if st == "done":
                lines.append(m["pt_apt_line_done"].format(id=apt["id"], doctor=dn))
            elif st == "confirmed" and apt.get("date"):
                lines.append(m["pt_apt_line_confirmed"].format(
                    id=apt["id"], doctor=dn,
                    date=apt["date"], time=apt.get("time", ""),
                ))
            else:
                lines.append(m["pt_apt_line_pending"].format(id=apt["id"], doctor=dn))

    hope = random.choice([
        MSG2[lang]["hope_general_1"],
        MSG2[lang]["hope_general_2"],
        MSG2[lang]["hope_general_3"],
        MSG2[lang]["hope_general_4"],
    ])
    lines.append(hope)
    return "\n".join(lines)


def delete_patient_data(chat_id) -> bool:
    cid = str(chat_id)

    pats = load_patients()
    pats["patients"] = [p for p in pats["patients"] if p.get("chat_id") != cid]
    save_patients(pats)

    apts = load_appointments()
    apts["appointments"] = [a for a in apts["appointments"] if a.get("patient_chat_id") != cid]
    save_appointments(apts)

    comps = _load_default(COMPANIONS_FILE, {"companions": {}})
    comps.setdefault("companions", {})
    if cid in comps["companions"]:
        del comps["companions"][cid]
        _save(COMPANIONS_FILE, comps)

    meds = _load_default(MEDS_FILE, {"meds": []})
    meds["meds"] = [m for m in meds.get("meds", []) if m.get("chat_id") != cid]
    _save(MEDS_FILE, meds)

    pays = _load_default(PAYMENTS_FILE, {"payments": []})
    pays["payments"] = [p for p in pays.get("payments", []) if p.get("chat_id") != cid]
    _save(PAYMENTS_FILE, pays)

    return True


# ═══════════════════════════════════════════════
# REFERRALS
# ═══════════════════════════════════════════════

def load_referrals():
    return _load_default(REFERRALS_FILE, {"users": {}, "codes": {}})


def save_referrals(data) -> bool:
    return _save(REFERRALS_FILE, data)


def next_ref_code() -> str:
    data = load_referrals()
    max_num = 100
    for code in data.get("codes", {}).keys():
        m = re.match(r"REF-A?(\d+)", code)
        if m:
            try:
                n = int(m.group(1))
                if n > max_num:
                    max_num = n
            except Exception:
                pass
    return "REF-A" + str(max_num + 1)


def get_or_create_referral_code(chat_id) -> str:
    data = load_referrals()
    cid = str(chat_id)
    if cid in data["users"] and data["users"][cid].get("code"):
        return data["users"][cid]["code"]

    code = next_ref_code()
    data["users"].setdefault(cid, {})
    data["users"][cid]["code"] = code
    data["users"][cid].setdefault("count", 0)
    data["users"][cid].setdefault("rewards", [])
    data["codes"][code] = cid
    save_referrals(data)
    return code


def apply_referral(new_chat_id, ref_code: str):
    data = load_referrals()
    ncid = str(new_chat_id)
    ref_code = ref_code.upper()

    if ncid in data["users"] and data["users"][ncid].get("referred_by"):
        return None

    inviter = data["codes"].get(ref_code)
    if not inviter or inviter == ncid:
        return None

    data["users"].setdefault(ncid, {})
    data["users"][ncid]["referred_by"] = ref_code
    data["users"][ncid]["reward"] = "5%"

    data["users"].setdefault(inviter, {})
    data["users"][inviter]["count"] = data["users"][inviter].get("count", 0) + 1
    data["users"][inviter].setdefault("rewards", [])
    data["users"][inviter]["rewards"].append("10%")

    save_referrals(data)
    return {"inviter": inviter, "inviter_code": ref_code}


def get_referral_stats(chat_id):
    data = load_referrals()
    cid = str(chat_id)
    if cid not in data["users"]:
        return {"code": "", "count": 0, "rewards": []}
    u = data["users"][cid]
    return {
        "code": u.get("code", ""),
        "count": u.get("count", 0),
        "rewards": u.get("rewards", []),
    }


def build_referral_link(code: str) -> str:
    return "https://ble.ir/" + BOT_USERNAME + "?start=" + code


def try_apply_start_param(message, text: str, lang: str):
    if not text:
        return None
    m = re.match(r"^/start\s+(REF-A?\d+)", text.strip(), re.IGNORECASE)
    if not m:
        return None
    code = m.group(1).upper()
    res = apply_referral(message.chat.id, code)
    if res:
        try:
            bot.send_message(message.chat.id,
                             MSG2[lang]["ref_welcome_new"].format(code=code))
            bot.send_message(res["inviter"],
                             MSG2[lang]["ref_new_from"].format(code=code))
        except Exception as e:
            print("REF_NOTIFY_ERR:", str(e))
    return res


# ═══════════════════════════════════════════════
# CHANNEL REWARD
# ═══════════════════════════════════════════════

def is_channel_joined(chat_id) -> bool:
    data = load_referrals()
    cid = str(chat_id)
    return data["users"].get(cid, {}).get("channel_reward", False)


def grant_channel_reward(chat_id) -> bool:
    data = load_referrals()
    cid = str(chat_id)
    data["users"].setdefault(cid, {})
    if data["users"][cid].get("channel_reward"):
        return False
    data["users"][cid]["channel_reward"] = True
    data["users"][cid]["channel_discount"] = CHANNEL_DISCOUNT
    data["users"][cid]["channel_joined_at"] = datetime.now().strftime("%Y/%m/%d %H:%M")
    save_referrals(data)
    return True


# ═══════════════════════════════════════════════
# COMPANIONS
# ═══════════════════════════════════════════════

def load_companions():
    return _load_default(COMPANIONS_FILE, {"companions": {}})


def save_companions(data) -> bool:
    return _save(COMPANIONS_FILE, data)


def set_companion(chat_id, name: str, phone: str) -> bool:
    data = load_companions()
    data.setdefault("companions", {})
    data["companions"][str(chat_id)] = {"name": name, "phone": phone}
    save_companions(data)
    return True


def get_companion(chat_id):
    data = load_companions()
    return data.get("companions", {}).get(str(chat_id))


# ═══════════════════════════════════════════════
# USERS (stats)
# ═══════════════════════════════════════════════

def load_users():
    return _load_default(USERS_FILE, {"users": {}, "start_count": 0, "apt_count": 0})


def save_users(data) -> bool:
    return _save(USERS_FILE, data)


def register_user(chat_id, lang: str):
    data = load_users()
    cid = str(chat_id)
    today = datetime.now().strftime("%Y/%m/%d")
    if cid not in data["users"]:
        data["users"][cid] = {
            "first_seen": today,
            "last_seen": today,
            "lang": lang,
            "interactions": 1,
            "appointments": 0,
        }
        data["start_count"] = data.get("start_count", 0) + 1
    else:
        data["users"][cid]["last_seen"] = today
        data["users"][cid]["lang"] = lang
        data["users"][cid]["interactions"] = data["users"][cid].get("interactions", 0) + 1
    save_users(data)


def register_appointment_for_stats(chat_id):
    data = load_users()
    cid = str(chat_id)
    if cid in data["users"]:
        data["users"][cid]["appointments"] = data["users"][cid].get("appointments", 0) + 1
    data["apt_count"] = data.get("apt_count", 0) + 1
    save_users(data)


def get_user_stats():
    data = load_users()
    users = data.get("users", {})
    now = datetime.now()
    today_str = now.strftime("%Y/%m/%d")
    seven_days_ago = (now - timedelta(days=7)).strftime("%Y/%m/%d")
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y/%m/%d")

    total = len(users)
    dau = wau = mau = 0
    for u in users.values():
        ls = u.get("last_seen", "")
        if ls == today_str:
            dau += 1
        if ls >= seven_days_ago:
            wau += 1
        if ls >= thirty_days_ago:
            mau += 1

    starts = data.get("start_count", 0)
    apts = data.get("apt_count", 0)
    conv = round((apts / starts) * 100, 1) if starts > 0 else 0.0

    ref_data = load_referrals()
    channel_count = sum(
        1 for u in ref_data.get("users", {}).values() if u.get("channel_reward")
    )

    return {
        "total": total,
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "conv": conv,
        "channel": channel_count,
    }


# ═══════════════════════════════════════════════
# COMPLAINTS
# ═══════════════════════════════════════════════

def load_complaints():
    return _load_default(COMPLAINTS_FILE, {"next_id": 1001, "complaints": []})


def save_complaints(data) -> bool:
    return _save(COMPLAINTS_FILE, data)


def create_complaint(chat_id, category: str, name: str, text: str) -> dict:
    data = load_complaints()
    data.setdefault("next_id", 1001)
    cid = "CMP-" + str(data["next_id"])
    data["next_id"] += 1
    item = {
        "id": cid,
        "chat_id": str(chat_id),
        "category": category,
        "name": name,
        "text": text,
        "status": "new",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }
    data["complaints"].append(item)
    save_complaints(data)
    return item


# ═══════════════════════════════════════════════
# MEDS (medication reminders)
# ═══════════════════════════════════════════════

def load_meds():
    return _load_default(MEDS_FILE, {"meds": []})


def save_meds(data) -> bool:
    return _save(MEDS_FILE, data)


def create_med(chat_id, name: str, time_str: str, lang: str = "fa") -> dict:
    data = load_meds()
    item = {
        "chat_id": str(chat_id),
        "name": name,
        "time": time_str,
        "lang": lang,
        "active": True,
        "last_reminded_date": "",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }
    data["meds"].append(item)
    save_meds(data)
    return item


def get_user_meds(chat_id):
    data = load_meds()
    return [m for m in data["meds"]
            if m.get("chat_id") == str(chat_id) and m.get("active", True)]


def mark_med_reminded(chat_id, med_name: str, date_str: str) -> bool:
    data = load_meds()
    for m in data["meds"]:
        if (m.get("chat_id") == str(chat_id)
                and m.get("name") == med_name
                and m.get("active", True)):
            m["last_reminded_date"] = date_str
            save_meds(data)
            return True
    return False


# ═══════════════════════════════════════════════
# PACKAGES (Grand Slam)
# ═══════════════════════════════════════════════

def load_packages():
    return _load_default(PACKAGES_FILE, {"next_id": 1001, "packages": []})


def save_packages(data) -> bool:
    return _save(PACKAGES_FILE, data)


def create_package(chat_id, name: str, phone: str, lang: str) -> dict:
    data = load_packages()
    data.setdefault("next_id", 1001)
    pkg_id = "PKG-" + str(data["next_id"])
    data["next_id"] += 1
    pkg = {
        "id": pkg_id,
        "chat_id": str(chat_id),
        "name": name,
        "phone": phone,
        "lang": lang,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }
    data["packages"].append(pkg)
    save_packages(data)
    return pkg


# ═══════════════════════════════════════════════
# RATINGS
# ═══════════════════════════════════════════════

def load_ratings():
    return _load_default(RATINGS_FILE, {"ratings": []})


def save_rating(apt_id: str, chat_id, stars: int, feedback: str = "") -> dict:
    data = load_ratings()
    item = {
        "apt_id": apt_id,
        "chat_id": str(chat_id),
        "stars": int(stars),
        "feedback": feedback,
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }
    data["ratings"].append(item)
    _save(RATINGS_FILE, data)
    return item


def get_average_rating() -> float:
    data = load_ratings()
    items = [r for r in data.get("ratings", []) if r.get("stars")]
    if not items:
        return 0.0
    return round(sum(r["stars"] for r in items) / len(items), 2)


# ═══════════════════════════════════════════════
# PAYMENTS (Zarinpal)
# ═══════════════════════════════════════════════

def load_payments():
    return _load_default(PAYMENTS_FILE, {"next_id": 1001, "payments": []})


def save_payments(data) -> bool:
    return _save(PAYMENTS_FILE, data)


def create_payment_record(chat_id, apt_id: str, amount: int, authority: str = "",
                          status: str = "pending") -> dict:
    data = load_payments()
    data.setdefault("next_id", 1001)
    pid = "PAY-" + str(data["next_id"])
    data["next_id"] += 1
    item = {
        "id": pid,
        "chat_id": str(chat_id),
        "apt_id": apt_id,
        "amount": int(amount),
        "authority": authority,
        "ref_id": "",
        "status": status,   # pending | paid | failed | verified
        "created_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "verified_at": "",
    }
    data["payments"].append(item)
    save_payments(data)
    return item


def update_payment(pid: str, updates: dict):
    data = load_payments()
    for p in data["payments"]:
        if p.get("id") == pid:
            p.update(updates)
            save_payments(data)
            return p
    return None


def find_payment_by_authority(authority: str):
    data = load_payments()
    for p in data["payments"]:
        if p.get("authority") == authority:
            return p
    return None


def find_payment_by_id(pid: str):
    data = load_payments()
    for p in data["payments"]:
        if p.get("id") == pid:
            return p
    return None


# ═══════════════════════════════════════════════
# HUBS (transport terminals)
# ═══════════════════════════════════════════════

def load_hubs():
    data = _load_default(os.path.join(DATA_DIR, "transport_hubs.json"), {})
    return data.get("shiraz_transport_hubs", [])


def find_hub_field(hubs, hub_key: str, field_key: str, lang: str) -> str:
    for f in hubs:
        if f.get("key") == field_key:
            hv = f.get(hub_key, {})
            return hv.get("value_" + lang, "") or hv.get("value_fa", "")
    return ""


def format_hub(hub_key: str, lang: str) -> str:
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

    lat = lng = ""
    for f in hubs:
        if f.get("key") == "latitude":
            lat = f.get(hub_key, {}).get("value_fa", "")
        if f.get("key") == "longitude":
            lng = f.get(hub_key, {}).get("value_fa", "")

    if lat and lng and lat != "—" and lng != "—":
        lines.append("")
        lines.append("🗺 " + GOOGLE_MAPS_DIR + str(lat) + "," + str(lng))

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# INSURANCES
# ═══════════════════════════════════════════════

_INSURANCE_CACHE = {"data": None, "loaded": False}


def load_all_insurances():
    if _INSURANCE_CACHE["loaded"]:
        return _INSURANCE_CACHE["data"]
    all_ins = []
    candidates = (
    "ins_p1.json", "ins_p2.json", "ins_p3.json", "ins_p4.json",
    "insurances.json", "insurance.json", "ins.json",
)
for fn in candidates:
    data = _load_default(os.path.join(DATA_DIR, fn), {})
    items = data.get("insurances", []) or []
    if items:
        all_ins.extend(items)
    _INSURANCE_CACHE["data"] = all_ins
    _INSURANCE_CACHE["loaded"] = True
    return all_ins


def reload_insurances():
    _INSURANCE_CACHE["loaded"] = False
    return load_all_insurances()


def find_insurance_by_id(ins_id: str):
    for ins in load_all_insurances():
        if ins.get("id") == ins_id:
            return ins
    return None


def format_insurance(ins: dict, lang: str) -> str:
    if not ins:
        return MSG[lang]["insurance_not_found"]

    name = (
        ins.get("name_" + lang, "")
        or ins.get("name_fa", "")
        or ins.get("id", "")
    )
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


# ═══════════════════════════════════════════════
# DOCTOR STATUS (activate / deactivate)
# ═══════════════════════════════════════════════

def set_doctor_status(doc_id: str, new_status: str) -> bool:
    for fn in set(SPECIALTY_MAP.values()):
        path = os.path.join(DATA_DIR, "doctors", fn)
        data = load_json(path)
        if not data:
            continue
        found = False
        for item in data:
            if item.get("id", "") == doc_id:
                item["status"] = new_status
                item["updated_at"] = datetime.now().strftime("%Y/%m/%d %H:%M")
                found = True
                break
        if found:
            _save(path, data)
            return True
    return False


def get_meta_info():
    return _load_default(META_FILE, None)


# ═══════════════════════════════════════════════
# DATE / TIME HELPERS
# ═══════════════════════════════════════════════

def local_now() -> datetime:
    return datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET_HOURS)


def shamsi_to_miladi(jy: int, jm: int, jd: int):
    """Convert Jalali (Shamsi) to Gregorian. Uses jdatetime if available, else fallback."""
    if HAS_JDATETIME:
        try:
            g = jdatetime.date(jy, jm, jd).togregorian()
            return datetime(g.year, g.month, g.day)
        except Exception:
            return None
    return _jalali_fallback(jy, jm, jd)


def _jalali_fallback(jy: int, jm: int, jd: int):
    """Pure-python Jalali → Gregorian using Burkhardt algorithm."""
    try:
        jy -= 979
        jm -= 1
        jd -= 1
        j_day_no = 365 * jy + (jy // 33) * 8 + ((jy % 33 + 3) // 4)
        for i in range(jm):
            j_day_no += 31 if i < 6 else 30
        j_day_no += jd
        g_day_no = j_day_no + 79
        gy = 1600 + 400 * (g_day_no // 146097)
        g_day_no %= 146097
        leap = True
        if g_day_no >= 36525:
            g_day_no -= 1
            gy += 100 * (g_day_no // 36524)
            g_day_no %= 36524
            if g_day_no >= 365:
                g_day_no += 1
            else:
                leap = False
        gy += 4 * (g_day_no // 1461)
        g_day_no %= 1461
        if g_day_no >= 366:
            leap = False
            g_day_no -= 1
            gy += g_day_no // 365
            g_day_no %= 365
        gd = g_day_no + 1
        months = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        gm = 0
        while gd > months[gm]:
            gd -= months[gm]
            gm += 1
        gm += 1
        return datetime(gy, gm, gd)
    except Exception:
        return None


def miladi_to_shamsi(dt: datetime):
    """Convert Gregorian to Jalali. Returns (jy, jm, jd)."""
    if HAS_JDATETIME:
        try:
            j = jdatetime.date.fromgregorian(date=dt.date())
            return j.year, j.month, j.day
        except Exception:
            pass
    return _gregorian_to_jalali_fallback(dt.year, dt.month, dt.day)


def _gregorian_to_jalali_fallback(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gm > 2:
        gy2 = gy + 1
    else:
        gy2 = gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def format_jalali(dt: datetime) -> str:
    jy, jm, jd = miladi_to_shamsi(dt)
    return "{}/{}/{}".format(str(jy), str(jm).zfill(2), str(jd).zfill(2))


def format_date_full(offset_days: int = 0, lang: str = "fa") -> str:
    today = datetime.now() + timedelta(days=offset_days)
    return today.strftime("%Y/%m/%d")


def parse_apt_datetime(apt: dict):
    """Parse Jalali date + time from appointment into Gregorian datetime."""
    if not apt or not apt.get("date") or not apt.get("time"):
        return None
    try:
        dparts = apt["date"].split("/")
        tparts = apt["time"].split(":")
        if len(dparts) != 3 or len(tparts) != 2:
            return None
        jy, jm, jd = int(dparts[0]), int(dparts[1]), int(dparts[2])
        hh, mm = int(tparts[0]), int(tparts[1])
        g = shamsi_to_miladi(jy, jm, jd)
        if g is None:
            return None
        return datetime(g.year, g.month, g.day, hh, mm)
    except Exception:
        return None


# ═══════════════════════════════════════════════
# VALIDATORS
# ═══════════════════════════════════════════════

def validate_phone(text: str):
    phone = re.sub(r"[^0-9+]", "", text.translate(DIGITS).strip())
    if len(phone) < 8 or len(phone) > 15:
        return None
    return phone


def validate_time(text: str):
    t = re.sub(r"[^0-9:]", "", text.translate(DIGITS).strip())
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
    except Exception:
        pass
    return None


def validate_date_shamsi(s: str):
    try:
        parts = re.sub(r"[^0-9/]", "", s.translate(DIGITS)).split("/")
        if len(parts) != 3:
            return None
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
        if jy < 1400 or jy > 1500 or jm < 1 or jm > 12 or jd < 1 or jd > 31:
            return None
        return "{}/{}/{}".format(str(jy), str(jm).zfill(2), str(jd).zfill(2))
    except Exception:
        return None


def validate_iranian_national_id(text: str) -> str:
    """Official Iranian national ID (Melli code) checksum validation."""
    s = re.sub(r"[^0-9]", "", text.translate(DIGITS).strip())
    if len(s) != 10:
        return ""
    if len(set(s)) == 1:
        return ""
    try:
        check = int(s[9])
        total = 0
        for i in range(9):
            total += int(s[i]) * (10 - i)
        rem = total % 11
        if rem < 2:
            valid = (check == rem)
        else:
            valid = (check == (11 - rem))
        return s if valid else ""
    except Exception:
        return ""


def clean(text: str) -> str:
    if not text:
        return ""
    return text.translate(DIGITS).strip().lower().strip(" .!؟?،,؛;:")


def pick_language(text: str):
    t = clean(text)
    if t in ("1",) or "فارسی" in t or "persian" in t or "farsi" in t:
        return "fa"
    if t in ("2",) or "عرب" in t or "arab" in t:
        return "ar"
    if t in ("3",) or "english" in t or "انگلیس" in t:
        return "en"
    return None


def english_words(text: str):
    return re.findall(r"[a-zA-Z]+", (text or "").lower())


def is_simple_cmd(text: str, cmd_set) -> bool:
    return clean(text) in cmd_set


def is_all_request(text: str) -> bool:
    low = text.lower()
    words = re.findall(r"\w+", low)
    for w in ["همه", "تمام", "کل", "همگی", "all", "كل", "جميع"]:
        if w.lower() in words:
            return True
    return False


def is_best_request(text: str) -> bool:
    low = text.lower()
    words = english_words(text)
    return ("بهترین" in low) or ("best" in words) or ("أفضل" in low)


def is_emergency(text: str) -> bool:
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


def get_user_name(message) -> str:
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
    except Exception:
        return "ناشناس"


# ═══════════════════════════════════════════════
# PRICE RESOLVER (for payment)
# ═══════════════════════════════════════════════

def resolve_price_for_doctor(doctor: dict, insurance_id: str = "",
                             payment_type: str = "full", lang: str = "fa") -> int:
    """
    Resolve price in Toman.
    priority:
      1. if insurance_id given and payment_type == 'insurance' → insurance price
      2. doctor's explicit 'price_toman' or 'price_range_toman' as int
      3. default ranges from insurance
    """
    # 1. Insurance price
    if insurance_id and payment_type == "insurance":
        ins = find_insurance_by_id(insurance_id)
        if ins:
            for key in ("price_insurance_toman", "price_insurance", "insurance_price"):
                v = ins.get(key) or ins.get("fields", {}).get(key, {})
                if isinstance(v, dict):
                    v = v.get("value_fa", "") or v.get("value_" + lang, "")
                try:
                    n = int(re.sub(r"[^0-9]", "", str(v)))
                    if n > 0:
                        return n
                except Exception:
                    pass

    # 2. Doctor explicit price
    for key in ("price_toman", "price_range_toman", "price_range", "price"):
        v = doctor.get(key)
        if isinstance(v, dict):
            v = v.get(lang, v.get("fa", ""))
        if v:
            try:
                n = int(re.sub(r"[^0-9]", "", str(v)))
                if n > 0:
                    return n
            except Exception:
                pass

    # 3. Fallback
    return 500000


# ═══════════════════════════════════════════════
# SEARCH ENGINE
# ═══════════════════════════════════════════════

def search_by_doctor_name(text: str):
    low = text.lower()
    st = low
    for w in ["دکتر", "doctor", "دكتور", "طبيب", "dr"]:
        st = st.replace(w, "")
    st = st.strip()
    if not st or len(st) < 3:
        return None

    for fn in set(SPECIALTY_MAP.values()):
        data = load_json(os.path.join(DATA_DIR, "doctors", fn))
        if not data:
            continue
        for item in data:
            if item.get("status", "active") == "inactive":
                continue
            name = item_name_for_search(item).lower()
            if st in name or name in st:
                return item
    return None


def search_specialty(text: str):
    low = text.lower()
    words = english_words(text)
    scores = {}
    for k, fn in SPECIALTY_MAP.items():
        if k.isascii():
            matched = (k in words) or ((k + "s") in words)
        else:
            matched = (k in low)
        if matched:
            w = len(k)
            if k.lower() in [cw.lower() for cw in CONTEXT_WORDS]:
                w = w * 0.3
            scores[fn] = scores.get(fn, 0) + w

    if not scores:
        return None
    best = max(scores, key=scores.get)
    data = load_json(os.path.join(DATA_DIR, "doctors", best))
    if not data:
        return None
    data = [d for d in data if d.get("status", "active") != "inactive"]
    if not data:
        return None

    def sc(x):
        r = x.get("ratings", {})
        if isinstance(r, dict) and "patient_satisfaction_score" in r:
            return r["patient_satisfaction_score"]
        return x.get("patient_satisfaction_score", x.get("rating", 0))

    try:
        data.sort(key=sc, reverse=True)
    except Exception:
        pass
    return data


def search_non_medical(text: str):
    low = text.lower()
    words = english_words(text)
    scores = {}
    for fn, kws in NON_MEDICAL_MAP.items():
        s = 0
        for kw in kws:
            kl = kw.lower()
            if kl.isascii():
                matched = (kl in words) or ((kl + "s") in words)
            else:
                matched = (kl in low)
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


# ═══════════════════════════════════════════════
# FORMATTERS
# ═══════════════════════════════════════════════

def format_doctor(doc: dict, lang: str) -> str:
    n = get_value(doc, "name", lang) or ""
    s = get_value(doc, "specialty", lang) or ""
    p = get_value(doc, "phone", lang) or doc.get("phone", "")
    a = get_value(doc, "office_address", lang) or get_value(doc, "address", lang) or ""
    hs = get_value(doc, "surgeries_done_at", lang) or []
    if isinstance(hs, str):
        hs = [hs]
    h = " - ".join(str(x) for x in hs) if hs else ""
    pr = get_value(doc, "price_range_toman", lang) or get_value(doc, "price_range", lang) or ""
    r = doc.get("patient_satisfaction_score", doc.get("rating", ""))
    lat = doc.get("lat", "")
    lng = doc.get("lng", "")

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
        if r != "":
            lines.append("Rating: " + str(r) + "/5")
        if lat and lng:
            lines.append("Map: " + GOOGLE_MAPS_DIR + str(lat) + "," + str(lng))
        elif a and str(a) != "None":
            lines.append("Map: " + GOOGLE_MAPS_SEARCH + quote(str(a)))
    elif lang == "ar":
        lines.append("الطبيب: " + str(n))
        lines.append("التخصص: " + str(s))
        lines.append("العنوان: " + str(a))
        if h:
            lines.append("المستشفيات: " + str(h))
        lines.append("الهاتف: " + str(p))
        if pr:
            lines.append("التكلفة: " + str(pr))
        if r != "":
            lines.append("التقييم: " + str(r) + "/5")
        if lat and lng:
            lines.append("الخريطة: " + GOOGLE_MAPS_DIR + str(lat) + "," + str(lng))
        elif a and str(a) != "None":
            lines.append("الخريطة: " + GOOGLE_MAPS_SEARCH + quote(str(a)))
    else:
        lines.append("دکتر: " + str(n))
        lines.append("تخصص: " + str(s))
        lines.append("آدرس: " + str(a))
        if h:
            lines.append("بیمارستان: " + str(h))
        lines.append("تلفن: " + str(p))
        if pr:
            lines.append("قیمت: " + str(pr))
        if r != "":
            lines.append("امتیاز: " + str(r) + "/5")
        if lat and lng:
            lines.append("مسیریاب: " + GOOGLE_MAPS_DIR + str(lat) + "," + str(lng))
        elif a and str(a) != "None":
            lines.append("مسیریاب: " + GOOGLE_MAPS_SEARCH + quote(str(a)))
    return "\n".join(lines)


def format_generic(item: dict, lang: str) -> str:
    if not isinstance(item, dict):
        return str(item)
    fnames = FIELD_NAMES.get(lang, {})
    lines = []
    seen = set()
    skip_keys = ("id", "status", "lat", "lng", "created_at", "updated_at", "pkg_id", "type")

    for k, v in item.items():
        if k in skip_keys:
            continue
        if k.endswith("_fa") or k.endswith("_ar") or k.endswith("_en"):
            bk = k[:-3]
            if bk in seen:
                continue
            val = None
            for p in (lang, "fa", "en", "ar"):
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
            for L in (lang, "fa", "en", "ar"):
                if L in val and val[L]:
                    val = val[L]
                    break
            else:
                continue
        if isinstance(val, list):
            val = " - ".join(str(x) for x in val)
        elif isinstance(val, bool):
            if k in ("has_home_service", "has_translator"):
                val = "✅" if val else "❌"
        sv = str(val).strip()
        if sv and sv != "None":
            lines.append(str(label) + ": " + sv)

    lat = item.get("lat", "")
    lng = item.get("lng", "")
    addr = get_value(item, "address", lang)
    if lat and lng:
        lines.append("مسیریاب: " + GOOGLE_MAPS_DIR + str(lat) + "," + str(lng))
    elif addr and str(addr) != "None":
        lines.append("مسیریاب: " + GOOGLE_MAPS_SEARCH + quote(str(addr)))

    return "\n".join(lines)


print("═══ PART 4/6 LOADED ═══ Data layer ready")
# ═══════════════════════════════════════════════
# AI — AvalAI (gpt-4o-mini)
# ═══════════════════════════════════════════════

def get_ai(text: str, lang: str):
    if not AVALAI_API_KEY:
        return None
    prompt = SYSTEM_PROMPT + " پاسخ را به زبان " + LANG_NAMES.get(lang, "فارسی") + " بنویس."
    try:
        r = requests.post(
            AVALAI_URL,
            headers={
                "Authorization": "Bearer " + AVALAI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
            },
            timeout=20,
        )
        if r.status_code != 200:
            print("AI_ERR_CODE:", r.status_code)
            return None
        result = r.json()["choices"][0]["message"]["content"]
        if result and len(result.strip()) > 5:
            return result
        return None
    except Exception as e:
        print("AI_ERR:", str(e))
        return None


# ═══════════════════════════════════════════════
# STT — Whisper via AvalAI
# ═══════════════════════════════════════════════

def voice_to_text(file_url: str):
    if not AVALAI_API_KEY:
        return None
    try:
        r = requests.get(file_url, timeout=30)
        if r.status_code != 200:
            print("STT_DL_ERR:", r.status_code)
            return None
        audio_data = r.content
        files = {"file": ("voice.ogg", audio_data, "audio/ogg")}
        headers = {"Authorization": "Bearer " + AVALAI_API_KEY}
        data = {"model": STT_MODEL}
        resp = requests.post(
            AVALAI_STT_URL, headers=headers, files=files, data=data, timeout=60
        )
        if resp.status_code != 200:
            print("STT_ERR_CODE:", resp.status_code, resp.text[:200])
            return None
        result = resp.json()
        text = result.get("text", "").strip()
        return text if text else None
    except Exception as e:
        print("STT_ERR:", str(e))
        return None


# ═══════════════════════════════════════════════
# Translator (via AvalAI)
# ═══════════════════════════════════════════════

def translate_text(text: str, source_lang: str, target_lang: str):
    if not AVALAI_API_KEY:
        return None
    lang_names = {"fa": "فارسی", "ar": "العربية", "en": "English"}
    prompt = (
        "Translate the following text from "
        + lang_names.get(source_lang, source_lang)
        + " to "
        + lang_names.get(target_lang, target_lang)
        + ". Output only the translation, nothing else. Text: "
        + text
    )
    try:
        r = requests.post(
            AVALAI_URL,
            headers={
                "Authorization": "Bearer " + AVALAI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if r.status_code != 200:
            print("TR_ERR_CODE:", r.status_code)
            return None
        result = r.json()["choices"][0]["message"]["content"]
        return result.strip() if result else None
    except Exception as e:
        print("TR_ERR:", str(e))
        return None


# ═══════════════════════════════════════════════
# ZARINPAL — Payment Gateway (v4 REST)
# ═══════════════════════════════════════════════

def zarinpal_request(amount_toman: int, description: str, callback_url: str,
                     mobile: str = "", email: str = ""):
    """
    Request a payment from Zarinpal.
    Returns dict {ok: bool, authority: str, url: str, error: str}
    """
    try:
        payload = {
            "merchant_id": ZARINPAL_MERCHANT_ID,
            "amount": int(amount_toman) * 10,   # Zarinpal uses Rial
            "description": description[:255],
            "callback_url": callback_url,
        }
        if mobile:
            payload["metadata"] = {"mobile": mobile}
        if email:
            payload.setdefault("metadata", {})["email"] = email

        r = requests.post(
            ZARINPAL_REQUEST_URL,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )
        data = r.json() if r.content else {}
        if r.status_code == 200 and data.get("data", {}).get("code") == 100:
            authority = data["data"]["authority"]
            return {
                "ok": True,
                "authority": authority,
                "url": ZARINPAL_STARTPAY + authority,
                "error": "",
            }
        err = data.get("errors", {})
        return {
            "ok": False,
            "authority": "",
            "url": "",
            "error": str(err) if err else ("HTTP " + str(r.status_code)),
        }
    except Exception as e:
        print("ZP_REQ_ERR:", str(e))
        return {"ok": False, "authority": "", "url": "", "error": str(e)}


def zarinpal_verify(authority: str, amount_toman: int):
    """
    Verify a Zarinpal payment.
    Returns dict {ok: bool, ref_id: str, card_pan: str, error: str}
    """
    try:
        payload = {
            "merchant_id": ZARINPAL_MERCHANT_ID,
            "amount": int(amount_toman) * 10,
            "authority": authority,
        }
        r = requests.post(
            ZARINPAL_VERIFY_URL,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )
        data = r.json() if r.content else {}
        code = data.get("data", {}).get("code")
        if r.status_code == 200 and code in (100, 101):
            return {
                "ok": True,
                "ref_id": str(data["data"].get("ref_id", "")),
                "card_pan": str(data["data"].get("card_pan", "")),
                "error": "",
            }
        err = data.get("errors", {})
        return {
            "ok": False,
            "ref_id": "",
            "card_pan": "",
            "error": str(err) if err else ("code " + str(code)),
        }
    except Exception as e:
        print("ZP_VERIFY_ERR:", str(e))
        return {"ok": False, "ref_id": "", "card_pan": "", "error": str(e)}


# ═══════════════════════════════════════════════
# INVOICE PDF (reportlab)
# ═══════════════════════════════════════════════

_FONT_REGISTERED = {"done": False, "name": "Helvetica"}


def _register_persian_font():
    """Try to register a Persian-capable TTF font. Falls back to Helvetica."""
    if _FONT_REGISTERED["done"]:
        return _FONT_REGISTERED["name"]
    if not HAS_REPORTLAB:
        _FONT_REGISTERED["done"] = True
        return "Helvetica"

    candidates = [
        ("Vazir",   os.path.join(FONTS_DIR, "Vazirmatn-Regular.ttf")),
        ("Vazir",   os.path.join(FONTS_DIR, "Vazir.ttf")),
        ("DejaVu",  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("Amiri",   os.path.join(FONTS_DIR, "Amiri-Regular.ttf")),
    ]
    for name, path in candidates:
        try:
            if os.path.isfile(path):
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT_REGISTERED["name"] = name
                break
        except Exception as e:
            print("FONT_REG_ERR:", name, str(e))
    _FONT_REGISTERED["done"] = True
    return _FONT_REGISTERED["name"]


def generate_invoice_pdf(apt: dict, lang: str = "fa") -> bytes:
    """
    Generate an official PDF invoice for an appointment.
    Returns PDF bytes, or None if reportlab is missing.
    """
    if not HAS_REPORTLAB:
        return None

    font_name = _register_persian_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # ─── Header ───
    c.setFillColorRGB(0.06, 0.31, 0.55)
    c.rect(0, H - 30 * mm, W, 30 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(font_name, 20)
    c.drawString(20 * mm, H - 18 * mm, "Shiraz Medical")
    c.setFont(font_name, 10)
    c.drawString(20 * mm, H - 25 * mm, "Tourism Health Center — Shiraz, Iran")

    # ─── Title ───
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, 16)
    title_map = {"fa": "فیش رسمی نوبت", "ar": "فاتورة رسمية", "en": "Official Invoice"}
    c.drawString(20 * mm, H - 45 * mm, title_map.get(lang, "Invoice"))

    # ─── Invoice number ───
    c.setFont(font_name, 11)
    c.drawString(20 * mm, H - 55 * mm, "Invoice No: " + str(apt.get("id", "")))
    c.drawString(20 * mm, H - 62 * mm, "Date: " + str(apt.get("created_at", "")))
    c.drawString(20 * mm, H - 69 * mm, "Status: " + str(apt.get("status", "")))

    # ─── Table ───
    y = H - 85 * mm
    c.setFont(font_name, 11)
    label_map = {
        "fa": {
            "patient": "نام بیمار",
            "phone": "تلفن بیمار",
            "nid": "کد ملی",
            "doctor": "پزشک",
            "office": "مطب",
            "date": "تاریخ",
            "time": "ساعت",
            "insurance": "بیمه",
            "priority": "اولویت",
            "amount": "مبلغ (تومان)",
            "pay_type": "نوع پرداخت",
            "pay_status": "وضعیت پرداخت",
            "ref": "کد رهگیری",
        },
        "ar": {
            "patient": "اسم المريض",
            "phone": "هاتف المريض",
            "nid": "رقم الهوية",
            "doctor": "الطبيب",
            "office": "العيادة",
            "date": "التاريخ",
            "time": "الساعة",
            "insurance": "التأمين",
            "priority": "الأولوية",
            "amount": "المبلغ (تومان)",
            "pay_type": "نوع الدفع",
            "pay_status": "حالة الدفع",
            "ref": "الرقم المرجعي",
        },
        "en": {
            "patient": "Patient",
            "phone": "Phone",
            "nid": "National ID",
            "doctor": "Doctor",
            "office": "Office",
            "date": "Date",
            "time": "Time",
            "insurance": "Insurance",
            "priority": "Priority",
            "amount": "Amount (Toman)",
            "pay_type": "Payment type",
            "pay_status": "Payment status",
            "ref": "Reference",
        },
    }.get(lang, {})

    rows = [
        ("patient",    apt.get("patient_name", "")),
        ("phone",      apt.get("patient_phone", "")),
        ("nid",        apt.get("patient_national_id", "")),
        ("doctor",     apt.get("doctor_name_" + lang) or apt.get("doctor_name_fa", "")),
        ("office",     apt.get("office", "")),
        ("date",       apt.get("date", "")),
        ("time",       apt.get("time", "")),
        ("insurance",  apt.get("insurance_name", "")),
        ("priority",   apt.get("priority", "")),
        ("amount",     str(apt.get("amount", 0))),
        ("pay_type",   apt.get("payment_type", "")),
        ("pay_status", apt.get("payment_status", "")),
        ("ref",        apt.get("payment_ref", "")),
    ]

    for key, val in rows:
        label = label_map.get(key, key)
        c.setFont(font_name, 10)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(20 * mm, y, label + ":")
        c.setFillColorRGB(0, 0, 0)
        c.drawString(70 * mm, y, str(val))
        y -= 7 * mm
        if y < 60 * mm:
            c.showPage()
            c.setFont(font_name, 10)
            y = H - 30 * mm

    # ─── QR code (linking to tracking) ───
    if HAS_QRCODE:
        try:
            track_url = "https://ble.ir/" + BOT_USERNAME + "?start=" + str(apt.get("id", ""))
            qr = qrcode.QRCode(version=1, box_size=4, border=1)
            qr.add_data(track_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            qr_buf = io.BytesIO()
            img.save(qr_buf, format="PNG")
            qr_buf.seek(0)
            from reportlab.lib.utils import ImageReader
            c.drawImage(
                ImageReader(qr_buf),
                W - 45 * mm, 40 * mm, width=30 * mm, height=30 * mm,
                preserveAspectRatio=True,
            )
        except Exception as e:
            print("QR_ERR:", str(e))

    # ─── Footer ───
    c.setFont(font_name, 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(20 * mm, 25 * mm, "Shiraz Medical  •  ble.ir/" + BOT_USERNAME)
    c.drawString(20 * mm, 20 * mm, "This invoice is computer-generated and valid without signature.")

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


# ═══════════════════════════════════════════════
# REMINDERS — 24h + 2h + medication
# ═══════════════════════════════════════════════

def get_pending_reminders(now_local: datetime):
    data = load_appointments()
    one_day = []
    two_hours = []
    for a in data["appointments"]:
        if a.get("status") != "confirmed":
            continue
        dt = parse_apt_datetime(a)
        if dt is None:
            continue
        diff = dt - now_local
        diff_min = diff.total_seconds() / 60.0
        if not a.get("reminded_1d"):
            if 23.5 * 60 <= diff_min <= 24.5 * 60:
                one_day.append(a)
        if not a.get("reminded_2h"):
            if 1.5 * 60 <= diff_min <= 2.5 * 60:
                two_hours.append(a)
    return one_day, two_hours


def get_pending_med_reminders(now_local: datetime):
    data = load_meds()
    result = []
    today_str = now_local.strftime("%Y/%m/%d")
    for m in data["meds"]:
        if not m.get("active", True):
            continue
        if m.get("last_reminded_date") == today_str:
            continue
        mt = m.get("time", "")
        if not mt:
            continue
        try:
            hh, mm = int(mt.split(":")[0]), int(mt.split(":")[1])
        except Exception:
            continue
        target_min = hh * 60 + mm
        now_min = now_local.hour * 60 + now_local.minute
        if 0 <= (target_min - now_min) <= 30:
            result.append(m)
    return result


def _send_apt_reminder(apt: dict, kind: str):
    lang = apt.get("patient_lang", "fa")
    cid = apt.get("patient_chat_id", "")
    if not cid:
        return
    dn = apt.get("doctor_name_" + lang) or apt.get("doctor_name_fa", "")
    ad = apt.get("doctor_address_" + lang) or apt.get("doctor_address_fa", "")
    try:
        if kind == "1d":
            txt = MSG[lang]["remind_apt_1d"].format(
                time=apt.get("time", ""), doctor=dn, address=ad
            )
        else:
            txt = MSG[lang]["remind_apt_2h"].format(
                time=apt.get("time", ""), doctor=dn, address=ad
            )
        bot.send_message(cid, txt, reply_markup=back_kb(lang))
    except Exception as e:
        print("APT_REMIND_ERR:", str(e))


def _send_med_reminder(med: dict, today_str: str):
    cid = med.get("chat_id", "")
    if not cid:
        return
    lang = med.get("lang", "fa")
    try:
        bot.send_message(cid, MSG[lang]["remind_med"].format(med=med.get("name", "")))
        mark_med_reminded(cid, med.get("name", ""), today_str)
    except Exception as e:
        print("MED_REMIND_ERR:", str(e))


def reminder_worker():
    print("REMINDER_WORKER: started (loop every 15 min)")
    time_module.sleep(30)
    while True:
        try:
            now_local = local_now()
            one_d, two_h = get_pending_reminders(now_local)
            for apt in one_d:
                _send_apt_reminder(apt, "1d")
                mark_reminded(apt["id"], "reminded_1d")
            for apt in two_h:
                _send_apt_reminder(apt, "2h")
                mark_reminded(apt["id"], "reminded_2h")

            today_str = now_local.strftime("%Y/%m/%d")
            meds_due = get_pending_med_reminders(now_local)
            for m in meds_due:
                _send_med_reminder(m, today_str)
        except Exception as e:
            print("REMINDER_LOOP_ERR:", str(e))
        time_module.sleep(15 * 60)


# ═══════════════════════════════════════════════
# SENDER HELPERS
# ═══════════════════════════════════════════════

def send_with_kb(chat_id, text: str, kb=None):
    try:
        if kb:
            bot.send_message(chat_id, text, reply_markup=kb)
        else:
            bot.send_message(chat_id, text)
    except Exception as e:
        print("SEND_ERR:", str(e))


def reply_with_kb(message, text: str, kb=None):
    try:
        if kb:
            bot.reply_to(message, text, reply_markup=kb)
        else:
            bot.reply_to(message, text)
    except Exception as e:
        print("REPLY_ERR:", str(e))


def send_hope_flower(chat_id, lang: str):
    key = random.choice([
        "hope_general_1", "hope_general_2", "hope_general_3", "hope_general_4"
    ])
    msg = MSG2[lang].get(key, "")
    try:
        bot.send_message(chat_id, "🌹\n\n" + msg, reply_markup=back_kb(lang))
    except Exception:
        pass


def send_hope_for_stage(chat_id, lang: str, stage: str):
    key = "hope_stage_" + stage
    msg = MSG2[lang].get(key)
    if msg:
        try:
            bot.send_message(chat_id, msg)
        except Exception:
            pass


def show_main_menu(message, lang: str):
    reply_with_kb(message, MSG2[lang]["menu_main"], main_menu_kb(lang))


def ask_more(message):
    cid = message.chat.id
    with STATE_LOCK:
        user_state[cid] = "awaiting_more"
    reply_with_kb(message, MSG[user_lang.get(cid, "fa")]["more"])


# ═══════════════════════════════════════════════
# KEYBOARD BUILDERS — Main
# ═══════════════════════════════════════════════

def back_kb(lang: str, cb: str = "back_main"):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data=cb))
    return m


def main_menu_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        types.InlineKeyboardButton(text=b["btn_docs"],      callback_data="menu_docs"),
        types.InlineKeyboardButton(text=b["btn_nonmed"],    callback_data="menu_nonmed"),
        types.InlineKeyboardButton(text=b["btn_tourist"],   callback_data="menu_tourist"),
        types.InlineKeyboardButton(text=b["btn_para"],      callback_data="menu_para"),
        types.InlineKeyboardButton(text=b["btn_elder"],     callback_data="menu_elder"),
        types.InlineKeyboardButton(text=b["btn_pkg"],       callback_data="menu_pkg"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_hubs"],      callback_data="do_hubs"),
        types.InlineKeyboardButton(text=b["btn_taxi"],      callback_data="do_taxi"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_insurance"], callback_data="do_insurance"),
        types.InlineKeyboardButton(text=b["btn_translator"],callback_data="do_translator"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_charter"],   callback_data="do_charter"),
        types.InlineKeyboardButton(text=b["btn_deepseek"],  callback_data="do_deepseek"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_file"],      callback_data="do_file"),
        types.InlineKeyboardButton(text=b["btn_apt"],       callback_data="do_apt"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_med"],       callback_data="do_med"),
        types.InlineKeyboardButton(text=b["btn_sos"],       callback_data="do_sos"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_channel"],   callback_data="do_channel"),
    )
    m.add(
        types.InlineKeyboardButton(text=b["btn_invite"],    callback_data="do_invite"),
        types.InlineKeyboardButton(text=b["btn_help"],      callback_data="do_help"),
    )
    return m


# ═══════════════════════════════════════════════
# KEYBOARD BUILDERS — Sections
# ═══════════════════════════════════════════════

def specialties_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    items = [
        ("قلب",           "cardiology",           "قلبية",       "Heart"),
        ("پوست",          "dermatology",          "جلدية",       "Skin"),
        ("دندان",         "dentistry",            "أسنان",       "Dental"),
        ("چشم",           "ophthalmology",        "عيون",        "Eye"),
        ("گوش و حلق",     "ent",                  "أنف",         "ENT"),
        ("ارتوپدی",       "orthopedics",          "عظام",        "Ortho"),
        ("زنان و زایمان", "gynecology",           "نساء",        "Gyneco"),
        ("کودکان",        "pediatrics",           "أطفال",       "Pediatrics"),
        ("روان‌پزشکی",    "psychiatry",           "نفسي",        "Psychiatry"),
        ("داخلی",         "internal_medicine",    "باطنية",      "Internal"),
        ("اورولوژی",      "urology",              "مسالك",       "Urology"),
        ("جراحی عمومی",   "general_surgery",      "جراحة",       "Surgery"),
        ("گوارش",         "gastroenterology",     "هضمي",        "Gastro"),
        ("غدد",           "endocrinology",        "غدة",         "Endocrine"),
        ("خون و سرطان",   "hematology_oncology",  "أورام",       "Hematology"),
        ("مغز و اعصاب",   "neurosurgery",         "أعصاب",       "Neurosurgery"),
        ("آلرژی",         "allergy",              "حساسية",      "Allergy"),
        ("طب سنتی",       "traditional_medicine", "طب تقليدي",   "Traditional"),
    ]
    btns = []
    for fa, fn, ar, en in items:
        label = fa if lang == "fa" else (ar if lang == "ar" else en)
        btns.append(types.InlineKeyboardButton(text=label, callback_data="spec_" + fn))
    m.add(*btns)
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def nonmed_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        types.InlineKeyboardButton(text=b["btn_hospitals"], callback_data="non_hospitals"),
        types.InlineKeyboardButton(text=b["btn_hotels"],    callback_data="non_hotels"),
        types.InlineKeyboardButton(text=b["btn_motels"],    callback_data="non_motels"),
        types.InlineKeyboardButton(text=b["btn_houses"],    callback_data="non_tourist_houses"),
        types.InlineKeyboardButton(text=b["btn_transport"], callback_data="non_transport"),
    )
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def tourist_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        types.InlineKeyboardButton(text=b["btn_city"],    callback_data="non_leisure_city"),
        types.InlineKeyboardButton(text=b["btn_outside"], callback_data="non_leisure_outside"),
    )
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def para_kb(lang: str):
    """Paramedical services. Each button has its own callback so we can search specifically."""
    m = types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    items = [
        (b["btn_physio"],       "para_physiotherapy"),
        (b["btn_lab"],          "para_lab"),
        (b["btn_radiology"],    "para_radiology"),
        (b["btn_nursing"],      "para_nursing"),
        (b["btn_injection"],    "para_injection"),
        (b["btn_trad_med"],     "para_traditional_medicine"),
        (b["btn_occupational"], "para_occupational"),
        (b["btn_speech"],       "para_speech"),
        (b["btn_orthotics"],    "para_orthotics"),
    ]
    btns = [types.InlineKeyboardButton(text=label, callback_data=cb) for label, cb in items]
    m.add(*btns)
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def elderly_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(types.InlineKeyboardButton(text=b["btn_elder_all"], callback_data="elder_all"))
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def package_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(types.InlineKeyboardButton(text=b["btn_pkg_order"], callback_data="pkg_order"))
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def doctor_action_kb(lang: str, doc_id: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        types.InlineKeyboardButton(text=b["btn_book"], callback_data="book_" + doc_id),
        types.InlineKeyboardButton(text=b["btn_call"], callback_data="call_" + doc_id),
    )
    m.add(types.InlineKeyboardButton(text=b["btn_taxi"], callback_data="do_taxi"))
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def taxi_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    b = MSG_BTN[lang]
    m.add(
        types.InlineKeyboardButton(text=b["btn_snapp"], url=SNAPP_URL),
        types.InlineKeyboardButton(text=b["btn_tap30"], url=TAP30_URL),
    )
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def hubs_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    for hub_id, labels in HUB_LABELS.items():
        label = labels.get(lang, labels.get("fa", hub_id))
        m.add(types.InlineKeyboardButton(text=label, callback_data="hub_" + hub_id))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def hub_action_kb(lang: str, hub_id: str = ""):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton(
        text=MSG_BTN[lang]["btn_back_hubs"], callback_data="do_hubs"
    ))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def insurance_kb(lang: str, page: int = 0):
    all_ins = load_all_insurances()
    if not all_ins:
        return back_kb(lang)
    per_page = 10
    total = len(all_ins)
    start = page * per_page
    end = min(start + per_page, total)

    m = types.InlineKeyboardMarkup(row_width=1)
    for ins in all_ins[start:end]:
        name = ins.get("name_" + lang, "") or ins.get("name_fa", "") or ins.get("id", "")
        ins_id = ins.get("id", "")
        if name and ins_id:
            m.add(types.InlineKeyboardButton(
                text="🏥 " + name, callback_data="ins_" + ins_id
            ))

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(
            text="◀️ " + ("قبلی" if lang == "fa" else ("السابق" if lang == "ar" else "Prev")),
            callback_data="ins_page_" + str(page - 1),
        ))
    if end < total:
        nav.append(types.InlineKeyboardButton(
            text=("بعدی" if lang == "fa" else ("التالي" if lang == "ar" else "Next")) + " ▶️",
            callback_data="ins_page_" + str(page + 1),
        ))
    if nav:
        m.add(*nav)
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def insurance_action_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton(
        text=MSG_BTN[lang]["btn_back_insurance"], callback_data="do_insurance"
    ))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def translator_lang_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(
        types.InlineKeyboardButton(text=b["btn_tr_fa_ar"], callback_data="tr_fa_ar"),
        types.InlineKeyboardButton(text=b["btn_tr_ar_fa"], callback_data="tr_ar_fa"),
        types.InlineKeyboardButton(text=b["btn_tr_fa_en"], callback_data="tr_fa_en"),
        types.InlineKeyboardButton(text=b["btn_tr_en_fa"], callback_data="tr_en_fa"),
    )
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def translator_result_kb(lang: str, translated_text: str, target_lang_code: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    encoded = quote(translated_text[:400])
    url = (
        "https://translate.google.com/?sl=auto&tl="
        + target_lang_code + "&text=" + encoded + "&op=translate"
    )
    m.add(types.InlineKeyboardButton(text=MSG[lang]["translator_listen"], url=url))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def deepseek_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    b = MSG_BTN[lang]
    m.add(types.InlineKeyboardButton(text=b["btn_deepseek_go"], url=DEEPSEEK_URL))
    m.add(types.InlineKeyboardButton(text=b["btn_back"], callback_data="back_main"))
    return m


def channel_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    b = MSG_CH[lang]
    m.add(types.InlineKeyboardButton(text=b["btn_channel_go"], url=CHANNEL_LINK))
    m.add(types.InlineKeyboardButton(text=b["btn_channel_ok"], callback_data="channel_confirm"))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def rate_kb(lang: str, apt_id: str):
    m = types.InlineKeyboardMarkup(row_width=5)
    m.add(
        types.InlineKeyboardButton(text="1⭐", callback_data="rate_1_" + apt_id),
        types.InlineKeyboardButton(text="2⭐", callback_data="rate_2_" + apt_id),
        types.InlineKeyboardButton(text="3⭐", callback_data="rate_3_" + apt_id),
        types.InlineKeyboardButton(text="4⭐", callback_data="rate_4_" + apt_id),
        types.InlineKeyboardButton(text="5⭐", callback_data="rate_5_" + apt_id),
    )
    return m


# ═══════════════════════════════════════════════
# APPOINTMENT FLOW — Keyboards
# ═══════════════════════════════════════════════

def offices_kb(lang: str, doctor: dict):
    """Build office selection keyboard from doctor's offices (or fallback to main address)."""
    m = types.InlineKeyboardMarkup(row_width=1)
    offices = doctor.get("offices", [])
    if not isinstance(offices, list) or not offices:
        # single office (main address)
        addr = (
            get_value(doctor, "office_address", lang)
            or get_value(doctor, "address", lang)
            or "—"
        )
        m.add(types.InlineKeyboardButton(
            text="🏥 " + str(addr)[:55], callback_data="office_0"
        ))
    else:
        for i, off in enumerate(offices):
            name = off.get("name_" + lang, "") or off.get("name_fa", "") or ("مطب " + str(i + 1))
            m.add(types.InlineKeyboardButton(
                text="🏥 " + str(name)[:55], callback_data="office_" + str(i)
            ))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def date_kb(lang: str):
    """14-day Jalali calendar."""
    m = types.InlineKeyboardMarkup(row_width=4)
    today = local_now()
    weekday_names = {
        "fa": ["د", "ی", "د", "س", "چ", "پ", "ج"],
        "ar": ["ح", "ن", "ث", "ر", "خ", "ج", "س"],
        "en": ["M", "T", "W", "T", "F", "S", "S"],
    }[lang]
    btns = []
    for i in range(14):
        d = today + timedelta(days=i)
        jy, jm, jd = miladi_to_shamsi(d)
        label = "{}/{}/{} {}".format(str(jy), str(jm).zfill(2), str(jd).zfill(2),
                                     weekday_names[d.weekday()])
        cb = "date_{}_{}_{}".format(str(jy), str(jm), str(jd))
        btns.append(types.InlineKeyboardButton(text=label, callback_data=cb))
    for i in range(0, len(btns), 4):
        m.add(*btns[i:i + 4])
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def time_kb(lang: str, date_str: str):
    """15-minute intervals from 08:00 to 20:00."""
    m = types.InlineKeyboardMarkup(row_width=4)
    btns = []
    for h in range(8, 20):
        for mins in (0, 15, 30, 45):
            tstr = "{:02d}:{:02d}".format(h, mins)
            cb = "time_{}_{}".format(date_str.replace("/", "-"), tstr.replace(":", "-"))
            btns.append(types.InlineKeyboardButton(text=tstr, callback_data=cb))
    for i in range(0, len(btns), 4):
        m.add(*btns[i:i + 4])
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def insurance_choice_kb(lang: str):
    """Yes/No insurance + skip."""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton(text="✅ " + ("دارم" if lang == "fa" else ("نعم" if lang == "ar" else "Yes")),
                                   callback_data="apt_ins_yes"),
        types.InlineKeyboardButton(text="❌ " + ("ندارم" if lang == "fa" else ("لا" if lang == "ar" else "No")),
                                   callback_data="apt_ins_no"),
    )
    return m


def apt_insurance_pick_kb(lang: str, page: int = 0):
    """Insurance selection during appointment flow (with skip)."""
    all_ins = load_all_insurances()
    per_page = 8
    total = len(all_ins)
    start = page * per_page
    end = min(start + per_page, total)

    m = types.InlineKeyboardMarkup(row_width=1)
    for ins in all_ins[start:end]:
        name = ins.get("name_" + lang, "") or ins.get("name_fa", "") or ins.get("id", "")
        ins_id = ins.get("id", "")
        if name and ins_id:
            m.add(types.InlineKeyboardButton(
                text="🏥 " + name, callback_data="apt_ins_pick_" + ins_id
            ))

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(
            text="◀️", callback_data="apt_ins_page_" + str(page - 1)
        ))
    if end < total:
        nav.append(types.InlineKeyboardButton(
            text="▶️", callback_data="apt_ins_page_" + str(page + 1)
        ))
    if nav:
        m.add(*nav)

    skip_txt = "❌ بدون بیمه" if lang == "fa" else ("❌ بدون تأمين" if lang == "ar" else "❌ No insurance")
    m.add(types.InlineKeyboardButton(text=skip_txt, callback_data="apt_ins_pick_none"))
    return m


def payment_type_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton(
            text="1️⃣ " + MSG[lang]["payment_full"], callback_data="apt_paytype_full"
        ),
        types.InlineKeyboardButton(
            text="2️⃣ " + MSG[lang]["payment_insurance"], callback_data="apt_paytype_insurance"
        ),
    )
    return m


def priority_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton(
            text="1️⃣ " + MSG[lang]["priority_normal"], callback_data="apt_prio_normal"
        ),
        types.InlineKeyboardButton(
            text="2️⃣ " + MSG[lang]["priority_urgent"], callback_data="apt_prio_urgent"
        ),
    )
    return m


def apt_confirm_kb(lang: str):
    m = types.InlineKeyboardMarkup(row_width=2)
    yes_txt = "✅ بله" if lang == "fa" else ("✅ نعم" if lang == "ar" else "✅ Yes")
    no_txt = "❌ خیر" if lang == "fa" else ("❌ لا" if lang == "ar" else "❌ No")
    m.add(
        types.InlineKeyboardButton(text=yes_txt, callback_data="apt_confirm_yes"),
        types.InlineKeyboardButton(text=no_txt, callback_data="apt_confirm_no"),
    )
    return m


def pay_link_kb(lang: str, pay_url: str, amount: int, pid: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton(
        text=MSG[lang]["pay_button"].format(amount=str(amount)),
        url=pay_url,
    ))
    m.add(types.InlineKeyboardButton(
        text=MSG[lang]["pay_check_button"],
        callback_data="pay_check_" + pid,
    ))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


def invoice_kb(lang: str, apt_id: str):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton(
        text=MSG[lang]["invoice_button"],
        callback_data="invoice_" + apt_id,
    ))
    m.add(types.InlineKeyboardButton(text=MSG_BTN[lang]["btn_back"], callback_data="back_main"))
    return m


print("═══ PART 5/6 LOADED ═══ Logic + Keyboards ready")
# ═══════════════════════════════════════════════
# PROCESS QUERY — text router (main dispatcher)
# ═══════════════════════════════════════════════

def process_query(message, text: str, lang: str) -> bool:
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
            st = a.get("status", "pending")
            if st == "done":
                lines.append(MSG[lang]["pt_apt_line_done"].format(id=a["id"], doctor=dn))
            elif st == "confirmed" and a.get("date"):
                lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                    id=a["id"], doctor=dn, date=a["date"], time=a.get("time", "")
                ))
            else:
                lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a["id"], doctor=dn))
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
        reply_with_kb(
            message,
            MSG2[lang]["rights_title"] + "\n\n" + MSG2[lang]["rights_body"],
            back_kb(lang),
        )
        return True

    if is_simple_cmd(text, CMD_FOOD):
        reply_with_kb(
            message,
            MSG2[lang]["food_title"] + "\n\n" + MSG2[lang]["food_body"],
            back_kb(lang),
        )
        return True

    if is_simple_cmd(text, CMD_FLOWER):
        send_hope_flower(cid, lang)
        return True

    if is_simple_cmd(text, CMD_SOS):
        user_state[cid] = "awaiting_sos_choice"
        reply_with_kb(message, MSG2[lang]["sos_menu"])
        return True

    if is_simple_cmd(text, CMD_INVITE):
        code = get_or_create_referral_code(cid)
        link = build_referral_link(code)
        reply_with_kb(
            message,
            MSG2[lang]["ref_invite_msg"].format(code=code, link=link),
            back_kb(lang),
        )
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
        data = load_json(os.path.join(DATA_DIR, "elderly_homes.json"))
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

    # ─── Search by doctor name ───
    doc = search_by_doctor_name(text)
    if doc:
        doc_id = doc.get("id", "")
        user_temp.setdefault(cid, {})["doctor"] = doc
        reply_with_kb(message, format_doctor(doc, lang), doctor_action_kb(lang, doc_id))
        return True

    # ─── Search by specialty ───
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
            did = d.get("id", "")
            reply_with_kb(message, format_doctor(d, lang), doctor_action_kb(lang, did))
        if shown:
            user_temp.setdefault(cid, {})["doctor"] = shown[0]
        return True

    # ─── Search non-medical ───
    fn = search_non_medical(text)
    if fn:
        data = load_json(os.path.join(DATA_DIR, fn))
        if data:
            items = data[:10] if is_all_request(text) else data[:5]
            for item in items:
                reply_with_kb(message, format_generic(item, lang), back_kb(lang))
            return True

    # ─── AI fallback ───
    ai = get_ai(text, lang)
    if ai:
        reply_with_kb(message, ai + AI_DISCLAIMER[lang], back_kb(lang))
        return True

    reply_with_kb(message, MSG2[lang]["ai_unavailable"], back_kb(lang))
    return True


# ═══════════════════════════════════════════════
# CALLBACK QUERY HANDLER
# ═══════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    try:
        cid = call.message.chat.id
        lang = user_lang.get(cid, "fa")
        data = call.data or ""

        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        # ─── Rating ───
        if data.startswith("rate_"):
            parts = data.split("_")
            stars = int(parts[1])
            apt_id = parts[2]
            set_apt_rating(apt_id, stars)
            save_rating(apt_id, cid, stars, "")
            satisfaction_counter["count"] += 1

            if stars >= 4:
                satisfaction_counter["positive"] += 1
                update_patient_stage(cid, "followup", True)
                code = get_or_create_referral_code(cid)
                link = build_referral_link(code)
                bot.send_message(cid, MSG[lang]["rate_thanks_5" if stars == 5 else "rate_thanks_4"])
                bot.send_message(cid, MSG2[lang]["ref_invite_msg"].format(code=code, link=link))
            elif stars == 3:
                bot.send_message(cid, MSG[lang]["rate_thanks_3"])
            else:
                satisfaction_counter["negative"] += 1
                user_state[cid] = "awaiting_rate_feedback_" + apt_id
                bot.send_message(cid, MSG[lang]["rate_thanks_low"])
            return

        # ─── Channel ───
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
            if grant_channel_reward(cid):
                send_with_kb(cid, MSG_CH[lang]["msg_channel_done"], back_kb(lang))
                if ADMIN_CHAT_ID:
                    try:
                        bot.send_message(ADMIN_CHAT_ID, "📢 عضو جدید کانال: " + str(cid))
                    except Exception:
                        pass
            else:
                send_with_kb(cid, MSG_CH[lang]["msg_channel_already"], back_kb(lang))
            return

        # ─── Simple menu actions ───
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
            except Exception:
                page = 0
            try:
                bot.edit_message_text(
                    chat_id=cid,
                    message_id=call.message.message_id,
                    text=MSG[lang]["insurance_title"],
                    reply_markup=insurance_kb(lang, page),
                )
            except Exception:
                send_with_kb(cid, MSG[lang]["insurance_title"], insurance_kb(lang, page))
            return

        if data.startswith("ins_"):
            ins_id = data[4:]
            ins = find_insurance_by_id(ins_id)
            if not ins:
                send_with_kb(cid, MSG[lang]["insurance_not_found"], back_kb(lang))
                return
            send_with_kb(cid, format_insurance(ins, lang), insurance_action_kb(lang))
            return

        if data == "do_translator":
            send_with_kb(cid, MSG[lang]["translator_title"], translator_lang_kb(lang))
            return

        if data in ("tr_fa_ar", "tr_ar_fa", "tr_fa_en", "tr_en_fa"):
            parts = data.split("_")
            source, target = parts[1], parts[2]
            user_temp.setdefault(cid, {})["tr_source"] = source
            user_temp[cid]["tr_target"] = target
            user_state[cid] = "awaiting_voice_translate"
            send_with_kb(cid, MSG[lang]["translator_active"], back_kb(lang))
            return

        if data == "do_charter":
            send_with_kb(cid, MSG[lang]["charter_title"] + "\n\n" + MSG[lang]["charter_body"],
                         back_kb(lang))
            return

        if data == "do_deepseek":
            send_with_kb(cid, MSG[lang]["deepseek_title"], deepseek_kb(lang))
            return

        if data == "back_main":
            try:
                bot.edit_message_text(
                    chat_id=cid,
                    message_id=call.message.message_id,
                    text=MSG2[lang]["menu_main"],
                    reply_markup=main_menu_kb(lang),
                )
            except Exception:
                show_main_menu(call.message, lang)
            return

        # ─── Menu sections ───
        if data == "menu_docs":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["docs_list_title"], reply_markup=specialties_kb(lang),
                )
            except Exception:
                send_with_kb(cid, MSG2[lang]["docs_list_title"], specialties_kb(lang))
            return

        if data.startswith("spec_"):
            fn = data[5:] + ".json"
            docs = load_json(os.path.join(DATA_DIR, "doctors", fn))
            if not docs:
                send_with_kb(cid, "❌ اطلاعاتی یافت نشد.", back_kb(lang))
                return
            docs = [d for d in docs if d.get("status", "active") != "inactive"]
            if not docs:
                send_with_kb(cid, "❌ پزشکی نیست.", back_kb(lang))
                return

            def sc(x):
                r = x.get("ratings", {})
                if isinstance(r, dict) and "patient_satisfaction_score" in r:
                    return r["patient_satisfaction_score"]
                return x.get("patient_satisfaction_score", x.get("rating", 0))

            try:
                docs.sort(key=sc, reverse=True)
            except Exception:
                pass

            for d in docs[:3]:
                did = d.get("id", "")
                send_with_kb(cid, format_doctor(d, lang), doctor_action_kb(lang, did))
            return

        if data == "menu_nonmed":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["nonmed_list_title"], reply_markup=nonmed_kb(lang),
                )
            except Exception:
                send_with_kb(cid, MSG2[lang]["nonmed_list_title"], nonmed_kb(lang))
            return

        if data.startswith("non_"):
            fn = data[4:] + ".json"
            items = load_json(os.path.join(DATA_DIR, fn))
            if not items:
                send_with_kb(cid, "❌ اطلاعاتی یافت نشد.", back_kb(lang))
                return
            for item in items[:5]:
                send_with_kb(cid, format_generic(item, lang), back_kb(lang))
            return

        if data == "menu_tourist":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["tourist_list_title"], reply_markup=tourist_kb(lang),
                )
            except Exception:
                send_with_kb(cid, MSG2[lang]["tourist_list_title"], tourist_kb(lang))
            return

        if data == "menu_para":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["para_list_title"], reply_markup=para_kb(lang),
                )
            except Exception:
                send_with_kb(cid, MSG2[lang]["para_list_title"], para_kb(lang))
            return

        if data.startswith("para_"):
            service = data[5:].replace("_", " ")
            items = load_json(os.path.join(DATA_DIR, "paramedical.json"))
            if not items:
                send_with_kb(cid, "❌ اطلاعاتی یافت نشد.", back_kb(lang))
                return
            # filter by service keyword
            matches = []
            kw = service.lower()
            for it in items:
                blob = json.dumps(it, ensure_ascii=False).lower()
                if kw in blob or any(w in blob for w in kw.split()):
                    matches.append(it)
            for it in (matches[:5] or items[:3]):
                send_with_kb(cid, format_generic(it, lang), back_kb(lang))
            return

        if data == "menu_elder":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["elderly_list_title"], reply_markup=elderly_kb(lang),
                )
            except Exception:
                send_with_kb(cid, MSG2[lang]["elderly_list_title"], elderly_kb(lang))
            return

        if data == "elder_all":
            items = load_json(os.path.join(DATA_DIR, "elderly_homes.json"))
            if items:
                send_with_kb(cid, MSG2[lang]["elderly_all_title"])
                for it in items[:10]:
                    send_with_kb(cid, format_generic(it, lang), back_kb(lang))
            return

        if data == "menu_pkg":
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG2[lang]["package_title"], reply_markup=package_kb(lang),
                )
            except Exception:
                send_with_kb(cid, MSG2[lang]["package_title"], package_kb(lang))
            return

        if data == "pkg_order":
            send_with_kb(cid, MSG2[lang]["package_pitch"])
            send_with_kb(cid, MSG2[lang]["package_value"])
            send_with_kb(cid, MSG2[lang]["package_cta"])
            user_state[cid] = "awaiting_pkg_name"
            send_with_kb(cid, MSG2[lang]["package_ask_name"])
            return

        # ─── Doctor actions ───
        if data.startswith("call_"):
            doc_id = data[5:]
            doc = _find_doctor_by_id(doc_id)
            if not doc:
                send_with_kb(cid, "❌ پزشک پیدا نشد.", back_kb(lang))
                return
            phone = doc.get("phone", "")
            send_with_kb(cid, "📞 " + str(phone), back_kb(lang))
            return

        if data.startswith("book_"):
            doc_id = data[5:]
            doc = _find_doctor_by_id(doc_id)
            if not doc:
                send_with_kb(cid, "❌ پزشک پیدا نشد.", back_kb(lang))
                return
            user_temp.setdefault(cid, {})["doctor"] = doc
            user_temp[cid]["apt_step"] = "office"
            user_state[cid] = "apt_choose_office"
            send_with_kb(cid, MSG[lang]["apt_choose_office"], offices_kb(lang, doc))
            return

        # ─── Appointment flow — office ───
        if data.startswith("office_"):
            try:
                idx = int(data.split("_")[1])
            except Exception:
                idx = 0
            doctor = user_temp.get(cid, {}).get("doctor", {})
            offices = doctor.get("offices", [])
            if isinstance(offices, list) and offices and idx < len(offices):
                off = offices[idx]
                office_name = (
                    off.get("name_" + lang, "")
                    or off.get("name_fa", "")
                    or off.get("address_fa", "")
                )
            else:
                office_name = (
                    get_value(doctor, "office_address", lang)
                    or get_value(doctor, "address", lang)
                    or "—"
                )
            user_temp.setdefault(cid, {})["office"] = office_name
            user_state[cid] = "apt_choose_date"
            send_with_kb(cid, MSG[lang]["apt_choose_date"], date_kb(lang))
            return

        # ─── Appointment flow — date ───
        if data.startswith("date_"):
            parts = data.split("_")
            try:
                jy, jm, jd = int(parts[1]), int(parts[2]), int(parts[3])
                date_str = "{}/{}/{}".format(str(jy), str(jm).zfill(2), str(jd).zfill(2))
            except Exception:
                date_str = ""
            user_temp.setdefault(cid, {})["date"] = date_str
            user_state[cid] = "apt_choose_time"
            send_with_kb(cid, MSG[lang]["apt_choose_time"], time_kb(lang, date_str))
            return

        # ─── Appointment flow — time ───
        if data.startswith("time_"):
            parts = data.split("_", 2)
            try:
                tstr = parts[2].replace("-", ":")
            except Exception:
                tstr = ""
            user_temp.setdefault(cid, {})["time"] = tstr
            user_state[cid] = "apt_ask_national_id"
            send_with_kb(cid, MSG[lang]["apt_ask_national_id"])
            return

        # ─── Appointment flow — insurance ───
        if data == "apt_ins_yes":
            user_state[cid] = "apt_choose_insurance"
            send_with_kb(cid, MSG[lang]["apt_choose_insurance"], apt_insurance_pick_kb(lang, 0))
            return

        if data == "apt_ins_no":
            user_temp.setdefault(cid, {})["insurance_id"] = ""
            user_temp[cid]["insurance_name"] = ""
            user_state[cid] = "apt_choose_payment_type"
            send_with_kb(cid, MSG[lang]["apt_choose_payment_type"], payment_type_kb(lang))
            return

        if data.startswith("apt_ins_page_"):
            try:
                page = int(data.replace("apt_ins_page_", ""))
            except Exception:
                page = 0
            try:
                bot.edit_message_text(
                    chat_id=cid, message_id=call.message.message_id,
                    text=MSG[lang]["apt_choose_insurance"],
                    reply_markup=apt_insurance_pick_kb(lang, page),
                )
            except Exception:
                send_with_kb(cid, MSG[lang]["apt_choose_insurance"], apt_insurance_pick_kb(lang, page))
            return

        if data.startswith("apt_ins_pick_"):
            ins_id = data.replace("apt_ins_pick_", "")
            if ins_id == "none":
                user_temp.setdefault(cid, {})["insurance_id"] = ""
                user_temp[cid]["insurance_name"] = ""
            else:
                ins = find_insurance_by_id(ins_id)
                if ins:
                    user_temp.setdefault(cid, {})["insurance_id"] = ins_id
                    user_temp[cid]["insurance_name"] = (
                        ins.get("name_" + lang, "")
                        or ins.get("name_fa", "")
                        or ins_id
                    )
            user_state[cid] = "apt_choose_payment_type"
            send_with_kb(cid, MSG[lang]["apt_choose_payment_type"], payment_type_kb(lang))
            return

        # ─── Appointment flow — payment type ───
        if data == "apt_paytype_full":
            user_temp.setdefault(cid, {})["payment_type"] = "full"
            user_state[cid] = "apt_choose_priority"
            send_with_kb(cid, MSG[lang]["apt_ask_priority"], priority_kb(lang))
            return

        if data == "apt_paytype_insurance":
            user_temp.setdefault(cid, {})["payment_type"] = "insurance"
            user_state[cid] = "apt_choose_priority"
            send_with_kb(cid, MSG[lang]["apt_ask_priority"], priority_kb(lang))
            return

        # ─── Appointment flow — priority ───
        if data in ("apt_prio_normal", "apt_prio_urgent"):
            prio = "normal" if data.endswith("normal") else "urgent"
            user_temp.setdefault(cid, {})["priority"] = prio

            # resolve amount
            doctor = user_temp[cid].get("doctor", {})
            ins_id = user_temp[cid].get("insurance_id", "")
            ptype = user_temp[cid].get("payment_type", "full")
            amount = resolve_price_for_doctor(doctor, ins_id, ptype, lang)
            if prio == "urgent":
                amount = int(amount * 1.5)
            user_temp[cid]["amount"] = amount

            user_state[cid] = "awaiting_apt_name"
            send_with_kb(cid, MSG[lang]["apt_name"])
            return

        # ─── Appointment flow — final confirm buttons ───
        if data == "apt_confirm_yes":
            _finalize_appointment(call.message, cid, lang)
            return

        if data == "apt_confirm_no":
            user_temp.pop(cid, None)
            user_state[cid] = "active"
            send_with_kb(cid, MSG[lang]["apt_cancelled"], back_kb(lang))
            return

        # ─── Payment check ───
        if data.startswith("pay_check_"):
            pid = data.replace("pay_check_", "")
            pay = find_payment_by_id(pid)
            if not pay:
                send_with_kb(cid, MSG[lang]["pay_not_found"], back_kb(lang))
                return
            if pay.get("status") == "paid":
                send_with_kb(cid, MSG[lang]["pay_success"].format(
                    ref=pay.get("ref_id", "-"), pid=pid
                ), back_kb(lang))
                return
            # try verify
            res = zarinpal_verify(pay.get("authority", ""), pay.get("amount", 0))
            if res["ok"]:
                update_payment(pid, {
                    "status": "paid",
                    "ref_id": res["ref_id"],
                    "verified_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
                })
                mark_apt_paid(pay.get("apt_id", ""), res["ref_id"], pid)
                send_with_kb(cid, MSG[lang]["pay_success"].format(
                    ref=res["ref_id"], pid=pid
                ), back_kb(lang))
                _send_invoice_to_user(cid, lang, pay.get("apt_id", ""), res["ref_id"])
            else:
                send_with_kb(cid, MSG[lang]["pay_pending"], back_kb(lang))
            return

        # ─── Invoice ───
        if data.startswith("invoice_"):
            apt_id = data.replace("invoice_", "")
            apt = find_appointment(apt_id)
            if not apt:
                send_with_kb(cid, "❌", back_kb(lang))
                return
            _send_invoice_to_user(cid, lang, apt_id, apt.get("payment_ref", ""))

        # ─── Simple menu actions (from keyboard) ───
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
                st = a.get("status", "pending")
                if st == "done":
                    lines.append(MSG[lang]["pt_apt_line_done"].format(id=a["id"], doctor=dn))
                elif st == "confirmed" and a.get("date"):
                    lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                        id=a["id"], doctor=dn, date=a["date"], time=a.get("time", "")
                    ))
                else:
                    lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a["id"], doctor=dn))
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
            send_with_kb(cid, MSG2[lang]["ref_invite_msg"].format(code=code, link=link),
                         back_kb(lang))
            return

        if data == "do_help":
            send_with_kb(cid,
                         MSG2[lang]["rights_title"] + "\n\n" + MSG2[lang]["rights_body"],
                         back_kb(lang))
            return

    except Exception as e:
        print("CB_ERR:", str(e))


# ═══════════════════════════════════════════════
# APPOINTMENT HELPERS
# ═══════════════════════════════════════════════

def _find_doctor_by_id(doc_id: str):
    for fn in set(SPECIALTY_MAP.values()):
        items = load_json(os.path.join(DATA_DIR, "doctors", fn))
        for d in items:
            if d.get("id", "") == doc_id:
                return d
    return None


def _finalize_appointment(message, cid: int, lang: str):
    """Called when user taps ✅ Yes on final confirmation."""
    t = user_temp.get(cid, {})
    doc = t.get("doctor", {})
    pname = t.get("name", "")
    pphone = t.get("phone", "")
    nid = t.get("national_id", "")
    office = t.get("office", "")
    date_str = t.get("date", "")
    time_str = t.get("time", "")
    ins_id = t.get("insurance_id", "")
    ins_name = t.get("insurance_name", "")
    amount = int(t.get("amount", 0))
    ptype = t.get("payment_type", "full")
    prio = t.get("priority", "normal")

    try:
        apt = create_appointment(
            doc, pname, pphone, cid, lang,
            national_id=nid, office=office,
            insurance_id=ins_id, insurance_name=ins_name,
            amount=amount, payment_type=ptype,
            priority=prio, date=date_str, time_str=time_str,
        )
        patient = create_or_get_patient(cid, pname, pphone, lang)
        add_appointment_to_patient(cid, apt["id"])
        update_patient_stage(cid, "doctor", True)
        register_appointment_for_stats(cid)

        dn = get_value(doc, "name", lang) or get_value(doc, "name", "fa") or ""
        bot.send_message(cid, MSG[lang]["apt_submitted"].format(id=apt["id"], doctor=dn))
        bot.send_message(cid, MSG[lang]["pt_created"].format(code=patient["code"]))
        send_hope_for_stage(cid, lang, "request")

        # ─── Payment link ───
        _start_payment(cid, lang, apt["id"], amount)

        # ─── Notify admin ───
        if ADMIN_CHAT_ID:
            try:
                dphone = doc.get("phone", "")
                bot.send_message(ADMIN_CHAT_ID, MSG["fa"]["apt_admin_new"].format(
                    id=apt["id"], name=pname, phone=pphone, nid=nid,
                    doctor=dn, dphone=dphone, office=office,
                    date=date_str, time=time_str,
                    insurance=ins_name or "—", amount=str(amount),
                    priority=MSG[lang].get("priority_" + prio, prio),
                ))
            except Exception as e:
                print("ADMIN_NOTIFY_ERR:", str(e))

        user_state[cid] = "awaiting_comp_ask"
        bot.send_message(cid, MSG2[lang]["comp_ask"])
    except Exception as e:
        print("APT_FINALIZE_ERR:", str(e))
        bot.send_message(cid, MSG[lang]["apt_error"])
    finally:
        user_temp.pop(cid, None)


def _start_payment(cid: int, lang: str, apt_id: str, amount: int):
    """Create a payment record and send a payment link."""
    if amount <= 0:
        return
    try:
        bot.send_message(cid, MSG[lang]["pay_creating"])
        callback_url = "https://ble.ir/" + BOT_USERNAME
        desc = "Shiraz Medical - Appointment " + apt_id
        res = zarinpal_request(amount, desc, callback_url)

        if not res["ok"]:
            print("ZP_REQ_FAIL:", res["error"])
            # still create a manual record
            pay = create_payment_record(cid, apt_id, amount, authority="", status="pending")
            bot.send_message(cid, MSG[lang]["pay_error"], reply_markup=back_kb(lang))
            return

        pay = create_payment_record(cid, apt_id, amount,
                                    authority=res["authority"], status="pending")
        update_appointment(apt_id, {"payment_id": pay["id"]})

        msg = MSG[lang]["pay_link"].format(
            pid=pay["id"], amount=str(amount), apt_id=apt_id
        )
        bot.send_message(
            cid, msg,
            reply_markup=pay_link_kb(lang, res["url"], amount, pay["id"])
        )
    except Exception as e:
        print("PAY_START_ERR:", str(e))


def _send_invoice_to_user(cid: int, lang: str, apt_id: str, ref_id: str = ""):
    """Send PDF invoice if reportlab is available, else text fallback."""
    apt = find_appointment(apt_id)
    if not apt:
        return
    try:
        bot.send_message(cid, MSG[lang]["invoice_generating"])
        pdf_bytes = generate_invoice_pdf(apt, lang)
        if pdf_bytes:
            bot.send_document(
                cid,
                io.BytesIO(pdf_bytes),
                visible_file_name="invoice_" + apt_id + ".pdf",
                caption=MSG[lang]["invoice_caption"].format(
                    apt_id=apt_id,
                    amount=str(apt.get("amount", 0)),
                    ref=ref_id or apt.get("payment_ref", "-"),
                ),
            )
            update_appointment(apt_id, {"invoice_sent": True})
        else:
            # fallback text
            txt = "📄 " + apt_id + "\n💰 " + str(apt.get("amount", 0)) + " تومان"
            bot.send_message(cid, txt, reply_markup=back_kb(lang))
    except Exception as e:
        print("INVOICE_ERR:", str(e))
        bot.send_message(cid, MSG[lang]["retry"], reply_markup=back_kb(lang))


# ═══════════════════════════════════════════════
# TEXT MESSAGE HANDLER (main state machine)
# ═══════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(message):
    cid = message.chat.id
    user_state[cid] = "choose_lang"
    bot.reply_to(message, START_MSG)


@bot.message_handler(commands=["menu"])
def cmd_menu(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    show_main_menu(message, lang)


@bot.message_handler(commands=["lang"])
def cmd_lang(message):
    cid = message.chat.id
    user_state[cid] = "choose_lang"
    bot.reply_to(message, START_MSG)


@bot.message_handler(commands=["myfile"])
def cmd_myfile(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    p = get_patient_by_chat(cid)
    bot.reply_to(message, format_patient_file(p, lang))


@bot.message_handler(commands=["myapt"])
def cmd_myapt(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    apts = get_patient_appointments(cid)
    if not apts:
        bot.reply_to(message, MSG[lang]["apt_none"])
        return
    lines = [MSG[lang]["apt_my"]]
    for a in apts[-5:]:
        dn = a.get("doctor_name_" + lang) or a.get("doctor_name_fa", "")
        st = a.get("status", "pending")
        if st == "done":
            lines.append(MSG[lang]["pt_apt_line_done"].format(id=a["id"], doctor=dn))
        elif st == "confirmed" and a.get("date"):
            lines.append(MSG[lang]["pt_apt_line_confirmed"].format(
                id=a["id"], doctor=dn, date=a["date"], time=a.get("time", "")
            ))
        else:
            lines.append(MSG[lang]["pt_apt_line_pending"].format(id=a["id"], doctor=dn))
    bot.reply_to(message, "\n\n".join(lines))


@bot.message_handler(commands=["mycode"])
def cmd_mycode(message):
    cid = message.chat.id
    lang = user_lang.get(cid, "fa")
    code = get_or_create_referral_code(cid)
    link = build_referral_link(code)
    bot.reply_to(message, MSG2[lang]["ref_your_code"].format(code=code, link=link))


@bot.message_handler(commands=["id"])
def cmd_id(message):
    bot.reply_to(message, str(message.chat.id))


# ─── Admin commands ───

@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    meta = get_meta_info()
    apt_data = load_appointments()
    pending = [a for a in apt_data["appointments"] if a.get("status") == "pending"]
    confirmed = [a for a in apt_data["appointments"] if a.get("status") == "confirmed"]
    done = [a for a in apt_data["appointments"] if a.get("status") == "done"]
    rated = [a for a in apt_data["appointments"] if a.get("rating", 0) > 0]
    avg_rating = 0
    if rated:
        avg_rating = round(sum(a["rating"] for a in rated) / len(rated), 1)

    complaints = load_complaints().get("complaints", [])
    new_complaints = [c for c in complaints if c.get("status") == "new"]
    pkg_data = load_packages()
    pending_pkgs = [p for p in pkg_data["packages"] if p.get("status") == "pending"]
    stats = get_user_stats()

    lines = ["📊 وضعیت ربات"]
    if meta:
        lines.append("آخرین آپدیت: " + str(meta.get("last_update", "نامشخص")))
    lines.append("")
    lines.append("👥 کاربران:")
    lines.append("• کل: " + str(stats["total"]))
    lines.append("• امروز (DAU): " + str(stats["dau"]))
    lines.append("• ۷ روز (WAU): " + str(stats["wau"]))
    lines.append("• ۳۰ روز (MAU): " + str(stats["mau"]))
    lines.append("")
    lines.append("📈 نرخ تبدیل: " + str(stats["conv"]) + "%")
    lines.append("📢 عضو کانال: " + str(stats["channel"]))
    lines.append("")
    lines.append("📅 نوبت‌ها:")
    lines.append("• در انتظار: " + str(len(pending)))
    lines.append("• تأیید شده: " + str(len(confirmed)))
    lines.append("• انجام شده: " + str(len(done)))
    for a in pending[-5:]:
        dn = a.get("doctor_name_fa", "")
        lines.append("• " + a["id"] + " — " + a.get("patient_name", "") + " — " + str(dn))
    lines.append("")
    lines.append("⭐ نظرسنجی:")
    lines.append("• تعداد: " + str(len(rated)))
    lines.append("• میانگین: " + str(avg_rating) + "/5")
    lines.append("")
    lines.append("💎 پکیج در انتظار: " + str(len(pending_pkgs)))
    for p in pending_pkgs[-3:]:
        lines.append("• " + p["id"] + " — " + p.get("name", "") + " — " + p.get("phone", ""))
    lines.append("")
    lines.append("📩 شکایت جدید: " + str(len(new_complaints)))
    lines.append("")
    lines.append("⏰ سرور (local): " + local_now().strftime("%Y/%m/%d %H:%M"))
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["confirm"])
def cmd_confirm(message):
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
    update_patient_stage(apt.get("patient_chat_id"), "date", True)

    p_cid = apt.get("patient_chat_id", "")
    p_lang = apt.get("patient_lang", "fa")
    if p_cid:
        dn = apt.get("doctor_name_" + p_lang) or apt.get("doctor_name_fa", "")
        ad = apt.get("doctor_address_" + p_lang) or apt.get("doctor_address_fa", "")
        try:
            bot.send_message(p_cid, MSG[p_lang]["apt_patient_confirmed"].format(
                id=apt_id, doctor=dn, date=date_str, time=time_str, address=ad,
            ))
            send_hope_for_stage(p_cid, p_lang, "date")
        except Exception:
            pass


@bot.message_handler(commands=["done"])
def cmd_done(message):
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
    p_cid = apt.get("patient_chat_id", "")
    p_lang = apt.get("patient_lang", "fa")
    update_patient_stage(p_cid, "treatment", True)
    if p_cid:
        try:
            bot.send_message(p_cid, MSG[p_lang]["apt_done_patient"],
                             reply_markup=rate_kb(p_lang, apt_id))
        except Exception:
            pass


@bot.message_handler(commands=["pt"])
def cmd_pt(message):
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
    bot.reply_to(message, format_patient_file(p, p.get("lang", "fa")))


@bot.message_handler(commands=["activate", "deactivate"])
def cmd_toggle_doctor(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "فرمت: /activate doc_001")
        return
    doc_id = parts[1]
    new_status = "active" if "activate" in message.text.split()[0] else "inactive"
    if set_doctor_status(doc_id, new_status):
        bot.reply_to(message, "✅ " + new_status)
    else:
        bot.reply_to(message, "❌ پیدا نشد.")


@bot.message_handler(commands=["reload_insurance"])
def cmd_reload_insurance(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return
    n = len(reload_insurances())
    bot.reply_to(message, "✅ بیمه‌ها دوباره لود شد: " + str(n))


# ─── Voice ───

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
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
        token = BALE_BOT_TOKEN or TELEGRAM_BOT_TOKEN
        if PLATFORM == "bale":
            file_url = "https://tapi.bale.ai/file/bot" + token + "/" + file_info.file_path
        else:
            file_url = "https://api.telegram.org/file/bot" + token + "/" + file_info.file_path

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
        bot.reply_to(message, result_msg,
                     reply_markup=translator_result_kb(lang, translated, target))
    except Exception as e:
        print("VOICE_ERR:", str(e))
        bot.reply_to(message, MSG[lang]["translator_error"], reply_markup=back_kb(lang))


@bot.message_handler(content_types=["photo", "audio", "document", "video", "sticker"])
def handle_other(message):
    cid = message.chat.id
    if cid in user_lang:
        bot.reply_to(message, MSG[user_lang[cid]]["text_only"])
    else:
        user_state[cid] = "choose_lang"
        bot.reply_to(message, START_MSG)


# ═══════════════════════════════════════════════
# MAIN TEXT HANDLER (state machine)
# ═══════════════════════════════════════════════

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    cid = message.chat.id
    text = message.text or ""
    state = user_state.get(cid)

    # ─── Language selection / first contact ───
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
        except Exception:
            bot.reply_to(message, MSG[lang]["welcome"])
        try_apply_start_param(message, text, lang)
        return

    lang = user_lang.get(cid, "fa")
    t = clean(text)
    user_name = get_user_name(message)

    # ─── Escape words ───
    ESCAPE_WORDS = {"منو", "لغو", "انصراف", "menu", "cancel"}
    if t in ESCAPE_WORDS:
        user_state[cid] = "active"
        user_temp.pop(cid, None)
        show_main_menu(message, lang)
        return

    # ─── Rate feedback ───
    if state and state.startswith("awaiting_rate_feedback_"):
        apt_id = state.replace("awaiting_rate_feedback_", "")
        apt = find_appointment(apt_id)
        pname = apt.get("patient_name", "") if apt else ""
        try:
            bot.send_message(ADMIN_CHAT_ID, MSG["fa"]["rate_thanks_low_admin"].format(
                id=apt_id, stars=apt.get("rating", 0) if apt else 0,
                name=pname, cid=cid, text=text,
            ))
        except Exception:
            pass
        reply_with_kb(message, MSG[lang]["rate_feedback_thanks"], back_kb(lang))
        user_state[cid] = "active"
        return

    # ─── Voice-translate mode ───
    if state == "awaiting_voice_translate":
        bot.reply_to(message, MSG[lang]["translator_active"])
        return

    # ─── Package flow ───
    if state == "awaiting_pkg_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG2[lang]["package_ask_name"])
            return
        user_temp.setdefault(cid, {})["pkg_name"] = text.strip()
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
            bot.reply_to(message, MSG2[lang]["package_saved"].format(id=pkg["id"]))
            if ADMIN_CHAT_ID:
                try:
                    bot.send_message(ADMIN_CHAT_ID, MSG2["fa"]["package_admin_new"].format(
                        id=pkg["id"], name=pkg_name, phone=phone, cid=cid,
                    ))
                except Exception:
                    pass
        except Exception as e:
            print("PKG_ERR:", str(e))
            bot.reply_to(message, MSG[lang]["apt_error"])
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    # ─── Appointment: name ───
    if state == "awaiting_apt_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG[lang]["apt_name"])
            return
        user_temp.setdefault(cid, {})["name"] = text.strip()
        user_state[cid] = "awaiting_apt_phone"
        bot.reply_to(message, MSG[lang]["apt_phone"])
        return

    # ─── Appointment: phone ───
    if state == "awaiting_apt_phone":
        phone = validate_phone(text)
        if not phone:
            bot.reply_to(message, MSG[lang]["apt_phone"])
            return
        user_temp.setdefault(cid, {})["phone"] = phone

        # ─── Reconfirmation card ───
        t_ = user_temp[cid]
        doc = t_.get("doctor", {})
        dn = get_value(doc, "name", lang) or get_value(doc, "name", "fa") or ""
        card = MSG[lang]["apt_confirm_final"].format(
            name=t_.get("name", ""),
            phone=phone,
            nid=t_.get("national_id", ""),
            doctor=dn,
            office=t_.get("office", "—"),
            date=t_.get("date", "—"),
            time=t_.get("time", "—"),
            insurance=t_.get("insurance_name", "—") or "—",
            amount=str(t_.get("amount", 0)),
            priority=MSG[lang].get("priority_" + t_.get("priority", "normal"), t_.get("priority", "")),
        )
        user_state[cid] = "awaiting_apt_confirm"
        bot.reply_to(message, card, reply_markup=apt_confirm_kb(lang))
        return

    # ─── Appointment: national ID (text input) ───
    if state == "apt_ask_national_id":
        nid = validate_iranian_national_id(text)
        if not nid:
            bot.reply_to(message, MSG[lang]["apt_invalid_national_id"])
            return
        user_temp.setdefault(cid, {})["national_id"] = nid
        user_state[cid] = "apt_insurance_choice"
        bot.reply_to(message, MSG[lang]["apt_ask_insurance"], reply_markup=insurance_choice_kb(lang))
        return

    # ─── Appointment: final yes/no via text (fallback to buttons) ───
    if state == "awaiting_apt_confirm":
        if t in YES_WORDS:
            _finalize_appointment(message, cid, lang)
            return
        if t in NO_WORDS:
            user_temp.pop(cid, None)
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            ask_more(message)
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
        return

    # ─── Companion flow ───
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
        user_temp.setdefault(cid, {})["comp_name"] = text.strip()
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

    # ─── Complaint flow ───
    if state == "awaiting_complaint_menu":
        cat_map = {
            "1": "doctor", "2": "center", "3": "accommodation",
            "4": "transport", "5": "general",
        }
        if t in ("6",):
            user_state[cid] = "active"
            bot.reply_to(message, MSG2[lang]["comp_voice_skip"])
            return
        if t in cat_map:
            user_temp.setdefault(cid, {})["comp_category"] = cat_map[t]
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
        bot.reply_to(message, MSG2[lang]["comp_voice_saved"].format(id=c["id"]))
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(ADMIN_CHAT_ID, MSG2["fa"]["comp_voice_admin"].format(
                    id=c["id"], category=category, name=name, cid=cid, text=text,
                ))
            except Exception:
                pass
        user_temp.pop(cid, None)
        user_state[cid] = "active"
        ask_more(message)
        return

    # ─── Med flow ───
    if state == "awaiting_med_menu":
        if t == "1":
            user_state[cid] = "awaiting_med_name"
            bot.reply_to(message, MSG2[lang]["med_ask_name"])
            return
        if t == "2":
            meds = get_user_meds(cid)
            if not meds:
                bot.reply_to(message, MSG2[lang]["med_none"])
            else:
                lines = ["⏰:"]
                for m in meds:
                    lines.append("💊 " + m["name"] + " — " + m["time"])
                bot.reply_to(message, "\n".join(lines))
            user_state[cid] = "active"
            ask_more(message)
            return
        if t == "3":
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            return
        user_state[cid] = "active"

    if state == "awaiting_med_name":
        if len(text.strip()) < 2:
            bot.reply_to(message, MSG2[lang]["med_ask_name"])
            return
        user_temp.setdefault(cid, {})["med_name"] = text.strip()
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

    # ─── SOS flow ───
    if state == "awaiting_sos_choice":
        if t == "1":
            bot.reply_to(message, MSG2[lang]["sos_115"])
            user_state[cid] = "active"
            return
        if t == "2":
            data = load_json(os.path.join(DATA_DIR, "hospitals.json"))
            for h in data[:3]:
                n = get_value(h, "name", lang) or ""
                a = get_value(h, "address", lang) or ""
                p = get_value(h, "phone", lang) or h.get("phone", "")
                bot.reply_to(message, "🏥 " + str(n) + "\n📍 " + str(a) + "\n📞 " + str(p))
            user_state[cid] = "active"
            return
        if t == "3":
            bot.reply_to(message, MSG2[lang]["sos_first_aid"])
            user_state[cid] = "active"
            return
        if t == "4":
            comp = get_companion(cid)
            if not comp:
                bot.reply_to(message, MSG2[lang]["sos_no_companion"])
            else:
                bot.reply_to(message, "✅ " + str(comp.get("name", "")) + " — " + str(comp.get("phone", "")))
            user_state[cid] = "active"
            return
        if t == "5":
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["apt_cancelled"])
            return
        bot.reply_to(message, MSG[lang]["apt_invalid"])
        return

    # ─── Delete confirm ───
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

    # ─── "Any other question?" ───
    if state == "awaiting_more":
        if t in YES_WORDS:
            user_state[cid] = "active"
            bot.reply_to(message, MSG[lang]["go"])
            return
        user_state[cid] = "active"

    # ─── Emergency check ───
    if is_emergency(text):
        bot.reply_to(message, EMERGENCY_RESP[lang])
        ask_more(message)
        return

    # ─── Main dispatcher ───
    old_state = user_state.get(cid)
    answered = process_query(message, text, lang)
    new_state = user_state.get(cid)
    if new_state != old_state and answered:
        return
    if not answered:
        bot.reply_to(message, MSG[lang]["retry"])
    if new_state == old_state or not answered:
        ask_more(message)


# ═══════════════════════════════════════════════
# STARTUP BANNER + THREADS + POLLING
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 55)
    print("  Shiraz Medical Bot — v46 (Full Featured)")
    print("═" * 55)
    print("Platform         :", PLATFORM)
    print("Data dir         :", DATA_DIR)
    print("Admin chat       :", ADMIN_CHAT_ID or "(not set)")
    print("Timezone offset  : +" + str(TIMEZONE_OFFSET_HOURS) + "h")
    print("jdatetime        :", HAS_JDATETIME)
    print("reportlab        :", HAS_REPORTLAB)
    print("qrcode           :", HAS_QRCODE)
    print("Zarinpal sandbox :", ZARINPAL_SANDBOX)
    print("AI model         :", AI_MODEL)
    print("STT model        :", STT_MODEL)
    print("Specialties      :", len(set(SPECIALTY_MAP.values())))
    print("Insurances       :", len(load_all_insurances()))
    print("═" * 55)

    if not HAS_JDATETIME:
        print("⚠️  jdatetime not installed — using fallback converter.")
    if not HAS_REPORTLAB:
        print("⚠️  reportlab not installed — invoice falls back to text.")
    if not HAS_QRCODE:
        print("⚠️  qrcode not installed — PDF invoice will have no QR.")

    # Reminder thread
    try:
        reminder_thread = threading.Thread(target=reminder_worker, daemon=True)
        reminder_thread.start()
        print("✅ Reminder thread started.")
    except Exception as e:
        print("❌ Reminder thread failed:", str(e))

    print("🚀 Polling started...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print("POLL_ERR:", str(e))
            time_module.sleep(5)