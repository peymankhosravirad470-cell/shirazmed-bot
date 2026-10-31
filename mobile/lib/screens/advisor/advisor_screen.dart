import 'package:flutter/material.dart';

import '../../core/l10n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../services/data_repository.dart';
import 'triage_flow.dart';

/// منوی «مشاور سلامت» — ۱۸ علامت (داده از assets/data/symptoms.json؛
/// همان محتوای ربات). مسیر مستقیم اورژانس هم از این‌جا شروع می‌شود.
enum AdvisorRoute { symptoms, emergency }

class AdvisorScreen extends StatelessWidget {
  final DataRepository repository;
  final AdvisorRoute initialRoute;

  const AdvisorScreen({
    super.key,
    required this.repository,
    this.initialRoute = AdvisorRoute.symptoms,
  });

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final lang = AppState.language.value;
    if (initialRoute == AdvisorRoute.emergency) {
      return EmergencyScreen(repository: repository);
    }
    final symptoms = repository.symptoms;
    return Scaffold(
      appBar: AppBar(title: Text(loc.t('advisor'))),
      body: symptoms.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(12),
              children: [
                Card(
                  color: AppColors.primary.withValues(alpha: .08),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(
                      loc.t('disclaimer'),
                      style: const TextStyle(color: AppColors.primaryDark, fontSize: 13, height: 1.6),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
                for (final s in symptoms)
                  Card(
                    child: ListTile(
                      leading: Text(s.icon, style: const TextStyle(fontSize: 26)),
                      title: Text(s.title[lang.code] ?? s.title['fa'] ?? s.id),
                      trailing: s.severity == 'critical'
                          ? const Icon(Icons.warning_amber_rounded, color: AppColors.accent)
                          : null,
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => TriageScreen(repository: repository, symptom: s),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}
