import sqlite3
import os
import sys

def get_db_path():
    net_dir = r"G:\Triagem AITs"
    net_db = os.path.join(net_dir, "triagem_ait.db")
    if os.path.exists(net_dir) and os.path.exists(net_db):
        return net_db
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "triagem_ait.db")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "triagem_ait.db")

def log_auditoria(usuario, perfil, acao, tabela=None, registro_id=None, antes=None, depois=None, justificativa=None):
    try:
        conn = sqlite3.connect(get_db_path(), timeout=10.0)
        conn.execute("""
        INSERT INTO auditoria_logs (usuario, perfil, acao, tabela_afetada, registro_id, detalhes_antes, detalhes_depois, justificativa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(usuario), str(perfil), str(acao), tabela, registro_id, str(antes) if antes else None, str(depois) if depois else None, justificativa))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao gravar log de auditoria: {e}")
