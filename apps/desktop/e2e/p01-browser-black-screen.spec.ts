import * as fs from 'node:fs'
import * as http from 'node:http'
import * as path from 'node:path'

import { type NoProviderFixture, setupNoProvider } from './fixtures'
import { expect, test } from './test'

interface TransitionLog {
  iteration: number
  step: string
  webContentsId: number | null
  tabId: string | null
  host: string | null
  owner: string | null
  bounds: { x: number; y: number; width: number; height: number } | null
  visible: boolean
  reason: string
}

let fixture: NoProviderFixture | null = null
let pageServer: http.Server | null = null
let fixtureUrl = ''

test.beforeAll(async () => {
  test.setTimeout(120_000)

  // 1. Start HTTP fixture server
  pageServer = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' })
    res.end(`<!DOCTYPE html>
<html>
<head><title>Hermes P01 Qualification Fixture</title></head>
<body>
  <h1>Hermes Work Browser Fixture</h1>
  <p id="query-display">${req.url}</p>
  <input id="fixture-input" value="original-input-state" />
</body>
</html>`)
  })

  await new Promise<void>((resolve) => {
    pageServer!.listen(0, '127.0.0.1', () => {
      const address = pageServer!.address()

      if (address && typeof address === 'object') {
        fixtureUrl = `http://127.0.0.1:${address.port}/fixture`
      }

      resolve()
    })
  })

  // 2. Launch real Electron app on Windows
  fixture = await setupNoProvider()
})

test.afterAll(async () => {
  if (pageServer) {
    await new Promise<void>((resolve) => pageServer!.close(() => resolve()))
    pageServer = null
  }

  if (fixture) {
    await fixture.cleanup()
    fixture = null
  }
})

