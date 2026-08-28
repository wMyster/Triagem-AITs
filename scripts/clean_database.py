import sqlite3
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from werkzeug.security import generate_password_hash

def clean_database():
    db_paths = [
        r"c:\Projetos Programação\Triagem AIT\triagem_ait.db",
        r"c:\Projetos Programação\Triagem AIT\dist\triagem_ait.db",
        r"G:\Triagem AITs\triagem_ait.db"
    ]
    
    # Default users to preserve/re-create (3 usuários essenciais)
    usuarios_padrao = [
        ("admin", "Administrador Geral", "0000", "admin123!", "setor_publico", "admin"),
        ("triagem", "Operador Triagem", "1001", "triagem123!", "setor_publico", "transporte"),
        ("dct", "Conferente DCT", "2002", "dct123!", "setor_publico", "dct")
    ]
    
    print("=== Limpando Banco de Dados (Reset Zerado) ===")
    for path in db_paths:
        if not os.path.exists(path):
            print(f" -> Ignorado (não encontrado): {path}")
            continue
            
        try:
            conn = sqlite3.connect(path, timeout=15.0)
            cursor = conn.cursor()
            
            # Limpar tabelas operacionais
            cursor.execute("DELETE FROM remessa_divergencias")
            cursor.execute("DELETE FROM ait")
            cursor.execute("DELETE FROM remessas")
            cursor.execute("DELETE FROM taloes_transferencias")
            cursor.execute("DELETE FROM taloes")
            cursor.execute("DELETE FROM agentes_gcm")
            cursor.execute("DELETE FROM auditoria_logs")
            cursor.execute("DELETE FROM usuarios")
            
            # Zerar sequências numéricas autoincremento
            cursor.execute("DELETE FROM sqlite_sequence")
            
            # Re-inserir usuários padrões
            for username, nome, mat, senha, vinc, setor in usuarios_padrao:
                senha_hash = generate_password_hash(senha)
                cursor.execute("""
                INSERT INTO usuarios (username, nome_completo, matricula, senha_hash, vinculo, setor, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (username, nome, mat, senha_hash, vinc, setor))
                
            # Re-inserir matrículas oficiais de AFTS e GCM
            try:
                from scripts.import_matriculas import ler_matriculas_excel
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                afts_l = ler_matriculas_excel(os.path.join(base_dir, "MATRICULAS AFTS.xlsx"))
                gcm_l = ler_matriculas_excel(os.path.join(base_dir, "MATRICULAS GCM.xlsx"))
                for m in afts_l:
                    cursor.execute("INSERT OR IGNORE INTO agentes_gcm (nome_completo, matricula, categoria, situacao, unidade_setor, criado_por) VALUES (?, ?, 'AGENTE', 'ATIVO', 'Fiscalização de Trânsito (AFTS)', 'IMPORTAÇÃO_EXCEL')", (f"Agente Mat. {m}", m))
                for m in gcm_l:
                    cursor.execute("INSERT OR IGNORE INTO agentes_gcm (nome_completo, matricula, categoria, situacao, unidade_setor, criado_por) VALUES (?, ?, 'GCM', 'ATIVO', 'Guarda Civil Municipal (GCM)', 'IMPORTAÇÃO_EXCEL')", (f"GCM Mat. {m}", m))
            except Exception as e:
                print(f" [AVISO MATRÍCULAS]: {e}")

            conn.commit()
            
            # Executar VACUUM para otimizar o tamanho do arquivo
            cursor.execute("VACUUM")
            conn.close()
            print(f" [OK] Banco de dados limpo e zerado com sucesso: {path}")
        except Exception as e:
            print(f" [ERRO] Falha ao limpar {path}: {e}")

if __name__ == "__main__":
    clean_database()
