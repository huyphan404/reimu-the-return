# ==============================================================================
# HAKUREI REIMU DISCORD BOT - FULL EDITION (UPDATED)
# GEMINI FLASH CHATBOT + MONGODB ATLAS CLOUD + TOUHOU GACHA & AUTO-BATTLE & RAID
# ==============================================================================
# 1. BOSS STATS: Phase 1 (35k HP, 15k DMG) & Phase 2 Thức Tỉnh (50k HP, 22k DMG)
# 2. BOSS DROP: Rương chiến lợi phẩm quy đổi 100% thành Vé Pull
# 3. BOSS COOLDOWN: Hồi chiêu 15 phút tính từ lúc có bất kỳ ai tham gia raid
# 4. ADMIN COMMANDS: /admin_set_level, /admin_confiscate, /admin_add_card (ID: 1502579398560317441)
# 5. LEVEL UP MỚI: Mỗi cấp tăng +50 XP (Lv.1: 100 XP, Lv.2: 150 XP, Lv.3: 200 XP...)
# 6. EVOL UPDATE:
#    - Luôn hiển thị ID nhân vật: [#13] Reimu Hakurei, [#16] Sakuya Izayoi
#    - Lệnh /evol hỗ trợ nhập trực tiếp ID hoặc tên
#    - Hoạt ảnh GIF hiển thị trực tiếp trong Discord (embed image & direct GIF)
#    - Buff tối thượng Ace: Mọi nhân vật đạt Ace đều được cộng +100 ATK (Power) và +250 Máu (HP)!
# 7. LIVE RAID COMBAT: Trận chiến chạy turn-by-turn theo thời gian thực để mọi người cùng theo dõi!
# ==============================================================================

import os
import time
import json
import random
import asyncio
import threading
import sqlite3
from datetime import datetime
from typing import Optional, Union, List, Dict
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
    try:
        return int(user_id) == AUTHORIZED_ADMIN_ID
    except (ValueError, TypeError):
        return False

# ==============================================================================
# BUFF CHỈ SỐ ACE (ÁP DỤNG CHO MỌI NHÂN VẬT TIẾN HÓA ACE)
# ==============================================================================
ACE_POWER_BUFF = 100  # +100 ATK
ACE_HP_BUFF = 250     # +250 Máu

# ==============================================================================
# 1. WEB SERVER CHO RENDER FREE
# ==============================================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Hakurei Reimu Discord Bot (Gacha + Battle + Live Raid + Admin) is online!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==============================================================================
# 2. HỆ THỐNG CẤP ĐỘ & XP MỚI (+50 XP MỖI CẤP, CHUẨN XÁC TUYỆT ĐỐI)
# ==============================================================================
MAX_LEVEL = 100

def get_xp_needed_for_level(level: int) -> int:
    if level < 1:
        level = 1
    return 100 + (level - 1) * 50

def get_total_xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    n = level - 1
    return 25 * n * (n + 3)

