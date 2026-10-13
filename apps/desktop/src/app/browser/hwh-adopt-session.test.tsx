import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { requestGatewayForProfile } from '@/store/gateway'
import { openWorkstationBrowserPreview } from '@/store/preview'

import type { WorkstationBrowserState } from './types'

import { BrowserView } from './index'

vi.mock('./task-rail', () => ({ TaskRail: () => null }))
vi.mock('./task-journal-drawer', () => ({ TaskJournalDrawer: () => null }))
vi.mock('@/app/open-session', () => ({ openSession: vi.fn() }))
vi.mock('@/store/gateway', () => ({
  requestGatewayForProfile: vi.fn().mockResolvedValue({
    session_id: 'rt-session-adopted-1',
    stored_session_id: 'stored-session-adopted-1'
  })
}))
vi.mock('@/store/preview', () => ({
  $previewTabs: { get: () => [] },
  closeRightRail: vi.fn(),
  openWorkstationBrowserPreview: vi.fn()
}))

const browserState = {
  runtime: 'electron-chromium',
  ready: true,
  attached: true,
  viewportHost: 'hub',
  backgroundCapable: true,
  paused: false,
  controlOwner: 'human',
  controlReady: true,
  profilePath: 'test',
  cacheBytes: 0,
  activeTabId: 'web-1',
  tabs: [
    {
      id: 'web-1',
      title: 'Web Page',
      url: 'https://example.test',
      active: true,
      loading: false,
      crashed: false,
      canGoBack: false,
      canGoForward: false,
      ownerTaskId: null
    }
  ],
  tasks: [],
  downloads: [],
  lastError: null
} as unknown as WorkstationBrowserState

describe('HWH-03: Levar para sessão (adopt tab into session)', () => {
  let bridge: Record<string, ReturnType<typeof vi.fn>>

  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0)

      return 1
    })
    vi.stubGlobal('cancelAnimationFrame', () => {})
    bridge = {
      ensure: vi.fn().mockResolvedValue(browserState),
      onState: vi.fn().mockReturnValue(() => {}),
      attach: vi.fn().mockResolvedValue(browserState),
      setBounds: vi.fn().mockResolvedValue(browserState),
      setVisible: vi.fn().mockResolvedValue(browserState),
      detach: vi.fn().mockResolvedValue(browserState),
      activateTab: vi.fn().mockResolvedValue(browserState),
      newTab: vi.fn().mockResolvedValue(browserState),
      adoptTab: vi.fn().mockResolvedValue({
        success: true,
        tabId: 'web-1',
        taskId: 'rt-session-adopted-1',
        sessionId: 'rt-session-adopted-1',
        state: { ...browserState, tasks: [{ taskId: 'rt-session-adopted-1', sessionHost: 'rt-session-adopted-1' }] }
      })
    }
    vi.stubGlobal('hermesDesktop', { workstationBrowser: bridge })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('renders "Levar para sessão" button and adopts the active manual tab', async () => {
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')

    const adoptBtn = screen.getByRole('button', { name: 'Levar para sessão' })
    expect(adoptBtn).toBeTruthy()

    fireEvent.click(adoptBtn)

    await waitFor(() => {
      expect(bridge.adoptTab).toHaveBeenCalledWith('web-1', 'rt-session-adopted-1', 'rt-session-adopted-1')
    })
    expect(bridge.newTab).not.toHaveBeenCalled()
  })

  it('fails closed when Gateway session.create fails (never invents a local session)', async () => {
    vi.mocked(requestGatewayForProfile).mockRejectedValueOnce(new Error('Gateway offline'))
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')
    fireEvent.click(screen.getByRole('button', { name: 'Levar para sessão' }))
    expect(await screen.findByText(/Gateway offline/)).toBeTruthy()
    expect(bridge.adoptTab).not.toHaveBeenCalled()
    expect(openWorkstationBrowserPreview).not.toHaveBeenCalled()
  })

  it('binds the preview to the newly created session instead of the previous chat', async () => {
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')
    fireEvent.click(screen.getByRole('button', { name: 'Levar para sessão' }))
    await waitFor(() => expect(openWorkstationBrowserPreview).toHaveBeenCalledWith({
      fromHub: true, sessionId: 'stored-session-adopted-1'
    }))
  })

  it('prevents double-clicks / concurrent adoption attempts', async () => {
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')

    const adoptBtn = screen.getByRole('button', { name: 'Levar para sessão' })
    fireEvent.click(adoptBtn)
    fireEvent.click(adoptBtn)

    await waitFor(() => {
      expect(bridge.adoptTab).toHaveBeenCalledTimes(1)
    })
  })

  it('handles partial failure gracefully without crash', async () => {
    bridge.adoptTab = vi.fn().mockRejectedValue(new Error('Foreign session conflict'))
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')

    const adoptBtn = screen.getByRole('button', { name: 'Levar para sessão' })
    fireEvent.click(adoptBtn)

    await waitFor(() => {
      expect(screen.getByText(/Foreign session conflict/i)).toBeTruthy()
    })
  })
})
