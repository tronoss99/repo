# -*- coding: utf-8 -*-
import sys
import os
import urllib.parse
import re
import shutil
import zipfile
import xbmcplugin
import xbmcgui
import xbmcvfs
import xbmc
import hashlib
from datetime import datetime
import json
import uuid
import requests

def list_dependencies():
    return [
        {
            "name": "requests",
            "url": "https://tronoss99.github.io/repo/addons/dependencias/requests.zip"
        },
        {
            "name": "mysql-connector-python",
            "url": "https://tronoss99.github.io/repo/addons/dependencias/mysql-connector-python.zip"
        }
    ]

def download_and_unzip_kodi(url, dependency_name, output_dir):
    try:
        temp_path = xbmcvfs.translatePath('special://temp/')
        local_path = os.path.join(temp_path, f"{dependency_name}.zip")

        xbmc.log(f"Descargando {dependency_name} desde {url}...", level=xbmc.LOGINFO)
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        xbmc.log(f"Archivo descargado: {local_path}", level=xbmc.LOGINFO)

        if zipfile.is_zipfile(local_path):
            with zipfile.ZipFile(local_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            xbmc.log(f"Archivo {dependency_name} descomprimido en {output_dir}", level=xbmc.LOGINFO)
        else:
            xbmcgui.Dialog().notification("Error", "Archivo no soportado", xbmcgui.NOTIFICATION_ERROR)
            return False

        os.remove(local_path)
        xbmc.log(f"Archivo temporal eliminado: {local_path}", level=xbmc.LOGINFO)
        return True
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().notification("Error", f"Error en la descarga: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"Error en la descarga: {e}", level=xbmc.LOGERROR)
        return False

output_dir = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/resources/lib/')
dependencies = list_dependencies()

for dependency in dependencies:
    dependency_folder = os.path.join(output_dir, dependency["name"])
    if os.path.exists(dependency_folder):
        sys.path.insert(0, dependency_folder)
        xbmc.log(f"Ruta añadida para {dependency['name']}: {dependency_folder}", level=xbmc.LOGINFO)
    else:
        xbmc.log(f"No se encontró la dependencia {dependency['name']}. Intentando descargar...", level=xbmc.LOGINFO)
        if download_and_unzip_kodi(dependency["url"], dependency["name"], output_dir):
            sys.path.insert(0, dependency_folder)
            xbmc.log(f"Dependencia {dependency['name']} instalada y ruta añadida.", level=xbmc.LOGINFO)
        else:
            xbmcgui.Dialog().notification("Error", f"No se pudo instalar la dependencia {dependency['name']}", xbmcgui.NOTIFICATION_ERROR)
            xbmc.log(f"No se pudo instalar la dependencia {dependency['name']}.", level=xbmc.LOGERROR)
            sys.exit(1)

addon_lib_path = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/resources/lib/')
mysql_connector_path = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/resources/lib/mysql-connector-python/')

if addon_lib_path not in sys.path:
    sys.path.insert(0, addon_lib_path)

if mysql_connector_path not in sys.path:
    sys.path.insert(0, mysql_connector_path)

try:
    import mysql.connector
    xbmc.log("mysql.connector importado correctamente.", level=xbmc.LOGINFO)
except ImportError as e:
    xbmcgui.Dialog().notification("Error", f"No se pudo importar mysql.connector: {e}", xbmcgui.NOTIFICATION_ERROR)
    xbmc.log(f"Error al importar mysql.connector: {e}", level=xbmc.LOGERROR)
    sys.exit(1)

DB_HOST = "btu73hhmyjd94a9udngy-mysql.services.clever-cloud.com"
DB_NAME = "btu73hhmyjd94a9udngy"
DB_USER = "uuyxjmtlimnea2uo"
DB_PASSWORD = "vfymuvMZIAXLks0xAyVQ"
DB_PORT = 3306

addon_handle = int(sys.argv[1])
base_url = sys.argv[0]

ICON_PATH = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/icono.png')
FANART_PATH = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/resources/fanart.jpg')
CREDENTIALS_FILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.tronosstv/credentials.json')
DEVICE_ID_FILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.tronosstv/device_id.json')
REMOTE_STATUS_URL = "https://raw.githubusercontent.com/tronoss99/repo/main/status.json"
UPDATE_URL = "https://raw.githubusercontent.com/tronoss99/repo/main/main.py"
DEPENDENCIES_URL = "https://tronoss99.github.io/repo/addons/dependencias"
DEPENDENCIES_LIST = ["mysql-connector-python", "requests"]
TARGET_DIRECTORY = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/resources/lib/')
ACESTREAM_URL = "https://ipfs.io/ipns/elcano.top"
EVENTS_URL = "http://141.145.210.168"

user_id_global = None 
is_logged_in = False 
addon_active = False 
device_marked_active = False
current_device_id = None

def connect_db():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        return connection
    except mysql.connector.Error as e:
        xbmcgui.Dialog().notification("Error DB", f"No se pudo conectar: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"Error en la conexión a la base de datos: {e}", level=xbmc.LOGERROR)
        return None

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
                    to_utf8(status_data.get("message", "El addon está en mantenimiento."))
                )
                return False  
        return True
    except Exception as e:
        xbmcgui.Dialog().notification(
            to_utf8("Error"),
            to_utf8(f"No se pudo verificar el estado remoto: {e}"),
            xbmcgui.NOTIFICATION_ERROR
        )
        xbmc.log(f"Error al verificar el estado remoto: {e}", level=xbmc.LOGERROR)
        return True

def save_credentials(username, password):
    if username and password: 
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        credentials = {"username": username, "password": password}
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f)
        xbmc.log(f"Credenciales guardadas para el usuario {username}.", level=xbmc.LOGINFO)

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            try:
                credentials = json.load(f)
                if "username" in credentials and "password" in credentials:
                    xbmc.log(f"Credenciales cargadas para el usuario {credentials['username']}.", level=xbmc.LOGINFO)
                    return credentials
            except json.JSONDecodeError:
                xbmc.log("Error leyendo el archivo de credenciales. Eliminando archivo corrupto.", level=xbmc.LOGWARNING)
                os.remove(CREDENTIALS_FILE)
    return None

def prompt_for_credentials():
    keyboard = xbmcgui.Dialog()
    username = keyboard.input("Introduce el usuario", type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        return None, None
    password = keyboard.input("Introduce la contraseña", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.PASSWORD_VERIFY)
    if not password:
        return None, None
    return username, password

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def check_user(username, password):
    connection = connect_db()
    if not connection:
        return None
    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT users.*, plans.name AS plan_name FROM users JOIN plans ON users.plan_id = plans.id WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        if user and hash_password(password) == user['password_hash']:
            expiry_date = user.get('expiry_date')
            if expiry_date:
                if isinstance(expiry_date, str):
                    expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                current_date = datetime.now()
                if current_date > expiry_date:
                    xbmcgui.Dialog().notification(
                        "Cuenta Expirada",
                        "Tu cuenta ha expirado. Por favor, renueva tu suscripción.",
                        xbmcgui.NOTIFICATION_ERROR
                    )
                    xbmc.log(f"Cuenta del usuario {username} ha expirado el {expiry_date}.", level=xbmc.LOGINFO)
                    if os.path.exists(CREDENTIALS_FILE):
                        os.remove(CREDENTIALS_FILE)
                        xbmc.log(f"Archivo de credenciales eliminado para el usuario {username}.", level=xbmc.LOGINFO)
                    return None
            else:
                xbmc.log(f"Usuario {username} tiene una cuenta ilimitada.", level=xbmc.LOGINFO)
            
            if user['active_devices'] >= user['max_devices']:
                xbmcgui.Dialog().notification(
                    "Error",
                    "Dispositivos máximos alcanzados",
                    xbmcgui.NOTIFICATION_ERROR
                )
                xbmc.log(f"Usuario {username} ha alcanzado el número máximo de dispositivos.", level=xbmc.LOGINFO)
                return None

            user['plan_name'] = user.get('plan_name')
            user['expiry_date'] = expiry_date

            return user
        else:
            xbmcgui.Dialog().notification(
                "Error",
                "Usuario o contraseña incorrectos.",
                xbmcgui.NOTIFICATION_ERROR
            )
            xbmc.log(f"Intento de acceso fallido para el usuario {username}.", level=xbmc.LOGWARNING)
            return None
    except Exception as e:
        xbmcgui.Dialog().notification(
            "Error",
            f"Error al verificar el usuario: {e}",
            xbmcgui.NOTIFICATION_ERROR
        )
        xbmc.log(f"Error en check_user: {e}", level=xbmc.LOGERROR)
        return None
    finally:
        cursor.close()
        connection.close()

def show_account_info(user):
    plan_name = user.get('plan_name')
    expiry_date = user.get('expiry_date')
    max_devices = user.get('max_devices', 'N/A')  

    if plan_name:
        message = f"Plan: {plan_name}\nMáximo de dispositivos: {max_devices}"
        if expiry_date:
            if isinstance(expiry_date, str):
                expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
            formatted_date = expiry_date.strftime("%d/%m/%Y")
            message += f"\nExpira el: {formatted_date}"
        else:
            message += "\nExpiración: Ilimitada"
        
        xbmcgui.Dialog().notification(
            "Inicio de Sesión Exitoso",
            message,
            xbmcgui.NOTIFICATION_INFO,
            5000
        )
        xbmc.log(f"Información de cuenta mostrada para el usuario {user['username']}.", level=xbmc.LOGINFO)

def get_device_id():
    global current_device_id
    if current_device_id:  
        return current_device_id
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, 'r') as f:
            current_device_id = json.load(f).get("device_id")
            xbmc.log(f"ID de dispositivo cargado: {current_device_id}", level=xbmc.LOGINFO)
    else:
        current_device_id = str(uuid.uuid4())
        with open(DEVICE_ID_FILE, 'w') as f:
            json.dump({"device_id": current_device_id}, f)
        xbmc.log(f"Nuevo ID de dispositivo generado: {current_device_id}", level=xbmc.LOGINFO)
    return current_device_id

def update_active_devices(user_id, device_id, increment=True):
    connection = connect_db()
    if not connection:
        xbmc.log("No se pudo conectar a la base de datos", level=xbmc.LOGERROR)
        return False

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT device_id, active_devices FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            xbmc.log("No se encontró el usuario en la base de datos", level=xbmc.LOGERROR)
            return False

        current_device_ids = result[0] if result[0] else ""
        active_devices = result[1] if len(result) > 1 else 0
        device_list = current_device_ids.split(",") if current_device_ids else []

        if increment:
            if device_id in device_list:
                xbmc.log(f"Dispositivo ya activo: {device_id}", level=xbmc.LOGINFO)
                return True

            device_list.append(device_id)
            updated_device_ids = ",".join(device_list)
            query = "UPDATE users SET active_devices = active_devices + 1, device_id = %s WHERE id = %s"
            cursor.execute(query, (updated_device_ids, user_id))
            xbmc.log(f"Dispositivo {device_id} añadido para el usuario {user_id}.", level=xbmc.LOGINFO)

        else:
            if device_id not in device_list:
                xbmc.log(f"El dispositivo {device_id} no está en la lista para el usuario {user_id}", level=xbmc.LOGINFO)
                return True

            device_list = [d for d in device_list if d != device_id]
            updated_device_ids = ",".join(device_list)
            query = "UPDATE users SET active_devices = active_devices - 1, device_id = %s WHERE id = %s"
            cursor.execute(query, (updated_device_ids, user_id))
            xbmc.log(f"Dispositivo {device_id} removido para el usuario {user_id}.", level=xbmc.LOGINFO)

        connection.commit()
        xbmc.log(f"Dispositivos activos actualizados para usuario {user_id}: {updated_device_ids}", level=xbmc.LOGINFO)
        return True

    except Exception as e:
        xbmc.log(f"Error en update_active_devices: {e}", level=xbmc.LOGERROR)
        return False
    finally:
        cursor.close()
        connection.close()

def get_page_content(url):
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        else:
            xbmcgui.Dialog().notification("Error", f"HTTP {response.status_code}", xbmcgui.NOTIFICATION_ERROR)
            xbmc.log(f"Error HTTP {response.status_code} al acceder a {url}", level=xbmc.LOGERROR)
            return ""
    except Exception as e:
        xbmcgui.Dialog().notification("Error", str(e), xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"Error al obtener contenido de {url}: {e}", level=xbmc.LOGERROR)
        return ""

def build_url(query):
    return f"{base_url}?{urllib.parse.urlencode(query)}"

def list_channels(user):
    content = get_page_content(ACESTREAM_URL)
    if not content:
        xbmcplugin.endOfDirectory(addon_handle)
        return

    channels = extract_acestream_links(content)
    if not channels:
        xbmcgui.Dialog().notification("Error", "No se encontraron canales", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(addon_handle)
        return

    for name, channel_id in channels:
        url = build_url({"action": "play", "id": channel_id}) if channel_id else ""
        list_item = xbmcgui.ListItem(name)
        list_item.setInfo("video", {"title": name})
        list_item.setProperty("IsPlayable", "true")
        list_item.setArt({
            'icon': ICON_PATH,
            'thumb': ICON_PATH,
            'fanart': FANART_PATH
        })
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)

def extract_acestream_links(content):
    channels = []
    pattern_full = r'"name":\s*"([^"]+)".*?"url":\s*"acestream://([a-fA-F0-9]+)"'
    matches_full = re.findall(pattern_full, content)
    for name, channel_id in matches_full:
        if '{' not in name and '}' not in name:  
            channels.append((name.strip(), channel_id.strip()))
    pattern_no_link = r'"name":\s*"([^"]+)"'
    matches_no_link = re.findall(pattern_no_link, content)
    for name in matches_no_link:
        if '{' not in name and '}' not in name:  
            if name not in [c[0] for c in channels]:
                channels.append((name.strip(), ""))
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if "acestream://" in line and not re.search(r'acestream://[a-fA-F0-9]+', line):
            name_match = re.match(r'(.*?)\s*acestream://', line)
            if name_match:
                name = name_match.group(1).strip()
                if '{' not in name and '}' not in name: 
                    if name not in [c[0] for c in channels]:
                        channels.append((name, ""))
    return sorted(channels, key=lambda x: x[0].lower())

def extract_acestream_events(content):
    xbmc.log("Iniciando extracción de eventos", level=xbmc.LOGINFO)
    events = []

    row_pattern = r"<tr>(.*?)</tr>"
    rows = re.findall(row_pattern, content, re.DOTALL)
    xbmc.log(f"Filas encontradas: {len(rows)}", level=xbmc.LOGINFO)

    for row in rows:
        xbmc.log(f"Procesando fila: {row}", level=xbmc.LOGDEBUG)
        columns = re.findall(r"<td>(.*?)</td>", row, re.DOTALL)
        if len(columns) < 5:
            xbmc.log("Fila inválida, se omite.", level=xbmc.LOGWARNING)
            continue

        time, competition, team1, team2, links = columns[:5]
        xbmc.log(f"Datos extraídos: {time}, {competition}, {team1}, {team2}", level=xbmc.LOGINFO)

        link_pattern = r"<a href=acestream://([a-fA-F0-9]+)>(.*?)</a>"
        link_matches = re.findall(link_pattern, links)
        for channel_id, channel_name in link_matches:
            event = {
                "time": time.strip(),
                "competition": competition.strip(),
                "teams": f"{team1.strip()} Vs {team2.strip()}",
                "channel_name": channel_name.strip(),
                "channel_id": channel_id.strip(),
            }
            events.append(event)

    xbmc.log(f"Eventos extraídos: {len(events)}", level=xbmc.LOGINFO)
    return events

def list_acestream_events(user):
    xbmc.log("Entrando en list_acestream_events", level=xbmc.LOGINFO)
    content = get_page_content(EVENTS_URL)
    if not content:
        xbmc.log("No se pudo obtener contenido de la página.", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", "No se pudo obtener contenido de la página.", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(addon_handle)
        return
    
    events = extract_acestream_events(content)
    if not events:
        xbmc.log("No se encontraron eventos.", level=xbmc.LOGWARNING)
        xbmcgui.Dialog().notification("Error", "No se encontraron eventos.", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(addon_handle)
        return

    for event in events:
        url = build_url({"action": "play", "id": event["channel_id"]})
        list_item = xbmcgui.ListItem(label=f"{event['time']} | {event['competition']} | {event['teams']}")
        list_item.setInfo("video", {"title": event["channel_name"]})
        list_item.setProperty("IsPlayable", "true")
        list_item.setArt({
            "icon": ICON_PATH,
            "thumb": ICON_PATH,
            "fanart": FANART_PATH
        })

        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=False)

    xbmc.log("Finalizando list_acestream_events", level=xbmc.LOGINFO)
    xbmcplugin.endOfDirectory(addon_handle)

def play_channel(channel_id):
    if not channel_id:
        xbmcgui.Dialog().notification("Error", "Canal sin ID disponible", xbmcgui.NOTIFICATION_ERROR)
        return

    horus_command = f'RunPlugin("plugin://script.module.horus/?action=play&id={channel_id}")'
    try:
        xbmc.executebuiltin(horus_command)
        xbmcgui.Dialog().notification("Horus", "Reproduciendo en AceStream Engine...", xbmcgui.NOTIFICATION_INFO)
    except Exception as e:
        xbmcgui.Dialog().notification("Error", f"No se pudo ejecutar Horus: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"Error al ejecutar Horus: {e}", level=xbmc.LOGERROR)

def build_main_menu():
    xbmc.executebuiltin('Container.SetViewMode(55)')

    url_tronosstv = build_url({"action": "tronosstv"})
    list_item_tronosstv = xbmcgui.ListItem(label="TronossTV")
    list_item_tronosstv.setProperty("IsPlayable", "false")
    list_item_tronosstv.setArt({'icon': '', 'thumb': ICON_PATH, 'fanart': FANART_PATH})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_tronosstv, listitem=list_item_tronosstv, isFolder=True)

    url_agendatronoss = build_url({"action": "agendatronoss"})
    list_item_agendatronoss = xbmcgui.ListItem(label="Agenda Tronoss")
    list_item_agendatronoss.setProperty("IsPlayable", "false")
    list_item_agendatronoss.setArt({'icon': '', 'thumb': ICON_PATH, 'fanart': FANART_PATH})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_agendatronoss, listitem=list_item_agendatronoss, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

def on_exit():
    global user_id_global, is_logged_in, addon_active, device_marked_active, current_device_id

    if user_id_global and is_logged_in and addon_active and device_marked_active:
        xbmc.log(f"Reduciendo dispositivos activos para el usuario {user_id_global}", level=xbmc.LOGINFO)
        success = update_active_devices(user_id_global, current_device_id, increment=False)
        if success:
            xbmc.log(f"Dispositivo {current_device_id} desactivado correctamente para el usuario {user_id_global}", level=xbmc.LOGINFO)
        else:
            xbmc.log(f"Error al desactivar el dispositivo {current_device_id} para el usuario {user_id_global}", level=xbmc.LOGERROR)

    is_logged_in = False
    addon_active = False
    device_marked_active = False
    current_device_id = None
    xbmc.log("Estado de sesión limpiado correctamente.", level=xbmc.LOGINFO)

def router(args):
    global user_id_global, is_logged_in, addon_active, device_marked_active, current_device_id
    
    if not check_remote_status():
        sys.exit(0)
    
    if not is_logged_in:
        credentials = load_credentials()
        if not credentials:
            username, password = prompt_for_credentials()
            if username and password:
                user = check_user(username, password)
                if user:
                    save_credentials(username, password)
                    device_id = get_device_id()
                    if update_active_devices(user['id'], device_id, increment=True):
                        is_logged_in = True
                        user_id_global = user['id']
                        addon_active = True
                        device_marked_active = True
                        show_account_info(user)
                    else:
                        xbmcgui.Dialog().notification("Error", "No se pudo registrar el dispositivo.", xbmcgui.NOTIFICATION_ERROR)
        else:
            username = credentials['username']
            password = credentials['password']
            user = check_user(username, password)
            if user:
                device_id = get_device_id()
                if not device_marked_active:
                    if update_active_devices(user['id'], device_id, increment=True):
                        is_logged_in = True
                        user_id_global = user['id']
                        addon_active = True
                        device_marked_active = True
                        show_account_info(user)
            else:
                if os.path.exists(CREDENTIALS_FILE):
                    os.remove(CREDENTIALS_FILE)
                    xbmc.log("Credenciales eliminadas debido a fallo en la autenticación.", level=xbmc.LOGINFO)
                username, password = prompt_for_credentials()
                if username and password:
                    user = check_user(username, password)
                    if user:
                        save_credentials(username, password)
                        device_id = get_device_id()
                        if update_active_devices(user['id'], device_id, increment=True):
                            is_logged_in = True
                            user_id_global = user['id']
                            addon_active = True
                            device_marked_active = True
                            show_account_info(user)
                        else:
                            xbmcgui.Dialog().notification("Error", "No se pudo registrar el dispositivo.", xbmcgui.NOTIFICATION_ERROR)

    if not is_logged_in:
        xbmcplugin.endOfDirectory(addon_handle)
        return
    
    action = args.get("action", [None])[0]
    channel_id = args.get("id", [None])[0]
    
    if action == "play" and channel_id:
        play_channel(channel_id)
    elif action == "tronosstv":
        list_channels(user)
    elif action == "agendatronoss":
        list_acestream_events(user)
    else:
        build_main_menu()

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    if not check_remote_status():
        sys.exit(0) 
    try:
        args = urllib.parse.parse_qs(sys.argv[2][1:])
        router(args)
    except Exception as e:
        xbmcgui.Dialog().notification("Error", f"Error inesperado: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"Error inesperado en el router: {e}", level=xbmc.LOGERROR)
    finally:
        monitor.waitForAbort()
        on_exit()
