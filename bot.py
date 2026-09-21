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
# 9. ACE 2 MỚI:
#    - [#09] Flandre Scarlet (30 thẻ): Ripples of 495 Years — 25% xóa 50% HP đối thủ (Battle/PvP)
#      hoặc 30% HP Boss (Raid Phase 1 & 2), kích hoạt 1 lần/trận, kèm GIF kỹ năng trực tiếp!
#    - Buff Marisa Ace 2 [#17]: Master Spark tăng sát thương từ ×1.5 lên ×2.0!
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
                "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/e7/fe/JOKpsPyd.gif"
            },
            "master_spark": {
                "name": "Master Spark",
                "chance": 0.30,
                "multiplier": 1.5,
                "desc": "30% gây 1.5x sát thương 1 lần trong trận",
                "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/f4/32/3xCGLkOw.gif"
            },
            "medicine_sign": {
                "name": "Medicine Sign",
                "chance": 0.20,
                "desc": "20% hồi phục cho bản thân 1 lần trong trận",
                "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/8d/12/mwVdJaFQsefrsAuNS.gif"
            }
        }
    }
}
CARDS_DATA["T1"] = CARDS_DATA["t1"]

# ==============================================================================
# GIF HOẠT ẢNH TUYỆT KỸ THẺ [T] #t1 SEIKI (dùng chung cho Raid, Battle & PvP)
# ==============================================================================
T1_SKILL_CONFIGS = CARDS_DATA["t1"]["skills"]
T1_SEAL_GIF = T1_SKILL_CONFIGS["fantasy_seal"]["gif"]    # https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/e7/fe/JOKpsPyd.gif
T1_SPARK_GIF = T1_SKILL_CONFIGS["master_spark"]["gif"]   # https://www.google.com/url?sa=E&q=https%3A%2F%2Fstatic2.klipy.com%2Fii%2Fc3a19a0b747a76e98651f2b9a3cca5ff%2Ff4%2F32%2F3xCGLkOw.gif
T1_HEAL_GIF = T1_SKILL_CONFIGS["medicine_sign"]["gif"]   # https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/8d/12/mwVdJaFQsefrsAuNS.gif

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
            "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/f4/32/3xCGLkOw.gif"
        },
        "fantasy_seal": {
            "name": "Fantasy Seal",
            "chance": 0.20,
            "desc": "20% kích hoạt kết giới phong ấn, MIỄN TOÀN BỘ SÁT THƯƠNG trong 1 turn!",
            "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/e7/fe/JOKpsPyd.gif"
        },
        "blitz_attack": {
            "name": "Blitz Attack",
            "chance": 0.25,
            "damage": 4000,
            "desc": "25% gây 4,000 DMG diện rộng trực tiếp lên toàn bộ thẻ tiền tuyến!",
            "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/53/3d/F3J4ZC2CZxVLy4Nh.gif"
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
        "skill_name": "Bát Quái Lô - Master Spark (Sát Thương ×2.0)",
        "skill_desc": "Kích hoạt 1 lần trong trận: 30% tung ra Master Spark với sát thương ×2.0 lần sát thương gốc!",
        "skill_gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/f4/32/73qv2IMW.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    9: {
        "id": 9,
        "key": "flandre",
        "name": "Flandre Scarlet",
        "title": "[#09] Flandre Scarlet - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 30,
        "required_pulls": 30,
        "evol_gif": "https://static2.klipy.com/ii/e1b92bb53e0c9e442408bc677a56c789/97/0e/NQbwEU2dLTI18V.gif",
        "skill_name": "Ripples of 495 Years (Bóng Gợn 495 Năm)",
        "skill_desc": "Kích hoạt 1 lần duy nhất trong trận (Tỷ lệ 25%): Xóa sổ 50% HP đối thủ trong Battle/PvP, hoặc lấy đi 30% HP Boss trong Raid (áp dụng cả Phase 1 & Phase 2)!",
        "skill_gif": "https://static2.klipy.com/ii/e293a233a303a98e471f78d04e13a1b0/b2/cf/xq2ZW3uF.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    }
}
EVOL_CONFIG["13"] = EVOL_CONFIG[13]
EVOL_CONFIG["16"] = EVOL_CONFIG[16]
EVOL_CONFIG["17"] = EVOL_CONFIG[17]
EVOL_CONFIG["9"] = EVOL_CONFIG[9]

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
    9: {"title": "Ác Ma Cuồng Loạn", "skill_name": "Tuyệt Đối Phá Hủy (Kyū)", "skill_desc": "Bóp nát 'mục tiêu tồn tại' trong lòng bàn tay, giải phóng sức mạnh ma cà rồng hủy diệt không thể ngăn cản (610 ATK / 5,700 HP). [Ace 2 ⭐⭐]: Ripples of 495 Years (25%) — Xóa sổ 50% HP đối thủ (Battle/PvP) hoặc 30% HP Boss (Raid), kích hoạt 1 lần trong trận!"},
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

