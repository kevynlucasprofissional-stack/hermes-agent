/**
 * B1.1 — Task-oriented snapshot views for economical browser observation.
 *
 * These are opt-in projections of an existing `PageInventoryResult`. They never
 * replace the default `formatInventory` output; callers request a view by name
 * and receive a compact, budget-aware rendering suitable for model consumption.
 *
 * Design constraints (D-049):
 * - Views are pure functions over `PageInventoryResult`; no CDP, no DOM access.
 * - `@eN` refs are preserved verbatim so action continuity is not broken.
 * - Every view accepts an explicit byte/char budget and reports truncation.
 * - No new types beyond what the existing snapshot module already exports.
 */

import type { PageInventoryResult } from './workstation-browser-snapshot'

export type SnapshotViewName = 'summary' | 'action_map' | 'focus' | 'content'

export interface SnapshotViewOptions {
  /** Maximum characters for the rendered view. Default varies per view. */
  maxChars?: number
  /** For `focus`: the @eN ref to center on. Required when view === 'focus'. */
  focusRef?: string
  /** For `focus`: how many sibling elements to include around the target. */
  focusNeighbors?: number
}

export interface SnapshotViewResult {
  view: SnapshotViewName
  text: string
  truncated: boolean
  /** When true, the requested focus ref was not found in the inventory. */
  focusMissing?: boolean
}

const DEFAULT_BUDGETS: Record<SnapshotViewName, number> = {
  summary: 600,
  action_map: 4000,
  focus: 2000,
  content: 4000
}

function truncate(text: string, maxChars: number): { text: string; truncated: boolean } {
  if (text.length <= maxChars) {
    return { text, truncated: false }
  }

  return { text: text.slice(0, maxChars), truncated: true }
}

/**
 * Compact page-state summary: URL host, title, element counts, warnings.
 * Sanitized — no raw page text or credential-bearing values.
 */
function renderSummary(inv: PageInventoryResult, maxChars: number): SnapshotViewResult {
  const lines: string[] = []

  try {
    const host = new URL(inv.url).hostname
    lines.push(`Host: ${host}`)
  } catch {
    lines.push(`URL: ${inv.url}`)
  }

  if (inv.title) {
    lines.push(`Title: ${inv.title}`)
  }

  lines.push(`Elements: ${inv.elements.length}`)
  lines.push(`Text chars: ${inv.totalTextChars}${inv.truncated ? ' (truncated)' : ''}`)

  if (inv.wallDetected) {
    lines.push(`⚠️ Wall: ${inv.wallReason || 'verification_required'}`)
  }

  if (inv.spaNotice) {
    lines.push(`Note: ${inv.spaNotice}`)
  }

  const { text, truncated } = truncate(lines.join('\n'), maxChars)

  return { view: 'summary', text, truncated }
}

/**
 * Action map: interactive elements with ref, role, label, testid.
 * Preserves @eN refs exactly as they appear in the inventory.
 */
function renderActionMap(inv: PageInventoryResult, maxChars: number): SnapshotViewResult {
  const lines: string[] = []

  if (inv.elements.length === 0) {
    lines.push('No interactive elements.')
  } else {
    for (const el of inv.elements) {
      const parts: string[] = [el.ref]
      parts.push(el.role || el.tag)

      if (el.label) {
        parts.push(`"${el.label.replace(/"/g, '\\"')}"`)
      }

      if (el.testid) {
        parts.push(`testid=${el.testid}`)
      }

      if (el.disabled) {
        parts.push('disabled')
      }

      lines.push(parts.join(' '))
    }
  }

  const { text, truncated } = truncate(lines.join('\n'), maxChars)

  return { view: 'action_map', text, truncated }
}

/**
 * Focus: subset of the inventory centered on a specific @eN ref.
 * Returns focusMissing=true when the ref is absent (fail-closed signal).
 */
function renderFocus(
  inv: PageInventoryResult,
  maxChars: number,
  focusRef: string,
  neighbors: number
): SnapshotViewResult {
  const idx = inv.elements.findIndex(el => el.ref === focusRef)

  if (idx === -1) {
    return {
      view: 'focus',
      text: `Focus target ${focusRef} not found in current snapshot (${inv.elements.length} elements).`,
      truncated: false,
      focusMissing: true
    }
  }

  const start = Math.max(0, idx - neighbors)
  const end = Math.min(inv.elements.length, idx + neighbors + 1)
  const window = inv.elements.slice(start, end)
  const lines: string[] = []

  for (let i = 0; i < window.length; i++) {
    const el = window[i]
    const marker = el.ref === focusRef ? '→' : ' '
    const label = el.label ? ` "${el.label.replace(/"/g, '\\"')}"` : ''
    const value = el.value ? ` value="${el.value.replace(/"/g, '\\"')}"` : ''
    const disabled = el.disabled ? ' disabled' : ''
    const testid = el.testid ? ` testid=${el.testid}` : ''
    lines.push(`${marker} [${el.ref}] ${el.role || el.tag}${label}${value}${disabled}${testid}`)
  }

  const { text, truncated } = truncate(lines.join('\n'), maxChars)

  return { view: 'focus', text, truncated }
}

/**
 * Content: main readable text of the page, preferring semantic containers.
 * Falls back to the full body text when no article/main landmark exists.
 * This view does NOT re-fetch from the DOM; it works with what the inventory
 * already captured (body text). A future enhancement could accept a richer
 * text source, but for now this keeps the contract narrow and side-effect-free.
 */
function renderContent(inv: PageInventoryResult, maxChars: number): SnapshotViewResult {
  // The inventory's .text field is already the body text (possibly truncated at
  // capture time). We apply the view-level budget on top of that.
  const raw = inv.text.trim()

  if (!raw) {
    return {
      view: 'content',
      text: 'No readable text captured.',
      truncated: false
    }
  }

  const { text, truncated } = truncate(raw, maxChars)

  return { view: 'content', text, truncated: truncated || inv.truncated }
}

/**
 * Render an opt-in snapshot view from an existing inventory.
 * Pure function — no CDP, no DOM, no async.
 */
export function renderSnapshotView(
  inv: PageInventoryResult,
  view: SnapshotViewName,
  options: SnapshotViewOptions = {}
): SnapshotViewResult {
  const maxChars = options.maxChars ?? DEFAULT_BUDGETS[view]

  switch (view) {
    case 'summary':
      return renderSummary(inv, maxChars)

    case 'action_map':
      return renderActionMap(inv, maxChars)
    case 'focus': {
      const ref = options.focusRef

      if (!ref) {
        return {
          view: 'focus',
          text: 'focus view requires a focusRef option.',
          truncated: false,
          focusMissing: true
        }
      }

      return renderFocus(inv, maxChars, ref, options.focusNeighbors ?? 3)
    }

    case 'content':
      return renderContent(inv, maxChars)

    default:
      return {
        view,
        text: `Unknown snapshot view: ${String(view)}`,
        truncated: false
      }
  }
}