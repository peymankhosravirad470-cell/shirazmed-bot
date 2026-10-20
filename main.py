# -*- coding: utf-8 -*-
"""Shiraz Medical Bot v46 — minimal entrypoint."""

import logging
import sys
from pathlib import Path

from app.bot import build_application


def main() -> None:
    """Configure logging, ensure data dir, and start polling."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    Path("data").mkdir(parents=True, exist_ok=True)
    try:
        app = build_application()
        app.run_polling()
    except Exception as exc:
        logging.exception("Fatal error during startup: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()