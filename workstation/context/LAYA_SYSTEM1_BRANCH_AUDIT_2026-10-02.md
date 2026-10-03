# H-081 Laya Direct System-1 Branch Audit — 2026-10-02

**Audited branch:** `workstation/laya-direct-system1`  
**Audited implementation head:** `736be5b9cebc8ffcb1c02a084a4bdba3755a5074`  
**Baseline:** `main@e4d079f005ba6b324316e70bb4f9915460f555aa`  
**Observed relation at audit:** 9 commits ahead, 0 behind.  
**Classification:** **IMPLEMENTATION SCAFFOLD LOCALLY TESTED / REMEDIATION REQUIRED / NOT QUALIFIED FOR MERGE**.

This audit supersedes any branch-local wording that described H-081 or HW-033 as
"qualified" merely because focused contract tests passed. The architecture direction
is retained; the production-readiness claim is not.

## What remains accepted

Preserve these parts unless new evidence falsifies them:

- the generic `agent/system1_decision.py` seam: Hermes core depends on a generic
  System-1 provider contract, not on Laya classes;
- Laya is non-authoritative: it may classify/rank bounded candidates but cannot mint
  authority, certificates, verifier truth, COMMITTED state or capability promotion;
- candidate reordering remains downstream of deterministic candidate construction and
  upstream of the existing Router/Policy/Verifier proof chain;
- the pinned Laya source is vendored as a secondary upstream via git subtree and recorded
  in `workstation/components.lock.json`;
- typed authority-supersession/checkpoint concepts are useful and stale runs must remain
  strictly fenced from new mutations;
- outcome-oriented telemetry, Cost per Verified Outcome and dual-rate learning remain the
  intended direction.

## Blocking findings

### P0-1 — Real Laya response contract is parsed incorrectly

`workstation/system1/laya_provider.py` currently reads a prediction approximately as
`raw_output[q_id]["answer"]`. Laya 0.3.23 returns typed answers under
`result["answers"][qid]`, with the decision stored by question type
(`choice`, `score`, `noul`) plus confidence/probabilities.

Consequence: FakeSystem1 tests can pass while the real Laya provider returns
`None`/zero confidence and abstains or falls back, so active real-provider influence is
not proven.

Required closure:

- parse the actual vendored Laya 0.3.23 contract;
- use the calibrated answer confidence appropriate to the Laya API;
- preserve typed probabilities and abstention semantics;
- add a contract test against a realistic Laya output payload;
- add an opt-in/live real-checkpoint smoke proving a bounded decision reaches Router
  influence without bypassing Router/Policy/Verifier.

### P0-2 — Vendoring is not activation; packaging/provenance is not closed

The root extra installs Laya dependencies but does not prove that `import laya` resolves
from `workstation/third_party/laya` in a supported Hermes environment. The adapter also
constructs `LayaDecisionProvider(strict_provenance=False)`, which can tolerate an
unapproved import source.

Required closure:

- package/install the vendored local Laya source through supported environment semantics;
- no runtime `sys.path` hack;
- when Workstation expects the vendored provider, provenance must fail closed;
- never silently use unrelated global/PyPI Laya;
- expose source path, subtree/source revision, Laya version, checkpoint revision/digest
  and device;
- prove the actual imported file lives inside the approved subtree.

### P0-3 — `stale_task_run` is checkpointed but not resumed end to end

`workstation/authority_supersession.py` introduces useful typed state and
`resume_superseded_work()`, but production paths still return/raise
`stale_task_run`. No proven normal-runtime path consumes the checkpoint and rebinds
pending work to the current canonical TaskRun.

Required closure:

```text
stale run loses mutation authority
-> classify termination
-> persist completed/pending/uncertain state
-> current canonical run adopts resumable work
-> reconcile uncertain effects before any redispatch
-> resume only unconfirmed work
-> explicit cancel/revoke/policy revoke never auto-resumes
```

The acceptance test must exercise the real TaskCompiler/runtime path, not call only the
helper in isolation.

### P0-4 — `needs_system2=False` does not generally prevent `WAKE_LLM`

The Router records System-1 reasoning-gap decisions, but TaskCompiler converts a remaining
`ReasoningDecision` to `WAKE_LLM` unconditionally. The current special case for
`reprobe_state` is useful but does not prove the general contract.

Required closure:

- define typed non-System-2 outcomes for known deterministic recovery/continuation paths;
- when System-1 confidently selects an admissible known path, execute that path without
  waking the LLM;
- otherwise abstain/fallback safely;
- prove at least one production-like case with main-provider/System-2 calls = 0.

### P0-5 — LearningReview cannot manufacture `VERIFIED_SUCCESS`

`System1DatasetBuilder.ingest_learning_review()` currently risks treating background
review success as operational verification. Background-review completion/action generation
is not verifier evidence. The action shape also must be normalized explicitly instead of
assuming review actions are dicts.

Required closure:

