# Workstation roadmap

## Foundation — included in this patch
- `workstation/` architecture, contracts, policies and upstream tracking.
- first-class `/browser` route in Hermes Desktop.
- internal Electron Chromium Browser runtime with dedicated persistent profile.
- multiple tabs, navigation, attach/detach, background survival and cache-only maintenance.
- pause/resume, focus, take/release control primitives.
- loopback-only bearer-authenticated Browser controller in Hermes Desktop.
- `browser_*` integration that prefers internal Chromium and fails closed after task binding.
- Kanban Desktop enabled by default in this downstream distribution.
- stable/edge channel metadata.
- CI skeleton, lock/license validation and Windows Browser E2E workflow.
- eval matrix prepared for internal/agent-browser/browser-exec.

## V1 next
1. Persist controller/session/run/Kanban identity bindings across process restarts.
2. Promote multistep requests into Kanban automatically.
3. Add follow-up task discovery metadata and parent dependency policy.
4. Add Workstation Execution Journal persistence and selective screenshots.
5. Generate browser task completion reports into `kanban_complete(metadata=...)`.
6. Add Browser live task rail in Desktop and Dashboard/mobile.
7. Add LAN settings page/toggle with auth preflight, IP and QR.
8. Add richer popup/SSO handling and download/upload UX.
9. Recovery E2E: crash controller/browser -> pause -> reconnect -> verify -> resume.
10. Windows clean-install E2E.

## V1.1
- Tailscale integration.
- optional external Hermes Browser Extension compatibility mode.
- richer cache/resource maintenance.
- download/upload UX.
- multi-task browser tab ownership.

## V2
- procedural web memory (`discover -> run -> explore -> learn`).
- provenance-aware compact perception engine inspired by Lattice.
- drift diagnosis and governed adaptation.
- Lightpanda runtime for ultra-light headless tasks.
