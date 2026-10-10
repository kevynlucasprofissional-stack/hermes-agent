# EXECUTE — Hermes CW engine-neutral human+AI workstation (D-043, 2026-10-10)

**Authority:** `workstation/context/DECISIONS.md` D-043, `workstation/ROADMAP.md`, [architecture](ENGINE_NEUTRAL_ARCHITECTURE_2026-10-10.md), `workstation/creative-workstation/VERIFICATION_MATRIX.md`. **Status: implementation request only; no runtime is hereby qualified.**

## Mission — do not redesign it

Implement in order **CWN-00 through CWN-09**, preserving the already-built Hermes Workstation and existing creative proofs. Deliver a SINGLE editable Creative Document and command surface controlled by human gestures, Hermes AI, headless/automation and contextual workspaces. Keep backend choice neutral: HyperFrames, OpenReel, EffectCraft, Remotion, Three.js and Penpot are references/adapters, not mandatory primary products. Never turn the CW into three unrelated apps or a rigid After Effects clone. Maintain source editability, exact time, security, provenance, user revisions and frame-accurate export.

**Repo**: `kevynlucasprofissional-stack/hermes-agent`. **Observed main** `f21e803b3525b70ee6be2305e579c1cc1f930e74` on 2026-10-10; **reverify**. Existing creative drafts (not merged): PR #57 Stage A; #58 `creative_apps.py/creative_process.py/creative_runtime.py`; #59 `creative_project_store.py/creative_project_runtime.py/creative_render.py/creative_media.py` and Electron `workstation-creative-frame.ts`; #60 `creative_video*.py`; #61 `creative_remotion_source.py`; #62 D-041 HyperFrames-first docs **SUPERSEDED FOR ARCHITECTURE**; #63 D-042 dogfood, **keep gates**. Review PR chains/CI exactly, salvage symbol by symbol; none is qualified merely for existing. Preserve any local uncommitted work (GitHub cannot show it). Do not merge to main.

## 0. Required bounded preflight (CWN-00)

