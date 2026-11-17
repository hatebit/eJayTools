"""The composition root: one registry holding all five format adapters.

This module is the only player file that names a format tree.
``apps/emp/src/mixplayer.py`` and ``apps/emp/src/mixtui.py`` both import
:data:`REGISTRY` from here, and ``apps/emp/src/core/`` never imports a tree,
so a sixth format means a new adapter plus one line in this file.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from apps.emp.src.core import registry  # noqa: E402
from apps.emp.src.format.dance.adapter import DanceAdapter  # noqa: E402
from apps.emp.src.format.dance2.adapter import Dance2Adapter  # noqa: E402
from apps.emp.src.format.hiphop.adapter import HipHopAdapter  # noqa: E402
from apps.emp.src.format.rave.adapter import RaveAdapter  # noqa: E402
from apps.emp.src.format.techno.adapter import TechnoAdapter  # noqa: E402

REGISTRY = registry.Registry([
    DanceAdapter(),
    RaveAdapter(),
    HipHopAdapter(),
    Dance2Adapter(),
    TechnoAdapter(),
])


