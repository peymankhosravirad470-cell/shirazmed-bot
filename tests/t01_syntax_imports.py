# -*- coding: utf-8 -*-
"""T01 — بررسی نحو و importهای اصلی (بخش ۳.۱ دستور + بخش J)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import Result, ROOT  # noqa: E402


def main() -> int:
    r = Result()
    import compileall
    ok = compileall.compile_dir(ROOT, quiet=2, force=True)
    r.check("compileall کل مخزن", bool(ok))

    # import همه‌ی ماژول‌های اصلی — خطای import در runtime ربات یعنی کرش کامل
    import importlib
    modules = [
        "config", "main_api",
        "app", "app.runtime", "app.data_seed", "app.health",
        "app.bot", "app.handlers.start", "app.handlers.callbacks",
        "app.handlers.booking", "app.handlers.survey", "app.handlers.companion",
        "app.handlers.meds", "app.handlers.doctor_reg", "app.handlers.chunks",
        "app.services.booking", "app.services.payment", "app.services.receipt",
        "app.services.contract", "app.services.data_loader", "app.services.doctor_loader",
        "app.keyboards.main", "app.keyboards.tourism", "app.keyboards.paramedical",
        "app.keyboards.elderly", "app.keyboards.non_medical", "app.keyboards.utils",
        "app.locales",
    ]
    for mod in modules:
        try:
            importlib.import_module(mod)
            r.check(f"import {mod}", True)
        except Exception as exc:  # noqa: BLE001
            r.check(f"import {mod}", False, repr(exc))

    # کلاس‌ها/ثابت‌های کلیدی
    from config import VERSION, DATA_DIR
    r.check("VERSION تعریف شده", isinstance(VERSION, str) and VERSION != "", VERSION)
    r.check("DATA_DIR مطلق", os.path.isabs(DATA_DIR), DATA_DIR)

    import app.services.booking as bs
    r.check("AppointmentsReadError وجود دارد (fail-closed)", hasattr(bs, "AppointmentsReadError"))
    import app.services.payment as pm
    r.check("قفل تراکنش _TX_LOCK وجود دارد", hasattr(pm, "_TX_LOCK"))
    import app.data_seed as ds
    r.check("data_seed RUNTIME_ONLY شامل appointments", "appointments.json" in ds.RUNTIME_ONLY)

    return r.finish("T01 syntax+imports")


if __name__ == "__main__":
    sys.exit(main())
