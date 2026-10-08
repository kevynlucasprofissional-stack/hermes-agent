# D-039 — Laya adaptive autonomy, opportunity-preserving online learning and durable reuse (2026-10-08)

**Status:** ACCEPTED PRODUCT DIRECTION / IMPLEMENTATION AND QUALIFICATION OPEN / NO MAIN MERGE.
**Branch analyzed:** `workstation/laya-direct-system1` at `938d9b2beeafde554b961112bca8ca5af2212df5`.
**Owners:** OnlineCompilabilityMonitor (suggestions), ExperienceCorpus/ExperienceCompiler (evidence/mining), RunAdoptionOwner + Policy + TaskRun (delegated authority), ValidationEnvironmentProvider + Verifier + replay (truth), RunLocalAdopter (effects at safe checkpoint).
**Basis:** 2026-10-08 user-requested choice favoring autonomous learning and valid same-TaskRun reuse, accepting greater computational/operational risk; follow-up technical review of real code. Extends D-037/D-038 without weakening provenance, user-granted effect scope or confirmed readback.

## 1. North star — protect opportunities, not rigid counters

The main product failure to avoid is: a repetitive TaskRun produces a potentially reusable verified procedure but Hermes stays in SHADOW, drops critical events when the queue fills, forgets a window after idle timeout, or stops attempting compilation after exactly three immature attempts. Those are **opportunity losses**, not justified safety decisions. Preserve **learn -> validate -> propose -> adopt during the same TaskRun** as the preferred eligible path; a user who already delegated effects should not repeatedly authorize a narrower, identical operation.

Do **not** interpret this as permission for learning-plane self-issued LOCAL_MUTATION, guessed validation receipts, expired-lease use, cross-run privilege leakage, irreversible retries, or global promotion without policy. D-038 proof/authority boundaries remain mandatory. Greater acceptable risk is additional verified work and bounded resource expenditure, not forged permission/truth.

## 2. Delegated automatic authority, not self-granted authority

- `OnlineCompilabilityMonitor` may proactively request/assemble a *narrower* `RunLocalAdoptionRequest` for the next canonical pending equivalent item. Policy/RunAdoptionOwner determines permission **without user re-prompt** if an existing active TaskRun already authorizes the exact primitive, target, effect class, budget, lease and bindings.
- Runtime should derive a **short-lived item/operation-scoped execution grant** from the active user's admitted `AuthorityScope` and `effect_budget`. It is not a new root authority. Re-evaluate at each item boundary, keep owner/tenant/task/run identity, revocation/supersession and uncertainty reconciliation. Prefer explicit `authority_covers`/`effect_contained` checks already used by `plan_item_adoption`.
- If authority is missing, record `AWAIT_AUTHORITY`/held candidate; do not erase learning, falsely pretend authorization, or silently expand scope. The main run can continue on independently authorized work. New consent is required only when the action exceeds the *originally* delegated scope.
- Reuse can be immediate after verifier/readback and owner receipt; never demand arbitrary multiple-run proof for **temporary same-run** adoption. **Global promotion** remains separate and needs existing cross-run policy.

## 3. Replace binary permanent SHADOW with evidence-based progression

Distinguish learning activity from external effects:
1. **OBSERVE_ACTIVE**: inexpensive semantic capture, durable evidence, Laya readiness and scoped candidate mining should be available immediately where supported (no blanket SHADOW preventing mining). Independent validation is also permitted; failed/missing verifier keeps a candidate held, not forgotten.
2. **DIRECT_VERIFIED / eligible fast lane**: for owner-certified primitives with real sandbox verifier/replay/readback and an active authorized TaskRun, a *genuine, version-bound qualification attestation* allows automatic same-run adoption. Prefer this path in eligible day-to-day use, including file operations already delegated. No new consent prompt inside scope.
3. **SHADOW_FOR_EFFECTS / unsupported scope**: still record events, mine and queue candidate for later admission; no external mutation while missing authorization, reliable validation owner, replay, task identity, or verifiable effects. A system-wide default that entirely suppresses mining is not the desired steady state.
4. **QUARANTINE/RECONCILE**: source conflict, verifier failure, uncertain previous mutation, superseded authority or rollback triggers hold/quarantine of this candidate/item only, not global disable or loss of other healthy opportunities.

**Qualification:** replace the current nonempty `direct_qualification_ref` test with a persisted, resolvable attestation bound to exact code/model/provider/schema/decision-domain revision, operation family/effect class, environment, verifier contract and tests; validate it at use, including expiry/revocation. A configured arbitrary string grants nothing. An explicit, auditable **developer dogfood** path may test expanded performance risks in a contained environment while preserving root authority and verifier boundaries; never mislabel it production qualified.

**Progressive metrics:** collect false positives, verified candidate yield, acceptance rates, memory/CPU/delay, cost per verified outcome, System-2 savings with observed baseline; allow faster qualified scope expansion with positive results. Lack of calibrated classifier labels does not forbid evidence capture or candidate mining; it forbids calling Laya's confidence a permission or verified success.

