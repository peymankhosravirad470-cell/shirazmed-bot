# Shiraz Medical — اپلیکیشن همراه بیمار (Flutter)

اپلیکیشن مستقل Android/iOS سامانهٔ گردشگری سلامت «شیراز مدیکال» — سه‌زبانه
(فارسی/عربی/انگلیسی) با پشتیبانی کامل راست‌چین.

## ساختار

```
mobile/
├── pubspec.yaml                # تعریف پروژه (بدون وابستگی سنگین)
├── assets/data/                # دادهٔ مشترک با ربات (تک‌منبع حقیقت)
│   ├── symptoms.json           # ۱۸ علامت مشاور سلامت (همسنگ app/services/health_advisor.py)
│   ├── emergency_numbers.json  # شمارهٔ اورژانس ۱۲ کشور
│   └── search_index.json       # ایندکس جست‌وجو (۱۳ دسته، ~۱۷۰ آیتم واقعی مخزن)
├── lib/
│   ├── main.dart / app.dart    # نقطهٔ ورود + ریشهٔ MaterialApp
│   ├── core/l10n/              # سه‌زبانه‌سازی + برچسب تخصص‌ها
│   ├── core/theme/             # تم بصری (Material 3)
│   ├── models/                 # Symptom/Triage/Emergency/Search + منطق تریاژ
│   ├── services/
│   │   ├── data_repository.dart   # بارگذاری assets
│   │   └── search_service.dart    # جست‌وجوی فازی سه‌زبانه (همسنگ ربات)
│   └── screens/
│       ├── home_screen.dart       # جست‌وجو در صفحهٔ اصلی (الزام محصول)
│       ├── search_screen.dart     # نتایج دسته‌بندی‌شده
│       └── advisor/               # مشاور سلامت: ۱۸ علامت، تریاژ، اورژانس، ارجاع
└── test/                       # تست منطق جست‌وجو و تریاژ
```

## اجرا (Android)

```bash
cd mobile
flutter pub get
flutter run                # یا: flutter build apk --release
```

## اجرا (iOS)

```bash
cd mobile
flutter pub get
cd ios && pod install && cd ..
flutter run                # یا: flutter build ios --release
# انتشار به App Store نیازمند Xcode و حساب Apple Developer است.
```

> پیش‌نیاز: Flutter SDK ≥ 3.19 (Dart ≥ 3.3).

## همگام‌سازی داده با ربات

دادهٔ علائم/اورژانس/جست‌وجو از مخزن ربات صادر می‌شود — پس از هر تغییر در
`app/services/health_advisor.py` یا داده‌های مخزن، اجرا کنید:

```bash
python3 scripts/export_mobile_assets.py
```

## نکات ایمنی (همسنگ ربات)

- مشاور سلامت «تشخیص یا تجویز» نیست؛ فقط فوریت + ارجاع.
- هیچ ادعای «اعزام آمبولانس» وجود ندارد؛ فقط شمارهٔ درستِ کشور + متن آماده.
- نسخهٔ فعلی: فقط ساختار اولیه؛ اتصال به API عمومی (main_api.py) در نسخهٔ بعد.
