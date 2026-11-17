"""Command line for the shared PXD decoder (``python -m libs.pxd``).

Run ``python libs/pxd FILE --stats`` (or
``python -m libs.pxd`` from the repository root) for a generic command
line; there are no per-tree wrappers and every format decodes through this
package.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

from .bundle import Bundle, IndexRecord
from .codec import PxdSample, decode_file, write_wav


def stats_line(sample: PxdSample) -> str:
    audio = sample.samples.astype(np.float32) / 32768.0
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0
    clipped = int(np.sum(np.abs(sample.samples.astype(np.int32)) >= 32767))
    return ('peak %.3f  rms %.3f  declared %d  decoded %d  clipped %d'
            % (peak, rms, sample.declared_count, len(sample.samples), clipped))


def run_bundle(bundle: Bundle, args) -> None:
    print('== %s (%d records, %d bytes)' % (os.path.basename(bundle.data_path),
                                            len(bundle), len(bundle.data)))
    wanted = args.id
    for record in bundle.records:
        if wanted and record.sample_id not in wanted:
            continue
        if args.list:
            print('  id %-5d bank %d  %-14s %8d+%-8d %s'
                  % (record.sample_id, record.bank, record.file, record.offset,
                     record.length, record.label))
            continue
        sample = bundle.decode(record)
        print('  id %-5d %-24s %7d samples  %6.3f s  %r'
              % (record.sample_id, record.label, len(sample.samples),
                 sample.duration, sample.name))
        if args.stats:
            print('      ' + stats_line(sample))
        if args.wav:
            write_wav(args.wav, sample.samples)
            print('      wrote', args.wav)
            args.wav = None


def main(argv=None, *, description: str = 'decode eJay .PXD samples',
         bundle_cls: type[Bundle] = Bundle,
         allow_headerless: bool = False) -> int:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument('files', nargs='+',
                    help='standalone .PXD files, or .INF indexes / bundle files')
    ap.add_argument('--inf', help='index for a bundle given as the file argument')
    ap.add_argument('--id', type=int, action='append',
                    help='decode only this sample id from a bundle')
    ap.add_argument('--wav', help='write a 16 bit mono WAV of the first sample')
    ap.add_argument('--stats', action='store_true', help='print levels per sample')
    ap.add_argument('--list', action='store_true', help='list index records only')
    args = ap.parse_args(argv)

    for path in args.files:
        if path.lower().endswith('.inf'):
            bundle = bundle_cls(os.path.splitext(path)[0], path)
            run_bundle(bundle, args)
        elif args.inf:
            bundle = bundle_cls(path, args.inf)
            run_bundle(bundle, args)
        else:
            sample = decode_file(path, allow_headerless=allow_headerless)
            print('%-30s %7d samples  %6.3f s  header %d  %r'
                  % (os.path.basename(path), len(sample.samples),
                     sample.duration, sample.header_size, sample.name))
            if args.stats:
                print('    ' + stats_line(sample))
            if args.wav:
                write_wav(args.wav, sample.samples)
                print('    wrote', args.wav)
                args.wav = None
    return 0


__all__ = ['main', 'run_bundle', 'stats_line', 'IndexRecord']

