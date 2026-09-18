# Browser Operational Admission & Primitive Closure — 2026-09-18

> **Companion P0 lane:** Browser task/session/viewport presentation recovery is tracked
> in [BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md](BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md).
> Admission answers whether an operation may execute and be verified; the companion
> lane answers whether the correct BrowserTask is the surface the user sees before
> and after restart. Neither may create a second Browser/session state owner.


## Status

**LIVE DOGFOOD REPRODUCED / P0 IMPLEMENTATION REQUIRED.**

This document records the post-CP0–CP9 integration gap exposed by a real authenticated
Hermes Work task against Trello in the native Electron Chromium Browser. It is not a
Trello-specific workaround plan. The reproduction exposed a missing contract between:

```text
adaptive agent execution
  -> execution-policy admission
  -> Experience Compiler / OperationalCapability
  -> Operational Kernel browser primitives
  -> Verified Operational Control Plane
  -> persisted verification / uncertainty
```

The native Browser itself was able to navigate, snapshot, click, inspect and keep the
same BrowserTask. The failure occurs when discovered operational knowledge becomes
repetitive and the legacy compilation gate requires a deterministic representation
that the Browser Kernel cannot yet faithfully express.

## Canonical diagnosis

```text
LLM discovers a valid UI procedure
  -> native browser executes it
  -> repetition detector asks for work_execute/compilation
  -> durable path requires typed mutation + authority + verifier/readback
  -> exact UI effect is not representable by current trusted primitives
  -> arbitrary browser_console can express it, but is correctly opaque/mutating
  -> preparation tools are also admitted as mutations by the legacy gate
  -> durable_compile_required <-> PREFLIGHT_REQUIRED loop
```

The correction is **not** to make arbitrary JavaScript, shell or file writes trusted.
The correction is to close the typed primitive/admission gap and make the Verified
Operational Control Plane the authoritative mutation-admission boundary.

## Reproduced findings on current main

### BOA-001 — effect taxonomy misclassifies first-party read surfaces

`tools/read_preview_tool.py` registers `read_preview` without explicit read effect
metadata, while `tools/effects.py` conservatively defaults unknown builtins to
`MUTATION`. Live evidence therefore recorded `read_preview` as
`unknown_mutation`.

Required correction:
- explicitly classify `read_preview` as `PURE_READ`;
- audit other first-party read-only registrations for the same omission;
- preserve the conservative unknown => mutation default;
- for multi-action tools such as `drive_preview`, support action-sensitive effect
  classification or split read/discovery operations from mutating operations.

### BOA-002 — structural repetition can still force compilation without semantic closure

`workstation/execution_policy.py::decisions_for_calls()` still contains a non-browser
structural fallback capable of reaching `REQUIRE_COMPILE`, and broad families such
as `filesystem.file` collapse unrelated resource instances.

Required correction:
- `REQUIRE_COMPILE` requires positive semantic homogeneity for **all** backends;
- structural similarity may only `SUGGEST_COMPILE` / seed Experience Compiler work;
- semantic identity must include the stable operation family and sufficiently specific
  target/resource family;
- `terminal` is never one semantic operation merely because the same tool is used;
- distinct `write_file` targets are not automatically one homogeneous fan-out;
- preserve real homogeneous fan-out compilation/canary behavior.

### BOA-003 — native Browser lacks a deterministic rich-text paste primitive

Current native `browser_type` lowers to CDP `Input.insertText`. In the reproduced
Trello ProseMirror editor this did not preserve the required newline semantics.
A page-side `ClipboardEvent("paste")` with `DataTransfer(text/plain)` did preserve
the desired text, but arbitrary `browser_console` JavaScript is not an acceptable
promoted Capability primitive.

Required correction:
- extend the existing Browser tool/runtime surface rather than add arbitrary JS trust;
- add a trusted first-party semantic operation equivalent to
  `browser_paste_text(target, text, clear=true)`, or an explicit
  `browser_type(..., mode="plain_text_paste")`;
