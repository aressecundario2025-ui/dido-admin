import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
import json
from datetime import datetime

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

CANALES_PANEL = [
    1434297124539076738,
    1551198802164064266
]

ROL_SOPORTE = 1552374542909833246

NOMBRE_CATEGORIA_CERRADOS = "📂 TICKETS CERRADOS"

LOGO_PATH = "logo.png"

# =========================================================
# BASE DE DATOS
# =========================================================

DB_FILE = "tickets.db"

db = sqlite3.connect(DB_FILE)
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


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

views_registered = False


# =========================================================
# CATEGORÍAS
# =========================================================

CATEGORIAS = {
    "soporte": {
        "nombre": "🎫 Soporte general",
        "titulo": "🎫 Soporte general",
        "campos": [
            ("problema", "¿En qué podemos ayudarte?", discord.TextStyle.paragraph, True),
            ("info", "Información adicional", discord.TextStyle.paragraph, False)
        ]
    },

    "reportar": {
        "nombre": "🚨 Reportar usuario",
        "titulo": "🚨 Reportar usuario",
        "campos": [
            ("usuario", "Usuario a reportar", discord.TextStyle.short, True),
            ("motivo", "Motivo del reporte", discord.TextStyle.paragraph, True),
            ("pruebas", "Pruebas o enlaces", discord.TextStyle.paragraph, False)
        ]
    },

    "bug": {
        "nombre": "🐛 Reportar bug",
        "titulo": "🐛 Reportar bug",
        "campos": [
            ("bug", "¿Qué bug encontraste?", discord.TextStyle.paragraph, True),
            ("lugar", "¿Dónde ocurre?", discord.TextStyle.short, True),
            ("pasos", "Pasos para reproducirlo", discord.TextStyle.paragraph, True),
            ("pruebas", "Pruebas o capturas", discord.TextStyle.paragraph, False)
        ]
    },

    "postulacion": {
        "nombre": "👥 Postulaciones",
        "titulo": "👥 Postulación",
        "campos": [
            ("puesto", "¿A qué puesto te postulas?", discord.TextStyle.short, True),
            ("motivo", "¿Por qué quieres entrar?", discord.TextStyle.paragraph, True),
            ("experiencia", "Experiencia previa", discord.TextStyle.paragraph, True)
        ]
    },

    "estafa": {
        "nombre": "💰 Estafas",
        "titulo": "💰 Reporte de estafa",
        "campos": [
            ("usuario", "Usuario involucrado", discord.TextStyle.short, True),
            ("ocurrido", "¿Qué ocurrió?", discord.TextStyle.paragraph, True),
            ("pruebas", "Pruebas o enlaces", discord.TextStyle.paragraph, False)
        ]
    }
}


# =========================================================
# OBTENER / CREAR CATEGORÍA CERRADOS
# =========================================================

async def obtener_categoria_cerrados(guild: discord.Guild):

    categoria = discord.utils.get(
        guild.categories,
        name=NOMBRE_CATEGORIA_CERRADOS
    )

    if categoria:
        return categoria

    everyone = guild.default_role
    soporte = guild.get_role(ROL_SOPORTE)

    overwrites = {
        everyone: discord.PermissionOverwrite(
            view_channel=False
        )
    }

    if soporte:
        overwrites[soporte] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

    bot_member = guild.me

    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        )

    categoria = await guild.create_category(
        name=NOMBRE_CATEGORIA_CERRADOS,
        overwrites=overwrites,
        reason="Categoría privada para tickets cerrados"
    )

    return categoria


# =========================================================
# MODAL
# =========================================================

