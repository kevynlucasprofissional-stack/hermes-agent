# Third-party notices and reuse decisions

Hermes Agent remains MIT under its upstream license.

## Code/patterns adapted

### browser-use/desktop
Repository: `browser-use/desktop`
License: MIT

Workstation's Electron `WebContentsView` lifecycle, pooling/attach-detach,
background frame-rate and safe parking concepts were studied from
`app/src/main/sessions/BrowserPool.ts`. The Workstation implementation is
rewritten for Hermes's architecture and keeps this attribution.

### abundantbeing/hermes-browser-extension
Repository: `abundantbeing/hermes-browser-extension`
License: MIT

The fail-closed session-binding, tab-lease, reconnect and approval/safety
architecture are design inputs for Workstation. The V1 internal controller uses
a smaller loopback HTTP contract tailored to Electron; it does not copy or claim
wire compatibility with the extension protocol. The full extension is not vendored.

## External dependencies / references, not vendored
- `vercel-labs/agent-browser` — Apache-2.0 — deterministic fallback.
- `browser-use/browser-use` — MIT — Hermes power mode.
- `browser-use/browser-harness` — MIT — Browser Use browser-exec harness.
- `browser-memory/browser-memory` — MIT — procedural-memory reference.
- `apatureai/lattice` — MIT — perception reference.
- `aaronlab/browsertrace` — observability reference.
- `EricFinland/witness` — observability reference.
- `VasuBansal7576/driftlock` — drift/recovery reference.
- `lamenting-hawthorn/browserbench` — transactional safety eval reference.
- `visnia-ai/browsewebapp-bench` — browser workflow eval reference.

## Explicitly reference-only
BrowserOS is AGPL-3.0 and is treated as UX/architecture reference only. No
BrowserOS source is incorporated into the MIT Hermes Workstation patch.
