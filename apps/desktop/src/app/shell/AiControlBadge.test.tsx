import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AiControlBadge } from './AiControlBadge'

describe('AiControlBadge (native authority)', () => {
  let original: PropertyDescriptor | undefined
  let push: (enabled: boolean) => void
  let unsubscribe: ReturnType<typeof vi.fn>
  let getStatus: ReturnType<typeof vi.fn>

  beforeEach(() => {
    original = Object.getOwnPropertyDescriptor(window, 'hermesDesktop')
    unsubscribe = vi.fn()
    getStatus = vi.fn().mockResolvedValue(false)
    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true, value: {
        aiControl: {
          getStatus,
          onStatus: vi.fn(callback => { push = callback; return unsubscribe })
        }
      }
    })
    window.__hermesAiControlActive = false
  })

  afterEach(() => {
    if (original) Object.defineProperty(window, 'hermesDesktop', original)
    else delete (window as any).hermesDesktop
    delete window.__hermesAiControlActive
  })

  it('starts disabled and cannot be enabled by a renderer keyboard event or spoofed JS flag', async () => {
    const { container } = render(<AiControlBadge />)
    await waitFor(() => expect(getStatus).toHaveBeenCalled())
    fireEvent.keyDown(window, { key: 'A', ctrlKey: true, shiftKey: true })
    window.__hermesAiControlActive = true
    expect(screen.queryByText('🤖 AI Control')).toBeNull()
    expect(container.textContent).toBe('')
  })

  it('reflects only main-process state changes and unsubscribes', async () => {
    const view = render(<AiControlBadge />)
    act(() => push(true))
    await waitFor(() => expect(screen.getByText('🤖 AI Control')).toBeTruthy())
    expect(window.__hermesAiControlActive).toBe(true)
    act(() => push(false))
    await waitFor(() => expect(screen.queryByText('🤖 AI Control')).toBeNull())
    view.unmount()
    expect(unsubscribe).toHaveBeenCalled()
  })
})
