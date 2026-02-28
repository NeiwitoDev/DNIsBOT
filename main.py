import os
import discord
import requests
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime
from typing import Literal

# ===============================
# CONFIG
# ===============================
load_dotenv()
TOKEN = os.getenv("TOKEN")

CANAL_SOLICITUDES_DNI = 1469498959004172388
CANAL_BIENVENIDA = 1466215432418492416
CANAL_COMANDOS = 1466231866041307187

# Canales recomendados
CANALES_RECOMENDADOS = [
    1466215119372554260, 
    1466216894242492436, 
    1466229592858558565, 
    1466240677607244012
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

dni_db = {}

# ===============================
# FUNCIONES AUXILIARES
# ===============================

def calcular_edad(fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        return edad
    except:
        return None


def obtener_usuario_roblox(username):
    # Obtener ID y datos básicos
    url_user = "https://users.roblox.com/v1/usernames/users"
    data_user = {"usernames": [username], "excludeBannedUsers": False}
    r_user = requests.post(url_user, json=data_user)

    if r_user.status_code != 200:
        return None

    res_user = r_user.json()["data"]
    if not res_user:
        return None

    user_id = res_user[0]["id"]
    display_name = res_user[0]["displayName"]
    name = res_user[0]["name"]

    # Obtener descripción (bio)
    url_info = f"https://users.roblox.com/v1/users/{user_id}"
    r_info = requests.get(url_info)
    description = "Sin descripción"
    if r_info.status_code == 200:
        description = r_info.json().get("description", "Sin descripción") or "Sin descripción"

    # Obtener Avatar
    avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    avatar_data = requests.get(avatar_url).json()
    avatar = avatar_data["data"][0]["imageUrl"]

    return {
        "id": user_id,
        "name": name,
        "displayName": display_name,
        "avatar": avatar,
        "description": description
    }

# ===============================
# SLASH: CREAR DNI
# ===============================

@tree.command(name="crear-dni", description="Solicitar creación de DNI")
@app_commands.describe(
    nacionalidad="Selecciona tu nacionalidad",
    fecha_nacimiento="Formato DD/MM/AAAA"
)
async def crear_dni(
    interaction: discord.Interaction,
    nombre: str,
    apellido: str,
    nacionalidad: Literal["Argentino", "Cordobes", "Paraguayo", "Chileno", "Venezolano"],
    fecha_nacimiento: str,
    roblox_user: str
):
    edad = calcular_edad(fecha_nacimiento)

    if edad is None or edad > 100 or edad < 0:
        await interaction.response.send_message(
            "❌ Fecha inválida. Usa formato DD/MM/AAAA y una fecha real.",
            ephemeral=True
        )
        return

    roblox_data = obtener_usuario_roblox(roblox_user)

    if not roblox_data:
        await interaction.response.send_message(
            "❌ Usuario de Roblox no encontrado.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔎 ¿Este es tu perfil?",
        description=f"**Descripción:**\n{roblox_data['description']}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Username", value=roblox_data["name"], inline=True)
    embed.add_field(name="Display Name", value=roblox_data["displayName"], inline=True)
    embed.add_field(name="Roblox ID", value=str(roblox_data["id"]), inline=True)
    embed.set_thumbnail(url=roblox_data["avatar"])

    # ===============================
    # VIEW CONFIRMAR PERFIL
    # ===============================

    class ConfirmarPerfil(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)

        @discord.ui.button(label="Si, Es mi perfil", style=discord.ButtonStyle.green)
        async def confirmar(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            if interaction_btn.user != interaction.user:
                await interaction_btn.response.send_message("❌ No es tu solicitud.", ephemeral=True)
                return

            solicitud = {
                "nombre": nombre,
                "apellido": apellido,
                "edad": edad,
                "fecha": fecha_nacimiento,
                "nacionalidad": nacionalidad,
                "roblox": roblox_data["displayName"],
                "roblox_avatar": roblox_data["avatar"],
                "user_id": interaction.user.id
            }

            canal = bot.get_channel(CANAL_SOLICITUDES_DNI)
            if not canal:
                await interaction_btn.response.send_message("❌ Error: Canal de solicitudes no encontrado.", ephemeral=True)
                return

            embed_solicitud = discord.Embed(
                title="📄 Nueva Solicitud DNI",
                color=discord.Color.blue()
            )
            embed_solicitud.add_field(name="Usuario Discord", value=interaction.user.mention, inline=False)
            embed_solicitud.add_field(name="Nombre Completo", value=f"{nombre} {apellido}", inline=True)
            embed_solicitud.add_field(name="Edad", value=f"{edad} años", inline=True)
            embed_solicitud.add_field(name="Nacionalidad", value=nacionalidad, inline=True)
            embed_solicitud.add_field(name="Roblox", value=f"{roblox_data['displayName']} ({roblox_data['id']})", inline=False)
            embed_solicitud.set_thumbnail(url=roblox_data["avatar"])

            class AdminView(discord.ui.View):
                @discord.ui.button(label="Aceptar", style=discord.ButtonStyle.green)
                async def aceptar(self, admin_inter: discord.Interaction, button: discord.ui.Button):
                    dni_db[interaction.user.id] = solicitud
                    try:
                        await interaction.user.send(f"✅ Tu DNI ha sido **emitido**. Ya puedes usarlo en el servidor.")
                    except:
                        pass
                    await admin_inter.response.edit_message(content=f"✅ DNI ACEPTADO por {admin_inter.user.mention}", view=None)

                @discord.ui.button(label="Denegar", style=discord.ButtonStyle.red)
                async def denegar(self, admin_inter: discord.Interaction, button: discord.ui.Button):
                    try:
                        await interaction.user.send(f"❌ Tu solicitud de DNI ha sido **denegada**.")
                    except:
                        pass
                    await admin_inter.response.edit_message(content=f"❌ DNI DENEGADO por {admin_inter.user.mention}", view=None)

            await canal.send(embed=embed_solicitud, view=AdminView())
            await interaction_btn.response.edit_message(content="✅ Solicitud enviada correctamente. Espera la respuesta en tus MD.", embed=None, view=None)

        @discord.ui.button(label="No, Cambiar", style=discord.ButtonStyle.red)
        async def cancelar(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            if interaction_btn.user != interaction.user:
                await interaction_btn.response.send_message("❌ No es tu solicitud.", ephemeral=True)
                return
            await interaction_btn.response.edit_message(content="Usa nuevamente `/crear-dni` con los datos correctos.", embed=None, view=None)

    await interaction.response.send_message(
        embed=embed,
        view=ConfirmarPerfil(),
        ephemeral=True
    )

# ===============================
# SLASH: VER DNI
# ===============================

@tree.command(name="ver-dni", description="Ver tu DNI aprobado")
async def ver_dni(interaction: discord.Interaction):

    if interaction.channel.id != CANAL_COMANDOS:
        await interaction.response.send_message(
            "❌ Usa este comando en el canal comandos.",
            ephemeral=True
        )
        return

    if interaction.user.id not in dni_db:
        await interaction.response.send_message(
            "❌ No tienes DNI aprobado.",
            ephemeral=True
        )
        return

    data = dni_db[interaction.user.id]

    embed = discord.Embed(
        title="💳 REGISTRO CIVIL - DNI VIRTUAL",
        description="Este documento certifica la identidad del ciudadano en el entorno virtual.",
        color=0x2b2d31  # Color oscuro elegante
    )
    embed.set_thumbnail(url=data.get("roblox_avatar", ""))
    
    # Diseño de campos con separadores y emojis
    embed.add_field(name="👤 DATOS PERSONALES", value=f"**Nombre:** {data['nombre']}\n**Apellido:** {data['apellido']}\n**Edad:** {data['edad']} años", inline=True)
    embed.add_field(name="🌎 ORIGEN", value=f"**Nacionalidad:** {data['nacionalidad']}", inline=True)
    
    # Línea divisoria invisible usando campos vacíos o formato
    embed.add_field(name="🎮 IDENTIDAD VIRTUAL", value=f"**Roblox:** {data['roblox']}\n**ID:** `{interaction.user.id}`", inline=False)
    
    # Firma con estilo
    embed.add_field(name="🖋️ FIRMA DEL CIUDADANO", value=f"*{data['nombre']} {data['apellido']}*", inline=False)

    embed.set_footer(text=f"EMITIDO EL: {datetime.now().strftime('%d/%m/%Y')} | VALIDEZ PERMANENTE", icon_url=bot.user.display_avatar.url)
    
    # Imagen decorativa si existiera, o simplemente un separador visual
    # embed.set_image(url="...") 

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ===============================
# EVENTOS
# ===============================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Sistema DNI activo como {bot.user}")

bot.run(TOKEN)
