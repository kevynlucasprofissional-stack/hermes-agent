# D-043 — Hermes Creative Workstation engine-neutral architecture (2026-10-10)

**Status: ARCHITECTURE DECISION; IMPLEMENTATION NOT QUALIFIED.** Owner: Workstation. Current baseline observed: `main@f21e803b`; verify when coding. This document **supersedes D-041/PR #62 HyperFrames-first as a tool-selection mandate**, but retains the existing HyperFrames installation, proofs, assets and reusable integration work. D-042/PR #63 dogfood acceptance and D-038/D-039, H-079, H-080, H-081/H-082 and permission/release gates remain in force. Neither this document nor the linked prompt authorizes merging a draft PR or installing external software.

## Product invariant

A user and Hermes act on the **same persisted Creative Document** with the **same typed commands**, whichever visual workspace or render backend is active. Switching from cuts to motion, design, 3D, transcription or scripting changes the view/available operations, not the document or product/browser ownership. The UI need not reproduce After Effects, Premiere, OpenReel or HyperFrames Studio. Favor context-aware panes, manual pinning and direct manipulation plus agent selection context.

HyperFrames, OpenReel, EffectCraft, Remotion, Penpot, Three.js and Rust/WebGPU are candidates/adapters/references, **not preselected universal owners**. Do not create a second Browser/SessionDB/TaskRun/verification/approval/Experience Compiler/asset authority. Renderers render; the Hermes Workstation owns task authority and provenance. Existing Electron/Chromium remains the user's browser surface.

## Reference findings (source research, not qualification)

- **EffectCraft** `storytold/effectcraft`: versioned JSON `.ecproj`; command registry shared by UI/CLI/MCP; `engine.batch` supports atomic grouped operations; keyframe Graph Editor and branching history. Reference: `docs/architecture.md`, `docs/agents.md`, `crates/engine/src/commands/batch.rs`, `crates/engine/src/history.rs`. Project is young; broad feature claims are not a parity benchmark. Rust/egui UI cannot be dropped into React as native components without a bridge; observe license/asset attribution.
- **OpenReel** `Augani/openreel-video`: `packages/core/src/actions/action-executor.ts` edits via `clip/split`, `clip/trim`, `clip/rippleDelete`, `clip/slip`, `clip/slide`, `clip/roll` etc; `packages/agent/src/host.ts` supplies `EditingHost`; editor/headless/AI share actions. `packages/agent/src/loop.ts` exposes approval, dry-run and interruption. Static analysis observed risks: same-track ripple, split with rate mapping, divided history, partial turn commit, huge tool registry; validate versions/tests before reusing code.
- **HyperFrames** `heygen-com/hyperframes`: HTML/SVG/Canvas/WebGL/Three.js can receive seek time (`hf-seek`); `packages/core/src/runtime/adapters/three.ts`, `typegpu.ts`; Studio/engine/producer offer real production infrastructure. Preserve as a qualified candidate, **not** the project's canonical scene schema by default.
- **AI-freeform**: direct SVG/Canvas/WebGL/Three.js/GSAP code often offers flexible authoring; arbitrary code is not automatically editable or seek-safe. Freeform must expose declared parameters or remain an opaque node with editable outer transforms.

Original conversation supplied as 2026-10-10 attachment `ChatGPT-Comparar Opções De Motion-20261010-1444.md`; recommendations are design proposals until tested.

## Layered design (logical, not permission to introduce replacement owners)

```text
Contextual Experience: NLE | Motion | Design | 3D | Transcript | Agent
            | same selection / semantic commands
Creative Document (versioned) + rational Time/Media Map + Asset refs
            | Command Registry + policy/owner gate
Transactional Creative Editing + Revision/History + Edit Plan
            | constrained, typed backend capability adapters
NLE/audio | SVG/Canvas | WebGL/3D | HyperFrames | other qualified engines
            | existing Chromium/user-preview, owned render workers
Existing Workstation TaskRun / verifier / artifacts / journal / Experience Compiler
```

### Creative Document v0 contract

* Immutable/stable IDs for project, composition, track, clip, layer, node, property, effect and asset; reference by ID, not array index or coordinate. Versioned schema; deterministic migration/read-only refusal for unknown incompatible future schemas; preserve unknown fields when safe.
* One save authority and per-project revision ID/ETag; immutable source/media identities, hashes and provenance; profile isolation. Native backend source may be retained as linked source; do not silently flatten editable content into images.
* Composition contains layer/clip graph, effects, parent-child relationships, masks, nested compositions, keyframe/property curves, media source/ranges, audio links and markers. Support `editable declared-parameters` versus `opaque procedural layer`.
* **Canonical time:** rational frame rates including 30000/1001; integer ticks/rational conversions; explicit half-open ranges and source↔timeline mapping. Separate display drop-frame timecode from sample rate. Reject NaN, zero/negative durations and overflow. Rate, reverse, freeze and speed-ramp operations must preserve source mapping, sync and frame identity.
* Changes occur exclusively through typed commands with actor identity, scope, expected document revision, idempotency key, inverse or snapshot and verifier receipts. UI gestures and AI/tool API invoke the same commands. Read-only introspection does not mutate state.
* Single journal/Undo/Redo for committed document mutations; reversible preview branches and optional durable branching later. No blind retry on unknown outcome; non-document external effects (generation/export) require separate receipts, cleanup and explicit non-rollback semantics.
* Reader and writer accept conflict (409-like revision mismatch), diagnose it and require rebase/approval; never silently overwrite manual edits.

