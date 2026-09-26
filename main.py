import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
import json
from datetime import datetime, timezone

# ============================================================
# ECLIPSE WORLD — TICKET SYSTEM
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Canales donde se puede publicar el panel
PANEL_CHANNELS = [
    1434297124539076738,
    1551198802164064266
]

# Rol existente de soporte
SUPPORT_ROLE_ID = 1552374542909833246

# La categoría de cerrados la crea automáticamente el bot
CLOSED_CATEGORY_NAME = "📂 TICKETS CERRADOS"

# Logo
LOGO_PATH = "logo.png"

# Base de datos
DATABASE = "tickets.db"


# ============================================================
# BASE DE DATOS
# ============================================================

db = sqlite3.connect(DATABASE, check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    claimed_by INTEGER,
    closed INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    form_answers TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    staff_id INTEGER,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(channel_id, user_id)
)
""")

db.commit()


# ============================================================
# CONFIGURACIÓN DEL BOT
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

views_loaded = False


# ============================================================
# CATEGORÍAS / FORMULARIOS
# ============================================================

TICKET_TYPES = {

    "soporte": {
        "name": "🎫 Soporte general",
        "title": "Soporte general",
        "description": "Ayuda general con Eclipse World.",
        "color": discord.Color.blurple(),
        "fields": [
            {
                "id": "problema",
                "label": "¿En qué podemos ayudarte?",
                "style": discord.TextStyle.paragraph,
                "required": True
            },
            {
                "id": "extra",
                "label": "Información adicional",
                "style": discord.TextStyle.paragraph,
                "required": False
            }
        ]
    },

    "reportar": {
        "name": "🚨 Reportar usuario",
        "title": "Reporte de usuario",
        "description": "Utiliza esta sección para reportar un comportamiento.",
        "color": discord.Color.red(),
        "fields": [
            {
                "id": "usuario",
                "label": "Usuario a reportar",
                "style": discord.TextStyle.short,
                "required": True
            },
            {
                "id": "motivo",
                "label": "Motivo del reporte",
                "style": discord.TextStyle.paragraph,
                "required": True
            },
            {
                "id": "pruebas",
                "label": "Pruebas o enlaces",
                "style": discord.TextStyle.paragraph,
                "required": False
            }
        ]
    },

    "bug": {
        "name": "🐛 Reportar bug",
        "title": "Reporte de bug",
        "description": "Ayúdanos a detectar y solucionar problemas.",
        "color": discord.Color.orange(),
        "fields": [
            {
                "id": "bug",
                "label": "¿Qué bug encontraste?",
                "style": discord.TextStyle.paragraph,
                "required": True
            },
            {
                "id": "lugar",
                "label": "¿Dónde ocurre?",
                "style": discord.TextStyle.short,
                "required": True
            },
            {
                "id": "pasos",
                "label": "Pasos para reproducirlo",
                "style": discord.TextStyle.paragraph,
                "required": True
            },
            {
                "id": "pruebas",
                "label": "Pruebas o enlaces",
                "style": discord.TextStyle.paragraph,
                "required": False
            }
        ]
    },

    "postulacion": {
        "name": "👥 Postulaciones",
        "title": "Postulación",
        "description": "Presenta tu candidatura para formar parte del equipo.",
        "color": discord.Color.green(),
        "fields": [
            {
                "id": "puesto",
                "label": "¿A qué puesto te postulas?",
                "style": discord.TextStyle.short,
                "required": True
            },
            {
                "id": "motivo",
                "label": "¿Por qué quieres entrar?",
                "style": discord.TextStyle.paragraph,
                "required": True
            },
            {
                "id": "experiencia",
                "label": "Experiencia previa",
                "style": discord.TextStyle.paragraph,
                "required": True
            }
        ]
    },

    "estafa": {
        "name": "💰 Estafas",
        "title": "Reporte de estafa",
        "description": "Reporta posibles estafas o fraudes.",
        "color": discord.Color.red(),
        "fields": [
            {
                "id": "usuario",
                "label": "Usuario involucrado",
                "style": discord.TextStyle.short,
                "required": True
            },
            {
                "id": "ocurrido",
                "label": "¿Qué ocurrió?",
                "style": discord.TextStyle.paragraph,
                "required": True
            },
            {
                "id": "pruebas",
                "label": "Pruebas o enlaces",
                "style": discord.TextStyle.paragraph,
                "required": False
            }
        ]
    }
}


# ============================================================
# UTILIDADES
# ============================================================

def now():
    return datetime.now(timezone.utc)


def discord_timestamp(dt=None):
    if dt is None:
        dt = now()
    return f"<t:{int(dt.timestamp())}:F>"


def is_support(member: discord.Member):
    role = member.guild.get_role(SUPPORT_ROLE_ID)

    if role is None:
        return False

    return role in member.roles or member.guild_permissions.administrator


async def get_closed_category(guild: discord.Guild):

    category = discord.utils.get(
        guild.categories,
        name=CLOSED_CATEGORY_NAME
    )

    if category:
        return category

    support_role = guild.get_role(SUPPORT_ROLE_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        )
    }

    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        )

    category = await guild.create_category(
        CLOSED_CATEGORY_NAME,
        overwrites=overwrites,
        reason="Eclipse World ticket archive"
    )

    return category


# ============================================================
# FORMULARIO
# ============================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, ticket_type):

        self.ticket_type = ticket_type
        data = TICKET_TYPES[ticket_type]

        super().__init__(
            title=data["title"][:45]
        )

        self.inputs = []

        for field in data["fields"]:

            text_input = discord.ui.TextInput(
                label=field["label"][:45],
                custom_id=field["id"],
                style=field["style"],
                required=field["required"],
                max_length=1000
            )

            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        if guild is None:
            return

        # ====================================================
        # COMPROBAR TICKET ABIERTO
        # ====================================================

        existing = db.execute("""
            SELECT channel_id
            FROM tickets
            WHERE guild_id = ?
            AND user_id = ?
            AND closed = 0
        """, (
            guild.id,
            interaction.user.id
        )).fetchone()

        if existing:

            channel = guild.get_channel(
                existing["channel_id"]
            )

            if channel:

                await interaction.response.send_message(
                    f"⚠️ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )

                return

            db.execute("""
                UPDATE tickets
                SET closed = 1
                WHERE channel_id = ?
            """, (
                existing["channel_id"],
            ))

            db.commit()

        # ====================================================
        # RESPUESTAS
        # ====================================================

        answers = {}

        for item in self.inputs:
            answers[item.custom_id] = item.value

        data = TICKET_TYPES[self.ticket_type]

        # ====================================================
        # PERMISOS
        # ====================================================

        support_role = guild.get_role(
            SUPPORT_ROLE_ID
        )

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        if support_role:

            overwrites[support_role] = \
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

        if guild.me:

            overwrites[guild.me] = \
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

        # ====================================================
        # NOMBRE
        # ====================================================

        username = (
            interaction.user.name
            .lower()
            .replace(" ", "-")
        )

        channel_name = f"ticket-{username}"[:100]

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason="Nuevo ticket Eclipse World"
        )

        # ====================================================
        # GUARDAR
        # ====================================================

        db.execute("""
            INSERT INTO tickets (
                channel_id,
                guild_id,
                user_id,
                category,
                claimed_by,
                closed,
                created_at,
                form_answers
            )
            VALUES (?, ?, ?, ?, NULL, 0, ?, ?)
        """, (
            channel.id,
            guild.id,
            interaction.user.id,
            self.ticket_type,
            now().isoformat(),
            json.dumps(
                answers,
                ensure_ascii=False
            )
        ))

        db.commit()

        # ====================================================
        # EMBED
        # ====================================================

        embed = discord.Embed(
            title=f"{data['name']}",
            description=(
                f"## Eclipse World Support\n\n"
                f"Hola {interaction.user.mention} 👋\n\n"
                f"Tu solicitud ha sido registrada correctamente.\n"
                f"Un miembro del equipo la revisará lo antes posible.\n\n"
                f"**Estado:** 🟢 Abierto\n"
                f"**Creado:** {discord_timestamp()}"
            ),
            color=data["color"]
        )

        embed.set_footer(
            text="Eclipse World • Support System"
        )

        if os.path.exists(LOGO_PATH):

            file = discord.File(
                LOGO_PATH,
                filename="logo.png"
            )

            embed.set_thumbnail(
                url="attachment://logo.png"
            )

        else:
            file = None

        # ====================================================
        # RESPUESTAS FORMULARIO
        # ====================================================

        for field in data["fields"]:

            value = answers.get(
                field["id"],
                ""
            )

            if value:

                embed.add_field(
                    name=field["label"],
                    value=value[:1024],
                    inline=False
                )

        content = (
            f"{interaction.user.mention}\n"
            f"<@&{SUPPORT_ROLE_ID}>"
        )

        if file:

            await channel.send(
                content=content,
                embed=embed,
                file=file,
                view=TicketControlView()
            )

        else:

            await channel.send(
                content=content,
                embed=embed,
                view=TicketControlView()
            )

        await interaction.response.send_message(
            f"✅ Tu ticket ha sido creado: {channel.mention}",
            ephemeral=True
        )


# ============================================================
# PANEL PRINCIPAL
# ============================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soporte",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ew_ticket_support"
    )
    async def support(self, interaction, button):

        await interaction.response.send_modal(
            TicketModal("soporte")
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ew_ticket_report"
    )
    async def report(self, interaction, button):

        await interaction.response.send_modal(
            TicketModal("reportar")
        )

    @discord.ui.button(
        label="Bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="ew_ticket_bug"
    )
    async def bug(self, interaction, button):

        await interaction.response.send_modal(
            TicketModal("bug")
        )

    @discord.ui.button(
        label="Postulación",
        emoji="👥",
        style=discord.ButtonStyle.success,
        custom_id="ew_ticket_application"
    )
    async def application(self, interaction, button):

        await interaction.response.send_modal(
            TicketModal("postulacion")
        )

    @discord.ui.button(
        label="Estafa",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ew_ticket_scam"
    )
    async def scam(self, interaction, button):

        await interaction.response.send_modal(
            TicketModal("estafa")
        )


# ============================================================
# CONTROLES DE TICKET
# ============================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # ========================================================
    # RECLAMAR
    # ========================================================

    @discord.ui.button(
        label="Reclamar",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="ew_ticket_claim"
    )
    async def claim(self, interaction, button):

        if not interaction.guild:
            return

        if not is_support(interaction.user):

            await interaction.response.send_message(
                "⛔ Esta acción está reservada al equipo de soporte.",
                ephemeral=True
            )

            return

        ticket = db.execute("""
            SELECT *
            FROM tickets
            WHERE channel_id = ?
        """, (
            interaction.channel.id,
        )).fetchone()

        if not ticket:

            await interaction.response.send_message(
                "❌ Este ticket no está registrado.",
                ephemeral=True
            )

            return

        if ticket["closed"]:

            await interaction.response.send_message(
                "🔒 Este ticket ya está cerrado.",
                ephemeral=True
            )

            return

        if ticket["claimed_by"]:

            staff = interaction.guild.get_member(
                ticket["claimed_by"]
            )

            name = (
                staff.mention
                if staff
                else f"<@{ticket['claimed_by']}>"
            )

            await interaction.response.send_message(
                f"📌 Este ticket ya está siendo atendido por {name}.",
                ephemeral=True
            )

            return

        db.execute("""
            UPDATE tickets
            SET claimed_by = ?
            WHERE channel_id = ?
        """, (
            interaction.user.id,
            interaction.channel.id
        ))

        db.commit()

        support_role = interaction.guild.get_role(
            SUPPORT_ROLE_ID
        )

        if support_role:

            await interaction.channel.set_permissions(
                support_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

        await interaction.channel.set_permissions(
            interaction.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        button.label = f"Atendido por {interaction.user.display_name}"
        button.disabled = True

        await interaction.response.edit_message(
            view=self
        )

        await interaction.channel.send(
            f"📌 **{interaction.user.mention} ha tomado este ticket.**\n\n"
            f"El resto del equipo puede seguir consultándolo, "
            f"pero únicamente el usuario y el staff asignado podrán escribir."
        )

    # ========================================================
    # LIBERAR
    # ========================================================

    @discord.ui.button(
        label="Liberar",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="ew_ticket_release"
    )
    async def release(self, interaction, button):

        if not interaction.guild:
            return

        if not is_support(interaction.user):

            await interaction.response.send_message(
                "⛔ Esta acción está reservada al equipo de soporte.",
                ephemeral=True
            )

            return

        ticket = db.execute("""
            SELECT *
            FROM tickets
            WHERE channel_id = ?
        """, (
            interaction.channel.id,
        )).fetchone()

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket no encontrado.",
                ephemeral=True
            )

            return

        if not ticket["claimed_by"]:

            await interaction.response.send_message(
                "ℹ️ Este ticket no está reclamado.",
                ephemeral=True
            )

            return

        if ticket["claimed_by"] != interaction.user.id:

            await interaction.response.send_message(
                "⛔ Solo puede liberar el ticket la persona que lo reclamó.",
                ephemeral=True
            )

            return

        db.execute("""
            UPDATE tickets
            SET claimed_by = NULL
            WHERE channel_id = ?
        """, (
            interaction.channel.id,
        ))

        db.commit()

        support_role = interaction.guild.get_role(
            SUPPORT_ROLE_ID
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
            overwrite=None
        )

        claim_button = discord.utils.get(
            self.children,
            custom_id="ew_ticket_claim"
        )

        if claim_button:

            claim_button.label = "Reclamar"
            claim_button.disabled = False

        await interaction.response.edit_message(
            view=self
        )

        await interaction.channel.send(
            f"🔄 **{interaction.user.mention} ha liberado el ticket.**"
        )

    # ========================================================
    # CERRAR
    # ========================================================

    @discord.ui.button(
        label="Cerrar",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ew_ticket_close"
    )
    async def close(self, interaction, button):

        if not interaction.guild:
            return

        if not is_support(interaction.user):

            await interaction.response.send_message(
                "⛔ Solo el equipo de soporte puede cerrar tickets.",
                ephemeral=True
            )

            return

        ticket = db.execute("""
            SELECT *
            FROM tickets
            WHERE channel_id = ?
        """, (
            interaction.channel.id,
        )).fetchone()

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket no encontrado.",
                ephemeral=True
            )

            return

        if ticket["closed"]:

            await interaction.response.send_message(
                "🔒 Este ticket ya está cerrado.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        # ====================================================
        # CATEGORÍA ARCHIVO
        # ====================================================

        closed_category = await get_closed_category(
            interaction.guild
        )

        # ====================================================
        # DATABASE
        # ====================================================

        db.execute("""
            UPDATE tickets
            SET closed = 1,
                closed_at = ?
            WHERE channel_id = ?
        """, (
            now().isoformat(),
            interaction.channel.id
        ))

        db.commit()

        # ====================================================
        # MOVER
        # ====================================================

        await interaction.channel.edit(
            category=closed_category,
            reason="Ticket cerrado y archivado"
        )

        # ====================================================
        # BLOQUEAR USUARIO
        # ====================================================

        user = interaction.guild.get_member(
            ticket["user_id"]
        )

        if user:

            await interaction.channel.set_permissions(
                user,
                view_channel=False,
                send_messages=False
            )

        support_role = interaction.guild.get_role(
            SUPPORT_ROLE_ID
        )

        if support_role:

            await interaction.channel.set_permissions(
                support_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

        # Staff que lo atendió
        if ticket["claimed_by"]:

            staff = interaction.guild.get_member(
                ticket["claimed_by"]
            )

            if staff:

                await interaction.channel.set_permissions(
                    staff,
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True
                )

        # ====================================================
        # NOMBRE
        # ====================================================

        new_name = interaction.channel.name

        if not new_name.startswith("🔒-"):

            new_name = f"🔒-{new_name}"

        await interaction.channel.edit(
            name=new_name[:100]
        )

        # ====================================================
        # RESUMEN
        # ====================================================

        category_data = TICKET_TYPES.get(
            ticket["category"]
        )

        category_name = (
            category_data["name"]
            if category_data
            else ticket["category"]
        )

        claimed = (
            f"<@{ticket['claimed_by']}>"
            if ticket["claimed_by"]
            else "Sin asignar"
        )

        embed = discord.Embed(
            title="📁 TICKET ARCHIVADO",
            description=(
                "Este ticket ha sido cerrado y archivado.\n"
                "La conversación se conserva para el equipo de Eclipse World."
            ),
            color=discord.Color.dark_grey()
        )

        embed.add_field(
            name="👤 Usuario",
            value=f"<@{ticket['user_id']}",
            inline=True
        )

        embed.add_field(
            name="📂 Categoría",
            value=category_name,
            inline=True
        )

        embed.add_field(
            name="👮 Atendido por",
            value=claimed,
            inline=True
        )

        embed.add_field(
            name="🔒 Cerrado por",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="🕐 Fecha",
            value=discord_timestamp(),
            inline=True
        )

        embed.set_footer(
            text="Eclipse World • Ticket Archive"
        )

        await interaction.channel.send(
            embed=embed
        )

        # ====================================================
        # VALORACIÓN
        # ====================================================

        if user:

            try:

                rating_embed = discord.Embed(
                    title="⭐ Tu opinión importa",
                    description=(
                        "Tu ticket de **Eclipse World** ha sido cerrado.\n\n"
                        "Selecciona una valoración de **1 a 5 estrellas** "
                        "para valorar la atención recibida."
                    ),
                    color=discord.Color.gold()
                )

                rating_embed.set_footer(
                    text="Eclipse World • Support Quality"
                )

                await user.send(
                    embed=rating_embed,
                    view=RatingView(
                        interaction.channel.id
                    )
                )

            except discord.Forbidden:

                await interaction.channel.send(
                    f"⚠️ No se pudo enviar la valoración a <@{ticket['user_id']}> "
                    f"porque tiene los mensajes directos cerrados."
                )

        await interaction.followup.send(
            "✅ Ticket cerrado y archivado. La conversación no ha sido eliminada.",
            ephemeral=True
        )


# ============================================================
# VALORACIONES
# ============================================================

class RatingView(discord.ui.View):

    def __init__(self, channel_id):

        super().__init__(timeout=None)

        self.channel_id = channel_id

    async def rate(
        self,
        interaction,
        rating
    ):

        ticket = db.execute("""
            SELECT *
            FROM tickets
            WHERE channel_id = ?
        """, (
            self.channel_id,
        )).fetchone()

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket no encontrado.",
                ephemeral=True
            )

            return

        if interaction.user.id != ticket["user_id"]:

            await interaction.response.send_message(
                "⛔ Esta valoración pertenece a otro usuario.",
                ephemeral=True
            )

            return

        existing = db.execute("""
            SELECT id
            FROM ratings
            WHERE channel_id = ?
            AND user_id = ?
        """, (
            self.channel_id,
            interaction.user.id
        )).fetchone()

        if existing:

            await interaction.response.send_message(
                "⭐ Ya has valorado este ticket.",
                ephemeral=True
            )

            return

        db.execute("""
            INSERT INTO ratings (
                channel_id,
                guild_id,
                user_id,
                staff_id,
                rating,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, NULL, ?)
        """, (
            self.channel_id,
            ticket["guild_id"],
            interaction.user.id,
            ticket["claimed_by"],
            rating,
            now().isoformat()
        ))

        db.commit()

        await interaction.response.send_modal(
            RatingCommentModal(
                self.channel_id,
                rating
            )
        )

    @discord.ui.button(
        label="1",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="ew_rating_1"
    )
    async def one(self, interaction, button):
        await self.rate(interaction, 1)

    @discord.ui.button(
        label="2",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="ew_rating_2"
    )
    async def two(self, interaction, button):
        await self.rate(interaction, 2)

    @discord.ui.button(
        label="3",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="ew_rating_3"
    )
    async def three(self, interaction, button):
        await self.rate(interaction, 3)

    @discord.ui.button(
        label="4",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="ew_rating_4"
    )
    async def four(self, interaction, button):
        await self.rate(interaction, 4)

    @discord.ui.button(
        label="5",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="ew_rating_5"
    )
    async def five(self, interaction, button):
        await self.rate(interaction, 5)


# ============================================================
# COMENTARIO DE VALORACIÓN
# ============================================================

class RatingCommentModal(discord.ui.Modal):

    def __init__(
        self,
        channel_id,
        rating
    ):

        super().__init__(
            title="Comentario opcional"
        )

        self.channel_id = channel_id
        self.rating = rating

        self.comment = discord.ui.TextInput(
            label="¿Quieres dejar un comentario?",
            placeholder="Cuéntanos qué tal fue la atención...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )

        self.add_item(self.comment)

    async def on_submit(self, interaction):

        db.execute("""
            UPDATE ratings
            SET comment = ?
            WHERE channel_id = ?
            AND user_id = ?
        """, (
            self.comment.value or None,
            self.channel_id,
            interaction.user.id
        ))

        db.commit()

        ticket = db.execute("""
            SELECT *
            FROM tickets
            WHERE channel_id = ?
        """, (
            self.channel_id,
        )).fetchone()

        if ticket:

            guild = bot.get_guild(
                ticket["guild_id"]
            )

            if guild:

                channel = guild.get_channel(
                    self.channel_id
                )

                if channel:

                    comment = (
                        self.comment.value
                        if self.comment.value
                        else "Sin comentario"
                    )

                    embed = discord.Embed(
                        title="⭐ Nueva valoración",
                        color=discord.Color.gold()
                    )

                    embed.add_field(
                        name="👤 Usuario",
                        value=interaction.user.mention,
                        inline=True
                    )

                    embed.add_field(
                        name="⭐ Puntuación",
                        value=f"{self.rating}/5",
                        inline=True
                    )

                    embed.add_field(
                        name="💬 Comentario",
                        value=comment[:1024],
                        inline=False
                    )

                    embed.set_footer(
                        text="Eclipse World • Support Quality"
                    )

                    await channel.send(
                        embed=embed
                    )

        await interaction.response.send_message(
            "⭐ Gracias por valorar el soporte de Eclipse World.",
            ephemeral=True
        )


# ============================================================
# /ticketpanel
# ============================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica el sistema de tickets de Eclipse World"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="ECLIPSE WORLD",
        description=(
            "## 🎫 Centro de soporte\n\n"
            "Bienvenido al sistema oficial de soporte de **Eclipse World**.\n\n"
            "Selecciona la categoría que corresponda a tu solicitud. "
            "Antes de crear el ticket se te solicitará información "
            "para que el equipo pueda atenderte correctamente.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "### 📋 Normativa\n\n"
            "⏳ **1.** Ten paciencia durante la atención.\n\n"
            "🚫 **2.** No insultes ni faltes al respeto al equipo.\n\n"
            "📌 **3.** Mantente activo en tu ticket.\n\n"
            "📂 **4.** Utiliza la categoría correspondiente.\n\n"
            "⚠️ **5.** Abrir tickets sin motivo puede ser sancionable.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 **Nuestro equipo atenderá tu solicitud lo antes posible.**"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Eclipse World • Official Support System"
    )

    if os.path.exists(LOGO_PATH):

        file = discord.File(
            LOGO_PATH,
            filename="logo.png"
        )

        embed.set_thumbnail(
            url="attachment://logo.png"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file,
            view=TicketPanelView()
        )

    else:

        await interaction.response.send_message(
            embed=embed,
            view=TicketPanelView()
        )


@ticketpanel.error
async def ticketpanel_error(
    interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        await interaction.response.send_message(
            "⛔ Necesitas permisos de administrador.",
            ephemeral=True
        )


# ============================================================
# /ticketstats
# ============================================================

@bot.tree.command(
    name="ticketstats",
    description="Muestra estadísticas del sistema de soporte"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketstats(
    interaction: discord.Interaction
):

    total = db.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE guild_id = ?
    """, (
        interaction.guild.id,
    )).fetchone()["total"]

    open_tickets = db.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE guild_id = ?
        AND closed = 0
    """, (
        interaction.guild.id,
    )).fetchone()["total"]

    closed = db.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE guild_id = ?
        AND closed = 1
    """, (
        interaction.guild.id,
    )).fetchone()["total"]

    rating_data = db.execute("""
        SELECT
            COUNT(*) AS amount,
            AVG(rating) AS average
        FROM ratings
        WHERE guild_id = ?
    """, (
        interaction.guild.id,
    )).fetchone()

    amount = rating_data["amount"] or 0
    average = rating_data["average"]

    average_text = (
        f"{average:.2f}/5"
        if average is not None
        else "Sin valoraciones"
    )

    embed = discord.Embed(
        title="📊 Eclipse World • Support Analytics",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🎫 Tickets totales",
        value=str(total),
        inline=True
    )

    embed.add_field(
        name="🟢 Abiertos",
        value=str(open_tickets),
        inline=True
    )

    embed.add_field(
        name="🔒 Cerrados",
        value=str(closed),
        inline=True
    )

    embed.add_field(
        name="⭐ Valoraciones",
        value=str(amount),
        inline=True
    )

    embed.add_field(
        name="📈 Media",
        value=average_text,
        inline=True
    )

    embed.set_footer(
        text="Eclipse World • Support Analytics"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# INICIO
# ============================================================

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

        await bot.tree.sync()

        views_loaded = True

    print(
        f"✅ Eclipse World Tickets conectado como {bot.user}"
    )


# ============================================================
# ARRANQUE
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "❌ No existe la variable DISCORD_TOKEN en Railway."
    )

bot.run(TOKEN)
