"""Errors raised by the shared eJay player core."""

from __future__ import annotations


class PlayerError(Exception):
    """Base class for errors a frontend reports instead of a traceback."""


class MixError(PlayerError):
    """A mix file could not be decoded by its format adapter."""


class CatalogError(PlayerError):
    """A ``--catalog`` list could not be read."""


class AudioUnavailable(PlayerError):
    """Live output is unavailable (``sounddevice`` is missing or failed)."""
