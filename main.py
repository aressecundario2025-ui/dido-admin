import discord
from discord.ext import commands
from discord import app_commands

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = "PON_AQUI_EL_TOKEN_DEL_BOT"

CANALES_PANEL = [
    1434297124539076738,
    1551198802164064266
]

ROL_SOPORTE = 1434289818992382084

# Pon aquí el enlace directo de la imagen/logo
IMAGEN_LOGO = "PON_AQUI_EL_ENLACE_DIRECTO_DE_LA_IMAGEN"

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
# COLORES
# =========================================================

COLOR = discord.Color.from_rgb(88, 101, 242)

# =========================================================
# NOMBRES DE TICKETS
# =========================================================

TIPOS_TICKET = {
    "soporte": "🎫 Soporte general",
    "reportar": "🚨 Reportar usuario",
    "bug": "🐛 Reportar bug",
    "postulacion": "👥 Postulaciones",
    "estafa": "💰 Estafas"
}


# =========================================================
# FUNCIÓN PARA COMPROBAR SI YA TIENE TICKET
# =========================================================

async def buscar_ticket(guild: discord.Guild, user: discord.Member):

    for canal in guild.text_channels:
        if canal.name == f"ticket-{user.id}":
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
        return

    rol_staff = guild.get_role(ROL_SOPORTE)

    if rol_staff is None:
        await interaction.response.send_message(
            "❌ No encuentro el rol de soporte configurado.",
            ephemeral=True
        )
        return

    ticket_existente = await buscar_ticket(guild, usuario)

    if ticket_existente:

        await interaction.response.send_message(
            f"❌ Ya tienes un ticket abierto: {ticket_existente.mention}",
            ephemeral=True
        )

        return

    await interaction.response.defer(ephemeral=True)

    # =====================================================
    # PERMISOS DEL TICKET
    # =====================================================

    overwrites = {

        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        usuario: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        ),

        rol_staff: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        ),

        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    # =====================================================
    # CREAR CANAL
    # =====================================================

    nombre = f"ticket-{usuario.id}"

    canal = await guild.create_text_channel(
        name=nombre,
        overwrites=overwrites,
        reason=f"Ticket creado por {usuario}"
    )

    # =====================================================
    # EMBED DEL TICKET
    # =====================================================

    embed = discord.Embed(
        title=f"{TIPOS_TICKET.get(tipo, '🎫 Ticket')}",
        description=(
            f"Hola {usuario.mention} 👋\n\n"
            "Tu ticket ha sido creado correctamente.\n\n"
            "Un miembro del equipo de soporte te atenderá "
            "lo antes posible.\n\n"
            "📌 **Recuerda:**\n"
            "• Explica claramente tu problema.\n"
            "• No hagas spam.\n"
            "• No abras varios tickets por el mismo motivo.\n"
            "• Aporta pruebas si son necesarias.\n\n"
            "🔒 Cuando hayas terminado, utiliza el botón "
            "**Cerrar ticket**."
        ),
        color=COLOR
    )

    if IMAGEN_LOGO.startswith("http"):
        embed.set_thumbnail(url=IMAGEN_LOGO)

    embed.set_footer(
        text="Eclipse World • Sistema de soporte"
    )

    # =====================================================
    # MENCIÓN USUARIO + STAFF
    # =====================================================

    await canal.send(
        content=f"{usuario.mention} <@&{ROL_SOPORTE}>",
        embed=embed,
        view=CerrarTicketView(),
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=True
        )
    )

    await interaction.followup.send(
        f"✅ Tu ticket ha sido creado: {canal.mention}",
        ephemeral=True
    )


# =========================================================
# BOTÓN CERRAR TICKET
# =========================================================

class CerrarTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

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
            "🔒 Este ticket se cerrará en 5 segundos..."
        )

        await discord.utils.sleep_until(
            discord.utils.utcnow() + discord.timedelta(seconds=5)
        )

        try:
            await canal.delete(
                reason=f"Ticket cerrado por {interaction.user}"
            )
        except Exception:
            pass


# =========================================================
# PANEL DE TICKETS
# =========================================================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soporte general",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_soporte"
    )
    async def soporte(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "soporte"
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_reportar"
    )
    async def reportar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "reportar"
        )

    @discord.ui.button(
        label="Reportar bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_bug"
    )
    async def bug(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "bug"
        )

    @discord.ui.button(
        label="Postulaciones",
        emoji="👥",
        style=discord.ButtonStyle.success,
        custom_id="ticket_postulacion"
    )
    async def postulacion(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "postulacion"
        )

    @discord.ui.button(
        label="Estafas",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_estafa"
    )
    async def estafa(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await crear_ticket(
            interaction,
            "estafa"
        )


# =========================================================
# EVENTO READY
# =========================================================

@bot.event
async def on_ready():

    print("----------------------------------------")
    print(f"Bot conectado como {bot.user}")
    print(f"ID: {bot.user.id}")
    print("----------------------------------------")

    try:
        bot.add_view(TicketView())
        bot.add_view(CerrarTicketView())

        synced = await bot.tree.sync()

        print(f"Comandos sincronizados: {len(synced)}")

    except Exception as e:
        print(f"Error sincronizando comandos: {e}")


# =========================================================
# COMANDO /TICKETPANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica el panel de tickets de Eclipse World"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketpanel(
    interaction: discord.Interaction
):

    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="🎫 Soporte • Eclipse World",
        description=(
            "¿Necesitas ayuda? Abre un ticket seleccionando "
            "una de las opciones de abajo.\n\n"

            "🎫 **Soporte general**\n"
            "Para dudas, problemas o ayuda general.\n\n"

            "🚨 **Reportar usuario**\n"
            "Para informar sobre un usuario que incumpla las normas.\n\n"

            "🐛 **Reportar bug**\n"
            "Para informar de errores o problemas del servidor.\n\n"

            "👥 **Postulaciones**\n"
            "Para solicitar un puesto dentro del equipo.\n\n"

            "💰 **Estafas**\n"
            "Para informar sobre posibles estafas o engaños.\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "⚠️ **IMPORTANTE**\n"
            "No abras tickets innecesarios ni hagas spam.\n"
            "Explica claramente tu problema y aporta pruebas "
            "cuando sea necesario.\n\n"
            "El mal uso del sistema de tickets puede conllevar "
            "sanciones."
        ),
        color=COLOR
    )

    if IMAGEN_LOGO.startswith("http"):
        embed.set_image(url=IMAGEN_LOGO)

    embed.set_footer(
        text="Eclipse World • Soporte"
    )

    enviados = 0

    for canal_id in CANALES_PANEL:

        canal = bot.get_channel(canal_id)

        if canal is None:
            print(
                f"No se encontró el canal: {canal_id}"
            )
            continue

        try:

            await canal.send(
                embed=embed,
                view=TicketView()
            )

            enviados += 1

        except Exception as e:

            print(
                f"Error enviando panel a {canal_id}: {e}"
            )

    await interaction.followup.send(
        f"✅ Panel enviado a {enviados} canal(es).",
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
            "❌ Necesitas permisos de Administrador "
            "para utilizar este comando."
        )

    else:

        mensaje = (
            f"❌ Ha ocurrido un error:\n"
            f"`{error}`"
        )

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


# =========================================================
# INICIAR BOT
# =========================================================

bot.run(TOKEN)