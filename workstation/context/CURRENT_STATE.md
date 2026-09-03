# Current State

Snapshot date: 2026-09-02. The pre-V1 #1.5 consolidation audit starts from
`main@4b04f4c4d2af5620426589529d29b700cfc21fb0`, after promotion of
BrowserSessionState through PR #11 and the dogfood sequencing/launcher through
PR #12.

This file describes **observed implementation state**, not target architecture.
When it disagrees with code on current `main`, inspect the code and update this
file.

## Working now

On the consolidated line:

- Hermes Workstation is first-class in this downstream fork and Desktop exposes
  the built-in `/browser` route.
- The internal browser uses Electron Chromium through `WebContentsView` and a
  dedicated persistent Electron session/profile outside the repository.
- Navigation, ordinary tabs, task-owned tabs, background parking, pause/resume,
  focus and human/agent control primitives are implemented.
- The Workstation controller is loopback-bound and bearer-token authenticated.
- `browser_*` prefers the Workstation controller before allowed fallback and
  remains fail-closed after task binding.
- Desktop Browser schema capability is session-scoped and protected from
  process-global reachability/cache leakage.
- Workstation install validates committed integration without rewriting tracked
  source and uses an isolated repository `.venv`.
- BrowserTask has explicit `create`, `show`, `hide`, `park`, `destroy`, crash
  recovery and logical restart restoration. `taskTabs` plus
  `BrowserEntry.ownerTaskId` remain the sole in-process task-to-live-page owner.
- BrowserSessionState is one composite, versioned, atomic structural projection
  for ordinary/task logical tabs, ordering, active selection, sanitized
  restorable URL/title metadata and the BrowserTask snapshot.
- A failed atomic BrowserSessionState replacement preserves the latest intended
  in-process composite so a later successful write cannot regress the other
  half of state. Explicit task destroy remains convergent across a failed save.
- Profile-managed state (cookies/localStorage/IndexedDB and compatible login)
  remains separate from BrowserSessionState and survives through the persistent
  Electron partition.
- Restart restores safe logical metadata, parks BrowserTasks and lazily creates
  exactly one replacement page when a restored task is used. It never claims a
  process-local `WebContentsView` or JavaScript heap survives restart.
- The repository-root `START-HERMES-WORKSTATION.bat` performs canonical
  install → doctor → start and passes `-SkipInstall` only after successful
  installation so dependencies are not installed twice.
- The V1 #1.5 whole-roadmap MVP boundary is versioned in `ROADMAP.md` without
  removing the original hardening milestones.
- The extraordinary Mainline Consolidation Gate is recorded as PASS in
  `MAINLINE_CONSOLIDATION.md`; all predecessor/historical PRs and observed
  branches have a disposition, and new V1 #1.5 work must start from `main`.

## BrowserSessionState — promoted V1 #1

