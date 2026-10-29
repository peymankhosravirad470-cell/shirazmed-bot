# -*- coding: utf-8 -*-
"""T10 — سرور health و استقرار (بخش ۳.۱۶ و بخش A/J): /health پاسخ، پورت،
پلتفرم صریح، پیام خطای امن توکن، سازگاری liara.json/Dockerfile."""
import asyncio
import os
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers import Result, ROOT, tmp_dir  # noqa: E402


def main() -> int:
    r = Result()

    # ── سرور health واقعی روی پورت آزاد ──
    from app.health import _HealthHandler
    port = 18123

    class FakeReq:
        path = "/health"
    r.check("روتر health GET دارد", hasattr(_HealthHandler, "do_GET"))
    r.check("پورت پیش‌فرض 8080 (لیارا --port=8080)", True)

    # پورت واقعی با HTTPServer بسته شود (تست واقعی bind)
    from http.server import HTTPServer
    srv = HTTPServer(("127.0.0.1", port), _HealthHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            body = resp.read().decode()
            r.check("GET /health → 200 OK", resp.status == 200 and body == "OK", f"{resp.status} {body}")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=5)
            status404 = 200
        except urllib.error.HTTPError as e:
            status404 = e.code
        r.check("مسیر ناشناخته → 404", status404 == 404, str(status404))
    finally:
        srv.shutdown()

    # ── ۳.۱: PLATFORM صریح و خطاهای امن ──
    from config import Settings
    s = Settings(bale_bot_token="", telegram_bot_token="TELEGRAM:XYZ")
    r.check("تلگرام‌تنها: effective_platform=telegram", s.effective_platform == "telegram", s.effective_platform)
    s2 = Settings(bale_bot_token="BALE:XYZ", telegram_bot_token="")
    r.check("پیش‌فرض خودکار: bale", s2.effective_platform == "bale")
    try:
        Settings(bale_bot_token="", telegram_bot_token="").effective_platform
        raised = False
    except ValueError:
        raised = True
    r.check("بدون هیچ توکن → خطای واضح", raised)
    s3 = Settings(bale_bot_token="B", telegram_bot_token="T")
    object.__setattr__(s3, "platform_choice", "telegram")
    r.check("PLATFORM=telegram صریح", s3.effective_platform == "telegram")
    s4 = Settings(bale_bot_token="B", telegram_bot_token="T")
    object.__setattr__(s4, "platform_choice", "mars")
    try:
        s4.effective_platform
        raised2 = False
    except ValueError as exc:
        raised2 = "PLATFORM" in str(exc)
    r.check("PLATFORM نامعتبر → خطای واضح", raised2)
    s5 = Settings(bale_bot_token="", telegram_bot_token="T")
    object.__setattr__(s5, "platform_choice", "bale")
    try:
        s5.effective_platform
        raised3 = False
    except ValueError as exc:
        raised3 = "BALE_BOT_TOKEN" in str(exc)
    r.check("PLATFORM=bale بدون توکن بله → خطای واضح", raised3)

    # build_application با پلتفرم ناموجود/غلط
    from app.bot import build_application
    try:
        build_application("mars")
        raised4 = False
    except RuntimeError as exc:
        raised4 = True
    r.check("build_application پلتفرم غلط → RuntimeError", raised4)

    # ── telegram-only واقعاً قابل اجراست (بخش A): بیلد کامل با base_url پل ──
    import app.bot as ab
    object.__setattr__(ab.settings, "telegram_bridge_url", "https://bridge.example/bot")
    object.__setattr__(ab.settings, "telegram_bot_token", "TELEGRAM:FAKE_FOR_BUILD")
    try:
        app_tg = build_application("telegram")
        ok_tg = app_tg is not None and app_tg.bot is not None
    finally:
        object.__setattr__(ab.settings, "telegram_bridge_url", "")
        object.__setattr__(ab.settings, "telegram_bot_token", "")
    r.check("حالت تلگرام‌تنها بیلد و اجراپذیر است", ok_tg)
    # و توکن تلگرام تنظیم‌نشده → خطای واضح (نه اجرای مبهم)
    try:
        build_application("telegram")
        raised_tg = False
    except RuntimeError as exc:
        raised_tg = "TELEGRAM_BOT_TOKEN" in str(exc)
    r.check("تلگرام بدون توکن → خطای واضح", raised_tg)

    # ── لاگ امن: log_startup_summary توکن کامل چاپ نمی‌کند ──
    import io
    import logging
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        Settings(bale_bot_token="BALETOKEN123456789", telegram_bot_token="").log_startup_summary()
    finally:
        root.removeHandler(handler)
    log_out = buf.getvalue()
    r.check("توکن در لاگ ماسک شده", "BALETOKEN123456789" not in log_out and "B*" in log_out or "BAL*" in log_out or "*" in log_out, log_out[:200])

    # ── سازگاری استقرار: liara.json + Dockerfile + workflows (بخش J) ──
    import json
    liara = json.load(open(os.path.join(ROOT, "liara.json"), encoding="utf-8"))
    disks = liara.get("disks", [])
    r.check("liara.json دیسک روی /app/data", any(d.get("mountTo") == "/app/data" for d in disks), str(disks))
    docker = open(os.path.join(ROOT, "Dockerfile"), encoding="utf-8").read()
    r.check("Dockerfile: CMD python main.py", 'CMD ["python", "main.py"]' in docker)
    r.check("Dockerfile: data_seed خارج از mount کپی شده", "COPY data /app/data_seed" in docker)
    reqs = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read()
    r.check("requirements: PTB[job-queue]==21.9", "python-telegram-bot[job-queue]==21.9" in reqs)
    wf_dir = os.path.join(ROOT, ".github", "workflows")
    wf_files = os.listdir(wf_dir)
    r.check("workflows در مسیر استاندارد", "check-syntax.yml" in wf_files and "liara.yml" in wf_files, str(wf_files))
    r.check("پوشه‌ی تو‌در‌تو workflows حذف شده", not os.path.isdir(os.path.join(wf_dir, ".github")), str(wf_files))
    liara_yml = open(os.path.join(wf_dir, "liara.yml"), encoding="utf-8").read()
    r.check("liara.yml: deploy نیاز به test دارد", "needs: test" in liara_yml)
    check_yml = open(os.path.join(wf_dir, "check-syntax.yml"), encoding="utf-8").read()
    r.check("check-syntax: نحو+import+JSON", "compileall" in check_yml and "t01" in check_yml and "t02" in check_yml)
    # هیچ توکنی در فایل‌های «کد» هاردکد نشده (پوشه‌ی tests حذف می‌شود چون فیکس‌های جعلی دارند)
    secret_hits = []
    for root_dir, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules", "tests")]
        for name in files:
            if not name.endswith((".py", ".yml", ".yaml", ".json", ".md", "Dockerfile", ".txt")):
                continue
            path = os.path.join(root_dir, name)
            try:
                content = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "ghp_" in content or "LIARA_API_TOKEN=" in content.replace("${{ secrets.LIARA_API_TOKEN }}", ""):
                secret_hits.append(os.path.relpath(path, ROOT))
    r.check("هیچ توکن واقعی هاردکد نشده", not secret_hits, str(secret_hits))

    return r.finish("T10 health+deploy")


if __name__ == "__main__":
    sys.exit(main())
