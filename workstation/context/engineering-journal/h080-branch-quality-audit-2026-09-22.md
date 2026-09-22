# H-080 — Published Branch Quality Audit

Date: 2026-09-22

Status: **IMPLEMENTATION DIRECTION SOUND / PROMOTION BLOCKED**

Audited branch:

`integration/upstream-20260922-71a2fe39-h0793`

Audited branch head:

`9c217afbc84e89acb32f83043f800ad6df9eb55d`

Shared main at audit start:

`bdd25751088427b83482331aa74a82d24d789cf4`

Merge base:

`4cdf543f9a6627bc00284e61df637054920ed29d`

Frozen upstream pin carried by the branch:

`71a2fe399bbd7a219c71f9d9fca2b313b01f2057`

True upstream merge:

`a8dfcd21f5c641d01a5989e223a987687018db7f`

At audit time the branch was published, had no open PR, had no GitHub Actions/status evidence on its head, and compared to `main@bdd2575...` as 22 commits ahead / 11 behind. Those ahead/behind counts are a dated snapshot and will change as main receives documentation commits.

## Overall assessment

The branch is materially better than the rejected `471e9b5` attempt. The central architecture is now aligned with H-078B/H-080:

```text
conversation_loop
-> generic operational-resolution phase
-> generic provider registry
-> Workstation first-party provider
-> TaskCompiler / CapabilityRouter
-> certificate / CertifiedDispatcher / OperationalKernel
-> canonical verification
```

The generic core does not directly import Workstation for this concern. Raw prose is no longer synthesized into an executable `OperationIntent`; the Workstation provider searches for a previously established durable intent. Browser result projection has also been moved out of generic `tools/browser_tool.py` into Workstation ownership.

This is an implementation to **keep and repair**, not revert.

## Proven strengths

1. **Generic pre-reasoning boundary is correctly placed.**
   `agent/conversation_loop.py` adds only a narrow phase call between preflight and provider execution.

2. **Generic core / Workstation separation is preserved.**
   Generic files own the lifecycle contract; `workstation/integrations/hermes/operational_resolution.py` owns Workstation semantics.

3. **Intent trust improved.**
   The provider consumes durable established intent and rejects trivial/default TRUE goals rather than inventing an intent from raw text.

4. **Existing control plane is reused.**
   Routing continues through `TaskCompiler`, `CapabilityRouter`, certificates, dispatch and canonical verification rather than duplicating decision logic.

5. **Uncertain-mutation handling is more conservative.**
   Runtime uncertainty is passed to the router and unresolved effects prevent another deterministic dispatch lane.

6. **Browser ownership improved.**
   `browser_extract_items` domain projection moved to `workstation/browser_projection.py`; the Workstation controller no longer imports the private projection helper from generic `browser_tool.py`.

7. **Negative coverage is substantially improved.**
   Tests cover no established intent, raw text not becoming intent, trivial TRUE goal, invalid/non-promoted capabilities, uncertain mutations, fallback to provider and generic provider failures.

## Promotion blockers

### B1 — E001 is currently a false positive for the critical claim

`workstation/tests/test_e2e_operational_resolution.py::test_known_promoted_capability_bypasses_llm`

uses a semantic state where the goal is already true:

```text
semantic_state: record.state = written
goal:           record.state = written
```

The router can therefore return `SATISFIED` before candidate execution. The test proves:

```text
already satisfied goal -> provider calls = 0
```

It does **not** prove:

```text
promoted capability -> EXECUTE -> physical dispatch exactly once
-> canonical VERIFIED/accepted -> COMMITTED -> provider calls = 0
```

Required repair:
- initial semantic state must not satisfy the goal;
- prove `routing_decision == EXECUTE`;
- prove physical dispatcher count == 1;
- prove canonical verification `VERIFIED` and `accepted == true`;
- prove dispatch record `COMMITTED`;
- prove provider calls == 0;
- prove finalizer/persistence path remains canonical.

### B2 — Verifier-failure E2E is empty

`test_verifier_failure_no_commit` currently ends in `pass`.

Required proof:
- physical tool handler returns ACK/success;
- canonical verification is FAILED or INCONCLUSIVE;
- dispatch is not accepted as committed success;
- no terminal EXECUTED success is produced;
- no blind LLM retry of the same mutation occurs.

This is a merge blocker.

### B3 — Scratch route fixture must be absorbed or renamed

`workstation/tests/test_zz_scratch_route_fixture.py` proves useful direct routing behavior, including physical dispatch and verification, but is explicitly a scratch fixture and bypasses the normal Hermes turn.

Move the useful proof into the canonical E2E suite or rename/restructure it as a permanent semantic test. Do not promote a `test_zz_scratch_*` artifact as release evidence.

### B4 — upstream_interventions.json contains incorrect provenance

The feature code was introduced in `9c217af...`, but entries currently record:

`downstream_commit_sha = a8dfcd21...`

That SHA is the upstream merge baseline, not the feature commit.

