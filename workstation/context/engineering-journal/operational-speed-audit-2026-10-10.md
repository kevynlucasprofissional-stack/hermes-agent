# Engineering Journal — Hermes Work operational latency/cost audit (2026-10-10)

**Entry classification:** STATIC CODE + REPO LOG FORENSICS + MAINTAINER-PROVIDED 3 DOCUMENTS. **No source-code patch, local Windows/Electron test, exact-HEAD CI, upstream Stage A refresh, or measured currency/tokens saving in this docs-only activity.** Audited `codex/dogfood-causal-closure-20261009@8e64b38a81adcf8a01dc2ed05aa3eb078adc9f9f`, main `f21e803b3525b70ee6be2305e579c1cc1f930e74`. Source evidence: `dados/Sessões Hermes/` (not `Data/`), dated `workstation/dogfood/` records and 2026-10-10 attached analyses.

## Hypothesis and discriminating experiment

**HYPOTHESIS:** for well-known native browser and Studio procedures, end-user latency and costs are dominated by LLM-mediated capability rediscovery, primitive-by-primitive turns, repeated readiness probes and large payload handling; not the speed of individual Chromium operations. **Falsifier:** instrumented equivalent cold/warm tasks reveal high browser runtime dominance or no verified reduction after pre-LLM, composed, typed execution; in either case re-rank priorities based on actual evidence. **Smallest experiment:** instrument fresh `open Trello` and `open HyperFrames` on controlled Electron with unique calls and provider rounds, then compare baseline/fast path at identical starting state. Compare median/p95, terminal errors, readback, tokens and actual cost. Before P0 live results all expected savings are estimates/targets.

**Safety hypothesis:** historical Trello human-edit overwrite (#012) indicates sync lacks sufficient concurrency protection. **Falsifier:** reproduce against current exact HEAD with immutable 2567/2480-character versioned test and show no possible overwrite; otherwise implement CAS/conditional UI-safe readback and fail-closed conflict.

## Observed evidence and reproducibility limits

| Trace | Export messages | Logged tool calls | Console requests | Distinct console call IDs | Terminal requests | Distinct terminal IDs |
|---|---:|---:|---:|---:|---:|---:|
| Open Trello 2026-10-09 | 837 | 386 | 163 | 122 | 76 | 69 |
| Abrir HyperFrames 2026-10-09 | 301 | 146 | 0 | — | 53 | 45 |

Trello median matched `browser_console` tool elapsed ~0.06s vs ~90-minute recorded session; HyperFrames first confirmed open ~5m40s. Trello had 137 distinct console scripts among 163 logged requests. Four additional heterogeneous historical traces recorded 761 Browser calls, 678 console requests, 238 terminal calls. Exports contain duplicate call IDs; no physical operation unique counts or cost inference from these totals. HyperFrames demo later included creative modifications but no proven coediting/animated MP4 E2E.

**Specific Trello incident:** automation wrote 2567-character description, user changed to 2480, automation restored old 2567, then manual recovery from Trello history; rollback is not a substitute for prevention. Other trace evidence: API 403 CSRF, long text truncation/`InvalidCharacterError`, base64/local Python server/`window.name` handling, `SUPERSEDED` handoff loops, non-atomic `execution_state_v2.json` update. Trello 33/33 claim lacks editorial exact-match/concurrent-edit guarantee.

## Source and prior-claim reconciliation

- Already present in audited branch: `agent/operational_resolution.py` pre-provider boundary, `workstation/integrations/hermes/operational_resolution.py` recovering established persisted intent, `OperationalKernel` browser primitives, `browser_readiness.py` wait contracts, `tools/browser_workstation.py` ref payload, `creative_studio_service.py` lifecycle and Electron `browser_creative_studio_open`, SHADOW mining/checkpoint handling and same-run offers in `compilability_monitor.py`. **Do not code duplicate systems.**
- Open: **new utterance** pre-LLM matching; full typed Studio start→health→native open; site operation composition; ordinary browser's exact artifact path wiring; safe Trello concurrent edit/resume; production E2E proof of same-run learning/economics.
- **P0 authenticity defect:** `compilability_monitor.py` `payload["signature"]=digest(payload)[:32]`, `recipes.py::digest` SHA256 without keyed emitter. Changes can be rehashed; hash protects accidental changes, not trusted issuer identity. Qualifying `DIRECT` requires actual authenticated, scoped, revocable attestation. Lack of evidence is not proof of unauthorized execution by itself.
- **P1 opportunity durability gap:** queue saturation preserves pointers/checkpoints, `schedule_event` may still return `False`; captured != evaluated != durably retried. `system2_calls_avoided_estimated` is **not** measured calls saved.
- `DF-BASELINE.md` reports `61/61` green local dogfood suites and `verified` labels, but Trello uses mock, native Chrome tests and Creative tests lack the requested live Windows/human UI validation. Correct semantics of status before release. Older D-042 documents that describe SHADOW=zero mining, DIRECT arbitrary nonempty ref and Studio not integrated describe **earlier/main** snapshots, not the exact audited branch. Do not rewrite old history as though every current code path were unchanged.

## Experiment ledger — designed, not run

| ID | Experiment | Support | Refute | Status |
|---|---|---|---|---|
| SPEED-01 | Instrument `open Trello` and `open HyperFrames`, baseline unique call/tokens/latency | System-2 and skills dominate; browser calls short | Chromium loads dominate equivalent full wall time | PLANNED / NOT RUN |
| SPEED-02 | RED for new-user-utterance fast path before persisted `objective_ref` | Existing resolver falls through despite known alias | Production binding already handles new intent | PLANNED / NOT RUN |
| SPEED-03 | RED for forged unkeyed DIRECT attestation | Altered payload with recalculated hash verifies | Independent trusted issuer check rejects | PLANNED / NOT RUN |
| SPEED-04 | RED for #012 edit conflict and safe 33-card replay | Automatic write overwrites manual remote state | Fails closed before overwrite | PLANNED / NOT RUN |
| SPEED-05 | HyperFrames registered Studio process vs arbitrary localhost origin | Foreign process URL currently admitted | Owner-bound instance provenance exists and rejects | PLANNED / NOT RUN |
| SPEED-06 | E2 12-item same-run compile/verified adoption and queue saturation | Qualifying sample leads to next verified item without System-2 | Missing proof, duplicated effect or dropped work | PLANNED / NOT RUN |

No experiment identifier reuses H/KI labels. Follow Engineering Journal anti-repeat: log each RED→GREEN result and exact candidate SHA, branch, runner, native TaskRun IDs, pass/fail, before/after metrics. Subsequent behavior claims require proof stronger than assertions in fixtures.

## Accepted documentation outcome

D-043: optimize latency and **cost per verified outcome** using existing owners, prioritize P0 baseline/attestation and P1 new-utterance fast-path, composed Browser readiness/artifact transport/Studio, P2 conflict-safe batching+same-run reuse, P3 native+CI qualification. **This entry records an implementation plan, not finished fixes.** Primary directive: `../OPERATIONAL_SPEED_COST_REDUCTION_2026-10-10.md`; command-ready handoff: `../OPERATIONAL_SPEED_IMPLEMENTER_HANDOFF_2026-10-10.md`. Keep H-079 and all effect/ownership proof gates open until satisfied.
