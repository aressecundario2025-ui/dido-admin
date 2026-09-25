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

# STAFF QUE SE MENCIONA
ROL_SOPORTE = 1434289818992382084

# ROL QUE TIENE ACCESO PERO NO SE MENCIONA
ROL_ACCESO_EXTRA = 1552374542909833246

# LOGO
LOGO_PATH = "logo.png"

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
# COLOR
# =========================================================

COLOR = discord.Color.from_rgb(88, 101, 242)

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
# MENSAJE DE REGLAS
# =========================================================

MENSAJE_REGLAS = """
:54967105671957: **¿Necesitas Ayuda? Abre un ticket en la categoría que necesitas! Ten paciencia a la hora de abrir ticket o de lo contrario serás sancionado!** :1219816049822666893:

:3057195671616: **Reglas** :3057195671616:

:0974966496677: *1)* **Ten paciencia a la hora de abrir ticket!** :1195801251850502175:

:30571957289: *2)* **No insultar al equipo del staff!** :1219816049822666893:

:205719567E93093984: *3)* **Estar activo en el ticket o de lo contrario será cerrado por inactividad!** :1195801251850502175:

:4947569375939420: *4)* **Abrir ticket en su categoría que corresponde o de lo contrario serás sancionado!**

:30572935723: *5)* **Abrir ticket sin razón es sancionable!** :1219816049822666893:


:1216991711872684052: **Te atenderemos lo mas rápido posible!** :1216999826248437784:
"""


# =========================================================
# BUSCAR TICKET EXISTENTE
# =========================================================

async def buscar_ticket(
    guild: discord.Guild,
    usuario: discord.Member
):

    nombre_ticket = f"ticket-{usuario.id}"

    for canal in guild.text_channels:

        if canal.name == nombre_ticket:
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
    rol_extra = guild.get_role(ROL_ACCESO_EXTRA)

    # =====================================================
    # COMPROBAR STAFF
    # =====================================================

    if rol_staff is None:

        await interaction.response.send_message(
            "❌ No se encuentra el rol de soporte.",
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

        await interaction.response.send_message(
            f"❌ Ya tienes un ticket abierto: "
            f"{ticket_existente.mention}",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    # =====================================================
    # PERMISOS
    # =====================================================

    overwrites = {

        # Nadie más puede ver el ticket
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        # Usuario que abrió el ticket
        usuario: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        ),

        # Bot
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    # =====================================================
    # STAFF
    # =====================================================

    overwrites[rol_staff] = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True
    )

    # =====================================================
    # SEGUNDO ROL
    # ACCESO SIN MENCIÓN
    # =====================================================

    if rol_extra:

        overwrites[rol_extra] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

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

    except discord.HTTPException as e:

        await interaction.followup.send(
            f"❌ No pude crear el ticket: `{e}`",
            ephemeral=True
        )

        return

    # =====================================================
    # EMBED DEL TICKET
    # =====================================================

    embed = discord.Embed(
        title=TIPOS_TICKET.get(
            tipo,
            "🎫 Ticket"
        ),
        description=(
            f"Hola {usuario.mention} 👋\n\n"

            "Tu ticket ha sido creado correctamente.\n\n"

            "Un miembro del equipo de soporte "
            "te atenderá lo antes posible.\n\n"

            "📌 **Recuerda:**\n"
            "• Explica claramente tu problema.\n"
            "• No hagas spam.\n"
            "• No abras tickets duplicados.\n"
            "• Aporta pruebas cuando sea necesario.\n\n"

            "🔒 Cuando hayas terminado, pulsa "
            "**Cerrar ticket**."
        ),
        color=COLOR
    )

    embed.set_footer(
        text="Eclipse World • Sistema de soporte"
    )

    # =====================================================
    # MENSAJE DEL TICKET
    # SOLO MENCIONA USUARIO + STAFF
    # =====================================================

    if os.path.exists(LOGO_PATH):

        file = discord.File(
            LOGO_PATH,
            filename="logo.png"
        )

        embed.set_thumbnail(
            url="attachment://logo.png"
        )

        await canal.send(
            content=(
                f"{usuario.mention} "
                f"<@&{ROL_SOPORTE}>"
            ),
            embed=embed,
            file=file,
            view=CerrarTicketView(),
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=True
            )
        )

    else:

        await canal.send(
            content=(
                f"{usuario.mention} "
                f"<@&{ROL_SOPORTE}>"
            ),
            embed=embed,
            view=CerrarTicketView(),
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=True
            )
        )

    # =====================================================
    # CONFIRMACIÓN
    # =====================================================

    await interaction.followup.send(
        f"✅ Tu ticket ha sido creado: {canal.mention}",
        ephemeral=True
    )