## 4. Durable, adaptive event/learning scheduler

The present monitor has defaults of 64 queued events, 64 per-run events, 64 windows, 900s idle TTL, 3 compilation attempts per segment, 3 validations per candidate, 4 offers per window and 100 adopted items/checkpoint. These may be retained as **memory/CPU envelopes**, not irreversible learning caps.

**Priority + coalescing:** score events deterministically (durable verifier outcome, newly verified sample, new parameter variant, new negative/control result, critical cancellation, significant repeated family > redundant tool_finished/unchanged state). Deduplicate noisy observations before expensive Laya inference. Queue saturation MUST preserve a minimal durable pointer for high-value verified/negative/closure evidence; discard redundant low-priority in-memory work first. Preserve source refs and rehydrate using `ExperienceCorpus`/`ArtifactStore`, not a second truth database. Give every active TaskRun fair admission; avoid one run flooding the worker.

**Adaptive attempts:** replace `max_compile_attempts_per_segment=3` and `max_validation_attempts=3` as terminal exclusion with bounded-per-evidence-revision attempts. Track semantic evidence fingerprint, last failure class, last attempt, next eligibility/backoff, budget consumed and current result. New verified success, new parameter variant, resolved failure, changed verifier, added counterexample or a material corpus revision reopens an attempt with exponential cooldown/jitter and bounded per-time CPU. Identical evidence + deterministic failure must not spin forever. Transient provider/environment failure should be retried when the dependency recovers, not invalidate candidate forever.

**Durable lifecycle:** persist compact `run_learning_checkpoint.v1` using existing artifact/task stores: task/run, event cursor, source sample refs, candidate/offer refs, evidence digest, attempt schedules, denial reasons, verifier state, last known lease/status, monotonic schema version. On idle eviction/shutdown/restart, rehydrate from canonical artifacts. Never serialize/store a stale live `RunAdoptionOwner`, permissions, callbacks, or actual granted execution lease; reconstruct and revalidate these at next checkpoint. Runtime plan remains canonical. TTL and LRU only evict the hot cache, not the learnable corpus or rehydratable candidate.

**Resource protection:** keep hard caps on concurrent workers/inference, memory and disk spool, per-turn foreground latency, cancellation/safe shutdown and in-flight mutations. These caps may **defer** optional learning but do not silently delete indispensable provenance or cancel the user's TaskRun. On actual disk-pressure budget breach, surface a durable `LEARNING_BACKPRESSURE` diagnosis with what was dropped and an explicit best-effort policy (no fiction of lossless persistence). Nonblocking capture; do not run expensive replay on the user's foreground path.

**Checkpoint budget:** `RunLocalAdopter(item_limit=100)` is a per-checkpoint fairness/yield envelope, **not** a lifetime TaskRun stop. If pending items remain, preserve offer and schedule the next checkpoint; no repeated unsafe dispatch, no duplicate mutation; break for cancellation, revoked authority, negative readback or uncertainty. Enable adaptive batch size on stable verifier-observed operations, without taking the runtime hostage.

## 5. Production-ready verifier and real task opportunity

Current validation calls `get_validation_environment_provider()` and denies `validation_environment_unavailable` if no production owner registered; production `integrations/hermes/run_local_adoption.py` supports a small verified `write_file`/readback surface. Prior local positive TaskRun simulation used a test-owned SafeEnvironment runner and model doubles, not proof of general production operation.

Implement a **small real production validation owner**, starting with an isolated/readback-capable filesystem `write_file` (or a *safer owner-certified family* after code discovery) with genuine isolated canary, positive/negative verifier receipt, replay evidence, approved target/effect scope and real task lifecycle. No fictitious receipts; no uncontrolled replay on the live path. Enable subsequent operation families incrementally with explicit verifier/readback contracts.

Dogfood using actual Laya 0.3.23, actual Hermes TaskRun/observer, user-delegated safe target, canonical capture and provider registered through the product composition root. Show: first 2–3 verified examples, scoped candidate mined, replay and verifier accepted, next 4+ equivalent pending items automatically adopted, persisted receipts/readback, counterfactual System-2 counts; negative tests for scope/revocation/uncertain effects. Do not claim real-model readiness merely from typed response shape.

## 6. Exact code touchpoints

