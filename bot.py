# ==============================================================================
# HAKUREI REIMU DISCORD BOT - FULL EDITION (UPDATED & SECURED)
# GEMINI FLASH CHATBOT + MONGODB ATLAS CLOUD + TOUHOU GACHA & AUTO-BATTLE & RAID
# ==============================================================================
# 1. BOSS STATS: Phase 1 (30k HP, 3k DMG) & Phase 2 Thức Tỉnh (50k HP, 10k DMG)
# 2. BOSS DROP: Rương chiến lợi phẩm quy đổi 100% thành Vé Pull
# 3. BOSS COOLDOWN: Hồi chiêu 15 phút tính từ lúc có bất kỳ ai tham gia raid
# 4. ADMIN COMMANDS: /admin_set_level, /admin_confiscate, /admin_add_card, /admin_lock (ID: 1502579398560317441)
# 5. LEVEL UP MỚI: Mỗi cấp tăng +50 XP (Lv.1: 100 XP, Lv.2: 150 XP, Lv.3: 200 XP...)
# 6. EVOL UPDATE:
#    - Luôn hiển thị ID nhân vật: [#13] Reimu Hakurei, [#16] Sakuya Izayoi
#    - Lệnh /evol hỗ trợ nhập trực tiếp ID hoặc tên
#    - Hoạt ảnh GIF hiển thị trực tiếp trong Discord (embed image & direct GIF)
#    - Buff tối thượng Ace: Mọi nhân vật đạt Ace đều được cộng +300 ATK (Power) và +300 Máu (HP)!
# 7. LIVE RAID COMBAT: Trận chiến chạy turn-by-turn theo thời gian thực để mọi người cùng theo dõi!
# 8. TÍNH NĂNG MỚI:
#    - Lệnh /admin_lock: Khóa thẻ của người chơi, gỡ khỏi team, chỉ mở khi pull trúng lại!
#    - Vá lỗi Tutorial: Tiến trình tuyến tính 1 chiều tuyệt đối, cờ vĩnh viễn chống farm 3 thẻ không trùng!
# ==============================================================================

import os
import re
import time
import json
import random
import asyncio
import threading
import sqlite3
from datetime import datetime, timezone, timedelta
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

def is_authorized_admin(user_or_id) -> bool:
    try:
        if isinstance(user_or_id, (int, str)):
            return int(user_or_id) == AUTHORIZED_ADMIN_ID
        uid = getattr(user_or_id, "id", None)
        if uid and int(uid) == AUTHORIZED_ADMIN_ID:
            return True
        guild_perms = getattr(user_or_id, "guild_permissions", None)
        if guild_perms and (guild_perms.administrator or guild_perms.manage_guild):
            return True
        guild = getattr(user_or_id, "guild", None)
        if guild and getattr(guild, "owner_id", None) == uid:
            return True
        return False
    except (ValueError, TypeError, Exception):
        return False

# ==============================================================================
# HỆ THỐNG MÚI GIỜ & TỰ ĐỘNG RESET 00:00 NỬA ĐÊM (GMT+7 / VIỆT NAM)
# ==============================================================================
VN_TZ = timezone(timedelta(hours=7))

def get_today_vn() -> str:
    """Trả về ngày hiện tại theo múi giờ Việt Nam (GMT+7) định dạng YYYY-MM-DD."""
    return datetime.now(VN_TZ).strftime("%Y-%m-%d")

def get_seconds_until_midnight_vn() -> int:
    """Tính số giây còn lại cho tới 00:00 (nửa đêm) ngày tiếp theo theo giờ Việt Nam."""
    now = datetime.now(VN_TZ)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(0, int((tomorrow - now).total_seconds()))

def format_time_until_midnight_vn() -> str:
    """Định dạng thời gian đếm ngược tới lần tự động làm mới tiếp theo (ví dụ: '5h 24m')."""
    total_seconds = get_seconds_until_midnight_vn()
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours} giờ {minutes:02d} phút"

# ==============================================================================
# BUFF CHỈ SỐ ACE (ÁP DỤNG CHO MỌI NHÂN VẬT TIẾN HÓA ACE) & BUFF CẤP ĐỘ MỚI
# ==============================================================================
ACE_POWER_BUFF = 300  # +300 ATK (Buff mới theo yêu cầu)
ACE_HP_BUFF = 300     # +300 Máu (Buff mới theo yêu cầu)

def get_level_atk_buff(level: int) -> int:
    return max(0, (level - 1) * 20)  # +20 ATK mỗi khi lên cấp

def get_level_hp_buff(level: int) -> int:
    return max(0, (level - 1) * 25)  # +25 HP mỗi khi lên cấp

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
# 3. TOUHOU CARDS DATABASE (26 NHÂN VẬT CHUẨN THÔNG SỐ + THẺ NHÓM T SEIKI)
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
    26: {"id": 26, "name": "Tewi Inaba", "rank": "C", "power": 150, "hp": 1500, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362906154410034/images.png?ex=6aaa6c26&is=6aa91aa6&hm=ac3b4dca861840ea6c0c5b41288fb528b56543df60081fe62ff774f75449e847&=&format=webp&quality=lossless"},
    "t1": {
        "id": "t1",
        "name": "Seiki đệ pháp toàn năng",
        "rank": "T",
        "power": 600,
        "hp": 6500,
        "image": "https://media.discordapp.net/attachments/1543072032034521228/1550428671284879470/content.png?ex=6aae4cb8&is=6aacfb38&hm=17b71e9140ae62c544872acbbfd654f97eaff639a2f40c400047e7cb786ec3a4&=&format=webp&quality=lossless&width=512&height=456",
        "skills": {
            "fantasy_seal": {
                "name": "Fantasy Seal",
                "chance": 0.40,
                "desc": "40% miễn thương 1 lần trong trận",
                "gif": "https://klipy.com/gifs/hakurei-reimu-touhou"
            },
            "master_spark": {
                "name": "Master Spark",
                "chance": 0.30,
                "multiplier": 1.5,
                "desc": "30% gây 1.5x sát thương 1 lần trong trận",
                "gif": "https://klipy.com/gifs/marisa-master-spark"
            },
            "medicine_sign": {
                "name": "Medicine Sign",
                "chance": 0.20,
                "desc": "20% hồi phục cho bản thân 1 lần trong trận",
                "gif": "https://klipy.com/gifs/shoko-ieiri-2"
            }
        }
    }
}
CARDS_DATA["T1"] = CARDS_DATA["t1"]

CARDS_BY_RANK = {
    "SS": [c for c in CARDS_DATA.values() if c["rank"] == "SS"],
    "S":  [c for c in CARDS_DATA.values() if c["rank"] == "S"],
    "A":  [c for c in CARDS_DATA.values() if c["rank"] == "A"],
    "B":  [c for c in CARDS_DATA.values() if c["rank"] == "B"],
    "C":  [c for c in CARDS_DATA.values() if c["rank"] == "C"],
    "T":  [c for c in CARDS_DATA.values() if c["rank"] == "T"],
}

# ==============================================================================
# BOSS REIMU DỊ HÌNH - CHỈ SỐ MỚI (PHASE 1: 30K HP, 3K DMG | PHASE 2: 50K HP, 10K DMG)
# ==============================================================================
BOSS_CONFIG = {
    "name": "Reimu Dị Hình - Phase 1",
    "desc": "Đó không phải Reimu, sẵn sàng giao chiến!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1549077421624401971/content.png?ex=6aa96245&is=6aa810c5&hm=c0248e497ee5afeed898b457736b39fc71368af3be1630f1cd59b5609c99fbeb&=&format=webp&quality=lossless&width=351&height=512",
    "hp": 30000,      # Phase 1: 30,000 HP
    "power": 3000,    # Phase 1: 3,000 DMG đánh thường chia đều
    "max_players": 6,
    "cooldown_seconds": 15 * 60  # 15 phút (900s)
}

BOSS_PHASE2_CONFIG = {
    "name": "Reimu Dị Hình - Thức Tỉnh (Phase 2)",
    "desc": "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội!",
    "image": "https://media.discordapp.net/attachments/1549063334781911070/1549275653239472148/artwork.png?ex=6aaa1ae3&is=6aa8c963&hm=7187404882d4b8b0fcef91ef64aee3c73711924e971fb7b28b6fb3bf394a47d3&=&format=webp&quality=lossless&width=640&height=336",
    "hp": 50000,      # Phase 2: 50,000 HP
    "power": 10000    # Phase 2: 10,000 DMG đánh thường chia đều
}

# ==============================================================================
# BOSS SEIKI DỊ HÌNH - DỊ TÀ ĐỆ NHẤT PHÁP SƯ (PHASE 1: 30K HP, 3K DMG, PASSIVE 1.5% HP)
# ==============================================================================
SEIKI_BOSS_CONFIG = {
    "id": "seiki",
    "name": "Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư",
    "desc": "Đó không phải cha ta!",
    "reimu_quote": "Đó không phải cha ta! Dị khí ngập tràn, người này đã bị tà niệm nuốt chửng!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1550376898641788938/content.png?ex=6aae1c81&is=6aaccb01&hm=d3c3c9d6c077931869c7f11e64fb4de796b79fecc3a9210008008fbc15a25e5f&=&format=webp&quality=lossless&width=643&height=1024",
    "hp": 30000,      # 30,000 HP
    "power": 3000,    # 3,000 DMG chia đều tiền tuyến
    "passive_regen_pct": 0.015,  # Hồi 1.5% HP tối đa mỗi lượt (450 HP)
    "max_players": 6,
    "cooldown_seconds": 15 * 60,
    "skills": {
        "multi_spark": {
            "name": "Multi Master Spark",
            "chance": 0.15,
            "multiplier": 1.5,
            "turns": 3,
            "desc": "15% kích hoạt, gây 1.5x sát thương trong 3 lượt (4,500 DMG chia đều tiền tuyến)!",
            "gif": "https://klipy.com/gifs/marisa-master-spark"
        },
        "fantasy_seal": {
            "name": "Fantasy Seal",
            "chance": 0.20,
            "desc": "20% kích hoạt kết giới phong ấn, MIỄN TOÀN BỘ SÁT THƯƠNG trong 1 turn!",
            "gif": "https://klipy.com/gifs/hakurei-reimu-touhou"
        },
        "blitz_attack": {
            "name": "Blitz Attack",
            "chance": 0.20,
            "damage": 4000,
            "desc": "20% gây 4,000 DMG diện rộng trực tiếp lên toàn bộ thẻ tiền tuyến!",
            "gif": "https://klipy.com/gifs/naoya-jujutsu-kaisen"
        }
    }
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
        "skill_desc": "Miễn toàn bộ sát thương duy nhất 1 lần trong trận (Tỷ lệ đồng nhất 40% mỗi hiệp khi nhận đòn cả trong Raid Boss và Battle/PvP, chỉ bảo vệ riêng Reimu).",
        "skill_gif": "https://c.tenor.com/gc4ws16CrTYAAAAC/reimu-touhou.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    16: {
        "id": 16,
        "key": "sakuya",
        "name": "Sakuya Izayoi",
        "title": "[#16] Sakuya Izayoi - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 30,
        "required_pulls": 30,
        "evol_gif": "https://static2.klipy.com/ii/d7aec6f6f171607374b2065c836f92f4/e8/09/O842rz9E.gif",
        "skill_name": "Thời Gian Đóng Băng (Stun Đối Thủ / Boss)",
        "skill_desc": "Khiến Boss/đối thủ bị đóng băng (Stun) mất lượt duy nhất 1 lần trong trận (Tỷ lệ đồng nhất 40% mỗi hiệp khi ở tiền tuyến cả trong Raid Boss và Battle/PvP).",
        "skill_gif": "https://c.tenor.com/0lC8dyA6_OwAAAAC/sakuya-izayoi-sakuya.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    17: {
        "id": 17,
        "key": "marisa",
        "name": "Marisa Kirisame",
        "title": "[#17] Marisa Kirisame - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 25,
        "required_pulls": 25,
        "evol_gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/de/e5/qY4XYpLV.gif",
        "skill_name": "Bát Quái Lô - Master Spark (Sát Thương ×1.5)",
        "skill_desc": "Kích hoạt 1 lần trong trận: 30% tung ra Master Spark với sát thương ×1.5 lần sát thương gốc!",
        "skill_gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/f4/32/73qv2IMW.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    }
}
EVOL_CONFIG["13"] = EVOL_CONFIG[13]
EVOL_CONFIG["16"] = EVOL_CONFIG[16]
EVOL_CONFIG["17"] = EVOL_CONFIG[17]

# ==============================================================================
# 3.1 CHI TIẾT NĂNG LỰC & KỸ NĂNG 26 NHÂN VẬT TOUHOU (CHO TÍNH NĂNG CHECK NHÂN VẬT)
# ==============================================================================
CHARACTER_DETAILS = {
    1: {"title": "Nữ Thần Địa Ngục Tam Thân", "skill_name": "Tam Giới Hỗn Mang", "skill_desc": "Nữ thần tự do sở hữu 3 thân xác (Trái Đất, Mặt Trăng, Địa Ngục). Sát thương và sinh lực áp đảo hàng đầu Gensokyo (850 ATK / 8,500 HP)."},
    2: {"title": "Hồn Tinh Khiết Căm Hờn", "skill_name": "Nguyên Lực Tinh Khiết", "skill_desc": "Thanh lọc mọi năng lượng về bản thể sơ khai nhất, giải phóng luồng đạn ma thuật thuần khiết hủy diệt vạn vật (800 ATK / 8,000 HP)."},
    3: {"title": "Bí Thần Tối Cao Gensokyo", "skill_name": "Hậu Môn Bí Cảnh", "skill_desc": "Mở những cánh cổng bí ẩn sau lưng vạn vật, thao túng năng lượng sinh mệnh và tinh thần để khống chế toàn cục (750 ATK / 7,500 HP)."},
    4: {"title": "Đại Yêu Quái Cảnh Giới", "skill_name": "Thao Túng Cảnh Giới", "skill_desc": "Kiểm soát ranh giới giữa thực và ảo, ánh sáng và bóng tối, biến mọi đòn công kích thành hư vô và mở kết giới phản đòn (720 ATK / 7,200 HP)."},
    5: {"title": "Đại Quỷ Núi Yêu Quái", "skill_name": "Đại Quỷ Thần Lực (Tụ Tán)", "skill_desc": "Thao túng mật độ không gian và vật chất, có thể phân tán thành làn sương hoặc tụ thành quỷ khổng lồ giáng đòn nghiền nát (670 ATK / 6,700 HP)."},
    6: {"title": "Dược Sư Nguyệt Đô", "skill_name": "Hourai Trường Sinh Dược", "skill_desc": "Bác sĩ thiên tài của Mặt Trăng, bậc thầy chế tạo mọi loại tiên dược Hourai và xạ kích tiễn thuật chuẩn xác (640 ATK / 6,600 HP)."},
    7: {"title": "Bạo Chúa Thái Dương Hoa", "skill_name": "Hồng Hoa Diệt Tuyệt", "skill_desc": "Yêu quái hoa lâu đời nhất Gensokyo, bắn ra những chùm tia Master Spark hồng hoa hủy diệt kẻ xâm phạm (630 ATK / 6,300 HP)."},
    8: {"title": "U Linh Bạch Ngọc Lâu", "skill_name": "Bướm Ma Dẫn Hồn", "skill_desc": "Công chúa u linh cai quản cõi chết, dẫn dụ linh hồn bước vào giấc ngủ vĩnh hằng bằng điệu múa bướm ma quái (620 ATK / 6,200 HP)."},
    9: {"title": "Ác Ma Cuồng Loạn", "skill_name": "Tuyệt Đối Phá Hủy (Kyū)", "skill_desc": "Bóp nát 'mục tiêu tồn tại' trong lòng bàn tay, giải phóng sức mạnh ma cà rồng hủy diệt không thể ngăn cản (610 ATK / 5,700 HP)."},
    10: {"title": "Công Chúa Ánh Trăng", "skill_name": "Vĩnh Cửu & Tức Thời", "skill_desc": "Công chúa Nguyệt Cung lưu đày tại Eientei, điều khiển dòng chảy thời gian vĩnh cửu và tức thời cùng thần bảo quý giá (590 ATK / 6,400 HP)."},
    11: {"title": "Chúa Tể Hồng Ma Quán", "skill_name": "Thương Đỏ Gungnir (Vận Mệnh)", "skill_desc": "Ma cà rồng kiêu hãnh bẻ cong số mệnh kẻ thù, phóng ra ngọn giáo ánh sáng đỏ Gungnir xuyên thủng phòng ngự (560 ATK / 5,600 HP)."},
    12: {"title": "Mặt Trời Địa Ngục", "skill_name": "Hạch Tâm Phản Ứng (Nuclear)", "skill_desc": "Mang sức mạnh thần mặt trời Yatagarasu, thi triển hạch tâm nhiệt hạch thiêu đốt toàn bộ chiến trường (550 ATK / 5,300 HP)."},
    13: {"title": "Vu Nữ Đền Hakurei", "skill_name": "Bùa Chú Vô Tưởng Chuyển Sinh", "skill_desc": "Bay lượn khỏi thực tại và trừ tà ma thuật. [Ace 2 ⭐⭐]: Miễn toàn bộ sát thương 1 lần trong trận (Tỷ lệ đồng nhất 40% cả trong Raid Boss và Battle/PvP)!"},
    14: {"title": "Phượng Hoàng Bất Tử", "skill_name": "Phượng Hoàng Bất Diệt", "skill_desc": "Cơ thể bất tử do uống tiên dược Hourai, triệu hồi ngọn lửa phượng hoàng thiêu đốt kẻ địch mà không hề sợ chết (490 ATK / 5,200 HP)."},
    15: {"title": "Tiên Nhân Một Tay", "skill_name": "Thần Thú Giáng Lâm", "skill_desc": "Một trong Tứ Thiên Vương ẩn mình dưới thân phận tiên nhân dạy dỗ yêu quái và điều khiển muôn loài linh thú (480 ATK / 4,900 HP)."},
    16: {"title": "Hầu Gái Trưởng Hoàn Hảo", "skill_name": "Thời Gian Đóng Băng", "skill_desc": "Bậc thầy phi dao bạc và không-thời gian. [Ace 2 ⭐⭐]: Đóng băng thời gian làm đối thủ/boss bị STUN mất lượt 1 lần trong trận (Tỷ lệ đồng nhất 40% cả trong Raid Boss và Battle/PvP)!"},
    17: {"title": "Phù Thủy Bình Thường", "skill_name": "Bát Quái Lô - Master Spark", "skill_desc": "Ma thuật ánh sáng và nhiệt độ cao. [Ace 2 ⭐⭐]: Bắn đại bác ma thuật Master Spark gây sát thương ×1.5 lần sát thương gốc (Tỷ lệ 30% 1 lần trong trận)!"},
    18: {"title": "Kiếm Sĩ Nửa Người Nửa Ma", "skill_name": "Song Kiếm Lâu Quan & Bạch Lâu", "skill_desc": "Thần tốc kiếm đạo: Lâu Quan Kiếm chém vạn vật và Bạch Lâu Kiếm chém tan ảo tưởng mê muội (410 ATK / 4,100 HP)."},
    19: {"title": "Thỏ Ngọc Chiến Binh", "skill_name": "Hồng Nhãn Cuồng Loạn", "skill_desc": "Thỏ ngọc từ Mặt Trăng phát sóng ảo giác từ ánh mắt đỏ rực làm hoa mắt và rối loạn phương hướng đối phương (390 ATK / 3,900 HP)."},
    20: {"title": "Đại Ma Đạo Sĩ Thất Diệu", "skill_name": "Thất Diệu Ma Thuật", "skill_desc": "Phù thủy thông thái trong thư viện ngầm, kết hợp 7 nguyên tố tự nhiên tạo thành ma trận công thủ liên hoàn (380 ATK / 3,200 HP)."},
    21: {"title": "Đệ Nhất Băng Tiên", "skill_name": "Perfect Freeze (Băng Đạn)", "skill_desc": "Tiên tử băng giá mạnh nhất Hồ Sương Mù, đóng băng mọi vật thể và phóng mưa mảnh băng sắc nhọn (300 ATK / 3,000 HP)."},
    22: {"title": "Thủ Môn Hồng Ma Quán", "skill_name": "Thái Cực Khí Công Quyền", "skill_desc": "Nữ võ sư tinh thông thể thuật khí công ngũ sắc, tạo rào chắn phòng thủ kiên cố bảo vệ tiền tuyến (260 ATK / 2,800 HP)."},
    23: {"title": "Yêu Quái Hoàng Hôn", "skill_name": "Dạ Tối Kết Giới", "skill_desc": "Yêu quái bóng đêm bao bọc mình trong vòm đêm thuần túy, tung những đòn cắn xé bất ngờ từ bóng tối (220 ATK / 2,200 HP)."},
    24: {"title": "Dạ Tước Huyễn Ca", "skill_name": "Huyễn Ca Dạ Manh", "skill_desc": "Giọng hát chim đêm mê hoặc khiến đối thủ bị chứng quáng gà và suy giảm độ chính xác đòn đánh (200 ATK / 2,000 HP)."},
    25: {"title": "Đom Đóm Phát Quang", "skill_name": "Đom Đóm Lôi Triệu", "skill_desc": "Điều khiển hàng triệu côn trùng dạ quang tạo nên biển ánh sáng mê ảo làm hoa mắt đối thủ (180 ATK / 1,800 HP)."},
    26: {"title": "Thỏ Rừng May Mắn", "skill_name": "Vận May Thần Tài", "skill_desc": "Thủ lĩnh thỏ rừng Inaba tinh nghịch, ban phát vận may cực lớn cho bản thân và đồng đội (150 ATK / 1,500 HP)."},
    "t1": {
        "title": "Dị Tà Đệ Nhất Pháp Sư (Nhóm T-Đặc Biệt)",
        "skill_name": "Tam Đại Tuyệt Kỹ (Fantasy Seal • Master Spark • Medicine Sign)",
        "skill_desc": "Thẻ bài thần thoại nhóm T. Sở hữu 3 tuyệt kỹ: Fantasy Seal (40% miễn thương 1 lần), Master Spark (30% x1.5 sát thương 1 lần), Medicine Sign (20% hồi phục 30% sinh lực bản thân 1 lần). Tuân thủ nghiêm ngặt nguyên tắc tối đa 1 chiêu mỗi lượt và mỗi chiêu kích hoạt 1 lần trong trận!"
    }
}
CHARACTER_DETAILS["T1"] = CHARACTER_DETAILS["t1"]

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
        "unlocked_cards": [],
        "locked_cards": [],  # DANH SÁCH THẺ BỊ ADMIN KHÓA (CHỈ MỞ KHI PULL LẠI)
        "evolutions": {},
        "team": [],
        "shards": {
            "seiki": 0  # KHO MẢNH ĐẶC BIỆT SEIKI (10 MẢNH = 1 THẺ SEIKI T1)
        },
        "language": "vi",
        "battles_won": 0,
        "battles_total": 0,
        "last_battle_time": 0.0,
        "recent_opponents": [],
        "tutorial": {
            "active": True,
            "step": "pull",
            "quest_pulls_remaining": 3,
            "pull_used": False,  # CỜ BẢO MẬT CHỐNG BUG FARM FULL S
            "completed": False
        },
        "daily_quests": {
            "date": "",
            "quests": [],
            "all_completed_claimed": False
        }
    }

# ==============================================================================
# HỆ THỐNG DAILY QUEST (3/3 NHIỆM VỤ MỖI NGÀY)
# ==============================================================================
DAILY_QUEST_POOL = [
    {
        "type": "pull",
        "name": "Quay thẻ Touhou gacha",
        "targets": [10, 20],
        "reward_range": (2, 5)
    },
    {
        "type": "battle",
        "name": "Chiến đấu PvE Battle",
        "targets": [10, 15, 20],
        "reward_range": (2, 5)
    },
    {
        "type": "daily",
        "name": "Điểm danh hàng ngày (/daily)",
        "targets": [1],
        "reward_range": (1, 2)
    },
    {
        "type": "pvp",
        "name": "Thách đấu PvP đại chiến",
        "targets": [3, 4, 5],
        "reward_range": (2, 5)
    },
    {
        "type": "raid",
        "name": "Tham gia diệt Boss Reimu Dị Hình",
        "targets": [1, 2, 3],
        "reward_range": (5, 7)
    }
]

def ensure_daily_quests(player: dict, force_reset: bool = False) -> dict:
    today = get_today_vn()
    dq = player.get("daily_quests")
    # Tự động reset khi: chưa có quest, hoặc sang ngày mới (date != today), hoặc không đủ 3 quest, hoặc force_reset
    if force_reset or not dq or dq.get("date") != today or len(dq.get("quests", [])) != 3:
        chosen = random.sample(DAILY_QUEST_POOL, 3)
        quests = []
        for idx, item in enumerate(chosen):
            target = random.choice(item["targets"])
            reward = random.randint(item["reward_range"][0], item["reward_range"][1])
            quests.append({
                "id": idx + 1,
                "type": item["type"],
                "name": item["name"],
                "target": target,
                "current": 0,
                "reward": reward,
                "completed": False,
                "claimed": False
            })
        player["daily_quests"] = {
            "date": today,
            "quests": quests,
            "all_completed_claimed": False
        }
    return player["daily_quests"]

