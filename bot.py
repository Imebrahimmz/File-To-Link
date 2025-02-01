import os
import logging
import requests
from telegram import Update, File
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_UPLOAD_URL = "https://api.files.vc/upload"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramFileStreamer:
    def __init__(self, file_path: str):
        self.response = requests.get(file_path, stream=True)
        self.response.raise_for_status()
        self.iterator = self.response.iter_content(chunk_size=8192)
        self.total_size = int(self.response.headers.get('content-length', 0))
        self.uploaded_size = 0

    def read(self, chunk_size=None):
        try:
            chunk = next(self.iterator)
            self.uploaded_size += len(chunk)
            logger.info(f"Uploaded {self.uploaded_size} of {self.total_size} bytes")
            return chunk
        except StopIteration:
            return b''

    def close(self):
        self.response.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text(
        "📤 Send me any file to get a download link!"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.document:
            file = update.message.document
            filename = file.file_name
            file_id = file.file_id
        elif update.message.video:
            file = update.message.video
            filename = f"{file.file_name}.mp4"
            file_id = file.file_id
        elif update.message.photo:
            file = update.message.photo[-1]
            filename = f"{update.message.caption or 'photo'}.jpg"
            file_id = file.file_id
        else:
            await update.message.reply_text("❌ Unsupported file type. Please send a document, video, or photo.")
            return

        logger.info(f"File name: {filename}")
        logger.info(f"File ID: {file_id}")

        # Store the file_id for later use
        context.user_data['file_id'] = file_id

        # Use the file_id to get the file path
        file_obj = await context.bot.get_file(file_id)
        logger.info(f"File path: {file_obj.file_path}")

        streamer = TelegramFileStreamer(file_obj.file_path)

        files = {'file': (filename, streamer)}
        response = requests.post(API_UPLOAD_URL, files=files)

        logger.info(f"API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            result = response.json()
            if "file_url" in result:
                download_url = result["file_url"]
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

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_TOKEN!")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, handle_file))

    # Keep the bot running
    app.run_polling(poll_interval=1.0)
