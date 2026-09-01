"""
Módulo de Gerenciamento de Conectividade Externa e Túnel Seguro (Cloudflare Quick Tunnel)
Permite que o setor DCT / Terceirizada acerte a aplicação em tempo real mesmo em redes separadas
sem necessidade de privilégios de Administrador do Windows.
"""

import os
import sys
import re
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


def obter_caminho_cloudflared():
    """Retorna o caminho do executável portátil cloudflared.exe."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Se estiver rodando empacotado no PyInstaller
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)

    # 1. Tenta na raiz do projeto / executável
    caminho = os.path.join(base_dir, "cloudflared.exe")
    if os.path.exists(caminho):
        return caminho

    # 2. Tenta na pasta scripts
    caminho_scripts = os.path.join(base_dir, "scripts", "cloudflared.exe")
    if os.path.exists(caminho_scripts):
        return caminho_scripts

    return caminho


def obter_ip_local():
    """Descobre o endereço IP local desta máquina na rede (ex: 192.168.1.50)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Não precisa enviar dados reais, apenas conecta para descobrir a interface padrão
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def _monitor_tunnel_output(proc):
    global _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time
    url_found = False

    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            line_str = line.strip()
            # Procura a URL do TryCloudflare
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line_str)
            if match and not url_found:
                with _lock:
                    _tunnel_url = match.group(0)
                    _tunnel_status = "ativo"
                    _tunnel_start_time = time.time()
                    url_found = True
                logger.info(f"[TÚNEL ATIVO] URL pública para DCT: {_tunnel_url}")

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
    """Inicia o túnel seguro da Cloudflare em segundo plano."""
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

        try:
            # Inicia subprocesso sem janela visível (CREATE_NO_WINDOW)
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

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

            # Thread para ler os logs e capturar a URL
            t = threading.Thread(target=_monitor_tunnel_output, args=(_tunnel_process,), daemon=True)
            t.start()

        except Exception as e:
            _tunnel_status = "erro"
            _tunnel_error = str(e)
            return {
                "sucesso": False,
                "status": "erro",
                "mensagem": f"Falha ao iniciar processo: {e}"
            }

    # Aguarda até 12 segundos para a URL ser gerada
    start_wait = time.time()
    while time.time() - start_wait < 12:
        with _lock:
            if _tunnel_status == "ativo" and _tunnel_url:
                return {
                    "sucesso": True,
                    "status": "ativo",
                    "url": _tunnel_url,
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
        "url": _tunnel_url,
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
    """Retorna o estado atual do túnel e o link de acesso local/remoto."""
    with _lock:
        ip_local = obter_ip_local()
        uptime_segundos = int(time.time() - _tunnel_start_time) if _tunnel_start_time and _tunnel_status == "ativo" else 0
        return {
            "status": _tunnel_status,
            "url": _tunnel_url,
            "ip_local": f"http://{ip_local}:5000",
            "uptime_segundos": uptime_segundos,
            "erro": _tunnel_error
        }


# Garante encerramento limpo ao finalizar a aplicação
atexit.register(parar_tunel)
