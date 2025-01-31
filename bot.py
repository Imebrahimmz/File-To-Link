import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
FILE_VC_UPLOAD_URL = "https://file.vc/upload"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text(
        "📤 To upload a large file, please use the following link:\n"
        f"{FILE_VC_UPLOAD_URL}\n\n"
        "After uploading, send me the download link."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logger.info(f"Received message: {text}")
    # Process the download link as needed
    await update.message.reply_text(f"✅ Received the download link: {text}")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_TOKEN!")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Keep the bot running
    app.run_polling(poll_interval=1.0)
