import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/l10n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../models/models.dart';
import '../../services/data_repository.dart';

/// جریان تریاژ: توضیح کوتاه → پرسش‌ها (پیشوندی) → صفحهٔ نتیجه.
/// الزام ایمنی: علامت بحرانی فقط «یک» پرسش سریع دارد؛ در نتیجهٔ اورژانسی
/// دکمهٔ تماس اولویت اول است و هیچ ادعای اعزام آمبولانس نمی‌شود.
class TriageScreen extends StatefulWidget {
  final DataRepository repository;
  final Symptom symptom;

  const TriageScreen({super.key, required this.repository, required this.symptom});

  @override
  State<TriageScreen> createState() => _TriageScreenState();
}

class _TriageScreenState extends State<TriageScreen> {
  int qIndex = 0;
  final Map<String, bool> answers = {};

  Symptom get s => widget.symptom;

  void _answer(bool v) {
    setState(() {
      answers[s.questions[qIndex].key] = v;
      qIndex += 1;
    });
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final lang = AppState.language.value;
    if (qIndex >= s.questions.length) {
      final level = evaluateTriage(s, answers);
      return level == 'emergency'
          ? EmergencyScreen(repository: widget.repository, symptom: s)
          : ReferralScreen(repository: widget.repository, symptom: s, urgent: level == 'urgent');
    }
    final q = s.questions[qIndex];
    return Scaffold(
      appBar: AppBar(title: Text('${s.icon} ${s.title[lang.code] ?? s.title['fa']}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // توضیح کوتاه + نشانه‌های خطر (بخش بالای جریان)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(s.brief[lang.code] ?? s.brief['fa'] ?? '',
                      style: const TextStyle(fontSize: 15, height: 1.7)),
                  if (s.redFlags.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Text('🚩 ${loc.t('red_flags')}',
                        style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.accent)),
                    for (final f in s.redFlags)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text('• ${f[lang.code] ?? f['fa'] ?? ''}'),
                      ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  Text('${loc.t('question')} ${qIndex + 1}/${s.questions.length}',
                      style: const TextStyle(color: AppColors.muted, fontSize: 13)),
                  const SizedBox(height: 8),
                  Text(q.text[lang.code] ?? q.text['fa'] ?? '',
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
                      textAlign: TextAlign.center),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
                  onPressed: () => _answer(true),
                  child: Text(loc.t('yes')),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _answer(false),
                  child: Text(loc.t('no')),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            loc.t('disclaimer'),
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.muted, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

/// صفحهٔ اورژانس: انتخاب کشور → شمارهٔ درست + tel: + متن آماده (بدون ادعا).
class EmergencyScreen extends StatelessWidget {
  final DataRepository repository;
  final Symptom? symptom;

  const EmergencyScreen({super.key, required this.repository, this.symptom});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final lang = AppState.language.value;
    final order = repository.emergencyOrder;
    return Scaffold(
      appBar: AppBar(title: Text(loc.t('emergency'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(loc.t('choose_country'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center),
          const SizedBox(height: 12),
          for (final cc in order)
            Card(
              child: ListTile(
                title: Text(repository.emergencyCountries[cc]
                        ?.label[lang.code] ??
                    repository.emergencyCountries[cc]?.label['fa'] ??
                    cc),
                trailing: Text(
                  repository.emergencyCountries[cc]?.ambulance ?? repository.emergencyFallback,
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.accent),
                ),
                onTap: () => _showNumber(context, repository.emergencyCountries[cc]),
              ),
            ),
        ],
      ),
    );
  }

  void _showNumber(BuildContext context, EmergencyCountry? c) {
    final loc = AppLocalizations.of(context);
    final num = c?.ambulance ?? repository.emergencyFallback;
    final info = StringBuffer('🚨 ${symptom != null ? (symptom!.title['fa'] ?? '') : loc.t('emergency')}');
    if (c != null) info.write('\n🌍 ${c.label['fa'] ?? c.code}');
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('${loc.t('call')} $num',
                  style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.accent)),
              const SizedBox(height: 12),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
                icon: const Icon(Icons.call),
                label: Text('${loc.t('call')} $num'),
                onPressed: () => launchUrl(Uri(scheme: 'tel', path: num)),
              ),
              const SizedBox(height: 12),
              Text(info.toString(), textAlign: TextAlign.center),
              const SizedBox(height: 10),
              Text(
                loc.t('honest_note'),
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// صفحهٔ ارجاع: تخصص مرتبط + دکمهٔ پزشکان + یادآوری اورژانس.
class ReferralScreen extends StatelessWidget {
  final DataRepository repository;
  final Symptom symptom;
  final bool urgent;

  const ReferralScreen({
    super.key,
    required this.repository,
    required this.symptom,
    required this.urgent,
  });

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final lang = AppState.language.value;
    return Scaffold(
      appBar: AppBar(title: Text(loc.t('referral'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Text(
                '${symptom.icon} ${symptom.title[lang.code] ?? symptom.title['fa']}'
                '\n\n→ ${specialtyLabel(symptom.specialty, lang)}',
                style: const TextStyle(fontSize: 16, height: 1.6),
                textAlign: TextAlign.center,
              ),
            ),
          ),
          if (urgent) ...[
            const SizedBox(height: 8),
            Text(
              '⏳ ${loc.t('emergency')}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.accent, fontWeight: FontWeight.w700),
            ),
          ],
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text(loc.t('coming_soon'))),
              );
            },
            child: Text(loc.t('see_doctors')),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.accent,
              side: const BorderSide(color: AppColors.accent),
            ),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => EmergencyScreen(repository: repository, symptom: symptom),
              ),
            ),
            child: Text(loc.t('call_emergency')),
          ),
        ],
      ),
    );
  }
}
