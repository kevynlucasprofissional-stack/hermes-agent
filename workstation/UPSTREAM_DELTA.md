# Hermes Workstation upstream delta

## HW-031 — H-079.2 promotion-gap and dogfood closure (2026-09-20)

Current downstream truth differs from the prior H-079 narrative in three important ways:
- upstream refresh `8d153b26...` is not ancestral to `main`; the live pin remains `c1488ac947...`;
- the pipless-venv installer repair and its CI fixture exist off-main;
- the explicit negative H-077 ACK-without-delta regression exists off-main.

Current observed upstream drift from `main@964c133...` is 622 upstream-only commits with merge-base `c1488ac947...`. H-079.2 must adopt a fresh pin before reapplying these target fixes.

This delta is not a request to preserve historical file locations. Resolve against current upstream owners and preserve only the behavior contracts.


## HW-030 — Upstream-first qualified baseline discipline (2026-09-20)

Decision D-030 makes upstream freshness an admission condition for downstream code work.

This changes the maintenance model from:
```text
feature work -> more feature work -> periodic large upstream catch-up
```

to:
```text
upstream preflight -> pinned baseline sync -> seam reconciliation -> baseline qualification
-> target downstream work -> target qualification -> final drift check
```

The sync lane and feature/fix lane remain separately reviewable.

