#!/usr/bin/env node
// WhatsApp Web Operations — Deterministic Layer
//
// Fast, reliable operations for WhatsApp Web executed via CDP without LLM inference.
// Selectors are resolved from the site map (baseline or local override), with auto-healing
// on failure.
//
// Usage:
//   node whatsapp-web.mjs <operation> [args...]
//
// Operations:
//   open-chat <contact-name>    — Open chat with contact
//   send-message <text>         — Send message in current chat
//   get-unread-count            — Get count of unread messages

import { CdpClient } from '../../framework/cdp-client.mjs'
import { loadSiteMap } from '../../framework/map-loader.mjs'
import { withAutoHealing } from '../../framework/auto-heal.mjs'
import { findElement, resolveSelector } from '../../framework/selector-resolver.mjs'

const SITE_SLUG = 'whatsapp-web'
const SITE_PATTERN = 'web.whatsapp.com'

const client = new CdpClient()

// Operations
async function openChat(contactName) {
  if (!contactName) {
    throw new Error('Contact name is required for open-chat')
  }

  const map = loadSiteMap(SITE_SLUG)
  const searchInput = findElement(map, e =>
    e.ariaLabel?.includes('Search') || e.placeholder?.includes('Search')
  )

  if (!searchInput) {
    throw new Error('Search input not found in site map')
  }

  const selector = resolveSelector(searchInput)
  if (!selector) {
    throw new Error('Could not resolve selector for search input')
  }

  // Click search input
  await client.eval(`document.querySelector('${selector}')?.click()`)
  await new Promise(r => setTimeout(r, 300))

  // Type contact name
  await client.eval(`(() => {
    const input = document.querySelector('${selector}')
    if (!input) return false
    input.focus()
    input.value = '${contactName.replace(/'/g, "\\'")}'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })()`)

  await new Promise(r => setTimeout(r, 800))

  // Click first result
  const clicked = await client.eval(`(() => {
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
  if (!text) {
    throw new Error('Message text is required for send-message')
  }

  const map = loadSiteMap(SITE_SLUG)
  const messageInput = findElement(map, e =>
    e.ariaLabel === 'Type a message' || e.role === 'textbox'
  )

  if (!messageInput) {
    throw new Error('Message input not found in site map')
  }

  const selector = resolveSelector(messageInput)
  if (!selector) {
    throw new Error('Could not resolve selector for message input')
  }

  // Focus and type message
  await client.eval(`(() => {
    const input = document.querySelector('${selector}')
    if (!input) return false
    input.focus()
    input.textContent = '${text.replace(/'/g, "\\'")}'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })()`)

  await new Promise(r => setTimeout(r, 200))

  // Press Enter to send
  await client.eval(`(() => {
    const input = document.querySelector('${selector}')
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
  const count = await client.eval(`(() => {
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
  const target = await client.findTarget(SITE_PATTERN)
  await client.connect(target)

  const healOptions = { sitePattern: SITE_PATTERN, siteSlug: SITE_SLUG }
  let result

  switch (operation) {
    case 'open-chat':
      result = await withAutoHealing('open-chat', () => openChat(args[1]), healOptions)
      break
    case 'send-message':
      result = await withAutoHealing('send-message', () => sendMessage(args.slice(1).join(' ')), healOptions)
      break
    case 'get-unread-count':
      result = await withAutoHealing('get-unread-count', getUnreadCount, healOptions)
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
  client.close()
}
