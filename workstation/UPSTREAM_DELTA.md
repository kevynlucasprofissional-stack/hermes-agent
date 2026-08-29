# Hermes Workstation upstream delta

Base: `NousResearch/hermes-agent@057dcdf236f8a6a26721c10fcc6ccb72726e272a`

| ID | Area | Downstream change | Why core-level | Upstream candidate |
|---|---|---|---|---|
| HW-001 | Desktop main | Load Workstation Browser runtime IPC | Browser is a first-class Desktop subsystem | Maybe |
| HW-002 | Desktop preload | Expose narrow Browser runtime bridge | Native view is owned by Electron main | Maybe |
| HW-003 | Desktop routes/sidebar | Add `/browser` as core page/nav item | Workstation Browser is non-optional in this distribution | No |
| HW-004 | Desktop surfaces | Render Browser page as built-in workspace page | Same reason as HW-003 | No |
| HW-005 | Desktop Kanban plugin | Enable bundled Kanban by default | Kanban is Workstation task source of truth | Maybe |
| HW-006 | global.d.ts | Type the Browser IPC bridge | Required by HW-002 | Maybe |
| HW-007 | Browser tool registry | Prefer Workstation Chromium before extension/legacy lanes | Browser must be a first-class agent capability | Yes |
| HW-008 | CLI config example | Document `browser.workstation` defaults | Makes routing/fail-closed behavior explicit | Yes |
| HW-009 | Root `AGENTS.md` | Point coding agents at the downstream Workstation operational context/read-order | Prevents downstream architecture changes from being made from upstream-only context | No |
| HW-010 | GitHub Actions | Windows Workstation gate installs/tests the committed downstream tree, exposes focused BrowserTask lifecycle results, and fails if install dirties the checkout | Prevents CI from silently repairing source and keeps scoped native-browser regressions visible beside known broad Windows failures | Maybe |
| HW-011 | Tool schema assembly / registry | Preserve selected Workstation Browser schemas from session-scoped Desktop capability and fingerprint that capability in the tool-definition cache | One gateway serves multiple client surfaces; transient controller reachability must not erase a valid Desktop schema or leak it across sessions | Yes |
| HW-012 | Desktop Browser runtime / BrowserTask lifecycle | Add first-class BrowserTask metadata/lifecycle (`create`, `show`, `hide`, `park`, explicit `destroy`, crash recovery and safe logical restart restoration) around the existing `taskTabs` + `BrowserEntry.ownerTaskId` page ownership primitives, with focused runtime/persistence regression tests | BrowserTask semantics must be owned where Electron `WebContentsView` lifetime and task→page binding are enforced; implementing it only in downstream wrapper code would duplicate browser state or lose native lifecycle control | Maybe |

Operational context, engineering journal/probes, tests, migration helpers, and other files under `workstation/` are downstream-owned and do not add rows by themselves. Keep this list small. New edits outside `workstation/` require a row or an explicit expansion of an existing row.

## Implementation 4 evidence boundary

HW-012 was validated by the focused automated BrowserTask tests and the real Windows/Electron lifecycle smoke recorded in `workstation/context/TESTING.md` and `workstation/context/engineering-journal/CURRENT.md`. The native smoke proves BrowserTask lifecycle/restart semantics only; it does not make future Browser Hub, Chat Browser View, Preview unification, complete BrowserSessionState, or single-host transfer part of this delta yet.
