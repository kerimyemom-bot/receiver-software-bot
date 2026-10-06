import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# ----------------- CONFIGURATION (ENVIRONMENT VARIABLES) -----------------
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")

if not TOKEN:
  raise ValueError("⚠️ የቦት ቶከን (BOT_TOKEN) አልተገኘም! እባክዎ Environment Variable ላይ ያስገቡ።")

if not ADMIN_ID_STR:
  raise ValueError("⚠️ የአድሚን ID (ADMIN_ID) አልተገኘም! እባክዎ Environment Variable ላይ ያስገቡ።")

ADMIN_ID = int(ADMIN_ID_STR)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Flask app for Render Keep-Alive
app = Flask(__name__)


@app.route("/")
def home():
  return "Bot is running live!"


def run_flask():
  port = int(os.getenv("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# ----------------- DATABASE SETUP -----------------
def init_db():
  conn = sqlite3.connect("bot_database.db", check_same_thread=False)
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'free'
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            device_type TEXT, -- 'receiver' ወይም 'tv'
            photo_id TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER,
            title TEXT,
            file_id TEXT,
            file_size TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(brand_id) REFERENCES brands(id)
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount TEXT,
            receipt_info TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
  conn.commit()
  conn.close()


init_db()


def get_db():
  return sqlite3.connect("bot_database.db", check_same_thread=False)


# ----------------- KEYBOARDS -----------------
def main_menu_keyboard(user_id):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(
      types.KeyboardButton("📺 ሪሲቨር ሶፍትዌሮች"),
      types.KeyboardButton("🖥 የቲቪ ሶፍትዌሮች"),
  )
  markup.add(
      types.KeyboardButton("🔍 ፋይል ፈልግ"),
      types.KeyboardButton("⭐ ቪአይፒ ፕላን (VIP)"),
  )
  markup.add(types.KeyboardButton("❓ እገዛ"))

  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton("🛠 አድሚን ፓነል"))
  return markup


# ----------------- START & MAIN MENU -----------------
@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = message.from_user.id
  username = message.from_user.username or "No Username"

  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
      (user_id, username),
  )
  conn.commit()
  conn.close()

  welcome_text = (
      f"ሰላም <b>{message.from_user.first_name}</b>! 👋\n\n"
      "ወደ ሶፍትዌር ማከፋፈያ ቦታችን በደህና መጡ። የሚፈልጉትን የቲቪ ወይም ሪሲቨር ሶፍትዌር ከታች ካሉት አማራጮች ማግኘት ይችላሉ።"
  )
  bot.send_message(
      message.chat.id, welcome_text, reply_markup=main_menu_keyboard(user_id)
  )


# ----------------- RECEIVER & TV BROWSING -----------------
@bot.message_handler(func=lambda msg: msg.text in ["📺 ሪሲቨር ሶፍትዌሮች", "🖥 የቲቪ ሶፍትዌሮች"])
def show_device_brands(message):
  device_type = "receiver" if "ሪሲቨር" in message.text else "tv"

  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, name, photo_id FROM brands WHERE device_type = ?",
      (device_type,),
  )
  brands = cursor.fetchall()
  conn.close()

  if not brands:
    title_name = "ሪሲቨሮች" if device_type == "receiver" else "ቲቪዎች"
    bot.send_message(
        message.chat.id,
        f"⚠️ እስካሁን የተመዘገቡ የ{title_name} ብራንዶች የሉም። እባክዎ ቆይተው ይሞክሩ።",
    )
    return

  markup = types.InlineKeyboardMarkup()
  for b_id, name, _ in brands:
    prefix = "📺" if device_type == "receiver" else "🖥"
    markup.add(
        types.InlineKeyboardButton(f"{prefix} {name}", callback_data=f"brand_{b_id}")
    )

  markup.add(
      types.InlineKeyboardButton(
          "⬅️ ወደ ዋና ሜኑ ተመለስ", callback_data="back_to_main"
      )
  )

  title_text = (
      "የሪሲቨር ብራንዶች ዝርዝር"
      if device_type == "receiver"
      else "የቲቪ ብራንዶች ዝርዝር"
  )
  bot.send_message(
      message.chat.id, f"እባክዎ ከታች ካሉት ውስጥ የሚፈልጉትን <b>{title_text}</b> ይምረጡ፡",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("brand_"))
