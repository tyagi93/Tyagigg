import asyncio
import random
import yt_dlp
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ━━━━━━━━━━━━━━━━━━━━ CONFIGURATION ━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = "8996186987:AAFeF_T7tdfcHXRN-_0OwlDBmxCuKsqgpiM" 

TRENDING_HINT_POOL = [
    "Karan Aujla - Tauba Tauba",
    "Diljit Dosanjh - Born to Shine",
    "Shubh - King Shit",
    "Divine - Baazigar",
    "Badshah - Soulmate",
    "King - Tu Aake Dekhle",
    "Eminem - Houdini",
    "Haryanvi Mashup trending hip hop",
    "Krsna - Prarthana",
    "Yo Yo Honey Singh - Kalastar",
    "Sidhu Moose Wala - 295",
    "Travis Scott - Goosebumps",
    "The Weeknd - Blinding Lights"
]

# ━━━━━━━━━━━━━━━━━━━━ WEB SERVER FOR RENDER (KEEP ALIVE) ━━━━━━━━━━━━━━━━━━━━
web_app = Flask('')
@web_app.route('/')
def home(): return "Music Bot Live"

def run_web_server(): web_app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web_server, daemon=True).start()

# ━━━━━━━━━━━━━━━━━━━━ FREE AD-FREE MUSIC EXTRACTOR ━━━━━━━━━━━━━━━━━━━━
def search_and_download_audio(query):
    # Strict config to block internal saving and stream directly
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False) # Storage full nahi hoga, direct link uthayega
            if 'entries' in info and len(info['entries']) > 0:
                video_data = info['entries']
            else:
                video_data = info
            return {
                'url': video_data['url'],
                'title': video_data.get('title', 'Unknown Track'),
                'id': video_data.get('id', '')
            }
        except Exception as e:
            print(f"Extraction Error: {e}")
            return None

# ━━━━━━━━━━━━━━━━━━━━ HANDLERS ━━━━━━━━━━━━━━━━━━━━
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to TYAGI VIP Music Bot!**\n\n"
        "🎵 Hindi, Punjabi, Haryanvi aur English ke saare naye trending bangers bina kisi ads ke chalenge.\n"
        "✨ *Pehla random song load ho raha hai...*"
    )
    random_song = random.choice(TRENDING_HINT_POOL)
    await play_music_track(update.message, random_song)

async def play_music_track(message_obj, song_name):
    waiting_msg = await message_obj.reply_text(f"🔍 Fetching: `{song_name}`...")
    
    loop = asyncio.get_event_loop()
    track = await loop.run_in_executor(None, search_and_download_audio, song_name)
    
    if not track:
        await waiting_msg.edit_text("❌ Gaana nahi mila. Kripya naya naam try karein!")
        return
        
    keyboard = [
        [
            InlineKeyboardButton("▶️ Play", callback_data=f"play_{track['id']}"),
            InlineKeyboardButton("⏸️ Pause", callback_data="pause_track"),
            InlineKeyboardButton("⏹️ Stop", callback_data="stop_track")
        ],
        [
            InlineKeyboardButton("🔀 Next Random Hit", callback_data="next_random")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await waiting_msg.delete()
        await message_obj.reply_audio(
            audio=track['url'], # On-the-fly streaming direct URL se
            title=track['title'],
            performer="TYAGI Ad-Free Stream",
            reply_markup=reply_markup
        )
    except Exception as e:
        await message_obj.reply_text(f"⚠️ Playback Error: {e}")

async def handle_music_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "next_random":
        random_song = random.choice(TRENDING_HINT_POOL)
        await play_music_track(query.message, random_song)
    elif query.data == "pause_track":
        await query.message.reply_text("⏸️ **Music Paused!** Aap device player se control kar sakte hain.")
    elif query.data.startswith("play_"):
        await query.message.reply_text("▶️ **Playing / Resuming Track...**")
    elif query.data == "stop_track":
        try:
            await query.message.delete()
            await query.message.reply_text("⏹️ **Playback Stopped!** Naya gaana chalane ke liye naam type karein.")
        except Exception:
            await query.message.reply_text("⏹️ **Playback Stopped!**")

async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    
    banned_keywords = ["old", "1990", "1980", "1970", "kishore", "lata", "rafi", "vintage", "purane gane"]
    if any(word in user_input.lower() for word in banned_keywords):
        await update.message.reply_text("⚠️ **Notice:** Is bot par purane gaane allowed nahi hain! Kripya sirf naye aur energetic gaane hi search karein.")
        return
        
    await play_music_track(update.message, user_input)

if __name__ == "__main__":
    keep_alive()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_music_controls))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_music_search))
    
    print("TYAGI Control-Enabled Ad-Free Music Bot is Active!")
    app.run_polling()
  
