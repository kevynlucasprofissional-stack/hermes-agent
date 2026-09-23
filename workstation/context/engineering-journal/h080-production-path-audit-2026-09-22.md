# H-080 — Production-Path Qualification Audit

Date: 2026-09-22

Status: **ARCHITECTURE SOUND / CONTROL-PLANE E2E IMPROVED / PRODUCTION-PATH PROOF STILL OPEN**

Audited implementation branch:

`integration/upstream-20260922-71a2fe39-h0793`

Audited branch head:

`89a745d2ee0346c7030134c10b24071ce9e234f1`

Shared main at audit time:

`df2222caf843479b5315a0aaa8d0a1df32735f01`

Branch relation at audit time:

`24 ahead / 0 behind`.

Frozen upstream pin:

`71a2fe399bbd7a219c71f9d9fca2b313b01f2057`

True upstream merge:

`a8dfcd21f5c641d01a5989e223a987687018db7f`

Latest upstream observed during this audit:

`d3b25b52ad1318c526bdb259b600eeca3d5f38e6`

Drift from the frozen pin: 23 upstream commits, with no overlap in the four H-080 upstream-owned intervention surfaces:
- `agent/conversation_loop.py`
- `agent/operational_resolution.py`
- `agent/turn_operational_resolution.py`
- `tools/browser_tool.py`

Classification at audit time: **NON_OVERLAPPING**. Re-run immediately before promotion.

## What is genuinely fixed

The correction work after the first branch audit materially improved the implementation.

1. **E001 no longer short-circuits through SATISFIED.**
   The test now begins from `semantic_state={"route_artifact": {"exists": False}}` while the goal is `EXISTS("route_artifact")`. A capability path is therefore required for deterministic completion.

2. **Verifier-failure E2E is no longer an empty test.**
   `test_verifier_failure_no_commit` now drives a normal turn, forces canonical verification to FAILED, records one dispatch callback invocation and asserts zero provider calls.

3. **Intervention registry scope/provenance is corrected.**
   `workstation/upstream_interventions.json` now contains four upstream-owned interventions only, all attributed to feature commit `9c217afbc84e89acb32f83043f800ad6df9eb55d`.

4. **Operational-resolution seam is registered.**
   `SEAM-OPERATIONAL-RESOLUTION` now exists in `workstation/first_party_seams.json` as `UPSTREAM_ABSTRACT`.

5. **Browser ownership/authority remains healthy.**
   Browser result projection is Workstation-owned and focused tests cover exactly-once mutation, never-bound fallback and bound/offline fail-closed behavior.

These corrections mean the architecture should be preserved. The remaining work is production-path proof, not another redesign.

## Remaining blocker A — production authority is injected by the E2E

The current E001 monkeypatches `TaskCompiler.execute` and assigns:

```python
self.trusted_authority = AuthorityScope(
    level=AuthorityLevel.EXTERNAL_REVERSIBLE,
    allowed_actions={"browser.navigate"},
    allowed_resources={TARGET},
)
```

This means the test does not yet prove that a normal authenticated turn naturally supplies the authority required by a promoted mutating capability.

Production `TaskCompiler._execute_route()` resolves trusted authority in this order:

```text
self.trusted_authority
-> canonical task.authority_scope
-> READ
```

At audit time:
- `hermes_cli/kanban_db.py` contains no canonical `authority_scope` task field/path;
- `workstation/kanban.py` does not persist an `AuthorityScope`;
- `workstation/work_intent.py` establishes trusted `MessageEnvelope` / `IntentAuthority`, but does not bridge that ingress trust to the control-plane `AuthorityScope`.

Therefore the current mutable E2E proves an **assisted authority path**, not the actual production grant path.

