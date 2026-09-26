import os
import sqlite3
import discord

from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("TOKEN_DISCORD")

PANEL_CHANNELS = [
    1434297124539076738,
    1551198802164064266,
]

ROL_SOPORTE = 1552374542909833246

LOGO_PATH = "logo.png"
DB_PATH = "tickets.db"

OPEN_CATEGORY_NAME = "🎫 TICKETS"
CLOSED_CATEGORY_NAME = "📂 TICKETS CERRADOS"


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# BASE DE DATOS
# =========================================================

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    claimed_by INTEGER,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    rating INTEGER,
    rating_comment TEXT
)
""")

db.commit()


def get_ticket(channel_id):
    return db.execute(
        "SELECT * FROM tickets WHERE channel_id = ?",
        (channel_id,)
    ).fetchone()


def create_ticket(channel_id, guild_id, user_id, category):
    db.execute(
        """
        INSERT INTO tickets
        (channel_id, guild_id, user_id, category, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            channel_id,
            guild_id,
            user_id,
            category,
            datetime.now(timezone.utc).isoformat()
        )
    )
    db.commit()


def claim_ticket(channel_id, staff_id):
    db.execute(
        "UPDATE tickets SET claimed_by = ? WHERE channel_id = ?",
        (staff_id, channel_id)
    )
    db.commit()


def unclaim_ticket(channel_id):
    db.execute(
        "UPDATE tickets SET claimed_by = NULL WHERE channel_id = ?",
        (channel_id,)
    )
    db.commit()


