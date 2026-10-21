import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { AiControlBadge } from './AiControlBadge'

declare global {
  interface Window {
    __hermesAiControlActive?: boolean
  }
}

describe('AiControlBadge', () => {
  beforeEach(() => {
    window.__hermesAiControlActive = false
  })

  afterEach(() => {
    delete window.__hermesAiControlActive
  })

  it('renders nothing when flag is false', () => {
    const { container } = render(<AiControlBadge />)
    expect(container.innerHTML).toBe('')
  })

  it('renders badge when flag is true', async () => {
    window.__hermesAiControlActive = true
    render(<AiControlBadge />)
    await waitFor(() => {
      expect(screen.getByText('🤖 AI Control')).toBeTruthy()
    })
  })

  it('toggles flag and badge visibility on Ctrl+Shift+A', async () => {
    render(<AiControlBadge />)
    expect(screen.queryByText('🤖 AI Control')).toBeNull()

    fireEvent.keyDown(window, { key: 'a', ctrlKey: true, shiftKey: true })
    expect(window.__hermesAiControlActive).toBe(true)
    await waitFor(() => {
      expect(screen.getByText('🤖 AI Control')).toBeTruthy()
    })

    fireEvent.keyDown(window, { key: 'A', ctrlKey: true, shiftKey: true })
    expect(window.__hermesAiControlActive).toBe(false)
    await waitFor(() => {
      expect(screen.queryByText('🤖 AI Control')).toBeNull()
    })
  })

  it('does not toggle on partial shortcut', () => {
    render(<AiControlBadge />)
    fireEvent.keyDown(window, { key: 'a', ctrlKey: true })
    expect(window.__hermesAiControlActive).toBe(false)
    expect(screen.queryByText('🤖 AI Control')).toBeNull()
  })
})