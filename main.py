import os
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("TOKEN_DISCORD")

CANAL_INFO = 1549058205051527198

WEB = "https://pillar-arena-survival.base44.app/"
IP = "minepillarss.minehut.gg"
DISCORD_INVITE = "https://discord.gg/ajfMu4ryJU"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


def es_admin(member):
    return member.guild_permissions.administrator


@bot.event
async def on_ready():
    print(f"DiDo Admin conectado como {bot.user}")
    print(f"ID: {bot.user.id}")

    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} comandos sincronizados.")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Canal específico para web, IP y Discord
    if message.channel.id == CANAL_INFO:

        texto = message.content.strip().lower()

        if texto == "web":
            embed = discord.Embed(
                title="🌐 Web de Pilares",
                description=f"🔗 {WEB}",
                color=discord.Color.blurple()
            )
            await message.channel.send(embed=embed)
            return

        if texto == "ip":
            embed = discord.Embed(
                title="🎮 IP de Pilares",
                description=f"```{IP}```",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            return

        if texto == "discord":
            embed = discord.Embed(
                title="💬 Discord de Pilares",
                description=DISCORD_INVITE,
                color=discord.Color.purple()
            )
            await message.channel.send(embed=embed)
            return

        if texto == "ayuda":
            embed = discord.Embed(
                title="📋 Información de Pilares",
                description=(
                    "**web** → Web de Pilares\n"
                    "**ip** → IP del servidor\n"
                    "**discord** → Discord de Pilares"
                ),
                color=discord.Color.blurple()
            )
            await message.channel.send(embed=embed)
            return

    await bot.process_commands(message)


@bot.tree.command(
    name="admin",
    description="Da el rol DiDo Admin a un usuario."
)
@app_commands.describe(
    usuario="Usuario al que quieres dar DiDo Admin"
)
async def admin(interaction: discord.Interaction, usuario: discord.Member):

    if not es_admin(interaction.user):
        await interaction.response.send_message(
            "❌ Necesitas permisos de Administrador.",
            ephemeral=True
        )
        return

    rol = discord.utils.get(
        interaction.guild.roles,
        name="DiDo Admin"
    )

    if rol is None:
        try:
            rol = await interaction.guild.create_role(
                name="DiDo Admin",
                reason="Rol creado por DiDo Admin"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permiso para crear roles.",
                ephemeral=True
            )
            return

    if rol >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Mi rol debe estar por encima de `DiDo Admin`.",
            ephemeral=True
        )
        return

    try:
        await usuario.add_roles(
            rol,
            reason=f"Asignado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ {usuario.mention} ahora tiene **DiDo Admin**."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No puedo asignar el rol. "
            "Coloca mi rol por encima de `DiDo Admin`.",
            ephemeral=True
        )


@bot.tree.command(
    name="quitaradmin",
    description="Quita el rol DiDo Admin a un usuario."
)
@app_commands.describe(
    usuario="Usuario al que quieres quitar DiDo Admin"
)
async def quitaradmin(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not es_admin(interaction.user):
        await interaction.response.send_message(
            "❌ Necesitas permisos de Administrador.",
            ephemeral=True
        )
        return

    rol = discord.utils.get(
        interaction.guild.roles,
        name="DiDo Admin"
    )

    if rol is None:
        await interaction.response.send_message(
            "ℹ️ El rol DiDo Admin no existe.",
            ephemeral=True
        )
        return

    if rol >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Mi rol debe estar por encima de `DiDo Admin`.",
            ephemeral=True
        )
        return

    try:
        await usuario.remove_roles(
            rol,
            reason=f"Retirado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Se ha quitado **DiDo Admin** a {usuario.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ No puedo quitar el rol.",
            ephemeral=True
        )


@bot.tree.command(
    name="ayuda",
    description="Muestra los comandos de DiDo Admin."
)
async def ayuda(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🤖 DiDo Admin",
        description="Panel de administración de Pilares.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🛡️ Administración",
        value=(
            "`/admin @usuario` → Dar DiDo Admin\n"
            "`/quitaradmin @usuario` → Quitar DiDo Admin"
        ),
        inline=False
    )

    embed.add_field(
        name="📢 Canal de información",
        value=(
            f"<#{CANAL_INFO}>\n\n"
            "`web` → Web\n"
            "`ip` → IP\n"
            "`discord` → Discord"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


if not TOKEN:
    raise RuntimeError(
        "Falta la variable TOKEN_DISCORD en Railway."
    )


bot.run(TOKEN)

