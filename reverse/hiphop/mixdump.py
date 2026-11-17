"""Dump HipHop eJay ``*.MIX`` files in readable form / verify the decoder.

Usage
-----
    python reverse/hiphop/mixdump.py FILE [FILE ...]        text dump
    python reverse/hiphop/mixdump.py --json OUTDIR FILE ... one JSON file per mix
    python reverse/hiphop/mixdump.py --verify FILE ...      re-encode and byte-compare
    python reverse/hiphop/mixdump.py --all                  every mix in disks/Hiphop_eJay/MIX
    python reverse/hiphop/mixdump.py -v FILE                add per-track statistics
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from libs.mix.hiphop import mixfmt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'disks', 'Hiphop_eJay')
MIXDIR = os.path.join(ROOT, 'MIX')


def track_label(track: int) -> str:
    return 'T%d' % (track + 1)


def verbose_lines(mix: mixfmt.Mix, catalog: mixfmt.Catalogs) -> list[str]:
    """Extra per-file statistics printed by ``--verbose``."""
    lines = ['  tracks: ' + '  '.join(
        'T%d %d/%d' % (i + 1, placed, distinct) for i, (placed, distinct)
        in enumerate(mix.track_usage()))]
    kinds = {'pxd': 0, 'wav': 0, 'unresolved': 0}
    for _bar, _track, sample_id in mix.events():
        info = catalog.describe(sample_id)
        path = info['path'] or ''
        if path.startswith('SPECIAL/'):
            kinds['wav'] += 1
        elif path:
            kinds['pxd'] += 1
        else:
            kinds['unresolved'] += 1
    lines.append('  sources: %d .PXD, %d SPECIAL WAV, %d unresolved'
                 % (kinds['pxd'], kinds['wav'], kinds['unresolved']))
    return lines


def bank_line(bank: mixfmt.BankBlock) -> str:
    """One-line description of the bank block fields that are understood."""
    first_words = [int.from_bytes(bank.tables[i:i + 2], 'little')
                   for i in (0, mixfmt.TABLE_BYTES)]
    return ('   bank block: signature 0x%04x, %d list(s), version %r, '
            '%d-byte tables (first words %s), head %s, %d tracks, pan %s'
            % (bank.signature, bank.nlists, bank.version, len(bank.tables),
               first_words, bank.head, bank.track_count,
               ' '.join(bank.pan_name(t) for t in range(mixfmt.TRACKS))))


def text_dump(path: str, catalog: mixfmt.Catalogs, verbose: bool = False) -> str:
    mix = mixfmt.read_mix(path)
    out = []
    out.append('== %s' % os.path.basename(path))
    out.append('   signature 0x%04x, %d bars x %d tracks, %d bpm, %.1f s'
               % (mix.signature, mixfmt.BARS, mixfmt.TRACKS, mixfmt.BPM, mix.duration()))
    out.append('   used: %d bars, %d placed samples, %d distinct samples'
               % (mix.song_length, sum(1 for _ in mix.events()), len(mix.used_samples())))
    if verbose:
        out.extend(verbose_lines(mix, catalog))
    if mix.bank:
        out.append(bank_line(mix.bank))
    else:
        out.append('   bank block: none (built-in samples only)')
    out.append('')
    # per-bar listing
    for bar in range(mix.song_length):
        cells = []
        for track, sid in enumerate(mix.grid[bar]):
            if not sid:
                continue
            info = catalog.describe(sid)
            label = info['name'] or '?'
            cells.append('%s=%-4d %-34s %s' % (track_label(track), sid,
                                               label, info['path'] or ''))
        if cells:
            out.append('  bar %3d  %5.2fs' % (bar, bar * mixfmt.bar_seconds()))
            for cell in cells:
                out.append('      ' + cell)
    return '\n'.join(out)


def json_dump(path: str, catalog: mixfmt.Catalogs) -> dict:
    mix = mixfmt.read_mix(path)
    doc = {
        'file': os.path.basename(path),
        'signature': '0x%04x' % mix.signature,
        'tracks': mixfmt.TRACKS,
        'grid_bars': mixfmt.BARS,
        'song_bars': mix.song_length,
        'bpm': mixfmt.BPM,
        'beats_per_bar': mixfmt.BEATS_PER_BAR,
        'samples_per_bar': mixfmt.BAR_SAMPLES,
        'seconds': round(mix.duration(), 2),
        'bank': None,
        'samples': {},
        'grid': [],
    }
    if mix.bank:
        b = mix.bank
        doc['bank'] = {
            'signature': '0x%04x' % b.signature,
            'nlists': b.nlists,
            'version': b.version,
            'head': list(b.head),
            'track_count': b.track_count,
            'pan': list(b.pan),
            'pan_names': [b.pan_name(t) for t in range(mixfmt.TRACKS)],
            'tables': {'bytes': len(b.tables),
                       'first_words': [int.from_bytes(b.tables[i:i + 2], 'little')
                                       for i in (0, mixfmt.TABLE_BYTES)]},
        }
    for sid in mix.used_samples():
        doc['samples'][str(sid)] = catalog.describe(sid)
    for bar, slots in enumerate(mix.grid[:mix.song_length]):
        doc['grid'].append({'bar': bar,
                            'time': round(bar * mixfmt.bar_seconds(), 3),
                            'slots': [sid if sid else None for sid in slots]})
    return doc


def verify(paths, catalog: mixfmt.Catalogs, verbose: bool = False) -> int:
    bad = 0
    for path in paths:
        with open(path, 'rb') as fh:
            original = fh.read()
        mix = mixfmt.Mix.parse(original)
        rebuilt = mix.build()
        ok = rebuilt == original
        print('%-14s %s  (%d bytes)' % (os.path.basename(path), 'OK  ' if ok else 'FAIL', len(original)))
        if verbose:
            for line in verbose_lines(mix, catalog):
                print(line)
        if not ok:
            bad += 1
            for i, (a, b) in enumerate(zip(original, rebuilt)):
                if a != b:
                    print('   first difference at 0x%x: %02x != %02x' % (i, a, b))
                    break
    print('%d/%d files round-trip byte-identically' % (len(paths) - bad, len(paths)))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*')
    ap.add_argument('--all', action='store_true', help='all disks/Hiphop_eJay/MIX/*.MIX')
    ap.add_argument('--json', metavar='OUTDIR', help='write JSON dumps')
    ap.add_argument('--verify', action='store_true', help='re-encode and compare')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='print per-track and sample-source statistics')
    args = ap.parse_args(argv)

    files = list(args.files)
    if args.all or not files:
        files = sorted(glob.glob(os.path.join(MIXDIR, '*.MIX')))
    catalog = mixfmt.hiphop_catalogs(ROOT)

    if args.verify:
        return 1 if verify(files, catalog, args.verbose) else 0

    if args.json:
        os.makedirs(args.json, exist_ok=True)
        for path in files:
            doc = json_dump(path, catalog)
            out = os.path.join(args.json,
                               os.path.splitext(os.path.basename(path))[0] + '.json')
            with open(out, 'w', encoding='utf-8') as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False)
            print('wrote', out)
            if args.verbose:
                for line in verbose_lines(mixfmt.read_mix(path), catalog):
                    print(line)
        return 0

    for path in files:
        print(text_dump(path, catalog, args.verbose))
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
