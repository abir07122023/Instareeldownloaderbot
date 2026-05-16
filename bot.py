import os
import time
import logging
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

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
    except:
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 *Video Downloader Bot*\n\n"
        "Send a video link from:\n"
        "• Instagram • TikTok • YouTube\n"
        "• Facebook • Twitter/X\n"
        "• Reddit • Pinterest • LinkedIn\n\n"
        "Unlimited & Free! 🚀",
        parse_mode='Markdown'
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    start_time = time.time()
    
    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text(
            "❌ Send a valid link!\n\n"
            "Supported: Instagram, TikTok, YouTube, Facebook, Twitter, Reddit"
        )
        return

    if CHANNEL_USERNAME:
        is_member = await check_membership(user_id, context)
        if not is_member:
            keyboard = [[InlineKeyboardButton(
                "📣 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
            )]]
            await update.message.reply_text(
                "❌ Join our channel first!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            platform = get_platform(url)
    status_msg = await update.message.reply_text("⏳ Processing...")
    
    ydl_opts = {
        'format': 'best[ext=mp4][filesize<48M]/best[filesize<48M]/best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        # Extract video info WITHOUT downloading
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # Get direct video URL
        video_url = info.get('url')
        title = info.get('title', 'Video')
        
        if not video_url:
            raise ValueError("No video URL found")
        
        await status_msg.edit_text("✅ Sending video...")
        elapsed = round(time.time() - start_time, 1)
        caption = f"📱 *{platform}*\n⏱️ {elapsed}s 🔥\n🤖 @InstaReelDownloaderBot"
        
        # Method 1: Try sending direct URL (FAST - no download)
        try:
            await update.message.reply_video(
                video_url,
                caption=caption,
                parse_mode='Markdown',
                read_timeout=30,
                write_timeout=30
            )
            await status_msg.delete()
            logger.info(f"✅ Direct URL worked for {platform}")
            return
            
        except Exception as url_error:
            logger.warning(f"Direct URL failed: {url_error}, trying download method...")
            
            # Method 2: Fallback - Download to server (SLOW but reliable)
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = f'{tmpdir}/video.%(ext)s'
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
                
                files = [f for f in os.listdir(tmpdir) if f.startswith('video.')]
                if not files:
                    raise FileNotFoundError("Download failed")
                
                filename = os.path.join(tmpdir, files[0])
                file_size = os.path.getsize(filename) / (1024 * 1024)
                
                if file_size > 49:
                    await status_msg.edit_text("❌ Video too large (>50MB)")
                    return
                
                with open(filename, 'rb') as f:
                    await update.message.reply_video(
                        f,
                        caption=caption,
                        parse_mode='Markdown',
                        read_timeout=60
                    )
                
                await status_msg.delete()
                logger.info(f"✅ Download method worked for {platform}")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(
            "❌ Failed!\n"
            "Video may be private, age-restricted, or region-blocked."
        )

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_health_server():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), HealthHandler).serve_forever()

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set!")
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    logger.info("Bot started!")
    app.run_polling()

if name == 'main':
    main()



