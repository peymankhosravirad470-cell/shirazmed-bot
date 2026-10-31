# -*- coding: utf-8 -*-
"""T02 — بارگذاری همه‌ی JSONها + ساختار + پزشکان تکراری + شمارش (بخش ۳.۲ و ۳.۳ و بخش F/G)."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import Result, ROOT  # noqa: E402


def main() -> int:
    r = Result()
    bad = []
    all_files = sorted(glob.glob(os.path.join(ROOT, "data", "*.json")) + glob.glob(os.path.join(ROOT, "data", "doctors", "*.json")))
    r.check("فایل JSON پیدا شد", len(all_files) >= 60, f"{len(all_files)} file")
    for path in all_files:
        try:
            with open(path, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{os.path.relpath(path, ROOT)}: {exc}")
    r.check("همه‌ی JSONها valid", not bad, "; ".join(bad[:5]))

    # transport_hubs ساختار شیء دارد و show_hubs باید آن را بخواند (بخش G)
    from app.handlers.callbacks import _transport_hub_items
    hubs = _transport_hub_items()
    r.check("transport_hubs ≥ 4 مرکز (فرودگاه/راه‌آهن/پایانه‌ها)", len(hubs) >= 4, f"{len(hubs)}")
    names = [str(h.get("official_name_fa", "")) for h in hubs]
    r.check("فرودگاه شیراز در لیست", any("دستغیب" in n or "فرودگاه" in n for n in names), str(names[:2]))
    with_coords = sum(1 for h in hubs if h.get("lat") is not None and h.get("lng") is not None)
    r.check("مختصات مراکز قابل تبدیل به float", with_coords >= 2, f"{with_coords}/{len(hubs)}")

    # پزشکان: تکراری/خالی/وضعیت نامعتبر + شمارش واقعی (بخش F)
    from app.services import doctor_loader
    total = 0
    active_specs = 0
    total_active = 0
    dup_report = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "doctors", "*.json"))):
        spec = os.path.basename(path)[:-5]
        try:
            docs = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(docs, list):
            continue
        seen = set()
        active = 0
        for d in docs:
            if not isinstance(d, dict):
                continue
            total += 1
            did = str(d.get("id", ""))
            if did in seen:
                dup_report.append(f"{spec}:{did}")
            seen.add(did)
            st = d.get("status", "active")
            if st not in ("active", "inactive"):
                dup_report.append(f"{spec}:{did}:bad-status:{st}")
            if st == "active" and str(d.get("name_fa", "")).strip():
                active += 1
        total_active += active
        if active:
            active_specs += 1
    r.check("شناسه تکراری پزشک = 0", not dup_report, "; ".join(dup_report[:5]))
    # 🔧 CI-FIX (T02): workflow روزانهٔ «Collect Doctors» دادهٔ پزشکان را به‌روز
    # می‌کند (افزودن/حذف پزشک؛ مثلاً 114→115 در 2026-10-31). تعداد دقیق نباید
    # هاردکد شود وگرنه هر به‌روزرسانی داده، CI و دیپلوی لیارا را قرمز می‌کند.
    # فقط ثابت‌های ساختاری چک می‌شوند تا تغییر طبیعیِ داده، خطا تلقی نشود:
    r.check("کل رکوردهای پزشکان ≥ 100 (دادهٔ واقعی موجود)", total >= 100, str(total))
    r.check("پزشکان فعال ≥ 100 و ≤ کل رکوردها", 100 <= total_active <= total, f"active={total_active}/total={total}")
    r.check("تخصص‌های دارای پزشک فعال ≥ 1", active_specs >= 1, f"{active_specs} specs")
    specs = doctor_loader.load_specialties()
    r.check("لودر فقط تخصص‌های دارای پزشک را می‌دهد", all(s["count"] > 0 for s in specs))
    r.check("تعداد تخصص فعال لودر = تعداد واقعی فایل‌ها", len(specs) == active_specs, f"loader={len(specs)}/files={active_specs}")

    # hospitals2 تکرار کامل hospitals — dedupe در show_hospitals
    h1 = json.load(open(os.path.join(ROOT, "data", "hospitals.json"), encoding="utf-8"))
    h2 = json.load(open(os.path.join(ROOT, "data", "hospitals2.json"), encoding="utf-8"))
    ids1 = {str(i.get("id")) for i in h1}
    ids2 = {str(i.get("id")) for i in h2}
    r.check("hospitals2.json تکرار کامل hospitals.json است (مستند در گزارش)", ids1 == ids2 and len(ids1) == 7, f"{len(ids1)}/{len(ids2)}")

    return r.finish("T02 json+data")


if __name__ == "__main__":
    sys.exit(main())
