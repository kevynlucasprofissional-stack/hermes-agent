# Hermes Workstation

Hermes Workstation is a thin downstream distribution of
`NousResearch/hermes-agent`. The upstream Hermes architecture remains the source
of truth for sessions, Kanban, memory, skills, Gateway, Desktop and Dashboard.
Workstation adds tightly integrated product capabilities rather than parallel
state.

## V1 invariants

1. **One Hermes state.** No Workstation session DB, task DB or memory DB when
   Hermes already owns that state.
2. **Browser is first-class.** The Desktop exposes `/browser` directly in core
   navigation.
3. **No external Chrome dependency.** The primary Browser runtime uses the
   Chromium bundled with Electron via `WebContentsView`.
4. **Persistent browser identity.** The Browser uses a dedicated Electron
   `Session` stored outside the repository.
5. **Background capable.** Browser WebContents survive route changes. The UI
   attaches/detaches the native view; it does not destroy the browser.
6. **Fail closed after binding.** A task bound to the internal browser pauses
   and recovers there; it never silently moves to another backend.
7. **Kanban is the task source of truth.** Multistep Workstation work maps to
   Hermes Kanban cards.
8. **Risk gates.** Sensitive/irreversible browser actions require approval.
9. **Evidence and reports.** Browser work produces a journal plus structured
   completion metadata.
10. **Upstream delta stays visible.** Every core change is documented in
    `UPSTREAM_DELTA.md`.
11. **Isolated Python runtime.** Development/runtime dependencies live in the
    repo-local `.venv`; Workstation never intentionally mutates the user's
    global Python environment.

## One-click Windows dogfood

For the normal personal/dogfood path, double-click the repository-root launcher:

```text
START-HERMES-WORKSTATION.bat
```

It orchestrates the canonical steps in order:

```text
install → doctor → start
```

The launcher stops on an installation/start failure and keeps the failure visible.
After installation succeeds it starts Desktop with `-SkipInstall`, so the same run
does not execute the dependency installation a second time.

Use the individual commands below when debugging or when you intentionally want
to run a single phase.

## Windows bootstrap

From the root of the Hermes fork, use the `.cmd` launchers. They start Windows
PowerShell with `-ExecutionPolicy Bypass`, so the first run does not depend on
the machine's script execution policy:

```bat
workstation\install.cmd
workstation\doctor.cmd
```

Dependency installation is the normal installer path. `-InstallDependencies`
remains accepted for backwards compatibility; `-SkipDependencies` is the explicit
fast/diagnostic override when dependencies are already prepared and should not be
touched.

The installer creates/reuses `.venv` at the repository root and installs Hermes
there in editable mode. `.venv` is already ignored by Git. Node workspaces remain
managed by `npm ci`.

Then start Desktop development with:

```bat
workstation\start.cmd
```

`start.cmd` prepends `.venv\Scripts` to `PATH` and sets `VIRTUAL_ENV`/
`HERMES_PYTHON` before starting Electron, so the Desktop resolves this checkout's
Hermes backend instead of a global Python installation.

The one-click launcher uses the internal orchestration flag:

```bat
workstation\start.cmd -SkipInstall
```

Only use `-SkipInstall` after a successful install in the same orchestration or
when you deliberately know the checkout dependencies are already prepared.

The PowerShell entrypoints remain available when needed explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\workstation\install.ps1
```

The installer selects an available Python 3.13/3.12/3.11 through the Windows
`py` launcher when possible, validates every core patch anchor before writing,
and checks native-command exit codes. Dependency installation requires Hermes'
current Python range `>=3.11,<3.14` and Desktop requires Node `>=22.22.0` (the
repository `.nvmrc` selects Node 26; CI validates with Node 26).

## Browser integration

The initial patch provides a functional in-app Chromium Browser surface **and**
a loopback-authenticated controller used by Hermes `browser_*` tools. Internal
Chromium is the first browser lane; the official extension router and legacy
backend are fallback lanes only while routing is enabled and the task has not
bound to the persistent internal browser.

Automatic Kanban promotion/orchestration, LAN settings UI and durable Execution
Journal persistence are later integrations. The roadmap now schedules an
**Integrated Dogfood MVP** after complete BrowserSessionState: minimal real
vertical slices of those later capabilities are implemented first for continuous
usage, while the original milestones remain in place for subsequent architectural
hardening.

See `ARCHITECTURE.md`, `ROADMAP.md`, and `UPSTREAM_DELTA.md`.
