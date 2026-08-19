import asyncio
import sqlite3
import requests
import json
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

# ━━━━━━━━━━━━━━━━━━━━ CONFIG IMPORT ━━━━━━━━━━━━━━━━━━━━
import config

BOT_TOKEN = config.BOT_TOKEN
ADMIN_ID = int(config.ADMIN_ID)
BOT_NAME = config.BOT_NAME
SUPPORT = config.SUPPORT
VEHICLE_API_URL = config.VEHICLE_API_URL
API_URL = config.API_URL

BOT_USERNAME_SIGNATURE = "@TYAGI_NUMBER_INFO_BOT"
GROQ_API_KEY = "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"

try:
    ai_client = Groq(api_key=GROQ_API_KEY)
    AI_MODEL = "llama3-70b-8192" 
except Exception:
    ai_client = None
    AI_MODEL = None

DB = "bot.db"
USER_STATES = {}

# ━━━━━━━━━━━━━━━━━━━━ WEB SERVER FOR RENDER ━━━━━━━━━━━━━━━━━━━━
web_app = Flask('')
@web_app.route('/')
def home(): return "Live"

def run_web_server(): web_app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web_server, daemon=True).start()

# ━━━━━━━━━━━━━━━━━━━━ DATABASE SETUP ━━━━━━━━━━━━━━━━━━━━
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

# ━━━━━━━━━━━━━━━━━━━━ HANDLERS ━━━━━━━━━━━━━━━━━━━━
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username)
    USER_STATES[user.id] = None 
    
    keyboard = [
        [InlineKeyboardButton("📋 Menu", callback_data="menu_info")],
        [InlineKeyboardButton("🔍 Number Info", callback_data="lookup_mode"), InlineKeyboardButton("🚗 Vehicle Info", callback_data="vehicle_mode")],
        [InlineKeyboardButton("🤖 AI Search", callback_data="ai_mode")], 
        [InlineKeyboardButton("👤 Profile", callback_data="profile"), InlineKeyboardButton("⭐ Premium", callback_data="premium")]
    ]
    await update.message.reply_text(
        f"👋 Welcome to {BOT_NAME}\n\nSearch karne ke liye niche diye gaye buttons mein se koi ek option select karein:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "lookup_mode":
        USER_STATES[user_id] = "NUMBER_SEARCH"
        await query.message.reply_text("📞 **Number Info Mode Active!**\nSend 10-digit number.")
    elif query.data == "vehicle_mode":
        USER_STATES[user_id] = "VEHICLE_SEARCH"
        await query.message.reply_text("🚗 **Vehicle Info Mode Active!**\nKripya apna gaadi ka number send karein (e.g. UK04AQ9000).")
    elif query.data == "ai_mode":
        USER_STATES[user_id] = "AI_SEARCH"
        await query.message.reply_text("🤖 **AI Chat Search Mode Active!**\nAb aap mujhse koi bhi sawal pooch sakte hain.")
    elif query.data == "menu_info":
        await query.message.reply_text("📋 Menu active.")
    elif query.data == "profile":
        await query.message.reply_text(f"👤 User ID: {user_id}\nBot: {BOT_USERNAME_SIGNATURE}")
    elif query.data == "premium":
        await query.message.reply_text(f"⭐ Premium Support: {SUPPORT}")

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    state = USER_STATES.get(user_id)

    if not state:
        await update.message.reply_text("⚠️ **Notice:** Kripya pehle upar diye gaye buttons mein se select karein!")
        return

    # 1. NUMBER SEARCH
    if state == "NUMBER_SEARCH":
        if not user_input.isdigit() or len(user_input) != 10:
            await update.message.reply_text("❌ Error: Enter 10-digit mobile number.")
            return
        await update.message.reply_text("🔍 Status: Searching phone records...")
        try:
            r = requests.get(f"{API_URL}{user_input}", timeout=20)
            if r.status_code == 200:
                clean_text = r.text.replace("@YeuIin", SUPPORT).replace("@kihoerack", BOT_USERNAME_SIGNATURE)
                await update.message.reply_text(f"📊 Search Result:\n\n{clean_text[:1500]}")
            else:
                await update.message.reply_text(f"⚠️ API Error ({r.status_code})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        USER_STATES[user_id] = None 
        return

    # 2. VEHICLE SEARCH
    elif state == "VEHICLE_SEARCH":
        clean_vehicle = user_input.replace(" ", "").upper()
        await update.message.reply_text(f"🚗 Status: Fetching details for vehicle `{clean_vehicle}`...")
        try:
            target_url = f"{VEHICLE_API_URL}{clean_vehicle}"
            r = requests.get(target_url, timeout=20)
            if r.status_code == 200:
                try:
                    raw_data = r.json()
                    response_obj = raw_data.get("response", {})
                    
                    if response_obj and isinstance(response_obj, dict):
                        rto_data = response_obj.get("rtoData", {})
                        
                        report = (
                            f"📋 **Vehicle Information Report**\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 **Owner**: {response_obj.get('owner', 'N/A')}\n"
                            f"🔢 **Reg No**: {raw_data.get('regNo', clean_vehicle)}\n"
                            f"📅 **Reg Date**: {response_obj.get('regDate', 'N/A')}\n"
                            f"🚘 **Class**: {response_obj.get('vehicleClass', 'N/A')}\n"
                            f"🏭 **Manufacturer**: {response_obj.get('manufacturer') or 'N/A'}\n"
                            f"⛽ **Fuel Type**: {response_obj.get('fuelType') or 'N/A'}\n"
                            f"⚙️ **Engine No**: {response_obj.get('engine', 'N/A')}\n"
                            f"🛠️ **Chassis No**: {response_obj.get('chassis', 'N/A')}\n"
                            f"🏢 **Authority**: {response_obj.get('regAuthority', 'N/A')}\n"
                            f"📍 **RTO**: {rto_data.get('rtoName', 'N/A')} ({rto_data.get('statename', 'N/A')})\n"
                            f"🛡️ **Insurance**: {response_obj.get('insuranceCompanyName', 'N/A')}\n"
                            f"📆 **Insurance Upto**: {response_obj.get('insuranceUpto', 'N/A')}\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"👑 **Admin**: {SUPPORT}\n"
                            f"🤖 **Owner / Bot**: {BOT_USERNAME_SIGNATURE}"
                        )
                        await update.message.reply_text(report)
                    else:
                        clean_fb = r.text.replace("@YeuIin", SUPPORT).replace("@kihoerack", BOT_USERNAME_SIGNATURE)
                        await update.message.reply_text(f"📊 Vehicle Result:\n\n{clean_fb[:1500]}")
                except Exception:
                    clean_fb = r.text.replace("@YeuIin", SUPPORT).replace("@kihoerack", BOT_USERNAME_SIGNATURE)
                    await update.message.reply_text(f"📊 Vehicle Result:\n\n{clean_fb[:1500]}")
            else:
                await update.message.reply_text(f"⚠️ API Error ({r.status_code})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        USER_STATES[user_id] = None 
        return

    # 3. AI SEARCH 
    elif state == "AI_SEARCH":
        if not ai_client:
            await update.message.reply_text("⚠️ AI Client Configuration Error!")
            return
        await update.message.reply_text("🤖 Typing...")
        try:
            chat_completion = ai_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Keep responses sweet, clean, and useful."},
                    {"role": "user", "content": user_input}
                ],
                model=AI_MODEL,
                timeout=25
            )
            ai_response = chat_completion.choices.message.content
            await update.message.reply_text(ai_response)
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
    
    print("Bot is up and running successfully!")
    app.run_polling()

