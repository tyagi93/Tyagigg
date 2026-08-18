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

# 📦 Config load logic
try:
    import config
    BOT_TOKEN = config.BOT_TOKEN
    API_URL = config.API_URL
    VEHICLE_API_URL = config.VEHICLE_API_URL
    BOT_NAME = config.BOT_NAME
    ADMIN_ID = config.ADMIN_ID
    SUPPORT = config.SUPPORT
except Exception:
    BOT_TOKEN = "8996186987:AAFeF_T7tdfcHXRN-_0OwlDBmxCuKsqgpiM"
    API_URL = "http://subhxcosmo.in"
    VEHICLE_API_URL = "https://vehicleinfo-byrack.vercel.app/api?search="
    BOT_NAME = "TYAGI Number To Info Bot "
    ADMIN_ID = 5744767539
    SUPPORT = "@TYAGI8"

BOT_USERNAME_SIGNATURE = "@TYAGI_NUMBER_INFO_BOT"
ADMIN_ID = int(ADMIN_ID)
DB = "bot.db"
USER_STATES = {}

# Keep-Alive Server
web_app = Flask('')
@web_app.route('/')
def home(): return "Bot is running!"
def run_web_server(): web_app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_web_server, daemon=True)
    t.start()

# Database Setup
def connect(): return sqlite3.connect(DB)
def create_tables():
    con = connect()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, free_try INTEGER DEFAULT 3, premium INTEGER DEFAULT 0, premium_expiry TEXT, join_date TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, number TEXT, result TEXT, date TEXT)")
    con.commit()
    con.close()

def add_user(user_id, username, first_name):
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)", (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d")))
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
    cur.execute("INSERT INTO history (user_id, number, result, date) VALUES (?, ?, ?, ?)", (user_id, number, result, datetime.now().strftime("%Y-%m-%d %H:%M")))
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
    return count[0] if count else 0

def is_premium(user_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT premium, premium_expiry FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if not row or row[0] == 0: return False
    if row[1] == "Lifetime": return True
    return datetime.now().date() <= datetime.strptime(row[1], "%Y-%m-%d").date()

def activate_premium(user_id, days):
    con = connect()
    cur = con.cursor()
    expiry = "Lifetime" if str(days).lower() == "lifetime" else (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d")
    cur.execute("UPDATE users SET premium=?, premium_expiry=? WHERE user_id=?", (1, expiry, user_id))
    con.commit()
    con.close()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    keyboard = [
        [InlineKeyboardButton("📋 Menu", callback_data="menu_info")],
        [InlineKeyboardButton("🔍 Number Info", callback_data="lookup_mode"), InlineKeyboardButton("🚗 Vehicle Info", callback_data="vehicle_mode")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile"), InlineKeyboardButton("⭐ Premium", callback_data="premium")],
        [InlineKeyboardButton("📜 History", callback_data="history"), InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"), InlineKeyboardButton("📞 Contact", callback_data="contact")]
    ]
    await update.message.reply_text(f"👋 Welcome to {BOT_USERNAME_SIGNATURE}\n\nChoose an option below to continue.", reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "menu_info":
        await query.message.reply_text("📋 Welcome to Menu!")
    elif query.data == "lookup_mode":
        USER_STATES[user_id] = "NUMBER_SEARCH"
        await query.message.reply_text("📞 **Number Info Mode Active!**\nKripya 10-digit ka mobile number send karein.")
    elif query.data == "vehicle_mode":
        USER_STATES[user_id] = "VEHICLE_SEARCH"
        await query.message.reply_text("🚗 **Vehicle Info Mode Active!**\nKripya apna gaadi ka number send karein (e.g. UK04AQ9000).")
    elif query.data == "help":
        await query.message.reply_text(f"❓ Guidelines:\nPremium active karne ke liye support par sampark karein: {SUPPORT}")
    elif query.data == "contact":
        await query.message.reply_text(f"📞 Contact Support: {SUPPORT}")
    elif query.data == "profile":
        u = get_user(user_id)
        p_status = "PREMIUM 💎" if is_premium(user_id) else "FREE"
        await query.message.reply_text(f"👑 Admin: {SUPPORT}\n🆔 User ID: {user_id}\n⭐ Plan: {p_status}\n🤖 Bot: {BOT_USERNAME_SIGNATURE}")
    elif query.data == "history":
        rows = history(user_id)
        if not rows: await query.message.reply_text("📜 Notice: History empty."); return
        await query.message.reply_text("📜 Your Search History:\n\n" + "\n".join([f"🔍 {n} — {d}" for n, d in rows]))
    elif query.data == "about":
        await query.message.reply_text(f"ℹ️ About Bot\n\n{BOT_USERNAME_SIGNATURE} live retrieval system.")
    elif query.data == "premium":
        await query.message.reply_text("⭐ Premium Plans:\n1 Day -> ₹20\nLifetime -> ₹500\nClick pay now for QR.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay Now", callback_data="pay_now")]]))
    elif query.data == "pay_now":
        await query.message.reply_text(f"💳 Scan QR & send screenshot to {SUPPORT}\nLink: https://ibb.co")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(f"👑 Admin Hub\nTotal Users: {total_users()}")

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    state = USER_STATES.get(user_id)
    
    if not state:
        await update.message.reply_text("⚠️ Kripya pehle upar diye gaye buttons select karein!")
        return

    # ---------------- TELEPHONE SEARCH ----------------
    if state == "NUMBER_SEARCH":
        if not user_input.isdigit() or len(user_input) != 10:
            await update.message.reply_text("❌ Error: Kripya sirf 10-digit number bhejni.")
            return
        await update.message.reply_text("🔍 Status: Searching phone records...")
        try:
            full_search_url = f"{API_URL}&search={user_input}"
            r = requests.get(full_search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            report_text = f"📊 Search Report for: {user_input}\n\n"
            
            if r.status_code == 200:
                try:
                    data = r.json()
                    records = data.get("Data", data) if isinstance(data, dict) else data
                    if isinstance(records, list):
                        for idx, item in enumerate(records, 1):
                            report_text += f"📍 Record #{idx}\n"
                            for k, v in item.items():
                                if v and str(v).strip() != "" and str(v).upper() != "NA":
                                    report_text += f"🔹 {k.capitalize()}: {v}\n"
                            report_text += "\n"
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            report_text += f"🔍 {k.capitalize()}: {v}\n"
                except Exception:
                    if r.text.strip(): report_text += f"📝 Response:\n{r.text.strip()}\n"
                    else: report_text += "⚠️ Error: API response was blank.\n"
            else:
                report_text += f"⚠️ API Error Code: {r.status_code}\n📝 Response: {r.text[:200]}"
                
            report_text += f"\n🤖 Bot: {BOT_USERNAME_SIGNATURE}"
            await update.message.reply_text(report_text)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")

    # ---------------- VEHICLE SEARCH (Fixed Fixed Fixed) ----------------
    elif state == "VEHICLE_SEARCH":
        clean_vehicle = user_input.replace(" ", "").upper()
        await update.message.reply_text(f"🚗 Status: Fetching details for vehicle `{clean_vehicle}`...")
        try:
            # 🛠️ Fixed URL joining format string issue
            final_url = f"{VEHICLE_API_URL}{clean_vehicle}"
            r = requests.get(final_url, timeout=20)
            
            report_text = f"📊 Vehicle Report for: {clean_vehicle}\n\n"
    
