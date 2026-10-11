# Hermes Work — CW-01 baseline unblock and implementation resumption (2026-10-08)

**Document type:** actionable corrective handoff, not runtime implementation or proof of qualification.  
**Disposition:** BASELINE BLOCKED; corrective work may start in separate branches, **CW-02 not released**.  
**Authority:** [H-079](../context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md), [TESTING](../context/TESTING.md), [CURRENT_STATE](../context/CURRENT_STATE.md), [Known Issues](../context/KNOWN_ISSUES.md), [Creative implementation plan](IMPLEMENTATION_PLAN.md), [Verification Matrix](VERIFICATION_MATRIX.md). This handoff does not override any of them.

## 1. Observed anchors, not speculative claims

| Item | Evidence at investigation | Interpretation |
| --- | --- | --- |
| Downstream main | `f21e803b3525b70ee6be2305e579c1cc1f930e74`, 2026-10-08 | Laya D-038/D-039 was merged into main. Older branch-only/no-main-merge status sections are historical. |
| Adopted Hermes upstream pin | `71a2fe399bbd7a219c71f9d9fca2b313b01f2057` | Ancestor / prior adopted pin, not latest qualified upstream. |
| Observed candidate | `517b5e10febd619ce30bb22580e29b160266eb43` | Candidate only, not integrated or validated. CW-01 refresh reports 857 downstream-only / 10,510 upstream-only and material overlap; repeat on the future start HEAD. |
| CW-01 refresh | [PR #52](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/52), branch `codex/creative-cw01-refresh-20261008`, head `989e4aabd033` | Open, not merged when observed; contains refreshed receipts and `CW01_REFRESH_2026-10-08.md`. Do not treat its file as already present in main. |
| Exact-main Workstation CI | [run 37826432518](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37826432518) | `contracts` 7 failed / 893 passed / 2 skipped; all 7 share `ModuleNotFoundError: No module named 'laya'`. `core-patch-dry-run` passed. Core regressions/replay after failed test step were skipped. |
| Workstation Windows | [PR #52 run 37829895692](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37829895692) | Production `npm audit --omit=dev --audit-level=moderate` failed with **19** findings: 2 critical, 5 high, 4 moderate, 8 low. Subsequent packaging/Electron checks skipped. This is not a TypeScript compiler failure. |
| Distinct local historical audit | Earlier CW-01 audit reported 18 findings (2 critical, 4 high, 3 moderate, 9 low) | Not interchangeable with the PR #52 remote registry audit or a new current audit. |
| CW development | CW-01 BLOCKED; Creative/Electron E2E NOT_RUN; no engines installed/proven | Neither passing local owner tests nor source/license metadata qualifies an engine. |

**Source chain:** [CI profile](../../.github/workflows/workstation-ci.yml), [Laya qualification workflow](../../.github/workflows/laya-system1-qualification.yml), [project extras](../../pyproject.toml), [Windows audit workflow](../../.github/workflows/workstation-browser-windows.yml), [CW-01 main audit](CW01_AUDIT_2026-10-08.md), [PR #52 detailed refresh](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/codex/creative-cw01-refresh-20261008/workstation/creative-workstation/CW01_REFRESH_2026-10-08.md). Re-read current HEAD before executing.

## 2. Important causal distinctions

1. **Missing Laya in test environment is a verified immediate cause of these seven failures, not proof that Laya runtime is defective.** `workstation-ci.yml` currently installs `uv sync --locked --python 3.13 --extra dev --extra anthropic`. `pyproject.toml` declares `workstation-laya` through `system1-laya`, pinned to vendored `laya==0.3.23`; the dedicated Windows qualification workflow already uses `--extra workstation-laya`. Add the missing extra to the ordinary Workstation CI, without modifying tests/provenance. This is a **candidate fix**; rerun required.
2. **npm security gate is independent.** Registry-backed production audit ran in GitHub Actions despite a separately rejected *local* permission request. Do not report “no audit available.” Logs report affected paths including `@simple-git/argv-parser`/`simple-git`, `dompurify`/`mermaid`, `katex` (then no fix), `brace-expansion`, `http-cache-semantics`, `ip-address`, `postcss-selector-parser`, `source-map-js` and `undici`. Current advisory/version applicability and direct/transitive reachability require fresh review.
3. **Upstream divergence is not 10,510 independent manual fixes.** It is a frozen-pin ancestry + semantic owner-conflict reconciliation + test qualification task; neither blindly merge all upstream nor assert that old upstream pin is current.
4. **H-079 exception is narrowly defined.** Its documented temporary exception is admissible only with proof the upstream candidate is broken/unadoptable and explicit canonical records. Red CI and a large divergence do not constitute automatic user-approved waiver.
5. **Security and runtime readiness are different.** KI-024 is a confirmed P0 *voice input-authority* defect (ambient speech submitted as authoritative user turns); H-080B.3 still requires real native Electron proof; KI-025/H-082 covers startup/warm-install reliability. Treat prior locally passed tests as historical unless tied to the candidate.
6. **Historical documents require temporal qualifiers.** `CURRENT_STATE.md` and related notes contain pre-merge assertions that Laya was absent from main. Preserve historical evidence; append a prominent current status overlay, not retrospective rewrites or false closure claims.

## 3. Corrective lanes, owners, order and acceptance

| Lane | Smallest scope / starting files | Action | Required finish / stop |
| --- | --- | --- | --- |
| **R1 CI parity (first)** | `.github/workflows/workstation-ci.yml`; `pyproject.toml`; `uv.lock`; `workstation/context/TESTING.md`; `workstation/system1/provenance.py`; `workstation/tests/test_laya_*.py` | Make a single isolated workflow repair replacing `uv sync --locked --python 3.13 --extra dev --extra anthropic` with the same command plus `--extra workstation-laya`. Do not change Python, locks, tests or vendored Laya to make it green. Record H-079 preflight; this repair is infrastructure baseline triage, **not a CW-02 runtime waiver**. | Locked install, real import/provenance, 7 former failure tests, all Workstation contracts, subsequently unskipped core seam regression/replay, strict seams/anchors and exact-HEAD CI. If new failures appear, investigate root cause and keep separate. |
| **R2 npm production security** | `.github/workflows/workstation-browser-windows.yml`; root `package.json`, `package-lock.json`, `.npmrc`; impacted workspaces | Use remote audit log first; map advisories, exposure, direct/transitive edges, lock versions and compatible fixes. Update manifest/lock deliberately in its own PR; test install reproducibility, UI/build/platform and audit. `npm audit fix --force` is forbidden as blanket remediation. | Required production audit actually green, or explicitly reviewed, bounded risk exception according to project policy. Do not silently lower severity/skip audit. Local registry submission requires proper approval and secret/private-dependency check. |
| **R3 H-079 Stage A** | `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`; `UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md`; `FIRST_PARTY_SEAM_POLICY.md`; seam audit script; original upstream | Fix candidate SHA, fetch remotes, record merge-base/ahead-behind, inspect overlap; *actual* upstream-history integration on `integration/upstream-...`, concern-level `ADOPT_UPSTREAM / KEEP_WORKSTATION / SEMANTIC_PORT / EXTRACT_BOUNDARY`; reconcile first-party seams and owner authority, run H-079/H-078/H-077/Windows/Electron ladder. Do not mix with Creative feature and do not auto-merge. | Qualified pinned ancestry, exact-head CI, reconciled owners/seams, H-079 release evidence and final drift classification; if impossible, formal documented non-waived hold or evidence-based temporary exception. |
| **R4 P0 and product proof** | `workstation/context/KNOWN_ISSUES.md`; `VOICE_AUTOSTART_INPUT_AUTHORITY_INCIDENT_2026-10-03.md`; composer/voice source; H-080B.3; `WORKSTATION_BOOTSTRAP_STARTUP_RELIABILITY_2026-10-07.md` | Separate bugfix PRs, traced attribution to actual user/session, idle and remount negatives, real Electron/native tests and bootstrap warm-start/no-network proofs. Determine applicability to each Creative phase, never infer closure from unrelated gates. | Closed or explicitly and safely contained applicable blockers with actual receipts and required CI; no ambient STT authority, no optimistic UI/readback claims. |
| **R5 CW-02 onward** | `workstation/creative-workstation/IMPLEMENTATION_PLAN.md`, `VERIFICATION_MATRIX.md`, `PHASE_PROMPTS.md` | Only after R1-R4 applicable gates and admissible Stage A. CW-02 minimum opt-in discovery/health/lifecycle, then CW-03A React/SVG→Electron→PNG; CW-03B FFmpeg/ffprobe; CW-03C optional Remotion only after exact use/license review; CW-04 Penpot; CW-05 Three.js; CW-06 optional engines; CW-07 experience-backed reuse after one verified vertical. | Separate small PRs, concrete artifacts, positive/negative/E2E evidence, rollbacks, exact SHA, no auto merge. Independent CW-04/CW-05 and CW-03C paths must not block already qualified non-Remotion output. |

**R1/R2 may be investigated in parallel on independent branches.** H-079 preflight must be performed first for code-changing work; do not treat these lanes as authorization to skip its mandatory baseline gate for actual downstream feature development. If the baseline still blocks, only bounded gate-repair / safety work and investigation are admissible pending documented policy disposition.

### Exact known test and workflow entrypoints

```bash
# Original failing CI install (historical):
uv sync --locked --python 3.13 --extra dev --extra anthropic
# Proposed CI-only correction:
uv sync --locked --python 3.13 --extra dev --extra anthropic --extra workstation-laya

# Linux CI command after installation:
.venv/bin/python workstation/scripts/validate_lock.py
.venv/bin/python workstation/scripts/verify_licenses.py
.venv/bin/python -m pytest -q workstation/tests
.venv/bin/python -m pytest -q tests/tools/test_registry.py tests/tools/test_mcp_schema_cache.py tests/tools/test_mcp_trust_gating.py tests/agent/test_auxiliary_client.py tests/agent/test_tool_guardrails.py tests/agent/test_compaction_operational_refs.py
.venv/bin/python -m workstation.benchmarks.trello_regression
python workstation/scripts/apply_core_integration.py --root . --check

# Windows Laya qualification is a distinct profile (see workflow):
uv sync --locked --python 3.11 --extra dev --extra anthropic --extra workstation-laya
.venv/Scripts/python.exe -m workstation.scripts.qualify_laya_system1 --full

# Existing Windows production audit. Requires registry access:
npm audit --omit=dev --audit-level=moderate
```

**These commands are references from versioned workflows, not a claim they were re-executed during documentation work.** Confirm applicability/runner resources at execution time. Do not disable failed tests, replace imports with fakes, automatically retry uncertain effects, or merge if required gates fail.

## 4. Creative architecture to preserve after release

- Reuse `hermes_platform/resolver/app.py::AppResolver`, `workstation/capabilities.py`, `workstation/health.py`, `tools/process_registry.py`, `workstation/workers.py`, `workstation/host.py`, `tools/mcp_tool.py`, `agent/skill_commands.py`.
- Existing Electron `apps/desktop/electron/workstation-browser-runtime.ts` owns BrowserTask; `workstation/control_plane/` owns policy/certificates; `workstation/task_compiler.py` owns plan dispatch; `workstation/operational_capabilities.py` owns durable operational registry; `workstation/artifacts.py` and `workstation/journal.py` own evidence; `workstation/experience_compiler/` owns candidate validation/replay/promotion.
- Discovery is read-only; installed ≠ healthy ≠ authorized. No new authority/store, arbitrary privileged JS, hidden installs, cross-profile network/FS writes or silent retry.
- CW-03A independent of Remotion produces editable source and decodable PNG with dimensions/hash/readback; CW-03B proves ffprobe metadata and MP4; CW-04 Penpot proves human-agent-human revision preservation; CW-05 Three.js proves typed scene mutations, GLB, reopen, undo.
- `SOURCE_MATRIX.md` retains external-license/source policy. Penpot core/MPL and AI Kit/CC-BY are distinct; FFmpeg build/codec license depends on binary; Remotion eligibility and embedding/redistribution remain unapproved. A pinned source and license review are **not** engine qualification.
- Laya D-038/D-039 remains non-authoritative for effects and promotion: owner authority, verified receipts, validated replay, drift and calibrated promotion remain mandatory.

## 5. Recording/PR discipline

For each lane: baseline SHA + selected upstream pin + affected owner/seam + hypothesis/falsifier + actual commands + result (PASS/FAIL/NOT_RUN) + exact-head Actions links + negative proof + rollback + PR/commit. Maintain `workstation/ROADMAP.md` (priority), `workstation/context/CURRENT_STATE.md` (present facts vs historical), `workstation/context/engineering-journal/CURRENT.md` (execution evidence), `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` (strategic rationale) and `workstation/context/DECISIONS.md` (accepted constraints). Keep historical receipts; no retrospective relabelling. `main` remains untouched until the maintainer decides to merge.

**First runnable action for the next agent:** R1 CI profile parity corrective PR; not a repeat CW-01 audit and not direct CW-02 coding.
