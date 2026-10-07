import os
import io
import re
import sqlite3
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta, timezone

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
# SERVIDOR HTTP PARA RENDER
# ============================================================

PORT = int(os.getenv("PORT", "10000"))


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(
            b"Corruption Network Discord Bot is online."
        )

    def log_message(self, format, *args):
        return


def start_web_server():
    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(f"🌐 Servidor HTTP iniciado en el puerto {PORT}")

    server.serve_forever()


web_thread = threading.Thread(
    target=start_web_server,
    daemon=True
)

web_thread.start()


# ============================================================
# BASE DE DATOS
# ============================================================

db = sqlite3.connect(
    "corruption_network.db",
    check_same_thread=False
)

cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ticket_type TEXT NOT NULL,
    claimed_by INTEGER DEFAULT NULL,
    created_at TEXT NOT NULL
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
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
# UTILIDADES
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


async def send_log(guild, message):

    if not LOG_CHANNEL_ID:
        return

    channel = guild.get_channel(
        LOG_CHANNEL_ID
    )

    if channel:
        try:
            await channel.send(message)
        except Exception:
            pass


def get_ticket(channel_id):

    cursor.execute(
        "SELECT * FROM tickets WHERE channel_id = ?",
        (channel_id,)
    )

    return cursor.fetchone()


# ============================================================
# VERIFICACIÓN
# ============================================================

class VerificationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

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

        if not interaction.guild:
            return

        role = interaction.guild.get_role(
            MEMBER_ROLE_ID
        )

        if role is None:
            await interaction.response.send_message(
                "❌ No encuentro el rol `Miembro`.",
                ephemeral=True
            )
            return

        member = interaction.user

        if role in member.roles:

            await interaction.response.send_message(
                "✅ Ya estás verificado.",
                ephemeral=True
            )

            return

        try:

            await member.add_roles(
                role,
                reason="Verificación Corruption Network"
            )

            await interaction.response.send_message(
                "✅ **Verificación completada.**\n"
                "Ya tienes acceso a los canales.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No puedo darte el rol `Miembro`.\n\n"
                "Comprueba que el rol del bot esté por encima "
                "de `Miembro`.",
                ephemeral=True
            )

        except Exception as e:

            print(
                "ERROR VERIFICACIÓN:",
                repr(e)
            )

            await interaction.response.send_message(
                "❌ Ha ocurrido un error al verificarte.",
                ephemeral=True
            )


