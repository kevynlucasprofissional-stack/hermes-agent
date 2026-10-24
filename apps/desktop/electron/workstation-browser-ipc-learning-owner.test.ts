import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let currentRuntime: any = null

vi.mock('electron', () => ({
  app: { whenReady: vi.fn().mockResolvedValue(undefined), getPath: vi.fn().mockReturnValue('/tmp/test'), on: vi.fn(), quit: vi.fn() },
  ipcMain: { handle: vi.fn(), on: vi.fn() },
  BrowserWindow: { fromWebContents: vi.fn() },
  WebContentsView: vi.fn(),
  session: { defaultSession: { cookies: { get: vi.fn().mockResolvedValue([]) } } }
}))

vi.mock('./workstation-browser-runtime', () => ({
  getWorkstationBrowserRuntime: () => {
    if (!currentRuntime) {throw new Error('test setup error: currentRuntime not initialized')}
    return currentRuntime
  },
  registerWorkstationBrowserIpc: vi.fn()
}))

import { BrowserWindow, ipcMain } from 'electron'

describe('learning control IPC uses the owning host window', () => {
  let handlers: Record<string, (...args: any[]) => any>
  let host: any

  beforeEach(async () => {
    handlers = {}
    host = { id: 1, webContents: { id: 99, mainFrame: { url: 'file:///hermes/index.html' } } }
    vi.mocked(BrowserWindow.fromWebContents).mockReturnValue(host)
    vi.mocked(ipcMain.handle).mockImplementation((channel: string, handler: any) => {handlers[channel] = handler})
    currentRuntime = {
      state: vi.fn().mockReturnValue({ activeTabId: 'tab-owner' }),
      getWebContents: vi.fn().mockReturnValue({ id: 42 }),
      isLearningControlOwner: vi.fn((window: unknown, tabId?: string) => window === host && (!tabId || tabId === 'tab-owner')),
      startLearning: vi.fn().mockResolvedValue({ status: 'learning' }),
      stopLearning: vi.fn().mockResolvedValue({ status: 'idle' }),
      discardLearning: vi.fn().mockResolvedValue(undefined),
      getLearningStatus: vi.fn().mockReturnValue({ tabId: 'tab-owner', status: 'learning' }),
      setLearningIntensity: vi.fn().mockResolvedValue({ intensity: 'intensivo' }),
      answerLearningQuestion: vi.fn().mockResolvedValue({ state: 'confirmed' }),
      getLearningQuestions: vi.fn().mockReturnValue([])
    }
    const mod = await import('./workstation-browser-ipc')
    mod.registerWorkstationBrowserIpc()
  })

  afterEach(() => {
    currentRuntime = null
    vi.restoreAllMocks()
  })

  function event() {
    return { sender: host.webContents, senderFrame: host.webContents.mainFrame } as any
  }

  it('allows the owning host to start a distinct browser webContents', async () => {
    await handlers['hermes:workstation-browser:learning:start'](event(), 'tab-owner', 'sess-1', 'intensivo')
    expect(currentRuntime.startLearning).toHaveBeenCalledWith('tab-owner', 'sess-1', 'intensivo')
  })

  it('rejects a page sender even when its id matches the target tab', () => {
    const page = { ...event(), sender: { id: 42 } }
    expect(() => handlers['hermes:workstation-browser:learning:start'](page, 'tab-owner')).toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.startLearning).not.toHaveBeenCalled()
  })

  it('rejects a target outside the host runtime', () => {
    expect(() => handlers['hermes:workstation-browser:learning:start'](event(), 'foreign-tab')).toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.startLearning).not.toHaveBeenCalled()
  })

  it.each(['stop', 'discard', 'intensity', 'answer'])('rejects %s from another window', (operation) => {
    currentRuntime.isLearningControlOwner.mockReturnValue(false)
    expect(() => handlers['hermes:workstation-browser:learning:' + operation](event(), 'q-1', 'confirm')).toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.stopLearning).not.toHaveBeenCalled()
    expect(currentRuntime.discardLearning).not.toHaveBeenCalled()
    expect(currentRuntime.setLearningIntensity).not.toHaveBeenCalled()
    expect(currentRuntime.answerLearningQuestion).not.toHaveBeenCalled()
  })

  it('rejects child-frame control commands', () => {
    expect(() => handlers['hermes:workstation-browser:learning:start']({
      ...event(), senderFrame: { url: 'file:///hermes/child.html' }
    }, 'tab-owner')).toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.startLearning).not.toHaveBeenCalled()
  })
})
