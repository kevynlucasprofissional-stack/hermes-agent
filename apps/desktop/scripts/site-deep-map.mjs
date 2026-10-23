// Site Deep Map — Recursive UI mapping for external sites via CDP
//
// Maps ALL interactive elements on external sites loaded in Hermes' native
// browser (or any CDP-enabled Chromium). Connects directly to the site's
// CDP target (not the Hermes renderer), enabling full DOM access.
//
// Usage:
//   node scripts/site-deep-map.mjs init <url-pattern>   — start fresh map for site matching pattern
//   node scripts/site-deep-map.mjs continue             — resume from last state
//   node scripts/site-deep-map.mjs status               — show progress
//   node scripts/site-deep-map.mjs scan                 — single-pass element scan (no navigation)
//
// Output: workstation/dogfood/artifacts/site-map-<slug>.json
// State:  workstation/dogfood/artifacts/site-map-<slug>-state.json
//
// Architecture: "LLM writes script > Script > Runtime > Script > Runtime > Output"
// This script IS the deterministic layer. The LLM only analyzes the output.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ARTIFACTS_DIR = resolve(__dirname, '../../../workstation/dogfood/artifacts')
if (!existsSync(ARTIFACTS_DIR)) mkdirSync(ARTIFACTS_DIR, { recursive: true })

const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9222)
const args = process.argv.slice(2)
const command = args[0] || 'status'

// --- Target Discovery ---
async function findTarget(urlPattern) {
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
  const pages = targets.filter(t => t.type === 'page' && t.url !== 'about:blank' && t.url !== '')

  if (urlPattern) {
    const match = pages.find(t => t.url.includes(urlPattern) || (t.title || '').includes(urlPattern))
    if (match) return match
    throw new Error(`No CDP target matching "${urlPattern}". Available: ${pages.map(p => p.url).join(', ')}`)
  }

  // Auto-detect: prefer non-Hermes pages
  const external = pages.filter(t => !t.url.includes('127.0.0.1:5174'))
  if (external.length === 1) return external[0]
  if (external.length > 1) {
    console.error(`Multiple external targets found. Specify one:`)
    external.forEach(p => console.error(`  - ${p.title || '(no title)'} → ${p.url}`))
    process.exit(1)
  }
  throw new Error('No external CDP targets found. Open a site in Hermes browser first.')
}

// --- CDP Connection ---
let ws, id = 0
const pending = new Map()

async function connectCDP(target) {
  ws = new WebSocket(target.webSocketDebuggerUrl)
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  })
  await new Promise(r => ws.addEventListener('open', r))
  console.error(`[SITE-MAP] Connected to: ${target.title || target.url}`)
}

const evalExpr = async (expr) => {
  const i = ++id
  const p = new Promise((res) => pending.set(i, res))
  ws.send(JSON.stringify({ id: i, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }))
  const r = await p
  if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || 'eval error')
  return r.result.result.value
}

// --- State Management ---
function slugify(url) {
  try { return new URL(url).hostname.replace(/[^a-z0-9]/g, '-') } catch { return 'unknown-site' }
}

function getPaths(slug) {
  return {
    mapFile: resolve(ARTIFACTS_DIR, `site-map-${slug}.json`),
    stateFile: resolve(ARTIFACTS_DIR, `site-map-${slug}-state.json`),
  }
}

function loadState(slug) {
  const { stateFile } = getPaths(slug)
  if (existsSync(stateFile)) return JSON.parse(readFileSync(stateFile, 'utf-8'))
  return { slug, url: null, completedPhases: [], pendingPhases: ['main'], lastUpdated: null }
}

function saveState(slug, state) {
  const { stateFile } = getPaths(slug)
  state.lastUpdated = new Date().toISOString()
  writeFileSync(stateFile, JSON.stringify(state, null, 2))
}

function loadMap(slug) {
  const { mapFile } = getPaths(slug)
  if (existsSync(mapFile)) return JSON.parse(readFileSync(mapFile, 'utf-8'))
  return { version: '1.0', site: null, generatedAt: null, screens: {} }
}

function saveMap(slug, map) {
  const { mapFile } = getPaths(slug)
  map.generatedAt = new Date().toISOString()
  writeFileSync(mapFile, JSON.stringify(map, null, 2))
}

