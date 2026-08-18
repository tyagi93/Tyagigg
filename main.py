import asyncio
import sqlite3
import requests
from datetime import datetime, timedelta
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

# 📦 Yahan aapki config.py se saari settings import ho rahi hain
try:
    from config import BOT_TOKEN, API_URL, VEHICLE_API_URL, BOT_NAME, ADMIN_ID, SUPPORT
except ImportError:
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    API_URL = "YOUR_NUMBER_API_URL"
    VEHICLE_API_URL = "https://vehicleinfo-byrack.vercel.app/api?search="
    BOT_NAME = "TYAGI Number To Info Bot"
    ADMIN_ID = 5744767539
    SUPPORT = "@TYAGI8"

# Fixed Username according to user request
BOT_USERNAME_SIGNATURE = "@TYAGI_NUMBER_INFO_BOT"
ADMIN_ID = int(ADMIN_ID)
DB = "bot.db"

# User state track karne ke liye dictionary (ki user number search kar raha hai ya vehicle)
USER_STATES = {}

# ==========================================
# 🚀 KEEP-ALIVE SERVER (Render Keep-Alive Setup)
# ==========================================
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is alive and running 24/7!"

def run_web_server():
    web_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# DATABASE LOGIC
# ==========================================
def connect():
    return sqlite3.connect(DB)

