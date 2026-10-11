import sqlite3
from telebot import TeleBot, types

# ==========================================
# ⚙️ CONFIGURATION & 4 CHANNELS
# ==========================================
BOT_TOKEN = "8620675983:AAGJUNNSOcQ043ADLYai4LW9GU8hJZZBYqk"
BOT_NAME = "Deepak redeem code"
BOT_USERNAME = "Deepakredeemcode1_bot"  # Fixed: Exact bot username updated
ADMIN_ID = 5744767539
SUPPORT_USERNAME = "Tyagizbg"

PER_REFER_BONUS = 3.0
CODE_COST = 10.0

CHANNELS = [
    {
        "name": "Join Deepak Channel 1",
        "url": "https://t.me/itzdeepakisking?livestream=51fd857879b74b2af7"
    },
    {
        "name": "Join Deepak Channel 2",
        "url": "https://t.me/+xObMfd9OJvs4OWFl"
    },
    {
        "name": "Join Rich Paid Mod Hub",
        "url": "https://t.me/Richpaidmodhub"
    },
    {
        "name": "Join Deepak Channel 4",
        "url": "https://t.me/+2jedZDCLLxVkMDQ1"
    }
]

INITIAL_CODES = [
    ("4FXYDYVXTL56JPZM", 10), ("4WBCL3L45GV5R07V", 10),
    ("58JPF8NER05H1PEL", 10), ("K1BRX6EPZTE75XZL", 10),
    ("EPZ7ZC3287FTE3NU", 50), ("3KBVTGFVMWDNPV74", 50),
    ("AJBL6TNVAKXVJBMH", 50), ("8XHKN770WTE131LL", 10),
    ("E7KFGJHCTEPYJPL4", 10), ("DME4KUJ3B5PY923X", 10),
    ("H2A915L32NGD7WA1", 10), ("1SASBTVSACA7GU67", 10),
    ("59MNMWE7DEC1UA7H", 10), ("BYBSMA3PF7R2TNBD", 10),
    ("ERJ7BMTAGHHHF1YC", 10), ("JGTPVMKTW111069V", 10),
    ("8PR6BY152YZXFP7S", 10), ("6S0CET0CFCMPBM0Z", 10),
    ("15H90YC8JXP0GESU", 10), ("E9RV32GA6MPVDPYA", 10),
    ("C7GCDKPE9NBKH454", 10), ("91V0YD9L6Z1ABZF7", 10),
    ("08RW0YJBZCCHYLU1", 10)
]

