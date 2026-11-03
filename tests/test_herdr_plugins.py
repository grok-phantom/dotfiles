"""Herdr maintenance uses temporary files and a fake CLI, never host plugins."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_updates as base
from dotfiles_lib import herdr, quicklook


class PluginsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root/'repo'
        self.home = self.root/'home'
        (self.repo/'locks').mkdir(parents=True)
        shutil.copy(base.ROOT/'locks/herdr-plugins.tsv', self.repo/'locks/herdr-plugins.tsv')
        self.entries = herdr.read_lock(self.repo)
        source = self.repo/'home/private_dot_config/herdr/plugins/local/dotfiles-quick-actions'
        shutil.copytree(base.ROOT/'home/private_dot_config/herdr/plugins/local/dotfiles-quick-actions', source)
        shutil.copytree(source, self.home/herdr.LOCAL_DIR)
        self.plugins = []
        for source, revision, _ in self.entries:
            owner, name = source.split('/')
            self.plugins.append(dict(plugin_id=name, enabled=True, source=dict(kind='github',
                owner=owner, repo=name, requested_ref=revision, resolved_commit=revision),
                plugin_root=str(self.root/'plugins'/name)))
        self.quick = herdr.find(self.plugins, 'dwarvesf/herdr-quicklook')
        self.lib = Path(self.quick['plugin_root'])/'scripts/lib.sh'
        self.lib.parent.mkdir(parents=True)
        self.original = '# reviewed fixture\n' + quicklook.OLD + '\n'
        self.lib.write_text(self.original.replace(quicklook.OLD, quicklook.NEW))
        self.addCleanup(patch.stopall)
        patch.object(quicklook, 'ORIGINAL_SHA256', hashlib.sha256(self.original.encode()).hexdigest()).start()
        patch.object(quicklook.Path, 'home', return_value=self.home).start()
        self.plugins.append(dict(plugin_id=herdr.LOCAL_ID, enabled=True, source=dict(kind='local'),
                                 plugin_root=str(self.home/herdr.LOCAL_DIR)))
        self.calls = []
        patch.object(herdr, 'run', side_effect=self.fake_run).start()
        patch.object(herdr.shutil, 'which', return_value='/mock/tool').start()
        self.args = SimpleNamespace(repo=self.repo, target=self.home, action='plan', yes=False)

    def fake_run(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[1:3] == ['plugin', 'list']:
            return json.dumps({'result': {'plugins': self.plugins}}).encode()
        if argv[1:3] == ['plugin', 'install']:
            plugin = herdr.find(self.plugins, argv[3])
            plugin['enabled'] = True
            plugin['source'].update(requested_ref=argv[5], resolved_commit=argv[5])
        if argv[1:3] == ['plugin', 'link']:
            self.plugins.append(dict(plugin_id=herdr.LOCAL_ID, enabled=True,
                source=dict(kind='local'), plugin_root=str(argv[3])))
        return b''

    def mutations(self):
        return [c for c in self.calls if c[1:3] != ['plugin', 'list']]

    def test_plan_and_verify_do_not_write_or_install(self):
        before = self.lib.read_bytes()
        herdr.maintain(self.args)
        self.args.action = 'verify'
        herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.lib.read_bytes(), before)
        self.assertFalse((self.home/'.local').exists())

    def test_install_twice_is_noop_when_matching(self):
        self.args.action, self.args.yes = 'install', True
        herdr.maintain(self.args)
        herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])

    def test_missing_late_dependency_prevents_every_install(self):
        for plugin in self.plugins[:-1]:
            plugin['enabled'] = False
        self.args.action, self.args.yes = 'install', True
        with patch.object(herdr.shutil, 'which', side_effect=lambda name: None if name == 'cargo' else '/mock/tool'):
            with self.assertRaisesRegex(herdr.Stop, 'cargo'):
                herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])

    def test_local_files_must_be_applied_before_any_install(self):
        (self.home/herdr.LOCAL_DIR/'paste-image.sh').write_text('local edit')
        with self.assertRaisesRegex(herdr.Stop, 'chezmoi'):
            herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])

    def test_wrong_local_registration_is_preserved(self):
        self.plugins[-1]['plugin_root'] = '/another/plugin'
        with self.assertRaisesRegex(herdr.Stop, 'different source'):
            herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])

    def test_verify_reports_missing_patch_without_repair(self):
        self.lib.write_text(self.original)
        self.args.action = 'verify'
        with self.assertRaisesRegex(herdr.Stop, 'patch is missing'):
            herdr.maintain(self.args)
        self.assertEqual(self.lib.read_text(), self.original)
        self.assertEqual(self.mutations(), [])

    def test_patch_checks_hash_and_backs_up_before_write(self):
        self.lib.write_text(self.original)
        quicklook.apply(self.quick)
        backup = self.home/'.local/state/dotfiles-backups/herdr-quicklook-cjk'/quicklook.REVISION/'lib.sh'
        self.assertEqual(backup.read_text(), self.original)
        quicklook.apply(self.quick)
        self.assertEqual(backup.read_text(), self.original)
        self.lib.write_text(self.lib.read_text() + 'user edit')
        with self.assertRaisesRegex(ValueError, 'local edits'):
            quicklook.apply(self.quick)
        self.assertTrue(self.lib.read_text().endswith('user edit'))

    def test_bad_patch_preflight_prevents_other_install(self):
        self.plugins[0]['enabled'] = False
        self.lib.write_text('unexpected bytes')
        self.args.action, self.args.yes = 'install', True
        with self.assertRaisesRegex(ValueError, 'local edits'):
            herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])

    def test_partial_failure_can_resume_without_reinstalling_success(self):
        self.plugins[0]['enabled'] = self.plugins[1]['enabled'] = False
        self.args.action, self.args.yes = 'install', True
        second = self.entries[1][0]
        def fail_second(argv, **kwargs):
            if argv[1:4] == ['plugin', 'install', second]:
                raise herdr.Stop('injected installation failure')
            return self.fake_run(argv, **kwargs)
        with patch.object(herdr, 'run', side_effect=fail_second):
            with self.assertRaisesRegex(herdr.Stop, 'injected'):
                herdr.maintain(self.args)
        self.assertTrue(self.plugins[0]['enabled'])
        self.calls.clear()
        herdr.maintain(self.args)
        self.assertEqual([c[3] for c in self.mutations()], [second])

    def test_install_requires_yes(self):
        self.args.action = 'install'
        with self.assertRaisesRegex(herdr.Stop, '--yes'):
            herdr.maintain(self.args)
        self.assertEqual(self.mutations(), [])

    def test_readback_catches_silent_install_failure(self):
        self.plugins[0]['enabled'] = False
        self.args.action, self.args.yes = 'install', True
        with patch.object(herdr, 'run', side_effect=lambda argv, **kw:
                          self.fake_run(argv, **kw) if argv[2] == 'list' else b''):
            with self.assertRaisesRegex(herdr.Stop, 'readback'):
                herdr.maintain(self.args)

    def test_lock_rejects_duplicates_and_patch_revision_drift(self):
        lock = self.repo/'locks/herdr-plugins.tsv'
        original = lock.read_text()
        lock.write_text(original + original)
        with self.assertRaisesRegex(herdr.Stop, 'duplicate'):
            herdr.read_lock(self.repo)
        lock.write_text(original.replace(quicklook.REVISION, 'a'*40))
        with self.assertRaisesRegex(herdr.Stop, 'patch revision'):
            herdr.read_lock(self.repo)


class ClipboardTests(base.Fixture):
    def test_routes_to_captured_pane_without_enter(self):
        if not shutil.which('jq'):
            self.skipTest('jq is required for the clipboard routing test')
        self.mock('herdr', 'printf "%s\\n" "$@" > "$TEST_ROOT/keys"\n')
        script = base.ROOT/'home/private_dot_config/herdr/plugins/local/dotfiles-quick-actions/paste-image.sh'
        for agent, key in [('codex', 'ctrl+alt+v'), ('claude', 'super+v'), ('', 'super+v')]:
            env = dict(self.env, HERDR_BIN_PATH=str(self.bin/'herdr'),
                HERDR_PLUGIN_CONTEXT_JSON=json.dumps(dict(focused_pane_id='captured-pane', focused_pane_agent=agent)))
            self.cmd(['sh', script], env=env)
            self.assertEqual((self.root/'keys').read_text().splitlines(), ['pane','send-keys','captured-pane',key])
        env['HERDR_PLUGIN_CONTEXT_JSON'] = '{}'
        (self.root/'keys').unlink()
        self.cmd(['sh', script], env=env, okay=False)
        self.assertFalse((self.root/'keys').exists())
