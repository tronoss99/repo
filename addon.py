import sys
import urllib.parse
import re
import xbmcplugin
import xbmcgui
import xbmc
import requests
import xbmcvfs
import os
import json
import base64
import hashlib
import hmac

addon_handle = int(sys.argv[1])
base_url = sys.argv[0]

ICON_PATH = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/icono.png')
FANART_PATH = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/resources/fanart.jpg')
CREDENTIALS_FILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.tronosstv/credentials.json')
SECRET_KEY = "c0mpl3xS3cur3K3y"
REMOTE_STATUS_URL = "https://raw.githubusercontent.com/tronoss99/repo/main/status.json"
UPDATE_URL = "https://raw.githubusercontent.com/tronoss99/repo/main/addon.py"
ACESTREAM_URL = "https://ipfs.io/ipns/elcano.top"

def to_utf8(text):
    if isinstance(text, str):
        return text.encode('utf-8', 'ignore').decode('utf-8')
    return text

def check_remote_status():
    try:
        response = requests.get(REMOTE_STATUS_URL)
        if response.status_code == 200:
            status_data = response.json()
            if status_data.get("status") == "mantenimiento":
                xbmcgui.Dialog().ok(
                    to_utf8("Mantenimiento"),
                    to_utf8(status_data.get("message", "El addon esta en mantenimiento."))
                )
                return False  
        return True
    except Exception as e:
        xbmcgui.Dialog().notification(
            to_utf8("Error"),
            to_utf8(f"No se pudo verificar el estado remoto: {e}"),
            xbmcgui.NOTIFICATION_ERROR
        )
        return True

def update_addon_script():
    try:
        response = requests.get(UPDATE_URL)
        if response.status_code == 200:
            temp_path = xbmcvfs.translatePath('special://temp/addon_updated.py')
            addon_path = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/addon.py')

            with open(temp_path, 'wb') as f:
                f.write(response.content)

            os.replace(temp_path, addon_path)

            xbmcgui.Dialog().notification(
                "Actualización",
                "El addon se ha actualizado. Reiniciando...",
                xbmcgui.NOTIFICATION_INFO
            )
            xbmc.executebuiltin("Container.Refresh()") 
            xbmc.executebuiltin("ReloadSkin()") 
        else:
            xbmcgui.Dialog().notification(
                "Error",
                f"No se pudo actualizar: HTTP {response.status_code}",
                xbmcgui.NOTIFICATION_ERROR
            )
    except Exception as e:
        xbmcgui.Dialog().notification(
            "Error",
            f"Fallo al actualizar: {str(e)}",
            xbmcgui.NOTIFICATION_ERROR
        )


def obfuscate_credentials(username, password):
    combined = f"{username}:{password}".encode('utf-8')
    hmac_digest = hmac.new(SECRET_KEY.encode('utf-8'), combined, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(hmac_digest).decode('utf-8')

def save_credentials(username, password):
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    obfuscated = obfuscate_credentials(username, password)
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump({"auth": obfuscated}, f)

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            return data.get("auth")
    return None

def prompt_for_credentials():
    keyboard = xbmcgui.Dialog()
    username = to_utf8(keyboard.input(to_utf8("Introduce el usuario"), type=xbmcgui.INPUT_ALPHANUM))
    if not username:
        return None, None
    password = to_utf8(keyboard.input(to_utf8("Introduce la contrasena"), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.PASSWORD_VERIFY))
    if not password:
        return None, None
    return username, password

def check_credentials():
    stored_auth = load_credentials()
    correct_auth = obfuscate_credentials("tronoss", "tronoss1234")
    if stored_auth == correct_auth:
        return True

    xbmcgui.Dialog().notification(to_utf8("Inicio de sesion"), to_utf8("Por favor, inicia sesion"), xbmcgui.NOTIFICATION_INFO)
    while True:
        username, password = prompt_for_credentials()
        if obfuscate_credentials(username, password) == correct_auth:
            save_credentials(username, password)
            xbmcgui.Dialog().notification(to_utf8("Exito"), to_utf8("Inicio de sesion correcto"), xbmcgui.NOTIFICATION_INFO)
            return True
        else:
            xbmcgui.Dialog().notification(to_utf8("Error"), to_utf8("Usuario o contrasena incorrectos"), xbmcgui.NOTIFICATION_ERROR)

def get_page_content(url):
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        else:
            xbmcgui.Dialog().notification(to_utf8("Error"), to_utf8(f"HTTP {response.status_code}"), xbmcgui.NOTIFICATION_ERROR)
            return ""
    except Exception as e:
        xbmcgui.Dialog().notification(to_utf8("Error"), to_utf8(str(e)), xbmcgui.NOTIFICATION_ERROR)
        return ""

def extract_acestream_links(content):
    channels = []
    name_pattern = r'"name":\s*"([^"]+)"'
    full_pattern = r'"name":\s*"([^"]+)".*?"url":\s*"acestream://([a-fA-F0-9]+)"'
    all_names = re.findall(name_pattern, content)
    full_matches = re.findall(full_pattern, content)
    links_dict = {name.strip(): f"acestream://{channel_id.strip()}" for name, channel_id in full_matches}

    for name in all_names:
        name = name.strip()
        link = links_dict.get(name, None)  
        channels.append((to_utf8(name), link))  
    return sorted(channels, key=lambda x: x[0].lower())

def build_url(query):
    return f"{base_url}?{urllib.parse.urlencode(query)}"

def list_channels():
    content = get_page_content(ACESTREAM_URL)
    if not content:
        xbmcplugin.endOfDirectory(addon_handle)
        return

    channels = extract_acestream_links(content)
    if not channels:
        xbmcgui.Dialog().notification(to_utf8("Error"), to_utf8("No se encontraron canales"), xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(addon_handle)
        return

    for name, channel_id in channels:
        url = build_url({"action": "play", "id": channel_id}) if channel_id else ""
        list_item = xbmcgui.ListItem(to_utf8(name))
        list_item.setInfo("video", {"title": to_utf8(name)})
        list_item.setProperty("IsPlayable", "true")
        list_item.setArt({
            'icon': ICON_PATH,
            'thumb': ICON_PATH,
            'fanart': FANART_PATH
        })
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)

def play_channel(channel_id):
    if not channel_id:
        xbmcgui.Dialog().notification(to_utf8("Error"), to_utf8("Canal sin ID disponible"), xbmcgui.NOTIFICATION_ERROR)
        return

    horus_command = f'RunPlugin("plugin://script.module.horus/?action=play&id={channel_id}")'
    try:
        xbmc.executebuiltin(horus_command)
        xbmcgui.Dialog().notification(to_utf8("Horus"), to_utf8("Reproduciendo en AceStream Engine..."), xbmcgui.NOTIFICATION_INFO)
    except Exception as e:
        xbmcgui.Dialog().notification(to_utf8("Error"), to_utf8(f"No se pudo ejecutar Horus: {e}"), xbmcgui.NOTIFICATION_ERROR)

def router(args):
    action = args.get("action", [None])[0]
    channel_id = args.get("id", [None])[0]

    if action == "play" and channel_id:
        play_channel(channel_id)
    else:
        list_channels()

if __name__ == "__main__":
    update_addon_script()
    if not check_remote_status(): 
        xbmcplugin.endOfDirectory(addon_handle)  
    elif check_credentials():
        args = urllib.parse.parse_qs(sys.argv[2][1:])
        router(args)
    else:
        xbmcplugin.endOfDirectory(addon_handle)
