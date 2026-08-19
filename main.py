import asyncio
import sqlite3
import requests
import emoji  # Safe emoji rendering module
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

# 📦 Configuration Settings
try:
    from config import BOT_TOKEN, API_URL, VEHICLE_API_URL, BOT_NAME, ADMIN_ID, SUPPORT
except ImportError:
    BOT_TOKEN = "8996186987:AAFeF_T7tdfcHXRN-_0OwlDBmxCuKsqgpiM"
    API_URL = "http://subhxcosmo.in"
    VEHICLE_API_URL = "https://vercel.app"
    BOT_NAME = "TYAGI Number To Info Bot "
    ADMIN_ID = 5744767539
    SUPPORT = "@TYAGI8"

BOT_USERNAME_SIGNATURE = "@TYAGI_NUMBER_INFO_BOT"
ADMIN_ID = int(ADMIN_ID)
DB = "bot.db"

USER_STATES = {}

# ==========================================
# 🚀 KEEP-ALIVE SERVER
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
    count = cur.fetchone()
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
# BUTTON HANDLERS (DYNAMIC EMOJI PARSING FIXED)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    keyboard = [
        [InlineKeyboardButton(emoji.emojize(":clipboard: Menu"), callback_data="menu_info")],
        [
            InlineKeyboardButton(emoji.emojize(":magnifying_glass_tilted_left: Number Info"), callback_data="lookup_mode"),
            InlineKeyboardButton(emoji.emojize(":automobile: Vehicle Info"), callback_data="vehicle_mode")
        ],
        [
            InlineKeyboardButton(emoji.emojize(":bust_in_silhouette: Profile"), callback_data="profile"),
            InlineKeyboardButton(emoji.emojize(":star: Premium"), callback_data="premium")
        ],
        [
            InlineKeyboardButton(emoji.emojize(":scroll: History"), callback_data="history"),
            InlineKeyboardButton(emoji.emojize(":question_mark: Help"), callback_data="help")
        ],
        [
            InlineKeyboardButton(emoji.emojize(":information: About"), callback_data="about"),
            InlineKeyboardButton(emoji.emojize(":telephone_receiver: Contact"), callback_data="contact")
        ]
    ]

    welcome_msg = emoji.emojize(f":waving_hand: Welcome to {BOT_USERNAME_SIGNATURE}\n\nChoose an option below to continue.")
    await update.message.reply_text(welcome_msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "menu_info":
        await query.message.reply_text(emoji.emojize(":clipboard: Welcome to Menu! Aap niche diye gaye options ka use karke navigation kar sakte hain."))

    elif query.data == "lookup_mode":
        USER_STATES[user_id] = "NUMBER_SEARCH"
        await query.message.reply_text(emoji.emojize(":telephone_receiver: **Number Info Mode Active!**\nKripya 10-digit ka mobile number send karein."))

    elif query.data == "vehicle_mode":
        USER_STATES[user_id] = "VEHICLE_SEARCH"
        await query.message.reply_text(emoji.emojize(":automobile: **Vehicle Info Mode Active!**\nKripya apna gaadi ka number send karein (e.g. UK04AQ9000)."))

    elif query.data == "help":
        help_text = emoji.emojize(
            f":question_mark: Help & Guidelines\n\n"
            f":magnifying_glass_tilted_left: Search Kaise Karein: Pehle 'Number Info' ya 'Vehicle Info' button dabayein, phir details send karein.\n"
            f":star: Free Limit: Har standard account ko default search limit milti hai.\n\n"
            f"Premium subscription active karne ya kisi madad ke liye support par sampark karein: {SUPPORT}"
        )
        await query.message.reply_text(help_text)
        
    elif query.data == "contact":
        contact_text = emoji.emojize(
            f":telephone_receiver: Contact Support\n\n"
            f"Technical help ya premium activation ke liye yahan message karein:\n"
            f":loudspeaker: Support Desk: {SUPPORT}"
        )
        await query.message.reply_text(contact_text)
        
    elif query.data == "profile":
        u = get_user(user_id)
        premium_active = is_premium(user_id)
        premium_status = "FREE"
        days_left_text = ""
        
        if premium_active:
            premium_status = emoji.emojize("PREMIUM :gem_stone:")
            expiry_str = u
            if expiry_str == "Lifetime":
                days_left_text = emoji.emojize("\n:hourglass_not_done: Validity : Lifetime")
            elif expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    current_date = datetime.now().date()
                    remaining_days = (expiry_date - current_date).days
                    if remaining_days >= 0:
                        days_left_text = emoji.emojize(f"\n:hourglass_not_done: Days Left : {remaining_days} Days")
                    else:
                        premium_status = "FREE"
                except Exception:
                    pass

        profile_text = emoji.emojize(
            f":crown: Admin: {SUPPORT}\n\n"
            f":id: User ID :  {u}\n"
            f":bust_in_silhouette: Name : {u}\n"
            f":star: Plan : {premium_status}{days_left_text}\n"
            f":magnifying_glass_tilted_left: Searches : {u if u >= 0 else 0} Left\n"
            f":calendar: Joined : {u if u else 'First Join'}\n"
            f"_________________________\n\n"
            f":robot: Bot : {BOT_USERNAME_SIGNATURE}"
        )
        await query.message.reply_text(profile_text)
        
    elif query.data == "history":
        rows = history(user_id)
        if not rows:
            await query.message.reply_text(emoji.emojize(":scroll: Notice: Aapka koi purana search record nahi mila."))
            return
        text = emoji.emojize(":scroll: Your Search History:\n\n") + "\n".join([emoji.emojize(f":magnifying_glass_tilted_left: {n} — Date: {d}") for n, d in rows])
        await query.message.reply_text(text)
        
    elif query.data == "about":
        await query.message.reply_text(emoji.emojize(f":information: About Bot\n\n{BOT_USERNAME_SIGNATURE} ek high-speed live info retrieval portal system hai.\n:crown: Admin: {SUPPORT}"))

    elif query.data == "premium":