- resolve semantic anchors/ref immediately before action;
- support contenteditable / ProseMirror-class targets without site-specific Trello code;
- return structured target metadata and semantic effect;
- do not let model-supplied JavaScript become the deterministic implementation.

### BOA-004 — persisted browser readback has no narrow first-party primitive

DOM observation after a Save click is not sufficient evidence that the external
provider persisted the value. In the reproduction, authenticated same-origin GET
readback worked while direct write attempts were blocked by provider CSRF.

Required correction:
- add or extend a Browser read primitive for bounded `GET`/`HEAD` only;
- same-origin by default, with existing website/network policy for any allowed
  cross-origin case;
- no request body and no arbitrary JavaScript;
- bounded response size with ArtifactStore spillover for large results;
- structured JSON/text result suitable for verifier contracts;
- classify as `PURE_READ`/discovery;
- preserve credential/cookie isolation: the model receives response data, never raw
  cookie/auth material.

### BOA-005 — two admission planes can disagree

Normal model tool calls still pass through legacy `run_agent -> decisions_for_calls`
and may be blocked by `durable_compile_required` before the new Capability Router
controls the decision. `work_execute(action="route")` uses the new Control Plane.

Target ownership:
- Capability Router / policy / certified dispatch becomes the authoritative admission
  boundary for mutating operational work;
- the legacy repetition detector becomes a learning/optimization signal, not a second
  independent government;
- safe bounded adaptive execution remains possible when no executable Capability exists;
- mandatory compilation is legal only when the runtime can actually represent and
  verify the homogeneous operation.

### BOA-006 — CP route integration must not accept model-authored authority as truth

`TaskCompiler._execute_route()` currently accepts authority material from the request.
OperationIntent may request effects, but execution authority must come from trusted
runtime context.

Required correction:
- derive effective `AuthorityScope` from trusted `MessageEnvelope`,
  `IntentAuthority`, TaskRun/policy/approval context;
- request payload may narrow authority, never mint or broaden it;
- missing trusted authority fails closed for mutation;
- keep `IntentAllows(effect) AND AuthorityAllows(effect) AND PolicyAllows(effect)`.

### BOA-007 — certified dispatch must be the mandatory mutation chokepoint

The Router can emit a valid certificate, but `TaskCompiler._execute_route()` currently
invokes capability execution directly instead of making `CertifiedDispatcher` the
enforced boundary.

Required correction:
- every mutating EXECUTE/COMPOSE route must pass a valid certificate through the
  certified dispatcher;
- pre-dispatch freshness, uncertainty, run fencing and authority are revalidated there;
- no certificate => no mutation dispatch in production paths;
- successful tool return must not become COMMITTED without verifier evidence when the
  effect contract requires persisted verification.

### BOA-008 — browser timeouts need effect-sensitive uncertainty

The browser controller currently treats timeout as retryable generically.
For reads this can be safe; for click/type/paste/submit/save a timeout may occur after
the page already received the mutation.

Required correction:
- read/discovery timeout may remain bounded retryable;
- mutation timeout after possible dispatch becomes `UNCERTAIN`;
- never blind-retry an uncertain mutation;
- reconcile with authoritative readback / operation identity before continuation.

### BOA-009 — SPA snapshot readiness can accept a transient empty state

Live evidence produced a successful snapshot with the target URL but zero body text and
zero elements; moments later the same page was fully hydrated.

Required correction:
- do not add hostname-specific sleeps;
- when a non-blank HTTP(S) page reports loaded but both semantic inventory and body text
  are unexpectedly empty, perform bounded semantic re-observation;
- prefer stability/readiness criteria over fixed delay;
- return explicit readiness/freshness metadata when observation remains ambiguous.

## Canonical desired flow

```text
human intent
  -> immutable OperationIntent
  -> trusted AuthorityScope + Policy
  -> Capability Router

exact executable Capability?
  yes
    -> RoutingCertificate
    -> CertifiedDispatcher
    -> deterministic Operational Kernel
    -> persisted verifier
    -> COMMITTED

no exact executable Capability?
  -> bounded adaptive execution where policy permits
  -> capture TransitionSamples
  -> Experience Compiler candidate
  -> canary / validation / promotion
  -> future exact replay

repetition detected?
  -> learning/optimization signal
  -> REQUIRE_COMPILE only if semantic family is proven AND executable/verifiable closure exists
```

