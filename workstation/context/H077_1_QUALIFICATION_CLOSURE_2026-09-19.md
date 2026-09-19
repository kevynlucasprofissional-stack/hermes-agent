# H-077.1 — Truthful Core Qualification Closure

Date established: 2026-09-19  
Status: **ACTIVE CORRECTIVE QUALIFICATION / H-077 CORE RETAINED**  
Audit baseline: `main@92a3acb51e87af85a9f380ee04d2cf47d7900ca5` (PR #36 merged)  
Parent decision: D-025 — scoped VERIFIED + external falsification before new horizontal primitives

## Why this exists

PR #36 materially improved Hermes Work, but post-merge falsification showed that the
claim "H-077 implemented and fully qualified" was too strong. The architecture is kept;
qualification is reopened.

```text
H-077 CORE IMPLEMENTED
H-077 QUALIFICATION PARTIAL
H-077.1 CORRECTIVE QUALIFICATION ACTIVE
```

Core invariant:

```text
execution ACK != VERIFIED != terminal completion != externally correct outcome
```

## Confirmed residuals

### Q0 — TaskCompiler can close ACK as completed
`OperationalKernel.execute_capability()` may return `success=True` when physical
execution completed while canonical verification is not VERIFIED. The direct
TaskCompiler path currently uses that success flag to validate/complete the WorkItem and
WorkPlan. Terminal validation must require canonical VERIFIED.

### Q1 — VerificationEvidence provenance can still be backfilled from the contract
Expected value no longer becomes evidence value, but evidence strength/trust/source/
failure-domain metadata can still be inferred from VerificationContract requirements.
Observation receipts must declare what actually happened; the contract only judges
admissibility. Missing provenance yields INCONCLUSIVE.

### Q2 — task/run lineage is accepted but not enforced
When expected lineage is known, task_id, run_id and operation_id must bind the evidence.
Do not treat operation-id uniqueness as a substitute for explicit lineage proof.

### Q3 — ValidityEnvelope is fail-open on missing context and is not reuse admission
The pure derived envelope is the right architecture. It must fail closed when required
tenant/target/resource/authority/temporal dimensions are absent, and it must gate
deterministic reuse through an existing owner. No ApplicabilityCompiler/registry.

### Q4 — external metrics can improve when external truth is absent
Observed FCOR must use externally adjudicated certified outcomes, paired with explicit
`external_oracle_coverage`. External correctness/reuse/recovery metrics must not treat
missing external truth as success, failure or an optimistic default.

### Q5 — AFB-v0 is adversarial regression, not yet the claimed external harness
AFB-v0.1 must derive each row from a real system result plus an independently executed
hidden/external oracle. Do not hand-label `external_success`.

Required falsifiers: hidden-state counterfactual pair, source disagreement,
non-idempotent mutation + lost ACK/restart, temporal MAINTAIN, composition emergence,
semantic drift same schema, intent/goal shift, dynamic closed-loop queue,
post-promotion holdout, plus retained concurrency/race/side-effect cases.

### Q6 — model-inadequacy tripwire is not fully automatic
Normal Experience Compiler flow must convert non-discriminable PASS/FAIL evidence into
model-inadequacy state, suspend generalization, quarantine/narrow/reason through current
owners and preserve the counterexample. Never invent a PRE to rationalize the failure.

### Q7 — ACK can still inflate success/replay/savings counters
Separate execution attempts/ACK from verified success and verified deterministic replay.
Trusted savings/amortization must not count non-VERIFIED executions as successful reuse.

## Corrective sequence

1. **P0 — terminal truth closure:** TaskCompiler/Kernel completion and truthful counters.
2. **P1 — observation receipt + lineage:** real provenance and task/run/op fencing.
3. **P2 — validity-envelope admission:** fail closed + existing reuse gate.
4. **P3 — external metrics:** adjudicated denominators + oracle coverage.
5. **P4 — AFB-v0.1:** generated internal result + independent oracle result.
6. **P5 — automatic model inadequacy:** normal compiler integration.
7. **P6 — qualification:** focused tests, H-076/H-075 regressions, full Workstation,
   affected Browser/Electron gates when touched, exact-head required CI.

## Minimum RED/GREEN gates

- physical success + INCONCLUSIVE/FAILED/STALE/CONFLICT cannot complete WorkItem/WorkPlan;
- canonical VERIFIED closes the same path exactly once;
- weak observer cannot inherit E3/trusted-owner provenance from contract requirements;
- wrong/missing task/run/op lineage fails when those bounds are expected;
- missing required envelope dimensions fail closed and prevent deterministic reuse;
- one failed external adjudication among 100 certifications with 1% oracle coverage cannot
  be reported as 1% observed FCOR;
- benchmark rows are generated from system output + hidden oracle, never hand-labelled;
- non-discriminable outcomes in normal compiler flow automatically suspend generalization;
- non-VERIFIED execution does not increment verified-success/replay/savings accounting.

## Still prohibited

No ApplicabilityCompiler, AssumptionRegistry, PolicyCompiler, TemporalIntent solely for
the benchmark, WorldModelService, VerifierDB, OracleManager, UnknownUnknownDetector,
second Control Plane/evidence store/predicate IR, LLM commit judge or epistemic 0–100
score.

## Qualification rule

Only restore `IMPLEMENTED & QUALIFIED` after all reproduced residuals are closed with
behavior tests and exact-head CI.

> Preserve owners -> harden truth boundaries -> independently adjudicate -> measure only
> what was observed -> falsify -> learn limits -> generalize inside a proven envelope.
