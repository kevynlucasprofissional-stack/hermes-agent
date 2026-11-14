# Workstation Kanban — incremental separation, 2026-11-01

## Current baseline (not promoted)
- Shared checkout: C:\Github\hermes-agent, branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e.
- origin/main ahead by 1 at inspection; upstream/main local ref 571a5911ae (2026-10-24). Shared checkout had ~293 dirty/untracked paths before this task.
- Do not reset, stash, merge, switch branches, restart Hermes, or touch other agents' dirty files.
- Existing upstream Kanban DB: C:\Users\Kevyn Lucas\AppData\Local\hermes\kanban.db, 79 tasks, no hybrid boards/cards.
- Verified consistent snapshot: C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\kanban-upstream-snapshot.sqlite; PRAGMA integrity_check=ok; SHA256 8280ac1b637b1a4b74a8708a87977760a3938befab5f703c4085c3be456b1761.

## Additive MVP implementation (uncommitted, original unaffected)
- workstation/kanban_local.py — independent SQLite schema, transactionally creates boards, columns, cards; moves and edits with revision checks. DB lives at <Hermes home>/workstation/board.sqlite.
- plugins/workstation-board/dashboard/{manifest.json,plugin_api.py} — dedicated FastAPI REST namespace /api/plugins/workstation-board, no imports from hermes_cli.kanban_db.
- apps/desktop/src/plugins/workstation-board/{api.ts,board.tsx,plugin.tsx} — bundled on-by-default route /workstation/kanban; sidebar item; create/select board, add columns/cards, drag or select move, edit details.
- tests/workstation/test_kanban_local.py — backend persistence, revision conflict, rank, HTTP contract.
- No original Kanban file was changed by this task, and the current 79 tasks were not copied/deleted/modified.

## Verification
- Python pytest tests/workstation/test_kanban_local.py: 3 passed, 1 existing Starlette deprecation warning.
- ESLint focused on new frontend files: exit 0 after --fix.
- Python py_compile on new backend files: exit 0.
- Full desktop TypeScript typecheck stalled for many minutes and was terminated; NOT qualified.
- Running Electron was not restarted, and no real native UI/browser end-to-end proof exists.
- New backend plugin requires reload/restart of the runtime to mount the router; do so only with coordinated preservation of active sessions.

## Mandatory next gate
1. Verify exact shared Git HEAD and new files, no write collisions; qualify upstream pin/baseline before promotion.
2. Run focused TypeScript check/build, verify API plugin mounted through the actual Hermes backend and native route with real create/edit/move/reopen on a dedicated test profile.
3. Reconcile all existing 79 original tasks and required agentic behavior (delegation, logs, approvals, runs) before migration; use a read-only inventory and explicit one-time importer, not a live write-through coupling.
4. Only after parity and recoverable cutover, restore the original upstream Kanban. Keep any useful integrations as optional adapters; no One State Hermes requirement.
5. Vault is already a standalone plugin; verify whether user term "Vals" means Vault or another feature before moving it.

Status: additive MVP coded and backend tested; native app not qualified. Upstream restoration NOT started.
