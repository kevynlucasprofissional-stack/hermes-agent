// Hermes Deep Map — Recursive UI mapping via CDP
//
// Maps ALL interactive elements across ALL modules, following navigation
// depth-first. Skips session list (always changing). Saves progress to
// allow resumption across sessions.
//
// Usage:
//   node scripts/hermes-deep-map.mjs init          — start fresh map
//   node scripts/hermes-deep-map.mjs continue      — resume from last state
//   node scripts/hermes-deep-map.mjs status        — show progress
//   node scripts/hermes-deep-map.mjs module <name> — map single module
//
// Output: workstation/dogfood/artifacts/hermes-complete-map.json
// State:  workstation/dogfood/artifacts/deep-map-state.json

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { connectAiControl } from './ai-control-client.mjs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ARTIFACTS_DIR = resolve(__dirname, '../../../workstation/dogfood/artifacts')
const MAP_FILE = resolve(ARTIFACTS_DIR, 'hermes-complete-map.json')
const STATE_FILE = resolve(ARTIFACTS_DIR, 'deep-map-state.json')

if (!existsSync(ARTIFACTS_DIR)) mkdirSync(ARTIFACTS_DIR, { recursive: true })

const args = process.argv.slice(2)
const command = args[0] || 'status'
let client
try { client = await connectAiControl() }
catch (err) { console.error(JSON.stringify({ error: err.message })); process.exit(1) }
const evalExpr = expression => client.evaluate(expression)
// --- Module definitions ---
const MODULES = ['workstation', 'capabilities', 'messaging', 'artifacts', 'scheduled', 'vault', 'kanban']
const MODULE_DISPLAY_NAMES = {
  workstation: 'Workstation',
  capabilities: 'Capabilities',
  messaging: 'Messaging',
  artifacts: 'Artifacts',
  scheduled: 'Scheduled jobs',
  vault: 'Vault',
  kanban: 'Kanban',
}

// --- State management ---
function loadState() {
  if (existsSync(STATE_FILE)) {
    return JSON.parse(readFileSync(STATE_FILE, 'utf-8'))
  }
  return {
    completedModules: [],
    currentModule: null,
    pendingModules: [...MODULES],
    mappedElements: {},
    navigationTree: {},
    lastUpdated: null,
  }
}

function saveState(state) {
  state.lastUpdated = new Date().toISOString()
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2))
}

function loadMap() {
  if (existsSync(MAP_FILE)) {
    return JSON.parse(readFileSync(MAP_FILE, 'utf-8'))
  }
  return { version: '1.0', generatedAt: null, modules: {} }
}

function saveMap(map) {
  map.generatedAt = new Date().toISOString()
  writeFileSync(MAP_FILE, JSON.stringify(map, null, 2))
}

// --- Core mapping functions ---
async function checkAiControl() {
  const active = await evalExpr('window.__hermesAiControlActive')
  if (!active) throw new Error('AI Control not active. Press Ctrl+Shift+A.')
  return true
}

// Recovery: ensure sidebar nav buttons are visible before navigating
// Closes overlay panels (profiles, settings) and toggles sidebar back if hidden
async function ensureSidebarVisible() {
  const result = await evalExpr(`(() => {
    const btns = document.querySelectorAll('button[data-sidebar="menu-button"]');
    const visible = Array.from(btns).filter(b => b.getBoundingClientRect().width > 0);
    if (visible.length > 0) return { ok: true, count: visible.length };

    // Try closing overlay panels that may be blocking the sidebar
    const closeLabels = ['close profiles', 'close settings', 'close'];
    const allBtns = Array.from(document.querySelectorAll('button'));
    for (const label of closeLabels) {
      const closeBtn = allBtns.find(b => {
        const ariaLabel = (b.getAttribute('aria-label') || '').toLowerCase();
        return ariaLabel === label;
      });
      if (closeBtn && closeBtn.getBoundingClientRect().width > 0) {
        closeBtn.click();
        return { ok: false, action: 'clicked-close-' + label };
      }
    }

    // Dispatch Ctrl+B as last resort to toggle sidebar
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', ctrlKey: true, bubbles: true, cancelable: true }));
    return { ok: false, action: 'dispatched-ctrl-b' };
  })()`)

  if (!result.ok) {
    // Wait for UI to settle after recovery action
    await new Promise(r => setTimeout(r, 500))
    // Re-check
    const recheck = await evalExpr(`document.querySelectorAll('button[data-sidebar="menu-button"]').length`)
    if (recheck === 0) {
      console.error('[DEEP-MAP] ⚠ Sidebar recovery failed — nav buttons still missing')
    } else {
      console.error(`[DEEP-MAP] ✓ Sidebar recovered via ${result.action}`)
    }
  }
  return result
}

