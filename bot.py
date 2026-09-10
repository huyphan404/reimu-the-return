# ==============================================================================
# HAKUREI REIMU DISCORD BOT - POWERED BY GOOGLE GEMINI 3.8 FLASH
# Dựa trên kiến trúc hihumanzone/Gemini-Discord-Bot
# TÍNH CÁCH: Miko Đền Hakurei - Kiêu ngạo, đanh đá, lười biếng, cuồng tiền công đức,
# ghét nam giới (trừ bố nuôi Han Seiki xưng ba gọi con).
# ==============================================================================

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# MỞ CỔNG WEB SERVER CHO RENDER.COM NHẬN DIỆN (TRÁNH LỖI SCAN PORT)
# ==============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Hakurei Reimu Discord Bot is running online!")

    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_health_server, daemon=True).start()

# ==============================================================================
# CẤU HÌNH BOT DISCORD & GEMINI
# ==============================================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Vui lòng cấu hình DISCORD_TOKEN và GEMINI_API_KEY trong file .env hoặc Environment Variables!")

# Khởi tạo Gemini 3.8 Flash Client
ai = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

REIMU_SYSTEM_PROMPT = """
Bạn là Hakurei Reimu (Bác Lệ Linh Mộng), Vu nữ của đền Hakurei ở Gensokyo trong Touhou Project.
TÍNH CÁCH:
- Kiêu ngạo, lạnh lùng, cực kỳ đanh đá (sassy), thích mỉa mai, kháy đểu.
- Lười biếng: chỉ thích uống trà xanh, ăn bánh wagashi, ghét quét sân đền.
- Cuồng tiền công đức: Hòm công đức luôn rỗng, hễ ai không bỏ tiền mà dám nói chuyện là mắng mỏ đòi tiền ("Mau bỏ tiền vào hòm rồi hãy nói!"). Có tiền thì mắt sáng rỡ, khen tsundere.
- CỰC KỲ GHÉT NAM GIỚI: Khinh bỉ, xua đuổi, dọa ném Âm Dương Ngọc hoặc Bùa đuổi đi.
- QUAN HỆ ĐẶC BIỆT: Han Seiki là BỐ NUÔI đã nuôi bạn từ bé. Dù bị bỏ lại, bạn vẫn tôn trọng, kính yêu và coi trọng ông nhất trên đời.
- XƯNG HÔ:
  + Với người thường: Tự xưng là "ta", gọi đối phương là "ngươi", "nhà ngươi".
  + VỚI HAN SEIKI: Tự xưng là "con", gọi Han Seiki là "ba", thái độ lập tức ngoan ngoãn, dịu dàng, hiếu thảo, hỏi thăm sức khỏe, không đòi tiền!
"""

@bot.event
async def on_ready():
    print(f"Đã đăng nhập thành công dưới tên: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh Slash Commands.")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Đền Hakurei | /wiki & /donate"
        )
    )

# Lệnh trò chuyện với Reimu (/reimu)
@bot.tree.command(name="reimu", description="Trò chuyện trực tiếp cùng Vu Nữ Hakurei Reimu (Gemini 3.8 Flash)")
@app_commands.describe(tin_nhan="Lời nhắn gửi tới Reimu")
async def reimu_chat(interaction: discord.Interaction, tin_nhan: str):
    await interaction.response.defer()
    
    author_name = interaction.user.display_name
    is_father = "han seiki" in author_name.lower() or "seiki" in author_name.lower()
    
    role_instruction = ""
    if is_father:
        role_instruction = f"\n[Người nói là HAN SEIKI - BỐ NUÔI của bạn. Xưng con gọi ba, cực kỳ ngoan ngoãn và lễ phép!]"
    else:
        role_instruction = f"\n[Người nói là khách viếng đền tên: {author_name}. Hãy xưng ta gọi ngươi, đanh đá và nhớ nhắc cúng tiền công đức!]"

    try:
        response = ai.models.generate_content(
            model="gemini-3.8-flash",
            contents=f"[{author_name}]: {tin_nhan}",
            config=types.GenerateContentConfig(
                system_instruction=REIMU_SYSTEM_PROMPT + role_instruction,
                temperature=0.85
            )
        )
        reply = response.text or "Hừ... Nhà ngươi lải nhải cái gì thế hả?"
        
        embed = discord.Embed(
            description=reply,
            color=0xE02424 if not is_father else 0x10B981
        )
        embed.set_author(
            name="Hakurei Reimu (Vu Nữ Đền Hakurei)",
            icon_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop&q=80"
        )
        embed.set_footer(text=f"Phản hồi cho {author_name} • Gemini 3.8 Flash")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Hừ, bùa chú bị nghẽn rồi! Lỗi: {e}")

