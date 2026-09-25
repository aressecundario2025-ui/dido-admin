import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("TOKEN_DISCORD")

# ==========================================
# CONFIGURACIÓN
# ==========================================

# Canales donde aparecerá el panel
CANALES_PANEL = [
    1434297124539076738,
    1551198802164064266
]

# Rol que recibirá/atenderá los tickets
ROL_SOPORTE = 1434289818992382084

# Categoría donde se crearán los tickets
# Si no quieres categoría, déjalo en 0
CATEGORIA_TICKETS = 0

# ==========================================
# LOGO DE ECLIPSE WORLD
# ==========================================
# Pega aquí el enlace directo a la imagen del logo.
# Ejemplo:
# https://cdn.discordapp.com/attachments/....../logo.png

IMAGEN_LOGO = "PEGA_AQUI_EL_ENLACE_DEL_LOGO"


# ==========================================
# BOT
# ==========================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==========================================
# INICIO
# ==========================================

@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync()

        bot.add_view(TicketView())

        print(
            f"🌑 Eclipse World | Tickets conectado como {bot.user}"
        )

        print(
            f"✅ {len(synced)} comandos sincronizados"
        )

    except Exception as e:
        print(f"❌ Error iniciando el bot: {e}")


# ==========================================
# CREAR TICKET
# ==========================================

async def crear_ticket(
    interaction: discord.Interaction,
    tipo: str
):

    guild = interaction.guild
    usuario = interaction.user

    rol_soporte = guild.get_role(ROL_SOPORTE)

    if rol_soporte is None:

        await interaction.response.send_message(
            "❌ No encuentro el rol de soporte configurado.",
            ephemeral=True
        )

        return

    # ======================================
    # COMPROBAR TICKET EXISTENTE
    # ======================================

    nombre_ticket = f"ticket-{usuario.id}"

    for canal in guild.text_channels:

        if canal.name == nombre_ticket:

            await interaction.response.send_message(
                f"❌ Ya tienes un ticket abierto: {canal.mention}",
                ephemeral=True
            )

            return

    # ======================================
    # PERMISOS
    # ======================================

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        usuario:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),

        rol_soporte:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                send_messages=True,
                manage_channels=True,
                attach_files=True,
                embed_links=True
            )
    }

    # ======================================
    # CATEGORÍA
    # ======================================

    categoria = None

    if CATEGORIA_TICKETS != 0:

        categoria = guild.get_channel(
            CATEGORIA_TICKETS
        )

    # ======================================
    # CREAR CANAL
    # ======================================

    canal = await guild.create_text_channel(

        name=nombre_ticket,

        category=(
            categoria
            if isinstance(
                categoria,
                discord.CategoryChannel
            )
            else None
        ),

        overwrites=overwrites,

        reason=f"Ticket de {usuario} - {tipo}"
    )

    # ======================================
    # EMBED DEL TICKET
    # ======================================

    embed = discord.Embed(

        title="🌑 Eclipse World | Ticket",

        description=(
            f"👋 Bienvenido {usuario.mention}\n\n"

            f"Has abierto un ticket de **{tipo}**.\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "📝 **Explica tu problema**\n"
            "Cuéntanos qué necesitas y proporciona "
            "toda la información posible.\n\n"

            "📎 **Pruebas**\n"
            "Si tienes capturas, vídeos u otras pruebas, "
            "puedes adjuntarlas.\n\n"

            "⏳ **Soporte**\n"
            "Un miembro del equipo de Eclipse World "
            "te atenderá lo antes posible."
        ),

        color=discord.Color.dark_blue()
    )

    if IMAGEN_LOGO.startswith("http"):

        embed.set_thumbnail(
            url=IMAGEN_LOGO
        )

    embed.set_footer(
        text="Eclipse World • Sistema de Tickets"
    )

    # ======================================
    # MENSAJE DEL TICKET
    # ======================================

    await canal.send(

        content=(
            f"{usuario.mention} "
            f"{rol_soporte.mention}"
        ),

        embed=embed,

        view=CerrarTicketView()
    )

    # ======================================
    # RESPUESTA AL USUARIO
    # ======================================

    await interaction.response.send_message(

        f"✅ Tu ticket ha sido creado: {canal.mention}",

        ephemeral=True
    )


