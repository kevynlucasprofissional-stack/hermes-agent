# Mainline Consolidation

This is the durable record for the extraordinary consolidation performed before
V1 #1.5. It complements the smaller Mainline Consolidation Review required after
later major milestones.

## Gate result

**PASS**

- audit base: `main@4b04f4c4d2af5620426589529d29b700cfc21fb0`;
- V1 #1 accepted head: `d5be442021ea0c744351622317eef5212219786d`;
- V1 #1 promotion merge: `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`;
- V1 #1.5 sequencing/launcher accepted head:
  `39e51787d2414d0165ae8fa8b47d1f0e5f3e65cd`;
- sequencing/launcher promotion merge:
  `4b04f4c4d2af5620426589529d29b700cfc21fb0`;
- gate evidence head: `872cbc57ce919ca505650da4a7593fc73f4276bb`;
- material `NEEDS INVESTIGATION`: **0**;
- open predecessor or historical diagnostic PRs after closure: **0**.

`PASS` means the accepted product line and required evidence are reachable from
the audit base, every repository line observed during the audit has a disposition,
and V1 #1.5 may branch only from the resulting `main`. It does not mean all known
product debt is fixed. In particular, KI-006 remains classified Windows
portability/test debt and must not be presented as a green broad suite.

## Promotion sequence closed

| Work                                    | Accepted disposition                                                                           | Evidence                                                                                                                       |
| --------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| PR #11 — BrowserSessionState            | `MERGE` — completed                                                                            | H010 `VALIDATED`; 5 focused files / 46 tests; merge `e0a99ef3...`                                                              |
| PR #12 — sequencing + one-click dogfood | `REBASE+MERGE` equivalent via explicit non-rewriting merge of `main`, then `MERGE` — completed | reconciled tree `2eb3f9a7...`; 26 Workstation contracts; exact Windows install/typecheck/focused/H010 pass; merge `4b04f4c...` |
| PRs #4, #5                              | `HISTORICAL EVIDENCE ONLY` + `CLOSE PR` — completed                                            | controlled Implementation 2 / KI-006 baseline and candidate diagnostics                                                        |
| PR #6                                   | `SUPERSEDED` + `CLOSE PR` — completed                                                          | schema capability was finalized and promoted by PR #7                                                                          |
| PR #8                                   | `HISTORICAL EVIDENCE ONLY` + `CLOSE PR` — completed                                            | temporary source-identical Implementation 3 validation workflow                                                                |

PRs #1, #2, #3, #7, #9, #10, #11, and #12 are merged. PRs #4,
#5, #6, and #8 are explicitly closed with their classification recorded on the
PR. There is no predecessor PR left open.

## Branch disposition ledger

The following table classifies every non-`main` branch observed through the
GitHub API at the audit base. Retained historical refs are not alternate product
lines and must not be used as the base of new work.

| Branch                                        |                    Audit relationship to `main` | Classification                            | Action / rationale                                                                           |
| --------------------------------------------- | ----------------------------------------------: | ----------------------------------------- | -------------------------------------------------------------------------------------------- |
| `bot/js-autofix`                              |                        diverged; one bot commit | `REJECTED/DO NOT PROMOTE`                 | Formatter output touches unrelated product files and is reproducible; never merge wholesale. |
| `diagnostic/impl2-ui-platform-baseline`       |               diverged; diagnostic-only commits | `HISTORICAL EVIDENCE ONLY`                | Keep ref for KI-006 provenance; PR #4 closed.                                                |
| `diagnostic/impl2-ui-platform-candidate`      | diverged; obsolete candidate/diagnostic commits | `SUPERSEDED` + `HISTORICAL EVIDENCE ONLY` | Accepted installer source is already on `main`; PR #5 closed.                                |
| `docs/impl4-promotion-closure`                |                                        ancestor | `ALREADY ON MAIN`                         | Historical ref only.                                                                         |
| `feat/workstation-integrated-mvp-dogfood`     |                                        ancestor | `ALREADY ON MAIN`                         | Promoted by PR #12; historical ref only.                                                     |
| `fix/workstation-bootstrap-installer`         |                                        ancestor | `ALREADY ON MAIN`                         | Promoted bootstrap history.                                                                  |
| `impl3/workstation-browser-capability`        |                                        ancestor | `ALREADY ON MAIN`                         | Promoted capability history.                                                                 |
| `impl4-browser-task-lifecycle`                |                                        ancestor | `ALREADY ON MAIN`                         | Promoted BrowserTask history.                                                                |
| `noop`                                        |                                        ancestor | `ALREADY ON MAIN`                         | Old merge anchor; no active work.                                                            |
| `validation/impl2-canonical-source`           |                                        ancestor | `ALREADY ON MAIN`                         | Validation ref points at promoted source.                                                    |
| `validation/impl3-browser-session-capability` |     diverged; older source + temporary workflow | `SUPERSEDED`                              | Final source is on `main` through PR #7; PR #6 closed.                                       |
| `validation/impl3-final`                      |                                        ancestor | `ALREADY ON MAIN`                         | PR #7 history.                                                                               |
| `validation/impl3-focused-final`              |                 diverged; workflow-only commits | `HISTORICAL EVIDENCE ONLY`                | Evidence retained; PR #8 closed.                                                             |
| `workstation/browser-session-state-stabilize` |                                        ancestor | `ALREADY ON MAIN`                         | Exact accepted PR #11 head.                                                                  |
| `workstation-validation`                      |                                        ancestor | `ALREADY ON MAIN`                         | Promoted context history.                                                                    |
| `wp/codex/browser-session-state-core`         |                                        ancestor | `ALREADY ON MAIN`                         | Core candidate is contained by accepted PR #11 history.                                      |

