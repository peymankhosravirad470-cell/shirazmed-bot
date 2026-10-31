import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'core/l10n/app_localizations.dart';
import 'core/theme/app_theme.dart';
import 'screens/home_screen.dart';

/// ریشهٔ اپلیکیشن Shiraz Medical.
///
/// وضعیت زبان سراسری با ValueNotifier نگه داشته می‌شود (بدون وابستگی اضافه؛
/// مهاجرت آینده به Riverpod/go_router ساختار را نمی‌شکند).
class ShirazMedicalApp extends StatelessWidget {
  const ShirazMedicalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<AppLanguage>(
      valueListenable: AppState.language,
      builder: (context, lang, _) {
        return MaterialApp(
          title: 'Shiraz Medical',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          locale: lang.locale,
          // RTL برای فارسی/عربی و LTR برای انگلیسی — الزام سه‌زبانه؛
          // GlobalWidgetsLocalizations هم جهت را از locale تضمین می‌کند.
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: const [
            AppLocalizationsDelegate(),
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: const HomeScreen(),
        );
      },
    );
  }
}
