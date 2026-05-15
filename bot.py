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

def get_ydl_opts(platform, tmpdir):
    """Platform-specific yt-dlp options for better reliability"""
    base_opts = {
        'outtmpl': f'{tmpdir}/video.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 60,  # Longer timeout for long videos
        'retries': 5,
        'fragment_retries': 5,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
    
    # Platform-specific formats
    if 'Instagram' in platform:
        base_opts['format'] = 'best[ext=mp4][filesize<48M]/best[filesize<48M]'
    elif 'Facebook' in platform:
        base_opts['format'] = 'best[ext=mp4][filesize<48M]/bestvideo[ext=mp4]+bestaudio/best'
    elif 'TikTok' in platform:
        base_opts['format'] = 'best[ext=mp4]'
    else:
        base_opts['format'] = 'best[ext=mp4][filesize<48M]/best[filesize<48M]/best'
    
    return base_opts

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
    status_msg = await update.message.reply_text("⏳ Processing your link...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = get_ydl_opts(platform, tmpdir)
        
        # Try download with retries
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    await status_msg.edit_text(f"⏳ Retrying... (Attempt {attempt + 1}/{max_attempts})")
                    time.sleep(2)  # Brief pause between retries
                else:
                    await status_msg.edit_text("⏳ Downloading your video... Please wait.")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if not info:
                        raise ValueError("No video info")
                
                # Find downloaded file
                files = [f for f in os.listdir(tmpdir) if f.startswith('video.')]
                if not files:
                    raise FileNotFoundError("Download completed but file not found")
                
                filename = os.path.join(tmpdir, files[0])
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                
                logger.info(f"Downloaded {platform} video: {file_size_mb:.1f}MB")

                if file_size_mb > 49:
                    await status_msg.edit_text(
                        "❌ Video is too large (>50MB).\n"
                        "Telegram bots can only send videos up to 50MB. Try a shorter video!"
                    )
                    return

                await status_msg.edit_text("✅ Video downloaded! Sending now...")
                elapsed = round(time.time() - start_time, 1)
                
                caption = f"📱 *{platform}*\n⏱ Time taken: {elapsed}s 🔥\n🤖 @InstaReelDownloaderBot"

                with open(filename, 'rb') as f:
                    await update.message.reply_video(
                        f, 
                        caption=caption, 
                        parse_mode='Markdown',
                        supports_streaming=True,
                        read_timeout=60,
                        write_timeout=60
                    )

                await status_msg.delete()
                return  # Success! Exit function
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                
                if attempt == max_attempts - 1:
                    # Final attempt failed
                    error_msg = "❌ Download failed after multiple attempts!\n\n"
                    
                    if 'age' in str(e).lower() or 'login' in str(e).lower():
                        error_msg += "This video is age-restricted or private.\n"
                    elif 'geo' in str(e).lower() or 'region' in str(e).lower():
                        error_msg += "This video is region-blocked.\n"
                    elif 'copyright' in str(e).lower():
                        error_msg += "This video has copyright restrictions.\n"
                    else:
                        error_msg += "The video may be:\n• Private or deleted\n• Age-restricted (18+)\n• Region-blocked\n• Too large\n\n"
                    
                    error_msg += "Try another link!"
                    await status_msg.edit_text(error_msg)
                # Otherwise continue to next attempt

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
