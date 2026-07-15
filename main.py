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

# 👑 INTERNAL ADMINISTRATIVE CONFIGURATION (Hidden from Users)
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
# BUTTON HANDLERS (EXECUTIVE FORMATTING)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)

    keyboard = [
        [InlineKeyboardButton("🔹 Execute Query Lookup", callback_data="lookup")],
        [
            InlineKeyboardButton("▫️ User Profile", callback_data="profile"),
            InlineKeyboardButton("♦️ Premium Subscriptions", callback_data="premium")
        ],
        [InlineKeyboardButton("▫️ Retrieval Logs", callback_data="history")],
        [
            InlineKeyboardButton("➡️ User Manual", callback_data="help"),
            InlineKeyboardButton("✉️ Corporate Desk", callback_data="contact")
        ]
    ]

    await update.message.reply_text(
        f"♦️ **{BOT_NAME} Enterprise Resource Portal**\n\n"
        f"Centralized Data Management Console Activated.\n"
        f"Kindly input a designated 10-digit communication vector to initiate system lookup processing.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text(
            f"➡️ **Operational Framework & Guidelines**\n\n"
            f"🔹 **Data Retrieval:** Transmit any authorized 10-digit system numeric directly into the secure chat sequence to execute query processing.\n"
            f"🔹 **Allocation Allotment:** Standard user nodes are configured with an operational quota of 3 default diagnostics.\n\n"
            f"♦️ For account authorization adjustments or enterprise scale access requirements, submit an official request to the operations management desk: {SUPPORT}."
        )
    elif query.data == "contact":
        await query.message.reply_text(
            f"✉️ **Official Operations Management Desk**\n\n"
            f"For subscription processing adjustments, high-volume server access requirements, or technical node verification, coordinate at:\n\n"
            f"➡️ **Management Registry:** {SUPPORT}"
        )
    elif query.data == "profile":
        u = get_user(query.from_user.id)
        premium_status = "Premium Node [Authorized] ♦️" if is_premium(query.from_user.id) else "Standard Tier Account"
        await query.message.reply_text(
            f"▫️ **User Node Parameter Summary**\n\n"
            f"🔹 **System Account ID:** `{u[0]}`\n"
            f"🔹 **Registered Identity:** {u[2]}\n"
            f"🔹 **Complimentary Queries Remaining:** {u[3]}\n"
            f"🔹 **Infrastructure Profile Allocation:** {premium_status}"
        )
    elif query.data == "history":
        rows = history(query.from_user.id)
        if not rows:
            await query.message.reply_text("▫️ **System Log Notice:** Database registers null entries for the requested account profile.")
            return
        text = "▫️ **Historical Retrieval Logs (Last 10 Matrix Processes):**\n\n" + "\n".join([f"🔹 Vector: {n} — Process Time: {d}" for n, d in rows])
        await query.message.reply_text(text)
    elif query.data == "premium":
        keyboard = [[InlineKeyboardButton("💳 Generate Invoice Gateway (QR)", callback_data="pay_now")]]
        await query.message.reply_text(
            "♦️ **Premium Enterprise Plan Structure**\n\n"
            f"➡️ **Operational Tiers:**\n"
            f"◽️ 01 Day Infrastructure Pass ➡️ ₹20\n"
            f"◽️ 15 Days Infrastructure Pass ➡️ ₹100\n"
            f"◽️ 30 Days Infrastructure Pass ➡️ ₹150\n"
            f"◽️ Corporate Lifetime Allocation ➡️ ₹500\n\n"
            "Select the validation module ниже to interface with the designated transaction node infrastructure.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "pay_now":
        QR_CODE_URL = "https://i.ibb.co/HDx1Fscz/IMG-20260715-074133-850.jpg" 
        
        caption_text = (
            f"💳 **Secure Transaction Node & Digital Remittance Invoice**\n\n"
            f"➡️ **Tariff Assessment Matrix:**\n"
            f"🔹 01 Day Infrastructure Pass ➡️ ₹20\n"
            f"🔹 15 Days Infrastructure Pass ➡️ ₹100\n"
            f"🔹 30 Days Infrastructure Pass ➡️ ₹150\n"
            f"🔹 Corporate Lifetime Allocation ➡️ ₹500\n\n"
            f"✔️ **Operational Directive:** Execute remittance processing by rendering the attached secure network QR vector via any UPI or authorized corporate clearance terminal.\n\n"
            f"✅ **Mandatory Verification Protocol:** Upon execution of the fund clearance, forward the ledger receipt asset along with the designated **System Account ID** (retrievable via User Profile) to our administrative validation hub for final profile upgrade execution: {SUPPORT}"
        )
        
        try:
            await query.message.reply_photo(photo=QR_CODE_URL, caption=caption_text)
        except Exception:
            await query.message.reply_text(caption_text + f"\n\n🔗 **Secure Transaction Link:** {QR_CODE_URL}\n⚠️ (System Note: If the secure graphic network fails to preview inline, initialize processing via the manual database redirection hyperlink above.)")
            
    elif query.data == "lookup":
        await query.message.reply_text("🔹 **Database Directive:** Please input the target 10-digit communication vector to run analytics.")

# ==========================================
# ADMINISTRATIVE BACKEND MANAGEMENT (Only for You)
# ==========================================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ System Exception: Access Violation. Security Credentials Mismatch.")
        return
    await update.message.reply_text(
        f"👑 Executive System Administrative Hub\n\n👥 Registered Matrix Client Density: {total_users()}\n\nExecution Script Controls:\n/users\n/addpremium USER_ID DAYS"
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
        await update.message.reply_text("No client matrix parameters located inside active memory.")
        return
    text = "👥 Core Mainframe Client Node Directory\n\n"
    for uid, name in rows:
        text += f"Node ID: {uid} | Matrix Label: {name}\n"
    await update.message.reply_text(text)

async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Syntax Directive: /addpremium USER_ID DAYS")
        return
    try:
        user_id = int(context.args[0])
        days = context.args[1]
        activate_premium(user_id, days)
        await update.message.reply_text(f"✅ Protocol Success: System database credentials modified for Node ID {user_id} for a duration of {days} computational allocations.")
    except Exception as e:
        await update.message.reply_text(f"Exception Matrix Error Raised: {e}")

# ==========================================
# RETRIEVAL INFRASTRUCTURE ANALYSIS
# ==========================================
async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()
    if not number.isdigit() or len(number) != 10:
        await update.message.reply_text("❌ **Data Format Rejection:** Parameter violation. Input must be structured strictly within a 10-digit matrix array.")
        return
        
    user_id = update.effective_user.id
    user = get_user(user_id)
    premium = is_premium(user_id)
    
    if not premium and (user and user[3] <= 0):
        await update.message.reply_text("❌ **Operation Halted:** Allocation limits exhausted. Please upgrade account settings via the Premium Plan panel to reactivate node processing.")
        return
        
    if not premium:
        reduce_try(user_id)
        
    await update.message.reply_text("🔎 **Process Log:** Evaluating infrastructure servers and indexing records. Processing query...")
    try:
        r = requests.get(API_URL + number, timeout=20)
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, dict):
                    text = f"📊 **Analytical Output Report for Query Node: {number}**\n\n"
                    for key, val in data.items():
                        text += f"🔹 **{key.capitalize()}:** {val}\n"
                else:
                    text = str(data)
            except ValueError:
                text = r.text
        else:
            text = f"⚠️ **Mainframe Sync Disruption:** API Gateway Endpoint Returned State {r.status_code}"

        if "@kihoerack" in text or "@YeuIin" in text:
            text = text.replace("@kihoerack", f"@{context.bot.username} (Internal Host)")
            text = text.replace("@YeuIin", f"{BOT_NAME} Enterprise Management Desk")

        add_history(user_id, number, text)
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ **Network Core Exception Interrupted:** {e}")

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

    print(f"🤖 Secure Mainframe Node {BOT_NAME} Initialized Successfully...")
    
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
