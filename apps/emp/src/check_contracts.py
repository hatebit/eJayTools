"""Check that every format tree implements the shared contracts.

Usage
-----
    python apps/emp/src/check_contracts.py

The script imports the five trees in one process (as
``libs.mix.dance.mixfmt`` and so on, not as five modules named
``mixfmt``) and verifies that each format library and adapter subclasses the
abstract base classes in :mod:`libs.mix.contracts` and
:mod:`apps.emp.src.format.ports`.  It reads no song data and writes nothing,
so it is a fast structural check; the byte-exact behaviour is still proved by
``reverse/<tree>/mixdump.py --verify --all``.
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from libs.mix.contracts import (BankBlockDocument, GridMix,  # noqa: E402
                                MixDocument, SampleCatalog, SectionMix)
from apps.emp.src.format.ports import FormatAdapter  # noqa: E402

#: mix package, player runtime package, family
TREES = (
    ('libs.mix.dance', 'apps.emp.src.format.dance', 'grid'),
    ('libs.mix.rave', 'apps.emp.src.format.rave', 'grid'),
    ('libs.mix.hiphop', 'apps.emp.src.format.hiphop', 'grid'),
    ('libs.mix.dance2', 'apps.emp.src.format.dance2', 'section'),
    ('libs.mix.techno', 'apps.emp.src.format.techno', 'section'),
)


def check_tree(mix_package: str, runtime_package: str,
               family: str) -> list[str]:
    """Return the contract violations of one tree, empty when it conforms."""
    failures: list[str] = []
    try:
        mixfmt = importlib.import_module(mix_package + '.mixfmt')
    except Exception as exc:  # import error is a failure, not a traceback
        return ['cannot import %s.mixfmt: %s' % (mix_package, exc)]

    base = GridMix if family == 'grid' else SectionMix
    label = '%s.mixfmt' % mix_package

    if not isinstance(getattr(mixfmt, 'SIGNATURE', None), int):
        failures.append('%s: no int SIGNATURE' % label)
    if not isinstance(getattr(mixfmt, 'TRACKS', None), int):
        failures.append('%s: no int TRACKS' % label)
    for name in ('read_mix', 'write_mix'):
        if not callable(getattr(mixfmt, name, None)):
            failures.append('%s: no %s()' % (label, name))

    mix_cls = getattr(mixfmt, 'Mix', None)
    if not (inspect.isclass(mix_cls) and issubclass(mix_cls, MixDocument)):
        failures.append('%s.Mix is not a MixDocument' % label)
    elif not issubclass(mix_cls, base):
        failures.append('%s.Mix is not a %s' % (label, base.__name__))
    elif inspect.isabstract(mix_cls):
        failures.append('%s.Mix leaves abstract methods: %s'
                        % (label, ', '.join(sorted(mix_cls.__abstractmethods__))))

    catalog_cls = getattr(mixfmt, 'Catalog', None)
    if not (inspect.isclass(catalog_cls)
            and issubclass(catalog_cls, SampleCatalog)):
        failures.append('%s.Catalog is not a SampleCatalog' % label)
    elif inspect.isabstract(catalog_cls):
        failures.append('%s.Catalog leaves abstract methods: %s'
                        % (label, ', '.join(sorted(
                            catalog_cls.__abstractmethods__))))

    if family == 'grid':
        bank_cls = getattr(mixfmt, 'BankBlock', None)
        if not (inspect.isclass(bank_cls)
                and issubclass(bank_cls, BankBlockDocument)):
            failures.append('%s.BankBlock is not a BankBlockDocument' % label)

    try:
        adapter_module = importlib.import_module(runtime_package + '.adapter')
    except Exception as exc:
        failures.append('cannot import %s.adapter: %s'
                        % (runtime_package, exc))
        return failures

    adapters = [value for value in vars(adapter_module).values()
                if inspect.isclass(value)
                and value.__module__ == adapter_module.__name__
                and issubclass(value, FormatAdapter)]
    if len(adapters) != 1:
        failures.append('%s.adapter: expected one FormatAdapter, found %d'
                        % (package, len(adapters)))
        return failures
    adapter = adapters[0]
    if inspect.isabstract(adapter):
        failures.append('%s leaves abstract methods: %s'
                        % (adapter.__name__, ', '.join(sorted(
                            adapter.__abstractmethods__))))
    if not adapter.format_id:
        failures.append('%s: empty format_id' % adapter.__name__)
    if not isinstance(adapter.track_count, int) or adapter.track_count <= 0:
        failures.append('%s: bad track_count' % adapter.__name__)

    if not failures:
        print('%-34s %-7s %-8s adapter %s'
              % (mix_package, family, mix_cls.__name__, adapter.__name__))
    return failures


def main(argv: list[str] | None = None) -> int:
    """Check every tree, print one line per pass and return an exit status."""
    del argv
    failures: list[str] = []
    for mix_package, runtime_package, family in TREES:
        failures.extend(check_tree(mix_package, runtime_package, family))
    for failure in failures:
        print('FAIL: ' + failure, file=sys.stderr)
    if failures:
        print('%d contract violation(s)' % len(failures), file=sys.stderr)
        return 1
    print('%d/%d trees implement the shared contracts'
          % (len(TREES), len(TREES)))
    return 0


if __name__ == '__main__':
    sys.exit(main())


