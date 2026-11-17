"""A Textual frontend for the shared eJay player core.

The same ``PlayerApplication`` the CLI uses, driven by a file list: the
directory given on the command line is scanned for ``*.MIX`` files, the left
panel lists them with their detected format, and selecting one loads it.  Play
sends the selected bar range to ``sounddevice``; Export renders the same range
to WAV.  Pause/resume, stop, seek and the live gain multiplier work on the
loaded mix.  Audio still comes from ``sounddevice``; rendering works without
it.

``textual`` is an optional dependency of this file only.  The core and the
CLIs keep working when it is not installed.  The directory is
required and is not searched recursively.  Each track has one table row showing
the catalogue label of the sample sounding on that track; the row clears when
the sample ends.

    python apps/emp/src/mixtui.py disks/Dance_eJay/MIX
    python apps/emp/src/mixtui.py disks/Dance_2/MIX
"""

from __future__ import annotations

import argparse
import bisect
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from apps.emp.src.core.cli import VERSION  # noqa: E402
from apps.emp.src.core.errors import (AudioUnavailable, CatalogError,  # noqa: E402
                                      MixError, PlayerError)
from apps.emp.src.format.ports import FormatAdapter, LoadOptions  # noqa: E402
from apps.emp.src.core.reporting import RecordingReporter  # noqa: E402
from apps.emp.src.core.session import (PlayerApplication, PlayerState,  # noqa: E402
                                       make_selection, past_the_end)
from apps.emp.src.core.sinks import SoundDeviceOutput  # noqa: E402
from apps.emp.src.formats import REGISTRY  # noqa: E402

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import (Button, Checkbox, DataTable, Footer, Header,
                                 Input, ProgressBar, RichLog, Static)
    TEXTUAL_ERROR: Exception | None = None
except ImportError as exc:  # pragma: no cover - optional dependency
    TEXTUAL_ERROR = exc
    App = object            # type: ignore[assignment,misc]