Read only mandatory rules and this handoff before coding: root `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md`, `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `workstation/creative-workstation/AGENTS.md`, `workstation/context/DECISIONS.md` D-038..D-043, this specification; for dogfood inspect PR #63 gate. Do NOT reread thousands of old journal lines or rediscover the architectural decision. Inspect current HEAD, worktrees, user modifications, upstream pin, license/deps, PR #57–#63 CI. Run canonical H-079 gate, never bypass sandbox/permissions/TaskRun/BrowserTask/profile/authorization or exact-head CI. Produce `CWN_BASELINE.md` in reviewable branch: baseline SHA/pins, owners and source paths, existing/tested/missing matrix, PR salvage map, red blockers and next test. If release is blocked but bounded isolated development is authorized under existing policy, keep coding with explicit `DEVELOPMENT_ONLY` status; stop deployment/promotion, not all safe experimentation.

Existing owners to inspect **before creating any new module**:
- `workstation/creative_apps.py`, `creative_process.py`, `creative_runtime.py` (PR #58).
- `workstation/creative_project_store.py`, `creative_project_runtime.py`, `creative_render.py`, `creative_media.py`, `creative_video*.py` (#59/#60), `creative_remotion_source.py` (#61).
- `apps/desktop/electron/workstation-creative-frame.ts` (#59), `apps/desktop/electron/workstation-browser-runtime.ts`, current renderer/webview, `apps/desktop/src/app/`, `apps/desktop/e2e/`.
- Existing Workstation ProcessRegistry/AppResolver/ScopedPolicyEngine, BrowserTask/session owner, TaskRun, ArtifactStore, journal, security/admission and Experience Compiler. Verify actual symbol definitions on the target branch before editing; if a candidate file exists only in a draft, label it as such. Do not replace a proven owner.

## 1. CWN-01 — Creative Document and canonical time (FIRST CODE FOUNDATION)

Extend current `creative_project_store.py` / `creative_project_runtime.py` when available, otherwise add minimal owned `workstation/creative_document.py` and `workstation/creative_time.py` plus tests in `workstation/tests/test_creative_document.py`, `test_creative_time.py` (adapt to repository test layout). Versioned project schema with stable IDs, compositions, tracks/clips, layers, properties, graph edges, media, source references/hash, source offsets, keys and assets. Implement canonical rational fps/tick + half-open intervals and source-to-timeline map handling 30000/1001, 60 fps, 2x speed, reverse, freeze and speed ramps. Schema validation, roundtrip reopen, migration, conflict and incompatible future version behavior. No arbitrary binary blobs in project JSON; no silent conversion of editable layers to flattened PNGs. Scope owner to Workstation existing profile/project data.

**RED/DoD:** seek/map near cut boundaries matches source frames; 29.97 vs timecode; split 2s at 2x maps to correct source; no NaN/overflow/negative duration; reopen loses no IDs/assets; wrong owner denied; conflicting revision rejected.

## 2. CWN-02 — Command Registry and atomic history

Implement narrow typed commands, initially `project.open/save`, `asset.import`, `track.add`, `clip.add`, `layer.create/move/setProperty`, `keyframe.set/remove`, `history.undo/redo`. Prefer extending existing action/project store, otherwise minimal `workstation/creative_commands.py` + `creative_transactions.py` (tests matching modules). Frontend interactions and Hermes/typed tool bridge must call SAME reducer/command schema and owner checks. Include actor/task, expectedRevision, scope, idempotencyKey, conflict, dry-run preview as actual copied project, validation and inverse/snapshot. Atomic batches commit once; failure no mutation, timeout no blind retry; one durable project history owner, no duplicate DB or CLI state. Tool schema discovery is bounded: expose relevant capabilities, not 300 tools in every prompt.

**RED/DoD:** mouse and agent equivalent serialized mutation; compound 4-step command fault at step 3 leaves exact old state; undo/redo recovers byte-equivalent document; revision mismatch rejects; canceled/restarted command cannot silently double-apply.

## 3. CWN-03 — NLE cutting primitives with linked A/V

Implement `clip.split/trim/rippleDelete/slip/slide/roll/setSpeed` through same command layer, adding `workstation/creative_timeline.py` only if no existing owner. Retain source ranges and precise time mapping, with track locks, linked audio, sync locks, edge constraints, transitions, multi-track ripple scope and per-asset provenance. Use OpenReel `packages/core/src/actions/action-executor.ts` as algorithmic reference, NOT blindly copied truth: audit same-track ripple, split at altered rate and history fragmentation. UI timeline manipulation must invoke these command IDs; typed tools must do the identical operation.

**RED/DoD:** cut at first/last legal frame; 29.97/60; 200%/reverse/variable-rate; linked A/V not desynced; locked track never shifts; ripple correct scope, no negative media position/overlap; canonical undo and cancellation.

## 4. CWN-04 — Semantic Edit Plan + reversible preview

Implement `workstation/creative_edit_plan.py` if needed. Plan fields `planId`, `baseRevision`, `targetIds`, `commands`, read/write sets, predictedDiff, previewRevision, diagnostics, provenance. States `PROPOSED/PREVIEWED/VALIDATED/APPLIED/REJECTED/BLOCKED/PARTIAL/ROLLED_BACK`; partial never DONE. Run proposed edits against isolated copy-on-write revision; render TRUE preview; let user select/reject subsets with dependency checks, only then commit as a single transaction. Respect manual edits made after plan creation; rebase or reject conflict, never overwrite. External AI media-generation/export is a separate effect with receipts and cancellation cleanup.

**RED/DoD:** proposal preview does not modify user document; accept subset and rerender; conflict after manual edit denied or resolved explicitly; cancel restores original; missing external artifact is not classified as applied.

## 5. CWN-05 — freeform authoring without engine lock

Implement declarative scene capability adapters for SVG/HTML/Canvas 2D/WebGL/Three.js, using existing `creative_render.py` / Electron Creative surface and existing HyperFrames `hf-seek` when useful. A node exposes `prepare`, `renderAt(frame/time)`, `ready`, `dispose`, parameter schema, source asset refs. Seek must be deterministic independent of frame order; fixed seed; asynchronous fonts/media/GPU readiness barriers. Expose text/color/transform/keyframe/parameters for editable layers; mark opaque procedural internals honestly. Run user/AI JS in isolated render origin/process, restricted files/network and bounded resources; never in privileged Electron origin.

**RED/DoD:** same project has editable SVG title + Canvas effect + Three.js object + video/audio, with arbitrary frame seek, save/reopen, parameter-only modification and zero cross-profile leakage. If 3D dependency unavailable, isolate as BLOCKED, retain prior phases and continue a 2D vertical.

## 6. CWN-06 — rendering engines/real export

Extend `creative_render.py`, `creative_video*.py` and owned process/FFmpeg flow only where already qualified. Define typed adapter `prepare/seek/snapshot/render/cancel/dispose` and capability table for installed HyperFrames, headless Chromium, FFmpeg/WebCodecs, optional native engines. No universal backend by decree. Pin and license-audit dependencies; never auto-install. Compare preview stills with independently decoded output frames; audio silence/offset/duration, frame count, dimensions, codec, hash, cancellations, timed media, GPU fallback and error quarantine. Preserve original native sources and machine-readable receipts.

**RED/DoD:** 10–15s vertical with real AV source exports MP4 (plus supported still sequence), reimports/decodes correctly and validates representative frames including last-before-cut/first-after-cut; no orphan process after canceled render.

## 7. CWN-07 — contextual UI / Graph Editor

In existing `apps/desktop/src/app/` and its Creative entry, implement **progressive** workspaces: montage/timeline, motion/easing, design/shape, 3D and transcript views over SAME document; users can pin panels. Prioritize practical Project/preview/timeline/inspector/agent selection, not a traditional clone or autonomous UI expansion. Graph Editor supports property keyframe handles, velocity/value and command-based selection. Selected IDs/time/media and owner bounds become agent context; ask "smooth this ease" and operate exactly those keys. Reuse existing desktop Browser/WebContentsView and React; do not embed unrelated privileged standalone windows.

**RED/DoD:** user splits/keys/moves object, Hermes adjusts, user undoes one semantic operation, closes/reopens project and exports; screens/interaction E2E verified (not a mock).

## 8. CWN-08 — verified creative reuse

Only once real editor commands and validators exist, connect successful repeated procedures to existing `workstation/experience_compiler/`, lifecycle/run-local adoption and TaskRun evidence. Example: detect silence -> generate candidate cuts -> preview -> verify linked sync -> apply with user approval. Compiler may store **verified typed semantic transitions**, never raw gestures, prompt-only claims, uncertified effects or a new capabilities registry. Preserve D-038 safety, D-039 safe opportunity mining and D-042 dogfood acceptance. Measure tool calls and System-2 steps saved against instrumented baseline, not estimates.

## 9. CWN-09 — advanced plugins and performance

Evaluate EffectCraft/MCP/Rust/WASM for useful effect/render adapters; OpenReel algorithms/UX; HyperFrames Studio parts; Remotion, Penpot/Graphite/Blender/Three.js as justified. Score each by user capability, performance, fidelity, license, sandbox boundary, maintenance and interchange. Optimize playback/render only after empirical benchmarks. Do not copy proprietary assets, ignore licenses or put speculative integrations before working product.

## Execution loop (mandatory for EACH PR)

1. Begin at CWN-00; identify exact code symbols and tests. Follow `AGENTS.md` and H-079 owner/upstream-first rules. Preserve local uncommitted changes. Never merge, reset or clean worktrees without inspection.
2. RED test tied to observable real behavior + negative owner/safety test -> minimal implementation -> focused GREEN tests -> affected regressions -> real GUI/headless E2E when relevant -> exact SHA CI -> drift recheck. Record real results only; report missing execution as NOT_RUN/BLOCKED.
3. Branch/PR per vertical or coherent slice, never mega-merge. Don't rewrite Hermes upstream, duplicate BrowserTask/TaskRun/SessionDB/ArtifactStore/approvals/verifier/Experience Compiler. No external download/installation without permission. User-owned projects/creations must survive error and restart.
4. Update `workstation/ROADMAP.md`, `workstation/context/{CURRENT_STATE,DECISIONS,HERMES_WORKSTATION_INTELLIGENCE}.md`, `workstation/context/engineering-journal/CURRENT.md` plus new immutable experiment logs and verification matrix by each real milestone. Do not mark D-043 implemented by writing documentation.
5. Continue automatically through allowed stages; when blocked by safety/permission/CI, mark `BLOCKED_FOR_PROMOTION`, give exact unblock criteria and perform independent read-only/development work that remains allowed. Do not invent qualification, skip failing tests or merge main.
6. For each completed slice report PR URL, exact SHA, file/owner map, tests (command/result), real artifact/preview evidence, negative cases, current gates, regression impact, rollback plan and next immediately actionable step.

**Start now with CWN-00 and CWN-01. Do not stop after writing another architectural proposal.**
