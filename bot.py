# ==============================================================================
# HAKUREI REIMU DISCORD BOT - FULL EDITION (UPDATED)
# GEMINI FLASH CHATBOT + MONGODB ATLAS CLOUD + TOUHOU GACHA & AUTO-BATTLE & RAID
# ==============================================================================
# CÁC TÍNH NĂNG MỚI ĐÃ ĐƯỢC CẬP NHẬT:
# 1. BOSS STATS: Máu tăng lên 35,000 HP, DMG tăng lên 15,000 DMG
# 2. BOSS DROP: Rương chiến lợi phẩm (3 rương) quy đổi 100% thành Vé Pull (giữ nguyên tỉ lệ S: 10% -> 2 vé, A: 40% -> 0.5 vé, B: 50% -> 1/3 vé)
# 3. BOSS COOLDOWN: Hồi chiêu 15 phút tính từ lúc có bất kỳ người chơi nào tham gia raid
# 4. ADMIN COMMANDS: /admin_set_level (set cấp và đồng bộ XP) & /admin_confiscate (tước đoạt thẻ phạt cheat)
# 5. LEVEL UP CƠ CHẾ MỚI: Mỗi cấp tăng thêm +50 XP (Lv.1 cần 100 XP, Lv.2 cần 150 XP, Lv.3 cần 200 XP...) CHUẨN XÁC TUYỆT ĐỐI KHÔNG BUG!
# ==============================================================================

import os
import time
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
# QUẢN TRỊ VIÊN DUY NHẤT ĐƯỢC PHÉP DÙNG LỆNH ADMIN (OWNER EXCLUSIVE)
# ==============================================================================
AUTHORIZED_ADMIN_ID = 1502579398560317441

def is_authorized_admin(user_id: int) -> bool:
    """Kiểm tra chỉ duy nhất ID 1502579398560317441 mới có quyền thực thi lệnh Admin"""
    try:
        return int(user_id) == AUTHORIZED_ADMIN_ID
    except (ValueError, TypeError):
        return False

# ==============================================================================
# 1. WEB SERVER CHO RENDER FREE (GIỮ CONTAINER KHÔNG BỊ QUÉT LỖI PORT)
# ==============================================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Hakurei Reimu Discord Bot (Gacha + Battle + Raid + Admin) is online!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==============================================================================
# 2. HỆ THỐNG CẤP ĐỘ & XP MỚI (+50 XP MỖI CẤP, CHUẨN XÁC TUYỆT ĐỐI KHÔNG BUG)
# ==============================================================================
MAX_LEVEL = 100

def get_xp_needed_for_level(level: int) -> int:
    """
    Số XP cần tích lũy để thăng cấp từ `level` lên `level + 1`.
    Lv 1: cần 100 XP
    Lv 2: cần 150 XP (+50)
    Lv 3: cần 200 XP (+50)
    Công thức: 100 + (level - 1) * 50
    """
    if level < 1:
        level = 1
    return 100 + (level - 1) * 50

def get_total_xp_for_level(level: int) -> int:
    """
    Tổng XP tích lũy (Cumulative XP) cần có để đạt tới `level` tính từ lúc Lv 1 (0 XP).
    Lv 1: 0 XP
    Lv 2: 100 XP
    Lv 3: 100 + 150 = 250 XP
    Lv 4: 250 + 200 = 450 XP
    Lv 5: 450 + 250 = 700 XP
    Công thức toán học cấp số cộng: Sum_{k=1..n}(100 + 50*(k-1)) = 25*n*(n+3) với n = level - 1
    """
    if level <= 1:
        return 0
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    n = level - 1
    return 25 * n * (n + 3)

def calculate_level_from_xp(total_xp: int) -> int:
    """
    Tính chính xác cấp độ hiện tại dựa trên tổng XP tích lũy (Total XP).
    Tuyệt đối không bị bug, không bao giờ lệch điểm hoặc vượt quá MAX_LEVEL.
    """
    if total_xp <= 0:
        return 1
    lvl = 1
    while lvl < MAX_LEVEL:
        next_threshold = get_total_xp_for_level(lvl + 1)
        if total_xp >= next_threshold:
            lvl += 1
        else:
            break
    return lvl

def get_level_progress(total_xp: int):
    """
    Trả về chi tiết:
    (level, xp_in_current_level, xp_needed_for_next_level, ratio_progress)
    """
    lvl = calculate_level_from_xp(total_xp)
    if lvl >= MAX_LEVEL:
        return lvl, 0, 0, 1.0
    base_xp = get_total_xp_for_level(lvl)
    xp_in_level = max(0, total_xp - base_xp)
    needed = get_xp_needed_for_level(lvl)
    ratio = min(1.0, max(0.0, xp_in_level / needed)) if needed > 0 else 1.0
    return lvl, xp_in_level, needed, ratio

# ==============================================================================
# 3. TOUHOU CARDS DATABASE (26 NHÂN VẬT CHUẨN THÔNG SỐ)
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
        "name": "Yuyuko Saigyouji",
        "rank": "S",
        "power": 620,
        "hp": 6200,
        "image": "https://media.discordapp.net/attachments/1527157582115111077/1549361604234313839/images.png?ex=6aaa6af0&is=6aa91970&hm=674ea5e76356fcd1cea0a0545f5eb9a5ea5d9513216ebf6bccbc175569ab934b&=&format=webp&quality=lossless"
    },
    9: {
        "id": 9,
        "name": "Flandre Scarlet",
        "rank": "S",
        "power": 610,
        "hp": 5700,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082626147483798/y4nci1hurauf1.png?ex=6aa9671e&is=6aa8159e&hm=a2b7e911c0855f2715e551e3ebfb0299758a3461ba0d6b14222e130bb2160ce2&=&format=webp&quality=lossless&width=361&height=512"
    },
    10: {
        "id": 10,
        "name": "Kaguya Houraisan",
        "rank": "S",
        "power": 590,
        "hp": 6400,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082450930696282/images.png?ex=6aa966f4&is=6aa81574&hm=363a0b7d509db06c3773fba176ede9646cfef4a95c5d2515703120d30bfc4e94&=&format=webp&quality=lossless&width=361&height=512"
    },
    11: {
        "id": 11,
        "name": "Remilia Scarlet",
        "rank": "S",
        "power": 560,
        "hp": 5600,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079793461633065/images.png?ex=6aa9647b&is=6aa812fb&hm=19fc0f72cd5fca597f9eeae493b1c7c663d11ffc98fff679bfd2dfdb588950e1&=&format=webp&quality=lossless"
    },
    12: {
        "id": 12,
        "name": "Utsuho Reiuji (Okuu)",
        "rank": "S",
        "power": 550,
        "hp": 5300,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081971169304647/images.png?ex=6aa96682&is=6aa81502&hm=6f7668c4db22133f1aa0bdc07ec7fa2c050ff4e4d220f744cd02e8cc04662c0f&=&format=webp&quality=lossless"
    },
    13: {
        "id": 13,
        "name": "Reimu Hakurei",
        "rank": "A",
        "power": 500,
        "hp": 5000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549078962746171463/images.png?ex=6aa963b5&is=6aa81235&hm=3fa720bd7311e4ca45789c6a0112327878135e9d9944c31c6ed2ea1f60885853&=&format=webp&quality=lossless"
    },
    14: {
        "id": 14,
        "name": "Fujiwara no Mokou",
        "rank": "A",
        "power": 490,
        "hp": 5200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080689079754812/images.png?ex=6aa96550&is=6aa813d0&hm=962822a973a1e1535007f1597c0c7b468a287ec0f3d212dcf58c7ca1d9a0c5a3&=&format=webp&quality=lossless"
    },
    15: {
        "id": 15,
        "name": "Kasen Ibaraki",
        "rank": "A",
        "power": 480,
        "hp": 4900,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080849083924531/images.png?ex=6aa96576&is=6aa813f6&hm=802e894777a879074a59fa3dcae74394f73523e31d9b9272f19e4aff95ec36aa&=&format=webp&quality=lossless"
    },
    16: {
        "id": 16,
        "name": "Sakuya Izayoi",
        "rank": "A",
        "power": 460,
        "hp": 4500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079438719844372/images.png?ex=6aa96426&is=6aa812a6&hm=263f21e095ef7f36f411473590d92012d350ab3e7b8ea13e72a443a0672a719a&=&format=webp&quality=lossless&width=307&height=512"
    },
    17: {
        "id": 17,
        "name": "Marisa Kirisame",
        "rank": "A",
        "power": 450,
        "hp": 4400,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081039660654612/images.png?ex=6aa965a4&is=6aa81424&hm=0ff6e9df5e0d49e483e0560bba442927385b8fa930187276b921012ad16071ad&=&format=webp&quality=lossless"
    },
    18: {
        "id": 18,
        "name": "Youmu Konpaku",
        "rank": "B",
        "power": 410,
        "hp": 4100,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081249036116059/images.png?ex=6aa965d6&is=6aa81456&hm=2dc107dd368c53b9c1a94c54e1cfe4a1d9b7ff6ac224dc830d6c9297d5b19e53&=&format=webp&quality=lossless"
    },
    19: {
        "id": 19,
        "name": "Reisen Udongein Inaba",
        "rank": "B",
        "power": 390,
        "hp": 3900,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081419777577130/images.png?ex=6aa965ff&is=6aa8147f&hm=8948e38a77f4c00d21819a6e34e2fd1a13b1853e4c92886d1e6ac3ccae6afd75&=&format=webp&quality=lossless"
    },
    20: {
        "id": 20,
        "name": "Patchouli Knowledge",
        "rank": "B",
        "power": 380,
        "hp": 3200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081654948134994/images.png?ex=6aa96637&is=6aa814b7&hm=7e444589e6db73d24fb53445ea713ddb5e5bcc7c75e58ea91a619a694f0d23eb&=&format=webp&quality=lossless&width=385&height=512"
    },
    21: {
        "id": 21,
        "name": "Cirno",
        "rank": "B",
        "power": 300,
        "hp": 3000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080400742195260/images.png?ex=6aa9650c&is=6aa8138c&hm=e3d3d5bf2196f4a3b0fdafcc37063c5ad16897726bdf5514be92b3f3b7719cc4&=&format=webp&quality=lossless"
    },
    22: {
        "id": 22,
        "name": "Hong Meiling",
        "rank": "C",
        "power": 260,
        "hp": 2800,
        "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362028601417869/images.png?ex=6aaa6b55&is=6aa919d5&hm=95498119b7d8e5f7563f28bde4efabe919878bcd40b70bf4037edb73eac009aa&=&format=webp&quality=lossless&width=363&height=512"
    },
    23: {
        "id": 23,
        "name": "Rumia",
        "rank": "C",
        "power": 220,
        "hp": 2200,
        "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362134440485004/images.png?ex=6aaa6b6e&is=6aa919ee&hm=860b0ede2ccf2585fb605cdef8864b141980395e5eee9d3f4f78c5692fa3827b&=&format=webp&quality=lossless&width=361&height=512"
    },
    24: {
        "id": 24,
        "name": "Mystia Lorelei",
        "rank": "C",
        "power": 200,
        "hp": 2000,
        "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362390641020948/84f96d0ce2f04a42a63cff967b6ec6bf.png?ex=6aaa6bab&is=6aa91a2b&hm=9c09d786873a4a70d3dbc27e10934ee7e8463964d89acc42cc1214e29e3185a2&=&format=webp&quality=lossless&width=385&height=512"
    },
    25: {
        "id": 25,
        "name": "Wriggle Nightbug",
        "rank": "C",
        "power": 180,
        "hp": 1800,
        "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362613421351043/images.png?ex=6aaa6be0&is=6aa91a60&hm=56779b03181c9c34cb7de4974bfdc60dc452be7d450818daeaeddbf8f36250d0&=&format=webp&quality=lossless"
    },
    26: {
        "id": 26,
        "name": "Tewi Inaba",
        "rank": "C",
        "power": 150,
        "hp": 1500,
        "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362906154410034/images.png?ex=6aaa6c26&is=6aa91aa6&hm=ac3b4dca861840ea6c0c5b41288fb528b56543df60081fe62ff774f75449e847&=&format=webp&quality=lossless"
    }
}

