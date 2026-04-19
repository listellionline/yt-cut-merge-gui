# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os

block_cipher = None

project_root = Path(os.getcwd())
src_root = project_root / "src"
assets_root = project_root / "assets"

icon_file = str(assets_root / "app.ico") if (assets_root / "app.ico").exists() else None

a = Analysis(
    [str(src_root / "yt_cut_merge" / "gui.py")],
    pathex=[str(src_root), str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "VERSION"), "."),
        (str(project_root / "version.json"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="yt_cut_merge_gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="yt_cut_merge_gui",
)
