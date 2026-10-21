# AI Control Guide — Hermes Desktop CDP

This document describes how Claude Code interacts with the running Hermes
Desktop renderer via Chrome DevTools Protocol (CDP) during development.

## Prerequisites

- `npm run dev` running in `apps/desktop` (Vite on `http://127.0.0.1:5174`).
- Renderer debugging port active on `http://127.0.0.1:9222` (default; opt out
  with `HERMES_DESKTOP_CDP_PORT=off`). See `electron/dev-cdp.ts`.
- The badge "🤖 AI Control" visible in the top-right corner of the app window
  confirms AI control mode is active. Toggle with **Ctrl+Shift+A**.

## Base command

```bash
node apps/desktop/scripts/eval.mjs "<expression>"
```

Override the port: `HERMES_DESKTOP_CDP_PORT=9333 node apps/desktop/scripts/eval.mjs "..."`.

The script connects to the first page target whose URL contains `5174` (the
Vite dev server), evaluates the expression with `awaitPromise: true`, and
prints the JSON-serialized result to stdout. Exceptions go to stderr.

## Reading state

```bash
# Window title
node apps/desktop/scripts/eval.mjs "document.title"

# Current URL / hash route
node apps/desktop/scripts/eval.mjs "location.href"

# Chat input value
node apps/desktop/scripts/eval.mjs "document.querySelector('[data-testid=\"chat-input\"]')?.value"

# Button label
node apps/desktop/scripts/eval.mjs "document.querySelector('button[type=\"submit\"]')?.textContent?.trim()"

# AI control flag (always check before destructive actions)
node apps/desktop/scripts/eval.mjs "window.__hermesAiControlActive"
```

## Writing / interacting

```bash
# Click a button
node apps/desktop/scripts/eval.mjs "document.querySelector('button.submit')?.click()"

# Fill an input (React-compatible)
node apps/desktop/scripts/eval.mjs "(() => { const el = document.querySelector('input[name=\"q\"]'); if (!el) return false; const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; nativeInputValueSetter.call(el, 'search term'); el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"

# Dispatch a keyboard shortcut
node apps/desktop/scripts/eval.mjs "document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }))"

# Navigate within the SPA
node apps/desktop/scripts/eval.mjs "history.pushState(null, '', '/settings')"
```

## Coordination rule

Before any destructive action (click, fill, navigate, dispatch), verify:

```bash
node apps/desktop/scripts/eval.mjs "window.__hermesAiControlActive"
```

Only proceed when the result is `true`. When `false` or absent, the human has
control — limit yourself to read-only expressions. The user toggles the flag
with **Ctrl+Shift+A**; the badge in the top-right corner reflects the current
state.

## Logging test actions

When executing a test step, log it so the user can observe progress in the
DevTools Console (F12) or the Vite terminal:

```bash
node apps/desktop/scripts/eval.mjs "console.log('[AI-TEST]', 'click', 'submit-button', true)"
```

## Injecting Prompts into the Hermes Internal AI

The Hermes Desktop renderer has its own internal AI agent. You can send it
prompts programmatically via CDP — this is the primary mechanism for
orchestrating the Hermes AI from an external Claude Code session.

### Why not Kanban/SQLite directly?

Inserting tasks directly into the Kanban SQLite database does **not** trigger
the Hermes AI. The backend requires UI-level notification that only fires when
a message is submitted through the renderer's input field. CDP injection
through the chat input is the reliable path.

### Step-by-step: send a prompt to the Hermes AI

1. **Verify AI Control is active:**

   ```bash
   node apps/desktop/scripts/eval.mjs "window.__hermesAiControlActive"
   ```

   Must return `true`. If `false`, ask the user to press **Ctrl+Shift+A**.

2. **Locate the chat input field:**

   ```bash
   node apps/desktop/scripts/eval.mjs "document.querySelector('div[role=\"textbox\"][aria-label=\"Message\"]') !== null"
   ```

3. **Inject the prompt text (paste event for React compatibility):**

   ```bash
   node apps/desktop/scripts/eval.mjs "(() => { const el = document.querySelector('div[role=\"textbox\"][aria-label=\"Message\"]'); if (!el) return 'NOT_FOUND'; el.focus(); const text = 'YOUR_PROMPT_HERE'; const dataTransfer = new DataTransfer(); dataTransfer.setData('text/plain', text); el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dataTransfer, bubbles: true, cancelable: true })); return 'INJECTED'; })()"
   ```

4. **Send the message (dispatch Enter):**

   ```bash
   node apps/desktop/scripts/eval.mjs "(() => { const el = document.querySelector('div[role=\"textbox\"][aria-label=\"Message\"]'); if (!el) return false; el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true })); return true; })()"
   ```

5. **Verify receipt and monitor execution:**

   - Check for new journal files in `workstation/dogfood/artifacts/journals/`.
   - Inspect the UI thread for assistant action summaries.
   - Search trace artifacts under `workstation/dogfood/artifacts/` for detailed
     tool call evidence (journal `.jsonl` may only show high-level events).

### Journal structure notes

- Journal files use the naming pattern `YYYYMMDD_HHMMSS_microseconds.jsonl`.
- High-level `adaptive_observation` events may lack explicit tool names; actual
  tool invocations appear in linked trace artifacts.
- To confirm specific tool usage, search artifact traces or check UI messages.

## Known limitations (MVP)

- **No native screenshot.** `Page.captureScreenshot` requires extending
  `eval.mjs`; deferred to Cycle 2. Use `preview_screenshot` from the Browser
  pane when visual verification is needed.
- **No wait-for-selector.** Poll manually with repeated `eval.mjs` calls when
  waiting for async UI updates.
- **No structured error handling.** Failures print to stderr; parse exit code
  and output in the calling shell.
- **Loopback only.** Port 9222 binds to `127.0.0.1`; never expose off-host.
- **Dev only.** Packaged builds disable the debugging port unconditionally.
- **Cooperative coordination.** The `__hermesAiControlActive` flag is a
  convention, not an enforcement mechanism. A malicious or buggy script can
  ignore it. This is acceptable for local dogfooding; do not ship as a
  security boundary.

## Files

- `apps/desktop/scripts/eval.mjs` — CDP eval CLI.
- `apps/desktop/electron/dev-cdp.ts` — debugging port gate.
- `apps/desktop/src/app/shell/AiControlBadge.tsx` — badge + toggle.
- `apps/desktop/src/app/contrib/controller.tsx` — badge mount point.