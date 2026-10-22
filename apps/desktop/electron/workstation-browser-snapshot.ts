/**
 * Hermes Workstation Browser Snapshot (AXTree & DOM Hybrid)
 *
 * Implements CDP Accessibility.getFullAXTree snapshot generation with safe
 * DOM element mapping and fallback to traditional DOM inventory script.
 * Preserves @eN refs in window.__hermesWorkstationRefs for action continuity.
 */

import crypto from 'node:crypto'

import type { WebContents } from 'electron'

export interface AXNode {
  nodeId: string
  role?: { value?: string }
  name?: { value?: string }
  value?: { value?: string }
  description?: { value?: string }
  ignored?: boolean
  backendDOMNodeId?: number
  properties?: Array<{ name: string; value?: { value?: unknown } }>
}

export interface ElementBounds {
  x: number
  y: number
  width: number
  height: number
}

export interface AXInventoryElement {
  ref: string
  tag: string
  role: string
  label: string
  value?: string
  disabled: boolean
  testid?: string
  name?: string
  bounds?: ElementBounds
}

export interface PageInventoryResult {
  url: string
  title: string
  text: string
  totalTextChars: number
  truncated: boolean
  elements: AXInventoryElement[]
  viewportHeight?: number
  spaNotice?: string
  wallDetected?: boolean
  wallReason?: string
}

const INTERACTIVE_AX_ROLES = new Set([
  'button',
  'link',
  'textbox',
  'searchbox',
  'checkbox',
  'radio',
  'combobox',
  'menuitem',
  'menuitemcheckbox',
  'menuitemradio',
  'option',
  'switch',
  'slider',
  'tab',
  'treeitem',
  'spinbutton',
  'popuponbutton',
  'popupbutton'
])

export function isAccessibilitySnapshotEnabled(): boolean {
  const env = process.env.HERMES_BROWSER_AXTREE_ENABLED

  return env === '1' || env === 'true'
}

export function isInteractiveAXNode(node: AXNode): boolean {
  if (node.ignored) {return false}
  const role = String(node.role?.value || '').toLowerCase()

  if (INTERACTIVE_AX_ROLES.has(role)) {return true}

  const isEditable = Boolean(node.properties?.some(p => p.name === 'editable' && Boolean(p.value?.value)))
  const isFocusable = Boolean(node.properties?.some(p => p.name === 'focusable' && p.value?.value === true))

  return isEditable || isFocusable
}

export function hasUsableAXTree(nodes: AXNode[]): boolean {
  if (!Array.isArray(nodes) || nodes.length === 0) {return false}

  return nodes.some(n => isInteractiveAXNode(n) && typeof n.backendDOMNodeId === 'number' && n.backendDOMNodeId > 0)
}

/**
 * Attempt to generate an interactive snapshot using CDP Accessibility tree.
 * Returns null on failure, missing capability, or when fallback to DOM is warranted.
 */
