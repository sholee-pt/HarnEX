"""Published GitHub releases, independent of development branch heads."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from . import distribution as dist

REPOSITORY = 'sholee-pt/HarnEX'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def request(url, *, timeout=5, accept='application/vnd.github+json'):
    if not url.startswith(('https://api.github.com/repos/sholee-pt/HarnEX/',
                           'https://api.github.com/repos/openai/codex/')):
        raise ValueError('Unexpected release API URL')
    headers = {'User-Agent': 'HarnEX-updater', 'Accept': accept}
    token = os.environ.get('HARNESS_GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    return urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url, headers=headers), timeout=timeout)


def metadata(repository, suffix, *, timeout=5):
    with request('https://api.github.com/repos/' + repository + '/' + suffix, timeout=timeout) as incoming:
        content = incoming.read(4 * 1024 * 1024 + 1)
    if len(content) > 4 * 1024 * 1024:
        raise ValueError('Release metadata exceeds its size bound')
    return json.loads(content)


def asset(release, name, repository):
    entries = release.get('assets', [])
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise ValueError('Invalid release asset list')
    candidates = [item for item in entries if item.get('name') == name]
    if len(candidates) != 1:
        raise ValueError('Published release is missing a unique asset: ' + name)
    value = candidates[0]
    prefix = 'https://api.github.com/repos/' + repository + '/releases/assets/'
    digest = value.get('digest', '')
    if (not isinstance(value.get('url'), str) or not re.fullmatch(re.escape(prefix) + r'[0-9]+', value['url'])
            or not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest)):
        raise ValueError('Release asset has no trusted URL or SHA-256 digest')
    return value


def download(value, destination, *, limit=512 * 1024 * 1024, timeout=120):
    deadline = time.monotonic() + timeout
    try:
        incoming = request(value['url'], timeout=min(timeout, 15), accept='application/octet-stream')
    except urllib.error.HTTPError as error:
        if error.code not in {301, 302, 303, 307, 308}:
            raise
        url = error.headers.get('Location', '')
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}:
            raise ValueError('Unexpected release download redirect') from None
        # A signed download receives no API credential.
        incoming = urllib.request.urlopen(url, timeout=min(timeout, 15))
    digest, size = hashlib.sha256(), 0
    with incoming, destination.open('xb') as stream:
        while block := incoming.read(1024 * 1024):
            if time.monotonic() > deadline:
                raise TimeoutError('Release download timed out; previous installation is retained')
            size += len(block)
            if size > limit:
                raise ValueError('Release asset exceeds its size bound')
            digest.update(block)
            stream.write(block)
    if value['digest'] != 'sha256:' + digest.hexdigest() or size != value.get('size'):
        raise ValueError('Release asset size or digest mismatch')


def target_platform():
    machine = {'amd64': 'x86_64', 'x86_64': 'x86_64', 'arm64': 'aarch64', 'aarch64': 'aarch64'}.get(platform.machine().lower())
    if sys.platform == 'linux' and machine:
        return 'linux-' + machine
    if sys.platform == 'win32' and machine == 'x86_64':
        return 'windows-x86_64'
    raise ValueError('No published HarnEX update supports this operating system and architecture')


def platform_assets(release, target):
    if target not in {'linux-x86_64', 'linux-aarch64', 'windows-x86_64'}:
        raise ValueError('Unsupported HarnEX update platform')
    version = release.get('tag_name', '').removeprefix('v')
    renamed = dist._version(version) >= dist._version('0.36.0-beta')
    windows = target.startswith('windows-')
    source = f'harness-codex-{version}-' + ('windows.zip' if windows else 'linux.tar.gz')
    installer = ('install_harnex' if renamed else 'install_harness_codex') + ('.ps1' if windows else '.sh')
    names = [source, installer, 'SHA256SUMS', 'build.json']
    if windows:
        names.append(f'harness-codex-ui-{version}-{target}.tar.gz')
    values = {name: asset(release, name, REPOSITORY) for name in names}
    if any(type(value.get('size')) is not int or value['size'] <= 0 or value.get('state', 'uploaded') != 'uploaded' for value in values.values()):
        raise ValueError('Published release has an incomplete platform asset')
    return values[source], values.get(names[-1]) if windows else None


def latest_harness(*, timeout=5, target=None):
    target = target or target_platform()
    deadline = time.monotonic() + timeout
    releases = []
    for page in range(1, 21):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('HarnEX release discovery timed out; retry the update check')
        suffix = 'releases?per_page=100' + (f'&page={page}' if page > 1 else '')
        entries = metadata(REPOSITORY, suffix, timeout=remaining)
        if time.monotonic() >= deadline:
            raise TimeoutError('HarnEX release discovery timed out; retry the update check')
        if not isinstance(entries, list) or len(entries) > 100:
            raise ValueError('Invalid GitHub release list')
        releases.extend(entries)
        if len(entries) < 100:
            break
    else:
        raise ValueError('HarnEX release discovery exceeded its page bound; no complete update check was possible')
    candidates = [item for item in releases if isinstance(item, dict) and not item.get('draft') and
                  isinstance(item.get('tag_name'), str) and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-beta)?', item['tag_name'])]
    for release in sorted(candidates, key=lambda item: dist._version(item['tag_name'][1:]), reverse=True):
        try:
            platform_assets(release, target)
        except ValueError:
            continue
        return release
    raise ValueError('No complete published HarnEX release is available for ' + target)


def check(data_root, *, timeout=5):
    state = dist.installed_status(data_root)
    target = target_platform()
    release = latest_harness(timeout=timeout, target=target)
    version = release['tag_name'][1:]
    available = dist._version(version) > dist._version(state['version'])
    return {'status': 'update-available' if available else 'up-to-date', 'updateAvailable': available,
            'currentVersion': state['version'], 'availableVersion': version, 'release': release, 'platform': target,
            'majorUpgrade': dist._version(version)[0] > dist._version(state['version'])[0]}


def extract_windows(archive, output):
    """Extract a bounded Windows source ZIP without links or path aliases."""
    output = dist._path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(dist._path(archive)) as incoming:
            members = incoming.infolist()
            if len(members) > dist.MAX_FILES:
                raise ValueError('Windows archive has too many entries')
            seen, total = set(), 0
            for member in members:
                name = dist._relative(member.filename.rstrip('/'))
                kind = stat.S_IFMT(member.external_attr >> 16)
                if (name.casefold() in seen or kind not in {0, stat.S_IFDIR if member.is_dir() else stat.S_IFREG}
                        or member.flag_bits & 1 or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or not 0 <= member.file_size <= dist.MAX_FILE_BYTES or member.is_dir() and member.file_size):
                    raise ValueError('Unsupported or duplicate Windows archive member')
                seen.add(name.casefold())
                total += member.file_size
                if total > dist.MAX_TREE_BYTES:
                    raise ValueError('Windows archive exceeds the unpacked size bound')
                destination = dist._path(output / name)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with incoming.open(member) as source, destination.open('xb') as stream:
                    remaining = member.file_size
                    while remaining:
                        block = source.read(min(1024 * 1024, remaining))
                        if not block:
                            raise ValueError('Truncated Windows archive member')
                        stream.write(block)
                        remaining -= len(block)
                    if source.read(1):
                        raise ValueError('Windows archive member exceeds its declared size')
    except zipfile.BadZipFile as error:
        raise ValueError('Invalid Windows release archive') from error


def update(data_root, *, selected=None, timeout=120):
    """Install the selected published bytes, retaining the old immutable release."""
    root = dist._storage_path(data_root)
    before = dist.installed_status(root)
    selected = selected or check(root, timeout=min(timeout, 10))
    if not selected['updateAvailable']:
        return {**selected, 'updated': False, 'installation': before}
    version = selected['availableVersion']
    if dist._version(version) <= dist._version(before['version']):
        raise ValueError('HarnEX update would not be a forward version change')
    release = selected['release']
    if release.get('draft') or release.get('tag_name') != 'v' + version:
        raise ValueError('Selected HarnEX release identity changed')
    target = target_platform()
    if selected.get('platform', target) != target:
        raise ValueError('Selected HarnEX update belongs to a different platform; check again')
    value, native = platform_assets(release, target)
    if native is not None:
        from . import codex_integration, native_package, native_ui
        previous_integration = codex_integration.read(root)
    with tempfile.TemporaryDirectory(prefix='harness-release-') as temporary:
        temporary = Path(temporary).resolve()
        archive = temporary / value['name']
        download(value, archive, limit=dist.MAX_TREE_BYTES, timeout=timeout)
        # Reject unsafe members within the isolated temporary extraction tree.
        from .native_package import extract
        if native is not None:
            extract_windows(archive, temporary / 'unpacked')
        else:
            extract(archive, temporary / 'unpacked', max_files=dist.MAX_FILES, max_tree=dist.MAX_TREE_BYTES)
        source = temporary / 'unpacked' / ('harness-codex-' + version)
        snapshot = dist._snapshot(source)
        declared_version, commit = dist._source_info(snapshot)
        if declared_version != version or not commit:
            raise ValueError('Published source lacks matching version and commit provenance')
        if native is not None and previous_integration is not None:
            package = temporary / native['name']
            download(native, package, limit=native_package.MAX_FILE, timeout=timeout)
            extract(package, temporary / 'native')
            receipt = native_package.verify(temporary / 'native', version, target)
            if receipt.get('harnessSourceCommit') != commit or receipt.get('directIntegrationVersion') != 1:
                raise ValueError('Windows native package differs from the selected HarnEX source')
            # Prepare the verified package before switching the tool pointer.
            binary = native_ui.ensure(root, version, archive=package)
            if native_package.verify(binary.parent.parent, version, target) != receipt:
                raise ValueError('Prepared Windows package differs from the selected release')
        with dist._lock(root):
            current = dist.installed_status(root)
            if current != before:
                raise ValueError('HarnEX installation changed during download; retry')
            if native is not None and codex_integration.read(root) != previous_integration:
                raise ValueError('Windows integration changed during download; retry')
            active = {key: item for key, item in before.items() if key not in {'dataRoot', 'sourceRoot', 'releasePath', 'release_root'}}
            active.update(version=version, commit=commit)
            installation = dist._activate(snapshot, root, active)
    from .installation_paths import repair_entrypoints
    repair_entrypoints(root)
    installation = dist.migrate_command(root)
    return {**selected, 'status': 'updated', 'updated': True, 'installation': installation}
