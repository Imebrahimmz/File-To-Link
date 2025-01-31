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
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # From GitHub Secrets
API_UPLOAD_URL = "https://api.files.vc/upload"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

# Configure logging
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
    """Send welcome message"""
    await update.message.reply_text(
        "📤 Send me any file (document or photo) to upload!\n"
        "Max size: 50MB"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads to API"""
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
        
        # Send to API with enhanced logging
        response = requests.post(
            API_UPLOAD_URL,
            files=files,
            timeout=10  # Add timeout for reliability
        )
        
        # Log API response details
        logger.info(f"API Status Code: {response.status_code}")
        logger.info(f"API Response: {response.text}")

        # Handle API response
        if response.status_code in (200, 201):  # Accept both success codes
            await update.message.reply_text("✅ File uploaded successfully!")
            # Optional: Send file URL from response
            # result = response.json()
            # await update.message.reply_text(f"URL: {result['file_url']}")
        else:
            await update.message.reply_text(
                f"❌ API Error ({response.status_code}): {response.text[:200]}"
            )

    except Exception as e:
        logger.error(f"Critical Error: {str(e)}", exc_info=True)
        await update.message.reply_text(f"⚠️ System Error: {str(e)}")
        
    finally:
        if streamer:
            streamer.close()

if __name__ == "__main__":
    # Validate environment setup
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        exit(1)
        
    # Initialize and run bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    
    logger.info("Bot is starting...")
    app.run_polling()
