#!/usr/bin/env node
// WhatsApp Web Operations — Deterministic Layer
//
// This script provides fast, reliable operations for WhatsApp Web
// without requiring LLM inference for each action. It reads selectors
// from the site map and executes them via CDP.
//
// Usage:
//   node whatsapp-web.mjs <operation> [args...]
//
// Operations:
//   open-chat <contact-name>    — Open chat with contact
//   send-message <text>         — Send message in current chat
//   search-contact <query>      — Search for contact
//   get-unread-count            — Get count of unread messages
//   get-chat-list               — List recent chats
//
// Auto-healing: if a selector fails, the script triggers re-mapping
// and updates the site map automatically.

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SITE_MAP_PATH = resolve(__dirname, '../../assets/site-maps/whatsapp-web.json')
const LOCAL_MAP_PATH = resolve(__dirname, '../../../../../.claude/site-maps/whatsapp-web.local.json')

// Load site map (prefer local overrides, fallback to repo version)
function loadSiteMap() {
  if (existsSync(LOCAL_MAP_PATH)) {
    return JSON.parse(readFileSync(LOCAL_MAP_PATH, 'utf-8'))
  }
  if (existsSync(SITE_MAP_PATH)) {
    return JSON.parse(readFileSync(SITE_MAP_PATH, 'utf-8'))
  }
  throw new Error('Site map not found. Run site-deep-map.mjs first.')
}

// CDP connection (reuse from site-deep-map pattern)
const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9222)

async function findWhatsAppTarget() {
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
  const target = targets.find(t => t.type === 'page' && t.url.includes('web.whatsapp.com'))
  if (!target) throw new Error('WhatsApp Web not found in CDP targets')
  return target
}

let ws, id = 0
const pending = new Map()

async function connectCDP(target) {
  ws = new WebSocket(target.webSocketDebuggerUrl)
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (pending.has(m.id)) {
      pending.get(m.id)(m)
      pending.delete(m.id)
    }
  })
  await new Promise(r => ws.addEventListener('open', r))
}

const evalExpr = async (expr) => {
  const i = ++id
  const p = new Promise((res) => pending.set(i, res))
  ws.send(JSON.stringify({
    id: i,
    method: 'Runtime.evaluate',
    params: { expression: expr, returnByValue: true, awaitPromise: true }
  }))
  const r = await p
  if (r.result.exceptionDetails) {
    throw new Error(r.result.exceptionDetails.exception?.description || 'eval error')
  }
  return r.result.result.value
}

// Auto-healing wrapper: if selector fails, re-map and retry
async function withAutoHealing(operationName, operationFn) {
  try {
    return await operationFn()
  } catch (err) {
    console.error(`[AUTO-HEAL] Operation "${operationName}" failed: ${err.message}`)
    console.error('[AUTO-HEAL] Triggering re-mapping...')

    // Re-run deep map
    execSync(`node ${resolve(__dirname, '../site-deep-map.mjs')} init "web.whatsapp.com"`, {
      stdio: 'inherit'
    })
    execSync(`node ${resolve(__dirname, '../site-deep-map.mjs')} scan "web.whatsapp.com"`, {
      stdio: 'inherit'
    })

    // Copy new map to local override
    const newMap = readFileSync(resolve(__dirname, '../../../workstation/dogfood/artifacts/site-map-web-whatsapp-com.json'), 'utf-8')
    if (!existsSync(dirname(LOCAL_MAP_PATH))) {
      const { mkdirSync } = await import('node:fs')
      mkdirSync(dirname(LOCAL_MAP_PATH), { recursive: true })
    }
    writeFileSync(LOCAL_MAP_PATH, newMap)

    console.error('[AUTO-HEAL] Site map updated. Retrying operation...')

    // Retry once
    try {
      return await operationFn()
    } catch (retryErr) {
      throw new Error(`Operation failed even after re-mapping: ${retryErr.message}`)
    }
  }
}

// Operations
async function openChat(contactName) {
  const map = loadSiteMap()
  const searchInput = map.screens.main.elements.find(e =>
    e.ariaLabel?.includes('Search') || e.placeholder?.includes('Search')
  )

  if (!searchInput) {
    throw new Error('Search input not found in site map')
  }

  // Click search input
  await evalExpr(`document.querySelector('${searchInput.selector}')?.click()`)
  await new Promise(r => setTimeout(r, 300))

  // Type contact name
  await evalExpr(`(() => {
    const input = document.querySelector('${searchInput.selector}')
    if (!input) return false
    input.focus()
    input.value = '${contactName.replace(/'/g, "\\'")}'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })()`)

  await new Promise(r => setTimeout(r, 800))

  // Click first result
  const clicked = await evalExpr(`(() => {
    const results = document.querySelectorAll('[data-testid="contact-item"]')
    if (results.length > 0) {
      results[0].click()
      return true
    }
    return false
  })()`)

  if (!clicked) {
    throw new Error(`No contact found matching "${contactName}"`)
  }

  return { success: true, contact: contactName }
}

async function sendMessage(text) {
  const map = loadSiteMap()
  const messageInput = map.screens.main.elements.find(e =>
    e.ariaLabel === 'Type a message' || e.role === 'textbox'
  )

  if (!messageInput) {
    throw new Error('Message input not found in site map')
  }

  // Focus and type message
  await evalExpr(`(() => {
    const input = document.querySelector('${messageInput.selector}')
    if (!input) return false
    input.focus()
    input.textContent = '${text.replace(/'/g, "\\'")}'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })()`)

  await new Promise(r => setTimeout(r, 200))

  // Press Enter to send
  await evalExpr(`(() => {
    const input = document.querySelector('${messageInput.selector}')
    if (!input) return false
    input.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      bubbles: true
    }))
    return true
  })()`)

  return { success: true, messageLength: text.length }
}

async function getUnreadCount() {
  const count = await evalExpr(`(() => {
    const badges = document.querySelectorAll('[data-testid="icon-unread-count"]')
    let total = 0
    badges.forEach(badge => {
      const num = parseInt(badge.textContent?.trim() || '0')
      if (!isNaN(num)) total += num
    })
    return total
  })()`)

  return { unreadCount: count }
}

// Main dispatch
const args = process.argv.slice(2)
const operation = args[0]

try {
  const target = await findWhatsAppTarget()
  await connectCDP(target)

  let result
  switch (operation) {
    case 'open-chat':
      result = await withAutoHealing('open-chat', () => openChat(args[1]))
      break
    case 'send-message':
      result = await withAutoHealing('send-message', () => sendMessage(args.slice(1).join(' ')))
      break
    case 'get-unread-count':
      result = await withAutoHealing('get-unread-count', getUnreadCount)
      break
    default:
      console.error(`Unknown operation: ${operation}`)
      console.error('Available: open-chat, send-message, get-unread-count')
      process.exit(1)
  }

  console.log(JSON.stringify(result, null, 2))
} catch (err) {
  console.error(JSON.stringify({ error: err.message }))
  process.exit(1)
} finally {
  if (ws) ws.close()
}