PR #11 accepted exact head
`d5be442021ea0c744351622317eef5212219786d` and was merged as
`e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.

The promoted state adds and protects:

1. ordinary and task logical tab coexistence, order and active logical id;
2. safe URL restoration with credential-like query/path/matrix/backslash and
   encoded pseudo-query material rejected;
3. conservative title handling and no persisted renderer/page secret values;
4. one composite persistence seam shared with BrowserTask lifecycle rather than
   a second task store;
5. one-shot migration from the former BrowserTask-only state;
6. newer-version refusal, malformed-state recovery and atomic replacement;
7. failed-write convergence in both session→task and task→session directions;
8. explicit-destroy cleanup even when persistence fails;
9. real two-process clean and abrupt restart recovery with lazy exactly-one-page
   task ownership;
10. explicit separation between structural state and Chromium profile state.

The exact-head native Windows/Electron probe emitted
`H010_CLASSIFICATION=VALIDATED`.

## Dogfood sequencing and launcher — promoted

PR #12 was reconciled with the V1 #1 promotion at accepted head
`39e51787d2414d0165ae8fa8b47d1f0e5f3e65cd` (tree `2eb3f9a7...`) and
merged as `4b04f4c4d2af5620426589529d29b700cfc21fb0`.

It promotes the MVP-first delivery contract and one-click bootstrap only. It
does **not** by itself implement the 23 V1 #1.5 slices.

## Partially implemented

Several foundations required by 1.5 exist but are not yet the integrated MVP:

- BrowserTask stores host/session/control linkage strings, but complete
  one-time controller/session/run/Kanban binding and mismatch enforcement are
  not yet wired end to end.
- The Browser route can manage tabs/tasks at runtime, but it is not yet the MVP
  Browser Hub with a canonical live-task rail.
- BrowserTask can preserve/hide/park one task page, but Chat/Hub manual host
  transfer is not yet exposed as a product path.
- popup routing and scoped cache cleanup have foundations, while explicit
  upload chooser and visible download status are incomplete.
- routing has an external extension fallback boundary, but the explicit
  opt-in compatibility contract for unbound work is not yet an integrated MVP.
- `workstation/contracts.py`, `memory.py`, and `perception.py` define partial
  interfaces; canonical Kanban/journal/report/memory execution is not complete.

## Not implemented yet

The V1 #1.5 implementation still must deliver executable MVP paths for:

- contextual Chat Browser View and global Browser Hub over the same task/runtime;
- manual single-host Chat ↔ Hub transfer and Preview duplicate refusal/reuse;
- durable task/session/run/card binding;
- automatic clearly-multistep Kanban promotion, follow-up dependency and
  append-only journal/completion metadata;
- task rail groupings and at least two-task FIFO/manual ownership;
- official authenticated Dashboard LAN/Tailscale opt-ins;
- upload chooser and visible download list/completion location;
- controller interruption/reconnect/rebind/resume golden recovery;
- clean-checkout one-click Windows host-composition E2E;
- opt-in procedure save/replay, compact provenance perception, governed drift
  stop/replan and Lightpanda read-only stateless routing.

These are not complete merely because the roadmap or interface scaffold exists.

## Manual validation already observed

- H004 proved the promoted BrowserTask lifecycle with a real BrowserWindow,
  WebContentsView, renderer and two Windows/Electron processes.
- H010 on PR #11 exact head proved clean and abrupt two-process
  BrowserSessionState restart, profile separation, lazy exactly-one-page task
  recovery, failed-write convergence and explicit-destroy failure cleanup.
- Earlier Desktop dogfood proved that Browser and Preview can render, but also
  proved they are independent lanes. That observation is not shared-runtime
  acceptance evidence.

No manual observation yet proves the full V1 #1.5 golden path.

## Known bugs / gaps

See `KNOWN_ISSUES.md`.

- KI-003 is resolved by promoted BrowserSessionState.
- KI-002/KI-004 (Preview duplication and host overlap/ownership composition)
  are active targets of the 1.5 shared-runtime slice.
- KI-006 remains causally classified broad Windows portability/test debt; it is
  visible and is not re-described as a green broad suite.
- KI-007 (`Session not found` / exported `session: null`) remains a separate,
  unproven causal track.

## Latest automated validation state

PR #11 exact head `d5be442...`:

- committed integration, install/checkout-clean, diff, Desktop typecheck,
  BrowserSessionState lint and format passed;
- Browser foundation passed 5 files / 46 tests;
- H010 emitted all phase markers and `H010_CLASSIFICATION=VALIDATED`;
- Workstation CI and Docker completed successfully;
- broad Windows UI/platform remained red only in KI-006 classes (one missing
  route mock and 31 unrelated POSIX/path/mode/SSH/platform assumptions).

PR #12 exact reconciled head `39e5178...`:

- Workstation integration/lock/license gates passed;
- 26 Workstation contract tests passed, including one-click bootstrap policy;
- exact-candidate Windows install, checkout-clean, diff, typecheck,
  BrowserSessionState static checks, 46 focused tests and native H010 passed;
- local committed-integration check, diff check and Desktop typecheck passed;
- local Python execution was unavailable because the present `.venv` does not
  contain pytest; CI supplied the canonical Python evidence.

Mainline Gate candidate `872cbc5...`:

- integration anchors, lockfile and license policy passed;
- **29 Workstation contracts passed**;
- exact Windows install and checkout-clean, diff, complete Desktop typecheck,
  BrowserSessionState static checks, 46 focused tests and H010 passed;
- only documentation and Workstation document contracts differ from the audit
  base, so existing H010 product evidence remains within its proven boundary.

## Promotion status

- Implementation 4 BrowserTask: **PROMOTED / RESOLVED** through PR #9.
- V1 #1 BrowserSessionState: **PROMOTED / RESOLVED** through PR #11.
- V1 #1.5 sequencing + launcher: **PROMOTED** through PR #12.
- Pre-1.5 Mainline Consolidation Gate: **PASS** for the audit base and gate
  candidate; its durable branch/PR ledger is in `MAINLINE_CONSOLIDATION.md`.
- Next implementation track after the gate merge: **V1 #1.5 Integrated Dogfood
  MVP**, starting exclusively from `main`.
