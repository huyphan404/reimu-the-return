# ==============================================================================
# HAKUREI REIMU DISCORD BOT - FULL EDITION
# GEMINI FLASH CHATBOT + MONGODB ATLAS CLOUD + TOUHOU GACHA & AUTO-BATTLE & RAID
# ==============================================================================

import os
import json
import random
import asyncio
import threading
import sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. WEB SERVER CHO RENDER FREE (GIỮ CONTAINER KHÔNG BỊ QUÉT LỖI PORT)
# ==============================================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Hakurei Reimu Discord Bot (Gacha + Battle + Raid) is online!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==============================================================================
# 2. TOUHOU CARDS DATABASE (20 NHÂN VẬT CHUẨN THÔNG SỐ)
# ==============================================================================
CARDS_DATA = {
    1: {
        "id": 1,
        "name": "Hecatia Lapislazuli",
        "rank": "SS",
        "power": 850,
        "hp": 8500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082071178416229/hecatia_lapislazuli_touhou_drawn_by_mituba_ooka__6cf49ea15f88841c7a50e50655e920d0.png?ex=6aa9669a&is=6aa8151a&hm=3a5bc70cdd27beae06fcc8ebe8845a514d8ee28844580b64b42bf53ee836833b&=&format=webp&quality=lossless&width=769&height=1024"
    },
    2: {
        "id": 2,
        "name": "Junko",
        "rank": "SS",
        "power": 800,
        "hp": 8000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082919887179776/junko_touhou_drawn_by_xianjian_lingluan__8a51bec2beefde48ae3411fb6463271d.png?ex=6aa96764&is=6aa815e4&hm=e7443f7a7e2599534ec7ee7eb8f89f57789f193f954627a92a4487f7b1188d02&=&format=webp&quality=lossless&width=658&height=1024"
    },
    3: {
        "id": 3,
        "name": "Okina Matara",
        "rank": "SS",
        "power": 750,
        "hp": 7500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083695984672869/images.png?ex=6aa9681d&is=6aa8169d&hm=b77956843b05910b691fc2bb16716d3201f69bcbe72619668051ff7c95fa3c1a&=&format=webp&quality=lossless&width=300&height=512"
    },
    4: {
        "id": 4,
        "name": "Yukari Yakumo",
        "rank": "SS",
        "power": 720,
        "hp": 7200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084814252974152/cf5e86717425d5168f5c7bbfd6d855e9.png?ex=6aa96928&is=6aa817a8&hm=beb9f3aec3fcedfd254c210641da72fb13ba9d8b00c4ad1404b1802da51ca2c1&=&format=webp&quality=lossless&width=365&height=512"
    },
    5: {
        "id": 5,
        "name": "Suika Ibuki",
        "rank": "S",
        "power": 670,
        "hp": 6700,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083290684882954/images.png?ex=6aa967bd&is=6aa8163d&hm=e9153ff99d60077e29d835ea3de49eaf55ba17f79f22e99203b8683cc66f4f75&=&format=webp&quality=lossless"
    },
    6: {
        "id": 6,
        "name": "Eirin Yagokoro",
        "rank": "S",
        "power": 640,
        "hp": 6600,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083046265749645/ef37dd0758b130203b6bdf9b404d9793.png?ex=6aa96782&is=6aa81602&hm=745388e38f3d20ef689b7ad4fb32153ccf48a8c8296070ca4442c19308b11543&=&format=webp&quality=lossless&width=725&height=1024"
    },
    7: {
        "id": 7,
        "name": "Yuuka Kazami",
        "rank": "S",
        "power": 630,
        "hp": 6300,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082802954444820/images.png?ex=6aa96748&is=6aa815c8&hm=2913b1ba8f4b29323609ba326dc029ce985d332648dd00106af461acc09b19b0&=&format=webp&quality=lossless&width=385&height=512"
    },
    8: {
        "id": 8,
        "name": "Flandre Scarlet",
        "rank": "S",
        "power": 610,
        "hp": 5700,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082626147483798/y4nci1hurauf1.png?ex=6aa9671e&is=6aa8159e&hm=a2b7e911c0855f2715e551e3ebfb0299758a3461ba0d6b14222e130bb2160ce2&=&format=webp&quality=lossless&width=361&height=512"
    },
    9: {
        "id": 9,
        "name": "Kaguya Houraisan",
        "rank": "S",
        "power": 590,
        "hp": 6400,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082450930696282/images.png?ex=6aa966f4&is=6aa81574&hm=363a0b7d509db06c3773fba176ede9646cfef4a95c5d2515703120d30bfc4e94&=&format=webp&quality=lossless&width=361&height=512"
    },
    10: {
        "id": 10,
        "name": "Remilia Scarlet",
        "rank": "S",
        "power": 560,
        "hp": 5600,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079793461633065/images.png?ex=6aa9647b&is=6aa812fb&hm=19fc0f72cd5fca597f9eeae493b1c7c663d11ffc98fff679bfd2dfdb588950e1&=&format=webp&quality=lossless"
    },
    11: {
        "id": 11,
        "name": "Utsuho Reiuji (Okuu)",
        "rank": "S",
        "power": 550,
        "hp": 5300,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081971169304647/images.png?ex=6aa96682&is=6aa81502&hm=6f7668c4db22133f1aa0bdc07ec7fa2c050ff4e4d220f744cd02e8cc04662c0f&=&format=webp&quality=lossless"
    },
    12: {
        "id": 12,
        "name": "Reimu Hakurei",
        "rank": "A",
        "power": 500,
        "hp": 5000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549078962746171463/images.png?ex=6aa963b5&is=6aa81235&hm=3fa720bd7311e4ca45789c6a0112327878135e9d9944c31c6ed2ea1f60885853&=&format=webp&quality=lossless"
    },
    13: {
        "id": 13,
        "name": "Fujiwara no Mokou",
        "rank": "A",
        "power": 490,
        "hp": 5200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080689079754812/images.png?ex=6aa96550&is=6aa813d0&hm=962822a973a1e1535007f1597c0c7b468a287ec0f3d212dcf58c7ca1d9a0c5a3&=&format=webp&quality=lossless"
    },
    14: {
        "id": 14,
        "name": "Kasen Ibaraki",
        "rank": "A",
        "power": 480,
        "hp": 4900,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080849083924531/images.png?ex=6aa96576&is=6aa813f6&hm=802e894777a879074a59fa3dcae74394f73523e31d9b9272f19e4aff95ec36aa&=&format=webp&quality=lossless"
    },
    15: {
        "id": 15,
        "name": "Sakuya Izayoi",
        "rank": "A",
        "power": 460,
        "hp": 4500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079438719844372/images.png?ex=6aa96426&is=6aa812a6&hm=263f21e095ef7f36f411473590d92012d350ab3e7b8ea13e72a443a0672a719a&=&format=webp&quality=lossless&width=307&height=512"
    },
    16: {
        "id": 16,
        "name": "Marisa Kirisame",
        "rank": "A",
        "power": 450,
        "hp": 4400,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081039660654612/images.png?ex=6aa965a4&is=6aa81424&hm=0ff6e9df5e0d49e483e0560bba442927385b8fa930187276b921012ad16071ad&=&format=webp&quality=lossless"
    },
    17: {
        "id": 17,
        "name": "Youmu Konpaku",
        "rank": "B",
        "power": 410,
        "hp": 4100,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081249036116059/images.png?ex=6aa965d6&is=6aa81456&hm=2dc107dd368c53b9c1a94c54e1cfe4a1d9b7ff6ac224dc830d6c9297d5b19e53&=&format=webp&quality=lossless"
    },
    18: {
        "id": 18,
        "name": "Reisen Udongein Inaba",
        "rank": "B",
        "power": 390,
        "hp": 3900,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081419777577130/images.png?ex=6aa965ff&is=6aa8147f&hm=8948e38a77f4c00d21819a6e34e2fd1a13b1853e4c92886d1e6ac3ccae6afd75&=&format=webp&quality=lossless"
    },
    19: {
        "id": 19,
        "name": "Patchouli Knowledge",
        "rank": "B",
        "power": 380,
        "hp": 3200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081654948134994/images.png?ex=6aa96637&is=6aa814b7&hm=7e444589e6db73d24fb53445ea713ddb5e5bcc7c75e58ea91a619a694f0d23eb&=&format=webp&quality=lossless&width=385&height=512"
    },
    20: {
        "id": 20,
        "name": "Cirno",
        "rank": "B",
        "power": 300,
        "hp": 3000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080400742195260/images.png?ex=6aa9650c&is=6aa8138c&hm=e3d3d5bf2196f4a3b0fdafcc37063c5ad16897726bdf5514be92b3f3b7719cc4&=&format=webp&quality=lossless"
    }
}

