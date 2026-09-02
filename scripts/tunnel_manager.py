"""
Módulo de Gerenciamento de Conectividade Externa, Link Fixo e Proteção por PIN (Acesso DCT)
Suporta Link Fixo Permanente via Localtunnel (subdomínio customizado) e Modo Rápido Cloudflare.
Gera e gerencia PIN dinâmico de 4 dígitos para autenticação de operadores remotos da DCT.
"""

import os
import sys
import re
import json
import random
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
_tunnel_pin = None
_lock = threading.RLock()



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
        "url_fixa": "https://dct-triagem.com",
        "subdominio": "dct-triagem.com",
        "pin_padrao": ""
    }
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default_config, **data}
        except Exception:
            pass
    return default_config


def salvar_config_tunel(provedor="cloudflare", url_fixa="https://dct-triagem.com", subdominio="dct-triagem.com", pin_padrao=""):
    """Salva as configurações de provedor, URL fixa e PIN padrão."""
    caminho = obter_caminho_config()
    
    url_limpa = url_fixa.strip() if url_fixa else ""
    if url_limpa and not url_limpa.startswith("http"):
        url_limpa = f"https://{url_limpa}"

    config = {
        "provedor": provedor or "cloudflare",
        "url_fixa": url_limpa or "https://dct-triagem.com",
        "subdominio": subdominio or "dct-triagem.com",
        "pin_padrao": str(pin_padrao).strip()[:4] if pin_padrao else ""
    }
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return {"sucesso": True, "config": config}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao salvar configuração: {e}"}



# ==========================================
# Gerenciador de PIN de 4 Dígitos
# ==========================================

def gerar_novo_pin():
    """Gera um novo PIN aleatório de 4 dígitos numéricos (ex: 7429)."""
    global _tunnel_pin
    with _lock:
        _tunnel_pin = f"{random.randint(1000, 9999)}"
        return _tunnel_pin


def obter_pin_atual():
    """Retorna o PIN atual de 4 dígitos (ou gera um novo se não existir)."""
    global _tunnel_pin
    with _lock:
        if not _tunnel_pin:
            cfg = obter_config_tunel()
            if cfg.get("pin_padrao") and len(cfg.get("pin_padrao")) == 4:
                _tunnel_pin = cfg.get("pin_padrao")
            else:
                _tunnel_pin = f"{random.randint(1000, 9999)}"
        return _tunnel_pin


def definir_pin(novo_pin):
    """Define um PIN manual de 4 dígitos numéricos."""
    global _tunnel_pin
    pin_str = str(novo_pin).strip()
    if len(pin_str) == 4 and pin_str.isdigit():
        with _lock:
            _tunnel_pin = pin_str
        return {"sucesso": True, "pin": _tunnel_pin}
    return {"sucesso": False, "mensagem": "O PIN deve conter exatamente 4 dígitos numéricos (0-9)."}


def validar_pin(pin_digitado):
    """Valida se o PIN informado confere com o PIN ativo da sessão."""
    pin_atual = obter_pin_atual()
    pin_limpo = str(pin_digitado).strip()
    return pin_limpo == pin_atual


# ==========================================
# Descoberta de IP e Executáveis
# ==========================================

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

def _monitor_tunnel_output(proc, provedor="localtunnel", subdominio=""):
    global _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time
    url_found = False

    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            line_str = line.strip()

            if provedor == "localtunnel":
                # Procura 'your url is: https://*.loca.lt'
                match = re.search(r'https://[a-zA-Z0-9-]+\.loca\.lt', line_str)
                if match and not url_found:
                    with _lock:
                        _tunnel_url = match.group(0)
                        _tunnel_status = "ativo"
                        _tunnel_start_time = time.time()
                        url_found = True
                    logger.info(f"[TÚNEL FIXO ATIVO - LOCALTUNNEL] URL DCT: {_tunnel_url}")
            else:
                # Procura 'https://*.trycloudflare.com'
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line_str)
                if match and not url_found:
                    with _lock:
                        _tunnel_url = match.group(0)
                        _tunnel_status = "ativo"
                        _tunnel_start_time = time.time()
                        url_found = True
                    logger.info(f"[TÚNEL ATIVO - CLOUDFLARE] URL DCT: {_tunnel_url}")

        proc.stdout.close()
        proc.wait()
    except Exception as e:
        logger.error(f"[TÚNEL] Erro na leitura dos logs: {e}")
    finally:
        with _lock:
            if _tunnel_process == proc:
                _tunnel_status = "desconectado"
                _tunnel_url = None


