"""Dance eJay 2 adapter for the shared player core."""

from __future__ import annotations

import os
import struct

from apps.emp.src.core.errors import MixError
from apps.emp.src.core.model import LoadedSong, Placement, SongStats, TrackInfo
from apps.emp.src.core.peak import auto_gain, bar_peak_sections
from apps.emp.src.core.registry import resolve_mix
from apps.emp.src.format.ports import FormatAdapter, LoadOptions, Reporter
from apps.emp.src.core.sources import BundleSampleSource
from apps.emp.src.paths import data_root
from libs.pxd import SAMPLE_RATE as SR

from libs.mix.dance2 import mixfmt
from .banks import Banks

TRACKS = mixfmt.TRACKS
ROOT = os.path.join(data_root(__file__), 'disks', 'Dance_2')
MIXDIR = os.path.join(ROOT, 'MIX')
#: Pan word -> (left, right) gain.
PAN_GAINS = {0: (1.0, 1.0), 1: (1.0, 0.0), 2: (0.0, 1.0)}


class Dance2Adapter(FormatAdapter):
    """Format adapter for Dance eJay 2's section-based ``*.MIX`` songs."""

    format_id = 'dance2'
    format_version = '1.0.0'
    display_name = 'Dance eJay 2'
    mix_dir = MIXDIR
    track_count = TRACKS
    supports_catalog = False
    bar_origin = 1
    default_start_bar = 1
    description = 'play a Dance eJay 2 .MIX from its decoded pattern block'
    from_help = 'first bar to play (1 = the first bar)'
    catalog_help = None

    def matches(self, path: str, head: bytes, size: int) -> bool:
        """True when the file starts with the Dance eJay 2 signature."""
        return len(head) >= 2 and struct.unpack('<H', head[:2])[0] == mixfmt.SIGNATURE

    def resolve(self, name: str) -> str | None:
        """Accept a path, a bare song name or a name without the suffix."""
        return resolve_mix(MIXDIR, name)

    def load(self, path: str, options: LoadOptions,
             reporter: Reporter) -> LoadedSong:
        """Read a mix, decode the samples it needs and return the model."""
        mix = mixfmt.read_mix(path)
        sections = mix.pattern_sections()
        if sections is None:
            raise MixError('the pattern block of %s does not decode' % path)
        bar_samples = SR * mixfmt.BEATS_PER_BAR * 60 // mix.bpm
        pan = [PAN_GAINS.get(track.pan, (1.0, 1.0)) for track in mix.tracks]
        allowed = set(range(TRACKS))
        if options.solo:
            allowed &= options.solo
        if options.mute:
            allowed -= options.mute

        source = BundleSampleSource(Banks(reporter))
        placements: list[Placement] = []
        placed = [0] * TRACKS
        distinct = [set() for _ in range(TRACKS)]
        missing = 0
        missing_ids: set[int] = set()
        clips = 0
        hits = 0
        last_start = 1.0
        for section in sections[:-1]:
            track = section.index - 1
            notes = section.notes
            for index, note in enumerate(notes):
                last_start = max(last_start, note.start_bar)
                if track not in allowed:
                    continue
                later = next((other.start_bar for other in notes[index + 1:]
                              if other.start_bar > note.start_bar), None)
                audio = source.audio(note.sample_id)
                if audio is None:
                    missing += 1
                    missing_ids.add(note.sample_id)
                    continue
                ref = source.ref(note.sample_id)
                label = ref.label if ref is not None else '?'
                onset = int(round((note.start_bar - 1) * bar_samples))
                stop = onset + len(audio)
                if later is not None:
                    stop = min(stop,
                               int(round((later - 1) * bar_samples)))
                if stop <= onset:
                    continue
                left, right = pan[track]
                placements.append(Placement(onset, stop, audio, left, right,
                                            track, label))
                placed[track] += 1
                distinct[track].add(note.sample_id)
                if note.is_hit:
                    hits += 1
                else:
                    clips += 1

        end = max((p.stop for p in placements), default=0)
        bars = max(1, -(-end // bar_samples))
        arrangement_bars = max(1, int(round(last_start)))
        peak = bar_peak_sections(placements, bars, bar_samples)
        gain = (options.gain if options.gain is not None else auto_gain(peak))

        if options.verbose:
            ids = sorted({note.sample_id for section in sections[:-1]
                          for note in section.notes
                          if section.index - 1 in allowed})
            for sample_id in ids:
                audio = source.audio(sample_id)
                ref = source.ref(sample_id)
                reporter.sample(sample_id,
                                ref.label if ref is not None else '?', None,
                                len(audio) / SR if audio is not None else 0.0)

        notes = []
        if bars > arrangement_bars:
            notes.append('  tail: the last samples ring out to bar %d '
                         '(last record starts at %d)'
                         % (bars, arrangement_bars))
        if missing:
            notes.append('  note: %d records skipped, %d sample ids not on disk'
                         % (missing, len(missing_ids)))

        tracks = [TrackInfo(index, mixfmt.PAN_NAMES.get(mix.tracks[index].pan,
                                                        'unknown'),
                            placed[index], len(distinct[index]))
                  for index in range(TRACKS)]
        used = len(frozenset().union(*distinct)) if distinct else 0
        return LoadedSong(
            path=path, format_id=self.format_id, sample_rate=SR,
            bar_samples=bar_samples, bar_origin=self.bar_origin,
            bars=bars, arrangement_bars=arrangement_bars, tail_bars=bars,
            tracks=tracks, placements=placements,
            stats=SongStats(missing=missing,
                            missing_ids=frozenset(missing_ids),
                            used_samples=used, peak=peak,
                            clips=clips, hits=hits),
            gain=gain,
            detail='%d records placed (%d clips, %d hits)'
                   % (clips + hits, clips, hits),
            notes=notes)

