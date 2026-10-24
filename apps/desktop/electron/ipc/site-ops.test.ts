import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'

import { beforeEach, test, vi } from 'vitest'

const mock = vi.hoisted(() => ({
  handlers: {} as Record<string, (...args: unknown[]) => Promise<unknown>>,
  spawns: [] as Array<{ command: string; args: string[] }>,
  result: { code: 0, stdout: '{"initialized":true,"slug":"web-whatsapp-com"}', stderr: '' }
}))

vi.mock('electron', () => ({
  ipcMain: {
    handle: (name: string, fn: (...args: unknown[]) => Promise<unknown>) => { mock.handlers[name] = fn },
    removeHandler: (name: string) => { delete mock.handlers[name] }
  }
}))

vi.mock('node:child_process', async (loadActual) => {
  const actual = await loadActual() as Record<string, (...args: unknown[]) => unknown>

  return {
    ...actual,
    spawn: (command: string, args: string[]) => {
      mock.spawns.push({ command, args })

      const proc = Object.assign(new EventEmitter(), {
        stdout: new EventEmitter(),
        stderr: new EventEmitter(),
        kill: vi.fn()
      })

      queueMicrotask(() => {
        if (mock.result.stdout) {proc.stdout.emit('data', Buffer.from(mock.result.stdout))}

        if (mock.result.stderr) {proc.stderr.emit('data', Buffer.from(mock.result.stderr))}
        proc.emit('close', mock.result.code)
      })

      return proc
    }
  }
})

import { disposeSiteOpsIpc, registerSiteOpsIpc } from './site-ops'

beforeEach(() => {
  mock.spawns.length = 0
  mock.result = { code: 0, stdout: '{"initialized":true,"slug":"web-whatsapp-com"}', stderr: '' }
  disposeSiteOpsIpc()
  registerSiteOpsIpc()
})

test('deep-map launches the actual script exactly once and returns parsed data', async () => {
  const result = await mock.handlers['hermes:site-ops:deep-map']({}, 'init', 'web.whatsapp.com')
  assert.deepEqual(result, { success: true, data: { initialized: true, slug: 'web-whatsapp-com' } })
  assert.equal(mock.spawns.length, 1)
  assert.equal(mock.spawns[0].command, 'node')
  assert.equal(mock.spawns[0].args[0].replaceAll('\\', '/').endsWith('/site-ops/scripts/site-deep-map.mjs'), true)
  assert.deepEqual(mock.spawns[0].args.slice(1), ['init', 'web.whatsapp.com'])
})

test('failed child process is reported, without claiming success', async () => {
  mock.result = { code: 1, stdout: '', stderr: 'simulated remapping failure' }
  const result = await mock.handlers['hermes:site-ops:deep-map']({}, 'scan', 'web.whatsapp.com')
  assert.deepEqual(result, { success: false, error: 'simulated remapping failure' })
})

test('malformed JSON from a zero-exit child is not silently successful', async () => {
  mock.result = { code: 0, stdout: 'not JSON', stderr: '' }
  const result = await mock.handlers['hermes:site-ops:deep-map']({}, 'status', 'web.whatsapp.com') as { success: boolean }
  assert.equal(result.success, false)
})

test('empty successful child output is rejected, not accepted as an empty map', async () => {
  mock.result = { code: 0, stdout: '', stderr: '' }
  const result = await mock.handlers['hermes:site-ops:deep-map']({}, 'init', 'web.whatsapp.com') as { success: boolean }
  assert.equal(result.success, false)
})

test('semantic failure on a zero-exit child does not claim completion', async () => {
  mock.result = { code: 0, stdout: '{"scanned":false,"elements":0}', stderr: '' }
  const result = await mock.handlers['hermes:site-ops:deep-map']({}, 'scan', 'web.whatsapp.com') as { success: boolean }
  assert.equal(result.success, false)
})