# ==========================================
# CERRAR TICKET
# ==========================================

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

        custom_id="eclipse_cerrar_ticket"
    )
    async def cerrar(

        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(

            "🔒 Este ticket se cerrará en 5 segundos."
        )

        await asyncio.sleep(5)

        try:

            await interaction.channel.delete(

                reason=(
                    f"Ticket cerrado por "
                    f"{interaction.user}"
                )
            )

        except discord.NotFound:

            pass


# ==========================================
# PANEL DE TICKETS
# ==========================================

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

        custom_id="eclipse_soporte"
    )
    async def soporte(

        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "Soporte general"
        )

    @discord.ui.button(

        label="Reportar usuario",

        emoji="🚨",

        style=discord.ButtonStyle.danger,

        custom_id="eclipse_reportar_usuario"
    )
    async def reporte(

        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "Reportar usuario"
        )

    @discord.ui.button(

        label="Reportar bug",

        emoji="🐛",

        style=discord.ButtonStyle.secondary,

        custom_id="eclipse_bug"
    )
    async def bug(

        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "Reportar bug"
        )

    @discord.ui.button(

        label="Postulaciones",

        emoji="👥",

        style=discord.ButtonStyle.success,

        custom_id="eclipse_postulacion"
    )
    async def postulacion(

        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "Postulación"
        )

    @discord.ui.button(

        label="Estafas",

        emoji="💰",

        style=discord.ButtonStyle.danger,

        custom_id="eclipse_estafa"
    )
    async def estafa(

        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "Estafa"
        )


# ==========================================
# /TICKETPANEL
# ==========================================

@bot.tree.command(

    name="ticketpanel",

    description=(
        "Publica el panel de tickets "
        "de Eclipse World."
    )
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(

    interaction: discord.Interaction
):

    embed = discord.Embed(

        title="🌑 ECLIPSE WORLD",

        description=(
            "## 🎫 Sistema de Tickets\n\n"

            "Bienvenido al sistema oficial de soporte "
            "de **Eclipse World**.\n\n"

            "Abre un ticket seleccionando la categoría "
            "que corresponda a tu caso.\n\n"

            "🎫 **Soporte general**\n"
            "Dudas, problemas o ayuda.\n\n"

            "🚨 **Reportar usuario**\n"
            "Reporta comportamientos que incumplan "
            "las normas.\n\n"

            "🐛 **Reportar bug**\n"
            "Comunica errores o fallos del servidor.\n\n"

            "👥 **Postulaciones**\n"
            "Solicita formar parte del equipo.\n\n"

            "💰 **Estafas**\n"
            "Reporta posibles estafas o problemas "
            "relacionados.\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "⚠️ **USO CORRECTO DE LOS TICKETS**\n\n"

            "• Abre un ticket únicamente cuando sea "
            "necesario.\n"

            "• No abras tickets repetidos.\n"

            "• No hagas spam al equipo de soporte.\n"

            "• Explica claramente tu problema.\n"

            "• Aporta pruebas cuando sean necesarias.\n"

            "• El uso inapropiado de tickets puede "
            "conllevar sanciones.\n\n"

            "👇 **Selecciona una opción para comenzar.**"
        ),

        color=discord.Color.dark_blue()
    )

    if IMAGEN_LOGO.startswith("http"):

        embed.set_image(
            url=IMAGEN_LOGO
        )

    embed.set_footer(

        text=(
            "Eclipse World • "
            "Sistema oficial de soporte"
        )
    )

    enviados = 0

    for canal_id in CANALES_PANEL:

        canal = bot.get_channel(
            canal_id
        )

        if canal is None:

            print(
                f"⚠️ No se encontró "
                f"el canal {canal_id}"
            )

            continue

        try:

            await canal.send(

                embed=embed,

                view=TicketView()
            )

            enviados += 1

        except discord.Forbidden:

            print(
                f"❌ Sin permisos en "
                f"el canal {canal_id}"
            )

    await interaction.response.send_message(

        f"✅ Panel enviado en "
        f"{enviados}/{len(CANALES_PANEL)} canales.",

        ephemeral=True
    )


# ==========================================
# ERRORES
# ==========================================

@ticketpanel.error
async def ticketpanel_error(

    interaction: discord.Interaction,

    error
):

    if isinstance(

        error,

        app_commands.errors.MissingPermissions

    ):

        await interaction.response.send_message(

            "❌ Necesitas permisos de administrador.",

            ephemeral=True
        )

    else:

        print(
            f"❌ Error en /ticketpanel: {error}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(

                "❌ Ha ocurrido un error.",

                ephemeral=True
            )


# ==========================================
# ARRANQUE
# ==========================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta TOKEN_DISCORD en Railway."
    )

bot.run(TOKEN)
