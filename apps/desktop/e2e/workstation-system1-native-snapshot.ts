import fs from 'node:fs'
import http from 'node:http'
import { performance } from 'node:perf_hooks'
import { app, BrowserWindow } from 'electron'
import {
  getWorkstationBrowserRuntime,
  workstationBrowserControlPath,
} from '../electron/workstation-browser-runtime'

async function main(): Promise<void> {
  await app.whenReady()
  const runtime = getWorkstationBrowserRuntime()
  const window = new BrowserWindow({
    show: false, focusable: true, skipTaskbar: true,
    x: -22000, y: -22000, width: 1300, height: 850,
  })
  const server = http.createServer((_req, res) => {
    res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'})
    res.end('<!doctype html><title>Hermes System 1 Fixture</title><button>Relatórios</button><button>Configurações</button><div role="tab" tabindex="0">Painel</div>')
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  try {
    const address = server.address()
    if (!address || typeof address === 'string') throw Error('test_server_not_ready')
    await runtime.startControlServer()
    window.showInactive()
    if (window.isFocused()) throw Error('test_window_stole_focus')
    const taskId = 'task-system1-isolated'
    const sessionId = 'session-system1-isolated'
    const runId = 'run-system1-isolated'
    runtime.createTask({taskId, sessionHost: sessionId, runId})
    runtime.showTask(taskId, window, {x: 0, y: 0, width: 1200, height: 700}, 'hub')
    const control = JSON.parse(fs.readFileSync(workstationBrowserControlPath(), 'utf8')) as {
      url: string, token: string
    }
    async function post(action: string, operation: string, args: Record<string, unknown>) {
      const response = await fetch(control.url + '/v1/action', {
        method: 'POST',
        headers: {
          authorization: 'Bearer ' + control.token,
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          action, task_id: taskId, session_id: sessionId, run_id: runId,
          operation_id: operation, arguments: args,
        }),
      })
      const data = await response.json() as Record<string, any>
      if (!response.ok || data.success !== true) {
        throw Error('native_' + action + '_' + response.status + '_' + String(data.error_code))
      }
      return data.result as Record<string, any>
    }
    const url = 'http://127.0.0.1:' + address.port + '/fixture'
    await post('browser_navigate', 'system1_native_navigation', {url})
    const snapshots: Record<string, unknown>[] = []
    const durations: number[] = []
    for (let i = 0; i < 9; i++) {
      const started = performance.now()
      const snapshot = await post('browser_snapshot', 'system1_native_snapshot_' + i, {full: false})
      durations.push(Number((performance.now() - started).toFixed(3)))
      if (!snapshot || snapshot.task_id !== taskId || snapshot.url !== url ||
          snapshot.readiness !== 'stable' || snapshot.truncated ||
          !Array.isArray(snapshot.elements) || snapshot.elements.length < 3) {
        throw Error('native_snapshot_invalid_' + JSON.stringify(snapshot).slice(0, 500))
      }
      snapshots.push(snapshot)
    }
    const result = {
      snapshots: snapshots.slice(0, 2),
      snapshot_durations_ms: durations,
      native: true, renderer_has_focus: window.isFocused(),
      browser_task_count: runtime.listTasks().length,
    }
    console.log('SYSTEM1_NATIVE_SNAPSHOT_E2E=' + JSON.stringify(result))
  } finally {
    await runtime.destroy()
    window.destroy()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
}
main().then(() => app.quit()).catch(e => {
  console.error('SYSTEM1_NATIVE_ERROR=' + String(e?.stack || e))
  app.exit(2)
})
