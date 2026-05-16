import os
import logging
import tempfile
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ADMIN_ID = 1234567890  # REPLACE WITH YOUR TELEGRAM USER ID

# Track users
def log_user(user_id, username):
    try:
        with open('/tmp/users.txt', 'a') as f:
            f.write(f"{user_id}|{username}\n")
    except:
        pass

SUPPORTED = [
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
    'youtube.com', 'youtu.be', 'youtube.com/shorts',
    'facebook.com', 'fb.watch', 'reddit.com', 'vm.tiktok.com'
]

PLATFORM_ICONS = {
    'Instagram': '📷',
    'TikTok': '🎵',
    'Twitter': '🐦',
    'YouTube': '▶️',
    'Facebook': '👍',
    'Reddit': '🤖',
}

PLATFORM_NAMES = {
    'instagram.com': 'Instagram', 'tiktok.com': 'TikTok', 'vm.tiktok.com': 'TikTok',
    'twitter.com': 'Twitter', 'x.com': 'Twitter', 'youtube.com': 'YouTube',
    'youtu.be': 'YouTube', 'youtube.com/shorts': 'YouTube', 'facebook.com': 'Facebook', 
    'fb.watch': 'Facebook', 'reddit.com': 'Reddit',
}

def get_platform(url):
    for d, n in PLATFORM_NAMES.items():
        if d in url:
            return n
    return "Video"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "no_username"
    log_user(user_id, username)
    
    await update.message.reply_text(
        "📥 *Video Downloader Bot*\n\n"
        "📷 Instagram • 🎵 TikTok • ▶️ YouTube\n"
        "👍 Facebook • 🐦 Twitter\n\n"
        "Send any video link! 🚀",
        parse_mode='Markdown'
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    
    try:
        with open('/tmp/users.txt', 'r') as f:
            users = set(line.split('|')[0] for line in f if line.strip())
        await update.message.reply_text(f"📊 Total users: {len(users)}")
    except:
        await update.message.reply_text("📊 Total users: 0")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "no_username"
    log_user(user_id, username)
    
    start_time = time.time()
    
    if not any(d in url for d in SUPPORTED):
        return
    
    status = await update.message.reply_text("⏳ Downloading...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {
            'outtmpl': f'{tmpdir}/video.%(ext)s',
            'format': 'best[filesize<48M]/best',
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            files = [f for f in os.listdir(tmpdir) if f.startswith('video')]
            if not files:
                raise Exception("No file")
            
            file_path = os.path.join(tmpdir, files[0])
            size = os.path.getsize(file_path) / 1024 / 1024
            
            if size > 49:
                await status.edit_text("❌ Too large (>50MB)")
                return
            
            platform = get_platform(url)
            icon = PLATFORM_ICONS.get(platform, '📱')
            elapsed = round(time.time() - start_time, 1)
            caption = f"{icon} *{platform}*\n⏱ {elapsed}s\n🤖 @Insta_Reel_Downloaderbot"
            
            await status.edit_text("✅ Sending...")
            
            with open(file_path, 'rb') as f:
                await update.message.reply_video(
                    f, 
                    caption=caption, 
                    parse_mode='Markdown',
                    read_timeout=60,
                    write_timeout=60
                )
            
            await status.delete()
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await status.edit_text("❌ Failed! Try another link.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()