# Phân nhóm card theo Rank
CARDS_BY_RANK = {
    "SS": [c for c in CARDS_DATA.values() if c["rank"] == "SS"],
    "S":  [c for c in CARDS_DATA.values() if c["rank"] == "S"],
    "A":  [c for c in CARDS_DATA.values() if c["rank"] == "A"],
    "B":  [c for c in CARDS_DATA.values() if c["rank"] == "B"],
    "C":  [c for c in CARDS_DATA.values() if c["rank"] == "C"],
}

# ==============================================================================
# BOSS REIMU DỊ HÌNH - CHỈ SỐ MỚI (HP 35K, DMG 15K, COOLDOWN 15 PHÚT)
# ==============================================================================
BOSS_CONFIG = {
    "name": "Reimu Dị Hình - Phase 1",
    "desc": "Đó không phải Reimu, sẵn sàng giao chiến!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1549077421624401971/content.png?ex=6aa96245&is=6aa810c5&hm=c0248e497ee5afeed898b457736b39fc71368af3be1630f1cd59b5609c99fbeb&=&format=webp&quality=lossless&width=351&height=512",
    "hp": 35000,      # Phase 1: 35,000 HP
    "power": 15000,   # Phase 1: 15,000 DMG chia đều
    "max_players": 6,
    "cooldown_seconds": 15 * 60  # 15 phút (900s) sau khi có bất kỳ ai tham gia raid
}

BOSS_PHASE2_CONFIG = {
    "name": "Reimu Dị Hình - Thức Tỉnh (Phase 2)",
    "desc": "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội!",
    "image": "https://media.discordapp.net/attachments/1549063334781911070/1549275653239472148/artwork.png?ex=6aaa1ae3&is=6aa8c963&hm=7187404882d4b8b0fcef91ef64aee3c73711924e971fb7b28b6fb3bf394a47d3&=&format=webp&quality=lossless&width=640&height=336",
    "hp": 50000,      # Phase 2: 50,000 HP
    "power": 22000    # Phase 2: 22,000 DMG chia đều
}

# Biến toàn cục theo dõi thời gian hồi chiêu Boss tiếp theo
boss_cooldown_until = 0.0

# ==============================================================================
# 4. DATABASE SETUP: MONGODB ATLAS + SQLITE DỰ PHÒNG
# ==============================================================================
MONGO_URI = os.getenv("MONGO_URI")
use_mongo = False
mongo_client = None
users_collection = None
conversations_collection = None
players_collection = None
mongo_error_detail = "Biến môi trường MONGO_URI chưa được thiết lập."

