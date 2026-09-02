# CURRENT — Workstation Engineering Journal

Last updated: 2026-09-02
Active track: WP-02 / pre-V1 #1.5 Mainline Consolidation Gate — PASS candidate
Repository: `kevynlucasprofissional-stack/hermes-agent`
Historical milestone branch: `impl4-browser-task-lifecycle`
Code-bearing BrowserTask ancestor: `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`
Native-smoke evidence SHA: `d8acc752133b125b9619cbc7fe09199f1283a22b`
Accepted PR head: `75d10d35d4757496390debf8e4b4f9efb44c5432`
Promotion merge on `main`: `fada723f43613e5e0f061cab24445573ac298998`
Previous `main`: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`
V1 #1 accepted head: `d5be442021ea0c744351622317eef5212219786d`
V1 #1 promotion merge: `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`
V1 #1.5 sequencing accepted head: `39e51787d2414d0165ae8fa8b47d1f0e5f3e65cd`
Consolidation audit base: `main@4b04f4c4d2af5620426589529d29b700cfc21fb0`
Next product track after gate promotion: V1 #1.5 Integrated Dogfood MVP

> Journal/probe/documentation commits after `1ac0e0a9...` do not change BrowserTask product behavior unless this file explicitly records a later code-bearing candidate. Always verify live `main` and compare product paths before carrying evidence into a later implementation.

## WP-02 — Mainline Consolidation Gate

### Preconditions closed

- PR #11 was accepted at exact head `d5be442...` after H010 emitted
  `H010_CLASSIFICATION=VALIDATED`; it merged as `e0a99ef3...`.
- PR #12 then merged that promoted main without rewriting either history. Its
  reconciled head `39e5178...` passed Workstation CI (26 contracts), exact
  Windows install/checkout-clean/diff/typecheck, 46 focused browser tests and
  the native H010 step; it merged as `4b04f4c...`.
- The broad Windows aggregator still reported the classified KI-006 baseline:
  one missing UI route mock and 31 unrelated POSIX/path/mode/SSH/platform
  failures. No BrowserSessionState/BrowserTask scoped test failed.

### G-001 — repository-wide disposition audit

**Hypothesis:** after #11/#12 promotion, no accepted product delta remains only
on a lateral branch; the remaining divergent refs are temporary diagnostics,
superseded source snapshots or reproducible formatter output.

**Confirming evidence required:** compare every GitHub branch to exact audit-base
main, inspect unique file/commit scope, close all superseded open PRs, and leave
zero material `NEEDS INVESTIGATION`.

**Observed result:**

- all ancestor refs classify `ALREADY ON MAIN`;
- PR #4/#5 diagnostic lines contain historical Windows evidence and obsolete
  snapshots only;
- PR #6 source was finalized/promoted by #7; its unique workflow is temporary;
- PR #8 is workflow-only historical validation;
- `bot/js-autofix` is one broad mechanical formatter commit and is
  `REJECTED/DO NOT PROMOTE` wholesale;
- comments carrying these dispositions were added and PRs #4/#5/#6/#8 were
  closed;
- no source/evidence needed for V1 #1.5 remains branch-only.

**Classification:** `VALIDATED`. The complete branch/PR table and checklist are
canonical in `../MAINLINE_CONSOLIDATION.md`.

### G-002 — canonical-document convergence

**Hypothesis:** promotion is incomplete while canonical documents still say
BrowserSessionState is a candidate or V1 #1 is next.

**Confirming evidence required:** update current state, decisions, constraints,
architecture/delta, roadmap, testing, known issues, patch manifest, README and
journal; protect ordering/disposition with executable contracts.

**Result target:** the gate candidate passes Workstation contracts and exact-tree
CI, is promoted to main, and V1 #1.5 branches only after that merge.

**Current classification:** `ACTIVE` until the gate candidate is promoted; the
repository/PR audit itself is complete with zero material unknowns.

## Why this journal exists

This file is the Workstation project's durable anti-repeat memory for active engineering. It records not only experiments, but the **mistakes, rejected premises, evidence boundaries, and decision lineage** that a future agent must know before proposing another implementation.

The evidence hierarchy is:

1. current repository code/tests on the exact ref being changed;
2. versioned executable evidence tied to an exact SHA;
3. current GitHub CI/workflow results for that SHA;
4. canonical Workstation documents (`DECISIONS`, `CONSTRAINTS`, `CURRENT_STATE`, `TESTING`, `KNOWN_ISSUES`, `UPSTREAM_DELTA`, etc.);
5. historical session exports, manual observations, screenshots, and attached context;
6. model/agent narrative.

A lower layer may explain or motivate an investigation, but it must not override a higher layer. In particular, **an assistant saying that a tool/runtime was used is not evidence that it was actually used**; inspect the tool call/result, runtime boundary, code path, or executable marker.

Historical chats are useful because they preserve why a decision changed. They are not permission to resurrect an older architecture after a later decision became canonical.

## Durable project lineage — do not reopen settled branches casually

The project did not start with the current architecture. The early question was which external browser stack should be integrated with Hermes. `agent-browser`, Browser Use, BrowserOS, Browser4, VibeSurf, Sabrina, Hermes Browser Extension, Hermes WebUI, and other approaches were investigated at different times.

Several intermediate architectures were reasonable hypotheses at the time:

- `agent-browser` as the primary Hermes browser engine;
- BrowserOS as the dedicated persistent/logged-in browser;
- a separate `hermes-workstation` repository;
- plugin-first Workstation integration;
- Hermes + separate extension + separate WebUI + launcher;
- a Workstation monorepo wrapping an otherwise untouched Hermes.

Those were **decision stages, not current open choices**.

The settled product direction is now:

- this repository is a **thin downstream distribution/fork of Hermes**, with Workstation first-class;
- upstream Hermes remains authoritative for generic Hermes behavior;
- `workstation/` is the main downstream-owned architecture surface;
- core/upstream-owned changes are allowed only when deep integration requires them, and the delta must stay small, explicit, tested, and tracked;
- Hermes Sessions, Gateway, Kanban, Memory, approvals, profiles, tool registry, and routing remain the source of truth instead of being duplicated;
- the primary Workstation Browser is **Electron Chromium inside Hermes Desktop**, rendered with `WebContentsView`, with a dedicated persistent profile/session;
- `BrowserRuntime` remains an abstraction boundary so specialist/external runtimes can exist without redefining BrowserTask semantics;
- `BrowserTask` is the semantic identity/ownership unit for durable browser work, with at most one live task page per task in a process;
- Preview, Chat Browser View, and Browser Hub must ultimately become views/adapters over the same BrowserTask/runtime rather than independently navigated pages;
- external projects are reused selectively as code, protocol, benchmark, fallback, or design reference according to `SOURCE_MATRIX.md`; they are not automatically vendored into the product.

### Decisions that require new material evidence before reopening

| Old debate                             | Current settled direction                                  | What would justify reopening it                                                                                      |
| -------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| plugin/separate repo vs fork           | thin downstream fork; Workstation first-class              | a concrete upstream capability that removes the need for cross-cutting downstream integration, with migration proof  |
| external browser vs internal browser   | internal Electron Chromium is primary                      | measured inability of Electron runtime to satisfy a required invariant that a specialist runtime demonstrably solves |
| BrowserOS vs agent-browser as the core | neither is the primary Workstation runtime                 | changed product requirements or benchmark evidence, not familiarity/preference                                       |
| separate WebUI                         | official Hermes Desktop/Dashboard remain UI/state surfaces | a specific unmet product requirement that cannot be added without duplicating state/control planes                   |
| second Kanban/SessionDB/Memory         | reuse Hermes-owned systems                                 | only an explicit replacement architecture that supersedes the canonical decisions and includes migration/tests       |
| synchronize Preview and Browser by URL | one BrowserTask/live page, views/hosts                     | never as a cosmetic synchronization workaround; only a replacement of the ownership model with stronger proof        |
| browser availability from process env  | session/platform capability                                | only if Hermes changes its gateway/session architecture materially and tests prove the new identity model            |

The rule is not “never change architecture.” A replacement decision must identify the material new evidence, name the decision it supersedes, define migration, and prove the new behavior.

## Cross-track findings imported from prior investigations

### CT-001 — Preview is not proof of the Workstation Browser

A real Desktop smoke was once reported as “Workstation Browser interno” after the agent called `open_preview` and `read_preview`. That was a **false-positive identity claim**.

What that test actually proved:

- the Desktop Preview surface could navigate/render/read the page;
- Electron/Preview was functioning.

What it did **not** prove:

- `browser_navigate` existed in the session schema;
- `browser_snapshot` existed in the session schema;
- the Workstation `BrowserRuntime` handled the action;
- a BrowserTask was created/bound;
- Preview and Browser were the same page/runtime.

**Anti-repeat rule:** acceptance criteria that name a tool/runtime must be proven by the **exact tool invocation and execution boundary**, not by visually similar output. A successful substitute is evidence for the substitute only.

### CT-002 — Real Desktop tool exposure can fail before BrowserTask

A real-environment investigation established this before-state:

- the Capabilities UI showed **Browser Automation = ON**;
- `coding_context = auto`;
- `agent.disabled_toolsets = []`;
- persisted `platform_toolsets.cli` did **not** contain `browser`;
- effective `_get_platform_tools(..., "cli")` did **not** resolve `browser`;
- a genuinely new Desktop session did not receive `browser_navigate` or `browser_snapshot`.

This refuted the tempting hypothesis that `coding_context=focus` was simply stripping Browser in that environment.

The proven boundary was:

```text
Capabilities UI
  → toolset API/configuration
  → profile/config persistence
  → toolset resolution
  → Desktop session schema
  → browser_* execution
  → BrowserTask/runtime
