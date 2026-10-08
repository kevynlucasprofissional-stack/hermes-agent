import assert from 'node:assert/strict'
import crypto from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { app, BrowserWindow, nativeImage } from 'electron'

const output = path.resolve(process.argv[2])
const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-creative-native-'))
app.setPath('userData', path.join(sandbox, 'electron'))
process.env.HERMES_WORKSTATION_HOME = path.join(sandbox, 'workstation')
process.env.HERMES_WORKSTATION_BROWSER_PROFILE = path.join(sandbox, 'browser')
process.env.HERMES_WORKSTATION_BROWSER_CONTROL_FILE = path.join(sandbox, 'controller.json')
process.env.HERMES_WORKSTATION_BROWSER_TASK_FILE = path.join(sandbox, 'browser-tasks.json')

async function run() {
  const { getWorkstationBrowserRuntime, workstationBrowserControlPath } = await import('./workstation-browser-runtime')
  const runtime = getWorkstationBrowserRuntime()
  const deadline = Date.now() + 10_000
  while (!fs.existsSync(workstationBrowserControlPath())) {
    if (Date.now() > deadline) throw new Error('native_controller_start_timeout')
    await new Promise(resolve => setTimeout(resolve, 25))
  }
  const control = JSON.parse(fs.readFileSync(workstationBrowserControlPath(), 'utf8'))
  const window = new BrowserWindow({ show: true, opacity: 0, skipTaskbar: true, width: 480, height: 720 })
  const sessionId = 'cw03a-native-session'
  const runId = 'cw03a-native-run'
  const taskId = 'cw03a-native-render'
  const humanTaskId = 'cw03a-native-human'
  runtime.createTask({ taskId: humanTaskId, sessionHost: sessionId, runId })
  runtime.showTask(humanTaskId, window, { x: 0, y: 0, width: 400, height: 650 })
  runtime.createTask({ taskId, sessionHost: sessionId, runId })
  const activeTab = runtime.state().activeTabId
  fs.mkdirSync(output, { recursive: true })
  let operation = 0
  const document = {
    schemaVersion: 1, width: 360, height: 640, background: '#14263d',
    elements: [
      { kind: 'circle', x: 180, y: 130, radius: 62, fill: '#f6c85f' },
      { kind: 'rect', x: 28, y: 240, width: 304, height: 230, radius: 16, fill: '#234366' },
      { kind: 'text', x: 180, y: 300, size: 30, fill: '#ffffff', anchor: 'middle', text: 'HERMES' },
      { kind: 'text', x: 180, y: 355, size: 22, fill: '#f6c85f', anchor: 'middle', text: 'Creative invitation' },
      { kind: 'text', x: 180, y: 410, size: 18, fill: '#ffffff', anchor: 'middle', text: '08 October · 19:00' }
    ]
  }
  const sourcePath = path.join(output, 'invitation.creative.json')
  fs.writeFileSync(sourcePath, JSON.stringify(document, null, 2))
  async function request(source: string, overrides: Record<string, unknown> = {}) {
    return fetch(`${control.url}/v1/action`, {
      method: 'POST', headers: { Authorization: `Bearer ${control.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'browser_creative_render', task_id: taskId, session_id: sessionId,
        run_id: runId, operation_id: `cw03a-native-op-${++operation}`,
        arguments: { source_json: source, source_sha256: crypto.createHash('sha256').update(source).digest('hex') },
        ...overrides
      })
    })
  }
  try {
    const source = fs.readFileSync(sourcePath, 'utf8')
    const firstResponse = await request(source)
    const firstBody = await firstResponse.json()
    assert.equal(firstResponse.status, 200, JSON.stringify(firstBody))
    const first = firstBody.result
    const firstPng = fs.readFileSync(first.screenshot_path)
    const decoded = nativeImage.createFromBuffer(firstPng)
    assert.deepEqual(decoded.getSize(), { width: 360, height: 640 })
    assert.equal(crypto.createHash('sha256').update(firstPng).digest('hex'), first.sha256)
    assert.equal(first.receipt.taskId, taskId)
    assert.equal(first.receipt.runId, runId)
    assert.equal(runtime.state().activeTabId, activeTab, 'background render must preserve foreground tab')
    fs.writeFileSync(path.join(output, 'invitation.png'), firstPng)
    fs.writeFileSync(path.join(output, 'invitation.svg'), first.svg_source)
    // Reopen the persisted editable source through the real controller.
    const reopenedResponse = await request(fs.readFileSync(sourcePath, 'utf8'))
    const reopened = (await reopenedResponse.json()).result
    assert.equal(reopenedResponse.status, 200)
    assert.equal(reopened.sha256, first.sha256)
    const variant = JSON.parse(source)
    variant.background = '#382544'
    variant.elements[3].text = 'Second edition'
    const variantResponse = await request(JSON.stringify(variant))
    const variantResult = (await variantResponse.json()).result
    assert.equal(variantResponse.status, 200)
    assert.notEqual(variantResult.sha256, first.sha256)
    fs.copyFileSync(variantResult.screenshot_path, path.join(output, 'invitation-variant.png'))
    const before = fs.readdirSync(path.dirname(first.screenshot_path)).length
    const malformed = await request(JSON.stringify({ ...document, elements: [{ kind: 'script', code: 'process.exit()' }] }))
    assert.equal(malformed.status, 400)
    const stale = await request(source, { arguments: { source_json: source, source_sha256: '0'.repeat(64) } })
    assert.equal(stale.status, 400)
    const wrongOwner = await request(source, { session_id: 'other-session' })
    assert.ok(wrongOwner.status >= 400)
    const staleRun = await request(source, { run_id: 'stale-run' })
    assert.ok(staleRun.status >= 400)
    runtime.takeControl(taskId)
    const fenced = await request(source)
    assert.equal(fenced.status, 409)
    runtime.releaseControl(taskId)
    assert.equal(fs.readdirSync(path.dirname(first.screenshot_path)).length, before, 'negative controls must not export')
    fs.writeFileSync(path.join(output, 'native-receipt.json'), JSON.stringify({
      schema_version: 1, runtime: 'electron-chromium', electron: process.versions.electron,
      chromium: process.versions.chrome, first: { ...first, screenshot_path: 'invitation.png', svg_source: undefined },
      reopen_sha256: reopened.sha256, variant_sha256: variantResult.sha256,
      negative_controls: ['malformed-shape', 'stale-source', 'wrong-session', 'stale-run', 'human-control'],
      foreground_preserved: runtime.state().activeTabId === activeTab
    }, null, 2))
  } finally {
    await runtime.destroy()
    window.destroy()
  }
}

app.whenReady().then(run).then(() => app.exit(0)).catch(error => {
  console.error(error)
  app.exit(1)
})