def test_and_connect_mongo():
    global use_mongo, mongo_client, users_collection, conversations_collection, players_collection, mongo_error_detail
    current_uri = os.getenv("MONGO_URI")
    if not current_uri:
        mongo_error_detail = "Chưa thiết lập biến môi trường MONGO_URI trong .env hoặc Render Dashboard."
        use_mongo = False
        return False, mongo_error_detail

    if "xxxxxx" in current_uri:
        mongo_error_detail = "Chuỗi MONGO_URI vẫn chứa placeholder 'xxxxxx'. Bạn cần thay thế bằng subdomain cluster thật từ MongoDB Atlas."
        use_mongo = False
        return False, mongo_error_detail

    try:
        from pymongo import MongoClient
        client = MongoClient(current_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client["reimu_database"]
        users_collection = db["users"]
        conversations_collection = db["conversations"]
        players_collection = db["players"]
        mongo_client = client
        use_mongo = True
        mongo_error_detail = None
        print("✅ [DATABASE] Kết nối MONGODB ATLAS thành công! Dữ liệu game và ký ức được bảo toàn vĩnh viễn trên đám mây.", flush=True)
        return True, "Thành công"
    except Exception as e:
        use_mongo = False
        err_msg = f"{type(e).__name__}: {str(e)}"
        mongo_error_detail = err_msg
        print(f"⚠️ [DATABASE] Lỗi kết nối MongoDB ({err_msg}). Chuyển sang SQLite tạm thời.", flush=True)
        return False, err_msg

# Chạy kiểm tra kết nối ban đầu
if MONGO_URI:
    test_and_connect_mongo()

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
        "battles_total": 0,
        "last_battle_time": 0.0,
        "recent_opponents": []
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

    # Reset 5 lượt pull free mỗi ngày
    if data.get("free_pulls_date") != now_date:
        data["free_pulls_date"] = now_date
        data["free_pulls_remaining"] = 5

    # Âm thầm dịch chuyển ID thẻ cũ (>= 8 tăng 1 bậc do thêm #08 Yuyuko Saigyouji)
    # Không làm ảnh hưởng hay sai lệch lá bài người chơi đã lắp trong team và kho đồ
    if data.get("schema_version", 1) < 2:
        new_team = []
        for cid in data.get("team", []):
            try:
                cid_int = int(cid)
                if cid_int >= 8:
                    new_team.append(cid_int + 1)
                else:
                    new_team.append(cid_int)
            except Exception:
                new_team.append(cid)
        data["team"] = new_team

        old_inv = data.get("inventory", {})
        new_inv = {}
        for k, v in old_inv.items():
            try:
                k_int = int(k)
                if k_int >= 8:
                    new_inv[str(k_int + 1)] = v
                else:
                    new_inv[str(k_int)] = v
            except Exception:
                new_inv[str(k)] = v
        data["inventory"] = new_inv

        data["schema_version"] = 2
        save_player(data)

    # CẬP NHẬT: TÍNH LEVEL THEO HỆ THỐNG MỚI (+50 XP MỖI CẤP, TUYỆT ĐỐI KHÔNG BUG)
    data["level"] = calculate_level_from_xp(data.get("xp", 0))
    return data

def save_player(player_data):
    uid_str = str(player_data["user_id"])
    now_iso = datetime.now().isoformat()
    # Đồng bộ level dựa trên tổng XP tích lũy
    player_data["level"] = calculate_level_from_xp(player_data.get("xp", 0))
    
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
# 5. CẤU HÌNH BOT & GEMINI FLASH
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
    models = [
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.1-pro-preview",
        "gemini-3.0-flash",
        "gemini-flash-latest"
    ]
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
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "404" in err_str or "NOT_FOUND" in err_str:
                    break
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    await asyncio.sleep(0.5)
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
# 6. QUẢN LÝ BOSS RAID (35K HP, 15K DMG, RƯƠNG QUY ĐỔI VÉ PULL, COOLDOWN 15 PHÚT)
# ==============================================================================
active_raid = None  # Lưu trữ thông tin boss raid đang diễn ra

class RaidJoinView(discord.ui.View):
    def __init__(self, raid_data):
        super().__init__(timeout=120)  # Tự động đóng / xuất trận sau 2 phút
        self.raid_data = raid_data

    @discord.ui.button(label="⚔️ Tham Gia / Join Raid (Miễn phí)", style=discord.ButtonStyle.danger, emoji="💥")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global boss_cooldown_until
        user_id = interaction.user.id
        if user_id in self.raid_data["participants"]:
            await interaction.response.send_message("Bạn đã tham gia hàng ngũ diệt boss rồi!", ephemeral=True)
            return

        if len(self.raid_data["participants"]) >= BOSS_CONFIG["max_players"]:
            await interaction.response.send_message(f"Đội hình đã đầy ({BOSS_CONFIG['max_players']} người)!", ephemeral=True)
            return

        player = get_player(user_id, interaction.user.display_name)
        has_any_card = len(player.get("team", [])) > 0 or any(cnt > 0 for cnt in player.get("inventory", {}).values())
        if not has_any_card:
            await interaction.response.send_message("⚠️ Bạn chưa sở hữu thẻ bài nào! Hãy gõ `/pull` để nhận thẻ Touhou trước nhé!", ephemeral=True)
            return

        # Đảm bảo đội hình có đủ tối đa 3 lá bài mạnh nhất
        current_team = [cid for cid in player.get("team", []) if cid in CARDS_DATA]
        if len(current_team) < 3:
            owned_ids = [int(cid) for cid, cnt in player.get("inventory", {}).items() if cnt > 0 and int(cid) in CARDS_DATA]
            owned_ids.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
            for cid in owned_ids:
                if cid not in current_team:
                    current_team.append(cid)
                if len(current_team) >= 3:
                    break
            player["team"] = current_team
            save_player(player)

        self.raid_data["participants"].append(user_id)
        self.raid_data["names"].append(interaction.user.display_name)
        count = len(self.raid_data["participants"])

        # CẬP NHẬT: KHI CÓ BẤT KỲ AI THAM GIA RAID, KÍCH HOẠT COOLDOWN 15 PHÚT CHO LƯỢT SPAWN TIẾP THEO
        boss_cooldown_until = time.time() + BOSS_CONFIG["cooldown_seconds"]

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

    async def on_timeout(self):
        global active_raid
        for child in self.children:
            child.disabled = True

        if self.raid_data.get("msg"):
            try:
                await self.raid_data["msg"].edit(view=self)
            except Exception:
                pass

        if active_raid is self.raid_data:
            participants = self.raid_data.get("participants", [])
            channel_id = self.raid_data.get("channel_id")
            channel = bot.get_channel(channel_id)
            if participants and channel:
                await channel.send(f"⏰ **Đã hết 2 phút chuẩn bị!** Toàn bộ {len(participants)} dũng giả cùng toàn thể đạo quân thẻ bài đồng loạt xông lên khai chiến quyết tử với Reimu Dị Hình!")
                await execute_raid(channel, self.raid_data)
            elif channel:
                active_raid = None
                await channel.send("⌛ **Đã hết 2 phút!** Không có dũng giả nào dám bước tới nghênh chiến. Reimu Dị Hình cười khẩy rồi xé rách không gian trốn thoát...")

async def execute_raid(channel, raid_data):
    global active_raid, boss_cooldown_until
    active_raid = None  # Giải phóng cờ active

    participants = raid_data["participants"]
    if not participants:
        await channel.send("⛩️ Reimu Dị Hình đã biến mất vào hư không vì không ai dám đối đầu...")
        return

    # KÍCH HOẠT HOẶC DUY TRÌ COOLDOWN 15 PHÚT SAU KHI TRẬN CHIẾN KẾT THÚC
    boss_cooldown_until = max(boss_cooldown_until, time.time() + BOSS_CONFIG["cooldown_seconds"])

    # Chuẩn bị đội hình chiến đấu cho từng dũng giả
    combatants = []
    for uid in participants:
        p = get_player(uid)
        lvl_buff = (p["level"] - 1) * 10

        team_cids = [cid for cid in p.get("team", []) if cid in CARDS_DATA]

        if len(team_cids) < 3:
            owned_ids = [int(cid) for cid, cnt in p.get("inventory", {}).items() if cnt > 0 and int(cid) in CARDS_DATA]
            owned_ids.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
            for cid in owned_ids:
                if cid not in team_cids:
                    team_cids.append(cid)
                if len(team_cids) >= 3:
                    break
            p["team"] = team_cids
            save_player(p)

        team_pwr = 0
        team_hp = 0
        card_names = []
        for cid in team_cids[:3]:
            card = CARDS_DATA.get(cid)
            if card:
                team_pwr += card["power"] + lvl_buff
                team_hp += card["hp"] + lvl_buff
                card_names.append(f"{card['name']} (⚔️{card['power'] + lvl_buff:,}/❤️{card['hp'] + lvl_buff:,})")

        combatants.append({
            "uid": uid,
            "username": p["username"],
            "level": p["level"],
            "power": team_pwr,
            "max_hp": team_hp,
            "current_hp": team_hp,
            "is_alive": True,
            "total_dmg": 0,
            "cards": card_names,
            "death_round": None
        })

    # GIAI ĐOẠN 1 (PHASE 1): 35,000 HP, 15,000 POWER
    p1_max_hp = BOSS_CONFIG["hp"]
    p1_hp = p1_max_hp
    p1_power = BOSS_CONFIG["power"]

    p1_rounds = 0
    max_rounds = 35
    p1_battle_history = []

    while p1_hp > 0 and p1_rounds < max_rounds:
        alive_players = [c for c in combatants if c["is_alive"]]
        if not alive_players:
            break

        p1_rounds += 1

        # 1. Các dũng giả còn sống tấn công Boss Phase 1
        round_player_dmg = sum(c["power"] for c in alive_players)
        p1_hp = max(0, p1_hp - round_player_dmg)
        for c in alive_players:
            c["total_dmg"] += c["power"]

        if p1_hp <= 0:
            p1_battle_history.append(
                f"**⚔️ Hiệp {p1_rounds} (Phase 1):** {len(alive_players)} dũng giả đồng loạt tung đòn tất sát gây **{round_player_dmg:,} DMG**! 💥 **Reimu Dị Hình Phase 1 đã bị đánh gục!**"
            )
            break

        # 2. Boss Phase 1 phản đòn (15,000 DMG chia đều cho người sống)
        dmg_per_player = max(400, p1_power // len(alive_players))
        fallen_names = []

        for c in alive_players:
            c["current_hp"] -= dmg_per_player
            if c["current_hp"] <= 0:
                c["current_hp"] = 0
                c["is_alive"] = False
                c["death_round"] = p1_rounds
                fallen_names.append(c["username"])

        log_msg = (
            f"**⚔️ Hiệp {p1_rounds}:** Dũng giả gây **{round_player_dmg:,} DMG** (Boss còn **{p1_hp:,}/{p1_max_hp:,} HP**). "
            f"Boss giáng **{dmg_per_player:,} DMG** lên mỗi dũng giả!"
        )
        if fallen_names:
            log_msg += f" 💀 *Tử trận: {', '.join(fallen_names)}*"
        p1_battle_history.append(log_msg)

    p1_defeated = (p1_hp <= 0)

    # TRƯỜNG HỢP 1: THẤT THỦ NGAY TẠI PHASE 1
    if not p1_defeated:
        embed_fail = discord.Embed(
            title="❌ QUÂN ĐOÀN THẤT THỦ TẠI PHASE 1!",
            description=(
                f"Toàn bộ dũng giả đã tử trận trước Reimu Dị Hình (35k HP / 15k DMG) sau {p1_rounds} hiệp!\n"
                f"Boss Phase 1 còn sót lại **{p1_hp:,} HP** và đã xé rách không gian trốn thoát.\n"
                f"⏳ Hồi chiêu **15 phút** đã bắt đầu kích hoạt!"
            ),
            color=0xEF4444
        )
        embed_fail.set_thumbnail(url=BOSS_CONFIG["image"])
        if len(p1_battle_history) > 6:
            disp = p1_battle_history[:3] + [f"*... (giằng co ác liệt {len(p1_battle_history)-5} hiệp) ...*"] + p1_battle_history[-2:]
        else:
            disp = p1_battle_history
        embed_fail.add_field(name="📜 Diễn Biến Phase 1:", value="\n".join(disp), inline=False)
        await channel.send(embed=embed_fail)
        return

    # PHASE 1 CHIẾN THẮNG: TRAO QUÀ PHASE 1 (3 QUÀ: 40% RA 0.5 VÉ, 60% RA 0.33 VÉ)
    p1_rewards_data = {}
    for uid in participants:
        p = get_player(uid)
        p1_total = 0.0
        p1_items = []
        for g_idx in range(1, 4):
            roll = random.random()
            if roll < 0.40:
                ticket_val = 0.5
                desc_str = "+0.5 Vé Pull (40%)"
            else:
                ticket_val = 1.0 / 3.0
                desc_str = "+0.33 Vé Pull (60%)"
            p1_total += ticket_val
            p1_items.append(f"Quà {g_idx}: {desc_str}")
        p["pull_tickets"] += p1_total
        p["xp"] += 100
        save_player(p)
        p1_rewards_data[uid] = {
            "total_pulls": p1_total,
            "items": p1_items,
            "username": p["username"]
        }

    # GỬI THÔNG BÁO CHUYỂN PHASE 2:
    # "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động giữ dội"
    phase2_alert_embed = discord.Embed(
        title="🚨 DỊ BIẾN BIẾN ĐỔI - BÙA CHÚ RUNG ĐỘNG DỮ DỘI! (PHASE 2 BẮT ĐẦU)",
        description=(
            "⚡ **Dị hình đang biến đổi, bùa chú của chúng ta đang rung động giữ dội!**\n\n"
            f"👺 **{BOSS_PHASE2_CONFIG['name']}** đã thức tỉnh với ma lực kinh hoàng!\n"
            f"❤️ **Máu tăng lên:** **`50,000 HP`**\n"
            f"⚔️ **Power tăng lên:** **`22,000 DMG`** *(chia đều cho dũng giả còn sống)*\n\n"
            f"✨ **PHÉP MÀU BÙA CHÚ THANH TẨY:**\n"
            f"**Lập tức hồi sinh và hồi phục 100% sinh lực toàn bộ lá bài tham chiến của tất cả người chơi tham gia raid!**"
        ),
        color=0x9333EA
    )
    phase2_alert_embed.set_image(url=BOSS_PHASE2_CONFIG["image"])
    await channel.send(embed=phase2_alert_embed)

    # LẬP TỨC HỒI PHỤC TOÀN BỘ LÁ BÀI THAM CHIẾN CỦA NGƯỜI THAM GIA RAID (100% HP & HỒI SINH)
    for c in combatants:
        c["current_hp"] = c["max_hp"]
        c["is_alive"] = True
        c["death_round"] = None

    # GIAI ĐOẠN 2 (PHASE 2): 50,000 HP, 22,000 POWER
    p2_max_hp = BOSS_PHASE2_CONFIG["hp"]
    p2_hp = p2_max_hp
    p2_power = BOSS_PHASE2_CONFIG["power"]
    p2_rounds = 0
    p2_battle_history = []

    while p2_hp > 0 and p2_rounds < max_rounds:
        alive_players = [c for c in combatants if c["is_alive"]]
        if not alive_players:
            break

        p2_rounds += 1

        # 1. Dũng giả tấn công Boss Phase 2
        round_player_dmg = sum(c["power"] for c in alive_players)
        p2_hp = max(0, p2_hp - round_player_dmg)
        for c in alive_players:
            c["total_dmg"] += c["power"]

        if p2_hp <= 0:
            p2_battle_history.append(
                f"**⚡ Hiệp {p2_rounds} (Phase 2):** {len(alive_players)} dũng giả đồng lòng tung chiêu thức tối thượng gây **{round_player_dmg:,} DMG**! 💥 **Reimu Dị Hình Phase 2 đã bị tiêu diệt hoàn toàn!**"
            )
            break

        # 2. Boss Phase 2 phản đòn (22,000 DMG chia đều cho người sống)
        dmg_per_player = max(600, p2_power // len(alive_players))
        fallen_names = []

        for c in alive_players:
            c["current_hp"] -= dmg_per_player
            if c["current_hp"] <= 0:
                c["current_hp"] = 0
                c["is_alive"] = False
                c["death_round"] = p2_rounds
                fallen_names.append(c["username"])

        log_msg = (
            f"**⚡ Hiệp {p2_rounds} (Phase 2):** Dũng giả gây **{round_player_dmg:,} DMG** (Boss Phase 2 còn **{p2_hp:,}/{p2_max_hp:,} HP**). "
            f"Boss giáng đòn 22,000 DMG gây **{dmg_per_player:,} DMG** lên mỗi dũng giả!"
        )
        if fallen_names:
            log_msg += f" 💀 *Tử trận: {', '.join(fallen_names)}*"
        p2_battle_history.append(log_msg)

    p2_defeated = (p2_hp <= 0)
    total_raid_dmg = sum(c["total_dmg"] for c in combatants)

    # TRAO THƯỞNG PHASE 2 NẾU HẠ GỤC PHASE 2:
    # 20% ra 10 pull, 40% ra 5 pull, 60% ra 3 pull (tổng cộng 3 quà tặng ngẫu nhiên)
    p2_rewards_data = {}
    if p2_defeated:
        for uid in participants:
            p = get_player(uid)
            old_lvl = p["level"]
            p2_total = 0.0
            p2_items = []
            for g_idx in range(1, 4):
                roll = random.random()
                if roll < 0.20:
                    ticket_val = 10.0
                    desc_str = "🔥 **+10 Vé Pull** (20%)"
                elif roll < 0.60:
                    ticket_val = 5.0
                    desc_str = "💎 **+5 Vé Pull** (40%)"
                else:
                    ticket_val = 3.0
                    desc_str = "✨ **+3 Vé Pull** (60%)"
                p2_total += ticket_val
                p2_items.append(f"Quà {g_idx}: {desc_str}")
            p["pull_tickets"] += p2_total
            p["xp"] += 150  # Thưởng thêm 150 XP cho Phase 2 (Tổng 250 XP cả 2 phase)
            save_player(p)
            p2_rewards_data[uid] = {
                "total_pulls": p2_total,
                "items": p2_items,
                "username": p["username"],
                "new_level": p["level"],
                "old_level": old_lvl,
                "total_tickets": p["pull_tickets"]
            }

    # TỔNG KẾT TRẬN ĐẤU VÀ PHẦN THƯỞNG
    embed = discord.Embed(
        title="⚔️ KẾT QUẢ ĐẠI CHIẾN QUYẾT TỬ: REIMU DỊ HÌNH (FULL 2 PHASES)!",
        description=(
            f"**Phase 1:** 🎉 Hạ gục sau **{p1_rounds} hiệp**\n"
            f"**Phase 2:** {'🎉 TOÀN THẮNG HUY HOÀNG (Boss 0 HP)' if p2_defeated else f'❌ THẤT THỦ (Boss còn {p2_hp:,}/{p2_max_hp:,} HP)'} sau **{p2_rounds} hiệp**\n"
            f"**Tổng Sát Thương Cả 2 Phase:** **{total_raid_dmg:,} DMG**\n"
            f"⏳ **Hồi chiêu Boss tiếp theo:** **15 phút**"
        ),
        color=0x10B981 if p2_defeated else 0xF59E0B
    )
    embed.set_thumbnail(url=BOSS_PHASE2_CONFIG["image"] if p2_defeated else BOSS_CONFIG["image"])

    # Diễn biến
    if len(p2_battle_history) > 5:
        disp_p2 = p2_battle_history[:2] + [f"*... (giằng co Phase 2 {len(p2_battle_history)-3} hiệp) ...*"] + p2_battle_history[-2:]
    else:
        disp_p2 = p2_battle_history
    embed.add_field(name="⚡ Diễn Biến Kịch Chiến Phase 2:", value="\n".join(disp_p2) if disp_p2 else "Phase 2 kết thúc chớp nhoáng!", inline=False)

    # Báo cáo tình trạng
    player_reports = []
    for c in combatants:
        card_desc = ", ".join(c["cards"]) if c["cards"] else "Không có thẻ"
        if c["is_alive"]:
            status_str = f"✅ Sống sót (**{c['current_hp']:,}/{c['max_hp']:,} HP**)"
        else:
            status_str = f"💀 Tử trận Phase 2 ở hiệp {c['death_round']} (0/{c['max_hp']:,} HP)"
        player_reports.append(
            f"• **{c['username']}** (Lv.{c['level']}): Gây **{c['total_dmg']:,} DMG** | {status_str}"
        )
    embed.add_field(name="📋 Tình Trạng Dũng Giả:", value="\n".join(player_reports), inline=False)

    # Tổng kết quà tặng Phase 1
    p1_summary_lines = []
    for uid, r in p1_rewards_data.items():
        p1_summary_lines.append(f"🎁 **{r['username']}**: +{r['total_pulls']:.2f} Vé Pull ({', '.join(r['items'])}) + 100 XP")
    embed.add_field(name="📦 Phần Thưởng Phase 1 (40% ra 0.5 vé, 60% ra 0.33 vé):", value="\n".join(p1_summary_lines), inline=False)

    # Tổng kết quà tặng Phase 2
    if p2_defeated:
        p2_summary_lines = []
        for uid, r in p2_rewards_data.items():
            lvl_up = f" 🌟 **LÊN CẤP {r['new_level']}!**" if r['new_level'] > r['old_level'] else ""
            p2_summary_lines.append(
                f"🏆 **{r['username']}**: Nhận **+{r['total_pulls']:.0f} Vé Pull** ({', '.join(r['items'])}) + 150 XP!{lvl_up}\n"
                f"   └ *Tổng vé tích lũy hiện có: {r['total_tickets']:.2f} vé*"
            )
        embed.add_field(
            name="💎 Phần Thưởng Siêu Cấp Phase 2 (20% ra 10 vé, 40% ra 5 vé, 60% ra 3 vé):",
            value="\n".join(p2_summary_lines),
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ Kết Quả Phase 2:",
            value=(
                f"Quân đoàn chưa hạ gục được Reimu Dị Hình Phase 2 (còn sót lại {p2_hp:,} HP)!\n"
                f"Tất cả người chơi vẫn **bảo lưu toàn bộ quà tặng Phase 1** đã nhận được ở trên."
            ),
            inline=False
        )

    await channel.send(embed=embed)

# ==============================================================================
# 7. SỰ KIỆN BOT ON_READY & ON_MESSAGE (CHAT VỚI REIMU + RANDOM BOSS 10% + COOLDOWN 15P)
# ==============================================================================
@bot.event
async def on_ready():
    print(f"Bot Hakurei Reimu đã khởi động thành công: {bot.user.name}", flush=True)
    if use_mongo:
        print("🌟 [DATABASE STATUS] Đang kết nối MONGODB ATLAS CLOUD (Dữ liệu an toàn vĩnh viễn)!", flush=True)
    else:
        print("⚠️ [DATABASE CẢNH BÁO] Đang chạy trên SQLITE TẠM THỜI!", flush=True)
        print(f"   Chi tiết lỗi: {mongo_error_detail}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} Slash Commands (bao gồm các lệnh Admin mới)!", flush=True)
    except Exception as e:
        print(f"Lỗi đồng bộ slash command: {e}", flush=True)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Đền Hakurei | /help | /pull | /battle | Boss 35k HP"
        )
    )

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.author == bot.user:
        return

    content_lower = message.content.lower()

    # CẬP NHẬT: RANDOM 10% XUẤT HIỆN BOSS VÀ KIỂM TRA COOLDOWN 15 PHÚT
    global active_raid, boss_cooldown_until
    now_ts = time.time()
    
    # Chỉ xét spawn khi:
    # 1. Không có boss nào đang active
    # 2. Đã HẾT thời gian hồi chiêu 15 phút (boss_cooldown_until <= now)
    # 3. Không phải tin nhắn lệnh (! hoặc /)
    if active_raid is None and now_ts >= boss_cooldown_until and not content_lower.startswith("!") and not content_lower.startswith("/"):
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
            embed.add_field(name="❤️ Máu Boss (HP):", value=f"{BOSS_CONFIG['hp']:,} HP *(Tăng cường 35k HP)*", inline=True)
            embed.add_field(name="⚔️ Sát Thương (Power):", value=f"{BOSS_CONFIG['power']:,} DMG *(15k DMG chia đều)*", inline=True)
            embed.add_field(name=f"👥 Người Tham Gia (0/{BOSS_CONFIG['max_players']}):", value="Chưa có ai", inline=False)
            embed.add_field(
                name="🎁 Cơ Chế 2 Phase & Phần Thưởng Đột Phá:",
                value=(
                    "• **Phase 1 (3 Quà):** 40% ra **0.5 Vé**, 60% ra **0.33 Vé** (1/3 vé)!\n"
                    "• **Chuyển Phase 2 (50k HP / 22k DMG):** Hồi sinh & phục hồi **100% HP toàn bộ lá bài** tham chiến!\n"
                    "• **Phase 2 (3 Quà Siêu Cấp):** 20% ra **10 Vé Pull**, 40% ra **5 Vé Pull**, 60% ra **3 Vé Pull**!\n"
                    "*Tất cả phần thưởng được quy đổi tự động thành vé gacha tích lũy!*"
                ),
                inline=False
            )
            embed.add_field(
                name="⏱️ Quy Tắc & Hồi Chiêu (15 Phút):",
                value=(
                    "⏳ **Thời gian chuẩn bị:** 2 phút (120s) trước khi xuất trận!\n"
                    "🛡️ **Hồi chiêu Spawn:** Khi có bất kỳ ai tham gia, lượt spawn tiếp theo sẽ cần chờ **15 phút**!"
                ),
                inline=False
            )
            embed.set_footer(text="Bấm 'Tham Gia' để xuất trận • Miễn phí • Hồi chiêu 15 phút sau raid")
            
            view = RaidJoinView(active_raid)
            msg = await message.channel.send(embed=embed, view=view)
            active_raid["msg"] = msg

    # XỬ LÝ TRÒ CHUYỆN VỚI REIMU
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
                err_str = str(e)
                print(f"Lỗi AI Chat: {e}", flush=True)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    await message.reply("⛩️ Hừ, linh lực Gemini của đền Hakurei tạm thời bị quá tải! Hãy đợi khoảng 15-30 giây rồi trò chuyện tiếp với ta nhé!", mention_author=False)
                else:
                    await message.reply("⛩️ Hừ, bùa chú đền Hakurei tạm thời bị nhiễu loạn linh lực! Đợi vài giây rồi gọi lại ta!", mention_author=False)

    await bot.process_commands(message)

# ==============================================================================
# 8. CƠ CHẾ GACHA PULL TOUHOU
# ==============================================================================
def execute_single_pull(player):
    roll = random.random()
    if roll < 0.0001:  # 0.01% Hạng SS
        chosen = random.choice(CARDS_BY_RANK["SS"])
    elif roll < 0.1001:  # 10.0% Hạng S (Nerf tỷ lệ pull ra S xuống đúng 10%)
        chosen = random.choice(CARDS_BY_RANK["S"])
    elif roll < 0.3501:  # 25.0% Hạng A
        chosen = random.choice(CARDS_BY_RANK["A"])
    elif roll < 0.6501:  # 30.0% Hạng B
        chosen = random.choice(CARDS_BY_RANK["B"])
    else:  # 34.99% Hạng C
        chosen = random.choice(CARDS_BY_RANK["C"])

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
            converted_pulls = 1.0 / 3.0
        elif chosen["rank"] == "C":
            converted_pulls = 0.2

        player["pull_tickets"] += converted_pulls

    return chosen, is_duplicate, converted_pulls

# ==============================================================================
# 9. LỆNH ADMIN MỚI: SET LEVEL VÀ TƯỚC ĐOẠT BÀI (TRỪNG PHẠT CHEAT)
# ==============================================================================

# --- LỆNH ADMIN: SET LEVEL USER (ĐỒNG BỘ XP VÀ LEVEL CHUẨN XÁC KHÔNG BUG) ---
@bot.tree.command(name="admin_set_level", description="[CHỦ BOT DUY NHẤT] Đặt cấp độ cho người chơi (đồng bộ XP chính xác không bug)")
@app_commands.describe(
    nguoi_dung="Chọn người chơi cần đặt cấp độ",
    cap_do="Cấp độ mới từ 1 đến 100"
)
async def slash_admin_set_level(interaction: discord.Interaction, nguoi_dung: discord.Member, cap_do: int):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message(
            f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**\nChỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới có quyền sử dụng lệnh này.",
            ephemeral=True
        )
        return

    if cap_do < 1: cap_do = 1
    if cap_do > MAX_LEVEL: cap_do = MAX_LEVEL

    target_player = get_player(nguoi_dung.id, nguoi_dung.display_name)
    old_lvl = target_player["level"]
    old_xp = target_player["xp"]

    # Đặt lại XP chính xác bằng mốc XP yêu cầu của cấp độ đó
    new_xp = get_total_xp_for_level(cap_do)
    target_player["xp"] = new_xp
    target_player["level"] = cap_do
    save_player(target_player)

    next_req = get_xp_needed_for_level(cap_do)
    embed = discord.Embed(
        title="⚙️ [ADMIN] ĐÃ THAY ĐỔI CẤP ĐỘ NGƯỜI CHƠI THÀNH CÔNG",
        description=(
            f"👑 **Quản trị viên tối cao:** {interaction.user.mention}\n"
            f"👤 **Mục tiêu:** {nguoi_dung.mention} (`{nguoi_dung.display_name}`)\n"
            f"📊 **Thay đổi cấp độ:** `Lv.{old_lvl}` ➔ **`Lv.{cap_do}`**\n"
            f"📈 **Đồng bộ XP:** `{old_xp:,} XP` ➔ **`{new_xp:,} XP`**\n"
            f"⭐ **Cần để lên Lv.{min(MAX_LEVEL, cap_do + 1)}:** `{next_req:,} XP`"
        ),
        color=0x10B981
    )
    embed.set_footer(text="Hakurei Shrine Admin Security System • Exclusive Owner Access")
    await interaction.response.send_message(embed=embed)

@bot.command(name="setlevel", aliases=["setlvl", "adminsetlevel"])
async def prefix_admin_set_level(ctx, member: discord.Member, level: int):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send(f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới có quyền sử dụng lệnh này.")
        return

    if level < 1: level = 1
    if level > MAX_LEVEL: level = MAX_LEVEL

    target_player = get_player(member.id, member.display_name)
    old_lvl = target_player["level"]
    old_xp = target_player["xp"]

    new_xp = get_total_xp_for_level(level)
    target_player["xp"] = new_xp
    target_player["level"] = level
    save_player(target_player)

    next_req = get_xp_needed_for_level(level)
    embed = discord.Embed(
        title="⚙️ [ADMIN] ĐÃ THAY ĐỔI CẤP ĐỘ THÀNH CÔNG",
        description=(
            f"👑 **Admin:** {ctx.author.mention}\n"
            f"👤 **Người chơi:** {member.mention}\n"
            f"📊 **Cấp độ:** `Lv.{old_lvl}` ➔ **`Lv.{level}`**\n"
            f"📈 **Đồng bộ XP:** `{old_xp:,} XP` ➔ **`{new_xp:,} XP`**\n"
            f"⭐ **Cần để lên cấp tiếp theo:** `{next_req:,} XP`"
        ),
        color=0x10B981
    )
    await ctx.send(embed=embed)


# --- LỆNH ADMIN: TƯỚC ĐOẠT BÀI (TRỪNG PHẠT CHEAT / GIAN LẬN) ---
@bot.tree.command(name="admin_confiscate", description="[CHỦ BOT DUY NHẤT] Tước đoạt thẻ bài của người chơi (trừng phạt cheat/gian lận)")
@app_commands.describe(
    nguoi_dung="Người chơi bị trừng phạt",
    id_the="Số ID thẻ từ 1 đến 26, hoặc nhập 0 để tịch thu TOÀN BỘ bài",
    so_luong="Số lượng thẻ muốn tịch thu (mặc định tịch thu hết số lượng thẻ đó)"
)
async def slash_admin_confiscate(interaction: discord.Interaction, nguoi_dung: discord.Member, id_the: int = 0, so_luong: int = 0):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message(
            f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**\nChỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới có quyền sử dụng lệnh này.",
            ephemeral=True
        )
        return

    target_player = get_player(nguoi_dung.id, nguoi_dung.display_name)
    inv = target_player.get("inventory", {})
    team = target_player.get("team", [])

    if id_the == 0:
        # Tịch thu toàn bộ bài trong kho đồ và xóa sạch đội hình
        total_cards_confiscated = sum(inv.values())
        target_player["inventory"] = {}
        target_player["team"] = []
        save_player(target_player)

        embed = discord.Embed(
            title="⚖️ [TRỪNG PHẠT CHEAT] ĐÃ TỊCH THU TOÀN BỘ THẺ BÀI!",
            description=(
                f"🚨 **Án phạt ban hành bởi Quản trị viên:** {interaction.user.mention}\n"
                f"👤 **Đối tượng xử phạt:** {nguoi_dung.mention} (`{nguoi_dung.display_name}`)\n"
                f"🚫 **Hành vi:** Vi phạm quy chế / nghi vấn cheat bẩn Gensokyo\n"
                f"📦 **Hình phạt:** Tước đoạt toàn bộ **{total_cards_confiscated} lá bài** trong kho đồ và giải tán đội hình chiến đấu!"
            ),
            color=0xDC2626
        )
        embed.set_footer(text="Luật pháp Đền Hakurei • Không khoan nhượng với hành vi cheat!")
        await interaction.response.send_message(embed=embed)
        return

    if id_the not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ! ID thẻ nằm trong khoảng từ 1 đến {len(CARDS_DATA)}.", ephemeral=True)
        return

    card = CARDS_DATA[id_the]
    cid_str = str(id_the)
    owned = inv.get(cid_str, 0)
    if owned <= 0:
        await interaction.response.send_message(f"⚠️ Người chơi {nguoi_dung.display_name} hiện không sở hữu thẻ #{id_the:02d} {card['name']}!", ephemeral=True)
        return

    # Tịch thu số lượng cụ thể hoặc hết
    to_remove = owned if (so_luong <= 0 or so_luong >= owned) else so_luong
    inv[cid_str] = owned - to_remove
    if inv[cid_str] <= 0:
        del inv[cid_str]
        # Nếu thẻ đang có trong team thì xóa khỏi team
        if id_the in team:
            team.remove(id_the)

    target_player["inventory"] = inv
    target_player["team"] = team
    save_player(target_player)

    embed = discord.Embed(
        title="⚖️ [TRỪNG PHẠT CHEAT] ĐÃ TƯỚC ĐOẠT THẺ BÀI!",
        description=(
            f"🚨 **Quản trị viên:** {interaction.user.mention}\n"
            f"👤 **Đối tượng bị tước bài:** {nguoi_dung.mention}\n"
            f"🎴 **Thẻ bị tước đoạt:** `[{card['rank']}]` **#{card['id']:02d} {card['name']}**\n"
            f"🔢 **Số lượng tước:** `{to_remove}` lá (Còn lại: `{inv.get(cid_str, 0)}` lá)\n"
            f"🛡️ **Đội hình hiện tại:** {len(team)}/3 thẻ"
        ),
        color=0xDC2626
    )
    embed.set_thumbnail(url=card["image"])
    embed.set_footer(text="Hakurei Shrine Disciplinary Action")
    await interaction.response.send_message(embed=embed)

@bot.command(name="confiscate", aliases=["tuocdoat", "adminconfiscate"])
async def prefix_admin_confiscate(ctx, member: discord.Member, card_id: int = 0, quantity: int = 0):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send(f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới có quyền sử dụng lệnh này.")
        return

    target_player = get_player(member.id, member.display_name)
    inv = target_player.get("inventory", {})
    team = target_player.get("team", [])

    if card_id == 0:
        total = sum(inv.values())
        target_player["inventory"] = {}
        target_player["team"] = []
        save_player(target_player)
        await ctx.send(f"🚨 Đã tước đoạt **toàn bộ {total} thẻ bài** của {member.mention} và xóa sạch đội hình do vi phạm!")
        return

    if card_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-{len(CARDS_DATA)})!")
        return

    card = CARDS_DATA[card_id]
    cid_str = str(card_id)
    owned = inv.get(cid_str, 0)
    if owned <= 0:
        await ctx.send(f"⚠️ {member.display_name} không sở hữu thẻ này!")
        return

    to_remove = owned if (quantity <= 0 or quantity >= owned) else quantity
    inv[cid_str] = owned - to_remove
    if inv[cid_str] <= 0:
        del inv[cid_str]
        if card_id in team:
            team.remove(card_id)

    target_player["inventory"] = inv
    target_player["team"] = team
    save_player(target_player)

    await ctx.send(f"⚖️ Đã tịch thu **{to_remove}x [{card['rank']}] {card['name']}** của {member.mention}!")


# --- LỆNH ADMIN: LẤY / CẤP THẺ NHÂN VẬT (CHỦ BOT ĐỘC QUYỀN) ---
@bot.tree.command(name="admin_add_card", description="[CHỦ BOT DUY NHẤT] Lấy/cấp thẻ nhân vật Touhou vào kho đồ người chơi")
@app_commands.describe(
    id_the="Số ID thẻ từ 1 đến 26 (ví dụ: 8 là Yuyuko Saigyouji)",
    so_luong="Số lượng thẻ muốn lấy/cấp (mặc định: 1)",
    nguoi_dung="Người nhận thẻ (để trống nếu tự cấp cho chính bản thân chủ bot)"
)
async def slash_admin_add_card(interaction: discord.Interaction, id_the: int, so_luong: int = 1, nguoi_dung: discord.Member = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message(
            f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**\nChỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới có quyền sử dụng lệnh này.",
            ephemeral=True
        )
        return

    if id_the not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ! Vui lòng nhập ID từ 1 đến {len(CARDS_DATA)}.", ephemeral=True)
        return

    if so_luong < 1:
        so_luong = 1

    target = nguoi_dung if nguoi_dung else interaction.user
    target_player = get_player(target.id, target.display_name)
    cid_str = str(id_the)
    card = CARDS_DATA[id_the]

    inv = target_player.setdefault("inventory", {})
    old_cnt = inv.get(cid_str, 0)
    new_cnt = old_cnt + so_luong
    inv[cid_str] = new_cnt
    save_player(target_player)

    embed = discord.Embed(
        title="🎁 [ADMIN] ĐÃ LẤY / CẤP THẺ BÀI THÀNH CÔNG!",
        description=(
            f"👑 **Quản trị viên thực hiện:** {interaction.user.mention}\n"
            f"👤 **Người nhận thẻ:** {target.mention} (`{target.display_name}`)\n"
            f"🎴 **Thẻ nhận được:** `[{card['rank']}]` **#{card['id']:02d} {card['name']}**\n"
            f"⚔️ **Chỉ số:** Power: **{card['power']:,}** | HP: **{card['hp']:,}**\n"
            f"📦 **Số lượng cấp:** `+{so_luong}` lá (Hiện có trong kho: `{new_cnt}` lá)"
        ),
        color=0x10B981
    )
    embed.set_thumbnail(url=card["image"])
    embed.set_footer(text=f"Hakurei Shrine Admin Management • Card #{card['id']:02d}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="addcard", aliases=["adminaddcard", "givecard", "thembai"])
async def prefix_admin_add_card(ctx, card_id: int, quantity: int = 1, member: discord.Member = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send(f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới có quyền sử dụng lệnh này.")
        return

    if card_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ! Vui lòng chọn ID từ 1 đến {len(CARDS_DATA)}.")
        return

    if quantity < 1:
        quantity = 1

    target = member if member else ctx.author
    target_player = get_player(target.id, target.display_name)
    cid_str = str(card_id)
    card = CARDS_DATA[card_id]

    inv = target_player.setdefault("inventory", {})
    old_cnt = inv.get(cid_str, 0)
    new_cnt = old_cnt + quantity
    inv[cid_str] = new_cnt
    save_player(target_player)

    embed = discord.Embed(
        title="🎁 [ADMIN] ĐÃ LẤY / CẤP THẺ BÀI THÀNH CÔNG!",
        description=(
            f"👑 **Quản trị viên thực hiện:** {ctx.author.mention}\n"
            f"👤 **Người nhận thẻ:** {target.mention}\n"
            f"🎴 **Thẻ nhận được:** `[{card['rank']}]` **#{card['id']:02d} {card['name']}**\n"
            f"📦 **Số lượng cấp:** `+{quantity}` lá (Hiện có trong kho: `{new_cnt}` lá)"
        ),
        color=0x10B981
    )
    embed.set_thumbnail(url=card["image"])
    embed.set_footer(text="Hakurei Shrine Admin Management")
    await ctx.send(embed=embed)

# ==============================================================================
# 10. SLASH COMMANDS & PREFIX COMMANDS (PULL, TEAM, BATTLE, DAILY, BOSS STATUS)
# ==============================================================================

# --- LỆNH /pull hoặc !pull ---
async def handle_pull(ctx_or_interaction, count: int = 1):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")

    if count < 1: count = 1
    if count > 10: count = 10

    total_available = player.get("free_pulls_remaining", 0) + int(player.get("pull_tickets", 0))

    if total_available < count:
        msg = f"❌ Bạn không đủ lượt pull! (Đang có: {player.get('free_pulls_remaining', 0)} free + {player.get('pull_tickets', 0):.1f} vé, cần: {count}).\nDùng `/daily` hoặc tham gia Boss Raid để nhận thêm vé!" if lang == "vi" else f"❌ Not enough pulls! (Available: {player.get('free_pulls_remaining', 0)} free + {player.get('pull_tickets', 0):.1f} tickets, needed: {count})."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

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


# --- LỆNH /team hoặc !team (HIỂN THỊ TIẾN TRÌNH XP CẤP ĐỘ MỚI CHUẨN XÁC) ---
def build_team_guide_embed(player, user, lang="vi", error_msg=None):
    cur_lvl, xp_in_lvl, needed_xp, ratio = get_level_progress(player.get("xp", 0))
    lvl_buff = (cur_lvl - 1) * 10
    embed = discord.Embed(
        title="🛡️ HƯỚNG DẪN CHI TIẾT: CƠ CHẾ XẾP ĐỘI HÌNH (Team <hanh_dong><thêm thẻ><id>)",
        color=0xEF4444 if error_msg else 0x3B82F6
    )
    if error_msg:
        embed.description = f"⚠️ **Chú Ý:** {error_msg}\n\nĐội hình chiến đấu của bạn gồm tối đa **3 thẻ Touhou**.\n"
    else:
        embed.description = "Đội hình chiến đấu gồm tối đa **3 thẻ Touhou**. Sức mạnh toàn đội sẽ quyết định thắng bại trong **/battle** và **Boss Raid**!\n"

    embed.add_field(
        name=f"⭐ Cấp Độ Người Chơi: Lv.{cur_lvl}",
        value=f"• Tiến trình cấp: **{xp_in_lvl}/{needed_xp} XP** (Cần thêm {needed_xp - xp_in_lvl} XP để lên Lv.{cur_lvl + 1})\n• Buff chỉ số cho mỗi thẻ trong đội: **+{lvl_buff:,} Power & +{lvl_buff:,} HP**",
        inline=False
    )

    team_ids = player.get("team", [])
    slots_text = []
    for i in range(3):
        if i < len(team_ids):
            cid = team_ids[i]
            c = CARDS_DATA.get(cid)
            if c:
                pwr = c["power"] + lvl_buff
                hp = c["hp"] + lvl_buff
                slots_text.append(f"• **Slot {i+1}:** `[{c['rank']}]` **#{c['id']:02d} {c['name']}** (⚔️ {pwr:,} | ❤️ {hp:,})")
            else:
                slots_text.append(f"• **Slot {i+1}:** Thẻ #{cid}")
        else:
            slots_text.append(f"• **Slot {i+1}:** 🔲 *[Trống - Chưa xếp thẻ]*")
    embed.add_field(name=f"📋 Trạng Thái Đội Hình Hiện Tại ({len(team_ids)}/3 Thẻ):", value="\n".join(slots_text), inline=False)

    inv = player.get("inventory", {})
    owned_lines = []
    for cid in range(1, len(CARDS_DATA) + 1):
        cnt = inv.get(str(cid), 0)
        if cnt > 0:
            c = CARDS_DATA[cid]
            pwr = c["power"] + lvl_buff
            hp = c["hp"] + lvl_buff
            in_team_tag = " ⭐ *(Đang ra trận)*" if cid in team_ids else ""
            owned_lines.append(f"`#{c['id']:02d}` `[{c['rank']}]` **{c['name']}** ×{cnt} (⚔️{pwr:,} | ❤️{hp:,}){in_team_tag}")

    if owned_lines:
        display_lines = "\n".join(owned_lines[:10])
        if len(owned_lines) > 10:
            display_lines += f"\n*...và còn {len(owned_lines) - 10} thẻ khác (gõ `/collection` để xem)*"
        embed.add_field(name=f"🎒 Thẻ Bạn Đang Sở Hữu ({len(owned_lines)} loại) - Dùng ID để Add:", value=display_lines, inline=False)
    else:
        embed.add_field(name="🎒 Thẻ Bạn Đang Sở Hữu:", value="❌ Bạn chưa sở hữu thẻ nào! Hãy gõ `/pull` để quay thẻ miễn phí!", inline=False)

    syntax_guide = (
        "• Thêm thẻ vào đội: `Team <hanh_dong><thêm thẻ><id>` hoặc `/team add id_the:<ID>` (ví dụ: `/team add 8`)\n"
        "• Gỡ thẻ khỏi đội: `/team remove id_the:<ID>`\n"
        "• Xem đội hình hiện tại: `/team view`\n"
        "• Khiêu chiến kiếm XP: `/battle` (hồi chiêu 2 phút)"
    )
    embed.add_field(name="⚡ Hướng Dẫn Cú Pháp Thao Tác:", value=syntax_guide, inline=False)
    embed.set_footer(text="Gensokyo Team Builder • Hakurei Shrine")
    return embed

async def handle_team(ctx_or_interaction, action: str = "view", card_id: int = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")
    cur_lvl, xp_in_lvl, needed_xp, ratio = get_level_progress(player.get("xp", 0))
    lvl_buff = (cur_lvl - 1) * 10
    act = action.lower().strip() if action else "view"

    if act in ["guide", "help", "huongdan"]:
        guide_embed = build_team_guide_embed(player, user, lang)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=guide_embed)
        else:
            await ctx_or_interaction.send(embed=guide_embed)
        return

    if act == "add":
        if not card_id or card_id not in CARDS_DATA:
            err = f"Bạn chưa nhập số ID thẻ hợp lệ (từ 1 đến {len(CARDS_DATA)})!"
            guide_embed = build_team_guide_embed(player, user, lang, error_msg=err)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=guide_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=guide_embed)
            return

        cid_str = str(card_id)
        if player["inventory"].get(cid_str, 0) < 1:
            err = f"Bạn chưa sở hữu thẻ #{card_id:02d} {CARDS_DATA[card_id]['name']}!"
            guide_embed = build_team_guide_embed(player, user, lang, error_msg=err)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=guide_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=guide_embed)
            return

        if card_id in player["team"]:
            err = f"Thẻ #{card_id:02d} {CARDS_DATA[card_id]['name']} đã có sẵn trong đội hình rồi!"
            guide_embed = build_team_guide_embed(player, user, lang, error_msg=err)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=guide_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=guide_embed)
            return

        if len(player["team"]) >= 3:
            err = "Đội hình đã đủ tối đa 3 thẻ! Hãy gỡ bớt 1 thẻ trước khi thêm."
            guide_embed = build_team_guide_embed(player, user, lang, error_msg=err)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=guide_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=guide_embed)
            return

        player["team"].append(card_id)
        save_player(player)
        card = CARDS_DATA[card_id]
        tot_pwr = sum(CARDS_DATA[cid]["power"] + lvl_buff for cid in player["team"])
        tot_hp = sum(CARDS_DATA[cid]["hp"] + lvl_buff for cid in player["team"])

        embed_succ = discord.Embed(
            title="✅ ĐÃ THÊM THÀNH CÔNG VÀO ĐỘI HÌNH!",
            description=f"Chiến binh **[{card['rank']}] #{card['id']:02d} {card['name']}** đã gia nhập đội hình của **{user.display_name}**!",
            color=0x10B981
        )
        embed_succ.set_thumbnail(url=card["image"])

        slots_info = []
        for idx, cid in enumerate(player["team"], 1):
            c = CARDS_DATA[cid]
            slots_info.append(f"• **Slot {idx}:** `[{c['rank']}]` **#{c['id']:02d} {c['name']}** (⚔️ {c['power'] + lvl_buff:,} | ❤️ {c['hp'] + lvl_buff:,})")
        for idx in range(len(player["team"]) + 1, 4):
            slots_info.append(f"• **Slot {idx}:** 🔲 *[Trống]*")

        embed_succ.add_field(name=f"📋 Đội Hình ({len(player['team'])}/3 Thẻ):", value="\n".join(slots_info), inline=False)
        embed_succ.add_field(name="📊 Tổng Lực Chiến:", value=f"⚔️ Power: **{tot_pwr:,}** | ❤️ HP: **{tot_hp:,}**", inline=False)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed_succ)
        else:
            await ctx_or_interaction.send(embed=embed_succ)
        return

    elif act == "remove":
        if not card_id or card_id not in player["team"]:
            err = "Vui lòng nhập ID thẻ đang có trong đội hình của bạn để gỡ!"
            guide_embed = build_team_guide_embed(player, user, lang, error_msg=err)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=guide_embed, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=guide_embed)
            return

        player["team"].remove(card_id)
        save_player(player)
        card = CARDS_DATA[card_id]
        msg = f"🗑️ Đã gỡ thành công **[{card['rank']}] #{card['id']:02d} {card['name']}** khỏi đội hình! (Hiện còn {len(player['team'])}/3 thẻ)"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    # View đội hình mặc định
    filled_bars = int(ratio * 10)
    bar_str = "▰" * filled_bars + "▱" * (10 - filled_bars)

    embed = discord.Embed(
        title=f"🛡️ ĐỘI HÌNH CHIẾN ĐẤU - {user.display_name.upper()}",
        color=0x3B82F6
    )

    # Hiển thị Cấp Độ theo công thức +50 XP mỗi cấp
    embed.add_field(
        name=f"⭐ CẤP ĐỘ CHIẾN BINH: Lv.{cur_lvl}",
        value=(
            f"• **Tiến Trình Cấp:** `{bar_str}` **{xp_in_lvl}/{needed_xp} XP** *(Cần thêm {needed_xp - xp_in_lvl} XP để lên Lv.{cur_lvl + 1})*\n"
            f"• **Tổng XP Tích Lũy:** `{player['xp']:,} XP`\n"
            f"• **Buff Cấp Độ:** **+{lvl_buff:,} Power** & **+{lvl_buff:,} HP** cho toàn bộ thẻ trong đội!"
        ),
        inline=False
    )

    if not player["team"]:
        embed.add_field(
            name="📋 Trạng Thái 3 Vị Trí (0/3 Thẻ):",
            value="❌ Đội hình hiện đang trống!\n👉 Hãy dùng: `Team <hanh_dong><thêm thẻ><id>` (ví dụ: `/team add 8`) để đưa thẻ vào đội chiến đấu!",
            inline=False
        )
    else:
        tot_pwr = 0
        tot_hp = 0
        for idx in range(1, 4):
            if idx <= len(player["team"]):
                cid = player["team"][idx - 1]
                c = CARDS_DATA[cid]
                pwr = c["power"] + lvl_buff
                hp = c["hp"] + lvl_buff
                tot_pwr += pwr
                tot_hp += hp
                embed.add_field(
                    name=f"Vị trí #{idx}: [{c['rank']}] #{c['id']:02d} {c['name']}",
                    value=f"⚔️ Power: **{pwr:,}** (Gốc: {c['power']} + Buff Lv.{cur_lvl}: +{lvl_buff})\n❤️ HP: **{hp:,}** (Gốc: {c['hp']} + Buff Lv.{cur_lvl}: +{lvl_buff})",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"Vị trí #{idx}: 🔲 [Trống]",
                    value="Dùng `Team <hanh_dong><thêm thẻ><id>` để thêm thẻ.",
                    inline=False
                )

        embed.add_field(
            name="📊 TỔNG LỰC CHIẾN TOÀN ĐỘI:",
            value=f"⚔️ Tổng Power: **{tot_pwr:,}** | ❤️ Tổng HP: **{tot_hp:,}**",
            inline=False
        )
        first_card = CARDS_DATA[player["team"][0]]
        embed.set_thumbnail(url=first_card["image"])

    embed.set_footer(text=f"Hakurei Shrine • Lv.{cur_lvl} (+{lvl_buff} stats) • Thắng {player.get('battles_won', 0)} trận")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="team", description="Quản lý đội hình 3 thẻ chiến đấu (view, add, remove, guide)")
