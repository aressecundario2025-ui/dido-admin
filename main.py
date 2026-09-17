import discord
from discord.ext import commands
import os

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")

# Canal específico para las respuestas automáticas
CANAL_IP = 1549058205051527198

IP_SERVIDOR = "horrorserv-gLWC.aternos.me"
WEB_SERVIDOR = "https://zerro-horror-hub.base44.app/"

MENSAJE_IP = (
    "🌐 **IP DEL SERVIDOR**\n\n"
    f"`{IP_SERVIDOR}`\n\n"
    "🎮 ¡Nos vemos dentro!"
)

MENSAJE_WEB = (
    "🌐 **WEB OFICIAL DE ZerroHorror**\n\n"
    f"{WEB_SERVIDOR}\n\n"
    "🧱 ¡Entra y descubre el servidor!"
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("========================================")
    print("🤖 DiDo Admin")
    print(f"Conectado como: {bot.user}")
    print(f"Canal: {CANAL_IP}")
    print(f"IP: {IP_SERVIDOR}")
    print(f"Web: {WEB_SERVIDOR}")
    print("Respuestas ip/web: ACTIVADAS")
    print("========================================")

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    if message.channel.id == CANAL_IP:
        texto = message.content.strip().lower()

        if texto == "ip":
            await message.reply(MENSAJE_IP)

        elif texto == "web":
            await message.reply(MENSAJE_WEB)

    await bot.process_commands(message)

if not TOKEN_DISCORD:
    raise RuntimeError(
        "Falta TOKEN_DISCORD en las variables de entorno de Discloud."
    )

bot.run(TOKEN_DISCORD)
