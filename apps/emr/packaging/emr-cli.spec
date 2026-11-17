# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the unified ``emr-cli`` PNG renderer.

Build from the repository root::

    python apps/emr/packaging/build_emr_cli.py --clean

The result is a one-dir bundle at ``dist/emr-cli/`` (``emr-cli.exe`` on
Windows).  eJay data is never embedded: the binary reads ``disks/`` from
``EJAY_DATA_ROOT`` or from the nearest folder above the executable that
contains one (see ``apps/emp/src/paths.py``).

The renderer is standard-library only, so the bundle carries no third-party
packages -- the parsers it imports from ``libs/mix/`` are pure Python.
"""

from pathlib import Path

REPO = Path(SPECPATH).resolve().parents[2]
ENTRY = REPO / 'apps' / 'emr' / 'src' / 'mixrender.py'

a = Analysis(
    [str(ENTRY)],
    pathex=[str(REPO)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='emr-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='emr-cli',
)