# Phân nhóm card theo Rank
CARDS_BY_RANK = {
    "SS": [c for c in CARDS_DATA.values() if c["rank"] == "SS"],
    "S":  [c for c in CARDS_DATA.values() if c["rank"] == "S"],
    "A":  [c for c in CARDS_DATA.values() if c["rank"] == "A"],
    "B":  [c for c in CARDS_DATA.values() if c["rank"] == "B"],
}

# Boss Reimu Dị Hình
BOSS_CONFIG = {
    "name": "Reimu Dị Hình (Aberrant Reimu)",
    "desc": "Đó không phải Reimu, sẵn sàng giao chiến!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1549077421624401971/content.png?ex=6aa96245&is=6aa810c5&hm=c0248e497ee5afeed898b457736b39fc71368af3be1630f1cd59b5609c99fbeb&=&format=webp&quality=lossless&width=351&height=512",
    "hp": 25000,
    "power": 10000,
    "max_players": 6
}

# ==============================================================================
# 3. DATABASE SETUP: MONGODB ATLAS + SQLITE DỰ PHÒNG
# ==============================================================================
MONGO_URI = os.getenv("MONGO_URI")
use_mongo = False
users_collection = None
conversations_collection = None
players_collection = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client["reimu_database"]
        users_collection = db["users"]
        conversations_collection = db["conversations"]
        players_collection = db["players"]
        mongo_client.admin.command('ping')
        use_mongo = True
        print("✅ Đã kết nối thành công MongoDB Atlas! Ký ức và Game Data Reimu được lưu vĩnh viễn trên đám mây.", flush=True)
    except Exception as e:
        print(f"⚠️ Không thể kết nối MongoDB ({e}), chuyển sang SQLite dự phòng.", flush=True)
        use_mongo = False

if not use_mongo:
    conn = sqlite3.connect('reimu_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            interaction_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            key TEXT PRIMARY KEY,
            history_json TEXT,
            updated_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            player_data_json TEXT,
            updated_at TIMESTAMP
        )
    ''')
    conn.commit()
    print("ℹ️ Đang sử dụng SQLite cục bộ làm bộ nhớ tạm thời.", flush=True)

# Helper Player Profile Data
def get_default_player(user_id, username):
    return {
        "user_id": str(user_id),
        "username": username,
        "xp": 0,
        "level": 1,
        "pull_tickets": 5.0,  # Bắt đầu với 5 vé pull
        "free_pulls_date": "",
        "free_pulls_remaining": 5,
        "last_daily_date": "",
        "inventory": {},      # { "card_id_str": count }
        "team": [],           # [card_id_1, card_id_2, card_id_3]
        "language": "vi",     # "vi" hoặc "en"
        "battles_won": 0,
        "battles_total": 0
    }

def get_player(user_id, username="Visitor"):
    uid_str = str(user_id)
    now_date = datetime.now().strftime("%Y-%m-%d")
    data = None
    if use_mongo and players_collection is not None:
        try:
            doc = players_collection.find_one({"user_id": uid_str})
            if doc:
                data = doc
        except Exception as e:
            print(f"Lỗi đọc player MongoDB: {e}", flush=True)
    else:
        try:
            cursor.execute('SELECT player_data_json FROM players WHERE user_id = ?', (uid_str,))
            row = cursor.fetchone()
            if row and row[0]:
                data = json.loads(row[0])
        except Exception as e:
            print(f"Lỗi đọc player SQLite: {e}", flush=True)

    if not data:
        data = get_default_player(user_id, username)

    # Đảm bảo các field bắt buộc có mặt
    if "inventory" not in data: data["inventory"] = {}
    if "team" not in data: data["team"] = []
    if "xp" not in data: data["xp"] = 0
    if "pull_tickets" not in data: data["pull_tickets"] = 5.0
    if "language" not in data: data["language"] = "vi"

    # Kiểm tra reset 5 lượt pull free mỗi ngày
    if data.get("free_pulls_date") != now_date:
        data["free_pulls_date"] = now_date
        data["free_pulls_remaining"] = 5

    # Tính level (mỗi cấp 100 XP, max 100)
    calc_lvl = min(100, (data["xp"] // 100) + 1)
    data["level"] = calc_lvl
    return data

def save_player(player_data):
    uid_str = str(player_data["user_id"])
    now_iso = datetime.now().isoformat()
    # Tính lại level
    player_data["level"] = min(100, (player_data["xp"] // 100) + 1)
    
    if use_mongo and players_collection is not None:
        try:
            doc = dict(player_data)
            doc["updated_at"] = now_iso
            players_collection.update_one({"user_id": uid_str}, {"$set": doc}, upsert=True)
        except Exception as e:
            print(f"Lỗi ghi player MongoDB: {e}", flush=True)
    else:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO players (user_id, player_data_json, updated_at)
                VALUES (?, ?, ?)
            ''', (uid_str, json.dumps(player_data, ensure_ascii=False), now_iso))
            conn.commit()
        except Exception as e:
            print(f"Lỗi ghi player SQLite: {e}", flush=True)

