"""Public command replacement preserves user files and recovers interruptions."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from harness_cli import distribution as dist, main, management_relay, uninstall


REPO = Path(__file__).resolve().parents[1]


class HarnEXIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data, self.binary = self.root / 'tool', self.root / 'bin'

    def previous(self, command='harness-codex'):
        source = self.root / 'previous'
        for name, data in dist._snapshot(REPO).items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name in {dist.METADATA, '.agents/skills/harness/assets/manifest.json'}:
                data = data.replace(b'0.36.3-beta', b'0.35.3-beta')
            path.write_bytes(data)
        state = dist.install_tool(source, self.data, self.binary)
        if command == 'harness':
            active = dist._read_json(self.data / 'active.json')
            for path in active['launchers']:
                if Path(path).parent == self.binary:
                    Path(path).unlink()
            import hashlib
            launchers = dist._launchers(self.data, self.binary, sys.executable, 'harness')
            for path, data in launchers.items():
                path.write_bytes(data)
            active.pop('command')
            active['launchers'] = {str(path): hashlib.sha256(data).hexdigest() for path, data in launchers.items()}
            dist._write_json(self.data / 'active.json', active)
            state = dist.installed_status(self.data)
        return state

    def test_fresh_install_owns_only_new_command(self):
        state = dist.install_tool(REPO, self.data, self.binary)
        self.assertEqual(state['command'], 'harnex')
        expected = {'harnex'} | ({'harnex.cmd'} if os.name == 'nt' else set())
        self.assertEqual({path.name for path in self.binary.iterdir()}, expected)
        self.assertEqual(main.build_parser(REPO).prog, 'harnex')
        self.assertEqual(dist.install_tool(REPO, self.data, self.binary)['launchers'], state['launchers'])

    def test_reinstall_replaces_old_commands_and_preserves_preferences(self):
        for command in ('harness-codex', 'harness'):
            with self.subTest(command=command):
                self.data, self.binary = self.root / command / 'tool', self.root / command / 'bin'
                self.previous(command)
                old = list(self.binary.iterdir())
                state = dist.install_tool(REPO, self.data, self.binary, auto_update='off')
                self.assertEqual(state['command'], 'harnex')
                self.assertEqual(state['auto_update'], 'off')
                for path in old:
                    self.assertFalse(path.exists())
                    self.assertNotIn(str(path), state['launchers'])
                self.assertEqual(dist.install_tool(REPO, self.data, self.binary, auto_update='off')['launchers'], state['launchers'])

    def test_user_command_collision_preserves_previous_installation(self):
        before = self.previous()
        (self.binary / 'harnex').write_text('user command')
        with self.assertRaisesRegex(ValueError, 'user-owned'):
            dist.install_tool(REPO, self.data, self.binary)
        self.assertEqual(dist.installed_status(self.data), before)
        self.assertEqual((self.binary / 'harnex').read_text(), 'user command')

    def test_interrupted_command_migration_recovers_and_preserves_edits(self):
        self.previous()
        write = dist._write_json
        def interrupt(path, value):
            if Path(path).name == 'active.json' and value.get('command') == 'harnex':
                raise OSError('simulated interruption')
            return write(path, value)
        with mock.patch.object(dist, '_write_json', side_effect=interrupt):
            with self.assertRaisesRegex(OSError, 'simulated interruption'):
                dist.install_tool(REPO, self.data, self.binary)
        self.assertTrue((self.data / '.command-migration.json').is_file())
        path = self.binary / 'harnex'
        owned = path.read_bytes()
        path.write_text('user changed this file')
        with self.assertRaisesRegex(ValueError, 'changed'):
            dist.migrate_command(self.data)
        self.assertEqual(path.read_text(), 'user changed this file')
        path.write_bytes(owned)
        self.assertEqual(dist.install_tool(REPO, self.data, self.binary)['command'], 'harnex')
        self.assertFalse((self.data / '.command-migration.json').exists())
        self.assertFalse((self.binary / 'harness-codex').exists())

    def test_interrupted_old_command_removal_recovers_without_deleting_edits(self):
        self.previous()
        retired = self.binary / 'harness-codex'
        owned = retired.read_bytes()
        unlink = Path.unlink
        def interrupt(path, *args, **kwargs):
            result = unlink(path, *args, **kwargs)
            if path == retired:
                raise OSError('interrupted removal')
            return result
        with mock.patch.object(Path, 'unlink', interrupt):
            with self.assertRaisesRegex(OSError, 'interrupted removal'):
                dist.install_tool(REPO, self.data, self.binary)
        self.assertFalse(retired.exists())
        self.assertEqual(dist._read_json(self.data / 'active.json')['command'], 'harnex')
        with self.assertRaisesRegex(ValueError, 'replacement is pending'):
            dist.installed_status(self.data)
        retired.write_text('new user content')
        with self.assertRaisesRegex(ValueError, 'changed'):
            dist.migrate_command(self.data)
        self.assertEqual(retired.read_text(), 'new user content')
        retired.write_bytes(owned)
        self.assertEqual(dist.migrate_command(self.data)['command'], 'harnex')
        self.assertFalse(retired.exists())
        self.assertFalse((self.data / '.command-migration.json').exists())

    def test_modified_previous_command_stops_replacement(self):
        self.previous()
        retired = self.binary / 'harness-codex'
        retired.write_text('user modified old command')
        before = (self.data / 'active.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed'):
            dist.install_tool(REPO, self.data, self.binary)
        self.assertEqual(retired.read_text(), 'user modified old command')
        self.assertEqual((self.data / 'active.json').read_bytes(), before)
        self.assertFalse((self.binary / 'harnex').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows batch command replacement')
    def test_running_old_windows_command_requests_source_installer_without_self_deletion(self):
        self.previous()
        dist._install_tool(REPO, self.data, self.binary)
        command = self.binary / 'harness-codex.cmd'
        result = subprocess.run([str(command), 'update', '--repair-launcher'], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn('source installer with -Existing reuse', result.stderr)
        self.assertNotIn('batch file cannot be found', result.stderr.lower())
        self.assertTrue(command.is_file())
        self.assertFalse((self.binary / 'harnex').exists())
        dist.install_tool(REPO, self.data, self.binary)
        self.assertFalse(command.exists())
        result = subprocess.run([str(self.binary / 'harnex.cmd'), '--version'], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'HarnEX 0.36.3-beta')

    def test_uninstall_preview_includes_all_owned_commands(self):
        state = dist.install_tool(REPO, self.data, self.binary)
        unrelated = self.binary / 'another-tool'
        unrelated.write_text('keep')
        report = uninstall.prepare(self.data)
        self.assertEqual(dist.installed_status(self.data), state)
        self.assertEqual(unrelated.read_text(), 'keep')
        self.assertIn('harnex', str(report))
        self.assertNotIn('harness-codex', str(report))

    def test_old_repository_transports_canonicalize_without_changing_protocol(self):
        for prefix in ('https://github.com/', 'git@github.com:', 'ssh://git@github.com/'):
            for name in ('Harness', 'Harness-Codex', 'HarnEX'):
                self.assertEqual(dist.canonical_repository(prefix + 'sholee-pt/' + name + '.git'), prefix + 'sholee-pt/HarnEX.git')

    def test_old_and_new_menu_namespaces_have_identical_dispatch(self):
        for suffix in ('', 'status', 'init --goal "sample project"'):
            parse = lambda prefix: management_relay.parse({'input': [{'type': 'text', 'text': prefix + suffix}]})
            self.assertEqual(parse('/harnex/'), parse('/harness/'))
        self.assertIsNone(management_relay.parse({'input': [{'type': 'text', 'text': 'Discuss /harnex/status'}]}))
