# D-041 implementation specification — HyperFrames-first Hermes Creative Workstation
Date: 2026-10-09. **Decision accepted for architecture; implementation NOT qualified.**
Owner: Hermes Workstation. Canonical authority: [../ROADMAP.md](../ROADMAP.md), [../context/DECISIONS.md](../context/DECISIONS.md). Executable handoff: [HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md](HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md).

## 0. Decision, source and scope

**Decision:** adopt **self-hosted HyperFrames Studio** as the *single default creative UI* in the Hermes Workstation's existing Electron/Chromium surface. Use **OpenReel** (video NLE/trim/audio/clip UX) and **Diffusion Studio** (agent/code/visual bidirectional edits) as **references only**, never assumed drop-in dependencies. HyperFrames provides the editor and primary HTML/CSS/JS seekable-motion rendering workflow. Extend incrementally; do not build separate Penpot, Remotion and Three.js products as competing default editors.

This supersedes the *creative tool ranking and implementation order* recorded on 2026-10-08 (CW-03A/B/C, CW-04/05) but **does not annul** H-079 upstream-first, H-080 safety/Experience Compiler, H-081 CI, H-082 bootstrap, KI-024/025, permission, verification or release holds. Previous CW documents remain historical evidence. No prior PR may be merged simply because this decision exists.

Use one editable HyperFrames project (source HTML/CSS/JS, media/assets, tracks and compositional metadata) with a **thin Hermes provenance manifest** and canonical external artifact/journal references. Do **not** rush into a second universal scene document or a competing project database. An explicit adapter/compatibility and fidelity contract is required for any future imported non-HyperFrames project.

## 1. Verified source observations as of research on 2026-10-09

- HyperFrames upstream: https://github.com/heygen-com/hyperframes — Apache-2.0 at repository root; **candidate observed SHA** `6ae1af7470133db72de6d9bbceeaf80e85695c68`. A coding agent must recheck and pin one exact audited SHA (avoid floating `main`). Distribution also requires transitive dependency, font, media, FFmpeg and other license review.
- Studio: `packages/studio` (`@hyperframes/studio`, observed package version `0.8.143`); `src/index.ts` exposes `StudioApp`, `EditorShell`, `Timeline`, `NLEPreview`, `SourceEditor`, `PropertyPanel`, `LayersPanel`, `RenderQueue`, edit/history/DOM hooks. Verify API stability on the pinned commit. React 19, CodeMirror, Zustand, Studio Vite 6 dev; Hermes Desktop React 19, Electron 40 and Vite 8 at observed main. **Avoid bundling the monorepo or sharing build toolchains prematurely.**
- Studio server: `packages/studio-server/src/createStudioApi.ts` exposes API routes for projects/files/preview/render/media/history, with host adapter. Studio file writer: `packages/studio/src/hooks/useProjectFileWriter.ts` uses ETag, `If-Match`/`If-None-Match`, versioned reads and 409 conflict handling. These are candidate integration seams, **not evidence of Hermes authority**.
- CLI: `packages/cli` offers `preview`, `lint`, `doctor`, `render` and managed preview lifecycle. Node >=22 and FFmpeg noted in CLI docs; renderer may use a separate browser process. The **existing Electron renderer is the user-facing UI**; an owned *headless rendering subprocess* may be necessary and is not the same as launching another sovereign interactive browser or task owner.
- OpenReel: https://github.com/Augani/openreel-video — MIT repository listing; NLE inspiration, not approved code import.
- Diffusion Studio: https://github.com/diffusionstudio/editor — MPL-2.0 repository listing; code/agent/editor patterns only. Study per-file licenses before adaptation.
- Hermes main at analysis: `f21e803b3525b70ee6be2305e579c1cc1f930e74`. These are **observations**, not new test execution.

## 2. What exists, and what does not