def show_brand_files(call):
  brand_id = int(call.data.split("_")[1])
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT name, device_type, photo_id FROM brands WHERE id = ?", (brand_id,)
  )
  brand_info = cursor.fetchone()

  cursor.execute(
      "SELECT id, title, file_size FROM files WHERE brand_id = ?", (brand_id,)
  )
  files = cursor.fetchall()
  conn.close()

  if not brand_info:
    bot.answer_callback_query(call.id, "ብራንዱ አልተገኘም!")
    return

  brand_name, device_type, brand_photo = brand_info

  markup = types.InlineKeyboardMarkup()
  for f_id, title, size in files:
    btn_text = f"{title} ({size})" if size else title
    markup.add(
        types.InlineKeyboardButton(btn_text, callback_data=f"getfile_{f_id}")
    )

  back_callback = (
      "back_to_receivers" if device_type == "receiver" else "back_to_tvs"
  )
  markup.add(types.InlineKeyboardButton("⬅️ ተመለስ", callback_data=back_callback))

  caption_text = f"📂 የብራንድ ስም፦ <b>{brand_name}</b>\n\nእባክዎ የሚፈልጉትን ፋይል ይምረጡ፡"

  try:
    bot.delete_message(call.message.chat.id, call.message.message_id)
  except Exception:
    pass

  if brand_photo:
    try:
      bot.send_photo(
          call.message.chat.id,
          brand_photo,
          caption=caption_text,
          reply_markup=markup,
      )
    except Exception:
      bot.send_message(
          call.message.chat.id, caption_text, reply_markup=markup
      )
  else:
    bot.send_message(call.message.chat.id, caption_text, reply_markup=markup)


@bot.callback_query_handler(
    func=lambda call: call.data in ["back_to_receivers", "back_to_tvs", "back_to_main"]
)
def handle_back_buttons(call):
  try:
    bot.delete_message(call.message.chat.id, call.message.message_id)
  except Exception:
    pass

  if call.data == "back_to_receivers":
    message = call.message
    message.text = "📺 ሪሲቨር ሶፍትዌሮች"
    show_device_brands(message)
  elif call.data == "back_to_tvs":
    message = call.message
    message.text = "🖥 የቲቪ ሶፍትዌሮች"
    show_device_brands(message)
  else:
    bot.send_message(
        call.message.chat.id,
        "ዋናው ሜኑ:",
        reply_markup=main_menu_keyboard(call.from_user.id),
    )


# ----------------- FILE DOWNLOAD HANDLER -----------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("getfile_"))
def send_selected_file(call):
  file_id_db = int(call.data.split("_")[1])
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT file_id, title FROM files WHERE id = ?", (file_id_db,)
  )
  file_data = cursor.fetchone()
  conn.close()

  if file_data:
    tg_file_id, title = file_data
    try:
      bot.send_document(
          call.message.chat.id,
          tg_file_id,
          caption=f"📂 <b>{title}</b>\n\nተጭኗል! ⚠️ ፋይሉ አልሰራ ካለ 'ሪፖርት' ያድርጉ።",
      )
    except Exception:
      bot.answer_callback_query(
          call.id, "ፋይሉን መላክ አልተቻለም (File ID Error)"
      )
  else:
    bot.answer_callback_query(call.id, "ፋይሉ አልተገኘም!")


# ----------------- SEARCH FEATURE -----------------
@bot.message_handler(func=lambda msg: msg.text == "🔍 ፋይል ፈልግ")
def search_prompt(message):
  msg = bot.send_message(
      message.chat.id,
      "🔍 ሊፈልጉት የሚፈልጉትን የቲቪ ወይም ሪሲቨር ሶፍትዌር ስም ይጻፉ (ለምሳሌ፦ Samsung ወይም Tiger):",
  )
  bot.register_next_step_handler(msg, process_search)


