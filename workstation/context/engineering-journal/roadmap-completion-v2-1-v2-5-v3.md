# Engineering Journal — Roadmap Completion (V2.1, V2.5, V3)

**Date**: 2026-09-03  
**Branch**: `feat/workstation-v1-1-5-integrated-dogfood`  
**Status**: COMPLETE (100 Pytest passing, 55 Vitest passing, TypeScript clean)

---

## 1. Context & Discovery

During the `/goal` execution, remote branch inspection discovered `origin/docs/roadmap-agentic-control-plane`, which formally specified:
1. **V2.1**: Native Chrome Web Store Extensions Support.
2. **V2.5**: Agent Runtime + System Capability Control Plane (Worker Registry, System Capability Layer, System Event Pipeline, Scoped Autonomy Policy Engine).
3. **V3**: Cross-Platform Agentic Workstation (Omarchy Linux reference host, Cross-platform host adapters, Agentic Desktop Reference Tracking).

## 2. Implementation Summary

### V2.1 — Native Chrome Web Store Extensions Support
- **Downloader & Unpacker (`workstation/extensions.py`)**:
  - `ChromeExtensionManager` extracts extension IDs from Chrome Web Store URLs.
  - Downloads `.crx` packages directly from official Chromium update endpoint:
    `https://clients2.google.com/service/update2/crx?response=redirect&prodversion=128.0.0.0&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc`
  - Unpacks CRX by stripping the binary `Cr24` header and extracting the internal ZIP stream into `~/.hermes/workstation/extensions/<id>/`.
  - Reads `manifest.json`, resolves option pages, and exposes install/uninstall/list APIs.
- **Electron Session Integration (`apps/desktop/electron/workstation-browser-runtime.ts`)**:
  - `loadInstalledExtensions()` in `ensureSession()` scans the extensions directory and registers all unpacked extensions via `session.loadExtension(path, { allowFileAccess: true })`.
- **Tests**: `workstation/tests/test_extensions.py` (2 passed).

### V2.5 — Agent Runtime + System Capability Control Plane
- **Worker Registry (`workstation/workers.py`)**:
  - Normalized discovery, readiness, and bounded subtask delegation for specialized coding agents (Antigravity, Claude Code, Codex, OpenCode, K-Tools-Neo).
  - Maintains canonical Hermes task, session, and Kanban card lineage by logging subtask starts and completions to `ExecutionJournal`.
  - **Tests**: `workstation/tests/test_workers.py` (5 passed).
- **System Capability Layer (`workstation/host.py`)**:
  - Safe host capability boundary outside the browser:
    - Filesystem/workspace inspection (`inspect_workspace`)
    - Process execution with timeout and output capture (`run_command`)
    - Native clipboard read/write (`read_clipboard`, `write_clipboard`)
    - Git status inspection (`git_status`)
    - Desktop notifications (`send_notification`)
    - Machine diagnostics and disk metrics (`get_diagnostics`)
  - Providers: `WindowsHostCapabilityProvider`, `LinuxHostCapabilityProvider`, and `KToolsNeoCapabilityAdapter` (candidate adapter without becoming a hard dependency).
  - **Tests**: `workstation/tests/test_host_capabilities.py` (8 passed).
- **System Event → Hermes Task Pipeline (`workstation/events.py`)**:
  - Inverse automation direction surfacing machine events back into the canonical Hermes task model:
    - Event types: `PROCESS_CRASH`, `BUILD_FAILURE`, `BUILD_SUCCESS`, `DOWNLOAD_COMPLETED`, `REPO_STATE_CHANGED`, `CONTROLLER_HEALTH_CHANGED`, `USER_ATTENTION_REQUIRED`, `LONG_RUNNING_JOB_COMPLETED`.
    - Wakes/enriches active tasks via `ExecutionJournal`.
    - Promotes untracked critical events into Kanban tasks via `WorkstationKanbanBridge`.
    - Retains provenance, reason, and execution evidence without duplicate stores or schedulers.
  - **Tests**: `workstation/tests/test_events_pipeline.py` (4 passed).
- **Scoped Autonomy Policy Engine (`workstation/policy.py`)**:
  - Explicit scoped autonomy classifying actions into: `ALLOW`, `SANDBOX`, `REQUIRE_APPROVAL`, `DENY`.
  - Blocks dangerous destructive commands (`rm -rf /`, `format`, fork bombs) and sensitive OS path tampering (`C:\Windows`, `/etc`, `~/.ssh`).
  - Gates out-of-workspace file modifications and financial/destructive actions behind human confirmation.
  - Maintains an auditable decision log.
  - **Tests**: `workstation/tests/test_policy.py` (7 passed).

### V3 — Cross-Platform Agentic Workstation
- **Omarchy Reference Host (`workstation/omarchy.py`)**:
  - `OmarchyAdapter` detecting Omarchy Linux environment, default coding agent, system skills, and normalized agent CLI launcher without distro-specific file hacking.
- **Cross-Platform Host Manager (`workstation/cross_platform.py`)**:
  - Normalizes capability discovery, execution, and host summaries across Windows and Linux.
- **Agentic Desktop Reference Tracking (`workstation/cross_platform.py`)**:
  - `AgenticBenchmarkRegistry` evaluating 8 major harnesses (Omarchy, Hermes upstream, OpenHands, OpenCode, Claude Code, Codex, Antigravity, BrowserOS) against core architectural questions.
- **Tests**: `workstation/tests/test_cross_platform.py` (6 passed).

---

## 3. Verification Evidence

- **Pytest**:
  ```bash
  python -m pytest workstation/tests
  ============================= 100 passed in 3.47s =============================
  ```
- **Vitest**:
  ```bash
  npx vitest run electron/workstation-browser
  Test Files  7 passed (7)
  Tests       55 passed (55)
  ```
- **TypeScript Typecheck**:
  ```bash
  npm run typecheck --workspace apps/desktop
  tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit
  exited with code 0 (0 errors)
  ```
