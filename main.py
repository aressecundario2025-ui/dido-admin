import os
import io
import re
import random
import string
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# CONFIGURACIÓN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Servidor de Discord
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# ============================================================
# TICKETS
# ============================================================

TICKET_PANEL_CHANNEL_ID = int(os.getenv("TICKET_PANEL_CHANNEL_ID", "0"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
RATINGS_CHANNEL_ID = int(os.getenv("RATINGS_CHANNEL_ID", "0"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID", "0"))

STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))

# ============================================================
# VERIFICACIÓN
# ============================================================

VERIFICATION_CHANNEL_ID = 1555632348907708508
MEMBER_ROLE_ID = 1556321345145667708


# ============================================================
# BASE DE DATOS
# ============================================================

DB_FILE = "corruption_network.db"

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER UNIQUE,
    guild_id INTEGER,
    user_id INTEGER,
    ticket_type TEXT,
    reason TEXT,
    claimed_by INTEGER DEFAULT 0,
    created_at TEXT,
    closed_at TEXT,
    status TEXT DEFAULT 'open'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
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
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    created_at TEXT
)
""")

db.commit()


# ============================================================
# INTENTS
# ============================================================

# No usamos Message Content ni Members para evitar
# el error PrivilegedIntentsRequired.
intents = discord.Intents.default()
intents.guilds = True


# ============================================================
# BOT
# ============================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# UTILIDADES
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_channel(channel_id: int):
    return bot.get_channel(channel_id)


def get_member_role(guild: discord.Guild):
    return guild.get_role(MEMBER_ROLE_ID)


def is_staff_or_admin(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    if STAFF_ROLE_ID and any(role.id == STAFF_ROLE_ID for role in member.roles):
        return True

    if ADMIN_ROLE_ID and any(role.id == ADMIN_ROLE_ID for role in member.roles):
        return True

    return False


def is_admin(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    if ADMIN_ROLE_ID and any(role.id == ADMIN_ROLE_ID for role in member.roles):
        return True

    return False


def safe_channel_name(name: str):
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name[:80]


def get_open_ticket(user_id: int, guild_id: int):
    row = cursor.execute(
        """
        SELECT * FROM tickets
        WHERE user_id = ?
        AND guild_id = ?
        AND status = 'open'
        """,
        (user_id, guild_id)
    ).fetchone()

    return row


def get_ticket(channel_id: int):
    return cursor.execute(
        "SELECT * FROM tickets WHERE channel_id = ?",
        (channel_id,)
    ).fetchone()


async def send_log(
    guild: discord.Guild,
    title: str,
    description: str,
    color=discord.Color.blurple()
):
    if not LOG_CHANNEL_ID:
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)

    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_footer(text="Corruption Network • Logs")

    try:
        await channel.send(embed=embed)
    except Exception:
        pass


# ============================================================
# CAPTCHA
# ============================================================

captcha_storage = {}


def generate_captcha_code(length=6):
    characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    return "".join(
        random.choice(characters)
        for _ in range(length)
    )


def create_captcha_image(code: str):
    width = 500
    height = 180

    image = Image.new(
        "RGB",
        (width, height),
        (245, 247, 250)
    )

    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype(
            "DejaVuSans-Bold.ttf",
            62
        )
    except Exception:
        font = ImageFont.load_default()

    # Fondo con puntos
    for _ in range(700):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)

        draw.point(
            (x, y),
            fill=(
                random.randint(150, 220),
                random.randint(150, 220),
                random.randint(150, 220)
            )
        )

    # Líneas anti-bot
    for _ in range(12):
        draw.line(
            (
                random.randint(0, width),
                random.randint(0, height),
                random.randint(0, width),
                random.randint(0, height)
            ),
            fill=(
                random.randint(80, 180),
                random.randint(80, 180),
                random.randint(80, 180)
            ),
            width=random.randint(1, 3)
        )

    # Código
    char_width = width // len(code)

    for index, char in enumerate(code):

        x = index * char_width + random.randint(10, 25)
        y = random.randint(40, 75)

        draw.text(
            (x, y),
            char,
            font=font,
            fill=(
                random.randint(15, 70),
                random.randint(15, 70),
                random.randint(15, 70)
            )
        )

    image = image.filter(
        ImageFilter.GaussianBlur(radius=0.25)
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    buffer.seek(0)

    return buffer


# ============================================================
# MODAL CAPTCHA
# ============================================================

class CaptchaModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="🛡️ Verificación • Corruption Network",
            timeout=180
        )

        self.answer = discord.ui.TextInput(
            label="Código CAPTCHA",
            placeholder="Escribe el código de la imagen",
            required=True,
            min_length=6,
            max_length=6
        )

        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):

        user_id = interaction.user.id

        data = captcha_storage.get(user_id)

        if not data:
            await interaction.response.send_message(
                "❌ Tu CAPTCHA ha expirado. Pulsa **Verificarme** para generar uno nuevo.",
                ephemeral=True
            )
            return

        code = data["code"]
        expires = data["expires"]

        if datetime.now(timezone.utc) > expires:
            captcha_storage.pop(user_id, None)

            await interaction.response.send_message(
                "⌛ Tu CAPTCHA ha expirado. Genera uno nuevo.",
                ephemeral=True
            )
            return

        answer = str(self.answer.value).strip().upper()

        if answer != code:

            captcha_storage.pop(user_id, None)

            await interaction.response.send_message(
                "❌ **CAPTCHA incorrecto.**\n\nPulsa **Verificarme** para obtener otro CAPTCHA.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        if not guild:
            await interaction.response.send_message(
                "❌ No se pudo identificar el servidor.",
                ephemeral=True
            )
            return

        role = guild.get_role(MEMBER_ROLE_ID)

        if not role:
            await interaction.response.send_message(
                "❌ No encuentro el rol **Miembro**. Revisa el ID del rol.",
                ephemeral=True
            )
            return

        member = interaction.user

        if not isinstance(member, discord.Member):
            try:
                member = await guild.fetch_member(user_id)
            except Exception:
                await interaction.response.send_message(
                    "❌ No pude obtener tus datos del servidor.",
                    ephemeral=True
                )
                return

        if role in member.roles:
            captcha_storage.pop(user_id, None)

            await interaction.response.send_message(
                "ℹ️ Ya estás verificado.",
                ephemeral=True
            )

            return

        try:
            await member.add_roles(
                role,
                reason="Verificación CAPTCHA"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ No puedo darte el rol **Miembro**.\n\n"
                "Comprueba que el rol del bot esté por encima de `Miembro`.",
                ephemeral=True
            )

            return

        except Exception as e:

            print("Error dando rol:", e)

            await interaction.response.send_message(
                "❌ Ocurrió un error al asignarte el rol.",
                ephemeral=True
            )

            return

        captcha_storage.pop(user_id, None)

        embed = discord.Embed(
            title="✅ Verificación completada",
            description=(
                f"¡Bienvenido a **{guild.name}**, {member.mention}!\n\n"
                "Has completado correctamente el CAPTCHA.\n"
                "Ya tienes acceso como miembro de la comunidad."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_footer(
            text="Corruption Network • Sistema de verificación"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        await send_log(
            guild,
            "🛡️ Usuario verificado",
            f"{member.mention} (`{member.id}`) ha completado el CAPTCHA.",
            discord.Color.green()
        )


# ============================================================
# BOTÓN VERIFICACIÓN
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

        guild = interaction.guild

        if not guild:
            await interaction.response.send_message(
                "❌ Este botón solo funciona dentro del servidor.",
                ephemeral=True
            )
            return

        role = guild.get_role(MEMBER_ROLE_ID)

        if not role:
            await interaction.response.send_message(
                "❌ El rol `Miembro` no existe o el ID es incorrecto.",
                ephemeral=True
            )
            return

        member = interaction.user

        if isinstance(member, discord.Member):

            if role in member.roles:

                await interaction.response.send_message(
                    "ℹ️ Ya estás verificado y tienes el rol **Miembro**.",
                    ephemeral=True
                )

                return

        code = generate_captcha_code()

        captcha_storage[interaction.user.id] = {
            "code": code,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=3)
        }

        image_buffer = create_captcha_image(code)

        file = discord.File(
            image_buffer,
            filename="captcha.png"
        )

        embed = discord.Embed(
            title="🛡️ CAPTCHA de seguridad",
            description=(
                "**Paso 1:** Mira la imagen.\n"
                "**Paso 2:** Pulsa `Introducir CAPTCHA`.\n"
                "**Paso 3:** Escribe exactamente el código.\n\n"
                "⏱️ El CAPTCHA expira en **3 minutos**."
            ),
            color=discord.Color.blurple()
        )

        embed.set_image(url="attachment://captcha.png")

        await interaction.response.send_message(
            embed=embed,
            file=file,
            view=CaptchaInputView(),
            ephemeral=True
        )


# ============================================================
# BOTÓN PARA ABRIR MODAL CAPTCHA
# ============================================================

class CaptchaInputView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Introducir CAPTCHA",
        emoji="🔐",
        style=discord.ButtonStyle.primary
    )
    async def input_captcha(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id not in captcha_storage:

            await interaction.response.send_message(
                "❌ Tu CAPTCHA ha expirado. Genera uno nuevo.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            CaptchaModal()
        )


# ============================================================
# PANEL DE VERIFICACIÓN
# ============================================================

async def send_verification_panel(
    channel: discord.TextChannel
):

    embed = discord.Embed(
        title="🛡️ Verificación • Corruption Network",
        description=(
            "## Bienvenido a Corruption Network\n\n"
            "Antes de acceder al servidor debes completar "
            "una pequeña verificación de seguridad.\n\n"
            "### 🔐 ¿Cómo funciona?\n"
            "1. Pulsa **Verificarme**.\n"
            "2. Completa el CAPTCHA personalizado.\n"
            "3. Si el código es correcto, recibirás automáticamente "
            "el rol **Miembro**.\n\n"
            "### ⚠️ Importante\n"
            "No compartas códigos de verificación con otras personas.\n"
            "El CAPTCHA expira después de unos minutos."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Corruption Network • Sistema de seguridad"
    )

    if channel.guild.icon:
        embed.set_thumbnail(
            url=channel.guild.icon.url
        )

    await channel.send(
        embed=embed,
        view=VerificationView()
    )


# ============================================================
# TICKET PANEL
# ============================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, ticket_type: str):
        super().__init__(
            title=f"Ticket • {ticket_type}",
            timeout=300
        )

        self.ticket_type = ticket_type

        self.reason = discord.ui.TextInput(
            label="Explícanos tu problema",
            placeholder="Describe detalladamente lo que necesitas...",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=5,
            max_length=1500
        )

        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        if not guild:
            await interaction.response.send_message(
                "❌ No se pudo identificar el servidor.",
                ephemeral=True
            )
            return

        existing = get_open_ticket(
            interaction.user.id,
            guild.id
        )

        if existing:

            channel = guild.get_channel(
                existing["channel_id"]
            )

            if channel:

                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )

                return

        category = guild.get_channel(
            TICKET_CATEGORY_ID
        )

        if not category or not isinstance(
            category,
            discord.CategoryChannel
        ):

            await interaction.response.send_message(
                "❌ La categoría de tickets no está configurada correctamente.",
                ephemeral=True
            )

            return

        staff_role = guild.get_role(
            STAFF_ROLE_ID
        )

        admin_role = guild.get_role(
            ADMIN_ROLE_ID
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

        if staff_role:

            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

        if admin_role:

            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )

        ticket_number = random.randint(
            1000,
            9999
        )

        channel_name = safe_channel_name(
            f"ticket-{ticket_number}-{interaction.user.name}"
        )

        try:

            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user} • {self.ticket_type}"
            )

        except Exception as e:

            print("Error creando ticket:", e)

            await interaction.response.send_message(
                "❌ No pude crear el ticket. Revisa los permisos del bot.",
                ephemeral=True
            )

            return

        cursor.execute(
            """
            INSERT INTO tickets
            (
                channel_id,
                guild_id,
                user_id,
                ticket_type,
                reason,
                claimed_by,
                created_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                channel.id,
                guild.id,
                interaction.user.id,
                self.ticket_type,
                self.reason.value,
                0,
                now_iso(),
                "open"
            )
        )

        db.commit()

        embed = discord.Embed(
            title=f"🎫 Ticket • {self.ticket_type}",
            description=(
                f"Bienvenido {interaction.user.mention}.\n\n"
                "Un miembro del equipo te atenderá lo antes posible.\n\n"
                f"**Motivo:**\n{self.reason.value}"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="Estado",
            value="🟢 Abierto",
            inline=True
        )

        embed.add_field(
            name="Staff asignado",
            value="Nadie todavía",
            inline=True
        )

        embed.set_footer(
            text="Corruption Network • Soporte"
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketControlView()
        )

        await interaction.response.send_message(
            f"✅ Ticket creado correctamente: {channel.mention}",
            ephemeral=True
        )

        await send_log(
            guild,
            "🎫 Ticket creado",
            (
                f"**Usuario:** {interaction.user.mention}\n"
                f"**Tipo:** {self.ticket_type}\n"
                f"**Canal:** {channel.mention}"
            ),
            discord.Color.green()
        )


# ============================================================
# PANEL DE TICKETS
# ============================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def open_ticket(
        self,
        interaction: discord.Interaction,
        ticket_type: str
    ):

        guild = interaction.guild

        if not guild:
            return

        existing = get_open_ticket(
            interaction.user.id,
            guild.id
        )

        if existing:

            channel = guild.get_channel(
                existing["channel_id"]
            )

            if channel:

                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )

                return

        await interaction.response.send_modal(
            TicketModal(ticket_type)
        )

    @discord.ui.button(
        label="Soporte",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="corruption_ticket_support"
    )
    async def support(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.open_ticket(
            interaction,
            "Soporte"
        )

    @discord.ui.button(
        label="Bug",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
        custom_id="corruption_ticket_bug"
    )
    async def bug(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.open_ticket(
            interaction,
            "Bug"
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="corruption_ticket_report"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.open_ticket(
            interaction,
            "Reportar usuario"
        )

    @discord.ui.button(
        label="Estafa",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="corruption_ticket_scam"
    )
    async def scam(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.open_ticket(
            interaction,
            "Estafa"
        )

    @discord.ui.button(
        label="Postulación",
        emoji="📋",
        style=discord.ButtonStyle.success,
        custom_id="corruption_ticket_application"
    )
    async def application(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.open_ticket(
            interaction,
            "Postulación"
        )


# ============================================================
# RECLAMAR TICKET
# ============================================================

class TicketClaimView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(
        label="Reclamar ticket",
        emoji="🙋",
        style=discord.ButtonStyle.success
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            await interaction.response.send_message(
                "❌ No se pudo identificar tu usuario.",
                ephemeral=True
            )

            return

        if not is_staff_or_admin(interaction.user):

            await interaction.response.send_message(
                "❌ No tienes permisos para reclamar tickets.",
                ephemeral=True
            )

            return

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Este canal no es un ticket válido.",
                ephemeral=True
            )

            return

        if ticket["claimed_by"]:

            claimed = interaction.guild.get_member(
                ticket["claimed_by"]
            )

            name = (
                claimed.mention
                if claimed
                else f"`{ticket['claimed_by']}`"
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
                interaction.channel.id
            )
        )

        db.commit()

        await interaction.response.send_message(
            f"🙋 {interaction.user.mention} ha reclamado este ticket."
        )

        await send_log(
            interaction.guild,
            "🙋 Ticket reclamado",
            (
                f"**Staff:** {interaction.user.mention}\n"
                f"**Ticket:** {interaction.channel.mention}"
            ),
            discord.Color.green()
        )


# ============================================================
# AÑADIR USUARIO AL TICKET
# ============================================================

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

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_staff_or_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

            return

        try:
            user_id = int(
                self.user_id.value.strip()
            )
        except ValueError:

            await interaction.response.send_message(
                "❌ ID inválido.",
                ephemeral=True
            )

            return

        try:
            member = await interaction.guild.fetch_member(
                user_id
            )
        except Exception:

            await interaction.response.send_message(
                "❌ No encontré ese usuario en el servidor.",
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


# ============================================================
# CONFIRMACIÓN DE CIERRE
# ============================================================

class CloseConfirmView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await close_ticket(
            interaction
        )

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
            embed=None,
            view=None
        )


# ============================================================
# CONTROL TICKET
# ============================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Reclamar",
        emoji="🙋",
        style=discord.ButtonStyle.success,
        custom_id="corruption_ticket_claim"
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_staff_or_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ No tienes permisos para reclamar tickets.",
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

        if ticket["claimed_by"]:

            staff = interaction.guild.get_member(
                ticket["claimed_by"]
            )

            staff_text = (
                staff.mention
                if staff
                else f"`{ticket['claimed_by']}`"
            )

            await interaction.response.send_message(
                f"❌ Ya está reclamado por {staff_text}.",
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
            f"🙋 Ticket reclamado por {interaction.user.mention}."
        )

    @discord.ui.button(
        label="Añadir usuario",
        emoji="👤",
        style=discord.ButtonStyle.secondary,
        custom_id="corruption_ticket_add"
    )
    async def add_user(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_staff_or_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ No tienes permisos.",
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
        custom_id="corruption_ticket_close"
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
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

        allowed = False

        if interaction.user.id == ticket["user_id"]:
            allowed = True

        if isinstance(
            interaction.user,
            discord.Member
        ) and is_staff_or_admin(
            interaction.user
        ):
            allowed = True

        if ticket["claimed_by"] == interaction.user.id:
            allowed = True

        if not allowed:

            await interaction.response.send_message(
                "❌ No tienes permisos para cerrar este ticket.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🔒 Confirmar cierre",
            description=(
                "¿Seguro que quieres cerrar este ticket?\n\n"
                "Se generará una transcripción antes de cerrarlo."
            ),
            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            view=CloseConfirmView()
        )


# ============================================================
# TRANSCRIPCIÓN
# ============================================================

async def generate_transcript(
    channel: discord.TextChannel
):

    lines = []

    lines.append(
        f"TRANSCRIPCIÓN - {channel.guild.name}"
    )

    lines.append(
        f"Canal: #{channel.name}"
    )

    lines.append(
        f"Fecha: {datetime.now(timezone.utc).isoformat()}"
    )

    lines.append(
        "=" * 70
    )

    try:

        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):

            timestamp = message.created_at.isoformat()

            author = (
                f"{message.author} "
                f"({message.author.id})"
            )

            content = message.content

            if not content:
                content = "[Sin texto]"

            lines.append(
                f"[{timestamp}] {author}: {content}"
            )

            for attachment in message.attachments:

                lines.append(
                    f"    Archivo: {attachment.url}"
                )

    except Exception as e:

        lines.append(
            f"[ERROR OBTENIENDO MENSAJES] {e}"
        )

    return "\n".join(lines)


# ============================================================
# CERRAR TICKET
# ============================================================

async def close_ticket(
    interaction: discord.Interaction
):

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):

        return

    ticket = get_ticket(
        channel.id
    )

    if not ticket:

        await interaction.response.send_message(
            "❌ Este canal no es un ticket.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔄 Cerrando ticket y generando transcripción..."
    )

    transcript = await generate_transcript(
        channel
    )

    transcript_file = io.BytesIO(
        transcript.encode(
            "utf-8",
            errors="replace"
        )
    )

    transcript_file.seek(0)

    filename = (
        f"transcript-{channel.id}.txt"
    )

    cursor.execute(
        """
        UPDATE tickets
        SET status = 'closed',
            closed_at = ?
        WHERE channel_id = ?
        """,
        (
            now_iso(),
            channel.id
        )
    )

    db.commit()

    # Canal de transcripciones
    if TRANSCRIPT_CHANNEL_ID:

        transcript_channel = interaction.guild.get_channel(
            TRANSCRIPT_CHANNEL_ID
        )

        if transcript_channel:

            file = discord.File(
                transcript_file,
                filename=filename
            )

            embed = discord.Embed(
                title="📝 Transcripción de ticket",
                description=(
                    f"**Ticket:** #{channel.name}\n"
                    f"**Usuario:** <@{ticket['user_id']}>\n"
                    f"**Tipo:** {ticket['ticket_type']}"
                ),
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )

            if ticket["claimed_by"]:

                embed.add_field(
                    name="Staff",
                    value=f"<@{ticket['claimed_by']}>",
                    inline=True
                )

            await transcript_channel.send(
                embed=embed,
                file=file
            )

    # Valoración
    if RATINGS_CHANNEL_ID:

        rating_channel = interaction.guild.get_channel(
            RATINGS_CHANNEL_ID
        )

        if rating_channel:

            staff_id = ticket["claimed_by"]

            if staff_id:

                embed = discord.Embed(
                    title="⭐ Valora la atención recibida",
                    description=(
                        "Gracias por utilizar el soporte de "
                        "**Corruption Network**.\n\n"
                        "Selecciona una puntuación de **1 a 5 estrellas**."
                    ),
                    color=discord.Color.gold()
                )

                await rating_channel.send(
                    content=f"<@{ticket['user_id']}>",
                    embed=embed,
                    view=RatingView(
                        ticket_id=ticket["id"],
                        staff_id=staff_id,
                        user_id=ticket["user_id"]
                    )
                )

    await send_log(
        interaction.guild,
        "🔒 Ticket cerrado",
        (
            f"**Canal:** `#{channel.name}`\n"
            f"**Usuario:** <@{ticket['user_id']}>\n"
            f"**Cerrado por:** {interaction.user.mention}"
        ),
        discord.Color.red()
    )

    await asyncio.sleep(2)

    try:
        await channel.delete(
            reason="Ticket cerrado"
        )
    except Exception as e:
        print("Error eliminando ticket:", e)


# ============================================================
# VALORACIONES
# ============================================================

class RatingView(discord.ui.View):

    def __init__(
        self,
        ticket_id: int,
        staff_id: int,
        user_id: int
    ):

        super().__init__(timeout=None)

        self.ticket_id = ticket_id
        self.staff_id = staff_id
        self.user_id = user_id

    async def rate(
        self,
        interaction: discord.Interaction,
        rating: int
    ):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "❌ Esta valoración no es para ti.",
                ephemeral=True
            )

            return

        existing = cursor.execute(
            """
            SELECT * FROM ratings
            WHERE ticket_id = ?
            """,
            (self.ticket_id,)
        ).fetchone()

        if existing:

            await interaction.response.send_message(
                "ℹ️ Este ticket ya tiene una valoración.",
                ephemeral=True
            )

            return

        cursor.execute(
            """
            INSERT INTO ratings
            (
                guild_id,
                ticket_id,
                staff_id,
                user_id,
                rating,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild.id,
                self.ticket_id,
                self.staff_id,
                self.user_id,
                rating,
                now_iso()
            )
        )

        db.commit()

        stars = "⭐" * rating

        await interaction.response.edit_message(
            content=f"✅ Valoración registrada: {stars}",
            embed=None,
            view=None
        )

        await send_log(
            interaction.guild,
            "⭐ Nueva valoración",
            (
                f"**Usuario:** {interaction.user.mention}\n"
                f"**Staff:** <@{self.staff_id}>\n"
                f"**Valoración:** {stars} ({rating}/5)"
            ),
            discord.Color.gold()
        )

    @discord.ui.button(
        label="1",
        emoji="⭐",
        style=discord.ButtonStyle.danger
    )
    async def one(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.rate(interaction, 1)

    @discord.ui.button(
        label="2",
        emoji="⭐",
        style=discord.ButtonStyle.danger
    )
    async def two(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.rate(interaction, 2)

    @discord.ui.button(
        label="3",
        emoji="⭐",
        style=discord.ButtonStyle.secondary
    )
    async def three(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.rate(interaction, 3)

    @discord.ui.button(
        label="4",
        emoji="⭐",
        style=discord.ButtonStyle.success
    )
    async def four(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.rate(interaction, 4)

    @discord.ui.button(
        label="5",
        emoji="⭐",
        style=discord.ButtonStyle.success
    )
    async def five(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.rate(interaction, 5)


# ============================================================
# EVENTO READY
# ============================================================

@bot.event
async def on_ready():

    print("=" * 60)
    print("CORRUPTION NETWORK BOT")
    print("=" * 60)
    print(f"Bot: {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"Servidores: {len(bot.guilds)}")
    print("=" * 60)

    # Vistas persistentes
    bot.add_view(
        VerificationView()
    )

    bot.add_view(
        TicketPanelView()
    )

    bot.add_view(
        TicketControlView()
    )

    # Sincronización
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
                f"Comandos sincronizados: {len(synced)}"
            )

        else:

            synced = await bot.tree.sync()

            print(
                f"Comandos globales sincronizados: {len(synced)}"
            )

    except Exception as e:

        print(
            "Error sincronizando comandos:",
            e
        )


# ============================================================
# COMANDO VERIFICACIÓN
# ============================================================

@bot.tree.command(
    name="verificacion",
    description="Envía el panel de verificación."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def verificacion(
    interaction: discord.Interaction
):

    if interaction.channel.id != VERIFICATION_CHANNEL_ID:

        await interaction.response.send_message(
            f"❌ Este comando solo puede utilizarse en <#{VERIFICATION_CHANNEL_ID}>.",
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
# COMANDO TICKET PANEL
# ============================================================

@bot.tree.command(
    name="ticketpanel",
    description="Envía el panel de tickets."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def ticketpanel(
    interaction: discord.Interaction
):

    if TICKET_PANEL_CHANNEL_ID:

        if interaction.channel.id != TICKET_PANEL_CHANNEL_ID:

            await interaction.response.send_message(
                f"❌ Este comando solo puede utilizarse en <#{TICKET_PANEL_CHANNEL_ID}>.",
                ephemeral=True
            )

            return

    embed = discord.Embed(
        title="🎫 Centro de Soporte",
        description=(
            "Bienvenido al soporte de **Corruption Network**.\n\n"
            "Selecciona la categoría que mejor describa tu solicitud.\n\n"
            "🎫 **Soporte**\n"
            "Ayuda general y dudas.\n\n"
            "🐛 **Bug**\n"
            "Reporta errores del servidor.\n\n"
            "🚨 **Reportar usuario**\n"
            "Reporta comportamientos o usuarios.\n\n"
            "💰 **Estafa**\n"
            "Reporta posibles estafas.\n\n"
            "📋 **Postulación**\n"
            "Solicita entrar al equipo."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Corruption Network • Sistema de Tickets"
    )

    if interaction.guild.icon:

        embed.set_thumbnail(
            url=interaction.guild.icon.url
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
# ADMINISTRACIÓN
# ============================================================

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
    reason: str = "Sin motivo especificado"
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ No puedes expulsarte a ti mismo.",
            ephemeral=True
        )

        return

    try:

        await member.kick(
            reason=reason
        )

        await interaction.response.send_message(
            f"👢 {member.mention} ha sido expulsado.\n"
            f"**Motivo:** {reason}"
        )

        await send_log(
            interaction.guild,
            "👢 Usuario expulsado",
            (
                f"**Usuario:** {member.mention}\n"
                f"**Moderador:** {interaction.user.mention}\n"
                f"**Motivo:** {reason}"
            ),
            discord.Color.orange()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo expulsar a ese usuario.",
            ephemeral=True
        )


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
    reason: str = "Sin motivo especificado"
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ No puedes banearte a ti mismo.",
            ephemeral=True
        )

        return

    try:

        await member.ban(
            reason=reason
        )

        await interaction.response.send_message(
            f"🔨 {member.mention} ha sido baneado.\n"
            f"**Motivo:** {reason}"
        )

        await send_log(
            interaction.guild,
            "🔨 Usuario baneado",
            (
                f"**Usuario:** {member.mention}\n"
                f"**Moderador:** {interaction.user.mention}\n"
                f"**Motivo:** {reason}"
            ),
            discord.Color.red()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo banear a ese usuario.",
            ephemeral=True
        )


@bot.tree.command(
    name="unban",
    description="Desbanea un usuario mediante su ID."
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):

    try:

        uid = int(user_id)

    except ValueError:

        await interaction.response.send_message(
            "❌ ID inválido.",
            ephemeral=True
        )

        return

    try:

        user = await bot.fetch_user(
            uid
        )

        await interaction.guild.unban(
            user
        )

        await interaction.response.send_message(
            f"✅ {user.mention} ha sido desbaneado."
        )

        await send_log(
            interaction.guild,
            "🔓 Usuario desbaneado",
            (
                f"**Usuario:** {user.mention}\n"
                f"**Moderador:** {interaction.user.mention}"
            ),
            discord.Color.green()
        )

    except discord.NotFound:

        await interaction.response.send_message(
            "❌ Ese usuario no está baneado.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No tengo permisos para desbanear usuarios.",
            ephemeral=True
        )


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
    reason: str = "Sin motivo especificado"
):

    if minutos < 1 or minutos > 40320:

        await interaction.response.send_message(
            "❌ El tiempo debe estar entre 1 y 40320 minutos.",
            ephemeral=True
        )

        return

    until = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=minutos
    )

    try:

        await member.timeout(
            until,
            reason=reason
        )

        await interaction.response.send_message(
            f"🔇 {member.mention} ha recibido un timeout de "
            f"**{minutos} minutos**.\n"
            f"**Motivo:** {reason}"
        )

        await send_log(
            interaction.guild,
            "🔇 Timeout",
            (
                f"**Usuario:** {member.mention}\n"
                f"**Moderador:** {interaction.user.mention}\n"
                f"**Duración:** {minutos} minutos\n"
                f"**Motivo:** {reason}"
            ),
            discord.Color.orange()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo aplicar timeout a ese usuario.",
            ephemeral=True
        )


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
            reason="Timeout eliminado"
        )

        await interaction.response.send_message(
            f"🔊 Timeout eliminado para {member.mention}."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ No puedo modificar el timeout de ese usuario.",
            ephemeral=True
        )


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
    reason: str
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
            now_iso()
        )
    )

    db.commit()

    count = cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM warnings
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (
            interaction.guild.id,
            member.id
        )
    ).fetchone()["total"]

    await interaction.response.send_message(
        f"⚠️ {member.mention} ha recibido una advertencia.\n"
        f"**Motivo:** {reason}\n"
        f"**Advertencias totales:** `{count}`"
    )

    await send_log(
        interaction.guild,
        "⚠️ Advertencia",
        (
            f"**Usuario:** {member.mention}\n"
            f"**Moderador:** {interaction.user.mention}\n"
            f"**Motivo:** {reason}\n"
            f"**Total:** {count}"
        ),
        discord.Color.orange()
    )


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

    rows = cursor.execute(
        """
        SELECT *
        FROM warnings
        WHERE guild_id = ?
        AND user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (
            interaction.guild.id,
            member.id
        )
    ).fetchall()

    if not rows:

        await interaction.response.send_message(
            f"✅ {member.mention} no tiene advertencias."
        )

        return

    embed = discord.Embed(
        title=f"⚠️ Advertencias • {member}",
        color=discord.Color.orange()
    )

    for index, row in enumerate(rows, 1):

        moderator = interaction.guild.get_member(
            row["moderator_id"]
        )

        moderator_text = (
            moderator.mention
            if moderator
            else str(row["moderator_id"])
        )

        embed.add_field(
            name=f"Advertencia #{index}",
            value=(
                f"**Motivo:** {row['reason']}\n"
                f"**Moderador:** {moderator_text}"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="clear",
    description="Elimina mensajes de un canal."
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

    deleted = await interaction.channel.purge(
        limit=cantidad
    )

    await interaction.followup.send(
        f"🧹 Se han eliminado **{len(deleted)} mensajes**.",
        ephemeral=True
    )


@bot.tree.command(
    name="lock",
    description="Bloquea un canal."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def lock(
    interaction: discord.Interaction
):

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
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
    description="Desbloquea un canal."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def unlock(
    interaction: discord.Interaction
):

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
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
    description="Configura el modo lento de un canal."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def slowmode(
    interaction: discord.Interaction,
    segundos: app_commands.Range[int, 0, 21600]
):

    await interaction.channel.edit(
        slowmode_delay=segundos
    )

    await interaction.response.send_message(
        f"🐢 Slowmode configurado a **{segundos} segundos**."
    )


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
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Usuario",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=f"`{member.id}`",
        inline=True
    )

    embed.add_field(
        name="Cuenta creada",
        value=discord.utils.format_dt(
            member.created_at,
            "F"
        ),
        inline=False
    )

    embed.add_field(
        name="Entró al servidor",
        value=(
            discord.utils.format_dt(
                member.joined_at,
                "F"
            )
            if member.joined_at
            else "Desconocido"
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
        value=(
            ", ".join(roles)
            if roles
            else "Sin roles"
        )[:1024],
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="serverinfo",
    description="Muestra información del servidor."
)
async def serverinfo(
    interaction: discord.Interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🌐 {guild.name}",
        color=discord.Color.blurple()
    )

    if guild.icon:

        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="ID",
        value=f"`{guild.id}`",
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
            "F"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# ESTADÍSTICAS DE STAFF
# ============================================================

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

    row = cursor.execute(
        """
        SELECT
            COUNT(*) AS total,
            AVG(rating) AS average
        FROM ratings
        WHERE guild_id = ?
        AND staff_id = ?
        """,
        (
            interaction.guild.id,
            member.id
        )
    ).fetchone()

    total = row["total"] or 0
    average = row["average"]

    if average is None:
        average_text = "Sin valoraciones"
    else:
        average_text = f"{average:.2f}/5 ⭐"

    embed = discord.Embed(
        title="📊 Estadísticas de Staff",
        color=discord.Color.blurple()
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
        value=average_text,
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# MANEJO DE ERRORES
# ============================================================

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
        app_commands.errors.CheckFailure
    ):

        message = (
            "❌ No tienes permisos para utilizar este comando."
        )

    else:

        print(
            "Error de slash command:",
            repr(error)
        )

        message = (
            "❌ Ha ocurrido un error ejecutando el comando."
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
# ARRANQUE
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "Falta la variable DISCORD_TOKEN en Railway."
    )


bot.run(TOKEN)
