"""Exercise uploads through a local SSH stand-in; never use the real clipboard or network."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'home/bin/executable_clip-to-remote'


class ClipToRemote(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root/'bin'
        self.remote = self.root/'remote'
        self.clipboard = self.root/'clipboard'
        self.bin.mkdir()
        self.remote.mkdir()
        self.clipboard.write_text('previous clipboard')
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                        HOME=str(self.root), CLIP_REMOTE_HOST='fixture-host',
                        FIXTURE_REMOTE=str(self.remote), FIXTURE_CLIPBOARD=str(self.clipboard))
        self.stub('ssh', '''
            import os, subprocess, sys
            env = dict(os.environ, HOME=os.environ['FIXTURE_REMOTE'])
            sys.exit(subprocess.run(['/bin/sh', '-c', sys.argv[-1]],
                                    cwd=env['HOME'], env=env).returncode)
        ''')
        # Keep foreground detection off; notification output is discarded.
        self.stub('osascript', 'print("false")\n')
        self.stub('pbcopy', '''
            import os, pathlib, sys
            pathlib.Path(os.environ['FIXTURE_CLIPBOARD']).write_bytes(sys.stdin.buffer.read())
        ''')

    def stub(self, name, code):
        path = self.bin/name
        path.write_text('#!'+sys.executable+'\n'+textwrap.dedent(code))
        path.chmod(0o755)

    def upload(self, path):
        return subprocess.run(['bash', str(SCRIPT), str(path)], env=self.env,
                              cwd=self.root, capture_output=True, text=True, timeout=10)

    def image(self, name='image.png'):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'image fixture\x00\xff')
        return path

    def assert_uploaded(self, source, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        uploaded = Path(result.stdout.strip())
        self.assertEqual(uploaded.parent, self.remote/'.cache/clip')
        self.assertEqual(uploaded.suffix, '.png')
        self.assertEqual(uploaded.read_bytes(), source.read_bytes())
        self.assertEqual(self.clipboard.read_text(), str(uploaded))

    def assert_failed(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertEqual(self.clipboard.read_text(), 'previous clipboard')

    def test_success_copies_uploaded_path_and_preserves_file_bytes(self):
        source = self.image('image with spaces.PNG')
        self.assert_uploaded(source, self.upload(source))

    def test_extensionless_file_in_dotted_directory_uses_png(self):
        source = self.image('folder.with.dots/image')
        self.assert_uploaded(source, self.upload(source))

    def test_extension_cannot_execute_a_remote_shell_command(self):
        source = self.image('image.$(touch injected)')
        result = self.upload(source)
        self.assertFalse((self.remote/'injected').exists(), 'Filename was executed by the remote shell')
        self.assert_failed(result)

    def test_remote_directory_failure_does_not_publish_a_path(self):
        (self.remote/'.cache').mkdir()
        (self.remote/'.cache/clip').write_text('existing file')
        self.assert_failed(self.upload(self.image()))

    def test_remote_write_failure_does_not_publish_a_path(self):
        self.stub('cat', '''
            import sys
            sys.stdout.buffer.write(sys.stdin.buffer.read()[:2])
            sys.exit(1)
        ''')
        self.assert_failed(self.upload(self.image()))

    def test_remote_cleanup_failure_warns_but_keeps_successful_upload(self):
        self.stub('find', 'raise SystemExit(1)\n')
        source = self.image()
        result = self.upload(source)
        self.assert_uploaded(source, result)
        self.assertIn('upload succeeded; old remote files could not be cleaned up', result.stderr)


if __name__ == '__main__':
    unittest.main()
