import os
import re
from datetime import timedelta
import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN_DISCORD")
PANEL_CHANNEL_ID = 1434297124539076738

CATEGORY_NAME = "🎫 TICKETS"
STAFF_ROLE_NAME = "Staff"


intents = discord.Intents.default()
intents.guilds = True
intents.members = True


def safe_name(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ_-]+", "-", text)
    return text.strip("-")[:20] or "usuario"


class TicketTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Postulación",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:postulacion",
    )
    async def postulacion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PostulacionModal())

    @discord.ui.button(
        label="Duda",
        emoji="❓",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:duda",
    )
    async def duda(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DudaModal())

    @discord.ui.button(
        label="Reportar bug",
        emoji="🐛",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:bug",
    )
    async def bug(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BugModal())

    @discord.ui.button(
        label="Reportar usuario",
        emoji="🚨",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:usuario",
    )
    async def usuario(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReportUserModal())


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Cerrar ticket",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:close",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Este botón solo funciona dentro de un ticket.",
                ephemeral=True,
            )
            return

        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        is_staff = staff_role in interaction.user.roles if staff_role else False
        is_admin = interaction.user.guild_permissions.administrator

        if not is_staff and not is_admin:
            await interaction.response.send_message(
                "Solo el Staff puede cerrar tickets.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("🔒 Cerrando ticket en 5 segundos...")
        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=5))
        await channel.delete(reason=f"Ticket cerrado por {interaction.user}")


class BaseModal(discord.ui.Modal):
    ticket_type = "ticket"

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        fields: list[tuple[str, str]],
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Este formulario solo puede usarse dentro de un servidor.",
                ephemeral=True,
            )
            return

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        if category is None:
            await interaction.response.send_message(
                f"❌ No existe la categoría **{CATEGORY_NAME}**.",
                ephemeral=True,
            )
            return

        if staff_role is None:
            await interaction.response.send_message(
                f"❌ No existe el rol **{STAFF_ROLE_NAME}**.",
                ephemeral=True,
            )
            return

        # Evita que el mismo usuario abra otro ticket mientras ya tiene uno abierto.
        existing = None
        for channel in category.text_channels:
            if channel.topic and str(interaction.user.id) in channel.topic:
                existing = channel
                break

        if existing:
            await interaction.response.send_message(
                f"Ya tienes un ticket abierto: {existing.mention}",
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        channel_name = f"{self.ticket_type}-{safe_name(interaction.user.name)}"

        channel = await guild.create_text_channel(
            channel_name[:100],
            category=category,
            overwrites=overwrites,
            topic=f"user_id:{interaction.user.id} | type:{self.ticket_type}",
            reason=f"Ticket de {interaction.user}",
        )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="👤 Usuario",
            value=f"{interaction.user.mention}\n`{interaction.user}`\nID: `{interaction.user.id}`",
            inline=False,
        )

        for name, value in fields:
            if value.strip():
                embed.add_field(
                    name=name[:256],
                    value=value[:1024],
                    inline=False,
                )

        embed.set_footer(text="Sistema de tickets • Pilares")

        await channel.send(
            content=f"{interaction.user.mention} <@&{staff_role.id}>",
            embed=embed,
            view=CloseTicketView(),
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=True,
            ),
        )

        await interaction.response.send_message(
            f"✅ Ticket creado correctamente: {channel.mention}",
            ephemeral=True,
        )