```

**Anti-repeat rule:** do not modify BrowserTask lifecycle/persistence to fix a failure that occurs before the model receives `browser_*` tools.

### CT-003 — Automated lifecycle tests and native lifecycle evidence are different claims

Passing pure or mocked tests did not prove a real `WebContentsView`, native Windows process restart, or renderer identity behavior.

- pure tests prove lifecycle logic/serialization;
- mocked runtime tests prove adapter contracts;
- build/typecheck proves compilation;
- process launch proves launch;
- H-004 native probe proves the actual Windows/Electron/Chromium lifecycle contract.

**Anti-repeat rule:** never upgrade a lower-layer green result into a stronger claim than that layer can observe.

### CT-004 — CI must test committed source, not an auto-repaired checkout

An earlier Workstation install path could mutate/repair tracked source before validation, creating a false-green risk.

Durable policy:

- committed downstream source is canonical;
- normal install validates integration read-only;
- runtime state lives outside tracked source where appropriate;
- install must not dirty the checkout;
- migration/rebase helpers are separate from normal validation.

### CT-005 — A red broad Windows gate needs causality, not storytelling

Durable method:

1. reproduce exact base and candidate;
2. same OS/toolchain/dependency install/commands;
3. compare failure **signatures/classes**, not only counts;
4. keep scoped outcomes independently visible;
5. preserve final red when any required broad suite is red;
6. never delete/allowlist coverage to manufacture green.

### CT-006 — GUI/browser surface identity belongs to the session

Implementation 3 established:

- GUI/Desktop surface identity is session/platform state, not a process-global env proxy;
- controller reachability is execution state, not surface existence;
- tool-definition caching must include session-surface capability to avoid Desktop↔TUI leakage.

### CT-007 — Old BrowserClaw experiments are historical motivation, not the current architecture

Earlier BrowserClaw experiments inform requirements/failure modes; they are not permission to reintroduce BrowserClaw as the primary Workstation browser after the internal-runtime decision.

## Long-term product north star — governed by the roadmap

The broader direction is Hermes as a persistent execution/orchestration layer
for recurring work. V1 #1.5 now authorizes only the narrow, executable slices
listed in the roadmap; it is not permission to claim their later hardening scope
or to create parallel owners.

## WP-01 / BrowserSessionState objective — resolved and promoted

Complete the canonical BrowserSessionState foundation beyond BrowserTask-only
metadata while preserving the current live-page owners and avoiding a second
page store, SessionDB, Kanban, or control plane.

Operational base verification on 2026-08-30:

- the initially checked local `main` ref was stale at
  `ce78f120e8ed2974d6174e475cc7572afcfe41e0`;
- after fetching, `origin/main` resolved to the packet base
  `46a6ef9e257b4add01d6eb7f2a95a82bb433ee89`;
- branch `wp/codex/browser-session-state-core` was created directly from that
  verified remote ref without moving local `main`.

Scope boundary: ordinary logical tabs, order, active logical/generic tab, safe
URL/title metadata, BrowserTask relationship, available identity linkage, and
explicit recovery metadata/policy. Chat Browser View, Browser Hub, Preview
unification, host transfer, SessionDB/Gateway semantics, Kanban implementation,
LAN/Tailscale, Browser Memory, and KI-007 remain out of scope.

### Historical candidate acceptance status (superseded by final promotion)

- Implementer-focused validation on candidate
  `9ce769ee54ab6a02cad77a266c87cb05a8cad3f6` passed the scoped
  BrowserSessionState/BrowserTask tests, Desktop typecheck and Workstation
  contracts recorded below.
- Independent verification **blocked** that candidate because arbitrary raw
  page titles could cross the durable boundary and because the possible
  `new browserTasks + previous sanitized tab projection` crash snapshots had
  not been exercised through runtime restart/recovery.
- At that checkpoint the writer-branch work was a corrective candidate, not an
  accepted or promoted implementation.
- Independent re-verification and native Electron restart acceptance were still
  pending at that checkpoint; H010 and the final PR #11 promotion below
  supersede those temporary blockers.

### H-007 — BrowserSessionState can be a safe structural projection of existing authorities

Origin: WP-01 requires restart-safe logical browser state beyond the promoted
BrowserTask metadata, but forbids a second live-page owner.

Hypothesis:

- `entries`, `taskTabs`, and `activeTabId` remain authoritative for live
  process-local pages, task bindings, ordering, and active page;
- `BrowserTaskLifecycle` remains authoritative for logical task lifecycle and
  task identity/linkage metadata;
- the Chromium profile remains authoritative for browser-managed site/auth
  state;
- a versioned BrowserSessionState file can persist only a sanitized structural
  projection of those owners and restore logical intent without serializing or
  owning `WebContentsView`, `WebContents`, renderer heap, or process identity.

Experiment (registered before code inspection):

1. trace every mutation/read of `entries`, `taskTabs`, `activeTabId`, and
   `BrowserTaskLifecycle` on exact `origin/main`;
2. inspect current persistence, recovery, and BrowserTask regression tests;
3. classify each field as process-, BrowserTask-, BrowserSessionState-,
   Hermes-session-, or Chromium-profile-scoped;
4. derive the smallest persistence/migration seam that writes atomically and
   reconciles through the existing runtime owners;
5. define adversarial URL/title inputs whose credentials, secret markers, or
   sensitive content must fail closed before entering structural JSON.

Confirming evidence:

- no existing durable ordinary-tab owner exists;
- one snapshot can be built from current owners and restored through their
  existing mutation paths;
- task-owned tabs reconcile by `taskTabs`/`ownerTaskId` without duplicate pages;
- corrupt/unknown versions are ignored safely and atomic replacement preserves
  the last valid snapshot.

Refuting/reformulating evidence:

- another durable owner already exists for any proposed field;
- restoration would require a second `WebContentsView` map or independent task
  binding;
- raw URL/title persistence cannot be bounded by an explicit safe-metadata
  policy;
- any required change crosses SessionDB, Gateway, Kanban, Preview, or host/UI
  ownership.

Classification: **VALIDATED**.

Observed authority trace on exact base `46a6ef9e257b4add01d6eb7f2a95a82bb433ee89`:

- `WorkstationBrowserRuntime.entries` is the sole process-local live-page map.
  Its `Map` insertion order is the current tab order, and each `BrowserEntry`
  exclusively owns one `WebContentsView` plus live loading/crash state.
- `taskTabs` is the task id → live tab id index; `BrowserEntry.ownerTaskId` is
  the reciprocal ownership marker. `createTab(..., ownerTaskId)` and
  `rawEntryForTask()` reconcile stale/destroyed mappings through those two
  primitives and never allocate a second live page for the same task.
- `activeTabId` is the sole process-local physical active-tab pointer. Attach,
  navigation and UI state derive from it; it is cleared when its entry is
  discarded or destroyed.
- `BrowserTaskLifecycle.tasks` owns logical BrowserTask status, recovery and
  available linkage (`panelHost`, `controlHost`, `sessionHost`,
  `localConnection`, `leaseState`). Its version-1 `browser-tasks.json` is the
  only durable state on the base, and it deliberately contains no page URL,
  title, renderer object, or typed/page secret.
- `session.fromPath(workstationBrowserProfilePath(), { cache: true })` owns the
  dedicated Chromium profile: cookies, localStorage, IndexedDB, cache and
  compatible browser authentication. It is not BrowserSessionState.
- request `session_id` reaches the Desktop controller, but the base runtime does
  not currently mutate SessionDB/Gateway semantics with it. WP-01 therefore
  preserves available BrowserTask linkage without inventing missing
  SessionDB/run/Kanban authority.

Scope classification:

- process-scoped: `WebContentsView`, `WebContents`, renderer heap/process
  identity, `entries`, `taskTabs`, physical `activeTabId`, loading/crash flags,
  attach/bounds/control-server handles;
- BrowserTask-scoped: task id, lifecycle status/parked state, task recovery,
  task timestamps and available host/session/connection/lease linkage;
- BrowserSessionState-scoped: logical tab ids, ordinary/task relationship,
  structural order, active logical/generic tab, sanitized URL/title metadata,
  and explicit page-recreation policy/status;
- Hermes-session-scoped: the externally supplied Hermes session identity and
  its SessionDB/Gateway lineage remain owned outside this runtime; WP-01 only
  preserves an already-available linkage string inside BrowserTask metadata;
- Chromium-profile-scoped: site storage, cookies, cache, browser auth and other
  Chromium-managed data under the dedicated profile path.

Minimal persistence/migration conclusion:

1. introduce one versioned `browser-session.json` containing sanitized logical
   tab state plus the existing BrowserTask snapshot;
2. expose a BrowserTask persistence adapter over that same atomic file, so
   `BrowserTaskLifecycle` remains the in-memory task authority and no second
   BrowserTask JSON source remains active;
3. import valid version-1 `browser-tasks.json` only when
   `browser-session.json` is absent, atomically commit the composite state, then
   remove the legacy file; never fall back to stale legacy data when a new file
   exists but is corrupt or from an unknown version;
4. restore ordinary tabs by recreating new process objects in persisted order,
   while BrowserTask tabs remain metadata-only recovery hints until the promoted
   lifecycle lazily recreates exactly one page;
5. derive every subsequent snapshot from current runtime/lifecycle owners;
   temporary restart hints contain structural metadata only and never own a
   page object.

Security conclusion:

- URL metadata is safe only after an explicit allowlist/sanitization step:
  `about:blank` or HTTP(S), no userinfo, no query/fragment, bounded length, and
  rejection of credential/secret/session markers or opaque token-like path
  material;
- **Historical title conclusion — SUPERSEDED BY H-009 FOR DURABLE TITLES:**
  title metadata was considered safe after bounded normalization and rejection
  of controls, URLs/email-like data, secret markers, assignments and opaque
  token-like material;
- unsafe URL/title values become `null`/blank recovery metadata; raw values are
  never copied into structural JSON.

Current canonical durable-title rule: **Arbitrary page-controlled titles never
cross BrowserSessionState persistence; `safeTitle` is always `null`. Live
`WebContents` titles remain available in-process.**

Practical implication: H-007 supports the scoped implementation; it does not
justify changes to SessionDB, Gateway, Kanban, Preview, UI hosts, LAN, or KI-007.

### H-008 — Composite persistence and owner-driven reconciliation satisfy WP-01

Hypothesis:

- a standalone, pure BrowserSessionState serializer/persistence module plus a
  narrow runtime adapter can cover ordinary tab/order/active restoration,
  BrowserTask coexistence, safe metadata and restart reconciliation without
  changing any current live-page or lifecycle authority;
- adversarial serialization and runtime restart tests can prove that secret
  material and Electron process objects never enter the JSON and that task
  pages remain singular/lazy.

Confirming evidence: focused pure/runtime tests cover ordinary/order/active,
safe URL/title, unknown/corrupt version, atomic replacement failure, legacy
migration, BrowserTask coexistence/no duplicates, restart, secret exclusion and
stale/crashed reconciliation while all promoted BrowserTask regressions remain
green.

Refuting evidence: duplicate task pages, eager task-page resurrection, loss of
ordinary order/active state, raw secret markers in JSON, two independently
writable task files after migration, or any required cross-scope change.

Classification: **ACTIVE — REGISTERED BEFORE PRODUCT CHANGE**.

Product boundary marker: product edits are limited to the Electron runtime,
BrowserTask persistence seam, a dedicated BrowserSessionState module/tests, and
the branch-local engineering journal.

Historical policy qualifier: H-008 ran before the independent durable-title
blocker and H-009 correction. Its references to safe-title restoration or
preservation record the then-current candidate behavior, not the canonical
durable-title contract. The experimental outcomes below remain chronological
evidence and are not rewritten.

#### H-008 experiment 1 — focused pure/runtime gate

Command:

`npm run test:desktop:platforms --workspace apps/desktop -- electron/workstation-browser-session-state.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-runtime-task.test.ts`

Sandbox result: runner bootstrap failed before tests with `spawn EPERM`; this was
a sandbox subprocess restriction, not product evidence. The identical command
was rerun with approved process execution.

Executed result: **24 passed / 4 failed across 3 files**; the new pure
BrowserSessionState file and promoted pure BrowserTask file both passed. All
four failures were isolated to the runtime adapter:

1. three restored safe-title assertions under the historical pre-H-009 policy
   received `New Tab` because the fake WebContents emits `did-navigate` before
   any page title and `updateEntrySafeMetadata()` replaced the persisted safe
   title with `null`;
2. same-process crashed BrowserTask recovery reused the pending logical tab id,
   while the promoted regression requires a visibly new replacement tab/page id
   after a crash (`assert.notEqual(owned[0].id, firstTab.id)`).

Classification: **PARTIAL / CORRECTIVE**. H-008's composite persistence premise
is not refuted; the pure security/version/migration/atomic contracts passed.
The runtime reconciliation needs two narrow corrections.

Material correction registered before change:

- under the historical pre-H-009 policy, retain a previously safe title while
  navigation has no non-empty title, but still clear/reject it when a non-empty
  unsafe title arrives;
- distinguish restart recovery (`restored` hint may retain its logical tab id)
  from a same-process stale/crashed page (`stale` hint must allocate a new tab
  id while reusing only sanitized URL/title metadata and preserving order).

#### H-008 experiment 2 — focused gate after corrective changes

Identical approved command result: **3 test files passed / 28 tests passed / 0
failed**.

Covered outcomes:

- ordinary tab persistence, ordering and active logical tab restoration;
- historical pre-H-009 safe URL/title preservation and adversarial
  userinfo/query/fragment, secret-marker, opaque-token, URL/email-title and
  process-object exclusion;
- unknown/corrupt version fail-closed behavior;
- atomic replacement failure preserving the previous valid snapshot and
  cleaning the temp file;
- one-shot legacy BrowserTask migration into the composite file;
- BrowserTask/ordinary coexistence, lazy restart recovery and no duplicate task
  pages;
- unexpected stale ordinary-page reconciliation;
- all promoted pure/runtime BrowserTask regression tests.

Classification: **VALIDATED AT FOCUSED PURE/RUNTIME LAYER**. Next evidence
boundary: Desktop TypeScript typecheck/lint and the broader Electron platform
suite; no native Windows identity claim is added by this mocked runtime gate.

#### H-008 experiment 3 — Desktop typecheck, first pass

Command: `npm run typecheck --workspace apps/desktop`.

Result: **failed with one TypeScript error** at
`workstation-browser-session-state.ts`: the optional `browserTaskId` property
was correctly runtime-validated but TypeScript did not preserve narrowing across
a second property access before `.trim()` (`TS2339: Property 'trim' does not
exist on type 'unknown'`).

Classification: **STATIC NARROWING DEFECT**. Registered correction: capture the
unknown property once in a local, validate that local, then trim the narrowed
value. No runtime/persistence behavior changes.

First correction result: **still failed with the same TS2339**. Capturing the
property was insufficient because the `null | undefined | unknown` union was
reintroduced by the ternary expression. Materially changed correction: use an
explicit `if (rawBrowserTaskId === null) ... else { guard; trim }` branch so the
custom type predicate narrows inside one control-flow block.

Second correction result: the BrowserTask id occurrence narrowed successfully;
typecheck then reported the same TS2339 class at the sibling optional
`activeTabId` ternary. Registered correction: apply the same explicit guarded
branch to `activeTabId` before another full rerun.

Final typecheck result: **PASS / exit 0** for all three Desktop TypeScript
configs (`tsc -p .`, `tsconfig.electron.json`, and `tsconfig.e2e.json`, all
`--noEmit`).

Classification: **STATIC CONTRACT VALIDATED**.

Formatting check result: Prettier reported the four modified TS/test files plus
unchanged `workstation-browser-task.test.ts`. Classification: **EXPECTED LOCAL
FORMAT CORRECTION + PRE-EXISTING UNTOUCHED DRIFT**. Only modified files will be
formatted; the promoted untouched regression file will not receive unrelated
churn.

Focused ESLint first result: **423 problems (147 errors / 276 warnings)** across
the two modified legacy runtime files plus the two new files. The output shows
the legacy runtime/test already violate the current global `curly` and padding
rules throughout untouched lines; auto-fixing those files would create broad
out-of-scope churn. The new files also contain fixable import-order,
curly/padding and one `no-control-regex` issue.

Classification: **MIXED — PRE-EXISTING LEGACY LINT DEBT + NEW-FILE LINT**.
Registered action: make both new files independently ESLint-clean, then retain
typecheck/tests as the executable contract for the narrowly modified legacy
files rather than mass-rewriting them.

New-file lint/format result after scoped fixes:

- `npx eslint electron/workstation-browser-session-state.ts electron/workstation-browser-session-state.test.ts`: **PASS / 0 errors / 0 warnings**;
- `npx prettier --check` for the same files: **PASS**.

The `no-control-regex` occurrence was replaced with explicit code-point checks
covering C0 plus DEL/C1 controls; the security policy is unchanged.

#### H-008 experiment 4 — post-format focused/typecheck rerun

- focused Electron gate: **3 files passed / 28 tests passed / 0 failed**;
- Desktop typecheck: **PASS / exit 0** across renderer, Electron and E2E TS
  configs.

#### H-008 experiment 5 — full Electron/platform suite

Command: `npm run test:desktop:platforms --workspace apps/desktop`.

Final rerun after the active-logical-tab adversary: **12 files failed / 109
passed / 1 skipped; 33 tests failed / 1694 passed / 5 skipped (1732 total)**.

The three WP-01/BrowserTask files passed inside the full run. Every reported
failure is outside the changed subsystem and matches a documented KI-006
Windows class: POSIX permission-bit assertions, Darwin staging mode, Windows
8.3/realpath normalization, SSH ControlPath/Include assumptions, WSL probe
timeouts, symlink privileges, Git temp cleanup/timeouts, and PowerShell handoff
timing. No BrowserSessionState/BrowserTask failure appeared.

Classification: **KI-006 BROAD RED / WP-01 NON-REGRESSIVE AT SCOPED GATE**.
The broad command remains correctly reported as exit 1; no test was disabled,
weakened or allowlisted.

#### H-008 experiment 6 — Workstation Python contracts

Required wrapper: `scripts/run_tests.sh workstation/tests`.

Harness resolution evidence:

1. WSL Bash was denied inside the sandbox (`CreateInstance/E_ACCESSDENIED`);
2. approved WSL execution then found no pytest-capable WSL venv;
3. the Windows `.venv` also lacked pytest;
4. a system Windows Python had pytest 9.0.2, but passing it through WSL produced
   the invalid mixed path `C:\\mnt\\c\\...` before collection;
5. Git Bash provided the correct MSYS→Windows path translation; its first
   sandboxed launch was denied a signal pipe, then the identical approved
   wrapper run executed normally.

Final exact wrapper result: **4 files / 24 tests passed / 0 failed** in 5.9s.
This includes context-document contracts, bootstrap canonical-source checks,
Workstation contracts and browser routing/fail-closed tests.

Classification: **WORKSTATION CONTRACTS VALIDATED**. The failed preliminary
attempts were harness/environment failures before test collection, not product
failures.

#### H-008 experiment 7 — interleaved ordinary/task ordering adversary

The BrowserTask coexistence test was strengthened to persist order
`ordinary A → lazy task T → ordinary B` and assert `A → T → B` after T's lazy
page recreation.

First result: **27 passed / 1 failed**. T was recreated once with correct id,
URL, title and ownership, but appeared as `A → B → T`.

Root cause evidence: `restoreSessionTabs()` establishes the full restored order
before iterating, but creation of A called `reconcileRestoredEntryOrder()` while
the loop had not yet registered T as pending. Seeing zero pending hints, the
helper cleared the restored order prematurely.

Classification: **VALID ORDERING DEFECT / H-008 CORRECTIVE**. Registered minimal
fix: never clear the restored-order hint while the outer session restoration is
active; after the complete loop, retain it only while a lazy/stale structural
hint remains.

Corrective result: **3 files / 28 tests passed / 0 failed**. The strengthened
coexistence case now restores `A → T → B`, T is still created lazily through
`BrowserTaskLifecycle`, and its persisted logical id maps to exactly one live
page. A final forward-version adversary also proved that an existing
`BrowserSessionState.version > 1` is neither interpreted nor overwritten and
never triggers fallback to the stale legacy BrowserTask file; malformed/current
version state still starts from a fresh sanitized projection.

Classification: **H-008 VALIDATED**. The ordering hint is transient process
coordination only; `entries`, `taskTabs` and `BrowserEntry.ownerTaskId` remain
the live page/ownership authorities, while the composite file remains the only
restart projection.

#### H-008 experiment 8 — active logical BrowserTask without eager page resurrection

Hypothesis: reusing only process-authoritative `activeTabId` during restoration
would lose a persisted active BrowserTask because its physical page must remain
lazy. A task-only state would also need a generic live fallback page without
changing the structural active selection.

Experiment: make a task tab active, persist/restart, assert that no task page is
alive before `showTask()`, inspect the composite `activeTabId`, then show the
task twice and inspect id/ownership/page count.

Evidence: the first audit found that the physical fallback could overwrite the
structural selection. The corrective retains one transient
`restoredLogicalActiveTabId` only while its lazy tab hint exists. It is not a
page store: `activeTabId` still owns the physical active `entries` member, and
any ordinary activation or task materialization consumes the hint.

Final focused result: **3 files / 29 tests passed / 0 failed**. Before
`showTask()`, zero task pages exist and `browser-session.json.activeTabId`
retains the task's logical tab id. After `showTask()`, that same id maps to one
live page and becomes the physical `activeTabId`; the second show remains
idempotent.

Final static/contract results:

- full Desktop TypeScript typecheck (renderer + Electron + E2E): **passed**;
- ESLint for both new BrowserSessionState files: **0 errors / 0 warnings**;
- Prettier check for both new BrowserSessionState files: **passed**;
- final Workstation wrapper rerun: **4 files / 24 tests passed / 0 failed** in 4.9s.

Historical classification at that candidate: **IMPLEMENTER-FOCUSED VALIDATION
ONLY / INDEPENDENTLY BLOCKED**. These scoped results remain useful evidence, but they did not prove
the durable-title boundary or material composite-write interruption states.
Native Electron restart was still pending and promotion was not authorized at
that point; the later H010 final result supersedes this state.

### H-009 — Durable-title denial and executable composite recovery can correct the candidate narrowly

Origin: independent verification of candidate `9ce769ee...` demonstrated that
`safeTitleMetadata("Recovery code 482913")` returned the raw recovery code and
correctly identified that one BrowserTask operation can durably publish new
BrowserTask metadata before the final tabs/active projection.

Hypothesis:

- durable BrowserSessionState can set every page-controlled title to `null`
  without weakening the live `WebContents.getTitle()` surface;
- URL persistence can retain its conservative structural policy while failing
  closed for explicit recovery/verification/OTP/PIN/magic/one-time credential
  path semantics;
- injecting failure through the existing BrowserSessionState filesystem seam
  can capture the C1 create, C2 recreate/show and C3 destroy intermediate files
  through the real `WorkstationBrowserRuntime` integration;
- each possible `new browserTasks + previous sanitized tab projection`
  snapshot will restart deterministically, preserve at-most-one ownership,
  remain secret-free and converge to one canonical composite file.

Confirming evidence:

- every raw title, including harmless display text and numeric/customer labels,
  serializes as `safeTitle: null` while the live runtime still reports its real
  page title;
- credential-bearing URL query/fragment/userinfo/JWT/signed material and the
  explicit authentication path classes never appear in serialized or reloaded
  state;
- C1/C2/C3 restart assertions prove logical task uniqueness, lazy page
  recreation, orphan removal, deterministic active/order reconciliation and a
  canonical final snapshot.

Refuting evidence:

- any raw page title or forbidden credential material appears in JSON or after
  reload;
- a recovered task is duplicated, eagerly materialized, rebound to two pages,
  resurrected after destroy, or cannot converge after a faulted projection;
- proving recovery requires a second state owner or transaction framework.

Classification: **ACTIVE — REGISTERED BEFORE CORRECTIVE PRODUCT CHANGE**.

Product boundary marker: edits remain limited to the existing
BrowserSessionState sanitizer/persistence seam, its runtime injection point,
focused pure/runtime regressions and this journal. Native Electron restart is
still a later acceptance layer, not implied by the mocked Electron runtime
fault tests.

#### H-009 experiment 1 — security boundary and C1/C2/C3 focused gate

Command:

`npm run test:desktop:platforms --workspace apps/desktop -- electron/workstation-browser-session-state.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-runtime-task.test.ts`

The first sandboxed launch failed before config load with `spawn EPERM`; the
identical approved command then executed normally.

Result: **3 files / 33 tests passed / 0 failed**.

Observed executable evidence:

- every page-controlled title, including the five credential examples,
  harmless display text and a customer-number label, became `safeTitle: null`;
- live fake-WebContents titles remained visible before process teardown, while
  restored titles fell back to `New Tab`;
- access-token query, OAuth code, fragment token, userinfo/password, JWT and
  presigned credential material were absent from serialized and reloaded JSON;
- explicit recovery/verification/OTP/temporary-PIN/magic-login/one-time path
  classes failed closed, while `/customers/482913` remained restorable;
- C1 captured new BrowserTask T plus the previous sanitized ordinary-tab
  projection, then restored T parked/lazy and materialized exactly one page;
- C2 captured recreated/visible BrowserTask metadata plus the previous lazy
  sanitized tab/active projection, then restarted parked/lazy and converged to
  one task/page binding with deterministic order and active selection;
- C3 captured durable task removal before the final runtime projection, pruned
  the orphan relationship during normalization, refused later `showTask(T)` and
  reconciled the remaining ordinary tab as active.

Classification: **VALIDATED AT FOCUSED PURE/MOCKED-RUNTIME LAYER**. The
possible `new browserTasks + previous sanitized tab projection` intermediate is
explicitly accepted and proven recoverable; it is not described as impossible.
Next evidence boundary: formatting/static checks, full focused
`workstation-browser` tests, Desktop typecheck and Workstation contracts.

#### H-009 experiment 2 — required corrective validation matrix

Final scoped JavaScript results after formatting:

- BrowserSessionState focused: **1 file / 9 tests passed / 0 failed**;
- BrowserTask pure: **1 file / 10 tests passed / 0 failed**;
- Browser runtime-task: **1 file / 14 tests passed / 0 failed**;
- all focused `workstation-browser` tests together: **3 files / 33 tests
  passed / 0 failed**;
- targeted adversarial security regression: **1 passed / 8 skipped** under the
  title filter;
- targeted C1/C2/C3 regressions: **3 passed / 11 skipped** under the crash
  boundary filter.

Static results:

- complete Desktop typecheck (`tsc -p .`, Electron and E2E configs): **PASS /
  exit 0**;
- ESLint for the two dedicated BrowserSessionState files: **0 errors / 0
  warnings**;
- Prettier check for the two dedicated BrowserSessionState files: **PASS**.

Workstation Python contract result:

- the first exact wrapper attempt correctly refused to run because the local
  `.venv` lacks pytest;
- rerunning the same repository wrapper with `HERMES_PYTHON` pointing to the
  installed pytest-capable Python produced **4 files / 24 tests passed / 0
  failed** in 6.6s;
- context-document contracts passed with the corrected candidate/non-promotion
  terminology.

Historical classification at that candidate: **CORRECTIVE CANDIDATE VALIDATED
AT REQUESTED AUTOMATED LAYERS / NATIVE ELECTRON RESTART PENDING / PROMOTION NOT
AUTHORIZED**.
The delivery commit freezes the exact Git head for independent verification;
this journal does not treat that delivery action as promotion or native
acceptance.

### H-010 — The native profile-cookie failure is a probe lifetime defect

Origin: the `Workstation Browser Windows` run for PR #11 head
`9177d5a1ebab23d9ce3e5fe9664afbb7fdd43ec5` reached the H010 product path.
Phase A passed structural persistence, safe metadata and BrowserTask ordering,
but phase B failed with `phaseB Chromium profile cookie missing`.

The same exact-head run also exposed two independent static issues: Prettier
reported the two resilience test files, while the focused BrowserSessionState
suite still passed 5 files / 46 tests. Those formatting failures are mechanical
and are not evidence about runtime behavior.

Hypothesis registered before changing the probe:

- H010 creates `h010_profile_cookie` without `expirationDate`; Electron therefore
  treats it as a session cookie, which is not required to survive termination of
  the Chromium session;
- the dedicated `session.fromPath(...)` profile may be healthy even though the
  probe incorrectly asks a session cookie to prove durable profile persistence;
- setting an explicit future `expirationDate`, verifying the cookie immediately
  in phase A, flushing storage, and retaining the existing two-process phase-B
  assertion will test the intended persistent-profile boundary.

Confirming evidence:

- phase A observes the explicitly persistent cookie before shutdown;
- phase B observes the same cookie from the same Workstation profile path in a
  different Electron process;
- the cookie value remains absent from `browser-session.json`;
- all other H010 phases continue to pass on the exact corrected SHA.

Refuting/reformulating evidence:

- an explicitly persistent cookie is visible in phase A but missing in phase B;
- the two processes resolve different Workstation browser profile paths;
- a product shutdown/session-path defect, rather than cookie lifetime, is needed
  to explain the failure.

Local correction evidence after the change:

- the PR branch was first reconciled with `main` at
  `ce448d829e95112fd08b21535c7a8426ee866035`, preserving the one-click
  launcher before any promotion attempt;
- the five-file Browser foundation selection passed **5 files / 46 tests / 0
  failed**;
- complete Desktop typecheck passed;
- exact BrowserSessionState ESLint selection passed with **0 errors / 0
  warnings** after mechanical layout cleanup;
- exact BrowserSessionState Prettier selection passed;
- `git diff --check` and committed Workstation integration validation passed;
- this Linux environment cannot supply the repository's pytest-capable Python
  offline, so the unchanged Python contracts were not represented as a fresh
  local run. Their existing exact-branch evidence remains recorded above and
  GitHub CI must independently rerun them.

Classification: **LOCAL CORRECTION VALIDATED / EXACT-SHA WINDOWS H010 PENDING**.
Product boundary marker: this correction changes only the versioned native probe
and formatting-only test layout. It does not change BrowserSessionState or
BrowserTask runtime semantics. A new exact-SHA Windows run is mandatory because
the native probe itself changes.

Exact-SHA Windows result for `b5910874b27a4bfb4b45485a6438adbfd72cdcfb`:

- checkout identity, clean install, checkout-clean assertion, diff check,
  typecheck, exact ESLint/Prettier and the 5-file / 46-test focused suite passed;
- phase A observed the explicitly persistent cookie and completed;
- phase B, in a different Electron process, observed the same cookie from the
  same dedicated profile, retained it outside `browser-session.json`, restored
  ordinary/task ordering and lazily recreated exactly one task page;
- the original `phaseB Chromium profile cookie missing` failure is therefore
  **resolved**, validating the session-cookie lifetime diagnosis;
- H010 then advanced into its independent failed-write/destroy phase. Failed
  write convergence passed, but the immediate post-`destroyTask` assertion saw
  the old native `WebContents` before Electron emitted `destroyed`.

Reclassification: **COOKIE HYPOTHESIS VALIDATED / NEW NATIVE TEARDOWN TIMING
BOUNDARY ISOLATED AS H-011**.

### H-011 — Native `WebContents.close()` completion is asynchronous

Origin: H010 at exact head `b5910874...` failed with
`destroy fault mode prior WebContents survived` immediately after the runtime
had removed the BrowserTask and page entry in process.

Hypothesis registered before changing product or probe:

- `discardEntry()` synchronously detaches the view, clears `taskTabs`, removes
  the `entries` owner and calls Electron `webContents.close()`;
- real Electron completes `close()` asynchronously and emits `destroyed`, while
  the focused fake marks itself destroyed synchronously;
- the native probe's immediate `isDestroyed()` assertion therefore conflates
  synchronous logical-owner removal with asynchronous Chromium teardown;
- the correct native contract is: immediately no runtime/task owner remains,
  then the old `WebContents` reaches `destroyed` within a bounded wait before
  task-id reuse and fresh-page assertions continue.

Confirming evidence:

- immediately after the failed persistence write, `listTasks()` omits the task
  and `state().tabs` omits its old tab;
- the captured native `WebContents` emits/reaches `destroyed` within a short
  bounded wait;
- subsequent durable convergence and same-id recreation produce one fresh,
  blank page with a different tab id;
- the rest of H010, including abrupt-process restart, remains green.

Refuting/reformulating evidence:

- the runtime still exposes the old task/tab after `destroyTask` returns;
- native destruction does not complete within the bound;
- same-id recreation overlaps the old renderer or inherits its URL;
- a product-side lifecycle change is required to prevent continued page work.

Classification: **ACTIVE — NATIVE TIMING HYPOTHESIS REGISTERED BEFORE CHANGE**.
Product boundary marker: first correct the probe to observe Electron's
documented `destroyed` event/state with a bounded wait. Do not weaken immediate
assertions about logical task/tab ownership or fresh recreation.

Native result at exact head `ad905ddee902efc7d66db76220f44e963030843b`:

- immediate logical task/tab removal passed;
- bounded native `WebContents` teardown passed;
- durable convergence and same-id fresh recreation passed;
- H-011 is therefore **VALIDATED**;
- the probe then exposed a separate harness exit-code issue in abrupt phase A,
  isolated below as H-012.

### H-012 — Electron `process.exit()` return overwrote the abrupt exit code

Origin: H010 at exact head `ad905dde...` emitted
`H010_ABRUPT_PHASE1_DURABLE` and then unexpectedly emitted
`H010_MODE_PASS abrupt1`; the parent observed exit code `0` instead of the
allowed sentinel `17`.

Hypothesis registered before changing the probe:

- Electron's Windows main-process `process.exit(17)` shim initiated exit but
  returned control to the async ready callback;
- the common success tail then executed `app.exit(0)`, replacing the intended
  abrupt sentinel with a normal success code;
- persisted BrowserSessionState had already passed its pre-termination checks,
  so this is an orchestration/exit-code defect after the product boundary;
- selecting the final exit code exactly once through `app.exit(...)`, without
  calling `runtime.destroy()`, should preserve the abrupt-state experiment.

Confirming evidence:

- abrupt phase A exits with code `17` after its durable marker;
- abrupt phase B starts under a different PID, restores the ordinary logical
  tab and parked BrowserTask, lazily creates exactly one task page, and passes;
- full H010 reaches `H010_CLASSIFICATION=VALIDATED`.

Refuting/reformulating evidence:

- phase A still exits `0`, times out, or performs the runtime's clean destroy;
- phase B cannot restore the durable task/tab projection;
- a product persistence change is required before phase B can pass.

Final exact-SHA result at `d5be442021ea0c744351622317eef5212219786d`:

- abrupt phase A emitted `H010_ABRUPT_PHASE1_DURABLE` and exited with the
  allowed non-zero sentinel;
- abrupt phase B ran under a distinct PID and emitted
  `H010_ABRUPT_RESTART_PASS`;
- clean restart, profile separation, failed-write convergence and
  explicit-destroy cleanup remained green;
- the probe emitted `H010_CLASSIFICATION=VALIDATED`.

Classification: **VALIDATED / HARNESS DEFECT CORRECTED**. No
BrowserSessionState product change was required for H-012. PR #11 then promoted
the exact head as merge `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.

