// site-ops/framework/cdp-client.mjs
// CDP Client — Reusable CDP connection + eval wrapper.
// Supports both class-based (CdpClient) and functional (connectCDP, evalCDP, etc.) usage.

let activeWs = null
let msgId = 0
const activePending = new Map()

export class CdpClient {
  constructor(options = {}) {
    this.port = Number(options.port || process.env.HERMES_DESKTOP_CDP_PORT || 9222)
    this.ws = null
    this.id = 0
    this.pending = new Map()
    this.target = null
  }

  async listTargets() {
    const res = await fetch(`http://127.0.0.1:${this.port}/json`)
    if (!res.ok) {
      throw new Error(`Failed to list CDP targets (HTTP ${res.status}): ensure Chrome/Electron is running with --remote-debugging-port=${this.port}`)
    }
    return await res.json()
  }

  async findTarget(urlPattern) {
    const targets = await this.listTargets()
    const pages = targets.filter(t => t.type === 'page' && t.url !== 'about:blank' && t.url !== '')

    if (urlPattern) {
      const match = pages.find(t => t.url.includes(urlPattern) || (t.title || '').includes(urlPattern))
      if (match) return match
      throw new Error(`No CDP target matching "${urlPattern}". Available targets: ${pages.map(p => p.url).join(', ')}`)
    }

    // Auto-detect: prefer non-Hermes renderer pages (port 5174 is Vite dev server)
    const external = pages.filter(t => !t.url.includes('127.0.0.1:5174'))
    if (external.length === 1) return external[0]
    if (external.length > 1) {
      const targetList = external.map(p => `  - ${p.title || '(no title)'} → ${p.url}`).join('\n')
      throw new Error(`Multiple external targets found. Specify one with pattern:\n${targetList}`)
    }
    throw new Error('No external CDP targets found. Open a site in Hermes browser first.')
  }

  async connect(targetOrPattern) {
    let target = targetOrPattern
    if (!target || typeof target === 'string') {
      target = await this.findTarget(targetOrPattern)
    }
    this.target = target

    if (!target.webSocketDebuggerUrl) {
      throw new Error(`Target ${target.title || target.url} does not have a webSocketDebuggerUrl`)
    }

    this.ws = new WebSocket(target.webSocketDebuggerUrl)
    this.ws.addEventListener('message', (ev) => {
      try {
        const m = JSON.parse(ev.data)
        if (this.pending.has(m.id)) {
          this.pending.get(m.id)(m)
          this.pending.delete(m.id)
        }
      } catch (err) {
        console.error('[CDP-CLIENT] Error parsing message:', err)
      }
    })

    await new Promise((resolve, reject) => {
      const onOpen = () => {
        cleanup()
        resolve()
      }
      const onError = (err) => {
        cleanup()
        reject(new Error(`WebSocket connection failed: ${err?.message || 'unknown error'}`))
      }
      const cleanup = () => {
        this.ws.removeEventListener('open', onOpen)
        this.ws.removeEventListener('error', onError)
      }
      this.ws.addEventListener('open', onOpen)
      this.ws.addEventListener('error', onError)
    })

    return this
  }

  async eval(expr) {
    if (!this.ws) {
      throw new Error('CDP client is not connected. Call connect() first.')
    }
    const i = ++this.id
    const p = new Promise((resolve) => this.pending.set(i, resolve))
    this.ws.send(JSON.stringify({
      id: i,
      method: 'Runtime.evaluate',
      params: { expression: expr, returnByValue: true, awaitPromise: true }
    }))
    const r = await p
    if (r.result?.exceptionDetails) {
      throw new Error(r.result.exceptionDetails.exception?.description || 'eval error')
    }
    return r.result?.result?.value
  }

  close() {
    if (this.ws) {
      try {
        this.ws.close()
      } catch {}
      this.ws = null
    }
  }
}

// Functional API
export async function findCdpTarget(port = 9222, urlPattern = '') {
  const client = new CdpClient({ port })
  return client.findTarget(urlPattern)
}

export async function connectCDP(targetOrPattern, options = {}) {
  const client = new CdpClient(options)
  await client.connect(targetOrPattern)
  activeWs = client.ws
  return client
}

export async function evalCDP(expr) {
  if (!activeWs) throw new Error('No active CDP connection. Call connectCDP first.')
  const id = ++msgId
  const p = new Promise((resolve) => activePending.set(id, resolve))
  activeWs.send(JSON.stringify({
    id,
    method: 'Runtime.evaluate',
    params: { expression: expr, returnByValue: true, awaitPromise: true }
  }))
  const r = await p
  if (r.result?.exceptionDetails) {
    throw new Error(r.result.exceptionDetails.exception?.description || 'eval error')
  }
  return r.result?.result?.value
}

export function closeCDP() {
  if (activeWs) {
    try { activeWs.close() } catch {}
    activeWs = null
  }
}
