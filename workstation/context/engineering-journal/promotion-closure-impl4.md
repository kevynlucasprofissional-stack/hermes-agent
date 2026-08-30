# Implementation 4 — Promotion Closure

Date: 2026-08-30
PR: #9 — `feat(workstation): formalize BrowserTask lifecycle`
Status: **PROMOTED / RESOLVED**
Accepted PR head: `75d10d35d4757496390debf8e4b4f9efb44c5432`
Merge commit on `main`: `fada723f43613e5e0f061cab24445573ac298998`
Previous `main`: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`

## Windows baseline comparison

Controlled native-Windows side-by-side validation compared:

- baseline: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`
- candidate before attribution-only closure: `2ffee2335b6aba071e7b63457a047cd9334d4d92`

Result:

`WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`

Observed:
- baseline UI legacy: 5 failed files / 11 failed tests;
- candidate UI legacy: 5 failed files / 9 failed tests;
- baseline platform/Electron legacy: 11 failed files / 33 failed tests;
- candidate platform/Electron legacy: 10 failed files / 28 failed tests;
- every remaining candidate legacy failure was classified as identical baseline failure or a baseline variant with the same causal class;
- candidate-specific BrowserTask focused suite passed: 2 files / 16 tests;
- candidate typecheck passed;
- no tracked product files were modified to obtain the result.

Conclusion: broad Windows red is KI-006 baseline debt, not an Implementation 4 regression.

## Native acceptance evidence

The real H-004 lifecycle smoke is anchored at repository head `d8acc752133b125b9619cbc7fe09199f1283a22b`, with BrowserTask product code anchored at `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`.

Observed markers:
- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

It proved real Electron/Chromium same-page identity across hide/show and park/show, explicit destruction, two-process logical restart restoration/recreation, exactly-one-page ownership and structural secret isolation.

## E-020 — contributor attribution gate

After the technical promotion gate was closed, repository-wide CI revealed one independent process failure: the PR author email had no mapping under `contributors/emails/`.

Classification: **repository process gate, not BrowserTask/product regression**.

Correction:
- `contributors/emails/kevynlucasprofissional@gmail.com` was added rather than bypassing the check;
- the contributor-attribution check passed on the new exact PR head.

Anti-repeat rule:
- before final promotion, inspect repository-wide CI failures in addition to implementation-scoped gates;
- contributor attribution is part of merge hygiene and must be resolved rather than dismissed as unrelated red;
- a promotion-only metadata/documentation change creates a new final SHA, so exact-head automated gates must be observed again where path triggers apply;
- prior native BrowserTask evidence may be carried forward only after Git proves no BrowserTask/runtime/probe code changed.

## Final-head equivalence

Git comparison proved that the accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432` differs from controlled candidate `2ffee2335b6aba071e7b63457a047cd9334d4d92` only by:

- contributor-attribution mapping;
- Workstation engineering-journal promotion closure material.

No BrowserTask product/runtime/probe/workflow/dependency code changed. The H-004 native evidence and the controlled Windows causal classification therefore carry forward to the accepted head.

## Exact-final-head automated gates

On accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432`:

- `Workstation CI`: success;
- Docker Build/Test/Publish: success;
- contributor attribution: success;
- Windows committed-integration validation: success;
- Windows normal Workstation install: success;
- Windows checkout-clean assertion: success;
- Desktop typecheck: success;
- BrowserTask focused lifecycle tests: success;
- broad UI/platform diagnostics executed;
- final broad Windows aggregator: red, preserving KI-006 rather than masking it.

Because the final head contained no material code change after the controlled Windows comparison, the final red was classified as `KI-006_ONLY_BY_CONTROLLED_EQUIVALENCE`, with no new Implementation 4 failure class.

## Promotion execution

1. final live PR head verified as `75d10d35d4757496390debf8e4b4f9efb44c5432`;
2. final-head Workstation/Docker/focused Windows/repository-process gates observed;
3. PR #9 marked ready for review;
4. merge executed with `expected_head_sha=75d10d35d4757496390debf8e4b4f9efb44c5432`;
5. GitHub returned merge commit `fada723f43613e5e0f061cab24445573ac298998`;
6. PR #9 verified closed and merged;
7. `main` verified at `fada723f43613e5e0f061cab24445573ac298998`;
8. merge parents verified as previous main `ce78f120e8ed2974d6174e475cc7572afcfe41e0` plus accepted PR head `75d10d35d4757496390debf8e4b4f9efb44c5432`.

## Final decision

**PROMOTE — Implementation 4 is complete and integrated.**

KI-006 remains deliberately open as separate Windows portability/test debt. Browser Hub, Chat Browser View, Preview unification, complete BrowserSessionState, single-host transfer and later browser-foundation work remain future scope.

Implementation 5 may begin only as a new implementation cycle on top of promoted `main`; it must not retroactively expand the acceptance claim of Implementation 4.