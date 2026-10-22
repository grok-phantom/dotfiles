"""Syntax checks render synthetic templates without executing their shell bodies."""
import os
from pathlib import Path
import tempfile
import unittest

from run_tests import check_shell_files


class ShellSyntaxTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root/'home').mkdir()
        (self.root/'.chezmoiroot').write_text('home\n')
        self.env = dict(os.environ)

    def write(self, name, text):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return name

    def test_discovers_new_tools_and_shell_configs_without_executing_them(self):
        marker = self.root/'should-not-exist'
        names = [self.write('home/bin/executable_new-tool', f'#!/usr/bin/env bash\ntouch "{marker}"\n'),
                 self.write('home/private_dot_config/zsh/conf.d/new.zsh', 'items=(one two)\n'),
                 self.write('scripts/other', '#!/bin/sh\necho unused\n')]
        self.assertEqual(check_shell_files(self.root, names, self.env), (3, 3))
        self.assertFalse(marker.exists())

    def test_bad_plain_script_reports_its_path(self):
        name = self.write('home/bin/executable_bad', '#!/usr/bin/env bash\nif then\n')
        with self.assertRaisesRegex(RuntimeError, name):
            check_shell_files(self.root, [name], self.env)

    def test_checks_rendered_platform_and_profile_branches(self):
        name = self.write('home/bin/executable_variant.tmpl', '''#!/usr/bin/env bash
{{ if and (eq .chezmoi.os "linux") (eq .profile "full") }}
if then
{{ else }}
echo valid
{{ end }}
''')
        with self.assertRaisesRegex(RuntimeError, r'linux/full'):
            check_shell_files(self.root, [name], self.env)

    def test_renders_shared_helpers_and_zsh_templates(self):
        self.write('home/.chezmoitemplates/fragment', 'items=(one two)\n')
        name = self.write('home/dot_zshrc.tmpl', '{{ includeTemplate "fragment" . }}')
        completion = self.write('home/private_dot_config/zsh/completions/_probe.tmpl', '{{ completion "zsh" }}')
        self.assertEqual(check_shell_files(self.root, [name, completion], self.env), (2, 8))


if __name__ == '__main__':
    unittest.main()