async function navigateToModule(moduleName) {
  const displayName = MODULE_DISPLAY_NAMES[moduleName]
  const clicked = await evalExpr(`(() => {
    const btns = document.querySelectorAll('button[data-sidebar="menu-button"]');
    for (const b of btns) {
      if (b.textContent?.trim() === '${displayName}') { b.click(); return true; }
    }
    return false;
  })()`)
  if (!clicked) throw new Error(`Could not navigate to ${moduleName}`)
  await new Promise(r => setTimeout(r, 500)) // Wait for render
  return true
}

async function mapCurrentScreen(moduleName, depth = 0, path = []) {
  // Collect ALL interactive elements on current screen
  const elements = await evalExpr(`(() => {
    const interactive = document.querySelectorAll('button, [role="button"], a[href], input, select, textarea, [role="tab"], [role="textbox"], [contenteditable="true"]');
    const results = [];
    const seen = new Set();
    for (const el of interactive) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue; // hidden
      if (!el.offsetParent && el.tagName !== 'BODY') continue; // not visible

      const text = (el.textContent || '').trim().substring(0, 100);
      const ariaLabel = el.getAttribute('aria-label');
      const title = el.getAttribute('title');
      const role = el.getAttribute('role');
      const placeholder = el.getAttribute('placeholder');
      const type = el.getAttribute('type');
      const dataSlot = el.getAttribute('data-slot');
      const dataSidebar = el.getAttribute('data-sidebar');
      const id = el.id;
      const classes = (el.className || '').toString().substring(0, 150);

      // Skip session list items (always changing)
      if (text.match(/^(Abrir|Criar|Enviar|Automatizar|Investigar|Buscar|Inventar)/)) continue;
      if (classes.includes('block w-full text-left') && el.tagName === 'BUTTON' && !ariaLabel) continue;

      // Skip time group headers
      if (text.match(/^(Yesterday|Earlier|Last week|Last month|Today)/)) continue;

      // Generate stable key
      const key = [el.tagName, ariaLabel || '', role || '', text.substring(0, 40)].join('|');
      if (seen.has(key)) continue;
      seen.add(key);

      // Detect if element is a navigation trigger (opens new panel/modal/screen)
      // EXCLUDE: sidebar module buttons (data-sidebar="menu-button") — these switch modules, not sub-screens
      // EXCLUDE: session list actions — these are per-session, not structural
      // EXCLUDE: layout toggles and profile overlays — these break navigation state
      const isSidebarModuleBtn = dataSidebar === 'menu-button';
      const isSessionListBtn = classes.includes('block w-full text-left') && !ariaLabel;
      const isLayoutToggle = ariaLabel?.match(/^(Hide sidebar|Show sidebar|Hide right sidebar|Swap sidebar|Layout editor|HUD mode)$/i) || text.match(/^(Hide|Show)$/i);
      const isProfileOverlay = ariaLabel?.match(/^(New profile|Import profile|Manage profiles|Manage gateways|Close profiles)$/i);
      // Exclude triggers that open external windows or break CDP context
      const isExternalWindow = ariaLabel?.match(/^(Pop out|Open preview DevTools|Show preview console|Pop out to Browser Hub)$/i) || text.match(/^(Pop out|DevTools|Preview console)$/i);
      // Exclude buttons that trigger native OS dialogs (file pickers, color pickers, etc.)
      // These block CDP execution as the renderer waits for user interaction in a non-DOM window
      const isNativeDialog = (el.tagName === 'INPUT' && ['file', 'color'].includes(type)) ||
        ariaLabel?.match(/^(Browse|Choose file|Select file|Upload|Pick|Attach)$/i) ||
        text.match(/^(Browse|Choose|Select file|Upload|Attach|Add file)$/i);
      const isDangerousTrigger = isLayoutToggle || isProfileOverlay || isExternalWindow || isNativeDialog;
      const isNavTrigger = !isSidebarModuleBtn && !isSessionListBtn && !isDangerousTrigger && (
        (el.tagName === 'BUTTON' && (
          text.match(/^(Open|New|Manage|Import|Add|Create|Edit|View|Show|Toggle|Load|Filters|Pop out)/i) ||
          ariaLabel?.match(/^(Open|New|Manage|Import|Add|Create|Edit|View|Show|Toggle|Load|Filters|Pop out)/i) ||
          dataSlot === 'context-menu-trigger' ||
          role === 'tab'
        )) ||
        (el.tagName === 'A' && el.getAttribute('href'))
      );

      results.push({
        tag: el.tagName,
        text: text,
        ariaLabel: ariaLabel,
        title: title,
        role: role,
        placeholder: placeholder,
        type: type,
        dataSlot: dataSlot,
        dataSidebar: dataSidebar,
        id: id,
        classes: classes,
        isVisible: true,
        isNavTrigger: isNavTrigger,
        boundingRect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
        selector: buildSelector(el),
      });
    }

    function buildSelector(el) {
      if (el.id) return '#' + el.id;
      if (el.getAttribute('aria-label')) return el.tagName.toLowerCase() + '[aria-label="' + el.getAttribute('aria-label') + '"]';
      if (el.getAttribute('data-sidebar')) return el.tagName.toLowerCase() + '[data-sidebar="' + el.getAttribute('data-sidebar') + '"]';
      if (el.getAttribute('role')) return el.tagName.toLowerCase() + '[role="' + el.getAttribute('role') + '"]';
      // Fallback: use nth-of-type among same-tag siblings for stable positioning
      const tag = el.tagName.toLowerCase();
      const parent = el.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
        const idx = siblings.indexOf(el) + 1;
        if (idx > 0) return tag + ':nth-of-type(' + idx + ')';
      }
      return tag;
    }

    return results;
  })()`)

  // Also capture headings and structural info
  const structure = await evalExpr(`(() => {
    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(h => ({
      level: parseInt(h.tagName[1]),
      text: h.textContent?.trim().substring(0, 100),
    }));
    const activeTab = document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim() || null;
    const breadcrumbs = Array.from(document.querySelectorAll('[class*="breadcrumb"], nav[aria-label]')).map(el => el.textContent?.trim().substring(0, 100));
    return { headings, activeTab, breadcrumbs };
  })()`)

  return {
    screenPath: [...path, moduleName],
    depth: depth,
    timestamp: new Date().toISOString(),
    structure: structure,
    elements: elements,
    elementCount: elements.length,
  }
}

