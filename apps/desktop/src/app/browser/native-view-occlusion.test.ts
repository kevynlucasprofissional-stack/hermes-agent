import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { isNativeViewOccluded, useNativeViewOcclusion } from './native-view-occlusion'
import type { WorkstationBrowserBridge } from './types'

describe('Native View Occlusion', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('tooltip with popper wrapper does NOT trigger native-view occlusion', () => {
    // Radix Tooltip renders inside [data-radix-popper-content-wrapper] with [data-slot="tooltip-content"]
    const wrapper = document.createElement('div')
    wrapper.setAttribute('data-radix-popper-content-wrapper', '')

    const tip = document.createElement('div')
    tip.setAttribute('data-slot', 'tooltip-content')
    tip.textContent = 'Chat Row Tooltip'
    wrapper.appendChild(tip)
    document.body.appendChild(wrapper)

    expect(isNativeViewOccluded(document)).toBe(false)
  })

  it.each([
    ['dialog role', 'role', 'dialog'],
    ['menu role', 'role', 'menu'],
    ['popover slot', 'data-slot', 'popover-content']
  ])('unmarked %s does NOT trigger native-view occlusion', (_label, attribute, value) => {
    const element = document.createElement('div')
    element.setAttribute(attribute, value)
    document.body.appendChild(element)

    expect(isNativeViewOccluded(document)).toBe(false)
  })

  it('real dropdown menu content triggers native-view occlusion', () => {
    const menu = document.createElement('div')
    menu.setAttribute('data-slot', 'dropdown-menu-content')
    menu.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(menu)

    expect(isNativeViewOccluded(document)).toBe(true)
  })

  it('real dialog content triggers native-view occlusion', () => {
    const dialog = document.createElement('div')
    dialog.setAttribute('data-slot', 'dialog-content')
    dialog.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(dialog)

    expect(isNativeViewOccluded(document)).toBe(true)
  })

  it('real context menu content triggers native-view occlusion', () => {
    const contextMenu = document.createElement('div')
    contextMenu.setAttribute('data-slot', 'context-menu-content')
    contextMenu.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(contextMenu)

    expect(isNativeViewOccluded(document)).toBe(true)
  })

  it('real select content triggers native-view occlusion', () => {
    const select = document.createElement('div')
    select.setAttribute('data-slot', 'select-content')
    select.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(select)

    expect(isNativeViewOccluded(document)).toBe(true)
  })

  it('real popover content triggers native-view occlusion', () => {
    const popover = document.createElement('div')
    popover.setAttribute('data-slot', 'popover-content')
    popover.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(popover)

    expect(isNativeViewOccluded(document)).toBe(true)
  })

  it('useNativeViewOcclusion hook ignores tooltips and hides/restores native view for real occluders with host fencing', async () => {
    const setVisible = vi.fn().mockResolvedValue({})
    const bridge = { setVisible } as unknown as WorkstationBrowserBridge

    const { renderHook, act } = await import('@testing-library/react')
    const { unmount } = renderHook(() => useNativeViewOcclusion(bridge, 'chat'))

    // 1. Tooltip appears -> setVisible must NOT be called with false
    await act(async () => {
      const wrapper = document.createElement('div')
      wrapper.setAttribute('data-radix-popper-content-wrapper', '')
      const tip = document.createElement('div')
      tip.setAttribute('data-slot', 'tooltip-content')
      wrapper.appendChild(tip)
      document.body.appendChild(wrapper)
      // Allow MutationObserver to deliver
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    expect(setVisible).not.toHaveBeenCalledWith(false, 'chat')

    // 2. Real dialog appears -> setVisible must be called with (false, 'chat')
    let dialogEl: HTMLElement
    await act(async () => {
      dialogEl = document.createElement('div')
      dialogEl.setAttribute('data-slot', 'dialog-content')
      dialogEl.setAttribute('data-native-view-occluder', 'true')
      document.body.appendChild(dialogEl)
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    expect(setVisible).toHaveBeenCalledWith(false, 'chat')

    // 3. Dialog closes -> setVisible must be called with (true, 'chat')
    await act(async () => {
      dialogEl.remove()
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    expect(setVisible).toHaveBeenCalledWith(true, 'chat')

    // 4. Open dialog again, then unmount hook -> must restore visibility
    await act(async () => {
      const menu = document.createElement('div')
      menu.setAttribute('data-slot', 'dropdown-menu-content')
      menu.setAttribute('data-native-view-occluder', 'true')
      document.body.appendChild(menu)
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    setVisible.mockClear()
    unmount()
    expect(setVisible).toHaveBeenCalledWith(true, 'chat')
  })
})
