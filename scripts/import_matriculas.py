import sqlite3
import os
import sys
import openpyxl

def get_db_paths():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = [
        os.path.join(base_dir, "triagem_ait.db"),
        os.path.join(base_dir, "dist", "triagem_ait.db"),
        r"G:\Triagem AITs\triagem_ait.db"
    ]
    return [p for p in paths if os.path.exists(os.path.dirname(p))]

def ler_matriculas_excel(caminho):
    if not os.path.exists(caminho):
        return []
    wb = openpyxl.load_workbook(caminho)
    sheet = wb.active
    matriculas = []
    for r in sheet.iter_rows(values_only=True):
        for c in r:
            if c is not None:
                s = str(c).strip()
                if s and s.upper() not in ["MATRÍCULA", "MATRICULA", "NONE", "CATEGORIA"]:
                    # Remove .0 se for float
                    if s.endswith(".0"):
                        s = s[:-2]
                    matriculas.append(s)
    return list(dict.fromkeys(matriculas))  # preserva ordem e unicidade

def importar_matriculas():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    file_afts = os.path.join(base_dir, "MATRICULAS AFTS.xlsx")
    file_gcm = os.path.join(base_dir, "MATRICULAS GCM.xlsx")

    afts_list = ler_matriculas_excel(file_afts)
    gcm_list = ler_matriculas_excel(file_gcm)

    print(f"[IMPORTADOR] AFTS encontradas: {len(afts_list)}")
    print(f"[IMPORTADOR] GCM encontradas: {len(gcm_list)}")

    db_paths = get_db_paths()
    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Garante a existência da tabela
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

            # 1. Inserir AFTS (Categoria AGENTE)
            for mat in afts_list:
                cursor.execute("""
                INSERT OR IGNORE INTO agentes_gcm (nome_completo, matricula, categoria, situacao, unidade_setor, criado_por)
                VALUES (?, ?, 'AGENTE', 'ATIVO', 'Fiscalização de Trânsito (AFTS)', 'IMPORTAÇÃO_EXCEL')
                """, (f"Agente Mat. {mat}", mat))

            # 2. Inserir GCM (Categoria GCM)
            for mat in gcm_list:
                cursor.execute("""
                INSERT OR IGNORE INTO agentes_gcm (nome_completo, matricula, categoria, situacao, unidade_setor, criado_por)
                VALUES (?, ?, 'GCM', 'ATIVO', 'Guarda Civil Municipal (GCM)', 'IMPORTAÇÃO_EXCEL')
                """, (f"GCM Mat. {mat}", mat))

            conn.commit()
            total = cursor.execute("SELECT COUNT(*) FROM agentes_gcm").fetchone()[0]
            conn.close()
            print(f"[OK] {db_path} -> Total de servidores cadastrados: {total}")
        except Exception as e:
            print(f"[ERRO] Falha ao importar em {db_path}: {e}")

if __name__ == "__main__":
    importar_matriculas()
