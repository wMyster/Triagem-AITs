import urllib.request
import os
import re

def download_assets():
    base_static = r"c:\Projetos Programação\Triagem AIT\static"
    fa_css_dir = os.path.join(base_static, "fontawesome", "css")
    fa_fonts_dir = os.path.join(base_static, "fontawesome", "webfonts")
    
    os.makedirs(fa_css_dir, exist_ok=True)
    os.makedirs(fa_fonts_dir, exist_ok=True)
    
    css_url = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    print("Baixando FontAwesome CSS...")
    req = urllib.request.Request(css_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        css_content = resp.read().decode("utf-8")
        
    with open(os.path.join(fa_css_dir, "all.min.css"), "w", encoding="utf-8") as f:
        f.write(css_content)
    print("CSS all.min.css salvo localmente com sucesso.")
    
    # Arquivos de webfonts do FontAwesome 6.4.0
    font_files = [
        "fa-solid-900.woff2",
        "fa-solid-900.ttf",
        "fa-regular-400.woff2",
        "fa-regular-400.ttf",
        "fa-brands-400.woff2",
        "fa-brands-400.ttf",
        "fa-v4compatibility.woff2",
        "fa-v4compatibility.ttf"
    ]
    
    for filename in font_files:
        font_url = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/{filename}"
        dest_path = os.path.join(fa_fonts_dir, filename)
        print(f"Baixando webfont {filename}...")
        try:
            req_font = urllib.request.Request(font_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_font) as f_resp:
                with open(dest_path, "wb") as f_out:
                    f_out.write(f_resp.read())
            print(f" -> Salvo com sucesso: {filename} ({os.path.getsize(dest_path)} bytes)")
        except Exception as e:
            print(f" -> Aviso/Erro ao baixar {filename}: {e}")

if __name__ == "__main__":
    download_assets()
