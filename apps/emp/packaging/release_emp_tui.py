"""Build, zip and publish the ``emp-tui`` GitHub release.

Run from the repository root::

    python apps/emp/packaging/release_emp_tui.py --tag emp-tui-v0.1.0

The shared build, zip and upload logic lives in
``apps/emp/packaging/empbundle.py``.
"""

from __future__ import annotations

import sys

from empbundle import release_main

if __name__ == '__main__':
    sys.exit(release_main('emp-tui', sys.argv[1:]))
