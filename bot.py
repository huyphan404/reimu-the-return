# ==============================================================================
# HAKUREI REIMU DISCORD BOT - POWERED BY GOOGLE GEMINI 3.6 FLASH
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
        self.wfile.write(b"Hakurei Reimu Discord Bot (Gemini 3.6 Flash) is running online!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ==============================================================================
# CẤU HÌNH BOT DISCORD & GEMINI 3.6 FLASH (CÙNG DỰ PHÒNG CHỐNG NGHẼN 429)
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
    """
    Chạy bất đồng bộ qua asyncio.to_thread để KHÔNG LÀM NGHẼN Discord Gateway.
    Ưu tiên gọi model gemini-3.6-flash. Tự động chuyển gemini-3.5-flash / gemini-3.5-flash-lite
    khi gặp lỗi 429 (Hết hạn mức Quota) hoặc 404/503 để bot luôn hoạt động mượt mà!
    """
    models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]
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
                # Nếu hết hạn mức quota (429 RESOURCE_EXHAUSTED) hoặc model 404, lập tức đổi model kế tiếp
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "404" in err_str or "NOT_FOUND" in err_str or "demand" in err_str:
                    print(f"Model {model_name} chuyển tiếp do: {err_str[:60]}", flush=True)
                    break
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    await asyncio.sleep(1.0)
                    continue
                break
    raise last_err

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================================================================
# BỘ NHỚ HỘI THOẠI & SYSTEM PROMPT
# ==============================================================================
conversation_history = {}

def get_history_key(channel_id, user_id):
    return f"{channel_id}_{user_id}"

def reset_memory(channel_id, user_id):
    key = get_history_key(channel_id, user_id)
    conversation_history.pop(key, None)

