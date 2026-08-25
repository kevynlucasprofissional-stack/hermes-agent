# Workstation Constraints

These constraints apply to Workstation changes in addition to the repository-wide rules in `AGENTS.md`.

## State and ownership

- Do not create a second SessionDB, Kanban, Memory system, approval system, or browser-routing control plane when Hermes already owns that concern.
- Do not duplicate Browser state to keep two independent pages “in sync”. BrowserTask is the semantic owner; UI surfaces are views/hosts.
- A live `WebContentsView` belongs to at most one active host at a time.
- Distinguish process-scoped, profile-scoped, Hermes-session-scoped, BrowserTask-scoped, and renderer/view-scoped state explicitly.
- Closing/hiding a view must not imply destroying the BrowserTask unless the user or lifecycle explicitly requests destruction.

## Browser profile and secrets

- Never reuse a user's personal Chrome/Edge profile for Workstation automation.
- Persistent Chromium profile data stays outside Git/source control and is managed by the dedicated Electron session/partition.
- BrowserSessionState may persist safe structural metadata only. Do not persist passwords, typed secrets, page-extracted access tokens, sensitive form values, or screenshots in that state file.
- Local controller secrets/tokens must not be logged or committed.

## Network and control

- Local Workstation controllers bind to loopback by default. Expanding exposure beyond localhost requires an explicit security design and is out of scope for the browser-foundation phase.
- A BrowserTask already bound to the Workstation controller is fail-closed if that controller disappears. Do not silently fall back to another browser/runtime.
- `routing.enabled: false` remains internal-only behavior; it must not unexpectedly route to external automation.

## Agent/tool contract

- GUI/browser surface availability is resolved from the Hermes session/platform, not `HERMES_DESKTOP` or another process environment proxy.
- Process-wide `check_fn` caching must not encode per-session surface identity.
- Keep prompt/tool schemas stable during a conversation in accordance with Hermes prompt-caching rules.
- `web_search` remains distinct from visible/authenticated browser interaction; do not eliminate it to force browser use.

## Human control and approvals

- Human `Take Control` and agent control operate on the same BrowserTask/page.
- Existing Hermes approval/security gates remain authoritative for sensitive actions. Workstation must not bypass approvals merely because the page is locally visible.
- Pause/resume/stop/focus/control ownership semantics must remain recoverable and explicit.

## Upstream maintenance

- Prefer extending existing code over adding parallel managers or frameworks.
- Every edit to an upstream-owned integration point must have a concrete consumer, a behavior test, and an entry in `workstation/UPSTREAM_DELTA.md` when it changes the maintained downstream delta.
- Normal install/CI validates committed source; it must not auto-heal missing downstream edits before tests run.
- Keep dependencies pinned and license policy intact.

## Scope boundary for the browser-foundation phase

Do not use browser-foundation work as an excuse to implement the later Kanban automation layer, full execution reports, LAN/QR/Tailscale access, Browser Memory, Perception Engine V2, Browser4, or Lightpanda. Those features depend on a proven unified Browser foundation.