class TicketModal(discord.ui.Modal):

    def __init__(self, categoria_id):
        self.categoria_id = categoria_id

        datos = CATEGORIAS[categoria_id]

        super().__init__(
            title=datos["titulo"]
        )

        self.inputs = []

        for custom_id, label, style, required in datos["campos"]:

            campo = discord.ui.TextInput(
                label=label,
                custom_id=custom_id,
                style=style,
                required=required,
                max_length=1000
            )

            self.inputs.append(campo)
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ Este formulario solo funciona dentro del servidor.",
                ephemeral=True
            )
            return

        # Comprobar ticket abierto
        existente = db.execute(
            """
            SELECT channel_id
            FROM tickets
            WHERE guild_id = ?
            AND user_id = ?
            AND closed = 0
            """,
            (guild.id, interaction.user.id)
        ).fetchone()

        if existente:
            canal = guild.get_channel(existente[0])

            if canal:
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {canal.mention}",
                    ephemeral=True
                )
                return

            db.execute(
                "UPDATE tickets SET closed = 1 WHERE channel_id = ?",
                (existente[0],)
            )
            db.commit()

        datos = CATEGORIAS[self.categoria_id]

        respuestas = {}

        for campo in self.inputs:
            respuestas[campo.custom_id] = campo.value

        # =====================================================
        # PERMISOS DEL TICKET
        # =====================================================

        soporte = guild.get_role(ROL_SOPORTE)

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

        if soporte:
            overwrites[soporte] = discord.PermissionOverwrite(
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
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True
            )

        nombre = (
            f"ticket-{interaction.user.name}"
            .lower()
            .replace(" ", "-")
        )

        # Limitar longitud
        nombre = nombre[:90]

        canal = await guild.create_text_channel(
            name=nombre,
            overwrites=overwrites,
            reason=f"Ticket de {interaction.user}"
        )

        # =====================================================
        # GUARDAR EN DB
        # =====================================================

        db.execute(
            """
            INSERT INTO tickets
            (
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
            """,
            (
                canal.id,
                guild.id,
                interaction.user.id,
                self.categoria_id,
                datetime.utcnow().isoformat(),
                json.dumps(respuestas, ensure_ascii=False)
            )
        )

        db.commit()

        # =====================================================
        # EMBED DEL TICKET
        # =====================================================

        embed = discord.Embed(
            title=f"🎫 {datos['titulo']}",
            description=(
                f"Hola {interaction.user.mention} 👋\n\n"
                f"Tu ticket ha sido creado correctamente.\n"
                f"Un miembro del equipo te atenderá lo antes posible.\n\n"
                f"📌 **Categoría:** {datos['nombre']}"
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text="Eclipse World • Sistema de Tickets"
        )

        if os.path.exists(LOGO_PATH):
            file = discord.File(LOGO_PATH, filename="logo.png")
            embed.set_thumbnail(url="attachment://logo.png")
        else:
            file = None

        # Respuestas del formulario
        for custom_id, label, style, required in datos["campos"]:

            valor = respuestas.get(custom_id)

            if valor:
                embed.add_field(
                    name=label,
                    value=valor[:1024],
                    inline=False
                )

        mensaje = (
            f"{interaction.user.mention}\n"
            f"<@&{ROL_SOPORTE}>\n\n"
            f"**Controles del ticket:**"
        )

        if file:
            await canal.send(
                content=mensaje,
                embed=embed,
                file=file,
                view=TicketControlView()
            )
        else:
            await canal.send(
                content=mensaje,
                embed=embed,
                view=TicketControlView()
            )

        await interaction.response.send_message(
            f"✅ Ticket creado correctamente: {canal.mention}",
            ephemeral=True
        )


# =========================================================
# BOTONES DEL PANEL
# =========================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soporte general",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_soporte"
    )
    async def soporte(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            TicketModal("soporte")
        )

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_reportar"
    )
    async def reportar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            TicketModal("reportar")
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
        await interaction.response.send_modal(
            TicketModal("bug")
        )

    @discord.ui.button(
        label="Postulaciones",
        emoji="👥",
        style=discord.ButtonStyle.success,
        custom_id="ticket_postulacion"
    )
    async def postulacion(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            TicketModal("postulacion")
        )

    @discord.ui.button(
        label="Estafas",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_estafa"
    )
    async def estafa(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            TicketModal("estafa")
        )