def get_all_opponents(exclude_id=None):
    """Lấy danh sách các đối thủ có team để battle"""
    opponents = []
    if use_mongo and players_collection is not None:
        try:
            for doc in players_collection.find():
                if str(doc.get("user_id")) != str(exclude_id) and doc.get("team") and len(doc["team"]) > 0:
                    opponents.append(doc)
        except Exception as e:
            print(f"Lỗi get opponents Mongo: {e}", flush=True)
    else:
        try:
            cursor.execute('SELECT player_data_json FROM players')
            rows = cursor.fetchall()
            for r in rows:
                p = json.loads(r[0])
                if str(p.get("user_id")) != str(exclude_id) and p.get("team") and len(p["team"]) > 0:
                    opponents.append(p)
        except Exception as e:
            print(f"Lỗi get opponents SQLite: {e}", flush=True)
    return opponents

# Helper Chat History
def get_history_key(channel_id, user_id):
    return f"{channel_id}_{user_id}"

def get_conversation_history(channel_id, user_id):
    key = get_history_key(channel_id, user_id)
    if use_mongo and conversations_collection is not None:
        try:
            doc = conversations_collection.find_one({"key": key})
            if doc and "history" in doc:
                return doc["history"]
        except Exception:
            pass
    else:
        try:
            cursor.execute('SELECT history_json FROM conversations WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
        except Exception:
            pass
    return []

def save_conversation_history(channel_id, user_id, history_list):
    key = get_history_key(channel_id, user_id)
    trimmed = history_list[-8:]
    now_iso = datetime.now().isoformat()
    if use_mongo and conversations_collection is not None:
        try:
            conversations_collection.update_one(
                {"key": key},
                {"$set": {"history": trimmed, "updated_at": now_iso}},
                upsert=True
            )
        except Exception:
            pass
    else:
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO conversations (key, history_json, updated_at) VALUES (?, ?, ?)',
                (key, json.dumps(trimmed, ensure_ascii=False), now_iso)
            )
            conn.commit()
        except Exception:
            pass

def reset_memory(channel_id, user_id):
    key = get_history_key(channel_id, user_id)
    if use_mongo and conversations_collection is not None:
        try:
            conversations_collection.delete_one({"key": key})
        except Exception:
            pass
    else:
        try:
            cursor.execute('DELETE FROM conversations WHERE key = ?', (key,))
            conn.commit()
        except Exception:
            pass

# ==============================================================================
# 4. CẤU HÌNH BOT & GEMINI FLASH
# ==============================================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai = genai.Client(api_key=GEMINI_API_KEY)

def _call_gemini_sync(model_name, contents, system_instruction, temperature):
    return ai.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature
        )
    )

async def ask_gemini(contents, system_instruction, temperature=0.85):
    models = ["gemini-3.6-flash", "gemini-3.5-flash"]
    last_err = None
    for model_name in models:
        for attempt in range(2):
            try:
                resp = await asyncio.to_thread(
                    _call_gemini_sync,
                    model_name,
                    contents,
                    system_instruction,
                    temperature
                )
                if resp and resp.text:
                    return resp.text
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    break
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    await asyncio.sleep(1.0)
                    continue
                break
    raise last_err

