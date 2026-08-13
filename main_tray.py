import threading
import time
import os
import sys
import subprocess
import webbrowser
import ctypes
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# Named Mutex configuration for Single Instance check on Windows
MUTEX_NAME = "Local\\TriagemAITSingleInstanceMutex"
kernel32 = ctypes.windll.kernel32
mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
last_error = kernel32.GetLastError()

# Target URL for the web app
URL = "http://127.0.0.1:5000"

def get_chrome_path():
    """Locate Google Chrome executable on Windows."""
    paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
    ]
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        path, _ = winreg.QueryValueEx(key, "")
        if os.path.exists(path):
            return path
    except Exception:
        pass
        
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def open_in_chrome():
    """Launch URL as a standard tab in Google Chrome or default browser."""
    chrome_path = get_chrome_path()
    if chrome_path:
        try:
            subprocess.Popen([chrome_path, URL])
        except Exception:
            webbrowser.open(URL)
    else:
        webbrowser.open(URL)

if last_error == 183:  # ERROR_ALREADY_EXISTS
    # Single Instance Alert: If already running, open Chrome and notify user
    open_in_chrome()
    ctypes.windll.user32.MessageBoxW(
        0, 
        "O sistema Triagem AIT já está em execução na barra de tarefas (canto inferior direito próximo ao relógio).", 
        "Triagem AIT", 
        0x40 | 0x0  # MB_ICONINFORMATION | MB_OK
    )
    sys.exit(0)

# Run database migrations auto-check before starting server
try:
    from scripts.migrate_v3 import migrate
    migrate()
except Exception as e:
    print(f"Migração auto-check aviso: {e}")

# Import Flask app
from app import app

def run_flask():
    """Run Flask server in background thread without debug reloader."""
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def get_resources_path():
    """Get absolute path to resources for dev and PyInstaller (_MEIPASS)."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_icon_image():
    """Load app_icon.ico or generate dynamic fallback image."""
    ico_path = os.path.join(get_resources_path(), "app_icon.ico")
    if os.path.exists(ico_path):
        try:
            return Image.open(ico_path)
        except Exception:
            pass
    return create_tray_icon_image()

def create_tray_icon_image():
    """Generate dynamic traffic icon if ico is missing."""
    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse([2, 2, width - 2, height - 2], fill=(15, 23, 42, 255), outline=(249, 115, 22, 255), width=2)
    dc.polygon([(width / 2, 6), (6, height - 6), (width - 6, height - 6)], fill=(249, 115, 22, 255))
    dc.text((26, 26), "A", fill=(255, 255, 255, 255), align="center")
    return image

def on_open_action(icon, item):
    """Callback when clicking 'Abrir Triagem AIT' or double clicking icon."""
    open_in_chrome()

def on_exit_action(icon, item):
    """Shutdown tray icon and exit application process."""
    icon.stop()
    os._exit(0)

def notify_started(icon):
    time.sleep(1.5)
    try:
        icon.notify("O servidor Triagem AIT está em execução na barra de tarefas (próximo ao relógio).", "Triagem AIT")
    except Exception:
        pass

def main():
    # 1. Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Allow server to initialize
    time.sleep(1.0)
    
    # 2. Open Google Chrome automatically
    open_in_chrome()
    
    # 3. Setup and run Windows System Tray Icon
    icon_image = get_icon_image()
    menu = (
        item('Abrir Triagem AIT', on_open_action, default=True),
        item('Status: Servidor Online (Porta 5000)', lambda i, it: None, enabled=False),
        item('---', None),
        item('Sair do Sistema', on_exit_action)
    )
    
    tray_icon = pystray.Icon(
        "triagem_ait",
        icon_image,
        "Triagem AIT — Servidor Ativo (127.0.0.1:5000)",
        menu
    )
    
    threading.Thread(target=notify_started, args=(tray_icon,), daemon=True).start()
    tray_icon.run()

if __name__ == "__main__":
    main()
