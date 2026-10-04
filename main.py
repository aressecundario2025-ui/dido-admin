import os
import io
import re
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# CONFIGURACIÓN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))

TICKET_PANEL_CHANNEL_ID = int(os.getenv("TICKET_PANEL_CHANNEL_ID", "0"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
RATINGS_CHANNEL_ID = int(os.getenv("RATINGS_CHANNEL_ID", "0"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID", "0"))

STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))

# VERIFICACIÓN
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
# INTENTS
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

    if STAFF_ROLE_ID and any(
        role.id == STAFF_ROLE_ID for role in member.roles
    ):
        return True

    if ADMIN_ROLE_ID and any(
        role.id == ADMIN_ROLE_ID for role in member.roles
    ):
        return True

    return False


def is_admin(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    if ADMIN_ROLE_ID and any(
        role.id == ADMIN_ROLE_ID for role in member.roles
    ):
        return True

    return False


async def send_log(message):
    if not LOG_CHANNEL_ID:
        return

    channel = bot.get_channel(LOG_CHANNEL_ID)

    if channel:
        try:
            await channel.send(message)
        except Exception:
            pass


# ============================================================
# CAPTCHA
# ============================================================

captcha_storage = {}


def generate_captcha_code(length=4):
    """
    CAPTCHA fácil:
    - 4 caracteres
    - Sin O/0
    - Sin I/1
    - Sin S/5
    """

    characters = "ABCDEFGHJKLMNPQRTUVWXYZ2346789"

    return "".join(
        random.choice(characters)
        for _ in range(length)
    )


def create_captcha_image(code):

    width = 600
    height = 220

    image = Image.new(
        "RGB",
        (width, height),
        (245, 245, 245)
    )

    draw = ImageDraw.Draw(image)

    # Fondo con pequeños puntos
    for _ in range(120):
        x = random.randint(0, width)
        y = random.randint(0, height)

        draw.ellipse(
            (x, y, x + 2, y + 2),
            fill=(190, 190, 190)
        )

    # Líneas suaves
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)

        x2 = random.randint(0, width)
        y2 = random.randint(0, height)

        draw.line(
            (x1, y1, x2, y2),
            fill=(150, 150, 150),
            width=2
        )

    # Fuente
    try:
        font = ImageFont.truetype(
            "DejaVuSans-Bold.ttf",
            82
        )
    except Exception:
        font = ImageFont.load_default()

    # Dibujar caracteres separados
    total_width = 0
    char_widths = []

    for char in code:
        bbox = draw.textbbox(
            (0, 0),
            char,
            font=font
        )

        char_width = bbox[2] - bbox[0]

        char_widths.append(char_width)
        total_width += char_width

    spacing = 15
    total_width += spacing * (len(code) - 1)

    x = (width - total_width) // 2

    for index, char in enumerate(code):

        y = random.randint(65, 90)

        draw.text(
            (x, y),
            char,
            font=font,
            fill=(30, 30, 30)
        )

        x += char_widths[index] + spacing

    image = image.filter(
        ImageFilter.GaussianBlur(radius=0.3)
    )

    output = io.BytesIO()

    image.save(
        output,
        format="PNG"
    )

    output.seek(0)

    return output


class CaptchaModal(discord.ui.Modal, title="Introducir CAPTCHA"):

    captcha = discord.ui.TextInput(
        label="Escribe el código de la imagen",
        placeholder="Ejemplo: K7P4",
        min_length=4,
        max_length=4,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        user_id = interaction.user.id

        data = captcha_storage.get(user_id)

        if not data:
            await interaction.response.send_message(
                "❌ Tu CAPTCHA ha caducado. Pulsa **Verificarme** otra vez.",
                ephemeral=True
            )
            return

        code = data["code"]
        expires = data["expires"]

        if datetime.now(timezone.utc) > expires:

            captcha_storage.pop(user_id, None)

            await interaction.response.send_message(
                "⏰ El CAPTCHA ha caducado. Pulsa **Verificarme** otra vez.",
                ephemeral=True
            )

            return

        if self.captcha.value.upper().strip() != code:

            await interaction.response.send_message(
                "❌ CAPTCHA incorrecto. Inténtalo de nuevo.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ No se ha podido encontrar el servidor.",
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
                "❌ No encuentro el rol de miembro.",
                ephemeral=True
            )

            return

        if role in member.roles:

            captcha_storage.pop(
                user_id,
                None
            )

            await interaction.response.send_message(
                "✅ Ya estás verificado.",
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
                "❌ No puedo darte el rol. Asegúrate de que mi rol esté **por encima de Miembro**.",
                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"Error dando rol: {e}"
            )

            await interaction.response.send_message(
                "❌ Ha ocurrido un error al darte el rol.",
                ephemeral=True
            )

            return

        captcha_storage.pop(
            user_id,
            None
        )

        await interaction.response.send_message(
            "🎉 **Verificación completada correctamente.**\n"
            "Ya tienes acceso al servidor.",
            ephemeral=True
        )


class CaptchaInputView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Introducir CAPTCHA",
        style=discord.ButtonStyle.primary,
        emoji="🔑"
    )
    async def enter_captcha(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            CaptchaModal()
        )


class VerificationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verificarme",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="corruption_verify"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = interaction.user.id

        code = generate_captcha_code()

        captcha_storage[user_id] = {
            "code": code,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=3)
        }

        image = create_captcha_image(
            code
        )

        file = discord.File(
            image,
            filename="captcha.png"
        )

        embed = discord.Embed(
            title="🔐 Verificación",
            description=(
                "Para verificarte, escribe exactamente "
                "los **4 caracteres** que aparecen en la imagen.\n\n"
                "⏱️ Tienes **3 minutos**."
            ),
            color=discord.Color.blue()
        )

        embed.set_image(
            url="attachment://captcha.png"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file,
            view=CaptchaInputView(),
            ephemeral=True
        )


async def send_verification_panel(channel):

    embed = discord.Embed(
        title="🛡️ Verificación — Corruption Network",
        description=(
            "Bienvenido a **Corruption Network**.\n\n"
            "Para acceder al servidor debes verificarte.\n\n"
            "Pulsa el botón **✅ Verificarme** y completa "
            "el pequeño CAPTCHA que aparecerá.\n\n"
            "🔐 La verificación es rápida y automática."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="Corruption Network • Sistema de verificación"
    )

    await channel.send(
        embed=embed,
        view=VerificationView()
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
        interaction: discord.Interaction
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

                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
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
            (channel_id, user_id, ticket_type, claimed_by, created_at)
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
                "Un miembro del equipo atenderá tu ticket "
                "lo antes posible."
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
        super().__init__(timeout=None)

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
        interaction: discord.Interaction
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
                "❌ ID de usuario inválida.",
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
        super().__init__(timeout=60)

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

        await interaction.response.defer()

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
        super().__init__(timeout=None)

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
                "❌ No tienes permiso para reclamar tickets.",
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


async def close_ticket(channel, closed_by):

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

    transcript_file = None

    if transcript:

        transcript_file = discord.File(
            io.BytesIO(
                transcript.encode(
                    "utf-8"
                )
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
                    (ticket_id, staff_id, user_id, rating, created_at)
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
                        f"⭐ Gracias por valorar la atención con "
                        f"**{value}/5**."
                    ),
                    view=None
                )

            button.callback = callback

            self.add_item(
                button
            )


# ============================================================
# COMANDOS DE ADMINISTRACIÓN
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
    description="Desbanea un usuario mediante ID."
)
@app_commands.describe(
    user_id="ID del usuario"
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

        until = now() + timedelta(
            minutes=minutes
        )

        await member.timeout(
            until,
            reason=reason
        )

        await interaction.response.send_message(
            f"🔇 {member.mention} ha recibido un timeout "
            f"de **{minutes} minutos**.\n"
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
@app_commands.describe(
    member="Usuario",
    reason="Motivo"
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
    description="Consulta las advertencias de un usuario."
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
@app_commands.describe(
    amount="Cantidad"
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

    if amount < 1:
        amount = 1

    if amount > 100:
        amount = 100

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
@app_commands.describe(
    seconds="Segundos"
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

    if seconds < 0:
        seconds = 0

    if seconds > 21600:
        seconds = 21600

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

    embed.add_field(
        name="Entró al servidor",
        value=(
            discord.utils.format_dt(
                member.joined_at,
                style="F"
            )
            if member.joined_at
            else "Desconocido"
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
            "❌ Este comando solo puede utilizarse en el canal de verificación.",
            ephemeral=True
        )

        return

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "❌ No tienes permisos para hacer esto.",
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
            "❌ Este comando solo puede utilizarse en el canal configurado.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🎫 Centro de soporte — Corruption Network",
        description=(
            "¿Necesitas ayuda?\n\n"
            "Selecciona el tipo de ticket que necesitas "
            "utilizando los botones de abajo.\n\n"
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
# STAFF STATS
# ============================================================

@bot.tree.command(
    name="staffstats",
    description="Muestra las estadísticas de atención de un staff."
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

    # Registrar botones persistentes
    bot.add_view(
        VerificationView()
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
        "❌ Falta la variable DISCORD_TOKEN en Railway."
    )

bot.run(
    TOKEN
)
