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

# API_URL ekdam sahi se verify kar liya hai taaki NameResolutionError na aaye
API_URL = "http://subhxcosmo.in"
BOT_USERNAME_SIGNATURE = "@TYAGI_NUMBER_INFO_BOT"

# Aapki Groq Free API Key yahan bilkul sahi setup hai
GROQ_API_KEY = "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"

try:
    ai_client = Groq(api_key=GROQ_API_KEY)
except Exception:
    ai_client = None

DB = "bot.db"
USER_STATES = {}

# Keep-Alive Engine for Render 24/7
web_app = Flask('')
@web_app.route('/')
def home(): return "Bot Server Live & Double Checked!"
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
# PANEL LAYOUT (WITH WORKING AI BUTTON)
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
        [InlineKeyboardButton("🤖 AI Search", callback_data="ai_mode")], # AI search button
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
        await query.message.reply_text("📞 Number Info Mode Active!\nKripya 10-digit mobile number send karein.")
    elif query.data == "vehicle_mode":
        USER_STATES[user_id] = "VEHICLE_SEARCH"
        await query.message.reply_text("🚗 Vehicle Info Mode Active!\nKripya apna gaadi ka number send karein (e.g. UK04AQ9000).")
    elif query.data == "ai_mode":
        USER_STATES[user_id] = "AI_SEARCH"
        await query.message.reply_text("🤖 AI Chat Search Mode Active!\nAb aap mujhse koi bhi sawal pooch sakte hain, main uska jwab dunga.")
    elif query.data == "menu_info":
        await query.message.reply_text("📋 Menu configuration active.")
