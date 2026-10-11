# OPC-001 — Prefabricated Operational Capabilities — Engineering Journal

**Recorded:** 2026-10-10 | **Classification:** design/specification validated against main code; reference package tested offline; **production integration UNQUALIFIED**.

## Hypotheses, evidence and falsifiers

**H-OPC-001-A — A closed pre-LLM intent match can avoid reasoning and navigate a known destination safely.** Evidence: `agent/operational_resolution.py` has terminal `EXECUTED`, `WAIT`, `HANDOFF` contracts; `workstation/integrations/hermes/operational_resolution.py` runs before provider and uses owner-mediated dispatch; v0.1 reference has exact match + independent browser snapshot. Falsified if desktop actual run calls LLM before resolver, returns EXECUTED on tool ACK alone, or dispatches on untrusted ingress. NEXT: Electron Windows E2E with tool counters.

**H-OPC-001-B — Agent and Workstation can share a prefab catalog without duplicate executor.** Evidence: `model_tools.py` discovers `tools/*.py` registrations; `toolsets.py` distinguishes `browser`/`desktop_ui`. v0.2 reference adds `tools/hermes_prefab_catalog.py` read-only discovery, while Workstation retains `tools/workstation_prefabs.py` + Fast Path. Falsified if schema absent under real Agent toolset, toolset disabled but tool still visible, or extra side-effect authority appears. NEXT: `get_tool_definitions` + gateway integration test.

**H-OPC-001-C — We can extract valuable candidates from real sessions + HTML without leaking content.** Static evidence in 9 distinct supplied session JSONs and 8 distinct snapshots: total 3,297 tool calls, 1,109 browser-prefixed calls; family breakdown Instagram 543, Trello 387, WhatsApp 148, ChatGPT 17, generic browser 14. Trello snapshots include 761 + 539 card nodes, but those are historical DOM observations, not live API truths. Falsified if authenticated live DOM shifts, source associations false, or corpus contains sensitive data. NEXT: re-run SHA-dedup inventory locally and compare with canonical safe owner receipts.

**H-OPC-001-D — Current compiler needs no replacement but browser admission/readback needs additional qualification.** Observed `run_local_adoption.py` supports write_file/read_file only, readback write_file. `compilability_monitor.py` SHADOW suppresses mining, and `resolve_policy` checks direct_qualification_ref only nonblank. D-039 proposes active observation/mining while preserving effect authority. Falsifier: current checkout materially changed after the inspected f21e803 main; re-evaluate and adapt, do not patch by stale line number.

## Local candidate/reference status

- Existing user package `Hermes-Work-Prefabs-Plug-and-Play-v0.1.zip` includes 17 files, shell/bat installer, catalog, Trello official API adapter, scoped navigation, offline fingerprints, candidate `DISCOVERED` seed and unit tests; it is a reference, not qualified production code.
- Complement `Hermes-Work-Prefabs-Integracao-v0.2.zip` adds generic Agent `browser` toolset `prefab_catalog`, offline multi-file `harvester.audit_corpus` and `audit-corpus` CLI, plus privacy tests. **33/33 local Python unittests passed** in isolated package. Not an Electron/live policy/CI qualification.
- v0.2 audit of provided copies deduplicated 9 JSON and 8 HTML. File names and fingerprints support a site-family association only. Never represent the HTML as step-by-step independent runtime verification.
- The local Windows paths from user are *not* on the examined GitHub main tree; implementer must verify Windows checkout contents. Remote Desktop Commander device was offline; no local checkout verification performed.

## Risks/known limitations

1. **H-079 upstream-first** mandatory; H-081/H-082 and exact-head Windows/Workstation CI remain to be checked. Documentation merge f21e803 does not prove qualification.
2. Model tool schemas and instructions alone do not ensure appropriate invocation. Need deterministic dispatcher preference test plus Agent toolset visibility assertions.
3. Original ref Fast Path matches exact human command only; no guarantee of zero LLM on natural-language variants. Stale selectors/prompt injection must fail closed.
4. Trello CLI manual writes are not agent action authorization. No agent mutation until TaskRun Policy/effect budget/readback owner is proven.
5. Unknown external effects must not be repeated. Route ambiguous post-dispatch outcomes to WAIT/HANDOFF with durable reconciliation.
6. Laya should classify opportunities, not produce proof, labels, promotion, or permissions.

## Smallest discriminating experiment and acceptance

E0: run source inventory offline without content disclosure. E1: `prefab_catalog` visible to Agent in browser toolset; `prefab_execute` visible Workstation desktop_ui. E2: open Editorial on native Electron with 0 System-2 calls and owner URL readback. E3: Trello GET with correct source and 0 System-2 calls. E4: run-time missing scope/policy blocks. E5: add one canonical Trello write with readback + no uncertain retry. E6: `ExperienceCompiler.mine()` scoped candidates + real verifier/replay, no global auto-promotion. Record actual commands/results per experiment and stop on failure.

## Next

Implement OPC-00/01 proof and small RED fixtures in a new qualified branch after H-079; keep docs PR separate. Canonical implementation prompt: [PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md](../PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md). Canonical decision: [PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md](../PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md).