# =========================================================
# BOTONES DENTRO DEL TICKET
# =========================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # -----------------------------------------------------
    # RECLAMAR
    # -----------------------------------------------------

    @discord.ui.button(
        label="Reclamar ticket",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_reclamar"
    )
    async def reclamar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.guild:
            return

        soporte = interaction.guild.get_role(ROL_SOPORTE)

        if not soporte or soporte not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Solo el equipo de soporte puede reclamar tickets.",
                ephemeral=True
            )
            return

        datos = db.execute(
            """
            SELECT user_id, claimed_by, closed
            FROM tickets
            WHERE channel_id = ?
            """,
            (interaction.channel.id,)
        ).fetchone()

        if not datos:
            await interaction.response.send_message(
                "❌ No se encontró este ticket en la base de datos.",
                ephemeral=True
            )
            return

        user_id, claimed_by, closed = datos

        if closed:
            await interaction.response.send_message(
                "❌ Este ticket ya está cerrado.",
                ephemeral=True
            )
            return

        if claimed_by:
            miembro = interaction.guild.get_member(claimed_by)

            nombre = miembro.mention if miembro else f"<@{claimed_by}>"

            await interaction.response.send_message(
                f"❌ Este ticket ya está reclamado por {nombre}.",
                ephemeral=True
            )
            return

        db.execute(
            """
            UPDATE tickets
            SET claimed_by = ?
            WHERE channel_id = ?
            """,
            (interaction.user.id, interaction.channel.id)
        )

        db.commit()

        # Soporte puede ver pero NO escribir
        await interaction.channel.set_permissions(
            soporte,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

        # El staff que reclama puede escribir
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
            f"Solo el creador y el miembro de staff que lo ha reclamado "
            f"pueden escribir ahora."
        )

    # -----------------------------------------------------
    # LIBERAR
    # -----------------------------------------------------

    @discord.ui.button(
        label="Liberar ticket",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_liberar"
    )
    async def liberar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.guild:
            return

        soporte = interaction.guild.get_role(ROL_SOPORTE)

        if not soporte or soporte not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Solo el equipo de soporte puede liberar tickets.",
                ephemeral=True
            )
            return

        datos = db.execute(
            """
            SELECT claimed_by, closed
            FROM tickets
            WHERE channel_id = ?
            """,
            (interaction.channel.id,)
        ).fetchone()

        if not datos:
            await interaction.response.send_message(
                "❌ Ticket no encontrado.",
                ephemeral=True
            )
            return

        claimed_by, closed = datos

        if closed:
            await interaction.response.send_message(
                "❌ Este ticket está cerrado.",
                ephemeral=True
            )
            return

        if not claimed_by:
            await interaction.response.send_message(
                "❌ Este ticket no está reclamado.",
                ephemeral=True
            )
            return

        if claimed_by != interaction.user.id:
            await interaction.response.send_message(
                "❌ Solo quien reclamó el ticket puede liberarlo.",
                ephemeral=True
            )
            return

        db.execute(
            """
            UPDATE tickets
            SET claimed_by = NULL
            WHERE channel_id = ?
            """,
            (interaction.channel.id,)
        )

        db.commit()

        # Staff vuelve a poder escribir
        await interaction.channel.set_permissions(
            soporte,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        # Quitar permiso individual del staff
        await interaction.channel.set_permissions(
            interaction.user,
            overwrite=None
        )

        button_reclamar = discord.utils.get(
            self.children,
            custom_id="ticket_reclamar"
        )

        if button_reclamar:
            button_reclamar.label = "Reclamar ticket"
            button_reclamar.disabled = False

        await interaction.response.edit_message(
            view=self
        )

        await interaction.channel.send(
            f"🔄 **Ticket liberado por {interaction.user.mention}.**\n"
            f"El equipo de soporte vuelve a poder atenderlo."
        )

    # -----------------------------------------------------
    # CERRAR
    # -----------------------------------------------------

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_cerrar"
    )
    async def cerrar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.guild:
            return

        soporte = interaction.guild.get_role(ROL_SOPORTE)

        if not soporte or soporte not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Solo el equipo de soporte puede cerrar tickets.",
                ephemeral=True
            )
            return

        datos = db.execute(
            """
            SELECT user_id, claimed_by, category, closed
            FROM tickets
            WHERE channel_id = ?
            """,
            (interaction.channel.id,)
        ).fetchone()

        if not datos:
            await interaction.response.send_message(
                "❌ No se encontró este ticket.",
                ephemeral=True
            )
            return

        user_id, claimed_by, category_id, closed = datos

        if closed:
            await interaction.response.send_message(
                "❌ Este ticket ya está cerrado.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # =================================================
        # CATEGORÍA PRIVADA
        # =================================================

        categoria_cerrados = await obtener_categoria_cerrados(
            interaction.guild
        )

        # =================================================
        # ACTUALIZAR DB
        # =================================================

        ahora = datetime.utcnow().isoformat()

        db.execute(
            """
            UPDATE tickets
            SET closed = 1,
                closed_at = ?
            WHERE channel_id = ?
            """,
            (ahora, interaction.channel.id)
        )

        db.commit()

        # =================================================
        # MOVER TICKET
        # =================================================

        await interaction.channel.edit(
            category=categoria_cerrados,
            sync_permissions=True,
            reason="Ticket cerrado"
        )

        # Usuario pierde acceso
        usuario = interaction.guild.get_member(user_id)

        if usuario:
            await interaction.channel.set_permissions(
                usuario,
                view_channel=False,
                send_messages=False
            )

        # Staff solo lectura
        await interaction.channel.set_permissions(
            soporte,
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )

        # Staff que lo reclamó también solo lectura
        if claimed_by:
            staff = interaction.guild.get_member(claimed_by)

            if staff:
                await interaction.channel.set_permissions(
                    staff,
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True
                )

        # Bot
        if interaction.guild.me:
            await interaction.channel.set_permissions(
                interaction.guild.me,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )

        # =================================================
        # RENOMBRAR
        # =================================================

        await interaction.channel.edit(
            name=f"🔒-{interaction.channel.name}"[:100]
        )

        # =================================================
        # MENSAJE DE ARCHIVO
        # =================================================

        categoria_nombre = CATEGORIAS.get(
            category_id,
            {}
        ).get(
            "nombre",
            category_id
        )

        staff_text = (
            f"<@{claimed_by}>"
            if claimed_by
            else "Sin reclamar"
        )

        embed = discord.Embed(
            title="📁 TICKET CERRADO",
            color=discord.Color.dark_grey()
        )

        embed.add_field(
            name="👤 Usuario",
            value=f"<@{user_id}>",
            inline=True
        )

        embed.add_field(
            name="📂 Categoría",
            value=categoria_nombre,
            inline=True
        )

        embed.add_field(
            name="👮 Atendido por",
            value=staff_text,
            inline=True
        )

        embed.add_field(
            name="🕐 Cerrado",
            value=f"<t:{int(datetime.now().timestamp())}:F>",
            inline=False
        )

        embed.set_footer(
            text="Eclipse World • Ticket archivado"
        )

        await interaction.channel.send(
            embed=embed
        )

        # =================================================
        # PEDIR VALORACIÓN POR DM
        # =================================================

        if usuario:

            try:

                embed_rating = discord.Embed(
                    title="⭐ Valora tu atención",
                    description=(
                        "Tu ticket de **Eclipse World** ha sido cerrado.\n\n"
                        "Nos gustaría saber qué tal fue la atención recibida.\n"
                        "Selecciona una valoración de **1 a 5 estrellas**."
                    ),
                    color=discord.Color.gold()
                )

                await usuario.send(
                    embed=embed_rating,
                    view=RatingView(
                        interaction.channel.id
                    )
                )

            except discord.Forbidden:
                await interaction.channel.send(
                    f"⚠️ No pude enviar el mensaje de valoración a "
                    f"<@{user_id}> porque tiene los mensajes directos cerrados."
                )

        await interaction.followup.send(
            "🔒 Ticket cerrado y archivado correctamente.",
            ephemeral=True
        )


# =========================================================
# VALORACIONES
# =========================================================

class RatingView(discord.ui.View):

    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    async def registrar(
        self,
        interaction: discord.Interaction,
        puntuacion: int
    ):

        datos = db.execute(
            """
            SELECT user_id, guild_id, claimed_by, closed
            FROM tickets
            WHERE channel_id = ?
            """,
            (self.channel_id,)
        ).fetchone()

        if not datos:
            await interaction.response.send_message(
                "❌ No se encontró el ticket.",
                ephemeral=True
            )
            return

        user_id, guild_id, staff_id, closed = datos

        if interaction.user.id != user_id:
            await interaction.response.send_message(
                "❌ Esta valoración pertenece a otro usuario.",
                ephemeral=True
            )
            return

        existente = db.execute(
            """
            SELECT id
            FROM ratings
            WHERE channel_id = ?
            AND user_id = ?
            """,
            (self.channel_id, interaction.user.id)
        ).fetchone()

        if existente:
            await interaction.response.send_message(
                "❌ Ya has valorado este ticket.",
                ephemeral=True
            )
            return

        db.execute(
            """
            INSERT INTO ratings
            (
                channel_id,
                guild_id,
                user_id,
                staff_id,
                rating,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                self.channel_id,
                guild_id,
                interaction.user.id,
                staff_id,
                puntuacion,
                datetime.utcnow().isoformat()
            )
        )

        db.commit()

        await interaction.response.send_modal(
            RatingCommentModal(
                self.channel_id,
                puntuacion
            )
        )

    @discord.ui.button(
        label="1",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="rating_1"
    )
    async def rating1(self, interaction, button):
        await self.registrar(interaction, 1)

    @discord.ui.button(
        label="2",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="rating_2"
    )
    async def rating2(self, interaction, button):
        await self.registrar(interaction, 2)

    @discord.ui.button(
        label="3",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="rating_3"
    )
    async def rating3(self, interaction, button):
        await self.registrar(interaction, 3)

    @discord.ui.button(
        label="4",
        emoji="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="rating_4"
    )
    async def rating4(self, interaction, button):
        await self.registrar(interaction, 4)

    @discord.ui.button(
        label="5",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="rating_5"
    )
    async def rating5(self, interaction, button):
        await self.registrar(interaction, 5)


# =========================================================
# MODAL DE COMENTARIO
# =========================================================

class RatingCommentModal(discord.ui.Modal):

    def __init__(self, channel_id, rating):
        super().__init__(
            title="💬 Comentario opcional"
        )

        self.channel_id = channel_id
        self.rating = rating

        self.comentario = discord.ui.TextInput(
            label="¿Quieres dejar un comentario?",
            placeholder="Escribe aquí tu opinión...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )

        self.add_item(self.comentario)

    async def on_submit(self, interaction):

        db.execute(
            """
            UPDATE ratings
            SET comment = ?
            WHERE channel_id = ?
            AND user_id = ?
            """,
            (
                self.comentario.value,
                self.channel_id,
                interaction.user.id
            )
        )

        db.commit()

        # Buscar ticket
        datos = db.execute(
            """
            SELECT guild_id, claimed_by
            FROM tickets
            WHERE channel_id = ?
            """,
            (self.channel_id,)
        ).fetchone()

        if datos:
            guild_id, staff_id = datos

            guild = bot.get_guild(guild_id)

            if guild:

                canal = guild.get_channel(self.channel_id)

                # Mostrar valoración dentro del ticket archivado
                if canal:

                    comentario = (
                        self.comentario.value
                        if self.comentario.value
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
                        name="⭐ Valoración",
                        value=f"{self.rating}/5",
                        inline=True
                    )

                    embed.add_field(
                        name="💬 Comentario",
                        value=comentario[:1024],
                        inline=False
                    )

                    await canal.send(
                        embed=embed
                    )

        await interaction.response.send_message(
            "⭐ ¡Gracias por valorar la atención de Eclipse World!",
            ephemeral=True
        )


# =========================================================
# COMANDO /TICKETPANEL
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Publica el panel de tickets de Eclipse World"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎫 Tickets • Eclipse World",
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
        text="Eclipse World • Sistema de Tickets"
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


# =========================================================
# ERRORES
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

        await interaction.response.send_message(
            "❌ Necesitas permisos de administrador para usar este comando.",
            ephemeral=True
        )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global views_registered

    if not views_registered:

        bot.add_view(TicketPanelView())
        bot.add_view(TicketControlView())

        # Las RatingView necesitan channel_id dinámico,
        # por eso se restauran mediante los mensajes existentes
        # cuando se pulsan. Los botones del DM permanecen activos
        # durante la sesión actual.

        await bot.tree.sync()

        views_registered = True

    print(f"✅ Eclipse World Tickets conectado como {bot.user}")


# =========================================================
# ARRANCAR
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "❌ Falta la variable DISCORD_TOKEN en Railway."
    )

bot.run(TOKEN)