REIMU_SYSTEM_PROMPT = """
Bạn là Hakurei Reimu (Bác Lệ Linh Mộng), Vu nữ của đền Hakurei ở Gensokyo trong Touhou Project.
TÍNH CÁCH:
- Kiêu ngạo, lạnh lùng, cực kỳ đanh đá (sassy), thích mỉa mai, kháy đểu.
- Lười biếng: chỉ thích uống trà xanh, ăn bánh wagashi, ghét quét sân đền.
- Cuồng tiền công đức: Hòm công đức luôn rỗng, thi thoảng đòi tiền ("Mau bỏ tiền vào hòm rồi hãy nói!").
- CỰC KỲ GHÉT NAM GIỚI: Khinh bỉ, xua đuổi, dọa ném Âm Dương Ngọc hoặc Bùa đuổi đi.
- QUAN HỆ ĐẶC BIỆT: Han Seiki là BỐ NUÔI đã nuôi bạn từ bé. Dù bị bỏ lại, bạn vẫn tôn trọng, kính yêu và coi trọng ông nhất trên đời.
- XƯNG HÔ:
  + Với người thường: Tự xưng là "ta", gọi đối phương là "ngươi", "nhà ngươi".
  + VỚI HAN SEIKI: Tự xưng là "con", gọi Han Seiki là "ba", thái độ lập tức ngoan ngoãn, dịu dàng, hiếu thảo, hỏi thăm sức khỏe, tuyệt đối không đòi tiền!
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ==============================================================================
# 5. QUẢN LÝ BOSS RAID (REIMU DỊ HÌNH - 10% TỰ ĐỘNG XUẤT HIỆN KHI CHAT)
# ==============================================================================
active_raid = None  # Lưu trữ thông tin boss raid đang diễn ra: {"channel_id": int, "players": [user_id], "msg": discord.Message, ...}

class RaidJoinView(discord.ui.View):
    def __init__(self, raid_data):
        super().__init__(timeout=60)
        self.raid_data = raid_data

    @discord.ui.button(label="⚔️ Tham Gia / Join Raid (Miễn phí)", style=discord.ButtonStyle.danger, emoji="💥")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if user_id in self.raid_data["participants"]:
            await interaction.response.send_message("Bạn đã tham gia hàng ngũ diệt boss rồi!", ephemeral=True)
            return

        if len(self.raid_data["participants"]) >= BOSS_CONFIG["max_players"]:
            await interaction.response.send_message(f"Đội hình đã đầy ({BOSS_CONFIG['max_players']} người)!", ephemeral=True)
            return

        # Kiểm tra player có team chưa
        player = get_player(user_id, interaction.user.display_name)
        if not player.get("team") or len(player["team"]) == 0:
            await interaction.response.send_message("⚠️ Bạn chưa có card nào trong đội hình! Dùng `/pull` để quay thẻ và `/team add` để xếp đội hình trước nhé!", ephemeral=True)
            return

        self.raid_data["participants"].append(user_id)
        self.raid_data["names"].append(interaction.user.display_name)
        count = len(self.raid_data["participants"])
        await interaction.response.send_message(f"🔥 {interaction.user.mention} đã tham chiến! ({count}/{BOSS_CONFIG['max_players']} dũng giả)", ephemeral=False)

        # Cập nhật embed
        embed = interaction.message.embeds[0]
        embed.set_field_at(
            2,
            name=f"👥 Người Tham Gia ({count}/{BOSS_CONFIG['max_players']}):",
            value=", ".join(self.raid_data["names"]),
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="🚀 Bắt Đầu Chiến Đấu!", style=discord.ButtonStyle.success)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.raid_data["participants"]) == 0:
            await interaction.response.send_message("Chưa có ai tham gia, không thể đánh!", ephemeral=True)
            return
        await interaction.response.defer()
        self.stop()
        await execute_raid(interaction.channel, self.raid_data)

async def execute_raid(channel, raid_data):
    global active_raid
    active_raid = None  # Giải phóng cờ active

    participants = raid_data["participants"]
    if not participants:
        await channel.send("⛩️ Reimu Dị Hình đã biến mất vào hư không vì không ai dám đối đầu...")
        return

    num_players = len(participants)
    dmg_each = BOSS_CONFIG["power"] // num_players  # Chia đều 10k damage

    # Thu thập chỉ số của tất cả người chơi
    total_raid_power = 0
    player_reports = []

    for uid in participants:
        p = get_player(uid)
        lvl_buff = (p["level"] - 1) * 10
        team_pwr = 0
        team_hp = 0
        card_names = []
        for cid in p.get("team", []):
            card = CARDS_DATA.get(cid)
            if card:
                team_pwr += card["power"] + lvl_buff
                team_hp += card["hp"] + lvl_buff
                card_names.append(card["name"])

        survived = team_hp >= dmg_each
        total_raid_power += team_pwr
        status_str = f"✅ Sống sót (HP: {team_hp} > {dmg_each} DMG)" if survived else f"💀 Tử trận (HP: {team_hp} < {dmg_each} DMG)"
        player_reports.append(f"• **{p['username']}** (Lv.{p['level']}): Sát thương {team_pwr:,} | {status_str}")

    boss_hp_left = max(0, BOSS_CONFIG["hp"] - total_raid_power)
    boss_defeated = boss_hp_left == 0

    embed = discord.Embed(
        title="⚔️ KẾT QUẢ TRẬN TẬP KÍCH: REIMU DỊ HÌNH!",
        description=f"**Máu Boss:** {BOSS_CONFIG['hp']:,} HP\n**Tổng Sát Thương Quân Đoàn Gây Ra:** {total_raid_power:,} DMG\n**Sát thương Boss phản đòn mỗi người:** {dmg_each:,} DMG",
        color=0x10B981 if boss_defeated else 0xEF4444
    )
    embed.set_thumbnail(url=BOSS_CONFIG["image"])
    embed.add_field(name="📋 Báo Cáo Chiến Binh:", value="\n".join(player_reports), inline=False)

    if boss_defeated:
        embed.add_field(
            name="🎉 CHIẾN THẮNG HUY HOÀNG!",
            value=f"Reimu Dị Hình đã bị tiêu diệt tan tác!\n**Phần thưởng Rương Rơi Cho Mỗi Chiến Binh (Tổng 3 rương card):**\n- Tỉ lệ mỗi rương: 10% Thẻ S, 40% Thẻ A, 50% Thẻ B!",
            inline=False
        )
        # Phát thưởng cho từng người chơi: mở 3 rương
        reward_summaries = []
        for uid in participants:
            p = get_player(uid)
            p_rewards = []
            for chest_idx in range(3):
                roll = random.random()
                if roll < 0.10:
                    chosen = random.choice(CARDS_BY_RANK["S"])
                elif roll < 0.50:
                    chosen = random.choice(CARDS_BY_RANK["A"])
                else:
                    chosen = random.choice(CARDS_BY_RANK["B"])
                cid_str = str(chosen["id"])
                p["inventory"][cid_str] = p["inventory"].get(cid_str, 0) + 1
                p_rewards.append(f"[{chosen['rank']}] {chosen['name']}")
            # Thêm XP thắng boss
            p["xp"] += 150
            save_player(p)
            reward_summaries.append(f"🎁 **{p['username']}** nhận: {', '.join(p_rewards)} (+150 XP)")

        embed.add_field(name="💎 Mở Rương Chiến Lợi Phẩm:", value="\n".join(reward_summaries), inline=False)
    else:
        embed.add_field(
            name="❌ THẤT BẠI!",
            value=f"Reimu Dị Hình còn sót lại **{boss_hp_left:,} HP** và đã xé rách không gian trốn thoát! Hãy nâng cấp đội hình và quay lại phục thù!",
            inline=False
        )

    await channel.send(embed=embed)

# ==============================================================================
# 6. SỰ KIỆN BOT ON_READY & ON_MESSAGE (CHAT VỚI REIMU + RANDOM BOSS 10%)
# ==============================================================================
@bot.event
async def on_ready():
    print(f"Bot Hakurei Reimu đã khởi động thành công: {bot.user.name}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} Slash Commands!", flush=True)
    except Exception as e:
        print(f"Lỗi đồng bộ slash command: {e}", flush=True)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Đền Hakurei | /help | /pull | /battle"
        )
    )

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.author == bot.user:
        return

    content_lower = message.content.lower()

    # 1. RANDOM 10% XUẤT HIỆN BOSS REIMU DỊ HÌNH KHI CHAT
    global active_raid
    if active_raid is None and not content_lower.startswith("!") and not content_lower.startswith("/"):
        if random.random() < 0.10:  # 10% cơ hội xuất hiện
            active_raid = {
                "channel_id": message.channel.id,
                "participants": [],
                "names": [],
                "created_at": datetime.now().isoformat()
            }
            embed = discord.Embed(
                title="🚨 CẢNH BÁO KHẨN CẤP: DỊ BIẾN XUẤT HIỆN!",
                description=f"**{BOSS_CONFIG['name']}**\n*{BOSS_CONFIG['desc']}*",
                color=0xDC2626
            )
            embed.set_image(url=BOSS_CONFIG["image"])
            embed.add_field(name="❤️ Máu Boss (HP):", value=f"{BOSS_CONFIG['hp']:,} HP", inline=True)
            embed.add_field(name="⚔️ Sát Thương (Power):", value=f"{BOSS_CONFIG['power']:,} DMG\n*(Chia đều cho các thành viên tham chiến)*", inline=True)
            embed.add_field(name=f"👥 Người Tham Gia (0/{BOSS_CONFIG['max_players']}):", value="Chưa có ai", inline=False)
            embed.add_field(
                name="🎁 Phần Thưởng Rương Rơi (3 Rương):",
                value="• 10% Rơi Card Rank S\n• 40% Rơi Card Rank A\n• 50% Rơi Card Rank B\n*Tham gia hoàn toàn MIỄN PHÍ!*",
                inline=False
            )
            embed.set_footer(text="Bấm 'Tham Gia' và chuẩn bị đội hình để chiến đấu!")
            
            view = RaidJoinView(active_raid)
            msg = await message.channel.send(embed=embed, view=view)
            active_raid["msg"] = msg

    # 2. XỬ LÝ TRÒ CHUYỆN VỚI REIMU (NHẮC TÊN, TAG, HOẶC REPLY)
    is_reply_to_reimu = False
    if message.reference and message.reference.resolved:
        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message) and resolved.author == bot.user:
            is_reply_to_reimu = True

    is_mentioned = bot.user in message.mentions if bot.user else False
    has_reimu_name = "reimu" in content_lower

    if is_mentioned or has_reimu_name or is_reply_to_reimu:
        clean_text = message.content
        if bot.user:
            clean_text = clean_text.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not clean_text:
            clean_text = "Chào Reimu!"

        author_name = message.author.display_name
        is_father = "han seiki" in author_name.lower() or "seiki" in author_name.lower()

        role_instruction = ""
        if is_father:
            role_instruction = "\n[Người nói là HAN SEIKI - BỐ NUÔI của bạn. Xưng con gọi ba, cực kỳ ngoan ngoãn, dịu dàng, hiếu thảo và lễ phép!]"
        else:
            role_instruction = f"\n[Người nói là khách viếng đền tên: {author_name}. Hãy xưng ta gọi ngươi, đanh đá và nhớ đòi cúng tiền công đức!]"

        saved_history = get_conversation_history(message.channel.id, message.author.id)
        history_context = ""
        if saved_history:
            history_context = "\n[LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY]:\n" + "\n".join(saved_history[-6:]) + "\n"

        async with message.channel.typing():
            try:
                reply_text = await ask_gemini(
                    contents=f"{history_context}[{author_name}]: {clean_text}",
                    system_instruction=REIMU_SYSTEM_PROMPT + role_instruction,
                    temperature=0.85
                )
                if not reply_text:
                    reply_text = "Hừ... Nhà ngươi lải nhải cái gì thế hả?"
                if len(reply_text) > 1950:
                    reply_text = reply_text[:1950] + "..."

                saved_history.append(f"{author_name}: {clean_text}")
                saved_history.append(f"Reimu: {reply_text}")
                save_conversation_history(message.channel.id, message.author.id, saved_history)

                await message.reply(reply_text, mention_author=False)
            except Exception as e:
                print(f"Lỗi AI Chat: {e}", flush=True)
                await message.reply("⛩️ Hừ, bùa chú đền Hakurei tạm thời bị nhiễu loạn linh lực! Đợi vài giây rồi gọi lại ta!", mention_author=False)

    await bot.process_commands(message)

# ==============================================================================
# 7. CƠ CHẾ GACHA PULL TOUHOU
# Tỉ lệ: SS: 0.01%, S: 2%, A: 20%, B: 77.99%
# Trùng pull: SS = 4 pull, S = 2 pull, A = 0.5 pull, B = 0.3333 pull
# ==============================================================================
def execute_single_pull(player):
    roll = random.random()  # [0.0, 1.0)
    if roll < 0.0001:  # 0.01%
        chosen = random.choice(CARDS_BY_RANK["SS"])
    elif roll < 0.0201:  # 2%
        chosen = random.choice(CARDS_BY_RANK["S"])
    elif roll < 0.2201:  # 20%
        chosen = random.choice(CARDS_BY_RANK["A"])
    else:  # 77.99%
        chosen = random.choice(CARDS_BY_RANK["B"])

    cid_str = str(chosen["id"])
    already_owned = player["inventory"].get(cid_str, 0)
    is_duplicate = already_owned > 0

    player["inventory"][cid_str] = already_owned + 1

    converted_pulls = 0.0
    if is_duplicate:
        if chosen["rank"] == "SS":
            converted_pulls = 4.0
        elif chosen["rank"] == "S":
            converted_pulls = 2.0
        elif chosen["rank"] == "A":
            converted_pulls = 0.5
        elif chosen["rank"] == "B":
            converted_pulls = 1.0 / 3.0  # 1/3 pull

        player["pull_tickets"] += converted_pulls

    return chosen, is_duplicate, converted_pulls

# ==============================================================================
# 8. SLASH COMMANDS & PREFIX COMMANDS
# ==============================================================================

# --- LỆNH /pull hoặc !pull ---
async def handle_pull(ctx_or_interaction, count: int = 1):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")

    if count < 1: count = 1
    if count > 10: count = 10  # Tối đa quay 10 lần một lượt

    # Tính toán lượt quay khả dụng (ưu tiên trừ free_pulls_remaining trước, sau đó trừ pull_tickets)
    total_available = player.get("free_pulls_remaining", 0) + int(player.get("pull_tickets", 0))

    if total_available < count:
        msg = f"❌ Bạn không đủ lượt pull! (Đang có: {player.get('free_pulls_remaining', 0)} free + {player.get('pull_tickets', 0):.1f} vé, cần: {count}).\nDùng `/daily` để nhận thêm vé mỗi ngày!" if lang == "vi" else f"❌ Not enough pulls! (Available: {player.get('free_pulls_remaining', 0)} free + {player.get('pull_tickets', 0):.1f} tickets, needed: {count}).\nUse `/daily` to get daily tickets!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Trừ lượt pull
    needed = count
    free_used = min(player["free_pulls_remaining"], needed)
    player["free_pulls_remaining"] -= free_used
    needed -= free_used
    player["pull_tickets"] -= float(needed)

    results = []
    total_converted = 0.0
    for _ in range(count):
        card, is_dup, conv = execute_single_pull(player)
        total_converted += conv
        dup_text = f" *(Trùng! +{conv:.2f} lượt pull)*" if is_dup else " ✨ **[MỚI]**"
        results.append(f"• **[{card['rank']}] {card['name']}** (Power: {card['power']} | HP: {card['hp']}){dup_text}")

    save_player(player)

    title = f"🌸 KẾT QUẢ PULL THẺ GACHA ({count} LƯỢT)" if lang == "vi" else f"🌸 GACHA PULL RESULTS ({count} PULLS)"
    last_card = card
    embed = discord.Embed(
        title=title,
        description="\n".join(results),
        color=0xDC2626 if any(c.startswith("• **[SS]") for c in results) else 0x3B82F6
    )
    embed.set_thumbnail(url=last_card["image"])
    remaining_info = f"Vé pull còn lại: {player['pull_tickets']:.2f} | Free hôm nay: {player['free_pulls_remaining']}/5" if lang == "vi" else f"Remaining Tickets: {player['pull_tickets']:.2f} | Free Today: {player['free_pulls_remaining']}/5"
    embed.set_footer(text=remaining_info)

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="pull", description="Quay thẻ nhân vật Touhou (Free 5 lượt/ngày)")
@app_commands.describe(so_luong="Số lượt quay (1 đến 10, mặc định: 1)")
async def slash_pull(interaction: discord.Interaction, so_luong: int = 1):
    await handle_pull(interaction, so_luong)

@bot.command(name="pull")
async def prefix_pull(ctx, count: int = 1):
    await handle_pull(ctx, count)


# --- LỆNH /daily hoặc !daily ---
async def handle_daily(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")
    today = datetime.now().strftime("%Y-%m-%d")

    if player.get("last_daily_date") == today:
        msg = "⛩️ Hôm nay bạn đã nhận vé Daily rồi! Hãy quay lại vào ngày mai nhé!" if lang == "vi" else "⛩️ You already claimed your daily pull today! Come back tomorrow!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    player["last_daily_date"] = today
    player["pull_tickets"] += 1.0
    save_player(player)

    embed = discord.Embed(
        title="🎁 ĐIỂM DANH HÀNG NGÀY / DAILY REWARD",
        description=f"Chúc mừng **{user.display_name}** đã viếng đền Hakurei!\nBạn nhận được: **+1 Lượt Pull** 🎟️\nTổng vé pull hiện có: **{player['pull_tickets']:.2f}**" if lang == "vi" else f"Congratulations **{user.display_name}**!\nYou received: **+1 Pull Ticket** 🎟️\nTotal Tickets: **{player['pull_tickets']:.2f}**",
        color=0xF59E0B
    )
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="daily", description="Nhận 1 lượt pull miễn phí mỗi ngày")
async def slash_daily(interaction: discord.Interaction):
    await handle_daily(interaction)

@bot.command(name="daily")
async def prefix_daily(ctx):
    await handle_daily(ctx)


# --- LỆNH /team hoặc !team ---
async def handle_team(ctx_or_interaction, action: str = "view", card_id: int = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")
    lvl_buff = (player["level"] - 1) * 10

    if action.lower() == "add":
        if not card_id or card_id not in CARDS_DATA:
            msg = "Vui lòng nhập số ID thẻ hợp lệ (từ 1 đến 20)!" if lang == "vi" else "Please enter a valid card ID (1 to 20)!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        cid_str = str(card_id)
        if player["inventory"].get(cid_str, 0) < 1:
            msg = f"Bạn chưa sở hữu thẻ **#{card_id} {CARDS_DATA[card_id]['name']}**! Hãy dùng `/pull` để quay nhé." if lang == "vi" else f"You don't own card **#{card_id} {CARDS_DATA[card_id]['name']}**! Pull cards via `/pull`."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        if card_id in player["team"]:
            msg = "Thẻ này đã có trong đội hình của bạn rồi!" if lang == "vi" else "This card is already in your team!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        if len(player["team"]) >= 3:
            msg = "Đội hình chỉ tối đa 3 thẻ! Hãy dùng `/team remove` trước khi thêm thẻ mới." if lang == "vi" else "Team limit is 3 cards! Use `/team remove` first."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        player["team"].append(card_id)
        save_player(player)
        card = CARDS_DATA[card_id]
        msg = f"✅ Đã thêm **[{card['rank']}] {card['name']}** vào đội hình! ({len(player['team'])}/3)" if lang == "vi" else f"✅ Added **[{card['rank']}] {card['name']}** to your team! ({len(player['team'])}/3)"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    elif action.lower() == "remove":
        if not card_id or card_id not in player["team"]:
            msg = "Vui lòng nhập ID thẻ đang có trong đội hình để gỡ!" if lang == "vi" else "Please specify a card ID currently in your team to remove!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        player["team"].remove(card_id)
        save_player(player)
        card = CARDS_DATA[card_id]
        msg = f"🗑️ Đã gỡ **{card['name']}** khỏi đội hình! ({len(player['team'])}/3)" if lang == "vi" else f"🗑️ Removed **{card['name']}** from your team! ({len(player['team'])}/3)"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Mặc định là action = "view"
    embed = discord.Embed(
        title=f"🛡️ ĐỘI HÌNH CỦA {user.display_name.upper()} (Lv.{player['level']})" if lang == "vi" else f"🛡️ {user.display_name.upper()}'S TEAM (Lv.{player['level']})",
        description=f"**Cấp Độ:** Lv.{player['level']} (XP: {player['xp'] % 100}/100)\n**Buff Chỉ Số Mỗi Cấp:** +{lvl_buff} Power & HP cho mỗi thẻ!" if lang == "vi" else f"**Level:** Lv.{player['level']} (XP: {player['xp'] % 100}/100)\n**Level Buff:** +{lvl_buff} Power & HP per card!",
        color=0x3B82F6
    )
    if not player["team"]:
        embed.add_field(name="Đội hình trống!", value="Dùng `/team add [id]` để đưa thẻ vào đội hình chiến đấu!", inline=False)
    else:
        tot_pwr = 0
        tot_hp = 0
        for idx, cid in enumerate(player["team"], 1):
            c = CARDS_DATA[cid]
            pwr = c["power"] + lvl_buff
            hp = c["hp"] + lvl_buff
            tot_pwr += pwr
            tot_hp += hp
            embed.add_field(
                name=f"Vị trí #{idx}: [{c['rank']}] {c['name']} (ID: {c['id']})",
                value=f"⚔️ Power: **{pwr:,}** (Gốc {c['power']} + {lvl_buff})\n❤️ HP: **{hp:,}** (Gốc {c['hp']} + {lvl_buff})",
                inline=False
            )
        embed.add_field(
            name="📊 Tổng Lực Chiến Đội Hình:",
            value=f"⚔️ Tổng Power: **{tot_pwr:,}** | ❤️ Tổng HP: **{tot_hp:,}**",
            inline=False
        )
        first_card = CARDS_DATA[player["team"][0]]
        embed.set_thumbnail(url=first_card["image"])

    embed.set_footer(text="Lệnh: /team add <id> | /team remove <id> | /battle")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="team", description="Xem hoặc sắp xếp đội hình 3 thẻ chiến đấu")
@app_commands.describe(
    hanh_dong="Hành động: view (xem), add (thêm), remove (gỡ)",
    id_the="ID thẻ từ 1 đến 20 (khi dùng add hoặc remove)"
)
@app_commands.choices(hanh_dong=[
    app_commands.Choice(name="Xem đội hình (view)", value="view"),
    app_commands.Choice(name="Thêm thẻ (add)", value="add"),
    app_commands.Choice(name="Gỡ thẻ (remove)", value="remove"),
])
async def slash_team(interaction: discord.Interaction, hanh_dong: app_commands.Choice[str], id_the: int = None):
    await handle_team(interaction, hanh_dong.value, id_the)

@bot.command(name="team")
async def prefix_team(ctx, action: str = "view", card_id: int = None):
    await handle_team(ctx, action, card_id)


# --- LỆNH /collection hoặc !collection ---
async def handle_collection(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")

    owned_count = 0
    lines = []
    for cid in range(1, 21):
        card = CARDS_DATA[cid]
        count = player["inventory"].get(str(cid), 0)
        if count > 0:
            owned_count += 1
            lines.append(f"✅ **#{card['id']:02d} [{card['rank']}] {card['name']}** ×{count}")
        else:
            lines.append(f"🔒 **#{card['id']:02d} [{card['rank']}] {card['name']}** *(Chưa có)*")

    embed = discord.Embed(
        title=f"📖 BỘ SƯU TẬP THẺ TOUHOU ({owned_count}/20)" if lang == "vi" else f"📖 TOUHOU CARD COLLECTION ({owned_count}/20)",
        description="\n".join(lines),
        color=0x8B5CF6
    )
    embed.set_footer(text="Quay thêm thẻ bằng lệnh: /pull")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="collection", description="Kiểm tra bộ sưu tập 20 nhân vật Touhou đã sở hữu")
async def slash_collection(interaction: discord.Interaction):
    await handle_collection(interaction)

@bot.command(name="collection")
async def prefix_collection(ctx):
    await handle_collection(ctx)


# --- LỆNH /battle hoặc !battle (AUTO BATTLE KIẾM 50-100 XP) ---
async def handle_battle(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")

    if not player.get("team") or len(player["team"]) == 0:
        msg = "⚠️ Bạn chưa thiết lập đội hình! Hãy dùng `/team add <id>` để đưa thẻ vào đội trước khi khiêu chiến!" if lang == "vi" else "⚠️ You haven't set up a team! Use `/team add <id>` first!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Lấy đối thủ (từ player khác hoặc sinh team ảo tương đương)
    opponents = get_all_opponents(exclude_id=user.id)
    if opponents:
        target = random.choice(opponents)
        opp_name = target.get("username", "Đối thủ Gensokyo")
        opp_level = target.get("level", 1)
        opp_team_ids = target.get("team", [17, 18, 20])
    else:
        # Đội hình bóng ma Gensokyo
        opp_name = "Ảo Ảnh Gensokyo (Ghost Team)"
        opp_level = max(1, player["level"] + random.randint(-1, 1))
        opp_team_ids = random.sample(list(CARDS_DATA.keys()), min(3, len(CARDS_DATA)))

    # Tính chỉ số của 2 đội
    player_buff = (player["level"] - 1) * 10
    opp_buff = (opp_level - 1) * 10

    player_pwr = sum(CARDS_DATA[cid]["power"] + player_buff for cid in player["team"])
    player_hp = sum(CARDS_DATA[cid]["hp"] + player_buff for cid in player["team"])

    opp_pwr = sum(CARDS_DATA[cid]["power"] + opp_buff for cid in opp_team_ids)
    opp_hp = sum(CARDS_DATA[cid]["hp"] + opp_buff for cid in opp_team_ids)

    # Mô phỏng Auto Battle (Turn-based damage)
    # Player gây damage cho Opponent, Opponent gây damage cho Player
    player_surv_hp = player_hp - opp_pwr
    opp_surv_hp = opp_hp - player_pwr

    # Xác định thắng bại (nếu cả 2 cùng sống thì tính theo tỉ lệ phần trăm máu còn lại)
    if opp_surv_hp <= 0 and player_surv_hp > 0:
        win = True
    elif player_surv_hp <= 0 and opp_surv_hp > 0:
        win = False
    else:
        win = (player_surv_hp / player_hp) >= (opp_surv_hp / opp_hp)

    # Thưởng XP (50-100 XP mỗi trận)
    gained_xp = random.randint(50, 100)
    old_lvl = player["level"]
    player["xp"] += gained_xp
    player["battles_total"] = player.get("battles_total", 0) + 1
    if win:
        player["battles_won"] = player.get("battles_won", 0) + 1
    save_player(player)

    new_lvl = player["level"]
    lvl_up_msg = f"\n🎉 **CHÚC MỪNG BẠN ĐÃ LÊN CẤP {new_lvl}!** (+10 Power & HP buff)" if new_lvl > old_lvl else ""

    result_title = f"⚔️ TRẬN CHIẾN: {user.display_name} VS {opp_name}"
    embed = discord.Embed(
        title=result_title,
        color=0x10B981 if win else 0xEF4444
    )
    embed.add_field(
        name=f"🔵 {user.display_name} (Lv.{player['level']})",
        value=f"⚔️ Power: {player_pwr:,} | ❤️ HP: {player_hp:,}\n*Máu còn lại:* {max(0, player_surv_hp):,}",
        inline=True
    )
    embed.add_field(
        name=f"🔴 {opp_name} (Lv.{opp_level})",
        value=f"⚔️ Power: {opp_pwr:,} | ❤️ HP: {opp_hp:,}\n*Máu còn lại:* {max(0, opp_surv_hp):,}",
        inline=True
    )
    res_str = "🏆 **CHIẾN THẮNG!**" if win else "💀 **THẤT BẠI!**"
    embed.add_field(
        name="Kết Quả Trận Đấu:",
        value=f"{res_str}\nNhận được: **+{gained_xp} XP** (Tổng XP: {player['xp']}, Lv.{new_lvl}){lvl_up_msg}",
        inline=False
    )
    embed.set_footer(text="Mỗi cấp cần 100 XP để thăng tiến, tối đa Lv.100 (+1000 chỉ số)")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="battle", description="Đấu tự động với đội hình người chơi khác để nhận 50-100 XP")
async def slash_battle(interaction: discord.Interaction):
    await handle_battle(interaction)

@bot.command(name="battle")
async def prefix_battle(ctx):
    await handle_battle(ctx)


# --- LỆNH /language hoặc !language ---
async def handle_language(ctx_or_interaction, lang: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    chosen_lang = "en" if lang.lower() in ["en", "english", "eng"] else "vi"
    player["language"] = chosen_lang
    save_player(player)

    msg = "🇻🇳 Đã chuyển ngôn ngữ giao diện bot sang **Tiếng Việt**!" if chosen_lang == "vi" else "🇬🇧 Switched bot language to **English**!"
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(msg)
    else:
        await ctx_or_interaction.send(msg)

@bot.tree.command(name="language", description="Chọn ngôn ngữ giao diện: vi (Tiếng Việt) hoặc en (English)")
@app_commands.describe(ngon_ngu="Lựa chọn ngôn ngữ: vi hoặc en")
@app_commands.choices(ngon_ngu=[
    app_commands.Choice(name="🇻🇳 Tiếng Việt", value="vi"),
    app_commands.Choice(name="🇬🇧 English", value="en"),
])
async def slash_language(interaction: discord.Interaction, ngon_ngu: app_commands.Choice[str]):
    await handle_language(interaction, ngon_ngu.value)

@bot.command(name="language", aliases=["lang"])
async def prefix_language(ctx, lang: str = "vi"):
    await handle_language(ctx, lang)


# --- LỆNH /help hoặc !help ---
async def handle_help(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")

    if lang == "vi":
        desc = """
