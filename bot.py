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
TELEGRAM_TOKEN = "7820471600:AAHz_4zXFykyefwA8BiX9fYxIWe24AeePxQ"  # Your token
API_UPLOAD_URL = "https://api.files.vc/upload"  # Your API endpoint
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramFileStreamer:
    """Stream files directly from Telegram's servers"""
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
    """Welcome message handler"""
    await update.message.reply_text(
        "📤 Send me any file (document or photo) to upload!\n"
        "Max size: 50MB"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    streamer = None
    try:
        # Get file metadata
        if update.message.document:
            file = update.message.document
            filename = file.file_name
        elif update.message.photo:
            file = update.message.photo[-1]
            filename = "photo.jpg"
        else:
            await update.message.reply_text("❌ Unsupported file type")
            return

        # Check file size
        if file.file_size > MAX_FILE_SIZE:
            await update.message.reply_text("⚠️ File exceeds 50MB limit")
            return

        # Get direct file URL
        file_obj = await file.get_file()
        streamer = TelegramFileStreamer(file_obj.file_path)

        # Prepare upload
        files = {'file': (filename, streamer)}
        
        # Add custom headers if needed
        headers = {
            # "Authorization": "Bearer YOUR_API_KEY"  # Uncomment if needed
        }
        
        # Upload to API
        response = requests.post(
            API_UPLOAD_URL,
            files=files,
            headers=headers
        )
        
        if response.status_code == 200:
            await update.message.reply_text("✅ Upload successful!")
        else:
            await update.message.reply_text(f"❌ API Error: {response.text}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        
    finally:
        if streamer:
            streamer.close()

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    app.run_polling()