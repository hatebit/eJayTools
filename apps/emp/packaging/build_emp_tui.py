"""Build the one-dir ``emp-tui`` bundle with PyInstaller.

Run from the repository root::

    python apps/emp/packaging/build_emp_tui.py --clean

The bundle is written to ``dist/emp-tui/`` (``emp-tui.exe`` on Windows) and
reads the eJay data from ``disks/`` at run time; nothing under ``disks/`` is
packaged.
"""

from __future__ import annotations

import sys

from empbundle import build_main

if __name__ == '__main__':
    sys.exit(build_main('emp-tui', sys.argv[1:]))
