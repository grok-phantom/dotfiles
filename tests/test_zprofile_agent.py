"""The forwarded-agent link in ~/.zprofile survives one-off SSH commands."""
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZPROFILE = re.sub(r'\{\{/\*.*?\*/\}\}', '', (ROOT / 'home/dot_zprofile.tmpl').read_text())


@unittest.skipUnless(shutil.which('zsh'), 'zsh not installed')
class ForwardedAgentLink(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(dir='/tmp'))  # short path: unix sockets have a length limit
        self.addCleanup(shutil.rmtree, self.home)
        (self.home / '.ssh').mkdir()
        self.link = self.home / '.ssh/agent-forwarded.sock'
        self.script = self.home / 'zprofile'
        self.script.write_text(ZPROFILE)

    def sock(self, name):
        path = self.home / name
        server = socket.socket(socket.AF_UNIX)
        server.bind(str(path))
        self.addCleanup(server.close)
        return path

    def login(self, agent):
        env = {'HOME': str(self.home), 'PATH': os.environ['PATH'], 'SSH_CONNECTION': '192.0.2.1 1 192.0.2.2 22',
               'SSH_AUTH_SOCK': str(agent)}
        subprocess.run(['zsh', '-c', f'source {self.script}'], env=env, stdin=subprocess.DEVNULL, check=True)

    def test_a_command_without_a_terminal_keeps_a_live_link(self):
        live = self.sock('live.sock')
        self.link.symlink_to(live)
        self.login(self.sock('oneoff.sock'))
        self.assertEqual(os.readlink(self.link), str(live))

    def test_a_dead_link_is_replaced(self):
        self.link.symlink_to(self.home / 'gone.sock')
        agent = self.sock('new.sock')
        self.login(agent)
        self.assertEqual(os.readlink(self.link), str(agent))


if __name__ == '__main__':
    unittest.main()
