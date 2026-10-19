import { describe, expect, it } from 'vitest'

import type { PageInventoryResult } from './workstation-browser-snapshot'
import { renderSnapshotView } from './workstation-browser-snapshot-views'

function makeInventory(overrides: Partial<PageInventoryResult> = {}): PageInventoryResult {
  return {
    url: 'https://app.example.com/dashboard',
    title: 'Dashboard',
    text: 'Welcome back. Here are your projects.',
    totalTextChars: 38,
    truncated: false,
    elements: [
      { ref: '@e1', tag: 'button', role: 'button', label: 'New Project', disabled: false },
      { ref: '@e2', tag: 'input', role: 'textbox', label: 'Search', disabled: false, testid: 'search-box' },
      { ref: '@e3', tag: 'a', role: 'link', label: 'Settings', disabled: false },
      { ref: '@e4', tag: 'button', role: 'button', label: 'Delete', disabled: true }
    ],
    ...overrides
  }
}

describe('B1.1 snapshot views', () => {
  describe('summary', () => {
    it('renders host, title, counts and warnings within budget', () => {
      const result = renderSnapshotView(makeInventory(), 'summary')
      expect(result.view).toBe('summary')
      expect(result.truncated).toBe(false)
      expect(result.text).toContain('Host: app.example.com')
      expect(result.text).toContain('Title: Dashboard')
      expect(result.text).toContain('Elements: 4')
    })

    it('reports wall detection when present', () => {
      const inv = makeInventory({ wallDetected: true, wallReason: 'captcha_required' })
      const result = renderSnapshotView(inv, 'summary')
      expect(result.text).toContain('Wall: captcha_required')
    })

    it('truncates when budget is exceeded', () => {
      const result = renderSnapshotView(makeInventory(), 'summary', { maxChars: 20 })
      expect(result.truncated).toBe(true)
      expect(result.text.length).toBeLessThanOrEqual(20)
    })
  })

  describe('action_map', () => {
    it('lists interactive elements with ref, role, label and testid', () => {
      const result = renderSnapshotView(makeInventory(), 'action_map')
      expect(result.view).toBe('action_map')
      expect(result.text).toContain('@e1 button "New Project"')
      expect(result.text).toContain('@e2 textbox "Search" testid=search-box')
      expect(result.text).toContain('@e4 button "Delete" disabled')
    })

    it('handles empty element list', () => {
      const inv = makeInventory({ elements: [] })
      const result = renderSnapshotView(inv, 'action_map')
      expect(result.text).toContain('No interactive elements.')
    })
  })

  describe('focus', () => {
    it('centers on the requested ref with neighbors', () => {
      const result = renderSnapshotView(makeInventory(), 'focus', { focusRef: '@e2', focusNeighbors: 1 })
      expect(result.view).toBe('focus')
      expect(result.focusMissing).toBeFalsy()
      expect(result.text).toContain('→ [@e2]')
      expect(result.text).toContain('[@e1]')
      expect(result.text).toContain('[@e3]')
      // @e4 should be outside the neighbor window
      expect(result.text).not.toContain('@e4')
    })

    it('returns focusMissing when ref is absent', () => {
      const result = renderSnapshotView(makeInventory(), 'focus', { focusRef: '@e99' })
      expect(result.focusMissing).toBe(true)
      expect(result.text).toContain('Focus target @e99 not found')
    })

    it('requires focusRef option', () => {
      const result = renderSnapshotView(makeInventory(), 'focus')
      expect(result.focusMissing).toBe(true)
      expect(result.text).toContain('focus view requires a focusRef')
    })
  })

  describe('element suppression for model-facing payload', () => {
    it('omits elements when a view projection is active (B1.1)', () => {
      // The runtime's snapshotForEntry spreads `elements` only when no view is
      // requested; opt-in views are already compact and must not duplicate the
      // inventory in structured form. This test validates the contract at the
      // view-rendering layer so the runtime spread stays safe to change.
      const inv = makeInventory()
      const viewResult = renderSnapshotView(inv, 'action_map')
      expect(viewResult.view).toBe('action_map')
      // View text carries refs; the redundant structured list is intentionally
      // absent from the projected payload.
      expect(viewResult.text).toContain('@e1')
      expect('elements' in viewResult).toBe(false)
    })
  })

  describe('content', () => {
    it('returns trimmed body text within budget', () => {
      const result = renderSnapshotView(makeInventory(), 'content')
      expect(result.view).toBe('content')
      expect(result.text).toContain('Welcome back')
      expect(result.truncated).toBe(false)
    })

    it('propagates inventory-level truncation', () => {
      const inv = makeInventory({ truncated: true })
      const result = renderSnapshotView(inv, 'content')
      expect(result.truncated).toBe(true)
    })

    it('reports absence of readable text', () => {
      const inv = makeInventory({ text: '   ' })
      const result = renderSnapshotView(inv, 'content')
      expect(result.text).toContain('No readable text captured.')
    })
  })
})