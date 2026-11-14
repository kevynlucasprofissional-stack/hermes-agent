# WhatsApp Native Catalog — Stage A HOLD / 2026-10-25

**Scope:** read-only gate and synthetic RED verification, no runtime edits, no live WhatsApp effects. This checkpoint supplements `whatsapp-native-integration-audit-20261025.md`.

## Checkout (revalidated)
- `C:\Github\hermes-agent` on `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`.
- Local `origin/main@bafa3c43f4ecf7953e377e29cca6515089e530fe` (1 ahead of checkout, no pull).
- Locally cached `upstream/main@571a5911ae6aaa05ef3df53bf0f6720c4556c24a`.
- `merge-base(main, upstream/main)=3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065`, ahead/behind `1349/6574` (local ref snapshot). Previously observed remote tip `4ea8d23cc9f527332ccb1d55359b27741b6ea51b`; not freshly fetched in this pass.
- Prior selected pin `66605471e9f0b0832abbefaf625ce08e948ca540` **is** a main ancestor (`git merge-base --is-ancestor` success). This does **not** establish a qualified latest Stage A.
- Since the merge base, upstream changed `model_tools.py`, `tools/browser_tool.py` and `tools/registry.py`: relevant owner overlap. Latest upstream log touching these paths in local ref: `b87977cadd` (2026-10-23).
- No documented target-scoped H-079 Stage A exception for THIS mission and no exact-head green Workstation qualification evidence. Do not infer one from another conversation or historical branch. A dirty shared `main` prevents safe ad-hoc baseline merge. **HOLD** runtime implementation.

## Concurrent ownership (real claims, do not take over)
- `site-ops-migration` claims `apps/desktop/scripts/site-ops` and other site-ops paths.
- `chatgpt-whatsapp-m3` claims `tools/browser_workstation.py`, `workstation/integrations/hermes/whatsapp_browser_executor.py`, `workstation/tests/test_whatsapp_browser_executor.py`, `tests/tools/test_whatsapp_browser_tools.py` and central Workstation context files. M3 is an independent concurrent writer; no modification of its paths. Inspect claim again on resumption.

## Reproducible RED for catalog/privacy/approval
Command:
`$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/tools/test_whatsapp_native_catalog_regression.py -q -p no:cacheprovider --tb=line`

Observed **3 failed in 37.53s**:
1. `test_native_read_and_preview_are_registered_in_agent_catalog`: missing first-class registrations `whatsapp_batch_preview`, `whatsapp_read_messages`. Existing `whatsapp_send_message` is registered in `desktop_ui`.
2. `test_batch_preview_never_exposes_raw_phone_to_model`: `whatsapp_batch_executor.whatsapp_batch_preview` emits raw synthetic phone in `sample_messages` and `eligible_recipients`.
3. `test_batch_token_cannot_be_minted_by_unverified_operator_string`: `whatsapp_batch_approve` emits `APPROVED` token on arbitrary `approved_by` string.

Prior checkpoint verified **64 passed** (M1/M2/tool regressions), **8 existing M3 failures**, and **3 RED** above. Did not rerun M3 while another writer claims its files. All uncommitted RED tests are developmental evidence, not production/native E2E.

