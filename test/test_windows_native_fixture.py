"""Windows test input repair must preserve assertions and packaged source bytes."""
import contextlib
import hashlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from integration import run_windows_native_tests as native


class WindowsNativeFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.path = self.root / native.FIXTURE_PATH
        self.path.parent.mkdir(parents=True)
        self.original = b'// fixture\r\n' + native.OLD_LINK + b'\r\nassert_snapshot!("first (first.txt)\\nsecond.txt");\r\n'
        self.path.write_bytes(self.original)
        patch = mock.patch.object(native, 'FIXTURE_SHA256', hashlib.sha256(self.original).hexdigest())
        patch.start()
        self.addCleanup(patch.stop)
        self.target = 'x86_64-pc-windows-msvc'

    def test_all_assertions_are_retained_and_bytes_restored_after_success_or_test_failure(self):
        for result in (0, 100):
            with self.subTest(result=result):
                def invoke(command, **kwargs):
                    self.assertEqual(self.path.read_bytes().replace(native.NEW_LINK, native.OLD_LINK), self.original)
                    self.assertIn(b'url::Url::from_file_path', self.path.read_bytes())
                    self.assertEqual(command[2], str(self.root / 'build/native_ui/run_tests.py'))
                    self.assertEqual(command[-2:], ['--target', self.target])
                    return subprocess.CompletedProcess(command, result)
                with mock.patch.object(native.subprocess, 'run', side_effect=invoke) as runner, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(native.run_tests(self.root, self.root, self.target), result)
                runner.assert_called_once()
                self.assertEqual(self.path.read_bytes(), self.original)

    def test_launch_error_or_interrupt_restores_original_source(self):
        for failure in (OSError('launch failed'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                with mock.patch.object(native.subprocess, 'run', side_effect=failure), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(type(failure)):
                        native.run_tests(self.root, self.root, self.target)
                self.assertEqual(self.path.read_bytes(), self.original)

    def test_unreviewed_fixture_is_preserved_without_launching_tests(self):
        changed = self.original + b'// upstream change\n'
        self.path.write_bytes(changed)
        with mock.patch.object(native.subprocess, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'fixture changed'):
                native.run_tests(self.root, self.root, self.target)
        runner.assert_not_called()
        self.assertEqual(self.path.read_bytes(), changed)

    def test_other_platform_does_not_modify_its_fixture(self):
        with mock.patch.object(native.subprocess, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'only for Windows'):
                native.run_tests(self.root, self.root, 'x86_64-unknown-linux-musl')
        runner.assert_not_called()
        self.assertEqual(self.path.read_bytes(), self.original)
