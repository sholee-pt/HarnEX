"""Preserve owned retrieval state across the Harness-Codex command rename."""
import hashlib
import os
import stat
import unittest
from unittest import mock

from harness_cli import graft, graft_setup, main, project, workspace_context
import test_cli_graft as fixtures

REPO = fixtures.REPO
LEGACY_SKILL = graft.SKILL.replace('harnex graft query', 'harness-codex graft query').encode()


class GraftCompatibilityTests(unittest.TestCase):
    setUp = fixtures.GraftTests.setUp
    run_command = fixtures.GraftTests.run_command
    enable = fixtures.GraftTests.enable

    def previous(self, *, enabled=True, unscoped=False):
        self.assertEqual(hashlib.sha256(LEGACY_SKILL).hexdigest(), graft.LEGACY_SKILL_HASH)
        folder = graft.legacy_storage(self.root) if unscoped else graft.storage(self.root)
        path = folder / 'settings.json'
        state = {'owner': graft.OWNER, 'enabled': enabled, 'package': '/old/package', 'node': '/old/node',
                 'skillHash': graft.LEGACY_SKILL_HASH, 'skillOwned': enabled, 'disabledByUser': not enabled,
                 'externalSources': {'library': str(self.root.parent / 'external')}, 'revision': 'previous'}
        graft._save(path, state)
        skill = self.root / graft.SKILL_PATH
        if enabled:
            skill.parent.mkdir(parents=True)
            skill.write_bytes(LEGACY_SKILL)
        return path, skill, state

    def test_status_is_read_only_and_enable_migrates_owned_skill_and_preserves_state(self):
        path, skill, previous = self.previous()
        graph = path.parent / 'graph/retained.txt'
        graph.parent.mkdir()
        graph.write_bytes(b'keep graph')
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (path, skill, graph)}
        result = self.run_command('status')
        self.assertTrue(result['skillUpgradeRequired'])
        self.assertFalse(result['skillInstalled'])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})
        mode = stat.S_IMODE(skill.stat().st_mode)
        self.enable()
        state = graft._load(path)
        self.assertEqual(skill.read_bytes(), graft.SKILL.encode())
        self.assertEqual(stat.S_IMODE(skill.stat().st_mode), mode)
        self.assertEqual(state['skillHash'], graft.SKILL_HASH)
        self.assertEqual(state['externalSources'], previous['externalSources'])
        self.assertEqual(state['revision'], previous['revision'])
        self.assertEqual((graph.read_bytes(), graph.stat().st_mtime_ns), before[graph])
        self.assertFalse(self.run_command('status')['skillUpgradeRequired'])
        after = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (path, skill)]
        self.enable()
        self.assertEqual(after, [(p.read_bytes(), p.stat().st_mtime_ns) for p in (path, skill)])

    def test_automatic_migrates_enabled_legacy_setup(self):
        path, skill, previous = self.previous()
        with mock.patch.object(graft.shutil, 'which', return_value='/old/node'), mock.patch.object(graft, '_invoke', return_value={}), \
             mock.patch.object(graft_setup, 'prepare', side_effect=AssertionError('Use this host receipt')):
            self.assertTrue(graft.automatic(self.root, REPO)['enabled'])
        self.assertEqual(skill.read_bytes(), graft.SKILL.encode())
        self.assertEqual(graft._load(path)['externalSources'], previous['externalSources'])

    def test_opt_out_is_preserved_without_migration_or_network(self):
        for unscoped in (False, True):
            with self.subTest(unscoped=unscoped):
                path, skill, previous = self.previous(enabled=False, unscoped=unscoped)
                before = path.read_bytes(), path.stat().st_mtime_ns
                with mock.patch.object(graft, '_invoke', side_effect=AssertionError('Opt-out')), \
                     mock.patch.object(graft_setup, 'prepare', side_effect=AssertionError('Opt-out')):
                    self.assertEqual(graft.automatic(self.root, REPO)['state'], 'disabled')
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
                self.assertFalse(skill.exists())
                path.unlink()
                if not unscoped:
                    path.parent.rmdir()

    def test_unscoped_receipt_migrates_skill_without_importing_host_paths_or_sources(self):
        path, skill, previous = self.previous(unscoped=True)
        before = path.read_bytes(), path.stat().st_mtime_ns
        self.enable()
        current = graft._load(graft.storage(self.root) / 'settings.json')
        self.assertNotIn('externalSources', current)
        self.assertEqual(current['node'], '/node')
        self.assertEqual(current['package'], str(self.root / 'dependency'))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertEqual(skill.read_bytes(), graft.SKILL.encode())

    def test_new_host_uses_portable_legacy_skill_receipt_only(self):
        path, skill, previous = self.previous()
        with mock.patch.object(workspace_context, 'probe', return_value='not-applicable'):
            workspace_context.refresh(self.root, ['codex'])
        workspace_context.record_retrieval(self.root, graft.LEGACY_SKILL_HASH)
        before = path.read_bytes()
        with mock.patch.object(graft, 'host_key', return_value='new-host'):
            self.enable()
            current = graft._load(graft.storage(self.root) / 'settings.json')
            self.assertNotIn('externalSources', current)
            self.assertEqual(current['node'], '/node')
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(workspace_context.retrieval_owned(self.root, graft.SKILL_HASH))

    def test_modified_legacy_skill_is_preserved(self):
        path, skill, previous = self.previous()
        skill.write_bytes(LEGACY_SKILL + b'User instruction.\n')
        before = path.read_bytes(), skill.read_bytes()
        with self.assertRaisesRegex(ValueError, 'user-owned or modified'):
            self.enable()
        self.assertEqual((path.read_bytes(), skill.read_bytes()), before)

    def test_unknown_receipt_is_reported_with_path_and_preserved(self):
        path, skill, previous = self.previous()
        for changes, reason in (({'skillHash': 'f' * 64}, 'Unsupported skill hash'), ({'owner': 'user'}, 'Invalid owner or fields')):
            with self.subTest(reason=reason):
                graft._save(path, {**previous, **changes})
                before = path.read_bytes(), skill.read_bytes()
                with self.assertRaisesRegex(graft.RetrievalSettingsError, reason) as error:
                    self.enable()
                self.assertIn(str(path), str(error.exception))
                self.assertEqual((path.read_bytes(), skill.read_bytes()), before)

    def test_unowned_legacy_skill_requires_explicit_adoption(self):
        skill = self.root / graft.SKILL_PATH
        skill.parent.mkdir(parents=True)
        skill.write_bytes(LEGACY_SKILL)
        with self.assertRaisesRegex(ValueError, 'user-owned or modified'):
            self.enable()
        self.assertEqual(skill.read_bytes(), LEGACY_SKILL)
        with mock.patch.object(graft.shutil, 'which', return_value='/node'), mock.patch.object(graft, '_invoke', return_value={}):
            self.run_command('enable', '--adopt-skill', '--package', str(self.root / 'dependency'))
        self.assertEqual(skill.read_bytes(), graft.SKILL.encode())

    def test_disable_during_legacy_build_wins(self):
        path, skill, previous = self.previous()
        def build(*args, **kwargs):
            self.run_command('disable')
            return {}
        with mock.patch.object(graft.shutil, 'which', return_value='/node'), mock.patch.object(graft, '_invoke', side_effect=build):
            result = self.run_command('enable', '--package', str(self.root / 'dependency'))
        self.assertEqual(result['state'], 'superseded')
        self.assertFalse(skill.exists())
        self.assertTrue(graft._load(path)['disabledByUser'])

    def test_failed_settings_commit_restores_old_skill_bytes_permissions_and_mtime(self):
        path, skill, previous = self.previous()
        before = skill.read_bytes(), stat.S_IMODE(skill.stat().st_mode), skill.stat().st_mtime_ns
        save = graft._save
        def fail(destination, value):
            if destination == path and value['skillHash'] == graft.SKILL_HASH:
                raise OSError('settings-commit')
            return save(destination, value)
        with mock.patch.object(graft, '_save', side_effect=fail), self.assertRaisesRegex(OSError, 'settings-commit'):
            self.enable()
        self.assertEqual((skill.read_bytes(), stat.S_IMODE(skill.stat().st_mode), skill.stat().st_mtime_ns), before)
        self.assertEqual(graft._load(path), previous)
        self.assertTrue(self.enable()['enabled'])

    def test_failed_commit_preserves_concurrent_skill_edit(self):
        path, skill, previous = self.previous()
        save = graft._save
        def fail(destination, value):
            if destination == path and value['skillHash'] == graft.SKILL_HASH:
                skill.write_bytes(b'User edit during commit')
                raise OSError('settings-commit')
            return save(destination, value)
        with mock.patch.object(graft, '_save', side_effect=fail), self.assertRaisesRegex(OSError, 'settings-commit'):
            self.enable()
        self.assertEqual(skill.read_bytes(), b'User edit during commit')
        self.assertEqual(graft._load(path), previous)

    def test_concurrent_edit_before_replacement_is_preserved(self):
        path, skill, previous = self.previous()
        chmod = os.chmod
        def change(destination, mode):
            skill.write_bytes(b'Concurrent user edit')
            return chmod(destination, mode)
        with mock.patch.object(graft.os, 'chmod', side_effect=change), self.assertRaisesRegex(ValueError, 'concurrent edit'):
            self.enable()
        self.assertEqual(skill.read_bytes(), b'Concurrent user edit')
        self.assertEqual(graft._load(path), previous)

    def test_interrupted_migration_can_finish_without_replacing_current_skill(self):
        path, skill, previous = self.previous()
        skill.write_bytes(graft.SKILL.encode())
        before = skill.stat().st_mtime_ns
        self.enable()
        self.assertEqual(skill.stat().st_mtime_ns, before)
        self.assertEqual(graft._load(path)['skillHash'], graft.SKILL_HASH)

    def test_disable_removes_only_unchanged_owned_legacy_skill(self):
        path, skill, previous = self.previous()
        self.run_command('disable')
        self.assertFalse(skill.exists())
        self.assertTrue(graft._load(path)['disabledByUser'])

    def test_invalid_settings_do_not_recommend_unchanged_retry(self):
        path, skill, previous = self.previous()
        graft._save(path, {**previous, 'skillHash': 'unknown'})
        args = main.build_parser(REPO).parse_args(['init'])
        with mock.patch.object(project.ui, 'report') as report:
            project._configure_retrieval(args, REPO, self.root)
        warnings = '\n'.join(report.call_args.args[0]['warnings'])
        self.assertIn(str(path), warnings)
        self.assertNotIn('Retry with harnex graft enable', warnings)
