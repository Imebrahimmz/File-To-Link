import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_UPLOAD_URL = "https://api.files.vc/upload"
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramFileStreamer:
    def __init__(self, file_url):
        self.response = requests.get(file_url, stream=True)
        self.response.raise_for_status()
        self.iterator = self.response.iter_content(chunk_size=8192)

    def read(self, chunk_size=None):
        try:
            return next(self.iterator)
        except StopIteration:
            return b''

    def close(self):
        self.response.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text(
        "📤 Send me any file to get a download link!\n"
        "Max size: 2GB"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    streamer = None
    try:
        if update.message.document:
            file = update.message.document
            filename = file.file_name
        elif update.message.photo:
            file = update.message.photo[-1]
            filename = "photo.jpg"
        else:
            await update.message.reply_text("❌ Unsupported file type")
            return

        if file.file_size > MAX_FILE_SIZE:
            await update.message.reply_text("⚠️ File exceeds 2GB limit")
            return

        file_obj = await file.get_file()
        streamer = TelegramFileStreamer(file_obj.file_path)

        files = {'file': (filename, streamer)}
        response = requests.post(API_UPLOAD_URL, files=files)

        logger.info(f"API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            result = response.json()
            download_url = result.get("file_url")
            if download_url:
                await update.message.reply_text(
                    f"✅ Upload successful!\n"
                    f"🔗 Download link: {download_url}"
                )
            else:
                await update.message.reply_text(f"❌ API Error: {result.get('message', 'Unknown error')}")
        else:
            await update.message.reply_text(f"❌ API Error: {response.text}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
    finally:
        if streamer:
            streamer.close()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_TOKEN!")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))

    # Keep the bot running
    app.run_polling(poll_interval=1.0)
