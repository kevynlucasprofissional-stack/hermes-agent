# H-079 — Upstream-First Change Gate / Qualified Baseline Discipline

Date established: 2026-09-20  
Status: **PRIMARY OPERATING POLICY — MANDATORY FOR DOWNSTREAM CODE CHANGES**  
Parent programs: H-078 / H-078A / H-078B / H-078C

## Decision in one sentence

> **No downstream implementation, bug fix, refactor, feature, seam adjustment or behavioral
> change starts from a stale Hermes baseline. First refresh and qualify the upstream
> baseline, reconcile the Workstation seam surface, and only then perform the target
> downstream change.**

This is the highest-priority engineering gate for Hermes Work whenever the requested work
can change runtime code or an upstream-owned integration point.

## Why this exists

The H-078C migration proved two things at once:

1. allowing the fork to drift for a long time creates a very expensive structural merge;
2. merely making downstream code dependency-clean does not guarantee that it is aligned
   with current upstream owners.

After H-078C, the pinned upstream commit became a true ancestor of downstream main, but the
post-merge audit still found qualification debt: Workstation CI red on the exact main head,
Browser convergence partial, duplicate batch admission, a silent adapter fail-open path,
stale documentation and incomplete final qualification.

The lesson is operational, not merely historical:

> **upstream synchronization is not a periodic cleanup task; it is the first phase of every
> downstream change cycle.**

## Better strategy than “always merge upstream immediately”

The policy is **upstream-first**, but not “chase a moving upstream HEAD inside the same
feature implementation.”

Use a two-stage cycle:

```text
STAGE A — QUALIFIED BASELINE
fetch upstream
-> choose exact upstream SHA
-> pin it for the cycle
-> true merge into an integration branch
-> reconcile seams
-> run baseline qualification
-> establish a green downstream baseline

STAGE B — TARGET CHANGE
branch from that qualified baseline
-> implement exactly the requested downstream change
-> run target + regression qualification
-> final upstream drift check
-> merge only if the baseline is still admissible
```

The exact upstream pin is immutable during Stage A/Stage B. This prevents the target change
from being built on a moving foundation.

Before final merge, fetch upstream again **only to snapshot and classify drift**. The selected
pin stays immutable. If upstream advanced, record the observed tip, compare it with the pin,
and classify the delta for the next cycle. Do not reopen Stage A or perform another upstream
merge in the active promotion cycle solely because `upstream/main` moved: qualification is for
the recorded SHA, not a moving branch name.

Hold promotion only for a confirmed defect in the candidate itself or a failed required check.
After the PR is approved and merged, fetch `origin/main` and fast-forward local `main`; the
newly observed upstream tip is input to the next Stage A cycle.

## Mandatory pre-change gate

Before editing runtime code, the coding agent must record:

```text
DOWNSTREAM_MAIN_SHA
UPSTREAM_MAIN_SHA_OBSERVED
CURRENT_PIN_SHA
git merge-base
downstream ahead/behind
current required CI state
affected owners
affected registered seams
```

Then answer:

1. Is the selected upstream pin already an ancestor of the candidate baseline?
2. Has upstream advanced since that pin?
3. Do the new upstream commits touch any affected owner or seam?
4. Is current downstream main green on required exact-head gates?
5. Are there unclassified or overdue REMOVE seams in the affected surface?
6. Can the target change be implemented on a qualified baseline without mixing it with
   migration work?

If the answer to 1 or 4 is **no**, ordinary target implementation is blocked.

If upstream has advanced, Stage A must either:
- adopt a newly selected exact upstream pin and qualify it, or
- document an explicit temporary exception because the upstream candidate itself is known
  broken/unadoptable. Such an exception must be recorded in CURRENT_STATE + engineering
  journal and may not be silently assumed.

## Branch discipline

Never perform “sync + feature” as an indistinguishable single patch.

Preferred sequence:

```text
main
 |
 +-- integration/upstream-<date>-<sha>
 |      true two-parent merge
 |      seam reconciliation
 |      qualification
 |
 +-- feat/<target-change>
        based on qualified integration/main baseline
        target implementation only
```

For large migrations, the integration lane may be promoted to main before the feature lane.
For a small delta, the integration lane may remain a separate parent/PR, but its ancestry,
tests and seam state must remain independently inspectable.

## Upstream merge rules

