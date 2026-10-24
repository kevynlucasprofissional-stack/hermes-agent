// Hermes Navigation Helper — batch-first CDP navigation for AI agents.
//
// Usage:
//   node scripts/hermes-nav.mjs <command> [args...]
//
// Commands:
//   status              — check AI control + current module + active tab
//   goto <module>       — navigate to module (workstation|capabilities|messaging|artifacts|scheduled|vault|kanban)
//   click <selector>    — click element by CSS selector
//   read <selector>     — read textContent of element
//   inject <prompt>     — inject prompt into chat input and send
//   tour [modules...]   — run a multi-module tour with verification
//
// All commands use a single CDP connection. Output is JSON to stdout.
// Requires AI Control active (Ctrl+Shift+A).

import { connectAiControl } from './ai-control-client.mjs'

const args = process.argv.slice(2)
const command = args[0]
if (!command) {
  console.error('Usage: hermes-nav.mjs <status|goto|click|read|inject|tour>')
  process.exit(1)
}
let client
try { client = await connectAiControl() }
catch (err) { console.error(JSON.stringify({ error: err.message })); process.exit(1) }
const evalExpr = expression => client.evaluate(expression)

async function requireAiControl() {
  if (!(await evalExpr('window.__hermesAiControlActive'))) {
    throw new Error('AI Control not active. Press Ctrl+Shift+A.')
  }
}
// --- Module selectors (data-sidebar + text based; sidebar buttons lack aria-label) ---
// Sidebar nav buttons use data-sidebar="menu-button" and have no aria-label.
// We match by exact textContent within that scoped set to avoid session list items.
const MODULE_NAMES = {
  workstation:  'Workstation',
  capabilities: 'Capabilities',
  messaging:    'Messaging',
  artifacts:    'Artifacts',
  scheduled:    'Scheduled jobs',
  vault:        'Vault',
  kanban:       'Kanban',
}

function buildModuleClickExpr(moduleName) {
  const name = MODULE_NAMES[moduleName.toLowerCase()]
  if (!name) return null
  // data-sidebar="menu-button" is the stable attribute on all sidebar nav buttons
  return `(() => { const btns = document.querySelectorAll('button[data-sidebar="menu-button"]'); for (const b of btns) { if (b.textContent?.trim() === '${name}') { b.click(); return true; } } return false; })()`
}

// --- Commands ---

async function cmdStatus() {
  const aiControl = await evalExpr('window.__hermesAiControlActive')
  const activeTab = await evalExpr(`document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim() || null`)
  const headings = await evalExpr(`Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 5).map(h => h.textContent?.trim())`)
  const backendStatus = await evalExpr(`(() => { const els = document.querySelectorAll('button, span'); for (const el of els) { const t = (el.textContent || '').trim(); if (t.length < 40 && (t === 'Backend offline' || t === 'desktop' || /^v\\d/.test(t))) return t; } return null; })()`)
  return { aiControl, activeTab, headings, backendStatus }
}

async function cmdGoto(moduleName) {
  await requireAiControl()
  const key = moduleName.toLowerCase()
  const clickExpr = buildModuleClickExpr(key)

  if (!clickExpr) {
    return { error: `unknown module: ${moduleName}. Valid: ${Object.keys(MODULE_NAMES).join(', ')}` }
  }

  const clicked = await evalExpr(clickExpr)
  if (!clicked) {
    return { error: `could not find or click module: ${moduleName}` }
  }

  // Wait briefly for React render, then verify
  await new Promise(r => setTimeout(r, 200))
  const headings = await evalExpr(`Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 5).map(h => h.textContent?.trim())`)
  const activeTab = await evalExpr(`document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim() || null`)

  return { success: true, module: moduleName, headings, activeTab }
}

async function cmdClick(selector) {
  await requireAiControl()
  const result = await evalExpr(`(() => { const el = document.querySelector('${selector.replace(/'/g, "\\'")}'); if (!el) return { error: 'not found' }; el.click(); return { clicked: true, tag: el.tagName, text: (el.textContent || '').trim().substring(0, 60) }; })()`)
  return result
}

async function cmdRead(selector) {
  const result = await evalExpr(`(() => { const el = document.querySelector('${selector.replace(/'/g, "\\'")}'); if (!el) return { error: 'not found' }; return { text: (el.textContent || '').trim().substring(0, 200), tag: el.tagName }; })()`)
  return result
}

async function cmdInject(promptText) {
  // Step 1: Check AI control
  const aiControl = await evalExpr('window.__hermesAiControlActive')
  if (!aiControl) return { error: 'AI Control not active. Press Ctrl+Shift+A.' }

  // Step 2: Inject via paste event
  const injected = await evalExpr(`(() => {
    const el = document.querySelector('div[role="textbox"][aria-label="Message"]');
    if (!el) return 'NOT_FOUND';
    el.focus();
    const text = ${JSON.stringify(promptText)};
    const dt = new DataTransfer();
    dt.setData('text/plain', text);
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
    return 'INJECTED';
  })()`)

  if (injected !== 'INJECTED') return { error: 'chat input not found', detail: injected }

  // Step 3: Send via Enter key
  const sent = await evalExpr(`(() => {
    const el = document.querySelector('div[role="textbox"][aria-label="Message"]');
    if (!el) return false;
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    return true;
  })()`)

  return { success: sent, injected: true, promptLength: promptText.length }
}

async function cmdTour(modules) {
  const results = []
  for (const mod of modules) {
    const start = Date.now()
    try {
      const nav = await cmdGoto(mod)
      results.push({ module: mod, ...nav, durationMs: Date.now() - start })
    } catch (err) {
      results.push({ module: mod, error: err.message, durationMs: Date.now() - start })
    }
  }
  return results
}

// --- Main dispatch ---
try {
  let output
  switch (command) {
    case 'status':
      output = await cmdStatus()
      break
    case 'goto':
      output = await cmdGoto(args[1])
      break
    case 'click':
      output = await cmdClick(args[1])
      break
    case 'read':
      output = await cmdRead(args[1])
      break
    case 'inject':
      output = await cmdInject(args.slice(1).join(' '))
      break
    case 'tour':
      output = await cmdTour(args.slice(1).length > 0 ? args.slice(1) : ['workstation', 'capabilities', 'kanban', 'messaging'])
      break
    default:
      output = { error: `unknown command: ${command}` }
  }
  console.log(JSON.stringify(output, null, 2))
} catch (err) {
  console.error(JSON.stringify({ error: err.message }))
  process.exit(1)
} finally {
  client.close()
}