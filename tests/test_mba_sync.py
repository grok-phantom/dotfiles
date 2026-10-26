"""Run mba-sync with real rsync against a local SSH stand-in; never touches the network."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'home/bin/executable_mba-sync'


@unittest.skipUnless(shutil.which('rsync'), 'rsync is not installed')
class SyncRemote(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root/'bin'
        self.home = self.root/'home'
        self.remote = self.root/'remote'
        for path in (self.bin, self.home, self.remote):
            path.mkdir()
        self.log = self.root/'ssh.log'
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'], HOME=str(self.home),
                        MBA_HOST='fixture-host', FIXTURE_REMOTE=str(self.remote), FIXTURE_LOG=str(self.log))
        # Like ssh: drop options and the host, join the rest into one remote shell command.
        self.stub('ssh', '''
            import os, subprocess, sys
            args = sys.argv[1:]
            while args and args[0].startswith('-'):
                args = args[1:]
            command = ' '.join(args[1:])
            with open(os.environ['FIXTURE_LOG'], 'a') as log:
                log.write(command + '\\n')
            env = dict(os.environ, HOME=os.environ['FIXTURE_REMOTE'])
            sys.exit(subprocess.run(['/bin/sh', '-c', command], cwd=env['HOME'], env=env).returncode)
        ''')
        self.stub('osascript', 'pass\n')
        self.project = self.home/"workspace/my project's"
        self.write(self.project/'src/main file.txt', 'main')
        self.write(self.project/'.gitignore', 'build/\n')
        self.write(self.project/'build/out.bin', 'built')
        self.write(self.project/'.git/HEAD', 'ref: refs/heads/main')
        self.write(self.project/'.DS_Store', 'finder')

    def stub(self, name, code):
        path = self.bin/name
        path.write_text('#!'+sys.executable+'\n'+textwrap.dedent(code))
        path.chmod(0o755)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def sync(self, *args, cwd=None):
        return subprocess.run(['bash', str(SCRIPT), *map(str, args)], env=self.env, cwd=cwd or self.home,
                              capture_output=True, text=True, timeout=30)

    def files(self, base):
        return sorted(str(p.relative_to(base)) for p in base.rglob('*') if p.is_file())

    def test_directory_lands_at_same_path_under_remote_home_without_git_or_ignored_files(self):
        result = self.sync(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.files(self.remote/"workspace/my project's"), ['.gitignore', 'src/main file.txt'])

    def test_all_includes_git_and_ignored_files(self):
        result = self.sync('--all', self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.files(self.remote/"workspace/my project's"),
                         ['.git/HEAD', '.gitignore', 'build/out.bin', 'src/main file.txt'])

    def test_remote_only_files_and_remote_git_state_are_kept(self):
        # macOS's openrsync ignores .gitignore when deleting, so the tool never deletes.
        target = self.remote/"workspace/my project's"
        self.write(target/'.env', 'remote secret')
        self.write(target/'.git/HEAD', 'remote git')
        result = self.sync(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target/'.env').read_text(), 'remote secret')
        self.assertEqual((target/'.git/HEAD').read_text(), 'remote git')

    def test_single_file_creates_missing_parent(self):
        result = self.sync('main file.txt', cwd=self.project/'src')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.remote/"workspace/my project's/src/main file.txt").read_text(), 'main')

    def test_dry_run_changes_nothing(self):
        result = self.sync('-n', self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.files(self.remote), [])
        self.assertIn('dry run', result.stdout)

    def test_paths_outside_home_or_home_itself_are_refused_before_connecting(self):
        outside = self.root/'outside'
        outside.mkdir()
        for path in (outside, self.home):
            result = self.sync(path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not inside ~', result.stderr)
        self.assertFalse(self.log.exists())

    def test_newer_file_on_receiving_side_is_not_overwritten(self):
        target = self.remote/"workspace/my project's/src/main file.txt"
        self.write(target, 'edited on remote')
        later = (self.project/'src/main file.txt').stat().st_mtime + 60
        os.utime(target, (later, later))
        self.assertEqual(self.sync(self.project).returncode, 0)
        self.assertEqual(target.read_text(), 'edited on remote')

    def git(self, cwd, *args):
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *args],
                       cwd=cwd, check=True, capture_output=True)

    def remote_repo(self):
        repo = self.remote/'workspace/remote repo'
        self.write(repo/'tracked.txt', 'tracked')
        self.write(repo/'.gitignore', 'build/\n')
        self.write(repo/'gone.txt', 'deleted but not committed')
        self.git(repo, 'init', '-q')
        self.git(repo, 'add', '.')
        self.git(repo, 'commit', '-qm', 'fixture')
        (repo/'gone.txt').unlink()
        self.write(repo/'new file.txt', 'untracked')
        self.write(repo/'build/out.bin', 'built')
        self.write(repo/'.DS_Store', 'finder')
        return repo

    def test_pull_copies_remote_git_files_into_a_new_local_directory(self):
        self.remote_repo()
        result = self.sync('--pull', self.home/'workspace/remote repo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.files(self.home/'workspace/remote repo'), ['.gitignore', 'new file.txt', 'tracked.txt'])

    def test_pull_all_includes_git_and_ignored_files(self):
        self.remote_repo()
        result = self.sync('--pull', '--all', self.home/'workspace/remote repo')
        self.assertEqual(result.returncode, 0, result.stderr)
        files = self.files(self.home/'workspace/remote repo')
        self.assertIn('build/out.bin', files)
        self.assertIn('.git/HEAD', files)

    def test_pull_plain_directory_skips_only_git_and_finder_files(self):
        folder = self.remote/'notes'
        self.write(folder/'a.txt', 'a')
        self.write(folder/'.git/HEAD', 'not a real repo')
        self.write(folder/'.DS_Store', 'finder')
        result = self.sync('--pull', self.home/'notes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.files(self.home/'notes'), ['a.txt'])

    def test_pull_keeps_newer_local_edits_and_local_only_files(self):
        repo = self.remote_repo()
        local = self.home/'workspace/remote repo'
        self.write(local/'tracked.txt', 'edited here')
        self.write(local/'local only.txt', 'mine')
        later = (repo/'tracked.txt').stat().st_mtime + 60
        os.utime(local/'tracked.txt', (later, later))
        self.assertEqual(self.sync('--pull', local).returncode, 0)
        self.assertEqual((local/'tracked.txt').read_text(), 'edited here')
        self.assertTrue((local/'local only.txt').exists())

    def test_pull_single_file_and_missing_remote_path(self):
        self.write(self.remote/'docs/plan.md', 'plan')
        result = self.sync('--pull', 'docs/plan.md')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home/'docs/plan.md').read_text(), 'plan')
        missing = self.sync('--pull', 'docs/none.md')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('not found on fixture-host', missing.stderr)

    def test_short_pull_flag_and_raycast_style_arguments(self):
        self.write(self.remote/'docs/plan.md', 'plan')
        self.assertEqual(self.sync('-r', 'docs/plan.md').returncode, 0)
        self.assertEqual((self.home/'docs/plan.md').read_text(), 'plan')
        # Raycast passes the dropdown value, then an empty path when left blank.
        self.write(self.home/'docs/push.md', 'push')
        result = self.sync('--push', self.home/'docs/push.md')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.remote/'docs/push.md').read_text(), 'push')

    def test_shell_metacharacters_in_names_are_not_executed_remotely(self):
        # The relative path is the part that goes through the remote shell.
        name = 'notes $(touch injected); `touch injected2` *'
        self.write(self.home/name/'x.txt', 'safe')
        result = self.sync(self.home/name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.remote/'injected').exists())
        self.assertFalse((self.remote/'injected2').exists())
        self.assertEqual(self.files(self.remote/name), ['x.txt'])


if __name__ == '__main__':
    unittest.main()
