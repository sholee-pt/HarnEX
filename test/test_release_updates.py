"""Platform-specific release selection and failure before tool activation."""
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

from harness_cli import codex_integration, distribution as dist, native_ui, release_updates as updates
from test_cli_distribution import files, source
from test_native_ui import archive as native_archive, fixture as native_fixture


def release_fixture(version, platforms=('linux', 'windows')):
    names = ['SHA256SUMS', 'build.json']
    installer = 'install_harnex' if dist._version(version) >= dist._version('0.36.0-beta') else 'install_harness_codex'
    if 'linux' in platforms:
        names += [f'harness-codex-{version}-linux.tar.gz', installer + '.sh']
    if 'windows' in platforms:
        names += [f'harness-codex-{version}-windows.zip', installer + '.ps1', f'harness-codex-ui-{version}-windows-x86_64.tar.gz']
    return {'tag_name': 'v' + version, 'assets': [
        {'name': name, 'url': 'https://api.github.com/repos/sholee-pt/HarnEX/releases/assets/' + str(index + 1),
         'digest': 'sha256:' + 'a' * 64, 'size': 1, 'state': 'uploaded'} for index, name in enumerate(names)]}


class PlatformSelectionTests(unittest.TestCase):
    def test_host_detection_and_unsupported_architectures(self):
        for system, machine, expected in [('linux', 'x86_64', 'linux-x86_64'), ('linux', 'arm64', 'linux-aarch64'),
                                           ('win32', 'AMD64', 'windows-x86_64'), ('win32', 'ARM64', None), ('darwin', 'arm64', None)]:
            with self.subTest(system=system, machine=machine), mock.patch.object(updates.sys, 'platform', system), \
                    mock.patch.object(updates.platform, 'machine', return_value=machine):
                if expected:
                    self.assertEqual(updates.target_platform(), expected)
                else:
                    with self.assertRaisesRegex(ValueError, 'operating system and architecture'):
                        updates.target_platform()

    def test_checks_choose_the_latest_complete_release_for_each_platform_without_downloads(self):
        releases = [release_fixture('0.36.0-beta'), release_fixture('0.36.1-beta', ('linux',)),
                    release_fixture('0.37.0-beta', ('windows',)), {'tag_name': 'preview'}, None]
        draft = release_fixture('9.0.0')
        draft['draft'] = True
        releases.append(draft)
        for target, expected in [('linux-x86_64', '0.36.1-beta'), ('linux-aarch64', '0.36.1-beta'), ('windows-x86_64', '0.37.0-beta')]:
            with self.subTest(target=target), mock.patch.object(updates, 'target_platform', return_value=target), \
                    mock.patch.object(updates, 'metadata', return_value=releases), mock.patch.object(updates, 'download') as download, \
                    mock.patch.object(dist, 'installed_status', return_value={'version': '0.35.3-beta'}):
                result = updates.check(Path('unused'))
                self.assertEqual(result['availableVersion'], expected)
                self.assertEqual(result['platform'], target)
                self.assertTrue(result['updateAvailable'])
                download.assert_not_called()

    def test_incomplete_duplicate_and_untrusted_assets_are_not_advertised(self):
        complete = release_fixture('0.36.0-beta')
        candidate = release_fixture('0.36.1-beta')
        _, native = updates.platform_assets(candidate, 'windows-x86_64')
        required = [item['name'] for item in candidate['assets'] if not item['name'].endswith(('-linux.tar.gz', '.sh'))]
        variants = []
        for name in required:
            changed = copy.deepcopy(candidate)
            changed['assets'] = [item for item in changed['assets'] if item['name'] != name]
            variants.append(changed)
        for field, value in [('digest', None), ('url', 'https://example.org/package'), ('size', 0), ('state', 'starter')]:
            changed = copy.deepcopy(candidate)
            next(item for item in changed['assets'] if item['name'] == native['name'])[field] = value
            variants.append(changed)
        changed = copy.deepcopy(candidate)
        changed['assets'].append(copy.deepcopy(native))
        variants.extend([changed, {**candidate, 'assets': None}, {**candidate, 'assets': [None]}])
        for changed in variants:
            with self.subTest(changed=changed), mock.patch.object(updates, 'metadata', return_value=[complete, changed]):
                self.assertEqual(updates.latest_harness(target='windows-x86_64')['tag_name'], 'v0.36.0-beta')

    def test_missing_platform_is_reported_as_unavailable_and_never_as_current(self):
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(updates, 'metadata', return_value=[release_fixture('0.36.1-beta', ('linux',))]), \
                mock.patch.object(dist, 'installed_status', return_value={'version': '0.36.0-beta'}):
            with self.assertRaisesRegex(ValueError, 'No complete.*windows-x86_64'):
                updates.check(Path('unused'))

    def test_legacy_installer_names_and_newer_installed_version_remain_supported(self):
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(updates, 'metadata', return_value=[release_fixture('0.35.3-beta')]), \
                mock.patch.object(dist, 'installed_status', return_value={'version': '0.36.0-beta'}):
            self.assertFalse(updates.check(Path('unused'))['updateAvailable'])


class ReleaseActivationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.old = source(self.root / 'old', '0.36.0-beta', 'a' * 40)
        self.new = source(self.root / 'new', '0.36.1-beta', 'b' * 40)
        (self.old / 'harness_cli/retired.py').write_text('old = True\n')
        self.data = self.root / 'data'
        self.before = dist.install_tool(self.old, self.data, self.root / 'bin', sys.executable)
        self.release = release_fixture('0.36.1-beta')
        self.payloads = {}
        for suffix in ('linux.tar.gz', 'windows.zip'):
            path = self.root / suffix
            if suffix.endswith('.zip'):
                with zipfile.ZipFile(path, 'w') as bundle:
                    for file in self.new.rglob('*'):
                        if file.is_file():
                            bundle.write(file, 'harness-codex-0.36.1-beta/' + file.relative_to(self.new).as_posix())
            else:
                with tarfile.open(path, 'w:gz') as bundle:
                    for file in self.new.rglob('*'):
                        if file.is_file():
                            bundle.add(file, arcname='harness-codex-0.36.1-beta/' + file.relative_to(self.new).as_posix())
            self.payload('harness-codex-0.36.1-beta-' + suffix, path.read_bytes())
        self.selected = {'updateAvailable': True, 'availableVersion': '0.36.1-beta', 'release': self.release}

    def payload(self, name, content):
        value = next(item for item in self.release['assets'] if item['name'] == name)
        value.update(size=len(content), digest='sha256:' + hashlib.sha256(content).hexdigest())
        self.payloads[value['url']] = content

    def request(self, url, **kwargs):
        return io.BytesIO(self.payloads[url])

    def test_each_platform_downloads_its_own_source_and_retains_previous_files(self):
        for target, suffix in [('linux-x86_64', 'linux.tar.gz'), ('linux-aarch64', 'linux.tar.gz'), ('windows-x86_64', 'windows.zip')]:
            data = self.root / target
            before = dist.install_tool(self.old, data, self.root / (target + '-bin'), sys.executable)
            old_bytes = files(Path(before['sourceRoot']))
            with self.subTest(target=target), mock.patch.object(updates, 'target_platform', return_value=target), \
                    mock.patch.object(updates, 'request', side_effect=self.request) as request:
                result = updates.update(data, selected=self.selected)
                expected = next(item for item in self.release['assets'] if item['name'].endswith(suffix))
                self.assertEqual([call.args[0] for call in request.call_args_list], [expected['url']])
                self.assertTrue(result['updated'])
                self.assertEqual(result['installation']['version'], '0.36.1-beta')
                self.assertFalse((Path(result['installation']['sourceRoot']) / 'harness_cli/retired.py').exists())
                self.assertEqual(files(Path(before['sourceRoot'])), old_bytes)

    def test_selected_platform_or_missing_assets_cannot_bypass_the_update_check(self):
        for selected in ({**self.selected, 'platform': 'linux-x86_64'},
                         {**self.selected, 'release': release_fixture('0.36.1-beta', ('linux',))}):
            with self.subTest(selected=selected), mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                    mock.patch.object(updates, 'download') as download:
                with self.assertRaises(ValueError):
                    updates.update(self.data, selected=selected)
                download.assert_not_called()
                self.assertEqual(dist.installed_status(self.data), self.before)

    def test_windows_native_failure_does_not_activate_new_tool_source(self):
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(codex_integration, 'read', return_value={'schema': 1}), \
                mock.patch.object(updates, 'request', side_effect=self.request), mock.patch.object(native_ui, 'ensure') as ensure:
            native = next(item for item in self.release['assets'] if '-ui-' in item['name'])
            self.payloads[native['url']] = b'corrupt native archive'
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                updates.update(self.data, selected=self.selected)
            ensure.assert_not_called()
            self.assertEqual(dist.installed_status(self.data), self.before)

    def prepare_native(self, commit='b' * 40):
        native = self.root / 'native'
        native_fixture(native)
        metadata = native / 'harness-ui.json'
        receipt = json.loads(metadata.read_text())
        receipt.update(version='0.36.1-beta', harnessSourceCommit=commit)
        metadata.write_text(json.dumps(receipt))
        path = self.root / 'native.tar.gz'
        native_archive(native, path)
        self.payload('harness-codex-ui-0.36.1-beta-windows-x86_64.tar.gz', path.read_bytes())
        return native

    def test_windows_native_is_verified_and_prepared_before_pointer_switch(self):
        self.prepare_native()
        ensure = native_ui.ensure
        def prepare(*args, **kwargs):
            self.assertEqual(dist.installed_status(self.data), self.before)
            return ensure(*args, **kwargs)
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(codex_integration, 'read', return_value={'schema': 1}), \
                mock.patch.object(native_ui, 'platform_key', return_value='windows-x86_64'), \
                mock.patch.object(native_ui, 'ensure', side_effect=prepare) as prepared, \
                mock.patch.object(updates, 'request', side_effect=self.request):
            result = updates.update(self.data, selected=self.selected)
            prepared.assert_called_once()
            self.assertTrue(result['updated'])
            self.assertTrue((self.data / 'native-ui/v0.36.1-beta/windows-x86_64/bin/codex.exe').is_file())

    def test_wrong_native_source_commit_is_rejected_before_preparing_or_activating(self):
        self.prepare_native('c' * 40)
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(codex_integration, 'read', return_value={'schema': 1}), \
                mock.patch.object(native_ui, 'ensure') as ensure, mock.patch.object(updates, 'request', side_effect=self.request):
            with self.assertRaisesRegex(ValueError, 'differs from the selected HarnEX source'):
                updates.update(self.data, selected=self.selected)
            ensure.assert_not_called()
            self.assertEqual(dist.installed_status(self.data), self.before)

    def test_different_cached_native_package_is_not_accepted_for_the_selected_release(self):
        native = self.prepare_native()
        metadata = native / 'harness-ui.json'
        receipt = json.loads(metadata.read_text())
        receipt['harnessSourceCommit'] = 'c' * 40
        metadata.write_text(json.dumps(receipt))
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(codex_integration, 'read', return_value={'schema': 1}), \
                mock.patch.object(native_ui, 'ensure', return_value=native / 'bin/codex.exe'), \
                mock.patch.object(updates, 'request', side_effect=self.request):
            with self.assertRaisesRegex(ValueError, 'Prepared Windows package differs'):
                updates.update(self.data, selected=self.selected)
            self.assertEqual(dist.installed_status(self.data), self.before)

    def test_concurrent_windows_integration_change_preserves_the_active_source(self):
        with mock.patch.object(updates, 'target_platform', return_value='windows-x86_64'), \
                mock.patch.object(codex_integration, 'read', side_effect=[None, {'schema': 1}]), \
                mock.patch.object(updates, 'request', side_effect=self.request):
            with self.assertRaisesRegex(ValueError, 'Windows integration changed'):
                updates.update(self.data, selected=self.selected)
            self.assertEqual(dist.installed_status(self.data), self.before)


