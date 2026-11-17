"""Build the one-dir ``emp-cli`` bundle with PyInstaller.

Run from the repository root::

    python apps/emp/packaging/build_emp_cli.py --clean

The bundle is written to ``dist/emp-cli/`` (``emp-cli.exe`` on Windows) and
reads the eJay data from ``disks/`` at run time; nothing under ``disks/`` is
packaged.
"""

from __future__ import annotations

import sys

from empbundle import build_main

if __name__ == '__main__':
    sys.exit(build_main('emp-cli', sys.argv[1:]))
