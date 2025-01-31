import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_UPLOAD_URL = "https://api.files.vc/upload"
DOWNLOAD_BASE_URL = "https://files.vc/d/dl?hash="
MAX_FILE_SIZE = 50 * 1024 * 1024

# Configure logging
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
    await update.message.reply_text(
        "📤 Send me any file to get a download link!\n"
        "Max size: 50MB"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    streamer = None
    try:
        # File type handling
        if update.message.document:
            file = update.message.document
            filename = file.file_name
        elif update.message.photo:
            file = update.message.photo[-1]
            filename = "photo.jpg"
        else:
            await update.message.reply_text("❌ Unsupported file type")
            return

        # Size check
        if file.file_size > MAX_FILE_SIZE:
            await update.message.reply_text("⚠️ File exceeds 50MB limit")
            return

        # Get file stream
        file_obj = await file.get_file()
        streamer = TelegramFileStreamer(file_obj.file_path)

        # Upload to API
        files = {'file': (filename, streamer)}
        response = requests.post(API_UPLOAD_URL, files=files)
        response.raise_for_status()  # Will trigger except for 4xx/5xx errors

        # Parse response
        result = response.json()
        if 'hash' not in result.get('debug_info', {}):
            raise ValueError("Missing hash in API response")
        
        # Build download link
        file_hash = result['debug_info']['hash']
        download_url = f"{DOWNLOAD_BASE_URL}{file_hash}"
        
        # Send success message with link
        await update.message.reply_text(
            f"✅ Upload successful!\n"
            f"🔗 Download link: {download_url}"
        )

    except requests.exceptions.HTTPError as e:
        error_msg = f"API Error ({e.response.status_code}): {e.response.text[:200]}"
        logger.error(error_msg)
        await update.message.reply_text(error_msg)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        
    finally:
        if streamer:
            streamer.close()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_TOKEN environment variable!")
        exit(1)
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    app.run_polling()
