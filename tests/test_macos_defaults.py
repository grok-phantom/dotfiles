"""Preference round trips and failures with a typed, in-memory defaults stand-in."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('macos_defaults', ROOT/'scripts/manual/macos_defaults.py')
PREFERENCES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFERENCES)


class MacOSDefaultsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = self.root/'state'
        self.values = {
            'com.apple.dock': {'tilesize': 47.5, 'unmanaged': 'before'},
            'com.apple.Safari': {'SearchProviderIdentifier': 'old "provider"\nname',
                                 'SearchProviderShortName': ''},
            'NSGlobalDomain': {'com.apple.mouse.tapBehavior': True, 'AppleShowAllExtensions': False},
        }
        self.initial = copy.deepcopy(self.values)
        self.mutations = []
        self.fail_key = None
        self.ignore_key = None
        self.fail_export = False
        self.fail_readback = False

    def command(self, args, **kwargs):
        if args[0] == 'killall':
            self.mutations.append(args)
            return subprocess.CompletedProcess(args, 0)
        self.assertEqual(args[0], 'defaults', f'Unexpected command: {args}')
        operation, domain = args[1:3]
        if operation == 'export':
            if self.fail_export or (self.fail_readback and self.mutations):
                return subprocess.CompletedProcess(args, 1, b'', b'export denied')
            return subprocess.CompletedProcess(args, 0, plistlib.dumps(self.values.get(domain, {})), b'')
        # A readable backup must exist before the first preference mutation.
        self.assertTrue(self.backups())
        for backup in self.backups():
            self.assertEqual(len(json.loads(backup.read_text())['preferences']), 24)
        self.mutations.append(args)
        key = args[3]
        if key == self.fail_key:
            return subprocess.CompletedProcess(args, 1, b'', b'write denied')
        if key != self.ignore_key:
            values = self.values.setdefault(domain, {})
            if operation == 'delete':
                del values[key]
            else:
                self.assertEqual(operation, 'write')
                flag, text = args[4:]
                convert = {'-string': str, '-bool': lambda s: s == 'true', '-int': int, '-float': float}
                values[key] = convert[flag](text)
        return subprocess.CompletedProcess(args, 0, b'', b'')

    def run_preferences(self, *args, platform='darwin'):
        output, errors = io.StringIO(), io.StringIO()
        with (patch.dict(os.environ, HOME=str(self.root), XDG_STATE_HOME=str(self.state)),
              patch.object(PREFERENCES.sys, 'platform', platform),
              patch.object(PREFERENCES.subprocess, 'run', side_effect=self.command),
              redirect_stdout(output), redirect_stderr(errors)):
            result = PREFERENCES.main(list(args))
        return result, output.getvalue(), errors.getvalue()

    def backups(self):
        return sorted(self.state.glob('dotfiles/macos-defaults/*/backup.json'))

    def test_check_shows_typed_differences_without_writes_or_backups(self):
        code, output, errors = self.run_preferences('--check')
        self.assertEqual(code, 0, errors)
        self.assertIn('float 47.5 -> int 31', output)
        self.assertIn('bool true -> int 1', output)
        self.assertEqual(self.values, self.initial)
        self.assertFalse(self.mutations)
        self.assertFalse(self.state.exists())

    def test_apply_restore_preserves_types_absence_and_unrelated_edits(self):
        code, output, errors = self.run_preferences('--apply')
        self.assertEqual(code, 0, errors)
        self.assertIn('Applied and verified', output)
        backup, = self.backups()
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backup.parent.stat().st_mode), 0o700)
        self.assertNotIn('unmanaged', backup.read_text())
        self.assertIs(type(self.values['com.apple.dock']['tilesize']), int)
        self.assertIs(type(self.values['NSGlobalDomain']['com.apple.mouse.tapBehavior']), int)
        self.values['com.apple.dock']['unmanaged'] = 'later edit'
        applied = copy.deepcopy(self.values)

        code, output, errors = self.run_preferences('--restore', str(backup))
        self.assertEqual(code, 0, errors)
        self.assertIn('Restored and verified', output)
        expected = copy.deepcopy(self.initial)
        expected['com.apple.dock']['unmanaged'] = 'later edit'
        self.assertEqual({domain: values for domain, values in self.values.items() if values}, expected)
        self.assertIs(type(self.values['com.apple.dock']['tilesize']), float)
        self.assertIs(type(self.values['NSGlobalDomain']['com.apple.mouse.tapBehavior']), bool)
        # Restore itself has a backup, so it can also be undone.
        undo, = set(self.backups()) - {backup}
        self.assertEqual(self.run_preferences('--restore', str(undo))[0], 0)
        self.assertEqual(self.values, applied)

    def test_repeat_apply_does_not_write_back_up_or_restart(self):
        self.assertEqual(self.run_preferences('--apply')[0], 0)
        backups = self.backups()
        self.mutations.clear()
        code, output, errors = self.run_preferences('--apply')
        self.assertEqual(code, 0, errors)
        self.assertIn('0 preference(s) differ', output)
        self.assertFalse(self.mutations)
        self.assertEqual(self.backups(), backups)

    def test_backup_failure_prevents_all_preference_writes(self):
        self.state.write_text('cannot create a directory here')
        self.assertNotEqual(self.run_preferences('--apply')[0], 0)
        self.assertFalse(self.mutations)
        self.assertEqual(self.values, self.initial)

    def test_read_failure_does_not_treat_values_as_absent(self):
        self.fail_export = True
        code, _, errors = self.run_preferences('--apply')
        self.assertNotEqual(code, 0)
        self.assertIn('export denied', errors)
        self.assertFalse(self.mutations)
        self.assertFalse(self.backups())

    def test_unsupported_existing_value_stops_before_writing(self):
        self.values['com.apple.dock']['tilesize'] = ['unexpected type']
        code, _, errors = self.run_preferences('--apply')
        self.assertNotEqual(code, 0)
        self.assertIn('Unsupported preference value', errors)
        self.assertFalse(self.mutations)
        self.assertFalse(self.backups())

    def test_partial_write_failure_keeps_backup_and_returns_failure(self):
        self.fail_key = 'SearchProviderIdentifier'
        code, output, errors = self.run_preferences('--apply')
        self.assertNotEqual(code, 0)
        self.assertIn('write denied', errors)
        self.assertIn('partially updated', errors)
        self.assertNotIn('Applied and verified', output)
        self.assertEqual(self.values['com.apple.dock']['tilesize'], 31)
        backup, = self.backups()
        self.fail_key = None
        self.assertEqual(self.run_preferences('--restore', str(backup))[0], 0)
        self.assertEqual({domain: values for domain, values in self.values.items() if values}, self.initial)

    def test_successful_write_with_incorrect_readback_is_failure(self):
        self.ignore_key = 'tilesize'
        code, output, errors = self.run_preferences('--apply')
        self.assertNotEqual(code, 0)
        self.assertIn('readback mismatch for com.apple.dock / tilesize', errors)
        self.assertNotIn('Applied and verified', output)
        self.assertEqual(len(self.backups()), 1)

    def test_readback_failure_reports_recovery_after_writing(self):
        self.fail_readback = True
        code, output, errors = self.run_preferences('--apply')
        self.assertNotEqual(code, 0)
        self.assertIn('export denied', errors)
        self.assertIn('Changes may be partial', errors)
        backup, = self.backups()
        self.assertIn(f'--restore {backup}', errors)
        self.assertNotIn('Applied and verified', output)

    def test_restore_rejects_unmanaged_or_duplicate_keys_before_writing(self):
        self.assertEqual(self.run_preferences('--apply')[0], 0)
        backup, = self.backups()
        original = json.loads(backup.read_text())
        for identity in ('unmanaged', 'duplicate'):
            with self.subTest(identity=identity):
                payload = copy.deepcopy(original)
                if identity == 'unmanaged':
                    payload['preferences'][0]['key'] = 'not-managed-by-dotfiles'
                else:
                    payload['preferences'][0] = payload['preferences'][1]
                malformed = self.root/'malformed.json'
                malformed.write_text(json.dumps(payload))
                self.mutations.clear()
                code, _, errors = self.run_preferences('--restore', str(malformed))
                self.assertNotEqual(code, 0)
                self.assertIn('Unexpected or duplicate preference', errors)
                self.assertFalse(self.mutations)

    def test_non_macos_is_rejected_without_writes(self):
        code, _, errors = self.run_preferences('--apply', platform='linux')
        self.assertNotEqual(code, 0)
        self.assertIn('macOS is required', errors)
        self.assertFalse(self.mutations)
        self.assertFalse(self.backups())


if __name__ == '__main__':
    unittest.main()
