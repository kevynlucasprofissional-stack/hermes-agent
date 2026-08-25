# Hermes Workstation

Hermes Workstation is a thin downstream distribution of
`NousResearch/hermes-agent`. The upstream Hermes architecture remains the source
of truth for sessions, Kanban, memory, skills, Gateway, Desktop and Dashboard.
Workstation adds tightly integrated product capabilities rather than parallel
state.

## V1 invariants

1. **One Hermes state.** No Workstation session DB, task DB or memory DB when
   Hermes already owns that state.
2. **Browser is first-class.** The Desktop exposes `/browser` directly in core
   navigation.
3. **No external Chrome dependency.** The primary Browser runtime uses the
   Chromium bundled with Electron via `WebContentsView`.
4. **Persistent browser identity.** The Browser uses a dedicated Electron
   `Session` stored outside the repository.
5. **Background capable.** Browser WebContents survive route changes. The UI
   attaches/detaches the native view; it does not destroy the browser.
6. **Fail closed after binding.** A task bound to the internal browser pauses
   and recovers there; it never silently moves to another backend.
7. **Kanban is the task source of truth.** Multistep Workstation work maps to
   Hermes Kanban cards.
8. **Risk gates.** Sensitive/irreversible browser actions require approval.
9. **Evidence and reports.** Browser work produces a journal plus structured
   completion metadata.
10. **Upstream delta stays visible.** Every core change is documented in
    `UPSTREAM_DELTA.md`.

## Apply the initial integration

From the root of your clean Hermes fork:

```powershell
powershell -ExecutionPolicy Bypass -File .\workstation\install.ps1
```

For development:

```powershell
powershell -ExecutionPolicy Bypass -File .\workstation\start.ps1
```

The initial patch provides a functional in-app Chromium Browser surface **and**
a loopback-authenticated controller used by Hermes `browser_*` tools. Internal
Chromium is the first browser lane; the official extension router and legacy
backend are fallback lanes only while routing is enabled and the task has not
bound to the persistent internal browser.

Automatic Kanban promotion/orchestration, LAN settings UI and durable Execution
Journal persistence are the next integrations. Their contracts and schemas are
already staged here so those features extend Hermes state instead of creating
parallel state stores.

See `ARCHITECTURE.md`, `ROADMAP.md`, and `UPSTREAM_DELTA.md`.
