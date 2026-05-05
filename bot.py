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

# Set to your channel username (e.g. "@mychannel") via Railway env var, or leave empty to disable
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")

SUPPORTED = [
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
    'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch',
    'reddit.com', 'linkedin.com', 'pinterest.com', 'vm.tiktok.com'
]

PLATFORM_NAMES = {
    'instagram.com': 'Instagram',
    'tiktok.com': 'TikTok',
    'vm.tiktok.com': 'TikTok',
    'twitter.com': 'Twitter',
    'x.com': 'Twitter/X',
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'facebook.com': 'Facebook',
    'fb.watch': 'Facebook',
    'reddit.com': 'Reddit',
    'linkedin.com': 'LinkedIn',
    'pinterest.com': 'Pinterest',
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
        return True  # allow if check fails

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f"/start from user {user.id} ({user.username})")
    await update.message.reply_text(
        "📥 *Video Downloader Bot*\n\n"
        "Send me a video link from:\n"
        "• Instagram Reels\n"
        "• TikTok\n"
        "• YouTube Shorts\n"
        "• Facebook Reels\n"
        "• Twitter/X\n"
        "• Reddit, Pinterest, LinkedIn\n\n"
        "Just paste the link and I'll download it for you! 🚀",
        parse_mode='Markdown'
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    logger.info(f"Received URL from {user_id}: {url}")

    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text(
            "❌ Please send a valid video link!\n\n"
            "Supported: Instagram, TikTok, YouTube, Facebook, Twitter/X, Reddit, LinkedIn, Pinterest"
        )
        return

    if CHANNEL_USERNAME:
        is_member = await check_membership(user_id, context)
        if not is_member:
            keyboard = [[InlineKeyboardButton(
                "📣 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
            )]]
            await update.message.reply_text(
                "❌ You must join our channel to use this bot!\n\n"
                "🔔 Click below to join, then try again.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    platform = get_platform(url)
    start_time = time.time()
    status_msg = await update.message.reply_text("⏳ Downloading... Please wait.")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, 'video.%(ext)s')

        ydl_opts = {
            'outtmpl': output_template,
            'format': 'bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<45M]/best[filesize<45M]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            # Find the downloaded file
            filename = None
            for f in os.listdir(tmpdir):
                if f.startswith('video.'):
                    filename = os.path.join(tmpdir, f)
                    break

            if not filename or not os.path.exists(filename):
                raise FileNotFoundError("Downloaded file not found")

            file_size_mb = os.path.getsize(filename) / (1024 * 1024)
            elapsed = round(time.time() - start_time, 1)
            logger.info(f"Downloaded {filename} ({file_size_mb:.1f}MB) in {elapsed}s")

            if file_size_mb > 49:
                await status_msg.edit_text(
                    "❌ Video is too large to send via Telegram (>50MB).\nTry a shorter video!"
                )
                return

            await status_msg.edit_text("✅ Downloaded! Sending now...")

            caption = (
                f"📱 *{platform}*\n"
                f"⏱ Downloaded in {elapsed}s\n"
                f"🤖 @InstaReelDownloaderBot"
            )

            with open(filename, 'rb') as f:
                await update.message.reply_video(
                    f,
                    caption=caption,
                    parse_mode='Markdown',
                    supports_streaming=True
                )

            await status_msg.delete()

        except FileNotFoundError as e:
            logger.error(f"File error: {e}")
            await status_msg.edit_text(
                "❌ Download failed — the video could not be saved.\n"
                "The link may be private or region-restricted. Try another link!"
            )
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            await status_msg.edit_text(
                "❌ Failed to download this video.\n"
                "The link may be private, expired, or unsupported. Try another link!"
            )

# Health check server — Railway requires a port to be bound
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health server on port {port}")
    server.serve_forever()

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
