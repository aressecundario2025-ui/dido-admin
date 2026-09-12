import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import datetime
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")

# Canal donde DiDo Admin registra baneos
CANAL_BANEOS = 1546534756441653261

# Canal donde DiDo Admin anuncia vídeos de YouTube
CANAL_YOUTUBE = 1546538212896280596

# Canal de YouTube
YOUTUBE_URL = "https://youtube.com/@zerronova2026_yt"

# Intervalo de comprobación de YouTube
YOUTUBE_INTERVALO_MINUTOS = 5

# Silencio automático por spam
SPAM_MENSAJES = 6
SPAM_SEGUNDOS = 8
SPAM_TIMEOUT_MINUTOS = 5

# Archivo local para recordar el último vídeo
YOUTUBE_STATE_FILE = "youtube_state.json"

# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =========================================================
# DATOS EN MEMORIA
# =========================================================

warnings = defaultdict(list)
spam_tracker = defaultdict(lambda: deque())

# =========================================================
# UTILIDADES
# =========================================================

def canal(id_canal):
    return bot.get_channel(id_canal)


async def enviar_log_ban(guild, miembro, moderador, motivo):
    canal_log = canal(CANAL_BANEOS)

    if not canal_log:
        print(f"⚠️ No encuentro el canal de baneos: {CANAL_BANEOS}")
        return

    embed = discord.Embed(
        title="🔨 Baneo realizado",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 Usuario",
        value=f"{miembro} (`{miembro.id}`)",
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderador",
        value=f"{moderador} (`{moderador.id}`)",
        inline=False
    )

    embed.add_field(
        name="📝 Motivo",
        value=motivo,
        inline=False
    )

    embed.set_footer(text=f"Servidor: {guild.name}")

    await canal_log.send(embed=embed)


async def timeout_miembro(miembro, minutos, motivo):
    await miembro.timeout(
        datetime.timedelta(minutes=minutos),
        reason=motivo
    )


# =========================================================
# EVENTO READY
# =========================================================

@bot.event
async def on_ready():
    print("========================================")
    print("🤖 DiDo Admin")
    print("========================================")
    print(f"Conectado como: {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"Canal baneos: {CANAL_BANEOS}")
    print(f"Canal YouTube: {CANAL_YOUTUBE}")
    print(f"YouTube: {YOUTUBE_URL}")
    print("Moderación: ACTIVADA")
    print("Anti-spam: ACTIVADO")
    print("========================================")

    if not youtube_checker.is_running():
        youtube_checker.start()


# =========================================================
# COMANDOS DE MODERACIÓN
# =========================================================

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, miembro: discord.Member, *, motivo="Sin motivo"):
    if miembro == ctx.author:
        await ctx.send("😂 No puedes banearte a ti mismo.")
        return

    if miembro == ctx.guild.owner:
        await ctx.send("⚠️ No puedo banear al propietario del servidor.")
        return

    if miembro.top_role >= ctx.guild.me.top_role:
        await ctx.send("⚠️ Ese usuario tiene un rol igual o superior al mío.")
        return

    try:
        await miembro.ban(reason=f"{motivo} | Moderador: {ctx.author}")
        await ctx.send(f"🔨 **{miembro}** ha sido baneado.")

        await enviar_log_ban(
            ctx.guild,
            miembro,
            ctx.author,
            motivo
        )

    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos suficientes para banearlo.")


@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx, *, usuario_id: int):
    try:
        usuario = await bot.fetch_user(usuario_id)
        await ctx.guild.unban(
            usuario,
            reason=f"Desbaneado por {ctx.author}"
        )
        await ctx.send(f"✅ **{usuario}** ha sido desbaneado.")
    except discord.NotFound:
        await ctx.send("❌ No encuentro a ese usuario baneado.")
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos para desbanear.")


@bot.command()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, miembro: discord.Member, *, motivo="Sin motivo"):
    if miembro == ctx.guild.owner:
        await ctx.send("⚠️ No puedo expulsar al propietario.")
        return

    if miembro.top_role >= ctx.guild.me.top_role:
        await ctx.send("⚠️ Ese usuario tiene un rol igual o superior al mío.")
        return

    try:
        await miembro.kick(reason=f"{motivo} | Moderador: {ctx.author}")
        await ctx.send(f"👢 **{miembro}** ha sido expulsado.")
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos suficientes.")


