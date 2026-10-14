import { act, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { WorkstationBrowserBridge, WorkstationBrowserState } from '@/app/browser/types'
import { PaneVisibleContext } from '@/components/pane-shell/pane-visibility'
import { $activeSessionId, $selectedStoredSessionId, $sessions } from '@/store/session'
import { makeSessionInfo } from '@/test/session-info'

import { WorkstationBrowserPane } from './workstation-browser-pane'

const restoredState: WorkstationBrowserState = {
  runtime: 'electron-chromium',
  ready: true,
  attached: false,
  viewportHost: null,
  backgroundCapable: true,
  paused: false,
  controlOwner: 'agent',
  controlReady: true,
  profilePath: 'test-profile',
  cacheBytes: 0,
  activeTabId: null,
  tabs: [],
  tasks: [
    {
      taskId: 'task-b',
      createdAt: '2026-09-19T00:00:00Z',
      updatedAt: '2026-09-19T00:00:00Z',
      panelHost: null,
      controlHost: null,
      sessionHost: 'session-b',
      kanbanCardId: null,
      runId: null,
      localConnection: null,
      status: 'parked',
      leaseState: null,
      parked: true,
      recoveryState: 'restored'
    }
  ],
  downloads: [],
  lastError: null
}

describe('WorkstationBrowserPane cold attach', () => {
  const originalRect = HTMLElement.prototype.getBoundingClientRect

  beforeEach(() => {
    HTMLElement.prototype.getBoundingClientRect = () =>
      ({ x: 0, y: 0, top: 0, left: 0, right: 900, bottom: 600, width: 900, height: 600, toJSON: () => ({}) }) as DOMRect
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      }
    )
    $activeSessionId.set('session-b')
    $selectedStoredSessionId.set(null)
    $sessions.set([makeSessionInfo({ id: 'session-b' })])
  })

  afterEach(() => {
    HTMLElement.prototype.getBoundingClientRect = originalRect
    vi.unstubAllGlobals()
    $activeSessionId.set(null)
    $selectedStoredSessionId.set(null)
    $sessions.set([])
    Reflect.deleteProperty(window, 'hermesDesktop')
  })

  it('discovers restored tasks before the first visual attach and binds that attach to the matching task', async () => {
    const attach = vi.fn(
      async (_bounds: unknown, _host?: string, _preferredTaskId?: string) =>
        ({ ...restoredState, attached: true, viewportHost: 'chat' }) as WorkstationBrowserState
    )

    const bridge = {
      ensure: vi.fn(async () => restoredState),
      attach,
      setBounds: vi.fn(async () => restoredState),
      detach: vi.fn(async () => restoredState),
      setVisible: vi.fn(async () => restoredState),
      onState: vi.fn(() => () => undefined)
    } as unknown as WorkstationBrowserBridge

    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true,
      value: { workstationBrowser: bridge }
    })

    render(<WorkstationBrowserPane />)

    await waitFor(() => expect(bridge.ensure).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(attach).toHaveBeenCalled())

    expect(attach.mock.calls[0]?.[2]).toBe('task-b')
    expect(attach).toHaveBeenCalledTimes(1)

    await act(async () => undefined)
  })

  it('keeps a hidden Browser pane from stealing the foreground native viewport', async () => {
    const attach = vi.fn(async () =>
      ({ ...restoredState, attached: true, viewportHost: 'chat' }) as WorkstationBrowserState
    )

    const setVisible = vi.fn(async () => restoredState)

    const bridge = {
      ensure: vi.fn(async () => restoredState),
      attach,
      setBounds: vi.fn(async () => restoredState),
      detach: vi.fn(async () => restoredState),
      setVisible,
      onState: vi.fn(() => () => undefined)
    } as unknown as WorkstationBrowserBridge

    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true,
      value: { workstationBrowser: bridge }
    })

    const surface = (visible: boolean) => (
      <PaneVisibleContext.Provider value={visible}>
        <WorkstationBrowserPane />
      </PaneVisibleContext.Provider>
    )

    const { rerender } = render(surface(false))

    await waitFor(() => expect(bridge.ensure).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(false, 'chat', 'session-b'))
    expect(attach).not.toHaveBeenCalled()

    rerender(surface(true))
    await waitFor(() => expect(attach).toHaveBeenCalledTimes(1))

    setVisible.mockClear()
    rerender(surface(false))
    await waitFor(() => expect(setVisible).toHaveBeenCalledWith(false, 'chat', 'session-b'))

    await act(async () => { $activeSessionId.set('session-new') })
    expect(attach).toHaveBeenCalledTimes(1)

    rerender(surface(true))
    await waitFor(() => expect(attach).toHaveBeenCalledTimes(2))
  })

  it('shows session-scoped native human review and acknowledges it only once', async () => {
    const { fireEvent, screen } = await import('@testing-library/react')

    const api = vi.fn(async (request: { path: string; method?: string; body?: unknown }) => {
      if (request.method === 'POST') {return { status: 'ready', readback_required: true, mutation_authorized: false }}

      return { handoffs: [{
        handoff_id: 'handoff-test-1', task_id: 'task-b', session_id: 'session-b',
        run_id: 'run-b', status: 'waiting-for-human', reason: 'uncertain_mutation_requires_review',
        requested_at: '2026-10-12T00:00:00Z'
      }] }
    })

    const bridge = {
      ensure: vi.fn(async () => restoredState),
      attach: vi.fn(async () => ({ ...restoredState, attached: true, viewportHost: 'chat' })),
      setBounds: vi.fn(async () => restoredState),
      detach: vi.fn(async () => restoredState),
      setVisible: vi.fn(async () => restoredState),
      onState: vi.fn(() => () => undefined)
    } as unknown as WorkstationBrowserBridge

    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true, value: { workstationBrowser: bridge, api }
    })
    render(<WorkstationBrowserPane />)
    const button = await screen.findByRole('button', { name: 'Acknowledge uncertain Browser operation' })
    fireEvent.click(button)
    await waitFor(() => {
      expect(api).toHaveBeenCalledWith(expect.objectContaining({
        path: '/api/workstation/handoffs/handoff-test-1/review',
        method: 'POST',
        body: { session_id: 'session-b', run_id: 'run-b' }
      }))
    })
    expect(screen.getByText(/readback is required/i)).toBeTruthy()
  })

})
