import sqlite3
import os
import sys
import shutil
from werkzeug.security import generate_password_hash

def get_db_path():
    local_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "triagem_ait.db")
    net_dir = r"G:\Triagem AITs"
    net_db = os.path.join(net_dir, "triagem_ait.db")
    
    if os.path.exists(net_dir):
        if not os.path.exists(net_db) and os.path.exists(local_db):
            try:
                shutil.copy2(local_db, net_db)
            except Exception as e:
                print(f"Aviso ao copiar para rede: {e}")
                return local_db
        if os.path.exists(net_db):
            return net_db

    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "triagem_ait.db")
    return local_db

def apply_migrations(db_path):
    print(f"Aplicando esquema v1.1 no banco de dados: {db_path}")
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()

    # Re-create usuarios table to allow new roles
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios_temp AS SELECT * FROM usuarios;")
    cursor.execute("DROP TABLE IF EXISTS usuarios;")
    
    cursor.execute("""
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nome_completo TEXT NOT NULL,
        matricula TEXT,
        senha_hash TEXT NOT NULL,
        vinculo TEXT NOT NULL DEFAULT 'setor_publico' CHECK(vinculo IN ('setor_publico', 'empresa_processamento', 'suporte_tecnico')),
        setor TEXT NOT NULL CHECK(setor IN ('transporte', 'dct', 'empresa', 'admin', 'consulta')),
        ativo INTEGER DEFAULT 1,
        ultimo_acesso DATETIME,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        criado_por TEXT
    );
    """)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios_temp';")
    if cursor.fetchone():
        try:
            cursor.execute("""
            INSERT OR IGNORE INTO usuarios (id, username, nome_completo, senha_hash, setor, ativo, criado_em)
            SELECT id, username, nome_completo, senha_hash, setor, ativo, criado_em FROM usuarios_temp;
            """)
        except Exception as e:
            print(f"Aviso ao restaurar usuarios_temp: {e}")
        cursor.execute("DROP TABLE IF EXISTS usuarios_temp;")

    # Usuários padrões com senhas atualizadas (apenas admin, triagem e dct)
    cursor.execute("DELETE FROM usuarios WHERE username IN ('transporte', 'empresa', 'consulta');")
    usuarios_iniciais = [
        ("admin", "Administrador Geral", "0000", "admin123!", "setor_publico", "admin"),
        ("triagem", "Operador Triagem", "1001", "triagem123!", "setor_publico", "transporte"),
        ("dct", "Conferente DCT", "2002", "dct123!", "setor_publico", "dct")
    ]
    for username, nome, mat, senha, vinc, setor in usuarios_iniciais:
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        rec = cursor.fetchone()
        if not rec:
            hash_s = generate_password_hash(senha)
            cursor.execute("""
            INSERT INTO usuarios (username, nome_completo, matricula, senha_hash, vinculo, setor)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (username, nome, mat, hash_s, vinc, setor))
            print(f" -> Usuário '{username}' ({setor}) criado.")
        else:
            # Force update password hash for standard users
            hash_s = generate_password_hash(senha)
            cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE username = ?", (hash_s, username))

    # 2. Tabela agentes_gcm
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agentes_gcm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_completo TEXT NOT NULL,
        matricula TEXT UNIQUE NOT NULL,
        categoria TEXT NOT NULL CHECK(categoria IN ('AGENTE', 'GCM')),
        situacao TEXT DEFAULT 'ATIVO' CHECK(situacao IN ('ATIVO', 'AFASTADO', 'INATIVO')),
        unidade_setor TEXT,
        observacao TEXT,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        criado_por TEXT
    );
    """)

    # 3. Tabela taloes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taloes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_recibo TEXT,
        data_entrega DATE NOT NULL,
        agente_gcm_id INTEGER NOT NULL,
        numero_inicial INTEGER NOT NULL,
        numero_final INTEGER NOT NULL,
        quantidade_calculada INTEGER NOT NULL,
        situacao TEXT DEFAULT 'EM_UTILIZACAO' CHECK(situacao IN ('CADASTRADO', 'EM_UTILIZACAO', 'PARCIALMENTE_ENTREGUE', 'INTEGRALMENTE_ENTREGUE', 'TRANSFERIDO', 'ENCERRADO')),
        observacao TEXT,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        criado_por TEXT,
        FOREIGN KEY (agente_gcm_id) REFERENCES agentes_gcm(id)
    );
    """)

    # 4. Tabela taloes_transferencias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taloes_transferencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        talao_id INTEGER NOT NULL,
        agente_origem_id INTEGER NOT NULL,
        agente_destino_id INTEGER NOT NULL,
        ait_numero_inicial INTEGER NOT NULL,
        ait_numero_final INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        data_transferencia DATETIME DEFAULT CURRENT_TIMESTAMP,
        motivo TEXT NOT NULL,
        registrado_por TEXT NOT NULL,
        FOREIGN KEY (talao_id) REFERENCES taloes(id),
        FOREIGN KEY (agente_origem_id) REFERENCES agentes_gcm(id),
        FOREIGN KEY (agente_destino_id) REFERENCES agentes_gcm(id)
    );
    """)

    # 5. Tabela remessas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remessas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_remessa TEXT UNIQUE NOT NULL,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        criado_por TEXT NOT NULL,
        quantidade_aits INTEGER DEFAULT 0,
        situacao TEXT DEFAULT 'EM_PREPARACAO' CHECK(situacao IN ('EM_PREPARACAO', 'FECHADA', 'ENVIADA', 'EM_CONFERENCIA', 'RECEBIDA_INTEGRALMENTE', 'COM_DIVERGENCIA', 'CANCELADA')),
        data_envio_fisico DATE,
        data_fechamento DATETIME,
        data_recebimento_empresa DATETIME,
        observacao TEXT
    );
    """)

    # 6. Atualizar estrutura da tabela ait
    cols_ait = [c[1] for c in cursor.execute("PRAGMA table_info(ait);").fetchall()]
    new_cols_ait = [
        ("codigo_barras", "TEXT"),
        ("talao_id", "INTEGER"),
        ("agente_gcm_id", "INTEGER"),
        ("agente_original_id", "INTEGER"),
        ("remessa_id", "INTEGER"),
        ("forma_entrada", "TEXT DEFAULT 'DIGITACAO'"),
        ("status_conferencia", "TEXT DEFAULT 'PENDENTE'")
    ]
    for c_name, c_type in new_cols_ait:
        if c_name not in cols_ait:
            cursor.execute(f"ALTER TABLE ait ADD COLUMN {c_name} {c_type};")

    # 7. Tabela remessa_divergencias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remessa_divergencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        remessa_id INTEGER NOT NULL,
        ait_id INTEGER NOT NULL,
        situacao_informada TEXT NOT NULL CHECK(situacao_informada IN ('NAO_LOCALIZADO', 'ILEGIVEL', 'DANIFICADO', 'OUTRO')),
        observacao_empresa TEXT,
        registrado_por_empresa TEXT NOT NULL,
        data_hora_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        situacao_analise TEXT DEFAULT 'ABERTA' CHECK(situacao_analise IN ('ABERTA', 'EM_ANALISE', 'RESOLVIDA', 'CANCELADA')),
        providencia_setor TEXT,
        resolvido_por_setor TEXT,
        data_hora_resolucao DATETIME,
        FOREIGN KEY (remessa_id) REFERENCES remessas(id),
        FOREIGN KEY (ait_id) REFERENCES ait(id)
    );
    """)

    # 8. Tabela auditoria_logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        perfil TEXT NOT NULL,
        acao TEXT NOT NULL,
        tabela_afetada TEXT,
        registro_id INTEGER,
        detalhes_antes TEXT,
        detalhes_depois TEXT,
        justificativa TEXT,
        ip_origem TEXT,
        hostname TEXT,
        data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Garantir colunas novas caso a tabela já exista
    try:
        cols = [row[1] for row in cursor.execute("PRAGMA table_info(auditoria_logs)").fetchall()]
        if "ip_origem" not in cols:
            cursor.execute("ALTER TABLE auditoria_logs ADD COLUMN ip_origem TEXT;")
        if "hostname" not in cols:
            cursor.execute("ALTER TABLE auditoria_logs ADD COLUMN hostname TEXT;")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print(f"Migração v1.1 concluída com sucesso para {db_path}!")

def migrate():
    main_db = get_db_path()
    apply_migrations(main_db)

    local_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "triagem_ait.db")
    if main_db != local_db and os.path.exists(local_db):
        apply_migrations(local_db)

if __name__ == "__main__":
    migrate()
