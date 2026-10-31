/// مدل‌های دادهٔ اپ — نگاشت مستقیم به assets/data/*.json
/// (ساخته‌شده از ماژول‌های ربات: تک‌منبع حقیقت).
library;

class Symptom {
  final String id;
  final String icon;
  final String severity; // critical | high
  final Map<String, String> title;
  final Map<String, String> brief;
  final List<Map<String, String>> redFlags;
  final List<TriageQuestion> questions;
  final String specialty;

  const Symptom({
    required this.id,
    required this.icon,
    required this.severity,
    required this.title,
    required this.brief,
    required this.redFlags,
    required this.questions,
    required this.specialty,
  });

  factory Symptom.fromJson(Map<String, dynamic> j) => Symptom(
        id: j['id'] as String,
        icon: j['icon'] as String? ?? '🩺',
        severity: j['severity'] as String? ?? 'high',
        title: strMap(j['title']),
        brief: strMap(j['brief']),
        redFlags: (j['redFlags'] as List<dynamic>? ?? [])
            .map((e) => strMap(e as Map<String, dynamic>))
            .toList(),
        questions: (j['questions'] as List<dynamic>? ?? [])
            .map((e) => TriageQuestion.fromJson(e as Map<String, dynamic>))
            .toList(),
        specialty: j['specialty'] as String? ?? 'internal',
      );

  /// تبدیل مقدار JSON به نگاشت سه‌زبانه (عمومی تا سرویس‌های دیگر هم استفاده کنند).
  static Map<String, String> strMap(dynamic v) {
    if (v is Map<String, dynamic>) {
      return v.map((k, val) => MapEntry(k, val?.toString() ?? ''));
    }
    return const {};
  }
}

class TriageQuestion {
  final String key;
  final Map<String, String> text;
  final String yes; // emergency | urgent | referral
  final String no;

  const TriageQuestion({
    required this.key,
    required this.text,
    required this.yes,
    required this.no,
  });

  factory TriageQuestion.fromJson(Map<String, dynamic> j) => TriageQuestion(
        key: j['key'] as String,
        text: Symptom.strMap(j['text']),
        yes: j['yes'] as String? ?? 'referral',
        no: j['no'] as String? ?? 'referral',
      );
}

/// تریاژ — همان قاعدهٔ سرویس ربات: emergency > urgent > referral.
String evaluateTriage(Symptom s, Map<String, bool> answers) {
  const rank = {'referral': 0, 'urgent': 1, 'emergency': 2};
  var level = 'referral';
  for (final q in s.questions) {
    final a = answers[q.key];
    if (a == null) continue;
    final mapped = a ? q.yes : q.no;
    if (rank[mapped]! > rank[level]!) level = mapped;
  }
  return level;
}

class EmergencyCountry {
  final String code;
  final Map<String, String> label;
  final String ambulance;
  final String? alt;

  const EmergencyCountry({
    required this.code,
    required this.label,
    required this.ambulance,
    this.alt,
  });

  factory EmergencyCountry.fromJson(String code, Map<String, dynamic> j) =>
      EmergencyCountry(
        code: code,
        label: Symptom.strMap(j['label']),
        ambulance: j['ambulance'] as String,
        alt: j['alt'] as String?,
      );
}

class SearchItem {
  final int index;
  final Map<String, String> name; // fa/en/ar
  final String corpus; // متن نرمال‌شده برای جست‌وجو
  final String subtitle;

  const SearchItem({
    required this.index,
    required this.name,
    required this.corpus,
    required this.subtitle,
  });
}

class SearchCategory {
  final String id;
  final String icon;
  final Map<String, String> label;
  final List<SearchItem> items;

  const SearchCategory({
    required this.id,
    required this.icon,
    required this.label,
    required this.items,
  });
}
