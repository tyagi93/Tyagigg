import sqlite3

DB_NAME = "bot_data.db"

# Aapke diye hue saare codes (Code, Amount)
INITIAL_CODES = [
    ("4FXYDYVXTL56JPZM", 10),
    ("4WBCL3L45GV5R07V", 10),
    ("58JPF8NER05H1PEL", 10),
    ("K1BRX6EPZTE75XZL", 10),
    ("EPZ7ZC3287FTE3NU", 50),
    ("3KBVTGFVMWDNPV74", 50),
    ("AJBL6TNVAKXVJBMH", 50),
    ("8XHKN770WTE131LL", 10),
    ("E7KFGJHCTEPYJPL4", 10),
    ("DME4KUJ3B5PY923X", 10),
    ("H2A915L32NGD7WA1", 10),
    ("1SASBTVSACA7GU67", 10),
    ("59MNMWE7DEC1UA7H", 10),
    ("BYBSMA3PF7R2TNBD", 10),
    ("ERJ7BMTAGHHHF1YC", 10),
    ("JGTPVMKTW111069V", 10),
    ("8PR6BY152YZXFP7S", 10),
    ("6S0CET0CFCMPBM0Z", 10),
    ("15H90YC8JXP0GESU", 10),
    ("E9RV32GA6MPVDPYA", 10),
    ("C7GCDKPE9NBKH454", 10),
    ("91V0YD9L6Z1ABZF7", 10),
    ("08RW0YJBZCCHYLU1", 10)
]

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        referrer_id INTEGER,
        balance REAL DEFAULT 0.0,
        total_referred INTEGER DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        has_claimed INTEGER DEFAULT 0
    )''')
    
    # Claimed codes history
    cursor.execute('''CREATE TABLE IF NOT EXISTS redeemed_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        code TEXT,
        amount REAL
    )''')
    
    # Stock codes table
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        amount REAL,
        is_claimed INTEGER DEFAULT 0
    )''')
    
    # Saare 23 codes automatically load ho jayenge
    for code, amt in INITIAL_CODES:
        cursor.execute("INSERT OR IGNORE INTO stock_codes (code, amount, is_claimed) VALUES (?, ?, 0)", (code, amt))
    
    conn.commit()
    conn.close()

def add_code_to_stock(code, amount):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO stock_codes (code, amount, is_claimed) VALUES (?, ?, 0)", (code, amount))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