## Implementation 4 objective — closed

Required native lifecycle contract:

`create/navigate → hide or park → re-expose without replacement navigation → explicit destroy → real process restart → logical restore/recovery`

Final conclusion: **validated and promoted to `main`**.

## Evidence ledger

### H-001 — BrowserTask lifecycle caused the V9 native-smoke timeout

Classification: **REFUTED**.

Evidence: V9 printed `HARNESS_BOOT` but never `HARNESS_READY`; product runtime import had not occurred.

### H-002 — Electron 40.10.2 / Windows cannot reach `app.ready`

Classification: **REFUTED**.

Evidence: bare Electron readiness probe reached ready and created a BrowserWindow with exit code 0.

### H-003 — V9 readiness stall is caused by top-level `await app.whenReady()` in its ESM main path

Classification: **VALIDATED**.

Experiment: `probes/h003-esm-ready.mjs`.

Evidence:

- TLA case: boot → internal timeout; exit 3;
- `.then(...)` case: boot → ready → BrowserWindow → PASS; exit 0.

Conclusion: V9 was a harness bootstrap defect. Product runtime already uses non-blocking readiness registration.

### H-004 — Real BrowserTask lifecycle satisfies the Implementation 4 acceptance contract

Classification: **VALIDATED**.

Experiment: `probes/h004-native-browser-task-smoke.mjs` at `d8acc752133b125b9619cbc7fe09199f1283a22b`.

