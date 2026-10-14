### Linux installation

```bash
curl -fsSL https://github.com/sholee-pt/HarnEX/releases/download/v{version}/install_harnex.sh | sh
harnex --version
# Existing tool installation:
harnex update
# Review existing project artifacts when configuration needs updating:
harnex config --project /path/to/project
```

Default Linux installation prepares the isolated tool environment, official Codex integration and PATH. Open a new shell with the installation prompt, or run `source ~/.bashrc` in the current shell. Codex handles login. Start project work with `codex`; use `codex resume` for an existing conversation. Enter `/harnex/` to choose project initialization or another management action.

On Linux, official Codex is downloaded independently during integration setup and confirmed updates; no Codex build is required. The terminal release gate runs on Linux x86_64. Linux aarch64 package resolution is supported but not covered by that gate. Windows assets require a separately authorized and verified supplement; use Windows installation only when this release lists its PowerShell installer, Windows ZIP and matching native package. For Linux migration from the old patched integration, use this installer with `--existing reuse`, then run `config` once.

For a Windows supplement, first project configuration requires an existing native Codex executable and working account/provider access; the Windows installer prepares HarnEX only. In an interactive PowerShell terminal, pass `--codex-binary 'C:\path\to\codex.exe'` to `init/config` when needed; `.cmd`/`.bat` wrappers are refused. The matching native integration is installed after successful configuration. Confirm that a newer release has Windows assets before accepting a HarnEX update; the updater does not filter releases by platform availability.

### Release assets and verification

| Asset | Purpose |
| --- | --- |
| `install_harnex.sh` | Linux downloader and isolated tool setup |
| `harness-codex-{version}-linux.tar.gz` | Generator, CLI and source installer |
| `SHA256SUMS` | Checksums of the downloadable assets |
| `build.json` | Exact HarnEX source commit and platforms |

Linux publication requires installation, upgrade and official TUI/production-adapter checks. These establish tested behavior with synthetic model responses, not paid account compatibility, model quality or token savings. The installer verifies the archive automatically. For manually downloaded Linux assets, download the matching `SHA256SUMS` and use `sha256sum --check --ignore-missing SHA256SUMS` in the download directory; confirm an `OK` result for each selected asset. Windows users can compare `Get-FileHash -Algorithm SHA256` results with the matching manifest. Interactive Linux `codex` launches offer updates for published Codex and HarnEX releases before opening a conversation; downloads require your selection.

Use `harnex uninstall` to review tool removal and confirm with Enter, `y` or `yes`; decline with `n` or `no`. Project harnesses and native conversation history are preserved.
