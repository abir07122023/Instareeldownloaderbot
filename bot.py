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
ADMIN_ID = 6294267891
LOG_CHANNEL_ID = -1003744819617

def log_user(user_id, username):
    try:
        with open('/tmp/users.txt', 'a') as f:
            f.write(f"{user_id}|{username}\n")
    except:
        pass

async def log_to_channel(context, user_message, bot_message):
    try:
        await user_message.forward(LOG_CHANNEL_ID)
        await bot_message.forward(LOG_CHANNEL_ID)
    except:
        pass

SUPPORTED = [
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
    'youtube.com', 'youtu.be', 'youtube.com/shorts',
    'facebook.com', 'fb.watch', 'reddit.com', 'vm.tiktok.com'
]

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
        "Send links from:\n"
        "📷 Instagram • 🎵 TikTok • ▶️ YouTube\n"
        "👍 Facebook • 🐦 Twitter\n\n"
        "Just paste a link! 🚀",
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
    platform = get_platform(url)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        if 'YouTube' in platform:
            format_str = 'best[filesize<48M]/bestvideo[height<=720][filesize<48M]+bestaudio/best[height<=480]'
        else:
            format_str = 'best[filesize<48M]/best'
        
        opts = {
            'outtmpl': f'{tmpdir}/video.%(ext)s',
            'format': format_str,
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            files = [f for f in os.listdir(tmpdir) if f.startswith('video')]
            if not files:
                raise Exception("No file")
            
            file_path = os.path.join(tmpdir, files[0])
            size_mb = os.path.getsize(file_path) / 1024 / 1024
            
            elapsed = round(time.time() - start_time, 1)
            caption = f"📱 *{platform}*\n⏱️ {elapsed}s 🔥\n🤖 @Insta_Reel_Downloaderbot"
            
            await status.edit_text("✅ Sending...")
            

with open(file_path, 'rb') as f:
    if size_mb < 49:
        sent_msg = await update.message.reply_video(
            f,
            caption=caption,
            parse_mode='Markdown',
            read_timeout=120,
            write_timeout=120
        )

    elif size_mb < 2000:
        sent_msg = await update.message.reply_document(
            f,
            caption=caption + "\n📦 (Sent as file)",
            parse_mode='Markdown',
            read_timeout=180,
            write_timeout=180
        )

    else:
        await status.edit_text("❌ Too large (>2GB)")
        return

await log_to_channel(context, update.message, sent_msg)

try:
    await status.delete()

except:
    pass
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await status.edit_text("❌ Failed! Try another link.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    logger.info("Bot starting with polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()


