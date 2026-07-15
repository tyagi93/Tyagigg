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

# 👑 INTERNAL ADMIN CONFIGURATION (Hidden from Users)
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
# BUTTON HANDLERS (SIMPLE & CLEAN HINGLISH)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    keyboard = [
        [InlineKeyboardButton("🔎 Number Info", callback_data="lookup")],
        [
            InlineKeyboardButton("🔹 Profile", callback_data="profile"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ],
        [InlineKeyboardButton("🔹 History", callback_data="history")],
        [
            InlineKeyboardButton("➡️ Help", callback_data="help"),
            InlineKeyboardButton("➡️ Contact Support", callback_data="contact")
        ]
    ]

    await update.message.reply_text(
        f"🔹 **Welcome to {BOT_NAME}**\n\n"
        f"Aapka swagat hai. Search shuru karne ke liye niche diye gaye button par click karein ya direct 10-digit mobile number send karein.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text(
            f"➡️ **Help & Guidelines**\n\n"
            f"🔹 **Search Kaise Karein:** Chat me direct koi bhi 10-digit mobile number type karke send karein.\n"
            f"🔹 **Free Limit:** Har normal account ko 3 free search milte hain.\n\n"
            f"Premium subscription active karne ya kisi bhi madad ke liye support handle par sampark karein: {SUPPORT}."
        )
    elif query.data == "contact":
        await query.message.reply_text(
            f"➡️ **Official Support Desk**\n\n"
            f"Kisi bhi tarah ki technical help ya premium activation ke liye yahan message karein:\n"
            f"🔹 **Support Username:** {SUPPORT}"
        )
    elif query.data == "profile":
        u = get_user(query.from_user.id)
        premium_status = "Active 💎" if is_premium(query.from_user.id) else "Standard User"
        await query.message.reply_text(
            f"🔹 **Account Profile Details**\n\n"
            f"🔹 **User ID:** `{u[0]}`\n"
            f"🔹 **Name:** {u[2]}\n"
            f"🔹 **Free Search Left:** {u[3]}\n"
            f"🔹 **Account Status:** {premium_status}"
        )
    elif query.data == "history":
        rows = history(query.from_user.id)
        if not rows:
            await query.message.reply_text("🔹 **Notice:** Aapka koi purana search record nahi mila.")
            return
        text = "🔹 **Aapki Last 10 Search History:**\n\n" + "\n".join([f"🔹 {n} — Date: {d}" for n, d in rows])
        await query.message.reply_text(text)
    elif query.data == "premium":
        keyboard = [[InlineKeyboardButton("💳 Pay Now (QR Code)", callback_data="pay_now")]]
        await query.message.reply_text(
            "🔹 **Premium Subscription Plans:**\n\n"
            f"➡️ **Plan Details:**\n"
            f"🔹 1 Day Pack ➡️ ₹20\n"
            f"🔹 15 Days Access ➡️ ₹100\n"
            f"🔹 30 Days Access ➡️ ₹150\n"
            f"🔹 Lifetime Access ➡️ ₹500\n\n"
            "Niche diye gaye button par click karke payment QR code dekhein.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "pay_now":
        QR_CODE_URL = "https://i.ibb.co/HDx1Fscz/IMG-20260715-074133-850.jpg" 
        
        caption_text = (
            f"💳 **Secure Payment Gateway**\n\n"
            f"➡️ **Plans Price List:**\n"
            f"🔹 1 Day Pack ➡️ ₹20\n"
            f"🔹 15 Days Access ➡️ ₹100\n"
            f"🔹 30 Days Access ➡️ ₹150\n"
            f"🔹 Lifetime Access ➡️ ₹500\n\n"
            f"✔️ **Instructions:** Upar diye gaye QR Code ko kisi bhi UPI app (PhonePe, Paytm, GooglePay) se scan karke payment karein.\n\n"
            f"✅ **Zaroori Protocol:** Payment successful hone ke baad screenshot aur apni **User ID** (jo Profile section me milti hai) support par send karein: {SUPPORT}"
        )
        
        try:
            await query.message.reply_photo(photo=QR_CODE_URL, caption=caption_text)
        except Exception:
            await query.message.reply_text(caption_text + f"\n\n🔗 **QR Link:** {QR_CODE_URL}\n⚠️ (Agar upar photo show na ho toh is link par click karke QR code dekh lein.)")
            
    elif query.data == "lookup":
        await query.message.reply_text("🔹 Please 10-digit mobile number send karein.")

# ==========================================
# ADMINISTRATIVE BACKEND MANAGEMENT (Only for You)
# ==========================================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied. Unauthorized Personnel.")
        return
    await update.message.reply_text(
        f"👑 Executive Administrative Hub\n\n👥 Total Registered Users: {total_users()}\n\nCommands:\n/users\n/addpremium USER_ID DAYS"
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
    text = "👥 Registered Client Directory\n\n"
    for uid, name in rows:
        text += f"ID: {uid} | Name: {name}\n"
    await update.message.reply_text(text)

async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Syntax: /addpremium USER_ID DAYS")
        return
    try:
        user_id = int(context.args[0])
        days = context.args[1]
        activate_premium(user_id, days)
        await update.message.reply_text(f"✅ Success: Premium active ho gaya hai user {user_id} ke liye {days} days tak.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ==========================================
# RETRIEVAL INFRASTRUCTURE ANALYSIS
# ==========================================
async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()
    if not number.isdigit() or len(number) != 10:
        await update.message.reply_text("❌ **Format Error:** Kripya sirf 10-digit ka sahi mobile number hi enter karein.")
        return
        
    user_id = update.effective_user.id
    user = get_user(user_id)
    premium = is_premium(user_id)
    
    if not premium and (user and user[3] <= 0):
        await update.message.reply_text("❌ **Limit Exhausted:** Aapki free limits khatam ho chuki hain. Kripya aage continue karne ke liye Premium purchase karein.")
        return
        
    if not premium:
        reduce_try(user_id)
        
    await update.message.reply_text("🔍 **Status:** Database se details fetch ki ja rahi hain. Kripya thoda intezar karein...")
    try:
        r = requests.get(API_URL + number, timeout=20)
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, dict):
                    text = f"📊 **Search Report for: {number}**\n\n"
                    for key, val in data.items():
                        text += f"🔹 **{key.capitalize()}:** {val}\n"
                else:
                    text = str(data)
            except ValueError:
                text = r.text
        else:
            text = f"⚠️ **Error:** API Gateway se data nahi mila (Status Code: {r.status_code})"

        if "@kihoerack" in text or "@YeuIin" in text:
            text = text.replace("@kihoerack", f"@{context.bot.username} (Internal Node)")
            text = text.replace("@YeuIin", f"{BOT_NAME} Support Desk")

        add_history(user_id, number, text)
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ **Connection Error:** {e}")

# ==========================================
# SYSTEM SETUP INITIALIZATION
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

    print(f"🤖 Secure Server Node {BOT_NAME} Activated...")
    
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
