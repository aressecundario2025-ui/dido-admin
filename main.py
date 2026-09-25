import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Canales donde se publicará el panel
CANALES_PANEL = [
    1434297124539076738,
    1551198802164064266
]

# ÚNICO ROL DE SOPORTE
ROL_SOPORTE = 1552374542909833246

# Logo dentro de Railway
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
# TEXTO DE REGLAS
# =========================================================

MENSAJE_REGLAS = """🎫 **¿Necesitas Ayuda? Abre un ticket en la categoría que necesitas! Ten paciencia a la hora de abrir ticket o de lo contrario serás sancionado!** ⚠️

📋 **Reglas** 📋

⏳ *1)* **Ten paciencia a la hora de abrir ticket!** 🕐

🚫 *2)* **No insultar al equipo del staff!** ⚠️

📌 *3)* **Estar activo en el ticket o de lo contrario será cerrado por inactividad!** 🕐

📂 *4)* **Abrir ticket en su categoría que corresponde o de lo contrario serás sancionado!**

⚠️ *5)* **Abrir ticket sin razón es sancionable!** 🚫


🚀 **Te atenderemos lo mas rápido posible!** ⚡"""


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
# BUSCAR TICKET EXISTENTE
# =========================================================

def buscar_ticket(guild, usuario):

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

        await interaction.followup.send(
            "❌ Este botón solo funciona dentro del servidor.",
            ephemeral=True
        )

        return

    # Buscar rol de soporte
    rol_soporte = guild.get_role(
        ROL_SOPORTE
    )

    if rol_soporte is None:

        await interaction.followup.send(
            "❌ No encuentro el rol de soporte en este servidor.",
            ephemeral=True
        )

        print(
            f"❌ No se encontró el rol {ROL_SOPORTE} "
            f"en {guild.name} ({guild.id})"
        )

        return

    # =====================================================
    # COMPROBAR TICKET EXISTENTE
    # =====================================================

    ticket_existente = buscar_ticket(
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

    permisos_staff = discord.PermissionOverwrite(
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

        rol_soporte:
            permisos_staff,

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
            f"❌ Error creando ticket: {e}"
        )

        await interaction.followup.send(
            "❌ Ha ocurrido un error creando el ticket.",
            ephemeral=True
        )

        return

    # =====================================================
    # EMBED DEL TICKET
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
            "📌 Explica claramente tu problema o solicitud.\n\n"
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

    contenido = (
        f"{usuario.mention} <@&{ROL_SOPORTE}>"
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
            f"✅ Ticket creado: {canal.name}"
        )

    except Exception as e:

        print(
            f"❌ Error enviando mensaje del ticket: {e}"
        )

        await interaction.followup.send(
            "⚠️ El ticket se creó, pero hubo un error enviando el mensaje.",
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
                reason=f"Ticket cerrado por {interaction.user}"
            )

        except Exception as e:

            print(
                f"❌ Error cerrando ticket: {e}"
            )


# =========================================================
# PANEL DE TICKETS
# =========================================================

class TicketView(discord.ui.View):

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

        # Registrar botones persistentes
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

        # Sincronizar comandos
        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} comandos sincronizados."
        )

        # Comprobar rol
        for guild in bot.guilds:

            rol = guild.get_role(
                ROL_SOPORTE
            )

            if rol:

                print(
                    f"✅ Rol de soporte encontrado: "
                    f"{rol.name} ({ROL_SOPORTE})"
                )

            else:

                print(
                    f"⚠️ Rol {ROL_SOPORTE} "
                    f"no encontrado en {guild.name}"
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
                f"❌ No encuentro el canal {canal_id}"
            )

            continue

        try:

            # =================================================
            # 1. REGLAS
            # =================================================

            await canal.send(
                content=MENSAJE_REGLAS,
                allowed_mentions=discord.AllowedMentions.none()
            )

            # =================================================
            # 2. MENCIONAR SOPORTE
            # =================================================

            await canal.send(
                content=f"<@&{ROL_SOPORTE}>",
                allowed_mentions=discord.AllowedMentions(
                    roles=True
                )
            )

            # =================================================
            # 3. PANEL
            # =================================================

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
        f"✅ Panel enviado a "
        f"{enviados}/{len(CANALES_PANEL)} canales.",
        ephemeral=True
    )


# =========================================================
# ERROR /TICKETPANEL
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
# COMPROBAR TOKEN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta DISCORD_TOKEN en las variables de Railway."
    )


# =========================================================
# INICIAR
# =========================================================

print("🚀 Iniciando bot de tickets...")

bot.run(TOKEN)