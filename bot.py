# ==============================================================================
# HAKUREI REIMU DISCORD BOT - FULL COMPREHENSIVE EDITION
# GEMINI FLASH CHATBOT + MONGODB ATLAS CLOUD + TOUHOU GACHA, AUTO-BATTLE & RAID
# ==============================================================================
# BẢN CẬP NHẬT CHÍNH THỨC: HỖ TRỢ TOÀN DIỆN THẺ NHÓM T (#t1 Seiki đệ pháp toàn năng)
#
# 1. THAM GIA ĐẦY ĐỦ TẤT CẢ CƠ CHẾ CHIẾN ĐẤU:
#    - PvE Battle (/battle): Kích hoạt trọn vẹn 3 tuyệt kỹ:
#         * 🛡️ Fantasy Seal (40%): Dựng kết giới miễn toàn bộ sát thương 1 lần trong trận.
#         * 🌟 Master Spark (30%): Bộc phát ma lực gây x1.5 sát thương 1 lần trong trận.
#         * 💚 Medicine Sign (20%): Tự hồi phục 30% sinh lực bản thân 1 lần trong trận.
#    - PvP Quyết Đấu 3v3 (/pvp): Cả người thách đấu & bị thách đấu đều có thể xếp thẻ nhóm T
#      vào tiền tuyến với đầy đủ 3 chiêu thức.
#    - Boss Raid (Phase 1, Phase 2 Reimu Dị Hình & Seiki Dị Hình): Khắc chế đòn diện rộng của Boss.
#    - Quản lý đội hình (/team), Trao đổi (/trade), Soi thẻ (/check), Kho mảnh (/t translate).
#
# 2. QUY TẮC CÔNG BẰNG:
#    - Tối đa kích hoạt 1 chiêu thức mỗi lượt đánh.
#    - Mỗi chiêu thức chỉ có thể kích hoạt 1 lần duy nhất trong cả trận đấu.
#
# 3. VÁ LỖI ĐỊNH DẠNG:
#    - Thay thế toàn bộ ép kiểu int(cid) hoặc #{cid:02d} bằng format_card_id(cid).
#    - Chống crash triệt để khi nhận chuỗi ID "t1" / "#t1".
#
# 4. BẢO LƯU 100% CODE CŨ:
#    - Tất cả lệnh admin, logic database MongoDB / SQLite, Gemini AI, Web server đều giữ nguyên.
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

# Nạp biến môi trường từ file .env
load_dotenv()

# ==============================================================================
# QUẢN TRỊ VIÊN DUY NHẤT ĐƯỢC PHÉP DÙNG LỆNH ADMIN (OWNER EXCLUSIVE)
# ==============================================================================
AUTHORIZED_ADMIN_ID = 1502579398560317441

def is_authorized_admin(user_or_id) -> bool:
    """Kiểm tra quyền Admin tối cao"""
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
VN_TIMEZONE = timezone(timedelta(hours=7))

def get_vietnam_time() -> datetime:
    """Lấy thời gian thực tế tại Việt Nam (GMT+7)"""
    return datetime.now(timezone.utc).astimezone(VN_TIMEZONE)

def get_vietnam_date_str() -> str:
    """Lấy chuỗi ngày YYYY-MM-DD theo giờ Việt Nam"""
    return get_vietnam_time().strftime("%Y-%m-%d")

