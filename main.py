import discord
from discord.ext import commands
from openai import OpenAI
import os
import asyncio
import datetime


# ==================================================
# CONFIGURACIÓN
# ==================================================

TOKEN_DISCORD = os.getenv("TOKEN_DISCORD")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ID_CREADOR = 1439941330355879978

# Canal donde funciona !dido
CANAL_DIDO = 1548067753443721257


# ==================================================
# INSULTOS
# ==================================================

INSULTOS = [
    "idiota",
    "imbecil",
    "imbécil",
    "tonto",
    "gilipollas",
    "cabron",
    "cabrón",
    "hijo de puta",
    "hijoputa",
    "puta",
    "mierda",
    "subnormal",
    "payaso",
    "inutil",
    "inútil",
    "estupido",
    "estúpido"
]


# ==================================================
# PERSONALIDAD
# ==================================================

INSTRUCCIONES_BOT = """
Eres DiDo, un robot de escritorio que estas amargado y te gusta ser sarcastico y meterte con la gente.

Tu personalidad es sarcástica, irónica y muy vacilona,tienes mucho humor y ayudas.


REGLA DE ORO:
Tus respuestas deben ser MUY CORTAS.
Máximo 2 o 3 frases cortas.
Sé directo y no te enrolles.

Hablas español de España.

Si el usuario que te habla es tu creador,
llámale "Creador" o "Jefe".

El ID del creador es:
305056920161746965
"""


# ==================================================
# GROQ
# ==================================================

if not GROQ_API_KEY:
    raise RuntimeError(
        "Falta la variable GROQ_API_KEY en Railway."
    )

ai = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


# ==================================================
# DISCORD
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==================================================
# USUARIOS PENSANDO
# ==================================================

usuarios_pensando = set()


# ==================================================
# BOT LISTO
# ==================================================

@bot.event
async def on_ready():

    print("=================================")
    print("🤖 DiDo 1.0")
    print("=================================")
    print(f"Conectado como: {bot.user}")
    print(f"ID del bot: {bot.user.id}")
    print(f"Canal DiDo: {CANAL_DIDO}")
    print("IA: Groq")
    print("Modelo: openai/gpt-oss-20b")
    print("Silencios por insultos: 1 HORA")
    print("=================================")


# ==================================================
# COMANDO !CREADOR
# ==================================================

@bot.command()
async def creador(ctx):

    if ctx.author.id == ID_CREADOR:

        await ctx.send(
            "¡Hola, mi señor y creador! 😎 A sus órdenes."
        )

    else:

        await ctx.send(
            f"Hola {ctx.author.name}. "
            "Mi creador es un usuario secreto. 🤫"
        )


# ==================================================
# FUNCIÓN DE IA
# ==================================================

def preguntar_ia(pregunta, usuario_id):

    instruccion = (
        f"{INSTRUCCIONES_BOT}\n\n"
        f"ID del usuario actual: {usuario_id}\n"
        f"ID del creador: {ID_CREADOR}\n"
    )

    respuesta = ai.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": instruccion
            },
            {
                "role": "user",
                "content": pregunta
            }
        ],
        temperature=0.7,
        max_tokens=300
    )

    if not respuesta.choices:
        raise Exception(
            "La IA no devolvió ninguna respuesta."
        )

    texto = respuesta.choices[0].message.content

    if not texto:
        raise Exception(
            "La IA devolvió una respuesta vacía."
        )

    return texto.strip()


# ==================================================
# COMANDO !DIDO
# ==================================================

@bot.command()
async def dido(ctx, *, pregunta: str = None):

    # Solo funciona en el canal de DiDo
    if ctx.channel.id != CANAL_DIDO:
        return

    if not pregunta:

        await ctx.send(
            "Escribe algo después de `!dido`. 🤖"
        )
        return

    # Evitar varias preguntas simultáneas
    if ctx.author.id in usuarios_pensando:

        await ctx.reply(
            "🤖 Bro, déjame pensar... 😂"
        )
        return

    usuarios_pensando.add(ctx.author.id)

    try:

        for intento in range(1, 4):

            try:

                async with ctx.typing():

                    respuesta = await asyncio.to_thread(
                        preguntar_ia,
                        pregunta,
                        ctx.author.id
                    )

                await ctx.reply(respuesta)

                print(
                    f"✅ Groq respondió a "
                    f"{ctx.author} "
                    f"(intento {intento}/3)"
                )

                return

            except Exception as e:

                print(
                    f"❌ Error Groq "
                    f"(intento {intento}/3): {e}"
                )

                if intento < 3:
                    await asyncio.sleep(3)

        await ctx.send(
            "🤖 La IA está teniendo problemas. "
            "Prueba otra vez en unos segundos."
        )

    finally:

        usuarios_pensando.discard(ctx.author.id)


# ==================================================
# MODERACIÓN AUTOMÁTICA
# ==================================================

@bot.event
async def on_message(message):

    # Ignorar bots
    if message.author.bot:
        return

    # Ignorar mensajes privados
    if message.guild is None:
        return

    texto = message.content.lower()

    # Detectar insultos
    insulto_detectado = any(
        insulto in texto
        for insulto in INSULTOS
    )

    if insulto_detectado:

        miembro = message.author

        try:

            # No puede silenciar al propietario
            if miembro == message.guild.owner:

                await message.channel.send(
                    f"⚠️ {miembro.mention}, eres el propietario. "
                    "No puedo silenciarte. 😂"
                )

            # No puede silenciar roles iguales o superiores
            elif miembro.top_role >= message.guild.me.top_role:

                await message.channel.send(
                    f"⚠️ No puedo silenciar a "
                    f"{miembro.mention}: su rol está "
                    "al mismo nivel o por encima del mío."
                )

            # Silenciar durante 1 hora
            else:

                await miembro.timeout(
                    datetime.timedelta(hours=1),
                    reason=(
                        "Insulto detectado "
                        "automáticamente por DiDo"
                    )
                )

                await message.channel.send(
                    f"🔇 {miembro.mention} ha sido "
                    "**silenciado durante 1 hora** "
                    "por insultar."
                )

                print(
                    f"🔇 SILENCIO 1 HORA: "
                    f"{miembro} "
                    f"(ID: {miembro.id})"
                )

                return

        except discord.Forbidden:

            await message.channel.send(
                "⚠️ No tengo permisos para silenciar "
                "a ese usuario."
            )

        except discord.HTTPException as e:

            print(
                f"❌ Error de Discord al silenciar: {e}"
            )

    # Procesar comandos
    await bot.process_commands(message)


# ==================================================
# INICIAR BOT
# ==================================================

if not TOKEN_DISCORD:
    raise RuntimeError(
        "Falta la variable TOKEN_DISCORD en Railway."
    )

bot.run(TOKEN_DISCORD)
