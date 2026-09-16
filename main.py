import discord
from discord.ext import commands
import os

# ==================================================
# CONFIGURACIÓN
# ==================================================

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")

# Canal específico donde DiDo Admin responderá a "ip"
CANAL_IP = 1549058205051527198

# IP del servidor Minecraft
IP_SERVIDOR = "zerrohorror.mcsh.io"

# Mensaje personalizado
MENSAJE_IP = (
    "🌐 **IP DEL SERVIDOR**\n\n"
    f"`{IP_SERVIDOR}`\n\n"
    "🎮 ¡Nos vemos dentro!"
)

# ==================================================
# DISCORD
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ==================================================
# READY
# ==================================================

@bot.event
async def on_ready():
    print("========================================")
    print("🤖 DiDo Admin")
    print("========================================")
    print(f"Conectado como: {bot.user}")
    print(f"ID del bot: {bot.user.id}")
    print(f"Canal IP: {CANAL_IP}")
    print(f"IP Minecraft: {IP_SERVIDOR}")
    print("Respuesta automática de IP: ACTIVADA")
    print("========================================")

# ==================================================
# RESPUESTA AUTOMÁTICA
# ==================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None:
        return

    # Solo responde en el canal configurado.
    if message.channel.id == CANAL_IP:
        if message.content.strip().lower() == "ip":
            await message.reply(MENSAJE_IP)

    # Mantiene funcionando los comandos de DiDo Admin.
    await bot.process_commands(message)

# ==================================================
# COMPROBACIÓN
# ==================================================

if not TOKEN_DISCORD:
    raise RuntimeError(
        "Falta TOKEN_DISCORD en las variables de entorno de Discloud."
    )

bot.run(TOKEN_DISCORD)
