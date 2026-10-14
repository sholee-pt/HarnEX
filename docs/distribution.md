# Release assets and verification

Each [GitHub Release](https://github.com/sholee-pt/HarnEX/releases) contains installation instructions and version changes directly in its body.

| Asset | Platform | Purpose |
| --- | --- | --- |
| `install_harness_codex.sh` | Linux | One-command downloader and checksum verifier |
| `harness-codex-VERSION-linux.tar.gz` | Linux | Generator, management CLI, Auto adapter and source installer |
| `install_harness_codex.ps1` | Windows, when separately published | PowerShell downloader and checksum verifier |
| `harness-codex-VERSION-windows.zip` | Windows, when separately published | Generator, management CLI and source installer |
| `harness-codex-ui-VERSION-windows-x86_64.tar.gz` | Windows, when separately published | Matching native Codex package with Auto and Windows helpers |
| `SHA256SUMS` | Published platforms | SHA-256 digests of the downloadable payloads and installers |
| `build.json` | Published platforms | Exact HarnEX source commit and build metadata |

The [v0.35.3-beta release](https://github.com/sholee-pt/HarnEX/releases/tag/v0.35.3-beta) contains all seven assets after successful [Linux](https://github.com/sholee-pt/HarnEX/actions/runs/38237923067) and [Windows](https://github.com/sholee-pt/HarnEX/actions/runs/38240636795) verification, from source commit `d3cf44d67cfbfb0084bee3a5bce87a3cd6971616`. Later documentation commits do not replace that release source.

On Linux, official Codex packages are fetched separately from `openai/codex` during integration setup and confirmed updates. They are neither rebuilt nor repackaged as Harness-versioned UI assets. Windows uses the separately built version-matched native package. Source snapshots generated automatically by GitHub are not the release installers.

## Maintainers

Build with `conda run -n harness python build/build_release.py --output PATH` from clean committed source. The default emits Linux assets only. Local inspection may use `--allow-dirty`; these artifacts cannot claim an immutable source commit. `build/release_notes.py` combines the current changelog section with `docs/release-installation.md`. Published release text is a copy, not a live Markdown-file link.

The Linux publisher requires exactly its installer, archive, `SHA256SUMS` and `build.json`. Before any GitHub request, it checks bounded regular files, both asset digests against the checksum manifest and build report, archive paths and limits, and the complete payload against the selected clean checkout's immutable source. It uploads a private copy of those verified bytes and preserves existing version tags. Source downloads and provenance checks archive only declared distribution/runtime paths, so unrelated documentation and fixtures do not consume runtime archive limits.

Repeated installed-status checks still re-read and hash every managed file, receipt and launcher. Only successful syntax/import analysis of an identical verified source hash is reused in a bounded process-local cache; local changes or a different source hash receive the existing ownership checks and fresh analysis.

After confirming successful publication and the Linux installer asset, update the README's **Latest release** label and Linux installation URL to that version in a `[Doc]` commit without a version bump. Update the Windows installation URL only after its separate publication succeeds; it may remain on an older version. Keep these blocks pinned to published assets while the development branch advances. Create each release with its version tag from the start; retain older version tags, assets and their version-specific installation instructions when publishing the next release. Do not rename or move version tags to track the latest release.

Checks and releases are currently on a manual hold: branch pushes do not start Actions. When authorized, dispatch the current branch's Linux workflow with `publish` disabled for checks or enabled for release. Publication requires generation/apply, installer, ownership, uninstall, immediate-previous-version upgrade checks and the official Linux terminal/production-adapter gate. The latter resolves the latest official stable package at run time, verifies its digest, exercises Auto with a synthetic local model provider, and checks that binary bytes remain unchanged. It requires the Auto menu and actual selected model/reasoning in the footer and provider requests, plus native resume/fork picker transitions without replaying inference. Failure blocks publication. No Rust compilation is part of this Linux workflow.

This establishes tested terminal and protocol behavior, not paid account compatibility, model quality, token savings or all future Codex APIs. Runtime capabilities are checked at launch, with an explicit native-mode fallback. The retained `build/native_ui` code and its tests support legacy package ownership and Windows native builds; they are not the current Linux release path.

Each Windows release requires explicit authorization for that release only. The separate `windows-release.yml` workflow takes the exact 40-character Linux source commit, validates Windows installation/PATH/uninstall and immediate-previous-version upgrades, runs native TUI/extension tests, and builds the matching Windows executable. Publication requires an already published Linux release with the same version and source commit. It adds three Windows assets and merges checksums/build metadata while preserving Linux payloads and the version tag; existing Windows assets with different bytes are refused. Windows success does not establish Linux adapter feature parity, paid model quality or Graft support. See [platform-specific installation](installation.md).

The Windows workflow ref selects a separate validation checkout. Its resolved commit must match `source_commit` outside `test/` and `.github/workflows/windows-release.yml`; only those validation changes may differ. Even a later documentation-only commit fails that identity guard. Check the resolved ref and diff before dispatch instead of assuming the newest development branch can supplement an older Linux release. Both checkouts must remain clean; the native executable is built from `source_commit`, not from the validation checkout.

Interactive prelaunch checks display their progress. Native fallback guidance explicitly identifies both unavailable features—HarnEX Auto and `/harnex/` management—and supplies terminal commands for the selected project. These messages do not change Codex arguments, settings or permissions, and do not add checks to help, automation or disabled update channels.

The Linux workflow publishes `Harness / verification` and `Harness / release` commit statuses against its exact `GITHUB_SHA`. The Windows workflow publishes `Harness / Windows release` against the selected source commit. A release alone does not create a commit checkmark or transfer passing statuses to later commits. Cancelled, skipped or failed required jobs cannot produce a successful release status. After dispatch, provide the Actions link and stop; the repository owner checks progress. Do not poll, watch or schedule monitoring without a new request.
