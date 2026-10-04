import os
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CORRUPTION NETWORK
# TICKETS + ADMINISTRACIÓN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# Canales
TICKET_PANEL_CHANNEL_ID = int(os.getenv("TICKET_PANEL_CHANNEL_ID", "0"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
RATINGS_CHANNEL_ID = int(os.getenv("RATINGS_CHANNEL_ID", "0"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID", "0"))

# Roles
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))

DATABASE = "corruption_network.db"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True


# ============================================================
# BOT
# ============================================================

class CorruptionNetwork(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        init_database()

        # Registrar vistas persistentes
        self.add_view(TicketPanelView())
        self.add_view(TicketControlView())

        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)

            self.tree.copy_global_to(guild=guild)

            await self.tree.sync(guild=guild)

            print(f"[OK] Comandos sincronizados en {GUILD_ID}")

        else:
            await self.tree.sync()

            print("[OK] Comandos globales sincronizados")

    async def on_ready(self):

        print("=" * 55)
        print("CORRUPTION NETWORK")
        print("=" * 55)
        print(f"Bot: {self.user}")
        print(f"ID: {self.user.id}")
        print(f"Servidores: {len(self.guilds)}")
        print("=" * 55)


bot = CorruptionNetwork()


# ============================================================
# DATABASE
# ============================================================

def db_connect():
    return sqlite3.connect(DATABASE)


def init_database():

    db = db_connect()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE,
            guild_id INTEGER,
            user_id INTEGER,
            staff_id INTEGER DEFAULT NULL,
            category TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            closed_at TEXT DEFAULT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER UNIQUE,
            staff_id INTEGER,
            user_id INTEGER,
            rating INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


# ============================================================
# UTILIDADES
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def is_staff(member: discord.Member):

    if member.guild_permissions.administrator:
        return True

    if STAFF_ROLE_ID:
        if any(role.id == STAFF_ROLE_ID for role in member.roles):
            return True

    if ADMIN_ROLE_ID:
        if any(role.id == ADMIN_ROLE_ID for role in member.roles):
            return True

    return False


def is_admin(member: discord.Member):

    if member.guild_permissions.administrator:
        return True

    if ADMIN_ROLE_ID:
        return any(
            role.id == ADMIN_ROLE_ID
            for role in member.roles
        )

    return False


def embed(
    title,
    description,
    color=discord.Color.blurple()
):

    e = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )

    e.set_footer(
        text="Corruption Network"
    )

    return e


async def send_log(
    guild,
    title,
    description,
    color=discord.Color.blurple()
):

    if not LOG_CHANNEL_ID:
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)

    if not channel:
        return

    try:

        await channel.send(
            embed=embed(
                title,
                description,
                color
            )
        )

    except discord.HTTPException:
        pass


