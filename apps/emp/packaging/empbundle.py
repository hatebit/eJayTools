"""Shared build and release plumbing for the packaged bundles.

``build_emp_cli.py``, ``build_emp_tui.py``, ``release_emp_cli.py`` and
``release_emp_tui.py`` are thin entry points onto :func:`build_main` and
:func:`release_main` here, and so are ``apps/emr/packaging/build_emr_cli.py``
and ``apps/emr/packaging/release_emr_cli.py`` for the PNG renderer,
plus ``apps/pxd2wav/packaging/build_pxd2wav.py`` for the PXD converter.  The
archive version is the ``VERSION`` string of the target's own CLI module; the
eJay data under ``disks/`` is never packaged.
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

PACKAGING = Path(__file__).resolve().parent
REPO = PACKAGING.parents[2]
DIST = REPO / 'dist'

OS_TAGS = {'windows': 'windows', 'linux': 'linux', 'darwin': 'macos'}
ARCH_TAGS = {'amd64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64',
             'aarch64': 'arm64'}


@dataclass(frozen=True)
class Target:
    """One packaged executable and the text its release needs."""

    name: str
    description: str
    usage: str
    audio_hint: str
    #: Folder holding ``<name>.spec``; ``None`` means this packaging folder.
    spec_dir: Path | None = None
    #: Module holding ``VERSION``; ``None`` means the player CLI module.
    version_source: Path | None = None


TARGETS = {
    'emp-cli': Target(
        name='emp-cli',
        description='the unified command-line player',
        usage='START.MIX --format dance --from 82 --bars 8 --wav out.wav',
        audio_hint='Live playback needs an audio device; `--wav` renders '
                   'instead.'),
    'emp-tui': Target(
        name='emp-tui',
        description='the Textual front-end for the shared player core',
        usage='START.MIX',
        audio_hint='Live playback needs an audio device; use Render to write '
                   'a WAV instead.'),
    'emr-cli': Target(
        name='emr-cli',
        description='the unified PNG arrangement renderer',
        usage='--all --out images',
        audio_hint='Writes PNG files only; no audio device is needed.',
        spec_dir=REPO / 'apps' / 'emr' / 'packaging',
        version_source=REPO / 'apps' / 'emr' / 'src' / 'render' / 'cli.py',
    ),
    'pxd2wav': Target(
        name='pxd2wav',
        description='the PXD to WAV converter',
        usage='AAAF.PXD out.wav',
        audio_hint='Writes WAV files only; no audio device is needed.',
        spec_dir=REPO / 'apps' / 'pxd2wav' / 'packaging',
        version_source=REPO / 'apps' / 'pxd2wav' / 'src' / 'pxd2wav.py',
    ),
}


def target_of(name: str) -> Target:
    """Return the :class:`Target` called ``name``."""
    try:
        return TARGETS[name]
    except KeyError:
        raise RuntimeError('unknown target %r (choose from %s)'
                           % (name, ', '.join(TARGETS))) from None


def bundle_dir(target: Target) -> Path:
    """Return the one-dir output folder for ``target``."""
    return DIST / target.name


def exe_path(target: Target) -> Path:
    """Return the executable inside the one-dir bundle."""
    return bundle_dir(target) / (target.name + ('.exe'
                                                if sys.platform == 'win32'
                                                else ''))


def spec_path(target: Target) -> Path:
    """Return the PyInstaller spec for ``target``."""
    return (target.spec_dir or PACKAGING) / (target.name + '.spec')


def wrapper_name(action: str, target: Target) -> str:
    """Return ``build_emp_cli.py``-style wrapper names for error hints."""
    return '%s_%s.py' % (action, target.name.replace('-', '_'))


def wrapper_path(action: str, target: Target) -> Path:
    """Return the wrapper script beside ``target``'s spec."""
    return ((target.spec_dir or PACKAGING)
            / wrapper_name(action, target))