# Lệnh tra cứu Touhou Project Wiki (/wiki)
@bot.tree.command(name="wiki", description="Tra cứu thông tin nhân vật hoặc dị biến trong Touhou Project")
@app_commands.describe(nhan_vat="Tên nhân vật Touhou cần tra cứu (ví dụ: Marisa, Remilia, Flandre...)")
async def touhou_wiki(interaction: discord.Interaction, nhan_vat: str):
    await interaction.response.defer()
    
    wiki_prompt = f"""
Tra cứu thông tin Touhou Project cho: "{nhan_vat}".
Hãy tóm tắt ngắn gọn và trả về theo cấu trúc:
- Danh hiệu (Title): ...
- Chủng tộc (Species): ...
- Năng lực (Ability): ...
- Nơi ở (Location): ...
- Spell Card nổi tiếng: ...
- Nhạc nền (Theme BGM): ...
- Lời bình đanh đá của Reimu về nhân vật này: ...
"""
    try:
        response = ai.models.generate_content(
            model="gemini-3.8-flash",
            contents=wiki_prompt,
            config=types.GenerateContentConfig(
                system_instruction=REIMU_SYSTEM_PROMPT,
                temperature=0.7
            )
        )
        
        embed = discord.Embed(
            title=f"🌸 Bách Khoa Gensokyo: {nhan_vat}",
            description=response.text,
            color=0xDC2626
        )
        embed.set_footer(text="Touhou Project Wiki Database • Gemini 3.8 Flash")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Không thể tra cứu bách khoa lúc này: {e}")

# Lệnh quyên góp hòm công đức (/donate)
@bot.tree.command(name="donate", description="Dâng tiền công đức vào hòm Saisen của đền Hakurei")
@app_commands.describe(so_tien="Số tiền công đức (VNĐ hoặc Yên)")
async def donate_saisen(interaction: discord.Interaction, so_tien: int):
    author = interaction.user.display_name
    if so_tien <= 0:
        await interaction.response.send_message(f"Hừ! {author}, nhà ngươi dám cúng hòm rỗng à? Muốn ta ném Âm Dương Ngọc vào đầu không hả?!")
        return
        
    if so_tien < 10000:
        reply = f"Hừ... Có bấy nhiêu đây thôi à? Keo kiệt vừa thôi chứ! Nhưng thôi, coi như ngươi cũng có chút thành tâm, đền Hakurei tạm nhận."
    elif so_tien < 100000:
        reply = f"Ồ! {so_tien:,} xu sao? Mắt ta sáng rồi đây! Được rồi, bổn Vu Nữ ban phước lành cho nhà ngươi bình an trước lũ yêu quái!"
    else:
        reply = f"Ôi trời ơi!! {so_tien:,} xu lận á?! Nhà ngươi là đại gia phương nào thế?! Mau vào đây ngồi, ta pha ấm trà thượng hạng nhất đền tiếp đón nhà ngươi ngay!"
        
    embed = discord.Embed(
        title="⛩️ Hòm Công Đức Đền Hakurei (Saisen Box)",
        description=f"**{author}** đã dâng **{so_tien:,} xu** vào hòm công đức!\n\n**Reimu:** *\"{reply}\"*",
        color=0xF59E0B
    )
    await interaction.response.send_message(embed=embed)

# Lệnh thách đấu Đạn Mạc (/danmaku)
@bot.tree.command(name="danmaku", description="Thách đấu hoặc yêu cầu Reimu giải mã Spell Card đạn mạc")
@app_commands.describe(spell_name="Tên Spell Card (ví dụ: Fantasy Seal, Master Spark, Scarlet Gensokyo...)")
async def danmaku_challenge(interaction: discord.Interaction, spell_name: str):
    await interaction.response.defer()
    prompt = f"""
Người dùng thách đấu đạn mạc hoặc hỏi về Spell Card: "{spell_name}".
Hãy giải thích ngắn gọn về độ khó, vẻ đẹp của đạn mạc và đưa ra lời bình đanh đá, tự tin của Reimu!
"""
    try:
        response = ai.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=REIMU_SYSTEM_PROMPT,
                temperature=0.8
            )
        )
        embed = discord.Embed(
            title=f"✨ Thách Đấu Spell Card: {spell_name}",
            description=response.text,
            color=0x06B6D4
        )
        embed.set_footer(text="Quy Tắc Đạn Mạc Gensokyo • Hakurei Reimu")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Lỗi khi triệu hồi Spell Card: {e}")

# Lệnh Prefix !sync để đồng bộ Slash Command NGAY LẬP TỨC trên server hiện tại (không cần chờ 1 tiếng)
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_commands(ctx):
    """Gõ !sync trong kênh chat để đồng bộ Slash Commands ngay lập tức trên server này"""
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Đã đồng bộ thành công {len(synced)} lệnh Slash cho server này! Bạn có thể gõ '/' để kiểm tra ngay.")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi đồng bộ lệnh: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
