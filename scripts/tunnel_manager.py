"""
Módulo de Gerenciamento de Conectividade Externa & Acesso DCT
Suporta Link Fixo Permanente via Localtunnel (subdomínio: triagem-caragua-dct.loca.lt) e Cloudflare.
Inicia automaticamente em segundo plano ao abrir a aplicação.
"""

import os
import sys
import re
import json
import socket
import threading
import subprocess
import shutil
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
_lock = threading.RLock()
_auto_start_thread = None


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
        "provedor": "cloudflare",
        "subdominio": "triagem-caragua-dct",
        "auto_start": True,
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


def salvar_config_tunel(provedor="cloudflare", subdominio="triagem-caragua-dct", auto_start=True, url_fixa=""):
    """Salva as configurações de provedor, subdomínio e inicialização automática."""
    caminho = obter_caminho_config()
    config = {
        "provedor": provedor or "cloudflare",
        "subdominio": (subdominio or "triagem-caragua-dct").strip().lower(),
        "auto_start": bool(auto_start),
        "url_fixa": url_fixa.strip() if url_fixa else ""
    }
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return {"sucesso": True, "config": config}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao salvar configuração: {e}"}


def obter_caminho_cloudflared():
    """Retorna o caminho do executável portátil cloudflared.exe com busca em múltiplos locais."""
    # 1. Se estiver rodando dentro do PyInstaller (descompactado em _MEIPASS)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_cf = os.path.join(sys._MEIPASS, "cloudflared.exe")
        if os.path.exists(meipass_cf):
            return meipass_cf

    # 2. Checa no diretório do executável / pasta raiz da aplicação
    base_dir = obter_caminho_base()
    caminho = os.path.join(base_dir, "cloudflared.exe")
    if os.path.exists(caminho):
        return caminho

    # 3. Checa dentro da subpasta scripts/
    caminho_scripts = os.path.join(base_dir, "scripts", "cloudflared.exe")
    if os.path.exists(caminho_scripts):
        return caminho_scripts

    # 4. Checa no diretório de trabalho atual
    if os.path.exists("cloudflared.exe"):
        return os.path.abspath("cloudflared.exe")

    # 5. Checa no PATH global do Windows
    which_cf = shutil.which("cloudflared.exe") or shutil.which("cloudflared")
    if which_cf:
        return which_cf

    return caminho


def obter_caminho_npx():
    """Retorna o executável do npx no sistema se existir."""
    return shutil.which("npx.cmd") or shutil.which("npx")



