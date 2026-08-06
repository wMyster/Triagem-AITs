import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

def get_db_paths():
    paths = []
    local_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "triagem_ait.db")
    if os.path.exists(local_db):
        paths.append(local_db)
        
    net_db = r"G:\Triagem AITs\triagem_ait.db"
    if os.path.exists(net_db) and net_db not in paths:
        paths.append(net_db)
        
    dist_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "triagem_ait.db")
    if os.path.exists(dist_db) and dist_db not in paths:
        paths.append(dist_db)
        
    return paths

def update_passwords():
    new_passwords = {
        "admin": "admin123!",
        "transporte": "transporte123!",
        "dct": "dct123!"
    }
    
    db_paths = get_db_paths()
    print(f"Atualizando senhas nos bancos encontrados: {db_paths}")

    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            for username, new_pass in new_passwords.items():
                new_hash = generate_password_hash(new_pass)
                cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE username = ?", (new_hash, username))
                print(f" -> [{db_path}] Senha do usuário '{username}' atualizada com sucesso para '{new_pass}'")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Erro ao atualizar banco {db_path}: {e}")

if __name__ == "__main__":
    update_passwords()
