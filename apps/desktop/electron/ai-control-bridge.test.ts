import { describe, expect, it } from 'vitest'
import { createAiControlBridge } from './ai-control-bridge'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

describe('native AI Control bridge', () => {
  it('is off by default, authenticates, evaluates only when enabled and revokes on disable', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-ai-control-'))
    const file = path.join(dir, 'bridge.json')
    const calls: string[] = []
    const state: boolean[] = []
    const wc = { isDestroyed: () => false, executeJavaScript: async (s: string) => { calls.push(s); return 42 } }
    const bridge = createAiControlBridge({
      controlFile: file, getWebContents: () => wc, onStateChange: value => state.push(value)
    })
    try {
      expect(bridge.active()).toBe(false)
      expect(fs.existsSync(file)).toBe(false)
      expect(await bridge.toggle()).toBe(true)
      const details = JSON.parse(fs.readFileSync(file, 'utf8'))
      expect(details.host).toBe('127.0.0.1')
      const url = 'http://127.0.0.1:' + details.port
      expect((await fetch(url + '/status')).status).toBe(401)
      const hdr = { Authorization: 'Bearer ' + details.token, 'Content-Type': 'application/json' }
      expect((await fetch(url + '/evaluate', { method: 'POST', headers: { ...hdr, Origin: 'https://evil.test' }, body: JSON.stringify({ expression: 'evil' }) })).status).toBe(401)
      const response = await fetch(url + '/evaluate', { method: 'POST', headers: hdr, body: JSON.stringify({ expression: '1+1' }) })
      expect(response.status).toBe(200)
      expect(await response.json()).toEqual({ result: 42 })
      expect(calls).toEqual(['1+1'])
      expect(await bridge.toggle()).toBe(false)
      expect(fs.existsSync(file)).toBe(false)
      expect(bridge.active()).toBe(false)
      expect(state).toEqual([true, false])
    } finally {
      await bridge.disable()
      fs.rmSync(dir, { recursive: true, force: true })
    }
  })
  it('cannot activate without a live primary renderer', async () => {
    const file = path.join(os.tmpdir(), 'hermes-absent-' + process.pid + '.json')
    const bridge = createAiControlBridge({
      controlFile: file, getWebContents: () => null, onStateChange: () => undefined
    })
    await expect(bridge.toggle()).rejects.toThrow('primary_renderer_unavailable')
    expect(fs.existsSync(file)).toBe(false)
  })
})
