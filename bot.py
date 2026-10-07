import os
import sqlite3
import logging
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
PHOTO_FILE_ID = os.environ.get("PHOTO_FILE_ID", "YOUR_PHOTO_FILE_ID_HERE")

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
    
    try:
        cursor.execute("ALTER TABLE bin_files ADD COLUMN sub_folder_id INTEGER DEFAULT 0")
    except Exception:
        pass

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
    for char in ["🔹", "🔷", "✨", "🛒", "💻", "📚", "⭐", "🔥", "🔍", "⏱", "❓", "🌐", "⚙", "📺", "📌", "📁", "📂", "🔲"]:
        text = text.replace(char, "")
    return text.strip().replace(" ", "_").upper()

def get_all_receivers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key FROM receivers")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_all_tvs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key FROM tv_software")
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
    buttons = [
        KeyboardButton("🔲 CORONATE"),
        KeyboardButton("🔲 FREE SAT"),
        KeyboardButton("🔲 GOLDSTAR"),
        KeyboardButton("🔲 LEG"),
        KeyboardButton("🔲 LIFESTARE"),
        KeyboardButton("🔲 MEWE"),
        KeyboardButton("🔲 SUPERMAX"),
        KeyboardButton("🔲 TIGER")
    ]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.row(KeyboardButton("🔙 Back"), KeyboardButton("🔝 Main Menu"))
    return markup

def tv_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    tvs = get_all_tvs()
    buttons = [KeyboardButton(f"📺 {name.replace('_', ' ')}") for name in tvs]
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
    
    welcome_text = "✨ ሰላም! እንኳን ወደ ሪሲቨር እና ቲቪ ሶፍትዌር ማከማቻ ቦት በደህና መጡ።"
    try:
        bot.send_photo(message.chat.id, PHOTO_FILE_ID, caption=welcome_text, reply_markup=main_menu(user_id, is_admin), parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(user_id, is_admin), parse_mode="Markdown")

