import 'package:flutter_test/flutter_test.dart';

import 'package:shiraz_medical/models/models.dart';
import 'package:shiraz_medical/services/search_service.dart';

SearchCategory _cat(String id, List<Map<String, dynamic>> items) =>
    SearchCategory(
      id: id,
      icon: '🏥',
      label: const {'fa': 'تست', 'en': 'Test', 'ar': 'اختبار'},
      items: items
          .map((it) => SearchItem(
                index: it['i'] as int,
                name: (it['n'] as Map).cast<String, String>(),
                corpus: it['c'] as String? ?? '',
                subtitle: '',
              ))
          .toList(),
    );

void main() {
  test('نرمال‌سازی فارسی/عربی', () {
    expect(SearchService.normalize('بیمارستان كوثر'), 'بیمارستان کوثر');
    // اعراب به فاصله تبدیل می‌شود و «ي» به «ی» — خروجی دقیقاً همسنگ
    // موتور ربات (search_engine.normalize) برای یکدستی نتایج.
    expect(SearchService.normalize('  المُستشفى   الطبي  '), 'الم ستشفى الطبی');
    // ارقام فارسی/عربی → ASCII (همسنگ _CHAR_MAP ربات)
    expect(SearchService.normalize('کوثر ۱۲'), 'کوثر 12');
  });

  test('جست‌وجوی فارسی ساده', () {
    final cats = [
      _cat('hospitals', [
        {'i': 0, 'n': {'fa': 'بیمارستان فوق تخصصی کوثر', 'en': 'Kowsar Hospital', 'ar': 'مستشفى كوثر'}},
        {'i': 1, 'n': {'fa': 'بیمارستان نمازی', 'en': 'Nemazee Hospital', 'ar': 'مستشفى النمازي'}},
      ]),
    ];
    final hits = SearchService.search('کوثر', cats);
    expect(hits, isNotEmpty);
    expect(hits.first.item.name['fa'], contains('کوثر'));
  });

  test('غلط املایی و عبارت ناقص', () {
    final cats = [
      _cat('hospitals', [
        {'i': 0, 'n': {'fa': 'بیمارستان فوق تخصصی کوثر', 'en': 'Kowsar Hospital', 'ar': 'مستشفى كوثر'}},
      ]),
    ];
    // «کوسر» = حرف جاافتاده؛ «کوثر» فاصلهٔ ویرایشی ۱
    expect(SearchService.search('کوسر', cats), isNotEmpty);
    // «کوثرشیراز» عبارت پیوسته — زیررشتهٔ مستقیم در عنوان نیست ولی توکن fuzzy هست
    expect(SearchService.search('كوثر', cats), isNotEmpty); // ک عربی
  });

  test('جست‌وجوی انگلیسی در دادهٔ فارسی', () {
    final cats = [
      _cat('hospitals', [
        {'i': 0, 'n': {'fa': 'بیمارستان کوثر', 'en': 'Kowsar Hospital', 'ar': 'مستشفى كوثر'}, 'c': 'kowsar hospital shiraz'},
      ]),
    ];
    expect(SearchService.search('kowsar', cats), isNotEmpty);
  });

  test('کوئری بی‌معنی نتیجه نمی‌دهد', () {
    final cats = [
      _cat('hospitals', [
        {'i': 0, 'n': {'fa': 'بیمارستان کوثر', 'en': 'Kowsar', 'ar': 'كوثر'}, 'c': 'kowsar'},
      ]),
    ];
    expect(SearchService.search('xyzzy qqq', cats), isEmpty);
    expect(SearchService.search('a', cats), isEmpty);
    expect(SearchService.search('  ', cats), isEmpty);
  });
}