def create_tables():
    con = connect()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        free_try INTEGER DEFAULT 3,
        premium INTEGER DEFAULT 0,
        premium_expiry TEXT,
        join_date TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        number TEXT,
        result TEXT,
        date TEXT
    )
    """)
    con.commit()
    con.close()

def add_user(user_id, username, first_name):
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)",
                (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d")))
    con.commit()
    con.close()

def get_user(user_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    return row

def reduce_try(user_id):
    con = connect()
    cur = con.cursor()
    cur.execute("UPDATE users SET free_try = free_try - 1 WHERE user_id=?", (user_id,))
    con.commit()
    con.close()

def add_history(user_id, number, result):
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT INTO history (user_id, number, result, date) VALUES (?, ?, ?, ?)",
                (user_id, number, result, datetime.now().strftime("%Y-%m-%d %H:%M")))
    con.commit()
    con.close()

def history(user_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT number, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def total_users():
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    con.close()
    return count

# ==========================================
# PREMIUM LOGIC
# ==========================================
def is_premium(user_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT premium, premium_expiry FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return False
    premium, expiry = row
    if premium == 0:
        return False
    if expiry == "Lifetime":
        return True
    return datetime.now().date() <= datetime.strptime(expiry, "%Y-%m-%d").date()

def activate_premium(user_id, days):
    con = connect()
    cur = con.cursor()
    if str(days).lower() == "lifetime":
        expiry = "Lifetime"
    else:
        expiry = (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d")
    cur.execute(
        "UPDATE users SET premium=?, premium_expiry=? WHERE user_id=?",
        (1, expiry, user_id)
    )
    con.commit()
    con.close()

# ==========================================
# BUTTON HANDLERS (CLEAN FORMATTING)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    keyboard = [
        [InlineKeyboardButton("📋 Menu", callback_data="menu_info")],
        [
            InlineKeyboardButton("🔍 Number Info", callback_data="lookup_mode"),
            InlineKeyboardButton("🚗 Vehicle Info", callback_data="vehicle_mode")
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("⭐ Premium", callback_data="premium")
        ],
        [
            InlineKeyboardButton("📜 History", callback_data="history"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ],
        [
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
            InlineKeyboardButton("📞 Contact", callback_data="contact")
        ]
    ]

    await update.message.reply_text(
        f"👋 Welcome to {BOT_USERNAME_SIGNATURE}\n\nChoose an option below to continue.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "menu_info":
        await query.message.reply_text("📋 Welcome to Menu! Aap niche diye gaye options ka use karke navigation kar sakte hain.")

    elif query.data == "lookup_mode":
        USER_STATES[user_id] = "NUMBER_SEARCH"
        await query.message.reply_text("📞 **Number Info Mode Active!**\nKripya 10-digit ka mobile number send karein.")

    elif query.data == "vehicle_mode":
        USER_STATES[user_id] = "VEHICLE_SEARCH"
        await query.message.reply_text("🚗 **Vehicle Info Mode Active!**\nKripya apna gaadi ka number send karein (e.g. UK04AQ9000).")

    elif query.data == "help":
        await query.message.reply_text(
            f"❓ Help & Guidelines\n\n"
            f"🔍 Search Kaise Karein: Pehle 'Number Info' ya 'Vehicle Info' button dabayein, phir details send karein.\n"
            f"⭐ Free Limit: Har standard account ko default search limit milti hai.\n\n"
            f"Premium subscription active karne ya kisi madad ke liye support par sampark karein: {SUPPORT}"
        )
    elif query.data == "contact":
        await query.message.reply_text(
            f"📞 Contact Support\n\n"
            f"Technical help ya premium activation ke liye yahan message karein:\n"
            f"📣 Support Desk: {SUPPORT}"
        )
    elif query.data == "profile":
        u = get_user(user_id)
        premium_active = is_premium(user_id)
        premium_status = "FREE"
        days_left_text = ""
        
        if premium_active:
            premium_status = "PREMIUM 💎"
            expiry_str = u[5] # premium_expiry column
            if expiry_str == "Lifetime":
                days_left_text = "\n⏳ Validity : Lifetime"
            elif expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    current_date = datetime.now().date()
                    remaining_days = (expiry_date - current_date).days
                    if remaining_days >= 0:
                        days_left_text = f"\n⏳ Days Left : {remaining_days} Days"
                    else:
                        premium_status = "FREE"
                except Exception:
                    pass

        # Added space after User ID according to request
        await query.message.reply_text(
            f"👑 Admin: {SUPPORT}\n\n"
            f"🆔 User ID :  {u[0]}\n"
            f"👤 Name : {u[2]}\n"
            f"⭐ Plan : {premium_status}{days_left_text}\n"
            f"🔍 Searches : {u[3] if u[3] >= 0 else 0} Left\n"
            f"📅 Joined : {u[6] if u[6] else 'First Join'}\n"
            f"_________________________\n\n"
            f"🤖 Bot : {BOT_USERNAME_SIGNATURE}"
        )
    elif query.data == "history":
        rows = history(user_id)
        if not rows:
            await query.message.reply_text("📜 Notice: Aapka koi purana search record nahi mila.")
            return
        text = "📜 Your Search History:\n\n" + "\n".join([f"🔍 {n} — Date: {d}" for n, d in rows])
        await query.message.reply_text(text)
        
    elif query.data == "about":
        await query.message.reply_text(f"ℹ️ About Bot\n\n{BOT_USERNAME_SIGNATURE} ek high-speed live info retrieval portal system hai.\n👑 Admin: {SUPPORT}")

    elif query.data == "premium":
        keyboard = [[InlineKeyboardButton("💳 Pay Now (QR Code)", callback_data="pay_now")]]
        await query.message.reply_text(
            "⭐ Premium Subscription Plans\n\n"
            f"◽️ 1 Day Pack ➡️ ₹20\n"
            f"◽️ 15 Days Access ➡️ ₹100\n"
            f"◽️ 30 Days Access ➡️ ₹150\n"
            f"◽️ Lifetime Access ➡️ ₹500\n\n"
            "Niche diye gaye button par click karke payment QR code dekhein.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "pay_now":
        QR_CODE_URL = "https://ibb.co" 
        caption_text = (
            f"💳 Payment Gateway\n\n"
            f"◽️ 1 Day Pack ➡️ ₹20\n"
            f"◽️ 15 Days Access ➡️ ₹100\n"
            f"◽️ 30 Days Access ➡️ ₹150\n"