@bot.tree.command(
    name="verificacion",
    description="Crear el panel de verificación"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def verificacion(
    interaction: discord.Interaction
):

    if interaction.channel_id != VERIFICATION_CHANNEL_ID:

        await interaction.response.send_message(
            f"❌ Este comando solo puede utilizarse en "
            f"<#{VERIFICATION_CHANNEL_ID}>.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🛡️ Verificación",
        description=(
            "**Bienvenido a Corruption Network.**\n\n"
            "Para acceder al servidor debes verificarte.\n\n"
            "Pulsa **✅ Verificarme** y recibirás "
            "automáticamente el rol **Miembro**.\n\n"
            "⚡ Verificación instantánea\n"
            "🔓 Acceso automático a los canales"
        ),
        color=discord.Color.red()
    )

    embed.set_footer(
        text="Corruption Network • Verificación"
    )

    await interaction.channel.send(
        embed=embed,
        view=VerificationView()
    )

    await interaction.response.send_message(
        "✅ Panel de verificación creado.",
        ephemeral=True
    )


# ============================================================
# PLATAFORMAS
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

    try:

        if java_role is None:

            java_role = await guild.create_role(
                name="JAVA",
                reason="Rol de plataforma Corruption Network"
            )

        if bedrock_role is None:

            bedrock_role = await guild.create_role(
                name="BEDROCK",
                reason="Rol de plataforma Corruption Network"
            )

    except discord.Forbidden:

        return None, None

    return java_role, bedrock_role


class PlatformView(discord.ui.View):

    def __init__(
        self,
        java_role_id,
        bedrock_role_id
    ):

        super().__init__(timeout=None)

        self.java_role_id = java_role_id
        self.bedrock_role_id = bedrock_role_id


    async def assign_platform(
        self,
        interaction,
        platform
    ):

        guild = interaction.guild

        if guild is None:
            return

        java_role = guild.get_role(
            self.java_role_id
        )

        bedrock_role = guild.get_role(
            self.bedrock_role_id
        )

        if java_role is None or bedrock_role is None:

            java_role, bedrock_role = (
                await get_or_create_platform_roles(guild)
            )

        if java_role is None or bedrock_role is None:

            await interaction.response.send_message(
                "❌ No puedo encontrar los roles.",
                ephemeral=True
            )

            return

        member = interaction.user

        try:

            if platform == "JAVA":

                if bedrock_role in member.roles:

                    await member.remove_roles(
                        bedrock_role,
                        reason="Cambio de plataforma"
                    )

                if java_role not in member.roles:

                    await member.add_roles(
                        java_role,
                        reason="Selección de plataforma JAVA"
                    )

                await interaction.response.send_message(
                    "☕ **Has seleccionado JAVA.**",
                    ephemeral=True
                )

            else:

                if java_role in member.roles:

                    await member.remove_roles(
                        java_role,
                        reason="Cambio de plataforma"
                    )

                if bedrock_role not in member.roles:

                    await member.add_roles(
                        bedrock_role,
                        reason="Selección de plataforma BEDROCK"
                    )

                await interaction.response.send_message(
                    "📱 **Has seleccionado BEDROCK.**",
                    ephemeral=True
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No puedo modificar los roles.\n\n"
                "Pon el rol del bot **por encima de JAVA y BEDROCK**.",
                ephemeral=True
            )

        except Exception as e:

            print(
                "ERROR PLATAFORMA:",
                repr(e)
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

        await self.assign_platform(
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

        await self.assign_platform(
            interaction,
            "BEDROCK"
        )


@bot.tree.command(
    name="plataformas",
    description="Crear el panel JAVA / BEDROCK"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def plataformas(
    interaction: discord.Interaction
):

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(
            "❌ Este comando solo funciona en un servidor.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    java_role, bedrock_role = (
        await get_or_create_platform_roles(guild)
    )

    if java_role is None or bedrock_role is None:

        await interaction.followup.send(
            "❌ No puedo crear los roles.\n"
            "Dale al bot el permiso **Gestionar roles**.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🌐 Selecciona tu plataforma",
        description=(
            "Selecciona la edición de Minecraft que utilizas.\n\n"
            "☕ **JAVA**\n"
            "Minecraft Java Edition.\n\n"
            "📱 **BEDROCK**\n"
            "Minecraft Bedrock Edition.\n\n"
            "⚠️ Solo puedes tener una plataforma."
        ),
        color=discord.Color.red()
    )

    embed.set_footer(
        text="Corruption Network • Plataformas"
    )

    await interaction.channel.send(
        embed=embed,
        view=PlatformView(
            java_role.id,
            bedrock_role.id
        )
    )

    await interaction.followup.send(
        "✅ Panel de plataformas creado.",
        ephemeral=True
    )


# ============================================================
# TICKETS
# ============================================================

TICKET_TYPES = {

    "soporte": {
        "name": "Soporte",
        "emoji": "🎫"
    },

    "bug": {
        "name": "Bug",
        "emoji": "🐛"
    },

    "reporte": {
        "name": "Reportar usuario",
        "emoji": "🚨"
    },

    "estafa": {
        "name": "Estafa",
        "emoji": "💰"
    },

    "postulacion": {
        "name": "Postulación",
        "emoji": "📝"
    }
}


class TicketReasonModal(discord.ui.Modal):

    def __init__(self, ticket_type):

        self.ticket_type = ticket_type

        super().__init__(
            title=(
                f"Ticket • "
                f"{TICKET_TYPES[ticket_type]['name']}"
            )
        )

        self.reason = discord.ui.TextInput(
            label="¿En qué podemos ayudarte?",
            placeholder="Explica brevemente el motivo...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.reason)


    async def on_submit(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:
            return

        category = guild.get_channel(
            TICKET_CATEGORY_ID
        )

        if category is None:

            await interaction.response.send_message(
                "❌ La categoría de tickets no existe.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        staff_role = guild.get_role(
            STAFF_ROLE_ID
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

        if staff_role:

            overwrites[staff_role] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True
                )
            )

        safe_name = re.sub(
            r"[^a-zA-Z0-9-]",
            "-",
            interaction.user.name.lower()
        )

        safe_name = safe_name[:20]

        channel_name = (
            f"{TICKET_TYPES[self.ticket_type]['emoji']}-"
            f"{safe_name}-ticket"
        )

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason="Creación de ticket"
        )

        cursor.execute(
            """
            INSERT INTO tickets
            (
                channel_id,
                user_id,
                ticket_type,
                claimed_by,
                created_at
            )
            VALUES (?, ?, ?, NULL, ?)
            """,
            (
                channel.id,
                interaction.user.id,
                self.ticket_type,
                now().isoformat()
            )
        )

        db.commit()

        embed = discord.Embed(
            title=(
                f"{TICKET_TYPES[self.ticket_type]['emoji']} "
                f"Ticket de "
                f"{TICKET_TYPES[self.ticket_type]['name']}"
            ),
            description=(
                f"Hola {interaction.user.mention} 👋\n\n"
                f"**Motivo:**\n"
                f"{self.reason.value}\n\n"
                "Un miembro del equipo atenderá tu ticket "
                "lo antes posible."
            ),
            color=discord.Color.red()
        )

        embed.set_footer(
            text="Corruption Network • Soporte"
        )

        staff_text = ""

        if staff_role:
            staff_text = staff_role.mention

        await channel.send(
            content=(
                f"{interaction.user.mention} "
                f"{staff_text}"
            ),
            embed=embed,
            view=TicketControlView()
        )

        await interaction.followup.send(
            f"✅ Ticket creado: {channel.mention}",
            ephemeral=True
        )


class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)


    async def open_ticket(
        self,
        interaction,
        ticket_type
    ):

        await interaction.response.send_modal(
            TicketReasonModal(ticket_type)
        )


    @discord.ui.button(
        label="Soporte",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_support"
    )
    async def soporte(
        self,
        interaction,
        button
    ):

        await self.open_ticket(
            interaction,
            "soporte"
        )


    @discord.ui.button(
        label="Bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_bug"
    )
    async def bug(
        self,
        interaction,
        button
    ):

        await self.open_ticket(
            interaction,
            "bug"
        )


    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_report"
    )
    async def reporte(
        self,
        interaction,
        button
    ):

        await self.open_ticket(
            interaction,
            "reporte"
        )


    @discord.ui.button(
        label="Estafa",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_scam"
    )
    async def estafa(
        self,
        interaction,
        button
    ):

        await self.open_ticket(
            interaction,
            "estafa"
        )


    @discord.ui.button(
        label="Postulación",
        emoji="📝",
        style=discord.ButtonStyle.success,
        custom_id="ticket_application"
    )
    async def postulacion(
        self,
        interaction,
        button
    ):

        await self.open_ticket(
            interaction,
            "postulacion"
        )


class AddUserModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(
            title="Añadir usuario al ticket"
        )

        self.user_id = discord.ui.TextInput(
            label="ID del usuario",
            placeholder="Ejemplo: 123456789012345678",
            required=True
        )

        self.add_item(self.user_id)


    async def on_submit(
        self,
        interaction
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

            return

        try:

            user_id = int(
                self.user_id.value
            )

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

            await interaction.response.send_message(
                "❌ No encuentro ese usuario.",
                ephemeral=True
            )

            return

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )

        await interaction.response.send_message(
            f"✅ {member.mention} ha sido añadido al ticket."
        )


class RatingView(discord.ui.View):

    def __init__(
        self,
        staff_id,
        user_id
    ):

        super().__init__(
            timeout=300
        )

        self.staff_id = staff_id
        self.user_id = user_id

        for rating in range(1, 6):

            button = discord.ui.Button(
                label=f"{rating} ⭐",
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
                    (
                        staff_id,
                        user_id,
                        rating,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        self.staff_id,
                        self.user_id,
                        value,
                        now().isoformat()
                    )
                )

                db.commit()

                ratings_channel = (
                    interaction.guild.get_channel(
                        RATINGS_CHANNEL_ID
                    )
                )

                if ratings_channel:

                    cursor.execute(
                        """
                        SELECT COUNT(*), AVG(rating)
                        FROM ratings
                        WHERE staff_id = ?
                        """,
                        (self.staff_id,)
                    )

                    count, average = cursor.fetchone()

                    staff = interaction.guild.get_member(
                        self.staff_id
                    )

                    staff_text = (
                        staff.mention
                        if staff
                        else f"<@{self.staff_id}>"
                    )

                    await ratings_channel.send(
                        f"⭐ **Nueva valoración**\n\n"
                        f"👤 Usuario: "
                        f"{interaction.user.mention}\n"
                        f"🛡️ Staff: {staff_text}\n"
                        f"⭐ Nota: **{value}/5**\n"
                        f"📊 Media: **{average:.2f}/5**\n"
                        f"📝 Total: **{count}**"
                    )

                await interaction.response.edit_message(
                    content=(
                        f"✅ Gracias por valorar la atención "
                        f"con **{value}/5 ⭐**."
                    ),
                    embed=None,
                    view=None
                )

                self.stop()

            button.callback = callback

            self.add_item(button)


class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)


    @discord.ui.button(
        label="Reclamar",
        emoji="🙋",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_claim"
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

        channel = interaction.channel

        data = get_ticket(
            channel.id
        )

        if not data:

            await interaction.response.send_message(
                "❌ Este canal no es un ticket.",
                ephemeral=True
            )

            return

        if data[3]:

            claimed_member = (
                interaction.guild.get_member(
                    data[3]
                )
            )

            name = (
                claimed_member.mention
                if claimed_member
                else f"<@{data[3]}>"
            )

            await interaction.response.send_message(
                f"❌ Este ticket ya fue reclamado por {name}.",
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
                channel.id
            )
        )

        db.commit()

        staff_role = interaction.guild.get_role(
            STAFF_ROLE_ID
        )

        if staff_role:

            await channel.set_permissions(
                staff_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

        await channel.set_permissions(
            interaction.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )

        await interaction.response.send_message(
            f"🙋 **Ticket reclamado por "
            f"{interaction.user.mention}.**\n"
            "Este miembro del staff se encargará del ticket."
        )


    @discord.ui.button(
        label="Añadir usuario",
        emoji="➕",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_add_user"
    )
    async def add_user(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

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
        custom_id="ticket_close"
    )
    async def close(
        self,
        interaction,
        button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Solo el staff puede cerrar tickets.",
                ephemeral=True
            )

            return

        channel = interaction.channel

        data = get_ticket(
            channel.id
        )

        if not data:

            await interaction.response.send_message(
                "❌ Este canal no es un ticket.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 Cerrando ticket..."
        )

        transcript_lines = []

        try:

            async for message in channel.history(
                limit=None,
                oldest_first=True
            ):

                timestamp = (
                    message.created_at.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                )

                content = (
                    message.content
                    or "[Sin texto]"
                )

                transcript_lines.append(
                    f"[{timestamp}] "
                    f"{message.author} "
                    f"({message.author.id}): "
                    f"{content}"
                )

        except Exception as e:

            transcript_lines.append(
                f"Error obteniendo historial: {e}"
            )

        transcript = "\n".join(
            transcript_lines
        )

        transcript_file = discord.File(
            io.BytesIO(
                transcript.encode("utf-8")
            ),
            filename=f"{channel.name}.txt"
        )

        transcript_channel = (
            interaction.guild.get_channel(
                TRANSCRIPT_CHANNEL_ID
            )
        )

        if transcript_channel:

            try:

                await transcript_channel.send(
                    content=(
                        f"📁 **Transcript de "
                        f"{channel.name}**\n"
                        f"👤 Usuario: <@{data[1]}>\n"
                        f"🛡️ Cerrado por: "
                        f"{interaction.user.mention}"
                    ),
                    file=transcript_file
                )

            except Exception as e:

                print(
                    "ERROR TRANSCRIPT:",
                    repr(e)
                )

        claimed_by = data[3]

        if claimed_by:

            user = interaction.guild.get_member(
                data[1]
            )

            if user:

                try:

                    await user.send(
                        "⭐ **¿Cómo fue la atención recibida?**\n"
                        "Valora al miembro del staff que atendió "
                        "tu ticket.",
                        view=RatingView(
                            claimed_by,
                            user.id
                        )
                    )

                except discord.Forbidden:

                    pass

        await send_log(
            interaction.guild,
            f"🔒 Ticket cerrado: **{channel.name}**\n"
            f"👤 Usuario: <@{data[1]}>\n"
            f"🛡️ Cerrado por: "
            f"{interaction.user.mention}"
        )

        cursor.execute(
            "DELETE FROM tickets WHERE channel_id = ?",
            (channel.id,)
        )

        db.commit()

        await asyncio.sleep(3)

        try:

            await channel.delete(
                reason="Ticket cerrado"
            )

        except Exception:
            pass


@bot.tree.command(
    name="ticketpanel",
    description="Crear el panel de tickets"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(
    interaction
):

    if TICKET_PANEL_CHANNEL_ID:

        if interaction.channel_id != TICKET_PANEL_CHANNEL_ID:

            await interaction.response.send_message(
                f"❌ Este comando solo puede utilizarse en "
                f"<#{TICKET_PANEL_CHANNEL_ID}>.",
                ephemeral=True
            )

            return

    embed = discord.Embed(
        title="🎫 Soporte • Corruption Network",
        description=(
            "¿Necesitas ayuda? Abre un ticket seleccionando "
            "una categoría.\n\n"

            "🎫 **Soporte**\n"
            "Ayuda general.\n\n"

            "🐛 **Bug**\n"
            "Reporta errores o problemas.\n\n"

            "🚨 **Reportar usuario**\n"
            "Reporta a un usuario.\n\n"

            "💰 **Estafa**\n"
            "Reporta posibles estafas.\n\n"

            "📝 **Postulación**\n"
            "Solicita entrar al equipo."
        ),
        color=discord.Color.red()
    )

    embed.set_footer(
        text="Corruption Network • Sistema de tickets"
    )

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "✅ Panel de tickets creado.",
        ephemeral=True
    )


# ============================================================
# STAFF STATS
# ============================================================

@bot.tree.command(
    name="staffstats",
    description="Ver estadísticas del staff"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def staffstats(
    interaction
):

    cursor.execute(
        """
        SELECT
            staff_id,
            COUNT(*),
            AVG(rating)
        FROM ratings
        GROUP BY staff_id
        ORDER BY average DESC
        """
    )

    rows = cursor.fetchall()

    if not rows:

        await interaction.response.send_message(
            "📊 Todavía no hay valoraciones.",
            ephemeral=True
        )

        return

    description = ""

    for staff_id, total, average in rows:

        member = interaction.guild.get_member(
            staff_id
        )

        mention = (
            member.mention
            if member
            else f"<@{staff_id}>"
        )

        description += (
            f"🛡️ {mention}\n"
            f"⭐ **{average:.2f}/5** "
            f"({total} valoraciones)\n\n"
        )

    embed = discord.Embed(
        title="📊 Estadísticas del Staff",
        description=description,
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# MODERACIÓN
# ============================================================

@bot.tree.command(
    name="kick",
    description="Expulsar a un usuario"
)
@app_commands.describe(
    member="Usuario a expulsar",
    reason="Motivo"
)
@app_commands.checks.has_permissions(
    kick_members=True
)
async def kick(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    await member.kick(
        reason=reason
    )

    await interaction.response.send_message(
        f"👢 {member.mention} ha sido expulsado.\n"
        f"**Motivo:** {reason}"
    )

    await send_log(
        interaction.guild,
        f"👢 {member.mention} expulsado por "
        f"{interaction.user.mention}\n"
        f"Motivo: {reason}"
    )


@bot.tree.command(
    name="ban",
    description="Banear a un usuario"
)
@app_commands.describe(
    member="Usuario a banear",
    reason="Motivo"
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def ban(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    await member.ban(
        reason=reason
    )

    await interaction.response.send_message(
        f"🔨 {member.mention} ha sido baneado.\n"
        f"**Motivo:** {reason}"
    )

    await send_log(
        interaction.guild,
        f"🔨 {member.mention} baneado por "
        f"{interaction.user.mention}\n"
        f"Motivo: {reason}"
    )


@bot.tree.command(
    name="unban",
    description="Desbanear mediante ID"
)
@app_commands.describe(
    user_id="ID del usuario",
    reason="Motivo"
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def unban(
    interaction,
    user_id: str,
    reason: str = "Sin motivo"
):

    try:

        user = await bot.fetch_user(
            int(user_id)
        )

        await interaction.guild.unban(
            user,
            reason=reason
        )

        await interaction.response.send_message(
            f"🔓 {user} ha sido desbaneado."
        )

    except Exception as e:

        await interaction.response.send_message(
            f"❌ No se pudo desbanear al usuario.\n"
            f"`{e}`",
            ephemeral=True
        )


@bot.tree.command(
    name="timeout",
    description="Aplicar timeout"
)
@app_commands.describe(
    member="Usuario",
    minutes="Duración en minutos",
    reason="Motivo"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def timeout(
    interaction,
    member: discord.Member,
    minutes: int,
    reason: str = "Sin motivo"
):

    if minutes < 1 or minutes > 40320:

        await interaction.response.send_message(
            "❌ La duración debe estar entre 1 y 40320 minutos.",
            ephemeral=True
        )

        return

    await member.timeout(
        now() + timedelta(
            minutes=minutes
        ),
        reason=reason
    )

    await interaction.response.send_message(
        f"🔇 {member.mention} ha recibido timeout durante "
        f"**{minutes} minutos**.\n"
        f"**Motivo:** {reason}"
    )


@bot.tree.command(
    name="untimeout",
    description="Quitar timeout"
)
@app_commands.describe(
    member="Usuario",
    reason="Motivo"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def untimeout(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    await member.timeout(
        None,
        reason=reason
    )

    await interaction.response.send_message(
        f"🔊 Timeout eliminado a {member.mention}."
    )


@bot.tree.command(
    name="warn",
    description="Advertir a un usuario"
)
@app_commands.describe(
    member="Usuario",
    reason="Motivo"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warn(
    interaction,
    member: discord.Member,
    reason: str = "Sin motivo"
):

    cursor.execute(
        """
        INSERT INTO warnings
        (
            guild_id,
            user_id,
            moderator_id,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            interaction.guild.id,
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
    description="Ver advertencias"
)
@app_commands.describe(
    member="Usuario"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warnings(
    interaction,
    member: discord.Member
):

    cursor.execute(
        """
        SELECT moderator_id, reason, created_at
        FROM warnings
        WHERE guild_id = ?
        AND user_id = ?
        ORDER BY id DESC
        """,
        (
            interaction.guild.id,
            member.id
        )
    )

    rows = cursor.fetchall()

    if not rows:

        await interaction.response.send_message(
            f"✅ {member.mention} no tiene advertencias."
        )

        return

    description = ""

    for index, (
        moderator_id,
        reason,
        created_at
    ) in enumerate(rows, 1):

        description += (
            f"**#{index}** — {reason}\n"
            f"Moderador: <@{moderator_id}>\n\n"
        )

    embed = discord.Embed(
        title=f"⚠️ Advertencias de {member}",
        description=description,
        color=discord.Color.orange()
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="clear",
    description="Borrar mensajes"
)
@app_commands.describe(
    amount="Cantidad de mensajes"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clear(
    interaction,
    amount: int
):

    if amount < 1 or amount > 100:

        await interaction.response.send_message(
            "❌ La cantidad debe estar entre 1 y 100.",
            ephemeral=True
        )

        return

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
    description="Bloquear canal"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def lock(interaction):

    overwrite = (
        interaction.channel.overwrites_for(
            interaction.guild.default_role
        )
    )

    overwrite.send_messages = False

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message(
        "🔒 Canal bloqueado."
    )


@bot.tree.command(
    name="unlock",
    description="Desbloquear canal"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def unlock(interaction):

    overwrite = (
        interaction.channel.overwrites_for(
            interaction.guild.default_role
        )
    )

    overwrite.send_messages = None

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message(
        "🔓 Canal desbloqueado."
    )


@bot.tree.command(
    name="slowmode",
    description="Configurar slowmode"
)
@app_commands.describe(
    seconds="Segundos"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def slowmode(
    interaction,
    seconds: int
):

    if seconds < 0 or seconds > 21600:

        await interaction.response.send_message(
            "❌ Debe estar entre 0 y 21600 segundos.",
            ephemeral=True
        )

        return

    await interaction.channel.edit(
        slowmode_delay=seconds
    )

    await interaction.response.send_message(
        f"🐢 Slowmode establecido en **{seconds} segundos**."
    )


# ============================================================
# INFORMACIÓN
# ============================================================

@bot.tree.command(
    name="userinfo",
    description="Ver información de un usuario"
)
@app_commands.describe(
    member="Usuario"
)
async def userinfo(
    interaction,
    member: discord.Member
):

    embed = discord.Embed(
        title=f"👤 Información de {member}",
        color=member.color
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="🆔 ID",
        value=str(member.id),
        inline=False
    )

    embed.add_field(
        name="📅 Cuenta creada",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    if member.joined_at:

        embed.add_field(
            name="📥 Entrada al servidor",
            value=discord.utils.format_dt(
                member.joined_at,
                style="F"
            ),
            inline=False
        )

    roles = [
        role.mention
        for role in member.roles[1:]
    ]

    embed.add_field(
        name="🎭 Roles",
        value=(
            " ".join(roles)
            if roles
            else "Sin roles"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="serverinfo",
    description="Ver información del servidor"
)
async def serverinfo(
    interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🌐 {guild.name}",
        color=discord.Color.red()
    )

    if guild.icon:

        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="👥 Miembros",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="💬 Canales",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="🆔 ID",
        value=str(guild.id),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# ERRORES
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        message = (
            "❌ No tienes permisos para utilizar "
            "este comando."
        )

    else:

        print(
            "ERROR SLASH COMMAND:",
            repr(error)
        )

        message = (
            "❌ Ha ocurrido un error ejecutando "
            "el comando."
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

    except Exception:
        pass


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print("=" * 60)
    print(f"🤖 BOT: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("=" * 60)

    # Views persistentes
    try:
        bot.add_view(
            VerificationView()
        )
    except Exception:
        pass

    try:
        bot.add_view(
            TicketPanelView()
        )
    except Exception:
        pass

    try:
        bot.add_view(
            TicketControlView()
        )
    except Exception:
        pass

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild:

        print(
            f"🏠 Servidor encontrado: {guild.name}"
        )

        java_role = discord.utils.get(
            guild.roles,
            name="JAVA"
        )

        bedrock_role = discord.utils.get(
            guild.roles,
            name="BEDROCK"
        )

        if java_role and bedrock_role:

            try:

                bot.add_view(
                    PlatformView(
                        java_role.id,
                        bedrock_role.id
                    )
                )

            except Exception:
                pass

        # ====================================================
        # SINCRONIZAR COMANDOS EN EL SERVIDOR
        # ====================================================

        try:

            bot.tree.copy_global_to(
                guild=guild
            )

            synced = await bot.tree.sync(
                guild=guild
            )

            print(
                f"✅ {len(synced)} comandos sincronizados."
            )

            print("📋 COMANDOS:")

            for command in synced:

                print(
                    f"   /{command.name}"
                )

        except Exception as e:

            print(
                "❌ ERROR SINCRONIZANDO:",
                repr(e)
            )

    else:

        print(
            "❌ No encuentro el GUILD_ID."
        )

    print(
        "🚀 CORRUPTION NETWORK BOT ONLINE"
    )


# ============================================================
# INICIAR
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "❌ Falta DISCORD_TOKEN en las variables de entorno."
    )


bot.run(TOKEN)
