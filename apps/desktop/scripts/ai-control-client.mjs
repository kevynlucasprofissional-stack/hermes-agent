/**
 * Hermes AI Control client. Discovers the native, short-lived authenticated
 * loopback bridge. Explicit HERMES_DESKTOP_CDP_PORT continues to support the
 * old manual dev-debugger workflow; the default never opens Chromium CDP.
 */
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

export function aiControlDiscoveryPath(env = process.env) {
  const appData = env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming')
  return env.HERMES_AI_CONTROL_FILE || path.join(appData, 'Hermes', 'ai-control-bridge.json')
}

export async function connectAiControl({ env = process.env, discoveryPath = aiControlDiscoveryPath(env) } = {}) {
  const override = env.HERMES_DESKTOP_CDP_PORT?.trim()
  if (override && !['off', '0', 'false', 'no'].includes(override.toLowerCase())) {
    const port = Number(override)
    if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('invalid explicit CDP port')
    const response = await fetch('http://127.0.0.1:' + port + '/json', { signal: AbortSignal.timeout(3000) })
    if (!response.ok) throw new Error('CDP unavailable on ' + port)
    const targets = await response.json()
    const target = targets.find(t => t.url?.includes('5174')) ?? targets.find(t => t.type === 'page')
    if (!target?.webSocketDebuggerUrl) throw new Error('no desktop page target on CDP port ' + port)
    const ws = new WebSocket(target.webSocketDebuggerUrl)
    await Promise.race([
      new Promise((resolve, reject) => {
        ws.addEventListener('open', resolve, { once: true })
        ws.addEventListener('error', () => reject(new Error('CDP websocket failed')), { once: true })
      }),
      new Promise((_resolve, reject) => setTimeout(() => reject(new Error('CDP websocket timeout')), 3500))
    ])
    let id = 0
    const pending = new Map()
    ws.addEventListener('message', ev => {
      const reply = JSON.parse(ev.data)
      if (pending.has(reply.id)) {
        pending.get(reply.id)(reply)
        pending.delete(reply.id)
      }
    })
    return {
      mode: 'explicit-cdp',
      async evaluate(expression) {
        const reqId = ++id
        const reply = new Promise(resolve => pending.set(reqId, resolve))
        ws.send(JSON.stringify({ id: reqId, method: 'Runtime.evaluate',
          params: { expression, returnByValue: true, awaitPromise: true } }))
        const result = await reply
        if (result.error || result.result?.exceptionDetails) {
          throw new Error(result.error?.message || result.result.exceptionDetails.exception?.description || 'CDP evaluation failed')
        }
        return result.result?.result?.value
      },
      close() { ws.close() }
    }
  }

  let info
  try {
    info = JSON.parse(fs.readFileSync(discoveryPath, 'utf8'))
  } catch {
    throw new Error('AI Control disabled or Hermes not restarted with native bridge. Press Ctrl+Shift+A in the new Hermes window.')
  }
  if (info?.version !== 1 || info?.host !== '127.0.0.1' ||
      !Number.isInteger(info.port) || info.port < 1024 || info.port > 65535 ||
      typeof info.token !== 'string' || info.token.length < 32) {
    throw new Error('invalid AI Control discovery file')
  }
  const base = 'http://127.0.0.1:' + info.port
  async function request(url, payload) {
    let response
    try {
      response = await fetch(base + url, {
        method: payload === undefined ? 'GET' : 'POST',
        headers: { Authorization: 'Bearer ' + info.token, ...(payload === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
        signal: AbortSignal.timeout(15000)
      })
    } catch {
      throw new Error('AI Control endpoint unavailable; toggle AI Control in the current Hermes window.')
    }
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.error || 'AI Control rejected request (' + response.status + ')')
    return data
  }
  await request('/status')
  return {
    mode: 'native-bridge',
    async evaluate(expression) { return (await request('/evaluate', { expression })).result },
    close() {}
  }
}
