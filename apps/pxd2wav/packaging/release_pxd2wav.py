"""Build, zip and publish the ``pxd2wav`` GitHub release.

Run from the repository root::

    python apps/pxd2wav/packaging/release_pxd2wav.py --tag pxd2wav-v1.0.0

The shared build, zip and upload logic lives in
``apps/emp/packaging/empbundle.py``; ``gh`` must be installed and
authenticated once with ``gh auth login``.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from apps.emp.packaging.empbundle import release_main  # noqa: E402

if __name__ == '__main__':
    sys.exit(release_main('pxd2wav', sys.argv[1:]))