async function exploreModule(moduleName) {
  console.error(`[DEEP-MAP] Exploring module: ${moduleName}`)
  await checkAiControl()
  await ensureSidebarVisible()
  await navigateToModule(moduleName)

  const map = loadMap()
  const state = loadState()

  // Map the main screen of this module
  const mainScreen = await mapCurrentScreen(moduleName, 0, [moduleName])

  // Initialize module entry in map
  if (!map.modules[moduleName]) {
    map.modules[moduleName] = {
      displayName: MODULE_DISPLAY_NAMES[moduleName],
      mainScreen: mainScreen,
      subScreens: [],
      navigationTargets: [],
      exploredAt: new Date().toISOString(),
    }
  } else {
    map.modules[moduleName].mainScreen = mainScreen
  }

  // Identify navigation targets from main screen
  const navTriggers = mainScreen.elements.filter(e => e.isNavTrigger)
  map.modules[moduleName].navigationTargets = navTriggers.map(t => ({
    selector: t.selector,
    text: t.text,
    ariaLabel: t.ariaLabel,
  }))

  // For each nav trigger, attempt to click and map the resulting screen
  for (const trigger of navTriggers.slice(0, 10)) { // Limit to 10 per module to avoid infinite loops
    try {
      console.error(`[DEEP-MAP]   Clicking nav trigger: ${trigger.text || trigger.ariaLabel}`)
      const clickResult = await evalExpr(`(() => {
        const el = document.querySelector('${trigger.selector.replace(/'/g, "\\'")}');
        if (!el) return { error: 'not found' };
        el.click();
        return { clicked: true, tag: el.tagName };
      })()`)

      if (clickResult.clicked) {
        // Adaptive wait: poll until screen content changes or timeout (3s max)
        // This prevents capturing stale DOM when React render is slower than fixed delay
        const baselineCount = mainScreen.elementCount
        const baselineHeadings = mainScreen.structure.headings.map(h => h.text).join(',')
        let settled = false
        for (let attempt = 0; attempt < 10; attempt++) {
          await new Promise(r => setTimeout(r, 300))
          const probe = await evalExpr(`(() => {
            const count = document.querySelectorAll('button, [role="button"], input, select, textarea, [role="tab"], [role="textbox"], [contenteditable="true"]').length
            const heads = Array.from(document.querySelectorAll('h1,h2,h3')).map(h => h.textContent?.trim()).join(',')
            return { count, heads }
          })()`)
          if (probe.count !== baselineCount || probe.heads !== baselineHeadings) {
            settled = true
            break
          }
        }
        if (!settled) {
          console.error(`[DEEP-MAP]   ⚠ Screen did not change after 3s for trigger: ${trigger.text || trigger.ariaLabel}`)
        }
        const subScreen = await mapCurrentScreen(moduleName, 1, [moduleName, trigger.text || trigger.ariaLabel])

        // Only record if screen actually changed
        const subHeadings = subScreen.structure.headings.map(h => h.text).join(',')
        if (subHeadings !== baselineHeadings || subScreen.elementCount !== baselineCount) {
          map.modules[moduleName].subScreens.push({
            trigger: trigger,
            screen: subScreen,
          })
          console.error(`[DEEP-MAP]   Mapped sub-screen: ${subScreen.elementCount} elements`)

          // Try to close/dismiss the sub-screen to return to main
          await evalExpr(`(() => {
            const candidates = Array.from(document.querySelectorAll('button'));
            const closeBtn = candidates.find(b => {
              const label = (b.getAttribute('aria-label') || '').toLowerCase();
              const text = (b.textContent || '').trim().toLowerCase();
              return label === 'close' || label === 'dismiss' || text === 'close' || text === 'cancel' || text === 'dismiss';
            });
            if (closeBtn) closeBtn.click();
          })()`)
          await new Promise(r => setTimeout(r, 300))
        }
      }
    } catch (err) {
      console.error(`[DEEP-MAP]   Error exploring trigger: ${err.message}`)
    }
  }

  saveMap(map)

  // Update state
  state.currentModule = moduleName
  state.completedModules.push(moduleName)
  state.pendingModules = state.pendingModules.filter(m => m !== moduleName)
  saveState(state)

  return {
    module: moduleName,
    mainScreenElements: mainScreen.elementCount,
    subScreens: map.modules[moduleName].subScreens.length,
    navTriggers: navTriggers.length,
  }
}

