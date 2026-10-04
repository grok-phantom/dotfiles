"""No host installations: temporary homes/repos and mock network/package tools only."""
import hashlib
import io
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import tarfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / 'scripts' / name))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


UPDATE = load('dotfiles')
SOFTWARE = load('software')


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dotfiles-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.target = self.root / 'target'
        self.bin = self.root / 'bin'
        for path in (self.repo / 'home', self.target, self.bin):
            path.mkdir(parents=True)
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'data': {'ephemeral': False, 'company': False,
            'homebrew': True, 'sudo': False, 'osid': 'darwin', 'email': ''}}))
        self.env = dict(os.environ, HOME=str(self.target), XDG_CONFIG_HOME=str(self.root/'config'),
            XDG_CACHE_HOME=str(self.root/'cache'), GIT_CONFIG_GLOBAL='/dev/null',
            GIT_CONFIG_SYSTEM='/dev/null', PYTHONDONTWRITEBYTECODE='1',
            PATH=str(self.bin)+os.pathsep+os.environ['PATH'], TEST_ROOT=str(self.root))
        (self.repo / '.chezmoiroot').write_text('home\n')
        (self.repo / 'home/dot_probe').write_text('before\n')
        self.git('init', '-b', 'main')
        self.commit()
        self.options = ['--repo', self.repo, '--target', self.target, '--config', self.config,
                        '--state', self.root/'state.boltdb', '--cache', self.root/'cache']
        # Accidental software/network commands fail and leave evidence.
        for command in ('brew', 'curl', 'sudo', 'chsh', 'usermod', 'apt-get', 'ya', 'defaults'):
            self.mock(command, 'echo "$0 $*" >> "$TEST_ROOT/unexpected"\nexit 97\n')

    def cmd(self, args, okay=True, env=None):
        result = subprocess.run([str(x) for x in args], env=env or self.env, capture_output=True, text=True)
        if okay:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def git(self, *args):
        return self.cmd(['git', '-C', self.repo, '-c', 'core.hooksPath=/dev/null',
            '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            '-c', 'commit.gpgsign=false', *args]).stdout.strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-m', 'fixture')

    def cli(self, *args, okay=True):
        return self.cmd([sys.executable, ROOT/'scripts/dotfiles', *args, *self.options], okay=okay)

    def plan_apply(self, name='plan.json', *args):
        path = self.root/name
        self.cli('plan', '--plan', path, *args)
        self.cli('apply', '--plan', path, '--yes', *args)

    def mock(self, name, content):
        path = self.bin/name
        path.write_text('#!/bin/sh\nset -eu\n'+content)
        path.chmod(0o755)

    def software(self, *args, okay=True):
        return self.cmd([sys.executable, ROOT/'scripts/software', *args, '--repo', self.repo,
                        '--target', self.target, '--config', self.config], okay=okay)


class UpdateTests(Fixture):
    def test_default_status_read_only(self):
        self.cli()
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertFalse((self.root/'unexpected').exists())

    def test_plan_apply_verify_repeat(self):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        self.assertFalse((self.target/'.probe').exists())
        self.cli('apply', '--plan', plan, okay=False)
        self.cli('apply', '--plan', plan, '--yes')
        self.cli('verify')
        self.plan_apply('second.json')
        self.assertEqual((self.target/'.probe').read_text(), 'before\n')
        self.assertFalse((self.root/'unexpected').exists())

    def test_dirty_source_rejected_preserved(self):
        (self.repo/'home/dot_probe').write_text('user source\n')
        for command in ('status', 'fetch', 'plan'):
            result = self.cli(command, okay=False)
            self.assertIn('Dirty source', result.stderr)
        self.assertEqual((self.repo/'home/dot_probe').read_text(), 'user source\n')

    def test_target_changes_preserved(self):
        self.plan_apply()
        (self.target/'.probe').write_text('user target\n')
        result = self.cli('plan', okay=False)
        self.assertIn('Target has local changes', result.stderr)
        self.assertEqual((self.target/'.probe').read_text(), 'user target\n')

    def test_stale_target_and_config_plans_stop(self):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        (self.target/'.probe').write_text('new user file\n')
        self.cli('apply', '--plan', plan, '--yes', okay=False)
        self.assertEqual((self.target/'.probe').read_text(), 'new user file\n')
        (self.target/'.probe').unlink()
        self.config.write_text(self.config.read_text()+'\n')
        result = self.cli('apply', '--plan', plan, '--yes', okay=False)
        self.assertIn('stale', result.stderr)
        self.assertFalse((self.target/'.probe').exists())

    def test_fast_forward_only_and_pinned_plan(self):
        self.plan_apply()
        base = self.git('rev-parse', 'HEAD')
        self.git('switch', '-c', 'candidate')
        (self.repo/'home/dot_probe').write_text('after\n')
        self.commit()
        candidate = self.git('rev-parse', 'HEAD')
        self.git('switch', 'main')
        plan = self.root/'next.json'
        self.cli('plan', '--ref', candidate, '--plan', plan)
        self.assertEqual(self.git('rev-parse', 'HEAD'), base)
        self.cli('apply', '--plan', plan, '--yes')
        self.assertEqual(self.git('rev-parse', 'HEAD'), candidate)
        self.assertEqual((self.target/'.probe').read_text(), 'after\n')
        self.cli('plan', '--ref', base, okay=False)

    def test_fetch_failure_does_not_apply(self):
        before = self.git('rev-parse', 'HEAD')
        self.git('remote', 'add', 'offline', str(self.root/'missing-remote'))
        self.cli('fetch', '--remote', 'offline', okay=False)
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertFalse((self.target/'.probe').exists())

    def test_fetch_only_then_review(self):
        remote = self.root/'remote.git'
        self.cmd(['git', 'clone', '--bare', self.repo, remote])
        self.git('remote', 'add', 'origin', str(remote))
        before = self.git('rev-parse', 'HEAD')
        self.cli('fetch')
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertFalse((self.target/'.probe').exists())
        self.cli('plan', '--ref', 'FETCH_HEAD')

    def test_render_error_prevents_source_advance(self):
        base = self.git('rev-parse', 'HEAD')
        self.git('switch', '-c', 'broken')
        (self.repo/'home/dot_bad.tmpl').write_text('{{ fail "broken template" }}')
        self.commit()
        self.git('switch', 'main')
        self.cli('plan', '--ref', 'broken', okay=False)
        self.assertEqual(self.git('rev-parse', 'HEAD'), base)
        self.assertFalse((self.target/'.probe').exists())

    def test_core_rejects_externals(self):
        self.cli('plan', '--component', 'externals', okay=False)
        self.assertFalse((self.root/'unexpected').exists())

    def test_unsupported_os_arch(self):
        for system, arch in [('Windows', 'x86_64'), ('Linux', 'riscv64'), ('Darwin', 'aarch64')]:
            with patch.object(UPDATE.platform, 'system', return_value=system), patch.object(UPDATE.platform, 'machine', return_value=arch):
                with self.assertRaises(UPDATE.Stop):
                    UPDATE.host()

    def test_timeout_is_a_controlled_stop(self):
        with self.assertRaisesRegex(UPDATE.Stop, 'timed out'):
            UPDATE.run([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=0.05)

    def test_cancellation_stops_child_before_it_can_write(self):
        for signum in (signal.SIGINT, signal.SIGTERM):
            ready = self.root/f'ready-{signum}'
            marker = self.root/f'continued-{signum}'
            child = f'from pathlib import Path;import time;Path({str(ready)!r}).touch();time.sleep(1);Path({str(marker)!r}).touch()'
            parent = f'import runpy,sys;m=runpy.run_path({str(ROOT/"scripts/dotfiles")!r});m["run"]([sys.executable,"-c",{child!r}])'
            process = subprocess.Popen([sys.executable,'-c',parent],env=self.env,
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic()+5
                while not ready.exists() and time.monotonic()<deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists())
                process.send_signal(signum)
                process.wait(timeout=5)
                time.sleep(1.1)
                self.assertFalse(marker.exists(), 'Cancelled subprocess continued changing files')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

    def test_permissions_rejected(self):
        args = types.SimpleNamespace(repo=self.repo, target=self.target, config=self.config)
        update = UPDATE.Updates(args)
        with patch.object(UPDATE.os, 'access', return_value=False):
            with self.assertRaisesRegex(UPDATE.Stop, 'not writable'):
                update.permissions(['.probe'])

    def test_apply_failure_does_not_verify(self):
        args = types.SimpleNamespace(repo=self.repo, target=self.target, config=self.config, profile='core',
                                     component='config', state=self.root/'state.boltdb', cache=self.root/'cache',
                                     yes=True, plan=self.root/'plan.json')
        self.cli('plan', '--plan', args.plan)
        update = UPDATE.Updates(args)
        original = update.cm
        writes = []
        def fail_apply(source, command, *values):
            if command in ('apply', 'verify'):
                writes.append((Path(source), command))
            if command == 'apply':
                raise UPDATE.Stop('Injected failure')
            return original(source, command, *values)
        with patch.object(update, 'cm', side_effect=fail_apply):
            with self.assertRaisesRegex(UPDATE.Stop, 'No automatic rollback'):
                update.apply()
        self.assertEqual([command for _, command in writes], ['apply'])
        self.assertFalse(writes[0][0].exists(), 'Failed apply left its temporary source export')


class SoftwareTests(Fixture):
    def setUp(self):
        super().setUp()
        (self.repo/'home/.chezmoidata').mkdir()
        shutil.copy(ROOT/'home/.chezmoidata/packages.yaml', self.repo/'home/.chezmoidata/packages.yaml')
        (self.repo/'locks').mkdir()
        self.installer = self.root/'fake-installer.sh'
        self.installer.write_text('''#!/bin/bash
set -eu
while [ "$#" -gt 0 ]; do
  if [ "$1" = -p ]; then prefix=$2; shift; fi
  shift
done
mkdir -p "$prefix/bin"
printf '#!/bin/sh\\nexit 0\\n' > "$prefix/bin/conda"
chmod +x "$prefix/bin/conda"
echo installed >> "$TEST_ROOT/install-log"
''')
        sha = hashlib.sha256(self.installer.read_bytes()).hexdigest()
        platforms = {x:{'url':'https://example.invalid/installer.sh','sha256':sha}
                     for x in ('MacOSX-arm64','MacOSX-x86_64','Linux-aarch64','Linux-x86_64')}
        (self.repo/'locks/miniforge.json').write_text(json.dumps({'version':'test','platforms':platforms}))
        self.commit()

    def fake_download(self):
        self.mock('curl', 'while [ "$#" -gt 0 ]; do\n if [ "$1" = --output ]; then cp "$TEST_ROOT/fake-installer.sh" "$2"; exit 0; fi\n shift\ndone\nexit 1\n')

    def test_software_core_profile_no_actions(self):
        self.software('packages', 'install', '--yes', okay=False)
        self.software('miniforge', 'apply', '--yes', okay=False)
        self.assertFalse((self.root/'unexpected').exists())

    def test_default_python_does_not_write_source_bytecode(self):
        scripts = self.repo/'scripts'
        scripts.mkdir()
        for name in ('dotfiles', 'software'):
            shutil.copy(ROOT/'scripts'/name, scripts/name)
        self.commit()
        env = dict(self.env)
        env.pop('PYTHONDONTWRITEBYTECODE', None)
        env.pop('PYTHONPYCACHEPREFIX', None)
        # Force the normal CPython location even on Apple's prefixed-cache build.
        code = "import sys,runpy;sys.pycache_prefix=None;sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
        self.cmd([sys.executable, '-c', code, scripts/'software', 'miniforge', 'plan',
                  '--profile', 'full', '--target', self.target], env=env)
        self.assertFalse((scripts/'__pycache__').exists())
        self.assertEqual(self.git('status', '--porcelain=v1'), '')

    def test_brew_install_and_upgrade_separate(self):
        self.mock('brew', 'printf "%s %s %s\\n" "$*" "$HOMEBREW_NO_AUTO_UPDATE" "$HOMEBREW_NO_INSTALL_CLEANUP" >> "$TEST_ROOT/brew-log"\n')
        self.software('packages', 'plan', '--profile', 'full')
        self.assertFalse((self.root/'brew-log').exists())
        self.software('packages', 'install', '--profile', 'full', '--yes')
        log = (self.root/'brew-log').read_text()
        self.assertIn('--no-upgrade', log)
        self.assertNotIn('--upgrade', log)
        self.assertNotIn('update ', log)
        self.software('packages', 'upgrade', '--profile', 'full', '--yes')
        log = (self.root/'brew-log').read_text()
        self.assertIn('--upgrade', log)
        self.assertIn('update ', log)

    def test_brew_failure_stops_verification(self):
        self.mock('brew', 'echo "$*" >> "$TEST_ROOT/brew-log"\nexit 9\n')
        self.software('packages', 'upgrade', '--profile', 'full', '--yes', okay=False)
        self.assertEqual((self.root/'brew-log').read_text(), 'update\n')

    def test_apt_wrong_platform_rejected(self):
        with patch.object(SOFTWARE, 'package_data', return_value={'packages': {'darwin': {}}, 'osid':'darwin'}):
            args = types.SimpleNamespace(action='plan', manager='apt')
            with self.assertRaises(SOFTWARE.Stop):
                SOFTWARE.packages(args, ['Darwin','arm64'])

    def test_apt_permission_and_selected_upgrade_only(self):
        data = {'packages': {'linux': {'apt':['git','zsh']}}, 'osid':'linux-ubuntu', 'sudo':False}
        args = types.SimpleNamespace(action='upgrade', manager='apt', yes=True)
        with patch.object(SOFTWARE, 'package_data', return_value=data), \
             patch.object(SOFTWARE.shutil, 'which', return_value='/mock/apt-get'), \
             patch.object(SOFTWARE, 'run', return_value=b'') as command:
            with self.assertRaises(SOFTWARE.Stop):
                SOFTWARE.packages(args, ['Linux','aarch64'])
            command.assert_not_called()
            data['sudo'] = True
            SOFTWARE.packages(args, ['Linux','aarch64'])
            self.assertEqual(command.call_args_list[-1].args[0],
                ['sudo','-n','apt-get','install','-y','--only-upgrade','git','zsh'])
            self.assertEqual(command.call_args_list[0].args[0], ['sudo','-n','true'])

    def test_miniforge_network_failure_no_install(self):
        self.software('miniforge', 'apply', '--profile', 'full', '--yes', okay=False)
        self.assertFalse((self.target/'opt/miniforge3').exists())

    def test_miniforge_symlink_prefix_refused(self):
        (self.target/'opt').symlink_to(self.root, target_is_directory=True)
        self.software('miniforge','apply','--profile','full','--yes',okay=False)
        self.assertFalse((self.root/'unexpected').exists())

    def test_miniforge_hash_mismatch_no_install(self):
        self.fake_download()
        self.installer.write_text(self.installer.read_text()+'# changed\n')
        result = self.software('miniforge', 'apply', '--profile', 'full', '--yes', okay=False)
        self.assertIn('SHA-256 mismatch', result.stderr)
        self.assertFalse((self.root/'install-log').exists())

    def test_miniforge_repeat_and_explicit_existing_update(self):
        self.fake_download()
        self.software('miniforge', 'plan', '--profile', 'full')
        self.assertFalse((self.root/'install-log').exists())
        for _ in range(2):
            self.software('miniforge', 'apply', '--profile', 'full', '--yes')
        self.assertEqual((self.root/'install-log').read_text(), 'installed\n')
        self.software('miniforge', 'verify', '--profile', 'full')
        (self.target/'opt/miniforge3/.dotfiles-installer-sha256').unlink()
        self.software('miniforge', 'apply', '--profile', 'full', '--yes', okay=False)
        self.software('miniforge', 'apply', '--profile', 'full', '--yes', '--update-existing')
        self.assertEqual((self.root/'install-log').read_text().count('installed'), 2)


class TemplateTests(Fixture):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.repo/'home')
        shutil.copytree(ROOT/'home', self.repo/'home')
        self.commit()
        self.mock('brew', 'if [ "${1:-}" = --prefix ]; then echo /mock/brew; else exit 97; fi\n')

    def chezmoi(self, profile, component, command, *args, okay=True, extra=None):
        data = dict(profile=profile, update_component=component)
        if extra:
            data.update(extra)
        return self.cmd(['chezmoi', '--source', self.repo, '--destination', self.target,
            '--config', self.config, '--persistent-state', self.root/'state.boltdb',
            '--cache', self.root/'cache', '--override-data', json.dumps(data),
            command, *args], okay=okay)

    def test_core_and_full_isolation_and_shell_syntax(self):
        for profile in ('core','full'):
            contents = json.loads(self.chezmoi(profile, 'config', 'dump', '--format=json').stdout)
            self.assertNotIn('.tmux', contents)
            if profile == 'core':
                self.assertNotIn('.vimrc', contents)
                self.assertNotIn('.oh-my-zsh', contents)
                self.assertNotIn('conda shell.zsh hook', contents['.zshrc']['contents'])
            else:
                self.assertIn('.vimrc', contents)
                self.assertIn('.tmux.conf', contents)
            gitconfig = self.root/'rendered.gitconfig'
            gitconfig.write_text(contents['.config/git/config']['contents'])
            self.cmd(['git','config','--file',gitconfig,'--list'])
            self.assertNotIn('Lei Chen', gitconfig.read_text())
            self.assertNotIn('grok-phantom', gitconfig.read_text())
            for name, entry in contents.items():
                if name.endswith(('.zsh', '.zshrc', '.zprofile')) and entry['type'] == 'file':
                    output = self.root/'rendered.zsh'
                    output.write_text(entry['contents'])
                    self.cmd(['zsh','-n',output])

    def test_config_only_preserves_external_overlay_files(self):
        external = self.target/'.oh-my-zsh'
        external.mkdir()
        (external/'user-plugin.txt').write_text('keep me\n')
        self.plan_apply('full.json', '--profile', 'full')
        self.assertEqual((external/'user-plugin.txt').read_text(), 'keep me\n')
        self.assertFalse((self.root/'unexpected').exists())

    def test_externals_rendered_only_for_explicit_full(self):
        path = self.repo/'home/.chezmoiexternal.toml.tmpl'
        for profile, component in [('core','config'), ('full','config'), ('core','externals')]:
            output = self.chezmoi(profile, component, 'execute-template', '--file', path).stdout
            self.assertEqual(output.strip(), '')
        output = self.chezmoi('full','externals','execute-template','--file',path).stdout
        self.assertEqual(output.count('checksum.sha256'),20)
        self.assertNotIn('master', output)
        self.assertNotIn('latest', output)
        self.assertNotIn('168h', output)

    def test_linux_template_platform_guards(self):
        extra = {'chezmoi': {'os':'linux','arch':'arm64','osRelease':{'id':'ubuntu'}}, 'osid':'linux-ubuntu'}
        contents = json.loads(self.chezmoi('full','config','dump','--format=json',extra=extra).stdout)
        self.assertNotIn('.config/karabiner/karabiner.json', contents)
        self.assertFalse(any(x.startswith('Library/') for x in contents))
        external = self.chezmoi('full','externals','execute-template','--file',
            self.repo/'home/.chezmoiexternal.toml.tmpl',extra=extra).stdout
        self.assertIn('.local/share/fonts', external)
        self.assertNotIn('Library/Fonts', external)

    def test_external_checksum_failure_before_apply(self):
        asset = self.root/'external.txt'
        asset.write_text('actual bytes')
        manifest = self.repo/'home/.chezmoidata/external-lock.json'
        manifest.write_text(json.dumps({'external_lock':[{'target':'test.ttf','kind':'font',
            'url':asset.as_uri(), 'sha256':'0'*64}]}))
        self.commit()
        self.cli('plan','--profile','full','--component','externals',okay=False)
        self.assertFalse((self.target/'Library/Fonts/test.ttf').exists())

    def test_external_archives_with_own_config_are_consistent(self):
        locked = []
        for number, (target, name) in enumerate([('.oh-my-zsh','oh-my-zsh.sh'),
                ('.oh-my-zsh/custom/plugins/test','plugin.zsh'), ('.vim_runtime','vimrcs/basic.vim')]):
            archive = self.root/f'archive-{number}.tar.gz'
            with tarfile.open(archive, 'w:gz') as stream:
                data = b'# harmless fixture\n'
                entry = tarfile.TarInfo('upstream/'+name)
                entry.size = len(data)
                stream.addfile(entry, io.BytesIO(data))
            locked.append(dict(target=target, kind='archive', url=archive.as_uri(),
                               sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
        (self.repo/'home/.chezmoidata/external-lock.json').write_text(json.dumps({'external_lock':locked}))
        self.commit()
        self.plan_apply('externals.json','--profile','full','--component','externals')
        self.cli('verify','--profile','full','--component','externals')
        self.assertTrue((self.target/'.config/vim/my_configs.vim').is_file())
        self.assertTrue((self.target/'.config/zsh/completions/_chezmoi').is_file())
        self.assertTrue((self.target/'.oh-my-zsh/custom/plugins/test/plugin.zsh').is_file())
        self.plan_apply('repeat.json','--profile','full','--component','externals')

    def test_ephemeral_fonts_and_unknown_os_are_guarded(self):
        template = self.repo/'home/.chezmoiexternal.toml.tmpl'
        for extra in ({'ephemeral':True}, {'chezmoi':{'os':'freebsd','arch':'amd64'}}):
            output = self.chezmoi('full','externals','execute-template','--file',template,extra=extra).stdout
            self.assertNotIn('.ttf', output)

    def test_init_blank_and_local_identity(self):
        path = self.repo/'home/.chezmoi.toml.tmpl'
        output = self.chezmoi('core','config','execute-template','--init',
            '--promptBool','company=false,ephemeral=false,sudo=false',
            '--promptString','Git name (blank to configure locally)=',
            '--promptChoice','Configuration profile=core','--file',path).stdout
        self.assertIn('git_name = ""',output)
        self.assertNotIn('grok.phantom',output)
        output = self.chezmoi('core','config','execute-template','--file',
            self.repo/'home/private_dot_config/git/config.tmpl',
            extra={'git_name':'Example User','email':'person@example.invalid'}).stdout
        self.assertIn('name = "Example User"',output)
        self.assertIn('email = "person@example.invalid"',output)


if __name__ == '__main__':
    unittest.main()
