import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

CANALES_PANEL = [
    1434297124539076738,
    1551198802164064266
]

# LOS DOS SON ROLES DE SOPORTE
ROL_SOPORTE_1 = 1434289818992382084
ROL_SOPORTE_2 = 1552374542909833246

LOGO_PATH = "logo.png"

COLOR = discord.Color.from_rgb(88, 101, 242)


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# EMOJIS
# =========================================================

EMOJI_IDS = {
    "ayuda": "54967105671957",
    "atencion": "1219816049822666893",
    "reglas": "3057195671616",
    "regla1": "0974966496677",
    "regla2": "30571957289",
    "regla3": "205719567E93093984",
    "regla4": "4947569375939420",
    "regla5": "30572935723",
    "rapido": "1216991711872684052",
    "rapido2": "1216999826248437784",
    "paciencia": "1195801251850502175"
}

EMOJIS = {}


async def cargar_emoji(nombre, emoji_id):

    try:

        if not str(emoji_id).isdigit():

            print(
                f"[EMOJI] ⚠️ ID inválido: {emoji_id}"
            )

            EMOJIS[nombre] = f":{emoji_id}:"
            return

        emoji_id = int(emoji_id)

        emoji = bot.get_emoji(emoji_id)

        if emoji is None:

            try:
                emoji = await bot.fetch_emoji(emoji_id)

            except discord.NotFound:
                emoji = None

            except discord.Forbidden:
                emoji = None

            except discord.HTTPException:
                emoji = None

        if emoji:

            EMOJIS[nombre] = str(emoji)

            print(
                f"[EMOJI] ✅ {nombre}: {emoji}"
            )

        else:

            EMOJIS[nombre] = f":{emoji_id}:"

            print(
                f"[EMOJI] ⚠️ No encontrado: {emoji_id}"
            )

    except Exception as e:

        print(
            f"[EMOJI] ❌ Error: {e}"
        )

        EMOJIS[nombre] = f":{emoji_id}:"


async def cargar_todos_los_emojis():

    print("🔎 Cargando emojis...")

    for nombre, emoji_id in EMOJI_IDS.items():

        await cargar_emoji(
            nombre,
            emoji_id
        )

    print("✅ Emojis cargados.")


def emoji(nombre):

    return EMOJIS.get(
        nombre,
        ""
    )


# =========================================================
# REGLAS
# =========================================================

def obtener_mensaje_reglas():

    return (
        f"{emoji('ayuda')} **¿Necesitas Ayuda? Abre un ticket en la categoría "
        f"que necesitas! Ten paciencia a la hora de abrir ticket o de lo "
        f"contrario serás sancionado!** {emoji('atencion')}\n\n"

        f"{emoji('reglas')} **Reglas** {emoji('reglas')}\n\n"

        f"{emoji('regla1')} *1)* **Ten paciencia a la hora de abrir ticket!** "
        f"{emoji('paciencia')}\n\n"

        f"{emoji('regla2')} *2)* **No insultar al equipo del staff!** "
        f"{emoji('atencion')}\n\n"

        f"{emoji('regla3')} *3)* **Estar activo en el ticket o de lo "
        f"contrario será cerrado por inactividad!** {emoji('paciencia')}\n\n"

        f"{emoji('regla4')} *4)* **Abrir ticket en su categoría que "
        f"corresponde o de lo contrario serás sancionado!**\n\n"

        f"{emoji('regla5')} *5)* **Abrir ticket sin razón es sancionable!** "
        f"{emoji('atencion')}\n\n\n"

        f"{emoji('rapido')} **Te atenderemos lo mas rápido posible!** "
        f"{emoji('rapido2')}"
    )


# =========================================================
# TIPOS DE TICKET
# =========================================================

TIPOS_TICKET = {
    "soporte": "🎫 Soporte general",
    "reportar": "🚨 Reportar usuario",
    "bug": "🐛 Reportar bug",
    "postulacion": "👥 Postulaciones",
    "estafa": "💰 Estafas"
}


# =========================================================
# BUSCAR TICKET
# =========================================================

async def buscar_ticket(guild, usuario):

    nombre = f"ticket-{usuario.id}"

    for canal in guild.text_channels:

        if canal.name == nombre:
            return canal

    return None


# =========================================================
# CREAR TICKET
# =========================================================

