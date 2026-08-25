# Hermes Workstation downstream distribution

This fork carries an integrated Workstation layer under [`workstation/`](workstation/).

The Workstation is **upstream-first**: Hermes Sessions, Gateway, Kanban, Memory,
Skills, Desktop and Dashboard remain the single sources of truth. The first
downstream feature is a first-class in-app Chromium Browser hosted by Hermes
Desktop itself.

Start here: [`workstation/README.md`](workstation/README.md).


## Apply after extracting this patch at the repository root

```powershell
.\workstation\install.ps1
.\workstation\doctor.ps1
.\workstation\start.ps1
```

Use `install.ps1 -InstallDependencies` only when Python/Node workspace dependencies need to be installed. The installer is idempotent and records its core integration through stable anchors rather than replacing the Hermes source wholesale.
