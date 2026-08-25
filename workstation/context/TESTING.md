# Workstation Testing

A Workstation change is stable only when its **behavioral contract** is proven at the lowest useful layer and the relevant integration path remains green. Typecheck or source-shape checks alone are not proof.

## Validation ladder

Use the smallest focused gate first, then expand only after it passes:

1. **Pure/unit behavior** — extracted logic, state transitions, serialization, routing decisions, host/geometry helpers.
2. **Workstation contracts** — `workstation/tests/` for Python-side routing/config/integration contracts.
3. **Desktop UI tests** — renderer behavior through Vitest/React tests when UI state or actions change.
4. **Desktop platform tests** — Electron/main-process behavior for `WebContentsView`, BrowserRuntime, host ownership, persistence, and IPC contracts.
5. **Desktop typecheck/build gates** — ensure changed contracts compile across renderer/preload/main boundaries.
6. **Windows Desktop E2E/smoke** — required for claims that depend on real Electron/Windows composition, restart, profile persistence, or native view geometry.

Do not replace an executable behavior test with a test that greps `.py`, `.ts`, or `.tsx` source text. Follow the root `AGENTS.md` testing rules.

## Existing Workstation gates

- `Workstation CI`
  - component lock validation;
  - third-party license validation;
  - `workstation/tests/`;
  - downstream integration-anchor check.
- `Workstation Browser Windows`
  - Node/Python setup;
  - Desktop typecheck;
  - Desktop UI tests;
  - Desktop platform/Electron tests.

The Windows workflow must test the **committed tree**. Migration/patch helpers must not repair source before these tests run.

## Required browser-foundation invariants

As the corresponding implementation lands, tests must establish these relationships rather than freeze incidental values:

- a GUI/Desktop session receives its browser surface capability independently of process env identity;
- controller reachability affects execution/recovery, not whether the valid session surface is known to the model;
- a BrowserTask can hide/show/park/focus without creating a replacement live page;
- destroy is explicit and different from hide;
- task-bound controller loss is fail-closed;
- routing-disabled stays internal-only;
- Chat Browser View and Browser Hub reference the same BrowserTask/runtime;
- only one host owns the live `WebContentsView` at a time;
- host transfer/resize updates bounds without overlap;
- multiple BrowserTasks remain isolated;
- BrowserSessionState restoration preserves safe logical metadata without storing credentials;
- Chromium profile persistence is tested separately from logical tab/task restoration;
- Preview compatibility in Workstation mode does not create a second independent browser lane;
- `web_search` remains available for factual non-UI research while explicit visible/authenticated browser work exposes the Workstation Browser contract.

## Manual Windows smoke evidence

For behavior Electron automation cannot reliably prove, record a reproducible smoke procedure and result. The browser foundation's final smoke must cover at least:

1. start a cleanly installed Desktop build;
2. start a browser task from Chat;
3. observe the same task in Chat Browser View and Browser Hub;
4. interact through agent control, then Take Control as a human on the same page;
5. hide and reopen without a new navigation;
6. switch Chat ↔ Browser Hub and resize/maximize/restore without native-view overlap;
7. create a second task and verify isolation;
8. restart Desktop and verify logical tabs/task mappings restore;
9. separately verify compatible login state persists through the dedicated Chromium profile;
10. exercise controller loss for a bound task and verify fail-closed behavior.

Record the exact commit SHA, Windows/Node/Python versions, commands/workflow run, observed result, and any limitation. A manual pass on an unidentifiable build is not durable evidence.

## Failure policy

A red gate is investigated, not disabled. If a pre-existing failure blocks validation, reproduce it, identify whether it is in scope, and either fix it in the narrowest appropriate implementation or record why a different existing gate provides sufficient proof. Never make CI green by deleting coverage for the behavior being changed.