"""Convert eJay ``.PXD`` samples to 16 bit mono WAV files.

Two front ends over the shared decoder in ``libs/pxd``:

* ``python apps/pxd2wav/src/pxd2wav.py SAMPLE.PXD [OUT.WAV]`` converts one
  standalone sample; ``... BUNDLE.INF --id 1512 [OUT.WAV]`` takes one record of
  an eJay 2 bundle, and ``--list`` prints the ids an index holds.
* ``python apps/pxd2wav/src/pxd2wav.py`` opens a Tk window: drop (or browse to)
  a ``.PXD``, an ``.INF`` or an extensionless bundle file, filter its records by
  id or name, then save the chosen sample as a WAV.

``--check`` prints the decoder, Tk and drag-and-drop availability of the
build; it is how the packaged bundle is smoke-tested.

This app holds no format logic; the decoding is the one implementation every
tree uses.  It needs ``numpy`` like the rest of the codec and ``tkinter``
(ships with CPython on Windows) for the window.  Drag and drop also wants
``tkinterdnd2``; without it the window still works through the file picker.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

VERSION = '1.0.0'


def _bootstrap() -> None:
    """Make ``libs.pxd`` importable when started as a script from any folder."""
    root = Path(__file__).resolve().parents[3]
    if (root / 'libs' / 'pxd' / '__init__.py').is_file() and str(root) not in sys.path:
        sys.path.insert(0, str(root))


_bootstrap()

from libs.pxd.bundle import Bundle, IndexRecord  # noqa: E402
from libs.pxd.codec import PxdSample, decode_file, write_wav  # noqa: E402

try:  # the window is optional, the headless conversion is not
    import tkinter as tk
    from tkinter import filedialog, ttk
except ImportError:  # pragma: no cover - depends on how Python was built
    tk = None

try:  # drag and drop needs an extra package; everything else works without it
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - depends on the environment
    DND_FILES = ''
    TkinterDnD = None


def bundle_paths(path: Path) -> tuple[Path, Path] | None:
    """Return ``(data, index)`` when ``path`` names an eJay 2 bundle.

    Bundles are an ``.INF`` index plus a data file of the same name without an
    extension (``DANCE20.INF`` and ``DANCE20``), so either half identifies one.
    """
    if path.suffix.lower() == '.inf':
        return path.with_suffix(''), path
    if path.suffix == '':
        index = path.with_name(path.name + '.INF')
        if index.is_file():
            return path, index
    return None


def default_target(source: Path) -> Path:
    """Return the WAV path beside the sample, with the extension replaced."""
    return source.with_suffix('.wav')


def display_name(sample: PxdSample) -> str:
    """Return the sample name without the NUL padding its metadata carries."""
    name = sample.name.replace('\x00', '').strip()
    return name or '(unnamed)'


def describe(sample: PxdSample) -> str:
    """Return a one line summary of a decoded sample."""
    return '%s: %d samples, %.3f s' % (
        display_name(sample), len(sample.samples), sample.duration)


def convert(source: Path, target: Path) -> PxdSample:
    """Decode one standalone sample and write its audio to ``target``."""
    sample = decode_file(source)
    write_wav(str(target), sample.samples)
    return sample


class ConverterWindow:
    """Convert a standalone sample, or one record of a bundle, to WAV."""

    def __init__(self, root: tk.Tk, *, dnd: bool = False) -> None:
        self.root = root
        self.dnd = dnd
        self.source: Path | None = None
        self.bundle: Bundle | None = None
        self.record: IndexRecord | None = None
        self.sample: PxdSample | None = None
        self.shown: list[IndexRecord] = []

        root.title('PXD to WAV')
        root.minsize(680, 520)
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, justify='left', wraplength=620,
                  text='Convert an eJay .PXD sample to a mono 16 bit 44.1 kHz WAV. '
                       'A bundle (.INF) lists its samples: pick one by id or '
                       'name.').pack(anchor='w')

        self.drop_zone = ttk.Frame(frame, relief='groove', borderwidth=1,
                                   padding=14)
        self.drop_zone.pack(fill='x', pady=(14, 0))
        hint = ('Drop a .PXD or .INF here, or browse for one'
                if dnd else
                'Browse for a .PXD or .INF (drag and drop needs tkinterdnd2)')
        ttk.Label(self.drop_zone, text=hint, justify='left',
                  wraplength=580).pack(side='left', fill='x', expand=True)
        ttk.Button(self.drop_zone, text='Open\u2026',
                   command=self.choose).pack(side='right', padx=(12, 0))
        if dnd:
            for widget in (root, self.drop_zone):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind('<<Drop>>', self._on_drop)

        self.path_text = tk.StringVar(value='no file chosen')
        ttk.Label(frame, textvariable=self.path_text, anchor='w',
                  wraplength=620).pack(fill='x', pady=(10, 0))

        self.bundle_panel = ttk.Frame(frame)
        picker = ttk.Frame(self.bundle_panel)
        picker.pack(fill='x', pady=(0, 6))
        ttk.Label(picker, text='Sample id or name').pack(side='left')
        self.filter_text = tk.StringVar()
        self.filter_entry = ttk.Entry(picker, textvariable=self.filter_text)
        self.filter_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))
        self.filter_entry.bind('<KeyRelease>', self._refill)
        self.filter_entry.bind('<Return>', self._goto_id)
        self.count_text = tk.StringVar()
        ttk.Label(picker, textvariable=self.count_text).pack(side='left',
                                                             padx=(8, 0))

        listing = ttk.Frame(self.bundle_panel)
        listing.pack(fill='both', expand=True)
        self.record_list = tk.Listbox(listing, height=10, activestyle='dotbox',
                                      exportselection=False)
        self.record_list.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(listing, orient='vertical',
                               command=self.record_list.yview)
        scroll.pack(side='right', fill='y')
        self.record_list.configure(yscrollcommand=scroll.set)
        self.record_list.bind('<<ListboxSelect>>', self._on_select)

        self.info_text = tk.StringVar()
        ttk.Label(frame, textvariable=self.info_text, anchor='w', justify='left',
                  wraplength=620).pack(fill='x', pady=(12, 0))

        self.save_button = ttk.Button(frame, text='Save WAV\u2026',
                                      command=self.save, state='disabled')
        self.save_button.pack(anchor='w', pady=(14, 0))

        self.status_text = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_text, anchor='w',
                  wraplength=620).pack(fill='x', pady=(12, 0))

    # -- loading ---------------------------------------------------------

    def choose(self) -> None:
        """Ask for a ``.PXD``, ``.INF`` or bundle file and open it."""
        chosen = filedialog.askopenfilename(
            title='Open a .PXD sample or an eJay 2 .INF bundle',
            filetypes=[('eJay samples and indexes', '*.pxd *.inf'),
                       ('eJay PXD samples', '*.pxd'),
                       ('eJay 2 indexes', '*.inf'),
                       ('All files', '*.*')],
        )
        if chosen:
            self.load(Path(chosen))

    def load(self, path: Path) -> None:
        """Open a standalone sample or a bundle and show what it holds."""
        self._reset()
        self.path_text.set(str(path))

        found = bundle_paths(path)
        if found is not None:
            data, index = found
            if not data.is_file():
                self.status_text.set('%s has no sample file beside it' % index.name)
                return
            try:
                self.bundle = Bundle(data, index)
            except (OSError, ValueError) as error:
                self.status_text.set('Could not read %s: %s' % (index.name, error))
                return
            self.source = data
            self.count_text.set('%d samples' % len(self.bundle))
            self.bundle_panel.pack(fill='both', expand=True, pady=(12, 0),
                                   before=self.save_button)
            self.filter_text.set('')
            self._fill_records()
            self.status_text.set('Pick a sample id or click a row, then save it.')
            return

        try:
            sample = decode_file(path)
        except (OSError, ValueError) as error:
            self.status_text.set('Could not decode %s: %s' % (path.name, error))
            return
        self.source = path
        self.sample = sample
        self.info_text.set('%s\n%d samples, %.3f s' % (
            display_name(sample), len(sample.samples), sample.duration))
        self.save_button.state(['!disabled'])
        self.status_text.set('Ready to save.')

    def _reset(self) -> None:
        """Forget the open file and empty the record list."""
        self.source = None
        self.bundle = None
        self.record = None
        self.sample = None
        self.shown = []
        self.info_text.set('')
        self.status_text.set('')
        self.count_text.set('')
        self.record_list.delete(0, 'end')
        self.bundle_panel.pack_forget()
        self.save_button.state(['disabled'])

    def _fill_records(self) -> None:
        """List the bundle records that match the filter."""
        if self.bundle is None:
            return
        query = self.filter_text.get().strip().lower()
        self.shown = []
        self.record_list.delete(0, 'end')
        for record in self.bundle.records:
            if query and query not in str(record.sample_id) \
                    and query not in record.label.lower():
                continue
            self.shown.append(record)
            self.record_list.insert('end', '%6d  %s'
                                    % (record.sample_id, record.label))

    def _refill(self, event: tk.Event) -> None:
        """Refill the list after a keystroke in the filter."""
        self._fill_records()

    def _goto_id(self, event: tk.Event) -> None:
        """Select the record whose id is typed in the filter."""
        if self.bundle is None:
            return
        text = self.filter_text.get().strip()
        if not text.isdigit():
            return
        sample_id = int(text)
        for position, record in enumerate(self.shown):
            if record.sample_id == sample_id:
                self.record_list.selection_clear(0, 'end')
                self.record_list.selection_set(position)
                self.record_list.see(position)
                self._select(record)
                return
        self.status_text.set('no sample %d matches the filter' % sample_id)

    def _select(self, record: IndexRecord) -> None:
        """Decode ``record`` and show its summary."""
        if self.bundle is None:
            return
        try:
            sample = self.bundle.decode(record)
        except (OSError, ValueError) as error:
            self.sample = None
            self.record = None
            self.save_button.state(['disabled'])
            self.status_text.set('Could not decode id %d: %s'
                                 % (record.sample_id, error))
            return
        self.record = record
        self.sample = sample
        self.info_text.set('id %d  %s\n%d samples, %.3f s' % (
            record.sample_id, record.label, len(sample.samples),
            sample.duration))
        self.status_text.set('Ready to save.')
        self.save_button.state(['!disabled'])

    def _on_select(self, event: tk.Event | None) -> None:
        """Decode the row the user clicked."""
        selection = self.record_list.curselection()
        if selection and selection[0] < len(self.shown):
            self._select(self.shown[selection[0]])

    def _on_drop(self, event: tk.Event) -> None:
        """Open the first file dropped on the window."""
        paths = self.root.tk.splitlist(event.data)
        if paths:
            self.load(Path(paths[0]))

    # -- saving ----------------------------------------------------------

    def save(self) -> None:
        """Write the decoded sample to the WAV path the user picks."""
        if self.source is None or self.sample is None:
            return
        if self.record is None:
            initial = default_target(self.source).name
        else:
            initial = '%s_%d.wav' % (self.source.stem, self.record.sample_id)
        chosen = filedialog.asksaveasfilename(
            title='Save WAV',
            defaultextension='.wav',
            initialfile=initial,
            initialdir=str(self.source.parent),
            filetypes=[('WAV audio', '*.wav'), ('All files', '*.*')],
        )
        if not chosen:
            return
        target = Path(chosen)
        try:
            write_wav(str(target), self.sample.samples)
        except OSError as error:
            self.status_text.set('Could not write %s: %s' % (target.name, error))
            return
        self.status_text.set('Wrote %s (%d samples, %.3f s).' % (
            target.name, len(self.sample.samples), self.sample.duration))


def _make_root() -> tuple[tk.Tk, bool]:
    """Return the window root and whether drag and drop is available."""
    if TkinterDnD is not None:
        try:
            return TkinterDnD.Tk(), True
        except (RuntimeError, tk.TclError):
            pass  # the TkDND binary is missing; a plain window still works
    return tk.Tk(), False


def run_window() -> int:
    """Open the converter window and return the process exit status."""
    if tk is None:
        print('this Python has no tkinter; pass a .PXD file to convert it '
              'headlessly', file=sys.stderr)
        return 1
    root, dnd = _make_root()
    ConverterWindow(root, dnd=dnd)
    root.mainloop()
    return 0


def run_check() -> int:
    """Report what this build can do, including whether drag and drop loaded."""
    import platform

    import numpy

    name = Path(sys.argv[0]).name
    print('%s (%s)' % (name, VERSION))
    print('python %s, %s' % (
        platform.python_version(),
        'frozen bundle' if getattr(sys, 'frozen', False) else 'source checkout'))
    print('numpy %s' % numpy.__version__)
    if tk is None:
        print('tkinter: missing (the window is unavailable, headless works)')
        return 0
    print('tkinter %s' % tk.TkVersion)
    try:
        root, dnd = _make_root()
    except tk.TclError as error:
        print('window: unavailable (%s)' % error)
        print('drag and drop: unknown (no window to attach it to)')
        return 0
    root.withdraw()
    root.destroy()
    print('drag and drop: %s'
          % ('yes' if dnd else 'no (tkinterdnd2 missing or TkDND did not load)'))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description='convert eJay .PXD samples to mono 16 bit WAV')
    parser.add_argument('file', nargs='?',
                        help='a .PXD sample, an .INF index or a bundle file; '
                             'omit it to open a window')
    parser.add_argument('out', nargs='?',
                        help='output .wav (default: the input name with .wav, '
                             'or <bundle>_<id>.wav)')
    parser.add_argument('--inf', help='index for a bundle passed as the file')
    parser.add_argument('--id', type=int,
                        help='sample id to take from a bundle')
    parser.add_argument('--list', action='store_true',
                        help='print the ids and names a bundle holds')
    parser.add_argument('--check', action='store_true',
                        help='report the decoder, Tk and drag and drop, then exit')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + VERSION)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Convert one sample, or open the window when no file is given."""
    args = parse_args(argv)
    if args.check:
        return run_check()
    if args.file is None:
        return run_window()

    source = Path(args.file)
    found = (source, Path(args.inf)) if args.inf else bundle_paths(source)
    if found is not None:
        return _convert_bundle(found[0], found[1], args)
    return _convert_single(source, args)


