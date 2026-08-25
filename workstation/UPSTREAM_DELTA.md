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
| HW-010 | GitHub Actions | Windows Workstation gate installs and tests the committed downstream tree and fails if install dirties the checkout | Prevents CI from silently repairing downstream source before validating it | Maybe |

Operational context, tests, migration helpers, and other files under `workstation/` are downstream-owned and do not add rows by themselves. Keep this list small. New edits outside `workstation/` require a new row.
