# Internal browser controller

Hermes Workstation V1 owns Chromium inside Electron main and exposes that same
runtime to normal Hermes `browser_*` tools through a loopback-only controller.
There is no second browser process and no second task/session store.

## V1 transport

Desktop writes a private descriptor outside the repository:

`%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-control.json` on Windows
(platform-appropriate config roots are used elsewhere).

The descriptor contains:

- protocol version
- Desktop PID
- a `http://127.0.0.1:<ephemeral-port>` controller URL
- a random 256-bit bearer token
- runtime/profile metadata

Endpoints:

- `GET /health`
- `POST /v1/action`

The controller never binds a non-loopback interface and is independent from LAN
Dashboard exposure.

## Routing invariant

```text
browser_* call
  -> internal Workstation Browser
  -> only while unbound + routing enabled: official extension router / legacy backend
```

Any successful internal action binds that task/session to the persistent
Workstation Browser for the rest of the running agent process. If the Desktop
controller then disappears, the call fails closed so recovery can restore the
same profile/tab instead of silently moving work to a different browser.

## Next hardening/integration

- persist `Hermes session -> Kanban task -> run -> browser tab` binding across
  process restarts instead of only the current Desktop/agent lifetime
- emit controller/action events into the durable Workstation Execution Journal
- surface live task/controller state in Dashboard/mobile
- reuse/align additional semantics from the official Hermes browser-extension
  controller where that reduces protocol duplication
- richer popup/SSO and download/upload handling
- recovery E2E: controller/browser crash -> pause -> reconnect -> verify -> resume

Raw CDP stays in Electron main. Renderer code receives only the narrow Browser
IPC bridge and state updates.