def iniciar_tunel(porta=5000):
    """Inicia o túnel seguro com subdomínio permanente e gera o PIN da sessão."""
    global _tunnel_process, _tunnel_url, _tunnel_status, _tunnel_error, _tunnel_start_time

    # Garante a geração de um PIN para a sessão
    pin_sessao = gerar_novo_pin()

    with _lock:
        if _tunnel_status in ["ativo", "conectando"] and _tunnel_process and _tunnel_process.poll() is None:
            return {
                "sucesso": True,
                "status": _tunnel_status,
                "url": _tunnel_url,
                "pin": pin_sessao,
                "mensagem": "Túnel já está em execução."
            }

        _tunnel_status = "conectando"
        _tunnel_url = None
        _tunnel_error = None

        config = obter_config_tunel()
        url_fixa = config.get("url_fixa")
        provedor = config.get("provedor", "cloudflare")
        subdominio = config.get("subdominio", "dct-triagem.com")

        # Se já temos uma URL fixa configurada (ex: Cloudflare permanente), ativa ela diretamente
        if url_fixa:
            _tunnel_url = url_fixa
            _tunnel_status = "ativo"
            _tunnel_start_time = time.time()
            return {
                "sucesso": True,
                "status": "ativo",
                "url": _tunnel_url,
                "pin": pin_sessao,
                "provedor": provedor,
                "ip_local": f"http://{obter_ip_local()}:{porta}",
                "mensagem": "Link fixo permanente ativo!"
            }

        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW


            if provedor == "localtunnel" and shutil.which("npx"):
                cmd = ["npx", "-y", "localtunnel", "--port", str(porta), "--subdomain", subdominio]
            else:
                provedor = "cloudflare"
                caminho_cf = obter_caminho_cloudflared()
                if not os.path.exists(caminho_cf):
                    raise FileNotFoundError(f"Arquivo cloudflared.exe não encontrado em {caminho_cf}")
                cmd = [caminho_cf, "tunnel", "--url", f"http://127.0.0.1:{porta}", "--no-autoupdate"]

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
                "pin": pin_sessao,
                "mensagem": f"Falha ao iniciar túnel: {e}"
            }

    # Aguarda até 10 segundos para a URL ser gerada
    start_wait = time.time()
    while time.time() - start_wait < 10:
        with _lock:
            if _tunnel_status == "ativo" and _tunnel_url:
                return {
                    "sucesso": True,
                    "status": "ativo",
                    "url": _tunnel_url,
                    "pin": pin_sessao,
                    "provedor": provedor,
                    "ip_local": f"http://{obter_ip_local()}:{porta}"
                }
            if _tunnel_status == "erro":
                return {
                    "sucesso": False,
                    "status": "erro",
                    "pin": pin_sessao,
                    "mensagem": _tunnel_error
                }
        time.sleep(0.5)

    return {
        "sucesso": True,
        "status": "conectando",
        "url": _tunnel_url or f"https://{subdominio}.loca.lt",
        "pin": pin_sessao,
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
    """Retorna o estado atual do túnel, links de acesso e PIN de segurança."""
    with _lock:
        ip_local = obter_ip_local()
        uptime_segundos = int(time.time() - _tunnel_start_time) if _tunnel_start_time and _tunnel_status == "ativo" else 0
        config = obter_config_tunel()
        provedor = config.get("provedor", "cloudflare")
        
        if _tunnel_url:
            url_retorno = _tunnel_url
        elif provedor == "localtunnel":
            url_retorno = f"https://{config.get('subdominio', 'triagem-ait-caragua')}.loca.lt"
        else:
            url_retorno = config.get("url_fixa", "https://dct-triagem.com")

        return {
            "status": _tunnel_status,
            "url": url_retorno,
            "url_fixa": config.get("url_fixa", "https://dct-triagem.com"),
            "pin": obter_pin_atual(),
            "ip_local": f"http://{ip_local}:5000",
            "uptime_segundos": uptime_segundos,
            "erro": _tunnel_error,
            "provedor": provedor,
            "subdominio": config.get("subdominio", "dct-triagem.com")
        }




# Garante encerramento limpo ao finalizar a aplicação
atexit.register(parar_tunel)
