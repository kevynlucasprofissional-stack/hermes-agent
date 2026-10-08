import { act, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { WorkstationBrowserBridge, WorkstationBrowserState } from '@/app/browser/types'
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
})
