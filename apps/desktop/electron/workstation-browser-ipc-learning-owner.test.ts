import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Mutable reference shared between the test scope and the mocked module factory.
let currentRuntime: any = null

vi.mock('electron', () => ({
  app: {
    whenReady: vi.fn().mockResolvedValue(undefined),
    getPath: vi.fn().mockReturnValue('/tmp/test'),
    on: vi.fn(),
    quit: vi.fn()
  },
  ipcMain: {
    handle: vi.fn(),
    on: vi.fn()
  },
  BrowserWindow: {
    fromWebContents: vi.fn().mockReturnValue({ id: 1 })
  },
  WebContentsView: vi.fn(),
  session: {
    defaultSession: {
      cookies: { get: vi.fn().mockResolvedValue([]) }
    }
  }
}))

vi.mock('./workstation-browser-runtime', () => ({
  getWorkstationBrowserRuntime: () => {
    if (!currentRuntime) {
      throw new Error('test setup error: currentRuntime not initialized')
    }
    return currentRuntime
  },
  registerWorkstationBrowserIpc: vi.fn()
}))

import { ipcMain } from 'electron'

describe('HLM-MVP P0a — Learning IPC Owner Binding', () => {
  let handlers: Record<string, (...args: any[]) => any>

  beforeEach(async () => {
    handlers = {}

    vi.mocked(ipcMain.handle).mockImplementation((channel: string, handler: any) => {
      handlers[channel] = handler
    })

    currentRuntime = {
      activeTabId: 'tab-owner',
      getWebContents: vi.fn(),
      startLearning: vi.fn().mockResolvedValue({ status: 'learning' }),
      stopLearning: vi.fn().mockResolvedValue({ status: 'idle' }),
      discardLearning: vi.fn().mockResolvedValue(undefined),
      getLearningStatus: vi.fn().mockReturnValue({ tabId: 'tab-owner', status: 'learning' }),
      setLearningIntensity: vi.fn().mockResolvedValue({ intensity: 'intensivo' }),
      answerLearningQuestion: vi.fn().mockResolvedValue({ state: 'confirmed' }),
      getLearningQuestions: vi.fn().mockReturnValue([])
    }

    // Import once; handlers are registered via registerWorkstationBrowserIpc which we call below
    const mod = await import('./workstation-browser-ipc')
    if (typeof (mod as any).registerWorkstationBrowserIpc === 'function') {
      ;(mod as any).registerWorkstationBrowserIpc()
    }
  })

  afterEach(() => {
    currentRuntime = null
    vi.restoreAllMocks()
  })

  function makeEvent(senderId: number) {
    return {
      sender: { id: senderId },
      frameId: 0,
      processId: 0,
      returnValue: undefined
    } as any
  }

  it('rejects learning:start when sender webContents does not match target tab', () => {
    currentRuntime.getWebContents.mockReturnValue({ id: 42 })
    const event = makeEvent(99)
    const handler = handlers['hermes:workstation-browser:learning:start']
    expect(handler).toBeDefined()
    expect(() => handler(event, 'tab-owner', 'sess-1', 'intensivo'))
      .toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.startLearning).not.toHaveBeenCalled()
  })

  it('allows learning:start when sender matches target tab webContents', async () => {
    currentRuntime.getWebContents.mockReturnValue({ id: 42 })
    const event = makeEvent(42)
    const handler = handlers['hermes:workstation-browser:learning:start']
    expect(handler).toBeDefined()
    await handler(event, 'tab-owner', 'sess-1', 'intensivo')
    expect(currentRuntime.startLearning).toHaveBeenCalledWith('tab-owner', 'sess-1', 'intensivo')
  })

  it('rejects learning:stop when sender does not match active learning session tab', () => {
    currentRuntime.getLearningStatus.mockReturnValue({ tabId: 'tab-owner', status: 'learning' })
    currentRuntime.getWebContents.mockReturnValue({ id: 42 })
    const event = makeEvent(99)
    const handler = handlers['hermes:workstation-browser:learning:stop']
    expect(handler).toBeDefined()
    expect(() => handler(event)).toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.stopLearning).not.toHaveBeenCalled()
  })

  it('rejects learning:intensity when sender does not match learning session tab', () => {
    currentRuntime.getLearningStatus.mockReturnValue({ tabId: 'tab-owner', status: 'learning' })
    currentRuntime.getWebContents.mockReturnValue({ id: 42 })
    const event = makeEvent(99)
    const handler = handlers['hermes:workstation-browser:learning:intensity']
    expect(handler).toBeDefined()
    expect(() => handler(event, 'discreto')).toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.setLearningIntensity).not.toHaveBeenCalled()
  })

  it('rejects learning:answer when sender does not match learning session tab', () => {
    currentRuntime.getLearningStatus.mockReturnValue({ tabId: 'tab-owner', status: 'learning' })
    currentRuntime.getWebContents.mockReturnValue({ id: 42 })
    const event = makeEvent(99)
    const handler = handlers['hermes:workstation-browser:learning:answer']
    expect(handler).toBeDefined()
    expect(() => handler(event, 'q-1', 'confirm', undefined))
      .toThrow(/learning_owner_mismatch/)
    expect(currentRuntime.answerLearningQuestion).not.toHaveBeenCalled()
  })
})