### Editing commands and correctness

Initial verbs: `project.open/save`, `asset.import`, `track.add`, `clip.add/split/trim/rippleDelete/slip/slide/roll/setSpeed`, `layer.create/move/setProperty`, `keyframe.set/remove`, `history.undo/redo`, `editPlan.preview/apply/reject`, `render.snapshot/export`. Define JSON schemas and capabilities with explicit denial reasons. A compound command is atomic: validate -> stage copy-on-write -> calculate derived sync/media effects -> verify -> commit exactly once; failure leaves original revision intact. Preserve linked audio, track locks, ripple scope, overlaps/transitions, mixed rate, boundaries and modified speed.

### Semantic Edit Plan

Typed plan fields: `planId`, `baseRevision`, `intent`, `targetIds`, `commands`, `readSet/writeSet`, `preconditions`, `predictedDiff`, `previewRevision`, `validation`, `state`, `provenance`. States: `PROPOSED -> PREVIEWED -> VALIDATED -> APPLIED` or `REJECTED/BLOCKED/PARTIAL/ROLLED_BACK`; partial status never claims DONE. Preview must render a separate revision, **not** claim a no-op dry-run as visual evidence. Support selective acceptance with conflict/re-evaluation; avoid auto-merging conflicting edits and preserve original manual state.

### Adapter/render contract

Capability discovery by outputs, project/seek support, accepted media, isolation, performance, license and evidence—not popularity. Typed `prepare`, `seek(frame)`, `ready`, `snapshot`, `render`, `cancel`, `dispose`, with scoped authority, timeouts and receipts. Seek arbitrary frames out of order. Seed procedural randomness, await fonts/media/GPU completion, ban wall-clock state in render-critical paths. Compare player frame with decoded export; characterize fidelity, CPU/GPU resources, license, cross-profile isolation and failure recovery. Preserve HyperFrames existing `hf-seek` support as adapter when useful. Do not embed arbitrary LLM-supplied JS in privileged Electron origin.

### UX and learning

Start with project/preview/trim/timeline/inspector and contextual agent selection; progressive workspaces can expose Graph Editor, design canvas, scene navigator, transcription, code and render queue. Human can lock/pin panels. Every gesture maps to typed command; no requirement to mimic an Adobe interface. Existing Experience Compiler may mine **verified creative operations only** after stable commands and real positive/negative tests; no parallel skills/registries and no global promotion from simulated or unverified trials.

## Executable priority order (CWN labels do not rename historical CW-01..CW-07)

| Phase | Scope | Exit condition |
| --- | --- | --- |
| CWN-00 | Recover PRs #57..#63, local work, baseline/CI/security/license/D-042; salvage-by-symbol | factual GO_FOR_DEVELOPMENT / BLOCKED_FOR_PROMOTION with receipts |
| CWN-01 | Creative Document + exact time/media map and migration | round-trip/reopen and 29.97/60fps/rate/reverse tests |
| CWN-02 | Command Registry, owner fencing, transactional history | UI/headless same mutation, atomic failure, undo/readback |
| CWN-03 | NLE primitives and linked A/V correctness | split/trim/ripple/slip/slide/roll; multitrack sync and locks |
| CWN-04 | Semantic Edit Plan/revision preview/selective acceptance | conflicting human changes preserved; approve/reject/rollback |
| CWN-05 | Freeform SVG/Canvas/Three.js editable adapters | arbitrary seek/declared params/reopen/isolated code |
| CWN-06 | Render parity/backends and real export | decoded frame+audio validation, cancellation and provenance |
| CWN-07 | Responsive adaptive UI, Graph Editor and keyframes | same edit via mouse/AI; workspace pins; automated user journey |
| CWN-08 | Experience Compiler verified creative procedures | cross-run verified reuse, no unverified promotion |
| CWN-09 | Advanced effects, specialized backends, performance | selected from measured gaps and licensing/sandbox proof |

**Cross-phase:** minimal early vertical/experiments should probe Canvas/HTML/3D and native export before freezing architecture, but do not change phase dependencies or claim product acceptance from a mock.

## Implementation / qualification policy

1. Read `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md` and H-079; preserve clean/dirty user checkout. Do not auto-install engines, change main or merge drafts.
2. Inventory actual PRs #57–#63 and distinguish historical branch evidence from merged runtime. PR #62 is **D-041 superseded for engine authority**, not a safe merge candidate without reconciliation. PR #63 D-042 dogfood constraints must remain intact.
3. Use existing Workstation/browser/process/TaskRun/verification/ArtifactStore/Experience Compiler owners. Introduce minimal domain modules under existing Creative subsystem only if owners lack them; do not create a second sovereign process, browser, database or verifier.
4. One vertical tested behavior per PR, RED test -> minimal implementation -> adversarial/real tests -> exact-HEAD CI -> journal+state and rollback. P0 security/permission red blocks release; development-only exceptions must be stated, never assumed.
5. Measure implementation truth: NOT_IMPLEMENTED / DESIGN_ONLY / LOCAL_TESTED / REAL_E2E / EXACT_HEAD_CI / QUALIFIED. No claim of successful preview/export without real media readback.

## Cross-references

- [Implementation prompt](ENGINE_NEUTRAL_IMPLEMENTER_HANDOFF_2026-10-10.md)
- [Verification matrix](VERIFICATION_MATRIX.md)
- [D-043 journal](../context/engineering-journal/creative-engine-neutral-2026-10-10.md)
- [D-041 pending draft](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/62)
- [D-042 dogfood draft](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/63)
