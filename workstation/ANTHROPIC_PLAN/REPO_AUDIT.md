# Repository audit ledger — scope, evidence and gaps

## Snapshot and source-of-truth
- `kevynlucasprofissional-stack/hermes-agent` GitHub repository metadata: `main@f21e803b3525b70ee6be2305e579c1cc1f930e74` observed 2026-10-08; repo size reported ~824 MiB (size includes repository assets, not semantic source LOC).
- Relevant open at observation: [PR #53](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/53) (R1–R5 planning, **not main**), [PR #54](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/54) (CI Laya extra correction, **not main**). [PR #52](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/52) refreshes CW-01 evidence; recheck PR state before decisions.
- `main` already contains D-038 corrective code, including `workstation/experience_compiler/compilability_monitor.py`; older notes declaring Laya not merged must be treated as historical. D-039 adaptive optimization remains an **unqualified proposed improvement**, not an implemented guarantee.
- All assessments in this file are **STATIC SOURCE REVIEW** unless separately linked to exact commit and executed-test logs. No current tests run as part of this plan bootstrap.

## Canonical documentation actually inspected at phase-0 intake
- `workstation/AGENTS.md`, `workstation/ARCHITECTURE.md`, `workstation/ROADMAP.md`, `workstation/SOURCE_MATRIX.md`
- `workstation/context/README.md`, `CURRENT_STATE.md`, `DECISIONS.md`, `HERMES_WORKSTATION_INTELLIGENCE.md`, `EXPERIENCE_COMPILER.md`, `UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `ONLINE_COMPILABILITY_POST_IMPLEMENTATION_AUDIT_2026-10-08.md`, `LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md`
- `workstation/creative-workstation/{README,ARCHITECTURE,IMPLEMENTATION_PLAN,CW01_AUDIT_2026-10-08,EXECUTION_BRIEF,VERIFICATION_MATRIX,INTEGRATIONS}.md`
- `workstation/context/engineering-journal/CURRENT.md` (initial lines); PR #53 proposed `BASELINE_UNBLOCK_EXECUTION_2026-10-08.md`, `IMPLEMENTER_PROMPT.md` and proposed top-of-roadmap R1–R5.
**Coverage classification:** HEADINGS / targeted passages / selected whole documents, **not exhaustive line-by-line audit**. Some files are 100–340 KiB; historical sections intentionally not yet exhausted.

## First-party production code actually inspected (static signatures and entry points, not full behavioral audit)
| Owner | Inspected entry points | Why it matters |
| --- | --- | --- |
| `workstation/task_compiler.py` | `TaskCompiler.execute/resume`, `_execute_route`, `_execute_capability` | Canonical work-plan/dispatch seam |
| `workstation/run_closure.py` | `RunClosureProof`, `evaluate_run_local_closure`, `execute_in_flight_handoff` | No fabricated effect/closure receipt |
| `workstation/experience_compiler/compiler.py` | `ExperienceCompiler.compile/mine/promote` | Scope-first candidate generation; existing promotion authority |
| `workstation/experience_compiler/lifecycle.py` | `ExperienceValidationPromotionCoordinator`, `ValidationEnvironmentProvider` | Empirical verifier and promotion owner |
| `workstation/experience_compiler/compilability_monitor.py` | `LearningPolicy`, `TaskRunObservationWindow`, `OnlineCompilabilityMonitor` | Adaptive learning / scheduling / evidence backlog |
| `workstation/system1/laya_provider.py` | `LayaDecisionProvider.decide` | Bounded System-1; abstention/calibration |
| `workstation/control_plane/router.py`, `composition.py` | `CapabilityRouter.route`, `CompositionEngine.compose` | Authorization/proof boundary |
| `workstation/operational_kernel.py` | `OperationalKernel.execute_capability` | Deterministic execution and effect admission |
| `workstation/runtime.py` | `EvidenceState`, `EvidenceStateStore` | Evidence projections, not a second TaskRun owner |
**Other code owners identified from canonical docs but NOT independently inspected yet:** Electron native BrowserTask, ProcessRegistry, AppResolver, MCP host, package workflows, UI/voice, persistence, workspace artifact and integration tests.

## Current gates (re-verify from exact HEAD)
- **R1:** main Workstation CI reported 7 Laya import failures due to missing `--extra workstation-laya` in workflow. Candidate fix is in open PR #54; not a frontier-model task.
- **R2:** PR #52 Windows production npm audit reported 19 findings in that run (historical CW01 local analysis had 18 in a distinct audit). Follow-up is dependency and security triage; not a frontier-model task by default.
- **R3:** H-079 upstream Stage A remains unqualified. Adopted pin `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`; PR #53 cites candidate `517b5e10febd619ce30bb22580e29b160266eb43`, 857/10,510 divergence at its snapshot. Frozen candidate is NOT adopted merely by citation.
- **R4:** voice input authority KI-024, native Electron H-080B.3, warm bootstrap KI-025/H-082 require independent release verification. Frontiers do not waive gates.
- **R5:** Creative Runtime remains planned; CW-03A/B, Penpot/Three.js/Remotion are unqualified and license-gated as applicable.
- **D-039:** active scoped learning, durable checkpoint and adaptive retry are desirable, but actual provider/replay/authorization and end-to-end proof remain necessary.

## Comprehensive audit protocol (pending)
1. Capture immutable `git ls-files -z` for main and relevant divergent branches, classify path, language, generated, vendored, binary, tests, docs, licensed third party; record SHA+size. Mark binary/vendor **inventoried**, not `semantically read`.
2. Construct module graph (Python import graph, TypeScript workspace dependencies, IPC entrypoints, owner/state boundaries), symbol indices, test-to-owner edges, CI gates; flag inaccessible code.
3. Read high-centrality source fully **with cheap models and deterministic parsers**, not Anthropic; inspect every user-owned production source at least for definitions, imports, effect boundaries, and mutation paths. Focus deep review only on high-risk owners and candidates.
4. Classify old docs vs current SHA; scan unresolved TODO/FIXME and design contradictions with independent source/test evidence.
5. For Source Matrix: enumerate every named external reference and license/status; prioritize code-to-code on shortlisted sources, exact SHA and narrow questions. Other references receive explicit `NOT REVIEWED / NOT APPLICABLE`, not false `READ`.
6. Export reproducible `FILES_MANIFEST.json`, `OWNERS_MAP.md`, `REFERENCES_AUDIT.md` and `GAP_REGISTER.md` in this folder. Each claim has source SHA/path/symbol/test and confidence level.
7. Reconcile PR merges and CI before freezing context packs. A merged PR invalidates affected pack hashes.

## Initial candidate source-to-source comparisons
- Experience Compiler: FlowEvo, RethinkSkill, Double-Ratchet, Trace2Skill, agent-workflow-memory (review relevant modules/research, code licenses and pinned SHA only).
- Runtime/recovery: OpenHands, DeerFlow, DeepSeek Harness and OpenClaw (owner lifecycle patterns only).
- Creative: Penpot official MCP, Three.js Editor bridge surface, React/SVG/FFmpeg, conditional Remotion use license.
- Browser/MCP: Stagehand, browser-use, MCP TypeScript SDK, LibreChat and AnythingLLM where existing Hermes owners show measurable gaps.
No third-party source copy without separate license/security/admission evidence.
