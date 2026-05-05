import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
import tempfile
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPPORTED = ['instagram.com', 'tiktok.com', 'twitter.com', 'x.com', 'youtu']

# Keeps Render happy
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me any Instagram Reel, TikTok, or Twitter video link.\n"
        "I'll send it back instantly — no ads, no apps!\n\n"
        "Just paste a link 👇"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text("Send me a valid Instagram, TikTok or Twitter link! 🎬")
        return

    msg = await update.message.reply_text("⬇️ Downloading... hang on!")

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

            await msg.delete()
            with open(filename, 'rb') as f:
                await update.message.reply_video(f, caption="@InstaReelDownloaderBot 🔥")

        except Exception as e:
            await msg.edit_text("❌ Couldn't grab this one. Try another link!")

def main():
    # Start health server in background thread
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