Live identity evidence:

- task `impl4-h004-live-task`;
- tab id stayed `a27236b9-4aaf-4adc-9556-7ee14f5c4274`;
- real `webContentsId` stayed `3`;
- owner page count stayed `1`;
- URL and renderer sentinel survived hide/show and park/show;
- hide produced logical `hidden` without destroying page;
- park produced logical `parked` without destroying page.

Explicit destroy evidence:

- `destroyTask` returned true;
- prior WebContents destroyed;
- task not listed;
- zero remaining task-owned tabs;
- no automatic replacement page.

Real restart evidence:

- process 1 PID `30968`: task persisted `parked` / `fresh`, structural state excluded page URL secret and renderer secret;
- process 2 PID `37440`: same task restored `parked` / `restored`, zero eager pages before show, first show created exactly one task page under same task id, recovery became `recreated`.

Practical conclusion: **Implementation 4 native lifecycle acceptance behavior is proven.**

### H-005 — Documentation-closure Workstation CI red represented a BrowserTask/product regression

Classification: **REFUTED AS PRODUCT REGRESSION / VALIDATED AS DOCUMENTATION CONTRACT REGRESSION**.

Evidence:

- `core-patch-dry-run` passed;
- 23/24 Workstation contract tests passed;
- sole failure was `test_context_separates_current_state_from_target_and_known_issues`;
- fingerprint was missing literal heading `## Not implemented yet` after a documentation rewrite combined tested sections.

