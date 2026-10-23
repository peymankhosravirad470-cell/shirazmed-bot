import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler,
    filters, CallbackQueryHandler, Application
)
from telegram.error import TelegramError
from telegram.constants import ParseMode

# ==================== تنظیمات ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BOTGATE_BASE_URL = os.environ.get("BOTGATE_BASE_URL", "https://bot-gate.ru").strip().rstrip("/")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()
PORT = int(os.environ.get("PORT", 8080))

# ✅ بررسی توکن
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN تعریف نشده است.")
if ":" not in BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN نامعتبر است.")

# ==================== لاگینگ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ==================== URL ها ====================
SITE_URL = os.environ.get("SITE_URL", "https://shirazmedical.ir").rstrip("/")
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://ble.ir/shiraz_medical")

# ==================== کیبوردها ====================

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🏥 خدمات پزشکی", url=f"{SITE_URL}/#medical")],
        [InlineKeyboardButton("🏨 اقامتگاه‌ها", url=f"{SITE_URL}/#non-medical")],
        [InlineKeyboardButton("🏛️ گردشگری", url=f"{SITE_URL}/#tourism")],
        [InlineKeyboardButton("🩺 پیراپزشکی", url=f"{SITE_URL}/#paramedical")],
        [InlineKeyboardButton("🚨 اورژانس و پشتیبانی", url=f"{SITE_URL}/#emergency")],
        [InlineKeyboardButton("📢 کانال ما", url=CHANNEL_URL)],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")]
    ])


# ==================== توابع ربات ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"👤 کاربر {user.id} ({user.first_name}) → /start")
    
    text = (
        f"🌟 سلام {user.first_name or 'کاربر'} عزیز!\n\n"
        "به ربات **شیراز مدیکال** خوش آمدید.\n\n"
        "🏥 این ربات به سایت شیراز مدیکال متصل است و شما را به تمام "
        "خدمات پزشکی، اقامتی و گردشگری شیراز هدایت می‌کند.\n\n"
        "برای استفاده، از دکمه‌های زیر استفاده کنید:"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"👤 {update.effective_user.id} → /help")
    
    text = (
        "📖 **راهنمای ربات**\n\n"
        "🔹 /start — شروع مجدد و نمایش منو\n"
        "🔹 /help — نمایش این راهنما\n"
        "🔹 /about — درباره ربات و سایت\n\n"
        "🏥 **دسترسی به خدمات:**\n"
        "از دکمه‌های پیام /start استفاده کنید یا به سایت مراجعه کنید.\n\n"
        f"🌐 [سایت شیراز مدیکال]({SITE_URL})\n"
        f"📢 [کانال تلگرام]({CHANNEL_URL})"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"👤 {update.effective_user.id} → /about")
    
    text = (
        "🏥 **شیراز مدیکال**\n\n"
        "📌 **درباره ما:**\n"
        "شیراز مدیکال یک پلتفرم جامع برای دسترسی به خدمات پزشکی، "
        "اقامتی و گردشگری در شیراز است.\n\n"
        "🎯 **خدمات ما:**\n"
        "• بیمارستان‌ها و مراکز درمانی\n"
        "• بیمه‌های تحت پوشش\n"
        "• پیراپزشکی و خانه سالمندان\n"
        "• اقامتگاه‌ها و هتل‌ها\n"
        "• حمل و نقل و گردشگری\n"
        "• پشتیبانی و اورژانس\n\n"
        "🤝 **همراه شما در سفر سلامت**"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    
    if query.data == "back_to_menu":
        text = "🌟 به منوی اصلی بازگشتید. یکی از گزینه‌های زیر را انتخاب کنید:"
        try:
            await query.edit_message_text(
                text,
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        except TelegramError as e:
            logger.warning(f"ویرایش پیام ممکن نشد: {e}")
            await query.message.reply_text(
                text,
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ متوجه دستور شما نشدم.\n"
        "برای مشاهده راهنما، /help را بزنید یا /start کنید.",
        reply_markup=back_keyboard()
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"❌ خطا: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید یا /start را بزنید."
            )
        except TelegramError:
            pass


async def post_init(app: Application):
    """بعد از راه‌اندازی، دستورات پویا را ثبت کن"""
    try:
        from telegram import BotCommand
        await app.bot.set_my_commands([
            BotCommand("start", "شروع مجدد و نمایش منو"),
            BotCommand("help", "راهنمای ربات"),
            BotCommand("about", "درباره شیراز مدیکال"),
        ])
        logger.info("✅ دستورات ربات ثبت شدند.")
    except Exception as e:
        logger.warning(f"ثبت دستورات ممکن نشد: {e}")


# ==================== ساخت اپلیکیشن ====================

def build_application() -> Application:
    """ساخت اپلیکیشن با تنظیمات صحیح و امن"""
    builder = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .post_init(post_init)
    )
    
    # ✅ اگر Webhook است، از API تلگرام مستقیم استفاده کن
    if WEBHOOK_URL:
        logger.info(f"🌐 حالت Webhook — URL: {WEBHOOK_URL}")
    else:
        # ✅ اصلاح: آدرس BotGate باید شامل توکن ربات باشد
        builder = (
            builder
            .base_url(f"{BOTGATE_BASE_URL}/bot{BOT_TOKEN}")
            .base_file_url(f"{BOTGATE_BASE_URL}/file/bot{BOT_TOKEN}")
        )
        logger.info(f"📡 حالت Polling از طریق BotGate: {BOTGATE_BASE_URL}")
    
    return builder.build()


# ==================== Main ====================

def main():
    logger.info("🚀 راه‌اندازی ربات شیراز مدیکال...")
    
    app = build_application()
    
    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_error_handler(error_handler)
    
    logger.info("✅ ربات آماده است.")
    
    if WEBHOOK_URL:
        # ✅ Webhook امن
        logger.info(f"🌐 Webhook روی پورت {PORT}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=f"{WEBHOOK_URL}/webhook",
            secret_token=WEBHOOK_SECRET if WEBHOOK_SECRET else None,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
    else:
        # ✅ Polling
        logger.info("📡 Polling")
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )


if __name__ == "__main__":
    main() 