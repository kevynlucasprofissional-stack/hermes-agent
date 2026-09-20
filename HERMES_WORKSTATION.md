# Hermes Workstation downstream distribution

This fork carries an integrated Workstation layer under [`workstation/`](workstation/).

The Workstation is **upstream-first**: Hermes Sessions, Gateway, Kanban, Memory,
Skills, Desktop and Dashboard remain the single sources of truth. The first
downstream feature is a first-class in-app Chromium Browser hosted by Hermes
Desktop itself.

Start here: [`workstation/README.md`](workstation/README.md).

## Engineering change protocol — upstream baseline first

For coding/maintenance work, “upstream-first” now has a strict operational meaning:
**before any downstream runtime implementation or adjustment, refresh/pin upstream,
establish a qualified upstream-aligned baseline, reconcile seams, and only then implement
the target change**.

Canonical procedure:
[`workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`](workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).

Do not continuously chase a moving upstream HEAD during the feature. Pin one exact SHA for
the cycle, qualify it, implement the target on top, then classify final upstream drift.


## Windows first run

From the repository root, prefer the `.cmd` launchers so Windows PowerShell's
execution policy cannot block the bootstrap before it starts:

```bat
workstation\install.cmd
workstation\doctor.cmd
workstation\start.cmd
```

Install the full development dependency set only when needed:

```bat
workstation\install.cmd -InstallDependencies
```

Equivalent explicit PowerShell invocation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\workstation\install.ps1
```

The installer is idempotent, validates all core patch anchors before writing,
selects a usable Python interpreter, and records its integration through stable
anchors rather than replacing Hermes source wholesale.