// --- Commands ---
async function cmdInit() {
  const state = {
    completedModules: [],
    currentModule: null,
    pendingModules: [...MODULES],
    mappedElements: {},
    navigationTree: {},
    lastUpdated: new Date().toISOString(),
  }
  saveState(state)
  saveMap({ version: '1.0', generatedAt: null, modules: {} })
  console.log(JSON.stringify({ initialized: true, modules: MODULES }))
}

async function cmdStatus() {
  const state = loadState()
  const map = loadMap()
  const moduleStats = {}
  for (const [name, data] of Object.entries(map.modules || {})) {
    moduleStats[name] = {
      mainElements: data.mainScreen?.elementCount || 0,
      subScreens: data.subScreens?.length || 0,
      navTargets: data.navigationTargets?.length || 0,
    }
  }
  console.log(JSON.stringify({
    completedModules: state.completedModules,
    pendingModules: state.pendingModules,
    currentModule: state.currentModule,
    lastUpdated: state.lastUpdated,
    totalModules: MODULES.length,
    progress: `${state.completedModules.length}/${MODULES.length}`,
    moduleStats: moduleStats,
  }, null, 2))
}

async function cmdContinue() {
  const state = loadState()
  if (state.pendingModules.length === 0) {
    console.log(JSON.stringify({ complete: true, message: 'All modules already mapped' }))
    return
  }
  const nextModule = state.pendingModules[0]
  const result = await exploreModule(nextModule)
  console.log(JSON.stringify(result, null, 2))
}

async function cmdModule(moduleName) {
  if (!MODULES.includes(moduleName)) {
    console.error(JSON.stringify({ error: `unknown module: ${moduleName}. Valid: ${MODULES.join(', ')}` }))
    process.exit(1)
  }
  const result = await exploreModule(moduleName)
  console.log(JSON.stringify(result, null, 2))
}

// --- Main dispatch ---
try {
  switch (command) {
    case 'init': await cmdInit(); break
    case 'status': await cmdStatus(); break
    case 'continue': await cmdContinue(); break
    case 'module': await cmdModule(args[1]); break
    default:
      console.error(JSON.stringify({ error: `unknown command: ${command}. Valid: init, status, continue, module <name>` }))
      process.exit(1)
  }
} catch (err) {
  console.error(JSON.stringify({ error: err.message }))
  process.exit(1)
} finally {
  client.close()
}