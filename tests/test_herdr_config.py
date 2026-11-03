"""Shared configuration ownership, retirement and local feature selection."""
import json
import shutil
from types import SimpleNamespace
from unittest.mock import patch
import test_updates as base


class ConfigurationTests(base.Fixture):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.repo/'home')
        shutil.copytree(base.ROOT/'home', self.repo/'home')
        self.data = dict(profile='full', ephemeral=False, claude_proxy=False, roost_hooks=True)
        self.config.write_text(json.dumps({'data': self.data}))
        self.cm = ['chezmoi', '--source', self.repo, '--destination', self.target,
                   '--config', self.config, '--persistent-state', self.root/'state',
                   '--cache', self.root/'cache', '--refresh-externals=never']

    def render(self, relative, current=None, okay=True):
        path = self.target/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if current is not None:
            path.write_text(current)
        return self.cmd(self.cm + ['cat', path], okay=okay).stdout

    def test_merge_preserves_local_keys_and_is_byte_idempotent(self):
        import tomllib
        current = '[custom]\nvalue = "keep"\n[[keys.command]]\nkey = "prefix+9"\ncommand = "user.action"\ntype = "plugin_action"\n'
        rendered = self.render('.config/herdr/config.toml', current)
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed['custom']['value'], 'keep')
        self.assertTrue(any(x['command'] == 'user.action' for x in parsed['keys']['command']))
        self.assertEqual(self.render('.config/herdr/config.toml', rendered), rendered)
        memex = self.render('.memex/config.toml', '[custom]\nvalue = 1\n')
        self.assertEqual(tomllib.loads(memex)['custom']['value'], 1)
        self.assertFalse(tomllib.loads(memex)['embeddings'])
        self.assertEqual(self.render('.memex/config.toml', memex), memex)

    def test_shortcut_conflict_does_not_touch_target(self):
        current = '[[keys.command]]\nkey = "prefix+f"\ncommand = "user.action"\n'
        self.render('.config/herdr/config.toml', current, okay=False)
        self.assertEqual((self.target/'.config/herdr/config.toml').read_text(), current)

    def test_removed_binding_is_retired_without_removing_user_command(self):
        import tomllib
        current = self.render('.config/herdr/config.toml', '[[keys.command]]\nkey = "prefix+9"\ncommand = "user.action"\n')
        manifest = self.repo/'home/.chezmoidata/herdr.json'
        data = json.loads(manifest.read_text())
        removed = data['herdr_shortcuts']['bindings'].pop(0)
        data['herdr_shortcuts']['retired_commands'].append(removed['command'])
        manifest.write_text(json.dumps(data))
        rendered = self.render('.config/herdr/config.toml', current)
        commands = [x['command'] for x in tomllib.loads(rendered)['keys']['command']]
        self.assertNotIn(removed['command'], commands)
        self.assertIn('user.action', commands)

    def test_help_and_bindings_share_the_manifest(self):
        import tomllib
        config = tomllib.loads(self.render('.config/herdr/config.toml'))
        help_text = self.render('.config/herdr/shortcuts.txt')
        bindings = json.loads((self.repo/'home/.chezmoidata/herdr.json').read_text())['herdr_shortcuts']['bindings']
        self.assertEqual(config['keys']['command'], bindings)
        for item in bindings:
            self.assertIn(item['key'] + '  ' + item['description'], help_text)
        self.assertEqual(len({x['key'] for x in bindings}), len(bindings))
        self.assertEqual(len({x['command'] for x in bindings}), len(bindings))

    def test_optional_flags_and_core_do_not_manage_or_delete_existing_files(self):
        path = self.target/'.config/herdr/config.toml'
        path.parent.mkdir(parents=True)
        path.write_text('# user settings\n')
        for extra in (dict(herdr_enabled=False, cmux_enabled=False), dict(profile='core')):
            self.config.write_text(json.dumps({'data': dict(self.data, **extra)}))
            managed = self.cmd(self.cm + ['managed', '--include=files']).stdout
            self.assertNotIn('.config/herdr/', managed)
            self.assertNotIn('.config/cmux/', managed)
            self.assertNotIn('.memex/', managed)
            self.assertEqual(path.read_text(), '# user settings\n')
        self.config.write_text(json.dumps({'data': dict(self.data, herdr_enabled='false')}))
        self.cmd(self.cm + ['managed'], okay=False)

    def test_reinit_preserves_terminal_choices(self):
        import tomllib
        self.data.update(herdr_enabled=False, cmux_enabled=True, company=False, sudo=True,
                         homebrew=True, email='', git_name='')
        self.config.write_text(json.dumps({'data': self.data}))
        result = self.cmd(self.cm + ['execute-template', '--init', '--file', self.repo/'home/.chezmoi.toml.tmpl'])
        parsed = tomllib.loads(result.stdout)['data']
        self.assertIs(parsed['herdr_enabled'], False)
        self.assertIs(parsed['cmux_enabled'], True)

    def test_mixed_user_and_managed_hooks_survive_enable_and_disable(self):
        user = dict(type='command', command='user-hook', timeout=42)
        for relative, agent in [('.claude/settings.json','claude'), ('.codex/hooks.json','codex')]:
            owned = dict(type='command', command=f'{self.target}/bin/roost hook {agent}', timeout=10)
            current = json.dumps({'hooks': {'Stop': [{'matcher': 'custom', 'hooks': [owned, user]}]}})
            for enabled in (True, False):
                self.data['roost_hooks'] = enabled
                self.config.write_text(json.dumps({'data': self.data}))
                rendered = json.loads(self.render(relative, current))
                groups = rendered['hooks']['Stop']
                self.assertIn({'matcher':'custom','hooks':[user]}, groups)
                commands = [h['command'] for g in groups for h in g['hooks']]
                self.assertEqual(commands.count('user-hook'), 1)
                self.assertEqual(commands.count(owned['command']), int(enabled))

    def test_disabled_herdr_omits_only_its_packages(self):
        from contextlib import redirect_stdout
        import io
        data = dict(homebrew=True, herdr_enabled=False, packages={'darwin': {
            'brews':['herdr','memex','git','go'], 'casks':[]}})
        args = SimpleNamespace(action='plan', manager='brew')
        output = io.StringIO()
        with patch.object(base.SOFTWARE, 'package_data', return_value=data), \
             patch.object(base.SOFTWARE.shutil, 'which', return_value='/mock/brew'), redirect_stdout(output):
            base.SOFTWARE.packages(args, ['Darwin','arm64'])
        self.assertNotIn('brew "herdr"', output.getvalue())
        self.assertNotIn('brew "memex"', output.getvalue())
        self.assertIn('brew "git"', output.getvalue())
        self.assertIn('brew "go"', output.getvalue())

    def test_disabled_plugin_cli_stops_before_inventory(self):
        self.data['herdr_enabled'] = False
        self.config.write_text(json.dumps({'data': self.data}))
        self.commit()
        self.mock('herdr', 'touch "$TEST_ROOT/unexpected"\nexit 97\n')
        result = self.software('herdr-plugins', okay=False)
        self.assertIn('Herdr is disabled', result.stderr)
        self.assertFalse((self.root/'unexpected').exists())

    def test_core_plugin_cli_stops_before_inventory(self):
        self.commit()
        self.mock('herdr', 'touch "$TEST_ROOT/unexpected"\nexit 97\n')
        result = self.software('herdr-plugins', '--profile', 'core', okay=False)
        self.assertIn('require --profile full', result.stderr)
        self.assertFalse((self.root/'unexpected').exists())
