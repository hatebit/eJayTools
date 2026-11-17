"""The renderer's composition root: one provider per format tree.

This module and the five ``apps/emr/src/format/<tree>/mixrender.py`` wrappers are the
only renderer files that name a format.  It imports no adapter, no player core
and no ``.PXD`` codec, so ``apps/emr/src/mixrender.py`` stays standard-library only.
"""

from __future__ import annotations

from apps.emr.src.format.dance.mixrender import FORMAT as DANCE
from apps.emr.src.format.dance2.mixrender import FORMAT as DANCE2
from apps.emr.src.format.hiphop.mixrender import FORMAT as HIPHOP
from apps.emr.src.format.rave.mixrender import FORMAT as RAVE
from apps.emr.src.format.techno.mixrender import FORMAT as TECHNO

REGISTRY = [
    DANCE,
    RAVE,
    HIPHOP,
    DANCE2,
    TECHNO,
]