## Single highest-priority next action
1. Qualify appropriate upstream Stage A baseline (pin + seam reconcile + exact-head gates) separately, or obtain **explicit task-scoped written maintainer exception** recorded in `CURRENT_STATE.md` and `engineering-journal/CURRENT.md` by their rightful owner. Do not merge into dirty main, manipulate others' claims, or erase local changes.
2. Claim non-overlapping paths for catalogue handler/contract; coordinate `tools/browser_workstation.py` with M3 owner if needed.
3. Expose a read-only `whatsapp_read_messages` tool limited to native Desktop session, no implicit DB write, never with uncontrolled contact header spoofing. For preview, model inputs must be source alias + campaign/step reference, never raw recipient phone/text or arbitrary DB path. Trusted resolver fetches only authorized rows. Model-facing outputs show count, exclusion reasons, safe IDs, masked identity, bounded preview and manifest digest without raw numbers or sensitive bodies; do not expose `whatsapp_batch_approve` until authenticated human gate.
4. Turn 3 RED -> GREEN without weakening assertions, test via actual registry dispatch and synthetic temporary DB; then separately close M3 causal RED through its owner.
5. Only when gates pass, E2E prompts in native Hermes chat: read current controlled synthetic conversation and preview temp synthetic campaign; no real sends and no fallback external Chromium/CDP.
6. Cross-turn BrowserTask mismatch remains a hypothesis: `tools/browser_workstation.py` computes `effective_rid = rid or session_id` whereas Electron `workstation-browser-task.ts::bindRun` rejects rebinding a task to another run. Preserve fence and show two-turn native receipts before changing lifecycle.
7. No GH integration, PR, commit, automated background work or release claim made. Record exact HEAD/tests/CI at every gate.

**GO/HOLD**: HOLD. No user-data write, WhatsApp send, runtime fix, Stage A merge, branch change, stash, reset or release qualification in this pass.

## Revalidation of next turn (2026-10-25, 02:15 BRT)

- Exact HEAD unchanged: f1d5ab2f030e940ed4571371b0de45a21a009c9e; main remains one commit behind origin/main. No source edits by this turn.
- Fresh READ-ONLY git ls-remote: origin/main=bafa3c43f4ecf7953e377e29cca6515089e530fe; upstream/main=4ea8d23cc9f527332ccb1d55359b27741b6ea51b. Local upstream/main=571a5911ae6aaa05ef3df53bf0f6720c4556c24a; no fetch/merge.
- Active claims include chatgpt-whatsapp-m3 (tools/browser_workstation.py, whatsapp_browser_executor.py, M3 tests and central context); site-ops-migration; chatgpt-siteops-contract; chatgpt-siteops-sim. Do not steal/release/edit claimed files.
- Scoped native Vitest: cd apps/desktop; env CI=1; node_modules/.bin/vitest.cmd run electron/workstation-browser-task.test.ts --reporter=dot -> 1 file / 17 tests PASS; process exit 0. This is NOT a two-turn Hermes chat E2E.
- tools/browser_workstation.py::_task_key (approx line 549) uses stable session_id for chat turns; _dispatch (approx line 972) uses effective_rid = rid or session_id. Electron workstation-browser-runtime.ts::executeControlRequest (approx line 2819) computes an effective run and binds it around line 3000. workstation-browser-task.ts::bindRun (approx line 388) correctly refuses changed run on same BrowserTask. This establishes a mechanism, not the exact live cross-turn root cause; require actual agent receipts before remediation. Do not weaken the fence.
- Native tool discovery: tools/browser_tool.py registers only whatsapp_send_message; whatsapp_read_messages and whatsapp_batch_preview wrappers exist but do not register. Three previous RED tests remain valid evidence and were NOT rerun during this resumed pass. No claim of GREEN.
- Boundary design: trusted private preview may retain full recipient phone internally but must NEVER pass raw content to the model. The missing MODEL-FACING tool requires configured-source and campaign/step references, trusted scope/opt-in, sanitization and bounded results. The existing direct primitive test proves raw primitive output, not an actual currently exposed tool egress. Trusted human approval must be independently authenticated; agent-supplied approved_by text cannot attest human consent. Keep safeguards, don't satisfy RED by changing an unrelated private helper alone.
- H-079 Stage A remains unqualified; no task-scoped exception recorded for this mission. Dirty shared tree and active ownership bar runtime edits. No runtime changes, no send, no DB production writes, no agent-driven native E2E, no Git mutations in this turn.

Final disposition: HOLD. Next gate: qualified upstream Stage A OR explicit documented task-scoped developer exception, and coordinate M3 owner before shared-file edits. Then implement safe first-class registration, verify registry dispatch with synthetic temp DB, close causal M3 RED, run BrowserTask two-turn and native Hermes chat E2E A/B before any release claim.