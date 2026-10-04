import os
import io
import re
import sqlite3
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands


# ============================================================
# CONFIGURACIÓN
# ============================================================

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


# ============================================================
# VERIFICACIÓN
# ============================================================

VERIFICATION_CHANNEL_ID = 1555632348907708508
MEMBER_ROLE_ID = 1556321345145667708


# ============================================================
# BASE DE DATOS
# ============================================================

db = sqlite3.connect("corruption_network.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    user_id INTEGER,
    ticket_type TEXT,
    claimed_by INTEGER,
    created_at TEXT,
    closed_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    staff_id INTEGER,
    user_id INTEGER,
    rating INTEGER,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    created_at TEXT
)
""")

db.commit()


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def now():
    return datetime.now(timezone.utc)


def is_staff(member: discord.Member):

    if member.guild_permissions.administrator:
        return True

    if STAFF_ROLE_ID:
        if any(
            role.id == STAFF_ROLE_ID
            for role in member.roles
        ):
            return True

    if ADMIN_ROLE_ID:
        if any(
            role.id == ADMIN_ROLE_ID
            for role in member.roles
        ):
            return True

    return False


def is_admin(member: discord.Member):

    if member.guild_permissions.administrator:
        return True

    if ADMIN_ROLE_ID:
        if any(
            role.id == ADMIN_ROLE_ID
            for role in member.roles
        ):
            return True

    return False


async def send_log(message):

    if not LOG_CHANNEL_ID:
        return

    channel = bot.get_channel(
        LOG_CHANNEL_ID
    )

    if channel:

        try:
            await channel.send(message)
        except Exception:
            pass


# ============================================================
# VERIFICACIÓN
# ============================================================

class VerificationView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Verificarme",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="corruption_verify"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ No se ha encontrado el servidor.",
                ephemeral=True
            )

            return

        try:

            member = await guild.fetch_member(
                interaction.user.id
            )

        except Exception:

            await interaction.response.send_message(
                "❌ No se ha podido encontrar tu usuario.",
                ephemeral=True
            )

            return

        role = guild.get_role(
            MEMBER_ROLE_ID
        )

        if not role:

            await interaction.response.send_message(
                "❌ No encuentro el rol **Miembro**.",
                ephemeral=True
            )

            return

        if role in member.roles:

            await interaction.response.send_message(
                "✅ Ya estás verificado.",
                ephemeral=True
            )

            return

        try:

            await member.add_roles(
                role,
                reason="Verificación mediante botón"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No puedo darte el rol **Miembro**.\n\n"
                "Asegúrate de que el rol del bot esté "
                "**por encima del rol Miembro**.",
                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"Error dando rol de verificación: {e}"
            )

            await interaction.response.send_message(
                "❌ Ha ocurrido un error al verificarte.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🎉 **¡Verificación completada!**\n\n"
            "Ya tienes el rol **Miembro** y puedes acceder "
            "a las zonas correspondientes del servidor.",
            ephemeral=True
        )

        await send_log(
            f"✅ **Usuario verificado**\n"
            f"Usuario: {member.mention}\n"
            f"ID: `{member.id}`"
        )


async def send_verification_panel(channel):

    embed = discord.Embed(
        title="🛡️ Verificación — Corruption Network",
        description=(
            "Bienvenido a **Corruption Network**.\n\n"
            "Para acceder al servidor debes verificarte.\n\n"
            "Pulsa el botón **✅ Verificarme** "
            "y recibirás automáticamente el rol "
            "**Miembro**.\n\n"
            "⚡ Sin CAPTCHA y sin complicaciones."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="Corruption Network • Verificación"
    )

    await channel.send(
        embed=embed,
        view=VerificationView()
    )


# ============================================================
# ROLES JAVA / BEDROCK
# ============================================================

async def get_or_create_platform_roles(guild):

    java_role = discord.utils.get(
        guild.roles,
        name="JAVA"
    )

    bedrock_role = discord.utils.get(
        guild.roles,
        name="BEDROCK"
    )

    if not java_role:

        java_role = await guild.create_role(
            name="JAVA",
            reason="Rol de plataforma Corruption Network"
        )

    if not bedrock_role:

        bedrock_role = await guild.create_role(
            name="BEDROCK",
            reason="Rol de plataforma Corruption Network"
        )

    return java_role, bedrock_role


class PlatformView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    async def give_platform_role(
        self,
        interaction,
        platform
    ):

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ No se ha encontrado el servidor.",
                ephemeral=True
            )

            return

        java_role, bedrock_role = (
            await get_or_create_platform_roles(guild)
        )

        if platform == "JAVA":

            selected_role = java_role
            other_role = bedrock_role
            emoji = "☕"

        else:

            selected_role = bedrock_role
            other_role = java_role
            emoji = "📱"

        try:

            if other_role in interaction.user.roles:

                await interaction.user.remove_roles(
                    other_role,
                    reason="Cambio de plataforma"
                )

            if selected_role in interaction.user.roles:

                await interaction.response.send_message(
                    f"✅ Ya tienes el rol **{platform}**.",
                    ephemeral=True
                )

                return

            await interaction.user.add_roles(
                selected_role,
                reason=f"Selección de plataforma {platform}"
            )

            await interaction.response.send_message(
                f"{emoji} Has seleccionado **{platform}** correctamente.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No puedo asignar el rol.\n\n"
                "Pon los roles **JAVA** y **BEDROCK** "
                "por debajo del rol del bot.",
                ephemeral=True
            )

        except Exception as e:

            print(
                f"Error asignando plataforma: {e}"
            )

            await interaction.response.send_message(
                "❌ Ha ocurrido un error.",
                ephemeral=True
            )


    @discord.ui.button(
        label="JAVA",
        emoji="☕",
        style=discord.ButtonStyle.primary,
        custom_id="platform_java"
    )
    async def java(
        self,
        interaction,
        button
    ):

        await self.give_platform_role(
            interaction,
            "JAVA"
        )


    @discord.ui.button(
        label="BEDROCK",
        emoji="📱",
        style=discord.ButtonStyle.success,
        custom_id="platform_bedrock"
    )
    async def bedrock(
        self,
        interaction,
        button
    ):

        await self.give_platform_role(
            interaction,
            "BEDROCK"
        )


# ============================================================
# TICKETS
# ============================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, ticket_type):

        super().__init__(
            title=f"Ticket — {ticket_type}"
        )

        self.ticket_type = ticket_type

        self.reason = discord.ui.TextInput(
            label="Explica tu problema",
            placeholder="Describe detalladamente lo que necesitas...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.add_item(
            self.reason
        )

    async def on_submit(
        self,
        interaction
    ):

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ No se ha encontrado el servidor.",
                ephemeral=True
            )

            return

        category = None

        if TICKET_CATEGORY_ID:

            category = guild.get_channel(
                TICKET_CATEGORY_ID
            )

        if not category:

            await interaction.response.send_message(
                "❌ La categoría de tickets no está configurada.",
                ephemeral=True
            )

            return

        safe_name = re.sub(
            r"[^a-zA-Z0-9-]",
            "-",
            interaction.user.name.lower()
        )

        channel_name = (
            f"ticket-{safe_name}"
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
                    attach_files=True
                )
        }

        if STAFF_ROLE_ID:

            staff_role = guild.get_role(
                STAFF_ROLE_ID
            )

            if staff_role:

                overwrites[staff_role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=True
                    )
                )

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket de {interaction.user}"
        )

        cursor.execute(
            """
            INSERT INTO tickets
            (channel_id, user_id, ticket_type,
             claimed_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                channel.id,
                interaction.user.id,
                self.ticket_type,
                None,
                now().isoformat()
            )
        )

        db.commit()

        ticket_id = cursor.lastrowid

        embed = discord.Embed(
            title=f"🎫 Ticket — {self.ticket_type}",
            description=(
                f"Bienvenido {interaction.user.mention}.\n\n"
                f"**Motivo:**\n"
                f"{self.reason.value}\n\n"
                "Un miembro del equipo atenderá "
                "tu ticket lo antes posible."
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Ticket #{ticket_id}"
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

        await send_log(
            f"🎫 **Nuevo ticket**\n"
            f"Usuario: {interaction.user.mention}\n"
            f"Tipo: **{self.ticket_type}**\n"
            f"Canal: {channel.mention}"
        )


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    async def create_ticket(
        self,
        interaction,
        ticket_type
    ):

        await interaction.response.send_modal(
            TicketModal(ticket_type)
        )

    @discord.ui.button(
        label="Soporte",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="ticket_support"
    )
    async def support(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "Soporte"
        )

    @discord.ui.button(
        label="Bug",
        style=discord.ButtonStyle.danger,
        emoji="🐛",
        custom_id="ticket_bug"
    )
    async def bug(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "Bug"
        )

    @discord.ui.button(
        label="Reportar usuario",
        style=discord.ButtonStyle.danger,
        emoji="🚨",
        custom_id="ticket_report"
    )
    async def report(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "Reportar usuario"
        )

    @discord.ui.button(
        label="Estafa",
        style=discord.ButtonStyle.danger,
        emoji="💰",
        custom_id="ticket_scam"
    )
    async def scam(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "Estafa"
        )

    @discord.ui.button(
        label="Postulación",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="ticket_application"
    )
    async def application(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "Postulación"
        )


class AddUserModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(
            title="Añadir usuario"
        )

        self.user_id = discord.ui.TextInput(
            label="ID del usuario",
            placeholder="123456789012345678",
            required=True
        )

        self.add_item(
            self.user_id
        )

    async def on_submit(
        self,
        interaction
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permiso.",
                ephemeral=True
            )

            return

        try:

            user_id = int(
                self.user_id.value.strip()
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ ID inválida.",
                ephemeral=True
            )

            return

        try:

            member = await interaction.guild.fetch_member(
                user_id
            )

        except Exception:

            await interaction.response.send_message(
                "❌ No he encontrado ese usuario.",
                ephemeral=True
            )

            return

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

        await interaction.response.send_message(
            f"✅ {member.mention} ha sido añadido al ticket."
        )


class CloseConfirmView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=60
        )

    @discord.ui.button(
        label="Confirmar cierre",
        style=discord.ButtonStyle.danger,
        emoji="🔒"
    )
    async def confirm(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permiso.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        await close_ticket(
            interaction.channel,
            interaction.user
        )

        await interaction.followup.send(
            "🔒 Ticket cerrado.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Cancelar",
        style=discord.ButtonStyle.secondary,
        emoji="❌"
    )
    async def cancel(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content="❌ Cierre cancelado.",
            view=None
        )


class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Reclamar",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="ticket_claim"
    )
    async def claim(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permiso.",
                ephemeral=True
            )

            return

        cursor.execute(
            """
            SELECT claimed_by
            FROM tickets
            WHERE channel_id = ?
            """,
            (
                interaction.channel.id,
            )
        )

        result = cursor.fetchone()

        if not result:

            await interaction.response.send_message(
                "❌ No se ha encontrado el ticket.",
                ephemeral=True
            )

            return

        if result[0]:

            await interaction.response.send_message(
                "⚠️ Este ticket ya ha sido reclamado.",
                ephemeral=True
            )

            return

        cursor.execute(
            """
            UPDATE tickets
            SET claimed_by = ?
            WHERE channel_id = ?
            """,
            (
                interaction.user.id,
                interaction.channel.id
            )
        )

        db.commit()

        await interaction.response.send_message(
            f"🙋 {interaction.user.mention} ha reclamado este ticket."
        )

        await send_log(
            f"🙋 **Ticket reclamado**\n"
            f"Staff: {interaction.user.mention}\n"
            f"Canal: {interaction.channel.mention}"
        )

    @discord.ui.button(
        label="Añadir usuario",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="ticket_add"
    )
    async def add_user(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permiso.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            AddUserModal()
        )

    @discord.ui.button(
        label="Cerrar",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_close"
    )
    async def close(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permiso.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "¿Seguro que quieres cerrar este ticket?",
            view=CloseConfirmView(),
            ephemeral=True
        )


async def generate_transcript(channel):

    messages = []

    try:

        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):

            content = message.content.replace(
                "\n",
                " "
            )

            messages.append(
                f"[{message.created_at}] "
                f"{message.author}: "
                f"{content}"
            )

    except Exception as e:

        messages.append(
            f"Error generando transcript: {e}"
        )

    return "\n".join(messages)


