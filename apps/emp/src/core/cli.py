"""The shared command-line frontend for the eJay players."""

from __future__ import annotations

import argparse
import os
import sys

from .errors import AudioUnavailable, CatalogError, MixError, PlayerError
from apps.emp.src.format.ports import FormatAdapter, LoadOptions
from .registry import Registry
from .reporting import TextReporter
from .session import (PlayerApplication, make_selection, past_the_end)
from .sinks import SoundDeviceOutput

FORMAT_HELP = 'format of the mix (default: detect from the file signature)'

VERSION = '1.0.0'


def parse_tracks(text: str | None, track_count: int) -> set[int] | None:
    """'1,3' -> {0, 2} (1-based on the command line, 0-based internally)."""
    if not text:
        return None
    tracks = set()
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        number = int(part)
        if not 1 <= number <= track_count:
            raise argparse.ArgumentTypeError('track numbers are 1..%d'
                                             % track_count)
        tracks.add(number - 1)
    return tracks


def _build_parser(registry: Registry, fixed_format: bool, doc: str | None):
    adapter = registry.adapters[0] if fixed_format else None
    if fixed_format and adapter is not None:
        description = adapter.description
    else:
        description = ('play or render a Dance, Rave, HipHop, Dance eJay 2 '
                       'or Techno eJay 2 .MIX')
    ap = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=doc)
    ap.add_argument('--version', action='version',
                    version='%(prog)s ' + VERSION)
    ap.add_argument('mix', help='path to a .MIX file (or just its name)')
    if not fixed_format:
        ap.add_argument('--format', metavar='ID', choices=[
            item.format_id for item in registry.adapters], help=FORMAT_HELP)
    ap.add_argument('--from', dest='start_bar', type=int, default=None,
                    metavar='BAR',
                    help=adapter.from_help if adapter is not None else
                    'first bar to play (0 = the first bar)')
    ap.add_argument('--bars', type=int, default=0, metavar='N',
                    help='bars to play (0 = to the end)')
    ap.add_argument('--solo', metavar='LIST',
                    help='play only these tracks, e.g. 3 or 1,4')
    ap.add_argument('--mute', metavar='LIST', help='mute these tracks')
    ap.add_argument('--gain', type=float, default=None,
                    help='output gain (default: automatic, peak-normalised)')
    ap.add_argument('--loop', action='store_true',
                    help='loop the selected range')
    ap.add_argument('--wav', metavar='OUT',
                    help='render to a WAV file instead of playing')
    supports_catalog = any(item.supports_catalog for item in registry.adapters)
    if supports_catalog:
        ap.add_argument(
            '--catalog', action='append', nargs=3, metavar=('LIST', 'DIR', 'BASE'),
            help=adapter.catalog_help if adapter is not None else
            'add a catalogue list, its sample directory and first id '
            '(repeatable, searched before the built-in lists)')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='log decoded samples and per-track statistics')
    return ap


def _choose_adapter(registry: Registry, fixed_format: bool, args,
                    ap: argparse.ArgumentParser):
    """Return ``(adapter or None, forced)`` from the command line."""
    if fixed_format:
        return registry.adapters[0], False
    if args.format:
        return registry.get(args.format), True
    return None, False


def _locate(registry: Registry, args, adapter,
            forced: bool) -> tuple[str, FormatAdapter] | None:
    """Resolve the positional argument to a path and an adapter."""
    if os.path.exists(args.mix):
        path = args.mix
        if adapter is None:
            adapter = registry.detect(path)
            if adapter is None:
                print('%s: unrecognised mix (unknown signature)' % args.mix,
                      file=sys.stderr)
                return None
        elif forced:
            with open(path, 'rb') as fh:
                head = fh.read(2)
            if not adapter.matches(path, head, os.path.getsize(path)):
                print('%s is not a %s mix' % (args.mix, adapter.display_name),
                      file=sys.stderr)
                return None
        return path, adapter

    found = registry.resolve(args.mix,
                             [adapter] if adapter is not None else None)
    if len(found) == 1:
        return found[0][1], found[0][0]
    if len(found) > 1:
        print('%s is ambiguous:' % args.mix, file=sys.stderr)
        for _item, candidate in found:
            print('  %s' % candidate, file=sys.stderr)
        print('use --format <id> or pass a path', file=sys.stderr)
        return None
    return args.mix, adapter


