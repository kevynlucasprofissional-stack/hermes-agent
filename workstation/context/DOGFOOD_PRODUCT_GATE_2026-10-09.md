# Dogfood Product Gate — Hermes Workstation (2026-10-09)

**Status: PRODUCT ACCEPTANCE CONTRACT / IMPLEMENTATION OPEN / NOT QUALIFIED.**
**Source priority:** the maintainer's observed-use notes in `workstation/dogfood/` are first-class product requirements, not optional UX ideas. The engineering audit supplied 2026-10-09 is an evidence snapshot, not proof of the user's later local HyperFrames installation. Follow `AGENTS.md`, `workstation/AGENTS.md`, upstream-first H-079, D-038 security and D-039 active learning. This gate does not authorize effects or waive CI.

## What this means

A feature is DONE only when a real normal Hermes Work run demonstrates the behavior and durable evidence proves its owner/authority, native GUI, verification and outcome. A unit-test green, mock-only success, documented capability, candidate artifact, passing typed Laya contract or screenshot is not a substitute. `NOT VERIFIED` is not `ABSENT`. If a user's local Worktree runs a newer HyperFrames than GitHub, inspect/preserve it; do not overwrite or declare it nonexistent.

**Truth hierarchy:** (1) the original, immutable human dogfood notes determine *intent*; (2) real run receipts, code, exact-head tests and independent readback determine *implementation truth*; (3) the supplied audit is a dated gap hypothesis; (4) design decisions/proposals do not imply code exists. Any apparent conflict must be reconciled, not silently declared closed. Never silently edit a note in `dogfood/`.

## Complete source index

- `dogfood/readme.md`: each timestamped record corresponds to an actual human Work run.
- `dogfood/210926 05h58.md`: optimal upstream seams; integrated native browser and Experience Compiler.
- `dogfood/220926 22h07.md`: initial launch code 01, browser logged-in reuse, browser/experience/Laya causal loop, Playwright/CDP to native surface, Trello cards, microprocedures -> workflows.
- `dogfood/02.10.26.md`: subagent native browser and Browser Hub, opt-in human recorder, site prebake, n8n/MCP simpler UX, Chrome extensions, tool consolidation, Agora simulation ideas.
- `dogfood/03.10.26.md`: web UI -> typed service adapter; Google AI Studio transcription hypothesis; ACIRV marketing-agent input in Data.
- `dogfood/06.10.26.md`: persistent semantic Laya observation concurrently with normal TaskRun, progressive mining and same-run reuse.
- `dogfood/07.10.26.md`: HTML/site prebake, historical .md backfill, quantitative audit of missed compilation and true negatives.
- `dogfood/.obsidian/`: Obsidian UI/configuration metadata, **not** extra product run notes. workspace.json references local non-versioned files; require separate access before claiming they were read.

## Atomic requirement-to-proof ledger

Every ID requires: source -> affected code/owner -> RED test -> GREEN test -> **real-product** receipt -> status -> regression guard -> root-cause explanation if deferred. An entry may be `implemented_unverified`, `verified`, `blocked`, `not_implemented`, `not_applicable`, never silently removed.