async def close_ticket(
    channel,
    closed_by
):

    cursor.execute(
        """
        SELECT id, user_id, claimed_by
        FROM tickets
        WHERE channel_id = ?
        """,
        (
            channel.id,
        )
    )

    ticket = cursor.fetchone()

    if not ticket:
        return

    ticket_id = ticket[0]
    user_id = ticket[1]
    claimed_by = ticket[2]

    transcript = await generate_transcript(
        channel
    )

    transcript_file = discord.File(
        io.BytesIO(
            transcript.encode("utf-8")
        ),
        filename=f"ticket-{ticket_id}.txt"
    )

    cursor.execute(
        """
        UPDATE tickets
        SET closed_at = ?
        WHERE channel_id = ?
        """,
        (
            now().isoformat(),
            channel.id
        )
    )

    db.commit()

    if TRANSCRIPT_CHANNEL_ID:

        transcript_channel = bot.get_channel(
            TRANSCRIPT_CHANNEL_ID
        )

        if transcript_channel:

            try:

                await transcript_channel.send(
                    content=(
                        f"📁 **Ticket cerrado**\n"
                        f"Ticket: `#{ticket_id}`\n"
                        f"Cerrado por: {closed_by.mention}"
                    ),
                    file=transcript_file
                )

            except Exception:
                pass

    if RATINGS_CHANNEL_ID and claimed_by:

        rating_channel = bot.get_channel(
            RATINGS_CHANNEL_ID
        )

        if rating_channel:

            try:

                user = await bot.fetch_user(
                    user_id
                )

                await rating_channel.send(
                    f"⭐ {user.mention}, valora la atención recibida:",
                    view=RatingView(
                        ticket_id,
                        claimed_by,
                        user_id
                    )
                )

            except Exception:
                pass

    await send_log(
        f"🔒 **Ticket cerrado**\n"
        f"Ticket: `#{ticket_id}`\n"
        f"Cerrado por: {closed_by.mention}"
    )

    await asyncio.sleep(3)

    try:

        await channel.delete(
            reason="Ticket cerrado"
        )

    except Exception:
        pass


