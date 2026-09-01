import asyncio
import sqlite3
import requests
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Config file se variables import ho rahe hain
from config import BOT_TOKEN, ADMIN_ID, NUMBER_API_URL, VEHICLE_API_URL, BOT_NAME, SUPPORT
ADMIN_ID = int(ADMIN_ID)
DB = "bot.db"

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

# ==========================================
# BUTTON HANDLERS (ICONS ADDED)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    keyboard = [
        [InlineKeyboardButton("🔎 Lookup Info", callback_data="lookup")],
        [
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ],
        [InlineKeyboardButton("📜 History", callback_data="history")],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("📞 Contact Support", callback_data="contact")
        ]
    ]

    await update.message.reply_text(
        f"👋 **Welcome to {BOT_NAME}**\n\n"
        f"📝 Send a **10-digit mobile number** OR a **Vehicle Registration number** (e.g., UK04AQ9000) directly!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text("💡 **How to Use:**\n\nSimply send any valid 10-digit mobile number or vehicle plate number in chat.", parse_mode="Markdown")
    elif query.data == "contact":
        await query.message.reply_text(f"📞 **Contact Admin:**\nSupport: {SUPPORT}", parse_mode="Markdown")
    elif query.data == "profile":
        u = get_user(query.from_user.id)
        premium_status = "✅ Premium Active" if is_premium(query.from_user.id) else "❌ Free Account"
        text = (
            f"👤 **Your Account Profile**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **User ID:** `{u[0]}`\n"
            f"👤 **Name:** {u[2]}\n"
            f"📊 **Free Search Left:** {u[3]}\n"
            f"💎 **Status:** {premium_status}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        await query.message.reply_text(text, parse_mode="Markdown")
    elif query.data == "history":
        rows = history(query.from_user.id)
        if not rows:
            await query.message.reply_text("❌ No search history found.")
            return
        text = "📜 **Your Last 10 Lookups:**\n━━━━━━━━━━━━━━━━━━━\n" + "\n".join([f"🔹 `{n}` — *{d}*" for n, d in rows])
        await query.message.reply_text(text, parse_mode="Markdown")
    elif query.data == "premium":
        text = (
            f"💎 **Premium Subscription Plans**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ 1 Day ━━━━━━━━ ₹20\n"
            f"🗓 15 Days ━━━━━━ ₹100\n"
            f"📅 30 Days ━━━━━━ ₹150\n"
            f"👑 Lifetime ━━━━━ ₹500\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 Click on **📞 Contact Support** button or message {SUPPORT} to activate!"
        )
        await query.message.reply_text(text, parse_mode="Markdown")
    elif query.data == "lookup":
        await query.message.reply_text("📥 Please send your **10-digit mobile number** or **Vehicle ID** now:", parse_mode="Markdown")

# ==========================================
# ADMIN PANEL COMMANDS
# ==========================================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied.")
        return
    await update.message.reply_text(
        f"👑 **Admin Control Panel**\n\n👥 **Total Bot Users:** {total_users()}\n\n"
        f"⚙️ **Available Commands:**\n"
        f"🔹 `/users` — List total users\n"
        f"🔹 `/addpremium USER_ID DAYS` — Add premium",
        parse_mode="Markdown"
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT user_id, first_name FROM users")
    rows = cur.fetchall()
    con.close()

    if not rows:
        await update.message.reply_text("No users found.")
        return
    text = "👥 **Users Database List**\n━━━━━━━━━━━━━━━━━━━\n"
    for uid, name in rows:
        text += f"👤 `{uid}` — {name}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: `/addpremium USER_ID DAYS`", parse_mode="Markdown")
        return
    try:
        user_id = int(context.args[0])
        days = context.args[1]
        activate_premium(user_id, days)
        await update.message.reply_text(f"✅ Premium subscription updated for user `{user_id}` for `{days}` days.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ==========================================
# DUAL API LOOKUP SYSTEM (CLEANED & BEAUTIFIED)
# ==========================================
async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_input = update.message.text.strip()
    clean_input = re.sub(r'[\s\-]', '', raw_input) # Spaces ya symbols hatane k liye
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    premium = is_premium(user_id)
    
    if not premium and (user and user[3] <= 0):