@app_commands.describe(
    hanh_dong="view (xem đội), add (thêm thẻ), remove (gỡ thẻ), guide (hướng dẫn chi tiết)",
    id_the="Số ID thẻ từ 1 đến 26 (khi dùng add hoặc remove)"
)
@app_commands.choices(hanh_dong=[
    app_commands.Choice(name="👁️ Xem đội hình hiện tại (view)", value="view"),
    app_commands.Choice(name="➕ Thêm thẻ vào đội (add)", value="add"),
    app_commands.Choice(name="➖ Gỡ thẻ khỏi đội (remove)", value="remove"),
    app_commands.Choice(name="📖 Hướng dẫn chi tiết (guide)", value="guide"),
])
async def slash_team(interaction: discord.Interaction, hanh_dong: app_commands.Choice[str] = None, id_the: int = None):
    action = hanh_dong.value if hanh_dong else "view"
    await handle_team(interaction, action, id_the)

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
    for cid in range(1, len(CARDS_DATA) + 1):
        card = CARDS_DATA[cid]
        count = player["inventory"].get(str(cid), 0)
        if count > 0:
            owned_count += 1
            lines.append(f"✅ **#{card['id']:02d} [{card['rank']}] {card['name']}** ×{count}")
        else:
            lines.append(f"🔒 **#{card['id']:02d} [{card['rank']}] {card['name']}** *(Chưa có)*")

    embed = discord.Embed(
        title=f"📖 BỘ SƯU TẬP THẺ TOUHOU ({owned_count}/{len(CARDS_DATA)})" if lang == "vi" else f"📖 TOUHOU CARD COLLECTION ({owned_count}/{len(CARDS_DATA)})",
        description="\n".join(lines),
        color=0x8B5CF6
    )
    embed.set_footer(text="Quay thêm thẻ bằng lệnh: /pull")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="collection", description="Kiểm tra bộ sưu tập 26 nhân vật Touhou đã sở hữu")