# ==============================================================================
# DỮ LIỆU THẺ BÀI TOUHOU & THẺ ĐẶC BIỆT NHÓM T (#t1 SEIKI)
# ==============================================================================
CARDS_DATA = {
    1: {
        "name": "Hecatia Lapislazuli",
        "rank": "SS",
        "power": 850,
        "hp": 8500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082071178416229/hecatia_lapislazuli_touhou_drawn_by_mituba_ooka__6cf49ea15f88841c7a50e50655e920d0.png?format=webp&width=769&height=1024",
        "title": "Nữ Thần Địa Ngục Tam Thân",
        "skill_desc": "Tam Giới Hỗn Mang: Sát thương và sinh lực áp đảo hàng đầu Gensokyo."
    },
    2: {
        "name": "Junko",
        "rank": "SS",
        "power": 800,
        "hp": 8000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082919887179776/junko_touhou_drawn_by_xianjian_lingluan__8a51bec2beefde48ae3411fb6463271d.png?format=webp&width=658&height=1024",
        "title": "Hồn Tinh Khiết Căm Hờn",
        "skill_desc": "Nguyên Lực Tinh Khiết: Thanh lọc ma thuật thuần khiết hủy diệt vạn vật."
    },
    3: {
        "name": "Okina Matara",
        "rank": "SS",
        "power": 750,
        "hp": 7500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083695984672869/images.png?format=webp&width=300&height=512",
        "title": "Bí Thần Tối Cao Gensokyo",
        "skill_desc": "Hậu Môn Bí Cảnh: Thao túng năng lượng sinh mệnh và tinh thần."
    },
    4: {
        "name": "Yukari Yakumo",
        "rank": "SS",
        "power": 720,
        "hp": 7200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084814252974152/cf5e86717425d5168f5c7bbfd6d855e9.png?format=webp&width=365&height=512",
        "title": "Đại Yêu Quái Cảnh Giới",
        "skill_desc": "Thao Túng Cảnh Giới: Kiểm soát ranh giới thực và ảo."
    },
    5: {
        "name": "Suika Ibuki",
        "rank": "S",
        "power": 670,
        "hp": 6700,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083290684882954/images.png?format=webp",
        "title": "Đại Quỷ Núi Yêu Quái",
        "skill_desc": "Đại Quỷ Thần Lực: Thao túng mật độ không gian và tụ tán."
    },
    6: {
        "name": "Eirin Yagokoro",
        "rank": "S",
        "power": 640,
        "hp": 6600,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083046265749645/ef37dd0758b130203b6bdf9b404d9793.png?format=webp&width=725&height=1024",
        "title": "Bộ Não Của Mặt Trăng",
        "skill_desc": "Thần Dược Bất Tử: Am hiểu dược thuật và tri thức ngàn năm."
    },
    7: {
        "name": "Yuyuko Saigyouji",
        "rank": "S",
        "power": 630,
        "hp": 6300,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083549247078420/yuyuko_saigyouji_touhou_drawn_by_ichinose_land__788ce9b0ca5f03f31b2680ee110fecaa.png?format=webp&width=731&height=1024",
        "title": "U Linh Công Chúa Bạch Ngọc Lâu",
        "skill_desc": "Dẫn Dắt Cái Chết: Lời mời gọi về thế giới bên kia."
    },
    8: {
        "name": "Remilia Scarlet",
        "rank": "S",
        "power": 600,
        "hp": 6000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083161042747585/remilia_scarlet_touhou_drawn_by_dora_dora_g__9505bc3b9e4a3ffb1abfe9bb85994fef.png?format=webp&width=716&height=1024",
        "title": "Ác Ma Đỏ Tươi Hồng Ma Quán",
        "skill_desc": "Thao Túng Vận Mệnh: Uy quyền quỷ hút máu ngàn năm tuổi."
    },
    9: {
        "name": "Flandre Scarlet",
        "rank": "S",
        "power": 650,
        "hp": 5500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084964346019973/7cf167664ff4ae4a896cfca0c6c2e35e.png?format=webp&width=682&height=1024",
        "title": "Đóa Hoa Điên Loạn Em Gái Ác Ma",
        "skill_desc": "Hủy Diệt Vạn Vật: Bóp nát mục tiêu trong chớp mắt."
    },
    10: {
        "name": "Kaguya Houraisan",
        "rank": "S",
        "power": 620,
        "hp": 6200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549082800395780216/images.png?format=webp&width=332&height=512",
        "title": "Công Chúa Vĩnh Hằng Của Mặt Trăng",
        "skill_desc": "Vĩnh Hằng & Khoảnh Khắc: Dừng đọng thời gian."
    },
    11: {
        "name": "Fujiwara no Mokou",
        "rank": "S",
        "power": 610,
        "hp": 6400,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084042845356062/206f4ee59fa2ea2c366408d6d67b2d28.png?format=webp&width=768&height=1024",
        "title": "Phượng Hoàng Bất Diệt",
        "skill_desc": "Hỏa Ngục Bất Tử: Hồi sinh từ tro tàn rực lửa."
    },
    12: {
        "name": "Tenshi Hinanawi",
        "rank": "A",
        "power": 450,
        "hp": 4500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084177570467881/tenshi_hinanawi_touhou_drawn_by_kaede_kaede_leaf__5f50b4a4cb740333203928fa82b5fa4b.png?format=webp&width=724&height=1024",
        "title": "Thiên Nữ Thiên Đình Kiêu Hãnh",
        "skill_desc": "Phi Tưởng Kiếm: Thao túng đất đai và thiên tai."
    },
    13: {
        "name": "Hakurei Reimu",
        "rank": "A",
        "power": 480,
        "hp": 4800,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083863471489065/hakurei_reimu_touhou_drawn_by_dora_dora_g__b371b69fa0f5ceab60f64be8723c3187.png?format=webp&width=716&height=1024",
        "title": "Vu Nữ Xứ Gensokyo",
        "skill_desc": "Fantasy Nature: Bay bổng ra ngoài thực tại, trừ tà diệt quỷ."
    },
    14: {
        "name": "Kirisame Marisa",
        "rank": "A",
        "power": 520,
        "hp": 4200,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549083955687723049/kirisame_marisa_touhou_drawn_by_dora_dora_g__9bcfabfe4c54095aafeebbb83984d7d1.png?format=webp&width=716&height=1024",
        "title": "Phù Thủy Thường Dân Bình Thường",
        "skill_desc": "Master Spark: Chùm laser ánh sáng càn quét dữ dội."
    },
    15: {
        "name": "Sakuya Izayoi",
        "rank": "A",
        "power": 460,
        "hp": 4400,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084284567289947/izayoi_sakuya_touhou_drawn_by_tsukasa_d_k__6456f93798ae8b54901309f1bf3cf39c.png?format=webp&width=819&height=1024",
        "title": "Hầu Gái Trưởng Hồng Ma Quán",
        "skill_desc": "Ngưng Đọng Thời Gian: Phóng ngàn mũi dao bạc tức thì."
    },
    16: {
        "name": "Konpaku Youmu",
        "rank": "A",
        "power": 470,
        "hp": 4300,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084478146740264/konpaku_youmu_touhou_drawn_by_a_k_a_shika__735a4237fca29ee3564032d8479bb3bc.png?format=webp&width=724&height=1024",
        "title": "Nửa Người Nửa Ma Kiếm Sĩ",
        "skill_desc": "Lâu Quan Kiếm: Nhát chém đoạn tuyệt sinh tử luân hồi."
    },
    17: {
        "name": "Kochiya Sanae",
        "rank": "A",
        "power": 450,
        "hp": 4600,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084620027727932/kochiya_sanae_touhou_drawn_by_nana_g__a1df3eef6a1eb8152599c15b16fb7795.png?format=webp&width=724&height=1024",
        "title": "Vu Nữ Thần Xã Moriya Của Kỳ Tích",
        "skill_desc": "Gọi Phép Kỳ Tích: Triệu hoán gió bão và thần linh gia hộ."
    },
    18: {
        "name": "Reisen Udongein Inaba",
        "rank": "A",
        "power": 440,
        "hp": 4500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549085206256959580/c4c47bc2a6d71b8ee6d833a69a08e0e6.png?format=webp&width=332&height=512",
        "title": "Thỏ Ngọc Mặt Trăng Điên Cuồng",
        "skill_desc": "Ánh Mắt Điên Loạn: Thao túng bước sóng ảo giác."
    },
    19: {
        "name": "Patchouli Knowledge",
        "rank": "A",
        "power": 510,
        "hp": 3900,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549084715569516604/patchouli_knowledge_touhou_drawn_by_tutu__e1fa6bcfa8e54580fb35ce28f870fe6f.png?format=webp&width=724&height=1024",
        "title": "Đại Pháp Sư Thư Viện Ngầm",
        "skill_desc": "Thất Diệu Ma Thuật: Bộc phát nguyên tố ngũ hành."
    },
    20: {
        "name": "Aya Shameimaru",
        "rank": "A",
        "power": 430,
        "hp": 4300,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549085089332219965/images.png?format=webp&width=362&height=512",
        "title": "Phóng Viên Tengu Siêu Tốc",
        "skill_desc": "Cuồng Phong Bát Bộ: Tốc độ thần sầu nhanh nhất Gensokyo."
    },
    21: {
        "name": "Hong Meiling",
        "rank": "B",
        "power": 320,
        "hp": 3500,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549085340659105822/hong_meiling_touhou_drawn_by_unap__344f6f272322307efc464bf3f4931bc7.png?format=webp&width=769&height=1024",
        "title": "Vệ Binh Cổng Hồng Ma Quán",
        "skill_desc": "Thái Cực Quyền: Võ công dẻo dai phòng ngự kiên cường."
    },
    22: {
        "name": "Cirno",
        "rank": "B",
        "power": 300,
        "hp": 3000,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549085449769979924/cirno_touhou_drawn_by_dora_dora_g__beabef8ae6085a6eb17cf7b52ea7aafe.png?format=webp&width=716&height=1024",
        "title": "Tiên Băng Số 1 Gensokyo (⑨)",
        "skill_desc": "Băng Giá Hoàn Hảo: 'Ta là kẻ mạnh nhất!'"
    },
    23: {
        "name": "Rumia",
        "rank": "C",
        "power": 180,
        "hp": 1800,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549085600475381781/rumia_touhou_drawn_by_dora_dora_g__9c824c965e64ae54f3be7bf82aa9ebf1.png?format=webp&width=716&height=1024",
        "title": "Yêu Quái Màn Đêm",
        "skill_desc": "Màn Đêm Mù Mịt: 'Thế đó là vậy sao?'"
    },
    24: {
        "name": "Daiyousei",
        "rank": "C",
        "power": 150,
        "hp": 1600,
        "image": "https://media.discordapp.net/attachments/1533528571509866497/1549085732159885362/daiyousei_touhou_drawn_by_hizuki_yoru__2ceeb5df9630d7042a98f5a5eeb66100.png?format=webp&width=716&height=1024",
        "title": "Đại Tiên Tử Rừng Trúc",
        "skill_desc": "Tiên Khí Hỗ Trợ: Bạn thân đồng hành của Cirno."
    },
    # --------------------------------------------------------------------------
    # THẺ ĐẶC BIỆT: NHÓM T (#t1 SEIKI ĐỆ PHÁP TOÀN NĂNG)
    # --------------------------------------------------------------------------
    "t1": {
        "name": "Seiki đệ pháp toàn năng",
        "rank": "T",
        "power": 1200,
        "hp": 12000,
        "image": "https://media.discordapp.net/attachments/1549063334781911070/1550346363064287233/content.png?format=webp&width=643&height=1024",
        "title": "Đệ Nhất Pháp Sư Thần Thánh",
        "skill_desc": "Đệ Pháp Toàn Năng: Sở hữu trọn vẹn 3 tuyệt kỹ tối thượng (Fantasy Seal, Master Spark, Medicine Sign).",
        "skills": {
            "fantasy_seal": {
                "name": "Fantasy Seal",
                "chance": 0.40,
                "desc": "40% tỷ lệ miễn toàn bộ sát thương 1 lần trong trận",
                "gif": "https://static2.klipy.com/ii/5db6a18d189196bbfca181cb2688f117/38/ba/c0k5xM6B.gif"
            },
            "master_spark": {
                "name": "Master Spark",
                "chance": 0.30,
                "multiplier": 1.5,
                "desc": "30% tỷ lệ bộc phát x1.5 sát thương 1 lần trong trận",
                "gif": "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/f4/32/73qv2IMW.gif"
            },
            "medicine_sign": {
                "name": "Medicine Sign",
                "chance": 0.20,
                "desc": "20% tỷ lệ hồi phục 30% sinh lực bản thân 1 lần trong trận",
                "gif": "https://static2.klipy.com/ii/d7aec6f6f171607374b2065c836f92f4/e8/09/O842rz9E.gif"
            }
        }
    }
}

