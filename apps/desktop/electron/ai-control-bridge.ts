/**
 * User-activated loopback bridge for the primary Hermes renderer.
 * No Chromium remote debugging port or renderer-controlled authorization.
 */
import { randomBytes, timingSafeEqual } from 'node:crypto'
import fs from 'node:fs'
import http, { type IncomingMessage, type ServerResponse } from 'node:http'
import path from 'node:path'

export interface AiControlWebContents {
  isDestroyed(): boolean
  executeJavaScript(code: string, userGesture?: boolean): Promise<unknown>
}
export interface AiControlBridgeOptions {
  controlFile: string
  getWebContents(): AiControlWebContents | null
  onStateChange(active: boolean): void
}

const MAX_BODY_BYTES = 128 * 1024
const MAX_EXPRESSION_BYTES = 64 * 1024
const EVAL_TIMEOUT_MS = 12000

function json(res: ServerResponse, status: number, value: object) {
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff'
  })
  res.end(JSON.stringify(value))
}

function authorized(header: string | undefined, expected: string): boolean {
  if (typeof header !== 'string' || !header.startsWith('Bearer ')) return false
  const candidate = Buffer.from(header.slice(7))
  const secret = Buffer.from(expected)
  return candidate.length === secret.length && timingSafeEqual(candidate, secret)
}

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks: Buffer[] = []
    req.on('data', (chunk: Buffer) => {
      size += chunk.length
      if (size > MAX_BODY_BYTES) {
        reject(new Error('request_too_large'))
        req.destroy()
      } else {
        chunks.push(chunk)
      }
    })
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
    req.on('error', reject)
  })
}

export function createAiControlBridge(options: AiControlBridgeOptions) {
  let server: http.Server | null = null
  let token: string | null = null
  let port = 0
  let transition: Promise<void> = Promise.resolve()
  const active = () => server !== null && token !== null

  function removeOwnedDiscovery(secret: string) {
    try {
      const current = JSON.parse(fs.readFileSync(options.controlFile, 'utf8'))
      if (current.pid === process.pid && current.token === secret) fs.unlinkSync(options.controlFile)
    } catch { /* A different or already removed file must never be deleted. */ }
  }

  async function enable(): Promise<void> {
    if (active()) return
    const wc = options.getWebContents()
    if (!wc || wc.isDestroyed()) throw new Error('primary_renderer_unavailable')
    const newToken = randomBytes(32).toString('base64url')
    const listener = http.createServer(async (req, res) => {
      if (req.headers.host !== '127.0.0.1:' + port ||
          typeof req.headers.origin === 'string' ||
          !authorized(req.headers.authorization, newToken)) {
        json(res, 401, { error: 'unauthorized' })
        return
      }
      if (!active() || token !== newToken) {
        json(res, 403, { error: 'ai_control_disabled' })
        return
      }
      if (req.method === 'GET' && req.url === '/status') {
        json(res, 200, { active: true, pid: process.pid })
        return
      }
      if (req.method !== 'POST' || req.url !== '/evaluate') {
        json(res, 404, { error: 'not_found' })
        return
      }
      if (!(req.headers['content-type'] ?? '').startsWith('application/json')) {
        json(res, 415, { error: 'json_required' })
        return
      }
      try {
        const body = JSON.parse(await readBody(req))
        const expression = body?.expression
        if (typeof expression !== 'string' || !expression.trim() ||
            Buffer.byteLength(expression, 'utf8') > MAX_EXPRESSION_BYTES) {
          json(res, 400, { error: 'invalid_expression' })
          return
        }
        if (!active() || token !== newToken) {
          json(res, 403, { error: 'ai_control_disabled' })
          return
        }
        const current = options.getWebContents()
        if (!current || current.isDestroyed()) {
          json(res, 503, { error: 'primary_renderer_unavailable' })
          return
        }
        let timer: ReturnType<typeof setTimeout> | undefined
        try {
          const result = await Promise.race([
            current.executeJavaScript(expression, false),
            new Promise<never>((_resolve, reject) => {
              timer = setTimeout(() => reject(new Error('evaluation_timeout')), EVAL_TIMEOUT_MS)
            })
          ])
          if (token !== newToken || !active()) {
            json(res, 403, { error: 'ai_control_disabled' })
          } else {
            json(res, 200, { result: result === undefined ? null : result })
          }
        } finally {
          if (timer) clearTimeout(timer)
        }
      } catch (err) {
        if (!res.writableEnded && !res.destroyed) {
          json(res, 400, { error: err instanceof Error ? err.message : 'evaluation_failed' })
        }
      }
    })
    try {
      await new Promise<void>((resolve, reject) => {
        listener.once('error', reject)
        listener.listen(0, '127.0.0.1', () => {
          listener.off('error', reject)
          resolve()
        })
      })
      const address = listener.address()
      if (!address || typeof address === 'string') throw new Error('bridge_bind_failed')
      port = address.port
      fs.mkdirSync(path.dirname(options.controlFile), { recursive: true })
      const tmp = options.controlFile + '.' + process.pid + '.' + randomBytes(6).toString('hex') + '.tmp'
      try {
        fs.writeFileSync(tmp, JSON.stringify({
          version: 1, pid: process.pid, port, host: '127.0.0.1', token: newToken
        }), { mode: 0o600, flag: 'wx' })
        fs.renameSync(tmp, options.controlFile)
      } finally {
        try { fs.unlinkSync(tmp) } catch { /* renamed */ }
      }
      server = listener
      token = newToken
      options.onStateChange(true)
    } catch (err) {
      listener.close()
      port = 0
      throw err
    }
  }

  async function disable(): Promise<void> {
    const oldServer = server
    const oldToken = token
    server = null
    token = null
    port = 0
    if (oldToken) removeOwnedDiscovery(oldToken)
    if (oldServer) oldServer.close()
    options.onStateChange(false)
  }

  function toggle(): Promise<boolean> {
    const next = transition.catch(() => undefined).then(() => active() ? disable() : enable())
    transition = next
    return next.then(() => active())
  }
  return { active, toggle, disable }
}
