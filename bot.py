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
# 9. BẢN CẬP NHẬT HOÀN CHỈNH:
#    - Thêm ở Boss Seiki Drop: Hiển thị và bảo đảm 2.5% cơ hội rơi ra Seiki Shards (10 mảnh = 1 thẻ [T] Seiki).
#    - Hoạt ảnh GIF chuẩn không bị trùng lặp hoặc thiếu:
#      * Blitz Attack: https://klipy.com/gifs/naoya-jujutsu-kaisen
#      * Multi Master Spark: 30% gây 1.5x sát thương 1 lần/trận - gif: https://klipy.com/gifs/marisa-master-spark
#      * Medicine Sign: 20% hồi phục cho bản thân 1 lần/trận - gif: https://klipy.com/gifs/shoko-ieiri-2
#    - Sửa triệt để lỗi thẻ Nhóm T (T1 Seiki) không tham chiến được trong PvP, Raid, Battle (khắc phục ép kiểu int và định dạng :02d).
#    - Bổ sung tính năng kiểm tra thẻ Nhóm T trong lệnh /card_info và /check.
#    - Buff riêng Master Spark của Marisa Ace: tăng từ 1.5x lên 2.0x sát thương gốc (2x DMG)!
# ==============================================================================

import os
import re
import time
import json
import random
import asyncio
import threading
from threading import Thread
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional, Union, List, Dict
from http.server import HTTPServer, BaseHTTPRequestHandler
from flask import Flask
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
ACE_POWER_BUFF = 300  # +300 ATK (Buff theo yêu cầu)
ACE_HP_BUFF = 300     # +300 Máu (Buff theo yêu cầu)

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
# 3. TOUHOU CARDS DATABASE (26 NHÂN VẬT CHUẨN THÔNG SỐ + NHÓM T ĐẶC BIỆT)
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
# BUFF RIÊNG MARISA ACE: 1.5x -> 2.0x SÁT THƯƠNG GỐC (2x DMG)
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
        "skill_name": "Bát Quái Lô - Master Spark (Sát Thương ×2.0)",
        "skill_desc": "Kích hoạt 1 lần trong trận: 30% tung ra Master Spark với sát thương ×2.0 lần sát thương gốc!",
        "skill_gif": "https://klipy.com/gifs/marisa-master-spark",
        "bonus_power": 300,
        "bonus_hp": 300
    }
}
EVOL_CONFIG["13"] = EVOL_CONFIG[13]
EVOL_CONFIG["16"] = EVOL_CONFIG[16]
EVOL_CONFIG["17"] = EVOL_CONFIG[17]

# ==============================================================================
# 3.1 CHI TIẾT NĂNG LỰC & KỸ NĂNG 26 NHÂN VẬT TOUHOU + THẺ T1 SEIKI
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
    17: {"title": "Phù Thủy Bình Thường", "skill_name": "Bát Quái Lô - Master Spark", "skill_desc": "Ma thuật ánh sáng và nhiệt độ cao. [Ace 2 ⭐⭐]: Bắn đại bác ma thuật Master Spark gây sát thương ×2.0 lần sát thương gốc (Tỷ lệ 30% 1 lần trong trận)!"},
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
        "skill_desc": "Thẻ bài thần thoại nhóm T. Sở hữu 3 tuyệt kỹ: Fantasy Seal (40% miễn thương 1 lần), Master Spark (30% x1.5 sát thương 1 lần), Medicine Sign (20% hồi phục cho bản thân 1 lần). Tuân thủ nghiêm ngặt nguyên tắc tối đa 1 chiêu mỗi hiệp và mỗi chiêu kích hoạt 1 lần trong trận!"
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
            "👑 **HOÀN THÀNH TOÀN BỘ 3/3 NHIỆM VỤ NGÀY!**\\n"
            "⛩️ **Reimu:** *\\\"10 lượt pull đây, lo mà sử dụng cẩn thận\\\"*\\n"
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
                card_tag = format_card_id(c['cid'])
                lbl = f"{ace_tag}{card_tag} {c['raw_name']} [{c['rank']}]"[:100]
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
        card_id_str = format_card_id(c['cid'])
        embed = discord.Embed(
            title=f"👁️ TOÀN BỘ ĐỘI HÌNH ĐỐI THỦ: {self.opp_name} (Lv.{self.opp_level})",
            description=f"Soi chiến thuật thẻ bài **{'⭐ [Ace 2] ' if is_ace else ''}{card_id_str} {c['raw_name']}** của đối phương!",
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
            value=f"**{c['power']:,} DMG**\\n{buff_breakdown}",
            inline=True
        )

        hp_breakdown = f"*(Gốc: {c['base_hp']:,} + Buff: {c['hp'] - c['base_hp']:,})*"
        if is_ace:
            hp_breakdown = f"*(Gốc: {c['base_hp']:,} + Buff Lv: {c['hp'] - c['base_hp'] - ACE_HP_BUFF:,} + Ace: +{ACE_HP_BUFF})*"
        embed.add_field(
            name="❤️ Sinh Mệnh (HP):",
            value=f"**{c['hp']:,} HP**\\n{hp_breakdown}",
            inline=True
        )

        skill_text = c.get("skill") or "Tấn công Danmaku cơ bản"
        cid_norm = normalize_card_id(c["cid"])
        if is_ace and cid_norm in [13, 16, 17]:
            if cid_norm == 13:
                skill_text += "\\n🛡️ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Vô Tưởng Chuyển Sinh* né toàn bộ sát thương."
            elif cid_norm == 16:
                skill_text += "\\n⏳ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Thời Gian Đóng Băng* khiến đối phương mất lượt."
            elif cid_norm == 17:
                skill_text += "\\n🌟 **[Ace 2 Hiệu Ứng]** 30% kích hoạt *Master Spark* bộc phá ×2.0 sát thương."
        elif str(cid_norm).lower() == "t1":
            skill_text = "🛡️ **Fantasy Seal (40%)**: Miễn thương 1 lần\\n🌟 **Master Spark (30%)**: Gây 1.5x sát thương 1 lần\\n💚 **Medicine Sign (20%)**: Hồi phục cho bản thân 1 lần"
        embed.add_field(name="✨ Kỹ Năng / Tuyệt Kỹ Danmaku:", value=f"*{skill_text}*", inline=False)

        summary_lines = []
        for i, card in enumerate(self.opp_cards):
            arrow = "👉 " if i == self.selected_idx else "• "
            ace_star = "⭐ " if card.get("is_ace2") else ""
            ace_label = " `[Ace 2]`" if card.get("is_ace2") else ""
            summary_lines.append(
                f"{arrow}{ace_star}**{format_card_id(card['cid'])} {card['raw_name']}** `[{card['rank']}]`{ace_label} ⚔️ `{card['power']:,} DMG` | ❤️ `{card['hp']:,} HP`"
            )
        embed.add_field(name="👥 Danh Sách Đầy Đủ 3 Thẻ Đối Thủ:", value="\\n".join(summary_lines), inline=False)
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
            f"👑 **Thực hiện bởi:** {author.mention}\\n"
            f"✅ **Trạng thái:** {'Đã giải phóng Boss Raid bị kẹt trước đó!' if was_stuck else 'Boss Raid đã được dọn sạch hoàn toàn.'}\\n"
            "⏱️ **Hồi chiêu:** Đã đưa thời gian hồi chiêu về **0 giây**.\\n"
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
                f"⏰ **ĐÃ HẾT 2 PHÚT CHUẨN BỊ!**\\n"
                f"⚔️ **{len(participants)} Dũng Giả** ({names_str}) đồng loạt dàn quân xuất trận!\\n"
                f"👹 **{raid_data.get('boss_config', {}).get('name', 'Boss Dị Hình')}** gầm thét kinh thiên động địa — **TRẬN ĐẠI CHIẾN CHÍNH THỨC BẮT ĐẦU!**"
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
                "🌌 **Dị hình đã xé toạc không gian và trốn thoát do không có pháp sư nào dám nghênh chiến!**\\n"
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
        reimu_line = f"🌸 **Reimu thảng thốt:** *\\\"{cfg['reimu_quote']}\\\"*\n\n"
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
                "• ⚡ **Blitz Attack (20%):** Oanh tạc chớp nhoáng gây **4,000 DMG** lên toàn bộ thẻ tiền tuyến!\n"
                "*(Lưu ý: Không bao giờ kích hoạt trùng chiêu trong cùng một hiệp)*"
            ),
            inline=False
        )
        embed.add_field(
            name="🎁 Phần Thưởng Thanh Tẩy Boss:",
            value="• 10% cơ hội nhận **10 Vé Pull**, 40% nhận **5 Vé**, 50% nhận **3 Vé**!\n• 🔮 **2.5% cơ hội rơi ra 1 Mảnh Seiki Shards** (Thu thập 10 mảnh để đổi thẻ [T] Seiki Đệ Pháp Toàn Năng)!\n• Nhận thêm **+100 XP** và điểm danh nhiệm vụ diệt Boss!",
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
                "• **Phase 1 (30k HP):** 10% ra **10 Vé**, 40% ra **5 Vé**, 50% ra **3 Vé**!\n"
                f"• **Chuyển Phase 2 ({BOSS_PHASE2_CONFIG['hp']:,} HP / {BOSS_PHASE2_CONFIG['power']:,} DMG chia đều):** Hồi sinh & phục hồi **100% HP toàn bộ thẻ bài**!\n"
                "• **Phase 2:** 10% ra **20 Vé**, 40% ra **10 Vé**, 50% ra **5 Vé**!\n"
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

        current_team = [cid for cid in player.get("team", []) if (cid in CARDS_DATA or normalize_card_id(cid) in CARDS_DATA) and not is_card_locked(player, cid)]
        if len(current_team) < 3:
            owned_ids = [cid for cid, cnt in player.get("inventory", {}).items() if cnt > 0 and (cid in CARDS_DATA or normalize_card_id(cid) in CARDS_DATA) and not is_card_locked(player, cid)]
            owned_ids.sort(key=lambda cid: CARDS_DATA.get(normalize_card_id(cid), CARDS_DATA.get(cid, {})).get("power", 0), reverse=True)
            for cid in owned_ids:
                norm = normalize_card_id(cid)
                if norm and norm not in current_team and cid not in current_team:
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
        team_cids = [cid for cid in p.get("team", []) if (cid in CARDS_DATA or normalize_card_id(cid) in CARDS_DATA) and not is_card_locked(p, cid)]
        if len(team_cids) < 3:
            owned_ids = [cid for cid, cnt in p.get("inventory", {}).items() if cnt > 0 and (cid in CARDS_DATA or normalize_card_id(cid) in CARDS_DATA) and not is_card_locked(p, cid)]
            owned_ids.sort(key=lambda cid: CARDS_DATA.get(normalize_card_id(cid), CARDS_DATA.get(cid, {})).get("power", 0), reverse=True)
            for cid in owned_ids:
                norm = normalize_card_id(cid)
                if norm and norm not in team_cids and cid not in team_cids:
                    team_cids.append(cid)
                if len(team_cids) >= 3:
                    break
            p["team"] = team_cids
            save_player(p)

        team_cards = []
        for cid in team_cids[:3]:
            card = CARDS_DATA.get(cid) or CARDS_DATA.get(normalize_card_id(cid))
            if card:
                is_ace2 = is_card_ace2(p, cid)
                ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
                ace_hp = ACE_HP_BUFF if is_ace2 else 0
                card_pwr = card["power"] + lvl_buff_pwr + ace_pwr
                card_hp = card["hp"] + lvl_buff_hp + ace_hp
                card_name = f"[Ace 2 ⭐⭐] {format_card_id(card['id'])} {card['name']}" if is_ace2 else f"{format_card_id(card['id'])} {card['name']}"
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
                f"🌸 **Reimu thảng thốt:** *\"{boss_cfg['reimu_quote']}\"*\n\n"
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
                elif roll_s < 0.35:
                    seiki_invul = True
                    seiki_action = "fantasy_seal"
                elif roll_s < 0.55:
                    seiki_action = "blitz_attack"
                else:
                    seiki_action = "normal"

        round_player_dmg = 0
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            card_dmg = ac["power"]
            # BUFF RIÊNG MARISA ACE: 2.0x DMG
            if ac["cid"] == 17 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/marisa-master-spark"
                    marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss!"
            
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
            # BUFF RIÊNG MARISA ACE: 2.0x DMG
            if ac["cid"] == 17 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/marisa-master-spark"
                    marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"

            # Kỹ năng Thẻ Seiki T1
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
                *([("🌟 Master Spark:", marisa_spark_notif, False)] if marisa_spark_notif else []),
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
            name="Đền Hakurei | /help | /pull | /battle | Boss 30k HP"
        )
    )

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.author == bot.user:
        return

    content_lower = message.content.lower()
    clean_stripped = message.content.strip().lower()

    if clean_stripped in ["boss admin spawn", "!boss admin spawn", "!boss_admin spawn"] or clean_stripped.startswith("boss admin spawn"):
        if not is_authorized_admin(message.author):
            await message.channel.send(f"⛔ {message.author.mention} Ngươi không có quyền hạn! Chỉ có bố Seiki hoặc Quản Trị Viên mới được phép điều động Boss Raid!")
            return
        b_type = None
        if "seiki" in clean_stripped:
            b_type = "seiki"
        elif "reimu" in clean_stripped:
            b_type = "reimu"
        await admin_spawn_boss(message.channel, message.author, boss_type=b_type)
        return

    if clean_stripped in ["boss admin reset", "!boss admin reset", "!boss_admin reset"] or clean_stripped.startswith("boss admin reset"):
        if not is_authorized_admin(message.author):
            await message.channel.send(f"⛔ {message.author.mention} Ngươi không có quyền hạn! Chỉ có bố Seiki hoặc Quản Trị Viên mới được phép reset Boss Raid!")
            return
        await admin_reset_boss(message.channel, message.author)
        return

    global active_raid, boss_cooldown_until
    check_and_clean_expired_raid()
    now_ts = time.time()
    
    if active_raid is None and now_ts >= boss_cooldown_until and not content_lower.startswith("!") and not content_lower.startswith("/"):
        spawn_roll = random.random()
        if spawn_roll < 0.05:
            # 5% xuất hiện Seiki Dị Hình (nếu ra Seiki thì không ra Reimu)
            await spawn_boss_raid(message.channel, None, boss_type="seiki")
        elif spawn_roll < 0.10:
            # 5% xuất hiện Reimu Dị Hình (nếu ra Reimu thì không ra Seiki)
            await spawn_boss_raid(message.channel, None, boss_type="reimu")

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
# 8. CƠ CHẾ GACHA PULL TOUHOU & TỰ ĐỘNG MỞ KHÓA THẺ KHI PULL LẠI
# ==============================================================================
def execute_single_pull(player):
    roll = random.random()
    if roll < 0.0001: chosen = random.choice(CARDS_BY_RANK["SS"])
    elif roll < 0.1001: chosen = random.choice(CARDS_BY_RANK["S"])
    elif roll < 0.3501: chosen = random.choice(CARDS_BY_RANK["A"])
    elif roll < 0.6501: chosen = random.choice(CARDS_BY_RANK["B"])
    else: chosen = random.choice(CARDS_BY_RANK["C"])

    cid_str = str(chosen["id"])
    cid_int = int(chosen["id"])
    already_owned = player["inventory"].get(cid_str, 0)
    is_duplicate = already_owned > 0
    player["inventory"][cid_str] = already_owned + 1
    player.setdefault("pull_stats", {})[cid_str] = player.get("pull_stats", {}).get(cid_str, 0) + 1

    unlocked = player.setdefault("unlocked_cards", [])
    if cid_int not in unlocked:
        unlocked.append(cid_int)

    unlocked_from_lock = False
    locked_list = player.setdefault("locked_cards", [])
    if cid_int in locked_list:
        locked_list.remove(cid_int)
        unlocked_from_lock = True
    if cid_str in locked_list:
        locked_list.remove(cid_str)
        unlocked_from_lock = True

    converted_pulls = 0.0
    if is_duplicate:
        if chosen["rank"] == "SS": converted_pulls = 4.0
        elif chosen["rank"] == "S": converted_pulls = 2.0
        elif chosen["rank"] == "A": converted_pulls = 0.5
        elif chosen["rank"] == "B": converted_pulls = 1.0 / 3.0
        elif chosen["rank"] == "C": converted_pulls = 0.2
        player["pull_tickets"] += converted_pulls

    return chosen, is_duplicate, converted_pulls, unlocked_from_lock

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
@app_commands.describe(nguoi_dung="Người chơi bị xử phạt", id_the="ID thẻ (hoặc nhập 0 để tịch thu TOÀN BỘ)", so_luong="Số lượng thẻ (0 = tịch thu hết)")
async def slash_admin_confiscate(interaction: discord.Interaction, nguoi_dung: discord.Member, id_the: str = "0", so_luong: int = 0):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    target = get_player(nguoi_dung.id, nguoi_dung.display_name)
    inv = target.get("inventory", {})
    team = target.get("team", [])

    if id_the == "0" or id_the == 0:
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

    norm_id = normalize_card_id(id_the)
    if not norm_id or norm_id not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-26 hoặc t1)!", ephemeral=True)
        return

    card = CARDS_DATA[norm_id]
    cid_str = str(norm_id)
    owned = inv.get(cid_str, 0)
    if owned <= 0:
        await interaction.response.send_message(f"⚠️ {nguoi_dung.display_name} không sở hữu thẻ {format_card_id(card['id'])} {card['name']}!", ephemeral=True)
        return

    to_remove = owned if (so_luong <= 0 or so_luong >= owned) else so_luong
    inv[cid_str] = owned - to_remove
    if inv[cid_str] <= 0:
        del inv[cid_str]
        if norm_id in team: team.remove(norm_id)
        if cid_str in team: team.remove(cid_str)

    target["inventory"] = inv
    target["team"] = team
    save_player(target)
    embed = discord.Embed(
        title="⚖️ [TRỪNG PHẠT CHEAT] ĐÃ TƯỚC ĐOẠT THẺ BÀI!",
        description=f"🚨 **Admin:** {interaction.user.mention}\n👤 **Đối tượng:** {nguoi_dung.mention}\n🎴 **Thẻ bị tước:** `[{card['rank']}]` **{format_card_id(card['id'])} {card['name']}**\n🔢 **Số lượng:** `{to_remove}` lá (Còn lại: `{inv.get(cid_str, 0)}`)",
        color=0xDC2626
    )
    embed.set_thumbnail(url=card["image"])
    await interaction.response.send_message(embed=embed)

