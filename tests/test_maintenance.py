"""Migration and diagnostics regressions, using synthetic local data only."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tomllib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_updates as base
import check_runtime


class LocalChoicesTests(base.Fixture):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.repo/'home')
        shutil.copytree(base.ROOT/'home', self.repo/'home')
        self.commit()

    def render_init(self, data):
        values = dict(company=False, ephemeral=False, sudo=True, homebrew=True,
                      email='person@example.invalid', git_name='Example', profile='full')
        self.config.write_text(json.dumps({'data':dict(values, **data)}))
        return tomllib.loads(self.cmd(['chezmoi', '--source', self.repo, '--destination', self.target,
                   '--config', self.config, '--persistent-state', self.root/'state', '--cache', self.root/'cache',
                   'execute-template', '--init', '--file', self.repo/'home/.chezmoi.toml.tmpl']).stdout)['data']

    def test_reinit_preserves_local_proxy_and_empty_package_choice(self):
        custom = dict(proxy_host='localhost', proxy_http_port='18080', proxy_socks_port='18081',
                      hostname='synthetic', package_cask_groups=[], package_cask_exclude=['example-app'])
        rendered = self.render_init(custom)
        for key, value in custom.items():
            self.assertEqual(rendered[key], value)
        self.assertEqual(rendered['profile'], 'full')

    def test_default_proxy_remains_platform_specific(self):
        rendered = self.render_init({})
        expected = ('6152','6153') if sys.platform == 'darwin' else ('7890','7890')
        self.assertEqual((rendered['proxy_http_port'],rendered['proxy_socks_port']), expected)

    def test_claude_proxy_defaults_to_persistent_macs_only(self):
        expected = sys.platform == 'darwin'
        self.assertIs(self.render_init({})['claude_proxy'], expected)
        self.assertIs(self.render_init({'ephemeral': True})['claude_proxy'], False)
        self.assertIs(self.render_init({'claude_proxy': not expected})['claude_proxy'], not expected)
        self.assertIs(self.render_init({'automation_git': True})['automation_git'], True)
        self.assertNotIn('automation_git', self.render_init({}))

    def render_claude(self, data, settings):
        self.config.write_text(json.dumps({'data': dict(profile='full', ephemeral=False, **data)}))
        (self.target/'.claude').mkdir(exist_ok=True)
        if settings is not None:
            (self.target/'.claude/settings.json').write_text(settings)
        chezmoi = ['chezmoi', '--source', self.repo, '--destination', self.target, '--config', self.config,
                   '--persistent-state', self.root/'state', '--cache', self.root/'cache']
        managed = self.cmd(chezmoi + ['managed', '--include=files', self.target/'.claude']).stdout.split()
        if '.claude/settings.json' not in managed:
            return None
        return self.cmd(chezmoi + ['cat', self.target/'.claude/settings.json']).stdout

    def test_claude_settings_merge_and_toggle(self):
        self.assertIsNone(self.render_claude({'claude_proxy': False}, None))
        merged = json.loads(self.render_claude({'claude_proxy': True, 'proxy_host': '127.0.0.1',
            'proxy_http_port': '18080'}, '{"theme":"dark","env":{"KEEP":"1"}}'))
        self.assertEqual(merged['theme'], 'dark')
        self.assertEqual(merged['env']['KEEP'], '1')
        self.assertEqual(merged['env']['HTTPS_PROXY'], 'http://127.0.0.1:18080')
        # Already-correct files pass through byte for byte so app formatting is kept.
        current = json.dumps({'z': 1, 'env': merged['env']})
        entry = self.render_claude({'claude_proxy': True, 'proxy_host': '127.0.0.1',
            'proxy_http_port': '18080'}, current)
        self.assertEqual(entry, current)

    def test_automation_git_adds_and_removes_only_its_git_config(self):
        data = {'claude_proxy': False, 'automation_git': True}
        merged = json.loads(self.render_claude(data, '{"env":{"KEEP":"1"}}'))
        env = merged['env']
        self.assertNotIn('HTTPS_PROXY', env)
        self.assertEqual(env['KEEP'], '1')
        pairs = [(env[f'GIT_CONFIG_KEY_{i}'], env[f'GIT_CONFIG_VALUE_{i}']) for i in range(int(env['GIT_CONFIG_COUNT']))]
        self.assertIn(('url.https://github.com/.insteadOf', 'git@github.com:'), pairs)
        self.assertIn(('gpg.ssh.program', 'ssh-keygen'), pairs)
        self.assertIn(('user.signingkey', f'{self.target}/.ssh/automation-signing'), pairs)
        # The empty helper resets inherited helpers before gh's is added.
        helpers = [value for key, value in pairs if key == 'credential.https://github.com.helper']
        self.assertEqual(helpers[0], '')
        self.assertTrue(helpers[1].endswith('auth git-credential'))
        # Turning the switch off (proxy still managed) removes the git entries and nothing else.
        off = json.loads(self.render_claude({'claude_proxy': True, 'proxy_host': '127.0.0.1',
            'proxy_http_port': '18080'}, json.dumps(merged)))
        self.assertFalse([key for key in off['env'] if key.startswith('GIT_CONFIG_')])
        self.assertEqual(off['env']['KEEP'], '1')
        # A GIT_CONFIG_* set by hand is left alone.
        manual = '{"env":{"GIT_CONFIG_COUNT":"1","GIT_CONFIG_KEY_0":"core.pager","GIT_CONFIG_VALUE_0":"cat"}}'
        kept = json.loads(self.render_claude({'claude_proxy': True, 'proxy_host': '127.0.0.1',
            'proxy_http_port': '18080'}, manual))
        self.assertEqual(kept['env']['GIT_CONFIG_KEY_0'], 'core.pager')

    def test_roost_hooks_add_and_remove_only_their_entries(self):
        command = f'{self.target}/bin/roost hook claude'
        mine = {'hooks': [{'type': 'command', 'command': 'say done'}]}
        current = json.dumps({'hooks': {'Stop': [mine]}, 'theme': 'dark'})
        on = self.render_claude({'claude_proxy': False, 'roost_hooks': True}, current)
        merged = json.loads(on)
        self.assertNotIn('env', merged)
        self.assertEqual(merged['theme'], 'dark')
        self.assertEqual(merged['hooks']['Stop'][0], mine)
        events = ['SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
                  'PermissionRequest', 'PermissionDenied', 'Notification', 'Stop', 'StopFailure', 'SessionEnd']
        self.assertEqual(sorted(merged['hooks']), sorted(events))
        for event in events:
            ours = [g for g in merged['hooks'][event] if g['hooks'][0]['command'] == command]
            self.assertEqual(ours, [{'hooks': [{'type': 'command', 'command': command, 'timeout': 10}]}])
        # Already applied: passes through byte for byte.
        self.assertEqual(self.render_claude({'claude_proxy': False, 'roost_hooks': True}, on), on)
        # Off keeps the hand-written hook and drops events that only had roost's.
        off = json.loads(self.render_claude({'claude_proxy': False, 'roost_hooks': False, 'automation_git': True}, on))
        self.assertEqual(off['hooks'], {'Stop': [mine]})
        self.assertIsNone(self.render_claude({'claude_proxy': False}, '{}'))

    def render_codex(self, data, content, name='config.toml'):
        self.config.write_text(json.dumps({'data': dict(profile='full', ephemeral=False, claude_proxy=False, **data)}))
        (self.target/'.codex').mkdir(exist_ok=True)
        if content is not None:
            (self.target/'.codex'/name).write_text(content)
        chezmoi = ['chezmoi', '--source', self.repo, '--destination', self.target, '--config', self.config,
                   '--persistent-state', self.root/'state', '--cache', self.root/'cache']
        managed = self.cmd(chezmoi + ['managed', '--include=files', self.target/'.codex']).stdout.split()
        if f'.codex/{name}' not in managed:
            return None
        return self.cmd(chezmoi + ['cat', self.target/'.codex'/name]).stdout

    def test_roost_takes_itself_out_of_codex_notify(self):
        roost = json.dumps(f'{self.target}/bin/roost')
        before = 'model = "gpt-5"\nnotify = ["/Apps/Sky.app/Client", "turn-ended"]\n\n[tui]\nx = 1\n'
        # Left alone when roost isn't in it, on or off.
        self.assertEqual(self.render_codex({'roost_hooks': True}, before), before)
        self.assertEqual(self.render_codex({'roost_hooks': False}, before), before)
        # The old wrapping, roost outside.
        wrapped = before.replace('notify = [', f'notify = [{roost}, "hook", "codex", "--chain", ')
        self.assertEqual(self.render_codex({'roost_hooks': True}, wrapped), before)
        # Computer Use wrapped roost's wrapping again; roost lost $TMUX_PANE in there.
        chain = json.dumps([f'{self.target}/bin/roost', 'hook', 'codex', '--chain', '/Apps/Sky.app/Client', 'turn-ended'], separators=(',', ':')).replace('/', '\\/')
        nested = before.replace('"turn-ended"]', '"turn-ended", "--previous-notify", ' + json.dumps(chain) + ']')
        self.assertIn('--previous-notify', tomllib.loads(nested)['notify'])
        self.assertEqual(self.render_codex({'roost_hooks': True}, nested), before)
        # Only roost: notify goes away.
        alone = f'notify = [{roost}, "hook", "codex"]\n[tui]\nx = 1\n'
        self.assertEqual(self.render_codex({'roost_hooks': True}, alone), '[tui]\nx = 1\n')
        # Hosts that never set roost_hooks don't manage Codex at all.
        self.assertIsNone(self.render_codex({}, before))

    def test_codex_multiline_notify_without_roost_is_preserved(self):
        before = ('model = "gpt-5"\nnotify = [\n'
                  '    "/Apps/Computer Use.app/Client", # keep this comment\n'
                  '    "turn-ended",\n]\n\n[tui]\nx = 1\n')
        for enabled in (True, False):
            with self.subTest(roost_hooks=enabled):
                self.assertEqual(self.render_codex({'roost_hooks': enabled}, before), before)

    def test_roost_multiline_notify_migrates_without_changing_other_settings(self):
        roost = f'{self.target}/bin/roost'
        client = ['/Apps/[Computer Use]/$Client', 'turn-ended']
        suffix = '\n[tui]\nx = 1\nnotify = ["unrelated nested setting"]\n'
        legacy = [roost, 'hook', 'codex', '--chain', *client]
        nested = [*client, '--previous-notify', json.dumps(legacy)]
        for args in (legacy, nested, [roost, 'hook', 'codex']):
            for enabled in (True, False):
                with self.subTest(args=args, roost_hooks=enabled):
                    before = 'model = "gpt-5"\nnotify = [\n' + ''.join(
                        f'    {json.dumps(arg)}, # argument\n' for arg in args) + '] # notify\n' + suffix
                    rendered = self.render_codex({'roost_hooks': enabled}, before)
                    parsed = tomllib.loads(rendered)
                    self.assertEqual(parsed.get('notify'), client if len(args) > 3 else None)
                    self.assertTrue(rendered.startswith('model = "gpt-5"\n'))
                    self.assertTrue(rendered.endswith(suffix))
                    self.assertEqual(self.render_codex({'roost_hooks': enabled}, rendered), rendered)

    def test_roost_notify_accepts_literal_strings_and_crlf(self):
        before = (f"notify = [\r\n  '{self.target}/bin/roost', 'hook', 'codex',\r\n"
                  "  '--chain', '/Apps/[Computer Use]/$Client', 'turn-ended',\r\n] # keep\r\n"
                  "[tui]\r\nx = 1\r\n")
        # subprocess text mode normalizes newlines in captured output.
        rendered = self.render_codex({'roost_hooks': True}, before)
        self.assertEqual(tomllib.loads(rendered)['notify'], ['/Apps/[Computer Use]/$Client', 'turn-ended'])
        self.assertIn(' # keep\n[tui]\nx = 1\n', rendered)

    def test_nested_notify_without_top_level_notify_is_preserved(self):
        before = f'[custom]\nnotify = [\n"{self.target}/bin/roost", "hook", "codex",\n]\n'
        self.assertEqual(self.render_codex({'roost_hooks': True}, before), before)

    def test_roost_codex_hooks_add_and_remove_only_their_entries(self):
        command = f'{self.target}/bin/roost hook codex'
        mine = {'hooks': [{'type': 'command', 'command': 'say done'}]}
        on = self.render_codex({'roost_hooks': True}, json.dumps({'hooks': {'Stop': [mine]}}), 'hooks.json')
        merged = json.loads(on)
        events = ['SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PermissionRequest', 'PostToolUse', 'Stop']
        self.assertEqual(sorted(merged['hooks']), sorted(events))
        self.assertEqual(merged['hooks']['Stop'][0], mine)
        roost = {'type': 'command', 'command': command, 'timeout': 10}
        self.assertEqual(merged['hooks']['PreToolUse'], [{'matcher': '*', 'hooks': [roost]}])
        self.assertEqual(merged['hooks']['SessionStart'], [{'hooks': [roost]}])
        # Already applied: passes through byte for byte.
        self.assertEqual(self.render_codex({'roost_hooks': True}, on, 'hooks.json'), on)
        # Off keeps the hand-written hook only.
        off = json.loads(self.render_codex({'roost_hooks': False}, on, 'hooks.json'))
        self.assertEqual(off, {'hooks': {'Stop': [mine]}})
        # No file yet.
        fresh = json.loads(self.render_codex({'roost_hooks': True}, None, 'hooks.json'))
        self.assertEqual(sorted(fresh['hooks']), sorted(events))
        self.assertIsNone(self.render_codex({}, None, 'hooks.json'))

    def test_full_shell_does_not_load_removed_tldr_plugin(self):
        rendered = self.cmd(['chezmoi', '--source', self.repo, '--destination', self.target,
                    '--config', self.config, '--override-data', '{"profile":"full"}',
                    'execute-template', '--file', self.repo/'home/dot_zshrc.tmpl']).stdout
        self.assertNotIn('tldr', rendered)

    def test_false_homebrew_preserved_and_guards_retained(self):
        # Avoid keyword override ambiguity when composing fixture dictionaries.
        data = dict(company=False, ephemeral=False, sudo=True, homebrew=False,
                    email='person@example.invalid', git_name='Example', profile='full')
        for updates in ({}, {'homebrew':True, 'sudo':False}, {'homebrew':True,'ephemeral':True}):
            self.config.write_text(json.dumps({'data':dict(data, **updates)}))
            output = self.cmd(['chezmoi','--source',self.repo,'--destination',self.target,'--config',self.config,
                       'execute-template','--init','--file',self.repo/'home/.chezmoi.toml.tmpl']).stdout
            self.assertFalse(tomllib.loads(output)['data']['homebrew'])

    def test_paths_created_after_render_are_found_and_deduplicated(self):
        rendered = self.cmd(['chezmoi', '--source', self.repo, '--destination', self.target,
                    '--config', self.config, '--override-data', '{"profile":"core"}',
                    'execute-template', '--file', self.repo/'home/dot_zshrc.tmpl']).stdout
        (self.target/'.zshrc').write_text(rendered)
        directories = ['bin','go/bin','.cargo/bin','.local/bin']
        for name in directories:
            (self.target/name).mkdir(parents=True)
        output = self.cmd(['zsh','-f','-c','source ~/.zshrc; source ~/.zshrc; print -l -- $path'],
                          env=dict(self.env, TERM_PROGRAM='')).stdout.splitlines()
        for name in directories:
            self.assertEqual(output.count(str(self.target/name)), 1)
        self.assertEqual(output[:4], [str(self.target/name) for name in directories])

    def test_conda_source_and_explicit_or_missing_script_hook_fallback(self):
        prefix = self.target/'opt/miniforge3'
        (prefix/'bin').mkdir(parents=True)
        (prefix/'etc/profile.d').mkdir(parents=True)
        conda = prefix/'bin/conda'
        conda.write_text('#!/bin/sh\necho "export DOTFILES_TEST_CONDA=hook"\n')
        conda.chmod(0o755)
        script = prefix/'etc/profile.d/conda.sh'
        script.write_text('export DOTFILES_TEST_CONDA=source\n')
        output = self.cmd(['chezmoi','--source',self.repo,'--destination',self.target,'--config',self.config,
                   'execute-template','--file',self.repo/'home/dot_zshrc.tmpl']).stdout
        (self.target/'.zshrc').write_text(output)
        command = ['zsh','-f','-c','source ~/.zshrc; print -r -- "$DOTFILES_TEST_CONDA"']
        self.assertEqual(self.cmd(command).stdout.strip(), 'source')
        self.assertEqual(self.cmd(command, env=dict(self.env,DOTFILES_CONDA_INIT='hook')).stdout.strip(), 'hook')
        script.unlink()
        self.assertEqual(self.cmd(command).stdout.strip(), 'hook')


class CaskChoicesTests(unittest.TestCase):
    packages = dict(casks=['old-app'], cask_groups={'personal':['personal-app'], 'company':['work-app']})

    def test_role_selects_additions_without_removing_legacy_apps(self):
        self.assertEqual(base.SOFTWARE.selected_casks(self.packages, {'company':False}), ['old-app','personal-app'])
        self.assertEqual(base.SOFTWARE.selected_casks(self.packages, {'company':True}), ['old-app','work-app'])

    def test_explicit_groups_and_exclusions_override_role_without_uninstalling(self):
        result = base.SOFTWARE.selected_casks(self.packages, dict(company=True, groups=['desktop','personal','personal'],exclude=['old-app']))
        self.assertEqual(result, ['personal-app'])
        self.assertEqual(base.SOFTWARE.selected_casks(self.packages, {'groups':[]}), [])

    def test_invalid_group_and_exclusion_types_fail(self):
        for data in ({'groups':['unknown']}, {'groups':'desktop'}, {'exclude':'old-app'}):
            with self.assertRaises(base.SOFTWARE.Stop):
                base.SOFTWARE.selected_casks(self.packages, data)


class DiagnosticTests(base.Fixture):
    def command(self):
        return [sys.executable,'-c',"import sys; print('synthetic-secret'); print('package reason', file=sys.stderr); sys.exit(9)"]

    def test_default_failure_names_stage_without_output(self):
        with self.assertRaises(base.UPDATE.Stop) as result:
            base.UPDATE.run(self.command(), stage='Homebrew install', diagnostic_output=True)
        self.assertIn('Homebrew install', str(result.exception))
        self.assertNotIn('synthetic-secret', str(result.exception))
        self.assertIsNone(base.UPDATE._diagnostics)

    def test_opt_in_log_is_private_and_only_eligible_output_is_recorded(self):
        directory = self.root/'diagnostic'
        with base.UPDATE.diagnostic_session(directory, self.repo):
            with self.assertRaises(base.UPDATE.Stop):
                base.UPDATE.run(self.command(), stage='configuration dump')
            self.assertNotIn('synthetic-secret', (directory/'commands.log').read_text())
            with self.assertRaises(base.UPDATE.Stop):
                base.UPDATE.run(self.command(), stage='Homebrew install', diagnostic_output=True)
        self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((directory/'commands.log').stat().st_mode), 0o600)
        self.assertIn('package reason', (directory/'commands.log').read_text())
        self.assertIsNone(base.UPDATE._diagnostics)

    def test_existing_directory_and_source_destination_refused(self):
        for destination in (self.repo/'diagnostics', self.root):
            with self.assertRaises((base.UPDATE.Stop, FileExistsError)):
                with base.UPDATE.diagnostic_session(destination, self.repo):
                    self.fail('Unsafe diagnostic destination accepted')

    def test_cli_opt_in_metadata_does_not_log_rendered_configuration(self):
        result = self.cli('status','--diagnostic-dir',self.root/'diagnostic')
        log = (self.root/'diagnostic/commands.log').read_text()
        self.assertIn('configuration status',log)
        self.assertNotIn('before',log)
        self.assertNotIn('stderr:',log)


class SoftwareIntegrationTests(base.Fixture):
    def setUp(self):
        super().setUp()
        (self.repo/'home/.chezmoidata').mkdir()
        shutil.copy(base.ROOT/'home/.chezmoidata/packages.yaml', self.repo/'home/.chezmoidata/packages.yaml')
        self.commit()

    def test_generated_package_plans_omit_removed_software_on_all_managers(self):
        args = SimpleNamespace(repo=self.repo, target=self.target, config=self.config,
                               action='plan', manager='brew')
        with patch.dict(os.environ, self.env):
            data = base.SOFTWARE.package_data(args)
        for system, manager, company in [('Darwin', 'brew', False), ('Darwin', 'brew', True),
                                         ('Linux', 'brew', False), ('Linux', 'apt', False)]:
            with self.subTest(system=system, manager=manager, company=company):
                args.manager = manager
                selected = dict(data, company=company, osid='linux-ubuntu' if system == 'Linux' else 'darwin')
                output = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
                with patch.object(base.SOFTWARE, 'package_data', return_value=selected), \
                     patch.object(base.SOFTWARE.shutil, 'which', side_effect=lambda name: '/mock/'+name), \
                     patch.object(base.SOFTWARE, 'run', return_value=b'') as run, redirect_stdout(output):
                    base.SOFTWARE.packages(args, [system, 'arm64'])
                output.flush()
                plan = output.buffer.getvalue().decode()
                for removed in ('tldr', 'discord', 'qbittorrent'):
                    self.assertNotIn(removed, plan)
                if manager == 'apt':
                    command = run.call_args.args[0]
                    self.assertEqual(command[:4], ['apt-get', '--simulate', 'install', '--no-upgrade'])
                    self.assertNotIn('tldr', command)
                    self.assertIn('vim-nox', command)
                else:
                    run.assert_not_called()
                    self.assertIn('brew "vim"', plan)
                    if system == 'Darwin':
                        self.assertIn('cask "ghostty"', plan)
                output.close()

    def test_explicit_empty_cask_groups_through_cli(self):
        self.config.write_text(json.dumps({'data':dict(company=True, homebrew=True, sudo=False,
                              osid='darwin', package_cask_groups=[])}))
        result = self.software('packages','plan')
        self.assertIn('brew "fzf"',result.stdout)
        self.assertNotIn('cask ',result.stdout)

    def test_package_failure_default_redacted_and_opt_in_private(self):
        self.mock('brew', 'echo synthetic-secret >&2\nexit 9\n')
        result = self.software('packages','install','--yes',okay=False)
        self.assertIn('Homebrew install',result.stderr)
        self.assertNotIn('synthetic-secret',result.stdout+result.stderr)
        result = self.software('packages','install','--yes','--diagnostic-dir',self.root/'optin',okay=False)
        self.assertNotIn('synthetic-secret',result.stdout+result.stderr)
        self.assertIn('synthetic-secret',(self.root/'optin/commands.log').read_text())


class RuntimeBoundaryTests(base.Fixture):
    def test_unsupported_ctags_is_blocked(self):
        with patch.object(check_runtime.shutil,'which',return_value='/mock/tool'), \
             patch.object(check_runtime.subprocess,'run',return_value=type('Result',(),dict(returncode=1,stdout='',stderr='unsupported'))()):
            with self.assertRaises(check_runtime.Blocked):
                check_runtime.check(self.target, {'PATH':'/mock'})

    def test_tmux_cancellation_cleans_only_dedicated_socket(self):
        calls = []
        def interrupt(command, **kwargs):
            calls.append(command)
            raise KeyboardInterrupt
        with patch.object(check_runtime.subprocess,'run') as cleanup:
            with self.assertRaises(KeyboardInterrupt):
                check_runtime.tmux_smoke(self.target, {'PATH':os.defpath}, interrupt)
        args = cleanup.call_args.args[0]
        self.assertEqual(args[0:2], ['tmux','-S'])
        self.assertEqual(args[-1], 'kill-server')
        self.assertEqual(args[2], str(calls[0][2]))
        self.assertFalse(Path(args[2]).parent.exists())


if __name__ == '__main__':
    unittest.main()
