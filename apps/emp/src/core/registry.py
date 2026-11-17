"""Adapter registry, signature detection and bare-name resolution."""

from __future__ import annotations

import os

from apps.emp.src.format.ports import FormatAdapter


def resolve_mix(mix_dir: str, name: str) -> str:
    """Resolve a bare song name against one tree's ``MIX`` directory.

    A name that exists as given is returned unchanged, and so is a name no
    candidate matches, so the caller reports the missing file itself.
    """
    if os.path.exists(name):
        return name
    filename = name if name.lower().endswith('.mix') else name + '.MIX'
    for candidate in (os.path.join(mix_dir, filename),
                      os.path.join(mix_dir,
                                   os.path.basename(filename).upper())):
        if os.path.exists(candidate):
            return candidate
    return name


class Registry:
    """An ordered set of format adapters."""

    def __init__(self, adapters: list[FormatAdapter]):
        self.adapters = list(adapters)
        self.by_id = {adapter.format_id: adapter for adapter in self.adapters}

    def get(self, format_id: str) -> FormatAdapter | None:
        """Adapter with this ``--format`` id, if any."""
        return self.by_id.get(format_id)

    def detect(self, path: str) -> FormatAdapter | None:
        """Adapter whose signature matches the file, if any."""
        with open(path, 'rb') as fh:
            head = fh.read(2)
        size = os.path.getsize(path)
        for adapter in self.adapters:
            if adapter.matches(path, head, size):
                return adapter
        return None

    def resolve(self, name: str, adapters=None) -> list[tuple[FormatAdapter, str]]:
        """Every existing mix a bare name resolves to, in adapter order."""
        found = []
        for adapter in (adapters if adapters is not None else self.adapters):
            path = adapter.resolve(name)
            if path is not None and path != name and os.path.exists(path):
                found.append((adapter, path))
        return found

