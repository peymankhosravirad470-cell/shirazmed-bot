import 'package:flutter/material.dart';

/// تم بصری Shiraz Medical — آرام، حرفه‌ای و مناسب سالمندان (متن درشت‌تر).
class AppColors {
  static const primary = Color(0xFF0E6E6B); // سبز-آبی درمانی
  static const primaryDark = Color(0xFF0A4F4D);
  static const accent = Color(0xFFE05A6C); // قرمز اورژانس
  static const background = Color(0xFFF6F8F8);
  static const card = Colors.white;
  static const text = Color(0xFF1C2B2A);
  static const muted = Color(0xFF6B7B7A);
}

class AppTheme {
  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primary,
        primary: AppColors.primary,
        secondary: AppColors.accent,
      ),
      scaffoldBackgroundColor: AppColors.background,
    );
    return base.copyWith(
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        centerTitle: true,
      ),
      textTheme: base.textTheme.apply(bodyColor: AppColors.text),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(52),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: AppColors.primary),
        ),
      ),
    );
  }
}