class WindowsArchiveTests(unittest.TestCase):
    def test_unsafe_paths_links_duplicates_and_bounds_are_rejected(self):
        for mode in ('traversal', 'case', 'symlink', 'stream', 'reserved', 'file-limit', 'tree-limit', 'count-limit', 'corrupt'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / 'source.zip'
                with zipfile.ZipFile(archive, 'w') as bundle:
                    name = {'traversal': '../outside', 'stream': 'file:stream', 'reserved': 'CON.txt'}.get(mode, 'source/file')
                    info = zipfile.ZipInfo(name)
                    if mode == 'symlink':
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    bundle.writestr(info, b'content')
                    if mode == 'case':
                        bundle.writestr('source/FILE', b'other')
                if mode == 'corrupt':
                    archive.write_bytes(b'not a ZIP')
                with mock.patch.object(dist, 'MAX_FILE_BYTES', 1 if mode == 'file-limit' else dist.MAX_FILE_BYTES), \
                        mock.patch.object(dist, 'MAX_TREE_BYTES', 1 if mode == 'tree-limit' else dist.MAX_TREE_BYTES), \
                        mock.patch.object(dist, 'MAX_FILES', 0 if mode == 'count-limit' else dist.MAX_FILES):
                    with self.assertRaises(ValueError):
                        updates.extract_windows(archive, root / 'output')
                self.assertFalse((root / 'outside').exists())


if __name__ == '__main__':
    unittest.main()
