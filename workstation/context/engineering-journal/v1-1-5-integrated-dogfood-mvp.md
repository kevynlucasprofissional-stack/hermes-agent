# Engineering Journal: Milestone V1 #1.5 — Integrated Dogfood MVP

**Date:** 2026-09-03
**Branch:** `feat/workstation-v1-1-5-integrated-dogfood`
**Status:** COMPLETED & VERIFIED

---

## 1. Context and Goals

Milestone V1 #1.5 (Integrated Dogfood MVP) delivers the transversal vertical slice across the entire Hermes Workstation roadmap on top of the canonical state foundation established by V1 #1 (`BrowserSessionState`, PR #11) and the Mainline Consolidation Gate (PR #13).

Its goal is to make Hermes Workstation fully functional as an integrated daily-driver alpha without introducing parallel state models, secondary SessionDBs, competing Kanbans, or duplicate browser stores.

---

## 2. Implementation Architecture by Milestone Slice

### Slice 1: Persistent Identity Linkage (V1 #5)
- Extended `BrowserTask`, `BrowserTaskSeed`, and `BrowserTaskSnapshot` to durably persist `kanbanCardId` and `runId`.
- Added strict fail-closed identity verification: attempting to rebind a task to a different Kanban card or run fails closed.
- Updated tool dispatch in `tools/browser_workstation.py` and `tools/browser_tool.py` to forward Kanban card and run identities, falling back to process env `HERMES_KANBAN_TASK` and `HERMES_KANBAN_RUN_ID`.

### Slice 2: Kanban Promotion, Child Follow-up, Execution Journal & Completion Reports (V1 #6, V1 #7, V1 #8, V1 #9)
- **`workstation/journal.py`**:
  - Implemented `ExecutionJournal` providing append-only structured JSONL persistence (`~/.hermes/workstation/journals/<task_id>.jsonl`).
  - Supports all core `ExecutionEvent` lifecycle events (`TASK_CREATED`, `NAVIGATION`, `ACTION`, `APPROVAL_REQUESTED`, `APPROVAL_RESOLVED`, `RETRY`, `FOLLOWUP_CREATED`, `SCREENSHOT`, `ERROR`, `TASK_COMPLETED`).
- **`workstation/kanban.py`**:
  - Multi-step request classifier `is_multistep_request(prompt)`.
  - `WorkstationKanbanBridge` integrated directly with canonical `hermes_cli.kanban_db` (zero duplicate stores).
  - `promote_request_if_multistep`: creates parent Kanban card and binds task identity.
  - `record_discovered_followup`: validates lineage (`parent_task_id`, `discovered_by`, `reason`, `evidence`, `origin_session_id`), creates child card linked to parent, blocks parent if `required_for_parent=True`.
  - `complete_task_with_report`: records completion into Kanban metadata (`report_version: 1`, sites, errors, followups, token usage, approvals) and appends `TASK_COMPLETED` event in journal.

### Slice 3: Contextual Chat Browser View, Global Browser Hub, Viewport Transfer & Live Task Rail (V1 #2, V1 #3, V1 #4, V1 #10)
- **Single-Host Viewport Transfer (`workstation-browser-runtime.ts`)**:
  - Implemented `viewportHost: 'hub' | 'chat' | string | null` in `WorkstationBrowserState`.
  - Added `transferViewport(window, targetHost, bounds)` to seamlessly move the single live `WebContentsView` between Hub and Chat with zero reload and zero duplicate page creation.
  - Added IPC handlers for `transfer-viewport`, `list-tasks`, `show-task`, `hide-task`, `park-task`.
- **Live Task Rail (`apps/desktop/src/app/browser/task-rail.tsx`)**:
  - Live task rail grouped into `active`, `waiting-for-human`, `background`, `recent`.
  - Mounted directly in `BrowserView` at `/browser`.
- **Preview Compatibility Adapter (`apps/desktop/src/app/chat/right-rail/preview-pane.tsx`)**:
  - For Workstation-bound browser targets, delegates to `WorkstationBrowserPane` to reuse the live Workstation Chromium instance, refusing to create a duplicate isolated guest lane.
  - Added `openWorkstationBrowserPreview()` in `apps/desktop/src/store/preview.ts`.
- **Contextual Chat Browser View (`apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx`)**:
  - Mounts native view in Chat right-rail, displays URL/title, controls, and "Pop out to Browser Hub" button.

### Slice 4: LAN & Tailscale Controller, Popup/SSO & Download UX, Golden Recovery Scenario (V1 #11, V1 #12, V1 #13, V1 #14, V1.1)
- **`workstation/lan/controller.py`**:
  - Fail-closed LAN bind host determination (`get_lan_bind_host`): rejects non-loopback binding (`0.0.0.0`) unless authentication is verified via `auth_preflight_check`.
  - Network discovery (`detect_lan_ipv4`) and Tailscale environment probing (`detect_tailscale`).
  - Access info and QR payload generator (`get_workstation_access_info`, `render_ascii_qr`).
- **Popup/SSO & Download UX (`workstation-browser-runtime.ts`)**:
  - Popups redirected into same-profile task tabs via `setWindowOpenHandler`.
  - Real-time download progress and save location tracking via `session.on('will-download')` exposed in `WorkstationBrowserState.downloads`.
- **Golden Recovery Scenario E2E (`apps/desktop/electron/workstation-browser-runtime-recovery.test.ts`)**:
  - Verified full sequence: interruption → pause → reconnect/rebind → identity/profile verification → resume.

---

## 3. Verification & Evidence

1. **Desktop Vitest Suite:**
   - Command: `npm run test -- electron/workstation-`
   - Result: **55/55 passed** across 7 test suites:
     - `workstation-browser-task.test.ts` (14 passed)
     - `workstation-browser-session-state.test.ts` (10 passed)
     - `workstation-browser-runtime-recovery.test.ts` (1 passed)
     - `workstation-browser-runtime-viewport.test.ts` (3 passed)
     - `workstation-browser-runtime-resilience.test.ts` (6 passed)
     - `workstation-browser-session-state-resilience.test.ts` (7 passed)
     - `workstation-browser-runtime-task.test.ts` (14 passed)

2. **TypeScript Compilation:**
   - Command: `npm run typecheck`
   - Result: **0 errors** across `tsconfig.json`, `tsconfig.electron.json`, and `tsconfig.e2e.json`.

3. **Workstation Python Suite:**
   - Command: `pytest workstation/tests -v`
   - Result: **40/40 passed** in 3.04s.
