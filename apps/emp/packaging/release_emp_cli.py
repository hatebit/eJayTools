"""Build, zip and publish the ``emp-cli`` GitHub release.

Run from the repository root::

    python apps/emp/packaging/release_emp_cli.py --tag emp-cli-v0.1.0

The shared build, zip and upload logic lives in
``apps/emp/packaging/empbundle.py``.
"""

from __future__ import annotations

import sys

from empbundle import release_main

if __name__ == '__main__':
    sys.exit(release_main('emp-cli', sys.argv[1:]))
