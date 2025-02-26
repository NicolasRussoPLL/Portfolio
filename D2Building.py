import discord
import logging
import os
import requests
from urllib.parse import urlencode
from urllib.parse import urlparse
from discord import app_commands
from discord.ui import View, Select
import time
import webserver

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
BUNGIE_TOKEN_URL = os.getenv("BUNGIE_TOKEN_URL", "https://www.bungie.net/platform/app/oauth/token/")
BUNGIE_BASE_URL = os.getenv("BUNGIE_BASE_URL", "https://www.bungie.net/Platform")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "MTM0MDAyNjAyNTY4MTIyNzg3Nw.GuIfAw.lfm4sM_andC6ZLGOOU15eMDzgTiEgEO4L8ocT4")

HEADERS = {"X-API-KEY": BUNGIE_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}

# Diccionario con información meta para cada actividad (enlaces y descripción)
META_DATA = {
    "trials": {
        "title": "Pruebas de Osiris",
        "description": "Descubre las builds más populares en Pruebas de Osiris.",
        "dim_link": "https://destinyitemmanager.com/?mode=osiris",
        "lightgg_link": "https://destinytrialsreport.com/weeks"
    },
    "nightfall": {
        "title": "Asaltos del Ocaso y Endgame",
        "description": "Builds y tendencias en Nightfall y Endgame",
        "dim_link": "https://destinyitemmanager.com/?mode=nightfall",
        "lightgg_link": "https://www.light.gg/loadouts/stats/?f=11(26)"
    },
    "all": {
        "title": "Builds diversas",
        "description": "Builds para todo tipo de juego.",
        "dim_link": "https://destinyitemmanager.com/?mode=raid",
        "lightgg_link": "https://www.light.gg/loadouts/db/"
    }
}

user_tokens = {}  # Diccionario temporal {user_id: {"access_token": "...", "refresh_token": "..."}}


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
    await interaction.response.defer(ephemeral=True)  # Evita timeout

    if not code:
        await interaction.followup.send("🔴 Error: Por favor, proporciona el código de autorización.", ephemeral=True)
        return
    
    # Datos necesarios para hacer la solicitud de intercambio del código por el token
    data = {
        "client_id": BUNGIE_CLIENT_ID,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": BUNGIE_REDIRECT_URL
    }

    # Realiza la solicitud POST para obtener el token de acceso
    response = requests.post(BUNGIE_TOKEN_URL, data=data, headers=HEADERS)

    try:
        response_data = response.json()
    except ValueError as e:
        await interaction.followup.send(f"❌ Error al procesar la respuesta JSON: {str(e)}", ephemeral=True)
        return

    if response.status_code == 200 and "access_token" in response_data:
        access_token = response_data.get("access_token")
        refresh_token = response_data.get("refresh_token", "No disponible")
        membership_id = response_data.get("membership_id", "Desconocido")  
        
        user_tokens[interaction.user.id] = {
            "access_token": response_data["access_token"],
            "refresh_token": response_data["refresh_token"],
            "expires_in": time.time() + response_data["expires_in"]
        }


        await interaction.followup.send(f"✅ Autenticación exitosa. Token guardado.\nTu ID de Bungie: {membership_id}", ephemeral=True)

    
    else:
        error_msg = response_data.get("error_description", "Error desconocido.")
        await interaction.followup.send(f"❌ Error en la autenticación: {error_msg}", ephemeral=True)

@tree.command(name="stat", description="Muestra estadísticas generales del jugador autenticado")
async def stat(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in user_tokens:
        await interaction.response.send_message("🔴 Error: No estás autenticado. Usa /get_token primero.", ephemeral=True)
        return
    
    tokens = user_tokens[user_id]
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "X-API-Key": BUNGIE_API_KEY}
    
    # Obtener el membership_id del usuario
    profile_url = f"{BUNGIE_API_BASE}/Destiny2/254/Profile/{user_id}/?components=100"
    profile_response = requests.get(profile_url, headers=headers)
    profile_data = profile_response.json()
    
    if "ErrorCode" in profile_data and profile_data["ErrorCode"] != 1:
        await interaction.response.send_message("❌ Error al obtener el perfil. Intenta autenticarte nuevamente.", ephemeral=True)
        return
    
    membership_id = profile_data["Response"]["profile"]["data"]["userInfo"]["membershipId"]
    membership_type = profile_data["Response"]["profile"]["data"]["userInfo"]["membershipType"]
    
    # Obtener estadísticas del usuario
    stats_url = f"{BUNGIE_API_BASE}/Destiny2/{membership_type}/Account/{membership_id}/Stats/"
    stats_response = requests.get(stats_url, headers=headers)
    stats_data = stats_response.json()
    
    if "ErrorCode" in stats_data and stats_data["ErrorCode"] != 1:
        await interaction.response.send_message("❌ Error al obtener estadísticas.", ephemeral=True)
        return
    
    # Extraer datos relevantes
    all_time_stats = stats_data["Response"]["mergedAllCharacters"]["results"]["allPvE"]["allTime"]
    kills = all_time_stats["kills"]["basic"]["value"]
    kd_ratio = all_time_stats["killsDeathsRatio"]["basic"]["value"]
    pvp_wins = stats_data["Response"]["mergedAllCharacters"]["results"]["allPvP"]["allTime"]["activitiesWon"]["basic"]["value"]
    raids_completed = stats_data["Response"]["mergedAllCharacters"]["results"]["raid"]["allTime"]["activitiesCleared"]["basic"]["value"]
    
    # Responder con las estadísticas
    embed = discord.Embed(title="📊 Tus estadísticas generales", color=discord.Color.blue())
    embed.add_field(name="🔹 Kills Totales", value=f"{kills:,}", inline=False)
    embed.add_field(name="🔹 K/D Ratio", value=f"{kd_ratio:.2f}", inline=False)
    embed.add_field(name="🔹 Victorias en PvP", value=f"{pvp_wins:,}", inline=False)
    embed.add_field(name="🔹 Raids Completadas", value=f"{raids_completed:,}", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="meta", description="Muestra las builds más usadas en diferentes actividades")
async def meta(interaction: discord.Interaction):
    class ActivitySelect(View):
        def __init__(self):
            super().__init__()
            self.add_item(ActivityDropdown())

    class ActivityDropdown(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Pruebas de Osiris", value="trials"),
                discord.SelectOption(label="Asaltos del Ocaso y Endgame", value="nightfall"),
                discord.SelectOption(label="Todo tipo de juego", value="all")
            ]
            super().__init__(placeholder="Elige una actividad", options=options)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            activity = self.values[0]
            data = META_DATA.get(activity)
            if data:
                embed = discord.Embed(
                    title=data["title"],
                    description=data["description"],
                    color=discord.Color.blue()
                )
                embed.add_field(name="DIM", value=f"[Ver en DIM]({data['dim_link']})", inline=True)
                embed.add_field(name="Light.gg", value=f"[Ver en Light.gg]({data['lightgg_link']})", inline=True)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("No se encontró información para esta actividad.")

    await interaction.response.send_message("Selecciona una actividad para ver las builds meta:", view=ActivitySelect())

# 📌 Ejecutar el bot
webserver.keep_alive()
bot.run(DISCORD_TOKEN)
