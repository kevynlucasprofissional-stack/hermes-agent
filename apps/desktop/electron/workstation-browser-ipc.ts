import { BrowserWindow, dialog, ipcMain, type IpcMainInvokeEvent } from 'electron'

import { pageWatchDisconnectForTab, pageWatchEnable, pageWatchPause, pageWatchUiState } from './workstation-browser-page-watch-service'
import {
  getWorkstationBrowserRuntime,
  type WorkstationBrowserBounds
} from './workstation-browser-runtime'

const MAX_EVENTS_ENDPOINT = 200

function senderWindow(event: IpcMainInvokeEvent): BrowserWindow {
  const window = BrowserWindow.fromWebContents(event.sender)

  if (!window) {
    throw new Error('Hermes Browser IPC sender is not a BrowserWindow.')
  }

  return window
}

function learningControlRuntime(event: IpcMainInvokeEvent, tabId?: string) {
  const window = senderWindow(event)
  const runtime = getWorkstationBrowserRuntime()

  if (event.sender !== window.webContents || !event.senderFrame
    || event.senderFrame !== window.webContents.mainFrame
    || !runtime.isLearningControlOwner(window, tabId)) {
    throw new Error('learning_owner_mismatch: IPC sender is not the owning host window main frame')
  }

  return runtime
}

function pageWatchOwner(event: IpcMainInvokeEvent, tabId: string): void {
  learningControlRuntime(event,tabId)

  if (getWorkstationBrowserRuntime().state().activeTabId !== tabId) {
    throw new Error('page_watch_wrong_active_tab')
  }
}

