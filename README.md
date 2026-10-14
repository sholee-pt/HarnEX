<h1 align="center">HarnEX <img src="https://img.shields.io/badge/Beta-F59E0B.svg?style=flat-square" alt="Beta" height="24"></h1>

<p align="center">
  An enhanced Codex experience, powered by project-aware harness orchestration.
</p>

<p align="center">
  <a href="https://github.com/sholee-pt/HarnEX/tree/v0.36.3-beta"><img src="https://img.shields.io/badge/Version-v0.36.3--beta-2563EB.svg?style=flat-square" alt="Version: v0.36.3-beta"></a>
  <a href="https://github.com/sholee-pt/HarnEX/actions/workflows/codex-beta.yml"><img src="https://github.com/sholee-pt/HarnEX/actions/workflows/codex-beta.yml/badge.svg?branch=v0.36.3-beta&amp;event=workflow_dispatch" alt="Linux verification and release status"></a>
  <a href="#agent-editions"><img src=".github/badges/agent-codex.svg" alt="Agent: Codex"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-64748B.svg?style=flat-square" alt="License: Apache 2.0"></a>
</p>

<p align="center">
  <a href="environment.yml"><img src="https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.11"></a>
  <a href="#installation-guide"><img src=".github/badges/platform.svg" alt="Platform: Linux and Windows"></a>
</p>

<p align="center">
  <a href="#for-linux">Linux install</a> &middot;
  <a href="#for-windows">Windows install</a> &middot;
  <a href="#quick-start">Quick start</a> &middot;
  <a href="https://github.com/sholee-pt/HarnEX/releases">Release</a> &middot;
  <a href="CHANGELOG.md">Changelog</a>
</p>

**HarnEX extends the experience inside Codex with guided project setup, in-conversation management, project switching and optional Auto model selection.** On Linux, these controls work through an adapter around the unmodified official Codex terminal, preserving its conversations, renderer, history and permission controls.

Behind that experience, HarnEX brings its own project-analysis, orchestration and safe-update logic. It derives agents and skills from workspace evidence, distinguishes direct work from delegation and coordination, and materializes validated plans before applying changes with ownership and hash checks. One shared project harness keeps those decisions consistent across plain folders, Git worktrees and workspaces containing multiple repositories.

| Layer | What HarnEX adds |
| --- | --- |
| Inside Codex on Linux | `/harnex/` menus, guided setup, local status, project preferences, queued project switching and update choices |
| Project harness | Project-specific instructions, evidence-based agent/skill selection and task-level orchestration contracts |
| Controlled changes | Deterministic plan generation, validation, ownership checks, recoverable changes and opt-in maintenance |
| Optional assistance | Auto model/effort routing, local Graft retrieval and separately configured Jev advice |

Windows uses a separate native package and terminal management commands; it does not yet provide Linux's in-conversation management adapter. Routing rules and structural checks do not establish measured cost or quality gains. See [architecture](docs/architecture.md), [management](docs/management.md) and [routing](docs/routing.md).

**Development source:** v0.36.3-beta skips the reuse/reset prompt when only shared PATH registration remains after uninstall; these changes are not yet published as release assets.

**Beta releases:** Linux **v0.36.1-beta** is published with the `harnex` command and `/harnex/` controls. No Windows assets are currently listed in the published releases. The previously verified v0.35.3-beta Windows release is no longer available at its release URL.

## Installation Guide

### For Linux

