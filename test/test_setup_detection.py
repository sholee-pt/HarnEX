"""PATH registration alone must not require a reinstall preference choice."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from harness_cli import distribution as dist, main, setup, shell, uninstall, windows_path

REPO = Path(__file__).resolve().parents[1]


class InstallationDetectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.data, self.binary, self.home = self.base / 'data', self.base / 'bin', self.base / 'home'
        self.binary.mkdir()
        self.home.mkdir()
        self.profile = self.home / '.bashrc'
        self.profile.write_bytes(shell._block(str(self.binary)))
        self.other = self.binary / 'another-command'
        self.other.write_bytes(b'keep shared command')
        self.enterContext(mock.patch.object(Path, 'home', return_value=self.home))
        self.enterContext(mock.patch.dict(os.environ, {'CODEX_HOME': str(self.base / 'codex'), 'HARNESS_CREDENTIAL_HOME': str(self.base / 'credentials')}))

    def test_path_only_is_fresh_without_a_terminal_or_path_probe(self):
        before = self.profile.read_bytes(), self.profile.stat().st_mtime_ns
        with mock.patch('builtins.input', side_effect=AssertionError('No preference choice')), \
             mock.patch('builtins.open', side_effect=AssertionError('No terminal access')), \
             mock.patch.object(windows_path, 'register_path', side_effect=AssertionError('PATH is not installation evidence')):
            self.assertEqual(setup.choose(self.data, self.binary, 'ask'), ('fresh', None))
            self.data.mkdir()
            self.assertEqual(setup.choose(self.data, self.binary, 'ask'), ('fresh', None))
        self.assertEqual((self.profile.read_bytes(), self.profile.stat().st_mtime_ns), before)
        self.assertEqual(self.other.read_bytes(), b'keep shared command')

    def test_uninstall_then_install_skips_choice_and_does_not_restore_old_preferences(self):
        installed = dist.install_tool(REPO, self.data, self.binary, sys.executable, auto_update='off')
        before = self.profile.read_bytes(), self.profile.stat().st_mtime_ns
        plan = uninstall.prepare(self.data)
        self.assertEqual(plan['path']['reason'], 'shared command directory')
        self.assertEqual(uninstall.remove(plan)['state'], 'uninstalled')
        self.assertFalse(self.data.exists())
        self.assertTrue(all(not Path(path).exists() for path in installed['launchers']))
        with mock.patch.object(main, '_environment'), contextlib.redirect_stdout(io.StringIO()), \
             mock.patch('builtins.input', side_effect=AssertionError('No preference choice')), \
             mock.patch.object(setup.sys.stdin, 'isatty', return_value=False):
            result = main.main(['install', '--data-dir', str(self.data), '--bin-dir', str(self.binary), '--no-modify-path'], source_root=REPO)
        self.assertEqual(result, 0)
        self.assertEqual(dist.installed_status(self.data)['auto_update'], 'compatible')
        self.assertEqual((self.profile.read_bytes(), self.profile.stat().st_mtime_ns), before)
        self.assertEqual(self.other.read_bytes(), b'keep shared command')

    def test_actual_installation_still_asks_and_identifies_the_installation(self):
        dist.install_tool(REPO, self.data, self.binary, sys.executable, auto_update='off')
        before = (self.data / 'active.json').read_bytes()
        with mock.patch.object(sys.stdin, 'isatty', return_value=True), mock.patch.object(sys.stdout, 'isatty', return_value=True), \
             mock.patch('builtins.input', return_value='reuse') as prompt:
            choice, previous = setup.choose(self.data, self.binary, 'ask')
        self.assertEqual(choice, 'reuse')
        self.assertEqual(previous['auto_update'], 'off')
        self.assertIn('An existing HarnEX installation was found.', prompt.call_args.args[0])
        self.assertNotIn('or PATH registration', prompt.call_args.args[0])
        self.assertEqual((self.data / 'active.json').read_bytes(), before)

    @unittest.skipUnless(os.name == 'posix', 'Real Bash PATH registration')
    def test_linux_reinstall_reuses_shared_path_without_prompt_or_profile_writes(self):
        before = self.profile.read_bytes(), self.profile.stat().st_mtime_ns
        arguments = ['install', '--data-dir', str(self.data), '--bin-dir', str(self.binary), '--no-codex-integration']
        with mock.patch.object(main, '_environment'), contextlib.redirect_stdout(io.StringIO()), \
             mock.patch('builtins.input', side_effect=AssertionError('PATH alone must not prompt')):
            self.assertEqual(main.main(arguments, source_root=REPO), 0)
            self.assertEqual(uninstall.remove(uninstall.prepare(self.data))['state'], 'uninstalled')
            self.assertFalse(self.data.exists())
            self.assertEqual(main.main(arguments, source_root=REPO), 0)
        self.assertEqual((self.profile.read_bytes(), self.profile.stat().st_mtime_ns), before)
        self.assertEqual(self.other.read_bytes(), b'keep shared command')

    def test_orphan_commands_are_preserved_and_reported_before_any_choice(self):
        for name in ('harnex', 'harnex.cmd', 'harness-codex', 'harness-codex.cmd'):
            path = self.binary / name
            path.write_bytes(b'unowned command')
            for choice in ('ask', 'reuse', 'reset'):
                with self.subTest(name=name, choice=choice), mock.patch('builtins.input', side_effect=AssertionError('No misleading choice')):
                    with self.assertRaisesRegex(ValueError, 'without a verified installation') as error:
                        setup.choose(self.data, self.binary, choice)
                    self.assertIn(str(path), str(error.exception))
                    self.assertEqual(path.read_bytes(), b'unowned command')
                    self.assertFalse(self.data.exists())
            path.unlink()

    def test_explicit_reset_without_installation_reaches_path_registration(self):
        with mock.patch.object(main, '_environment'), mock.patch.object(setup, 'prepare_integration'), \
             mock.patch.object(setup, 'path_registration', return_value={'state': 'reset'}) as registration, \
             mock.patch('builtins.input', side_effect=AssertionError('Explicit choice')), contextlib.redirect_stdout(io.StringIO()):
            result = main.main(['install', '--data-dir', str(self.data), '--bin-dir', str(self.binary), '--existing', 'reset'], source_root=REPO)
        self.assertEqual(result, 0)
        self.assertEqual(registration.call_args_list, [mock.call(self.binary, reset=True, dry_run=True, previous=None),
                                                     mock.call(self.binary, reset=True, previous=None)])