# =========================================================
# BOTÓN CERRAR TICKET
# =========================================================

class CerrarTicketView(discord.ui.View):

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
                reason=(
                    f"Ticket cerrado por "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass


# =========================================================
# PANEL DE TICKETS
# =========================================================

class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # =====================================================
    # SOPORTE GENERAL
    # =====================================================

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

    # =====================================================
    # REPORTAR USUARIO
    # =====================================================

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

    # =====================================================
    # REPORTAR BUG
    # =====================================================

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

    # =====================================================
    # POSTULACIONES
    # =====================================================

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

    # =====================================================
    # ESTAFAS
    # =====================================================

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
# READY
# =========================================================

@bot.event
async def on_ready():

    print("========================================")
    print(f"✅ Bot conectado como {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("========================================")

    try:

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

        synced = await bot.tree.sync()

        print(
            f"✅ Comandos sincronizados: "
            f"{len(synced)}"
        )

    except Exception as e:

        print(
            f"❌ Error sincronizando comandos: "
            f"{e}"
        )


# =========================================================
# /TICKETPANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica el panel de tickets de Eclipse World"
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

    # =====================================================
    # ENVIAR PRIMERO LAS REGLAS
    # =====================================================

    for canal_id in CANALES_PANEL:

        canal = bot.get_channel(
            canal_id
        )

        if canal is None:

            print(
                f"⚠️ No se encontró el canal "
                f"{canal_id}"
            )

            continue

        try:

            # -------------------------------------------------
            # 1. MENSAJE DE REGLAS
            # -------------------------------------------------

            await canal.send(
                content=MENSAJE_REGLAS,
                allowed_mentions=discord.AllowedMentions.none()
            )

            # -------------------------------------------------
            # 2. MENCIÓN SOLO AL STAFF
            # -------------------------------------------------

            await canal.send(
                content=f"<@&{ROL_SOPORTE}>",
                allowed_mentions=discord.AllowedMentions(
                    roles=True
                )
            )

            # -------------------------------------------------
            # 3. PANEL
            # -------------------------------------------------

            embed = discord.Embed(
                title="",
                description="",
                color=COLOR
            )

            # El panel solo lleva el logo
            # y los botones de abajo.

            if os.path.exists(LOGO_PATH):

                file = discord.File(
                    LOGO_PATH,
                    filename="logo.png"
                )

                embed.set_image(
                    url="attachment://logo.png"
                )

                await canal.send(
                    embed=embed,
                    file=file,
                    view=TicketView()
                )

            else:

                print(
                    "⚠️ No se encontró logo.png"
                )

                await canal.send(
                    view=TicketView()
                )

            enviados += 1

            print(
                f"✅ Panel completo enviado a "
                f"{canal_id}"
            )

        except discord.Forbidden:

            print(
                f"❌ Sin permisos en {canal_id}"
            )

        except discord.HTTPException as e:

            print(
                f"❌ Error enviando a "
                f"{canal_id}: {e}"
            )

    # =====================================================
    # RESPUESTA
    # =====================================================

    await interaction.followup.send(
        f"✅ Panel enviado a {enviados}/2 canales.",
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
# COMPROBAR TOKEN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ No existe la variable DISCORD_TOKEN "
        "en Railway."
    )


# =========================================================
# INICIAR BOT
# =========================================================

bot.run(TOKEN)