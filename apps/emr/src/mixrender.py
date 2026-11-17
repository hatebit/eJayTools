"""Render a Dance, Rave, HipHop, Dance 2 or Techno eJay ``*.MIX`` as PNG.

One command for all five format trees.  The format is detected from the file
signature, so a path is enough; a bare song name is resolved against every
tree's ``MIX`` directory, and a name that exists in more than one tree is
reported as ambiguous until ``--format`` names the tree.

The five trees stay independent: each one owns its parser, sample ids and
length probe, and ``apps/emr/src/render/registry.py`` is the only module that names
all five render providers.  The per-tree ``apps/emr/src/format/<tree>/mixrender.py``
wrappers still work and take the same options; they just skip detection.

    python apps/emr/src/mixrender.py --all
    python apps/emr/src/mixrender.py disks/Dance_eJay/MIX/START.MIX --out reverse/dance/images
    python apps/emr/src/mixrender.py OTHER.MIX --format dance2 --out reverse/dance2/images

Options: --format ID, --all, --out DIR, --cell-w N, --cell-h N, --verbose,
--version.
Without --out the renderer writes to ``reverse/<format>/images``.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from apps.emr.src.render import cli  # noqa: E402
from apps.emr.src.render.registry import REGISTRY  # noqa: E402

if __name__ == '__main__':
    sys.exit(cli.main(sys.argv[1:], REGISTRY, doc=__doc__))







