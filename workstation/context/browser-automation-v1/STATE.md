# BAV State — 2026-10-12

## Errata de estado — 2026-10-18 (não apagar histórico de 12/10)
Consulta GitHub posterior comprova que [PR #85](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/85) foi **MERGED** em `main` em **2026-10-13**, merge SHA `7b9392466e854be70777f7f67a3ed581b62404dd`. As frases de 12/10 `DRAFT/unmerged` são um *snapshot histórico do momento*, não o estado atual. O merge incorporou provas/fixtures experimentais e documentação, **não** qualificou Browser Automation V1 em produto. BAV04 testou perda de worker Python na mesma BrowserTask com admissão sintética; crash do processo Electron, remint de TaskRun/lease autenticado, Trello live, CI exact-head e H-079/H-081/H-082 permanecem pendentes. D-049: [novo plano de fechamento](../BROWSER_REFINEMENT_2026-10-18.md).

Repository: C:\Github\hermes-agent; original checkout dirty (~34 modified tracked files), untouched.
Branch: feat/hermes-browser-automation-v1-20261012
Worktree: C:\Github\hermes-agent\.worktrees\browser-automation-v1-20261012
Base: origin/main a2b56db1bc9e0b5acf48d94fa86a9844a1005842. Read actual HEAD with git rev-parse HEAD after commits.
GitHub PR #82: OPEN DRAFT unmerged, head f552c96b782d5e7570bf841bd0e9694a9206c618 last checked, keep independent.
Parallel worktree: .worktrees/playwright-c2c-impl-20261012 at 246477e4c0 with its own uncommitted documentation; do not alter or cherry-pick wholesale.
Scope: Only test-only Electron runners/JSON fixture and documentation changed. H-079 required upstream qualified baseline remains HOLD; separate local-dev authorization from Playwright C2C branch does not constitute release waiver here. No production Browser runtime code changed.
Evidence: BAV01 Playwright CDP connects to WebContentsView on localhost and clicks; 1 effect. BAV03 authenticated native controller singleton executes two fixture parameter sets (Alpha/Beta), 2 server-confirmed effects, 12 controller calls, 0 LLM calls in harness. BAV05 deliberately invalid refs recovered via testid. Real ProceduralMemory integration not done.
Scratch logs: .bav*.log untracked; preserve, never stage. H-079/H-081/H-082/exact-head CI not qualified.
Read PLAN/STATE/EVIDENCE/DECISIONS/REFERENCE_MATRIX/METRICS/NEXT_PROMPT at start of next session.

## Continuation checkpoint — 2026-10-12
The experimental controller harness was extended (not production runtime). New files: apps/desktop/electron/workstation-browser-bav1-memory.worker.py and workstation-browser-bav1-persistence.contract.test.cjs. Existing controller.runner.cjs now supports BAV_PERSISTENCE_TEST=1. RED confirmed missing persistence marker, then GREEN in isolated Electron under same 'bav-run' authorized owner. A deliberately mismatched run_id was rejected with HTTP 400 CAPABILITY_MISSING; do NOT turn off admission. Replayed procedure is local fixture-only; no cross-run authority, live Trello, product integration, Playwright production CDP, or release qualification.

## Publicação — 2026-10-12
PR #85 DRAFT: https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/85; commit principal d1d867a3a22fa6e77a45000992f54784c71954f2. GitHub HEAD sem combined statuses e sem PR workflow runs na checagem; CI exact-head NÃO qualificado. Leia git rev-parse HEAD para o último SHA, pois o checkpoint documental pode ter commit posterior.

## Continuation state — 2026-10-12 BAV04
- Code-only commit: 5448f889fe94af43c0534b26a0243364be1a078e, branch feat/hermes-browser-automation-v1-20261012, PR #85 Draft (verify final HEAD after documentation commit).
- Changed test-only apps/desktop/electron/workstation-browser-bav1-memory.worker.py and controller.runner.cjs, plus new workstation-browser-bav1-recovery.contract.test.cjs, workstation/tests/bav04_experimental_recovery.py and test_bav04_experimental_recovery.py. No production modules modified.
- Python crash worker dies os._exit(37) after effect but before evidence checkpoint. Existing append-only ExecutionJournal boundary:'acceptance' survives, and a new Python worker consults independent snapshot + server counter before producing an ArtifactStore resume_ref and using the canonical DeterministicRoutineRunner to skip the click.
- Full product restart/TaskRun remint/real lease revocation/CI exact-head remain unverified. The fixture admission map is synthetic and explicitly NOT an authority token.
- Local statuses: tracked changes were committed; scratch .bav*.log untracked and preserved, not staged. Current exact HEAD must be re-read.
