"""bin/claude-rc against a private tmux server and a fake `claude`; never starts the real one."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('tmux'), 'tmux not installed')
class ClaudeRcTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='claude-rc-test-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        fake_bin = self.tmp/'bin'
        fake_bin.mkdir()
        self.calls = self.tmp/'calls'
        claude = fake_bin/'claude'
        claude.write_text(f'#!/bin/sh\necho "$PWD $*" >> {self.calls}\nexec sleep 60\n')
        claude.chmod(0o755)
        (self.tmp/'home/workspace').mkdir(parents=True)
        (self.tmp/'home/notes').mkdir()
        # A short TMUX_TMPDIR keeps the socket path under the macOS length limit.
        self.sockdir = Path(tempfile.mkdtemp(prefix='rc', dir='/tmp'))
        self.addCleanup(shutil.rmtree, self.sockdir, True)
        self.env = dict(os.environ, HOME=str(self.tmp/'home'), TMUX_TMPDIR=str(self.sockdir),
                        PATH=f'{fake_bin}:{os.environ["PATH"]}', CLAUDE_RC_SESSION='rc-test')
        self.env.pop('TMUX', None)
        self.addCleanup(subprocess.run, ['tmux', 'kill-server'], env=self.env, capture_output=True)
        self.script = self.tmp/'claude-rc'
        self.script.write_text(self.render('home/bin/executable_claude-rc.tmpl', {'claude_rc_dirs': ['workspace', 'notes', 'missing']}))
        self.script.chmod(0o755)

    def render(self, path, data):
        config = self.tmp/'chezmoi.json'
        config.write_text(json.dumps({'data': data}))
        return subprocess.run(['chezmoi', '--config', config, '--source', ROOT/'home', 'execute-template',
            '--file', ROOT/path], capture_output=True, text=True, check=True, env=self.env).stdout

    def rc(self, *args):
        result = subprocess.run([self.script, *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def wait_calls(self, n):
        for _ in range(50):
            if self.calls.exists() and len(self.calls.read_text().splitlines()) >= n:
                return self.calls.read_text().splitlines()
            time.sleep(0.1)
        self.fail(f'expected {n} claude starts, got {self.calls.read_text() if self.calls.exists() else "none"}')

    def test_starts_one_window_per_dir_and_is_idempotent(self):
        out = self.rc()
        self.assertIn('started workspace', out)
        self.assertIn('started notes', out)
        self.assertIn('skip', out)
        calls = self.wait_calls(2)
        self.assertTrue(all(c.endswith('remote-control -c') for c in calls), calls)
        self.assertNotIn('started', self.rc())
        status = self.rc('status')
        self.assertIn('workspace', status)
        self.assertIn('notes', status)

    def test_restart_respawns_windows(self):
        self.rc()
        self.wait_calls(2)
        self.assertIn('restarted', self.rc('restart'))
        self.wait_calls(4)

    @unittest.skipUnless(sys.platform == 'darwin', 'claude-rc is macOS-only')
    def test_ignored_unless_opted_in(self):
        self.assertIn('\nbin/claude-rc\n', self.render('home/.chezmoiignore.tmpl', {}))
        self.assertNotIn('\nbin/claude-rc\n', self.render('home/.chezmoiignore.tmpl', {'claude_rc': True}))


if __name__ == '__main__':
    unittest.main()
