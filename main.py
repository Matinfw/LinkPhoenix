import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp
import threading

# توکن ربات
TOKEN = "YOUR_BOT_TOKEN"

# پوشه موقت برای ذخیره فایل‌ها
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# تابع پاک کردن فایل بعد از ۲ ساعت
def delete_file_after_delay(filepath, delay=7200):
    time.sleep(delay)
    if os.path.exists(filepath):
        os.remove(filepath)

# منوی اصلی
def main_menu():
    keyboard = [
        [InlineKeyboardButton("ارسال فایل و دریافت لینک مستقیم 🔗", callback_data="file_to_link")],
        [InlineKeyboardButton("ارسال لینک و دریافت فایل از تلگرام 📤", callback_data="link_to_file")],
        [InlineKeyboardButton("دانلود از یوتیوب 🎥", callback_data="youtube_download")],
        [InlineKeyboardButton("حمایت مالی 💵", callback_data="donate")],
    ]
    return InlineKeyboardMarkup(keyboard)

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "خوش اومدی به LinkifyBot!\nاینجا می‌تونی فایل به لینک یا لینک به فایل تبدیل کنی و از یوتیوب دانلود کنی.\nگزینه مورد نظرتو انتخاب کن:",
        reply_markup=main_menu()
    )

# مدیریت انتخاب گزینه‌ها
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    messages = {
        "file_to_link": "فایل مورد نظرتو ارسال کن تا تبدیل به لینک‌ کنم!",
        "link_to_file": "لینک مورد نظرتو ارسال کن تا تبدیل به فایل کنم!",
        "youtube_download": "برای دانلود از یوتیوب، لینک ویدیوی مورد نظرتو بفرست!",
        "donate": "از حمایتت ممنونم! اگه دوست داری از ما حمایت کنی، می‌تونی از این لینک استفاده کنی: [لینک پرداخت]"
    }
    
    await query.edit_message_text(messages.get(query.data, "لطفاً گزینه درست رو انتخاب کن."))

# مدیریت پیام‌ها (فایل، لینک، یا لینک یوتیوب)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    # اگه فایل ارسال شده باشه
    if message.document or message.photo or message.video or message.audio:
        file = message.document or message.photo[-1] if message.photo else message.video or message.audio
        file_path = os.path.join(TEMP_DIR, file.file_id + ".tmp")
        
        # دانلود فایل از تلگرام
        new_file = await context.bot.get_file(file.file_id)
        await new_file.download_to_drive(file_path)
        
        # تولید لینک مستقیم (این لینک فقط نمونه است و باید به لینک واقعی سرورت تغییر کنه)
        file_url = f"https://example.com/{file.file_id}"
        await message.reply_text(f"لینک مستقیم: {file_url}")
        
        # پاک کردن فایل بعد از ۲ ساعت
        threading.Thread(target=delete_file_after_delay, args=(file_path,)).start()

    # اگه لینک ارسال شده باشه
    elif message.text and "http" in message.text:
        url = message.text
        
        # اگه لینک یوتیوب باشه
        if "youtube.com" in url or "youtu.be" in url:
            await message.reply_text("لطفاً کیفیت مورد نظرتو انتخاب کن:", reply_markup=youtube_quality_menu(url))
        else:
            # دانلود فایل از لینک معمولی
            file_path = os.path.join(TEMP_DIR, f"{chat_id}_{int(time.time())}.tmp")
            response = requests.get(url)
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            # ارسال فایل به تلگرام
            with open(file_path, "rb") as f:
                await message.reply_document(f)
            
            # پاک کردن فایل بعد از ۲ ساعت
            threading.Thread(target=delete_file_after_delay, args=(file_path,)).start()

# منوی انتخاب کیفیت یوتیوب
def youtube_quality_menu(url):
    keyboard = [
        [InlineKeyboardButton("1080p", callback_data=f"yt_1080p_{url}")],
        [InlineKeyboardButton("720p", callback_data=f"yt_720p_{url}")],
        [InlineKeyboardButton("480p", callback_data=f"yt_480p_{url}")],
        [InlineKeyboardButton("فقط صدا (MP3)", callback_data=f"yt_mp3_{url}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# دانلود از یوتیوب
async def youtube_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_", 2)
    quality = data[1]
    url = data[2]
    chat_id = query.message.chat_id

    ydl_opts = {
        "outtmpl": os.path.join(TEMP_DIR, f"{chat_id}_%(title)s.%(ext)s"),
        "format": "bestvideo+bestaudio" if quality in ["1080p", "720p", "480p"] else "bestaudio",
    }
    if quality == "mp3":
        ydl_opts["format"] = "bestaudio"
        ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    elif quality == "1080p":
        ydl_opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    elif quality == "720p":
        ydl_opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif quality == "480p":
        ydl_opts["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info).replace(".webm", ".mp4") if quality != "mp3" else ydl.prepare_filename(info).replace(".webm", ".mp3")

    # ارسال فایل به تلگرام
    with open(file_path, "rb") as f:
        await context.bot.send_document(chat_id, f)
    
    # پاک کردن فایل بعد از ۲ ساعت
    threading.Thread(target=delete_file_after_delay, args=(file_path,)).start()

# راه‌اندازی ربات
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button, pattern="^(file_to_link|link_to_file|youtube_download|donate)$"))
    application.add_handler(CallbackQueryHandler(youtube_download, pattern="^yt_"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()