def update_daily_quest_progress(player: dict, quest_type: str, amount: int = 1) -> list:
    dq = ensure_daily_quests(player)
    notifs = []
    
    for q in dq.get("quests", []):
        if q["type"] == quest_type and not q.get("completed", False):
            q["current"] = min(q["target"], q["current"] + amount)
            if q["current"] >= q["target"]:
                q["completed"] = True
                if not q.get("claimed", False):
                    q["claimed"] = True
                    player["pull_tickets"] += float(q["reward"])
                    notifs.append(f"🎯 **Hoàn thành Nhiệm vụ Ngày:** *{q['name']}* ({q['target']}/{q['target']}) ➔ Nhận ngay **+{q['reward']} Vé Pull**! 🎟️")

    all_done = all(q.get("completed", False) for q in dq.get("quests", []))
    if all_done and not dq.get("all_completed_claimed", False):
        dq["all_completed_claimed"] = True
        player["pull_tickets"] += 10.0
        notifs.append(
            "👑 **HOÀN THÀNH TOÀN BỘ 3/3 NHIỆM VỤ NGÀY!**\n"
            "⛩️ **Reimu:** *\"10 lượt pull đây, lo mà sử dụng cẩn thận\"*\n"
            "🎁 Nhận thêm **+10 Lượt Pull** tích lũy vào tài khoản!"
        )
    return notifs

def format_card_id(cid) -> str:
    """Format ID thẻ hiển thị đẹp mắt: #01, #13, hoặc #t1 đối với thẻ nhóm T."""
    if cid is None:
        return "#??"
    try:
        return f"#{int(cid):02d}"
    except (ValueError, TypeError):
        return f"#{cid}"

CARD_ALIASES = {
    "hecatia": 1, "lapislazuli": 1,
    "junko": 2,
    "okina": 3, "matara": 3,
    "yukari": 4, "yakumo": 4,
    "suika": 5, "ibuki": 5,
    "eirin": 6, "yagokoro": 6,
    "yuuka": 7, "kazami": 7,
    "yuyuko": 8, "saigyouji": 8,
    "flandre": 9, "flan": 9,
    "kaguya": 10, "houraisan": 10,
    "remilia": 11, "remi": 11,
    "utsuho": 12, "okuu": 12, "reiuji": 12,
    "reimu": 13, "hakurei": 13,
    "mokou": 14, "fujiwara": 14,
    "kasen": 15, "ibaraki": 15,
    "sakuya": 16, "izayoi": 16,
    "marisa": 17, "kirisame": 17,
    "youmu": 18, "konpaku": 18,
    "reisen": 19, "udongein": 19, "udonge": 19,
    "patchouli": 20, "patchy": 20, "knowledge": 20,
    "cirno": 21,
    "meiling": 22, "hong": 22,
    "rumia": 23,
    "mystia": 24, "lorelei": 24,
    "wriggle": 25, "nightbug": 25,
    "tewi": 26,
    "seiki": "t1", "t1": "t1", "dephap": "t1", "toannang": "t1"
}

def normalize_card_id(raw_id):
    """Chuẩn hóa ID thẻ từ int hoặc str (#1, 't1', 13) về key chính xác trong CARDS_DATA."""
    if raw_id is None:
        return None
    s = str(raw_id).strip().lower().replace("#", "")
    if s in CARDS_DATA:
        return s
    try:
        val = int(s)
        if val in CARDS_DATA:
            return val
    except ValueError:
        pass
    if s in CARD_ALIASES:
        return CARD_ALIASES[s]
    return None

def is_card_unlocked(player: dict, card_id: Union[int, str]) -> bool:
    try:
        cid_int = int(card_id)
    except (ValueError, TypeError):
        cid_int = None
    cid_str = str(card_id).lower()
    unlocked = player.get("unlocked_cards", [])
    if (cid_int is not None and cid_int in unlocked) or (cid_str in [str(x).lower() for x in unlocked]):
        return True
    if player.get("pull_stats", {}).get(cid_str, 0) > 0:
        return True
    if player.get("inventory", {}).get(cid_str, 0) > 0:
        return True
    return False

def is_card_locked(player: dict, card_id: Union[int, str]) -> bool:
    try:
        cid_int = int(card_id)
    except (ValueError, TypeError):
        cid_int = None
    cid_str = str(card_id).lower()
    locked = player.get("locked_cards", [])
    return (cid_int is not None and cid_int in locked) or (cid_str in [str(x).lower() for x in locked])

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
    now_date = get_today_vn()
    data = None
    is_new = False
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
        is_new = True

    if "inventory" not in data: data["inventory"] = {}
    if "pull_stats" not in data: data["pull_stats"] = {}
    if "unlocked_cards" not in data:
        data["unlocked_cards"] = []
        for cid_s, cnt in data.get("pull_stats", {}).items():
            if cnt > 0:
                try: data["unlocked_cards"].append(int(cid_s))
                except Exception:
                    data["unlocked_cards"].append(str(cid_s))
    if "locked_cards" not in data: data["locked_cards"] = []
    if "evolutions" not in data: data["evolutions"] = {}
    if "team" not in data: data["team"] = []
    if "shards" not in data or not isinstance(data.get("shards"), dict):
        data["shards"] = {"seiki": 0}
    else:
        data["shards"].setdefault("seiki", 0)
    if "xp" not in data: data["xp"] = 0
    if "pull_tickets" not in data: data["pull_tickets"] = 0.0
    if "language" not in data: data["language"] = "vi"
    if "tutorial" not in data:
        data["tutorial"] = {
            "active": False,
            "step": None,
            "quest_pulls_remaining": 0,
            "pull_used": False,
            "completed": False
        }
    if "pull_used" not in data["tutorial"]:
        data["tutorial"]["pull_used"] = data["tutorial"].get("completed", False)
    
    # TỰ ĐỘNG RESET NHIỆM VỤ NGÀY KHI QUA NGÀY MỚI (00:00 GMT+7)
    ensure_daily_quests(data)

    if is_new:
        data["_is_first_time"] = True

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

