from telebot import TeleBot, types
import config
import database

database.init_db()
bot = TeleBot(config.BOT_TOKEN)

def check_user_joined(user_id):
    for ch in config.CHANNELS:
        try:
            member = bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def join_channels_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [types.InlineKeyboardButton(f"🔹 {ch['name']}", url=ch["url"]) for ch in config.CHANNELS]
    markup.add(*btns)
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

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    referrer = None
    if not user:
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer = int(args[1].replace("ref_", ""))
                if referrer == user_id:
                    referrer = None
            except ValueError:
                referrer = None
        # Default starting balance = 0
        cursor.execute("INSERT INTO users (user_id, referrer_id, balance, total_referred, is_verified, has_claimed) VALUES (?, ?, 0, 0, 0, 0)", (user_id, referrer))
        conn.commit()
    conn.close()

    if not check_user_joined(user_id):
        text = (
            "🔒 **ACCESS REQUIRED**\n\n"
            "Join the channel(s) below to use this bot:\n\n"
            "🔔 **Refer bonus milega sirf tab jab aap saare channels join kar ke Verify dabayein.**"
        )
        bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=join_channels_keyboard())
    else:
        conn = database.get_connection()
        conn.cursor().execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        send_home_screen(user_id)

def send_home_screen(user_id):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    bal = int(row[0]) if row else 0
    conn.close()

    text = (
        "✅ **Verified!**\n\n"
        "🔗 No referrer attached.\n"
        f"💰 **Balance:** ₹{bal}\n\n"
        "Choose an option:"
    )
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# Admin Command: Naye codes dalne ke liye
@bot.message_handler(commands=['addcode'])
def add_code_cmd(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) == 3:
        code_str = parts[1].strip()
        try:
            amt = float(parts[2])
            if database.add_code_to_stock(code_str, amt):
                bot.reply_to(message, f"✅ Code `{code_str}` (₹{int(amt)}) stock me add ho gaya!", parse_mode="Markdown")
            else:
                bot.reply_to(message, "⚠️ Yeh code pehle se stock me available hai.")
        except ValueError:
            bot.reply_to(message, "❌ Invalid format! Example: `/addcode 4FXYDYVXTL56JPZM 10`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Sahi format: `/addcode <CODE> <AMOUNT>`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id

    if call.data == "verify_action":
        if check_user_joined(user_id):
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT referrer_id, is_verified FROM users WHERE user_id = ?", (user_id,))
            data = cursor.fetchone()
            
            if data and data[1] == 0:
                ref_id = data[0]
                if ref_id:
                    cursor.execute("UPDATE users SET balance = balance + ?, total_referred = total_referred + 1 WHERE user_id = ?", (config.PER_REFER_BONUS, ref_id))
                    cursor.execute("SELECT balance, total_referred FROM users WHERE user_id = ?", (ref_id,))
                    ref_data = cursor.fetchone()
                    conn.commit()

                    ref_msg = (
                        "✨ **REFER BONUS CREDITED!**\n\n"
                        "✨ A new user joined using your link.\n"
                        f"✨ Bonus: ₹{int(config.PER_REFER_BONUS)}\n"
                        f"✨ New Balance: ₹{int(ref_data[0])}\n"
                        f"✨ Total Referred: {ref_data[1]}"
                    )
                    try:
                        bot.send_message(ref_id, ref_msg, parse_mode="Markdown")
                    except Exception:
                        pass
                cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
                conn.commit()
            conn.close()

            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_home_screen(user_id)
        else:
            bot.answer_callback_query(call.id, "❌ Pehle saare channels join karein!", show_alert=True)

    elif call.data == "menu_refer":
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT total_referred, balance FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        ref_count, bal = row if row else (0, 0.0)
        ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{user_id}"
        
        text = (
            "🎁 **REFER & EARN**\n\n"
            f"👤 Per Refer: **₹{int(config.PER_REFER_BONUS)}**\n"
            f"👥 Total Referred: **{ref_count}**\n"
            f"💰 Your Balance: **₹{int(bal)}**\n\n"
            f"🔗 **Your Refer Link:**\n`{ref_link}`\n\n"
            "🚨 **Note:** Bonus milega jab aapka friend saare channels join kar ke Verify dabaye."
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_keyboard())

    elif call.data == "menu_getcode":
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance, has_claimed FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        bal = user_row[0] if user_row else 0
        has_claimed = user_row[1] if user_row else 0

        cursor.execute("SELECT id, code, amount FROM stock_codes WHERE is_claimed = 0 LIMIT 1")
        code_row = cursor.fetchone()

        # Sirf 1 code lifetime limit
        if has_claimed == 1:
            text = (
                "⚠️ **LIMIT REACHED!**\n\n"
                "Aap pehle hi apna 1 code claim kar chuke hain.\n"
                "Ek user sirf 1 hi code le sakta hai.\n\n"
                f"💰 **Aapka Balance:** ₹{int(bal)}"
            )
        # Minimum ₹10 balance limit
        elif bal < config.CODE_COST:
            text = (
                "⚠️ **INSUFFICIENT BALANCE!**\n\n"
                f"Redeem code lene ke liye kam se kam ₹{int(config.CODE_COST)} chahiye.\n"
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
            cursor.execute("UPDATE users SET balance = balance - ?, has_claimed = 1 WHERE user_id = ?", (config.CODE_COST, user_id))
            cursor.execute("INSERT INTO redeemed_history (user_id, code, amount) VALUES (?, ?, ?)", (user_id, code_text, amt))
            conn.commit()

            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_bal = cursor.fetchone()[0]

            text = (
                "🎉 **CODE REDEEMED SUCCESSFULLY!**\n\n"
                f"✨ Code: `{code_text}` — ₹{int(amt)}\n"
                f"💰 **Remaining Balance:** ₹{int(new_bal)}"
            )

        conn.close()
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_keyboard())

    elif call.data == "menu_history":
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]

        cursor.execute("SELECT code, amount FROM redeemed_history WHERE user_id = ? ORDER BY id DESC", (user_id,))
        history_rows = cursor.fetchall()
        conn.close()

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
        markup.add(types.InlineKeyboardButton("📩 Contact Support", url=f"https://t.me/{config.SUPPORT_USERNAME}"))
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_back"))
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "menu_back":
        text = "✨ **MAIN MENU**\n\nChoose an option:"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=main_menu_keyboard())

if __name__ == "__main__":
    print("🚀 Deepak Redeem Code Bot successfully running...")
    bot.infinity_polling()
            
