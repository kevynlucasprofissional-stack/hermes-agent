import { beforeEach, expect, test, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  handlers: {} as Record<string, (...args: any[]) => any>,
  fromWebContents: vi.fn(),
  showMessageBox: vi.fn()
}))

vi.mock('electron', () => ({
  ipcMain: {handle: (name: string, fn: (...args: any[]) => any) => {mocks.handlers[name] = fn}},
  BrowserWindow: {fromWebContents: mocks.fromWebContents},
  dialog: {showMessageBox: mocks.showMessageBox}
}))

const runtime = vi.hoisted(() => ({
  isLearningControlOwner: vi.fn(),
  listVerifiedNavigationReviews: vi.fn(),
  reviewVerifiedNavigation: vi.fn(),
  listUncertainBatchReviews: vi.fn(),
  reviewUncertainBatch: vi.fn()
}))

vi.mock('./workstation-browser-runtime', () => ({
  getWorkstationBrowserRuntime: () => runtime
}))

import { registerWorkstationBrowserIpc } from './workstation-browser-ipc'

function setup() {
  const host = {
    isFocused: vi.fn(() => true),
    webContents: {mainFrame: {url: 'file:///hermes/index.html'}}
  }
  mocks.fromWebContents.mockReturnValue(host)
  runtime.isLearningControlOwner.mockReturnValue(true)
  runtime.listVerifiedNavigationReviews.mockReturnValue([])
  mocks.showMessageBox.mockResolvedValue({response: 0})
  runtime.reviewVerifiedNavigation.mockImplementation(async (_id, confirm) => ({
    status: await confirm({operationId:'op-local',safeUrl:'https://example.test/safe'})
      ? 'reconciled' : 'cancelled',
    operation_id: 'op-local'
  }))
  registerWorkstationBrowserIpc()
  return {host, event: {sender: host.webContents, senderFrame: host.webContents.mainFrame}}
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const key of Object.keys(mocks.handlers)) {delete mocks.handlers[key]}
})

test('human review can be requested only by owner top frame with focused window', async () => {
  const {host, event} = setup()
  const channel = mocks.handlers['hermes:workstation-browser:human-review:confirm-navigation']
  await expect(channel({...event, senderFrame: {}}, 'op-local')).rejects.toThrow(/human_review_owner_mismatch/)
  host.isFocused.mockReturnValue(false)
  await expect(channel(event, 'op-local')).rejects.toThrow(/human_review_owner_mismatch/)
  host.isFocused.mockReturnValue(true)
  await expect(channel(event, '../../../bad')).rejects.toThrow(/human_review_invalid_operation/)
  expect(mocks.showMessageBox).not.toHaveBeenCalled()
  expect(runtime.reviewVerifiedNavigation).not.toHaveBeenCalled()
})

test('native Cancel is default, JavaScript request alone does not approve', async () => {
  const {event} = setup()
  const handler = mocks.handlers['hermes:workstation-browser:human-review:confirm-navigation']
  const result = await handler(event, 'op-local')
  expect(result.status).toBe('cancelled')
  expect(mocks.showMessageBox).toHaveBeenCalledOnce()
  const args = mocks.showMessageBox.mock.calls[0][1]
  expect(args.defaultId).toBe(0)
  expect(args.cancelId).toBe(0)
})

test('only native affirmative action can reach guarded reconciliation', async () => {
  const {event} = setup()
  mocks.showMessageBox.mockResolvedValue({response: 1})
  const handler = mocks.handlers['hermes:workstation-browser:human-review:confirm-navigation']
  const result = await handler(event, 'op-local')
  expect(result.status).toBe('reconciled')
  expect(runtime.reviewVerifiedNavigation).toHaveBeenCalledOnce()
})

test('batch review requires owning focused main frame and validated operation ID', async () => {
  const {host, event} = setup()
  const handler = mocks.handlers['hermes:workstation-browser:human-review:confirm-batch']
  await expect(handler({...event, senderFrame: {}}, 'op-batch')).rejects.toThrow(/human_review_owner_mismatch/)
  host.isFocused.mockReturnValue(false)
  await expect(handler(event, 'op-batch')).rejects.toThrow(/human_review_owner_mismatch/)
  host.isFocused.mockReturnValue(true)
  await expect(handler(event, '../bad')).rejects.toThrow(/human_review_invalid_operation/)
  expect(runtime.reviewUncertainBatch).not.toHaveBeenCalled()
  expect(mocks.showMessageBox).not.toHaveBeenCalled()
})

test('batch review needs an affirmative native decision and never replays an action', async () => {
  const {event} = setup()
  runtime.reviewUncertainBatch.mockImplementation(async (_id, approve) => ({
    status: await approve({operationId: 'op-batch', sessionId: 'session-1', reason: 'click_postcondition_not_observed'})
      ? 'reconciled' : 'cancelled', operation_id: 'op-batch'
  }))
  const handler = mocks.handlers['hermes:workstation-browser:human-review:confirm-batch']
  const rejected = await handler(event, 'op-batch')
  expect(rejected.status).toBe('cancelled')
  const args = mocks.showMessageBox.mock.calls[0][1]
  expect(args.defaultId).toBe(0)
  expect(args.cancelId).toBe(0)
  expect(args.detail).toContain('does NOT')
  mocks.showMessageBox.mockResolvedValue({response: 1})
  const accepted = await handler(event, 'op-batch')
  expect(accepted.status).toBe('reconciled')
})