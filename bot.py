import os
import time
import logging
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")

SUPPORTED = [
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
    'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch',
    'reddit.com', 'linkedin.com', 'pinterest.com', 'vm.tiktok.com'
]

PLATFORM_NAMES = {
    'instagram.com': 'Instagram', 'tiktok.com': 'TikTok', 'vm.tiktok.com': 'TikTok',
    'twitter.com': 'Twitter', 'x.com': 'Twitter', 'youtube.com': 'YouTube',
    'youtu.be': 'YouTube', 'facebook.com': 'Facebook', 'fb.watch': 'Facebook',
    'reddit.com': 'Reddit', 'linkedin.com': 'LinkedIn', 'pinterest.com': 'Pinterest',
}

def get_platform(url):
    for domain, name in PLATFORM_NAMES.items():
        if domain in url:
            return name
    return "Video"

async def check_membership(user_id, context):
    if not CHANNEL_USERNAME:
        return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.warning(f"Membership check failed: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 *Video Downloader Bot*\n\n"
        "Send a video link from:\n"
        "• Instagram • TikTok • YouTube\n"
        "• Facebook • Twitter/X\n"
        "• Reddit • Pinterest • LinkedIn\n\n"
        "Just paste the link! 🚀",
        parse_mode='Markdown'
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Start timer when user sends link
    start_time = time.time()
    
    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text(
            "❌ Send a valid link!\n\n"
            "Supported: Instagram, TikTok, YouTube, Facebook, Twitter, Reddit, LinkedIn, Pinterest"
        )
        return

    if CHANNEL_USERNAME:
        is_member = await check_membership(user_id, context)
        if not is_member:
            keyboard = [[InlineKeyboardButton(
                "📣 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
            )]]
            await update.message.reply_text(
                "❌ Join our channel first!\n🔔 Click below:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    platform = get_platform(url)
    
    # Validate link first before showing "downloading"
    status_msg = await update.message.reply_text("⏳ Checking link...")
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Invalid")
    except:
        await status_msg.edit_text(
            "❌ This link is invalid, private, or unsupported.\n"
            "Check the URL and try again!"
        )
        return
    
    # Now download
    await status_msg.edit_text("⏳ Downloading your video... Please wait.")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            'outtmpl': f'{tmpdir}/video.%(ext)s',
            'format': 'best[ext=mp4][filesize<48M]/best[filesize<48M]/best',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            files = [f for f in os.listdir(tmpdir) if f.startswith('video.')]
            if not files:
                raise FileNotFoundError("No file")
            
            filename = os.path.join(tmpdir, files[0])
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)

            if file_size_mb > 49:
                await status_msg.edit_text("❌ Video too large (>50MB). Try shorter!")
                return

            await status_msg.edit_text("✅ Video downloaded! Sending now...")

            # Total time from link sent to video sent
            elapsed = round(time.time() - start_time, 1)
            
            caption = f"📱 *{platform}*\n⏱ Time taken: {elapsed}s 🔥\n🤖 @InstaReelDownloaderBot"

            with open(filename, 'rb') as f:
                await update.message.reply_video(f, caption=caption, parse_mode='Markdown')

            await status_msg.delete()

        except Exception as e:
            logger.error(f"Error: {e}")
            await status_msg.edit_text(
                "❌ Download failed!\nVideo may be private, region-locked, or too large. Try another!"
            )

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set!")
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    logger.info("Bot started!")
    app.run_polling()

if __name__ == '__main__':
    main()