Correction:

- separate canonical headings restored;
- test was not weakened.

### H-006 — Final-head broad Windows red introduced a new Implementation 4 failure class

Classification: **REFUTED BY CONTROLLED EQUIVALENCE**.

Controlled native-Windows A/B:

- baseline `ce78f120e8ed2974d6174e475cc7572afcfe41e0`;
- candidate `2ffee2335b6aba071e7b63457a047cd9334d4d92`;
- result `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`;
- candidate-specific BrowserTask tests: 2 files / 16 tests passed;
- candidate had fewer legacy failures than baseline and every remaining failure was identical to baseline or a variant of the same KI-006 causal class.

Final accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432` differed from `2ffee...` only by contributor-attribution mapping and Workstation journal material. No BrowserTask product/runtime/probe/workflow/dependency code changed. On that head, committed integration, install, checkout-clean, typecheck and BrowserTask focused steps passed; only the broad aggregator remained red.

Classification used at promotion: `KI-006_ONLY_BY_CONTROLLED_EQUIVALENCE`.

## Experiment / failure ledger

| ID    | Attempt / fingerprint                                                | What happened                                                                                  | Classification                      | Anti-repeat lesson                                                                                                                               |
| ----- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| E-001 | PowerShell interpolation with `$code:` / `$ExpectedBranch:`          | ParserError before test                                                                        | Harness defect                      | Use `${name}:` when `:` follows an interpolated PowerShell variable.                                                                             |
| E-002 | Assume Electron/esbuild at root `.bin`                               | Dependency discovery failed despite `npm ci`                                                   | Harness defect                      | Inspect workspace ownership before hard-coding executable paths.                                                                                 |
| E-003 | PowerShell parameter `$Args`                                         | Arguments swallowed; tools printed usage                                                       | Harness defect                      | Never shadow automatic `$Args`.                                                                                                                  |
| E-004 | native stderr + `$ErrorActionPreference='Stop'`                      | Normal esbuild stderr became `NativeCommandError`                                              | Harness defect                      | stderr is not failure; gate on exit status.                                                                                                      |
| E-005 | `Start-Process` exit code on Windows PowerShell 5.1                  | successful run exposed unusable/null exit status                                               | Harness defect                      | Prefer Node `child_process` for native orchestration.                                                                                            |
| E-006 | arbitrary bundled `.mjs` as Electron target                          | launch did not prove valid app-entry semantics                                                 | Harness defect                      | Use a valid Electron app directory.                                                                                                              |
| E-007 | V9 + top-level `await app.whenReady()`                               | boot marker printed; ready marker never printed                                                | Harness defect                      | Never attribute pre-runtime timeout to BrowserTask.                                                                                              |
| E-008 | H-002 bare CommonJS readiness                                        | ready + BrowserWindow succeeded                                                                | Control evidence                    | General Electron/Windows startup is healthy.                                                                                                     |
| E-009 | H-003 ESM paired control                                             | TLA fails; `.then(...)` passes                                                                 | Root-cause evidence                 | Register readiness non-blockingly on this Windows/Electron path.                                                                                 |
| E-010 | H-004 real BrowserTask lifecycle                                     | live identity, explicit destroy, two-process restart, lazy recovery, secret isolation all pass | Acceptance evidence                 | Reuse the versioned probe; do not reconstruct ad hoc runners.                                                                                    |
| E-011 | Preview described as Workstation Browser validation                  | visually successful page was wrong lane                                                        | False-positive validation           | Exact tool/runtime boundary, not visual similarity, proves identity.                                                                             |
| E-012 | exact `browser_navigate` + `browser_snapshot` requested while absent | test correctly stopped rather than substituting                                                | Correct fail-closed behavior        | Capability absence is a result; do not substitute and call it passed.                                                                            |
| E-013 | coding focus blamed for Browser absence                              | environment showed `coding_context=auto`                                                       | Refuted hypothesis                  | Remove plausible explanations after direct contradiction.                                                                                        |
| E-014 | Capabilities UI ON but resolved CLI toolsets lacked `browser`        | new Desktop session lacked tools                                                               | Cross-layer discrepancy             | Trace UI → API → persistence → resolution → schema before changing runtime.                                                                      |
| E-015 | unit/adapter lifecycle tests treated as native smoke                 | mocks could not prove native restart/page identity                                             | Evidence-boundary error             | Match claim to observing layer; H-004 later supplied native proof.                                                                               |
| E-016 | installer repaired source before validation                          | mutated checkout could hide missing committed integration                                      | Resolved validation-design defect   | Test committed tree; keep repair/migration separate.                                                                                             |
| E-017 | broad Windows red interpreted without exact baseline                 | base/candidate shared failure classes                                                          | Causality lesson                    | Controlled A/B + signatures; baseline-equivalent red remains red.                                                                                |
| E-018 | GUI capability tied to process env/reachability/cache                | Desktop surface could disappear/leak across session types                                      | Resolved ownership-model defect     | Session-scoped surface identity; runtime reachability is execution state.                                                                        |
| E-019 | documentation rewrite removed tested canonical heading               | Workstation CI failed 1/24 although product code unchanged                                     | Documentation contract regression   | Inspect context-doc tests before restructuring canonical docs; documentation-only commits still require CI.                                      |
| E-020 | contributor email unmapped at final promotion                        | repository-wide attribution check failed                                                       | Process gate, corrected             | Merge hygiene is part of promotion; fix the mapping instead of dismissing/bypassing the gate.                                                    |
| E-021 | post-merge canonical docs still said Impl4 was pending               | code/GitHub and `CURRENT_STATE`/`ROADMAP` disagreed after merge                                | Post-promotion documentation defect | Promotion is not complete until canonical state documents reflect the new `main`; correct via a separate docs closure and run context contracts. |

## Stable anti-patterns / rules learned

1. Do not change product code because a validation harness failed before reaching the product boundary.
2. Instrument explicit markers at process boot, Electron ready, product import and each lifecycle milestone.
3. Prefer one orchestration layer with explicit timeout/exit semantics; on Windows use Node `child_process`, not stacked PowerShell wrappers.
4. Compare against a smallest known-good control and vary one material factor at a time.
5. Build success proves compilation only; process launch proves launch only; require behavior evidence.
6. Do not use top-level `await app.whenReady()` in native Workstation validation harnesses on the current Windows/Electron target.
7. Never repeat an experiment unless the materially changed input/assumption is recorded here first.
8. Never call `close-tab` or UI X equivalent to `destroyTask`; test explicit task destruction directly.
9. Do not use Task Manager PID disappearance as the canonical destroy invariant; use WebContents destruction + ownership/state evidence.
10. Once a reusable regression probe exists, improve that probe rather than creating an untracked replacement unless necessary.
11. Carry native smoke to a later documentation-only SHA only after Git proves relevant product/probe code unchanged.
12. Do not infer tool/runtime identity from screen location; inspect actual invocation/route/runtime identifiers.
13. Do not substitute Preview/web search/other browser lane when acceptance explicitly requires Workstation `browser_*`.
14. Never confuse Preview with Workstation Browser while separate lanes remain.
15. Locate the first broken boundary before fixing downstream components.
16. Label statements observed fact / hypothesis / inference / proven cause; reclassify when contradicted.
17. Typecheck, unit, mocked runtime, native smoke, and full E2E are distinct evidence classes.
18. A UI toggle is not proof backend configuration persisted.
19. Session, process, BrowserTask, profile, and renderer state have different owners/lifetimes; name owner before storing/caching/restoring.
20. Do not create parallel SessionDB/Kanban/Memory/browser state/control planes.
21. Do not synchronize duplicate browser pages by URL to imitate a shared BrowserTask; fix ownership.
22. Profile persistence and BrowserSessionState are different; renderer object identity never survives process restart.
23. Bound BrowserTasks fail closed; do not silently switch to a different stateful runtime.
24. Never allow install/CI to auto-heal tracked source before validation.
25. Broad pre-existing red requires controlled baseline/candidate evidence and remains red until fixed.
26. Keep diagnostic suites independent enough to collect evidence, while preserving final failure when required suites fail.
27. Prefer extending existing primitives over creating duplicate state owners.
28. Do not reopen superseded architecture debates without material new evidence.
29. One implementation/hypothesis cycle at a time: reproduce → isolate → smallest complete change → focused validation → correction → regressions → exact-SHA gates → docs → next.
30. In TDD corrective work, RED fails for intended reason; GREEN is smallest fix; REFACTOR only after green.
31. A checkpoint is memory, not a stop condition.
32. Before claiming a full Workstation browser path, separately prove configuration persistence, session schema exposure, exact tool execution, BrowserTask behavior, host/view unification, restart recovery, and profile persistence.
33. Canonical documentation is part of the tested product contract. Before renaming/removing required headings, fields, tables, or markers, inspect `workstation/tests` for structural assertions and run the relevant contracts after the edit.
34. After a promotion merge, audit state-bearing documents against the new `main`; pre-merge wording such as “candidate”, “pending”, or an old main SHA becomes a real consistency defect once the merge lands.

## Promotion closure

Implementation 4 promotion sequence is complete:

1. H-004 real Windows/Electron lifecycle accepted;
2. controlled Windows baseline comparison classified remaining broad red as KI-006;
3. final PR head frozen at `75d10d35d4757496390debf8e4b4f9efb44c5432` with no product/runtime/probe change after causal validation;
4. exact-final-head Workstation CI, Docker, contributor attribution, install/typecheck/focused BrowserTask gates observed;
5. PR #9 marked ready;
6. merge executed with expected head SHA;
7. PR verified merged and `main` verified at `fada723f43613e5e0f061cab24445573ac298998`;
8. merge parents verified: `ce78f120...` + `75d10d35...`;
9. canonical state/roadmap/known-issues/testing/journal closure is being reconciled in `docs/impl4-promotion-closure` because the pre-merge wording became stale only after promotion.

No WP-01 / BrowserSessionState candidate work belongs in this historical
Implementation 4 closure branch.

## Continuous update protocol

Before an experiment/change:

- register hypothesis/experiment ID when causal uncertainty exists;
- state confirming/refuting evidence;
- identify the product boundary marker;
- search this journal for the same fingerprint/premise/already-refuted hypothesis;
- inspect relevant executable contracts, including documentation contracts, before restructuring tested surfaces;
- state what material input changed if repeating a prior approach.

Immediately after:

- record exact output/error fingerprint;
- classify the hypothesis (`VALIDATED`, `PARTIAL`, `REFORMULATED`, `REFUTED`, `INCONCLUSIVE`);
- record practical implication;
- identify the next materially relevant action;
- promote stable product truth into canonical docs instead of leaving it only here.

No experiment is complete until this file is updated. A checkpoint is never permission to stop; it is memory for the next action.
