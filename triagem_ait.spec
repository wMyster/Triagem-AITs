# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('audit.py', '.'),
        ('app_icon.ico', '.')
    ],
    hiddenimports=['audit', 'sqlite3', 'werkzeug.security'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='triagem_ait',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)

# Sincronização automática do banco de dados na compilação
spec_dir = SPECPATH if 'SPECPATH' in globals() else os.path.dirname(os.path.abspath(__file__))
dist_dir = DISTPATH if 'DISTPATH' in globals() else os.path.join(spec_dir, 'dist')

src_db = os.path.join(spec_dir, 'triagem_ait.db')
dst_db = os.path.join(dist_dir, 'triagem_ait.db')

if os.path.exists(src_db):
    print(f"\n[INFO] Sincronizando banco de dados durante a compilação...")
    print(f"[INFO] Origem: {src_db}")
    print(f"[INFO] Destino: {dst_db}")
    
    try:
        os.makedirs(dist_dir, exist_ok=True)
        shutil.copy2(src_db, dst_db)
        print(f"[INFO] Banco de dados sincronizado com sucesso!\n")
    except Exception as e:
        print(f"[ERROR] Não foi possível copiar o banco de dados: {e}")
else:
    print(f"\n[WARNING] Banco de dados original não encontrado em '{src_db}'.\n")