async def crear_ticket(
    interaction: discord.Interaction,
    tipo: str
):

    guild = interaction.guild
    usuario = interaction.user

    if guild is None:

        await interaction.followup.send(
            "❌ Este botón solo funciona dentro del servidor.",
            ephemeral=True
        )

        return

    # =====================================================
    # BUSCAR LOS DOS ROLES DE SOPORTE
    # =====================================================

    rol_soporte_1 = guild.get_role(
        ROL_SOPORTE_1
    )

    rol_soporte_2 = guild.get_role(
        ROL_SOPORTE_2
    )

    # Mostrar en consola qué encuentra
    print(
        f"[ROLES] Soporte 1: {rol_soporte_1}"
    )

    print(
        f"[ROLES] Soporte 2: {rol_soporte_2}"
    )

    # Si falta cualquiera de los dos
    if rol_soporte_1 is None or rol_soporte_2 is None:

        await interaction.followup.send(
            "❌ No encuentro uno de los dos roles de soporte. "
            "Comprueba que el bot esté en el servidor y que los IDs sean correctos.",
            ephemeral=True
        )

        return

    # =====================================================
    # COMPROBAR TICKET EXISTENTE
    # =====================================================

    ticket_existente = await buscar_ticket(
        guild,
        usuario
    )

    if ticket_existente:

        await interaction.followup.send(
            f"❌ Ya tienes un ticket abierto: {ticket_existente.mention}",
            ephemeral=True
        )

        return

    # =====================================================
    # PERMISOS
    # =====================================================

    permisos_usuario = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True
    )

    permisos_soporte = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
        manage_messages=True
    )

    permisos_bot = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        manage_channels=True,
        manage_messages=True
    )

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        usuario:
            permisos_usuario,

        rol_soporte_1:
            permisos_soporte,

        rol_soporte_2:
            permisos_soporte,

        guild.me:
            permisos_bot
    }

    # =====================================================
    # CREAR CANAL
    # =====================================================

    try:

        canal = await guild.create_text_channel(
            name=f"ticket-{usuario.id}",
            overwrites=overwrites,
            reason=f"Ticket creado por {usuario}"
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ No tengo permisos para crear canales.",
            ephemeral=True
        )

        return

    except Exception as e:

        print(
            f"[TICKET] ❌ Error creando canal: {e}"
        )

        await interaction.followup.send(
            "❌ Ha ocurrido un error creando el ticket.",
            ephemeral=True
        )

        return

    # =====================================================
    # EMBED
    # =====================================================

    nombre_tipo = TIPOS_TICKET.get(
        tipo,
        "🎫 Ticket"
    )

    embed = discord.Embed(
        title=nombre_tipo,
        description=(
            f"👋 Bienvenido/a {usuario.mention}.\n\n"
            "Un miembro del equipo de soporte te atenderá "
            "lo antes posible.\n\n"
            "🔒 Cuando hayas terminado, utiliza el botón "
            "**Cerrar ticket**."
        ),
        color=COLOR
    )

    embed.set_footer(
        text="Eclipse World • Sistema de tickets"
    )

    # =====================================================
    # MENCIÓN
    # =====================================================
    #
    # SOLO SE MENCIONA:
    # - Usuario
    # - ROL_SOPORTE_1
    #
    # ROL_SOPORTE_2 TIENE ACCESO PERO NO SE MENCIONA.
    #

    contenido = (
        f"{usuario.mention} "
        f"<@&{ROL_SOPORTE_1}>"
    )

    # =====================================================
    # ENVIAR MENSAJE
    # =====================================================

    try:

        if os.path.exists(LOGO_PATH):

            archivo = discord.File(
                LOGO_PATH,
                filename="logo.png"
            )

            embed.set_thumbnail(
                url="attachment://logo.png"
            )

            await canal.send(
                content=contenido,
                embed=embed,
                file=archivo,
                view=CerrarTicketView(),
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=True
                )
            )

        else:

            await canal.send(
                content=contenido,
                embed=embed,
                view=CerrarTicketView(),
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=True
                )
            )

        await interaction.followup.send(
            f"✅ Ticket creado correctamente: {canal.mention}",
            ephemeral=True
        )

        print(
            f"[TICKET] ✅ Creado: {canal.name}"
        )

    except Exception as e:

        print(
            f"[TICKET] ❌ Error enviando mensaje: {e}"
        )

        await interaction.followup.send(
            "⚠️ El ticket se creó, pero hubo un error enviando el mensaje.",
            ephemeral=True
        )


# =========================================================
# CERRAR TICKET
# =========================================================

class CerrarTicketView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="cerrar_ticket"
    )
    async def cerrar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        canal = interaction.channel

        if canal is None:
            return

        await interaction.response.send_message(
            "🔒 El ticket se cerrará en 5 segundos..."
        )

        await asyncio.sleep(5)

        try:

            await canal.delete(
                reason=f"Ticket cerrado por {interaction.user}"
            )

        except Exception as e:

            print(
                f"[TICKET] ❌ Error cerrando: {e}"
            )


