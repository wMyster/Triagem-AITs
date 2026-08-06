import sqlite3
import os
import sys
import shutil
from werkzeug.security import generate_password_hash

def get_db_path():
    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "triagem_ait.db")
    net_dir = r"G:\Triagem AITs"
    net_db = os.path.join(net_dir, "triagem_ait.db")
    
    # If network dir exists
    if os.path.exists(net_dir):
        # If DB doesn't exist in network dir yet, copy local DB if exists
        if not os.path.exists(net_db) and os.path.exists(local_db):
            print(f"Copiando banco local para o compartilhamento de rede: {net_db}")
            try:
                shutil.copy2(local_db, net_db)
            except Exception as e:
                print(f"Erro ao copiar para rede: {e}. Usando banco local.")
                return local_db
        if os.path.exists(net_db):
            return net_db

    # Local fallback
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "triagem_ait.db")
    return local_db

def migrate():
    db_path = get_db_path()
    print(f"Iniciando migração no banco de dados: {db_path}")
    
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()

    # Verify if 'ait' table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ait';")
    if not cursor.fetchone():
        print("Criando tabela 'ait'...")
        cursor.execute("""
        CREATE TABLE ait (
            id INTEGER PRIMARY KEY,
            data_ait TEXT,
            numero_ait TEXT,
            agente TEXT,
            status TEXT,
            observacao TEXT,
            data_digitacao TEXT,
            placa TEXT
        );
        """)

    # 1. Tabela de usuários
    print("Criando tabela 'usuarios'...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nome_completo TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        setor TEXT NOT NULL CHECK(setor IN ('transporte', 'dct', 'admin')),
        ativo INTEGER DEFAULT 1,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Criar usuários padronizados se não existirem
    usuarios_iniciais = [
        ("admin", "Administrador Geral", "admin123", "admin"),
        ("transporte", "Operador Transporte", "transporte123", "transporte"),
        ("dct", "Conferente DCT", "dct123", "dct")
    ]

    for username, nome, senha, setor in usuarios_iniciais:
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        if not cursor.fetchone():
            senha_hash = generate_password_hash(senha)
            cursor.execute("""
            INSERT INTO usuarios (username, nome_completo, senha_hash, setor)
            VALUES (?, ?, ?, ?)
            """, (username, nome, senha_hash, setor))
            print(f" -> Usuário '{username}' ({setor}) criado com sucesso.")

    # 3. Adicionar novas colunas em 'ait' para auditoria e controle de conferência
    print("Atualizando estrutura da tabela 'ait'...")
    existing_columns = [col[1] for col in cursor.execute("PRAGMA table_info(ait);").fetchall()]

    new_columns = [
        ("criado_por", "TEXT"),
        ("criado_em", "DATETIME"),
        ("atualizado_por", "TEXT"),
        ("conferido_por", "TEXT"),
        ("conferido_em", "DATETIME"),
        ("status_conferencia", "TEXT DEFAULT 'PENDENTE'")
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE ait ADD COLUMN {col_name} {col_type};")
            print(f" -> Coluna '{col_name}' adicionada à tabela 'ait'.")

    # Atualizar status_conferencia padrão para registros existentes
    cursor.execute("""
    UPDATE ait 
    SET status_conferencia = 'PENDENTE' 
    WHERE status_conferencia IS NULL OR status_conferencia = '';
    """)

    conn.commit()
    conn.close()
    print("Migração realizada com sucesso no banco principal!")

    # Se estiver usando banco de rede, aplicar migração no banco local também para sincronia
    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "triagem_ait.db")
    if db_path != local_db and os.path.exists(local_db):
        print(f"Aplicando migração também no banco local: {local_db}")
        conn_l = sqlite3.connect(local_db, timeout=30.0)
        conn_l.execute("PRAGMA journal_mode = WAL;")
        cursor_l = conn_l.cursor()
        cursor_l.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome_completo TEXT NOT NULL,
            senha_hash TEXT NOT NULL,
            setor TEXT NOT NULL CHECK(setor IN ('transporte', 'dct', 'admin')),
            ativo INTEGER DEFAULT 1,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        for username, nome, senha, setor in usuarios_iniciais:
            cursor_l.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
            if not cursor_l.fetchone():
                senha_hash = generate_password_hash(senha)
                cursor_l.execute("INSERT INTO usuarios (username, nome_completo, senha_hash, setor) VALUES (?, ?, ?, ?)",
                                 (username, nome, senha_hash, setor))
        existing_cols_l = [col[1] for col in cursor_l.execute("PRAGMA table_info(ait);").fetchall()]
        for col_name, col_type in new_columns:
            if col_name not in existing_cols_l:
                cursor_l.execute(f"ALTER TABLE ait ADD COLUMN {col_name} {col_type};")
        cursor_l.execute("UPDATE ait SET status_conferencia = 'PENDENTE' WHERE status_conferencia IS NULL OR status_conferencia = '';")
        conn_l.commit()
        conn_l.close()
        print("Migração no banco local concluída!")

if __name__ == "__main__":
    migrate()