- `workstation/experience_compiler/compilability_monitor.py`: `LearningPolicy`, `resolve_policy`, `TaskRunObservationWindow`, `_get_window`, `schedule_event`, `process_event`, `_query_system1_compilability`, `mine_candidate_in_run`, `validate_candidate_run_local`, `ready_offers`, `stop`/`drain`. Separate *learning activity* from *effect admission*; adaptive evidence-version budgets, fair durable scheduler, non-discarded opportunities, rehydrate.
- `workstation/experience_compiler/corpus.py`, `progressive.py`: canonical per-run source and durable event refs; no duplicate corpus.
- `workstation/experience_compiler/compilability_validation.py`, `lifecycle.py`: real validation owner and held-for-retry classification, validation-only vs global promotion.
- `workstation/run_adoption.py` and `workstation/integrations/hermes/run_local_adoption.py`: derived short-lived policy grants at existing checkpoint, recheck between items, idle continuation after fairness limit.
- `workstation/integrations/hermes/operational_resolution.py`, `tool_observer.py`, `operational_kernel.py`: real checkpoint + verified semantic evidence, never raw gesture polling; validate owner construction.
- `workstation/system1/contracts.py`, `schemas.py`, `laya_provider.py`: preserve typed decisions, only expand metadata needed to classify evidence/abstain.
- `workstation/tests/test_online_compilability_safety.py` and `test_online_compilability_monitor.py`: tests + qualification driver `workstation/scripts/qualify_laya_system1.py`.

## 7. Implementation order, evidence and release

**A0 — mandatory baseline:** record HEAD, CI, H-079 one-pin upstream pre-change gate, H-081 exact-head and H-082 state; do not violate repository `AGENTS.md`. If baseline blocks runtime changes, preserve this accepted design and report precise blocker; no backdoor runtime edits. The old exact-head workflow `37804714508` FAILED in full Workstation on runner timeouts after focused gates passed; no CI green claimed.
**A1 — policy/attestation:** RED for nonempty fake qualification, missing live provider, wrong revision/scope; GREEN evidence-backed family-scoped DIRECT and active capture+mining even where effects remain SHADOW.
**A2 — adaptive learning state:** RED for three premature failures + new evidence, TTL expiry + restart, transient verifier outage + recovery; GREEN version-aware retry/backoff and durable checkpoint.
**A3 — priority/fairness/resource scheduling:** RED for saturated queue with valuable verified event, 2 concurrent runs, bounded wall/CPU usage, shutdown; GREEN deterministic priority and durable catch-up without foreground stall.
**A4 — authority:** RED for denied original scope, policy revocation, stale lease, changed effect budget, uncertain readback; GREEN automatic narrower delegation without re-prompt inside TaskRun, no monitor-minted authority.
**A5 — owner verification and dogfood:** register real safe isolated verification/replay owner, observe actual Laya and actual workload, feed verifier-based calibration; same-run next-item reuse without user confirmation inside grant.
**A6 — checkpoint fairness:** RED for >100 valid work items, restart with outstanding offer, terminal failure/uncertainty; GREEN resume next checkpoint, never replay completed effect, honor cancellations.
**A7 — quantify/qualify:** true receipts, measured savings, false-positive outcomes, all focused + full suite and exact-head CI; strict seam audit, H-079/H-081 gates. Separate blocked from failed and don't weaken timeout/assertions to force green. Record real qualified family/mode, no global registry promotion from one TaskRun.

### Acceptance matrix

1. 3 empty/failed early compilations followed by new verified examples -> eligible retrial and verified new candidate, no infinite loop on unchanged evidence.
2. Long-running multi-hour TaskRun with idle TTL/cache eviction/restart -> rehydrate durable evidence/held candidate and continue learning, without resurrecting old authority.
3. Queue saturation across two tasks -> canonical high-value verified/negative evidence still recoverable; main run latency bounded; loss/backpressure metrics honest.
4. Valid user-authorized file write repetition -> automatic derived grant, no additional user prompt, safe verifier/readback and same-run reuse, real provider.
5. Fake direct_qualification_ref/foreign family/expired attestation -> no mutating DIRECT; learning still allowed if non-effectful.
6. Missing production ValidationEnvironmentProvider -> candidate HELD and retried when a real provider appears, no invented replay or irreversible dispatch.
7. Run cancellation, stale lease, over-budget effects, uncertain write -> no mutation, no retry of uncertain side effects, other independent learning continues.
8. >100 pending equivalent items -> checkpoint yields then continues on later checkpoint until actual TaskRun goal complete; never falsely marks TaskRun done.
9. Laya abstain/invalid/timeout -> deterministic collection and optionally existing verified-candidate progression continue without speculative effect; System-2 remains available.
10. CI red or absent held-out calibration -> production family stays unqualified; dogfood scope clearly labeled, no fake production qualification.

**Trade-off consciously accepted:** more Laya inference, additional compilation attempts, larger durable observation overhead and qualified same-run automation in exchange for fewer missed operationalization opportunities and earlier cost reduction. **Trade-off NOT accepted:** out-of-scope authority, unverifiable real-world effects, duplicate uncertain mutation, fabricated replay or bypass of upstream-first/release gates.

### Delivery/measurement

Track `opportunities_detected`, `queued_durable`, `coalesced`, `dropped_redundant`, `backpressure_durable`, `retry_reopened_by_new_evidence`, `retry_after_dependency_recovery`, `held_candidates`, `validated_candidates`, `offers_rehydrated`, `same_run_verified_items`, `missed_opportunity_rate`, `foreground_latency_p95`, `model_cpu_seconds`, `measured_system2_calls_saved`, `cost_per_verified_outcome`. Never report avoided calls without instrumented reference. 