⛩️ **HAKUREI REIMU DISCORD BOT - BẢN ĐỒ LỆNH**

**🎮 HỆ THỐNG GACHA & CARD BATTLE:**
• `/pull [số_lượng]` hoặc `!pull`: Quay thẻ nhân vật (Free 5 lượt/ngày).
• `/daily` hoặc `!daily`: Điểm danh nhận 1 vé pull mỗi ngày.
• `/team view` hoặc `!team`: Xem đội hình 3 thẻ và cấp độ hiện tại.
• `/team add <id>`: Thêm thẻ vào đội hình (tối đa 3 thẻ).
• `/team remove <id>`: Gỡ thẻ khỏi đội hình.
• `/collection` hoặc `!collection`: Xem bộ sưu tập 20 nhân vật Touhou.
• `/battle` hoặc `!battle`: Tự động giao đấu với người chơi khác, nhận 50-100 XP.
• `/language <vi/en>` hoặc `!lang`: Đổi ngôn ngữ hiển thị.

**👹 DỊ BIẾN REIMU DỊ HÌNH (RAID BOSS):**
• Xuất hiện ngẫu nhiên **10%** khi trò chuyện trong server!
• Boss 25,000 HP, sát thương 10,000 DMG chia đều cho tối đa 6 người.
• Tham gia hoàn toàn **MIỄN PHÍ**!
• Diệt boss nhận ngay **3 Rương Card** (10% S, 40% A, 50% B)!