Required correction:
- find the smallest existing trusted owner from which a control-plane `AuthorityScope` can be derived or referenced;
- if no canonical owner exists, add the minimal explicit bridge at trusted ingress/task admission;
- never derive broad mutation authority from raw user prose;
- never equate `IntentAuthority.CREATE_WORK` by itself with unrestricted `EXTERNAL_REVERSIBLE`;
- preserve narrowing semantics: request/intent may narrow trusted authority, never expand it;
- remove the `TaskCompiler.execute` monkeypatch from the release E2E.

The release test must succeed using the same authority source that production uses.

## Remaining blocker B — physical dispatch is replaced by a recorder

The current E001 patches:

`workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch`

to return `_DispatchRecorder`.

This proves the normal turn reaches the control-plane dispatch callback exactly once, but it does not prove the real Hermes dispatcher path:

```text
workstation_durable_dispatch
-> tool-scope validation
-> tool_call wrapping when needed
-> execute_tool_calls_sequential
-> guardrails / approval / route policy
-> raw post-tool observation
-> take_raw_result
```

The fixture also patches `model_tools.get_tool_definitions` to `[]` and leaves `agent.valid_tool_names = set()`, which would not constitute a realistic admitted primitive for the real durable dispatcher.

Required correction:
- add at least one normal-turn E2E that uses real `workstation_durable_dispatch()`;
- expose a harmless real primitive through the actual tool catalog/session scope;
- prefer a local reversible temp-filesystem primitive if that is a real admitted route; otherwise use the smallest safe production primitive;
- instrument only the lowest physical handler or safe local effect, not the durable dispatcher itself;
- prove exactly one real tool execution and raw-result capture.

## Remaining blocker C — causal claims are stronger than the asserts

The E001 docstring/report claims:
- `routing_decision == EXECUTE`;
- valid RoutingCertificate;
- canonical `VERIFIED`;
- `accepted == true`;
- dispatch `COMMITTED`;
- provider calls 0.

The current assertions directly prove only:
- provider calls 0;
- turn completed/not failed;
- final response text contains verified/completed language;
- supplied dispatch callback called exactly once.

`TaskCompiler._execute_route()` already returns the missing causal markers, but `workstation_operational_resolution()` currently projects only task/plan/routing-decision into `OperationalResolution.details`.

Required correction:
- expose non-authoritative observability fields in `OperationalResolution.details` (or another existing diagnostic surface), such as capability id, certificate hash, verification status, verification accepted and dispatch status;
- do not use those diagnostic fields for routing or authority;
- assert the real causal values directly in E001;
- in E003V, assert the dispatch record is not COMMITTED success after FAILED/INCONCLUSIVE verification.

## Remaining blocker D — scratch release artifact still exists

`workstation/tests/test_zz_scratch_route_fixture.py` remains present.

Its direct-route proof is useful, but it must be either:
- absorbed into the canonical E2E/control-plane suites and removed; or
- renamed/restructured as a permanent semantic regression test.

Do not promote an explicitly scratch-named test as release evidence.

## Metrics truth

`agent/operational_resolution.py::operational_resolution_metrics()` currently exposes:
- steps
- attempts
- hits
- misses
- errors
- self_reported

A `hit` is a terminal operational resolution and is not itself equivalent to `EXECUTED+VERIFIED`.

Statements such as `llm_calls_per_verified_outcome = 0` for E001 are test observations, not yet runtime telemetry.

Do not create a second metrics subsystem. Wire/derive the required measures through existing generic resolution counters plus Workstation ORA/VOLC owners:
- verified deterministic executions;
- failed/inconclusive deterministic executions;
- reasoning fallbacks;
- LLM calls per verified outcome/completed item;
- coverage/novelty only when a real denominator exists.

Unknown remains `None`, never invented zero.

## H-080 lane split

The audit distinguishes two closures:

### H-080A — Pre-reasoning capability reuse

