import requests
import os
import xbmcvfs
import xbmc
import xbmcgui

UPDATE_URL = "https://raw.githubusercontent.com/tronoss99/repo/main/main.py"
MAIN_SCRIPT_PATH = xbmcvfs.translatePath('special://home/addons/plugin.video.tronosstv/main.py')

def download_main_script():
    try:
        response = requests.get(UPDATE_URL)
        if response.status_code == 200:
            with open(MAIN_SCRIPT_PATH, 'wb') as f:
                f.write(response.content)
            xbmcgui.Dialog().notification("Actualizacion Exitosa", "El addon se ha actualizado correctamente.", xbmcgui.NOTIFICATION_INFO, 3000)
    except Exception:
        pass 
def execute_main_script():
    if os.path.exists(MAIN_SCRIPT_PATH):
        with open(MAIN_SCRIPT_PATH, 'rb') as f:
            exec(compile(f.read(), MAIN_SCRIPT_PATH, 'exec'), globals())
    else:
        xbmcgui.Dialog().notification("Error", "Archivo main.py no encontrado", xbmcgui.NOTIFICATION_ERROR)

if __name__ == "__main__":
    download_main_script() 
    execute_main_script()  