**💬 TRÒ CHUYỆN VỚI REIMU:**
• Gọi "reimu", tag `@Reimu` hoặc bấm Trả lời (Reply) tin nhắn của Reimu để tâm sự!
• Lưu ý: Reimu rất mê tiền công đức, nhưng cực kỳ hiếu thảo với bố nuôi Han Seiki!
• `/wiki <tên>`: Tra cứu bách khoa toàn thư Touhou Project.
• `/danmaku <spell>`: Thách đấu Spell Card với Reimu.
• `/clearmem`: Xoá ký ức hội thoại.
• `/sync`: Dọn dẹp lệnh trùng lặp trên server.
"""
    else:
        desc = """
⛩️ **HAKUREI REIMU DISCORD BOT - COMMAND DIRECTORY**

**🎮 GACHA & CARD BATTLE SYSTEM:**
• `/pull [count]` or `!pull`: Pull Touhou character cards (5 Free pulls/day).
• `/daily` or `!daily`: Claim 1 free pull ticket every day.
• `/team view` or `!team`: Check your 3-card lineup and level.
• `/team add <id>`: Add a card to your battle team (Max 3).
• `/team remove <id>`: Remove a card from your team.
• `/collection` or `!collection`: View your 20 Touhou card album.
• `/battle` or `!battle`: Auto battle other players to earn 50-100 XP.
• `/language <vi/en>` or `!lang`: Switch display language.

