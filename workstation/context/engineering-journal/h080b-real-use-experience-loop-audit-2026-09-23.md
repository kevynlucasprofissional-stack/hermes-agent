# H-080B — Real-use Experience Loop Audit

Date: 2026-09-23

Status: **H-080A IMPLEMENTED / EXACT-HEAD CI RED; H-080B OPEN; REAL CAPTURE ACTIVE / REAL COMPILATION NOT YET CLOSED**

This audit incorporates three new evidence sources:

1. two real Hermes Work conversations using the native browser;
2. the OpenCode implementation/export that produced PR #45;
3. the architectural analysis of Experience Compiler + native Browser + future Laya integration.

It supersedes any statement that H-080A is exact-head qualified or that the Experience loop is already closed.

## 1. Current Git / PR truth

At the start of this audit:

```text
PR: #45 — H-080A: native pre-reasoning operational resolution production path
branch: integration/upstream-20260922-71a2fe39-h0793
reported implementation head: 68392e4b1678671b158fb6584a76a8da8964b2c3
base main at PR creation: 4893bf408a3a2b18120f52ff85c6cf0370ceded7
```

The implementation report is materially stronger than the previous H-080A audit:
- trusted production authority is derived from envelope + canonical task/session binding;
- raw prose cannot expand authority;
- E001F proves real deterministic mutation + real post-effect readback + EXECUTE / certificate / VERIFIED / accepted / COMMITTED + provider calls 0;
- E001D exercises real `workstation_durable_dispatch -> execute_tool_calls_sequential -> todo_list` exactly once;
- E003VF proves verifier failure does not commit and does not trigger blind LLM retry;
- metrics distinguish executed/satisfied/wait/handoff while unknown denominators remain `None`.

However, **exact-head CI is not green** at the audit snapshot.

Observed PR-head workflow state:
- `Workstation CI`: failed;
- `Workstation Browser Windows`: failed;
- Docker / Plugin Catalog: green;
- other workflows were still queued or undecided when inspected.

### Workstation CI failure

The contract job reaches 778 passing tests and one failure:

```text
workstation/tests/test_non_resident_await_telemetry.py
::test_wait_persists_releases_executor_and_resumes_after_restart

MockRouterWait.route()
got an unexpected keyword argument 'runtime_state'
```

This is a compatibility/test-double drift caused by the current router call shape. It is small but is still a release-gate failure until corrected.

### Windows workflow failures

Core H-080/browser foundation checks in the Windows job were green. The red aggregate came from broader release/platform gates, including:

- Linux/POSIX-specific assertions executed on Windows:
  - `linux-crash-diagnostics.test.ts` path separator mismatch;
  - `log-rotation.test.ts` Windows `EPERM` on `ftruncate`;
  - `tray-host.test.ts` assumes `process.getuid()`.
- release qualification `workstation_smoke` timed out after 900 seconds;
- packaged Desktop GUI E2E observed `Timed out connecting to Hermes backend`.

These may be pre-existing or cross-platform qualification debt, but they are **not green evidence**. Before PR #45 promotion, either fix the real defects or prove and scope platform-specific tests without hiding portable regressions.

## 2. Real-use case A — “Abre o browser”

Observed behavior:

```text
user: "Abre o browser"
-> model reasons about BrowserClaw / browser_exec / MCP
-> loads mcp-browser-automation + browserclaw-usage skills
-> probes configuration / runtime
-> user clarifies: use native browser
-> native browser_navigate finally runs
```

For the Hermes Workstation product, this is unnecessary cognitive/tool overhead for a common operational intent.

The architecture already declares Electron Chromium as the primary internal Browser and the broker/controller as the routing authority. A normal Workstation/Desktop request to open the browser should therefore be resolvable as a native-browser intent when policy/session context makes that route available. Explicit “browser nativo” phrasing must never detour into BrowserClaw skill discovery.

This is not a license to hard-code natural-language strings into execution authority. The correct target is:

```text
trusted turn
-> bounded OperationIntent / browser route family
-> known promoted capability if available
-> CapabilityRouter proof
-> native Browser controller
```

When intent cannot be established safely, reasoning remains the fallback.

## 3. Real-use case B — “Abre o ChatGPT pelo browser nativo”

The first native operation already returned:

