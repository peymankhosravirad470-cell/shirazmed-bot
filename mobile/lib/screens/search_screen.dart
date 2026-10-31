import 'package:flutter/material.dart';

import '../core/l10n/app_localizations.dart';
import '../core/theme/app_theme.dart';
import '../services/data_repository.dart';
import '../services/search_service.dart';

/// صفحهٔ جست‌وجوی هوشمند — نتیجه دسته‌بندی‌شده (الزام محصول بخش ۱).
class SearchScreen extends StatefulWidget {
  final DataRepository? repository;

  const SearchScreen({super.key, this.repository});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  late final DataRepository repo;
  List<SearchHit> results = const [];
  bool searched = false;

  @override
  void initState() {
    super.initState();
    repo = widget.repository ?? DataRepository();
    if (repo.searchCategories.isEmpty) {
      repo.loadAll().then((_) => setState(() {}));
    }
  }

  void _run(String q) {
    setState(() {
      results = SearchService.search(q, repo.searchCategories);
      searched = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final lang = AppState.language.value;
    return Scaffold(
      appBar: AppBar(title: Text(loc.t('search'))),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              autofocus: true,
              textInputAction: TextInputAction.search,
              onSubmitted: _run,
              onChanged: (v) {
                if (v.trim().length >= 2) _run(v);
              },
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: loc.t('search_hint'),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
          Expanded(
            child: !searched
                ? const SizedBox.shrink()
                : results.isEmpty
                    ? Center(child: Text(loc.t('no_result')))
                    : ListView.builder(
                        itemCount: results.length,
                        itemBuilder: (context, i) {
                          final hit = results[i];
                          final name = hit.item.name[lang.code] ??
                              hit.item.name['fa'] ??
                              '';
                          final catLabel = hit.category.label[lang.code] ??
                              hit.category.label['fa'] ??
                              hit.category.id;
                          return Card(
                            child: ListTile(
                              leading: Text(hit.category.icon,
                                  style: const TextStyle(fontSize: 24)),
                              title: Text(name),
                              subtitle: hit.item.subtitle.isEmpty
                                  ? null
                                  : Text(hit.item.subtitle,
                                      maxLines: 1, overflow: TextOverflow.ellipsis),
                              trailing: Text(catLabel,
                                  style: const TextStyle(color: AppColors.muted, fontSize: 11)),
                              onTap: () {
                                // نتیجهٔ واقعی داده؛ صفحهٔ جزئیات در نسخهٔ بعد
                                // از API عمومی تغذیه می‌شود.
                                showModalBottomSheet<void>(
                                  context: context,
                                  builder: (_) => SafeArea(
                                    child: Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: Column(
                                        mainAxisSize: MainAxisSize.min,
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text('${hit.category.icon} $name',
                                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                                          if (hit.item.subtitle.isNotEmpty)
                                            Padding(
                                              padding: const EdgeInsets.only(top: 8),
                                              child: Text(hit.item.subtitle),
                                            ),
                                        ],
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
