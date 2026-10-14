### Linux installation

```bash
curl -fsSL https://github.com/sholee-pt/HarnEX/releases/download/v{version}/install_harnex.sh | sh
harnex --version
# Existing tool installation:
harnex update
# Review existing project artifacts when configuration needs updating:
harnex config --project /path/to/project
```

Default Linux installation prepares the isolated tool environment, official Codex CLI integration and PATH. Open a new shell with the installation prompt, or run `source ~/.bashrc` in the current shell. Codex CLI handles login. Start project work in its terminal with `codex`; use `codex resume` for an existing conversation. Enter `/harnex/` to choose project initialization or another management action.

From v0.36.3-beta, installation asks reuse/reset only when a verified tool installation exists. Shared PATH registration alone proceeds as a fresh install without that question. Command files without a verified installation and invalid tool directories are preserved and reported for inspection. Explicit `--existing reuse|reset` remains available for an existing installation; reset preserves project harnesses.

On Linux, official Codex is downloaded independently during integration setup and confirmed updates; no Codex build is required. The terminal release gate runs on Linux x86_64. Linux aarch64 package resolution is supported but not covered by that gate. Windows assets require a separately authorized and verified supplement; use Windows installation only when this release lists its PowerShell installer, Windows ZIP and matching native package. For Linux migration from the old patched integration, use this installer with `--existing reuse`, then run `config` once.

For a Windows supplement, first project configuration requires an existing native Codex executable and working account/provider access; the Windows installer prepares HarnEX only. In an interactive PowerShell terminal, pass `--codex-binary 'C:\path\to\codex.exe'` to `init/config` when needed; `.cmd`/`.bat` wrappers are refused. The matching native integration is installed after successful configuration. From v0.36.1-beta, release-channel updates select only complete releases for the current OS and architecture and download that platform's source archive. Explicit source branch pins instead follow that branch and do not establish platform publication. Older installed updaters still require you to confirm Windows asset availability before accepting an update.

### Release assets and verification

| Asset | Purpose |
| --- | --- |
| `install_harnex.sh` | Linux downloader and isolated tool setup |
| `harness-codex-{version}-linux.tar.gz` | Generator, CLI and source installer |
| `SHA256SUMS` | Checksums of the downloadable assets |
| `build.json` | Exact HarnEX source commit and platforms |

Linux publication requires installation, upgrade and official TUI/production-adapter checks. These establish tested behavior with synthetic model responses, not paid account compatibility, model quality or token savings. The installer verifies the archive automatically. For manually downloaded Linux assets, download the matching `SHA256SUMS` and use `sha256sum --check --ignore-missing SHA256SUMS` in the download directory; confirm an `OK` result for each selected asset. Windows users can compare `Get-FileHash -Algorithm SHA256` results with the matching manifest. Interactive Linux `codex` launches offer updates for published Codex and HarnEX releases before opening a conversation; downloads require your selection.

Use `harnex uninstall` to review tool removal and confirm with Enter, `y` or `yes`; decline with `n` or `no`. Project harnesses and native conversation history are preserved. Shared command directories can retain their PATH registration so other programs remain available; that alone does not mean the tool is still installed.
