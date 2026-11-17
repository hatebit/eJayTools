"""Command-line frontend for the shared PNG renderer.

``apps/emr/src/mixrender.py`` passes every registered format; each
``apps/emr/src/format/<tree>/mixrender.py`` passes its own format with
``fixed_format=True``.  The renderer detects a song by signature, resolves a
bare name against the trees' ``MIX`` directories, and reports an ambiguous name
rather than guessing.
"""

from __future__ import annotations

import argparse
import glob
import os
import struct
import sys

from apps.emr.src.render.canvas import draw
from apps.emr.src.render.layout import RenderFormat

# The renderer never imports the player core (it stays standard-library only),
# so the version string is mirrored here.  Keep it in step with VERSION in
# apps/emp/src/core/cli.py, which is what the release archives are named after.
VERSION = '1.0.0'


def _build_parser(formats: list[RenderFormat], fixed_format: bool,
                  doc: str | None) -> argparse.ArgumentParser:
    if fixed_format:
        description = 'render %s .MIX arrangements as PNG track grids' \
                      % formats[0].display_name
    else:
        description = ('render Dance, Rave, HipHop, Dance eJay 2 or Techno '
                       'eJay 2 .MIX arrangements as PNG track grids')
    ap = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=doc)
    ap.add_argument('--version', action='version',
                    version='%(prog)s ' + VERSION)
    ap.add_argument('files', nargs='*',
                    help='paths or bare names; default: every mix')
    if not fixed_format:
        ap.add_argument('--format', metavar='ID', choices=[
            item.format_id for item in formats],
            help='format of the mix (default: detect from the file signature)')
    ap.add_argument('--all', action='store_true',
                    help='render every mix in the selected format(s)')
    ap.add_argument('--out', default=None,
                    help='output directory (default: reverse/<format>/images)')
    ap.add_argument('--cell-w', type=int, default=0,
                    help='pixels per bar (default: chosen from song length, '
                         '4..10)')
    ap.add_argument('--cell-h', type=int, default=18,
                    help='pixels per track (default 18)')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='print per-track placement statistics')
    return ap


def _detect(path: str, formats: list[RenderFormat]) -> RenderFormat | None:
    """Return the format whose signature the file carries, or ``None``."""
    try:
        with open(path, 'rb') as fh:
            head = fh.read(2)
    except OSError:
        return None
    if len(head) < 2:
        return None
    signature = struct.unpack('<H', head[:2])[0]
    for item in formats:
        if signature == item.signature:
            return item
    return None


def _resolve(item: RenderFormat, name: str) -> str | None:
    """Resolve ``name`` inside one tree's ``MIX`` directory."""
    filename = name if name.lower().endswith('.mix') else name + '.MIX'
    for candidate in (os.path.join(item.mix_dir, filename),
                      os.path.join(item.mix_dir,
                                   os.path.basename(filename).upper())):
        if os.path.exists(candidate):
            return candidate
    return None


def _locate(name: str, formats: list[RenderFormat],
            forced: bool) -> tuple[str, RenderFormat] | None:
    """Return ``(path, format)`` for one command-line name, or ``None``."""
    if os.path.exists(name):
        path = name
        if forced:
            item = formats[0]
            if _detect(path, formats) is not item:
                print('%s is not a %s mix' % (name, item.display_name),
                      file=sys.stderr)
                return None
            return path, item
        item = _detect(path, formats)
        if item is None:
            print('%s: unrecognised mix (unknown signature)' % name,
                  file=sys.stderr)
            return None
        return path, item

    found: list[tuple[RenderFormat, str]] = []
    for item in formats:
        candidate = _resolve(item, name)
        if candidate is not None:
            found.append((item, candidate))
    if len(found) == 1:
        return found[0][1], found[0][0]
    if len(found) > 1:
        print('%s is ambiguous:' % name, file=sys.stderr)
        for _item, candidate in found:
            print('  %s' % candidate, file=sys.stderr)
        print('use --format <id> or pass a path', file=sys.stderr)
        return None
    print('no such mix: %s' % name, file=sys.stderr)
    return None


def _output_path(path: str, out_dir: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0].lower() + '.png'
    return os.path.join(out_dir, name)


def main(argv=None, formats: list[RenderFormat] | None = None,
         fixed_format: bool = False, doc: str | None = None) -> int:
    """Run the renderer; return the process exit status."""
    assert formats is not None
    ap = _build_parser(formats, fixed_format, doc)
    args = ap.parse_args(argv)

    forced = fixed_format or getattr(args, 'format', None) is not None
    if fixed_format:
        active = formats
    elif getattr(args, 'format', None) is not None:
        active = [item for item in formats if item.format_id == args.format]
    else:
        active = formats

    if args.all or not args.files:
        paths: list[str] = []
        for item in active:
            paths.extend(sorted(glob.glob(
                os.path.join(item.mix_dir, '*.MIX'))))
    else:
        paths = list(args.files)

    located: list[tuple[str, RenderFormat]] = []
    for name in paths:
        found = _locate(name, active, forced)
        if found is None:
            return 2
        located.append(found)

    multiple_formats = len({item.format_id for _path, item in located}) > 1
    failed = 0
    for path, item in located:
        if args.out is None:
            out_dir = item.default_out
        elif multiple_formats:
            out_dir = os.path.join(args.out, item.format_id)
        else:
            out_dir = args.out
        os.makedirs(out_dir, exist_ok=True)
        out = _output_path(path, out_dir)
        try:
            layout = item.layout(path)
            width, height = draw(layout, out, args.cell_w, args.cell_h)
        except (OSError, ValueError, struct.error) as exc:
            print('%-14s %s' % (os.path.basename(path), exc), file=sys.stderr)
            failed += 1
            continue

        if layout.grid_bars is not None and layout.bars > layout.grid_bars:
            length = '%d bars (%d in grid)' % (layout.bars, layout.grid_bars)
        else:
            length = '%d bars' % layout.bars
        print('%-14s %s, %d %s -> %s (%dx%d)'
              % (os.path.basename(path), length, len(layout.spans),
                 layout.unit, out, width, height))
        if args.verbose:
            if any(distinct is not None for _placed, distinct
                   in layout.track_stats):
                line = '  tracks: ' + '  '.join(
                    'T%d %d/%d' % (index + 1, placed, distinct)
                    for index, (placed, distinct)
                    in enumerate(layout.track_stats))
            else:
                line = '  tracks: ' + '  '.join(
                    'T%d %d' % (index + 1, placed)
                    for index, (placed, _distinct)
                    in enumerate(layout.track_stats) if placed)
            print(line)
    return 1 if failed else 0


