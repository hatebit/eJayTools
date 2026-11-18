# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the ``pxd2wav`` PXD to WAV converter.

Build from the repository root::

    python apps/pxd2wav/packaging/build_pxd2wav.py --clean

The result is a one-dir bundle at ``dist/pxd2wav/`` (``pxd2wav.exe`` on
Windows).  The app decodes through ``libs/pxd``, which it imports at run time
after adding the checkout root to ``sys.path``, so the package is listed as a
hidden import; ``libs/`` is pure Python plus ``numpy``.

``tkinterdnd2`` is what makes drag and drop work: it loads the TkDND binary and
Tcl scripts that ship inside the package, and PyInstaller does not follow a
lazily imported package's data.  Both are collected explicitly so the window
keeps accepting dropped files in the frozen build; if they ever go missing the
app falls back to the file picker instead of failing.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

REPO = Path(SPECPATH).resolve().parents[2]
ENTRY = REPO / 'apps' / 'pxd2wav' / 'src' / 'pxd2wav.py'

datas = collect_data_files('tkinterdnd2')
binaries = collect_dynamic_libs('tkinterdnd2')

a = Analysis(
    [str(ENTRY)],
    pathex=[str(REPO)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # Imported at run time, after the script adds the checkout to sys.path.
        'libs.pxd',
        'libs.pxd.bundle',
        'libs.pxd.codec',
        # Imported lazily, so PyInstaller cannot see it.
        'tkinterdnd2',
    ],
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
    name='pxd2wav',
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
    name='pxd2wav',
)