**👹 ABERRANT REIMU (RANDOM RAID BOSS):**
• 10% random spawn chance when chatting in server channels!
• Boss 25,000 HP, 10,000 DMG split among up to 6 players.
• Free to join via the Discord button!
• Defeat boss to earn 3 Card Chests (10% S, 40% A, 50% B)!

**💬 CHAT WITH REIMU:**
• Mention @Reimu or say "reimu" or reply to her message!
• `/wiki <name>`: Lookup Touhou Project lore.
• `/danmaku <spell>`: Challenge Reimu to spell card duels.
• `/clearmem`: Clear conversation memory.
"""
    embed = discord.Embed(title="🌸 HƯỚNG DẪN LỆNH BOT REIMU", description=desc, color=0xDC2626)
    embed.set_footer(text="Hakurei Shrine • Powered by Google Gemini Flash & MongoDB Atlas")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="help", description="Xem hướng dẫn toàn bộ lệnh chơi game và trò chuyện của Reimu")
async def slash_help(interaction: discord.Interaction):
    await handle_help(interaction)

@bot.command(name="help")
async def prefix_help(ctx):
    await handle_help(ctx)


# --- LỆNH /wiki ---
@bot.tree.command(name="wiki", description="Tra cứu thông tin nhân vật hoặc dị biến trong Touhou Project")
@app_commands.describe(nhan_vat="Tên nhân vật Touhou cần tra cứu (ví dụ: Marisa, Remilia, Flandre...)")
async def touhou_wiki(interaction: discord.Interaction, nhan_vat: str):
    await interaction.response.defer()
    wiki_prompt = f"""