# ==========================================
# 🗄️ DATABASE (NO LOCK FIX)
# ==========================================
DB_NAME = "bot_data.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            balance REAL DEFAULT 0.0,
            total_referred INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0,
            has_claimed INTEGER DEFAULT 0
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS redeemed_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            amount REAL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS stock_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            amount REAL,
            is_claimed INTEGER DEFAULT 0
        )''')
        for code, amt in INITIAL_CODES:
            cursor.execute("INSERT OR IGNORE INTO stock_codes (code, amount, is_claimed) VALUES (?, ?, 0)", (code, amt))
        conn.commit()

def add_code_to_stock(code, amount):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO stock_codes (code, amount, is_claimed) VALUES (?, ?, 0)", (code, amount))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

init_db()
bot = TeleBot(BOT_TOKEN)

try:
    bot.remove_webhook()
except Exception:
    pass

# ==========================================
# ⚡ AUTO-APPROVE REQUESTS (Private Channels)
# ==========================================
@bot.chat_join_request_handler()
def approve_join_request(update: types.ChatJoinRequest):
    try:
        bot.approve_chat_join_request(update.chat.id, update.from_user.id)
    except Exception:
        pass

def join_channels_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🔹 " + CHANNELS[0]["name"], url=CHANNELS[0]["url"])
    b2 = types.InlineKeyboardButton("🔹 " + CHANNELS[1]["name"], url=CHANNELS[1]["url"])
    b3 = types.InlineKeyboardButton("🔹 " + CHANNELS[2]["name"], url=CHANNELS[2]["url"])
    b4 = types.InlineKeyboardButton("🔹 " + CHANNELS[3]["name"], url=CHANNELS[3]["url"])
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(types.InlineKeyboardButton("✅ Verify Joined", callback_data="verify_action"))
    return markup

def main_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🎁 Refer", callback_data="menu_refer")
    b2 = types.InlineKeyboardButton("💳 Get Code", callback_data="menu_getcode")
    b3 = types.InlineKeyboardButton("💖 Support", callback_data="menu_support")
    b4 = types.InlineKeyboardButton("📜 My History", callback_data="menu_history")
    markup.add(b1, b2)
    markup.add(b3, b4)
    return markup

def back_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_back"))
    return markup

# ==========================================
# 💬 /start HANDLER
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    text_split = message.text.strip().split()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_verified FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            referrer_id = None
            if len(text_split) > 1 and text_split[1].startswith("ref_"):
                try:
                    possible_ref = int(text_split[1].replace("ref_", ""))
                    if possible_ref != user_id:
                        referrer_id = possible_ref
                except ValueError:
                    referrer_id = None
            
            cursor.execute("INSERT INTO users (user_id, referrer_id, balance, total_referred, is_verified, has_claimed) VALUES (?, ?, 0, 0, 0, 0)", (user_id, referrer_id))
            conn.commit()
            is_verified = 0
        else:
            is_verified = user[0]

    if is_verified == 0:
        text = (
            "🔒 **ACCESS REQUIRED**\n\n"
            "Join the channel(s) below to use this bot:\n\n"
            "🔔 **Refer bonus milega sirf tab jab aap saare channels join kar ke Verify dabayein.**"
        )
        bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=join_channels_keyboard())
    else:
        send_home_screen(user_id)

def send_home_screen(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance, referrer_id FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        bal = int(row[0]) if row else 0
        ref_attached = row[1] if row else None

    ref_status = "🔗 No referrer attached." if not ref_attached else "🔗 Referrer attached."
    text = (
        "✅ **Verified!**\n\n"
        f"{ref_status}\n"
        f"💰 **Balance:** ₹{bal}\n\n"
        "Choose an option:"
    )
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ==========================================
# 🔘 VERIFY & CALLBACK HANDLER
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id

    if call.data == "verify_action":
        ref_to_notify = None
        new_ref_bal = 0
        new_ref_count = 0

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT referrer_id, is_verified FROM users WHERE user_id = ?", (user_id,))
            user_info = cursor.fetchone()

            if user_info:
                referrer_id, is_verified = user_info[0], user_info[1]

                if is_verified == 0:
                    cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
                    if referrer_id:
                        cursor.execute("UPDATE users SET balance = balance + ?, total_referred = total_referred + 1 WHERE user_id = ?", (PER_REFER_BONUS, referrer_id))
                        cursor.execute("SELECT balance, total_referred FROM users WHERE user_id = ?", (referrer_id,))
                        referrer_data = cursor.fetchone()
                        if referrer_data:
                            ref_to_notify = referrer_id
                            new_ref_bal = int(referrer_data[0])
                            new_ref_count = referrer_data[1]
                    conn.commit()

        if ref_to_notify:
            ref_msg = (
                "✨ **REFER BONUS CREDITED!**\n\n"
                "✨ A new user joined using your link.\n"
                f"✨ Bonus: ₹{int(PER_REFER_BONUS)}\n"
                f"✨ New Balance: ₹{new_ref_bal}\n"
                f"✨ Total Referred: {new_ref_count}"
            )
            try:
                bot.send_message(ref_to_notify, ref_msg, parse_mode="Markdown")
            except Exception:
                pass

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_home_screen(user_id)

    elif call.data == "menu_refer":
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_referred, balance FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        
        ref_count = row[0] if row else 0
        bal = int(row[1]) if row else 0
        # Corrected username link
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        
        text = (
            "🎁 **REFER & EARN**\n\n"
            f"👤 Per Refer: **₹{int(PER_REFER_BONUS)}**\n"
            f"👥 Total Referred: **{ref_count}**\n"
            f"💰 Your Balance: **₹{bal}**\n\n"
            f"🔗 **Your Refer Link:**\n`{ref_link}`\n\n"
            "🚨 **Note:** Bonus milega jab aapka friend saare channels join kar ke Verify dabaye."
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_keyboard())

    elif call.data == "menu_getcode":
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance, has_claimed FROM users WHERE user_id = ?", (user_id,))
            user_row = cursor.fetchone()
            bal = user_row[0] if user_row else 0
            has_claimed = user_row[1] if user_row else 0

            cursor.execute("SELECT id, code, amount FROM stock_codes WHERE is_claimed = 0 LIMIT 1")
            code_row = cursor.fetchone()

            if has_claimed == 1:
                text = (
                    "⚠️ **LIMIT REACHED!**\n\n"
                    "Aap pehle hi apna 1 code claim kar chuke hain.\n"
                    "Ek user sirf 1 hi code le sakta hai.\n\n"
                    f"💰 **Aapka Balance:** ₹{int(bal)}"
                )
            elif bal < CODE_COST:
                text = (
                    "⚠️ **INSUFFICIENT BALANCE!**\n\n"
                    f"Redeem code lene ke liye kam se kam ₹{int(CODE_COST)} chahiye.\n"
                    f"💰 **Aapka Current Balance:** ₹{int(bal)}\n\n"
                    "Friends ko refer karein aur balance badhayein!"
                )
            elif not code_row:
                text = (
                    "👾 **No codes available right now.**\n\n"
                    "Codes jald hi add kiye jayenge. Stock refill hone ka wait karein.\n"
                    f"💰 **Aapka Balance:** ₹{int(bal)}"
                )
            else:
                c_id, code_text, amt = code_row
                cursor.execute("UPDATE stock_codes SET is_claimed = 1 WHERE id = ?", (c_id,))
                cursor.execute("UPDATE users SET balance = balance - ?, has_claimed = 1 WHERE user_id = ?", (CODE_COST, user_id))
                cursor.execute("INSERT INTO redeemed_history (user_id, code, amount) VALUES (?, ?, ?)", (user_id, code_text, amt))
                conn.commit()

                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                new_bal = cursor.fetchone()[0]

                text = (
                    "🎉 **CODE REDEEMED SUCCESSFULLY!**\n\n"
                    f"✨ Code: `{code_text}` — ₹{int(amt)}\n"
                    f"💰 **Remaining Balance:** ₹{int(new_bal)}"
                )

        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_keyboard())

    elif call.data == "menu_history":
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            bal = cursor.fetchone()[0]

            cursor.execute("SELECT code, amount FROM redeemed_history WHERE user_id = ? ORDER BY id DESC", (user_id,))
            history_rows = cursor.fetchall()

        if not history_rows:
            history_str = "   ✨ No codes yet."
        else:
            history_str = "\n".join([f"   ✨ {r[0]} — ₹{int(r[1])}" for r in history_rows])

        text = (
            "✨ **MY HISTORY**\n\n"
            f"✨ **Balance:** ₹{int(bal)}\n\n"
            f"✨ **Redeemed Codes:**\n{history_str}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_keyboard())

    elif call.data == "menu_support":
        text = "💜 **SUPPORT**\n\nContact our support team for help:"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_back"))
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "menu_back":
        text = "✨ **MAIN MENU**\n\nChoose an option:"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['addcode'])
def add_code_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) == 3:
        code_str = parts[1].strip()
        try:
            amt = float(parts[2])
            if add_code_to_stock(code_str, amt):
                bot.reply_to(message, f"✅ Code `{code_str}` (₹{int(amt)}) stock me add ho gaya!", parse_mode="Markdown")
            else:
                bot.reply_to(message, "⚠️ Yeh code pehle se stock me available hai.")
        except ValueError:
            bot.reply_to(message, "❌ Invalid format! Example: `/addcode 4FXYDYVXTL56JPZM 10`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Sahi format: `/addcode <CODE> <AMOUNT>`", parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Deepak Redeem Code Bot running...")
    bot.infinity_polling(allowed_updates=['message', 'callback_query', 'chat_join_request'], timeout=20)
