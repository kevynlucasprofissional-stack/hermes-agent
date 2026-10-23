import { useCallback, useEffect, useState } from 'react'

import type { WorkstationBrowserBridge } from './types'

export const NATIVE_VIEW_OCCLUDER_SELECTOR = '[data-native-view-occluder="true"]'

export function isElementActiveOccluder(el: Element): boolean {
  if (el.getAttribute('data-native-view-occluder') !== 'true') {
    return false
  }

  // If the element itself or any ancestor has data-state="closed", it is closing/closed and not occluding
  if (el.getAttribute('data-state') === 'closed' || Boolean(el.closest('[data-state="closed"]'))) {
    return false
  }

  // If the element itself or any ancestor has aria-hidden="true"
  if (el.getAttribute('aria-hidden') === 'true' || Boolean(el.closest('[aria-hidden="true"]'))) {
    return false
  }

  // Hidden attribute or inline styles
  if (el instanceof HTMLElement) {
    if (el.hidden || el.style.display === 'none' || el.style.visibility === 'hidden') {
      return false
    }
  }

  // Computed style check if available in DOM environment
  if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
    try {
      const style = window.getComputedStyle(el)

      if (style.display === 'none' || style.visibility === 'hidden') {
        return false
      }
    } catch {
      // Ignore if element is detached
    }
  }

  return true
}

export function isNativeViewOccluded(root: ParentNode = document): boolean {
  const elements = root.querySelectorAll(NATIVE_VIEW_OCCLUDER_SELECTOR)

  for (let i = 0; i < elements.length; i++) {
    if (isElementActiveOccluder(elements[i])) {
      return true
    }
  }

  return false
}

export interface NativeViewGate {
  /**
   * Whether this host has a reason of its own to keep the view off screen: an
   * inactive keep-alive tab (whose rect is identical to the visible one) or a
   * layout box that collapsed to nothing. Both leave the pane mounted over a
   * rect the user no longer sees it in, and the view is an OS-level child of
   * the window content view — it paints above the DOM and swallows the clicks
   * of whatever is actually on screen there.
   */
  enabled?: boolean
  ownerId?: string
  /** Bump to re-assert the current decision — `attach()` forces the view back on. */
  revision?: number
}

export interface NativeViewOcclusion {
  /** True while a surface carrying the occluder marker is mounted. */
  occluded: boolean
  /** Re-assert the composed decision now. */
  assertVisible: () => void
}

/**
 * The single authority over whether a host's native browser view is on screen.
 *
 * Parking removes the child view but keeps the page and its session alive, so
 * hiding the view for an overlay or an inactive tab costs a frame, not a task.
 */
export function useNativeViewOcclusion(
  bridge: WorkstationBrowserBridge | null | undefined,
  host: 'hub' | 'chat',
  gate?: NativeViewGate
): NativeViewOcclusion {
  const enabled = gate?.enabled ?? true
  const ownerId = gate?.ownerId
  const revision = gate?.revision ?? 0
  const [occluded, setOccluded] = useState(() => isNativeViewOccluded(document))

  const assertVisible = useCallback(() => {
    if (!bridge?.setVisible) {
      return
    }

    if (ownerId !== undefined) {
      void bridge.setVisible(enabled && !isNativeViewOccluded(document), host, ownerId)
    } else {
      void bridge.setVisible(enabled && !isNativeViewOccluded(document), host)
    }
  }, [bridge, enabled, host, ownerId])

  // Seed from the document: an overlay can already be open when the pane mounts
  // (switching tabs while a dialog is up) and the observer only fires on the
  // next mutation. Its scans are coalesced per task, so a burst of mutations
  // costs one whole-document query.
  useEffect(() => {
    let timer = 0

    setOccluded(isNativeViewOccluded(document))

    // Mutations arrive in bursts (one React commit, one streamed chunk); one
    // scan per task keeps this off the streaming-chat critical path while the
    // state above still bails out when the answer did not change.
    const observer = new MutationObserver(() => {
      if (timer) {
        return
      }

      timer = window.setTimeout(() => {
        timer = 0
        setOccluded(isNativeViewOccluded(document))
      }, 0)
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['data-native-view-occluder', 'data-state', 'aria-hidden', 'style', 'class', 'hidden']
    })

    return () => {
      observer.disconnect()

      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [])

  useEffect(() => {
    assertVisible()
  }, [assertVisible, occluded, revision])

  // The owning surface detaches or parks the native child on transition.
  // Unmount MUST NOT reveal it: that would resurrect Chromium above a new chat.

  return { assertVisible, occluded }
}
