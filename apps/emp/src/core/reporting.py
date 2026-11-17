"""Reporters: the only place the core turns state into display text."""

from __future__ import annotations

import sys

from apps.emp.src.format.ports import Reporter


class NullReporter(Reporter):
    """Discards everything, for embedding and tests."""

    def info(self, text: str) -> None:
        pass

    def warning(self, text: str) -> None:
        pass

    def decoding(self, count: int) -> None:
        pass

    def sample(self, sample_id: int, label: str, path: str | None,
               seconds: float) -> None:
        pass

    def skipped(self, sample_id: int, label: str) -> None:
        pass

    def progress(self, position: int, total: int, bar: int) -> None:
        pass

    def finished(self, overflows: int, bar: int, total: float) -> None:
        pass


class TextReporter(NullReporter):
    """The CLI's exact historical wording for both format families."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def info(self, text: str) -> None:
        print(text)

    def warning(self, text: str) -> None:
        print(text, file=sys.stderr)

    def decoding(self, count: int) -> None:
        print('  decoding %d sample files...' % count, flush=True)

    def sample(self, sample_id: int, label: str, path: str | None,
               seconds: float) -> None:
        if path is not None:
            print('  sample %-4d %-36.36s %-20s %6.2f s'
                  % (sample_id, label, path, seconds))
        else:
            print('  sample %-5d %-36.36s %6.2f s'
                  % (sample_id, label, seconds))

    def skipped(self, sample_id: int, label: str) -> None:
        print('  skip   %-4d %-36.36s unavailable' % (sample_id, label))

    def progress(self, position: int, total: int, bar: int) -> None:
        sys.stdout.write('\r  bar %3d  %5.1f / %5.1f s'
                         % (bar, position / self.sample_rate,
                            total / self.sample_rate))
        sys.stdout.flush()

    def finished(self, overflows: int, bar: int, total: float) -> None:
        print('\r  bar %3d  %5.1f / %5.1f s  done%s'
              % (bar, total, total,
                 '  (overflows: %d)' % overflows if overflows else ''))


class RecordingReporter(NullReporter):
    """Appends immutable ``(kind, payload)`` events for tests and UIs."""

    def __init__(self):
        self.events: list[tuple[str, object]] = []

    def info(self, text: str) -> None:
        self.events.append(('info', text))

    def warning(self, text: str) -> None:
        self.events.append(('warning', text))

    def decoding(self, count: int) -> None:
        self.events.append(('decoding', count))

    def sample(self, sample_id: int, label: str, path: str | None,
               seconds: float) -> None:
        self.events.append(('sample', (sample_id, label, path, seconds)))

    def skipped(self, sample_id: int, label: str) -> None:
        self.events.append(('skipped', (sample_id, label)))

    def progress(self, position: int, total: int, bar: int) -> None:
        self.events.append(('progress', (position, total, bar)))

    def finished(self, overflows: int, bar: int, total: float) -> None:
        self.events.append(('finished', (overflows, bar, total)))

