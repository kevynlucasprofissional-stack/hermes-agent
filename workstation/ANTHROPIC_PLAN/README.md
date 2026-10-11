# ANTHROPIC_PLAN — Hermes Work | preparation before paid frontier session

**Status:** PHASE 0 — evidence intake / not ready for Anthropic spending. **Date:** 2026-10-08. **Baseline observed:** `main@f21e803b3525b70ee6be2305e579c1cc1f930e74`.
**Scope:** documentation and evidence planning only. No runtime changes, paid Anthropic invocation, third-party install, merge, or claim of E2E qualification.

## Goal
Use up to **US$90 of Anthropic API promotional credits** to buy irreplaceable reasoning and high-coupling implementation, NOT repository navigation, dependency setup, low-risk fixes, retries, generic explanations, or uncontrolled large-context ingestion. Unspent credit is preferable to unverifiable code or artificial token consumption.

## Non-negotiable architecture
Preserve Hermes upstream and Workstation canonical owners: Session/TaskRun, BrowserTask/Electron Chromium, TaskCompiler, Control Plane Router/Policy/Verifier, RunClosureProof, ArtifactStore/Journal, OperationalCapabilityRegistry, Experience Compiler and System-1/Laya as **non-authoritative decision support**. No invented proof/authority, no second database/registry/runtime, no hidden consent or installation, no unverified mutation. Keep source-editable projects + verifiable effects.

## Strategy
1. **FREE PREPARATION**: systematically inventory and inspect first-party code/tests/docs and external Source Matrix references; map dependencies, symbols, tests, risks, versioned refs, proven gaps. Codex/Antigravity/Nemotron may do this; mark actual evidence separately from hypotheses. Preparation agents are allowed to read everything; do not send bulk repository context to Anthropic.
2. **RECONCILIATION**: apply H-079 one-pin upstream gate, read current CI and conflicts, distinguish `main` from open PRs; avoid duplicate work. Security/P0 and exact-head CI are hard release gates.
3. **FRONTIER SELECTION**: rank high-coupling architecture and verified cross-cutting verticals by expected lift of premium model vs cheaper alternatives. Small individual fixes are delegated elsewhere. Read [CANDIDATES.md](CANDIDATES.md).
4. **CONTEXT COMPILATION**: one actionable packet per intervention, with immutable SHA, precise code owner, narrowed source excerpts/contracts, actual tests, expected diff, no-go zones, negative controls, stop conditions and rollback. See [PACKETS.md](PACKETS.md).
5. **ONE CONTROLLED SESSION**: cost meter + per-task stop conditions + independent tests/review. Use Opus first and Fable only for demonstrably harder residual problems. See [BUDGET.md](BUDGET.md) and [SESSION_RUNBOOK.md](SESSION_RUNBOOK.md).

## Special constraint: do not require the frontier model to discover the repository
Packets must be self-sufficient enough to begin implementation immediately. **Do not categorically prohibit checking changed source files**: a model must validate live signatures, dependency contracts and current hashes before committing to avoid unsafe/stale edits. Allow at most strictly scoped changed-file verification, not an exploratory read of the whole repository. Otherwise stop and send the missing evidence back to the cheap preparation lane.

## Ready-to-spend gate — all required
- [ ] Full recursive tracked-file inventory + first-party module/test mapping is recorded (exclude binary/vendor assets from semantic source reading, still inventory provenance/license).
- [ ] Required canonical context and latest branch/PR reconciliation complete.
- [ ] Source Matrix references triaged by relevance, license and pinned SHA; full code-to-code review of **selected** references, not indiscriminate cloning/reading of all projects.
- [ ] Known P0 release blockers and H-079 baseline disposition recorded; no silent waiver.
- [ ] Every selected packet has exact owner, existing signatures/contracts, positive and negative tests, expected E2E/rollback.
- [ ] Model access, startup credits/expiration and current API balance verified in Anthropic Console; spending ceiling and alerts set.
- [ ] Dry-run packets executed with a cheaper model; failures/ambiguities eliminated.
- [ ] Budget and exact stop rule approved by user before consuming credit.

## Canonical precedence
`AGENTS.md` → `workstation/AGENTS.md` → `workstation/context/README.md` → H-079 → `workstation/ROADMAP.md` / `context/CURRENT_STATE.md` / `context/DECISIONS.md` / `SOURCE_MATRIX.md` → scoped implementation plan. This folder is a planning overlay, **not another source of architecture authority**.

## Files in this planning workspace
- [REPO_AUDIT.md](REPO_AUDIT.md): evidence inventory, file/code/source audit coverage and current known blockers.
- [INVENTORY_SNAPSHOT.md](INVENTORY_SNAPSHOT.md): verified Git-tree census of all 30 root directories (16,190 entries including root files); not semantic source reading.
- [CANDIDATES.md](CANDIDATES.md): ranked preliminary frontier work candidates, alternatives and dependencies.
- [PACKETS.md](PACKETS.md): reproducible context packet template and seed backlog.
- [BUDGET.md](BUDGET.md): observed pricing, cost controls and provisional allocation.
- [SESSION_RUNBOOK.md](SESSION_RUNBOOK.md): free-to-paid transition, execution, test and stop/rollback protocol.

**Explicitly not completed yet:** whole-repository semantic read, every Source Matrix upstream repository read, fresh local/CI tests, frontier pack validation, license clearance. Never infer completion from this bootstrap document.
