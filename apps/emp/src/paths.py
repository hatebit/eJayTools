"""Locate the ``disks/`` data folder for a source checkout or a frozen build.

The players read eJay data from ``disks/`` but never embed it.  A source
checkout keeps that folder a fixed number of levels above each module, while a
PyInstaller build runs from a temporary bundle, so for a frozen executable the
search starts next to the executable and walks upwards instead.  In both cases
the first folder containing a ``disks`` directory wins, and ``EJAY_DATA_ROOT``
overrides the search.

This module is standard-library only and names no format.
"""

from __future__ import annotations

import os
import sys

ENV_VAR = 'EJAY_DATA_ROOT'


def data_root(module_file: str, levels_up: int = 5) -> str:
    """Return the directory that contains the ``disks`` data folder.

    ``module_file`` is the caller's ``__file__`` and ``levels_up`` is how many
    directories lie between it and the repository root (five for a module in
    ``apps/emp/src/format/<tree>/``).  ``EJAY_DATA_ROOT`` may name either
    that repository root or the ``disks`` directory itself.
    """
    override = os.environ.get(ENV_VAR)
    if override:
        override = os.path.abspath(override)
        if os.path.basename(override.rstrip('\\/')).lower() == 'disks':
            override = os.path.dirname(override)
        return override

    module_dir = os.path.dirname(os.path.abspath(module_file))
    fallback = os.path.normpath(os.path.join(module_dir, *(['..'] * levels_up)))
    starts = [module_dir]
    if getattr(sys, 'frozen', False):
        starts.insert(0, os.path.dirname(os.path.abspath(sys.executable)))
        fallback = starts[0]

    for start in starts:
        current = start
        while True:
            if os.path.isdir(os.path.join(current, 'disks')):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    return fallback