```text
success = true
runtime = electron-chromium
url = https://chatgpt.com/
title = ChatGPT...
wall_detected = false
readiness = stable
semantic interactive elements present
```

That is strong goal-aligned evidence for the narrow goal **“open ChatGPT in the native browser”**.

The turn nevertheless spent additional rounds on:
- `browser_vision`;
- `vision_analyze`;

to ask whether the account was logged in, even though the user had not requested login-state verification.

New rule:

> **Verification must be proportional to the declared operational goal.**

For `open_site(chatgpt.com)`, authoritative browser readback of expected host/URL plus controller readiness can be sufficient. Login/authentication is a distinct semantic predicate and must only be verified when required by the intent/postcondition or when the route is ambiguous.

This avoids replacing one form of expensive reasoning with redundant “verification theater”.

## 4. Production Experience Compiler truth from the real session

The native browser session itself exposed the current H-080B bottleneck.

Real production artifacts/journals exist:
- `transition_*.json` and `trace_*.json`;
- journal events such as `adaptive observation captured; semantic verification required`.

But the observed samples are not admissible learning capital:

```text
outcome = uncertain
verification.status = INCONCLUSIVE
evidence_strength = 0
trust_class = runtime_observation
source = adaptive_trace
```

The runtime reported no real promoted learned capability/procedure from these sessions.

The current production hook already exists after canonical accepted completion:

```text
canonical completion
-> ExperienceCorpus(..., discover=True)
-> corpus.accept_run(journal, outcome)
-> ExperienceCompiler(..., corpus).mine()
-> journal "experience operational candidate; causal validation required"
```

The gate sequence is intentional:

1. `ExperienceCorpus.accept_run()` rejects a run that is not `verified_completed` or contains unresolved uncertainty.
2. `ExperienceCompiler` refuses unverified semantic experience.
3. Global promotion requires cross-run evidence/diversity and validation.

The safety gates are correct. **Do not weaken them.**

The missing work is to make real product operations capable of producing the verified, lineage-bound semantic evidence those gates require.

## 5. Important correction: browser navigation is not inherently “uncompilable”

A prior runtime explanation concluded that a request such as “open ChatGPT” is structurally incompilable because it lacks persisted external-state verification.

That conclusion is too broad.

The semantic effect does not need to be “ChatGPT changed state”. The effect can be a Workstation-owned browser state transition:

```text
before:
  native browser task not at target host

operation:
  native browser navigate(chatgpt.com)

after:
  authoritative Browser controller reports
  host == chatgpt.com
  expected BrowserTask/tab ownership
  readiness == stable
```

This can be a verifiable **local browser capability** if the verification contract is explicitly scoped to Workstation-owned browser state and uses a trusted post-effect browser readback.

Do not mislabel such evidence as external persisted state. The verifier strength/trust/source must truthfully describe browser-controller-owned state.

Authentication state, form submission, external account changes, and third-party mutations require stronger/domain-specific verification.

## 6. Canonical architectural decision

Do **not** introduce a parallel executable abstraction such as `LearnedScript`, `MicroProcedure`, `BrowserSkill` or arbitrary generated TypeScript/Python as a new authority plane.

The executable unit remains:

```text
OperationalCapability
```

Browser-specific deterministic representation may evolve inside:

```text
OperationalCapability.implementation
```

If the current step representation is insufficient, a typed `BrowserProcedureIR` is acceptable **only as an implementation format**, e.g.:

```text
navigate(target)
observe()
resolve(semantic_anchor)
click(anchor)
fill(anchor, value)
wait(predicate)
verify(predicate)
```

Execution must remain under the existing certificate / authority / dispatcher / BrowserControlBroker / WorkstationBrowserController / verifier chain. Do not create an `eval(generated_script)` bypass.

## 7. H-080B minimum vertical proof

The next high-impact implementation lane is one vertical product experiment, not a broad learning redesign.

Preferred first target: a **safe native-browser local-state capability** such as opening a known site in the Workstation browser.

Required causal chain:

```text
normal novel Hermes turn
-> reasoning resolves native-browser action
-> physical native-browser execution
-> authoritative post-effect browser readback
-> canonical VERIFIED completion
-> TransitionSample / ExperienceCorpus accepts the run
-> candidate compilation
-> second independent compatible verified run (when required by promotion policy)
-> controlled replay / verifier validation
-> ExperiencePromotionPolicy
-> PROMOTED OperationalCapability
-> future normal turn with an already-established typed OperationIntent
-> Operational Resolution before provider
-> CapabilityRouter selects/proves capability
-> native Browser executes exactly once
-> VERIFIED / COMMITTED
-> provider calls = 0
```