class RatingView(discord.ui.View):

    def __init__(
        self,
        ticket_id,
        staff_id,
        user_id
    ):

        super().__init__(
            timeout=86400
        )

        self.ticket_id = ticket_id
        self.staff_id = staff_id
        self.user_id = user_id

        for rating in range(1, 6):

            button = discord.ui.Button(
                label="⭐" * rating,
                style=discord.ButtonStyle.secondary
            )

            async def callback(
                interaction,
                value=rating
            ):

                if interaction.user.id != self.user_id:

                    await interaction.response.send_message(
                        "❌ Esta valoración no es para ti.",
                        ephemeral=True
                    )

                    return

                cursor.execute(
                    """
                    INSERT INTO ratings
                    (ticket_id, staff_id, user_id,
                     rating, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        self.ticket_id,
                        self.staff_id,
                        self.user_id,
                        value,
                        now().isoformat()
                    )
                )

                db.commit()

                await interaction.response.edit_message(
                    content=(
                        f"⭐ Gracias por valorar la atención "
                        f"con **{value}/5**."
                    ),
                    view=None
                )

            button.callback = callback

            self.add_item(
                button
            )


# ============================================================
# ADMINISTRACIÓN
# ============================================================

@bot.tree.command(
    name="kick",
    description="Expulsa a un usuario."
)
@app_commands.describe(
    member="Usuario",
    reason="Motivo"
)
async def kick(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    try:

        await member.kick(
            reason=reason
        )

        await interaction.response.send_message(
            f"🔴 {member.mention} ha sido expulsado.\n"
            f"**Motivo:** {reason}"
        )

    except Exception:

        await interaction.response.send_message(
            "❌ No puedo expulsar a ese usuario.",
            ephemeral=True
        )


@bot.tree.command(
    name="ban",
    description="Banea a un usuario."
)
@app_commands.describe(
    member="Usuario",
    reason="Motivo"
)
async def ban(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    try:

        await member.ban(
            reason=reason
        )

        await interaction.response.send_message(
            f"⛔ {member.mention} ha sido baneado.\n"
            f"**Motivo:** {reason}"
        )

    except Exception:

        await interaction.response.send_message(
            "❌ No puedo banear a ese usuario.",
            ephemeral=True
        )


@bot.tree.command(
    name="unban",
    description="Desbanea a un usuario mediante ID."
)
async def unban(
    interaction,
    user_id: str
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    try:

        user = await bot.fetch_user(
            int(user_id)
        )

        await interaction.guild.unban(
            user
        )

        await interaction.response.send_message(
            f"✅ {user} ha sido desbaneado."
        )

    except Exception:

        await interaction.response.send_message(
            "❌ No se ha podido desbanear.",
            ephemeral=True
        )


@bot.tree.command(
    name="timeout",
    description="Aplica un timeout."
)
@app_commands.describe(
    member="Usuario",
    minutes="Minutos",
    reason="Motivo"
)
async def timeout(
    interaction,
    member: discord.Member,
    minutes: int,
    reason: str = "Sin motivo"
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    if minutes < 1:
        minutes = 1

    if minutes > 40320:
        minutes = 40320

    try:

        await member.timeout(
            now() + discord.utils.timedelta(
                minutes=minutes
            ),
            reason=reason
        )

        await interaction.response.send_message(
            f"🔇 {member.mention} ha recibido "
            f"un timeout de **{minutes} minutos**.\n"
            f"**Motivo:** {reason}"
        )

    except Exception:

        await interaction.response.send_message(
            "❌ No se pudo aplicar el timeout.",
            ephemeral=True
        )


@bot.tree.command(
    name="untimeout",
    description="Quita el timeout."
)
async def untimeout(
    interaction,
    member: discord.Member
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    try:

        await member.timeout(
            None
        )

        await interaction.response.send_message(
            f"🔊 Timeout retirado a {member.mention}."
        )

    except Exception:

        await interaction.response.send_message(
            "❌ No se pudo quitar el timeout.",
            ephemeral=True
        )


@bot.tree.command(
    name="warn",
    description="Advierte a un usuario."
)
async def warn(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    cursor.execute(
        """
        INSERT INTO warnings
        (user_id, moderator_id, reason, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            member.id,
            interaction.user.id,
            reason,
            now().isoformat()
        )
    )

    db.commit()

    await interaction.response.send_message(
        f"⚠️ {member.mention} ha recibido una advertencia.\n"
        f"**Motivo:** {reason}"
    )