export async function tryAccessibilitySnapshot(
  wc: WebContents,
  cdp: (method: string, params?: any) => Promise<any>,
  full: boolean,
  maxTextChars = 8_000,
  maxElements = 120
): Promise<PageInventoryResult | null> {
  if (wc.isDestroyed()) {return null}

  try {
    // Capture document identity before the AX command. SPA/full reloads can
    // change the document while CDP backend nodes are being resolved.
    const documentBefore = (await wc.executeJavaScript(
      `(function () { /* __HERMES_AX_DOCUMENT_IDENTITY__ */
        return { url: location.href, documentToken: String(performance.timeOrigin) };
      })()`, true
    )) as { url?: string; documentToken?: string }

    if (!documentBefore?.url || !documentBefore?.documentToken) {return null}
    await cdp('Accessibility.enable')
    const tree = (await cdp('Accessibility.getFullAXTree', { depth: -1 })) as { nodes?: AXNode[] }
    const nodes = tree?.nodes

    if (!nodes || !hasUsableAXTree(nodes)) {
      return null
    }

    const interactiveNodes = nodes.filter(
      n => isInteractiveAXNode(n) && typeof n.backendDOMNodeId === 'number' && n.backendDOMNodeId > 0
    )

    if (interactiveNodes.length === 0) {
      return null
    }

    const elements: AXInventoryElement[] = []
    // Collect CDP remote handles in a snapshot-scoped group, then release once.
    const objectGroup = `hermes-ax-snapshot-${crypto.randomUUID()}`

    try {
      for (const node of interactiveNodes) {
        if (elements.length >= maxElements) {break}

        try {
          const resolved = (await cdp('DOM.resolveNode', {
            backendNodeId: node.backendDOMNodeId,
            objectGroup
          })) as { object?: { objectId?: string } }

          const objectId = resolved?.object?.objectId

          if (!objectId) {continue}

          const callRes = (await cdp('Runtime.callFunctionOn', {
            objectId,
            functionDeclaration: `function () {
            var el = this;
            var w = window;
            var state = w.__hermesWorkstationRefs;
            if (!state || state.href !== location.href) {
              state = { href: location.href, counter: 0, byRef: new Map(), byElement: new WeakMap() };
              w.__hermesWorkstationRefs = state;
            }
            var existingRef = state.byElement.get(el);
            var ref = existingRef || '@e' + (state.counter + 1);
            if (!existingRef) {
              state.byElement.set(el, ref);
              state.byRef.set(ref, el);
              var num = parseInt(ref.replace('@e', ''), 10);
              if (!isNaN(num) && num > state.counter) state.counter = num;
            }
            var tag = String(el.tagName || '').toLowerCase();
            var role = String(el.getAttribute && el.getAttribute('role') || tag || 'element');
            var rawValue = 'value' in el ? String(el.value || '') : '';
            var type = String(el.getAttribute && el.getAttribute('type') || '').toLowerCase();
            var val = type === 'password' && rawValue ? '[REDACTED]' : rawValue;
            var testid = String(el.getAttribute && (el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa')) || '').trim();
            var label = String(
              el.getAttribute && (el.getAttribute('aria-label') || el.getAttribute('alt') || el.getAttribute('title') || el.getAttribute('placeholder')) ||
              el.innerText || el.textContent || ''
            ).replace(/\\s+/g, ' ').trim().slice(0, 240);
            var rect = el.getBoundingClientRect();
            var bounds = (rect.width > 0 && rect.height > 0) ? {
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height)
            } : undefined;
            return {
              ref: ref,
              tag: tag,
              role: role,
              label: label,
              value: val ? val.slice(0, 240) : undefined,
              disabled: Boolean(el.disabled || (el.getAttribute && el.getAttribute('aria-disabled') === 'true')),
              testid: testid || undefined,
              name: (el.getAttribute && el.getAttribute('name')) || undefined,
              bounds: bounds
            };
          }`,
            returnByValue: true
          })) as { result?: { value?: AXInventoryElement } }

          const val = callRes?.result?.value

          if (val) {
            elements.push({
              ...val,
              disabled: Boolean(val.disabled)
            })
          }
        } catch {
          // Individual node resolution error: continue to next node
        }
      }
    } finally {
      try {
        await cdp('Runtime.releaseObjectGroup', { objectGroup })
      } catch {
        // Debugger can detach mid-snapshot; never block DOM fallback on cleanup.
      }
    }

    if (elements.length === 0) {
      return null
    }

    const docMeta = (await wc.executeJavaScript(
      `({
        url: location.href,
        title: document.title || '',
        documentToken: String(performance.timeOrigin),
        bodyText: String(document.body && document.body.innerText || '').replace(/\\u0000/g, ''),
      })`,
      true
    )) as { url: string; title: string; bodyText: string; documentToken?: string; totalTextChars?: number }

    if (docMeta.url !== documentBefore.url ||
        !docMeta.documentToken || docMeta.documentToken !== documentBefore.documentToken) {
      return null
    }

    const rawText = docMeta.bodyText || ''
    const text = rawText.slice(0, maxTextChars)
    const truncated = rawText.length > maxTextChars

    const viewportHeight = Number(
      await wc.executeJavaScript('window.innerHeight', true)
    ) || undefined

    return {
      url: docMeta.url,
      title: docMeta.title,
      text,
      totalTextChars: docMeta.totalTextChars ?? rawText.length,
      truncated,
      elements,
      viewportHeight
    }
  } catch {
    return null
  }
}
