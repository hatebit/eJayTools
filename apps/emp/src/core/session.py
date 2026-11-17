"""Application layer: selection, transport and WAV rendering."""

from __future__ import annotations

import queue
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

from .errors import PlayerError
from .mixer import apply_gain, mix_placements
from .model import LoadedSong
from apps.emp.src.format.ports import AudioSink, LoadOptions
from .sinks import WavSink

SinkFactory = Callable[[str], AudioSink]


class PlayerState(str, Enum):
    """Transport states a frontend may display, in their normal order."""

    IDLE = 'idle'
    LOADING = 'loading'
    READY = 'ready'
    PLAYING = 'playing'
    PAUSED = 'paused'
    STOPPED = 'stopped'
    FINISHED = 'finished'


@dataclass(frozen=True)
class TransportSnapshot:
    """Immutable view of a transport, safe to read from a frontend thread."""

    state: PlayerState
    position: int       # absolute sample index
    start_sample: int   # absolute sample index of ``start_bar``
    start_bar: int      # user numbering, as printed by the CLI
    end_bar: int
    bar: int
    total: int          # frames in the selection
    gain: float         # runtime multiplier, not including the song gain
    loop: bool


@dataclass(frozen=True)
class Selection:
    """A bar range in user numbering plus its absolute sample range."""

    start_bar: int
    end_bar: int
    start_sample: int
    end_sample: int
    bar_origin: int


def make_selection(song: LoadedSong, start_bar: int, bars: int) -> Selection:
    """Convert user bar numbers to the absolute range the mixer uses.

    ``bars`` of 0 selects to the end of the song; a negative count is
    rejected rather than producing an empty range.  ``end_bar`` is the raw
    exclusive end index the summary prints: it is 0-based exclusive and
    1-based inclusive at the same time.
    """
    if bars < 0:
        raise PlayerError('bars must be 0 (to the end) or a positive number, '
                          'not %d' % bars)
    start_bar = max(song.bar_origin, start_bar)
    if bars:
        end_bar = min(song.bars, start_bar - song.bar_origin + bars)
    else:
        end_bar = song.bars
    return Selection(start_bar, end_bar,
                     (start_bar - song.bar_origin) * song.bar_samples,
                     end_bar * song.bar_samples,
                     song.bar_origin)


def past_the_end(song: LoadedSong, start_bar: int) -> bool:
    """True when the requested first bar is not in the song."""
    return start_bar - song.bar_origin >= song.bars


class Transport:
    """Pull-based playback state for the sounddevice callback.

    The audio callback only calls :meth:`fill`; a frontend may call
    :meth:`pause`, :meth:`resume`, :meth:`stop`, :meth:`seek_bar` and
    :meth:`set_gain` from its own thread and read :meth:`snapshot` at any
    time.  Those methods assign ints, floats and flags only, so they neither
    block the callback nor need a lock.  One event per bar boundary is queued
    in :attr:`progress` and drained with :meth:`drain_progress`.
    """

    def __init__(self, song: LoadedSong, selection: Selection, loop: bool = False):
        self.song = song
        self.selection = selection
        self.start = selection.start_sample
        self.end = selection.end_sample
        self.loop = loop
        self.position = self.start
        self.finished = False
        self.overflows = 0
        self.gain = 1.0                 # runtime multiplier on ``song.gain``
        self.state = PlayerState.PLAYING
        self.progress: queue.SimpleQueue = queue.SimpleQueue()
        self._last_bar: int | None = None

    def fill(self, outdata: np.ndarray) -> bool:
        """Fill ``outdata``; return True when playback has finished."""
        frames = len(outdata)
        if self.state in (PlayerState.STOPPED, PlayerState.FINISHED):
            outdata.fill(0)
            return True
        if self.end <= self.start:            # nothing selected
            outdata.fill(0)
            self._finish()
            return True
        if self.state is PlayerState.PAUSED:
            outdata.fill(0)
            return False
        filled = 0
        while filled < frames:
            if self.position >= self.end:
                if not self.loop:
                    outdata[filled:].fill(0)
                    self._finish()
                    return True
                self.position = self.start
            count = min(frames - filled, self.end - self.position)
            block = mix_placements(self.song.placements, self.position, count)
            outdata[filled:filled + count, :] = apply_gain(
                block, self.song.gain * self.gain)
            self.position += count
            filled += count
            self._note_bar()
        return False

    # -- frontend controls -------------------------------------------------

    def pause(self) -> None:
        """Freeze playback; the callback keeps writing silence."""
        if self.state is PlayerState.PLAYING:
            self.state = PlayerState.PAUSED

    def resume(self) -> None:
        """Continue a paused transport."""
        if self.state is PlayerState.PAUSED:
            self.state = PlayerState.PLAYING

    def stop(self) -> None:
        """End playback now; the next callback returns True."""
        self.state = PlayerState.STOPPED
        self.finished = True

    def seek_bar(self, bar: int) -> None:
        """Jump to ``bar`` in user numbering, clamped to the selection.

        Seeking on a stopped or finished transport returns it to paused, so a
        frontend can seek and then resume without opening a new transport.
        """
        bar = min(max(int(bar), self.selection.start_bar),
                  self.selection.end_bar)
        self.position = min(
            (bar - self.song.bar_origin) * self.song.bar_samples, self.end)
        self._last_bar = None
        if self.state in (PlayerState.STOPPED, PlayerState.FINISHED):
            self.state = PlayerState.PAUSED
            self.finished = False

    def set_gain(self, gain: float) -> None:
        """Set the runtime multiplier, applied on top of the song gain."""
        gain = float(gain)
        if gain != gain or gain < 0.0:      # NaN or negative
            raise ValueError('gain must be a non-negative number')
        self.gain = gain

    def snapshot(self) -> TransportSnapshot:
        """Return the current state without holding a lock."""
        return TransportSnapshot(
            state=self.state,
            position=self.position,
            start_sample=self.start,
            start_bar=self.selection.start_bar,
            end_bar=self.selection.end_bar,
            bar=self.position // self.song.bar_samples + self.song.bar_origin,
            total=self.end - self.start,
            gain=self.gain,
            loop=self.loop)

    def drain_progress(self) -> list[tuple[int, int, int]]:
        """Every ``(position, total, bar)`` event queued since the last call."""
        events = []
        while True:
            try:
                events.append(self.progress.get_nowait())
            except queue.Empty:
                return events

    # -- internals ---------------------------------------------------------

    def _note_bar(self) -> None:
        """Queue one progress event when the bar under the play head changes."""
        bar = self.position // self.song.bar_samples + self.song.bar_origin
        if bar != self._last_bar:
            self._last_bar = bar
            self.progress.put((self.position - self.start,
                               self.end - self.start, bar))

    def _finish(self) -> None:
        self.finished = True
        if self.state is not PlayerState.STOPPED:
            self.state = PlayerState.FINISHED


