"""bin/workspace in temporary roots; local bare repos only, no network."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GIT_ID = ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-c', 'commit.gpgsign=false']


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='workspace-test-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.ws = self.tmp/'ws'
        self.env = dict(os.environ, HOME=str(self.tmp/'home'), XDG_CONFIG_HOME=str(self.tmp/'config'),
            WORKSPACE_ROOT=str(self.ws), WORKSPACE_COMPANY='0', GIT_CONFIG_GLOBAL='/dev/null',
            GIT_CONFIG_SYSTEM='/dev/null')
        self.script = self.tmp/'workspace'
        self.script.write_text(self.render('home/bin/executable_workspace.tmpl', {'company': False}))
        self.script.chmod(0o755)

    def render(self, path, data):
        config = self.tmp/'chezmoi.json'
        config.write_text(json.dumps({'data': data}))
        return subprocess.run(['chezmoi', '--config', config, '--source', ROOT/'home', 'execute-template',
            '--file', ROOT/path], capture_output=True, text=True, check=True, env=self.env).stdout

    def run_ws(self, *args, okay=True, **env):
        result = subprocess.run([self.script, *args], capture_output=True, text=True,
                                env=dict(self.env, **env))
        self.assertEqual(result.returncode == 0, okay, result.stdout + result.stderr)
        return result.stdout

    def git(self, *args, cwd=None):
        subprocess.run(['git', *GIT_ID, *args], cwd=cwd, check=True, capture_output=True, env=self.env)

    def repo(self, rel, remote=True):
        path = self.ws/rel
        path.mkdir(parents=True)
        self.git('init', '-q', '-b', 'main', cwd=path)
        (path/'f').write_text('x\n')
        self.git('add', '.', cwd=path)
        self.git('commit', '-qm', 'init', cwd=path)
        if remote:
            bare = self.tmp/'remotes'/(path.name + '.git')
            self.git('clone', '-q', '--bare', path, bare)
            self.git('remote', 'add', 'origin', bare, cwd=path)
            self.git('fetch', '-q', 'origin', cwd=path)
        return path

    def test_init_creates_owner_layout(self):
        self.run_ws('init')
        self.assertTrue((self.ws/'personal/projects').is_dir())
        self.assertTrue((self.ws/'scratch').is_dir())
        self.assertFalse((self.ws/'company').exists())
        self.run_ws('init', WORKSPACE_COMPANY='1')
        self.assertTrue((self.ws/'company/worktrees').is_dir())

    def test_doctor_flags_layout_and_unsynced_repos(self):
        self.run_ws('init')
        self.repo('personal/projects/good')
        self.assertIn('0 warning(s)', self.run_ws('doctor'))
        self.repo('personal/projects/local-only', remote=False)
        (self.ws/'personal/projects/group/inner').mkdir(parents=True)
        (self.ws/'tmp').mkdir()
        (self.ws/'personal/products').mkdir()
        out = self.run_ws('doctor', okay=False)
        self.assertIn('personal/projects/local-only  no origin remote', out)
        self.assertIn('commit(s) not on any remote', out)
        self.assertIn('personal/projects/group  not a git repo', out)
        self.assertIn('tmp  unexpected top-level', out)
        self.assertIn('personal/products  unexpected category', out)

    def test_list_and_clone_round_trip(self):
        self.run_ws('init')
        self.repo('personal/projects/app')
        self.repo('personal/oss/lib')
        listing = self.run_ws('list')
        self.assertEqual(sorted(line.split('\t')[0] for line in listing.splitlines()),
                         ['personal/oss/lib', 'personal/projects/app'])
        manifest = self.tmp/'repos.tsv'
        manifest.write_text('# comment\n' + listing + 'company/projects/secret\t/nonexistent\n')
        other = self.tmp/'other'
        self.run_ws('init', WORKSPACE_ROOT=str(other))
        out = self.run_ws('clone', manifest, WORKSPACE_ROOT=str(other))
        self.assertIn('2 cloned, 1 already present or skipped', out)
        self.assertTrue((other/'personal/projects/app/f').is_file())
        self.assertFalse((other/'company').exists())
        self.assertIn('0 cloned, 3', self.run_ws('clone', manifest, WORKSPACE_ROOT=str(other)))

    def test_clone_rejects_paths_outside_layout(self):
        self.run_ws('init')
        manifest = self.tmp/'bad.tsv'
        manifest.write_text('personal/products/x\t/nonexistent\n')
        self.run_ws('clone', manifest, okay=False)

    def test_unmounted_root_creates_nothing(self):
        link = self.tmp/'link'
        link.symlink_to(self.tmp/'missing-volume/workspace')
        self.run_ws('init', okay=False, WORKSPACE_ROOT=str(link))
        self.assertFalse((self.tmp/'missing-volume').exists())

    def test_symlink_only_managed_when_root_is_set(self):
        plain = self.render('home/.chezmoiignore.tmpl', {})
        self.assertIn('\nworkspace\n', plain)
        moved = self.render('home/.chezmoiignore.tmpl', {'workspace_root': '/Volumes/X/workspace'})
        self.assertNotIn('\nworkspace\n', moved)
        self.assertEqual(self.render('home/symlink_workspace.tmpl', {'workspace_root': '/Volumes/X/workspace'}).strip(),
                         '/Volumes/X/workspace')


if __name__ == '__main__':
    unittest.main()
