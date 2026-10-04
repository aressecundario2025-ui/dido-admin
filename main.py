import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))

TICKET_PANEL_CHANNEL_ID = int(
    os.getenv("TICKET_PANEL_CHANNEL_ID", "0")
)

TICKET_CATEGORY_ID = int(
    os.getenv("TICKET_CATEGORY_ID", "0")
)

LOG_CHANNEL_ID = int(
    os.getenv("LOG_CHANNEL_ID", "0")
)

RATINGS_CHANNEL_ID = int(
    os.getenv("RATINGS_CHANNEL_ID", "0")
)

TRANSCRIPT_CHANNEL_ID = int(
    os.getenv("TRANSCRIPT_CHANNEL_ID", "0")
)

STAFF_ROLE_ID = int(
    os.getenv("STAFF_ROLE_ID", "0")
)

ADMIN_ROLE_ID = int(
    os.getenv("ADMIN_ROLE_ID", "0")
)


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True


# =========================================================
# BOT
# =========================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATABASE
# =========================================================

DB_FILE = "corruption_network.db"


def db_connection():
    return sqlite3.connect(DB_FILE)


def init_database():
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            staff_id INTEGER,
            created_at TEXT NOT NULL,
            closed_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            ticket_channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# COLORES
# =========================================================

COLOR_MAIN = discord.Color.from_rgb(150, 0, 0)
COLOR_SUCCESS = discord.Color.green()
COLOR_ERROR = discord.Color.red()
COLOR_WARNING = discord.Color.orange()
COLOR_INFO = discord.Color.blurple()


# =========================================================
# UTILIDADES
# =========================================================

def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def has_staff_role(member: discord.Member) -> bool:
    if STAFF_ROLE_ID == 0:
        return False

    return any(
        role.id == STAFF_ROLE_ID
        for role in member.roles
    )


def has_admin_role(member: discord.Member) -> bool:
    if ADMIN_ROLE_ID == 0:
        return False

    return any(
        role.id == ADMIN_ROLE_ID
        for role in member.roles
    )


def is_staff_or_admin(member: discord.Member) -> bool:
    return (
        has_staff_role(member)
        or has_admin_role(member)
        or member.guild_permissions.administrator
    )


async def send_log(guild: discord.Guild, embed: discord.Embed):
    if LOG_CHANNEL_ID == 0:
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)

    if channel is None:
        return

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass


def get_open_ticket(user_id: int, guild_id: int):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT channel_id
        FROM tickets
        WHERE user_id = ?
        AND guild_id = ?
        AND closed_at IS NULL
    """, (user_id, guild_id))

    result = cursor.fetchone()

    conn.close()

    return result[0] if result else None


def get_ticket(channel_id: int):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT channel_id, guild_id, user_id, category,
               staff_id, created_at, closed_at
        FROM tickets
        WHERE channel_id = ?
    """, (channel_id,))

    result = cursor.fetchone()

    conn.close()

    return result


def set_ticket_staff(channel_id: int, staff_id: int):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET staff_id = ?
        WHERE channel_id = ?
    """, (staff_id, channel_id))

    conn.commit()
    conn.close()


def close_ticket_database(channel_id: int):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET closed_at = ?
        WHERE channel_id = ?
    """, (now(), channel_id))

    conn.commit()
    conn.close()


def create_ticket_database(
    channel_id: int,
    guild_id: int,
    user_id: int,
    category: str
):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO tickets
        (
            channel_id,
            guild_id,
            user_id,
            category,
            staff_id,
            created_at,
            closed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        channel_id,
        guild_id,
        user_id,
        category,
        None,
        now(),
        None
    ))

    conn.commit()
    conn.close()


# =========================================================
# TRANSCRIPCIÓN
# =========================================================

async def create_transcript(
    channel: discord.TextChannel
):
    messages = []

    try:
        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):
            timestamp = message.created_at.strftime(
                "%d/%m/%Y %H:%M:%S"
            )

            content = message.content

            if not content:
                content = "[Sin contenido]"

            attachments = ""

            if message.attachments:
                attachments = " | Adjuntos: " + ", ".join(
                    attachment.url
                    for attachment in message.attachments
                )

            messages.append(
                f"[{timestamp}] "
                f"{message.author} ({message.author.id}): "
                f"{content}{attachments}"
            )

    except discord.Forbidden:
        return None

    transcript = "\n".join(messages)

    if not transcript:
        transcript = "No hay mensajes."

    filename = f"transcript-{channel.id}.txt"

    with open(filename, "w", encoding="utf-8") as file:
        file.write(
            f"CORRUPTION NETWORK\n"
            f"TICKET: {channel.name}\n"
            f"CHANNEL ID: {channel.id}\n"
            f"{'=' * 70}\n\n"
        )

        file.write(transcript)

    return filename


