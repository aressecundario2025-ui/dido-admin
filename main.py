import os
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")

# PON AQUÍ TU ID DE DISCORD
ID_CREADOR = 123456789012345678


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True


# =========================================================
# BOT
# =========================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# CUANDO EL BOT SE CONECTA
# =========================================================

@bot.event
async def on_ready():
    print(f"================================")
    print(f"✅ DiDo-ADMIN conectado")
    print(f"🤖 Usuario: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"================================")

    try:
        comandos = await bot.tree.sync()
        print(f"✅ {len(comandos)} comandos / sincronizados")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")


# =========================================================
# COMPROBAR ADMIN
# =========================================================

def es_admin(interaction: discord.Interaction) -> bool:

    if interaction.user.id == ID_CREADOR:
        return True

    if not isinstance(interaction.user, discord.Member):
        return False

    return interaction.user.guild_permissions.administrator


# =========================================================
# /PING
# =========================================================

@bot.tree.command(
    name="ping",
    description="Comprueba si DiDo está funcionando"
)
async def ping(interaction: discord.Interaction):

    latencia = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 Pong! **{latencia} ms**"
    )


# =========================================================
# /ADMIN
# =========================================================

@bot.tree.command(
    name="admin",
    description="Da el rol ADMIN a un usuario"
)
@app_commands.describe(
    usuario="Usuario al que quieres dar el rol ADMIN"
)
async def admin(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos para usar este comando.",
            ephemeral=True
        )
        return

    rol = discord.utils.get(
        interaction.guild.roles,
        name="ADMIN"
    )

    if rol is None:
        await interaction.response.send_message(
            "❌ No existe un rol llamado `ADMIN`.",
            ephemeral=True
        )
        return

    if rol >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Mi rol debe estar por encima del rol `ADMIN`.",
            ephemeral=True
        )
        return

    try:

        await usuario.add_roles(rol)

        await interaction.response.send_message(
            f"👑 {usuario.mention} ahora tiene el rol **ADMIN**."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo darle ese rol.",
            ephemeral=True
        )


# =========================================================
# /KICK
# =========================================================

@bot.tree.command(
    name="kick",
    description="Expulsa a un usuario del servidor"
)
@app_commands.describe(
    usuario="Usuario que quieres expulsar",
    motivo="Motivo de la expulsión"
)
async def kick(
    interaction: discord.Interaction,
    usuario: discord.Member,
    motivo: str = "Sin motivo"
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )
        return

    if usuario == interaction.user:
        await interaction.response.send_message(
            "❌ No puedes expulsarte a ti mismo.",
            ephemeral=True
        )
        return

    try:

        await usuario.kick(reason=motivo)

        await interaction.response.send_message(
            f"👢 **Usuario expulsado**\n"
            f"👤 Usuario: {usuario.mention}\n"
            f"📝 Motivo: {motivo}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo expulsar a ese usuario.",
            ephemeral=True
        )


# =========================================================
# /BAN
# =========================================================

@bot.tree.command(
    name="ban",
    description="Banea a un usuario"
)
@app_commands.describe(
    usuario="Usuario que quieres banear",
    motivo="Motivo del baneo"
)
async def ban(
    interaction: discord.Interaction,
    usuario: discord.Member,
    motivo: str = "Sin motivo"
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )
        return

    if usuario == interaction.user:
        await interaction.response.send_message(
            "❌ No puedes banearte a ti mismo.",
            ephemeral=True
        )
        return

    try:

        await usuario.ban(
            reason=motivo
        )

        await interaction.response.send_message(
            f"🔨 **Usuario baneado**\n"
            f"👤 Usuario: {usuario.mention}\n"
            f"📝 Motivo: {motivo}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo banear a ese usuario.",
            ephemeral=True
        )


# =========================================================
# /UNBAN
# =========================================================

@bot.tree.command(
    name="unban",
    description="Desbanea a un usuario usando su ID"
)
@app_commands.describe(
    usuario_id="ID de Discord del usuario"
)
async def unban(
    interaction: discord.Interaction,
    usuario_id: str
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )
        return

    try:

        user_id = int(usuario_id)

        usuario = await bot.fetch_user(
            user_id
        )

        await interaction.guild.unban(
            usuario
        )

        await interaction.response.send_message(
            f"✅ **{usuario}** ha sido desbaneado."
        )

    except ValueError:

        await interaction.response.send_message(
            "❌ La ID introducida no es válida.",
            ephemeral=True
        )

    except discord.NotFound:

        await interaction.response.send_message(
            "❌ Ese usuario no está baneado.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No tengo permiso para desbanear.",
            ephemeral=True
        )