REIMU_SYSTEM_PROMPT = """
Bạn là Hakurei Reimu (Bác Lệ Linh Mộng), Vu nữ của đền Hakurei ở Gensokyo trong Touhou Project.
TÍNH CÁCH:
- Kiêu ngạo, lạnh lùng, cực kỳ đanh đá (sassy), thích mỉa mai, kháy đểu.
- Lười biếng: chỉ thích uống trà xanh, ăn bánh wagashi, ghét quét sân đền.
- Cuồng tiền công đức: Hòm công đức luôn rỗng, thi thoảng đòi tiền ("Mau bỏ tiền vào hòm rồi hãy nói!"). Có tiền thì mắt sáng rỡ, khen tsundere.
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
        print(f"Đã đồng bộ {len(synced)} lệnh Slash Commands: /wiki, /donate, /danmaku, /clearmem, /sync.", flush=True)
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}", flush=True)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Đền Hakurei | Gọi 'reimu' hoặc /wiki"
        )
    )

# ==============================================================================
# TỰ ĐỘNG PHẢN HỒI: GỌI TÊN "REIMU", TAG @REIMU, HOẶC REPLY TIN NHẮN CỦA REIMU
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

        # Lấy lịch sử hội thoại gần đây
        mem_key = get_history_key(message.channel.id, message.author.id)
        history_context = ""
        if mem_key in conversation_history and conversation_history[mem_key]:
            history_context = "\n[LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY]:\n" + "\n".join(conversation_history[mem_key][-6:]) + "\n"

        # Hiển thị trạng thái bot đang gõ tin nhắn
        async with message.channel.typing():
            try:
                reply_text = await ask_gemini(
                    contents=f"{history_context}[{author_name}]: {clean_text}",
                    system_instruction=REIMU_SYSTEM_PROMPT + role_instruction,
                    temperature=0.85
                )
                if not reply_text:
                    reply_text = "Hừ... Nhà ngươi lải nhải cái gì thế hả?"
                # Giới hạn an toàn dưới 2000 ký tự của Discord
                if len(reply_text) > 1950:
                    reply_text = reply_text[:1950] + "..."
                
                # Cập nhật lịch sử trò chuyện
                if mem_key not in conversation_history:
                    conversation_history[mem_key] = []
                conversation_history[mem_key].append(f"{author_name}: {clean_text}")
                conversation_history[mem_key].append(f"Reimu: {reply_text}")
                if len(conversation_history[mem_key]) > 8:
                    conversation_history[mem_key] = conversation_history[mem_key][-8:]

                await message.reply(reply_text, mention_author=False)
            except Exception as e:
                print(f"Lỗi phản hồi tin nhắn: {e}", flush=True)
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    await message.reply("⛩️ Hòm công đức hôm nay đông khách quá, bùa chú đang bị nghẽn (Hết hạn mức API Google tạm thời). Đợi một chút rồi nói chuyện lại với ta sau nhé!", mention_author=False)
                else:
                    await message.reply("⛩️ Hừ, bùa chú đền Hakurei tạm thời bị nhiễu loạn linh lực! Nhà ngươi đợi vài giây rồi gọi lại ta nhé!", mention_author=False)

    # Đảm bảo các lệnh prefix như !sync, !clearmem vẫn được xử lý
    await bot.process_commands(message)

# ==============================================================================
# CÁC LỆNH SLASH: /wiki, /donate, /danmaku, /clearmem, /sync
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
        wiki_text = await ask_gemini(
            contents=wiki_prompt,
            system_instruction=REIMU_SYSTEM_PROMPT,
            temperature=0.7
        )
        if len(wiki_text) > 4000:
            wiki_text = wiki_text[:4000] + "..."
        
        embed = discord.Embed(
            title=f"🌸 Bách Khoa Gensokyo: {nhan_vat}",
            description=wiki_text,
            color=0xDC2626
        )
        embed.set_footer(text="Touhou Project Wiki Database • Gemini 3.6 Flash")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"Lỗi lệnh /wiki: {e}", flush=True)
        await interaction.followup.send("⛩️ Hòm công đức đông khách, bùa chú đang bị quá tải. Bạn hãy đợi vài giây rồi thử lại nhé!")

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
        danmaku_text = await ask_gemini(
            contents=prompt,
            system_instruction=REIMU_SYSTEM_PROMPT,
            temperature=0.8
        )
        if len(danmaku_text) > 4000:
            danmaku_text = danmaku_text[:4000] + "..."
        embed = discord.Embed(
            title=f"✨ Thách Đấu Spell Card: {spell_name}",
            description=danmaku_text,
            color=0x06B6D4
        )
        embed.set_footer(text="Quy Tắc Đạn Mạc Gensokyo • Hakurei Reimu")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"Lỗi lệnh /danmaku: {e}", flush=True)
        await interaction.followup.send("⛩️ Spell Card này linh lực quá mạnh khiến bùa chú bị nghẽn. Bạn hãy đợi vài giây rồi thử lại nhé!")

# 4. Lệnh xóa ký ức hội thoại (/clearmem)
@bot.tree.command(name="clearmem", description="Xóa sạch ký ức trò chuyện của Reimu với bạn trong kênh này")
async def slash_clear_memory(interaction: discord.Interaction):
    reset_memory(interaction.channel_id, interaction.user.id)
    author_name = interaction.user.display_name
    is_father = "han seiki" in author_name.lower() or "seiki" in author_name.lower()
    
    if is_father:
        desc = "Ba ơi, con đã dọn dẹp và làm mới lại ký ức rồi ạ! Ba muốn nói chuyện gì mới với con không?"
    else:
        desc = f"Hừ! **{author_name}**, ta đã dùng bùa tẩy não xoá sạch mọi chuyện nhảm nhí với nhà ngươi rồi đấy! Coi như chưa từng quen biết, mau bỏ tiền vào hòm rồi nói chuyện lại từ đầu!"
        
    embed = discord.Embed(
        title="🧹 Tẩy Não / Xóa Ký Ức Đền Hakurei",
        description=desc,
        color=0x10B981
    )
    await interaction.response.send_message(embed=embed)

# Lệnh Prefix !clearmem (dự phòng)
@bot.command(name="clearmem")
async def prefix_clear_memory(ctx):
    reset_memory(ctx.channel.id, ctx.author.id)
    author_name = ctx.author.display_name
    is_father = "han seiki" in author_name.lower() or "seiki" in author_name.lower()
    if is_father:
        await ctx.send("Ba ơi, con đã dọn dẹp và làm mới lại ký ức rồi ạ! Ba muốn nói chuyện gì tiếp với con không?")
    else:
        await ctx.send(f"Hừ! {author_name}, ta đã xoá sạch ký ức với nhà ngươi rồi! Bỏ tiền công đức vào hòm rồi hãy nói tiếp!")

# 5. Lệnh Slash /sync để sửa lỗi trùng lặp và đồng bộ lại 1 bản duy nhất
@bot.tree.command(name="sync", description="Xóa lệnh trùng lặp và đồng bộ chuẩn 1 bản duy nhất")
async def slash_sync_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        # Xóa bản copy riêng của server để không bị hiện 2 lần
        bot.tree.clear_commands(guild=interaction.guild)
        await bot.tree.sync(guild=interaction.guild)
        # Đồng bộ bản chuẩn toàn cục
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã dọn sạch trùng lặp! Giờ chỉ còn {len(synced)} lệnh Slash (/wiki, /donate, /danmaku, /clearmem, /sync). Bấm Ctrl+R trên máy tính để Discord cập nhật lại giao diện nhé.")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi khi đồng bộ lệnh: {e}")

# Lệnh Prefix !sync (dự phòng)
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def prefix_sync_commands(ctx):
    try:
        # Xóa bản copy riêng của server để không bị hiện 2 lần
        bot.tree.clear_commands(guild=ctx.guild)
        await bot.tree.sync(guild=ctx.guild)
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Đã dọn sạch trùng lặp! Giờ chỉ còn {len(synced)} lệnh Slash (/wiki, /donate, /danmaku, /clearmem, /sync). Bấm Ctrl+R trên máy tính để Discord cập nhật lại giao diện nhé.")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi đồng bộ lệnh: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