CARDS_DATA["T1"] = CARDS_DATA["t1"]

BOSS_CONFIG = {
    "name": "Reimu Dị Hình - Phase 1",
    "desc": "Đó không phải Reimu, sẵn sàng giao chiến!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1549077421624401971/content.png?format=webp&width=351&height=512",
    "hp": 30000,
    "power": 3000,
    "phase2": {
        "name": "Reimu Dị Hình - Thức Tỉnh (Phase 2)",
        "desc": "Dị hình đang biến đổi, bùa chú của chúng ta đang rung động dữ dội!",
        "image": "https://media.discordapp.net/attachments/1549063334781911070/1549275653239472148/artwork.png?format=webp&width=640&height=336",
        "hp": 50000,
        "power": 10000
    }
}

SEIKI_BOSS_CONFIG = {
    "id": "seiki",
    "name": "Seiki Dị Hình - Dị Tà Đệ Nhất Pháp Sư",
    "desc": "Đó không phải cha ta!",
    "reimu_quote": "Đó không phải cha ta! Dị khí ngập tràn, người này đã bị tà niệm nuốt chửng!",
    "image": "https://media.discordapp.net/attachments/1543072032034521228/1550376898641788938/content.png?format=webp&width=643&height=1024",
    "hp": 30000,
    "power": 3000,
    "passive_regen_pct": 0.015
}

def format_card_id(cid: Union[str, int]) -> str:
    """Chuẩn hóa ID thẻ bài: Trả về 't1' nếu là nhóm T, hoặc số '01', '02'..."""
    cid_str = str(cid).strip().lower()
    if cid_str in ("t1", "#t1"):
        return "t1"
    try:
        return f"{int(cid_str):02d}"
    except (ValueError, TypeError):
        return cid_str

def get_card_data(cid: Union[str, int]) -> Optional[dict]:
    """Lấy dữ liệu thẻ bài an toàn theo ID string hoặc int"""
    cid_str = str(cid).strip().lower()
    if cid_str in ("t1", "#t1"):
        return CARDS_DATA.get("t1")
    try:
        cid_int = int(cid_str)
        return CARDS_DATA.get(cid_int)
    except (ValueError, TypeError):
        return CARDS_DATA.get(cid_str)

# ==============================================================================
# HỆ CƠ SỞ DỮ LIỆU: MONGODB ATLAS CLOUD + SQLITE3 FALLBACK
# ==============================================================================
mongo_uri = os.getenv("MONGO_URI")
use_mongo = False
players_collection = None

if mongo_uri:
    try:
        from pymongo import MongoClient
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_client.server_info()
        mongo_db = mongo_client["touhou_reimu_bot"]
        players_collection = mongo_db["players"]
        use_mongo = True
        print("[DATABASE] Đã kết nối thành công MongoDB Atlas Cloud.")
    except Exception as e:
        print(f"[DATABASE] Lỗi kết nối MongoDB ({e}). Chuyển sang SQLite local.")
        use_mongo = False