@bot.command(name="confiscate", aliases=["tuocdoat"])
async def prefix_admin_confiscate(ctx, member: discord.Member, card_id: str = "0", quantity: int = 0):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    target = get_player(member.id, member.display_name)
    inv = target.get("inventory", {})
    team = target.get("team", [])
    if card_id == "0" or card_id == 0:
        total = sum(inv.values())
        target["inventory"] = {}
        target["team"] = []
        save_player(target)
        await ctx.send(f"🚨 Đã tịch thu toàn bộ **{total} thẻ bài** của {member.mention}!")
        return
    norm_id = normalize_card_id(card_id)
    if not norm_id or norm_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-26 hoặc t1)!")
        return
    card = CARDS_DATA[norm_id]
    cid_str = str(norm_id)
    owned = inv.get(cid_str, 0)
    if owned <= 0:
        await ctx.send(f"⚠️ {member.display_name} không sở hữu thẻ này!")
        return
    to_rem = owned if (quantity <= 0 or quantity >= owned) else quantity
    inv[cid_str] = owned - to_rem
    if inv[cid_str] <= 0:
        del inv[cid_str]
        if norm_id in team: team.remove(norm_id)
        if cid_str in team: team.remove(cid_str)
    target["inventory"] = inv
    target["team"] = team
    save_player(target)
    await ctx.send(f"⚖️ Đã tịch thu **{to_rem}x [{card['rank']}] {format_card_id(card['id'])} {card['name']}** của {member.mention}!")

@bot.tree.command(name="admin_add_card", description="[CHỦ BOT DUY NHẤT] Cấp thẻ nhân vật Touhou vào kho đồ người chơi")
@app_commands.describe(id_the="ID thẻ (1-26 hoặc t1)", so_luong="Số lượng thẻ (mặc định: 1)", nguoi_dung="Người nhận (để trống nếu tự cấp cho bản thân)")
async def slash_admin_add_card(interaction: discord.Interaction, id_the: str, so_luong: int = 1, nguoi_dung: discord.Member = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    norm_id = normalize_card_id(id_the)
    if not norm_id or norm_id not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-26 hoặc t1)!", ephemeral=True)
        return
    so_luong = max(1, so_luong)
    target = nguoi_dung if nguoi_dung else interaction.user
    target_player = get_player(target.id, target.display_name)
    cid_str = str(norm_id)
    card = CARDS_DATA[norm_id]
    inv = target_player.setdefault("inventory", {})
    new_cnt = inv.get(cid_str, 0) + so_luong
    inv[cid_str] = new_cnt
    if norm_id not in target_player.get("unlocked_cards", []):
        target_player.setdefault("unlocked_cards", []).append(norm_id)
    target_player.setdefault("pull_stats", {})[cid_str] = target_player.get("pull_stats", {}).get(cid_str, 0) + so_luong
    save_player(target_player)
    embed = discord.Embed(
        title="🎁 [ADMIN] ĐÃ CẤP THẺ BÀI THÀNH CÔNG!",
        description=f"👑 **Admin:** {interaction.user.mention}\n👤 **Người nhận:** {target.mention}\n🎴 **Thẻ:** `[{card['rank']}]` **{format_card_id(card['id'])} {card['name']}**\n📦 **Số lượng cấp:** `+{so_luong}` lá (Hiện có: `{new_cnt}` lá)",
        color=0x10B981
    )
    embed.set_thumbnail(url=card["image"])
    await interaction.response.send_message(embed=embed)

@bot.command(name="addcard", aliases=["adminaddcard", "givecard"])
async def prefix_admin_add_card(ctx, card_id: str, quantity: int = 1, member: discord.Member = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    norm_id = normalize_card_id(card_id)
    if not norm_id or norm_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-26 hoặc t1)!")
        return
    quantity = max(1, quantity)
    target = member if member else ctx.author
    target_player = get_player(target.id, target.display_name)
    cid_str = str(norm_id)
    card = CARDS_DATA[norm_id]
    inv = target_player.setdefault("inventory", {})
    new_cnt = inv.get(cid_str, 0) + quantity
    inv[cid_str] = new_cnt
    if norm_id not in target_player.get("unlocked_cards", []):
        target_player.setdefault("unlocked_cards", []).append(norm_id)
    target_player.setdefault("pull_stats", {})[cid_str] = target_player.get("pull_stats", {}).get(cid_str, 0) + quantity
    save_player(target_player)
    await ctx.send(f"🎁 Đã cấp **+{quantity}x [{card['rank']}] {format_card_id(card['id'])} {card['name']}** cho {target.mention} (Hiện có: {new_cnt})!")

@bot.tree.command(name="admin_add_shard", description="[CHỦ BOT DUY NHẤT] Cấp mảnh đặc biệt (shards) cho người chơi")
@app_commands.describe(loai_shard="Loại mảnh (mặc định: seiki)", so_luong="Số lượng mảnh (mặc định: 10)", nguoi_dung="Người nhận (để trống nếu tự cấp cho bản thân)")
async def slash_admin_add_shard(interaction: discord.Interaction, loai_shard: str = "seiki", so_luong: int = 10, nguoi_dung: discord.Member = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    so_luong = max(1, so_luong)
    target = nguoi_dung if nguoi_dung else interaction.user
    target_player = get_player(target.id, target.display_name)
    s_key = loai_shard.lower().strip()
    if s_key in ["seiki", "t1", "dephap", "toannang"]:
        s_key = "seiki"
    shards = target_player.setdefault("shards", {})
    shards[s_key] = shards.get(s_key, 0) + so_luong
    save_player(target_player)
    embed = discord.Embed(
        title="🔮 [ADMIN] ĐÃ CẤP MẢNH NHÂN VẬT THÀNH CÔNG!",
        description=(
            f"👑 **Admin:** {interaction.user.mention}\n"
            f"👤 **Người nhận:** {target.mention}\n"
            f"💎 **Loại mảnh:** `{s_key}` (Mảnh Seiki Đệ Pháp Toàn Năng)\n"
            f"🔢 **Số lượng cấp:** `+{so_luong}` mảnh (Tổng kho: `{shards[s_key]}` mảnh)\n\n"
            f"💡 *Dùng `/t translate` để đổi 10 mảnh thành Thẻ [T] #t1 Seiki!*"
        ),
        color=0x8B5CF6
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name="addshard", aliases=["giveshard"])
async def prefix_admin_add_shard(ctx, loai_shard: str = "seiki", quantity: int = 10, member: discord.Member = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    quantity = max(1, quantity)
    target = member if member else ctx.author
    target_player = get_player(target.id, target.display_name)
    s_key = loai_shard.lower().strip()
    if s_key in ["seiki", "t1", "dephap", "toannang"]:
        s_key = "seiki"
    shards = target_player.setdefault("shards", {})
    shards[s_key] = shards.get(s_key, 0) + quantity
    save_player(target_player)
    await ctx.send(f"🔮 Đã cấp **+{quantity} Mảnh `{s_key}`** cho {target.mention} (Tổng kho: {shards[s_key]}/10)! Dùng `/t translate` để đổi thẻ.")

@bot.tree.command(name="admin_lock", description="[CHỦ BOT DUY NHẤT] Khóa lá bài đã sở hữu của người chơi (chỉ mở khi pull ra lại)")
@app_commands.describe(nguoi_dung="Người chơi bị khóa thẻ", id_the="ID lá bài (1-26 hoặc t1)")
async def slash_admin_lock(interaction: discord.Interaction, nguoi_dung: discord.Member, id_the: str):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ chủ bot mới có quyền khóa thẻ.", ephemeral=True)
        return

    norm_id = normalize_card_id(id_the)
    if not norm_id or norm_id not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-26 hoặc t1)!", ephemeral=True)
        return

    target = get_player(nguoi_dung.id, nguoi_dung.display_name)
    inv = target.get("inventory", {})
    cid_str = str(norm_id)
    owned = inv.get(cid_str, 0)
    unlocked = is_card_unlocked(target, norm_id)

    if owned <= 0 and not unlocked:
        await interaction.response.send_message(
            f"⚠️ **{nguoi_dung.display_name}** chưa từng sở hữu thẻ bài {format_card_id(CARDS_DATA[norm_id]['id'])} {CARDS_DATA[norm_id]['name']}! Không thể khóa.",
            ephemeral=True
        )
        return

    locked_list = target.setdefault("locked_cards", [])
    if norm_id in locked_list or cid_str in locked_list:
        await interaction.response.send_message(
            f"⚠️ Thẻ {format_card_id(norm_id)} của {nguoi_dung.mention} đã bị khóa từ trước rồi!",
            ephemeral=True
        )
        return

    locked_list.append(norm_id)

    team = target.get("team", [])
    removed_from_team = False
    if norm_id in team:
        team.remove(norm_id)
        target["team"] = team
        removed_from_team = True
    if cid_str in team:
        team.remove(cid_str)
        target["team"] = team
        removed_from_team = True

    save_player(target)
    card = CARDS_DATA[norm_id]

    removed_team_str = "• ⚠️ Đã tự động gỡ khỏi đội hình chiến đấu (/team)!\n" if removed_from_team else ""
    embed = discord.Embed(
        title="🔒 [ADMIN LOCK] ĐÃ NIÊM PHONG THẺ BÀI!",
        description=(
            f"👑 **Thực hiện bởi:** {interaction.user.mention}\n"
            f"👤 **Người chơi bị phạt:** {nguoi_dung.mention}\n"
            f"🎴 **Lá bài bị khóa:** `[{card['rank']}]` **{format_card_id(card['id'])} {card['name']}**\n\n"
            f"⚙️ **Cơ chế niêm phong:**\n"
            f"{removed_team_str}"
            f"• Cấm mang vào đội hình và cấm đem đi giao dịch (/trade).\n"
            f"• 🔓 **Cách duy nhất để mở khóa:** Người chơi bắt buộc phải quay gacha (`/pull`) trúng lại chính lá bài này!"
        ),
        color=0xDC2626
    )
    embed.set_thumbnail(url=card["image"])
    await interaction.response.send_message(embed=embed)

@bot.command(name="lock", aliases=["admin_lock", "adminlock"])
async def prefix_admin_lock(ctx, member: discord.Member, card_id: str):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return

    norm_id = normalize_card_id(card_id)
    if not norm_id or norm_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-26 hoặc t1)!")
        return

    target = get_player(member.id, member.display_name)
    cid_str = str(norm_id)
    inv = target.get("inventory", {})
    owned = inv.get(cid_str, 0)
    unlocked = is_card_unlocked(target, norm_id)

    if owned <= 0 and not unlocked:
        await ctx.send(f"⚠️ {member.display_name} chưa từng sở hữu thẻ bài này!")
        return

    locked_list = target.setdefault("locked_cards", [])
    if norm_id in locked_list or cid_str in locked_list:
        await ctx.send(f"⚠️ Thẻ này của {member.mention} đã bị khóa từ trước!")
        return

    locked_list.append(norm_id)
    if norm_id in target.get("team", []):
        target["team"].remove(norm_id)
    if cid_str in target.get("team", []):
        target["team"].remove(cid_str)

    save_player(target)
    card = CARDS_DATA[norm_id]
    await ctx.send(f"🔒 Đã khóa thẻ **[{format_card_id(card['id'])}] {card['name']}** của {member.mention}! Chỉ được mở khi pull trúng lại.")