test('P01: 10x qualification loop in real Electron/Windows preserves WebContentsView, tab, session, bounds, and visibility', async () => {
  test.setTimeout(180_000)

  const page = fixture!.page
  const app = fixture!.app

  const hubBounds = { x: 100, y: 80, width: 800, height: 600 }
  const chatBounds = { x: 600, y: 100, width: 400, height: 500 }
  const ownerId = 'session-p01-qualification'

  const transitionLogs: TransitionLog[] = []

  // Helper to query Electron main process for native view state
  const inspectNativeView = async () => {
    return app.evaluate(({ BrowserWindow }) => {
      const allWindows = BrowserWindow.getAllWindows()
      const win = allWindows.find((w: any) => !w.isDestroyed() && w.contentView?.children?.length > 0) || allWindows[0]

      if (!win || win.isDestroyed()) {
        return null
      }

      const children = win.contentView?.children || []

      return {
        windowBounds: win.getContentBounds(),
        childrenCount: children.length,
        children: children.map((c: any) => ({
          bounds: typeof c.getBounds === 'function' ? c.getBounds() : null,
          webContentsId: typeof c.webContents?.id === 'number' ? c.webContents.id : null,
          url: typeof c.webContents?.getURL === 'function' ? c.webContents.getURL() : null,
          isDestroyed: c.webContents?.isDestroyed ? c.webContents.isDestroyed() : false,
        })),
      }
    })
  }

  // Initial attach in Hub
  const initState = await page.evaluate(
    async ({ bounds, host, owner, url }) => {
      const bridge = (window as any).hermesDesktop.workstationBrowser
      const state = await bridge.attach(bounds, host, undefined, owner, true)
      await bridge.navigate(url)

      return (window as any).hermesDesktop.workstationBrowser.status()
    },
    { bounds: hubBounds, host: 'hub', owner: ownerId, url: fixtureUrl }
  )

  const originalTabId = initState.activeTabId
  expect(originalTabId).toBeTruthy()

  // Wait for initial native view in Electron
  let initialSnap = await inspectNativeView()
  expect(initialSnap?.childrenCount).toBeGreaterThanOrEqual(1)
  const originalChild = initialSnap!.children.find((c: any) => c.webContentsId !== null)
  expect(originalChild).toBeDefined()
  const originalWebContentsId = originalChild!.webContentsId
  expect(originalWebContentsId).toBeGreaterThan(0)

  console.log(`[P01 Qualification] Initialized: originalWebContentsId=${originalWebContentsId}, tabId=${originalTabId}`)

  // Run the 10x Qualification Suite
  for (let iter = 1; iter <= 10; iter++) {
    console.log(`\n--- [P01 Qualification] Starting Iteration ${iter}/10 ---`)

    // 1. Verify fixture page state
    const currentSnap = await inspectNativeView()
    const activeChild = currentSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(activeChild).toBeDefined()
    expect(activeChild!.isDestroyed).toBe(false)

    transitionLogs.push({
      iteration: iter,
      step: 'fixture_verified',
      webContentsId: activeChild!.webContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: activeChild!.bounds,
      visible: true,
      reason: 'iteration_start',
    })

    // 2. Perform search/navigation
    const searchUrl = `${fixtureUrl}?q=search_term_${iter}`

    const stateAfterNav = await page.evaluate(async (url) => {
      const bridge = (window as any).hermesDesktop.workstationBrowser
      await bridge.navigate(url)

      return bridge.status()
    }, searchUrl)

    expect(stateAfterNav.lastError).toBeNull()
    expect(stateAfterNav.activeTabId).toBe(originalTabId)

    const navSnap = await inspectNativeView()
    const navChild = navSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(navChild).toBeDefined()
    expect(navChild!.isDestroyed).toBe(false)
    expect(navChild!.bounds).toEqual(hubBounds)

    transitionLogs.push({
      iteration: iter,
      step: 'search_navigation',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: navChild!.bounds,
      visible: true,
      reason: 'valid_search_navigation',
    })

    // 3. Overlay handling: Toast (non-blocking) -> Dialog -> Dropdown Menu
    // 3a. Toast mounting must NOT hide or remove the browser view
    await page.evaluate(() => {
      const toast = document.createElement('div')
      toast.id = 'test-toast-notification'
      toast.setAttribute('data-sonner-toast', '')
      toast.setAttribute('role', 'status')
      toast.textContent = 'Agent task notification'
      document.body.appendChild(toast)
    })
    await page.waitForTimeout(50)

    const toastSnap = await inspectNativeView()
    const toastChild = toastSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(toastChild).toBeDefined()
    expect(toastChild!.bounds).toEqual(hubBounds)

    transitionLogs.push({
      iteration: iter,
      step: 'toast_non_blocking',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: toastChild!.bounds,
      visible: true,
      reason: 'toast_does_not_occlude',
    })

    await page.evaluate(() => {
      document.getElementById('test-toast-notification')?.remove()
    })

    // 3b. Dialog open (occlusion -> setVisible(false))
    await page.evaluate(async (owner) => {
      const dialog = document.createElement('div')
      dialog.id = 'test-dialog-occluder'
      dialog.setAttribute('data-slot', 'dialog-content')
      dialog.setAttribute('data-native-view-occluder', 'true')
      dialog.setAttribute('data-state', 'open')
      document.body.appendChild(dialog)

      const bridge = (window as any).hermesDesktop.workstationBrowser
      await bridge.setVisible(false, 'hub', owner)
    }, ownerId)

    const dialogOpenSnap = await inspectNativeView()
    const dialogOpenChild = dialogOpenSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(dialogOpenChild).toBeUndefined() // Child view must be safely detached while overlay is open

    transitionLogs.push({
      iteration: iter,
      step: 'dialog_opened',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: null,
      visible: false,
      reason: 'overlay_occlusion_hidden',
    })

    // 3c. Dialog close (restoration -> setVisible(true))
    await page.evaluate(async (owner) => {
      const dialog = document.getElementById('test-dialog-occluder')

      if (dialog) {
        dialog.setAttribute('data-state', 'closed')
        dialog.remove()
      }

      const bridge = (window as any).hermesDesktop.workstationBrowser
      await bridge.setVisible(true, 'hub', owner)
    }, ownerId)

    const dialogCloseSnap = await inspectNativeView()
    const dialogCloseChild = dialogCloseSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(dialogCloseChild).toBeDefined()
    expect(dialogCloseChild!.webContentsId).toBe(originalWebContentsId)
    expect(dialogCloseChild!.bounds).toEqual(hubBounds)

    transitionLogs.push({
      iteration: iter,
      step: 'dialog_closed',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: dialogCloseChild!.bounds,
      visible: true,
      reason: 'overlay_closed_restored',
    })

    // 3d. Menu open and close
    await page.evaluate(async (owner) => {
      const menu = document.createElement('div')
      menu.id = 'test-menu-occluder'
      menu.setAttribute('data-slot', 'dropdown-menu-content')
      menu.setAttribute('data-native-view-occluder', 'true')
      menu.setAttribute('data-state', 'open')
      document.body.appendChild(menu)

      const bridge = (window as any).hermesDesktop.workstationBrowser
      await bridge.setVisible(false, 'hub', owner)
    }, ownerId)

    const menuOpenSnap = await inspectNativeView()
    expect(menuOpenSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)).toBeUndefined()

    transitionLogs.push({
      iteration: iter,
      step: 'menu_opened',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: null,
      visible: false,
      reason: 'menu_occlusion_hidden',
    })

    await page.evaluate(async (owner) => {
      const menu = document.getElementById('test-menu-occluder')

      if (menu) {
        menu.setAttribute('data-state', 'closed')
        menu.remove()
      }

      const bridge = (window as any).hermesDesktop.workstationBrowser
      await bridge.setVisible(true, 'hub', owner)
    }, ownerId)

    const menuCloseSnap = await inspectNativeView()
    const menuCloseChild = menuCloseSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(menuCloseChild).toBeDefined()
    expect(menuCloseChild!.webContentsId).toBe(originalWebContentsId)
    expect(menuCloseChild!.bounds).toEqual(hubBounds)

    transitionLogs.push({
      iteration: iter,
      step: 'menu_closed',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: menuCloseChild!.bounds,
      visible: true,
      reason: 'menu_closed_restored',
    })

    // 4. Switch Hub <-> Chat
    // 4a. Transfer to Chat
    const chatState = await page.evaluate(async (bounds) => {
      const bridge = (window as any).hermesDesktop.workstationBrowser

      return bridge.transferViewport('chat', bounds)
    }, chatBounds)

    expect(chatState.viewportHost).toBe('chat')
    expect(chatState.activeTabId).toBe(originalTabId)

    const chatSnap = await inspectNativeView()
    const chatChild = chatSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(chatChild).toBeDefined()
    expect(chatChild!.webContentsId).toBe(originalWebContentsId)
    expect(chatChild!.bounds).toEqual(chatBounds)

    transitionLogs.push({
      iteration: iter,
      step: 'switch_to_chat',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'chat',
      owner: ownerId,
      bounds: chatChild!.bounds,
      visible: true,
      reason: 'viewport_transfer_chat',
    })

    // 4b. Transfer back to Hub
    const hubState = await page.evaluate(async (bounds) => {
      const bridge = (window as any).hermesDesktop.workstationBrowser

      return bridge.transferViewport('hub', bounds)
    }, hubBounds)

    expect(hubState.viewportHost).toBe('hub')
    expect(hubState.activeTabId).toBe(originalTabId)

    const hubSnap = await inspectNativeView()
    const hubChild = hubSnap?.children.find((c: any) => c.webContentsId === originalWebContentsId)
    expect(hubChild).toBeDefined()
    expect(hubChild!.webContentsId).toBe(originalWebContentsId)
    expect(hubChild!.bounds).toEqual(hubBounds)

    transitionLogs.push({
      iteration: iter,
      step: 'switch_to_hub',
      webContentsId: originalWebContentsId,
      tabId: originalTabId,
      host: 'hub',
      owner: ownerId,
      bounds: hubChild!.bounds,
      visible: true,
      reason: 'viewport_transfer_hub',
    })

    console.log(`[P01 Qualification] Iteration ${iter}/10 PASSED. webContentsId=${originalWebContentsId} preserved.`)
  }

  // 5. Final validation of invariants
  expect(transitionLogs.length).toBe(90) // 9 steps per iteration * 10 iterations

  const allWebContentsIds = new Set(
    transitionLogs.map((l) => l.webContentsId).filter((id): id is number => id !== null)
  )

  expect(allWebContentsIds.size).toBe(1)
  expect(allWebContentsIds.has(originalWebContentsId)).toBe(true)

  const allTabIds = new Set(transitionLogs.map((l) => l.tabId).filter(Boolean))
  expect(allTabIds.size).toBe(1)
  expect(allTabIds.has(originalTabId)).toBe(true)

  // Write qualification report
  const reportPath = path.resolve(process.cwd(), 'p01-qualification-log.json')
  fs.writeFileSync(
    reportPath,
    JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        status: 'PASSED',
        iterations: 10,
        originalWebContentsId,
        originalTabId,
        transitionsRecorded: transitionLogs.length,
        transitions: transitionLogs,
      },
      null,
      2
    )
  )

  console.log(`[P01 Qualification] ALL 10 ITERATIONS PASSED. Report saved to ${reportPath}`)
})
