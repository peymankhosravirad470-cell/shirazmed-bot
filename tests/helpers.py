# -*- coding: utf-8 -*-
"""هارنس مشترک آزمون‌های اجباری — بدون توکن واقعی، بدون شبکه، بدون اثر روی مخزن.

الگو (همان هارنس اثبات‌شده‌ی اسکریپت‌های قبلی):
- DATA_DIR/… به tmp هدایت می‌شود (قبل از import config)
- fake_post جای app.bot._post می‌نشیند و همه‌ی فراخوانی‌های API را ثبت می‌کند
- هر Update/set_bot کامل می‌شود تا مسیر واقعی handlerها اجرا شود
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import traceback
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚠️ ترتیب حیاتی: env باید قبل از import ماژول‌های پروژه تنظیم شود
_TMP = tempfile.mkdtemp(prefix="smtest_")
os.environ.setdefault("BALE_BOT_TOKEN", "TEST:FAKE_TOKEN_FOR_TESTS")
os.environ["DATA_DIR"] = os.path.join(_TMP, "data")
os.environ["DATA_SEED_DIR"] = os.path.join(_TMP, "seed")
# 🧹 ایزولاسیون: مسیر پشتیبان مشترک (/tmp/shirazmed_data) بین اجرای سوئیت‌ها
# نباید state نشت بدهد (نوبت paid باقی‌مانده → «اسلات اشغال» کاذب در سوت بعدی).
os.environ["MEDS_FALLBACK_DIR"] = os.path.join(_TMP, "fallback_data")
os.environ.setdefault("ADMIN_CHAT_ID", "111")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def tmp_dir() -> str:
    return _TMP


class CallRecorder:
    """ثبت همه‌ی فراخوانی‌های API ربات (endpoint, data)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._seq = {"n": 100}

    async def fake_post(self, endpoint: str, data: dict | None = None, *args, **kwargs):
        data = dict(data or {})
        self.calls.append((endpoint, data))
        if endpoint == "getMe":
            return {
                "id": 900700, "is_bot": True, "first_name": "ShirazMedTest",
                "username": "shirazmed_test_bot",
                "can_join_groups": True, "can_read_all_group_messages": False,
                "supports_inline_queries": False, "can_pin_messages": True,
            }
        if endpoint in ("sendMessage", "editMessageText", "sendDocument", "sendPhoto"):
            self._seq["n"] += 1
            return {"message_id": self._seq["n"], "date": 1, "chat": {"id": data.get("chat_id", 1), "type": "private"}}
        if endpoint == "deleteMessage":
            return True
        if endpoint == "answerCallbackQuery":
            return True
        return True

    # ── کوئری‌های کمکی ──
    def sent_texts(self) -> list[str]:
        return [d.get("text", "") for ep, d in self.calls if ep in ("sendMessage", "editMessageText") and d.get("text")]

    def sent_to(self, chat_id: int) -> list[dict]:
        return [d for ep, d in self.calls if ep in ("sendMessage", "editMessageText", "sendDocument") and (d.get("chat_id") == chat_id or (isinstance(d.get("chat"), dict) and d["chat"].get("id") == chat_id))]

    def keyboards(self) -> list[Any]:
        return [d.get("reply_markup") for ep, d in self.calls if ep in ("sendMessage", "editMessageText") and d.get("reply_markup") is not None]

    def documents(self) -> list[dict]:
        return [d for ep, d in self.calls if ep == "sendDocument"]

    def reset(self) -> None:
        self.calls.clear()


REC = CallRecorder()


def kb_buttons(rm: Any) -> list[tuple[str, str]]:
    """استخراج (label, callback_data|url) از reply_markup (dict یا PTB object)."""
    if rm is None:
        return []
    rows: Any
    if hasattr(rm, "inline_keyboard"):
        rows = rm.inline_keyboard
    elif isinstance(rm, dict):
        rows = rm.get("inline_keyboard", [])
    else:
        return []
    out = []
    for row in rows:
        for b in row:
            if hasattr(b, "text"):
                out.append((b.text, b.callback_data or b.url or ""))
            elif isinstance(b, dict):
                out.append((b.get("text", ""), b.get("callback_data") or b.get("url") or ""))
    return out