@bot.command(aliases=["mute", "timeout"])
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def silenciar(ctx, miembro: discord.Member, minutos: int = 10, *, motivo="Sin motivo"):
    if minutos < 1 or minutos > 40320:
        await ctx.send("⚠️ El tiempo debe estar entre 1 minuto y 28 días.")
        return

    if miembro == ctx.guild.owner:
        await ctx.send("⚠️ No puedo silenciar al propietario.")
        return

    if miembro.top_role >= ctx.guild.me.top_role:
        await ctx.send("⚠️ Ese usuario tiene un rol igual o superior al mío.")
        return

    try:
        await timeout_miembro(
            miembro,
            minutos,
            f"{motivo} | Moderador: {ctx.author}"
        )
        await ctx.send(
            f"🔇 **{miembro}** ha sido silenciado durante **{minutos} minutos**."
        )
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos suficientes.")


@bot.command(aliases=["unmute", "untimeout"])
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def unsilenciar(ctx, miembro: discord.Member):
    try:
        await miembro.timeout(
            None,
            reason=f"Silencio retirado por {ctx.author}"
        )
        await ctx.send(f"🔊 **{miembro}** ya puede hablar.")
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos suficientes.")


# =========================================================
# WARNINGS
# =========================================================

@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, miembro: discord.Member, *, motivo="Sin motivo"):
    warnings[miembro.id].append({
        "moderador": str(ctx.author),
        "motivo": motivo,
        "fecha": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    total = len(warnings[miembro.id])

    await ctx.send(
        f"⚠️ **{miembro}** ha recibido un aviso. "
        f"Total: **{total}**."
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warns(ctx, miembro: discord.Member):
    lista = warnings.get(miembro.id, [])

    if not lista:
        await ctx.send(f"✅ **{miembro}** no tiene avisos.")
        return

    embed = discord.Embed(
        title=f"⚠️ Avisos de {miembro}",
        color=discord.Color.orange()
    )

    for i, aviso in enumerate(lista, 1):
        embed.add_field(
            name=f"Aviso {i}",
            value=(
                f"**Motivo:** {aviso['motivo']}\n"
                f"**Moderador:** {aviso['moderador']}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, miembro: discord.Member):
    warnings.pop(miembro.id, None)
    await ctx.send(f"🧹 Avisos de **{miembro}** eliminados.")


# =========================================================
# MENSAJES / CANALES
# =========================================================

@bot.command(aliases=["purge", "limpiar"])
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear(ctx, cantidad: int):
    if cantidad < 1 or cantidad > 100:
        await ctx.send("⚠️ Puedes borrar entre 1 y 100 mensajes.")
        return

    mensajes = await ctx.channel.purge(limit=cantidad + 1)
    aviso = await ctx.send(
        f"🧹 He borrado **{len(mensajes) - 1}** mensajes."
    )
    await asyncio.sleep(3)
    try:
        await aviso.delete()
    except discord.HTTPException:
        pass


@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx):
    overwrites = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrites.send_messages = False

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrites,
        reason=f"Canal bloqueado por {ctx.author}"
    )

    await ctx.send("🔒 Canal bloqueado.")


@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx):
    overwrites = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrites.send_messages = True

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrites,
        reason=f"Canal desbloqueado por {ctx.author}"
    )

    await ctx.send("🔓 Canal desbloqueado.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, segundos: int):
    if segundos < 0 or segundos > 21600:
        await ctx.send("⚠️ Usa entre 0 y 21600 segundos.")
        return

    await ctx.channel.edit(
        slowmode_delay=segundos,
        reason=f"Slowmode cambiado por {ctx.author}"
    )

    await ctx.send(f"⏱️ Slowmode: **{segundos} segundos**.")


# =========================================================
# ROLES
# =========================================================

@bot.command()
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def addrole(ctx, miembro: discord.Member, *, rol: discord.Role):
    if rol >= ctx.guild.me.top_role:
        await ctx.send("⚠️ No puedo gestionar ese rol.")
        return

    await miembro.add_roles(
        rol,
        reason=f"Rol añadido por {ctx.author}"
    )
    await ctx.send(f"✅ Rol **{rol.name}** añadido a **{miembro}**.")


@bot.command()
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def removerole(ctx, miembro: discord.Member, *, rol: discord.Role):
    if rol >= ctx.guild.me.top_role:
        await ctx.send("⚠️ No puedo gestionar ese rol.")
        return

    await miembro.remove_roles(
        rol,
        reason=f"Rol quitado por {ctx.author}"
    )
    await ctx.send(f"✅ Rol **{rol.name}** quitado a **{miembro}**.")


# =========================================================
# INFORMACIÓN
# =========================================================

@bot.command()
async def userinfo(ctx, miembro: discord.Member = None):
    miembro = miembro or ctx.author

    embed = discord.Embed(
        title=f"👤 Información de {miembro}",
        color=discord.Color.blurple()
    )

    embed.add_field(name="ID", value=str(miembro.id), inline=False)
    embed.add_field(name="Nombre", value=str(miembro), inline=False)
    embed.add_field(
        name="Cuenta creada",
        value=discord.utils.format_dt(miembro.created_at, "F"),
        inline=False
    )
    embed.add_field(
        name="Entró al servidor",
        value=(
            discord.utils.format_dt(miembro.joined_at, "F")
            if miembro.joined_at else "Desconocido"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(name="ID", value=str(guild.id), inline=False)
    embed.add_field(name="Miembros", value=str(guild.member_count), inline=False)
    embed.add_field(name="Canales", value=str(len(guild.channels)), inline=False)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=False)
    embed.add_field(
        name="Creado",
        value=discord.utils.format_dt(guild.created_at, "F"),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def permisos(ctx, miembro: discord.Member = None):
    miembro = miembro or ctx.author
    p = miembro.guild_permissions

    permisos_lista = [
        f"Administrador: {'✅' if p.administrator else '❌'}",
        f"Banear: {'✅' if p.ban_members else '❌'}",
        f"Expulsar: {'✅' if p.kick_members else '❌'}",
        f"Gestionar mensajes: {'✅' if p.manage_messages else '❌'}",
        f"Moderar miembros: {'✅' if p.moderate_members else '❌'}",
        f"Gestionar roles: {'✅' if p.manage_roles else '❌'}",
        f"Gestionar canales: {'✅' if p.manage_channels else '❌'}",
        f"Gestionar servidor: {'✅' if p.manage_guild else '❌'}"
    ]

    await ctx.send(
        f"🛡️ **Permisos de {miembro}**\n" +
        "\n".join(permisos_lista)
    )


# =========================================================
# AYUDA
# =========================================================

@bot.command(name="ayuda")
async def ayuda(ctx):
    embed = discord.Embed(
        title="🛡️ DiDo Admin",
        description="Comandos disponibles:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Moderación",
        value=(
            "`!ban @usuario motivo`\n"
            "`!unban ID`\n"
            "`!kick @usuario motivo`\n"
            "`!silenciar @usuario minutos motivo`\n"
            "`!unsilenciar @usuario`\n"
            "`!warn @usuario motivo`\n"
            "`!warns @usuario`\n"
            "`!clearwarns @usuario`"
        ),
        inline=False
    )

    embed.add_field(
        name="Servidor",
        value=(
            "`!clear 10`\n"
            "`!lock`\n"
            "`!unlock`\n"
            "`!slowmode 10`\n"
            "`!addrole @usuario @rol`\n"
            "`!removerole @usuario @rol`"
        ),
        inline=False
    )

    embed.add_field(
        name="Información",
        value=(
            "`!userinfo @usuario`\n"
            "`!serverinfo`\n"
            "`!permisos @usuario`"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# =========================================================
# ANTI-SPAM
# =========================================================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    ahora = datetime.datetime.now(datetime.timezone.utc).timestamp()
    clave = (message.guild.id, message.author.id)

    cola = spam_tracker[clave]
    cola.append(ahora)

    while cola and ahora - cola[0] > SPAM_SEGUNDOS:
        cola.popleft()

    if len(cola) >= SPAM_MENSAJES:
        miembro = message.author

        if (
            miembro != message.guild.owner
            and miembro.top_role < message.guild.me.top_role
            and message.guild.me.guild_permissions.moderate_members
        ):
            try:
                await timeout_miembro(
                    miembro,
                    SPAM_TIMEOUT_MINUTOS,
                    "Anti-spam automático"
                )

                await message.channel.send(
                    f"🔇 {miembro.mention} ha sido silenciado "
                    f"**{SPAM_TIMEOUT_MINUTOS} minutos** por spam."
                )

                cola.clear()

            except discord.HTTPException:
                pass

    await bot.process_commands(message)


# =========================================================
# MANEJO DE ERRORES
# =========================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ No tienes permisos para usar este comando.")
        return

    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("⛔ A DiDo Admin le faltan permisos para hacer eso.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Faltan argumentos. Usa `!ayuda`.")
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ No encuentro a ese usuario.")
        return

    if isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ No encuentro ese rol.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ El argumento no es válido.")
        return

    print(f"❌ Error de comando: {error}")


# =========================================================
# YOUTUBE
# =========================================================

def cargar_estado_youtube():
    if not os.path.exists(YOUTUBE_STATE_FILE):
        return None

    try:
        with open(YOUTUBE_STATE_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return datos.get("video_id")
    except Exception:
        return None


def guardar_estado_youtube(video_id):
    try:
        with open(YOUTUBE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id}, f)
    except Exception as e:
        print(f"⚠️ No se pudo guardar estado de YouTube: {e}")


async def obtener_channel_id():
    """
    Obtiene el ID del canal a partir del enlace @handle.
    Se usa yt-dlp para evitar tener que configurar una API de YouTube.
    """
    try:
        proceso = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "yt_dlp",
            "--flat-playlist",
            "--playlist-end",
            "1",
            "--print",
            "channel_id",
            YOUTUBE_URL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proceso.communicate()

        if proceso.returncode != 0:
            print(
                "❌ No pude obtener el ID de YouTube:\n"
                + stderr.decode(errors="ignore")
            )
            return None

        texto = stdout.decode(errors="ignore").strip()

        for linea in texto.splitlines():
            linea = linea.strip()
            if re.fullmatch(r"UC[a-zA-Z0-9_-]{20,}", linea):
                return linea

    except Exception as e:
        print(f"❌ Error obteniendo ID de YouTube: {e}")

    return None


async def obtener_ultimo_video(channel_id):
    url = (
        "https://www.youtube.com/feeds/videos.xml"
        f"?channel_id={channel_id}"
    )

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as respuesta:

            if respuesta.status != 200:
                print(
                    f"⚠️ RSS de YouTube devolvió HTTP {respuesta.status}"
                )
                return None

            contenido = await respuesta.text()

    root = ET.fromstring(contenido)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015"
    }

    entrada = root.find("atom:entry", ns)

    if entrada is None:
        return None

    video_id = entrada.findtext("yt:videoId", default="", namespaces=ns)
    titulo = entrada.findtext("atom:title", default="Nuevo vídeo", namespaces=ns)
    enlace = entrada.find("atom:link", ns)

    video_url = (
        enlace.attrib.get("href")
        if enlace is not None
        else f"https://www.youtube.com/watch?v={video_id}"
    )

    publicado = entrada.findtext(
        "atom:published",
        default="",
        namespaces=ns
    )

    return {
        "id": video_id,
        "titulo": titulo,
        "url": video_url,
        "publicado": publicado
    }


youtube_channel_id = None
youtube_primera_comprobacion = True


@tasks.loop(minutes=YOUTUBE_INTERVALO_MINUTOS)
async def youtube_checker():
    global youtube_channel_id
    global youtube_primera_comprobacion

    if youtube_channel_id is None:
        youtube_channel_id = await obtener_channel_id()

        if youtube_channel_id:
            print(f"✅ Canal YouTube detectado: {youtube_channel_id}")
        else:
            print("⚠️ No se pudo detectar el canal de YouTube.")
            return

    try:
        video = await obtener_ultimo_video(youtube_channel_id)

        if not video:
            return

        ultimo_guardado = cargar_estado_youtube()

        # Primera comprobación: guardar el vídeo actual sin anunciarlo.
        # Así no manda un aviso falso al arrancar Railway.
        if ultimo_guardado is None or youtube_primera_comprobacion:
            guardar_estado_youtube(video["id"])
            youtube_primera_comprobacion = False
            print(
                f"📺 YouTube inicializado con: "
                f"{video['titulo']}"
            )
            return

        if video["id"] == ultimo_guardado:
            return

        guardar_estado_youtube(video["id"])

        canal_youtube = canal(CANAL_YOUTUBE)

        if not canal_youtube:
            print(
                f"⚠️ No encuentro el canal Discord de YouTube: "
                f"{CANAL_YOUTUBE}"
            )
            return

        embed = discord.Embed(
            title="📺 ¡Nuevo vídeo de ZerroNova!",
            description=f"**{video['titulo']}**\n\n{video['url']}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(text="DiDo Admin • YouTube")

        await canal_youtube.send(embed=embed)

        print(
            f"📺 Nuevo vídeo anunciado: {video['titulo']}"
        )

    except Exception as e:
        print(f"❌ Error comprobando YouTube: {e}")


@youtube_checker.before_loop
async def before_youtube_checker():
    await bot.wait_until_ready()


# =========================================================
# ARRANQUE
# =========================================================

if not TOKEN_DISCORD:
    raise RuntimeError(
        "Falta TOKEN_DISCORD en las variables de entorno."
    )

bot.run(TOKEN_DISCORD)
