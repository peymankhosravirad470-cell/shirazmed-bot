# -*- coding: utf-8 -*-
"""هندلرهای ساده‌ی نمایش منو: /start (و بازگشت به خانه) و /help. بدون منطق دیتابیس یا API."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.locales.fa import MSG, MSG_BTN
from app.keyboards.main import get_main_menu, get_back_button

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام خوش‌آمدگویی به همراه منوی اصلی را نمایش می‌دهد (برای /start و callback main:home)."""
    # TODO: این لاگ تشخیصی موقتی است — بعد از رفع مشکل حذف شود.
    logger.info("start_handler فراخوانی شد | update: %s", update.to_dict())

    if update.effective_chat is None:
        logger.warning("start_handler: effective_chat خالی است، پیام ارسال نشد.")
        return

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MSG["welcome"],
            reply_markup=get_main_menu(),
        )
        logger.info("start_handler: پیام با موفقیت به chat_id=%s ارسال شد.", update.effective_chat.id)
    except Exception as exc:  # noqa: BLE001 — لاگ تشخیصی موقت، نباید برنامه کرش کند
        logger.error("start_handler: خطا در ارسال پیام: %s", exc)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام راهنمای موقت را به همراه دکمه‌ی بازگشت نمایش می‌دهد."""
    if update.effective_chat is None:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="راهنمای ربات به‌زودی اضافه می‌شود.",
        reply_markup=get_back_button(),
    )
