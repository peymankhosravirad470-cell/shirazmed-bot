# -*- coding: utf-8 -*-
"""اجرای کامل ۱۸ آزمون اجباری (سکشن ۳ دستور ممیزی) — بدون توکن واقعی و بدون شبکه.

هر فایل t* مستقل است؛ این runner همه را با subprocess ایزوله اجرا می‌کند و
جدول نتیجه می‌دهد. exit code = تعداد سوت‌های شکست‌خورده (سقف ۱۲۵).
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SUITES = [
    ("T01 نحو + importها", "t01_syntax_imports.py"),
    ("T02 بارگذاری JSON + پزشکان", "t02_json_data.py"),
    ("T03 رزرو + fail-closed", "t03_booking_flow.py"),
    ("T04 پرداخت کامل", "t04_payment_flow.py"),
    ("T05 رسید PDF", "t05_receipt.py"),
    ("T06 ثبت‌نام پزشک", "t06_doctor_reg.py"),
    ("T07 منوها + callbackها", "t07_menus_callbacks.py"),
    ("T08 یادآور دارو", "t08_meds.py"),
    ("T09 /start ریست + بازیابی", "t09_start_reset.py"),
    ("T10 health + استقرار + پلتفرم", "t10_health_deploy.py"),
    ("T11 امنیت لاگ + سه‌زبانه", "t11_security_i18n.py"),
    ("T12 شش مورد محدوده نهایی", "t12_scope_six.py"),
]


def main() -> int:
    failed = []
    total_seconds = 0.0
    print("=" * 72)
    print("آزمون‌های اجباری شیراز مدیکال — ۱۸ موردِ دستور، در ۱۱ سوت")
    print("=" * 72)
    for title, fname in SUITES:
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, fname)],
            capture_output=True, text=True, timeout=300, cwd=ROOT,
        )
        dt = time.time() - t0
        total_seconds += dt
        status = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"\n######## {title} [{fname}] → {status} ({dt:.1f}s)")
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        # خلاصه: آخرین خط نتیجه + خطاهای FAIL
        lines = out.splitlines()
        tail = [l for l in lines if l.startswith("== ") or l.startswith("   FAIL") or "✘" in l]
        for l in tail[-25:]:
            print(l)
        if proc.returncode != 0:
            failed.append((title, fname))
            if err:
                print("---- stderr (tail) ----")
                for l in err.splitlines()[-30:]:
                    print(l)
    print("\n" + "=" * 72)
    print(f"نتیجه‌ی نهایی: {len(SUITES) - len(failed)}/{len(SUITES)} سوت PASS — {total_seconds:.1f}s")
    if failed:
        print("سوت‌های شکست‌خورده:")
        for title, fname in failed:
            print(f"  ✘ {title} [{fname}]")
        return min(125, len(failed))
    print("همه‌ی آزمون‌ها موفق ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