# =========================================================
# /TIMEOUT
# =========================================================

@bot.tree.command(
    name="timeout",
    description="Pone un timeout a un usuario"
)
@app_commands.describe(
    usuario="Usuario al que quieres poner timeout",
    minutos="Duración del timeout en minutos",
    motivo="Motivo"
)
async def timeout(
    interaction: discord.Interaction,
    usuario: discord.Member,
    minutos: int,
    motivo: str = "Sin motivo"
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )
        return

    if minutos < 1:

        await interaction.response.send_message(
            "❌ Los minutos deben ser mayores que 0.",
            ephemeral=True
        )
        return

    if minutos > 40320:

        await interaction.response.send_message(
            "❌ El máximo es de 28 días.",
            ephemeral=True
        )
        return

    try:

        duracion = timedelta(
            minutes=minutos
        )

        await usuario.timeout(
            duracion,
            reason=motivo
        )

        await interaction.response.send_message(
            f"⏱️ **Timeout aplicado**\n"
            f"👤 Usuario: {usuario.mention}\n"
            f"⏳ Duración: **{minutos} minutos**\n"
            f"📝 Motivo: {motivo}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo ponerle timeout a ese usuario.",
            ephemeral=True
        )


# =========================================================
# /UNTIMEOUT
# =========================================================

@bot.tree.command(
    name="untimeout",
    description="Quita el timeout de un usuario"
)
@app_commands.describe(
    usuario="Usuario al que quieres quitar el timeout"
)
async def untimeout(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )
        return

    try:

        await usuario.timeout(
            None,
            reason="Timeout eliminado"
        )

        await interaction.response.send_message(
            f"🔊 Timeout eliminado a {usuario.mention}."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo quitarle el timeout.",
            ephemeral=True
        )


# =========================================================
# /CLEAR
# =========================================================

@bot.tree.command(
    name="clear",
    description="Borra mensajes del canal"
)
@app_commands.describe(
    cantidad="Cantidad de mensajes a borrar (1-100)"
)
async def clear(
    interaction: discord.Interaction,
    cantidad: int
):

    if not es_admin(interaction):
        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )
        return

    if cantidad < 1 or cantidad > 100:

        await interaction.response.send_message(
            "❌ La cantidad debe estar entre 1 y 100.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        mensajes = await interaction.channel.purge(
            limit=cantidad
        )

        await interaction.followup.send(
            f"🧹 Se han borrado **{len(mensajes)} mensajes**.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ No tengo permiso para borrar mensajes.",
            ephemeral=True
        )


# =========================================================
# /INFO
# =========================================================

@bot.tree.command(
    name="info",
    description="Muestra información de un usuario"
)
@app_commands.describe(
    usuario="Usuario del que quieres información"
)
async def info(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    embed = discord.Embed(
        title="👤 Información del usuario",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Usuario",
        value=usuario.mention,
        inline=False
    )

    embed.add_field(
        name="Nombre",
        value=str(usuario),
        inline=False
    )

    embed.add_field(
        name="ID",
        value=str(usuario.id),
        inline=False
    )

    embed.add_field(
        name="Cuenta creada",
        value=discord.utils.format_dt(
            usuario.created_at,
            style="F"
        ),
        inline=False
    )

    if usuario.joined_at:
        embed.add_field(
            name="Entró al servidor",
            value=discord.utils.format_dt(
                usuario.joined_at,
                style="F"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# ERROR GENERAL DE COMANDOS
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(f"❌ Error en comando: {error}")

    if interaction.response.is_done():
        await interaction.followup.send(
            "❌ Ha ocurrido un error al ejecutar el comando.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Ha ocurrido un error al ejecutar el comando.",
            ephemeral=True
        )


# =========================================================
# ARRANCAR BOT
# =========================================================

if not TOKEN_DISCORD:

    print("❌ ERROR: No existe la variable TOKEN_DISCORD.")
    raise SystemExit(1)


bot.run(TOKEN_DISCORD)