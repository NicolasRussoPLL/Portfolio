import discord
import logging
import os
import requests
from urllib.parse import urlencode
from urllib.parse import urlparse

# 📌 Configurar el logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
    handlers=[
        logging.FileHandler(filename="Builder_bot-log.txt", encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("discord")  # Logger de Discord
logger_bot = logging.getLogger("D2Building")  # Logger del bot

# 📌 Configurar Intents
intents = discord.Intents.all()  # Activa todos los intents para máxima compatibilidad
bot = discord.Client(intents=intents)  # Cliente de Discord
tree = discord.app_commands.CommandTree(bot)  # Sistema de Slash Commands

BUNGIE_API_KEY = os.getenv("BUNGIE_API_KEY", "46f5b80f36584f779f56017a4b76a647")
BUNGIE_REDIRECT_URL = os.getenv("BUNGIE_REDIRECT_URL", "https://oauth.pstmn.io/v1/browser-callback")
BUNGIE_CLIENT_ID = os.getenv("BUNGIE_CLIENT_ID", "49012")
BUNGIE_AUTH_URL = os.getenv("BUNGIE_AUTH_URL", "https://www.bungie.net/es/OAuth/Authorize")
BUNGIE_TOKEN_URL = os.getenv("BUNGIE_TOKEN_URL", "https://www.bungie.net/Platform/Destiny2/Auth/Token")

HEADERS = {"X-API-KEY": BUNGIE_API_KEY}



# 📌 Evento cuando el bot está listo
@bot.event
async def on_ready():
    try:
        await tree.sync()  # Sincroniza los Slash Commands con Discord
        logger.info(f"✅ Bot conectado como {bot.user}")
        logger.info("✅ Slash Commands sincronizados correctamente.")
    except Exception as e:
        logger.error(f"⚠️ Error al sincronizar comandos: {e}")

# 📌 Evento para errores en comandos
@bot.event
async def on_error(event, *args, **kwargs):
    logger_bot.error(f"⚠️ Error en evento {event}: {args} - {kwargs}")

# 📌 Slash Command de prueba
@tree.command(name="ping", description="Muestra la latencia del bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latencia: {round(bot.latency * 1000)}ms")

@tree.command(name="auth", description="Autoriza el bot para acceder a datos de Bungie")
async def auth(interaction: discord.Interaction):
    params = {
        "client_id": BUNGIE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": BUNGIE_REDIRECT_URL,
    }
    auth_link = f"{BUNGIE_AUTH_URL}?{urlencode(params)}"
    await interaction.response.send_message(f"🔐 Para autorizar el bot, haz clic en el siguiente enlace:\n{auth_link}", ephemeral=True)

@tree.command(name="get_token", description="Proporciona el código de autorización para obtener el token de acceso")
async def get_token(interaction: discord.Interaction, code: str):
    # El 'code' es el parámetro que el usuario deberá copiar desde la URL de redirección y enviar al bot
    if not code:
        await interaction.response.send_message("🔴 Error: Por favor, proporciona el código de autorización.", ephemeral=True)
        return

    # Datos necesarios para hacer la solicitud de intercambio del código por el token
    data = {
        "client_id": BUNGIE_CLIENT_ID,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": BUNGIE_REDIRECT_URL
    }

    # Realiza la solicitud POST para obtener el token de acceso
    response = requests.post(BUNGIE_TOKEN_URL, data=data)
    response_data = response.json()

    if response.status_code == 200:
        access_token = response_data["access_token"]
        refresh_token = response_data["refresh_token"]

        # Puedes almacenar el token de acceso de manera segura aquí
        await interaction.response.send_message(f"🔑 Token de acceso obtenido con éxito:\n{access_token}", ephemeral=True) #Por cambiar
    else:
        await interaction.response.send_message(f"❌ Error al obtener el token: {response_data}", ephemeral=True)


# 📌 Ejecutar el bot
TOKEN = "MTM0MTIzNTUxMDQ3MDkwNTkxNw.GMwbzL.0YnfAgK8DhXK5vWiBwJJ_jGVbc_3oxvev_iUHU"  # Reemplaza con tu token de bot / token de prueba
bot.run(TOKEN)
