"""
Módulo de Gerenciamento de Conectividade Externa e Túnel Seguro (Cloudflare Tunnel)
Suporta tanto o Modo Rápido (TryCloudflare) quanto o Modo Fixo Permanente com Token (Cloudflare Zero Trust).
Permite que o setor DCT / Terceirizada acesse a aplicação em tempo real mesmo em redes separadas
sem necessidade de privilégios de Administrador do Windows.
"""

import os
import sys
import re
import json
import socket
import threading
import subprocess
import atexit
import time
import logging

logger = logging.getLogger("tunnel_manager")

# Estado global do túnel
_tunnel_process = None
_tunnel_url = None
_tunnel_status = "desconectado"  # 'desconectado', 'conectando', 'ativo', 'erro'
_tunnel_error = None
_tunnel_start_time = None
_lock = threading.Lock()


def obter_caminho_base():
    """Retorna o diretório base da aplicação (compatível com PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def obter_caminho_config():
    """Retorna o caminho do arquivo de configuração do túnel."""
    return os.path.join(obter_caminho_base(), "config_tunel.json")


def obter_config_tunel():
    """Carrega as configurações salvas do túnel."""
    caminho = obter_caminho_config()
    default_config = {
        "modo": "rapido",  # "rapido" ou "token_fixo"
        "token": "",
        "url_fixa": ""
    }
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default_config, **data}
        except Exception:
            pass
    return default_config


def salvar_config_tunel(modo="rapido", token="", url_fixa=""):
    """Salva as configurações de modo, token e url fixa do túnel."""
    caminho = obter_caminho_config()
    config = {
        "modo": "token_fixo" if modo == "token_fixo" else "rapido",
        "token": token.strip() if token else "",
        "url_fixa": url_fixa.strip() if url_fixa else ""
    }
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return {"sucesso": True, "config": config}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao salvar configuração: {e}"}


def obter_caminho_cloudflared():
    """Retorna o caminho do executável portátil cloudflared.exe."""
    base_dir = obter_caminho_base()
    caminho = os.path.join(base_dir, "cloudflared.exe")
    if os.path.exists(caminho):
        return caminho

    caminho_scripts = os.path.join(base_dir, "scripts", "cloudflared.exe")
    if os.path.exists(caminho_scripts):
        return caminho_scripts

    return caminho


def obter_ip_local():
    """Descobre o endereço IP local desta máquina na rede (ex: 192.168.1.50)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def _monitor_tunnel_output(proc, modo="rapido", url_fixa=""):
    global _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time
    url_found = False

    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            line_str = line.strip()

            if modo == "rapido":
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line_str)
                if match and not url_found:
                    with _lock:
                        _tunnel_url = match.group(0)
                        _tunnel_status = "ativo"
                        _tunnel_start_time = time.time()
                        url_found = True
                    logger.info(f"[TÚNEL ATIVO] URL pública para DCT: {_tunnel_url}")
            else:
                # Modo Token Fixo: Detecta quando a conexão é estabelecida
                if ("Registered tunnel connection" in line_str or "Connection established" in line_str or "Connected to" in line_str) and not url_found:
                    with _lock:
                        _tunnel_url = url_fixa if url_fixa else "Túnel Conectado (Domínio Fixo Cloudflare)"
                        _tunnel_status = "ativo"
                        _tunnel_start_time = time.time()
                        url_found = True
                    logger.info(f"[TÚNEL FIXO ATIVO] Conectado via Token! URL: {_tunnel_url}")

        proc.stdout.close()
        proc.wait()
    except Exception as e:
        logger.error(f"[TÚNEL] Erro na leitura dos logs: {e}")
    finally:
        with _lock:
            if _tunnel_process == proc:
                _tunnel_status = "desconectado"
                _tunnel_url = None


def baixar_cloudflared_se_necessario():
    """Verifica se o cloudflared.exe existe ou faz o download oficial automaticamente."""
    caminho = obter_caminho_cloudflared()
    if os.path.exists(caminho) and os.path.getsize(caminho) > 10000000:
        return caminho

    url = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response, open(caminho, 'wb') as out_file:
            block_size = 1024 * 512
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
        return caminho
    except Exception as e:
        logger.error(f"Erro ao baixar cloudflared.exe: {e}")
        return None