| Item | Preserved candidate | Status / follow-up |
| --- | --- | --- |
| Baseline Stage A | Draft PR [#57](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/57) | Not baseline-qualified; do not merge |
| CW-02 scoped creative runtime | Draft [#58](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/58): `workstation/creative_{apps,process,runtime}.py` | Reuse app process/health authority after compatibility review |
| CW-03A editability/image | Draft [#59](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/59): `creative_project_store.py`, `creative_project_runtime.py`, `creative_render.py`, `apps/desktop/electron/workstation-creative-frame.ts`, `workstation-browser-runtime.ts` | Reuse revision, artifact, BrowserTask and image verification contracts; do not impose invitation JSON as universal project format |
| CW-03B video | Draft [#60](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/60): `creative_video*.py` | Reuse FFmpeg process/ffprobe controls; existing trial encoded a *still* PNG into MP4, not motion render |
| CW-03C Remotion | Draft [#61](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/61): `creative_remotion_source.py` | Preserve as optional historical adapter, **pause Remotion rendering/installation** |
| Native compositor capture repair | Reported uncommitted in Windows worktree `C:\Users\Kevyn Lucas\.codex\worktrees\creative-stage-a\hermes-agent`; branch reportedly `codex/creative-native-capture-20261008` | **Local-only reported state**; cannot be recovered from GitHub alone. Inspect the authorized local worktree before cleaning/checking out anything. If inaccessible, record unresolved without inventing recovery |
| HyperFrames/Hermes integration | No integrated E2E verified | NOT IMPLEMENTED; no claims of Studio installed/opening/working inside Hermes |

PR dependency chain: `#57(main) -> #58(#57) -> #59(#58) -> #60(#59) -> #61(#60)`. Preserve and selectively port code in small reviewable units. Do not merge the chain blindly. Upstream pin/release qualifications remain separate.

**CI diagnostic, not root cause assertion:** PR #61 HEAD `426f736d84293bf623956a783aac56614eced7d8` had a failed aggregate `desktop-typecheck` check although the individual Desktop TypeScript check succeeded. Its `workstation_smoke` qualification ran into a 1800s timeout and reported `ModuleNotFoundError: laya` in provenance tests. Investigate as a baseline/environment issue; do not claim Creative caused or fixed it. No exact-head production qualification.

## 3. Architecture to implement

```text
Hermes Workstation: Session / TaskRun / policy / agent / user
                         |
       existing BrowserTask / WebContentsView (human UI)
                         |
       HyperFrames Studio locally served on loopback
            |     |      |       |
         canvas timeline code  properties
                         |
              scoped Creative Bridge
        (typed operations, etags, revision/owner policy)
                         |
   existing ProcessRegistry, ExecutionJournal, ArtifactStore
                 |                  |
        HyperFrames CLI/engine   FFmpeg/ffprobe
                 |                  |
      source project + immutable output receipts
                         |
       independent verification -> Experience Compiler
```

**Do not** create a second session, Browser controller, privileged Electron renderer, TaskRun DB, ProcessRegistry, permission store, task router, independent compiler/verifier or global capability registry. The Studio's internal editor state is UI state only, not authority over execution. An owned local service is allowed; its HTTP presence is not a grant to change arbitrary files. No cloud or Framey prerequisite.

### Sidecar-first deployment contract
1. **Isolated pinned HyperFrames source/dependencies** in a documented workspace/managed install location; exact SHA, lockfile, artifact hashes, Node/Bun compatibility, package provenance. No floating `npx` pulls on normal startup; no automatic external binary downloads.
2. Reuse CW-02 `creative.enabled` and the existing AppResolver/ProcessRegistry/ScopedPolicyEngine/TaskRun admission. Define a **narrow typed** `hyperframes.studio` service adapter (discover -> approve/start -> readiness with actual UI/API readback -> bind -> stop -> crash/restart -> recovery), never arbitrary shell/argv exposure.
3. Bind localhost/127.0.0.1 only. Validate the real listener, negotiate occupied ports, enforce random per-session credentials and origin/CSRF controls at an audited host boundary, block arbitrary localhost websites and other browser tabs from using file APIs. Never log tokens, URLs with credentials, secrets or filesystem internals.
4. Open within an owned existing WebContentsView/BrowserTask; preserve user foreground, navigation/host ownership and cancellation. **Do not** create a parallel interactive browser or Electron window to bypass policy. UI & rendering processes may be distinct where required and remain owned.
5. Reuse source project files and existing Studio optimistic concurrency, then map changed-file revisions to Hermes hashes, journals and ArtifactStore. On 409, human edits win until explicit reconciliation; write timeout/partial success becomes `EFFECT_UNCERTAIN` with operation_id and **no blind retry**.
6. Prefer HyperFrames render/lint APIs with owned headless browser/FFmpeg execution; compare decoded PNG, MP4 codec/duration/dimensions/frame count/timing and project hashes independently. A successful HTTP response/exit code alone is not certification.
7. Keep install optional/explicit and all effects subject to scope, owner, effect budget and consent. Build/render scripts and user JS need an isolated sandbox; untrusted composition code MUST NOT run with Node integration or Electron privileged APIs.

## 4. Delivery plan — P0 to P6

| Stage | Action (reviewable PR) | Exit/evidence |
| --- | --- | --- |
| **P0 Recovery & baseline** | Refresh required context/H-079, inventory the draft chain, preserve Windows worktree, pin source, map owners/seams and classify CI failures. Upstream alignment remains an independently reviewed lane. | SHA matrix, recovery report, exact blockers. Documentation/preflight always permitted; **no unsafe runtime promotion** |
| **P1 Studio visible** | Isolated self-hosted HyperFrames service, Hermes scoped lifecycle, existing BrowserTask/WebContentsView placement, local auth, cancellation/restart | Actual Windows/Electron studio interaction, UI health, profile isolation, no orphan/unsafe port. **Milestone M1a** |
| **P2 Project persistence + export** | One native HTML/CSS/JS/media project, ETag conflict handling, immutable revisions, PNG/MP4 export via existing owned media/ArtifactStore | Create -> human edit -> save -> restart -> reopen -> render -> independent decode/readback |
| **P3 Hermes agent edits** | Typed read/list/inspect/select/create/update/reorder/keyframe/asset/render operations; revision/owner policy; no arbitrary privileged JS | User edit A -> agent edit B -> human edit C, all preserved, conflict/rollback/unsafe input negative tests. **Milestone M1b** |
| **P4 NLE/design extensions** | Gap-driven evaluation of built-in HyperFrames vs OpenReel/Diffusion patterns for trim, split, tracks/audio, vector/style control, masks/transitions | Each increment proven on same project, no new competing main editor |
| **P5 3D/advanced** | Three.js animation/GLB where justified; possible Blender/Penpot/Graphite specialist bridges later | Isolated adapter with typed transactions + verified outputs; not a P1 dependency |
| **P6 Verification/reuse** | Full suite/electron Windows E2E and exact-head CI plus Experience Compiler candidates after independent proof | No self-certification, real verifier/replay/calibration/reuse metrics, valid release gates before merge |

P0 and P1 **experimental work may proceed in separate isolated worktrees only under the already recorded 2026-10-08 development exception**; it does not waive required upstream-first preflight or authorize main merge, runtime privilege, auto-install, operational capability promotion or release. If a gate forbids a specific code change, record `BLOCKED` and continue independent documentation, tests and safe investigation without fabricating success. Deliver each stage in a separate draft PR. Do not stop after P0 when a permitted independent stage can proceed.

**M1 acceptance:** M1a = actual Studio under Hermes browser with owned lifecycle. M1b = editable composition manually + via agent, reopened, exported as PNG/MP4 and independently verified with negative authority/conflict/cancel cases. Neither mock-only tests nor a loopback health check qualifies.

## 5. Risk matrix / non-negotiables

- **H-079 / CI / Laya**: no qualified release baseline; publish exact failing step and restore test environment rather than disabling tests/raising timeout as a substitute.
- **Upstream/ref licensing**: Apache-2.0 root is not blanket licensing for all assets, fonts and dependencies; OpenReel MIT and Diffusion MPL-2.0 are *references* only; Remotion optional separate license.
- **Files and network**: profile boundary, path canonicalization + symlinks, traversal, CORS/Origin/CSRF and token lifecycle, arbitrary network access, media URLs, secret env and user JS sandbox.
- **Capture and export**: foreground/user state restoration; concurrent and late capture; renderer crash; headless child cancellation; deterministic seeks and frame-by-frame consistency.
- **Concurrency**: If-Match/409, human edits, stale task, external source drift, partial writes, restart and fail-closed reconciliation.
- **Agent and autonomy**: Laya/System-1 proposes only; no new authority, evidence fabrication or automatic Experience Compiler promotion.

## 6. Change locations and evidence outputs

Core review entry points:
- `workstation/creative_{apps,process,runtime}.py` (draft #58), `workstation/creative_project_{store,runtime}.py`, `workstation/creative_render.py`, `workstation/creative_media.py` (draft #59), `workstation/creative_video*.py` (draft #60).
- `apps/desktop/electron/workstation-browser-runtime.ts`, `apps/desktop/electron/workstation-creative-frame.ts` (draft #59); `apps/desktop/src/` existing application navigation; `workstation/browser/`, `workstation/browser_session.py`, `workstation/integrations/hermes/browser_controller.py`.
- `workstation/control_plane/`, `workstation/task_compiler.py`, `workstation/artifacts.py`, `workstation/journal.py`, `workstation/experience_compiler/` — use existing owners; verify current paths and signatures.
- HyperFrames `packages/studio/src/index.ts`, `packages/studio/src/hooks/useProjectFileWriter.ts`, `packages/studio-server/src/createStudioApi.ts`, `packages/cli/src/`.

One PR per substantial capability, with `workstation/creative-workstation/evidence/hyperframes-YYYYMMDD-<stage>/` for safely portable logs, sanitized receipts, hashes, sample projects/screenshots/output and actual test commands; **do not commit large generated videos or secrets**. Update journal/roadmap/status on every shipped PR. Specify baseline SHA, fork SHA, external SHA, CI URL and remaining blockers.

## 7. Required verification gates

`NOT_RUN -> UNIT_PASS -> INTEGRATION_PASS -> E2E_PASS -> QUALIFIED` must retain their semantics. See [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) (new P0–P6 section). Native Windows/Electron UI tests, real service stop/restart and task/profile denial tests are required. Do not relabel a build, docs, source package or still-image MP4 as a complete editor/render engine.

## 8. Historical documents and instruction precedence

This D-041 specification supersedes older **tool-selection and creative sequencing** paragraphs in `README.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `EXECUTION_BRIEF.md`, `PHASE_PROMPTS.md`, `IMPLEMENTER_PROMPT.md` and `INTEGRATIONS.md`; preserve them only for historical evaluation until deliberately migrated. More-specific canonical security and Workstation context instructions retain priority. Mandatory reading: repository `AGENTS.md` -> `workstation/AGENTS.md` -> `workstation/context/README.md` and its ordered references -> `creative-workstation/AGENTS.md` -> this spec/hand-off. No document here overrides agent safety or upstream gate.
