"""sshtmp keeps temporary SSH hosts with expiry dates in their own file."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'home/bin/executable_sshtmp'


class SshTmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / 'config.d/temp.conf'

    def run_tool(self, *args, today='2026-10-13', okay=True):
        env = dict(os.environ, SSHTMP_FILE=str(self.file), SSHTMP_TODAY=today, HOME=self.tmp.name)
        result = subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, okay, result.stdout + result.stderr)
        return result

    def test_add_writes_a_parseable_isolated_host(self):
        self.run_tool('add', 'lab', 'root@192.0.2.5:2222', '--days', '3', '--jump', 'bastion')
        text = self.file.read_text()
        self.assertIn('# sshtmp alias=lab expires=2026-10-16', text)
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)
        resolved = subprocess.run(['ssh', '-G', '-F', self.file, 'lab'], capture_output=True, text=True,
                                  env=dict(os.environ, HOME=self.tmp.name)).stdout
        for line in ('hostname 192.0.2.5', 'user root', 'port 2222', 'proxyjump bastion',
                     'stricthostkeychecking accept-new'):
            self.assertIn(line, resolved)
        self.assertIn('known_hosts.temp', resolved)

    def test_expired_hosts_are_pruned_and_replace_keeps_one_entry(self):
        self.run_tool('add', 'old', 'old.example', '--days', '1')
        self.run_tool('add', 'keep', 'keep.example', '--days', '30')
        self.run_tool('add', 'keep', 'new.example', '--days', '30')
        listing = self.run_tool('list', today='2026-10-20')
        self.assertNotIn('old', listing.stdout)
        self.assertIn('expired: old', listing.stderr)
        text = self.file.read_text()
        self.assertEqual(text.count('Host keep'), 1)
        self.assertIn('HostName new.example', text)
        self.assertNotIn('old.example', text)

    def test_extend_rm_and_bad_input(self):
        self.run_tool('add', 'box', 'box.example')
        self.assertIn('2026-11-12', self.run_tool('extend', 'box', '--days', '30').stdout)
        self.assertIn('expires=2026-11-12', self.file.read_text())
        self.run_tool('rm', 'box')
        self.assertNotIn('Host box', self.file.read_text())
        self.run_tool('rm', 'box', okay=False)
        self.run_tool('add', 'bad alias', 'x.example', okay=False)
        self.run_tool('add', 'ok', 'user@', okay=False)
        self.run_tool('add', 'ok', 'x.example', '--days', '0', okay=False)


if __name__ == '__main__':
    unittest.main()
