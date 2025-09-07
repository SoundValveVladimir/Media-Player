# -*- mode: python ; coding: utf-8 -*-
import os

# Ищем уникальное имя папки
base_name = 'SoundValve'
build_name = base_name
i = 1
while os.path.exists(os.path.join('dist', build_name)):
    build_name = f"{base_name}_{i}"
    i += 1

# Теперь в переменной build_name лежит НАЗВАНИЕ папки без пути
print(f"Build folder: {build_name}")


a = Analysis(
    ['Player.py'],
    pathex=[],
    binaries=[],
    datas=[('Data', 'Data')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='SoundValve',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
	icon=['Logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=build_name,
)