def process_search(message):
  query = message.text.strip()
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, title, file_size FROM files WHERE title LIKE ?",
      (f"%{query}%",),
  )
  results = cursor.fetchall()
  conn.close()

  if not results:
    bot.send_message(
        message.chat.id, f"❌ '{query}' የሚል ፋይል አልተገኘም። እባክዎ እንደገና ይሞክሩ።"
    )
    return

  markup = types.InlineKeyboardMarkup()
  for f_id, title, size in results:
    markup.add(
        types.InlineKeyboardButton(
            f"{title} ({size})", callback_data=f"getfile_{f_id}"
        )
    )

  bot.send_message(
      message.chat.id, f"🔍 የፍለጋ ውጤቶች ለ '{query}':", reply_markup=markup
  )


# ----------------- ADMIN PANEL & MANAGEMENT -----------------
@bot.message_handler(
    func=lambda msg: msg.text == "🛠 አድሚን ፓነል" and msg.from_user.id == ADMIN_ID
)
def admin_panel(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(types.KeyboardButton("📢 ታለመ ብሮድካስት (Targeted Broadcast)"))
  markup.add(
      types.KeyboardButton("➕ ብራንድ/ቲቪ/ሪሲቨር ጫን"),
      types.KeyboardButton("📤 ፋይል ጫን"),
  )
  markup.add(types.KeyboardButton("🗑️ የዲሌት (Delete) ሜኑ"))
  markup.add(types.KeyboardButton("🏠 ወደ ዋና ሜኑ ተመለስ"))
  bot.send_message(message.chat.id, "አድሚን ፓነል ተከፍቷል:", reply_markup=markup)


# --- 1. ADD BRAND / FOLDER HANDLER ---
@bot.message_handler(
    func=lambda msg: msg.text == "➕ ብራንድ/ቲቪ/ሪሲቨር ጫን"
    and msg.from_user.id == ADMIN_ID
)
def add_brand_step1(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
  markup.add(types.KeyboardButton("receiver"), types.KeyboardButton("tv"))
  msg = bot.send_message(
      message.chat.id,
      "ይህንን ብራንድ የትኛው ምድብ ስር መመዝገብ ይፈልጋሉ? (ከታች ካሉት ይምረጡ ወይም ይጻፉ: receiver ወይም"
      " tv)",
      reply_markup=markup,
  )
  bot.register_next_step_handler(msg, add_brand_step2)


def add_brand_step2(message):
  device_type = message.text.strip().lower()
  if device_type not in ["receiver", "tv"]:
    bot.send_message(
        message.chat.id,
        "⚠️ የተሳሳተ ምድብ! እባክዎ እንደገና '➕ ብራንድ/ቲቪ/ሪሲቨር ጫን' የሚለውን በመጫን ይሞክሩ።",
    )
    return

  msg = bot.send_message(
      message.chat.id,
      "እባክዎ የአዲሱን ብራንድ ስም ይጻፉ (ለምሳሌ፦ Tiger, Samsung, LG):",
      reply_markup=types.ReplyKeyboardRemove(),
  )
  bot.register_next_step_handler(msg, add_brand_step3, device_type)


def add_brand_step3(message, device_type):
  brand_name = message.text.strip()
  msg = bot.send_message(
      message.chat.id,
      f"ለ '{brand_name}' ብራንድ የሚያሳይ **ፎቶ (Logo)** ይላኩ (ወይም 'skip' ብለው ይለፉ):",
  )
  bot.register_next_step_handler(msg, add_brand_save, device_type, brand_name)


def add_brand_save(message, device_type, brand_name):
  photo_id = None
  if message.photo:
    photo_id = message.photo[-1].file_id
  elif message.text and message.text.strip().lower() == "skip":
    photo_id = None
  else:
    # ፎቶ ካልላከ በስተቀር በጽሁፍ skip ካለ ይለፋል፣ ካልሆነ ያለ ፎቶ ይመዝገበዋል
    pass

  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO brands (name, device_type, photo_id) VALUES (?, ?, ?)",
      (brand_name, device_type, photo_id),
  )
  conn.commit()
  conn.close()

  bot.send_message(
      message.chat.id,
      f"✅ ብራንድ <b>{brand_name}</b> በተሳካ ሁኔታ ተመዝግቧል!",
      reply_markup=main_menu_keyboard(ADMIN_ID),
  )


# --- 2. UPLOAD FILE HANDLER ---
@bot.message_handler(
    func=lambda msg: msg.text == "📤 ፋይል ጫን" and msg.from_user.id == ADMIN_ID
)
def upload_file_step1(message):
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, device_type FROM brands")
  brands = cursor.fetchall()
  conn.close()

  if not brands:
    bot.send_message(
        message.chat.id,
        "⚠️ መጀመሪያ ብራንድ (ፎልደር) መፍጠር አለብዎት! እባክዎ '➕ ብራንድ/ቲቪ/ሪሲቨር ጫን' ይጠቀሙ።",
    )
    return

  markup = types.InlineKeyboardMarkup()
  for b_id, name, dtype in brands:
    markup.add(
        types.InlineKeyboardButton(
            f"📁 {name} ({dtype})", callback_data=f"upbrand_{b_id}"
        )
    )

  bot.send_message(
      message.chat.id,
      "እባክዎ ፋይሉ የሚቀመጥበትን **ብራንድ (ፎልደር)** ከታች ይምረጡ፡",
      reply_markup=markup,
  )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("upbrand_")
)
def upload_file_step2(call):
  brand_id = int(call.data.split("_")[1])
  msg = bot.send_message(
      call.message.chat.id,
      "📥 አሁን ሊጭኑት የሚፈልጉትን **ፋይል (Document)** ወደ ቦቱ ይላኩ (ሊንክ ሳይሆን ዱክመንት fileupload"
      " አድርገው):",
  )
  bot.register_next_step_handler(msg, upload_file_save, brand_id)
  try:
    bot.delete_message(call.message.chat.id, call.message.message_id)
  except Exception:
    pass


