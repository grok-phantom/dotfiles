"""Preview, back up and restore only the macOS preferences owned by this script."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile


PREFERENCES = (
    # Safari search provider.
    ('com.apple.Safari', 'SearchProviderIdentifier', 'com.google.www'),
    ('com.apple.Safari', 'SearchProviderShortName', 'Google'),
    ('com.apple.Safari', 'SearchProviderURL', 'https://www.google.com/search?q={searchTerms}'),
    # Tap to click, secondary click, and no three-finger Look Up gesture.
    ('com.apple.AppleMultitouchTrackpad', 'Clicking', True),
    ('com.apple.driver.AppleBluetoothMultitouch.trackpad', 'Clicking', True),
    ('NSGlobalDomain', 'com.apple.mouse.tapBehavior', 1),
    ('NSGlobalDomain', 'com.apple.trackpad.enableSecondaryClick', True),
    ('com.apple.AppleMultitouchTrackpad', 'TrackpadThreeFingerTapGesture', 0),
    ('com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadThreeFingerTapGesture', 0),
    # Automatic appearance, smaller Dock, fixed Spaces order, no tiling gaps.
    ('NSGlobalDomain', 'AppleInterfaceStyleSwitchesAutomatically', True),
    ('com.apple.dock', 'tilesize', 31),
    ('com.apple.dock', 'mru-spaces', False),
    ('com.apple.WindowManager', 'EnableTiledWindowMargins', False),
    # Fast key repeat instead of the press-and-hold accent popup.
    ('NSGlobalDomain', 'KeyRepeat', 2),
    ('NSGlobalDomain', 'InitialKeyRepeat', 15),
    ('NSGlobalDomain', 'ApplePressAndHoldEnabled', False),
    # Finder list view, path/status bars and filename extensions.
    ('com.apple.finder', 'ShowPathbar', True),
    ('com.apple.finder', 'ShowStatusBar', True),
    ('com.apple.finder', 'FXPreferredViewStyle', 'Nlsv'),
    ('NSGlobalDomain', 'AppleShowAllExtensions', True),
    # macOS 26 menu bar keys; older keys do not control these icons.
    ('com.apple.Spotlight', 'NSStatusItem VisibleCC Item-0', False),
    ('com.apple.controlcenter', 'NSStatusItem VisibleCC WiFi', False),
    ('com.apple.controlcenter', 'NSStatusItem VisibleCC Battery', False),
    ('com.apple.TextInputMenu', 'visible', False),
)


def defaults(*args):
    result = subprocess.run(['defaults', *args], capture_output=True, env=dict(os.environ, LC_ALL='C'))
    if result.returncode:
        raise RuntimeError(f'defaults {args[0]} {args[1]}: {result.stderr.decode(errors="replace").strip()}')
    return result.stdout


def validate_entries(entries):
    expected = {(domain, key) for domain, key, _ in PREFERENCES}
    if not isinstance(entries, list) or len(entries) != len(expected):
        raise ValueError('Backup must contain exactly the managed preference keys')
    found = {}
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get('domain'), str)
                or not isinstance(entry.get('key'), str) or type(entry.get('present')) is not bool):
            raise ValueError('Invalid preference entry')
        identity = (entry['domain'], entry['key'])
        if identity not in expected or identity in found:
            raise ValueError(f'Unexpected or duplicate preference: {identity}')
        if entry['present']:
            value = entry.get('value')
            if (type(value) not in (str, bool, int, float)
                    or (type(value) is float and not math.isfinite(value))
                    or (type(value) is str and '\0' in value)):
                raise ValueError(f'Unsupported preference value: {identity}')
        elif 'value' in entry:
            raise ValueError(f'Absent preference has a value: {identity}')
        found[identity] = entry
    return [found[(domain, key)] for domain, key, _ in PREFERENCES]


def snapshot():
    domains = {}
    for domain, _, _ in PREFERENCES:
        if domain not in domains:
            # Export retains types and distinguishes absent keys from empty strings.
            domains[domain] = plistlib.loads(defaults('export', domain, '-'))
            if not isinstance(domains[domain], dict):
                raise ValueError(f'Expected a preference dictionary for {domain}')
    entries = []
    for domain, key, _ in PREFERENCES:
        entry = dict(domain=domain, key=key, present=key in domains[domain])
        if entry['present']:
            entry['value'] = domains[domain][key]
        entries.append(entry)
    return validate_entries(entries)


def same(left, right):
    return (left['present'] == right['present'] and
            (not left['present'] or (type(left['value']) is type(right['value']) and
                                     left['value'] == right['value'])))


def describe(entry):
    if not entry['present']:
        return '<absent>'
    return f"{type(entry['value']).__name__} {json.dumps(entry['value'], ensure_ascii=False)}"


def save_backup(entries):
    state = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'dotfiles/macos-defaults'
    repository = Path(__file__).resolve().parents[2]
    if repository == state.resolve() or repository in state.resolve().parents:
        raise ValueError('Preference backups must stay outside the source repository')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-')
    directory = Path(tempfile.mkdtemp(prefix=stamp, dir=state))
    path = directory/'backup.json'
    payload = dict(schema_version=1, created_at=datetime.now(timezone.utc).isoformat(), preferences=entries)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write('\n')
        file.flush()
        os.fsync(file.fileno())
    return path


def load_backup(path):
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or payload.get('schema_version') != 1:
        raise ValueError('Unsupported preference backup format')
    return validate_entries(payload.get('preferences'))


def write_preference(entry):
    domain, key = entry['domain'], entry['key']
    if not entry['present']:
        defaults('delete', domain, key)
        return
    value = entry['value']
    flag = {bool: '-bool', int: '-int', float: '-float', str: '-string'}[type(value)]
    text = str(value).lower() if type(value) is bool else str(value)
    defaults('write', domain, key, flag, text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='Show current -> desired values without writing')
    mode.add_argument('--apply', action='store_true', help='Back up, apply and verify the managed preferences')
    mode.add_argument('--restore', type=Path, metavar='BACKUP', help='Restore managed keys from a backup JSON file')
    args = parser.parse_args(argv)
    backup = None
    try:
        if sys.platform != 'darwin':
            raise RuntimeError('macOS is required')
        target = load_backup(args.restore) if args.restore else [
            dict(domain=domain, key=key, present=True, value=value) for domain, key, value in PREFERENCES]
        before = snapshot()
        changes = [new for old, new in zip(before, target) if not same(old, new)]
        for old, new in zip(before, target):
            if not same(old, new):
                print(f"{new['domain']} / {new['key']}: {describe(old)} -> {describe(new)}")
        print(f'{len(changes)} preference(s) differ.')
        if args.check or not changes:
            return 0

        backup = save_backup(before)
        print(f'Backup: {backup}', flush=True)
        failed = False
        wrote = False
        for entry in changes:
            try:
                write_preference(entry)
                wrote = True
            except RuntimeError as error:
                failed = True
                print(f"ERROR: {entry['key']}: {error}", file=sys.stderr)

        current = snapshot()
        for actual, expected in zip(current, target):
            if not same(actual, expected):
                failed = True
                print(f"ERROR: readback mismatch for {expected['domain']} / {expected['key']}: "
                      f'{describe(actual)}; expected {describe(expected)}', file=sys.stderr)
        if wrote:
            subprocess.run(['killall', 'Dock', 'Finder', 'SystemUIServer', 'ControlCenter', 'Spotlight'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if failed:
            print(f'Preferences only partially updated. Use --restore {backup} to recover.', file=sys.stderr)
            return 1
        print('Restored and verified macOS defaults.' if args.restore else 'Applied and verified macOS defaults.')
        return 0
    except (OSError, ValueError, RuntimeError, plistlib.InvalidFileException) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        if backup is not None:
            print(f'Changes may be partial. Use --restore {backup} to recover.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
