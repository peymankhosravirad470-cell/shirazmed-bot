# -*- coding: utf-8 -*-
"""
🩺 مشاور سلامت شیراز مدیکال (مأموریت مکمل — بخش ۲ و ۳ و ۴)

مهم و الزامی (نقل از دستور محصول):
- این بخش «تشخیص پزشکی» نمی‌دهد و «دارو تجویز» نمی‌کند؛ فقط فوریت را
  تخمین می‌زند و به متخصص/اورژانس ارجاع می‌دهد.
- در علائم تهدیدکنندهٔ حیات، تماس فوری با اورژانس مقدم بر ارجاع عادی است؛
  بیمار را معطل پرسش‌های طولانی نمی‌کنیم (نشانهٔ خطر فوری → مستقیم اورژانس).
- ربات هرگز ادعا نمی‌کند آمبولانس اعزام شده یا اورژانس مطلع شده؛ چون
  اتصال تأییدشده‌ای با مرکز مربوطه وجود ندارد. فقط «اطلاعات تماس» و
  «متن آماده برای اپراتور» ارائه می‌شود.
- شمارهٔ اورژانس بر اساس کشور بیمار؛ اگر کشور مشخص نیست ابتدا پرسیده می‌شود.
- حریم خصوصی: موقعیت مکانی فقط با رضایت صریح (دکمهٔ ارسال موقعیت) و صرفاً
  در «متن آماده» درج می‌شود؛ هیچ اطلاعاتی بدون اجازه ارسال نمی‌شود.

محتوای علائم با ساختار متخصص‌محور (تعریف علامت + نشانه‌های خطر + پرسش‌های
تریاژ کوتاه) نوشته شده تا بازبینی و اعتبارسنجی توسط پزشکان واجد صلاحیت
به‌سادگی ممکن باشد (فقط همین فایل ویرایش می‌شود).
"""

from __future__ import annotations

# ── شماره‌های اورژانس کشورها (راستی‌آزمایی‌شده) ──────────────────────────────
# منبع: فهرست جهانی شماره‌های اورژانس (ویکی‌پدیا) + پورتال رسمی gov.om و
# راهنمای گردشگران امارات/قطر. برای کشورهای ناموجود: 112 استاندارد GSM.
EMERGENCY_NUMBERS: dict[str, dict] = {
    "ir": {"label": {"fa": "ایران 🇮🇷", "en": "Iran 🇮🇷", "ar": "إيران 🇮🇷"}, "ambulance": "115", "note": {"fa": "اورژانس پیش‌بیمارستانی", "en": "Pre-hospital EMS", "ar": "الإسعاف"}},
    "iq": {"label": {"fa": "عراق 🇮🇶", "en": "Iraq 🇮🇶", "ar": "العراق 🇮🇶"}, "ambulance": "122", "alt": "112", "note": {"fa": "آمبولانس ۱۲۲؛ ۱۱۲ روی موبایل (GSM)", "en": "Ambulance 122; 112 on mobile (GSM)", "ar": "الإسعاف 122؛ 112 عبر الجوال (GSM)"}},
    "ae": {"label": {"fa": "امارات 🇦🇪", "en": "UAE 🇦🇪", "ar": "الإمارات 🇦🇪"}, "ambulance": "998"},
    "sa": {"label": {"fa": "عربستان 🇸🇦", "en": "Saudi Arabia 🇸🇦", "ar": "السعودية 🇸🇦"}, "ambulance": "997", "alt": "911", "note": {"fa": "آمبولانس ۹۹۷؛ شمارهٔ یکپارچهٔ ۹۱۱ (از جمله زائران)", "en": "Ambulance 997; unified 911 (incl. pilgrims)", "ar": "الإسعاف 997؛ الرقم الموحد 911 (بما فيهم الحجاج)"}},
    "qa": {"label": {"fa": "قطر 🇶🇦", "en": "Qatar 🇶🇦", "ar": "قطر 🇶🇦"}, "ambulance": "999"},
    "om": {"label": {"fa": "عمان 🇴🇲", "en": "Oman 🇴🇲", "ar": "عُمان 🇴🇲"}, "ambulance": "9999"},
    "bh": {"label": {"fa": "بحرین 🇧🇭", "en": "Bahrain 🇧🇭", "ar": "البحرين 🇧🇭"}, "ambulance": "999"},
    "tr": {"label": {"fa": "ترکیه 🇹🇷", "en": "Türkiye 🇹🇷", "ar": "تركيا 🇹🇷"}, "ambulance": "112"},
    "uk": {"label": {"fa": "بریتانیا 🇬🇧", "en": "UK 🇬🇧", "ar": "بريطانيا 🇬🇧"}, "ambulance": "999", "alt": "112"},
    "de": {"label": {"fa": "آلمان 🇩🇪", "en": "Germany 🇩🇪", "ar": "ألمانيا 🇩🇪"}, "ambulance": "112"},
    "us": {"label": {"fa": "آمریکا 🇺🇸", "en": "USA 🇺🇸", "ar": "أمريكا 🇺🇸"}, "ambulance": "911"},
    "au": {"label": {"fa": "استرالیا 🇦🇺", "en": "Australia 🇦🇺", "ar": "أستراليا 🇦🇺"}, "ambulance": "000"},
}
# ترتیب نمایش دکمه‌ها: ایران (مقصد) → کشورهای مبدأ بیماران خارجی → سایر
EMERGENCY_COUNTRY_ORDER = ["ir", "iq", "ae", "sa", "qa", "om", "bh", "tr", "uk", "de", "us", "au"]
GLOBAL_FALLBACK_NUMBER = "112"  # استاندارد جهانی GSM

