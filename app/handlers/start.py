# -*- coding: utf-8 -*-
"""هندلرهای ساده‌ی نمایش منو: /start (و بازگشت به خانه) و /help."""

from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.locales.fa import MSG
from app.keyboards.main import get_main_menu, get_back_button

logger = logging.getLogger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام خوش‌آمدگویی به همراه منوی اصلی را نمایش می‌دهد."""
    logger.info("START_HANDLER_CALLED")  # لاگ تست
    
    # بستن اسپینر دکمه در صورت کلیک روی کیبورد اینلاین
    if update.callback_query:
        await update.callback_query.answer()
    
    if update.effective_chat is None:
        return
        
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=MSG["welcome"],
        reply_markup=get_main_menu(),
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام راهنمای موقت را به همراه دکمه‌ی بازگشت نمایش می‌دهد."""
    if update.callback_query:
        await update.callback_query.answer()
        
    if update.effective_chat is None:
        return
        
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="راهنمای ربات به‌زودی اضافه می‌شود.",
        reply_markup=get_back_button(),
    )