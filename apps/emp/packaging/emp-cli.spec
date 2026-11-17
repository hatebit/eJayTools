# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the unified ``emp-cli`` CLI.

Build from the repository root::

    python -m PyInstaller apps/emp/packaging/emp-cli.spec --noconfirm

The result is a one-dir bundle at ``dist/emp-cli/`` (``emp-cli.exe`` on
Windows).  eJay data is never embedded: the binary reads ``disks/`` from
``EJAY_DATA_ROOT`` or from the nearest folder above the executable that
contains one (see ``apps/emp/src/paths.py``).
"""

from pathlib import Path

REPO = Path(SPECPATH).resolve().parents[2]
ENTRY = REPO / 'apps' / 'emp' / 'src' / 'mixplayer.py'

a = Analysis(
    [str(ENTRY)],
    pathex=[str(REPO)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Imported lazily by the live sound sink, so PyInstaller cannot see it.
        'sounddevice',
    ],
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
    name='emp-cli',
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
    name='emp-cli',
)

