"""``python -m libs.pxd`` or ``python libs/pxd``."""

import os
import sys

if __package__ in (None, ''):
    # Started as ``python libs/pxd``: make the repository package importable.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

from libs.pxd.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())