@bot.tree.command(name="admin_reset_quest", description="[CHỦ BOT DUY NHẤT] Làm mới thủ công 3/3 Nhiệm Vụ Ngày cho người chơi (hoặc chính mình)")
@app_commands.describe(nguoi_dung="Chọn người chơi muốn reset nhiệm vụ (để trống = bản thân)")
async def slash_admin_reset_quest(interaction: discord.Interaction, nguoi_dung: Optional[discord.Member] = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message(f"⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ duy nhất chủ sở hữu Bot (<@{AUTHORIZED_ADMIN_ID}>) mới có quyền.", ephemeral=True)
        return
    target_user = nguoi_dung or interaction.user
    target = get_player(target_user.id, target_user.display_name)
    ensure_daily_quests(target, force_reset=True)
    save_player(target)
    await interaction.response.send_message(
        f"✅ Đã làm mới thủ công toàn bộ 3/3 Nhiệm Vụ Ngày cho **{target_user.display_name}** thành công!\n"
        f"📅 Ngày áp dụng: `{target['daily_quests']['date']}` (GMT+7).",
        ephemeral=True
    )

@bot.command(name="reset_quest", aliases=["admin_reset_quest", "resetquest"])
async def prefix_admin_reset_quest(ctx, member: Optional[discord.Member] = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    target_user = member or ctx.author
    target = get_player(target_user.id, target_user.display_name)
    ensure_daily_quests(target, force_reset=True)
    save_player(target)
    await ctx.send(f"✅ Đã làm mới thủ công toàn bộ 3/3 Nhiệm Vụ Ngày cho **{target_user.display_name}** thành công!")

# ==============================================================================
# 10. CƠ CHẾ TIẾN HÓA /evol (ACE 2 - KHẤU TRỪ CHI PHÍ, BUFF +300/+300, MARISA ACE 2)
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

    @discord.ui.button(label="🌟 [#17] Tiến Hóa Marisa Ace 2 (25 Thẻ)", style=discord.ButtonStyle.success, emoji="✨")
    async def button_evol_marisa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 17)

def execute_card_evolution(player, cid: int):
    cfg = EVOL_CONFIG.get(cid)
    if not cfg:
        return False, f"❌ Thẻ ID #{cid} hiện chưa hỗ trợ tính năng tiến hóa Ace 2!", None

    if is_card_ace2(player, cid):
        return False, f"⚠️ Thẻ **[#{cfg['id']:02d}] {cfg['name']}** của bạn đã đạt cảnh giới **{cfg['ace_level']}** từ trước rồi!", None

    cid_str = str(cid)
    inventory = player.get("inventory", {})
    current_cnt = inventory.get(cid_str, 0)
    req_cards = cfg["required_cards"]

    if current_cnt < req_cards:
        return (
            False,
            f"❌ Bạn chưa đủ số lượng thẻ **[#{cfg['id']:02d}] {cfg['name']}** trong túi đồ!\n"
            f"• Số thẻ hiện có: **{current_cnt}/{req_cards}** lá\n"
            f"• Cần thêm: **{req_cards - current_cnt}** lá nữa để tiến hóa! (Có thể quay `/pull` hoặc dùng `/trade` với bạn bè)",
            None
        )

    player["inventory"][cid_str] = current_cnt - req_cards
    remaining_cnt = player["inventory"][cid_str]

    if "evolutions" not in player or not isinstance(player["evolutions"], dict):
        player["evolutions"] = {}
    player["evolutions"][cid_str] = 2
    save_player(player)

    color_map = {13: 0xEF4444, 16: 0x3B82F6, 17: 0xF59E0B}
    embed = discord.Embed(
        title=f"🌟 TIẾN HÓA THÀNH CÔNG: [{cfg['ace_level']}] [#{cfg['id']:02d}] {cfg['name'].upper()}!",
        description=(
            f"⚡ **TIẾN TRÌNH ĐẠT CẢNH GIỚI TỐI THƯỢNG:**\n"
            f"🎴 **ID & Nhân vật:** **[#{cfg['id']:02d}] {cfg['name']}**\n"
            f"⭐ **Cấp bậc mới:** `{cfg['ace_level']}`\n"
            f"📉 **Khấu trừ chi phí:** Đã tiêu hao **{req_cards}** lá *(Túi đồ còn lại: **{remaining_cnt}** lá)*\n\n"
            f"💪 **BUFF CHỈ SỐ ACE 2:**\n"
            f"⚔️ **+{ACE_POWER_BUFF} ATK (Power)** & ❤️ **+{ACE_HP_BUFF} Máu (Max HP)** vĩnh viễn!\n\n"
            f"🔮 **KỸ NĂNG / NỘI TẠI ĐỘC NHẤT:**\n"
            f"**{cfg['skill_name']}**\n"
            f"*{cfg['skill_desc']}*"
        ),
        color=color_map.get(cid, 0x10B981)
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
        elif "17" in nv_clean or "marisa" in nv_clean:
            cid_target = 17

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

    reimu_cnt = player.get("inventory", {}).get("13", 0)
    reimu_ace = is_card_ace2(player, 13)
    reimu_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if reimu_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if reimu_cnt >= 20 else f"🔴 Chưa đủ ({reimu_cnt}/20)")

    sakuya_cnt = player.get("inventory", {}).get("16", 0)
    sakuya_ace = is_card_ace2(player, 16)
    sakuya_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if sakuya_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if sakuya_cnt >= 30 else f"🔴 Chưa đủ ({sakuya_cnt}/30)")

    marisa_cnt = player.get("inventory", {}).get("17", 0)
    marisa_ace = is_card_ace2(player, 17)
    marisa_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if marisa_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if marisa_cnt >= 25 else f"🔴 Chưa đủ ({marisa_cnt}/25)")

    embed = discord.Embed(
        title="🌟 PHÒNG TIẾN HÓA NHÂN VẬT TOUHOU (EVOLUTION - ACE 2)",
        description=(
            "Thu thập đủ số lượng thẻ yêu cầu để tiến hóa nhân vật lên **Ace 2 ⭐⭐**!\n"
            "✨ **Quy tắc Ace mới:** Sau khi tiến hóa sẽ **trừ đi chi phí thẻ** tương ứng (ví dụ: 30 lá -> 0, 32 lá -> 2).\n"
            "💪 **Buff Ace 2 mới:** Cộng **+300 ATK** và **+300 HP** vĩnh viễn!\n"
            "🌟 **Buff Marisa Ace:** Bộc phá Master Spark tăng từ 1.5x lên **2.0x sát thương**!\n\n"
            "👉 **Cú pháp theo ID:** `/evol id_hoac_ten:13`, `/evol id_hoac_ten:16` hoặc `/evol id_hoac_ten:17`\n"
            "Hoặc bấm các nút bên dưới để tiến hóa ngay:"
        ),
        color=0x8B5CF6
    )

    reimu_cfg = EVOL_CONFIG[13]
    embed.add_field(
        name=f"⛩️ [#{reimu_cfg['id']:02d}] {reimu_cfg['name']} (Yêu cầu 20 thẻ):",
        value=(
            f"• Trạng thái: **{reimu_status}**\n"
            f"• Trong túi đồ: **{reimu_cnt}/20** lá *(tiến hóa xong trừ 20 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{reimu_cfg['skill_name']}** (Miễn thương 1 lần trong trận, tỷ lệ 40% cả raid và battle/pvp)"
        ),
        inline=False
    )

    sakuya_cfg = EVOL_CONFIG[16]
    embed.add_field(
        name=f"🕰️ [#{sakuya_cfg['id']:02d}] {sakuya_cfg['name']} (Yêu cầu 30 thẻ):",
        value=(
            f"• Trạng thái: **{sakuya_status}**\n"
            f"• Trong túi đồ: **{sakuya_cnt}/30** lá *(tiến hóa xong trừ 30 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{sakuya_cfg['skill_name']}** (Stun đối thủ 1 lần trong trận, tỷ lệ 40% cả raid và battle/pvp)"
        ),
        inline=False
    )

    marisa_cfg = EVOL_CONFIG[17]
    embed.add_field(
        name=f"🌟 [#{marisa_cfg['id']:02d}] {marisa_cfg['name']} (Yêu cầu 25 thẻ):",
        value=(
            f"• Trạng thái: **{marisa_status}**\n"
            f"• Trong túi đồ: **{marisa_cnt}/25** lá *(tiến hóa xong trừ 25 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{marisa_cfg['skill_name']}** (Master Spark ×2.0 sát thương gốc, rate 30% kích hoạt 1 lần trong trận)"
        ),
        inline=False
    )
    embed.set_footer(text="Bấm nút chọn hoặc dùng /evol kèm ID nhân vật!")

    view = EvolSelectView(player, user.id)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="evol", description="Tiến hóa nhân vật Touhou lên Ace 2 (13: Reimu, 16: Sakuya, 17: Marisa)")
@app_commands.describe(id_hoac_ten="Nhập số ID thẻ (13, 16 hoặc 17) hoặc chọn nhân vật")
@app_commands.choices(id_hoac_ten=[
    app_commands.Choice(name="[#13] Reimu Hakurei (Ace 2 - Cần 20 thẻ, trừ 20 khi Ace)", value="13"),
    app_commands.Choice(name="[#16] Sakuya Izayoi (Ace 2 - Cần 30 thẻ, trừ 30 khi Ace)", value="16"),
    app_commands.Choice(name="[#17] Marisa Kirisame (Ace 2 - Cần 25 thẻ, Master Spark x2.0)", value="17")
])
async def slash_evol(interaction: discord.Interaction, id_hoac_ten: str = None):
    await handle_evol(interaction, id_hoac_ten)

@bot.command(name="evol", aliases=["tienhoa", "ace2"])
async def prefix_evol(ctx, id_hoac_ten: str = None):
    await handle_evol(ctx, id_hoac_ten)


# ==============================================================================
# 11. CÁC LỆNH GAME: PULL, DAILY, TEAM, COLLECTION, CARD_INFO
# ==============================================================================
@bot.tree.command(name="pull", description="Quay gacha thẻ bài nhân vật Touhou (1 Lượt hoặc 10 Lượt)")
@app_commands.describe(so_luong="Chọn số lượt quay (1 hoặc 10)")
@app_commands.choices(so_luong=[
    app_commands.Choice(name="1 Lượt Quay (1 Vé)", value=1),
    app_commands.Choice(name="10 Lượt Quay (10 Vé)", value=10)
])
async def slash_pull(interaction: discord.Interaction, so_luong: int = 1):
    await handle_pull(interaction, so_luong)

@bot.command(name="pull", aliases=["gacha", "quay"])
async def prefix_pull(ctx, count: int = 1):
    count = 10 if count >= 10 else 1
    await handle_pull(ctx, count)