def upload_file_save(message, brand_id):
  if not message.document:
    bot.send_message(
        message.chat.id,
        "⚠️ የላኩት ፋይል ትክክለኛ ዱክመንት አይደለም። እባክዎ '📤 ፋይል ጫን' በመጫን እንደገና ይሞክሩ።",
    )
    return

  file_id = message.document.file_id
  file_name = message.document.file_name or "Unknown Title"
  file_size_bytes = message.document.file_size
  # ሳይዙን ወደ MB መቀየር
  file_size = (
      f"{round(file_size_bytes / (1024 * 1024), 2)} MB"
      if file_size_bytes
      else "Unknown Size"
  )

  conn = get_db()
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO files (brand_id, title, file_id, file_size) VALUES (?, ?,"
      " ?, ?)",
      (brand_id, file_name, file_id, file_size),
  )
  conn.commit()
  conn.close()

  bot.send_message(
      message.chat.id,
      f"✅ ፋይሉ <b>{file_name} ({file_size})</b> በተሳካ ሁኔታ ተጭኗል!",
      reply_markup=main_menu_keyboard(ADMIN_ID),
  )


# --- 3. DELETE MENU HANDLER ---
@bot.message_handler(
    func=lambda msg: msg.text == "🗑️ የዲሌት (Delete) ሜኑ"
    and msg.from_user.id == ADMIN_ID
)
def delete_menu(message):
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "🗑️ ብራንድ (ፎልደር) ሰርዝ", callback_data="del_menu_brand"
      )
  )
  markup.add(
      types.InlineKeyboardButton(
          "🗑️ ሶፍትዌር (ፋይል) ሰርዝ", callback_data="del_menu_file"
      )
  )
  bot.send_message(
      message.chat.id,
      "ምን መሰረዝ ይፈልጋሉ? ከታች ያለውን ይምረጡ:",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data == "del_menu_brand")
def delete_brand_list(call):
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, device_type FROM brands")
  brands = cursor.fetchall()
  conn.close()

  if not brands:
    bot.answer_callback_query(call.id, "ምንም የተመዘገበ ብራንድ የለም!")
    return

  markup = types.InlineKeyboardMarkup()
  for b_id, name, dtype in brands:
    markup.add(
        types.InlineKeyboardButton(
            f"❌ ሰርዝ: {name} ({dtype})", callback_data=f"delbrand_{b_id}"
        )
    )

  bot.edit_message_text(
      "የሚሰርዙትን ብራንድ ይምረጡ (ማስታወሻ፦ ብራንዱ ሲጠፋ ስር ያሉ ፋይሎችም ይሰረዛሉ):",
      call.message.chat.id,
      call.message.message_id,
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("delbrand_"))
def execute_delete_brand(call):
  brand_id = int(call.data.split("_")[1])
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM files WHERE brand_id = ?", (brand_id,))
  cursor.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
  conn.commit()
  conn.close()

  bot.answer_callback_query(call.id, "ብራንዱ እና ፋይሎቹ ተሰርዘዋል!")
  bot.edit_message_text(
      "✅ ብራንዱ በተሳካ ሁኔታ ተሰርዟል!",
      call.message.chat.id,
      call.message.message_id,
  )


