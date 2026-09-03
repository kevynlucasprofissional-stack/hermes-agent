# Reverting or Toggling Upstream Browser Isolation in Hermes Workstation

This document provides clear, step-by-step instructions to understand, toggle, or fully revert the decision to isolate upstream browser backends from Hermes Workstation.

---

## 1. What was Isolated & Why

### The Context
Upstream Hermes includes a legacy browser automation stack based on:
1. `agent-browser` (an npm CLI package wrapping Playwright that spawns an external Chromium window or runs headless).
2. `browser-use` CLI (`browser_exec`).
3. `open_preview` / `drive_preview` in `desktop_ui` (a separate preview pane beside chat).

### The Problem in Hermes Workstation
Hermes Workstation features its own first-class, embedded Electron Chromium browser with the **Browser Hub** and contextual **Chat Browser View** (`tools/browser_workstation.py` + `apps/desktop/electron/workstation-browser-runtime.ts`). 

When a user asked *"Entra no browser hub e abre o trello"*:
- The LLM previously saw ambiguous descriptions pointing to generic browser automation or `open_preview`.
- Fallback routing (`workstation_routing_enabled()`) could silently fall back to spawning external `agent-browser` / Playwright processes if the internal controller had a momentary hiccup or unbound state.

### The Changes Applied
1. **Disabled Fallback (Fail-Closed)**: `workstation_routing_enabled()` now defaults to `False`. Workstation sessions will never fall back to upstream Playwright or `agent-browser`.
2. **Dedicated Tool Descriptions**:
   - `browser_navigate`: Explicitly describes controlling the **Hermes Workstation Browser (Browser Hub / Embedded Chromium)**, clarifying that requests like *"entra no browser hub e abre o trello"* or *"abra o site X"* use this tool.
   - `browser_snapshot`: Explicitly describes capturing snapshots from the **Hermes Workstation Browser**.
   - `open_preview`: Clarified as being reserved strictly for previewing local files (HTML/markdown) and localhost dev servers, directing interactive web navigation to `browser_navigate`.
3. **Resilient Tab Adoption**: In Electron `workstation-browser-runtime.ts`, `browser_snapshot` automatically adopts an active open tab in the Browser Hub or re-hydrates a parked tab rather than erroring with `no_bound_browser_tab`.

---

## 2. How to Revert or Toggle Without Touching Code

You do **not** need to touch source code if you only want to re-enable upstream fallbacks or switch modes.

### Option A: Re-enable Upstream Browser Fallback (Allowing Workstation to Fall Back to Playwright)
If you want Hermes Workstation to attempt the internal browser first, but fall back to the upstream `agent-browser` (Playwright) if the internal browser is unavailable:

1. In `~/.hermes/config.yaml`, add:
   ```yaml
   browser:
     workstation:
       routing_enabled: true
   ```
   *Or* set the environment variable in your shell/launcher:
   ```powershell
   $env:HERMES_WORKSTATION_BROWSER_ROUTING = "1"
   ```

### Option B: Completely Disable Workstation Browser (Restore 100% Upstream Browser)
If you ever want to turn off the Workstation Browser entirely and revert to standard upstream Hermes behavior across the board:

1. In `~/.hermes/config.yaml`, set:
   ```yaml
   browser:
     workstation:
       enabled: false
   ```
   *Or* set the environment variable:
   ```powershell
   $env:HERMES_WORKSTATION_BROWSER = "0"
   ```
When `HERMES_WORKSTATION_BROWSER=0`:
- `workstation_browser_enabled()` returns `False`.
- All `browser_*` tools immediately dispatch through upstream `agent-browser` / `routed_browser_handler`.
- Upstream tools like `browser_cdp` and `browser_dialog` regain their standard upstream behavior.

---

## 3. How to Revert the Code Changes via Git

If you want to completely undo the code modifications made in this iteration:

1. Check git status to see the modified files:
   ```bash
   git status
   ```
2. The specific files changed were:
   - `tools/browser_workstation.py`
   - `tools/browser_tool.py`
   - `tools/open_preview_tool.py`
   - `apps/desktop/electron/workstation-browser-runtime.ts`
   - `workstation/config.py`
   - `workstation/tests/test_browser_workstation_route.py`

3. To revert the commit from git history:
   ```bash
   git revert HEAD
   ```
   *Or* to discard uncommitted changes in those files:
   ```bash
   git checkout HEAD -- tools/browser_workstation.py tools/browser_tool.py tools/open_preview_tool.py apps/desktop/electron/workstation-browser-runtime.ts workstation/config.py workstation/tests/test_browser_workstation_route.py
   ```
