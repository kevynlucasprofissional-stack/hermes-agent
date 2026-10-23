# Site Operations (site-ops) Guide

## Overview

The `site-ops` framework provides a reusable, deterministic layer for automating external websites via Chrome DevTools Protocol (CDP) in Hermes Desktop. It replaces ad-hoc browser automation with a structured three-layer architecture:

1. **Framework** (`site-ops/framework/`) — Reusable CDP client, auto-healing, map loading, and selector resolution
2. **Site Maps** (`site-ops/maps/`) — Baseline element catalogs with stable selectors (versioned in repo)
3. **Operations Scripts** (`site-ops/scripts/site-ops/`) — Fast CLI operations using map selectors
4. **Playbooks** (`site-ops/skills/`) — LLM instructions for when/how to use operations

## Architecture

```
site-ops/
├── framework/
│   ├── cdp-client.mjs        # CDP connection + eval wrapper (class-based)
│   ├── auto-heal.mjs         # Generic selector failure → re-map → retry logic
│   ├── map-loader.mjs        # Baseline + local override resolution by site slug
│   └── selector-resolver.mjs # Priority-based selector lookup (testId > aria-label > role > text)
├── maps/
│   └── whatsapp-web.json     # Baseline element catalog (versioned)
├── skills/
│   └── whatsapp-web-ops/     # Playbook for LLM
│       └── SKILL.md
└── scripts/
    ├── site-deep-map.mjs     # Recursive UI mapper for external sites
    └── site-ops/
        └── whatsapp-web.mjs  # Deterministic WhatsApp Web operations
```

## Quick Start

### Prerequisites

- Hermes Desktop running with CDP enabled (port 9222 by default)
- Target site open in Hermes browser (e.g., `web.whatsapp.com`)

### CLI Usage

```bash
# Check deep map status
node site-ops/scripts/site-deep-map.mjs status "web.whatsapp.com"

# Initialize deep map for a site
node site-ops/scripts/site-deep-map.mjs init "web.whatsapp.com"

# Scan current screen
node site-ops/scripts/site-deep-map.mjs scan "web.whatsapp.com"

# WhatsApp Web operations
node site-ops/scripts/site-ops/whatsapp-web.mjs get-unread-count
node site-ops/scripts/site-ops/whatsapp-web.mjs open-chat "Contact Name"
node site-ops/scripts/site-ops/whatsapp-web.mjs send-message "Hello world"
```

### Via Desktop IPC (Renderer)

```typescript
// In renderer process (preload exposes window.hermesDesktop.siteOps)
const result = await window.hermesDesktop.siteOps.execute(
  'whatsapp-web',
  'get-unread-count',
  [],
  { timeoutMs: 30000, sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' }
)

if (result.success) {
  console.log('Unread:', result.data.unreadCount)
} else {
  console.error('Failed:', result.error)
}
```

## Auto-Healing Protocol

When any operation fails due to stale/missing selectors:

1. **Detect** — Script throws error with failed selector
2. **Re-map** — Runs `site-deep-map.mjs init + scan` for the site
3. **Update local override** — Saves new map to `.claude/site-maps/<site>.local.json`
4. **Retry** — Re-runs the failed operation once with updated selectors
5. **Report** — Logs what changed; escalates if retry still fails

### Configuration

Auto-heal behavior is configured per-operation via `healOptions`:

```javascript
const healOptions = {
  sitePattern: 'web.whatsapp.com',  // CDP target URL pattern
  siteSlug: 'whatsapp-web'          // Site slug for map/artifact paths
}
```

### Guards (Prevent Infinite Loops)

- **Max 1 retry** per operation
- **30s cooldown** between heals (per site)
- **Max 3 heals** per session before escalation to user

## Adding a New Site

### 1. Create Site Map Baseline

```bash
# Open the site in Hermes browser
# Then run:
node site-ops/scripts/site-deep-map.mjs init "example.com"
node site-ops/scripts/site-deep-map.mjs scan "example.com"
# Output: workstation/dogfood/artifacts/site-map-example-com.json
```

### 2. Commit Baseline Map

```bash
cp workstation/dogfood/artifacts/site-map-example-com.json site-ops/maps/example-com.json
git add site-ops/maps/example-com.json
```

### 3. Create Operations Script

```javascript
// site-ops/scripts/site-ops/example-com.mjs
import { CdpClient } from '../../framework/cdp-client.mjs'
import { loadSiteMap } from '../../framework/map-loader.mjs'
import { withAutoHealing } from '../../framework/auto-heal.mjs'
import { findElement, resolveSelector } from '../../framework/selector-resolver.mjs'

const SITE_SLUG = 'example-com'
const SITE_PATTERN = 'example.com'

const client = new CdpClient()

async function myOperation(param) {
  const map = loadSiteMap(SITE_SLUG)
  const element = findElement(map, e => e.ariaLabel?.includes('My Button'))
  const selector = resolveSelector(element)
  await client.eval(`document.querySelector('${selector}')?.click()`)
  return { success: true }
}

// Main dispatch...
```

