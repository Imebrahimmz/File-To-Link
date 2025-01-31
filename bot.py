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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_UPLOAD_URL = "https://api.files.vc/upload"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    streamer = None
    try:
        # [Previous file handling code remains the same]
        
        # Upload to API
        files = {'file': (filename, streamer)}
        response = requests.post(API_UPLOAD_URL, files=files)
        
        # NEW: Detailed response logging
        logger.info("Full API Response:")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Headers: {response.headers}")
        logger.info(f"Raw Content: {response.content.decode()}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                logger.info(f"Parsed JSON: {response_data}")
                
                # Check different possible locations for hash
                file_hash = (
                    response_data.get('debug_info', {}).get('hash') or
                    response_data.get('hash') or
                    response_data.get('file_id')
                )
                
                if file_hash:
                    download_url = f"https://files.vc/d/dl?hash={file_hash}"
                    await update.message.reply_text(
                        f"✅ Upload successful!\n"
                        f"🔗 Download link: {download_url}"
                    )
                else:
                    await update.message.reply_text(
                        "✅ Upload successful!\n"
                        "⚠️ Could not retrieve download link from API response"
                    )
                    logger.error("Hash not found in response: %s", response_data)
                    
            except Exception as parse_error:
                await update.message.reply_text(
                    "✅ Upload successful!\n"
                    "⚠️ Failed to parse API response"
                )
                logger.error("JSON Parse Error: %s", parse_error)
        else:
            await update.message.reply_text(f"❌ API Error: {response.text}")

    except Exception as e:
        logger.error("Upload failed: %s", str(e))
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        
    finally:
        if streamer:
            streamer.close()

# [Rest of the code remains unchanged]
