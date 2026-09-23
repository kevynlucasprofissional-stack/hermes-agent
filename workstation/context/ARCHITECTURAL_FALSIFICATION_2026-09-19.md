# Architectural Falsification / External Validity — H-077

## 2026-09-23 external-reference intake — comparative audit as a falsifier

The new Source Matrix / code-to-code audit program is an extension of H-077's method, not a replacement architecture.

External projects are valuable here for two reasons:
1. they may contain mechanisms Hermes should learn from;
2. they provide **countermodels** that can falsify Hermes assumptions (for example different skill lifecycle, evaluator governance, browser recovery, workflow representation or durability boundaries).

The future comparison must therefore record not only `what can we copy?` but `what does this implementation show our current ontology/owner split may be missing or overfitting?`.

Any cross-project superiority claim requires evidence outside Hermes' own internal certificate/metric loop. README statements and benchmark leaderboards may guide discovery, but they are not sufficient proof of a Hermes architecture decision.

Canonical comparative protocol: [REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md](REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md).

Date established: 2026-09-19  
Status: **CORE IMPLEMENTED / QUALIFICATION PARTIAL — H-077.1 CORRECTIVE CLOSURE ACTIVE**  
Current audited baseline: `main@92a3acb51e87af85a9f380ee04d2cf47d7900ca5` (PR #36 merged; post-merge qualification reopened)

## Executive decision

The Hermes Work architecture is **not being replaced**.

The adversarial research falsified a universal claim, not the operational core:

```text
HermesCertificate(x) = VERIFIED
does NOT universally imply
RealWorldOutcome(x) = CORRECT
and HumanIntent(x) = SATISFIED
```

The safe interpretation is narrower:

> A Hermes certificate is a scoped claim about predicates covered by a current
> contract, admissible evidence, authority, temporal basis and known applicability
> conditions. It is not proof that the model contains every fact that matters.

The project therefore changes its **criterion of progress**, not its core route.

```text
preserve the proven owners
-> remove remaining false-confidence seams
-> measure against independent outcomes
-> actively falsify the model
-> learn the validity envelope
-> generalize only after the envelope survives
```

The product objective is not "eliminate reasoning". It is:

> **eliminate unnecessary reasoning without eliminating the ability to detect when
> reasoning must return.**

## Post-implementation falsification — H-077.1

PR #36 landed substantial truthful-core work, but the stronger closure claim did not
survive post-merge review. The corrective companion is
[H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

Residual classes: ACK -> terminal completion bypass; contract-derived evidence provenance;
unenforced task/run lineage; fail-open/diagnostic-only applicability envelope; external
metrics that can hide missing oracle coverage; adversarial tests that do not yet form a
fully generated hidden-oracle harness; incomplete automatic model-inadequacy integration;
and optimistic success/replay accounting.

This falsifies the **qualification claim**, not the H-077 architectural direction.

## What survives

The red-team work did not justify deleting the central owners:

- `OperationIntent`: keep as the current operational specification, not guaranteed
  equivalence with the full human need.
- `SemanticState`: keep as an explicit projection of the world, not the world itself.
- `CapabilityFormalContract`: keep as the typed operational boundary.
- `CapabilityRouter`: keep as mutation-admission/typechecking owner.
- `CertifiedDispatcher`: keep ACK separate from terminal truth.
- `OperationalCapability`: keep as a reusable unit inside a demonstrated envelope.
- VOT: keep as a verified operational transition, not a universal ontology of all work.
- Await/Trigger: keep; "event wakes, authoritative state confirms" remains correct.
- Experience Compiler: keep, but learn both **how to reuse** and **when not to generalize**.
- RunClosureProof: keep; run-local operationalization remains distinct from global
  promotion.
- progressive compilation: keep as an optimization conditioned on external quality.

The architecture is strongest for operationally closable digital work:

```text
observe -> decide -> mutate -> independently observe -> reconcile -> close
```

It is less naturally complete for open-ended research, negotiation, unstable human
preferences, shared control, path-dependent/temporal obligations, and tasks without a
defensible oracle.

## Confirmed post-H-076 residual seams on current main

H-076 materially improved verification, but a post-qualification audit of
`main@2babc8b4cf89bab217cd76b5992d192776184337` reproduces five remaining false-confidence seams.

### F1 — routing-time ORA inflation

`workstation/control_plane/metrics.py` still records an
`ExecutableDecision` or `ComposedDecision` as
`record_transition(verified=True, reasoned=False)` inside `on_routing_decision()`,
before execution and verification. `record_transition()` and `on_transition()` also
retain optimistic `verified=True` defaults.

**Required property:** routing may record "deterministic route selected", but only an
outcome owner may increment a verified-transition numerator.

### F2 — unknown condition fails open

`workstation/operational_kernel.py::verify_condition()` still returns `True` for an
unrecognized condition type.

**Required property:** unsupported condition types fail closed, never approve execution.

### F3 — evidence may be synthesized from the expected value

When `verification_evidence` is absent,
`OperationalKernel.execute_capability()` can construct `VerificationEvidence` for an
owner-declared verifier using the expected value itself and contract-declared strength,
trust, coverage, read-after-write and a fallback resource version.

**Required property:** no layer may manufacture terminal evidence from the proposition
being proved. Missing evidence must either invoke the declared observer and obtain real
observation, or yield `INCONCLUSIVE`.

### F4 — resource binding is represented but not enforced

`VerificationContract.resource_binding` exists, but
`evaluate_verification()` does not establish that admitted evidence is bound to the
concrete resource that the claim targets.

**Required property:** required resource identity/binding participates in evidence
admissibility and mismatch is not VERIFIED.

### F5 — causal transition identity is too weak

For a transition claim, `evaluate_verification()` currently treats non-empty evidence
`operation_id` values as enough to mark the transition proven.

**Required property:** transition verification accepts an explicit
`expected_operation_id` (and lineage/fencing where required) and proves identity, not
mere presence.

### Compatibility seam — boolean verifier

Legacy boolean verifier callbacks are already prevented from becoming canonical
terminal truth in Dispatcher. H-077 completes migration and removes or explicitly
deprecates the compatibility path once callers are migrated.

## Architectural claim after falsification

Use this semantics:

```text
VERIFIED(C, A, E, W)
```

means approximately:

> under contract C, known applicability assumptions A, admissible evidence E and
> temporal/version window W, the covered predicates were demonstrated.

It does not mean that the world is completely modeled, the user is necessarily
satisfied, or no relevant unknown variable exists.

Terminal epistemic states remain distinct:
- insufficient evidence -> `INCONCLUSIVE`
- conflicting sources -> `CONFLICT`
- expired/version-invalid evidence -> `STALE`
- future observable condition -> `WAIT`
- missing authority or unresolved preference -> `ASK_HUMAN`
- known model/strategy no longer closes -> `WAKE_LLM`
- valid scoped proof -> `VERIFIED`

## Validity domains

### H1 — strong domain: dominate

Files, APIs, persisted SaaS resources, cards, configuration, browser actions with a
source of record, reconciliable mutations, typed PRE/POST and stable authority.

### H2 — adjacent domain: experiment

Long workflows, concurrency/shared control, temporal obligations, dynamic queues,
closed-loop sensing and long-running maintenance. Use AFB-v0 to determine whether
existing `OperationalCapability` semantics can represent deterministic
policies/controllers before introducing a new top-level type.

### H3 — counter-domain: do not fake closure

Open research, negotiation, creative work, unstable preference, social judgment and
goals without a defensible oracle. Retain adaptive reasoning/human interaction.

## Minimal assumption ledger

A strong certificate depends on at least:
1. intent completeness enough for the claim;
2. intent currency;
3. state discriminativeness;
4. observability;
5. source authority;
6. verifier independence where required;
7. verifier sensitivity;
8. temporal validity;
9. causal identity when required;
10. concurrency safety;
11. composition closure;
12. applicability stability.

No implementation can prove that there are zero unknown assumptions. The runtime goal
is to detect **evidence that the current abstraction stopped explaining outcomes**.

## H-077 implementation sequence

### P0 — Truthful Core Cleanup

Implement before any new runtime primitive:
1. remove routing-time `verified=True` transition accounting;
2. make transition verification explicit with no optimistic default;
3. make unknown condition types fail closed;
4. remove synthetic evidence built from expected values;
5. invoke real owner-declared observers or return `INCONCLUSIVE`;
6. enforce verification resource binding;
7. bind transition claims to expected operation identity/lineage;
8. complete migration away from boolean verifier compatibility;
9. add focused RED/GREEN tests for every seam.

### P1 — AFB-v0: Architectural Falsification Benchmark

Build an external/adversarial harness, not another control plane.

Minimum test families:
- hidden compliance/state counterfactual pairs;
- stale/version race;
- concurrent human/agent lost update;
- source disagreement;
- non-idempotent send + lost ACK/restart;
- temporal `MAINTAIN` trajectory failure;
- composition where every child passes but global invariant fails;
- semantic drift with unchanged schema/fingerprint;
- intent ambiguity / goal shift;
- dynamic queue / closed-loop controller case;
- promotion-set holdout vs post-promotion reuse.

The benchmark oracle must be separated from the internal verifier being evaluated.

### P2 — External outcome metrics

ORA remains an efficiency metric, not product truth.

Required vector:
- False Certified Outcome Rate (FCOR);
- Certification Coverage;
- External Outcome Correctness;
- Internal-External Agreement;
- False Abstention Rate;
- Hidden-Assumption Robustness;
- Model-Inadequacy Detection Recall;
- False-Safe Rate;
- Unsafe Mutation Rate;
- Conflict Detection Recall;
- Recovery Correctness;
- Verifier Sensitivity;
- ReuseReliability(N);
- time-to-detection;
- LLM wake appropriateness;
- ASK_HUMAN precision / human interruption burden;
- ORA and VOLC/cost only after quality constraints hold.

Never collapse these into one 0-100 epistemic score.

### P3 — Model-inadequacy tripwires

If the same represented state/fingerprint + same action repeatedly yields both PASS and
FAIL under an independent outcome oracle, do not invent a PRE automatically.

```text
same abstraction + materially different outcomes
-> abstraction cannot currently discriminate
-> suspend generalization/promotion
-> seek additional observation
-> quarantine when consequential
-> WAKE_LLM / ASK_HUMAN where appropriate
```

### P4 — Derived validity envelope

A validity envelope is required **as a concept**. Do not create a
`ValidityEnvelopeRegistry` yet. Derive it from existing owners: OperationIntent,
CapabilityFormalContract, VerificationContract, authority/effect budget,
resource/operation binding, temporal/version basis, observed context/fingerprint,
provenance/evidence history, counterexamples and validation receipts.

### P5 — New primitive decision gate

Only after AFB-v0 and external metrics should the project decide whether it needs
stronger trajectory predicates, belief state, closed-loop policy/controller semantics,
persistent intent uncertainty, applicability models, or a first-class assumption object.

A proposed new horizontal primitive must pass:
1. **Counterexample** — reproducible case current owners cannot represent correctly.
2. **Frequency/value** — common or consequential enough for permanent software.
3. **No natural owner** — cannot fit cleanly in current owners.
4. **Measured improvement** — improves an external metric/falsification outcome.

## Explicitly deferred / prohibited premature work

Do not create now:
- `ApplicabilityCompiler`;
- `AssumptionRegistry` / parallel AssumptionContract subsystem;
- `PolicyCompiler` or second policy ecosystem;
- `StrategyRegistry`;
- `TemporalIntent` merely because temporal counterexamples exist;
- `WorldModelService`;
- `VerifierDB` / `OracleManager`;
- universal `UnknownUnknownDetector`;
- second evidence store, predicate IR or Control Plane;
- generic LLM/fuzzy judge as mutation commit authority.

## Qualification rules

P0 qualification requires direct negative tests for every reproduced seam, focused
suite green, full Workstation regression green, no evidence synthesized from the
expected proposition, routing unable to increment a VERIFIED numerator, unsupported
condition types failing closed, and wrong resource/operation identity rejected.

AFB-v0 qualification requires hidden oracle separation, reproducible counterfactual
pairs/fault schedules, FCOR reported with coverage, multi-run reuse reliability, and at
least one falsifier per high-impact assumption.

## North-star statement

Hermes should become a substrate for **certifiable operational execution inside known
validity envelopes**, with the ability to notice evidence that the envelope has broken.

```text
reason when necessary
-> resolve enough intent
-> prove only what is actually provable
-> compile only inside a demonstrated validity envelope
-> reuse while assumptions remain supported
-> watch for evidence that the envelope broke
-> abstain / wait / ask / reconcile / reason when it did
```

This is a refinement of the current architecture, not a pivot away from it.
