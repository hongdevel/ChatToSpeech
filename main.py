import discord
from discord import app_commands
from discord import FFmpegPCMAudio
from discord.ui import View, Button
from gtts import gTTS
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

async def play_audio(voice_client, content, file_name):
    if voice_client.is_playing():
        voice_client.stop()
    speech = gTTS(text=content, lang="ko", slow=False)
    speech.save(f"{file_name}.mp3")
    source = FFmpegPCMAudio(f"./{file_name}.mp3")
    voice_client.play(source, after=lambda e: print(f"음성 재생 완료: {e}"))

class SoundBoardView(View):
    def __init__(self, voice_client, content):
        super().__init__(timeout=None)
        self.voice_client = voice_client
        self.content = content
    
    @discord.ui.button(label="재생", style=discord.ButtonStyle.green)
    async def play_button(self, interaction: discord.Interaction, button: Button):
        if self.voice_client.is_connected():
            await play_audio(self.voice_client, self.content, "soundboard")
            await interaction.response.defer()
        else:
            await interaction.response.send_message("봇이 음성 채널에 연결되어 있지 않습니다.", ephemeral=True)

intents = discord.Intents.default()  # 기본적인 intents만 활성화
intents.message_content = True  # 메시지 내용 읽기
intents.voice_states = True  # 음성 상태 추적

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.target_channel_id = {}

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def setup_hook(self):
        await self.tree.sync()

    async def on_message(self, message):
        if message.author == self.user:
            return

        if self.target_channel_id and message.channel.id in self.target_channel_id:
            if message.author.voice:
                channel = message.author.voice.channel
                voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
                if not voice_client or not voice_client.is_connected():
                    voice_client = await channel.connect()
                await play_audio(voice_client, message.content, "speak")
            print(f"감지된 메시지: {message.content}")

client = MyClient()

@client.tree.command(name="select", description="봇이 채팅을 읽어줄 채널을 정합니다.")
async def select_channel(interaction: discord.Interaction):
    if interaction.channel_id not in client.target_channel_id:
        client.target_channel_id[interaction.channel_id] = interaction.guild_id
        await interaction.response.send_message("지금부터 이 채널의 채팅을 읽습니다.")
    else:
        await interaction.response.send_message("이미 이 채널의 채팅을 읽을 준비가 되었습니다.", ephemeral=True)
    print(client.target_channel_id)

@client.tree.command(name="deselect", description="봇이 더 이상 해당 채널의 채팅을 읽지 않습니다.")
async def deselect_channel(interaction: discord.Interaction):
    if interaction.channel_id in client.target_channel_id:
        del client.target_channel_id[interaction.channel_id]
        await interaction.response.send_message("더 이상 이 채널의 채팅을 읽지 않습니다.")
    else:
        await interaction.response.send_message("이미 이 채널의 채팅을 읽고 있지 않습니다.")
    print(client.target_channel_id)

@client.tree.command(name="join", description="봇을 음성 채널에 연결합니다.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_connected():
            channel = interaction.user.voice.channel
            await channel.connect()
            await interaction.response.send_message(f"'{channel.name}' 채널에 연결되었습니다!")
        else:
            await interaction.response.send_message(f"이미 '{interaction.guild.voice_client.channel.name}' 채널에 연결되어있습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("먼저 음성 채널에 들어가 주세요!", ephemeral=True)


@client.tree.command(name="leave", description="봇을 음성 채널에서 나가게 합니다. 또한 이전에 선택한 채널들에서 봇이 더 이상 채팅을 읽지 않습니다.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        client.target_channel_id = {channel_id: guild_id for channel_id, guild_id in client.target_channel_id.items() if guild_id != interaction.guild_id}
        await interaction.response.send_message("음성 채널에서 나왔습니다!")
        print(client.target_channel_id)
    else:
        await interaction.response.send_message("봇이 음성 채널에 연결되어 있지 않습니다!", ephemeral=True)


@client.tree.command(name="stop", description="현재 재생 중인 음성을 중지합니다.")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("음성 재생을 중지했습니다!")
    else:
        await interaction.response.send_message("현재 재생 중인 음성이 없습니다!", ephemeral=True)

@client.tree.command(name="soundboard", description="반복 재생 가능한 사운드보드를 생성합니다.")
async def soundboard(interaction: discord.Interaction, content: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("먼저 음성 채널에 들어가 주세요!", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    if not voice_client or not voice_client.is_connected():
        voice_client = await channel.connect()

    embed = discord.Embed(
        title=f"{interaction.user.display_name}님의 사운드보드",
        description=f"{content}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="재생 버튼을 클릭하세요!")
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, view=SoundBoardView(voice_client, content))

client.run(DISCORD_TOKEN)