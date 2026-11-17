"""Dump Dance eJay 2 ``*.MIX`` files in readable form / verify the decoder.

Usage
-----
    python reverse/dance2/mixdump.py FILE [FILE ...]         text dump
    python reverse/dance2/mixdump.py --json OUTDIR FILE ...  one JSON file per mix
    python reverse/dance2/mixdump.py --verify FILE ...       re-encode and compare
    python reverse/dance2/mixdump.py --all                   every mix in disks/Dance_2/MIX
    python reverse/dance2/mixdump.py --summary               one line per mix
    python reverse/dance2/mixdump.py --pattern FILE ...      drum-pattern timeline
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from libs.mix.dance2 import mixfmt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                    'disks', 'Dance_2')
MIXDIR = os.path.join(ROOT, 'MIX')


def track_label(index: int) -> str:
    return 'T%d' % (index + 1)


def bar_text(bar: float) -> str:
    """Format a bar position, dropping trailing zeros."""
    return ('%.3f' % bar).rstrip('0').rstrip('.')


def pattern_summary(mix: mixfmt.Mix) -> list[str]:
    """Lines describing the decoded drum-pattern block."""
    sections = mixfmt.decode_pattern(mix.pattern)
    if sections is None:
        return ['   drum pattern: %d bytes (does not decode)' % len(mix.pattern)]
    notes = [note for section in sections[:-1] for note in section.notes]
    clips = sum(1 for note in notes if not note.is_hit)
    lines = ['   drum pattern: %d bytes, %d track sections (%d empty), '
             '%d clips, %d hits, event count %d'
             % (len(mix.pattern), len(sections) - 1,
                sum(1 for s in sections[:-1] if not s.notes), clips,
                len(notes) - clips, sections[-1].tail_count)]
    for section in sections[:-1]:
        if section.notes:
            lines.append('      %-4s %3d record(s)  bars %s - %s'
                         % (track_label(section.index - 1), len(section.notes),
                            bar_text(section.notes[0].start_bar),
                            bar_text(section.notes[-1].start_bar)))
    return lines


def timeline_lines(mix: mixfmt.Mix, catalog: mixfmt.Catalog) -> list[str]:
    """One line per pattern record, in track and time order."""
    sections = mixfmt.decode_pattern(mix.pattern)
    if sections is None:
        return ['   drum pattern does not decode']
    lines = []
    for section in sections[:-1]:
        for note in section.notes:
            record = catalog.record_for(note.sample_id)
            lines.append('      bar %-7s %-4s %-4s id %-5d %s'
                         % (bar_text(note.start_bar),
                            track_label(section.index - 1),
                            'hit' if note.is_hit else 'clip', note.sample_id,
                            record.label if record else '?'))
    return lines


def summary_line(path: str, mix: mixfmt.Mix) -> str:
    left = [i + 1 for i, t in enumerate(mix.tracks) if t.pan == 1]
    right = [i + 1 for i, t in enumerate(mix.tracks) if t.pan == 2]
    return ('%-13s %5d B  %-22s %-24s bars=%-3d ev=%-3d L=%-12s R=%-12s'
            % (os.path.basename(path), len(mix.build()), mix.author, mix.title,
               mix.field_04, len(mix.events),
               ','.join(map(str, left)) or '-', ','.join(map(str, right)) or '-'))


def text_dump(path: str, catalog: mixfmt.Catalog) -> str:
    mix = mixfmt.read_mix(path)
    out = ['== %s' % os.path.basename(path)]
    out.append('   signature 0x%04x, %d bpm, field_04=%d, field_0a=%d, field_0e=%d'
               % (mix.signature, mix.bpm, mix.field_04, mix.field_0a,
                  mix.field_0e))
    out.append('   author %r, id %r, title %r'
               % (mix.author, mix.ident, mix.title))
    out.append('   16 tracks (pan 0=both, 1=left, 2=right; volume 0..32767):')
    for index, track in enumerate(mix.tracks):
        out.append('      %-4s pan %-6s volume %5d'
                   % (track_label(index), track.pan_name, track.volume))
    out.append('   sample set %r, marker %d, %d sample kit(s)'
               % (mix.sample_set, mix.marker, len(mix.boxes)))
    for box in mix.boxes:
        out.append('      ids %5d..%-5d  %s' % (box.lo, box.hi, box.name))
    out.append('   drum pads: %d' % len(mix.pads))
    for pad in mix.pads:
        record = catalog.record_for(pad.sample_id)
        label = record.label if record else '?'
        out.append('      pad id %-5d pitch %+3d words %5d %5d %d  %-20s %s'
                   % (pad.sample_id, pad.pitch, pad.word2, pad.word3,
                      pad.word4, pad.name, label))
    out.extend(pattern_summary(mix))
    out.append('   imported sample events: %d' % len(mix.events))
    for event in mix.events:
        out.append('      %-12r %-6r channel 0x%02x pitch %+3d instance %d'
                   % (event.name, event.number, event.channel, event.pitch,
                      event.instance))
    return '\n'.join(out)


def json_dump(path: str, catalog: mixfmt.Catalog) -> dict:
    mix = mixfmt.read_mix(path)
    sections = mixfmt.decode_pattern(mix.pattern)
    doc = {
        'file': os.path.basename(path),
        'signature': '0x%04x' % mix.signature,
        'bpm': mix.bpm,
        'field_04': mix.field_04,
        'field_0a': mix.field_0a,
        'field_0e': mix.field_0e,
        'author': mix.author,
        'ident': mix.ident,
        'title': mix.title,
        'tracks': [{'track': i + 1, 'pan': t.pan, 'pan_name': t.pan_name,
                    'volume': t.volume} for i, t in enumerate(mix.tracks)],
        'trailing_words': list(mix.trailing_words),
        'sample_set': mix.sample_set,
        'marker': mix.marker,
        'boxes': [{'lo': b.lo, 'hi': b.hi, 'name': b.name} for b in mix.boxes],
        'pads': [
            {'sample_id': p.sample_id, 'name': p.name, 'pitch': p.pitch,
             'word2': p.word2, 'word3': p.word3, 'word4': p.word4,
             'catalog': (catalog.record_for(p.sample_id).label
                         if catalog.record_for(p.sample_id) else None)}
            for p in mix.pads],
        'pattern_bytes': len(mix.pattern),
        'pattern_hex': mix.pattern.hex(),
        'pattern_sections': ([
            {'index': section.index,
             'count': len(section.notes) or section.tail_count,
             'notes': [{'kind': 'hit' if n.is_hit else 'clip',
                        'sample_id': n.sample_id,
                        'start_bar': n.start_bar,
                        'block': n.block,
                        'byte0': n.byte0, 'byte1': n.byte1, 'word': n.word}
                       for n in section.notes]}
            for section in sections] if sections else None),
        'events': [
            {'name': e.name, 'number': e.number, 'kind': e.kind,
             'channel': e.channel, 'pitch': e.pitch, 'instance': e.instance}
            for e in mix.events],
        'tail_hex': [e.tail.hex() for e in mix.events],
    }
    return doc


def verify(paths, verbose: bool = False) -> int:
    bad = 0
    for path in paths:
        with open(path, 'rb') as fh:
            original = fh.read()
        mix = mixfmt.Mix.parse(original)
        rebuilt = mix.build()
        ok = rebuilt == original
        print('%-14s %s  (%d bytes)' % (os.path.basename(path),
                                        'OK  ' if ok else 'FAIL',
                                        len(original)))
        if verbose and not ok:
            for i, (a, b) in enumerate(zip(original, rebuilt)):
                if a != b:
                    print('   first difference at 0x%x: %02x != %02x'
                          % (i, a, b))
                    break
        if not ok:
            bad += 1
    print('%d/%d files round-trip byte-identically' % (len(paths) - bad,
                                                        len(paths)))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*')
    ap.add_argument('--all', action='store_true',
                    help='all disks/Dance_2/MIX/*.MIX')
    ap.add_argument('--json', metavar='OUTDIR', help='write JSON dumps')
    ap.add_argument('--verify', action='store_true', help='re-encode and compare')
    ap.add_argument('--summary', action='store_true', help='one line per mix')
    ap.add_argument('--pattern', action='store_true',
                    help='print the drum-pattern timeline only')
    args = ap.parse_args(argv)

    files = list(args.files)
    if args.all or not files:
        files = sorted(glob.glob(os.path.join(MIXDIR, '*.MIX')))
    catalog = mixfmt.dance2_catalog(ROOT)

    if args.verify:
        return 1 if verify(files) else 0

    if args.json:
        os.makedirs(args.json, exist_ok=True)
        for path in files:
            doc = json_dump(path, catalog)
            out = os.path.join(args.json, os.path.splitext(
                os.path.basename(path))[0] + '.json')
            with open(out, 'w', encoding='utf-8') as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False)
            print('wrote', out)
        return 0

    if args.summary:
        for path in files:
            print(summary_line(path, mixfmt.read_mix(path)))
        return 0

    if args.pattern:
        for path in files:
            print('== %s' % os.path.basename(path))
            print('\n'.join(timeline_lines(mixfmt.read_mix(path), catalog)))
        return 0

    for path in files:
        print(text_dump(path, catalog))
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
