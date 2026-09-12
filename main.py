import os
from datetime import timedelta

import discord
from discord.ext import commands
from discord import app_commands


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")

# Tu ID de Discord
ID_CREADOR = 1439941330355879978

# ID DEL SERVIDOR DONDE QUIERES LOS COMANDOS
ID_SERVIDOR = 1544430992364802178

# Nombre del rol de administrador
NOMBRE_ROL_ADMIN = "DiDo Admin"


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# =========================================================
# BOT
# =========================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# COMPROBAR CREADOR
# =========================================================

def es_creador(interaction: discord.Interaction) -> bool:
    return interaction.user.id == ID_CREADOR


async def comprobar_creador(interaction: discord.Interaction) -> bool:

    if not es_creador(interaction):
        await interaction.response.send_message(
            "❌ No tienes permiso para usar este comando.",
            ephemeral=True
        )
        return False

    return True


# =========================================================
# OBTENER / CREAR ROL ADMIN
# =========================================================

async def obtener_rol_admin(guild: discord.Guild):

    rol = discord.utils.get(
        guild.roles,
        name=NOMBRE_ROL_ADMIN
    )

    if rol:
        return rol

    try:
        rol = await guild.create_role(
            name=NOMBRE_ROL_ADMIN,
            permissions=discord.Permissions(administrator=True),
            reason="Rol de administración de DiDo Admin"
        )

        return rol

    except discord.Forbidden:
        return None


# =========================================================
# BOT CONECTADO
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"🤖 DiDo Admin conectado como {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("====================================")

    guild = discord.Object(id=ID_SERVIDOR)

    try:
        # Copiar los comandos al servidor específico
        bot.tree.copy_global_to(guild=guild)

        # Sincronizarlos inmediatamente
        comandos = await bot.tree.sync(guild=guild)

        print(
            f"✅ {len(comandos)} comandos sincronizados "
            f"en el servidor {ID_SERVIDOR}."
        )

    except Exception as error:
        print(f"❌ Error sincronizando comandos: {error}")

    # Preparar el rol en el servidor
    servidor = bot.get_guild(ID_SERVIDOR)

    if servidor:

        rol = await obtener_rol_admin(servidor)

        if rol:
            print(
                f"🛡️ Rol '{NOMBRE_ROL_ADMIN}' preparado "
                f"en {servidor.name}"
            )

        else:
            print("❌ No pude crear/obtener el rol DiDo Admin.")

    else:
        print("❌ DiDo Admin no está dentro del servidor.")


# =========================================================
# /ADMIN
# =========================================================

@bot.tree.command(
    name="admin",
    description="Da el rol de Administrador a un usuario."
)
@app_commands.describe(
    usuario="Usuario al que quieres dar Administrador"
)
async def admin(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not await comprobar_creador(interaction):
        return

    rol = await obtener_rol_admin(interaction.guild)

    if rol is None:
        await interaction.response.send_message(
            "❌ No puedo crear el rol DiDo Admin.",
            ephemeral=True
        )
        return

    if rol >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Mi rol está por debajo del rol DiDo Admin. "
            "Pon el rol del bot por encima.",
            ephemeral=True
        )
        return

    try:

        await usuario.add_roles(
            rol,
            reason=f"Administrador dado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"🛡️ {usuario.mention} ahora tiene **DiDo Admin**."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Discord no me permite darle ese rol.",
            ephemeral=True
        )


# =========================================================
# /QUITARADMIN
# =========================================================