### 4. Create Playbook Skill

```markdown
---
name: example-com-ops
description: Native Example.com operations via CDP
version: 1.0.0
native: true
site_map: site-ops/maps/example-com.json
operations_script: site-ops/scripts/site-ops/example-com.mjs
deep_map_script: site-ops/scripts/site-deep-map.mjs
---

# Example.com Operations — Native Skill
...
```

### 5. Register in Build System

The `site-ops/` directory is automatically included in the agent payload via `RESOURCE_ENV["site-ops"] = "HERMES_SITE_OPS"` in `scripts/build/inputs.py`.

## API Reference

### `CdpClient` (framework/cdp-client.mjs)

```javascript
const client = new CdpClient()

// Find CDP target by URL pattern
const target = await client.findTarget('web.whatsapp.com')

// Connect to target
await client.connect(target)

// Evaluate expression in target context
const result = await client.eval(`document.querySelector('button')?.click()`)

// Close connection
client.close()
```

### `loadSiteMap(slug)` (framework/map-loader.mjs)

```javascript
const map = loadSiteMap('whatsapp-web')
// Returns map object with screens.main.elements[]
```

### `findElement(map, predicate)` (framework/selector-resolver.mjs)

```javascript
const element = findElement(map, e => e.ariaLabel?.includes('Search'))
// Returns element with selector property
```

### `resolveSelector(element)` (framework/selector-resolver.mjs)

```javascript
const selector = resolveSelector(element)
// Returns CSS selector string (testId > aria-label > id > role > text)
```

### `withAutoHealing(operationName, operationFn, options)` (framework/auto-heal.mjs)

```javascript
const result = await withAutoHealing('my-op', () => myOperation(), {
  sitePattern: 'web.whatsapp.com',
  siteSlug: 'whatsapp-web'
})
```

### IPC API (Renderer → Main)

```typescript
// Execute site operation
await window.hermesDesktop.siteOps.execute(site, operation, args?, options?)

// Run deep map command
await window.hermesDesktop.siteOps.deepMap(command, sitePattern)

// Cancel running operation
await window.hermesDesktop.siteOps.cancel(procId?)
```

## Security

- **Allowed contacts for WhatsApp testing**: Only "Kevyn ACIRV" and "+55 64 9247-0988 (Você)"
- **CDP port**: Loopback only (127.0.0.1:9222), never exposed off-host
- **AI Control**: Requires `window.__hermesAiControlActive === true` for destructive actions
- **Human override**: "Take Human Control" button in Browser pane immediately reclaims control

## Troubleshooting

### CDP Connection Failed

```bash
# Check if Desktop is running with CDP
curl http://127.0.0.1:9222/json

# Check HERMES_DESKTOP_CDP_PORT
echo $HERMES_DESKTOP_CDP_PORT
```

### WhatsApp Web Target Not Found

- Ensure WhatsApp Web is open in Hermes browser (not external browser)
- Run `node site-ops/scripts/site-deep-map.mjs status "web.whatsapp.com"` to verify

### Selectors Stale / Auto-Heal Not Working

- Check `.claude/site-maps/whatsapp-web.local.json` exists and is valid JSON
- Verify artifact map exists: `workstation/dogfood/artifacts/site-map-web-whatsapp-com.json`
- Run manual re-map: `node site-ops/scripts/site-deep-map.mjs init "web.whatsapp.com" && node site-ops/scripts/site-deep-map.mjs scan "web.whatsapp.com"`

### IPC Timeout

- Increase `timeoutMs` in options (default: 60000ms)
- Check CDP connection health
- Verify site-ops scripts work via CLI first

## File Locations

| File | Purpose |
|------|---------|
| `site-ops/framework/*.mjs` | Reusable framework modules |
| `site-ops/maps/*.json` | Baseline site maps (committed) |
| `site-ops/skills/*/SKILL.md` | Playbooks for LLM |
| `site-ops/scripts/site-deep-map.mjs` | Deep mapping tool |
| `site-ops/scripts/site-ops/*.mjs` | Deterministic operation CLIs |
| `.claude/site-maps/*.local.json` | Auto-healed local overrides (gitignored) |
| `workstation/dogfood/artifacts/site-map-*.json` | Generated artifacts |
| `apps/desktop/electron/ipc/site-ops.ts` | IPC handler (main process) |
| `apps/desktop/electron/preload.ts` | Renderer API exposure |

## Testing

```bash
# Run E2E tests (requires Desktop + WhatsApp Web open)
python -m pytest workstation/tests/test_site_ops_e2e.py -v

# Or run standalone test
python workstation/tests/test_site_ops_e2e.py
```

## Contributing

1. Follow the three-layer architecture
2. Prefer `data-testid` > `aria-label` > `role` > text selectors
3. Always implement auto-healing for new operations
4. Update playbook (`SKILL.md`) when adding capabilities
5. Test with CLI before IPC integration
6. Document new sites in this guide