def main(argv=None, registry: Registry | None = None,
         fixed_format: bool = False, doc: str | None = None) -> int:
    """Run the CLI; return the process exit status."""
    assert registry is not None
    ap = _build_parser(registry, fixed_format, doc)
    args = ap.parse_args(argv)
    reporter = TextReporter()

    adapter, forced = _choose_adapter(registry, fixed_format, args, ap)
    located = _locate(registry, args, adapter, forced)
    if located is None:
        return 2
    path, adapter = located
    if not os.path.exists(path):
        print('no such mix: %s' % args.mix, file=sys.stderr)
        return 2

    catalog_specs = []
    for list_path, sample_dir, base in getattr(args, 'catalog', None) or []:
        if not adapter.supports_catalog:
            ap.error('--catalog is not supported for %s' % adapter.display_name)
        if not os.path.exists(list_path):
            print('no such catalogue list: %s' % list_path, file=sys.stderr)
            return 2
        if not os.path.isdir(sample_dir):
            print('no such sample directory: %s' % sample_dir, file=sys.stderr)
            return 2
        catalog_specs.append((list_path, sample_dir, base))

    solo = parse_tracks(args.solo, adapter.track_count)
    mute = parse_tracks(args.mute, adapter.track_count)
    options = LoadOptions(solo=solo, mute=mute, gain=args.gain,
                          catalog_specs=catalog_specs, verbose=args.verbose)

    application = PlayerApplication(adapter, reporter)
    try:
        song = application.open(path, options)
    except CatalogError as exc:
        print('bad --catalog: %s' % exc, file=sys.stderr)
        return 2
    except MixError as exc:
        print(exc, file=sys.stderr)
        return 2

    start_bar = (args.start_bar if args.start_bar is not None
                 else adapter.default_start_bar)
    if past_the_end(song, start_bar):
        print('bar %d is past the end (%d bars)' % (start_bar, song.bars),
              file=sys.stderr)
        return 2
    try:
        selection = make_selection(song, start_bar, args.bars)
    except PlayerError as exc:
        print(exc, file=sys.stderr)
        return 2

    reporter.info(song.summary())
    if args.verbose:
        reporter.info('  tracks: ' + '  '.join(
            'T%d %d/%d' % (track.index + 1, track.placed, track.distinct)
            for track in song.tracks))
        reporter.info('  peak estimate %.2f -> gain %.2f'
                      % (song.stats.peak, song.gain))
    for note in song.notes:
        reporter.info(note)
    total = selection.end_sample - selection.start_sample
    reporter.info('  playing bars %d..%d (%.1f s)'
                  % (selection.start_bar, selection.end_bar,
                     total / song.sample_rate))

    if args.wav:
        application.render_wav(song, selection, args.wav)
        reporter.info('  wrote %s' % args.wav)
        return 0

    try:
        output = SoundDeviceOutput()
    except AudioUnavailable:
        reporter.warning('sounddevice is not available; use --wav to render '
                         'instead')
        return 2
    if not song.placements:
        reporter.warning('nothing to play: no available samples')
        return 2

    transport = application.play(song, selection, args.loop)

    def on_progress() -> None:
        bar = transport.position // song.bar_samples + song.bar_origin
        reporter.progress(transport.position - selection.start_sample,
                          total, bar)

    try:
        output.run(transport, on_progress)
    except KeyboardInterrupt:
        reporter.info('\n  stopped')
        return 0
    reporter.finished(transport.overflows, selection.end_bar,
                      total / song.sample_rate)
    return 0

