"""Regression checks for instruction selection and managed path preflight."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_harness_tools import harness_apply, harness_state, inventory, minimal_plan, validate_harness
from harness_cli import lifecycle

REPO = Path(__file__).resolve().parents[1]


class InstructionSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / 'project'
        self.root.mkdir()
        self.home = self.base / 'codex-home'
        self.home.mkdir()
        patch = mock.patch.dict(os.environ, {'CODEX_HOME': str(self.home)})
        patch.start()
        self.addCleanup(patch.stop)

    def configure(self, folder, names):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'config.toml').write_text('project_doc_fallback_filenames = ' + json.dumps(names) + '\n', encoding='utf-8')

    def test_global_fallback_preserves_user_guidance_through_apply_repeat_and_remove(self):
        self.configure(self.home, ['TEAM_GUIDE.md'])
        path = self.root / 'TEAM_GUIDE.md'
        original = b'# User policy\r\nKeep the original instructions.'
        path.write_bytes(original)
        report = inventory.build_inventory(self.root, 100)
        self.assertEqual(report['existingActiveRootInstruction'], path.name)
        self.assertEqual(report['plannedRootInstruction'], path.name)
        self.assertEqual(report['instructionSelectionErrors'], [])
        plan = minimal_plan(self.root)
        harness_apply.apply_application(harness_apply.build_application(self.root, plan))
        self.assertFalse((self.root / 'AGENTS.md').exists())
        self.assertEqual(harness_state.instruction_user_content(path.read_bytes()), original)
        self.assertTrue(validate_harness.Validator(self.root).run()['valid'])
        self.assertEqual(harness_apply.apply_application(harness_apply.build_application(self.root, plan))['writes'], 0)
        lifecycle.remove_project(self.root, source_root=REPO, dry_run=False)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.root / 'AGENTS.md').exists())

    def test_default_home_and_project_override_including_empty_list(self):
        default_home = self.home / '.codex'
        self.configure(default_home, ['GLOBAL.md'])
        (self.root / 'GLOBAL.md').write_text('Global fallback policy')
        with mock.patch.dict(os.environ, {'CODEX_HOME': ''}), mock.patch.object(Path, 'home', return_value=self.home):
            self.assertEqual(harness_state.active_instruction_relative(self.root), 'GLOBAL.md')
            self.configure(self.root / '.codex', ['LOCAL.md'])
            (self.root / 'LOCAL.md').write_text('Local fallback policy')
            self.assertEqual(harness_state.active_instruction_relative(self.root), 'LOCAL.md')
            self.configure(self.root / '.codex', [])
            self.assertEqual(harness_state.active_instruction_relative(self.root), 'AGENTS.md')

    def test_nested_project_inherits_nearest_repository_config(self):
        self.configure(self.home, ['GLOBAL.md'])
        (self.root / '.git').mkdir()
        self.configure(self.root / '.codex', ['INHERITED.md'])
        nested = self.root / 'src/component'
        nested.mkdir(parents=True)
        (nested / 'INHERITED.md').write_text('Inherited policy')
        self.assertEqual(harness_state.active_instruction_relative(nested), 'INHERITED.md')
        self.configure(nested / '.codex', ['LOCAL.md'])
        (nested / 'LOCAL.md').write_text('Local policy')
        self.assertEqual(harness_state.active_instruction_relative(nested), 'LOCAL.md')

    def test_invalid_global_config_and_nonregular_config_fail_before_writes(self):
        path = self.home / 'config.toml'
        for text in ('project_doc_fallback_filenames = [', 'project_doc_fallback_filenames = ["../escape"]',
                     'project_doc_fallback_filenames = ["guide."]', 'x = "' + 'x' * harness_state.PROJECT_CONFIG_MAX_BYTES + '"'):
            with self.subTest(text=text[:70]):
                path.write_text(text, encoding='utf-8')
                report = inventory.build_inventory(self.root, 100)
                self.assertIsNone(report['plannedRootInstruction'])
                self.assertTrue(report['instructionSelectionErrors'])
                with self.assertRaises(ValueError):
                    harness_apply.build_application(self.root, minimal_plan(self.root))
                self.assertFalse((self.root / '.harness').exists())
                self.assertFalse((self.root / 'AGENTS.md').exists())
        path.unlink()
        path.mkdir()
        with self.assertRaisesRegex(ValueError, 'regular file'):
            harness_state.active_instruction_relative(self.root)

    def test_changed_global_fallback_after_plan_prevents_apply(self):
        plan = minimal_plan(self.root)
        application = harness_apply.build_application(self.root, plan)
        self.configure(self.home, ['TEAM_GUIDE.md'])
        (self.root / 'TEAM_GUIDE.md').write_text('Newly selected user policy')
        with self.assertRaisesRegex(ValueError, 'instruction changed before apply'):
            harness_apply.apply_application(application)
        self.assertFalse((self.root / '.harness').exists())
        self.assertFalse((self.root / 'AGENTS.md').exists())

    def test_nonportable_artifact_paths_fail_without_journal_or_outputs(self):
        plan = minimal_plan(self.root)
        for name in ('file.', 'file ', 'file:stream', 'CON.md', 'nul', 'LPT1.txt', 'bad?.md', '.git./marker'):
            with self.subTest(name=name):
                candidate = {**plan, 'artifacts': [*plan['artifacts'], {
                    'path': '.agents/skills/project-harness/references/' + name, 'content': 'fixture\n', 'mode': '0644'}]}
                with self.assertRaisesRegex(ValueError, 'nonportable managed path'):
                    harness_apply.build_application(self.root, candidate)
                self.assertFalse((self.root / '.harness').exists())
                self.assertFalse((self.root / '.agents').exists())


if __name__ == '__main__':
    unittest.main()
