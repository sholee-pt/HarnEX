"""Use a Markdown-safe Windows test link, restoring the pinned upstream bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FIXTURE_PATH = 'codex-rs/tui/src/markdown_render/file_citations_tests.rs'
FIXTURE_SHA256 = '04ed9d07010cc9992a14350d118a4f319579e517627ef0797e8d573e35ff7e68'
OLD_LINK = b'        cwd.join("first.txt").display(),'
NEW_LINK = b'        url::Url::from_file_path(cwd.join("first.txt")).expect("absolute fixture path"),'


def run_tests(source_root: Path, root: Path, target: str) -> int:
    if target != 'x86_64-pc-windows-msvc':
        raise ValueError('The citation fixture adapter is only for Windows native tests')
    path = root / FIXTURE_PATH
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != FIXTURE_SHA256 or original.count(OLD_LINK) != 1:
        raise ValueError('Upstream citation fixture changed; review it before applying the Windows adapter')
    command = [sys.executable, '-B', str(source_root / 'build/native_ui/run_tests.py'),
               '--root', str(root), '--target', target]
    try:
        # File URLs preserve separators, spaces and punctuation through Markdown parsing.
        path.write_bytes(original.replace(OLD_LINK, NEW_LINK))
        print(json.dumps({'windowsCitationFixture': FIXTURE_PATH, 'originalSha256': FIXTURE_SHA256,
                          'snapshotExpectationsChanged': False}), flush=True)
        return subprocess.run(command, check=False).returncode
    finally:
        path.write_bytes(original)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    raise SystemExit(run_tests(args.source_root.resolve(), args.root.resolve(), args.target))