async def slash_collection(interaction: discord.Interaction):
    await handle_collection(interaction)

@bot.command(name="collection")
async def prefix_collection(ctx):
    await handle_collection(ctx)


# DANH SÁCH NPC GENSOKYO CHO BATTLE
GENSOKYO_NPCS = [
    {"name": "Cirno Đệ Nhất", "title": "Băng Tinh Tự Xưng Vô Địch Gensokyo", "badge": "❄️ Băng Tinh", "preferred": [18, 19, 20]},
    {"name": "Marisa Đạo Tặc", "title": "Phù Thủy Ánh Sáng Rừng Ma Thuật", "badge": "⭐ Tinh Linh", "preferred": [6, 13, 17]},
    {"name": "Alice Ma Đạo", "title": "Nghệ Nhân Điều Khiển Búp Bê Thượng Hải", "badge": "🪆 Búp Bê", "preferred": [12, 15, 21]},
    {"name": "Aya Phóng Viên", "title": "Ký Giả Tốc Độ Bão Cuộn Bunbunmaru", "badge": "🌪️ Phong Thần", "preferred": [13, 14, 16]},
    {"name": "Youmu Kiếm Hồn", "title": "Hộ Vệ Nửa Người Nửa Ma Bạch Ngọc Lâu", "badge": "⚔️ Song Kiếm", "preferred": [8, 14, 15]},
    {"name": "Remilia Huyết Ma", "title": "Chúa Tể Huyết Nguyệt Tươi Thắm", "badge": "🦇 Huyết Tộc", "preferred": [3, 4, 10]},
    {"name": "Flandre Hủy Diệt", "title": "Cuồng Nộ Tầng Hầm Cấm Địa Laevateinn", "badge": "💎 Hủy Diệt", "preferred": [3, 5, 9]},
    {"name": "Suika Quỷ Vương", "title": "Đại Quỷ Bách Quỷ Dạ Hành Mê Tửu", "badge": "🍶 Đại Quỷ", "preferred": [5, 6, 9]},
    {"name": "Mokou Phượng Hoàng", "title": "Ngọn Lửa Bất Tử Bất Diệt Rừng Tre Lạc Lối", "badge": "🔥 Bất Tử", "preferred": [6, 10, 13]},
    {"name": "Hecatia Hỗn Mang", "title": "Nữ Thần Địa Ngục Ba Hành Tinh Thần Bí", "badge": "🌌 Hỗn Mang", "preferred": [1, 2, 4]}
]