def platform_tags() -> tuple[str, str]:
    """Return the ``(os, arch)`` names used in the archive filename."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    return (OS_TAGS.get(system, system or 'unknown'),
            ARCH_TAGS.get(machine, machine or 'unknown'))


def default_tag(target: Target, today: datetime.date | None = None) -> str:
    """Return the default release tag, ``<name>-vYYYY.MM.DD``."""
    today = today or datetime.date.today()
    return '%s-v%d.%02d.%02d' % (target.name, today.year, today.month,
                                 today.day)


def title_of(target: Target, tag: str) -> str:
    """Return ``<name> <version>`` with a leading ``<name>-`` stripped."""
    prefix = target.name + '-'
    version = tag[len(prefix):] if tag.startswith(prefix) else tag
    return '%s %s' % (target.name, version)


def package_version(target: Target | None = None) -> str:
    """Return ``VERSION`` from ``target``'s CLI module without importing it.

    The default is the player CLI module; the renderer names its own.
    """
    path = ((target.version_source if target else None)
            or REPO / 'apps' / 'emp' / 'src' / 'core' / 'cli.py')
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (OSError, SyntaxError) as exc:
        raise RuntimeError('cannot read %s: %s' % (path, exc)) from exc
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(item, ast.Name) and item.id == 'VERSION'
                   for item in node.targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            break
        if isinstance(value, str) and value:
            return value
        break
    raise RuntimeError('no VERSION string in %s' % path)


def asset_name(target: Target, version: str, os_tag: str, arch: str) -> str:
    """Return the archive filename for one release."""
    return '%s-%s-%s-%s.zip' % (target.name, version, os_tag, arch)


def sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def zip_bundle(source: Path, target: Path) -> None:
    """Zip ``source`` as a top-level folder, keeping Unix executable bits."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.part')
    try:
        with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED,
                             compresslevel=9) as archive:
            for path in sorted(source.rglob('*')):
                arcname = (Path(source.name)
                           / path.relative_to(source)).as_posix()
                if path.is_dir():
                    info = zipfile.ZipInfo(arcname + '/')
                    info.create_system = 3
                    info.external_attr = (0o40755 << 16) | 0x10
                    archive.writestr(info, b'')
                    continue
                info = zipfile.ZipInfo.from_file(path, arcname)
                info.create_system = 3
                mode = 0o755 if os.access(path, os.X_OK) else 0o644
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with path.open('rb') as src, archive.open(info, 'w') as dst:
                    shutil.copyfileobj(src, dst)
        with zipfile.ZipFile(partial, 'r') as archive:
            corrupt = archive.testzip()
        if corrupt is not None:
            raise RuntimeError('archive entry is corrupt: %s' % corrupt)
        partial.replace(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def release_notes(target: Target, version: str, commit: str, os_tag: str,
                  arch: str, digest: str) -> str:
    """Return the default Markdown body of the release."""
    exe = target.name + ('.exe' if os_tag == 'windows' else '')
    return '\n'.join([
        'One-dir PyInstaller bundle of `%s`, %s, version %s (%s %s).'
        % (target.name, target.description, version, os_tag, arch),
        '',
        'Built from commit `%s`.' % commit,
        '',
        'Unzip the archive, then keep the eJay `disks/` folder next to the',
        'bundle, or point `EJAY_DATA_ROOT` at the folder that contains it:',
        '',
        '```bash',
        '%s/%s %s' % (target.name, exe, target.usage),
        '```',
        '',
        target.audio_hint,
        'eJay data is not included.',
        '',
        'SHA-256: `%s`' % digest,
    ])


def run(command: list[str], capture: bool = False,
        echo: bool = True) -> subprocess.CompletedProcess:
    """Run a command, optionally echoing it; raise on a non-zero status."""
    if echo:
        print('+ ' + ' '.join(shlex.quote(part) for part in command))
    result = subprocess.run(command, cwd=str(REPO), text=True,
                            capture_output=capture, check=False)
    if result.returncode != 0:
        if capture and result.stderr:
            sys.stderr.write(result.stderr)
        raise RuntimeError('command failed with status %d: %s'
                           % (result.returncode, command[0]))
    return result


def git_commit() -> str:
    """Return the full commit hash of HEAD."""
    return run(['git', 'rev-parse', 'HEAD'],
               capture=True, echo=False).stdout.strip()


def is_pushed() -> bool:
    """True when HEAD is contained in a known remote-tracking branch."""
    try:
        branches = run(['git', 'branch', '-r', '--contains', 'HEAD'],
                       capture=True, echo=False).stdout
    except (OSError, RuntimeError):
        return False
    return bool(branches.strip())


def is_dirty() -> bool:
    """True when the working tree has uncommitted changes."""
    return bool(run(['git', 'status', '--porcelain'],
                    capture=True, echo=False).stdout.strip())


def parse_remote(url: str) -> str:
    """Turn a GitHub remote URL into ``owner/name``."""
    match = re.search(r'github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?$',
                      url.strip())
    if match is None:
        raise RuntimeError('cannot read a GitHub repository from %r' % url)
    return '%s/%s' % (match.group(1), match.group(2))


def repo_name(explicit: str | None) -> str:
    """Return ``owner/name`` from ``--repo``, ``gh`` or the origin remote."""
    if explicit:
        return explicit
    try:
        return run(['gh', 'repo', 'view', '--json', 'nameWithOwner',
                    '-q', '.nameWithOwner'],
                   capture=True, echo=False).stdout.strip()
    except (OSError, RuntimeError):
        url = run(['git', 'remote', 'get-url', 'origin'],
                  capture=True, echo=False).stdout.strip()
        return parse_remote(url)


def build(target: Target, clean: bool = False) -> int:
    """Run PyInstaller on one target; return the process exit status."""
    command = [sys.executable, '-m', 'PyInstaller', str(spec_path(target)),
               '--noconfirm']
    if clean:
        command.append('--clean')
    try:
        run(command)
    except (OSError, RuntimeError) as exc:
        print('error: %s' % exc, file=sys.stderr)
        return 2
    exe = exe_path(target)
    if not exe.is_file():
        print('error: PyInstaller did not write %s' % exe, file=sys.stderr)
        return 2
    print('built %s' % exe)
    return 0


def build_main(target_name: str, argv: list[str] | None = None) -> int:
    """CLI for the ``build_emp_*.py`` and ``build_emr_cli.py`` wrappers."""
    target = target_of(target_name)
    ap = argparse.ArgumentParser(
        description='Build the %s PyInstaller bundle.' % target.name)
    ap.add_argument('--clean', action='store_true',
                    help='remove PyInstaller caches and the previous build')
    args = ap.parse_args(argv)
    return build(target, clean=args.clean)


def release_main(target_name: str, argv: list[str] | None = None) -> int:
    """CLI for the ``release_emp_*.py`` and ``release_emr_cli.py`` wrappers."""
    target = target_of(target_name)
    name = target.name
    ap = argparse.ArgumentParser(
        description='Build the %s bundle, zip it and publish a GitHub '
                    'release.' % name)
    ap.add_argument('--tag', default=None,
                    help='release tag (default: %s-v<today>)' % name)
    ap.add_argument('--title', default=None,
                    help='release title (default: %s <version>)' % name)
    ap.add_argument('--notes', default=None, help='release body text')
    ap.add_argument('--notes-file', metavar='PATH', default=None,
                    help='read the release body from a file')
    ap.add_argument('--repo', metavar='OWNER/NAME', default=None,
                    help='GitHub repository (default: the origin repository)')
    ap.add_argument('--draft', action='store_true', help='publish as a draft')
    ap.add_argument('--prerelease', action='store_true',
                    help='mark the release as a pre-release')
    ap.add_argument('--replace', action='store_true',
                    help='upload the asset to an existing release (clobber)')
    ap.add_argument('--skip-build', action='store_true',
                    help='reuse dist/%s instead of rebuilding it' % name)
    ap.add_argument('--no-clean', action='store_true',
                    help='do not pass --clean to the builder')
    ap.add_argument('--dry-run', action='store_true',
                    help='build and zip, but do not create the release')
    ap.add_argument('--yes', '-y', action='store_true',
                    help='do not ask for confirmation')
    args = ap.parse_args(argv)

    if args.notes and args.notes_file:
        ap.error('use either --notes or --notes-file')

    tag = args.tag or default_tag(target)
    os_tag, arch = platform_tags()
    try:
        version = package_version(target)
    except RuntimeError as exc:
        print('error: %s' % exc, file=sys.stderr)
        return 2
    asset = DIST / asset_name(target, version, os_tag, arch)

    try:
        repo = repo_name(args.repo)
        commit = git_commit()
    except (OSError, RuntimeError) as exc:
        print('error: %s' % exc, file=sys.stderr)
        return 2

    if is_dirty():
        print('warning: the working tree has uncommitted changes; the release '
              'will not match any commit exactly.', file=sys.stderr)
    if not is_pushed():
        print('warning: HEAD is not on a known remote branch; push the commit '
              'first or the release target will not exist on GitHub.',
              file=sys.stderr)

    if not args.skip_build:
        status = build(target, clean=not args.no_clean)
        if status != 0:
            return status
    if not bundle_dir(target).is_dir():
        print('error: no bundle at %s; run python %s first'
              % (bundle_dir(target),
                 wrapper_path('build', target).relative_to(REPO)),
              file=sys.stderr)
        return 2

    try:
        zip_bundle(bundle_dir(target), asset)
    except (OSError, RuntimeError) as exc:
        print('error: %s' % exc, file=sys.stderr)
        return 2
    digest = sha256(asset)
    print('zipped %s (%.1f MB, sha256 %s)'
          % (asset, asset.stat().st_size / (1 << 20), digest))

    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding='utf-8')
    elif args.notes:
        notes = args.notes
    else:
        notes = release_notes(target, version, commit[:7], os_tag, arch,
                              digest)
    title = args.title or title_of(target, tag)

    if args.replace:
        command = ['gh', 'release', 'upload', tag, str(asset),
                   '--clobber', '--repo', repo]
    else:
        command = ['gh', 'release', 'create', tag, str(asset),
                   '--title', title, '--notes', notes,
                   '--target', commit, '--repo', repo]
        if args.draft:
            command.append('--draft')
        if args.prerelease:
            command.append('--prerelease')

    if args.dry_run:
        print('dry run: would publish %s to %s' % (tag, repo))
        print('  title: %s' % title)
        print('  asset: %s' % asset)
        print('  target commit: %s' % commit[:7])
        flags = [flag for flag, on in (('draft', args.draft),
                                       ('prerelease', args.prerelease),
                                       ('replace', args.replace)) if on]
        if flags:
            print('  flags: %s' % ', '.join(flags))
        return 0

    if not args.yes:
        try:
            answer = input('Release %s (%s) in %s? [y/N] '
                           % (tag, title, repo))
        except EOFError:
            answer = ''
        if answer.strip().lower() not in ('y', 'yes'):
            print('aborted; pass --yes to publish without asking')
            return 2

    try:
        run(command)
    except (OSError, RuntimeError) as exc:
        print('error: %s' % exc, file=sys.stderr)
        print('if gh is missing, install it and run: gh auth login',
              file=sys.stderr)
        return 2
    print('published %s to %s' % (tag, repo))
    return 0

