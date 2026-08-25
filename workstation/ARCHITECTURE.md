# Hermes Workstation Architecture

## Product boundary

```text
Hermes Desktop / Dashboard
        |
        v
Hermes Gateway + Sessions + Kanban + Memory + Skills
        |
        +---------------- Browser Router ----------------+
        |                    |                           |
        v                    v                           v
Internal Browser       extension/agent-browser     browser_exec
(Electron Chromium)    optional fallback lanes     adaptive/power
        |
        v
persistent Electron Session
        |
        v
task binding + controller + journal + safety
```

### Internal Browser

The primary Workstation browser is not a second application. Hermes Desktop is
Electron, therefore it already ships an open-source Chromium runtime. Workstation
creates a dedicated Electron `Session` and manages one or more
`WebContentsView`s in the Desktop main process.

This is deliberately different from the existing Preview `<webview>`:

- Preview is a chat-adjacent rendering surface.
- Workstation Browser is a long-lived runtime owned by main.
- route changes only detach the view; WebContents keep running.
- all tabs share one persistent browser profile.
- agent control uses the same WebContents through CDP via a loopback-only authenticated controller.
- the profile does not share Hermes Desktop cookies.

Default Windows profile:

`%LOCALAPPDATA%\HermesWorkstation\Browser\User Data`

Linux/macOS use platform-appropriate configuration roots.

### BrowserRuntime abstraction

The product-level browser contract is runtime-neutral:

- `electron-chromium` — V1 primary, visible + persistent + background
- `agent-browser` — deterministic disposable fallback
- `browser-exec` — adaptive/power mode via Hermes Browser Use path
- `lightpanda` — future ultra-light headless runtime

Routing is configurable. When routing is disabled, Workstation uses only the
internal browser.

### Task lifecycle

```text
chat request
  -> classify as multistep/asynchronous work
  -> create Hermes Kanban card
  -> bind session/run/card
  -> choose BrowserRuntime if browser capability is needed
  -> journal actions/evidence
  -> create follow-up cards when discovered
  -> execute child only when required for parent
  -> complete card with summary + structured metadata
  -> report back into the originating chat
```

A discovered task must retain:

`parent_task_id`, `discovered_by`, `reason`, `evidence`,
`origin_session_id`.

### Safety

A browser task already bound to the internal runtime never silently fails over.
If browser/controller connectivity is lost:

`pause -> health/reconnect -> rebind -> verify -> resume`

Sensitive side effects cross an approval gate. The default policy covers
payments, send/publish, delete, contracts/terms, credentials/permissions,
money movement, irreversible actions and secrets entering a new context.

### LAN/mobile

LAN reuses the official `hermes dashboard` backend. It must never create a
second Workstation server or a second state store. Non-loopback bind is
fail-closed unless an official Hermes dashboard auth provider is configured.

V1 target:

`Desktop toggle -> auth verification -> dashboard bind -> IP detection -> QR`

Tailscale is V1.1.

## Source reuse

We adapt concepts/code only where that is architecturally valuable:

- `browser-use/desktop` MIT: WebContentsView pool/parking/lifecycle patterns.
- `hermes-browser-extension` MIT: browser-controller protocol, leases, safety,
  approvals and reconnect patterns.
- `browser-memory` MIT: procedural memory lifecycle, interface only in V1.
- `lattice` MIT: compact perception contract, interface only in V1.
- BrowserTrace/Witness/Driftlock: journal/replay/drift design references.
- BrowserOS: UX reference only; AGPL code is not incorporated.

See `THIRD_PARTY_NOTICES.md`.

## V1 controller and routing order

```text
browser_* tool call
  -> Workstation router
     -> internal Electron Chromium when available
     -> if unavailable AND task is unbound AND routing is enabled:
          official Hermes extension router
          -> legacy local/cloud backend
     -> if task is already bound OR routing is disabled:
          fail closed and recover the internal runtime
```

The controller descriptor contains a random bearer token and loopback URL and is
written outside the repository with private-file permissions where supported.
It is never exposed through LAN mode. A successful internal browser action binds
the task/session to that runtime for the remainder of the process.