class OpponentTeamView(discord.ui.View):
    def __init__(self, opp_cards, opp_name="", opp_level=1):
        super().__init__(timeout=300)
        self.opp_cards = opp_cards or []
        self.opp_name = opp_name
        self.opp_level = opp_level
        self.selected_idx = 0

        if len(self.opp_cards) > 1:
            options = []
            for i, c in enumerate(self.opp_cards):
                ace_tag = "⭐ [Ace 2] " if c.get("is_ace2") else ""
                cid_val = c.get("cid", "?")
                lbl = f"{ace_tag}#{cid_val} {c['raw_name']} [{c['rank']}]"[:100]
                desc = f"ATK: {c['power']:,} | HP: {c['hp']:,}"[:100]
                options.append(discord.SelectOption(label=lbl, value=str(i), description=desc, default=(i == 0)))
            select_menu = discord.ui.Select(
                placeholder="🔍 Chọn thẻ bài đối thủ để soi Artwork & Kỹ Năng...",
                options=options,
                row=0
            )
            select_menu.callback = self.select_callback
            self.add_item(select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_idx = int(interaction.data["values"][0])
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                for opt in item.options:
                    opt.default = (opt.value == str(self.selected_idx))
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        if not self.opp_cards:
            return discord.Embed(title="👁️ ĐỘI HÌNH ĐỐI THỦ", description="Không có thông tin đội hình đối thủ!", color=0x3B82F6)
        c = self.opp_cards[self.selected_idx]
        is_ace = c.get("is_ace2", False)
        embed = discord.Embed(
            title=f"👁️ TOÀN BỘ ĐỘI HÌNH ĐỐI THỦ: {self.opp_name} (Lv.{self.opp_level})",
            description=f"Soi chiến thuật thẻ bài **{'⭐ [Ace 2] ' if is_ace else ''}#{c.get('cid', '?')} {c['raw_name']}** của đối phương!",
            color=0xF59E0B if is_ace else 0x3B82F6
        )
        if c.get("image"):
            embed.set_thumbnail(url=c["image"])
        rank_str = f"**[{c['rank']}]**" + (" `⭐⭐ [TIẾN HÓA ACE 2]`" if is_ace else "")
        embed.add_field(name="⭐ Phẩm Cấp / Rank:", value=rank_str, inline=True)

        buff_breakdown = f"*(Gốc: {c['base_power']:,} + Buff: {c['power'] - c['base_power']:,})*"
        if is_ace:
            buff_breakdown = f"*(Gốc: {c['base_power']:,} + Buff Lv: {c['power'] - c['base_power'] - ACE_POWER_BUFF:,} + Ace: +{ACE_POWER_BUFF})*"
        embed.add_field(
            name="⚔️ Sức Mạnh (ATK):",
            value=f"**{c['power']:,} DMG**\n{buff_breakdown}",
            inline=True
        )

        hp_breakdown = f"*(Gốc: {c['base_hp']:,} + Buff: {c['hp'] - c['base_hp']:,})*"
        if is_ace:
            hp_breakdown = f"*(Gốc: {c['base_hp']:,} + Buff Lv: {c['hp'] - c['base_hp'] - ACE_HP_BUFF:,} + Ace: +{ACE_HP_BUFF})*"
        embed.add_field(
            name="❤️ Sinh Mệnh (HP):",
            value=f"**{c['hp']:,} HP**\n{hp_breakdown}",
            inline=True
        )

        skill_text = c.get("skill") or "Tấn công Danmaku cơ bản"
        if is_ace and c.get("cid") in [13, 16, 17]:
            if c["cid"] == 13:
                skill_text += "\n🛡️ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Vô Tưởng Chuyển Sinh* né toàn bộ sát thương."
            elif c["cid"] == 16:
                skill_text += "\n⏳ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Thời Gian Đóng Băng* khiến đối phương mất lượt."
            elif c["cid"] == 17:
                skill_text += "\n🌟 **[Ace 2 Hiệu Ứng]** 30% kích hoạt *Master Spark* bộc phá ×1.5 sát thương."
        embed.add_field(name="✨ Kỹ Năng / Tuyệt Kỹ Danmaku:", value=f"*{skill_text}*", inline=False)

        summary_lines = []
        for i, card in enumerate(self.opp_cards):
            arrow = "👉 " if i == self.selected_idx else "• "
            ace_star = "⭐ " if card.get("is_ace2") else ""
            ace_label = " `[Ace 2]`" if card.get("is_ace2") else ""
            summary_lines.append(
                f"{arrow}{ace_star}**#{card.get('cid', '?')} {card['raw_name']}** `[{card['rank']}]`{ace_label} ⚔️ `{card['power']:,} DMG` | ❤️ `{card['hp']:,} HP`"
            )
        embed.add_field(name="👥 Danh Sách Đầy Đủ 3 Thẻ Đối Thủ:", value="\n".join(summary_lines), inline=False)
        embed.set_footer(text=f"Đang xem thẻ #{self.selected_idx + 1}/{len(self.opp_cards)} • Dùng menu bên dưới để đổi thẻ")
        return embed

class OpenDetailsView(discord.ui.View):
    def __init__(self, turns_data, opp_cards=None, opp_name="", opp_level=1):
        super().__init__(timeout=600)
        self.turns_data = turns_data
        self.opp_cards = opp_cards or []
        self.opp_name = opp_name
        self.opp_level = opp_level

    @discord.ui.button(label="📜 Diễn Biến Từng Hiệp (GIF)", style=discord.ButtonStyle.success, emoji="📜", row=0)
    async def open_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.turns_data:
            await interaction.response.send_message("Không có dữ liệu chi tiết cho trận chiến này!", ephemeral=True)
            return
        view = BattleDetailsView(self.turns_data)
        await interaction.response.send_message(embed=view.get_current_embed(), view=view, ephemeral=True)

    @discord.ui.button(label="👁️ Soi Toàn Bộ Đội Hình Đối Thủ", style=discord.ButtonStyle.primary, emoji="👁️", row=0)
    async def opp_team_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.opp_cards:
            await interaction.response.send_message("Không tìm thấy thông tin thẻ của đối thủ!", ephemeral=True)
            return
        view = OpponentTeamView(self.opp_cards, self.opp_name, self.opp_level)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

# ==============================================================================
# 6. QUẢN LÝ BOSS RAID (LIVE TURN-BY-TURN COMBAT, 15P COOLDOWN, TICKET REWARDS)
# ==============================================================================
def check_and_clean_expired_raid():
    global active_raid
    if active_raid is not None:
        created_ts = active_raid.get("created_timestamp")
        if not active_raid.get("started") and created_ts and (time.time() - created_ts > 180):
            if active_raid.get("task") and not active_raid["task"].done():
                active_raid["task"].cancel()
            active_raid = None
            return True
    return False

async def admin_reset_boss(channel_or_interaction, author):
    global active_raid, boss_cooldown_until
    was_stuck = (active_raid is not None)
    if active_raid is not None:
        if active_raid.get("task") and not active_raid["task"].done():
            active_raid["task"].cancel()
        if active_raid.get("view"):
            for child in active_raid["view"].children:
                child.disabled = True
            if active_raid.get("msg"):
                try: await active_raid["msg"].edit(view=active_raid["view"])
                except Exception: pass
    active_raid = None
    boss_cooldown_until = 0

    embed = discord.Embed(
        title="🧹 [ADMIN] ĐÃ RESET BOSS RAID THÀNH CÔNG!",
        description=(
            f"👑 **Thực hiện bởi:** {author.mention}\n"
            f"✅ **Trạng thái:** {'Đã giải phóng Boss Raid bị kẹt trước đó!' if was_stuck else 'Boss Raid đã được dọn sạch hoàn toàn.'}\n"
            "⏱️ **Hồi chiêu:** Đã đưa thời gian hồi chiêu về **0 giây**.\n"
            "⛩️ **Sẵn sàng:** Bạn có thể dùng `boss admin spawn` để gọi ngay tại kênh này, hoặc để boss tự xuất hiện khi chat!"
        ),
        color=0x10B981
    )
    embed.set_footer(text="Hakurei Shrine • Boss Raid Admin Reset")
    if isinstance(channel_or_interaction, discord.Interaction):
        if channel_or_interaction.response.is_done():
            await channel_or_interaction.followup.send(embed=embed)
        else:
            await channel_or_interaction.response.send_message(embed=embed)
    elif hasattr(channel_or_interaction, "send"):
        await channel_or_interaction.send(embed=embed)

async def raid_timer_lifecycle(channel, raid_data, view):
    global active_raid, boss_cooldown_until
    try:
        try:
            await asyncio.wait_for(raid_data["start_event"].wait(), timeout=120.0)
        except asyncio.TimeoutError:
            pass

        for child in view.children:
            child.disabled = True
        if raid_data.get("msg"):
            try:
                await raid_data["msg"].edit(view=view)
            except Exception:
                pass

        if raid_data.get("started") or raid_data.get("closed"):
            return

        participants = raid_data.get("participants", [])

        if participants:
            raid_data["started"] = True
            boss_cooldown_until = time.time() + BOSS_CONFIG["cooldown_seconds"]
            names_str = ", ".join(raid_data.get("names", []))
            await channel.send(
                f"⏰ **ĐÃ HẾT 2 PHÚT CHUẨN BỊ!**\n"
                f"⚔️ **{len(participants)} Dũng Giả** ({names_str}) đồng loạt dàn quân xuất trận!\n"
                f"👹 **Reimu Dị Hình** gầm thét kinh thiên động địa — **TRẬN ĐẠI CHIẾN CHÍNH THỨC BẮT ĐẦU!**"
            )
            try:
                await execute_raid(channel, raid_data)
            except Exception as e:
                print(f"Lỗi khi thực thi Boss Raid: {e}", flush=True)
                try:
                    await channel.send(f"⚠️ Đã xảy ra sự cố kỹ thuật trong trận đánh Boss: `{e}`")
                except Exception:
                    pass
            finally:
                active_raid = None
        else:
            raid_data["closed"] = True
            active_raid = None
            boss_cooldown_until = time.time() + 60
            await channel.send(
                "🌌 **Dị hình đã xé toạc không gian và trốn thoát do không có pháp sư nào dám nghênh chiến!**\n"
                "*(Đền Hakurei tạm thời tĩnh lặng, hãy chuẩn bị lực lượng cho lần dị biến tiếp theo...)*"
            )
    except asyncio.CancelledError:
        return
    except Exception as ex:
        print(f"Lỗi trong raid_timer_lifecycle: {ex}", flush=True)
        active_raid = None

async def spawn_boss_raid(channel, author=None, boss_type=None):
    global active_raid, boss_cooldown_until
    if active_raid is not None:
        if active_raid.get("task") and not active_raid["task"].done():
            active_raid["task"].cancel()
        active_raid = None

    if boss_type not in ["reimu", "seiki"]:
        boss_type = "seiki" if random.random() < 0.50 else "reimu"

    is_seiki = (boss_type == "seiki")
    cfg = SEIKI_BOSS_CONFIG if is_seiki else BOSS_CONFIG

    start_event = asyncio.Event()
    raid_data = {
        "channel_id": channel.id,
        "boss_type": boss_type,
        "boss_config": cfg,
        "participants": [],
        "names": [],
        "created_at": datetime.now().isoformat(),
        "created_timestamp": time.time(),
        "start_event": start_event,
        "started": False,
        "closed": False,
        "msg": None,
        "view": None,
        "task": None
    }
    active_raid = raid_data

    is_admin = (author is not None)
    title = f"🚨 [ADMIN TRIỆU HỒI] CẢNH BÁO KHẨN CẤP: DỊ BIẾN {cfg['name'].upper()}!" if is_admin else f"🚨 CẢNH BÁO KHẨN CẤP: DỊ BIẾN {cfg['name'].upper()}!"

    if is_seiki:
        reimu_line = f"🌸 **Reimu thảng thốt:** *{cfg['reimu_quote']}*\n\n"
        desc = (f"👑 **Được triệu hồi bởi Admin:** {author.mention}\n\n{reimu_line}👺 **{cfg['name']}**\n*{cfg['desc']}*" 
                if is_admin else f"{reimu_line}👺 **{cfg['name']}**\n*{cfg['desc']}*")
        embed = discord.Embed(title=title, description=desc, color=0x7C3AED)
        embed.set_image(url=cfg["image"])
        embed.add_field(name="❤️ Máu Boss (HP):", value=f"**{cfg['hp']:,} HP** *(Phase 1)*", inline=True)
        embed.add_field(name="⚔️ Sát Thương Đánh Thường:", value=f"• Cơ bản: **{cfg['power']:,} DMG** *(chia đều)*\n• Khi có Spark: **4,500 DMG** *(x1.5)*", inline=True)
        embed.add_field(name=f"👥 Người Tham Gia (0/{cfg['max_players']}):", value="Chưa có ai", inline=False)
        embed.add_field(
            name="🔮 Kỹ Năng & Nội Tại (Độc Quyền - Không Trùng Turn):",
            value=(
                "• 💚 **Nội Tại:** Mỗi hiệp tự hồi phục **1.5% HP tối đa (450 HP)**!\n"
                "• 🌟 **Multi Master Spark (15%):** Bộc phát ma lực x1.5 sát thương (4,500 DMG chia đều) duy trì trong **3 lượt**!\n"
                "• 🛡️ **Fantasy Seal (20%):** Dựng kết giới phong ấn, **MIỄN TOÀN BỘ SÁT THƯƠNG** trong 1 turn!\n"
                "• ⚡ **Blitz Attack (20%):** Oanh tạc chớp nhoáng gây **4,000 DMG** diện rộng trực tiếp lên toàn bộ thẻ tiền tuyến!\n"
                "*(Lưu ý: Không bao giờ kích hoạt trùng chiêu trong cùng một hiệp)*"
            ),
            inline=False
        )
        embed.add_field(
            name="🎁 Phần Thưởng Thanh Tẩy Boss:",
            value="• 10% cơ hội nhận **10 Vé Pull**, 40% nhận **5 Vé**, 50% nhận **3 Vé**!\n• Tỉ lệ **2.5%** rơi Mảnh Seiki Độc Quyền!\n• Nhận thêm **+100 XP** và điểm danh nhiệm vụ diệt Boss!",
            inline=False
        )
        embed.add_field(
            name="⏱️ Thời Gian Chuẩn Bị (2 Phút):",
            value=(
                "• Có đúng **2 phút (120 giây)** để bấm **'Tham Gia'** (Miễn phí)!\n"
                "• **Tự động mở raid:** Khi hết 2 phút, nếu có dũng giả tham chiến, trận đại chiến sẽ **TỰ ĐỘNG KHỞI TRANH** ngay lập tức!\n"
                "• **Tự động đóng:** Nếu sau 2 phút không có ai tham gia, Dị Hình sẽ xé toạc không gian và trốn thoát!"
            ),
            inline=False
        )
    else:
        desc = f"👑 **Được triệu hồi bởi Admin:** {author.mention}\n\n**{BOSS_CONFIG['name']}**\n*{BOSS_CONFIG['desc']}*" if is_admin else f"**{BOSS_CONFIG['name']}**\n*{BOSS_CONFIG['desc']}*"
        embed = discord.Embed(title=title, description=desc, color=0xDC2626)
        embed.set_image(url=BOSS_CONFIG["image"])
        embed.add_field(name="❤️ Máu Boss (HP):", value=f"{BOSS_CONFIG['hp']:,} HP *(Phase 1: 30k HP)*", inline=True)
        embed.add_field(name="⚔️ Sát Thương Đánh Thường:", value=f"• Phase 1: **{BOSS_CONFIG['power']:,} DMG** *(chia đều)*\n• Phase 2: **{BOSS_PHASE2_CONFIG['power']:,} DMG** *(chia đều)*", inline=True)
        embed.add_field(name=f"👥 Người Tham Gia (0/{BOSS_CONFIG['max_players']}):", value="Chưa có ai", inline=False)
        embed.add_field(
            name="🎁 Cơ Chế 2 Phase & Phần Thưởng Đột Phá:",
            value=(
                "• **Phase 1 (30k HP):** 10% ra **10 Vé**, 40% ra **5 Vé**, 50% ra **3 Vé**, 2.5% rơi Mảnh Seiki!\n"
                f"• **Chuyển Phase 2 ({BOSS_PHASE2_CONFIG['hp']:,} HP / {BOSS_PHASE2_CONFIG['power']:,} DMG chia đều):** Hồi sinh & phục hồi **100% HP toàn bộ thẻ bài**!\n"
                "• **Phase 2:** 10% ra **20 Vé**, 40% ra **10 Vé**, 50% ra **5 Vé**, 2.5% rơi Mảnh Seiki!\n"
                "• **Trận đấu trực tiếp:** Diễn biến từng hiệp được phát sóng trực tiếp!"
            ),
            inline=False
        )
        embed.add_field(
            name="⏱️ Thời Gian Chuẩn Bị (2 Phút):",
            value=(
                "• Có đúng **2 phút (120 giây)** để bấm **'Tham Gia'** (Miễn phí)!\n"
                "• **Tự động mở raid:** Khi hết 2 phút, nếu có dũng giả tham chiến, trận đại chiến sẽ **TỰ ĐỘNG KHỞI TRANH** ngay lập tức!\n"
                "• **Tự động đóng:** Nếu sau 2 phút không có ai tham gia, Dị Hình sẽ xé toạc không gian và trốn thoát!"
            ),
            inline=False
        )
    embed.set_footer(text=f"Bấm 'Tham Gia' để xuất trận • Miễn phí • {'Admin Force Spawn' if is_admin else 'Boss Tự Nhiên'}")
    view = RaidJoinView(raid_data)
    raid_data["view"] = view
    msg = await channel.send(embed=embed, view=view)
    raid_data["msg"] = msg
    task = asyncio.create_task(raid_timer_lifecycle(channel, raid_data, view))
    raid_data["task"] = task

async def admin_spawn_boss(channel, author, boss_type=None):
    global boss_cooldown_until
    boss_cooldown_until = 0
    await spawn_boss_raid(channel, author, boss_type=boss_type)

class RaidJoinView(discord.ui.View):
    def __init__(self, raid_data):
        super().__init__(timeout=None)
        self.raid_data = raid_data

    @discord.ui.button(label="⚔️ Tham Gia / Join Raid (Miễn phí)", style=discord.ButtonStyle.danger, emoji="💥")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.raid_data.get("started") or self.raid_data.get("closed"):
            await interaction.response.send_message("Trận chiến đã bắt đầu hoặc thời gian chuẩn bị đã kết thúc!", ephemeral=True)
            return

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

        current_team = [cid for cid in player.get("team", []) if cid in CARDS_DATA and not is_card_locked(player, cid)]
        if len(current_team) < 3:
            owned_ids = [cid for cid, cnt in player.get("inventory", {}).items() if cnt > 0 and cid in CARDS_DATA and not is_card_locked(player, cid)]
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

        await interaction.response.send_message(f"🔥 {interaction.user.mention} đã tham chiến! ({count}/{BOSS_CONFIG['max_players']} dũng giả)", ephemeral=False)

        try:
            embed = interaction.message.embeds[0]
            embed.set_field_at(
                2,
                name=f"👥 Người Tham Gia ({count}/{BOSS_CONFIG['max_players']}):",
                value=", ".join(self.raid_data["names"]),
                inline=False
            )
            await interaction.message.edit(embed=embed, view=self)
        except Exception:
            pass

        if count >= BOSS_CONFIG["max_players"]:
            self.raid_data["start_event"].set()

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
        lvl_buff_pwr = get_level_atk_buff(p["level"])
        lvl_buff_hp = get_level_hp_buff(p["level"])
        team_cids = [cid for cid in p.get("team", []) if cid in CARDS_DATA and not is_card_locked(p, cid)]
        if len(team_cids) < 3:
            owned_ids = [cid for cid, cnt in p.get("inventory", {}).items() if cnt > 0 and cid in CARDS_DATA and not is_card_locked(p, cid)]
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
                card_pwr = card["power"] + lvl_buff_pwr + ace_pwr
                card_hp = card["hp"] + lvl_buff_hp + ace_hp
                card_name = f"[Ace 2 ⭐⭐] #{card['id']} {card['name']}" if is_ace2 else f"{format_card_id(card['id'])} {card['name']}"
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
            "marisa_spark_used": False,
            "seiki_seal_used": False,
            "seiki_spark_used": False,
            "seiki_heal_used": False,
            "seiki_used_turn": -1,
            "death_round": None
        })

    boss_type = raid_data.get("boss_type", "reimu")
    boss_cfg = raid_data.get("boss_config", SEIKI_BOSS_CONFIG if boss_type == "seiki" else BOSS_CONFIG)
    p1_max_hp = boss_cfg["hp"]
    p1_hp = p1_max_hp
    p1_power = boss_cfg["power"]
    seiki_spark_turns = 0

    if boss_type == "seiki":
        init_embed = discord.Embed(
            title="⚔️ ĐẠI CHIẾN BẮT ĐẦU: SEIKI DỊ HÌNH - DỊ TÀ ĐỆ NHẤT PHÁP SƯ",
            description=(
                f"🌸 **Reimu thảng thốt:** *{boss_cfg['reimu_quote']}*\n\n"
                f"🔥 **{len(combatants)} Dũng Giả** cùng đội quân thẻ bài đã dàn trận nghênh chiến!\n"
                f"Theo dõi diễn biến từng hiệp trực tiếp ngay bên dưới!"
            ),
            color=0x7C3AED
        )
    else:
        init_embed = discord.Embed(
            title="⚔️ ĐẠI CHIẾN BẮT ĐẦU: REIMU DỊ HÌNH (PHASE 1)",
            description=f"🔥 **{len(combatants)} Dũng Giả** cùng đội quân thẻ bài đã dàn trận nghênh chiến!\nTheo dõi diễn biến từng hiệp trực tiếp ngay bên dưới!",
            color=0xDC2626
        )
    init_embed.set_thumbnail(url=boss_cfg["image"])
    init_embed.add_field(name=f"❤️ Máu {boss_cfg['name']}:", value=f"`{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**", inline=False)
    battle_msg = await channel.send(embed=init_embed)
    await asyncio.sleep(2.0)

    p1_rounds = 0
    max_rounds = 35
    p1_battle_history = []
    all_raid_turns = []

    while p1_hp > 0 and p1_rounds < max_rounds:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants:
            break

        p1_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        passive_log = None
        if boss_type == "seiki":
            heal_amt = int(p1_max_hp * boss_cfg.get("passive_regen_pct", 0.015))
            old_hp = p1_hp
            p1_hp = min(p1_max_hp, p1_hp + heal_amt)
            actual_healed = p1_hp - old_hp
            if actual_healed > 0:
                passive_log = f"💚 **[Nội Tại - Hồi Phục]** Seiki Dị Hình hấp thụ dị khí hồi phục **+{actual_healed:,} HP** (1.5% HP tối đa)!"

        boss_stunned = False
        sakuya_stun_notif = None
        marisa_spark_notif = None
        turn_image = None

        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 16 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.40:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#16] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss bị **STUN** mất lượt!"
                    break

        seiki_invul = False
        seiki_action = "normal"
        if boss_type == "seiki" and not boss_stunned:
            if seiki_spark_turns > 0:
                seiki_spark_turns -= 1
                seiki_action = "spark_active"
            else:
                roll_s = random.random()
                if roll_s < 0.15:
                    seiki_spark_turns = 2  # Turn hiện tại + 2 turn kế = 3 lượt
                    seiki_action = "spark_start"
                elif roll_s < 0.35:  # 0.15 + 0.20 = 0.35
                    seiki_invul = True
                    seiki_action = "fantasy_seal"
                elif roll_s < 0.55:  # 0.35 + 0.20 = 0.55
                    seiki_action = "blitz_attack"
                else:
                    seiki_action = "normal"

        round_player_dmg = 0
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            card_dmg = ac["power"]
            if ac["cid"] == 17 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 1.5)
                    if not turn_image:
                        turn_image = EVOL_CONFIG[17]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×1.5 giáng **{card_dmg:,} DMG** lên Boss!"
            
            # Kỹ năng Thẻ Seiki T1 (Tuân thủ: Không bao giờ kích hoạt 2 chiêu trong cùng 1 lượt!)
            if str(ac["cid"]).lower() == "t1":
                if c.get("seiki_used_turn") != p1_rounds:
                    if not c.get("seiki_spark_used") and random.random() < 0.30:
                        c["seiki_spark_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image:
                            turn_image = "https://klipy.com/gifs/marisa-master-spark"
                        marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({c['username']}) bộc phát **Master Spark** (30%)! Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss!"
                    elif not c.get("seiki_heal_used") and ac["current_hp"] < ac["max_hp"] and random.random() < 0.20:
                        c["seiki_heal_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        heal_val = int(ac["max_hp"] * 0.30)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image:
                            turn_image = "https://klipy.com/gifs/shoko-ieiri-2"
                        passive_log = (passive_log + "\n" if passive_log else "") + f"💚 **[Nhóm T] [#t1] Seiki** ({c['username']}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_val:,} HP** cho bản thân! ({ac['current_hp']:,}/{ac['max_hp']:,} HP)"

            round_player_dmg += card_dmg
            c["total_dmg"] += card_dmg

        if boss_type == "seiki" and seiki_invul and not boss_stunned:
            player_atk_str = f"🛡️ Toàn quân dồn **{round_player_dmg:,} DMG** nhưng **Seiki Dị Hình** đã kích hoạt **Fantasy Seal**, MIỄN TOÀN BỘ SÁT THƯƠNG trong hiệp này!"
        else:
            p1_hp = max(0, p1_hp - round_player_dmg)
            player_atk_str = f"Toàn quân gây **{round_player_dmg:,} DMG** lên Boss!"

        boss_action_log = ""
        if boss_type == "seiki":
            if p1_hp <= 0:
                boss_action_log = "💥 **Seiki Dị Hình đã bị đánh gục hoàn toàn! Dị tà ma thuật tiêu tan!**"
            elif boss_stunned:
                boss_action_log = "❄️ Boss bị đóng băng thời gian, bất lực không thể ra đòn!"
            else:
                if seiki_action == "fantasy_seal":
                    turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                    boss_action_log = "🛡️ **[KỸ NĂNG] Seiki Dị Hình** kích hoạt **Fantasy Seal (20%)**! Vận khởi kết giới phong ấn tuyệt đối, MIỄN TOÀN BỘ SÁT THƯƠNG trong 1 turn!"
                elif seiki_action == "blitz_attack":
                    turn_image = "https://klipy.com/gifs/naoya-jujutsu-kaisen"
                    boss_action_log = "⚡ **[KỸ NĂNG] Seiki Dị Hình** phát động **Blitz Attack (20%)**! Oanh kích chớp nhoáng gây **4,000 DMG** diện rộng lên toàn bộ thẻ tiền tuyến!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                            if c.get("seiki_used_turn") != p1_rounds and random.random() < 0.40:
                                c["seiki_seal_used"] = True
                                c["seiki_used_turn"] = p1_rounds
                                invul = True
                                turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            ac["current_hp"] -= 4000
                elif seiki_action in ["spark_start", "spark_active"]:
                    turn_image = "https://klipy.com/gifs/marisa-master-spark"
                    num_front = len(frontline_cards)
                    curr_dmg = int(p1_power * 1.5)  # 4,500 DMG
                    dmg_per_card = max(100, curr_dmg // num_front)
                    if seiki_action == "spark_start":
                        boss_action_log = f"🌟 **[KỸ NĂNG] Seiki Dị Hình** bộc phát **Multi Master Spark (15%)**! Cường hóa x1.5 sát thương trong 3 lượt và giáng **{curr_dmg:,} DMG** chia đều **{dmg_per_card:,} DMG** lên mỗi thẻ tiền tuyến ({num_front} lá)!"
                    else:
                        boss_action_log = f"🌟 **[Multi Master Spark Duy Trì]** Sát thương cường hóa x1.5, giáng **{curr_dmg:,} DMG** chia đều **{dmg_per_card:,} DMG** lên mỗi thẻ tiền tuyến ({num_front} lá)! (Còn {seiki_spark_turns} lượt)"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                            if c.get("seiki_used_turn") != p1_rounds and random.random() < 0.40:
                                c["seiki_seal_used"] = True
                                c["seiki_used_turn"] = p1_rounds
                                invul = True
                                turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            ac["current_hp"] -= dmg_per_card
                else:  # normal
                    num_front = len(frontline_cards)
                    dmg_per_card = max(100, p1_power // num_front)
                    boss_action_log = f"⚔️ Seiki Dị Hình phóng đạn hắc ám tổng **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 13 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                            if c.get("seiki_used_turn") != p1_rounds and random.random() < 0.40:
                                c["seiki_seal_used"] = True
                                c["seiki_used_turn"] = p1_rounds
                                invul = True
                                turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            ac["current_hp"] -= dmg_per_card
        else:
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
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                if not turn_image or turn_image == BOSS_SKILL_CONFIG["gif"]:
                                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                            if c.get("seiki_used_turn") != p1_rounds and random.random() < 0.40:
                                c["seiki_seal_used"] = True
                                c["seiki_used_turn"] = p1_rounds
                                invul = True
                                turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN THƯƠNG!"
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
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                            if c.get("seiki_used_turn") != p1_rounds and random.random() < 0.40:
                                c["seiki_seal_used"] = True
                                c["seiki_used_turn"] = p1_rounds
                                invul = True
                                turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN THƯƠNG!"
                        if not invul:
                            ac["current_hp"] -= dmg_per_card

        push_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["current_hp"] <= 0:
                ac["current_hp"] = 0
                dead_name = ac["name"]
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
            title=f"⚔️ HIỆP {p1_rounds} - {boss_cfg['name'].upper()}",
            description=f"❤️ **Máu Boss:** `{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**",
            color=0x7C3AED if boss_type == "seiki" else 0xDC2626
        )
        if passive_log:
            round_embed.add_field(name="💚 Nội Tại Hồi Phục:", value=passive_log, inline=False)
        round_embed.add_field(name="💥 Tiền Tuyến Tấn Công:", value=player_atk_str, inline=False)
        if sakuya_stun_notif:
            round_embed.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
        if marisa_spark_notif:
            round_embed.add_field(name="🌟 Master Spark Oanh Tạc:", value=marisa_spark_notif, inline=False)
        round_embed.add_field(name="👺 Phản Kích Của Boss:", value=boss_action_log, inline=False)
        if push_logs:
            round_embed.add_field(name="🔄 Thay Đổi Tiền Tuyến:", value="\n".join(push_logs), inline=False)
        round_embed.add_field(name="🛡️ Tình Trạng Tiền Tuyến Hiện Tại:", value="\n".join(round_card_status), inline=False)

        if turn_image:
            round_embed.set_image(url=turn_image)
        else:
            round_embed.set_thumbnail(url=boss_cfg["image"])

        p1_battle_history.append(f"Hiệp {p1_rounds}: Gây {round_player_dmg:,} DMG (Boss còn {p1_hp:,} HP).")
        all_raid_turns.append({
            "round": p1_rounds,
            "phase": 1,
            "title": f"Hiệp {p1_rounds}: {boss_cfg['name']}",
            "short_label": f"H{p1_rounds} - {boss_cfg['name'][:10]}",
            "short_desc": f"Boss còn {p1_hp:,} HP",
            "desc": f"👹 **{boss_cfg['name']}**\n❤️ Máu Boss: `{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**",
            "color": 0x7C3AED if boss_type == "seiki" else 0xDC2626,
            "image": turn_image,
            "fields": [
                *([("💚 Nội Tại Hồi Phục:", passive_log, False)] if passive_log else []),
                ("💥 Tiền Tuyến Tấn Công:", player_atk_str, False),
                *([("❄️ Kỹ Năng Đột Biến:", sakuya_stun_notif, False)] if sakuya_stun_notif else []),
                *([("🌟 Master Spark:", marisa_spark_notif, False)] if marisa_spark_notif else []),
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
            title=f"❌ QUÂN ĐOÀN THẤT THỦ TRƯỚC {boss_cfg['name'].upper()}!",
            description=f"Toàn bộ dũng giả đã tử trận sau {p1_rounds} hiệp!\nBoss còn **{p1_hp:,} HP** và đã trốn thoát.\n⏳ Hồi chiêu **15 phút** đã kích hoạt!",
            color=0xEF4444
        )
        embed_fail.set_thumbnail(url=boss_cfg["image"])
        await channel.send(embed=embed_fail, view=OpenDetailsView(all_raid_turns))
        return

    p1_rewards_data = {}
    for uid in participants:
        p = get_player(uid)
        roll = random.random()
        if roll < 0.10:
            t_val = 10.0
            d_str = "🔥 **+10 Vé** (10%)"
        elif roll < 0.50:
            t_val = 5.0
            d_str = "💎 **+5 Vé** (40%)"
        else:
            t_val = 3.0
            d_str = "✨ **+3 Vé** (50%)"

        items_won = [d_str]
        # 2.5% tỉ lệ rơi Mảnh Seiki Đệ Pháp Toàn Năng (10 Mảnh đổi 1 Thẻ T1)
        if random.random() < 0.025:
            p_shards = p.setdefault("shards", {})
            p_shards["seiki"] = p_shards.get("seiki", 0) + 1
            cur_shards = p_shards["seiki"]
            shard_notice = f"🔮 **+1 Mảnh Seiki** (2.5% Siêu Hiếm! Kho: {cur_shards}/10)"
            if cur_shards >= 10:
                shard_notice += " ✨ *(Đã đủ 10 mảnh! Dùng `/t translate`)*"
            items_won.append(shard_notice)

        p["pull_tickets"] += t_val
        p["xp"] += 100
        update_daily_quest_progress(p, "raid", 1)
        save_player(p)
        p1_rewards_data[uid] = {"total_pulls": t_val, "items": items_won, "username": p["username"]}

    if boss_type == "seiki":
        total_raid_dmg = sum(c["total_dmg"] for c in combatants)
        final_embed = discord.Embed(
            title="🌟 CHIẾN THẮNG HUY HOÀNG: THANH TẨY SEIKI DỊ HÌNH!",
            description=(
                "🌸 **Reimu thở phào nhẹ nhõm:** *\"Đó không phải cha ta! Dị tà ma thuật đã tan biến, ngài ấy đã được thanh tẩy hoàn toàn! Cảm ơn mọi người nhiều lắm!\"*\n\n"
                f"🎉 **Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư** đã bị khuất phục hoàn toàn sau **{p1_rounds} hiệp**!\n"
                f"💥 **Tổng sát thương toàn quân:** **{total_raid_dmg:,} DMG**\n"
                f"⏳ **Hồi chiêu Boss tiếp theo:** **15 phút**"
            ),
            color=0x10B981
        )
        final_embed.set_thumbnail(url=boss_cfg["image"])
        p1_summary = [f"🎁 **{r['username']}**: +{r['total_pulls']:.0f} Vé Pull ({r['items'][0]}) + 100 XP" + (f"\n   └ {r['items'][1]}" if len(r['items']) > 1 else "") for r in p1_rewards_data.values()]
        final_embed.add_field(name="📦 Phần Thưởng Dũng Giả (10% 10 vé, 40% 5 vé, 50% 3 vé, 2.5% Mảnh Seiki):", value="\n".join(p1_summary), inline=False)
        await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))
        return

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
        c["marisa_spark_used"] = False
        c["seiki_seal_used"] = False
        c["seiki_spark_used"] = False
        c["seiki_heal_used"] = False
        c["seiki_used_turn"] = -1
        for card in c["team_cards"]:
            card["current_hp"] = card["max_hp"]

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
        marisa_spark_notif = None
        turn_image = None

        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 16 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.40:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#16] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss Phase 2 bị **STUN**!"
                    break

        round_player_dmg = 0
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            card_dmg = ac["power"]
            if ac["cid"] == 17 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 1.5)
                    if not turn_image:
                        turn_image = EVOL_CONFIG[17]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×1.5 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"

            # Kỹ năng Thẻ Seiki T1 (Tuân thủ: Không bao giờ kích hoạt 2 chiêu trong cùng 1 lượt!)
            if str(ac["cid"]).lower() == "t1":
                if c.get("seiki_used_turn") != p2_rounds:
                    if not c.get("seiki_spark_used") and random.random() < 0.30:
                        c["seiki_spark_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image:
                            turn_image = "https://klipy.com/gifs/marisa-master-spark"
                        marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({c['username']}) bộc phát **Master Spark** (30%)! Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"
                    elif not c.get("seiki_heal_used") and ac["current_hp"] < ac["max_hp"] and random.random() < 0.20:
                        c["seiki_heal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        heal_val = int(ac["max_hp"] * 0.30)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image:
                            turn_image = "https://klipy.com/gifs/shoko-ieiri-2"

            round_player_dmg += card_dmg
            c["total_dmg"] += card_dmg

        p2_hp = max(0, p2_hp - round_player_dmg)

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
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True
                            invul = True
                            if not turn_image or turn_image == BOSS_SKILL_CONFIG["gif"]:
                                turn_image = EVOL_CONFIG[13]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                        if c.get("seiki_used_turn") != p2_rounds and random.random() < 0.40:
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p2_rounds
                            invul = True
                            turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                            boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
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
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True
                            invul = True
                            turn_image = EVOL_CONFIG[13]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#13] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and not c.get("seiki_seal_used"):
                        if c.get("seiki_used_turn") != p2_rounds and random.random() < 0.40:
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p2_rounds
                            invul = True
                            turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                            boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                    if not invul:
                        ac["current_hp"] -= dmg_per_card

        push_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["current_hp"] <= 0:
                ac["current_hp"] = 0
                dead_name = ac["name"]
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
        if marisa_spark_notif:
            round_embed.add_field(name="🌟 Master Spark Oanh Tạc:", value=marisa_spark_notif, inline=False)
        round_embed.add_field(name="👺 Boss Phase 2 Ra Đòn:", value=boss_action_log, inline=False)
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
                *([("🌟 Master Spark:", marisa_spark_notif, False)] if marisa_spark_notif else []),
                ("👺 Boss Phase 2 Ra Đòn:", boss_action_log, False),
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
            roll = random.random()
            if roll < 0.10:
                t_val = 20.0
                d_str = "👑 **+20 Vé** (10%)"
            elif roll < 0.50:
                t_val = 10.0
                d_str = "🔥 **+10 Vé** (40%)"
            else:
                t_val = 5.0
                d_str = "💎 **+5 Vé** (50%)"

            items_won = [d_str]
            # 2.5% tỉ lệ rơi Mảnh Seiki Đệ Pháp Toàn Năng
            if random.random() < 0.025:
                p_shards = p.setdefault("shards", {})
                p_shards["seiki"] = p_shards.get("seiki", 0) + 1
                cur_shards = p_shards["seiki"]
                shard_notice = f"🔮 **+1 Mảnh Seiki** (2.5% Siêu Hiếm! Kho: {cur_shards}/10)"
                if cur_shards >= 10:
                    shard_notice += " ✨ *(Đã đủ 10 mảnh! Dùng `/t translate`)*"
                items_won.append(shard_notice)

            p["pull_tickets"] += t_val
            p["xp"] += 150
            save_player(p)
            p2_rewards_data[uid] = {
                "total_pulls": t_val,
                "items": items_won,
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

    p1_summary = [f"🎁 **{r['username']}**: +{r['total_pulls']:.0f} Vé Pull ({r['items'][0]}) + 100 XP" + (f"\n   └ {r['items'][1]}" if len(r['items']) > 1 else "") for r in p1_rewards_data.values()]
    final_embed.add_field(name="📦 Phần Thưởng Phase 1 (10% 10 vé, 40% 5 vé, 50% 3 vé, 2.5% Mảnh Seiki):", value="\n".join(p1_summary), inline=False)

    if p2_defeated:
        p2_summary = []
        for r in p2_rewards_data.values():
            lvl_up = f" 🌟 **LÊN CẤP {r['new_level']}!**" if r['new_level'] > r['old_level'] else ""
            shard_line = f"\n   └ {r['items'][1]}" if len(r['items']) > 1 else ""
            p2_summary.append(f"🏆 **{r['username']}**: Nhận **+{r['total_pulls']:.0f} Vé Pull** ({r['items'][0]}) + 150 XP!{lvl_up}{shard_line}\n   └ *Tổng vé hiện có: {r['total_tickets']:.2f} vé*")
        final_embed.add_field(name="💎 Phần Thưởng Siêu Cấp Phase 2 (10% 20 vé, 40% 10 vé, 50% 5 vé, 2.5% Mảnh Seiki):", value="\n".join(p2_summary), inline=False)
    else:
        final_embed.add_field(name="⚠️ Kết QuẢ Phase 2:", value=f"Boss Phase 2 còn {p2_hp:,} HP! Toàn bộ quà Phase 1 vẫn được bảo lưu trọn vẹn.", inline=False)

    await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))

# ==============================================================================
# 7. SỰ KIỆN BOT DISCORD (ON_READY & ON_MESSAGE)
# ==============================================================================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành công dưới tên: {bot.user} (ID: {bot.user.id})", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã đồng bộ thành công {len(synced)} lệnh Slash toàn cục!", flush=True)
    except Exception as e:
        print(f"❌ Lỗi đồng bộ Slash Commands: {e}", flush=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    check_and_clean_expired_raid()

    uid = str(message.author.id)
    uname = message.author.display_name
    now_iso = datetime.now().isoformat()

    if use_mongo and users_collection is not None:
        try:
            users_collection.update_one(
                {"user_id": uid},
                {"$set": {"username": uname, "last_seen": now_iso},
                 "$inc": {"interaction_count": 1},
                 "$setOnInsert": {"first_seen": now_iso}},
                upsert=True
            )
        except Exception:
            pass
    else:
        try:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_seen, last_seen, interaction_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    last_seen=excluded.last_seen,
                    interaction_count=users.interaction_count + 1
            """, (uid, uname, now_iso, now_iso))
            conn.commit()
        except Exception:
            pass

    # ==============================================================================
    # 7.1 XỬ LÝ LỆNH PREFIX CŨ (BẬT PREFIX VÀ SLASH COMMAND HOẠT ĐỘNG SONG SONG)
    # ==============================================================================
    raw_content = message.content.strip()

    # Hỗ trợ cả prefix ! và / (khi người dùng gõ / nhưng chưa chọn Slash Menu của Discord)
    used_prefix = None
    if raw_content.startswith("!"):
        used_prefix = "!"
    elif raw_content.startswith("/"):
        used_prefix = "/"

    if used_prefix:
        cmd_text = raw_content[len(used_prefix):].strip()
        cmd_parts = cmd_text.split()
        if cmd_parts:
            primary_cmd = cmd_parts[0].lower()

            if primary_cmd in ["boss"]:
                if len(cmd_parts) > 1 and cmd_parts[1].lower() == "admin":
                    if len(cmd_parts) > 2 and cmd_parts[2].lower() in ["spawn", "summon"]:
                        await slash_admin_boss_spawn.callback(message)
                        return
                    elif len(cmd_parts) > 2 and cmd_parts[2].lower() in ["reset", "clean", "clear"]:
                        await slash_admin_boss_reset.callback(message)
                        return
                    else:
                        await slash_boss_admin.callback(message)
                        return
                else:
                    await slash_boss_status.callback(message)
                    return

            if primary_cmd in ["shards", "shard", "manh"]:
                await slash_shards_view.callback(message)
                return

            if primary_cmd in ["card_info", "cardinfo", "infocard", "check_card"]:
                arg_val = " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else None
                await handle_check_character(message, nhan_vat=arg_val)
                return

            if primary_cmd in ["t", "the"]:
                if len(cmd_parts) > 1:
                    sub = cmd_parts[1].lower()
                    if sub in ["translate", "trans", "doi", "craft"]:
                        await slash_t_translate.callback(message)
                        return
                    elif sub in ["shards", "shard", "manh", "kho"]:
                        await slash_t_shards.callback(message)
                        return
                    elif sub in ["check", "info"]:
                        await handle_check_character(message, nhan_vat="t1")
                        return
                await slash_t_shards.callback(message)
                return

            if primary_cmd in ["pvp", "duel"]:
                if message.mentions:
                    target = message.mentions[0]
                    await handle_pvp(message, target)
                    return
                else:
                    await message.channel.send("⚠️ Bạn cần tag người muốn thách đấu! Ví dụ: `!pvp @nguoidung`")
                    return

            if primary_cmd in ["trade", "traodoi", "giaodich"]:
                target_user = message.mentions[0] if message.mentions else None
                await handle_trade(message, user=target_user)
                return

    # TỰ ĐỘNG XUẤT HIỆN BOSS REIMU HOẶC SEIKI DỊ HÌNH KHI CHAT (5% TỈ LỆ, HỒI CHIÊU 15P)
    global active_raid, boss_cooldown_until
    current_time = time.time()
    check_and_clean_expired_raid()
    if active_raid is None and current_time >= boss_cooldown_until:
        if random.random() < 0.05 and len(raw_content) > 3 and not used_prefix:
            boss_cooldown_until = current_time + BOSS_CONFIG["cooldown_seconds"]
            chosen_boss = "seiki" if random.random() < 0.50 else "reimu"
            await spawn_boss_raid(message.channel, boss_type=chosen_boss)

    is_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    clean_text = message.clean_content.replace(f"@{bot.user.display_name}", "").strip()

    is_custom_prefix_cmd = False
    if used_prefix:
        first_word = raw_content[len(used_prefix):].strip().split()[0].lower() if raw_content[len(used_prefix):].strip() else ""
        all_registered = set(bot.commands.keys())
        for c in bot.commands.values():
            all_registered.update(c.aliases)
        if first_word in all_registered or first_word in ["boss", "card_info", "cardinfo", "shards", "shard", "t", "the", "pvp", "trade", "traodoi", "giaodich"]:
            is_custom_prefix_cmd = True

    if not is_custom_prefix_cmd and (is_mentioned or is_dm or "reimu" in message.content.lower()):
        async with message.channel.typing():
            history = get_conversation_history(message.channel.id, message.author.id)
            user_msg = f"{message.author.display_name}: {clean_text if clean_text else message.content}"

            contents = []
            for item in history:
                contents.append(types.Content(role=item["role"], parts=[types.Part.from_text(text=item["text"])]))
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_msg)]))

            try:
                reply_text = await ask_gemini(contents, REIMU_SYSTEM_PROMPT, temperature=0.85)
                history.append({"role": "user", "text": user_msg})
                history.append({"role": "model", "text": reply_text})
                save_conversation_history(message.channel.id, message.author.id, history)
                await message.reply(reply_text, mention_author=False)
            except Exception as e:
                err_str = str(e)
                print(f"Gemini API Error: {err_str}", flush=True)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    await message.reply("Mau bỏ tiền vào hòm công đức rồi ta nói chuyện tiếp!", mention_author=False)
                else:
                    await message.reply("Ồn ào quá, để ta yên tĩnh uống trà một lát!", mention_author=False)
        return

    await bot.process_commands(message)

# ==============================================================================
# 8. HỆ THỐNG GACHA PULL TOUHOU
# ==============================================================================
def execute_single_pull():
    roll = random.random()
    if roll < 0.005: rank = "SS"
    elif roll < 0.035: rank = "S"
    elif roll < 0.155: rank = "A"
    elif roll < 0.455: rank = "B"
    else: rank = "C"
    card = random.choice(CARDS_BY_RANK[rank])
    return card, rank

# ==============================================================================
# HỆ THỐNG LỆNH ADMIN ĐỘC QUYỀN (CHỈ DÀNH RIÊNG CHO ID: 1502579398560317441)
# ==============================================================================
@bot.tree.command(name="admin_set_level", description="👑 [ADMIN] Thay đổi cấp độ (Level) của người chơi")
@app_commands.describe(user="Người chơi cần chỉnh cấp độ", level="Cấp độ mới muốn thiết lập (1 - 100)")
async def slash_admin_set_level(interaction: discord.Interaction, user: discord.Member, level: int):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **Từ chối truy cập:** Bạn không có thẩm quyền sử dụng lệnh quản trị này!", ephemeral=True)
        return
    if level < 1 or level > MAX_LEVEL:
        await interaction.response.send_message(f"⚠️ Cấp độ phải nằm trong khoảng từ 1 đến {MAX_LEVEL}!", ephemeral=True)
        return
    p = get_player(user.id, user.display_name)
    old_level = p["level"]
    target_xp = get_total_xp_for_level(level)
    p["xp"] = target_xp
    p["level"] = level
    save_player(p)
    embed = discord.Embed(
        title="👑 [ADMIN] THAY ĐỔI CẤP ĐỘ THÀNH CÔNG!",
        description=(
            f"👤 **Người chơi:** {user.mention}\n"
            f"📊 **Cấp độ:** `Lv.{old_level}` ➔ `Lv.{level}`\n"
            f"✨ **Tổng XP thiết lập:** `{target_xp:,} XP`\n"
            f"⚔️ **Buff chỉ số mới:** `+{get_level_atk_buff(level):,} ATK` | `+{get_level_hp_buff(level):,} HP`"
        ),
        color=0xF59E0B
    )
    embed.set_footer(text=f"Thực hiện bởi Quản trị viên: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_set_level")
async def prefix_admin_set_level(ctx, user: discord.Member = None, level: int = None):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ **Từ chối truy cập:** Bạn không có thẩm quyền sử dụng lệnh này!")
        return
    if not user or level is None:
        await ctx.send("⚠️ Cú pháp đúng: `!admin_set_level @nguoidung <cap_do>` (Ví dụ: `!admin_set_level @User 50`)")
        return
    if level < 1 or level > MAX_LEVEL:
        await ctx.send(f"⚠️ Cấp độ phải nằm trong khoảng từ 1 đến {MAX_LEVEL}!")
        return
    p = get_player(user.id, user.display_name)
    old_level = p["level"]
    target_xp = get_total_xp_for_level(level)
    p["xp"] = target_xp
    p["level"] = level
    save_player(p)
    await ctx.send(f"👑 **[ADMIN]** Đã đổi cấp độ của {user.mention} từ **Lv.{old_level}** thành **Lv.{level}** (`{target_xp:,} XP`)!")

@bot.tree.command(name="admin_confiscate", description="👑 [ADMIN] Thu hồi toàn bộ thẻ bài và vé pull của người chơi")
@app_commands.describe(user="Người chơi cần thu hồi toàn bộ tài nguyên")
async def slash_admin_confiscate(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **Từ chối truy cập:** Bạn không có thẩm quyền sử dụng lệnh quản trị này!", ephemeral=True)
        return
    p = get_player(user.id, user.display_name)
    total_cards = sum(p.get("inventory", {}).values())
    total_tickets = p.get("pull_tickets", 0.0)
    p["inventory"] = {}
    p["team"] = []
    p["pull_tickets"] = 0.0
    p["shards"] = {"seiki": 0}
    save_player(p)
    embed = discord.Embed(
        title="👑 [ADMIN] TỊCH THU TÀI NGUYÊN THÀNH CÔNG!",
        description=(
            f"👤 **Đối tượng:** {user.mention}\n"
            f"🗑️ **Số thẻ đã thu hồi:** `{total_cards:,} thẻ`\n"
            f"🎟️ **Số vé pull đã xóa bỏ:** `{total_tickets:.2f} vé`\n"
            f"🧹 **Đội hình & Kho Mảnh:** Đã dọn sạch hoàn toàn về 0!"
        ),
        color=0xEF4444
    )
    embed.set_footer(text=f"Lệnh trừng phạt thực thi bởi Admin: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_confiscate")
async def prefix_admin_confiscate(ctx, user: discord.Member = None):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ **Từ chối truy cập:** Bạn không có quyền dùng lệnh này!")
        return
    if not user:
        await ctx.send("⚠️ Cú pháp đúng: `!admin_confiscate @nguoidung`")
        return
    p = get_player(user.id, user.display_name)
    total_cards = sum(p.get("inventory", {}).values())
    total_tickets = p.get("pull_tickets", 0.0)
    p["inventory"] = {}
    p["team"] = []
    p["pull_tickets"] = 0.0
    p["shards"] = {"seiki": 0}
    save_player(p)
    await ctx.send(f"👑 **[ADMIN]** Đã tịch thu toàn bộ `{total_cards:,} thẻ`, `{total_tickets:.2f} vé pull` và làm trống đội hình của {user.mention}!")

@bot.tree.command(name="admin_add_card", description="👑 [ADMIN] Cấp phát thẻ bài trực tiếp cho người chơi")
@app_commands.describe(user="Người chơi nhận thẻ bài", card_id="ID hoặc tên thẻ bài (1 - 26 hoặc t1)", amount="Số lượng thẻ muốn cấp phát (Mặc định: 1)")
async def slash_admin_add_card(interaction: discord.Interaction, user: discord.Member, card_id: str, amount: int = 1):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **Từ chối truy cập:** Bạn không có thẩm quyền sử dụng lệnh quản trị này!", ephemeral=True)
        return
    cid = normalize_card_id(card_id)
    if not cid or cid not in CARDS_DATA:
        await interaction.response.send_message("⚠️ ID thẻ không hợp lệ! Vui lòng nhập từ 1 đến 26 hoặc 't1'.", ephemeral=True)
        return
    if amount < 1 or amount > 100:
        await interaction.response.send_message("⚠️ Số lượng cấp phát phải từ 1 đến 100!", ephemeral=True)
        return
    card = CARDS_DATA[cid]
    p = get_player(user.id, user.display_name)
    cid_str = str(cid)
    p["inventory"][cid_str] = p.get("inventory", {}).get(cid_str, 0) + amount
    p["pull_stats"][cid_str] = p.get("pull_stats", {}).get(cid_str, 0) + amount
    if cid not in p.get("unlocked_cards", []):
        p.setdefault("unlocked_cards", []).append(cid)
    save_player(p)
    embed = discord.Embed(
        title="👑 [ADMIN] CẤP PHÁT THẺ BÀI THÀNH CÔNG!",
        description=(
            f"👤 **Người nhận:** {user.mention}\n"
            f"🃏 **Thẻ bài:** **{format_card_id(card['id'])} {card['name']}** `[{card['rank']}]`\n"
            f"📦 **Số lượng cấp:** `+{amount}`\n"
            f"📚 **Tổng sở hữu hiện tại:** `{p['inventory'][cid_str]} thẻ`"
        ),
        color=0x10B981
    )
    if card.get("image"):
        embed.set_thumbnail(url=card["image"])
    embed.set_footer(text=f"Cấp phát bởi Admin: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_add_card")
async def prefix_admin_add_card(ctx, user: discord.Member = None, card_id: str = None, amount: int = 1):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ **Từ chối truy cập:** Bạn không có quyền dùng lệnh này!")
        return
    if not user or not card_id:
        await ctx.send("⚠️ Cú pháp: `!admin_add_card @nguoidung <card_id> [so_luong]` (Ví dụ: `!admin_add_card @User 13 5` hoặc `!admin_add_card @User t1 1`)")
        return
    cid = normalize_card_id(card_id)
    if not cid or cid not in CARDS_DATA:
        await ctx.send("⚠️ ID thẻ không hợp lệ! Vui lòng nhập từ 1 đến 26 hoặc 't1'.")
        return
    card = CARDS_DATA[cid]
    p = get_player(user.id, user.display_name)
    cid_str = str(cid)
    p["inventory"][cid_str] = p.get("inventory", {}).get(cid_str, 0) + amount
    p["pull_stats"][cid_str] = p.get("pull_stats", {}).get(cid_str, 0) + amount
    if cid not in p.get("unlocked_cards", []):
        p.setdefault("unlocked_cards", []).append(cid)
    save_player(p)
    await ctx.send(f"👑 **[ADMIN]** Đã cấp phát thành công **+{amount} thẻ {format_card_id(card['id'])} {card['name']}** `[{card['rank']}]` cho {user.mention}!")

@bot.tree.command(name="admin_add_shard", description="👑 [ADMIN] Cấp phát Mảnh Thẻ Seiki trực tiếp cho người chơi")
@app_commands.describe(user="Người chơi nhận mảnh", amount="Số lượng Mảnh Seiki muốn cấp phát (Mặc định: 1)")
async def slash_admin_add_shard(interaction: discord.Interaction, user: discord.Member, amount: int = 1):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **Từ chối truy cập:** Bạn không có thẩm quyền sử dụng lệnh quản trị này!", ephemeral=True)
        return
    if amount < 1 or amount > 100:
        await interaction.response.send_message("⚠️ Số lượng mảnh cấp phát phải từ 1 đến 100!", ephemeral=True)
        return
    p = get_player(user.id, user.display_name)
    shards_dict = p.setdefault("shards", {})
    shards_dict["seiki"] = shards_dict.get("seiki", 0) + amount
    save_player(p)
    cur = shards_dict["seiki"]
    embed = discord.Embed(
        title="👑 [ADMIN] CẤP PHÁT MẢNH SEIKI THÀNH CÔNG!",
        description=(
            f"👤 **Người nhận:** {user.mention}\n"
            f"🔮 **Vật phẩm:** **Mảnh Seiki Đệ Pháp Toàn Năng**\n"
            f"📦 **Số lượng cấp:** `+{amount} Mảnh`\n"
            f"🏺 **Kho hiện tại:** `{cur}/10 Mảnh`" + (" *(Đã đủ 10 mảnh! Dùng `/t translate` để ghép)*" if cur >= 10 else "")
        ),
        color=0x7C3AED
    )
    embed.set_footer(text=f"Cấp phát bởi Admin: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_add_shard")
async def prefix_admin_add_shard(ctx, user: discord.Member = None, amount: int = 1):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ **Từ chối truy cập:** Bạn không có quyền dùng lệnh này!")
        return
    if not user:
        await ctx.send("⚠️ Cú pháp: `!admin_add_shard @nguoidung [so_luong]` (Ví dụ: `!admin_add_shard @User 10`)")
        return
    p = get_player(user.id, user.display_name)
    shards_dict = p.setdefault("shards", {})
    shards_dict["seiki"] = shards_dict.get("seiki", 0) + amount
    save_player(p)
    cur = shards_dict["seiki"]
    await ctx.send(f"👑 **[ADMIN]** Đã cấp phát thành công **+{amount} Mảnh Seiki** cho {user.mention} (Hiện có: `{cur}/10 Mảnh`)!")

@bot.tree.command(name="admin_lock", description="🔒 [ADMIN] Khóa thẻ của người chơi, gỡ khỏi team (chỉ mở khi pull lại)")
@app_commands.describe(user="Người chơi cần khóa thẻ", card_id="ID thẻ muốn khóa (1 - 26 hoặc t1)")
async def slash_admin_lock(interaction: discord.Interaction, user: discord.Member, card_id: str):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **Từ chối truy cập:** Bạn không có quyền dùng lệnh quản trị này!", ephemeral=True)
        return
    cid = normalize_card_id(card_id)
    if not cid or cid not in CARDS_DATA:
        await interaction.response.send_message("⚠️ ID thẻ không hợp lệ! Vui lòng nhập từ 1 đến 26 hoặc 't1'.", ephemeral=True)
        return
    card = CARDS_DATA[cid]
    p = get_player(user.id, user.display_name)
    locked_list = p.setdefault("locked_cards", [])
    if cid not in locked_list and str(cid) not in locked_list:
        locked_list.append(cid)
    # Gỡ thẻ khỏi đội hình
    if "team" in p:
        p["team"] = [c for c in p["team"] if str(c).lower() != str(cid).lower()]
    save_player(p)
    embed = discord.Embed(
        title="🔒 [ADMIN] KHÓA THẺ THÀNH CÔNG!",
        description=(
            f"👤 **Người chơi:** {user.mention}\n"
            f"🃏 **Thẻ bị khóa:** **{format_card_id(card['id'])} {card['name']}** `[{card['rank']}]`\n"
            f"🚫 **Trạng thái:** Đã gỡ khỏi đội hình chiến đấu.\n"
            f"🔓 **Điều kiện mở:** Thẻ này sẽ **BỊ KHÓA HOÀN TOÀN** cho đến khi người chơi này **quay gacha pull trúng lại** thẻ đó!"
        ),
        color=0xEF4444
    )
    if card.get("image"):
        embed.set_thumbnail(url=card["image"])
    embed.set_footer(text=f"Thực thi bởi Admin: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_lock")
async def prefix_admin_lock(ctx, user: discord.Member = None, card_id: str = None):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ **Từ chối truy cập:** Bạn không có quyền dùng lệnh này!")
        return
    if not user or not card_id:
        await ctx.send("⚠️ Cú pháp: `!admin_lock @nguoidung <card_id>` (Ví dụ: `!admin_lock @User 13` hoặc `!admin_lock @User t1`)")
        return
    cid = normalize_card_id(card_id)
    if not cid or cid not in CARDS_DATA:
        await ctx.send("⚠️ ID thẻ không hợp lệ! Vui lòng nhập từ 1 đến 26 hoặc 't1'.")
        return
    card = CARDS_DATA[cid]
    p = get_player(user.id, user.display_name)
    locked_list = p.setdefault("locked_cards", [])
    if cid not in locked_list and str(cid) not in locked_list:
        locked_list.append(cid)
    if "team" in p:
        p["team"] = [c for c in p["team"] if str(c).lower() != str(cid).lower()]
    save_player(p)
    await ctx.send(f"🔒 **[ADMIN]** Đã khóa thành công thẻ **{format_card_id(card['id'])} {card['name']}** của {user.mention}! Thẻ đã bị gỡ khỏi team và chỉ mở lại khi pull trúng!")

@bot.tree.command(name="admin_reset_daily_quest", description="👑 [ADMIN] Reset ngay lập tức 3/3 Nhiệm vụ Ngày cho bản thân hoặc người chơi")
@app_commands.describe(user="Người chơi cần reset nhiệm vụ ngày (Để trống nếu tự reset cho bản thân)")
async def slash_admin_reset_daily_quest(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **Từ chối truy cập:** Bạn không có thẩm quyền sử dụng lệnh quản trị này!", ephemeral=True)
        return
    target_user = user or interaction.user
    p = get_player(target_user.id, target_user.display_name)
    ensure_daily_quests(p, force_reset=True)
    save_player(p)
    embed = discord.Embed(
        title="👑 [ADMIN] ĐÃ RESET 3/3 NHIỆM VỤ NGÀY!",
        description=(
            f"👤 **Đối tượng:** {target_user.mention}\n"
            f"📅 **Ngày áp dụng:** `{get_today_vn()}` (GMT+7)\n"
            f"🎯 **Trạng thái:** Đã tạo mới hoàn toàn 3 nhiệm vụ ngày chưa hoàn thành.\n"
            f"🎟️ **Phần thưởng:** Có thể tiếp tục làm để tích lũy vé pull và nhận thêm **+10 vé pull thưởng mốc**!"
        ),
        color=0x10B981
    )
    embed.set_footer(text=f"Reset bởi Admin: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_reset_daily_quest")
async def prefix_admin_reset_daily_quest(ctx, user: discord.Member = None):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ **Từ chối truy cập:** Bạn không có quyền dùng lệnh này!")
        return
    target_user = user or ctx.author
    p = get_player(target_user.id, target_user.display_name)
    ensure_daily_quests(p, force_reset=True)
    save_player(p)
    await ctx.send(f"👑 **[ADMIN]** Đã reset thành công 3/3 nhiệm vụ ngày cho {target_user.mention}! Gõ `/daily_quest` để kiểm tra.")

# ==============================================================================
# HỆ THỐNG TIẾN HÓA THẺ BÀI (EVOL ACE 2 ⭐⭐ - KÈM ID NHÂN VẬT & DIRECT GIF)
# ==============================================================================
class EvolSelectView(discord.ui.View):
    def __init__(self, user_id, evol_options):
        super().__init__(timeout=60)
        self.user_id = user_id
        options = []
        for opt in evol_options:
            options.append(discord.SelectOption(
                label=opt["title"],
                value=str(opt["id"]),
                description=f"Yêu cầu: {opt['curr_cards']}/{opt['req_cards']} thẻ | {opt['curr_pulls']}/{opt['req_pulls']} lần pull"
            ))
        select_menu = discord.ui.Select(placeholder="🔽 Chọn nhân vật muốn tiến hóa lên Ace 2...", options=options)
        select_menu.callback = self.select_callback
        self.add_item(select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Bạn không thể tương tác với menu của người khác!", ephemeral=True)
            return
        cid = int(interaction.data["values"][0])
        await do_evolve_interaction(interaction, cid)

def execute_card_evolution(player: dict, card_id: int):
    cfg = EVOL_CONFIG.get(card_id)
    if not cfg:
        return False, "Nhân vật này hiện chưa mở tính năng tiến hóa Ace 2!"
    cid_str = str(card_id)
    if player.get("evolutions", {}).get(cid_str, 0) >= 2:
        return False, f"**{cfg['title']}** đã đạt trạng thái Ace 2 tối thượng rồi!"
    curr_cards = player.get("inventory", {}).get(cid_str, 0)
    curr_pulls = player.get("pull_stats", {}).get(cid_str, 0)
    if curr_cards < cfg["required_cards"]:
        return False, f"Chưa đủ thẻ bài! Cần **{cfg['required_cards']} thẻ** (Hiện có: `{curr_cards}/{cfg['required_cards']}`)."
    if curr_pulls < cfg["required_pulls"]:
        return False, f"Chưa đủ số lần pull trúng! Cần pull trúng **{cfg['required_pulls']} lần** (Hiện tại: `{curr_pulls}/{cfg['required_pulls']}`)."

    player["inventory"][cid_str] -= cfg["required_cards"]
    player.setdefault("evolutions", {})[cid_str] = 2
    save_player(player)
    return True, cfg

async def do_evolve_interaction(interaction_or_ctx, cid: int):
    author = interaction_or_ctx.user if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author
    p = get_player(author.id, author.display_name)
    success, res = execute_card_evolution(p, cid)
    if not success:
        if isinstance(interaction_or_ctx, discord.Interaction):
            await interaction_or_ctx.response.send_message(f"❌ {res}", ephemeral=True)
        else:
            await interaction_or_ctx.send(f"❌ {res}")
        return

    cfg = res
    embed = discord.Embed(
        title=f"✨ TIẾN HÓA THÀNH CÔNG: {cfg['title']}!",
        description=(
            f"🎉 Chúc mừng {author.mention} đã thức tỉnh cảnh giới tối thượng **{cfg['ace_level']}**!\n\n"
            f"💥 **BUFF CHỈ SỐ TỐI THƯỢNG (ÁP DỤNG TOÀN BỘ ACE):**\n"
            f"• ⚔️ **Sức mạnh (ATK):** **+{cfg['bonus_power']} DMG**!\n"
            f"• ❤️ **Sinh mệnh (HP):** **+{cfg['bonus_hp']} HP**!\n\n"
            f"🌟 **KỸ NĂNG ĐỘC QUYỀN:**\n"
            f"**{cfg['skill_name']}**\n"
            f"*{cfg['skill_desc']}*"
        ),
        color=0xF59E0B
    )
    embed.set_image(url=cfg["evol_gif"])
    embed.set_footer(text=f"Tiến hóa thành công • Tiêu thụ {cfg['required_cards']} thẻ bài • Giữ nguyên tổng số lần pull")

    if isinstance(interaction_or_ctx, discord.Interaction):
        await interaction_or_ctx.response.send_message(embed=embed)
        await interaction_or_ctx.followup.send(cfg["evol_gif"])
    else:
        await interaction_or_ctx.send(embed=embed)
        await interaction_or_ctx.send(cfg["evol_gif"])

async def handle_evol(ctx_or_interaction, nhan_vat: Optional[str] = None):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)

    if nhan_vat:
        target_cid = None
        s = nhan_vat.strip().lower().replace("#", "")
        if s in ["13", "reimu", "reimu hakurei"]: target_cid = 13
        elif s in ["16", "sakuya", "sakuya izayoi"]: target_cid = 16
        elif s in ["17", "marisa", "marisa kirisame"]: target_cid = 17

        if target_cid:
            await do_evolve_interaction(ctx_or_interaction, target_cid)
            return

    evol_options = []
    for cid in [13, 16, 17]:
        cfg = EVOL_CONFIG[cid]
        curr_cards = p.get("inventory", {}).get(str(cid), 0)
        curr_pulls = p.get("pull_stats", {}).get(str(cid), 0)
        is_ace2 = p.get("evolutions", {}).get(str(cid), 0) >= 2
        status_tag = " [ĐÃ ACE 2 ⭐⭐]" if is_ace2 else (" [ĐỦ ĐIỀU KIỆN!]" if (curr_cards >= cfg["required_cards"] and curr_pulls >= cfg["required_pulls"]) else "")
        evol_options.append({
            "id": cid,
            "title": f"{cfg['title']}{status_tag}",
            "req_cards": cfg["required_cards"],
            "req_pulls": cfg["required_pulls"],
            "curr_cards": curr_cards,
            "curr_pulls": curr_pulls,
            "is_ace2": is_ace2
        })

    embed = discord.Embed(
        title="🌟 ĐỀN HAKUREI - HỆ THỐNG TIẾN HÓA THẺ BÀI (ACE 2 ⭐⭐)",
        description=(
            f"Chào {author.mention}! Khi thu thập đủ số lượng thẻ và pull đạt mốc, "
            f"bạn có thể thức tỉnh nhân vật lên **Ace 2 ⭐⭐** với **hoạt ảnh GIF trực tiếp** và **kỹ năng bá đạo**!\n\n"
            f"🔥 **BUFF TỐI THƯỢNG ACE MỚI:** Mọi nhân vật đạt Ace 2 đều nhận **+{ACE_POWER_BUFF} ATK** và **+{ACE_HP_BUFF} HP**!\n\n"
            "📜 **Danh sách nhân vật hỗ trợ Ace 2 hiện tại:**\n"
        ),
        color=0xF59E0B
    )

    for opt in evol_options:
        tag = "⭐ **ĐÃ ĐẠT ACE 2 ⭐⭐**" if opt["is_ace2"] else f"`{opt['curr_cards']}/{opt['req_cards']}` Thẻ | `{opt['curr_pulls']}/{opt['req_pulls']}` Lần Pull"
        embed.add_field(
            name=opt["title"],
            value=f"• Tiến độ: {tag}\n• Kỹ năng: *{EVOL_CONFIG[opt['id']]['skill_name']}*\n• Buff chỉ số: **+{ACE_POWER_BUFF} ATK** & **+{ACE_HP_BUFF} HP**",
            inline=False
        )
    embed.set_footer(text="Chọn nhân vật từ Menu bên dưới để tiến hóa hoặc nhập ID: /evol nhan_vat:13")

    view = EvolSelectView(author.id, evol_options)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="evol", description="🌟 Tiến hóa thẻ bài Touhou lên trạng thái Ace 2 ⭐⭐ (Kèm ID & Hoạt ảnh GIF)")
@app_commands.describe(nhan_vat="Nhập ID nhân vật (13, 16, 17) hoặc tên (Reimu, Sakuya, Marisa)")
async def slash_evol(interaction: discord.Interaction, nhan_vat: Optional[str] = None):
    await handle_evol(interaction, nhan_vat)

@bot.command(name="evol", aliases=["tienhoa", "ace"])
async def prefix_evol(ctx, *, nhan_vat: str = None):
    await handle_evol(ctx, nhan_vat)

# ==============================================================================
# HỆ THỐNG LỆNH CHÍNH (GACHA, BATTLE, DAILY, TEAM, CHECK...)
# ==============================================================================
async def handle_pull(ctx_or_interaction, amount: int = 1):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    now_date = get_today_vn()

    # TỰ ĐỘNG RESET 5 LƯỢT FREE KHI SANG NGÀY MỚI (GMT+7)
    if p.get("free_pulls_date") != now_date:
        p["free_pulls_date"] = now_date
        p["free_pulls_remaining"] = 5

    # VÁ LỖI TUTORIAL BẢO MẬT: BẢO ĐẢM TIẾN TRÌNH TUYẾN TÍNH CHỐNG BUG FARM FULL S
    tut = p.get("tutorial", {})
    if tut.get("active", False) and not tut.get("completed", False):
        if tut.get("step") == "pull":
            # CHỐNG BUG FARM: NẾU ĐÃ SỬ DỤNG 1 LẦN PULL TÂN THỦ RỒI THÌ KHÔNG CHO ROLL NỮA!
            if tut.get("pull_used", False):
                msg_err = (
                    "⚠️ **BẠN ĐÃ HOÀN THÀNH LƯỢT QUAY TÂN THỦ RỒI!**\n"
                    "👉 Bước tiếp theo của bạn là sắp xếp đội hình: Hãy gõ `/team` để vào hướng dẫn tiếp theo!"
                )
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(msg_err, ephemeral=True)
                else:
                    await ctx_or_interaction.send(msg_err)
                return

            # CẤP 3 THẺ CỐ ĐỊNH BAN ĐẦU: REIMU (#13), MARISA (#17), CIRNO (#21)
            fixed_cards = [CARDS_DATA[13], CARDS_DATA[17], CARDS_DATA[21]]
            unlocked_set = set(p.get("unlocked_cards", []))

            for card in fixed_cards:
                cid_str = str(card["id"])
                p["inventory"][cid_str] = p.get("inventory", {}).get(cid_str, 0) + 1
                p["pull_stats"][cid_str] = p.get("pull_stats", {}).get(cid_str, 0) + 1
                unlocked_set.add(card["id"])

            p["unlocked_cards"] = list(unlocked_set)
            tut["pull_used"] = True  # ĐÁNH DẤU CỜ VĨNH VIỄN
            tut["quest_pulls_remaining"] = 0
            tut["step"] = "team"
            save_player(p)

            embed = discord.Embed(
                title="🎁 QUAY TÂN THỦ THÀNH CÔNG (KHỞI ĐẦU GENSOKYO)!",
                description=(
                    f"Chúc mừng {author.mention} đã nhận được **3 Thẻ Bài Tân Thủ Độc Quyền**:\n"
                    "• **[#13] Reimu Hakurei** `[Rank A]`\n"
                    "• **[#17] Marisa Kirisame** `[Rank A]`\n"
                    "• **[#21] Cirno** `[Rank B]`\n\n"
                    "🎯 **BƯỚC TIẾP THEO:**\n"
                    "Hãy gõ `/team` hoặc `!team` để kiểm tra và thiết lập đội hình xuất trận!"
                ),
                color=0x10B981
            )
            embed.set_thumbnail(url=CARDS_DATA[13]["image"])
            embed.set_footer(text="Nhiệm vụ tân thủ 1/3 hoàn tất • Tiếp theo: /team")

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return

    free_avail = p.get("free_pulls_remaining", 0)
    tickets = p.get("pull_tickets", 0.0)
    total_avail = free_avail + int(tickets)

    if amount < 1:
        msg = "Số lượt pull tối thiểu là 1!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if amount > 10:
        msg = "Bạn chỉ có thể quay tối đa 10 lượt một lần!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if total_avail < amount:
        time_left_str = format_time_until_midnight_vn()
        msg = (
            f"❌ Bạn không đủ lượt pull! (Yêu cầu: {amount}, Hiện có: {free_avail} lượt miễn phí + {tickets:.2f} vé pull).\n"
            f"💡 Bạn nhận 5 lượt miễn phí mỗi ngày (Làm mới sau: **{time_left_str}**)! "
            f"Hoặc kiếm vé qua `/daily`, hoàn thành `/daily_quest`, chiến thắng `/battle`, hoặc tham gia Raid Boss!"
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    rem = amount
    used_free = min(free_avail, rem)
    p["free_pulls_remaining"] -= used_free
    rem -= used_free

    if rem > 0:
        p["pull_tickets"] -= float(rem)

    results = []
    best_card = None
    rank_order = {"SS": 5, "S": 4, "A": 3, "B": 2, "C": 1}

    unlocked_set = set(p.get("unlocked_cards", []))
    locked_list = p.get("locked_cards", [])
    unlocked_msg_list = []

    for _ in range(amount):
        card, rank = execute_single_pull()
        cid_str = str(card["id"])
        p["inventory"][cid_str] = p.get("inventory", {}).get(cid_str, 0) + 1
        p["pull_stats"][cid_str] = p.get("pull_stats", {}).get(cid_str, 0) + 1
        results.append((card, rank))
        unlocked_set.add(card["id"])

        # MỞ KHÓA NẾU THẺ NÀY ĐANG BỊ ADMIN KHÓA
        if card["id"] in locked_list or cid_str in locked_list:
            p["locked_cards"] = [x for x in locked_list if str(x) != cid_str and str(x) != str(card["id"])]
            locked_list = p["locked_cards"]
            unlocked_msg_list.append(f"🔓 **Kỳ tích!** Bạn đã pull trúng lại **{format_card_id(card['id'])} {card['name']}**, thẻ đã được TỰ ĐỘNG GIẢI MÃ KHÓA!")

        if not best_card or rank_order[rank] > rank_order[best_card[1]["rank"]]:
            best_card = (card, rank)

    p["unlocked_cards"] = list(unlocked_set)

    # TIẾN ĐỘ NHIỆM VỤ NGÀY CHO HÀNH ĐỘNG PULL
    quest_notifs = update_daily_quest_progress(p, "pull", amount)
    save_player(p)

    lines = []
    for c, r in results:
        count = p["inventory"].get(str(c["id"]), 1)
        is_dup = (count > 1)
        dup_str = f" *(Trùng x{count})*" if is_dup else " ✨ *(Mới!)*"
        lines.append(f"• **[{r}]** **{format_card_id(c['id'])} {c['name']}** (⚔️{c['power']:,} | ❤️{c['hp']:,}){dup_str}")

    embed = discord.Embed(
        title=f"⛩️ KẾT QUẢ GACHA ({amount} LƯỢT QUAY)",
        description="\n".join(lines),
        color=0x3B82F6 if amount > 1 else 0x10B981
    )
    if best_card and best_card[0].get("image"):
        embed.set_thumbnail(url=best_card[0]["image"])

    rem_free = p["free_pulls_remaining"]
    rem_tick = p["pull_tickets"]
    embed.set_footer(text=f"Còn lại: {rem_free} lượt miễn phí hôm nay | {rem_tick:.2f} vé pull")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
        if unlocked_msg_list:
            await ctx_or_interaction.followup.send("\n".join(unlocked_msg_list))
        if quest_notifs:
            await ctx_or_interaction.followup.send("\n".join(quest_notifs))
    else:
        await ctx_or_interaction.send(embed=embed)
        if unlocked_msg_list:
            await ctx_or_interaction.send("\n".join(unlocked_msg_list))
        if quest_notifs:
            await ctx_or_interaction.send("\n".join(quest_notifs))

@bot.tree.command(name="pull", description="⛩️ Quay thẻ bài Touhou ngẫu nhiên (Dùng lượt miễn phí hoặc Vé Pull)")
@app_commands.describe(amount="Số lượt muốn quay (Từ 1 đến 10, mặc định: 1)")
async def slash_pull(interaction: discord.Interaction, amount: int = 1):
    await handle_pull(interaction, amount)

@bot.command(name="pull", aliases=["gacha", "quay"])
async def prefix_pull(ctx, amount: int = 1):
    await handle_pull(ctx, amount)

async def handle_daily(ctx_or_interaction):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    now_date = get_today_vn()

    if p.get("last_daily_date") == now_date:
        time_left_str = format_time_until_midnight_vn()
        msg = f"⏳ Bạn đã điểm danh hôm nay rồi! Hãy quay lại sau **{time_left_str}** (làm mới lúc 00:00 GMT+7) nhé!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    p["last_daily_date"] = now_date
    p["pull_tickets"] += 1.0
    p["xp"] += 50
    quest_notifs = update_daily_quest_progress(p, "daily", 1)
    save_player(p)

    embed = discord.Embed(
        title="⛩️ ĐIỂM DANH ĐỀN HAKUREI THÀNH CÔNG!",
        description=(
            f"Chào buổi sáng, {author.mention}! Cảm ơn bạn đã ghé thăm đền Hakurei.\n\n"
            "🎁 **Phần thưởng điểm danh hôm nay:**\n"
            "• **+1 Vé Pull Gacha** 🎟️\n"
            "• **+50 Điểm Kinh Nghiệm (XP)** ⭐\n"
            f"• Tài khoản hiện có: **{p['pull_tickets']:.2f} Vé Pull**\n"
            f"• Đẳng cấp hiện tại: **Lv.{p['level']}** (`{p['xp']:,} XP`)"
        ),
        color=0x10B981
    )
    embed.set_footer(text="Điểm danh mỗi ngày để nhận Vé Pull & XP tăng chiến lực!")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
        if quest_notifs:
            await ctx_or_interaction.followup.send("\n".join(quest_notifs))
    else:
        await ctx_or_interaction.send(embed=embed)
        if quest_notifs:
            await ctx_or_interaction.send("\n".join(quest_notifs))

@bot.tree.command(name="daily", description="⛩️ Điểm danh nhận thưởng hàng ngày (+1 Vé Pull, +50 XP)")
async def slash_daily(interaction: discord.Interaction):
    await handle_daily(interaction)

@bot.command(name="daily", aliases=["diemdanh"])
async def prefix_daily(ctx):
    await handle_daily(ctx)

async def handle_team(ctx_or_interaction, action: str = "view", id_the: Optional[str] = None):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    lvl_buff_pwr = get_level_atk_buff(p["level"])
    lvl_buff_hp = get_level_hp_buff(p["level"])

    # XỬ LÝ NHIỆM VỤ TÂN THỦ BƯỚC 2 (/team)
    tut = p.get("tutorial", {})
    tut_notice = None
    if tut.get("active", False) and not tut.get("completed", False):
        if tut.get("step") == "team":
            # TỰ ĐỘNG THIẾT LẬP 3 THẺ KHỞI ĐẦU VÀO ĐỘI HÌNH
            p["team"] = [13, 17, 21]
            tut["step"] = "battle"
            save_player(p)
            tut_notice = (
                "🎉 **HOÀN THÀNH BƯỚC 2 TÂN THỦ: THIẾT LẬP ĐỘI HÌNH!**\n"
                "⛩️ **Reimu:** *\"Đội hình 3 người [#13 Reimu, #17 Marisa, #21 Cirno] đã sẵn sàng chiến đấu!\"*\n"
                "👉 **BƯỚC CUỐI CÙNG:** Hãy gõ `/battle` hoặc `!battle` để nghênh chiến thử thách đầu tiên!"
            )

    action = action.lower() if action else "view"

    if action == "clear":
        p["team"] = []
        save_player(p)
        msg = "🧹 Đã xóa toàn bộ thẻ bài khỏi đội hình chiến đấu!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else: await ctx_or_interaction.send(msg)
        return

    if action == "add":
        if not id_the:
            msg = "⚠️ Vui lòng nhập ID thẻ muốn thêm! Ví dụ: `/team action:add id_the:13` hoặc `!team add 13` (hoặc `t1` cho Thẻ Seiki)"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        cid = normalize_card_id(id_the)
        if not cid or cid not in CARDS_DATA:
            msg = "⚠️ ID thẻ không hợp lệ! Hãy kiểm tra kho thẻ qua lệnh `/collection`."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        if is_card_locked(p, cid):
            msg = f"⛔ **Thẻ #{format_card_id(cid)} đang bị KHÓA!** Bạn không thể đưa thẻ bị khóa vào đội hình (Hãy pull lại để mở khóa)."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        if not is_card_unlocked(p, cid):
            msg = f"⚠️ Bạn chưa sở hữu thẻ **{format_card_id(cid)}**! Hãy dùng `/pull` để tìm kiếm nhé."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        current_team = p.get("team", [])
        if any(str(x).lower() == str(cid).lower() for x in current_team):
            msg = f"⚠️ Thẻ **{format_card_id(cid)}** đã có sẵn trong đội hình rồi!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        if len(current_team) >= 3:
            msg = "⚠️ Đội hình tối đa chỉ chứa 3 thẻ bài! Hãy gõ `/team action:clear` hoặc `/team action:remove` trước."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        current_team.append(cid)
        p["team"] = current_team
        save_player(p)
        c_info = CARDS_DATA[cid]
        msg = f"✅ Đã thêm **{format_card_id(c_info['id'])} {c_info['name']}** vào đội hình! ({len(current_team)}/3)"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else: await ctx_or_interaction.send(msg)
        return

    if action == "remove":
        if not id_the:
            msg = "⚠️ Vui lòng nhập ID thẻ muốn gỡ khỏi đội hình! Ví dụ: `/team action:remove id_the:13`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        cid = normalize_card_id(id_the)
        current_team = p.get("team", [])
        matched = None
        for x in current_team:
            if str(x).lower() == str(cid).lower() or str(x).lower() == str(id_the).lower():
                matched = x
                break

        if not matched:
            msg = f"⚠️ Thẻ **{id_the}** không có trong đội hình hiện tại!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        current_team.remove(matched)
        p["team"] = current_team
        save_player(p)
        msg = f"✅ Đã gỡ thẻ **{format_card_id(matched)}** khỏi đội hình! ({len(current_team)}/3)"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else: await ctx_or_interaction.send(msg)
        return

    # CHẾ ĐỘ VIEW (XEM ĐỘI HÌNH)
    team_cids = p.get("team", [])
    valid_cids = [cid for cid in team_cids if cid in CARDS_DATA]

    embed = discord.Embed(
        title=f"🛡️ ĐỘI HÌNH XUẤT TRẬN: {author.display_name} (Lv.{p['level']})",
        description=(
            f"Tổng số vị trí: **{len(valid_cids)}/3 thẻ**\n"
            f"⭐ **Buff Cấp Độ Hiện Tại (Lv.{p['level']}):** `+{lvl_buff_pwr:,} ATK` | `+{lvl_buff_hp:,} HP`\n"
            f"🔥 **Buff Ace 2 (Nếu đạt):** `+{ACE_POWER_BUFF:,} ATK` | `+{ACE_HP_BUFF:,} HP`"
        ),
        color=0x3B82F6
    )

    if not valid_cids:
        embed.add_field(
            name="⚠️ Đội hình đang trống!",
            value=(
                "Bạn chưa cài đặt thẻ nào vào đội hình!\n"
                "• Dùng `/team action:add id_the:<ID>` để thêm thẻ.\n"
                "• Hoặc khi tham gia Battle/Raid, hệ thống sẽ tự động xếp 3 thẻ mạnh nhất của bạn."
            ),
            inline=False
        )
    else:
        tot_power = 0
        tot_hp = 0
        for i, cid in enumerate(valid_cids):
            c = CARDS_DATA[cid]
            is_ace2 = is_card_ace2(p, cid)
            is_locked = is_card_locked(p, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
            ace_hp = ACE_HP_BUFF if is_ace2 else 0
            card_pwr = c["power"] + lvl_buff_pwr + ace_pwr
            card_hp = c["hp"] + lvl_buff_hp + ace_hp
            tot_power += card_pwr
            tot_hp += card_hp
            ace_tag = " ⭐⭐ `[TIẾN HÓA ACE 2]`" if is_ace2 else ""
            locked_tag = " 🔒 `[ĐANG BỊ KHÓA]`" if is_locked else ""
            embed.add_field(
                name=f"Vị trí #{i+1}: {format_card_id(c['id'])} {c['name']} [{c['rank']}]{ace_tag}{locked_tag}",
                value=f"• ⚔️ **Sức mạnh:** `{card_pwr:,} DMG` *(Gốc: {c['power']:,})*\n• ❤️ **Sinh mệnh:** `{card_hp:,} HP` *(Gốc: {c['hp']:,})*",
                inline=False
            )
        embed.add_field(
            name="📊 Tổng Lực Chiến Đội Hình:",
            value=f"⚔️ **Tổng Công:** `{tot_power:,} DMG` | ❤️ **Tổng Thủ:** `{tot_hp:,} HP`",
            inline=False
        )

    embed.set_footer(text="Sử dụng: /team add <id> | /team remove <id> | /team clear")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
        if tut_notice:
            await ctx_or_interaction.followup.send(tut_notice)
    else:
        await ctx_or_interaction.send(embed=embed)
        if tut_notice:
            await ctx_or_interaction.send(tut_notice)

@bot.tree.command(name="team", description="🛡️ Quản lý và thiết lập đội hình 3 thẻ bài xuất trận")
@app_commands.describe(action="Hành động: view (xem), add (thêm), remove (gỡ), clear (xóa hết)", id_the="ID thẻ bài (1 - 26 hoặc t1)")
@app_commands.choices(action=[
    app_commands.Choice(name="Xem đội hình hiện tại", value="view"),
    app_commands.Choice(name="Thêm thẻ vào đội hình", value="add"),
    app_commands.Choice(name="Gỡ thẻ khỏi đội hình", value="remove"),
    app_commands.Choice(name="Xóa toàn bộ đội hình", value="clear")
])
async def slash_team(interaction: discord.Interaction, action: str = "view", id_the: Optional[str] = None):
    await handle_team(interaction, action, id_the)

@bot.command(name="team", aliases=["doihinh", "doi"])
async def prefix_team(ctx, action: str = "view", id_the: str = None):
    await handle_team(ctx, action, id_the)

async def handle_collection(ctx_or_interaction, page: int = 1):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    inv = p.get("inventory", {})

    all_cards = list(CARDS_DATA.values())
    total_distinct = len([c for c in all_cards if inv.get(str(c["id"]), 0) > 0])
    total_cards_count = sum(inv.values())

    per_page = 8
    max_page = (len(all_cards) + per_page - 1) // per_page
    page = max(1, min(page, max_page))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_cards = all_cards[start_idx:end_idx]

    embed = discord.Embed(
        title=f"📚 KHO BỘ SƯU TẬP THẺ BÀI: {author.display_name}",
        description=(
            f"👤 **Cấp độ người chơi:** `Lv.{p['level']}` (`{p['xp']:,} XP`)\n"
            f"🃏 **Sở hữu:** `{total_distinct}/{len(all_cards)} nhân vật` (Tổng `{total_cards_count:,} thẻ`)\n"
            f"🎟️ **Vé Pull tích lũy:** `{p['pull_tickets']:.2f} vé`\n"
            f"🔮 **Mảnh Seiki:** `{p.get('shards', {}).get('seiki', 0)}/10 Mảnh` *(10 mảnh = 1 Thẻ Seiki T1)*"
        ),
        color=0x3B82F6
    )

    for c in page_cards:
        cid_str = str(c["id"])
        count = inv.get(cid_str, 0)
        is_ace2 = is_card_ace2(p, c["id"])
        is_locked = is_card_locked(p, c["id"])
        status = f"✅ Đang có: **x{count}**" if count > 0 else "❌ *Chưa mở khóa*"
        ace_tag = " ⭐⭐ `[ACE 2]`" if is_ace2 else ""
        locked_tag = " 🔒 `[BỊ KHÓA]`" if is_locked else ""
        embed.add_field(
            name=f"{format_card_id(c['id'])} {c['name']} [{c['rank']}]{ace_tag}{locked_tag}",
            value=f"{status}\n⚔️ ATK: `{c['power']:,}` | ❤️ HP: `{c['hp']:,}`",
            inline=True
        )

    embed.set_footer(text=f"Trang {page}/{max_page} • Gõ /collection page:{page+1} để xem trang kế tiếp")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="collection", description="📚 Xem toàn bộ kho thẻ bài Touhou đã thu thập")
@app_commands.describe(page="Trang muốn xem (Mặc định: 1)")
async def slash_collection(interaction: discord.Interaction, page: int = 1):
    await handle_collection(interaction, page)

@bot.command(name="collection", aliases=["kho", "tuido", "cards"])
async def prefix_collection(ctx, page: int = 1):
    await handle_collection(ctx, page)

# ==============================================================================
# HỆ THỐNG MẢNH THẺ BÀI (SHARD SYSTEM) & CHUYỂN ĐỔI THẺ NHÓM T
# ==============================================================================
async def handle_translate_shard(ctx_or_interaction):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    shards_dict = p.setdefault("shards", {})
    seiki_shards = shards_dict.get("seiki", 0)

    if seiki_shards < 10:
        msg = (
            f"❌ **Chưa đủ Mảnh Seiki!**\n"
            f"Bạn hiện chỉ có: **`{seiki_shards}/10 Mảnh Seiki`**.\n"
            f"💡 Hãy tham gia diệt Boss Raid (Tỉ lệ 2.5% rơi mỗi trận) hoặc nhận từ sự kiện để tích lũy đủ 10 mảnh nhé!"
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # TIẾN HÀNH QUY ĐỔI 10 MẢNH THÀNH 1 THẺ T1 SEIKI
    shards_dict["seiki"] -= 10
    cid_str = "t1"
    p["inventory"][cid_str] = p.get("inventory", {}).get(cid_str, 0) + 1
    p["pull_stats"][cid_str] = p.get("pull_stats", {}).get(cid_str, 0) + 1
    if "t1" not in p.get("unlocked_cards", []):
        p.setdefault("unlocked_cards", []).append("t1")
    save_player(p)

    c_info = CARDS_DATA["t1"]
    embed = discord.Embed(
        title="✨ QUY ĐỔI MẢNH THÀNH CÔNG: THẺ BÀI HUYỀN THOẠI NHÓM T!",
        description=(
            f"🎉 Chúc mừng {author.mention} đã tập hợp đủ **10 Mảnh Seiki** và khai mở sức mạnh tối thượng!\n\n"
            f"🃏 **Thẻ Nhận Được:** **{format_card_id(c_info['id'])} {c_info['name']}** `[Rank T]`\n"
            f"⚔️ **Chỉ số:** Sức mạnh `{c_info['power']:,} ATK` | Sinh mệnh `{c_info['hp']:,} HP`\n\n"
            f"🔮 **Kỹ Năng Độc Bản (Nhóm T):**\n"
            f"• 🛡️ **Fantasy Seal (40%):** Miễn toàn bộ sát thương 1 lần trong trận!\n"
            f"• 🌟 **Master Spark (30%):** Sát thương ×1.5 lần trong 1 lượt!\n"
            f"• 💚 **Medicine Sign (20%):** Tự hồi phục 30% sinh lực bản thân 1 lần!\n\n"
            f"🏺 **Mảnh Seiki còn lại:** `{shards_dict['seiki']} Mảnh`"
        ),
        color=0x7C3AED
    )
    if c_info.get("image"):
        embed.set_thumbnail(url=c_info["image"])
    embed.set_footer(text="Dùng /team add id_the:t1 để đưa Seiki vào đội hình chiến đấu ngay!")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

async def handle_view_shards(ctx_or_interaction):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    shards_dict = p.setdefault("shards", {})
    seiki_shards = shards_dict.get("seiki", 0)

    embed = discord.Embed(
        title=f"🏺 KHO MẢNH THẺ BÀI (SHARDS): {author.display_name}",
        description=(
            f"🔮 **Mảnh Seiki Đệ Pháp Toàn Năng:**\n"
            f"• Số lượng hiện có: **`{seiki_shards}/10 Mảnh`**\n"
            f"• Công dụng: Quy đổi lấy **[#t1] Seiki đệ pháp toàn năng** `[Rank T]`!\n"
            f"• Cách kiếm: Tham gia đánh Boss Raid (2.5% cơ hội rơi) hoặc nhận từ Admin.\n"
            f"• Trạng thái: {'✨ **ĐÃ ĐỦ 10 MẢNH!** Dùng `/t translate` để đổi ngay!' if seiki_shards >= 10 else f'*(Cần thêm {10 - seiki_shards} mảnh nữa)*'}"
        ),
        color=0x7C3AED
    )
    embed.set_footer(text="Lệnh ghép mảnh: /t translate • Kiểm tra thẻ: /card_info nhan_vat:t1")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

# SLASH COMMAND GROUP: /t
class ShardGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="t", description="🔮 Quản lý và quy đổi mảnh thẻ bài huyền thoại")

    @app_commands.command(name="translate", description="✨ Ghép 10 Mảnh Seiki thành 1 Thẻ Bài Seiki đệ pháp toàn năng (Rank T)")
    async def slash_translate(self, interaction: discord.Interaction):
        await handle_translate_shard(interaction)

    @app_commands.command(name="shards", description="🏺 Xem số lượng Mảnh Thẻ Seiki hiện có trong kho")
    async def slash_view(self, interaction: discord.Interaction):
        await handle_view_shards(interaction)

shard_group = ShardGroup()
bot.tree.add_command(shard_group)

# Lệnh Slash dự phòng độc lập
@bot.tree.command(name="shards", description="🏺 Xem số lượng Mảnh Thẻ Seiki hiện có trong kho")
async def slash_shards_view(interaction: discord.Interaction):
    await handle_view_shards(interaction)

@bot.tree.command(name="translate_seiki", description="✨ Quy đổi 10 Mảnh Seiki thành Thẻ Seiki đệ pháp toàn năng (Rank T)")
async def slash_t_translate(interaction: discord.Interaction):
    await handle_translate_shard(interaction)

@bot.tree.command(name="seiki_shards", description="🏺 Kiểm tra kho Mảnh Seiki")
async def slash_t_shards(interaction: discord.Interaction):
    await handle_view_shards(interaction)

# Lệnh Prefix cho Shards
@bot.command(name="shards", aliases=["shard", "manh"])
async def prefix_shards(ctx):
    await handle_view_shards(ctx)

@bot.command(name="translate", aliases=["trans", "doimanh", "ghepmanh"])
async def prefix_translate(ctx):
    await handle_translate_shard(ctx)

# ==============================================================================
# HỆ THỐNG HƯỚNG DẪN TÂN THỦ & NHIỆM VỤ NGÀY (/tutorial, /quest)
# ==============================================================================
async def send_tutorial_intro(channel_or_ctx, author, p):
    embed = discord.Embed(
        title="🌸 CHÀO MỪNG ĐẾN VỚI ĐỀN HAKUREI (GENSOKYO)!",
        description=(
            f"Chào {author.mention}! Ta là **Hakurei Reimu**, vu nữ của ngôi đền này.\n"
            "Dị biến đang lan rộng khắp Gensokyo, ta sẽ trao cho ngươi sức mạnh ban đầu để cùng ta dẹp loạn!\n\n"
            "🎁 **PHẦN THƯỞNG KHỞI ĐẦU DÀNH CHO BẠN:**\n"
            "• **1 Lượt Quay Tân Thủ Miễn Phí** (Nhận ngay bộ 3 thẻ bài cốt lõi: Reimu, Marisa, Cirno)!\n"
            "• **Thiết lập đội hình 3 người** chuẩn bị xuất trận.\n"
            "• **Thực chiến PvE đầu tiên** nhận thêm kinh nghiệm và vé pull!\n\n"
            "👉 **BƯỚC 1:** Gõ ngay lệnh `/pull` hoặc `!pull` để nhận 3 thẻ bài đầu tiên của bạn!"
        ),
        color=0xF43F5E
    )
    embed.set_thumbnail(url=CARDS_DATA[13]["image"])
    embed.set_footer(text="Nhiệm vụ tân thủ: Bước 1/3 (Quay thẻ gacha)")
    if hasattr(channel_or_ctx, "send"):
        await channel_or_ctx.send(embed=embed)
    elif isinstance(channel_or_ctx, discord.Interaction):
        if channel_or_ctx.response.is_done():
            await channel_or_ctx.followup.send(embed=embed)
        else:
            await channel_or_ctx.response.send_message(embed=embed)

async def handle_tutorial(ctx_or_interaction):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    tut = p.get("tutorial", {})

    if tut.get("completed", False):
        msg = "✅ Bạn đã hoàn thành toàn bộ khóa hướng dẫn Tân Thủ rồi! Hãy tiếp tục cày cuốc qua `/daily_quest`, `/battle` và `/boss` nhé!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    step = tut.get("step", "pull")
    if step == "pull":
        await send_tutorial_intro(ctx_or_interaction, author, p)
    elif step == "team":
        embed = discord.Embed(
            title="🎯 HƯỚNG DẪN TÂN THỦ: BƯỚC 2/3",
            description=(
                f"Chào {author.mention}! Bạn đã sở hữu 3 thẻ bài khởi đầu.\n\n"
                "👉 **Nhiệm vụ của bạn:** Hãy gõ lệnh `/team` hoặc `!team` để hệ thống tự động sắp xếp đội hình 3 người xuất trận!"
            ),
            color=0x3B82F6
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else: await ctx_or_interaction.send(embed=embed)
    elif step == "battle":
        embed = discord.Embed(
            title="🎯 HƯỚNG DẪN TÂN THỦ: BƯỚC 3/3 (CUỐI CÙNG)",
            description=(
                f"Đội hình đã sẵn sàng, {author.mention}!\n\n"
                "👉 **Nhiệm vụ cuối cùng:** Hãy gõ lệnh `/battle` hoặc `!battle` để tham gia trận chiến PvE đầu tiên và hoàn tất khóa huấn luyện tân thủ!"
            ),
            color=0x10B981
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="tutorial", description="🎯 Hướng dẫn Tân Thủ và tiến trình khởi đầu Gensokyo")
async def slash_tutorial(interaction: discord.Interaction):
    await handle_tutorial(interaction)

@bot.command(name="tutorial", aliases=["huongdan", "tanthu"])
async def prefix_tutorial(ctx):
    await handle_tutorial(ctx)

async def handle_quest(ctx_or_interaction):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)
    dq = ensure_daily_quests(p)
    time_left_str = format_time_until_midnight_vn()

    embed = discord.Embed(
        title=f"📜 NHIỆM VỤ HÀNG NGÀY (DAILY QUESTS) - {author.display_name}",
        description=(
            f"📅 **Ngày:** `{dq.get('date', get_today_vn())}` (GMT+7)\n"
            f"⏳ **Thời gian làm mới tiếp theo:** Còn **{time_left_str}** (Tự động reset lúc 00:00 nửa đêm)\n"
            f"👑 **Thưởng mốc hoàn thành toàn bộ (3/3):** Nhận ngay **+10 Lượt Pull** từ Reimu!\n"
            f"*(Trạng thái mốc: {'🎁 **ĐÃ NHẬN THƯỞNG 10 VÉ!**' if dq.get('all_completed_claimed') else '⏳ Đang thực hiện...'})*"
        ),
        color=0xF59E0B
    )

    quests = dq.get("quests", [])
    completed_count = sum(1 for q in quests if q.get("completed", False))

    for q in quests:
        done = q.get("completed", False)
        status_icon = "✅ **[HOÀN THÀNH]**" if done else f"⏳ `{q['current']}/{q['target']}`"
        progress_bar = get_hp_bar(q["current"], q["target"], 8)
        embed.add_field(
            name=f"Nhiệm Vụ #{q['id']}: {q['name']} (+{q['reward']} Vé)",
            value=f"• Tiến độ: `{progress_bar}` {status_icon}\n• Phần thưởng: **+{q['reward']} Vé Pull**",
            inline=False
        )

    embed.set_footer(text=f"Tiến độ hôm nay: {completed_count}/3 nhiệm vụ • Hakurei Daily System")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="daily_quest", description="📜 Xem tiến độ 3/3 Nhiệm vụ Hàng Ngày và phần thưởng Vé Pull")
async def slash_quest(interaction: discord.Interaction):
    await handle_quest(interaction)

@bot.command(name="daily_quest", aliases=["quest", "nhiemvu", "nv"])
async def prefix_quest(ctx):
    await handle_quest(ctx)

# ==============================================================================
# HỆ THỐNG CHECK NHÂN VẬT & CHI TIẾT NĂNG LỰC (/check, /card_info)
# ==============================================================================
class CharacterCheckView(discord.ui.View):
    def __init__(self, current_cid: Union[int, str]):
        super().__init__(timeout=180)
        self.current_cid = current_cid
        self.update_select()

    def update_select(self):
        self.clear_items()
        all_cids = list(range(1, 27)) + ["t1"]
        options = []
        for cid in all_cids:
            c = CARDS_DATA[cid]
            lbl = f"{format_card_id(c['id'])} {c['name']} [{c['rank']}]"[:100]
            options.append(discord.SelectOption(label=lbl, value=str(cid), default=(str(cid).lower() == str(self.current_cid).lower())))

        select_part1 = discord.ui.Select(
            placeholder="🔽 Chọn nhân vật (Từ #01 đến #25)...",
            options=options[:25],
            row=0
        )
        select_part1.callback = self.select_callback
        self.add_item(select_part1)

        select_part2 = discord.ui.Select(
            placeholder="🔽 Chọn nhân vật (#26 Tewi hoặc #t1 Seiki)...",
            options=options[25:],
            row=1
        )
        select_part2.callback = self.select_callback
        self.add_item(select_part2)

    async def select_callback(self, interaction: discord.Interaction):
        selected_val = interaction.data["values"][0]
        try:
            self.current_cid = int(selected_val)
        except ValueError:
            self.current_cid = str(selected_val).lower()
        self.update_select()
        await interaction.response.edit_message(embed=self.get_embed(interaction.user), view=self)

    def get_embed(self, user):
        cid = self.current_cid
        card = CARDS_DATA.get(cid)
        if not card:
            return discord.Embed(title="Lỗi", description="Không tìm thấy thẻ bài!", color=0xEF4444)

        cid_int = int(cid) if isinstance(cid, int) or (isinstance(cid, str) and cid.isdigit()) else cid
        det = CHARACTER_DETAILS.get(cid_int) or CHARACTER_DETAILS.get(str(cid).lower()) or {
            "title": "Nhân Vật Gensokyo",
            "skill_name": "Tấn Công Danmaku",
            "skill_desc": "Bắn ra các chùm đạn Danmaku cơ bản gây sát thương cho đối thủ."
        }

        p = get_player(user.id, user.display_name)
        lvl_buff_pwr = get_level_atk_buff(p["level"])
        lvl_buff_hp = get_level_hp_buff(p["level"])
        is_ace2 = is_card_ace2(p, cid)
        is_locked = is_card_locked(p, cid)
        owned_count = p.get("inventory", {}).get(str(cid), 0)
        pull_count = p.get("pull_stats", {}).get(str(cid), 0)

        ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
        ace_hp = ACE_HP_BUFF if is_ace2 else 0
        final_pwr = card["power"] + lvl_buff_pwr + ace_pwr
        final_hp = card["hp"] + lvl_buff_hp + ace_hp

        embed = discord.Embed(
            title=f"🌸 THÔNG TIN NHÂN VẬT: {format_card_id(card['id'])} {card['name']}",
            description=f"*{det['title']}*\n\n**Danh hiệu & Phẩm cấp:** `[{card['rank']}]`" + (" `⭐⭐ [ACE 2]`" if is_ace2 else ""),
            color=0xF59E0B if is_ace2 else (0x7C3AED if str(cid).lower() == "t1" else 0xF43F5E)
        )
        if card.get("image"):
            embed.set_thumbnail(url=card["image"])

        embed.add_field(
            name="⚔️ Sức Mạnh (ATK):",
            value=f"• Cơ bản: `{card['power']:,} DMG`\n• Buff Cấp (Lv.{p['level']}): `+{lvl_buff_pwr:,}`\n• Buff Ace: `+{ace_pwr:,}`\n👉 **Thực chiến: `{final_pwr:,} DMG`**",
            inline=True
        )
        embed.add_field(
            name="❤️ Sinh Mệnh (HP):",
            value=f"• Cơ bản: `{card['hp']:,} HP`\n• Buff Cấp (Lv.{p['level']}): `+{lvl_buff_hp:,}`\n• Buff Ace: `+{ace_hp:,}`\n👉 **Thực chiến: `{final_hp:,} HP`**",
            inline=True
        )

        status_str = f"✅ Đang có: **x{owned_count} thẻ** (Đã pull trúng {pull_count} lần)" if owned_count > 0 else "❌ *Chưa sở hữu*"
        if is_locked:
            status_str += " \n🔒 **[ĐANG BỊ KHÓA]** (Pull lại để giải mã)"
        embed.add_field(name="📦 Tình Trạng Sở Hữu:", value=status_str, inline=False)

        skill_text = f"**{det['skill_name']}**\n{det['skill_desc']}"
        if cid in [13, 16, 17] or str(cid) in ["13", "16", "17"]:
            cfg = EVOL_CONFIG[int(cid)]
            skill_text += f"\n\n⭐ **[Nội Tại Ace 2 ⭐⭐]:** {cfg['skill_name']}\n*{cfg['skill_desc']}*"
        embed.add_field(name="✨ Tuyệt Kỹ & Cơ Chế Hoạt Ảnh:", value=skill_text, inline=False)

        embed.set_footer(text=f"Đang xem {format_card_id(card['id'])} • Chọn nhân vật khác bằng Menu bên dưới")
        return embed

async def handle_check_character(ctx_or_interaction, nhan_vat: Optional[str] = None):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    target_cid = 13  # Mặc định Reimu Hakurei
    if nhan_vat:
        norm = normalize_card_id(nhan_vat)
        if norm and norm in CARDS_DATA:
            target_cid = norm
        else:
            q = nhan_vat.strip().lower()
            for c in CARDS_DATA.values():
                if q in c["name"].lower():
                    target_cid = c["id"]
                    break

    view = CharacterCheckView(target_cid)
    embed = view.get_embed(author)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="check", description="🔍 Tra cứu chỉ số, kỹ năng và ảnh của nhân vật Touhou")
@app_commands.describe(nhan_vat="ID thẻ (1 - 26, t1) hoặc tên nhân vật (Ví dụ: Reimu, 16, Marisa, t1, seiki)")
async def slash_check(interaction: discord.Interaction, nhan_vat: Optional[str] = None):
    await handle_check_character(interaction, nhan_vat)

@bot.tree.command(name="card_info", description="🔍 Xem chi tiết thẻ bài Touhou (bao gồm Thẻ Nhóm T Seiki)")
@app_commands.describe(nhan_vat="ID thẻ (1 - 26, t1) hoặc tên nhân vật (Ví dụ: t1, seiki, 13, reimu)")
async def slash_card_info(interaction: discord.Interaction, nhan_vat: Optional[str] = None):
    await handle_check_character(interaction, nhan_vat)

@bot.command(name="check", aliases=["card_info", "cardinfo", "infocard", "check_card"])
async def prefix_check(ctx, *, nhan_vat: str = None):
    await handle_check_character(ctx, nhan_vat)

# ==============================================================================
# 9. HỆ THỐNG BATTLE PVE (CHIẾN ĐẤU THẺ BÀI)
# ==============================================================================
GENSOKYO_NPCS = [
    {
        "name": "Yêu Quái Rừng Ma Thuật",
        "title": "Yêu Quái Rừng Ma Thuật (Cấp Dễ)",
        "cards": [
            {"raw_name": "Cirno", "rank": "B", "base_power": 300, "base_hp": 3000, "image": CARDS_DATA[21]["image"], "skill": "Tia Băng Tuyết", "cid": 21},
            {"raw_name": "Rumia", "rank": "C", "base_power": 220, "base_hp": 2200, "image": CARDS_DATA[23]["image"], "skill": "Dạ Tối Kết Giới", "cid": 23},
            {"raw_name": "Mystia Lorelei", "rank": "C", "base_power": 200, "base_hp": 2000, "image": CARDS_DATA[24]["image"], "skill": "Dạ Tước Huyễn Ca", "cid": 24}
        ]
    },
    {
        "name": "Đội Phòng Thủ Hồng Ma Quán",
        "title": "Đội Phòng Thủ Hồng Ma Quán (Cấp Trung Bình)",
        "cards": [
            {"raw_name": "Sakuya Izayoi", "rank": "A", "base_power": 460, "base_hp": 4500, "image": CARDS_DATA[16]["image"], "skill": "Phi Dao Bạc Thời Gian", "cid": 16},
            {"raw_name": "Patchouli Knowledge", "rank": "B", "base_power": 380, "base_hp": 3200, "image": CARDS_DATA[20]["image"], "skill": "Thất Diệu Thần Chú", "cid": 20},
            {"raw_name": "Hong Meiling", "rank": "C", "base_power": 260, "base_hp": 2800, "image": CARDS_DATA[22]["image"], "skill": "Thái Cực Khí Công", "cid": 22}
        ]
    },
    {
        "name": "Liên Minh Nguyệt Đô & Mê Lạc Trúc Lâm",
        "title": "Liên Minh Eientei & Mokou (Cấp Khó)",
        "cards": [
            {"raw_name": "Eirin Yagokoro", "rank": "S", "base_power": 640, "base_hp": 6600, "image": CARDS_DATA[6]["image"], "skill": "Hourai Dược Tiễn", "cid": 6},
            {"raw_name": "Fujiwara no Mokou", "rank": "A", "base_power": 490, "base_hp": 5200, "image": CARDS_DATA[14]["image"], "skill": "Phượng Hoàng Bất Diệt", "cid": 14},
            {"raw_name": "Reisen Udongein Inaba", "rank": "B", "base_power": 390, "base_hp": 3900, "image": CARDS_DATA[19]["image"], "skill": "Hồng Nhãn Sóng Âm", "cid": 19}
        ]
    },
    {
        "name": "Cổ Thần Tối Cao Gensokyo",
        "title": "Cổ Thần & Đại Quỷ Vương (Cấp Thần Thoại)",
        "cards": [
            {"raw_name": "Hecatia Lapislazuli", "rank": "SS", "base_power": 850, "base_hp": 8500, "image": CARDS_DATA[1]["image"], "skill": "Tam Thân Dị Giới", "cid": 1},
            {"raw_name": "Junko", "rank": "SS", "base_power": 800, "base_hp": 8000, "image": CARDS_DATA[2]["image"], "skill": "Thanh Lọc Nguyên Lực", "cid": 2},
            {"raw_name": "Yukari Yakumo", "rank": "SS", "base_power": 720, "base_hp": 7200, "image": CARDS_DATA[4]["image"], "skill": "Cảnh Giới Đoạt Mệnh", "cid": 4}
        ]
    }
]

async def handle_battle(ctx_or_interaction):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    p = get_player(author.id, author.display_name)

    # KIỂM TRA NHIỆM VỤ TÂN THỦ BƯỚC 3 (BATTLE)
    tut = p.get("tutorial", {})
    tut_complete_notice = None
    if tut.get("active", False) and not tut.get("completed", False):
        if tut.get("step") == "battle":
            tut["completed"] = True
            tut["active"] = False
            p["pull_tickets"] += 5.0
            p["xp"] += 100
            tut_complete_notice = (
                "👑 **CHÚC MỪNG BẠN ĐÃ HOÀN THÀNH TOÀN BỘ KHÓA HUẤN LUYỆN TÂN THỦ!**\n"
                "⛩️ **Reimu:** *\"Ngươi làm tốt lắm! Đây là phần thưởng tốt nghiệp 5 Vé Pull và 100 XP! Giờ thì tự mình tung hoành Gensokyo đi!\"*\n"
                "🎁 **Đã nhận thêm:** **+5 Vé Pull** 🎟️ & **+100 XP** ⭐!"
            )

    lvl_buff_pwr = get_level_atk_buff(p["level"])
    lvl_buff_hp = get_level_hp_buff(p["level"])

    # LỰA CHỌN ĐỘI HÌNH
    team_cids = [cid for cid in p.get("team", []) if cid in CARDS_DATA and not is_card_locked(p, cid)]
    if len(team_cids) < 3:
        owned_ids = [cid for cid, cnt in p.get("inventory", {}).items() if cnt > 0 and cid in CARDS_DATA and not is_card_locked(p, cid)]
        owned_ids.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
        for cid in owned_ids:
            if cid not in team_cids:
                team_cids.append(cid)
            if len(team_cids) >= 3:
                break
        p["team"] = team_cids
        save_player(p)

    if not team_cids:
        msg = "⚠️ Bạn chưa sở hữu thẻ bài nào để chiến đấu! Hãy quay gacha qua `/pull` trước nhé!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    player_cards = []
    for cid in team_cids[:3]:
        c_info = CARDS_DATA[cid]
        is_ace2 = is_card_ace2(p, cid)
        ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
        ace_hp = ACE_HP_BUFF if is_ace2 else 0
        card_pwr = c_info["power"] + lvl_buff_pwr + ace_pwr
        card_hp = c_info["hp"] + lvl_buff_hp + ace_hp
        card_name = f"[Ace 2 ⭐⭐] #{c_info['id']} {c_info['name']}" if is_ace2 else f"{format_card_id(c_info['id'])} {c_info['name']}"
        player_cards.append({
            "cid": cid,
            "name": card_name,
            "base_name": c_info["name"],
            "rank": c_info["rank"],
            "power": card_pwr,
            "hp": card_hp,
            "max_hp": card_hp,
            "is_ace2": is_ace2,
            "image": c_info.get("image")
        })

    # TẠO ĐỐI THỦ PVE TƯƠNG ĐƯƠNG TRÌNH ĐỘ
    npc_template = random.choice(GENSOKYO_NPCS)
    opp_name = npc_template["title"]
    opp_cards = []
    opp_level = max(1, p["level"] + random.randint(-1, 2))
    opp_lvl_pwr = get_level_atk_buff(opp_level)
    opp_lvl_hp = get_level_hp_buff(opp_level)

    for c in npc_template["cards"]:
        pwr = c["base_power"] + opp_lvl_pwr
        hp = c["base_hp"] + opp_lvl_hp
        opp_cards.append({
            "cid": c.get("cid", 1),
            "name": f"#{c.get('cid', 1)} {c['raw_name']}",
            "raw_name": c["raw_name"],
            "rank": c["rank"],
            "power": pwr,
            "base_power": c["base_power"],
            "hp": hp,
            "base_hp": c["base_hp"],
            "max_hp": hp,
            "is_ace2": False,
            "image": c.get("image"),
            "skill": c.get("skill")
        })

    # MÔ PHỎNG CHIẾN ĐẤU TURN-BY-TURN CHI TIẾT
    p_idx = 0
    o_idx = 0
    turns_history = []
    p_sakuya_used = False
    p_reimu_used = False
    p_marisa_used = False
    p_seiki_seal_used = False
    p_seiki_spark_used = False
    p_seiki_heal_used = False
    p_seiki_turn_used = -1

    round_cnt = 0
    max_rounds = 30

    while p_idx < len(player_cards) and o_idx < len(opp_cards) and round_cnt < max_rounds:
        round_cnt += 1
        pc = player_cards[p_idx]
        oc = opp_cards[o_idx]

        turn_gif = None
        sakuya_stun = False
        marisa_spark = False
        reimu_invul = False
        seiki_spark = False
        seiki_seal = False
        seiki_heal = False

        # Ace 2 Sakuya (40% Stun)
        if pc["cid"] == 16 and pc["is_ace2"] and not p_sakuya_used:
            if random.random() < 0.40:
                p_sakuya_used = True
                sakuya_stun = True
                turn_gif = EVOL_CONFIG[16]["skill_gif"]

        # Ace 2 Marisa (30% Spark x1.5 DMG)
        p_dmg = pc["power"]
        if pc["cid"] == 17 and pc["is_ace2"] and not p_marisa_used:
            if random.random() < 0.30:
                p_marisa_used = True
                marisa_spark = True
                p_dmg = int(p_dmg * 1.5)
                turn_gif = EVOL_CONFIG[17]["skill_gif"]

        # Thẻ Nhóm T Seiki (Fantasy Seal, Master Spark, Medicine Sign - Tối đa 1 chiêu/lượt, 1 lần/trận)
        if str(pc["cid"]).lower() == "t1" and p_seiki_turn_used != round_cnt:
            if not p_seiki_spark_used and random.random() < 0.30:
                p_seiki_spark_used = True
                p_seiki_turn_used = round_cnt
                seiki_spark = True
                p_dmg = int(p_dmg * 1.5)
                turn_gif = "https://klipy.com/gifs/marisa-master-spark"
            elif not p_seiki_heal_used and pc["hp"] < pc["max_hp"] and random.random() < 0.20:
                p_seiki_heal_used = True
                p_seiki_turn_used = round_cnt
                seiki_heal = True
                heal_amt = int(pc["max_hp"] * 0.30)
                pc["hp"] = min(pc["max_hp"], pc["hp"] + heal_amt)
                turn_gif = "https://klipy.com/gifs/shoko-ieiri-2"

        # Người chơi tấn công
        oc["hp"] -= p_dmg
        p_atk_log = f"⚔️ **{pc['name']}** tấn công gây **{p_dmg:,} DMG** lên **{oc['name']}**!"
        if marisa_spark:
            p_atk_log = f"🌟 **[Ace 2] [#17] Marisa** bộc phá **Master Spark (30%)**! Gây x1.5 sát thương (**{p_dmg:,} DMG**)!"
        elif seiki_spark:
            p_atk_log = f"🌟 **[Nhóm T] [#t1] Seiki** phát động **Master Spark (30%)**! Giáng x1.5 sát thương (**{p_dmg:,} DMG**)!"

        o_atk_log = ""
        if oc["hp"] > 0:
            if sakuya_stun:
                o_atk_log = f"❄️ **[Ace 2] [#16] Sakuya** kích hoạt **Thời Gian Đóng Băng** (40%)! **{oc['name']}** bị **STUN** mất lượt!"
            else:
                o_dmg = oc["power"]
                # Ace 2 Reimu (40% Né đòn)
                if pc["cid"] == 13 and pc["is_ace2"] and not p_reimu_used:
                    if random.random() < 0.40:
                        p_reimu_used = True
                        reimu_invul = True
                        turn_gif = EVOL_CONFIG[13]["skill_gif"]
                # Seiki Fantasy Seal (40% Né đòn)
                elif str(pc["cid"]).lower() == "t1" and not p_seiki_seal_used and p_seiki_turn_used != round_cnt:
                    if random.random() < 0.40:
                        p_seiki_seal_used = True
                        p_seiki_turn_used = round_cnt
                        seiki_seal = True
                        turn_gif = "https://klipy.com/gifs/hakurei-reimu-touhou"

                if reimu_invul:
                    o_atk_log = f"🛡️ **[Ace 2] [#13] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN HOÀN TOÀN **{o_dmg:,} DMG** từ đối thủ!"
                elif seiki_seal:
                    o_atk_log = f"🛡️ **[Nhóm T] [#t1] Seiki** kích hoạt **Fantasy Seal** (40%)! MIỄN HOÀN TOÀN **{o_dmg:,} DMG** từ đối thủ!"
                else:
                    pc["hp"] -= o_dmg
                    o_atk_log = f"💥 **{oc['name']}** phản đòn gây **{o_dmg:,} DMG** lên **{pc['name']}**!"
        else:
            o_atk_log = f"💀 **{oc['name']}** đã bị đánh bại hoàn toàn!"

        push_log = ""
        if oc["hp"] <= 0:
            o_idx += 1
            if o_idx < len(opp_cards):
                push_log += f"\n➡️ Đối thủ đẩy **{opp_cards[o_idx]['name']}** lên tiền tuyến!"
        if pc["hp"] <= 0:
            p_idx += 1
            if p_idx < len(player_cards):
                push_log += f"\n➡️ Bạn cử tiếp **{player_cards[p_idx]['name']}** xuất trận!"

        turns_history.append({
            "round": round_cnt,
            "title": f"Hiệp {round_cnt}: {pc['base_name']} vs {oc['raw_name']}",
            "short_label": f"H{round_cnt} - {pc['base_name'][:8]}",
            "short_desc": f"{pc['base_name']} vs {oc['raw_name']}",
            "desc": f"**Chiến Tuyến:** {pc['name']} *(❤️ {max(0, pc['hp']):,}/{pc['max_hp']:,})*\n⚔️ **Đối Thủ:** {oc['name']} *(❤️ {max(0, oc['hp']):,}/{oc['max_hp']:,})*",
            "color": 0x3B82F6,
            "image": turn_gif,
            "fields": [
                ("👉 Hành Động Của Bạn:", p_atk_log, False),
                ("👹 Đối Thủ Phản Hồi:", o_atk_log, False),
                *([("🔄 Đổi Thẻ Bài Tiền Tuyến:", push_log.strip(), False)] if push_log else []),
                *([("💚 Kỹ Năng Phục Hồi:", f"**[#t1] Seiki** hồi phục **+{int(pc['max_hp'] * 0.30):,} HP** (Medicine Sign)!", False)] if seiki_heal else [])
            ]
        })

    is_victory = (p_idx < len(player_cards) and o_idx >= len(opp_cards))
    p["battles_total"] = p.get("battles_total", 0) + 1

    if is_victory:
        p["battles_won"] = p.get("battles_won", 0) + 1
        xp_gain = 30
        p["xp"] += xp_gain
        p["pull_tickets"] += 0.2
        reward_str = f"• **+{xp_gain} Điểm Kinh Nghiệm (XP)** ⭐\n• **+0.20 Vé Pull** 🎟️"
        color = 0x10B981
        title = "🎉 CHIẾN THẮNG HUY HOÀNG (PVE BATTLE)!"
    else:
        xp_gain = 10
        p["xp"] += xp_gain
        reward_str = f"• **+{xp_gain} XP Khuyến Khích** ⭐"
        color = 0xEF4444
        title = "❌ THẤT BẠI TRONG TRẬN CHIẾN PVE!"

    quest_notifs = update_daily_quest_progress(p, "battle", 1)
    save_player(p)

    embed_result = discord.Embed(
        title=title,
        description=(
            f"👤 **Người chơi:** {author.mention} (Lv.{p['level']})\n"
            f"👹 **Đối thủ:** {opp_name}\n"
            f"⏱️ **Tổng số hiệp:** {round_cnt} hiệp\n\n"
            f"🎁 **Phần thưởng nhận được:**\n{reward_str}"
        ),
        color=color
    )
    embed_result.add_field(
        name="📜 Xem Lại Trận Đấu & Đội Hình:",
        value="Bấm nút **'Diễn Biến Từng Hiệp (GIF)'** bên dưới để xem lại từng hiệp đánh có hoạt ảnh GIF, hoặc bấm **'Soi Đội Hình Đối Thủ'** để xem toàn bộ 3 thẻ của đối phương!",
        inline=False
    )
    embed_result.set_footer(text=f"Tỉ lệ thắng: {p['battles_won']}/{p['battles_total']} trận • Hakurei Battle System")

    view = OpenDetailsView(turns_history, opp_cards=opp_cards, opp_name=opp_name, opp_level=opp_level)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed_result, view=view)
        if tut_complete_notice:
            await ctx_or_interaction.followup.send(tut_complete_notice)
        if quest_notifs:
            await ctx_or_interaction.followup.send("\n".join(quest_notifs))
    else:
        await ctx_or_interaction.send(embed=embed_result, view=view)
        if tut_complete_notice:
            await ctx_or_interaction.send(tut_complete_notice)
        if quest_notifs:
            await ctx_or_interaction.send("\n".join(quest_notifs))

@bot.tree.command(name="battle", description="⚔️ Chiến đấu PvE với các đối thủ tại Gensokyo (Xem GIF trực tiếp)")
async def slash_battle(interaction: discord.Interaction):
    await handle_battle(interaction)

@bot.command(name="battle", aliases=["pvb", "danhpve", "fight"])
async def prefix_battle(ctx):
    await handle_battle(ctx)

# ==============================================================================
# 10. HỆ THỐNG PVP ĐẠI CHIẾN (CHIẾN ĐẤU GIỮA 2 NGƯỜI CHƠI - XEM GIF TRỰC TIẾP)
# ==============================================================================
class PvPChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, target: discord.Member, c_team_cids, t_team_cids):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target
        self.c_team_cids = c_team_cids
        self.t_team_cids = t_team_cids
        self.accepted = False

    @discord.ui.button(label="⚔️ Chấp Nhận Thách Đấu!", style=discord.ButtonStyle.danger, emoji="💥")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Lời thách đấu này không dành cho bạn!", ephemeral=True)
            return

        self.accepted = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            f"🔥 **{self.target.mention} ĐÃ CHẤP NHẬN THÁCH ĐẤU TỪ {self.challenger.mention}!**\n"
            "⛩️ Trận thư hùng Danmaku đỉnh cao giữa 2 đại pháp sư chính thức khởi tranh!"
        )
        await run_pvp_match(interaction.channel, self.challenger, self.target, self.c_team_cids, self.t_team_cids)

    @discord.ui.button(label="🏳️ Từ Chối", style=discord.ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id and interaction.user.id != self.challenger.id:
            await interaction.response.send_message("❌ Bạn không liên quan đến trận đấu này!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🏳️ Lời thách đấu giữa {self.challenger.mention} và {self.target.mention} đã bị hủy bỏ.")

async def run_pvp_match(channel, challenger, target, c_team_cids, t_team_cids, interaction: discord.Interaction = None, msg: discord.Message = None):
    p1 = get_player(challenger.id, challenger.display_name)
    p2 = get_player(target.id, target.display_name)

    p1_lvl_pwr = get_level_atk_buff(p1["level"])
    p1_lvl_hp = get_level_hp_buff(p1["level"])
    p2_lvl_pwr = get_level_atk_buff(p2["level"])
    p2_lvl_hp = get_level_hp_buff(p2["level"])

    # Xây dựng 3 thẻ bài cho P1
    cards_p1 = []
    for cid in c_team_cids[:3]:
        c = CARDS_DATA[cid]
        is_ace2 = is_card_ace2(p1, cid)
        ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
        ace_hp = ACE_HP_BUFF if is_ace2 else 0
        card_pwr = c["power"] + p1_lvl_pwr + ace_pwr
        card_hp = c["hp"] + p1_lvl_hp + ace_hp
        card_name = f"[Ace 2 ⭐⭐] #{c['id']} {c['name']}" if is_ace2 else f"{format_card_id(c['id'])} {c['name']}"
        cards_p1.append({
            "cid": cid,
            "name": card_name,
            "base_name": c["name"],
            "rank": c["rank"],
            "power": card_pwr,
            "base_power": c["power"],
            "hp": card_hp,
            "base_hp": c["hp"],
            "max_hp": card_hp,
            "is_ace2": is_ace2,
            "image": c.get("image")
        })

    # Xây dựng 3 thẻ bài cho P2
    cards_p2 = []
    for cid in t_team_cids[:3]:
        c = CARDS_DATA[cid]
        is_ace2 = is_card_ace2(p2, cid)
        ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
        ace_hp = ACE_HP_BUFF if is_ace2 else 0
        card_pwr = c["power"] + p2_lvl_pwr + ace_pwr
        card_hp = c["hp"] + p2_lvl_hp + ace_hp
        card_name = f"[Ace 2 ⭐⭐] #{c['id']} {c['name']}" if is_ace2 else f"{format_card_id(c['id'])} {c['name']}"
        cards_p2.append({
            "cid": cid,
            "name": card_name,
            "base_name": c["name"],
            "rank": c["rank"],
            "power": card_pwr,
            "base_power": c["power"],
            "hp": card_hp,
            "base_hp": c["hp"],
            "max_hp": card_hp,
            "is_ace2": is_ace2,
            "image": c.get("image")
        })

    idx1 = 0
    idx2 = 0
    turns_history = []
    round_cnt = 0
    max_rounds = 35

    p1_sakuya = False
    p1_reimu = False
    p1_marisa = False
    p1_seiki_seal = False
    p1_seiki_spark = False
    p1_seiki_heal = False
    p1_seiki_turn = -1

    p2_sakuya = False
    p2_reimu = False
    p2_marisa = False
    p2_seiki_seal = False
    p2_seiki_spark = False
    p2_seiki_heal = False
    p2_seiki_turn = -1

    while idx1 < len(cards_p1) and idx2 < len(cards_p2) and round_cnt < max_rounds:
        round_cnt += 1
        c1 = cards_p1[idx1]
        c2 = cards_p2[idx2]

        turn_gif = None
        sakuya1_stun = False
        sakuya2_stun = False
        marisa1_spark = False
        marisa2_spark = False
        reimu1_invul = False
        reimu2_invul = False
        seiki1_seal = False
        seiki2_seal = False
        seiki1_spark = False
        seiki2_spark = False
        seiki1_heal = False
        seiki2_heal = False

        # Kiểm tra Sakuya Stun P1
        if c1["cid"] == 16 and c1["is_ace2"] and not p1_sakuya:
            if random.random() < 0.40:
                p1_sakuya = True
                sakuya1_stun = True
                turn_gif = EVOL_CONFIG[16]["skill_gif"]

        # Kiểm tra Sakuya Stun P2
        if c2["cid"] == 16 and c2["is_ace2"] and not p2_sakuya:
            if random.random() < 0.40:
                p2_sakuya = True
                sakuya2_stun = True
                if not turn_gif: turn_gif = EVOL_CONFIG[16]["skill_gif"]

        # Marisa Spark P1
        dmg1 = c1["power"]
        if c1["cid"] == 17 and c1["is_ace2"] and not p1_marisa:
            if random.random() < 0.30:
                p1_marisa = True
                marisa1_spark = True
                dmg1 = int(dmg1 * 1.5)
                if not turn_gif: turn_gif = EVOL_CONFIG[17]["skill_gif"]

        # Seiki T1 P1
        if str(c1["cid"]).lower() == "t1" and p1_seiki_turn != round_cnt:
            if not p1_seiki_spark and random.random() < 0.30:
                p1_seiki_spark = True
                p1_seiki_turn = round_cnt
                seiki1_spark = True
                dmg1 = int(dmg1 * 1.5)
                if not turn_gif: turn_gif = "https://klipy.com/gifs/marisa-master-spark"
            elif not p1_seiki_heal and c1["hp"] < c1["max_hp"] and random.random() < 0.20:
                p1_seiki_heal = True
                p1_seiki_turn = round_cnt
                seiki1_heal = True
                h_amt = int(c1["max_hp"] * 0.30)
                c1["hp"] = min(c1["max_hp"], c1["hp"] + h_amt)
                if not turn_gif: turn_gif = "https://klipy.com/gifs/shoko-ieiri-2"

        # Marisa Spark P2
        dmg2 = c2["power"]
        if c2["cid"] == 17 and c2["is_ace2"] and not p2_marisa:
            if random.random() < 0.30:
                p2_marisa = True
                marisa2_spark = True
                dmg2 = int(dmg2 * 1.5)
                if not turn_gif: turn_gif = EVOL_CONFIG[17]["skill_gif"]

        # Seiki T1 P2
        if str(c2["cid"]).lower() == "t1" and p2_seiki_turn != round_cnt:
            if not p2_seiki_spark and random.random() < 0.30:
                p2_seiki_spark = True
                p2_seiki_turn = round_cnt
                seiki2_spark = True
                dmg2 = int(dmg2 * 1.5)
                if not turn_gif: turn_gif = "https://klipy.com/gifs/marisa-master-spark"
            elif not p2_seiki_heal and c2["hp"] < c2["max_hp"] and random.random() < 0.20:
                p2_seiki_heal = True
                p2_seiki_turn = round_cnt
                seiki2_heal = True
                h_amt = int(c2["max_hp"] * 0.30)
                c2["hp"] = min(c2["max_hp"], c2["hp"] + h_amt)
                if not turn_gif: turn_gif = "https://klipy.com/gifs/shoko-ieiri-2"

        # P1 tấn công P2
        p1_log = ""
        if sakuya2_stun:
            p1_log = f"❄️ **{c1['name']}** bị **STUN** bởi Sakuya đối phương!"
        else:
            # P2 Reimu Né Đòn
            if c2["cid"] == 13 and c2["is_ace2"] and not p2_reimu:
                if random.random() < 0.40:
                    p2_reimu = True
                    reimu2_invul = True
                    if not turn_gif: turn_gif = EVOL_CONFIG[13]["skill_gif"]
            elif str(c2["cid"]).lower() == "t1" and not p2_seiki_seal and p2_seiki_turn != round_cnt:
                if random.random() < 0.40:
                    p2_seiki_seal = True
                    p2_seiki_turn = round_cnt
                    seiki2_seal = True
                    if not turn_gif: turn_gif = "https://klipy.com/gifs/hakurei-reimu-touhou"

            if reimu2_invul:
                p1_log = f"🛡️ **[Ace 2] [#13] Reimu** ({challenger.display_name}) né toàn bộ **{dmg1:,} DMG** nhờ Vô Tưởng Chuyển Sinh!"
            elif seiki2_seal:
                p1_log = f"🛡️ **[Nhóm T] [#t1] Seiki** ({target.display_name}) kích hoạt **Fantasy Seal** (40%)! Miễn hoàn toàn **{dmg1:,} DMG**!"
            else:
                c2["hp"] -= dmg1
                spark_txt = " *(🌟 Master Spark x1.5)*" if (marisa1_spark or seiki1_spark) else ""
                p1_log = f"⚔️ **{c1['name']}** ({challenger.display_name}) giáng **{dmg1:,} DMG**{spark_txt} lên **{c2['name']}**!"

        # P2 phản công P1 (nếu còn sống)
        p2_log = ""
        if c2["hp"] > 0:
            if sakuya1_stun:
                p2_log = f"❄️ **{c2['name']}** bị **STUN** bởi Sakuya đối phương!"
            else:
                if c1["cid"] == 13 and c1["is_ace2"] and not p1_reimu:
                    if random.random() < 0.40:
                        p1_reimu = True
                        reimu1_invul = True
                        if not turn_gif: turn_gif = EVOL_CONFIG[13]["skill_gif"]
                elif str(c1["cid"]).lower() == "t1" and not p1_seiki_seal and p1_seiki_turn != round_cnt:
                    if random.random() < 0.40:
                        p1_seiki_seal = True
                        p1_seiki_turn = round_cnt
                        seiki1_seal = True
                        if not turn_gif: turn_gif = "https://klipy.com/gifs/hakurei-reimu-touhou"

                if reimu1_invul:
                    p2_log = f"🛡️ **[Ace 2] [#13] Reimu** ({challenger.display_name}) né toàn bộ **{dmg2:,} DMG** nhờ Vô Tưởng Chuyển Sinh!"
                elif seiki1_seal:
                    p2_log = f"🛡️ **[Nhóm T] [#t1] Seiki** ({challenger.display_name}) kích hoạt **Fantasy Seal** (40%)! Miễn hoàn toàn **{dmg2:,} DMG**!"
                else:
                    c1["hp"] -= dmg2
                    spark_txt = " *(🌟 Master Spark x1.5)*" if (marisa2_spark or seiki2_spark) else ""
                    p2_log = f"💥 **{c2['name']}** ({target.display_name}) phản công **{dmg2:,} DMG**{spark_txt} lên **{c1['name']}**!"
        else:
            p2_log = f"💀 **{c2['name']}** ({target.display_name}) đã bị hạ gục!"

        push_log = ""
        if c2["hp"] <= 0:
            idx2 += 1
            if idx2 < len(cards_p2):
                push_log += f"\n➡️ {target.display_name} cử **{cards_p2[idx2]['name']}** lên tiền tuyến!"
        if c1["hp"] <= 0:
            idx1 += 1
            if idx1 < len(cards_p1):
                push_log += f"\n➡️ {challenger.display_name} cử **{cards_p1[idx1]['name']}** lên tiền tuyến!"

        turns_history.append({
            "round": round_cnt,
            "title": f"Hiệp {round_cnt}: {c1['base_name']} vs {c2['base_name']}",
            "short_label": f"H{round_cnt} - PvP",
            "short_desc": f"{challenger.display_name} vs {target.display_name}",
            "desc": f"**{challenger.display_name}:** {c1['name']} *(❤️{max(0, c1['hp']):,}/{c1['max_hp']:,})*\n⚔️ **{target.display_name}:** {c2['name']} *(❤️{max(0, c2['hp']):,}/{c2['max_hp']:,})*",
            "color": 0xDC2626,
            "image": turn_gif,
            "fields": [
                (f"👉 {challenger.display_name}:", p1_log, False),
                (f"👹 {target.display_name}:", p2_log, False),
                *([("🔄 Đổi Thẻ Bài Tiền Tuyến:", push_log.strip(), False)] if push_log else []),
                *([("💚 Phục Hồi Seiki:", f"**[#t1] Seiki** hồi phục **+{int(c1['max_hp'] * 0.30):,} HP** (Medicine Sign)!", False)] if seiki1_heal else []),
                *([("💚 Phục Hồi Seiki:", f"**[#t1] Seiki** hồi phục **+{int(c2['max_hp'] * 0.30):,} HP** (Medicine Sign)!", False)] if seiki2_heal else [])
            ]
        })

    # Xác định người thắng cuộc
    p1_won = (idx1 < len(cards_p1) and idx2 >= len(cards_p2))
    p2_won = (idx2 < len(cards_p2) and idx1 >= len(cards_p1))

    if p1_won:
        winner = challenger
        loser = target
        winner_p = p1
        loser_p = p2
    elif p2_won:
        winner = target
        loser = challenger
        winner_p = p2
        loser_p = p1
    else:
        winner = None

    if winner:
        winner_p["xp"] += 50
        winner_p["pull_tickets"] += 0.5
        loser_p["xp"] += 15
        update_daily_quest_progress(p1, "pvp", 1)
        update_daily_quest_progress(p2, "pvp", 1)
        save_player(p1)
        save_player(p2)

        res_embed = discord.Embed(
            title="👑 KẾT QUẢ ĐẠI CHIẾN PVP TOUHOU!",
            description=(
                f"🏆 **NGƯỜI CHIẾN THẮNG:** {winner.mention} (Lv.{winner_p['level']})\n"
                f"💀 **Thất bại anh dũng:** {loser.mention} (Lv.{loser_p['level']})\n"
                f"⏱️ **Số hiệp đấu:** {round_cnt} hiệp đầy kịch tính\n\n"
                f"🎁 **Phần thưởng cho {winner.display_name}:**\n"
                "• **+50 XP** ⭐ | **+0.50 Vé Pull** 🎟️\n\n"
                f"🎖️ **Khuyến khích {loser.display_name}:** **+15 XP** ⭐"
            ),
            color=0x10B981
        )
    else:
        update_daily_quest_progress(p1, "pvp", 1)
        update_daily_quest_progress(p2, "pvp", 1)
        save_player(p1)
        save_player(p2)
        res_embed = discord.Embed(
            title="🤝 KẾT QUẢ PVP: BẤT PHÂN THẮNG BẠI!",
            description=f"Sau {round_cnt} hiệp chiến đấu ác liệt, cả 2 dũng giả đều kiệt sức cùng lúc!\nCả hai nhận được **+25 XP** khuyến khích!",
            color=0xF59E0B
        )

    res_embed.add_field(
        name="📜 Xem Diễn Biến & GIF Chiêu Thức:",
        value="Bấm nút **'Diễn Biến Từng Hiệp (GIF)'** bên dưới để xem lại từng hiệp thi đấu với ảnh GIF tuyệt chiêu!",
        inline=False
    )
    res_embed.set_footer(text="Hakurei PvP Arena • 3v3 Danmaku Combat")

    view = OpenDetailsView(turns_history, opp_cards=cards_p2, opp_name=target.display_name, opp_level=p2["level"])
    await channel.send(embed=res_embed, view=view)

async def handle_pvp(ctx_or_interaction, target: discord.Member):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    channel = ctx_or_interaction.channel

    if target.id == author.id:
        msg = "⚠️ Bạn không thể tự thách đấu chính mình!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if target.bot:
        msg = "⚠️ Bạn không thể thách đấu bot!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    p_author = get_player(author.id, author.display_name)
    p_target = get_player(target.id, target.display_name)

    # Đội hình người thách đấu
    c_team = [cid for cid in p_author.get("team", []) if cid in CARDS_DATA and not is_card_locked(p_author, cid)]
    if len(c_team) < 3:
        owned = [cid for cid, cnt in p_author.get("inventory", {}).items() if cnt > 0 and cid in CARDS_DATA and not is_card_locked(p_author, cid)]
        owned.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
        for cid in owned:
            if cid not in c_team: c_team.append(cid)
            if len(c_team) >= 3: break
        p_author["team"] = c_team
        save_player(p_author)

    # Đội hình người nhận thách đấu
    t_team = [cid for cid in p_target.get("team", []) if cid in CARDS_DATA and not is_card_locked(p_target, cid)]
    if len(t_team) < 3:
        owned = [cid for cid, cnt in p_target.get("inventory", {}).items() if cnt > 0 and cid in CARDS_DATA and not is_card_locked(p_target, cid)]
        owned.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
        for cid in owned:
            if cid not in t_team: t_team.append(cid)
            if len(t_team) >= 3: break
        p_target["team"] = t_team
        save_player(p_target)

    if len(c_team) < 1:
        msg = "⚠️ Bạn chưa có thẻ bài nào trong tay để tham gia PvP! Hãy `/pull` trước."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if len(t_team) < 1:
        msg = f"⚠️ Đối thủ {target.mention} chưa có thẻ bài nào để nghênh chiến!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    embed = discord.Embed(
        title="⚔️ LỜI THÁCH ĐẤU ĐẠI CHIẾN PVP TOUHOU!",
        description=(
            f"🔥 **{author.mention}** (Lv.{p_author['level']}) đã gửi thư thách đấu Danmaku trực tiếp tới **{target.mention}** (Lv.{p_target['level']})!\n\n"
            f"• **Đội hình {author.display_name}:** `{len(c_team)}/3 thẻ`\n"
            f"• **Đội hình {target.display_name}:** `{len(t_team)}/3 thẻ`\n\n"
            f"⏳ **Thời gian chờ:** 60 giây để {target.mention} bấm **'Chấp Nhận Thách Đấu'**!"
        ),
        color=0xDC2626
    )
    embed.set_footer(text="Hakurei PvP Arena • Cả 2 đều nhận XP và tính nhiệm vụ ngày!")

    view = PvPChallengeView(author, target, c_team, t_team)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="pvp", description="⚔️ Thách đấu PvP đại chiến thẻ bài Touhou với người chơi khác")
@app_commands.describe(user="Người chơi bạn muốn thách đấu")
async def slash_pvp(interaction: discord.Interaction, user: discord.Member):
    await handle_pvp(interaction, user)

@bot.command(name="pvp", aliases=["duel", "thachdau"])
async def prefix_pvp(ctx, user: discord.Member = None):
    if not user:
        await ctx.send("⚠️ Bạn cần tag người muốn thách đấu! Ví dụ: `!pvp @nguoidung`")
        return
    await handle_pvp(ctx, user)

# ==============================================================================
# HỆ THỐNG TRAO ĐỔI THẺ BÀI (TRADE CARDS - CHỐNG CLONE & XÁC NHẬN 2/2)
# ==============================================================================
def find_card_by_name_or_id(query: str):
    """Tìm card_id từ query (có thể là ID: 1, #13, 't1' hoặc tên: reimu, sakuya...)."""
    if not query:
        return None
    s = str(query).strip().lower().replace("#", "")
    if s in CARDS_DATA:
        return s
    try:
        val = int(s)
        if val in CARDS_DATA:
            return val
    except ValueError:
        pass
    if s in CARD_ALIASES:
        return CARD_ALIASES[s]
    # Tìm kiếm gần đúng theo tên
    for cid, c in CARDS_DATA.items():
        if s in c["name"].lower():
            return cid
    return None

def parse_trade_offer(offer_str: str):
    """Phân tích chuỗi trade ví dụ: '13' hoặc '13 2' hoặc 'reimu 2' thành list các (cid, count)."""
    if not offer_str:
        return []
    parts = offer_str.strip().split()
    if not parts:
        return []

    # Trường hợp: ID / tên và số lượng (ví dụ: '13 2' hoặc 'reimu 1')
    if len(parts) >= 2 and parts[-1].isdigit():
        count = max(1, int(parts[-1]))
        card_query = " ".join(parts[:-1])
        cid = find_card_by_name_or_id(card_query)
        if cid:
            return [(cid, count)]
        return []

    # Trường hợp nhiều thẻ cách nhau bằng dấu phẩy: '13, 16, 17' hoặc khoảng trắng
    tokens = [t.strip() for t in offer_str.replace(",", " ").split() if t.strip()]
    results = []
    for tok in tokens:
        cid = find_card_by_name_or_id(tok)
        if cid:
            results.append((cid, 1))
    return results

class TradeConfirmationView(discord.ui.View):
    def __init__(self, user_a: discord.Member, user_b: discord.Member, offer_a: list, offer_b: list):
        super().__init__(timeout=120)
        self.user_a = user_a
        self.user_b = user_b
        self.offer_a = offer_a  # List of (cid, count)
        self.offer_b = offer_b  # List of (cid, count)
        self.confirmed_a = False
        self.confirmed_b = False
        self.is_done = False

    def get_trade_embed(self):
        embed = discord.Embed(
            title="🤝 XÁC NHẬN GIAO DỊCH THẺ BÀI TOUHOU",
            description=(
                "Cả hai người chơi vui lòng kiểm tra kỹ thẻ bài trao đổi bên dưới.\n"
                "**Giao dịch CHỈ HOÀN TẤT khi CẢ 2 BÊN đều bấm Xác Nhận!**"
            ),
            color=0x3B82F6
        )

        def format_offer(offer_list, user):
            if not offer_list:
                return "*Không đưa ra thẻ nào (Tặng/Cho không)*"
            lines = []
            for cid, cnt in offer_list:
                c = CARDS_DATA[cid]
                lines.append(f"• **{format_card_id(c['id'])} {c['name']}** `[{c['rank']}]` x{cnt}")
            return "\n".join(lines)

        status_a = "✅ **ĐÃ XÁC NHẬN**" if self.confirmed_a else "⏳ *Chờ xác nhận...*"
        status_b = "✅ **ĐÃ XÁC NHẬN**" if self.confirmed_b else "⏳ *Chờ xác nhận...*"

        embed.add_field(
            name=f"👤 {self.user_a.display_name} Giao Ra ({status_a}):",
            value=format_offer(self.offer_a, self.user_a),
            inline=False
        )
        embed.add_field(
            name=f"👤 {self.user_b.display_name} Giao Ra ({status_b}):",
            value=format_offer(self.offer_b, self.user_b),
            inline=False
        )
        embed.set_footer(text="Giao dịch an toàn • Tự động hủy sau 2 phút nếu một trong hai bên không bấm nút")
        return embed

    @discord.ui.button(label="✅ Xác Nhận Giao Dịch", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in [self.user_a.id, self.user_b.id]:
            await interaction.response.send_message("❌ Bạn không thuộc giao dịch này!", ephemeral=True)
            return

        if self.is_done:
            await interaction.response.send_message("Giao dịch này đã hoàn tất hoặc đã kết thúc!", ephemeral=True)
            return

        if uid == self.user_a.id:
            self.confirmed_a = True
        elif uid == self.user_b.id:
            self.confirmed_b = True

        # Nếu cả 2 đều đã xác nhận -> Thực hiện giao dịch an toàn (Chống clone & check lại inventory tại thời điểm chốt)
        if self.confirmed_a and self.confirmed_b:
            self.is_done = True
            for child in self.children:
                child.disabled = True

            # Kiểm tra inventory người A
            pa = get_player(self.user_a.id, self.user_a.display_name)
            pb = get_player(self.user_b.id, self.user_b.display_name)

            for cid, cnt in self.offer_a:
                cid_str = str(cid)
                if pa.get("inventory", {}).get(cid_str, 0) < cnt:
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            title="❌ GIAO DỊCH THẤT BẠI!",
                            description=f"{self.user_a.mention} không còn đủ số lượng thẻ **#{cid}** trong túi đồ!",
                            color=0xEF4444
                        ),
                        view=None
                    )
                    return

            for cid, cnt in self.offer_b:
                cid_str = str(cid)
                if pb.get("inventory", {}).get(cid_str, 0) < cnt:
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            title="❌ GIAO DỊCH THẤT BẠI!",
                            description=f"{self.user_b.mention} không còn đủ số lượng thẻ **#{cid}** trong túi đồ!",
                            color=0xEF4444
                        ),
                        view=None
                    )
                    return

            # Chuyển thẻ từ A sang B
            for cid, cnt in self.offer_a:
                cid_str = str(cid)
                pa["inventory"][cid_str] -= cnt
                if pa["inventory"][cid_str] <= 0:
                    del pa["inventory"][cid_str]
                pb["inventory"][cid_str] = pb.get("inventory", {}).get(cid_str, 0) + cnt
                pb["pull_stats"][cid_str] = pb.get("pull_stats", {}).get(cid_str, 0) + cnt
                if cid not in pb.get("unlocked_cards", []):
                    pb.setdefault("unlocked_cards", []).append(cid)

            # Chuyển thẻ từ B sang A
            for cid, cnt in self.offer_b:
                cid_str = str(cid)
                pb["inventory"][cid_str] -= cnt
                if pb["inventory"][cid_str] <= 0:
                    del pb["inventory"][cid_str]
                pa["inventory"][cid_str] = pa.get("inventory", {}).get(cid_str, 0) + cnt
                pa["pull_stats"][cid_str] = pa.get("pull_stats", {}).get(cid_str, 0) + cnt
                if cid not in pa.get("unlocked_cards", []):
                    pa.setdefault("unlocked_cards", []).append(cid)

            # Lưu dữ liệu an toàn
            save_player(pa)
            save_player(pb)

            success_embed = discord.Embed(
                title="🎉 GIAO DỊCH THÀNH CÔNG RỰC RỠ!",
                description=(
                    f"Chúc mừng {self.user_a.mention} và {self.user_b.mention} đã hoàn tất trao đổi thẻ bài!\n"
                    "Thẻ bài đã được cập nhật ngay lập tức vào kho `/collection` của cả hai!"
                ),
                color=0x10B981
            )
            await interaction.response.edit_message(embed=success_embed, view=None)
        else:
            await interaction.response.edit_message(embed=self.get_trade_embed(), view=self)

    @discord.ui.button(label="❌ Hủy Giao Dịch", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in [self.user_a.id, self.user_b.id]:
            await interaction.response.send_message("❌ Bạn không có quyền hủy giao dịch này!", ephemeral=True)
            return
        self.is_done = True
        for child in self.children:
            child.disabled = True
        cancel_embed = discord.Embed(
            title="🚫 GIAO DỊCH ĐÃ BỊ HỦY BỎ",
            description=f"Giao dịch đã bị hủy bởi {interaction.user.mention}.",
            color=0xEF4444
        )
        await interaction.response.edit_message(embed=cancel_embed, view=None)

async def send_trade_msg(ctx_or_interaction, content=None, embed=None, view=None, ephemeral=False):
    if isinstance(ctx_or_interaction, discord.Interaction):
        if ctx_or_interaction.response.is_done():
            return await ctx_or_interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)
        else:
            return await ctx_or_interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=ephemeral)
    else:
        return await ctx_or_interaction.send(content=content, embed=embed, view=view)

async def handle_trade(ctx_or_interaction, user: Union[discord.Member, discord.User], your: str = None, their: str = None):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    if not user:
        await send_trade_msg(ctx_or_interaction, "⚠️ Vui lòng tag người chơi bạn muốn trao đổi! Ví dụ: `/trade user:@nguoidung your:13 their:16`", ephemeral=True)
        return

    if user.id == author.id:
        await send_trade_msg(ctx_or_interaction, "⚠️ Bạn không thể giao dịch với chính mình!", ephemeral=True)
        return

    if user.bot:
        await send_trade_msg(ctx_or_interaction, "⚠️ Bạn không thể giao dịch với bot!", ephemeral=True)
        return

    pa = get_player(author.id, author.display_name)
    pb = get_player(user.id, user.display_name)

    # Phân tích thẻ đưa ra
    offer_a = parse_trade_offer(your) if your else []
    offer_b = parse_trade_offer(their) if their else []

    if not offer_a and not offer_b:
        await send_trade_msg(
            ctx_or_interaction,
            "⚠️ Bạn cần chỉ định ít nhất 1 thẻ để trao đổi!\n"
            "Ví dụ: `/trade user:@User your:13 their:16` (Đổi thẻ #13 của bạn lấy #16 của đối phương)\n"
            "Hoặc: `/trade user:@User your:reimu` (Tặng Reimu cho đối phương)",
            ephemeral=True
        )
        return

    # Kiểm tra xem A có sở hữu thẻ đưa ra không
    for cid, cnt in offer_a:
        cid_str = str(cid)
        avail = pa.get("inventory", {}).get(cid_str, 0)
        c = CARDS_DATA[cid]
        if avail < cnt:
            await send_trade_msg(ctx_or_interaction, f"❌ Bạn không có đủ thẻ **{format_card_id(c['id'])} {c['name']}** (Cần: {cnt}, Có: {avail})!", ephemeral=True)
            return

    # Kiểm tra xem B có sở hữu thẻ yêu cầu không
    for cid, cnt in offer_b:
        cid_str = str(cid)
        avail = pb.get("inventory", {}).get(cid_str, 0)
        c = CARDS_DATA[cid]
        if avail < cnt:
            await send_trade_msg(ctx_or_interaction, f"❌ {user.display_name} không có đủ thẻ **{format_card_id(c['id'])} {c['name']}** (Cần: {cnt}, Có: {avail})!", ephemeral=True)
            return

    view = TradeConfirmationView(author, user, offer_a, offer_b)
    await send_trade_msg(ctx_or_interaction, embed=view.get_trade_embed(), view=view)

@bot.tree.command(name="trade", description="🤝 Trao đổi thẻ bài Touhou an toàn với người chơi khác")
@app_commands.describe(
    user="Người chơi bạn muốn trao đổi",
    your="Thẻ bạn đưa ra (ID hoặc tên, ví dụ: 13 hoặc '13 2' hoặc 'reimu')",
    their="Thẻ bạn muốn nhận (ID hoặc tên, ví dụ: 16 hoặc '16 1' hoặc 'sakuya')"
)
async def slash_trade(interaction: discord.Interaction, user: discord.Member, your: Optional[str] = None, their: Optional[str] = None):
    await handle_trade(interaction, user, your, their)

@bot.command(name="trade", aliases=["traodoi", "giaodich"])
async def prefix_trade(ctx, user: discord.Member = None, *, details: str = None):
    if not user:
        await ctx.send("⚠️ Cú pháp: `!trade @nguoidung [thẻ_bạn] [thẻ_họ]` (Ví dụ: `!trade @User 13 16`)")
        return

    your = None
    their = None
    if details:
        parts = details.strip().split()
        if len(parts) >= 2:
            your = parts[0]
            their = parts[1]
        elif len(parts) == 1:
            your = parts[0]

    await handle_trade(ctx, user, your=your, their=their)

# ==============================================================================
# HỆ THỐNG LỆNH BOSS & ADMIN RAID
# ==============================================================================
@bot.tree.command(name="boss_status", description="👹 Kiểm tra thời gian hồi chiêu và trạng thái Boss Raid hiện tại")
async def slash_boss_status(interaction: discord.Interaction):
    global active_raid, boss_cooldown_until
    check_and_clean_expired_raid()
    now_ts = time.time()
    rem = max(0, int(boss_cooldown_until - now_ts))
    if active_raid is not None:
        cfg = active_raid.get("boss_config", BOSS_CONFIG)
        count = len(active_raid.get("participants", []))
        embed = discord.Embed(
            title=f"🚨 ĐANG CÓ DỊ BIẾN: {cfg['name'].upper()}!",
            description=(
                f"🔥 **Trạng thái:** {'Đang chiến đấu kịch liệt!' if active_raid.get('started') else 'Đang chuẩn bị nghênh chiến!'}\n"
                f"👥 **Người tham gia:** `{count}/{cfg['max_players']} dũng giả`\n"
                f"📍 Hãy tìm thông báo Raid gần nhất trong kênh để bấm nút tham gia!"
            ),
            color=0xDC2626
        )
        embed.set_thumbnail(url=cfg["image"])
    elif rem > 0:
        mins = rem // 60
        secs = rem % 60
        embed = discord.Embed(
            title="⏳ BOSS RAID ĐANG TRONG THỜI GIAN HỒI CHIÊU",
            description=(
                f"⛩️ Đền Hakurei đang tĩnh lặng sau trận chiến dị biến trước đó.\n\n"
                f"⏱️ **Thời gian hồi chiêu còn lại:** **`{mins:02d} phút {secs:02d} giây`**\n"
                f"💡 Khi hết thời gian hồi chiêu, Boss Reimu hoặc Seiki Dị Hình có thể xuất hiện bất kỳ lúc nào khi mọi người trò chuyện!"
            ),
            color=0x3B82F6
        )
    else:
        embed = discord.Embed(
            title="⛩️ BOSS RAID ĐÃ SẴN SÀNG XUẤT HIỆN!",
            description=(
                "⚡ Dị khí đang tụ lại xung quanh đền Hakurei...\n\n"
                "• **Boss Reimu Dị Hình** hoặc **Seiki Dị Hình** có thể xuất hiện bất cứ lúc nào khi các pháp sư nhắn tin (5% cơ hội)!\n"
                "• Quản trị viên cũng có thể sử dụng lệnh `/boss admin spawn` để triệu hồi Boss khẩn cấp!"
            ),
            color=0x10B981
        )
    embed.set_footer(text="Hakurei Boss Raid System • Hồi chiêu chuẩn 15 phút")
    await interaction.response.send_message(embed=embed)

@bot.command(name="boss_status", aliases=["boss"])
async def prefix_boss_status(ctx):
    global active_raid, boss_cooldown_until
    check_and_clean_expired_raid()
    now_ts = time.time()
    rem = max(0, int(boss_cooldown_until - now_ts))
    if active_raid is not None:
        cfg = active_raid.get("boss_config", BOSS_CONFIG)
        count = len(active_raid.get("participants", []))
        await ctx.send(f"🚨 **Đang có Boss Raid ({cfg['name']})!** Hiện có `{count}/{cfg['max_players']}` người tham gia!")
    elif rem > 0:
        mins = rem // 60
        secs = rem % 60
        await ctx.send(f"⏳ Boss Raid đang hồi chiêu! Còn lại: **`{mins:02d} phút {secs:02d} giây`**.")
    else:
        await ctx.send("⛩️ Boss Raid đã sẵn sàng! Hãy nhắn tin để Boss có cơ hội tự xuất hiện, hoặc nhờ Admin dùng `!boss admin spawn`!")

@bot.tree.command(name="boss_admin", description="👑 [ADMIN] Bảng điều khiển quản lý Boss Raid")
async def slash_boss_admin(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ Bạn không có quyền sử dụng bảng điều khiển Boss Admin!", ephemeral=True)
        return
    embed = discord.Embed(
        title="👑 [ADMIN] BẢNG ĐIỀU KHIỂN BOSS RAID",
        description=(
            "Các lệnh quản trị Boss dành riêng cho Quản trị viên:\n\n"
            "• `/boss_spawn [boss_type]` (hoặc `/admin_boss_spawn`): Triệu hồi Boss ngay lập tức (Hỗ trợ chọn Reimu hoặc Seiki)\n"
            "• `/boss_reset` (hoặc `/admin_boss_reset`): Dọn sạch trận Boss đang kẹt và xóa hồi chiêu về 0\n"
            "• `!boss admin spawn`: Triệu hồi qua prefix\n"
            "• `!boss admin reset`: Reset qua prefix"
        ),
        color=0xF59E0B
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="boss_spawn", description="👑 [ADMIN] Triệu hồi ngay lập tức Boss Raid (Reimu hoặc Seiki)")
@app_commands.describe(boss_type="Chọn loại Boss: seiki (Mặc định) hoặc reimu")
@app_commands.choices(boss_type=[
    app_commands.Choice(name="Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư (Nhóm T)", value="seiki"),
    app_commands.Choice(name="Reimu Dị Hình - 2 Phase Thức Tỉnh", value="reimu")
])
async def slash_admin_boss_spawn(interaction: discord.Interaction, boss_type: Optional[str] = "seiki"):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ Bạn không có quyền triệu hồi Boss!", ephemeral=True)
        return
    chosen = boss_type or "seiki"
    await interaction.response.send_message(f"👑 **[ADMIN]** Đang tiến hành triệu hồi **{chosen.upper()} BOSS RAID**...", ephemeral=True)
    await admin_spawn_boss(interaction.channel, interaction.user, boss_type=chosen)

@bot.tree.command(name="boss_reset", description="👑 [ADMIN] Reset toàn bộ Boss Raid bị kẹt và đưa hồi chiêu về 0")
async def slash_admin_boss_reset(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ Bạn không có quyền reset Boss!", ephemeral=True)
        return
    await admin_reset_boss(interaction, interaction.user)

# ==============================================================================
# HỆ THỐNG TRỢ GIÚP & TRA CỨU (/help, /wiki)
# ==============================================================================
async def handle_help(ctx_or_interaction):
    embed = discord.Embed(
        title="⛩️ HAKUREI REIMU DISCORD BOT - DANH SÁCH LỆNH",
        description="Chào mừng bạn đến với đền Hakurei! Dưới đây là toàn bộ các lệnh hỗ trợ:",
        color=0xF43F5E
    )
    embed.add_field(
        name="🌸 Hướng Dẫn & Khởi Đầu:",
        value="• `/tutorial` hoặc `!tutorial`: Khóa huấn luyện Tân Thủ 3 bước (Nhận thẻ, xếp team, xuất trận)\n• `/daily_quest` hoặc `!quest`: Xem 3/3 Nhiệm vụ Hàng Ngày (+Vé pull, tích lũy nhận +10 vé)",
        inline=False
    )
    embed.add_field(
        name="🎴 Gacha & Bộ Sưu Tập:",
        value="• `/pull [số_lượng]` hoặc `!pull`: Quay gacha Touhou (5 lượt miễn phí mỗi ngày)\n• `/collection [trang]` hoặc `!collection`: Xem toàn bộ thẻ bài đã thu thập\n• `/card_info [tên/id]` hoặc `!card_info`: Tra cứu chỉ số, kỹ năng và artwork nhân vật (Hỗ trợ Thẻ Seiki T1)\n• `/check [tên/id]`: Tra cứu nhanh thẻ bài",
        inline=False
    )
    embed.add_field(
        name="⚔️ Chiến Đấu & Đội Hình:",
        value="• `/team [action] [id_the]` hoặc `!team`: Quản lý đội hình 3 thẻ bài (view, add, remove, clear)\n• `/battle` hoặc `!battle`: Đấu PvE với cư dân Gensokyo (Xem GIF trực tiếp)\n• `/pvp @nguoidung` hoặc `!pvp @nguoidung`: Thách đấu người chơi khác",
        inline=False
    )
    embed.add_field(
        name="🤝 Giao Dịch & Mảnh Thẻ:",
        value="• `/trade user:@User your:13 their:16`: Giao dịch thẻ bài chống clone an toàn\n• `/t shards` hoặc `!shards`: Xem kho Mảnh Seiki\n• `/t translate`: Ghép 10 Mảnh Seiki thành Thẻ Seiki Đệ Pháp Toàn Năng (Rank T)",
        inline=False
    )
    embed.add_field(
        name="🌟 Tiến Hóa & Đột Phá:",
        value="• `/evol [nhan_vat]` hoặc `!evol`: Tiến hóa Reimu, Sakuya, Marisa lên Ace 2 ⭐⭐ (+300 ATK, +300 HP, kỹ năng độc quyền)",
        inline=False
    )
    embed.add_field(
        name="👹 Boss Raid Dị Biến:",
        value="• `/boss_status` hoặc `!boss`: Kiểm tra thời gian hồi chiêu và trạng thái Boss\n• Tự động xuất hiện khi chat (5% cơ hội, hồi chiêu 15 phút)",
        inline=False
    )
    embed.set_footer(text="Gensokyo Card Battle • Hỗ trợ cả Slash Command (/) và Prefix (!)")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="help", description="⛩️ Hiển thị toàn bộ danh sách lệnh và hướng dẫn sử dụng bot")
async def slash_help(interaction: discord.Interaction):
    await handle_help(interaction)

@bot.command(name="help", aliases=["trogiup", "lenh"])
async def prefix_help(ctx):
    await handle_help(ctx)

@bot.tree.command(name="wiki", description="📖 Tra cứu bách khoa toàn thư Touhou Project (Sử dụng AI)")
@app_commands.describe(chu_de="Nhân vật, địa điểm hoặc sự kiện Touhou cần tra cứu")
async def touhou_wiki(interaction: discord.Interaction, chu_de: str):
    await interaction.response.defer()
    sys_prompt = "Bạn là bách khoa toàn thư Touhou Project. Hãy giải thích chi tiết, chuẩn lore, hấp dẫn về chủ đề được hỏi bằng Tiếng Việt."
    try:
        ans = await ask_gemini([types.Content(role="user", parts=[types.Part.from_text(text=f"Giải thích về: {chu_de}")])], sys_prompt)
        embed = discord.Embed(title=f"📖 TOUHOU WIKI: {chu_de.upper()}", description=ans[:4000], color=0x3B82F6)
        embed.set_footer(text="Hakurei Shrine Archive • Gemini Flash")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Không thể tra cứu lúc này: `{e}`")

@bot.tree.command(name="clear_memory", description="🧹 Xóa lịch sử trò chuyện AI giữa bạn và Reimu trong kênh này")
async def slash_clear_memory(interaction: discord.Interaction):
    reset_memory(interaction.channel.id, interaction.user.id)
    await interaction.response.send_message("🧹 Reimu đã 'quên sạch' những gì vừa nói với bạn trong kênh này rồi!", ephemeral=True)

@bot.tree.command(name="sync_commands", description="👑 [ADMIN] Đồng bộ hóa toàn bộ Slash Commands với Discord")
async def slash_sync_commands(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ Chỉ có Quản trị viên mới có thể đồng bộ lệnh!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã đồng bộ thành công `{len(synced)} lệnh Slash` toàn cục!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi đồng bộ: `{e}`")

@bot.command(name="sync_commands")
async def prefix_sync_commands(ctx):
    if not is_authorized_admin(ctx.author):
        await ctx.send("⛔ Bạn không có quyền dùng lệnh này!")
        return
    msg = await ctx.send("⏳ Đang đồng bộ hóa Slash Commands...")
    try:
        synced = await bot.tree.sync()
        await msg.edit(content=f"✅ Đã đồng bộ thành công `{len(synced)} lệnh Slash` toàn cục!")
    except Exception as e:
        await msg.edit(content=f"❌ Lỗi đồng bộ: `{e}`")

@bot.tree.command(name="dbcheck", description="🔍 [ADMIN] Kiểm tra trạng thái kết nối cơ sở dữ liệu MongoDB Atlas")
async def slash_dbcheck(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ Chỉ có Quản trị viên mới có thể kiểm tra database!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    is_ok, msg = test_and_connect_mongo()
    embed = discord.Embed(
        title="🔍 KIỂM TRA KẾT NỐI MONGODB ATLAS",
        description=f"• **Trạng thái:** {'✅ Hoạt động tốt' if is_ok else '❌ Gặp lỗi (Đang dùng SQLite dự phòng)'}\n• **Chi tiết:** `{msg}`",
        color=0x10B981 if is_ok else 0xEF4444
    )
    await interaction.followup.send(embed=embed)

# ==============================================================================
# KHỞI CHẠY BOT DISCORD
# ==============================================================================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN trong .env!", flush=True)
    else:
        bot.run(DISCORD_TOKEN)
