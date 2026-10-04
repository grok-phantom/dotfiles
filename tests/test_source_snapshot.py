"""Plan/apply source boundaries with real chezmoi and disposable target homes."""
from pathlib import Path
import types
from unittest.mock import patch

from test_updates import Fixture, ROOT, UPDATE


class SourceSnapshotTests(Fixture):
    def setUp(self):
        super().setUp()
        (self.repo/'.gitignore').write_bytes((ROOT/'.gitignore').read_bytes())
        (self.repo/'home/.chezmoiignore.tmpl').write_bytes((ROOT/'home/.chezmoiignore.tmpl').read_bytes())
        self.commit()

    def ignored_file(self, content='unplanned fixture\n'):
        path = self.repo/'home/dot_unplanned.pyc'
        path.write_text(content)
        self.assertEqual(self.git('check-ignore', 'home/dot_unplanned.pyc'), 'home/dot_unplanned.pyc')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        return path

    def test_ignored_source_is_not_planned_applied_or_verified(self):
        ignored = self.ignored_file()
        plan = self.root/'plan.json'
        preview = self.cli('plan', '--diff', '--plan', plan)
        self.assertNotIn('.unplanned.pyc', preview.stdout)
        self.cli('apply', '--plan', plan, '--yes')
        self.cli('verify')
        self.assertFalse((self.target/'.unplanned.pyc').exists())
        self.assertEqual(ignored.read_text(), 'unplanned fixture\n')
        # An unmanaged target with the same name belongs to the user.
        (self.target/'.unplanned.pyc').write_text('user-owned fixture\n')
        self.cli('status')
        self.cli('verify')
        self.plan_apply('repeat.json')
        self.assertEqual((self.target/'.unplanned.pyc').read_text(), 'user-owned fixture\n')

    def test_ignored_source_added_after_plan_is_not_applied(self):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        ignored = self.ignored_file('added after review\n')
        self.cli('apply', '--plan', plan, '--yes')
        self.cli('verify')
        self.assertFalse((self.target/'.unplanned.pyc').exists())
        self.assertEqual(ignored.read_text(), 'added after review\n')

    def test_tracked_file_matching_ignore_rule_is_still_managed(self):
        self.ignored_file('deliberately committed fixture\n')
        self.git('add', '-f', 'home/dot_unplanned.pyc')
        self.commit()
        plan = self.root/'plan.json'
        preview = self.cli('plan', '--diff', '--plan', plan)
        self.assertIn('.unplanned.pyc', preview.stdout)
        self.cli('apply', '--plan', plan, '--yes')
        self.cli('verify')
        self.assertEqual((self.target/'.unplanned.pyc').read_text(), 'deliberately committed fixture\n')

    def assert_source_change_refused(self, name, *, staged=False):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        source = self.repo/'home'/name
        source.write_text('preserve user source\n')
        if staged:
            self.git('add', 'home/'+name)
        before = self.git('status', '--porcelain')
        for command in [('apply', '--plan', plan, '--yes'), ('verify',)]:
            result = self.cli(*command, okay=False)
            self.assertIn('Dirty source', result.stderr)
        self.assertFalse((self.target/'.probe').exists())
        self.assertEqual(source.read_text(), 'preserve user source\n')
        self.assertEqual(self.git('status', '--porcelain'), before)

    def test_untracked_source_after_plan_is_refused_and_preserved(self):
        self.assert_source_change_refused('dot_untracked')

    def test_unstaged_source_after_plan_is_refused_and_preserved(self):
        self.assert_source_change_refused('dot_probe')

    def test_staged_source_after_plan_is_refused_and_preserved(self):
        self.assert_source_change_refused('dot_probe', staged=True)

    def test_source_head_advance_invalidates_saved_plan(self):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        (self.repo/'home/dot_probe').write_text('new committed source\n')
        self.commit()
        current = self.git('rev-parse', 'HEAD')
        self.cli('apply', '--plan', plan, '--yes', okay=False)
        self.assertEqual(self.git('rev-parse', 'HEAD'), current)
        self.assertFalse((self.target/'.probe').exists())

    def test_moving_candidate_ref_does_not_change_reviewed_commit(self):
        self.git('switch', '-c', 'candidate')
        (self.repo/'home/dot_probe').write_text('reviewed candidate\n')
        self.commit()
        reviewed = self.git('rev-parse', 'HEAD')
        self.git('switch', 'main')
        plan = self.root/'plan.json'
        self.cli('plan', '--ref', 'candidate', '--plan', plan)
        self.git('switch', 'candidate')
        (self.repo/'home/dot_probe').write_text('later unreviewed candidate\n')
        self.commit()
        self.git('switch', 'main')
        self.cli('apply', '--plan', plan, '--yes')
        self.assertEqual(self.git('rev-parse', 'HEAD'), reviewed)
        self.assertEqual((self.target/'.probe').read_text(), 'reviewed candidate\n')

    def test_source_commit_changed_during_validation_stops_before_apply(self):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        args = types.SimpleNamespace(repo=self.repo, target=self.target, config=self.config,
                                     profile='core', component='config', state=self.root/'state.boltdb',
                                     cache=self.root/'cache', yes=True, plan=plan)
        update = UPDATE.Updates(args)
        original = update.cm

        def advance_source_after_diff(source, command, *values):
            result = original(source, command, *values)
            if command == 'diff':
                (self.repo/'home/dot_probe').write_text('concurrent committed source\n')
                self.commit()
            return result

        with patch.object(update, 'cm', side_effect=advance_source_after_diff):
            with self.assertRaisesRegex(UPDATE.Stop, 'Source changed'):
                update.apply()
        self.assertFalse((self.target/'.probe').exists())
        self.assertEqual((self.repo/'home/dot_probe').read_text(), 'concurrent committed source\n')

    def test_late_worktree_change_cannot_replace_validated_apply_source(self):
        plan = self.root/'plan.json'
        self.cli('plan', '--plan', plan)
        args = types.SimpleNamespace(repo=self.repo, target=self.target, config=self.config,
                                     profile='core', component='config', state=self.root/'state.boltdb',
                                     cache=self.root/'cache', yes=True, plan=plan)
        update = UPDATE.Updates(args)
        original = update.cm
        used = {}

        def change_worktree_after_validation(source, command, *values):
            if command == 'apply':
                used['apply'] = Path(source)
                (self.repo/'home/dot_probe').write_text('late user edit\n')
                (self.repo/'home/dot_unplanned.pyc').write_text('late ignored fixture\n')
            elif command == 'verify':
                used['verify'] = Path(source)
            return original(source, command, *values)

        with patch.object(update, 'cm', side_effect=change_worktree_after_validation):
            update.apply()
        self.assertEqual((self.target/'.probe').read_text(), 'before\n')
        self.assertFalse((self.target/'.unplanned.pyc').exists())
        self.assertEqual((self.repo/'home/dot_probe').read_text(), 'late user edit\n')
        self.assertEqual(used['apply'], used['verify'])
        self.assertNotEqual(used['apply'], self.repo)
        self.assertFalse(used['apply'].exists(), 'Disposable source export was not cleaned')
        self.assertFalse((self.root/'unexpected').exists())