# --- LỆNH /battle hoặc !battle (AUTO BATTLE KIẾM 50-100 XP - COOLDOWN 2 PHÚT) ---
async def handle_battle(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    lang = player.get("language", "vi")

    if not player.get("team") or len(player["team"]) == 0:
        err = "Bạn chưa thiết lập đội hình chiến đấu! Vui lòng dùng: `Team <hanh_dong><thêm thẻ><id>` (ví dụ: `/team add 8`) để xếp thẻ."
        guide_embed = build_team_guide_embed(player, user, lang, error_msg=err)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=guide_embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=guide_embed)
        return

    now = time.time()
    last_battle = player.get("last_battle_time", 0)
    cooldown = 120
    if now - last_battle < cooldown:
        remaining = int(cooldown - (now - last_battle))
        mins = remaining // 60
        secs = remaining % 60
        time_str = f"{mins} phút {secs} giây" if mins > 0 else f"{secs} giây"
        embed_cd = discord.Embed(
            title="⏳ ĐANG TRONG THỜI GIAN HỒI SỨC!",
            description=f"Chiến binh **{user.display_name}**, bạn vừa trải qua một trận chiến kịch liệt!\nVui lòng nghỉ ngơi thêm **{time_str}** nữa trước khi bước vào trận chiến tiếp theo.",
            color=0xF59E0B
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed_cd, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed_cd)
        return

    recent_opponents = player.get("recent_opponents", [])
    all_opponents = get_all_opponents(exclude_id=user.id)
    eligible_real = [
        op for op in all_opponents
        if op.get("username", "") not in recent_opponents and str(op.get("user_id")) not in recent_opponents
    ]

    choose_real = False
    if eligible_real and random.random() < 0.25:
        choose_real = True

    pl_lvl = player.get("level", 1)

    if choose_real:
        target = random.choice(eligible_real)
        opp_raw_name = target.get("username", "Dũng Giả Gensokyo")
        opp_name = f"👤 {opp_raw_name}"
        opp_level = target.get("level", 1)
        opp_title = f"Người chơi Gensokyo (Thắng {target.get('battles_won', 0)} trận)"
        opp_badge = "⚔️ [Người Chơi Thật]"
        opp_team_ids = target.get("team", [17, 18, 20])
    else:
        available_npcs = [n for n in GENSOKYO_NPCS if n["name"] not in recent_opponents]
        if not available_npcs:
            available_npcs = GENSOKYO_NPCS
        npc = random.choice(available_npcs)
        opp_raw_name = npc["name"]
        opp_name = f"{npc['badge']} {npc['name']}"
        opp_title = npc["title"]

        delta = random.choice([-1, 0, 1, 2])
        opp_badge = "⚖️ [Cân Sức]" if delta <= 0 else "🔥 [Tinh Anh]"
        opp_level = max(1, min(MAX_LEVEL, pl_lvl + delta))

        pref = npc.get("preferred", [])
        all_cids = list(CARDS_DATA.keys())
        team_set = list(pref)
        random.shuffle(all_cids)
        for cid in all_cids:
            if len(team_set) >= 3:
                break
            if cid not in team_set:
                team_set.append(cid)
        opp_team_ids = team_set[:3]

    player_buff = (player["level"] - 1) * 10
    opp_buff = (opp_level - 1) * 10

    player_pwr = sum(CARDS_DATA[cid]["power"] + player_buff for cid in player["team"])
    player_hp = sum(CARDS_DATA[cid]["hp"] + player_buff for cid in player["team"])

    opp_pwr = sum(CARDS_DATA[cid]["power"] + opp_buff for cid in opp_team_ids)
    opp_hp = sum(CARDS_DATA[cid]["hp"] + opp_buff for cid in opp_team_ids)

    player_surv_hp = player_hp - opp_pwr
    opp_surv_hp = opp_hp - player_pwr

    if opp_surv_hp <= 0 and player_surv_hp > 0:
        win = True
    elif player_surv_hp <= 0 and opp_surv_hp > 0:
        win = False
    else:
        win = (player_surv_hp / player_hp) >= (opp_surv_hp / opp_hp)

    gained_xp = random.randint(50, 100)
    old_lvl = player["level"]
    player["last_battle_time"] = now
    player["xp"] += gained_xp
    player["battles_total"] = player.get("battles_total", 0) + 1
    if win:
        player["battles_won"] = player.get("battles_won", 0) + 1

    if "recent_opponents" not in player or not isinstance(player["recent_opponents"], list):
        player["recent_opponents"] = []
    player["recent_opponents"].append(opp_raw_name)
    player["recent_opponents"] = player["recent_opponents"][-6:]
    save_player(player)

    new_lvl = player["level"]
    lvl_up_msg = f"\n🎉 **CHÚC MỪNG BẠN ĐÃ LÊN CẤP {new_lvl}!** (+10 Power & HP buff)" if new_lvl > old_lvl else ""

    result_title = f"⚔️ TRẬN CHIẾN: {user.display_name} (Lv.{player['level']}) VS {opp_name} (Lv.{opp_level})"
    embed = discord.Embed(
        title=result_title,
        color=0x10B981 if win else 0xEF4444
    )
    embed.add_field(
        name=f"🔵 {user.display_name} (Lv.{player['level']})",
        value=f"⚔️ Power: **{player_pwr:,}**\n❤️ HP: **{player_hp:,}**\n*Máu còn:* `{max(0, player_surv_hp):,}` HP",
        inline=True
    )
    embed.add_field(
        name=f"🔴 {opp_name} (Lv.{opp_level}) {opp_badge}",
        value=f"*{opp_title}*\n⚔️ Power: **{opp_pwr:,}**\n❤️ HP: **{opp_hp:,}**\n*Máu còn:* `{max(0, opp_surv_hp):,}` HP",
        inline=True
    )

    res_str = "🏆 **CHIẾN THẮNG TUYỆT ĐỐI!**" if win else "💀 **THẤT BẠI TIẾC NUỐI!**"
    cur_lvl, xp_in_lvl, needed_xp, _ = get_level_progress(player["xp"])
    embed.add_field(
        name="Kết Quả Trận Đấu:",
        value=f"{res_str}\nNhận được: **+{gained_xp} XP** (Tổng XP: {player['xp']:,} XP | Tiến trình: {xp_in_lvl}/{needed_xp} XP){lvl_up_msg}",
        inline=False
    )
    embed.set_footer(text="Hồi chiêu lệnh chiến đấu: 2 phút")

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


