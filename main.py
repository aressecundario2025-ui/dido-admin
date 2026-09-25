import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import os
import re


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

CANALES_PANEL = [
    1434297124539076738,
    1551198802164064266
]

ROL_SOPORTE = 1552374542909833246

LOGO_PATH = "logo.png"


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# DATOS DE LOS TICKETS
# =========================================================

tickets = {}


# =========================================================
# FUNCIONES
# =========================================================

def limpiar_nombre(nombre):
    nombre = nombre.lower()
    nombre = re.sub(r"[^a-z0-9\-]", "-", nombre)
    nombre = re.sub(r"-+", "-", nombre)
    return nombre[:20]


def es_staff(member):
    return (
        isinstance(member, discord.Member)
        and member.get_role(ROL_SOPORTE) is not None
    )


# =========================================================
# EMBED DE REGLAS
# =========================================================

def crear_reglas_embed():

    embed = discord.Embed(
        title="🎫 ¿Necesitas Ayuda?",
        description=(
            "Abre un ticket en la categoría que necesitas.\n"
            "Ten paciencia a la hora de abrir un ticket o de lo "
            "contrario serás sancionado. ⚠️\n\n"

            "📋 **Reglas** 📋\n\n"

            "⏳ **1)** Ten paciencia a la hora de abrir ticket. 🕐\n\n"

            "🚫 **2)** No insultar al equipo del staff. ⚠️\n\n"

            "📌 **3)** Estar activo en el ticket o de lo contrario "
            "será cerrado por inactividad. 🕐\n\n"

            "📂 **4)** Abrir ticket en su categoría correspondiente "
            "o de lo contrario serás sancionado.\n\n"

            "⚠️ **5)** Abrir ticket sin razón es sancionable. 🚫\n\n\n"

            "🚀 **Te atenderemos lo más rápido posible!** ⚡"
        ),
        color=discord.Color.from_rgb(255, 170, 0)
    )

    if os.path.exists(LOGO_PATH):
        embed.set_thumbnail(
            url="attachment://logo.png"
        )

    return embed


# =========================================================
# EMBED DEL PANEL
# =========================================================

def crear_panel_embed():

    embed = discord.Embed(
        title="🎫 Soporte Eclipse World",
        description=(
            "Selecciona la categoría que necesitas para abrir un ticket.\n\n"

            "🎫 **Soporte general**\n"
            "🚨 **Reportar usuario**\n"
            "🐛 **Reportar bug**\n"
            "👥 **Postulaciones**\n"
            "💰 **Estafas**\n\n"

            "⚠️ **Recuerda:** abre el ticket en la categoría "
            "correcta y ten paciencia mientras el staff te atiende."
        ),
        color=discord.Color.from_rgb(88, 101, 242)
    )

    embed.set_footer(
        text="Eclipse World • Sistema de soporte"
    )

    if os.path.exists(LOGO_PATH):
        embed.set_thumbnail(
            url="attachment://logo.png"
        )

    return embed


# =========================================================
# PANEL DE CREACIÓN DE TICKETS
# =========================================================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soporte general",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_soporte",
        row=0
    )
    async def soporte(self, interaction, button):

        await crear_ticket(
            interaction,
            "Soporte general",
            "🎫"
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_usuario",
        row=0
    )
    async def reportar_usuario(self, interaction, button):

        await crear_ticket(
            interaction,
            "Reportar usuario",
            "🚨"
        )

    @discord.ui.button(
        label="Reportar bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_bug",
        row=1
    )
    async def reportar_bug(self, interaction, button):

        await crear_ticket(
            interaction,
            "Reportar bug",
            "🐛"
        )

    @discord.ui.button(
        label="Postulaciones",
        emoji="👥",
        style=discord.ButtonStyle.success,
        custom_id="ticket_postulacion",
        row=1
    )
    async def postulaciones(self, interaction, button):

        await crear_ticket(
            interaction,
            "Postulaciones",
            "👥"
        )

    @discord.ui.button(
        label="Estafas",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_estafa",
        row=1
    )
    async def estafas(self, interaction, button):

        await crear_ticket(
            interaction,
            "Estafas",
            "💰"
        )


# =========================================================
# CREAR TICKET
# =========================================================

