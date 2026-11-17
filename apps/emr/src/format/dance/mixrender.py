"""Render decoded Dance eJay ``*.MIX`` arrangements as PNG track grids.

Every placement becomes a coloured bar: x = bar, y = track (T1 on top), and
its width is the sample's own length in whole bars (a two-bar loop covers two
bars, a one-shot one).  The canvas also covers the tail of a sample placed
near the end, so it matches what the player actually plays.  Repeated samples
keep the same colour, so loops and fills are visible at a glance, and the
ruler marks every 4 bars (labelled every 8).

The drawing engine is shared with the other four formats in ``apps/emr/src/render/``;
this module supplies only Dance's catalogue, bar length and default output.

    python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images --all
    python apps/emr/src/format/dance/mixrender.py --out reverse/dance/images disks/Dance_eJay/MIX/START.MIX
    python apps/emr/src/format/dance/mixrender.py -v --out reverse/dance/images --all
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))))

from libs.mix.dance import mixfmt  # noqa: E402
from apps.emp.src.paths import data_root  # noqa: E402
from apps.emr.src.render import cli  # noqa: E402
from apps.emr.src.render.layout import RenderFormat, grid_layout  # noqa: E402

#: eJay data and default output are found from the checkout or the bundle.
ROOT = os.path.join(data_root(__file__), 'disks', 'Dance_eJay')
MIXDIR = os.path.join(ROOT, 'MIX')
DEFAULT_OUT = os.path.join(data_root(__file__), 'reverse', 'dance', 'images')

#: Samples are mono 44.1 kHz; at 140 BPM one bar is exactly 75 600 frames.
SAMPLES_PER_BAR = 44100 * mixfmt.BEATS_PER_BAR * 60 // mixfmt.BPM


def layout(path: str):
    """Build Dance eJay's PNG layout for one mix."""
    return grid_layout(mixfmt.read_mix(path), mixfmt.dance_catalogs(ROOT),
                       SAMPLES_PER_BAR, mixfmt.BEATS_PER_BAR, mixfmt.BPM)


FORMAT = RenderFormat(
    format_id='dance',
    display_name='Dance eJay 1.x',
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


