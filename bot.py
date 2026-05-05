import os
import yt_dlp
import tempfile
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

SUPPORTED = ['instagram.com', 'tiktok.com', 'twitter.com', 'x.com', 'youtu']

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not any(d in url for d in SUPPORTED):
        await update.message.reply_text(
            "Send me a link from Instagram, TikTok, or Twitter! 🎬"
        )
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
                await update.message.reply_video(
                    f,
                    caption="@YourBotUsername — Save reels without leaving Telegram 🔥"
                )

        except Exception as e:
            await msg.edit_text("❌ Couldn't grab this one. Try another link!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me any Instagram Reel, TikTok, or Twitter video link.\n"
        "I'll send it back as a video instantly — no ads, no apps!\n\n"
        "Just paste a link below 👇"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