Branch deletion is not required for this gate because immutable diagnostic refs
carry useful provenance. Their classification is authoritative: only `main` is
the product base. If a retained ref becomes operationally confusing, it may be
deleted after verifying that its linked PR and evidence remain reachable.

## Canonical-state reconciliation

The consolidation candidate reconciles the state-bearing documents so they no
longer describe Implementation 4 or BrowserSessionState as pending:

- `CURRENT_STATE.md` records promoted BrowserSessionState and the dogfood
  sequencing/launcher;
- `DECISIONS.md` records mainline/consolidation policy as D-012;
- `CONSTRAINTS.md`, `TESTING.md`, `KNOWN_ISSUES.md`, `ROADMAP.md`, and the
  Workstation README use the same phase boundary;
- `UPSTREAM_DELTA.md` marks HW-013 as validated and promoted;
- the engineering journal closes WP-01 and records this audit;
- executable document contracts protect this gate record and ordering.

No source or evidence needed by V1 #1.5 exists only on a lateral branch.

## Gate-candidate evidence

On exact candidate `872cbc57ce919ca505650da4a7593fc73f4276bb`:

- Workstation integration anchors, component lock and license policy passed;
- all **29 Workstation contracts passed**, including the three new mainline
  consolidation contracts;
- normal Windows install passed and left the checkout clean;
- candidate diff and complete Desktop typecheck passed;
- BrowserSessionState lint/format, 5-file / 46-test focused foundation and the
  native H010 step passed;
- local `git diff --check`, integration validation, targeted Markdown Prettier
  and seven direct document-contract checks passed;
- the canonical local Python runner correctly refused the pytest-less local
  environment; the 29-test GitHub run is the authoritative Python evidence.

The unchanged broad UI/Electron diagnostics continue after these scoped gates
and retain the KI-006 classification. They are not represented as green.

## Gate checklist

- [x] Accepted/required code is reachable from the audit-base `main`.
- [x] No valid lateral product fix remains unpromoted.
- [x] Every observed PR and branch is classified.
- [x] Superseded diagnostic PRs are formally closed.
- [x] Canonical state, roadmap, decisions, constraints, tests, and journal agree.
- [x] Required BrowserTask/BrowserSessionState tests and native probes are versioned.
- [x] No stale predecessor milestone remains active.
- [x] Only one canonical product line exists.
- [x] V1 #1.5 can start exclusively from `main`.
- [x] No material `NEEDS INVESTIGATION` remains in the gate.

## Recurring Mainline Consolidation Review

At the end of each later major milestone, before starting the next, perform a
proportional review:

1. verify the accepted head and merge are reachable from `main`;
2. classify new PRs/branches and close superseded temporary lines;
3. reconcile canonical state/roadmap/decisions/testing documentation;
4. confirm required tests, probes, workflows, and upstream-delta entries are on
   `main`;
5. record unresolved material work explicitly before it can block or transfer
   to the next milestone.

This recurring review is intentionally smaller than the one-time historical
gate recorded above.