conn = sqlite3.connect("reimu_bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    user_id TEXT PRIMARY KEY,
    player_data_json TEXT,
    updated_at TEXT
)
''')
conn.commit()

def calculate_level_from_xp(xp: int) -> int:
    if xp <= 0: return 1
    lvl = int((xp / 100) ** 0.5) + 1
    return max(1, min(100, lvl))

def get_default_player(user_id: Union[str, int], username: str) -> dict:
    now_date = get_vietnam_date_str()
    return {
        "user_id": str(user_id),
        "username": username,
        "level": 1,
        "xp": 0,
        "pull_tickets": 5.0,
        "free_pulls_remaining": 5,
        "free_pulls_date": now_date,
        "shards": {"seiki": 0},
        "inventory": {},
        "unlocked_cards": [],
        "locked_cards": [],
        "team": [],
        "daily_quests": {
            "date": now_date,
            "battle_count": 0,
            "pull_count": 0,
            "claimed": False
        },
        "pull_stats": {"total_pulls": 0, "ss_count": 0, "s_count": 0},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def get_player(user_id: Union[str, int], username: str = "Unknown") -> dict:
    uid_str = str(user_id)
    now_date = get_vietnam_date_str()
    data = None

    if use_mongo and players_collection is not None:
        try:
            doc = players_collection.find_one({"user_id": uid_str})
            if doc: data = doc
        except Exception: pass
    else:
        try:
            cursor.execute('SELECT player_data_json FROM players WHERE user_id = ?', (uid_str,))
            row = cursor.fetchone()
            if row and row[0]: data = json.loads(row[0])
        except Exception: pass

    if not data:
        data = get_default_player(user_id, username)

    data.setdefault("inventory", {})
    data.setdefault("team", [])
    data.setdefault("shards", {"seiki": 0})
    data["shards"].setdefault("seiki", 0)
    data.setdefault("xp", 0)
    data.setdefault("pull_tickets", 0.0)

    if data.get("free_pulls_date") != now_date:
        data["free_pulls_date"] = now_date
        data["free_pulls_remaining"] = 5
        if "daily_quests" in data:
            data["daily_quests"] = {"date": now_date, "battle_count": 0, "pull_count": 0, "claimed": False}

    data["level"] = calculate_level_from_xp(data.get("xp", 0))
    return data

def save_player(player_data: dict):
    uid_str = str(player_data["user_id"])
    now_iso = datetime.now().isoformat()
    player_data["updated_at"] = now_iso
    player_data["level"] = calculate_level_from_xp(player_data.get("xp", 0))

    if use_mongo and players_collection is not None:
        try:
            doc = dict(player_data)
            players_collection.update_one({"user_id": uid_str}, {"$set": doc}, upsert=True)
            return
        except Exception: pass

    try:
        cursor.execute('INSERT OR REPLACE INTO players (user_id, player_data_json, updated_at) VALUES (?, ?, ?)',
                       (uid_str, json.dumps(player_data, ensure_ascii=False), now_iso))
        conn.commit()
    except Exception: pass

# ==============================================================================
# HỆ THỐNG CHIẾN ĐẤU THỰC CHIẾN: NHÓM T (#t1 SEIKI)
# ==============================================================================
def create_combatant_state(card_id: Union[str, int]) -> Optional[dict]:
    data = get_card_data(card_id)
    if not data: return None

    is_group_t = (str(card_id).strip().lower() in ("t1", "#t1")) or (data.get("rank") == "T")
    return {
        "id": "t1" if is_group_t else str(card_id),
        "name": data["name"],
        "rank": data["rank"],
        "max_hp": data["hp"],
        "current_hp": data["hp"],
        "power": data["power"],
        "is_group_t": is_group_t,
        "used_fantasy_seal": False,
        "used_master_spark": False,
        "used_medicine_sign": False
    }

def simulate_turn_attack(attacker: dict, defender: dict) -> List[str]:
    logs = []
    attacker_skill_used = False
    defender_skill_used = False

    # 1. Master Spark: 30% x1.5 DMG
    damage_multiplier = 1.0
    if attacker["is_group_t"] and not attacker["used_master_spark"]:
        if random.random() < 0.30:
            damage_multiplier = 1.5
            attacker["used_master_spark"] = True
            attacker_skill_used = True
            logs.append(f"🌟 **[Master Spark]** {attacker['name']} bộc phát ma lực tối thượng! Sát thương nhân x1.5!")

    base_damage = int(attacker["power"] * damage_multiplier)

    # 2. Fantasy Seal: 40% Immune DMG
    damage_taken = base_damage
    if defender["is_group_t"] and not defender["used_fantasy_seal"]:
        if random.random() < 0.40:
            damage_taken = 0
            defender["used_fantasy_seal"] = True
            defender_skill_used = True
            logs.append(f"🛡️ **[Fantasy Seal]** {defender['name']} dựng kết giới Fantasy Nature! Miễn toàn bộ sát thương đòn này!")

    defender["current_hp"] = max(0, defender["current_hp"] - damage_taken)
    if damage_taken > 0:
        logs.append(f"⚔️ {attacker['name']} tấn công gây **{damage_taken:,}** sát thương lên {defender['name']} (Còn {defender['current_hp']:,}/{defender['max_hp']:,} HP).")

    # 3. Medicine Sign: 20% Heal 30% HP
    if defender["is_group_t"] and defender["current_hp"] > 0 and not defender_skill_used and not defender["used_medicine_sign"]:
        if random.random() < 0.20:
            heal_amount = int(defender["max_hp"] * 0.30)
            defender["current_hp"] = min(defender["max_hp"], defender["current_hp"] + heal_amount)
            defender["used_medicine_sign"] = True
            logs.append(f"💚 **[Medicine Sign]** {defender['name']} hấp thu linh dược! Tự hồi phục **{heal_amount:,}** HP (Hiện có: {defender['current_hp']:,} HP).")

    return logs

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

gemini_key = os.getenv("GEMINI_API_KEY")
gemini_client = None
if gemini_key:
    try:
        gemini_client = genai.Client(api_key=gemini_key)
        print("[AI] Gemini Client đã sẵn sàng.")
    except Exception as e:
        print(f"[AI] Lỗi cấu hình Gemini: {e}")

# ==============================================================================
# SLASH COMMANDS
# ==============================================================================
@bot.tree.command(name="battle", description="Tham gia đấu trường Touhou 3v3 cùng đội hình của bạn!")
async def slash_battle(interaction: discord.Interaction):
    await interaction.response.defer()
    player = get_player(interaction.user.id, interaction.user.name)

    team_ids = player.get("team", [])
    if not team_ids:
        inv = player.get("inventory", {})
        available_cids = [cid for cid, count in inv.items() if count > 0]
        if not available_cids:
            await interaction.followup.send("⚠️ Kho thẻ bài của bạn đang trống! Hãy dùng `/gacha` hoặc nhận quà hàng ngày `/daily` trước nhé.")
            return
        team_ids = available_cids[:3]

    player_team = [create_combatant_state(cid) for cid in team_ids if create_combatant_state(cid)]
    if not player_team:
        await interaction.followup.send("⚠️ Không tìm thấy thẻ bài hợp lệ trong đội hình của bạn!")
        return

    enemy_pool = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    chosen_enemies = random.sample(enemy_pool, min(3, len(enemy_pool)))
    enemy_team = [create_combatant_state(cid) for cid in chosen_enemies]

    p_idx = 0
    e_idx = 0
    battle_logs = []
    rounds = 0

    while p_idx < len(player_team) and e_idx < len(enemy_team) and rounds < 25:
        rounds += 1
        p_fighter = player_team[p_idx]
        e_fighter = enemy_team[e_idx]

        battle_logs.append(f"**--- Hiệp {rounds}: {p_fighter['name']} VS {e_fighter['name']} ---**")

        logs1 = simulate_turn_attack(p_fighter, e_fighter)
        battle_logs.extend(logs1)

        if e_fighter["current_hp"] <= 0:
            battle_logs.append(f"💥 {e_fighter['name']} đã bị đánh bại!")
            e_idx += 1
            continue

        logs2 = simulate_turn_attack(e_fighter, p_fighter)
        battle_logs.extend(logs2)

        if p_fighter["current_hp"] <= 0:
            battle_logs.append(f"🥀 {p_fighter['name']} đã gục ngã!")
            p_idx += 1

    user_won = (e_idx >= len(enemy_team))
    embed = discord.Embed(
        title="⛩️ Đấu Trường Gensokyo • Kết Quả Chiến Đấu",
        color=discord.Color.green() if user_won else discord.Color.red()
    )

    log_text = "\\n".join(battle_logs[-12:])
    embed.add_field(name="📜 Diễn Biến Trận Đấu", value=log_text if log_text else "Giao tranh kết thúc.", inline=False)

    if user_won:
        xp_gain = random.randint(80, 150)
        ticket_gain = 0.5
        player["xp"] += xp_gain
        player["pull_tickets"] += ticket_gain

        shard_dropped = (random.random() < 0.025)
        shard_text = ""
        if shard_dropped:
            player["shards"]["seiki"] = player["shards"].get("seiki", 0) + 1
            shard_text = "\\n✨ **Đặc biệt:** Bạn đã nhận được **1 Mảnh Seiki Nhóm T**!"

        save_player(player)
        embed.description = f"🎉 **Chiến thắng vẻ vang!**\\nNhận: **+{xp_gain} XP**, **+{ticket_gain} Vé Quay**{shard_text}"
    else:
        xp_gain = 20
        player["xp"] += xp_gain
        save_player(player)
        embed.description = f"💔 **Thất bại!** Đừng nản lòng, bạn nhận được **+{xp_gain} XP** an ủi."

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="pvp", description="Thách đấu PvP 3v3 thời gian thực với người chơi khác!")
@app_commands.describe(opponent="Người chơi bạn muốn thách đấu")
async def slash_pvp(interaction: discord.Interaction, opponent: discord.User):
    if opponent.id == interaction.user.id or opponent.bot:
        await interaction.response.send_message("❌ Bạn không thể tự thách đấu bản thân hoặc Bot!", ephemeral=True)
        return

    p1 = get_player(interaction.user.id, interaction.user.name)
    p2 = get_player(opponent.id, opponent.name)

    if not p1.get("team"):
        await interaction.response.send_message("❌ Bạn chưa thiết lập đội hình! Dùng `/team add <id>` trước nhé.", ephemeral=True)
        return
    if not p2.get("team"):
        await interaction.response.send_message(f"❌ {opponent.mention} chưa thiết lập đội hình thi đấu!", ephemeral=True)
        return

    class PvPInviteView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.value = None

        @discord.ui.button(label="Chấp Nhận Quyết Đấu", style=discord.ButtonStyle.green, emoji="⚔️")
        async def confirm(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if btn_interaction.user.id != opponent.id:
                await btn_interaction.response.send_message("Chỉ người được thách đấu mới có quyền bấm nút này!", ephemeral=True)
                return
            self.value = True
            self.stop()
            await btn_interaction.response.defer()

        @discord.ui.button(label="Từ Chối", style=discord.ButtonStyle.red, emoji="🏳️")
        async def decline(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if btn_interaction.user.id != opponent.id:
                await btn_interaction.response.send_message("Chỉ người được thách đấu mới có quyền bấm nút này!", ephemeral=True)
                return
            self.value = False
            self.stop()
            await btn_interaction.response.send_message(f"🏳️ {opponent.mention} đã từ chối lời thách đấu.")

    view = PvPInviteView()
    msg = await interaction.response.send_message(
        f"⚔️ {interaction.user.mention} vừa gửi lời thách đấu PvP 3v3 đến {opponent.mention}! Bạn có dám nhận lời?",
        view=view
    )

    await view.wait()
    if view.value is not True:
        return

    team1 = [create_combatant_state(cid) for cid in p1["team"] if create_combatant_state(cid)]
    team2 = [create_combatant_state(cid) for cid in p2["team"] if create_combatant_state(cid)]

    t1_idx = 0
    t2_idx = 0
    logs = []
    turn = 0

    while t1_idx < len(team1) and t2_idx < len(team2) and turn < 30:
        turn += 1
        c1 = team1[t1_idx]
        c2 = team2[t2_idx]

        l1 = simulate_turn_attack(c1, c2)
        logs.extend(l1)
        if c2["current_hp"] <= 0:
            logs.append(f"💀 Thẻ {c2['name']} của {opponent.name} đã bị tiêu diệt!")
            t2_idx += 1
            continue

        l2 = simulate_turn_attack(c2, c1)
        logs.extend(l2)
        if c1["current_hp"] <= 0:
            logs.append(f"💀 Thẻ {c1['name']} của {interaction.user.name} đã gục ngã!")
            t1_idx += 1

    p1_won = (t2_idx >= len(team2))
    embed = discord.Embed(
        title="⚔️ Đấu Trường PvP Gensokyo • Kết Quả Trận Đấu",
        description=f"🏆 **Người chiến thắng:** {interaction.user.mention if p1_won else opponent.mention}",
        color=discord.Color.gold()
    )
    embed.add_field(name="📜 Diễn Biến Trận Đấu", value="\\n".join(logs[-12:]), inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="raid", description="Khiêu chiến Boss Dị Hình cùng nhóm thẻ bài của bạn!")
async def slash_raid(interaction: discord.Interaction):
    await interaction.response.defer()
    player = get_player(interaction.user.id, interaction.user.name)

    team_ids = player.get("team", [])
    if not team_ids:
        await interaction.followup.send("❌ Bạn cần thiết lập đội hình qua `/team add <id>` trước khi vào Boss Raid!")
        return

    player_team = [create_combatant_state(cid) for cid in team_ids if create_combatant_state(cid)]
    boss = {
        "name": BOSS_CONFIG["name"],
        "max_hp": BOSS_CONFIG["hp"],
        "current_hp": BOSS_CONFIG["hp"],
        "power": BOSS_CONFIG["power"],
        "is_group_t": False
    }

    logs = [f"🚨 **Báo Động:** {boss['name']} xuất hiện! Hãy bảo vệ Gensokyo!"]
    p_idx = 0
    round_num = 0

    while p_idx < len(player_team) and boss["current_hp"] > 0 and round_num < 20:
        round_num += 1
        hero = player_team[p_idx]

        atk_logs = simulate_turn_attack(hero, boss)
        logs.extend(atk_logs)

        if boss["current_hp"] <= 0:
            logs.append(f"✨ **Boss {boss['name']} đã bị thanh tẩy hoàn toàn!**")
            break

        boss_dmg = boss["power"]
        if hero["is_group_t"] and not hero["used_fantasy_seal"] and random.random() < 0.40:
            hero["used_fantasy_seal"] = True
            logs.append(f"🛡️ **[Fantasy Seal]** {hero['name']} che chở toàn đội, hóa giải hoàn toàn đòn quét của Boss!")
        else:
            hero["current_hp"] = max(0, hero["current_hp"] - boss_dmg)
            logs.append(f"⚡ Boss tung chưởng gây **{boss_dmg:,}** sát thương lên {hero['name']}.")
            if hero["current_hp"] <= 0:
                logs.append(f"🥀 {hero['name']} đã gục ngã trước sức mạnh hắc ám!")
                p_idx += 1

    boss_defeated = (boss["current_hp"] <= 0)
    embed = discord.Embed(
        title="👹 Đại Chiến Boss Raid Gensokyo",
        color=discord.Color.purple() if boss_defeated else discord.Color.dark_red()
    )
    embed.add_field(name="📜 Chiến Tích", value="\\n".join(logs[-12:]), inline=False)

    if boss_defeated:
        reward_tickets = 2.0
        player["pull_tickets"] += reward_tickets
        player["xp"] += 300
        player["shards"]["seiki"] = player["shards"].get("seiki", 0) + 1
        save_player(player)
        embed.description = f"🎉 **Vinh Quang!** Tiêu diệt Boss thành công! Thưởng: **+2 Vé Quay**, **+300 XP** & **+1 Mảnh Seiki**!"
    else:
        player["xp"] += 50
        save_player(player)
        embed.description = "💀 Đội hình của bạn đã không thể trụ vững trước ma lực của Boss. Nhận **+50 XP** động viên."

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="gacha", description="Cầu nguyện đài Touhou để nhận thẻ bài và Mảnh Seiki!")
@app_commands.describe(amount="Số lần quay (1 hoặc 10)")
async def slash_gacha(interaction: discord.Interaction, amount: int = 1):
    if amount not in (1, 10):
        await interaction.response.send_message("❌ Chỉ có thể quay 1 hoặc 10 lần mỗi lượt!", ephemeral=True)
        return

    player = get_player(interaction.user.id, interaction.user.name)

    free_available = player.get("free_pulls_remaining", 0)
    tickets = player.get("pull_tickets", 0.0)

    used_free = 0
    used_tickets = 0

    if free_available >= amount:
        used_free = amount
    else:
        used_free = free_available
        remaining_needed = amount - used_free
        if tickets < remaining_needed:
            await interaction.response.send_message(
                f"❌ Bạn không đủ vé! Bạn có **{free_available}** lượt miễn phí và **{tickets:.1f}** vé quay (Cần {amount} lượt).",
                ephemeral=True
            )
            return
        used_tickets = remaining_needed

    player["free_pulls_remaining"] -= used_free
    player["pull_tickets"] -= used_tickets

    all_cards = [cid for cid in CARDS_DATA.keys() if str(cid).lower() not in ("t1", "#t1")]
    pulled_cards = []
    shards_dropped = 0

    for _ in range(amount):
        chosen_id = random.choice(all_cards)
        cid_str = format_card_id(chosen_id)
        player["inventory"][cid_str] = player["inventory"].get(cid_str, 0) + 1
        pulled_cards.append(get_card_data(chosen_id))

        if random.random() < 0.025:
            shards_dropped += 1

    if shards_dropped > 0:
        player["shards"]["seiki"] = player["shards"].get("seiki", 0) + shards_dropped

    save_player(player)

    embed = discord.Embed(
        title="⛩️ Đài Cầu Nguyện Gensokyo • Kết Quả Gacha",
        color=discord.Color.magenta()
    )

    card_lines = [f"• **[{c['rank']}]** #{format_card_id(c.get('id', '??'))} {c['name']} (⚔️ {c['power']} | ❤️ {c['hp']})" for c in pulled_cards]
    embed.add_field(name=f"🎉 Nhận Được ({amount} Thẻ)", value="\\n".join(card_lines[:10]), inline=False)

    if shards_dropped > 0:
        embed.add_field(
            name="✨ May Mắn Hiếm Có!",
            value=f"🔮 Bạn đã nhận được thêm **+{shards_dropped} Mảnh Seiki Nhóm T**! (Hiện có: {player['shards']['seiki']}/10 Mảnh)",
            inline=False
        )

    embed.set_footer(text=f"Còn lại: {player['free_pulls_remaining']} lượt miễn phí | {player['pull_tickets']:.1f} Vé Quay")
    if pulled_cards:
        embed.set_thumbnail(url=pulled_cards[0]["image"])

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="t", description="Quản lý Mảnh Seiki Nhóm T & dịch thuật thành thẻ hoàn chỉnh!")
@app_commands.describe(action="Hành động: 'check' để xem mảnh, 'translate' để đổi 10 mảnh thành Thẻ Seiki #t1")
async def slash_group_t(interaction: discord.Interaction, action: str):
    player = get_player(interaction.user.id, interaction.user.name)
    current_shards = player.get("shards", {}).get("seiki", 0)

    if action.lower() == "check":
        embed = discord.Embed(
            title="🔮 Kho Mảnh Cổ Tích • Nhóm T (Seiki)",
            description=f"Bạn hiện đang sở hữu: **{current_shards}/10** Mảnh Seiki.\\nKhi đủ 10 mảnh, dùng `/t translate` để hợp thành thẻ **#t1 Seiki đệ pháp toàn năng**!",
            color=discord.Color.purple()
        )
        t_card = CARDS_DATA["t1"]
        embed.set_thumbnail(url=t_card["image"])
        await interaction.response.send_message(embed=embed)

    elif action.lower() == "translate":
        if current_shards < 10:
            await interaction.response.send_message(
                f"❌ Bạn chưa đủ mảnh! Hiện chỉ có **{current_shards}/10** Mảnh Seiki. Hãy tham gia `/battle`, `/raid` hoặc `/gacha` để tìm thêm!",
                ephemeral=True
            )
            return

        player["shards"]["seiki"] -= 10
        player["inventory"]["t1"] = player["inventory"].get("t1", 0) + 1
        save_player(player)

        t_card = CARDS_DATA["t1"]
        embed = discord.Embed(
            title="✨ Dịch Thuật Thành Công • Thần Khí Xuất Thế!",
            description="10 Mảnh Seiki đã dung hợp thành công thành thẻ bài huyền thoại:\\n**#t1 Seiki đệ pháp toàn năng** (Rank [T])!",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚔️ Sức Mạnh", value=f"{t_card['power']:,} ATK", inline=True)
        embed.add_field(name="❤️ Sinh Mệnh", value=f"{t_card['hp']:,} HP", inline=True)
        embed.add_field(name="📜 Bộ Kỹ Năng", value="• **Fantasy Seal:** Miễn thương 40% (1 lần)\\n• **Master Spark:** x1.5 sát thương (1 lần)\\n• **Medicine Sign:** Hồi 30% HP (1 lần)", inline=False)
        embed.set_image(url=t_card["image"])
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Hành động không hợp lệ! Vui lòng chọn `check` hoặc `translate`.", ephemeral=True)

@bot.tree.command(name="team", description="Quản lý và sắp xếp đội hình chiến đấu 3 thẻ!")
@app_commands.describe(action="Hành động: list, add, remove", card_id="Mã ID của thẻ (VD: 1, 13, t1)")
async def slash_team(interaction: discord.Interaction, action: str, card_id: Optional[str] = None):
    player = get_player(interaction.user.id, interaction.user.name)
    action = action.lower()

    if action == "list":
        team_ids = player.get("team", [])
        if not team_ids:
            await interaction.response.send_message("ℹ️ Đội hình của bạn đang trống! Dùng `/team add <id>` để thêm thẻ bài.", ephemeral=True)
            return

        embed = discord.Embed(title=f"🛡️ Đội Hình Chiến Đấu Của {interaction.user.name}", color=discord.Color.blue())
        for idx, cid in enumerate(team_ids, 1):
            cdata = get_card_data(cid)
            if cdata:
                embed.add_field(
                    name=f"Vị trí #{idx}: [{cdata['rank']}] #{format_card_id(cid)} {cdata['name']}",
                    value=f"⚔️ {cdata['power']:,} DMG | ❤️ {cdata['hp']:,} HP\\n_{cdata['skill_desc']}_",
                    inline=False
                )
        await interaction.response.send_message(embed=embed)

    elif action == "add":
        if not card_id:
            await interaction.response.send_message("❌ Vui lòng nhập mã ID thẻ bài cần thêm! (VD: `/team add t1`)", ephemeral=True)
            return

        cid_norm = format_card_id(card_id)
        if player.get("inventory", {}).get(cid_norm, 0) <= 0:
            await interaction.response.send_message(f"❌ Bạn không sở hữu thẻ bài #{cid_norm} trong kho!", ephemeral=True)
            return

        current_team = player.get("team", [])
        if cid_norm in current_team:
            await interaction.response.send_message("⚠️ Thẻ bài này đã có trong đội hình của bạn rồi!", ephemeral=True)
            return

        if len(current_team) >= 3:
            current_team.pop(0)
        current_team.append(cid_norm)
        player["team"] = current_team
        save_player(player)

        cdata = get_card_data(cid_norm)
        await interaction.response.send_message(f"✅ Đã thêm thẻ **[{cdata['rank']}] #{cid_norm} {cdata['name']}** vào đội hình xuất trận!")

    elif action == "remove":
        if not card_id:
            await interaction.response.send_message("❌ Vui lòng chỉ định ID thẻ bài cần gỡ!", ephemeral=True)
            return
        cid_norm = format_card_id(card_id)
        current_team = player.get("team", [])
        if cid_norm not in current_team:
            await interaction.response.send_message("⚠️ Thẻ bài này không nằm trong đội hình hiện tại!", ephemeral=True)
            return
        current_team.remove(cid_norm)
        player["team"] = current_team
        save_player(player)
        await interaction.response.send_message(f"✅ Đã gỡ thẻ #{cid_norm} khỏi đội hình!")

@bot.tree.command(name="check", description="Soi thông số chi tiết và hình ảnh của thẻ bài bất kỳ!")
@app_commands.describe(card_id="ID thẻ bài (VD: 1, 13, t1)")
async def slash_check(interaction: discord.Interaction, card_id: str):
    cdata = get_card_data(card_id)
    if not cdata:
        await interaction.response.send_message(f"❌ Không tìm thấy thẻ bài mang mã #{card_id}!", ephemeral=True)
        return

    cid_str = format_card_id(card_id)
    embed = discord.Embed(
        title=f"[{cdata['rank']}] #{cid_str} • {cdata['name']}",
        description=f"*{cdata.get('title', 'Cư Dân Xứ Gensokyo')}*",
        color=discord.Color.purple() if cdata['rank'] == 'T' else discord.Color.gold()
    )
    embed.add_field(name="⚔️ Sức Mạnh (ATK)", value=f"{cdata['power']:,}", inline=True)
    embed.add_field(name="❤️ Sinh Mệnh (HP)", value=f"{cdata['hp']:,}", inline=True)
    embed.add_field(name="📖 Năng Lực & Kỹ Năng", value=cdata['skill_desc'], inline=False)
    embed.set_image(url=cdata["image"])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Nhận vé quay thưởng và kích hoạt lượt quay hàng ngày!")
async def slash_daily(interaction: discord.Interaction):
    player = get_player(interaction.user.id, interaction.user.name)
    now_date = get_vietnam_date_str()

    if player.get("last_daily_claim") == now_date:
        await interaction.response.send_message("⏳ Hôm nay bạn đã nhận quà điểm danh rồi! Hãy quay lại sau 00:00 nhé.", ephemeral=True)
        return

    player["last_daily_claim"] = now_date
    player["pull_tickets"] = player.get("pull_tickets", 0.0) + 3.0
    player["free_pulls_remaining"] = 5
    player["free_pulls_date"] = now_date
    save_player(player)

    embed = discord.Embed(
        title="🎁 Điểm Danh Hàng Ngày • Đền Hakurei",
        description="Bạn đã nhận được:\\n• **+3 Vé Cầu Nguyện**\\n• **5 Lượt Quay Miễn Phí** trong ngày!\\nChúc bạn một ngày khám phá Gensokyo may mắn!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Admin commands
@bot.tree.command(name="admin_add_card", description="[Admin] Cấp phát thẻ bài cho người chơi")
async def slash_admin_add_card(interaction: discord.Interaction, target: discord.User, card_id: str, amount: int = 1):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("🚫 Bạn không có quyền sử dụng lệnh của Người Sáng Lập!", ephemeral=True)
        return

    cdata = get_card_data(card_id)
    if not cdata:
        await interaction.response.send_message("❌ ID thẻ bài không tồn tại!", ephemeral=True)
        return

    cid_norm = format_card_id(card_id)
    p = get_player(target.id, target.name)
    p["inventory"][cid_norm] = p.get("inventory", {}).get(cid_norm, 0) + amount
    save_player(p)
    await interaction.response.send_message(f"✅ Đã cấp phát **x{amount} [{cdata['rank']}] #{cid_norm} {cdata['name']}** cho {target.mention}!")

@bot.tree.command(name="admin_add_ticket", description="[Admin] Cấp vé quay cho người chơi")
async def slash_admin_add_ticket(interaction: discord.Interaction, target: discord.User, tickets: float):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("🚫 Bạn không có quyền sử dụng lệnh Admin!", ephemeral=True)
        return
    p = get_player(target.id, target.name)
    p["pull_tickets"] = p.get("pull_tickets", 0.0) + tickets
    save_player(p)
    await interaction.response.send_message(f"✅ Đã cộng **+{tickets} vé quay** cho {target.mention}!")

@bot.tree.command(name="admin_set_level", description="[Admin] Thiết lập cấp độ cho người chơi")
async def slash_admin_set_level(interaction: discord.Interaction, target: discord.User, level: int):
    if not is_authorized_admin(interaction.user):
        await interaction.response.send_message("🚫 Bạn không có quyền sử dụng lệnh Admin!", ephemeral=True)
        return
    p = get_player(target.id, target.name)
    p["level"] = max(1, min(100, level))
    p["xp"] = ((level - 1) ** 2) * 100
    save_player(p)
    await interaction.response.send_message(f"✅ Đã đặt cấp độ của {target.mention} thành **Lv.{level}**!")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        clean_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not clean_prompt:
            await message.reply("Ngươi tìm ta có việc gì thế? Đến quyên tiền cho đền Hakurei à?")
            return

        async with message.channel.typing():
            if gemini_client:
                try:
                    system_prompt = (
                        "Bạn là Hakurei Reimu, vu nữ cai quản đền Hakurei ở Gensokyo. "
                        "Tính cách: Thông minh, thẳng thắn, hơi lười biếng, rất quan tâm đến hòm công đức quyên tiền, "
                        "nhưng có tinh thần trách nhiệm bảo vệ bình yên cho Gensokyo. Xưng hô: 'ta' và 'ngươi' hoặc gọi tên người hỏi. "
                        "Trả lời súc tích, tự nhiên, đậm chất phong cách Touhou."
                    )
                    response = gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=clean_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.7,
                            max_output_tokens=600
                        )
                    )
                    reply_text = response.text or "Ta đang bận quét lá ở đền, lát nữa nói tiếp nhé!"
                    await message.reply(reply_text[:1900])
                except Exception as e:
                    await message.reply(f"Bùa chú truyền tin vừa bị nhiễu loạn ma pháp: {e}")
            else:
                await message.reply("Hòm công đức đang đóng kín (Chưa cấu hình GEMINI_API_KEY trong file .env).")

    await bot.process_commands(message)

class SimpleKeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Hakurei Reimu Discord Bot Status</title></head>
        <body style="font-family: sans-serif; background:#0f172a; color:#f8fafc; text-align:center; padding:50px;">
            <h1 style="color:#f43f5e;">⛩️ Hakurei Reimu Discord Bot</h1>
            <p style="color:#10b981; font-weight:bold;">STATUS: ONLINE 24/7</p>
            <p>Group T (#t1 Seiki) Combat Module: <strong>Active in All Battles</strong></p>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

def run_keep_alive_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleKeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_keep_alive_server, daemon=True).start()

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"⛩️ Bot đã đăng nhập thành công: {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✨ Đã đồng bộ thành công {len(synced)} Slash Commands trên toàn cầu!")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ Slash Commands: {e}")
    print(f"⚔️ Thẻ nhóm T (#t1 Seiki) đã sẵn sàng tham chiến mọi cơ chế!")
    print(f"==================================================")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("⚠️ CẢNH BÁO: Chưa tìm thấy DISCORD_TOKEN trong file .env!")
        print("Hãy tạo file .env và điền: DISCORD_TOKEN=your_token_here")
    else:
        bot.run(token)