def get_ticket(channel_id):

    db = db_connect()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            id,
            channel_id,
            guild_id,
            user_id,
            staff_id,
            category,
            reason,
            created_at,
            closed_at
        FROM tickets
        WHERE channel_id = ?
    """, (channel_id,))

    result = cursor.fetchone()

    db.close()

    return result


# ============================================================
# TICKET MODAL
# ============================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, category):

        self.category = category

        titles = {
            "soporte": "Soporte general",
            "bug": "Reportar bug",
            "reporte": "Reportar usuario",
            "estafa": "Reportar estafa",
            "postulacion": "Postulación"
        }

        super().__init__(
            title=titles.get(
                category,
                "Crear ticket"
            )
        )

    motivo = discord.ui.TextInput(
        label="Explica tu solicitud",
        placeholder="Escribe aquí todos los detalles...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=5,
        max_length=1500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild
        user = interaction.user

        if not guild:
            return

        # ----------------------------------------------------
        # COMPROBAR TICKET ABIERTO
        # ----------------------------------------------------

        db = db_connect()
        cursor = db.cursor()

        cursor.execute("""
            SELECT channel_id
            FROM tickets
            WHERE guild_id = ?
            AND user_id = ?
            AND closed_at IS NULL
        """, (
            guild.id,
            user.id
        ))

        existing = cursor.fetchone()

        db.close()

        if existing:

            channel = guild.get_channel(existing[0])

            if channel:

                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # CATEGORÍA
        # ----------------------------------------------------

        category_channel = None

        if TICKET_CATEGORY_ID:

            category_channel = guild.get_channel(
                TICKET_CATEGORY_ID
            )

        # ----------------------------------------------------
        # PERMISOS
        # ----------------------------------------------------

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            user:
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
                    manage_channels=True,
                    manage_messages=True
                )
        }

        staff_role = None

        if STAFF_ROLE_ID:

            staff_role = guild.get_role(
                STAFF_ROLE_ID
            )

        if staff_role:

            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        # ----------------------------------------------------
        # NOMBRE
        # ----------------------------------------------------

        username = user.name.lower()

        username = "".join(
            character
            for character in username
            if character.isalnum() or character == "-"
        )

        channel_name = f"ticket-{username}"

        # ----------------------------------------------------
        # CREAR CANAL
        # ----------------------------------------------------

        try:

            channel = await guild.create_text_channel(
                channel_name,
                category=category_channel,
                overwrites=overwrites,
                topic=f"Ticket de {user} | ID {user.id}"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No tengo permisos para crear canales.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # GUARDAR TICKET
        # ----------------------------------------------------

        db = db_connect()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO tickets (
                channel_id,
                guild_id,
                user_id,
                category,
                reason,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            channel.id,
            guild.id,
            user.id,
            self.category,
            self.motivo.value,
            utc_now()
        ))

        db.commit()

        ticket_id = cursor.lastrowid

        db.close()

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        category_names = {
            "soporte": "🎫 Soporte general",
            "bug": "🐛 Reporte de bug",
            "reporte": "🚨 Reporte de usuario",
            "estafa": "💰 Reporte de estafa",
            "postulacion": "📋 Postulación"
        }

        category_name = category_names.get(
            self.category,
            "🎫 Ticket"
        )

        ticket_embed = embed(
            f"{category_name}",
            (
                f"Bienvenido {user.mention}.\n\n"
                "Tu solicitud ha sido creada correctamente. "
                "Un miembro del equipo la atenderá lo antes posible.\n\n"
                f"**Solicitud:**\n"
                f"{self.motivo.value}"
            ),
            discord.Color.blurple()
        )

        ticket_embed.add_field(
            name="Estado",
            value="🟢 Abierto",
            inline=True
        )

        ticket_embed.add_field(
            name="Ticket",
            value=f"`#{ticket_id}`",
            inline=True
        )

        ticket_embed.add_field(
            name="Usuario",
            value=user.mention,
            inline=True
        )

        await channel.send(
            content=user.mention,
            embed=ticket_embed,
            view=TicketControlView()
        )

        await interaction.response.send_message(
            f"✅ Tu ticket ha sido creado: {channel.mention}",
            ephemeral=True
        )

        await send_log(
            guild,
            "🎫 Ticket creado",
            (
                f"**Usuario:** {user.mention}\n"
                f"**Canal:** {channel.mention}\n"
                f"**Categoría:** {category_name}\n"
                f"**ID:** `{ticket_id}`"
            ),
            discord.Color.green()
        )


# ============================================================
# PANEL DE TICKETS
# ============================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Soporte",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="cn_ticket_soporte"
    )
    async def soporte(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            TicketModal("soporte")
        )

    @discord.ui.button(
        label="Reportar bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="cn_ticket_bug"
    )
    async def bug(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            TicketModal("bug")
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="cn_ticket_reporte"
    )
    async def reporte(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            TicketModal("reporte")
        )

    @discord.ui.button(
        label="Estafa",
        emoji="💰",
        style=discord.ButtonStyle.secondary,
        custom_id="cn_ticket_estafa"
    )
    async def estafa(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            TicketModal("estafa")
        )

    @discord.ui.button(
        label="Postulación",
        emoji="📋",
        style=discord.ButtonStyle.success,
        custom_id="cn_ticket_postulacion"
    )
    async def postulacion(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            TicketModal("postulacion")
        )


# ============================================================
# CONFIRMACIÓN DE CIERRE
# ============================================================

class CloseConfirmView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=60
        )

    @discord.ui.button(
        label="Sí, cerrar",
        emoji="🔒",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction,
        button
    ):

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Este canal no es un ticket.",
                ephemeral=True
            )

            return

        db = db_connect()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE tickets
            SET closed_at = ?
            WHERE channel_id = ?
        """, (
            utc_now(),
            interaction.channel.id
        ))

        db.commit()
        db.close()

        await interaction.response.edit_message(
            content="🔒 Cerrando ticket...",
            embed=None,
            view=None
        )

        await send_log(
            interaction.guild,
            "🔒 Ticket cerrado",
            (
                f"**Ticket:** #{ticket[0]}\n"
                f"**Usuario:** <@{ticket[3]}>\n"
                f"**Staff:** "
                f"{f'<@{ticket[4]}>' if ticket[4] else 'Sin reclamar'}\n"
                f"**Cerrado por:** {interaction.user.mention}"
            ),
            discord.Color.red()
        )

        # ----------------------------------------------------
        # VALORACIÓN
        # ----------------------------------------------------

        if RATINGS_CHANNEL_ID:

            rating_channel = interaction.guild.get_channel(
                RATINGS_CHANNEL_ID
            )

            if rating_channel:

                await rating_channel.send(
                    embed=embed(
                        "⭐ Valora la atención",
                        (
                            f"<@{ticket[3]}>\n\n"
                            "Gracias por contactar con "
                            "**Corruption Network**.\n\n"
                            "¿Cómo valorarías la atención recibida?"
                        ),
                        discord.Color.gold()
                    ),
                    view=RatingView(
                        ticket[0],
                        ticket[4]
                    )
                )

        await create_transcript(
            interaction.guild,
            ticket,
            interaction.channel
        )

        await interaction.channel.delete(
            reason="Ticket cerrado"
        )

    @discord.ui.button(
        label="Cancelar",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content="❌ Cierre cancelado.",
            embed=None,
            view=None
        )


# ============================================================
# CONTROL DEL TICKET
# ============================================================

class TicketControlView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Reclamar",
        emoji="🙋",
        style=discord.ButtonStyle.success,
        custom_id="cn_ticket_claim"
    )
    async def claim(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Solo el staff puede reclamar tickets.",
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

        if ticket[4]:

            await interaction.response.send_message(
                f"❌ Este ticket ya ha sido reclamado por "
                f"<@{ticket[4]}>.",
                ephemeral=True
            )

            return

        db = db_connect()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE tickets
            SET staff_id = ?
            WHERE channel_id = ?
        """, (
            interaction.user.id,
            interaction.channel.id
        ))

        db.commit()
        db.close()

        await interaction.response.send_message(
            embed=embed(
                "🙋 Ticket reclamado",
                (
                    f"Este ticket está siendo atendido por "
                    f"{interaction.user.mention}.\n\n"
                    "El miembro del staff que ha reclamado "
                    "el ticket queda registrado."
                ),
                discord.Color.green()
            )
        )

        await send_log(
            interaction.guild,
            "🙋 Ticket reclamado",
            (
                f"**Ticket:** {interaction.chan