class MixTuiApp(App):  # type: ignore[misc,valid-type]
    """Textual frontend on top of :class:`PlayerApplication`."""

    TITLE = 'eJay mix player'
    SUB_TITLE = 'apps/emp/src/mixtui.py'

    CSS = """
    #controls { width: 46; padding: 0 1; }
    #controls > * { margin-bottom: 1; }
    #mixes-title { height: auto; }
    #mixes { height: 14; }
    .row { height: auto; }
    .row Input { width: 1fr; margin-right: 1; }
    .buttons { height: auto; margin-top: 1; }
    .buttons Button { width: 1fr; min-width: 0; margin-right: 1; }
    #main { width: 1fr; padding: 0 1; }
    #summary { height: auto; padding: 0 0 1 0; }
    #tracks { height: 18; }
    #meter { margin: 1 0; }
    #status { height: 1; }
    #log { height: 1fr; border: round white; padding: 0 1; }
    """

    def __init__(self, directory: str):
        super().__init__()
        self.directory = os.path.abspath(directory)
        self.mixes: list[tuple[str, str, FormatAdapter | None]] = []
        self.mix_adapters: dict[str, FormatAdapter] = {}
        self.application: PlayerApplication | None = None
        self.reporter: RecordingReporter | None = None
        self.song = None
        self.selection = None
        self.summary_text = ''
        self.last_wav: str | None = None
        self.audio_thread: threading.Thread | None = None
        self.timer = None
        self.track_entries: list[list[tuple[int, int, str]]] = []
        self.track_latest_stop: list[int] = []
        self.track_display: list[str] = []

    # -- layout ------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with VerticalScroll(id='controls'):
                yield Static('', id='mixes-title')
                yield DataTable(id='mixes')
                with Horizontal(classes='buttons'):
                    yield Button('Play', id='play', variant='primary')
                    yield Button('Export', id='export')
                yield Input(value='out.wav', id='wav')
                with Horizontal(classes='row'):
                    yield Input(placeholder='from bar', id='start-bar')
                    yield Input(placeholder='bars (0 = all)', id='bars',
                                value='0')
                yield Checkbox('Loop', id='loop')
                with Horizontal(classes='buttons'):
                    yield Button('Pause', id='pause')
                    yield Button('Stop', id='stop')
                with Horizontal(classes='row'):
                    yield Input(placeholder='bar to seek', id='seek-bar')
                    yield Button('Seek', id='seek')
                with Horizontal(classes='row'):
                    yield Input(placeholder='gain multiplier, e.g. 0.8',
                                id='gain')
                    yield Button('Set', id='apply-gain')
            with Vertical(id='main'):
                yield Static('Select a mix to begin.', id='summary')
                yield DataTable(id='tracks')
                yield ProgressBar(id='meter', total=1,
                                  show_eta=False, show_percentage=False)
                yield Static('idle', id='status')
                yield RichLog(id='log', markup=False, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        """Prepare the tables, start the timer and open the first mix."""
        table = self.query_one('#tracks', DataTable)
        table.add_column('#', width=3, key='track')
        table.add_column('pan', width=7, key='pan')
        table.add_column('playing', width=48, key='playing')
        table.zebra_stripes = True
        mixes = self.query_one('#mixes', DataTable)
        mixes.add_column('mix', width=26, key='mix')
        mixes.add_column('format', width=16, key='format')
        mixes.cursor_type = 'row'
        mixes.zebra_stripes = True
        self.timer = self.set_interval(0.1, self._tick)
        self._log('textual %s; %d formats available'
                  % (_textual_version(), len(REGISTRY.adapters)))
        self._populate_mixes()
        if self.mixes:
            mixes.focus()
            self._open_path(self.mixes[0][1])

    def on_unmount(self) -> None:
        """Stop polling before the widgets go away."""
        if self.timer is not None:
            self.timer.stop()

    # -- commands ----------------------------------------------------------

    def _populate_mixes(self) -> None:
        """Fill the left panel from the directory given on the command line."""
        try:
            self.mixes = list_mixes(self.directory)
        except OSError as exc:
            self._log('cannot read %s: %s' % (self.directory, exc))
            self.mixes = []
        self.mix_adapters = {path: adapter
                             for _name, path, adapter in self.mixes
                             if adapter is not None}
        table = self.query_one('#mixes', DataTable)
        table.clear()
        for name, path, adapter in self.mixes:
            table.add_row(name,
                          adapter.display_name if adapter else 'unknown',
                          key=path)
        count = len(self.mixes)
        self.query_one('#mixes-title', Static).update(
            '%d mix%s in %s' % (count, '' if count == 1 else 'es',
                                self.directory))

    def _open_path(self, path: str) -> None:
        """Load the mix at ``path``, replacing any current one."""
        if self.song is not None and self.song.path == path:
            return
        adapter = self.mix_adapters.get(path)
        if adapter is None:
            self._log('%s: unrecognised mix (unknown signature)'
                      % os.path.basename(path))
            return
        self.reporter = RecordingReporter()
        application = PlayerApplication(adapter, self.reporter)
        try:
            song = application.open(path, LoadOptions())
        except (CatalogError, MixError) as exc:
            self._log(str(exc))
            return
        except OSError as exc:
            self._log('cannot read %s: %s' % (path, exc))
            return
        if self.application is not None:
            self.application.stop()      # retire the previous transport
        self.application = application
        self.song = song
        self.selection = None
        self.summary_text = song.summary()
        self.query_one('#summary', Static).update(self.summary_text)
        start = self.query_one('#start-bar', Input)
        if not start.value.strip():
            start.value = str(adapter.default_start_bar)
        table = self.query_one('#tracks', DataTable)
        table.clear()
        for track in song.tracks:
            table.add_row(str(track.index + 1), track.pan_name, '',
                          key=str(track.index))
        self._prepare_tracks(song)
        self._refresh_tracks()
        self._drain_reports()
        self.query_one('#meter', ProgressBar).update(total=1, progress=0)
        self.query_one('#status', Static).update('ready')

    def _play(self) -> None:
        """Start live playback through ``sounddevice``."""
        if self.application is None or self.song is None:
            self._log('select a mix first')
            return
        try:
            selection = self._selection()
        except PlayerError as exc:
            self._log(str(exc))
            return
        except ValueError:
            self._log('from/bars must be whole numbers')
            return
        if not self.song.placements:
            self._log('nothing to play: no available samples')
            return
        try:
            output = SoundDeviceOutput()
        except AudioUnavailable as exc:
            self._log('sounddevice is not available (%s); use Render instead'
                      % exc)
            return
        if self.application.state in (PlayerState.PLAYING,
                                      PlayerState.PAUSED):
            self.application.stop()      # restart from the new selection
        self.selection = selection
        transport = self.application.play(self.song, selection,
                                          self._loop_enabled())
        self._log('playing bars %d..%d (%.1f s)'
                  % (selection.start_bar, selection.end_bar,
                     (selection.end_sample - selection.start_sample)
                     / self.song.sample_rate))
        self._restart_meter()
        self.audio_thread = threading.Thread(
            target=self._run_audio, args=(output, transport), daemon=True)
        self.audio_thread.start()

    def _toggle_pause(self) -> None:
        """Pause a playing transport or resume a paused one."""
        if self.application is None:
            return
        if self.application.state is PlayerState.PAUSED:
            self.application.resume()
            self._log('resumed')
        elif self.application.state is PlayerState.PLAYING:
            self.application.pause()
            self._log('paused')

    def _stop(self) -> None:
        """Stop live playback."""
        if self.application is None:
            return
        self.application.stop()
        self._refresh_tracks()
        self._log('stopped')

    def _seek(self) -> None:
        """Seek the playing transport to the bar in the input."""
        if self.application is None or self.application.snapshot() is None:
            self._log('nothing playing; press Play first')
            return
        text = self.query_one('#seek-bar', Input).value.strip()
        if not text:
            self._log('enter a bar to seek to')
            return
        try:
            bar = int(text)
        except ValueError:
            self._log('seek bar must be a whole number')
            return
        self.application.seek_bar(bar)
        self._log('seek to bar %d' % bar)

    def _apply_gain(self) -> None:
        """Change the gain of the running transport or of the loaded song."""
        if self.application is None:
            self._log('select a mix first')
            return
        text = self.query_one('#gain', Input).value.strip()
        if not text:
            self._log('enter a gain multiplier, e.g. 0.8')
            return
        try:
            value = float(text)
            self.application.set_gain(value)
        except ValueError as exc:
            self._log('bad gain: %s' % exc)
            return
        snapshot = self.application.snapshot()
        effective = self.song.gain * (snapshot.gain if snapshot else 1.0)
        self._log('gain %.2f (effective %.2f)' % (value, effective))

    def _render(self) -> None:
        """Export the selected bars to WAV in a worker thread."""
        if self.application is None or self.song is None:
            self._log('select a mix first')
            return
        try:
            selection = self._selection()
        except PlayerError as exc:
            self._log(str(exc))
            return
        except ValueError:
            self._log('from/bars must be whole numbers')
            return
        target = self.query_one('#wav', Input).value.strip() or 'out.wav'
        application = self.application
        song = self.song
        self.selection = selection
        self._log('rendering bars %d..%d to %s'
                  % (selection.start_bar, selection.end_bar, target))
        threading.Thread(target=self._render_worker,
                         args=(application, song, selection, target),
                         daemon=True).start()

    # -- worker plumbing ---------------------------------------------------

    def _run_audio(self, output, transport) -> None:
        """Block on the live stream, then report back on the UI thread."""
        try:
            overflows = output.run(transport)
        except Exception as exc:        # PortAudio errors and the like
            self.call_from_thread(self._log, 'audio error: %s' % exc)
            return
        snapshot = transport.snapshot()
        self.call_from_thread(self.reporter.finished, overflows,
                              snapshot.end_bar,
                              snapshot.total / transport.song.sample_rate)

    def _render_worker(self, application: PlayerApplication, song, selection,
                       target: str) -> None:
        """Render with the application captured when the job started.

        It is passed in rather than read from ``self`` so that opening
        another mix mid-render cannot redirect the job at a new
        ``PlayerApplication``.
        """
        try:
            application.render_wav(song, selection, target)
        except Exception as exc:
            self.call_from_thread(self._log, 'render failed: %s' % exc)
            return
        self.call_from_thread(self._render_finished, target)

    def _render_finished(self, target: str) -> None:
        """Record and log a completed render on the UI thread."""
        self.last_wav = target
        self._log('wrote %s' % target)

    def _tick(self) -> None:
        """Queue transport progress, drain events and refresh the meter."""
        if self.application is not None:
            transport = self.application.transport
            if transport is not None and self.reporter is not None:
                for position, total, bar in transport.drain_progress():
                    self.reporter.progress(position, total, bar)
        self._drain_reports()
        if self.application is None:
            return
        snapshot = self.application.snapshot()
        self._refresh_tracks()
        if snapshot is None:
            return
        elapsed = snapshot.position - snapshot.start_sample
        self.query_one('#meter', ProgressBar).update(
            total=max(snapshot.total, 1), progress=max(elapsed, 0))
        self.query_one('#status', Static).update(
            '%s  bar %d  %5.1f / %5.1f s  gain %.2f'
            % (snapshot.state.value, snapshot.bar,
               elapsed / self.song.sample_rate,
               snapshot.total / self.song.sample_rate,
               self.song.gain * snapshot.gain))
        pause = self.query_one('#pause', Button)
        pause.label = 'Resume' if snapshot.state is PlayerState.PAUSED \
            else 'Pause'

    def _drain_reports(self) -> None:
        """Move every reporter event into the log."""
        if self.reporter is None:
            return
        events, self.reporter.events = self.reporter.events, []
        for kind, payload in events:
            if kind in ('info', 'warning'):
                self._log(payload)
            elif kind == 'decoding':
                self._log('  decoding %d sample files...' % payload)
            elif kind == 'sample':
                sample_id, label, path, seconds = payload
                self._log('  sample %-4d %-36.36s %6.2f s'
                          % (sample_id, label, seconds))
            elif kind == 'skipped':
                sample_id, label = payload
                self._log('  skip   %-4d %-36.36s unavailable'
                          % (sample_id, label))
            elif kind == 'progress':
                self._log('  bar %3d' % payload[2])
            elif kind == 'finished':
                overflows = payload[0]
                self._log('finished%s'
                          % ('  (overflows: %d)' % overflows
                             if overflows else ''))

    def _prepare_tracks(self, song) -> None:
        """Index each placement by track for the 100 ms display refresh."""
        entries: list[list[tuple[int, int, str]]] = [
            [] for _ in range(len(song.tracks))]
        for placement in song.placements:
            if 0 <= placement.track < len(entries):
                entries[placement.track].append(
                    (placement.onset, placement.stop, placement.label))
        for track_entries in entries:
            track_entries.sort()
        self.track_entries = entries
        self.track_latest_stop = [max((item[1] for item in track_entries),
                                      default=0)
                                  for track_entries in entries]
        self.track_display = [''] * len(entries)

    def _refresh_tracks(self) -> None:
        """Show each track's active sample name, blank when it has stopped."""
        if self.song is None or not self.track_entries:
            return
        snapshot = (None if self.application is None
                    else self.application.snapshot())
        active = (snapshot is not None and snapshot.state in
                  (PlayerState.PLAYING, PlayerState.PAUSED))
        labels = [self._active_label(track, snapshot.position)
                  if active else ''
                  for track in range(len(self.track_entries))]
        table = self.query_one('#tracks', DataTable)
        for track, label in enumerate(labels):
            if label != self.track_display[track]:
                table.update_cell(str(track), 'playing', label)
                self.track_display[track] = label

    def _active_label(self, track: int, position: int) -> str:
        """The latest placement covering ``position`` on ``track``, or ''."""
        entries = self.track_entries[track]
        if (not entries or position < entries[0][0]
                or position >= self.track_latest_stop[track]):
            return ''
        index = bisect.bisect_right(
            entries, (position, float('inf'), '')) - 1
        while index >= 0:
            _onset, stop, label = entries[index]
            if stop > position:
                return label
            index -= 1
        return ''

    def _restart_meter(self) -> None:
        if self.selection is not None:
            self.query_one('#meter', ProgressBar).update(
                total=max(self.selection.end_sample
                          - self.selection.start_sample, 1), progress=0)

    def _log(self, text: str) -> None:
        self.query_one('#log', RichLog).write(text)

    # -- helpers -----------------------------------------------------------

    def _loop_enabled(self) -> bool:
        """Whether the loop checkbox is ticked."""
        return bool(self.query_one('#loop', Checkbox).value)

    def _selection(self):
        """Build the selection from the two bar inputs."""
        assert self.song is not None and self.application is not None
        start_text = self.query_one('#start-bar', Input).value.strip()
        bars_text = self.query_one('#bars', Input).value.strip()
        start_bar = (int(start_text) if start_text
                     else self.application.adapter.default_start_bar)
        bars = int(bars_text) if bars_text else 0
        if past_the_end(self.song, start_bar):
            raise PlayerError('bar %d is past the end (%d bars)'
                              % (start_bar, self.song.bars))
        return make_selection(self.song, start_bar, bars)

    # -- events ------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handler = {
            'play': self._play,
            'pause': self._toggle_pause,
            'stop': self._stop,
            'seek': self._seek,
            'apply-gain': self._apply_gain,
            'export': self._render,
        }.get(event.button.id or '')
        if handler is not None:
            event.stop()
            handler()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open the mix the user picked in the left panel."""
        if event.data_table.id == 'mixes':
            event.stop()
            self._open_path(str(event.row_key.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'seek-bar':
            self._seek()
        elif event.input.id == 'gain':
            self._apply_gain()


def list_mixes(directory: str) -> list[tuple[str, str, FormatAdapter | None]]:
    """Every ``*.MIX`` directly in ``directory``, with its detected format."""
    mixes = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not name.lower().endswith('.mix') or not os.path.isfile(path):
            continue
        try:
            adapter = REGISTRY.detect(path)
        except OSError:
            adapter = None
        mixes.append((name, path, adapter))
    return mixes


def _textual_version() -> str:
    """Installed textual version, for the opening log line."""
    try:
        from importlib.metadata import version
        return version('textual')
    except Exception:                   # pragma: no cover - packaging oddity
        return 'unknown'


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description='Textual frontend for the shared eJay player core.',
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument('--version', action='version',
                    version='%(prog)s ' + VERSION)
    ap.add_argument('directory',
                    help='directory scanned for *.MIX files')
    return ap


def main(argv=None) -> int:
    """Run the TUI; return the process exit status."""
    args = _build_parser().parse_args(argv)
    if TEXTUAL_ERROR is not None:
        print('apps/emp/src/mixtui.py needs the optional textual package:\n'
              '  python -m pip install textual', file=sys.stderr)
        return 2
    if not os.path.isdir(args.directory):
        print('%s: not a directory' % args.directory, file=sys.stderr)
        return 2
    MixTuiApp(args.directory).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())


