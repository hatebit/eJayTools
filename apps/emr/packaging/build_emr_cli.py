"""Build the one-dir ``emr-cli`` bundle with PyInstaller.

Run from the repository root::

    python apps/emr/packaging/build_emr_cli.py --clean

The bundle is written to ``dist/emr-cli/`` (``emr-cli.exe`` on Windows) and
reads the eJay data from ``disks/`` at run time; nothing under ``disks/`` is
packaged.  The build, zip and upload code is shared with the player bundles in
``apps/emp/packaging/empbundle.py``.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from apps.emp.packaging.empbundle import build_main  # noqa: E402

if __name__ == '__main__':
    sys.exit(build_main('emr-cli', sys.argv[1:]))
