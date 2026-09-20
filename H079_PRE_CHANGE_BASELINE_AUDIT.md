# H-079 Pre-Change Baseline Audit

Date: 2026-09-20  
Status: `STAGE A & B COMPLETE — LOCALLY QUALIFIED (see H079_BASELINE_QUALIFICATION_REPORT.md)`  
Repository: `kevynlucasprofissional-stack/hermes-agent`

## Immutable cycle baseline

| Field | Value |
|---|---|
| `DOWNSTREAM_MAIN_SHA` | `6dd02b9e3f026e4ed8f6cfe36d75cb770002dd2a` |
| `UPSTREAM_MAIN_SHA_OBSERVED` | `b7d7d2929a10e0658a98a7a03f4531093e1480ed` |
| `CURRENT_PIN_SHA` / `UPSTREAM_PIN` | `b7d7d2929a10e0658a98a7a03f4531093e1480ed` |
| merge-base before sync | `6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170` |
| downstream ahead before sync | `504` commits |
| downstream behind before sync | `364` commits |
| integration branch | `integration/upstream-20260920-b7d7d292-h079` |
| origin remote | `https://github.com/kevynlucasprofissional-stack/hermes-agent.git` |
| upstream remote | `https://github.com/NousResearch/hermes-agent.git` |

The selected upstream pin is immutable for this cycle. A later upstream fetch is a drift
classification gate, not permission to move the pin inside this implementation.

## Repository state before changes

- `git status --short --branch`: clean `main...origin/main`; Git emitted a permission warning
  while enumerating the unrelated `test-tmp-h0771/` directory.
- starting branch: `main`.
- starting `HEAD`: `6dd02b9e3f026e4ed8f6cfe36d75cb770002dd2a`.
- both required remotes were already configured with the expected URLs.
- `git fetch origin --prune` and `git fetch upstream --prune` completed before selecting the
  pin.
- the upstream-first policy branch is present as
  `origin/docs/upstream-first-change-gate` at
  `9fa2e2fd5e2b2a3bb84b5a365f4e38e6cb061253`; it is not yet an ancestor of the starting
  downstream `main` and must be included unchanged in the final implementation branch.

## Pre-change gate answers

1. **Is the selected upstream pin already an ancestor of the candidate baseline?** No. The
   true upstream merge and ancestry proof are Stage A work.
2. **Has upstream advanced since the previously adopted pin?** Yes. The selected pin is 364
   commits ahead of downstream `main` relative to the existing merge-base.
3. **Do the new commits touch affected owners or seams?** Pending owner-level diff audit
   before conflict resolution.
4. **Is current downstream `main` green on required exact-head gates?** No. The canonical
   policy records Workstation CI at approximately `728 passed, 1 failed, 1 warning`, plus a
   failing Browser AppView core-patch dry-run anchor.
5. **Are there unclassified or overdue REMOVE seams in the affected surface?** The existing
   registry must be audited after required-context reading. A zero-unclassified audit will
   not be treated as proof that REMOVE debt is closed.
6. **May target corrective implementation begin now?** No. It remains blocked until the
   pinned upstream is truly merged, conflicts and affected seams are reconciled, and the
   baseline qualification sequence reaches the corrective owners.

## Known affected owner families to verify against current code

- Workstation Runtime independence and alternate-reasoner lifecycle.
- Browser registrations, generic extension router, `BrowserControlBroker`, Workstation
  controller attachment, native Electron runtime, BrowserTask/session/run/principal fencing,
  recovery and compatibility routing.
- `agent/turn_tool_round.py` full-batch admission and every caller of
  `run_agent.py::_execute_tool_calls`.
- Workstation adapter installation/bootstrap semantics.
- Desktop integration patch anchors and their current upstream owners.
- H-077 operational truth, Kanban completion transaction, and pre-/post-tool causal ordering.

## Required CI state at entry

The exact starting head is not qualified. Stage A must not claim `QUALIFIED` until the
required local baseline ladder and exact candidate-head GitHub Actions are green. The final
upstream drift check may also force Stage A to reopen if new upstream changes overlap these
owners.
