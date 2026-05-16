import os
import logging
import tempfile
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Railway will provide this

SUPPORTED = [
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
    'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch',
    'reddit.com', 'vm.tiktok.com'
]

PLATFORM_NAMES = {
    'instagram.com': 'Instagram', 'tiktok.com': 'TikTok', 'vm.tiktok.com': 'TikTok',
    'twitter.com': 'Twitter', 'x.com': 'Twitter', 'youtube.com': 'YouTube',
    'youtu.be': 'YouTube', 'facebook.com': 'Facebook', 'fb.watch': 'Facebook',
}

def get_platform(url):
    for d, n in PLATFORM_NAMES.items():
        if d in url:
            return n
    return "Video"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 *Video Downloader*\n\n"
        "Send: Instagram, TikTok, YouTube, Facebook, Twitter links\n\n"
        "Unlimited & Fast! 🚀",
        parse_mode='Markdown'
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text("❌ Invalid link!")
        return
    
    status = await update.message.reply_text("⏳ Downloading...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {
            'outtmpl': f'{tmpdir}/%(title).50s.%(ext)s',
            'format': 'best[filesize<48M]/best',
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            files = [f for f in os.listdir(tmpdir) if not f.startswith('.')]
            if not files:
                raise Exception("No file")
            
            file_path = os.path.join(tmpdir, files[0])
            size = os.path.getsize(file_path) / 1024 / 1024
            
            if size > 49:
                await status.edit_text("❌ Too large (>50MB)")
                return
            
            platform = get_platform(url)
            caption = f"📱 {platform}\n🤖 @InstaReelDownloaderBot"
            
            with open(file_path, 'rb') as f:
                await update.message.reply_video(f, caption=caption)
            
            await status.delete()
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await status.edit_text("❌ Failed! Video may be private or restricted.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    # Webhook mode (efficient!)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()