H-079 qualified baseline snapshot (2026-09-20; qualification applies only to the recorded SHA):
- upstream pin `c1488ac947c9bc33fd65ec464548dc9d8edd6122` merged into `main` (`24a8501934374e47a23b51f21183fb9c4edd3a76`); the earlier H-079 candidate pin `b7d7d2929a10e0658a98a7a03f4531093e1480ed` (integration lane `a13929fb35`) was superseded by it;
- ancestry verified: the pin is the merge base of downstream snapshot `9e8127e247...` and upstream snapshot `2c0b2a980c...`; drift between these SHAs is 544 downstream-only and 447 upstream-only commits;
- **baseline qualified at exact head**: `9e8127e247accf6858f295e554cab7d4bb7adefe` (PR #41, carrying the browser-routing-ladder fix `1716062f32...`) is green on `Workstation CI` (run `35536129052`); the red run was at `d0ade123c0...`, which that fix supersedes. This evidence does not automatically qualify later branch or main heads;
- aggregate browser convergence is **UNMEASURED**: no named acceptance check is cited for the former `FULL` claim; the narrower browser-authority evidence below remains separate;
- `FPS-RUN-001` (`SEAM-RUN-BATCH`) closed: single tool batch admission in `agent/turn_tool_round.py`;
- `FPS-BROWSER-001` (`SEAM-BROWSER-ROUTE`) closed: authoritative browser dispatch via `browser_extension_router` -> `BrowserControlBroker` -> `WorkstationBrowserController`;
- `FPS-BROWSER-LEGACY` retained as non-authoritative compatibility adapter;
- adapter bootstrap made explicit and fail-closed when Workstation supervision is expected;
- Desktop multi-tab structure ported with active BrowserTask viewport persistence and preview routing;
- Workstation test suite (741 passed), H004, H013 (3/3), and Work100 (30 PASS) green.


## HW-029 — First-Party Workstation Adapter and Generic Core Decoupling (2026-09-19)

H-078B implementation has been completed, eliminating all direct Workstation imports from the generic
Hermes core without losing any Workstation capability.

Summary of changes:
- **Generic Core Extensions (`agent/`)**:
  - `turn_ingress.py`: `TurnIngress` metadata class, `TurnOrigin`, `TurnTrustClass`.
  - `turn_admission.py`: `register_turn_admission_provider`, `admit_turn`.
  - `tool_batch_admission.py`: `register_tool_batch_admission_provider`, `admit_tool_batch`, `BatchAdmissionAction`.
  - `scoped_execution.py`: `register_scoped_execution_provider`, `scoped_execution`.
  - `pre_dispatch.py`: `register_pre_authorized_dispatch_hook`, `dispatch_pre_authorized_checkpoint`.
  - `post_tool.py`: `register_raw_post_tool_observer`, `dispatch_raw_post_tool_observation`.
  - `execution_persistence.py`: `ExecutionPersistenceDisposition`, `get_persistence_disposition`, `register_persistence_disposition_provider`.
  - `turn_route_policy.py`: `TurnRoutePolicy`, `require_allowed_route`.
  - `completion_admission.py`: `register_completion_admission_provider`, `admit_completion`.
  - `compression_admission.py`: `register_compression_bypass_provider`, `should_bypass_compression`.
  - `conversation_projection.py`: `register_conversation_projection_provider`, `project_messages_for_provider`.
  - `task_completion_admission.py`: `register_task_completion_admission_provider`, `admit_task_completion`.
- **First-Party Adapter (`workstation/integrations/hermes/`)**:
  - `adapter.py`: registers first-party handlers with all generic core extension points upon `install_workstation_adapter()`.
  - `turn_admission.py`: maps `TurnIngress` to canonical `MessageEnvelope` & prepares work intent.
  - `tool_batch_admission.py`: translates progressive compilation & human handoffs into `BatchAdmissionResult`.
  - `scoped_execution.py`: manages execution context and attaches operational reference envelopes.
  - `tool_observer.py`: records mutation checkpoints and raw results.
  - `completion_admission.py`: verifies procedure trace steps and kanban run candidates.
  - `task_completion_admission.py`: validates two-phase kanban task acceptance contracts.
  - `browser_controller.py`: registers workstation browser capabilities with `BrowserControlBroker`.
  - `api.py`: FastAPI endpoints for Workstation control plane.
- **Core Decoupling Audit**:
  - `run_agent.py`, `conversation_loop.py`, `tool_executor.py`, `turn_finalizer.py`, `turn_constraints.py`,
    `chat_completion_helpers.py`, `conversation_compression.py`, `cli.py`, `gateway/run.py`, `kanban_db.py`,
    `web_server.py`, `file_tools.py`, `tool_search.py`, `close_preview_tool.py` all have **0** direct imports from `workstation`.
  - `audit_hermes_seams.py --strict` passes with 0 unclassified seams and 0 budget regressions.


## HW-028 — Semantic seam registry / causal upstream migration (2026-09-19)

H-078B refines HW-026/HW-027 after a three-tree code-to-code audit.

The canonical machine-readable registry is now
`hermes.workstation.first-party-seams.v2`. The policy unit is no longer merely a file:
each path may contain multiple semantic concerns with independent owners, required causal
ordering, dispositions, replacements, parity tests and sunset conditions.

Newly explicit high-risk seams:

- `run_agent.py` batch admission / execution scope / route authority;
- `tool_executor.prepare_mutation` exact authorized-pre-I/O checkpoint;
- internal compiled execution persistence ownership;
- completion admission before canonical DONE;
- trusted TurnIngress and turn-scoped route authority.

Newly strengthened REMOVE paths:

- post-effect/raw-result observation -> raw `post_tool_call`;
- provider wire projection -> `llm_request` middleware;
- `work_execute` -> plugin tool registration;
- Workstation web APIs -> plugin dashboard router;
- forced Browser schemas -> broker/controller capability exposure.

Browser target becomes:

```text
generic browser_tool
-> browser_extension_router
-> BrowserControlBroker
-> WorkstationBrowserController
-> Workstation Electron native runtime
```

The broker owns routing/controller identity/dispatch/fail-closed; Workstation owns
BrowserTask/page/native Chromium/human control/persistence/semantics/recovery.

Migration shadow rule: reads may be compared; **mutations are executed once only**. The
shadow path may resolve/predict controller and fail-closed outcome but cannot perform the
second click/type/submit.

The downstream H-078 branch must be reconciled with current main before integration, and
the upstream SHA must be freshly selected/pinned for the cycle rather than inherited from
the research snapshot.


## HW-027 — Minimum necessary first-party seam policy (2026-09-19)

Decision: D-027. Policy:
`context/FIRST_PARTY_SEAM_POLICY.md`. Registry:
`first_party_seams.json`.

H-078 is refined from "retire direct seams progressively" to **minimize accidental seams
while preserving the narrow first-party seams required for product capability**.

This matters because the Workstation Browser currently depends on capabilities that are not
equivalent to renderer-level plugin extensibility: Electron main-process ownership of a
persistent `WebContentsView`, BrowserTask/page identity, background continuity,
take/release control, stale-run fencing, Hub <-> Chat viewport transfer, native IPC and
recovery. The modern upstream Plugin SDK can replace some presentation-layer seams, but it
must not be assumed to replace privileged native lifecycle.

Source seams now receive one disposition:
- `REMOVE` — generic existing surface has full parity;
- `UPSTREAM_ABSTRACT` — add/use a small generic extension boundary;
- `PRESERVE_FIRST_PARTY` — keep a narrow first-party integration because higher layers
  cannot preserve equivalent behavior.

The seam budget requires rationale, concentration, behavioral tests, delta registration and
re-evaluation every upstream cycle. No proven Workstation capability may be downgraded to
achieve a zero-diff or plugin-purity goal.

## HW-026 — Upstream Migration as Decoupling / seam-retirement program (2026-09-19)

Decision: D-026. Canonical:
`context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md`.

This delta changes how future downstream deltas are integrated. The next upstream sync
must not mechanically reconstruct old Workstation imports inside the upstream's newly
decomposed modules. Each touched overlap is classified as `ADOPT_UPSTREAM`,
`KEEP_WORKSTATION`, `SEMANTIC_PORT`, or `EXTRACT_BOUNDARY`.

Current high-value inward seams observed on the downstream baseline:
- `agent/conversation_loop.py` -> Workstation turn preparation/routing/continuation;
- `agent/tool_executor.py` -> durable execution, mutation preparation/recording and raw
  result capture;
- `agent/turn_finalizer.py` -> Workstation completion/procedure learning;
- `tools/browser_tool.py` -> Workstation Browser routing and Workstation-owned
  artifact/task helpers.

The preferred target for these seams is the generic Hermes extension surface already
present in the fork/upstream: lifecycle hooks plus `tool_request/tool_execution` and
`llm_request/llm_execution` middleware, with browser/provider boundaries where
appropriate. Workstation becomes the subscriber/supervisor; generic Hermes core should
not know Workstation identity.

Initial migration guardrail:
`workstation/scripts/audit_hermes_seams.py` reports direct generic-core ->
`workstation.*` imports and edge references so a migration can prove the inward seam
surface is shrinking.

This is not yet a claim that any runtime seam has been retired. Old paths remain
authoritative until shadow/parity and Workstation qualification prove the replacement.

## HW-025 — H-071 Browser operational admission corrective closure (2026-09-19)

Downstream base: `main@6328894c0a5f51a61da772593842c25d377d553f`.
Branch: `codex/browser-operational-admission-closure`.
Extends HW-024 in `CertifiedDispatcher`, TaskCompiler, OperationalKernel, execution
policy, Browser tool/runtime and reference plane. ACK is no longer proof; compositions
execute and verify; authority has trusted provenance; mandatory compilation requires
closure; native readback is same-origin/reference-first/fail-closed. No new store,
browser engine, policy plane or model tool was introduced.


## HW-024 — Browser Operational Admission & Primitive Closure (2026-09-18)

Downstream base: `main@63fa4244a3c5c1a30ec766fc9023437f61fdff62`.
Branch: `fix/browser-operational-admission-p0`.
Canonical plan: `context/BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md`.
Decision: `D-021`.
Engineering evidence: H-070.


**Post-merge qualification note (2026-09-19):** implementation landed in PR #29,
but H-071 reopened product qualification. The list below records the intended/landed
adaptations, not proof that every invariant is currently satisfied. Audit found:
COMPOSE may commit without executing its plan; ACK may be treated as verifier success;
authority can still be synthesized from request/task/session defaults; mandatory
compilation does not yet require full operational closure; native Browser HTTP readback
is not yet same-origin/policy/fail-closed end to end; terminal families are too broad;
and exact-head Linux/Windows integration checks fail the `browser_type` patch anchor.
HW-024 remains an active downstream delta until those contracts and candidate-head gates
are green.


Production adaptations landed (final contract/product qualification reopened by H-071):

1. **Effect Truth & Dynamic Resolvers:**
   - Files: `tools/registry.py`, `tools/effects.py`, `tools/read_preview_tool.py`, `tools/read_window_tool.py`, `tools/drive_preview_tool.py`.
   - Invariant: `read_preview` and `read_window_below` explicitly registered with `effect=ToolEffect.PURE_READ`. ToolEntry supports dynamic `effect_resolver: Callable[[dict], Any]`. Multi-action `drive_preview` classifies `"elements"` as discovery/read and mutations as `MUTATION`. Fail-closed unknown effect defaults preserved.

2. **Semantic Admission & Execution Policy:**
   - File: `workstation/execution_policy.py`.
   - Invariant: Structural repetition without positive semantic homogeneity never triggers `REQUIRE_COMPILE`. `write_file`/`patch` scoped to `filesystem.file:<normpath>` and `terminal` scoped to command families. Homogeneous repetition with operational closure retains compilation gating.

3. **Native Chromium Plain-Text Paste & Read HTTP Primitives:**
   - Files: `apps/desktop/electron/workstation-browser-runtime.ts`, `tools/browser_tool.py`, `workstation/operational_kernel.py`.
   - Invariant: `browser_type` supports `mode="plain_text_paste"` with first-party synthetic DOM `ClipboardEvent("paste")` + `DataTransfer` (no system clipboard pollution) and pre-action semantic anchor re-acquisition. `browser_read_http` provides GET/HEAD only readback inside page context with loopback and private IP blocking, plus ArtifactStore spillover for large payloads.

4. **Trusted Authority Narrowing & Certified Dispatch:**
   - Files: `workstation/control_plane/lattice.py`, `workstation/control_plane/dispatcher.py`, `workstation/task_compiler.py`.
   - Invariant: Ambient authority resolved from trusted task context; requested authority can ONLY narrow permissions (`trusted.narrow(requested)`); untrusted minting fails closed with `ASK_HUMAN`. All route execution routes through `CertifiedDispatcher` enforcing `PREPARED -> DISPATCHED -> ACKNOWLEDGED -> VERIFIED -> COMMITTED`.

5. **Effect-Sensitive Timeout & SPA Readiness:**
   - Files: `tools/browser_workstation.py`, `apps/desktop/electron/workstation-browser-runtime.ts`.
   - Invariant: Mutating browser calls timing out raise `TIMEOUT_UNCERTAIN` (`state_changed=True`, `retryable=False`), blocking blind retry without external reconciliation. Electron snapshot performs bounded re-observation (< 1.2s total) for hydrating SPAs.


## HW-023 — Upstream reliability hardening P0 lane (2026-09-18)

Downstream base: `main@03e06cfd8c94e5a7627c288c8eddfd5d4c5c8033`.
Branch: `fix/workstation-upstream-reliability-p0`.
Canonical plan: `context/UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md`.
Engineering evidence: H-065, H-066.

Production adaptations implemented and contract-verified:

1. **Native Browser Task Smoke Probe & Real Discriminators (#114964-derived):**
   - Commit: `2e3f5a058d` (`test(workstation): harden native browser task smoke probe with real discriminators`).
   - File: `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`.
   - Invariant: live `webContents` id, timer counter, input value, scroll position, and loopback controller action execution (`browser_snapshot`, `electron-chromium`) survive across hide/show and park/show without falling back to external browsers.

2. **In-Flight Turn Journal Recovery Tail & Deduplication (#115068):**
   - Commit: `fd2651d7bd` (`fix(desktop): restore live projection tail and prevent interim row duplication in in-flight journal`).
   - Files: `apps/desktop/src/lib/inflight-turn-journal.ts`, `apps/desktop/src/lib/inflight-turn-journal.test.ts`.
   - Invariant: `mergeInFlightMessages` selects last live projection row via `findLastIndex` and filters duplicate sealed IDs via `withoutBaseIds`.

3. **Optimistic Pending User Message Retention on Resync (#115085):**
   - Commit: `ca90122d89` (`fix(desktop): preserve optimistic pending turn messages during background transcript resync`).
   - Files: `apps/desktop/src/app/contrib/hooks/use-background-sync.ts`, `apps/desktop/src/app/contrib/hooks/use-background-sync.test.ts`, `apps/desktop/src/app/contrib/wiring.tsx`.
   - Invariant: unacknowledged optimistic user messages are retained across background resyncs until authoritative ACK.

4. **One Canonical Writer Per Session & Read-Only Observer Resume (#111493):**
   - Commit: `511117ec19` (`fix(active_sessions): enforce one canonical writer per session and read-only observer resume`).
   - Files: `hermes_cli/active_sessions.py`, `cli.py`, `tests/hermes_cli/test_cli_resume_read_only_owner.py`.
   - Invariant: single live writer exclusivity per `session_id`, read-only observer resume (`mode="observer"`), foreign writer transfer fencing, and fail-closed corrupt registry handling.

5. **Kanban Session Provenance, Heartbeat Fence & Durable Exit Evidence (#114785, #114793, #114904):**
   - Commit: `fd38773cd3` (`fix(kanban): validate session provenance, harden worker heartbeat, and record durable exit evidence`).
   - Files: `tools/kanban_tools.py`, `hermes_cli/kanban_db.py`, `cli.py`, `tests/hermes_cli/test_kanban_provenance_and_exit_evidence.py`.
   - Invariant: session provenance is verified against SessionDB and prefers request-scoped ContextVar; heartbeat requires both claim and worker writes and fences delegated children; durable worker exit trailers (`HERMES_WORKER_EXIT_TRAILER_V1`) provide cross-process exit classification.

6. **Bounded CDP Supervisor Reconnect Budget (#114897):**
   - Commit: `285675418b` (`fix(browser): cap post-attach CDP supervisor reconnect attempts and evict on terminal failure`).
   - Files: `tools/browser_supervisor.py`, `tests/tools/test_browser_supervisor_reconnect_cap.py`.
   - Invariant: post-attach reconnect attempts capped at 5 with supervisor eviction from registry and credential redaction in logs.

Remaining P1 lane: Durable Delivery Rail (#115009/#115010/#114780) and snapshot quality/freshness benchmark (#115056) are planned for follow-up PR B.

## HW-022 — Verified procedure admission and planner context (2026-09-16)

Downstream base: `a977651539dd4b793e26f96c6116bce187677cc9`.
No new upstream comparison, wholesale file replacement or upstream merge.

Core adaptations: `agent/conversation_loop.py` projects authenticated durable state
on a copy immediately before provider sanitation/cache decoration. Automatic
`agent/conversation_compression.py` uses a deduplicated durable handoff when available;
manual force, commit fences and ordinary compression retain their existing paths.
`agent/context_compressor.py` is reused without modification for trusted references
and real-user turn identification. SessionDB history and cached system text remain.

`agent/tool_guardrails.py` scopes failures by structural ExperimentKey and verified
progress generation. Item values are excluded; selectors, commands, graph tool
identity/order/multiplicity and verifier expectations distinguish hypotheses.
Arbitrary tool output cannot declare progress. `agent/tool_result_classification.py`
uses canonical effect metadata instead of a second no-effect name whitelist.
`tools/registry.py` assigns first-party effects on registration; `tools/effects.py`
covers instructional reads and vision, with conservative unknown write capability.
`tools/workstation_work.py` exposes the bounded contract and recipe arguments through
the existing session-gated tool, without adding core tools or changing toolsets.

Canonical compiler/store/graph extensions and the seven-case Trello replay are
downstream-owned. TurnConstraintContext was already correctly scoped: real two-turn
tests prove reset and auxiliary route propagation; its lifecycle was not rewritten.
Workstation CI retains locked uv sync and adds the controlled replay and path filters
for affected core seams. See engineering journal for exact GitHub evidence.

Promotion gate follow-up extends Desktop-owned helpers: Windows secret-file mode
checks reject symlinks before the chmod no-op, and BrowserRuntime emits typed
human-control faults through the existing controller contract. First-launch E2E
checks visible setup/recovery or completed boot instead of arbitrary shell text;
stable UI selectors are additive. Windows qualification has an explicit bounded
900s timeout for the full suite (local Windows run measured 448s), Dashboard smoke
builds canonical web assets, and load evidence validates from repository cwd.
No gate, scope check, permission guard or uncertain replay protection is removed.

## HW-021 — Final durable graph/effect/turn hardening (2026-09-16)

Audit base: `17df394cfe3e913e6fce6f3130e3efc47e4592a2`, equal to fetched origin/main.
Focused upstream guardrails: `4716ec0ba4e212105f8f162c226f052b25f8a76b`.
No blind merge or downstream file replacement.

Core seams: `tools/effects.py` plus `tools/registry.py` add operator/plugin effect,
idempotency-key and provider-route metadata without enlarging LLM schemas.
`tools/mcp_tool.py` retains read hints on live/lazy-cache registrations while
preserving trust authorization. `agent/tool_executor.py` records successful
pre-compilation mutation artifacts; `run_agent.py` detects structural fan-out,
allows discovery beside rejected writes, carries adopted results, checks tool
routes and guards streaming/non-streaming provider calls. `agent/conversation_loop.py`
establishes TurnConstraintContext before provider selection; scoped ambient context
in `run_agent.py` and `agent/auxiliary_client.py` covers auxiliary resolver/cache
routes. `agent/chat_completion_helpers.py` prunes forbidden fallback entries before
client/credential resolution. ModelRouter shares the provider-route normalizer.

Guardrail adaptation centralizes upstream FAILURE_TOLERANT_TOOL_NAMES and
PROGRESS_RESET_TOOL_NAMES, and adds platform-aware non_interactive_hard_stop_enabled.
`agent/agent_init.py` uses that config instead of a separate environment/platform
override. Existing identical/cycle detection, downstream pollers and loop caps
remain. Unlike upstream blanket command-success reset, downstream requires trusted
delta/checkpoint or canonical landed file-write evidence.

Workstation additions extend existing compiler/runner/store: phase WorkItems,
bounded topological DAG, reference bindings, phase gates/checkpoints, graph ledger
and tool-owned connection closure. Linear plans remain compatible. Tests:
`test_durable_hardening.py` and controlled `benchmarks/trello_regression.py`.
CI uses the existing pinned setup-uv action/retry convention and uv.lock;
no individual missing dependencies are added manually.

## HW-020 — Durable execution boundary (2026-09-16)

Audited fork base: `3344e67fb67a3f9d2e89fa08707325807449d9b8`.
Restricted upstream comparison: `4e9d3c713a` (fetched upstream/main).
No merge/rebase or wholesale file replacement was performed.

Maintained core seams: `agent/conversation_loop.py` detects conservative repetitive
requests and records provider-reported usage for assistant persistence;
`run_agent.py` requires compiled mutations when the session has work_execute,
binds the existing scoped dispatcher, attaches trusted KanbanRun refs and forwards
token_count on flush. `agent/tool_executor.py` preserves pre-spill verifier input
and prevents private WorkItem messages from becoming unpaired transcript rows.
`toolsets.py`/`tools/workstation_work.py` add a session-selected desktop_ui capability,
never a new core tool. `tools/file_tools.py` adds hash/ref projection only for durable
reads, preserving legacy behavior/security/read stamps. `tools/tool_search.py` adds
Desktop session/profile/schema-addressed descriptions and explicit full reload.
`tools/browser_workstation.py` enforces constrained/durable internal routes before
probes or fallback.

Carefully adapted upstream guardrail behavior in `agent/tool_guardrails.py`:
period-2–4 identical cycles, identical-call halts, failure-tolerant distinct shell
commands and progress reset. Downstream tool names and poller exemptions remain.
`agent/agent_init.py` defaults unattended platforms to hard stops, respecting explicit
configuration and attended CLI/TUI/Desktop/subagent behavior. Verified checkpoint
progress is an explicit runtime signal; arbitrary result text cannot assert it.

Compressor comparison found substantial upstream refactoring; the fork's trusted
operational-ref boundary was preserved and reused. Storage comparison showed that
the scoped content-addressed downstream spillover extensions would disappear with
wholesale upstream replacement, so they were preserved. SessionDB already accounts
canonical provider usage: the missing per-message token_count came from the flush
payload, not a need to replace SessionDB. No new session/board/browser database.

Base: `NousResearch/hermes-agent@057dcdf236f8a6a26721c10fcc6ccb72726e272a`

| ID     | Area                                            | Downstream change                                                                                                                                                                                                                                                                                                    | Why core-level                                                                                                                                                                                                                   | Upstream candidate |
| ------ | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| HW-001 | Desktop main                                    | Load Workstation Browser runtime IPC                                                                                                                                                                                                                                                                                 | Browser is a first-class Desktop subsystem                                                                                                                                                                                       | Maybe              |
| HW-002 | Desktop preload                                 | Expose narrow Browser runtime bridge                                                                                                                                                                                                                                                                                 | Native view is owned by Electron main                                                                                                                                                                                            | Maybe              |
| HW-003 | Desktop routes/sidebar                          | Add `/browser` as core page/nav item                                                                                                                                                                                                                                                                                 | Workstation Browser is non-optional in this distribution                                                                                                                                                                         | No                 |
| HW-004 | Desktop surfaces                                | Render Browser page as built-in workspace page with host-aware native viewport geometry, native content clamping and resize/maximize/restore reconciliation, so stale Chat/Hub updates cannot move the single live `WebContentsView`                                                                                                                                          | Same reason as HW-003; host ownership and native window transitions must be enforced at the shared Desktop surface boundary                                                                                                                                                                  | No                 |
| HW-005 | Desktop Kanban plugin                           | Enable bundled Kanban by default                                                                                                                                                                                                                                                                                     | Kanban is Workstation task source of truth                                                                                                                                                                                       | Maybe              |
| HW-006 | global.d.ts                                     | Type the Browser IPC bridge                                                                                                                                                                                                                                                                                          | Required by HW-002                                                                                                                                                                                                               | Maybe              |
| HW-007 | Browser tool registry                           | Prefer Workstation Chromium before extension/legacy lanes                                                                                                                                                                                                                                                            | Browser must be a first-class agent capability                                                                                                                                                                                   | Yes                |
| HW-008 | CLI config example                              | Document `browser.workstation` defaults                                                                                                                                                                                                                                                                              | Makes routing/fail-closed behavior explicit                                                                                                                                                                                      | Yes                |
| HW-009 | Root `AGENTS.md`                                | Point coding agents at the downstream Workstation operational context/read-order                                                                                                                                                                                                                                     | Prevents downstream architecture changes from being made from upstream-only context                                                                                                                                              | No                 |
| HW-010 | GitHub Actions / Windows bootstrap                | Windows Workstation gate installs/tests the committed downstream tree and runs the strict doctor; the user-facing one-click bootstrap delegates to that same strict doctor before start, while the gate exposes focused Browser foundation lifecycle/session-state results and fails if install dirties the checkout | Prevents CI or the user-facing launcher from silently proceeding past a broken dependency/integration state while keeping scoped native-browser regressions visible beside known broad Windows failures | Maybe              |
| HW-011 | Tool schema assembly / registry                 | Preserve selected Workstation Browser schemas from session-scoped Desktop capability and fingerprint that capability in the tool-definition cache                                                                                                                                                                    | One gateway serves multiple client surfaces; transient controller reachability must not erase a valid Desktop schema or leak it across sessions                                                                                  | Yes                |
| HW-012 | Desktop Browser runtime / BrowserTask lifecycle | Add first-class BrowserTask metadata/lifecycle (`create`, `show`, `hide`, `park`, explicit `destroy`, crash recovery and safe logical restart restoration) around the existing `taskTabs` + `BrowserEntry.ownerTaskId` page ownership primitives, with focused runtime/persistence regression tests                  | BrowserTask semantics must be owned where Electron `WebContentsView` lifetime and task→page binding are enforced; implementing it only in downstream wrapper code would duplicate browser state or lose native lifecycle control | Maybe              |
| HW-013 | Desktop Browser runtime / BrowserSessionState   | Add one composite, versioned BrowserSessionState restart projection for ordinary/task logical tabs, order, active selection, sanitized restorable URL metadata and BrowserTask snapshot, including atomic-replacement recovery semantics that preserve the latest in-process intended projection after failed writes | Electron main owns the live page/runtime facts needed to derive and reconcile restart state; a wrapper-side store would duplicate page/task authority and cannot correctly preserve lazy task ownership                          | Maybe              |
| HW-014 | Desktop packaged/dev E2E harness                  | Inject Playwright's Electron loader when launching the packaged executable through a custom `executablePath`, isolate the Workstation Browser state/profile per sandbox, and resolve both workspace-local and Windows `.exe` Electron development binaries | Playwright only auto-injects its loader for the npm Electron binary; the real packaged executable otherwise starts without `__playwright_run()`, while workspace-local npm installs and Windows executable naming must also resolve to the same hidden dev runtime | Yes                |
| HW-015 | Workstation resource/event projection / client adapters | Expose the Electron-owned BrowserTask and Execution Journal projection through versioned loopback `/resources` and bounded `/events` endpoints, Desktop IPC, Dashboard REST and TUI JSON-RPC adapters, with a Dashboard recent-events view | Resource identity, permissions, lineage and operational events must be resolved from one browser/runtime authority across clients; keeping this adapter outside `workstation/` preserves upstream Hermes' narrow core and avoids a second task/journal store | Maybe              |
| HW-016 | Dashboard cross-engine E2E harness                 | Add a provider-free, isolated Playwright smoke for the built Dashboard served by the real Python backend in Chromium and Firefox, with Edge when the supported system browser is available | Cross-engine client compatibility is a Workstation acceptance gate, while the reusable harness/config belongs at the Desktop/Dashboard integration boundary rather than in the Python contract layer | No                 |
| HW-017 | Release qualification / bounded soak               | Add an evidence-producing release gate runner and bounded-duration soak metrics without mutating the checkout or inferring clean-machine results; execute the canonical four-session reconnect soak, the hidden-window native Electron Browser runtime reconnect soak, a real headless `hermes serve` multi-session/reconnect soak, and an integrated hidden-window Desktop/Browser load E2E in the Windows release workflow while retaining their JSON/durable evidence artifacts; let H013 select a bounded larger task/round/duration profile in candidate CI | Release promotion needs reproducible, reviewable evidence while clean-install and full agent/backend production-like Desktop/Browser load remain explicit acceptance boundaries; the backend probe and the integrated E2E extend evidence at the actual gateway/Chromium boundary without adding a second runtime owner, and explicit CI parameters distinguish a stronger release profile from the fast local regression | No                 |
| HW-018 | Desktop Windows portability closure                 | Make Desktop path, permission, Git, SSH, WSL, staging and deterministic-format contracts valid on Windows while preserving explicit POSIX and no-mux behavior | These are Desktop-owned runtime/test boundaries; fixing them at the integration edge removes the broad Windows gate debt without widening Hermes' core tool surface | Maybe              |
| HW-019 | Canonical Kanban Hybrid workspace                  | Add additive Hybrid board/column/card/activity tables to the existing per-board Kanban SQLite schema, a transaction-backed shared domain service, authenticated plugin routes, a service-gated agent tool and a Desktop projection that uses semantic moves rather than client ranks | Human and agent must mutate one canonical work domain without changing Agentic `tasks.status`; the existing Kanban DB, transaction and plugin transport are the only safe common seam | Maybe |

Operational context, engineering journal/probes, tests, migration helpers, and other files under `workstation/` are downstream-owned and do not add rows by themselves. Keep this list small. New edits outside `workstation/` require a row or an explicit expansion of an existing row.

HW-010 also covers the Windows workflow's fresh `RUNNER_TEMP` Workstation
home, persisted through `GITHUB_ENV` and shared by install and strict doctor;
the default user-facing `%LOCALAPPDATA%` path remains unchanged.

HW-017 also covers the release workflow's explicit isolated validation-dependency
step: the production Workstation install remains runtime-only, while the
candidate gate installs the pinned `[dev]` extra into `.venv` before invoking
the Python contract runner, so clean candidates do not fail merely because
`pytest` is absent from the runtime environment.

HW-017 also covers the production-only npm audit gate and the lockfile refresh
that closes the transitively reported `nanoid`, `sanitize-html` and `colord`
advisories without changing package manifests or enabling forced upgrades.

## Promoted browser-foundation evidence boundary

HW-012 was validated by the focused automated BrowserTask tests and the real Windows/Electron H004 lifecycle smoke recorded in `workstation/context/TESTING.md` and `workstation/context/engineering-journal/CURRENT.md`.

HW-013 is validated and promoted through PR #11. Exact head
`d5be442021ea0c744351622317eef5212219786d` passed static/focused gates and
the real Windows/Electron H010 clean/fault/abrupt restart probe; merge
`e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29` is reachable from `main`.
The composite persistence adapter preserves HW-012 live ownership rather than
becoming a second BrowserTask/page store.

Neither promotion makes Browser Hub, Chat Browser View, Preview unification,
single-host transfer or complete Kanban/run integration part of the existing
delta. Those require their own V1 #1.5 rows/expansions when implemented.

## Canonical Work Loop working-tree seams (2026-09-17)

Additive canonical acceptance table/gates and Hybrid completion projection;
existing verification DB outcome events; shared ToolCallGuardrailController
WorkItem systemic failures; tool_contract introspection defaults; artifact refs
in read_file; cron drift migration metadata; SessionSearchMixin compacted dedup;
authenticated cockpit route in web_server. Provider schemas/system prompts,
SessionDB history and authorized red-team harness are unchanged. See
[implementation scope](context/CANONICAL_WORK_LOOP.md).
# Read-only durable preflight — 2026-09-17

Core seams: `run_agent.py` keeps discovery alive after refused compilation;
`agent/turn_constraints.py` parses mutation-scoped route restrictions without
changing global restrictions; `agent/conversation_loop.py` resets per-conversation
effect evidence; `tools/effects.py` separates method/channel capability evidence;
`tools/browser_tool.py` reuses structured extraction for Workstation inspection.
Canonical compiler/store checkpoints own persistence and restart behavior.
See `context/READONLY_DURABLE_PREFLIGHT.md` and `test_readonly_preflight.py`.
