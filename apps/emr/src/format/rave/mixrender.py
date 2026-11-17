"""Render decoded Rave eJay ``*.MIX`` arrangements as PNG track grids.

Every placement becomes a coloured bar: x = bar, y = track (T1 on top), and
its width is the sample's own length in whole bars (a two-bar loop covers two
bars, a one-shot one).  The canvas also covers the tail of a sample placed
near the end, so it matches what the player actually plays.  Repeated samples
keep the same colour, so loops and fills are visible at a glance, and the
ruler marks every 4 bars (labelled every 8).

The drawing engine is shared with the other four formats in ``apps/emr/src/render/``;
this module supplies only Rave's catalogue, bar length and default output.
Rave is also the one tree that ships a headerless ``.PXD`` stream.

    python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images --all
    python apps/emr/src/format/rave/mixrender.py --out reverse/rave/images disks/Rave_eJay/MIX/START.MIX
    python apps/emr/src/format/rave/mixrender.py -v --out reverse/rave/images --all
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))))

from libs.mix.rave import mixfmt
from apps.emp.src.paths import data_root  # noqa: E402
from apps.emr.src.render import cli  # noqa: E402
from apps.emr.src.render.layout import RenderFormat, grid_layout  # noqa: E402

#: eJay data and default output are found from the checkout or the bundle.
ROOT = os.path.join(data_root(__file__), 'disks', 'Rave_eJay')
MIXDIR = os.path.join(ROOT, 'MIX')
DEFAULT_OUT = os.path.join(data_root(__file__), 'reverse', 'rave', 'images')

#: Samples are mono 44.1 kHz; at 180 BPM one bar is exactly 58 800 frames.
SAMPLES_PER_BAR = mixfmt.SAMPLES_PER_BAR


def layout(path: str):
    """Build Rave eJay's PNG layout for one mix."""
    return grid_layout(mixfmt.read_mix(path), mixfmt.rave_catalogs(ROOT),
                       SAMPLES_PER_BAR, mixfmt.BEATS_PER_BAR, mixfmt.BPM,
                       allow_headerless=True)


FORMAT = RenderFormat(
    format_id='rave',
    display_name='Rave eJay 1.x',
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


