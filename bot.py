# ==============================================================================
# HAKUREI REIMU DISCORD BOT - POWERED BY GOOGLE GEMINI 3.8 FLASH
# TÍNH CÁCH: Miko Đền Hakurei - Kiêu ngạo, đanh đá, cuồng tiền công đức,
# ghét nam giới (trừ bố nuôi Han Seiki xưng ba gọi con).
# ==============================================================================

import os
import asyncio
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
# MỞ CỔNG WEB SERVER CHO RENDER FREE (TRÁNH LỖI QUÉT CỔNG)
# ==============================================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Hakurei Reimu Discord Bot (Gemini 3.8 Flash) is running online!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==============================================================================
# CẤU HÌNH BOT DISCORD & GEMINI 3.8 FLASH (CÓ AUTO-RETRY CHỐNG NGHẼN 503)
# ==============================================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai = genai.Client(api_key=GEMINI_API_KEY)

async def ask_gemini_38(contents, system_instruction, temperature=0.85):
    """Gửi trực tiếp tới Gemini 3.8 Flash. Tự động thử lại 3 lần nếu Google bị nghẽn 503 tạm thời."""
    last_err = None
    for attempt in range(3):
        try:
            resp = ai.models.generate_content(
                model="gemini-3.8-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature
                )
            )
            if resp and resp.text:
                return resp.text
        except Exception as e:
            last_err = e
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str:
                print(f"[*] Gemini 3.8 Flash bận tạm thời (503), thử lại lần {attempt + 1}/3 sau 2 giây...", flush=True)
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise e
    raise last_err

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
  + VỚI HAN SEIKI: Tự xưng là "con", gọi Han Seiki là "ba", thái độ lập tức ngoan ngoãn, dịu dàng, hiếu thảo, hỏi thăm sức khỏe, tuyệt đối không đòi tiền!
"""

@bot.event
async def on_ready():
    print(f"Đã đăng nhập thành công dưới tên: {bot.user.name}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh Slash Commands: /wiki, /donate, /danmaku.", flush=True)
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}", flush=True)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Đền Hakurei | Gọi 'reimu' hoặc /wiki"
        )
    )

# ==============================================================================
# TỰ ĐỘNG PHẢN HỒI KHI: GỌI TÊN "REIMU", TAG @REIMU, HOẶC REPLY TIN NHẮN CỦA REIMU
# ==============================================================================
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user or message.author.bot:
        return

    content_lower = message.content.lower()

    # Kiểm tra xem tin nhắn có bấm Trả lời (Reply) vào Reimu hay không
    is_reply_to_reimu = False
    if message.reference and message.reference.resolved:
        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message) and resolved.author == bot.user:
            is_reply_to_reimu = True

    # Điều kiện kích hoạt: Nhắc chữ "reimu", hoặc Tag bot, hoặc Reply bot
    is_mentioned = bot.user in message.mentions if bot.user else False
    has_reimu_name = "reimu" in content_lower

    if is_mentioned or has_reimu_name or is_reply_to_reimu:
        # Làm sạch nội dung (bỏ tag mention để câu chuyện tự nhiên)
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

        # Hiển thị trạng thái đang gõ phím
        async with message.channel.typing():
            try:
                reply_text = await ask_gemini_38(
                    contents=f"[{author_name}]: {clean_text}",
                    system_instruction=REIMU_SYSTEM_PROMPT + role_instruction,
                    temperature=0.85
                )
                await message.reply(reply_text or "Hừ... Nhà ngươi lải nhải cái gì thế hả?", mention_author=False)
            except Exception as e:
                await message.reply(f"Hừ, bùa chú bị nghẽn rồi! Lỗi: {e}", mention_author=False)

    # Đảm bảo các lệnh prefix như !sync vẫn được xử lý
    await bot.process_commands(message)

# ==============================================================================
# 3 LỆNH SLASH CÒN LẠI: /wiki, /donate, /danmaku
# ==============================================================================

# 1. Lệnh tra cứu Touhou Project Wiki (/wiki)
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
        wiki_text = await ask_gemini_38(
            contents=wiki_prompt,
            system_instruction=REIMU_SYSTEM_PROMPT,
            temperature=0.7
        )
        
        embed = discord.Embed(
            title=f"🌸 Bách Khoa Gensokyo: {nhan_vat}",
            description=wiki_text,
            color=0xDC2626
        )
        embed.set_footer(text="Touhou Project Wiki Database • Gemini 3.8 Flash")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Không thể tra cứu bách khoa lúc này: {e}")

# 2. Lệnh quyên góp hòm công đức (/donate)
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

# 3. Lệnh thách đấu Đạn Mạc (/danmaku)
@bot.tree.command(name="danmaku", description="Thách đấu hoặc yêu cầu Reimu giải mã Spell Card đạn mạc")
@app_commands.describe(spell_name="Tên Spell Card (ví dụ: Fantasy Seal, Master Spark, Scarlet Gensokyo...)")
async def danmaku_challenge(interaction: discord.Interaction, spell_name: str):
    await interaction.response.defer()
    prompt = f"""
Người dùng thách đấu đạn mạc hoặc hỏi về Spell Card: "{spell_name}".
Hãy giải thích ngắn gọn về độ khó, vẻ đẹp của đạn mạc và đưa ra lời bình đanh đá, tự tin của Reimu!
"""
    try:
        danmaku_text = await ask_gemini_38(
            contents=prompt,
            system_instruction=REIMU_SYSTEM_PROMPT,
            temperature=0.8
        )
        embed = discord.Embed(
            title=f"✨ Thách Đấu Spell Card: {spell_name}",
            description=danmaku_text,
            color=0x06B6D4
        )
        embed.set_footer(text="Quy Tắc Đạn Mạc Gensokyo • Hakurei Reimu")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Lỗi khi triệu hồi Spell Card: {e}")

# Lệnh Slash /sync để đồng bộ lại lệnh Slash
@bot.tree.command(name="sync", description="Đồng bộ Slash Command ngay lập tức cho server này")
async def slash_sync_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        bot.tree.copy_global_to(guild=interaction.guild)
        synced = await bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send(f"✅ Đã đồng bộ thành công {len(synced)} lệnh Slash (/wiki, /donate, /danmaku)!")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi khi đồng bộ lệnh: {e}")

# Lệnh Prefix !sync
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def prefix_sync_commands(ctx):
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Đã đồng bộ thành công {len(synced)} lệnh Slash (/wiki, /donate, /danmaku)!")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi đồng bộ lệnh: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