Can close after:
- real production authority reaches the route without monkeypatch;
- real `workstation_durable_dispatch` path is exercised by a normal-turn E2E;
- direct causal asserts prove EXECUTE, certificate, VERIFIED+accepted, COMMITTED and provider calls 0;
- verifier-failure E2E proves not-COMMITTED and no blind retry;
- scratch artifact is removed/normalized;
- exact-head focused/full tests, strict seam audit and GitHub CI are green;
- final upstream drift remains classified.

### H-080B — Experience feedback-loop closure

Remains OPEN until one end-to-end experiment proves:

```text
novel verified execution
-> TransitionSample / ExperienceCorpus
-> compile
-> causal/controlled replay
-> verifier validation
-> ExperiencePromotionPolicy
-> PROMOTED capability
-> future equivalent normal Hermes turn
-> EXECUTE / VERIFIED / COMMITTED
-> provider calls = 0
```

H-080A may be promoted independently if its exact scope is documented truthfully. Do not call Progressive Operational Compilation end-to-end closed while H-080B remains open.

## Promotion order

```text
merge current main docs/state into feature branch
-> implement trusted authority bridge / remove authority monkeypatch
-> add real durable-dispatch E2E
-> expose causal observability + strengthen E001/E003V asserts
-> absorb/rename scratch test
-> wire truthful metrics to existing owners
-> focused operational tests
-> Browser regressions
-> strict seam audit
-> full Workstation + affected upstream-owner tests
-> final upstream drift check
-> open PR
-> exact-head GitHub CI
-> promote H-080A only if green
-> continue H-080B separately
```

## Promotion rule

Do not merge H-080A while the only mutable normal-turn proof requires injected control-plane authority or a replacement durable dispatcher.

## Additional blocker E — E001 pre-seeds verification evidence

The current E001 fixture persists `verification_evidence` in the objective **before execution**. The evidence already claims:
- expected value present;
- `read_after_write=True`;
- trusted owner/source-of-record provenance;
- covered predicate fingerprint;
- matching task/run/operation lineage.

`OperationalKernel.execute_capability()` consumes `exec_context["verification_evidence"]` directly when supplied and therefore does not run a real post-effect observer in that case.

This means E001 can obtain a canonical VERIFIED result from synthetic preloaded evidence even though the claimed readback did not occur after the mutation.

Required correction:
- remove pre-seeded success `verification_evidence` from the release E2E;
- use an actual post-effect observer/readback owned by the runtime;
- never manufacture `read_after_write`, trust class, coverage or provenance from expected values.

Preferred minimal proof decomposition:
1. **E001F — filesystem deterministic reuse:** use a `filesystem` capability with a harmless `fs_write` to `tmp_path`, `LOCAL_MUTATION` authority, and the kernel's real builtin `fs_stat`/filesystem readback after the write. This proves production authority -> route -> certificate -> kernel mutation -> independent canonical verification -> COMMITTED -> 0 LLM without synthetic evidence.
2. **E001D — durable dispatcher parity:** separately exercise real `workstation_durable_dispatch` with a real admitted tool through `execute_tool_calls_sequential`; instrument only the lowest safe handler/controller, never replace the dispatcher. For Browser, reuse a deterministic fake `BrowserControlBroker` controller rather than network/runtime I/O.

A single combined Browser test is acceptable only if it can obtain genuine post-navigation readback without pre-seeded evidence. Do not add production-only complexity merely to force one monolithic test.

Implementation note from code inspection:
- `OperationalKernel.execute_primitive()` handles `fs_write/write_file` internally, so a filesystem success test does **not** exercise `workstation_durable_dispatch`; that is acceptable for E001F but must not be mislabeled.
- `todo_list` is an actual always-available registered Hermes tool, is not intercepted by the kernel's filesystem/browser primitives, and is a good hermetic candidate for a separate real-dispatch parity test through `workstation_durable_dispatch -> execute_tool_calls_sequential`. Use its real `TodoStore` revision/state to prove exactly-once mutation. The dispatcher-parity test may intentionally end WAIT/HANDOFF if canonical post-effect verification is unavailable; E001F separately owns verified-success proof.
