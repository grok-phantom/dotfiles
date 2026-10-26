"""ssh-lan-reachable with stand-ins for ifconfig, nc and uname; no real network."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'home/bin/executable_ssh-lan-reachable'

IFCONFIG = '''\
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 192.0.2.23 netmask 0xffffff00 broadcast 192.0.2.255
utun1: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 4064
\tinet 198.18.0.1 netmask 0xffff0000
utun2: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1400
\tinet 198.51.100.250 netmask 0xffffff00
'''


class SshLanReachable(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.calls = self.root/'nc.log'
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                        FIXTURE_IFCONFIG=IFCONFIG, FIXTURE_CALLS=str(self.calls), FIXTURE_NC='0')
        self.stub('uname', 'print("Darwin")\n')
        self.stub('ifconfig', 'import os, sys; sys.stdout.write(os.environ["FIXTURE_IFCONFIG"])\n')
        self.stub('nc', '''
            import os, sys
            with open(os.environ['FIXTURE_CALLS'], 'a') as log:
                log.write(' '.join(sys.argv[1:]) + '\\n')
            sys.exit(int(os.environ['FIXTURE_NC']))
        ''')

    def stub(self, name, code):
        path = self.bin/name
        path.write_text('#!'+sys.executable+'\n'+textwrap.dedent(code))
        path.chmod(0o755)

    def probe(self, *args, **env):
        return subprocess.run(['bash', str(SCRIPT), *args], env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=10).returncode

    def nc_calls(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def test_same_subnet_probes_bound_to_the_physical_interface(self):
        self.assertEqual(self.probe('192.0.2.50', '2222'), 0)
        self.assertEqual(self.nc_calls(), ['-z -G 1 -b en0 192.0.2.50 2222'])

    def test_port_closed_on_the_lan_is_no(self):
        self.assertEqual(self.probe('192.0.2.50', FIXTURE_NC='1'), 1)

    def test_other_subnet_is_no_without_probing_even_if_a_tunnel_covers_it(self):
        # utun2 (a VPN or Surge) sits on 198.51.100.0/24; it must not count as being there.
        self.assertEqual(self.probe('198.51.100.194'), 1)
        self.assertEqual(self.nc_calls(), [])

    def test_bad_arguments_are_usage_errors(self):
        for args in ((), ('host.example',), ('192.0.2.5', 'ssh')):
            self.assertEqual(self.probe(*args), 2)


if __name__ == '__main__':
    unittest.main()