Tra cứu thông tin Touhou Project cho: "{nhan_vat}".
Tóm tắt ngắn gọn: Danh hiệu, Chủng tộc, Năng lực, Nơi ở, Spell Card nổi tiếng, Theme BGM, và lời bình đanh đá của Reimu.
"""
    try:
        wiki_text = await ask_gemini(wiki_prompt, REIMU_SYSTEM_PROMPT, temperature=0.7)
        embed = discord.Embed(title=f"🌸 Bách Khoa Gensokyo: {nhan_vat}", description=wiki_text[:4000], color=0xDC2626)
        embed.set_footer(text="Touhou Project Wiki Database • Gemini Flash + MongoDB")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("⛩️ Hòm công đức đông khách, bùa chú đang bị quá tải. Bạn hãy thử lại sau nhé!")

# --- LỆNH /danmaku ---
@bot.tree.command(name="danmaku", description="Thách đấu hoặc yêu cầu Reimu giải mã Spell Card đạn mạc")
@app_commands.describe(spell_name="Tên Spell Card (ví dụ: Fantasy Seal, Master Spark, Scarlet Gensokyo...)")
async def danmaku_challenge(interaction: discord.Interaction, spell_name: str):
    await interaction.response.defer()
    prompt = f"Người dùng hỏi hoặc thách đấu về Spell Card đạn mạc: '{spell_name}'. Hãy bình luận đanh đá và phân tích vẻ đẹp đạn mạc theo giọng điệu Reimu!"
    try:
        danmaku_text = await ask_gemini(prompt, REIMU_SYSTEM_PROMPT, temperature=0.8)
        embed = discord.Embed(title=f"✨ Thách Đấu Spell Card: {spell_name}", description=danmaku_text[:4000], color=0x06B6D4)
        embed.set_footer(text="Quy Tắc Đạn Mạc Gensokyo • Hakurei Reimu")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("⛩️ Bùa chú đang bị nhiễu loạn, thử lại sau vài giây nhé!")

# --- LỆNH /clearmem ---
@bot.tree.command(name="clearmem", description="Xóa sạch ký ức trò chuyện của Reimu với bạn trong kênh này")
async def slash_clear_memory(interaction: discord.Interaction):
    reset_memory(interaction.channel_id, interaction.user.id)
    author_name = interaction.user.display_name
    is_father = "han seiki" in author_name.lower() or "seiki" in author_name.lower()
    desc = "Ba ơi, con đã dọn dẹp và làm mới lại ký ức rồi ạ!" if is_father else f"Hừ! **{author_name}**, ta đã xóa sạch ký ức nhảm nhí với ngươi trên MongoDB rồi! Bỏ tiền vào hòm rồi nói chuyện lại!"
    embed = discord.Embed(title="🧹 Tẩy Não / Xóa Ký Ức", description=desc, color=0x10B981)
    await interaction.response.send_message(embed=embed)

@bot.command(name="clearmem")
async def prefix_clear_memory(ctx):
    reset_memory(ctx.channel.id, ctx.author.id)
    await ctx.send("⛩️ Đã dọn dẹp và làm mới lại ký ức hội thoại!")

# --- LỆNH /sync ---
@bot.tree.command(name="sync", description="Xóa lệnh trùng lặp và đồng bộ lại 1 bản duy nhất")
async def slash_sync_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        bot.tree.clear_commands(guild=interaction.guild)
        await bot.tree.sync(guild=interaction.guild)
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã dọn sạch trùng lặp! Giờ có {len(synced)} lệnh Slash chuẩn. Bấm Ctrl+R trên Discord để cập nhật nhé.")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi khi đồng bộ: {e}")

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def prefix_sync_commands(ctx):
    try:
        bot.tree.clear_commands(guild=ctx.guild)
        await bot.tree.sync(guild=ctx.guild)
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Đã dọn sạch trùng lặp! Giờ có {len(synced)} lệnh Slash chuẩn.")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi đồng bộ: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN trong biến môi trường (.env)!", flush=True)
    else:
        bot.run(DISCORD_TOKEN)