def iniciar_tunel(porta=5000):
    """Inicia o túnel seguro da Cloudflare em segundo plano (Modo Rápido ou Token Fixo)."""
    global _tunnel_process, _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time

    with _lock:
        if _tunnel_status in ["ativo", "conectando"] and _tunnel_process and _tunnel_process.poll() is None:
            return {
                "sucesso": True,
                "status": _tunnel_status,
                "url": _tunnel_url,
                "mensagem": "Túnel já está em execução."
            }

        caminho_exe = baixar_cloudflared_se_necessario()
        if not caminho_exe or not os.path.exists(caminho_exe):
            _tunnel_status = "erro"
            _tunnel_error = "Executável cloudflared.exe não encontrado e falha no download automático."
            return {
                "sucesso": False,
                "status": "erro",
                "mensagem": _tunnel_error
            }

        _tunnel_status = "conectando"
        _tunnel_url = None
        _tunnel_error = None

        config = obter_config_tunel()
        modo = config.get("modo", "rapido")
        token = config.get("token", "").strip()
        url_fixa = config.get("url_fixa", "").strip()

        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            if modo == "token_fixo" and token:
                cmd = [
                    caminho_exe,
                    "tunnel",
                    "run",
                    "--token", token
                ]
            else:
                cmd = [
                    caminho_exe,
                    "tunnel",
                    "--url", f"http://127.0.0.1:{porta}",
                    "--no-autoupdate"
                ]

            _tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creation_flags
            )

            t = threading.Thread(target=_monitor_tunnel_output, args=(_tunnel_process, modo, url_fixa), daemon=True)
            t.start()

        except Exception as e:
            _tunnel_status = "erro"
            _tunnel_error = str(e)
            return {
                "sucesso": False,
                "status": "erro",
                "mensagem": f"Falha ao iniciar processo: {e}"
            }

    # Aguarda até 12 segundos para a inicialização
    start_wait = time.time()
    while time.time() - start_wait < 12:
        with _lock:
            if _tunnel_status == "ativo" and _tunnel_url:
                return {
                    "sucesso": True,
                    "status": "ativo",
                    "url": _tunnel_url,
                    "modo": modo,
                    "ip_local": f"http://{obter_ip_local()}:{porta}"
                }
            if _tunnel_status == "erro":
                return {
                    "sucesso": False,
                    "status": "erro",
                    "mensagem": _tunnel_error
                }
        time.sleep(0.5)

    return {
        "sucesso": True,
        "status": "conectando",
        "url": _tunnel_url or (url_fixa if modo == "token_fixo" else None),
        "mensagem": "Túnel está sendo inicializado. Aguarde alguns instantes."
    }


def parar_tunel():
    """Encerra o túnel seguro."""
    global _tunnel_process, _tunnel_url, _tunnel_status, _tunnel_start_time

    with _lock:
        if _tunnel_process:
            try:
                _tunnel_process.terminate()
                _tunnel_process.wait(timeout=2)
            except Exception:
                try:
                    _tunnel_process.kill()
                except Exception:
                    pass
            _tunnel_process = None

        _tunnel_status = "desconectado"
        _tunnel_url = None
        _tunnel_start_time = None

    return {
        "sucesso": True,
        "status": "desconectado",
        "mensagem": "Túnel encerrado com sucesso."
    }


def status_tunel():
    """Retorna o estado atual do túnel, links de acesso e configurações salvas."""
    with _lock:
        ip_local = obter_ip_local()
        uptime_segundos = int(time.time() - _tunnel_start_time) if _tunnel_start_time and _tunnel_status == "ativo" else 0
        config = obter_config_tunel()
        return {
            "status": _tunnel_status,
            "url": _tunnel_url or (config.get("url_fixa") if _tunnel_status == "ativo" and config.get("modo") == "token_fixo" else None),
            "ip_local": f"http://{ip_local}:5000",
            "uptime_segundos": uptime_segundos,
            "erro": _tunnel_error,
            "modo": config.get("modo", "rapido"),
            "tem_token": bool(config.get("token")),
            "url_fixa": config.get("url_fixa", "")
        }


# Garante encerramento limpo ao finalizar a aplicação
atexit.register(parar_tunel)
