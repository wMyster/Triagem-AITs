import sqlite3
import os
import sys
import time
import threading
from datetime import datetime

def get_base_db_path():
    net_dir = r"G:\Triagem AITs"
    net_db = os.path.join(net_dir, "triagem_ait.db")
    if os.path.exists(net_dir) and os.path.exists(net_db):
        return net_db

    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "triagem_ait.db")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "triagem_ait.db")

def get_backup_dir():
    base_db = get_base_db_path()
    db_dir = os.path.dirname(base_db)
    backup_dir = os.path.join(db_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def criar_backup(tipo="MANUAL"):
    """
    Gera um backup consistente usando a API sqlite3.backup().
    Tipos: MANUAL, AUTO, PRE_RESET, PRE_RESTORE, SHUTDOWN
    """
    src_db = get_base_db_path()
    if not os.path.exists(src_db):
        return False, "Banco de dados de origem não encontrado.", None, 0

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"triagem_ait_backup_{tipo}_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        src_conn = sqlite3.connect(src_db, timeout=30.0)
        dst_conn = sqlite3.connect(backup_path)
        
        with dst_conn:
            src_conn.backup(dst_conn)
            
        dst_conn.close()
        src_conn.close()
        
        # Limpar backups antigos mantendo os últimos 50
        limpar_backups_antigos(backup_dir, max_keep=50)
        
        size_bytes = os.path.getsize(backup_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        return True, backup_filename, backup_path, size_mb
    except Exception as e:
        return False, str(e), None, 0

def restaurar_backup(filename):
    """
    Restaura um arquivo de backup para o banco ativo atual, gerando antes uma cópia PRE_RESTORE.
    """
    backup_dir = get_backup_dir()
    target_backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(target_backup_path):
        return False, f"Arquivo de backup '{filename}' não encontrado."

    active_db = get_base_db_path()

    # 1. Gera cópia de segurança antes de restaurar
    ok_pre, pre_name, pre_p, pre_mb = criar_backup(tipo="PRE_RESTORE")
    if not ok_pre:
        return False, f"Falha ao gerar cópia de segurança pré-restauração: {pre_name}"

    # 2. Executa a restauração atômica
    try:
        src_conn = sqlite3.connect(target_backup_path, timeout=30.0)
        dst_conn = sqlite3.connect(active_db, timeout=30.0)
        
        with dst_conn:
            src_conn.backup(dst_conn)
            
        dst_conn.close()
        src_conn.close()
        
        return True, f"Banco de dados restaurado com sucesso a partir de '{filename}'! (Cópia prévia: {pre_name})"
    except Exception as e:
        return False, f"Erro durante a restauração do banco: {e}"

def limpar_backups_antigos(backup_dir, max_keep=50):
    try:
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("triagem_ait_backup_") and f.endswith(".db")]
        files.sort(key=os.path.getmtime, reverse=True)
        if len(files) > max_keep:
            for f_to_delete in files[max_keep:]:
                try:
                    os.remove(f_to_delete)
                except Exception:
                    pass
    except Exception as e:
        print(f"Erro ao limpar backups antigos: {e}")

def listar_backups():
    backup_dir = get_backup_dir()
    backups = []
    if os.path.exists(backup_dir):
        files = [f for f in os.listdir(backup_dir) if f.startswith("triagem_ait_backup_") and f.endswith(".db")]
        files.sort(reverse=True)
        for f in files:
            full_p = os.path.join(backup_dir, f)
            stat = os.stat(full_p)
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            dt_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            
            # Detecta o tipo do backup a partir do nome
            tipo = "MANUAL"
            if "_AUTO_" in f:
                tipo = "AUTOMÁTICO"
            elif "_PRE_RESET_" in f:
                tipo = "PRÉ-RESET"
            elif "_PRE_RESTORE_" in f:
                tipo = "PRÉ-RESTAURAÇÃO"
            elif "_SHUTDOWN_" in f:
                tipo = "ENCERRAMENTO"

            backups.append({
                "filename": f,
                "path": full_p,
                "size_mb": size_mb,
                "data_hora": dt_str,
                "tipo": tipo
            })
    return backups

# --- Thread de Agendamento Automático de Backups ---
_SCHEDULER_STARTED = False

def _backup_scheduler_worker(interval_seconds=14400):  # 4 horas
    time.sleep(10.0)  # Aguarda inicialização completa do sistema
    
    # 1. Executa backup de inicialização diário
    try:
        today_str = datetime.now().strftime("%Y%m%d")
        existing = [b for b in listar_backups() if today_str in b["filename"] and b["tipo"] == "AUTOMÁTICO"]
        if not existing:
            ok, name, _, mb = criar_backup(tipo="AUTO")
            if ok:
                print(f"[BACKUP AGENDADO] Backup automático inicial criado: {name} ({mb} MB)")
    except Exception as e:
        print(f"[BACKUP AGENDADO AVISO] {e}")

    # 2. Loop de execução a cada 4 horas
    while True:
        try:
            time.sleep(interval_seconds)
            ok, name, _, mb = criar_backup(tipo="AUTO")
            if ok:
                print(f"[BACKUP AGENDADO] Backup periódico criado: {name} ({mb} MB)")
        except Exception as e:
            print(f"[BACKUP AGENDADO ERRO] {e}")

def iniciar_agendador_backups():
    global _SCHEDULER_STARTED
    if not _SCHEDULER_STARTED:
        _SCHEDULER_STARTED = True
        t = threading.Thread(target=_backup_scheduler_worker, daemon=True)
        t.start()
        print("[BACKUP AGENDADOR] Serviço de backups automáticos periódicos (a cada 4h) ativado.")

if __name__ == "__main__":
    ok, name, p, mb = criar_backup(tipo="MANUAL")
    if ok:
        print(f"Backup criado com sucesso: {name} ({mb} MB)")
    else:
        print(f"Erro ao criar backup: {name}")
