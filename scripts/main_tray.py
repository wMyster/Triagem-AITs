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
# CreateMutexW (LPSECURITY_ATTRIBUTES, BOOL bInitialOwner, LPCWSTR lpName)
mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
last_error = kernel32.GetLastError()

if last_error == 183:  # ERROR_ALREADY_EXISTS
    # Show native dialog informing user it is already running and exit
    ctypes.windll.user32.MessageBoxW(
        0, 
        "O sistema Triagem AIT já está rodando em segundo plano.\nVerifique o ícone do triângulo na barra de tarefas (canto inferior direito).", 
        "Triagem AIT", 
        0x40 | 0x0  # MB_ICONINFORMATION | MB_OK
    )
    sys.exit(0)

# Import the flask app from app.py
from app import app

# Target URL for the web app
URL = "http://127.0.0.1:5000"

def get_chrome_path():
    """Locate Google Chrome executable on Windows."""
    paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
    ]
    
    # Also check Registry if paths fail
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
            # Opens as a standard new tab in Google Chrome
            subprocess.Popen([chrome_path, URL])
        except Exception:
            webbrowser.open(URL)
    else:
        webbrowser.open(URL)

def run_flask():
    """Run Flask server in background thread without debug reloader."""
    # use_reloader=False is critical to prevent duplicate processes inside PyInstaller
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def get_resources_path():
    """Get absolute path to resources, works for dev and for PyInstaller."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_icon_image():
    """Load the app_icon.ico or generate a fallback dynamic image."""
    ico_path = os.path.join(get_resources_path(), "app_icon.ico")
    if os.path.exists(ico_path):
        try:
            return Image.open(ico_path)
        except Exception:
            pass
    # If the ico file couldn't be loaded, generate the dynamic fallback
    return create_tray_icon_image()

def create_tray_icon_image():
    """Generate a sleek orange/blue traffic triangle icon dynamically."""
    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Draw a traffic orange rounded triangle
    # Coordinates of triangle
    padding = 4
    pt1 = (width / 2, padding)
    pt2 = (padding, height - padding)
    pt3 = (width - padding, height - padding)
    
    # Outer dark blue background circle to look premium
    dc.ellipse([2, 2, width - 2, height - 2], fill=(15, 23, 42, 255), outline=(249, 115, 22, 255), width=2)
    
    # Inner orange triangle
    dc.polygon([pt1, pt2, pt3], fill=(249, 115, 22, 255))
    
    # Draw white 'A' in the middle of triangle
    # Try using default font
    dc.text((26, 26), "A", fill=(255, 255, 255, 255), font_size=18, align="center")
    
    return image

def on_open_action(icon, item):
    """Callback when clicking 'Open' or double-clicking the icon."""
    open_in_chrome()

def on_exit_action(icon, item):
    """Shutdown the tray icon and exit process."""
    icon.stop()
    # Force kill the background thread/process
    os._exit(0)

def main():
    # 1. Start Flask in a background daemon thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Give the server a second to initialize before opening the window
    time.sleep(1.2)
    
    # 2. Open Google Chrome in App Mode instantly on startup
    open_in_chrome()
    
    # 3. Setup and start the System Tray Icon
    icon_image = get_icon_image()
    menu = (
        item('Abrir Triagem AIT', on_open_action, default=True),
        item('---', None),
        item('Sair', on_exit_action)
    )
    
    tray_icon = pystray.Icon(
        "triagem_ait",
        icon_image,
        "Triagem AIT (Rodando em segundo plano)",
        menu
    )
    
    # Start pystray event loop (blocks until icon.stop() is called)
    tray_icon.run()

if __name__ == "__main__":
    main()