async def handle_pull(ctx_or_interaction, count: int):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    now_date = get_today_vn()

    tut = player.get("tutorial", {})
    tut_active = tut.get("active", False)
    tut_step = tut.get("step")
    is_tut_pull = tut_active and (tut_step == "pull") and not tut.get("pull_used", False)

    if not is_tut_pull:
        cost = float(count)
        if player["free_pulls_date"] != now_date:
            player["free_pulls_date"] = now_date
            player["free_pulls_remaining"] = 5

        free_rem = player["free_pulls_remaining"]
        used_free = min(count, free_rem)
        needed_tickets = float(count - used_free)

        if player["pull_tickets"] < needed_tickets:
            msg = (
                f"❌ Bạn không đủ vé quay!\n"
                f"• Cần: **{count} lượt** (Miễn phí hôm nay còn: **{free_rem}**, Cần thêm: **{needed_tickets:.1f} vé**)\n"
                f"• Bạn đang có: **{player['pull_tickets']:.2f} vé**.\n\n"
                f"💡 *Mẹo: Hãy dùng `/daily` để nhận vé miễn phí hoặc đánh Boss Raid để gom vé nhé!*"
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        player["free_pulls_remaining"] -= used_free
        player["pull_tickets"] -= needed_tickets

    results = []
    total_conv = 0.0
    unlocked_names = []

    if is_tut_pull:
        tut_cards = [
            random.choice(CARDS_BY_RANK["S"]),
            random.choice(CARDS_BY_RANK["A"]),
            random.choice(CARDS_BY_RANK["B"])
        ]
        for c in tut_cards:
            cid_str = str(c["id"])
            cid_int = int(c["id"])
            player["inventory"][cid_str] = player["inventory"].get(cid_str, 0) + 1
            player.setdefault("pull_stats", {})[cid_str] = player.get("pull_stats", {}).get(cid_str, 0) + 1
            if cid_int not in player.setdefault("unlocked_cards", []):
                player["unlocked_cards"].append(cid_int)
            results.append((c, False, 0.0, False))

        player["tutorial"]["active"] = True
        player["tutorial"]["step"] = "battle"
        player["tutorial"]["pull_used"] = True
        player["tutorial"]["quest_pulls_remaining"] = 0
    else:
        for _ in range(count):
            c, is_dup, conv, unlocked_now = execute_single_pull(player)
            results.append((c, is_dup, conv, unlocked_now))
            total_conv += conv
            if unlocked_now:
                unlocked_names.append(f"`[{c['rank']}]` **{format_card_id(c['id'])} {c['name']}**")

    update_daily_quest_progress(player, "pull", count)
    save_player(player)

    embed = discord.Embed(
        title=f"🌸 KẾT QUẢ QUAY GACHA TOUHOU ({count} LƯỢT)",
        color=0xEC4899
    )

    lines = []
    for c, is_dup, conv, unlocked_now in results:
        star_str = "⭐" * {"SS": 5, "S": 4, "A": 3, "B": 2, "C": 1}.get(c["rank"], 1)
        card_label = f"[{c['rank']}] {format_card_id(c['id'])} {c['name']}"
        if is_dup:
            lines.append(f"• {star_str} **{card_label}** *(Trùng ➔ Quy đổi: `+{conv:.2f} vé`)*")
        else:
            lines.append(f"• {star_str} **{card_label}** 🆕 *(Mới tinh!)*")

    embed.description = "\n".join(lines)

    if total_conv > 0:
        embed.add_field(
            name="🔄 Hoàn Trả Thẻ Trùng:",
            value=f"Đã quy đổi tổng cộng **+{total_conv:.2f} Vé Pull** vào tài khoản!",
            inline=False
        )

    if unlocked_names:
        embed.add_field(
            name="🔓 MỞ KHÓA NIÊM PHONG THÀNH CÔNG!",
            value=f"Bạn đã pull trúng lại các thẻ bị Admin khóa:\n" + "\n".join(unlocked_names) + "\n*Các thẻ này giờ đây đã có thể tham chiến và giao dịch bình thường!*",
            inline=False
        )

    if is_tut_pull:
        embed.add_field(
            name="📜 Hướng Dẫn Tân Thủ (Bước 2/3):",
            value="🎉 Chúc mừng bạn đã nhận 3 thẻ bài tân thủ đầu tiên!\n👉 Tiếp theo, hãy gõ lệnh `/battle` để thử sức với đối thủ trong võ đài Touhou!",
            inline=False
        )
    else:
        embed.set_footer(text=f"Vé còn lại: {player['pull_tickets']:.2f} • Miễn phí hôm nay: {player['free_pulls_remaining']}/5")

    if len(results) == 1 and results[0][0].get("image"):
        embed.set_image(url=results[0][0]["image"])

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="daily", description="Điểm danh nhận vé quay Touhou hàng ngày")
async def slash_daily(interaction: discord.Interaction):
    await handle_daily(interaction)

@bot.command(name="daily", aliases=["diemdanh"])
async def prefix_daily(ctx):
    await handle_daily(ctx)

async def handle_daily(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    now_date = get_today_vn()

    if player.get("last_daily_date") == now_date:
        msg = f"⏳ Hôm nay bạn đã điểm danh rồi! Hãy quay lại vào ngày mai nhé (Ngày mới tính theo giờ VN GMT+7)!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    reward_tickets = 5.0
    reward_xp = 50
    player["last_daily_date"] = now_date
    player["pull_tickets"] += reward_tickets
    player["xp"] += reward_xp
    notifs = update_daily_quest_progress(player, "daily", 1)
    save_player(player)

    embed = discord.Embed(
        title="⛩️ ĐIỂM DANH HÀNG NGÀY THÀNH CÔNG",
        description=(
            f"Chào mừng {user.mention} đã đến viếng đền Hakurei hôm nay!\n\n"
            f"🎁 **Phần Thưởng Điểm Danh:**\n"
            f"• **+{reward_tickets:.0f} Vé Quay Gacha** 🎟️\n"
            f"• **+{reward_xp} XP** Kinh Nghiệm\n\n"
            f"📊 **Tài sản hiện tại:** `{player['pull_tickets']:.2f} Vé` | Cấp độ: `Lv.{player['level']}`"
        ),
        color=0x10B981
    )
    if notifs:
        embed.add_field(name="🎯 Cập Nhật Nhiệm Vụ Ngày:", value="\n".join(notifs), inline=False)
    embed.set_footer(text="Điểm danh lại vào ngày mai • Hakurei Shrine Daily")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="team", description="Xem hoặc thiết lập đội hình 3 thẻ bài chiến đấu (Hỗ trợ cả thẻ T như t1)")
@app_commands.describe(
    the_1="ID thẻ 1 (ví dụ: 13 hoặc t1)",
    the_2="ID thẻ 2 (ví dụ: 16 hoặc t1)",
    the_3="ID thẻ 3 (ví dụ: 17 hoặc t1)"
)
async def slash_team(interaction: discord.Interaction, the_1: str = None, the_2: str = None, the_3: str = None):
    await handle_team(interaction, the_1, the_2, the_3)

@bot.command(name="team", aliases=["doihinh"])
async def prefix_team(ctx, the_1: str = None, the_2: str = None, the_3: str = None):
    await handle_team(ctx, the_1, the_2, the_3)

async def handle_team(ctx_or_interaction, the_1: str = None, the_2: str = None, the_3: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)

    if the_1 is not None or the_2 is not None or the_3 is not None:
        raw_inputs = [x for x in [the_1, the_2, the_3] if x is not None]
        new_team = []
        for raw in raw_inputs:
            norm = normalize_card_id(raw)
            if not norm or norm not in CARDS_DATA:
                err = f"❌ ID thẻ `{raw}` không hợp lệ! (ID từ 1 đến 26 hoặc t1)"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(err, ephemeral=True)
                else:
                    await ctx_or_interaction.send(err)
                return

            if is_card_locked(player, norm):
                err = f"🔒 Thẻ **{format_card_id(norm)}** đang bị Admin niêm phong! Không thể cho vào đội hình."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(err, ephemeral=True)
                else:
                    await ctx_or_interaction.send(err)
                return

            if not is_card_unlocked(player, norm) and player.get("inventory", {}).get(str(norm), 0) <= 0:
                err = f"❌ Bạn chưa sở hữu thẻ bài **{format_card_id(norm)} {CARDS_DATA[norm]['name']}**!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(err, ephemeral=True)
                else:
                    await ctx_or_interaction.send(err)
                return

            if norm in new_team:
                err = f"❌ Không được xếp trùng thẻ bài **{format_card_id(norm)}** trong cùng một đội hình!"
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(err, ephemeral=True)
                else:
                    await ctx_or_interaction.send(err)
                return

            new_team.append(norm)

        if len(new_team) != 3:
            err = "⚠️ Đội hình thi đấu bắt buộc phải có đủ đúng **3 thẻ bài khác nhau**!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(err, ephemeral=True)
            else:
                await ctx_or_interaction.send(err)
            return

        player["team"] = new_team
        save_player(player)

        embed = discord.Embed(
            title="⚔️ THIẾT LẬP ĐỘI HÌNH THÀNH CÔNG!",
            description=f"Đã cập nhật 3 thẻ bài xung trận cho {user.mention}:",
            color=0x10B981
        )
        for idx, cid in enumerate(new_team, start=1):
            c = CARDS_DATA[cid]
            is_ace = is_card_ace2(player, cid)
            ace_txt = " `⭐ [Ace 2]`" if is_ace else ""
            embed.add_field(
                name=f"Vị trí {idx}: {format_card_id(c['id'])} {c['name']} [{c['rank']}]{ace_txt}",
                value=f"ATK: `{c['power']:,}` | HP: `{c['hp']:,}`\nKỹ năng: *{c.get('skill', 'Tấn công cơ bản')}*",
                inline=False
            )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
        return

    current_team = player.get("team", [])
    if not current_team:
        msg = (
            f"ℹ️ **{user.display_name}** chưa thiết lập đội hình thi đấu!\n"
            f"👉 Hãy dùng lệnh: `/team the_1:13 the_2:16 the_3:t1` (hoặc `!team 13 16 t1`) để thiết lập đội hình."
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    embed = discord.Embed(
        title=f"🛡️ ĐỘI HÌNH CHIẾN ĐẤU CỦA {user.display_name.upper()}",
        color=0x3B82F6
    )
    lvl_atk = get_level_atk_buff(player["level"])
    lvl_hp = get_level_hp_buff(player["level"])

    for idx, cid in enumerate(current_team, start=1):
        norm = normalize_card_id(cid)
        c = CARDS_DATA.get(norm, CARDS_DATA.get(cid))
        if not c:
            embed.add_field(name=f"Vị trí {idx}: Thẻ không xác định (#{cid})", value="Hãy đặt lại đội hình", inline=False)
            continue

        is_ace = is_card_ace2(player, cid)
        total_pwr = c["power"] + lvl_atk + (ACE_POWER_BUFF if is_ace else 0)
        total_hp = c["hp"] + lvl_hp + (ACE_HP_BUFF if is_ace else 0)
        ace_label = " `⭐⭐ [TIẾN HÓA ACE 2]`" if is_ace else ""

        embed.add_field(
            name=f"Vị trí {idx}: {format_card_id(c['id'])} {c['name']} [{c['rank']}]{ace_label}",
            value=(
                f"⚔️ **Sức mạnh:** `{total_pwr:,} DMG` *(Gốc: {c['power']:,} + Level: {lvl_atk}{' + Ace: 300' if is_ace else ''})*\n"
                f"❤️ **Sinh mệnh:** `{total_hp:,} HP` *(Gốc: {c['hp']:,} + Level: {lvl_hp}{' + Ace: 300' if is_ace else ''})*\n"
                f"✨ **Kỹ năng:** *{c.get('skill', 'Tấn công Danmaku cơ bản')}*"
            ),
            inline=False
        )

    embed.set_footer(text="Dùng /team the_1 the_2 the_3 để thay đổi đội hình bất kỳ lúc nào!")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="collection", description="Xem bộ sưu tập thẻ bài Touhou và mảnh Shards đã sở hữu")
async def slash_collection(interaction: discord.Interaction):
    await handle_collection(interaction)

@bot.command(name="collection", aliases=["bosuutap", "cards", "kho"])
async def prefix_collection(ctx):
    await handle_collection(ctx)

