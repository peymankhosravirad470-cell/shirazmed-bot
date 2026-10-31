import 'package:flutter_test/flutter_test.dart';

import 'package:shiraz_medical/models/models.dart';

Symptom _sym({
  required String severity,
  required List<TriageQuestion> questions,
}) =>
    Symptom(
      id: 'test',
      icon: '🩺',
      severity: severity,
      title: const {'fa': 'تست', 'en': 'Test', 'ar': 'اختبار'},
      brief: const {'fa': '', 'en': '', 'ar': ''},
      redFlags: const [],
      questions: questions,
      specialty: 'internal',
    );

void main() {
  test('تریاژ: emergency بر urgent و referral غالب است', () {
    final s = _sym(severity: 'high', questions: const [
      TriageQuestion(
        key: 'a',
        text: {'fa': '', 'en': '', 'ar': ''},
        yes: 'emergency',
        no: 'referral',
      ),
      TriageQuestion(
        key: 'b',
        text: {'fa': '', 'en': '', 'ar': ''},
        yes: 'urgent',
        no: 'referral',
      ),
    ]);
    expect(evaluateTriage(s, {'a': true, 'b': true}), 'emergency');
    expect(evaluateTriage(s, {'a': false, 'b': true}), 'urgent');
    expect(evaluateTriage(s, {'a': false, 'b': false}), 'referral');
    expect(evaluateTriage(s, {}), 'referral'); // بدون پاسخ
  });

  test('علامت بحرانی فقط یک پرسش سریع دارد (الزام ایمنی)', () {
    // در دادهٔ صادرشدهٔ واقعی: critical ها تک‌پرسشی‌اند — این قرارداد را
    // مدل نمی‌شکند؛ تست قرارداد سرویس ربات در python (T16) پوشش داده است.
    final s = _sym(severity: 'critical', questions: const [
      TriageQuestion(
        key: 'now',
        text: {'fa': '', 'en': '', 'ar': ''},
        yes: 'emergency',
        no: 'referral',
      ),
    ]);
    expect(s.questions.length, 1);
    expect(evaluateTriage(s, {'now': true}), 'emergency');
    expect(evaluateTriage(s, {'now': false}), 'referral');
  });
}