- fetch `NousResearch/hermes-agent:main`;
- choose one exact SHA and record it;
- merge the actual upstream history; do not fake synchronization by copying files;
- do not squash away the upstream ancestry for baseline adoption;
- do not use blanket ours/theirs on semantic conflicts;
- adopt upstream structural owners first;
- semantic-port Workstation invariants through generic contracts;
- keep only minimum necessary first-party seams;
- no capability regression for diff purity;
- no second canonical owner.

Canonical rule:

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ MINIMUM NECESSARY FIRST-PARTY SEAMS
+ EXACT-HEAD QUALIFICATION
```

## Seam maintenance is part of synchronization

Every Stage A cycle must re-run the semantic seam decision procedure.

For each affected seam:

```text
REMOVE
UPSTREAM_ABSTRACT
PRESERVE_FIRST_PARTY
```

A seam already marked REMOVE is **open debt until it is actually removed**. A passing seam
inventory only proves that seams are classified; it does not prove that the intended
migration is complete.

The cycle must update:

- `workstation/first_party_seams.json`;
- `workstation/UPSTREAM_DELTA.md`;
- `workstation/PATCH_MANIFEST.md`;
- current state / roadmap / engineering journal when disposition or qualification changes.

## Current baseline snapshot at policy creation

Observed on 2026-09-20:

```text
downstream main:
6dd02b9e3f026e4ed8f6cfe36d75cb770002dd2a

last adopted upstream pin:
6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170

latest upstream main observed:
501d8ba4e075281d5d7ea97b59cbac810ef12d89

downstream vs latest upstream:
ahead: 504
behind: 365
merge-base: 6a078969...
```

The historical 13k-commit divergence is closed, but the downstream is already behind again.
Therefore the **next code-changing downstream cycle must begin with a new Stage A upstream
baseline refresh**.

## H-078C post-merge qualification debt that Stage A must carry

The current exact-head Workstation CI is red.

Observed contract run:

```text
728 passed
1 failed
1 warning
```

The failure is the H-078B runtime-independence test observing `run_agent` already present
in `sys.modules`. Treat this as a qualification failure until the cause is reproduced and
closed; do not preserve a VERIFIED claim merely because the same test passed in an isolated
local subset.

The Workstation `core-patch-dry-run` also reports:

```text
ERROR: browser AppView: expected one anchor, found 0
```

Open architectural debt confirmed by post-merge inspection:

1. **Browser authority switch incomplete** — `WorkstationBrowserController.attach_to_broker()`
   exists, but the normal Browser path still retains the bespoke
   `tools.browser_workstation.workstation_routed_browser_handler` route and registered
   REMOVE seams.
2. **Duplicate batch admission** — `admit_tool_batch()` is invoked in
   `agent/turn_tool_round.py` and again in `run_agent.py::_execute_tool_calls()`.
   The normal full-batch boundary must have one owner.
3. **Adapter bootstrap fail-open** — `workstation/__init__.py` catches adapter installation
   errors with a broad silent exception. When Workstation is expected to supervise, adapter
   installation failure must be explicit/fail-closed or a clearly degraded mode.
4. **Documentation / registry stale** — historical H-078B COMPLETE/VERIFIED language and
   pre-H-078C baselines no longer describe exact main state.
5. **H-078C implementation report incomplete** — baseline ancestry is proven, but the
   report did not complete the requested Browser/Desktop/H-077/full-qualification closure
   sections.

## Required closure before H-078C can be called QUALIFIED

At minimum:

- new upstream Stage A pin adopted and ancestry proven;
- exact-head Workstation CI green;
- runtime-independence gate correctly isolated and green;
- browser AppView/core-patch anchor gate green;
- one canonical tool-batch admission owner;
- Browser routing authority either switched to BrowserControlBroker/controller or the
  deliberate residual path is explicitly justified and reclassified;
- no silent required-adapter initialization failure;
- H-077/H-078 regression ladder green on the exact candidate head;
- affected Desktop/Browser E2E green;
- seam registry reflects actual state, not intended state;
- roadmap/current state/journal/intelligence match the exact candidate;
- final report states READY_FOR_MAIN only from exact-head evidence.

## Final promotion rule

A downstream target change is not ready merely because its focused tests pass.

Promotion requires:

```text
qualified upstream baseline
+ seam audit / disposition current
+ target behavior green
+ required exact-head CI green
+ final upstream drift classified
```

If any of those is missing, the correct state is **NOT READY FOR MAIN**.