@bot.message_handler(content_types=['document', 'photo', 'video', 'text'])
def handle_all_messages(message):
    global ADMIN_STATE
    user_id = message.from_user.id
    is_admin = (user_id == SUPER_ADMIN_ID)
    text = message.text or ""

    clean_msg = text.strip().lower()
    if clean_msg.startswith("supre"):
        clean_msg = clean_msg.replace("supre", "")

    if clean_msg.isdigit():
        f_id = int(clean_msg)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_size, file_id, downloads_count FROM bin_files WHERE id = ?", (f_id,))
        row = cursor.fetchone()
        
        if row:
            f_name, f_size, f_file_id, d_count = row
            new_count = d_count + 1
            cursor.execute("UPDATE bin_files SET downloads_count = ? WHERE id = ?", (new_count, f_id))
            conn.commit()
            conn.close()

            try:
                bot.send_document(message.chat.id, f_file_id, caption=f"✅ ፋይል፦ `{f_name}`\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Error auto-sending file: {e}")
                bot.reply_to(message, "⚠️ ፋይሉን ማስተላለፍ አልተቻለም።")
        else:
            conn.close()
            bot.reply_to(message, f"⚠️ በ ID ({f_id}) የተመዘገበ ፋይል አልተገኘም!")
        return

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

    if is_admin and user_id in ADMIN_STATE and isinstance(ADMIN_STATE.get(user_id), dict):
        state_data = ADMIN_STATE[user_id]
        
        if state_data.get("state") == "WAITING_NEW_RECEIVER":
            rcv_name = text.strip().upper()
            ADMIN_STATE.pop(user_id, None)
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR IGNORE INTO receivers (key, caption) VALUES (?, ?)", (rcv_name, f"{rcv_name} RECEIVER SOFTWARE"))
                conn.commit()
                bot.send_message(message.chat.id, f"📁 **{rcv_name}** አዲስ የሪሲቨር ፎልደር ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ ስህተት: {e}")
            conn.close()
            return

        elif state_data.get("state") == "WAITING_SUB_FOLDER_NAME":
            target_rcv = state_data["receiver_key"]
            sub_name = text.strip()
            ADMIN_STATE.pop(user_id, None)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sub_folders (receiver_key, folder_name) VALUES (?, ?)", (target_rcv, sub_name))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"📂 ለ **{target_rcv}** የሚሆን **{sub_name}** ንዑስ ፎልደር ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
            return

        elif state_data.get("state") == "WAITING_NEW_CHANNEL":
            new_channel = text.strip()
            if not new_channel.startswith("@"):
                new_channel = "@" + new_channel
            ADMIN_STATE.pop(user_id, None)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET value = ? WHERE key = 'must_join_channel'", (new_channel,))
            conn.commit()
            conn.close()
            
            bot.send_message(message.chat.id, f"✅ ቻናሉ በተሳካ ሁኔታ ወደ **{new_channel}** ተቀይሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
            return

        elif state_data.get("state") == "WAITING_FILE_UPLOAD":
            if message.content_type != 'document':
                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
                bot.send_message(message.chat.id, "⚠️ እባክዎ ትክክለኛ የሶፍትዌር ፋይል (Document) ይላኩ።", reply_markup=markup)
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

            ADMIN_STATE.pop(user_id, None)

            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("❌ አፕሎድ ጨርሻለሁ (Done)", callback_data="cancel_upload"))
            bot.reply_to(message, f"🔥 **አዲስ ሪሲቨር ሶፍትዌር ተጫነ!**\n📄 ፋይል፦ `{file_name}` ({file_size_str})\n📂 ፎልደር፦ **{target_rcv}**", parse_mode="Markdown", reply_markup=markup)
            return

        elif state_data.get("state") == "WAITING_TV_UPLOAD":
            if message.content_type != 'document':
                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
                bot.send_message(message.chat.id, "⚠️ እባክዎ ትክክለኛ የቲቪ ሶፍትዌር ፋይል (Document) ይላኩ።", reply_markup=markup)
                return

            target_tv = state_data["tv_key"]
            file_name = message.document.file_name or "tv_software.bin"
            file_size_bytes = message.document.file_size or 0
            file_size_str = f"{round(file_size_bytes / (1024 * 1024), 2)} MB" if file_size_bytes > 1024 * 1024 else f"{round(file_size_bytes / 1024, 2)} KB"

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tv_files (tv_key, file_name, file_id, file_size) VALUES (?, ?, ?, ?)", 
                           (target_tv, file_name, message.document.file_id, file_size_str))
            conn.commit()
            conn.close()
            
            ADMIN_STATE.pop(user_id, None)
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🔝 ወደ ዋናው ማውጫ", callback_data="cancel_upload"))
            bot.reply_to(message, f"📺 **አዲስ ቲቪ ሶፍትዌር ተጫነ!**\n📄 ፋይል፦ `{file_name}` ({file_size_str})\n🏷 ብራንድ፦ **{target_tv}**", parse_mode="Markdown", reply_markup=markup)
            return

        elif state_data.get("state") == "WAITING_NEW_TV_BRAND":
            tv_name = text.strip().upper()
            ADMIN_STATE.pop(user_id, None)
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR IGNORE INTO tv_software (key, caption) VALUES (?, ?)", (tv_name, f"{tv_name} TV SOFTWARE"))
                conn.commit()
                bot.send_message(message.chat.id, f"📺 **{tv_name}** አዲስ የቲቪ ብራንድ ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ ስህተት: {e}")
            conn.close()
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
        try:
            bot.send_photo(message.chat.id, PHOTO_FILE_ID, caption="ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, is_admin), parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, "ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, is_admin))
        return

    if "እቃ ለመግዛት" in text:
        try:
            bot.send_photo(message.chat.id, PHOTO_FILE_ID, caption=BUY_ITEM_TEXT, parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, BUY_ITEM_TEXT, parse_mode="Markdown")
        return

    if "SERVER ለመግዛት" in text:
        try:
            bot.send_photo(message.chat.id, PHOTO_FILE_ID, caption=SERVER_INFO_TEXT, parse_mode="Markdown")
        except Exception:
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
        try:
            bot.send_photo(message.chat.id, PHOTO_FILE_ID, caption=ref_msg, parse_mode="Markdown")
        except Exception:
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

    if "HD RECEIVER" in text:
        bot.send_message(message.chat.id, "📁 ሪሲቨር ፎልደር ይምረጡ፦", reply_markup=receivers_menu())
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

    clean_text = clean_key(text)
    
    if clean_text in receivers:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, folder_name FROM sub_folders WHERE receiver_key = ?", (clean_text,))
        sub_folders = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        if is_admin:
            markup.row(InlineKeyboardButton("➕ ንዑስ ፎልደር ፍጠር", callback_data=f"create_sub_{clean_text}"))

        sub_buttons = [InlineKeyboardButton(f"{sf_name}", callback_data=f"open_sub_{sf_id}") for sf_id, sf_name in sub_folders]
        for i in range(0, len(sub_buttons), 2):
            markup.row(*sub_buttons[i:i+2])

        bot.send_message(message.chat.id, f"📂 **{clean_text} ፎልደሮች፦**", reply_markup=markup, parse_mode="Markdown")
        return

    if clean_text in tvs:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, file_size FROM tv_files WHERE tv_key = ? ORDER BY id DESC", (clean_text,))
        files_data = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        for f_id, f_name, f_size in files_data:
            if is_admin:
                markup.row(
                    InlineKeyboardButton(f"{f_name} ({f_size})", callback_data=f"dl_tv_{f_id}"),
                    InlineKeyboardButton("❌ አጥፋ", callback_data=f"del_tv_{f_id}")
                )
            else:
                markup.row(InlineKeyboardButton(f"{f_name} ({f_size})", callback_data=f"dl_tv_{f_id}"))
            
        bot.send_message(message.chat.id, f"📺 **{clean_text}** ቲቪ ፋይሎች፦", reply_markup=markup, parse_mode="Markdown")
        return

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_callbacks(call):
    global ADMIN_STATE
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    is_admin = (user_id == SUPER_ADMIN_ID)

    if data == "adm_upload_sw" and is_admin:
        receivers = get_all_receivers()
        markup = InlineKeyboardMarkup()
        for r in receivers:
            markup.row(InlineKeyboardButton(f"📁 {r}", callback_data=f"rcv_up_target_{r}"))
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📁 ፋይሉ የሚጫንበትን የሪሲቨር ብራንድ ይምረጡ፦", reply_markup=markup)
        return

    if data == "adm_set_channel" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_CHANNEL"}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.send_message(chat_id, "⚙️ አዲስ ማካተት/መቀየር የሚፈልጉትን የቻናል ዩዘርናም (ለምሳሌ: `@your_channel`) ጽሁፍ ልከው ያስመዝግቡ:", reply_markup=markup)
        return

    if data.startswith("rcv_up_target_") and is_admin:
        rcv_key = data.replace("rcv_up_target_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, folder_name FROM sub_folders WHERE receiver_key = ?", (rcv_key,))
        subs = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(f"📁 ዋናው ፎልደር ({rcv_key})", callback_data=f"do_upload_bin_{rcv_key}_0"))
        for s_id, s_name in subs:
            markup.row(InlineKeyboardButton(f"📂 {s_name}", callback_data=f"do_upload_bin_{rcv_key}_{s_id}"))
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))

        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📂 ለ **{rcv_key}** ፋይሉ የሚቀመጥበትን ንዑስ ፎልደር ይምረጡ (ወይም ዋናውን ይጫኑ):", reply_markup=markup, parse_mode="Markdown")
        return

    if data.startswith("do_upload_bin_") and is_admin:
        parts = data.replace("do_upload_bin_", "").rsplit("_", 1)
        rcv_key = parts[0]
        sub_id = int(parts[1])
        
        ADMIN_STATE[user_id] = {"state": "WAITING_FILE_UPLOAD", "target_receiver": rcv_key, "sub_folder_id": sub_id}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"📥 ለ **{rcv_key}** ሶፍትዌር ፋይሉን (Document) አሁን ይላኩልኝ።", reply_markup=markup, parse_mode="Markdown")
        return

    if data == "adm_create_folder" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_RECEIVER"}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"✍️ አዲስ መፍጠር የሚፈልጉትን የሪሲቨር ብራንድ ስም (ለምሳሌ STARX) ጽሁፍ ልከው ያስመዝግቡ:", reply_markup=markup)
        return

    if data.startswith("create_sub_") and is_admin:
        rcv_key = data.replace("create_sub_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_SUB_FOLDER_NAME", "receiver_key": rcv_key}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"✍️ ለ **{rcv_key}** የሚሆን አዲስ ንዑስ ፎልደር ስም (ለምሳሌ: Version 2) ጽሁፍ ልከው ያስመዝግቡ:", reply_markup=markup)
        return

    if data == "adm_manage_sw" and is_admin:
        receivers = get_all_receivers()
        markup = InlineKeyboardMarkup()
        for r in receivers:
            markup.row(InlineKeyboardButton(f"🗑 {r} ፋይሎች ማስተዳደሪያ", callback_data=f"rcv_manage_target_{r}"))
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🗑 ፋይሎቹን ለማየት እና ለመሰረዝ የሪሲቨር ብራንዱን ይምረጡ፦", reply_markup=markup)
        return

    if data.startswith("rcv_manage_target_") and is_admin:
        rcv_key = data.replace("rcv_manage_target_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, file_size FROM bin_files WHERE receiver_key = ? ORDER BY id DESC", (rcv_key,))
        files = cursor.fetchall()
        conn.close()

        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for f_id, f_name, f_size in files:
            markup.row(
                InlineKeyboardButton(f"{f_name} ({f_size})", callback_data=f"dl_bin_{f_id}"),
                InlineKeyboardButton("❌ አጥፋ", callback_data=f"del_bin_{f_id}")
            )
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        if files:
            bot.send_message(chat_id, f"🗑 **{rcv_key}** ፋይሎች ዝርዝር (ለመሰረዝ ❌ አጥፋ የሚለውን ይጫኑ):", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ በ **{rcv_key}** ስር የተጫነ ፋይል የለም።", reply_markup=markup)
        return

    if data.startswith("del_bin_") and is_admin:
        f_id = data.replace("del_bin_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bin_files WHERE id = ?", (f_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ ሪሲቨር ሶፍትዌሩ ተሰርዟል!", show_alert=True)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        return

    if data.startswith("open_sub_"):
        sub_id = data.replace("open_sub_", "")
        bot.answer_callback_query(call.id, "📥 ፋይሉ በመውረድ ላይ ነው...")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_name, file_size, file_id, downloads_count FROM bin_files WHERE sub_folder_id = ? ORDER BY id DESC", (sub_id,))
            files = cursor.fetchall()
            conn.close()

            if files:
                for f_id, f_name, f_size, f_file_id, d_count in files:
                    new_count = d_count + 1
                    
                    conn_update = get_db_connection()
                    cur_update = conn_update.cursor()
                    cur_update.execute("UPDATE bin_files SET downloads_count = ? WHERE id = ?", (new_count, f_id))
                    conn_update.commit()
                    conn_update.close()

                    bot.send_document(chat_id, f_file_id, caption=f"✅ ፋይል፦ `{f_name}`\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "⚠️ በዚህ ፎልደር ስር ምንም ፋይል አልተገኘም!")
        except Exception as e:
            logging.error(f"Error auto-sending subfolder files: {e}")
            bot.send_message(chat_id, f"⚠️ ፋይሉን በሚልክበት ጊዜ ስህተት ተፈጥሯል: {e}")
        return

    if data == "adm_upload_tv" and is_admin:
        tvs = get_all_tvs()
        markup = InlineKeyboardMarkup()
        for t in tvs:
            markup.row(InlineKeyboardButton(f"📺 {t}", callback_data=f"tv_up_target_{t}"))
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📺 ፋይሉ የሚጫንበትን የቲቪ ብራንድ ይምረጡ፦", reply_markup=markup)
        return

    if data.startswith("tv_up_target_") and is_admin:
        tv_key = data.replace("tv_up_target_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_TV_UPLOAD", "tv_key": tv_key}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back (ሰርዝ)", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"📥 ለ **{tv_key}** ቲቪ ሶፍትዌር ፋይሉን (Document) አሁን ይላኩልኝ።", reply_markup=markup, parse_mode="Markdown")
        return

    if data == "adm_create_tv_folder" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_TV_BRAND"}
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.send_message(chat_id, f"✍️ አዲስ መፍጠር የሚፈልጉትን የቲቪ ብራንድ ስም (ለምሳሌ SONY) ጽሁፍ ልከው ያስመዝግቡ:", reply_markup=markup)
        return

    if data == "adm_manage_tv" and is_admin:
        tvs = get_all_tvs()
        markup = InlineKeyboardMarkup()
        for t in tvs:
            markup.row(InlineKeyboardButton(f"🗑 {t} ፋይሎች ማስተዳደሪያ", callback_data=f"tv_manage_target_{t}"))
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🗑 ፋይሎቹን ለማየት እና ለመሰረዝ የቲቪ ብራንዱን ይምረጡ፦", reply_markup=markup)
        return

    if data.startswith("tv_manage_target_") and is_admin:
        tv_key = data.replace("tv_manage_target_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, file_size FROM tv_files WHERE tv_key = ? ORDER BY id DESC", (tv_key,))
        files = cursor.fetchall()
        conn.close()

        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for f_id, f_name, f_size in files:
            markup.row(
                InlineKeyboardButton(f"{f_name} ({f_size})", callback_data=f"dl_tv_{f_id}"),
                InlineKeyboardButton("❌ አጥፋ", callback_data=f"del_tv_{f_id}")
            )
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="cancel_upload"))
        if files:
            bot.send_message(chat_id, f"🗑 **{tv_key}** ፋይሎች ዝርዝር (ለመሰረዝ ❌ አጥፋ የሚለውን ይጫኑ):", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ በ **{tv_key}** ስር የተጫነ ፋይል የለም።", reply_markup=markup)
        return

    if data.startswith("del_tv_") and is_admin:
        f_id = data.replace("del_tv_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tv_files WHERE id = ?", (f_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ ቲቪ ሶፍትዌሩ ተሰርዟል!", show_alert=True)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        return

    if data.startswith("dl_bin_"):
        f_id = data.replace("dl_bin_", "")
        bot.answer_callback_query(call.id, "📥 ፋይሉ በመውረድ ላይ ነው...")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_name, file_size, file_id, downloads_count FROM bin_files WHERE id = ?", (f_id,))
            row = cursor.fetchone()
            
            if row:
                f_name, f_size, f_file_id, d_count = row
                new_count = d_count + 1
                cursor.execute("UPDATE bin_files SET downloads_count = ? WHERE id = ?", (new_count, f_id))
                conn.commit()
                conn.close()

                bot.send_document(chat_id, f_file_id, caption=f"✅ ፋይል፦ `{f_name}`\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ", parse_mode="Markdown")
            else:
                conn.close()
                bot.send_message(chat_id, f"⚠️ በ ID ({f_id}) የተመዘገበ ፋይል በሰርቨር ዳታቤዝ ውስጥ አልተገኘም!")
        except Exception as e:
            logging.error(f"Error in dl_bin_: {e}")
            bot.send_message(chat_id, f"⚠️ ፋይሉን በሚልክበት ጊዜ ስህተት ተፈጥሯል: {e}")
        return

    if data.startswith("dl_tv_"):
        f_id = data.replace("dl_tv_", "")
        bot.answer_callback_query(call.id, "📥 ቲቪ ሶፍትዌር በመውረድ ላይ ነው...")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_name, file_size, file_id, downloads_count FROM tv_files WHERE id = ?", (f_id,))
            row = cursor.fetchone()
            
            if row:
                f_name, f_size, f_file_id, d_count = row
                new_count = d_count + 1
                cursor.execute("UPDATE tv_files SET downloads_count = ? WHERE id = ?", (new_count, f_id))
                conn.commit()
                conn.close()

                bot.send_document(chat_id, f_file_id, caption=f"✅ ቲቪ ሶፍትዌር፦ `{f_name}`\n📦 መጠን: {f_size}\n📥 የወረደበት ብዛት: {new_count} ጊዜ", parse_mode="Markdown")
            else:
                conn.close()
                bot.send_message(chat_id, f"⚠️ በ ID ({f_id}) የተመዘገበ የቲቪ ፋይል አልተገኘም!")
        except Exception as e:
            logging.error(f"Error in dl_tv_: {e}")
            bot.send_message(chat_id, f"⚠️ ፋይሉን በሚልክበት ጊዜ ስህተት ተፈጥሯል: {e}")
        return

    if data == "cancel_upload":
        ADMIN_STATE.pop(user_id, None)
        bot.answer_callback_query(call.id, "✅ ተሰርዟል!", show_alert=True)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        try:
            bot.send_photo(chat_id, PHOTO_FILE_ID, caption="ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, "ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, True))

bot.infinity_polling()
