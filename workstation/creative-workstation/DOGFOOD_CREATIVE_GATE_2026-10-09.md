# Creative / HyperFrames — Dogfood native-product qualification (2026-10-09)

**Status: ACCEPTANCE SPECIFICATION ONLY; installed user-local HyperFrames runtime NOT inspected.** Companion to `../context/DOGFOOD_PRODUCT_GATE_2026-10-09.md` and draft PR #62 D-041. This does not supersede upstream-first, creative source/engine safety or preserve-history rules.

## First step is evidence recovery, NOT a clean install

The maintainer reports HyperFrames already integrated into a local Hermes Work instance, but the consulted GitHub main `f21e803b` and Creative draft PRs #57–#62 do not contain an auditable final implementation. In the authorized local checkout, inspect `git status`, branches, worktrees, staged/untracked source, commits, process startup and Desktop routing; preserve ALL uncommitted changes, do not clean/reset/checkout over them. Identify the real project source-of-truth, running HyperFrames version and pinned upstream SHA. If absent, report MISSING_CODE and request access; do not silently reimplement.

## Proof obligations

| ID | Native product check | Negative control / required evidence |
| --- | --- | --- |
| HC-01 | Open Studio inside the *existing* Hermes Electron/Chromium `WebContentsView` and TaskRun/BrowserTask | No external browser as substitute; restart, close/cancel, owner/lease, unique process |
| HC-02 | Human manually edits project; agent modifies exact same project with typed operations | ETag/If-Match conflict -> 409; never overwrite human concurrent edits |
| HC-03 | Save original editable HyperFrames HTML/CSS/JS + media and provenance manifest; close/reopen with source fidelity | Tamper/revision mismatch, path escape, symlink, unauthorized project and foreign session denied |
| HC-04 | Export genuine animated MP4, not still-loop; independent ffprobe decode and compare separated frames; also PNG frame | Failed frame or no motion must not pass. Bind source revision and resulting artifact hashes |
| HC-05 | Local sidecar auth / allowed loopback / ProcessRegistry resource and cancellation control; no Framey cloud requirement | Cross-origin localhost attack, token leak, external access, dead process and stale link denied |
| HC-06 | Canonical `Session/TaskRun`, Approval/Policy, ArtifactStore, Journal, Verification and ExperienceCorpus observations | No new Creative authority/compilability database or pre-approved external effects |
| HC-07 | Same ExperienceCompiler can mine verified creative edit sequence and propose later replayable animation procedure | Only qualified/scoped effect executes; unverified or ambiguous composition stays candidate |
| HC-08 | Packaged Windows desktop E2E and restart under representative saved project; headless renderer process if genuinely required | Do not treat renderer child as second user-facing browser owner; no clean smoke-only release |

Potential predecessor owners: `workstation/creative_{apps,process,runtime}.py` PR #58; `creative_project_store.py`, `creative_project_runtime.py`, `creative_render.py`, `apps/desktop/electron/workstation-creative-frame.ts` PR #59; `creative_video*.py` PR #60 (still video only); `creative_remotion_source.py` PR #61 (optional, pause); source specification `HYPERFRAMES_ADOPTION_2026-10-09.md` exists on PR #62 branch and not necessarily on main. Read actual local files before selecting owners.

**Success is a runnable user's Work, not a package test:** human changes keyframe, agent changes another property via typed bridge, concurrent conflict is caught, edited source reopens, genuine animated output independently plays/decodes with distinct frames, and the normal Work learning pipeline records only VERIFIED transitions. If runtime not accessible, status remains BLOCKED_BY_LOCAL_CODE and this document records only the demanded test.
