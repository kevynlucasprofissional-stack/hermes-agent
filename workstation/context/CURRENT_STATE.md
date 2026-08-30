# Current State

Snapshot date: 2026-08-30. Downstream `main` has promoted Implementation 4 via PR #9. The promotion merge is `fada723f43613e5e0f061cab24445573ac298998`; its parents are the previous Implementation 3 main `ce78f120e8ed2974d6174e475cc7572afcfe41e0` and the accepted PR head `75d10d35d4757496390debf8e4b4f9efb44c5432`.

This file describes **observed implementation state**, not the target architecture. When it disagrees with code on current `main`, inspect the code and update this file.

## Working now

On current `main`:

- Hermes Workstation is integrated into this downstream fork and Desktop exposes a dedicated `Browser` route.
- The internal browser runtime uses Electron Chromium through `WebContentsView` with a persistent Electron session/profile.
- Manual Browser navigation, tab creation/activation/close, back/forward/reload, pause/resume, focus, and human/agent control ownership are implemented.
- The Workstation controller is localhost-bound and token-authenticated.
- `browser_*` routing attempts the Workstation controller before fallback and preserves bound fail-closed behavior.
- Desktop Browser schema capability is session-scoped and separated from transient runtime reachability.
- The tool-definition cache fingerprints session-surface capability so Desktop schemas do not leak into TUI/CLI.
- Chromium profile state such as cookies/localStorage/IndexedDB is distinct from Workstation logical browser/task state.
- Workstation install validates committed integration without rewriting tracked source.
- BrowserTask is now a first-class logical lifecycle object with `create`, `show`, `hide`, `park`, explicit `destroy`, crash recovery, safe metadata persistence, and logical restart restoration.
- `taskTabs` plus `BrowserEntry.ownerTaskId` remain the authoritative in-process task → live-page binding; BrowserTask metadata does not create a second page store.
- Repeated creation for the same `taskId` is idempotent and does not allocate a second live task page.
- Within one Electron process, `hide` and `park` preserve the task page; later `show` re-exposes the same live `WebContents` and current URL.
- `destroyTask` explicitly removes the logical task and closes its owned page.
- Missing/crashed task pages may recover with exactly one replacement page while preserving logical task identity and recording `recoveryState: recreated`.
- Safe BrowserTask metadata is versioned and atomically persisted under the Workstation runtime directory.
- Restart restores logical task metadata as `parked` / `recoveryState: restored` before any task page is recreated. First use/show lazily creates one replacement page under the same `taskId`.
- Restart recovery does **not** claim that a process-local `WebContentsView`, renderer JavaScript heap, or object identity survives application restart.

## Implementation 4 — promoted BrowserTask lifecycle

PR #9 (`feat(workstation): formalize BrowserTask lifecycle`) was merged into `main` as `fada723f43613e5e0f061cab24445573ac298998` from accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432`.

The code-bearing BrowserTask implementation remains anchored at `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`. Later commits in the PR were validation-memory, documentation, probes, and repository-process closure; Git comparison established that the final attribution/journal closure after the controlled Windows comparison did not change BrowserTask product/runtime/probe behavior.

## Native Windows acceptance evidence

Implementation 4's required narrow native lifecycle smoke passed on Windows release `10.0.26200`, Electron `40.10.2`, outer Node `v24.14.1`, at repository head `d8acc752133b125b9619cbc7fe09199f1283a22b`.

The versioned probe is:

`workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`

Observed result:

- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

The smoke proved on real Electron/Chromium:

1. create/show/navigate produced one task-owned page;
2. hide/show retained the same `taskId`, task-owned tab id, `WebContents` identity/id, URL, and renderer sentinel;
3. park/show retained the same identity and page state;
4. explicit `destroyTask` destroyed the prior WebContents, removed the task, and left zero task-owned entries;
5. two distinct Electron PIDs proved a real process restart;
6. restart restored the same logical task as `parked` / `recoveryState: restored` with zero eager live task pages;
7. first show lazily created exactly one replacement page under the same task and changed recovery to `recreated`;
8. BrowserTask structural persistence contained neither the page URL secret nor renderer secret used by the smoke.

The native-smoke investigation also established that earlier V9 timeouts were harness defects: on this exact environment ESM top-level `await app.whenReady()` stalled, while non-blocking `app.whenReady().then(...)` reached readiness. The product runtime already uses the non-blocking pattern, so no BrowserTask product fix was required.

## Partially implemented

