# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the ``emp-tui`` Textual front-end.

Build from the repository root::

    python apps/emp/packaging/build_emp_tui.py

The result is a one-dir bundle at ``dist/emp-tui/`` (``emp-tui.exe`` on
Windows).  ``textual`` ships CSS, syntax data and package metadata, so they are
collected explicitly.  eJay data is never embedded: the binary reads ``disks/``
from ``EJAY_DATA_ROOT`` or from the nearest folder above the executable that
contains one (see ``apps/emp/src/paths.py``).
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

REPO = Path(SPECPATH).resolve().parents[2]
ENTRY = REPO / 'apps' / 'emp' / 'src' / 'mixtui.py'

datas = collect_data_files('textual') + copy_metadata('textual')

a = Analysis(
    [str(ENTRY)],
    pathex=[str(REPO)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Imported lazily by the live sound sink, so PyInstaller cannot see it.
        'sounddevice',
        'textual',
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
    name='emp-tui',
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
    name='emp-tui',
)

