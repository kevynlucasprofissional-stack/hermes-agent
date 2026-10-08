import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { promisify } from 'node:util'

import { app, BrowserWindow, nativeImage } from 'electron'

const [sandbox, python, repository, phase] = process.argv.slice(2)
const execute = promisify(execFile)
const home = path.join(sandbox, 'hermes')

interface FixtureArtifact { local_path: string; sha256: string }
interface FixtureProject {
  project_id: string
  revision_id: string
  source_sha256: string
  source_artifact: FixtureArtifact
  manifest_artifact: FixtureArtifact
}
interface FixtureRender {
  task_id: string
  browser_task_id: string
  session_id: string
  png_artifact: FixtureArtifact
  svg_artifact: FixtureArtifact
  media_readback: { decoded: boolean; width: number; height: number }
}
interface FixtureState {
  task_id: string
  run_id: number
  source: string
  project: FixtureProject
  browser_task_id: string
  render?: FixtureRender
  variant?: { project: FixtureProject; render: FixtureRender }
  create_pid?: number
  reopen_pid?: number
}
app.setPath('userData', path.join(sandbox, 'electron'))
Object.assign(process.env, {
  HERMES_TEST_ISOLATION: sandbox, HERMES_HOME: home,
  HERMES_KANBAN_DB: path.join(home, 'kanban.db'),
  HERMES_WORKSTATION_HOME: path.join(sandbox, 'workstation'),
  HERMES_WORKSTATION_BROWSER_PROFILE: path.join(sandbox, 'browser'),
  HERMES_WORKSTATION_BROWSER_CONTROL_FILE: path.join(sandbox, 'controller.json'),
  HERMES_WORKSTATION_BROWSER_TASK_FILE: path.join(sandbox, 'browser-tasks.json'),
  HERMES_SESSION_KEY: 'creative-project-approval-key', HERMES_SESSION_ID: 'creative-project-session'
})

async function pythonJson(args: string[]) {
  const result = await execute(python, args, { cwd: repository, env: process.env, windowsHide: true, timeout: 30_000 })
  const lines = result.stdout.trim().split(/\r?\n/)
  return JSON.parse(lines[lines.length - 1])
}

