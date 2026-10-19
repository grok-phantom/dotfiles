"""bin/claude-memory-link in temporary homes; no iCloud or real ~/.claude involved."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'home/bin/executable_claude-memory-link'


class ClaudeMemoryLinkTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='claude-memory-test-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.home = self.tmp/'home'
        self.ws = self.tmp/'volume/workspace'
        self.projects = self.home/'.claude/projects'
        self.shared = self.tmp/'icloud/claude-memory'
        self.shared.parent.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.home), WORKSPACE_ROOT=str(self.home/'workspace'),
            CLAUDE_PROJECTS_DIR=str(self.projects), CLAUDE_MEMORY_SHARED=str(self.shared),
            CHEZMOI_REPO=str(self.tmp/'no-chezmoi'))
        self.ws.mkdir(parents=True)
        self.home.mkdir()
        # ~/workspace is a symlink, as on a Mac that keeps it on an external disk.
        (self.home/'workspace').symlink_to(self.ws)

    def run_link(self, *args, okay=True):
        result = subprocess.run(['bash', SCRIPT, *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode == 0, okay, result.stdout + result.stderr)
        return result.stdout

    def repo(self, rel):
        path = self.ws/rel
        (path/'.git').mkdir(parents=True)
        return path

    def memory_dir(self, repo):
        return self.projects/re.sub('[^A-Za-z0-9]', '-', str(repo.resolve()))/'memory'

    def test_links_by_resolved_path_and_is_idempotent(self):
        repo = self.repo('personal/projects/app')
        self.assertIn('1 linked', self.run_link())
        memory = self.memory_dir(repo)
        self.assertEqual(os.readlink(memory), str(self.shared/'app'))
        self.assertIn('0 linked, 1 already linked', self.run_link())

    def test_moves_local_notes_into_empty_shared_folder(self):
        repo = self.repo('personal/projects/app')
        memory = self.memory_dir(repo)
        memory.mkdir(parents=True)
        (memory/'MEMORY.md').write_text('- note\n')
        self.run_link()
        self.assertTrue(memory.is_symlink())
        self.assertEqual((self.shared/'app/MEMORY.md').read_text(), '- note\n')
        self.assertTrue(list((self.home/'.claude/backups').glob('memory-before-icloud-app-*.tgz')))

    def test_both_sides_with_notes_are_left_alone(self):
        repo = self.repo('personal/projects/app')
        memory = self.memory_dir(repo)
        memory.mkdir(parents=True)
        (memory/'a.md').write_text('local\n')
        (self.shared/'app').mkdir(parents=True)
        (self.shared/'app/b.md').write_text('shared\n')
        self.assertIn('merge them by hand', self.run_link(okay=False))
        self.assertFalse(memory.is_symlink())

    def test_company_repos_and_dry_run(self):
        self.repo('company/projects/work')
        repo = self.repo('personal/oss/lib')
        out = self.run_link('-n')
        self.assertIn('would: ln -s', out)
        self.assertNotIn('company', out)
        self.assertFalse(self.memory_dir(repo).exists())

    def test_name_collision_is_skipped(self):
        self.repo('personal/projects/dup')
        self.repo('personal/oss/dup')
        self.assertIn('already uses the name dup', self.run_link(okay=False))

    def test_missing_icloud_fails(self):
        self.env['CLAUDE_MEMORY_SHARED'] = str(self.tmp/'nowhere/claude-memory')
        self.run_link(okay=False)

    def test_ignored_off_macos_or_on_ephemeral(self):
        def ignore(data):
            config = self.tmp/'chezmoi.json'
            config.write_text(json.dumps({'data': data}))
            return subprocess.run(['chezmoi', '--config', config, '--source', ROOT/'home', 'execute-template',
                '--file', ROOT/'home/.chezmoiignore.tmpl'], capture_output=True, text=True, check=True).stdout
        self.assertIn('\n.claude/CLAUDE.md\n', ignore({'ephemeral': True}))


if __name__ == '__main__':
    unittest.main()
