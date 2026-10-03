"""Recovery behavior using only synthetic source/target state, never host settings."""
import types
from unittest.mock import patch

from test_updates import Fixture, UPDATE


class RecoveryTests(Fixture):
    def candidate(self):
        self.git('switch', '-c', 'candidate')
        (self.repo/'home/dot_probe').write_text('after\n')
        self.commit()
        candidate = self.git('rev-parse', 'HEAD')
        self.git('switch', 'main')
        return candidate

    def test_forward_revert_restores_target_without_rewinding_source(self):
        self.plan_apply()
        base = self.git('rev-parse', 'HEAD')
        candidate = self.candidate()
        self.cli('plan', '--ref', candidate, '--plan', self.root/'upgrade.json')
        self.cli('apply', '--plan', self.root/'upgrade.json', '--yes')
        self.assertEqual((self.target/'.probe').read_text(), 'after\n')
        self.git('revert', '--no-edit', candidate)
        self.plan_apply('revert.json')
        self.cli('verify')
        self.assertNotEqual(self.git('rev-parse', 'HEAD'), base)
        self.assertEqual((self.target/'.probe').read_text(), 'before\n')

    def test_partial_failure_is_reported_and_manual_restore_can_replan(self):
        self.plan_apply()
        backup = (self.target/'.probe').read_bytes()
        candidate = self.candidate()
        plan = self.root/'upgrade.json'
        self.cli('plan', '--ref', candidate, '--plan', plan)
        args = types.SimpleNamespace(repo=self.repo, target=self.target, config=self.config,
                                     profile='core', component='config', state=self.root/'state.boltdb',
                                     cache=self.root/'cache', yes=True, plan=plan)
        update = UPDATE.Updates(args)
        original = update.cm

        def fail_after_write(source, command, *values):
            if command == 'apply':
                (self.target/'.probe').write_text('partial fixture write\n')
                raise UPDATE.Stop('Injected apply failure')
            return original(source, command, *values)

        with patch.object(update, 'cm', side_effect=fail_after_write):
            with self.assertRaisesRegex(UPDATE.Stop, 'No automatic rollback'):
                update.apply()
        self.assertEqual(self.git('rev-parse', 'HEAD'), candidate)
        self.assertEqual((self.target/'.probe').read_text(), 'partial fixture write\n')
        result = self.cli('plan', okay=False)
        self.assertIn('local changes', result.stderr)
        # Recovery is explicit and confined to this synthetic target backup.
        (self.target/'.probe').write_bytes(backup)
        self.plan_apply('recovered.json')
        self.cli('verify')
        self.assertEqual((self.target/'.probe').read_text(), 'after\n')


class ProfileRecoveryTests(Fixture):
    def test_full_to_core_preserves_previously_written_optional_files(self):
        (self.repo/'home/dot_optional').write_text('optional fixture\n')
        (self.repo/'home/.chezmoiignore.tmpl').write_text('{{ if ne .profile "full" }}.optional{{ end }}\n')
        self.commit()
        self.plan_apply('full.json', '--profile', 'full')
        self.assertTrue((self.target/'.optional').exists())
        self.plan_apply('core.json')
        self.cli('verify')
        self.assertEqual((self.target/'.optional').read_text(), 'optional fixture\n')
