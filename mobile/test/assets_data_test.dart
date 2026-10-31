// تست بارگذاری assetهای واقعی اپ + مسیرهای مشاور سلامت + سه‌زبانه/RTL.
//
// این تست همان مسیر بارگذاری اپ (DataRepository → rootBundle) را اجرا
// می‌کند تا هر خرابیِ JSON در CI و قبل از انتشار شنیده شود.
import 'package:flutter_test/flutter_test.dart';

import 'package:shiraz_medical/core/l10n/app_localizations.dart';
import 'package:shiraz_medical/models/models.dart';
import 'package:shiraz_medical/services/data_repository.dart';
import 'package:shiraz_medical/services/search_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late DataRepository repo;

  setUpAll(() async {
    repo = DataRepository();
    await repo.loadAll();
  });

  group('بارگذاری فایل‌های JSON (assets/data)', () {
    test('symptoms.json: ۱۸ علامت با ساختار کامل', () {
      expect(repo.symptoms.length, 18, reason: 'دستور مأموریت: ۱۸ علامت اورژانسی');
      for (final s in repo.symptoms) {
        expect(s.id, isNotEmpty);
        expect(s.title['fa'], isNotEmpty, reason: '${s.id}: عنوان فارسی');
        expect(s.title['en'], isNotEmpty, reason: '${s.id}: عنوان انگلیسی');
        expect(s.title['ar'], isNotEmpty, reason: '${s.id}: عنوان عربی');
        expect(s.brief['fa'], isNotEmpty, reason: '${s.id}: توضیح کوتاه');
        expect(s.questions, isNotEmpty, reason: '${s.id}: حداقل یک پرسش تریاژ');
      }
    });

    test('emergency_numbers.json: ۱۲ کشور + ترتیب + fallback', () {
      expect(repo.emergencyOrder, isNotEmpty);
      expect(repo.emergencyOrder.first, 'ir', reason: 'ایران اولین انتخاب');
      expect(repo.emergencyCountries.length, 12);
      expect(repo.emergencyFallback, '112');
      for (final cc in repo.emergencyOrder) {
        final c = repo.emergencyCountries[cc];
        expect(c, isNotNull, reason: cc);
        expect(c!.ambulance, matches(RegExp(r'^\d{2,4}$')), reason: cc);
        expect(c.label['fa'], isNotEmpty, reason: cc);
      }
    });

    test('search_index.json: ۱۳ دستهٔ مأموریت با نام سه‌زبانه', () {
      expect(repo.searchCategories.length, 13,
          reason: '۱۳ دستهٔ جست‌وجوی جامع مأموریت');
      for (final c in repo.searchCategories) {
        expect(c.label['fa'], isNotEmpty, reason: c.id);
        expect(c.label['en'], isNotEmpty, reason: c.id);
        expect(c.label['ar'], isNotEmpty, reason: c.id);
        expect(c.items, isNotEmpty, reason: c.id);
        for (final it in c.items.take(5)) {
          expect(it.name['fa'], isNotEmpty, reason: '${c.id}#${it.index}');
        }
      }
    });
  });

  group('جست‌وجوی سه‌زبانه روی دادهٔ واقعی', () {
    test('فارسی «بیمارستان» دستهٔ بیمارستان‌ها را می‌دهد', () {
      final hits = SearchService.search('بیمارستان', repo.searchCategories);
      expect(hits, isNotEmpty);
      expect(hits.first.category.id, 'hospitals');
    });

    test('انگلیسی «hospital» در داده فارسی جواب می‌دهد', () {
      final hits = SearchService.search('hospital', repo.searchCategories);
      expect(hits, isNotEmpty);
    });

    test('عربی «مستشفى» (ک عربی هم نرمال می‌شود)', () {
      final hits = SearchService.search('مستشفى', repo.searchCategories);
      expect(hits, isNotEmpty);
    });

    test('کوئری بی‌معنی و تک‌حرفی نتیجه نمی‌دهد', () {
      expect(SearchService.search('xyzzy qqq', repo.searchCategories), isEmpty);
      expect(SearchService.search('a', repo.searchCategories), isEmpty);
    });
  });

  group('RTL و سه‌زبانه‌سازی', () {
    test('fa/ar راست‌به‌چپ و en چپ‌به‌راست', () {
      expect(AppLanguage.fa.isRtl, isTrue);
      expect(AppLanguage.ar.isRtl, isTrue);
      expect(AppLanguage.en.isRtl, isFalse);
    });

    test('سه لوکال پشتیبانی‌شده', () {
      expect(AppLocalizations.supportedLocales.map((l) => l.languageCode),
          ['fa', 'ar', 'en']);
    });

    test('رشته‌های رابط کاربری هر سه زبان کامل است', () {
      const keys = [
        'app_name', 'search', 'advisor', 'emergency', 'choose_symptom',
        'disclaimer', 'call_emergency', 'referral', 'choose_country',
        'honest_note', 'no_result', 'yes', 'no',
      ];
      for (final lang in AppLanguage.values) {
        final loc = AppLocalizations(lang);
        for (final k in keys) {
          expect(loc.t(k), isNot(k), reason: '$lang/$k ترجمه نشده');
        }
      }
    });
  });

  group('مسیرهای مشاور سلامت: تریاژ → ارجاع/اورژانس', () {
    test('قاعدهٔ ایمنی: علامت بحرانی فقط یک پرسش سریع دارد (دادهٔ واقعی)', () {
      for (final s in repo.symptoms.where((s) => s.severity == 'critical')) {
        expect(s.questions.length, 1,
            reason: '${s.id}: در خطر فوری نباید معطل پرسش طولانی شد');
      }
    });

    test('هر تخصص علامت در برچسب‌های سه‌زبانهٔ تخصص‌ها هست (مسیر ارجاع)', () {
      for (final s in repo.symptoms) {
        for (final lang in AppLanguage.values) {
          expect(specialtyLabel(s.specialty, lang), isNot(s.specialty),
              reason: '${s.id} → ${s.specialty}/$lang');
        }
      }
    });

    test('پاسخ «بله» به پرسش اورژانسی، سطح emergency می‌دهد', () {
      Symptom? withEmergencyQ;
      for (final s in repo.symptoms) {
        if (s.questions.any((q) => q.yes == 'emergency')) {
          withEmergencyQ = s;
          break;
        }
      }
      expect(withEmergencyQ, isNotNull,
          reason: 'دست‌کم یک مسیر اورژانسی در داده باید باشد');
      final level = evaluateTriage(
        withEmergencyQ!,
        {for (final q in withEmergencyQ.questions) q.key: true},
      );
      expect(level, 'emergency');
    });

    test('پاسخ «خیر» به همهٔ پرسش‌ها به ارجاع می‌رسد (نه اورژانس)', () {
      for (final s in repo.symptoms.take(5)) {
        final level = evaluateTriage(
          s,
          {for (final q in s.questions) q.key: false},
        );
        expect(level, isNot('emergency'), reason: s.id);
      }
    });

    test('دادهٔ صفحهٔ اورژانس: ایران ۱۱۵ و fallback ۱۱۲', () {
      expect(repo.emergencyCountries['ir']!.ambulance, '115');
      expect(repo.emergencyFallback, '112');
    });
  });
}
