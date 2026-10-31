/// سه‌زبانه‌سازی دستی (بدون code-gen) — fa / ar / en.
///
/// متن‌های تخصصی علائم از assets/data/symptoms.json (تک‌منبع حقیقت مشترک
/// با ربات) می‌آیند؛ این فایل فقط رشته‌های رابط کاربری را نگه می‌دارد.
library;

import 'package:flutter/material.dart';

enum AppLanguage { fa, ar, en }

extension AppLanguageX on AppLanguage {
  Locale get locale => switch (this) {
        AppLanguage.fa => const Locale('fa'),
        AppLanguage.ar => const Locale('ar'),
        AppLanguage.en => const Locale('en'),
      };

  bool get isRtl => this != AppLanguage.en;

  String get label => switch (this) {
        AppLanguage.fa => 'فارسی',
        AppLanguage.ar => 'العربية',
        AppLanguage.en => 'English',
      };

  String get code => switch (this) {
        AppLanguage.fa => 'fa',
        AppLanguage.ar => 'ar',
        AppLanguage.en => 'en',
      };
}

/// LocalizationsDelegate سبک — فقط AppLocalizations را فراهم می‌کند؛
/// Material/Cupertino با delegateهای سراسری flutter_localizations پوشش داده می‌شوند.
class AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) =>
      ['fa', 'ar', 'en'].contains(locale.languageCode);

  @override
  Future<AppLocalizations> load(Locale locale) async =>
      AppLocalizations(_byCode(locale.languageCode));

  @override
  bool shouldReload(covariant LocalizationsDelegate<AppLocalizations> old) =>
      false;
}

AppLanguage _byCode(String code) => switch (code) {
      'ar' => AppLanguage.ar,
      'en' => AppLanguage.en,
      _ => AppLanguage.fa,
    };

class AppLocalizations {
  final AppLanguage lang;

  const AppLocalizations(this.lang);

  static const supportedLocales = [
    Locale('fa'),
    Locale('ar'),
    Locale('en'),
  ];

  static AppLocalizations of(BuildContext context) {
    final loc = Localizations.of<AppLocalizations>(context, AppLocalizations);
    return loc ?? AppLocalizations(_byCode(Localizations.localeOf(context).languageCode));
  }

  String t(String key) =>
      _strings[lang]?[key] ?? _strings[AppLanguage.fa]![key] ?? key;

  // ── رشته‌های رابط کاربری ──
  static const Map<AppLanguage, Map<String, String>> _strings = {
    AppLanguage.fa: {
      'app_name': 'شیراز مدیکال',
      'home_title': 'سلامت شما، تعهد ما',
      'search_hint': 'جست‌وجو: پزشک، بیمارستان، هتل، مترجم…',
      'search': 'جست‌وجوی هوشمند',
      'advisor': 'مشاور سلامت',
      'emergency': 'اورژانس',
      'book': 'نوبت بگیر',
      'cat_medical': 'درمان و پزشکان',
      'cat_travel': 'اقامت و حمل‌ونقل',
      'cat_tourism': 'گردشگری و پکیج',
      'cat_support': 'پشتیبانی و خدمات',
      'cat_me': 'پرونده و نوبت‌های من',
      'cat_contact': 'گفتگو و ارتباط',
      'choose_symptom': 'علامت مورد نظر را انتخاب کنید',
      'disclaimer': 'این بخش تشخیص پزشکی یا تجویز دارو نیست؛ فقط فوریت را تخمین می‌زند و ارجاع می‌دهد.',
      'red_flags': 'نشانه‌های خطر فوری',
      'yes': 'بله',
      'no': 'خیر',
      'question': 'پرسش',
      'call_emergency': 'کمک فوری — تماس با اورژانس',
      'referral': 'ارجاع پیشنهادی',
      'choose_country': 'برای نمایش شمارهٔ درست، کشور محل حضور شما کدام است؟',
      'call': 'تماس با',
      'honest_note': 'این اپلیکیشن نمی‌تواند آمبولانس اعزام کند یا اورژانس را مطلع کند — خودتان تماس بگیرید.',
      'operator_text': 'متن آماده برای اپراتور',
      'for_companion': 'متن برای همراه',
      'see_doctors': 'مشاهدهٔ پزشکان این تخصص',
      'nearby_hospitals': 'بیمارستان‌های دارای این تخصص',
      'coming_soon': 'این بخش در نسخه‌های بعدی فعال می‌شود.',
      'no_result': 'نتیجه‌ای پیدا نشد.',
      'language': 'زبان',
    },
    AppLanguage.ar: {
      'app_name': 'شيراز ميديكال',
      'home_title': 'صحتك التزامنا',
      'search_hint': 'ابحث: طبيب، مستشفى، فندق، مترجم…',
      'search': 'بحث ذكي',
      'advisor': 'مستشار الصحة',
      'emergency': 'الطوارئ',
      'book': 'احجز موعداً',
      'cat_medical': 'العلاج والأطباء',
      'cat_travel': 'الإقامة والنقل',
      'cat_tourism': 'السياحة والباقات',
      'cat_support': 'خدمات الدعم',
      'cat_me': 'ملفي ومواعيدي',
      'cat_contact': 'تواصل معنا',
      'choose_symptom': 'اختر العرض',
      'disclaimer': 'هذا ليس تشخيصاً طبياً ولا وصفة دواء؛ يقدّر الإلحاح ويحيلك للطبيب.',
      'red_flags': 'علامات الخطر الفوري',
      'yes': 'نعم',
      'no': 'لا',
      'question': 'سؤال',
      'call_emergency': 'مساعدة عاجلة — اتصل بالإسعاف',
      'referral': 'إحالة مقترحة',
      'choose_country': 'لعرض رقم الإسعاف الصحيح، في أي بلد أنت الآن؟',
      'call': 'اتصال بـ',
      'honest_note': 'لا يمكن للتطبيق إرسال إسعاف أو إبلاغ الطوارئ — يجب عليك الاتصال بنفسك.',
      'operator_text': 'نص جاهز للعامل',
      'for_companion': 'نص للمرافق',
      'see_doctors': 'أطباء هذا التخصص',
      'nearby_hospitals': 'المستشفيات التي بها هذا التخصص',
      'coming_soon': 'سيتم تفعيل هذا القسم في الإصدارات القادمة.',
      'no_result': 'لا نتائج.',
      'language': 'اللغة',
    },
    AppLanguage.en: {
      'app_name': 'Shiraz Medical',
      'home_title': 'Your health, our commitment',
      'search_hint': 'Search: doctor, hospital, hotel, translator…',
      'search': 'Smart Search',
      'advisor': 'Health Advisor',
      'emergency': 'Emergency',
      'book': 'Book Appointment',
      'cat_medical': 'Treatment & Doctors',
      'cat_travel': 'Stay & Transport',
      'cat_tourism': 'Tourism & Packages',
      'cat_support': 'Support Services',
      'cat_me': 'My File & Appointments',
      'cat_contact': 'Talk to Us',
      'choose_symptom': 'Choose a symptom',
      'disclaimer': 'Not a diagnosis or prescription; it estimates urgency and refers you.',
      'red_flags': 'Immediate danger signs',
      'yes': 'Yes',
      'no': 'No',
      'question': 'Question',
      'call_emergency': 'Urgent help — call emergency',
      'referral': 'Suggested referral',
      'choose_country': 'To show the correct number — which country are you in?',
      'call': 'Call',
      'honest_note': 'This app cannot dispatch an ambulance or notify EMS — please call yourself.',
      'operator_text': 'Text for the operator',
      'for_companion': 'Text for companion',
      'see_doctors': 'See doctors of this specialty',
      'nearby_hospitals': 'Hospitals offering this specialty',
      'coming_soon': 'This section will be available in future versions.',
      'no_result': 'No results found.',
      'language': 'Language',
    },
  };
}

