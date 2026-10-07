import os
import sqlite3
import logging
import zipfile
import io
from threading import Thread
from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

TOKEN = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
SUPER_ADMIN_ID = int(os.environ.get("SUPER_ADMIN_ID", "123456789"))

DB_PATH = os.environ.get("DB_PATH", "bot_database.db")

bot = telebot.TeleBot(TOKEN)

SERVER_INFO_TEXT = (
    "🔷 **የሰርቨር አገልግሎት መረጃ:**\n\n"
    "ሰርቨርዎን ማደስ ከፈለጉ ከክፍያ በኋላ የክፍያውን ደረሰኝ (Screenshot) በዚህ ቦት ይላኩን።\n\n"
    "ለማስጨረስ ወይም ጥያቄ ካሎት በቀጥታ በዚህ ያናግሩን: 👉 @kerim2000"
)

BUY_ITEM_TEXT = (
    "🛒 **እቃ ለመግዛት:**\n\n"
    "የሚፈልጉትን እቃ ወይም ሪሲቨር ለመግዛት ከፈለጉ ከታች ባለው ዩዘርናም በቀጥታ ያናግሩን።\n\n"
    "👉 @kerim2000"
)

ADMIN_STATE = {}

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS receivers (key TEXT PRIMARY KEY, caption TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tv_software (key TEXT PRIMARY KEY, caption TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS sub_folders (id INTEGER PRIMARY KEY AUTOINCREMENT, receiver_key TEXT, folder_name TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS bin_files (id INTEGER PRIMARY KEY AUTOINCREMENT, receiver_key TEXT, sub_folder_id INTEGER DEFAULT 0, file_name TEXT, file_id TEXT, file_size TEXT, downloads_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tv_files (id INTEGER PRIMARY KEY AUTOINCREMENT, tv_key TEXT, file_name TEXT, file_id TEXT, file_size TEXT, downloads_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, invited_by INTEGER, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, file_id TEXT, status TEXT DEFAULT 'PENDING', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('must_join_channel', '@your_channel_username')")

    default_receivers = ["FREE_SAT", "CORONATE", "MEWE", "TIGER", "LIFESTARE", "SUPERMAX", "GOLDSTAR", "LEG"]
    for key in default_receivers:
        cursor.execute("INSERT OR IGNORE INTO receivers (key, caption) VALUES (?, ?)", (key, f"{key} RECEIVER SOFTWARE"))

    default_tvs = ["SAMSUNG", "LG", "HISENSE", "TCL", "TOAST", "SKYWORTH"]
    for key in default_tvs:
        cursor.execute("INSERT OR IGNORE INTO tv_software (key, caption) VALUES (?, ?)", (key, f"{key} TV SOFTWARE"))

    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_must_join_channel():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'must_join_channel'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "@your_channel_username"

def register_user(user_id, username, invited_by=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute("INSERT INTO users (user_id, username, invited_by) VALUES (?, ?, ?)", (user_id, username, invited_by))
            conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error registering user: {e}")

def get_referral_count(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE invited_by = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def check_user_joined(user_id):
    channel = get_must_join_channel()
    if not channel or channel == "@your_channel_username":
        return True
    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except Exception:
        return True
    return False

def clean_key(text):
    for char in ["🔹", "🔷", "✨", "🛒", "💻", "📚", "⭐", "🔥", "🔍", "⏱", "❓", "🌐", "⚙", "📺", "📍", "🔻", "🔻"]:
        text = text.replace(char, "")
    return text.strip().replace(" ", "_").upper()

def get_all_receivers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key FROM receivers ORDER BY key ASC")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_all_tvs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key FROM tv_software ORDER BY key ASC")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def main_menu(user_id, is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🛒 ✨ እቃ ለመግዛት ✨ 🛒"), KeyboardButton("🔷 SERVER ለመግዛት 🔷"))
    markup.row(KeyboardButton("💻 📚 HD RECEIVER SOFTWARES 📚 💻"))
    markup.row(KeyboardButton("📺 📚 TV SOFTWARES 📚 📺"))
    markup.row(KeyboardButton("🔥 አዲስ የተለቀቁ"), KeyboardButton("🎁 ጓደኛጋብዝ (Referral)"))
    markup.row(KeyboardButton("🔍 ፋይል / ሪሲቨር ፈልግ"))
    if is_admin:
        markup.row(KeyboardButton("⚙ አድሚን ፓነል (Admin Panel)"))
    return markup

def receivers_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    receivers = get_all_receivers()
    buttons = [KeyboardButton(f"🔹 {name.replace('_', ' ')} 🔹") for name in receivers]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.row(KeyboardButton("🔙 Back"), KeyboardButton("🔝 Main Menu"))
    return markup

def tv_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    tvs = get_all_tvs()
    buttons = [KeyboardButton(f"📺 {name.replace('_', ' ')} 📺") for name in tvs]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.row(KeyboardButton("🔙 Back"), KeyboardButton("🔝 Main Menu"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    args = message.text.split()
    invited_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].replace("ref_", ""))
            if ref_id != user_id:  
                invited_by = ref_id
        except ValueError:
            pass

    register_user(user_id, username, invited_by)
    is_admin = (user_id == SUPER_ADMIN_ID)
    bot.send_message(message.chat.id, "🌟 **ሰላም! እንኳን ወደ ሪሲቨር እና ቲቪ ሶፍትዌር ማከማቻ ቦት በደህና መጡ።**", parse_mode="Markdown", reply_markup=main_menu(user_id, is_admin))

@bot.message_handler(content_types=['document', 'photo', 'video', 'text'])
def handle_all_messages(message):
    global ADMIN_STATE
    user_id = message.from_user.id
    is_admin = (user_id == SUPER_ADMIN_ID)
    text = message.text if message.text else ""

    if is_admin and user_id in ADMIN_STATE and ADMIN_STATE.get(user_id) == "WAITING_BROADCAST":
        ADMIN_STATE.pop(user_id, None)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        count = 0
        for u in users:
            try:
                bot.copy_message(u[0], message.chat.id, message.message_id)
                count += 1
            except Exception:
                pass
        bot.send_message(message.chat.id, f"✅ ማስታወቂያው ለ **{count}** ተጠቃሚዎች ተልኳል!")
        return

    if is_admin and user_id in ADMIN_STATE and ADMIN_STATE.get(user_id) == "WAITING_CHANNEL_UPDATE":
        ADMIN_STATE.pop(user_id, None)
        new_ch = text.strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'must_join_channel'", (new_ch,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ የማስገደጃ ቻናል ዩዘርናም ወደ **{new_ch}** ተቀይሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
        return

    if is_admin and user_id in ADMIN_STATE and isinstance(ADMIN_STATE.get(user_id), dict):
        state_data = ADMIN_STATE[user_id]
        if state_data.get("state") == "WAITING_NEW_FOLDER_NAME":
            folder_name = clean_key(text)
            ADMIN_STATE.pop(user_id, None)
            if folder_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO receivers (key, caption) VALUES (?, ?)", (folder_name, f"{folder_name} RECEIVER SOFTWARE"))
                conn.commit()
                conn.close()
                bot.send_message(message.chat.id, f"✅ **{folder_name}** የሚባል አዲስ የሪሲቨር ፎልደር ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
            return

        elif state_data.get("state") == "WAITING_NEW_TV_FOLDER_NAME":
            tv_folder_name = clean_key(text)
            ADMIN_STATE.pop(user_id, None)
            if tv_folder_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO tv_software (key, caption) VALUES (?, ?)", (tv_folder_name, f"{tv_folder_name} TV SOFTWARE"))
                conn.commit()
                conn.close()
                bot.send_message(message.chat.id, f"✅ **{tv_folder_name}** የሚባል አዲስ የቲቪ ፎልደር ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
            return

        elif state_data.get("state") == "WAITING_NEW_SUB_FOLDER":
            target_rcv = state_data["receiver_key"]
            sub_name = text.strip()
            ADMIN_STATE.pop(user_id, None)
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO sub_folders (receiver_key, folder_name) VALUES (?, ?)", (target_rcv, sub_name))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ ሪሲቨር ስር **{sub_name}** የሚባል ንዑስ ፎልደር ተፈጥሯል!", reply_markup=main_menu(user_id, True))
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ ስህተት: {e}")
            conn.close()
            return

        elif state_data.get("state") == "WAITING_FILE_UPLOAD":
            if message.content_type != 'document':
                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
                bot.send_message(message.chat.id, "⚠️ እባክዎ ትክክለኛ ፋይል ወይም ዚፕ (.zip) ፋይል ይላኩ።", reply_markup=markup)
                return

            target_rcv = state_data["target_receiver"]
            sub_id = state_data.get("sub_folder_id", 0)
            file_name = message.document.file_name or "unknown_file.bin"
            file_size_bytes = message.document.file_size or 0
            file_size_str = f"{round(file_size_bytes / (1024 * 1024), 2)} MB" if file_size_bytes > 1024 * 1024 else f"{round(file_size_bytes / 1024, 2)} KB"

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO bin_files (receiver_key, sub_folder_id, file_name, file_id, file_size) VALUES (?, ?, ?, ?, ?)", 
                           (target_rcv, sub_id, file_name, message.document.file_id, file_size_str))
            conn.commit()
            conn.close()

            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("❌ አፕሎድ ጨርሻለሁ (Done)", callback_data="cancel_upload"))
            bot.reply_to(message, f"🔥 **አዲስ ሶፍትዌር ተለቀቀ!**\n📄 ፋይል፦ `{file_name}` ({file_size_str})\n📂 ፎልደር፦ **{target_rcv}**", parse_mode="Markdown", reply_markup=markup)
            return

        elif state_data.get("state") == "WAITING_TV_FILE_UPLOAD":
            if message.content_type != 'document':
                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
                bot.send_message(message.chat.id, "⚠️ እባክዎ ትክክለኛ ፋይል ወይም ዚፕ (.zip) ፋይል ይላኩ።", reply_markup=markup)
                return

            target_tv = state_data["target_tv"]
            file_name = message.document.file_name or "unknown_file.bin"
            file_size_bytes = message.document.file_size or 0
            file_size_str = f"{round(file_size_bytes / (1024 * 1024), 2)} MB" if file_size_bytes > 1024 * 1024 else f"{round(file_size_bytes / 1024, 2)} KB"

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tv_files (tv_key, file_name, file_id, file_size) VALUES (?, ?, ?, ?)", 
                           (target_tv, file_name, message.document.file_id, file_size_str))
            conn.commit()
            conn.close()

            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("❌ አፕሎድ ጨርሻለሁ (Done)", callback_data="cancel_upload"))
            bot.reply_to(message, f"🔥 **አዲስ ቲቪ ሶፍትዌር ተለቀቀ!**\n📄 ፋይል፦ `{file_name}` ({file_size_str})\n📺 ፎልደር፦ **{target_tv}**", parse_mode="Markdown", reply_markup=markup)
            return

    if not is_admin and message.content_type == 'photo':
        user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        photo_id = message.photo[-1].file_id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO payments (user_id, username, file_id, status) VALUES (?, ?, ?, 'PENDING')", 
                       (user_id, user_name, photo_id))
        conn.commit()
        conn.close()

        caption = f"💳 **አዲስ የክፍያ ደረሰኝ ደረሰ!**\n👤 ተጠቃሚ: {user_name}\n🆔 ID: `{user_id}`"
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ አረጋግጥ (Approve)", callback_data=f"pay_approve_{user_id}"),
            InlineKeyboardButton("❌ ውድቅ አድርግ (Reject)", callback_data=f"pay_reject_{user_id}")
        )
        
        try:
            bot.forward_message(SUPER_ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(SUPER_ADMIN_ID, caption, parse_mode="Markdown", reply_markup=markup)
            bot.reply_to(message, "✅ የክፍያ ደረሰኝዎ ለአስተዳዳሪው ተልኳል። እባክዎ ትንሽ ይጠብቁ!")
        except Exception as e:
            logging.error(f"Error forwarding payment: {e}")
            bot.reply_to(message, "⚠️ ደረሰኙን መላክ አልተቻለም። እባክዎ እንደገና ይሞክሩ።")
        return

    if not is_admin and message.content_type != 'text':
        bot.send_message(message.chat.id, "⚠️ እባክዎ የክፍያ ደረሰኝ ፎቶ (Screenshot) ብቻ ይላኩ።")
        return

    register_user(user_id, message.from_user.username)
    is_admin = (user_id == SUPER_ADMIN_ID)
    receivers = get_all_receivers()
    tvs = get_all_tvs()

    if not is_admin and not check_user_joined(user_id):
        channel = get_must_join_channel()
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📢 ቻናላችንን የተቀላቀሉ", url=f"https://t.me/{channel.replace('@', '')}"))
        bot.send_message(message.chat.id, f"⚠️ ቦቱን ለመጠቀም እና ሶፍትዌር ለማውረድ መጀመሪያ ቻናላችንን መቀላቀል አለብዎት።", reply_markup=markup)
        return

    if text in ["🔝 Main Menu", "🔙 Back"]:
        ADMIN_STATE.pop(user_id, None)
        bot.send_message(message.chat.id, "ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, is_admin))
        return

    if "እቃ ለመግዛት" in text:
        bot.send_message(message.chat.id, BUY_ITEM_TEXT, parse_mode="Markdown")
        return

    if "SERVER ለመግዛት" in text:
        bot.send_message(message.chat.id, SERVER_INFO_TEXT, parse_mode="Markdown")
        return

    if "ጓደኛጋብዝ" in text or "Referral" in text:
        bot_info = bot.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        ref_count = get_referral_count(user_id)
        
        ref_msg = (
            f"🎁 **የጓደኛ ማግኛ (Referral) ፕሮግራም**\n\n"
            f"ሰዎችን ወደዚህ ቦት በመጋበዝ የእኛን ማህበረሰብ እንዲያድጉ ያድርጉ!\n\n"
            f"🔗 **የእርስዎ ልዩ የኢንቪቴሽን ሊንክ:**\n`{ref_link}`\n\n"
            f"👥 እስካሁን የጋበዟቸው ሰዎች ብዛት፦ **{ref_count}** ሰው\n\n"
            f"*(ይህንን ሊንክ ለጓደኞችዎ በመላክ ቦቱን እንዲጠቀሙ ጋብዟቸው!)*"
        )
        bot.send_message(message.chat.id, ref_msg, parse_mode="Markdown")
        return

    if text == "🔥 አዲስ የተለቀቁ":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT receiver_key, file_name, file_size, id FROM bin_files WHERE file_id != 'none' ORDER BY id DESC LIMIT 10")
        recent_bin = cursor.fetchall()
        cursor.execute("SELECT tv_key, file_name, file_size, id FROM tv_files ORDER BY id DESC LIMIT 10")
        recent_tv = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        for r_key, f_name, f_size, f_id in recent_bin:
            markup.row(InlineKeyboardButton(f"📁 [{r_key}] {f_name[:18]} ({f_size})", callback_data=f"dl_bin_{f_id}"))
        for t_key, f_name, f_size, f_id in recent_tv:
            markup.row(InlineKeyboardButton(f"📺 [{t_key}] {f_name[:18]} ({f_size})", callback_data=f"dl_tv_{f_id}"))

        if recent_bin or recent_tv:
            bot.send_message(message.chat.id, "🔥 **በቅርብ ጊዜ የተለቀቁ አዳዲስ ሶፍትዌሮች፦**", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ እስካሁን የተለቀቀ አዲስ ፋይል የለም።")
        return

    if user_id in ADMIN_STATE and ADMIN_STATE.get(user_id) == "WAITING_SEARCH":
        ADMIN_STATE.pop(user_id, None)
        query = text.strip().upper()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, receiver_key, file_name, file_size FROM bin_files WHERE (file_name LIKE ? OR receiver_key LIKE ?) AND file_id != 'none' ORDER BY file_name ASC", (f'%{query}%', f'%{query}%'))
        matching_files = cursor.fetchall()
        cursor.execute("SELECT id, tv_key, file_name, file_size FROM tv_files WHERE (file_name LIKE ? OR tv_key LIKE ?) ORDER BY file_name ASC", (f'%{query}%', f'%{query}%'))
        matching_tv_files = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        for f_id, r_key, f_name, f_size in matching_files[:5]:
            markup.row(InlineKeyboardButton(f"📁 [{r_key}] {f_name[:20]} ({f_size})", callback_data=f"dl_bin_{f_id}"))
        for f_id, t_key, f_name, f_size in matching_tv_files[:5]:
            markup.row(InlineKeyboardButton(f"📺 [{t_key}] {f_name[:20]} ({f_size})", callback_data=f"dl_tv_{f_id}"))
            
        if matching_files or matching_tv_files:
            bot.send_message(message.chat.id, f"🔍 **'{query}' በሚለው ፍለጋ የተገኙ ፋይሎች፦**", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ ምንም የተገኘ ፋይል የለም።")
        return

    if "HD RECEIVER" in text:
        bot.send_message(message.chat.id, "♦ ሪሲቨር ፎልደር ይምረጡ፦", reply_markup=receivers_menu())
        return

    if "TV SOFTWARES" in text:
        bot.send_message(message.chat.id, "📺 ቲቪ ብራንድ ይምረጡ፦", reply_markup=tv_menu())
        return

    if "🔍 ፋይል / ሪሲቨር ፈልግ" in text:
        ADMIN_STATE[user_id] = "WAITING_SEARCH"
        bot.send_message(message.chat.id, "🔍 ለመፈለግ የሚፈልጉትን የሶፍትዌር ስም ወይም ሪሲቨር ብራንድ ይጻፉልኝ:")
        return

    if is_admin and "አድሚን ፓነል" in text:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📤 ሪሲቨር ጫን", callback_data="adm_upload_sw"), InlineKeyboardButton("📤 ቲቪ ጫን", callback_data="adm_upload_tv"))
        markup.row(InlineKeyboardButton("📁 ሪሲቨር ፎልደር ፍጠር", callback_data="adm_create_folder"), InlineKeyboardButton("📁 ቲቪ ፎልደር ፍጠር", callback_data="adm_create_tv_folder"))
        markup.row(InlineKeyboardButton("🗑 ሪሲቨር ሰርዝ", callback_data="adm_manage_sw"), InlineKeyboardButton("🗑 ቲቪ ሰርዝ", callback_data="adm_manage_tv"))
        markup.row(InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("⚙️ ቻናል ቀይር", callback_data="adm_set_channel"))
        markup.row(InlineKeyboardButton("💾 Backup", callback_data="adm_backup"), InlineKeyboardButton("📊 ስታቲስቲክስ", callback_data="adm_stats"))
        bot.send_message(message.chat.id, "🛠 **የአስተዳዳሪ ፓነል:**", reply_markup=markup, parse_mode="Markdown")
        return

    if text.startswith("📍 ") or text.startswith("📍"):
        selected_model = text.replace("📍", "").strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM sub_folders WHERE folder_name = ?", (selected_model,))
        sf_row = cursor.fetchone()
        
        if sf_row:
            sf_id = sf_row[0]
            cursor.execute("SELECT file_name, file_id, file_size, downloads_count FROM bin_files WHERE sub_folder_id = ? LIMIT 1", (sf_id,))
            file_row = cursor.fetchone()
        else:
            cursor.execute("SELECT file_name, file_id, file_size, downloads_count FROM bin_files WHERE file_name = ?", (selected_model,))
            file_row = cursor.fetchone()
            
        conn.close()

        if file_row:
            f_name, f_file_id, f_size, d_count = file_row
            if f_file_id and f_file_id != "none":
                new_count = d_count + 1
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE bin_files SET downloads_count = ? WHERE file_name = ? OR sub_folder_id = (SELECT id FROM sub_folders WHERE folder_name = ?)", (new_count, selected_model, selected_model))
                conn.commit()
                conn.close()

                caption = f"✅ **{f_name}**\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ"
                bot.send_document(message.chat.id, f_file_id, caption=caption, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "⚠️ ለዚህ ሞዴል ገና ፋይል አልተጫነም።")
        else:
            bot.send_message(message.chat.id, "⚠️ ፋይሉ አልተገኘም።")
        return

    clean_text = clean_key(text)
    
    if clean_text in receivers:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, folder_name FROM sub_folders WHERE receiver_key = ? ORDER BY folder_name ASC", (clean_text,))
        sub_folders = cursor.fetchall()
        cursor.execute("SELECT id, file_name FROM bin_files WHERE receiver_key = ? AND sub_folder_id = 0 ORDER BY file_name ASC", (clean_text,))
        root_files = cursor.fetchall()
        conn.close()

        keyboard_buttons = []
        for sf_id, sf_name in sub_folders:
            keyboard_buttons.append([KeyboardButton(f"📍 {sf_name}")])

        for f_id, f_name in root_files:
            keyboard_buttons.append([KeyboardButton(f"📍 {f_name}")])

        keyboard_buttons.append([KeyboardButton("🔙 Back"), KeyboardButton("🔝 Main Menu")])
        markup = ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

        if is_admin:
            admin_markup = InlineKeyboardMarkup()
            admin_markup.row(InlineKeyboardButton(f"➕ ንዑስ ፎልደር ፍጠር", callback_data=f"create_sub_{clean_text}"))
            admin_markup.row(InlineKeyboardButton(f"📤 ፋይል ወደዚ ፎልደር ጫን", callback_data=f"upload_to_{clean_text}"))
            bot.send_message(message.chat.id, f"⚙️ **አድሚን አማራጮች ({clean_text}):**", reply_markup=admin_markup, parse_mode="Markdown")

        bot.send_message(message.chat.id, f"🔻 **{clean_text}** ውስጥ ያሉ ሞዴሎችና ፎልደሮች፦", reply_markup=markup, parse_mode="Markdown")
        return

    if clean_text in tvs:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, file_size FROM tv_files WHERE tv_key = ? ORDER BY file_name ASC", (clean_text,))
        files_data = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        for f_id, f_name, f_size in files_data:
            markup.row(InlineKeyboardButton(f"📥 {f_name} ({f_size})", callback_data=f"dl_tv_{f_id}"), InlineKeyboardButton("❌ አጥፋ" if is_admin else "", callback_data=f"del_tv_{f_id}" if is_admin else f"ignore_{f_id}"))
            
        bot.send_message(message.chat.id, f"📺 **{clean_text}** ቲቪ ፎልደር ፋይሎች፦", reply_markup=markup, parse_mode="Markdown")
        return

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_callbacks(call):
    global ADMIN_STATE
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    is_admin = (user_id == SUPER_ADMIN_ID)

    if data.startswith("create_sub_") and is_admin:
        r_key = data.replace("create_sub_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_SUB_FOLDER", "receiver_key": r_key}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"✍️ ለ **{r_key}** የሚሆን አዲስ ንዑስ ፎልደር ስም ይጻፉልኝ:", reply_markup=markup)

    elif data.startswith("upload_to_") and is_admin:
        r_key = data.replace("upload_to_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_FILE_UPLOAD", "target_receiver": r_key, "sub_folder_id": 0}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"📥 ለ **{r_key}** ዋና ፎልደር ፋይል አሁን ይላኩልኝ።", reply_markup=markup)

    elif data == "adm_upload_sw" and is_admin:
        receivers = get_all_receivers()
        markup = InlineKeyboardMarkup()
        for r_key in receivers:
            markup.row(InlineKeyboardButton(f"📁 {r_key}", callback_data=f"upload_to_{r_key}"))
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📤 የየትኛው ሪሲቨር ሶፍትዌር መጫን ይፈልጋሉ?", reply_markup=markup)

    elif data == "adm_upload_tv" and is_admin:
        tvs = get_all_tvs()
        markup = InlineKeyboardMarkup()
        for t_key in tvs:
            markup.row(InlineKeyboardButton(f"📺 {t_key}", callback_data=f"upload_tv_{t_key}"))
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📤 የየትኛው ቲቪ ሶፍትዌር መጫን ይፈልጋሉ?", reply_markup=markup)

    elif data.startswith("upload_tv_") and is_admin:
        t_key = data.replace("upload_tv_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_TV_FILE_UPLOAD", "target_tv": t_key}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"📥 ለ **{t_key}** ቲቪ ፋይል አሁን ይላኩልኝ።", reply_markup=markup)

    elif data == "adm_create_folder" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_FOLDER_NAME"}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, "📁 አዲስ የሪሲቨር ፎልደር ስም ይጻፉልኝ:", reply_markup=markup)

    elif data == "adm_create_tv_folder" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_TV_FOLDER_NAME"}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, "📺 አዲስ ቲቪ ፎልደር ስም ይጻፉልኝ:", reply_markup=markup)

    elif data == "adm_manage_sw" and is_admin:
        receivers = get_all_receivers()
        markup = InlineKeyboardMarkup()
        for r_key in receivers:
            markup.row(InlineKeyboardButton(f"❌ ፎልደር ሰርዝ: {r_key}", callback_data=f"del_folder_{r_key}"))
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🗑 ለመሰረዝ ሪሲቨር ይምረጡ:", reply_markup=markup)

    elif data.startswith("del_folder_") and is_admin:
        r_key = data.replace("del_folder_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bin_files WHERE receiver_key = ?", (r_key,))
        cursor.execute("DELETE FROM sub_folders WHERE receiver_key = ?", (r_key,))
        cursor.execute("DELETE FROM receivers WHERE key = ?", (r_key,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, f"✅ '{r_key}' ተሰርዟል!", show_alert=True)

    elif data == "adm_manage_tv" and is_admin:
        tvs = get_all_tvs()
        markup = InlineKeyboardMarkup()
        for t_key in tvs:
            markup.row(InlineKeyboardButton(f"❌ ፎልደር ሰርዝ: {t_key}", callback_data=f"del_tv_folder_{t_key}"))
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🗑 ለመሰረዝ ቲቪ ፎልደር ይምረጡ:", reply_markup=markup)

    elif data.startswith("del_tv_folder_") and is_admin:
        t_key = data.replace("del_tv_folder_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tv_files WHERE tv_key = ?", (t_key,))
        cursor.execute("DELETE FROM tv_software WHERE key = ?", (t_key,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, f"✅ '{t_key}' ቲቪ ፎልደር ተሰርዟል!", show_alert=True)

    elif data.startswith("del_tv_") and is_admin:
        f_id = data.replace("del_tv_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tv_files WHERE id = ?", (f_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ የቲቪ ፋይሉ ተሰርዟል!", show_alert=True)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass

    elif data == "adm_broadcast" and is_admin:
        ADMIN_STATE[user_id] = "WAITING_BROADCAST"
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, "📢 ለሁሉም ተጠቃሚዎች መላክ የሚፈልጉትን (ፎቶ፣ ቪዲዮ ወይም ጽሑፍ) አሁን ይላኩ:", reply_markup=markup)

    elif data == "adm_set_channel" and is_admin:
        ADMIN_STATE[user_id] = "WAITING_CHANNEL_UPDATE"
        bot.answer_callback_query(call.id)
        current_ch = get_must_join_channel()
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"⚙️ አሁን ያለው ቻናል: `{current_ch}`\n\nአዲሱን የቻናል ዩዘርናም (ለምሳሌ @newchannel) ይጻፉልኝ:", reply_markup=markup)

    elif data == "adm_backup" and is_admin:
        bot.answer_callback_query(call.id, "💾 ባክአፕ በመላክ ላይ...", show_alert=False)
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as db_file:
                bot.send_document(chat_id, db_file, caption="💾 **Database Backup**")

    elif data == "adm_stats" and is_admin:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        u_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM receivers")
        r_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tv_software")
        tv_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM bin_files")
        f_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM payments")
        p_cnt = cursor.fetchone()[0]
        conn.close()
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📊 **አጠቃላይ ስታቲስቲክስ፦**\n\n👥 ተጠቃሚዎች: **{u_cnt}**\n📁 ሪሲቨር ፎልደሮች: **{r_cnt}**\n📺 ቲቪ ፎልደሮች: **{tv_cnt}**\n📄 ፋይሎች/ሞዴሎች: **{f_cnt}**\n💳 የክፍያ ጥያቄዎች: **{p_cnt}**", parse_mode="Markdown")

    elif data.startswith("pay_approve_") and is_admin:
        target_user = data.replace("pay_approve_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status = 'APPROVED' WHERE user_id = ?", (target_user,))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "✅ ክፍያው ጸድቋል")
        try:
            bot.send_message(target_user, "✅ የላኩት የክፍያ ደረሰኝ በአስተዳዳሪው ጸድቋል! እናመሰግናለን።")
            bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **[STATUS: APPROVED]**", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ ተጠቃሚው ጋር መድረስ አልቻለም: {e}")

    elif data.startswith("pay_reject_") and is_admin:
        target_user = data.replace("pay_reject_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE payments SET status = 'REJECTED' WHERE user_id = ?", (target_user,))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "❌ ክፍያው ውድቅ ተደርጓል")
        try:
            bot.send_message(target_user, "❌ የላኩት የክፍያ ደረሰኝ ትክክለኛ ባለመሆኑ ውድቅ ተደርጓል። እባክዎ እንደገና ያረጋግጡ።")
            bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **[STATUS: REJECTED]**", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ ተጠቃሚው ጋር መድረስ አልቻለም: {e}")

    elif data.startswith("dl_bin_"):
        f_id = data.replace("dl_bin_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_id, file_size, downloads_count FROM bin_files WHERE id = ?", (f_id,))
        file_row = cursor.fetchone()
        if file_row:
            f_name, f_id_tg, f_size, d_count = file_row
            if f_id_tg == "none":
                conn.close()
                bot.answer_callback_query(call.id, "ℹ️ ይህ የሞዴል ስም ብቻ ነው", show_alert=True)
                return
            new_count = d_count + 1
            cursor.execute("UPDATE bin_files SET downloads_count = ? WHERE id = ?", (new_count, f_id))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "📥 ፋይሉ በመውረድ ላይ ነው...")
            bot.send_document(chat_id, f_id_tg, caption=f"✅ {f_name}\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ")
        else:
            conn.close()
            bot.answer_callback_query(call.id, "⚠️ ፋይሉ አልተገኘም!", show_alert=True)

    elif data.startswith("dl_tv_"):
        f_id = data.replace("dl_tv_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_id, file_size, downloads_count FROM tv_files WHERE id = ?", (f_id,))
        file_row = cursor.fetchone()
        if file_row:
            f_name, f_id_tg, f_size, d_count = file_row
            new_count = d_count + 1
            cursor.execute("UPDATE tv_files SET downloads_count = ? WHERE id = ?", (new_count, f_id))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "📥 ፋይሉ በመውረድ ላይ ነው...")
            bot.send_document(chat_id, f_id_tg, caption=f"✅ {f_name}\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ")
        else:
            conn.close()
            bot.answer_callback_query(call.id, "⚠️ ፋይሉ አልተገኘም!", show_alert=True)

    elif data == "cancel_upload":
        ADMIN_STATE.pop(user_id, None)
        bot.answer_callback_query(call.id, "✅ ተሰርዟል!", show_alert=True)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, "ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, True))

bot.infinity_polling()
