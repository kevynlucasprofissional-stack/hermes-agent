# Hermes Workstation downstream distribution

This fork carries an integrated Workstation layer under [`workstation/`](workstation/).

The Workstation is **upstream-first**: Hermes Sessions, Gateway, Kanban, Memory,
Skills, Desktop and Dashboard remain the single sources of truth. The first
downstream feature is a first-class in-app Chromium Browser hosted by Hermes
Desktop itself.

Start here: [`workstation/README.md`](workstation/README.md).

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
