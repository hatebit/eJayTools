"""Rave eJay 1.x adapter for the shared player core."""

from __future__ import annotations

import os
import struct

from apps.emp.src.core.errors import CatalogError
from apps.emp.src.core.model import LoadedSong, Placement, SongStats, TrackInfo
from apps.emp.src.core.peak import auto_gain, bar_peak_grid
from apps.emp.src.core.registry import resolve_mix
from apps.emp.src.format.ports import FormatAdapter, LoadOptions, Reporter
from apps.emp.src.core.sources import FileSampleSource
from apps.emp.src.paths import data_root
from libs.pxd import SAMPLE_RATE as SR, decode_file as _decode_file

from libs.mix.rave import mixfmt


def decode_file(path):
    """Decode a standalone Rave ``.PXD`` file, headerless allowed."""
    return _decode_file(path, allow_headerless=True)


BPM = mixfmt.BPM
BEATS_PER_BAR = mixfmt.BEATS_PER_BAR
BAR_SAMPLES = mixfmt.SAMPLES_PER_BAR   # 58 800, exact at 180 BPM
TRACKS = mixfmt.TRACKS
ROOT = os.path.join(data_root(__file__), 'disks', 'Rave_eJay')
MIXDIR = os.path.join(ROOT, 'MIX')


class RaveAdapter(FormatAdapter):
    """Format adapter for Rave eJay 1.x ``*.MIX`` songs."""

    format_id = 'rave'
    format_version = '1.0.0'
    display_name = 'Rave eJay 1.x'
    mix_dir = MIXDIR
    track_count = TRACKS
    supports_catalog = True
    bar_origin = 0
    default_start_bar = 0
    description = 'play a Rave eJay .MIX through sounddevice'
    from_help = None
    catalog_help = ('add a catalogue list, its sample directory and first id '
                    '(repeatable, searched before the built-in Rave list)')

    def matches(self, path: str, head: bytes, size: int) -> bool:
        """True when the file starts with the Rave eJay signature."""
        return len(head) >= 2 and struct.unpack('<H', head[:2])[0] == mixfmt.SIGNATURE

    def resolve(self, name: str) -> str | None:
        """Accept a path, a bare song name or a name without the suffix."""
        return resolve_mix(MIXDIR, name)

    def _catalogs(self, options: LoadOptions):
        catalogs = mixfmt.Catalogs()
        for list_path, sample_dir, base in options.catalog_specs:
            try:
                catalogs.add(list_path, sample_dir, int(base))
            except (OSError, ValueError) as exc:
                raise CatalogError(str(exc)) from exc
        catalogs.extend(mixfmt.rave_catalogs(ROOT))
        return catalogs

    def load(self, path: str, options: LoadOptions,
             reporter: Reporter) -> LoadedSong:
        """Read a mix, decode the samples it needs and return the model."""
        mix = mixfmt.read_mix(path)
        allowed = set(range(TRACKS))
        if options.solo:
            allowed &= options.solo
        if options.mute:
            allowed -= options.mute

        pending = [(bar * BAR_SAMPLES, sample_id, track)
                   for bar, track, sample_id in mix.events()
                   if track in allowed]
        pending.sort()

        placed = [0] * TRACKS
        distinct = [set() for _ in range(TRACKS)]
        for _onset, sample_id, track in pending:
            placed[track] += 1
            distinct[track].add(sample_id)

        source = FileSampleSource(self._catalogs(options), decode_file,
                                  reporter, SR)
        wanted = {sample_id for _onset, sample_id, _track in pending
                  if source.ref(sample_id) is not None}
        if wanted:
            reporter.decoding(len(wanted))

        placements: list[Placement] = []
        missing = 0
        missing_ids: set[int] = set()
        seen: set[int] = set()
        used = 0
        for onset, sample_id, track in pending:
            audio = source.audio(sample_id)
            ref = source.ref(sample_id)
            label = ref.label if ref is not None else '?'
            if sample_id not in seen:
                seen.add(sample_id)
                if options.verbose:
                    if audio is None:
                        reporter.skipped(sample_id, label)
                    else:
                        reporter.sample(sample_id, label,
                                        ref.path if ref is not None else None,
                                        len(audio) / SR)
                if audio is not None:
                    used += 1
            if audio is None:
                missing += 1
                missing_ids.add(sample_id)
                continue
            placements.append(Placement(onset, onset + len(audio), audio,
                                        1.0, 1.0, track, label))

        mix_bars = mix.song_length
        end = max((p.onset + len(p.audio) for p in placements), default=0)
        tail_bars = -(-end // BAR_SAMPLES)          # ceil
        bars = max(mix_bars, tail_bars)
        peak = bar_peak_grid(placements, bars, BAR_SAMPLES)
        gain = (options.gain if options.gain is not None else auto_gain(peak))

        notes = []
        if tail_bars > mix_bars:
            notes.append('  tail: samples ring out to bar %d '
                         '(arrangement ends at %d)' % (tail_bars, mix_bars))
        if missing:
            notes.append('  note: %d placements skipped, %d sample ids not on '
                         'disk' % (missing, len(missing_ids)))

        tracks = [TrackInfo(index, 'centred', placed[index],
                            len(distinct[index]))
                  for index in range(TRACKS)]
        return LoadedSong(
            path=path, format_id=self.format_id, sample_rate=SR,
            bar_samples=BAR_SAMPLES, bar_origin=self.bar_origin,
            bars=bars, arrangement_bars=mix_bars, tail_bars=tail_bars,
            tracks=tracks, placements=placements,
            stats=SongStats(missing=missing,
                            missing_ids=frozenset(missing_ids),
                            used_samples=used, peak=peak),
            gain=gain,
            detail='%d tracks (centred), %d samples used' % (TRACKS, used),
            notes=notes)