def get_owned_card_ids(player: dict) -> list:
    """Trả về danh sách ID thẻ đang sở hữu (đã chuẩn hóa, chưa bị Admin khóa).
    FIX: Hỗ trợ đầy đủ cả key string ('13', 't1') trong inventory và thẻ đặc biệt [T] #t1."""
    ids = []
    for cid, cnt in player.get("inventory", {}).items():
        if cnt <= 0:
            continue
        norm = normalize_card_id(cid)
        if norm is not None and norm in CARDS_DATA and not is_card_locked(player, norm):
            if norm not in ids:
                ids.append(norm)
    return ids

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
                lbl = f"{ace_tag}{format_card_id(c['cid'])} {c['raw_name']} [{c['rank']}]"[:100]
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
            description=f"Soi chiến thuật thẻ bài **{'⭐ [Ace 2] ' if is_ace else ''}{format_card_id(c['cid'])} {c['raw_name']}** của đối phương!",
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
        if is_ace and c["cid"] in [9, 13, 16, 17]:
            if c["cid"] == 13:
                skill_text += "\n🛡️ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Vô Tưởng Chuyển Sinh* né toàn bộ sát thương."
            elif c["cid"] == 16:
                skill_text += "\n⏳ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Thời Gian Đóng Băng* khiến đối phương mất lượt."
            elif c["cid"] == 17:
                skill_text += "\n🌟 **[Ace 2 Hiệu Ứng]** 30% kích hoạt *Master Spark* bộc phá ×2.0 sát thương."
            elif c["cid"] == 9:
                skill_text += "\n🦇 **[Ace 2 Hiệu Ứng]** 25% kích hoạt *Ripples of 495 Years* xóa sổ 50% HP đối thủ (30% HP Boss trong Raid, 1 lần/trận)."
        embed.add_field(name="✨ Kỹ Năng / Tuyệt Kỹ Danmaku:", value=f"*{skill_text}*", inline=False)

        summary_lines = []
        for i, card in enumerate(self.opp_cards):
            arrow = "👉 " if i == self.selected_idx else "• "
            ace_star = "⭐ " if card.get("is_ace2") else ""
            ace_label = " `[Ace 2]`" if card.get("is_ace2") else ""
            summary_lines.append(
                f"{arrow}{ace_star}**{format_card_id(card['cid'])} {card['raw_name']}** `[{card['rank']}]`{ace_label} ⚔️ `{card['power']:,} DMG` | ❤️ `{card['hp']:,} HP`"
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
        reimu_line = f"🌸 **Reimu thảng thốt:** *\"{cfg['reimu_quote']}\"*\n\n"
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
            value="• 10% cơ hội nhận **10 Vé Pull**, 40% nhận **5 Vé**, 50% nhận **3 Vé**!\n• 🔮 **2.5%** rơi **+1 Mảnh Seiki** (10 mảnh = 1 thẻ [T] #t1 Seiki - dùng `/t translate`)!\n• Nhận thêm **+100 XP** và điểm danh nhiệm vụ diệt Boss!",
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

        current_team = [cid for cid in player.get("team", []) if cid in CARDS_DATA and not is_card_locked(player, cid)]
        if len(current_team) < 3:
            owned_ids = get_owned_card_ids(player)
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
            owned_ids = get_owned_card_ids(p)
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
            "flandre_used": False,
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
        flandre_notif = None
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
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = EVOL_CONFIG[17]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss!"

            # KỸ NĂNG ACE 2 FLANDRE - RIPPLES OF 495 YEARS (25%: LẤY 30% HP BOSS, 1 LẦN/TRẬN)
            if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                if random.random() < 0.25:
                    c["flandre_used"] = True
                    rip_dmg = int(p1_hp * 0.30)
                    p1_hp = max(0, p1_hp - rip_dmg)
                    c["total_dmg"] += rip_dmg
                    if not turn_image:
                        turn_image = EVOL_CONFIG[9]["skill_gif"]
                    flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} DMG (30% HP Boss)** ngay lập tức!"
            
            # Kỹ năng Thẻ Seiki T1 (Tuân thủ: Không bao giờ kích hoạt 2 chiêu trong cùng 1 lượt!)
            if str(ac["cid"]).lower() == "t1":
                if c.get("seiki_used_turn") != p1_rounds:
                    if not c.get("seiki_spark_used") and random.random() < 0.30:
                        c["seiki_spark_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image:
                            turn_image = T1_SPARK_GIF
                        marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({c['username']}) bộc phát **Master Spark** (30%)! Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss!"
                    elif not c.get("seiki_heal_used") and ac["current_hp"] < ac["max_hp"] and random.random() < 0.20:
                        c["seiki_heal_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        heal_val = int(ac["max_hp"] * 0.30)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image:
                            turn_image = T1_HEAL_GIF
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
                    turn_image = SEIKI_BOSS_CONFIG["skills"]["fantasy_seal"]["gif"]
                    boss_action_log = "🛡️ **[KỸ NĂNG] Seiki Dị Hình** kích hoạt **Fantasy Seal (20%)**! Vận khởi kết giới phong ấn tuyệt đối, MIỄN TOÀN BỘ SÁT THƯƠNG trong 1 turn!"
                elif seiki_action == "blitz_attack":
                    turn_image = SEIKI_BOSS_CONFIG["skills"]["blitz_attack"]["gif"]
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
                                turn_image = T1_SEAL_GIF
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            ac["current_hp"] -= 4000
                elif seiki_action in ["spark_start", "spark_active"]:
                    turn_image = SEIKI_BOSS_CONFIG["skills"]["multi_spark"]["gif"]
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
                                turn_image = T1_SEAL_GIF
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
                                turn_image = T1_SEAL_GIF
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
                                turn_image = T1_SEAL_GIF
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
                                turn_image = T1_SEAL_GIF
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
        if flandre_notif:
            round_embed.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
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
                *([("🦇 Ripples of 495 Years:", flandre_notif, False)] if flandre_notif else []),
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
        c["flandre_used"] = False
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
        flandre_notif = None
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
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = EVOL_CONFIG[17]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#17] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"

            # KỸ NĂNG ACE 2 FLANDRE - RIPPLES OF 495 YEARS (25%: LẤY 30% HP BOSS PHASE 2, 1 LẦN/TRẬN)
            if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                if random.random() < 0.25:
                    c["flandre_used"] = True
                    rip_dmg = int(p2_hp * 0.30)
                    p2_hp = max(0, p2_hp - rip_dmg)
                    c["total_dmg"] += rip_dmg
                    if not turn_image:
                        turn_image = EVOL_CONFIG[9]["skill_gif"]
                    flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} DMG (30% HP Boss Phase 2)** ngay lập tức!"

            # Kỹ năng Thẻ Seiki T1 (Tuân thủ: Không bao giờ kích hoạt 2 chiêu trong cùng 1 lượt!)
            if str(ac["cid"]).lower() == "t1":
                if c.get("seiki_used_turn") != p2_rounds:
                    if not c.get("seiki_spark_used") and random.random() < 0.30:
                        c["seiki_spark_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image:
                            turn_image = T1_SPARK_GIF
                        marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({c['username']}) bộc phát **Master Spark** (30%)! Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"
                    elif not c.get("seiki_heal_used") and ac["current_hp"] < ac["max_hp"] and random.random() < 0.20:
                        c["seiki_heal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        heal_val = int(ac["max_hp"] * 0.30)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image:
                            turn_image = T1_HEAL_GIF

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
                            turn_image = T1_SEAL_GIF
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
                            turn_image = T1_SEAL_GIF
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
        if flandre_notif:
            round_embed.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
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
                *([("🦇 Ripples of 495 Years:", flandre_notif, False)] if flandre_notif else []),
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
    elif roll < 0.0301: chosen = random.choice(CARDS_BY_RANK["S"])
    elif roll < 0.2301: chosen = random.choice(CARDS_BY_RANK["A"])
    elif roll < 0.5301: chosen = random.choice(CARDS_BY_RANK["B"])
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

    # CƠ CHẾ MỞ KHÓA THẺ BỊ ADMIN LOCK: Khi quay trúng lại chính lá bài đó
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

# ==============================================================================
# LỆNH MỚI: /admin_lock - KHÓA THẺ ĐÃ SỞ HỮU, CHỈ MỞ KHI PULL RA LẠI
# ==============================================================================
@bot.tree.command(name="admin_lock", description="[CHỦ BOT DUY NHẤT] Khóa lá bài đã sở hữu của người chơi (chỉ mở khi pull ra lại)")
@app_commands.describe(nguoi_dung="Người chơi bị khóa thẻ", id_the="ID lá bài từ 1-26")
async def slash_admin_lock(interaction: discord.Interaction, nguoi_dung: discord.Member, id_the: int):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ chủ bot mới có quyền khóa thẻ.", ephemeral=True)
        return

    if id_the not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-{len(CARDS_DATA)})!", ephemeral=True)
        return

    target = get_player(nguoi_dung.id, nguoi_dung.display_name)
    inv = target.get("inventory", {})
    cid_str = str(id_the)
    owned = inv.get(cid_str, 0)
    unlocked = is_card_unlocked(target, id_the)

    if owned <= 0 and not unlocked:
        await interaction.response.send_message(
            f"⚠️ **{nguoi_dung.display_name}** chưa từng sở hữu thẻ bài #{id_the:02d} {CARDS_DATA[id_the]['name']}! Không thể khóa.",
            ephemeral=True
        )
        return

    locked_list = target.setdefault("locked_cards", [])
    if id_the in locked_list or cid_str in locked_list:
        await interaction.response.send_message(
            f"⚠️ Thẻ #{id_the:02d} của {nguoi_dung.mention} đã bị khóa từ trước rồi!",
            ephemeral=True
        )
        return

    locked_list.append(id_the)

    # Tự động gỡ khỏi đội hình nếu người đó đang trang bị thẻ này
    team = target.get("team", [])
    removed_from_team = False
    if id_the in team:
        team.remove(id_the)
        target["team"] = team
        removed_from_team = True

    save_player(target)
    card = CARDS_DATA[id_the]

    removed_team_str = "• ⚠️ Đã tự động gỡ khỏi đội hình chiến đấu (/team)!\n" if removed_from_team else ""
    embed = discord.Embed(
        title="🔒 [ADMIN LOCK] ĐÃ NIÊM PHONG THẺ BÀI!",
        description=(
            f"👑 **Thực hiện bởi:** {interaction.user.mention}\n"
            f"👤 **Người chơi bị phạt:** {nguoi_dung.mention}\n"
            f"🎴 **Lá bài bị khóa:** `[{card['rank']}]` **#{card['id']:02d} {card['name']}**\n\n"
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
async def prefix_admin_lock(ctx, member: discord.Member, card_id: int):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return

    if card_id not in CARDS_DATA:
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-{len(CARDS_DATA)})!")
        return

    target = get_player(member.id, member.display_name)
    cid_str = str(card_id)
    inv = target.get("inventory", {})
    owned = inv.get(cid_str, 0)
    unlocked = is_card_unlocked(target, card_id)

    if owned <= 0 and not unlocked:
        await ctx.send(f"⚠️ {member.display_name} chưa từng sở hữu thẻ bài này!")
        return

    locked_list = target.setdefault("locked_cards", [])
    if card_id in locked_list or cid_str in locked_list:
        await ctx.send(f"⚠️ Thẻ này của {member.mention} đã bị khóa từ trước!")
        return

    locked_list.append(card_id)
    if card_id in target.get("team", []):
        target["team"].remove(card_id)

    save_player(target)
    card = CARDS_DATA[card_id]
    await ctx.send(f"🔒 Đã khóa thẻ **[#{card['id']:02d}] {card['name']}** của {member.mention}! Chỉ được mở khi pull trúng lại.")

# LỆNH ADMIN: /admin_reset_quest - LÀM MỚI THỦ CÔNG NHIỆM VỤ NGÀY CHO NGƯỜI CHƠI HOẶC BẢN THÂN
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

    @discord.ui.button(label="🦇 [#09] Tiến Hóa Flandre Ace 2 (30 Thẻ)", style=discord.ButtonStyle.danger, emoji="💥")
    async def button_evol_flandre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 9)

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

    color_map = {9: 0xDC2626, 13: 0xEF4444, 16: 0x3B82F6, 17: 0xF59E0B}
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
        elif nv_clean in ("9", "#9", "09", "#09") or "flandre" in nv_clean or "flan" in nv_clean:
            cid_target = 9

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

    flandre_cnt = player.get("inventory", {}).get("9", 0)
    flandre_ace = is_card_ace2(player, 9)
    flandre_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if flandre_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if flandre_cnt >= 30 else f"🔴 Chưa đủ ({flandre_cnt}/30)")

    embed = discord.Embed(
        title="🌟 PHÒNG TIẾN HÓA NHÂN VẬT TOUHOU (EVOLUTION - ACE 2)",
        description=(
            "Thu thập đủ số lượng thẻ yêu cầu để tiến hóa nhân vật lên **Ace 2 ⭐⭐**!\n"
            "✨ **Quy tắc Ace mới:** Sau khi tiến hóa sẽ **trừ đi chi phí thẻ** tương ứng (ví dụ: 30 lá -> 0, 32 lá -> 2).\n"
            "💪 **Buff Ace 2 mới:** Cộng **+300 ATK** và **+300 HP** vĩnh viễn!\n\n"
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

    flandre_cfg = EVOL_CONFIG[9]
    embed.add_field(
        name=f"🦇 [#{flandre_cfg['id']:02d}] {flandre_cfg['name']} (Yêu cầu 30 thẻ):",
        value=(
            f"• Trạng thái: **{flandre_status}\n"
            f"• Trong túi đồ: **{flandre_cnt}/30** lá *(tiến hóa xong trừ 30 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{flandre_cfg['skill_name']}** (25% xóa 50% HP đối thủ / 30% HP Boss Raid, kích hoạt 1 lần trong trận, kèm GIF trực tiếp!)"
        ),
        inline=False
    )
    embed.set_footer(text="Bấm nút chọn hoặc dùng /evol kèm ID nhân vật!")

    view = EvolSelectView(player, user.id)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="evol", description="Tiến hóa nhân vật Touhou lên Ace 2 (9: Flandre, 13: Reimu, 16: Sakuya, 17: Marisa)")
@app_commands.describe(id_hoac_ten="Nhập số ID thẻ (9, 13, 16 hoặc 17) hoặc chọn nhân vật")
@app_commands.choices(id_hoac_ten=[
    app_commands.Choice(name="[#13] Reimu Hakurei (Ace 2 - Cần 20 thẻ, trừ 20 khi Ace)", value="13"),
    app_commands.Choice(name="[#16] Sakuya Izayoi (Ace 2 - Cần 30 thẻ, trừ 30 khi Ace)", value="16"),
    app_commands.Choice(name="[#17] Marisa Kirisame (Ace 2 - Cần 25 thẻ, Master Spark x2.0)", value="17"),
    app_commands.Choice(name="[#09] Flandre Scarlet (Ace 2 - Cần 30 thẻ, Ripples of 495 Years)", value="9")
])
async def slash_evol(interaction: discord.Interaction, id_hoac_ten: str = None):
    await handle_evol(interaction, id_hoac_ten)

@bot.command(name="evol", aliases=["tienhoa", "ace2"])
async def prefix_evol(ctx, id_hoac_ten: str = None):
    await handle_evol(ctx, id_hoac_ten)

# ==============================================================================
# 11. CÁC LỆNH GAME: PULL, DAILY, TEAM, COLLECTION, TUTORIAL, QUEST
# ==============================================================================
async def handle_pull(ctx_or_interaction, count: int = 1):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    tut = player.get("tutorial", {})

    # BẢO MẬT CHỐNG BUG TUTORIAL: Kiểm tra cờ vĩnh viễn pull_used
    if tut.get("active") and tut.get("step") == "pull" and not tut.get("pull_used", False):
        available_ids = [cid for cid, card in CARDS_DATA.items() if card.get("rank") != "SS" and isinstance(cid, int)]
        unowned = [cid for cid in available_ids if not is_card_unlocked(player, cid)]
        if len(unowned) >= 3:
            chosen_ids = random.sample(unowned, 3)
        else:
            chosen_ids = random.sample(available_ids, min(3, len(available_ids)))

        results = []
        last_card = None
        for cid in chosen_ids:
            card = CARDS_DATA[cid]
            last_card = card
            cid_str = str(cid)
            player["inventory"][cid_str] = player["inventory"].get(cid_str, 0) + 1
            player.setdefault("pull_stats", {})[cid_str] = player.get("pull_stats", {}).get(cid_str, 0) + 1
            unlocked = player.setdefault("unlocked_cards", [])
            if cid not in unlocked:
                unlocked.append(cid)
            results.append(f"• `[#{card['id']:02d}]` **[{card['rank']}] {card['name']}** (⚔️{card['power']} | ❤️{card['hp']}) ✨ **[MỚI]**")

        # KHÓA VĨNH VIỄN BƯỚC PULL TÂN THỦ: ĐẶT CỜ pull_used = True
        tut["quest_pulls_remaining"] = 0
        tut["pull_used"] = True
        tut["step"] = "collection"
        save_player(player)

        embed = discord.Embed(
            title="🌸 KẾT QUẢ PULL TÂN THỦ (3 LƯỢT 100% KHÔNG TRÙNG - KHÔNG RA BẬC SS)",
            description="\n".join(results),
            color=0x10B981
        )
        if last_card:
            embed.set_thumbnail(url=last_card["image"])
        embed.add_field(
            name="⛩️ BƯỚC TIẾP THEO (TIẾN TRÌNH 1 CHIỀU):",
            value=f"🔔 {user.mention} **Reimu:** *\"Có vẻ ngươi đã đủ đội hình rồi đấy, giờ hãy kiểm tra đội ngũ mình nào `/collection`\"*",
            inline=False
        )
        embed.set_footer(text="Nhiệm vụ tân thủ: Dùng lệnh /collection để tiếp tục!")
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
        else: await ctx_or_interaction.send(embed=embed)
        return

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
    unlocked_notifs = []
    card = None
    for _ in range(count):
        card, is_dup, conv, unlocked_from_lock = execute_single_pull(player)
        dup_text = f" *(Trùng! +{conv:.2f} vé pull)*" if is_dup else " ✨ **[MỚI]**"
        if unlocked_from_lock:
            dup_text += " 🔓 **[ĐÃ MỞ KHÓA BỞI ADMIN!]**"
            unlocked_notifs.append(f"🔓 Chúc mừng! Bạn đã quay trúng lại **#{card['id']:02d} {card['name']}**, thẻ bài đã được giải phóng khỏi trạng thái khóa Admin!")
        results.append(f"• `[#{card['id']:02d}]` **[{card['rank']}] {card['name']}** (⚔️{card['power']} | ❤️{card['hp']}){dup_text}")

    dq_notifs = update_daily_quest_progress(player, "pull", count)
    save_player(player)

    embed = discord.Embed(
        title=f"🌸 KẾT QUẢ PULL THẺ GACHA ({count} LƯỢT)",
        description="\n".join(results),
        color=0xDC2626 if any(c.startswith("• `[#") and "[SS]" in c for c in results) else 0x3B82F6
    )
    if card:
        embed.set_thumbnail(url=card["image"])
    if unlocked_notifs:
        embed.add_field(name="🔓 GIẢI PHÓNG THẺ BÀI BỊ KHÓA:", value="\n".join(unlocked_notifs), inline=False)
    if dq_notifs:
        embed.add_field(name="📜 Tiến Trình Nhiệm Vụ Ngày:", value="\n\n".join(dq_notifs), inline=False)
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

    if player.get("_is_first_time") and not player.get("tutorial", {}).get("completed"):
        player["_is_first_time"] = False
        await send_tutorial_intro(ctx_or_interaction, player)
        return

    today = get_today_vn()

    if player.get("last_daily_date") == today:
        time_left = format_time_until_midnight_vn()
        msg = f"⛩️ Hôm nay bạn đã nhận vé Daily rồi! Hãy quay lại sau **{time_left}** (vào lúc 00:00 ngày mai nhé)!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    player["last_daily_date"] = today
    player["pull_tickets"] += 1.0
    dq_notifs = update_daily_quest_progress(player, "daily", 1)
    save_player(player)
    embed = discord.Embed(
        title="🎁 ĐIỂM DANH HÀNG NGÀY / DAILY REWARD",
        description=f"Chúc mừng **{user.display_name}** đã viếng đền Hakurei!\nBạn nhận được: **+1 Lượt Pull** 🎟️\nTổng vé pull hiện có: **{player['pull_tickets']:.2f}**",
        color=0xF59E0B
    )
    if dq_notifs:
        embed.add_field(name="📜 Tiến Trình Nhiệm Vụ Ngày:", value="\n\n".join(dq_notifs), inline=False)
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

    if player.get("_is_first_time") and not player.get("tutorial", {}).get("completed"):
        player["_is_first_time"] = False
        await send_tutorial_intro(ctx_or_interaction, player)
        return

    cur_lvl, xp_in_lvl, needed_xp, ratio = get_level_progress(player.get("xp", 0))
    lvl_buff_pwr = get_level_atk_buff(cur_lvl)
    lvl_buff_hp = get_level_hp_buff(cur_lvl)
    act = action.lower().strip() if action else "view"
    if card_id is not None:
        card_id = normalize_card_id(card_id)

    if act == "add":
        if not card_id or card_id not in CARDS_DATA:
            msg = f"❌ Vui lòng nhập số ID thẻ hợp lệ (1-26 hoặc t1)!"
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        # CHẶN THẺ BỊ ADMIN KHÓA
        if is_card_locked(player, card_id):
            msg = f"🔒 Thẻ **{format_card_id(card_id)} {CARDS_DATA[card_id]['name']}** hiện đang bị Quản Trị Viên niêm phong! Bạn chỉ có thể dùng lại khi quay gacha (`/pull`) trúng lại lá này."
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        cid_str = str(card_id)
        owned_inv = player["inventory"].get(cid_str, 0)
        unlocked = is_card_unlocked(player, card_id)
        if owned_inv < 1 and not unlocked:
            msg = f"⚠️ Bạn chưa sở hữu hoặc chưa mở khóa thẻ {format_card_id(card_id)} {CARDS_DATA[card_id]['name']}! Hãy dùng `/pull` hoặc `/t translate` để mở khóa."
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

        if card_id in player["team"]:
            msg = f"⚠️ Thẻ {format_card_id(card_id)} đã có sẵn trong đội hình rồi!"
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
        msg = f"✅ Đã thêm **{format_card_id(card['id'])} [{card['rank']}] {card['name']}** vào đội hình! (Lực chiến: ⚔️{card['power'] + lvl_buff_pwr + ace_pwr:,} | ❤️{card['hp'] + lvl_buff_hp + ace_hp:,})"

        tut = player.get("tutorial", {})
        if tut.get("active") and tut.get("step") == "team":
            if len(player["team"]) >= 3:
                tut["step"] = "battle"
                save_player(player)
                msg += f"\n\n🔔 {user.mention} ⛩️ **Reimu:** *\"Giờ hãy thử `/battle` đi\"*"
            else:
                msg += f"\n\n💡 *Nhiệm vụ tân thủ: Đã thêm {len(player['team'])}/3 thẻ vào đội hình! Hãy tiếp tục add đủ 3 lần nhé!*"

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
        msg = f"🗑️ Đã gỡ thành công thẻ {format_card_id(card_id)} khỏi đội hình!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg)
        else: await ctx_or_interaction.send(msg)
        return

    filled_bars = int(ratio * 10)
    bar_str = "▰" * filled_bars + "▱" * (10 - filled_bars)
    embed = discord.Embed(title=f"🛡️ ĐỘI HÌNH CHIẾN ĐẤU - {user.display_name.upper()}", color=0x3B82F6)
    embed.add_field(
        name=f"⭐ CẤP ĐỘ: Lv.{cur_lvl}",
        value=f"• **Tiến trình:** `{bar_str}` **{xp_in_lvl}/{needed_xp} XP** (Cần {needed_xp - xp_in_lvl} XP để lên Lv.{cur_lvl + 1})\n• **Buff Lv.{cur_lvl}:** +{lvl_buff_pwr:,} Power & +{lvl_buff_hp:,} HP",
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
                pwr = c["power"] + lvl_buff_pwr + ace_pwr
                hp = c["hp"] + lvl_buff_hp + ace_hp
                tot_pwr += pwr
                tot_hp += hp
                ace_tag = f" ⭐ [Ace 2: +{ACE_POWER_BUFF} ATK, +{ACE_HP_BUFF} HP]" if is_ace else ""
                embed.add_field(name=f"Vị trí #{idx}: [{format_card_id(c['id'])}] [{c['rank']}] {c['name']}{ace_tag}", value=f"⚔️ Power: **{pwr:,}** | ❤️ HP: **{hp:,}**", inline=False)
            else:
                embed.add_field(name=f"Vị trí #{idx}: 🔲 [Trống]", value="Dùng `/team add` để xếp thêm thẻ.", inline=False)
        embed.add_field(name="📊 TỔNG LỰC CHIẾN:", value=f"⚔️ Tổng Power: **{tot_pwr:,}** | ❤️ Tổng HP: **{tot_hp:,}**", inline=False)
        embed.set_thumbnail(url=CARDS_DATA[player["team"][0]]["image"])

    embed.set_footer(text=f"Hakurei Shrine • Thắng {player.get('battles_won', 0)} trận")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="team", description="Quản lý đội hình 3 thẻ (view, add, remove)")
@app_commands.describe(hanh_dong="view (xem), add (thêm thẻ), remove (gỡ thẻ)", id_the="ID thẻ (1-26 hoặc t1)")
@app_commands.choices(hanh_dong=[
    app_commands.Choice(name="👁️ Xem đội hình (view)", value="view"),
    app_commands.Choice(name="➕ Thêm thẻ (add)", value="add"),
    app_commands.Choice(name="➖ Gỡ thẻ (remove)", value="remove")
])
async def slash_team(interaction: discord.Interaction, hanh_dong: app_commands.Choice[str] = None, id_the: str = None):
    action = hanh_dong.value if hanh_dong else "view"
    await handle_team(interaction, action, id_the)

@bot.command(name="team")
async def prefix_team(ctx, action: str = "view", card_id: str = None):
    await handle_team(ctx, action, card_id)

async def handle_collection(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    owned = 0
    lines = []
    for cid in range(1, 27):
        if cid not in CARDS_DATA:
            continue
        card = CARDS_DATA[cid]
        cnt = player["inventory"].get(str(cid), 0)
        unlocked = is_card_unlocked(player, cid)
        locked = is_card_locked(player, cid)

        if locked:
            lines.append(f"🔒 **{format_card_id(card['id'])} [{card['rank']}] {card['name']}** ×{cnt} `[BỊ ADMIN KHÓA - Cần pull ra để mở]`")
        elif cnt > 0 or unlocked:
            owned += 1
            is_ace = is_card_ace2(player, cid)
            ace_mark = " ⭐⭐ [Ace 2]" if is_ace else ""
            if cnt > 0:
                lines.append(f"✅ **{format_card_id(card['id'])} [{card['rank']}] {card['name']}** ×{cnt}{ace_mark}")
            else:
                lines.append(f"🔓 **{format_card_id(card['id'])} [{card['rank']}] {card['name']}** ×0 *(Đã mở khóa)*{ace_mark}")
        else:
            lines.append(f"🔒 `{format_card_id(card['id'])}` [{card['rank']}] {card['name']} *(Chưa có)*")

    t_lines = []
    shards_cnt = player.get("shards", {}).get("seiki", 0)
    for t_cid in ["t1"]:
        if t_cid in CARDS_DATA:
            t_card = CARDS_DATA[t_cid]
            t_cnt = player["inventory"].get(t_cid, 0)
            t_unlocked = is_card_unlocked(player, t_cid)
            if t_cnt > 0 or t_unlocked:
                t_status = f"✅ **{format_card_id(t_card['id'])} [{t_card['rank']}] {t_card['name']}** ×{t_cnt}"
            else:
                t_status = f"🔒 `{format_card_id(t_card['id'])}` [{t_card['rank']}] {t_card['name']} *(Chưa sở hữu)*"
            t_shard_info = f"   └ 💎 **Mảnh Seiki:** `{shards_cnt}/10` mảnh"
            if shards_cnt >= 10:
                t_shard_info += " ✨ *(Đủ 10 mảnh! Dùng `/t translate` để đổi ngay!)*"
            t_lines.append(f"{t_status}\n{t_shard_info}")

    desc_text = "\n".join(lines)
    if t_lines:
        desc_text += "\n\n🔮 **THẺ ĐẶC BIỆT (NHÓM T - ĐỔI TỪ MẢNH SHARDS):**\n" + "\n".join(t_lines)

    embed = discord.Embed(title=f"📖 BỘ SƯU TẬP THẺ TOUHOU ({owned}/26)", description=desc_text, color=0x8B5CF6)

    tut = player.get("tutorial", {})
    if tut.get("active") and tut.get("step") == "collection":
        tut["step"] = "team"
        save_player(player)
        embed.add_field(
            name="⛩️ BƯỚC TIẾP THEO (TIẾN TRÌNH 1 CHIỀU):",
            value=f"🔔 {user.mention} **Reimu:** *\"Tốt tốt, giờ nhìn id của họ và `/team add <id>` nào, nhớ là add đủ 3 lần nhé\"*",
            inline=False
        )

    embed.set_footer(text="Quay thêm thẻ bằng lệnh /pull • Thẻ quay được sẽ mở khóa vĩnh viễn")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="collection", description="Kiểm tra bộ sưu tập 26 nhân vật Touhou đã sở hữu")
async def slash_collection(interaction: discord.Interaction):
    await handle_collection(interaction)

@bot.command(name="collection")
async def prefix_collection(ctx):
    await handle_collection(ctx)

# ==============================================================================
# HỆ THỐNG KHO MẢNH (SHARDS) & LỆNH /T TRANSLATE (QUY ĐỔI MẢNH SANG THẺ T)
# ==============================================================================
async def handle_translate_shard(ctx_or_interaction, loai_shard: str = "seiki"):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    shards_dict = player.setdefault("shards", {})

    shard_key = loai_shard.lower().strip() if loai_shard else "seiki"
    if shard_key in ["seiki", "t1", "dephap", "toannang"]:
        shard_key = "seiki"
        target_card_id = "t1"
        needed_shards = 10
    else:
        msg = f"❌ Loại mảnh `{loai_shard}` không tồn tại! Hiện tại Gensokyo có mảnh: `seiki` (đổi ra Thẻ T1 Seiki Đệ Pháp Toàn Năng)."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    cur_shards = shards_dict.get(shard_key, 0)
    card_info = CARDS_DATA[target_card_id]

    if cur_shards < needed_shards:
        msg = (
            f"❌ **Không đủ mảnh quy đổi!**\n"
            f"• Bạn đang có: **{cur_shards}/{needed_shards} Mảnh Seiki**\n"
            f"• Cần thêm: **{needed_shards - cur_shards} mảnh** nữa để quy đổi ra thẻ bài **[{card_info['rank']}] #{target_card_id} {card_info['name']}**!\n"
            f"💡 *Mẹo: Tham gia đánh Boss Raid (Seiki Dị Hình hoặc Reimu Dị Hình) để nhận tỉ lệ 2.5% rơi mảnh Seiki!*"
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Trừ 10 mảnh và cấp thẻ T1
    shards_dict[shard_key] -= needed_shards
    if target_card_id not in player.get("unlocked_cards", []):
        player.setdefault("unlocked_cards", []).append(target_card_id)
    player["inventory"][target_card_id] = player["inventory"].get(target_card_id, 0) + 1
    save_player(player)

    embed = discord.Embed(
        title="🔮 QUY ĐỔI MẢNH THÀNH CÔNG: TRIỆU HỒI SEIKI ĐỆ PHÁP TOÀN NĂNG!",
        description=(
            f"✨ **Chúc mừng {user.mention}!** Bạn đã dung hợp thành công **10 Mảnh Seiki**!\n\n"
            f"🎴 **THẺ BÀI ĐẶC BIỆT NHẬN ĐƯỢC:**\n"
            f"• **Tên:** **[{card_info['rank']}] #{target_card_id} {card_info['name']}**\n"
            f"• **Chỉ số:** ⚔️ Power: **{card_info['power']:,}** | ❤️ HP: **{card_info['hp']:,}**\n"
            f"• **Kỹ năng tối thượng:**\n"
            f"  - 🛡️ **Fantasy Seal (40%):** Miễn toàn bộ sát thương 1 lần trong trận.\n"
            f"  - 🌟 **Master Spark (30%):** Bộc phát ×1.5 sát thương 1 lần trong trận.\n"
            f"  - 💚 **Medicine Sign (20%):** Hồi phục 30% sinh lực cho bản thân 1 lần trong trận.\n"
            f"*(Tuân thủ nguyên tắc cân bằng: không bao giờ kích hoạt 2 chiêu cùng 1 hiệp)*\n\n"
            f"📦 **Kho mảnh còn lại:** `{shards_dict[shard_key]} Mảnh Seiki`\n"
            f"🎒 **Kho đồ hiện tại:** Đang sở hữu `{player['inventory'][target_card_id]} lá`!"
        ),
        color=0x7C3AED
    )
    embed.set_image(url=card_info["image"])
    embed.set_footer(text="Dùng /team add id_the:t1 để đưa Seiki vào đội hình chiến đấu!")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

async def handle_view_shards(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    shards_dict = player.get("shards", {})
    seiki_shards = shards_dict.get("seiki", 0)
    card_info = CARDS_DATA["t1"]
    has_card = player["inventory"].get("t1", 0)

    embed = discord.Embed(
        title=f"💎 KHO MẢNH NHÂN VẬT ĐẶC BIỆT - {user.display_name.upper()}",
        description=(
            f"🔮 **Mảnh Seiki Đệ Pháp Toàn Năng:**\n"
            f"• Hiện có: **`{seiki_shards}/10` mảnh**\n"
            f"• Tiến độ: `{get_hp_bar(min(10, seiki_shards), 10)}` ({seiki_shards * 10}%)\n"
            f"• Thẻ quy đổi: **[{card_info['rank']}] #t1 {card_info['name']}** (Kho: {has_card} lá)\n"
            f"• Thao tác: Gõ `/t translate` hoặc `/translate` khi đủ 10 mảnh để quy đổi ngay!\n"
            f"• Nguồn rơi: Tỉ lệ 2.5% rơi ngẫu nhiên khi tham gia diệt Boss Raid (Phase 1 & Phase 2)."
        ),
        color=0x8B5CF6
    )
    embed.set_thumbnail(url=card_info["image"])
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

class ShardGroup(app_commands.Group, name="t", description="Quản lý kho mảnh nhân vật đặc biệt (shards) & quy đổi"):
    @app_commands.command(name="translate", description="Quy đổi 10 mảnh đặc biệt (shards) sang thẻ bài chính thức (Seiki T1)")
    @app_commands.describe(loai_shard="Loại mảnh muốn quy đổi (mặc định: seiki)")
    @app_commands.choices(loai_shard=[
        app_commands.Choice(name="Mảnh Seiki Đệ Pháp Toàn Năng (Đổi ra Thẻ [T] #t1 Seiki)", value="seiki")
    ])
    async def slash_t_translate(self, interaction: discord.Interaction, loai_shard: str = "seiki"):
        await handle_translate_shard(interaction, loai_shard)

    @app_commands.command(name="shard", description="Kiểm tra số lượng mảnh đặc biệt hiện có trong kho")
    async def slash_t_shard(self, interaction: discord.Interaction):
        await handle_view_shards(interaction)

    @app_commands.command(name="shards", description="Kiểm tra số lượng mảnh đặc biệt hiện có trong kho")
    async def slash_t_shards(self, interaction: discord.Interaction):
        await handle_view_shards(interaction)

bot.tree.add_command(ShardGroup())

@bot.tree.command(name="translate", description="Quy đổi 10 mảnh đặc biệt (shards) sang thẻ bài chính thức (Seiki T1)")
@app_commands.describe(loai_shard="Loại mảnh muốn quy đổi (mặc định: seiki)")
async def slash_standalone_translate(interaction: discord.Interaction, loai_shard: str = "seiki"):
    await handle_translate_shard(interaction, loai_shard)

@bot.tree.command(name="shards", description="Xem kho mảnh nhân vật đặc biệt (Seiki shards)")
async def slash_standalone_shards(interaction: discord.Interaction):
    await handle_view_shards(interaction)

@bot.group(name="t", invoke_without_command=True)
async def prefix_t_group(ctx):
    await handle_view_shards(ctx)

@prefix_t_group.command(name="translate")
async def prefix_t_translate(ctx, loai_shard: str = "seiki"):
    await handle_translate_shard(ctx, loai_shard)

@prefix_t_group.command(name="shard", aliases=["shards"])
async def prefix_t_shard(ctx):
    await handle_view_shards(ctx)

@bot.command(name="translate")
async def prefix_standalone_translate(ctx, loai_shard: str = "seiki"):
    await handle_translate_shard(ctx, loai_shard)

@bot.command(name="shards", aliases=["shard"])
async def prefix_standalone_shards(ctx):
    await handle_view_shards(ctx)

# ==============================================================================
# HỆ THỐNG TUTORIAL TÂN THỦ & NHIỆM VỤ NGÀY (TIẾN TRÌNH TUYẾN TÍNH 1 CHIỀU)
# ==============================================================================
async def send_tutorial_intro(ctx_or_interaction, player):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    tut = player.setdefault("tutorial", {})
    tut["active"] = True
    tut["step"] = "pull"
    tut["quest_pulls_remaining"] = 3
    tut["completed"] = False
    save_player(player)

    embed = discord.Embed(
        title="🌸 KHÓA HUẤN LUYỆN TÂN THỦ - ĐỀN HAKUREI",
        description=(
            f"⛩️ **Reimu:** *\"Hm? Lại thêm 1 kẻ ngốc rơi vào đây nữa ư? Nghe này thế giới này không giống Gensokyo mà các người biết nên là nghe cho kĩ đây\"*\n\n"
            "🎁 **Cấp người chơi 3 lượt pull** *(chỉ dành cho quest này thôi, pull 100% không trùng lá và TUYỆT ĐỐI KHÔNG BAO GIỜ ra bậc SS)*\n\n"
            "👉 **Bước 1:** *\"Sử dụng lệnh `/pull` để tìm đồng đội cho mình\"*"
        ),
        color=0xF59E0B
    )
    embed.set_footer(text="Phần thưởng sau khi hoàn thành: 10 Lượt Pull • Dùng /pull để bắt đầu")
    if isinstance(ctx_or_interaction, discord.Interaction):
        if ctx_or_interaction.response.is_done():
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

async def handle_tutorial(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    tut = player.get("tutorial", {})

    if tut.get("completed"):
        embed = discord.Embed(
            title="⛩️ NHIỆM VỤ TÂN THỦ ĐÃ HOÀN THÀNH",
            description=f"🎉 **{user.display_name}** đã hoàn thành toàn bộ khóa huấn luyện tân thủ và nhận thưởng 10 vé pull rồi!\nHãy dùng `/quest` để làm 3/3 Nhiệm Vụ Hàng Ngày nhé!",
            color=0x10B981
        )
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else: await ctx_or_interaction.send(embed=embed)
        return

    # NẾU ĐÃ PULL 3 LÁ RỒI THÌ TUYỆT ĐỐI KHÔNG RESET BƯỚC PULL NỮA!
    if tut.get("pull_used", False):
        curr_step = tut.get("step", "collection")
        step_hints = {
            "collection": "Bạn đã nhận 3 lá tân thủ rồi! Hãy dùng `/collection` để xem bài.",
            "team": f"Bạn đã mở khóa bộ sưu tập! Hãy dùng `/team add <id>` để xếp đủ 3 thẻ (Hiện có {len(player.get('team', []))}/3 thẻ).",
            "battle": "Đội hình đã sẵn sàng! Hãy dùng `/battle` tham gia trận chiến đầu tiên để hoàn tất nhiệm vụ và nhận 10 Vé Pull!"
        }
        hint = step_hints.get(curr_step, "Hãy tiếp tục hoàn tất nhiệm vụ tân thủ!")
        embed = discord.Embed(
            title="🌸 TIẾN TRÌNH NHIỆM VỤ TÂN THỦ (TIẾN TRÌNH 1 CHIỀU)",
            description=f"⚠️ **Bạn đang thực hiện nhiệm vụ dở dang:**\n{hint}\n\n*(Không thể reset lượt pull 3 lá khởi đầu)*",
            color=0xF59E0B
        )
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else: await ctx_or_interaction.send(embed=embed)
        return

    await send_tutorial_intro(ctx_or_interaction, player)

@bot.tree.command(name="tutorial", description="Mở khóa huấn luyện tân thủ đền Hakurei (Phần thưởng: 10 Lượt Pull)")
async def slash_tutorial(interaction: discord.Interaction):
    await handle_tutorial(interaction)

@bot.command(name="tutorial", aliases=["huongdan", "tanthu"])
async def prefix_tutorial(ctx):
    await handle_tutorial(ctx)

async def handle_quest(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    dq = ensure_daily_quests(player)
    save_player(player)

    today_str = dq.get("date", get_today_vn())
    completed_count = sum(1 for q in dq.get("quests", []) if q.get("completed"))
    time_until_reset = format_time_until_midnight_vn()

    embed = discord.Embed(
        title=f"📜 NHIỆM VỤ HÀNG NGÀY ({completed_count}/3 HOÀN THÀNH)",
        description=(
            f"📅 **Hôm nay:** `{today_str}` *(Giờ Việt Nam - GMT+7)*\n"
            f"⏱️ **Tự động làm mới sau:** `{time_until_reset}` *(vào đúng 00:00 nửa đêm)*\n\n"
            f"⛩️ Hoàn thành cả 3 nhiệm vụ ngày để nhận đại tiệc **10 Lượt Pull** từ Reimu!"
        ),
        color=0xF59E0B if completed_count < 3 else 0x10B981
    )

    for q in dq.get("quests", []):
        progress = min(q["current"], q["target"])
        pct = progress / q["target"] if q["target"] > 0 else 1.0
        filled = int(pct * 8)
        bar = "▰" * filled + "▱" * (8 - filled)
        status = "✅ **ĐÃ XONG** (Đã nhận vé)" if q.get("claimed") else ("🎯 Đang thực hiện" if progress > 0 else "⏳ Chưa bắt đầu")
        embed.add_field(
            name=f"Nhiệm vụ #{q['id']}: {q['name']}",
            value=f"• Tiến độ: `[{bar}]` **{progress}/{q['target']}**\n• Thưởng: **+{q['reward']} Vé Pull** 🎟️\n• Trạng thái: {status}",
            inline=False
        )

    all_done = dq.get("all_completed_claimed", False)
    all_bonus_status = "✅ ĐÃ NHẬN THƯỞNG 10 VÉ!" if all_done else ("🎁 SẴN SÀNG NHẬN!" if completed_count >= 3 else f"🔒 Hoàn thành thêm {3 - completed_count} nhiệm vụ để mở khóa")
    embed.add_field(
        name="👑 QUÀ ĐẶC BIỆT HOÀN THÀNH 3/3 NHIỆM VỤ:",
        value=f"⛩️ **Reimu:** *\"10 lượt pull đây, lo mà sử dụng cẩn thận\"*\n• Phần thưởng: **+10 Lượt Pull Tích Lũy** 🎟️\n• Trạng thái: **{all_bonus_status}**",
        inline=False
    )
    embed.set_footer(text=f"Vé pull: {player.get('pull_tickets', 0):.2f} • Tự động reset vào 00:00 hàng ngày (GMT+7)")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="quest", description="Xem danh sách 3/3 Nhiệm vụ Hàng Ngày và phần thưởng 10 lượt pull")
async def slash_quest(interaction: discord.Interaction):
    await handle_quest(interaction)

@bot.command(name="quest", aliases=["quests", "dailyquest"])
async def prefix_quest(ctx):
    await handle_quest(ctx)
# ==============================================================================
# TÍNH NĂNG CHECK NHÂN VẬT & SOI KỸ NĂNG (TOÀN BỘ 26 NHÂN VẬT + ACE 2)
# ==============================================================================
class CharacterCheckView(discord.ui.View):
    def __init__(self, current_index: int = 0, user_id: int = None, show_ace: bool = False, show_t1: bool = False):
        super().__init__(timeout=180)
        self.current_index = max(0, min(current_index, len(CARDS_DATA) - 1))
        self.user_id = user_id
        self.show_ace = show_ace
        self.show_t1 = show_t1
        self.rebuild_items()

    def rebuild_items(self):
        self.clear_items()
        cid = self.current_index + 1
        has_ace = cid in (9, 13, 16, 17)

        first_btn = discord.ui.Button(label="⏮️", style=discord.ButtonStyle.secondary, row=0)
        first_btn.callback = self.first_page
        self.add_item(first_btn)

        prev_btn = discord.ui.Button(label="◀ Trước", style=discord.ButtonStyle.primary, row=0)
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)

        counter_btn = discord.ui.Button(label=f"#{cid:02d} / 26", style=discord.ButtonStyle.secondary, disabled=True, row=0)
        self.add_item(counter_btn)

        next_btn = discord.ui.Button(label="Sau ▶", style=discord.ButtonStyle.primary, row=0)
        next_btn.callback = self.next_page
        self.add_item(next_btn)

        last_btn = discord.ui.Button(label="⏭️", style=discord.ButtonStyle.secondary, row=0)
        last_btn.callback = self.last_page
        self.add_item(last_btn)

        if has_ace:
            if self.show_ace:
                ace_toggle = discord.ui.Button(label="⭐ Xem Bản Thường", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
            else:
                ace_toggle = discord.ui.Button(label="🌟 Xem Bản Ace 2 ⭐⭐", style=discord.ButtonStyle.success, emoji="✨", row=1)
            ace_toggle.callback = self.toggle_ace
            self.add_item(ace_toggle)
        else:
            no_ace_btn = discord.ui.Button(label="⭐ Nhân Vật Bản Chuẩn", style=discord.ButtonStyle.secondary, disabled=True, row=1)
            self.add_item(no_ace_btn)

        t1_btn = discord.ui.Button(
            label="🔮 [T] #t1 Seiki Đệ Pháp Toàn Năng",
            style=discord.ButtonStyle.success if self.show_t1 else discord.ButtonStyle.secondary,
            emoji="🔮",
            row=1
        )
        t1_btn.callback = self.show_t1_card
        self.add_item(t1_btn)

        opt_part1 = []
        for i in range(1, 14):
            c = CARDS_DATA[i]
            star = " ⭐⭐" if i in (9, 13, 16, 17) else ""
            opt_part1.append(discord.SelectOption(
                label=f"#{c['id']:02d} [{c['rank']}] {c['name']}{star}"[:100],
                value=str(i),
                description=f"ATK {c['power']:,} | HP {c['hp']:,} • Rank {c['rank']}"[:100],
                default=(i == cid)
            ))
        select1 = discord.ui.Select(
            placeholder="🔽 Chọn nhanh #01 - #13 (Hecatia ➔ Reimu)...",
            options=opt_part1,
            row=2
        )
        select1.callback = self.select_callback
        self.add_item(select1)

        opt_part2 = []
        for i in range(14, 27):
            c = CARDS_DATA[i]
            star = " ⭐⭐" if i in (9, 13, 16, 17) else ""
            opt_part2.append(discord.SelectOption(
                label=f"#{c['id']:02d} [{c['rank']}] {c['name']}{star}"[:100],
                value=str(i),
                description=f"ATK {c['power']:,} | HP {c['hp']:,} • Rank {c['rank']}"[:100],
                default=(i == cid)
            ))
        select2 = discord.ui.Select(
            placeholder="🔽 Chọn nhanh #14 - #26 (Mokou ➔ Tewi)...",
            options=opt_part2,
            row=3
        )
        select2.callback = self.select_callback
        self.add_item(select2)

    def get_current_embed(self) -> discord.Embed:
        if self.show_t1:
            return self.get_t1_embed()
        cid = self.current_index + 1
        card = CARDS_DATA[cid]
        details = CHARACTER_DETAILS.get(cid, {})
        has_ace = cid in (9, 13, 16, 17)
        is_ace_mode = self.show_ace and has_ace

        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get(str(cid), 0) if player else 0
        is_user_ace = is_card_ace2(player, cid) if player else False
        is_locked = is_card_locked(player, cid) if player else False

        rank_colors = {
            "SS": 0xF59E0B,
            "S": 0x8B5CF6,
            "A": 0x3B82F6,
            "B": 0x10B981,
            "C": 0x6B7280
        }

        if is_ace_mode:
            cfg = EVOL_CONFIG[cid]
            color = 0xEF4444
            title = f"🌟 [Ace 2 ⭐⭐] #{cid:02d} {card['name']} (Thức Tỉnh)"
            power_val = card["power"] + 300
            hp_val = card["hp"] + 300
            skill_name = cfg["skill_name"]
            skill_desc = cfg["skill_desc"]
            img_url = cfg["evol_gif"]
            mode_desc = "🔥 **Đang xem trạng thái: THỨC TỈNH ACE 2 ⭐⭐**\n*(Được cường hóa +300 Sức Mạnh & +300 Máu, khai mở tuyệt kỹ tối thượng!)*"
        else:
            color = rank_colors.get(card["rank"], 0x3B82F6)
            title = f"🎴 [#{cid:02d}] {card['name']} • Rank [{card['rank']}]"
            power_val = card["power"]
            hp_val = card["hp"]
            skill_name = details.get("skill_name", "Ma Pháp Tấn Công")
            skill_desc = details.get("skill_desc", "Năng lực đặc trưng của nhân vật trong thế giới Gensokyo.")
            img_url = card["image"]
            mode_desc = f"*{details.get('title', 'Nhân Vật Touhou Project')}*"
            if has_ace:
                mode_desc += "\n✨ **Nhân vật này có thể tiến hóa Ace 2 ⭐⭐!** *(Bấm nút 'Xem Bản Ace 2' bên dưới)*"

        if is_locked:
            mode_desc += "\n🔒 **CẢNH BÁO: Thẻ này hiện đang bị ADMIN KHÓA!** Cần quay `/pull` ra lại để mở."

        embed = discord.Embed(
            title=title,
            description=mode_desc,
            color=color
        )
        embed.set_image(url=img_url)

        atk_team = power_val + lvl_atk_buff
        hp_team = hp_val + lvl_hp_buff
        stats_text = (
            f"• ⚔️ **Sức Mạnh (Power / ATK):** `{power_val:,}`\n"
            f"• ❤️ **Máu (HP):** `{hp_val:,}`\n"
            f"• 🛡️ **Trong Đội Hình (Cấp {user_level}):** `{atk_team:,}` ATK | `{hp_team:,}` HP\n"
            f"*(Mỗi cấp người chơi tăng +20 ATK và +25 HP)*"
        )
        if is_ace_mode:
            stats_text += "\n⭐ **Đặc quyền Ace 2:** `+300 ATK & +300 HP` cộng trực tiếp vĩnh viễn!"
        embed.add_field(name="⚔️ SỨC MẠNH & CHỈ SỐ:", value=stats_text, inline=False)

        embed.add_field(
            name=f"🔮 KỸ NĂNG & NĂNG LỰC: {skill_name}",
            value=f"{skill_desc}",
            inline=False
        )

        if player:
            if is_locked:
                ace_badge = "🔒 [BỊ ADMIN KHÓA]"
            elif is_user_ace:
                ace_badge = "🌟 ĐÃ THỨC TỈNH ACE 2 ⭐⭐"
            elif has_ace:
                req = EVOL_CONFIG[cid]["required_cards"]
                if owned_cnt >= req:
                    ace_badge = f"🟢 Đủ điều kiện ({owned_cnt}/{req} thẻ) - Dùng `/evol`!"
                else:
                    ace_badge = f"🔴 Chưa đủ ({owned_cnt}/{req} thẻ) - Cần thêm {req - owned_cnt} thẻ"
            else:
                ace_badge = "Chưa có dạng thức tỉnh"

            embed.add_field(
                name="🎒 TÚI ĐỒ CỦA BẠN:",
                value=f"• Sở hữu: **{owned_cnt}** lá\n• Cảnh giới: **{ace_badge}**",
                inline=True
            )

        embed.add_field(
            name="📊 HẠNG THẺ:",
            value=f"• Thứ tự: **#{cid:02d} / 26**\n• Phẩm cấp: **Rank [{card['rank']}]**",
            inline=True
        )

        embed.set_footer(
            text=f"Trang {self.current_index + 1}/26 • Bấm ◀ / ▶ hoặc dùng Menu chọn nhanh nhân vật!"
        )
        return embed

    async def show_t1_card(self, interaction: discord.Interaction):
        self.show_t1 = True
        self.show_ace = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    def get_t1_embed(self) -> discord.Embed:
        """Embed chi tiết thẻ đặc biệt [T] #t1 Seiki Đệ Pháp Toàn Năng: đầy đủ chỉ số, 3 tuyệt kỹ + GIF."""
        card = CARDS_DATA["t1"]
        details = CHARACTER_DETAILS["t1"]
        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get("t1", 0) if player else 0
        shards_cnt = player.get("shards", {}).get("seiki", 0) if player else 0
        is_locked = is_card_locked(player, "t1") if player else False

        embed = discord.Embed(
            title="🔮 [THẺ ĐẶC BIỆT NHÓM T] #t1 SEIKI ĐỆ PHÁP TOÀN NĂNG",
            description=(
                f"*{details['title']}*\n"
                "✨ Thẻ bài thần thoại chỉ có thể nhận bằng cách thu thập **10 Mảnh Seiki** "
                "(tỉ lệ rơi 2.5% từ Boss Raid) rồi dùng lệnh `/t translate`."
            ),
            color=0x7C3AED
        )
        embed.set_image(url=card["image"])

        stats_text = (
            f"• ⚔️ **Sức Mạnh (Power / ATK):** `{card['power']:,}`\n"
            f"• ❤️ **Máu (HP):** `{card['hp']:,}`\n"
            f"• 🛡️ **Trong Đội Hình (Cấp {user_level}):** `{card['power'] + lvl_atk_buff:,}` ATK | `{card['hp'] + lvl_hp_buff:,}` HP\n"
            f"*(Mỗi cấp ngườichơi tăng +20 ATK và +25 HP)*"
        )
        embed.add_field(name="⚔️ SỨC MẠNH & CHỈ SỐ:", value=stats_text, inline=False)

        sk = card["skills"]
        skills_text = (
            f"1️⃣ **{sk['fantasy_seal']['name']}** — {sk['fantasy_seal']['desc']}\n"
            f"   🎬 Hoạt ảnh: {sk['fantasy_seal']['gif']}\n"
            f"2️⃣ **{sk['master_spark']['name']}** — {sk['master_spark']['desc']}\n"
            f"   🎬 Hoạt ảnh: {sk['master_spark']['gif']}\n"
            f"3️⃣ **{sk['medicine_sign']['name']}** — {sk['medicine_sign']['desc']}\n"
            f"   🎬 Hoạt ảnh: {sk['medicine_sign']['gif']}\n"
            "⚖️ *Nguyên tắc cân bằng: tối đa 1 chiêu mỗi lượt, mỗi chiêu kích hoạt 1 lần trong trận. "
            "Hỗ trợ đầy đủ trong Raid Boss, Battle & PvP!*"
        )
        embed.add_field(name="🔮 TAM ĐẠI TUYỆT KỸ:", value=skills_text, inline=False)

        if player:
            lock_str = "\n🔒 **CẢNH BÁO: Thẻ này hiện đang bị ADMIN KHÓA!** Cần quay `/pull` ra lại để mở." if is_locked else ""
            shard_str = "\n✨ *Đã đủ 10 mảnh! Dùng `/t translate` để đổi thẻ ngay!*" if shards_cnt >= 10 else ""
            embed.add_field(
                name="🎒 TÚI ĐỒ CỦA BẠN:",
                value=f"• Sở hữu: **{owned_cnt}** lá{lock_str}\n• 💎 Mảnh Seiki: **{shards_cnt}/10**{shard_str}",
                inline=True
            )
        embed.add_field(
            name="📊 HẠNG THẺ:",
            value="• Phẩm cấp: **Rank [T] — Đặc Biệt**\n• Nguồn: Đổi từ **10 Mảnh Seiki** (Boss Raid)",
            inline=True
        )
        embed.set_footer(text="Thẻ nhóm T đặc biệt • Bấm ◀ / ▶ hoặc menu để xem 26 nhân vật chuẩn!")
        return embed

    async def first_page(self, interaction: discord.Interaction):
        self.current_index = 0
        self.show_ace = False
        self.show_t1 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def prev_page(self, interaction: discord.Interaction):
        self.current_index = (self.current_index - 1) % len(CARDS_DATA)
        self.show_ace = False
        self.show_t1 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_index = (self.current_index + 1) % len(CARDS_DATA)
        self.show_ace = False
        self.show_t1 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def last_page(self, interaction: discord.Interaction):
        self.current_index = len(CARDS_DATA) - 1
        self.show_ace = False
        self.show_t1 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def toggle_ace(self, interaction: discord.Interaction):
        self.show_ace = not self.show_ace
        self.show_t1 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def select_callback(self, interaction: discord.Interaction):
        selected_id = int(interaction.data["values"][0])
        self.current_index = selected_id - 1
        self.show_ace = False
        self.show_t1 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

async def handle_check_character(ctx_or_interaction, nhan_vat: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    
    target_idx = 0
    if nhan_vat:
        nv_clean = nhan_vat.strip().lower()
        if nv_clean in ("t1", "seiki", "dephap", "toannang"):
            view_t1 = CharacterCheckView(current_index=0, user_id=user.id, show_ace=False, show_t1=True)
            embed_t1 = view_t1.get_current_embed()
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed_t1, view=view_t1)
            else:
                await ctx_or_interaction.send(embed=embed_t1, view=view_t1)
            return
        if nv_clean.isdigit():
            val = int(nv_clean)
            if 1 <= val <= len(CARDS_DATA):
                target_idx = val - 1
        else:
            found = False
            for cid, c in CARDS_DATA.items():
                if nv_clean in c["name"].lower():
                    target_idx = cid - 1
                    found = True
                    break
            if not found:
                for cid, det in CHARACTER_DETAILS.items():
                    if nv_clean in det.get("title", "").lower() or nv_clean in det.get("skill_name", "").lower():
                        target_idx = cid - 1
                        break
    else:
        player = get_player(user.id, user.display_name)
        if player and player.get("team"):
            lead_id = player["team"][0]
            if 1 <= lead_id <= len(CARDS_DATA):
                target_idx = lead_id - 1

    view = CharacterCheckView(current_index=target_idx, user_id=user.id, show_ace=False)
    embed = view.get_current_embed()

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="check", description="Kiểm tra thông số sức mạnh, máu và kỹ năng của 26 nhân vật Touhou (kèm Ace 2)")
@app_commands.describe(nhan_vat="Nhập số ID (1-26) hoặc tên nhân vật muốn xem ngay (để trống để duyệt từ đầu)")
async def slash_check(interaction: discord.Interaction, nhan_vat: str = None):
    await handle_check_character(interaction, nhan_vat)

@bot.tree.command(name="card_info", description="Xem chi tiết sức mạnh, máu và chiêu thức thẻ bài Touhou (kèm Ace 2)")
@app_commands.describe(nhan_vat="Nhập số ID (1-26) hoặc tên nhân vật muốn xem ngay")
async def slash_card_info(interaction: discord.Interaction, nhan_vat: str = None):
    await handle_check_character(interaction, nhan_vat)

@bot.command(name="check", aliases=["char", "character", "card", "cardinfo"])
async def prefix_check(ctx, *, nhan_vat: str = None):
    await handle_check_character(ctx, nhan_vat)

# ==============================================================================
# HỆ THỐNG PVE BATTLE (ĐẤU THEO LƯỢT NPC GENSOKYO)
# ==============================================================================
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

    if player.get("_is_first_time") and not player.get("tutorial", {}).get("completed"):
        player["_is_first_time"] = False
        await send_tutorial_intro(ctx_or_interaction, player)
        return

    # Lọc bỏ thẻ bị Admin lock khỏi đội hình nếu có
    player["team"] = [cid for cid in player.get("team", []) if cid in CARDS_DATA and not is_card_locked(player, cid)]

    if not player.get("team"):
        msg = "⚠️ Đội hình của bạn đang trống hoặc các thẻ đang bị khóa! Dùng `/team add id_the:<ID>` để xếp thẻ."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    now = time.time()
    if now - player.get("last_battle_time", 0) < 60:
        rem = int(60 - (now - player.get("last_battle_time", 0)))
        msg = f"⏳ Bạn vừa chiến đấu kịch liệt, cần nghỉ ngơi thêm **{rem}s**!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    npc = random.choice(GENSOKYO_NPCS)
    opp_name = f"{npc['badge']} {npc['name']}"
    opp_level = max(1, min(MAX_LEVEL, player["level"] + random.choice([-1, 0, 1, 2])))
    opp_team_ids = npc.get("preferred", [17, 18, 20])

    p_buff_pwr = get_level_atk_buff(player["level"])
    p_buff_hp = get_level_hp_buff(player["level"])
    o_buff_pwr = get_level_atk_buff(opp_level)
    o_buff_hp = get_level_hp_buff(opp_level)

    player_cards = []
    for cid in player["team"][:3]:
        c = CARDS_DATA.get(cid)
        if c:
            is_ace = is_card_ace2(player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            cname = f"[Ace 2] {format_card_id(c['id'])} {c['name']}" if is_ace else f"{format_card_id(c['id'])} {c['name']}"
            player_cards.append({
                "cid": cid, "name": cname, "raw_name": c["name"], "rank": c.get("rank", "A"),
                "power": c["power"] + p_buff_pwr + ace_pwr,
                "hp": c["hp"] + p_buff_hp + ace_hp, "current_hp": c["hp"] + p_buff_hp + ace_hp,
                "is_ace2": is_ace, "base_power": c["power"], "base_hp": c["hp"],
                "image": c.get("image", "")
            })

    ace_supported_cids = list({int(k) for k in EVOL_CONFIG.keys() if str(k).isdigit() and int(k) in CARDS_DATA})
    npc_has_ace = (random.random() < 0.25) and len(ace_supported_cids) > 0
    npc_ace_idx = -1

    final_opp_team_ids = list(opp_team_ids[:3])

    if npc_has_ace:
        existing_ace_eligible = [i for i, cid in enumerate(final_opp_team_ids) if cid in ace_supported_cids]
        if existing_ace_eligible:
            npc_ace_idx = random.choice(existing_ace_eligible)
        else:
            replace_idx = random.randint(0, len(final_opp_team_ids) - 1)
            chosen_ace_cid = random.choice(ace_supported_cids)
            final_opp_team_ids[replace_idx] = chosen_ace_cid
            npc_ace_idx = replace_idx

    opp_cards = []
    for idx, cid in enumerate(final_opp_team_ids):
        c = CARDS_DATA.get(cid)
        if c:
            is_o_ace = (idx == npc_ace_idx)
            o_ace_pwr = ACE_POWER_BUFF if is_o_ace else 0
            o_ace_hp = ACE_HP_BUFF if is_o_ace else 0
            o_name = f"[Ace 2 ⭐⭐] #{c['id']:02d} {c['name']}" if is_o_ace else f"#{c['id']:02d} {c['name']}"
            opp_cards.append({
                "cid": cid, "name": o_name, "raw_name": c["name"],
                "rank": c.get("rank", "A"),
                "power": c["power"] + o_buff_pwr + o_ace_pwr,
                "hp": c["hp"] + o_buff_hp + o_ace_hp,
                "current_hp": c["hp"] + o_buff_hp + o_ace_hp,
                "is_ace2": is_o_ace,
                "base_power": c["power"], "base_hp": c["hp"],
                "skill": c.get("skill", "Tấn công Danmaku cơ bản"),
                "image": c.get("image", "")
            })

    p_idx, o_idx, r_cnt = 0, 0, 0
    p_sakuya, p_reimu, p_marisa = False, False, False
    p_flandre = False
    o_sakuya, o_reimu, o_marisa = False, False, False
    # Cờ tuyệt kỹ thẻ [T] #t1 Seiki (Battle): mỗi chiêu 1 lần/trận, tối đa 1 chiêu/lượt
    p_seiki_seal, p_seiki_spark, p_seiki_heal = False, False, False
    p_seiki_used_turn = -1
    battle_logs = []
    battle_turns = []

    while p_idx < len(player_cards) and o_idx < len(opp_cards) and r_cnt < 30:
        r_cnt += 1
        pc = player_cards[p_idx]
        oc = opp_cards[o_idx]
        turn_image = None
        turn_actions = []
        turn_trades = []
        stunned_pc = False
        stunned_oc = False

        if pc["cid"] == 16 and pc["is_ace2"] and not p_sakuya:
            if random.random() < 0.40:
                p_sakuya = True
                stunned_oc = True
                turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#16] Sakuya** kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ {oc['name']} bị STUN mất lượt!"
                battle_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if oc["cid"] == 16 and oc.get("is_ace2") and not o_sakuya:
            if random.random() < 0.30:
                o_sakuya = True
                stunned_pc = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **Đối thủ [Ace 2] [#16] Sakuya** kích hoạt **Thời Gian Đóng Băng** (30%)! ❄️ {pc['name']} bị STUN mất lượt!"
                battle_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        curr_pc_power = pc["power"]
        if pc["cid"] == 17 and pc["is_ace2"] and not p_marisa:
            if random.random() < 0.30:
                p_marisa = True
                curr_pc_power = int(curr_pc_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[17]["skill_gif"]
                msg_m = f"🌟 **[Ace 2] [#17] Marisa** tung ra **Master Spark** (30%)! Bộc phá ×2.0 sát thương gây **{curr_pc_power:,} DMG**!"
                battle_logs.append(msg_m)
                turn_actions.append(msg_m)

        # ===== ACE 2 FLANDRE - RIPPLES OF 495 YEARS (25%: XÓA 50% HP ĐỐI THỦ, 1 LẦN/TRẬN) =====
        if pc["cid"] == 9 and pc["is_ace2"] and not p_flandre:
            if random.random() < 0.25:
                p_flandre = True
                rip_dmg = int(oc["current_hp"] * 0.50)
                oc["current_hp"] = max(0, oc["current_hp"] - rip_dmg)
                if not turn_image:
                    turn_image = EVOL_CONFIG[9]["skill_gif"]
                msg_r = f"🦇 **[Ace 2] [#09] Flandre** kích hoạt **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} HP (50% HP đối thủ)** ngay lập tức!"
                battle_logs.append(msg_r)
                turn_actions.append(msg_r)

        # ===== TUYỆT KỸ THẺ [T] #t1 SEIKI - TẤN CÔNG (Master Spark 30% x1.5 / Medicine Sign 20% hồi phục) =====
        if str(pc["cid"]).lower() == "t1" and p_seiki_used_turn != r_cnt:
            roll_t1 = random.random()
            if not p_seiki_spark and roll_t1 < 0.30:
                p_seiki_spark = True
                p_seiki_used_turn = r_cnt
                curr_pc_power = int(curr_pc_power * 1.5)
                if not turn_image:
                    turn_image = T1_SPARK_GIF
                msg_m = f"🌟 **[Nhóm T] [#t1] Seiki** ({user.display_name}) tung **Master Spark** (30%)! Bộc phá ×1.5 sát thương ({curr_pc_power:,} DMG)!"
                battle_logs.append(msg_m)
                turn_actions.append(msg_m)
            elif not p_seiki_heal and pc["current_hp"] < pc["hp"] and roll_t1 < 0.50:
                p_seiki_heal = True
                p_seiki_used_turn = r_cnt
                heal_val = int(pc["hp"] * 0.30)
                pc["current_hp"] = min(pc["hp"], pc["current_hp"] + heal_val)
                if not turn_image:
                    turn_image = T1_HEAL_GIF
                msg_h = f"💚 **[Nhóm T] [#t1] Seiki** ({user.display_name}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_val:,} HP**! ({pc['current_hp']:,}/{pc['hp']:,} HP)"
                battle_logs.append(msg_h)
                turn_actions.append(msg_h)

        curr_oc_power = oc["power"]
        if oc["cid"] == 17 and oc.get("is_ace2") and not o_marisa:
            if random.random() < 0.25:
                o_marisa = True
                curr_oc_power = int(curr_oc_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[17]["skill_gif"]
                msg_m = f"🌟 **Đối thủ [Ace 2] [#17] Marisa** tung ra **Master Spark** (25%)! Bộc phá ×1.5 sát thương gây **{curr_oc_power:,} DMG**!"
                battle_logs.append(msg_m)
                turn_actions.append(msg_m)

        if not stunned_pc:
            oc_invul = False
            if oc["cid"] == 13 and oc.get("is_ace2") and not o_reimu:
                if random.random() < 0.30:
                    o_reimu = True
                    oc_invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    msg_skill = f"🛡️ **Đối thủ [Ace 2] [#13] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh** (30%)! MIỄN TOÀN BỘ THƯƠNG TỔN!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)

            if not oc_invul:
                oc["current_hp"] -= curr_pc_power
                turn_actions.append(f"⚔️ **{pc['name']}** tấn công gây **{curr_pc_power:,} DMG** lên **{oc['name']}**!")
            else:
                turn_actions.append(f"🛡️ **{oc['name']}** né tránh hoàn toàn đòn đánh của **{pc['name']}**!")
        else:
            turn_actions.append(f"❄️ **{pc['name']}** bị đóng băng nên không thể ra đòn!")

        if not stunned_oc:
            pc_invul = False
            if pc["cid"] == 13 and pc["is_ace2"] and not p_reimu:
                if random.random() < 0.40:
                    p_reimu = True
                    pc_invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    msg_skill = f"🛡️ **[Ace 2] [#13] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN TOÀN BỘ THƯƠNG TỔN!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)
            if not pc_invul and str(pc["cid"]).lower() == "t1" and not p_seiki_seal and p_seiki_used_turn != r_cnt:
                if random.random() < 0.40:
                    p_seiki_seal = True
                    p_seiki_used_turn = r_cnt
                    pc_invul = True
                    if not turn_image:
                        turn_image = T1_SEAL_GIF
                    msg_skill = f"🛡️ **[Nhóm T] [#t1] Seiki** ({user.display_name}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)
            if not pc_invul:
                pc["current_hp"] -= curr_oc_power
                turn_actions.append(f"⚔️ **{oc['name']}** phản công gây **{curr_oc_power:,} DMG** lên **{pc['name']}**!")
            else:
                turn_actions.append(f"🛡️ **{pc['name']}** miễn nhiễm toàn bộ đòn đánh của **{oc['name']}**!")
        else:
            turn_actions.append(f"❄️ **{oc['name']}** bị đóng băng nên không thể phản công!")

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
    if win:
        gained_xp = random.randint(100, 200)
    else:
        gained_xp = random.randint(30, 50)

    old_lvl = player["level"]
    player["last_battle_time"] = now
    player["xp"] += gained_xp
    player["battles_total"] = player.get("battles_total", 0) + 1
    if win: player["battles_won"] = player.get("battles_won", 0) + 1

    dq_notifs = update_daily_quest_progress(player, "battle", 1)

    tut = player.get("tutorial", {})
    tut_completed = False
    if tut.get("active") and tut.get("step") == "battle":
        tut["active"] = False
        tut["step"] = "completed"
        tut["completed"] = True
        player["pull_tickets"] += 10.0
        tut_completed = True

    save_player(player)

    new_lvl = player["level"]
    lvl_up_str = f"\n🎉 **LÊN CẤP {new_lvl}!** (+20 ATK & +25 HP buff)" if new_lvl > old_lvl else ""
    embed = discord.Embed(title=f"⚔️ BATTLE ({r_cnt} HIỆP): {user.display_name} VS {opp_name}", color=0x10B981 if win else 0xEF4444)

    your_team_lines = [
        f"• {'⭐ ' if pc.get('is_ace2') else ''}**{pc['name']}** `[{pc.get('rank', 'A')}]` ⚔️ `{pc['power']:,}` | ❤️ `{pc['hp']:,}`"
        for pc in player_cards
    ]
    embed.add_field(name=f"🔴 Đội Hình Của Bạn (Lv.{player['level']}):", value="\n".join(your_team_lines) if your_team_lines else "Trống", inline=False)

    opp_team_lines = [
        f"• {'⭐ ' if oc.get('is_ace2') else ''}**{format_card_id(oc['cid'])} {oc['raw_name']}** `[{oc['rank']}]`{' `[Ace 2 ⭐]`' if oc.get('is_ace2') else ''} ⚔️ `{oc['power']:,}` | ❤️ `{oc['hp']:,}`"
        for oc in opp_cards
    ]
    embed.add_field(name=f"🔵 Toàn Bộ Đội Hình Đối Thủ: {opp_name} (Lv.{opp_level}):", value="\n".join(opp_team_lines) if opp_team_lines else "Trống", inline=False)

    if battle_logs: embed.add_field(name="📜 Diễn Biến Nổi Bật:", value="\n".join(battle_logs[:5]), inline=False)
    cur_lvl, xp_in_lvl, needed_xp, _ = get_level_progress(player["xp"])
    embed.add_field(
        name="Kết Quả:",
        value=f"{'🏆 **CHIẾN THẮNG!**' if win else '💀 **THẤT BẠI!**'}\nNhận: **+{gained_xp} XP** ({'Thắng +100-200 XP' if win else 'Thua +30-50 XP'} | Tổng: {player['xp']:,} XP | Cấp: Lv.{cur_lvl}: {xp_in_lvl}/{needed_xp} XP){lvl_up_str}",
        inline=False
    )
    if tut_completed:
        embed.add_field(
            name="🎉 HOÀN THÀNH NHIỆM VỤ TÂN THỦ!",
            value=f"🔔 {user.mention} ⛩️ **Reimu:** *\"Hoàn thành nhiệm vụ tân thủ, nhận thưởng 10 lượt pull\"* 🎟️ (+10 Vé Pull đã được cộng vào tài khoản!)",
            inline=False
        )
    if dq_notifs:
        embed.add_field(name="📜 Tiến Trình Nhiệm Vụ Ngày:", value="\n\n".join(dq_notifs), inline=False)
    embed.set_footer(text="Hồi chiêu lệnh: 1 phút • Bấm 'Soi Toàn Bộ Đội Hình Đối Thủ' để xem chi tiết thẻ và kỹ năng đối phương")
    details_view = OpenDetailsView(battle_turns, opp_cards=opp_cards, opp_name=opp_name, opp_level=opp_level)
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed, view=details_view)
    else: await ctx_or_interaction.send(embed=embed, view=details_view)

@bot.tree.command(name="battle", description="Giao đấu theo lượt: Thắng nhận 100-200 XP, Thua nhận 30-50 XP")
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
        asyncio.create_task(run_pvp_match(interaction.channel, self.challenger, self.target, self.c_team, self.t_team, interaction=interaction, msg=self.msg))

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

async def run_pvp_match(channel, challenger, target, c_team_cids, t_team_cids, interaction: discord.Interaction = None, msg: discord.Message = None):
    c_player = get_player(challenger.id, challenger.display_name)
    t_player = get_player(target.id, target.display_name)

    c_buff_pwr = get_level_atk_buff(c_player["level"])
    c_buff_hp = get_level_hp_buff(c_player["level"])
    t_buff_pwr = get_level_atk_buff(t_player["level"])
    t_buff_hp = get_level_hp_buff(t_player["level"])

    c_cards = []
    for cid in c_team_cids[:3]:
        c = CARDS_DATA.get(cid)
        if c:
            is_ace = is_card_ace2(c_player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            cname = f"[Ace 2 ⭐⭐] {format_card_id(c['id'])} {c['name']}" if is_ace else f"{format_card_id(c['id'])} {c['name']}"
            c_cards.append({
                "cid": cid, "name": cname, "power": c["power"] + c_buff_pwr + ace_pwr,
                "hp": c["hp"] + c_buff_hp + ace_hp, "current_hp": c["hp"] + c_buff_hp + ace_hp,
                "max_hp": c["hp"] + c_buff_hp + ace_hp, "is_ace2": is_ace
            })

    t_cards = []
    for cid in t_team_cids[:3]:
        c = CARDS_DATA.get(cid)
        if c:
            is_ace = is_card_ace2(t_player, cid)
            ace_pwr = ACE_POWER_BUFF if is_ace else 0
            ace_hp = ACE_HP_BUFF if is_ace else 0
            cname = f"[Ace 2 ⭐⭐] {format_card_id(c['id'])} {c['name']}" if is_ace else f"{format_card_id(c['id'])} {c['name']}"
            t_cards.append({
                "cid": cid, "name": cname, "power": c["power"] + t_buff_pwr + ace_pwr,
                "hp": c["hp"] + t_buff_hp + ace_hp, "current_hp": c["hp"] + t_buff_hp + ace_hp,
                "max_hp": c["hp"] + t_buff_hp + ace_hp, "is_ace2": is_ace
            })

    c_idx, t_idx, r_cnt = 0, 0, 0
    c_sakuya, c_reimu, c_marisa = False, False, False
    c_flandre = False
    t_sakuya, t_reimu, t_marisa = False, False, False
    t_flandre = False
    # Cờ tuyệt kỹ thẻ [T] #t1 Seiki (PvP): mỗi chiêu 1 lần/trận, tối đa 1 chiêu/lượt
    c_seiki_seal, c_seiki_spark, c_seiki_heal = False, False, False
    c_seiki_used_turn = -1
    t_seiki_seal, t_seiki_spark, t_seiki_heal = False, False, False
    t_seiki_used_turn = -1
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

        if cc["cid"] == 16 and cc["is_ace2"] and not c_sakuya:
            if random.random() < 0.40:
                c_sakuya = True
                t_stunned = True
                turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#16] Sakuya** ({challenger.display_name}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ {tc['name']} bị STUN!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if tc["cid"] == 16 and tc["is_ace2"] and not t_sakuya:
            if random.random() < 0.40:
                t_sakuya = True
                c_stunned = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[16]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#16] Sakuya** ({target.display_name}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ {cc['name']} bị STUN!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        c_invul = False
        t_invul = False
        if cc["cid"] == 13 and cc["is_ace2"] and not c_reimu:
            if random.random() < 0.40:
                c_reimu = True
                c_invul = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_skill = f"🛡️ **[Ace 2] [#13] Reimu** ({challenger.display_name}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if not c_invul and str(cc["cid"]).lower() == "t1" and not c_seiki_seal and c_seiki_used_turn != r_cnt:
            if random.random() < 0.40:
                c_seiki_seal = True
                c_seiki_used_turn = r_cnt
                c_invul = True
                if not turn_image:
                    turn_image = T1_SEAL_GIF
                msg_skill = f"🛡️ **[Nhóm T] [#t1] Seiki** ({challenger.display_name}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if tc["cid"] == 13 and tc["is_ace2"] and not t_reimu:
            if random.random() < 0.40:
                t_reimu = True
                t_invul = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_skill = f"🛡️ **[Ace 2] [#13] Reimu** ({target.display_name}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if not t_invul and str(tc["cid"]).lower() == "t1" and not t_seiki_seal and t_seiki_used_turn != r_cnt:
            if random.random() < 0.40:
                t_seiki_seal = True
                t_seiki_used_turn = r_cnt
                t_invul = True
                if not turn_image:
                    turn_image = T1_SEAL_GIF
                msg_skill = f"🛡️ **[Nhóm T] [#t1] Seiki** ({target.display_name}) kích hoạt **Fantasy Seal** (40%)! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        c_curr_power = cc["power"]
        t_curr_power = tc["power"]
        if cc["cid"] == 17 and cc["is_ace2"] and not c_marisa:
            if random.random() < 0.30:
                c_marisa = True
                c_curr_power = int(c_curr_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[17]["skill_gif"]
                msg_m = f"🌟 **[Ace 2] [#17] Marisa** ({challenger.display_name}) tung ra **Master Spark** (30%)! Oanh tạc ×2.0 sát thương ({c_curr_power:,} DMG)!"
                pvp_logs.append(msg_m)
                turn_actions.append(msg_m)

        # ===== ACE 2 FLANDRE (Challenger) - RIPPLES OF 495 YEARS (25%: XÓA 50% HP ĐỐI THỦ) =====
        if cc["cid"] == 9 and cc["is_ace2"] and not c_flandre:
            if random.random() < 0.25:
                c_flandre = True
                rip_dmg = int(tc["current_hp"] * 0.50)
                tc["current_hp"] = max(0, tc["current_hp"] - rip_dmg)
                if not turn_image:
                    turn_image = EVOL_CONFIG[9]["skill_gif"]
                msg_r = f"🦇 **[Ace 2] [#09] Flandre** ({challenger.display_name}) kích hoạt **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} HP (50% HP đối thủ)**!"
                pvp_logs.append(msg_r)
                turn_actions.append(msg_r)

        # ===== TUYỆT KỸ THẺ [T] #t1 SEIKI (Challenger) - Master Spark / Medicine Sign =====
        if str(cc["cid"]).lower() == "t1" and c_seiki_used_turn != r_cnt:
            roll_t1 = random.random()
            if not c_seiki_spark and roll_t1 < 0.30:
                c_seiki_spark = True
                c_seiki_used_turn = r_cnt
                c_curr_power = int(c_curr_power * 1.5)
                if not turn_image:
                    turn_image = T1_SPARK_GIF
                msg_m = f"🌟 **[Nhóm T] [#t1] Seiki** ({challenger.display_name}) tung **Master Spark** (30%)! Bộc phá ×1.5 sát thương ({c_curr_power:,} DMG)!"
                pvp_logs.append(msg_m)
                turn_actions.append(msg_m)
            elif not c_seiki_heal and cc["current_hp"] < cc["max_hp"] and roll_t1 < 0.50:
                c_seiki_heal = True
                c_seiki_used_turn = r_cnt
                heal_val = int(cc["max_hp"] * 0.30)
                cc["current_hp"] = min(cc["max_hp"], cc["current_hp"] + heal_val)
                if not turn_image:
                    turn_image = T1_HEAL_GIF
                msg_h = f"💚 **[Nhóm T] [#t1] Seiki** ({challenger.display_name}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_val:,} HP**! ({cc['current_hp']:,}/{cc['max_hp']:,} HP)"
                pvp_logs.append(msg_h)
                turn_actions.append(msg_h)

        if tc["cid"] == 17 and tc["is_ace2"] and not t_marisa:
            if random.random() < 0.30:
                t_marisa = True
                t_curr_power = int(t_curr_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[17]["skill_gif"]
                msg_m = f"🌟 **[Ace 2] [#17] Marisa** ({target.display_name}) tung ra **Master Spark** (30%)! Oanh tạc ×2.0 sát thương ({t_curr_power:,} DMG)!"
                pvp_logs.append(msg_m)
                turn_actions.append(msg_m)

        # ===== ACE 2 FLANDRE (Target) - RIPPLES OF 495 YEARS (25%: XÓA 50% HP ĐỐI THỦ) =====
        if tc["cid"] == 9 and tc["is_ace2"] and not t_flandre:
            if random.random() < 0.25:
                t_flandre = True
                rip_dmg = int(cc["current_hp"] * 0.50)
                cc["current_hp"] = max(0, cc["current_hp"] - rip_dmg)
                if not turn_image:
                    turn_image = EVOL_CONFIG[9]["skill_gif"]
                msg_r = f"🦇 **[Ace 2] [#09] Flandre** ({target.display_name}) kích hoạt **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} HP (50% HP đối thủ)**!"
                pvp_logs.append(msg_r)
                turn_actions.append(msg_r)

        # ===== TUYỆT KỸ THẺ [T] #t1 SEIKI (Target) - Master Spark / Medicine Sign =====
        if str(tc["cid"]).lower() == "t1" and t_seiki_used_turn != r_cnt:
            roll_t1 = random.random()
            if not t_seiki_spark and roll_t1 < 0.30:
                t_seiki_spark = True
                t_seiki_used_turn = r_cnt
                t_curr_power = int(t_curr_power * 1.5)
                if not turn_image:
                    turn_image = T1_SPARK_GIF
                msg_m = f"🌟 **[Nhóm T] [#t1] Seiki** ({target.display_name}) tung **Master Spark** (30%)! Bộc phá ×1.5 sát thương ({t_curr_power:,} DMG)!"
                pvp_logs.append(msg_m)
                turn_actions.append(msg_m)
            elif not t_seiki_heal and tc["current_hp"] < tc["max_hp"] and roll_t1 < 0.50:
                t_seiki_heal = True
                t_seiki_used_turn = r_cnt
                heal_val = int(tc["max_hp"] * 0.30)
                tc["current_hp"] = min(tc["max_hp"], tc["current_hp"] + heal_val)
                if not turn_image:
                    turn_image = T1_HEAL_GIF
                msg_h = f"💚 **[Nhóm T] [#t1] Seiki** ({target.display_name}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_val:,} HP**! ({tc['current_hp']:,}/{tc['max_hp']:,} HP)"
                pvp_logs.append(msg_h)
                turn_actions.append(msg_h)

        if not c_stunned and not t_invul:
            tc["current_hp"] -= c_curr_power
            turn_actions.append(f"⚔️ **{cc['name']}** giáng **{c_curr_power:,} DMG** lên **{tc['name']}**!")
        elif c_stunned:
            turn_actions.append(f"❄️ **{cc['name']}** bị đóng băng không thể tấn công!")
        elif t_invul:
            turn_actions.append(f"🛡️ **{tc['name']}** miễn nhiễm toàn bộ đòn đánh!")

        if not t_stunned and not c_invul:
            cc["current_hp"] -= t_curr_power
            turn_actions.append(f"⚔️ **{tc['name']}** giáng **{t_curr_power:,} DMG** lên **{cc['name']}**!")
        elif t_stunned:
            turn_actions.append(f"❄️ **{tc['name']}** bị đóng băng không thể tấn công!")
        elif c_invul:
            turn_actions.append(f"🛡️ **{cc['name']}** miễn nhiễm toàn bộ đòn đánh!")

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

    dq_c = update_daily_quest_progress(c_player, "pvp", 1)
    dq_t = update_daily_quest_progress(t_player, "pvp", 1)

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

    details_view = OpenDetailsView(pvp_turns)
    sent = False

    # 1. Thử gửi trực tiếp qua channel (nếu bot có quyền và channel hợp lệ)
    target_channel = channel
    if target_channel is None and interaction:
        target_channel = interaction.channel

    if target_channel:
        try:
            await target_channel.send(embed=embed, view=details_view)
            sent = True
        except discord.errors.Forbidden:
            logger.warning(f"PvP: Missing Access in channel {getattr(target_channel, 'id', None)}, attempting fallback...")
        except Exception as e:
            logger.warning(f"PvP: Error sending to channel: {e}")

    # 2. Nếu channel.send thất bại (403 Forbidden / Missing Access), thử gửi qua interaction followup webhook
    if not sent and interaction:
        try:
            await interaction.followup.send(embed=embed, view=details_view)
            sent = True
        except Exception as e:
            logger.warning(f"PvP: Interaction followup fallback failed: {e}")

    # 3. Thử qua bot.fetch_channel nếu có ID
    if not sent and target_channel and hasattr(target_channel, "id"):
        try:
            fetched_ch = await bot.fetch_channel(target_channel.id)
            if fetched_ch:
                await fetched_ch.send(embed=embed, view=details_view)
                sent = True
        except Exception as e:
            logger.warning(f"PvP: bot.fetch_channel fallback failed: {e}")

    # 4. Fallback cuối cùng: Gửi kết quả qua DM cho người thách đấu và người được thách đấu
    if not sent:
        for p_user in [challenger, target]:
            try:
                await p_user.send(
                    content=f"⚔️ **Kết quả trận PvP 3v3 giữa {challenger.display_name} và {target.display_name}:** (Kênh máy chủ thiếu quyền gửi tin nhắn)",
                    embed=embed,
                    view=OpenDetailsView(pvp_turns)
                )
            except Exception as e:
                logger.warning(f"PvP: Could not DM {getattr(p_user, 'display_name', p_user)}: {e}")

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
        team = [cid for cid in p.get("team", []) if cid in CARDS_DATA and not is_card_locked(p, cid)]
        if len(team) < 3:
            owned_ids = get_owned_card_ids(p)
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
        msg = "⚠️ Bạn chưa sở hữu thẻ bài hợp lệ để tham chiến (hoặc các thẻ đang bị Admin khóa)! Dùng `/pull` để tìm kiếm thẻ bài nhé."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if not t_team:
        msg = f"⚠️ Đối thủ {target.mention} hiện chưa có thẻ bài khả dụng để tiếp nhận chiến thư!"
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

    c_cards_str = "\n".join([f"• {format_card_id(CARDS_DATA[cid]['id'])} {CARDS_DATA[cid]['name']} ({CARDS_DATA[cid]['rank']}) - {CARDS_DATA[cid]['power']:,} ATK" for cid in c_team if cid in CARDS_DATA])
    t_cards_str = "\n".join([f"• {format_card_id(CARDS_DATA[cid]['id'])} {CARDS_DATA[cid]['name']} ({CARDS_DATA[cid]['rank']}) - {CARDS_DATA[cid]['power']:,} ATK" for cid in t_team if cid in CARDS_DATA])

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

# ==============================================================================
# HỆ THỐNG TRAO ĐỔI THẺ BÀI (TRADE CARDS - CHỐNG CLONE & XÁC NHẬN 2/2)
# ==============================================================================

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

def find_card_by_name_or_id(query: str):
    if not query:
        return None
    raw = query.strip().lower()
    clean_num = raw.replace("#", "").strip()
    if clean_num in CARDS_DATA:
        return clean_num
    if clean_num.isdigit():
        cid = int(clean_num)
        if cid in CARDS_DATA:
            return cid
    if raw in CARD_ALIASES:
        return CARD_ALIASES[raw]
    for cid, c in CARDS_DATA.items():
        if raw == c["name"].lower():
            return cid
    for cid, c in CARDS_DATA.items():
        if raw in c["name"].lower():
            return cid
    words = raw.replace("#", " ").replace(":", " ").split()
    for w in words:
        w_clean = w.strip()
        if w_clean in CARD_ALIASES:
            return CARD_ALIASES[w_clean]
        for cid, c in CARDS_DATA.items():
            if w_clean and len(w_clean) >= 3 and w_clean in c["name"].lower():
                return cid
    return None

def parse_trade_offer(offer_str: str):
    if not offer_str or not offer_str.strip():
        return None, "Chuỗi đề nghị trao đổi thẻ không được để trống!"
    items = [x.strip() for x in re.split(r"[,;]+", offer_str) if x.strip()]
    if not items:
        return None, "Không tìm thấy thẻ nào trong mục trao đổi!"

    result = {}
    for item in items:
        if ":" in item:
            parts = item.rsplit(":", 1)
            card_part = parts[0].strip()
            qty_part = parts[1].strip()
        else:
            words = item.strip().split()
            if len(words) > 1 and words[-1].isdigit():
                card_part = " ".join(words[:-1])
                qty_part = words[-1]
            else:
                card_part = item.strip()
                qty_part = "1"

        try:
            qty = int(qty_part)
        except ValueError:
            return None, f"Số lượng thẻ không hợp lệ trong `{item}`! Cú pháp chuẩn: `tên_nhân_vật:số_lượng` (Ví dụ: `reimu: 1` hoặc `sakuya:12`)."

        if qty <= 0:
            return None, f"Số lượng thẻ phải lớn hơn 0 (bạn nhập `{qty}`)!"

        cid = find_card_by_name_or_id(card_part)
        if not cid:
            return None, f"Không tìm thấy nhân vật `{card_part}` trong Gensokyo! (Ví dụ hợp lệ: `reimu: 1`, `sakuya:12`, `marisa: 5`, `13: 1`)."

        result[cid] = result.get(cid, 0) + qty

    return result, None

class TradeConfirmationView(discord.ui.View):
    def __init__(self, initiator: discord.Member, target: discord.Member, offer_give: dict, offer_receive: dict):
        super().__init__(timeout=120)
        self.initiator = initiator
        self.target = target
        self.offer_give = offer_give
        self.offer_receive = offer_receive
        self.confirmed_users = set()
        self.msg = None

    def _get_confirm_label(self):
        return f"✅ Đồng Ý Xác Nhận ({len(self.confirmed_users)}/2)"

    @discord.ui.button(label="✅ Đồng Ý Xác Nhận (0/2)", style=discord.ButtonStyle.success, emoji="🤝")
    async def confirm_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.initiator.id, self.target.id]:
            await interaction.response.send_message("❌ Bạn không tham gia phiên giao dịch này!", ephemeral=True)
            return

        if interaction.user.id in self.confirmed_users:
            await interaction.response.send_message("⏳ Bạn đã xác nhận rồi! Đang chờ đối phương xác nhận...", ephemeral=True)
            return

        self.confirmed_users.add(interaction.user.id)
        button.label = self._get_confirm_label()

        if len(self.confirmed_users) < 2:
            other_user = self.target if interaction.user.id == self.initiator.id else self.initiator
            await interaction.response.edit_message(
                content=f"🔔 **{interaction.user.display_name}** đã bấm xác nhận (1/2)! Đang đợi **{other_user.mention}** bấm xác nhận...",
                view=self
            )
            return

        p_a = get_player(self.initiator.id, self.initiator.display_name)
        p_b = get_player(self.target.id, self.target.display_name)

        inv_a = p_a.get("inventory", {})
        inv_b = p_b.get("inventory", {})

        for cid, qty in self.offer_give.items():
            if is_card_locked(p_a, cid):
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** Thẻ #{cid:02d} của {self.initiator.display_name} đang bị Admin khóa.", view=self)
                self.stop()
                return
            if inv_a.get(str(cid), 0) < qty:
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** {self.initiator.display_name} không còn đủ {qty} lá #{cid:02d} trong túi đồ.", view=self)
                self.stop()
                return

        for cid, qty in self.offer_receive.items():
            if is_card_locked(p_b, cid):
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** Thẻ #{cid:02d} của {self.target.display_name} đang bị Admin khóa.", view=self)
                self.stop()
                return
            if inv_b.get(str(cid), 0) < qty:
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** {self.target.display_name} không còn đủ {qty} lá #{cid:02d} trong túi đồ.", view=self)
                self.stop()
                return

        for cid, qty in self.offer_give.items():
            inv_a[str(cid)] = inv_a.get(str(cid), 0) - qty
            inv_b[str(cid)] = inv_b.get(str(cid), 0) + qty

        for cid, qty in self.offer_receive.items():
            inv_b[str(cid)] = inv_b.get(str(cid), 0) - qty
            inv_a[str(cid)] = inv_a.get(str(cid), 0) + qty

        p_a["inventory"] = inv_a
        p_b["inventory"] = inv_b
        save_player(p_a)
        save_player(p_b)

        for child in self.children:
            child.disabled = True

        embed_success = discord.Embed(
            title="🎉 GIAO DỊCH THẺ BÀI THÀNH CÔNG (2/2 ĐÃ XÁC NHẬN)!",
            description=(
                f"✨ Thỏa thuận trao đổi thẻ bài giữa **{self.initiator.mention}** và **{self.target.mention}** đã hoàn tất an toàn!\n"
                f"Túi đồ của cả hai người chơi đã được cập nhật thành công."
            ),
            color=0x10B981
        )

        give_summary_a = "\n".join([f"• Gửi đi: {qty}x **#{cid:02d} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Còn: {inv_a.get(str(cid), 0)} lá)" for cid, qty in self.offer_give.items()])
        recv_summary_a = "\n".join([f"• Nhận về: {qty}x **#{cid:02d} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Hiện có: {inv_a.get(str(cid), 0)} lá)" for cid, qty in self.offer_receive.items()])
        embed_success.add_field(
            name=f"📦 {self.initiator.display_name} cập nhật:",
            value=f"{give_summary_a}\n{recv_summary_a}",
            inline=False
        )

        give_summary_b = "\n".join([f"• Gửi đi: {qty}x **#{cid:02d} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Còn: {inv_b.get(str(cid), 0)} lá)" for cid, qty in self.offer_give.items()])
        recv_summary_b = "\n".join([f"• Nhận về: {qty}x **#{cid:02d} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Hiện có: {inv_b.get(str(cid), 0)} lá)" for cid, qty in self.offer_receive.items()])
        embed_success.add_field(
            name=f"📦 {self.target.display_name} cập nhật:",
            value=f"{give_summary_b}\n{recv_summary_b}",
            inline=False
        )
        embed_success.set_footer(text="🛡️ Đã xác thực chống Spam Clone: Thẻ bài trao đổi cả 2 bên đều đã sở hữu trước đó.")

        await interaction.response.edit_message(
            content=f"✅ **GIAO DỊCH HOÀN TẤT!** {self.initiator.mention} ⇄ {self.target.mention}",
            embed=embed_success,
            view=self
        )
        self.stop()

    @discord.ui.button(label="❌ Từ Chối / Hủy Bỏ", style=discord.ButtonStyle.danger, emoji="🚫")
    async def cancel_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.initiator.id, self.target.id]:
            await interaction.response.send_message("❌ Bạn không tham gia phiên giao dịch này!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        canceller = self.initiator.display_name if interaction.user.id == self.initiator.id else self.target.display_name
        embed_cancel = discord.Embed(
            title="🚫 GIAO DỊCH ĐÃ BỊ HỦY BỎ",
            description=f"Phiên trao đổi thẻ đã bị từ chối hoặc hủy bởi **{canceller}**.",
            color=0xEF4444
        )
        await interaction.response.edit_message(content=None, embed=embed_cancel, view=self)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.msg:
            try:
                await self.msg.edit(content="⏰ **Hết thời gian chờ giao dịch (2 phút). Giao dịch đã tự động hủy.**", view=self)
            except Exception:
                pass

async def send_trade_msg(ctx_or_interaction, content=None, embed=None, view=None, ephemeral=False):
    if isinstance(ctx_or_interaction, discord.Interaction):
        if ctx_or_interaction.response.is_done():
            return await ctx_or_interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=ephemeral)
            return await ctx_or_interaction.original_response()
    else:
        return await ctx_or_interaction.send(content=content, embed=embed, view=view)

async def handle_trade(ctx_or_interaction, user: Union[discord.Member, discord.User], your: str = None, their: str = None):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    if user is None:
        msg = "⚠️ Vui lòng gắn thẻ người bạn muốn giao dịch cùng! Ví dụ: `/trade user:@NgườiDùng your:reimu: 1 their:sakuya:12`"
        await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
        return

    if getattr(user, "bot", False):
        msg = "🤖 Không thể giao dịch thẻ bài với Bot!"
        await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
        return

    if user.id == author.id:
        msg = "🤡 Bạn không thể tự giao dịch thẻ với chính mình!"
        await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
        return

    p_a = get_player(author.id, getattr(author, "display_name", str(author)))
    p_b = get_player(user.id, getattr(user, "display_name", str(user)))

    inv_a = p_a.get("inventory", {})
    inv_b = p_b.get("inventory", {})

    if not your or not their:
        eligible_a_gives = [cid for cid, c in CARDS_DATA.items() if inv_a.get(str(cid), 0) >= 1 and (inv_b.get(str(cid), 0) >= 1 or is_card_ace2(p_b, cid)) and not is_card_locked(p_a, cid)]
        eligible_b_gives = [cid for cid, c in CARDS_DATA.items() if inv_b.get(str(cid), 0) >= 1 and (inv_a.get(str(cid), 0) >= 1 or is_card_ace2(p_a, cid)) and not is_card_locked(p_b, cid)]

        a_cards_txt = ", ".join([f"#{c:02d} {CARDS_DATA[c]['name']}" for c in eligible_a_gives[:8]]) or "Chưa có thẻ chung hợp lệ"
        b_cards_txt = ", ".join([f"#{c:02d} {CARDS_DATA[c]['name']}" for c in eligible_b_gives[:8]]) or "Chưa có thẻ chung hợp lệ"

        embed_guide = discord.Embed(
            title="🤝 HỆ THỐNG TRAO ĐỔI THẺ BÀI (TRADE CARDS)",
            description=(
                f"**Giao dịch an toàn giữa {author.mention} và {user.mention}:**\n\n"
                f"📌 **Cú pháp lệnh:**\n"
                f"• `/trade user:@{getattr(user, 'display_name', str(user))} your:<tên_nhân_vật:số_lượng> their:<tên_nhân_vật:số_lượng>`\n"
                f"*(Ví dụ: `/trade user:@{getattr(user, 'display_name', str(user))} your:reimu: 1 their:sakuya:12`)*\n\n"
                f"🛡️ **QUY TẮC CHỐNG CLONE ACCOUNT & KHÓA ADMIN:**\n"
                f"• Người nhận **BẮT BUỘC ĐÃ SỞ HỮU THẺ ĐÓ RỒI** mới có thể nhận thêm.\n"
                f"• Tuyệt đối không thể trao đổi lá bài đang bị Admin niêm phong.\n"
                f"• Cả 2 bên bắt buộc phải gửi thẻ cho nhau (trao đổi tương hỗ).\n"
                f"• Cả 2 người phải cùng bấm nút xác nhận **(2/2)** trong vòng 2 phút để hoàn tất.\n\n"
                f"📋 **Gợi ý thẻ hợp lệ có thể trao đổi ngay:**\n"
                f"• **{getattr(author, 'display_name', str(author))} có thể gửi cho {getattr(user, 'display_name', str(user))}:**\n{a_cards_txt}\n"
                f"• **{getattr(user, 'display_name', str(user))} có thể gửi cho {getattr(author, 'display_name', str(author))}:**\n{b_cards_txt}"
            ),
            color=0x3B82F6
        )
        await send_trade_msg(ctx_or_interaction, embed=embed_guide)
        return

    offer_a, err_a = parse_trade_offer(your)
    if err_a:
        await send_trade_msg(ctx_or_interaction, content=f"⚠️ **Mục [your] không hợp lệ:** {err_a}", ephemeral=True)
        return

    offer_b, err_b = parse_trade_offer(their)
    if err_b:
        await send_trade_msg(ctx_or_interaction, content=f"⚠️ **Mục [their] không hợp lệ:** {err_b}", ephemeral=True)
        return

    for cid, qty in offer_a.items():
        card_info = CARDS_DATA[cid]
        if is_card_locked(p_a, cid):
            msg = f"🔒 Lá bài **#{cid:02d} {card_info['name']}** của bạn đang bị Admin niêm phong, không thể mang đi trao đổi!"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        has_cnt = inv_a.get(str(cid), 0)
        if has_cnt < qty:
            msg = f"❌ Bạn (**{getattr(author, 'display_name', str(author))}**) không đủ {qty} lá **#{cid:02d} [{card_info['rank']}] {card_info['name']}** để gửi đi! (Hiện chỉ có: {has_cnt} lá)"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        if inv_b.get(str(cid), 0) < 1 and not is_card_ace2(p_b, cid):
            msg = (
                f"🛡️ **Quy định chống Clone Account:**\n"
                f"Đối phương (**{getattr(user, 'display_name', str(user))}**) chưa từng sở hữu thẻ **#{cid:02d} [{card_info['rank']}] {card_info['name']}**!\n"
                f"⚠️ Người nhận bắt buộc phải đã sở hữu ít nhất 1 lá bài này từ trước mới được phép nhận trade."
            )
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

    for cid, qty in offer_b.items():
        card_info = CARDS_DATA[cid]
        if is_card_locked(p_b, cid):
            msg = f"🔒 Lá bài **#{cid:02d} {card_info['name']}** của đối phương đang bị Admin niêm phong, không thể mang đi trao đổi!"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        has_cnt = inv_b.get(str(cid), 0)
        if has_cnt < qty:
            msg = f"❌ Đối phương (**{getattr(user, 'display_name', str(user))}**) không đủ {qty} lá **#{cid:02d} [{card_info['rank']}] {card_info['name']}** để gửi lại! (Hiện chỉ có: {has_cnt} lá)"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        if inv_a.get(str(cid), 0) < 1 and not is_card_ace2(p_a, cid):
            msg = (
                f"🛡️ **Quy định chống Clone Account:**\n"
                f"Bạn (**{getattr(author, 'display_name', str(author))}**) chưa từng sở hữu thẻ **#{cid:02d} [{card_info['rank']}] {card_info['name']}**!\n"
                f"⚠️ Bạn bắt buộc phải đã sở hữu ít nhất 1 lá bài này từ trước mới được phép nhận trade."
            )
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

    trade_view = TradeConfirmationView(author, user, offer_a, offer_b)
    embed_trade = discord.Embed(
        title="🤝 LỜI ĐỀ NGHỊ TRAO ĐỔI THẺ BÀI TOUHOU",
        description=(
            f"🔥 **{author.mention}** đã gửi một lời đề nghị trao đổi thẻ bài tới **{user.mention}**!\n"
            f"*(Cả hai người chơi vui lòng kiểm tra kỹ chi tiết bên dưới và cùng bấm **Đồng Ý Xác Nhận (2/2)**)*"
        ),
        color=0xF59E0B
    )
    give_txt = "\n".join([f"• {qty}x **#{cid:02d} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Kho: {inv_a.get(str(cid), 0)} lá)" for cid, qty in offer_a.items()])
    recv_txt = "\n".join([f"• {qty}x **#{cid:02d} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Kho: {inv_b.get(str(cid), 0)} lá)" for cid, qty in offer_b.items()])

    embed_trade.add_field(
        name=f"📤 {getattr(author, 'display_name', str(author))} gửi đi:",
        value=give_txt,
        inline=True
    )
    embed_trade.add_field(
        name=f"📥 {getattr(user, 'display_name', str(user))} gửi lại:",
        value=recv_txt,
        inline=True
    )
    embed_trade.add_field(
        name="🛡️ Trạng Thái Chống Clone:",
        value="✅ **Hợp lệ:** Cả hai bên đều đã sở hữu trước các loại thẻ này!",
        inline=False
    )
    embed_trade.set_footer(text="Giao dịch sẽ tự động hủy sau 2 phút nếu không đủ 2/2 lượt xác nhận.")

    msg_obj = await send_trade_msg(ctx_or_interaction, content=f"{user.mention}", embed=embed_trade, view=trade_view)
    trade_view.msg = msg_obj

@bot.tree.command(name="pvp", description="Thách đấu người chơi khác trong server trận đại chiến 3v3")
@app_commands.describe(target="Chọn người chơi bạn muốn thách đấu")
async def slash_pvp(interaction: discord.Interaction, target: Union[discord.Member, discord.User]):
    await handle_pvp(interaction, target)

@bot.command(name="pvp")
async def prefix_pvp(ctx, target: Union[discord.Member, discord.User] = None):
    await handle_pvp(ctx, target)

@bot.tree.command(name="trade", description="Trao đổi thẻ bài giữa 2 người chơi (chống clone acc, xác nhận 2/2)")
@app_commands.describe(
    user="Người chơi bạn muốn trao đổi thẻ",
    your="Thẻ bạn đưa ra kèm số lượng (Ví dụ: reimu: 1 hoặc reimu:1, marisa:2)",
    their="Thẻ đối phương đưa ra kèm số lượng (Ví dụ: sakuya:12 hoặc sakuya:12, cirno:5)"
)
async def slash_trade(interaction: discord.Interaction, user: Union[discord.Member, discord.User], your: str = None, their: str = None):
    await interaction.response.defer()
    try:
        await handle_trade(interaction, user, your, their)
    except Exception as e:
        print(f"Lỗi khi thực hiện trade: {e}", flush=True)
        try:
            await interaction.followup.send(f"❌ Đã xảy ra sự cố khi xử lý trao đổi thẻ: {e}", ephemeral=True)
        except Exception:
            pass

@bot.command(name="trade")
async def prefix_trade(ctx, user: Union[discord.Member, discord.User] = None, *, offers: str = None):
    your = None
    their = None
    if offers:
        if "your:" in offers and "their:" in offers:
            try:
                parts = offers.split("their:")
                your = parts[0].replace("your:", "").strip()
                their = parts[1].strip()
            except Exception:
                pass
        else:
            items = offers.split()
            if len(items) == 2:
                your, their = items[0], items[1]
            elif len(items) >= 4:
                your, their = items[0] + " " + items[1], items[2] + " " + items[3]
    await handle_trade(ctx, user, your, their)

@bot.tree.command(name="boss_status", description="Kiểm tra trạng thái và thời gian hồi chiêu của Boss Raid")
async def slash_boss_status(interaction: discord.Interaction):
    global boss_cooldown_until, active_raid
    check_and_clean_expired_raid()
    now = time.time()
    embed = discord.Embed(title="👹 TRẠNG THÁI BOSS RAID: REIMU DỊ HÌNH (2 PHASE)", color=0xDC2626)
    embed.set_thumbnail(url=BOSS_CONFIG["image"])
    embed.add_field(name="❤️ Chỉ Số 2 Phase:", value=f"• Phase 1: HP {BOSS_CONFIG['hp']:,} | Đánh thường {BOSS_CONFIG['power']:,} DMG (chia đều)\n• Phase 2: HP {BOSS_PHASE2_CONFIG['hp']:,} | Đánh thường {BOSS_PHASE2_CONFIG['power']:,} DMG (chia đều)", inline=True)
    embed.add_field(name="🎁 Phần Thưởng:", value="100% Quy đổi thành Vé Pull tích lũy!", inline=True)
    if active_raid:
        if active_raid.get("started"):
            embed.add_field(name="🔥 Tình Trạng:", value="⚔️ **ĐANG TRỰC TIẾP GIAO CHIẾN!** Các hiệp đấu đang diễn ra gay cấn!", inline=False)
        else:
            time_left = max(0, int(120 - (now - active_raid.get("created_timestamp", now))))
            embed.add_field(name="🔥 Tình Trạng:", value=f"**ĐANG CHỜ XUẤT TRẬN!** Có **{len(active_raid.get('participants', []))}/{BOSS_CONFIG['max_players']} dũng giả**!\n⏱️ Còn lại: **{time_left} giây** (Hết giờ sẽ **TỰ ĐỘNG KHAI MÀN** nếu có người join, hoặc đóng lại nếu không ai dám nghênh chiến)!", inline=False)
    elif now < boss_cooldown_until:
        rem = int(boss_cooldown_until - now)
        embed.add_field(name="⏳ Hồi Chiêu:", value=f"Cần đợi thêm **{rem // 60} phút {rem % 60} giây** nữa!", inline=False)
    else:
        embed.add_field(name="🟢 Sẵn Sàng:", value="Boss đã sẵn sàng xuất hiện ngẫu nhiên (10% khi chat)!\n*(Hoặc Admin có thể dùng `boss admin spawn`)*", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.command(name="boss", aliases=["bossstatus"])
async def prefix_boss_status(ctx, *args):
    global boss_cooldown_until, active_raid
    if args:
        sub = " ".join(args).strip().lower()
        if sub in ["admin spawn", "spawn"] or sub.startswith("admin spawn") or sub.startswith("spawn"):
            if not is_authorized_admin(ctx.author):
                await ctx.send(f"⛔ {ctx.author.mention} Ngươi không có quyền hạn! Chỉ có bố Seiki hoặc Quản Trị Viên mới được triệu hồi Boss Raid!")
                return
            b_type = None
            if "seiki" in sub:
                b_type = "seiki"
            elif "reimu" in sub:
                b_type = "reimu"
            await admin_spawn_boss(ctx.channel, ctx.author, boss_type=b_type)
            return
        elif sub in ["admin reset", "reset"]:
            if not is_authorized_admin(ctx.author):
                await ctx.send(f"⛔ {ctx.author.mention} Ngươi không có quyền hạn! Chỉ có bố Seiki hoặc Quản Trị Viên mới được reset Boss Raid!")
                return
            await admin_reset_boss(ctx.channel, ctx.author)
            return

    check_and_clean_expired_raid()
    now = time.time()
    if active_raid:
        if active_raid.get("started"):
            await ctx.send("🚨 Boss Raid ĐANG TRỰC TIẾP GIAO CHIẾN!")
        else:
            time_left = max(0, int(120 - (now - active_raid.get("created_timestamp", now))))
            await ctx.send(f"🚨 Boss Raid ĐANG CHỜ XUẤT TRẬN ({len(active_raid.get('participants', []))}/{BOSS_CONFIG['max_players']} người)! Còn {time_left}s sẽ tự động mở trận!")
    elif now < boss_cooldown_until:
        rem = int(boss_cooldown_until - now)
        await ctx.send(f"⏳ Boss đang hồi chiêu 15 phút (Còn lại: {rem // 60}m {rem % 60}s).")
    else:
        await ctx.send("🟢 Boss đã sẵn sàng xuất hiện (Tỉ lệ 5% Seiki Dị Hình, 5% Reimu Dị Hình khi chat, hoặc dùng `boss admin spawn [seiki|reimu]`)!")

@bot.tree.command(name="boss_admin", description="[Admin] Quản trị Boss Raid (Reimu Dị Hình hoặc Seiki Dị Hình)")
@app_commands.describe(action="Hành động muốn thực hiện với Boss Raid", loai_boss="Loại Boss muốn triệu hồi (nếu chọn spawn)")
@app_commands.choices(action=[
    app_commands.Choice(name="spawn - Triệu hồi Boss ngay tại kênh này", value="spawn"),
    app_commands.Choice(name="reset - Giải phóng Boss kẹt và xóa hồi chiêu", value="reset")
], loai_boss=[
    app_commands.Choice(name="Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư", value="seiki"),
    app_commands.Choice(name="Reimu Dị Hình - 2 Phase Siêu Cấp", value="reimu"),
    app_commands.Choice(name="Ngẫu nhiên 50/50 giữa 2 Boss", value="random")
])
async def slash_boss_admin(interaction: discord.Interaction, action: str, loai_boss: str = "random"):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN HẠN!** Chỉ có Han Seiki hoặc Admin mới được dùng lệnh này!", ephemeral=True)
        return
    if action == "spawn":
        b_type = None if loai_boss == "random" else loai_boss
        boss_label = "Seiki Dị Hình" if b_type == "seiki" else ("Reimu Dị Hình" if b_type == "reimu" else "Boss Raid ngẫu nhiên")
        await interaction.response.send_message(f"⚡ Đang cưỡng chế triệu hồi {boss_label}...", ephemeral=True)
        await admin_spawn_boss(interaction.channel, interaction.user, boss_type=b_type)
    elif action == "reset":
        await admin_reset_boss(interaction, interaction.user)

@bot.tree.command(name="admin_boss_spawn", description="[Admin] Triệu hồi ngay Boss Raid (Seiki Dị Hình hoặc Reimu Dị Hình) tại kênh này")
@app_commands.describe(loai_boss="Chọn Boss muốn triệu hồi")
@app_commands.choices(loai_boss=[
    app_commands.Choice(name="Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư", value="seiki"),
    app_commands.Choice(name="Reimu Dị Hình - 2 Phase Siêu Cấp", value="reimu"),
    app_commands.Choice(name="Ngẫu nhiên 50/50 giữa 2 Boss", value="random")
])
async def slash_admin_boss_spawn(interaction: discord.Interaction, loai_boss: str = "random"):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN HẠN!**", ephemeral=True)
        return
    b_type = None if loai_boss == "random" else loai_boss
    boss_label = "Seiki Dị Hình" if b_type == "seiki" else ("Reimu Dị Hình" if b_type == "reimu" else "Boss Raid ngẫu nhiên")
    await interaction.response.send_message(f"⚡ Đang triệu hồi {boss_label}...", ephemeral=True)
    await admin_spawn_boss(interaction.channel, interaction.user, boss_type=b_type)

@bot.tree.command(name="admin_boss_reset", description="[Admin] Giải phóng Boss Raid bị kẹt và xóa hồi chiêu")
async def slash_admin_boss_reset(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN HẠN!**", ephemeral=True)
        return
    await admin_reset_boss(interaction, interaction.user)

async def handle_help(ctx_or_interaction):
    desc = """
⛩️ **HAKUREI REIMU DISCORD BOT - BẢN ĐỒ LỆNH**

**🌸 TÂN THỦ & NHIỆM VỤ:**
• `/tutorial`: Khóa huấn luyện tân thủ (Thưởng 10 lượt pull, cấp 3 lượt pull 100% không trùng lá, không bao giờ ra thẻ SS, tiến trình 1 chiều).
• `/quest`: Xem 3/3 Nhiệm vụ Hàng Ngày (Nhận vé pull & thưởng lớn +10 lượt pull khi xong cả 3).

**🎮 GACHA, TIẾN HÓA & TRAO ĐỔI:**
• `/pull [số_lượng]`: Quay thẻ Touhou (Free 5 lượt/ngày). *Thẻ đã quay được sẽ mở khóa vĩnh viễn! Quay trúng lại thẻ bị lock sẽ mở khóa!*
• `/daily`: Điểm danh nhận 1 vé pull mỗi ngày.
• `/evol [id_hoac_ten]`: Tiến hóa Ace 2 ⭐⭐ (Buff +300 ATK, +300 HP, trừ thẻ sau khi evol):
  - [#13] Reimu (20 thẻ): Vô Tưởng Chuyển Sinh (40% miễn sát thương).
  - [#16] Sakuya (30 thẻ): Thời Gian Đóng Băng (40% stun đối thủ).
  - [#17] Marisa (25 thẻ): Master Spark (30% kích hoạt sát thương ×2.0 lần).
  - [#09] Flandre (30 thẻ): Ripples of 495 Years (25% xóa 50% HP đối thủ / 30% HP Boss Raid, 1 lần/trận).
• `/trade <user> [your] [their]`: Trao đổi thẻ bài (Cú pháp `your:tên:số_lượng` và `their:tên:số_lượng`, ví dụ: `your:reimu: 1 their:sakuya:12`, giao diện xác nhận 2 bên).
• `/team [hanh_dong] [id_the]`: Quản lý đội hình (view, add, remove). Mỗi cấp độ tăng +20 ATK và +25 HP buff!
• `/check [id_hoac_ten]`: Soi chi tiết sức mạnh, máu và kỹ năng của 26 nhân vật Touhou + thẻ đặc biệt [T] #t1 Seiki (gõ `seiki` hoặc `t1`, kèm Ace 2, có nút ◀ ▶ lướt danh sách, menu chọn nhanh và nút 🔮 xem thẻ T1).
• `/collection`: Xem 26 nhân vật Touhou (SS, S, A, B, C).

**⚔️ CHIẾN ĐẤU & BOSS RAID:**
• `/battle`: Giao đấu nhân vật nhận 50-100 XP (hồi chiêu 1 phút).
• `/pvp <người_chơi>`: Thách đấu người chơi khác trong server trận đại chiến 3v3 đỉnh cao.
• `/boss_status`: Kiểm tra hồi chiêu 15 phút của Boss Raid.
• **Thông tin chi tiết trận chiến**: Sau Battle, Raid và PvP luôn có nút **📜 Xem Chi Tiết Trận Chiến & GIF Kỹ Năng** để xem lại từng hiệp kèm GIF hoạt ảnh trực tiếp (không dùng link dẫn ra ngoài).

**👹 DỊ BIẾN REIMU DỊ HÌNH (LIVE COMBAT):**
• **Phase 1 (30k HP / 15k DMG):** Quà rơi: 10% 10 vé, 40% 5 vé, 50% 3 vé. Trận đấu phát sóng turn-by-turn trực tiếp!
• **Phase 2 Thức Tỉnh (50k HP / 22k DMG):** Tự động hồi sinh & hồi 100% HP mọi thẻ bài! Quà siêu cấp: 10% 20 vé, 40% 10 vé, 50% 5 vé!

**👑 LỆNH ADMIN (OWNER EXCLUSIVE - ID: 1502579398560317441):**
• `/admin_lock <user> <id_the>`: Niêm phong thẻ bài của người chơi (chỉ mở khi pull ra lại).
• `/admin_reset_quest [user]`: Làm mới thủ công 3/3 Nhiệm Vụ Ngày (hệ thống vốn tự động reset lúc 00:00 GMT+7).
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