The test must also prove the negative path:
- wrong host/readiness/drift -> not VERIFIED;
- ambiguous or missing intent -> normal reasoner;
- controller bound but unavailable -> fail closed;
- no second browser backend retry;
- no blind LLM retry after an uncertain effect.

## 8. Evidence sufficiency / anti-overreasoning

Add a narrow policy/helper only if one does not already exist:

```text
declared goal predicates
+ authoritative post-effect evidence
-> goal satisfied?
```

If yes, stop. Do not invoke vision, screenshots, DOM re-analysis, or an LLM merely to reconfirm unrelated predicates.

For the ChatGPT example:

```text
goal: host == chatgpt.com and native browser ready
browser_navigate response: proves both
=> no browser_vision required
```

If the goal is instead:

```text
logged_in == true
```

then a separate trusted observer is required.

## 9. Laya sequencing

Laya remains deferred until the deterministic H-080B loop is proven without it.

After H-080B:

```text
OperationIntent / context
-> Laya candidate shortlist or family prediction (shadow first)
-> CapabilityRouter deterministic proof
-> RoutingCertificate
-> execution / verifier
```

Laya never grants authority, never bypasses the Router, and never decides terminal truth.

Train/evaluate against canonical decisions and verified outcomes, not against raw LLM guesses.

## 10. Limited-Codex priority order

Because implementation-model budget is constrained, spend it only on:

### P0 — make PR #45 exact-head qualification truthful
1. fix/triage current CI red gates;
2. correct the stale `MockRouterWait.route(... runtime_state=...)` contract test;
3. classify/fix Windows platform/release issues with evidence;
4. do not redesign H-080A.

### P1 — close one browser-native H-080B vertical loop
1. connect native browser post-effect evidence to canonical acceptance/Experience lineage;
2. produce the first real accepted verified browser TransitionSample;
3. produce cross-run evidence required for promotion;
4. compile/validate/promote an OperationalCapability;
5. prove a future normal turn with an already-established typed OperationIntent executes before provider with 0 provider calls.

Fresh natural-language paraphrase -> OperationIntent/capability recognition is **not** part of this first H-080B closure. That is the later System-1/Laya lane; do not add an ad-hoc prose classifier to close H-080B.

### P2 — eliminate obvious real-use waste
1. explicit native-browser intent must avoid BrowserClaw/skill detours;
2. goal-sufficient browser evidence must stop redundant `browser_vision` / `vision_analyze`;
3. add metrics for redundant reasoning/tool rounds only through existing metrics owners.

### DEFER
- production Laya integration;
- broad BrowserProcedureIR redesign unless P1 proves current implementation format inadequate;
- arbitrary generated scripts / Playwright escape hatches;
- new parallel capability or memory systems;
- generalized workflow synthesis beyond the first vertical proof.

## 11. Definition of done for this next lane

```text
PR #45 exact-head required CI: GREEN or each excluded gate causally proven out-of-scope and policy-correct
real browser post-effect evidence reaches canonical verification: YES
real verified browser experience accepted by ExperienceCorpus: YES
real experience-derived candidate created: YES
cross-run/promotion requirements satisfied without weakening policy: YES
promoted learned OperationalCapability exists: YES
future normal turn with established typed OperationIntent routes before LLM: YES
fresh-paraphrase semantic recognizer implemented as part of H-080B: NO
native browser is the only mutation executor: YES
future verification: VERIFIED
future dispatch: COMMITTED
future provider calls: 0
goal-sufficient open-site case avoids redundant vision: YES
novel/ambiguous/drift case still reasons safely: YES
Laya execution authority added: NO
parallel LearnedScript/BrowserSkill authority added: NO
```

## Principle

> **The next optimization is not “make the compiler more eager”. It is “make successful real operations produce truthful, goal-aligned, post-effect evidence that can safely become learning capital”.**

H-080B closes when experience from normal product use can cross the existing safety gates and later remove unnecessary reasoning — not when the gates are relaxed.
