import discord
import dotenv
import os
import asyncio
import edge_tts
import subprocess
import io
from client import Client, clients

dotenv.load_dotenv('.env')
intents = discord.Intents.all()

bot = discord.Bot(intents=intents)
client = Client.Clients          

VOICE_OPTIONS = {
    # 中文
    "zh_female": "zh-TW-HsiaoChenNeural",
    "zh_male":   "zh-TW-YunJheNeural",

    # 英文
    "en_female": "en-US-JennyNeural",
    "en_male":   "en-US-GuyNeural",

    # 日文
    "ja_female": "ja-JP-NanamiNeural",
    "ja_male":   "ja-JP-KeitaNeural",

    # 韓文
    "ko_female": "ko-KR-SunHiNeural",
    "ko_male":   "ko-KR-InJoonNeural",

    # 法文
    "fr_female": "fr-FR-DeniseNeural",
    "fr_male":   "fr-FR-HenriNeural",

    # 西班牙文
    "es_female": "es-ES-ElviraNeural",
    "es_male":   "es-ES-AlvaroNeural",

    # 德文
    "de_female": "de-DE-KatjaNeural",
    "de_male":   "de-DE-ConradNeural",

    # 義大利文
    "it_female": "it-IT-ElsaNeural",
    "it_male":   "it-IT-LucaNeural",
}


LANG_MAP = {
    "zh": "說：",
    "en": "says:",
    "ja": "が言った：",
    "ko": "가 말했다:",
    "fr": "dit :",
    "es": "dice:",
    "de": "sagt:",
    "it": "dice:"
}

@bot.event
async def on_ready():
    print(f"Bot 已上線：{bot.user}")
    await bot.sync_commands()

@bot.slash_command(description="連接至語音頻道")
async def connect(ctx: discord.ApplicationContext):

    if ctx.guild.id not in client.keys():
        client[ctx.guild.id] = clients()

    if ctx.author.voice is None:
        await ctx.respond("❌ 請先連接到語音頻道內")
        return
    
    guild = client.get(ctx.guild.id)
    channel = ctx.author.voice.channel

    if not guild.vc:
        vc = await channel.connect()
        guild.vc = vc
    else:
        await guild.vc.move_to(channel)

    await ctx.respond("🔊 已連接至語音頻道！")


@bot.slash_command(description="斷開語音頻道")
async def disconnect(ctx: discord.ApplicationContext):
    guild = client.get(ctx.guild.id)  
    vc = guild.vc

    if guild and vc:
        await ctx.voice_client.disconnect()
        await ctx.respond("👋 掰掰")
    else:
        await ctx.respond("❌ 不在語音頻道!")


@bot.slash_command(description="設置TTS頻道")
async def set_tts_channel(
    ctx: discord.ApplicationContext, 
    channel: discord.Option(discord.TextChannel, "choose channel") # type: ignore
): 
    permiss: discord.Permissions = ctx.channel.permissions_for(ctx.interaction.user)

    if not permiss.manage_channels:
            return await ctx.respond("❌ 您沒有管理權限所以無法操作!", ephemeral=True)
    
    if ctx.guild.id not in client.keys():
        client[ctx.guild.id] = clients()
    else:
        guild = client.get(ctx.guild.id)

    guild.tts_channel_id = channel.id

    await ctx.respond(f"📢 TTS 頻道設置為：{channel.mention}")


@bot.slash_command(description="設置TTS語音")
async def set_tts_voice(
    ctx: discord.ApplicationContext,
    voice: discord.Option(str, "選擇語音", choices=list(VOICE_OPTIONS.keys())) # type: ignore
):
    if ctx.guild.id not in client.keys():
        client[ctx.guild.id] = clients()
    else:
        guild = client.get(ctx.guild.id)

    guild.tts_voice = VOICE_OPTIONS[voice]

    await ctx.respond(f"🎤 語音已設定為：`{guild.tts_voice}`")


@bot.slash_command(description="永久駐留24/7")
async def stay(ctx: discord.ApplicationContext, mode: discord.Option(str, "選擇", choices=["on", "off"])): # type: ignore
    if ctx.guild.id not in client.keys():
        client[ctx.guild.id] = clients()
    else:
        guild = client.get(ctx.guild.id)

    guild.stay_24_7 = (mode == "on")

    await ctx.respond(
        "🔒 24/7 模式已 **開啟**，bot 會永久待在語音頻道"
        if guild.stay_24_7 else
        "🔓 24/7 模式已 **關閉**"
    )

@bot.event
async def on_message(message: discord.Message):
    guild = client.get(message.guild.id)

    if message.author.bot:
        return

    if guild.tts_channel_id is None:
        return message.channel.send("⚠️請選擇一個tts頻道")

    if message.channel.id != guild.tts_channel_id:
        return message.channel.send("⚠️請在同一個語音頻道內")

    if message.author.voice is None:
        return await message.channel.send("❌ 你要先加入語音頻道")
        
    voice_channel = message.author.voice.channel

    vc = guild.vc

    if vc is None:
        await voice_channel.connect()
    else:
        await vc.move_to(voice_channel)

    speaker = message.author.display_name or message.author.name
    text = f"{speaker} {LANG_MAP.get(guild.tts_voice[:2], 'says:')}: {message.content}"

    tts = edge_tts.Communicate(text, guild.tts_voice)

    audio_bytes = b''

    async for c in tts.stream():
        if c["type"] == "audio":
            audio_bytes += c["data"]  

    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-i", "pipe:0", "-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    pcm_data, _ = ffmpeg.communicate(input=audio_bytes)

    file = io.BytesIO(pcm_data)

    vc = message.guild.voice_client
    vc.play(discord.PCMAudio(file))

    while vc.is_playing():
        await asyncio.sleep(0.5)

    if not guild.stay_24_7:
        await asyncio.sleep(10000)
        await vc.disconnect()

bot.run(os.getenv("TOKEN"))