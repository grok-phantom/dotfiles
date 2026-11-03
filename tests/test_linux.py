"""Linux target guards and Ubuntu deployment prerequisites, without host writes."""
import json
import tomllib
from unittest.mock import patch
import test_updates as base


class LinuxTests(base.Fixture):
    def setUp(self):
        import shutil
        super().setUp()
        shutil.rmtree(self.repo/'home')
        shutil.copytree(base.ROOT/'home', self.repo/'home')
        self.mock('brew', 'if [ "${1:-}" = --prefix ]; then echo /mock/brew; else exit 97; fi\n')
        self.data = dict(company=False, ephemeral=False, sudo=False, homebrew=False,
                         profile='core', email='', git_name='', osid='linux-ubuntu')
        self.config.write_text(json.dumps({'data': self.data}))
        self.cm = ['chezmoi', '--source', self.repo, '--destination', self.target,
                   '--config', self.config, '--persistent-state', self.root/'state',
                   '--cache', self.root/'cache', '--refresh-externals=never']

    def render(self, profile, command, *args, extra=None):
        data = dict(chezmoi={'os':'linux','arch':'amd64','osRelease':{'id':'ubuntu','versionID':'24.04'}},
                    profile=profile, **(extra or {}))
        return self.cmd(self.cm + ['--override-data', json.dumps(data), command, *args]).stdout

    def test_linux_targets_exclude_macos_and_respect_profile(self):
        for profile in ('core','full'):
            contents = json.loads(self.render(profile, 'dump', '--format=json'))
            for name in contents:
                self.assertFalse(name.startswith(('Library/', '.config/ghostty/', '.config/cmux/', '.config/karabiner/')))
            for name in ('bin/mba-clip','bin/mba-shot','bin/git-ssh-sign'):
                self.assertNotIn(name, contents)
            for name in ('bin/mba','bin/mba-sync','bin/workspace','.zshrc','.config/git/config'):
                self.assertIn(name, contents)
            self.assertEqual('.config/herdr/config.toml' in contents, profile == 'full')
            self.assertEqual('.vimrc' in contents, profile == 'full')
            self.assertNotIn('1Password.app', contents['.config/git/config']['contents'])
            self.assertNotIn('launchctl', contents['.zshrc']['contents'])

    def test_linux_ssh_excludes_mac_agent_and_orbstack(self):
        result = self.render('core', 'cat', self.target/'.ssh/config',
                             extra={'ssh_managed':True,'ssh_1password_agent':True})
        self.assertNotIn('orbstack', result)
        self.assertNotIn('Group Containers', result)
        self.assertIn('ForwardAgent no', result)

    def test_existing_homebrew_without_sudo_is_preserved_but_ephemeral_stays_off(self):
        for ephemeral, expected in [(False, True), (True, False)]:
            self.config.write_text(json.dumps({'data':dict(self.data, homebrew=True, ephemeral=ephemeral)}))
            result = self.render('core', 'execute-template', '--init', '--file', self.repo/'home/.chezmoi.toml.tmpl')
            self.assertIs(tomllib.loads(result)['data']['homebrew'], expected)
        self.config.write_text(json.dumps({'data':self.data}))
        result = self.render('core','execute-template','--init','--file',self.repo/'home/.chezmoi.toml.tmpl')
        self.assertFalse(tomllib.loads(result)['data']['homebrew'])

    def test_linux_package_managers_include_their_declared_baseline(self):
        data = json.loads(self.render('full','execute-template','{{ .packages.linux | toJson }}'))
        for name in ('git','chezmoi','zsh','bat','jq','curl','tmux','ripgrep','less'):
            self.assertIn(name, data['brews'])
        for name in ('git','zsh','python3','openssh-client','ca-certificates','less','vim-nox','git-delta'):
            self.assertIn(name, data['apt'])
        for packages in data.values():
            self.assertEqual(len(packages), len(set(packages)))

    def test_noninteractive_linux_mba_does_not_try_desktop_or_ssh(self):
        self.mock('uname', 'echo Linux\n')
        self.mock('ssh', 'touch "$TEST_ROOT/unexpected"\n')
        result = self.cmd(['bash',base.ROOT/'home/bin/executable_mba','-H','example.invalid'],okay=False)
        self.assertIn('交互终端',result.stdout)
        self.assertFalse((self.root/'unexpected').exists())


class LinuxPreflight(base.Fixture):
    def test_targeted_check_rejects_mac_and_old_fzf_without_installing(self):
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader('linux_check', str(base.ROOT/'scripts/check-linux'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with patch.object(module.platform, 'system', return_value='Darwin'):
            with self.assertRaisesRegex(RuntimeError,'target Linux'):
                module.check('core')
        with patch.object(module.platform,'system',return_value='Linux'), \
             patch.object(module.platform,'machine',return_value='x86_64'), \
             patch.object(module.Path,'read_text',return_value='ID=ubuntu\nVERSION_ID="24.04"\n'), \
             patch.object(module.shutil,'which',return_value='/mock/tool'), \
             patch.object(module.subprocess,'check_output',return_value='0.44.1\n'), \
             patch.object(module.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'fzf >= 0.54.0'):
                module.check('full', apt=True)
            run.assert_not_called()

    def test_apt_interactive_keeps_sudo_on_terminal(self):
        from types import SimpleNamespace
        data = dict(packages={'linux':{'apt':['git','zsh']}},osid='linux-ubuntu',sudo=True)
        args = SimpleNamespace(action='install',manager='apt',yes=True,interactive=True)
        with patch.object(base.SOFTWARE,'package_data',return_value=data), \
             patch.object(base.SOFTWARE.shutil,'which',return_value='/mock/apt-get'), \
             patch.object(base.SOFTWARE,'run',return_value=b'') as run:
            base.SOFTWARE.packages(args,['Linux','x86_64'])
        self.assertEqual([c.args[0] for c in run.call_args_list], [
            ['sudo','true'], ['sudo','apt-get','update'],
            ['sudo','apt-get','install','-y','--no-upgrade','git','zsh']])
        self.assertTrue(all(c.kwargs['interactive'] for c in run.call_args_list))