- System-1 positive labels require canonical compatible verifier evidence;
- background review may propose examples/counterexamples but cannot self-certify them;
- bind samples to real task/run/operation lineage;
- preserve UNCERTAIN/FAILED/INTERRUPTED/AUTHORITY_SUPERSEDED counterevidence;
- never promote or train from a success label derived only from review completion.

### P1-1 — Dual-rate learning loop is mostly scaffolding

The branch adds a dataset builder and a review hook, but does not close progressive
TransitionSample capture through the existing Experience owners.

Required closure:

- progressively capture OBSERVED typed transitions during work;
- keep promotion gated by accepted verified evidence;
- persist the dataset/corpus rather than leaving the only builder in adapter memory;
- connect verified Experience/Journal/LearningReview inputs through one attributable
  pipeline without creating a second operational truth store.

### P1-2 — Decision receipts/provenance are incomplete for reproducibility

Populate and verify the fields already designed for lineage:

- state and candidate-set hashes/refs;
- question schema version;
- provider/model/checkpoint revision and digest;
- actual Laya source provenance;
- calibrated confidence/abstention;
- task/run/operation lineage;
- fallback mode;
- downstream RoutingCertificate and verification refs when available.

Do not claim a subtree source SHA merely by copying lock metadata if the checked-out
vendored bytes have drifted.

### P1-3 — Telemetry fields exist beyond proven event wiring

System-1/authority/cost counters must be projections of observed owner events, not merely
new mutable fields or methods.

Required closure:

- emit observations from canonical owners;
- derive System-1 calls/hits/abstentions/fallbacks, System-2 wakes,
  authority-superseded events and verified-outcome economics from those observations;
- leave unknown denominators/costs as unknown, never fabricated zero.

### Process blocker — H-079 and exact-head qualification were skipped

The experiment was allowed on an isolated branch, but promotion still requires the normal
upstream-first and release-evidence discipline. At this audit the head had no GitHub
workflow/status evidence and no open PR.

Before promotion:

- execute current H-079 upstream preflight/classification;
- reconcile only relevant upstream changes under existing seam policy;
- run strict seam audit;
- run focused System-1/supersession/learning tests;
- run affected Workstation regressions;
- run a real Laya smoke/dogfood;
- reproduce a long-run supersession/resume scenario;
- obtain exact-head GitHub CI evidence;
- classify final upstream drift.

## Required implementation order

```text
P0-A  supported vendored-Laya packaging + fail-closed provenance
P0-B  real Laya 0.3.23 response parsing + realistic/live contract proof
P0-C  production TaskRun AUTHORITY_SUPERSEDED -> adopt/resume/reconcile path
P0-D  needs_system2=False -> typed deterministic resolution without WAKE_LLM
P0-E  verifier-grounded System-1 labels + correct LearningReview normalization
P1-A  progressive TransitionSample capture + durable dataset pipeline
P1-B  complete DecisionReceipt/provenance/downstream linkage
P1-C  owner-event telemetry wiring and truthful outcome economics
QUAL  H-079 preflight -> seams -> regressions -> dogfood -> exact-head CI -> final drift
```

Do not broaden feature scope until these gates close.

## Merge gate

H-081 may be described as **QUALIFIED** only when all of the following are true:

1. supported Hermes install imports the approved vendored Laya and rejects unapproved
   provider provenance;
2. a real Laya decision changes bounded candidate ordering or resolves an admitted known
   path through the production control plane;
3. no System-1 decision can bypass authority, policy, certificate or verification gates;
4. at least one known case avoids a System-2/main-provider call with equivalent verified
   completion;
5. a superseded TaskRun resumes through the normal runtime without duplicating uncertain
   mutations;
6. System-1 training/eval labels are grounded in canonical verifier evidence;
7. progressive observations and retrospective reviews feed a durable attributable dataset;
8. System-1/authority/cost telemetry is derived from observed owner events;
9. focused + affected regression suites pass;
10. dogfood and exact-head CI are green and final upstream drift is classified.

Until then the canonical status is:

> **ARCHITECTURE ACCEPTED / IMPLEMENTATION PARTIAL / REAL-LAYA + CONTINUATION + LEARNING CLOSURE OPEN / NOT QUALIFIED.**


## 2026-10-02 corrective closure below the original findings

**P0-A through P0-E and P1-A through P1-C: CLOSED LOCALLY WITH RUNTIME EVIDENCE.**
**Exact-head CI: PENDING; H-081 remains NOT QUALIFIED until that run is green.**

[H-081 closure evidence](../qualification/H081_CLOSURE_2026-10-02.md) records the supported install, real checkpoint decision (confidence 0.9703),
39 focused passing proofs, complete Workstation regression, canonical supersession and
uncertain readback, verifier-grounded learning, durable reconstruction, receipts and
actual owner events. The audit above is preserved as the record of the original defects.
H-079 was refreshed/classified against `46904a3b467f62616f5b3ee247adce30b1b277a0`
(7,336 upstream-only commits; material file overlap); the original adopted pin remains
immutable. This evidence does not claim latest-upstream alignment or authorize a main merge.