# --- LỆNH /boss_status hoặc !boss (KIỂM TRA THỜI GIAN HỒI CHIÊU BOSS RAID) ---
@bot.tree.command(name="boss_status", description="Kiểm tra trạng thái và thời gian hồi chiêu của Boss Raid Reimu Dị Hình")
async def slash_boss_status(interaction: discord.Interaction):
    global boss_cooldown_until, active_raid
    now = time.time()
    
    embed = discord.Embed(title="👹 TRẠNG THÁI BOSS RAID: REIMU DỊ HÌNH (2 PHASE)", color=0xDC2626)
    embed.set_thumbnail(url=BOSS_CONFIG["image"])
    embed.add_field(
        name="❤️ Chỉ Số 2 Phase:",
        value=(
            f"• **Phase 1:** HP **{BOSS_CONFIG['hp']:,}** | Power **{BOSS_CONFIG['power']:,}**\n"
            f"• **Phase 2:** HP **{BOSS_PHASE2_CONFIG['hp']:,}** | Power **{BOSS_PHASE2_CONFIG['power']:,}**"
        ),
        inline=True
    )
    embed.add_field(
        name="🎁 Phần Thưởng 2 Phase:",
        value=(
            "• **Phase 1 (3 quà):** 40% 0.5 vé, 60% 0.33 vé\n"
            "• **Phase 2 (3 quà):** 20% 10 vé, 40% 5 vé, 60% 3 vé\n"
            "*(Vào Phase 2: Hồi phục 100% HP toàn bộ bài)*"
        ),
        inline=True
    )

    if active_raid is not None:
        p_count = len(active_raid.get("participants", []))
        embed.add_field(
            name="🔥 Tình Trạng Hiện Tại:",
            value=f"**ĐANG XUẤT HIỆN!** Có {p_count}/{BOSS_CONFIG['max_players']} dũng giả đã tham chiến!",
            inline=False
        )
    elif now < boss_cooldown_until:
        rem = int(boss_cooldown_until - now)
        mins = rem // 60
        secs = rem % 60
        embed.add_field(
            name="⏳ Đang Trong Thời Gian Hồi Chiêu:",
            value=f"Boss đã kết thúc raid gần đây. Cần đợi thêm **{mins} phút {secs} giây** nữa mới có thể xuất hiện lại ngẫu nhiên (10% khi chat)!",
            inline=False
        )
    else:
        embed.add_field(
            name="🟢 Đã Sẵn Sàng Xuất Hiện:",
            value="Boss đã hết thời gian hồi chiêu 15 phút! Sẽ có **10% cơ hội xuất hiện** ngẫu nhiên khi thành viên trò chuyện trong server.",
            inline=False
        )

    embed.set_footer(text="Quy tắc: Mỗi khi có bất kỳ ai tham gia raid, boss sẽ hồi chiêu 15 phút.")
    await interaction.response.send_message(embed=embed)