class RenderJob:
    """Render a selection to a WAV file, one bar-sized block at a time."""

    def __init__(self, song: LoadedSong, selection: Selection,
                 out_path: str, sink_factory: SinkFactory | None = None):
        self.song = song
        self.selection = selection
        self.out_path = out_path
        self.sink_factory = sink_factory or (
            lambda path: WavSink(path, song.sample_rate))

    def run(self) -> None:
        sink = self.sink_factory(self.out_path)
        try:
            position = self.selection.start_sample
            while position < self.selection.end_sample:
                count = min(self.song.bar_samples,
                            self.selection.end_sample - position)
                block = mix_placements(self.song.placements, position, count)
                sink.write(apply_gain(block, self.song.gain))
                position += count
        finally:
            sink.close()


class PlayerApplication:
    """The only API a frontend needs; owns loading, selection and rendering.

    It is also the state machine: ``open`` retires any current playback,
    moves ``IDLE -> LOADING -> READY`` (back to ``IDLE`` on failure), and
    ``play``/``pause``/``resume``/``stop`` follow the transport; a finished
    transport leaves it ``FINISHED``.
    """

    def __init__(self, adapter, reporter,
                 sink_factory: SinkFactory | None = None):
        self.adapter = adapter
        self.reporter = reporter
        self.sink_factory = sink_factory
        self._state = PlayerState.IDLE
        self.song: LoadedSong | None = None
        self.transport: Transport | None = None

    @property
    def state(self) -> PlayerState:
        """The visible state; a transport owns playback states once it exists."""
        if self.transport is not None:
            return self.transport.state
        return self._state

    @state.setter
    def state(self, state: PlayerState) -> None:
        self._state = state

    def open(self, path: str, options: LoadOptions) -> LoadedSong:
        """Load a mix through the adapter, updating the application state.

        A current transport is stopped and both it and the previously loaded
        song are dropped first, so the application reports its own state
        during the load and a failed load leaves it ``IDLE`` with nothing
        selected.
        """
        self.stop()
        self.song = None
        self.transport = None
        self.state = PlayerState.LOADING
        try:
            song = self.adapter.load(path, options, self.reporter)
        except Exception:
            self.state = PlayerState.IDLE
            raise
        self.song = song
        self.state = PlayerState.READY
        return song

    def play(self, song: LoadedSong, selection: Selection,
             loop: bool) -> Transport:
        """Start a transport for a selection and enter ``PLAYING``."""
        self.transport = Transport(song, selection, loop)
        self.song = song
        self.state = PlayerState.PLAYING
        return self.transport

    def pause(self) -> None:
        """Pause the current transport, if any."""
        if self.transport is not None:
            self.transport.pause()

    def resume(self) -> None:
        """Resume the current transport, if any."""
        if self.transport is not None:
            self.transport.resume()

    def stop(self) -> None:
        """Stop the current transport, if any."""
        if self.transport is not None:
            self.transport.stop()

    def seek_bar(self, bar: int) -> None:
        """Seek the current transport to a user bar number."""
        if self.transport is not None:
            self.transport.seek_bar(bar)

    def set_gain(self, gain: float) -> None:
        """Change the gain of the live transport, or of the loaded song.

        A playing or paused transport carries its own multiplier on top of the
        song gain, and the value becomes that multiplier.  Otherwise the value
        becomes the song gain, which is what the next playback and
        ``render_wav`` start from; a transport left over from an earlier
        playback has its multiplier reset to 1.0 then, so the value is not
        applied twice.
        """
        gain = float(gain)
        if gain != gain or gain < 0.0:      # NaN or negative
            raise ValueError('gain must be a non-negative number')
        transport = self.transport
        if (transport is not None
                and transport.state in (PlayerState.PLAYING,
                                        PlayerState.PAUSED)):
            transport.set_gain(gain)
        elif self.song is not None:
            self.song.gain = gain
            if transport is not None:
                transport.set_gain(1.0)
        elif transport is not None:
            transport.set_gain(gain)

    def snapshot(self) -> TransportSnapshot | None:
        """The current transport snapshot, or None before playback."""
        return None if self.transport is None else self.transport.snapshot()

    def render_wav(self, song: LoadedSong, selection: Selection,
                   out_path: str) -> None:
        RenderJob(song, selection, out_path, self.sink_factory).run()

