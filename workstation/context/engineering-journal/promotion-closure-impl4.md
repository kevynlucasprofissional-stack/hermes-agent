# Implementation 4 — Promotion Closure

Date: 2026-08-30
PR: #9 — `feat(workstation): formalize BrowserTask lifecycle`

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

## E-020 — contributor attribution gate

After the technical promotion gate was closed, the repository-wide CI revealed one independent process failure: a PR author email had no mapping under `contributors/emails/`.

Classification: **repository process gate, not BrowserTask/product regression**.

Correction:
- add the missing contributor mapping;
- do not bypass or disable the contributor check;
- rerun/observe CI on the new exact head before merge.

Anti-repeat rule:
- before final promotion, inspect repository-wide CI failures in addition to implementation-scoped gates;
- contributor attribution is part of merge hygiene and must be resolved rather than dismissed as unrelated red;
- a promotion-only metadata/documentation change creates a new final SHA, so exact-head automated gates must be observed again where path triggers apply;
- prior native BrowserTask evidence may be carried forward only after Git proves no BrowserTask/runtime/probe code changed.

## Native evidence carry-forward boundary

The native H-004 lifecycle smoke remains anchored at `d8acc752133b125b9619cbc7fe09199f1283a22b` with BrowserTask product code anchored at `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`.

Any final promotion SHA after this note may inherit that native evidence only if the diff since the validated candidate contains no changes to BrowserTask/runtime/native-probe behavior.

## Final promotion sequence

1. verify exact live PR head;
2. prove post-validation changes are attribution/journal-only and do not touch product/runtime/probe code;
3. observe Workstation CI, focused BrowserTask Windows gate, Docker and contributor attribution on the exact final head;
4. keep KI-006 broad Windows failures visible and classified;
5. mark PR ready;
6. merge using the exact expected head SHA;
7. verify `main` contains the merge;
8. produce the final Implementation 4 report;
9. only then open Implementation 5.