@bot.command(name="boss", aliases=["bossstatus", "raidstatus"])
async def prefix_boss_status(ctx):
    global boss_cooldown_until, active_raid
    now = time.time()
    if active_raid:
        await ctx.send("🚨 Boss Raid Reimu Dị Hình ĐANG XUẤT HIỆN! Hãy tham gia ngay!")
    elif now < boss_cooldown_until:
        rem = int(boss_cooldown_until - now)
        await ctx.send(f"⏳ Boss Raid đang trong thời gian hồi chiêu 15 phút (Còn lại: {rem // 60}m {rem % 60}s).")
    else:
        await ctx.send("🟢 Boss Raid đã sẵn sàng spawn ngẫu nhiên (10% cơ hội khi chat)!")


# --- LỆNH /help hoặc !help ---
async def handle_help(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    desc = """
⛩️ **HAKUREI REIMU DISCORD BOT - BẢN ĐỒ LỆNH CẬP NHẬT**

**🎮 HỆ THỐNG GACHA & CARD BATTLE:**
• `/pull [số_lượng]`: Quay thẻ Touhou (Free 5 lượt/ngày, nerf tỷ lệ S xuống đúng 10%).
• `/daily`: Điểm danh nhận 1 vé pull mỗi ngày.
• `Team <hanh_dong><thêm thẻ><id>` hoặc `/team [hanh_dong] [id_the]`: Quản lý đội hình 3 thẻ chiến đấu (view: xem đội hình & tiến trình cấp độ, add: thêm thẻ theo ID, remove: gỡ thẻ, guide: hướng dẫn chi tiết).
• `/collection`: Xem bộ sưu tập 26 nhân vật Touhou (SS, S, A, B, C).
• `/battle`: Giao đấu tự động nhận 50-100 XP.
• `/boss_status`: Kiểm tra thời gian hồi chiêu 15 phút của Boss.

**👹 DỊ BIẾN REIMU DỊ HÌNH (RAID BOSS 2 PHASE ĐỘT PHÁ):**
• **Phase 1 (35k HP / 15k DMG):** Nhận 3 quà tặng (40% ra 0.5 vé pull, 60% ra 0.33 vé pull).
• **Phase 2 Thức Tỉnh (50k HP / 22k DMG):**
  - "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội"
  - Lập tức hồi sinh & hồi 100% sinh lực toàn bộ lá bài tham chiến của tất cả người chơi!
  - 3 quà tặng ngẫu nhiên: 20% ra 10 pull, 40% ra 5 pull, 60% ra 3 pull!
• **Hồi chiêu 15 phút:** Kích hoạt sau mỗi đợt có người tham gia raid!

**👑 LỆNH QUẢN TRỊ VIÊN (CHỈ DUY NHẤT CHỦ BOT ID: 1502579398560317441):**
• `/admin_add_card <id_the> [so_luong] [user]`: Cấp/lấy thẻ nhân vật Touhou vào kho đồ người chơi (chủ bot dùng để lấy bất kỳ thẻ nào).
• `/admin_set_level <user> <level>`: Đặt cấp độ cho người chơi, đồng bộ XP chuẩn xác không bug.
• `/admin_confiscate <user> [id_the] [so_luong]`: Tước đoạt bài trừng phạt cheat (nhập ID = 0 để tịch thu toàn bộ).
• `/sync`: Đồng bộ lại cây lệnh Slash Commands.

**⭐ CƠ CHẾ LÊN CẤP MỚI (+50 XP MỖI CẤP):**
• Lv.1 cần 100 XP để lên Lv.2
• Lv.2 cần 150 XP để lên Lv.3 (+50)
• Lv.3 cần 200 XP để lên Lv.4 (+50)
• Chuẩn xác tuyệt đối và không bao giờ bị bug!
"""
    embed = discord.Embed(title="🌸 HƯỚNG DẪN LỆNH BOT REIMU (FULL EDITION)", description=desc, color=0xDC2626)
    embed.set_footer(text="Hakurei Shrine • Gemini Flash + MongoDB Atlas")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="help", description="Xem hướng dẫn toàn bộ lệnh chơi game, boss raid và lệnh admin")
async def slash_help(interaction: discord.Interaction):
    await handle_help(interaction)

@bot.command(name="help")
async def prefix_help(ctx):
    await handle_help(ctx)

# --- LỆNH /wiki ---
@bot.tree.command(name="wiki", description="Tra cứu thông tin nhân vật hoặc dị biến trong Touhou Project")
@app_commands.describe(nhan_vat="Tên nhân vật Touhou cần tra cứu")
async def touhou_wiki(interaction: discord.Interaction, nhan_vat: str):
    await interaction.response.defer()
    prompt = f"Tra cứu thông tin Touhou Project cho: '{nhan_vat}'. Tóm tắt danh hiệu, năng lực, nơi ở và lời bình đanh đá của Reimu."
    try:
        wiki_text = await ask_gemini(prompt, REIMU_SYSTEM_PROMPT, temperature=0.7)
        embed = discord.Embed(title=f"🌸 Bách Khoa Gensokyo: {nhan_vat}", description=wiki_text[:4000], color=0xDC2626)
        await interaction.followup.send(embed=embed)
    except Exception:
        await interaction.followup.send("⛩️ Hòm công đức đông khách, bùa chú đang bị quá tải. Hãy thử lại sau nhé!")

# --- LỆNH /clearmem ---
@bot.tree.command(name="clearmem", description="Xóa sạch ký ức trò chuyện của Reimu với bạn trong kênh này")
async def slash_clear_memory(interaction: discord.Interaction):
    reset_memory(interaction.channel_id, interaction.user.id)
    embed = discord.Embed(title="🧹 Tẩy Não / Xóa Ký Ức", description="Đã dọn dẹp và làm mới lại ký ức hội thoại!", color=0x10B981)
    await interaction.response.send_message(embed=embed)

# --- LỆNH /sync ---
@bot.tree.command(name="sync", description="[CHỦ BOT DUY NHẤT] Xóa lệnh trùng lặp và đồng bộ lại Slash Commands")
async def slash_sync_commands(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message(
            f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**\nChỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới được đồng bộ lệnh!",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã đồng bộ thành công {len(synced)} lệnh Slash Commands chuẩn!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi đồng bộ: {e}")

@bot.command(name="sync")
async def prefix_sync_commands(ctx):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send(f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}> - ID: `{AUTHORIZED_ADMIN_ID}`) mới được đồng bộ lệnh!")
        return

    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Đã đồng bộ {len(synced)} lệnh Slash chuẩn!")
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {e}")

# --- LỆNH /dbcheck (KIỂM TRA TRẠNG THÁI DATABASE MONGODB ATLAS) ---
@bot.tree.command(name="dbcheck", description="Kiểm tra trạng thái kết nối MongoDB Atlas")
async def slash_dbcheck(interaction: discord.Interaction):
    await interaction.response.defer()
    connected, msg = test_and_connect_mongo()
    if connected and use_mongo:
        p_count = players_collection.count_documents({}) if players_collection is not None else 0
        embed = discord.Embed(
            title="☁️ TRẠNG THÁI DATABASE: MONGODB ATLAS",
            description=f"🟢 Đang kết nối ổn định! Dữ liệu được bảo toàn vĩnh viễn.\nTổng người chơi: **{p_count}**",
            color=0x10B981
        )
    else:
        embed = discord.Embed(
            title="🚨 CẢNH BÁO: CHƯA KẾT NỐI MONGODB ATLAS",
            description=f"⚠️ Đang dùng SQLite tạm thời trên container.\nChi tiết: {mongo_error_detail}",
            color=0xEF4444
        )
    await interaction.followup.send(embed=embed)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN trong biến môi trường (.env)!", flush=True)
    else:
        bot.run(DISCORD_TOKEN)