// --- Element Scanning ---
async function scanCurrentScreen(label = 'main') {
  const elements = await evalExpr(`(() => {
    const interactive = document.querySelectorAll(
      'button, [role="button"], a[href], input, select, textarea, ' +
      '[role="tab"], [role="textbox"], [contenteditable="true"], ' +
      '[data-testid], [aria-label]'
    )
    const results = []
    const seen = new Set()
    for (const el of interactive) {
      const rect = el.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) continue
      if (!el.offsetParent && el.tagName !== 'BODY') continue

      const text = (el.textContent || '').trim().substring(0, 120)
      const ariaLabel = el.getAttribute('aria-label')
      const title = el.getAttribute('title')
      const role = el.getAttribute('role')
      const placeholder = el.getAttribute('placeholder')
      const type = el.getAttribute('type')
      const testId = el.getAttribute('data-testid')
      const href = el.getAttribute('href')
      const tag = el.tagName.toLowerCase()

      // Skip invisible/decorative elements
      if (!text && !ariaLabel && !title && !testId && !href && !placeholder) continue

      // Generate stable key
      const key = [tag, ariaLabel || '', testId || '', role || '', text.substring(0, 50)].join('|')
      if (seen.has(key)) continue
      seen.add(key)

      // Classify element purpose
      let category = 'interactive'
      if (tag === 'a' && href) category = 'navigation'
      else if (['input', 'select', 'textarea'].includes(tag) || role === 'textbox' || el.contentEditable === 'true') category = 'input'
      else if (role === 'tab' || role === 'menuitem') category = 'navigation'
      else if (tag === 'button' || role === 'button') category = 'action'

      // Detect if likely triggers navigation/state change
      const isNavTrigger = (
        category === 'navigation' ||
        (tag === 'button' && (
          /^(Open|New|Create|Add|Edit|Delete|Remove|Send|Submit|Save|Cancel|Close|Back|Next|Previous|More|Menu|Settings|Search|Filter|Sort|Toggle|Show|Hide|Expand|Collapse)/i.test(text) ||
          /^(Open|New|Create|Add|Edit|Delete|Send|Submit|Save|Cancel|Close|Back|Next|Settings|Search|Filter|Menu)/i.test(ariaLabel || '')
        ))
      )

      // Build best selector
      let selector = ''
      if (testId) selector = '[data-testid="' + testId + '"]'
      else if (ariaLabel) selector = tag + '[aria-label="' + ariaLabel.replace(/"/g, '\\"') + '"]'
      else if (el.id) selector = '#' + el.id
      else if (role) selector = tag + '[role="' + role + '"]'
      else if (text.length < 60 && text.length > 0) selector = tag + ':has-text("' + text.replace(/"/g, '\\"').substring(0, 40) + '")'

      results.push({
        tag, text: text.substring(0, 80), ariaLabel, title, role, placeholder, type, testId, href: href?.substring(0, 100),
        category, isNavTrigger, selector,
        boundingRect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
      })
    }
    return results
  })()`)

  const structure = await evalExpr(`(() => {
    const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4')).map(h => ({
      level: parseInt(h.tagName[1]), text: h.textContent?.trim().substring(0, 100)
    }))
    const title = document.title
    const url = location.href
    return { headings, title, url }
  })()`)

  return { label, timestamp: new Date().toISOString(), structure, elements, elementCount: elements.length }
}

// --- Commands ---
async function cmdInit(urlPattern) {
  const target = await findTarget(urlPattern)
  await connectCDP(target)
  const slug = slugify(target.url)
  const state = { slug, url: target.url, completedPhases: [], pendingPhases: ['main'], lastUpdated: new Date().toISOString() }
  saveState(slug, state)
  saveMap(slug, { version: '1.0', site: target.url, generatedAt: null, screens: {} })
  console.log(JSON.stringify({ initialized: true, slug, url: target.url }))
}

async function cmdStatus(urlPattern) {
  const target = await findTarget(urlPattern)
  const slug = slugify(target.url)
  const state = loadState(slug)
  const map = loadMap(slug)
  const screenStats = {}
  for (const [name, data] of Object.entries(map.screens || {})) {
    screenStats[name] = { elements: data.elementCount || 0, navTriggers: (data.elements || []).filter(e => e.isNavTrigger).length }
  }
  console.log(JSON.stringify({
    slug, url: state.url, completedPhases: state.completedPhases, pendingPhases: state.pendingPhases,
    lastUpdated: state.lastUpdated, totalScreens: Object.keys(map.screens || {}).length, screenStats,
  }, null, 2))
}

async function cmdScan(urlPattern) {
  const target = await findTarget(urlPattern)
  await connectCDP(target)
  const slug = slugify(target.url)
  const screen = await scanCurrentScreen('main')
  const map = loadMap(slug)
  map.site = target.url
  map.screens.main = screen
  saveMap(slug, map)
  console.log(JSON.stringify({ scanned: true, elements: screen.elementCount, navTriggers: screen.elements.filter(e => e.isNavTrigger).length, title: screen.structure.title }, null, 2))
}

async function cmdContinue(urlPattern) {
  const target = await findTarget(urlPattern)
  await connectCDP(target)
  const slug = slugify(target.url)
  const state = loadState(slug)
  const map = loadMap(slug)

  if (state.pendingPhases.length === 0) {
    console.log(JSON.stringify({ complete: true, message: 'All phases mapped' }))
    return
  }

  const phase = state.pendingPhases[0]
  console.error(`[SITE-MAP] Scanning phase: ${phase}`)
  const screen = await scanCurrentScreen(phase)
  map.screens[phase] = screen

  // Identify nav triggers for potential deeper exploration
  const navTriggers = screen.elements.filter(e => e.isNavTrigger)

  state.completedPhases.push(phase)
  state.pendingPhases.shift()
  saveState(slug, state)
  saveMap(slug, map)

  console.log(JSON.stringify({
    phase, elements: screen.elementCount, navTriggers: navTriggers.length,
    sampleTriggers: navTriggers.slice(0, 10).map(t => ({ text: t.text, ariaLabel: t.ariaLabel, category: t.category })),
  }, null, 2))
}

// --- Main Dispatch ---
try {
  switch (command) {
    case 'init': await cmdInit(args[1]); break
    case 'status': await cmdStatus(args[1]); break
    case 'scan': await cmdScan(args[1]); break
    case 'continue': await cmdContinue(args[1]); break
    default:
      console.error(`Usage: site-deep-map.mjs <init|status|scan|continue> [url-pattern]`)
      process.exit(1)
  }
} catch (err) {
  console.error(JSON.stringify({ error: err.message }))
  process.exit(1)
} finally {
  if (ws) ws.close()
}