def calculate_level_from_xp(total_xp: int) -> int:
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
    1: {"id": 1, "name": "Hecatia Lapislazuli", "rank": "SS", "power": 850, "hp": 8500, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082071178416229/hecatia_lapislazuli_touhou_drawn_by_mituba_ooka__6cf49ea15f88841c7a50e50655e920d0.png?ex=6aa9669a&is=6aa8151a&hm=3a5bc70cdd27beae06fcc8ebe8845a514d8ee28844580b64b42bf53ee836833b&=&format=webp&quality=lossless&width=769&height=1024"},
    2: {"id": 2, "name": "Junko", "rank": "SS", "power": 800, "hp": 8000, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082919887179776/junko_touhou_drawn_by_xianjian_lingluan__8a51bec2beefde48ae3411fb6463271d.png?ex=6aa96764&is=6aa815e4&hm=e7443f7a7e2599534ec7ee7eb8f89f57789f193f954627a92a4487f7b1188d02&=&format=webp&quality=lossless&width=658&height=1024"},
    3: {"id": 3, "name": "Okina Matara", "rank": "SS", "power": 750, "hp": 7500, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083695984672869/images.png?ex=6aa9681d&is=6aa8169d&hm=b77956843b05910b691fc2bb16716d3201f69bcbe72619668051ff7c95fa3c1a&=&format=webp&quality=lossless&width=300&height=512"},
    4: {"id": 4, "name": "Yukari Yakumo", "rank": "SS", "power": 720, "hp": 7200, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084814252974152/cf5e86717425d5168f5c7bbfd6d855e9.png?ex=6aa96928&is=6aa817a8&hm=beb9f3aec3fcedfd254c210641da72fb13ba9d8b00c4ad1404b1802da51ca2c1&=&format=webp&quality=lossless&width=365&height=512"},
    5: {"id": 5, "name": "Suika Ibuki", "rank": "S", "power": 670, "hp": 6700, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083290684882954/images.png?ex=6aa967bd&is=6aa8163d&hm=e9153ff99d60077e29d835ea3de49eaf55ba17f79f22e99203b8683cc66f4f75&=&format=webp&quality=lossless"},
    6: {"id": 6, "name": "Eirin Yagokoro", "rank": "S", "power": 640, "hp": 6600, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083046265749645/ef37dd0758b130203b6bdf9b404d9793.png?ex=6aa96782&is=6aa81602&hm=745388e38f3d20ef689b7ad4fb32153ccf48a8c8296070ca4442c19308b11543&=&format=webp&quality=lossless&width=725&height=1024"},
    7: {"id": 7, "name": "Yuuka Kazami", "rank": "S", "power": 630, "hp": 6300, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082802954444820/images.png?ex=6aa96748&is=6aa815c8&hm=2913b1ba8f4b29323609ba326dc029ce985d332648dd00106af461acc09b19b0&=&format=webp&quality=lossless&width=385&height=512"},
    8: {"id": 8, "name": "Yuyuko Saigyouji", "rank": "S", "power": 620, "hp": 6200, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549361604234313839/images.png?ex=6aaa6af0&is=6aa91970&hm=674ea5e76356fcd1cea0a0545f5eb9a5ea5d9513216ebf6bccbc175569ab934b&=&format=webp&quality=lossless"},
    9: {"id": 9, "name": "Flandre Scarlet", "rank": "S", "power": 610, "hp": 5700, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082626147483798/y4nci1hurauf1.png?ex=6aa9671e&is=6aa8159e&hm=a2b7e911c0855f2715e551e3ebfb0299758a3461ba0d6b14222e130bb2160ce2&=&format=webp&quality=lossless&width=361&height=512"},
    10: {"id": 10, "name": "Kaguya Houraisan", "rank": "S", "power": 590, "hp": 6400, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082450930696282/images.png?ex=6aa966f4&is=6aa81574&hm=363a0b7d509db06c3773fba176ede9646cfef4a95c5d2515703120d30bfc4e94&=&format=webp&quality=lossless&width=361&height=512"},
    11: {"id": 11, "name": "Remilia Scarlet", "rank": "S", "power": 560, "hp": 5600, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079793461633065/images.png?ex=6aa9647b&is=6aa812fb&hm=19fc0f72cd5fca597f9eeae493b1c7c663d11ffc98fff679bfd2dfdb588950e1&=&format=webp&quality=lossless"},
    12: {"id": 12, "name": "Utsuho Reiuji (Okuu)", "rank": "S", "power": 550, "hp": 5300, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081971169304647/images.png?ex=6aa96682&is=6aa81502&hm=6f7668c4db22133f1aa0bdc07ec7fa2c050ff4e4d220f744cd02e8cc04662c0f&=&format=webp&quality=lossless"},
    13: {"id": 13, "name": "Reimu Hakurei", "rank": "A", "power": 500, "hp": 5000, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549078962746171463/images.png?ex=6aa963b5&is=6aa81235&hm=3fa720bd7311e4ca45789c6a0112327878135e9d9944c31c6ed2ea1f60885853&=&format=webp&quality=lossless"},
    14: {"id": 14, "name": "Fujiwara no Mokou", "rank": "A", "power": 490, "hp": 5200, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080689079754812/images.png?ex=6aa96550&is=6aa813d0&hm=962822a973a1e1535007f1597c0c7b468a287ec0f3d212dcf58c7ca1d9a0c5a3&=&format=webp&quality=lossless"},
    15: {"id": 15, "name": "Kasen Ibaraki", "rank": "A", "power": 480, "hp": 4900, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080849083924531/images.png?ex=6aa96576&is=6aa813f6&hm=802e894777a879074a59fa3dcae74394f73523e31d9b9272f19e4aff95ec36aa&=&format=webp&quality=lossless"},
    16: {"id": 16, "name": "Sakuya Izayoi", "rank": "A", "power": 460, "hp": 4500, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079438719844372/images.png?ex=6aa96426&is=6aa812a6&hm=263f21e095ef7f36f411473590d92012d350ab3e7b8ea13e72a443a0672a719a&=&format=webp&quality=lossless&width=307&height=512"},
    17: {"id": 17, "name": "Marisa Kirisame", "rank": "A", "power": 450, "hp": 4400, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081039660654612/images.png?ex=6aa965a4&is=6aa81424&hm=0ff6e9df5e0d49e483e0560bba442927385b8fa930187276b921012ad16071ad&=&format=webp&quality=lossless"},
    18: {"id": 18, "name": "Youmu Konpaku", "rank": "B", "power": 410, "hp": 4100, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081249036116059/images.png?ex=6aa965d6&is=6aa81456&hm=2dc107dd368c53b9c1a94c54e1cfe4a1d9b7ff6ac224dc830d6c9297d5b19e53&=&format=webp&quality=lossless"},
    19: {"id": 19, "name": "Reisen Udongein Inaba", "rank": "B", "power": 390, "hp": 3900, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081419777577130/images.png?ex=6aa965ff&is=6aa8147f&hm=8948e38a77f4c00d21819a6e34e2fd1a13b1853e4c92886d1e6ac3ccae6afd75&=&format=webp&quality=lossless"},
    20: {"id": 20, "name": "Patchouli Knowledge", "rank": "B", "power": 380, "hp": 3200, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081654948134994/images.png?ex=6aa96637&is=6aa814b7&hm=7e444589e6db73d24fb53445ea713ddb5e5bcc7c75e58ea91a619a694f0d23eb&=&format=webp&quality=lossless&width=385&height=512"},
    21: {"id": 21, "name": "Cirno", "rank": "B", "power": 300, "hp": 3000, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080400742195260/images.png?ex=6aa9650c&is=6aa8138c&hm=e3d3d5bf2196f4a3b0fdafcc37063c5ad16897726bdf5514be92b3f3b7719cc4&=&format=webp&quality=lossless"},
    22: {"id": 22, "name": "Hong Meiling", "rank": "C", "power": 260, "hp": 2800, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362028601417869/images.png?ex=6aaa6b55&is=6aa919d5&hm=95498119b7d8e5f7563f28bde4efabe919878bcd40b70bf4037edb73eac009aa&=&format=webp&quality=lossless&width=363&height=512"},
    23: {"id": 23, "name": "Rumia", "rank": "C", "power": 220, "hp": 2200, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362134440485004/images.png?ex=6aaa6b6e&is=6aa919ee&hm=860b0ede2ccf2585fb605cdef8864b141980395e5eee9d3f4f78c5692fa3827b&=&format=webp&quality=lossless&width=361&height=512"},
    24: {"id": 24, "name": "Mystia Lorelei", "rank": "C", "power": 200, "hp": 2000, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362390641020948/84f96d0ce2f04a42a63cff967b6ec6bf.png?ex=6aaa6bab&is=6aa91a2b&hm=9c09d786873a4a70d3dbc27e10934ee7e8463964d89acc42cc1214e29e3185a2&=&format=webp&quality=lossless&width=385&height=512"},
    25: {"id": 25, "name": "Wriggle Nightbug", "rank": "C", "power": 180, "hp": 1800, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362613421351043/images.png?ex=6aaa6be0&is=6aa91a60&hm=56779b03181c9c34cb7de4974bfdc60dc452be7d450818daeaeddbf8f36250d0&=&format=webp&quality=lossless"},
    26: {"id": 26, "name": "Tewi Inaba", "rank": "C", "power": 150, "hp": 1500, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362906154410034/images.png?ex=6aaa6c26&is=6aa91aa6&hm=ac3b4dca861840ea6c0c5b41288fb528b56543df60081fe62ff774f75449e847&=&format=webp&quality=lossless"}
}

CARDS_BY_RANK = {
    "SS": [c for c in CARDS_DATA.values() if c["rank"] == "SS"],
    "S":  [c for c in CARDS_DATA.values() if c["rank"] == "S"],
    "A":  [c for c in CARDS_DATA.values() if c["rank"] == "A"],
    "B":  [c for c in CARDS_DATA.values() if c["rank"] == "B"],
    "C":  [c for c in CARDS_DATA.values() if c["rank"] == "C"],
}

# ==============================================================================
# BOSS REIMU DỊ HÌNH - CHỈ SỐ MỚI (PHASE 1: 35K HP, 15K DMG | PHASE 2: 50K HP, 22K DMG)
# ==============================================================================
BOSS_CONFIG = {
    "name": "Reimu Dị Hình - Phase 1",
    "desc": "Đó không phải Reimu, sẵn sàng giao chiến!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1549077421624401971/content.png?ex=6aa96245&is=6aa810c5&hm=c0248e497ee5afeed898b457736b39fc71368af3be1630f1cd59b5609c99fbeb&=&format=webp&quality=lossless&width=351&height=512",
    "hp": 35000,      # Phase 1: 35,000 HP
    "power": 3000,    # Phase 1: 3,000 DMG đánh thường
    "max_players": 6,
    "cooldown_seconds": 15 * 60  # 15 phút (900s) sau khi có bất kỳ ai tham gia raid
}

BOSS_PHASE2_CONFIG = {
    "name": "Reimu Dị Hình - Thức Tỉnh (Phase 2)",
    "desc": "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội!",
    "image": "https://media.discordapp.net/attachments/1549063334781911070/1549275653239472148/artwork.png?ex=6aaa1ae3&is=6aa8c963&hm=7187404882d4b8b0fcef91ef64aee3c73711924e971fb7b28b6fb3bf394a47d3&=&format=webp&quality=lossless&width=640&height=336",
    "hp": 50000,      # Phase 2: 50,000 HP
    "power": 10000    # Phase 2: 10,000 DMG đánh thường chia đều
}

boss_cooldown_until = 0.0

# ==============================================================================
# CƠ CHẾ TIẾN HÓA ACE 2 (KÈM ID NHÂN VẬT & DIRECT GIF HIỂN THỊ TRỰC TIẾP)
# ==============================================================================
EVOL_CONFIG = {
    13: {
        "id": 13,
        "key": "reimu",
        "name": "Reimu Hakurei",
        "title": "[#13] Reimu Hakurei - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 20,
        "required_pulls": 20,
        "evol_gif": "https://c.tenor.com/39VGItAUUCYAAAAC/reimu-reimu-hakurei.gif",
        "skill_name": "Bùa Chú Vô Tưởng Chuyển Sinh (Miễn Thương)",
        "skill_desc": "Miễn toàn bộ sát thương duy nhất 1 lần trong trận (30% xác suất mỗi hiệp khi ra trận nhận đòn, chỉ bảo vệ riêng Reimu).",
        "skill_gif": "https://c.tenor.com/gc4ws16CrTYAAAAC/reimu-touhou.gif",
        "bonus_power": 100,
        "bonus_hp": 250
    },
    16: {
        "id": 16,
        "key": "sakuya",
        "name": "Sakuya Izayoi",
        "title": "[#16] Sakuya Izayoi - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 30,
        "required_pulls": 30,
        "evol_gif": "https://c.tenor.com/cbZDFo59zV8AAAAC/touhou-izayoi-sakuya.gif",
        "skill_name": "Thời Gian Đóng Băng (Stun Boss)",
        "skill_desc": "Khiến Boss/đối thủ bị đóng băng (Stun) mất lượt duy nhất 1 lần trong trận (30% xác suất mỗi hiệp khi ở tiền tuyến).",
        "skill_gif": "https://c.tenor.com/0lC8dyA6_OwAAAAC/sakuya-izayoi-sakuya.gif",
        "bonus_power": 100,
        "bonus_hp": 250
    }
}
EVOL_CONFIG["13"] = EVOL_CONFIG[13]
EVOL_CONFIG["16"] = EVOL_CONFIG[16]

BOSS_SKILL_CONFIG = {
    "name": "Dị Hình Bùa Chú",
    "chance": 0.20,
    "damage": 5000,
    "desc": "Gây 5,000 DMG cho mỗi lá bài đang ở tiền tuyến (Boss không đánh thường)",
    "gif": "https://c.tenor.com/x27qU0sR_vkAAAAC/touhou-danmaku-touhou-yuyuko.gif"
}

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
        mongo_error_detail = "Chuỗi MONGO_URI vẫn chứa placeholder 'xxxxxx'."
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
        print("✅ [DATABASE] Kết nối MONGODB ATLAS thành công!", flush=True)
        return True, "Thành công"
    except Exception as e:
        use_mongo = False
        err_msg = f"{type(e).__name__}: {str(e)}"
        mongo_error_detail = err_msg
        print(f"⚠️ [DATABASE] Lỗi kết nối MongoDB ({err_msg}). Chuyển sang SQLite tạm thời.", flush=True)
        return False, err_msg

if MONGO_URI:
    test_and_connect_mongo()

if not use_mongo:
    conn = sqlite3.connect('reimu_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, username TEXT, first_seen TIMESTAMP, last_seen TIMESTAMP, interaction_count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS conversations (key TEXT PRIMARY KEY, history_json TEXT, updated_at TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS players (user_id TEXT PRIMARY KEY, player_data_json TEXT, updated_at TIMESTAMP)')
    conn.commit()

def get_default_player(user_id, username):
    return {
        "user_id": str(user_id),
        "username": username,
        "xp": 0,
        "level": 1,
        "pull_tickets": 0.0,
        "free_pulls_date": "",
        "free_pulls_remaining": 5,
        "last_daily_date": "",
        "inventory": {},
        "pull_stats": {},
        "evolutions": {},
        "team": [],
        "language": "vi",
        "battles_won": 0,
        "battles_total": 0,
        "last_battle_time": 0.0,
        "recent_opponents": []
    }

def get_card_pulled_count(player: dict, card_id: Union[int, str]) -> int:
    cid_str = str(card_id)
    inv_cnt = player.get("inventory", {}).get(cid_str, 0)
    pull_cnt = player.get("pull_stats", {}).get(cid_str, 0)
    return max(inv_cnt, pull_cnt)

def is_card_ace2(player: dict, card_id: Union[int, str]) -> bool:
    cid_str = str(card_id)
    return player.get("evolutions", {}).get(cid_str, 0) >= 2

def get_player(user_id, username="Visitor"):
    uid_str = str(user_id)
    now_date = datetime.now().strftime("%Y-%m-%d")
    data = None
    if use_mongo and players_collection is not None:
        try:
            doc = players_collection.find_one({"user_id": uid_str})
            if doc: data = doc
        except Exception as e:
            print(f"Lỗi đọc player MongoDB: {e}", flush=True)
    else:
        try:
            cursor.execute('SELECT player_data_json FROM players WHERE user_id = ?', (uid_str,))
            row = cursor.fetchone()
            if row and row[0]: data = json.loads(row[0])
        except Exception as e:
            print(f"Lỗi đọc player SQLite: {e}", flush=True)

    if not data:
        data = get_default_player(user_id, username)

    if "inventory" not in data: data["inventory"] = {}
    if "pull_stats" not in data: data["pull_stats"] = {}
    if "evolutions" not in data: data["evolutions"] = {}
    if "team" not in data: data["team"] = []
    if "xp" not in data: data["xp"] = 0
    if "pull_tickets" not in data: data["pull_tickets"] = 0.0
    if "language" not in data: data["language"] = "vi"

    if data.get("free_pulls_date") != now_date:
        data["free_pulls_date"] = now_date
        data["free_pulls_remaining"] = 5

    data["level"] = calculate_level_from_xp(data.get("xp", 0))
    return data

def save_player(player_data):
    uid_str = str(player_data["user_id"])
    now_iso = datetime.now().isoformat()
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
            cursor.execute('INSERT OR REPLACE INTO players (user_id, player_data_json, updated_at) VALUES (?, ?, ?)',
                           (uid_str, json.dumps(player_data, ensure_ascii=False), now_iso))
            conn.commit()
        except Exception as e:
            print(f"Lỗi ghi player SQLite: {e}", flush=True)

def get_all_opponents(exclude_id=None):
    opponents = []
    if use_mongo and players_collection is not None:
        try:
            for doc in players_collection.find():
                if str(doc.get("user_id")) != str(exclude_id) and doc.get("team") and len(doc["team"]) > 0:
                    opponents.append(doc)
        except Exception:
            pass
    else:
        try:
            cursor.execute('SELECT player_data_json FROM players')
            rows = cursor.fetchall()
            for r in rows:
                p = json.loads(r[0])
                if str(p.get("user_id")) != str(exclude_id) and p.get("team") and len(p["team"]) > 0:
                    opponents.append(p)
        except Exception:
            pass
    return opponents

def get_history_key(channel_id, user_id):
    return f"{channel_id}_{user_id}"

def get_conversation_history(channel_id, user_id):
    key = get_history_key(channel_id, user_id)
    if use_mongo and conversations_collection is not None:
        try:
            doc = conversations_collection.find_one({"key": key})
            if doc and "history" in doc: return doc["history"]
        except Exception: pass
    else:
        try:
            cursor.execute('SELECT history_json FROM conversations WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row and row[0]: return json.loads(row[0])
        except Exception: pass
    return []

def save_conversation_history(channel_id, user_id, history_list):
    key = get_history_key(channel_id, user_id)
    trimmed = history_list[-8:]
    now_iso = datetime.now().isoformat()
    if use_mongo and conversations_collection is not None:
        try:
            conversations_collection.update_one({"key": key}, {"$set": {"history": trimmed, "updated_at": now_iso}}, upsert=True)
        except Exception: pass
    else:
        try:
            cursor.execute('INSERT OR REPLACE INTO conversations (key, history_json, updated_at) VALUES (?, ?, ?)',
                           (key, json.dumps(trimmed, ensure_ascii=False), now_iso))
            conn.commit()
        except Exception: pass

def reset_memory(channel_id, user_id):
    key = get_history_key(channel_id, user_id)
    if use_mongo and conversations_collection is not None:
        try: conversations_collection.delete_one({"key": key})
        except Exception: pass
    else:
        try:
            cursor.execute('DELETE FROM conversations WHERE key = ?', (key,))
            conn.commit()
        except Exception: pass

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
    models = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.0-flash", "gemini-flash-latest"]
    last_err = None
    for model_name in models:
        for attempt in range(2):
            try:
                resp = await asyncio.to_thread(_call_gemini_sync, model_name, contents, system_instruction, temperature)
                if resp and resp.text: return resp.text
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str: break
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
active_raid = None

# ==============================================================================
# HỆ THỐNG XEM CHI TIẾT TRẬN CHIẾN & HOẠT ẢNH GIF KỸ NĂNG (IN-DISCORD)
# ==============================================================================
class BattleDetailsView(discord.ui.View):
    def __init__(self, turns_data):
        super().__init__(timeout=300)
        self.turns_data = turns_data
        self.current_idx = 0

        # Nếu số hiệp <= 25, bổ sung Dropdown Select để nhảy trực tiếp đến bất kỳ hiệp nào
        if 1 < len(self.turns_data) <= 25:
            options = []
            for i, t in enumerate(self.turns_data):
                has_skill = "✨ " if t.get("image") else ""
                lbl = f"{has_skill}{t.get('short_label', f'Hiệp {i+1}')}"[:100]
                desc = t.get("short_desc", f"Chi tiết diễn biến hiệp {i+1}")[:100]
                options.append(discord.SelectOption(label=lbl, value=str(i), description=desc))
            select_menu = discord.ui.Select(
                placeholder="🔽 Chọn hiệp muốn xem trực tiếp...",
                options=options,
                row=2
            )
            select_menu.callback = self.select_callback
            self.add_item(select_menu)

        self.update_buttons()

    async def select_callback(self, interaction: discord.Interaction):
        self.current_idx = int(interaction.data["values"][0])
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    def update_buttons(self):
        self.prev_btn.disabled = (self.current_idx <= 0)
        self.next_btn.disabled = (self.current_idx >= len(self.turns_data) - 1)
        self.skill_btn.disabled = not any(t.get("image") for t in self.turns_data)

    def get_current_embed(self):
        t = self.turns_data[self.current_idx]
        embed = discord.Embed(
            title=f"📜 CHI TIẾT TRẬN CHIẾN: {t.get('title', f'Hiệp {self.current_idx + 1}')}",
            description=t.get("desc", ""),
            color=t.get("color", 0x3B82F6)
        )
        for field in t.get("fields", []):
            if len(field) == 3:
                name, val, inl = field
                embed.add_field(name=name, value=val, inline=inl)
        if t.get("image"):
            embed.set_image(url=t["image"])
        embed.set_footer(
            text=f"Hiệp {self.current_idx + 1}/{len(self.turns_data)} • Nhấn 'Hiệp Dùng Kỹ Năng' để xem hoạt ảnh GIF chiêu thức trực tiếp"
        )
        return embed

    @discord.ui.button(label="⏮️ Đầu", style=discord.ButtonStyle.secondary, row=0)
    async def first_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_idx = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="◀ Hiệp Trước", style=discord.ButtonStyle.primary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_idx > 0:
            self.current_idx -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="Hiệp Sau ▶", style=discord.ButtonStyle.primary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_idx < len(self.turns_data) - 1:
            self.current_idx += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="⏭️ Cuối", style=discord.ButtonStyle.secondary, row=0)
    async def last_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_idx = len(self.turns_data) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    @discord.ui.button(label="✨ Hiệp Dùng Kỹ Năng (Xem GIF)", style=discord.ButtonStyle.success, row=1)
    async def skill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        skill_indices = [i for i, t in enumerate(self.turns_data) if t.get("image")]
        if not skill_indices:
            await interaction.response.send_message("Không có hiệp nào kích hoạt kỹ năng trong trận này!", ephemeral=True)
            return
        next_skills = [i for i in skill_indices if i > self.current_idx]
        self.current_idx = next_skills[0] if next_skills else skill_indices[0]
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

class OpenDetailsView(discord.ui.View):
    def __init__(self, turns_data):
        super().__init__(timeout=600)
        self.turns_data = turns_data

    @discord.ui.button(label="📜 Xem Chi Tiết Trận Chiến & GIF Kỹ Năng", style=discord.ButtonStyle.success, emoji="📜")
    async def open_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.turns_data:
            await interaction.response.send_message("Không có dữ liệu chi tiết cho trận chiến này!", ephemeral=True)
            return
        view = BattleDetailsView(self.turns_data)
        await interaction.response.send_message(embed=view.get_current_embed(), view=view, ephemeral=True)

# ==============================================================================
# 6. QUẢN LÝ BOSS RAID (LIVE TURN-BY-TURN COMBAT, 15P COOLDOWN, TICKET REWARDS)
# ==============================================================================
class RaidJoinView(discord.ui.View):
    def __init__(self, raid_data):
        super().__init__(timeout=120)
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
            await interaction.response.send_message("⚠️ Bạn chưa sở hữu thẻ bài nào! Hãy gõ `/pull` trước nhé!", ephemeral=True)
            return

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
        boss_cooldown_until = time.time() + BOSS_CONFIG["cooldown_seconds"]

        await interaction.response.send_message(f"🔥 {interaction.user.mention} đã tham chiến! ({count}/{BOSS_CONFIG['max_players']} dũng giả)", ephemeral=False)

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
            try: await self.raid_data["msg"].edit(view=self)
            except Exception: pass

        if active_raid is self.raid_data:
            participants = self.raid_data.get("participants", [])
            channel_id = self.raid_data.get("channel_id")
            channel = bot.get_channel(channel_id)
            if participants and channel:
                await channel.send(f"⏰ **Hết thời gian chuẩn bị!** Toàn bộ {len(participants)} dũng giả đồng loạt xuất quân khai chiến với Reimu Dị Hình!")
                await execute_raid(channel, self.raid_data)
            elif channel:
                active_raid = None
                await channel.send("⌛ Không có ai dám nghênh chiến, Reimu Dị Hình đã trốn thoát...")

def get_hp_bar(current_hp, max_hp, total_blocks=10):
    ratio = max(0.0, min(1.0, current_hp / max_hp)) if max_hp > 0 else 0
    filled = int(round(ratio * total_blocks))
    return "▰" * filled + "▱" * (total_blocks - filled)

async def execute_raid(channel, raid_data):
    global active_raid, boss_cooldown_until
    active_raid = None
    participants = raid_data["participants"]
    if not participants:
        await channel.send("⛩️ Reimu Dị Hình đã biến mất vì không có ai nghênh chiến...")
        return

    boss_cooldown_until = max(boss_cooldown_until, time.time() + BOSS_CONFIG["cooldown_seconds"])

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

        team_cards = []
        for cid in team_cids[:3]:
            card = CARDS_DATA.get(cid)
            if card:
                is_ace2 = is_card_ace2(p, cid)
                ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
                ace_hp = ACE_HP_BUFF if is_ace2 else 0
                card_pwr = card["power"] + lvl_buff + ace_pwr
                card_hp = card["hp"] + lvl_buff + ace_hp
                card_name = f"[Ace 2 ⭐⭐] #{card['id']:02d} {card['name']}" if is_ace2 else f"#{card['id']:02d} {card['name']}"
                team_cards.append({
                    "cid": cid,
                    "name": card_name,
                    "base_name": card["name"],
                    "rank": card["rank"],
                    "power": card_pwr,
                    "max_hp": card_hp,
                    "current_hp": card_hp,
                    "is_ace2": is_ace2
                })

        combatants.append({
            "uid": uid,
            "username": p["username"],
            "level": p["level"],
            "team_cards": team_cards,
            "current_card_index": 0,
            "is_alive": len(team_cards) > 0,
            "total_dmg": 0,
            "sakuya_stun_used": False,
            "reimu_invul_used": False,
            "death_round": None
        })

    # Khởi tạo màn hình đấu Boss trực tiếp (Live Turn-by-Turn)
    p1_max_hp = BOSS_CONFIG["hp"]
    p1_hp = p1_max_hp
    p1_power = BOSS_CONFIG["power"]
    
    init_embed = discord.Embed(
        title="⚔️ ĐẠI CHIẾN BẮT ĐẦU: REIMU DỊ HÌNH (PHASE 1)",
        description=f"🔥 **{len(combatants)} Dũng Giả** cùng đội quân thẻ bài đã dàn trận nghênh chiến!\nTheo dõi diễn biến từng hiệp trực tiếp ngay bên dưới!",
        color=0xDC2626
    )
    init_embed.set_thumbnail(url=BOSS_CONFIG["image"])
    init_embed.add_field(name="❤️ Máu Boss Phase 1:", value=f"`{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**", inline=False)
    battle_msg = await channel.send(embed=init_embed)
    await asyncio.sleep(2.0)

    p1_rounds = 0
    max_rounds = 35
    p1_battle_history = []
    all_raid_turns = []

    # CHẠY TURN-BY-TURN PHASE 1
    while p1_hp > 0 and p1_rounds < max_rounds:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants:
            break

        p1_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        boss_stunned = False
        sakuya_stun_notif = None
        turn_image = None

        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 16 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.30:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#16] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (30%)! ❄️ Boss bị **STUN** mất lượt!"
                    break

        round_player_dmg = sum(ac["power"] for ac in frontline_cards)
        p1_hp = max(0, p1_hp - round_player_dmg)
        for c in active_combatants:
            c["total_dmg"] += c["team_cards"][c["current_card_index"]]["power"]

        boss_action_log = ""
        if p1_hp <= 0:
            boss_action_log = "💥 **Reimu Dị Hình Phase 1 đã bị đánh gục hoàn toàn!**"
        elif boss_stunned:
            boss_action_log = "❄️ Boss bị đóng băng thời gian, bất lực không thể phản công!"
        else:
            if random.random() < 0.20:
                turn_image = BOSS_SKILL_CONFIG["gif"]
                boss_action_log = "👹 **[NỘI TẠI BOSS] Reimu Dị Hình** thi triển **Dị Hình Bùa Chú** (20%)! Giáng **5,000 DMG** diện rộng!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.30:
                            c["reimu_invul_used"] = True
                            invul = True
                            if not turn_image or turn_image == BOSS_SKILL_CONFIG["gif"]:
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (30%)! MIỄN THƯƠNG!"
                    if not invul:
                        ac["current_hp"] -= 5000
            else:
                num_front = len(frontline_cards)
                dmg_per_card = max(100, p1_power // num_front)
                boss_action_log = f"⚔️ Boss đánh thường tổng **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.30:
                            c["reimu_invul_used"] = True
                            invul = True
                            turn_image = EVOL_CONFIG[13]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                    if not invul:
                        ac["current_hp"] -= dmg_per_card

        push_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["current_hp"] <= 0:
                ac["current_hp"] = 0
                dead_name = ac["name"]

                # Lá bài trước khi chết đều thành công đổi sát thương vs Boss
                trade_dmg = ac["power"]
                p1_hp = max(0, p1_hp - trade_dmg)
                c["total_dmg"] += trade_dmg
                push_logs.append(f"💥 **[ĐỔI SÁT THƯƠNG]** **{dead_name}** ({c['username']}) trước khi gục ngã đã thành công đổi **{trade_dmg:,} DMG** lên Boss!")

                c["current_card_index"] += 1
                if c["current_card_index"] < len(c["team_cards"]):
                    next_card = c["team_cards"][c["current_card_index"]]
                    push_logs.append(f"💀 **{dead_name}** ({c['username']}) gục! ➡️ Đẩy **{next_card['name']}** (❤️{next_card['current_hp']:,} HP) lên!")
                else:
                    c["is_alive"] = False
                    c["death_round"] = p1_rounds
                    push_logs.append(f"☠️ **{c['username']}** đã hết thẻ bài và tử trận!")

        round_card_status = []
        for c in combatants:
            if c["current_card_index"] < len(c["team_cards"]):
                cur_c = c["team_cards"][c["current_card_index"]]
                round_card_status.append(f"• **{c['username']}**: {cur_c['name']} (❤️ {max(0, cur_c['current_hp']):,}/{cur_c['max_hp']:,} HP)")
            else:
                round_card_status.append(f"• **{c['username']}**: ☠️ Đã tử trận")

        round_embed = discord.Embed(
            title=f"⚔️ HIỆP {p1_rounds} - PHASE 1: REIMU DỊ HÌNH",
            description=f"❤️ **Máu Boss:** `{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**",
            color=0xDC2626
        )
        round_embed.add_field(name="💥 Tiền Tuyến Tấn Công:", value=f"Toàn quân gây **{round_player_dmg:,} DMG** lên Boss!", inline=False)
        if sakuya_stun_notif:
            round_embed.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
        round_embed.add_field(name="👺 Phản Kích Của Boss:", value=boss_action_log, inline=False)
        if push_logs:
            round_embed.add_field(name="🔄 Thay Đổi Tiền Tuyến:", value="\n".join(push_logs), inline=False)
        round_embed.add_field(name="🛡️ Tình Trạng Tiền Tuyến Hiện Tại:", value="\n".join(round_card_status), inline=False)

        if turn_image:
            round_embed.set_image(url=turn_image)
        else:
            round_embed.set_thumbnail(url=BOSS_CONFIG["image"])

        p1_battle_history.append(f"Hiệp {p1_rounds}: Gây {round_player_dmg:,} DMG (Boss còn {p1_hp:,} HP).")
        all_raid_turns.append({
            "round": p1_rounds,
            "phase": 1,
            "title": f"Phase 1 - Hiệp {p1_rounds}: Reimu Dị Hình",
            "short_label": f"P1 - Hiệp {p1_rounds}",
            "short_desc": f"Boss P1 còn {p1_hp:,} HP",
            "desc": f"👹 **Reimu Dị Hình Phase 1**\n❤️ Máu Boss: `{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**",
            "color": 0xDC2626,
            "image": turn_image,
            "fields": [
                ("💥 Tiền Tuyến Tấn Công:", f"Toàn quân gây **{round_player_dmg:,} DMG** lên Boss!", False),
                *([("❄️ Kỹ Năng Đột Biến:", sakuya_stun_notif, False)] if sakuya_stun_notif else []),
                ("👺 Phản Kích Của Boss:", boss_action_log, False),
                *([("🔄 Thay Đổi Tiền Tuyến & Đổi Sát Thương:", "\n".join(push_logs), False)] if push_logs else []),
                ("🛡️ Tình Trạng Tiền Tuyến Hiện Tại:", "\n".join(round_card_status), False)
            ]
        })
        try:
            await battle_msg.edit(embed=round_embed)
        except Exception:
            pass

        if p1_hp <= 0:
            break
        await asyncio.sleep(1.8)

    p1_defeated = (p1_hp <= 0)
    if not p1_defeated:
        embed_fail = discord.Embed(
            title="❌ QUÂN ĐOÀN THẤT THỦ TẠI PHASE 1!",
            description=f"Toàn bộ dũng giả đã tử trận sau {p1_rounds} hiệp!\nBoss Phase 1 còn **{p1_hp:,} HP** và đã trốn thoát.\n⏳ Hồi chiêu **15 phút** đã kích hoạt!",
            color=0xEF4444
        )
        embed_fail.set_thumbnail(url=BOSS_CONFIG["image"])
        await channel.send(embed=embed_fail, view=OpenDetailsView(all_raid_turns))
        return

    # TRAO THƯỞNG PHASE 1
    p1_rewards_data = {}
    for uid in participants:
        p = get_player(uid)
        p1_total = 0.0
        p1_items = []
        for g_idx in range(1, 4):
            roll = random.random()
            if roll < 0.40:
                t_val = 0.5
                d_str = "+0.5 Vé (40%)"
            else:
                t_val = 1.0 / 3.0
                d_str = "+0.33 Vé (60%)"
            p1_total += t_val
            p1_items.append(f"Quà {g_idx}: {d_str}")
        p["pull_tickets"] += p1_total
        p["xp"] += 100
        save_player(p)
        p1_rewards_data[uid] = {"total_pulls": p1_total, "items": p1_items, "username": p["username"]}

    # THÔNG BÁO PHASE 2 VÀ HỒI PHỤC 100% MÁU TOÀN BỘ LÁ BÀI
    p2_alert_embed = discord.Embed(
        title="🚨 DỊ BIẾN BIẾN ĐỔI - BÙA CHÚ RUNG ĐỘNG DỮ DỘI! (PHASE 2)",
        description=(
            "⚡ **Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội!**\n\n"
            f"👺 **{BOSS_PHASE2_CONFIG['name']}** đã thức tỉnh ma lực tối thượng!\n"
            f"❤️ **Máu tăng lên:** **`50,000 HP`**\n"
            f"⚔️ **Sát thương đánh thường:** **`10,000 DMG`** *(chia đều cho tiền tuyến)*\n\n"
            f"✨ **PHÉP MÀU THANH TẨY:**\n"
            f"**Lập tức hồi sinh và hồi 100% sinh lực toàn bộ thẻ bài của tất cả dũng giả!**"
        ),
        color=0x9333EA
    )
    p2_alert_embed.set_image(url=BOSS_PHASE2_CONFIG["image"])
    battle_msg = await channel.send(embed=p2_alert_embed)
    await asyncio.sleep(2.5)

    for c in combatants:
        c["current_card_index"] = 0
        c["is_alive"] = len(c["team_cards"]) > 0
        c["death_round"] = None
        c["sakuya_stun_used"] = False
        c["reimu_invul_used"] = False
        for card in c["team_cards"]:
            card["current_hp"] = card["max_hp"]

    # CHẠY TURN-BY-TURN PHASE 2
    p2_max_hp = BOSS_PHASE2_CONFIG["hp"]
    p2_hp = p2_max_hp
    p2_power = BOSS_PHASE2_CONFIG["power"]
    p2_rounds = 0
    p2_battle_history = []

    while p2_hp > 0 and p2_rounds < max_rounds:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants:
            break

        p2_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        boss_stunned = False
        sakuya_stun_notif = None
        turn_image = None

        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 16 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.30:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#16] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (30%)! ❄️ Boss Phase 2 bị **STUN**!"
                    break

        round_player_dmg = sum(ac["power"] for ac in frontline_cards)
        p2_hp = max(0, p2_hp - round_player_dmg)
        for c in active_combatants:
            c["total_dmg"] += c["team_cards"][c["current_card_index"]]["power"]

        boss_action_log = ""
        if p2_hp <= 0:
            boss_action_log = "⚡ **Reimu Dị Hình Phase 2 đã bị tiêu diệt hoàn toàn!**"
        elif boss_stunned:
            boss_action_log = "❄️ Boss Phase 2 bị đóng băng thời gian, không thể phát động đòn đánh!"
        else:
            if random.random() < 0.20:
                turn_image = BOSS_SKILL_CONFIG["gif"]
                boss_action_log = "👹 **[NỘI TẠI BOSS] Reimu Dị Hình** phát động **Dị Hình Bùa Chú** (20%)! Oanh tạc **5,000 DMG** diện rộng!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.30:
                            c["reimu_invul_used"] = True
                            invul = True
                            if not turn_image or turn_image == BOSS_SKILL_CONFIG["gif"]:
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (30%)! MIỄN THƯƠNG!"
                    if not invul:
                        ac["current_hp"] -= 5000
            else:
                num_front = len(frontline_cards)
                dmg_per_card = max(100, p2_power // num_front)
                boss_action_log = f"⚔️ Boss Phase 2 đánh thường tổng **{p2_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.30:
                            c["reimu_invul_used"] = True
                            invul = True
                            turn_image = EVOL_CONFIG[13]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                    if not invul:
                        ac["current_hp"] -= dmg_per_card

        push_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["current_hp"] <= 0:
                ac["current_hp"] = 0
                dead_name = ac["name"]

                # Lá bài trước khi chết đều thành công đổi sát thương vs Boss Phase 2
                trade_dmg = ac["power"]
                p2_hp = max(0, p2_hp - trade_dmg)
                c["total_dmg"] += trade_dmg
                push_logs.append(f"💥 **[ĐỔI SÁT THƯƠNG]** **{dead_name}** ({c['username']}) trước khi gục ngã đã thành công đổi **{trade_dmg:,} DMG** lên Boss Phase 2!")

                c["current_card_index"] += 1
                if c["current_card_index"] < len(c["team_cards"]):
                    next_card = c["team_cards"][c["current_card_index"]]
                    push_logs.append(f"💀 **{dead_name}** ({c['username']}) gục! ➡️ Đẩy **{next_card['name']}** (❤️{next_card['current_hp']:,} HP) lên!")
                else:
                    c["is_alive"] = False
                    c["death_round"] = p2_rounds
                    push_logs.append(f"☠️ **{c['username']}** cạn kiệt thẻ bài và tử trận!")

        round_card_status = []
        for c in combatants:
            if c["current_card_index"] < len(c["team_cards"]):
                cur_c = c["team_cards"][c["current_card_index"]]
                round_card_status.append(f"• **{c['username']}**: {cur_c['name']} (❤️ {max(0, cur_c['current_hp']):,}/{cur_c['max_hp']:,} HP)")
            else:
                round_card_status.append(f"• **{c['username']}**: ☠️ Đã tử trận")

        round_embed = discord.Embed(
            title=f"⚡ HIỆP {p2_rounds} - PHASE 2: THỨC TỈNH",
            description=f"❤️ **Máu Boss Phase 2:** `{get_hp_bar(p2_hp, p2_max_hp)}` **{p2_hp:,}/{p2_max_hp:,} HP**",
            color=0x9333EA
        )
        round_embed.add_field(name="💥 Tiền Tuyến Tấn Công:", value=f"Toàn quân dồn **{round_player_dmg:,} DMG**!", inline=False)
        if sakuya_stun_notif:
            round_embed.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
        round_embed.add_field(name="👹 Boss Phase 2 Ra Đòn:", value=boss_action_log, inline=False)
        if push_logs:
            round_embed.add_field(name="🔄 Thay Đổi Tiền Tuyến:", value="\n".join(push_logs), inline=False)
        round_embed.add_field(name="🛡️ Tình Trạng Tiền Tuyến Hiện Tại:", value="\n".join(round_card_status), inline=False)

        if turn_image:
            round_embed.set_image(url=turn_image)
        else:
            round_embed.set_thumbnail(url=BOSS_PHASE2_CONFIG["image"])

        p2_battle_history.append(f"Hiệp {p2_rounds}: Gây {round_player_dmg:,} DMG (Boss còn {p2_hp:,} HP).")
        all_raid_turns.append({
            "round": p2_rounds,
            "phase": 2,
            "title": f"Phase 2 - Hiệp {p2_rounds}: Thức Tỉnh",
            "short_label": f"P2 - Hiệp {p2_rounds}",
            "short_desc": f"Boss Phase 2 còn {p2_hp:,} HP",
            "desc": f"⚡ **Reimu Dị Hình - Thức Tỉnh Phase 2**\n❤️ Máu Boss: `{get_hp_bar(p2_hp, p2_max_hp)}` **{p2_hp:,}/{p2_max_hp:,} HP**",
            "color": 0x9333EA,
            "image": turn_image,
            "fields": [
                ("💥 Tiền Tuyến Tấn Công:", f"Toàn quân dồn **{round_player_dmg:,} DMG**!", False),
                *([("❄️ Kỹ Năng Đột Biến:", sakuya_stun_notif, False)] if sakuya_stun_notif else []),
                ("👹 Boss Phase 2 Ra Đòn:", boss_action_log, False),
                *([("🔄 Thay Đổi Tiền Tuyến & Đổi Sát Thương:", "\n".join(push_logs), False)] if push_logs else []),
                ("🛡️ Tình Trạng Tiền Tuyến Hiện Tại:", "\n".join(round_card_status), False)
            ]
        })
        try:
            await battle_msg.edit(embed=round_embed)
        except Exception:
            pass

        if p2_hp <= 0:
            break
        await asyncio.sleep(1.8)

    p2_defeated = (p2_hp <= 0)
    total_raid_dmg = sum(c["total_dmg"] for c in combatants)

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
                    t_val = 10.0
                    d_str = "🔥 **+10 Vé** (20%)"
                elif roll < 0.60:
                    t_val = 5.0
                    d_str = "💎 **+5 Vé** (40%)"
                else:
                    t_val = 3.0
                    d_str = "✨ **+3 Vé** (60%)"
                p2_total += t_val
                p2_items.append(f"Quà {g_idx}: {d_str}")
            p["pull_tickets"] += p2_total
            p["xp"] += 150
            save_player(p)
            p2_rewards_data[uid] = {
                "total_pulls": p2_total,
                "items": p2_items,
                "username": p["username"],
                "new_level": p["level"],
                "old_level": old_lvl,
                "total_tickets": p["pull_tickets"]
            }

    final_embed = discord.Embed(
        title="⚔️ KẾT QUẢ ĐẠI CHIẾN: REIMU DỊ HÌNH (FULL 2 PHASES)!",
        description=(
            f"**Phase 1:** 🎉 Hạ gục sau **{p1_rounds} hiệp**\n"
            f"**Phase 2:** {'🎉 TOÀN THẮNG HUY HOÀNG (Boss 0 HP)' if p2_defeated else f'❌ THẤT THỦ (Boss còn {p2_hp:,}/{p2_max_hp:,} HP)'} sau **{p2_rounds} hiệp**\n"
            f"**Tổng Sát Thương Cả 2 Phase:** **{total_raid_dmg:,} DMG**\n"
            f"⏳ **Hồi chiêu Boss tiếp theo:** **15 phút**"
        ),
        color=0x10B981 if p2_defeated else 0xF59E0B
    )
    final_embed.set_thumbnail(url=BOSS_PHASE2_CONFIG["image"] if p2_defeated else BOSS_CONFIG["image"])

    p1_summary = [f"🎁 **{r['username']}**: +{r['total_pulls']:.2f} Vé Pull ({', '.join(r['items'])}) + 100 XP" for r in p1_rewards_data.values()]
    final_embed.add_field(name="📦 Phần Thưởng Phase 1 (100% Vé Pull):", value="\n".join(p1_summary), inline=False)

    if p2_defeated:
        p2_summary = []
        for r in p2_rewards_data.values():
            lvl_up = f" 🌟 **LÊN CẤP {r['new_level']}!**" if r['new_level'] > r['old_level'] else ""
            p2_summary.append(f"🏆 **{r['username']}**: Nhận **+{r['total_pulls']:.0f} Vé Pull** ({', '.join(r['items'])}) + 150 XP!{lvl_up}\n   └ *Tổng vé hiện có: {r['total_tickets']:.2f} vé*")
        final_embed.add_field(name="💎 Phần Thưởng Siêu Cấp Phase 2 (20% 10 vé, 40% 5 vé, 60% 3 vé):", value="\n".join(p2_summary), inline=False)
    else:
        final_embed.add_field(name="⚠️ Kết Quả Phase 2:", value=f"Boss Phase 2 còn {p2_hp:,} HP! Toàn bộ quà Phase 1 vẫn được bảo lưu trọn vẹn.", inline=False)

    await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))

# ==============================================================================
# 7. SỰ KIỆN BOT ON_READY & ON_MESSAGE
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
            name="Đền Hakurei | /help | /pull | /battle | Boss 35k HP"
        )
    )

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.author == bot.user:
        return

    content_lower = message.content.lower()
    global active_raid, boss_cooldown_until
    now_ts = time.time()
    
    if active_raid is None and now_ts >= boss_cooldown_until and not content_lower.startswith("!") and not content_lower.startswith("/"):
        if random.random() < 0.10:
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
            embed.add_field(name="❤️ Máu Boss (HP):", value=f"{BOSS_CONFIG['hp']:,} HP *(35k HP)*", inline=True)
            embed.add_field(name="⚔️ Sát Thương Đánh Thường:", value=f"• Phase 1: **{BOSS_CONFIG['power']:,} DMG** *(chia đều)*\n• Phase 2: **{BOSS_PHASE2_CONFIG['power']:,} DMG** *(chia đều)*", inline=True)
            embed.add_field(name=f"👥 Người Tham Gia (0/{BOSS_CONFIG['max_players']}):", value="Chưa có ai", inline=False)
            embed.add_field(
                name="🎁 Cơ Chế 2 Phase & Phần Thưởng Đột Phá:",
                value=(
                    "• **Phase 1:** 40% ra **0.5 Vé**, 60% ra **0.33 Vé**!\n"
                    f"• **Chuyển Phase 2 ({BOSS_PHASE2_CONFIG['hp']:,} HP / {BOSS_PHASE2_CONFIG['power']:,} DMG chia đều):** Hồi sinh & phục hồi **100% HP toàn bộ thẻ bài**!\n"
                    "• **Phase 2:** 20% ra **10 Vé Pull**, 40% ra **5 Vé Pull**, 60% ra **3 Vé Pull**!\n"
                    "• **Trận đấu trực tiếp:** Diễn biến từng hiệp được phát sóng trực tiếp!"
                ),
                inline=False
            )
            embed.add_field(
                name="⏱️ Quy Tắc Hồi Chiêu 15 Phút:",
                value="Khi có bất kỳ ai tham gia, lượt spawn tiếp theo sẽ cần chờ **15 phút**!",
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
        role_instruction = "\n[Người nói là HAN SEIKI - BỐ NUÔI của bạn. Xưng con gọi ba, cực kỳ ngoan ngoãn, dịu dàng, hiếu thảo và lễ phép!]" if is_father else f"\n[Người nói là khách viếng đền: {author_name}. Hãy xưng ta gọi ngươi, đanh đá và nhớ đòi cúng tiền công đức!]"

        saved_history = get_conversation_history(message.channel.id, message.author.id)
        history_context = "\n[LỊCH SỬ GẦN ĐÂY]:\n" + "\n".join(saved_history[-6:]) + "\n" if saved_history else ""

        async with message.channel.typing():
            try:
                reply_text = await ask_gemini(f"{history_context}[{author_name}]: {clean_text}", REIMU_SYSTEM_PROMPT + role_instruction, 0.85)
                if not reply_text: reply_text = "Hừ... Nhà ngươi lải nhải cái gì thế hả?"
                if len(reply_text) > 1950: reply_text = reply_text[:1950] + "..."
                saved_history.append(f"{author_name}: {clean_text}")
                saved_history.append(f"Reimu: {reply_text}")
                save_conversation_history(message.channel.id, message.author.id, saved_history)
                await message.reply(reply_text, mention_author=False)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    await message.reply("⛩️ Hừ, linh lực Gemini của đền Hakurei tạm thời bị quá tải! Hãy đợi khoảng 15-30 giây nhé!", mention_author=False)
                else:
                    await message.reply("⛩️ Hừ, bùa chú đền Hakurei tạm thời bị nhiễu loạn! Đợi vài giây rồi gọi lại ta!", mention_author=False)

    await bot.process_commands(message)

# ==============================================================================
# 8. CƠ CHẾ GACHA PULL TOUHOU
# ==============================================================================
def execute_single_pull(player):
    roll = random.random()
    if roll < 0.0001: chosen = random.choice(CARDS_BY_RANK["SS"])
    elif roll < 0.1001: chosen = random.choice(CARDS_BY_RANK["S"])
    elif roll < 0.3501: chosen = random.choice(CARDS_BY_RANK["A"])
    elif roll < 0.6501: chosen = random.choice(CARDS_BY_RANK["B"])
    else: chosen = random.choice(CARDS_BY_RANK["C"])

    cid_str = str(chosen["id"])
    already_owned = player["inventory"].get(cid_str, 0)
    is_duplicate = already_owned > 0
    player["inventory"][cid_str] = already_owned + 1
    player.setdefault("pull_stats", {})[cid_str] = player.get("pull_stats", {}).get(cid_str, 0) + 1

    converted_pulls = 0.0
    if is_duplicate:
        if chosen["rank"] == "SS": converted_pulls = 4.0
        elif chosen["rank"] == "S": converted_pulls = 2.0
        elif chosen["rank"] == "A": converted_pulls = 0.5
        elif chosen["rank"] == "B": converted_pulls = 1.0 / 3.0
        elif chosen["rank"] == "C": converted_pulls = 0.2
        player["pull_tickets"] += converted_pulls

    return chosen, is_duplicate, converted_pulls

# ==============================================================================
# 9. LỆNH ADMIN (OWNER EXCLUSIVE: 1502579398560317441)
# ==============================================================================
@bot.tree.command(name="admin_set_level", description="[CHỦ BOT DUY NHẤT] Đặt cấp độ cho người chơi (đồng bộ XP chuẩn xác không bug)")
@app_commands.describe(nguoi_dung="Chọn người chơi", cap_do="Cấp độ từ 1 đến 100")
async def slash_admin_set_level(interaction: discord.Interaction, nguoi_dung: discord.Member, cap_do: int):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message(f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}>) mới có quyền.", ephemeral=True)
        return
    cap_do = max(1, min(MAX_LEVEL, cap_do))
    target = get_player(nguoi_dung.id, nguoi_dung.display_name)
    old_lvl, old_xp = target["level"], target["xp"]
    new_xp = get_total_xp_for_level(cap_do)
    target["xp"] = new_xp
    target["level"] = cap_do
    save_player(target)
    embed = discord.Embed(
        title="⚙️ [ADMIN] ĐÃ THAY ĐỔI CẤP ĐỘ NGƯỜI CHƠI THÀNH CÔNG",
        description=f"👑 **Admin:** {interaction.user.mention}\n👤 **Mục tiêu:** {nguoi_dung.mention}\n📊 **Cấp độ:** `Lv.{old_lvl}` ➔ **`Lv.{cap_do}`**\n📈 **Đồng bộ XP:** `{old_xp:,} XP` ➔ **`{new_xp:,} XP`**",
        color=0x10B981
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name="setlevel", aliases=["setlvl"])
async def prefix_admin_set_level(ctx, member: discord.Member, level: int):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    level = max(1, min(MAX_LEVEL, level))
    target = get_player(member.id, member.display_name)
    target["xp"] = get_total_xp_for_level(level)
    target["level"] = level
    save_player(target)
    await ctx.send(f"✅ Đã set level cho {member.mention} thành **Lv.{level}** (Đồng bộ: {target['xp']:,} XP).")

@bot.tree.command(name="admin_confiscate", description="[CHỦ BOT DUY NHẤT] Tước đoạt thẻ bài của người chơi (trừng phạt cheat bẩn)")
@app_commands.describe(nguoi_dung="Người chơi bị xử phạt", id_the="ID thẻ từ 1-26 (hoặc nhập 0 để tịch thu TOÀN BỘ)", so_luong="Số lượng thẻ (0 = tịch thu hết)")
async def slash_admin_confiscate(interaction: discord.Interaction, nguoi_dung: discord.Member, id_the: int = 0, so_luong: int = 0):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    target = get_player(nguoi_dung.id, nguoi_dung.display_name)
    inv = target.get("inventory", {})
    team = target.get("team", [])

    if id_the == 0:
        total = sum(inv.values())
        target["inventory"] = {}
        target["team"] = []
        save_player(target)
        embed = discord.Embed(
            title="⚖️ [TRỪNG PHẠT CHEAT] ĐÃ TỊCH THU TOÀN BỘ THẺ BÀI!",
            description=f"🚨 **Admin:** {interaction.user.mention}\n👤 **Đối tượng:** {nguoi_dung.mention}\n📦 **Hình phạt:** Tước đoạt toàn bộ **{total} lá bài** và giải tán đội hình!",
            color=0xDC2626
        )
        await interaction.response.send_message(embed=embed)
        return

    if id_the not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-{len(CARDS_DATA)})!", ephemeral=True)
        return

    card = CARDS_DATA[id_the]
    cid_str = str(id_the)
    owned = inv.get(cid_str, 0)
    if owned <= 0:
        await interaction.response.send_message(f"⚠️ {nguoi_dung.display_name} không sở hữu thẻ #{id_the:02d} {card['name']}!", ephemeral=True)
        return

    to_remove = owned if (so_luong <= 0 or so_luong >= owned) else so_luong
    inv[cid_str] = owned - to_remove
    if inv[cid_str] <= 0:
        del inv[cid_str]
        if id_the in team: team.remove(id_the)

    target["inventory"] = inv
    target["team"] = team
    save_player(target)
    embed = discord.Embed(
        title="⚖️ [TRỪNG PHẠT CHEAT] ĐÃ TƯỚC ĐOẠT THẺ BÀI!",
        description=f"🚨 **Admin:** {interaction.user.mention}\n👤 **Đối tượng:** {nguoi_dung.mention}\n🎴 **Thẻ bị tước:** `[{card['rank']}]` **#{card['id']:02d} {card['name']}**\n🔢 **Số lượng:** `{to_remove}` lá (Còn lại: `{inv.get(cid_str, 0)}`)",
        color=0xDC2626
    )
    embed.set_thumbnail(url=card["image"])
    await interaction.response.send_message(embed=embed)

@bot.command(name="confiscate", aliases=["tuocdoat"])
async def prefix_admin_confiscate(ctx, member: discord.Member, card_id: int = 0, quantity: int = 0):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    target = get_player(member.id, member.display_name)
    inv = target.get("inventory", {})
    team = target.get("team", [])
    if card_id == 0:
        total = sum(inv.values())
        target["inventory"] = {}
        target["team"] = []
        save_player(target)
        await ctx.send(f"🚨 Đã tịch thu toàn bộ **{total} thẻ bài** của {member.mention}!")
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
    to_rem = owned if (quantity <= 0 or quantity >= owned) else quantity
    inv[cid_str] = owned - to_rem
    if inv[cid_str] <= 0:
        del inv[cid_str]
        if card_id in team: team.remove(card_id)
    target["inventory"] = inv
    target["team"] = team
    save_player(target)
    await ctx.send(f"⚖️ Đã tịch thu **{to_rem}x [{card['rank']}] #{card['id']:02d} {card['name']}** của {member.mention}!")

@bot.tree.command(name="admin_add_card", description="[CHỦ BOT DUY NHẤT] Cấp thẻ nhân vật Touhou vào kho đồ người chơi")
@app_commands.describe(id_the="Số ID thẻ từ 1 đến 26", so_luong="Số lượng thẻ (mặc định: 1)", nguoi_dung="Người nhận (để trống nếu tự cấp cho bản thân)")
async def slash_admin_add_card(interaction: discord.Interaction, id_the: int, so_luong: int = 1, nguoi_dung: discord.Member = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    if id_the not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-{len(CARDS_DATA)})!", ephemeral=True)
        return
    so_luong = max(1, so_luong)
    target = nguoi_dung if nguoi_dung else interaction.user
    target_player = get_player(target.id, target.display_name)
    cid_str = str(id_the)
    card = CARDS_DATA[id_the]
    inv = target_player.setdefault("inventory", {})
    new_cnt = inv.get(cid_str, 0) + so_luong
    inv[cid_str] = new_cnt
    target_player.setdefault("pull_stats", {})[cid_str] = target_player.get("pull_stats", {}).get(cid_str, 0) + so_luong
    save_player(target_player)
    embed = discord.Embed(
        title="🎁 [ADMIN] ĐÃ CẤP THẺ BÀI THÀNH CÔNG!",
        description=f"👑 **Admin:** {interaction.user.mention}\n👤 **Người nhận:** {target.mention}\n🎴 **Thẻ:** `[{card['rank']}]` **#{card['id']:02d} {card['name']}**\n📦 **Số lượng cấp:** `+{so_luong}` lá (Hiện có: `{new_cnt}` lá)",
        color=0x10B981
    )
    embed.set_thumbnail(url=card["image"])
    await interaction.response.send_message(embed=embed)

@bot.command(name="addcard", aliases=["adminaddcard", "givecard"])
async def prefix_admin_add_card(ctx, card_id: int, quantity: int = 1, member: discord.Member = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    if card_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-{len(CARDS_DATA)})!")
        return
    quantity = max(1, quantity)
    target = member if member else ctx.author
    target_player = get_player(target.id, target.display_name)
    cid_str = str(card_id)
    card = CARDS_DATA[card_id]
    inv = target_player.setdefault("inventory", {})
    new_cnt = inv.get(cid_str, 0) + quantity
    inv[cid_str] = new_cnt
    target_player.setdefault("pull_stats", {})[cid_str] = target_player.get("pull_stats", {}).get(cid_str, 0) + quantity
    save_player(target_player)
    await ctx.send(f"🎁 Đã cấp **+{quantity}x [{card['rank']}] #{card['id']:02d} {card['name']}** cho {target.mention} (Hiện có: {new_cnt})!")

# ==============================================================================
# 10. CƠ CHẾ TIẾN HÓA /evol (ACE 2 - HIỂN THỊ ID & HOẠT ẢNH TRỰC TIẾP)
# ==============================================================================
class EvolSelectView(discord.ui.View):
    def __init__(self, player, user_id):
        super().__init__(timeout=120)
        self.player = player
        self.user_id = user_id

    @discord.ui.button(label="⛩️ [#13] Tiến Hóa Reimu Ace 2 (20 Thẻ)", style=discord.ButtonStyle.danger, emoji="🌸")
    async def button_evol_reimu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 13)

    @discord.ui.button(label="🕰️ [#16] Tiến Hóa Sakuya Ace 2 (30 Thẻ)", style=discord.ButtonStyle.primary, emoji="⏳")
    async def button_evol_sakuya(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 16)

def execute_card_evolution(player, cid: int):
    cfg = EVOL_CONFIG.get(cid)
    if not cfg:
        return False, f"❌ Thẻ ID #{cid} hiện chưa hỗ trợ tính năng tiến hóa Ace 2!", None

    if is_card_ace2(player, cid):
        return False, f"⚠️ Thẻ **[#{cfg['id']:02d}] {cfg['name']}** của bạn đã đạt cảnh giới **{cfg['ace_level']}** từ trước rồi!", None

    pulled_cnt = get_card_pulled_count(player, cid)
    req_pulls = cfg["required_pulls"]

    if pulled_cnt < req_pulls:
        return (
            False,
            f"❌ Bạn chưa đủ số lần pull **[#{cfg['id']:02d}] {cfg['name']}**!\n• Số lần đã sở hữu/pull: **{pulled_cnt}/{req_pulls}** thẻ\n• Cần thêm: **{req_pulls - pulled_cnt}** thẻ nữa để tiến hóa!",
            None
        )

    if "evolutions" not in player or not isinstance(player["evolutions"], dict):
        player["evolutions"] = {}
    player["evolutions"][str(cid)] = 2
    save_player(player)

    embed = discord.Embed(
        title=f"🌟 TIẾN HÓA THÀNH CÔNG: [{cfg['ace_level']}] [#{cfg['id']:02d}] {cfg['name'].upper()}!",
        description=(
            f"⚡ **TIẾN TRÌNH ĐẠT CẢNH GIỚI TỐI THƯỢNG:**\n"
            f"🎴 **ID & Nhân vật:** **[#{cfg['id']:02d}] {cfg['name']}**\n"
            f"⭐ **Cấp bậc mới:** `{cfg['ace_level']}`\n"
            f"✨ **Số lần triệu hồi:** `{pulled_cnt}/{req_pulls}` thẻ\n\n"
            f"💪 **BUFF TỐI THƯỢNG ACE:**\n"
            f"⚔️ **+100 ATK (Power)** & ❤️ **+250 Máu (Max HP)** vĩnh viễn!\n\n"
            f"🔮 **KỸ NĂNG ĐỘC NHẤT ĐÃ KHAI MỞ:**\n"
            f"**{cfg['skill_name']}**\n"
            f"*{cfg['skill_desc']}*"
        ),
        color=0xEC4899 if cid == 13 else 0x3B82F6
    )
    embed.set_image(url=cfg["evol_gif"])
    embed.set_footer(text=f"Touhou Evolution System • Ace 2 Activated • Card ID #{cfg['id']:02d}")
    return True, "", embed

async def do_evolve_interaction(interaction: discord.Interaction, player, cid: int):
    success, err_msg, embed = execute_card_evolution(player, cid)
    if not success:
        await interaction.response.send_message(err_msg, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed)

async def handle_evol(ctx_or_interaction, nhan_vat_hoac_id: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)

    cid_target = None
    if nhan_vat_hoac_id:
        nv_clean = str(nhan_vat_hoac_id).lower().strip()
        if "13" in nv_clean or "reimu" in nv_clean:
            cid_target = 13
        elif "16" in nv_clean or "sakuya" in nv_clean:
            cid_target = 16

    if cid_target:
        success, err_msg, embed = execute_card_evolution(player, cid_target)
        if not success:
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(err_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(err_msg)
        else:
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
        return

    reimu_cnt = get_card_pulled_count(player, 13)
    reimu_ace = is_card_ace2(player, 13)
    reimu_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if reimu_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if reimu_cnt >= 20 else f"🔴 Chưa đủ ({reimu_cnt}/20)")

    sakuya_cnt = get_card_pulled_count(player, 16)
    sakuya_ace = is_card_ace2(player, 16)
    sakuya_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if sakuya_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if sakuya_cnt >= 30 else f"🔴 Chưa đủ ({sakuya_cnt}/30)")

    embed = discord.Embed(
        title="🌟 PHÒNG TIẾN HÓA NHÂN VẬT TOUHOU (EVOLUTION - ACE 2)",
        description=(
            "Triệu hồi đủ số lượng thẻ yêu cầu để tiến hóa nhân vật lên **Ace 2 ⭐⭐**!\n"
            "✨ **Buff tối thượng:** Mọi nhân vật đạt Ace đều được cộng **+100 ATK** và **+250 Máu**!\n\n"
            "👉 **Cú pháp theo ID:** `/evol id_hoac_ten:13` hoặc `/evol id_hoac_ten:16`\n"
            "Hoặc bấm các nút bên dưới để tiến hóa ngay:"
        ),
        color=0x8B5CF6
    )

    reimu_cfg = EVOL_CONFIG[13]
    embed.add_field(
        name=f"⛩️ [#{reimu_cfg['id']:02d}] {reimu_cfg['name']} (Yêu cầu 20 thẻ):",
        value=(
            f"• Trạng thái: **{reimu_status}**\n"
            f"• Đã triệu hồi: **{reimu_cnt}/20** lá\n"
            f"• Buff Ace: **+100 ATK** & **+250 HP**\n"
            f"• Kỹ năng: **{reimu_cfg['skill_name']}** (Miễn thương 1 lần trong trận, 30% mỗi hiệp)"
        ),
        inline=False
    )

    sakuya_cfg = EVOL_CONFIG[16]
    embed.add_field(
        name=f"🕰️ [#{sakuya_cfg['id']:02d}] {sakuya_cfg['name']} (Yêu cầu 30 thẻ):",
        value=(
            f"• Trạng thái: **{sakuya_status}**\n"
            f"• Đã triệu hồi: **{sakuya_cnt}/30** lá\n"
            f"• Buff Ace: **+100 ATK** & **+250 HP**\n"
            f"• Kỹ năng: **{sakuya_cfg['skill_name']}** (Stun Boss 1 lần trong trận, 30% mỗi hiệp)"
        ),
        inline=False
    )
    embed.set_footer(text="Bấm nút chọn hoặc dùng /evol kèm ID nhân vật!")

    view = EvolSelectView(player, user.id)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="evol", description="Tiến hóa nhân vật Touhou lên Ace 2 (Kèm ID nhân vật: 13: Reimu, 16: Sakuya)")
@app_commands.describe(id_hoac_ten="Nhập số ID thẻ (13 hoặc 16) hoặc chọn nhân vật")
@app_commands.choices(id_hoac_ten=[
    app_commands.Choice(name="[#13] Reimu Hakurei (Ace 2 - Cần 20 thẻ)", value="13"),
    app_commands.Choice(name="[#16] Sakuya Izayoi (Ace 2 - Cần 30 thẻ)", value="16")
])
async def slash_evol(interaction: discord.Interaction, id_hoac_ten: str = None):
    await handle_evol(interaction, id_hoac_ten)

@bot.command(name="evol", aliases=["tienhoa", "ace2"])
async def prefix_evol(ctx, id_hoac_ten: str = None):
    await handle_evol(ctx, id_hoac_ten)

# ==============================================================================
# 11. CÁC LỆNH GAME: PULL, DAILY, TEAM, BATTLE, COLLECTION, BOSS STATUS, HELP
# ==============================================================================
async def handle_pull(ctx_or_interaction, count: int = 1):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    count = max(1, min(10, count))
    total_avail = player.get("free_pulls_remaining", 0) + int(player.get("pull_tickets", 0))

    if total_avail < count:
        msg = f"❌ Bạn không đủ lượt quay! (Có: {player.get('free_pulls_remaining', 0)} free + {player.get('pull_tickets', 0):.1f} vé, cần: {count}). Dùng `/daily` hoặc tham gia Raid để nhận thêm vé!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    needed = count
    free_used = min(player["free_pulls_remaining"], needed)
    player["free_pulls_remaining"] -= free_used
    needed -= free_used
    player["pull_tickets"] -= float(needed)

    results = []
    card = None
    for _ in range(count):
        card, is_dup, conv = execute_single_pull(player)
        dup_text = f" *(Trùng! +{conv:.2f} vé pull)*" if is_dup else " ✨ **[MỚI]**"
        results.append(f"• `[#{card['id']:02d}]` **[{card['rank']}] {card['name']}** (⚔️{card['power']} | ❤️{card['hp']}){dup_text}")

    save_player(player)
    embed = discord.Embed(
        title=f"🌸 KẾT QUẢ PULL THẺ GACHA ({count} LƯỢT)",
        description="\n".join(results),
        color=0xDC2626 if any(c.startswith("• `[#") and "[SS]" in c for c in results) else 0x3B82F6
    )
    if card:
        embed.set_thumbnail(url=card["image"])
    embed.set_footer(text=f"Vé pull còn lại: {player['pull_tickets']:.2f} | Free hôm nay: {player['free_pulls_remaining']}/5")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="pull", description="Quay thẻ nhân vật Touhou (Free 5 lượt/ngày)")
@app_commands.describe(so_luong="Số lượt quay (1 đến 10, mặc định: 1)")
async def slash_pull(interaction: discord.Interaction, so_luong: int = 1):
    await handle_pull(interaction, so_luong)

@bot.command(name="pull")
async def prefix_pull(ctx, count: int = 1):
    await handle_pull(ctx, count)

async def handle_daily(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    today = datetime.now().strftime("%Y-%m-%d")

    if player.get("last_daily_date") == today:
        msg = "⛩️ Hôm nay bạn đã nhận vé Daily rồi! Hãy quay lại vào ngày mai nhé!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    player["last_daily_date"] = today
    player["pull_tickets"] += 1.0
    save_player(player)
    embed = discord.Embed(
        title="🎁 ĐIỂM DANH HÀNG NGÀY / DAILY REWARD",
        description=f"Chúc mừng **{user.display_name}** đã viếng đền Hakurei!\nBạn nhận được: **+1 Lượt Pull** 🎟️\nTổng vé pull hiện có: **{player['pull_tickets']:.2f}**",
        color=0xF59E0B
    )
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="daily", description="Nhận 1 lượt pull miễn phí mỗi ngày")
async def slash_daily(interaction: discord.Interaction):
    await handle_daily(interaction)

@bot.command(name="daily")
async def prefix_daily(ctx):
    await handle_daily(ctx)

async def handle_team(ctx_or_interaction, action: str = "view", card_id: int = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    cur_lvl, xp_in_lvl, needed_xp, ratio = get_level_progress(player.get("xp", 0))
    lvl_buff = (cur_lvl - 1) * 10
    act = action.lower().strip() if action else "view"

    if act == "add":
        if not card_id or card_id not in CARDS_DATA:
            msg = f"❌ Vui lòng nhập số ID thẻ hợp lệ (1-{len(CARDS_DATA)})!"
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        cid_str = str(card_id)
        if player["inventory"].get(cid_str, 0) < 1:
            msg = f"⚠️ Bạn chưa sở hữu thẻ #{card_id:02d} {CARDS_DATA[card_id]['name']}!"
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        if card_id in player["team"]:
            msg = f"⚠️ Thẻ #{card_id:02d} đã có sẵn trong đội hình rồi!"
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        if len(player["team"]) >= 3:
            msg = "⚠️ Đội hình đã đủ 3 thẻ! Hãy gỡ bớt thẻ trước bằng `/team remove`."
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        player["team"].append(card_id)
        save_player(player)
        card = CARDS_DATA[card_id]
        is_ace = is_card_ace2(player, card_id)
        ace_pwr = ACE_POWER_BUFF if is_ace else 0
        ace_hp = ACE_HP_BUFF if is_ace else 0
        msg = f"✅ Đã thêm **#{card['id']:02d} [{card['rank']}] {card['name']}** vào đội hình! (Lực chiến: ⚔️{card['power'] + lvl_buff + ace_pwr:,} | ❤️{card['hp'] + lvl_buff + ace_hp:,})"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg)
        else: await ctx_or_interaction.send(msg)
        return

    elif act == "remove":
        if not card_id or card_id not in player["team"]:
            msg = "⚠️ Vui lòng nhập ID thẻ đang có trong đội hình để gỡ!"
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return
        player["team"].remove(card_id)
        save_player(player)
        msg = f"🗑️ Đã gỡ thành công thẻ #{card_id:02d} khỏi đội hình!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg)
        else: await ctx_or_interaction.send(msg)
        return

    # View team
    filled_bars = int(ratio * 10)
    bar_str = "▰" * filled_bars + "▱" * (10 - filled_bars)
    embed = discord.Embed(title=f"🛡️ ĐỘI HÌNH CHIẾN ĐẤU - {user.display_name.upper()}", color=0x3B82F6)
    embed.add_field(
        name=f"⭐ CẤP ĐỘ: Lv.{cur_lvl}",
        value=f"• **Tiến trình:** `{bar_str}` **{xp_in_lvl}/{needed_xp} XP** (Cần {needed_xp - xp_in_lvl} XP để lên Lv.{cur_lvl + 1})\n• **Buff Lv.{cur_lvl}:** +{lvl_buff} Power & +{lvl_buff} HP",
        inline=False
    )
    if not player["team"]:
        embed.add_field(name="📋 Trạng Thái Đội Hình (0/3):", value="Đội hình đang trống! Dùng `/team add id_the:<ID>` để thêm thẻ.", inline=False)
    else:
        tot_pwr, tot_hp = 0, 0
        for idx in range(1, 4):
            if idx <= len(player["team"]):
                cid = player["team"][idx - 1]
                c = CARDS_DATA[cid]
                is_ace = is_card_ace2(player, cid)
                ace_pwr = ACE_POWER_BUFF if is_ace else 0
                ace_hp = ACE_HP_BUFF if is_ace else 0
                pwr = c["power"] + lvl_buff + ace_pwr
                hp = c["hp"] + lvl_buff + ace_hp
                tot_pwr += pwr
                tot_hp += hp
                ace_tag = " ⭐ [Ace 2: +100 ATK, +250 HP]" if is_ace else ""
                embed.add_field(name=f"Vị trí #{idx}: [#{c['id']:02d}] [{c['rank']}] {c['name']}{ace_tag}", value=f"⚔️ Power: **{pwr:,}** | ❤️ HP: **{hp:,}**", inline=False)
            else:
                embed.add_field(name=f"Vị trí #{idx}: 🔲 [Trống]", value="Dùng `/team add` để xếp thêm thẻ.", inline=False)
        embed.add_field(name="📊 TỔNG LỰC CHIẾN:", value=f"⚔️ Tổng Power: **{tot_pwr:,}** | ❤️ Tổng HP: **{tot_hp:,}**", inline=False)
        embed.set_thumbnail(url=CARDS_DATA[player["team"][0]]["image"])

    embed.set_footer(text=f"Hakurei Shrine • Thắng {player.get('battles_won', 0)} trận")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="team", description="Quản lý đội hình 3 thẻ (view, add, remove)")
@app_commands.describe(hanh_dong="view (xem), add (thêm thẻ), remove (gỡ thẻ)", id_the="Số ID thẻ từ 1 đến 26")
@app_commands.choices(hanh_dong=[
    app_commands.Choice(name="👁️ Xem đội hình (view)", value="view"),
    app_commands.Choice(name="➕ Thêm thẻ (add)", value="add"),
    app_commands.Choice(name="➖ Gỡ thẻ (remove)", value="remove")
])
async def slash_team(interaction: discord.Interaction, hanh_dong: app_commands.Choice[str] = None, id_the: int = None):
    action = hanh_dong.value if hanh_dong else "view"
    await handle_team(interaction, action, id_the)

@bot.command(name="team")
async def prefix_team(ctx, action: str = "view", card_id: int = None):
    await handle_team(ctx, action, card_id)

async def handle_collection(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    owned = 0
    lines = []
    for cid in range(1, len(CARDS_DATA) + 1):
        card = CARDS_DATA[cid]
        cnt = player["inventory"].get(str(cid), 0)
        if cnt > 0:
            owned += 1
            is_ace = is_card_ace2(player, cid)
            ace_mark = " ⭐⭐ [Ace 2]" if is_ace else ""
            lines.append(f"✅ **#{card['id']:02d} [{card['rank']}] {card['name']}** ×{cnt}{ace_mark}")
        else:
            lines.append(f"🔒 `#{card['id']:02d}` [{card['rank']}] {card['name']} *(Chưa có)*")

    embed = discord.Embed(title=f"📖 BỘ SƯU TẬP THẺ TOUHOU ({owned}/{len(CARDS_DATA)})", description="\n".join(lines), color=0x8B5CF6)
    embed.set_footer(text="Quay thêm thẻ bằng lệnh /pull")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="collection", description="Kiểm tra bộ sưu tập 26 nhân vật Touhou đã sở hữu")
async def slash_collection(interaction: discord.Interaction):
    await handle_collection(interaction)

@bot.command(name="collection")
async def prefix_collection(ctx):
    await handle_collection(ctx)

GENSOKYO_NPCS = [
    {"name": "Cirno Đệ Nhất", "badge": "❄️ Băng Tinh", "preferred": [18, 19, 20]},
    {"name": "Marisa Đạo Tặc", "badge": "⭐ Tinh Linh", "preferred": [6, 13, 17]},
    {"name": "Alice Ma Đạo", "badge": "🪆 Búp Bê", "preferred": [12, 15, 21]},
    {"name": "Aya Phóng Viên", "badge": "🌪️ Phong Thần", "preferred": [13, 14, 16]},
    {"name": "Youmu Kiếm Hồn", "badge": "⚔️ Song Kiếm", "preferred": [8, 14, 15]},
    {"name": "Remilia Huyết Ma", "badge": "🦇 Huyết Tộc", "preferred": [3, 4, 10]},
    {"name": "Flandre Hủy Diệt", "badge": "💎 Hủy Diệt", "preferred": [3, 5, 9]},
    {"name": "Suika Quỷ Vương", "badge": "🍶 Đại Quỷ", "preferred": [5, 6, 9]},
    {"name": "Mokou Phượng Hoàng", "badge": "🔥 Bất Tử", "preferred": [6, 10, 13]},
    {"name": "Hecatia Hỗn Mang", "badge": "🌌 Hỗn Mang", "preferred": [1, 2, 4]}
]

async def handle_battle(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    if not player.get("team"):
        msg = "⚠️ Đội hình của bạn đang trống! Dùng `/team add id_the:<ID>` để xếp thẻ."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    now = time.time()
    if now - player.get("last_battle_time", 0) < 120:
        rem = int(120 - (now - player.get("last_battle_time", 0)))
        msg = f"⏳ Bạn vừa chiến đấu kịch liệt, cần nghỉ ngơi thêm **{rem // 60}m {rem % 60}s**!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    npc = random.choice(GENSOKYO_NPCS)
    opp_name = f"{npc['badge']} {npc['name']}"
    opp_level = max(1, min(MAX_LEVEL, player["level"] + random.choice([-1, 0, 1, 2])))
    opp_team_ids = npc.get("preferred", [17, 18, 20])

    p_buff = (player["level"] - 1) * 10
    o_buff = (opp_level - 1) * 10

    player_cards = []
    for cid in player["team"][:3]:
        c = CARDS_DATA.get(cid)
        if c:
            is_ace = is_card_ace2(player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            cname = f"[Ace 2] #{c['id']:02d} {c['name']}" if is_ace else f"#{c['id']:02d} {c['name']}"
            player_cards.append({
                "cid": cid, "name": cname, "power": c["power"] + p_buff + ace_pwr,
                "hp": c["hp"] + p_buff + ace_hp, "current_hp": c["hp"] + p_buff + ace_hp, "is_ace2": is_ace
            })

    opp_cards = []
    for cid in opp_team_ids[:3]:
        c = CARDS_DATA.get(cid)
        if c:
            opp_cards.append({"cid": cid, "name": f"#{c['id']:02d} {c['name']}", "power": c["power"] + o_buff, "hp": c["hp"] + o_buff, "current_hp": c["hp"] + o_buff})

    p_idx, o_idx, r_cnt = 0, 0, 0
    p_sakuya, p_reimu = False, False
    battle_logs = []
    battle_turns = []

    while p_idx < len(player_cards) and o_idx < len(opp_cards) and r_cnt < 30:
        r_cnt += 1
        pc = player_cards[p_idx]
        oc = opp_cards[o_idx]
        turn_image = None
        turn_actions = []
        turn_trades = []
        stunned = False

        if pc["cid"] == 16 and pc["is_ace2"] and not p_sakuya:
            if random.random() < 0.30:
                p_sakuya = True
                stunned = True
                turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#16] Sakuya** kích hoạt **Thời Gian Đóng Băng**! ❄️ {oc['name']} bị STUN mất lượt!"
                battle_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        oc["current_hp"] -= pc["power"]
        turn_actions.append(f"⚔️ **{pc['name']}** tấn công gây **{pc['power']:,} DMG** lên **{oc['name']}**!")

        if not stunned:
            invul = False
            if pc["cid"] == 13 and pc["is_ace2"] and not p_reimu:
                if random.random() < 0.30:
                    p_reimu = True
                    invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    msg_skill = f"🛡️ **[Ace 2] [#13] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN TOÀN BỘ THƯƠNG TỔN!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)
            if not invul:
                pc["current_hp"] -= oc["power"]
                turn_actions.append(f"⚔️ **{oc['name']}** phản công gây **{oc['power']:,} DMG** lên **{pc['name']}**!")
            else:
                turn_actions.append(f"🛡️ **{pc['name']}** miễn nhiễm toàn bộ đòn đánh của **{oc['name']}**!")
        else:
            turn_actions.append(f"❄️ **{oc['name']}** bị đóng băng nên không thể phản công!")

        # Cơ chế đổi sát thương trước khi tử trận (Last Stand Trade)
        if pc["current_hp"] <= 0:
            pc["current_hp"] = 0
            trade_dmg = pc["power"]
            oc["current_hp"] = max(0, oc["current_hp"] - trade_dmg)
            turn_trades.append(f"💥 **[ĐỔI SÁT THƯƠNG]** **{pc['name']}** trước khi gục ngã đã kịp thời đổi **{trade_dmg:,} DMG** vào **{oc['name']}**!")

        if oc["current_hp"] <= 0:
            oc["current_hp"] = 0
            trade_dmg = oc["power"]
            pc["current_hp"] = max(0, pc["current_hp"] - trade_dmg)
            turn_trades.append(f"💥 **[ĐỔI SÁT THƯƠNG]** **{oc['name']}** trước khi gục ngã đã kịp thời đổi **{trade_dmg:,} DMG** vào **{pc['name']}**!")

        push_msg = []
        if pc["current_hp"] <= 0:
            p_idx += 1
            if p_idx < len(player_cards):
                push_msg.append(f"💀 **{pc['name']}** gục! ➡️ Đẩy **{player_cards[p_idx]['name']}** lên tiền tuyến!")
                battle_logs.append(push_msg[-1])
            else:
                push_msg.append(f"☠️ Toàn bộ thẻ bài của **{user.display_name}** đã bị tiêu diệt!")
        if oc["current_hp"] <= 0:
            o_idx += 1
            if o_idx < len(opp_cards):
                push_msg.append(f"💥 Hạ gục **{oc['name']}**! ➡️ Đối thủ đưa **{opp_cards[o_idx]['name']}** lên nghênh chiến!")
                battle_logs.append(push_msg[-1])
            else:
                push_msg.append(f"🏆 Toàn bộ thẻ bài của đối thủ đã bị quét sạch!")

        battle_turns.append({
            "round": r_cnt,
            "title": f"Hiệp {r_cnt}: {pc['name']} VS {oc['name']}",
            "short_label": f"Hiệp {r_cnt}",
            "short_desc": f"{pc['name']} vs {oc['name']}",
            "desc": f"🔴 **{user.display_name}:** {pc['name']} (❤️ {max(0, pc['current_hp']):,} HP)\n🔵 **{opp_name}:** {oc['name']} (❤️ {max(0, oc['current_hp']):,} HP)",
            "color": 0x10B981 if (oc['current_hp'] <= 0 and pc['current_hp'] > 0) else 0x3B82F6,
            "image": turn_image,
            "fields": [
                ("⚡ Diễn Biến Giao Tranh:", "\n".join(turn_actions), False),
                *([("💥 Đổi Sát Thương Trước Khi Chết:", "\n".join(turn_trades), False)] if turn_trades else []),
                *([("🔄 Thay Đổi Tiền Tuyến:", "\n".join(push_msg), False)] if push_msg else []),
                ("👥 Quân Số Còn Lại:", f"• {user.display_name}: Còn {max(0, len(player_cards) - p_idx)} thẻ\n• {opp_name}: Còn {max(0, len(opp_cards) - o_idx)} thẻ", False)
            ]
        })

    win = (o_idx >= len(opp_cards))
    gained_xp = random.randint(50, 100)
    old_lvl = player["level"]
    player["last_battle_time"] = now
    player["xp"] += gained_xp
    player["battles_total"] = player.get("battles_total", 0) + 1
    if win: player["battles_won"] = player.get("battles_won", 0) + 1
    save_player(player)

    new_lvl = player["level"]
    lvl_up_str = f"\n🎉 **LÊN CẤP {new_lvl}!** (+10 Power & HP)" if new_lvl > old_lvl else ""
    embed = discord.Embed(title=f"⚔️ BATTLE ({r_cnt} HIỆP): {user.display_name} VS {opp_name}", color=0x10B981 if win else 0xEF4444)
    if battle_logs: embed.add_field(name="📜 Diễn Biến:", value="\n".join(battle_logs[:5]), inline=False)
    cur_lvl, xp_in_lvl, needed_xp, _ = get_level_progress(player["xp"])
    embed.add_field(
        name="Kết Quả:",
        value=f"{'🏆 **CHIẾN THẮNG!**' if win else '💀 **THẤT BẠI!**'}\nNhận: **+{gained_xp} XP** (Tổng: {player['xp']:,} XP | Cấp: Lv.{cur_lvl}: {xp_in_lvl}/{needed_xp} XP){lvl_up_str}",
        inline=False
    )
    embed.set_footer(text="Hồi chiêu lệnh: 2 phút • Bấm nút bên dưới để xem chi tiết từng hiệp kèm GIF")
    details_view = OpenDetailsView(battle_turns)
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed, view=details_view)
    else: await ctx_or_interaction.send(embed=embed, view=details_view)

@bot.tree.command(name="battle", description="Giao đấu theo lượt character-by-character nhận 50-100 XP")
async def slash_battle(interaction: discord.Interaction):
    await handle_battle(interaction)

@bot.command(name="battle")
async def prefix_battle(ctx):
    await handle_battle(ctx)

# ==============================================================================
# HỆ THỐNG ĐẠI CHIẾN PVP ĐỐI KHÁNG 3V3 (INTERACTIVE TURN-BY-TURN & GIF LOGS)
# ==============================================================================
class PvPChallengeView(discord.ui.View):
    def __init__(self, challenger, target, c_team, t_team):
        super().__init__(timeout=90)
        self.challenger = challenger
        self.target = target
        self.c_team = c_team
        self.t_team = t_team
        self.msg = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.msg:
            try:
                await self.msg.edit(content=f"⌛ Hết thời gian chờ! Lời thách đấu của {self.challenger.mention} tới {self.target.mention} đã hết hạn.", view=self)
            except Exception:
                pass

    @discord.ui.button(label="⚔️ Chấp Nhận Quyết Đấu", style=discord.ButtonStyle.danger, emoji="💥")
    async def accept_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Chỉ người được gửi chiến thư mới có quyền chấp nhận trận đấu!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🔥 **{self.target.mention} ĐÃ CHẤP NHẬN CHIẾN THƯ!** Trận đại chiến 3v3 bắt đầu...", view=self)
        self.stop()
        asyncio.create_task(run_pvp_match(interaction.channel, self.challenger, self.target, self.c_team, self.t_team))

    @discord.ui.button(label="🏳️ Từ Chối", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def decline_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.target.id, self.challenger.id]:
            await interaction.response.send_message("❌ Bạn không liên quan đến lời thách đấu này!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        if interaction.user.id == self.target.id:
            await interaction.response.edit_message(content=f"🏳️ **{self.target.mention}** đã từ chối lời thách đấu của **{self.challenger.mention}**.", view=self)
        else:
            await interaction.response.edit_message(content=f"🚫 **{self.challenger.mention}** đã hủy bỏ lời thách đấu.", view=self)
        self.stop()

async def run_pvp_match(channel, challenger, target, c_team_cids, t_team_cids):
    c_player = get_player(challenger.id, challenger.display_name)
    t_player = get_player(target.id, target.display_name)

    c_buff = (c_player["level"] - 1) * 10
    t_buff = (t_player["level"] - 1) * 10

    c_cards = []
    for cid in c_team_cids[:3]:
        c = CARDS_DATA.get(cid)
        if c:
            is_ace = is_card_ace2(c_player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            cname = f"[Ace 2 ⭐⭐] #{c['id']:02d} {c['name']}" if is_ace else f"#{c['id']:02d} {c['name']}"
            c_cards.append({
                "cid": cid, "name": cname, "power": c["power"] + c_buff + ace_pwr,
                "hp": c["hp"] + c_buff + ace_hp, "current_hp": c["hp"] + c_buff + ace_hp,
                "max_hp": c["hp"] + c_buff + ace_hp, "is_ace2": is_ace
            })

    t_cards = []
    for cid in t_team_cids[:3]:
        c = CARDS_DATA.get(cid)
        if c:
            is_ace = is_card_ace2(t_player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            cname = f"[Ace 2 ⭐⭐] #{c['id']:02d} {c['name']}" if is_ace else f"#{c['id']:02d} {c['name']}"
            t_cards.append({
                "cid": cid, "name": cname, "power": c["power"] + t_buff + ace_pwr,
                "hp": c["hp"] + t_buff + ace_hp, "current_hp": c["hp"] + t_buff + ace_hp,
                "max_hp": c["hp"] + t_buff + ace_hp, "is_ace2": is_ace
            })

    c_idx, t_idx, r_cnt = 0, 0, 0
    c_sakuya, c_reimu = False, False
    t_sakuya, t_reimu = False, False
    pvp_turns = []
    pvp_logs = []

    while c_idx < len(c_cards) and t_idx < len(t_cards) and r_cnt < 30:
        r_cnt += 1
        cc = c_cards[c_idx]
        tc = t_cards[t_idx]
        turn_image = None
        turn_actions = []
        turn_trades = []

        c_stunned = False
        t_stunned = False

        # Sakuya stun
        if cc["cid"] == 16 and cc["is_ace2"] and not c_sakuya:
            if random.random() < 0.30:
                c_sakuya = True
                t_stunned = True
                turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#16] Sakuya** ({challenger.display_name}) kích hoạt **Thời Gian Đóng Băng**! ❄️ {tc['name']} bị STUN!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if tc["cid"] == 16 and tc["is_ace2"] and not t_sakuya:
            if random.random() < 0.30:
                t_sakuya = True
                c_stunned = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#16] Sakuya** ({target.display_name}) kích hoạt **Thời Gian Đóng Băng**! ❄️ {cc['name']} bị STUN!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        # Reimu invul
        c_invul = False
        t_invul = False
        if cc["cid"] == 13 and cc["is_ace2"] and not c_reimu:
            if random.random() < 0.30:
                c_reimu = True
                c_invul = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_skill = f"🛡️ **[Ace 2] [#13] Reimu** ({challenger.display_name}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if tc["cid"] == 13 and tc["is_ace2"] and not t_reimu:
            if random.random() < 0.30:
                t_reimu = True
                t_invul = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_skill = f"🛡️ **[Ace 2] [#13] Reimu** ({target.display_name}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        # Giao tranh sát thương
        if not c_stunned and not t_invul:
            tc["current_hp"] -= cc["power"]
            turn_actions.append(f"⚔️ **{cc['name']}** giáng **{cc['power']:,} DMG** lên **{tc['name']}**!")
        elif c_stunned:
            turn_actions.append(f"❄️ **{cc['name']}** bị đóng băng không thể tấn công!")
        elif t_invul:
            turn_actions.append(f"🛡️ **{tc['name']}** miễn nhiễm toàn bộ đòn đánh!")

        if not t_stunned and not c_invul:
            cc["current_hp"] -= tc["power"]
            turn_actions.append(f"⚔️ **{tc['name']}** giáng **{tc['power']:,} DMG** lên **{cc['name']}**!")
        elif t_stunned:
            turn_actions.append(f"❄️ **{tc['name']}** bị đóng băng không thể tấn công!")
        elif c_invul:
            turn_actions.append(f"🛡️ **{cc['name']}** miễn nhiễm toàn bộ đòn đánh!")

        # Cơ chế đổi sát thương trước khi tử trận (Last Stand Trade)
        if cc["current_hp"] <= 0:
            cc["current_hp"] = 0
            trade_dmg = cc["power"]
            tc["current_hp"] = max(0, tc["current_hp"] - trade_dmg)
            turn_trades.append(f"💥 **[ĐỔI SÁT THƯƠNG]** **{cc['name']}** ({challenger.display_name}) trước khi gục đã kịp thời đổi **{trade_dmg:,} DMG** vào **{tc['name']}**!")

        if tc["current_hp"] <= 0:
            tc["current_hp"] = 0
            trade_dmg = tc["power"]
            cc["current_hp"] = max(0, cc["current_hp"] - trade_dmg)
            turn_trades.append(f"💥 **[ĐỔI SÁT THƯƠNG]** **{tc['name']}** ({target.display_name}) trước khi gục đã kịp thời đổi **{trade_dmg:,} DMG** vào **{cc['name']}**!")

        push_msg = []
        if cc["current_hp"] <= 0:
            c_idx += 1
            if c_idx < len(c_cards):
                push_msg.append(f"💀 **{cc['name']}** gục ngã! ➡️ {challenger.display_name} đưa **{c_cards[c_idx]['name']}** lên!")
                pvp_logs.append(push_msg[-1])
            else:
                push_msg.append(f"☠️ Toàn bộ thẻ bài của **{challenger.display_name}** đã bị tiêu diệt!")
        if tc["current_hp"] <= 0:
            t_idx += 1
            if t_idx < len(t_cards):
                push_msg.append(f"💀 **{tc['name']}** gục ngã! ➡️ {target.display_name} đưa **{t_cards[t_idx]['name']}** lên!")
                pvp_logs.append(push_msg[-1])
            else:
                push_msg.append(f"☠️ Toàn bộ thẻ bài của **{target.display_name}** đã bị tiêu diệt!")

        pvp_turns.append({
            "round": r_cnt,
            "title": f"PvP Hiệp {r_cnt}: {challenger.display_name} VS {target.display_name}",
            "short_label": f"Hiệp {r_cnt}",
            "short_desc": f"{cc['name']} vs {tc['name']}",
            "desc": (
                f"🔴 **{challenger.display_name}:** {cc['name']} (❤️ {max(0, cc['current_hp']):,} HP)\n"
                f"🔵 **{target.display_name}:** {tc['name']} (❤️ {max(0, tc['current_hp']):,} HP)"
            ),
            "color": 0xEF4444,
            "image": turn_image,
            "fields": [
                ("⚡ Diễn Biến Giao Tranh:", "\n".join(turn_actions), False),
                *([("💥 Đổi Sát Thương Trước Khi Chết:", "\n".join(turn_trades), False)] if turn_trades else []),
                *([("🔄 Thay Đổi Tiền Tuyến:", "\n".join(push_msg), False)] if push_msg else []),
                ("👥 Quân Số Còn Lại:", f"• {challenger.display_name}: Còn {max(0, len(c_cards) - c_idx)} thẻ\n• {target.display_name}: Còn {max(0, len(t_cards) - t_idx)} thẻ", False)
            ]
        })

    # Xác định người chiến thắng
    c_won = (t_idx >= len(t_cards) and c_idx < len(c_cards))
    t_won = (c_idx >= len(c_cards) and t_idx < len(t_cards))

    old_c_lvl = c_player["level"]
    old_t_lvl = t_player["level"]

    if c_won:
        winner_name = challenger.display_name
        c_player["xp"] += 100
        c_player["battles_won"] = c_player.get("battles_won", 0) + 1
        t_player["xp"] += 40
        result_desc = f"🏆 **{challenger.mention} ĐÃ GIÀNH CHIẾN THẮNG TUYỆT ĐỐI!**\n💀 {target.mention} đã thất thủ sau {r_cnt} hiệp đấu nghẹt thở."
    elif t_won:
        winner_name = target.display_name
        t_player["xp"] += 100
        t_player["battles_won"] = t_player.get("battles_won", 0) + 1
        c_player["xp"] += 40
        result_desc = f"🏆 **{target.mention} ĐÃ GIÀNH CHIẾN THẮNG TUYỆT ĐỐI!**\n💀 {challenger.mention} đã thất thủ sau {r_cnt} hiệp đấu nghẹt thở."
    else:
        winner_name = "Hòa"
        c_player["xp"] += 50
        t_player["xp"] += 50
        result_desc = f"⚖️ **KẾT QUẢ BẤT PHÂN THẮNG BẠI!**\nCả 2 bên đều chiến đấu anh dũng đến lá bài cuối cùng sau {r_cnt} hiệp."

    c_player["battles_total"] = c_player.get("battles_total", 0) + 1
    t_player["battles_total"] = t_player.get("battles_total", 0) + 1
    save_player(c_player)
    save_player(t_player)

    embed = discord.Embed(
        title=f"⚔️ KẾT QUẢ ĐẠI CHIẾN PVP ({r_cnt} HIỆP): {challenger.display_name} VS {target.display_name}",
        description=result_desc,
        color=0xF59E0B if winner_name == "Hòa" else 0x10B981
    )
    if pvp_logs:
        embed.add_field(name="📜 Điểm Nhấn Trận Đấu:", value="\n".join(pvp_logs[:5]), inline=False)

    c_lvl_str = f" 🎉 *(Lên Lv.{c_player['level']}!)*" if c_player['level'] > old_c_lvl else ""
    t_lvl_str = f" 🎉 *(Lên Lv.{t_player['level']}!)*" if t_player['level'] > old_t_lvl else ""

    embed.add_field(
        name="🎁 Phần Thưởng Kinh Nghiệm (XP):",
        value=(
            f"• **{challenger.display_name}**: +{'100' if c_won else ('50' if not t_won else '40')} XP "
            f"(Tổng: {c_player['xp']:,} XP | Cấp {c_player['level']}){c_lvl_str}\n"
            f"• **{target.display_name}**: +{'100' if t_won else ('50' if not c_won else '40')} XP "
            f"(Tổng: {t_player['xp']:,} XP | Cấp {t_player['level']}){t_lvl_str}"
        ),
        inline=False
    )
    embed.set_footer(text="Bấm 'Xem Chi Tiết Trận Chiến & GIF Kỹ Năng' bên dưới để xem lại từng hiệp đấu kèm GIF hoạt ảnh trực tiếp!")

    await channel.send(embed=embed, view=OpenDetailsView(pvp_turns))

async def handle_pvp(ctx_or_interaction, target: discord.Member):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    if not target:
        msg = "⚠️ Vui lòng tag hoặc chọn người chơi bạn muốn thách đấu! Ví dụ: `/pvp target:@User` hoặc `!pvp @User`"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if target.bot:
        msg = "🤖 Không thể thách đấu Bot! Bạn chỉ có thể thách đấu người chơi thực tế."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if target.id == user.id:
        msg = "🤡 Bạn không thể tự thách đấu chính mình!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    c_player = get_player(user.id, user.display_name)
    t_player = get_player(target.id, target.display_name)

    def get_effective_team(p):
        team = [cid for cid in p.get("team", []) if cid in CARDS_DATA]
        if len(team) < 3:
            owned_ids = [int(cid) for cid, cnt in p.get("inventory", {}).items() if cnt > 0 and int(cid) in CARDS_DATA]
            owned_ids.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
            for cid in owned_ids:
                if cid not in team:
                    team.append(cid)
                if len(team) >= 3:
                    break
        return team

    c_team = get_effective_team(c_player)
    t_team = get_effective_team(t_player)

    if not c_team:
        msg = "⚠️ Bạn chưa sở hữu thẻ bài nào để tham chiến! Dùng `/pull` để tìm kiếm thẻ bài nhé."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if not t_team:
        msg = f"⚠️ Đối thủ {target.mention} hiện chưa sở hữu bất kỳ thẻ bài nào trong kho để tiếp nhận chiến thư!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    c_player["team"] = c_team
    save_player(c_player)
    t_player["team"] = t_team
    save_player(t_player)

    embed_challenge = discord.Embed(
        title="⚔️ CHIẾN THƯ THÁCH ĐẤU PVP ĐỈNH CAO (3V3)",
        description=f"🔥 **{user.mention}** đã gửi chiến thư thách đấu đối kháng 3v3 tới **{target.mention}**!\n\nNhấn nút **Chấp Nhận Quyết Đấu** bên dưới để khai màn trận đấu!",
        color=0xEF4444
    )
    embed_challenge.set_thumbnail(url=user.display_avatar.url if hasattr(user, 'display_avatar') else "")

    c_cards_str = "\n".join([f"• #{cid:02d} {CARDS_DATA[cid]['name']} ({CARDS_DATA[cid]['rank']}) - {CARDS_DATA[cid]['power']:,} ATK" for cid in c_team])
    t_cards_str = "\n".join([f"• #{cid:02d} {CARDS_DATA[cid]['name']} ({CARDS_DATA[cid]['rank']}) - {CARDS_DATA[cid]['power']:,} ATK" for cid in t_team])

    embed_challenge.add_field(name=f"🔴 Đội Hình {user.display_name} (Lv.{c_player['level']}):", value=c_cards_str, inline=True)
    embed_challenge.add_field(name=f"🔵 Đội Hình {target.display_name} (Lv.{t_player['level']}):", value=t_cards_str, inline=True)
    embed_challenge.add_field(
        name="📜 Quy Tắc Quyết Đấu:",
        value="• Đấu lần lượt 3 thẻ bài (tự động cộng chỉ số theo Cấp & Thức tỉnh Ace 2).\n• Kỹ năng Ace 2: Sakuya đóng băng, Reimu vô tưởng chuyển sinh (hiện GIF trực tiếp).\n• Thẻ bài trước khi gục ngã đều đổi toàn bộ sát thương lên đối thủ!\n• Sau trận có mục **Xem Chi Tiết Trận Chiến** để xem lại từng hiệp kèm GIF.",
        inline=False
    )
    embed_challenge.set_footer(text="Thời gian chờ chấp nhận: 90 giây")

    challenge_view = PvPChallengeView(user, target, c_team, t_team)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(content=target.mention, embed=embed_challenge, view=challenge_view)
        challenge_view.msg = await ctx_or_interaction.original_response()
    else:
        challenge_view.msg = await ctx_or_interaction.send(content=target.mention, embed=embed_challenge, view=challenge_view)

@bot.tree.command(name="pvp", description="Thách đấu người chơi khác trong server trận đại chiến 3v3")
@app_commands.describe(target="Chọn người chơi bạn muốn thách đấu")
async def slash_pvp(interaction: discord.Interaction, target: discord.Member):
    await handle_pvp(interaction, target)

@bot.command(name="pvp")
async def prefix_pvp(ctx, target: discord.Member = None):
    await handle_pvp(ctx, target)

@bot.tree.command(name="boss_status", description="Kiểm tra trạng thái và thời gian hồi chiêu của Boss Raid")
async def slash_boss_status(interaction: discord.Interaction):
    global boss_cooldown_until, active_raid
    now = time.time()
    embed = discord.Embed(title="👹 TRẠNG THÁI BOSS RAID: REIMU DỊ HÌNH (2 PHASE)", color=0xDC2626)
    embed.set_thumbnail(url=BOSS_CONFIG["image"])
    embed.add_field(name="❤️ Chỉ Số 2 Phase:", value=f"• Phase 1: HP {BOSS_CONFIG['hp']:,} | Đánh thường {BOSS_CONFIG['power']:,} DMG (chia đều)\n• Phase 2: HP {BOSS_PHASE2_CONFIG['hp']:,} | Đánh thường {BOSS_PHASE2_CONFIG['power']:,} DMG (chia đều)", inline=True)
    embed.add_field(name="🎁 Phần Thưởng:", value="100% Quy đổi thành Vé Pull tích lũy!", inline=True)
    if active_raid:
        embed.add_field(name="🔥 Tình Trạng:", value=f"**ĐANG XUẤT HIỆN!** Có {len(active_raid.get('participants', []))}/{BOSS_CONFIG['max_players']} dũng giả!", inline=False)
    elif now < boss_cooldown_until:
        rem = int(boss_cooldown_until - now)
        embed.add_field(name="⏳ Hồi Chiêu:", value=f"Cần đợi thêm **{rem // 60} phút {rem % 60} giây** nữa!", inline=False)
    else:
        embed.add_field(name="🟢 Sẵn Sàng:", value="Boss đã sẵn sàng xuất hiện ngẫu nhiên (10% khi chat)!", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.command(name="boss", aliases=["bossstatus"])
async def prefix_boss_status(ctx):
    global boss_cooldown_until, active_raid
    now = time.time()
    if active_raid: await ctx.send("🚨 Boss Raid ĐANG XUẤT HIỆN! Hãy tham gia ngay!")
    elif now < boss_cooldown_until:
        rem = int(boss_cooldown_until - now)
        await ctx.send(f"⏳ Boss đang hồi chiêu 15 phút (Còn lại: {rem // 60}m {rem % 60}s).")
    else: await ctx.send("🟢 Boss đã sẵn sàng xuất hiện (10% cơ hội khi chat)!")

async def handle_help(ctx_or_interaction):
    desc = """
⛩️ **HAKUREI REIMU DISCORD BOT - BẢN ĐỒ LỆNH**

**🎮 GACHA & BATTLE:**
• `/pull [số_lượng]`: Quay thẻ Touhou (Free 5 lượt/ngày).
• `/daily`: Điểm danh nhận 1 vé pull mỗi ngày.
• `/evol [id_hoac_ten]`: Tiến hóa [#13] Reimu (20 thẻ) & [#16] Sakuya (30 thẻ) lên Ace 2 ⭐⭐ (Buff +100 ATK, +250 HP, hoạt ảnh GIF trực tiếp).
• `/team [hanh_dong] [id_the]`: Quản lý đội hình (view, add, remove).
• `/collection`: Xem 26 nhân vật Touhou (SS, S, A, B, C).
• `/battle`: Giao đấu nhân vật nhận 50-100 XP (hồi chiêu 2p).
• `/pvp <người_chơi>`: Thách đấu người chơi khác trong server trận đại chiến 3v3 đỉnh cao.
• `/boss_status`: Kiểm tra hồi chiêu 15 phút của Boss Raid.
• **Thông tin chi tiết trận chiến**: Sau Battle, Raid và PvP luôn có nút **📜 Xem Chi Tiết Trận Chiến & GIF Kỹ Năng** để xem lại từng hiệp kèm GIF hoạt ảnh trực tiếp (không dùng link dẫn ra ngoài).

**👹 DỊ BIẾN REIMU DỊ HÌNH (LIVE COMBAT):**
• **Phase 1 (35k HP / 15k DMG):** Nhận 3 quà vé pull. Trận đấu phát sóng turn-by-turn trực tiếp!
• **Phase 2 Thức Tỉnh (50k HP / 22k DMG):** Tự động hồi sinh & hồi 100% HP mọi thẻ bài! Quà siêu cấp: 3-10 vé!

**👑 LỆNH ADMIN (OWNER EXCLUSIVE - ID: 1502579398560317441):**
• `/admin_set_level <user> <level>`: Đặt cấp độ và đồng bộ XP (+50 XP/cấp chuẩn xác).
• `/admin_confiscate <user> [id_the] [so_luong]`: Tước đoạt bài trừng phạt cheat (0 = tất cả).
• `/admin_add_card <id_the> [so_luong] [user]`: Cấp thẻ cho người chơi / tự lấy thẻ.
• `/sync`: Đồng bộ lại cây lệnh Slash Commands.
"""
    embed = discord.Embed(title="🌸 HƯỚNG DẪN LỆNH BOT REIMU", description=desc, color=0xDC2626)
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="help", description="Xem hướng dẫn toàn bộ lệnh chơi game, boss raid và lệnh admin")
async def slash_help(interaction: discord.Interaction):
    await handle_help(interaction)

@bot.command(name="help")
async def prefix_help(ctx):
    await handle_help(ctx)

@bot.tree.command(name="wiki", description="Tra cứu nhân vật Touhou")
@app_commands.describe(nhan_vat="Tên nhân vật Touhou")
async def touhou_wiki(interaction: discord.Interaction, nhan_vat: str):
    await interaction.response.defer()
    prompt = f"Tra cứu Touhou Project cho: '{nhan_vat}'. Tóm tắt danh hiệu, năng lực và lời bình đanh đá của Reimu."
    try:
        wiki_text = await ask_gemini(prompt, REIMU_SYSTEM_PROMPT, 0.7)
        embed = discord.Embed(title=f"🌸 Bách Khoa Gensokyo: {nhan_vat}", description=wiki_text[:4000], color=0xDC2626)
        await interaction.followup.send(embed=embed)
    except Exception:
        await interaction.followup.send("⛩️ Hòm công đức đông khách, bùa chú đang quá tải!")

@bot.tree.command(name="clearmem", description="Xóa sạch ký ức trò chuyện với Reimu trong kênh này")
async def slash_clear_memory(interaction: discord.Interaction):
    reset_memory(interaction.channel_id, interaction.user.id)
    embed = discord.Embed(title="🧹 Tẩy Não", description="Đã dọn dẹp và làm mới ký ức hội thoại!", color=0x10B981)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sync", description="[CHỦ BOT DUY NHẤT] Đồng bộ Slash Commands")
async def slash_sync_commands(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã đồng bộ {len(synced)} Slash Commands chuẩn!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi: {e}")

@bot.command(name="sync")
async def prefix_sync_commands(ctx):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Đã đồng bộ {len(synced)} lệnh Slash chuẩn!")
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {e}")

@bot.tree.command(name="dbcheck", description="Kiểm tra kết nối MongoDB Atlas")
async def slash_dbcheck(interaction: discord.Interaction):
    await interaction.response.defer()
    connected, msg = test_and_connect_mongo()
    if connected and use_mongo:
        p_count = players_collection.count_documents({}) if players_collection is not None else 0
        embed = discord.Embed(title="☁️ DATABASE: MONGODB ATLAS", description=f"🟢 Kết nối ổn định! Tổng người chơi: **{p_count}**", color=0x10B981)
    else:
        embed = discord.Embed(title="🚨 CHƯA KẾT NỐI MONGODB ATLAS", description=f"⚠️ Đang dùng SQLite tạm thời.\n{mongo_error_detail}", color=0xEF4444)
    await interaction.followup.send(embed=embed)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN trong .env!", flush=True)
    else:
        bot.run(DISCORD_TOKEN)
