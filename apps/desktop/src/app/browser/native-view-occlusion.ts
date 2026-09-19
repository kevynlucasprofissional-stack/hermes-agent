import { useEffect } from 'react'

import type { WorkstationBrowserBridge } from './types'

export const NATIVE_VIEW_OCCLUDER_SELECTOR = [
  '[data-native-view-occluder="true"]',
  '[data-radix-menu-content]',
  '[data-slot="context-menu-content"]',
  '[data-slot="dropdown-menu-content"]',
  '[role="menu"]',
  '[data-radix-dialog-content]',
  '[data-slot="dialog-content"]',
  '[role="dialog"]',
  '[data-radix-select-content]',
  '[data-slot="select-content"]',
  '[data-slot="popover-content"]'
].join(', ')

export function isNativeViewOccluded(root: ParentNode = document): boolean {
  return Boolean(root.querySelector(NATIVE_VIEW_OCCLUDER_SELECTOR))
}

export function useNativeViewOcclusion(
  bridge: WorkstationBrowserBridge | null | undefined,
  host: 'hub' | 'chat'
): void {
  useEffect(() => {
    if (!bridge?.setVisible) {
      return
    }

    let isOverlayPresent = false

    const checkOverlay = () => {
      const active = isNativeViewOccluded(document)

      if (active !== isOverlayPresent) {
        isOverlayPresent = active
        void bridge.setVisible(!active, host)
      }
    }

    const observer = new MutationObserver(checkOverlay)
    observer.observe(document.body, { childList: true, subtree: true })

    return () => {
      observer.disconnect()

      if (isOverlayPresent) {
        void bridge.setVisible(true, host)
      }
    }
  }, [bridge, host])
}
