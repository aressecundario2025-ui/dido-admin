import os
import discord
from discord.ext import commands
from discord import app_commands

# =========================
# CONFIGURACIÓN
# =========================

TOKEN = os.getenv("TOKEN_DISCORD")

# Canal donde DiDo responde a:
# web / ip / discord / ayuda
CANAL_INFO = 1549058205051527198

WEB = "https://pillar-arena-survival.base44.app/"
IP = "minepillarss.minehut.gg"
DISCORD_INVITE = "https://discord.gg/ajfMu4ryJU"

# =========================
# INTENTS
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# FUNCIONES
# =========================

def es_administrador(member: discord.Member) -> bool:
    return member.guild_permissions.administrator


# =========================
# EVENTO: BOT CONECTADO
# =========================

@bot.event
async def on_ready():
    print(f"DiDo Admin conectado como {bot.user}")
    print(f"ID del bot: {bot.user.id}")

    try:
        comandos = await bot.tree.sync()
        print(f"{len(comandos)} comandos sincronizados.")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")


# =========================
# MENSAJES DEL CANAL WEB/IP
# =========================

@bot.event
async def on_message(message: discord.Message):

    # Ignorar mensajes de bots
    if message.author.bot:
        return

    # Solo responder automáticamente en el canal indicado
    if message.channel.id == CANAL_INFO:

        texto = message.content.strip().lower()

        # WEB
        if texto == "web":
            embed = discord.Embed(
                title="🌐 Web de Pilares",
                description=(
                    "Aquí tienes la web oficial de **Pilares**.\n\n"
                    f"🔗 {WEB}"
                ),
                color=discord.Color.blurple()
            )

            await message.channel.send(embed=embed)
            return

        # IP
        if texto == "ip":
            embed = discord.Embed(
                title="🎮 IP de Pilares",
                description=(
                    "Conéctate al servidor usando esta dirección:\n\n"
                    f"```{IP}```"
                ),
                color=discord.Color.green()
            )

            await message.channel.send(embed=embed)
            return

        # DISCORD
        if texto == "discord":
            embed = discord.Embed(
                title="💬 Discord de Pilares",
                description=(
                    "Únete a nuestra comunidad:\n\n"
                    f"{DISCORD_INVITE}"
                ),
                color=discord.Color.purple()
            )

            await message.channel.send(embed=embed)
            return

        # AYUDA
        if texto == "ayuda":
            embed = discord.Embed(
                title="📋 Información de Pilares",
                description=(
                    "**web** → enlace de la web\n"
                    "**ip** → IP del servidor Minecraft\n"
                    "**discord** → enlace del Discord"
                ),
                color=discord.Color.blurple()
            )

            await message.channel.send(embed=embed)
            return

    # Procesar comandos slash
    await bot.process_commands(message)


# =========================
# /ADMIN
# =========================

@bot.tree.command(
    name="admin",
    description="Da el rol DiDo Admin a un usuario."
)
@app_commands.describe(
    usuario="Usuario al que quieres dar el rol DiDo Admin"
)
async def admin(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    # Comprobar permisos
    if not isinstance(interaction.user, discord.Member):
        return

    if not es_administrador(interaction.user):
        await interaction.response.send_message(
            "❌ Necesitas permisos de **Administrador**.",
            ephemeral=True
        )
        return

    # Buscar rol
    rol = discord.utils.get(
        interaction.guild.roles,
        name="DiDo Admin"
    )

    # Crear rol si no existe
    if rol is None:
        try:
            rol = await interaction.guild.create_role(
                name="DiDo Admin",
                reason="Rol creado por DiDo Admin"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permiso para crear roles.",
                ephemeral=True
            )
            return

    # Comprobar jerarquía
    if rol >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ El rol **DiDo Admin** está por encima o al mismo nivel "
            "que mi rol. Coloca mi rol por encima de DiDo Admin.",
            ephemeral=True
        )
        return

    # Asignar rol
    try:
        await usuario.add_roles(
            rol,
            reason=f"Asignado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ {usuario.mention} ahora tiene el rol **DiDo Admin**."
        )

    except discord.For