Additionally, the registry was defined for downstream interventions in **upstream-owned code**. Entries for `workstation/**` are downstream architecture changes, not upstream interventions, and should be moved to the appropriate seam/changelog/history record rather than being misclassified.

At minimum upstream intervention candidates are:
- `agent/conversation_loop.py`
- `agent/operational_resolution.py`
- `agent/turn_operational_resolution.py`
- `tools/browser_tool.py`

Use the final semantic commit SHAs after cleanup, not provisional SHAs.

### B5 — seam registry is inconsistent

`workstation/upstream_interventions.json` references `SEAM-OPERATIONAL-RESOLUTION`, but `workstation/first_party_seams.json` does not currently define it.

Add a canonical concern with:
- disposition: `UPSTREAM_ABSTRACT`;
- generic owners: `agent/operational_resolution.py`, `agent/turn_operational_resolution.py`, narrow call site in `agent/conversation_loop.py`;
- first-party provider: `workstation/integrations/hermes/operational_resolution.py`;
- ordering: after turn/preflight admission and immediately before provider call;
- parity tests: normal-turn EXECUTE bypass, no-match reasoning fallback, no fabricated intent, uncertainty no-retry, canonical finalization;
- closure only after behavior is proven.

Do not close a seam merely because files exist.

### B6 — Experience Compiler feedback loop remains open

The branch establishes the pre-reasoning reuse boundary, but does not yet prove the full cycle:

```text
novel verified execution
-> TransitionSample
-> ExperienceCorpus
-> candidate compilation
-> controlled replay / causal validation
-> promotion
-> future equivalent normal turn
-> promoted capability executes
-> provider calls = 0
```

Either implement and prove this cycle in H-080, or explicitly keep this sub-lane OPEN. Do not describe Progressive Compilation as end-to-end closed without it.

### B7 — exact-head promotion evidence is absent

The branch head has no GitHub Actions/status evidence and no open PR. Before promotion:
- reconcile the latest main documentation/state into the branch;
- run focused tests;
- run strict seam audit;
- run Browser qualification;
- run full Workstation regression via the canonical runner;
- run relevant upstream-owner tests;
- inspect exact-head CI;
- perform final upstream drift classification;
- only then open/merge PR.

## Metrics debt

Generic boundary counters currently cover steps/attempts/hits/misses/errors/self-reported outcomes. H-080 still needs truthful operational metrics or explicit derived mappings for:
- capability resolution attempts/hits/misses;
- verified/failed capability executions;
- reasoning fallbacks;
- capability coverage / operational novelty;
- LLM calls per verified outcome;
- LLM calls per completed item.

Unknown usage must remain unknown/None; never invent zero.

## Required correction order

```text
1. bring branch current with canonical main docs/state
2. fix E001 to prove real EXECUTE, exact-once dispatch, VERIFIED/accepted, COMMITTED, zero LLM
3. implement verifier-failure E2E
4. absorb/remove scratch fixture
5. correct upstream_interventions provenance/scope
6. add SEAM-OPERATIONAL-RESOLUTION and run strict seam audit
7. close or explicitly leave OPEN the Experience feedback loop
8. finish truthful metrics mapping
9. Browser + owner regressions
10. full exact-head qualification + CI
11. final upstream drift classification
12. PR / promotion
```

## Promotion rule

Do not merge H-080 while any of B1-B7 remains unresolved.

The implementation direction is accepted; the remaining work is qualification, proof, registry truth and Experience-loop closure — not another architectural restart.

## Existing owners to reuse for the remaining closure

Do not create parallel implementations for the remaining Experience/metrics work.

Experience capture/compilation owners already present:
- `workstation/experience_compiler/corpus.py::ExperienceCorpus.capture`
- `ExperienceCorpus.accept_run`
- `ExperienceCorpus.traces`
- `workstation/experience_compiler/compiler.py::ExperienceCompiler.mine`
- `ExperienceCompiler.compile`
- `ExperienceCompiler.validate_verifier`
- `ExperienceCompiler.promote`
- `workstation/experience_compiler/causal.py::controlled_replay`
- `SafeEnvironment`
- `ExperiencePromotionPolicy`
- `OperationalCapabilityRegistry`

Current compiler metrics already expose candidate/promotion/dedupe/replay/drift data and intentionally leave `capability_coverage`, `operational_novelty_rate`, and `llm_calls_per_verified_outcome` unknown when there is no denominator. `workstation/control_plane/metrics.py` already owns ORA/VOLC concepts, including truthful `llm_calls_per_outcome`. Extend/derive from these owners rather than creating a second metrics subsystem.

Raw-result lineage note:
`procedure_trace.py` stores the sanitized raw terminal payload in ArtifactStore and uses that artifact as the semantic state's `artifact_ref`; `sample_from_trace()` currently exposes the same artifact as `raw_result_ref`. Do not split this into a second persistence owner merely for naming purity. If changing it, first prove that raw payload and semantic-state lineage require distinct artifacts; otherwise preserve the existing ArtifactStore reference and improve naming/tests only as needed.