async function run() {
  const statePath = path.join(sandbox, 'project-state.json')
  let state: FixtureState
  if (phase === 'create') {
    const prepared = await pythonJson(['-m', 'workstation.scripts.creative_project_native_fixture'])
    const saved = await pythonJson(['-m', 'workstation.creative', '--task-id', prepared.task_id,
      '--run-id', String(prepared.run_id), 'save', '--source', prepared.source])
    assert.equal(saved.success, true)
    state = { ...prepared, project: saved.result, browser_task_id: 'creative-project-browser', create_pid: process.pid }
  } else {
    state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
  }
  const { getWorkstationBrowserRuntime, workstationBrowserControlPath } = await import('./workstation-browser-runtime')
  const runtime = getWorkstationBrowserRuntime()
  const window = new BrowserWindow({ show: false, skipTaskbar: true, width: 480, height: 720 })
  await window.webContents.loadURL('data:text/html,<title>Hermes Creative native test</title>')
  window.showInactive()
  const deadline = Date.now() + 10_000
  while (!fs.existsSync(workstationBrowserControlPath())) {
    if (Date.now() > deadline) throw new Error('project_native_controller_start_timeout')
    await new Promise(resolve => setTimeout(resolve, 25))
  }
  // Reattach through the existing lifecycle after a real process restart.
  runtime.createTask({ taskId: state.browser_task_id, sessionHost: 'creative-project-session',
    runId: String(state.run_id), kanbanCardId: state.task_id })
  const humanTask = 'creative-project-human'
  runtime.createTask({ taskId: humanTask, sessionHost: 'creative-project-session', runId: String(state.run_id) })
  runtime.showTask(humanTask, window, { x: 0, y: 0, width: 400, height: 650 })
  const foreground = runtime.state().activeTabId
  const args = ['-m', 'workstation.creative', '--task-id', state.task_id, '--run-id', String(state.run_id),
    'render', '--project-id', state.project.project_id, '--revision-id', state.project.revision_id,
    '--browser-task-id', state.browser_task_id]
  try {
    const rendered = await pythonJson(args)
    assert.equal(rendered.success, true)
    assert.equal(rendered.result.task_id, state.task_id)
    assert.equal(rendered.result.browser_task_id, state.browser_task_id)
    assert.notEqual(state.task_id, state.browser_task_id)
    assert.equal(rendered.result.session_id, 'creative-project-session')
    assert.equal(rendered.result.media_readback.decoded, true)
    assert.equal(rendered.result.media_readback.width, 360)
    assert.equal(rendered.result.media_readback.height, 640)
    const image = nativeImage.createFromPath(rendered.result.png_artifact.local_path)
    const bitmap = image.toBitmap()
    const pixel = (x: number, y: number) => [...bitmap.subarray((y * 360 + x) * 4, (y * 360 + x) * 4 + 4)]
    assert.deepEqual(pixel(10, 10), [61, 38, 20, 255], 'source background must be painted')
    assert.deepEqual(pixel(180, 130), [95, 200, 246, 255], 'source logo must be painted')
    assert.equal(runtime.state().activeTabId, foreground)
    if (phase === 'reopen') {
      assert.notEqual(process.pid, state.create_pid)
      assert.equal(rendered.result.png_artifact.sha256, state.render?.png_artifact.sha256)
      state.reopen_pid = process.pid
    }
    state.render = rendered.result
    fs.writeFileSync(statePath, JSON.stringify(state, null, 2))
    runtime.takeControl(state.browser_task_id)
    await assert.rejects(pythonJson(args), 'human takeover must fence the product CLI')
    runtime.releaseControl(state.browser_task_id)
    const wrongSession = process.env.HERMES_SESSION_ID
    process.env.HERMES_SESSION_ID = 'different-session'
    await assert.rejects(pythonJson(args), 'foreign session must fail before dispatch')
    process.env.HERMES_SESSION_ID = wrongSession
    if (phase === 'reopen') {
      const source = JSON.parse(fs.readFileSync(state.source, 'utf8'))
      source.background = '#382544'
      source.elements[1].text = 'SECOND EDITION'
      fs.writeFileSync(state.source, JSON.stringify(source))
      const saved = await pythonJson(['-m', 'workstation.creative', '--task-id', state.task_id,
        '--run-id', String(state.run_id), 'save', '--source', state.source,
        '--project-id', state.project.project_id, '--parent-revision', state.project.revision_id])
      assert.equal(saved.success, true)
      const variant = await pythonJson(['-m', 'workstation.creative', '--task-id', state.task_id,
        '--run-id', String(state.run_id), 'render', '--project-id', saved.result.project_id,
        '--revision-id', saved.result.revision_id, '--browser-task-id', state.browser_task_id])
      assert.equal(variant.success, true)
      assert.notEqual(variant.result.png_artifact.sha256, rendered.result.png_artifact.sha256)
      assert.equal(runtime.state().activeTabId, foreground)
      state.variant = { project: saved.result, render: variant.result }
    }
    fs.writeFileSync(statePath, JSON.stringify(state, null, 2))
    console.log(JSON.stringify({ phase, project_id: state.project.project_id,
      png_sha256: state.render.png_artifact.sha256, real_cli: true, independent_decode: true,
      foreground_preserved: true, negative_controls: ['human-control', 'wrong-session'] }))
  } catch (error) {
    console.error('Native project fixture controller diagnostic:', runtime.state().lastError)
    throw error
  } finally {
    await runtime.destroy()
    window.destroy()
  }
}

app.whenReady().then(run).then(() => app.exit(0)).catch(error => {
  console.error(error)
  app.exit(1)
})