**Latest published Linux release: [v0.36.1-beta](https://github.com/sholee-pt/HarnEX/releases/tag/v0.36.1-beta)**

```bash
curl -fsSL https://github.com/sholee-pt/HarnEX/releases/download/v0.36.1-beta/install_harnex.sh | sh
harnex --version
```

Previous releases retain their version tags and installation commands on the [Releases page](https://github.com/sholee-pt/HarnEX/releases). Starting with v0.36.0-beta, standalone installers are named `install_harnex.sh` and `install_harnex.ps1`; use them only after the corresponding platform assets are published.

For source installation or development, clone the **v0.36.3-beta** branch:

```bash
git clone --branch v0.36.3-beta --single-branch https://github.com/sholee-pt/HarnEX.git HarnEX
bash HarnEX/installer/install.sh
harnex --version
```

For an existing installation, select `reuse` to retain its settings. HarnEX replaces the owned `harness-codex` command with `harnex`; the old command is removed, so update any scripts that call it. Existing project files, storage and credentials remain in place. A user-owned `harnex` command or modified old launcher is preserved and reported as a conflict. Run the Linux release installer above or install from source to cross the repository rename: older release updaters reject GitHub API redirects. See [migration details](docs/installation.md#harnex-name-and-command-migration).

Supports Linux x86_64 and aarch64. Source cloning requires Git; installation requires curl, Bash, tar and sha256sum. The installer validates the tool payload, prepares an isolated Python 3.11 environment and Git, installs the command in `~/.local/bin`, and registers PATH in `~/.bashrc`. Published release installation additionally verifies its archive checksum. No sudo is required. After installation, press Enter or type yes to open a new Bash with ~/.bashrc loaded. Exit returns to the original shell. To stay in the original shell instead, run `source ~/.bashrc` yourself. Redirected installation skips this prompt.

### For Windows

**Windows x86_64:** No downloadable Windows release is currently available on the [Releases page](https://github.com/sholee-pt/HarnEX/releases). To preview the HarnEX management CLI from source, run in 64-bit PowerShell under your normal script execution policy:

```powershell
git clone --branch v0.36.3-beta --single-branch https://github.com/sholee-pt/HarnEX.git HarnEX
& ./HarnEX/installer/install.ps1
harnex --version
```

The matching v0.36.3-beta Windows native package has not been published. Full Windows integration requires that separate release; source installation alone does not provide it. Existing installations can retain their verified Windows package while waiting for a compatible published update.

When a Windows release is available, its standalone installer verifies the ZIP, prepares an isolated Python 3.11 environment and Git, and registers the command in user PATH. First project setup requires an already installed Codex CLI with working account/provider access: HarnEX runs that CLI before installing its own Windows integration. Use an interactive PowerShell terminal. If `codex` resolves to a `.cmd` or `.bat` wrapper, select the actual native `codex.exe` with `--codex-binary`; batch wrappers are rejected. The following full integration example requires matching HarnEX Windows assets to be published first. Replace its paths with your project, existing Markdown brief and native executable:

```powershell
harnex init --project 'C:\path\to\project' --goal-file 'C:\path\to\PROJECT.md' --codex-binary 'C:\path\to\codex.exe'
# Open a new terminal after integration changes PATH:
codex --cd 'C:\path\to\project'
```

After successful project configuration, `init/config` downloads the matching Windows native package with Auto and Windows helpers. This is separate from Linux's official-package adapter: the `/harnex/` management menu, independent official Codex updates and observed-outcome Auto advice below apply to Linux. Use terminal `harnex` commands on Windows. Graft automatic setup and persistent Jev login remain Linux-only. Windows publication requires separate authorization and validation for each release; future Linux releases do not imply Windows assets. From v0.36.1-beta, the updater selects only releases with complete assets for the current OS and architecture. Older installed updaters still require you to confirm the target's Windows files before accepting an update. See [Windows setup and updates](docs/installation.md#windows-setup-and-updates).

When migrating from 0.10.0-beta, run this installer once: its updater cannot discover the new unprefixed branches. If a verified installation exists, choose **`reuse`** to retain tool preferences or **`reset`** to reset HarnEX update preferences, its check cache and managed PATH registration. Project harnesses and unrelated settings are preserved. Shared PATH registration alone does not trigger this choice. Unattended installation accepts `--existing reuse|reset` on Linux or `-Existing reuse|reset` on Windows. See [installation options](https://github.com/sholee-pt/HarnEX/blob/v0.36.3-beta/docs/installation.md).

## Quick Start

Default Linux installation also prepares the official Codex command. Codex handles login and retains its native model, trust, sandbox and approval settings. After applying PATH, you can start setup entirely from its screen:

```bash
codex
```

Enter `/harnex/`, select **Project → Init**, choose a project directory and supply a description or Markdown path. Confirm the summary to configure that project. An existing harness offers review and update. For another directory, finish the current work and use `/quit`; HarnEX opens the target conversation and continues setup there. Use **Settings → Preferences** for project preferences, **Settings → Jev** for private login, and **Tools** for updates or uninstall. Credential entry and tool removal open their terminal flows after exiting Codex. See [in-conversation management](docs/management.md).

The terminal workflow remains available:

The configuration picker and login prompts described below apply to terminal
`harnex init`. In the Codex menu, configuration uses the current conversation
settings; use **Settings → Preferences** for maintenance/routing and **Settings → Jev → Login** for credentials.

```bash
cd /path/to/project
harnex init --goal-file PROJECT.md
# Press Enter after init to open Bash with ~/.bashrc loaded.
# Or stay in the current shell and run: source ~/.bashrc
codex
codex resume
codex resume --last
```

`PROJECT.md` is an optional UTF-8 Markdown brief describing the project's purpose, responsibilities and constraints. When `--goal-file` is supplied, the file must already exist and contain nonempty Markdown; a relative path is resolved from the calling terminal's directory, not from `--project`. `init` uses Codex to inspect the project and create its harness, showing live stages and elapsed seconds instead of the internal setup prompt. Native approval requests and additional questions remain visible. It then validates the resulting files. For an existing harness, `init` without a brief retains generated artifacts and skips the configuration conversation; supplying `--goal` or `--goal-file` requests a reviewed update. You can also provide a short description with `--goal "..."`, or omit both brief options.

On Linux, `init` also prepares local Graft retrieval and enables Jev shadow advice automatically. The first setup downloads Graft's isolated runtime; subsequent projects reuse it. If no TypeSafe key is available, init guides you to its key page and accepts hidden input once, saving it for later projects without shell exports or restart. A newly entered key uses one small authentication request; existing credentials make no init API call. You can skip login and continue ordinary retrieval. Eligible Jev queries may send bounded code snippets to TypeSafe. Use `--retrieval off` to skip both setups, or `harnex jev disable` to keep only local retrieval. Explicit opt-outs survive repeated init. See [retrieval controls](docs/retrieval.md) and [Jev authentication and behavior](docs/jev.md).

Choose **Codex defaults** or **Manual** with the arrow keys and Enter. Codex defaults uses the recommended model and reasoning from your Codex catalog for configuration; it does not enable per-request HarnEX Auto routing. Manual offers the available models, reasoning levels and permissions. `--settings auto|manual|native` selects a mode directly. Three concise stages show configuration progress and file validation. Questions and approvals stay visible. See [session settings](docs/sessions.md#session-settings).

After successful setup, interactive `init` offers two project preferences: **maintenance** (`off`, `suggest`, `auto`) and **observed-outcome advice for Auto** (`off`, `on`). Each menu explains its effect; Enter keeps the current setting. New projects start with both off. Maintenance reviews can use conversation tokens; local Auto advice makes no extra model call and needs recorded quality feedback. Its observation and selection path requires the Linux adapter; enabling the preference does not add it to the Windows native package. Change either later with `harnex maintenance --mode suggest` or `harnex routing --adaptive on`. These commands and status checks are also listed in `.harness/GUIDE.md`. See [maintenance](docs/maintenance.md) and [Auto advice](docs/routing.md#optional-outcome-based-auto-advice).

`init` also registers and trusts only HarnEX maintenance hooks through Codex's native interface, even when both preferences are off. Trust stays ready when a project feature is enabled later; it does not enable the feature. Use `init --hook-trust manual` to leave trust unchanged. Unsupported Codex capabilities or managed restrictions produce manual guidance instead.

### Conversations and project maintenance

Inside a Linux adapter conversation, type `/harnex/status` for the boxed
dashboard or `/harnex/settings` for preferences. `/harnex/init` and
`/harnex/config` use the current conversation for generation and review.
These qualified inputs are handled by the adapter; they are not entries in the
built-in `/` completion menu. Terminal commands remain available. See
[management commands, project switching and removal](docs/management.md).

After `init`, run **`codex`** and select **Auto** at the top of `/model`.
The Linux integration downloads an unmodified official Codex release and connects its
original terminal to a local Auto adapter. The composer, colors, shortcuts,
approvals and native history remain Codex-owned. Your separately installed Codex
is preserved. Codex updates no longer require a Harness-specific Codex build.

When update checks are enabled, interactive launches check official Codex and,
for release-channel installations, published HarnEX releases. Branch-pinned
installations check only Codex; use `harnex update` to update the pinned
HarnEX source branch. The installer's `--auto-update off` policy or `HARNESS_NO_UPDATE_CHECK=1` skips both checks.
An arrow-key menu offers **update both**, **Codex only**, **HarnEX only**, or
**skip this time** when applicable. Downloads begin only after your selection,
before the conversation opens. Offline checks continue with installed files.

The model footer identifies **Auto, the selected model and reasoning level** while Auto is enabled.
Clear new tasks and complexity increases can change the selection immediately;
two consecutive clearly lighter requests allow a lower tier. Ambiguous follow-ups
keep the current selection. These are routing rules, not measured performance rankings.

For Auto to start enabled, configure with `--auto-model auto`; otherwise native
model defaults remain in effect until you select Auto. This preference is owned
by HarnEX and does not rewrite global Codex settings. The Auto integration
is currently validated on Linux x86_64. Linux aarch64 packages are resolved from
official releases but are not covered by the x86_64 terminal gate. On unsupported platforms, use
`--no-codex-integration` with a separately installed Codex; Auto is unavailable.
See [integration and routing](docs/routing.md).

| Command | Purpose and example |
| --- | --- |
| `init` | Create the project harness once: `harnex init --project PATH --goal-file PROJECT.md`. Missing project directories are created. |
| `context` | Inspect the current host or resolve an old project path after changing servers/mounts. See [portable workspaces](docs/sessions.md#shared-mounts-and-server-changes). |
| `config` | Refresh the owned generator and review the existing project harness in Codex |
| `maintenance` | Inspect opt-in maintenance; `--mode suggest` enables review notices, `--mode auto` permits bounded existing-skill corrections |
| `routing --adaptive status` | Inspect local Auto evidence; `--adaptive on` or `off` changes its use without selecting a model |
| `status` | Read-only installation, compatibility and evidence status, with a suggested next command |
| `doctor` | Read-only ownership, manifest, references and activation checks |
| `skills` | List project skills; `skills add --source PATH --dry-run` previews a reviewed local specialist skill import |
| `update --check` | Check for a newer published HarnEX release without installing it |
| `update` | Update HarnEX and migrate an existing integration; project agents and skills are reviewed separately |
| `remove` | Preview removal of the project's unchanged generated harness files |
| `reset` | Preview removal and fresh configuration of the project harness |
| `uninstall` | Preview the removal scope, then confirm with Enter or `y`; cancel with `n` |

Reports are concise by default. Add `--json` to `status`, `doctor`, update checks or previews for the complete diagnostic report. Native `codex` starts and resumes work without an artificial HarnEX activation message.

Project commands default to the current directory. Add `--project "/path/to/project"` to select another folder. `configure` remains an alias for `config`.

`init/config` validate the project after configuration; `status/doctor` perform
explicit checks. Codex reads the managed block in the active root instructions
and the project router. Source drift prompts review without preventing Codex
from starting. Detected managed-file corruption directs you to `doctor`.
One owned `.harness/GUIDE.md` is maintained during configuration. Ordinary Codex
conversations do not rewrite it. See [project lifecycle](docs/sessions.md).

### Update an existing project harness

```bash
harnex update
harnex status
# When the project generator needs updating:
harnex config
```

Compatible existing project harnesses can be reused. Source changes may require refreshing evidence; changed managed files require review. A valid status confirms file contracts, not measured model quality or token savings.

Optional maintenance can be enabled once with `harnex maintenance --mode suggest` or `--mode auto`. Successful automatic hook setup during `init` removes the need for a separate trust step. Ordinary turns do not launch an extra review model; scope growth alone never requires additional agents. See [maintenance limits and records](docs/maintenance.md).

### Remove, reset or uninstall

```bash
# Preview, then remove the project's generated harness and its generator:
harnex remove --include-generator
harnex remove --include-generator --yes

# Alternatively, review a fresh project configuration:
harnex reset
harnex reset --yes --goal-file PROJECT.md

# Remove the installed tool after reviewing the preview:
harnex uninstall --dry-run
harnex uninstall
# Enter/y/yes: confirm; n/no: cancel
```

Uninstall preserves project harnesses, native Codex conversations and pre-existing Conda environments. It removes the verified tool installation, its removable PATH registration and unchanged files in a runtime created exclusively for this installation. Added or modified files and shared PATH entries are preserved and reported. Windows finishes runtime cleanup after the command exits.

After reinstalling, run `status` in a project to recognize its retained harness. Reuse it with `codex`/`codex resume`, review it with `config`, or explicitly `reset` it. Remove project harnesses before uninstalling if you no longer need them; the tool never searches your disk to delete projects.

## Documentation

- [Native Codex integration and automatic model routing](docs/routing.md)
- [Installation, reinstall choices and troubleshooting](https://github.com/sholee-pt/HarnEX/blob/v0.36.3-beta/docs/installation.md)
- [Project and conversation lifecycle](https://github.com/sholee-pt/HarnEX/blob/v0.36.3-beta/docs/sessions.md)
- [Bounded maintenance and local records](docs/maintenance.md)
- [Optional task checkpoints and selective resume](.agents/skills/harness/references/task-checkpoints.md)
- [Optional local Graft retrieval](docs/retrieval.md)
- [Optional Jev advice, local observations and evaluation limits](docs/jev.md)
- [Dependency and optimization review](docs/optimization-review.md)
- [Beta versioning and migration](docs/versioning.md)
- [Generated structure and design](https://github.com/sholee-pt/HarnEX/blob/v0.36.3-beta/docs/architecture.md)
- [Quality evaluation and optional local evidence](https://github.com/sholee-pt/HarnEX/blob/v0.36.3-beta/docs/evaluation.md)
- [Workflow efficiency, instruction inventory and selected OMX concepts](docs/workflow-efficiency.md)
- [External specialist skills and selected upstream improvements](docs/external-skills.md)
- [Release assets and verification](https://github.com/sholee-pt/HarnEX/blob/v0.36.3-beta/docs/distribution.md)
- [Changelog](CHANGELOG.md) · [GitHub Releases](https://github.com/sholee-pt/HarnEX/releases) · [Contributing](CONTRIBUTING.md)

## Agent editions

This repository provides **`harnex`** and needs no `--agent` option. Hidden legacy Codex selectors remain accepted for older scripts. Claude integration is outside this repository; this command does not implement Claude sessions.

## License

Copyright 2026 sholee-pt. Licensed under the [Apache License, Version 2.0](LICENSE).

Third-party material remains subject to its respective copyright, license and notice terms.