# تخصیص تخصص برای ارجاع (کلیدها باید در doctor_loader.SPEC_LABELS_I18N باشند)
_REF_SPEC = {
    "dizziness": "internal", "seizure": "neuro", "asthma": "internal",
    "chest_pain": "cardio", "stroke": "neuro", "unconscious": "internal",
    "anaphylaxis": "internal", "bleeding": "internal", "choking": "internal",
    "hypoglycemia": "internal", "poisoning": "internal", "spine_injury": "neuro",
    "burn": "derma", "abdominal_pain": "gastro", "pregnancy": "obgyn",
    "child_fever": "pediatric", "weakness_speech": "neuro", "mental_crisis": "psychiatry",
}

# ── ۱۸ علامت (فهرست محصول؛ تکمیل‌پذیر با نظر متخصصان) ────────────────────────
# severity: critical = تهدید حیات → مسیر اورژانس پیش‌فرض (یک پرسش سریع)
#           high    = ۲-۳ پرسش کوتاه تریاژ
SYMPTOMS: list[dict] = [
    {"id": "dizziness", "icon": "💫", "severity": "high",
     "title": {"fa": "سرگیجهٔ شدید و ناگهانی", "en": "Sudden severe dizziness", "ar": "دوخة شديدة مفاجئة"},
     "brief": {"fa": "سرگیجهٔ ناگهانی و شدید می‌تواند نشانهٔ مشکل در تعادل، فشار خون، قلب یا مغز باشد. اگر با دوگانه‌بینی، اختلال گفتار یا ضعف اندام همراه شود، اورژانسی است.",
               "en": "Sudden severe dizziness may signal a problem with balance, blood pressure, heart, or brain. With double vision, slurred speech, or limb weakness it is an emergency.",
               "ar": "قد تشير الدوخة الشديدة المفاجئة إلى مشكلة في التوازن أو ضغط الدم أو القلب أو الدماغ. ومع ازدواج الرؤية أو تلعثم الكلام أو ضعف الأطراف فهي حالة طارئة."},
     "red_flags": [{"fa": "دوگانه‌بینی یا تاری دید", "en": "Double or blurred vision", "ar": "ازدواج الرؤية"},
                   {"fa": "اختلال گفتار", "en": "Slurred speech", "ar": "تلعثم الكلام"},
                   {"fa": "ضعف یا بی‌حسی دست/پا", "en": "Limb weakness or numbness", "ar": "ضعف أو تنميل الأطراف"},
                   {"fa": "افتادن روی زمین یا استفراغ شدید", "en": "Falling or severe vomiting", "ar": "السقوط أو القيء الشديد"}],
     "questions": [
         {"key": "neuro", "text": {"fa": "آیا دوبینی، اختلال گفتار یا ضعف دست/پا دارید؟", "en": "Double vision, slurred speech, or limb weakness?", "ar": "هل لديك ازدواج رؤية أو تلعثم كلام أو ضعف بالأطراف؟"}, "yes": "emergency", "no": "referral"},
         {"key": "persistent", "text": {"fa": "آیا سرگیجه چند ساعت ادامه دارد یا بدتر می‌شود؟", "en": "Has dizziness lasted hours or worsened?", "ar": "هل استمرت الدوخة لساعات أو ازدادت؟"}, "yes": "urgent", "no": "referral"},
     ]},
    {"id": "seizure", "icon": "⚡", "severity": "critical",
     "title": {"fa": "تشنج و حملهٔ صرع", "en": "Seizure", "ar": "تشنج أو نوبة صرع"},
     "brief": {"fa": "تشنج فعال وضعیت اورژانسی است. اولویت: حفظ راه تنفسی و جلوگیری از آسیب؛ سپس تماس با اورژانس.",
               "en": "An active seizure is an emergency. Priority: protect airway and prevent injury; then call EMS.",
               "ar": "التشنج النشط حالة طارئة. الأولوية: حماية مجرى الهواء ومنع الإصابة ثم الاتصال بالإسعاف."},
     "red_flags": [{"fa": "تشنج همین حالا در جریان است", "en": "Seizure is happening now", "ar": "التشنج مستمر الآن"},
                   {"fa": "بیش از ۵ دقیقه یا تکرار حمله", "en": "Lasting over 5 minutes or repeating", "ar": "أكثر من ٥ دقائق أو متكرر"},
                   {"fa": "تنگی نفس پس از حمله", "en": "Breathing difficulty after the attack", "ar": "صعوبة تنفس بعد النوبة"},
                   {"fa": "بارداری، دیابت یا اولین حمله", "en": "Pregnancy, diabetes, or first-ever seizure", "ar": "حمل أو سكري أو أول نوبة"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا یکی از موارد بالا همین حالا وجود دارد؟", "en": "Is any of the above happening now?", "ar": "هل يحدث أي مما سبق الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "asthma", "icon": "🫁", "severity": "critical",
     "title": {"fa": "حملهٔ شدید آسم و تنگی نفس", "en": "Severe asthma attack / breathlessness", "ar": "نوبة ربو شديدة وضيق تنفس"},
     "brief": {"fa": "در حملهٔ آسم، طبق برنامهٔ درمانی خودتان از داروی نجاتِ تجویزشده استفاده کنید و استراحت کنید. اگر با تکلم سخت، لب آبی یا بهبودنیافتن بعد از دارو همراه است، فوراً اورژانس را بگیرید.",
               "en": "During an asthma attack use your own prescribed rescue medication per your action plan and rest. If speech is hard, lips turn blue, or it doesn't improve after medication — call EMS immediately.",
               "ar": "أثناء نوبة الربو استخدم دواء الإنقاذ الموصوف لك وفق خطة علاجك وارتَح. إذا صعُب الكلام أو ازرقّقت الشفاه أو لم يتحسن بعد الدواء فاتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "تکلم سخت یا جملهٔ ناقص", "en": "Difficulty speaking full sentences", "ar": "صعوبة إكمال الجملة"},
                   {"fa": "آبی شدن لب‌ها", "en": "Blue lips", "ar": "ازرقاق الشفاه"},
                   {"fa": "بهبودنیافتن بعد از داروی نجات", "en": "No improvement after rescue medication", "ar": "لا تحسن بعد دواء الإنقاذ"},
                   {"fa": "تنگی نفس در حال استراحت", "en": "Breathlessness at rest", "ar": "ضيق تنفس في الراحة"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا یکی از نشانه‌های خطر بالا را دارید؟", "en": "Do you have any red flag above?", "ar": "هل لديك أحد علامات الخطر أعلاه؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "chest_pain", "icon": "❤️‍🩹", "severity": "critical",
     "title": {"fa": "درد یا فشار قفسهٔ سینه", "en": "Chest pain or pressure", "ar": "ألم أو ضغط في الصدر"},
     "brief": {"fa": "درد/فشار قفسهٔ سینه می‌تواند نشانهٔ مشکل قلبی باشد. از رانندگی خودداری کنید و فوراً اورژانس را مطلع کنید.",
               "en": "Chest pain/pressure can signal a heart problem. Do not drive yourself; call EMS immediately.",
               "ar": "قد يشير ألم أو ضغط الصدر إلى مشكلة قلبية. لا تَقُد السيارة واتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "فشار سنگین، گیرکردن یا سوزش در سینه", "en": "Heavy pressure, squeezing, or burning in chest", "ar": "ضغط شديد أو انقباض في الصدر"},
                   {"fa": "پخش درد به بازو/فک/گردن", "en": "Pain spreading to arm, jaw, or neck", "ar": "انتشار الألم للذراع أو الفك"},
                   {"fa": "عرق سرد، تهوع یا تنگی نفس", "en": "Cold sweat, nausea, or breathlessness", "ar": "عرق بارد أو غثيان أو ضيق نفس"},
                   {"fa": "درد با فعالیت یا در استراحت بیش از چند دقیقه", "en": "Pain lasting minutes at rest or on exertion", "ar": "ألم يستمر دقائق في الراحة"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا درد یا فشار سینه همین حالا وجود دارد؟", "en": "Do you have chest pain/pressure right now?", "ar": "هل تشعر بألم أو ضغط في الصدر الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "stroke", "icon": "🧠", "severity": "critical",
     "title": {"fa": "علائم سکتهٔ مغزی", "en": "Stroke symptoms", "ar": "أعراض السكتة الدماغية"},
     "brief": {"fa": "سکتهٔ مغزی بر اثر قطع خون‌رسانی مغز است و هر دقیقه اهمیت دارد. اقدام فوری: تماس با اورژانس — نه صبر و نه درمان در خانه.",
               "en": "Stroke means interrupted blood flow to the brain and every minute counts. Act now: call EMS — do not wait or self-treat.",
               "ar": "السكتة الدماغية انقطاع تدفق الدم إلى الدماغ وكل دقيقة مهمة. اتصل بالإسعاف فوراً ولا تنتظر."},
     "red_flags": [{"fa": "افتادگی یک طرف صورت", "en": "Facial droop on one side", "ar": "تدلي أحد جانبي الوجه"},
                   {"fa": "ضعف دست/پا در یک طرف", "en": "One-sided arm/leg weakness", "ar": "ضعف أحد الأطراف جانبياً"},
                   {"fa": "اختلال تکلم یا درک گفتار", "en": "Trouble speaking or understanding", "ar": "صعوبة الكلام أو الفهم"},
                   {"fa": "تاری دید یا سردرد شدید ناگهانی", "en": "Blurred vision or sudden severe headache", "ar": "تشوش الرؤية أو صداع شديد مفاجئ"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا یکی از این علائم همین حالا وجود دارد؟", "en": "Are any of these signs present now?", "ar": "هل توجد أحد هذه الأعراض الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "unconscious", "icon": "😵", "severity": "critical",
     "title": {"fa": "بیهوشی و کاهش سطح هوشیاری", "en": "Unconsciousness / reduced alertness", "ar": "فقدان الوعي أو انخفاض الوعي"},
     "brief": {"fa": "کاهش هوشیاری وضعیت بحرانی است. فرد را به پهلو بخوابانید (وضعیت نجات)، راه تنفس را باز نگه دارید و فوراً اورژانس را بگیرید.",
               "en": "Reduced consciousness is critical. Place the person on their side (recovery position), keep the airway open, and call EMS immediately.",
               "ar": "انخفاض الوعي حالة حرجة. ضع الشخص على جانبه وحافظ على مجرى الهواء واتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "پاسخ ندادن به صدا یا تکان دادن", "en": "No response to voice or shaking", "ar": "لا يستجيب للصوت أو الهز"},
                   {"fa": "نفس‌نکشیدن یا نفس سطحی", "en": "Not breathing or shallow breathing", "ar": "لا تنفس أو تنفس سطحي"},
                   {"fa": "ضربهٔ اخیر به سر", "en": "Recent head injury", "ar": "إصابة حديثة في الرأس"},
                   {"fa": "مصرف دارو یا الکل", "en": "Drug or alcohol intake", "ar": "تعاطي دواء أو كحول"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا فرد همین حالا بیهوش یا نیمه‌هوشیار است؟", "en": "Is the person unconscious or semi-conscious now?", "ar": "هل الشخص فاقد للوعي الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "anaphylaxis", "icon": "🚑", "severity": "critical",
     "title": {"fa": "واکنش آلرژیک شدید و آنافیلاکسی", "en": "Severe allergic reaction / anaphylaxis", "ar": "ردة فعل تحسسية شديدة / صدمة تحسسية"},
     "brief": {"fa": "آنافیلاکسی واکنش آلرژیک تهدیدکنندهٔ حیات است. اگر اپی‌پن/خودتزریق‌کنندهٔ تجویزشده دارید، مطابق آموزش قبلی استفاده کنید و بلافاصله اورژانس را بگیرید.",
               "en": "Anaphylaxis is a life-threatening allergic reaction. If you have a prescribed adrenaline auto-injector, use it as trained and call EMS immediately.",
               "ar": "الصدمة التحسسية حالة تهدد الحياة. إن كان لديك حاقن الأدرينالين الموصوف فاستخدمه كما تعلمت واتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "تورم لب/زبان/گلو", "en": "Swelling of lips, tongue, or throat", "ar": "تورم الشفاه أو اللسان أو الحلق"},
                   {"fa": "تنگی نفس یا خس‌خس", "en": "Breathing difficulty or wheeze", "ar": "صعوبة تنفس أو صفير"},
                   {"fa": "سرگیجه یا افت ناگهانی فشار", "en": "Dizziness or sudden blood-pressure drop", "ar": "دوار أو هبوط ضغط مفاجئ"},
                   {"fa": "کهیر گسترده با ضعف", "en": "Widespread hives with weakness", "ar": "شرى واسع مع ضعف"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا یکی از این نشانه‌ها وجود دارد؟", "en": "Any of these signs present?", "ar": "هل يوجد أحد هذه العلامات؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "bleeding", "icon": "🩸", "severity": "critical",
     "title": {"fa": "خونریزی شدید", "en": "Severe bleeding", "ar": "نزيف شديد"},
     "brief": {"fa": "خونریزی شدید را با فشار مستقیم با پارچهٔ تمیز مهار کنید و فرد را بخوابانید. اگر با فشار بند نمی‌آید، اورژانس را فوراً بگیرید.",
               "en": "Control severe bleeding with firm direct pressure using a clean cloth and lay the person down. If it doesn't stop with pressure, call EMS immediately.",
               "ar": "أوقف النزيف الشديد بضغط مباشر بقماة نظيفة واجعل الشخص يستلقي. إذا لم يتوقف فاتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "خون فوران‌دار یا بندنیامدن با فشار", "en": "Spurting blood or not stopping with pressure", "ar": "دم متدفق لا يتوقف بالضغط"},
                   {"fa": "خونریزی از دهان/معده/بول", "en": "Bleeding from mouth, stomach, or urine", "ar": "نزيف من الفم أو البول"},
                   {"fa": "ضعف، رنگ‌پریدگی یا بیهوشی", "en": "Weakness, pallor, or fainting", "ar": "ضعف أو شحوب أو إغماء"},
                   {"fa": "مصرف داروی ضد انعقاد", "en": "Taking blood thinners", "ar": "تناول مميعات الدم"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا خونریزی شدید در جریان است؟", "en": "Is severe bleeding ongoing?", "ar": "هل النزيف الشديد مستمر؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "choking", "icon": "😮‍💨", "severity": "critical",
     "title": {"fa": "خفگی و انسداد راه تنفسی", "en": "Choking / airway obstruction", "ar": "الاختناق أو انسداد المجاري التنفسية"},
     "brief": {"fa": "اگر فرد سرفه می‌کند، سرفه را ادامه دهید؛ اگر نمی‌تواند نفس بکشد، حرف بزند یا سرفه کند، مانور هایملیک (فشار شکمی) و کمک فوری لازم است.",
               "en": "If the person can cough, keep coughing; if they cannot breathe, speak, or cough, the Heimlich maneuver and immediate help are needed.",
               "ar": "إذا كان يسعل فليواصل السعال؛ وإذا عجز عن التنفس أو الكلام أو السعال فلازم манورة هيمليك ومساعدة فورية."},
     "red_flags": [{"fa": "ناتوانی در نفس کشیدن/سرفه/حرف‌زدن", "en": "Cannot breathe, cough, or speak", "ar": "عجز عن التنفس أو السعال أو الكلام"},
                   {"fa": "آبی شدن صورت", "en": "Bluish face", "ar": "ازرقاق الوجه"},
                   {"fa": "بیهوش شدن", "en": "Losing consciousness", "ar": "فقدان الوعي"},
                   {"fa": "خفگی نوزاد/کودک", "en": "Choking infant/child", "ar": "اختناق رضيع أو طفل"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا انسداد راه تنفس همین حالا وجود دارد؟", "en": "Is the airway blocked right now?", "ar": "هل المجرى التنفسي مسدود الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "hypoglycemia", "icon": "🍬", "severity": "critical",
     "title": {"fa": "افت شدید قند خون", "en": "Severe low blood sugar", "ar": "هبوط سكر الدم الشديد"},
     "brief": {"fa": "اگر فرد دیابتی است و هوشیار است، مطابق آموزش پزشک معالج، قند سریع‌جذب مصرف شود و قند مجدد بررسی شود. بی‌هوشی = اورژانس فوری.",
               "en": "If the person is diabetic and alert, take fast-acting sugar as previously instructed by their physician and recheck. Unconsciousness = immediate emergency.",
               "ar": "إذا كان مريض سكري وواعياً فليتناول سكراً سريع الامتصاص حسب تعليمات طبيبه وأعد القياس. فقدان الوعي = طوارئ فورية."},
     "red_flags": [{"fa": "بیهوشی یا گیجی شدید", "en": "Unconsciousness or severe confusion", "ar": "فقدان وعي أو تشوش شديد"},
                   {"fa": "ناتوانی در خوردن/آشامیدن", "en": "Unable to eat or drink", "ar": "عدم القدرة على الأكل أو الشرب"},
                   {"fa": "تشنج", "en": "Seizure", "ar": "تشنج"},
                   {"fa": "عدم بهبود بعد از قند", "en": "No improvement after sugar intake", "ar": "لا تحسن بعد السكر"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا فرد هوشیار است و می‌تواند چیزی بنوشد؟", "en": "Is the person alert and able to drink?", "ar": "هل الشخص واعٍ ويستطيع الشرب؟"}, "yes": "urgent", "no": "emergency"},
     ]},
    {"id": "poisoning", "icon": "☠️", "severity": "critical",
     "title": {"fa": "مسمومیت و مصرف بیش از حد دارو", "en": "Poisoning / drug overdose", "ar": "تسمم أو جرعة زائدة من دواء"},
     "brief": {"fa": "به فرد چیزی نخورانید و استفراغ نکنید. بسته‌بندی دارو/ماده را نگه دارید و فوراً با اورژانس یا مرکز مسمومیت تماس بگیرید.",
               "en": "Do not give anything by mouth and do not induce vomiting. Keep the packaging and call EMS or the poison center immediately.",
               "ar": "لا تعطِ شيئاً عن طريق الفم ولا تسبب القيء. احفظ العبوة واتصل بالإسعاف أو مركز السموم فوراً."},
     "red_flags": [{"fa": "بیهوشی یا خواب‌آلودگی شدید", "en": "Unconsciousness or severe drowsiness", "ar": "فقدان وعي أو نعاس شديد"},
                   {"fa": "استفراغ مداوم یا خون", "en": "Persistent or bloody vomiting", "ar": "قيء مستمر أو مدمى"},
                   {"fa": "درد شدید شکم یا سوزش گلو", "en": "Severe abdominal pain or burning throat", "ar": "ألم بطن شديد أو حرقة الحلق"},
                   {"fa": "مصرف چند دارو با هم", "en": "Multiple drugs taken together", "ar": "تناول عدة أدوية معاً"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا مصرف ماده/دارو در ساعت‌های اخیر بوده؟", "en": "Was the substance taken within recent hours?", "ar": "هل تم تناول المادة خلال الساعات الأخيرة؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "spine_injury", "icon": "🦴", "severity": "critical",
     "title": {"fa": "آسیب جدی سر و ستون فقرات", "en": "Serious head or spinal injury", "ar": "إصابة خطيرة في الرأس أو العمود الفقري"},
     "brief": {"fa": "فرد را حرکت ندهید مگر برای نجات از خطر مستقیم؛ حرکت می‌تواند آسیب مغزی/نخاعی را بدتر کند. فوراً اورژانس را بگیرید.",
               "en": "Do not move the person unless out of immediate danger; movement can worsen brain/spinal injury. Call EMS immediately.",
               "ar": "لا تحرّك الشخص إلا للخلاص من خطر مباشر؛ فالحركة قد تزيد الإصابة. اتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "بی‌حسی یا فلج اندام", "en": "Numbness or paralysis", "ar": "تنميل أو شلل"},
                   {"fa": "درد شدید گردن/کمر بعد از ضربه", "en": "Severe neck/back pain after impact", "ar": "ألم شديد بالرقبة أو الظهر بعد رض"},
                   {"fa": "استفراغ یا گیجی بعد از ضربهٔ سر", "en": "Vomiting or confusion after head impact", "ar": "قيء أو تشوش بعد رض الرأس"},
                   {"fa": "خروج مایع/خون از گوش یا بینی", "en": "Fluid/blood from ear or nose", "ar": "سائل أو دم من الأذن أو الأنف"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا ضربهٔ شدید به سر یا ستون فقرات اخیراً رخ داده؟", "en": "Did a severe head/spinal impact recently occur?", "ar": "هل حدث رض شديد للرأس أو العمود الفقري مؤخراً؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "burn", "icon": "🔥", "severity": "critical",
     "title": {"fa": "سوختگی شدید", "en": "Severe burn", "ar": "حرق شديد"},
     "brief": {"fa": "محل سوختگی را ۱۰ تا ۲۰ دقیقه زیر آب ولرم (نه سرد شدید) نگه دارید؛ یخ، خمیردندان یا مواد خانگی نزنید. لباس چسبیده به زخم را نکَنید.",
               "en": "Hold the burn under cool (not ice-cold) running water for 10-20 minutes; avoid ice, toothpaste, or home remedies. Do not peel off stuck clothing.",
               "ar": "أمسك موضع الحرق تحت ماء جارٍ فاتر (لا بارد جداً) 10-20 دقيقة؛ تجنب الثلج ومعجون الأسنان. لا تُنزع الملابس الملتصقة."},
     "red_flags": [{"fa": "سوختگی صورت/دست/پا/اندام تناسلی", "en": "Burn on face, hands, feet, or genitals", "ar": "حرق في الوجه أو اليدين أو القدمين"},
                   {"fa": "سوختگی وسیع یا عمیق (موشکها/تیرگی)", "en": "Large or deep burn (blisters/charred)", "ar": "حرق واسع أو عميق"},
                   {"fa": "سوختگی شیمیایی یا برق‌گرفتگی", "en": "Chemical or electrical burn", "ar": "حرق كيميائي أو كهربائي"},
                   {"fa": "سوختگی کودک یا سالمند", "en": "Burn in a child or elderly", "ar": "حرق طفل أو مسن"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا سوختگی وسیع، عمیق یا در ناحیهٔ حساس است؟", "en": "Is the burn large, deep, or on a sensitive area?", "ar": "هل الحرق واسع أو عميق أو في منطقة حساسة؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "abdominal_pain", "icon": "🤕", "severity": "high",
     "title": {"fa": "درد شدید و ناگهانی شکم", "en": "Sudden severe abdominal pain", "ar": "ألم بطن شديد ومفاجئ"},
     "brief": {"fa": "درد شدید ناگهانی شکم می‌تواند نشانهٔ مشکل گوارشی، آپاندیس یا زنان باشد. مسکن یا ملین نخورید تا بررسی پزشکی انجام شود.",
               "en": "Sudden severe abdominal pain may signal a digestive, appendiceal, or gynecologic problem. Avoid painkillers or laxatives until medically assessed.",
               "ar": "قد يشير الألم الشديد المفاجئ إلى مشكلة هضمية أو الزائدة أو أمراض النساء. تجنب المسكنات أو الملينات حتى التقييم الطبي."},
     "red_flags": [{"fa": "شکم سفت و پرهیز از لمس", "en": "Rigid abdomen, guarding", "ar": "بطن متصلبة"},
                   {"fa": "استفراغ خونی یا مدفوع سیاه", "en": "Bloody vomit or black stool", "ar": "قيء مدمى أو براز أسود"},
                   {"fa": "تب با درد شدید", "en": "Fever with severe pain", "ar": "حمى مع ألم شديد"},
                   {"fa": "درد با بیهوشی یا ضعف شدید", "en": "Pain with fainting or severe weakness", "ar": "ألم مع إغماء أو ضعف شديد"}],
     "questions": [
         {"key": "rf", "text": {"fa": "آیا یکی از نشانه‌های خطر بالا را دارید؟", "en": "Any red flag above present?", "ar": "هل لديك أحد علامات الخطر أعلاه؟"}, "yes": "emergency", "no": "referral"},
         {"key": "persist", "text": {"fa": "آیا درد بیش از ۲ ساعت ادامه دارد؟", "en": "Has pain lasted over 2 hours?", "ar": "هل استمر الألم أكثر من ساعتين؟"}, "yes": "urgent", "no": "referral"},
     ]},
    {"id": "pregnancy", "icon": "🤰", "severity": "critical",
     "title": {"fa": "علائم خطرناک بارداری و خونریزی", "en": "Danger signs of pregnancy & bleeding", "ar": "علامات خطيرة في الحمل والنزيف"},
     "brief": {"fa": "خونریزی، درد شدید شکم یا کاهش حرکت جنین در بارداری اورژانسی است. به پهلو بخوابید و فوراً با اورژانس یا مرکز زنان تماس بگیرید.",
               "en": "Bleeding, severe abdominal pain, or reduced fetal movement in pregnancy is an emergency. Lie on your side and call EMS or an obstetric center immediately.",
               "ar": "النزيف أو الألم الشديد أو نقص حركة الجنين أثناء الحمل حالة طارئة. استلقي على جانبك واتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "خونریزی واژینال", "en": "Vaginal bleeding", "ar": "نزيف مهبلي"},
                   {"fa": "درد شدید یا انقباضات", "en": "Severe pain or contractions", "ar": "ألم شديد أو تقلصات"},
                   {"fa": "کاهش یا توقف حرکت جنین", "en": "Reduced or absent fetal movement", "ar": "نقص حركة الجنين"},
                   {"fa": "سردرد شدید، تاری دید یا ورم صورت", "en": "Severe headache, blurred vision, facial swelling", "ar": "صداع شديد أو تشوش رؤية أو تورم وجه"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا یکی از این علائم در بارداری فعلی وجود دارد؟", "en": "Any of these signs in current pregnancy?", "ar": "هل يوجد أحد هذه الأعراض في الحمل الحالي؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "child_fever", "icon": "🧒", "severity": "critical",
     "title": {"fa": "تب و تشنج کودکان", "en": "Child fever & seizures", "ar": "حمى وتشنج الأطفال"},
     "brief": {"fa": "در تشنج فعال، کودک را در محیط امن بخوابانید و دهانش را چیزی پر نکنید؛ بعد از حمله پزشک ببینید. تب با بی‌حالی، راش یا عدم نوشیدن مایعات اورژانسی است.",
               "en": "During an active seizure lay the child in a safe place and put nothing in the mouth; see a doctor after the attack. Fever with lethargy, rash, or refusing fluids is an emergency.",
               "ar": "أثناء التشنج ضع الطفل في مكان آمن ولا تضع شيئاً في فمه؛ وراجع الطبيب بعد النوبة. الحمى مع خمول أو طفح أو رفض الشرب حالة طارئة."},
     "red_flags": [{"fa": "تشنج فعال", "en": "Active seizure", "ar": "تشنج نشط"},
                   {"fa": "خواب‌آلودگی غیرعادی یا گیجی", "en": "Unusual drowsiness or confusion", "ar": "نعاس غير معتاد أو تشوش"},
                   {"fa": "راش پخش‌شونده که با فشار محو نمی‌شود", "en": "Spreading rash that doesn't fade with pressure", "ar": "طفح لا يزول بالضغط"},
                   {"fa": "امتناع از نوشیدن یا نشانه‌های کم‌آبی", "en": "Refusing fluids or dehydration signs", "ar": "رفض الشرب أو علامات الجفاف"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا کودک همین حالا تشنج دارد یا بی‌حال است؟", "en": "Is the child seizing or unresponsive now?", "ar": "هل الطفل يحدث له تشنج الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "weakness_speech", "icon": "🗣️", "severity": "critical",
     "title": {"fa": "ضعف ناگهانی اندام‌ها یا اختلال گفتار", "en": "Sudden limb weakness or speech disturbance", "ar": "ضعف مفاجئ بالأطراف أو اضطراب الكلام"},
     "brief": {"fa": "این ترکیب می‌تواند نشانهٔ سکتهٔ مغزی باشد — حتی اگر ظرف چند دقیقه برطرف شود. هر دقیقه حیاتی است؛ فوراً اورژانس را بگیرید.",
               "en": "This combination can signal a stroke — even if it resolves within minutes. Every minute matters; call EMS immediately.",
               "ar": "قد يشير هذا إلى سكتة دماغية حتى لو زول خلال دقائق. كل دقيقة مهمة؛ اتصل بالإسعاف فوراً."},
     "red_flags": [{"fa": "شروع در چند دقیقه/ساعت اخیر", "en": "Started within minutes/hours", "ar": "بدأ خلال دقائق أو ساعات"},
                   {"fa": "یک‌طرفه بودن ضعف", "en": "One-sided weakness", "ar": "ضعف من جانب واحد"},
                   {"fa": "اختلال گفتار یا درک", "en": "Speech or comprehension problem", "ar": "اضطراب كلام أو فهم"},
                   {"fa": "با سردرد شدید یا گیجی", "en": "With severe headache or confusion", "ar": "مع صداع شديد أو تشوش"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا این ضعف/اختلال همین حالا وجود دارد؟", "en": "Is the weakness/speech issue present now?", "ar": "هل الضعف أو اضطراب الكلام موجود الآن؟"}, "yes": "emergency", "no": "referral"},
     ]},
    {"id": "mental_crisis", "icon": "💙", "severity": "critical",
     "title": {"fa": "افکار یا اقدام به خودکشی و بحران روانی", "en": "Suicidal thoughts / mental health crisis", "ar": "أفكار انتحارية أو أزمة نفسية"},
     "brief": {"fa": "شما تنها نیستید و این درد قابل درمان است. همین حالا با فردی قابل‌اعتماد در تماس باشید و تنها نمانید. کمک حرفه‌ای فوری در دسترس است — این پیام جایگزین کمک تخصصی نیست.",
               "en": "You are not alone and this pain is treatable. Reach out to someone you trust right now and stay with people. Professional help is available — this message is not a substitute for expert care.",
               "ar": "أنت لست وحدك وهذا الألم قابل للعلاج. تواصل الآن مع شخص تثق به ولا تبقَ وحدك. المساعدة المتخصصة متاحة — وهذه الرسالة ليست بديلاً عن الرعاية المتخصصة."},
     "red_flags": [{"fa": "برنامه یا اقدام برای آسیب رساندن", "en": "A plan or act of self-harm", "ar": "خطة أو محاولة إيذاء النفس"},
                   {"fa": "در دسترس داشتن ابزار آسیب", "en": "Access to means of harm", "ar": "توفر وسيلة للإيذاء"},
                   {"fa": "خداحافظی یا ناامیدی شدید", "en": "Goodbye messages or deep hopelessness", "ar": "رسائل وداع أو يأس شديد"}],
     "questions": [
         {"key": "now", "text": {"fa": "آیا خطر آسیب فوری وجود دارد؟ (خود یا دیگران)", "en": "Is there immediate danger of harm? (self or others)", "ar": "هل يوجد خطر إيذاء فوري؟ (للنفس أو للآخرين)"}, "yes": "emergency", "no": "referral"},
     ]},
]

SYMPTOM_BY_ID = {s["id"]: s for s in SYMPTOMS}


def get_symptom(symptom_id: str) -> dict | None:
    return SYMPTOM_BY_ID.get(symptom_id)


def evaluate(symptom: dict, answers: dict[str, bool]) -> str:
    """تعیین فوریت از پاسخ‌ها: emergency > urgent > referral.

    هر پرسش نگاشت yes/no به سطح دارد؛ بدترین (بالاترین) سطح برنده است.
    """
    rank = {"referral": 0, "urgent": 1, "emergency": 2}
    level = "referral"
    for q in symptom.get("questions", []):
        val = answers.get(q["key"])
        if val is None:
            continue
        mapped = q["yes"] if val else q.get("no", "referral")
        if rank[mapped] > rank[level]:
            level = mapped
    return level


def specialty_for(symptom_id: str) -> str:
    return _REF_SPEC.get(symptom_id, "internal")


def emergency_number(country_code: str | None) -> tuple[str, dict | None]:
    """شمارهٔ اورژانس آمبولانس برای کشور؛ خروجی: (شماره، رکورد کشور)."""
    if country_code and country_code in EMERGENCY_NUMBERS:
        rec = EMERGENCY_NUMBERS[country_code]
        return rec["ambulance"], rec
    return GLOBAL_FALLBACK_NUMBER, None
