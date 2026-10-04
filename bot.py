import sqlite3
import datetime
import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8968437244:AAHVhzoCY5weI1UGeVj5pMpbgilQbLbzI54"  # 👈 የቦትዎን ቶከን እዚህ ያስገቡ
SUPER_ADMIN_ID = 596243071  # 👈 የራስዎን የቴሌግራም ID እዚህ ያስገቡ
MUST_JOIN_CHANNEL = "@kerim20000"  # 👈 የቻናልዎን ዩዘርኔም እዚህ ያስገቡ (ለምሳሌ @MySatSoftware)

bot = telebot.TeleBot(TOKEN)
SERVER_INFO_TEXT = "🔷 የሰርቨር አገልግሎት መረጃ: በቴሌብር 150 ብር በመክፈል ያድሱ። ከክፍያ በኋላ ደረሰኙን (Screenshot) በዚህ ቦት ይላኩ።"
ADMIN_STATE = {}

def init_db():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS receivers (key TEXT PRIMARY KEY, caption TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tv_software (key TEXT PRIMARY KEY, caption TEXT)")  # 👈 ለቲቪ ሶፍትዌር የተሰራ ሠንጠረዥ
    cursor.execute("CREATE TABLE IF NOT EXISTS bin_files (id INTEGER PRIMARY KEY AUTOINCREMENT, receiver_key TEXT, file_name TEXT, file_id TEXT, file_size TEXT, downloads_count INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tv_files (id INTEGER PRIMARY KEY AUTOINCREMENT, tv_key TEXT, file_name TEXT, file_id TEXT, file_size TEXT, downloads_count INTEGER DEFAULT 0)")  # 👈 ለቲቪ ፋይሎች
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, receiver_key TEXT, PRIMARY KEY (user_id, receiver_key))")
    cursor.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, photo_id TEXT, status TEXT DEFAULT 'PENDING')")

    # ነባሪ የሪሲቨር ፎልደሮች
    default_receivers = [
        "FREE_SAT", "CORONATE", "MEWE", "TIGER", 
        "LIFESTARE", "SUPERMAX", "GOLDSTAR", "LEG"
    ]
    for key in default_receivers:
        cursor.execute("INSERT OR IGNORE INTO receivers (key, caption) VALUES (?, ?)", (key, f"{key} RECEIVER SOFTWARE"))

    # ነባሪ የቲቪ ፎልደሮች
    default_tvs = [
        "SAMSUNG", "LG", "HISENSE", "TCL", "TOAST", "SKYWORTH"
    ]
    for key in default_tvs:
        cursor.execute("INSERT OR IGNORE INTO tv_software (key, caption) VALUES (?, ?)", (key, f"{key} TV SOFTWARE"))

    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("bot_database.db", check_same_thread=False)