@bot.tree.command(
    name="quitaradmin",
    description="Quita el rol DiDo Admin."
)
@app_commands.describe(
    usuario="Usuario al que quieres quitar Administrador"
)
async def quitaradmin(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not await comprobar_creador(interaction):
        return

    rol = discord.utils.get(
        interaction.guild.roles,
        name=NOMBRE_ROL_ADMIN
    )

    if not rol:
        await interaction.response.send_message(
            "❌ No existe el rol DiDo Admin.",
            ephemeral=True
        )
        return

    try:

        await usuario.remove_roles(
            rol,
            reason=f"Administrador quitado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Se ha quitado DiDo Admin a {usuario.mention}."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo quitar ese rol.",
            ephemeral=True
        )


# =========================================================
# /BAN
# =========================================================

@bot.tree.command(
    name="ban",
    description="Banea a un usuario."
)
@app_commands.describe(
    usuario="Usuario a banear",
    motivo="Motivo del baneo"
)
async def ban(
    interaction: discord.Interaction,
    usuario: discord.Member,
    motivo: str = "Sin especificar"
):

    if not await comprobar_creador(interaction):
        return

    try:

        await usuario.ban(
            reason=motivo,
            delete_message_days=1
        )

        await interaction.response.send_message(
            f"🔨 {usuario.mention} ha sido baneado.\n"
            f"📝 Motivo: {motivo}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo banear a ese usuario.",
            ephemeral=True
        )


# =========================================================
# /KICK
# =========================================================

@bot.tree.command(
    name="kick",
    description="Expulsa a un usuario."
)
@app_commands.describe(
    usuario="Usuario a expulsar",
    motivo="Motivo"
)
async def kick(
    interaction: discord.Interaction,
    usuario: discord.Member,
    motivo: str = "Sin especificar"
):

    if not await comprobar_creador(interaction):
        return

    try:

        await usuario.kick(reason=motivo)

        await interaction.response.send_message(
            f"👢 {usuario.mention} ha sido expulsado.\n"
            f"📝 Motivo: {motivo}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo expulsar a ese usuario.",
            ephemeral=True
        )


# =========================================================
# /TIMEOUT
# =========================================================

@bot.tree.command(
    name="timeout",
    description="Pone a un usuario en timeout."
)
@app_commands.describe(
    usuario="Usuario al que poner timeout",
    minutos="Minutos de timeout",
    motivo="Motivo"
)
async def timeout(
    interaction: discord.Interaction,
    usuario: discord.Member,
    minutos: int,
    motivo: str = "Sin especificar"
):

    if not await comprobar_creador(interaction):
        return

    if minutos < 1 or minutos > 40320:

        await interaction.response.send_message(
            "❌ El tiempo debe estar entre 1 y 40320 minutos.",
            ephemeral=True
        )
        return

    try:

        hasta = discord.utils.utcnow() + timedelta(
            minutes=minutos
        )

        await usuario.timeout(
            hasta,
            reason=motivo
        )

        await interaction.response.send_message(
            f"⏱️ {usuario.mention} tiene timeout durante "
            f"**{minutos} minutos**."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo ponerle timeout.",
            ephemeral=True
        )


# =========================================================
# /UNBAN
# =========================================================

@bot.tree.command(
    name="unban",
    description="Desbanea usando la ID de Discord."
)
@app_commands.describe(
    usuario_id="ID del usuario"
)
async def unban(
    interaction: discord.Interaction,
    usuario_id: str
):

    if not await comprobar_creador(interaction):
        return

    try:

        usuario = await bot.fetch_user(
            int(usuario_id)
        )

        await interaction.guild.unban(
            usuario,
            reason=f"Desbaneo realizado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ {usuario} ha sido desbaneado."
        )

    except ValueError:

        await interaction.response.send_message(
            "❌ La ID no es válida.",
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
# /CLEAR
# =========================================================

@bot.tree.command(
    name="clear",
    description="Borra mensajes del canal."
)
@app_commands.describe(
    cantidad="Cantidad de mensajes a borrar"
)
async def clear(
    interaction: discord.Interaction,
    cantidad: int
):

    if not await comprobar_creador(interaction):
        return

    if cantidad < 1 or cantidad > 100:

        await interaction.response.send_message(
            "❌ La cantidad debe estar entre 1 y 100.",
            ephemeral=True
        )
        return

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ Este comando solo funciona en canales de texto.",
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
            f"🧹 He borrado **{len(mensajes)} mensajes**.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ No tengo permiso para borrar mensajes.",
            ephemeral=True
        )


# =========================================================
# /PERMISOS
# =========================================================

@bot.tree.command(
    name="permisos",
    description="Muestra los permisos de un usuario."
)
@app_commands.describe(
    usuario="Usuario que quieres comprobar"
)
async def permisos(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    p = usuario.guild_permissions

    texto = (
        f"👤 **{usuario.display_name}**\n\n"
        f"👑 Administrador: **{'Sí' if p.administrator else 'No'}**\n"
        f"🔨 Banear: **{'Sí' if p.ban_members else 'No'}**\n"
        f"👢 Expulsar: **{'Sí' if p.kick_members else 'No'}**\n"
        f"⏱️ Timeout: **{'Sí' if p.moderate_members else 'No'}**\n"
        f"🧹 Gestionar mensajes: **{'Sí' if p.manage_messages else 'No'}**\n"
        f"🔧 Gestionar servidor: **{'Sí' if p.manage_guild else 'No'}**\n"
        f"🎭 Gestionar roles: **{'Sí' if p.manage_roles else 'No'}**\n"
        f"📢 Gestionar canales: **{'Sí' if p.manage_channels else 'No'}**"
    )

    await interaction.response.send_message(
        texto
    )


# =========================================================
# /SERVERINFO
# =========================================================

@bot.tree.command(
    name="serverinfo",
    description="Muestra información del servidor."
)
async def serverinfo(
    interaction: discord.Interaction
):

    guild = interaction.guild

    texto = (
        f"🏠 **{guild.name}**\n\n"
        f"🆔 ID: `{guild.id}`\n"
        f"👥 Miembros: **{guild.member_count}**\n"
        f"💬 Canales: **{len(guild.channels)}**\n"
        f"🎭 Roles: **{len(guild.roles)}**\n"
        f"👑 Dueño: **{guild.owner}**"
    )

    await interaction.response.send_message(
        texto
    )


# =========================================================
# /INFO
# =========================================================

@bot.tree.command(
    name="info",
    description="Información sobre DiDo Admin."
)
async def info(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "🤖 **DiDo Admin**\n\n"
        "🛡️ Administración\n"
        "🔨 Moderación\n"
        "🎭 Roles\n"
        "🧹 Limpieza\n"
        "🔐 Comandos protegidos\n\n"
        "Creado por Ares."
    )


# =========================================================
# MENSAJES
# =========================================================

@bot.event
async def on_message(
    message: discord.Message
):

    if message.author.bot:
        return

    await bot.process_commands(message)


# =========================================================
# ERRORES
# =========================================================

@bot.tree.error
async def error_comando(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(f"ERROR: {error}")

    if interaction.response.is_done():

        await interaction.followup.send(
            "❌ Ha ocurrido un error.",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ Ha ocurrido un error.",
            ephemeral=True
        )


# =========================================================
# ARRANQUE
# =========================================================

if not TOKEN_DISCORD:

    raise RuntimeError(
        "❌ Falta TOKEN_DISCORD en las variables de Railway."
    )


bot.run(TOKEN_DISCORD)