export function registerWorkstationBrowserIpc(): void {
  ipcMain.handle('hermes:workstation-browser:page-watch:status', (event, tabId) => {
    const id=String(tabId ?? '')
    pageWatchOwner(event,id)

    return pageWatchUiState(id)
  })
  ipcMain.handle('hermes:workstation-browser:page-watch:enable', (event, tabId, selector) => {
    const id=String(tabId ?? '')
    pageWatchOwner(event,id)

    return pageWatchEnable(id,String(selector ?? ''))
  })
  ipcMain.handle('hermes:workstation-browser:page-watch:pause', (event, tabId) => {
    const id=String(tabId ?? '')
    pageWatchOwner(event,id)

    return pageWatchPause(id)
  })
  ipcMain.handle('hermes:workstation-browser:human-review:list-batches', event => {
    const window = senderWindow(event)
    const runtime = getWorkstationBrowserRuntime()
    if (event.sender !== window.webContents ||
        event.senderFrame !== window.webContents.mainFrame ||
        !runtime.isLearningControlOwner(window)) {throw new Error('human_review_owner_mismatch')}
    return runtime.listUncertainBatchReviews()
  })
  ipcMain.handle('hermes:workstation-browser:human-review:confirm-batch', async (event, operationId) => {
    const window = senderWindow(event)
    const runtime = getWorkstationBrowserRuntime()
    if (event.sender !== window.webContents ||
        event.senderFrame !== window.webContents.mainFrame ||
        !runtime.isLearningControlOwner(window) || !window.isFocused()) {
      throw new Error('human_review_owner_mismatch')
    }
    if (typeof operationId !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(operationId)) {
      throw new Error('human_review_invalid_operation')
    }
    return runtime.reviewUncertainBatch(operationId, async review => {
      const result = await dialog.showMessageBox(window, {
        type: 'warning',
        title: 'Hermes Browser — uncertain batch review',
        message: 'Did you independently inspect the target conversation and its actual result?',
        detail: `Session: ${review.sessionId}\nOperation: ${review.operationId}\nUncertainty: ${review.reason}\n` +
          (review.webContentsId === -1 ? 'The task was restored without loading its external page. ' : '') +
          'Confirm ONLY after independently inspecting the target conversation. This releases the fence; it does NOT ' +
          'send a message, replay the batch, or prove external delivery. Cancel if the outcome is unknown.',
        buttons: ['Cancel — keep blocked', 'I inspected the result — release this fence'],
        defaultId: 0, cancelId: 0, noLink: true
      })
      return result.response === 1
    })
  })
  ipcMain.handle('hermes:workstation-browser:human-review:list-navigation', event => {
    const window = senderWindow(event)
    const runtime = getWorkstationBrowserRuntime()
    if (event.sender !== window.webContents ||
        event.senderFrame !== window.webContents.mainFrame ||
        !runtime.isLearningControlOwner(window)) {
      throw new Error('human_review_owner_mismatch')
    }
    return runtime.listVerifiedNavigationReviews()
  })
  ipcMain.handle('hermes:workstation-browser:human-review:confirm-navigation', async (event, operationId) => {
    const window = senderWindow(event)
    const runtime = getWorkstationBrowserRuntime()
    if (event.sender !== window.webContents ||
        event.senderFrame !== window.webContents.mainFrame ||
        !runtime.isLearningControlOwner(window) || !window.isFocused()) {
      throw new Error('human_review_owner_mismatch')
    }
    if (typeof operationId !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(operationId)) {
      throw new Error('human_review_invalid_operation')
    }
    return runtime.reviewVerifiedNavigation(operationId, async review => {
      const result = await dialog.showMessageBox(window, {
        type: 'warning',
        title: 'Hermes Browser — verified local navigation',
        message: 'Reconcile this locally verified navigation?',
        detail: 'Durable owner receipt and live readback prove local navigation to ' +
          review.safeUrl + '. No click, batch, message or external delivery is approved. Operation: ' +
          review.operationId,
        buttons: ['Cancel — keep blocked', 'Confirm verified local navigation'],
        defaultId: 0, cancelId: 0, noLink: true
      })
      return result.response === 1
    })
  })
  ipcMain.handle('hermes:workstation-browser:status', () => getWorkstationBrowserRuntime().ensure())
  ipcMain.handle('hermes:workstation-browser:ensure', () => getWorkstationBrowserRuntime().ensure())
  ipcMain.handle('hermes:workstation-browser:resources', () => getWorkstationBrowserRuntime().resources())
  ipcMain.handle('hermes:workstation-browser:events', (_event, taskId, limit) =>
    getWorkstationBrowserRuntime().events(
      typeof taskId === 'string' ? taskId : null,
      typeof limit === 'number' ? limit : MAX_EVENTS_ENDPOINT
    )
  )
  ipcMain.handle('hermes:workstation-browser:new-tab', (_event, target) =>
    getWorkstationBrowserRuntime().createTab(String(target ?? 'about:blank'), true)
  )
  ipcMain.handle('hermes:workstation-browser:activate-tab', (_event, tabId) =>
    getWorkstationBrowserRuntime().activateTab(String(tabId ?? ''))
  )
  ipcMain.handle('hermes:workstation-browser:close-tab', (_event, tabId) => {
    pageWatchDisconnectForTab(String(tabId ?? ''))

    return getWorkstationBrowserRuntime().closeTab(String(tabId ?? ''))
  })
  ipcMain.handle('hermes:workstation-browser:navigate', async (_event, target) =>
    getWorkstationBrowserRuntime().navigate(String(target ?? ''))
  )
  ipcMain.handle('hermes:workstation-browser:back', () => getWorkstationBrowserRuntime().back())
  ipcMain.handle('hermes:workstation-browser:forward', () => getWorkstationBrowserRuntime().forward())
  ipcMain.handle('hermes:workstation-browser:reload', () => getWorkstationBrowserRuntime().reload())
  ipcMain.handle('hermes:workstation-browser:stop', () => getWorkstationBrowserRuntime().stop())
  ipcMain.handle('hermes:workstation-browser:focus', () => getWorkstationBrowserRuntime().focus())
  ipcMain.handle('hermes:workstation-browser:attach', (event, bounds, host, preferredTaskId, ownerId, visible) =>
    getWorkstationBrowserRuntime().attach(
      senderWindow(event),
      bounds as WorkstationBrowserBounds,
      typeof host === 'string' ? host : 'hub',
      typeof preferredTaskId === 'string' ? preferredTaskId : null,
      typeof ownerId === 'string' ? ownerId : null,
      typeof visible === 'boolean' ? visible : undefined
    )
  )
  ipcMain.handle('hermes:workstation-browser:set-bounds', (event, bounds, expectedHost, expectedOwnerId) =>
    getWorkstationBrowserRuntime().setBounds(
      senderWindow(event),
      bounds as WorkstationBrowserBounds,
      typeof expectedHost === 'string' ? expectedHost : undefined,
      typeof expectedOwnerId === 'string' ? expectedOwnerId : undefined
    )
  )
  ipcMain.handle('hermes:workstation-browser:detach', (event, expectedHost, expectedOwnerId) =>
    getWorkstationBrowserRuntime().detach(
      senderWindow(event),
      typeof expectedHost === 'string' ? expectedHost : undefined,
      typeof expectedOwnerId === 'string' ? expectedOwnerId : undefined
    )
  )
  ipcMain.handle('hermes:workstation-browser:set-visible', (_event, visible, expectedHost, expectedOwnerId) =>
    getWorkstationBrowserRuntime().setVisible(
      Boolean(visible),
      typeof expectedHost === 'string' ? expectedHost : undefined,
      typeof expectedOwnerId === 'string' ? expectedOwnerId : undefined
    )
  )
  ipcMain.handle('hermes:workstation-browser:clear-error', () => getWorkstationBrowserRuntime().clearError())
  ipcMain.handle('hermes:workstation-browser:transfer-viewport', (event, targetHost, bounds) =>
    getWorkstationBrowserRuntime().transferViewport(
      senderWindow(event),
      typeof targetHost === 'string' ? targetHost : 'hub',
      bounds as WorkstationBrowserBounds
    )
  )
  ipcMain.handle('hermes:workstation-browser:list-tasks', () => getWorkstationBrowserRuntime().listTasks())
  ipcMain.handle('hermes:workstation-browser:show-task', (event, taskId, bounds, host) =>
    getWorkstationBrowserRuntime().showTask(
      String(taskId ?? ''),
      senderWindow(event),
      bounds as WorkstationBrowserBounds,
      typeof host === 'string' ? host : 'hub'
    )
  )
  ipcMain.handle('hermes:workstation-browser:hide-task', (_event, taskId) =>
    getWorkstationBrowserRuntime().hideTask(String(taskId ?? ''))
  )
  ipcMain.handle('hermes:workstation-browser:park-task', (_event, taskId) =>
    getWorkstationBrowserRuntime().parkTask(String(taskId ?? ''))
  )
  ipcMain.handle('hermes:workstation-browser:destroy-task', (_event, taskId) =>
    getWorkstationBrowserRuntime().destroyTask(String(taskId ?? ''))
  )
  ipcMain.handle('hermes:workstation-browser:clear-parked-tasks', (_event, eligibleTaskIds) =>
    getWorkstationBrowserRuntime().clearParkedTasks(
      Array.isArray(eligibleTaskIds)
        ? eligibleTaskIds.filter((taskId): taskId is string => typeof taskId === 'string')
        : []
    )
  )
  ipcMain.handle('hermes:workstation-browser:pause', () => getWorkstationBrowserRuntime().pause())
  ipcMain.handle('hermes:workstation-browser:resume', () => getWorkstationBrowserRuntime().resume())
  ipcMain.handle('hermes:workstation-browser:take-control', (_event, taskId, sessionId) => {
    const tabId=getWorkstationBrowserRuntime().state().activeTabId

    if (tabId) {pageWatchPause(tabId,'human_takeover')}

    return getWorkstationBrowserRuntime().takeControl(
      typeof taskId === 'string' ? taskId : undefined,
      typeof sessionId === 'string' ? sessionId : undefined
    )
  })
  ipcMain.handle('hermes:workstation-browser:release-control', (_event, taskId) =>
    getWorkstationBrowserRuntime().releaseControl(typeof taskId === 'string' ? taskId : undefined)
  )
  ipcMain.handle('hermes:workstation-browser:renew-control', (_event, taskId) =>
    getWorkstationBrowserRuntime().renewControl(typeof taskId === 'string' ? taskId : undefined)
  )
  ipcMain.handle('hermes:workstation-browser:expire-control', (_event, taskId) =>
    getWorkstationBrowserRuntime().expireControl(typeof taskId === 'string' ? taskId : undefined)
  )
  ipcMain.handle('hermes:workstation-browser:cleanup-cache', (_event, force) =>
    getWorkstationBrowserRuntime().cleanupCache(Boolean(force))
  )
  ipcMain.handle('hermes:workstation-browser:task-journal', (_event, taskId) =>
    getWorkstationBrowserRuntime().getTaskJournal(String(taskId ?? ''))
  )
  ipcMain.handle('hermes:workstation-browser:adopt-tab', (_event, tabId, sessionId, taskId) =>
    getWorkstationBrowserRuntime().adoptTab(
      String(tabId ?? ''),
      String(sessionId ?? ''),
      typeof taskId === 'string' ? taskId : undefined
    )
  )
  ipcMain.handle('hermes:workstation-browser:learning:start', (event, tabId, sessionId, intensity) => {
    learningControlRuntime(event)

    const runtime = getWorkstationBrowserRuntime()
    const targetTabId = typeof tabId === 'string' ? tabId : runtime.state().activeTabId

    if (targetTabId) {
      const expectedWc = runtime.getWebContents(targetTabId)

      if (!expectedWc || !runtime.isLearningControlOwner(senderWindow(event), targetTabId)) {
        throw new Error('learning_owner_mismatch: IPC sender does not match target tab webContents')
      }
    }

    return runtime.startLearning(
      typeof tabId === 'string' ? tabId : undefined,
      typeof sessionId === 'string' ? sessionId : undefined,
      typeof intensity === 'string' ? intensity : undefined
    )
  })
  ipcMain.handle('hermes:workstation-browser:learning:stop', event => {
    learningControlRuntime(event)

    const runtime = getWorkstationBrowserRuntime()
    const status = runtime.getLearningStatus()

    if (status?.tabId) {
      const expectedWc = runtime.getWebContents(status.tabId)

      if (!expectedWc || !runtime.isLearningControlOwner(senderWindow(event), status.tabId)) {
        throw new Error('learning_owner_mismatch: IPC sender does not match learning session tab')
      }
    }

    return runtime.stopLearning()
  })
  ipcMain.handle('hermes:workstation-browser:learning:discard', event => {
    learningControlRuntime(event)

    const runtime = getWorkstationBrowserRuntime()
    const status = runtime.getLearningStatus()

    if (status?.tabId) {
      const expectedWc = runtime.getWebContents(status.tabId)

      if (!expectedWc || !runtime.isLearningControlOwner(senderWindow(event), status.tabId)) {
        throw new Error('learning_owner_mismatch: IPC sender does not match learning session tab')
      }
    }

    return runtime.discardLearning()
  })
  ipcMain.handle('hermes:workstation-browser:learning:status', event => {
    learningControlRuntime(event)

    return getWorkstationBrowserRuntime().getLearningStatus()
  })
  ipcMain.handle('hermes:workstation-browser:learning:intensity', (event, intensity) => {
    learningControlRuntime(event)

    const runtime = getWorkstationBrowserRuntime()
    const status = runtime.getLearningStatus()

    if (status?.tabId) {
      const expectedWc = runtime.getWebContents(status.tabId)

      if (!expectedWc || !runtime.isLearningControlOwner(senderWindow(event), status.tabId)) {
        throw new Error('learning_owner_mismatch: IPC sender does not match learning session tab')
      }
    }

    return runtime.setLearningIntensity(String(intensity ?? 'intensivo'))
  })
  ipcMain.handle('hermes:workstation-browser:learning:answer', (event, questionId, action, userCorrection) => {
    learningControlRuntime(event)

    const runtime = getWorkstationBrowserRuntime()
    const status = runtime.getLearningStatus()

    if (status?.tabId) {
      const expectedWc = runtime.getWebContents(status.tabId)

      if (!expectedWc || !runtime.isLearningControlOwner(senderWindow(event), status.tabId)) {
        throw new Error('learning_owner_mismatch: IPC sender does not match learning session tab')
      }
    }

    return runtime.answerLearningQuestion(
      String(questionId ?? ''),
      String(action ?? 'confirm'),
      typeof userCorrection === 'string' ? userCorrection : undefined
    )
  })
  ipcMain.handle('hermes:workstation-browser:learning:questions', event => {
    learningControlRuntime(event)

    return getWorkstationBrowserRuntime().getLearningQuestions()
  })
}