def register_user(user_id, username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def check_user_joined(user_id):
    if not MUST_JOIN_CHANNEL or MUST_JOIN_CHANNEL == "@your_channel_username":
        return True
    try:
        member = bot.get_chat_member(MUST_JOIN_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except Exception:
        return True
    return False

def clean_key(text):
    for char in ["🔹", "🔷", "✨", "🛒", "💻", "📚", "⭐", "🔥", "🔍", "⏱", "❓", "🌐", "⚙", "📺"]:
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
    markup.row(KeyboardButton("📺 📚 TV SOFTWARES 📚 📺"))  # 👈 አዲሱ የቲቪ ሶፍትዌር ሜኑ ከHD Receiver በታች ተጨመረ
    markup.row(KeyboardButton("⭐ የእኔ ተወዳጆች"), KeyboardButton("🔥 አዲስ የተለቀቁ"))
    markup.row(KeyboardButton("🔍 ሪሲቨር ፈልግ"))
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
    register_user(user_id, message.from_user.username)
    is_admin = (user_id == SUPER_ADMIN_ID)
    bot.send_message(message.chat.id, "ሰላም! እንኳን ወደ ሪሲቨር እና ቲቪ ሶፍትዌር ማከማቻ ቦት በደህና መጡ።", reply_markup=main_menu(user_id, is_admin))

# 1. የዶክመንት አፕሎድ መቆጣጠሪያ
@bot.message_handler(content_types=['document'])
def handle_documents(message):
    global ADMIN_STATE
    user_id = message.from_user.id
    is_admin = (user_id == SUPER_ADMIN_ID)

    if is_admin and user_id in ADMIN_STATE and isinstance(ADMIN_STATE[user_id], dict):
        state_data = ADMIN_STATE[user_id]
        file_id = message.document.file_id
        file_name = message.document.file_name or "unknown_file.bin"
        file_size_bytes = message.document.file_size or 0
        file_size_str = f"{round(file_size_bytes / (1024 * 1024), 2)} MB" if file_size_bytes > 1024 * 1024 else f"{round(file_size_bytes / 1024, 2)} KB"

        conn = get_db_connection()
        cursor = conn.cursor()

        if state_data.get("state") == "WAITING_FILE_UPLOAD":
            target_rcv = state_data["target_receiver"]
            cursor.execute("INSERT INTO bin_files (receiver_key, file_name, file_id, file_size) VALUES (?, ?, ?, ?)", 
                           (target_rcv, file_name, file_id, file_size_str))
            conn.commit()
            conn.close()

            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("❌ አፕሎድ ጨርሻለሁ (Done)", callback_data="cancel_upload"))
            bot.reply_to(message, f"✅ **ተሳክቷል!**\n📄 ፋይል፦ `{file_name}` ({file_size_str})\n📂 ሪሲቨር ፎልደር፦ **{target_rcv}**", parse_mode="Markdown", reply_markup=markup)

        elif state_data.get("state") == "WAITING_TV_FILE_UPLOAD":
            target_tv = state_data["target_tv"]
            cursor.execute("INSERT INTO tv_files (tv_key, file_name, file_id, file_size) VALUES (?, ?, ?, ?)", 
                           (target_tv, file_name, file_id, file_size_str))
            conn.commit()
            conn.close()

            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("❌ አፕሎድ ጨርሻለሁ (Done)", callback_data="cancel_upload"))
            bot.reply_to(message, f"✅ **ተሳክቷል!**\n📄 ፋይል፦ `{file_name}` ({file_size_str})\n📺 ቲቪ ፎልደር፦ **{target_tv}**", parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⚠️ ፋይል ለመጫን መጀመሪያ ከአድሚን ፓነል ውስጥ ፎልደር ይምረጡ።")

# 2. የጽሁፍ መልእክቶች መቆጣጠሪያ
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    global ADMIN_STATE
    user_id = message.from_user.id
    register_user(user_id, message.from_user.username)
    text = message.text
    is_admin = (user_id == SUPER_ADMIN_ID)
    receivers = get_all_receivers()
    tvs = get_all_tvs()

    if not is_admin and not check_user_joined(user_id):
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📢 ቻናላችንን የተቀላቀሉ", url=f"https://t.me/{MUST_JOIN_CHANNEL.replace('@', '')}"))
        bot.send_message(message.chat.id, f"⚠️ ቦቱን ለመጠቀም እና ሶፍትዌር ለማውረድ መጀመሪያ ቻናላችንን መቀላቀል አለብዎት።", reply_markup=markup)
        return

    if text in ["🔝 Main Menu", "🔙 Back"]:
        ADMIN_STATE.pop(user_id, None)
        bot.send_message(message.chat.id, "ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, is_admin))
        return

    # አዲስ ሪሲቨር ፎልደር መፍጠር
    if is_admin and user_id in ADMIN_STATE and isinstance(ADMIN_STATE.get(user_id), dict) and ADMIN_STATE[user_id].get("state") == "WAITING_NEW_FOLDER_NAME":
        ADMIN_STATE.pop(user_id, None)
        new_key = text.strip().upper().replace(" ", "_")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO receivers (key, caption) VALUES (?, ?)", (new_key, f"{new_key} RECEIVER SOFTWARE"))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ አዲስ ሪሲቨር ፎልደር **{new_key}** ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, "⚠️ ይህ ስም ያለው ፎልደር አለ።")
        conn.close()
        return

    # አዲስ ቲቪ ፎልደር መፍጠር
    if is_admin and user_id in ADMIN_STATE and isinstance(ADMIN_STATE.get(user_id), dict) and ADMIN_STATE[user_id].get("state") == "WAITING_NEW_TV_FOLDER_NAME":
        ADMIN_STATE.pop(user_id, None)
        new_key = text.strip().upper().replace(" ", "_")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO tv_software (key, caption) VALUES (?, ?)", (new_key, f"{new_key} TV SOFTWARE"))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ አዲስ ቲቪ ፎልደር **{new_key}** ተፈጥሯል!", reply_markup=main_menu(user_id, True), parse_mode="Markdown")
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, "⚠️ ይህ ስም ያለው ቲቪ ፎልደር አለ።")
        conn.close()
        return

    # ብሮድካስት
    if is_admin and user_id in ADMIN_STATE and ADMIN_STATE.get(user_id) == "WAITING_BROADCAST_MSG":
        ADMIN_STATE.pop(user_id, None)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        
        count = 0
        for u in users:
            try:
                bot.send_message(u[0], f"📢 **የአድሚን መልእክት፦**\n\n{text}", parse_mode="Markdown")
                count += 1
            except Exception:
                pass
        bot.send_message(message.chat.id, f"✅ መልእክቱ ለ **{count}** ተጠቃሚዎች ተልኳል!")
        return

    # ፍለጋ
    if user_id in ADMIN_STATE and ADMIN_STATE.get(user_id) == "WAITING_SEARCH":
        ADMIN_STATE.pop(user_id, None)
        query = text.strip().upper()
        matching_rcv = [r for r in receivers if query in r]
        matching_tv = [t for t in tvs if query in t]
        
        markup = InlineKeyboardMarkup()
        for m in matching_rcv:
            markup.row(InlineKeyboardButton(f"📁 ሪሲቨር: {m}", callback_data=f"get_rcv_{m}"))
        for m in matching_tv:
            markup.row(InlineKeyboardButton(f"📺 ቲቪ: {m}", callback_data=f"get_tv_{m}"))
            
        if matching_rcv or matching_tv:
            bot.send_message(message.chat.id, "🔍 **የተገኙ ውጤቶች፦**", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ ምንም የተገኘ ፋይል የለም።")
        return

    if "HD RECEIVER" in text:
        bot.send_message(message.chat.id, "♦️ ሪሲቨር ፎልደር ይምረጡ፦", reply_markup=receivers_menu())
        return

    if "TV SOFTWARES" in text:
        bot.send_message(message.chat.id, "📺 ቲቪ ብራንድ ይምረጡ፦", reply_markup=tv_menu())
        return

    if "SERVER ለመግዛት" in text:
        bot.send_message(message.chat.id, SERVER_INFO_TEXT)
        return

    if "🔍 ሪሲቨር ፈልግ" in text:
        ADMIN_STATE[user_id] = "WAITING_SEARCH"
        bot.send_message(message.chat.id, "🔍 ለመፈለግ የሚፈልጉትን ስም ይጻፉልኝ፦")
        return

    if is_admin and "አድሚን ፓነል" in text:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📤 ሪሲቨር ሶፍትዌር ጫን", callback_data="adm_upload_sw"), InlineKeyboardButton("📤 ቲቪ ሶፍትዌር ጫን", callback_data="adm_upload_tv"))
        markup.row(InlineKeyboardButton("📁 ሪሲቨር ፎልደር ፍጠር", callback_data="adm_create_folder"), InlineKeyboardButton("📁 ቲቪ ፎልደር ፍጠር", callback_data="adm_create_tv_folder"))
        markup.row(InlineKeyboardButton("🗑 ሪሲቨር ሰርዝ", callback_data="adm_manage_sw"), InlineKeyboardButton("🗑 ቲቪ ሰርዝ", callback_data="adm_manage_tv"))
        markup.row(InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("💾 Backup", callback_data="adm_backup"))
        markup.row(InlineKeyboardButton("📊 ስታቲስቲክስ", callback_data="adm_stats"))
        bot.send_message(message.chat.id, "🛠 **የአስተዳዳሪ ፓነል:**", reply_markup=markup, parse_mode="Markdown")
        return

    clean_text = clean_key(text)
    
    # ሪሲቨር ፋይል መላክ
    if clean_text in receivers:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_id, file_size FROM bin_files WHERE receiver_key = ? ORDER BY id DESC LIMIT 1", (clean_text,))
        file_data = cursor.fetchone()
        conn.close()

        if file_data:
            bot.send_document(message.chat.id, file_data[1], caption=f"✅ {file_data[0]}\n📦 መጠን: {file_data[2]}")
        else:
            bot.send_message(message.chat.id, f"⚠️ ለ **{clean_text}** የተጫነ ሶፍትዌር የለም።")
        return

    # ቲቪ ፋይል መላክ
    if clean_text in tvs:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_id, file_size FROM tv_files WHERE tv_key = ? ORDER BY id DESC LIMIT 1", (clean_text,))
        file_data = cursor.fetchone()
        conn.close()

        if file_data:
            bot.send_document(message.chat.id, file_data[1], caption=f"✅ {file_data[0]}\n📦 መጠን: {file_data[2]}")
        else:
            bot.send_message(message.chat.id, f"⚠️️ ለ **{clean_text}** ቲቪ የተጫነ ሶፍትዌር የለም።")
        return

# 3. የኢንላይን አዝራሮች መቆጣጠሪያ
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
        for r_key in receivers:
            markup.row(InlineKeyboardButton(f"📁 {r_key}", callback_data=f"upload_to_{r_key}"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📤 የየትኛው ሪሲቨር ሶፍትዌር መጫን ይፈልጋሉ?", reply_markup=markup)

    elif data.startswith("upload_to_") and is_admin:
        r_key = data.replace("upload_to_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_FILE_UPLOAD", "target_receiver": r_key}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📥 ለ **{r_key}** ፋይል አሁን ይላኩልኝ።")

    elif data == "adm_upload_tv" and is_admin:
        tvs = get_all_tvs()
        markup = InlineKeyboardMarkup()
        for t_key in tvs:
            markup.row(InlineKeyboardButton(f"📺 {t_key}", callback_data=f"upload_tv_{t_key}"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📤 የየትኛው ቲቪ ሶፍትዌር መጫን ይፈልጋሉ?", reply_markup=markup)

    elif data.startswith("upload_tv_") and is_admin:
        t_key = data.replace("upload_tv_", "")
        ADMIN_STATE[user_id] = {"state": "WAITING_TV_FILE_UPLOAD", "target_tv": t_key}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📥 ለ **{t_key}** ቲቪ ፋይል አሁን ይላኩልኝ።")

    elif data == "adm_create_folder" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_FOLDER_NAME"}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📁 አዲስ የሪሲቨር ፎልደር ስም ይጻፉልኝ:")

    elif data == "adm_create_tv_folder" and is_admin:
        ADMIN_STATE[user_id] = {"state": "WAITING_NEW_TV_FOLDER_NAME"}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📺 አዲስ ቲቪ ፎልደር ስም ይጻፉልኝ:")

    elif data == "adm_manage_sw" and is_admin:
        receivers = get_all_receivers()
        markup = InlineKeyboardMarkup()
        for r_key in receivers:
            markup.row(InlineKeyboardButton(f"❌ ሰርዝ: {r_key}", callback_data=f"del_folder_{r_key}"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🗑 ለመሰረዝ ሪሲቨር ይምረጡ:", reply_markup=markup)

    elif data.startswith("del_folder_") and is_admin:
        r_key = data.replace("del_folder_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bin_files WHERE receiver_key = ?", (r_key,))
        cursor.execute("DELETE FROM receivers WHERE key = ?", (r_key,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, f"✅ '{r_key}' ተሰርዟል!", show_alert=True)

    elif data == "adm_manage_tv" and is_admin:
        tvs = get_all_tvs()
        markup = InlineKeyboardMarkup()
        for t_key in tvs:
            markup.row(InlineKeyboardButton(f"❌ ሰርዝ: {t_key}", callback_data=f"del_tv_{t_key}"))
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🗑 ለመሰረዝ ቲቪ ፎልደር ይምረጡ:", reply_markup=markup)

    elif data.startswith("del_tv_") and is_admin:
        t_key = data.replace("del_tv_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tv_files WHERE tv_key = ?", (t_key,))
        cursor.execute("DELETE FROM tv_software WHERE key = ?", (t_key,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, f"✅ '{t_key}' ቲቪ ፎልደር ተሰርዟል!", show_alert=True)

    elif data == "adm_broadcast" and is_admin:
        ADMIN_STATE[user_id] = "WAITING_BROADCAST_MSG"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📢 የሚተላለፈውን መልእክት ይፃፉልኝ:")

    elif data == "adm_backup" and is_admin:
        bot.answer_callback_query(call.id, "💾 ባክአፕ በመላክ ላይ...", show_alert=False)
        if os.path.exists("bot_database.db"):
            with open("bot_database.db", "rb") as db_file:
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
        conn.close()
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📊 **ስታቲስቲክስ፦**\n\n👥 ተጠቃሚዎች: **{u_cnt}**\n📁 ሪሲቨር ፎልደሮች: **{r_cnt}**\n📺 ቲቪ ፎልደሮች: **{tv_cnt}**\n📄 ፋይሎች: **{f_cnt}**", parse_mode="Markdown")

    elif data.startswith("get_rcv_"):
        rcv = data.replace("get_rcv_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_id, file_size FROM bin_files WHERE receiver_key = ? ORDER BY id DESC LIMIT 1", (rcv,))
        file_data = cursor.fetchone()
        conn.close()
        bot.answer_callback_query(call.id)
        if file_data:
            bot.send_document(chat_id, file_data[1], caption=f"✅ {file_data[0]}\n📦 መጠን: {file_data[2]}")
        else:
            bot.send_message(chat_id, f"⚠️ ፋይል አልተገኘም።")

    elif data.startswith("get_tv_"):
        tv = data.replace("get_tv_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, file_id, file_size FROM tv_files WHERE tv_key = ? ORDER BY id DESC LIMIT 1", (tv,))
        file_data = cursor.fetchone()
        conn.close()
        bot.answer_callback_query(call.id)
        if file_data:
            bot.send_document(chat_id, file_data[1], caption=f"✅ {file_data[0]}\n📦 መጠን: {file_data[2]}")
        else:
            bot.send_message(chat_id, f"⚠️ ፋይል አልተገኘም።")

    elif data == "cancel_upload":
        ADMIN_STATE.pop(user_id, None)
        bot.answer_callback_query(call.id, "✅ ተጠናቋል።", show_alert=True)
        bot.send_message(chat_id, "ወደ ዋናው ማውጫ ተመለሰ:", reply_markup=main_menu(user_id, True))

bot.infinity_polling()
