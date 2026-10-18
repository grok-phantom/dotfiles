"""nori-watch reports nori and proxy problems and only notifies on change; a fake nori and local servers stand in."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'home/bin/executable_nori-watch'
HEALTHY = {'running': True, 'schedule_enabled': True, 'maintenance_required': False, 'recovery_required': False,
           'result': 'unchanged', 'last_attempt': 0, 'last_success': 0}


def serve(test, code):
    """A local server answering every GET/POST with `code`; returns its base URL and the request log."""
    log = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def answer(self):
            length = int(self.headers.get('Content-Length') or 0)
            log.append((self.command, self.path, self.rfile.read(length)))
            self.send_response(code)
            self.send_header('Content-Length', '0')
            self.end_headers()
        do_GET = do_POST = answer

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    test.addCleanup(server.server_close)
    test.addCleanup(server.shutdown)
    return f'http://127.0.0.1:{server.server_port}', log


class NoriWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.status_file = self.dir / 'status.json'
        self.nori = self.dir / 'nori'
        self.nori.write_text('#!/bin/sh\n[ -f "$0.fail" ] && { echo "error: config" >&2; exit 1; }\n'
                             f'cat {self.status_file}\n')
        self.nori.chmod(0o755)
        self.bark, self.notices = serve(self, 200)
        (self.dir / 'bark.url').write_text(self.bark + '/push\n')
        self.direct, _ = serve(self, 200)
        self.proxy, self.proxied = serve(self, 204)
        self.status()

    def status(self, **changes):
        self.status_file.write_text(json.dumps({**HEALTHY, 'last_success': time.time() - 3600, **changes}))

    def run_watch(self, *extra, proxy=None):
        env = dict(os.environ, NORI_WATCH_NORI=str(self.nori), NORI_WATCH_BARK=str(self.dir / 'bark.url'),
                   NORI_WATCH_STATE=str(self.dir / 'state/state.json'), HOME=self.tmp.name)
        for key in ('http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
            env.pop(key, None)  # the GUI proxy agent sets these for the login session; the script must not need them
        args = [sys.executable, str(SCRIPT), '--config', '~/nori.yaml', '--name', 'mac',
                '--probe-url', 'http://probe.invalid/generate_204', '--direct-url', self.direct + '/',
                '--proxy', proxy or self.proxy, *extra]
        return subprocess.run(args, env=env, capture_output=True, text=True)

    def printed(self, **kwargs):
        result = self.run_watch('--print', **kwargs)
        return result.stdout.strip().splitlines()

    def test_healthy_mac_is_ok_and_probe_goes_through_the_proxy(self):
        self.assertEqual(self.printed(), ['ok'])
        self.assertEqual(self.proxied[-1][1], 'http://probe.invalid/generate_204')

    def test_nori_problems_are_reported(self):
        self.status(running=False, schedule_enabled=False, maintenance_required=True, result='fetch',
                    last_success=time.time() - 70 * 3600)
        self.assertEqual(self.printed(), ['last refresh failed: fetch', 'no successful refresh for 70h',
                                          'nori needs maintenance', 'proxy is not running',
                                          'scheduled refresh is off'])
        (self.dir / 'nori.fail').write_text('')
        self.assertEqual(self.printed(), ['nori status failed: error: config'])

    def test_broken_proxy_is_reported_only_while_online(self):
        closed = 'http://127.0.0.1:9'
        self.assertEqual(self.printed(proxy=closed), ['request through the proxy failed: URLError'])
        self.direct = closed
        self.assertEqual(self.printed(proxy=closed), ['ok'])  # offline: no proxy verdict

    def test_only_changes_are_pushed_directly_to_bark(self):
        self.status(running=False)
        self.assertEqual(self.run_watch().returncode, 1)
        self.assertEqual(self.run_watch().returncode, 1)
        self.status()
        self.assertEqual(self.run_watch().returncode, 0)
        titles = [json.loads(body)['title'] for method, path, body in self.notices]
        self.assertEqual(titles, ['mac: 1 nori problem(s)', 'mac: nori all clear'])
        self.assertEqual(self.notices[0][1], '/push')  # sent to Bark itself, not through --proxy
        self.assertEqual(json.loads((self.dir / 'state/state.json').read_text()), [])

    def test_failed_notice_is_retried_next_run(self):
        (self.dir / 'bark.url').write_text('http://127.0.0.1:9/push\n')
        self.status(running=False)
        self.assertEqual(self.run_watch().returncode, 2)
        self.assertFalse((self.dir / 'state/state.json').exists())


if __name__ == '__main__':
    unittest.main()
