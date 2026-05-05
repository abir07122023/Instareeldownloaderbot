import os
import time
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@YourChannelUsername"  # Create a channel and put its username here

SUPPORTED = ['instagram.com', 'tiktok.com', 'twitter.com', 'x.com', 
             'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch',
             'reddit.com', 'linkedin.com', 'pinterest.com']

PLATFORM_NAMES = {
    'instagram.com': 'Instagram',
    'tiktok.com': 'TikTok',
    'twitter.com': 'Twitter',
    'x.com': 'Twitter',
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
    return "Unknown"

async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return True  # If check fails, allow anyway

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 *Download Videos Instantly!*\n\n"
        "Send a video link from *Instagram, TikTok, YouTube, Facebook, "
        "Twitter, Reddit, LinkedIn* or *Pinterest* and I'll fetch it for you. 🔗📲\n\n"
        "_Paste the URL below to start downloading:_",
        parse_mode='Markdown'
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id

    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text(
            "❌ Please send a valid video link from Instagram, TikTok, YouTube, "
            "Facebook, Twitter, Reddit, LinkedIn or Pinterest!"
        )
        return

    # Check channel membership
    is_member = await check_membership(user_id, context)
    if not is_member:
        keyboard = [[InlineKeyboardButton(
            f"📣 Join {CHANNEL_USERNAME}", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
        )]]
        await update.message.reply_text(
            f"❌ You must join our channel to use this bot!\n\n"
            f"🔔 Click the button below to join, then try again.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    platform = get_platform(url)
    start_time = time.time()

    # Status message
    status_msg = await update.message.reply_text(
        "⏳ Downloading your video... Please wait."
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            'outtmpl': f'{tmpdir}/video.%(ext)s',
            'format': 'best[filesize<45M]/best',
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            elapsed = round(time.time() - start_time, 1)

            await status_msg.edit_text("✅ Video downloaded successfully!\n📤 Trying to send your video...")

            with open(filename, 'rb') as f:
                caption = (
                    f"📷 {platform}\n"
                    f"Downloaded via @InstaReelDownloaderBot\n"
                    f"⏱ Time taken: {elapsed} seconds 🔥"
                )
                await update.message.reply_video(f, caption=caption)

            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text(
                "❌ Failed to download this video.\n"
                "The link may be private or unsupported. Try another link!"
            )

# Keep Render/Railway alive
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Running!")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("Bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()
