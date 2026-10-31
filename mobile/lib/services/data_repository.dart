import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

import '../models/models.dart';

/// بارگذاری دادهٔ بسته‌بندی‌شده (assets/data) — همان دادهٔ ربات.
///
/// نسخه‌های بعدی می‌توانند علاوه بر این، از API عمومی شیراز مدیکال
/// (main_api.py) دادهٔ زنده بگیرند؛ ساختار مدل‌ها عمداً سازگار است.
class DataRepository {
  List<Symptom> symptoms = [];
  Map<String, EmergencyCountry> emergencyCountries = {};
  List<String> emergencyOrder = [];
  String emergencyFallback = '112';
  List<SearchCategory> searchCategories = [];

  Future<void> loadAll() async {
    symptoms = await loadSymptoms();
    final em = await loadEmergency();
    emergencyOrder = em.$1;
    emergencyCountries = em.$2;
    emergencyFallback = em.$3;
    searchCategories = await loadSearchIndex();
  }

  Future<List<Symptom>> loadSymptoms() async {
    final raw = await rootBundle.loadString('assets/data/symptoms.json');
    final data = jsonDecode(raw) as Map<String, dynamic>;
    return (data['symptoms'] as List<dynamic>)
        .map((e) => Symptom.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<(List<String>, Map<String, EmergencyCountry>, String)>
      loadEmergency() async {
    final raw = await rootBundle.loadString('assets/data/emergency_numbers.json');
    final data = jsonDecode(raw) as Map<String, dynamic>;
    final countries = (data['countries'] as Map<String, dynamic>).map(
      (code, rec) => MapEntry(
        code,
        EmergencyCountry.fromJson(code, rec as Map<String, dynamic>),
      ),
    );
    return (
      (data['order'] as List<dynamic>).map((e) => e.toString()).toList(),
      countries,
      data['fallback'] as String? ?? '112',
    );
  }

  Future<List<SearchCategory>> loadSearchIndex() async {
    final raw = await rootBundle.loadString('assets/data/search_index.json');
    final data = jsonDecode(raw) as Map<String, dynamic>;
    return (data['categories'] as List<dynamic>)
        .map((e) => SearchCategory(
              id: e['id'] as String,
              icon: e['icon'] as String? ?? '🔎',
              label: Symptom.strMap(e['label']),
              items: (e['items'] as List<dynamic>? ?? [])
                  .map((it) => SearchItem(
                        index: it['i'] as int,
                        name: Symptom.strMap(it['n']),
                        corpus: it['c'] as String? ?? '',
                        subtitle: it['s'] as String? ?? '',
                      ))
                  .toList(),
            ))
        .toList();
  }
}