def close_ticket(channel_id):
    db.execute(
        """
        UPDATE tickets
        SET closed_at = ?
        WHERE channel_id = ?
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            channel_id
        )
    )
    db.commit()


def save_rating(channel_id, rating, comment):
    db.execute(
        """
        UPDATE tickets
        SET rating = ?, rating_comment = ?
        WHERE channel_id = ?
        """,
        (
            rating,
            comment,
            channel_id
        )
    )
    db.commit()


# =========================================================
# UTILIDADES
# =========================================================

def is_support(member: discord.Member):
    return (
        member.guild_permissions.administrator
        or any(role.id == ROL_SOPORTE for role in member.roles)
    )


def get_support_role(guild):
    return guild.get_role(ROL_SOPORTE)


def get_logo():
    if os.path.exists(LOGO_PATH):
        return discord.File(LOGO_PATH, filename="logo.png")

    return None


def logo_embed(embed):
    if os.path.exists(LOGO_PATH):
        embed.set_thumbnail(url="attachment://logo.png")


async def get_or_create_category(guild, name, private=False):

    existing = discord.utils.get(
        guild.categories,
        name=name
    )

    if existing:
        return existing

    overwrites = {}

    if private:
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=False
        )

        support_role = get_support_role(guild)

        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

    return await guild.create_category(
        name=name,
        overwrites=overwrites,
        reason="Sistema de tickets Eclipse World"
    )


# =========================================================
# PREGUNTAS DE LOS FORMULARIOS
# =========================================================

QUESTIONS = {

    "🎫 Soporte general": [
        ("problema", "¿En qué podemos ayudarte?", True),
        ("info", "Añade información adicional", False),
    ],

    "🚨 Reportar usuario": [
        ("usuario", "Usuario que quieres reportar", True),
        ("motivo", "¿Qué ha ocurrido?", True),
        ("pruebas", "Pruebas / información adicional", False),
    ],

    "🐛 Reportar bug": [
        ("bug", "Describe el bug", True),
        ("lugar", "¿Dónde ocurre?", True),
        ("pasos", "¿Cómo podemos reproducirlo?", False),
    ],

    "👥 Postulaciones": [
        ("usuario", "Tu nombre / usuario", True),
        ("puesto", "¿A qué puesto te presentas?", True),
        ("experiencia", "Cuéntanos tu experiencia", True),
        ("info", "Información adicional", False),
    ],

    "💰 Estafas": [
        ("usuario", "Usuario relacionado con la estafa", True),
        ("problema", "¿Qué ha ocurrido?", True),
        ("pruebas", "Pruebas / información adicional", False),
    ],
}


# =========================================================
# MODAL
# =========================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, category):
        super().__init__(
            title=f"Eclipse World • {category}"
        )

        self.category = category
        self.inputs = []

        questions = QUESTIONS[category]

        for custom_id, label, required in questions:

            text_input = discord.ui.TextInput(
                custom_id=custom_id,
                label=label[:45],
                style=discord.TextStyle.paragraph,
                required=required,
                max_length=1000
            )

            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ Este sistema solo funciona dentro del servidor.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Categoría de tickets abiertos
        open_category = await get_or_create_category(
            guild,
            OPEN_CATEGORY_NAME,
            private=False
        )

        support_role = get_support_role(guild)

        overwrites = {

            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        }

        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        username = interaction.user.name.lower()
        username = username.replace(" ", "-")

        channel_name = f"ticket-{username}"

        # Evitar duplicados
        existing = discord.utils.find(
            lambda c: c.name == channel_name,
            guild.text_channels
        )

        if existing:
            await interaction.followup.send(
                f"⚠️ Ya tienes un ticket abierto: {existing.mention}",
                ephemeral=True
            )
            return

        channel = await guild.create_text_channel(
            name=channel_name[:100],
            category=open_category,
            overwrites=overwrites,
            reason="Nuevo ticket Eclipse World"
        )

        create_ticket(
            channel.id,
            guild.id,
            interaction.user.id,
            self.category
        )

        # =================================================
        # EMBED DEL TICKET
        # =================================================

        embed = discord.Embed(
            title="🎫 Ticket creado",
            description=(
                f"Hola {interaction.user.mention}, tu ticket ha sido creado.\n\n"
                f"**Categoría:** {self.category}\n\n"
                "Un miembro del equipo te atenderá lo antes posible."
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        for text_input in self.inputs:

            value = text_input.value.strip()

            if not value:
                value = "No especificado"

            embed.add_field(
                name=text_input.label,
                value=value[:1024],
                inline=False
            )

        embed.set_footer(
            text="Eclipse World • Sistema de soporte"
        )

        logo_file = get_logo()

        if logo_file:
            embed.set_thumbnail(
                url="attachment://logo.png"
            )

        support_mention = (
            support_role.mention
            if support_role
            else "@Soporte"
        )

        content = (
            f"{interaction.user.mention} {support_mention}\n\n"
            "📌 **Un miembro del soporte puede reclamar este ticket.**"
        )

        if logo_file:

            await channel.send(
                content=content,
                embed=embed,
                file=logo_file,
                view=TicketControlView()
            )

        else:

            await channel.send(
                content=content,
                embed=embed,
                view=TicketControlView()
            )

        await interaction.followup.send(
            f"✅ Ticket creado correctamente: {channel.mention}",
            ephemeral=True
        )


# =========================================================
# PANEL PRINCIPAL
# =========================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def open_modal(
        self,
        interaction: discord.Interaction,
        category: str
    ):

        await interaction.response.send_modal(
            TicketModal(category)
        )

    @discord.ui.button(
        label="Soporte general",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_support"
    )
    async def support(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.open_modal(
            interaction,
            "🎫 Soporte general"
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_report"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.open_modal(
            interaction,
            "🚨 Reportar usuario"
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
        await self.open_modal(
            interaction,
            "🐛 Reportar bug"
        )

    @discord.ui.button(
        label="Postulaciones",
        emoji="👥",
        style=discord.ButtonStyle.success,
        custom_id="ticket_apply"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.open_modal(
            interaction,
            "👥 Postulaciones"
        )

    @discord.ui.button(
        label="Estafas",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_scam"
    )
    async def scam(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.open_modal(
            interaction,
            "💰 Estafas"
        )


# =========================================================
# CONTROL DEL TICKET
# =========================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Reclamar ticket",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_claim"
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(interaction.user, discord.Member):
            return

        if not is_support(interaction.user):

            await interaction.response.send_message(
                "❌ Solo el equipo de soporte puede reclamar tickets.",
                ephemeral=True
            )
            return

        ticket = get_ticket(interaction.channel.id)

        if not ticket:

            await interaction.response.send_message(
                "❌ Este canal no está registrado como ticket.",
                ephemeral=True
            )
            return

        if ticket["closed_at"]:

            await interaction.response.send_message(
                "❌ Este ticket ya está cerrado.",
                ephemeral=True
            )
            return

        if ticket["claimed_by"]:

            claimer = interaction.guild.get_member(
                ticket["claimed_by"]
            )

            name = (
                claimer.mention
                if claimer
                else f"<@{ticket['claimed_by']}>"
            )

            await interaction.response.send_message(
                f"📌 Este ticket ya ha sido reclamado por {name}.",
                ephemeral=True
            )
            return

        claim_ticket(
            interaction.channel.id,
            interaction.user.id
        )

        ticket = get_ticket(
            interaction.channel.id
        )

        support_role = get_support_role(
            interaction.guild
        )

        # El soporte deja de escribir
        if support_role:

            await interaction.channel.set_permissions(
                support_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                attach_files=False,
                embed_links=True
            )

        # El staff que reclama sí puede escribir
        await interaction.channel.set_permissions(
            interaction.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        button.label = f"Reclamado por {interaction.user.display_name}"
        button.disabled = True

        await interaction.response.edit_message(
            view=self
        )

        await interaction.channel.send(
            f"📌 **Ticket reclamado por {interaction.user.mention}.**\n"
            "Este miembro del staff se encargará del ticket."
        )

    @discord.ui.button(
        label="Liberar ticket",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_unclaim"
    )
    async def unclaim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(interaction.user, discord.Member):
            return

        if not is_support(interaction.user):

            await interaction.response.send_message(
                "❌ Solo el equipo de soporte puede utilizar esto.",
                ephemeral=True
            )
            return

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Este canal no es un ticket.",
                ephemeral=True
            )
            return

        if not ticket["claimed_by"]:

            await interaction.response.send_message(
                "ℹ️ Este ticket no está reclamado.",
                ephemeral=True
            )
            return

        if (
            ticket["claimed_by"] != interaction.user.id
            and not interaction.user.guild_permissions.administrator
        ):

            await interaction.response.send_message(
                "❌ Solo quien reclamó el ticket puede liberarlo.",
                ephemeral=True
            )
            return

        unclaim_ticket(
            interaction.channel.id
        )

        support_role = get_support_role(
            interaction.guild
        )

        if support_role:

            await interaction.channel.set_permissions(
                support_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        await interaction.channel.set_permissions(
            interaction.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        await interaction.response.send_message(
            "🔄 Ticket liberado. El equipo de soporte vuelve a poder responder.",
        )

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close"
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(interaction.user, discord.Member):
            return

        if not is_support(interaction.user):

            await interaction.response.send_message(
                "❌ Solo el equipo de soporte puede cerrar tickets.",
                ephemeral=True
            )
            return

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Este canal no es un ticket.",
                ephemeral=True
            )
            return

        if ticket["closed_at"]:

            await interaction.response.send_message(
                "❌ Este ticket ya está cerrado.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Cerrando ticket y archivándolo..."
        )

        close_ticket(
            interaction.channel.id
        )

        guild = interaction.guild

        closed_category = await get_or_create_category(
            guild,
            CLOSED_CATEGORY_NAME,
            private=True
        )

        requester = guild.get_member(
            ticket["user_id"]
        )

        support_role = get_support_role(
            guild
        )

        # =================================================
        # PERMISOS DEL TICKET CERRADO
        # =================================================

        await interaction.channel.set_permissions(
            guild.default_role,
            view_channel=False
        )

        if requester:

            await interaction.channel.set_permissions(
                requester,
                view_channel=False,
                send_messages=False
            )

        if support_role:

            await interaction.channel.set_permissions(
                support_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

        if guild.me:

            await interaction.channel.set_permissions(
                guild.me,
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True
            )

        await interaction.channel.edit(
            category=closed_category,
            sync_permissions=False
        )

        # =================================================
        # EMBED DE CIERRE
        # =================================================

        embed = discord.Embed(
            title="🔒 Ticket cerrado",
            description=(
                "Este ticket ha sido cerrado y archivado.\n\n"
                "La conversación **no ha sido eliminada**."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="👤 Usuario",
            value=f"<@{ticket['user_id']}>",
            inline=True
        )

        embed.add_field(
            name="📂 Categoría",
            value=ticket["category"],
            inline=True
        )

        embed.add_field(
            name="🛡️ Cerrado por",
            value=interaction.user.mention,
            inline=True
        )

        embed.set_footer(
            text="Eclipse World • Ticket archivado"
        )

        logo_file = get_logo()

        if logo_file:

            await interaction.channel.send(
                embed=embed,
                file=logo_file
            )

        else:

            await interaction.channel.send(
                embed=embed
            )

        # =================================================
        # RATING POR DM
        # =================================================

        if requester:

            try:

                await requester.send(
                    embed=discord.Embed(
                        title="⭐ Valora tu atención",
                        description=(
                            f"Tu ticket en **{guild.name}** ha terminado.\n\n"
                            "Selecciona una valoración del 1 al 5."
                        ),
                        color=discord.Color.gold()
                    ),
                    view=RatingView(
                        interaction.channel.id
                    )
                )

            except discord.Forbidden:

                await interaction.channel.send(
                    f"⚠️ No se pudo enviar la valoración a "
                    f"{requester.mention} porque tiene los MD cerrados."
                )


# =========================================================
# RATING
# =========================================================

class RatingModal(discord.ui.Modal):

    def __init__(self, channel_id, rating):
        super().__init__(
            title="⭐ Comentario de valoración"
        )

        self.channel_id = channel_id
        self.rating = rating

        self.comment = discord.ui.TextInput(
            label="Comentario (opcional)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            placeholder="Cuéntanos qué tal fue la atención..."
        )

        self.add_item(self.comment)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        ticket = get_ticket(
            self.channel_id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ No se encontró el ticket.",
                ephemeral=True
            )
            return

        if ticket["rating"]:

            await interaction.response.send_message(
                "⚠️ Ya has valorado este ticket.",
                ephemeral=True
            )
            return

        save_rating(
            self.channel_id,
            self.rating,
            self.comment.value
        )

        await interaction.response.send_message(
            f"⭐ Gracias por valorar la atención con **{self.rating}/5**.",
            ephemeral=True
        )


class RatingView(discord.ui.View):

    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    async def rate(
        self,
        interaction: discord.Interaction,
        rating: int
    ):

        ticket = get_ticket(
            self.channel_id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket no encontrado.",
                ephemeral=True
            )
            return

        if ticket["user_id"] != interaction.user.id:

            await interaction.response.send_message(
                "❌ Esta valoración no es para ti.",
                ephemeral=True
            )
            return

        if ticket["rating"]:

            await interaction.response.send_message(
                "⚠️ Ya has valorado este ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            RatingModal(
                self.channel_id,
                rating
            )
        )

    @discord.ui.button(
        label="1",
        emoji="⭐",
        style=discord.ButtonStyle.danger,
        custom_id="rating_1"
    )
    async def one(
        self,
        interaction,
        button
    ):
        await self.rate(interaction, 1)

    @discord.ui.button(
        label="2",
        emoji="⭐",
        style=discord.ButtonStyle.danger,
        custom_id="rating_2"
    )
    async def two(
        self,
        interaction,
        button
    ):
        await self.rate(interaction, 2)

    @discord.ui.button(
        label="3",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="rating_3"
    )
    async def three(
        self,
        interaction,
        button
    ):
        await self.rate(interaction, 3)

    @discord.ui.button(
        label="4",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="rating_4"
    )
    async def four(
        self,
        interaction,
        button
    ):
        await self.rate(interaction, 4)

    @discord.ui.button(
        label="5",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="rating_5"
    )
    async def five(
        self,
        interaction,
        button
    ):
        await self.rate(interaction, 5)


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

    await interaction.response.defer(
        ephemeral=True
    )

    embed = discord.Embed(
        title="🌌 ECLIPSE WORLD",
        description=(
            "🎫 **¿Necesitas Ayuda? Abre un ticket en la categoría "
            "que necesitas! Ten paciencia a la hora de abrir ticket "
            "o de lo contrario serás sancionado!** ⚠️\n\n"

            "📋 **Reglas** 📋\n\n"

            "⏳ *1)* **Ten paciencia a la hora de abrir ticket!** 🕐\n\n"

            "🚫 *2)* **No insultar al equipo del staff!** ⚠️\n\n"

            "📌 *3)* **Estar activo en el ticket o de lo contrario "
            "será cerrado por inactividad!** 🕐\n\n"

            "📂 *4)* **Abrir ticket en su categoría que corresponde "
            "o de lo contrario serás sancionado!**\n\n"

            "⚠️ *5)* **Abrir ticket sin razón es sancionable!** 🚫\n\n\n"

            "🚀 **Te atenderemos lo mas rápido posible!** ⚡"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Eclipse World • Sistema oficial de soporte"
    )

    # Logo
    logo_file = get_logo()

    # Publicar en los dos canales
    sent = []

    for channel_id in PANEL_CHANNELS:

        channel = interaction.guild.get_channel(
            channel_id
        )

        if not channel:
            continue

        try:

            if logo_file:
                # Hay que generar un archivo nuevo por canal
                file = get_logo()

                await channel.send(
                    embed=embed,
                    file=file,
                    view=TicketPanelView()
                )

            else:

                await channel.send(
                    embed=embed,
                    view=TicketPanelView()
                )

            sent.append(channel.mention)

        except discord.Forbidden:
            pass

    if sent:

        await interaction.followup.send(
            "✅ Panel publicado correctamente en:\n"
            + "\n".join(sent),
            ephemeral=True
        )

    else:

        await interaction.followup.send(
            "❌ No pude publicar el panel. "
            "Comprueba los permisos del bot.",
            ephemeral=True
        )


# =========================================================
# /TICKETSTATS
# =========================================================

@bot.tree.command(
    name="ticketstats",
    description="Muestra estadísticas del sistema de tickets"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketstats(
    interaction: discord.Interaction
):

    total = db.execute(
        "SELECT COUNT(*) FROM tickets"
    ).fetchone()[0]

    closed = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE closed_at IS NOT NULL"
    ).fetchone()[0]

    rated = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE rating IS NOT NULL"
    ).fetchone()[0]

    average = db.execute(
        "SELECT AVG(rating) FROM tickets WHERE rating IS NOT NULL"
    ).fetchone()[0]

    if average is None:
        average_text = "Sin valoraciones"
    else:
        average_text = f"{average:.2f}/5 ⭐"

    embed = discord.Embed(
        title="📊 Estadísticas de tickets",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🎫 Tickets totales",
        value=str(total),
        inline=True
    )

    embed.add_field(
        name="🔒 Tickets cerrados",
        value=str(closed),
        inline=True
    )

    embed.add_field(
        name="⭐ Tickets valorados",
        value=str(rated),
        inline=True
    )

    embed.add_field(
        name="📈 Valoración media",
        value=average_text,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# ERRORES DE COMANDOS
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

        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Necesitas permisos de administrador.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Necesitas permisos de administrador.",
                ephemeral=True
            )

    else:

        print(
            f"Error /ticketpanel: {error}"
        )


@ticketstats.error
async def ticketstats_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Necesitas permisos de administrador.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Necesitas permisos de administrador.",
                ephemeral=True
            )

    else:

        print(
            f"Error /ticketstats: {error}"
        )


# =========================================================
# READY
# =========================================================

views_loaded = False


@bot.event
async def on_ready():

    global views_loaded

    if not views_loaded:

        bot.add_view(
            TicketPanelView()
        )

        bot.add_view(
            TicketControlView()
        )

        views_loaded = True

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} comandos sincronizados."
        )

    except Exception as error:

        print(
            f"❌ Error sincronizando comandos: {error}"
        )

    print(
        f"🌌 Eclipse World Ticket Bot conectado como "
        f"{bot.user} ({bot.user.id})"
    )


# =========================================================
# ARRANQUE
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta la variable TOKEN_DISCORD en Railway."
    )


bot.run(TOKEN)
