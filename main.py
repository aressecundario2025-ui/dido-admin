import os
import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN_DISCORD")

# Canales donde se puede utilizar el sistema de tickets
CANALES_TICKETS = {
    1549058205051527198,
    1551198802164064266
}

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# MODALES
# =========================================================

class PostulacionModal(discord.ui.Modal, title="📝 Postulación"):

    minecraft = discord.ui.TextInput(
        label="Nombre de Minecraft",
        placeholder="Tu nick de Minecraft",
        max_length=100
    )

    puesto = discord.ui.TextInput(
        label="¿A qué puesto aspiras?",
        placeholder="Builder, Staff, Helper, etc.",
        max_length=100
    )

    experiencia = discord.ui.TextInput(
        label="Experiencia",
        placeholder="Cuéntanos tu experiencia",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    motivo = discord.ui.TextInput(
        label="¿Por qué quieres entrar?",
        placeholder="Explícanos tu interés",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):

        await crear_ticket(
            interaction,
            "postulacion",
            {
                "Minecraft": self.minecraft.value,
                "Puesto": self.puesto.value,
                "Experiencia": self.experiencia.value,
                "Motivo": self.motivo.value
            }
        )


class DudaModal(discord.ui.Modal, title="❓ Duda"):

    asunto = discord.ui.TextInput(
        label="Asunto",
        placeholder="¿Sobre qué tienes una duda?",
        max_length=150
    )

    descripcion = discord.ui.TextInput(
        label="Describe tu duda",
        placeholder="Explica tu duda con detalle",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):

        await crear_ticket(
            interaction,
            "duda",
            {
                "Asunto": self.asunto.value,
                "Descripción": self.descripcion.value
            }
        )


class BugModal(discord.ui.Modal, title="🐛 Reportar bug"):

    titulo = discord.ui.TextInput(
        label="Título del bug",
        placeholder="Ejemplo: Error al entrar al servidor",
        max_length=150
    )

    descripcion = discord.ui.TextInput(
        label="Describe el bug",
        placeholder="Explica qué ocurre",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    pasos = discord.ui.TextInput(
        label="¿Cómo reproducirlo?",
        placeholder="Explica los pasos para que ocurra",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        await crear_ticket(
            interaction,
            "bug",
            {
                "Título": self.titulo.value,
                "Descripción": self.descripcion.value,
                "Pasos": self.pasos.value
            }
        )


class ReporteModal(discord.ui.Modal, title="🚨 Reportar usuario"):

    usuario = discord.ui.TextInput(
        label="Usuario reportado",
        placeholder="Nick de Minecraft o usuario de Discord",
        max_length=100
    )

    motivo = discord.ui.TextInput(
        label="Motivo del reporte",
        placeholder="Explica qué ocurrió",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    pruebas = discord.ui.TextInput(
        label="Pruebas / información adicional",
        placeholder="Explica o aporta información adicional",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        await crear_ticket(
            interaction,
            "reporte",
            {
                "Usuario reportado": self.usuario.value,
                "Motivo": self.motivo.value,
                "Pruebas": self.pruebas.value
            }
        )


# =========================================================
# CREAR TICKET
# =========================================================

async def crear_ticket(interaction, tipo, datos):

    guild = interaction.guild
    usuario = interaction.user

    if guild is None:
        await interaction.response.send_message(
            "❌ Este sistema solo funciona dentro de un servidor.",
            ephemeral=True
        )
        return

    # Buscar categoría
    categoria = discord.utils.get(
        guild.categories,
        name="TICKETS"
    )

    # Crear categoría si no existe
    if categoria is None:

        try:
            categoria = await guild.create_category(
                "TICKETS",
                reason="Sistema de tickets de Pilares"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No tengo permiso para crear categorías.",
                ephemeral=True
            )

            return

    # Comprobar si ya tiene ticket
    for canal in categoria.text_channels:

        if canal.topic == f"ticket:{usuario.id}":

            await interaction.response.send_message(
                f"❌ Ya tienes un ticket abierto: {canal.mention}",
                ephemeral=True
            )

            return

    nombre = f"{tipo}-{usuario.name}".lower()

    # Limpiar caracteres
    nombre = "".join(
        c if c.isalnum() or c == "-" else "-"
        for c in nombre
    )

    nombre = nombre[:80]

    # Permisos
    permisos = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        usuario: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )
    }

    # Administradores existentes
    for miembro in guild.members:

        if miembro.guild_permissions.administrator:

            permisos[miembro] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

    try:

        canal = await guild.create_text_channel(
            nombre,
            category=categoria,
            overwrites=permisos,
            topic=f"ticket:{usuario.id}",
            reason=f"Ticket {tipo} creado por {usuario}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No tengo permisos para crear el ticket.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title=f"🎫 Ticket de {tipo.upper()}",
        description=(
            f"Hola {usuario.mention}.\n\n"
            "Tu ticket ha sido creado correctamente.\n"
            "Un administrador lo atenderá lo antes posible.\n\n"
            "Cuando esté solucionado, pulsa **🔒 Cerrar ticket**."
        ),
        color=discord.Color.blurple()
    )

    for nombre_campo, valor in datos.items():

        if valor:

            embed.add_field(
                name=nombre_campo,
                value=valor[:1024],
                inline=False
            )

    embed.set_footer(
        text=f"Ticket creado por {usuario}"
    )

    await canal.send(
        content=usuario.mention,
        embed=embed,
        view=CerrarTicketView()
    )

    await interaction.response.send_message(
        f"✅ Ticket creado correctamente: {canal.mention}",
        ephemeral=True
    )


# =========================================================
# BOTONES
# =========================================================

class PanelTicketsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Postulación",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_postulacion"
    )
    async def postulacion(self, interaction, button):

        await interaction.response.send_modal(
            PostulacionModal()
        )

    @discord.ui.button(
        label="Duda",
        emoji="❓",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_duda"
    )
    async def duda(self, interaction, button):

        await interaction.response.send_modal(
            DudaModal()
        )

    @discord.ui.button(
        label="Bug",
        emoji="🐛",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_bug"
    )
    async def bug(self, interaction, button):

        await interaction.response.send_modal(
            BugModal()
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_reporte"
    )
    async def reporte(self, interaction, button):

        await interaction.response.send_modal(
            ReporteModal()
        )


class CerrarTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_cerrar"
    )
    async def cerrar(self, interaction, button):

        canal = interaction.channel

        if not isinstance(canal, discord.TextChannel):

            await interaction.response.send_message(
                "❌ Este botón no funciona aquí.",
                ephemeral=True
            )

            return

        propietario = None

        if canal.topic and canal.topic.startswith("ticket:"):

            try:
                propietario = int(
                    canal.topic.split(":")[1]
                )

            except ValueError:
                pass

        es_propietario = propietario == interaction.user.id

        es_admin = (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.administrator
        )

        if not es_propietario and not es_admin:

            await interaction.response.send_message(
                "❌ Solo el creador del ticket o un administrador puede cerrarlo.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 Cerrando ticket..."
        )

        await canal.delete(
            reason=f"Ticket cerrado por {interaction.user}"
        )


# =========================================================
# COMANDO PARA PUBLICAR PANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica el panel de tickets."
)
async def ticketpanel(interaction):

    if interaction.channel_id not in CANALES_TICKETS:

        await interaction.response.send_message(
            "❌ Este comando solo funciona en los canales configurados.",
            ephemeral=True
        )

        return

    if not isinstance(interaction.user, discord.Member):

        return

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ Necesitas permisos de Administrador.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🎫 Centro de soporte de Pilares",
        description=(
            "¿Necesitas ayuda? Selecciona una opción:\n\n"
            "📝 **Postulación**\n"
            "Presenta tu candidatura para formar parte del equipo.\n\n"
            "❓ **Duda**\n"
            "Pregunta cualquier cosa sobre el servidor.\n\n"
            "🐛 **Bug**\n"
            "Reporta un error o problema.\n\n"
            "🚨 **Reportar usuario**\n"
            "Reporta a un usuario al equipo."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Pilares • Sistema de tickets"
    )

    await interaction.channel.send(
        embed=embed,
        view=PanelTicketsView()
    )

    await interaction.response.send_message(
        "✅ Panel publicado correctamente.",
        ephemeral=True
    )


# =========================================================
# BOT CONECTADO
# =========================================================

@bot.event
async def on_ready():

    print("--------------------------------")
    print(f"🎫 Bot de tickets: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("--------------------------------")

    bot.add_view(PanelTicketsView())
    bot.add_view(CerrarTicketView())

    try:

        comandos = await bot.tree.sync()

        print(
            f"✅ {len(comandos)} comandos sincronizados."
        )

    except Exception as error:

        print(
            f"❌ Error sincronizando comandos: {error}"
        )


# =========================================================
# INICIAR
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta TOKEN_DISCORD en las variables de Railway."
    )

bot.run(TOKEN)