@bot.tree.command(
    name="warnings",
    description="Consulta las advertencias."
)
async def warnings(
    interaction,
    member: discord.Member
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    cursor.execute(
        """
        SELECT reason, moderator_id, created_at
        FROM warnings
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (
            member.id,
        )
    )

    results = cursor.fetchall()

    if not results:

        await interaction.response.send_message(
            f"✅ {member.mention} no tiene advertencias.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title=f"⚠️ Advertencias de {member}",
        color=discord.Color.orange()
    )

    for index, (
        reason,
        moderator_id,
        created_at
    ) in enumerate(results, 1):

        embed.add_field(
            name=f"Advertencia #{index}",
            value=(
                f"**Motivo:** {reason}\n"
                f"**Moderador:** <@{moderator_id}>\n"
                f"**Fecha:** {created_at}"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="clear",
    description="Borra mensajes."
)
async def clear(
    interaction,
    amount: int
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    amount = max(
        1,
        min(amount, 100)
    )

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await interaction.channel.purge(
        limit=amount
    )

    await interaction.followup.send(
        f"🧹 Se han eliminado **{len(deleted)} mensajes**.",
        ephemeral=True
    )


@bot.tree.command(
    name="lock",
    description="Bloquea el canal."
)
async def lock(
    interaction
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        send_messages=False
    )

    await interaction.response.send_message(
        "🔒 Canal bloqueado."
    )


@bot.tree.command(
    name="unlock",
    description="Desbloquea el canal."
)
async def unlock(
    interaction
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        send_messages=None
    )

    await interaction.response.send_message(
        "🔓 Canal desbloqueado."
    )


@bot.tree.command(
    name="slowmode",
    description="Configura el modo lento."
)
async def slowmode(
    interaction,
    seconds: int
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    seconds = max(
        0,
        min(seconds, 21600)
    )

    await interaction.channel.edit(
        slowmode_delay=seconds
    )

    await interaction.response.send_message(
        f"🐌 Slowmode configurado a **{seconds}s**."
    )


@bot.tree.command(
    name="userinfo",
    description="Muestra información de un usuario."
)
async def userinfo(
    interaction,
    member: discord.Member
):

    embed = discord.Embed(
        title=f"👤 Información de {member}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=False
    )

    embed.add_field(
        name="Cuenta creada",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="serverinfo",
    description="Muestra información del servidor."
)
async def serverinfo(
    interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🌐 {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ID",
        value=str(guild.id)
    )

    embed.add_field(
        name="Miembros",
        value=str(guild.member_count)
    )

    embed.add_field(
        name="Canales",
        value=str(len(guild.channels))
    )

    if guild.icon:

        embed.set_thumbnail(
            url=guild.icon.url
        )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# COMANDO VERIFICACIÓN
# ============================================================

@bot.tree.command(
    name="verificacion",
    description="Envía el panel de verificación."
)
async def verificacion(
    interaction
):

    if interaction.channel.id != VERIFICATION_CHANNEL_ID:

        await interaction.response.send_message(
            "❌ Este comando solo puede utilizarse "
            "en el canal de verificación.",
            ephemeral=True
        )

        return

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    await send_verification_panel(
        interaction.channel
    )

    await interaction.response.send_message(
        "✅ Panel de verificación enviado.",
        ephemeral=True
    )


# ============================================================
# COMANDO TICKETS
# ============================================================

@bot.tree.command(
    name="ticketpanel",
    description="Envía el panel de tickets."
)
async def ticketpanel(
    interaction
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    if (
        TICKET_PANEL_CHANNEL_ID
        and interaction.channel.id != TICKET_PANEL_CHANNEL_ID
    ):

        await interaction.response.send_message(
            "❌ Este comando solo puede utilizarse "
            "en el canal configurado.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🎫 Centro de soporte — Corruption Network",
        description=(
            "¿Necesitas ayuda?\n\n"
            "Selecciona el tipo de ticket que necesitas:\n\n"
            "🎫 **Soporte**\n"
            "🐛 **Bug**\n"
            "🚨 **Reportar usuario**\n"
            "💰 **Estafa**\n"
            "📝 **Postulación**"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Corruption Network • Soporte"
    )

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "✅ Panel de tickets enviado.",
        ephemeral=True
    )


# ============================================================
# COMANDO PLATAFORMAS
# ============================================================

@bot.tree.command(
    name="plataformas",
    description="Crea los roles JAVA y BEDROCK y publica el panel."
)
async def plataformas(
    interaction
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    java_role, bedrock_role = (
        await get_or_create_platform_roles(
            interaction.guild
        )
    )

    embed = discord.Embed(
        title="🎮 Selecciona tu plataforma",
        description=(
            "Selecciona desde qué plataforma juegas "
            "en **Corruption Network**.\n\n"
            "☕ **JAVA**\n"
            "Pulsa el botón para recibir el rol `JAVA`.\n\n"
            "📱 **BEDROCK**\n"
            "Pulsa el botón para recibir el rol `BEDROCK`.\n\n"
            "⚠️ Solo puedes tener una plataforma."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Corruption Network • Plataformas"
    )

    await interaction.channel.send(
        embed=embed,
        view=PlatformView()
    )

    await interaction.response.send_message(
        "✅ Panel de plataformas creado.",
        ephemeral=True
    )


# ============================================================
# ESTADÍSTICAS STAFF
# ============================================================

@bot.tree.command(
    name="staffstats",
    description="Muestra las estadísticas de un staff."
)
async def staffstats(
    interaction,
    member: discord.Member
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos.",
            ephemeral=True
        )

        return

    cursor.execute(
        """
        SELECT COUNT(*), AVG(rating)
        FROM ratings
        WHERE staff_id = ?
        """,
        (
            member.id,
        )
    )

    count, average = cursor.fetchone()

    if not count:

        await interaction.response.send_message(
            f"📊 {member.mention} todavía no tiene valoraciones.",
            ephemeral=True
        )

        return

    average = round(
        average,
        2
    )

    embed = discord.Embed(
        title="📊 Estadísticas del Staff",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="Staff",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="Valoraciones",
        value=str(count)
    )

    embed.add_field(
        name="Media",
        value=f"⭐ {average}/5"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print(
        f"✅ Bot conectado como {bot.user}"
    )

    # Botones persistentes
    bot.add_view(
        VerificationView()
    )

    bot.add_view(
        PlatformView()
    )

    bot.add_view(
        TicketPanelView()
    )

    bot.add_view(
        TicketControlView()
    )

    try:

        if GUILD_ID:

            guild = discord.Object(
                id=GUILD_ID
            )

            bot.tree.copy_global_to(
                guild=guild
            )

            synced = await bot.tree.sync(
                guild=guild
            )

            print(
                f"✅ {len(synced)} comandos sincronizados."
            )

        else:

            synced = await bot.tree.sync()

            print(
                f"✅ {len(synced)} comandos globales sincronizados."
            )

    except Exception as e:

        print(
            f"❌ Error sincronizando comandos: {e}"
        )


# ============================================================
# ARRANQUE
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta DISCORD_TOKEN en Railway."
    )

bot.run(
    TOKEN
)
