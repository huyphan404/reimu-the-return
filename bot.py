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
#    - Luôn hiển thị ID nhân vật: [#15] Reimu Hakurei, [#18] Sakuya Izayoi
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
#    - Buff Marisa Ace 2 [#18]: Master Spark tăng sát thương từ ×1.5 lên ×2.0!
#    - [#t1] Seiki Đệ Nhất Pháp Sư (Ace 2 ⭐⭐): Cleave (+2% Max HP mục tiêu mọi đòn) • Medicine Sign (35% hồi 40% máu) •
#      Fantasy Seal (40% ở Ace 1 / buff lên 50% ở Ace 2: Miễn toàn bộ sát thương) • Bóng Khái Niệm (40%: 15% Max HP + xóa kỹ năng đối phương)!
# ==============================================================================

# UPDATE 2026-09-22: THEM [#10] KOISHI KOMEIJI (Rank S - 600 ATK / 6,060 HP) - ID CU 10-26 DAY LEN 11-27, TU DONG DI TRU DU LIEU NGUOI CHOI
# UPDATE 2026-09-24: THEM ACE 2 MOI - [#12] REMILIA (25 THE, THUONG DO GUNGNIR THU DONG +3% MAX HP MUC TIEU) & [#20] REISEN (40 THE, RED EYE MIND EXPLOSION 25% - MUC TIEU 20% TU SAT TRONG 4 TURN)
# UPDATE 2026-09-27: THEM BOSS MOI [BAT ACH KIEM THAN TUONG MAHORAGA] (90K HP / 6K DMG CHIA DEU) - THE TRUE ADAPT (HOI 3% HP + GIAM 3% ST MOI TURN) + THOAI MA KIEM (DON MUC TIEU), TI LE SPAWN 3 BOSS DEU 1/3, THEM MAHORAGA SHARD (5% DROP)
# UPDATE 2026-09-27: CAP NHAT ACE 2 MOI - [#22] CIRNO (60 THE, PERFECT FREEZE 40% - 2 TURN TIEP 45% DONG BANG KHONG DANH TRA) & [#13] UTSUHO REIUJI (30 THE, NUCLEAR SPELL CARD 30% - 3.0x DMG & DUNG NHAM BONG 2% MAX HP TRONG 3 TURN)
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

def keep_alive_ping():
    """Tự động ping chính web server mỗi 4 phút để Render không bao giờ ngủ"""
    import urllib.request
    port = int(os.environ.get("PORT", 10000))
    url = os.environ.get("RENDER_EXTERNAL_URL") or f"http://127.0.0.1:{port}/"
    while True:
        time.sleep(240)
        try:
            urllib.request.urlopen(url, timeout=10)
        except Exception:
            pass

threading.Thread(target=keep_alive_ping, daemon=True).start()

# ==============================================================================
# 2. HỆ THỐNG CẤP ĐỘ & XP MỚI (+50 XP MỖI CẤP, MỞ GIỚI HẠN THEO PRESTIGE)
# ==============================================================================
DEFAULT_MAX_LEVEL = 100

def get_max_level(prestige: int = 0) -> int:
    """Trả về giới hạn cấp tối đa dựa theo cấp chuyển sinh (Prestige)"""
    if prestige <= 1:
        return 100 # P0 và P1 không mở thêm lv (tối đa 100)
    elif prestige == 2:
        return 150 # P2 mở giới hạn lên 150 (bằng điều kiện lên P3)
    elif prestige == 3:
        return 200 # P3 mở giới hạn lên 200 (bằng điều kiện lên P4)
    elif prestige == 4:
        return 500 # P4 mở giới hạn lên 500 (bằng điều kiện lên P5)
    else:
        # P5 trở đi giữ tối thiểu 500 hoặc bằng điều kiện của Prestige đó
        return max(500, get_prestige_info(prestige).get("req_lvl", 500))

def get_xp_needed_for_level(level: int) -> int:
    if level < 1:
        level = 1
    return 100 + (level - 1) * 50

def get_total_xp_for_level(level: int, max_lvl: int = None) -> int:
    if level <= 1:
        return 0
    if max_lvl is not None and level > max_lvl:
        level = max_lvl
    n = level - 1
    return 25 * n * (n + 3)

def calculate_level_from_xp(total_xp: int, prestige_or_player: Union[int, dict] = 0) -> int:
    if total_xp <= 0:
        return 1
    p_lvl = prestige_or_player.get("prestige", 0) if isinstance(prestige_or_player, dict) else int(prestige_or_player or 0)
    max_lvl = get_max_level(p_lvl)
    lvl = 1
    while lvl < max_lvl:
        next_threshold = get_total_xp_for_level(lvl + 1)
        if total_xp >= next_threshold:
            lvl += 1
        else:
            break
    return lvl

def get_level_progress(total_xp: int, prestige_or_player: Union[int, dict] = 0):
    p_lvl = prestige_or_player.get("prestige", 0) if isinstance(prestige_or_player, dict) else int(prestige_or_player or 0)
    max_lvl = get_max_level(p_lvl)
    lvl = calculate_level_from_xp(total_xp, p_lvl)
    if lvl >= max_lvl:
        return lvl, 0, 0, 1.0
    base_xp = get_total_xp_for_level(lvl)
    xp_in_level = max(0, total_xp - base_xp)
    needed = get_xp_needed_for_level(lvl)
    ratio = min(1.0, max(0.0, xp_in_level / needed)) if needed > 0 else 1.0
    return lvl, xp_in_level, needed, ratio

# ==============================================================================
# HỆ THỐNG PRESTIGE (CHUYỂN SINH) & XP MULTIPLIER
# ==============================================================================
def get_prestige_info(current_p: int):
    next_p = current_p + 1
    if next_p == 1:
        return {"next_p": 1, "req_lvl": 50, "pulls": 50.0, "tokens": 100, "xp_mult": 2.0}
    elif next_p == 2:
        return {"next_p": 2, "req_lvl": 100, "pulls": 50.0, "tokens": 150, "xp_mult": 3.5}
    elif next_p == 3:
        return {"next_p": 3, "req_lvl": 150, "pulls": 50.0, "tokens": 250, "xp_mult": 5.0}
    elif next_p == 4:
        return {"next_p": 4, "req_lvl": 200, "pulls": 50.0, "tokens": 300, "xp_mult": 7.5}
    elif next_p == 5:
        return {"next_p": 5, "req_lvl": 500, "pulls": 50.0, "tokens": 1000, "xp_mult": 10.0}
    else:
        # P6 trở đi: Cố định hệ số nhân XP ở mức 10.0x
        return {"next_p": next_p, "req_lvl": 100, "pulls": 50.0, "tokens": 120, "xp_mult": 10.0}

def get_prestige_xp_multiplier(prestige_lvl: int) -> float:
    if prestige_lvl <= 0: return 1.0
    elif prestige_lvl == 1: return 2.0
    elif prestige_lvl == 2: return 3.5
    elif prestige_lvl == 3: return 5.0
    elif prestige_lvl == 4: return 7.5
    else: return 10.0
# ==============================================================================
# 3. TOUHOU CARDS DATABASE (27 NHÂN VẬT CHUẨN THÔNG SỐ)
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
    10: {"id": 10, "name": "Koishi Komeiji", "rank": "S", "power": 600, "hp": 6060, "image": "https://media.discordapp.net/attachments/1543072032034521228/1551877562995576952/images.png?ex=6ab3921b&is=6ab2409b&hm=52af3a3289d15e889b79325bc7d9a45403be6fb07cf7a4ab85b1f3a131da2d56&=&format=webp&quality=lossless"},
    11: {"id": 11, "name": "Kaguya Houraisan", "rank": "S", "power": 590, "hp": 6400, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082450930696282/images.png?ex=6aa966f4&is=6aa81574&hm=363a0b7d509db06c3773fba176ede9646cfef4a95c5d2515703120d30bfc4e94&=&format=webp&quality=lossless&width=361&height=512"},
    12: {"id": 12, "name": "Remilia Scarlet", "rank": "S", "power": 560, "hp": 5600, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079793461633065/images.png?ex=6aa9647b&is=6aa812fb&hm=19fc0f72cd5fca597f9eeae493b1c7c663d11ffc98fff679bfd2dfdb588950e1&=&format=webp&quality=lossless"},
    13: {"id": 13, "name": "Utsuho Reiuji (Okuu)", "rank": "S", "power": 550, "hp": 5300, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081971169304647/images.png?ex=6aa96682&is=6aa81502&hm=6f7668c4db22133f1aa0bdc07ec7fa2c050ff4e4d220f744cd02e8cc04662c0f&=&format=webp&quality=lossless"},
    14: {"id": 14, "name": "Ibaraki-Douji's Arm", "rank": "A", "power": 500, "hp": 4800, "image": "https://media.discordapp.net/attachments/1553441571767324732/1553442346476240966/content.png?ex=6abd37ec&is=6abbe66c&hm=f4746bd3947c98c6037201b16a57ba3138380fdc092d71a20f2ecf56b1436b55&=&format=webp&quality=lossless&width=971&height=1024"},
    15: {"id": 15, "name": "Reimu Hakurei", "rank": "A", "power": 500, "hp": 5000, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549078962746171463/images.png?ex=6aa963b5&is=6aa81235&hm=3fa720bd7311e4ca45789c6a0112327878135e9d9944c31c6ed2ea1f60885853&=&format=webp&quality=lossless"},
    16: {"id": 16, "name": "Fujiwara no Mokou", "rank": "A", "power": 490, "hp": 5200, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080689079754812/images.png?ex=6aa96550&is=6aa813d0&hm=962822a973a1e1535007f1597c0c7b468a287ec0f3d212dcf58c7ca1d9a0c5a3&=&format=webp&quality=lossless"},
    17: {"id": 17, "name": "Kasen Ibaraki", "rank": "A", "power": 480, "hp": 4900, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080849083924531/images.png?ex=6aa96576&is=6aa813f6&hm=802e894777a879074a59fa3dcae74394f73523e31d9b9272f19e4aff95ec36aa&=&format=webp&quality=lossless"},
    18: {"id": 18, "name": "Sakuya Izayoi", "rank": "A", "power": 460, "hp": 4500, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549079438719844372/images.png?ex=6aa96426&is=6aa812a6&hm=263f21e095ef7f36f411473590d92012d350ab3e7b8ea13e72a443a0672a719a&=&format=webp&quality=lossless&width=307&height=512"},
    19: {"id": 19, "name": "Marisa Kirisame", "rank": "A", "power": 450, "hp": 4400, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081039660654612/images.png?ex=6aa965a4&is=6aa81424&hm=0ff6e9df5e0d49e483e0560bba442927385b8fa930187276b921012ad16071ad&=&format=webp&quality=lossless"},
    20: {"id": 20, "name": "Youmu Konpaku", "rank": "B", "power": 410, "hp": 4100, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081249036116059/images.png?ex=6aa965d6&is=6aa81456&hm=2dc107dd368c53b9c1a94c54e1cfe4a1d9b7ff6ac224dc830d6c9297d5b19e53&=&format=webp&quality=lossless"},
    21: {"id": 21, "name": "Reisen Udongein Inaba", "rank": "B", "power": 390, "hp": 3900, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081419777577130/images.png?ex=6aa965ff&is=6aa8147f&hm=8948e38a77f4c00d21819a6e34e2fd1a13b1853e4c92886d1e6ac3ccae6afd75&=&format=webp&quality=lossless"},
    22: {"id": 22, "name": "Patchouli Knowledge", "rank": "B", "power": 380, "hp": 3200, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549081654948134994/images.png?ex=6aa96637&is=6aa814b7&hm=7e444589e6db73d24fb53445ea713ddb5e5bcc7c75e58ea91a619a694f0d23eb&=&format=webp&quality=lossless&width=385&height=512"},
    23: {"id": 23, "name": "Cirno", "rank": "B", "power": 300, "hp": 3000, "image": "https://media.discordapp.net/attachments/1533528571509866497/1549080400742195260/images.png?ex=6aa9650c&is=6aa8138c&hm=e3d3d5bf2196f4a3b0fdafcc37063c5ad16897726bdf5514be92b3f3b7719cc4&=&format=webp&quality=lossless"},
    24: {"id": 24, "name": "Hong Meiling", "rank": "C", "power": 260, "hp": 2800, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362028601417869/images.png?ex=6aaa6b55&is=6aa919d5&hm=95498119b7d8e5f7563f28bde4efabe919878bcd40b70bf4037edb73eac009aa&=&format=webp&quality=lossless&width=363&height=512"},
    25: {"id": 25, "name": "Rumia", "rank": "C", "power": 220, "hp": 2200, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362134440485004/images.png?ex=6aaa6b6e&is=6aa919ee&hm=860b0ede2ccf2585fb605cdef8864b141980395e5eee9d3f4f78c5692fa3827b&=&format=webp&quality=lossless&width=361&height=512"},
    26: {"id": 26, "name": "Mystia Lorelei", "rank": "C", "power": 200, "hp": 2000, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362390641020948/84f96d0ce2f04a42a63cff967b6ec6bf.png?ex=6aaa6bab&is=6aa91a2b&hm=9c09d786873a4a70d3dbc27e10934ee7e8463964d89acc42cc1214e29e3185a2&=&format=webp&quality=lossless&width=385&height=512"},
    27: {"id": 27, "name": "Wriggle Nightbug", "rank": "C", "power": 180, "hp": 1800, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362613421351043/images.png?ex=6aaa6be0&is=6aa91a60&hm=56779b03181c9c34cb7de4974bfdc60dc452be7d450818daeaeddbf8f36250d0&=&format=webp&quality=lossless"},
    28: {"id": 28, "name": "Tewi Inaba", "rank": "C", "power": 150, "hp": 1500, "image": "https://media.discordapp.net/attachments/1527157582115111077/1549362906154410034/images.png?ex=6aaa6c26&is=6aa91aa6&hm=ac3b4dca861840ea6c0c5b41288fb528b56543df60081fe62ff774f75449e847&=&format=webp&quality=lossless"},
    "t1": {
        "id": "t1",
        "name": "Seiki đệ pháp toàn năng",
        "rank": "T",
        "power": 695,
        "hp": 7000,
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
    },
    "t2": {
        "id": "t2",
        "name": "Mahoraga Bát ách kiếm thần tướng",
        "rank": "T",
        "power": 550,
        "hp": 7000,
        "image": "https://static2.klipy.com/ii/da290b156d64898341638f3c299e7478/86/35/wnul0BmH.gif",
        "passive": {
            "name": "The True adapt",
            "chance": 1.0,
            "heal_pct": 0.05,
            "damage_reduction_pct": 0.05,
            "desc": "Nội tại 100% kích hoạt: Mỗi turn hồi 5% máu tối đa & mỗi turn giảm 5% sát thương phải nhận (cộng dồn)",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/12/48/UtccMb4buubM.gif"
        },
        "skills": {
            "thoai_ma_kiem": {
                "name": "Thoái Ma kiếm",
                "chance": 0.30,
                "multiplier": 1.5,
                "desc": "Gây ra 1.5x sát thương cho mục tiêu",
                "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/fd/9a/evpBLiollsxMmiF1wK18.gif"
            }
        }
    },
    "t3": {
        "id": "t3",
        "name": "Kizuna the emperor of vampire",
        "rank": "T",
        "power": 780,
        "hp": 7700,
        "image": "https://media.discordapp.net/attachments/1543072032034521228/1555151435237294090/image.png?backend=b2&ex=6abf7b23&is=6abe29a3&hm=046b321ed799b1a5c6266bb195b80de0a345c35fdeb75211aef98176ab00e12a&=&format=webp&quality=lossless",
        "passive": {
            "name": "True vampire",
            "chance": 1.0,
            "heal_pct": 0.05,
            "desc": "True vampire — Hồi 5% máu mỗi lượt"
        },
        "skills": {
            "blood_chain": {
                "name": "Blood chain",
                "chance": 0.30,
                "multiplier": 1.5,
                "desc": "30% gây ra 1.5x sát thương (1 lần/trận)",
                "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/2f/38/H1AP9mdI3CzGLVUrFBF.gif"
            },
            "dark_chain": {
                "name": "Dark chain",
                "chance": 0.20,
                "multiplier": 1.0,
                "max_hp_pct": 0.05,
                "max_uses": 3,
                "desc": "20% gây 1.0x sát thương kèm 5% máu tối đa đối phương (tối đa 3 lần/trận)",
                "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/56/40/iq0ztIh38KLjZwtzI.gif"
            }
        }
    }
}
CARDS_DATA["T1"] = CARDS_DATA["t1"]
CARDS_DATA["T2"] = CARDS_DATA["t2"]
CARDS_DATA["t2"] = CARDS_DATA["t2"]
CARDS_DATA["t4"] = {
    "id": "t4",
    "name": "Fateria – Khuôn mẫu của số phận",
    "rank": "T",
    "power": 680,
    "hp": 7500,
    "image": "https://media.discordapp.net/attachments/1549063334781911070/1556698641002004480/image.png?backend=b2&ex=6ac51c16&is=6ac3ca96&hm=3f8bb669aa03006bbd2fce5b687c6d81a036e8349764d9569f6bd412784446ab&=&format=webp&quality=lossless",
    "unlock_gif": "https://static2.klipy.com/ii/bea85337777ad0e23e63683391435543/95/37/sM6GJwtt.gif",
    "passive": {
        "name": "Save loop",
        "chance": 0.15,
        "heal_pct": 0.50,
        "desc": "15% kích hoạt: Hồi 50% HP tối đa và miễn nhiễm sát thương trong turn đó",
        "gif": "https://static2.klipy.com/ii/e1b92bb53e0c9e442408bc677a56c789/3f/90/YA0o494Vr52yU7U.gif"
    },
    "skills": {
        "fate_loop": {
            "name": "Fate loop",
            "chance": 0.20,
            "turns": 2,
            "max_uses": 2,
            "desc": "20% khiến đối thủ không dùng skill 2 turn liên tiếp (tối đa 2 lần/trận, không lặp lại khi đang hiệu lực)",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/41/a1/shxGKwxeHM5dbAwHKGY.gif"
        },
        "clone_attack": {
            "name": "Clone attack",
            "chance": 0.40,
            "max_uses": 2,
            "desc": "40% kích hoạt (tối đa 2 lần/trận) random 1/3 chiêu con rối: Thunder blaze (2.3x DMG), The fallen hero (1.5x DMG + giảm 30% Heal), Ice spear (1.5x DMG + 40% khóa đánh thường 2 lượt sau)",
            "clones": {
                "thunder_blaze": {
                    "name": "Thunder blaze",
                    "multiplier": 2.3,
                    "gif": "https://static2.klipy.com/ii/39f2394ae36df6e199be9eb7c9fa1012/8d/df/9dfE0xSo.gif"
                },
                "the_fallen_hero": {
                    "name": "The fallen hero",
                    "multiplier": 1.5,
                    "heal_reduce_pct": 0.30,
                    "gif": "https://static2.klipy.com/ii/9294a2e836d178ddc22430dd7765727e/3f/b6/LMzSuK4eAAVA4rh.gif"
                },
                "ice_spear": {
                    "name": "Ice spear",
                    "multiplier": 1.5,
                    "stop_atk_chance": 0.40,
                    "turns": 2,
                    "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/62/60/sPhfFLdL.gif"
                }
            }
        }
    }
}
CARDS_DATA["T3"] = CARDS_DATA["t3"]
CARDS_DATA["t3"] = CARDS_DATA["t3"]
CARDS_DATA["T4"] = CARDS_DATA["t4"]
CARDS_DATA["t4"] = CARDS_DATA["t4"]

T1_SKILL_CONFIGS = CARDS_DATA["t1"]["skills"]
T1_SEAL_GIF = T1_SKILL_CONFIGS["fantasy_seal"]["gif"]
T1_SPARK_GIF = T1_SKILL_CONFIGS["master_spark"]["gif"]
T1_HEAL_GIF = T1_SKILL_CONFIGS["medicine_sign"]["gif"]
T2_PASSIVE_GIF = CARDS_DATA["t2"]["passive"]["gif"]
T2_THOAI_MA_GIF = CARDS_DATA["t2"]["skills"]["thoai_ma_kiem"]["gif"]
T3_BLOOD_GIF = "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/2f/38/H1AP9mdI3CzGLVUrFBF.gif"
T3_DARK_GIF = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/56/40/iq0ztIh38KLjZwtzI.gif"
T3_WONDER_GUARD_GIF = "https://static2.klipy.com/ii/d7aec6f6f171607374b2065c836f92f4/e5/ab/GDt4bKoq.gif"

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
    "hp": 30000,
    "power": 3000,
    "max_players": 6,
    "cooldown_seconds": 15 * 60
}

BOSS_PHASE2_CONFIG = {
    "name": "Reimu Dị Hình - Thức Tỉnh (Phase 2)",
    "desc": "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội!",
    "image": "https://media.discordapp.net/attachments/1549063334781911070/1549275653239472148/artwork.png?ex=6aaa1ae3&is=6aa8c963&hm=7187404882d4b8b0fcef91ef64aee3c73711924e971fb7b28b6fb3bf394a47d3&=&format=webp&quality=lossless&width=640&height=336",
    "hp": 50000,
    "power": 10000
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
    "hp": 30000,
    "power": 3000,
    "passive_regen_pct": 0.015,
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
# SEIKI DỊ HÌNH PHASE 2 - THỨC TỈNH (90K HP, 10K DMG CHIA ĐỀU, NUCLEAR + CLEAVE)
# ==============================================================================
SEIKI_BOSS_PHASE2_CONFIG = {
    "id": "seiki_phase2",
    "name": "Seiki Dị Hình - Thức Tỉnh (Phase 2)",
    "desc": "Dị tà ma lực bùng nổ, thân xác dị hình đang thức tỉnh hoàn toàn!",
    "reimu_quote": "Không thể nào... dị khí còn mạnh gấp bội! Mọi người cẩn thận, ngài ấy đã thức tỉnh rồi!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1550376618160169012/content.png?ex=6ab0bf3e&is=6aaf6dbe&hm=eb9bf84552e0b67e8e03f8ac403af2034904b4b48330bd8cd220f39feb3c11a2&=&format=webp&quality=lossless&width=357&height=512",
    "hp": 90000,
    "power": 10000,
    "skills": {
        "nuclear_spell": {
            "name": "Nuclear Spell Card",
            "chance": 0.15,
            "damage": 10000,
            "desc": "15% kích hoạt, gây 10,000 DMG lên TẤT CẢ lá bài đang ở tiền tuyến!",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/9a/95/QC2Rgxlj7qvePDfZJte.gif"
        },
        "cleave": {
            "name": "Cleave",
            "chance": 1.0,
            "pct": 0.20,
            "desc": "Nội tại THỤ ĐỘNG 100% kích hoạt: Mọi đòn đánh thường gây thêm sát thương chuẩn bằng 20% Máu Tối Đa của mục tiêu!",
            "gif": "https://static2.klipy.com/ii/9ed0121ed465c12e1f3dda331ed33f0e/9b/b3/mOb3k5Ux7HWC.gif"
        }
    }
}

# ==============================================================================
# HALLOWEEN EVENT 2026 CONFIG & EVENT BOSS KIZUNA - HUYẾT MA ĐẾ
# ==============================================================================
EVENT_CONFIG = {
    "id": "halloween_2026",
    "name": "Halloween Event 2026 - Lễ Hội Kẹo Ma Quái",
    "active": True,
    "start_date": "2026-10-02",
    "end_date": "2026-10-30",
    "banner": "https://media.discordapp.net/attachments/1527157582115111077/1555132294170419230/images.png?backend=b2&ex=6abf694f&is=6abe17cf&hm=0da7e8bf9d0062f5711ce6391b3216939b3b641e8743b8a6c707250d849e0bec&=&format=webp&quality=lossless&width=362&height=512",
    "quote": "Marisa: \"Thu thập những mảnh kẹo và đổi lấy phần thưởng nào!\"",
    "quests": {
        "battle": {"target": 100, "name": "Chiến đấu PvE (/battle) 100 lần"},
        "pvp": {"target": 100, "name": "Đại chiến PvP (/pvp) 100 lần"},
        "raid": {"target": 30, "name": "Đánh Boss Raid Thường 30 lần"},
        "event_raid": {"target": 30, "name": "Đánh Event Boss Kizuna 30 lần"}
    },
    "reward": {
        "thanh_loi": 1,
        "tokens": 250
    }
}

# Danh mục Vật phẩm Hỗ trợ Use [E] và Trade
ITEMS_DATABASE = {
    "thanh_loi": {
        "id": "thanh_loi",
        "name": "Thánh Lõi",
        "usable": False,
        "tradeable": True,
        "desc": "Lõi thần thánh dùng để tiến hóa thẻ bài [#t3] Kizuna lên Ace 2 ⭐⭐."
    },
    "keo_halloween": {
        "id": "keo_halloween",
        "name": "Kẹo Halloween 🍬",
        "usable": False,
        "tradeable": True,
        "desc": "Đơn vị tiền tệ sự kiện Halloween 2026, dùng mua đồ trong /event shop."
    },
    "ruong_halloween_e": {
        "id": "ruong_halloween_e",
        "name": "Rương Halloween Ma Quái [E]",
        "usable": True,
        "tradeable": True,
        "desc": "Vật phẩm [E] có thể mở: Nhận ngẫu nhiên 5-15 Vé Pull, 50-100 Kẹo hoặc 1-2 Mảnh Kizuna!"
    },
        "quat_giay": {
        "id": "quat_giay",
        "name": "Quạt Giấy 🪭",
        "usable": False,
        "tradeable": True,
        "desc": "Bảo vật quạt giấy cảnh giới của Yukari Yakumo, dùng để tiến hóa [#04] Yukari lên Ace 2 ⭐⭐."
    }
}

EVENT_BOSS_CONFIG = {
    "id": "kizuna_event",
    "name": "Kizuna - Huyết Ma Đế (Phase 1)",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1555151435237294090/image.png?backend=b2&ex=6abf7b23&is=6abe29a3&hm=046b321ed799b1a5c6266bb195b80de0a345c35fdeb75211aef98176ab00e12a&=&format=webp&quality=lossless",
    "hp": 50000,
    "power": 3000,
    "passive_regen_pct": 0.015, # Hồi 1,5% máu mỗi lượt
    "skills": {
        "blood_chain": {
            "name": "Blood chain",
            "chance": 0.20,
            "multiplier": 1.5,
            "desc": "20% gây 1.5x sát thương (4,500 DMG chia đều cho tiền tuyến)",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/2f/38/H1AP9mdI3CzGLVUrFBF.gif"
        },
        "dark_chain": {
            "name": "Dark chain",
            "chance": 0.20,
            "multiplier": 1.0,
            "pct_hp": 0.15,
            "desc": "20% gây 1x sát thương chia đều kèm 15% Máu Tối Đa cho tất cả các thẻ tiền tuyến",
            "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/56/40/iq0ztIh38KLjZwtzI.gif"
        }
    }
}

EVENT_BOSS_PHASE2_CONFIG = {
    "id": "kizuna_event_phase2",
    "name": "Kizuna - Huyết Ma Đế Thức Tỉnh (Phase 2)",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1555151435237294090/image.png?backend=b2&ex=6abf7b23&is=6abe29a3&hm=046b321ed799b1a5c6266bb195b80de0a345c35fdeb75211aef98176ab00e12a&=&format=webp&quality=lossless",
    "hp": 75000,
    "power": 7000,
    "passive_regen_pct": 0.015,
    "skills": {
        "blood_chain": {
            "name": "Blood chain",
            "chance": 0.20,
            "multiplier": 1.5,
            "desc": "20% gây 1.5x sát thương (9,000 DMG chia đều cho tiền tuyến)",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/2f/38/H1AP9mdI3CzGLVUrFBF.gif"
        },
        "dark_chain": {
            "name": "Dark chain",
            "chance": 0.20,
            "multiplier": 1.0,
            "pct_hp": 0.15,
            "desc": "20% gây 1x sát thương chia đều kèm 15% Máu Tối Đa cho tất cả các thẻ tiền tuyến",
            "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/56/40/iq0ztIh38KLjZwtzI.gif"
        },
        "wonder_guard": {
            "name": "Wonder guard",
            "chance": 0.15,
            "turns": 2,
            "reflect_pct": 0.90,
            "desc": "15% kích hoạt: Miễn toàn bộ sát thương và phản lại 90% sát thương + hiệu ứng của địch trong 2 lượt (không kích hoạt lặp lại khi đang hiệu lực)",
            "gif": "https://static2.klipy.com/ii/d7aec6f6f171607374b2065c836f92f4/e5/ab/GDt4bKoq.gif"
        }
    }
}


# ==============================================================================
# BOSS MAHORAGA - BÁT ÁCH KIẾM THẦN TƯỚNG (90K HP / 6K DMG CHIA ĐỀU / THE TRUE ADAPT)
# ==============================================================================
MAHORAGA_BOSS_CONFIG = {
    "id": "mahoraga",
    "name": "Bát Ách Kiếm Thần Tướng Mahoraga",
    "desc": "Thần tướng thuật thức tối thượng - kẻ thích nghi với mọi hiện tượng. Mọi đòn đánh chỉ khiến nó trở nên cứng cáp hơn!",
    "reimu_quote": "Cái thứ yêu quái nào vậy, cái thằng nhóc đầu nhím kia vừa triệu hồi cái gì vậy?",
    "image": "https://kimi-web-img.kimi.ai/img/gbaike-image.cdn.bcebos.com/84b485484cf2279a8a3412643b2a1c4f99bf0cd2",
    "hp": 90000,
    "power": 6000,
    "passive_regen_pct": 0.03,
    "passive_adapt_pct": 0.03,
    "max_players": 6,
    "cooldown_seconds": 15 * 60,
    "skills": {
        "the_true_adapt": {
            "name": "The True Adapt (Thích Nghi Tuyệt Đối)",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/12/48/UtccMb4buubM.gif",
            "desc": "Nội tại THỤ ĐỘNG 100% kích hoạt: Mỗi hiệp tự hồi phục 3% HP tối đa và GIẢM 3% sát thương phải nhận (cộng dồn mỗi hiệp)!"
        },
        "thoai_ma_kiem": {
            "name": "Thoái Ma Kiếm",
            "chance": 0.25,
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/fd/9a/evpBLiollsxMmiF1wK18.gif",
            "desc": "25% kích hoạt: Gây 1x sát thương (6,000 DMG) lên MỘT mục tiêu duy nhất - sát thương thuần, KHÔNG chia đều!"
        }
    }
}
# ==============================================================================
# BOSS FATERIA – KHUÔN MẪU CỦA SỐ PHẬN (95K HP / 6K2 DMG CHIA ĐỀU)
# ==============================================================================
FATERIA_BOSS_CONFIG = {
    "id": "fateria",
    "name": "Fateria – Khuôn mẫu của số phận",
    "desc": "Thực thể thao túng dòng chảy thời gian và những con rối định mệnh!",
    "reimu_quote": "kẻ kiểm soát dòng chảy của thời gian, tất cả nghênh chiến!",
    "image": "https://media.discordapp.net/attachments/1549063334781911070/1556698641002004480/image.png?backend=b2&ex=6ac51c16&is=6ac3ca96&hm=3f8bb669aa03006bbd2fce5b687c6d81a036e8349764d9569f6bd412784446ab&=&format=webp&quality=lossless",
    "hp": 95000,
    "power": 6200,
    "max_players": 6,
    "cooldown_seconds": 15 * 60,
    "passive": {
        "name": "Save loop",
        "chance": 0.15,
        "heal_pct": 0.30,
        "desc": "15% kích hoạt: Hồi 30% HP tối đa (28,500 HP) và miễn nhiễm toàn bộ sát thương trong turn đó!",
        "gif": "https://static2.klipy.com/ii/e1b92bb53e0c9e442408bc677a56c789/3f/90/YA0o494Vr52yU7U.gif"
    },
    "skills": {
        "fate_loop": {
            "name": "Fate loop",
            "chance": 0.10,
            "turns": 2,
            "desc": "10% khiến đối thủ không thể dùng skill trong 2 turn liên tiếp (không lặp lại cho đến khi hết 2 turn đó)!",
            "gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/41/a1/shxGKwxeHM5dbAwHKGY.gif"
        },
        "clone_attack": {
            "name": "Clone attack",
            "chance": 0.20,
            "clones": {
                "thunder_blaze": {
                    "name": "Thunder blaze",
                    "multiplier": 2.3,
                    "desc": "Những ngọn lửa chớp điện phập phờn gây 2.3x DMG (14,260 DMG) chia đều sát thương!",
                    "gif": "https://static2.klipy.com/ii/39f2394ae36df6e199be9eb7c9fa1012/8d/df/9dfE0xSo.gif"
                },
                "the_fallen_hero": {
                    "name": "The fallen hero",
                    "multiplier": 1.5,
                    "heal_reduce_pct": 0.30,
                    "desc": "Tung trảm kích ánh sáng 1.5x DMG (9,300 DMG) chia đều sát thương và giảm 30% hiệu quả hồi máu (Heal)!",
                    "gif": "https://static2.klipy.com/ii/9294a2e836d178ddc22430dd7765727e/3f/b6/LMzSuK4eAAVA4rh.gif"
                },
                "ice_spear": {
                    "name": "Ice spear",
                    "multiplier": 1.5,
                    "Stop_atk_chance": 0.40,
                    "turns": 2,
                    "desc": "Những ngọn giáo băng 1.5x DMG (9,300 DMG) chia đều khiến đối phương có 40% không thể tấn công trong 2 lượt sau!",
                    "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/62/60/sPhfFLdL.gif"
                }
            }
        }
    }
}        
# ==============================================================================
# CƠ CHẾ TIẾN HÓA ACE 2 (KÈM ID NHÂN VẬT & DIRECT GIF HIỂN THỊ TRỰC TIẾP)
# ==============================================================================
EVOL_CONFIG = {
    15: {
        "id": 15,
        "key": "reimu",
        "name": "Reimu Hakurei",
        "title": "[#15] Reimu Hakurei - Ace 2 ⭐⭐",
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
    18: {
        "id": 18,
        "key": "sakuya",
        "name": "Sakuya Izayoi",
        "title": "[#18] Sakuya Izayoi - Ace 2 ⭐⭐",
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
    19: {
        "id": 19,
        "key": "marisa",
        "name": "Marisa Kirisame",
        "title": "[#19] Marisa Kirisame - Ace 2 ⭐⭐",
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
    },
    12: {
        "id": 12,
        "key": "remilia",
        "name": "Remilia Scarlet",
        "title": "[#12] Remilia Scarlet - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 25,
        "required_pulls": 25,
        "evol_gif": "https://static2.klipy.com/ii/f87f46a2c5aeaeed4c68910815f73eaf/a5/4b/tHDGMmEH.gif",
        "skill_name": "Thương Đỏ Gungnir (Passive - Sát Thương Tối Đa)",
        "skill_desc": "Kỹ năng THỤ ĐỘNG vĩnh viễn (không cần kích hoạt): Mọi đòn đánh đều gây thêm sát thương bằng **3% Máu Tối Đa (Max HP)** của mục tiêu! Hoạt động xuyên suốt trong Raid Boss, Battle & PvP, kèm GIF chiêu thức trực tiếp!",
        "skill_gif": "https://static2.klipy.com/ii/2711dd8a75a85be822d136ec94899b3f/47/43/xa6lynan.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    21: {
        "id": 21,
        "key": "reisen",
        "name": "Reisen Udongein Inaba",
        "title": "[#21] Reisen Udongein Inaba - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 40,
        "required_pulls": 40,
        "evol_gif": "https://static2.klipy.com/ii/f87f46a2c5aeaeed4c68910815f73eaf/ba/a0/ddfDeM6F.gif",
        "skill_name": "Red Eye Mind Explosion (Điều Khiển Tâm Trí)",
        "skill_desc": "Kích hoạt 1 lần duy nhất trong trận (Tỷ lệ 25%): Gây ảo giác tâm lý khiến mục tiêu bị chọn có **20% tỷ lệ tự gây sát thương lên bản thân** sau mỗi lượt (không thể dùng lên chính mình). Hiệu ứng tồn tại trong **4 turn**, kèm GIF chiêu thức trực tiếp!",
        "skill_gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/4d/a6/qKiFSu8x.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    23: {
        "id": 23,
        "key": "cirno",
        "name": "Cirno",
        "title": "[#23] Cirno - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 60,
        "required_pulls": 60,
        "evol_gif": "https://static2.klipy.com/ii/4e7bea9f7a3371424e6c16ebc93252fe/3e/e0/xSNtB708MaDM.gif",
        "skill_name": "Perfect Freeze (Băng Đóng Tuyệt Đối)",
        "skill_desc": "Kích hoạt 1 lần trong trận (Tỷ lệ 40%): Khiến đối phương bị đóng băng dẫn đến trong 2 turn tiếp theo có 45% không thể đánh trả, kèm GIF chiêu thức trực tiếp!",
        "skill_gif": "https://static2.klipy.com/ii/e293a233a303a98e471f78d04e13a1b0/c3/f4/HRq1eslb.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    13: {
        "id": 13,
        "key": "utsuho",
        "name": "Utsuho Reiuji (Okuu)",
        "title": "[#13] Utsuho Reiuji - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 30,
        "required_pulls": 30,
        "evol_gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/06/9b/o5Pa7BgCiYHgJEb.gif",
        "skill_name": "Nuclear Spell Card (Hạch Tâm Bộc Phá)",
        "skill_desc": "30% kích hoạt: Gây ra 3.0x sát thương và khiến mặt đất nung chảy gây bỏng 2% Máu Tối Đa cho những lá bài địch ra sân sau đó trong 3 turn thì mặt đất sẽ bình thường trở lại, kèm GIF chiêu thức trực tiếp!",
        "skill_gif": "https://static2.klipy.com/ii/d7aec6f6f171607374b2065c836f92f4/5a/61/6mcQnspY.gif",
        "bonus_power": 300,
        "bonus_hp": 300
    },
    4: {
        "id": 4,
        "key": "yukari",
        "name": "Yukari Yakumo",
        "title": "[#04] Yukari Yakumo - Ace 2 ⭐⭐",
        "ace_level": "Ace 2 ⭐⭐",
        "required_cards": 10,
        "required_item": "quat_giay",
        "evol_gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/d8/aa/WN8D1IccKr8iW.gif",
        "skill_name": "Trip To The Old Station • Last Word • Invisible Gap",
        "skill_desc": (
            "🌌 **Trip To The Old Station (30%):** Gây sát thương ×2.0 (1 lần/trận).\n"
            "👁️ **⸮⸮⸮ : Last Word ! (25%):** Gây sát thương ×2.5 và STUN đóng băng đối thủ 1 turn (1 lần/trận).\n"
            "🌀 **Invisible Gap (Nội Tại - 10%):** Phản lại 100% sát thương đòn đánh thường của kẻ địch (không chặn kỹ năng)."
        ),
        "bonus_power": 300,
        "bonus_hp": 300
    }
}
EVOL_CONFIG["4"] = EVOL_CONFIG[4]
EVOL_CONFIG["15"] = EVOL_CONFIG[15]
EVOL_CONFIG["18"] = EVOL_CONFIG[18]
EVOL_CONFIG["19"] = EVOL_CONFIG[19]
EVOL_CONFIG["9"] = EVOL_CONFIG[9]
EVOL_CONFIG["12"] = EVOL_CONFIG[12]
EVOL_CONFIG["21"] = EVOL_CONFIG[21]
EVOL_CONFIG["23"] = EVOL_CONFIG[23]
EVOL_CONFIG["13"] = EVOL_CONFIG[13]

# ==============================================================================
# ACE 2 MỚI: [#t1] SEIKI ĐỆ NHẤT PHÁP SƯ (BỘ KỸ NĂNG THAY ĐỔI HOÀN TOÀN)
# ==============================================================================
T1_ACE2_CONFIG = {
    "required_ace2": [19, 15, 18],   # [#19] Marisa, [#15] Reimu, [#18] Sakuya phải đạt Ace 2
    "required_shards": 10,           # Chi phí: 10 Mảnh Seiki
    "cleave_pct": 0.02,              # Clave (thụ động 100%): đánh thường +2% Máu Tối Đa mục tiêu
    "gif_cleave": "https://static2.klipy.com/ii/9ed0121ed465c12e1f3dda331ed33f0e/9b/b3/mOb3k5Ux7HWC.gif",
    "medicine_sign": {
        "chance": 0.35, "heal_pct": 0.40,  # 35% kích hoạt, hồi 40% Máu tối đa bản thân, 1 lần/trận
        "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/8d/12/mwVdJaFQsefrsAuNS.gif"
    },
    "fantasy_seal": {
        "chance": 0.50,                # 50% kích hoạt 1 lần/trận: Miễn toàn bộ sát thương (buff lên 50% ở dạng Ace 2)
        "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/e7/fe/JOKpsPyd.gif"
    },
    "bong_khai_niem": {
        "chance": 0.20, "multiplier": 1.5, "dmg_pct": 0.10,  # 20% kích hoạt 1 lần/trận: 1.5x sát thương + 10% Máu Tối Đa + xóa kỹ năng đối phương
        "gif": "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/38/ec/4v5klqIf3v2WuSLgB.gif"
    }
}

EVOL_CONFIG["t1"] = {
    "id": "t1",
    "key": "seiki",
    "name": "Seiki Đệ Pháp Toàn Năng",
    "title": "[#t1] Seiki Đệ Nhất Pháp Sư - Ace 2 ⭐⭐",
    "ace_level": "Ace 2 ⭐⭐",
    "required_cards": 0,
    "required_pulls": 0,
    "required_shards": 10,
    "evol_gif": "https://static2.klipy.com/ii/2f34308bfc69e8c858753b83566e3ab4/00/52/j3kSrYrla8BSqcCal.gif",
    "skill_name": "Tứ Đại Tuyệt Kỹ Thức Tỉnh (Cleave • Medicine Sign • Fantasy Seal • Bóng Khái Niệm)",
    "skill_desc": (
        "🪓 **Cleave (Nội Tại - 100%):** Mọi đòn đánh thường gây thêm **2% Máu Tối Đa** của mục tiêu! "
        "💚 **Medicine Sign (35%):** Hồi phục **40% Máu Tối Đa** cho bản thân, 1 lần/trận. "
        "🛡️ **Fantasy Seal (50%):** Dựng kết giới phong ấn, **MIỄN TOÀN BỘ SÁT THƯƠNG** trong 1 hiệp (đã buff lên 50% ở dạng Ace 2), 1 lần/trận. "
        "🌑 **Bóng Khái Niệm (20%):** Gây **×1.5 Sát Thương** kèm **10% Máu Tối Đa** mục tiêu và **lập tức xóa kỹ năng của đối phương**, 1 lần/trận."
    ),
    "bonus_power": 300,
    "bonus_hp": 300
}

T3_ACE2_CONFIG = {
    "required_item": "thanh_loi",     # Yêu cầu vật phẩm Thánh Lõi
    "wonder_guard": {
        "chance": 0.20,
        "turns": 3,
        "reflect_pct": 0.60,
        "gif": T3_WONDER_GUARD_GIF,
        "desc": "20% kích hoạt: Miễn thương và phản lại 60% sát thương lẫn hiệu ứng trong 3 turn (1 lần/trận)"
    },
    "blood_chain": {
        "chance": 0.30,
        "multiplier": 2.0,
        "gif": T3_BLOOD_GIF,
        "desc": "30% gây 2.0x sát thương (1 lần/trận)"
    },
    "dark_chain": {
        "chance": 0.30,
        "multiplier": 1.5,
        "max_hp_pct": 0.05,
        "max_uses": 3,
        "gif": T3_DARK_GIF,
        "desc": "30% gây 1.5x sát thương kèm 5% máu tối đa đối phương (tối đa 3 lần/trận)"
    }
}

EVOL_CONFIG["t3"] = {
    "id": "t3",
    "key": "kizuna",
    "name": "Kizuna the emperor of vampire",
    "title": "[#t3] Kizuna the emperor of vampire - Ace 2 ⭐⭐",
    "ace_level": "Ace 2 ⭐⭐",
    "required_cards": 0,
    "required_pulls": 0,
    "required_item": "thanh_loi",
    "evol_gif": "https://static2.klipy.com/ii/d6b0ce929193df3c242ac34b5654d2ce/a2/4a/5wVVGJlo.gif",
    "skill_name": "True Vampire Thức Tỉnh (Wonder Guard • Blood Chain 2x • Dark Chain 1.5x)",
    "skill_desc": (
        "🩸 **True vampire (Nội tại):** Hồi 5% máu mỗi lượt.\n"
        "🛡️ **Wonder guard (20%):** Miễn thương & phản 60% sát thương + hiệu ứng địch trong 3 turn (1 lần/trận).\n"
        "💥 **Blood chain (30%):** Gây **2.0x sát thương** (1 lần/trận).\n"
        "🌑 **Dark chain (30%):** Gây **1.5x sát thương** + **15% Máu Tối Đa** mục tiêu (tối đa 3 lần/trận)."
    ),
    "bonus_power": 300,
    "bonus_hp": 300
}

# ==============================================================================
# 3.1 CHI TIẾT NĂNG LỰC & KỸ NĂNG 27 NHÂN VẬT TOUHOU (CHO TÍNH NĂNG CHECK NHÂN VẬT)
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
    10: {"title": "Tiểu Thư Tâm Trí Khép Kín", "skill_name": "Tâm Linh Cảm Ứng (Subconscious)", "skill_desc": "Em gái của Satori Komeiji, tự khép kín trái tim để thoát khỏi sự dị nghị của thế gian. Lướt đi vô thức khắp Gensokyo và tung những đòn đánh lén từ tiềm thức mà không một ai kịp lường trước (600 ATK / 6,060 HP)."},
    11: {"title": "Công Chúa Ánh Trăng", "skill_name": "Vĩnh Cửu & Tức Thời", "skill_desc": "Công chúa Nguyệt Cung lưu đày tại Eientei, điều khiển dòng chảy thời gian vĩnh cửu và tức thời cùng thần bảo quý giá (590 ATK / 6,400 HP)."},
    12: {"title": "Chúa Tể Hồng Ma Quán", "skill_name": "Thương Đỏ Gungnir (Vận Mệnh)", "skill_desc": "Ma cà rồng kiêu hãnh bẻ cong số mệnh kẻ thù, phóng ra ngọn giáo ánh sáng đỏ Gungnir xuyên thủng phòng ngự (560 ATK / 5,600 HP). [Ace 2 ⭐⭐]: Thương Đỏ Gungnir — kỹ năng THỤ ĐỘNG không cần kích hoạt: mọi đòn đánh gây thêm sát thương bằng 3% Máu Tối Đa (Max HP) của mục tiêu!"},
    13: {"title": "Mặt Trời Địa Ngục", "skill_name": "Hạch Tâm Phản Ứng (Nuclear)", "skill_desc": "Mang sức mạnh thần mặt trời Yatagarasu, thi triển hạch tâm nhiệt hạch thiêu đốt toàn bộ chiến trường (550 ATK / 5,300 HP). [Ace 2 ⭐⭐]: Nuclear Spell Card (30%) — Gây 3.0x sát thương và khiến mặt đất nung chảy gây bỏng 2% Máu Tối Đa cho những lá bài địch ra sân sau đó trong 3 turn!"},
    14: {"title": "Cánh Tay Quỷ Bị Phong Ấn", "skill_name": "Quỷ Khí Trảm Thiết", "skill_desc": "Cánh tay phải bị chém đứt của Đại Quỷ Ibaraki-Douji, ẩn chứa ma lực quỷ giới cuồng bạo và sức công phá kinh thiên động địa (500 ATK / 4,800 HP)."},
    15: {"title": "Vu Nữ Đền Hakurei", "skill_name": "Bùa Chú Vô Tưởng Chuyển Sinh", "skill_desc": "Bay lượn khỏi thực tại và trừ tà ma thuật. [Ace 2 ⭐⭐]: Miễn toàn bộ sát thương 1 lần trong trận (Tỷ lệ đồng nhất 40% cả trong Raid Boss và Battle/PvP)!"},
    16: {"title": "Phượng Hoàng Bất Tử", "skill_name": "Phượng Hoàng Bất Diệt", "skill_desc": "Cơ thể bất tử do uống tiên dược Hourai, triệu hồi ngọn lửa phượng hoàng thiêu đốt kẻ địch mà không hề sợ chết (490 ATK / 5,200 HP)."},
    17: {"title": "Tiên Nhân Một Tay", "skill_name": "Thần Thú Giáng Lâm", "skill_desc": "Một trong Tứ Thiên Vương ẩn mình dưới thân phận tiên nhân dạy dỗ yêu quái và điều khiển muôn loài linh thú (480 ATK / 4,900 HP)."},
    18: {"title": "Hầu Gái Trưởng Hoàn Hảo", "skill_name": "Thời Gian Đóng Băng", "skill_desc": "Bậc thầy phi dao bạc và không-thời gian. [Ace 2 ⭐⭐]: Đóng băng thời gian làm đối thủ/boss bị STUN mất lượt 1 lần trong trận (Tỷ lệ đồng nhất 40% cả trong Raid Boss và Battle/PvP)!"},
    19: {"title": "Phù Thủy Bình Thường", "skill_name": "Bát Quái Lô - Master Spark", "skill_desc": "Ma thuật ánh sáng và nhiệt độ cao. [Ace 2 ⭐⭐]: Bắn đại bác ma thuật Master Spark gây sát thương ×2.0 lần sát thương gốc (Tỷ lệ 30% 1 lần trong trận)!"},
    20: {"title": "Kiếm Sĩ Nửa Người Nửa Ma", "skill_name": "Song Kiếm Lâu Quan & Bạch Lâu", "skill_desc": "Thần tốc kiếm đạo: Lâu Quan Kiếm chém vạn vật và Bạch Lâu Kiếm chém tan ảo tưởng mê muội (410 ATK / 4,100 HP)."},
    21: {"title": "Thỏ Ngọc Chiến Binh", "skill_name": "Hồng Nhãn Cuồng Loạn", "skill_desc": "Thỏ ngọc từ Mặt Trăng phát sóng ảo giác từ ánh mắt đỏ rực làm hoa mắt và rối loạn phương hướng đối phương (390 ATK / 3,900 HP). [Ace 2 ⭐⭐]: Red Eye Mind Explosion (25%, 1 lần/trận) — mục tiêu bị chọn có 20% tỷ lệ tự gây sát thương lên bản thân sau mỗi lượt (không dùng lên chính mình), hiệu ứng tồn tại 4 turn!"},
    22: {"title": "Đại Ma Đạo Sĩ Thất Diệu", "skill_name": "Thất Diệu Ma Thuật", "skill_desc": "Phù thủy thông thái trong thư viện ngầm, kết hợp 7 nguyên tố tự nhiên tạo thành ma trận công thủ liên hoàn (380 ATK / 3,200 HP)."},
    23: {"title": "Đệ Nhất Băng Tiên", "skill_name": "Perfect Freeze (Băng Đạn)", "skill_desc": "Tiên tử băng giá mạnh nhất Hồ Sương Mù, đóng băng mọi vật thể và phóng mưa mảnh băng sắc nhọn (300 ATK / 3,000 HP). [Ace 2 ⭐⭐]: Perfect Freeze (40%) — 1 lần trong trận khiến đối phương đóng băng, trong 2 turn tiếp theo có 45% không thể đánh trả!"},
    24: {"title": "Thủ Môn Hồng Ma Quán", "skill_name": "Thái Cực Khí Công Quyền", "skill_desc": "Nữ võ sư tinh thông thể thuật khí công ngũ sắc, tạo rào chắn phòng thủ kiên cố bảo vệ tiền tuyến (260 ATK / 2,800 HP)."},
    25: {"title": "Yêu Quái Hoàng Hôn", "skill_name": "Dạ Tối Kết Giới", "skill_desc": "Yêu quái bóng đêm bao bọc mình trong vòm đêm thuần túy, tung những đòn cắn xé bất ngờ từ bóng tối (220 ATK / 2,200 HP)."},
    26: {"title": "Dạ Tước Huyễn Ca", "skill_name": "Huyễn Ca Dạ Manh", "skill_desc": "Giọng hát chim đêm mê hoặc khiến đối thủ bị chứng quáng gà và suy giảm độ chính xác đòn đánh (200 ATK / 2,000 HP)."},
    27: {"title": "Đom Đóm Phát Quang", "skill_name": "Đom Đóm Lôi Triệu", "skill_desc": "Điều khiển hàng triệu côn trùng dạ quang tạo nên biển ánh sáng mê ảo làm hoa mắt đối thủ (180 ATK / 1,800 HP)."},
    28: {"title": "Thỏ Rừng May Mắn", "skill_name": "Vận May Thần Tài", "skill_desc": "Thủ lĩnh thỏ rừng Inaba tinh nghịch, ban phát vận may cực lớn cho bản thân và đồng đội (150 ATK / 1,500 HP)."},
    "t1": {
        "title": "Dị Tà Đệ Nhất Pháp Sư (Nhóm T-Đặc Biệt)",
        "skill_name": "Tam Đại Tuyệt Kỹ (Fantasy Seal • Master Spark • Medicine Sign)",
        "skill_desc": "Thẻ bài thần thoại nhóm T. Bản thường: Fantasy Seal (40% miễn thương), Master Spark (30% ×1.5), Medicine Sign (20% hồi phục). [Ace 2 ⭐⭐ - Kỹ năng thay đổi]: 🪓 Cleave (thụ động 100%: mọi đòn đánh +2% Máu Tối Đa mục tiêu) • 💚 Medicine Sign (35% hồi 40% Máu, 1 lần/trận) • 🛡️ Fantasy Seal (50% miễn toàn bộ sát thương 1 hiệp, buff lên 50% ở dạng Ace 2, 1 lần/trận) • 🌑 Bóng Khái Niệm (20%: 1.5x sát thương + 10% Máu Tối Đa + xóa kỹ năng đối phương, 1 lần/trận)."
    },
    "t2": {
        "title": "Bát Ách Kiếm Thần Tướng (Nhóm T-Đặc Biệt)",
        "skill_name": "The True adapt • Thoái Ma Kiếm",
        "skill_desc": "Thần tướng thuật thức tối thượng Mahoraga nhóm T. Nội tại The True adapt (100% kích hoạt): Mỗi turn hồi 5% Máu tối đa và giảm 5% sát thương phải nhận (cộng dồn mỗi lượt). Tuyệt kỹ Thoái Ma kiếm (30% kích hoạt): Gây 1.5x sát thương cho mục tiêu (550 ATK / 7,000 HP)."
    },
    "t3": {
        "title": "Hoàng Đế Ma Cà Rồng (Nhóm T-Đặc Biệt)",
        "skill_name": "True vampire • Blood chain • Dark chain • Wonder guard",
        "skill_desc": "Thẻ bài T3 Kizuna the emperor of vampire (780 ATK / 7,700 HP). Nội tại True vampire (hồi 5% HP mỗi lượt). Blood chain (30%: 1.5x sát thương, 1 lần), Dark chain (20%: 1.0x sát thương + 5% Max HP mục tiêu, tối đa 3 lần). [Ace 2 ⭐⭐ - Cần vật phẩm Thánh Lõi]: Blood chain tăng lên 2.0x, Dark chain tăng lên 1.5x + 15% Max HP, mở khóa Wonder guard (20%: miễn thương & phản 60% sát thương + hiệu ứng trong 3 turn, 1 lần/trận)!"
    }
}
CHARACTER_DETAILS["T1"] = CHARACTER_DETAILS["t1"]
CHARACTER_DETAILS["T2"] = CHARACTER_DETAILS["t2"]
CHARACTER_DETAILS["t4"] = {
    "title": "Khuôn Mẫu Của Số Phận (Nhóm T-Đặc Biệt)",
    "skill_name": "Save loop • Fate loop • Clone attack",
    "skill_desc": (
        "Thẻ bài T4 Fateria – Khuôn mẫu của số phận (680 ATK / 7,500 HP). Mở khóa bằng 20 Fateria Shards.\n"
        "• 🔄 **Passive - Save loop (15%):** Hồi 50% HP tối đa và miễn nhiễm sát thương trong turn đó.\n"
        "• ⛓️ **Skill 1 - Fate loop (20%):** Khiến đối thủ không thể dùng skill 2 turn liên tiếp (tối đa 2 lần/trận).\n"
        "• 🪆 **Skill 2 - Clone attack (40%):** Random 1/3 chiêu con rối (tối đa 2 lần/trận): Thunder blaze (2.3x DMG), The fallen hero (1.5x DMG + giảm 30% Heal), Ice spear (1.5x DMG + 40% không tấn công trong 2 lượt sau)."
    )
}
CHARACTER_DETAILS["T3"] = CHARACTER_DETAILS["t3"]
CHARACTER_DETAILS["t3"] = CHARACTER_DETAILS["t3"]
CHARACTER_DETAILS["T4"] = CHARACTER_DETAILS["t4"]
CHARACTER_DETAILS["t4"] = CHARACTER_DETAILS["t4"]

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
        "tokens": 0,
        "prestige": 0,
        "free_pulls_date": "",
        "free_pulls_remaining": 5,
        "last_daily_date": "",
        "inventory": {},
        "pull_stats": {},
        "unlocked_cards": [],
        "locked_cards": [],
        "evolutions": {},
        "team": [],
        "shards": {
            "seiki": 0,
            "mahoraga": 0,
            "kizuna": 0,
            "fateria": 0,
            "thanh_loi": 0
        },
        "items": {
            "thanh_loi": 0,
            "keo_halloween": 0,
            "ruong_halloween_e": 0,
            "quat_giay": 0
        },
        "event_progress": {
            "battle": 0,
            "pvp": 0,
            "raid": 0,
            "event_raid": 0,
            "claimed": False
        },
        "last_event_raid_time": 0.0,
        "language": "vi",
        "id_schema": 3,
        "battles_won": 0,
        "battles_total": 0,
        "last_battle_time": 0.0,
        "recent_opponents": [],
        "tutorial": {
            "active": True,
            "step": "pull",
            "quest_pulls_remaining": 3,
            "pull_used": False,
            "completed": False
        },
        "daily_quests": {
            "date": "",
            "quests": [],
            "all_completed_claimed": False
        },
        "story": {
            "current_stage": 0,
            "battles_done": 0,
            "quest_claimed": False,
            "rumia_boss_level": None,
            "stage1_completed": False,
            "stage2_quiz_passed": False,
            "stage2_battles_done": 0,
            "stage2_quest_claimed": False,
            "cirno_boss_level": None,
            "stage2_completed": False
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

def update_event_quest_progress(player: dict, quest_type: str, amount: int = 1) -> list:
    """Cập nhật tiến trình nhiệm vụ sự kiện Halloween 2026.
    Trả về danh sách các thông báo (str) nếu có nhiệm vụ hoặc toàn bộ sự kiện hoàn thành."""
    if not EVENT_CONFIG.get("active", True):
        return []
        
    ep = player.setdefault("event_progress", {
        "battle": 0,
        "pvp": 0,
        "raid": 0,
        "event_raid": 0,
        "claimed": False
    })
    
    if ep.get("claimed", False):
        return []
        
    notifs = []
    quests = EVENT_CONFIG.get("quests", {})
    if quest_type not in quests:
        return []
        
    target = quests[quest_type]["target"]
    name = quests[quest_type]["name"]
    
    old_val = ep.get(quest_type, 0)
    if old_val < target:
        new_val = min(target, old_val + amount)
        ep[quest_type] = new_val
        if new_val >= target:
            notifs.append(f"🎃 **Hoàn thành Nhiệm vụ Sự kiện:** *{name}* ({target}/{target})! 🎉")
            
        # Kiểm tra xem toàn bộ 4 nhiệm vụ đã hoàn thành chưa
        all_done = True
        for qkey, qcfg in quests.items():
            if ep.get(qkey, 0) < qcfg["target"]:
                all_done = False
                break
                
        if all_done and not ep.get("claimed", False):
            ep["claimed"] = True
            
            # Phát quà: 1 Thánh Lõi + 250 Tokens
            p_items = player.setdefault("items", {})
            p_items["thanh_loi"] = p_items.get("thanh_loi", 0) + 1
            player["tokens"] = player.get("tokens", 0) + 250
            
            # Đồng bộ sang shards
            p_shards = player.setdefault("shards", {})
            p_shards["thanh_loi"] = p_items["thanh_loi"]
            
            notifs.append(
                "👑 **HOÀN THÀNH TOÀN BỘ 4/4 NHIỆM VỤ SỰ KIỆN HALLOWEEN 2026!**\n"
                "🎁 Nhận ngay phần thưởng tối thượng: **+1 Thánh Lõi** 🌟 và **+250 Tokens** 💎!"
            )
            
    return notifs

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
    "kaguya": 11, "houraisan": 11,
    "remilia": 12, "remi": 12,
    "utsuho": 13, "okuu": 13, "reiuji": 13,
    "arm": 14, "ibaraki_arm": 14, "canhtay": 14,
    "reimu": 15, "hakurei": 15,
    "mokou": 16, "fujiwara": 16,
    "kasen": 17, "ibaraki": 17,
    "sakuya": 18, "izayoi": 18,
    "marisa": 19, "kirisame": 19,
    "youmu": 20, "konpaku": 20,
    "reisen": 21, "udongein": 21, "udonge": 21,
    "patchouli": 22, "patchy": 22, "knowledge": 22,
    "cirno": 23,
    "meiling": 24, "hong": 24,
    "rumia": 25,
    "mystia": 26, "lorelei": 26,
    "wriggle": 27, "nightbug": 27,
    "tewi": 28,
    "koishi": 10, "komeiji": 10,
    "seiki": "t1", "t1": "t1", "dephap": "t1", "toannang": "t1",
    "mahoraga": "t2", "t2": "t2", "batach": "t2",
    "kizuna": "t3", "t3": "t3", "vampire": "t3", "emperor": "t3",
    "fateria": "t4", "t4": "t4", "khuonmau": "t4", "sophan": "t4"
}

def normalize_card_id(raw_id):
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
        data["shards"] = {"seiki": 0, "mahoraga": 0, "kizuna": 0, "fateria": 0, "thanh_loi": 0}
    else:
        data["shards"].setdefault("seiki", 0)
        data["shards"].setdefault("mahoraga", 0)
        data["shards"].setdefault("kizuna", 0)
        data["shards"].setdefault("fateria", 0)
        data["shards"].setdefault("thanh_loi", 0)

    if "items" not in data or not isinstance(data.get("items"), dict):
        data["items"] = {"thanh_loi": 0, "keo_halloween": 0, "ruong_halloween_e": 0, "quat_giay": 0}
    else:
        data["items"].setdefault("thanh_loi", 0)
        data["items"].setdefault("keo_halloween", 0)
        data["items"].setdefault("ruong_halloween_e", 0)
        data["items"].setdefault("quat_giay", 0)

    if "event_progress" not in data or not isinstance(data.get("event_progress"), dict):
        data["event_progress"] = {"battle": 0, "pvp": 0, "raid": 0, "event_raid": 0, "claimed": False}
    if "last_event_raid_time" not in data:
        data["last_event_raid_time"] = 0.0
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
    if "story" not in data or not isinstance(data.get("story"), dict):
        data["story"] = {
            "current_stage": 0, "battles_done": 0, "quest_claimed": False, "rumia_boss_level": None, "stage1_completed": False,
            "stage2_quiz_passed": False, "stage2_battles_done": 0, "stage2_quest_claimed": False, "cirno_boss_level": None, "stage2_completed": False
        }
    else:
        data["story"].setdefault("stage2_quiz_passed", False)
        data["story"].setdefault("stage2_battles_done", 0)
        data["story"].setdefault("stage2_quest_claimed", False)
        data["story"].setdefault("cirno_boss_level", None)
        data["story"].setdefault("stage2_completed", False)
    if "tokens" not in data:
        data["tokens"] = 0
    if "prestige" not in data:
        data["prestige"] = 0
    
    # ===== HỆ THỐNG DI TRÚ ID SCHEMA 3: THÊM [#14] IBARAKI-DOUJI'S ARM (ĐẨY 14-27 LÊN 15-28) =====
    if data.get("id_schema", 1) < 3:
        if data.get("id_schema", 1) < 2:
            def _migrate_v2(k):
                try:
                    ik = int(k)
                    if 10 <= ik <= 26: return str(ik + 1)
                except Exception: pass
                return str(k)
            data["inventory"] = {_migrate_v2(k): v for k, v in data.get("inventory", {}).items()}
            data["pull_stats"] = {_migrate_v2(k): v for k, v in data.get("pull_stats", {}).items()}
            data["evolutions"] = {_migrate_v2(k): v for k, v in data.get("evolutions", {}).items()}
            data["unlocked_cards"] = [int(_migrate_v2(x)) if str(_migrate_v2(x)).isdigit() else _migrate_v2(x) for x in data.get("unlocked_cards", [])]
            data["locked_cards"] = [int(_migrate_v2(x)) if str(_migrate_v2(x)).isdigit() else _migrate_v2(x) for x in data.get("locked_cards", [])]
            data["team"] = [int(_migrate_v2(x)) if str(_migrate_v2(x)).isdigit() else _migrate_v2(x) for x in data.get("team", [])]

        def _migrate_v3(k):
            try:
                ik = int(k)
                if 14 <= ik <= 27: return str(ik + 1)
            except Exception: pass
            return str(k)

        data["inventory"] = {_migrate_v3(k): v for k, v in data.get("inventory", {}).items()}
        data["pull_stats"] = {_migrate_v3(k): v for k, v in data.get("pull_stats", {}).items()}
        data["evolutions"] = {_migrate_v3(k): v for k, v in data.get("evolutions", {}).items()}
        data["unlocked_cards"] = [int(_migrate_v3(x)) if str(_migrate_v3(x)).isdigit() else _migrate_v3(x) for x in data.get("unlocked_cards", [])]
        data["locked_cards"] = [int(_migrate_v3(x)) if str(_migrate_v3(x)).isdigit() else _migrate_v3(x) for x in data.get("locked_cards", [])]
        data["team"] = [x for x in [int(_migrate_v3(x)) if str(_migrate_v3(x)).isdigit() else _migrate_v3(x) for x in data.get("team", [])] if x in CARDS_DATA]
        data["id_schema"] = 3
        save_player(data)

    ensure_daily_quests(data)

    if is_new:
        data["_is_first_time"] = True

    if data.get("free_pulls_date") != now_date:
        data["free_pulls_date"] = now_date
        data["free_pulls_remaining"] = 5

    data["level"] = calculate_level_from_xp(data.get("xp", 0), data.get("prestige", 0))
    return data

def save_player(player_data):
    uid_str = str(player_data["user_id"])
    now_iso = datetime.now().isoformat()
    player_data["level"] = calculate_level_from_xp(player_data.get("xp", 0), player_data.get("prestige", 0))
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
# 7. SỰ KIỆN BOT ON_READY & ON_MESSAGE (ĐÃ SỬA CHUẨN 3% CHAT SPAWN BOSS + COOLDOWN 15P)
# ==============================================================================
@bot.event
async def on_ready():
    print(f"==================================================", flush=True)
    print(f"✅ Bot đã đăng nhập thành công: {bot.user.name} ({bot.user.id})", flush=True)
    print(f"⛩️ Sẵn sàng phục vụ tại Đền Hakurei!", flush=True)
    print(f"==================================================", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Đã tự động đồng bộ {len(synced)} Slash Commands!", flush=True)
    except Exception as e:
        print(f"⚠️ Lỗi đồng bộ Slash Commands: {e}", flush=True)

@bot.event
async def on_message(message: discord.Message):
    # 1. Bỏ qua tin nhắn từ Bot
    if message.author.bot:
        return

    # 2. Xử lý các lệnh prefix (!pull, !daily, !battle, !boss,...)
    await bot.process_commands(message)

    # 3. TỶ LỆ 3% XUẤT HIỆN BOSS TỰ NHIÊN CHO MỌI TIN NHẮN TRONG SERVER (NẾU HẾT HỒI CHIÊU 15P)
    global boss_cooldown_until, active_raid
    now = time.time()
    if active_raid is None and now >= boss_cooldown_until:
        # Tỉ lệ 3% khi có bất kỳ ai chat (0.03)
        if random.random() < 0.03:
            print(f"🚨 [BOSS EVENT] Kích hoạt xuất hiện Boss ngẫu nhiên tại #{message.channel.name} do {message.author.display_name} chat!", flush=True)
            await spawn_boss_raid(message.channel)
            return

    # 4. Kiểm tra người dùng có gọi / tag Reimu để trò chuyện AI không
    content_lower = message.content.lower()
    is_mentioned = bot.user in message.mentions or (message.reference and message.reference.resolved and getattr(message.reference.resolved, "author", None) == bot.user)
    bot_names = ["reimu", "hakurei", "linh mộng", "bác lệ", "bác lệ linh mộng"]
    name_called = any(name in content_lower for name in bot_names)

    # Nếu không gọi Reimu thì dừng lại tại đây (không gọi Gemini AI)
    if not (is_mentioned or name_called):
        return

    # 5. In Log trò chuyện ra console
    print(f"📩 [CHAT IN #{message.channel}] {message.author.display_name} ({message.author.id}): {message.content}", flush=True)

    # 6. Xử lý nội dung gửi đến Gemini Flash AI
    clean_content = message.content
    if bot.user:
        clean_content = clean_content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

    if not clean_content:
        clean_content = "Ngươi gọi ta có chuyện gì? Mau bỏ tiền vào hòm công đức rồi nói!"

    is_father = (message.author.id == AUTHORIZED_ADMIN_ID or "seiki" in message.author.display_name.lower())
    history = get_conversation_history(message.channel.id, message.author.id)
    
    prompt_with_context = (
        f"[Thông tin người nói: Tên '{message.author.display_name}', "
        f"{'ĐÂY LÀ BỐ HAN SEIKI CỦA BẠN - HÃY NGOAN NGOÃN VÀ HIẾU THẢO!' if is_father else 'Đây là khách viếng đền bình thường'}]\n"
        f"Nội dung: {clean_content}"
    )

    contents = []
    for h in history:
        if isinstance(h, dict):
            r = h.get("role", "user")
            t = h.get("text", "")
            if t:
                contents.append({"role": r, "parts": [{"text": t}]})
        elif isinstance(h, str) and h.strip():
            # Tự động tương thích với dữ liệu chuỗi cũ trong Database
            contents.append({"role": "user", "parts": [{"text": h.strip()}]})

    contents.append({"role": "user", "parts": [{"text": prompt_with_context}]})

    async with message.channel.typing():
        try:
            reply_text = await ask_gemini(contents, REIMU_SYSTEM_PROMPT, temperature=0.85)
            history.append({"role": "user", "text": clean_content})
            history.append({"role": "model", "text": reply_text})
            save_conversation_history(message.channel.id, message.author.id, history)

            if len(reply_text) > 2000:
                for chunk in [reply_text[i:i+1900] for i in range(0, len(reply_text), 1900)]:
                    await message.reply(chunk)
            else:
                await message.reply(reply_text)
                
            print(f"🤖 [REIMU TRẢ LỜI -> {message.author.display_name}]: {reply_text[:100]}...", flush=True)
        except Exception as e:
            print(f"❌ [LỖI GEMINI CHAT]: {e}", flush=True)
            await message.reply("⛩️ *Hòm công đức đang đông khách quá, ta lười tiếp ngươi lúc này! Mau cúng tiền rồi quay lại sau!*")
# ==============================================================================
# HÀM TIẾN HÓA SEIKI ACE 2 & HÀM XỬ LÝ KỸ NĂNG DÙNG CHUNG (RAID / BATTLE / PVP)
# ==============================================================================
def execute_kizuna_ace2(player):
    """Tiến hóa Ace 2 [#t3] Kizuna: yêu cầu sở hữu thẻ Kizuna (Ace 1) + 1 vật phẩm Thánh Lõi."""
    if is_card_ace2(player, "t3"):
        return False, "⚠️ **[#t3] Kizuna the emperor of vampire** đã đạt **Ace 2 ⭐⭐** từ trước rồi!", None

    if not is_card_unlocked(player, "t3") and player.get("inventory", {}).get("t3", 0) <= 0:
        return False, "❌ Bạn phải sở hữu thẻ bài **[#t3] Kizuna the emperor of vampire (Ace 1)** trước khi tiến hóa!", None

    items = player.setdefault("items", {})
    shards = player.setdefault("shards", {})
    
    # Kiểm tra thánh lõi trong items hoặc shards
    cur_core = items.get("thanh_loi", 0) or shards.get("thanh_loi", 0)
    if cur_core < 1:
        return False, (
            "❌ Bạn chưa sở hữu vật phẩm **Thánh Lõi** để tiến hóa Kizuna lên Ace 2!\n"
            "💡 *Vật phẩm Thánh Lõi có thể nhận qua hoàn thành /event info hoặc nhận từ Admin.*"
        ), None

    if items.get("thanh_loi", 0) > 0:
        items["thanh_loi"] -= 1
    if shards.get("thanh_loi", 0) > 0:
        shards["thanh_loi"] -= 1

    player.setdefault("evolutions", {})["t3"] = 2
    save_player(player)

    embed = discord.Embed(
        title="🌟 TIẾN HÓA THÀNH CÔNG: [#t3] KIZUNA THE EMPEROR OF VAMPIRE - ACE 2 ⭐⭐!",
        description=(
            "🩸 **HOÀNG ĐẾ MA CÀ RỒNG THỨC TỈNH - BỘ KỸ NĂNG TỐI THƯỢNG ACE 2:**\n\n"
            "❤️ **True vampire (Nội tại - 100%):** Hồi phục **5% Máu Tối Đa** mỗi lượt!\n"
            "🛡️ **Wonder guard (20%):** Miễn thương & **phản lại 60% sát thương lẫn hiệu ứng** của địch trong **3 lượt** (1 lần/trận)!\n"
            "💥 **Blood chain (30%):** Gây **2.0x sát thương** (1 lần/trận)!\n"
            "🌑 **Dark chain (30%):** Gây **1.5x sát thương** kèm **5% Máu Tối Đa mục tiêu** (tối đa 3 lần/trận)!\n\n"
            f"📉 **Chi phí:** Đã tiêu hao **1 Thánh Lõi** (Còn lại: `{items.get('thanh_loi', 0)}` lõi)\n"
            "💪 **Buff Ace 2:** +300 ATK & +300 HP vĩnh viễn!"
        ),
        color=0x991B1B
    )
    embed.set_image(url="https://static2.klipy.com/ii/d6b0ce929193df3c242ac34b5654d2ce/a2/4a/5wVVGJlo.gif")
    embed.set_footer(text="Touhou Evolution System • Kizuna Ace 2 Activated • Card ID #t3")
    return True, "", embed


# ==============================================================================
# BỘ KỸ NĂNG ACE 2 CHO THẺ [T] #t1 SEIKI (CLEAVE, MEDICINE SIGN, FANTASY SEAL, BÓNG KHÁI NIỆM)
# ==============================================================================
def execute_seiki_ace2(player):
    """Tiến hóa Ace 2 [#t1] Seiki: yêu cầu đã mở khóa thẻ #t1 + Ace 2 của Marisa [#19], Reimu [#15], Sakuya [#18] + 10 Mảnh Seiki."""
    if is_card_ace2(player, "t1"):
        return False, "⚠️ **[#t1] Seiki Đệ Pháp Toàn Năng** đã đạt **Ace 2 ⭐⭐** từ trước rồi!", None

    if not is_card_unlocked(player, "t1") and player.get("inventory", {}).get("t1", 0) <= 0:
        return False, (
            "❌ **Bạn chưa mở khóa thẻ gốc [#t1] Seiki Đệ Pháp Toàn Năng!**\n"
            "• Bắt buộc phải thu thập **10 Mảnh Seiki** và dùng lệnh `/t translate` (hoặc `/translate`) để đổi thẻ gốc trước.\n"
            "• Sau khi sở hữu thẻ gốc, bạn mới có thể dùng thêm **10 Mảnh Seiki** nữa để tiến hóa lên **Ace 2 ⭐⭐**!"
        ), None

    missing = [cid for cid in T1_ACE2_CONFIG["required_ace2"] if not is_card_ace2(player, cid)]
    if missing:
        names = ", ".join(f"[#{c:02d}] {CARDS_DATA[c]['name']}" for c in missing)
        return False, (
            "❌ **Chưa đủ điều kiện tiến hóa Seiki Ace 2!**\n"
            "• Yêu cầu: **[#19] Marisa**, **[#15] Reimu**, **[#18] Sakuya** đều phải đạt **Ace 2 ⭐⭐**.\n"
            f"• Còn thiếu Ace 2: **{names}**"
        ), None

    shards = player.setdefault("shards", {})
    cur = shards.get("seiki", 0)
    need = T1_ACE2_CONFIG["required_shards"]
    if cur < need:
        return False, (
            f"❌ Chưa đủ **Mảnh Seiki**! (Hiện có: **{cur}/{need}** mảnh).\n"
            "💡 *Nguồn rơi: tham gia Boss Raid (tỉ lệ 2.5%/5%).*"
        ), None

    shards["seiki"] = cur - need
    player.setdefault("evolutions", {})["t1"] = 2
    save_player(player)

    embed = discord.Embed(
        title="🌟 TIẾN HÓA THÀNH CÔNG: [#t1] SEIKI ĐỆ NHẤT PHÁP SƯ - ACE 2 ⭐⭐!",
        description=(
            "⚡ **MA LỰC DỊ TÀ THỨC TỈNH - BỘ KỸ NĂNG ĐỘC QUYỀN ACE 2:**\n\n"
            "🪓 **Cleave (Nội Tại - 100%):** Mọi đòn đánh thường gây thêm **2% Máu Tối Đa** mục tiêu!\n"
            "💚 **Medicine Sign (35%):** Hồi phục **40% Máu Tối Đa** bản thân, 1 lần/trận.\n"
            "🛡️ **Fantasy Seal (50%):** Dựng kết giới phong ấn, **MIỄN TOÀN BỘ SÁT THƯƠNG** trong 1 hiệp (đã buff lên 50% ở dạng Ace 2), 1 lần/trận.\n"
            "🌑 **Bóng Khái Niệm (20%):** Gây **×1.5 Sát Thương** kèm **10% Máu Tối Đa** mục tiêu và **xóa kỹ năng đối phương**, 1 lần/trận.\n\n"
            f"📉 **Chi phí:** Đã tiêu hao **10 Mảnh Seiki** (Còn lại: `{shards['seiki']}` mảnh)\n"
            "💪 **Buff Ace 2:** +300 ATK & +300 HP vĩnh viễn! (Đạt 995 ATK & 7,300 HP gốc)"
        ),
        color=0x7C3AED
    )
    embed.set_image(url=EVOL_CONFIG["t1"]["evol_gif"])
    embed.set_footer(text="Touhou Evolution System • Seiki Ace 2 Activated • Card ID #t1")
    return True, "", embed
    
def apply_bong_khai_niem_boss(boss_type: str, phase: int, erased_skill_current: Optional[str]):
    """Xóa ngẫu nhiên tối đa 1 chiêu duy nhất của Boss (Limit: 1 chiêu/Boss, dù có bao nhiêu lá Seiki)."""
    if erased_skill_current:
        return erased_skill_current, (
            f"🛡️ **[Giới Hạn Bóng Khái Niệm]** Boss đã từng bị xóa chiêu **[{erased_skill_current}]** trước đó! "
            f"(Mỗi Boss chỉ bị mất tối đa 1 chiêu duy nhất, không mất thêm!)."
        )
    if boss_type == "seiki" and phase == 1:
        pool = [("multi_spark", "Multi Master Spark"), ("fantasy_seal", "Fantasy Seal"), ("blitz_attack", "Blitz Attack")]
    elif boss_type == "seiki" and phase == 2:
        pool = [("nuclear_spell", "Nuclear Spell Card")]
    elif boss_type == "mahoraga":
        pool = [("thoai_ma_kiem", "Thoái Ma Kiếm")]
    elif boss_type == "fateria":
        pool = [("save_loop", "Save loop"), ("fate_loop", "Fate loop"), ("clone_attack", "Clone attack")]
    elif boss_type == "kizuna_event" and phase == 1:
        pool = [("blood_chain", "Blood chain"), ("dark_chain", "Dark chain")]
    elif boss_type == "kizuna_event" and phase == 2:
        pool = [("wonder_guard", "Wonder guard"), ("blood_chain", "Blood chain"), ("dark_chain", "Dark chain")]
    else:
        pool = [("di_hinh_bua_chu", "Dị Hình Bùa Chú")]

    key, name = random.choice(pool)
    return key, f"🌑 **[Bóng Khái Niệm]** Đã xóa ngẫu nhiên 1 chiêu duy nhất của Boss: **[{name}]**! *(Đã chạm giới hạn tối đa 1 chiêu)*"


def apply_bong_khai_niem_card(target_card: dict):
    """Xóa ngẫu nhiên tối đa 1 chiêu duy nhất trên 1 lá bài đối phương trong PvP/Battle (Limit: 1 chiêu/lá)."""
    if target_card.get("erased_skill"):
        return (
            f"🛡️ **[Giới Hạn Bóng Khái Niệm]** **{target_card['name']}** đã bị xóa kỹ năng "
            f"**[{target_card.get('erased_skill_name', target_card['erased_skill'])}]** từ trước! (Tối đa mất 1 chiêu duy nhất)."
        )
    cid = target_card["cid"]
    cid_str = str(cid).lower()
    is_ace = target_card.get("is_ace2", False)
    pool = []

    if cid == 4 and is_ace:
        pool = [("yukari_station", "Trip To The Old Station"), ("yukari_lastword", "⸮⸮⸮ : Last Word !"), ("yukari_gap", "Invisible Gap")]
    elif cid_str == "t1":
        if is_ace:
            pool = [("t1_cleave", "Cleave"), ("t1_seal", "Fantasy Seal"), ("t1_bong", "Bóng Khái Niệm"), ("t1_med", "Medicine Sign")]
        else:
            pool = [("t1_seal", "Fantasy Seal"), ("t1_spark", "Master Spark"), ("t1_med", "Medicine Sign")]
    elif cid_str == "t2":
        pool = [("t2_adapt", "The True Adapt"), ("t2_kiem", "Thoái Ma Kiếm")]
    elif cid_str == "t3":
        if is_ace:
            pool = [("t3_vampire", "True Vampire"), ("t3_wonder", "Wonder Guard"), ("t3_blood", "Blood Chain"), ("t3_dark", "Dark Chain")]
        else:
            pool = [("t3_vampire", "True Vampire"), ("t3_blood", "Blood Chain"), ("t3_dark", "Dark Chain")]
    elif cid_str == "t4":
        pool = [("t4_save_loop", "Save loop"), ("t4_fate_loop", "Fate loop"), ("t4_clone_attack", "Clone attack")]
    elif cid == 18 and is_ace:
        pool = [("sakuya_stun", "Thời Gian Đóng Băng")]
    elif cid == 19 and is_ace:
        pool = [("marisa_spark", "Master Spark")]
    elif cid == 15 and is_ace:
        pool = [("reimu_invul", "Vô Tưởng Chuyển Sinh")]
    elif cid == 9 and is_ace:
        pool = [("flandre_ripples", "Ripples of 495 Years")]
    elif cid == 12 and is_ace:
        pool = [("remilia_gungnir", "Thương Đỏ Gungnir")]
    elif cid == 21 and is_ace:
        pool = [("reisen_mind", "Red Eye Mind Explosion")]
    elif cid == 23 and is_ace:
        pool = [("cirno_freeze", "Perfect Freeze")]
    elif cid == 13 and is_ace:
        pool = [("utsuho_nuclear", "Nuclear Spell Card")]

    if not pool:
        return f"🌑 **[Bóng Khái Niệm]** **{target_card['name']}** không sở hữu kỹ năng đặc biệt nào để xóa!"

    key, name = random.choice(pool)
    target_card["erased_skill"] = key
    target_card["erased_skill_name"] = name
    return f"🌑 **[Bóng Khái Niệm]** Đã xóa ngẫu nhiên 1 kỹ năng duy nhất **[{name}]** của **{target_card['name']}**! *(Tối đa mất 1 chiêu)*"


def t1_ace2_attack(t1_flags, ac, round_no, target_max_hp, target_desc, is_boss=False):
    """Kỹ năng Ace 2 ⭐⭐ [#t1] Seiki - dùng chung Raid / Battle / PvP.
    t1_flags: dict lưu cờ (seal_used / bong_used / med_used / used_turn).
    Quy tắc: Cleave thụ động 100% mọi đòn đánh; tối đa 1 chiêu/lượt; mỗi chiêu 1 lần/trận.
    ĐẶC BIỆT: Chiêu Fantasy Seal được buff tỷ lệ kích hoạt lên 50% ở dạng Ace 2 (Miễn toàn bộ sát thương 1 hiệp)!"""
    out = {"bonus": 0, "direct": 0, "heal": 0, "invul": False, "instant_kill": False, "boss_half_hp": False,
           "disable": False, "logs": [], "gif": None, "multiplier": 1.0}

    erased = ac.get("erased_skill")

    # 🪓 CLEAVE - Nội tại thụ động 100%: đánh thường +2% Máu Tối Đa mục tiêu (nếu không bị xóa bởi Bóng Khái Niệm)
    if erased != "t1_cleave":
        out["bonus"] = int(target_max_hp * T1_ACE2_CONFIG["cleave_pct"])
        out["logs"].append(
            f"🪓 **[Ace 2] [#t1] Seiki Đệ Nhất Pháp Sư** - **Cleave (Nội Tại - 100%)**: "
            f"Mọi đòn đánh +**{out['bonus']:,} DMG** (2% Máu Tối Đa {target_desc})!"
        )

    if t1_flags.get("used_turn") == round_no:
        return out

    roll = random.random()
    seal_cfg = T1_ACE2_CONFIG.get("fantasy_seal", {"chance": 0.50, "gif": T1_SEAL_GIF})
    seal_chance = seal_cfg["chance"]
    bong_chance = T1_ACE2_CONFIG["bong_khai_niem"]["chance"]
    med_chance = T1_ACE2_CONFIG["medicine_sign"]["chance"]

    if erased != "t1_seal" and not t1_flags.get("seal_used") and not t1_flags.get("seiki_seal_used") and roll < seal_chance:
        t1_flags["seal_used"] = True
        t1_flags["seiki_seal_used"] = True
        t1_flags["used_turn"] = round_no
        out["invul"] = True
        out["gif"] = seal_cfg.get("gif", T1_SEAL_GIF)
        out["logs"].append(
            f"🛡️ **[Ace 2] [#t1] Seiki** kích hoạt **FANTASY SEAL** (50%)! "
            f"Vận khởi kết giới phong ấn tuyệt đối — **MIỄN TOÀN BỘ SÁT THƯƠNG** trong hiệp này!"
        )
    elif erased != "t1_bong" and not t1_flags.get("bong_used") and roll < seal_chance + bong_chance:
        t1_flags["bong_used"] = True
        t1_flags["used_turn"] = round_no
        out["multiplier"] = T1_ACE2_CONFIG["bong_khai_niem"].get("multiplier", 1.5)
        out["direct"] = int(target_max_hp * T1_ACE2_CONFIG["bong_khai_niem"]["dmg_pct"])
        out["disable"] = True
        out["gif"] = T1_ACE2_CONFIG["bong_khai_niem"]["gif"]
        out["logs"].append(
            f"🌑 **[Ace 2] [#t1] Seiki** kích hoạt **BÓNG KHÁI NIỆM** (20%)! "
            f"Cường hóa **×{out['multiplier']} Sát Thương** kèm **{out['direct']:,} DMG** (10% Máu Tối Đa {target_desc}) và **XÓA NGẪU NHIÊN 1 KỸ NĂNG của đối phương (Tối đa 1 chiêu)**!"
        )
    elif erased != "t1_med" and not t1_flags.get("med_used") and ac.get("current_hp", 1) < ac.get("max_hp", ac.get("hp", 1)) and roll < seal_chance + bong_chance + med_chance:
        t1_flags["med_used"] = True
        t1_flags["used_turn"] = round_no
        out["heal"] = int(ac.get("max_hp", ac.get("hp", 1)) * T1_ACE2_CONFIG["medicine_sign"]["heal_pct"])
        out["gif"] = T1_ACE2_CONFIG["medicine_sign"]["gif"]
        out["logs"].append(
            f"💚 **[Ace 2] [#t1] Seiki** kích hoạt **MEDICINE SIGN** (35%)! "
            f"Hồi phục **+{out['heal']:,} HP** (40% Máu Tối Đa bản thân)!"
        )

    return out
    
# ==============================================================================
# HÀM XỬ LÝ LƯỢT ĐÁNH THẺ [#t3] KIZUNA THE EMPEROR OF VAMPIRE (DÙNG CHO PVP, RAID, BATTLE)
# ==============================================================================
def t3_combat_turn(t3_state: dict, card_data: dict, round_no: int, target_max_hp: int, target_name: str, is_ace2: bool = False):
    """
    Xử lý lượt đánh và kỹ năng của thẻ T3 Kizuna trong PvP, Battle, Raid Boss.
    - True vampire (100%): Tự hồi 5% Max HP mỗi lượt.
    - Blood chain (30%): 1.5x DMG (Bản thường) / 2.0x DMG (Ace 2), 1 lần/trận.
    - Dark chain (20% thường / 30% Ace 2): Gây thêm 15% Max HP mục tiêu (tối đa 3 lần/trận).
    - Wonder guard (20% ở Ace 2): Miễn thương & phản sát thương chủ động trong 3 lượt (1 lần/trận).
    """
    logs = []
    gif = None
    multiplier = 1.0
    bonus_hp_dmg = 0
    erased = card_data.get("erased_skill")

    # 1. NỘI TẠI: TRUE VAMPIRE (100% kích hoạt mỗi lượt nếu không bị xóa)
    max_hp = card_data.get("max_hp", card_data.get("hp", 7700))
    if erased != "t3_vampire":
        heal_amt = int(max_hp * 0.05)
        card_data["current_hp"] = min(max_hp, card_data.get("current_hp", max_hp) + heal_amt)
        logs.append(f"🩸 **[#t3] Kizuna** - **True Vampire (100%)**: Tự hồi **+{heal_amt:,} HP** ({card_data['current_hp']:,}/{max_hp:,} HP)!")

    # Khởi tạo state
    dark_chain_uses = t3_state.get("dark_chain_uses", 0)
    blood_used = t3_state.get("blood_used", False)
    wonder_guard_used = t3_state.get("wonder_guard_used", False)
    if erased == "t3_wonder":
        t3_state["wonder_guard_turns"] = 0

    # 2. XỬ LÝ KỸ NĂNG CHỦ ĐỘNG
    roll = random.random()

    if is_ace2 and erased != "t3_wonder" and not wonder_guard_used and roll < 0.20:
        t3_state["wonder_guard_used"] = True
        t3_state["wonder_guard_turns"] = 3
        gif = T3_WONDER_GUARD_GIF
        logs.append(
            f"🛡️ **[Ace 2] [#t3] Kizuna** kích hoạt **WONDER GUARD (20%)**! "
            f"Dựng huyết thuẫn tuyệt đối: **MIỄN TOÀN BỘ SÁT THƯƠNG & PHẢN 60% SÁT THƯƠNG LẪN HIỆU ỨNG** trong 3 lượt!"
        )

    elif erased != "t3_blood" and not blood_used and roll < (0.50 if is_ace2 else 0.30):
        t3_state["blood_used"] = True
        multiplier = 2.0 if is_ace2 else 1.5
        gif = T3_BLOOD_GIF
        logs.append(
            f"💥 **[#t3] Kizuna** tung xích máu **BLOOD CHAIN (30%)**! "
            f"Đòn đánh bộc phát ma lực **×{multiplier} Sát Thương** giáng vào {target_name}!"
        )

    elif erased != "t3_dark" and dark_chain_uses < 3 and roll < (0.80 if is_ace2 else 0.50):
        t3_state["dark_chain_uses"] = dark_chain_uses + 1
        multiplier = 1.5 if is_ace2 else 1.0
        bonus_hp_dmg = int(target_max_hp * 0.05)
        gif = T3_DARK_GIF
        logs.append(
            f"🌑 **[#t3] Kizuna** thi triển **DARK CHAIN**! "
            f"Gây sát thương ×{multiplier} kèm **+{bonus_hp_dmg:,} DMG** (5% Máu Tối Đa {target_name})! "
            f"*(Lần {t3_state['dark_chain_uses']}/3)*"
        )

    return {
        "multiplier": multiplier,
        "bonus_hp_dmg": bonus_hp_dmg,
        "logs": logs,
        "gif": gif,
        "wonder_guard_active": t3_state.get("wonder_guard_turns", 0) > 0
    }
def t4_combat_turn(t4_state: dict, card_data: dict, target_name: str, heal_mult: float = 1.0, enemy_fate_loop_turns: int = 0):
    """
    Xử lý lượt đánh và kỹ năng của thẻ [#t4] Fateria – Khuôn mẫu của số phận:
    - Passive Save loop (15%): Hồi 50% Max HP và miễn nhiễm sát thương turn đó.
    - Skill 1 Fate loop (20%): Khiến đối thủ không dùng skill 2 turn liên tiếp (tối đa 2 lần/trận, không lặp khi đang hiệu lực).
    - Skill 2 Clone attack (40%): Random 1/3 chiêu con rối (tối đa 2 lần/trận):
      + Thunder blaze: 2.3x DMG
      + The fallen hero: 1.5x DMG + giảm 30% Heal
      + Ice spear: 1.5x DMG + 40% không tấn công trong 2 lượt sau
    """
    logs = []
    gif = None
    multiplier = 1.0
    save_loop_invul = False
    fate_loop_triggered = False
    heal_reduce_triggered = False
    ice_spear_triggered = False
    erased = card_data.get("erased_skill")

    max_hp = card_data.get("max_hp", card_data.get("hp", 7500))
    cur_hp = card_data.get("current_hp", max_hp)

    # 1. PASSIVE: SAVE LOOP (15% kích hoạt)
    if erased != "t4_save_loop" and random.random() < 0.15:
        save_loop_invul = True
        heal_amt = int(max_hp * 0.50 * heal_mult)
        card_data["current_hp"] = min(max_hp, cur_hp + heal_amt)
        gif = CARDS_DATA["t4"]["passive"]["gif"]
        logs.append(
            f"🔄 **[#t4] Fateria** kích hoạt **Save loop (15%)**! "
            f"Hồi phục **+{heal_amt:,} HP (50% HP)** ({card_data['current_hp']:,}/{max_hp:,} HP) và **MIỄN NHIỄM SÁT THƯƠNG** trong turn này!"
        )

    fate_uses = t4_state.get("fate_uses", 0)
    clone_uses = t4_state.get("clone_uses", 0)

    # 2. SKILL 1 (Fate loop 20%) hoặc SKILL 2 (Clone attack 40%)
    can_fate = (erased != "t4_fate_loop") and (fate_uses < 2) and (enemy_fate_loop_turns <= 0)
    can_clone = (erased != "t4_clone_attack") and (clone_uses < 2)

    roll = random.random()
    if can_fate and roll < 0.20:
        t4_state["fate_uses"] = fate_uses + 1
        fate_loop_triggered = True
        gif = CARDS_DATA["t4"]["skills"]["fate_loop"]["gif"]
        logs.append(
            f"⛓️ **[#t4] Fateria** thi triển **FATE LOOP (20%)** *(Lần {t4_state['fate_uses']}/2)*! "
            f"Khóa toàn bộ kỹ năng của {target_name} trong **2 turn liên tiếp**!"
        )
    elif can_clone and ((can_fate and 0.20 <= roll < 0.60) or (not can_fate and roll < 0.40)):
        t4_state["clone_uses"] = clone_uses + 1
        clones_cfg = CARDS_DATA["t4"]["skills"]["clone_attack"]["clones"]
        c_key = random.choice(["thunder_blaze", "the_fallen_hero", "ice_spear"])
        c_info = clones_cfg[c_key]
        multiplier = c_info["multiplier"]
        gif = c_info["gif"]
        if c_key == "thunder_blaze":
            logs.append(
                f"⚡ **[#t4] Fateria** - **Clone attack ({t4_state['clone_uses']}/2): Thunder blaze**! "
                f"Những ngọn lửa chớp điện phập phờn gây **2.3x DMG** lên {target_name}!"
            )
        elif c_key == "the_fallen_hero":
            heal_reduce_triggered = True
            logs.append(
                f"🗡️ **[#t4] Fateria** - **Clone attack ({t4_state['clone_uses']}/2): The fallen hero**! "
                f"Tung trảm kích ánh sáng **1.5x DMG** và **giảm 30% Heal** của {target_name}!"
            )
        else:
            ice_spear_triggered = True
            logs.append(
                f"❄️ **[#t4] Fateria** - **Clone attack ({t4_state['clone_uses']}/2): Ice spear**! "
                f"Phóng giáo băng **1.5x DMG** khiến {target_name} có **40% không thể tấn công trong 2 lượt sau**!"
            )

    return {
        "multiplier": multiplier,
        "save_loop_invul": save_loop_invul,
        "fate_loop_triggered": fate_loop_triggered,
        "heal_reduce_triggered": heal_reduce_triggered,
        "ice_spear_triggered": ice_spear_triggered,
        "logs": logs,
        "gif": gif
    }

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
                desc = f"Chi tiết diễn biến hiệp {i+1}"[:100]
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
        if is_ace and c["cid"] in [4, 9, 12, 13, 15, 18, 19, 21, 23]:
            if c["cid"] == 4:
                skill_text += (
                    "\n🌌 **[Ace 2 Hiệu Ứng]** 30% *Trip To The Old Station* (×2.0 DMG, 1 lần/trận) • "
                    "25% *Last Word* (×2.5 DMG + Stun 1 turn, 1 lần/trận) • "
                    "10% *Invisible Gap* (Nội tại phản 100% sát thương đánh thường)."
                )
            elif c["cid"] == 15:
                skill_text += "\n🛡️ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Vô Tưởng Chuyển Sinh* né toàn bộ sát thương."
            elif c["cid"] == 18:
                skill_text += "\n⏳ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Thời Gian Đóng Băng* khiến đối phương mất lượt."
            elif c["cid"] == 19:
                skill_text += "\n🌟 **[Ace 2 Hiệu Ứng]** 30% kích hoạt *Master Spark* bộc phá ×2.0 sát thương."
            elif c["cid"] == 9:
                skill_text += "\n🦇 **[Ace 2 Hiệu Ứng]** 25% kích hoạt *Ripples of 495 Years* xóa sổ 50% HP đối thủ (30% HP Boss trong Raid, 1 lần/trận)."
            elif c["cid"] == 12:
                skill_text += "\n🩸 **[Ace 2 Hiệu Ứng]** *Thương Đỏ Gungnir* (THỤ ĐỘNG): mọi đòn đánh gây thêm 3% Máu Tối Đa của mục tiêu."
            elif c["cid"] == 21:
                skill_text += "\n🔴 **[Ace 2 Hiệu Ứng]** 25% kích hoạt *Red Eye Mind Explosion* (1 lần/trận): mục tiêu 20% tự gây sát thương lên bản thân trong 4 turn."
            elif c["cid"] == 23:
                skill_text += "\n❄️ **[Ace 2 Hiệu Ứng]** 40% kích hoạt *Perfect Freeze* (1 lần/trận): đóng băng đối thủ, trong 2 turn tiếp theo có 45% không thể đánh trả."
            elif c["cid"] == 13:
                skill_text += "\n☢️ **[Ace 2 Hiệu Ứng]** 30% kích hoạt *Nuclear Spell Card* bộc phá ×3.0 sát thương & nung chảy mặt đất gây bỏng 2% Máu Tối Đa cho bài địch trong 3 turn."
        if is_ace and str(c["cid"]).lower() == "t1":
            skill_text += "\n♾️ **[Ace 2 Hiệu Ứng]** *Cleave* (thụ động, +2% Máu tối đa mỗi đòn) • *Medicine Sign* (35% hồi 40% máu) • *Fantasy Seal* (buff lên 50% miễn toàn bộ sát thương 1 hiệp) • *Bóng Khái Niệm* (20%: 1.5x sát thương + 10% máu tối đa + xóa kỹ năng đối phương — mỗi chiêu 1 lần/trận)."
        if str(c["cid"]).lower() == "t2":
            skill_text += "\n🔱 **[Thần Tướng Hiệu Ứng]** *The True adapt* (thụ động 100%: mỗi turn hồi 5% Máu tối đa và giảm 5% sát thương phải nhận - cộng dồn) • *Thoái Ma kiếm* (30% kích hoạt gây ×1.5 sát thương)."
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

    if boss_type not in ["reimu", "seiki", "mahoraga", "fateria"]:
        boss_spawn_roll = random.random()
        if boss_spawn_roll < (1.0 / 4.0):
            boss_type = "seiki"
        elif boss_spawn_roll < (2.0 / 4.0):
            boss_type = "reimu"
        elif boss_spawn_roll < (3.0 / 4.0):
            boss_type = "mahoraga"
        else:
            boss_type = "fateria"

    is_seiki = (boss_type == "seiki")
    is_mahoraga = (boss_type == "mahoraga")
    is_fateria = (boss_type == "fateria")
    cfg = SEIKI_BOSS_CONFIG if is_seiki else (MAHORAGA_BOSS_CONFIG if is_mahoraga else (FATERIA_BOSS_CONFIG if is_fateria else BOSS_CONFIG))

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
        embed.add_field(name="❤️ Máu Boss (HP):", value=f"• Phase 1: **{cfg['hp']:,} HP**\n• Phase 2 Thức Tỉnh: **{SEIKI_BOSS_PHASE2_CONFIG['hp']:,} HP**", inline=True)
        embed.add_field(name="⚔️ Sát Thương Đánh Thường:", value=f"• Phase 1: **{cfg['power']:,} DMG** *(chia đều, Spark x1.5: 4,500)*\n• Phase 2: **{SEIKI_BOSS_PHASE2_CONFIG['power']:,} DMG** *(chia đều, kèm Cleave +20% Máu tối đa mục tiêu)*", inline=True)
        embed.add_field(name=f"👥 Người Tham Gia (0/{cfg['max_players']}):", value="Chưa có ai", inline=False)
        embed.add_field(
            name="🔮 Kỹ Năng & Nội Tại (Độc Quyền - Không Trùng Turn):",
            value=(
                "• 💚 **Nội Tại:** Mỗi hiệp tự hồi phục **1.5% HP tối đa (450 HP)**!\n"
                "• 🌟 **Multi Master Spark (15%):** Bộc phát ma lực x1.5 sát thương (4,500 DMG chia đều) duy trì trong **3 lượt**!\n"
                "• 🛡️ **Fantasy Seal (20%):** Dựng kết giới phong ấn, **MIỄN TOÀN BỘ SÁT THƯƠNG** trong 1 turn!\n"
                "• ⚡ **Blitz Attack (20%):** Oanh tạc chớp nhoáng gây **4,000 DMG** diện rộng lên toàn bộ thẻ tiền tuyến!\n"
                "*(Lưu ý: Không bao giờ kích hoạt trùng chiêu trong cùng một hiệp)*\n\n"
                "👹 **PHASE 2 - THỨC TỈNH (90K HP / 10K DMG CHIA ĐỀU):**\n"
                "• ☢️ **Nuclear Spell Card (15%):** Gây **10,000 DMG** lên **TẤT CẢ** lá bài đang ở tiền tuyến!\n"
                "• 🪓 **Cleave (Nội Tại - 100%):** Mọi đòn đánh thường gây thêm **20% Máu Tối Đa** của mục tiêu!"
            ),
            inline=False
        )
        embed.add_field(
            name="🎁 Phần Thưởng Thanh Tẩy Boss:",
            value="• **Phase 1:** 10% nhận **10 Vé**, 40% nhận **5 Vé**, 50% nhận **3 Vé**! (+100 XP)\n• **Phase 2 (Thức Tỉnh):** 10% nhận **30 Vé**, 40% nhận **20 Vé**, 50% nhận **10 Vé**! 🔮 **5%** rơi **+1 Mảnh Seiki** | 🪭 **2.5%** rơi **+1 Quạt Giấy**! (+150 XP)\n• 🔮 Mỗi Phase đều có **2.5%** rơi **+1 Mảnh Seiki** (10 mảnh = 1 thẻ [T] #t1 Seiki - dùng `/t translate`)!\n• Nhận thêm điểm danh nhiệm vụ diệt Boss!",
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
    elif boss_type == "mahoraga":
        reimu_line = f"🌸 **Reimu thảng thốt:** *\"{cfg['reimu_quote']}\"*\n\n"
        desc = (f"👑 **Được triệu hồi bởi Admin:** {author.mention}\n\n{reimu_line}👺 **{cfg['name']}**\n*{cfg['desc']}*"
                if is_admin else f"{reimu_line}👺 **{cfg['name']}**\n*{cfg['desc']}*")
        embed = discord.Embed(title=title, description=desc, color=0x1F2937)
        embed.set_image(url=cfg["image"])
        embed.add_field(name="❤️ Máu Boss (HP):", value=f"**{cfg['hp']:,} HP** *(Single Phase - không hồi sinh!)*", inline=True)
        embed.add_field(name="⚔️ Sát Thương Đánh Thường:", value=f"**{cfg['power']:,} DMG** *(chia đều tiền tuyến)*", inline=True)
        embed.add_field(name=f"👥 Người Tham Gia (0/{cfg['max_players']}):", value="Chưa có ai", inline=False)
        embed.add_field(
            name="♾️ Nội Tại & Kỹ Năng (Độc Quyền - The True Adapt):",
            value=(
                "• ♾️ **The True Adapt (100% - THỤ ĐỘNG):**\n"
                "  - Mỗi hiệp tự hồi phục **3% HP tối đa (2,700 HP)**!\n"
                "  - Mỗi hiệp **GIẢM 3% sát thương phải nhận** (cộng dồn mỗi hiệp - càng đánh càng cứng)!\n"
                "• ⚔️ **Thoái Ma Kiếm (25%):** Rút trường kiếm giáng **6,000 DMG sát thương thuần** lên **MỘT mục tiêu** duy nhất (không chia đều)!"
            ),
            inline=False
        )
        embed.add_field(
            name="🎁 Phần Thưởng Thanh Tẩy Boss:",
            value="• **10%** nhận **20 Vé** | **40%** nhận **15 Vé** | **50%** nhận **10 Vé**! (+100 XP)\n• 🔱 **5%** rơi **+1 Mảnh Mahoraga** (vật phẩm đặc biệt - Thẻ Mahoraga sắp ra mắt)!\n• Nhận thêm điểm danh nhiệm vụ diệt Boss!",
        )
        embed.add_field(
            name="⏱️ Thời Gian Chuẩn Bị (2 Phút):",
            value=(
                "• Có đúng **2 phút (120 giây)** để bấm **'Tham Gia'** (Miễn phí)!\n"
                "• **Tự động mở raid:** Khi hết 2 phút, nếu có dũng giả tham chiến, trận đại chiến sẽ **TỰ ĐỘNG KHỞI TRANH** ngay lập tức!\n"
                "• **Tự động đóng:** Nếu sau 2 phút không có ai tham gia, Mahoraga sẽ tan biến vào hư không!"
            ),
            inline=False
        )
    elif boss_type == "fateria":
        reimu_line = f"🌸 **Reimu:** *\"{cfg['reimu_quote']}\"*\n\n"
        desc = (f"👑 **Được triệu hồi bởi Admin:** {author.mention}\n\n{reimu_line}⏳ **{cfg['name']}**\n*{cfg['desc']}*"
                if is_admin else f"{reimu_line}⏳ **{cfg['name']}**\n*{cfg['desc']}*")
        embed = discord.Embed(title=title, description=desc, color=0x0EA5E9)
        embed.set_image(url=cfg["image"])
        embed.add_field(name="❤️ Máu Boss (HP):", value=f"**{cfg['hp']:,} HP** *(Single Phase)*", inline=True)
        embed.add_field(name="⚔️ Sát Thương Đánh Thường:", value=f"**{cfg['power']:,} DMG** *(chia đều tiền tuyến)*", inline=True)
        embed.add_field(name=f"👥 Người Tham Gia (0/{cfg['max_players']}):", value="Chưa có ai", inline=False)
        embed.add_field(
            name="⏳ Nội Tại & Kỹ Năng (Khuôn Mẫu Số Phận):",
            value=(
                "• 🔄 **Passive - Save loop (15%):** Hồi **30% HP tối đa (28,500 HP)** và **MIỄN NHIỄM SÁT THƯƠNG** trong turn đó!\n"
                "• ⛓️ **Skill 1 - Fate loop (10%):** Khiến đối thủ **không thể dùng skill trong 2 turn liên tiếp** (không lặp lại cho đến khi hết 2 turn đó)!\n"
                "• 🪆 **Skill 2 - Clone attack (20% kích hoạt - Random 1/3 chiêu con rối):**\n"
                "  - ⚡ **Thunder blaze:** Ngọn lửa chớp điện phập phờn gây **2.3x DMG (14,260 DMG)** chia đều sát thương!\n"
                "  - 🗡️ **The fallen hero:** Trảm kích ánh sáng **1.5x DMG (9,300 DMG)** chia đều & **giảm 30% Heal** của đối phương!\n"
                "  - ❄️ **Ice spear:** Ngọn giáo băng **1.5x DMG (9,300 DMG)** chia đều & khiến đối phương **40% không thể tấn công** trong **2 lượt sau**!"
            ),
            inline=False
        )
        embed.add_field(
            name="🎁 Phần Thưởng Thanh Tẩy Boss:",
            value=(
                "• **10%** nhận **30 Vé** | **40%** nhận **15 Vé** | **50%** nhận **10 Vé**! (+100 XP)\n"
                "• ⏳ **5%** rơi ra **+1 Fateria Shard**!\n"
                "• Nhận thêm điểm danh nhiệm vụ diệt Boss!"
            ),
            inline=False
        )
        embed.add_field(
            name="⏱️ Thời Gian Chuẩn Bị (2 Phút):",
            value=(
                "• Có đúng **2 phút (120 giây)** để bấm **'Tham Gia'** (Miễn phí)!\n"
                "• **Tự động mở raid:** Khi hết 2 phút, nếu có dũng giả tham chiến, trận đại chiến sẽ **TỰ ĐỘNG KHỞI TRANH** ngay lập tức!\n"
                "• **Tự động đóng:** Nếu sau 2 phút không có ai tham gia, Fateria sẽ biến mất vào dòng chảy thời gian!"
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
                "• **Phase 2:** 10% ra **20 Vé**, 40% ra **10 Vé**, 50% ra **5 Vé**! 🪭 **1%** rơi **+1 Quạt Giấy** (Tiến hóa Yukari Ace 2)!\n"
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

# ==============================================================================
# HÀM BẢO HIỂM: GIỚI HẠN 50% SÁT THƯƠNG CHUẨN TRONG RAID BOSS
# ==============================================================================
def apply_raid_true_damage(requested_dmg: int, current_accumulated: int, max_cap: int, skill_label: str):
    if requested_dmg <= 0:
        return 0, current_accumulated, None

    rem = max(0, max_cap - current_accumulated)
    if rem <= 0:
        cap_note = (
            f"🔒 **[TRẦN SÁT THƯƠNG CHUẨN 50%]** Đã đạt giới hạn tối đa ({max_cap:,} DMG)! "
            f"Kỹ năng {skill_label} bị vô hiệu hóa phần sát thương chuẩn, đòn đánh chỉ còn gây sát thương thuần "
            f"(hiệu ứng đi kèm vẫn kích hoạt bình thường)."
        )
        return 0, current_accumulated, cap_note
    elif requested_dmg > rem:
        actual_applied = rem
        new_accum = max_cap
        excess = requested_dmg - rem
        cap_note = (
            f"⚠️ **[CHẠM TRẦN 50% MAX HP]** {skill_label} chỉ được ghi nhận **{actual_applied:,} DMG** sát thương chuẩn "
            f"(phần vượt mức {excess:,} DMG bị triệt tiêu)! Từ giờ Boss chỉ còn nhận sát thương thuần."
        )
        return actual_applied, new_accum, cap_note
    else:
        new_accum = current_accumulated + requested_dmg
        return requested_dmg, new_accum, None
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
            "yukari_station_used": False,   
            "yukari_lastword_used": False,
            "sakuya_stun_used": False,
            "reimu_invul_used": False,
            "marisa_spark_used": False,
            "flandre_used": False,
            "reisen_used": False,
            "cirno_freeze_used": False,
            "seiki_seal_used": False,
            "seiki_spark_used": False,
            "seiki_heal_used": False,
            "seiki_used_turn": -1,
            "seal_used": False,
            "bong_used": False,
            "med_used": False,
            "death_round": None
        })

    boss_type = raid_data.get("boss_type", "reimu")
    boss_cfg = raid_data.get("boss_config", SEIKI_BOSS_CONFIG if boss_type == "seiki" else BOSS_CONFIG)
    p1_max_hp = boss_cfg["hp"]
    p1_hp = p1_max_hp
    p1_power = boss_cfg["power"]
    seiki_spark_turns = 0
    boss_skill_erased = None

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
    elif boss_type == "mahoraga":
        init_embed = discord.Embed(
            title="⚔️ ĐẠI CHIẾN BẮT ĐẦU: BÁT ÁCH KIẾM THẦN TƯỚNG MAHORAGA",
            description=(
                f"🌸 **Reimu thảng thốt:** *\"{boss_cfg['reimu_quote']}\"*\n\n"
                f"🔥 **{len(combatants)} Dũng Giả** cùng đội quân thẻ bài đã dàn trận nghênh chiến!\n"
                f"Theo dõi diễn biến từng hiệp trực tiếp ngay bên dưới!"
            ),
            color=0x1F2937
        )
    elif boss_type == "fateria":
        init_embed = discord.Embed(
            title="⚔️ ĐẠI CHIẾN BẮT ĐẦU: FATERIA – KHUÔN MẪU CỦA SỐ PHẬN",
            description=(
                f"🌸 **Reimu:** *\"{boss_cfg['reimu_quote']}\"*\n\n"
                f"🔥 **{len(combatants)} Dũng Giả** cùng đội quân thẻ bài đã dàn trận nghênh chiến!\n"
                f"Theo dõi diễn biến từng hiệp trực tiếp ngay bên dưới!"
            ),
            color=0x0EA5E9
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
    boss_mind_turns = 0
    boss_freeze_debuff_turns = 0
    boss_molten_ground_turns = 0
    mahoraga_adapt_red = 0.0
    fateria_fate_loop_turns = 0
    fateria_ice_spear_turns = 0
    fateria_heal_reduction = 0.0
    p1_battle_history = []
    all_raid_turns = []

    p1_true_cap = int(p1_max_hp * 0.50)
    p1_true_dmg_accum = 0
    boss_fate_locked_turns = 0
    boss_ice_spear_turns = 0
    boss_heal_mult = 1.0

    while p1_hp > 0 and p1_rounds < max_rounds:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants:
            break

        p1_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        passive_log = None
        boss_skills_locked_this_turn = False
        if boss_fate_locked_turns > 0:
            boss_skills_locked_this_turn = True
            boss_fate_locked_turns -= 1

        boss_ice_spear_this_turn = False
        if boss_ice_spear_turns > 0:
            boss_ice_spear_this_turn = True
            boss_ice_spear_turns -= 1

        if boss_type == "seiki":
            heal_amt = int(p1_max_hp * boss_cfg.get("passive_regen_pct", 0.015) * boss_heal_mult)
            old_hp = p1_hp
            p1_hp = min(p1_max_hp, p1_hp + heal_amt)
            actual_healed = p1_hp - old_hp
            if actual_healed > 0:
                passive_log = f"💚 **[Nội Tại - Hồi Phục]** Seiki Dị Hình hấp thụ dị khí hồi phục **+{actual_healed:,} HP**!"
        elif boss_type == "mahoraga":
            mahoraga_adapt_red = min(0.90, mahoraga_adapt_red + boss_cfg.get("passive_adapt_pct", 0.03))
            heal_amt = int(p1_max_hp * boss_cfg.get("passive_regen_pct", 0.03) * boss_heal_mult)
            old_hp = p1_hp
            p1_hp = min(p1_max_hp, p1_hp + heal_amt)
            actual_healed = p1_hp - old_hp
            passive_log = (
                f"♾️ **[Nội Tại - The True Adapt (100%)]** Mahoraga thích nghi tuyệt đối: "
                f"Hồi phục **+{actual_healed:,} HP** và **GIẢM {int(mahoraga_adapt_red * 100)}% sát thương phải nhận**!"
            )

        fateria_save_loop_active = False
        player_skills_locked = False
        fate_loop_status_log = None
        ice_spear_active_this_turn = False
        player_heal_mult = 1.0

        if boss_type == "fateria":
            if (boss_skill_erased != "save_loop") and random.random() < FATERIA_BOSS_CONFIG["passive"]["chance"]:
                fateria_save_loop_active = True
                heal_amt = int(p1_max_hp * FATERIA_BOSS_CONFIG["passive"]["heal_pct"])
                old_hp = p1_hp
                p1_hp = min(p1_max_hp, p1_hp + heal_amt)
                actual_healed = p1_hp - old_hp
                passive_log = (
                    f"🔄 **[Passive - Save loop (15%)]** Fateria quay ngược dòng chảy thời gian: "
                    f"Hồi phục **+{actual_healed:,} HP** (30% HP tối đa) và **MIỄN NHIỄM TOÀN BỘ SÁT THƯƠNG** trong turn này!"
                )
            if fateria_fate_loop_turns > 0:
                player_skills_locked = True
                fateria_fate_loop_turns -= 1
                fate_loop_status_log = (
                    f"⛓️ **[Hiệu ứng Fate loop]** Đối thủ **không thể dùng skill** trong hiệp này! "
                    f"(Còn **{fateria_fate_loop_turns}** lượt khóa — hết hiệu ứng sẽ dùng lại skill bình thường)"
                )
            if fateria_ice_spear_turns > 0:
                ice_spear_active_this_turn = True
                fateria_ice_spear_turns -= 1
            player_heal_mult = max(0.0, 1.0 - fateria_heal_reduction)

        reisen_boss_log = None
        boss_molten_log = None
        if boss_mind_turns > 0:
            boss_mind_turns -= 1
            if not player_skills_locked and random.random() < 0.20:
                _mind_dmg = p1_power
                p1_hp = max(0, p1_hp - _mind_dmg)
                reisen_boss_log = f"🌀 **[Red Eye Mind Explosion]** Boss mất kiểm soát tâm trí và **tự gây {_mind_dmg:,} DMG** lên bản thân! (Còn {boss_mind_turns} lượt ảo giác)"

        if boss_molten_ground_turns > 0:
            boss_molten_ground_turns -= 1
            if not player_skills_locked:
                raw_burn = int(p1_max_hp * 0.02)
                actual_burn, p1_true_dmg_accum, cap_burn_msg = apply_raid_true_damage(raw_burn, p1_true_dmg_accum, p1_true_cap, "Bỏng Mặt Đất (Utsuho)")
                if actual_burn > 0:
                    p1_hp = max(0, p1_hp - actual_burn)
                    boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham hạt nhân thiêu đốt Boss gây **{actual_burn:,} DMG** (2% Máu Tối Đa)! (Còn {boss_molten_ground_turns} lượt)"
                else:
                    boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Mặt đất vẫn sôi trào nhưng sát thương chuẩn đã bị triệt tiêu (0 DMG)! (Còn {boss_molten_ground_turns} lượt)"
                if cap_burn_msg:
                    boss_molten_log += f"\n{cap_burn_msg}"

        boss_stunned = False
        sakuya_stun_notif = None
        marisa_spark_notif = None
        flandre_notif = None
        remilia_notif = None
        reisen_notif = None
        cirno_notif = None
        utsuho_notif = None
        boss_molten_log = None
        cirno_freeze_log = None
        yukari_notif = None
        t1_notif = None
        t2_notif = None
        t3_notif = None
        turn_image = FATERIA_BOSS_CONFIG["passive"]["gif"] if fateria_save_loop_active else None

        if not player_skills_locked:
            for c in active_combatants:
                ac = c["team_cards"][c["current_card_index"]]
                if ac["cid"] == 18 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                    if random.random() < 0.40:
                        c["sakuya_stun_used"] = True
                        boss_stunned = True
                        turn_image = EVOL_CONFIG[18]["skill_gif"]
                        sakuya_stun_notif = f"⏳ **[Ace 2] [#18] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss bị **STUN** mất lượt!"
                        break

        if boss_freeze_debuff_turns > 0 and not boss_stunned:
            boss_freeze_debuff_turns -= 1
            if not player_skills_locked and random.random() < 0.45:
                boss_stunned = True
                cirno_freeze_log = f"❄️ **[Perfect Freeze]** Boss bị đóng băng cứng đờ (45%), không thể hành động trong hiệp này! (Còn {boss_freeze_debuff_turns} lượt duy trì)"

        seiki_invul = False
        seiki_action = "normal"
        if boss_type == "seiki" and not boss_stunned:
            if boss_skill_erased == "multi_spark":
                seiki_spark_turns = 0
            if seiki_spark_turns > 0:
                seiki_spark_turns -= 1
                seiki_action = "spark_active"
            else:
                roll_s = random.random()
                if roll_s < 0.15 and boss_skill_erased != "multi_spark":
                    seiki_spark_turns = 2
                    seiki_action = "spark_start"
                elif 0.15 <= roll_s < 0.35 and boss_skill_erased != "fantasy_seal":
                    seiki_invul = True
                    seiki_action = "fantasy_seal"
                elif 0.35 <= roll_s < 0.55 and boss_skill_erased != "blitz_attack":
                    seiki_action = "blitz_attack"
                else:
                    seiki_action = "normal"

        round_player_dmg = 0
        ice_spear_blocked_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ice_spear_active_this_turn and random.random() < 0.40:
                ice_spear_blocked_logs.append(f"❄️ **[Ice spear]** **{ac['name']}** ({c['username']}) bị giáo băng cầm chân (40%), không thể tấn công trong lượt này!")
                continue
            card_dmg = ac["power"]
            if player_skills_locked:
                round_player_dmg += card_dmg
                c["total_dmg"] += card_dmg
                continue
            if ac["cid"] == 19 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = EVOL_CONFIG[19]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#19] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss!"

            # Kỹ năng Yukari Ace 2 tấn công:
            if ac["cid"] == 4 and ac.get("is_ace2"):
                if not c.get("yukari_station_used") and random.random() < 0.30:
                    c["yukari_station_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/7e/69/snvix5aVyjKgjesAJV.gif"
                    yukari_notif = f"🌌 **[Ace 2] [#04] Yukari** ({c['username']}) tung **Trip To The Old Station** (30%)! Sát thương ×2.0 giáng **{card_dmg:,} DMG**!"
                elif not c.get("yukari_lastword_used") and random.random() < 0.25:
                    c["yukari_lastword_used"] = True
                    card_dmg = int(card_dmg * 2.5)
                    boss_stunned = True
                    if not turn_image:
                        turn_image = "https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/03/4b/epgnCZ5A8KOdm.gif"
                    yukari_notif = f"👁️ **[Ace 2] [#04] Yukari** ({c['username']}) kích hoạt **⸮⸮⸮ : Last Word !** (25%)! Bộc phá ×2.5 gây **{card_dmg:,} DMG** và **STUN đối thủ**!"

            if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                if random.random() < 0.25:
                    c["flandre_used"] = True
                    raw_rip = int(p1_hp * 0.30)
                    actual_rip, p1_true_dmg_accum, cap_rip_msg = apply_raid_true_damage(raw_rip, p1_true_dmg_accum, p1_true_cap, "Ripples of 495 Years (Flandre)")
                    p1_hp = max(0, p1_hp - actual_rip)
                    c["total_dmg"] += actual_rip
                    if not turn_image:
                        turn_image = EVOL_CONFIG[9]["skill_gif"]
                    if actual_rip > 0:
                        flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** (25%)! Gây **{actual_rip:,} DMG** sát thương chuẩn lên Boss!"
                    else:
                        flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** nhưng sát thương chuẩn đã chạm trần (0 DMG)!"
                    if cap_rip_msg:
                        flandre_notif += f"\n{cap_rip_msg}"

            if ac["cid"] == 12 and ac["is_ace2"]:
                raw_gungnir = int(p1_max_hp * 0.03)
                actual_gungnir, p1_true_dmg_accum, cap_gungnir_msg = apply_raid_true_damage(raw_gungnir, p1_true_dmg_accum, p1_true_cap, "Thương Đỏ Gungnir (Remilia)")
                card_dmg += actual_gungnir
                if not turn_image:
                    turn_image = EVOL_CONFIG[12]["skill_gif"]
                if actual_gungnir > 0:
                    remilia_notif = f"🩸 **[Ace 2] [#12] Remilia Scarlet** ({c['username']}) - **Thương Đỏ Gungnir** (Thụ động): Gây thêm **{actual_gungnir:,} DMG** (3% Máu tối đa Boss)!"
                else:
                    remilia_notif = f"🩸 **[Ace 2] [#12] Remilia Scarlet** ({c['username']}) - **Thương Đỏ Gungnir**: Sát thương chuẩn đã chạm trần (0 DMG)!"
                if cap_gungnir_msg:
                    remilia_notif += f"\n{cap_gungnir_msg}"

            if ac["cid"] == 21 and ac["is_ace2"] and not c.get("reisen_used"):
                if random.random() < 0.25:
                    c["reisen_used"] = True
                    boss_mind_turns = 4
                    if not turn_image:
                        turn_image = EVOL_CONFIG[21]["skill_gif"]
                    reisen_notif = f"🔴 **[Ace 2] [#21] Reisen Udongein Inaba** ({c['username']}) kích hoạt **Red Eye Mind Explosion** (25%)! 🌀 Boss bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"

            if ac["cid"] == 23 and ac["is_ace2"] and not c.get("cirno_freeze_used"):
                if random.random() < 0.40:
                    c["cirno_freeze_used"] = True
                    boss_freeze_debuff_turns = 2
                    if not turn_image:
                        turn_image = EVOL_CONFIG[23]["skill_gif"]
                    cirno_notif = f"❄️ **[Ace 2] [#23] Cirno** ({c['username']}) kích hoạt **Perfect Freeze** (40%)! Đóng băng đối thủ: Trong 2 turn tiếp theo có **45% không thể đánh trả**!"

            if ac["cid"] == 13 and ac["is_ace2"]:
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 3.0)
                    boss_molten_ground_turns = 3
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    utsuho_notif = f"☢️ **[Ace 2] [#13] Utsuho Reiuji** ({c['username']}) bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{card_dmg:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa cho bài địch trong 3 turn)!"

            if str(ac["cid"]).lower() == "t1":
                if ac.get("is_ace2"):
                    _t1 = t1_ace2_attack(c, ac, p1_rounds, p1_max_hp, f"Boss {boss_cfg['name']}", is_boss=True)
                    if _t1.get("multiplier", 1.0) > 1.0:
                        card_dmg = int(card_dmg * _t1["multiplier"])
                    if _t1["bonus"]:
                        raw_cleave = _t1["bonus"]
                        actual_cleave, p1_true_dmg_accum, cap_cleave_msg = apply_raid_true_damage(raw_cleave, p1_true_dmg_accum, p1_true_cap, "Cleave (Seiki Ace 2)")
                        card_dmg += actual_cleave
                        if cap_cleave_msg:
                            _t1["logs"].append(cap_cleave_msg)
                    if _t1["direct"]:
                        raw_bong = _t1["direct"]
                        actual_bong, p1_true_dmg_accum, cap_bong_msg = apply_raid_true_damage(raw_bong, p1_true_dmg_accum, p1_true_cap, "Bóng Khái Niệm (Seiki Ace 2)")
                        p1_hp = max(0, p1_hp - actual_bong)
                        c["total_dmg"] += actual_bong
                        if cap_bong_msg:
                            _t1["logs"].append(cap_bong_msg)
                    if _t1.get("invul"):
                        c["seiki_seal_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        c["seiki_invul_turn"] = p1_rounds
                    if _t1["disable"]:
                        boss_skill_erased, erase_msg = apply_bong_khai_niem_boss(boss_type, 1, boss_skill_erased)
                        _t1["logs"].append(erase_msg)
                        if boss_skill_erased == "multi_spark":
                            seiki_spark_turns = 0
                            if seiki_action in ("spark_start", "spark_active"):
                                seiki_action = "normal"
                        elif boss_skill_erased == "fantasy_seal" and seiki_action == "fantasy_seal":
                            seiki_invul = False
                            seiki_action = "normal"
                        elif boss_skill_erased == "blitz_attack" and seiki_action == "blitz_attack":
                            seiki_action = "normal"
                        elif boss_skill_erased == "save_loop":
                            fateria_save_loop_active = False
                    if _t1["heal"]:
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + int(_t1["heal"] * player_heal_mult))
                    if _t1["gif"] and not turn_image:
                        turn_image = _t1["gif"]
                    t1_notif = (t1_notif + "\n" if t1_notif else "") + "\n".join(_t1["logs"])
                elif c.get("seiki_used_turn") != p1_rounds:
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
                        heal_val = int(ac["max_hp"] * 0.30 * player_heal_mult)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image:
                            turn_image = T1_HEAL_GIF
                        passive_log = (passive_log + "\n" if passive_log else "") + f"💚 **[Nhóm T] [#t1] Seiki** ({c['username']}) thi triển **Medicine Sign** (20%)! Hồi phục **+{heal_val:,} HP** cho bản thân! ({ac['current_hp']:,}/{ac['max_hp']:,} HP)"

            if str(ac["cid"]).lower() == "t2":
                heal_mahoraga = int(ac["max_hp"] * 0.05 * player_heal_mult)
                ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_mahoraga)
                c["mahoraga_adapt_turns"] = c.get("mahoraga_adapt_turns", 0) + 1
                adapt_pct = min(0.90, c["mahoraga_adapt_turns"] * 0.05)
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 1.5)
                    if not turn_image:
                        turn_image = T2_THOAI_MA_GIF
                    t2_notif_str = (
                        f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt** "
                        f"(Hồi +{heal_mahoraga:,} HP, Kháng ST {int(adapt_pct*100)}%) & vung **Thoái Ma Kiếm** (30%)! "
                        f"Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss!"
                    )
                else:
                    if not turn_image:
                        turn_image = T2_PASSIVE_GIF
                    t2_notif_str = (
                        f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt**! "
                        f"Hồi phục **+{heal_mahoraga:,} HP** ({ac['current_hp']:,}/{ac['max_hp']:,} HP) và tăng kháng sát thương lên **{int(adapt_pct*100)}%**!"
                    )
                t2_notif = (t2_notif + "\n" if t2_notif else "") + t2_notif_str

            if str(ac["cid"]).lower() == "t3":
                t3_st = c.setdefault("t3_state", {})
                _t3 = t3_combat_turn(t3_st, ac, p1_rounds, p1_max_hp, f"Boss {boss_cfg['name']}", is_ace2=ac.get("is_ace2"))
                card_dmg = int(card_dmg * _t3["multiplier"])
                if _t3["bonus_hp_dmg"] > 0:
                    actual_hp_dmg, p1_true_dmg_accum, cap_hp_msg = apply_raid_true_damage(_t3["bonus_hp_dmg"], p1_true_dmg_accum, p1_true_cap, "Dark Chain (Kizuna)")
                    card_dmg += actual_hp_dmg
                    if cap_hp_msg:
                        _t3["logs"].append(cap_hp_msg)
                if _t3["gif"] and not turn_image:
                    turn_image = _t3["gif"]
                t3_notif_str = "\n".join(_t3["logs"])
                t3_notif = (t3_notif + "\n" if t3_notif else "") + t3_notif_str

            if str(ac["cid"]).lower() == "t4":
                t4_st = c.setdefault("t4_state", {})
                _t4 = t4_combat_turn(t4_st, ac, f"Boss {boss_cfg['name']}", heal_mult=player_heal_mult, enemy_fate_loop_turns=boss_fate_locked_turns)
                card_dmg = int(card_dmg * _t4["multiplier"])
                if _t4["save_loop_invul"]:
                    c["seiki_invul_turn"] = p1_rounds
                    ac["current_hp"] += p1_power
                if _t4["fate_loop_triggered"]:
                    boss_fate_locked_turns = 2
                    boss_skills_locked_this_turn = True
                    if boss_type == "seiki":
                        seiki_invul = False
                        seiki_action = "normal"
                if _t4["heal_reduce_triggered"]:
                    boss_heal_mult = 0.70
                if _t4["ice_spear_triggered"]:
                    boss_ice_spear_turns = 2
                if _t4["gif"] and not turn_image:
                    turn_image = _t4["gif"]
                if _t4["logs"]:
                    t4_str = "\n".join([f"({c['username']}) {l}" for l in _t4["logs"]])
                    t3_notif = (t3_notif + "\n" if t3_notif else "") + t4_str

            round_player_dmg += card_dmg
            c["total_dmg"] += card_dmg

        if boss_type == "seiki" and seiki_invul and not boss_stunned:
            player_atk_str = f"🛡️ Toàn quân dồn **{round_player_dmg:,} DMG** nhưng **Seiki Dị Hình** đã kích hoạt **Fantasy Seal**, MIỄN TOÀN BỘ SÁT THƯƠNG trong hiệp này!"
        elif boss_type == "fateria" and fateria_save_loop_active:
            player_atk_str = f"🔄 Toàn quân dồn **{round_player_dmg:,} DMG** nhưng **Fateria** đã kích hoạt **Save loop (15%)**, **MIỄN NHIỄM TOÀN BỘ SÁT THƯƠNG** trong turn này!"
        else:
            if boss_type == "mahoraga":
                mahoraga_reduced_dmg = int(round_player_dmg * (1.0 - mahoraga_adapt_red))
                p1_hp = max(0, p1_hp - mahoraga_reduced_dmg)
                player_atk_str = (
                    f"Toàn quân dồn **{round_player_dmg:,} DMG**, nhưng **[The True Adapt]** của Mahoraga đã thích nghi: "
                    f"Chặn đứng và giảm còn **{mahoraga_reduced_dmg:,} DMG** (Giảm {int(mahoraga_adapt_red * 100)}% - cộng dồn mỗi hiệp)!"
                )
            else:
                p1_hp = max(0, p1_hp - round_player_dmg)
                player_atk_str = f"Toàn quân gây **{round_player_dmg:,} DMG** lên Boss!"
        if ice_spear_blocked_logs:
            player_atk_str += "\n" + "\n".join(ice_spear_blocked_logs)

        if not boss_stunned and boss_ice_spear_this_turn and random.random() < 0.40:
            boss_stunned = True
            cirno_freeze_log = (cirno_freeze_log + "\n" if cirno_freeze_log else "") + "❄️ **[Ice spear - #t4 Fateria]** Giáo băng cầm chân khiến Boss không thể tấn công trong lượt này (40%)!"
        if boss_skills_locked_this_turn:
            seiki_invul = False
            seiki_action = "normal"
            fateria_save_loop_active = False

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
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(4000 * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= 4000
                elif seiki_action in ["spark_start", "spark_active"]:
                    turn_image = SEIKI_BOSS_CONFIG["skills"]["multi_spark"]["gif"]
                    num_front = len(frontline_cards)
                    curr_dmg = int(p1_power * 1.5)
                    dmg_per_card = max(100, curr_dmg // num_front)
                    if seiki_action == "spark_start":
                        boss_action_log = f"🌟 **[KỸ NĂNG] Seiki Dị Hình** bộc phát **Multi Master Spark (15%)**! Cường hóa x1.5 sát thương trong 3 lượt và giáng **{curr_dmg:,} DMG** chia đều **{dmg_per_card:,} DMG** lên mỗi thẻ tiền tuyến ({num_front} lá)!"
                    else:
                        boss_action_log = f"🌟 **[Multi Master Spark Duy Trì]** Sát thương cường hóa x1.5, giáng **{curr_dmg:,} DMG** chia đều **{dmg_per_card:,} DMG** lên mỗi thẻ tiền tuyến ({num_front} lá)! (Còn {seiki_spark_turns} lượt)"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(dmg_per_card * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= dmg_per_card
                else:
                    num_front = len(frontline_cards)
                    dmg_per_card = max(100, p1_power // num_front)
                    boss_action_log = f"⚔️ Seiki Dị Hình phóng đạn hắc ám tổng **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(dmg_per_card * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= dmg_per_card
        elif boss_type == "mahoraga":
            if p1_hp <= 0:
                boss_action_log = "💥 **Bát Ách Kiếm Thần Tướng Mahoraga đã bị đánh bại! Thần tướng tan biến vào hư không!**"
            elif boss_stunned:
                boss_action_log = "❄️ Mahoraga bị đóng băng thời gian, bất lực không thể ra đòn!"
            else:
                if (boss_skill_erased != "thoai_ma_kiem") and random.random() < MAHORAGA_BOSS_CONFIG["skills"]["thoai_ma_kiem"]["chance"]:
                    turn_image = MAHORAGA_BOSS_CONFIG["skills"]["thoai_ma_kiem"]["gif"]
                    target_c = random.choice(active_combatants)
                    ac = target_c["team_cards"][target_c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 15 and ac["is_ace2"] and not target_c["reimu_invul_used"]:
                        if random.random() < 0.40:
                            target_c["reimu_invul_used"] = True
                            invul = True
                            turn_image = EVOL_CONFIG[15]["skill_gif"]
                            boss_action_log = (
                                f"⚔️ **[KỸ NĂNG] Mahoraga** rút kiếm tung **THOÁI MA KIẾM** (25%)! "
                                f"Trường kiếm khổng lồ giáng **{p1_power:,} DMG sát thương thuần** (không chia đều) thẳng vào **{ac['name']}** ({target_c['username']})!\n"
                                f"🛡️ **[Ace 2] [#15] Reimu** ({target_c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                            )
                    if not invul and str(ac["cid"]).lower() == "t1" and (target_c.get("seiki_invul_turn") == p1_rounds or (not target_c.get("seiki_seal_used") and target_c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                        target_c["seiki_seal_used"] = True
                        target_c["seiki_used_turn"] = p1_rounds
                        invul = True
                        turn_image = T1_SEAL_GIF
                        title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                        pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                        boss_action_log = (
                            f"⚔️ **[KỸ NĂNG] Mahoraga** rút kiếm tung **THOÁI MA KIẾM** (25%)! "
                            f"Trường kiếm khổng lồ giáng **{p1_power:,} DMG sát thương thuần** (không chia đều) thẳng vào **{ac['name']}** ({target_c['username']})!\n"
                            f"🛡️ **{title_t1}** ({target_c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        )
                    if not invul:
                        if str(ac["cid"]).lower() == "t2":
                            adapt_pct = min(0.90, target_c.get("mahoraga_adapt_turns", 1) * 0.05)
                            actual_dmg = int(p1_power * (1.0 - adapt_pct))
                            ac["current_hp"] -= actual_dmg
                            boss_action_log = (
                                f"⚔️ **[KỸ NĂNG] Mahoraga** rút kiếm tung **THOÁI MA KIẾM** (25%)! "
                                f"Trường kiếm khổng lồ giáng **{p1_power:,} DMG** thẳng vào **{ac['name']}** ({target_c['username']})!\n"
                                f"🛡️ **[Nhóm T] [#t2] Mahoraga** Thích Nghi (The True Adapt: -{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            )
                        else:
                            ac["current_hp"] -= p1_power
                            boss_action_log = (
                                f"⚔️ **[KỸ NĂNG] Mahoraga** rút kiếm tung **THOÁI MA KIẾM** (25%)! "
                                f"Trường kiếm khổng lồ giáng **{p1_power:,} DMG sát thương thuần** (không chia đều) thẳng vào **{ac['name']}** ({target_c['username']})!"
                            )
                else:
                    num_front = len(frontline_cards)
                    dmg_per_card = max(100, p1_power // num_front)
                    boss_action_log = f"⚔️ Mahoraga đánh thường tổng **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(dmg_per_card * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= dmg_per_card
        elif boss_type == "fateria":
            if p1_hp <= 0:
                boss_action_log = "💥 **Fateria – Khuôn mẫu của số phận đã bị đánh bại! Dòng chảy thời gian trở lại bình thường!**"
            elif boss_stunned:
                boss_action_log = "❄️ Fateria bị đóng băng thời gian, bất lực không thể ra đòn!"
            else:
                num_front = len(frontline_cards)
                # Lưu ý: Fate loop không lặp lại cho đến khi hết 2 turn hiệu ứng
                can_cast_fate_loop = (not boss_skills_locked_this_turn) and (boss_skill_erased != "fate_loop") and (fateria_fate_loop_turns == 0) and (not player_skills_locked)
                fate_chance = FATERIA_BOSS_CONFIG["skills"]["fate_loop"].get("chance", 0.10)
                clone_chance = FATERIA_BOSS_CONFIG["skills"]["clone_attack"].get("chance", 0.20)
                fateria_skill_gif = None

                if can_cast_fate_loop and random.random() < fate_chance:
                    fateria_fate_loop_turns = 2
                    player_skills_locked = True
                    fateria_skill_gif = FATERIA_BOSS_CONFIG["skills"]["fate_loop"]["gif"]
                    turn_image = fateria_skill_gif
                    dmg_per_card = max(100, p1_power // num_front)
                    boss_action_log = (
                        f"⛓️ **[SKILL 1] Fateria** kích hoạt **Fate loop ({int(fate_chance*100)}%)**! "
                        f"Khiến đối thủ **không thể dùng skill trong 2 turn liên tiếp** (không lặp lại cho đến khi hết 2 turn)!\n"
                        f"⚔️ Sát thương kèm theo: **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá tiền tuyến ({num_front} lá)!"
                    )
                    is_normal_atk = False
                elif (not boss_skills_locked_this_turn) and (boss_skill_erased != "clone_attack") and random.random() < clone_chance:
                    clones_cfg = FATERIA_BOSS_CONFIG["skills"]["clone_attack"]["clones"]
                    chosen_clone_key = random.choice(["thunder_blaze", "the_fallen_hero", "ice_spear"])
                    c_info = clones_cfg[chosen_clone_key]
                    fateria_skill_gif = c_info["gif"]
                    turn_image = fateria_skill_gif
                    total_clone_dmg = int(p1_power * c_info["multiplier"])
                    dmg_per_card = max(100, total_clone_dmg // num_front)
                    is_normal_atk = False

                    if chosen_clone_key == "thunder_blaze":
                        boss_action_log = (
                            f"⚡ **[SKILL 2 - Clone Attack] Fateria** triệu hồi con rối tung **Thunder blaze**! "
                            f"Những ngọn lửa chớp điện phập phờn gây **2.3x DMG ({total_clone_dmg:,} DMG)**, chia đều **{dmg_per_card:,} DMG** lên mỗi thẻ ({num_front} lá)!"
                        )
                    elif chosen_clone_key == "the_fallen_hero":
                        fateria_heal_reduction = 0.30
                        boss_action_log = (
                            f"🗡️ **[SKILL 2 - Clone Attack] Fateria** triệu hồi con rối tung **The fallen hero**! "
                            f"Tung trảm kích ánh sáng **1.5x DMG ({total_clone_dmg:,} DMG)**, chia đều **{dmg_per_card:,} DMG** ({num_front} lá) và **GIẢM 30% HEAL**!"
                        )
                    else:
                        fateria_ice_spear_turns = 2
                        boss_action_log = (
                            f"❄️ **[SKILL 2 - Clone Attack] Fateria** triệu hồi con rối phóng **Ice spear**! "
                            f"Những ngọn giáo băng **1.5x DMG ({total_clone_dmg:,} DMG)**, chia đều **{dmg_per_card:,} DMG** ({num_front} lá) và khiến đối phương **40% không tấn công trong 2 lượt sau**!"
                        )
                else:
                    dmg_per_card = max(100, p1_power // num_front)
                    boss_action_log = f"⚔️ Fateria đánh thường tổng **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                    is_normal_atk = True

                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if not player_skills_locked:
                        if is_normal_atk and ac["cid"] == 4 and ac.get("is_ace2") and random.random() < 0.10:
                            invul = True
                            if not fateria_save_loop_active:
                                p1_hp = max(0, p1_hp - dmg_per_card)
                                c["total_dmg"] += dmg_per_card
                            boss_action_log += f"\n🌀 **[Ace 2] [#04] Yukari** ({c['username']}) kích hoạt **Invisible Gap (10%)**! Phản lại **{dmg_per_card:,} DMG** đánh thường!"
                        elif ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                if not fateria_skill_gif:
                                    turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            if not fateria_skill_gif:
                                turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t3" and c.get("t3_state", {}).get("wonder_guard_turns", 0) > 0:
                            c["t3_state"]["wonder_guard_turns"] -= 1
                            invul = True
                            ref_dmg = int(dmg_per_card * 0.60)
                            if not fateria_save_loop_active:
                                p1_hp = max(0, p1_hp - ref_dmg)
                                c["total_dmg"] += ref_dmg
                            if fateria_fate_loop_turns == 2:
                                fateria_fate_loop_turns = 0
                                boss_action_log += f"\n🛡️ **[Wonder Guard]** **{ac['name']}** ({c['username']}) hóa giải **Fate loop** của Fateria!"
                            if fateria_ice_spear_turns == 2:
                                fateria_ice_spear_turns = 0
                                boss_action_log += f"\n🛡️ **[Wonder Guard]** **{ac['name']}** ({c['username']}) phản ngược **Ice spear**!"
                            boss_action_log += f"\n🛡️ **[Ace 2] [#t3] Kizuna** ({c['username']}) duy trì **Wonder Guard**! Miễn thương và phản lại **{ref_dmg:,} DMG (60%)**!"
                    if not invul:
                        if (not player_skills_locked) and str(ac["cid"]).lower() == "t2":
                            adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                            actual_dmg = int(dmg_per_card * (1.0 - adapt_pct))
                            ac["current_hp"] -= actual_dmg
                            boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                        else:
                            ac["current_hp"] -= dmg_per_card
        else:
            if p1_hp <= 0:
                boss_action_log = "💥 **Reimu Dị Hình Phase 1 đã bị đánh gục hoàn toàn!**"
            elif boss_stunned:
                boss_action_log = "❄️ Boss bị đóng băng thời gian, bất lực không thể phản công!"
            else:
                if (boss_skill_erased != "di_hinh_bua_chu") and random.random() < 0.20:
                    turn_image = BOSS_SKILL_CONFIG["gif"]
                    boss_action_log = "👹 **[NỘI TẠI BOSS] Reimu Dị Hình** thi triển **Dị Hình Bùa Chú** (20%)! Giáng **5,000 DMG** diện rộng!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                if not turn_image or turn_image == BOSS_SKILL_CONFIG["gif"]:
                                    turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(5000 * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= 5000
                else:
                    num_front = len(frontline_cards)
                    dmg_per_card = max(100, p1_power // num_front)
                    boss_action_log = f"⚔️ Boss đánh thường tổng **{p1_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p1_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p1_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(dmg_per_card * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
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
            round_embed.add_field(name="💚 Nội Tại / Passive Boss:", value=passive_log, inline=False)
        if fate_loop_status_log:
            round_embed.add_field(name="⛓️ Phong Ấn Kỹ Năng (Fate Loop):", value=fate_loop_status_log, inline=False)
        round_embed.add_field(name="💥 Tiền Tuyến Tấn Công:", value=player_atk_str, inline=False)
        if sakuya_stun_notif:
            round_embed.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
        if yukari_notif:
            round_embed.add_field(name="🌌 Cảnh Giới Yukari Ace 2:", value=yukari_notif, inline=False)
        if marisa_spark_notif:
            round_embed.add_field(name="🌟 Master Spark Oanh Tạc:", value=marisa_spark_notif, inline=False)
        if remilia_notif:
            round_embed.add_field(name="🩸 Thương Đỏ Gungnir:", value=remilia_notif, inline=False)
        if reisen_notif:
            round_embed.add_field(name="🔴 Red Eye Mind Explosion:", value=reisen_notif, inline=False)
        if reisen_boss_log:
            round_embed.add_field(name="🌀 Ảo Giác Tâm Trí:", value=reisen_boss_log, inline=False)
        if cirno_notif:
            round_embed.add_field(name="❄️ Perfect Freeze (Cirno):", value=cirno_notif, inline=False)
        if cirno_freeze_log:
            round_embed.add_field(name="🧊 Băng Đóng Tuyệt Đối:", value=cirno_freeze_log, inline=False)
        if utsuho_notif:
            round_embed.add_field(name="☢️ Nuclear Spell Card (Utsuho):", value=utsuho_notif, inline=False)
        if boss_molten_log:
            round_embed.add_field(name="🌋 Mặt Đất Nung Chảy:", value=boss_molten_log, inline=False)
        if flandre_notif:
            round_embed.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
        if t1_notif:
            round_embed.add_field(name="🔮 Tuyệt Kỹ [Ace 2] [#t1] Seiki:", value=t1_notif, inline=False)
        if t2_notif:
            round_embed.add_field(name="🔱 Thần Tướng [Nhóm T] [#t2] Mahoraga:", value=t2_notif, inline=False)
        if t3_notif:
            round_embed.add_field(name="🩸 Hoàng Đế [Nhóm T] [#t3] Kizuna:", value=t3_notif, inline=False)
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
                *([("💚 Nội Tại / Passive Boss:", passive_log, False)] if passive_log else []),
                *([("⛓️ Phong Ấn Kỹ Năng (Fate Loop):", fate_loop_status_log, False)] if fate_loop_status_log else []),
                ("💥 Tiền Tuyến Tấn Công:", player_atk_str, False),
                *([("❄️ Kỹ Năng Đột Biến:", sakuya_stun_notif, False)] if sakuya_stun_notif else []),
                *([("🌟 Master Spark:", marisa_spark_notif, False)] if marisa_spark_notif else []),
                *([("🩸 Thương Đỏ Gungnir:", remilia_notif, False)] if remilia_notif else []),
                *([("🔴 Red Eye Mind Explosion:", reisen_notif, False)] if reisen_notif else []),
                *([("🌀 Ảo Giác Tâm Trí:", reisen_boss_log, False)] if reisen_boss_log else []),
                *([("❄️ Perfect Freeze (Cirno):", cirno_notif, False)] if cirno_notif else []),
                *([("🧊 Băng Đóng Tuyệt Đối:", cirno_freeze_log, False)] if cirno_freeze_log else []),
                *([("☢️ Nuclear Spell Card (Utsuho):", utsuho_notif, False)] if utsuho_notif else []),
                *([("🌋 Mặt Đất Nung Chảy:", boss_molten_log, False)] if boss_molten_log else []),
                *([("🦇 Ripples of 495 Years:", flandre_notif, False)] if flandre_notif else []),
                *([("🔮 Tuyệt Kỹ [Ace 2] [#t1] Seiki:", t1_notif, False)] if t1_notif else []),
                *([("🔱 Thần Tướng [Nhóm T] [#t2] Mahoraga:", t2_notif, False)] if t2_notif else []),
                *([("🩸 Hoàng Đế [Nhóm T] [#t3] Kizuna:", t3_notif, False)] if t3_notif else []),
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

        await asyncio.sleep(3.0)

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
        if boss_type == "fateria":
            if roll < 0.10:
                t_val = 30.0
                d_str = "👑 **+30 Vé** (10%)"
            elif roll < 0.50:
                t_val = 15.0
                d_str = "🔥 **+15 Vé** (40%)"
            else:
                t_val = 10.0
                d_str = "💎 **+10 Vé** (50%)"
        elif boss_type == "mahoraga":
            if roll < 0.10:
                t_val = 20.0
                d_str = "👑 **+20 Vé** (10%)"
            elif roll < 0.50:
                t_val = 15.0
                d_str = "🔥 **+15 Vé** (40%)"
            else:
                t_val = 10.0
                d_str = "💎 **+10 Vé** (50%)"
        else:
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
        p_shards = p.setdefault("shards", {})
        if boss_type == "fateria":
            if random.random() < 0.05:
                p_shards["fateria"] = p_shards.get("fateria", 0) + 1
                items_won.append(f"⏳ **+1 Fateria Shard** (5% Siêu Hiếm! Kho: {p_shards['fateria']} mảnh)")
        elif boss_type == "mahoraga":
            if random.random() < 0.05:
                p_shards["mahoraga"] = p_shards.get("mahoraga", 0) + 1
                items_won.append(f"🔱 **+1 Mảnh Mahoraga** (5% Siêu Hiếm! Kho: {p_shards['mahoraga']} mảnh)")
        else:
            if random.random() < 0.025:
                p_shards["seiki"] = p_shards.get("seiki", 0) + 1
                cur_shards = p_shards["seiki"]
                shard_notice = f"🔮 **+1 Mảnh Seiki** (2.5% Siêu Hiếm! Kho: {cur_shards}/10)"
                if cur_shards >= 10:
                    shard_notice += " ✨ *(Đã đủ 10 mảnh! Dùng `/t translate`)*"
                items_won.append(shard_notice)

        p["pull_tickets"] += t_val
        p["xp"] += 100
        dq_notifs = update_daily_quest_progress(p, "raid", 1)
        ev_notifs = update_event_quest_progress(p, "raid", 1)
        all_n = dq_notifs + ev_notifs
        for n in all_n:
            items_won.append(n)
        save_player(p)
        p1_rewards_data[uid] = {"total_pulls": t_val, "items": items_won, "username": p["username"]}
        
    if boss_type == "mahoraga":
        total_raid_dmg = sum(c["total_dmg"] for c in combatants)
        final_embed = discord.Embed(
            title="⚔️ KẾT QUẢ ĐẠI CHIẾN: BÁT ÁCH KIẾM THẦN TƯỚNG MAHORAGA!",
            description=(
                "🌸 **Reimu thở phào nhẹ nhõm:** *\"Phù... cuối cùng cũng hạ được cái thứ yêu quái đó. "
                "Vụ này chắc chắn là do thằng nhóc đầu nhím kia gây ra rồi...\"*\n\n"
                f"🎉 Đội quân đã hạ gục **Mahoraga** sau **{p1_rounds} hiệp**!\n"
                f"💥 **Tổng Sát Thương:** **{total_raid_dmg:,} DMG**\n"
                f"⏳ **Hồi chiêu Boss tiếp theo:** **15 phút**"
            ),
            color=0x10B981
        )
        final_embed.set_thumbnail(url=boss_cfg["image"])
        m_summary = [
            f"🏆 **{r['username']}**: Nhận **+{r['total_pulls']:.0f} Vé Pull** ({r['items'][0]}) + 100 XP!"
            + (f"\n   └ {r['items'][1]}" if len(r["items"]) > 1 else "")
            for r in p1_rewards_data.values()
        ]
        final_embed.add_field(
            name="🎁 Phần Thưởng (10% 20 vé, 40% 15 vé, 50% 10 vé, 5% Mảnh Mahoraga):",
            value="\n".join(m_summary),
            inline=False
        )
        await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))
        return

    if boss_type == "fateria":
        total_raid_dmg = sum(c["total_dmg"] for c in combatants)
        final_embed = discord.Embed(
            title="⚔️ KẾT QUẢ ĐẠI CHIẾN: FATERIA – KHUÔN MẪU CỦA SỐ PHẬN!",
            description=(
                "🌸 **Reimu:** *\"Vòng lặp thời gian đã bị phá vỡ! Kẻ thao túng những con rối số phận đã bị thanh tẩy hoàn toàn!\"*\n\n"
                f"🎉 Đội quân đã hạ gục **Fateria – Khuôn mẫu của số phận** sau **{p1_rounds} hiệp**!\n"
                f"💥 **Tổng Sát Thương:** **{total_raid_dmg:,} DMG**\n"
                f"⏳ **Hồi chiêu Boss tiếp theo:** **15 phút**"
            ),
            color=0x0EA5E9
        )
        final_embed.set_thumbnail(url=boss_cfg["image"])
        f_summary = [
            f"🏆 **{r['username']}**: Nhận **+{r['total_pulls']:.0f} Vé Pull** ({r['items'][0]}) + 100 XP!"
            + (f"\n   └ {r['items'][1]}" if len(r["items"]) > 1 else "")
            for r in p1_rewards_data.values()
        ]
        final_embed.add_field(
            name="🎁 Phần Thưởng (10% 30 vé, 40% 15 vé, 50% 10 vé, 5% Fateria Shards):",
            value="\n".join(f_summary),
            inline=False
        )
        await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))
        return
    # ========================================================================
    # PHASE 2: SEIKI DỊ HÌNH - THỨC TỈNH (90K HP / 10K DMG / NUCLEAR + CLEAVE)
    # ========================================================================
    if boss_type == "seiki":
        p2_cfg = SEIKI_BOSS_PHASE2_CONFIG
        p2_alert_embed = discord.Embed(
            title="🚨 MA LỰC DỊ TÀ BÙNG NỔ - SEIKI DỊ HÌNH THỨC TỈNH! (PHASE 2)",
            description=(
                f"🌸 **Reimu thảng thốt:** *\"{p2_cfg['reimu_quote']}\"*\n\n"
                f"👺 **{p2_cfg['name']}** đã thức tỉnh ma lực dị tà tối thượng!\n"
                f"❤️ **Máu tăng lên:** **`{p2_cfg['hp']:,} HP`**\n"
                f"⚔️ **Sát thương đánh thường:** **`{p2_cfg['power']:,} DMG`** *(chia đều tiền tuyến, kèm nội tại **Cleave** +20% Máu tối đa mục tiêu)*\n"
                f"☢️ **Nuclear Spell Card (15%):** Gây **10,000 DMG** lên **TẤT CẢ** lá bài tiền tuyến!\n\n"
                f"✨ **PHÉP MÀU THANH TẨY:**\n"
                f"**Lập tức hồi sinh và hồi 100% sinh lực toàn bộ thẻ bài của tất cả dũng giả!**"
            ),
            color=0x7C3AED
        )
        p2_alert_embed.set_image(url=p2_cfg["image"])
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
            c["reisen_used"] = False
            c["cirno_freeze_used"] = False
            c["seiki_seal_used"] = False
            c["seiki_spark_used"] = False
            c["seiki_heal_used"] = False
            c["seiki_used_turn"] = -1
            c["seal_used"] = False
            c["bong_used"] = False
            c["med_used"] = False
            for card in c["team_cards"]:
                card["current_hp"] = card["max_hp"]

        p2_max_hp = p2_cfg["hp"]
        p2_hp = p2_max_hp
        p2_power = p2_cfg["power"]
        p2_rounds = 0
        boss_mind_turns = 0
        boss_freeze_debuff_turns = 0
        boss_molten_ground_turns = 0
        boss_skill_erased = None

        p2_true_cap = int(p2_max_hp * 0.50)
        p2_true_dmg_accum = 0

        while p2_hp > 0 and p2_rounds < max_rounds:
            active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
            if not active_combatants:
                break

            p2_rounds += 1
            frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

            reisen_boss_log = None
            if boss_mind_turns > 0:
                boss_mind_turns -= 1
                if random.random() < 0.20:
                    _mind_dmg = p2_power
                    p2_hp = max(0, p2_hp - _mind_dmg)
                    reisen_boss_log = f"🌀 **[Red Eye Mind Explosion]** Boss mất kiểm soát tâm trí và **tự gây {_mind_dmg:,} DMG** lên bản thân! (Còn {boss_mind_turns} lượt ảo giác)"

            if boss_molten_ground_turns > 0:
                boss_molten_ground_turns -= 1
                raw_burn = int(p2_max_hp * 0.02)
                actual_burn, p2_true_dmg_accum, cap_burn_msg = apply_raid_true_damage(raw_burn, p2_true_dmg_accum, p2_true_cap, "Bỏng Mặt Đất (Utsuho)")
                if actual_burn > 0:
                    p2_hp = max(0, p2_hp - actual_burn)
                    boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham hạt nhân thiêu đốt Boss Phase 2 gây **{actual_burn:,} DMG** (2% Máu Tối Đa)! (Còn {boss_molten_ground_turns} lượt)"
                else:
                    boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Mặt đất vẫn sôi trào nhưng sát thương chuẩn đã bị triệt tiêu (0 DMG)! (Còn {boss_molten_ground_turns} lượt)"
                if cap_burn_msg:
                    boss_molten_log += f"\n{cap_burn_msg}"

            boss_stunned = False
            sakuya_stun_notif = None
            marisa_spark_notif = None
            flandre_notif = None
            remilia_notif = None
            reisen_notif = None
            cirno_notif = None
            utsuho_notif = None
            boss_molten_log = None
            cirno_freeze_log = None
            t1_notif = None
            t2_notif = None
            t3_notif = None
            turn_image = None

            for c in active_combatants:
                ac = c["team_cards"][c["current_card_index"]]
                if ac["cid"] == 18 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                    if random.random() < 0.40:
                        c["sakuya_stun_used"] = True
                        boss_stunned = True
                        turn_image = EVOL_CONFIG[19]["skill_gif"]
                        sakuya_stun_notif = f"⏳ **[Ace 2] [#18] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss Phase 2 bị **STUN**!"
                        break

            if boss_freeze_debuff_turns > 0 and not boss_stunned:
                boss_freeze_debuff_turns -= 1
                if random.random() < 0.45:
                    boss_stunned = True
                    cirno_freeze_log = f"❄️ **[Perfect Freeze]** Boss Phase 2 bị đóng băng cứng đờ (45%), không thể hành động trong hiệp này! (Còn {boss_freeze_debuff_turns} lượt duy trì)"

            round_player_dmg = 0
            for c in active_combatants:
                ac = c["team_cards"][c["current_card_index"]]
                card_dmg = ac["power"]
                if ac["cid"] == 19 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                    if random.random() < 0.30:
                        c["marisa_spark_used"] = True
                        card_dmg = int(card_dmg * 2.0)
                        if not turn_image:
                            turn_image = EVOL_CONFIG[19]["skill_gif"]
                        marisa_spark_notif = f"🌟 **[Ace 2] [#19] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"

                if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                    if random.random() < 0.25:
                        c["flandre_used"] = True
                        raw_rip = int(p2_hp * 0.30)
                        actual_rip, p2_true_dmg_accum, cap_rip_msg = apply_raid_true_damage(raw_rip, p2_true_dmg_accum, p2_true_cap, "Ripples of 495 Years (Flandre)")
                        p2_hp = max(0, p2_hp - actual_rip)
                        c["total_dmg"] += actual_rip
                        if not turn_image:
                            turn_image = EVOL_CONFIG[9]["skill_gif"]
                        if actual_rip > 0:
                            flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** (25%)! Gây **{actual_rip:,} DMG** sát thương chuẩn lên Boss Phase 2!"
                        else:
                            flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** nhưng sát thương chuẩn đã chạm trần (0 DMG)!"
                        if cap_rip_msg:
                            flandre_notif += f"\n{cap_rip_msg}"

                if ac["cid"] == 12 and ac["is_ace2"]:
                    raw_gungnir = int(p2_max_hp * 0.03)
                    actual_gungnir, p2_true_dmg_accum, cap_gungnir_msg = apply_raid_true_damage(raw_gungnir, p2_true_dmg_accum, p2_true_cap, "Thương Đỏ Gungnir (Remilia)")
                    card_dmg += actual_gungnir
                    if not turn_image:
                        turn_image = EVOL_CONFIG[12]["skill_gif"]
                    if actual_gungnir > 0:
                        remilia_notif = f"🩸 **[Ace 2] [#12] Remilia Scarlet** ({c['username']}) - **Thương Đỏ Gungnir** (Thụ động): Gây thêm **{actual_gungnir:,} DMG** (3% Máu tối đa Boss Phase 2)!"
                    else:
                        remilia_notif = f"🩸 **[Ace 2] [#12] Remilia Scarlet** ({c['username']}) - **Thương Đỏ Gungnir**: Sát thương chuẩn đã chạm trần (0 DMG)!"
                    if cap_gungnir_msg:
                        remilia_notif += f"\n{cap_gungnir_msg}"

                if ac["cid"] == 21 and ac["is_ace2"] and not c.get("reisen_used"):
                    if random.random() < 0.25:
                        c["reisen_used"] = True
                        boss_mind_turns = 4
                        if not turn_image:
                            turn_image = EVOL_CONFIG[21]["skill_gif"]
                        reisen_notif = f"🔴 **[Ace 2] [#21] Reisen Udongein Inaba** ({c['username']}) kích hoạt **Red Eye Mind Explosion** (25%)! 🌀 Boss Phase 2 bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"

                if ac["cid"] == 23 and ac["is_ace2"] and not c.get("cirno_freeze_used"):
                    if random.random() < 0.40:
                        c["cirno_freeze_used"] = True
                        boss_freeze_debuff_turns = 2
                        if not turn_image:
                            turn_image = EVOL_CONFIG[23]["skill_gif"]
                        cirno_notif = f"❄️ **[Ace 2] [#23] Cirno** ({c['username']}) kích hoạt **Perfect Freeze** (40%)! Đóng băng Boss Phase 2: Trong 2 turn tiếp theo có **45% tỷ lệ không thể đánh trả**!"

                if ac["cid"] == 13 and ac["is_ace2"]:
                    if random.random() < 0.30:
                        card_dmg = int(card_dmg * 3.0)
                        boss_molten_ground_turns = 3
                        if not turn_image:
                            turn_image = EVOL_CONFIG[13]["skill_gif"]
                        utsuho_notif = f"☢️ **[Ace 2] [#13] Utsuho Reiuji** ({c['username']}) bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{card_dmg:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa cho Boss Phase 2 trong 3 turn)!"

                if str(ac["cid"]).lower() == "t1":
                    if ac.get("is_ace2"):
                        _t1 = t1_ace2_attack(c, ac, p2_rounds, p2_max_hp, f"Boss Seiki Phase 2", is_boss=True)
                        if _t1.get("multiplier", 1.0) > 1.0:
                            card_dmg = int(card_dmg * _t1["multiplier"])
                        if _t1["bonus"]:
                            raw_cleave = _t1["bonus"]
                            actual_cleave, p2_true_dmg_accum, cap_cleave_msg = apply_raid_true_damage(raw_cleave, p2_true_dmg_accum, p2_true_cap, "Cleave (Seiki Ace 2)")
                            card_dmg += actual_cleave
                            if cap_cleave_msg:
                                _t1["logs"].append(cap_cleave_msg)
                        if _t1["direct"]:
                            raw_bong = _t1["direct"]
                            actual_bong, p2_true_dmg_accum, cap_bong_msg = apply_raid_true_damage(raw_bong, p2_true_dmg_accum, p2_true_cap, "Bóng Khái Niệm (Seiki Ace 2)")
                            p2_hp = max(0, p2_hp - actual_bong)
                            c["total_dmg"] += actual_bong
                            if cap_bong_msg:
                                _t1["logs"].append(cap_bong_msg)
                        if _t1.get("invul"):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p2_rounds
                            c["seiki_invul_turn"] = p2_rounds
                        if _t1["disable"]:
                            boss_skill_erased, erase_msg = apply_bong_khai_niem_boss("seiki", 2, boss_skill_erased)
                            _t1["logs"].append(erase_msg)
                        if _t1["heal"]:
                            ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + _t1["heal"])
                        if _t1["gif"] and not turn_image:
                            turn_image = _t1["gif"]
                        t1_notif = (t1_notif + "\n" if t1_notif else "") + "\n".join(_t1["logs"])
                    elif c.get("seiki_used_turn") != p2_rounds:
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

                if str(ac["cid"]).lower() == "t2":
                    heal_mahoraga = int(ac["max_hp"] * 0.05)
                    ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_mahoraga)
                    c["mahoraga_adapt_turns"] = c.get("mahoraga_adapt_turns", 0) + 1
                    adapt_pct = min(0.90, c["mahoraga_adapt_turns"] * 0.05)
                    if random.random() < 0.30:
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image:
                            turn_image = T2_THOAI_MA_GIF
                        t2_notif_str = (
                            f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt** "
                            f"(Hồi +{heal_mahoraga:,} HP, Kháng ST {int(adapt_pct*100)}%) & vung **Thoái Ma Kiếm** (30%)! "
                            f"Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"
                        )
                    else:
                        if not turn_image:
                            turn_image = T2_PASSIVE_GIF
                        t2_notif_str = (
                            f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt**! "
                            f"Hồi phục **+{heal_mahoraga:,} HP** ({ac['current_hp']:,}/{ac['max_hp']:,} HP) và tăng kháng sát thương lên **{int(adapt_pct*100)}%**!"
                        )
                    t2_notif = (t2_notif + "\n" if t2_notif else "") + t2_notif_str

                if str(ac["cid"]).lower() == "t3":
                    t3_st = c.setdefault("t3_state", {})
                    _t3 = t3_combat_turn(t3_st, ac, p2_rounds, p2_max_hp, f"Boss {p2_cfg['name']}", is_ace2=ac.get("is_ace2"))
                    card_dmg = int(card_dmg * _t3["multiplier"])
                    if _t3["bonus_hp_dmg"] > 0:
                        actual_hp_dmg, p2_true_dmg_accum, cap_hp_msg = apply_raid_true_damage(_t3["bonus_hp_dmg"], p2_true_dmg_accum, p2_true_cap, "Dark Chain (Kizuna)")
                        card_dmg += actual_hp_dmg
                        if cap_hp_msg:
                            _t3["logs"].append(cap_hp_msg)
                    if _t3["gif"] and not turn_image:
                        turn_image = _t3["gif"]
                    t3_notif_str = "\n".join(_t3["logs"])
                    t3_notif = (t3_notif + "\n" if t3_notif else "") + t3_notif_str

                if str(ac["cid"]).lower() == "t4":
                    t4_st = c.setdefault("t4_state", {})
                    _t4 = t4_combat_turn(t4_st, ac, f"Boss {p2_cfg['name']}", heal_mult=1.0, enemy_fate_loop_turns=c.get("p2_fate_turns", 0))
                    card_dmg = int(card_dmg * _t4["multiplier"])
                    if _t4["save_loop_invul"]:
                        c["seiki_invul_turn"] = p2_rounds
                    if _t4["fate_loop_triggered"]:
                        c["p2_fate_turns"] = 2
                        boss_skill_erased = "nuclear_spell"
                    if _t4["ice_spear_triggered"] and random.random() < 0.40:
                        boss_stunned = True
                    if _t4["gif"] and not turn_image:
                        turn_image = _t4["gif"]
                    if _t4["logs"]:
                        t3_notif = (t3_notif + "\n" if t3_notif else "") + "\n".join([f"({c['username']}) {l}" for l in _t4["logs"]])

                round_player_dmg += card_dmg
                c["total_dmg"] += card_dmg

            p2_hp = max(0, p2_hp - round_player_dmg)

            boss_action_log = ""
            if p2_hp <= 0:
                boss_action_log = "💥 **Seiki Dị Hình Phase 2 đã bị thanh tẩy hoàn toàn! Dị tà ma thuật tiêu tan!**"
            elif boss_stunned:
                boss_action_log = "❄️ Boss Phase 2 bị đóng băng thời gian, bất lực không thể ra đòn!"
            else:
                if (boss_skill_erased != "nuclear_spell") and random.random() < 0.15:
                    turn_image = p2_cfg["skills"]["nuclear_spell"]["gif"]
                    boss_action_log = (
                        f"☢️ **[KỸ NĂNG] Seiki Dị Hình Phase 2** kích hoạt **Nuclear Spell Card (15%)**! "
                        f"Oanh tạc hạt nhân gây **10,000 DMG** lên **TẤT CẢ {len(frontline_cards)} lá bài** đang ở tiền tuyến!"
                    )
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p2_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p2_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(10000 * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n🛡️ **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= 10000
                else:
                    num_front = len(frontline_cards)
                    dmg_per_card = max(100, p2_power // num_front)
                    boss_action_log = (
                        f"⚔️ Boss Phase 2 đánh thường tổng **{p2_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!\n"
                        f"🪓 **[Nội Tại - Cleave (100%)]** Mọi đòn đánh kèm thêm **20% Máu Tối Đa** sát thương chuẩn của từng mục tiêu!"
                    )
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        cleave_bonus = int(ac["max_hp"] * 0.20)
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True
                                invul = True
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p2_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True
                            c["seiki_used_turn"] = p2_rounds
                            invul = True
                            turn_image = T1_SEAL_GIF
                            title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                            pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                            boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                        if not invul:
                            raw_cleave_dmg = dmg_per_card + cleave_bonus
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                actual_dmg = int(raw_cleave_dmg * (1.0 - adapt_pct))
                                ac["current_hp"] -= actual_dmg
                                boss_action_log += f"\n• 💢 **{ac['name']}** ({c['username']}) nhận **{raw_cleave_dmg:,} DMG** nhưng Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!"
                            else:
                                ac["current_hp"] -= raw_cleave_dmg
                                boss_action_log += f"\n• 💢 **{ac['name']}** ({c['username']}) nhận **{dmg_per_card:,} + {cleave_bonus:,} (Cleave) = {raw_cleave_dmg:,} DMG**!"
                    if not turn_image:
                        turn_image = p2_cfg["skills"]["cleave"]["gif"]

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
                title=f"☢️ HIỆP {p2_rounds} - SEIKI DỊ HÌNH PHASE 2: THỨC TỈNH",
                description=f"❤️ **Máu Boss Phase 2:** `{get_hp_bar(p2_hp, p2_max_hp)}` **{p2_hp:,}/{p2_max_hp:,} HP**",
                color=0x7C3AED
            )
            round_embed.add_field(name="💥 Tiền Tuyến Tấn Công:", value=f"Toàn quân dồn **{round_player_dmg:,} DMG**!", inline=False)
            if sakuya_stun_notif:
                round_embed.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
            if marisa_spark_notif:
                round_embed.add_field(name="🌟 Master Spark Oanh Tạc:", value=marisa_spark_notif, inline=False)
            if remilia_notif:
                round_embed.add_field(name="🩸 Thương Đỏ Gungnir:", value=remilia_notif, inline=False)
            if reisen_notif:
                round_embed.add_field(name="🔴 Red Eye Mind Explosion:", value=reisen_notif, inline=False)
            if reisen_boss_log:
                round_embed.add_field(name="🌀 Ảo Giác Tâm Trí:", value=reisen_boss_log, inline=False)
            if flandre_notif:
                round_embed.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
            if t1_notif:
                round_embed.add_field(name="🔮 Tuyệt Kỹ [Ace 2] [#t1] Seiki:", value=t1_notif, inline=False)
            if t2_notif:
                round_embed.add_field(name="🔱 Thần Tướng [Nhóm T] [#t2] Mahoraga:", value=t2_notif, inline=False)
            if t3_notif:
                round_embed.add_field(name="🩸 Hoàng Đế [Nhóm T] [#t3] Kizuna:", value=t3_notif, inline=False)
            round_embed.add_field(name="👹 Boss Phase 2 Ra Đòn:", value=boss_action_log, inline=False)
            if push_logs:
                round_embed.add_field(name="🔄 Thay Đổi Tiền Tuyến:", value="\n".join(push_logs), inline=False)
            round_embed.add_field(name="🛡️ Tình Trạng Tiền Tuyến Hiện Tại:", value="\n".join(round_card_status), inline=False)

            if turn_image:
                round_embed.set_image(url=turn_image)
            else:
                round_embed.set_thumbnail(url=p2_cfg["image"])

            all_raid_turns.append({
                "round": p2_rounds,
                "phase": 2,
                "title": f"Seiki Phase 2 - Hiệp {p2_rounds}: Thức Tỉnh",
                "short_label": f"S-P2 - Hiệp {p2_rounds}",
                "short_desc": f"Boss Phase 2 còn {p2_hp:,} HP",
                "desc": f"☢️ **Seiki Dị Hình - Phase 2 Thức Tỉnh**\n❤️ Máu Boss: `{get_hp_bar(p2_hp, p2_max_hp)}` **{p2_hp:,}/{p2_max_hp:,} HP**",
                "color": 0x7C3AED,
                "image": turn_image,
                "fields": [
                    ("💥 Tiền Tuyến Tấn Công:", f"Toàn quân dồn **{round_player_dmg:,} DMG**!", False),
                    *([("❄️ Kỹ Năng Đột Biến:", sakuya_stun_notif, False)] if sakuya_stun_notif else []),
                    *([("🌟 Master Spark:", marisa_spark_notif, False)] if marisa_spark_notif else []),
                    *([("🩸 Thương Đỏ Gungnir:", remilia_notif, False)] if remilia_notif else []),
                    *([("🔴 Red Eye Mind Explosion:", reisen_notif, False)] if reisen_notif else []),
                    *([("🌀 Ảo Giác Tâm Trí:", reisen_boss_log, False)] if reisen_boss_log else []),
                    *([("🦇 Ripples of 495 Years:", flandre_notif, False)] if flandre_notif else []),
                    *([("🔮 Tuyệt Kỹ [Ace 2] [#t1] Seiki:", t1_notif, False)] if t1_notif else []),
                    *([("🔱 Thần Tướng [Nhóm T] [#t2] Mahoraga:", t2_notif, False)] if t2_notif else []),
                *([("🩸 Hoàng Đế [Nhóm T] [#t3] Kizuna:", t3_notif, False)] if t3_notif else []),
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
            await asyncio.sleep(3.0)

        p2_defeated = (p2_hp <= 0)
        total_raid_dmg = sum(c["total_dmg"] for c in combatants)

        p2_rewards_data = {}
        if p2_defeated:
            for uid in participants:
                p = get_player(uid)
                old_lvl = p["level"]
                roll = random.random()
                if roll < 0.10:
                    t_val = 30.0
                    d_str = "👑 **+30 Vé** (10%)"
                elif roll < 0.50:
                    t_val = 20.0
                    d_str = "🔥 **+20 Vé** (40%)"
                else:
                    t_val = 10.0
                    d_str = "💎 **+10 Vé** (50%)"

                items_won = [d_str]
                if random.random() < 0.05:
                    p_shards = p.setdefault("shards", {})
                    p_shards["seiki"] = p_shards.get("seiki", 0) + 1
                    cur_shards = p_shards["seiki"]
                    shard_notice = f"🔮 **+1 Mảnh Seiki** (5% Siêu Hiếm! Kho: {cur_shards}/10)"
                    if cur_shards >= 10:
                        shard_notice += " ✨ *(Đã đủ 10 mảnh! Dùng `/t translate`)*"
                    items_won.append(shard_notice)

                # 2.5% rơi Quạt Giấy ở Seiki Phase 2
                if random.random() < 0.025:
                    p_items = p.setdefault("items", {})
                    p_items["quat_giay"] = p_items.get("quat_giay", 0) + 1
                    items_won.append(f"🪭 **+1 Quạt Giấy** (2.5% Rơi từ Seiki Phase 2! Kho: {p_items['quat_giay']} cái)")

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
            title="🌟 KẾT QUẢ ĐẠI CHIẾN: SEIKI DỊ HÌNH (FULL 2 PHASES)!",
            description=(
                "🌸 **Reimu thở phào nhẹ nhõm:** *\"Đó không phải cha ta! Dị tà ma thuật đã tan biến, ngài ấy đã được thanh tẩy hoàn toàn! Cảm ơn mọi người nhiều lắm!\"*\n\n"
                f"**Phase 1:** 🎉 Hạ gục sau **{p1_rounds} hiệp**\n"
                f"**Phase 2:** {'🎉 TOÀN THẮNG HUY HOÀNG (Boss 0 HP)' if p2_defeated else f'❌ THẤT THỦ (Boss còn {p2_hp:,}/{p2_max_hp:,} HP)'} sau **{p2_rounds} hiệp**\n"
                f"💥 **Tổng Sát Thương Cả 2 Phase:** **{total_raid_dmg:,} DMG**\n"
                f"⏳ **Hồi chiêu Boss tiếp theo:** **15 phút**"
            ),
            color=0x10B981 if p2_defeated else 0xF59E0B
        )
        final_embed.set_thumbnail(url=p2_cfg["image"] if p2_defeated else boss_cfg["image"])
        p1_summary = [f"🎁 **{r['username']}**: +{r['total_pulls']:.0f} Vé Pull ({r['items'][0]}) + 100 XP" + (f"\n   └ {r['items'][1]}" if len(r['items']) > 1 else "") for r in p1_rewards_data.values()]
        final_embed.add_field(name="📦 Phần Thưởng Phase 1 (10% 10 vé, 40% 5 vé, 50% 3 vé, 2.5% Mảnh Seiki):", value="\n".join(p1_summary), inline=False)

        if p2_defeated:
            p2_summary = []
            for r in p2_rewards_data.values():
                lvl_up = f" 🌟 **LÊN CẤP {r['new_level']}!**" if r['new_level'] > r['old_level'] else ""
                shard_line = f"\n   └ {r['items'][1]}" if len(r['items']) > 1 else ""
                p2_summary.append(f"🏆 **{r['username']}**: Nhận **+{r['total_pulls']:.0f} Vé Pull** ({r['items'][0]}) + 150 XP!{lvl_up}{shard_line}\n   └ *Tổng vé hiện có: {r['total_tickets']:.2f} vé*")
            final_embed.add_field(name="💎 Phần Thưởng Siêu Cấp Phase 2 (10% 30 vé, 40% 20 vé, 50% 10 vé, 5% Mảnh Seiki, 2,5% Quạt giấy):", value="\n".join(p2_summary), inline=False)
        else:
            final_embed.add_field(name="⚠️ Kết Quả Phase 2:", value=f"Boss Phase 2 còn {p2_hp:,} HP! Toàn bộ quà Phase 1 vẫn được bảo lưu trọn vẹn.", inline=False)

        await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))
        return

    # ========================================================================
    # PHASE 2: REIMU DỊ HÌNH - THỨC TỈNH (50K HP / 10K DMG)
    # ========================================================================
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
        c["reisen_used"] = False
        c["cirno_freeze_used"] = False
        c["seiki_seal_used"] = False
        c["seiki_spark_used"] = False
        c["seiki_heal_used"] = False
        c["seiki_used_turn"] = -1
        c["seal_used"] = False
        c["bong_used"] = False
        c["med_used"] = False
        for card in c["team_cards"]:
            card["current_hp"] = card["max_hp"]

    p2_max_hp = BOSS_PHASE2_CONFIG["hp"]
    p2_hp = p2_max_hp
    p2_power = BOSS_PHASE2_CONFIG["power"]
    p2_rounds = 0
    p2_battle_history = []
    boss_mind_turns = 0
    boss_freeze_debuff_turns = 0
    boss_molten_ground_turns = 0
    boss_skill_erased = None

    p2_true_cap = int(p2_max_hp * 0.50)
    p2_true_dmg_accum = 0

    while p2_hp > 0 and p2_rounds < max_rounds:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants:
            break

        p2_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        reisen_boss_log = None
        if boss_mind_turns > 0:
            boss_mind_turns -= 1
            if random.random() < 0.20:
                _mind_dmg = p2_power
                p2_hp = max(0, p2_hp - _mind_dmg)
                reisen_boss_log = f"🌀 **[Red Eye Mind Explosion]** Boss mất kiểm soát tâm trí và **tự gây {_mind_dmg:,} DMG** lên bản thân! (Còn {boss_mind_turns} lượt ảo giác)"

        if boss_molten_ground_turns > 0:
            boss_molten_ground_turns -= 1
            raw_burn = int(p2_max_hp * 0.02)
            actual_burn, p2_true_dmg_accum, cap_burn_msg = apply_raid_true_damage(raw_burn, p2_true_dmg_accum, p2_true_cap, "Bỏng Mặt Đất (Utsuho)")
            if actual_burn > 0:
                p2_hp = max(0, p2_hp - actual_burn)
                boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham hạt nhân thiêu đốt Boss Phase 2 gây **{actual_burn:,} DMG** (2% Máu Tối Đa)! (Còn {boss_molten_ground_turns} lượt)"
            else:
                boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Mặt đất vẫn sôi trào nhưng sát thương chuẩn đã bị triệt tiêu (0 DMG)! (Còn {boss_molten_ground_turns} lượt)"
            if cap_burn_msg:
                boss_molten_log += f"\n{cap_burn_msg}"

        boss_stunned = False
        sakuya_stun_notif = None
        marisa_spark_notif = None
        flandre_notif = None
        remilia_notif = None
        reisen_notif = None
        cirno_notif = None
        utsuho_notif = None
        boss_molten_log = None
        cirno_freeze_log = None
        t1_notif = None
        t2_notif = None
        t3_notif = None
        turn_image = None

        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 18 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.40:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#18] Sakuya Izayoi** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss Phase 2 bị **STUN**!"
                    break

        if boss_freeze_debuff_turns > 0 and not boss_stunned:
            boss_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                boss_stunned = True
                cirno_freeze_log = f"❄️ **[Perfect Freeze]** Boss Phase 2 bị đóng băng cứng đờ (45%), không thể hành động trong hiệp này! (Còn {boss_freeze_debuff_turns} lượt duy trì)"

        round_player_dmg = 0
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            card_dmg = ac["power"]
            if ac["cid"] == 19 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = EVOL_CONFIG[19]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#19] Marisa Kirisame** ({c['username']}) bộc phá **Master Spark** (30%)! Đòn đánh ma thuật ×2.0 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"
# Kỹ năng Yukari Ace 2:
            if ac["cid"] == 4 and ac.get("is_ace2"):
                if not c.get("yukari_station_used") and random.random() < 0.30:
                    c["yukari_station_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image:
                        turn_image = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/7e/69/snvix5aVyjKgjesAJV.gif"
                    yukari_notif = f"🌌 **[Ace 2] [#04] Yukari** ({c['username']}) tung **Trip To The Old Station** (30%)! Sát thương ×2.0 giáng **{card_dmg:,} DMG**!"
                elif not c.get("yukari_lastword_used") and random.random() < 0.25:
                    c["yukari_lastword_used"] = True
                    card_dmg = int(card_dmg * 2.5)
                    boss_stunned = True
                    if not turn_image:
                        turn_image = "https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/03/4b/epgnCZ5A8KOdm.gif"
                    yukari_notif = f"👁️ **[Ace 2] [#04] Yukari** ({c['username']}) kích hoạt **⸮⸮⸮ : Last Word !** (25%)! Bộc phá ×2.5 gây **{card_dmg:,} DMG** và **STUN đối thủ**!"

            if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                if random.random() < 0.25:
                    c["flandre_used"] = True
                    raw_rip = int(p2_hp * 0.30)
                    actual_rip, p2_true_dmg_accum, cap_rip_msg = apply_raid_true_damage(raw_rip, p2_true_dmg_accum, p2_true_cap, "Ripples of 495 Years (Flandre)")
                    p2_hp = max(0, p2_hp - actual_rip)
                    c["total_dmg"] += actual_rip
                    if not turn_image:
                        turn_image = EVOL_CONFIG[9]["skill_gif"]
                    if actual_rip > 0:
                        flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** (25%)! Gây **{actual_rip:,} DMG** sát thương chuẩn lên Boss Phase 2!"
                    else:
                        flandre_notif = f"🦇 **[Ace 2] [#09] Flandre Scarlet** ({c['username']}) kích hoạt **Ripples of 495 Years** nhưng sát thương chuẩn đã chạm trần (0 DMG)!"
                    if cap_rip_msg:
                        flandre_notif += f"\n{cap_rip_msg}"

            if ac["cid"] == 12 and ac["is_ace2"]:
                raw_gungnir = int(p2_max_hp * 0.03)
                actual_gungnir, p2_true_dmg_accum, cap_gungnir_msg = apply_raid_true_damage(raw_gungnir, p2_true_dmg_accum, p2_true_cap, "Thương Đỏ Gungnir (Remilia)")
                card_dmg += actual_gungnir
                if not turn_image:
                    turn_image = EVOL_CONFIG[12]["skill_gif"]
                if actual_gungnir > 0:
                    remilia_notif = f"🩸 **[Ace 2] [#12] Remilia Scarlet** ({c['username']}) - **Thương Đỏ Gungnir** (Thụ động): Gây thêm **{actual_gungnir:,} DMG** (3% Máu tối đa Boss Phase 2)!"
                else:
                    remilia_notif = f"🩸 **[Ace 2] [#12] Remilia Scarlet** ({c['username']}) - **Thương Đỏ Gungnir**: Sát thương chuẩn đã chạm trần (0 DMG)!"
                if cap_gungnir_msg:
                    remilia_notif += f"\n{cap_gungnir_msg}"

            if ac["cid"] == 21 and ac["is_ace2"] and not c.get("reisen_used"):
                if random.random() < 0.25:
                    c["reisen_used"] = True
                    boss_mind_turns = 4
                    if not turn_image:
                        turn_image = EVOL_CONFIG[21]["skill_gif"]
                    reisen_notif = f"🔴 **[Ace 2] [#21] Reisen Udongein Inaba** ({c['username']}) kích hoạt **Red Eye Mind Explosion** (25%)! 🌀 Boss Phase 2 bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"

            if ac["cid"] == 23 and ac["is_ace2"] and not c.get("cirno_freeze_used"):
                if random.random() < 0.40:
                    c["cirno_freeze_used"] = True
                    boss_freeze_debuff_turns = 2
                    if not turn_image:
                        turn_image = EVOL_CONFIG[23]["skill_gif"]
                    cirno_notif = f"❄️ **[Ace 2] [#23] Cirno** ({c['username']}) kích hoạt **Perfect Freeze** (40%)! Đóng băng Boss Phase 2: Trong 2 turn tiếp theo có **45% tỷ lệ không thể đánh trả**!"

            if ac["cid"] == 13 and ac["is_ace2"]:
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 3.0)
                    boss_molten_ground_turns = 3
                    if not turn_image:
                        turn_image = EVOL_CONFIG[13]["skill_gif"]
                    utsuho_notif = f"☢️ **[Ace 2] [#13] Utsuho Reiuji** ({c['username']}) bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{card_dmg:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa cho Boss Phase 2 trong 3 turn)!"

            if str(ac["cid"]).lower() == "t1":
                if ac.get("is_ace2"):
                    _t1 = t1_ace2_attack(c, ac, p2_rounds, p2_max_hp, f"Boss Reimu Phase 2", is_boss=True)
                    if _t1.get("multiplier", 1.0) > 1.0:
                        card_dmg = int(card_dmg * _t1["multiplier"])
                    if _t1["bonus"]:
                        raw_cleave = _t1["bonus"]
                        actual_cleave, p2_true_dmg_accum, cap_cleave_msg = apply_raid_true_damage(raw_cleave, p2_true_dmg_accum, p2_true_cap, "Cleave (Seiki Ace 2)")
                        card_dmg += actual_cleave
                        if cap_cleave_msg:
                            _t1["logs"].append(cap_cleave_msg)
                    if _t1["direct"]:
                        raw_bong = _t1["direct"]
                        actual_bong, p2_true_dmg_accum, cap_bong_msg = apply_raid_true_damage(raw_bong, p2_true_dmg_accum, p2_true_cap, "Bóng Khái Niệm (Seiki Ace 2)")
                        p2_hp = max(0, p2_hp - actual_bong)
                        c["total_dmg"] += actual_bong
                        if cap_bong_msg:
                            _t1["logs"].append(cap_bong_msg)
                    if _t1.get("invul"):
                        c["seiki_seal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        c["seiki_invul_turn"] = p2_rounds
                    if _t1["disable"]:
                        boss_skill_erased, erase_msg = apply_bong_khai_niem_boss("reimu", 2, boss_skill_erased)
                        _t1["logs"].append(erase_msg)
                    if _t1["heal"]:
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + _t1["heal"])
                    if _t1["gif"] and not turn_image:
                        turn_image = _t1["gif"]
                    t1_notif = (t1_notif + "\n" if t1_notif else "") + "\n".join(_t1["logs"])
                elif c.get("seiki_used_turn") != p2_rounds:
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

            if str(ac["cid"]).lower() == "t2":
                heal_mahoraga = int(ac["max_hp"] * 0.05)
                ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_mahoraga)
                c["mahoraga_adapt_turns"] = c.get("mahoraga_adapt_turns", 0) + 1
                adapt_pct = min(0.90, c["mahoraga_adapt_turns"] * 0.05)
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 1.5)
                    if not turn_image:
                        turn_image = T2_THOAI_MA_GIF
                    t2_notif_str = (
                        f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt** "
                        f"(Hồi +{heal_mahoraga:,} HP, Kháng ST {int(adapt_pct*100)}%) & vung **Thoái Ma Kiếm** (30%)! "
                        f"Sát thương ×1.5 giáng **{card_dmg:,} DMG** lên Boss Phase 2!"
                    )
                else:
                    if not turn_image:
                        turn_image = T2_PASSIVE_GIF
                    t2_notif_str = (
                        f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt**! "
                        f"Hồi phục **+{heal_mahoraga:,} HP** ({ac['current_hp']:,}/{ac['max_hp']:,} HP) và tăng kháng sát thương lên **{int(adapt_pct*100)}%**!"
                    )
                t2_notif = (t2_notif + "\n" if t2_notif else "") + t2_notif_str
            if str(ac["cid"]).lower() == "t3":
                t3_st = c.setdefault("t3_state", {})
                _t3 = t3_combat_turn(t3_st, ac, p2_rounds, p2_max_hp, f"Boss {BOSS_PHASE2_CONFIG['name']}", is_ace2=ac.get("is_ace2"))
                card_dmg = int(card_dmg * _t3["multiplier"])
                if _t3["bonus_hp_dmg"] > 0:
                    actual_hp_dmg, p2_true_dmg_accum, cap_hp_msg = apply_raid_true_damage(_t3["bonus_hp_dmg"], p2_true_dmg_accum, p2_true_cap, "Dark Chain (Kizuna)")
                    card_dmg += actual_hp_dmg
                    if cap_hp_msg:
                        _t3["logs"].append(cap_hp_msg)
                if _t3["gif"] and not turn_image:
                    turn_image = _t3["gif"]
                t3_notif_str = "\n".join(_t3["logs"])
                t3_notif = (t3_notif + "\n" if t3_notif else "") + t3_notif_str

            if str(ac["cid"]).lower() == "t4":
                t4_st = c.setdefault("t4_state", {})
                _t4 = t4_combat_turn(t4_st, ac, f"Boss {BOSS_PHASE2_CONFIG['name']}", heal_mult=1.0, enemy_fate_loop_turns=c.get("p2_fate_turns", 0))
                card_dmg = int(card_dmg * _t4["multiplier"])
                if _t4["save_loop_invul"]:
                    c["seiki_invul_turn"] = p2_rounds
                if _t4["fate_loop_triggered"]:
                    c["p2_fate_turns"] = 2
                    boss_skill_erased = "di_hinh_bua_chu"
                if _t4["ice_spear_triggered"] and random.random() < 0.40:
                    boss_stunned = True
                if _t4["gif"] and not turn_image:
                    turn_image = _t4["gif"]
                if _t4["logs"]:
                    t3_notif = (t3_notif + "\n" if t3_notif else "") + "\n".join([f"({c['username']}) {l}" for l in _t4["logs"]])

            round_player_dmg += card_dmg
            c["total_dmg"] += card_dmg

        p2_hp = max(0, p2_hp - round_player_dmg)

        boss_action_log = ""
        if p2_hp <= 0:
            boss_action_log = "⚡ **Reimu Dị Hình Phase 2 đã bị tiêu diệt hoàn toàn!**"
        elif boss_stunned:
            boss_action_log = "❄️ Boss Phase 2 bị đóng băng thời gian, không thể phát động đòn đánh!"
        else:
            if (boss_skill_erased != "di_hinh_bua_chu") and random.random() < 0.20:
                turn_image = BOSS_SKILL_CONFIG["gif"]
                boss_action_log = "👹 **[NỘI TẠI BOSS] Reimu Dị Hình** phát động **Dị Hình Bùa Chú** (20%)! Oanh tạc **5,000 DMG** diện rộng!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True
                            invul = True
                            if not turn_image or turn_image == BOSS_SKILL_CONFIG["gif"]:
                                turn_image = EVOL_CONFIG[15]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p2_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                        c["seiki_seal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        invul = True
                        turn_image = T1_SEAL_GIF
                        title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                        pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                        boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                    if not invul:
                        ac["current_hp"] -= 5000
            else:
                num_front = len(frontline_cards)
                dmg_per_card = max(100, p2_power // num_front)
                boss_action_log = f"⚔️ Boss Phase 2 đánh thường tổng **{p2_power:,} DMG**, chia đều **{dmg_per_card:,} DMG** lên mỗi lá bài tiền tuyến ({num_front} lá)!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True
                            invul = True
                            turn_image = EVOL_CONFIG[15]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and c.get("seiki_used_turn") != p2_rounds and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                        c["seiki_seal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        invul = True
                        turn_image = T1_SEAL_GIF
                        title_t1 = "[Ace 2] [#t1] Seiki" if ac.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                        pct_t1 = "50%" if ac.get("is_ace2") else "40%"
                        boss_action_log += f"\n🛡️ **{title_t1}** ({c['username']}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
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
        if remilia_notif:
            round_embed.add_field(name="🩸 Thương Đỏ Gungnir:", value=remilia_notif, inline=False)
        if reisen_notif:
            round_embed.add_field(name="🔴 Red Eye Mind Explosion:", value=reisen_notif, inline=False)
        if reisen_boss_log:
            round_embed.add_field(name="🌀 Ảo Giác Tâm Trí:", value=reisen_boss_log, inline=False)
        if flandre_notif:
            round_embed.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
        if t1_notif:
            round_embed.add_field(name="🔮 Tuyệt Kỹ [Ace 2] [#t1] Seiki:", value=t1_notif, inline=False)
        if t2_notif:
            round_embed.add_field(name="🔱 Thần Tướng [Nhóm T] [#t2] Mahoraga:", value=t2_notif, inline=False)
        if t3_notif:
            round_embed.add_field(name="🩸 Hoàng Đế [Nhóm T] [#t3] Kizuna:", value=t3_notif, inline=False)
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
                *([("🩸 Thương Đỏ Gungnir:", remilia_notif, False)] if remilia_notif else []),
                *([("🔴 Red Eye Mind Explosion:", reisen_notif, False)] if reisen_notif else []),
                *([("🌀 Ảo Giác Tâm Trí:", reisen_boss_log, False)] if reisen_boss_log else []),
                *([("🦇 Ripples of 495 Years:", flandre_notif, False)] if flandre_notif else []),
                *([("🔮 Tuyệt Kỹ [Ace 2] [#t1] Seiki:", t1_notif, False)] if t1_notif else []),
                *([("🔱 Thần Tướng [Nhóm T] [#t2] Mahoraga:", t2_notif, False)] if t2_notif else []),
                *([("🩸 Hoàng Đế [Nhóm T] [#t3] Kizuna:", t3_notif, False)] if t3_notif else []),
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
        await asyncio.sleep(3.0)

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
            if random.random() < 0.025:
                p_shards = p.setdefault("shards", {})
                p_shards["seiki"] = p_shards.get("seiki", 0) + 1
                cur_shards = p_shards["seiki"]
                shard_notice = f"🔮 **+1 Mảnh Seiki** (2.5% Siêu Hiếm! Kho: {cur_shards}/10)"
                if cur_shards >= 10:
                    shard_notice += " ✨ *(Đã đủ 10 mảnh! Dùng `/t translate`)*"
                items_won.append(shard_notice)
# 1.0% rơi Quạt Giấy ở Reimu Phase 2:
            if random.random() < 0.01:
                p_items = p.setdefault("items", {})
                p_items["quat_giay"] = p_items.get("quat_giay", 0) + 1
                items_won.append(f"🪭 **+1 Quạt Giấy** (1% Cực Hiếm rơi từ Reimu Phase 2! Kho: {p_items['quat_giay']} cái)")
                
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
        final_embed.add_field(name="💎 Phần Thưởng Siêu Cấp Phase 2 (10% 20 vé, 40% 10 vé, 50% 5 vé, 2.5% Mảnh Seiki, 1% Quạt Giấy 🪭):", value="\n".join(p2_summary), inline=False)
    else:
        final_embed.add_field(name="⚠️ Kết Quả Phase 2:", value=f"Boss Phase 2 còn {p2_hp:,} HP! Toàn bộ quà Phase 1 vẫn được bảo lưu trọn vẹn.", inline=False)

    await channel.send(embed=final_embed, view=OpenDetailsView(all_raid_turns))
# ==============================================================================
# 7. SỰ KIỆN BOT ON_READY & ON_MESSAGE
# ==============================================================================

# ==============================================================================
# 6B. CHIẾN ĐẤU EVENT BOSS KIZUNA (PHASE 1 & PHASE 2 WONDER GUARD)
# ==============================================================================

# ==============================================================================
# HỆ THỐNG PHÒNG CHỜ (LOBBY 2 PHÚT) & LIVE COMBAT CHO EVENT BOSS KIZUNA
# ==============================================================================
active_event_raid = None

class EventRaidJoinView(discord.ui.View):
    def __init__(self, raid_data):
        super().__init__(timeout=None)
        self.raid_data = raid_data

    @discord.ui.button(label="⚔️ Tham Gia Diệt Huyết Ma Đế (Miễn Phí)", style=discord.ButtonStyle.danger, emoji="🩸")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.raid_data.get("started") or self.raid_data.get("closed"):
            await interaction.response.send_message("Trận chiến đã bắt đầu hoặc thời gian chuẩn bị đã kết thúc!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in self.raid_data["participants"]:
            await interaction.response.send_message("Bạn đã có tên trong danh sách xuất trận rồi!", ephemeral=True)
            return

        if len(self.raid_data["participants"]) >= 6:
            await interaction.response.send_message("Đội hình đã đủ 6 dũng giả!", ephemeral=True)
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
                if cid not in current_team: current_team.append(cid)
                if len(current_team) >= 3: break
            player["team"] = current_team
            save_player(player)

        self.raid_data["participants"].append(user_id)
        self.raid_data["names"].append(interaction.user.display_name)
        count = len(self.raid_data["participants"])

        await interaction.response.send_message(f"🔥 {interaction.user.mention} đã tham chiến diệt Event Boss Kizuna! ({count}/6 dũng giả)", ephemeral=False)

        try:
            embed = interaction.message.embeds[0]
            embed.set_field_at(
                2,
                name=f"👥 Người Tham Gia ({count}/6):",
                value=", ".join(self.raid_data["names"]),
                inline=False
            )
            await interaction.message.edit(embed=embed, view=self)
        except Exception:
            pass

        if count >= 6:
            self.raid_data["start_event"].set()

async def event_raid_timer_lifecycle(channel, raid_data, view):
    global active_event_raid
    try:
        try:
            await asyncio.wait_for(raid_data["start_event"].wait(), timeout=120.0)
        except asyncio.TimeoutError:
            pass

        for child in view.children:
            child.disabled = True
        if raid_data.get("msg"):
            try: await raid_data["msg"].edit(view=view)
            except Exception: pass

        if raid_data.get("started") or raid_data.get("closed"):
            return

        participants = raid_data.get("participants", [])
        if participants:
            raid_data["started"] = True
            names_str = ", ".join(raid_data.get("names", []))
            await channel.send(
                f"⏰ **HẾT 2 PHÚT CHUẨN BỊ EVENT RAID!**\n"
                f"⚔️ **{len(participants)} Dũng Giả** ({names_str}) đồng loạt tiến vào lâu đài huyết tộc!\n"
                f"🩸 **Kizuna - Huyết Ma Đế** thức tỉnh sát khí ngập trời — **TRẬN CHIẾN BẮT ĐẦU!**"
            )
            try:
                await execute_event_raid(channel, raid_data)
            except Exception as e:
                print(f"Lỗi khi thực thi Event Raid: {e}", flush=True)
                try: await channel.send(f"⚠️ Sự cố kỹ thuật: `{e}`")
                except Exception: pass
            finally:
                active_event_raid = None
        else:
            raid_data["closed"] = True
            active_event_raid = None
            await channel.send("🌌 Huyết Ma Đế Kizuna đã ẩn mình vào bóng tối vì không có ai dám nghênh chiến...")
    except asyncio.CancelledError:
        return
    except Exception as ex:
        print(f"Lỗi trong event_raid_timer_lifecycle: {ex}", flush=True)
        active_event_raid = None

async def spawn_event_boss_raid(channel, author, is_admin=False):
    global active_event_raid
    if active_event_raid is not None:
        if active_event_raid.get("task") and not active_event_raid["task"].done():
            active_event_raid["task"].cancel()
        active_event_raid = None

    start_event = asyncio.Event()
    raid_data = {
        "channel_id": channel.id,
        "boss_config": EVENT_BOSS_CONFIG,
        "participants": [author.id],
        "names": [author.display_name],
        "created_timestamp": time.time(),
        "start_event": start_event,
        "started": False,
        "closed": False,
        "msg": None,
        "view": None,
        "task": None
    }
    active_event_raid = raid_data

    title = "🚨 [ADMIN EVENT] TRIỆU HỒI EVENT BOSS: KIZUNA - HUYẾT MA ĐẾ!" if is_admin else "🚨 CẢNH BÁO EVENT BOSS: KIZUNA - HUYẾT MA ĐẾ GIÁNG LÂM!"
    desc = (
        f"👑 **Khởi xướng bởi:** {author.mention}\n\n"
        "🏰 *Hoàng đế ma cà rồng cổ đại Kizuna đã thức tỉnh tại lâu đài huyết sắc!*\n"
        "Mọi người hãy cùng liên minh tham gia đánh boss để nhận Kẹo Halloween 🍬, Vé Pull 🎟️ và Mảnh Kizuna 🩸!"
    )
    embed = discord.Embed(title=title, description=desc, color=0x991B1B)
    embed.set_image(url=EVENT_BOSS_CONFIG["image"])
    embed.add_field(name="❤️ Máu Boss (HP):", value="• Phase 1: **50,000 HP**\n• Phase 2 Thức Tỉnh: **75,000 HP**", inline=True)
    embed.add_field(name="⚔️ Sức Mạnh:", value="• Phase 1: **3,000 DMG** (chia đều)\n• Phase 2: **7,000 DMG** (chia đều)", inline=True)
    embed.add_field(name=f"👥 Người Tham Gia (1/6):", value=author.display_name, inline=False)
    embed.add_field(
        name="🔮 Kỹ Năng & Nội Tại Huyết Ma Đế:",
        value=(
            "• 🩸 **True vampire (100%):** Mỗi hiệp tự hồi **1,5% HP tối đa**!\n"
            "• 💥 **Blood chain (20%):** Gây **1.5x sát thương chia đều** cho toàn bộ thẻ tiền tuyến!\n"
            "• 🌑 **Dark chain (20%):** 1x sát thương chia đều kèm **15% Máu Tối Đa** của từng lá bài!\n"
            "• 🛡️ **Wonder guard (Phase 2 - 15%):** Miễn thương và **phản 90% sát thương + hiệu ứng** trong 2 lượt!"
        ),
        inline=False
    )
    embed.add_field(
        name="🎁 Phần Thưởng Rơi (Drop):",
        value=(
            "• **Phase 1:** 10% 20 vé, 40% 15 vé, 50% 10 vé | 30% 50 kẹo, 10% 100 kẹo | 2.5% Mảnh Kizuna\n"
            "• **Phase 2:** 10% 20 vé, 40% 15 vé, 50% 10 vé | 50% 120 kẹo, 30% 70 kẹo | 7% Mảnh Kizuna"
        ),
        inline=False
    )
    embed.add_field(
        name="⏱️ Thời Gian Chuẩn Bị (2 Phút):",
        value="Có **2 phút (120 giây)** để bấm nút **\'Tham Gia\'** bên dưới! Đủ 6 người hoặc hết giờ sẽ tự động khai màn trận chiến!",
        inline=False
    )
    embed.set_footer(text="Phòng chờ Event Raid • Tối đa 6 dũng giả tham chiến")

    view = EventRaidJoinView(raid_data)
    raid_data["view"] = view
    msg = await channel.send(embed=embed, view=view)
    raid_data["msg"] = msg
    task = asyncio.create_task(event_raid_timer_lifecycle(channel, raid_data, view))
    raid_data["task"] = task

# ==============================================================================
# HÀM CHIẾN ĐẤU EVENT BOSS KIZUNA (ĐẦY ĐỦ KỸ NĂNG & GIF THẺ T VÀ THẺ ACE 2)
# ==============================================================================
# ==============================================================================
# HÀM CHIẾN ĐẤU EVENT BOSS KIZUNA (CHUẨN 100% INDENT - ĐẦY ĐỦ SKILL THẺ T & ACE 2)
# ==============================================================================
async def execute_event_raid(channel, raid_data):
    global active_event_raid
    active_event_raid = None
    participants = raid_data["participants"]
    if not participants:
        await channel.send("⛩️ Kizuna - Huyết Ma Đế đã rời đi vì không có dũng giả nào nghênh chiến...")
        return

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
                if cid not in team_cids: team_cids.append(cid)
                if len(team_cids) >= 3: break
            p["team"] = team_cids
            save_player(p)

        team_cards = []
        for cid in team_cids[:3]:
            card = CARDS_DATA.get(cid)
            if card:
                is_ace2 = is_card_ace2(p, cid)
                ace_pwr = ACE_POWER_BUFF if is_ace2 else 0
                ace_hp = ACE_HP_BUFF if is_ace2 else 0
                team_cards.append({
                    "cid": cid,
                    "name": f"[Ace 2 ⭐⭐] #{card['id']} {card['name']}" if is_ace2 else f"{format_card_id(card['id'])} {card['name']}",
                    "power": card["power"] + lvl_buff_pwr + ace_pwr,
                    "max_hp": card["hp"] + lvl_buff_hp + ace_hp,
                    "current_hp": card["hp"] + lvl_buff_hp + ace_hp,
                    "is_ace2": is_ace2
                })

        combatants.append({
            "uid": uid,
            "username": p["username"],
            "team_cards": team_cards,
            "current_card_index": 0,
            "is_alive": len(team_cards) > 0,
            "total_dmg": 0,
            "yukari_station_used": False,  
            "yukari_lastword_used": False,
            "sakuya_stun_used": False,
            "reimu_invul_used": False,
            "marisa_spark_used": False,
            "flandre_used": False,
            "reisen_used": False,
            "cirno_freeze_used": False,
            "seiki_seal_used": False,
            "seiki_spark_used": False,
            "seiki_heal_used": False,
            "seiki_used_turn": -1,
            "seal_used": False,
            "bong_used": False,
            "med_used": False,
            "mahoraga_adapt_turns": 0,
            "t3_state": {}
        })

    all_event_raid_turns = []

    # ========================================================================
    # PHASE 1: KIZUNA - HUYẾT MA ĐẾ (50,000 HP / 3,000 DMG)
    # ========================================================================
    p1_cfg = EVENT_BOSS_CONFIG
    p1_max_hp = p1_cfg["hp"]
    p1_hp = p1_max_hp
    p1_power = p1_cfg["power"]
    p1_rounds = 0
    boss_mind_turns = 0
    boss_freeze_debuff_turns = 0
    boss_molten_ground_turns = 0
    boss_skill_erased = None

    p1_true_cap = int(p1_max_hp * 0.50)
    p1_true_dmg_accum = 0

    init_embed = discord.Embed(
        title="🎃 ĐẠI CHIẾN BẮT ĐẦU: KIZUNA - HUYẾT MA ĐẾ (PHASE 1)",
        description=f"🔥 **{len(combatants)} Dũng Giả** cùng toàn bộ thẻ bài xuất kích nghênh chiến!",
        color=0x991B1B
    )
    init_embed.set_thumbnail(url=p1_cfg["image"])
    init_embed.add_field(name="❤️ Sinh Lực Boss:", value=f"`{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**", inline=False)
    msg = await channel.send(embed=init_embed)
    await asyncio.sleep(2.0)

    while p1_hp > 0 and p1_rounds < 35:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants: break
        p1_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        heal_amt = int(p1_max_hp * 0.015)
        p1_hp = min(p1_max_hp, p1_hp + heal_amt)
        passive_log = f"🩸 **[True Vampire]** Huyết Ma Đế hấp thụ ma khí hồi **+{heal_amt:,} HP** (1,5% HP tối đa)!"

        # Debuffs lên Boss
        reisen_boss_log = None
        if boss_mind_turns > 0:
            boss_mind_turns -= 1
            if random.random() < 0.20:
                _mind_dmg = p1_power
                p1_hp = max(0, p1_hp - _mind_dmg)
                reisen_boss_log = f"🌀 **[Red Eye Mind]** Boss tự gây **{_mind_dmg:,} DMG** lên mình! (Còn {boss_mind_turns} lượt)"

        boss_molten_log = None
        if boss_molten_ground_turns > 0:
            boss_molten_ground_turns -= 1
            raw_burn = int(p1_max_hp * 0.02)
            actual_burn, p1_true_dmg_accum, _ = apply_raid_true_damage(raw_burn, p1_true_dmg_accum, p1_true_cap, "Bỏng Mặt Đất")
            if actual_burn > 0:
                p1_hp = max(0, p1_hp - actual_burn)
                boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Thiêu đốt Boss gây **{actual_burn:,} DMG**!"

        boss_stunned = False
        sakuya_stun_notif = None
        marisa_spark_notif = None
        flandre_notif = None
        remilia_notif = None
        reisen_notif = None
        cirno_notif = None
        utsuho_notif = None
        t1_notif = None
        t2_notif = None
        t3_notif = None
        turn_image = None

        # 1. Kích hoạt Stun Sakuya
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 18 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.40:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[18]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#18] Sakuya** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss bị **STUN**!"
                    break

        if boss_freeze_debuff_turns > 0 and not boss_stunned:
            boss_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                boss_stunned = True

        # 2. Toàn quân tung kỹ năng tấn công
        round_player_dmg = 0
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            card_dmg = ac["power"]

            if ac["cid"] == 19 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image: turn_image = EVOL_CONFIG[19]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#19] Marisa** ({c['username']}) tung **Master Spark (×2.0)**! Giáng **{card_dmg:,} DMG**!"

            if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                if random.random() < 0.25:
                    c["flandre_used"] = True
                    raw_rip = int(p1_hp * 0.30)
                    actual_rip, p1_true_dmg_accum, _ = apply_raid_true_damage(raw_rip, p1_true_dmg_accum, p1_true_cap, "Ripples of 495 Years")
                    p1_hp = max(0, p1_hp - actual_rip)
                    c["total_dmg"] += actual_rip
                    if not turn_image: turn_image = EVOL_CONFIG[9]["skill_gif"]
                    flandre_notif = f"🦇 **[Ace 2] [#09] Flandre** ({c['username']}) kích hoạt **Ripples of 495 Years**! Gây **{actual_rip:,} DMG** chuẩn!"

            if ac["cid"] == 12 and ac["is_ace2"]:
                raw_gungnir = int(p1_max_hp * 0.03)
                actual_gungnir, p1_true_dmg_accum, _ = apply_raid_true_damage(raw_gungnir, p1_true_dmg_accum, p1_true_cap, "Gungnir")
                card_dmg += actual_gungnir
                if not turn_image: turn_image = EVOL_CONFIG[12]["skill_gif"]
                remilia_notif = f"🩸 **[Ace 2] [#12] Remilia** ({c['username']}) - **Thương Đỏ Gungnir**: +**{actual_gungnir:,} DMG**!"

            if ac["cid"] == 21 and ac["is_ace2"] and not c.get("reisen_used"):
                if random.random() < 0.25:
                    c["reisen_used"] = True
                    boss_mind_turns = 4
                    if not turn_image: turn_image = EVOL_CONFIG[21]["skill_gif"]
                    reisen_notif = f"🔴 **[Ace 2] [#21] Reisen** ({c['username']}) kích hoạt **Red Eye Mind**! 🌀 Boss bị ảo giác 4 lượt!"

            if ac["cid"] == 23 and ac["is_ace2"] and not c.get("cirno_freeze_used"):
                if random.random() < 0.40:
                    c["cirno_freeze_used"] = True
                    boss_freeze_debuff_turns = 2
                    if not turn_image: turn_image = EVOL_CONFIG[23]["skill_gif"]
                    cirno_notif = f"❄️ **[Ace 2] [#23] Cirno** ({c['username']}) kích hoạt **Perfect Freeze** (40%)! Đóng băng Boss!"

            if ac["cid"] == 13 and ac["is_ace2"]:
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 3.0)
                    boss_molten_ground_turns = 3
                    if not turn_image: turn_image = EVOL_CONFIG[13]["skill_gif"]
                    utsuho_notif = f"☢️ **[Ace 2] [#13] Utsuho** ({c['username']}) tung **Nuclear Spell Card (×3.0)**! Giáng **{card_dmg:,} DMG** & nung đất 3 lượt!"

            # KỸ NĂNG THẺ T1 SEIKI
            if str(ac["cid"]).lower() == "t1":
                if ac.get("is_ace2"):
                    _t1 = t1_ace2_attack(c, ac, p1_rounds, p1_max_hp, "Boss Kizuna", is_boss=True)
                    if _t1.get("multiplier", 1.0) > 1.0:
                        card_dmg = int(card_dmg * _t1["multiplier"])
                    if _t1["bonus"]:
                        actual_cleave, p1_true_dmg_accum, _ = apply_raid_true_damage(_t1["bonus"], p1_true_dmg_accum, p1_true_cap, "Cleave Seiki")
                        card_dmg += actual_cleave
                    if _t1["direct"]:
                        actual_bong, p1_true_dmg_accum, _ = apply_raid_true_damage(_t1["direct"], p1_true_dmg_accum, p1_true_cap, "Bóng Khái Niệm")
                        p1_hp = max(0, p1_hp - actual_bong)
                        c["total_dmg"] += actual_bong
                    if _t1.get("invul"):
                        c["seiki_seal_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        c["seiki_invul_turn"] = p1_rounds
                    if _t1["disable"]:
                        boss_skill_erased, erase_msg = apply_bong_khai_niem_boss("kizuna_event", 1, boss_skill_erased)
                        _t1["logs"].append(erase_msg)
                    if _t1["heal"]: ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + _t1["heal"])
                    if _t1["gif"] and not turn_image: turn_image = _t1["gif"]
                    t1_notif = (t1_notif + "\n" if t1_notif else "") + "\n".join(_t1["logs"])
                elif c.get("seiki_used_turn") != p1_rounds:
                    if not c.get("seiki_spark_used") and random.random() < 0.30:
                        c["seiki_spark_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image: turn_image = T1_SPARK_GIF
                        marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({c['username']}) tung **Master Spark (×1.5)**! Giáng **{card_dmg:,} DMG**!"
                    elif not c.get("seiki_heal_used") and ac["current_hp"] < ac["max_hp"] and random.random() < 0.20:
                        c["seiki_heal_used"] = True
                        c["seiki_used_turn"] = p1_rounds
                        heal_val = int(ac["max_hp"] * 0.30)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image: turn_image = T1_HEAL_GIF

            # KỸ NĂNG THẺ T2 MAHORAGA
            if str(ac["cid"]).lower() == "t2":
                heal_mahoraga = int(ac["max_hp"] * 0.05)
                ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_mahoraga)
                c["mahoraga_adapt_turns"] = c.get("mahoraga_adapt_turns", 0) + 1
                adapt_pct = min(0.90, c["mahoraga_adapt_turns"] * 0.05)
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 1.5)
                    if not turn_image: turn_image = T2_THOAI_MA_GIF
                    t2_notif_str = f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (+{heal_mahoraga:,} HP) & vung **Thoái Ma Kiếm (×1.5)** giáng **{card_dmg:,} DMG**!"
                else:
                    if not turn_image: turn_image = T2_PASSIVE_GIF
                    t2_notif_str = f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt**! Tự hồi +{heal_mahoraga:,} HP (Kháng ST {int(adapt_pct*100)}%)!"
                t2_notif = (t2_notif + "\n" if t2_notif else "") + t2_notif_str

            # KỸ NĂNG THẺ T3 KIZUNA & T4 FATERIA
            if str(ac["cid"]).lower() == "t3":
                t3_st = c.setdefault("t3_state", {})
                _t3 = t3_combat_turn(t3_st, ac, p1_rounds, p1_max_hp, "Boss Kizuna", is_ace2=ac.get("is_ace2"))
                card_dmg = int(card_dmg * _t3["multiplier"])
                if _t3["bonus_hp_dmg"] > 0:
                    actual_hp_dmg, p1_true_dmg_accum, _ = apply_raid_true_damage(_t3["bonus_hp_dmg"], p1_true_dmg_accum, p1_true_cap, "Dark Chain")
                    card_dmg += actual_hp_dmg
                if _t3["gif"] and not turn_image: turn_image = _t3["gif"]
                t3_notif = (t3_notif + "\n" if t3_notif else "") + "\n".join(_t3["logs"])

            if str(ac["cid"]).lower() == "t4":
                t4_st = c.setdefault("t4_state", {})
                _t4 = t4_combat_turn(t4_st, ac, "Boss Kizuna", heal_mult=1.0, enemy_fate_loop_turns=c.get("ev_fate_turns", 0))
                card_dmg = int(card_dmg * _t4["multiplier"])
                if _t4["save_loop_invul"]:
                    c["seiki_invul_turn"] = p1_rounds
                if _t4["fate_loop_triggered"]:
                    c["ev_fate_turns"] = 2
                    boss_skill_erased = "fate_locked"
                if _t4["ice_spear_triggered"]:
                    boss_freeze_debuff_turns = max(boss_freeze_debuff_turns, 2)
                if _t4["gif"] and not turn_image: turn_image = _t4["gif"]
                if _t4["logs"]:
                    t3_notif = (t3_notif + "\n" if t3_notif else "") + "\n".join([f"({c['username']}) {l}" for l in _t4["logs"]])

            round_player_dmg += card_dmg
            c["total_dmg"] += card_dmg

        p1_hp = max(0, p1_hp - round_player_dmg)
        player_atk_str = f"Toàn quân xuất trận gây **{round_player_dmg:,} DMG** lên Kizuna!"

        # 3. Boss phản kích
        boss_action_log = ""
        if p1_hp <= 0:
            boss_action_log = "💥 **Kizuna Phase 1 đã bị đánh gục!**"
        elif boss_stunned:
            boss_action_log = "❄️ Boss bị đóng băng thời gian, không thể phát động đòn đánh!"
        else:
            roll_b = random.random()
            if (boss_skill_erased != "blood_chain") and roll_b < 0.20:
                turn_image = p1_cfg["skills"]["blood_chain"]["gif"]
                dmg_total = int(p1_power * 1.5)
                dmg_each = max(100, dmg_total // len(frontline_cards))
                boss_action_log = f"🩸 **[KỸ NĂNG] Kizuna** thi triển **Blood chain (20%)**! Giáng {dmg_total:,} DMG (chia đều **{dmg_each:,} DMG** lên {len(frontline_cards)} thẻ)!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True; invul = True; turn_image = EVOL_CONFIG[15]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                        c["seiki_seal_used"] = True; invul = True; turn_image = T1_SEAL_GIF
                        boss_action_log += f"\n🛡️ **[#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal**! MIỄN THƯƠNG!"
                    if not invul:
                        if str(ac["cid"]).lower() == "t2":
                            adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                            ac["current_hp"] -= int(dmg_each * (1.0 - adapt_pct))
                        else:
                            ac["current_hp"] -= dmg_each
            elif (boss_skill_erased != "dark_chain") and 0.20 <= roll_b < 0.40:
                turn_image = p1_cfg["skills"]["dark_chain"]["gif"]
                dmg_base_each = max(100, p1_power // len(frontline_cards))
                boss_action_log = f"🌑 **[KỸ NĂNG] Kizuna** tung **Dark chain (20%)**! Gây {dmg_base_each:,} DMG cơ bản kèm **15% Máu Tối Đa** từng thẻ tiền tuyến!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True; invul = True; turn_image = EVOL_CONFIG[15]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                        c["seiki_seal_used"] = True; invul = True; turn_image = T1_SEAL_GIF
                        boss_action_log += f"\n🛡️ **[#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal**! MIỄN THƯƠNG!"
                    if not invul:
                        extra_hp = int(ac["max_hp"] * 0.15)
                        if str(ac["cid"]).lower() == "t2":
                            adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                            ac["current_hp"] -= int((dmg_base_each + extra_hp) * (1.0 - adapt_pct))
                        else:
                            ac["current_hp"] -= (dmg_base_each + extra_hp)
            else:
                dmg_each = max(100, p1_power // len(frontline_cards))
                boss_action_log = f"⚔️ Kizuna đánh thường chia đều **{dmg_each:,} DMG** lên {len(frontline_cards)} thẻ tiền tuyến!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    invul = False
                    if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                        if random.random() < 0.40:
                            c["reimu_invul_used"] = True; invul = True; turn_image = EVOL_CONFIG[15]["skill_gif"]
                            boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                    elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p1_rounds or (not c.get("seiki_seal_used") and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                        c["seiki_seal_used"] = True; invul = True; turn_image = T1_SEAL_GIF
                        boss_action_log += f"\n🛡️ **[#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal**! MIỄN THƯƠNG!"
                    if not invul:
                        if str(ac["cid"]).lower() == "t2":
                            adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                            ac["current_hp"] -= int(dmg_each * (1.0 - adapt_pct))
                        else:
                            ac["current_hp"] -= dmg_each

        push_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["current_hp"] <= 0:
                dead_name = ac["name"]
                c["current_card_index"] += 1
                if c["current_card_index"] < len(c["team_cards"]):
                    push_logs.append(f"💀 **{dead_name}** ({c['username']}) gục! ➡️ Đẩy **{c['team_cards'][c['current_card_index']]['name']}** lên!")
                else:
                    c["is_alive"] = False
                    push_logs.append(f"☠️ **{c['username']}** đã hết thẻ bài!")

        round_status = [f"• **{c['username']}**: {c['team_cards'][c['current_card_index']]['name']} (❤️{max(0, c['team_cards'][c['current_card_index']]['current_hp']):,} HP)" if c['is_alive'] else f"• **{c['username']}**: ☠️ Tử trận" for c in combatants]

        r_emb = discord.Embed(
            title=f"🎃 HIỆP {p1_rounds} - KIZUNA HUYẾT MA ĐẾ (PHASE 1)",
            description=f"❤️ **Máu Boss:** `{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**",
            color=0x991B1B
        )
        r_emb.add_field(name="🩸 Nội Tại Hồi Phục:", value=passive_log, inline=False)
        r_emb.add_field(name="💥 Tiền Tuyến Tấn Công:", value=player_atk_str, inline=False)
        if sakuya_stun_notif: r_emb.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
        if marisa_spark_notif: r_emb.add_field(name="🌟 Master Spark:", value=marisa_spark_notif, inline=False)
        if remilia_notif: r_emb.add_field(name="🩸 Thương Đỏ Gungnir:", value=remilia_notif, inline=False)
        if reisen_notif: r_emb.add_field(name="🔴 Red Eye Mind:", value=reisen_notif, inline=False)
        if cirno_notif: r_emb.add_field(name="❄️ Perfect Freeze:", value=cirno_notif, inline=False)
        if utsuho_notif: r_emb.add_field(name="☢️ Nuclear Spell Card:", value=utsuho_notif, inline=False)
        if flandre_notif: r_emb.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
        if t1_notif: r_emb.add_field(name="🔮 Tuyệt Kỹ [#t1] Seiki:", value=t1_notif, inline=False)
        if t2_notif: r_emb.add_field(name="🔱 Thần Tướng [#t2] Mahoraga:", value=t2_notif, inline=False)
        if t3_notif: r_emb.add_field(name="🩸 Hoàng Đế [#t3] Kizuna:", value=t3_notif, inline=False)
        r_emb.add_field(name="👺 Phản Kích Của Boss:", value=boss_action_log, inline=False)
        if push_logs: r_emb.add_field(name="🔄 Thay Đổi Tiền Tuyến:", value="\n".join(push_logs), inline=False)
        r_emb.add_field(name="🛡️ Tình Trạng Đội Hình:", value="\n".join(round_status), inline=False)

        if turn_image: r_emb.set_image(url=turn_image)
        else: r_emb.set_thumbnail(url=p1_cfg["image"])

        all_event_raid_turns.append({
            "round": p1_rounds,
            "phase": 1,
            "title": f"Phase 1 - Hiệp {p1_rounds}: Huyết Ma Đế",
            "short_label": f"P1 - H{p1_rounds}",
            "short_desc": f"Boss còn {p1_hp:,} HP",
            "desc": f"🩸 **Kizuna - Huyết Ma Đế (Phase 1)**\n❤️ Máu Boss: `{get_hp_bar(p1_hp, p1_max_hp)}` **{p1_hp:,}/{p1_max_hp:,} HP**",
            "color": 0x991B1B,
            "image": turn_image,
            "fields": [
                ("🩸 Nội Tại Hồi Phục:", passive_log, False),
                ("💥 Tiền Tuyến Tấn Công:", player_atk_str, False),
                ("👺 Phản Kích Của Boss:", boss_action_log, False),
                ("🛡️ Tình Trạng Đội Hình:", "\n".join(round_status), False)
            ]
        })

        try: await msg.edit(embed=r_emb)
        except Exception: pass
        if p1_hp <= 0: break
        await asyncio.sleep(3.0)

    if p1_hp > 0:
        fail_emb = discord.Embed(
            title="❌ QUÂN ĐOÀN THẤT THỦ TRƯỚC KIZUNA PHASE 1!",
            description=f"Toàn bộ dũng giả đã bị tiêu diệt! Kizuna còn **{p1_hp:,} HP**.",
            color=0xEF4444
        )
        fail_emb.set_thumbnail(url=p1_cfg["image"])
        await channel.send(embed=fail_emb, view=OpenDetailsView(all_event_raid_turns))
        return

    # PHASE 1 DROP REWARDS
    p1_rewards = []
    for uid in participants:
        p = get_player(uid)
        p_items = p.setdefault("items", {})
        p_shards = p.setdefault("shards", {})

        t_roll = random.random()
        tickets = 20.0 if t_roll < 0.10 else (15.0 if t_roll < 0.50 else 10.0)
        p["pull_tickets"] += tickets

        c_roll = random.random()
        candies = 100 if c_roll < 0.10 else (50 if c_roll < 0.40 else 0)
        if candies > 0: p_items["keo_halloween"] = p_items.get("keo_halloween", 0) + candies

        shard_got = False
        if random.random() < 0.025:
            p_shards["kizuna"] = p_shards.get("kizuna", 0) + 1
            shard_got = True

        save_player(p)
        txt = f"• **{p['username']}**: +{tickets:.0f} Vé"
        if candies > 0: txt += f", +{candies} Kẹo 🍬"
        if shard_got: txt += ", 🩸 **+1 Mảnh Kizuna**!"
        p1_rewards.append(txt)

    # ========================================================================
    # PHASE 2: KIZUNA THỨC TỈNH (75,000 HP / 7,000 DMG / WONDER GUARD PHẢN 90% ST)
    # ========================================================================
    p2_cfg = EVENT_BOSS_PHASE2_CONFIG
    p2_max_hp = p2_cfg["hp"]
    p2_hp = p2_max_hp
    p2_power = p2_cfg["power"] # 7,000 DMG
    p2_rounds = 0
    wonder_guard_turns = 0
    boss_skill_erased = None
    boss_mind_turns = 0
    boss_freeze_debuff_turns = 0
    boss_molten_ground_turns = 0

    p2_true_cap = int(p2_max_hp * 0.50)
    p2_true_dmg_accum = 0

    for c in combatants:
        c["current_card_index"] = 0
        c["is_alive"] = True
        c["yukari_station_used"] = False
        c["yukari_lastword_used"] = False
        c["sakuya_stun_used"] = False
        c["reimu_invul_used"] = False
        c["marisa_spark_used"] = False
        c["flandre_used"] = False
        c["reisen_used"] = False
        c["cirno_freeze_used"] = False
        c["seiki_seal_used"] = False
        c["seiki_spark_used"] = False
        c["seiki_heal_used"] = False
        c["seiki_used_turn"] = -1
        c["seal_used"] = False
        c["bong_used"] = False
        c["med_used"] = False
        for cd in c["team_cards"]: cd["current_hp"] = cd["max_hp"]

    p2_emb_init = discord.Embed(
        title="🩸 KIZUNA THỨC TỈNH - HUYẾT MA ĐẾ TỐI THƯỢNG (PHASE 2)",
        description=(
            f"⚡ **Huyết Nguyệt Giáng Lâm:** Toàn bộ thẻ bài dũng giả được hồi sinh và hồi phục 100% HP!\n"
            f"❤️ **Máu:** `{p2_max_hp:,} HP` | ⚔️ **Sức mạnh:** `{p2_power:,} DMG` (chia đều)\n"
            f"🛡️ **Wonder Guard (15%):** Miễn thương & **phản lại 90% sát thương lẫn hiệu ứng** trong 2 lượt!"
        ),
        color=0x450A0A
    )
    p2_emb_init.set_image(url=p2_cfg["image"])
    msg = await channel.send(embed=p2_emb_init)
    await asyncio.sleep(2.5)

    while p2_hp > 0 and p2_rounds < 35:
        active_combatants = [c for c in combatants if c["is_alive"] and c["current_card_index"] < len(c["team_cards"])]
        if not active_combatants: break
        p2_rounds += 1
        frontline_cards = [c["team_cards"][c["current_card_index"]] for c in active_combatants]

        heal_amt = int(p2_max_hp * 0.015)
        p2_hp = min(p2_max_hp, p2_hp + heal_amt)
        passive_log = f"🩸 **[True Vampire]** Tự hồi **+{heal_amt:,} HP** (1,5% HP tối đa)!"

        # Debuffs lên Boss Phase 2
        reisen_boss_log = None
        if boss_mind_turns > 0:
            boss_mind_turns -= 1
            if random.random() < 0.20:
                _mind_dmg = p2_power
                p2_hp = max(0, p2_hp - _mind_dmg)
                reisen_boss_log = f"🌀 **[Red Eye Mind]** Boss tự gây **{_mind_dmg:,} DMG** lên mình! (Còn {boss_mind_turns} lượt)"

        boss_molten_log = None
        if boss_molten_ground_turns > 0:
            boss_molten_ground_turns -= 1
            raw_burn = int(p2_max_hp * 0.02)
            actual_burn, p2_true_dmg_accum, _ = apply_raid_true_damage(raw_burn, p2_true_dmg_accum, p2_true_cap, "Bỏng Mặt Đất")
            if actual_burn > 0:
                p2_hp = max(0, p2_hp - actual_burn)
                boss_molten_log = f"🌋 **[Mặt Đất Nung Chảy]** Thiêu đốt Boss Phase 2 gây **{actual_burn:,} DMG**!"

        boss_stunned = False
        sakuya_stun_notif = None
        marisa_spark_notif = None
        flandre_notif = None
        remilia_notif = None
        reisen_notif = None
        cirno_notif = None
        utsuho_notif = None
        t1_notif = None
        t2_notif = None
        t3_notif = None
        turn_image = None

        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["cid"] == 18 and ac["is_ace2"] and not c["sakuya_stun_used"]:
                if random.random() < 0.40:
                    c["sakuya_stun_used"] = True
                    boss_stunned = True
                    turn_image = EVOL_CONFIG[18]["skill_gif"]
                    sakuya_stun_notif = f"⏳ **[Ace 2] [#18] Sakuya** ({c['username']}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ Boss Phase 2 bị **STUN**!"
                    break

        if boss_freeze_debuff_turns > 0 and not boss_stunned:
            boss_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                boss_stunned = True

        # Tính sát thương & Kỹ năng người chơi Phase 2
        round_player_dmg = 0
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            card_dmg = ac["power"]

            if ac["cid"] == 19 and ac["is_ace2"] and not c.get("marisa_spark_used"):
                if random.random() < 0.30:
                    c["marisa_spark_used"] = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image: turn_image = EVOL_CONFIG[19]["skill_gif"]
                    marisa_spark_notif = f"🌟 **[Ace 2] [#19] Marisa** ({c['username']}) tung **Master Spark (×2.0)**! Giáng **{card_dmg:,} DMG**!"

            if ac["cid"] == 9 and ac["is_ace2"] and not c.get("flandre_used"):
                if random.random() < 0.25:
                    c["flandre_used"] = True
                    raw_rip = int(p2_hp * 0.30)
                    actual_rip, p2_true_dmg_accum, _ = apply_raid_true_damage(raw_rip, p2_true_dmg_accum, p2_true_cap, "Ripples of 495 Years")
                    p2_hp = max(0, p2_hp - actual_rip)
                    c["total_dmg"] += actual_rip
                    if not turn_image: turn_image = EVOL_CONFIG[9]["skill_gif"]
                    flandre_notif = f"🦇 **[Ace 2] [#09] Flandre** ({c['username']}) kích hoạt **Ripples of 495 Years**! Gây **{actual_rip:,} DMG** chuẩn!"

            if ac["cid"] == 12 and ac["is_ace2"]:
                raw_gungnir = int(p2_max_hp * 0.03)
                actual_gungnir, p2_true_dmg_accum, _ = apply_raid_true_damage(raw_gungnir, p2_true_dmg_accum, p2_true_cap, "Gungnir")
                card_dmg += actual_gungnir
                if not turn_image: turn_image = EVOL_CONFIG[12]["skill_gif"]
                remilia_notif = f"🩸 **[Ace 2] [#12] Remilia** ({c['username']}) - **Thương Đỏ Gungnir**: +**{actual_gungnir:,} DMG**!"

            if ac["cid"] == 21 and ac["is_ace2"] and not c.get("reisen_used"):
                if random.random() < 0.25:
                    c["reisen_used"] = True
                    boss_mind_turns = 4
                    if not turn_image: turn_image = EVOL_CONFIG[21]["skill_gif"]
                    reisen_notif = f"🔴 **[Ace 2] [#21] Reisen** ({c['username']}) kích hoạt **Red Eye Mind**! 🌀 Boss bị ảo giác 4 lượt!"

            if ac["cid"] == 23 and ac["is_ace2"] and not c.get("cirno_freeze_used"):
                if random.random() < 0.40:
                    c["cirno_freeze_used"] = True
                    boss_freeze_debuff_turns = 2
                    if not turn_image: turn_image = EVOL_CONFIG[23]["skill_gif"]
                    cirno_notif = f"❄️ **[Ace 2] [#23] Cirno** ({c['username']}) kích hoạt **Perfect Freeze** (40%)! Đóng băng Boss Phase 2!"

            if ac["cid"] == 13 and ac["is_ace2"]:
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 3.0)
                    boss_molten_ground_turns = 3
                    if not turn_image: turn_image = EVOL_CONFIG[13]["skill_gif"]
                    utsuho_notif = f"☢️ **[Ace 2] [#13] Utsuho** ({c['username']}) tung **Nuclear Spell Card (×3.0)**! Giáng **{card_dmg:,} DMG** & nung đất 3 lượt!"

            # KỸ NĂNG THẺ T1 SEIKI
            if str(ac["cid"]).lower() == "t1":
                if ac.get("is_ace2"):
                    _t1 = t1_ace2_attack(c, ac, p2_rounds, p2_max_hp, "Boss Kizuna Phase 2", is_boss=True)
                    if _t1.get("multiplier", 1.0) > 1.0:
                        card_dmg = int(card_dmg * _t1["multiplier"])
                    if _t1["bonus"]:
                        actual_cleave, p2_true_dmg_accum, _ = apply_raid_true_damage(_t1["bonus"], p2_true_dmg_accum, p2_true_cap, "Cleave Seiki")
                        card_dmg += actual_cleave
                    if _t1["direct"]:
                        actual_bong, p2_true_dmg_accum, _ = apply_raid_true_damage(_t1["direct"], p2_true_dmg_accum, p2_true_cap, "Bóng Khái Niệm")
                        p2_hp = max(0, p2_hp - actual_bong)
                        c["total_dmg"] += actual_bong
                    if _t1.get("invul"):
                        c["seiki_seal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        c["seiki_invul_turn"] = p2_rounds
                    if _t1["disable"]:
                        boss_skill_erased, erase_msg = apply_bong_khai_niem_boss("kizuna_event", 2, boss_skill_erased)
                        _t1["logs"].append(erase_msg)
                        if boss_skill_erased == "wonder_guard":
                            wonder_guard_turns = 0
                    if _t1["heal"]: ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + _t1["heal"])
                    if _t1["gif"] and not turn_image: turn_image = _t1["gif"]
                    t1_notif = (t1_notif + "\n" if t1_notif else "") + "\n".join(_t1["logs"])
                elif c.get("seiki_used_turn") != p2_rounds:
                    if not c.get("seiki_spark_used") and random.random() < 0.30:
                        c["seiki_spark_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        card_dmg = int(card_dmg * 1.5)
                        if not turn_image: turn_image = T1_SPARK_GIF
                        marisa_spark_notif = (marisa_spark_notif + "\n" if marisa_spark_notif else "") + f"🌟 **[Nhóm T] [#t1] Seiki** ({c['username']}) tung **Master Spark (×1.5)**! Giáng **{card_dmg:,} DMG**!"
                    elif not c.get("seiki_heal_used") and ac["current_hp"] < ac["max_hp"] and random.random() < 0.20:
                        c["seiki_heal_used"] = True
                        c["seiki_used_turn"] = p2_rounds
                        heal_val = int(ac["max_hp"] * 0.30)
                        ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_val)
                        if not turn_image: turn_image = T1_HEAL_GIF

            # KỸ NĂNG THẺ T2 MAHORAGA
            if str(ac["cid"]).lower() == "t2":
                heal_mahoraga = int(ac["max_hp"] * 0.05)
                ac["current_hp"] = min(ac["max_hp"], ac["current_hp"] + heal_mahoraga)
                c["mahoraga_adapt_turns"] = c.get("mahoraga_adapt_turns", 0) + 1
                adapt_pct = min(0.90, c["mahoraga_adapt_turns"] * 0.05)
                if random.random() < 0.30:
                    card_dmg = int(card_dmg * 1.5)
                    if not turn_image: turn_image = T2_THOAI_MA_GIF
                    t2_notif_str = f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) Thích Nghi (+{heal_mahoraga:,} HP) & vung **Thoái Ma Kiếm (×1.5)** giáng **{card_dmg:,} DMG**!"
                else:
                    if not turn_image: turn_image = T2_PASSIVE_GIF
                    t2_notif_str = f"🔱 **[Nhóm T] [#t2] Mahoraga** ({c['username']}) kích hoạt **The True Adapt**! Tự hồi +{heal_mahoraga:,} HP (Kháng ST {int(adapt_pct*100)}%)!"
                t2_notif = (t2_notif + "\n" if t2_notif else "") + t2_notif_str

            # KỸ NĂNG THẺ T3 KIZUNA & T4 FATERIA
            if str(ac["cid"]).lower() == "t3":
                t3_st = c.setdefault("t3_state", {})
                _t3 = t3_combat_turn(t3_st, ac, p2_rounds, p2_max_hp, "Boss Kizuna Phase 2", is_ace2=ac.get("is_ace2"))
                card_dmg = int(card_dmg * _t3["multiplier"])
                if _t3["bonus_hp_dmg"] > 0:
                    actual_hp_dmg, p2_true_dmg_accum, _ = apply_raid_true_damage(_t3["bonus_hp_dmg"], p2_true_dmg_accum, p2_true_cap, "Dark Chain")
                    card_dmg += actual_hp_dmg
                if _t3["gif"] and not turn_image: turn_image = _t3["gif"]
                t3_notif = (t3_notif + "\n" if t3_notif else "") + "\n".join(_t3["logs"])

            if str(ac["cid"]).lower() == "t4":
                t4_st = c.setdefault("t4_state", {})
                _t4 = t4_combat_turn(t4_st, ac, "Boss Kizuna Phase 2", heal_mult=1.0, enemy_fate_loop_turns=c.get("ev2_fate_turns", 0))
                card_dmg = int(card_dmg * _t4["multiplier"])
                if _t4["save_loop_invul"]:
                    c["seiki_invul_turn"] = p2_rounds
                if _t4["fate_loop_triggered"]:
                    c["ev2_fate_turns"] = 2
                    wonder_guard_turns = 0
                    boss_skill_erased = "fate_locked"
                if _t4["ice_spear_triggered"]:
                    boss_freeze_debuff_turns = max(boss_freeze_debuff_turns, 2)
                if _t4["gif"] and not turn_image: turn_image = _t4["gif"]
                if _t4["logs"]:
                    t3_notif = (t3_notif + "\n" if t3_notif else "") + "\n".join([f"({c['username']}) {l}" for l in _t4["logs"]])

            round_player_dmg += card_dmg
            c["total_dmg"] += card_dmg

        # XỬ LÝ PHẢN 90% SÁT THƯƠNG TỪ WONDER GUARD KIZUNA
        reflected_dmg_log = ""
        if wonder_guard_turns > 0 and boss_skill_erased != "wonder_guard":
            wonder_guard_turns -= 1
            ref_dmg = int(round_player_dmg * 0.90) # Phản đúng 90% sát thương
            ref_each = max(50, ref_dmg // len(frontline_cards))
            for ac in frontline_cards: ac["current_hp"] -= ref_each
            reflected_dmg_log = f"\n🛡️ **[Wonder Guard Hiệu Lực]** Boss MIỄN THƯƠNG và **phản lại {ref_dmg:,} DMG (90%)** ({ref_each:,} DMG/thẻ)!"
        else:
            p2_hp = max(0, p2_hp - round_player_dmg)

        boss_action_log = ""
        if p2_hp <= 0:
            boss_action_log = "💥 **Huyết Ma Đế Kizuna Phase 2 đã bị tiêu diệt hoàn toàn!**"
        elif boss_stunned:
            boss_action_log = "❄️ Boss Phase 2 bị đóng băng thời gian, không thể phát động đòn đánh!"
        else:
            if wonder_guard_turns > 0:
                dmg_each = max(100, p2_power // len(frontline_cards))
                boss_action_log = f"⚔️ [Wonder Guard Duy Trì] Boss chỉ đánh thường, gây chia đều **{dmg_each:,} DMG** lên {len(frontline_cards)} thẻ tiền tuyến!"
                for c in active_combatants:
                    ac = c["team_cards"][c["current_card_index"]]
                    if str(ac["cid"]).lower() == "t2":
                        adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                        ac["current_hp"] -= int(dmg_each * (1.0 - adapt_pct))
                    else:
                        ac["current_hp"] -= dmg_each
            else:
                roll_b = random.random()
                if (boss_skill_erased != "wonder_guard") and roll_b < 0.15: # 15% kích hoạt Wonder Guard 90%
                    wonder_guard_turns = 2
                    turn_image = p2_cfg["skills"]["wonder_guard"]["gif"]
                    dmg_each = max(100, p2_power // len(frontline_cards))
                    boss_action_log = (
                        f"🛡️ **[Wonder guard (15%)]** Kích hoạt huyết thuẫn: **MIỄN THƯƠNG & PHẢN 90% SÁT THƯƠNG + HIỆU ỨNG** trong 2 lượt!\n"
                        f"⚔️ Kizuna đánh thường chia đều **{dmg_each:,} DMG** lên {len(frontline_cards)} thẻ tiền tuyến!"
                    )
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        if str(ac["cid"]).lower() == "t2":
                            adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                            ac["current_hp"] -= int(dmg_each * (1.0 - adapt_pct))
                        else:
                            ac["current_hp"] -= dmg_each
                elif (boss_skill_erased != "blood_chain") and 0.15 <= roll_b < 0.35: # 20% Blood Chain
                    turn_image = p2_cfg["skills"]["blood_chain"]["gif"]
                    dmg_total = int(p2_power * 1.5)
                    dmg_each = max(100, dmg_total // len(frontline_cards))
                    boss_action_log = f"🩸 **Blood chain (20%)**! Giáng {dmg_total:,} DMG (chia đều **{dmg_each:,} DMG** mỗi thẻ)!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True; invul = True; turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True; invul = True; turn_image = T1_SEAL_GIF
                            boss_action_log += f"\n🛡️ **[#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal**! MIỄN THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                ac["current_hp"] -= int(dmg_each * (1.0 - adapt_pct))
                            else:
                                ac["current_hp"] -= dmg_each
                elif (boss_skill_erased != "dark_chain") and 0.35 <= roll_b < 0.55: # 20% Dark Chain
                    turn_image = p2_cfg["skills"]["dark_chain"]["gif"]
                    dmg_base_each = max(100, p2_power // len(frontline_cards))
                    boss_action_log = f"🌑 **Dark chain (20%)**! Gây {dmg_base_each:,} DMG chia đều kèm **15% Máu Tối Đa** từng thẻ tiền tuyến!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True; invul = True; turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True; invul = True; turn_image = T1_SEAL_GIF
                            boss_action_log += f"\n🛡️ **[#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal**! MIỄN THƯƠNG!"
                        if not invul:
                            extra_hp = int(ac["max_hp"] * 0.15)
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                ac["current_hp"] -= int((dmg_base_each + extra_hp) * (1.0 - adapt_pct))
                            else:
                                ac["current_hp"] -= (dmg_base_each + extra_hp)
                else: # Đánh thường 7,000 DMG chia đều
                    dmg_each = max(100, p2_power // len(frontline_cards))
                    boss_action_log = f"⚔️ Kizuna đánh thường chia đều **{dmg_each:,} DMG** lên {len(frontline_cards)} thẻ tiền tuyến!"
                    for c in active_combatants:
                        ac = c["team_cards"][c["current_card_index"]]
                        invul = False
                        if ac["cid"] == 15 and ac["is_ace2"] and not c["reimu_invul_used"]:
                            if random.random() < 0.40:
                                c["reimu_invul_used"] = True; invul = True; turn_image = EVOL_CONFIG[15]["skill_gif"]
                                boss_action_log += f"\n🛡️ **[Ace 2] [#15] Reimu** ({c['username']}) kích hoạt **Vô Tưởng Chuyển Sinh**! MIỄN THƯƠNG!"
                        elif str(ac["cid"]).lower() == "t1" and (c.get("seiki_invul_turn") == p2_rounds or (not c.get("seiki_seal_used") and random.random() < (0.50 if ac.get("is_ace2") else 0.40))):
                            c["seiki_seal_used"] = True; invul = True; turn_image = T1_SEAL_GIF
                            boss_action_log += f"\n🛡️ **[#t1] Seiki** ({c['username']}) kích hoạt **Fantasy Seal**! MIỄN THƯƠNG!"
                        if not invul:
                            if str(ac["cid"]).lower() == "t2":
                                adapt_pct = min(0.90, c.get("mahoraga_adapt_turns", 1) * 0.05)
                                ac["current_hp"] -= int(dmg_each * (1.0 - adapt_pct))
                            else:
                                ac["current_hp"] -= dmg_each

        push_logs = []
        for c in active_combatants:
            ac = c["team_cards"][c["current_card_index"]]
            if ac["current_hp"] <= 0:
                dead_name = ac["name"]
                c["current_card_index"] += 1
                if c["current_card_index"] < len(c["team_cards"]):
                    push_logs.append(f"💀 **{dead_name}** ({c['username']}) gục! ➡️ Đẩy **{c['team_cards'][c['current_card_index']]['name']}** lên!")
                else:
                    c["is_alive"] = False
                    push_logs.append(f"☠️ **{c['username']}** đã hết thẻ bài!")

        round_status = [f"• **{c['username']}**: {c['team_cards'][c['current_card_index']]['name']} (❤️{max(0, c['team_cards'][c['current_card_index']]['current_hp']):,} HP)" if c['is_alive'] else f"• **{c['username']}**: ☠️ Tử trận" for c in combatants]

        r_emb = discord.Embed(
            title=f"🎃 HIỆP {p2_rounds} - KIZUNA THỨC TỈNH (PHASE 2)",
            description=f"❤️ **Máu Boss:** `{get_hp_bar(p2_hp, p2_max_hp)}` **{p2_hp:,}/{p2_max_hp:,} HP**",
            color=0x450A0A
        )
        r_emb.add_field(name="🩸 Nội Tại Hồi Phục:", value=passive_log, inline=False)
        r_emb.add_field(name="💥 Tiền Tuyến Tấn Công:", value=f"{player_atk_str}{reflected_dmg_log}", inline=False)
        if sakuya_stun_notif: r_emb.add_field(name="❄️ Kỹ Năng Đột Biến:", value=sakuya_stun_notif, inline=False)
        if marisa_spark_notif: r_emb.add_field(name="🌟 Master Spark:", value=marisa_spark_notif, inline=False)
        if remilia_notif: r_emb.add_field(name="🩸 Thương Đỏ Gungnir:", value=remilia_notif, inline=False)
        if reisen_notif: r_emb.add_field(name="🔴 Red Eye Mind:", value=reisen_notif, inline=False)
        if cirno_notif: r_emb.add_field(name="❄️ Perfect Freeze:", value=cirno_notif, inline=False)
        if utsuho_notif: r_emb.add_field(name="☢️ Nuclear Spell Card:", value=utsuho_notif, inline=False)
        if flandre_notif: r_emb.add_field(name="🦇 Ripples of 495 Years:", value=flandre_notif, inline=False)
        if t1_notif: r_emb.add_field(name="🔮 Tuyệt Kỹ [#t1] Seiki:", value=t1_notif, inline=False)
        if t2_notif: r_emb.add_field(name="🔱 Thần Tướng [#t2] Mahoraga:", value=t2_notif, inline=False)
        if t3_notif: r_emb.add_field(name="🩸 Hoàng Đế [#t3] Kizuna:", value=t3_notif, inline=False)
        r_emb.add_field(name="👺 Phản Kích Của Boss:", value=boss_action_log, inline=False)
        if push_logs: r_emb.add_field(name="🔄 Thay Đổi Tiền Tuyến:", value="\n".join(push_logs), inline=False)
        r_emb.add_field(name="🛡️ Tình Trạng Đội Hình:", value="\n".join(round_status), inline=False)

        if turn_image: r_emb.set_image(url=turn_image)
        else: r_emb.set_thumbnail(url=p2_cfg["image"])

        all_event_raid_turns.append({
            "round": p2_rounds,
            "phase": 2,
            "title": f"Phase 2 - Hiệp {p2_rounds}: Thức Tỉnh",
            "short_label": f"P2 - H{p2_rounds}",
            "short_desc": f"Boss còn {p2_hp:,} HP",
            "desc": f"🩸 **Kizuna - Huyết Ma Đế Thức Tỉnh (Phase 2)**\n❤️ Máu Boss: `{get_hp_bar(p2_hp, p2_max_hp)}` **{p2_hp:,}/{p2_max_hp:,} HP**",
            "color": 0x450A0A,
            "image": turn_image,
            "fields": [
                ("🩸 Nội Tại Hồi Phục:", passive_log, False),
                ("💥 Tiền Tuyến Tấn Công:", f"{player_atk_str}{reflected_dmg_log}", False),
                ("👺 Phản Kích Của Boss:", boss_action_log, False),
                ("🛡️ Tình Trạng Đội Hình:", "\n".join(round_status), False)
            ]
        })

        try: await msg.edit(embed=r_emb)
        except Exception: pass
        if p2_hp <= 0: break
        await asyncio.sleep(3.0)

    p2_won = (p2_hp <= 0)
    final_emb = discord.Embed(
        title="🏆 HOÀN TẤT EVENT RAID BOSS: KIZUNA - HUYẾT MA ĐẾ!",
        description=f"Kết quả Phase 2: {'🎉 **CHIẾN THẮNG HUY HOÀNG (Boss 0 HP)!**' if p2_won else f'💀 **THẤT THỦ TẠI PHASE 2 (Boss còn {p2_hp:,} HP)!**'}",
        color=0x10B981 if p2_won else 0xF59E0B
    )
    final_emb.set_thumbnail(url=p2_cfg["image"] if p2_won else p1_cfg["image"])
    final_emb.add_field(name="📦 Phần Thưởng Phase 1 (Đã trao):", value="\n".join(p1_rewards), inline=False)

    if p2_won:
        p2_rewards = []
        for uid in participants:
            p = get_player(uid)
            p_items = p.setdefault("items", {})
            p_shards = p.setdefault("shards", {})

            t_roll = random.random()
            tickets = 20.0 if t_roll < 0.10 else (15.0 if t_roll < 0.50 else 10.0)
            p["pull_tickets"] += tickets

            c_roll = random.random()
            candies = 120 if c_roll < 0.50 else (70 if c_roll < 0.80 else 0)
            if candies > 0: p_items["keo_halloween"] = p_items.get("keo_halloween", 0) + candies

            shard_got = False
            if random.random() < 0.07:
                p_shards["kizuna"] = p_shards.get("kizuna", 0) + 1
                shard_got = True

            ev_notifs = update_event_quest_progress(p, "event_raid", 1)
            save_player(p)
            txt = f"• **{p['username']}**: +{tickets:.0f} Vé"
            if ev_notifs:
                txt += "\n   " + "\n   ".join(ev_notifs)
            if candies > 0: txt += f", +{candies} Kẹo 🍬"
            if shard_got: txt += ", 🩸 **+1 Mảnh Kizuna**!"
            p2_rewards.append(txt)
        final_emb.add_field(name="💎 Phần Thưởng Siêu Cấp Phase 2 (7% Mảnh Kizuna, 50% 120 Kẹo):", value="\n".join(p2_rewards), inline=False)

    await channel.send(embed=final_emb, view=OpenDetailsView(all_event_raid_turns))



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
    target = get_player(nguoi_dung.id, nguoi_dung.display_name)
    max_lvl = get_max_level(target.get("prestige", 0))
    cap_do = max(1, min(max_lvl, cap_do))
    old_lvl, old_xp = target["level"], target["xp"]
    new_xp = get_total_xp_for_level(cap_do, max_lvl)
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
    target = get_player(member.id, member.display_name)
    max_lvl = get_max_level(target.get("prestige", 0))
    level = max(1, min(max_lvl, level))
    target["xp"] = get_total_xp_for_level(level, max_lvl)
    target["level"] = level
    save_player(target)
    await ctx.send(f"✅ Đã set level cho {member.mention} thành **Lv.{level}** (Đồng bộ: {target['xp']:,} XP).")

@bot.tree.command(name="admin_confiscate", description="[CHỦ BOT DUY NHẤT] Tước đoạt thẻ bài của người chơi (trừng phạt cheat bẩn)")
@app_commands.describe(nguoi_dung="Người chơi bị xử phạt", id_the="ID thẻ từ 1-27 (hoặc nhập 0 để tịch thu TOÀN BỘ)", so_luong="Số lượng thẻ (0 = tịch thu hết)")
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
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-27)!", ephemeral=True)
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
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-27)!")
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
@app_commands.describe(id_the="ID thẻ (1-27 hoặc t1)", so_luong="Số lượng thẻ (mặc định: 1)", nguoi_dung="Người nhận (để trống nếu tự cấp cho bản thân)")
async def slash_admin_add_card(interaction: discord.Interaction, id_the: str, so_luong: int = 1, nguoi_dung: discord.Member = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!**", ephemeral=True)
        return
    norm_id = normalize_card_id(id_the)
    if not norm_id or norm_id not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-27 hoặc t1)!", ephemeral=True)
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
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-27 hoặc t1)!")
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
    elif s_key in ["mahoraga", "t2", "batach"]:
        s_key = "mahoraga"
    elif s_key in ["kizuna", "t3", "vampire"]:
        s_key = "kizuna"
    elif s_key in ["fateria", "t4", "sophan"]:
        s_key = "fateria"
    elif s_key in ["thanh_loi", "thanhloi", "core", "loi"]:
        s_key = "thanh_loi"
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
    elif s_key in ["mahoraga", "t2", "batach"]:
        s_key = "mahoraga"
    elif s_key in ["kizuna", "t3", "vampire"]:
        s_key = "kizuna"
    elif s_key in ["fateria", "t4", "sophan"]:
        s_key = "fateria"
    elif s_key in ["thanh_loi", "thanhloi", "core", "loi"]:
        s_key = "thanh_loi"
    shards = target_player.setdefault("shards", {})
    shards[s_key] = shards.get(s_key, 0) + quantity
    save_player(target_player)
    await ctx.send(f"🔮 Đã cấp **+{quantity} Mảnh `{s_key}`** cho {target.mention} (Tổng kho: {shards[s_key]}/10)! Dùng `/t translate` để đổi thẻ.")

@bot.tree.command(name="admin_lock", description="[CHỦ BOT DUY NHẤT] Khóa lá bài đã sở hữu của người chơi (chỉ mở khi pull ra lại)")
@app_commands.describe(nguoi_dung="Người chơi bị khóa thẻ", id_the="ID lá bài từ 1-27")
async def slash_admin_lock(interaction: discord.Interaction, nguoi_dung: discord.Member, id_the: int):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Chỉ chủ bot mới có quyền khóa thẻ.", ephemeral=True)
        return

    if id_the not in CARDS_DATA:
        await interaction.response.send_message(f"❌ ID thẻ không hợp lệ (1-27)!", ephemeral=True)
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
        await ctx.send(f"❌ ID thẻ không hợp lệ (1-27)!")
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
# 10. CƠ CHẾ TIẾN HÓA /evol (ACE 2 - KHẤU TRỪ CHI PHÍ, BUFF +300/+300, MARISA & SEIKI ACE 2)
# ==============================================================================
class EvolSelectView(discord.ui.View):
    def __init__(self, player, user_id):
        super().__init__(timeout=120)
        self.player = player
        self.user_id = user_id

    @discord.ui.button(label="🌌 [#04] Tiến Hóa Yukari Ace 2 (10 Thẻ + 1 Quạt Giấy 🪭)", style=discord.ButtonStyle.primary, emoji="🪭", row=0)
    async def button_evol_yukari(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 4)
        
    @discord.ui.button(label="⛩️ [#15] Tiến Hóa Reimu Ace 2 (20 Thẻ)", style=discord.ButtonStyle.danger, emoji="🌸")
    async def button_evol_reimu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 15)

    @discord.ui.button(label="🕰️ [#18] Tiến Hóa Sakuya Ace 2 (30 Thẻ)", style=discord.ButtonStyle.primary, emoji="⏳")
    async def button_evol_sakuya(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 18)

    @discord.ui.button(label="🌟 [#19] Tiến Hóa Marisa Ace 2 (25 Thẻ)", style=discord.ButtonStyle.success, emoji="✨")
    async def button_evol_marisa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 19)

    @discord.ui.button(label="🦇 [#09] Tiến Hóa Flandre Ace 2 (30 Thẻ)", style=discord.ButtonStyle.danger, emoji="💥")
    async def button_evol_flandre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 9)

    @discord.ui.button(label="🌙 [#12] Tiến Hóa Remilia Ace 2 (25 Thẻ)", style=discord.ButtonStyle.primary, emoji="🩸", row=1)
    async def button_evol_remilia(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 12)

    @discord.ui.button(label="🐰 [#21] Tiến Hóa Reisen Ace 2 (40 Thẻ)", style=discord.ButtonStyle.success, emoji="🔴", row=1)
    async def button_evol_reisen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 21)

    @discord.ui.button(label="❄️ [#23] Tiến Hóa Cirno Ace 2 (60 Thẻ)", style=discord.ButtonStyle.primary, emoji="🧊", row=2)
    async def button_evol_cirno(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 23)

    @discord.ui.button(label="☢️ [#13] Tiến Hóa Utsuho Ace 2 (30 Thẻ)", style=discord.ButtonStyle.danger, emoji="💥", row=2)
    async def button_evol_utsuho(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, 13)

    @discord.ui.button(label="🩸 [#t3] Tiến Hóa Kizuna Ace 2 (1 Thánh Lõi)", style=discord.ButtonStyle.danger, emoji="👑", row=3)
    async def button_evol_kizuna(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, "t3")

    @discord.ui.button(label="🔮 [#t1] Tiến Hóa Seiki Ace 2 (10 Mảnh + Ace2 Marisa/Reimu/Sakuya)", style=discord.ButtonStyle.secondary, emoji="♾️", row=3)
    async def button_evol_seiki(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải giao diện của bạn!", ephemeral=True)
            return
        await do_evolve_interaction(interaction, self.player, "t1")
        
def execute_card_evolution(player, cid: Union[int, str]):
    if str(cid).strip().lower() in ("t3", "kizuna", "vampire", "emperor"):
        return execute_kizuna_ace2(player)
    if str(cid).strip().lower() in ("t1", "seiki", "dephap", "toannang"):
        return execute_seiki_ace2(player)

    cfg = EVOL_CONFIG.get(cid)
    if not cfg:
        return False, f"❌ Thẻ ID #{cid} hiện chưa hỗ trợ tính năng tiến hóa Ace 2!", None

    if is_card_ace2(player, cid):
        return False, f"⚠️ Thẻ **[#{cfg['id']:02d}] {cfg['name']}** của bạn đã đạt cảnh giới **{cfg['ace_level']}** từ trước rồi!", None

    cid_str = str(cid)
    inventory = player.get("inventory", {})
    current_cnt = inventory.get(cid_str, 0)
    req_cards = cfg["required_cards"]

    # 1. Kiểm tra số lượng thẻ nhân vật
    if current_cnt < req_cards:
        return (
            False,
            f"❌ Bạn chưa đủ số lượng thẻ **[#{cfg['id']:02d}] {cfg['name']}** trong túi đồ!\n"
            f"• Số thẻ hiện có: **{current_cnt}/{req_cards}** lá\n"
            f"• Cần thêm: **{req_cards - current_cnt}** lá nữa để tiến hóa! (Có thể quay `/pull` hoặc dùng `/trade`)",
            None
        )

    # 2. Kiểm tra vật phẩm đặc biệt (Quạt Giấy nếu là Yukari)
    req_item = cfg.get("required_item")
    if req_item:
        p_items = player.setdefault("items", {})
        if p_items.get(req_item, 0) < 1:
            item_name = ITEMS_DATABASE.get(req_item, {}).get("name", req_item)
            return (
                False,
                f"❌ Bạn cần sở hữu **1x {item_name}** để tiến hóa **[#{cfg['id']:02d}] {cfg['name']}** lên Ace 2!\n"
                f"💡 *Có thể mua trong `/token` (600 Token), giao dịch qua `/item trade` hoặc săn Boss Phase 2.*",
                None
            )

    # 3. Khấu trừ chi phí thẻ & vật phẩm
    player["inventory"][cid_str] = current_cnt - req_cards
    remaining_cnt = player["inventory"][cid_str]
    
    item_deduct_str = ""
    if req_item:
        player["items"][req_item] -= 1
        item_name = ITEMS_DATABASE.get(req_item, {}).get("name", req_item)
        item_deduct_str = f" và **1x {item_name}** *(Kho còn: {player['items'][req_item]} cái)*"

    if "evolutions" not in player or not isinstance(player["evolutions"], dict):
        player["evolutions"] = {}
    player["evolutions"][cid_str] = 2
    save_player(player)

    color_map = {4: 0x8B5CF6, 9: 0xDC2626, 15: 0xEF4444, 18: 0x3B82F6, 19: 0xF59E0B, 12: 0x9333EA, 21: 0xEC4899, 23: 0x06B6D4, 13: 0xF97316}
    embed = discord.Embed(
        title=f"🌟 TIẾN HÓA THÀNH CÔNG: [{cfg['ace_level']}] [#{cfg['id']:02d}] {cfg['name'].upper()}!",
        description=(
            f"⚡ **TIẾN TRÌNH ĐẠT CẢNH GIỚI TỐI THƯỢNG:**\n"
            f"🎴 **ID & Nhân vật:** **[#{cfg['id']:02d}] {cfg['name']}**\n"
            f"⭐ **Cấp bậc mới:** `{cfg['ace_level']}`\n"
            f"📉 **Khấu trừ chi phí:** Đã tiêu hao **{req_cards}** lá{item_deduct_str} *(Túi đồ còn lại: **{remaining_cnt}** lá)*\n\n"
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

async def do_evolve_interaction(interaction: discord.Interaction, player, cid: Union[int, str]):
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
        if nv_clean in ("4", "#4", "04", "#04") or "yukari" in nv_clean:
            cid_target = 4
        elif "15" in nv_clean or "reimu" in nv_clean:
            cid_target = 15
        elif "18" in nv_clean or "sakuya" in nv_clean:
            cid_target = 18
        elif "19" in nv_clean or "marisa" in nv_clean:
            cid_target = 19
        elif nv_clean in ("9", "#9", "09", "#09") or "flandre" in nv_clean or "flan" in nv_clean:
            cid_target = 9
        elif nv_clean in ("12", "#12") or "remilia" in nv_clean or "remi" in nv_clean:
            cid_target = 12
        elif nv_clean in ("21", "#21") or "reisen" in nv_clean or "udonge" in nv_clean:
            cid_target = 21
        elif nv_clean in ("23", "#23") or "cirno" in nv_clean or "băng" in nv_clean:
            cid_target = 23
        elif nv_clean in ("13", "#13") or "utsuho" in nv_clean or "okuu" in nv_clean or "reiuji" in nv_clean:
            cid_target = 13
        elif nv_clean in ("t3", "#t3", "kizuna", "vampire", "emperor"):
            cid_target = "t3"
        elif nv_clean in ("t1", "#t1", "seiki", "dephap", "toannang"):
            cid_target = "t1"

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

    reimu_cnt = player.get("inventory", {}).get("15", 0)
    reimu_ace = is_card_ace2(player, 15)
    reimu_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if reimu_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if reimu_cnt >= 20 else f"🔴 Chưa đủ ({reimu_cnt}/20)")

    sakuya_cnt = player.get("inventory", {}).get("18", 0)
    sakuya_ace = is_card_ace2(player, 18)
    sakuya_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if sakuya_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if sakuya_cnt >= 30 else f"🔴 Chưa đủ ({sakuya_cnt}/30)")

    marisa_cnt = player.get("inventory", {}).get("19", 0)
    marisa_ace = is_card_ace2(player, 19)
    marisa_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if marisa_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if marisa_cnt >= 25 else f"🔴 Chưa đủ ({marisa_cnt}/25)")

    flandre_cnt = player.get("inventory", {}).get("9", 0)
    flandre_ace = is_card_ace2(player, 9)
    flandre_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if flandre_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if flandre_cnt >= 30 else f"🔴 Chưa đủ ({flandre_cnt}/30)")

    remilia_cnt = player.get("inventory", {}).get("12", 0)
    remilia_ace = is_card_ace2(player, 12)
    remilia_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if remilia_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if remilia_cnt >= 25 else f"🔴 Chưa đủ ({remilia_cnt}/25)")

    reisen_cnt = player.get("inventory", {}).get("21", 0)
    reisen_ace = is_card_ace2(player, 21)
    reisen_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if reisen_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if reisen_cnt >= 40 else f"🔴 Chưa đủ ({reisen_cnt}/40)")

    cirno_cnt = player.get("inventory", {}).get("23", 0)
    cirno_ace = is_card_ace2(player, 23)
    cirno_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if cirno_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if cirno_cnt >= 60 else f"🔴 Chưa đủ ({cirno_cnt}/60)")

    utsuho_cnt = player.get("inventory", {}).get("13", 0)
    utsuho_ace = is_card_ace2(player, 13)
    utsuho_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐" if utsuho_ace else ("🟢 SẴN SÀNG TIẾN HÓA!" if utsuho_cnt >= 30 else f"🔴 Chưa đủ ({utsuho_cnt}/30)")

    yukari_cnt = player.get("inventory", {}).get("4", 0)
    yukari_fan_cnt = player.get("items", {}).get("quat_giay", 0)
    yukari_ace = is_card_ace2(player, 4)
    if yukari_ace:
        yukari_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐"
    elif yukari_cnt >= 10 and yukari_fan_cnt >= 1:
        yukari_status = "🟢 SẴN SÀNG TIẾN HÓA! (Đủ 10 Thẻ + 1 Quạt Giấy 🪭)"
    else:
        yukari_status = f"🔴 Chưa đủ (Thẻ: {yukari_cnt}/10 | Quạt Giấy: {yukari_fan_cnt}/1)"
        
    seiki_shards = player.get("shards", {}).get("seiki", 0)
    seiki_unlocked = is_card_unlocked(player, "t1") or player.get("inventory", {}).get("t1", 0) > 0
    seiki_ace = is_card_ace2(player, "t1")
    seiki_req_ok = all(is_card_ace2(player, c) for c in T1_ACE2_CONFIG["required_ace2"])
    if seiki_ace:
        seiki_status = "✅ ĐÃ ĐẠT ACE 2 ⭐⭐"
    elif seiki_unlocked and seiki_req_ok and seiki_shards >= 10:
        seiki_status = f"🟢 SẴN SÀNG TIẾN HÓA! (Đã mở thẻ #t1 | Mảnh: {seiki_shards}/10)"
    else:
        seiki_status = (
            f"🔴 Chưa đủ (Mở thẻ #t1 qua /translate: {'✅' if seiki_unlocked else '❌'} | "
            f"Ace2 Marisa/Reimu/Sakuya: {'✅' if seiki_req_ok else '❌'} | Mảnh: {seiki_shards}/10)"
        )

    embed = discord.Embed(
        title="🌟 PHÒNG TIẾN HÓA NHÂN VẬT TOUHOU (EVOLUTION - ACE 2)",
        description=(
            "Thu thập đủ số lượng thẻ yêu cầu để tiến hóa nhân vật lên **Ace 2 ⭐⭐**!\n"
            "✨ **Quy tắc Ace:** Sau khi tiến hóa sẽ **trừ đi chi phí thẻ** tương ứng.\n"
            "💪 **Buff Ace 2:** Cộng **+300 ATK** và **+300 HP** vĩnh viễn!\n\n"
            "👉 **Cú pháp theo ID:** `/evol id_hoac_ten:14`, `/evol id_hoac_ten:17`, `/evol id_hoac_ten:18`, `/evol id_hoac_ten:9`, `/evol id_hoac_ten:12`, `/evol id_hoac_ten:20`, `/evol id_hoac_ten:22`, `/evol id_hoac_ten:13`, hoặc `/evol id_hoac_ten:t1`\n"
            "Hoặc bấm các nút bên dưới để tiến hóa ngay:"
        ),
        color=0x8B5CF6
    )

    reimu_cfg = EVOL_CONFIG[15]
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

    sakuya_cfg = EVOL_CONFIG[18]
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

    marisa_cfg = EVOL_CONFIG[19]
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
            f"• Trạng thái: **{flandre_status}**\n"
            f"• Trong túi đồ: **{flandre_cnt}/30** lá *(tiến hóa xong trừ 30 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{flandre_cfg['skill_name']}** (25% xóa 50% HP đối thủ / 30% HP Boss Raid, kích hoạt 1 lần trong trận, kèm GIF trực tiếp!)"
        ),
        inline=False
    )

    remilia_cfg = EVOL_CONFIG[12]
    embed.add_field(
        name=f"🌙 [#{remilia_cfg['id']:02d}] {remilia_cfg['name']} (Yêu cầu 25 thẻ):",
        value=(
            f"• Trạng thái: **{remilia_status}**\n"
            f"• Trong túi đồ: **{remilia_cnt}/25** lá *(tiến hóa xong trừ 25 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{remilia_cfg['skill_name']}** (THỤ ĐỘNG không cần kích hoạt: mọi đòn đánh +3% Máu Tối Đa mục tiêu, kèm GIF chiêu trực tiếp!)"
        ),
        inline=False
    )

    reisen_cfg = EVOL_CONFIG[21]
    embed.add_field(
        name=f"🐰 [#{reisen_cfg['id']:02d}] {reisen_cfg['name']} (Yêu cầu 40 thẻ):",
        value=(
            f"• Trạng thái: **{reisen_status}**\n"
            f"• Trong túi đồ: **{reisen_cnt}/40** lá *(tiến hóa xong trừ 40 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{reisen_cfg['skill_name']}** (25% kích hoạt 1 lần/trận: mục tiêu 20% tự gây sát thương lên bản thân trong 4 turn, không dùng lên chính mình!)"
        ),
        inline=False
    )

    cirno_cfg = EVOL_CONFIG[23]
    embed.add_field(
        name=f"❄️ [#{cirno_cfg['id']:02d}] {cirno_cfg['name']} (Yêu cầu 60 thẻ):",
        value=(
            f"• Trạng thái: **{cirno_status}**\n"
            f"• Trong túi đồ: **{cirno_cnt}/60** lá *(tiến hóa xong trừ 60 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{cirno_cfg['skill_name']}** (40% đóng băng đối phương 1 lần/trận, trong 2 turn tiếp theo có 45% không thể đánh trả)"
        ),
        inline=False
    )

    utsuho_cfg = EVOL_CONFIG[13]
    embed.add_field(
        name=f"☢️ [#{utsuho_cfg['id']:02d}] {utsuho_cfg['name']} (Yêu cầu 30 thẻ):",
        value=(
            f"• Trạng thái: **{utsuho_status}**\n"
            f"• Trong túi đồ: **{utsuho_cnt}/30** lá *(tiến hóa xong trừ 30 lá)*\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **{utsuho_cfg['skill_name']}** (30% gây 3.0x sát thương & nung chảy mặt đất gây bỏng 2% Máu Tối Đa cho bài địch ra sân sau đó trong 3 turn)"
        ),
        inline=False
    )

    yukari_cfg = EVOL_CONFIG[4]
    embed.add_field(
        name=f"🌌 [#{yukari_cfg['id']:02d}] {yukari_cfg['name']} (Yêu cầu: 10 thẻ + 1 Quạt Giấy 🪭):",
        value=(
            f"• Trạng thái: **{yukari_status}**\n"
            f"• Túi đồ: **{yukari_cnt}/10** Thẻ Yukari | **{yukari_fan_cnt}/1** Quạt Giấy 🪭\n"
            f"• Buff Ace: **+300 ATK** & **+300 HP**\n"
            f"• Kỹ năng: **Trip To The Old Station** (30% x2.0 DMG) • **Last Word** (25% x2.5 DMG + Stun 1 turn) • **Invisible Gap** (10% phản 100% đòn đánh thường)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔮 [#t1] Seiki Đệ Nhất Pháp Sư (Ace 2 - Điều kiện đặc biệt):",
        value=(
            f"• Trạng thái: **{seiki_status}**\n"
            "• Điều kiện: **[#19] Marisa + [#15] Reimu + [#18] Sakuya** đều Ace 2 ⭐⭐\n"
            "• Chi phí: **10 Mảnh Seiki** (không khấu trừ thẻ bài)\n"
            "• Buff Ace: **+300 ATK** & **+300 HP**\n"
            "• Kỹ năng: **Cleave** (thụ động +2% Máu tối đa mỗi đòn) • **Medicine Sign** (35% hồi 40% máu) • **Fantasy Seal** (buff lên 50% miễn toàn bộ sát thương 1 hiệp) • **Bóng Khái Niệm** (20%: 1.5x sát thương + 10% máu tối đa + xóa kỹ năng đối thủ)"
        ),
        inline=False
    )
    embed.set_footer(text="Bấm nút chọn hoặc dùng /evol kèm ID nhân vật!")

    view = EvolSelectView(player, user.id)
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="evol", description="Tiến hóa nhân vật lên Ace 2 (9, 12, 13, 15, 18, 19, 21, 23 hoặc t1)")
@app_commands.describe(id_hoac_ten="Nhập số ID thẻ hoặc chọn nhân vật")
@app_commands.choices(id_hoac_ten=[
    app_commands.Choice(name="[#04] Yukari Yakumo (Ace 2 - Cần 10 thẻ + 1 Quạt Giấy 🪭)", value="4"),
    app_commands.Choice(name="[#15] Reimu Hakurei (Ace 2 - Cần 20 thẻ, trừ 20 khi Ace)", value="15"),
    app_commands.Choice(name="[#18] Sakuya Izayoi (Ace 2 - Cần 30 thẻ, trừ 30 khi Ace)", value="18"),
    app_commands.Choice(name="[#19] Marisa Kirisame (Ace 2 - Cần 25 thẻ, Master Spark x2.0)", value="19"),
    app_commands.Choice(name="[#09] Flandre Scarlet (Ace 2 - Cần 30 thẻ, Ripples of 495 Years)", value="9"),
    app_commands.Choice(name="[#12] Remilia Scarlet (Ace 2 - Cần 25 thẻ, Gungnir thụ động +3% Max HP)", value="12"),
    app_commands.Choice(name="[#21] Reisen Udongein Inaba (Ace 2 - Cần 40 thẻ, Red Eye Mind Explosion)", value="21"),
    app_commands.Choice(name="[#23] Cirno (Ace 2 - Cần 60 thẻ, Perfect Freeze)", value="23"),
    app_commands.Choice(name="[#13] Utsuho Reiuji (Ace 2 - Cần 30 thẻ, Nuclear Spell Card)", value="13"),
    app_commands.Choice(name="[#t1] Seiki Đệ Nhất Pháp Sư (Ace 2 - Cần Ace2 Marisa + Reimu + Sakuya & 10 Mảnh Seiki)", value="t1"),
    app_commands.Choice(name="[#t3] Kizuna the emperor of vampire (Ace 2 - Cần 1 Thánh Lõi)", value="t3")
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

    count = max(1, min(40, count))
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
    if 'ev_notifs' in locals() and ev_notifs:
        embed.add_field(name="🎃 Tiến Trình Sự Kiện Halloween:", value="\n\n".join(ev_notifs), inline=False)
    embed.set_footer(text=f"Vé pull còn lại: {player['pull_tickets']:.2f} | Free hôm nay: {player['free_pulls_remaining']}/5")
    if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(embed=embed)
    else: await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="pull", description="Quay thẻ nhân vật Touhou (Free 5 lượt/ngày)")
@app_commands.describe(so_luong="Số lượt quay (1 đến 40, mặc định: 1)")
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

    cur_lvl, xp_in_lvl, needed_xp, ratio = get_level_progress(player.get("xp", 0), player.get("prestige", 0))
    lvl_buff_pwr = get_level_atk_buff(cur_lvl)
    lvl_buff_hp = get_level_hp_buff(cur_lvl)
    act = action.lower().strip() if action else "view"
    if card_id is not None:
        card_id = normalize_card_id(card_id)

    if act == "add":
        if not card_id or card_id not in CARDS_DATA:
            msg = f"❌ Vui lòng nhập số ID thẻ hợp lệ (1-27 hoặc t1)!"
            if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else: await ctx_or_interaction.send(msg)
            return

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

    p_lvl = player.get("prestige", 0)
    p_tokens = player.get("tokens", 0)
    p_mult = get_prestige_xp_multiplier(p_lvl)
    prestige_str = f" 👑 **[Prestige {p_lvl}]** *(x{p_mult:g} XP Bonus)*" if p_lvl > 0 else ""

    filled_bars = int(ratio * 10)
    bar_str = "▰" * filled_bars + "▱" * (10 - filled_bars)
    embed = discord.Embed(title=f"🛡️ ĐỘI HÌNH CHIẾN ĐẤU - {user.display_name.upper()}", color=0x3B82F6)
    embed.add_field(
        name=f"⭐ CẤP ĐỘ: Lv.{cur_lvl}{prestige_str}",
        value=(
            f"• **Tiến trình:** `{bar_str}` **{xp_in_lvl}/{needed_xp} XP** (Cần {needed_xp - xp_in_lvl} XP để lên Lv.{cur_lvl + 1})\n"
            f"• **Buff Lv.{cur_lvl}:** +{lvl_buff_pwr:,} Power & +{lvl_buff_hp:,} HP\n"
            f"• 💎 **Số dư Tokens:** **{p_tokens:,}** tokens *(Dùng `/token` để mở Token Shop)*"
        ),
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
@app_commands.describe(hanh_dong="view (xem), add (thêm thẻ), remove (gỡ thẻ)", id_the="ID thẻ (1-27 hoặc t1)")
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
    for cid in range(1, 29):
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
    for t_cid in ["t1", "t2", "t3", "t4"]:
        if t_cid in CARDS_DATA:
            t_card = CARDS_DATA[t_cid]
            t_cnt = player["inventory"].get(t_cid, 0)
            t_unlocked = is_card_unlocked(player, t_cid)
            t_ace_mark = " ⭐⭐ [Ace 2]" if is_card_ace2(player, t_cid) else ""
            if t_cnt > 0 or t_unlocked:
                t_status = f"✅ **{format_card_id(t_card['id'])} [{t_card['rank']}] {t_card['name']}** ×{t_cnt}{t_ace_mark}"
            else:
                t_status = f"🔒 `{format_card_id(t_card['id'])}` [{t_card['rank']}] {t_card['name']} *(Chưa sở hữu)*"
            if t_cid == "t1":
                t_shard_info = f"   └ 💎 **Mảnh Seiki:** `{shards_cnt}/10` mảnh"
                if shards_cnt >= 10:
                    t_shard_info += " ✨ *(Đủ 10 mảnh! Dùng `/t translate` để đổi ngay!)*"
            elif t_cid == "t2":
                mahoraga_shards = player.get("shards", {}).get("mahoraga", 0)
                t_shard_info = f"   └ 🔱 **Mảnh Mahoraga:** `{mahoraga_shards}/10` mảnh"
                if mahoraga_shards >= 10:
                    t_shard_info += " ✨ *(Đủ 10 mảnh! Dùng `/t translate loai_shard:mahoraga` để đổi ngay!)*"
            elif t_cid == "t3":
                kizuna_shards = player.get("shards", {}).get("kizuna", 0)
                thanh_loi_shards = player.get("shards", {}).get("thanh_loi", 0)
                t_shard_info = f"   └ 🩸 **Mảnh Kizuna:** `{kizuna_shards}/15` | 👑 **Thánh Lõi:** `{thanh_loi_shards}/1`"
                if kizuna_shards >= 15:
                    t_shard_info += " ✨ *(Đủ 15 mảnh! Dùng `/t translate loai_shard:kizuna` để đổi ngay!)*"
            elif t_cid == "t4":
                fateria_shards = player.get("shards", {}).get("fateria", 0)
                t_shard_info = f"   └ ⏳ **Mảnh Fateria:** `{fateria_shards}/20` mảnh"
                if fateria_shards >= 20:
                    t_shard_info += " ✨ *(Đủ 20 mảnh! Dùng `/t translate loai_shard:fateria` để đổi ngay!)*"
            t_lines.append(f"{t_status}\n{t_shard_info}")

    desc_text = "\n".join(lines)
    if t_lines:
        desc_text += "\n\n🔮 **THẺ ĐẶC BIỆT (NHÓM T - ĐỔI TỪ MẢNH SHARDS):**\n" + "\n".join(t_lines)

    embed = discord.Embed(title=f"📖 BỘ SƯU TẬP THẺ TOUHOU ({owned}/28)", description=desc_text, color=0x8B5CF6)

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

@bot.tree.command(name="collection", description="Kiểm tra bộ sưu tập 28 nhân vật Touhou đã sở hữu")
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
    elif shard_key in ["mahoraga", "t2", "batach", "than_tuong", "kiem_than_tuong", "mahoraga_shard"]:
        shard_key = "mahoraga"
        target_card_id = "t2"
        needed_shards = 10
    elif shard_key in ["kizuna", "t3", "vampire", "emperor", "kizuna_shard"]:
        shard_key = "kizuna"
        target_card_id = "t3"
        needed_shards = 15
    elif shard_key in ["fateria", "t4", "fateria_shard", "sophan", "khuonmau"]:
        shard_key = "fateria"
        target_card_id = "t4"
        needed_shards = 20
    else:
        msg = f"❌ Loại mảnh `{loai_shard}` không tồn tại! Hiện tại có: `seiki` (10 mảnh), `mahoraga` (10 mảnh), `kizuna` (15 mảnh) và `fateria` (20 mảnh)."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    cur_shards = shards_dict.get(shard_key, 0)
    card_info = CARDS_DATA[target_card_id]
    
    if cur_shards < needed_shards:
        shard_names = {"seiki": "Mảnh Seiki", "mahoraga": "Mảnh Mahoraga", "kizuna": "Mảnh Kizuna", "fateria": "Fateria Shards"}
        shard_name_display = shard_names.get(shard_key, "Mảnh")
        hint_text = "Tham gia đánh Boss Raid (Seiki Dị Hình hoặc Reimu Dị Hình) để nhận tỉ lệ 2.5% rơi mảnh Seiki!" if shard_key == "seiki" else "Tham gia đánh Boss Raid Mahoraga 90K HP để nhận tỉ lệ 5% rơi mảnh Mahoraga!"
        msg = (
            f"❌ **Không đủ mảnh quy đổi!**\n"
            f"• Bạn đang có: **{cur_shards}/{needed_shards} {shard_name_display}**\n"
            f"• Cần thêm: **{needed_shards - cur_shards} mảnh** nữa để quy đổi ra thẻ bài **[{card_info['rank']}] #{target_card_id} {card_info['name']}**!\n"
            f"💡 *Mẹo: {hint_text}*"
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    shards_dict[shard_key] -= needed_shards
    if target_card_id not in player.get("unlocked_cards", []):
        player.setdefault("unlocked_cards", []).append(target_card_id)
    player["inventory"][target_card_id] = player["inventory"].get(target_card_id, 0) + 1
    save_player(player)

    if target_card_id == "t4":
        embed = discord.Embed(
            title="⏳ QUY ĐỔI THÀNH CÔNG: FATERIA – KHUÔN MẪU CỦA SỐ PHẬN!",
            description=(
                f"✨ **Chúc mừng {user.mention}!** Bạn đã dung hợp thành công **20 Fateria Shards**!\n\n"
                f"🎴 **THẺ BÀI NHẬN ĐƯỢC:** **[T] #t4 Fateria – Khuôn mẫu của số phận**\n"
                f"• **Chỉ số:** ⚔️ Power: **{card_info['power']:,}** | ❤️ HP: **{card_info['hp']:,}**\n"
                f"• **Bộ kỹ năng thao túng số phận:**\n"
                f"  - 🔄 **Passive - Save loop (15%):** Hồi 50% HP tối đa và miễn nhiễm sát thương turn đó\n"
                f"  - ⛓️ **Skill 1 - Fate loop (20%):** Khiến đối thủ không dùng skill 2 turn liên tiếp (tối đa 2 lần/trận)\n"
                f"  - 🪆 **Skill 2 - Clone attack (40%):** Random 1/3 chiêu con rối (tối đa 2 lần/trận):\n"
                f"    • *Thunder blaze:* 2.3x DMG chia đều sát thương\n"
                f"    • *The fallen hero:* 1.5x DMG + giảm 30% Heal\n"
                f"    • *Ice spear:* 1.5x DMG + 40% không tấn công trong 2 lượt sau\n\n"
                f"📦 **Kho mảnh còn lại:** `{shards_dict[shard_key]} Fateria Shards`"
            ),
            color=0x0EA5E9
        )
        embed.set_image(url=card_info["unlock_gif"])
        embed.set_footer(text="Dùng /team add id_the:t4 để đưa Fateria vào đội hình chiến đấu!")
    elif target_card_id == "t3":
        embed = discord.Embed(
            title="🩸 QUY ĐỔI THÀNH CÔNG: HOÀNG ĐẾ MA CÀ RỒNG KIZUNA!",
            description=(
                f"✨ **Chúc mừng {user.mention}!** Bạn đã dung hợp thành công **15 Mảnh Kizuna**!\n\n"
                f"🎴 **THẺ BÀI NHẬN ĐƯỢC:** **[T] #t3 Kizuna the emperor of vampire**\n"
                f"• **Chỉ số:** ⚔️ Power: **{card_info['power']:,}** | ❤️ HP: **{card_info['hp']:,}**\n"
                f"• **Kỹ năng:**\n"
                f"  - 🩸 **True vampire:** Hồi 5% máu mỗi lượt\n"
                f"  - 💥 **Blood chain (30%):** Gây 1.5x sát thương (1 lần/trận)\n"
                f"  - 🌑 **Dark chain (20%):** Gây 1.0x sát thương + 5% Máu Tối Đa mục tiêu (tối đa 3 lần/trận)\n\n"
                f"📦 **Kho mảnh còn lại:** `{shards_dict[shard_key]} Mảnh Kizuna`"
            ),
            color=0x991B1B
        )
        embed.set_image(url=card_info["image"])
        embed.set_footer(text="Dùng /team add id_the:t3 để đưa Kizuna vào đội hình chiến đấu!")
    elif target_card_id == "t2":
        embed = discord.Embed(
            title="🔱 QUY ĐỔI MẢNH THÀNH CÔNG: TRIỆU HỒI MAHORAGA BÁT ÁCH KIẾM THẦN TƯỚNG!",
            description=(
                f"✨ **Chúc mừng {user.mention}!** Bạn đã dung hợp thành công **10 Mảnh Mahoraga**!\n\n"
                f"🎴 **THẺ BÀI ĐẶC BIỆT NHẬN ĐƯỢC:**\n"
                f"• **Tên:** **[{card_info['rank']}] #{target_card_id} {card_info['name']}**\n"
                f"• **Chỉ số:** ⚔️ Power: **{card_info['power']:,}** | ❤️ HP: **{card_info['hp']:,}**\n"
                f"• **Nội tại & Tuyệt kỹ tối thượng:**\n"
                f"  - 🌀 **The True adapt (100%):** Mỗi turn hồi 5% máu tối đa & mỗi turn giảm 5% sát thương phải nhận (cộng dồn).\n"
                f"  - ⚔️ **Thoái Ma kiếm (30%):** Gây ra 1.5x sát thương cho mục tiêu.\n\n"
                f"📦 **Kho mảnh còn lại:** `{shards_dict[shard_key]} Mảnh Mahoraga`\n"
                f"🎒 **Kho đồ hiện tại:** Đang sở hữu `{player['inventory'][target_card_id]} lá`!"
            ),
            color=0xDC2626
        )
        embed.set_image(url=card_info["image"])
        embed.set_footer(text="Dùng /team add id_the:t2 để đưa Mahoraga vào đội hình chiến đấu!")
    else:
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
    mahoraga_shards = shards_dict.get("mahoraga", 0)
    kizuna_shards = shards_dict.get("kizuna", 0)
    thanh_loi_cnt = shards_dict.get("thanh_loi", 0)
    has_kizuna = player["inventory"].get("t3", 0)
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
    has_mahoraga = player["inventory"].get("t2", 0)
    embed.add_field(
        name="🔱 Mảnh Bát Ách Kiếm Thần Tướng Mahoraga:",
        value=(
            f"• Hiện có: **`{mahoraga_shards}/10` mảnh**\n"
            f"• Tiến độ: `{get_hp_bar(min(10, mahoraga_shards), 10)}` ({min(100, mahoraga_shards * 10)}%)\n"
            f"• Thẻ quy đổi: **[T] #t2 Mahoraga Bát ách kiếm thần tướng** (Kho: {has_mahoraga} lá)\n"
            f"• Thao tác: Gõ `/t translate loai_shard:mahoraga` khi đủ 10 mảnh để quy đổi ngay!\n"
            f"• Nguồn rơi: Tỉ lệ **5%** khi tham gia diệt Boss **Mahoraga** (90K HP)."
        ),
        inline=False
    )
    fateria_shards = shards_dict.get("fateria", 0)
    has_fateria = player["inventory"].get("t4", 0)
    embed.add_field(
        name="⏳ Mảnh Fateria (Khuôn Mẫu Của Số Phận):",
        value=(
            f"• Hiện có: **`{fateria_shards}/20` Fateria Shards**\n"
            f"• Tiến độ: `{get_hp_bar(min(20, fateria_shards), 20)}` ({min(100, fateria_shards * 5)}%)\n"
            f"• Thẻ quy đổi: **[T] #t4 Fateria – Khuôn mẫu của số phận** (Kho: {has_fateria} lá)\n"
            f"• Thao tác: Gõ `/t translate loai_shard:fateria` khi đủ 20 mảnh để quy đổi ngay!\n"
            f"• Nguồn rơi: Tỉ lệ **5%** khi tham gia diệt Boss **Fateria – Khuôn mẫu của số phận** (95K HP / 6K2 DMG)."
        ),
        inline=False
    )
    embed.add_field(
        name="🩸 Mảnh Kizuna & Thánh Lõi (Hoàng Đế Ma Cà Rồng):",
        value=(
            f"• Mảnh Kizuna: **`{kizuna_shards}/15` mảnh** (Kho thẻ: {has_kizuna} lá)\n"
            f"• 👑 **Thánh Lõi (Vật phẩm tiến hóa Ace 2):** **`{thanh_loi_cnt}/1` lõi**\n"
            f"• Thao tác: Gõ `/t translate loai_shard:kizuna` khi đủ 15 mảnh để nhận thẻ [T] #t3 Kizuna!\n"
            f"• Tiến hóa Ace 2: Dùng `/evol id_hoac_ten:t3` khi đã có thẻ Kizuna và 1 Thánh Lõi."
        ),
        inline=False
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
        app_commands.Choice(name="Mảnh Seiki (10 mảnh -> Thẻ [T] #t1 Seiki)", value="seiki"),
        app_commands.Choice(name="Mảnh Mahoraga (10 mảnh -> Thẻ [T] #t2 Mahoraga)", value="mahoraga"),
        app_commands.Choice(name="Mảnh Kizuna (15 mảnh -> Thẻ [T] #t3 Kizuna)", value="kizuna"),
        app_commands.Choice(name="Mảnh Fateria (20 mảnh -> Thẻ [T] #t4 Fateria)", value="fateria")
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
# HỆ THỐNG TUTORIAL TÂN THỦ & NHIỆM VỤ NGÀY
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
# TÍNH NĂNG CHECK NHÂN VẬT & SOI KỸ NĂNG (CHUẨN HÓA TOÀN DIỆN - KHÔNG BỊ KẸT T3)
# ==============================================================================
class CharacterCheckView(discord.ui.View):
    def __init__(self, current_index: int = 0, user_id: int = None, show_ace: bool = False, show_t1: bool = False, show_t2: bool = False, show_t3: bool = False, show_t4: bool = False):
        super().__init__(timeout=180)
        self.current_index = max(0, min(current_index, 27))
        self.user_id = user_id
        self.show_ace = show_ace
        self.show_t1 = show_t1
        self.show_t2 = show_t2
        self.show_t3 = show_t3
        self.show_t4 = show_t4
        self.rebuild_items()

    def rebuild_items(self):
        self.clear_items()
        cid = self.current_index + 1
        has_ace = cid in (4, 9, 12, 13, 15, 18, 19, 21, 23)

        first_btn = discord.ui.Button(label="⏮️", style=discord.ButtonStyle.secondary, row=0)
        first_btn.callback = self.first_page
        self.add_item(first_btn)

        prev_btn = discord.ui.Button(label="◀ Trước", style=discord.ButtonStyle.primary, row=0)
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)

        counter_btn = discord.ui.Button(label=f"#{cid:02d} / 28", style=discord.ButtonStyle.secondary, disabled=True, row=0)
        self.add_item(counter_btn)

        next_btn = discord.ui.Button(label="Sau ▶", style=discord.ButtonStyle.primary, row=0)
        next_btn.callback = self.next_page
        self.add_item(next_btn)

        last_btn = discord.ui.Button(label="⏭️", style=discord.ButtonStyle.secondary, row=0)
        last_btn.callback = self.last_page
        self.add_item(last_btn)

        if (has_ace and not (self.show_t1 or self.show_t2 or self.show_t3 or self.show_t4)) or self.show_t1:
            if self.show_ace:
                ace_toggle = discord.ui.Button(label="⭐ Bản Thường", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
            else:
                ace_toggle = discord.ui.Button(label="🌟 Ace 2 ⭐⭐", style=discord.ButtonStyle.success, emoji="✨", row=1)
            ace_toggle.callback = self.toggle_ace
            self.add_item(ace_toggle)
        else:
            no_ace_btn = discord.ui.Button(label="⭐ Bản Chuẩn", style=discord.ButtonStyle.secondary, disabled=True, row=1)
            self.add_item(no_ace_btn)

        t1_btn = discord.ui.Button(label="#t1 Seiki", style=discord.ButtonStyle.success if self.show_t1 else discord.ButtonStyle.secondary, emoji="🔮", row=1)
        t1_btn.callback = self.show_t1_card
        self.add_item(t1_btn)

        t2_btn = discord.ui.Button(label="#t2 Mahoraga", style=discord.ButtonStyle.success if self.show_t2 else discord.ButtonStyle.secondary, emoji="🔱", row=1)
        t2_btn.callback = self.show_t2_card
        self.add_item(t2_btn)

        t3_btn = discord.ui.Button(label="#t3 Kizuna", style=discord.ButtonStyle.success if self.show_t3 else discord.ButtonStyle.secondary, emoji="🩸", row=1)
        t3_btn.callback = self.show_t3_card
        self.add_item(t3_btn)

        t4_btn = discord.ui.Button(label="#t4 Fateria", style=discord.ButtonStyle.success if self.show_t4 else discord.ButtonStyle.secondary, emoji="⏳", row=1)
        t4_btn.callback = self.show_t4_card
        self.add_item(t4_btn)

        opt_part1 = []
        for i in range(1, 15):
            c = CARDS_DATA[i]
            star = " ⭐⭐" if i in (4, 9, 12, 13, 15, 18, 19, 21, 23) else ""
            opt_part1.append(discord.SelectOption(
                label=f"#{c['id']:02d} [{c['rank']}] {c['name']}{star}"[:100],
                value=str(i),
                description=f"ATK {c['power']:,} | HP {c['hp']:,} • Rank {c['rank']}"[:100],
                default=(i == cid and not (self.show_t1 or self.show_t2 or self.show_t3 or self.show_t4))
            ))
        select1 = discord.ui.Select(placeholder="🔽 Chọn nhanh #01 - #14 (Hecatia ➔ Ibaraki Arm)...", options=opt_part1, row=2)
        select1.callback = self.select_callback
        self.add_item(select1)

        opt_part2 = []
        for i in range(15, 29):
            c = CARDS_DATA[i]
            star = " ⭐⭐" if i in (4, 9, 12, 13, 15, 18, 19, 21, 23) else ""
            opt_part2.append(discord.SelectOption(
                label=f"#{c['id']:02d} [{c['rank']}] {c['name']}{star}"[:100],
                value=str(i),
                description=f"ATK {c['power']:,} | HP {c['hp']:,} • Rank {c['rank']}"[:100],
                default=(i == cid and not (self.show_t1 or self.show_t2 or self.show_t3 or self.show_t4))
            ))
        select2 = discord.ui.Select(placeholder="🔽 Chọn nhanh #15 - #28 (Reimu ➔ Tewi)...", options=opt_part2, row=3)
        select2.callback = self.select_callback
        self.add_item(select2)

    def get_current_embed(self) -> discord.Embed:
        if self.show_t4:
            return self.get_t4_embed()
        if self.show_t3:
            return self.get_t3_embed()
        if self.show_t1:
            return self.get_t1_embed()
        if self.show_t2:
            return self.get_t2_embed()

        cid = self.current_index + 1
        card = CARDS_DATA[cid]
        details = CHARACTER_DETAILS.get(cid, {})
        has_ace = cid in (4, 9, 12, 13, 15, 18, 19, 21, 23)
        is_ace_mode = self.show_ace and has_ace

        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get(str(cid), 0) if player else 0
        is_user_ace = is_card_ace2(player, cid) if player else False
        is_locked = is_card_locked(player, cid) if player else False

        rank_colors = {"SS": 0xF59E0B, "S": 0x8B5CF6, "A": 0x3B82F6, "B": 0x10B981, "C": 0x6B7280}

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
                mode_desc += "\n✨ **Nhân vật này có thể tiến hóa Ace 2 ⭐⭐!** *(Bấm nút 'Ace 2' bên dưới)*"

        if is_locked:
            mode_desc += "\n🔒 **CẢNH BÁO: Thẻ này hiện đang bị ADMIN KHÓA!** Cần quay `/pull` ra lại để mở."

        embed = discord.Embed(title=title, description=mode_desc, color=color)
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
        embed.add_field(name=f"🔮 KỸ NĂNG & NĂNG LỰC: {skill_name}", value=f"{skill_desc}", inline=False)

        if player:
            if is_locked:
                ace_badge = "🔒 [BỊ ADMIN KHÓA]"
            elif is_user_ace:
                ace_badge = "🌟 ĐÃ THỨC TỈNH ACE 2 ⭐⭐"
            elif has_ace:
                req = EVOL_CONFIG[cid]["required_cards"]
                ace_badge = f"🟢 Đủ điều kiện ({owned_cnt}/{req} thẻ) - Dùng `/evol`!" if owned_cnt >= req else f"🔴 Chưa đủ ({owned_cnt}/{req} thẻ)"
            else:
                ace_badge = "Chưa có dạng thức tỉnh"

            embed.add_field(name="🎒 TÚI ĐỒ CỦA BẠN:", value=f"• Sở hữu: **{owned_cnt}** lá\n• Cảnh giới: **{ace_badge}**", inline=True)

        embed.add_field(name="📊 HẠNG THẺ:", value=f"• Thứ tự: **#{cid:02d} / 28**\n• Phẩm cấp: **Rank [{card['rank']}]**", inline=True)
        embed.set_footer(text=f"Trang {self.current_index + 1}/28 • Bấm ◀ / ▶ hoặc dùng Menu chọn nhanh nhân vật!")
        return embed

    async def first_page(self, interaction: discord.Interaction):
        self.current_index = 0
        self.show_ace = self.show_t1 = self.show_t2 = self.show_t3 = self.show_t4 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def prev_page(self, interaction: discord.Interaction):
        self.current_index = (self.current_index - 1) % 28
        self.show_ace = self.show_t1 = self.show_t2 = self.show_t3 = self.show_t4 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_index = (self.current_index + 1) % 28
        self.show_ace = self.show_t1 = self.show_t2 = self.show_t3 = self.show_t4 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def last_page(self, interaction: discord.Interaction):
        self.current_index = 27
        self.show_ace = self.show_t1 = self.show_t2 = self.show_t3 = self.show_t4 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def toggle_ace(self, interaction: discord.Interaction):
        self.show_ace = not self.show_ace
        self.show_t2 = self.show_t3 = self.show_t4 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def select_callback(self, interaction: discord.Interaction):
        selected_id = int(interaction.data["values"][0])
        self.current_index = selected_id - 1
        self.show_ace = self.show_t1 = self.show_t2 = self.show_t3 = self.show_t4 = False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def show_t1_card(self, interaction: discord.Interaction):
        self.show_t1, self.show_t2, self.show_t3, self.show_t4, self.show_ace = True, False, False, False, False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def show_t2_card(self, interaction: discord.Interaction):
        self.show_t1, self.show_t2, self.show_t3, self.show_t4, self.show_ace = False, True, False, False, False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def show_t3_card(self, interaction: discord.Interaction):
        self.show_t1, self.show_t2, self.show_t3, self.show_t4, self.show_ace = False, False, True, False, False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    async def show_t4_card(self, interaction: discord.Interaction):
        self.show_t1, self.show_t2, self.show_t3, self.show_t4, self.show_ace = False, False, False, True, False
        self.rebuild_items()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    def get_t1_embed(self) -> discord.Embed:
        card = CARDS_DATA["t1"]
        details = CHARACTER_DETAILS["t1"]
        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get("t1", 0) if player else 0
        shards_cnt = player.get("shards", {}).get("seiki", 0) if player else 0
        is_locked = is_card_locked(player, "t1") if player else False
        user_has_seiki_ace = is_card_ace2(player, "t1") if player else False
        is_seiki_ace = self.show_ace or user_has_seiki_ace

        embed = discord.Embed(
            title="🌟 [Ace 2 ⭐⭐] #t1 SEIKI ĐỆ NHẤT PHÁP SƯ (THỨC TỈNH)" if is_seiki_ace else "🔮 [THẺ ĐẶC BIỆT NHÓM T] #t1 SEIKI ĐỆ PHÁP TOÀN NĂNG",
            description=(
                "🔥 **Đang xem trạng thái: THỨC TỈNH ACE 2 ⭐⭐**\n*(Được cường hóa +300 Sức Mạnh & +300 Máu, khai mở Tứ Đại Tuyệt Kỹ!)*"
                if is_seiki_ace else
                f"*{details['title']}*\n✨ Thẻ bài thần thoại thu thập **10 Mảnh Seiki** rồi dùng `/t translate`.\n✨ **Nhân vật này có thể tiến hóa Ace 2 ⭐⭐!**"
            ),
            color=0xEF4444 if is_seiki_ace else 0x7C3AED
        )
        embed.set_image(url=EVOL_CONFIG["t1"]["evol_gif"] if is_seiki_ace else card["image"])

        power_val = card["power"] + (300 if is_seiki_ace else 0)
        hp_val = card["hp"] + (300 if is_seiki_ace else 0)
        stats_text = (
            f"• ⚔️ **Sức Mạnh (ATK):** `{power_val:,}`\n"
            f"• ❤️ **Máu (HP):** `{hp_val:,}`\n"
            f"• 🛡️ **Trong Đội Hình (Cấp {user_level}):** `{power_val + lvl_atk_buff:,}` ATK | `{hp_val + lvl_hp_buff:,}` HP"
        )
        embed.add_field(name="⚔️ SỨC MẠNH & CHỈ SỐ:", value=stats_text, inline=False)

        sk = card["skills"]
        skills_text = (
            f"1️⃣ **{sk['fantasy_seal']['name']}** — {sk['fantasy_seal']['desc']}\n"
            f"2️⃣ **{sk['master_spark']['name']}** — {sk['master_spark']['desc']}\n"
            f"3️⃣ **{sk['medicine_sign']['name']}** — {sk['medicine_sign']['desc']}"
        )
        embed.add_field(name="🔮 TAM ĐẠI TUYỆT KỸ (BẢN CHUẨN):", value=skills_text, inline=False)

        if is_seiki_ace:
            embed.add_field(
                name="🌟 TRẠNG THÁI ACE 2 ⭐⭐ - BỘ KỸ NĂNG THỨC TỈNH:",
                value=(
                    "🪓 **Cleave (Nội Tại - 100%):** Mọi đòn đánh thường +**2% Máu Tối Đa** mục tiêu!\n"
                    "💚 **Medicine Sign (35%):** Hồi **40% Máu Tối Đa** bản thân, 1 lần/trận.\n"
                    "🛡️ **Fantasy Seal (50%):** **MIỄN TOÀN BỘ SÁT THƯƠNG** trong 1 hiệp, 1 lần/trận.\n"
                    "🌑 **Bóng Khái Niệm (20%):** Gây **×1.5 Sát Thương** + **10% Máu Tối Đa** + **xóa kỹ năng đối phương**, 1 lần/trận."
                ),
                inline=False
            )

        if player:
            embed.add_field(name="🎒 TÚI ĐỒ CỦA BẠN:", value=f"• Sở hữu: **{owned_cnt}** lá\n• 💎 Mảnh Seiki: **{shards_cnt}/10**", inline=True)
        embed.set_footer(text="Thẻ nhóm T đặc biệt • Bấm ◀ / ▶ hoặc menu để xem 28 nhân vật chuẩn!")
        return embed

    def get_t2_embed(self) -> discord.Embed:
        card = CARDS_DATA["t2"]
        details = CHARACTER_DETAILS.get("t2", {})
        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get("t2", 0) if player else 0
        shards_cnt = player.get("shards", {}).get("mahoraga", 0) if player else 0

        embed = discord.Embed(
            title="🔱 [THẺ ĐẶC BIỆT NHÓM T] #t2 MAHORAGA BÁT ÁCH KIẾM THẦN TƯỚNG",
            description=f"*{details.get('title', 'Bát Ách Kiếm Thần Tướng')}*\n✨ Mở khóa bằng **10 Mảnh Mahoraga** (`/t translate loai_shard:mahoraga`).",
            color=0xDC2626
        )
        embed.set_image(url=card["image"])
        power_val, hp_val = card["power"], card["hp"]
        embed.add_field(
            name="⚔️ SỨC MẠNH & CHỈ SỐ:",
            value=f"• ⚔️ **ATK:** `{power_val:,}` | ❤️ **HP:** `{hp_val:,}`\n• 🛡️ **Trong Đội Hình (Lv.{user_level}):** `{power_val + lvl_atk_buff:,}` ATK | `{hp_val + lvl_hp_buff:,}` HP",
            inline=False
        )
        pas = card.get("passive", {})
        sk = card.get("skills", {})
        embed.add_field(
            name="🔱 BỘ KỸ NĂNG BÁT ÁCH THẦN TƯỚNG:",
            value=f"🌀 **{pas.get('name', 'The True adapt')} (100%):** {pas.get('desc', '')}\n⚔️ **{sk.get('thoai_ma_kiem', {}).get('name', 'Thoái Ma kiếm')} (30%):** {sk.get('thoai_ma_kiem', {}).get('desc', '')}",
            inline=False
        )
        if player:
            embed.add_field(name="🎒 TÚI ĐỒ CỦA BẠN:", value=f"• Sở hữu: **{owned_cnt}** lá\n• 🔱 Mảnh Mahoraga: **{shards_cnt}/10**", inline=True)
        embed.set_footer(text="Thẻ nhóm T đặc biệt • Bấm ◀ / ▶ hoặc menu để xem 28 nhân vật chuẩn!")
        return embed

    def get_t3_embed(self) -> discord.Embed:
        card = CARDS_DATA["t3"]
        details = CHARACTER_DETAILS.get("t3", {})
        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get("t3", 0) if player else 0
        shards_cnt = player.get("shards", {}).get("kizuna", 0) if player else 0
        thanh_loi_cnt = player.get("shards", {}).get("thanh_loi", 0) if player else 0
        is_kizuna_ace = is_card_ace2(player, "t3") if player else False

        embed = discord.Embed(
            title="🩸 [THẺ ĐẶC BIỆT NHÓM T] #t3 KIZUNA THE EMPEROR OF VAMPIRE" + (" - ACE 2 ⭐⭐" if is_kizuna_ace else ""),
            description=f"*{details.get('title', 'Hoàng Đế Ma Cà Rồng')}*\n✨ Mở khóa bằng **15 Mảnh Kizuna** (`/t translate loai_shard:kizuna`). Tiến hóa Ace 2 cần **1 Thánh Lõi**.",
            color=0x991B1B
        )
        embed.set_image(url=card["image"])
        power_val = card["power"] + (300 if is_kizuna_ace else 0)
        hp_val = card["hp"] + (300 if is_kizuna_ace else 0)
        embed.add_field(
            name="⚔️ SỨC MẠNH & CHỈ SỐ:",
            value=f"• ⚔️ **ATK:** `{power_val:,}` | ❤️ **HP:** `{hp_val:,}`\n• 🛡️ **Trong Đội Hình (Lv.{user_level}):** `{power_val + lvl_atk_buff:,}` ATK | `{hp_val + lvl_hp_buff:,}` HP",
            inline=False
        )
        skills_text = (
            "🩸 **True vampire (100%):** Hồi 5% máu tối đa mỗi lượt.\n"
            "💥 **Blood chain (30%):** Gây " + ("**2.0x sát thương** (Ace 2)" if is_kizuna_ace else "**1.5x sát thương**") + " (1 lần/trận).\n"
            "🌑 **Dark chain (" + ("30%" if is_kizuna_ace else "20%") + "):** Gây " + ("**1.5x sát thương**" if is_kizuna_ace else "**1.0x sát thương**") + " + **5% Máu Tối Đa mục tiêu** (tối đa 3 lần/trận)."
        )
        if is_kizuna_ace:
            skills_text += "\n🛡️ **Wonder guard (20% - Ace 2):** Miễn thương & **phản 60% sát thương lẫn hiệu ứng** trong **3 lượt** (1 lần/trận)!"
        embed.add_field(name="🩸 BỘ KỸ NĂNG HOÀNG ĐẾ MA CÀ RỒNG:", value=skills_text, inline=False)
        if player:
            embed.add_field(name="🎒 TÚI ĐỒ CỦA BẠN:", value=f"• Sở hữu: **{owned_cnt}** lá\n• 🩸 Mảnh Kizuna: **{shards_cnt}/15** | 👑 Thánh Lõi: **{thanh_loi_cnt}/1**", inline=True)
        embed.set_footer(text="Thẻ nhóm T đặc biệt • Bấm ◀ / ▶ hoặc menu để xem 28 nhân vật chuẩn!")
        return embed

    def get_t4_embed(self) -> discord.Embed:
        card = CARDS_DATA["t4"]
        details = CHARACTER_DETAILS.get("t4", {})
        player = get_player(self.user_id) if self.user_id else None
        user_level = player.get("level", 1) if player else 1
        lvl_atk_buff = (user_level - 1) * 20
        lvl_hp_buff = (user_level - 1) * 25
        owned_cnt = player.get("inventory", {}).get("t4", 0) if player else 0
        shards_cnt = player.get("shards", {}).get("fateria", 0) if player else 0

        embed = discord.Embed(
            title="⏳ [THẺ ĐẶC BIỆT NHÓM T] #t4 FATERIA – KHUÔN MẪU CỦA SỐ PHẬN",
            description=(
                f"*{details.get('title', 'Khuôn Mẫu Của Số Phận')}*\n"
                "✨ Thẻ bài thần thoại nhóm T mở khóa bằng **20 Fateria Shards** "
                "(dùng lệnh `/t translate loai_shard:fateria`)."
            ),
            color=0x0EA5E9
        )
        embed.set_thumbnail(url=card["image"])
        embed.set_image(url=card["unlock_gif"])

        power_val = card["power"]
        hp_val = card["hp"]
        stats_text = (
            f"• ⚔️ **Sức Mạnh (ATK):** `{power_val:,}`\n"
            f"• ❤️ **Máu (HP):** `{hp_val:,}`\n"
            f"• 🛡️ **Trong Đội Hình (Cấp {user_level}):** `{power_val + lvl_atk_buff:,}` ATK | `{hp_val + lvl_hp_buff:,}` HP"
        )
        embed.add_field(name="⚔️ SỨC MẠNH & CHỈ SỐ:", value=stats_text, inline=False)

        skills_text = (
            "🔄 **Passive - Save loop (15%):** Hồi **50% HP tối đa** và **miễn nhiễm sát thương** trong turn đó.\n"
            f"   🎬 GIF: {card['passive']['gif']}\n"
            "⛓️ **Skill 1 - Fate loop (20%):** Khiến đối thủ **không thể dùng skill 2 turn liên tiếp** (tối đa 2 lần/trận).\n"
            f"   🎬 GIF: {card['skills']['fate_loop']['gif']}\n"
            "🪆 **Skill 2 - Clone attack (40% - tối đa 2 lần/trận):** Random 1/3 chiêu con rối:\n"
            "  • ⚡ **Thunder blaze:** Ngọn lửa chớp điện gây **2.3x DMG** chia đều sát thương.\n"
            "  • 🗡️ **The fallen hero:** Trảm kích ánh sáng **1.5x DMG** + **giảm 30% Heal**.\n"
            "  • ❄️ **Ice spear:** Giáo băng **1.5x DMG** + khiến đối phương **40% không tấn công trong 2 lượt sau**."
        )
        embed.add_field(name="⏳ BỘ KỸ NĂNG KHUÔN MẪU SỐ PHẬN:", value=skills_text, inline=False)

        if player:
            shard_str = "\n✨ *Đã đủ 20 mảnh! Dùng `/t translate loai_shard:fateria` để đổi ngay!*" if shards_cnt >= 20 else ""
            embed.add_field(
                name="🎒 TÚI ĐỒ CỦA BẠN:",
                value=f"• Sở hữu: **{owned_cnt}** lá\n• ⏳ Fateria Shards: **{shards_cnt}/20**{shard_str}",
                inline=True
            )
        embed.add_field(
            name="📊 HẠNG THẺ:",
            value="• Phẩm cấp: **Rank [T] — Đặc Biệt**\n• Nguồn: Đổi từ **20 Fateria Shards**",
            inline=True
        )
        embed.set_footer(text="Thẻ nhóm T đặc biệt • Bấm ◀ / ▶ hoặc menu để xem 28 nhân vật chuẩn!")
        return embed

async def handle_check_character(ctx_or_interaction, nhan_vat: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    
    target_idx = 0
    show_t1_flag = False
    show_t2_flag = False
    show_t3_flag = False
    show_t4_flag = False

    if nhan_vat:
        nv_clean = str(nhan_vat).strip().lower()
        if nv_clean in ("t4", "#t4", "fateria", "sophan", "khuonmau") or "fateria" in nv_clean:
            show_t4_flag = True
        elif nv_clean in ("t3", "#t3", "kizuna", "vampire", "emperor", "huyetma", "huyetmade") or "kizuna" in nv_clean:
            show_t3_flag = True
        elif nv_clean in ("t1", "#t1", "seiki", "dephap", "toannang") or "seiki" in nv_clean:
            show_t1_flag = True
        elif nv_clean in ("t2", "#t2", "mahoraga", "batach", "thantuong", "kiemthantuong") or "mahoraga" in nv_clean:
            show_t2_flag = True
        else:
            clean_num = nv_clean.replace("#", "").strip()
            if clean_num.isdigit():
                val = int(clean_num)
                if 1 <= val <= 28:
                    target_idx = val - 1
            else:
                found = False
                for cid, c in CARDS_DATA.items():
                    if nv_clean in c["name"].lower():
                        cid_s = str(cid).lower()
                        if cid_s == "t1": show_t1_flag = True
                        elif cid_s == "t2": show_t2_flag = True
                        elif cid_s == "t3": show_t3_flag = True
                        elif cid_s == "t4": show_t4_flag = True
                        elif isinstance(cid, int) and 1 <= cid <= 28:
                            target_idx = cid - 1
                        found = True
                        break
    else:
        player = get_player(user.id, user.display_name)
        if player and player.get("team"):
            lead_id = player["team"][0]
            lead_s = str(lead_id).lower()
            if lead_s == "t1": show_t1_flag = True
            elif lead_s == "t2": show_t2_flag = True
            elif lead_s == "t3": show_t3_flag = True
            elif lead_s == "t4": show_t4_flag = True
            elif isinstance(lead_id, int) and 1 <= lead_id <= 28:
                target_idx = lead_id - 1

    view = CharacterCheckView(
        current_index=target_idx,
        user_id=user.id,
        show_ace=False,
        show_t1=show_t1_flag,
        show_t2=show_t2_flag,
        show_t3=show_t3_flag,
        show_t4=show_t4_flag
    )
    embed = view.get_current_embed()

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="check", description="Kiểm tra thông số sức mạnh, máu và kỹ năng của 28 nhân vật Touhou + Nhóm T")
@app_commands.describe(nhan_vat="Nhập số ID (1-28, t1-t4) hoặc tên nhân vật muốn xem ngay")
async def slash_check(interaction: discord.Interaction, nhan_vat: str = None):
    await handle_check_character(interaction, nhan_vat)

@bot.tree.command(name="card_info", description="Xem chi tiết sức mạnh, máu và chiêu thức thẻ bài Touhou + Nhóm T")
@app_commands.describe(nhan_vat="Nhập số ID (1-28, t1-t4) hoặc tên nhân vật muốn xem ngay")
async def slash_card_info(interaction: discord.Interaction, nhan_vat: str = None):
    await handle_check_character(interaction, nhan_vat)

@bot.command(name="check", aliases=["char", "character", "card", "cardinfo"])
async def prefix_check(ctx, *, nhan_vat: str = None):
    await handle_check_character(ctx, nhan_vat)

# ==============================================================================
# HỆ THỐNG PVE BATTLE (ĐẤU THEO LƯỢT NPC GENSOKYO)
# ==============================================================================
GENSOKYO_NPCS = [
    {"name": "Cirno Đệ Nhất", "badge": "❄️ Băng Tinh", "preferred": [20, 21, 23]},
    {"name": "Marisa Đạo Tặc", "badge": "⭐ Tinh Linh", "preferred": [6, 15, 19]},
    {"name": "Alice Ma Đạo", "badge": "🪆 Búp Bê", "preferred": [13, 17, 23]},
    {"name": "Aya Phóng Viên", "badge": "🌪️ Phong Thần", "preferred": [15, 16, 18]},
    {"name": "Youmu Kiếm Hồn", "badge": "⚔️ Song Kiếm", "preferred": [8, 16, 20]},
    {"name": "Remilia Huyết Ma", "badge": "🦇 Huyết Tộc", "preferred": [3, 4, 12]},
    {"name": "Flandre Hủy Diệt", "badge": "💎 Hủy Diệt", "preferred": [3, 5, 9]},
    {"name": "Suika Quỷ Vương", "badge": "🍶 Đại Quỷ", "preferred": [5, 6, 9]},
    {"name": "Mokou Phượng Hoàng", "badge": "🔥 Bất Tử", "preferred": [6, 11, 16]},
    {"name": "Hecatia Hỗn Mang", "badge": "🌌 Hỗn Mang", "preferred": [1, 2, 4]}
]

async def handle_battle(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)

    if player.get("_is_first_time") and not player.get("tutorial", {}).get("completed"):
        player["_is_first_time"] = False
        await send_tutorial_intro(ctx_or_interaction, player)
        return

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
    p_max_lvl = get_max_level(player.get("prestige", 0))
    opp_level = max(1, min(p_max_lvl, player["level"] + random.choice([-1, 0, 1, 2])))
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
    p_flandre, o_flandre = False, False
    o_sakuya, o_reimu, o_marisa = False, False, False
    reisen_used = False
    o_reisen_used = False
    o_mind_turns = 0
    p_mind_turns = 0
    p_t1 = {"seal_used": False, "bong_used": False, "med_used": False, "used_turn": -1}
    p_seiki_seal, p_seiki_spark, p_seiki_heal = False, False, False
    p_mahoraga_turns = 0
    p_t3_state = {}
    o_t3_state = {}
    p_t4_state = {}
    o_fate_lock_turns = 0
    o_ice_spear_turns = 0
    p_seiki_used_turn = -1
    p_cirno_freeze_used = False
    o_cirno_freeze_used = False
    o_freeze_debuff_turns = 0
    p_freeze_debuff_turns = 0
    o_molten_ground_turns = 0
    p_molten_ground_turns = 0
    battle_logs = []
    battle_turns = []
    p_yukari_station, p_yukari_lastword = False, False
    o_yukari_station, o_yukari_lastword = False, False

    while p_idx < len(player_cards) and o_idx < len(opp_cards) and r_cnt < 30:
        r_cnt += 1
        pc = player_cards[p_idx]
        oc = opp_cards[o_idx]
        turn_image = None
        turn_actions = []
        turn_trades = []
        stunned_pc = False
        stunned_oc = False

        if o_mind_turns > 0:
            o_mind_turns -= 1
            if random.random() < 0.20:
                _mc_dmg = oc["power"]
                oc["current_hp"] = max(0, oc["current_hp"] - _mc_dmg)
                msg_mc = f"🌀 **[Red Eye Mind Explosion]** **{oc['name']}** mất kiểm soát và **tự gây {_mc_dmg:,} DMG** lên bản thân! (Còn {o_mind_turns} lượt ảo giác)"
                battle_logs.append(msg_mc)
                turn_actions.append(msg_mc)

        if p_mind_turns > 0:
            p_mind_turns -= 1
            if random.random() < 0.20:
                _mc_dmg = pc["power"]
                pc["current_hp"] = max(0, pc["current_hp"] - _mc_dmg)
                msg_mc = f"🌀 **[Red Eye Mind Explosion]** **{pc['name']}** mất kiểm soát và **tự gây {_mc_dmg:,} DMG** lên bản thân! (Còn {p_mind_turns} lượt ảo giác)"
                battle_logs.append(msg_mc)
                turn_actions.append(msg_mc)

        if o_molten_ground_turns > 0:
            o_molten_ground_turns -= 1
            burn_dmg = int(oc["hp"] * 0.02)
            oc["current_hp"] = max(0, oc["current_hp"] - burn_dmg)
            msg_b = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham thiêu đốt **{oc['name']}** gây **{burn_dmg:,} DMG** (2% Máu Tối Đa)! (Còn {o_molten_ground_turns} turn)"
            battle_logs.append(msg_b)
            turn_actions.append(msg_b)

        if p_molten_ground_turns > 0:
            p_molten_ground_turns -= 1
            burn_dmg = int(pc["hp"] * 0.02)
            pc["current_hp"] = max(0, pc["current_hp"] - burn_dmg)
            msg_b = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham thiêu đốt **{pc['name']}** gây **{burn_dmg:,} DMG** (2% Máu Tối Đa)! (Còn {p_molten_ground_turns} turn)"
            battle_logs.append(msg_b)
            turn_actions.append(msg_b)

        if o_freeze_debuff_turns > 0 and not stunned_oc:
            o_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                stunned_oc = True
                msg_fz = f"❄️ **[Perfect Freeze]** **{oc['name']}** bị đóng băng cứng đờ (45%), không thể phản công trong hiệp này! (Còn {o_freeze_debuff_turns} turn duy trì)"
                battle_logs.append(msg_fz)
                turn_actions.append(msg_fz)

        if p_freeze_debuff_turns > 0 and not stunned_pc:
            p_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                stunned_pc = True
                msg_fz = f"❄️ **[Perfect Freeze]** **{pc['name']}** bị đóng băng cứng đờ (45%), không thể tấn công trong hiệp này! (Còn {p_freeze_debuff_turns} turn duy trì)"
                battle_logs.append(msg_fz)
                turn_actions.append(msg_fz)

        if pc["cid"] == 18 and pc["is_ace2"] and not p_sakuya:
            if random.random() < 0.40:
                p_sakuya = True
                stunned_oc = True
                turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#18] Sakuya** kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ {oc['name']} bị STUN mất lượt!"
                battle_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if oc["cid"] == 18 and oc.get("is_ace2") and not o_sakuya:
            if random.random() < 0.30:
                o_sakuya = True
                stunned_pc = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_skill = f"⏳ **Đối thủ [Ace 2] [#18] Sakuya** kích hoạt **Thời Gian Đóng Băng** (30%)! ❄️ {pc['name']} bị STUN mất lượt!"
                battle_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        curr_pc_power = pc["power"]
        if pc["cid"] == 19 and pc["is_ace2"] and not p_marisa:
            if random.random() < 0.30:
                p_marisa = True
                curr_pc_power = int(curr_pc_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_m = f"🌟 **[Ace 2] [#19] Marisa** tung ra **Master Spark** (30%)! Bộc phá ×2.0 sát thương gây **{curr_pc_power:,} DMG**!"
                battle_logs.append(msg_m)
                turn_actions.append(msg_m)
# Kỹ năng Yukari Ace 2 trong PvE Battle:
        if pc["cid"] == 4 and pc["is_ace2"]:
            if not p_yukari_station and random.random() < 0.30:
                p_yukari_station = True
                curr_pc_power = int(curr_pc_power * 2.0)
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/7e/69/snvix5aVyjKgjesAJV.gif"
                msg_y = f"🌌 **[Ace 2] [#04] Yukari** ({user.display_name}) tung **Trip To The Old Station** (30%)! Sát thương ×2.0 giáng **{curr_pc_power:,} DMG**!"
                battle_logs.append(msg_y)
                turn_actions.append(msg_y)
            elif not p_yukari_lastword and random.random() < 0.25:
                p_yukari_lastword = True
                curr_pc_power = int(curr_pc_power * 2.5)
                stunned_oc = True
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/03/4b/epgnCZ5A8KOdm.gif"
                msg_y = f"👁️ **[Ace 2] [#04] Yukari** ({user.display_name}) kích hoạt **⸮⸮⸮ : Last Word !** (25%)! Bộc phá ×2.5 gây **{curr_pc_power:,} DMG** và **STUN đối thủ**!"
                battle_logs.append(msg_y)
                turn_actions.append(msg_y)
                
        if pc["cid"] == 12 and pc["is_ace2"]:
            gungnir_bonus = int(oc["hp"] * 0.03)
            curr_pc_power += gungnir_bonus
            if not turn_image:
                turn_image = EVOL_CONFIG[12]["skill_gif"]
            turn_actions.append(f"🩸 **[Ace 2] [#12] Remilia** - **Thương Đỏ Gungnir** (Thụ động): Gây thêm **{gungnir_bonus:,} DMG** (3% Máu tối đa đối thủ)!")

        if pc["cid"] == 21 and pc["is_ace2"] and not reisen_used:
            if random.random() < 0.25:
                reisen_used = True
                o_mind_turns = 4
                if not turn_image:
                    turn_image = EVOL_CONFIG[21]["skill_gif"]
                msg_r = f"🔴 **[Ace 2] [#21] Reisen** kích hoạt **Red Eye Mind Explosion** (25%)! 🌀 **{oc['name']}** bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"
                battle_logs.append(msg_r)
                turn_actions.append(msg_r)

        if pc["cid"] == 23 and pc["is_ace2"] and not p_cirno_freeze_used:
            if random.random() < 0.40:
                p_cirno_freeze_used = True
                o_freeze_debuff_turns = 2
                if not turn_image:
                    turn_image = EVOL_CONFIG[23]["skill_gif"]
                msg_c = f"❄️ **[Ace 2] [#23] Cirno** ({user.display_name}) kích hoạt **Perfect Freeze** (40%)! Đóng băng đối thủ: Trong 2 turn tiếp theo có **45% tỷ lệ không thể đánh trả**!"
                battle_logs.append(msg_c)
                turn_actions.append(msg_c)

        if pc["cid"] == 13 and pc["is_ace2"]:
            if random.random() < 0.30:
                curr_pc_power = int(curr_pc_power * 3.0)
                o_molten_ground_turns = 3
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_u = f"☢️ **[Ace 2] [#13] Utsuho Reiuji** ({user.display_name}) bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{curr_pc_power:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa cho bài địch trong 3 turn)!"
                battle_logs.append(msg_u)
                turn_actions.append(msg_u)

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

        if str(pc["cid"]).lower() == "t1":
            if pc.get("is_ace2"):
                _t1 = t1_ace2_attack(p_t1, pc, r_cnt, oc["hp"], f"**{oc['name']}**", is_boss=False)
                if _t1.get("multiplier", 1.0) > 1.0:
                    curr_pc_power = int(curr_pc_power * _t1["multiplier"])
                curr_pc_power += _t1["bonus"]
                if _t1["direct"]:
                    oc["current_hp"] = max(0, oc["current_hp"] - _t1["direct"])
                if _t1.get("invul"):
                    pc_invul = True
                    p_seiki_seal = True
                    p_seiki_used_turn = r_cnt
                if _t1["heal"]:
                    pc["current_hp"] = min(pc["hp"], pc["current_hp"] + _t1["heal"])
                if _t1["disable"]:
                    erase_msg = apply_bong_khai_niem_card(oc)
                    _t1["logs"].append(erase_msg)
                    ek = oc.get("erased_skill")
                    if ek == "sakuya_stun": o_sakuya = True
                    elif ek == "marisa_spark": o_marisa = True
                    elif ek == "reimu_invul": o_reimu = True
                    elif ek == "reisen_mind": o_reisen_used = True
                    elif ek == "flandre_ripples": o_flandre = True
                    elif ek == "cirno_freeze": o_cirno_freeze_used = True
                    elif ek == "yukari_station": o_yukari_station = True
                    elif ek == "yukari_lastword": o_yukari_lastword = True
                if _t1["gif"] and not turn_image:
                    turn_image = _t1["gif"]
                turn_actions.extend(_t1["logs"])
            elif p_seiki_used_turn != r_cnt:
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

        if str(pc["cid"]).lower() == "t2":
            p_mahoraga_turns += 1
            heal_val = int(pc["hp"] * 0.05)
            pc["current_hp"] = min(pc["hp"], pc["current_hp"] + heal_val)
            adapt_pct = min(0.90, p_mahoraga_turns * 0.05)
            if random.random() < 0.30:
                curr_pc_power = int(curr_pc_power * 1.5)
                if not turn_image:
                    turn_image = T2_THOAI_MA_GIF
                msg_t2 = (
                    f"🔱 **[Nhóm T] [#t2] Mahoraga** ({user.display_name}) kích hoạt **The True Adapt** "
                    f"(Hồi +{heal_val:,} HP, Kháng ST {int(adapt_pct*100)}%) & vung **Thoái Ma Kiếm** (30%)! "
                    f"Sát thương ×1.5 giáng **{curr_pc_power:,} DMG** lên **{oc['name']}**!"
                )
            else:
                if not turn_image:
                    turn_image = T2_PASSIVE_GIF
                msg_t2 = (
                    f"🔱 **[Nhóm T] [#t2] Mahoraga** ({user.display_name}) kích hoạt **The True Adapt**! "
                    f"Hồi phục **+{heal_val:,} HP** ({pc['current_hp']:,}/{pc['hp']:,} HP) và tăng kháng sát thương lên **{int(adapt_pct*100)}%**!"
                )
            battle_logs.append(msg_t2)
            turn_actions.append(msg_t2)
        if str(pc["cid"]).lower() == "t3":
            _t3 = t3_combat_turn(p_t3_state, pc, r_cnt, oc["hp"], f"**{oc['name']}**", is_ace2=pc.get("is_ace2"))
            curr_pc_power = int(curr_pc_power * _t3["multiplier"]) + _t3["bonus_hp_dmg"]
            if _t3["gif"] and not turn_image:
                turn_image = _t3["gif"]
            turn_actions.extend(_t3["logs"])

        p_t4_save_invul = False
        if o_fate_lock_turns > 0:
            o_fate_lock_turns -= 1
            o_sakuya = o_reimu = o_marisa = o_flandre = o_reisen_used = o_cirno_freeze_used = True
            o_yukari_station = o_yukari_lastword = True
            oc["erased_skill"] = "fate_locked"
        if o_ice_spear_turns > 0:
            o_ice_spear_turns -= 1
            if random.random() < 0.40:
                stunned_oc = True
                turn_actions.append(f"❄️ **[Ice spear - #t4 Fateria]** **{oc['name']}** bị giáo băng cầm chân (40%), không thể tấn công trong lượt này!")

        if str(pc["cid"]).lower() == "t4":
            _t4 = t4_combat_turn(p_t4_state, pc, f"**{oc['name']}**", heal_mult=1.0, enemy_fate_loop_turns=o_fate_lock_turns)
            curr_pc_power = int(curr_pc_power * _t4["multiplier"])
            if _t4["save_loop_invul"]:
                p_t4_save_invul = True
            if _t4["fate_loop_triggered"]:
                o_fate_lock_turns = 2
                o_sakuya = o_reimu = o_marisa = o_flandre = o_reisen_used = o_cirno_freeze_used = True
                o_yukari_station = o_yukari_lastword = True
                oc["erased_skill"] = "fate_locked"
            if _t4["ice_spear_triggered"]:
                o_ice_spear_turns = 2
            if _t4["gif"] and not turn_image:
                turn_image = _t4["gif"]
            battle_logs.extend(_t4["logs"])
            turn_actions.extend(_t4["logs"])


        curr_oc_power = oc["power"]
        if oc["cid"] == 19 and oc.get("is_ace2") and not o_marisa:
            if random.random() < 0.30:
                o_marisa = True
                curr_oc_power = int(curr_oc_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_m = f"🌟 **Đối thủ [Ace 2] [#19] Marisa** tung ra **Master Spark** (30%)! Bộc phá ×2.0 sát thương gây **{curr_oc_power:,} DMG**!"
                battle_logs.append(msg_m)
                turn_actions.append(msg_m)

        # Kỹ năng Yukari Ace 2 của NPC Battle:
        if oc["cid"] == 4 and oc.get("is_ace2"):
            if not o_yukari_station and random.random() < 0.30:
                o_yukari_station = True
                curr_oc_power = int(curr_oc_power * 2.0)
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/7e/69/snvix5aVyjKgjesAJV.gif"
                msg_y = f"🌌 **Đối thủ [Ace 2] [#04] Yukari** tung **Trip To The Old Station** (30%)! Sát thương ×2.0 giáng **{curr_oc_power:,} DMG**!"
                battle_logs.append(msg_y)
                turn_actions.append(msg_y)
            elif not o_yukari_lastword and random.random() < 0.25:
                o_yukari_lastword = True
                curr_oc_power = int(curr_oc_power * 2.5)
                stunned_pc = True
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/03/4b/epgnCZ5A8KOdm.gif"
                msg_y = f"👁️ **Đối thủ [Ace 2] [#04] Yukari** kích hoạt **⸮⸮⸮ : Last Word !** (25%)! Bộc phá ×2.5 gây **{curr_oc_power:,} DMG** và **STUN bạn 1 lượt**!"
                battle_logs.append(msg_y)
                turn_actions.append(msg_y)

        # Kỹ năng Flandre Ace 2 của NPC Battle:
        if oc["cid"] == 9 and oc.get("is_ace2") and not o_flandre:
            if random.random() < 0.25:
                o_flandre = True
                rip_dmg = int(pc["current_hp"] * 0.50)
                pc["current_hp"] = max(0, pc["current_hp"] - rip_dmg)
                if not turn_image:
                    turn_image = EVOL_CONFIG[9]["skill_gif"]
                msg_f = f"🦇 **Đối thủ [Ace 2] [#09] Flandre** kích hoạt **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} HP (50% HP của {pc['name']})** ngay lập tức!"
                battle_logs.append(msg_f)
                turn_actions.append(msg_f)

        if oc["cid"] == 12 and oc.get("is_ace2") and oc.get("erased_skill") != "remilia_gungnir":
            o_gungnir_bonus = int(pc["hp"] * 0.03)
            curr_oc_power += o_gungnir_bonus
            if not turn_image:
                turn_image = EVOL_CONFIG[12]["skill_gif"]
            turn_actions.append(f"🩸 **Đối thủ [Ace 2] [#12] Remilia** - **Thương Đỏ Gungnir** (Thụ động): +**{o_gungnir_bonus:,} DMG** (3% Máu tối đa)!")

        if oc["cid"] == 21 and oc.get("is_ace2") and not o_reisen_used:
            if random.random() < 0.20:
                o_reisen_used = True
                p_mind_turns = 4
                if not turn_image:
                    turn_image = EVOL_CONFIG[21]["skill_gif"]
                msg_r = f"🔴 **Đối thủ [Ace 2] [#21] Reisen** kích hoạt **Red Eye Mind Explosion** (20%)! 🌀 **{pc['name']}** bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"
                battle_logs.append(msg_r)
                turn_actions.append(msg_r)

        if oc["cid"] == 23 and oc.get("is_ace2") and not o_cirno_freeze_used:
            if random.random() < 0.40:
                o_cirno_freeze_used = True
                p_freeze_debuff_turns = 2
                if not turn_image:
                    turn_image = EVOL_CONFIG[23]["skill_gif"]
                msg_c = f"❄️ **Đối thủ [Ace 2] [#23] Cirno** kích hoạt **Perfect Freeze** (40%)! Đóng băng bạn: Trong 2 turn tiếp theo có **45% không thể đánh trả**!"
                battle_logs.append(msg_c)
                turn_actions.append(msg_c)

        if oc["cid"] == 13 and oc.get("is_ace2") and oc.get("erased_skill") != "utsuho_nuclear":
            if random.random() < 0.30:
                curr_oc_power = int(curr_oc_power * 3.0)
                p_molten_ground_turns = 3
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_u = f"☢️ **Đối thủ [Ace 2] [#13] Utsuho Reiuji** bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{curr_oc_power:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa trong 3 turn)!"
                battle_logs.append(msg_u)
                turn_actions.append(msg_u)

        # [FIX WONDER GUARD KIZUNA ACE 2 - CHẶN & PHẢN HIỆU ỨNG NGAY LẬP TỨC]
        p_wg_active = (str(pc["cid"]).lower() == "t3" and pc.get("is_ace2") and p_t3_state.get("wonder_guard_turns", 0) > 0)
        if p_wg_active:
            if stunned_pc:
                stunned_pc = False
                stunned_oc = True
                msg_wg_stun = f"🛡️ **[Wonder Guard]** **{pc['name']}** miễn nhiễm STUN và **PHẢN NGƯỢC STUN** lại cho **{oc['name']}**!"
                battle_logs.append(msg_wg_stun)
                turn_actions.append(msg_wg_stun)
            if p_mind_turns > 0:
                o_mind_turns = max(o_mind_turns, p_mind_turns)
                p_mind_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{pc['name']}** phản ngược hiệu ứng **Red Eye Mind Explosion** sang **{oc['name']}**!")
            if p_freeze_debuff_turns > 0:
                o_freeze_debuff_turns = max(o_freeze_debuff_turns, p_freeze_debuff_turns)
                p_freeze_debuff_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{pc['name']}** phản ngược hiệu ứng **Perfect Freeze** sang **{oc['name']}**!")
            if p_molten_ground_turns > 0:
                o_molten_ground_turns = max(o_molten_ground_turns, p_molten_ground_turns)
                p_molten_ground_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{pc['name']}** phản ngược **Mặt Đất Nung Chảy** sang sân đối thủ!")

        if not stunned_pc:
            oc_invul = False
            if oc["cid"] == 15 and oc.get("is_ace2") and not o_reimu:
                if random.random() < 0.30:
                    o_reimu = True
                    oc_invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[15]["skill_gif"]
                    msg_skill = f"🛡️ **Đối thủ [Ace 2] [#15] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh** (30%)! MIỄN TOÀN BỘ THƯƠNG TỔN!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)

            if not oc_invul:
                oc["current_hp"] -= curr_pc_power
                turn_actions.append(f"⚔️ **{pc['name']}** tấn công gây **{curr_pc_power:,} DMG** lên **{oc['name']}**!")
            else:
                turn_actions.append(f"🛡️ **{oc['name']}** né tránh hoàn toàn đòn đánh của **{pc['name']}**!")
        else:
            turn_actions.append(f"❄️ **{pc['name']}** bị đóng băng nên không thể ra đòn!")

        if p_wg_active:
            p_t3_state["wonder_guard_turns"] -= 1

        if not stunned_oc:
            pc_invul = p_t4_save_invul
            if p_wg_active:
                pc_invul = True
                ref_dmg = int(curr_oc_power * 0.60)
                oc["current_hp"] = max(0, oc["current_hp"] - ref_dmg)
                if not turn_image:
                    turn_image = T3_WONDER_GUARD_GIF
                msg_wg_dmg = (
                    f"🛡️ **[Wonder Guard Duy Trì]** **{pc['name']}** MIỄN TOÀN BỘ **{curr_oc_power:,} DMG** từ **{oc['name']}** "
                    f"và **PHẢN LẠI {ref_dmg:,} DMG (60%)**! *(Còn {p_t3_state['wonder_guard_turns']} lượt)*"
                )
                battle_logs.append(msg_wg_dmg)
                turn_actions.append(msg_wg_dmg)
            if not pc_invul and pc["cid"] == 15 and pc["is_ace2"] and not p_reimu:
                if random.random() < 0.40:
                    p_reimu = True
                    pc_invul = True
                    if not turn_image:
                        turn_image = EVOL_CONFIG[15]["skill_gif"]
                    msg_skill = f"🛡️ **[Ace 2] [#15] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN TOÀN BỘ THƯƠNG TỔN!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)
            if not pc_invul and str(pc["cid"]).lower() == "t1" and not p_seiki_seal and p_seiki_used_turn != r_cnt:
                seal_chance = 0.50 if pc.get("is_ace2") else 0.40
                if random.random() < seal_chance:
                    p_seiki_seal = True
                    p_seiki_used_turn = r_cnt
                    pc_invul = True
                    if not turn_image:
                        turn_image = T1_SEAL_GIF
                    title_t1 = "[Ace 2] [#t1] Seiki" if pc.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                    pct_t1 = "50%" if pc.get("is_ace2") else "40%"
                    msg_skill = f"🛡️ **{title_t1}** ({user.display_name}) kích hoạt **Fantasy Seal** ({pct_t1})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                    battle_logs.append(msg_skill)
                    turn_actions.append(msg_skill)
            if not pc_invul:
                if str(pc["cid"]).lower() == "t2":
                    adapt_pct = min(0.90, p_mahoraga_turns * 0.05)
                    actual_dmg = int(curr_oc_power * (1.0 - adapt_pct))
                    pc["current_hp"] -= actual_dmg
                    turn_actions.append(f"⚔️ **{oc['name']}** phản công gây **{curr_oc_power:,} DMG** nhưng **Mahoraga** Thích Nghi (-{int(adapt_pct*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!")
                else:
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

    p_mult = get_prestige_xp_multiplier(player.get("prestige", 0))
    gained_xp = int(gained_xp * p_mult)

    old_lvl = player["level"]
    player["last_battle_time"] = now
    player["xp"] += gained_xp
    player["battles_total"] = player.get("battles_total", 0) + 1
    if win: player["battles_won"] = player.get("battles_won", 0) + 1

    st = player.setdefault("story", {})
    if st.get("current_stage", 0) == 0:
        st["battles_done"] = st.get("battles_done", 0) + 1
    elif st.get("current_stage", 0) == 2 and st.get("stage2_quiz_passed", False) and not st.get("stage2_quest_claimed", False):
        st["stage2_battles_done"] = st.get("stage2_battles_done", 0) + 1

    dq_notifs = update_daily_quest_progress(player, "battle", 1)
    ev_notifs = update_event_quest_progress(player, "battle", 1)

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
    cur_lvl, xp_in_lvl, needed_xp, _ = get_level_progress(player["xp"], player.get("prestige", 0))
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
    c_reisen_used = False
    t_reisen_used = False
    c_mind_turns = 0
    t_mind_turns = 0
    c_t1 = {"seal_used": False, "bong_used": False, "med_used": False, "used_turn": -1}
    t_t1 = {"seal_used": False, "bong_used": False, "med_used": False, "used_turn": -1}
    c_mahoraga_turns = 0
    t_mahoraga_turns = 0
    c_t3_state = {}
    t_t3_state = {}
    c_t4_state = {}
    t_t4_state = {}
    c_fate_locked_turns = 0
    t_fate_locked_turns = 0
    c_ice_spear_turns = 0
    t_ice_spear_turns = 0
    c_heal_mult = 1.0
    t_heal_mult = 1.0
    c_cirno_freeze_used = False
    t_cirno_freeze_used = False
    c_freeze_debuff_turns = 0
    t_freeze_debuff_turns = 0
    c_molten_ground_turns = 0
    t_molten_ground_turns = 0
    c_seiki_seal, c_seiki_spark, c_seiki_heal = False, False, False
    c_seiki_used_turn = -1
    t_seiki_seal, t_seiki_spark, t_seiki_heal = False, False, False
    t_seiki_used_turn = -1
    pvp_turns = []
    pvp_logs = []
    p_yukari_station, p_yukari_lastword = False, False
    o_yukari_station, o_yukari_lastword = False, False

    while c_idx < len(c_cards) and t_idx < len(t_cards) and r_cnt < 30:
        r_cnt += 1
        cc = c_cards[c_idx]
        tc = t_cards[t_idx]
        turn_image = None
        turn_actions = []
        turn_trades = []
        c_skills_locked = False
        t_skills_locked = False
        if c_fate_locked_turns > 0:
            c_skills_locked = True
            c_fate_locked_turns -= 1
            turn_actions.append(f"⛓️ **[Fate loop]** **{cc['name']}** ({challenger.display_name}) đang bị khóa kỹ năng! (Còn {c_fate_locked_turns} lượt)")
        if t_fate_locked_turns > 0:
            t_skills_locked = True
            t_fate_locked_turns -= 1
            turn_actions.append(f"⛓️ **[Fate loop]** **{tc['name']}** ({target.display_name}) đang bị khóa kỹ năng! (Còn {t_fate_locked_turns} lượt)")

        if t_mind_turns > 0:
            t_mind_turns -= 1
            if random.random() < 0.20:
                _mc_dmg = tc["power"]
                tc["current_hp"] = max(0, tc["current_hp"] - _mc_dmg)
                msg_mc = f"🌀 **[Red Eye Mind Explosion]** **{tc['name']}** ({target.display_name}) mất kiểm soát và **tự gây {_mc_dmg:,} DMG** lên bản thân! (Còn {t_mind_turns} lượt ảo giác)"
                pvp_logs.append(msg_mc)
                turn_actions.append(msg_mc)

        if c_mind_turns > 0:
            c_mind_turns -= 1
            if random.random() < 0.20:
                _mc_dmg = cc["power"]
                cc["current_hp"] = max(0, cc["current_hp"] - _mc_dmg)
                msg_mc = f"🌀 **[Red Eye Mind Explosion]** **{cc['name']}** ({challenger.display_name}) mất kiểm soát và **tự gây {_mc_dmg:,} DMG** lên bản thân! (Còn {c_mind_turns} lượt ảo giác)"
                pvp_logs.append(msg_mc)
                turn_actions.append(msg_mc)

        if t_molten_ground_turns > 0:
            t_molten_ground_turns -= 1
            burn_dmg = int(tc["max_hp"] * 0.02)
            tc["current_hp"] = max(0, tc["current_hp"] - burn_dmg)
            msg_b = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham thiêu đốt **{tc['name']}** ({target.display_name}) gây **{burn_dmg:,} DMG** (2% Máu Tối Đa)! (Còn {t_molten_ground_turns} turn)"
            pvp_logs.append(msg_b)
            turn_actions.append(msg_b)

        if c_molten_ground_turns > 0:
            c_molten_ground_turns -= 1
            burn_dmg = int(cc["max_hp"] * 0.02)
            cc["current_hp"] = max(0, cc["current_hp"] - burn_dmg)
            msg_b = f"🌋 **[Mặt Đất Nung Chảy]** Dung nham thiêu đốt **{cc['name']}** ({challenger.display_name}) gây **{burn_dmg:,} DMG** (2% Máu Tối Đa)! (Còn {c_molten_ground_turns} turn)"
            pvp_logs.append(msg_b)
            turn_actions.append(msg_b)

        c_stunned = False
        t_stunned = False

        if t_freeze_debuff_turns > 0:
            t_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                t_stunned = True
                msg_fz = f"❄️ **[Perfect Freeze]** **{tc['name']}** ({target.display_name}) bị đóng băng cứng đờ (45%), không thể ra đòn trong hiệp này! (Còn {t_freeze_debuff_turns} turn duy trì)"
                pvp_logs.append(msg_fz)
                turn_actions.append(msg_fz)

        if c_freeze_debuff_turns > 0:
            c_freeze_debuff_turns -= 1
            if random.random() < 0.45:
                c_stunned = True
                msg_fz = f"❄️ **[Perfect Freeze]** **{cc['name']}** ({challenger.display_name}) bị đóng băng cứng đờ (45%), không thể ra đòn trong hiệp này! (Còn {c_freeze_debuff_turns} turn duy trì)"
                pvp_logs.append(msg_fz)
                turn_actions.append(msg_fz)

        if cc["cid"] == 18 and cc["is_ace2"] and not c_sakuya:
            if random.random() < 0.40:
                c_sakuya = True
                t_stunned = True
                turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#18] Sakuya** ({challenger.display_name}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ {tc['name']} bị STUN!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if tc["cid"] == 18 and tc["is_ace2"] and not t_sakuya:
            if random.random() < 0.40:
                t_sakuya = True
                c_stunned = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_skill = f"⏳ **[Ace 2] [#18] Sakuya** ({target.display_name}) kích hoạt **Thời Gian Đóng Băng** (40%)! ❄️ {cc['name']} bị STUN!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        c_invul = False
        t_invul = False
        if cc["cid"] == 15 and cc["is_ace2"] and not c_reimu:
            if random.random() < 0.40:
                c_reimu = True
                c_invul = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[15]["skill_gif"]
                msg_skill = f"🛡️ **[Ace 2] [#15] Reimu** ({challenger.display_name}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if not c_invul and str(cc["cid"]).lower() == "t1" and not c_seiki_seal and c_seiki_used_turn != r_cnt:
            seal_chance = 0.50 if cc.get("is_ace2") else 0.40
            if random.random() < seal_chance:
                c_seiki_seal = True
                c_seiki_used_turn = r_cnt
                c_invul = True
                if not turn_image:
                    turn_image = T1_SEAL_GIF
                title_seiki = "[Ace 2] [#t1] Seiki" if cc.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                pct_seiki = "50%" if cc.get("is_ace2") else "40%"
                msg_skill = f"🛡️ **{title_seiki}** ({challenger.display_name}) kích hoạt **Fantasy Seal** ({pct_seiki})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if tc["cid"] == 15 and tc["is_ace2"] and not t_reimu:
            if random.random() < 0.40:
                t_reimu = True
                t_invul = True
                if not turn_image:
                    turn_image = EVOL_CONFIG[15]["skill_gif"]
                msg_skill = f"🛡️ **[Ace 2] [#15] Reimu** ({target.display_name}) kích hoạt **Vô Tưởng Chuyển Sinh** (40%)! MIỄN THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        if not t_invul and str(tc["cid"]).lower() == "t1" and not t_seiki_seal and t_seiki_used_turn != r_cnt:
            seal_chance = 0.50 if tc.get("is_ace2") else 0.40
            if random.random() < seal_chance:
                t_seiki_seal = True
                t_seiki_used_turn = r_cnt
                t_invul = True
                if not turn_image:
                    turn_image = T1_SEAL_GIF
                title_seiki = "[Ace 2] [#t1] Seiki" if tc.get("is_ace2") else "[Nhóm T] [#t1] Seiki"
                pct_seiki = "50%" if tc.get("is_ace2") else "40%"
                msg_skill = f"🛡️ **{title_seiki}** ({target.display_name}) kích hoạt **Fantasy Seal** ({pct_seiki})! MIỄN TOÀN BỘ SÁT THƯƠNG!"
                pvp_logs.append(msg_skill)
                turn_actions.append(msg_skill)

        c_curr_power = cc["power"]
        t_curr_power = tc["power"]
        if cc["cid"] == 19 and cc["is_ace2"] and not c_marisa:
            if random.random() < 0.30:
                c_marisa = True
                c_curr_power = int(c_curr_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_m = f"🌟 **[Ace 2] [#19] Marisa** ({challenger.display_name}) tung ra **Master Spark** (30%)! Oanh tạc ×2.0 sát thương ({c_curr_power:,} DMG)!"
                pvp_logs.append(msg_m)
                turn_actions.append(msg_m)
# Kỹ năng Yukari Ace 2 bên Thách đấu:
        if cc["cid"] == 4 and cc["is_ace2"]:
            if cc.get("erased_skill") != "yukari_station" and not p_yukari_station and random.random() < 0.30:
                p_yukari_station = True
                c_curr_power = int(c_curr_power * 2.0)
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/7e/69/snvix5aVyjKgjesAJV.gif"
                msg_y = f"🌌 **[Ace 2] [#04] Yukari** ({challenger.display_name}) tung **Trip To The Old Station** (30%)! Sát thương ×2.0 giáng **{c_curr_power:,} DMG**!"
                pvp_logs.append(msg_y)
                turn_actions.append(msg_y)
            elif cc.get("erased_skill") != "yukari_lastword" and not p_yukari_lastword and random.random() < 0.25:
                p_yukari_lastword = True
                c_curr_power = int(c_curr_power * 2.5)
                t_stunned = True
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/03/4b/epgnCZ5A8KOdm.gif"
                msg_y = f"👁️ **[Ace 2] [#04] Yukari** ({challenger.display_name}) kích hoạt **⸮⸮⸮ : Last Word !** (25%)! Bộc phá ×2.5 gây **{c_curr_power:,} DMG** và **STUN đối thủ**!"
                pvp_logs.append(msg_y)
                turn_actions.append(msg_y)

        if cc["cid"] == 12 and cc["is_ace2"] and cc.get("erased_skill") != "remilia_gungnir":
            _gungnir = int(tc["max_hp"] * 0.03)
            c_curr_power += _gungnir
            if not turn_image:
                turn_image = EVOL_CONFIG[12]["skill_gif"]
            turn_actions.append(f"🩸 **[Ace 2] [#12] Remilia** ({challenger.display_name}) - **Thương Đỏ Gungnir** (Thụ động): +**{_gungnir:,} DMG** (3% Máu tối đa đối thủ)!")

        if cc["cid"] == 21 and cc["is_ace2"] and not c_reisen_used:
            if random.random() < 0.25:
                c_reisen_used = True
                t_mind_turns = 4
                if not turn_image:
                    turn_image = EVOL_CONFIG[21]["skill_gif"]
                msg_r = f"🔴 **[Ace 2] [#21] Reisen** ({challenger.display_name}) kích hoạt **Red Eye Mind Explosion** (25%)! 🌀 **{tc['name']}** bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"
                pvp_logs.append(msg_r)
                turn_actions.append(msg_r)

        if cc["cid"] == 23 and cc["is_ace2"] and not c_cirno_freeze_used:
            if random.random() < 0.40:
                c_cirno_freeze_used = True
                t_freeze_debuff_turns = 2
                if not turn_image:
                    turn_image = EVOL_CONFIG[23]["skill_gif"]
                msg_c = f"❄️ **[Ace 2] [#23] Cirno** ({challenger.display_name}) kích hoạt **Perfect Freeze** (40%)! Đóng băng đối thủ: Trong 2 turn tiếp theo có **45% không thể đánh trả**!"
                pvp_logs.append(msg_c)
                turn_actions.append(msg_c)

        if cc["cid"] == 13 and cc["is_ace2"] and cc.get("erased_skill") != "utsuho_nuclear":
            if random.random() < 0.30:
                c_curr_power = int(c_curr_power * 3.0)
                t_molten_ground_turns = 3
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_u = f"☢️ **[Ace 2] [#13] Utsuho Reiuji** ({challenger.display_name}) bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{c_curr_power:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa cho bài địch trong 3 turn)!"
                pvp_logs.append(msg_u)
                turn_actions.append(msg_u)

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

        if str(cc["cid"]).lower() == "t1":
            if cc.get("is_ace2"):
                _t1 = t1_ace2_attack(c_t1, cc, r_cnt, tc["max_hp"], f"**{tc['name']}** ({target.display_name})", is_boss=False)
                if _t1.get("multiplier", 1.0) > 1.0:
                    c_curr_power = int(c_curr_power * _t1["multiplier"])
                c_curr_power += _t1["bonus"]
                if _t1["direct"]:
                    tc["current_hp"] = max(0, tc["current_hp"] - _t1["direct"])
                if _t1.get("invul"):
                    c_invul = True
                    c_seiki_seal = True
                    c_seiki_used_turn = r_cnt
                if _t1["heal"]:
                    cc["current_hp"] = min(cc["max_hp"], cc["current_hp"] + _t1["heal"])
                if _t1["disable"]:
                    erase_msg = apply_bong_khai_niem_card(tc)
                    _t1["logs"].append(erase_msg)
                    ek = tc.get("erased_skill")
                    if ek == "sakuya_stun": t_sakuya = True
                    elif ek == "marisa_spark": t_marisa = True
                    elif ek == "reimu_invul": t_reimu = True
                    elif ek == "reisen_mind": t_reisen_used = True
                    elif ek == "flandre_ripples": t_flandre = True
                    elif ek == "cirno_freeze": t_cirno_freeze_used = True
                    elif ek == "yukari_station": o_yukari_station = True
                    elif ek == "yukari_lastword": o_yukari_lastword = True
                    elif ek == "t1_seal": t_seiki_seal = True; t_t1["seal_used"] = True
                    elif ek == "t1_spark": t_seiki_spark = True
                    elif ek == "t1_med": t_seiki_heal = True; t_t1["med_used"] = True
                    elif ek == "t1_bong": t_t1["bong_used"] = True
                    elif ek == "t3_wonder": t_t3_state["wonder_guard_used"] = True; t_t3_state["wonder_guard_turns"] = 0
                    elif ek == "t3_blood": t_t3_state["blood_used"] = True
                    elif ek == "t3_dark": t_t3_state["dark_chain_uses"] = 99
                    elif ek == "t4_save_loop": t_invul = False
                    elif ek == "t4_fate_loop": t_t4_state["fate_uses"] = 99
                    elif ek == "t4_clone_attack": t_t4_state["clone_uses"] = 99
                if _t1["gif"] and not turn_image:
                    turn_image = _t1["gif"]
                turn_actions.extend(_t1["logs"])
            elif c_seiki_used_turn != r_cnt:
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

        if str(cc["cid"]).lower() == "t2":
            erased_c = cc.get("erased_skill")
            heal_val = 0
            adapt_pct = 0.0
            if erased_c != "t2_adapt":
                c_mahoraga_turns += 1
                heal_val = int(cc["max_hp"] * 0.05)
                cc["current_hp"] = min(cc["max_hp"], cc["current_hp"] + heal_val)
                adapt_pct = min(0.90, c_mahoraga_turns * 0.05)
            if erased_c != "t2_kiem" and random.random() < 0.30:
                c_curr_power = int(c_curr_power * 1.5)
                if not turn_image:
                    turn_image = T2_THOAI_MA_GIF
                msg_t2 = (
                    f"🔱 **[Nhóm T] [#t2] Mahoraga** ({challenger.display_name}) vung **Thoái Ma Kiếm** (30%)! "
                    f"Sát thương ×1.5 giáng **{c_curr_power:,} DMG** lên **{tc['name']}**!"
                )
                pvp_logs.append(msg_t2)
                turn_actions.append(msg_t2)
            elif erased_c != "t2_adapt":
                if not turn_image:
                    turn_image = T2_PASSIVE_GIF
                msg_t2 = (
                    f"🔱 **[Nhóm T] [#t2] Mahoraga** ({challenger.display_name}) kích hoạt **The True Adapt**! "
                    f"Hồi phục **+{heal_val:,} HP** ({cc['current_hp']:,}/{cc['max_hp']:,} HP) và tăng kháng sát thương lên **{int(adapt_pct*100)}%**!"
                )
                pvp_logs.append(msg_t2)
                turn_actions.append(msg_t2)

        
        if str(cc["cid"]).lower() == "t3" and not c_skills_locked:
            _t3 = t3_combat_turn(c_t3_state, cc, r_cnt, tc["max_hp"], f"**{tc['name']}** ({target.display_name})", is_ace2=cc.get("is_ace2"))
            c_curr_power = int(c_curr_power * _t3["multiplier"]) + _t3["bonus_hp_dmg"]
            if _t3["gif"] and not turn_image:
                turn_image = _t3["gif"]
            turn_actions.extend(_t3["logs"])

        if str(cc["cid"]).lower() == "t4" and not c_skills_locked:
            _t4 = t4_combat_turn(c_t4_state, cc, f"**{tc['name']}** ({target.display_name})", heal_mult=c_heal_mult, enemy_fate_loop_turns=t_fate_locked_turns)
            c_curr_power = int(c_curr_power * _t4["multiplier"])
            if _t4["save_loop_invul"]:
                c_invul = True
            if _t4["fate_loop_triggered"]:
                t_fate_locked_turns = 2
                t_skills_locked = True
                t_invul = False
                t_stunned = False
            if _t4["heal_reduce_triggered"]:
                t_heal_mult = 0.70
            if _t4["ice_spear_triggered"]:
                t_ice_spear_turns = 2
            if _t4["gif"] and not turn_image:
                turn_image = _t4["gif"]
            pvp_logs.extend(_t4["logs"])
            turn_actions.extend(_t4["logs"])

        if tc["cid"] == 19 and tc["is_ace2"] and not t_marisa:
            if random.random() < 0.30:
                t_marisa = True
                t_curr_power = int(t_curr_power * 2.0)
                if not turn_image:
                    turn_image = EVOL_CONFIG[19]["skill_gif"]
                msg_m = f"🌟 **[Ace 2] [#19] Marisa** ({target.display_name}) tung ra **Master Spark** (30%)! Oanh tạc ×2.0 sát thương ({t_curr_power:,} DMG)!"
                pvp_logs.append(msg_m)
                turn_actions.append(msg_m)
# Kỹ năng Yukari Ace 2 bên Nhận thách đấu:
        if tc["cid"] == 4 and tc["is_ace2"]:
            if tc.get("erased_skill") != "yukari_station" and not o_yukari_station and random.random() < 0.30:
                o_yukari_station = True
                t_curr_power = int(t_curr_power * 2.0)
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/4493325008d34b7bf8cd6813cd5c1619/7e/69/snvix5aVyjKgjesAJV.gif"
                msg_y = f"🌌 **[Ace 2] [#04] Yukari** ({target.display_name}) tung **Trip To The Old Station** (30%)! Sát thương ×2.0 giáng **{t_curr_power:,} DMG**!"
                pvp_logs.append(msg_y)
                turn_actions.append(msg_y)
            elif tc.get("erased_skill") != "yukari_lastword" and not o_yukari_lastword and random.random() < 0.25:
                o_yukari_lastword = True
                t_curr_power = int(t_curr_power * 2.5)
                c_stunned = True
                if not turn_image:
                    turn_image = "https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/03/4b/epgnCZ5A8KOdm.gif"
                msg_y = f"👁️ **[Ace 2] [#04] Yukari** ({target.display_name}) kích hoạt **⸮⸮⸮ : Last Word !** (25%)! Bộc phá ×2.5 gây **{t_curr_power:,} DMG** và **STUN đối thủ**!"
                pvp_logs.append(msg_y)
                turn_actions.append(msg_y)

        if tc["cid"] == 12 and tc["is_ace2"] and tc.get("erased_skill") != "remilia_gungnir":
            _gungnir = int(cc["max_hp"] * 0.03)
            t_curr_power += _gungnir
            if not turn_image:
                turn_image = EVOL_CONFIG[12]["skill_gif"]
            turn_actions.append(f"🩸 **[Ace 2] [#12] Remilia** ({target.display_name}) - **Thương Đỏ Gungnir** (Thụ động): +**{_gungnir:,} DMG** (3% Máu tối đa đối thủ)!")

        if tc["cid"] == 21 and tc["is_ace2"] and not t_reisen_used:
            if random.random() < 0.25:
                t_reisen_used = True
                c_mind_turns = 4
                if not turn_image:
                    turn_image = EVOL_CONFIG[21]["skill_gif"]
                msg_r = f"🔴 **[Ace 2] [#21] Reisen** ({target.display_name}) kích hoạt **Red Eye Mind Explosion** (25%)! 🌀 **{cc['name']}** bị điều khiển tâm trí: **20% tự gây sát thương** trong **4 lượt**!"
                pvp_logs.append(msg_r)
                turn_actions.append(msg_r)

        if tc["cid"] == 23 and tc["is_ace2"] and not t_cirno_freeze_used:
            if random.random() < 0.40:
                t_cirno_freeze_used = True
                c_freeze_debuff_turns = 2
                if not turn_image:
                    turn_image = EVOL_CONFIG[23]["skill_gif"]
                msg_c = f"❄️ **[Ace 2] [#23] Cirno** ({target.display_name}) kích hoạt **Perfect Freeze** (40%)! Đóng băng đối thủ: Trong 2 turn tiếp theo có **45% không thể đánh trả**!"
                pvp_logs.append(msg_c)
                turn_actions.append(msg_c)

        if tc["cid"] == 13 and tc["is_ace2"] and tc.get("erased_skill") != "utsuho_nuclear":
            if random.random() < 0.30:
                t_curr_power = int(t_curr_power * 3.0)
                c_molten_ground_turns = 3
                if not turn_image:
                    turn_image = EVOL_CONFIG[13]["skill_gif"]
                msg_u = f"☢️ **[Ace 2] [#13] Utsuho Reiuji** ({target.display_name}) bộc phát **Nuclear Spell Card** (30%)! Sát thương nhiệt hạch ×3.0 giáng **{t_curr_power:,} DMG** và nung chảy mặt đất (gây bỏng 2% Máu Tối Đa cho bài địch trong 3 turn)!"
                pvp_logs.append(msg_u)
                turn_actions.append(msg_u)

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

        if str(tc["cid"]).lower() == "t1":
            if tc.get("is_ace2"):
                _t1 = t1_ace2_attack(t_t1, tc, r_cnt, cc["max_hp"], f"**{cc['name']}** ({challenger.display_name})", is_boss=False)
                if _t1.get("multiplier", 1.0) > 1.0:
                    t_curr_power = int(t_curr_power * _t1["multiplier"])
                t_curr_power += _t1["bonus"]
                if _t1["direct"]:
                    cc["current_hp"] = max(0, cc["current_hp"] - _t1["direct"])
                if _t1.get("invul"):
                    t_invul = True
                    t_seiki_seal = True
                    t_seiki_used_turn = r_cnt
                if _t1["heal"]:
                    tc["current_hp"] = min(tc["max_hp"], tc["current_hp"] + _t1["heal"])
                if _t1["disable"]:
                    erase_msg = apply_bong_khai_niem_card(cc)
                    _t1["logs"].append(erase_msg)
                    ek = cc.get("erased_skill")
                    if ek == "sakuya_stun": c_sakuya = True
                    elif ek == "marisa_spark": c_marisa = True
                    elif ek == "reimu_invul": c_reimu = True
                    elif ek == "reisen_mind": c_reisen_used = True
                    elif ek == "flandre_ripples": c_flandre = True
                    elif ek == "cirno_freeze": c_cirno_freeze_used = True
                    elif ek == "yukari_station": p_yukari_station = True
                    elif ek == "yukari_lastword": p_yukari_lastword = True
                    elif ek == "t1_seal": c_seiki_seal = True; c_t1["seal_used"] = True
                    elif ek == "t1_spark": c_seiki_spark = True
                    elif ek == "t1_med": c_seiki_heal = True; c_t1["med_used"] = True
                    elif ek == "t1_bong": c_t1["bong_used"] = True
                    elif ek == "t3_wonder": c_t3_state["wonder_guard_used"] = True; c_t3_state["wonder_guard_turns"] = 0
                    elif ek == "t3_blood": c_t3_state["blood_used"] = True
                    elif ek == "t3_dark": c_t3_state["dark_chain_uses"] = 99
                    elif ek == "t4_save_loop": c_invul = False
                    elif ek == "t4_fate_loop": c_t4_state["fate_uses"] = 99
                    elif ek == "t4_clone_attack": c_t4_state["clone_uses"] = 99
                if _t1["gif"] and not turn_image:
                    turn_image = _t1["gif"]
                turn_actions.extend(_t1["logs"])
            elif t_seiki_used_turn != r_cnt:
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

        if str(tc["cid"]).lower() == "t2":
            erased_t = tc.get("erased_skill")
            heal_val = 0
            adapt_pct = 0.0
            if erased_t != "t2_adapt":
                t_mahoraga_turns += 1
                heal_val = int(tc["max_hp"] * 0.05)
                tc["current_hp"] = min(tc["max_hp"], tc["current_hp"] + heal_val)
                adapt_pct = min(0.90, t_mahoraga_turns * 0.05)
            if erased_t != "t2_kiem" and random.random() < 0.30:
                t_curr_power = int(t_curr_power * 1.5)
                if not turn_image:
                    turn_image = T2_THOAI_MA_GIF
                msg_t2 = (
                    f"🔱 **[Nhóm T] [#t2] Mahoraga** ({target.display_name}) vung **Thoái Ma Kiếm** (30%)! "
                    f"Sát thương ×1.5 giáng **{t_curr_power:,} DMG** lên **{cc['name']}**!"
                )
                pvp_logs.append(msg_t2)
                turn_actions.append(msg_t2)
            elif erased_t != "t2_adapt":
                if not turn_image:
                    turn_image = T2_PASSIVE_GIF
                msg_t2 = (
                    f"🔱 **[Nhóm T] [#t2] Mahoraga** ({target.display_name}) kích hoạt **The True Adapt**! "
                    f"Hồi phục **+{heal_val:,} HP** ({tc['current_hp']:,}/{tc['max_hp']:,} HP) và tăng kháng sát thương lên **{int(adapt_pct*100)}%**!"
                )
                pvp_logs.append(msg_t2)
                turn_actions.append(msg_t2)

        
        if str(tc["cid"]).lower() == "t3" and not t_skills_locked:
            _t3 = t3_combat_turn(t_t3_state, tc, r_cnt, cc["max_hp"], f"**{cc['name']}** ({challenger.display_name})", is_ace2=tc.get("is_ace2"))
            t_curr_power = int(t_curr_power * _t3["multiplier"]) + _t3["bonus_hp_dmg"]
            if _t3["gif"] and not turn_image:
                turn_image = _t3["gif"]
            turn_actions.extend(_t3["logs"])

        if str(tc["cid"]).lower() == "t4" and not t_skills_locked:
            _t4 = t4_combat_turn(t_t4_state, tc, f"**{cc['name']}** ({challenger.display_name})", heal_mult=t_heal_mult, enemy_fate_loop_turns=c_fate_locked_turns)
            t_curr_power = int(t_curr_power * _t4["multiplier"])
            if _t4["save_loop_invul"]:
                t_invul = True
            if _t4["fate_loop_triggered"]:
                c_fate_locked_turns = 2
                c_skills_locked = True
                c_invul = False
                c_stunned = False
            if _t4["heal_reduce_triggered"]:
                c_heal_mult = 0.70
            if _t4["ice_spear_triggered"]:
                c_ice_spear_turns = 2
            if _t4["gif"] and not turn_image:
                turn_image = _t4["gif"]
            pvp_logs.extend(_t4["logs"])
            turn_actions.extend(_t4["logs"])

        if c_ice_spear_turns > 0:
            c_ice_spear_turns -= 1
            if not c_stunned and random.random() < 0.40:
                c_stunned = True
                turn_actions.append(f"❄️ **[Ice spear]** **{cc['name']}** ({challenger.display_name}) bị giáo băng cầm chân (40%), không thể tấn công lượt này!")
        if t_ice_spear_turns > 0:
            t_ice_spear_turns -= 1
            if not t_stunned and random.random() < 0.40:
                t_stunned = True
                turn_actions.append(f"❄️ **[Ice spear]** **{tc['name']}** ({target.display_name}) bị giáo băng cầm chân (40%), không thể tấn công lượt này!")

        # [FIX WONDER GUARD KIZUNA ACE 2 TRONG PVP 3V3]
        c_wg_active = (str(cc["cid"]).lower() == "t3" and cc.get("is_ace2") and c_t3_state.get("wonder_guard_turns", 0) > 0)
        t_wg_active = (str(tc["cid"]).lower() == "t3" and tc.get("is_ace2") and t_t3_state.get("wonder_guard_turns", 0) > 0)

        if c_wg_active:
            c_t3_state["wonder_guard_turns"] -= 1
            c_invul = True
            if c_stunned:
                c_stunned = False
                t_stunned = True
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{cc['name']}** ({challenger.display_name}) miễn nhiễm STUN & **PHẢN NGƯỢC STUN** sang **{tc['name']}**!")
            if c_mind_turns > 0:
                t_mind_turns = max(t_mind_turns, c_mind_turns)
                c_mind_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{cc['name']}** phản ngược **Red Eye Mind** sang **{tc['name']}**!")
            if c_freeze_debuff_turns > 0:
                t_freeze_debuff_turns = max(t_freeze_debuff_turns, c_freeze_debuff_turns)
                c_freeze_debuff_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{cc['name']}** phản ngược **Perfect Freeze** sang **{tc['name']}**!")
            if c_molten_ground_turns > 0:
                t_molten_ground_turns = max(t_molten_ground_turns, c_molten_ground_turns)
                c_molten_ground_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{cc['name']}** phản ngược **Mặt Đất Nung Chảy** sang đối phương!")

        if t_wg_active:
            t_t3_state["wonder_guard_turns"] -= 1
            t_invul = True
            if t_stunned:
                t_stunned = False
                c_stunned = True
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{tc['name']}** ({target.display_name}) miễn nhiễm STUN & **PHẢN NGƯỢC STUN** sang **{cc['name']}**!")
            if t_mind_turns > 0:
                c_mind_turns = max(c_mind_turns, t_mind_turns)
                t_mind_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{tc['name']}** phản ngược **Red Eye Mind** sang **{cc['name']}**!")
            if t_freeze_debuff_turns > 0:
                c_freeze_debuff_turns = max(c_freeze_debuff_turns, t_freeze_debuff_turns)
                t_freeze_debuff_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{tc['name']}** phản ngược **Perfect Freeze** sang **{cc['name']}**!")
            if t_molten_ground_turns > 0:
                c_molten_ground_turns = max(c_molten_ground_turns, t_molten_ground_turns)
                t_molten_ground_turns = 0
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{tc['name']}** phản ngược **Mặt Đất Nung Chảy** sang đối phương!")

        if not c_stunned and not t_invul:
            if tc["cid"] == 4 and tc.get("is_ace2") and tc.get("erased_skill") != "yukari_gap" and c_curr_power == cc["power"] and random.random() < 0.10:
                cc["current_hp"] = max(0, cc["current_hp"] - c_curr_power)
                turn_actions.append(f"🌀 **[Ace 2] [#04] Yukari** ({target.display_name}) kích hoạt **Invisible Gap (10%)**! Miễn thương và phản lại 100% đòn đánh thường (**{c_curr_power:,} DMG**) vào **{cc['name']}**!")
            elif str(tc["cid"]).lower() == "t2" and tc.get("erased_skill") != "t2_adapt":
                t_adapt = min(0.90, t_mahoraga_turns * 0.05)
                actual_dmg = int(c_curr_power * (1.0 - t_adapt))
                tc["current_hp"] -= actual_dmg
                turn_actions.append(f"⚔️ **{cc['name']}** giáng **{c_curr_power:,} DMG** nhưng **{tc['name']}** Thích Nghi (-{int(t_adapt*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!")
            else:
                tc["current_hp"] -= c_curr_power
                turn_actions.append(f"⚔️ **{cc['name']}** giáng **{c_curr_power:,} DMG** lên **{tc['name']}**!")
        elif c_stunned:
            turn_actions.append(f"❄️ **{cc['name']}** bị đóng băng không thể tấn công!")
        elif t_invul:
            if t_wg_active and not c_stunned:
                ref_dmg = int(c_curr_power * 0.60)
                cc["current_hp"] = max(0, cc["current_hp"] - ref_dmg)
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{tc['name']}** miễn thương hoàn toàn & **PHẢN LẠI {ref_dmg:,} DMG (60%)** vào **{cc['name']}**! *(Còn {t_t3_state['wonder_guard_turns']} lượt)*")
            else:
                turn_actions.append(f"🛡️ **{tc['name']}** miễn nhiễm toàn bộ đòn đánh!")

        if not t_stunned and not c_invul:
            if cc["cid"] == 4 and cc.get("is_ace2") and cc.get("erased_skill") != "yukari_gap" and t_curr_power == tc["power"] and random.random() < 0.10:
                tc["current_hp"] = max(0, tc["current_hp"] - t_curr_power)
                turn_actions.append(f"🌀 **[Ace 2] [#04] Yukari** ({challenger.display_name}) kích hoạt **Invisible Gap (10%)**! Miễn thương và phản lại 100% đòn đánh thường (**{t_curr_power:,} DMG**) vào **{tc['name']}**!")
            elif str(cc["cid"]).lower() == "t2" and cc.get("erased_skill") != "t2_adapt":
                c_adapt = min(0.90, c_mahoraga_turns * 0.05)
                actual_dmg = int(t_curr_power * (1.0 - c_adapt))
                cc["current_hp"] -= actual_dmg
                turn_actions.append(f"⚔️ **{tc['name']}** giáng **{t_curr_power:,} DMG** nhưng **{cc['name']}** Thích Nghi (-{int(c_adapt*100)}% ST), chỉ nhận **{actual_dmg:,} DMG**!")
            else:
                cc["current_hp"] -= t_curr_power
                turn_actions.append(f"⚔️ **{tc['name']}** giáng **{t_curr_power:,} DMG** lên **{cc['name']}**!")
        elif t_stunned:
            turn_actions.append(f"❄️ **{tc['name']}** bị đóng băng không thể tấn công!")
        elif c_invul:
            if c_wg_active and not t_stunned:
                ref_dmg = int(t_curr_power * 0.60)
                tc["current_hp"] = max(0, tc["current_hp"] - ref_dmg)
                turn_actions.append(f"🛡️ **[Wonder Guard]** **{cc['name']}** miễn thương hoàn toàn & **PHẢN LẠI {ref_dmg:,} DMG (60%)** vào **{tc['name']}**! *(Còn {c_t3_state['wonder_guard_turns']} lượt)*")
            else:
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
    ev_c = update_event_quest_progress(c_player, "pvp", 1)
    ev_t = update_event_quest_progress(t_player, "pvp", 1)
    save_player(c_player)
    save_player(t_player)

    embed = discord.Embed(
        title=f"⚔️ KẾT QUẢ ĐẠI CHIẾN PVP ({r_cnt} HIỆP): {challenger.display_name} VS {target.display_name}",
        description=result_desc,
        color=0xF59E0B if winner_name == "Hòa" else 0x10B981
    )
    all_notifs = []
    if dq_c: all_notifs.extend([f"**[{challenger.display_name}]** {n}" for n in dq_c])
    if dq_t: all_notifs.extend([f"**[{target.display_name}]** {n}" for n in dq_t])
    if 'ev_c' in locals() and ev_c: all_notifs.extend([f"**[{challenger.display_name}]** {n}" for n in ev_c])
    if 'ev_t' in locals() and ev_t: all_notifs.extend([f"**[{target.display_name}]** {n}" for n in ev_t])
    if all_notifs:
        embed.add_field(name="📜 Tiến Trình Nhiệm Vụ & Sự Kiện:", value="\n".join(all_notifs), inline=False)
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
    embed.set_footer(text="Bấm 'Xem Chi Tiết Trận Chiến & GIF Kỹ Năng' bên dưới để xem lại từng hiệp kèm GIF hoạt ảnh trực tiếp!")

    details_view = OpenDetailsView(pvp_turns)
    sent = False

    target_channel = channel
    if target_channel is None and interaction:
        target_channel = interaction.channel

    if target_channel:
        try:
            await target_channel.send(embed=embed, view=details_view)
            sent = True
        except Exception:
            pass

    if not sent and interaction:
        try:
            await interaction.followup.send(embed=embed, view=details_view)
            sent = True
        except Exception:
            pass

    if not sent and target_channel and hasattr(target_channel, "id"):
        try:
            fetched_ch = await bot.fetch_channel(target_channel.id)
            if fetched_ch:
                await fetched_ch.send(embed=embed, view=details_view)
                sent = True
        except Exception:
            pass

    if not sent:
        for p_user in [challenger, target]:
            try:
                await p_user.send(
                    content=f"⚔️ **Kết quả trận PvP 3v3 giữa {challenger.display_name} và {target.display_name}:**",
                    embed=embed,
                    view=OpenDetailsView(pvp_turns)
                )
            except Exception:
                pass

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
        value="• Đấu lần lượt 3 thẻ bài (tự động cộng chỉ số theo Cấp & Thức tỉnh Ace 2).\n• Kỹ năng Ace 2: Sakuya đóng băng, Reimu vô tưởng chuyển sinh, Seiki 4 tuyệt kỹ (hiện GIF trực tiếp).\n• Thẻ bài trước khi gục ngã đều đổi toàn bộ sát thương lên đối thủ!\n• Sau trận có mục **Xem Chi Tiết Trận Chiến** để xem lại từng hiệp kèm GIF.",
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
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** Thẻ #{cid} của {self.initiator.display_name} đang bị Admin khóa.", view=self)
                self.stop()
                return
            if inv_a.get(str(cid), 0) < qty:
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** {self.initiator.display_name} không còn đủ {qty} lá #{cid} trong túi đồ.", view=self)
                self.stop()
                return

        for cid, qty in self.offer_receive.items():
            if is_card_locked(p_b, cid):
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** Thẻ #{cid} của {self.target.display_name} đang bị Admin khóa.", view=self)
                self.stop()
                return
            if inv_b.get(str(cid), 0) < qty:
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(content=f"❌ **Giao dịch thất bại!** {self.target.display_name} không còn đủ {qty} lá #{cid} trong túi đồ.", view=self)
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

        give_summary_a = "\n".join([f"• Gửi đi: {qty}x **#{cid} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Còn: {inv_a.get(str(cid), 0)} lá)" for cid, qty in self.offer_give.items()])
        recv_summary_a = "\n".join([f"• Nhận về: {qty}x **#{cid} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Hiện có: {inv_a.get(str(cid), 0)} lá)" for cid, qty in self.offer_receive.items()])
        embed_success.add_field(
            name=f"📦 {self.initiator.display_name} cập nhật:",
            value=f"{give_summary_a}\n{recv_summary_a}",
            inline=False
        )

        give_summary_b = "\n".join([f"• Gửi đi: {qty}x **#{cid} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Còn: {inv_b.get(str(cid), 0)} lá)" for cid, qty in self.offer_give.items()])
        recv_summary_b = "\n".join([f"• Nhận về: {qty}x **#{cid} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Hiện có: {inv_b.get(str(cid), 0)} lá)" for cid, qty in self.offer_receive.items()])
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
            msg = f"🔒 Lá bài **#{cid} {card_info['name']}** của bạn đang bị Admin niêm phong, không thể mang đi trao đổi!"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        has_cnt = inv_a.get(str(cid), 0)
        if has_cnt < qty:
            msg = f"❌ Bạn (**{getattr(author, 'display_name', str(author))}**) không đủ {qty} lá **#{cid} [{card_info['rank']}] {card_info['name']}** để gửi đi! (Hiện chỉ có: {has_cnt} lá)"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        if inv_b.get(str(cid), 0) < 1 and not is_card_ace2(p_b, cid):
            msg = (
                f"🛡️ **Quy định chống Clone Account:**\n"
                f"Đối phương (**{getattr(user, 'display_name', str(user))}**) chưa từng sở hữu thẻ **#{cid} [{card_info['rank']}] {card_info['name']}**!\n"
                f"⚠️ Người nhận bắt buộc phải đã sở hữu ít nhất 1 lá bài này từ trước mới được phép nhận trade."
            )
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

    for cid, qty in offer_b.items():
        card_info = CARDS_DATA[cid]
        if is_card_locked(p_b, cid):
            msg = f"🔒 Lá bài **#{cid} {card_info['name']}** của đối phương đang bị Admin niêm phong, không thể mang đi trao đổi!"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        has_cnt = inv_b.get(str(cid), 0)
        if has_cnt < qty:
            msg = f"❌ Đối phương (**{getattr(user, 'display_name', str(user))}**) không đủ {qty} lá **#{cid} [{card_info['rank']}] {card_info['name']}** để gửi lại! (Hiện chỉ có: {has_cnt} lá)"
            await send_trade_msg(ctx_or_interaction, content=msg, ephemeral=True)
            return

        if inv_a.get(str(cid), 0) < 1 and not is_card_ace2(p_a, cid):
            msg = (
                f"🛡️ **Quy định chống Clone Account:**\n"
                f"Bạn (**{getattr(author, 'display_name', str(author))}**) chưa từng sở hữu thẻ **#{cid} [{card_info['rank']}] {card_info['name']}**!\n"
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
    give_txt = "\n".join([f"• {qty}x **#{cid} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Kho: {inv_a.get(str(cid), 0)} lá)" for cid, qty in offer_a.items()])
    recv_txt = "\n".join([f"• {qty}x **#{cid} [{CARDS_DATA[cid]['rank']}] {CARDS_DATA[cid]['name']}** (Kho: {inv_b.get(str(cid), 0)} lá)" for cid, qty in offer_b.items()])

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
    embed.add_field(name="👺 Bát Ách Kiếm Thần Tướng Mahoraga (Single Phase):", value=f"• 90,000 HP | 6,000 DMG (chia đều)\n• Nội tại The True Adapt (100%): tự hồi 3% HP tối đa (2,700 HP) và GIẢM 3% sát thương phải nhận mỗi lượt (cộng dồn)!\n• Kỹ năng Thoái Ma Kiếm (25%): 6,000 DMG sát thương thuần lên 1 mục tiêu duy nhất!\n• Phần thưởng: 10% 20 vé, 40% 15 vé, 50% 10 vé, 5% Mảnh Mahoraga!", inline=False)
    embed.add_field(name="👹 Seiki Dị Hình (2 Phase):", value=f"• Phase 1: HP {SEIKI_BOSS_CONFIG['hp']:,} | {SEIKI_BOSS_CONFIG['power']:,} DMG (chia đều) + nội tại hồi 1.5% HP\n• Phase 2 Thức Tỉnh: HP {SEIKI_BOSS_PHASE2_CONFIG['hp']:,} | {SEIKI_BOSS_PHASE2_CONFIG['power']:,} DMG (chia đều) + Cleave +10% Máu tối đa mục tiêu + Nuclear Spell Card (10%) 10K DMG toàn tiền tuyến!", inline=False)
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
            if "fateria" in sub or "fate" in sub:
                b_type = "fateria"
            elif "mahoraga" in sub:
                b_type = "mahoraga"
            elif "seiki" in sub:
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
        await ctx.send("🟢 Boss đã sẵn sàng xuất hiện (Tỉ lệ đều 1/3 Mahoraga, Seiki, Reimu khi chat, hoặc dùng `boss admin spawn [mahoraga|seiki|reimu]`)!")

@bot.tree.command(name="boss_admin", description="[Admin] Quản trị Boss Raid (Fateria, Mahoraga, Seiki, Reimu)")
@app_commands.describe(action="Hành động muốn thực hiện với Boss Raid", loai_boss="Loại Boss muốn triệu hồi (nếu chọn spawn)")
@app_commands.choices(action=[
    app_commands.Choice(name="spawn - Triệu hồi Boss ngay tại kênh này", value="spawn"),
    app_commands.Choice(name="reset - Giải phóng Boss kẹt và xóa hồi chiêu", value="reset")
], loai_boss=[
    app_commands.Choice(name="Fateria – Khuôn mẫu của số phận (95k HP / 6k2 DMG)", value="fateria"),
    app_commands.Choice(name="Bát Ách Kiếm Thần Tướng Mahoraga (90k HP / The True Adapt)", value="mahoraga"),
    app_commands.Choice(name="Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư", value="seiki"),
    app_commands.Choice(name="Reimu Dị Hình - 2 Phase Siêu Cấp", value="reimu"),
    app_commands.Choice(name="Ngẫu nhiên tỉ lệ 1/4 giữa 4 Boss", value="random")
])
async def slash_boss_admin(interaction: discord.Interaction, action: str, loai_boss: str = "random"):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN HẠN!** Chỉ có Han Seiki hoặc Admin mới được dùng lệnh này!", ephemeral=True)
        return
    if action == "spawn":
        b_type = None if loai_boss == "random" else loai_boss
        boss_label = "Fateria" if b_type == "fateria" else ("Mahoraga" if b_type == "mahoraga" else ("Seiki Dị Hình" if b_type == "seiki" else ("Reimu Dị Hình" if b_type == "reimu" else "Boss Raid ngẫu nhiên")))
        await interaction.response.send_message(f"⚡ Đang cưỡng chế triệu hồi {boss_label}...", ephemeral=True)
        await admin_spawn_boss(interaction.channel, interaction.user, boss_type=b_type)
    elif action == "reset":
        await admin_reset_boss(interaction, interaction.user)

@bot.tree.command(name="admin_boss_spawn", description="[Admin] Triệu hồi ngay Boss Raid (Fateria, Mahoraga, Seiki, Reimu) tại kênh này")
@app_commands.describe(loai_boss="Chọn Boss muốn triệu hồi")
@app_commands.choices(loai_boss=[
    app_commands.Choice(name="Fateria – Khuôn mẫu của số phận (95k HP / 6k2 DMG)", value="fateria"),
    app_commands.Choice(name="Bát Ách Kiếm Thần Tướng Mahoraga (90k HP / The True Adapt)", value="mahoraga"),
    app_commands.Choice(name="Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư", value="seiki"),
    app_commands.Choice(name="Reimu Dị Hình - 2 Phase Siêu Cấp", value="reimu"),
    app_commands.Choice(name="Ngẫu nhiên tỉ lệ 1/4 giữa 4 Boss", value="random")
])
async def slash_admin_boss_spawn(interaction: discord.Interaction, loai_boss: str = "random"):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN HẠN!**", ephemeral=True)
        return
    b_type = None if loai_boss == "random" else loai_boss
    boss_label = "Fateria" if b_type == "fateria" else ("Mahoraga" if b_type == "mahoraga" else ("Seiki Dị Hình" if b_type == "seiki" else ("Reimu Dị Hình" if b_type == "reimu" else "Boss Raid ngẫu nhiên")))
    await interaction.response.send_message(f"⚡ Đang triệu hồi {boss_label}...", ephemeral=True)
    await admin_spawn_boss(interaction.channel, interaction.user, boss_type=b_type)

@bot.tree.command(name="admin_boss_reset", description="[Admin] Giải phóng Boss Raid bị kẹt và xóa hồi chiêu")
async def slash_admin_boss_reset(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN HẠN!**", ephemeral=True)
        return
    await admin_reset_boss(interaction, interaction.user)
# ==============================================================================
# LIVE BATTLE STORY MODE - STAGE 1: RUMIA (HỒ SƯƠNG MÙ)
# ==============================================================================
async def run_story_rumia_battle(channel_or_interaction, user, player):
    st = player.setdefault("story", {})
    boss_lvl = st.get("rumia_boss_level") or player.get("level", 1)
    
    boss_atk_buff = get_level_atk_buff(boss_lvl)
    boss_hp_buff = get_level_hp_buff(boss_lvl)
    rumia_max_hp = 4400 + boss_hp_buff
    rumia_hp = rumia_max_hp
    rumia_power = 440 + boss_atk_buff

    team_cids = [cid for cid in player.get("team", []) if cid in CARDS_DATA and not is_card_locked(player, cid)]
    if len(team_cids) < 3:
        owned = get_owned_card_ids(player)
        owned.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
        for cid in owned:
            if cid not in team_cids: team_cids.append(cid)
            if len(team_cids) >= 3: break
        player["team"] = team_cids
        save_player(player)

    p_buff_pwr = get_level_atk_buff(player["level"])
    p_buff_hp = get_level_hp_buff(player["level"])

    player_cards = []
    for cid in team_cids[:3]:
        c = CARDS_DATA[cid]
        is_ace = is_card_ace2(player, cid)
        ace_pwr = ACE_POWER_BUFF if is_ace else 0
        ace_hp = ACE_HP_BUFF if is_ace else 0
        card_pwr = c["power"] + p_buff_pwr + ace_pwr
        card_hp = c["hp"] + p_buff_hp + ace_hp
        player_cards.append({
            "cid": cid,
            "name": f"[Ace 2 ⭐⭐] #{c['id']} {c['name']}" if is_ace else f"#{c['id']} {c['name']}",
            "power": card_pwr,
            "max_hp": card_hp,
            "current_hp": card_hp,
            "is_ace2": is_ace
        })

    embed_init = discord.Embed(
        title="⚔️ [LIVE BATTLE] STAGE 1: HỒ SƯƠNG MÙ - ĐẠI CHIẾN RUMIA!",
        description=(
            f"👤 **Trợ thủ xuất trận:** {user.mention} (Lv.{player['level']})\n"
            f"👺 **Đối thủ:** [Rank C] **#25 Rumia (Yêu Quái Của Hoàng Hôn)** (Lv.{boss_lvl})\n"
            f"❤️ Máu Boss: `{get_hp_bar(rumia_hp, rumia_max_hp)}` **{rumia_hp:,}/{rumia_max_hp:,} HP**\n"
            f"⚔️ Sức mạnh: **{rumia_power:,} DMG**"
        ),
        color=0x7C3AED
    )
    embed_init.set_thumbnail(url=CARDS_DATA[25]["image"])
    
    if isinstance(channel_or_interaction, discord.Interaction):
        if channel_or_interaction.response.is_done():
            msg = await channel_or_interaction.followup.send(embed=embed_init)
        else:
            await channel_or_interaction.response.send_message(embed=embed_init)
            msg = await channel_or_interaction.original_response()
    else:
        msg = await channel_or_interaction.send(embed=embed_init)

    await asyncio.sleep(2.0)

    p_idx = 0
    rounds = 0
    sakuya_used, reimu_used, marisa_used = False, False, False
    flandre_used, reisen_used, yukari_used = False, False, False
    p_t1 = {"seal_used": False, "bong_used": False, "med_used": False, "used_turn": -1}
    boss_skill_erased = False

    while rumia_hp > 0 and p_idx < len(player_cards) and rounds < 25:
        rounds += 1
        pc = player_cards[p_idx]
        turn_image = None
        turn_logs = []
        card_dmg = pc["power"]

        if pc["cid"] == 18 and pc["is_ace2"] and not sakuya_used:
            if random.random() < 0.40:
                sakuya_used = True
                turn_image = EVOL_CONFIG[18]["skill_gif"]
                turn_logs.append("⏳ **[Ace 2] Sakuya** kích hoạt **Thời Gian Đóng Băng**! Rumia bị STUN mất lượt!")

        if pc["cid"] == 19 and pc["is_ace2"] and not marisa_used:
            if random.random() < 0.30:
                marisa_used = True
                card_dmg = int(card_dmg * 2.0)
                if not turn_image: turn_image = EVOL_CONFIG[19]["skill_gif"]
                turn_logs.append(f"🌟 **[Ace 2] Marisa** tung **Master Spark** (×2.0)! Giáng {card_dmg:,} DMG!")
                
          # Kỹ năng Seiki Ace 2 trong Story Mode
        if str(pc["cid"]).lower() == "t1" and pc.get("is_ace2"):
            _t1 = t1_ace2_attack(p_t1, pc, rounds, rumia_max_hp, "Boss Rumia", is_boss=True)
            if _t1.get("multiplier", 1.0) > 1.0:
                card_dmg = int(card_dmg * _t1["multiplier"])
            card_dmg += _t1["bonus"]
            if _t1["direct"]:
                rumia_hp = max(0, rumia_hp - _t1["direct"])
            if _t1["disable"]:
                boss_skill_erased = True
                turn_logs.append("🌑 **[Bóng Khái Niệm]** Đã xóa toàn bộ ma pháp bóng tối của Rumia!")
            if _t1["heal"]:
                pc["current_hp"] = min(pc["max_hp"], pc["current_hp"] + _t1["heal"])
            if _t1["gif"] and not turn_image:
                turn_image = _t1["gif"]
            turn_logs.extend(_t1["logs"])

        # Kỹ năng Remilia Ace 2 (Thụ động +3% Max HP)
        if pc["cid"] == 12 and pc.get("is_ace2"):
            gungnir_dmg = int(rumia_max_hp * 0.03)
            card_dmg += gungnir_dmg
            turn_logs.append(f"🩸 **[Ace 2] Remilia** - **Thương Đỏ Gungnir**: +{gungnir_dmg:,} DMG (3% Max HP)!")

        # Kỹ năng Flandre Ace 2 (Ripples of 495 Years - 50% HP)
        if pc["cid"] == 9 and pc.get("is_ace2") and not flandre_used:
            if random.random() < 0.25:
                flandre_used = True
                rip_dmg = int(rumia_hp * 0.50)
                rumia_hp = max(0, rumia_hp - rip_dmg)
                if not turn_image: turn_image = EVOL_CONFIG[9]["skill_gif"]
                turn_logs.append(f"🦇 **[Ace 2] Flandre** tung **Ripples of 495 Years** (25%)! Xóa sổ **{rip_dmg:,} HP (50% HP Rumia)**!")

        t4_invul_story = False
        if str(pc["cid"]).lower() == "t4":
            t4_st = pc.setdefault("t4_state", {})
            _t4 = t4_combat_turn(t4_st, pc, "Boss Rumia")
            card_dmg = int(card_dmg * _t4["multiplier"])
            if _t4["save_loop_invul"]:
                t4_invul_story = True
            if _t4["ice_spear_triggered"] and random.random() < 0.40:
                sakuya_used = True
            if _t4["gif"] and not turn_image:
                turn_image = _t4["gif"]
            turn_logs.extend(_t4["logs"])     

        rumia_hp = max(0, rumia_hp - card_dmg)
        turn_logs.append(f"🗡️ **{pc['name']}** tấn công gây **{card_dmg:,} DMG** lên Rumia!")

        if rumia_hp <= 0:
            turn_logs.append("💥 **Rumia đã bị đánh bay hoàn toàn!**")
        else:
            if sakuya_used and rounds == 1:
                turn_logs.append("❄️ Rumia bị đóng băng không thể phản công!")
            else:
                invul = t4_invul_story
                if pc["cid"] == 15 and pc["is_ace2"] and not reimu_used:
                    if random.random() < 0.40:
                        reimu_used = True
                        invul = True
                        if not turn_image: turn_image = EVOL_CONFIG[15]["skill_gif"]
                        turn_logs.append(f"🛡️ **[Ace 2] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh**! Miễn toàn bộ sát thương!")
                if not invul:
                    pc["current_hp"] -= rumia_power
                    turn_logs.append(f"🌑 **Rumia** phản kích bằng **Dạ Tối Kết Giới** gây **{rumia_power:,} DMG** lên {pc['name']}!")

        if pc["current_hp"] <= 0:
            pc["current_hp"] = 0
            trade = pc["power"]
            rumia_hp = max(0, rumia_hp - trade)
            turn_logs.append(f"💥 [Đổi Sát Thương] {pc['name']} trước khi gục đã đổi **{trade:,} DMG** vào Rumia!")
            p_idx += 1
            if p_idx < len(player_cards):
                turn_logs.append(f"💀 Đẩy **{player_cards[p_idx]['name']}** lên tiền tuyến!")

        r_embed = discord.Embed(
            title=f"⚔️ HIỆP {rounds} - QUYẾT ĐẤU RUMIA (STAGE 1)",
            description=(
                f"❤️ Máu Rumia: `{get_hp_bar(rumia_hp, rumia_max_hp)}` **{rumia_hp:,}/{rumia_max_hp:,} HP**\n\n"
                + "\n".join(turn_logs)
            ),
            color=0x7C3AED if rumia_hp > 0 else 0x10B981
        )
        if turn_image: r_embed.set_image(url=turn_image)
        else: r_embed.set_thumbnail(url=CARDS_DATA[25]["image"])
        try: await msg.edit(embed=r_embed)
        except Exception: pass

        if rumia_hp <= 0: break
        await asyncio.sleep(2.0)

    if rumia_hp <= 0:
        inv = player.setdefault("inventory", {})
        inv["25"] = inv.get("25", 0) + 10
        if 25 not in player.get("unlocked_cards", []):
            player.setdefault("unlocked_cards", []).append(25)
        player["pull_tickets"] += 10.0
        st["stage1_completed"] = True
        st["current_stage"] = 2
        save_player(player)

        embed_win = discord.Embed(
            title="🎉 CHIẾN THẮNG STAGE 1: HỒ SƯƠNG MÙ!",
            description=(
                "🌸 **\"Rumia bị Reimu cùng trợ thủ cô đánh bay trong khi còn không biết gì về làn sương\"**\n\n"
                "⛩️ **Reimu:** *\"Hừ, chỉ là một con yêu quái tép riu chắn đường thôi. Mau thu dọn chiến lợi phẩm rồi tiến sâu vào hồ nào trợ thủ!\"*\n\n"
                "🎁 **PHẦN THƯỞNG CHIẾN TÍCH:**\n"
                f"• 🎴 **+10 Thẻ bài [#25] Rumia (Rank C)** cộng thẳng vào túi đồ! (Hiện có: `{inv['25']}` lá)\n"
                f"• 🎟️ **+10 Lượt Pull Tích Lũy** (Tổng vé hiện có: `{player['pull_tickets']:.2f}` vé)!\n"
                f"• 🌟 **Mở khóa danh hiệu:** Người Thanh Tẩy Màn Đêm Hồ Sương Mù"
            ),
            color=0x10B981
        )
        embed_win.set_image(url="https://c.tenor.com/gc4ws16CrTYAAAAC/reimu-touhou.gif")
        embed_win.set_footer(text="Stage 1 Completed • Kiểm tra túi đồ bằng /collection hoặc /team")
        try: await msg.edit(embed=embed_win)
        except Exception: pass
    else:
        embed_loss = discord.Embed(
            title="💀 THẤT BẠI TẠI STAGE 1!",
            description=(
                f"Đội hình của {user.mention} đã bị quả cầu bóng tối của Rumia nuốt chửng!\n"
                "Rumia còn lại: **" + f"{rumia_hp:,}/{rumia_max_hp:,} HP**\n\n"
                "💡 *Hãy rèn luyện nâng cấp thẻ bài, xếp lại đội hình qua `/team` và gõ lại `/story` để phục thù!*"
            ),
            color=0xEF4444
        )
        embed_loss.set_thumbnail(url=CARDS_DATA[25]["image"])
        try: await msg.edit(embed=embed_loss)
        except Exception: pass

# ==============================================================================
# GIAO DIỆN & BỘ ĐIỀU HƯỚNG CỐT TRUYỆN (/STORY)
# ==============================================================================
class StoryBattleView(discord.ui.View):
    def __init__(self, user, player):
        super().__init__(timeout=180)
        self.user = user
        self.player = player

    @discord.ui.button(label="⚔️ Xuất Trận Quyết Đấu Rumia (Live Battle)", style=discord.ButtonStyle.danger, emoji="💥")
    async def fight_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên cốt truyện của bạn!", ephemeral=True)
            return
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content="🔥 **Trận chiến bắt đầu nghênh chiến Rumia!**", view=self)
        self.stop()
        await run_story_rumia_battle(interaction, self.user, self.player)

# ==============================================================================
# GIAO DIỆN CÂU ĐỐ STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ (TỰ ĐỘNG XÁO TRỘN KHI SAI)
# ==============================================================================
class Stage2QuizView(discord.ui.View):
    def __init__(self, user, player):
        super().__init__(timeout=180)
        self.user = user
        self.player = player
        self.options = [
            {"id": "1", "label": "Là 1 tiên nữ", "correct": True, "reply": "Phải rồi, xem nào."},
            {"id": "2", "label": "Là 1 con nhóc", "correct": False, "reply": "Ờ thì con nhóc rồi sao nữa?"},
            {"id": "3", "label": "Là 1 con yêu quái", "correct": False, "reply": "Chịu chết."},
            {"id": "4", "label": "Là vợ tôi?", "correct": False, "reply": "Gì cơ? Cậu muốn chết à?"}
        ]
        self.build_buttons()

    def build_buttons(self):
        self.clear_items()
        random.shuffle(self.options)
        for opt in self.options:
            btn = discord.ui.Button(
                label=opt["label"],
                style=discord.ButtonStyle.secondary,
                custom_id=opt["id"]
            )
            btn.callback = self.make_callback(opt)
            self.add_item(btn)

    def make_callback(self, opt):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("❌ Đây không phải lượt trả lời của bạn!", ephemeral=True)
                return

            if opt["correct"]:
                st = self.player.setdefault("story", {})
                st["stage2_quiz_passed"] = True
                save_player(self.player)

                embed_correct = discord.Embed(
                    title="✨ TRẢ LỜI CHÍNH XÁC!",
                    description=(
                        f"⛩️ **Reimu:** *\"{opt['reply']}\"*\n\n"
                        "🌫️ *Phía trước sương mù dày đặc, một luồng hàn khí thấu xương đang ập tới...*\n"
                        "👉 Đang mở khóa nhiệm vụ tập luyện chuẩn bị nghênh chiến!"
                    ),
                    color=0x10B981
                )
                for child in self.children: child.disabled = True
                await interaction.response.edit_message(embed=embed_correct, view=None)
                await handle_story(interaction)
            else:
                self.build_buttons()
                embed_wrong = discord.Embed(
                    title="❄️ BỀ MẶT HỒ SƯƠNG MÙ (LAKE SURFACE)",
                    description=(
                        "Khi tiến sâu vào lòng hồ để đến hòn đảo trung tâm, không khí trở nên lạnh giá.\n"
                        "Reimu quay sang hỏi trợ thủ:\n"
                        "**\"Thứ gì vậy?\"**\n\n"
                        f"💢 **Reimu:** *\"{opt['reply']}\"*\n"
                        "*(Đáp án chưa đúng! Các phương án bên dưới đã được xáo trộn lại, hãy chọn lại!)*"
                    ),
                    color=0xEF4444
                )
                await interaction.response.edit_message(embed=embed_wrong, view=self)
        return button_callback

# ==============================================================================
# LIVE BATTLE STORY MODE - STAGE 2: CIRNO ACE 2 (BỀ MẶT HỒ SƯƠNG MÙ)
# ==============================================================================
class StoryCirnoBattleView(discord.ui.View):
    def __init__(self, user, player):
        super().__init__(timeout=180)
        self.user = user
        self.player = player

    @discord.ui.button(label="⚔️ Xuất Trận Quyết Đấu Cirno Ace 2 (Live Battle)", style=discord.ButtonStyle.danger, emoji="💥")
    async def fight_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên cốt truyện của bạn!", ephemeral=True)
            return
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content="🔥 **Trận chiến bắt đầu nghênh chiến Cirno Ace 2!**", view=self)
        self.stop()
        await run_story_cirno_battle(interaction, self.user, self.player)

async def run_story_cirno_battle(channel_or_interaction, user, player):
    st = player.setdefault("story", {})
    boss_lvl = st.get("cirno_boss_level") or player.get("level", 20)

    boss_atk_buff = get_level_atk_buff(boss_lvl)
    boss_hp_buff = get_level_hp_buff(boss_lvl)
    cirno_max_hp = 6600 + boss_hp_buff
    cirno_hp = cirno_max_hp
    cirno_power = 1200 + boss_atk_buff

    team_cids = [cid for cid in player.get("team", []) if cid in CARDS_DATA and not is_card_locked(player, cid)]
    if len(team_cids) < 3:
        owned = get_owned_card_ids(player)
        owned.sort(key=lambda cid: CARDS_DATA[cid]["power"], reverse=True)
        for cid in owned:
            if cid not in team_cids: team_cids.append(cid)
            if len(team_cids) >= 3: break
        player["team"] = team_cids
        save_player(player)

    p_buff_pwr = get_level_atk_buff(player["level"])
    p_buff_hp = get_level_hp_buff(player["level"])

    player_cards = []
    for cid in team_cids[:3]:
        c = CARDS_DATA[cid]
        is_ace = is_card_ace2(player, cid)
        ace_pwr = ACE_POWER_BUFF if is_ace else 0
        ace_hp = ACE_HP_BUFF if is_ace else 0
        card_pwr = c["power"] + p_buff_pwr + ace_pwr
        card_hp = c["hp"] + p_buff_hp + ace_hp
        player_cards.append({
            "cid": cid,
            "name": f"[Ace 2 ⭐⭐] #{c['id']} {c['name']}" if is_ace else f"#{c['id']} {c['name']}",
            "power": card_pwr,
            "max_hp": card_hp,
            "current_hp": card_hp,
            "is_ace2": is_ace
        })

    embed_init = discord.Embed(
        title="⚔️ [LIVE BATTLE] STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ - CIRNO ACE 2!",
        description=(
            f"👤 **Trợ thủ xuất trận:** {user.mention} (Lv.{player['level']})\n"
            f"❄️ **Boss:** **[#23] Cirno (Đệ Nhất Băng Tiên - Ace 2 ⭐⭐)** (Lv.{boss_lvl})\n"
            f"❤️ Máu Boss: `{get_hp_bar(cirno_hp, cirno_max_hp)}` **{cirno_hp:,}/{cirno_max_hp:,} HP**\n"
            f"⚔️ Sức mạnh: **{cirno_power:,} DMG**\n"
            f"🧊 Tuyệt kỹ: **Perfect Freeze** (40% đóng băng, 2 turn tiếp có 45% không thể đánh trả)"
        ),
        color=0x06B6D4
    )
    embed_init.set_thumbnail(url=CARDS_DATA[23]["image"])

    if isinstance(channel_or_interaction, discord.Interaction):
        if channel_or_interaction.response.is_done():
            msg = await channel_or_interaction.followup.send(embed=embed_init)
        else:
            await channel_or_interaction.response.send_message(embed=embed_init)
            msg = await channel_or_interaction.original_response()
    else:
        msg = await channel_or_interaction.send(embed=embed_init)

    await asyncio.sleep(2.0)

    p_idx = 0
    rounds = 0
    cirno_freeze_turns = 0
    cirno_skill_used = False
    sakuya_used, reimu_used, marisa_used = False, False, False
    flandre_used, reisen_used, yukari_used = False, False, False
    p_t1 = {"seal_used": False, "bong_used": False, "med_used": False, "used_turn": -1}
    boss_skill_erased = False

    while cirno_hp > 0 and p_idx < len(player_cards) and rounds < 25:
        rounds += 1
        pc = player_cards[p_idx]
        turn_image = None
        turn_logs = []
        card_dmg = pc["power"]
        player_stunned = False

        if cirno_freeze_turns > 0:
            cirno_freeze_turns -= 1
            if random.random() < 0.45:
                player_stunned = True
                turn_logs.append(f"🧊 **[Perfect Freeze]** {pc['name']} bị đóng băng cứng đờ (45%), không thể ra đòn!")

        if not player_stunned:
            if pc["cid"] == 18 and pc["is_ace2"] and not sakuya_used:
                if random.random() < 0.40:
                    sakuya_used = True
                    turn_image = EVOL_CONFIG[18]["skill_gif"]
                    turn_logs.append("⏳ **[Ace 2] Sakuya** kích hoạt **Thời Gian Đóng Băng**! Cirno bị STUN mất lượt!")

            if pc["cid"] == 19 and pc["is_ace2"] and not marisa_used:
                if random.random() < 0.30:
                    marisa_used = True
                    card_dmg = int(card_dmg * 2.0)
                    if not turn_image: turn_image = EVOL_CONFIG[19]["skill_gif"]
                    turn_logs.append(f"🌟 **[Ace 2] Marisa** tung **Master Spark** (×2.0)! Giáng {card_dmg:,} DMG!")
                    
                    # Kỹ năng Seiki Ace 2 trong Stage 2
            if str(pc["cid"]).lower() == "t1" and pc.get("is_ace2"):
                _t1 = t1_ace2_attack(p_t1, pc, rounds, cirno_max_hp, "Boss Cirno", is_boss=True)
                if _t1.get("multiplier", 1.0) > 1.0:
                    card_dmg = int(card_dmg * _t1["multiplier"])
                card_dmg += _t1["bonus"]
                if _t1["direct"]:
                    cirno_hp = max(0, cirno_hp - _t1["direct"])
                if _t1["disable"]:
                    boss_skill_erased = True
                    cirno_freeze_turns = 0
                    turn_logs.append("🌑 **[Bóng Khái Niệm]** Đã khóa vĩnh viễn tuyệt kỹ Perfect Freeze của Cirno!")
                if _t1["heal"]:
                    pc["current_hp"] = min(pc["max_hp"], pc["current_hp"] + _t1["heal"])
                if _t1["gif"] and not turn_image:
                    turn_image = _t1["gif"]
                turn_logs.extend(_t1["logs"])

            # Kỹ năng Remilia Ace 2 (Thụ động +3% Max HP)
            if pc["cid"] == 12 and pc.get("is_ace2"):
                gungnir_dmg = int(cirno_max_hp * 0.03)
                card_dmg += gungnir_dmg
                turn_logs.append(f"🩸 **[Ace 2] Remilia** - **Thương Đỏ Gungnir**: +{gungnir_dmg:,} DMG!")

            # Kỹ năng Flandre Ace 2 (Ripples of 495 Years)
            if pc["cid"] == 9 and pc.get("is_ace2") and not flandre_used:
                if random.random() < 0.25:
                    flandre_used = True
                    rip_dmg = int(cirno_hp * 0.50)
                    cirno_hp = max(0, cirno_hp - rip_dmg)
                    if not turn_image: turn_image = EVOL_CONFIG[9]["skill_gif"]
                    turn_logs.append(f"🦇 **[Ace 2] Flandre** tung **Ripples of 495 Years**! Xóa sổ **{rip_dmg:,} HP (50% HP Cirno)**!")

            if str(pc["cid"]).lower() == "t4":
                t4_st = pc.setdefault("t4_state", {})
                _t4 = t4_combat_turn(t4_st, pc, "Boss Cirno")
                card_dmg = int(card_dmg * _t4["multiplier"])
                if _t4["save_loop_invul"]:
                    pc["current_hp"] += cirno_power
                if _t4["fate_loop_triggered"]:
                    boss_skill_erased = True
                    cirno_freeze_turns = 0
                if _t4["gif"] and not turn_image:
                    turn_image = _t4["gif"]
                turn_logs.extend(_t4["logs"])

            cirno_hp = max(0, cirno_hp - card_dmg)
            turn_logs.append(f"🗡️ **{pc['name']}** tấn công gây **{card_dmg:,} DMG** lên Cirno!")

        if cirno_hp <= 0:
            turn_logs.append("💥 **Cirno đã bị đánh văng xuống làn nước băng giá!**")
        else:
            if sakuya_used and rounds == 1:
                turn_logs.append("❄️ Cirno bị đóng băng thời gian nên không thể phản công!")
            else:
                if not boss_skill_erased and not cirno_skill_used and random.random() < 0.40:
                    cirno_skill_used = True
                    cirno_freeze_turns = 2
                    turn_image = EVOL_CONFIG[23]["skill_gif"]
                    turn_logs.append("❄️ **[Ace 2] Cirno** tung tuyệt kỹ **PERFECT FREEZE** (40%)! Đóng băng người chơi: trong 2 turn tiếp có 45% không thể đánh trả!")

                invul = False
                if pc["cid"] == 15 and pc["is_ace2"] and not reimu_used:
                    if random.random() < 0.40:
                        reimu_used = True
                        invul = True
                        if not turn_image: turn_image = EVOL_CONFIG[15]["skill_gif"]
                        turn_logs.append("🛡️ **[Ace 2] Reimu** kích hoạt **Vô Tưởng Chuyển Sinh**! Miễn sát thương!")
                if not invul:
                    pc["current_hp"] -= cirno_power
                    turn_logs.append(f"🧊 **Cirno Ace 2** phóng bão băng cực mạnh gây **{cirno_power:,} DMG** lên {pc['name']}!")

        if pc["current_hp"] <= 0:
            pc["current_hp"] = 0
            trade = pc["power"]
            cirno_hp = max(0, cirno_hp - trade)
            turn_logs.append(f"💥 [Đổi Sát Thương] {pc['name']} trước khi gục đã đổi **{trade:,} DMG** vào Cirno!")
            p_idx += 1
            if p_idx < len(player_cards):
                turn_logs.append(f"💀 Đẩy **{player_cards[p_idx]['name']}** lên nghênh chiến!")

        r_embed = discord.Embed(
            title=f"⚔️ HIỆP {rounds} - QUYẾT ĐẤU CIRNO ACE 2 (STAGE 2)",
            description=(
                f"❤️ Máu Cirno: `{get_hp_bar(cirno_hp, cirno_max_hp)}` **{cirno_hp:,}/{cirno_max_hp:,} HP**\n\n"
                + "\n".join(turn_logs)
            ),
            color=0x06B6D4 if cirno_hp > 0 else 0x10B981
        )
        if turn_image: r_embed.set_image(url=turn_image)
        else: r_embed.set_thumbnail(url=CARDS_DATA[23]["image"])
        try: await msg.edit(embed=r_embed)
        except Exception: pass

        if cirno_hp <= 0: break
        await asyncio.sleep(2.0)

    if cirno_hp <= 0:
        inv = player.setdefault("inventory", {})
        inv["23"] = inv.get("23", 0) + 30
        if 23 not in player.get("unlocked_cards", []):
            player.setdefault("unlocked_cards", []).append(23)
        player["pull_tickets"] += 5.0
        st["stage2_completed"] = True
        st["current_stage"] = 3
        save_player(player)

        embed_win = discord.Embed(
            title="🎉 CHIẾN THẮNG STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ!",
            description=(
                "🌸 **\"Con nhóc hỗn xược bị Reimu và trợ thủ ném xuống hồ băng\"**\n\n"
                "⛩️ **Reimu:** *\"Đúng là con bé phiền phức thích làm trò. Đường đến Hồng Ma Quán ở ngay phía trước rồi, mau đi thôi!\"*\n\n"
                "🎁 **PHẦN THƯỞNG CHIẾN TÍCH STAGE 2:**\n"
                f"• 🎴 **+30 Thẻ bài [#23] Cirno (Rank B)** cộng thẳng vào túi đồ! (Hiện có: `{inv['23']}` lá)\n"
                f"• 🎟️ **+5 Lượt Pull Tích Lũy** (Tổng vé hiện có: `{player['pull_tickets']:.2f}` vé)!\n"
                f"• 🏆 **Hoàn thành Stage 2!**"
            ),
            color=0x10B981
        )
        embed_win.set_image(url="https://c.tenor.com/gc4ws16CrTYAAAAC/reimu-touhou.gif")
        embed_win.set_footer(text="Stage 2 Completed • Dùng /collection hoặc /evol để nâng cấp Cirno Ace 2")
        try: await msg.edit(embed=embed_win)
        except Exception: pass
    else:
        embed_loss = discord.Embed(
            title="💀 THẤT BẠI TẠI STAGE 2!",
            description=(
                f"Đội hình của {user.mention} đã bị đóng băng cứng ngắc bởi Cirno Ace 2!\n"
                f"Cirno còn lại: **{cirno_hp:,}/{cirno_max_hp:,} HP**\n\n"
                "💡 *Gợi ý: Dùng /team sắp xếp thẻ có sát thương cao, nâng cấp bài và gõ lại /story để thử lại!*"
            ),
            color=0xEF4444
        )
        embed_loss.set_thumbnail(url=CARDS_DATA[23]["image"])
        try: await msg.edit(embed=embed_loss)
        except Exception: pass

async def handle_story(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    st = player.setdefault("story", {
        "current_stage": 0, "battles_done": 0, "quest_claimed": False, "rumia_boss_level": None, "stage1_completed": False
    })
    
    stage = st.get("current_stage", 0)

    if stage == 0:
        battles_cnt = st.get("battles_done", 0)
        user_lvl = player.get("level", 1)
        req_battle_ok = battles_cnt >= 10
        req_lvl_ok = user_lvl >= 10

        if req_battle_ok and req_lvl_ok:
            st["quest_claimed"] = True
            st["current_stage"] = 1
            st["rumia_boss_level"] = user_lvl
            player["pull_tickets"] += 10.0
            save_player(player)

            embed_unlock = discord.Embed(
                title="🎉 HOÀN THÀNH NHIỆM VỤ MỞ ĐẦU CỐT TRUYỆN!",
                description=(
                    f"⛩️ **Reimu:** *\"Khá lắm trợ thủ! Ngươi đã có đủ thực lực để cùng ta tiến sâu vào làn sương rồi đấy!\"*\n\n"
                    f"🎁 **PHẦN THƯỞNG HOÀN THÀNH:**\n"
                    f"• 🎟️ **+10 Lượt Pull Tích Lũy** (Đã cộng vào tài khoản! Hiện có: `{player['pull_tickets']:.2f}` vé)\n"
                    f"• 🗺️ **Mở khóa địa điểm mới:** **Stage 1: Hồ Sương Mù (Misty Lake)**!\n\n"
                    f"👉 **LƯU Ý:** Hãy gõ lại lệnh `/story` ngay bây giờ để tiến vào **Stage 1: Hồ Sương Mù** và bắt đầu hành trình!"
                ),
                color=0x10B981
            )
            embed_unlock.set_thumbnail(url="https://c.tenor.com/39VGItAUUCYAAAAC/reimu-reimu-hakurei.gif")
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed_unlock)
            else:
                await ctx_or_interaction.send(embed=embed_unlock)
            return

        status_battle = "✅ ĐÃ HOÀN THÀNH" if req_battle_ok else f"🔴 Chưa đủ ({battles_cnt}/10 trận)"
        status_lvl = "✅ ĐÃ ĐẠT" if req_lvl_ok else f"🔴 Chưa đủ (Cấp hiện tại: Lv.{user_lvl}/10)"

        embed_prologue = discord.Embed(
            title="📜 CỐT TRUYỆN: HỒNG MA DỊ BIẾN (EMBODIMENT OF SCARLET DEVIL)",
            description=(
                "Vào một ngày hè oi ả tại Ảo Tưởng Hương (Gensokyo), một làn sương màu đỏ dày đặc bất ngờ bùng phát "
                "và bao phủ khắp bầu trời, che khuất hoàn toàn ánh nắng mặt trời. Làn sương ấy làm nhiệt độ giảm xuống "
                "và khiến nơi đây sống trong chật vật. Thấy vậy Reimu bắt đầu lên đường xử lý vấn đề nhức nhối này.\n\n"
                f"⛩️ **Reimu:** *\"Được rồi trợ thủ {user.mention}, cùng tôi lên đường xử lý cái đám phiền phức này nào!\"*"
            ),
            color=0xDC2626
        )
        embed_prologue.set_image(url="https://media.discordapp.net/attachments/1533528571509866497/1549078962746171463/images.png?ex=6aa963b5&is=6aa81235&hm=3fa720bd7311e4ca45789c6a0112327878135e9d9944c31c6ed2ea1f60885853&=&format=webp&quality=lossless")
        embed_prologue.add_field(
            name="🎯 NHIỆM VỤ YÊU CẦU ĐỂ BƯỚC VÀO STAGE 1 (GAME STORY QUEST):",
            value=(
                f"• ⚔️ **Đánh `/battle` 10 lần:** **{status_battle}**\n"
                f"• ⭐ **Level tối thiểu 10:** **{status_lvl}**\n\n"
                "🎁 **Phần thưởng hoàn thành:** **+10 Lượt Pull** 🎟️ & Mở khóa **Stage 1: Hồ Sương Mù (Misty Lake)**!\n"
                "💡 *Sau khi hoàn thành đủ 2 điều kiện trên, hãy gõ lại `/story` để nhận thưởng và gặp gỡ Rumia!*"
            ),
            inline=False
        )
        embed_prologue.set_footer(text="Touhou Story Mode • Embodiment of Scarlet Devil • Gõ /battle để luyện cấp")
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed_prologue)
        else:
            await ctx_or_interaction.send(embed=embed_prologue)
        return

    elif stage == 1:
        boss_lvl = st.get("rumia_boss_level") or player.get("level", 1)
        dialogue_text = (
            "Trên đường tiến về phía hồ, họ gặp Rumia đang lơ lửng trong một cầu bóng tối do chính cô tạo ra...\n\n"
            "• 🌑 **Rumia:** *\"Phải rồi đó~ Có ma nữa nè, đơn giản là tuyệt vời thôi~\"*\n"
            "• ⛩️ **Reimu:** *\"Ờm... Ngươi là ai...?\"*\n"
            "• 🌑 **Rumia:** *\"Yêu quái của hoàng hôn, Rumia.\"*\n"
            "• ⛩️ **Reimu:** *\"...Ừ, và cô là?\"*\n"
            "• 🌑 **Rumia:** *\"Chẳng phải chúng ta đã gặp nhau vài phút trước rồi sao? Bộ cô bị quáng gà hả?\"*\n"
            "• ⛩️ **Reimu:** *\"Mắt người đâu phải để đi đêm!\"*\n"
            "• 🌑 **Rumia:** *\"Ồ? Nhưng tôi có gặp một số người chuyên làm việc vào ban đêm mà.\"*\n"
            "• ⛩️ **Reimu:** *\"Đối với loại người đó, cô có thể lấy họ làm bữa tối.\"*\n"
            "• 🌑 **Rumia:** *\"Ồ~ vậy à~\"*\n"
            "• ⛩️ **Reimu:** *\"Cô biết không, cô đang ngáng đường tôi đấy.\"*\n"
            "• 🌑 **Rumia:** *\"Thế kẻ đang đứng trước mặt tôi đây có phải loại người ăn thịt được không?\"*\n\n"
            "⚠️ **CẢNH BÁO:** Rumia đã mở rộng quả cầu hắc ám chuẩn bị tấn công! Hãy bấm nút **'Xuất Trận Quyết Đấu Rumia'** bên dưới để khai màn trận Live Battle!"
        )

        embed_stage1 = discord.Embed(
            title="🗺️ STAGE 1: HỒ SƯƠNG MÙ (MISTY LAKE)",
            description=dialogue_text,
            color=0x4F46E5
        )
        embed_stage1.set_thumbnail(url=CARDS_DATA[25]["image"])
        embed_stage1.add_field(
            name="👺 Thông Số Boss Rumia:",
            value=f"• Sức mạnh gốc: **440 DMG** | Máu gốc: **4,400 HP**\n• Cấp độ Boss: **Lv.{boss_lvl}** (Cố định bằng cấp độ của bạn lúc mở quest)",
            inline=True
        )
        embed_stage1.add_field(
            name="🎁 Phần Thưởng Sau Khi Hạ Gục:",
            value="• 🎴 **10 Thẻ bài ID 25 (Thẻ Rumia)** cộng thẳng vào túi đồ\n• 🎟️ **+10 Lượt Pull** tích lũy",
            inline=True
        )
        embed_stage1.set_footer(text="Bấm nút màu đỏ bên dưới để chiến đấu trực tiếp!")
        view = StoryBattleView(user, player)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed_stage1, view=view)
        else:
            await ctx_or_interaction.send(embed=embed_stage1, view=view)
        return

    elif stage == 2:
        if not st.get("stage2_quiz_passed", False):
            embed_quiz = discord.Embed(
                title="❄️ STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ (LAKE SURFACE)",
                description=(
                    "Khi tiến sâu vào lòng hồ để đến hòn đảo trung tâm, không khí trở nên lạnh giá.\n\n"
                    "Reimu quay sang hỏi trợ thủ:\n"
                    "⛩️ **Reimu:** *\"Thứ gì vậy?\"*\n\n"
                    "👉 **Hãy chọn câu trả lời đúng bên dưới để tiếp tục hành trình:**"
                ),
                color=0x06B6D4
            )
            embed_quiz.set_footer(text="Chọn phương án bên dưới • Nếu sai sẽ xáo trộn vị trí câu trả lời")
            quiz_view = Stage2QuizView(user, player)
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed_quiz, view=quiz_view)
            else:
                await ctx_or_interaction.send(embed=embed_quiz, view=quiz_view)
            return

        b_done = st.get("stage2_battles_done", 0)
        u_lvl = player.get("level", 1)
        req_b_ok = b_done >= 6
        req_l_ok = u_lvl >= 20

        if not st.get("stage2_quest_claimed", False):
            if req_b_ok and req_l_ok:
                st["stage2_quest_claimed"] = True
                st["cirno_boss_level"] = u_lvl
                player["pull_tickets"] += 10.0
                save_player(player)

                embed_q_win = discord.Embed(
                    title="🎉 HOÀN THÀNH NHIỆM VỤ TẬP LUYỆN STAGE 2!",
                    description=(
                        f"⛩️ **Reimu:** *\"Linh lực của ngươi đã vững vàng hơn rồi đấy trợ thủ! Mau xem kẻ tự xưng là 'mạnh nhất' này có bản lĩnh gì nào!\"*\n\n"
                        "🎁 **PHẦN THƯỞNG HOÀN THÀNH:**\n"
                        f"• 🎟️ **+10 Lượt Pull Tích Lũy** (Đã cộng vào tài khoản! Hiện có: `{player['pull_tickets']:.2f}` vé)\n"
                        f"• ❄️ **Mở khóa đại chiến:** **Cirno Ace 2 ⭐⭐ (Đệ Nhất Băng Tiên)**!\n\n"
                        "👉 **LƯU Ý:** Hãy gõ lại lệnh `/story` ngay bây giờ để tiến vào trận quyết đấu với Cirno!"
                    ),
                    color=0x10B981
                )
                embed_q_win.set_thumbnail(url=CARDS_DATA[23]["image"])
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(embed=embed_q_win)
                else:
                    await ctx_or_interaction.send(embed=embed_q_win)
                return

            status_b = "✅ ĐÃ HOÀN THÀNH" if req_b_ok else f"🔴 Chưa đủ ({b_done}/6 trận)"
            status_l = "✅ ĐÃ ĐẠT" if req_l_ok else f"🔴 Chưa đủ (Cấp hiện tại: Lv.{u_lvl}/20)"

            embed_stage2_quest = discord.Embed(
                title="🎯 NHIỆM VỤ YÊU CẦU STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ",
                description=(
                    "Không khí băng giá bao trùm mặt hồ, bạn cần tập luyện để chịu được giá rét trước khi chạm trán tiên nữ băng!\n\n"
                    f"• ⚔️ **Đánh `/battle` 6 lần:** **{status_b}**\n"
                    f"• ⭐ **Level tối thiểu 20:** **{status_l}**\n\n"
                    "🎁 **Phần thưởng:** **+10 Lượt Pull** 🎟️ & Mở khóa trận chiến với Cirno Ace 2!\n"
                    "💡 *Sau khi hoàn thành đủ, gõ lại `/story` để nhận thưởng và khai màn đại chiến!*"
                ),
                color=0x0284C7
            )
            embed_stage2_quest.set_thumbnail(url=CARDS_DATA[23]["image"])
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed_stage2_quest)
            else:
                await ctx_or_interaction.send(embed=embed_stage2_quest)
            return

        boss_lvl = st.get("cirno_boss_level") or player.get("level", 20)
        dialogue_text = (
            "• ❄️ **Cirno:** *\"Mục tiêu bị lạc đường đều là do tiên nữ làm cả đấy.\"*\n"
            "• ⛩️ **Reimu:** *\"Ồ, vậy à? Thế cô có thể chỉ đường cho tôi? Như là có hòn đảo nào quanh đây không?\"*\n"
            "• ❄️ **Cirno:** *\"Này, tỏ ra ngạc nhiên hơn chút đi chứ. Cô không thấy tôi là kẻ địch trước mắt sao?\"*\n"
            "• ⛩️ **Reimu:** *\"Mục tiêu á? Bất ngờ thật đấy.\"*\n"
            "• ❄️ **Cirno:** *\"Đừng có mà trêu ngươi ta!\"*\n"
            "• ❄️ **Cirno:** *\"Ta sẽ đóng băng ngươi thành đá với chút thịt bò kiểu Anh luôn!\"*\n\n"
            "⚠️ **CẢNH BÁO:** Cirno Ace 2 đã giải phóng toàn bộ ma pháp băng tuyết! Bấm nút bên dưới để bắt đầu trận Live Battle!"
        )

        embed_dialogue = discord.Embed(
            title="🗺️ STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ (LAKE SURFACE)",
            description=dialogue_text,
            color=0x06B6D4
        )
        embed_dialogue.set_thumbnail(url=CARDS_DATA[23]["image"])
        embed_dialogue.add_field(
            name="👺 Thông Số Boss Cirno Ace 2:",
            value=f"• Sức mạnh: **1,200 DMG** | Máu: **6,600 HP**\n• Cấp độ Boss: **Lv.{boss_lvl}** (Cố định lúc mở quest)\n• Tuyệt kỹ: **Perfect Freeze** (40% đóng băng)",
            inline=True
        )
        embed_dialogue.add_field(
            name="🎁 Phần Thưởng Chiến Thắng:",
            value="• 🎴 **30 Thẻ bài [#23] Cirno** cộng thẳng túi đồ\n• 🎟️ **+5 Lượt Pull** tích lũy",
            inline=True
        )
        view = StoryCirnoBattleView(user, player)
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed_dialogue, view=view)
        else:
            await ctx_or_interaction.send(embed=embed_dialogue, view=view)
        return

    else:
        embed_cleared = discord.Embed(
            title="🏆 BẠN ĐÃ VƯỢT QUA STAGE 2: BỀ MẶT HỒ SƯƠNG MÙ!",
            description=(
                "🌸 **\"Con nhóc hỗn xược bị Reimu và trợ thủ ném xuống hồ băng\"**\n\n"
                f"👤 Trợ thủ: {user.mention}\n"
                "✅ Bạn đã hạ gục Cirno Ace 2, nhận **30 Thẻ bài ID 23 (Cirno)** và **5 Vé Pull**!\n\n"
                "🏰 *Băng qua hồ nước đóng băng, cánh cổng Hồng Ma Quán sừng sững uy nghiêm đã hiện ra trước mắt...*\n"
                "🌟 **Stage 3 (Cổng Hồng Ma Quán - Hong Meiling) sẽ sớm cập bến trong bản cập nhật kế tiếp!**"
            ),
            color=0x10B981
        )
        embed_cleared.set_thumbnail(url=CARDS_DATA[23]["image"])
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed_cleared)
        else:
            await ctx_or_interaction.send(embed=embed_cleared)

# ==============================================================================
# LỆNH /PRESTIGE - CHUYỂN SINH RESET CẤP VÀ NHẬN VÉ PULL + TOKENS
# ==============================================================================
class PrestigeConfirmView(discord.ui.View):
    def __init__(self, user, player, p_info):
        super().__init__(timeout=90)
        self.user = user
        self.player = player
        self.p_info = p_info

    @discord.ui.button(label="👑 Xác Nhận Chuyển Sinh (Prestige)", style=discord.ButtonStyle.danger, emoji="⚡")
    async def confirm_prestige(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên chuyển sinh của bạn!", ephemeral=True)
            return

        cur_lvl = self.player.get("level", 1)
        req_lvl = self.p_info["req_lvl"]
        if cur_lvl < req_lvl:
            await interaction.response.send_message(f"❌ Bạn chưa đạt cấp độ yêu cầu! (Cần Lv.{req_lvl}, hiện tại Lv.{cur_lvl})", ephemeral=True)
            return

        for child in self.children: child.disabled = True
        
        old_p = self.player.get("prestige", 0)
        new_p = self.p_info["next_p"]
        old_tickets = self.player.get("pull_tickets", 0.0)

        self.player["prestige"] = new_p
        self.player["xp"] = 0
        self.player["level"] = 0
        self.player["pull_tickets"] = float(self.p_info["pulls"])
        self.player["tokens"] = self.player.get("tokens", 0) + self.p_info["tokens"]
        save_player(self.player)

        embed_success = discord.Embed(
            title=f"🎉 CHUYỂN SINH THÀNH CÔNG: CHÀO MỪNG ĐẾN PRESTIGE {new_p}!",
            description=(
                f"⛩️ **Chúc mừng {self.user.mention} đã đạt cảnh giới Chuyển Sinh mới!**\n\n"
                f"📊 **Cấp bậc mới:** `Prestige {new_p}` *(Trước: P{old_p})*\n"
                f"🔄 **Đặt lại cấp độ:** `Lv.0 (0 XP)`\n"
                f"🔓 **Mở giới hạn cấp tối đa:** Lên tới **Lv.{get_max_level(new_p)}**!\n"
                f"🎟️ **Làm mới kho Pull:** Thu hồi {old_tickets:.1f} vé cũ ➔ Cấp mới **+{int(self.p_info['pulls'])} Vé Pull**!\n"
                f"💎 **Thưởng Tokens:** **+{self.p_info['tokens']} Tokens** (Tổng kho: `{self.player['tokens']:,}` tokens)\n"
                f"⚡ **Đặc quyền mới:** Nhận **x{self.p_info['xp_mult']:g} XP Bonus** vĩnh viễn trong mọi trận chiến!"
            ),
            color=0xF59E0B
        )
        embed_success.set_thumbnail(url="https://c.tenor.com/gc4ws16CrTYAAAAC/reimu-touhou.gif")
        embed_success.set_footer(text="Dùng /token để mở Token Shop • Dùng /team để kiểm tra cấp độ mới")
        await interaction.response.edit_message(content=None, embed=embed_success, view=self)
        self.stop()

    @discord.ui.button(label="❌ Hủy Bỏ", style=discord.ButtonStyle.secondary)
    async def cancel_prestige(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên của bạn!", ephemeral=True)
            return
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content="🚫 Đã hủy thao tác chuyển sinh.", view=self)
        self.stop()

async def handle_prestige(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    cur_p = player.get("prestige", 0)
    cur_lvl = player.get("level", 1)
    p_info = get_prestige_info(cur_p)

    req_ok = cur_lvl >= p_info["req_lvl"]
    status_str = "🟢 **ĐỦ ĐIỀU KIỆN CHUYỂN SINH!**" if req_ok else f"🔴 **Chưa đủ cấp độ** (Cần Lv.{p_info['req_lvl']:,} • Hiện tại: Lv.{cur_lvl})"

    embed = discord.Embed(
        title=f"👑 HỆ THỐNG CHUYỂN SINH - PRESTIGE (HIỆN TẠI: P{cur_p})",
        description=(
            f"👤 **Người chơi:** {user.mention} • Cấp hiện tại: **Lv.{cur_lvl}**\n"
            f"⚡ **Quyền lợi hiện tại:** **x{get_prestige_xp_multiplier(cur_p):g} XP Bonus**\n"
            f"💎 **Tokens sở hữu:** **{player.get('tokens', 0):,}** tokens\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 **MỤC TIÊU TIẾP THEO: PRESTIGE {p_info['next_p']}**\n"
            f"• 🎯 **Yêu cầu:** Đạt tối thiểu **Cấp {p_info['req_lvl']}**\n"
            f"• 🎁 **Phần thưởng chuyển sinh:** **+{int(p_info['pulls'])} Vé Pull** 🎟️ & **+{p_info['tokens']} Tokens** 💎\n"
            f"• 🔓 **Phần thưởng mở giới hạn cấp:** Mở giới hạn lên **Lv.{get_max_level(p_info['next_p'])}**!\n"
            f"• ⚡ **Đặc quyền mở rộng:** Tăng hệ số nhận kinh nghiệm lên **x{p_info['xp_mult']:g} XP**!\n"
            f"• ⚠️ **Lưu ý cốt lõi:** Khi chuyển sinh, cấp độ sẽ đặt lại về **Lv.0** và **toàn bộ vé pull tích lũy cũ sẽ được làm mới** thành số vé thưởng mới!\n"
            f"• 📌 **Trạng thái:** {status_str}"
        ),
        color=0xF59E0B if req_ok else 0x3B82F6
    )
    embed.set_footer(text="Bấm 'Xác Nhận Chuyển Sinh' bên dưới để tiến hành!")
    view = PrestigeConfirmView(user, player, p_info)
    if not req_ok:
        view.children[0].disabled = True

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

# ==============================================================================
# HỆ THỐNG TOKEN SHOP - ĐỀN HAKUREI HOA ANH ĐÀO
# ==============================================================================
TOKEN_SHOP_BG = "https://media.discordapp.net/attachments/1549063334781911070/1554437905815048273/images.png?ex=6abce29c&is=6abb911c&hm=59c42e4441d97ef95d91b78093ac8bedb732a4d05addbc4eb3f78d46dbf31129&=&format=webp&quality=lossless"

class TokenBuyCardModal(discord.ui.Modal):
    def __init__(self, player, rank_target: str, cost_per_card: int):
        super().__init__(title=f"Đổi Thẻ Bậc {rank_target} ({cost_per_card} Token/Thẻ)")
        self.player = player
        self.rank_target = rank_target
        self.cost_per_card = cost_per_card

        self.card_input = discord.ui.TextInput(
            label="ID Thẻ hoặc Tên Nhân Vật:",
            placeholder="Ví dụ: 1 (Hecatia) hoặc 9 (Flandre)...",
            required=True,
            min_length=1,
            max_length=30
        )
        self.qty_input = discord.ui.TextInput(
            label="Số lượng thẻ muốn mua:",
            placeholder="Nhập số lượng (Ví dụ: 1, 2...)",
            default="1",
            required=True,
            min_length=1,
            max_length=3
        )
        self.add_item(self.card_input)
        self.add_item(self.qty_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw_cid = self.card_input.value.strip()
        cid = normalize_card_id(raw_cid)
        if not cid or cid not in CARDS_DATA:
            await interaction.response.send_message(f"❌ Không tìm thấy thẻ bài tương ứng với '{raw_cid}'!", ephemeral=True)
            return

        card = CARDS_DATA[cid]
        if card["rank"] != self.rank_target:
            await interaction.response.send_message(f"❌ Thẻ [{card['rank']}] #{card['id']} {card['name']} không thuộc bậc {self.rank_target}!", ephemeral=True)
            return

        try:
            qty = int(self.qty_input.value.strip())
            if qty <= 0: raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Số lượng thẻ phải là số nguyên dương!", ephemeral=True)
            return

        total_cost = self.cost_per_card * qty
        cur_tokens = self.player.get("tokens", 0)
        if cur_tokens < total_cost:
            await interaction.response.send_message(f"❌ Bạn không đủ tokens! (Cần {total_cost:,} tokens, hiện có {cur_tokens:,} tokens)", ephemeral=True)
            return

        self.player["tokens"] = cur_tokens - total_cost
        cid_str = str(card["id"])
        inv = self.player.setdefault("inventory", {})
        inv[cid_str] = inv.get(cid_str, 0) + qty
        if card["id"] not in self.player.get("unlocked_cards", []):
            self.player.setdefault("unlocked_cards", []).append(card["id"])
        save_player(self.player)

        embed = discord.Embed(
            title="🌸 GIAO DỊCH TOKEN SHOP THÀNH CÔNG!",
            description=(
                f"✨ Đã đổi thành công **+{qty}x [{card['rank']}] #{card['id']:02d} {card['name']}**!\n"
                f"📉 **Chi phí:** -{total_cost:,} Tokens\n"
                f"💎 **Số dư Tokens còn lại:** **{self.player['tokens']:,}** tokens\n"
                f"🎒 **Túi đồ hiện có:** `{inv[cid_str]}` lá"
            ),
            color=0x10B981
        )
        embed.set_thumbnail(url=card["image"])
        await interaction.response.send_message(embed=embed)

class TokenRandomModal(discord.ui.Modal):
    def __init__(self, player):
        super().__init__(title="Quay Random Thẻ SS-C (10 Token/Lượt)")
        self.player = player
        self.qty_input = discord.ui.TextInput(
            label="Số lượt quay random (1 - 50):",
            placeholder="Nhập số lượt...",
            default="1",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.qty_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.qty_input.value.strip())
            if qty <= 0 or qty > 50: raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Số lượt quay phải từ 1 đến 50!", ephemeral=True)
            return

        total_cost = 10 * qty
        cur_tokens = self.player.get("tokens", 0)
        if cur_tokens < total_cost:
            await interaction.response.send_message(f"❌ Bạn không đủ tokens! (Cần {total_cost:,} tokens, hiện có {cur_tokens:,} tokens)", ephemeral=True)
            return

        self.player["tokens"] = cur_tokens - total_cost
        results = []
        last_card = None

        for _ in range(qty):
            card, is_dup, conv, unlocked_from_lock = execute_single_pull(self.player)
            last_card = card
            dup_txt = f" *(Trùng! +{conv:.1f} vé)*" if is_dup else " ✨ **[MỚI]**"
            results.append(f"• `[#{card['id']:02d}]` **[{card['rank']}] {card['name']}**{dup_txt}")

        save_player(self.player)
        embed = discord.Embed(
            title=f"🎲 KẾT QUẢ QUAY RANDOM TỪ TOKEN SHOP ({qty} LƯỢT)",
            description="\n".join(results[:25]) + ("\n*(Còn nữa...)*" if len(results) > 25 else ""),
            color=0x8B5CF6
        )
        if last_card: embed.set_thumbnail(url=last_card["image"])
        embed.set_footer(text=f"Tiêu hao: {total_cost} Tokens • Số dư còn lại: {self.player['tokens']:,} Tokens")
        await interaction.response.send_message(embed=embed)

class TokenShopView(discord.ui.View):
    def __init__(self, user, player):
        super().__init__(timeout=180)
        self.user = user
        self.player = player

    @discord.ui.button(label="👑 Đổi Thẻ SS (50 Token)", style=discord.ButtonStyle.danger, emoji="💎", row=0)
    async def btn_buy_ss(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên shop của bạn!", ephemeral=True)
            return
        await interaction.response.send_modal(TokenBuyCardModal(self.player, "SS", 50))

    @discord.ui.button(label="⭐ Mua Thẻ S (20 Token)", style=discord.ButtonStyle.primary, emoji="✨", row=0)
    async def btn_buy_s(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên shop của bạn!", ephemeral=True)
            return
        await interaction.response.send_modal(TokenBuyCardModal(self.player, "S", 20))

    @discord.ui.button(label="🎲 Random Thẻ SS-C (10 Token)", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def btn_buy_rand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên shop của bạn!", ephemeral=True)
            return
        await interaction.response.send_modal(TokenRandomModal(self.player))
        
    @discord.ui.button(label="🪭 Mua Quạt Giấy Yukari (600 Token)", style=discord.ButtonStyle.secondary, emoji="🪭", row=1)
    async def btn_buy_fan(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Đây không phải phiên shop của bạn!", ephemeral=True)
            return
        cur_tokens = self.player.get("tokens", 0)
        if cur_tokens < 600:
            await interaction.response.send_message(f"❌ Bạn không đủ tokens! (Cần 600 tokens, hiện có {cur_tokens:,} tokens)", ephemeral=True)
            return
        self.player["tokens"] -= 600
        p_items = self.player.setdefault("items", {})
        p_items["quat_giay"] = p_items.get("quat_giay", 0) + 1
        save_player(self.player)
        await interaction.response.send_message(f"✅ Đã mua thành công **+1 Quạt Giấy 🪭**! (Số dư còn lại: `{self.player['tokens']:,}` Tokens)")

async def handle_token_shop(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    tokens = player.get("tokens", 0)
    prestige = player.get("prestige", 0)

    embed = discord.Embed(
        title="🌸 CỬA HÀNG TOKEN ĐỀN HAKUREI (HAKUREI TOKEN SHOP)",
        description=(
            f"Chào mừng **{user.display_name}** ghé thăm cửa hàng đền Hakurei mùa hoa anh nở rộ!\n\n"
            f"💎 **Số dư Tokens hiện có:** **`{tokens:,}` Tokens**\n"
            f"👑 **Cấp bậc Chuyển Sinh:** `Prestige {prestige}` *(Dùng `/prestige` để cày thêm Tokens)*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ **DANH MỤC VẬT PHẨM ĐỔI THƯỞNG:**\n\n"
            f"👑 **1. Đổi Thẻ Chỉ Định Bậc SS — 50 Tokens / 1 Lá**\n"
            f"   └ *Chọn 1 trong 4 vị thần: Hecatia (#1), Junko (#2), Okina (#3), Yukari (#4)*\n\n"
            f"⭐ **2. Mua Thẻ Chỉ Định Bậc S — 20 Tokens / 1 Lá**\n"
            f"   └ *Chọn Suika (#5), Eirin (#6), Yuuka (#7), Yuyuko (#8), Flandre (#9), Koishi (#10), Kaguya (#11), Remilia (#12), Utsuho (#13)*\n\n"
            f"🎲 **3. Rương May Mắn Random SS-C — 10 Tokens / 1 Lượt**\n"
            f"   └ *Quay ngẫu nhiên 1 lá bài bất kỳ từ bậc SS đến C*\n\n"
            f"🪭 **4. Bảo Vật Quạt Giấy Yukari — 600 Tokens / 1 Cái**\n"
            f"   └ *Vật phẩm dùng để tiến hóa [#04] Yukari Yakumo lên Ace 2 ⭐⭐*\n"
        ),
        color=0xF43F5E
    )
    embed.set_image(url=TOKEN_SHOP_BG)
    embed.set_footer(text="Bấm các nút bên dưới để mở bảng nhập số lượng và ID thẻ muốn đổi!")
    view = TokenShopView(user, player)

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

async def handle_help(ctx_or_interaction):
    desc = """
⛩️ **HAKUREI REIMU DISCORD BOT - BẢN ĐỒ LỆNH**

**🌸 TÂN THỦ & NHIỆM VỤ:**
• `/tutorial`: Khóa huấn luyện tân thủ (Thưởng 10 lượt pull, cấp 3 lượt pull 100% không trùng lá, không bao giờ ra thẻ SS, tiến trình 1 chiều).
• `/story`: Chế độ cốt truyện Touhou Story Mode (Hồng Ma Dị Biến - Stage 1: Rumia, Stage 2: Bề mặt Hồ Sương Mù vs Cirno Ace 2).
• `/prestige`: Hệ thống chuyển sinh (Reset Lv.0, nhận vé pull, tokens và nhân kinh nghiệm x2.0 - x10.0 XP, mở giới hạn cấp lên Lv.150, Lv.200, Lv.500+).
• `/token`: Mở Token Shop đền Hakurei (Đổi thẻ SS, S hoặc quay ngẫu nhiên bằng tokens).
• `/quest`: Xem 3/3 Nhiệm vụ Hàng Ngày (Nhận vé pull & thưởng lớn +10 lượt pull khi xong cả 3).

**🎮 GACHA, TIẾN HÓA & TRAO ĐỔI:**
• `/pull [số_lượng]`: Quay thẻ Touhou (Free 5 lượt/ngày). *Thẻ đã quay được sẽ mở khóa vĩnh viễn! Quay trúng lại thẻ bị lock sẽ mở khóa!*
• `/daily`: Điểm danh nhận 1 vé pull mỗi ngày.
• `/evol [id_hoac_ten]`: Tiến hóa Ace 2 ⭐⭐ (Buff +300 ATK, +300 HP, trừ thẻ sau khi evol):
  - [#15] Reimu (20 thẻ): Vô Tưởng Chuyển Sinh (40% miễn sát thương).
  - [#18] Sakuya (30 thẻ): Thời Gian Đóng Băng (40% stun đối thủ).
  - [#19] Marisa (25 thẻ): Master Spark (30% kích hoạt sát thương ×2.0 lần).
  - [#09] Flandre (30 thẻ): Ripples of 495 Years (25% xóa 50% HP đối thủ / 30% HP Boss Raid, 1 lần/trận).
  - [#12] Remilia (25 thẻ): Thương Đỏ Gungnir — THỤ ĐỘNG không cần kích hoạt: mọi đòn đánh +3% Máu Tối Đa (Max HP) mục tiêu, kèm GIF chiêu.
  - [#21] Reisen (40 thẻ): Red Eye Mind Explosion (25% kích hoạt 1 lần/trận): mục tiêu có 20% tự gây sát thương lên bản thân trong 4 turn (không dùng lên chính mình).
  - [#23] Cirno (60 thẻ): Perfect Freeze (40% kích hoạt 1 lần/trận): đóng băng khiến đối phương trong 2 turn tiếp có 45% không thể đánh trả, kèm GIF chiêu trực tiếp.
  - [#13] Utsuho Reiuji (30 thẻ): Nuclear Spell Card (30% kích hoạt): gây 3.0x sát thương & nung chảy mặt đất gây bỏng 2% Máu Tối Đa cho bài địch ra sân sau đó trong 3 turn, kèm GIF chiêu trực tiếp.
  - [#t1] Seiki Đệ Nhất Pháp Sư (Ace 2 - Điều kiện đặc biệt: Marisa, Reimu, Sakuya đều Ace 2 & 10 Mảnh Seiki):
    * Cleave: Thụ động 100% mọi đòn đánh thường +2% Máu Tối Đa mục tiêu!
    * Medicine Sign: 35% hồi 40% Máu Tối Đa bản thân, 1 lần/trận.
    * Fantasy Seal: Buff lên 50% miễn toàn bộ sát thương 1 hiệp (dạng Ace 2), 1 lần/trận.
    * Bóng Khái Niệm: 40% gây 15% Máu Tối Đa mục tiêu và lập tức xóa kỹ năng đối phương, 1 lần/trận.
• `/trade <user> [your] [their]`: Trao đổi thẻ bài (Cú pháp `your:tên:số_lượng` và `their:tên:số_lượng`, ví dụ: `your:reimu: 1 their:sakuya:12`, giao diện xác nhận 2 bên).
• `/team [hanh_dong] [id_the]`: Quản lý đội hình (view, add, remove). Mỗi cấp độ tăng +20 ATK và +25 HP buff!
• `/check [id_hoac_ten]`: Soi chi tiết sức mạnh, máu và kỹ năng của 28 nhân vật Touhou + thẻ đặc biệt [T] #t1 Seiki (gõ `seiki` hoặc `t1`, kèm Ace 2, có nút ◀ ▶ lướt danh sách, menu chọn nhanh và nút 🔮 xem thẻ T1).
• `/collection`: Xem 28 nhân vật Touhou (SS, S, A, B, C).

**⚔️ CHIẾN ĐẤU & BOSS RAID:**
• `/battle`: Giao đấu nhân vật nhận 50-100 XP (hồi chiêu 1 phút).
• `/pvp <người_chơi>`: Thách đấu người chơi khác trong server trận đại chiến 3v3 đỉnh cao.
• `/boss_status`: Kiểm tra hồi chiêu 15 phút của Boss Raid.
• **Thông tin chi tiết trận chiến**: Sau Battle, Raid và PvP luôn có nút **📜 Xem Chi Tiết Trận Chiến & GIF Kỹ Năng** để xem lại từng hiệp kèm GIF hoạt ảnh trực tiếp (không dùng link dẫn ra ngoài).

**👹 DỊ BIẾN REIMU DỊ HÌNH (LIVE COMBAT):**
• **Phase 1 (30k HP / 15k DMG):** Quà rơi: 10% 10 vé, 40% 5 vé, 50% 3 vé. Trận đấu phát sóng turn-by-turn trực tiếp!
• **Phase 2 Thức Tỉnh (50k HP / 22k DMG):** Tự động hồi sinh & hồi 100% HP mọi thẻ bài! Quà siêu cấp: 10% 20 vé, 40% 10 vé, 50% 5 vé!
**👹 DỊ BIẾN SEIKI DỊ HÌNH - DỊ TÀ ĐỆ NHẤT PHÁP SƯ (LIVE COMBAT 2 PHASE):**
• **Phase 1 (30k HP / 3k DMG chia đều):** Nội tại hồi 1.5% HP, Multi Master Spark (15%), Fantasy Seal (20%), Blitz Attack (20%). Quà: 10% 10 vé, 40% 5 vé, 50% 3 vé!
• **Phase 2 Thức Tỉnh (90k HP / 10k DMG chia đều):** Hồi sinh & hồi 100% HP mọi thẻ bài! Nội tại **Cleave (100%)**: +20% Máu tối đa mục tiêu! **Nuclear Spell Card (10%)**: 10K DMG toàn tiền tuyến! Quà: 10% 30 vé, 40% 20 vé, 50% 10 vé, 5% +1 Mảnh Seiki!
**👺 DỊ BIẾN BÁT ÁCH KIẾM THẦN TƯỚNG MAHORAGA (SINGLE PHASE - 90K HP):**
• **90,000 HP / 6,000 DMG (chia đều tiền tuyến):**
  - **The True Adapt (100% Thụ Động):** Mỗi hiệp tự hồi 3% HP tối đa (2,700 HP) & giảm 3% sát thương phải nhận (cộng dồn mỗi hiệp, tối đa 90%)!
  - **Thoái Ma Kiếm (25%):** Rút kiếm chém 6,000 DMG sát thương thuần lên MỘT mục tiêu duy nhất (không chia đều)!
• **Quà thanh tẩy:** 10% 20 vé, 40% 15 vé, 50% 10 vé (+100 XP), và 5% rơi +1 Mảnh Mahoraga (tích trữ cho Thẻ Mahoraga sắp ra mắt)!

**👑 LỆNH ADMIN (OWNER EXCLUSIVE - ID: 1502579398560317441):**
• `/admin_lock <user> <id_the>`: Niêm phong thẻ bài của người chơi (chỉ mở khi pull ra lại).
• `/admin_reset_quest [user]`: Làm mới thủ công 3/3 Nhiệm Vụ Ngày (hệ thống vốn tự động reset lúc 00:00 GMT+7).
• `/admin_set_level <user> <level>`: Đặt cấp độ và đồng bộ XP (+50 XP/cấp chuẩn xác theo Prestige).
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

@bot.tree.command(name="story", description="Tham gia chế độ cốt truyện Touhou Story Mode (Hồng Ma Dị Biến)")
async def slash_story(interaction: discord.Interaction):
    await handle_story(interaction)

@bot.command(name="story", aliases=["cotruyen"])
async def prefix_story(ctx):
    await handle_story(ctx)

# ==============================================================================
# ĐĂNG KÝ SLASH COMMANDS & PREFIX CHO PRESTIGE VÀ TOKEN SHOP
# ==============================================================================
@bot.tree.command(name="prestige", description="Hệ thống chuyển sinh: Reset về Lv.0, làm mới Pull, nhận Tokens & x2-10x XP")
async def slash_prestige(interaction: discord.Interaction):
    await handle_prestige(interaction)

@bot.command(name="prestige", aliases=["cs", "chuyensinh"])
async def prefix_prestige(ctx):
    await handle_prestige(ctx)

@bot.tree.command(name="token", description="Kiểm tra số dư Tokens và mở Cửa Hàng Đổi Thẻ SS/S/Random đền Hakurei")
async def slash_token(interaction: discord.Interaction):
    await handle_token_shop(interaction)

@bot.command(name="token", aliases=["tokens", "shop"])
async def prefix_token(ctx):
    await handle_token_shop(ctx)

@bot.tree.command(name="admin_token_add", description="[CHỦ BOT DUY NHẤT] Cấp Tokens cho người chơi hoặc bản thân")
@app_commands.describe(so_luong="Số lượng tokens cần cấp", nguoi_dung="Người nhận tokens (để trống nếu tự cấp)")
async def slash_admin_token_add(interaction: discord.Interaction, so_luong: int, nguoi_dung: Optional[discord.Member] = None):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Lệnh chỉ dành cho chủ sở hữu bot.", ephemeral=True)
        return
    if so_luong <= 0:
        await interaction.response.send_message("❌ Số lượng tokens phải lớn hơn 0!", ephemeral=True)
        return

    target = nguoi_dung or interaction.user
    target_player = get_player(target.id, target.display_name)
    target_player["tokens"] = target_player.get("tokens", 0) + so_luong
    save_player(target_player)

    embed = discord.Embed(
        title="💎 [ADMIN] ĐÃ CẤP TOKENS THÀNH CÔNG!",
        description=(
            f"👑 **Admin:** {interaction.user.mention}\n"
            f"👤 **Người nhận:** {target.mention}\n"
            f"➕ **Số lượng cấp:** **+{so_luong:,} Tokens**\n"
            f"💰 **Tổng số dư mới:** **{target_player['tokens']:,}** tokens"
        ),
        color=0x10B981
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name="admin_token_add", aliases=["addtoken", "givetoken"])
async def prefix_admin_token_add(ctx, so_luong: int, member: Optional[discord.Member] = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    if so_luong <= 0:
        await ctx.send("❌ Số lượng tokens phải lớn hơn 0!")
        return
    target = member or ctx.author
    target_player = get_player(target.id, target.display_name)
    target_player["tokens"] = target_player.get("tokens", 0) + so_luong
    save_player(target_player)
    await ctx.send(f"💎 Đã cấp **+{so_luong:,} Tokens** cho {target.mention} (Tổng: {target_player['tokens']:,} tokens)!")

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


# ==============================================================================
# HỆ THỐNG TOÀN DIỆN CHO PLAYER & ADMIN: /EVENT & /ITEM
# ==============================================================================

# --- VIEW NÚT MUA EVENT SHOP ---
class EventShopButtonsView(discord.ui.View):
    def __init__(self, player, user_id):
        super().__init__(timeout=120)
        self.player = player
        self.user_id = user_id

    @discord.ui.button(label="🎟️ 5 Vé Pull (50 Kẹo)", style=discord.ButtonStyle.primary)
    async def buy_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p_items = self.player.setdefault("items", {})
        candies = p_items.get("keo_halloween", 0)
        if candies < 50:
            await interaction.response.send_message("❌ Bạn không đủ Kẹo! (Cần 50 Kẹo)", ephemeral=True)
            return
        p_items["keo_halloween"] -= 50
        self.player["pull_tickets"] += 5.0
        save_player(self.player)
        await interaction.response.send_message(f"✅ Đã đổi thành công **+5 Vé Pull**! (Còn lại: {p_items['keo_halloween']} Kẹo)")

    @discord.ui.button(label="📦 Rương Ma Quái [E] (120 Kẹo)", style=discord.ButtonStyle.success)
    async def buy_chest(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p_items = self.player.setdefault("items", {})
        candies = p_items.get("keo_halloween", 0)
        if candies < 120:
            await interaction.response.send_message("❌ Bạn không đủ Kẹo! (Cần 120 Kẹo)", ephemeral=True)
            return
        p_items["keo_halloween"] -= 120
        p_items["ruong_halloween_e"] = p_items.get("ruong_halloween_e", 0) + 1
        save_player(self.player)
        await interaction.response.send_message(f"✅ Đã mua **+1 Rương Halloween Ma Quái [E]**! Dùng `/item use ruong_halloween_e` để mở.")

    @discord.ui.button(label="🩸 1 Mảnh Kizuna (200 Kẹo)", style=discord.ButtonStyle.danger)
    async def buy_shard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p_items = self.player.setdefault("items", {})
        candies = p_items.get("keo_halloween", 0)
        if candies < 200:
            await interaction.response.send_message("❌ Bạn không đủ Kẹo! (Cần 200 Kẹo)", ephemeral=True)
            return
        p_items["keo_halloween"] -= 200
        p_shards = self.player.setdefault("shards", {})
        p_shards["kizuna"] = p_shards.get("kizuna", 0) + 1
        save_player(self.player)
        await interaction.response.send_message(f"✅ Đã mua **+1 Mảnh Kizuna**! (Kho: {p_shards['kizuna']}/15 mảnh)")

# --- HÀM XỬ LÝ /EVENT INFO (XEM NHIỆM VỤ & THÔNG TIN EVENT) ---
async def handle_event_info(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    ep = player.setdefault("event_progress", {"battle": 0, "pvp": 0, "raid": 0, "event_raid": 0, "claimed": False})
    candies = player.get("items", {}).get("keo_halloween", 0)

    status_battle = "✅ ĐÃ HOÀN THÀNH" if ep.get("battle", 0) >= 100 else f"🔴 Đang làm ({ep.get('battle', 0)}/100)"
    status_pvp = "✅ ĐÃ HOÀN THÀNH" if ep.get("pvp", 0) >= 100 else f"🔴 Đang làm ({ep.get('pvp', 0)}/100)"
    status_raid = "✅ ĐÃ HOÀN THÀNH" if ep.get("raid", 0) >= 30 else f"🔴 Đang làm ({ep.get('raid', 0)}/30)"
    status_event_raid = "✅ ĐÃ HOÀN THÀNH" if ep.get("event_raid", 0) >= 30 else f"🔴 Đang làm ({ep.get('event_raid', 0)}/30)"

    embed = discord.Embed(
        title="🎃 HALLOWEEN EVENT 2026 - LỄ HỘI KẸO MA QUÁI",
        description=(
            f"🧙‍♀️ **{EVENT_CONFIG['quote']}**\n\n"
            f"📅 **Thời gian diễn ra:** `02/10/2026` ➔ `30/10/2026`\n"
            f"🍬 **Số Kẹo của bạn:** **`{candies:,}` Kẹo**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **TIẾN TRÌNH NHIỆM VỤ SỰ KIỆN (EVENT QUESTS):**\n"
            f"• ⚔️ **{EVENT_CONFIG['quests']['battle']['name']}:** {status_battle}\n"
            f"• 🥊 **{EVENT_CONFIG['quests']['pvp']['name']}:** {status_pvp}\n"
            f"• 👺 **{EVENT_CONFIG['quests']['raid']['name']}:** {status_raid}\n"
            f"• 🩸 **{EVENT_CONFIG['quests']['event_raid']['name']}:** {status_event_raid}\n\n"
            f"🎁 **PHẦN THƯỞNG HOÀN THÀNH 4/4 NHIỆM VỤ:**\n"
            f"• 🌟 **+1 Vật phẩm Thánh Lõi** (Dùng tiến hóa Kizuna lên Ace 2 ⭐⭐)\n"
            f"• 💎 **+250 Tokens**\n"
            f"• Trạng thái nhận quà: **{'✅ ĐÃ HOÀN THÀNH & NHẬN THƯỞNG!' if ep.get('claimed') else '⏳ Đang thực hiện'}**"
        ),
        color=0xF97316
    )
    embed.set_image(url=EVENT_CONFIG["banner"])
    embed.set_footer(text="Dùng /event shop để đổi Kẹo lấy quà • Dùng /event raid để mở phòng săn Boss!")
    
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

# --- HÀM XỬ LÝ /EVENT SHOP (ĐỔI KẸO LẤY VÉ, RƯƠNG [E], SHARD) ---
async def handle_event_shop(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    candies = player.get("items", {}).get("keo_halloween", 0)

    embed = discord.Embed(
        title="🍬 CỬA HÀNG KẸO HALLOWEEN (EVENT SHOP)",
        description=(
            f"Chào mừng **{user.display_name}** ghé thăm cửa hàng bí ngô ma quái của Marisa!\n\n"
            f"🍬 **Số Kẹo hiện có:** **`{candies:,}` Kẹo**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ **DANH MỤC ĐỔI THƯỞNG:**\n"
            f"1️⃣ **50 Kẹo:** Đổi **+5 Vé Pull** 🎟️\n"
            f"2️⃣ **120 Kẹo:** Đổi **+1 Rương Halloween Ma Quái [E]** 📦\n"
            f"3️⃣ **200 Kẹo:** Đổi **+1 Mảnh Kizuna** 🩸 (15 mảnh = 1 Thẻ [T] #t3 Kizuna)\n"
        ),
        color=0xF97316
    )
    embed.set_image(url=EVENT_CONFIG["banner"])
    embed.set_footer(text="Bấm các nút bên dưới để đổi vật phẩm trực tiếp!")
    view = EventShopButtonsView(player, user.id)

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

# --- HÀM XỬ LÝ /EVENT RAID (MỞ PHÒNG CHỜ 2 PHÚT CHO TẤT CẢ PLAYER) ---
async def handle_event_raid_open(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    now = time.time()
    last_t = player.get("last_event_raid_time", 0.0)

    is_adm = is_authorized_admin(user.id)
    if not is_adm and (now - last_t < 3600):
        rem = int(3600 - (now - last_t))
        msg = f"⏳ Bạn vừa triệu hồi Event Boss gần đây, vui lòng nghỉ ngơi thêm **{rem // 60} phút {rem % 60} giây** nữa!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    player["last_event_raid_time"] = now
    save_player(player)

    channel = ctx_or_interaction.channel
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(f"🎃 **{user.display_name}** đã kích hoạt nghi lễ mở phòng đại chiến **Event Boss Kizuna - Huyết Ma Đế**!", ephemeral=False)
    else:
        await ctx_or_interaction.send(f"🎃 **{user.display_name}** đã kích hoạt nghi lễ mở phòng đại chiến **Event Boss Kizuna - Huyết Ma Đế**!")

    await spawn_event_boss_raid(channel, user, is_admin=is_adm)

# --- HÀM XỬ LÝ /ITEM CHECK (XEM KHO VẬT PHẨM) ---
async def handle_item_check(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    p_items = player.get("items", {})

    lines = []
    for ik, iv in ITEMS_DATABASE.items():
        cnt = p_items.get(ik, 0)
        tag = " `[E - Có thể Dùng]`" if iv["usable"] else ""
        lines.append(f"• **{iv['name']}**{tag}: `{cnt}` cái\n  └ *{iv['desc']}*")

    embed = discord.Embed(
        title=f"🎒 KHO VẬT PHẨM (ITEMS) - {user.display_name.upper()}",
        description="\n\n".join(lines),
        color=0x3B82F6
    )
    embed.set_footer(text="Dùng /item use ruong_halloween_e để mở các vật phẩm có mác [E]")
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

# --- HÀM XỬ LÝ /ITEM USE (DÙNG ITEM [E]) ---
async def handle_item_use(ctx_or_interaction, item_id: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    player = get_player(user.id, user.display_name)
    p_items = player.setdefault("items", {})
    
    clean_id = item_id.strip().lower()
    if clean_id in ["ruong", "ruong_halloween", "ruong_halloween_e", "chest"]:
        clean_id = "ruong_halloween_e"

    cnt = p_items.get(clean_id, 0)
    if cnt <= 0:
        msg = f"❌ Bạn không có vật phẩm `{clean_id}` trong kho đồ!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if clean_id == "ruong_halloween_e":
        p_items[clean_id] -= 1
        roll = random.random()
        if roll < 0.50:
            t = random.randint(5, 15)
            player["pull_tickets"] += float(t)
            reward_txt = f"🎟️ **+{t} Vé Pull Tích Lũy**!"
        elif roll < 0.85:
            k = random.randint(50, 100)
            p_items["keo_halloween"] = p_items.get("keo_halloween", 0) + k
            reward_txt = f"🍬 **+{k} Kẹo Halloween**!"
        else:
            p_shards = player.setdefault("shards", {})
            p_shards["kizuna"] = p_shards.get("kizuna", 0) + 1
            reward_txt = f"🩸 **+1 Mảnh Kizuna** (Siêu Hiếm)!"

        save_player(player)
        embed = discord.Embed(
            title="🎁 MỞ RƯƠNG HALLOWEEN MA QUÁI [E] THÀNH CÔNG!",
            description=f"✨ **Phần thưởng mở ra:**\n{reward_txt}\n\n🎒 *Số rương còn lại: {p_items[clean_id]} cái.*",
            color=0x10B981
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    else:
        msg = f"⚠️ Vật phẩm `{clean_id}` không có tính năng sử dụng trực tiếp!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)

# --- HÀM XỬ LÝ /ITEM TRADE (TRAO ĐỔI ITEM GIỮA 2 PLAYER) ---
async def handle_item_trade(ctx_or_interaction, user: discord.Member, vat_pham: str, so_luong: int = 1):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    if user.id == author.id or user.bot:
        msg = "❌ Người nhận không hợp lệ! Không thể chuyển item cho bản thân hoặc Bot."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if so_luong <= 0:
        msg = "❌ Số lượng chuyển giao phải lớn hơn 0!"
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    p_a = get_player(author.id, author.display_name)
    p_b = get_player(user.id, user.display_name)
    inv_a = p_a.setdefault("items", {})
    inv_b = p_b.setdefault("items", {})

    clean_vp = vat_pham.strip().lower()
    if clean_vp in ["thanhloi", "thanh_loi", "core"]: clean_vp = "thanh_loi"
    elif clean_vp in ["keo", "candy", "keo_halloween"]: clean_vp = "keo_halloween"
    elif clean_vp in ["ruong", "ruong_halloween", "ruong_halloween_e"]: clean_vp = "ruong_halloween_e"

    if clean_vp not in ITEMS_DATABASE:
        msg = f"❌ Mã vật phẩm `{vat_pham}` không tồn tại! (Hợp lệ: `thanh_loi`, `keo_halloween`, `ruong_halloween_e`)."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    if inv_a.get(clean_vp, 0) < so_luong:
        item_name = ITEMS_DATABASE[clean_vp]["name"]
        msg = f"❌ Bạn không đủ số lượng để chuyển! (Cần {so_luong}x {item_name}, hiện chỉ có: {inv_a.get(clean_vp, 0)} cái)."
        if isinstance(ctx_or_interaction, discord.Interaction): await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else: await ctx_or_interaction.send(msg)
        return

    inv_a[clean_vp] -= so_luong
    inv_b[clean_vp] = inv_b.get(clean_vp, 0) + so_luong
    save_player(p_a)
    save_player(p_b)

    item_name = ITEMS_DATABASE[clean_vp]["name"]
    embed = discord.Embed(
        title="📦 GIAO DỊCH VẬT PHẨM (ITEM TRADE) THÀNH CÔNG!",
        description=(
            f"🤝 **{author.mention}** đã chuyển thành công **{so_luong}x {item_name}** cho **{user.mention}**!\n\n"
            f"• Kho của {author.display_name} còn lại: `{inv_a[clean_vp]}` cái\n"
            f"• Kho của {user.display_name} hiện có: `{inv_b[clean_vp]}` cái"
        ),
        color=0x10B981
    )
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

# ==============================================================================
# ĐĂNG KÝ SLASH COMMANDS VÀ PREFIX (CHO CẢ PLAYER & ADMIN)
# ==============================================================================

# 1. NHÓM LỆNH /EVENT (Gồm: /event info, /event shop, /event raid)
class EventGroup(app_commands.Group, name="event", description="Sự kiện Halloween Event 2026"):
    @app_commands.command(name="info", description="Xem nội dung và nhiệm vụ sự kiện Halloween 2026")
    async def slash_event_info_cmd(self, interaction: discord.Interaction):
        await handle_event_info(interaction)

    @app_commands.command(name="shop", description="Cửa hàng sự kiện Halloween đổi quà bằng Kẹo 🍬")
    async def slash_event_shop_cmd(self, interaction: discord.Interaction):
        await handle_event_shop(interaction)

    @app_commands.command(name="raid", description="Mở phòng chờ triệu hồi Event Boss Kizuna cho tất cả mọi người (Hồi chiêu 1 tiếng)")
    async def slash_event_raid_cmd(self, interaction: discord.Interaction):
        await handle_event_raid_open(interaction)

bot.tree.add_command(EventGroup())

# 2. NHÓM LỆNH /ITEM (Gồm: /item check, /item use, /item trade)
class ItemGroup(app_commands.Group, name="item", description="Quản lý kho vật phẩm, sử dụng [E] và trao đổi"):
    @app_commands.command(name="check", description="Kiểm tra kho đồ vật phẩm của bạn")
    async def slash_item_check_cmd(self, interaction: discord.Interaction):
        await handle_item_check(interaction)

    @app_commands.command(name="use", description="Sử dụng vật phẩm có mác [E] trong kho đồ")
    @app_commands.describe(item_id="Mã vật phẩm muốn dùng")
    @app_commands.choices(item_id=[
        app_commands.Choice(name="Rương Halloween Ma Quái [E] (ruong_halloween_e)", value="ruong_halloween_e")
    ])
    async def slash_item_use_cmd(self, interaction: discord.Interaction, item_id: str):
        await handle_item_use(interaction, item_id)

    @app_commands.command(name="trade", description="Trao đổi vật phẩm (Items) với người chơi khác")
    @app_commands.describe(user="Người chơi nhận", vat_pham="Mã vật phẩm", so_luong="Số lượng")
    @app_commands.choices(vat_pham=[
        app_commands.Choice(name="Thánh Lõi", value="thanh_loi"),
        app_commands.Choice(name="Kẹo Halloween", value="keo_halloween"),
        app_commands.Choice(name="Rương Halloween [E]", value="ruong_halloween_e"),
        app_commands.Choice(name="Quạt Giấy 🪭 (quat_giay)", value="quat_giay")
    ])
    async def slash_item_trade_cmd(self, interaction: discord.Interaction, user: discord.Member, vat_pham: str, so_luong: int = 1):
        await handle_item_trade(interaction, user, vat_pham, so_luong)

bot.tree.add_command(ItemGroup())

# 3. LỆNH ADMIN (OWNER EXCLUSIVE)
class EventAdminGroup(app_commands.Group, name="event_admin", description="[Admin] Quản trị sự kiện Halloween Event"):
    @app_commands.command(name="start", description="[Admin] Bật sự kiện Halloween Event 2026")
    async def slash_admin_event_start(self, interaction: discord.Interaction):
        if not is_authorized_admin(interaction.user.id):
            await interaction.response.send_message("⛔ Không có quyền!", ephemeral=True)
            return
        EVENT_CONFIG["active"] = True
        await interaction.response.send_message("🎃 **Đã BẬT sự kiện Halloween Event 2026!**")

    @app_commands.command(name="end", description="[Admin] Đóng sự kiện Halloween Event 2026")
    async def slash_admin_event_end(self, interaction: discord.Interaction):
        if not is_authorized_admin(interaction.user.id):
            await interaction.response.send_message("⛔ Không có quyền!", ephemeral=True)
            return
        EVENT_CONFIG["active"] = False
        await interaction.response.send_message("🚫 **Đã ĐÓNG sự kiện Halloween Event 2026!**")

bot.tree.add_command(EventAdminGroup())

@bot.tree.command(name="admin_event_boss_spawn", description="[Admin] Cưỡng chế mở phòng triệu hồi Event Boss Kizuna ngay lập tức")
async def slash_admin_event_boss_spawn(interaction: discord.Interaction):
    if not is_authorized_admin(interaction.user.id):
        await interaction.response.send_message("⛔ Không có quyền!", ephemeral=True)
        return
    await interaction.response.send_message("⚡ Đang cưỡng chế mở phòng triệu hồi Event Boss Kizuna...", ephemeral=True)
    await spawn_event_boss_raid(interaction.channel, interaction.user, is_admin=True)

# 4. HỖ TRỢ LỆNH PREFIX (!EVENT & !ITEM)
@bot.group(name="event", invoke_without_command=True)
async def prefix_event_group(ctx):
    await handle_event_info(ctx)

@prefix_event_group.command(name="shop")
async def prefix_event_shop(ctx):
    await handle_event_shop(ctx)

@prefix_event_group.command(name="raid")
async def prefix_event_raid(ctx):
    await handle_event_raid_open(ctx)

@prefix_event_group.command(name="info")
async def prefix_event_info(ctx):
    await handle_event_info(ctx)

@bot.group(name="item", invoke_without_command=True)
async def prefix_item_group(ctx):
    await handle_item_check(ctx)

@prefix_item_group.command(name="check")
async def prefix_item_check(ctx):
    await handle_item_check(ctx)

@prefix_item_group.command(name="use")
async def prefix_item_use(ctx, item_id: str = "ruong_halloween_e"):
    await handle_item_use(ctx, item_id)

@prefix_item_group.command(name="trade")
async def prefix_item_trade(ctx, user: discord.Member = None, vat_pham: str = "keo_halloween", so_luong: int = 1):
    if not user:
        await ctx.send("❌ Vui lòng gắn thẻ người nhận! Ví dụ: `!item trade @User keo_halloween 50`")
        return
    await handle_item_trade(ctx, user, vat_pham, so_luong)

# ==============================================================================
# LỆNH ADMIN: /ADMIN_GIVE ITEM & PREFIX !ADMIN_GIVE ITEM / !GIVEITEM
# ==============================================================================
class AdminGiveGroup(app_commands.Group, name="admin_give", description="[CHỦ BOT DUY NHẤT] Cấp thẻ, mảnh hoặc vật phẩm Item"):
    @app_commands.command(name="item", description="[CHỦ BOT DUY NHẤT] Cấp vật phẩm thuộc nhóm Item cho người chơi")
    @app_commands.describe(
        vat_pham="Chọn vật phẩm cần cấp",
        so_luong="Số lượng cần cấp (mặc định: 1)",
        nguoi_dung="Người nhận (để trống nếu tự cấp cho bản thân)"
    )
    @app_commands.choices(vat_pham=[
        app_commands.Choice(name="Thánh Lõi (thanh_loi)", value="thanh_loi"),
        app_commands.Choice(name="Kẹo Halloween 🍬 (keo_halloween)", value="keo_halloween"),
        app_commands.Choice(name="Rương Halloween Ma Quái [E] (ruong_halloween_e)", value="ruong_halloween_e"),
        app_commands.Choice(name="Quạt Giấy 🪭", value="quat_giay")
    ])
    async def slash_admin_give_item(self, interaction: discord.Interaction, vat_pham: str, so_luong: int = 1, nguoi_dung: Optional[discord.Member] = None):
        if not is_authorized_admin(interaction.user.id):
            await interaction.response.send_message("⛔ **TỪ CHỐI QUYỀN TRUY CẬP!** Lệnh chỉ dành riêng cho Admin.", ephemeral=True)
            return
        
        if so_luong <= 0:
            await interaction.response.send_message("❌ Số lượng cấp phải lớn hơn 0!", ephemeral=True)
            return

        target = nguoi_dung or interaction.user
        target_player = get_player(target.id, target.display_name)
        p_items = target_player.setdefault("items", {})
        p_shards = target_player.setdefault("shards", {})

        p_items[vat_pham] = p_items.get(vat_pham, 0) + so_luong
        if vat_pham == "thanh_loi":
            p_shards["thanh_loi"] = p_items["thanh_loi"]

        save_player(target_player)

        item_name = ITEMS_DATABASE.get(vat_pham, {}).get("name", vat_pham)
        embed = discord.Embed(
            title="🎁 [ADMIN] ĐÃ CẤP VẬT PHẨM (ITEM) THÀNH CÔNG!",
            description=(
                f"👑 **Admin thực hiện:** {interaction.user.mention}\n"
                f"👤 **Người nhận:** {target.mention}\n"
                f"📦 **Vật phẩm:** **{item_name}** (`{vat_pham}`)\n"
                f"➕ **Số lượng cấp:** **+{so_luong:,}** cái\n"
                f"🎒 **Tổng số lượng trong kho:** **`{p_items[vat_pham]:,}`** cái"
            ),
            color=0x10B981
        )
        await interaction.response.send_message(embed=embed)

bot.tree.add_command(AdminGiveGroup())

# Lệnh Prefix thay thế cho Admin: !admin_give item hoặc !giveitem
@bot.group(name="admin_give", invoke_without_command=True)
async def prefix_admin_give_group(ctx):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return
    await ctx.send("💡 Cú pháp: `!admin_give item <thanh_loi|keo_halloween|ruong_halloween_e> [số_lượng] [@User]`")

@prefix_admin_give_group.command(name="item")
async def prefix_admin_give_item(ctx, vat_pham: str = "thanh_loi", so_luong: int = 1, member: Optional[discord.Member] = None):
    if not is_authorized_admin(ctx.author.id):
        await ctx.send("⛔ Từ chối quyền truy cập! Lệnh dành riêng cho chủ bot.")
        return

    if so_luong <= 0:
        await ctx.send("❌ Số lượng phải lớn hơn 0!")
        return

    clean_vp = vat_pham.strip().lower()
    if clean_vp in ["thanhloi", "thanh_loi", "core", "loi"]: clean_vp = "thanh_loi"
    elif clean_vp in ["keo", "candy", "keo_halloween"]: clean_vp = "keo_halloween"
    elif clean_vp in ["ruong", "ruong_halloween", "ruong_halloween_e"]: clean_vp = "ruong_halloween_e"

    if clean_vp not in ITEMS_DATABASE:
        await ctx.send(f"❌ Mã vật phẩm `{vat_pham}` không tồn tại! (Hợp lệ: `thanh_loi`, `keo_halloween`, `ruong_halloween_e`)")
        return

    target = member or ctx.author
    target_player = get_player(target.id, target.display_name)
    p_items = target_player.setdefault("items", {})
    p_shards = target_player.setdefault("shards", {})

    p_items[clean_vp] = p_items.get(clean_vp, 0) + so_luong
    if clean_vp == "thanh_loi":
        p_shards["thanh_loi"] = p_items["thanh_loi"]

    save_player(target_player)
    item_name = ITEMS_DATABASE[clean_vp]["name"]
    await ctx.send(f"🎁 Đã cấp **+{so_luong:,}x {item_name}** cho {target.mention}! (Tổng kho: `{p_items[clean_vp]:,}` cái)")


import sys

def start_bot_safely():
    retry_delay = 60
    while True:
        try:
            print("🔄 [SYSTEM] Đang kết nối tới Discord Gateway...", flush=True)
            bot.run(DISCORD_TOKEN, reconnect=True)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(
                    f"🚨 [RATE LIMIT 429] IP của Render đang bị Discord chặn tạm thời!\n"
                    f"⏳ Đang tạm nghỉ {retry_delay} giây trước khi thử lại...",
                    flush=True
                )
                time.sleep(retry_delay)
                retry_delay = min(900, int(retry_delay * 1.5))
            else:
                print(f"⚠️ [HTTP ERROR] Mã lỗi {e.status}: {e}. Khởi động lại sau 30s...", flush=True)
                time.sleep(30)
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"❌ [CRASH] Bot bị ngắt kết nối ({e}). Đang khởi động lại sạch sẽ sau 15s...", flush=True)
            time.sleep(15)
            os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ LỖI: Chưa cấu hình DISCORD_TOKEN trong .env!", flush=True)
    else:
        start_bot_safely()
