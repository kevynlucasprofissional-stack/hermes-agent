# Single high-value Anthropic session — execution runbook

## Phase A — preparation (US$0 Anthropic)
1. On read-only clone/worktree record `git rev-parse HEAD`, `git status --porcelain`, `git ls-files`, default branch and PR/open gate state. Avoid altering user checkout.
2. Produce full file manifest + module/test/owner DAG, all canonical doc reconciliations and selected Source Matrix audits; assign evidence `FACT / INFERRED / PARTIAL / NOT_REVIEWED`.
3. With Codex/Antigravity/Nemotron, implement/verify cheaper baseline fixes in separate PRs where authorized (R1 already has PR #54). Never consume paid frontier tokens to make `npm ci` work or list files.
4. Validate H-079, CI, Electron, P0 voice, license and required test gates. Runtime creative work remains BLOCKED if required gates red.
5. Use cheap-model adversarial review of each candidate and each packet. Ask: missing signature? owner duplication? unverified assumptions? diff too wide? tests falsify success? safe rollback? E2E actually executable?
6. Freeze a short, ordered packet queue with SHA and exact owners, budgets and fallback strategy; user authorizes when ready.

## Phase B — startup (no paid call until passes)
- Inspect Anthropic Console credit balance **and expiration**, model availability, API workspace billing and request limits. Configure external capped usage if possible; do not rely on alert alone.
- Confirm exact working HEAD/gates/branch and that no PR has already solved the work. A packet with changed hash is STALE and cannot run.
- Start cost ledger; reserve US$10; threshold alert at US$60 and hard stop at US$80 pending deliberate reserve release.
- Prefer Opus for first frontier patch. Use Fable only for a previously evidenced hard bottleneck, never for first-pass code navigation.

## Phase C — per-packet microcycle
1. Stage isolated branch/worktree. Present self-contained packet + minimum source excerpts, expected diff, non-goals, test commands and prohibitions.
2. Model performs limited **changed-file verification** and writes RED test(s) first. No broad search, no dependency changes or external source downloads without packet.
3. Produce minimal patch; run focused tests locally. If the local environment is unavailable, mark `NOT_RUN` (not PASS) and send for cheaper executor validation.
4. Independent reviewer checks change against authority/effect/tenant/revision/license invariants. Run negative tests, regressions, exact-head CI and real native/effect E2E where applicable.
5. Record actual usage and artifacts/CI SHA. If successful, seal packet as VERIFIED; if ambiguous, stop or recompile with cheap agent. Avoid paying repeated premium turns for missing context.
6. Leave small PR with rollback; never automatically merge into `main`.

## Phase D — stop criteria
- **Budget:** global spend >= US$80, unless reserve explicitly released; per-packet cap reached.
- **Evidence:** source signatures differ, unseen PR changes, no actual independent verifier, unknown authorization, stale prepared excerpts or fake/mocked-only outcome.
- **Safety:** unexpected user effect, scope/tenant mismatch, privileged code execution, surprise install/license, secret handling, mutation retry uncertainty.
- **Quality:** failing required gate/CI, inability to reproduce, huge diff with no test, unqualified release claim.
- **Scheduling:** packet dependency incomplete or upstream pin changed.

## Session exit deliverables
- A small stack of discrete PRs, source/diff SHAs and formal before/after behavior.
- Tests: executed commands + PASS/FAIL/NOT_RUN and exact-head CI URLs; real product/Electron receipts where required.
- Spending: actual model/request usage, cache costs and remaining credits.
- Backlog: cheap-agent follow-up work, P0/blocked cases, omitted ideas and rationale.
- Documentary sync proposal into ROADMAP/CURRENT_STATE/DECISIONS/engineering journal, subject to normal architecture governance.

**Rule:** avoid a single unreviewable multi-feature change. "One paid session" may execute multiple microcycles while the account meter tracks the whole session.
