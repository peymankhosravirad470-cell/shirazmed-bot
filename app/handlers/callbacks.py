# -*- coding: utf-8 -*-
"""هندلر عمومی موقت برای دکمه‌های منوی اصلی (بخش‌هایی که هنوز پیاده‌سازی نشده‌اند)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main import get_back_button


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پاسخ موقت به کلیک روی دکمه‌های منوی اصلی، به همراه دکمه‌ی بازگشت."""
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    await query.answer()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="این بخش در نسخه‌های بعدی فعال می‌شود.",
        reply_markup=get_back_button(),
    )
