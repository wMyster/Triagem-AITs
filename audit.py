import sqlite3
import os
import sys
import socket

def get_db_path():
    net_dir = r"G:\Triagem AITs"
    net_db = os.path.join(net_dir, "triagem_ait.db")
    if os.path.exists(net_dir) and os.path.exists(net_db):
        return net_db
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "triagem_ait.db")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "triagem_ait.db")

def log_auditoria(usuario, perfil, acao, tabela=None, registro_id=None, antes=None, depois=None, justificativa=None, ip=None):
    try:
        ip_origem = ip
        hostname = None
        
        # Tenta obter IP do contexto de requisição do Flask se não informado
        try:
            from flask import has_request_context, request
            if has_request_context():
                if not ip_origem:
                    ip_origem = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if ip_origem and ',' in ip_origem:
                        ip_origem = ip_origem.split(',')[0].strip()
        except Exception:
            pass

        if not ip_origem:
            ip_origem = "127.0.0.1"

        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = "LocalHost"

        conn = sqlite3.connect(get_db_path(), timeout=10.0)
        
        # Garante que as colunas ip_origem e hostname existem na tabela auditoria_logs
        try:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(auditoria_logs)").fetchall()]
            if "ip_origem" not in cols:
                conn.execute("ALTER TABLE auditoria_logs ADD COLUMN ip_origem TEXT;")
            if "hostname" not in cols:
                conn.execute("ALTER TABLE auditoria_logs ADD COLUMN hostname TEXT;")
        except Exception:
            pass

        conn.execute("""
        INSERT INTO auditoria_logs (usuario, perfil, acao, tabela_afetada, registro_id, detalhes_antes, detalhes_depois, justificativa, ip_origem, hostname)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(usuario), str(perfil), str(acao), tabela, registro_id, str(antes) if antes else None, str(depois) if depois else None, justificativa, ip_origem, hostname))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao gravar log de auditoria: {e}")
