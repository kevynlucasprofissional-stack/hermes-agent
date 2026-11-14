# WhatsApp Native Catalog — safe model boundary test checkpoint

Date: 2026-10-25 (America/Sao_Paulo). **HOLD / NOT RELEASE QUALIFIED**. Continuation of `whatsapp-catalog-stagea-hold-20261025.md`; do not restart audit.

## Workspace and owners
- Windows checkout `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e` at entry. Local `origin/main=bafa3c43f4ecf7953e377e29cca6515089e530fe`, `upstream/main=571a5911ae6aaa05ef3df53bf0f6720c4556c24a`. Latest remote upstream observed earlier: `4ea8d23cc9f527332ccb1d55359b27741b6ea51b`. No fetch, merge, branch/worktree/PR/commit/push.
- Existing active claims at preflight: `chatgpt-whatsapp-m3` controls `tools/browser_workstation.py`, WA browser executor, its tests and central context; `chatgpt-whatsapp-m3-compat` controls metrics/recipient tests; `site-ops-migration`, `chatgpt-siteops-contract`, `chatgpt-siteops-docs`, and `chatgpt-siteops-sim` control Site Ops. No active claim crossed.
- H-079 requires scoped qualified upstream Stage A or explicitly authorized task-specific exception. Neither established for this mission; dirty shared checkout must not be overwritten. No production or runtime edit performed.

## Exact scope changed
- NEW untracked `tests/tools/test_whatsapp_native_registry_contract.py` (synthetic-only). The acceptance tests inspect actual `tools.registry.registry.get_entry` and schemas, call `registry.dispatch` for untrusted preview reference, and assert `whatsapp_batch_approve` is not registered.
- This test does not read live browser, contact data, or real production databases; its source identifier and phone token are synthetic. It cannot send WhatsApp messages.
- No existing test assertion weakened. Prior `tests/tools/test_whatsapp_native_catalog_regression.py` retained untouched.

## RED/GREEN evidence
Command (from repository root):
`$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/tools/test_whatsapp_native_registry_contract.py -q -p no:cacheprovider --tb=line`
Observed after correcting **test import only** (`ToolEffect` is in `tools.effects`, not `tools.registry`):
**4 failed, 1 passed in 1.28s**.
- RED: `test_native_capabilities_registered_for_desktop_only`: `whatsapp_read_messages` registry entry missing.
- RED: `test_read_contract_cannot_request_browser_mutations_or_database_writes`: read entry absent, so no proven PURE_READ / prohibited argument contract.
- RED: `test_preview_contract_uses_authorized_references_not_private_payloads`: preview entry absent; no secure schema.
- RED: `test_untrusted_preview_reference_fails_closed_at_real_dispatch`: registration absent; unknown-tool error is NOT a valid security denial. Test intentionally asserts a real handler before dispatch.
- GREEN: `test_human_approval_must_not_be_a_model_invocable_tool`: approval not registered.
Earlier evidence remains separate: 3 RED primitive/catalog tests and 8 M3 RED (last tested earlier), plus 64 M1/M2 unit GREEN and 17 browser-task Vitest GREEN (not rerun here).

## Minimal runtime patch when and ONLY when the gate/owners permit
- Registration owner: `tools/browser_tool.py`; desktop toolset owner `toolsets.py`; delegated wrapper source `tools/browser_workstation.py` is M3-claimed. A Python function or schema availability provider is not enough: need actual `registry.register`, desktop-only toolset, check_fn, safe schema, dispatch handler and model discovery proof.
- READ: mandatory `ToolEffect.PURE_READ`, limited `limit` and no model `persist` or `db_path`; persist=False at internal executor, native Browser-only session, bounded redacted result.
- PREVIEW: mandatory `ToolEffect.PURE_READ`, config-selected source alias, campaign and step references; no model-supplied recipients, DB path, phone, message template, bypass, token or `approved_by`. Trusted layer reads authorized campaign records only and redacts egress. Existing private primitive currently exposes full phones but is NOT registered; raw private primitive output != existing agent data leak. Preserve privacy boundary without breaking internal executor.
- APPROVAL: no `whatsapp_batch_approve` registration. Human-authenticated independent token gate needed before any real send; standalone `approved_by` string is not attestation.
- Causality and M3: wait for current owner, preserve BrowserTask run fencing and UNCERTAIN idempotency.
- Verification after patch: newly added 5 tests GREEN plus prior 3 RED transformed by genuine security fixes, actual registry dispatch + tool definitions on Desktop chat, BrowserTask two-turn, then native agent-driven E2E read/preview from safe fixture; no sends. Exact-head Electron/CI qualification before any READY claim.

**Disposition:** HOLD. Do not count RED as a runtime fix or claim native E2E. The single next external dependency is H-079 qualification or an explicit, scoped maintainer exception recorded by the authorized context owner; then coordinate shared source ownership.

## Revalidacao do gate — 2026-10-25 02:32 BRT

- Checkout: main HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e; dirty, preserve everything.
- origin/main local and remote bafa3c43f4ecf7953e377e29cca6515089e530fe. upstream/main local 571a5911ae6aaa05ef3df53bf0f6720c4556c24a; remote 4ea8d23cc9f527332ccb1d55359b27741b6ea51b (read-only ls-remote).
- merge-base main...upstream/main 3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065; ahead/behind 1349/6574 (cached ref). Prior pin 66605471 is an ancestor, NOT current Stage A qualification.
- CURRENT.md around line 6244 records a prior 2026-10-11 H-079 exception for a different operational cycle. No explicit task-scoped WhatsApp catalog exception granted in THIS user's request. Existing canonical docs claimed by M3 owner; must coordinate before recording exception.
- Claims still active: chatgpt-whatsapp-m3 (tools/browser_workstation.py, executor/tests and canonical docs), chatgpt-whatsapp-m3-compat (recipient/metrics), multiple SiteOps and planning owners. tools/browser_tool.py and toolsets.py are dirty and must preserve other changes.
- Registry.dispatch exists in tools/registry.py around line 931; ToolEffect.PURE_READ lives in tools/effects.py.
- Command: python -m pytest tests/tools/test_whatsapp_native_registry_contract.py tests/tools/test_whatsapp_native_catalog_regression.py -q -p no:cacheprovider --tb=line
- Observed: 7 FAILED, 1 PASSED in 2.79s (synthetic; no real WhatsApp). Four failures in native_registry_contract.py and three in native_catalog_regression.py. PASS: test_human_approval_must_not_be_a_model_invocable_tool.
- Direct private preview and approval RED assertions cannot turn GREEN from registering wrappers alone; trusted private-return data and human-authenticated token issuance need deliberate architectural correction without weakening assertions.
- No runtime edits, real sends, DB writes, native Hermes chat E2E, Stage A qualification or Git integration here. No PR created.

**Single next required gate:** explicit task-scoped maintainer waiver for H-079 Stage A local WhatsApp catalog development, documented in canonical CURRENT_STATE.md and engineering-journal/CURRENT.md by their owner; OR qualified upstream Stage A baseline. Only then claim non-overlapping code, build secure registered desktop_ui read/preview wrappers, close both sets of RED, and verify actual Hermes chat agent-driven A/B. Release remains HOLD.