async def crear_ticket(interaction, categoria, emoji):

    guild = interaction.guild
    usuario = interaction.user

    soporte_role = guild.get_role(ROL_SOPORTE)

    if soporte_role is None:

        await interaction.response.send_message(
            "❌ No encuentro el rol de soporte.",
            ephemeral=True
        )
        return

    # Comprobar si ya tiene un ticket
    for datos in tickets.values():

        if (
            datos["guild_id"] == guild.id
            and datos["user_id"] == usuario.id
            and not datos["closed"]
        ):

            canal_existente = guild.get_channel(
                datos["channel_id"]
            )

            if canal_existente:

                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: "
                    f"{canal_existente.mention}",
                    ephemeral=True
                )
                return

    # Permisos iniciales
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

        soporte_role: discord.PermissionOverwrite(
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

    nombre_usuario = limpiar_nombre(
        usuario.display_name
    )

    nombre_canal = f"ticket-{nombre_usuario}"

    try:

        canal = await guild.create_text_channel(
            name=nombre_canal,
            overwrites=overwrites,
            reason=f"Ticket creado por {usuario}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No tengo permisos suficientes para crear tickets.",
            ephemeral=True
        )
        return

    except Exception as e:

        print(f"Error creando ticket: {e}")

        await interaction.response.send_message(
            "❌ Ha ocurrido un error creando el ticket.",
            ephemeral=True
        )
        return

    # Guardar información
    tickets[canal.id] = {
        "guild_id": guild.id,
        "channel_id": canal.id,
        "user_id": usuario.id,
        "category": categoria,
        "claimed_by": None,
        "closed": False
    }

    await interaction.response.send_message(
        f"✅ Tu ticket ha sido creado: {canal.mention}",
        ephemeral=True
    )

    # Embed del ticket
    embed = discord.Embed(
        title=f"{emoji} {categoria}",
        description=(
            f"Hola {usuario.mention} 👋\n\n"

            "Tu ticket ha sido creado correctamente.\n"
            "Un miembro del equipo de soporte lo atenderá "
            "lo antes posible.\n\n"

            "📌 **Un miembro del staff debe reclamar el ticket "
            "para comenzar a atenderlo.**\n\n"

            "⚠️ No hagas spam ni menciones repetidamente al staff."
        ),
        color=discord.Color.from_rgb(88, 101, 242)
    )

    embed.add_field(
        name="📂 Categoría",
        value=categoria,
        inline=True
    )

    embed.add_field(
        name="👤 Usuario",
        value=usuario.mention,
        inline=True
    )

    embed.set_footer(
        text="Eclipse World • Sistema de tickets"
    )

    # Enviar ticket
    if os.path.exists(LOGO_PATH):

        archivo = discord.File(
            LOGO_PATH,
            filename="logo.png"
        )

        embed.set_thumbnail(
            url="attachment://logo.png"
        )

        await canal.send(
            content=f"{usuario.mention} <@&{ROL_SOPORTE}>",
            embed=embed,
            file=archivo,
            view=TicketControlView()
        )

    else:

        await canal.send(
            content=f"{usuario.mention} <@&{ROL_SOPORTE}>",
            embed=embed,
            view=TicketControlView()
        )


# =========================================================
# BOTONES DENTRO DEL TICKET
# =========================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # =====================================================
    # RECLAMAR
    # =====================================================

    @discord.ui.button(
        label="Reclamar ticket",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_reclamar",
        row=0
    )
    async def reclamar(self, interaction, button):

        canal = interaction.channel
        usuario = interaction.user

        datos = tickets.get(canal.id)

        if datos is None:

            await interaction.response.send_message(
                "❌ Este canal no está registrado como ticket.",
                ephemeral=True
            )
            return

        if not es_staff(usuario):

            await interaction.response.send_message(
                "❌ Solo el staff puede reclamar tickets.",
                ephemeral=True
            )
            return

        if datos["claimed_by"] is not None:

            reclamado = canal.guild.get_member(
                datos["claimed_by"]
            )

            if reclamado:

                mensaje = (
                    f"❌ Este ticket ya está reclamado por "
                    f"{reclamado.mention}."
                )

            else:

                mensaje = "❌ Este ticket ya está reclamado."

            await interaction.response.send_message(
                mensaje,
                ephemeral=True
            )
            return

        # Guardar quién lo reclamó
        datos["claimed_by"] = usuario.id

        guild = canal.guild

        soporte_role = guild.get_role(
            ROL_SOPORTE
        )

        creador = guild.get_member(
            datos["user_id"]
        )

        # El rol de staff puede ver pero NO escribir
        if soporte_role:

            await canal.set_permissions(
                soporte_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

        # El staff que reclamó puede escribir
        await canal.set_permissions(
            usuario,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        # El creador puede escribir
        if creador:

            await canal.set_permissions(
                creador,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        # El bot puede escribir
        if guild.me:

            await canal.set_permissions(
                guild.me,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )

        # Cambiar botón
        button.disabled = True
        button.label = f"Reclamado por {usuario.display_name}"
        button.emoji = "✅"

        await interaction.response.edit_message(
            view=self
        )

        await canal.send(
            f"📌 **Ticket reclamado**\n\n"
            f"Este ticket ha sido reclamado por {usuario.mention}.\n"
            f"🔒 Desde ahora, **solo el creador del ticket y "
            f"{usuario.mention} pueden escribir aquí.**"
        )

    # =====================================================
    # LIBERAR
    # =====================================================

    @discord.ui.button(
        label="Liberar ticket",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_liberar",
        row=0
    )
    async def liberar(self, interaction, button):

        canal = interaction.channel
        usuario = interaction.user

        datos = tickets.get(canal.id)

        if datos is None:

            await interaction.response.send_message(
                "❌ Este canal no está registrado como ticket.",
                ephemeral=True
            )
            return

        if not es_staff(usuario):

            await interaction.response.send_message(
                "❌ Solo el staff puede liberar tickets.",
                ephemeral=True
            )
            return

        if datos["claimed_by"] != usuario.id:

            await interaction.response.send_message(
                "❌ Solo el miembro del staff que reclamó "
                "este ticket puede liberarlo.",
                ephemeral=True
            )
            return

        guild = canal.guild

        soporte_role = guild.get_role(
            ROL_SOPORTE
        )

        creador = guild.get_member(
            datos["user_id"]
        )

        datos["claimed_by"] = None

        # Restaurar permisos del staff
        if soporte_role:

            await canal.set_permissions(
                soporte_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        # Mantener al creador
        if creador:

            await canal.set_permissions(
                creador,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        # Eliminar permiso individual del staff
        await canal.set_permissions(
            usuario,
            overwrite=None
        )

        # Restaurar botón
        for item in self.children:

            if isinstance(item, discord.ui.Button):

                if item.custom_id == "ticket_reclamar":

                    item.disabled = False
                    item.label = "Reclamar ticket"
                    item.emoji = "📌"

        await interaction.response.edit_message(
            view=self
        )

        await canal.send(
            f"🔄 {usuario.mention} ha liberado el ticket.\n"
            f"📌 Otro miembro del staff puede reclamarlo ahora."
        )

    # =====================================================
    # CERRAR
    # =====================================================

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_cerrar",
        row=1
    )
    async def cerrar(self, interaction, button):

        canal = interaction.channel
        usuario = interaction.user

        datos = tickets.get(canal.id)

        if datos is None:

            await interaction.response.send_message(
                "❌ Este canal no está registrado como ticket.",
                ephemeral=True
            )
            return

        if not es_staff(usuario):

            await interaction.response.send_message(
                "❌ Solo el staff puede cerrar tickets.",
                ephemeral=True
            )
            return

        datos["closed"] = True

        await interaction.response.send_message(
            "🔒 Este ticket se cerrará en **5 segundos**."
        )

        await discord.utils.sleep_until(
            discord.utils.utcnow() + timedelta(seconds=5)
        )

        try:

            await canal.delete(
                reason=f"Ticket cerrado por {usuario}"
            )

        except discord.NotFound:

            pass

        except discord.Forbidden:

            print(
                "❌ No tengo permisos para eliminar el ticket."
            )

        except Exception as e:

            print(
                f"❌ Error cerrando ticket: {e}"
            )


# =========================================================
# COMANDO /TICKETPANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica los paneles de tickets de Eclipse World."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(interaction):

    await interaction.response.send_message(
        "📨 Publicando los paneles de tickets...",
        ephemeral=True
    )

    enviados = 0

    for canal_id in CANALES_PANEL:

        canal = bot.get_channel(canal_id)

        if canal is None:

            print(
                f"❌ No se encontró el canal {canal_id}"
            )

            continue

        try:

            # Reglas
            if os.path.exists(LOGO_PATH):

                archivo_reglas = discord.File(
                    LOGO_PATH,
                    filename="logo.png"
                )

                await canal.send(
                    embed=crear_reglas_embed(),
                    file=archivo_reglas
                )

            else:

                await canal.send(
                    embed=crear_reglas_embed()
                )

            # Aviso al staff
            await canal.send(
                f"👮 **Equipo de soporte:** <@&{ROL_SOPORTE}>\n\n"
                "Cuando un usuario abra un ticket, un miembro "
                "del staff deberá pulsar **📌 Reclamar ticket** "
                "para atenderlo."
            )

            # Panel
            if os.path.exists(LOGO_PATH):

                archivo_panel = discord.File(
                    LOGO_PATH,
                    filename="logo.png"
                )

                await canal.send(
                    embed=crear_panel_embed(),
                    file=archivo_panel,
                    view=TicketView()
                )

            else:

                await canal.send(
                    embed=crear_panel_embed(),
                    view=TicketView()
                )

            enviados += 1

        except discord.Forbidden:

            print(
                f"❌ Sin permisos en el canal {canal_id}"
            )

        except Exception as e:

            print(
                f"❌ Error enviando panel a {canal_id}: {e}"
            )

    await interaction.followup.send(
        f"✅ Paneles publicados en "
        f"**{enviados}/{len(CANALES_PANEL)}** canales.",
        ephemeral=True
    )


# =========================================================
# ERRORES DEL COMANDO
# =========================================================

@ticketpanel.error
async def ticketpanel_error(interaction, error):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        mensaje = (
            "❌ Necesitas permisos de Administrador "
            "para utilizar este comando."
        )

    else:

        print(
            f"❌ Error /ticketpanel: {error}"
        )

        mensaje = (
            "❌ Ha ocurrido un error ejecutando el comando."
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
# BOT LISTO
# =========================================================

@bot.event
async def on_ready():

    print(
        f"✅ Eclipse World Tickets conectado como "
        f"{bot.user} | ID: {bot.user.id}"
    )

    # Vistas persistentes
    bot.add_view(
        TicketView()
    )

    bot.add_view(
        TicketControlView()
    )

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} comandos sincronizados."
        )

    except Exception as e:

        print(
            f"❌ Error sincronizando comandos: {e}"
        )


# =========================================================
# INICIAR BOT
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta la variable DISCORD_TOKEN en Railway."
    )

bot.run(TOKEN)