---
name: whatsapp-web-ops
description: Native WhatsApp Web operations via CDP with auto-healing site map
version: 1.0.0
native: true
auto_update: true
site_map: assets/site-maps/whatsapp-web.json
operations_script: scripts/site-ops/whatsapp-web.mjs
deep_map_script: scripts/site-deep-map.mjs
---

# WhatsApp Web Operations — Native Skill

This is a **native Hermes skill** stored in the source code, not in user-local data.
Any fork or fresh installation of Hermes has this capability available by default.

## Architecture

This skill uses a **three-layer architecture** for maximum efficiency and resilience:

| Layer | File | Purpose | Mutability |
|-------|------|---------|------------|
| **Deterministic Ops** | `scripts/site-ops/whatsapp-web.mjs` | Fast CLI operations (open-chat, send-message, get-unread) | Stable; updated when selectors change |
| **Site Map** | `assets/site-maps/whatsapp-web.json` | Baseline element catalog with selectors | Versioned in repo; overridden locally on heal |
| **Playbook** | This file (`SKILL.md`) | Instructions for LLM on when/how to use ops + map | Updated when new capabilities are discovered |

### Why three layers?

- **Script alone** breaks when WhatsApp changes its UI (selectors become stale).
- **Map alone** requires LLM inference for every action (slow, expensive).
- **Skill/playbook alone** is just instructions without execution capability.
- **Combined**: Script executes fast using map selectors → Map provides stable baseline → Skill tells LLM when to use script vs. re-map → Auto-healing updates map when script fails.

## Auto-Healing Protocol

When ANY operation fails due to selector mismatch or missing element:

1. **Detect**: Script throws error with selector that failed
2. **Re-map**: Run `node apps/desktop/scripts/site-deep-map.mjs init "web.whatsapp.com" && node apps/desktop/scripts/site-deep-map.mjs scan "web.whatsapp.com"`
3. **Compare**: Diff new map against baseline (`assets/site-maps/whatsapp-web.json`)
4. **Update local override**: Save new map to `.claude/site-maps/whatsapp-web.local.json` (user-local, not committed)
5. **Retry**: Re-run the failed operation with updated selectors
6. **Report**: If retry succeeds, log what changed. If it still fails, ask user for guidance.

### When to update the BASELINE map (committed to repo)

Only when:
- Multiple users report the same selector failure
- WhatsApp announces a major UI redesign
- You've verified the new selectors work across multiple sessions
- A human approves the baseline update

Never auto-update the repo baseline from a single healing event.

## Available Operations

```bash
# Open chat with a contact (searches + clicks first result)
node apps/desktop/scripts/site-ops/whatsapp-web.mjs open-chat "Contact Name"

# Send message in currently open chat
node apps/desktop/scripts/site-ops/whatsapp-web.mjs send-message "Hello world"

# Get total unread message count
node apps/desktop/scripts/site-ops/whatsapp-web.mjs get-unread-count
```

All operations connect directly to WhatsApp Web's CDP target (not the Hermes renderer),
bypassing the Hermes AI layer entirely for speed.

## Consulting the Site Map

Before attempting any WhatsApp Web automation:

1. **Check if map exists**: Read `assets/site-maps/whatsapp-web.json`
2. **Find your target element**: Search `screens.main.elements[]` by `ariaLabel`, `text`, `role`, or `testId`
3. **Use the selector**: Prefer `data-testid` > `aria-label` > `role` > text-based selectors
4. **If element not found**: Trigger auto-healing protocol above

### Example: finding the search input

```javascript
const map = require('./assets/site-maps/whatsapp-web.json')
const searchInput = map.screens.main.elements.find(e =>
  e.ariaLabel?.includes('Search') || e.placeholder?.includes('Search')
)
// Use searchInput.selector in your CDP expression
```

## Self-Improvement Triggers

The LLM should proactively improve this skill when:

| Signal | Action |
|--------|--------|
| Operation fails twice with same selector | Trigger auto-healing + log failure pattern |
| New interactive element discovered during re-map | Add to map + document in this SKILL.md |
| User manually corrects an operation | Update selector priority or add fallback |
| WhatsApp adds new feature (e.g., Communities, Channels) | Create new operation in script + update map |
| Map hasn't been validated in 30+ days | Suggest validation run to user |

## Integration with /hermes-work-control

This skill is referenced by `/hermes-work-control` as a native site capability.
When the user asks to interact with WhatsApp Web, `/hermes-work-control` should:

1. Check if WhatsApp Web is open in Hermes browser (`site-deep-map.mjs status "web.whatsapp.com"`)
2. If not open, ask Hermes AI to open it via chat injection
3. Once open, delegate to this skill's operations script
4. Never use raw CDP eval for WhatsApp operations — always go through the deterministic layer

## Files

- `apps/desktop/assets/site-skills/whatsapp-web-ops/SKILL.md` — This playbook
- `apps/desktop/assets/site-maps/whatsapp-web.json` — Baseline site map (versioned)
- `apps/desktop/scripts/site-ops/whatsapp-web.mjs` — Deterministic operations CLI
- `apps/desktop/scripts/site-deep-map.mjs` — Deep mapping tool for re-scanning
- `.claude/site-maps/whatsapp-web.local.json` — Local override (auto-healed, not committed)