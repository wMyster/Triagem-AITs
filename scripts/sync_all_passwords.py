import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

def sync_passwords():
    new_passwords = {
        "admin": "admin123!",
        "triagem": "triagem123!",
        "transporte": "triagem123!",
        "dct": "dct123!",
        "empresa": "empresa123!",
        "consulta": "consulta123!"
    }
    
    db_paths = [
        r"c:\Projetos Programação\Triagem AIT\triagem_ait.db",
        r"c:\Projetos Programação\Triagem AIT\dist\triagem_ait.db",
        r"G:\Triagem AITs\triagem_ait.db"
    ]
    
    print("=== Sincronizando senhas em todos os bancos de dados ===")
    for path in db_paths:
        if not os.path.exists(path):
            print(f" -> Ignorado (não encontrado): {path}")
            continue
            
        try:
            conn = sqlite3.connect(path, timeout=10.0)
            cursor = conn.cursor()
            for username, new_pass in new_passwords.items():
                new_hash = generate_password_hash(new_pass)
                cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE username = ?", (new_hash, username))
            conn.commit()
            conn.close()
            print(f" [OK] Senhas sincronizadas com sucesso no banco: {path}")
        except Exception as e:
            print(f" [ERRO] Falha ao atualizar {path}: {e}")

if __name__ == "__main__":
    sync_passwords()