def _convert_single(source: Path, args: argparse.Namespace) -> int:
    """Convert one standalone sample."""
    target = Path(args.out) if args.out else default_target(source)
    try:
        sample = convert(source, target)
    except (OSError, ValueError) as error:
        print('%s: %s' % (source.name, error), file=sys.stderr)
        return 1
    print('%s -> %s  (%s)' % (source.name, target.name, describe(sample)))
    return 0


def _convert_bundle(data: Path, index: Path, args: argparse.Namespace) -> int:
    """List a bundle, or convert the record ``--id`` names."""
    try:
        bundle = Bundle(data, index)
    except (OSError, ValueError) as error:
        print('%s: %s' % (index.name, error), file=sys.stderr)
        return 1
    if args.list:
        for record in bundle.records:
            print('%6d  %s' % (record.sample_id, record.label))
        return 0
    if args.id is None:
        print('%s holds %d samples; pass --id (or --list) to choose one'
              % (index.name, len(bundle)), file=sys.stderr)
        return 2
    target = Path(args.out) if args.out else data.with_name(
        '%s_%d.wav' % (data.stem, args.id))
    try:
        sample = bundle.decode_id(args.id)
        write_wav(str(target), sample.samples)
    except KeyError as error:
        print(error.args[0] if error.args else 'sample id not in the index',
              file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print('%s: %s' % (index.name, error), file=sys.stderr)
        return 1
    print('%s [id %d] -> %s  (%s)'
          % (index.name, args.id, target.name, describe(sample)))
    return 0


__all__ = ['ConverterWindow', 'VERSION', 'bundle_paths', 'convert',
           'default_target', 'describe', 'display_name', 'main', 'parse_args',
           'run_check', 'run_window']

if __name__ == '__main__':
    sys.exit(main())
