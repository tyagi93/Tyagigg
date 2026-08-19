import asyncio
import sqlite3
import requests
from datetime import datetime
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
from groq import Groq

# ==========================================
# CONFIGURATION SETTINGS
# ==========================================
BOT_TOKEN = "8996186987:AAFeF_T7tdfcHXRN-_0OwlDBmxCuKsqgpiM"
ADMIN_ID = 5744767539
BOT_NAME = "TYAGI Number To Info Bot"
SUPPORT = "@TYAGI8"
VEHICLE_API_URL = "https://vehicleinfo-byrack.vercel.app/api?search="
API_URL = "http://subhxcosmo.in"
BOT_USERNAME_SIGNATURE = "@TYAGI_NUMBER_INFO_BOT"

# Aapki Groq API Key yahan bilkul sahi setup hai
GROQ_API_KEY = "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"

try:
    ai_client = Groq(api_key=GROQ_API_KEY)
except Exception:
    ai_client = None

DB = "bot.db"
USER_STATES = {}

# Keep-Alive Engine for Render 24/7 online
web_app = Flask('')
@web_app.route('/')
def home(): return "Bot Server Live & Fully Checked!"
def run_web_server(): web_app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web_server, daemon=True).start()

# Database Setup
def connect(): return sqlite3.connect(DB)
def create_tables():
    con = connect()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, free_try INTEGER DEFAULT 3)")
    con.commit()
    con.close()

def add_user(user_id, username):
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    con.commit()
    con.close()

# ==========================================
# PANEL LAYOUT
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username)
    USER_STATES[user.id] = None 

    keyboard = [
        [InlineKeyboardButton("📋 Menu", callback_data="menu_info")],
        [
            InlineKeyboardButton("🔍 Number Info", callback_data="lookup_mode"), 
            InlineKeyboardButton("🚗 Vehicle Info", callback_data="vehicle_mode")
        ],
        [InlineKeyboardButton("🤖 AI Search", callback_data="ai_mode")], 
        [
            InlineKeyboardButton("👤 Profile", callback_data="profile"), 
            InlineKeyboardButton("⭐ Premium", callback_data="premium")
        ]
    ]
    await update.message.reply_text(
        f"👋 Welcome to {BOT_NAME}\n\nSearch karne ke liye niche diye gaye buttons mein se koi ek option select karein.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "lookup_mode":
        USER_STATES[user_id] = "NUMBER_SEARCH"
        await query.message.reply_text("📞 **Number Info Mode Active!**\nKripya 10-digit mobile number send karein.")
    elif query.data == "vehicle_mode":
        USER_STATES[user_id] = "VEHICLE_SEARCH"
        await query.message.reply_text("🚗 **Vehicle Info Mode Active!**\nKripya apna gaadi ka number send karein (e.g. UK04AQ9000).")
    elif query.data == "ai_mode":
        USER_STATES[user_id] = "AI_SEARCH"
        await query.message.reply_text("🤖 **AI Chat Search Mode Active!**\nAb aap mujhse koi bhi sawal pooch sakte hain.")
    elif query.data == "menu_info":
        await query.message.reply_text("📋 Menu configuration active.")
    elif query.data == "profile":
        await query.message.reply_text(f"👤 Profile Info\n\nUser ID: {user_id}\nBot: {BOT_USERNAME_SIGNATURE}")
    elif query.data == "premium":
        await query.message.reply_text(f"⭐ Premium Subscription ke liye message karein: {SUPPORT}")

# ==========================================
# TRAFFIC ROUTER
# ==========================================
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    state = USER_STATES.get(user_id)

    if not state:
        await update.message.reply_text("⚠️ **Notice:** Kripya pehle upar diye gaye buttons mein se **Number Info**, **Vehicle Info** ya **AI Search** select karein!")
        return

    # ---------------- TELEPHONE SEARCH ----------------
    if state == "NUMBER_SEARCH":
        if not user_input.isdigit() or len(user_input) != 10:
            await update.message.reply_text("❌ Error: Kripya sirf 10-digit mobile number enter karein.")
            return
        await update.message.reply_text("🔍 Status: Searching phone records...")
        try:
            full_target_url = f"{API_URL}&search={user_input}"
            r = requests.get(full_target_url, timeout=20)
            if r.status_code == 200:
                await update.message.reply_text(f"📊 Search Result:\n\n{r.text[:1500]}")
            else:
                await update.message.reply_text(f"⚠️ API Error (Status: {r.status_code})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Connection Error: {e}")
        USER_STATES[user_id] = None 
        return

    # ---------------- VEHICLE SEARCH ----------------
    elif state == "VEHICLE_SEARCH":
        clean_vehicle = user_input.replace(" ", "").upper()
        await update.message.reply_text(f"🚗 Status: Fetching details for vehicle `{clean_vehicle}`...")
        try:
            r = requests.get(VEHICLE_API_URL + clean_vehicle, timeout=20)
            if r.status_code == 200:
                await update.message.reply_text(f"📊 Vehicle Result:\n\n{r.text[:1500]}")
            else:
                await update.message.reply_text(f"⚠️ Vehicle API Error (Status: {r.status_code})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Connection Error: {e}")
        USER_STATES[user_id] = None 
        return

    # ---------------- FREE AI SEARCH (FIXED MODEL) ----------------
    elif state == "AI_SEARCH":
        if not ai_client:
            await update.message.reply_text("⚠️ AI System Error: Authorization failed.")
            return
            
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        try:
            # Model badal kar 'llama-3.1-8b-instant' kiya gaya hai jo 100% working hai
            chat_completion = ai_client.chat.completions.create(
                messages=[{"role": "user", "content": user_input}],
                model="llama-3.1-8b-instant",
            )
            reply = chat_completion.choices.message.content
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"⚠️ AI Server Error: {e}")
        USER_STATES[user_id] = None 
        return

if __name__ == "__main__":
    create_tables()
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.initialize())
    loop.run_until_complete(app.updater.start_polling(drop_pending_updates=True))
    loop.run_until_complete(app.start())
    loop.run_forever()
    