# =========================================================
# PANEL
# =========================================================

class TicketView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Soporte general",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_soporte",
        row=0
    )
    async def soporte(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        await crear_ticket(
            interaction,
            "soporte"
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_reportar",
        row=0
    )
    async def reportar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        await crear_ticket(
            interaction,
            "reportar"
        )

    @discord.ui.button(
        label="Reportar bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_bug",
        row=1
    )
    async def bug(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        await crear_ticket(
            interaction,
            "bug"
        )

    @discord.ui.button(
        label="Postulaciones",
        emoji="👥",
        style=discord.ButtonStyle.success,
        custom_id="ticket_postulacion",
        row=1
    )
    async def postulacion(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        await crear_ticket(
            interaction,
            "postulacion"
        )

    @discord.ui.button(
        label="Estafas",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_estafa",
        row=1
    )
    async def estafa(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        await crear_ticket(
            interaction,
            "estafa"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"✅ BOT CONECTADO: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("====================================")

    try:

        # Cargar emojis
        await cargar_todos_los_emojis()

        # Registrar botones
        if not getattr(
            bot,
            "_views_registered",
            False
        ):

            bot.add_view(
                TicketView()
            )

            bot.add_view(
                CerrarTicketView()
            )

            bot._views_registered = True

            print(
                "✅ Botones registrados."
            )

        # Sincronizar slash commands
        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} comandos sincronizados."
        )

        # Comprobar roles en todos los servidores
        for guild in bot.guilds:

            print(
                f"🏠 Servidor: {guild.name}"
            )

            rol1 = guild.get_role(
                ROL_SOPORTE_1
            )

            rol2 = guild.get_role(
                ROL_SOPORTE_2
            )

            print(
                f"   Soporte 1: {rol1}"
            )

            print(
                f"   Soporte 2: {rol2}"
            )

    except Exception as e:

        print(
            f"❌ Error en on_ready: {e}"
        )


# =========================================================
# /TICKETPANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica el panel de tickets."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    enviados = 0

    for canal_id in CANALES_PANEL:

        canal = bot.get_channel(
            canal_id
        )

        if canal is None:

            print(
                f"❌ No encuentro el canal: {canal_id}"
            )

            continue

        try:

            # ---------------------------------------------
            # 1. REGLAS
            # ---------------------------------------------

            await canal.send(
                content=obtener_mensaje_reglas(),
                allowed_mentions=discord.AllowedMentions.none()
            )

            # ---------------------------------------------
            # 2. MENCIÓN DEL SOPORTE PRINCIPAL
            # ---------------------------------------------

            await canal.send(
                content=f"<@&{ROL_SOPORTE_1}>",
                allowed_mentions=discord.AllowedMentions(
                    roles=True
                )
            )

            # ---------------------------------------------
            # 3. PANEL
            # ---------------------------------------------

            embed = discord.Embed(
                color=COLOR
            )

            if os.path.exists(LOGO_PATH):

                archivo = discord.File(
                    LOGO_PATH,
                    filename="logo.png"
                )

                embed.set_image(
                    url="attachment://logo.png"
                )

                await canal.send(
                    embed=embed,
                    file=archivo,
                    view=TicketView()
                )

            else:

                await canal.send(
                    embed=embed,
                    view=TicketView()
                )

                print(
                    "⚠️ No existe logo.png"
                )

            enviados += 1

            print(
                f"✅ Panel enviado en {canal.name}"
            )

        except discord.Forbidden:

            print(
                f"❌ Sin permisos en {canal_id}"
            )

        except Exception as e:

            print(
                f"❌ Error en {canal_id}: {e}"
            )

    await interaction.followup.send(
        f"✅ Panel enviado a {enviados}/{len(CANALES_PANEL)} canales.",
        ephemeral=True
    )


# =========================================================
# ERROR DEL COMANDO
# =========================================================

@ticketpanel.error
async def ticketpanel_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        mensaje = (
            "❌ Necesitas ser administrador "
            "para usar este comando."
        )

    else:

        print(
            f"❌ Error /ticketpanel: {error}"
        )

        mensaje = (
            "❌ Ha ocurrido un error ejecutando "
            "el comando."
        )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                mensaje,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                mensaje,
                ephemeral=True
            )

    except Exception:
        pass


# =========================================================
# TOKEN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta DISCORD_TOKEN en las variables de Railway."
    )


# =========================================================
# INICIAR
# =========================================================

print("🚀 Iniciando bot...")

bot.run(TOKEN)