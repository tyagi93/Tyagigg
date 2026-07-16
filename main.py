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

# ADMIN_ID agar string hai toh use number me convert karne ke liye
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
        f"👋 Welcome to {BOT_NAME}\n\nChoose an option below to continue.",
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
        premium_status = "PREMIUM 💎" if is_premium(user_id) else "FREE"
        
        await query.message.reply_text(
            f"👑 Admin: {SUPPORT}\n\n"
            f"🆔 User ID : {u[0]}\n"
            f"👤 Name : {u[2]}\n"
            f"⭐ Plan : {premium_status}\n"
            f"🔍 Searches : {u[3] if u[3] >= 0 else 0} Left\n"
            f"📅 Joined : {u[6] if u[6] else 'First Join'}\n"
            f"_________________________\n\n"
            f"🤖 Bot : {BOT_NAME}"
        )
    elif query.data == "history":
        rows = history(user_id)
        if not rows:
            await query.message.reply_text("📜 Notice: Aapka koi purana search record nahi mila.")
            return
        text = "📜 Your Search History:\n\n" + "\n".join([f"🔍 {n} — Date: {d}" for n, d in rows])
        await query.message.reply_text(text)
        
    elif query.data == "about":
        await query.message.reply_text(f"ℹ️ About Bot\n\n{BOT_NAME} ek high-speed live info retrieval portal system hai.\n👑 Admin: {SUPPORT}")

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
        QR_CODE_URL = "https://i.ibb.co/HDx1Fscz/IMG-20260715-074133-850.jpg" 
        caption_text = (
            f"💳 Payment Gateway\n\n"
            f"◽️ 1 Day Pack ➡️ ₹20\n"
            f"◽️ 15 Days Access ➡️ ₹100\n"
            f"◽️ 30 Days Access ➡️ ₹150\n"
            f"◽️ Lifetime Access ➡️ ₹500\n\n"
            f"✔️ Instructions: Upar diye gaye QR Code ko scan karke payment karein.\n\n"
            f"✅ Note: Payment successful hone ke baad screenshot aur apni User ID support par send karein: {SUPPORT}"
        )
        try:
            await query.message.reply_photo(photo=QR_CODE_URL, caption=caption_text)
        except Exception:
            await query.message.reply_text(caption_text + f"\n\n🔗 QR Link: {QR_CODE_URL}")

# ==========================================
# ADMINISTRATIVE BACKEND MANAGEMENT
# ==========================================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied.")
        return
    await update.message.reply_text(
        f"👑 Admin Hub\n\nTotal Registered Users: {total_users()}\n\nCommands:\n/users\n/addpremium USER_ID DAYS"
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
    text = "👥 Registered Users Directory\n\n"
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
# CORE SEARCH ROUTER & HANDLERS
# ==========================================
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    
    # State check karein ki kaun sa button dabaya tha
    state = USER_STATES.get(user_id)
    
    if not state:
        await update.message.reply_text("⚠️ Kripya pehle upar diye gaye buttons me se **Number Info** ya **Vehicle Info** select karein!")
        return

    user = get_user(user_id)
    premium = is_premium(user_id)
    
    # 3-Limit Check
    if not premium:
        if user and user[3] <= 0:
            await update.message.reply_text(
                "❌ Limit Exhausted: Aapki 3 Free search limits khatam ho chuki hain!\n\n"
                "Kripya aage search karne ke liye Premium active karein."
            )
            return
        reduce_try(user_id)

    # ---------------- TELEPHONE SEARCH ----------------
    if state == "NUMBER_SEARCH":
        if not user_input.isdigit() or len(user_input) != 10:
            await update.message.reply_text("❌ Error: Kripya sirf 10-digit ka mobile number enter karein.")
            return
            
        await update.message.reply_text("🔍 Status: Searching phone records...")
        try:
            r = requests.get(API_URL + user_input, timeout=20)
            report_text = f"📊 Search Report for: {user_input}\n\n"
            if r.status_code == 200:
                data = r.json()
                records = data.get("Data", data) if isinstance(data, dict) else data
                if isinstance(records, list):
                    for idx, item in enumerate(records, 1):
                        report_text += f"📍 Record #{idx}\n"
                        for k, v in item.items():
                            if v is not None and str(v).strip() != "" and str(v).upper() != "NA":
                                report_text += f"🔹 {k.capitalize()}: {v}\n"
                        report_text += "\n"
                elif isinstance(data, dict):
                    for k, v in data.items():
                        report_text += f"🔍 {k.capitalize()}: {v}\n"
            else:
                report_text += f"⚠️ Error: API Data issue (Status Code: {r.status_code})\n"
            
            report_text += f"\n🤖 Bot: {BOT_NAME}\n👑 Admin: {SUPPORT}"
            add_history(user_id, user_input, report_text)
            await update.message.reply_text(report_text)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Connection Error: {e}")

    # ---------------- VEHICLE SEARCH ----------------
    elif state == "VEHICLE_SEARCH":
        clean_vehicle = user_input.replace(" ", "").upper()
        await update.message.reply_text(f"🚗 Status: Fetching details for vehicle `{clean_vehicle}`...")
        try:
            r = requests.get(VEHICLE_API_URL + clean_vehicle, timeout=20)
            report_text = f"📊 Vehicle Report for: {clean_vehicle}\n\n"
            if r.status_code == 200:
                data = r.json()
                details = data.get("data", data)
                if isinstance(details, dict):
                    for k, v in details.items():
                        if v is not None and str(v).strip() != "" and str(v).upper() != "NA":
                            report_text += f"🔹 {k.replace('_', ' ').title()}: {v}\n"
                else:
                    report_text += str(data) + "\n"
            else:
                report_text += f"⚠️ Error: Vehicle API Data issue (Status Code: {r.status_code})\n"
            
            report_text += f"\n🤖 Bot: {BOT_NAME}\n👑 Admin: {SUPPORT}"
            add_history(user_id, clean_vehicle, report_text)
            await update.message.reply_text(report_text)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Connection Error: {e}")

# ==========================================
# SYSTEM SETUP INITIALIZATION
# ==========================================
if __name__ == "__main__":
    create_tables()
    keep_alive()
    print("🚀 Auto-ping background server started...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("addpremium", addpremium))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    print(f"🤖 Server Node {BOT_NAME} Activated...")
    
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
