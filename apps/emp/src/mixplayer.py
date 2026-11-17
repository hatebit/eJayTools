"""Play or render a Dance, Rave, HipHop, Dance 2 or Techno eJay ``*.MIX``.

One command for all five format trees.  The format is detected from the file
signature, so a path is enough; a bare song name is resolved against every
tree's ``MIX`` directory, and a name that exists in more than one tree is
reported as ambiguous until ``--format`` names the tree.

The five trees stay independent: each one owns its parser, sample ids, pan
rule, timing and wording, and ``apps/emp/src/formats.py`` is the only module
that names all five adapters.  This is the only player command; ``--format``
skips detection and names the tree directly.

    python apps/emp/src/mixplayer.py disks/Dance_eJay/MIX/START.MIX --wav start.wav
    python apps/emp/src/mixplayer.py OTHER.MIX --format dance2 --from 1 --bars 12
    python apps/emp/src/mixplayer.py --format techno WAMBAM.MIX --solo 3 --loop

Options: --format ID, --from BAR, --bars N, --solo 1,3, --mute 8, --gain X,
--loop, --wav OUT, --catalog LIST DIR BASE (repeatable, grid formats only),
--verbose.  ``--from`` is 0-based for the three grid formats (0 = the first
bar) and 1-based for the two section formats, exactly as each adapter defines
it.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from apps.emp.src.core import cli  # noqa: E402
from apps.emp.src.formats import REGISTRY  # noqa: E402

if __name__ == '__main__':
    sys.exit(cli.main(sys.argv[1:], REGISTRY, doc=__doc__))


