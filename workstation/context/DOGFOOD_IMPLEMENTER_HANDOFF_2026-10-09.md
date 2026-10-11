# IMPLEMENTER HANDOFF — Hermes Dogfood-first Causal Closure (D-042)
**Date:** 2026-10-09. **Status:** IMPLEMENTATION REQUEST — NOT EXECUTED. **Repo:** `kevynlucasprofissional-stack/hermes-agent`.
**Read-time budget:** first 15 minutes: the exact paths below; discover other source only when a falsifiable test demands it.
**Output goal:** a user-run Hermes Work that learns safely during use and a native HyperFrames creative experience, not a pile of green mocks.

## START IMMEDIATELY (in exactly this order)

1. Identify current local checkout, branch/HEAD, clean/dirty state, *all* worktrees and the last HyperFrames installation. **Preserve uncommitted code and outputs.** Compare actual local code against remote `main` (`f21e803b` as 2026-10-09 observation), creative PRs #57–#62, and branch `workstation/laya-direct-system1`. Read GitHub as the durable remote source; a missing remote HyperFrames commit is NOT permission to discard the installed local editor.
2. Mandatory rules: `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md`, `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `FIRST_PARTY_SEAM_POLICY.md`, `UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md`. Execute H-079 two-stage single-pin gate: upstream fetch/pin -> seam classification -> exact baseline tests -> only then target coding. If red: fix baseline first or explicitly document existing development-only exception; no production promotion. Do not change main.
3. User acceptance: `workstation/context/DOGFOOD_PRODUCT_GATE_2026-10-09.md` (DF-001..026); `workstation/dogfood/{210926 05h58.md,220926 22h07.md,02.10.26.md,03.10.26.md,06.10.26.md,07.10.26.md,readme.md}` (all original notes must be read in full). Read `workstation/context/LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md` (D-039), `ONLINE_COMPILABILITY_POST_IMPLEMENTATION_AUDIT_2026-10-08.md` (D-038 safety), `DECISIONS.md` D-037..040, `engineering-journal/h080b-real-use-experience-loop-audit-2026-09-23.md`. For Creative check this repo's PR #62 `workstation/creative-workstation/HYPERFRAMES_ADOPTION_2026-10-09.md`, `HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md`, and `DOGFOOD_CREATIVE_GATE_2026-10-09.md`.
4. Produce a compact `DF-BASELINE.md` in a reviewable branch: exact current SHA/upstream pin/CI, local WIP inventory, implementation facts per DF ID, P0 negatives and existing owners. Never treat the 2026-10-09 audit as a newer code snapshot. **From here implement; do not stop at an architectural proposal.**

## File-level execution DAG

`DF0 H-079 baseline & preservation`
-> `DF1 progressive verified evidence & OBSERVE_ACTIVE`
-> `DF2 durable adaptive learning scheduler`
-> `DF3 verifiable DIRECT / production validator / run-local adoption`
-> `DF4 native browser / delegated child run / goal-sufficient verification`
-> `DF5 historical opportunities / recorder / site adapters`
-> `DF6 existing local HyperFrames native life-cycle`
-> `DF7 empirical dogfood + Windows CI + drift`
-> `DF8 optional integrations discovery only`.

Parallel DF4/DF6 is allowed **only** after shared BrowserTask, TaskRun, proof and process contracts are stable and two agents do not modify the same owners. Never bypass RED gates to claim progress.

### DF1 — make safe learning active (highest impact)
- **Edit owners**: `workstation/experience_compiler/compilability_monitor.py::LearningPolicy,resolve_policy,TaskRunObservationWindow,process_event,mine_candidate_in_run`; `workstation/integrations/hermes/tool_observer.py`; `workstation/operational_kernel.py`; `workstation/experience_compiler/{progressive,corpus,lifecycle}.py`.
- Current verified defect: `mode != DIRECT` currently returns before `mine_candidate_in_run`; tests assert SHADOW=0 mining. **Separate** `OBSERVE_ACTIVE / safe scoped mining / preparatory validation` from `SHADOW_FOR_EFFECTS / DIRECT_VERIFIED`. Under effect SHADOW, capture/mining must still happen when canonical verified evidence exists. Never grant effects because Laya guessed MINE. Pre-filter on semantic verified transitions, repetition, counterexample, error resolution; bounded event-triggered decisions, no per token, wall-clock polling or raw gestures. Keep Laya non-authoritative; do not block the foreground on Laya.
- **RED first**: test SHADOW with verified in-run examples expected `mining_attempts>0` and `ready_offers==[]`; prove ambiguous/unverified samples never become VERIFIED; simulate model timeout/abstention and ensure agent keeps running. Replace old SHADOW zero-mining assertion with correct separation after first RED.

### DF2 — persist learning opportunities under bounded resources
- **Edit**: `compilability_monitor.py::_get_window,schedule_event,stop,TaskRunObservationWindow` plus **existing** `ExperienceCorpus/ArtifactStore` for compact `workstation.run_learning_checkpoint.v1` metadata.
- High-value refs (new VERIFIED, negative control, changed verifier, task closure) must survive queue full/idle TTL 900s/shutdown/restart. Use priority + dedup + canonical durable pointer on saturation; fair per TaskRun; safe spool quota and loss diagnostics if truly out of resources. Cache TTL must not erase knowledge or retry state.
- Replace permanent 3 compile / 3 validate exclusions with `evidence_revision`-keyed retry/backoff. Do not spin against same evidence. Continue after per-checkpoint 100 item yield until work ends; re-read owner/lease each time. Persist references, **never** a live owner, token or authority grant.
- RED/negative: 65+ events queue 2; restart with pending candidates; drifted lease; same-evidence repeated fail; fresh sample after failed trial re-enables; 101+ items yield and resume; cancellation and no duplicate effect.

### DF3 — secure real promotion/adoption
- **Edit**: `compilability_monitor.py::resolve_policy,validate_candidate_run_local`, `compilability_validation.py`, `experience_compiler/lifecycle.py::ValidationEnvironmentProvider`, `workstation/run_adoption.py`, `integrations/hermes/run_local_adoption.py`, `control_plane/verification.py` only if truly needed.
- Replace arbitrary nonempty `direct_qualification_ref` with signed or otherwise cryptographically integrity-bound **resolvable attestation** of code/provider/Laya model revision/schema/operation family/effect class/verifier/safe-env/exact tests/expiry/revocation; load via profile configuration, not new environment flag. Unqualified families continue safe mining without mutation.
- Implement first real, opt-in local `write_file` owner-certified canary: isolated positive + negative verifier execution, controlled replay, independent read-after-write, canonical receipts, active user TaskRun admitted effect budget; no synthetic replay or raised LOCAL_MUTATION.
- Same-run candidate allowed from verified examples for next equivalent pending item under existing owner, **not automatically global PROMOTED**; global requires cross-run policy. Verify every adopted item, stop and reconcile uncertain effect with zero blind retries.
- RED: qualification string fake/revoked/wrong model refuses DIRECT; missing validation env/ref; replay exceptions; foreign-run sample; wrong target; canceled/revoked lease; readback mismatch; work claimed as successful only after verified receipt. Meter true System-2 count vs instrumented baseline; unknown stays unknown.
- Use `test_online_compilability_safety.py`, `test_online_compilability_monitor.py`, `test_e2e_operational_resolution.py`, `test_hierarchical_experience_compiler.py` as existing suite anchors.

### DF4 — native browser: prime route, correct verified evidence, child parity
- **Owners**: `workstation/integrations/hermes/{browser_controller,operational_resolution,tool_observer}.py`, `workstation/browser_session.py`, `workstation/browser_runtime.py`, `tools/browser_workstation.py`, `gateway/browser_control_broker.py`, `agent/subagent_lifecycle.py`, `apps/desktop/electron/workstation-browser-runtime.ts`, existing Browser Hub UI.
- Native desktop/browser intent uses existing Chromium. When owner-bound controller is unavailable, fail closed, not fallback to an external browser. For `open_site`, verify target host/URL and readiness from trusted controller/readback, **not** unnecessary login/vision. Actual accepted evidence must reach ExperienceCorpus and eventually existing registry/provider-free compiler; do not create a BrowserSkill or parallel executor.
- Delegate BrowserTask identity with parent-child lineage, explicit narrower authority/session/lease, independent task/run id, same browser broker, visible child-run in Browser Hub, human takeover/fence/cancel propagation. No privilege inheritance by copying parent tokens. E2E two concurrent child runs and a human takeover; no cross-task tabs or leaked sessions.
- Native recorder opt-in (DF-015) comes only after browser lifecycle and privacy controls; record semantic operations and validated receipts, redact user-entered secrets/PII, support pause/review/delete. Site prep catalog (DF-016) as versioned templates with DOM/version checks; Chrome extensions (DF-020) as a separate empirical adapter gate.
- Tests: `test_browser_broker_authority.py`, `test_browser_lease.py`, `test_h080b_native_browser_experience_loop.py`, real packaged/Desktop Browser Hub E2E. Verify first novel browser run -> accepted samples -> eligible repeated run -> candidate -> validator/replay -> registry -> next route before provider (zero calls only when actual pre-reasoning path qualifies).

### DF5 — retroactive backfill and opportunity accounting
- **Owners**: `experience_compiler/{corpus,compiler,hierarchical,lifecycle}.py`, `operational_capabilities.py`, existing ArtifactStore, Skills/Memory and telemetry. **No second corpus, DB or workflow engine.**
- Add opt-in importer of historical conversation Markdown + relevant existing trace receipts, dedup/provenance/privacy scopes. Plain Markdown alone is unverified narrative, NEVER sufficient for promotion; link to real execution evidence or leave candidate HELD. Suggest prereasoned skills for repeated websites only after validation and versioning.
- Produce `workstation.compilability_opportunity_audit.v1` with `eligible,detected,attempted,held,validated,promoted,run_local_reused,missed,unknown,true_negative` and an explicit evaluated denominator from human-labeled/independently verified benchmark cases. **Do not** claim the runtime compiled *all possible* capabilities; exhaustive general possibility is unknowable. Use counterfactual verified replay for a bounded reference set to identify missed opportunities. Re-evaluate after changing evidence or interpreter version; no automatic unsupervised promotion from chat.
- DF-017 web UI -> typed API/procedure adapter: prove permission, per-service terms and rate limit, authentication and owner scope; Google AI Studio transcription is **research hypothesis**, not permission to bypass paid APIs or platform restrictions. DF-023 ACIRV brief only once verified available and authorized.
- Potential "MCP n8n" answer: offer visual reuse/composition over existing OperationalCapabilities; decide on workflow UX from benchmark rather than reimplement an unsupervised n8n engine.

### DF6 — audit actual HyperFrames Work (do not rebuild a working local installation)
- Read local installed source, PR #62 D-041 and `creative-workstation/DOGFOOD_CREATIVE_GATE_2026-10-09.md`; pin exact HyperFrames SHA, license/transitive dependencies and owner interfaces. Reconcile draft PRs #57–#61 selectively.
- Preserve one user-facing Electron WebContentsView/BrowserTask/Session/TaskRun, Studio's editable HTML/CSS/JS single project source, optimistic ETag 409, scoped typed AI edits, ProcessRegistry owned sidecar, ArtifactStore/Journal, independent PNG & genuinely **animated** MP4 verification using multiple decoded different frames. FFmpeg still-loop is NOT animation proof.
- Real human edit -> agent edit -> version conflict -> manual resolution -> save/reopen -> export -> same ExperienceCorpus observation and qualified deterministic creative microprocedure. No Framey cloud requirement or second permission / Experience compiler.
- Run Windows native packaged E2E, restart/crash/cancel, pressure tests, unauthorized-loopback mutation negatives. Unknown local code = explicit BLOCKED, not invented pass.

### DF7 — acceptance and CI
Build reproducible scenarios `E1 native browser`, `E2 12 Trello cards`, `E3 HyperFrames human+agent` exactly as in `DOGFOOD_PRODUCT_GATE_2026-10-09.md` and `DOGFOOD_CREATIVE_GATE_2026-10-09.md`. Produce actual TaskRun IDs, trace refs, receipts, baseline and replay decisions, screenshots/video only as supplements, System-2 measurement provenance. If external credentials not authorized, use a safe, explicitly labeled fixture **in addition to**, not instead of, real native-product smoke. No unattended posting on Trello/ChatGPT/Instagram or collection of confidential sessions.
- Run relevant old and new Python tests, Desktop typecheck, native Electron E2E, Workstation CI, Windows Browser workflow, smoke and seam audit on exact candidate HEAD. Classify failures (regression, existing baseline, environment) without disabling unrelated gates.
- Final upstream tip observation vs single fixed pin, drift classification. Update `ROADMAP.md`, `CURRENT_STATE.md`, `DECISIONS.md`, `HERMES_WORKSTATION_INTELLIGENCE.md`, Engineering Journal and dogfood ledger with **measured** status, test command, head SHA, artifact ref, remaining blockers. Do NOT merge main.

### DF8 — explicitly deferred peripheral backlog
K-Tools, X-cursos runner, YT-DLP_TUI, ECO, ATOM and Agora assessed via minimal adapter design; Agora/Mirofish/population simulation/Random Forest requires independent scientific and performance feasibility research, never assert "8 billion people" simulated. User's ACIRV Marketing Brief in Data must first be discovered and authorized. No speculative integrations during P0/P1.

## Recommended PR slices

- PR-A: DF0 baseline/seam + test groundwork (no Workstation feature mixed with upstream sync).
- PR-B: DF1–DF2 learning plane, RED/GREEN and durability.
- PR-C: DF3 attestation + local verified adoption.
- PR-D: DF4 native browser/subagent causal loop.
- PR-E: DF5 historical/replayer/recorder/site metadata (feature flagged).
- PR-F: DF6 existing HyperFrames product closure.
- PR-G: DF7 exact-head/native/Windows qualification; DF8 remains separately tracked.

## Required reporting contract

After each phase print:
`PHASE | exact_head | changed_paths | RED_before | GREEN_after | native_evidence | negative_cases | unresolved/CI | next_phase`.
At the end update **each DF ID** `implemented/verified/blocked/not_applicable` with hyperlinks/receipt hashes. A product feature is NOT VERIFIED until native E2E; an uncertain or mocked result is NOT VERIFIED. Report any user actions needed; do not overwrite a local worktree, alter `dogfood/`, force push, silently change upstream pin or merge main.

**Immediate command intent:** read mandatory agent/context docs, inventory local HyperFrames state, run upstream-first preflight, then create the first **failing DF1 shadow-safe-mining regression test** against the actual qualified baseline; proceed all the way through DF7 where execution/authority is available, recording truthful blockers otherwise.
