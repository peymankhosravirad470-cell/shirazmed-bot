import 'package:flutter/material.dart';

import '../core/l10n/app_localizations.dart';
import '../core/theme/app_theme.dart';
import '../services/data_repository.dart';
import 'advisor/advisor_screen.dart';
import 'search_screen.dart';

/// صفحهٔ اصلی — جست‌وجو در اولویت (الزام محصول)، مشاور سلامت و اورژانس
/// همیشه در دسترس، سپس شش دستهٔ خدماتی (ساختار همسنگ منوی ربات).
class HomeScreen extends StatefulWidget {
  final DataRepository? repository;

  const HomeScreen({super.key, this.repository});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final DataRepository repo;
  bool loaded = false;

  @override
  void initState() {
    super.initState();
    repo = widget.repository ?? DataRepository();
    repo.loadAll().then((_) {
      if (mounted) setState(() => loaded = true);
    });
  }

  void _pickLanguage() {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final l in AppLanguage.values)
              ListTile(
                title: Text(l.label, textAlign: TextAlign.center),
                onTap: () {
                  AppState.language.value = l;
                  Navigator.pop(ctx);
                  setState(() {});
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations(context);
    final lang = AppState.language.value;
    final cats = [
      (loc.t('cat_medical'), Icons.local_hospital_outlined, AppColors.primary),
      (loc.t('cat_travel'), Icons.luggage_outlined, Color(0xFF2E7D9A)),
      (loc.t('cat_tourism'), Icons.tour_outlined, Color(0xFF8C6D1F)),
      (loc.t('cat_support'), Icons.support_agent_outlined, Color(0xFF5B7C99)),
      (loc.t('cat_me'), Icons.folder_shared_outlined, Color(0xFF4E6E81)),
      (loc.t('cat_contact'), Icons.forum_outlined, Color(0xFF6A5ACD)),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(loc.t('app_name')),
        actions: [
          IconButton(
            tooltip: loc.t('language'),
            onPressed: _pickLanguage,
            icon: const Icon(Icons.language),
          ),
        ],
      ),
      body: !loaded
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    loc.t('home_title'),
                    style: Theme.of(context).textTheme.titleMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  // 🔍 جست‌وجو — کاملاً در دسترس از صفحهٔ اصلی (الزام دستور)
                  InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const SearchScreen()),
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: AppColors.primary.withOpacity(.3)),
                        boxShadow: [
                          BoxShadow(color: Colors.black.withOpacity(.05), blurRadius: 8),
                        ],
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.search, color: AppColors.primary),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              loc.t('search_hint'),
                              style: TextStyle(color: AppColors.muted, fontSize: 16),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _BigButton(
                          icon: Icons.health_and_safety_outlined,
                          label: loc.t('advisor'),
                          color: AppColors.primary,
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => AdvisorScreen(repository: repo),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _BigButton(
                          icon: Icons.emergency_outlined,
                          label: loc.t('emergency'),
                          color: AppColors.accent,
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => AdvisorScreen(
                                repository: repo,
                                initialRoute: AdvisorRoute.emergency,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const _PlaceholderScreen(titleKey: 'book'),
                      ),
                    ),
                    icon: const Icon(Icons.calendar_month),
                    label: Text(loc.t('book')),
                  ),
                  const SizedBox(height: 20),
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 1.55,
                    children: [
                      for (final c in cats)
                        _CategoryCard(
                          title: c.$1,
                          icon: c.$2,
                          color: c.$3,
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => _PlaceholderScreen(titleKey: null, title: c.$1),
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '© Shiraz Medical — shirazmedicall.ir',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.muted, fontSize: 12),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    lang.label,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.muted, fontSize: 11),
                  ),
                ],
              ),
            ),
    );
  }
}

class _BigButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _BigButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 18),
          child: Column(
            children: [
              Icon(icon, color: Colors.white, size: 30),
              const SizedBox(height: 6),
              Text(
                label,
                style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CategoryCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _CategoryCard({
    required this.title,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: color, size: 30),
              const SizedBox(height: 8),
              Text(title, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlaceholderScreen extends StatelessWidget {
  final String? titleKey;
  final String? title;

  const _PlaceholderScreen({required this.titleKey, this.title});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(title ?? (titleKey != null ? loc.t(titleKey!) : '')),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.construction, size: 48, color: AppColors.muted),
              const SizedBox(height: 12),
              Text(
                loc.t('coming_soon'),
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.muted, fontSize: 15),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
