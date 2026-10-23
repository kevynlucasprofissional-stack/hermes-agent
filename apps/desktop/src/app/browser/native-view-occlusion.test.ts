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

  it('closed occluder with data-state="closed" does NOT trigger native-view occlusion', () => {
    const dialog = document.createElement('div')
    dialog.setAttribute('data-slot', 'dialog-content')
    dialog.setAttribute('data-native-view-occluder', 'true')
    dialog.setAttribute('data-state', 'closed')
    document.body.appendChild(dialog)

    expect(isNativeViewOccluded(document)).toBe(false)
  })

  it('occluder whose ancestor has data-state="closed" does NOT trigger native-view occlusion', () => {
    const container = document.createElement('div')
    container.setAttribute('data-state', 'closed')

    const menu = document.createElement('div')
    menu.setAttribute('data-slot', 'dropdown-menu-content')
    menu.setAttribute('data-native-view-occluder', 'true')
    container.appendChild(menu)
    document.body.appendChild(container)

    expect(isNativeViewOccluded(document)).toBe(false)
  })

  it('occluder with aria-hidden="true" or hidden styles does NOT trigger native-view occlusion', () => {
    const hiddenEl = document.createElement('div')
    hiddenEl.setAttribute('data-native-view-occluder', 'true')
    hiddenEl.setAttribute('aria-hidden', 'true')
    document.body.appendChild(hiddenEl)

    expect(isNativeViewOccluded(document)).toBe(false)

    hiddenEl.removeAttribute('aria-hidden')
    hiddenEl.hidden = true
    expect(isNativeViewOccluded(document)).toBe(false)

    hiddenEl.hidden = false
    hiddenEl.style.display = 'none'
    expect(isNativeViewOccluded(document)).toBe(false)

    hiddenEl.style.display = ''
    hiddenEl.style.visibility = 'hidden'
    expect(isNativeViewOccluded(document)).toBe(false)
  })

  it('toast notification mounting into body does NOT trigger native-view occlusion', () => {
    const toast = document.createElement('div')
    toast.setAttribute('data-sonner-toast', '')
    toast.setAttribute('role', 'status')
    toast.textContent = 'Agent task finished'
    document.body.appendChild(toast)

    expect(isNativeViewOccluded(document)).toBe(false)
  })

  it('Radix transition from data-state="open" to data-state="closed" restores visibility via MutationObserver', async () => {
    const setVisible = vi.fn().mockResolvedValue({})
    const bridge = { setVisible } as unknown as WorkstationBrowserBridge

    const { renderHook, act } = await import('@testing-library/react')
    renderHook(() => useNativeViewOcclusion(bridge, 'hub'))

    const dialog = document.createElement('div')
    dialog.setAttribute('data-slot', 'dialog-content')
    dialog.setAttribute('data-native-view-occluder', 'true')
    dialog.setAttribute('data-state', 'open')

    await act(async () => {
      document.body.appendChild(dialog)
      await new Promise(resolve => setTimeout(resolve, 20))
    })

    expect(setVisible).toHaveBeenCalledWith(false, 'hub')
    setVisible.mockClear()

    // Radix animates out by changing data-state to "closed" before unmounting
    await act(async () => {
      dialog.setAttribute('data-state', 'closed')
      await new Promise(resolve => setTimeout(resolve, 20))
    })

    expect(setVisible).toHaveBeenCalledWith(true, 'hub')
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

    // 4. Overlay opens, then the hook unmounts while the overlay is still up:
    //    the view must stay parked. Re-showing it here would put the native
    //    view back on top of the overlay — the exact bug this guards against.
    await act(async () => {
      const menu = document.createElement('div')
      menu.setAttribute('data-slot', 'dropdown-menu-content')
      menu.setAttribute('data-native-view-occluder', 'true')
      document.body.appendChild(menu)
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    setVisible.mockClear()
    unmount()
    expect(setVisible).not.toHaveBeenCalledWith(true, 'chat')
  })

  it('does not resurrect a native view when an owner unmounts without an overlay', async () => {
    const setVisible = vi.fn().mockResolvedValue({})
    const bridge = { setVisible } as unknown as WorkstationBrowserBridge
    const { renderHook, waitFor } = await import('@testing-library/react')
    const { unmount } = renderHook(() => useNativeViewOcclusion(bridge, 'chat'))

    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(true, 'chat'))
    setVisible.mockClear()
    unmount()
    expect(setVisible).not.toHaveBeenCalledWith(true, 'chat')
  })

  it('parks the view for an overlay that is already open when the pane mounts', async () => {
    const setVisible = vi.fn().mockResolvedValue({})
    const bridge = { setVisible } as unknown as WorkstationBrowserBridge

    const overlay = document.createElement('div')
    overlay.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(overlay)

    const { renderHook, waitFor } = await import('@testing-library/react')
    renderHook(() => useNativeViewOcclusion(bridge, 'chat'))

    // No mutation is needed for this one — the mount scan alone must park it.
    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(false, 'chat'))
  })

  it('parks the view for a host whose own gate says it is not the visible surface', async () => {
    const setVisible = vi.fn().mockResolvedValue({})
    const bridge = { setVisible } as unknown as WorkstationBrowserBridge

    const { renderHook, waitFor } = await import('@testing-library/react')

    const { rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => useNativeViewOcclusion(bridge, 'chat', { enabled }),
      { initialProps: { enabled: false } }
    )

    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(false, 'chat'))

    rerender({ enabled: true })

    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(true, 'chat'))
  })

  it('re-asserts on a revision bump so a forced attach cannot leave the view over an overlay', async () => {
    const setVisible = vi.fn().mockResolvedValue({})
    const bridge = { setVisible } as unknown as WorkstationBrowserBridge

    const overlay = document.createElement('div')
    overlay.setAttribute('data-native-view-occluder', 'true')
    document.body.appendChild(overlay)

    const { renderHook, waitFor } = await import('@testing-library/react')

    const { rerender } = renderHook(
      ({ revision }: { revision: number }) => useNativeViewOcclusion(bridge, 'chat', { revision }),
      { initialProps: { revision: 0 } }
    )

    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(false, 'chat'))

    setVisible.mockClear()
    rerender({ revision: 1 })

    expect(setVisible).toHaveBeenCalledWith(false, 'chat')
  })
})
