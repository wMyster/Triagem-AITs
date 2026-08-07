import sqlite3
import os
import sys
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

def criar_backup():
    """Gera um backup consistente usando a API sqlite3.backup()."""
    src_db = get_base_db_path()
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"triagem_ait_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        src_conn = sqlite3.connect(src_db, timeout=30.0)
        dst_conn = sqlite3.connect(backup_path)
        
        with dst_conn:
            src_conn.backup(dst_conn)
            
        dst_conn.close()
        src_conn.close()
        
        # Limpar backups antigos mantendo os últimos 30
        limpar_backups_antigos(backup_dir, max_keep=30)
        
        size_bytes = os.path.getsize(backup_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        return True, backup_filename, backup_path, size_mb
    except Exception as e:
        return False, str(e), None, 0

def limpar_backups_antigos(backup_dir, max_keep=30):
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
            backups.append({
                "filename": f,
                "path": full_p,
                "size_mb": size_mb,
                "data_hora": dt_str
            })
    return backups

if __name__ == "__main__":
    ok, name, p, mb = criar_backup()
    if ok:
        print(f"Backup criado com sucesso: {name} ({mb} MB)")
    else:
        print(f"Erro ao criar backup: {name}")
