"""Migration and diagnostics regressions, using synthetic local data only."""
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tomllib
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
        self.config.write_text(json.dumps({'data':dict(company=False, ephemeral=False, sudo=True,
                               homebrew=True, email='person@example.invalid', git_name='Example', profile='full', **data)}))
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
