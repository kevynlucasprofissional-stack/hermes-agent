# 2026-10-10 — D-043 engine-neutral Creative Workstation design decision

**Classification:** SOURCE-ANALYSIS / ARCHITECTURE ACCEPTED BY USER / DOCUMENTATION-ONLY. No code, native GUI, third-party installation or CI gates were run by this documentation update.

## Trigger and evidence
- Attached transcript `ChatGPT-Comparar Opções De Motion-20261010-1444.md` consolidates user discussion on direct Canvas/SVG freeform motion, HyperFrames, EffectCraft and OpenReel.
- Latest explicit user correction: HyperFrames was first candidate only; do **not** privileged-lock the Creative Workstation to it. UI may intentionally differ from legacy editors.
- EffectCraft repo `storytold/effectcraft`: common command registry, atomic `engine.batch`, JSON document, property tree, Graph Editor and branching history. Its early maturity and parity estimates do not certify production use.
- OpenReel repo `Augani/openreel-video`: shared NLE action surface, editing host, typed timeline edits and AI/MCP/headless entry points. Static risks to test: multitrack ripple/audio link, altered speed cut mapping, multi-owner history and partial turn result. Findings are audit hypotheses, not test-proven defects in Hermes.
- HyperFrames `heygen-com/hyperframes`: seekable HTML/Canvas/Three.js and GPU completion pathway exist; existing implementation is a candidate adapter. No forced default engine.
- Observed GitHub `main@f21e803b` (2026-10-10). PRs #57..#61 are open creative draft chain, PR #62 is HyperFrames-first D-041 draft, PR #63 dogfood D-042 draft. Both are unmerged in observed status. Their contribution must be reconciled before any merge.

## Decision / falsifiers
- D-043 supersedes D-041 **only** on engine-first choice and target UI/project authority, not on security or existing owned assets; preserve #62 as historical evidence, do not merge its superseded mandate.
- Prioritize single Creative Document with exact time and stable IDs, a transactional typed command bus shared between GUI/AI/headless, accurate NLE cuts, Semantic Edit Plan revision previews, freeform adapters, engine-neutral render parity, contextual UX and verified reuse.
- Falsify architecture if a human edit and agent edit diverge in serialized result, speed/ripple breaks A/V sync, unknown revision overwrites manual work, arbitrary seek changes output, untrusted source runs with Electron privilege, or preview/export materially differs.
- D-038/D-039/D-042, upstream-first H-079, exact-head CI, permissions, TaskRun/Browser/ArtifactStore/Experience Compiler owners remain. No alternative authority planes.
- Revisit backend selection only against performance, fidelity, license, full-cost and failure test data.

## Next experiment
CWN-00 source/CI/PR reconciliation, then CWN-01 document+time map, CWN-02 command equivalence and Undo, CWN-03 linked A/V, CWN-04 plan preview and CWN-05+ preview/export parity. Keep development-only status while release gates red. See `workstation/creative-workstation/ENGINE_NEUTRAL_IMPLEMENTER_HANDOFF_2026-10-10.md` for exact staged handoff.
