# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: one-file build of D3LTool v2 (platform aware).

Build:  pyinstaller D3LToolNASA.spec --noconfirm
Result: Windows/Linux -> dist/D3LToolNASA(.exe)
        macOS         -> dist/D3LToolNASA.app (+ onefile binary)

PyInstaller cannot cross-compile: run this spec on each target OS
(or use .github/workflows/build.yml which does it in the cloud).
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
RES = ROOT / 'd3ltool' / 'resources'

block_cipher = None

icon = None
if sys.platform == 'win32':
    icon = str(RES / 'D3L.ico')
elif sys.platform == 'darwin':
    icon = str(RES / 'D3L.icns')

a = Analysis(
    [str(ROOT / 'D3LToolNASA.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(RES), 'd3ltool/resources'),
    ],
    hiddenimports=[
        'boto3',
        'botocore',
        's3fs',
        'fsspec',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='D3LToolNASA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed release build; smoke builds use True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version=None,
)

# macOS .app bundle (onefile exe wrapped)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='D3LToolNASA.app',
        icon=icon,
        bundle_identifier=None,
    )
