import '../models/models.dart';

/// موتور جست‌وجوی هوشمند اپ — همسنگ نسخهٔ ربات (search_engine.py):
/// نرمال‌سازی فارسی/عربی + تطبیق پیشوند + فاصلهٔ ویرایشی محدود + زیرمجموعهٔ
/// توکن‌ها؛ کوئری‌های بی‌معنی نتیجهٔ تصادفی نمی‌گیرند.
class SearchService {
  static String normalize(String text) {
    var s = text
        .replaceAll('ي', 'ی')
        .replaceAll('ك', 'ک')
        .replaceAll('ة', 'ه')
        .replaceAll('ۀ', 'ه')
        .replaceAll('أ', 'ا')
        .replaceAll('إ', 'ا')
        .replaceAll('ؤ', 'و')
        .replaceAll('ئ', 'ی')
        .toLowerCase();
    s = s.replaceAll(RegExp(r'[\u064B-\u065F\u0670\u0640\u200c\u200e\u200f]'), ' ');
    s = s.replaceAll(RegExp(r'[^\w\s]'), ' ');
    return s.trim().replaceAll(RegExp(r'\s+'), ' ');
  }

  static List<String> _tokens(String text) {
    final t = normalize(text);
    return t.isEmpty ? const [] : t.split(' ');
  }

  static int _editDistanceLimited(String a, String b, int maxD) {
    if ((a.length - b.length).abs() > maxD) return maxD + 1;
    var prev = List<int>.generate(b.length + 1, (i) => i);
    for (var i = 1; i <= a.length; i++) {
      final cur = <int>[i];
      var rowMin = i;
      for (var j = 1; j <= b.length; j++) {
        final cost = a.codeUnitAt(i - 1) == b.codeUnitAt(j - 1) ? 0 : 1;
        final v = [
          prev[j] + 1,
          cur[j - 1] + 1,
          prev[j - 1] + cost,
        ].reduce((x, y) => x < y ? x : y);
        cur.add(v);
        if (v < rowMin) rowMin = v;
      }
      if (rowMin > maxD) return maxD + 1;
      prev = cur;
    }
    return prev.last;
  }

  static bool _fuzzyHit(String q, String d) {
    if (q.isEmpty || d.isEmpty) return false;
    if (q == d) return true;
    if (q.length >= 3 && d.startsWith(q)) return true;
    if (q.length >= 4 && d.length >= 4 && d.contains(q)) return true;
    int maxD;
    if (q.length >= 7) {
      maxD = 2;
    } else if (q.length >= 4) {
      maxD = 1;
    } else if (q.length == 3 && q.substring(0, 2) == d.substring(0, 2)) {
      maxD = 1;
    } else {
      return false;
    }
    return _editDistanceLimited(q, d, maxD) <= maxD;
  }

  static int _score(List<String> queryToks, String corpus, String title) {
    if (queryToks.isEmpty) return 0;
    final titleToks = _tokens(title);
    final corpusToks = _tokens(corpus);
    var score = 0;
    for (final qt in queryToks) {
      if (qt.length < 2) return 0; // کوئری تک‌حرفی — نویز
      var best = 0;
      if (title.contains(qt)) best = 8;
      for (final dt in titleToks) {
        if (dt == qt) {
          best = best < 7 ? 7 : best;
        } else if (qt.length >= 3 && dt.startsWith(qt)) {
          best = best < 5 ? 5 : best;
        } else if (_fuzzyHit(qt, dt)) {
          best = best < 3 ? 3 : best;
        }
      }
      if (best == 0 && qt.length >= 3) {
        if (corpus.contains(qt)) {
          best = 4;
        } else if (qt.length >= 4) {
          for (final dt in corpusToks) {
            if (dt.length >= 4 && _editDistanceLimited(qt, dt, 1) <= 1) {
              best = 2;
              break;
            }
          }
        }
      }
      if (best == 0) return 0; // هر توکن باید جایی دیده شود
      score += best;
    }
    return score;
  }

  /// نتیجه: لیست (دسته، آیتم، امتیاز) مرتب — دسته‌بندی‌شده در UI.
  static List<SearchHit> search(
    String query,
    List<SearchCategory> categories, {
    int perCategory = 2,
    int maxGroups = 5,
  }) {
    final qToks = _tokens(query);
    if (qToks.isEmpty) return const [];
    final strong = qToks.where((t) => t.length >= 3).toList();
    final variants = <List<String>>[
      qToks,
      if (strong.length < qToks.length && strong.isNotEmpty) strong,
      ...strong.map((t) => [t]),
    ];
    final groups = <_Group>[];
    for (final cat in categories) {
      List<SearchHit> hits = [];
      for (final variant in variants) {
        hits = _match(cat, variant);
        if (hits.isNotEmpty) break;
      }
      if (hits.isNotEmpty) {
        groups.add(_Group(cat, hits));
      }
    }
    groups.sort((a, b) => b.best.compareTo(a.best));
    return [
      for (final g in groups.take(maxGroups)) ...g.hits.take(perCategory),
    ];
  }

  static List<SearchHit> _match(SearchCategory cat, List<String> variant) {
    final out = <SearchHit>[];
    for (final item in cat.items) {
      final title = item.name.values.where((v) => v.isNotEmpty).join(' ');
      if (title.isEmpty) continue;
      final s = _score(variant, item.corpus, normalize(title));
      if (s > 0) out.add(SearchHit(cat, item, s));
    }
    out.sort((a, b) => b.score.compareTo(a.score));
    return out;
  }
}

class SearchHit {
  final SearchCategory category;
  final SearchItem item;
  final int score;

  const SearchHit(this.category, this.item, this.score);
}

class _Group {
  final SearchCategory cat;
  final List<SearchHit> hits;
  int get best => hits.first.score;
  const _Group(this.cat, this.hits);
}
