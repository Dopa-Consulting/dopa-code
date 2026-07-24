# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

root = Path(".")

added_files = [
    (str(root / "inti" / "models"), "inti/models"),
    (str(root / "inti" / "api"), "inti/api"),
    (str(root / "inti"), "inti"),
]

# Include frontend dist if it exists
dist_dir = root.parent / "frontend-pwa" / "dist"
if dist_dir.exists():
    added_files.append((str(dist_dir), "frontend"))

hidden_imports = [
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "aiosqlite",
    "httpx",
    "pydantic",
    "pydantic_settings",
    "websockets",
    "uvicorn",
    "fastapi",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

a = Analysis(
    [str(root / "main.py")],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="dopa-code-daemon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