@bot.callback_query_handler(func=lambda call: call.data == "del_menu_file")
def delete_file_list(call):
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute("SELECT id, title, file_size FROM files")
  files = cursor.fetchall()
  conn.close()

  if not files:
    bot.answer_callback_query(call.id, "ምንም የተመዘገበ ፋይል የለም!")
    return

  markup = types.InlineKeyboardMarkup()
  for f_id, title, size in files:
    markup.add(
        types.InlineKeyboardButton(
            f"❌ ሰርዝ: {title} ({size})", callback_data=f"delfile_{f_id}"
        )
    )

  bot.edit_message_text(
      "የሚሰርዙትን ሶፍትዌር/ፋይል ይምረጡ:",
      call.message.chat.id,
      call.message.message_id,
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("delfile_"))
def execute_delete_file(call):
  file_id = int(call.data.split("_")[1])
  conn = get_db()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
  conn.commit()
  conn.close()

  bot.answer_callback_query(call.id, "ፋይሉ ተሰርዟል!")
  bot.edit_message_text(
      "✅ ፋይሉ በተሳካ ሁኔታ ተሰርዟል!",
      call.message.chat.id,
      call.message.message_id,
  )


# --- TARGETED BROADCAST ---
@bot.message_handler(
    func=lambda msg: msg.text == "📢 ታለመ ብሮድካስት (Targeted Broadcast)"
    and msg.from_user.id == ADMIN_ID
)
def broadcast_segment_prompt(message):
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "⭐ ለ VIP ተጠቃሚዎች ብቻ", callback_data="bc_vip"
      )
  )
  markup.add(
      types.InlineKeyboardButton(
          "🆓 ለ ነጻ (Free) ተጠቃሚዎች ብቻ", callback_data="bc_free"
      )
  )
  markup.add(
      types.InlineKeyboardButton(
          "👥 ለሁሉም ተጠቃሚዎች", callback_data="bc_all"
      )
  )
  bot.send_message(
      message.chat.id,
      "ማስታወቂያውን ለማስተላለፍ የሚፈልጉትን የተጠቃሚ ምድብ (Segment) ይምረጡ፡",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("bc_"))
def receive_broadcast_message(call):
  target_group = call.data.split("_")[1]
  msg = bot.send_message(
      call.message.chat.id,
      f"እባክዎ ለ [{target_group.upper()}] ሊልኩት የሚፈልጉትን መልዕክት (ጽሁፍ ወይም ፎቶ) ይጻፉ:",
  )
  bot.register_next_step_handler(msg, execute_targeted_broadcast, target_group)


def execute_targeted_broadcast(message, target_group):
  conn = get_db()
  cursor = conn.cursor()

  if target_group == "vip":
    cursor.execute("SELECT user_id FROM users WHERE status = 'vip'")
  elif target_group == "free":
    cursor.execute("SELECT user_id FROM users WHERE status = 'free'")
  else:
    cursor.execute("SELECT user_id FROM users")

  users = cursor.fetchall()
  conn.close()

  success_count = 0
  for (u_id,) in users:
    try:
      bot.copy_message(u_id, message.chat.id, message.message_id)
      success_count += 1
    except Exception:
      pass

  bot.send_message(
      message.chat.id,
      f"✅ ብሮድካስቱ በተሳካ ሁኔታ ለ {success_count} ተጠቃሚዎች ተደርሷል!",
  )


@bot.message_handler(func=lambda msg: msg.text == "🏠 ወደ ዋና ሜኑ ተመለስ")
def back_to_main(message):
  bot.send_message(
      message.chat.id,
      "ዋናው ሜኑ:",
      reply_markup=main_menu_keyboard(message.from_user.id),
  )


# ----------------- MAIN RUNNER -----------------
if __name__ == "__main__":
  t = threading.Thread(target=run_flask)
  t.daemon = True
  t.start()

  print("Bot is starting polling securely with full admin management tools...")
  bot.infinity_polling()
