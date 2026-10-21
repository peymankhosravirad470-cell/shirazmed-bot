import logging
from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import settings
from app.handlers.start import start_handler, help_handler, select_language_handler, change_language_handler, back_to_main_handler
from app.handlers.callbacks import main_menu_callback

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def build_application() -> Application:
    builder = ApplicationBuilder().token(settings.active_token)
    builder.base_url("https://tapi.bale.ai/bot")
    builder.base_file_url("https://tapi.bale.ai/file/bot")
    application = builder.build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CallbackQueryHandler(select_language_handler, pattern=r"^lang_(fa|en|ar)$"))
    application.add_handler(CallbackQueryHandler(change_language_handler, pattern=r"^change_language$"))
    application.add_handler(CallbackQueryHandler(back_to_main_handler, pattern=r"^back_main$"))
    
    # اضافه شدن دکمه‌های زیرمنو به الگوی اصلی
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^(medical|non_medical|non_hospitals|non_hotels|non_motels|non_tourist_houses|non_transport|tourism|paramedical|elderly|package|hubs|taxi|insurance|translator|charter|deepseek|file|appointments|medication|emergency|channel|invite|rights)$"))

    logger.info("Application built successfully.")
    return application