| ID / Priority | Maintainer intent / acceptance behavior | Existing owner and likely paths | Current remote/main evidence at 2026-10-09 |
| --- | --- | --- | --- |
| DF-001 P0 | Workstation/upstream behave as one; only necessary, well-audited source seams | `context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `first_party_seams.json`, `UPSTREAM_DELTA.md`, `scripts/audit_hermes_seams.py` | Contract exists; latest upstream-qualified feature baseline unverified |
| DF-002 P1 | "abre o browser"/"abre o ChatGPT" uses existing native Chromium without BrowserClaw detour when unambiguous | `integrations/hermes/operational_resolution.py`, `browser_controller.py`, `tools/browser_workstation.py` | H-080B real-use audit identified detours |
| DF-003 P1 | Goal-proportional verification: trusted host/ready readback suffices to open site; no unrelated vision/login checks | `browser_runtime.py`, `tools/browser_workstation.py`, `control_plane/verification.py` | H-080B audit documented extra vision |
| DF-004 P0 | Real browser action yields VERIFIED, accepted `TransitionSample` with task/run/operation lineage | `experience_compiler/corpus.py`, `integrations/hermes/tool_observer.py`, `operational_kernel.py` | Real-use audit reported INCONCLUSIVE samples; later tests need native E2E |
| DF-005 P1 | Individual procedures compose into Trello card creation then batch workflow; no parallel LearnedScript authority | `experience_compiler/{compiler,hierarchical,lifecycle}.py`, `operational_capabilities.py` | Implementation objects exist; full product demonstration open |
| DF-006 P0 | Laya observes meaningful events while agent works, proposes bounded typed compilability stages, not per-token/mouse polling | `experience_compiler/compilability_monitor.py`, `system1/`, `tool_observer.py` | Event hook exists; quality/production validation unproven |
| DF-007 P0 | SHADOW for effects still allows safe capture, mining, validation preparation; never blind auto-mutation | `compilability_monitor.py::process_event` | **Confirmed gap:** SHADOW exits before mining |
| DF-008 P0 | DIRECT must require resolvable signed/bound scoped qualification, real owner/verifier/replay; not arbitrary nonempty ref | `compilability_monitor.py::resolve_policy`, `compilability_validation.py` | **Confirmed gap:** any nonempty text enables DIRECT mode flag |
| DF-009 P0 | High-value verified/negative events and candidate opportunities survive queue full/TTL/shutdown/restart; bounded resource budget | `compilability_monitor.py`, `experience_compiler/corpus.py`, `artifacts.py` | **Confirmed gap:** queue sheds; 900s hot window eviction; pending worker work dropped |
| DF-010 P0 | Attempts reopen on materially new evidence, verifier recovery or parameter variant; no same-evidence busy loop | `compilability_monitor.py::TaskRunObservationWindow` | Fixed 3 compile/3 validation limits can suppress learning |
| DF-011 P0 | Isolated real product ValidationEnvironmentProvider + owner-sourced positive/negative/replay/readback and no fabricated receipt | `experience_compiler/lifecycle.py`, `compilability_validation.py`, `run_adoption.py` | Local positive tests use test provider; product owner gap documented |
| DF-012 P0 | Same TaskRun: 2–3 verified examples -> candidate -> NEXT 4+ equivalents adopted, each verified, without new System-2 on those items | `integrations/hermes/run_local_adoption.py`, `run_adoption.py` | Test fixture proves pattern; normal real product not qualified |
| DF-013 P1 | Real measured System-2 saving/latency/cost per verified outcome, opportunity loss and true negative reasons; unknown != zero | `compilability_monitor.py`, `telemetry/`, `control_plane/metrics.py` | Some counters present; no measured product baseline |
| DF-014 P1 | Delegated subagent uses same native BrowserTask API, gets child-scoped identity/authority; its run is visible in Browser Hub | `agent/subagent_lifecycle.py`, `gateway/browser_control_broker.py`, `browser_session.py`, desktop browser UI | Broker and subagent exist; combined E2E missing |
| DF-015 P2 | User opt-in human action recorder yields sanitized semantic browser transitions and optional candidate proposals; pause/erase explicit | Native browser bridge/observer + ExperienceCorpus | Not demonstrated; never record passwords/tokens/cookies or every mouse move |
| DF-016 P2 | Versioned, opt-in site preparation for Trello, Instagram, GitHub, ChatGPT, AI Studio, Gemini, Notebook, Apify; provenance and DOM invalidation | Existing Browser, Artifacts, registry, Skills | Not demonstrated; avoid persisted auth HTML or stale selectors as truth |
| DF-017 P2 | Expose allowed UI-derived procedures through typed scoped service calls, not insecure fake APIs | Browser broker/route, CapabilityRegistry, integration adapter | Research prototype only; do not bypass service terms/access controls or automate anti-bot evasion |
| DF-018 P2 | Ingest previous Hermes conversation .md and trace artifacts, propose skills/candidates with provenance and PII controls | ExperienceCorpus, Memory/Skills, ArtifactStore | No verified retro-import dogfood |
| DF-019 P1 | Answer: which reasonable compilations happened/missed/held/true-negative, with denominator from labeled evaluation set | Corpus + metrics + counterfactual replay/labels | No reliable completeness accounting in product |
| DF-020 P2 | Chrome extension load/use/remove in native Workstation with permission and isolation test | `browser_controller.py` browser_extension_* and Electron browser runtime | API exists; real-product compatibility not proven |
| DF-021 P3 | K-Tools, X-cursos runner, YT-DLP_TUI, ECO, ATOM integration backlog with adapter/licence/security owners | Workstation integrations + capabilities | Discovery/assessment only, not prerequisite for core |
| DF-022 P3 | Investigate Agora + Mirofish + large-population simulation + random forests scientifically before architecture commitment | Research / source matrix | Idea only; avoid asserting 8 billion individual agents feasible |
| DF-023 P2 | ACIRV marketing agent consumes "Briefing Agente Marketing ACIRV" input in Data with canonical permission/provenance | Workstation file/project integration | User reports file in local Data; path/content not verified in GitHub |
| DF-024 P1 | HyperFrames local studio: native Electron, human+agent share editable project, optimistic concurrency, real animated render and reopen | `creative-workstation/`, desktop Electron, ArtifactStore/Journal/ProcessRegistry | D-041 docs only in PR #62; user's installed code not available in consulted GitHub |
| DF-025 P0 | Three *real* proof scenarios: (A) browser learning; (B) 12 Trello cards same-run; (C) HyperFrames visual+agent shared edit | E2E test harness + real native GUI + telemetry | No evidence these three are fully qualified |
| DF-026 P1 | Cold/warm/offline start, startup code 01 recovery, Windows desktop/CI health including cancellation/restart | H-082, `workstation/qualification/`, Desktop tests | Historical startup incident; current product unqualified |

## Three flagship dogfood experiments

**E1 native browser**: novel "open ChatGPT in native browser" -> real browser action -> independent post-effect readback -> verified trace -> existing ExperienceCompiler -> cross-run policy proof for global promotion -> later typed/known-equivalent intent -> direct routing -> exactly one native browser operation -> VERIFIED; count provider calls (0 where pre-reasoning route genuinely suffices), no redundant vision. Include wrong host, revoked lease, ambiguity, drift, missing controller negatives.

**E2 Trello**: authorized sandbox/test board, 12 cards with title/description/due date; trace first 2–3 verified cards -> scoped candidate -> real verifier/replay/permission -> next 4+ equivalent pending items independently accepted/readback, no duplicate card creation, no stale date selection; measured System-2 differential with baseline. If insufficient evidence or external terms block real changes, record BLOCKED and use controlled fixture as weaker evidence.

**E3 Creative**: real, pinned local HyperFrames Studio in existing Electron: human edits project; agent applies typed change with ETag; manual edits persist and conflicts return 409; save/reopen/re-export animated PNG/MP4 as appropriate; independent frame variation/video probe; all task/process/artifact owners canonical; resulting action traces enter the **same ExperienceCompiler**, not a Creative compiler fork.

## Product/release gate

1. Before code: upstream-first exact pin + baseline CI; worktree/uncommitted preservation and optional bounded documented development exception **not** promotion permission.
2. Each ID has baseline evidence vs hypothesis; enforce D-038 readback, effect budget, task/run/tenant lease; Laya confidence never grants authority; same-run candidate != globally promoted.
3. Genuine product integration required: real installed Electron/Chromium and model/procedure lineage. Mock tests are necessary for falsification, insufficient for final closure.
4. Exact-head Windows, Workstation CI, upstream drift snapshot and independent evidence must be green. Do not bypass a check with a skip or inflated claim.
5. Do not merge to `main` from an agent without the maintainer's explicit release approval.