# =========================================================
# PANEL DE TICKETS
# =========================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        category: str,
        emoji: str
    ):
        if interaction.guild is None:
            return

        existing = get_open_ticket(
            interaction.user.id,
            interaction.guild.id
        )

        if existing:
            channel = interaction.guild.get_channel(existing)

            if channel:
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return

        if TICKET_CATEGORY_ID == 0:
            await interaction.response.send_message(
                "❌ El sistema de tickets todavía no está configurado.",
                ephemeral=True
            )
            return

        category_channel = interaction.guild.get_channel(
            TICKET_CATEGORY_ID
        )

        if not isinstance(
            category_channel,
            discord.CategoryChannel
        ):
            await interaction.response.send_message(
                "❌ La categoría de tickets configurada no es válida.",
                ephemeral=True
            )
            return

        modal = TicketModal(
            category,
            emoji
        )

        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Soporte",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="cn_ticket_support"
    )
    async def support(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(
            interaction,
            "Soporte",
            "🎫"
        )

    @discord.ui.button(
        label="Reportar bug",
        emoji="🐛",
        style=discord.ButtonStyle.success,
        custom_id="cn_ticket_bug"
    )
    async def bug(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(
            interaction,
            "Bug",
            "🐛"
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="cn_ticket_report"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(
            interaction,
            "Reporte",
            "🚨"
        )

    @discord.ui.button(
        label="Estafa",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="cn_ticket_scam"
    )
    async def scam(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(
            interaction,
            "Estafa",
            "💰"
        )

    @discord.ui.button(
        label="Postulación",
        emoji="📋",
        style=discord.ButtonStyle.secondary,
        custom_id="cn_ticket_application"
    )
    async def application(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(
            interaction,
            "Postulación",
            "📋"
        )


# =========================================================
# MODAL DE CREACIÓN
# =========================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, category: str, emoji: str):
        super().__init__(
            title=f"{emoji} {category}"
        )

        self.category = category
        self.emoji = emoji

        self.reason = discord.ui.TextInput(
            label="Explícanos tu situación",
            placeholder="Escribe aquí todos los detalles...",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=5,
            max_length=1500
        )

        self.add_item(self.reason)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        guild = interaction.guild

        if guild is None:
            return

        existing = get_open_ticket(
            interaction.user.id,
            guild.id
        )

        if existing:
            channel = guild.get_channel(existing)

            if channel:
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return

        category_channel = guild.get_channel(
            TICKET_CATEGORY_ID
        )

        if not isinstance(
            category_channel,
            discord.CategoryChannel
        ):
            await interaction.response.send_message(
                "❌ La categoría de tickets no está configurada.",
                ephemeral=True
            )
            return

        bot_member = guild.me

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
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        if STAFF_ROLE_ID != 0:
            staff_role = guild.get_role(STAFF_ROLE_ID)

            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

        if ADMIN_ROLE_ID != 0:
            admin_role = guild.get_role(ADMIN_ROLE_ID)

            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True
                )

        safe_name = interaction.user.name.lower()

        safe_name = "".join(
            character
            for character in safe_name
            if character.isalnum() or character in "-_"
        )

        if not safe_name:
            safe_name = "usuario"

        channel_name = f"{self.category.lower()}-{safe_name}"

        if len(channel_name) > 90:
            channel_name = channel_name[:90]

        try:
            channel = await guild.create_text_channel(
                channel_name,
                category=category_channel,
                overwrites=overwrites,
                topic=(
                    f"Ticket de {interaction.user} | "
                    f"Categoría: {self.category}"
                )
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permisos para crear tickets.",
                ephemeral=True
            )
            return

        create_ticket_database(
            channel.id,
            guild.id,
            interaction.user.id,
            self.category
        )

        embed = discord.Embed(
            title=f"{self.emoji} Ticket de {self.category}",
            description=(
                f"Hola {interaction.user.mention}.\n\n"
                "Un miembro del equipo atenderá tu solicitud "
                "lo antes posible.\n\n"
                f"**Motivo:**\n{self.reason.value}"
            ),
            color=COLOR_MAIN,
            timestamp=datetime.utcnow()
        )

        embed.set_footer(
            text="Corruption Network • Sistema de Tickets"
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketControlView()
        )

        await interaction.response.send_message(
            f"✅ Tu ticket ha sido creado: {channel.mention}",
            ephemeral=True
        )

        log_embed = discord.Embed(
            title="🎫 Ticket creado",
            color=COLOR_SUCCESS,
            timestamp=datetime.utcnow()
        )

        log_embed.add_field(
            name="Usuario",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=True
        )

        log_embed.add_field(
            name="Categoría",
            value=self.category,
            inline=True
        )

        log_embed.add_field(
            name="Canal",
            value=channel.mention,
            inline=True
        )

        await send_log(guild, log_embed)


# =========================================================
# VISTA DE CONTROL DEL TICKET
# =========================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Reclamar",
        emoji="🙋",
        style=discord.ButtonStyle.primary,
        custom_id="cn_ticket_claim"
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None:
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not is_staff_or_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Solo el equipo de staff puede reclamar tickets.",
                ephemeral=True
            )
            return

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:
            await interaction.response.send_message(
                "❌ Este canal no está registrado como ticket.",
                ephemeral=True
            )
            return

        staff_id = ticket[4]

        if staff_id:
            staff = interaction.guild.get_member(staff_id)

            if staff:
                await interaction.response.send_message(
                    f"❌ Este ticket ya fue reclamado por "
                    f"{staff.mention}.",
                    ephemeral=True
                )
                return

        set_ticket_staff(
            interaction.channel.id,
            interaction.user.id
        )

        embed = discord.Embed(
            title="🙋 Ticket reclamado",
            description=(
                f"Este ticket será atendido por "
                f"{interaction.user.mention}."
            ),
            color=COLOR_SUCCESS,
            timestamp=datetime.utcnow()
        )

        await interaction.channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Has reclamado este ticket.",
            ephemeral=True
        )

        log_embed = discord.Embed(
            title="🙋 Ticket reclamado",
            color=COLOR_INFO,
            timestamp=datetime.utcnow()
        )

        log_embed.add_field(
            name="Staff",
            value=interaction.user.mention,
            inline=True
        )

        log_embed.add_field(
            name="Ticket",
            value=interaction.channel.mention,
            inline=True
        )

        await send_log(
            interaction.guild,
            log_embed
        )

    @discord.ui.button(
        label="Añadir usuario",
        emoji="➕",
        style=discord.ButtonStyle.secondary,
        custom_id="cn_ticket_add_user"
    )
    async def add_user(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None:
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not is_staff_or_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Solo el staff puede añadir usuarios.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            AddUserModal()
        )

    @discord.ui.button(
        label="Cerrar",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="cn_ticket_close"
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None:
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
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

        owner_id = ticket[2]
        staff_id = ticket[4]

        allowed = (
            interaction.user.id == owner_id
            or is_staff_or_admin(interaction.user)
            or interaction.user.id == staff_id
        )

        if not allowed:
            await interaction.response.send_message(
                "❌ No tienes permiso para cerrar este ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ ¿Seguro que quieres cerrar este ticket?",
            ephemeral=True,
            view=CloseConfirmationView()
        )


# =========================================================
# AÑADIR USUARIO
# =========================================================

class AddUserModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Añadir usuario al ticket"
        )

        self.user_id = discord.ui.TextInput(
            label="ID del usuario",
            placeholder="Ejemplo: 123456789012345678",
            required=True,
            min_length=17,
            max_length=20
        )

        self.add_item(self.user_id)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if interaction.guild is None:
            return

        try:
            user_id = int(self.user_id.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ El ID no es válido.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(
            user_id
        )

        if member is None:
            try:
                member = await interaction.guild.fetch_member(
                    user_id
                )
            except discord.NotFound:
                member = None

        if member is None:
            await interaction.response.send_message(
                "❌ No encuentro ese usuario en el servidor.",
                ephemeral=True
            )
            return

        try:
            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permisos para añadirlo.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ {member.mention} ha sido añadido al ticket."
        )


# =========================================================
# CONFIRMACIÓN DE CIERRE
# =========================================================

class CloseConfirmationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="Sí, cerrar",
        emoji="🔒",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None:
            return

        channel = interaction.channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return

        ticket = get_ticket(channel.id)

        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket no encontrado.",
                ephemeral=True
            )
            return

        owner_id = ticket[2]
        staff_id = ticket[4]

        filename = await create_transcript(
            channel
        )

        close_ticket_database(
            channel.id
        )

        if filename and TRANSCRIPT_CHANNEL_ID != 0:
            transcript_channel = interaction.guild.get_channel(
                TRANSCRIPT_CHANNEL_ID
            )

            if transcript_channel:
                try:
                    await transcript_channel.send(
                        content=(
                            f"📁 Transcripción de `{channel.name}`"
                        ),
                        file=discord.File(filename)
                    )
                except discord.HTTPException:
                    pass

        if filename:
            try:
                os.remove(filename)
            except OSError:
                pass

        if RATINGS_CHANNEL_ID != 0 and staff_id:
            rating_channel = interaction.guild.get_channel(
                RATINGS_CHANNEL_ID
            )

            if rating_channel:
                try:
                    await rating_channel.send(
                        content=(
                            f"<@{owner_id}> tu ticket ha sido cerrado.\n"
                            "⭐ Valora la atención recibida:"
                        ),
                        view=RatingView(
                            owner_id=owner_id,
                            staff_id=staff_id,
                            ticket_channel_id=channel.id
                        )
                    )
                except discord.HTTPException:
                    pass

        log_embed = discord.Embed(
            title="🔒 Ticket cerrado",
            color=COLOR_ERROR,
            timestamp=datetime.utcnow()
        )

        log_embed.add_field(
            name="Ticket",
            value=channel.name,
            inline=True
        )

        log_embed.add_field(
            name="Usuario",
            value=f"<@{owner_id}>",
            inline=True
        )

        if staff_id:
            log_embed.add_field(
                name="Staff",
                value=f"<@{staff_id}>",
                inline=True
            )

        await send_log(
            interaction.guild,
            log_embed
        )

        await interaction.response.send_message(
            "🔒 Cerrando ticket..."
        )

        await discord.utils.sleep_until(
            datetime.now()
        )

        try:
            await channel.delete(
                reason="Ticket cerrado"
            )
        except discord.HTTPException:
            pass

    @discord.ui.button(
        label="Cancelar",
        emoji="❌",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="❌ Cierre cancelado.",
            view=None
        )


# =========================================================
# VALORACIONES
# =========================================================

class RatingView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        staff_id: int,
        ticket_channel_id: int
    ):
        super().__init__(timeout=None)

        self.owner_id = owner_id
        self.staff_id = staff_id
        self.ticket_channel_id = ticket_channel_id

    async def register_rating(
        self,
        interaction: discord.Interaction,
        rating: int
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Esta valoración pertenece al usuario del ticket.",
                ephemeral=True
            )
            return

        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM ratings
            WHERE ticket_channel_id = ?
        """, (self.ticket_channel_id,))

        existing = cursor.fetchone()

        if existing:
            conn.close()

            await interaction.response.send_message(
                "❌ Este ticket ya ha sido valorado.",
                ephemeral=True
            )
            return

        cursor.execute("""
            INSERT INTO ratings
            (
                guild_id,
                ticket_channel_id,
                user_id,
                staff_id,
                rating,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.guild.id,
            self.ticket_channel_id,
            self.owner_id,
            self.staff_id,
            rating,
            "",
            now()
        ))

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"⭐ Gracias por valorar la atención con **{rating}/5**.",
            ephemeral=True
        )

        if interaction.channel:
            try:
                embed = discord.Embed(
                    title="⭐ Nueva valoración",
                    color=COLOR_SUCCESS,
                    timestamp=datetime.utcnow()
                )

                embed.add_field(
                    name="Usuario",
                    value=f"<@{self.owner_id}>",
                    inline=True
                )

                embed.add_field(
                    name="Staff",
                    value=f"<@{self.staff_id}>",
                    inline=True
                )

                embed.add_field(
                    name="Valoración",
                    value=f"{rating}/5",
                    inline=True
                )

                await interaction.channel.send(
                    embed=embed
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(
        label="1",
        style=discord.ButtonStyle.danger,
        custom_id="cn_rating_1"
    )
    async def rating_1(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.register_rating(
            interaction,
            1
        )

    @discord.ui.button(
        label="2",
        style=discord.ButtonStyle.danger,
        custom_id="cn_rating_2"
    )
    async def rating_2(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.register_rating(
            interaction,
            2
        )

    @discord.ui.button(
        label="3",
        style=discord.ButtonStyle.secondary,
        custom_id="cn_rating_3"
    )
    async def rating_3(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.register_rating(
            interaction,
            3
        )

    @discord.ui.button(
        label="4",
        style=discord.ButtonStyle.success,
        custom_id="cn_rating_4"
    )
    async def rating_4(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.register_rating(
            interaction,
            4
        )

    @discord.ui.button(
        label="5",
        style=discord.ButtonStyle.success,
        custom_id="cn_rating_5"
    )
    async def rating_5(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.register_rating(
            interaction,
            5
        )


# =========================================================
# EVENTO READY
# =========================================================

@bot.event
async def on_ready():
    print("=" * 60)
    print("CORRUPTION NETWORK BOT")
    print("=" * 60)
    print(f"Bot: {bot.user}")
    print(f"ID: {bot.user.id}")
    print("=" * 60)

    bot.add_view(
        TicketPanelView()
    )

    bot.add_view(
        TicketControlView()
    )

    if GUILD_ID:
        guild = discord.Object(
            id=GUILD_ID
        )

        try:
            synced = await bot.tree.sync(
                guild=guild
            )

            print(
                f"Comandos sincronizados: {len(synced)}"
            )
        except Exception as error:
            print(
                f"Error sincronizando comandos: {error}"
            )
    else:
        try:
            synced = await bot.tree.sync()

            print(
                f"Comandos globales sincronizados: {len(synced)}"
            )
        except Exception as error:
            print(
                f"Error sincronizando comandos globales: {error}"
            )

    print("Bot conectado correctamente.")


# =========================================================
# COMANDO TICKET PANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Envía el panel profesional de tickets."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🎫 CORRUPTION NETWORK • SOPORTE",
        description=(
            "¿Necesitas ayuda?\n\n"
            "Selecciona la categoría que corresponda "
            "a tu solicitud utilizando los botones de abajo.\n\n"
            "🎫 **Soporte**\n"
            "Para dudas o problemas generales.\n\n"
            "🐛 **Reportar bug**\n"
            "Para informar de errores del servidor.\n\n"
            "🚨 **Reportar usuario**\n"
            "Para reportar comportamientos indebidos.\n\n"
            "💰 **Estafa**\n"
            "Para problemas relacionados con estafas.\n\n"
            "📋 **Postulación**\n"
            "Para solicitar formar parte del equipo."
        ),
        color=COLOR_MAIN,
        timestamp=datetime.utcnow()
    )

    embed.set_footer(
        text="Corruption Network • Atención al usuario"
    )

    if interaction.guild:
        embed.set_thumbnail(
            url=interaction.guild.icon.url
            if interaction.guild.icon
            else discord.Embed.Empty
        )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    await message.edit(
        view=TicketPanelView()
    )


# =========================================================
# BAN
# =========================================================

@bot.tree.command(
    name="ban",
    description="Banea a un usuario."
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "Sin especificar"
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ No puedes banearte a ti mismo.",
            ephemeral=True
        )
        return

    if interaction.guild:
        if (
            member.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            await interaction.response.send_message(
                "❌ No puedes moderar a un usuario con un rol igual o superior.",
                ephemeral=True
            )
            return

    try:
        await member.ban(
            reason=reason
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No puedo banear a ese usuario.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"🔨 {member.mention} ha sido baneado.\n"
        f"**Razón:** {reason}"
    )

    if interaction.guild:
        embed = discord.Embed(
            title="🔨 Usuario baneado",
            color=COLOR_ERROR,
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Usuario",
            value=f"{member} (`{member.id}`)",
            inline=False
        )

        embed.add_field(
            name="Moderador",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Razón",
            value=reason,
            inline=True
        )

        await send_log(
            interaction.guild,
            embed
        )


# =========================================================
# UNBAN
# =========================================================

@bot.tree.command(
    name="unban",
    description="Desbanea a un usuario mediante su ID."
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):
    try:
        user = await bot.fetch_user(
            int(user_id)
        )
    except (ValueError, discord.NotFound):
        await interaction.response.send_message(
            "❌ ID de usuario inválido.",
            ephemeral=True
        )
        return

    try:
        await interaction.guild.unban(
            user
        )
    except discord.NotFound:
        await interaction.response.send_message(
            "❌ Ese usuario no está baneado.",
            ephemeral=True
        )
        return
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No tengo permisos para quitar ese baneo.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"✅ **{user}** ha sido desbaneado."
    )


# =========================================================
# KICK
# =========================================================

@bot.tree.command(
    name="kick",
    description="Expulsa a un usuario."
)
@app_commands.checks.has_permissions(
    kick_members=True
)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "Sin especificar"
):
    if interaction.guild:
        if (
            member.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            await interaction.response.send_message(
                "❌ No puedes expulsar a ese usuario.",
                ephemeral=True
            )
            return

    try:
        await member.kick(
            reason=reason
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No puedo expulsar a ese usuario.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"👢 {member} ha sido expulsado.\n"
        f"**Razón:** {reason}"
    )


# =========================================================
# TIMEOUT
# =========================================================

@bot.tree.command(
    name="timeout",
    description="Silencia temporalmente a un usuario."
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutos: int,
    reason: str = "Sin especificar"
):
    if minutos < 1:
        await interaction.response.send_message(
            "❌ El tiempo debe ser de al menos 1 minuto.",
            ephemeral=True
        )
        return

    if minutos > 40320:
        await interaction.response.send_message(
            "❌ El máximo es 28 días.",
            ephemeral=True
        )
        return

    if interaction.guild:
        if (
            member.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            await interaction.response.send_message(
                "❌ No puedes aplicar timeout a ese usuario.",
                ephemeral=True
            )
            return

    try:
        await member.timeout(
            timedelta(minutes=minutos),
            reason=reason
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No puedo aplicar timeout a ese usuario.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"⏱️ {member.mention} ha recibido un timeout de "
        f"**{minutos} minutos**.\n"
        f"**Razón:** {reason}"
    )


# =========================================================
# UNTIMEOUT
# =========================================================

@bot.tree.command(
    name="untimeout",
    description="Quita el timeout a un usuario."
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):
    try:
        await member.timeout(
            None,
            reason=f"Timeout retirado por {interaction.user}"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No puedo quitar el timeout.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"✅ Timeout retirado a {member.mention}."
    )


# =========================================================
# CLEAR
# =========================================================

@bot.tree.command(
    name="clear",
    description="Elimina mensajes del canal."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clear(
    interaction: discord.Interaction,
    cantidad: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(
        ephemeral=True
    )

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        await interaction.followup.send(
            "❌ Este comando solo funciona en canales de texto.",
            ephemeral=True
        )
        return

    deleted = await interaction.channel.purge(
        limit=cantidad
    )

    await interaction.followup.send(
        f"🧹 Se han eliminado **{len(deleted)} mensajes**.",
        ephemeral=True
    )


# =========================================================
# WARN
# =========================================================

@bot.tree.command(
    name="warn",
    description="Añade una advertencia a un usuario."
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "Sin especificar"
):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO warnings
        (
            guild_id,
            user_id,
            moderator_id,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        interaction.guild.id,
        member.id,
        interaction.user.id,
        reason,
        now()
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"⚠️ {member.mention} ha recibido una advertencia.\n"
        f"**Razón:** {reason}"
    )


# =========================================================
# WARNINGS
# =========================================================

@bot.tree.command(
    name="warnings",
    description="Muestra las advertencias de un usuario."
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warnings(
    interaction: discord.Interaction,
    member: discord.Member
):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT moderator_id, reason, created_at
        FROM warnings
        WHERE guild_id = ?
        AND user_id = ?
        ORDER BY id DESC
    """, (
        interaction.guild.id,
        member.id
    ))

    rows = cursor.fetchall()

    conn.close()

    if not rows:
        await interaction.response.send_message(
            f"✅ {member.mention} no tiene advertencias.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"⚠️ Advertencias de {member}",
        color=COLOR_WARNING
    )

    for index, row in enumerate(rows, start=1):
        moderator_id, reason, created_at = row

        embed.add_field(
            name=f"Advertencia #{index}",
            value=(
                f"**Razón:** {reason}\n"
                f"**Moderador:** <@{moderator_id}>\n"
                f"**Fecha:** {created_at}"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# LOCK
# =========================================================

@bot.tree.command(
    name="lock",
    description="Bloquea el canal."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def lock(
    interaction: discord.Interaction
):
    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ Este comando solo funciona en canales de texto.",
            ephemeral=True
        )
        return

    await channel.set_permissions(
        interaction.guild.default_role,
        send_messages=False
    )

    await interaction.response.send_message(
        "🔒 Canal bloqueado."
    )


# =========================================================
# UNLOCK
# =========================================================

@bot.tree.command(
    name="unlock",
    description="Desbloquea el canal."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def unlock(
    interaction: discord.Interaction
):
    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ Este comando solo funciona en canales de texto.",
            ephemeral=True
        )
        return

    await channel.set_permissions(
        interaction.guild.default_role,
        send_messages=None
    )

    await interaction.response.send_message(
        "🔓 Canal desbloqueado."
    )


# =========================================================
# SLOWMODE
# =========================================================

@bot.tree.command(
    name="slowmode",
    description="Configura el modo lento del canal."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def slowmode(
    interaction: discord.Interaction,
    segundos: app_commands.Range[int, 0, 21600]
):
    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ Este comando solo funciona en canales de texto.",
            ephemeral=True
        )
        return

    await channel.edit(
        slowmode_delay=segundos
    )

    if segundos == 0:
        await interaction.response.send_message(
            "🐌 Modo lento desactivado."
        )
    else:
        await interaction.response.send_message(
            f"🐌 Modo lento configurado a **{segundos} segundos**."
        )


# =========================================================
# USERINFO
# =========================================================

@bot.tree.command(
    name="userinfo",
    description="Muestra información de un usuario."
)
async def userinfo(
    interaction: discord.Interaction,
    member: discord.Member
):
    embed = discord.Embed(
        title="👤 Información del usuario",
        color=COLOR_INFO
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Usuario",
        value=str(member),
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Mención",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="Cuenta creada",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    if member.joined_at:
        embed.add_field(
            name="Entró al servidor",
            value=discord.utils.format_dt(
                member.joined_at,
                style="F"
            ),
            inline=False
        )

    roles = [
        role.mention
        for role in member.roles
        if role != interaction.guild.default_role
    ]

    embed.add_field(
        name="Roles",
        value=", ".join(roles)
        if roles
        else "Sin roles",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# SERVERINFO
# =========================================================

@bot.tree.command(
    name="serverinfo",
    description="Muestra información del servidor de Discord."
)
async def serverinfo(
    interaction: discord.Interaction
):
    guild = interaction.guild

    if guild is None:
        return

    embed = discord.Embed(
        title=f"🏠 {guild.name}",
        color=COLOR_MAIN
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="ID",
        value=str(guild.id),
        inline=True
    )

    embed.add_field(
        name="Miembros",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="Canales",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="Creado",
        value=discord.utils.format_dt(
            guild.created_at,
            style="F"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# STAFF STATS
# =========================================================

@bot.tree.command(
    name="staffstats",
    description="Muestra las estadísticas de atención de un miembro del staff."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def staffstats(
    interaction: discord.Interaction,
    member: discord.Member
):
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*), AVG(rating)
        FROM ratings
        WHERE guild_id = ?
        AND staff_id = ?
    """, (
        interaction.guild.id,
        member.id
    ))

    total, average = cursor.fetchone()

    conn.close()

    total = total or 0
    average = average or 0

    embed = discord.Embed(
        title="📊 Estadísticas del Staff",
        color=COLOR_INFO
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Staff",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="Valoraciones",
        value=str(total),
        inline=True
    )

    embed.add_field(
        name="Media",
        value=f"{average:.2f}/5",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# MANEJO DE ERRORES
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        message = (
            "❌ No tienes permisos para utilizar este comando."
        )

    elif isinstance(
        error,
        app_commands.errors.MissingRole
    ):
        message = (
            "❌ No tienes el rol necesario para utilizar este comando."
        )

    elif isinstance(
        error,
        app_commands.errors.CheckFailure
    ):
        message = (
            "❌ No tienes permisos para utilizar este comando."
        )

    else:
        print(
            f"ERROR DE COMANDO: {repr(error)}"
        )

        message = (
            "❌ Ha ocurrido un error al ejecutar el comando."
        )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )
    except discord.HTTPException:
        pass


# =========================================================
# ARRANQUE
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "Falta la variable DISCORD_TOKEN en Railway."
    )

bot.run(TOKEN)
