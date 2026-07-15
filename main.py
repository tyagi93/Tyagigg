import asyncio
import sqlite3
import requests
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
try:
    from config import BOT_TOKEN, API_URL, BOT_NAME
except ImportError:
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    API_URL = "YOUR_API_URL"
    BOT_NAME = "Bot"

# 👑 OWNER & ADMIN CONTROLS FIXED
ADMIN_ID = 5744767539
SUPPORT = "@TYAGI8"
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
# BUTTON HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    keyboard = [
        [InlineKeyboardButton("🔎 Number Info", callback_data="lookup")],
        [
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ],
        [InlineKeyboardButton("📜 History", callback_data="history")],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("📞 Contact", callback_data="contact")
        ]
    ]

    await update.message.reply_text(
        f"👋 Welcome to {BOT_NAME}\n\nSend a 10-digit mobile number.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text(
            f"❓ **Help & Support** ❓\n\n"
            f"👑 **Admin Username:** {SUPPORT}\n"
            f"📌 **Admin ID:** `{ADMIN_ID}`\n\n"
            f"Agar bot me koi dikkat aa rahi hai ya premium purchase karna hai, toh upar diye gaye username par click karke direct mujhe message karein!"
        )
    elif query.data == "contact":
        await query.message.reply_text(f"📞 Contact Admin: {SUPPORT}\nAdmin ID: {ADMIN_ID}")
    elif query.data == "profile":
        u = get_user(query.from_user.id)
        premium_status = "Yes" if is_premium(query.from_user.id) else "No"
        await query.message.reply_text(
            f"ID: {u[0]}\nName: {u[2]}\nFree Left: {u[3]}\nPremium User: {premium_status}"
        )
    elif query.data == "history":
        rows = history(query.from_user.id)
        if not rows:
            await query.message.reply_text("No history found.")
            return
        text = "📜 Your Last 10 Lookups:\n\n" + "\n".join([f"{n} - {d}" for n, d in rows])
        await query.message.reply_text(text)
    elif query.data == "premium":
        keyboard = [[InlineKeyboardButton("💳 Pay Now (QR Code)", callback_data="pay_now")]]
        await query.message.reply_text(
            "💎 **Premium Plans:**\n1 Day --- ₹20\n15 Days --- ₹100\n30 Days --- ₹150\nLifetime --- ₹500\n\nNeeche diye gaye button par click karke payment details aur QR code dekhein!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "pay_now":
        # ✅ AAPKA REAL QR CODE IMAGE LINK SET KAR DIYA HAI
        QR_CODE_URL = "https://i.ibb.co/HDx1Fscz/IMG-20260715-074133-850.jpg" 
        
        caption_text = (
            f"💰 **Payment Details & QR Code** 💰\n\n"
            f"💵 **Plans:**\n"
            f"🔹 1 Day -> ₹20\n"
            f"🔹 15 Days -> ₹100\n"
            f"🔹 30 Days -> ₹150\n"
            f"🔹 Lifetime -> ₹500\n\n"
            f"📌 Upar diye gaye QR Code ko scan karke payment karein.\n\n"
            f"✅ **Zaroori:** Payment karne ke baad screenshot aur apni User ID (@profile section se copy karke) Admin ko bhejein: {SUPPORT}"
        )
        
        try:
            await query.message.reply_photo(photo=QR_CODE_URL, caption=caption_text)
        except Exception:
            await query.message.reply_text(caption_text + f"\n\n🔗 **Direct Link:** {QR_CODE_URL}\n⚠️ (Agar upar photo show na ho toh is link par click karke QR dekh lein)")
            
    elif query.data == "lookup":
        await query.message.reply_text("Send your 10-digit mobile number.")

# ==========================================
# ADMIN PANEL COMMANDS
# ==========================================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied.")
        return
    await update.message.reply_text(
        f"👑 Admin Panel\n\n👥 Total Users: {total_users()}\n\nCommands:\n/users\n/addpremium USER_ID DAYS"
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
    text = "👥 Users List\n\n"
    for uid, name in rows:
        text += f"{uid} - {name}\n"
    await update.message.reply_text(text)

async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpremium USER_ID DAYS")
        return
    try:
        user_id = int(context.args[0])
        days = context.args[1]
        activate_premium(user_id, days)
        await update.message.reply_text(f"✅ Premium updated for user {user_id} for {days} days.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ==========================================
# API LOOKUP SYSTEM
# ==========================================
async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()
    if not number.isdigit() or len(number) != 10:
        await update.message.reply_text("❌ Please send a valid 10-digit mobile number.")
        return
        
    user_id = update.effective_user.id
    user = get_user(user_id)
    premium = is_premium(user_id)
    
    if not premium and (user and user[3] <= 0):
        await update.message.reply_text("❌ Free limit over. Buy Premium.")
        return
        
    if not premium:
        reduce_try(user_id)
        
    await update.message.reply_text("🔍 Searching...")
    try:
        r = requests.get(API_URL + number, timeout=20)
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, dict):
                    text = f"📞 Number: {number}\n"
                    for key, val in data.items():
                        text += f"🔹 {key.capitalize()}: {val}\n"
                else:
                    text = str(data)
            except ValueError:
                text = r.text
        else:
            text = f"⚠️ API Error (Status Code: {r.status_code})"

        if "@kihoerack" in text or "@YeuIin" in text:
            text = text.replace("@kihoerack", f"@{context.bot.username} (You)")
            text = text.replace("@YeuIin", f"{BOT_NAME} Support")

        add_history(user_id, number, text)
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Error connecting to API: {e}")

# ==========================================
# MAIN INITIALIZATION
# ==========================================
if __name__ == "__main__":
    create_tables()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("addpremium", addpremium))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lookup))

    print(f"🤖 {BOT_NAME} Started...")
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(app.initialize())
    loop.run_until_complete(app.updater.start_polling(drop_pending_updates=True))
    loop.run_until_complete(app.start())
    
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