class PostulacionModal(BaseModal, title="📝 Postulación"):
    ticket_type = "postulacion"

    experiencia = discord.ui.TextInput(
        label="¿Qué puesto quieres solicitar?",
        placeholder="Builder, Staff, Moderador...",
        max_length=100,
    )
    edad = discord.ui.TextInput(
        label="Edad",
        placeholder="Escribe tu edad",
        max_length=3,
    )
    experiencia_detalle = discord.ui.TextInput(
        label="Experiencia",
        placeholder="Cuéntanos brevemente tu experiencia.",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
    )
    disponibilidad = discord.ui.TextInput(
        label="Disponibilidad",
        placeholder="Ej: tardes y fines de semana",
        max_length=300,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.create_ticket(
            interaction,
            "📝 Nueva postulación",
            "El usuario ha enviado una candidatura.",
            [
                ("🎯 Puesto solicitado", self.experiencia.value),
                ("🎂 Edad", self.edad.value),
                ("⭐ Experiencia", self.experiencia_detalle.value),
                ("🕐 Disponibilidad", self.disponibilidad.value),
            ],
        )


class DudaModal(BaseModal, title="❓ Duda"):
    ticket_type = "duda"

    asunto = discord.ui.TextInput(
        label="Asunto",
        placeholder="¿Sobre qué necesitas ayuda?",
        max_length=150,
    )
    descripcion = discord.ui.TextInput(
        label="Describe tu duda",
        placeholder="Explica el problema con el mayor detalle posible.",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.create_ticket(
            interaction,
            "❓ Nueva duda",
            "El usuario necesita ayuda del equipo.",
            [
                ("📌 Asunto", self.asunto.value),
                ("💬 Descripción", self.descripcion.value),
            ],
        )


class BugModal(BaseModal, title="🐛 Reportar bug"):
    donde = discord.ui.TextInput(
        label="¿Dónde ocurre?",
        placeholder="Servidor, minijuego, Discord, etc.",
        max_length=200,
    )
    descripcion = discord.ui.TextInput(
        label="Describe el bug",
        placeholder="Qué ocurre y cómo podemos reproducirlo.",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )
    evidencia = discord.ui.TextInput(
        label="Evidencia / enlace",
        placeholder="Opcional: imagen, vídeo o enlace.",
        max_length=500,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.create_ticket(
            interaction,
            "🐛 Nuevo reporte de bug",
            "El usuario ha reportado un posible error.",
            [
                ("📍 Dónde ocurre", self.donde.value),
                ("🐛 Descripción", self.descripcion.value),
                ("🔗 Evidencia", self.evidencia.value),
            ],
        )


class ReportUserModal(BaseModal, title="🚨 Reportar usuario"):
    usuario = discord.ui.TextInput(
        label="Usuario que quieres reportar",
        placeholder="Nombre o ID del usuario",
        max_length=100,
    )
    motivo = discord.ui.TextInput(
        label="Motivo",
        placeholder="Explica qué ha ocurrido.",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )
    evidencia = discord.ui.TextInput(
        label="Evidencia / enlace",
        placeholder="Opcional: imagen, vídeo o enlace.",
        max_length=500,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.create_ticket(
            interaction,
            "🚨 Reporte de usuario",
            "El usuario ha enviado un reporte para revisión del Staff.",
            [
                ("👤 Usuario reportado", self.usuario.value),
                ("📋 Motivo", self.motivo.value),
                ("🔗 Evidencia", self.evidencia.value),
            ],
        )


class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        # Vistas persistentes: los botones siguen funcionando después de reiniciar Railway.
        self.add_view(TicketTypeView())
        self.add_view(CloseTicketView())

    async def on_ready(self):
        print(f"✅ Bot conectado como {self.user} (ID: {self.user.id})")

        for guild in self.guilds:
            await ensure_server_setup(guild)

        print("✅ Sistema de tickets listo.")


bot = TicketBot()


async def ensure_server_setup(guild: discord.Guild):
    """Usa la categoría y el rol existentes. No crea nada."""
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

    if category is None:
        print(
            f"❌ No existe la categoría '{CATEGORY_NAME}' en {guild.name}. "
            "Créala antes de iniciar el bot."
        )
        return

    if staff_role is None:
        print(
            f"❌ No existe el rol '{STAFF_ROLE_NAME}' en {guild.name}. "
            "Créalo antes de iniciar el bot."
        )
        return

    channel = guild.get_channel(PANEL_CHANNEL_ID)
    if channel is None or not isinstance(channel, discord.TextChannel):
        print(
            f"⚠️ No encuentro el canal {PANEL_CHANNEL_ID} en {guild.name}. "
            "Comprueba que el ID sea correcto."
        )
        return

    # Solo crea el panel si no existe ya uno del bot.
    async for message in channel.history(limit=50):
        if message.author.id == bot.user.id and message.components:
            return

    embed = discord.Embed(
        title="🎫 Centro de soporte y postulaciones",
        description=(
            "Selecciona una opción para abrir un ticket.\n\n"
            "📝 **Postulación** — solicita entrar al equipo.\n"
            "❓ **Duda** — pregunta cualquier cosa relacionada con el servidor.\n"
            "🐛 **Reportar bug** — informa de errores.\n"
            "🚨 **Reportar usuario** — informa de una situación para que el Staff la revise.\n\n"
            "Al enviar el formulario se creará un canal privado para ti y el Staff."
        ),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Pilares • Sistema automático de tickets")

    await channel.send(embed=embed, view=TicketTypeView())
    print(f"📨 Panel enviado en #{channel.name} ({guild.name})")


@bot.event
async def on_guild_join(guild: discord.Guild):
    await ensure_server_setup(guild)


if not TOKEN:
    raise RuntimeError(
        "Falta la variable de entorno TOKEN_DISCORD en Railway."
    )

bot.run(TOKEN)
