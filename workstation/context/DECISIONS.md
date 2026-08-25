# Architectural Decisions

These are settled decisions for the Hermes Workstation downstream architecture. They narrow implementation choices; they are not a substitute for the detailed design in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## D-001 — Workstation is first-class in this downstream fork

Hermes Workstation is part of this fork's product architecture, not a temporary ZIP overlay. The committed `main` tree is the canonical integrated source for this downstream. Upstream synchronization remains deliberate and tracked.

## D-002 — Preserve Hermes upstream and extend existing ownership

Use Hermes Sessions, Gateway, tool registry/toolsets, approvals, memory, Kanban, profile handling, and browser routing instead of introducing parallel stores or control planes. Downstream edits to upstream-owned files must stay small, explicit, tested, and recorded in `UPSTREAM_DELTA.md`.

## D-003 — The internal browser is Electron Chromium

The primary Workstation Browser uses Electron's Chromium runtime through `WebContentsView` and a dedicated persistent Electron session/partition. Do not reuse the user's personal Chrome/Edge profile.

## D-004 — Browser profile state and BrowserSessionState are different

The Chromium profile owns browser-managed state such as cookies, localStorage, IndexedDB, cache, and compatible authentication state. Workstation BrowserSessionState owns only safe structural metadata such as logical tabs, active tab, BrowserTask linkage, URL/title/order/status, and related identifiers. Never conflate the two stores.

## D-005 — One BrowserTask owns one live page

A BrowserTask represents the durable semantic ownership of an automated web task. It may be hidden, parked, focused, or moved between hosts without navigating again. The same task must not be represented by two independently navigated live pages.

## D-006 — Chat Browser View and Browser Hub are views of the same runtime

The contextual Chat Browser View and the global Browser Hub expose the same BrowserRuntime/BrowserTask state. A live `WebContentsView` has one active host at a time; the other surface represents the task with state/card/thumbnail rather than duplicating the page.

## D-007 — Do not create second SessionDB, Kanban, or Memory systems

BrowserTask may reference Hermes session/run/agent identifiers, but it does not own a replacement session database. Workstation planning/execution features must reuse the existing Kanban and Memory abstractions when those features are later introduced.

## D-008 — Bound Browser tasks fail closed

Once a task is bound to the Workstation Browser/controller, loss of that controller must not silently move the task to a different browser/runtime with different authentication or page state. Recovery is explicit. Unbound requests may use configured fallback according to routing policy.

## D-009 — Surface capability is session-scoped

Whether a Desktop/GUI session should know about a GUI/browser surface is a property of the session/platform contract, not of process environment variables or a process-wide cached reachability probe. Reachability may gate execution/recovery, but must not silently erase a valid session surface from the model schema.

## D-010 — BrowserRuntime remains an abstraction boundary

Do not make Workstation business logic depend irreversibly on one concrete browser implementation. Electron Chromium is the current primary runtime, while the BrowserRuntime/controller boundary should remain explicit enough for future specialist runtimes without duplicating state or changing BrowserTask semantics.

## D-011 — Main is tested as committed

Installation and CI must validate the source committed in this downstream `main`. Migration/rebase helpers may exist, but normal install/test paths must not silently rewrite tracked source before validation; otherwise a missing integration can be hidden by the test harness itself.

## Changing a decision

A replacement decision must state which decision it supersedes, why the old invariant no longer holds, how migration/backward compatibility is handled, and which tests prove the new contract. Do not silently drift architecture through implementation-only changes.