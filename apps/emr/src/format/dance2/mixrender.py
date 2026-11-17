"""Render decoded Dance eJay 2 arrangements as PNG track grids.

Every pattern record becomes a coloured bar: x = start bar, y = track (T1 on
top).  Positions are fractional -- a clip can start on any sixteenth of a bar
(``FORMAT.md`` §7) -- so the x axis is drawn from the decoded start bar, not
from a cell index.  A record is drawn for as long as the player sounds it: cut
where the next record on the same track starts, otherwise for the sample's own
length, read from the ``tPxD`` header through the four ``.INF`` indexes without
decoding any audio.  Repeated samples keep the same colour, so loops and fills
are visible at a glance.  The ruler marks every 4 bars and is labelled every 8,
numbered the way ``mixdump.py --pattern`` numbers bars (first bar = 1).

The drawing engine is shared with the other four formats in ``apps/emr/src/render/``;
this module supplies only Dance 2's bundle index, bar length and default output.

    python apps/emr/src/format/dance2/mixrender.py --out reverse/dance2/images --all
    python apps/emr/src/format/dance2/mixrender.py --out reverse/dance2/images OTHER.MIX
    python apps/emr/src/format/dance2/mixrender.py -v --out reverse/dance2/images --all
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))))

from libs.mix.dance2 import mixfmt  # noqa: E402
from apps.emp.src.paths import data_root  # noqa: E402
from apps.emr.src.render import cli  # noqa: E402
from apps.emr.src.render.layout import RenderFormat, section_layout  # noqa: E402
from apps.emr.src.render.samples import BundleIndex  # noqa: E402

#: eJay data and default output are found from the checkout or the bundle.
ROOT = os.path.join(data_root(__file__), 'disks', 'Dance_2')
MIXDIR = os.path.join(ROOT, 'MIX')
DEFAULT_OUT = os.path.join(data_root(__file__), 'reverse', 'dance2', 'images')
PXD_DIR = os.path.join(ROOT, 'D_ejay2', 'PXD')
BUNDLES = ('DANCE20', 'DANCESK4', 'DANCESK5', 'DANCESK6')
SAMPLE_RATE = 44100

_INDEX: BundleIndex | None = None


def _index() -> BundleIndex:
    """The four ``.INF`` indexes, read once per process."""
    global _INDEX
    if _INDEX is None:
        bundles = []
        for name in BUNDLES:
            data_path = os.path.join(PXD_DIR, name)
            inf_path = data_path + '.INF'
            if os.path.exists(data_path) and os.path.exists(inf_path):
                catalog = mixfmt.Catalog(inf_path)
                bundles.append((data_path, catalog.records))
        _INDEX = BundleIndex(bundles)
    return _INDEX


def layout(path: str):
    """Build Dance eJay 2's PNG layout for one mix."""
    mix = mixfmt.read_mix(path)
    bar_samples = SAMPLE_RATE * mixfmt.BEATS_PER_BAR * 60 // mix.bpm
    return section_layout(mix, _index(), bar_samples)


FORMAT = RenderFormat(
    format_id='dance2',
    display_name='Dance eJay 2',
    signature=mixfmt.SIGNATURE,
    mix_dir=MIXDIR,
    default_out=DEFAULT_OUT,
    layout=layout,
)


def main(argv=None) -> int:
    """Run the fixed-format renderer; return the process exit status."""
    return cli.main(argv, [FORMAT], fixed_format=True, doc=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())


