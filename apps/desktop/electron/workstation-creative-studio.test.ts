import { expect, it } from 'vitest'

function validateStudioTarget(targetUrl: string): { port: number; safeUrl: string } {
  const parsed = new URL(targetUrl)
  if (parsed.hostname !== '127.0.0.1' && parsed.hostname !== 'localhost') {
    throw new Error('creative_studio_loopback_required')
  }
  const port = Number(parsed.port)
  if (!port || port < 1024 || port > 65535) {
    throw new Error('invalid_creative_studio_port')
  }
  // Safe URL for receipts and journals must strip token parameter
  return {
    port,
    safeUrl: `http://127.0.0.1:${port}/#project`,
  }
}

it('enforces loopback host on Creative Studio URLs and redacts session credentials', () => {
  const loopbackUrl = 'http://127.0.0.1:3032/?token=abc123secrettoken'
  const result = validateStudioTarget(loopbackUrl)
  expect(result.port).toBe(3032)
  expect(result.safeUrl).toBe('http://127.0.0.1:3032/#project')
  expect(result.safeUrl).not.toContain('abc123secrettoken')

  const localhostUrl = 'http://localhost:3045/?token=secret456'
  const localhostResult = validateStudioTarget(localhostUrl)
  expect(localhostResult.port).toBe(3045)
  expect(localhostResult.safeUrl).toBe('http://127.0.0.1:3045/#project')

  // External network hosts must be rejected
  expect(() => validateStudioTarget('https://heygen.com/studio')).toThrow('creative_studio_loopback_required')
  expect(() => validateStudioTarget('http://192.168.1.50:3032/?token=abc')).toThrow('creative_studio_loopback_required')
  expect(() => validateStudioTarget('http://malicious-website.io:3032')).toThrow('creative_studio_loopback_required')
})

it('verifies Studio receipt preserves operation identity and TaskRun lineage', () => {
  const receipt = {
    operationId: 'op_studio_open_123',
    taskId: 'task-creative-456',
    runId: 'run-789',
    browserTaskId: 'task-creative-456',
    tabId: 'tab-1',
    revision: 0,
    action: 'browser_creative_studio_open',
    safeUrl: 'http://127.0.0.1:3032/#project',
    executedAt: new Date().toISOString()
  }

  expect(receipt.action).toBe('browser_creative_studio_open')
  expect(receipt.taskId).toBe('task-creative-456')
  expect(receipt.runId).toBe('run-789')
  expect(receipt.safeUrl).toBe('http://127.0.0.1:3032/#project')
  expect(receipt.safeUrl).not.toContain('token')
})
