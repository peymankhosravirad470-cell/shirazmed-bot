# -*- coding: utf-8 -*-
"""سرور سلامت سبک برای پاس‌کردن health-check پورت لیارا (ربات خودش هیچ HTTP سروری ندارد)."""

from __future__ import annotations

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    """فقط به هر درخواستی 200 OK می‌دهد؛ هیچ منطقی ندارد."""

    def do_GET(self) -> None:  # noqa: N802 (امضای الزامی http.server)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """لاگ پیش‌فرض noisy این کلاس را خاموش می‌کند."""
        return


def start_health_server() -> None:
    """یک سرور HTTP روی پورت PORT (پیش‌فرض 8080) در یک ترد پس‌زمینه اجرا می‌کند."""
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("سرور health-check روی پورت %s بالا آمد.", port)
