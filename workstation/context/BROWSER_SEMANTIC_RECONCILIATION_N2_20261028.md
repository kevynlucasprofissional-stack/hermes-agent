# BROW-N2 — Semantic Browser readback and durable reconciliation diagnostics (2026-10-28)

## Status

**IMPLEMENTED LOCALLY / RELEASE HOLD.** Maintainer authorized skipping H-079 Stage A **for this mission's local development only**. No qualified exact-head CI, live native Electron E2E, WhatsApp send test, browser restart, operator-approved reconciliation, Git commit, branch or push.

Checkout: `C:\Github\hermes-agent`, `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`. Existing dirty files and other agents' work were preserved.

## Real incident and strength of evidence

The **live production ledger was read, not modified**. Incident session/task/run `20261028_112711_256509`; operation `op_browser_batch_actions_3d591fa7f8da` has neither parent ACK nor terminal. Last child receipt was `:0` (`browser_click`), `kanbanCardId=null`, task `parked`.

Proven class of defects: the old verifier accepted click toggles only; it could not verify an explicit local selection, a focused keyboard selection, or scroll inside an internal pane. It also published a child BrowserOwnerReceipt before checking the independent readback or owner lease. Existing session-state merges could erase a previously reconciled terminal when a stale writer saved its snapshot.

**Unproven:** whether these particular verification reasons caused the exact 11:46 event; no persisted outcome reason existed then. No inferences about external WhatsApp deliveries or Kanban causality. The unacknowledged operation must remain fenced until independently inspected and human-approved.

## Changes

- `apps/desktop/electron/workstation-browser-batch-proof.ts`: ephemeral readback adds `aria-selected`, focus, and center-wheel scroll-container identity and `scrollTop`. Verifies `selected` only on same document and same referenced element, with explicit typed postcondition; focused Enter selection is local-only and cannot prove a send. Panel scroll accepted only when the **same scroll container** moves in the requested direction. Generic Enter/composer clearance remains unverified.
- `apps/desktop/electron/workstation-browser-batch.ts`: typed optional `postcondition: {kind:'selected'}` for click, or for press with bound ref. Rejects malformed postconditions.
- `tools/browser_tool.py`: model-facing `browser_batch_actions.steps[].postcondition` schema, limited to `selected`; no delivery postcondition.
- `apps/desktop/electron/workstation-browser-runtime.ts`: before a selected Enter dispatch, requires the bound target to have focus. A child owner receipt is issued **only** after independent proof and retained BrowserTask authority. Unverified steps return null receipt and retain the pending parent fence; successful parent ACK P01 is unchanged. Uncertain outcomes request canonical durable diagnostic recording, without auto-reconciliation.
- `apps/desktop/electron/workstation-browser-session-state.ts`: `recordBatchUncertainty` persists only sanitized reason, steps, stop index and time under existing admission lock/fsync. Readers and stale writers cannot remove that pending diagnostic or erase immutable `RECONCILED` terminals. No new authority or secondary database.
- Regression tests in `workstation-browser-batch-proof.test.ts`, `workstation-browser-runtime-batch.test.ts`, `workstation-browser-session-state.test.ts` and `tests/tools/test_browser_batch_semantic_contract.py`.

## RED → GREEN evidence

1. Semantic readback Vitest: originally 3 RED cases (local selection, focused Enter selection, internal-pane scroll), now green.
2. Runtime proof: originally RED because an unverified click minted child receipt; now verified to retain null receipt and pending admission. Synthetic selected conversation completes parent ACK, survives runtime reconstruction, and permits a new navigation. Synthetic internal-pane wheel verified.
3. Diagnostic persistence: originally RED (missing method); now reason is durable after restart while the fence remains. Stale writer terminal collision: originally RED (RECONCILED lost); now terminal is retained.
4. Tool schema pytest: originally RED KeyError `postcondition`; now green.

Final focused checks:
- Electron Vitest, eight files: **71 PASS / 0 FAIL**. Nonfatal test-mock stderr `session.fromPath is not a function` in P0A suite, despite overall PASS.
- Python pytest (`test_browser_batch_semantic_contract.py` + `test_whatsapp_browser_tools.py`): **35 PASS / 0 FAIL**.
- TypeScript `tsc -p tsconfig.electron.json --noEmit`: exit 0.
- Kanban UI Vitest, ten files: **79 PASS / 0 FAIL**. Warnings about React `act` and Node localStorage test environment.
- Targeted `git diff --check` over changed runtime/proof/tool files returned no findings. Repository-wide `git diff --check` reports a pre-existing trailing blank-line issue in `workstation/dogfood/Prompts.md` and CRLF warnings; not edited.

These checks run in isolated temporary state, without sending WhatsApp messages or changing the live Browser admission ledger.

## Risk and boundaries

- An explicit `selected` postcondition is a **local UI selection** proof, never an external send/delivery ACK. It requires an element with observable `aria-selected`; WhatsApp's actual DOM may not expose this attribute or may replace the referenced element. If absent or replaced, the system fails closed.
- An uncertain batch remains fenced; timeouts, blind retries, checksum bypass, TTL admission expiry, or synthetic operator approvals are prohibited.
- `browser_admissions_inspect` exists as read-only inspection; `browser_admissions_reconcile` exists but current controller accepts caller-supplied review metadata. **This mission has NOT established a cryptographically authenticated human review channel or causal independent readback for the historical operation.** Do not call that mutation with fabricated evidence.
- Active desktop runtime has not been rebuilt/restarted. New source changes do not imply that the open live process uses them.

## Next highest-priority qualification gate

Implement and verify a native, strictly read-only site-specific semantic readback for WhatsApp conversation selection, using test fixtures first. Prove independent identity and ownership at the target page without exposing contacts/messages, then test renderer restart, parked-task recovery and authorized human review of a synthetic uncertain operation. Verify a real human approval boundary before opening any mutable reconciliation route to an agent. Keep Stage A/CI and release HOLD until explicitly qualified. The historical production operation remains unresolved.


## Additional lint/gate note

Targeted ESLint completed with **0 errors / 106 formatting warnings** (many in pre-existing Workstation WIP; no automatic --fix to preserve other agents' edits). Ruff could not run because the current Python environment reports `No module named ruff`; the Python test import and 35 relevant pytest cases passed. Full project test matrix, exact-head CI, upstream Stage A and native authenticated Browser evidence remain unqualified. No Git mutation was performed.