Implementation 4 narrows several browser-state gaps but does not complete the broader browser product architecture:

- BrowserTask metadata persists, but complete BrowserSessionState for ordinary/manual tab ordering, active generic tab, richer URL/title restoration, and controller/session/run/Kanban linkage is still incomplete.
- BrowserTask metadata has host/session/control linkage fields, but full live integration of those fields with Hermes SessionDB, Kanban, run orchestration, and controller recovery is not yet complete.
- The existing Browser route remains a conventional browser surface rather than the future Browser Hub.

## Not implemented yet

- Browser Hub groupings and contextual Chat Browser View.
- One-host transfer contract for moving the same live `WebContentsView` between Chat and Browser Hub.
- Preview compatibility that reuses the same BrowserTask/runtime instead of maintaining a separate browsing lane.
- Full Chat ↔ Browser Hub ↔ Preview resize/host-transfer E2E.
- Complete BrowserSessionState for all intended logical tabs/task linkage.
- Complete session/run/Kanban/controller linkage for BrowserTask metadata.

These remain future implementations and must not be inferred as complete from the narrower Implementation 4 acceptance.

## Manual validation already observed

Historical bootstrap validation proved that the Desktop application and dedicated Browser route can open and navigate, but it also exposed Preview/Browser lane divergence and incomplete logical restart state; those observations remain context, not proof of later lifecycle implementations.

For Implementation 4 specifically, the durable manual/native evidence is the H-004 real Windows/Electron smoke recorded above. It supersedes the earlier “native smoke missing” status for the narrow BrowserTask lifecycle contract while deliberately leaving later Chat/Hub/Preview host-transfer validation open.

Manual/native evidence and automated regression coverage remain complementary: H-004 proves the real Electron lifecycle behavior, while the pure/runtime-adapter tests protect the contract in CI.

## Known bugs / gaps

See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). The main remaining browser gaps after Implementation 4 are duplicate Preview/Browser lanes, incomplete BrowserSessionState, host ownership/composition, missing Chat/Hub shared-host surfaces, and pre-existing Windows portability/test assumptions in broad Desktop suites.

`Session not found` / exported `session: null` remains a separate causal track and is not established as the Browser root cause.

## Latest automated validation state

Promotion evidence was closed against the exact final PR head `75d10d35d4757496390debf8e4b4f9efb44c5432`:

- `Workstation CI` completed successfully;
- Docker Build/Test/Publish completed successfully;
- committed-source validation, normal Workstation install, and checkout-clean assertions passed on Windows;
- Desktop typecheck passed;
- focused BrowserTask lifecycle/runtime tests passed;
- repository contributor-attribution gate passed after the missing author-email mapping was added;
- the broad Windows Desktop workflow remained red only at its final aggregator, while scoped setup/typecheck/BrowserTask/UI/platform diagnostic steps completed.

The broad Windows red was causally classified through a controlled native-Windows side-by-side comparison of baseline `ce78f120e8ed2974d6174e475cc7572afcfe41e0` and candidate `2ffee2335b6aba071e7b63457a047cd9334d4d92`:

- baseline UI legacy: 5 failed files / 11 failed tests;
- candidate UI legacy: 5 failed files / 9 failed tests;
- baseline platform/Electron legacy: 11 failed files / 33 failed tests;
- candidate platform/Electron legacy: 10 failed files / 28 failed tests;
- every remaining candidate failure matched an identical baseline failure or a variant of the same KI-006 causal class;
- candidate-specific BrowserTask suite passed 2 files / 16 tests;
- candidate typecheck passed.

Result: `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`.

The final PR head differs from that controlled candidate only by contributor-attribution mapping plus Workstation engineering-journal material; no BrowserTask product/runtime/probe/workflow/dependency code changed. Therefore the final-head Windows aggregator red carries the established KI-006 classification and is not an Implementation 4 regression.

## Promotion status

Implementation 4 is **PROMOTED / RESOLVED**.

- PR #9 final accepted head: `75d10d35d4757496390debf8e4b4f9efb44c5432`.
- Merge commit on `main`: `fada723f43613e5e0f061cab24445573ac298998`.
- Previous `main` parent: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`.
- Native lifecycle acceptance: `H004_CLASSIFICATION=VALIDATED`.
- Windows baseline classification: `PASS_WITH_KI-006_RED`; KI-006 remains open debt and was not hidden or weakened.

Implementation 5 and later browser-foundation work may now build on the promoted BrowserTask lifecycle, but must preserve the scope boundaries above.