/// وضعیت سراسری زبان — تک‌منبع حقیقت زبان انتخابی.
class AppState {
  static final ValueNotifier<AppLanguage> language =
      ValueNotifier<AppLanguage>(AppLanguage.fa);
}

/// برچسب سه‌زبانهٔ تخصص‌ها — همسنگ doctor_loader.SPEC_LABELS_I18N ربات.
const Map<String, Map<String, String>> specialtyLabels = {
  'cardio': {'fa': 'قلب و عروق', 'en': 'Cardiology', 'ar': 'أمراض القلب'},
  'derma': {'fa': 'پوست و مو', 'en': 'Dermatology', 'ar': 'الجلدية'},
  'dental': {'fa': 'دندانپزشکی', 'en': 'Dentistry', 'ar': 'طب الأسنان'},
  'internal': {'fa': 'داخلی', 'en': 'Internal Medicine', 'ar': 'الباطنية'},
  'ortho': {'fa': 'ارتوپدی', 'en': 'Orthopedics', 'ar': 'جراحة العظام'},
  'gastro': {'fa': 'گوارش و کبد', 'en': 'Gastroenterology', 'ar': 'الجهاز الهضمي'},
  'neuro': {'fa': 'مغز و اعصاب', 'en': 'Neurology', 'ar': 'الأعصاب'},
  'obgyn': {'fa': 'زنان و زایمان', 'en': 'Obstetrics & Gynecology', 'ar': 'النساء والتوليد'},
  'pediatric': {'fa': 'اطفال', 'en': 'Pediatrics', 'ar': 'طب الأطفال'},
  'psy': {'fa': 'روانشناسی', 'en': 'Psychology', 'ar': 'علم النفس'},
  'psychiatry': {'fa': 'روانپزشکی', 'en': 'Psychiatry', 'ar': 'الطب النفسي'},
  'urology': {'fa': 'ارولوژی', 'en': 'Urology', 'ar': 'المسالك البولية'},
  'ent': {'fa': 'گوش، حلق و بینی', 'en': 'ENT', 'ar': 'الأنف والأذن والحنجرة'},
  'ophtha': {'fa': 'چشم‌پزشکی', 'en': 'Ophthalmology', 'ar': 'طب العيون'},
  'nutrition': {'fa': 'تغذیه', 'en': 'Nutrition', 'ar': 'التغذية'},
  'physio': {'fa': 'فیزیوتراپی', 'en': 'Physiotherapy', 'ar': 'العلاج الطبيعي'},
};

String specialtyLabel(String key, AppLanguage lang) =>
    specialtyLabels[key]?[lang.code] ?? key;
