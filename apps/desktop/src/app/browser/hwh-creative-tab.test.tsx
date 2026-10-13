import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { WorkstationBrowserState } from './types'

import { BrowserView } from './index'

vi.mock('./task-rail', () => ({ TaskRail: () => null }))
vi.mock('./task-journal-drawer', () => ({ TaskJournalDrawer: () => null }))
vi.mock('@/app/creative-workspace', () => ({
  CreativeWorkspacePage: () => <div data-testid="creative-editor">Internal React Creative Editor</div>
}))

const browserState = {
  runtime: 'electron-chromium', ready: true, attached: true, viewportHost: 'hub',
  backgroundCapable: true, paused: false, controlOwner: 'human', controlReady: true,
  profilePath: 'test', cacheBytes: 0, activeTabId: 'web-1',
  tabs: [{ id: 'web-1', title: 'Web Page', url: 'https://example.test',
    active: true, loading: false, crashed: false, canGoBack: false, canGoForward: false }],
  tasks: [], downloads: [], lastError: null
} as unknown as WorkstationBrowserState

describe('Workstation Hub internal Creative tab', () => {
  let bridge: Record<string, ReturnType<typeof vi.fn>>

  beforeEach(() => {
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
      newTab: vi.fn().mockResolvedValue(browserState)
    }
    vi.stubGlobal('hermesDesktop', { workstationBrowser: bridge })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('opens Creative as an internal tab, parks Chromium, and restores the existing web tab without reloading', async () => {
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')

    fireEvent.click(screen.getByRole('button', { name: 'Abrir Creative Workstation' }))
    expect(await screen.findByTestId('creative-editor')).toBeTruthy()
    await waitFor(() => expect(bridge.setVisible).toHaveBeenCalledWith(false, 'hub'))
    expect(bridge.newTab).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Web Page' }))
    await waitFor(() => expect(bridge.setVisible).toHaveBeenCalledWith(true, 'hub'))
    expect(screen.getByTestId('creative-workstation-tab').className).toContain('hidden')
    expect(bridge.activateTab).toHaveBeenCalledWith('web-1')
    expect(bridge.newTab).not.toHaveBeenCalled()
  })

  it('opens Creative when requested by the desktop agent route intent', async () => {
    render(<MemoryRouter initialEntries={['/browser?creative=1']}><BrowserView /></MemoryRouter>)
    expect(await screen.findByTestId('creative-editor')).toBeTruthy()
    await waitFor(() => expect(bridge.setVisible).toHaveBeenCalledWith(false, 'hub'))
  })

  it('closes Creative using an explicit close button and restores the native tab without reloading it', async () => {
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir Creative Workstation' }))
    expect(await screen.findByTestId('creative-editor')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Fechar Creative Workstation' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Creative Workstation' })).toBeNull())
    expect(screen.getByTestId('creative-workstation-tab').className).toContain('hidden')
    expect(bridge.newTab).not.toHaveBeenCalled()
    await waitFor(() => expect(bridge.setVisible).toHaveBeenCalledWith(true, 'hub'))
  })

  it('Creative tab is focusable repeatedly without duplicate tab creation', async () => {
    render(<MemoryRouter><BrowserView /></MemoryRouter>)
    await screen.findByText('Web Page')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir Creative Workstation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Creative Workstation' }))
    expect(screen.getAllByRole('button', { name: 'Creative Workstation' })).toHaveLength(1)
    expect(bridge.newTab).not.toHaveBeenCalled()
  })
})