def obter_ip_local():
    """Descobre o endereço IP local desta máquina na rede (ex: 192.168.100.83)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ==========================================
# Inicialização e Monitoramento do Túnel
# ==========================================

def _monitor_tunnel_output(proc, provedor="cloudflare", subdominio="triagem-caragua-dct"):
    global _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time
    url_found = False
    recent_logs = []
    debug_log_path = os.path.join(obter_caminho_base(), "tunnel_debug.log")

    try:
        with open(debug_log_path, "a", encoding="utf-8") as f_log:
            f_log.write(f"\n--- Iniciando túnel [{provedor}] em {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            line_str = line.strip()
            if line_str:
                recent_logs.append(line_str)
                if len(recent_logs) > 25:
                    recent_logs.pop(0)

                try:
                    with open(debug_log_path, "a", encoding="utf-8") as f_log:
                        f_log.write(line_str + "\n")
                except Exception:
                    pass

            # Procura por qualquer URL pública válida (Cloudflare ou Localtunnel)
            match = re.search(r'https://[a-zA-Z0-9-]+\.(trycloudflare\.com|loca\.lt)', line_str)
            if match and not url_found:
                with _lock:
                    _tunnel_url = match.group(0)
                    _tunnel_status = "ativo"
                    _tunnel_error = None
                    _tunnel_start_time = time.time()
                    url_found = True
                logger.info(f"[TÚNEL ATIVO] URL DCT gerada com sucesso: {_tunnel_url}")

        proc.stdout.close()
        rc = proc.wait()
        if not url_found:
            with _lock:
                _tunnel_status = "erro"
                # Pega as últimas linhas relevantes do erro
                filtered_err = [l for l in recent_logs if "ERR" in l or "WRN" in l or "failed" in l.lower() or "error" in l.lower()]
                log_excerpt = " | ".join(filtered_err[-2:]) if filtered_err else (" | ".join(recent_logs[-2:]) if recent_logs else f"Código: {rc}")
                _tunnel_error = f"O túnel encerrou (saída {rc}): {log_excerpt}"
    except Exception as e:
        logger.error(f"[TÚNEL] Erro na leitura dos logs: {e}")
        with _lock:
            if not url_found:
                _tunnel_status = "erro"
                _tunnel_error = str(e)
    finally:
        with _lock:
            if _tunnel_process == proc and not url_found:
                if _tunnel_status != "erro":
                    _tunnel_status = "erro"
                    _tunnel_error = "Túnel finalizou sem gerar uma URL pública."
                _tunnel_url = None



def iniciar_tunel(porta=5000):
    """Inicia o túnel seguro com subdomínio permanente ou Cloudflare portátil."""
    global _tunnel_process, _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time

    with _lock:
        if _tunnel_status == "ativo" and _tunnel_url and _tunnel_process and _tunnel_process.poll() is None:
            return {
                "sucesso": True,
                "status": "ativo",
                "url": _tunnel_url,
                "mensagem": "Túnel já está em execução."
            }

        _tunnel_status = "conectando"
        _tunnel_url = None
        _tunnel_error = None

        config = obter_config_tunel()
        provedor = config.get("provedor", "cloudflare")
        subdominio = config.get("subdominio", "triagem-caragua-dct")
        url_fixa = config.get("url_fixa")

        # Se houver URL externa manual fixa configurada
        if url_fixa:
            _tunnel_url = url_fixa
            _tunnel_status = "ativo"
            _tunnel_start_time = time.time()
            return {
                "sucesso": True,
                "status": "ativo",
                "url": _tunnel_url,
                "provedor": provedor,
                "ip_local": f"http://{obter_ip_local()}:{porta}",
                "mensagem": "Link fixo permanente ativo!"
            }

        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            npx_exe = obter_caminho_npx()
            # Se configurado para localtunnel mas a máquina não tiver Node.js/npx, faz fallback automático para cloudflared
            if provedor == "localtunnel" and not npx_exe:
                logger.warning("[TÚNEL] Node.js/npx não instalado nesta máquina. Alternando automaticamente para Cloudflare Tunnel portátil.")
                provedor = "cloudflare"

            if provedor == "localtunnel" and npx_exe:
                cmd = [npx_exe, "-y", "localtunnel", "--port", str(porta), "--subdomain", subdominio]
            else:
                caminho_cf = obter_caminho_cloudflared()
                if not os.path.exists(caminho_cf):
                    raise FileNotFoundError(f"Arquivo cloudflared.exe não encontrado em {caminho_cf}")
                # Parâmetros otimizados para redes corporativas/governamentais (Prefeituras):
                # --protocol http2: usa TCP 443 (HTTPS padrão) em vez de QUIC UDP 7844 (bloqueado em firewalls corporativos)
                # --edge-ip-version 4: evita falhas em redes com IPv6 incompleto/sem rota
                cmd = [
                    caminho_cf, "tunnel",
                    "--url", f"http://127.0.0.1:{porta}",
                    "--protocol", "http2",
                    "--edge-ip-version", "4",
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


            t = threading.Thread(target=_monitor_tunnel_output, args=(_tunnel_process, provedor, subdominio), daemon=True)
            t.start()

        except Exception as e:
            _tunnel_status = "erro"
            _tunnel_error = str(e)
            return {
                "sucesso": False,
                "status": "erro",
                "mensagem": f"Falha ao iniciar túnel: {e}"
            }

    # Aguarda até 15 segundos para a URL ser confirmada
    start_wait = time.time()
    while time.time() - start_wait < 15:
        with _lock:
            if _tunnel_status == "ativo" and _tunnel_url:
                return {
                    "sucesso": True,
                    "status": "ativo",
                    "url": _tunnel_url,
                    "provedor": provedor,
                    "ip_local": f"http://{obter_ip_local()}:{porta}"
                }
            if _tunnel_status == "erro":
                return {
                    "sucesso": False,
                    "status": "erro",
                    "mensagem": _tunnel_error or "Erro ao iniciar túnel."
                }
            if _tunnel_process and _tunnel_process.poll() is not None:
                rc = _tunnel_process.poll()
                _tunnel_status = "erro"
                _tunnel_error = f"O processo do túnel encerrou prematuramente com código {rc}."
                return {
                    "sucesso": False,
                    "status": "erro",
                    "mensagem": _tunnel_error
                }
        time.sleep(0.4)

    return {
        "sucesso": True,
        "status": _tunnel_status,
        "url": _tunnel_url or "",
        "ip_local": f"http://{obter_ip_local()}:{porta}",
        "mensagem": "Túnel em inicialização..."
    }


def parar_tunel():
    """Encerra o túnel seguro."""
    global _tunnel_process, _tunnel_url, _tunnel_status, _tunnel_start_time, _tunnel_error

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
        _tunnel_error = None
        _tunnel_start_time = None

    return {
        "sucesso": True,
        "status": "desconectado",
        "mensagem": "Túnel encerrado com sucesso."
    }


def status_tunel():
    """Retorna o estado atual do túnel e o link de acesso."""
    global _tunnel_status, _tunnel_url, _tunnel_error

    with _lock:
        ip_local = obter_ip_local()
        uptime_segundos = int(time.time() - _tunnel_start_time) if _tunnel_start_time and _tunnel_status == "ativo" else 0
        config = obter_config_tunel()
        provedor = config.get("provedor", "cloudflare")
        subdominio = config.get("subdominio", "triagem-caragua-dct")
        url_fixa = config.get("url_fixa")

        # Verifica se o processo morreu inesperadamente
        if _tunnel_process and _tunnel_process.poll() is not None:
            if not _tunnel_url:
                _tunnel_status = "erro"
                if not _tunnel_error:
                    _tunnel_error = f"Processo do túnel encerrou (código {_tunnel_process.poll()})."
            else:
                _tunnel_status = "desconectado"
                _tunnel_url = None

        if _tunnel_url:
            url_retorno = _tunnel_url
        elif url_fixa:
            url_retorno = url_fixa
        elif _tunnel_status == "conectando":
            url_retorno = ""
        else:
            url_retorno = ""

        return {
            "status": _tunnel_status,
            "url": url_retorno,
            "ip_local": f"http://{ip_local}:5000",
            "uptime_segundos": uptime_segundos,
            "erro": _tunnel_error,
            "provedor": provedor,
            "subdominio": subdominio,
            "auto_start": config.get("auto_start", True)
        }



def iniciar_tunel_auto_start(porta=5000):
    """Thread em segundo plano que inicia o túnel automaticamente se auto_start estiver habilitado."""
    def _worker():
        time.sleep(1.5)  # Breve espera para o servidor Flask subir
        config = obter_config_tunel()
        if config.get("auto_start", True):
            logger.info("[AUTO-START] Inicializando túnel de Acesso DCT em segundo plano...")
            iniciar_tunel(porta=porta)

    t = threading.Thread(target=_worker, daemon=True, name="TunnelAutoStart")
    t.start()


# Garante encerramento limpo ao finalizar a aplicação
atexit.register(parar_tunel)
