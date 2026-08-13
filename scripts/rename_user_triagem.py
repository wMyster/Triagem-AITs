import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

def update_user_triagem():
    db_paths = [
        r"c:\Projetos Programação\Triagem AIT\triagem_ait.db",
        r"c:\Projetos Programação\Triagem AIT\dist\triagem_ait.db",
        r"G:\Triagem AITs\triagem_ait.db"
    ]
    
    new_hash = generate_password_hash("triagem123!")
    
    print("=== Renomeando usuário 'transporte' para 'triagem' ===")
    for path in db_paths:
        if not os.path.exists(path):
            print(f" -> Ignorado (não encontrado): {path}")
            continue
            
        try:
            conn = sqlite3.connect(path, timeout=10.0)
            cursor = conn.cursor()
            
            # Check if user 'triagem' already exists
            cursor.execute("SELECT id FROM usuarios WHERE username = 'triagem'")
            row_triagem = cursor.fetchone()
            
            if row_triagem:
                cursor.execute("UPDATE usuarios SET senha_hash = ?, nome_completo = 'Operador Triagem' WHERE username = 'triagem'", (new_hash,))
                print(f" [OK] Usuário 'triagem' existente atualizado no banco: {path}")
            else:
                cursor.execute("UPDATE usuarios SET username = 'triagem', nome_completo = 'Operador Triagem', senha_hash = ? WHERE username = 'transporte'", (new_hash,))
                print(f" [OK] Usuário 'transporte' renomeado para 'triagem' no banco: {path}")
                
            conn.commit()
            conn.close()
        except Exception as e:
            print(f" [ERRO] Falha ao atualizar {path}: {e}")

if __name__ == "__main__":
    update_user_triagem()