async def handle_collection(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    inv = player.get("inventory", {})
    shards = player.get("shards", {})
    seiki_shards = shards.get("seiki", 0)

    embed = discord.Embed(
        title=f"🎴 BỘ SƯU TẬP THẺ BÀI TOUHOU: {user.display_name.upper()}",
        description=f"📊 Cấp độ: **Lv.{player['level']}** | Vé quay: **{player['pull_tickets']:.2f}** 🎟️",
        color=0x8B5CF6
    )

    ranks = ["SS", "S", "A", "B", "C"]
    for r in ranks:
        cards_in_rank = CARDS_BY_RANK[r]
        lines = []
        for c in cards_in_rank:
            cid = c["id"]
            cid_str = str(cid)
            owned_cnt = inv.get(cid_str, 0)
            is_ace = is_card_ace2(player, cid)
            is_locked = is_card_locked(player, cid)

            if is_locked:
                status = f"🔒 `[KHÓA - x{owned_cnt}]`"
            elif owned_cnt > 0:
                ace_tag = "⭐[Ace 2] " if is_ace else ""
                status = f"✅ `{ace_tag}x{owned_cnt}`"
            else:
                status = "❌ `Chưa có`"

            lines.append(f"{format_card_id(cid)} {c['name']}: {status}")

        embed.add_field(
            name=f"⭐ Rank [{r}] ({len(cards_in_rank)} Thẻ):",
            value="\n".join(lines),
            inline=False
        )

    # NHÓM THẺ ĐẶC BIỆT: [T] CARDS
    t_cards = [c for c in CARDS_DATA.values() if c.get("rank") == "T"]
    if t_cards:
        t_lines = []
        for tc in t_cards:
            cid = tc["id"]
            cid_str = str(cid)
            owned_cnt = inv.get(cid_str, 0)
            is_locked = is_card_locked(player, cid)
            if is_locked:
                st = f"🔒 `[KHÓA - x{owned_cnt}]`"
            elif owned_cnt > 0:
                st = f"👑 `x{owned_cnt} (Đã sở hữu)`"
            else:
                st = f"🔮 `Chưa ghép` ({seiki_shards}/10 Mảnh Seiki)"
            t_lines.append(f"**{format_card_id(cid)} {tc['name']}**: {st}")
        embed.add_field(name="🌟 Thẻ Bài Tối Thượng [Rank T]:", value="\n".join(t_lines), inline=False)

    # KHO MẢNH SHARDS
    embed.add_field(
        name="💎 Kho Mảnh Đặc Biệt (Shards):",
        value=(
            f"• 🔮 **Mảnh Seiki Đệ Pháp Toàn Năng:** `{seiki_shards}/10 Mảnh`" +
            (" ➔ **ĐỦ ĐIỀU KIỆN ĐỔI THẺ!** Gõ `/t translate`" if seiki_shards >= 10 else " *(Rơi 2.5% từ Boss Seiki)*")
        ),
        inline=False
    )

    embed.set_footer(text="Gõ /card_info <id> hoặc /check <id> để xem chi tiết từng lá bài!")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

# ==============================================================================
# 12. TÍNH NĂNG CHECK THẺ BÀI /card_info & /check (HỖ TRỢ FULL THẺ T & T1 SEIKI)
# ==============================================================================
@bot.tree.command(name="card_info", description="Xem thông tin chi tiết, chỉ số, kỹ năng và GIF của bất kỳ thẻ bài nào (kể cả thẻ T)")
@app_commands.describe(id_hoac_ten="Nhập ID thẻ bài (1-26, t1) hoặc tên nhân vật (Reimu, Seiki, Marisa,...)")
async def slash_card_info(interaction: discord.Interaction, id_hoac_ten: str):
    await handle_card_info(interaction, id_hoac_ten)

@bot.command(name="card_info", aliases=["cardinfo", "check", "the"])
async def prefix_card_info(ctx, *, id_hoac_ten: str = "13"):
    await handle_card_info(ctx, id_hoac_ten)

async def handle_card_info(ctx_or_interaction, id_hoac_ten: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)

    norm = normalize_card_id(id_hoac_ten)
    if not norm or norm not in CARDS_DATA:
        # Tìm theo tên nếu id_hoac_ten là chuỗi chữ
        search_kw = id_hoac_ten.lower().strip()
        found_id = None
        for cid, cdata in CARDS_DATA.items():
            if search_kw in cdata["name"].lower() or search_kw in str(cdata["id"]).lower():
                found_id = cid
                break
        if found_id:
            norm = found_id
        else:
            err = (
                f"❌ Không tìm thấy thẻ bài nào khớp với từ khóa `{id_hoac_ten}`!\n"
                f"💡 Gợi ý:\n"
                f"• Thẻ thường: Nhập số từ `1` đến `26` (Ví dụ: `/card_info 13`)\n"
                f"• Thẻ T: Nhập `t1` hoặc `seiki` (Ví dụ: `/card_info t1`)\n"
                f"• Tên nhân vật: `reimu`, `marisa`, `sakuya`, `seiki`, v.v."
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(err, ephemeral=True)
            else:
                await ctx_or_interaction.send(err)
            return

    card = CARDS_DATA[norm]
    cid = card["id"]
    cid_str = str(norm)
    owned_cnt = player.get("inventory", {}).get(cid_str, 0)
    is_ace = is_card_ace2(player, norm)
    is_locked = is_card_locked(player, norm)
    unlocked = is_card_unlocked(player, norm)

    color_map = {
        "SS": 0xF59E0B,
        "S": 0xEC4899,
        "A": 0x3B82F6,
        "B": 0x10B981,
        "C": 0x6B7280,
        "T": 0x8B5CF6
    }

    embed = discord.Embed(
        title=f"🎴 THÔNG TIN THẺ BÀI: {format_card_id(card['id'])} {card['name'].upper()}",
        description=card.get("desc", f"Thẻ bài nhân vật Touhou Project thuộc Rank [{card['rank']}]."),
        color=color_map.get(card["rank"], 0x3B82F6)
    )

    if card.get("image"):
        embed.set_thumbnail(url=card["image"])

    # TÌNH TRẠNG SỞ HỮU CỦA BẠN
    if is_locked:
        owner_status = f"🔒 **ĐÃ BỊ ADMIN KHÓA** *(Có {owned_cnt} lá, cần pull lại để mở!)*"
    elif owned_cnt > 0:
        ace_txt = " `⭐⭐ [ĐÃ TIẾN HÓA ACE 2]`" if is_ace else ""
        owner_status = f"✅ **Đã sở hữu:** `{owned_cnt} lá`{ace_txt}"
    elif unlocked:
        owner_status = "🔓 **Đã từng mở khóa** *(hiện tại 0 lá trong túi)*"
    else:
        owner_status = "❌ **Chưa sở hữu**"

    embed.add_field(name="👤 Tình Trạng Sở Hữu Của Bạn:", value=owner_status, inline=False)
    embed.add_field(name="⭐ Phẩm Cấp (Rank):", value=f"**[{card['rank']}]**" + (" `(Thẻ Tối Thượng)`" if card['rank'] == "T" else ""), inline=True)
    embed.add_field(name="⚔️ Sức Mạnh Cơ Bản:", value=f"**{card['power']:,} ATK**", inline=True)
    embed.add_field(name="❤️ Sinh Mệnh Cơ Bản:", value=f"**{card['hp']:,} HP**", inline=True)

    # NẾU LÀ THẺ T1 SEIKI: HIỂN THỊ ĐẦY ĐỦ BỘ 4 KỸ NĂNG VÀ HOẠT ẢNH
    if str(norm).lower() == "t1":
        seiki_shards = player.get("shards", {}).get("seiki", 0)
        embed.add_field(
            name="🔮 Tiến Trình Thu Thập Mảnh Seiki:",
            value=f"• Bạn đang có: **{seiki_shards}/10 Mảnh Seiki**\n• Nguồn nhận: Rơi **2.5%** từ Boss Seiki Dị Hình (/boss)\n• Ghép thẻ: Dùng `/t translate` khi đủ 10 mảnh!",
            inline=False
        )
        embed.add_field(
            name="✨ BỘ TUYỆT KỸ DANMAKU TOÀN NĂNG (TỐI ĐA 1 CHIÊU/LƯỢT):",
            value=(
                "🛡️ **Fantasy Seal (40% Tỷ Lệ):** Dựng kết giới thần thánh, **MIỄN TOÀN BỘ SÁT THƯƠNG** nhận vào trong 1 lượt!\n"
                "🌟 **Master Spark (30% Tỷ Lệ):** Bộc phát chùm ma pháp cực đại, gây **1.5x Sát Thương** ({int(card['power']*1.5):,} DMG)!\n"
                "💚 **Medicine Sign (20% Tỷ Lệ):** Dược liệu y đạo thần kỳ, tự **hồi phục 30% HP** cho bản thân!\n"
                "⚡ **Blitz Attack (20% trong Raid):** Oanh tạc chớp nhoáng gây **4,000 DMG** diện rộng!"
            ),
            inline=False
        )
        embed.set_image(url=card.get("image", "https://klipy.com/gifs/marisa-master-spark"))
    elif is_ace and norm in EVOL_CONFIG:
        cfg = EVOL_CONFIG[norm]
        embed.add_field(
            name=f"⭐ Kỹ Năng Đột Phá Ace 2: {cfg['skill_name']}",
            value=f"*{cfg['skill_desc']}*",
            inline=False
        )
        embed.set_image(url=cfg.get("skill_gif") or cfg.get("evol_gif"))
    else:
        embed.add_field(
            name="✨ Kỹ Năng / Tuyệt Kỹ:",
            value=f"*{card.get('skill', 'Tấn công Danmaku cơ bản')}*",
            inline=False
        )
        if card.get("gif"):
            embed.set_image(url=card["gif"])

    embed.set_footer(text=f"Thẻ ID #{card['id']} • Touhou Card Battle System")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)


# ==============================================================================
# 13. HỆ THỐNG CHIẾN ĐẤU PVE & PVP (HỖ TRỢ FULL THẺ T, BUFF MARISA 2.0X & GIF)
# ==============================================================================
def build_team_cards(player: dict) -> list:
    """Xây dựng dữ liệu thẻ bài thi đấu, tương thích 100% với cả thẻ số (1-26) và thẻ chữ (t1)."""
    lvl_buff_pwr = get_level_atk_buff(player["level"])
    lvl_buff_hp = get_level_hp_buff(player["level"])
    team_cids = [cid for cid in player.get("team", []) if (cid in CARDS_DATA or normalize_card_id(cid) in CARDS_DATA) and not is_card_locked(player, cid)]

    if len(team_cids) < 3:
        owned_ids = [cid for cid, cnt in player.get("inventory", {}).items() if cnt > 0 and (cid in CARDS_DATA or normalize_card_id(cid) in CARDS_DATA) and not is_card_locked(player, cid)]
        owned_ids.sort(key=lambda cid: CARDS_DATA.get(normalize_card_id(cid), CARDS_DATA.get(cid, {})).get("power", 0), reverse=True)
        for cid in owned_ids:
            norm = normalize_card_id(cid)
            if norm and norm not in team_cids and cid not in team_cids:
                team_cids.append(cid)
            if len(team_cids) >= 3:
                break
        player["team"] = team_cids
        save_player(player)

    team_cards = []
    for cid in team_cids[:3]:
        card = CARDS_DATA.get(cid) or CARDS_DATA.get(normalize_card_id(cid))
        if card:
            is_ace = is_card_ace2(player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            card_pwr = card["power"] + lvl_buff_pwr + ace_pwr
            card_hp = card["hp"] + lvl_buff_hp + ace_hp
            card_name = f"[Ace 2 ⭐⭐] {format_card_id(card['id'])} {card['name']}" if is_ace else f"{format_card_id(card['id'])} {card['name']}"
            team_cards.append({
                "cid": card["id"],
                "name": card_name,
                "raw_name": card["name"],
                "rank": card["rank"],
                "base_power": card["power"],
                "power": card_pwr,
                "base_hp": card["hp"],
                "max_hp": card_hp,
                "hp": card_hp,
                "current_hp": card_hp,
                "image": card.get("image"),
                "is_ace2": is_ace,
                "skill": card.get("skill")
            })
    return team_cards

def simulate_match(user_cards, opp_cards, user_name, opp_name, user_level, opp_level):
    """Mô phỏng trận chiến chi tiết từng hiệp giữa 2 đội hình 3vs3."""
    turns_data = []
    user_idx = 0
    opp_idx = 0
    round_num = 0
    max_rounds = 40

    user_sakuya_stun_used = False
    opp_sakuya_stun_used = False
    user_reimu_invul_used = False
    opp_reimu_invul_used = False
    user_marisa_spark_used = False
    opp_marisa_spark_used = False

    user_seiki_seal_used = False
    opp_seiki_seal_used = False
    user_seiki_spark_used = False
    opp_seiki_spark_used = False
    user_seiki_heal_used = False
    opp_seiki_heal_used = False
    user_seiki_turn_used = -1
    opp_seiki_turn_used = -1

    for c in user_cards:
        c["current_hp"] = c["hp"]
    for c in opp_cards:
        c["current_hp"] = c["hp"]

    while user_idx < len(user_cards) and opp_idx < len(opp_cards) and round_num < max_rounds:
        round_num += 1
        u_card = user_cards[user_idx]
        o_card = opp_cards[opp_idx]

        u_norm = normalize_card_id(u_card["cid"])
        o_norm = normalize_card_id(o_card["cid"])

        turn_logs = []
        turn_image = None
        sakuya_stun_notif = None
        marisa_spark_notif = None
        seiki_skill_notif = None

        opp_stunned = False
        user_stunned = False

        # Sakuya Ace 2 Stun (40%)
        if u_norm == 16 and u_card.get("is_ace2") and not user_sakuya_stun_used:
            if random.random() < 0.40:
                user_sakuya_stun_used = True
                opp_stunned = True
                turn_image = EVOL_CONFIG[16]["skill_gif"]
                sakuya_stun_notif = f"⏳ **[Ace 2] [#16] Sakuya Izayoi** ({user_name}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Đối thủ bị STUN mất lượt!"

        if o_norm == 16 and o_card.get("is_ace2") and not opp_sakuya_stun_used and not opp_stunned:
            if random.random() < 0.40:
                opp_sakuya_stun_used = True
                user_stunned = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                sakuya_stun_notif = f"⏳ **[Ace 2] [#16] Sakuya Izayoi** ({opp_name}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Bạn bị STUN mất lượt!"

        # User's Card Damage & Skills
        u_dmg = u_card["power"]
        # Buff Marisa Ace 2: 1.5x -> 2.0x DMG
        if u_norm == 17 and u_card.get("is_ace2") and not user_marisa_spark_used:
            if random.random() < 0.30:
                user_marisa_spark_used = True
                u_dmg = int(u_dmg * 2.0)
                if not turn_image:
                    turn_image = "https://klipy.com/gifs/marisa-master-spark"
                marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({user_name}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{u_dmg:,} DMG**!"

        # Kỹ năng Thẻ Seiki T1 (Nhóm T)
        if str(u_norm).lower() == "t1":
            if user_seiki_turn_used != round_num:
                # Master Spark 30% x1.5 dmg
                if not user_seiki_spark_used and random.random() < 0.30:
                    user_seiki_spark_used = True
                    user_seiki_turn_used = round_num
                    u_dmg = int(u_dmg * 1.5)
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/marisa-master-spark"
                    seiki_skill_notif = f"🌟 **[Nhóm T] [#t1] Seiki** ({user_name}) bộc phát **Master Spark** (30%)! Đòn đánh ma thuật ×1.5 giáng **{u_dmg:,} DMG**!"
                # Medicine Sign 20% tự hồi phục
                elif not user_seiki_heal_used and u_card["current_hp"] < u_card["max_hp"] and random.random() < 0.20:
                    user_seiki_heal_used = True
                    user_seiki_turn_used = round_num
                    heal_amt = int(u_card["max_hp"] * 0.30)
                    u_card["current_hp"] = min(u_card["max_hp"], u_card["current_hp"] + heal_amt)
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/shoko-ieiri-2"
                    seiki_skill_notif = f"💚 **[Nhóm T] [#t1] Seiki** ({user_name}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_amt:,} HP** cho bản thân!"

        # Opponent's Card Damage & Skills
        o_dmg = o_card["power"]
        if o_norm == 17 and o_card.get("is_ace2") and not opp_marisa_spark_used:
            if random.random() < 0.30:
                opp_marisa_spark_used = True
                o_dmg = int(o_dmg * 2.0)
                if not turn_image:
                    turn_image = "https://klipy.com/gifs/marisa-master-spark"
                marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({opp_name}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{o_dmg:,} DMG**!"

        if str(o_norm).lower() == "t1":
            if opp_seiki_turn_used != round_num:
                if not opp_seiki_spark_used and random.random() < 0.30:
                    opp_seiki_spark_used = True
                    opp_seiki_turn_used = round_num
                    o_dmg = int(o_dmg * 1.5)
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/marisa-master-spark"
                    seiki_skill_notif = (seiki_skill_notif + "\n" if seiki_skill_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({opp_name}) bộc phát **Master Spark** (30%)! Đòn đánh ma thuật ×1.5 giáng **{o_dmg:,} DMG**!"
                elif not opp_seiki_heal_used and o_card["current_hp"] < o_card["max_hp"] and random.random() < 0.20:
                    opp_seiki_heal_used = True
                    opp_seiki_turn_used = round_num
                    heal_amt = int(o_card["max_hp"] * 0.30)
                    o_card["current_hp"] = min(o_card["max_hp"], o_card["current_hp"] + heal_amt)
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/shoko-ieiri-2"
                    seiki_skill_notif = (seiki_skill_notif + "\n" if seiki_skill_notif else "") + f"💚 **[Nhóm T] [#t1] Seiki** ({opp_name}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_amt:,} HP** cho bản thân!"

        # Defensive Skills: Reimu Ace 2 Invul (40%) & Seiki T1 Fantasy Seal (40%)
        user_invul = False
        if not user_stunned:
            if u_norm == 13 and u_card.get("is_ace2") and not user_reimu_invul_used:
                if random.random() < 0.40:
                    user_reimu_invul_used = True
                    user_invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    turn_logs.append(f"🛡️ **[Ace 2] [#13] Reimu** ({user_name}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG hiệp này!")
            elif str(u_norm).lower() == "t1" and not user_seiki_seal_used:
                if user_seiki_turn_used != round_num and random.random() < 0.40:
                    user_seiki_seal_used = True
                    user_seiki_turn_used = round_num
                    user_invul = True
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                    turn_logs.append(f"🛡️ **[Nhóm T] [#t1] Seiki** ({user_name}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG hiệp này!")

        opp_invul = False
        if not opp_stunned:
            if o_norm == 13 and o_card.get("is_ace2") and not opp_reimu_invul_used:
                if random.random() < 0.40:
                    opp_reimu_invul_used = True
                    opp_invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    turn_logs.append(f"🛡️ **[Ace 2] [#13] Reimu** ({opp_name}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG hiệp này!")
            elif str(o_norm).lower() == "t1" and not opp_seiki_seal_used:
                if opp_seiki_turn_used != round_num and random.random() < 0.40:
                    opp_seiki_seal_used = True
                    opp_seiki_turn_used = round_num
                    opp_invul = True
                    if not turn_image:
                        turn_image = "https://klipy.com/gifs/hakurei-reimu-touhou"
                    turn_logs.append(f"🛡️ **[Nhóm T] [#t1] Seiki** ({opp_name}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG hiệp này!")

        # Execute Attacks
        if not user_stunned:
            if opp_invul:
                turn_logs.append(f"⚔️ **{u_card['name']}** tấn công dồn {u_dmg:,} DMG nhưng đối thủ đã miễn thương!")
            else:
                o_card["current_hp"] -= u_dmg
                turn_logs.append(f"⚔️ **{u_card['name']}** gây **{u_dmg:,} DMG** lên {o_card['name']}!")

        if not opp_stunned:
            if user_invul:
                turn_logs.append(f"👺 **{o_card['name']}** phản kích {o_dmg:,} DMG nhưng bạn đã miễn thương!")
            else:
                u_card["current_hp"] -= o_dmg
                turn_logs.append(f"👺 **{o_card['name']}** phản kích gây **{o_dmg:,} DMG** lên {u_card['name']}!")

        push_logs = []
        # Check deaths
        u_dead = u_card["current_hp"] <= 0
        o_dead = o_card["current_hp"] <= 0

        if u_dead:
            u_card["current_hp"] = 0
            user_idx += 1
            if user_idx < len(user_cards):
                next_c = user_cards[user_idx]
                push_logs.append(f"💀 **{u_card['name']}** gục ngã! ➡️ Đẩy **{next_c['name']}** (❤️{next_c['current_hp']:,} HP) lên sàn!")
            else:
                push_logs.append(f"☠️ Quân đoàn của **{user_name}** đã cạn kiệt thẻ bài!")

        if o_dead:
            o_card["current_hp"] = 0
            opp_idx += 1
            if opp_idx < len(opp_cards):
                next_c = opp_cards[opp_idx]
                push_logs.append(f"💀 **{o_card['name']}** gục ngã! ➡️ Đẩy **{next_c['name']}** (❤️{next_c['current_hp']:,} HP) lên sàn!")
            else:
                push_logs.append(f"☠️ Quân đoàn của **{opp_name}** đã cạn kiệt thẻ bài!")

        turn_desc = (
            f"👤 **{user_name}**: {u_card['name']} (❤️ {max(0, u_card['current_hp']):,}/{u_card['max_hp']:,} HP)\n"
            f"👺 **{opp_name}**: {o_card['name']} (❤️ {max(0, o_card['current_hp']):,}/{o_card['max_hp']:,} HP)"
        )

        turns_data.append({
            "round": round_num,
            "title": f"Hiệp {round_num}: {u_card['raw_name']} vs {o_card['raw_name']}",
            "short_label": f"H{round_num}: {u_card['raw_name'][:8]} vs {o_card['raw_name'][:8]}",
            "short_desc": f"HP: {max(0, u_card['current_hp']):,} vs {max(0, o_card['current_hp']):,}",
            "desc": turn_desc,
            "color": 0x3B82F6 if not (u_dead or o_dead) else (0x10B981 if o_dead and not u_dead else 0xEF4444),
            "image": turn_image,
            "fields": [
                *([("❄️ Thời Gian Đóng Băng:", sakuya_stun_notif, False)] if sakuya_stun_notif else []),
                *([("🌟 Master Spark:", marisa_spark_notif, False)] if marisa_spark_notif else []),
                *([("🔮 Kỹ Năng Seiki [T]:", seiki_skill_notif, False)] if seiki_skill_notif else []),
                ("⚔️ Diễn Biến Giao Chiến:", "\n".join(turn_logs) if turn_logs else "Hai bên giằng co!", False),
                *([("🔄 Đẩy Thẻ Mới Lên Tiền Tuyến:", "\n".join(push_logs), False)] if push_logs else [])
            ]
        })

    user_won = (opp_idx >= len(opp_cards)) and (user_idx < len(user_cards))
    is_draw = (opp_idx >= len(opp_cards)) and (user_idx >= len(user_cards))
    return user_won, is_draw, round_num, turns_data

@bot.tree.command(name="battle", description="Chiến đấu PvE với võ giả Touhou ngẫu nhiên (Thử thách đội hình 3vs3)")
async def slash_battle(interaction: discord.Interaction):
    await handle_battle(interaction)

@bot.command(name="battle", aliases=["chien", "pve"])
async def prefix_battle(ctx):
    await handle_battle(ctx)

async def handle_battle(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)

    user_cards = build_team_cards(player)
    if len(user_cards) < 3:
        msg = "⚠️ Bạn chưa có đủ 3 thẻ bài để tham chiến! Hãy dùng `/pull` để tìm thêm thẻ hoặc dùng `/team` để xếp đội hình nhé!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    opp_level = max(1, player["level"] + random.randint(-1, 2))
    lvl_buff_pwr = get_level_atk_buff(opp_level)
    lvl_buff_hp = get_level_hp_buff(opp_level)

    opp_cids = random.sample([cid for cid in CARDS_DATA.keys()], 3)
    opp_cards = []
    for cid in opp_cids:
        card = CARDS_DATA[cid]
        opp_cards.append({
            "cid": card["id"],
            "name": f"{format_card_id(card['id'])} {card['name']}",
            "raw_name": card["name"],
            "rank": card["rank"],
            "base_power": card["power"],
            "power": card["power"] + lvl_buff_pwr,
            "base_hp": card["hp"],
            "max_hp": card["hp"] + lvl_buff_hp,
            "hp": card["hp"] + lvl_buff_hp,
            "current_hp": card["hp"] + lvl_buff_hp,
            "image": card.get("image"),
            "is_ace2": False,
            "skill": card.get("skill")
        })

    opp_names = ["Kirisame Marisa (Ảo Ảnh)", "Izayoi Sakuya (Ảo Ảnh)", "Remilia Scarlet (Ảo Ảnh)", "Youmu Konpaku (Ảo Ảnh)", "Reisen Inaba (Ảo Ảnh)"]
    opp_name = random.choice(opp_names)

    user_won, is_draw, rounds, turns_data = simulate_match(
        user_cards, opp_cards, user.display_name, opp_name, player["level"], opp_level
    )

    player["battles_total"] += 1
    xp_gain = 40 if user_won else 15
    ticket_gain = 0.5 if user_won else 0.1
    if user_won:
        player["battles_won"] += 1

    player["xp"] += xp_gain
    player["pull_tickets"] += ticket_gain

    # Check tutorial
    tut = player.get("tutorial", {})
    tut_notice = ""
    if tut.get("active") and tut.get("step") == "battle":
        tut["active"] = False
        tut["step"] = "completed"
        tut["completed"] = True
        player["pull_tickets"] += 5.0
        tut_notice = "\n🎉 **HOÀN THÀNH HƯỚNG DẪN TÂN THỦ!** Nhận thêm **+5 Vé Pull** tích lũy!"

    notifs = update_daily_quest_progress(player, "battle", 1)
    save_player(player)

    color = 0x10B981 if user_won else (0xF59E0B if is_draw else 0xEF4444)
    title = f"⚔️ KẾT QUẢ VÕ ĐÀI PVE: {'CHIẾN THẮNG!' if user_won else ('HÒA NHAU!' if is_draw else 'THẤT BẠI!')}"

    embed = discord.Embed(
        title=title,
        description=(
            f"👤 **Bạn:** `{user.display_name}` (Lv.{player['level']})\n"
            f"👺 **Đối thủ:** `{opp_name}` (Lv.{opp_level})\n"
            f"⏱️ **Số hiệp giao tranh:** `{rounds} hiệp`\n\n"
            f"🎁 **Phần thưởng:** `+{xp_gain} XP` | `+{ticket_gain:.1f} Vé Pull`{tut_notice}"
        ),
        color=color
    )
    if notifs:
        embed.add_field(name="🎯 Cập Nhật Nhiệm Vụ Ngày:", value="\n".join(notifs), inline=False)
    embed.set_footer(text="Bấm các nút bên dưới để xem diễn biến từng hiệp kèm hoạt ảnh GIF hoặc soi thẻ bài đối thủ!")

    view = OpenDetailsView(turns_data, opp_cards, opp_name, opp_level)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="pvp", description="Thách đấu PvP 3vs3 với một người chơi khác trong server (Hỗ trợ thẻ T)")
@app_commands.describe(doi_thu="Người chơi muốn thách đấu")
async def slash_pvp(interaction: discord.Interaction, doi_thu: discord.Member):
    await handle_pvp(interaction, doi_thu)

@bot.command(name="pvp", aliases=["thachdau"])
async def prefix_pvp(ctx, member: discord.Member):
    await handle_pvp(ctx, member)

async def handle_pvp(ctx_or_interaction, opp_member: discord.Member):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    if opp_member.id == user.id:
        msg = "❌ Bạn không thể tự thách đấu chính mình!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    player = get_player(user.id, user.display_name)
    opp_player = get_player(opp_member.id, opp_member.display_name)

    user_cards = build_team_cards(player)
    opp_cards = build_team_cards(opp_player)

    if len(user_cards) < 3:
        msg = "⚠️ Đội hình của bạn chưa đủ 3 thẻ bài để tham chiến PvP! Hãy dùng `/team` để sắp xếp đội hình."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if len(opp_cards) < 3:
        msg = f"⚠️ Đối thủ {opp_member.mention} chưa có đủ 3 thẻ bài trong đội hình thi đấu!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    user_won, is_draw, rounds, turns_data = simulate_match(
        user_cards, opp_cards, user.display_name, opp_member.display_name, player["level"], opp_player["level"]
    )

    xp_gain = 50 if user_won else 20
    ticket_gain = 1.0 if user_won else 0.2
    player["xp"] += xp_gain
    player["pull_tickets"] += ticket_gain
    notifs = update_daily_quest_progress(player, "pvp", 1)
    save_player(player)

    color = 0x10B981 if user_won else (0xF59E0B if is_draw else 0xEF4444)
    result_title = f"⚔️ ĐẠI CHIẾN PVP: {user.display_name.upper()} {'THẮNG TRẬN' if user_won else ('HÒA' if is_draw else 'THẤT BẠI')}!"

    embed = discord.Embed(
        title=result_title,
        description=(
            f"👤 **Thách đấu:** {user.mention} (Lv.{player['level']})\n"
            f"👺 **Nghênh chiến:** {opp_member.mention} (Lv.{opp_player['level']})\n"
            f"⏱️ **Thời lượng:** `{rounds} hiệp quyết đấu đẫm máu`\n\n"
            f"🎁 **Phần thưởng người thắng:** `+{xp_gain} XP` | `+{ticket_gain:.1f} Vé Pull`"
        ),
        color=color
    )
    if notifs:
        embed.add_field(name="🎯 Cập Nhật Nhiệm Vụ Ngày:", value="\n".join(notifs), inline=False)
    embed.set_footer(text="Bấm 'Diễn Biến Từng Hiệp (GIF)' để xem trận đấu hoặc 'Soi Toàn Bộ Đội Hình'!")

    view = OpenDetailsView(turns_data, opp_cards, opp_member.display_name, opp_player["level"])
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

# ==============================================================================
# 14. HỆ THỐNG ĐỔI THẺ NHÓM T: /t translate (10 MẢNH SEIKI = 1 THẺ SEIKI T1)
# ==============================================================================
@bot.tree.command(name="t", description="Hệ thống Thẻ Tối Thượng [Rank T] & Đổi mảnh Shards (Ví dụ: /t translate)")
@app_commands.describe(hanh_dong="Hành động (ví dụ: translate)")
@app_commands.choices(hanh_dong=[
    app_commands.Choice(name="Đổi 10 Mảnh Seiki lấy Thẻ [T] #t1 Seiki (translate)", value="translate"),
    app_commands.Choice(name="Xem thông tin mảnh & cách kiếm Thẻ [T] (info)", value="info")
])
async def slash_t_group(interaction: discord.Interaction, hanh_dong: str = "translate"):
    await handle_t_group(interaction, hanh_dong)

@bot.command(name="t", aliases=["the_t", "thẻ_t", "shard"])
async def prefix_t_group(ctx, hanh_dong: str = "translate"):
    await handle_t_group(ctx, hanh_dong)

async def handle_t_group(ctx_or_interaction, hanh_dong: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    shards = player.setdefault("shards", {})
    seiki_shards = shards.get("seiki", 0)

    if hanh_dong == "translate":
        if seiki_shards < 10:
            msg = (
                f"❌ Bạn chưa đủ mảnh để ghép Thẻ Tối Thượng **[T] [#t1] Seiki**!\n"
                f"• Số mảnh hiện có: **{seiki_shards}/10 Mảnh Seiki**\n"
                f"• Cần thêm: **{10 - seiki_shards} Mảnh** nữa!\n\n"
                f"💡 *Cách kiếm mảnh: Tham gia tiêu diệt Boss Seiki Dị Hình (/boss)! Mỗi trận thắng có **2.5% tỷ lệ** rơi ra 1 Mảnh Seiki!*"
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        shards["seiki"] -= 10
        rem_shards = shards["seiki"]

        # Cấp thẻ T1 vào inventory
        t1_card = CARDS_DATA["t1"]
        inv = player.setdefault("inventory", {})
        inv["t1"] = inv.get("t1", 0) + 1
        if "t1" not in player.setdefault("unlocked_cards", []):
            player["unlocked_cards"].append("t1")
        player.setdefault("pull_stats", {})["t1"] = player.get("pull_stats", {}).get("t1", 0) + 1
        save_player(player)

        embed = discord.Embed(
            title="👑 CHÚC MỪNG: GHÉP THÀNH CÔNG THẺ TỐI THƯỢNG [T] SEIKI!",
            description=(
                f"🎉 {user.mention} đã thu thập đủ 10 Mảnh Shards và ngưng tụ thành công linh lực!\n\n"
                f"🎴 **Thẻ nhận được:** `[{t1_card['rank']}]` **{format_card_id(t1_card['id'])} {t1_card['name'].upper()}**\n"
                f"📉 **Khấu trừ:** Tiêu hao **10 Mảnh Seiki** *(Còn lại trong kho: {rem_shards} mảnh)*\n"
                f"⚔️ **Chỉ số:** `ATK: {t1_card['power']:,}` | `HP: {t1_card['hp']:,}`\n\n"
                f"🔮 **KỸ NĂNG ĐỘC QUYỀN TOÀN NĂNG (1 CHIÊU/HIỆP):**\n"
                f"• 🛡️ **Fantasy Seal (40%):** Miễn toàn bộ sát thương 1 lượt.\n"
                f"• 🌟 **Master Spark (30%):** Bộc phát ×1.5 sát thương ma pháp.\n"
                f"• 💚 **Medicine Sign (20%):** Hồi phục 30% sinh lực bản thân.\n\n"
                f"👉 Giờ đây bạn đã có thể đưa Thẻ T1 vào đội hình chiến đấu: `/team the_1:t1 ...`!"
            ),
            color=0x8B5CF6
        )
        embed.set_image(url=t1_card.get("image", "https://klipy.com/gifs/marisa-master-spark"))
        embed.set_footer(text="Hakurei Shrine • Nhóm Thẻ T Tối Thượng")

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
        return

    # hanh_dong == "info"
    t1_card = CARDS_DATA["t1"]
    embed = discord.Embed(
        title="🌟 THÔNG TIN THẺ TỐI THƯỢNG [RANK T] - HỆ THỐNG SHARDS",
        description=(
            "Nhóm Thẻ **[T]** là phẩm cấp thẻ bài thần thoại tối thượng, sở hữu bộ tuyệt kỹ ma thuật toàn diện và chỉ số chiến đấu vượt trội!\n\n"
            f"🎴 **Thẻ hiện tại:** `[{t1_card['rank']}]` **{format_card_id(t1_card['id'])} {t1_card['name']}**\n"
            f"🔮 **Kho mảnh của bạn:** `{seiki_shards}/10 Mảnh Seiki`\n\n"
            f"📌 **Quy tắc & Cách sở hữu:**\n"
            f"1. Tham gia đánh Boss **Seiki Dị Hình** (Raid Boss 30k HP).\n"
            f"2. Mỗi trận thắng có **2.5% cơ hội** rơi ra 1 Mảnh Seiki Shards.\n"
            f"3. Khi thu thập đủ **10 Mảnh**, gõ `/t translate` để ngưng tụ thành 1 thẻ bài vĩnh viễn!\n"
            f"4. Thẻ [T] hoàn toàn có thể tham gia **PvP, Võ Đài PvE, và Boss Raid**!"
        ),
        color=0x8B5CF6
    )
    embed.set_thumbnail(url=t1_card.get("image"))
    embed.set_footer(text="Dùng /t translate khi bạn có đủ 10 mảnh Seiki!")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)


# ==============================================================================
# 15. HỆ THỐNG GIAO DỊCH /trade (HỖ TRỢ THẺ SỐ VÀ THẺ T, BẢO VỆ THẺ KHÓA)
# ==============================================================================
class TradeConfirmView(discord.ui.View):
    def __init__(self, sender_id, target_id, sender_cid, target_cid, sender_name, target_name):
        super().__init__(timeout=120)
        self.sender_id = sender_id
        self.target_id = target_id
        self.sender_cid = sender_cid
        self.target_cid = target_cid
        self.sender_name = sender_name
        self.target_name = target_name
        self.target_accepted = False

    @discord.ui.button(label="🤝 Đồng Ý Trao Đổi", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Chỉ người nhận lời đề nghị trao đổi mới được bấm nút này!", ephemeral=True)
            return

        p1 = get_player(self.sender_id, self.sender_name)
        p2 = get_player(self.target_id, self.target_name)

        s_cid_str = str(self.sender_cid)
        t_cid_str = str(self.target_cid)

        # Kiểm tra thẻ khóa hoặc thiếu thẻ vào thời điểm xác nhận
        if is_card_locked(p1, self.sender_cid) or p1.get("inventory", {}).get(s_cid_str, 0) <= 0:
            await interaction.response.send_message(f"❌ Giao dịch thất bại! {self.sender_name} không còn sở hữu hoặc thẻ đã bị khóa!", ephemeral=False)
            self.stop()
            return

        if is_card_locked(p2, self.target_cid) or p2.get("inventory", {}).get(t_cid_str, 0) <= 0:
            await interaction.response.send_message(f"❌ Giao dịch thất bại! {self.target_name} không còn sở hữu hoặc thẻ đã bị khóa!", ephemeral=False)
            self.stop()
            return

        # Thực hiện hoán đổi
        p1["inventory"][s_cid_str] -= 1
        p1["inventory"][t_cid_str] = p1.get("inventory", {}).get(t_cid_str, 0) + 1
        if self.target_cid not in p1.setdefault("unlocked_cards", []):
            p1["unlocked_cards"].append(self.target_cid)

        p2["inventory"][t_cid_str] -= 1
        p2["inventory"][s_cid_str] = p2.get("inventory", {}).get(s_cid_str, 0) + 1
        if self.sender_cid not in p2.setdefault("unlocked_cards", []):
            p2["unlocked_cards"].append(self.sender_cid)

        # Nếu thẻ đang trong đội hình mà bị trừ về 0 thì gỡ ra
        if p1["inventory"][s_cid_str] <= 0 and self.sender_cid in p1.get("team", []):
            p1["team"].remove(self.sender_cid)
        if p2["inventory"][t_cid_str] <= 0 and self.target_cid in p2.get("team", []):
            p2["team"].remove(self.target_cid)

        save_player(p1)
        save_player(p2)

        c1 = CARDS_DATA[self.sender_cid]
        c2 = CARDS_DATA[self.target_cid]

        embed = discord.Embed(
            title="🤝 GIAO DỊCH THẺ BÀI THÀNH CÔNG!",
            description=(
                f"Chúc mừng hai người chơi đã hoàn tất trao đổi thẻ bài!\n\n"
                f"👤 **{self.sender_name}** nhận được: `[{c2['rank']}]` **{format_card_id(c2['id'])} {c2['name']}**\n"
                f"👤 **{self.target_name}** nhận được: `[{c1['rank']}]` **{format_card_id(c1['id'])} {c1['name']}**"
            ),
            color=0x10B981
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Từ Chối", style=discord.ButtonStyle.danger, emoji="✖️")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_id and interaction.user.id != self.sender_id:
            await interaction.response.send_message("❌ Bạn không liên quan đến cuộc giao dịch này!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 Giao dịch đã bị hủy bỏ!", view=self)
        self.stop()

@bot.tree.command(name="trade", description="Đề nghị trao đổi 1 thẻ bài của bạn lấy 1 thẻ bài của người chơi khác")
@app_commands.describe(
    nguoi_nhan="Người chơi muốn trao đổi thẻ",
    the_cua_ban="ID thẻ của bạn muốn đưa ra (ví dụ: 13, 16 hoặc t1)",
    the_muon_lay="ID thẻ bạn muốn nhận về từ đối phương"
)
async def slash_trade(interaction: discord.Interaction, nguoi_nhan: discord.Member, the_cua_ban: str, the_muon_lay: str):
    await handle_trade(interaction, nguoi_nhan, the_cua_ban, the_muon_lay)

@bot.command(name="trade", aliases=["traodoi", "giaodich"])
async def prefix_trade(ctx, member: discord.Member, your_card: str, target_card: str):
    await handle_trade(ctx, member, your_card, target_card)

async def handle_trade(ctx_or_interaction, target_member: discord.Member, your_card_raw: str, target_card_raw: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    if target_member.id == user.id:
        msg = "❌ Bạn không thể tự giao dịch thẻ bài với chính mình!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    c1_id = normalize_card_id(your_card_raw)
    c2_id = normalize_card_id(target_card_raw)

    if not c1_id or c1_id not in CARDS_DATA:
        msg = f"❌ ID thẻ của bạn `{your_card_raw}` không hợp lệ!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if not c2_id or c2_id not in CARDS_DATA:
        msg = f"❌ ID thẻ bạn muốn nhận `{target_card_raw}` không hợp lệ!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    p1 = get_player(user.id, user.display_name)
    p2 = get_player(target_member.id, target_member.display_name)

    if is_card_locked(p1, c1_id):
        msg = f"🔒 Thẻ **{format_card_id(c1_id)}** của bạn đang bị Admin niêm phong! Không thể giao dịch."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if p1.get("inventory", {}).get(str(c1_id), 0) <= 0:
        msg = f"❌ Bạn không sở hữu thẻ bài **{format_card_id(c1_id)} {CARDS_DATA[c1_id]['name']}**!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if is_card_locked(p2, c2_id):
        msg = f"🔒 Thẻ **{format_card_id(c2_id)}** của {target_member.display_name} đang bị Admin niêm phong! Không thể giao dịch."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if p2.get("inventory", {}).get(str(c2_id), 0) <= 0:
        msg = f"❌ Đối phương {target_member.mention} không sở hữu thẻ bài **{format_card_id(c2_id)} {CARDS_DATA[c2_id]['name']}**!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    card1 = CARDS_DATA[c1_id]
    card2 = CARDS_DATA[c2_id]

    embed = discord.Embed(
        title="🤝 LỜI ĐỀ NGHỊ GIAO DỊCH THẺ BÀI TOUHOU",
        description=(
            f"👤 **Người gửi đề nghị:** {user.mention}\n"
            f"👤 **Người nhận đề nghị:** {target_member.mention}\n\n"
            f"📤 **{user.display_name} gửi trao:** `[{card1['rank']}]` **{format_card_id(card1['id'])} {card1['name']}**\n"
            f"📥 **Yêu cầu đổi lấy:** `[{card2['rank']}]` **{format_card_id(card2['id'])} {card2['name']}**\n\n"
            f"👉 {target_member.mention}, bạn có đồng ý thực hiện cuộc trao đổi này không?"
        ),
        color=0x3B82F6
    )
    embed.set_footer(text="Giao dịch sẽ tự động hết hạn sau 2 phút!")

    view = TradeConfirmView(user.id, target_member.id, c1_id, c2_id, user.display_name, target_member.display_name)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

# ==============================================================================
# 16. CÁC LỆNH TIỆN ÍCH: PROFILE, QUEST, BOSS, HELP
# ==============================================================================
@bot.tree.command(name="profile", description="Xem hồ sơ cá nhân, cấp độ, vé quay và tiến trình thu thập mảnh")
@app_commands.describe(nguoi_dung="Xem hồ sơ người chơi khác (để trống nếu xem chính mình)")
async def slash_profile(interaction: discord.Interaction, nguoi_dung: Optional[discord.Member] = None):
    await handle_profile(interaction, nguoi_dung)

@bot.command(name="profile", aliases=["hoso", "me"])
async def prefix_profile(ctx, member: Optional[discord.Member] = None):
    await handle_profile(ctx, member)

async def handle_profile(ctx_or_interaction, member: Optional[discord.Member] = None):
    target = member or (ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author)
    p = get_player(target.id, target.display_name)

    cur_lvl = p["level"]
    cur_xp = p["xp"]
    req_xp = get_xp_required_for_next_level(cur_lvl)
    xp_bar = get_hp_bar(cur_xp, req_xp, 10)

    total_cards = sum(p.get("inventory", {}).values())
    unique_cards = len([cid for cid, cnt in p.get("inventory", {}).items() if cnt > 0])
    seiki_shards = p.get("shards", {}).get("seiki", 0)

    win_rate = (p["battles_won"] / p["battles_total"] * 100) if p["battles_total"] > 0 else 0

    embed = discord.Embed(
        title=f"⛩️ HỒ SƠ PHÁP SƯ TOUHOU: {target.display_name.upper()}",
        color=0xEC4899
    )
    if target.avatar:
        embed.set_thumbnail(url=target.avatar.url)

    embed.add_field(
        name="📊 Cấp Độ & Kinh Nghiệm:",
        value=(
            f"• Cấp độ: **`Lv.{cur_lvl}`** *(Buff: +{get_level_atk_buff(cur_lvl)} ATK / +{get_level_hp_buff(cur_lvl)} HP)*\n"
            f"• Tiến trình: `{xp_bar}` **{cur_xp:,}/{req_xp:,} XP**"
        ),
        inline=False
    )
    embed.add_field(
        name="🎟️ Tài Sản & Vé Quay:",
        value=f"• Vé Pull hiện có: **`{p['pull_tickets']:.2f} Vé`**\n• Lượt miễn phí hôm nay: **`{p.get('free_pulls_remaining', 0)}/5`**",
        inline=True
    )
    embed.add_field(
        name="🎴 Thẻ Bài & Mảnh Shards:",
        value=f"• Thẻ đang có: **`{total_cards} lá`** *(Độc nhất: {unique_cards})*\n• 🔮 Mảnh Seiki: **`{seiki_shards}/10 Mảnh`**",
        inline=True
    )
    embed.add_field(
        name="⚔️ Chiến Tích Võ Đài:",
        value=f"• Thắng: **`{p['battles_won']}/{p['battles_total']}`** trận *(Tỷ lệ thắng: `{win_rate:.1f}%`)*",
        inline=False
    )

    team_str = []
    for idx, cid in enumerate(p.get("team", [])[:3], 1):
        norm = normalize_card_id(cid)
        c = CARDS_DATA.get(norm, CARDS_DATA.get(cid))
        if c:
            is_ace = is_card_ace2(p, cid)
            ace_tag = " ⭐[Ace 2]" if is_ace else ""
            team_str.append(f"Vị trí {idx}: **{format_card_id(c['id'])} {c['name']}** `[{c['rank']}]`{ace_tag}")
    embed.add_field(
        name="🛡️ Đội Hình Chiến Đấu (/team):",
        value="\n".join(team_str) if team_str else "Chưa xếp đội hình! Dùng `/team` để chọn.",
        inline=False
    )

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="quest", description="Xem danh sách 3/3 Nhiệm Vụ Ngày và phần thưởng vé quay")
async def slash_quest(interaction: discord.Interaction):
    await handle_quest(interaction)

@bot.command(name="quest", aliases=["nhiemvu", "dailyquest"])
async def prefix_quest(ctx):
    await handle_quest(ctx)

async def handle_quest(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    dq = ensure_daily_quests(player)

    embed = discord.Embed(
        title="🎯 NHIỆM VỤ NGÀY HAKUREI SHRINE (3/3 MỖI NGÀY)",
        description=(
            f"📅 Ngày áp dụng: `{dq['date']}` (Làm mới mỗi ngày theo giờ GMT+7)\n"
            "Hoàn thành các nhiệm vụ bên dưới để nhận vé quay miễn phí!\n"
            "👑 **Thưởng lớn:** Hoàn thành đủ cả 3 nhiệm vụ để nhận ngay **+10 Vé Pull**!"
        ),
        color=0xF59E0B
    )

    all_done = True
    for q in dq.get("quests", []):
        st = "✅ ĐÃ XONG" if q.get("completed") else f"⏳ `{q['current']}/{q['target']}`"
        if not q.get("completed"):
            all_done = False
        embed.add_field(
            name=f"Nhiệm vụ {q['id']}: {q['name']} (+{q['reward']} Vé 🎟️)",
            value=f"Tiến độ: {st} (Mục tiêu: {q['target']})",
            inline=False
        )

    all_claimed = dq.get("all_completed_claimed", False)
    all_bonus_status = "✅ ĐÃ NHẬN THƯỞNG (+10 Vé)" if all_claimed else ("🎁 SẴN SÀNG NHẬN!" if all_done else "🔒 Chưa hoàn thành đủ 3/3")
    embed.add_field(name="👑 Thưởng Trọn Vẹn 3/3 Nhiệm Vụ (+10 Vé Pull):", value=all_bonus_status, inline=False)

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="boss", description="Xem trạng thái Boss Raid, thời gian hồi chiêu và thông tin Seiki Dị Hình")
async def slash_boss(interaction: discord.Interaction):
    await handle_boss_info(interaction)

@bot.command(name="boss", aliases=["raid", "bossinfo"])
async def prefix_boss(ctx):
    await handle_boss_info(ctx)

async def handle_boss_info(ctx_or_interaction):
    global active_raid, boss_cooldown_until
    check_and_clean_expired_raid()
    now_ts = time.time()
    rem_cd = max(0, int(boss_cooldown_until - now_ts))

    if active_raid is not None:
        b_cfg = active_raid.get("boss_config", BOSS_CONFIG)
        embed = discord.Embed(
            title=f"🚨 BOSS RAID ĐANG DIỄN RA: {b_cfg['name'].upper()}!",
            description=(
                f"Trận chiến đang diễn ra tại kênh <#{active_raid['channel_id']}>!\n"
                f"• Người tham gia: {len(active_raid.get('participants', []))}/{b_cfg['max_players']} dũng giả\n"
                f"• Trạng thái: {'Đang giao tranh kịch liệt!' if active_raid.get('started') else 'Đang chuẩn bị (2 phút)!'}"
            ),
            color=0xDC2626
        )
        embed.set_thumbnail(url=b_cfg["image"])
    else:
        cd_str = f"⏱️ Đang hồi chiêu: **{rem_cd} giây** còn lại!" if rem_cd > 0 else "🟢 **SẴN SÀNG XUẤT HIỆN!** (Tỷ lệ 5% mỗi tin nhắn chat thông thường)"
        embed = discord.Embed(
            title="👺 THÔNG TIN BOSS RAID TOUHOU & DỊ TÀ SEIKI",
            description=(
                f"{cd_str}\n\n"
                "⛩️ **Cơ Chế Xuất Hiện:**\n"
                "• Khi hết hồi chiêu 15 phút, mỗi tin nhắn chat có **5% cơ hội** gọi ra **Seiki Dị Hình** (30k HP) hoặc **5%** gọi ra **Reimu Dị Hình** (Phase 1 30k HP & Phase 2 50k HP)!\n\n"
                "🎁 **Phần Thưởng Đặc Biệt Từ Boss Seiki:**\n"
                "• 10% cơ hội nhận **10 Vé Pull**, 40% nhận **5 Vé**, 50% nhận **3 Vé**!\n"
                "• 🔮 **2.5% tỷ lệ rơi Mảnh Seiki Shards** (Thu thập 10 mảnh để đổi Thẻ [T] #t1 Seiki qua lệnh `/t translate`)!\n\n"
                "👑 **Lệnh Admin Triệu Hồi Nhanh:**\n"
                "`boss admin spawn seiki` hoặc `boss admin spawn reimu` (Không cần hồi chiêu)!"
            ),
            color=0x7C3AED
        )
        embed.set_thumbnail(url=SEIKI_BOSS_CONFIG["image"])

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="help", description="Xem hướng dẫn toàn bộ lệnh game Touhou Card Battle và tính năng Bot")
async def slash_help(interaction: discord.Interaction):
    await handle_help(interaction)

@bot.command(name="help", aliases=["huongdan", "lenh"])
async def prefix_help(ctx):
    await handle_help(ctx)

async def handle_help(ctx_or_interaction):
    embed = discord.Embed(
        title="🌸 CẨM NANG HƯỚNG DẪN HAKUREI REIMU TOUHOU CARD BOT",
        description=(
            "Chào mừng bạn đến với thế giới thẻ bài Touhou Gensokyo!\n"
            "Dưới đây là toàn bộ danh sách lệnh và tính năng hỗ trợ đầy đủ tiếng Việt:"
        ),
        color=0xEC4899
    )

    embed.add_field(
        name="🎴 Gacha, Thẻ Bài & Đội Hình:",
        value=(
            "• `/pull [so_luong]`: Quay thẻ bài Touhou (1 lượt hoặc 10 lượt, 5 lượt free/ngày).\n"
            "• `/daily`: Điểm danh nhận vé quay gacha và XP mỗi ngày.\n"
            "• `/team [the_1] [the_2] [the_3]`: Xếp đội hình 3 thẻ bài (hỗ trợ cả thẻ `t1`).\n"
            "• `/collection`: Xem kho thẻ bài đã sưu tập và số lượng mảnh Shards.\n"
            "• `/card_info [id]`: Xem chỉ số, ảnh GIF và kỹ năng chi tiết của thẻ (kể cả Thẻ T `t1`)!\n"
            "• `/evol [id]`: Tiến hóa Reimu (13), Sakuya (16) hoặc Marisa (17) lên Ace 2 (+300 ATK/HP, trừ thẻ, Marisa x2.0 DMG)!"
        ),
        inline=False
    )

    embed.add_field(
        name="⚔️ Đấu Trường & Boss Raid:",
        value=(
            "• `/battle`: Đấu trường PvE 3vs3 với ảo ảnh võ giả Gensokyo.\n"
            "• `/pvp [doi_thu]`: Thách đấu PvP trực tiếp với thành viên khác trong server.\n"
            "• `/boss`: Xem trạng thái Boss Raid, hồi chiêu và cơ chế quà drop.\n"
            "• Bấm **'Diễn Biến Từng Hiệp (GIF)'** trong trận để thưởng thức hoạt ảnh Danmaku!"
        ),
        inline=False
    )

    embed.add_field(
        name="🔮 Nhóm Thẻ T Tối Thượng & Trao Đổi:",
        value=(
            "• `/t translate`: Ghép 10 Mảnh Seiki thành Thẻ [T] #t1 Seiki Đệ Pháp Toàn Năng!\n"
            "• `/t info`: Xem hướng dẫn săn mảnh từ Boss Seiki (tỷ lệ 2.5%).\n"
            "• `/trade [nguoi_nhan] [the_cua_ban] [the_muon_lay]`: Trao đổi thẻ với bạn bè."
        ),
        inline=False
    )

    embed.add_field(
        name="💬 Trò Chuyện Cùng Reimu AI (Gemini Flash):",
        value=(
            "• Chat nhắc tên `Reimu` hoặc reply tin nhắn của bot để trò chuyện.\n"
            "• Reimu rất đanh đá, lười biếng, cuồng tiền công đức và cực kỳ ghét đàn ông (nhưng cực kỳ hiếu thảo, dịu dàng với Bố Nuôi Han Seiki)!"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Lệnh Admin (Dành riêng cho Owner & Bố Seiki):",
        value=(
            "• `boss admin spawn [seiki/reimu]`: Triệu hồi Boss khẩn cấp tại kênh.\n"
            "• `boss admin reset`: Reset toàn bộ trạng thái Boss Raid bị kẹt.\n"
            "• `/admin_add_card`, `/admin_add_shard`, `/admin_set_level`, `/admin_lock`, `/admin_confiscate`."
        ),
        inline=False
    )

    embed.set_footer(text="Hakurei Shrine • Touhou Project Card Battle System v3.0")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

# ==============================================================================
# 17. WEB SERVER HTTP KEEP-ALIVE & KHỞI CHẠY BOT
# ==============================================================================
def run_keep_alive():
    server_port = int(os.getenv("PORT", 8080))
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "Hakurei Reimu Discord Bot is alive and running 24/7!"

    @app.route('/health')
    def health():
        return {"status": "ok", "bot": "Hakurei Reimu", "uptime": "running"}

    app.run(host='0.0.0.0', port=server_port)

def keep_alive():
    t = Thread(target=run_keep_alive)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    keep_alive()
    if not DISCORD_TOKEN:
        print("❌ [LỖI] Biến môi trường DISCORD_TOKEN chưa được thiết lập!", flush=True)
    else:
        bot.run(DISCORD_TOKEN)