## Browser primitive closure target

The minimum native Browser kernel should be able to express, without model-authored
JavaScript:

```text
navigate
snapshot / semantic inventory
click_semantic
type_semantic
paste_text_semantic
press
scroll
extract_structured
read_http(GET/HEAD)
wait_semantic
verify/readback
```

Do not create a second browser, BrowserTask store, controller or session authority.

## Dogfood reference Capability

```text
trello.card.update_description_ui(card_url, expected_text)
  navigate(card_url)
  click_semantic("Edit description")
  paste_text_semantic(editor, expected_text, clear=true)
  click_semantic("Save")
  read_http(GET /1/cards/{id}?fields=desc)
  verify hash(desc) == hash(expected_text)
```

The production Browser primitives remain provider-generic; provider-specific composition
belongs in learned capability/skill/routine data.

## Required implementation order

1. **P0.1 Effect truth** — fix `read_preview`; action-sensitive effect contracts.
2. **P0.2 Semantic admission** — remove structural hard-force; tighten target families.
3. **P0.3 Browser primitive closure** — trusted plain-text paste + GET/HEAD readback.
4. **P0.4 One admission owner** — legacy repetition becomes advisory/learning input.
5. **P0.5 Trusted authority + certified dispatcher** — no payload-minted authority.
6. **P0.6 Uncertainty + readiness** — mutation timeout reconciliation + SPA stabilization.
7. **P0.7 Capability dogfood** — verified canary -> deterministic zero-planning fan-out.
8. **P0.8 Qualification** — focused RED/GREEN, Workstation, Electron, Work100, H004/native smoke.

## Required regression contracts

1. `read_preview` is PURE_READ and never increments mutation occurrence state.
2. Mixed preview/browser tools classify read vs mutation by operation.
3. Three structurally similar but semantically different terminal/file operations do not
   `REQUIRE_COMPILE`.
4. Proven same-family mutations retain mandatory compilation when executable closure exists.
5. Rich-text plain-text paste preserves exact newlines in a contenteditable fixture.
6. Paste reacquires a semantic target after rerender; stale refs are not durable identity.
7. Browser readback allows GET/HEAD and rejects mutation verbs/body/unsafe destinations.
8. Large readback spills by reference instead of bloating model context.
9. Request authority cannot increase trusted runtime authority.
10. Routed mutation without a valid certificate cannot reach the primitive dispatcher.
11. Stale certificate is rejected immediately before dispatch.
12. Read timeout retries are bounded; mutable timeout becomes UNCERTAIN.
13. UNCERTAIN mutation is not blindly retried and resumes only after reconciliation.
14. Transient empty SPA snapshot is re-observed with a hard bound.
15. Generic rich-editor fixture proves edit -> paste -> save -> persisted readback -> verify.
16. One canary fans out equivalent items with no LLM call between items.
17. Per-item drift preserves confirmed mutations and returns bounded NEEDS_REASONING.
18. No external/legacy browser fallback is introduced.
19. BrowserTask ownership, leases, TaskRun fencing, prompt caching and canonical commit remain green.

## Explicit non-solutions

Do **not**:
- globally mark `browser_console`, `terminal` or unknown tools read-only;
- treat conversational authorization as proof of arbitrary-code semantics;
- globally bypass Router/policy/approval/verifier;
- hard-code Trello selectors or sleeps into Browser runtime;
- make `@eN` refs durable identity;
- blindly retry timed-out external mutation;
- create another browser/session/task/memory database;
- let request prose mint trusted authority;
- weaken unknown-effect => mutation;
- claim live E2E from provider-free unit tests.

## Exit criterion

Complete only when the reproduced class can move
`novel discovery -> verified canary -> deterministic fan-out`
without a `durable_compile_required <-> PREFLIGHT_REQUIRED` deadlock, arbitrary
JavaScript as promoted implementation, authority escalation or blind retry after an
uncertain mutation.
