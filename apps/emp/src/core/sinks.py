"""Audio sinks: WAV rendering, discarding, and live sounddevice output."""

from __future__ import annotations

import time
import wave

import numpy as np

from .errors import AudioUnavailable
from apps.emp.src.format.ports import AudioSink, LiveOutput


class NullSink(AudioSink):
    """Discards every block, for benchmarking and tests."""

    def write(self, block: np.ndarray) -> None:
        pass

    def close(self) -> None:
        pass


class WavSink(AudioSink):
    """Writes 16-bit stereo WAV at the song's sample rate."""

    def __init__(self, path: str, sample_rate: int = 44100):
        self.wav = wave.open(path, 'wb')
        self.wav.setnchannels(2)
        self.wav.setsampwidth(2)
        self.wav.setframerate(sample_rate)

    def write(self, block: np.ndarray) -> None:
        pcm = np.clip(block * 32767.0, -32768, 32767).astype('<i2')
        self.wav.writeframes(pcm.tobytes())

    def close(self) -> None:
        self.wav.close()


class SoundDeviceOutput(LiveOutput):
    """Live output through a ``sounddevice`` callback (imported lazily)."""

    def __init__(self):
        try:
            import sounddevice as sd
        except Exception as exc:  # pragma: no cover - only live playback
            raise AudioUnavailable(str(exc)) from exc
        self.sd = sd

    def run(self, transport, on_progress=None, poll: float = 0.1) -> int:
        """Stream the transport; return the overflow count."""
        sd = self.sd

        def callback(outdata, frames, time_info, status) -> None:
            if status:
                transport.overflows += 1
            if transport.fill(outdata):
                raise sd.CallbackStop

        with sd.OutputStream(
                samplerate=transport.song.sample_rate, channels=2,
                dtype='float32', callback=callback) as stream:
            while stream.active and not transport.finished:
                if on_progress is not None:
                    on_progress()
                time.sleep(poll)
        return transport.overflows