def kb_rows(rm: Any) -> list[list[tuple[str, str]]]:
    if rm is None:
        return []
    rows: Any = rm.inline_keyboard if hasattr(rm, "inline_keyboard") else (rm.get("inline_keyboard", []) if isinstance(rm, dict) else [])
    out = []
    for row in rows:
        r = []
        for b in row:
            if hasattr(b, "text"):
                r.append((b.text, b.callback_data or b.url or ""))
            elif isinstance(b, dict):
                r.append((b.get("text", ""), b.get("callback_data") or b.get("url") or ""))
        out.append(r)
    return out


def make_user(user_id: int, first_name: str = "Tester", username: str | None = "tester"):
    from telegram import User
    return User(id=user_id, is_bot=False, first_name=first_name, username=username)


def make_message(user_id: int, text: str, chat_id: int | None = None):
    from telegram import Chat, Message
    from telegram.constants import ChatType
    chat_id = chat_id if chat_id is not None else user_id
    return Message(
        message_id=0, date=0, chat=Chat(id=chat_id, type=ChatType.PRIVATE),
        from_user=make_user(user_id), text=text,
    )


def make_start_update(user_id: int, text: str = "/start", chat_id: int | None = None):
    """Update پیام متنی با entity BOT_COMMAND (برای CommandHandler واقعی).

    ⚠️ PTB Message بعد از ساخت frozen است؛ entities باید در سازنده داده شود.
    """
    from telegram import Chat, Message, MessageEntity, Update
    from telegram.constants import ChatType
    chat_id = chat_id if chat_id is not None else user_id
    cmd_len = len(text.split()[0])
    m = Message(
        message_id=0, date=0, chat=Chat(id=chat_id, type=ChatType.PRIVATE),
        from_user=make_user(user_id), text=text,
        entities=(MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=cmd_len),),
    )
    m._bot = _APP.bot
    u = Update(update_id=next_id(), message=m)
    u._bot = _APP.bot
    return u


def make_text_update(user_id: int, text: str, chat_id: int | None = None):
    from telegram import Update
    m = make_message(user_id, text, chat_id)
    m._bot = _APP.bot
    u = Update(update_id=next_id(), message=m)
    u._bot = _APP.bot
    return u


def make_cb_update(user_id: int, data: str, chat_id: int | None = None, message_text: str = "x"):
    from telegram import CallbackQuery, Update
    chat_id = chat_id if chat_id is not None else user_id
    m = make_message(user_id, message_text, chat_id)
    m._bot = _APP.bot
    cq = CallbackQuery(id=f"cq{next_id()}", from_user=make_user(user_id), chat_instance="ci", data=data, message=m)
    cq._bot = _APP.bot
    u = Update(update_id=next_id(), callback_query=cq)
    u._bot = _APP.bot
    return u


def next_id() -> int:
    next_id.n += 1
    return next_id.n
next_id.n = 5000

_APP: Any = None


async def build_app(**env_overrides: str):
    """ساخت Application واقعی (پلتفرم بله با توکن جعلی) + نصب fake_post + bind runtime."""
    global _APP
    from app import runtime
    from app.bot import build_application
    app = build_application("bale")
    app.bot._post = REC.fake_post  # type: ignore[attr-defined]
    await app.initialize()
    runtime.bind_application(app)  # پل health-thread → event loop تست
    _APP = app
    return app


async def process(u) -> None:
    await _APP.process_update(u)


class Result:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> bool:
        if cond:
            self.passed += 1
            print(f"  ✔ {name}")
        else:
            self.failed += 1
            msg = f"  ✘ {name}" + (f" — {detail}" if detail else "")
            print(msg)
            self.failures.append(f"{name} {detail}".strip())
        return cond

    def finish(self, suite: str) -> int:
        print(f"\n== {suite}: {self.passed} passed, {self.failed} failed ==")
        for f in self.failures:
            print(f"   FAIL → {f}")
        return 1 if self.failed else 0


def run(main_coro_fn, suite: str) -> None:
    """اجرای یک سوت؛ خروجی exit code درست."""
    try:
        try:
            rc = asyncio.run(main_coro_fn())
        except TypeError:
            rc = main_coro_fn()
    except Exception:
        traceback.print_exc()
        rc = 1
    sys.exit(rc)


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
