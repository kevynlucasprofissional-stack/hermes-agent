# Current State

Snapshot date: 2026-08-29. Downstream `main` remains at Implementation 3 (`ce78f120e8ed2974d6174e475cc7572afcfe41e0`). Implementation 4 is on PR #9 / branch `impl4-browser-task-lifecycle` and has now passed its required real-Windows BrowserTask lifecycle smoke. Promotion still depends on final-head automated gates, documentation/upstream-delta closure, and final audit.

This file describes **observed implementation state**, not the target architecture. When it disagrees with code on current `main` or an explicitly named candidate branch, inspect the code and update this file.

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

## Implementation 4 candidate — BrowserTask lifecycle

The candidate formalizes BrowserTask without replacing the existing Chromium ownership primitives:

- `BrowserTask` is a first-class logical lifecycle object with `create`, `show`, `hide`, `park`, and explicit `destroy` semantics.
- `taskTabs` plus `BrowserEntry.ownerTaskId` remain the authoritative in-process task → live-page binding; BrowserTask metadata does not create a second page store.
- Repeated creation for the same `taskId` is idempotent and does not allocate a second live task page.
- Within one Electron process, `hide` and `park` preserve the task page; later `show` re-exposes the same live `WebContents` and current URL.
- Showing another BrowserTask parks the previously visible BrowserTask.
- `destroyTask` is distinct from hide/park and explicitly removes the logical task and closes its owned page.
- Missing/crashed task pages may recover with exactly one replacement page while preserving logical task identity and recording `recoveryState: recreated`.
- Safe BrowserTask metadata is versioned and atomically persisted under the Workstation runtime directory.
- Restart restores logical task metadata as `parked` / `recoveryState: restored` before any task page is recreated. First use/show lazily creates one replacement page under the same `taskId`.
- Restart recovery does **not** claim that a process-local `WebContentsView`, renderer JavaScript heap, or object identity survives application restart.

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

## Partially implemented / future work

Implementation 4 does **not** complete the later browser product architecture:

- complete BrowserSessionState for ordinary/manual tab ordering, active generic tab, richer URL/title restoration, and controller/session/run/Kanban linkage;
- Browser Hub groupings and contextual Chat Browser View;
- one-host transfer contract for moving the same live `WebContentsView` between Chat and Browser Hub;
- Preview compatibility that reuses the same BrowserTask/runtime instead of maintaining a separate browsing lane;
- full Chat ↔ Browser Hub ↔ Preview resize/host-transfer E2E;
- complete session/run/Kanban/controller linkage for BrowserTask metadata.

These remain future implementations and must not be inferred as complete from the narrower Implementation 4 smoke.

## Known bugs / gaps

See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). The main remaining browser gaps after Implementation 4 are duplicate Preview/Browser lanes, incomplete BrowserSessionState, host ownership/composition, missing Chat/Hub shared-host surfaces, and pre-existing Windows portability/test assumptions in broad Desktop suites.

`Session not found` / exported `session: null` remains a separate causal track and is not established as the Browser root cause.

## Latest automated validation state

The code-bearing BrowserTask candidate is rooted at `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`. The native smoke above ran on a later head containing only Workstation validation-memory/probe changes after that code-bearing candidate.

During the candidate cycle:

- focused BrowserTask lifecycle tests passed;
- runtime-adapter tests passed;
- Workstation CI passed;
- Docker validation passed;
- Desktop typecheck and committed-source/install/checkout-clean Windows steps passed;
- broad Windows Desktop UI/platform suites retained the documented KI-006 baseline failure classes and therefore remained red rather than being weakened or hidden.

After final documentation closure, automated gates must be observed on the exact final PR head. Native evidence may be carried from `d8acc752...` only if Git comparison proves that the relevant product code and executed H-004 probe are unchanged after that smoke.

## Promotion status

Implementation 4 is **technically accepted but not yet promoted**.

Remaining promotion steps:

1. finalize canonical documentation and `UPSTREAM_DELTA.md`;
2. prove the final head differs from the H-004 smoke SHA only in documentation for the relevant behavior/probe paths;
3. observe relevant automated gates on the exact final head and preserve KI-006 classification without masking failures;
4. perform final PR audit;
5. mark PR #9 ready and merge only if all gates remain satisfied.
