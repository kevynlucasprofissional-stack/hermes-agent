import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const FIXTURE_ROOT = join(dirname(fileURLToPath(import.meta.url)), 'fixtures')
const MAX_BODY_BYTES = 64 * 1024
const SCENARIOS = new Set([
  'forms',
  'delayed-hydration',
  'lists-tables',
  'rich-editor',
  'navigation',
  'navigation-target',
  'tab-recovery',
  'human-takeover'
])

function parseArgs(argv) {
  const args = { port: 0 }

  for (let index = 0; index < argv.length; index++) {
    const token = argv[index]
    if (token === '--port') {
      args.port = Number(argv[++index])
    } else {
      throw new Error(`unknown argument: ${token}`)
    }
  }

  if (!Number.isInteger(args.port) || args.port < 0 || args.port > 65_535) {
    throw new Error('--port must be an integer from 0 to 65535')
  }

  return args
}

function sendJson(response, status, value) {
  const body = JSON.stringify(value)
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    'cache-control': 'no-store'
  })
  response.end(body)
}

async function readJsonBody(request) {
  const chunks = []
  let size = 0

  for await (const chunk of request) {
    size += chunk.length
    if (size > MAX_BODY_BYTES) {
      throw new Error('request body exceeds 64 KiB')
    }
    chunks.push(chunk)
  }

  const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw new Error('request body must be a JSON object')
  }

  return body
}

export async function startFixtureServer({ port = 0 } = {}) {
  const state = new Map()
  const assets = new Map([
    ['/assets/fixture.css', ['fixture.css', 'text/css; charset=utf-8']],
    ['/assets/fixture.mjs', ['fixture.mjs', 'text/javascript; charset=utf-8']]
  ])
  const indexHtml = await readFile(join(FIXTURE_ROOT, 'index.html'))

  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url || '/', 'http://brow01.local')

      if (url.pathname === '/health') {
        sendJson(response, 200, {
          ready: true,
          classification: 'FIXTURE_SMOKE',
          native_browser_qualification: 'NV'
        })
        return
      }

      const asset = assets.get(url.pathname)
      if (asset) {
        const [fileName, contentType] = asset
        const body = await readFile(join(FIXTURE_ROOT, fileName))
        response.writeHead(200, {
          'content-type': contentType,
          'content-length': body.length,
          'cache-control': 'no-store'
        })
        response.end(body)
        return
      }

      if (url.pathname.startsWith('/api/state/')) {
        const scenario = decodeURIComponent(url.pathname.slice('/api/state/'.length))
        const runId = url.searchParams.get('run_id') || ''

        if (!SCENARIOS.has(scenario) || !runId || runId.length > 256) {
          sendJson(response, 400, { error: 'invalid_state_scope' })
          return
        }

        const key = `${scenario}\u0000${runId}`
        if (request.method === 'GET') {
          sendJson(response, 200, state.get(key) ?? { scenario, run_id: runId, write_count: 0, value: null })
          return
        }
        if (request.method === 'POST') {
          const value = await readJsonBody(request)
          const prior = state.get(key)
          const stored = {
            scenario,
            run_id: runId,
            write_count: (prior?.write_count ?? 0) + 1,
            value
          }
          state.set(key, stored)
          sendJson(response, 200, stored)
          return
        }
      }

      if (url.pathname === '/' || url.pathname.startsWith('/scenario/')) {
        const scenario = url.pathname.startsWith('/scenario/') ? url.pathname.slice('/scenario/'.length) : ''
        if (scenario && !SCENARIOS.has(scenario)) {
          sendJson(response, 404, { error: 'unknown_fixture' })
          return
        }
        response.writeHead(200, {
          'content-type': 'text/html; charset=utf-8',
          'content-length': indexHtml.length,
          'cache-control': 'no-store',
          'x-brow01-classification': 'FIXTURE_SMOKE'
        })
        response.end(indexHtml)
        return
      }

      sendJson(response, 404, { error: 'not_found' })
    } catch (error) {
      sendJson(response, 400, { error: error instanceof Error ? error.message : String(error) })
    }
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(port, '127.0.0.1', resolve)
  })

  const address = server.address()
  if (!address || typeof address === 'string') {
    throw new Error('BROW-01 fixture server did not bind a TCP port')
  }

  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  }
}

async function main() {
  const server = await startFixtureServer(parseArgs(process.argv.slice(2)))
  console.log(`BROW01_FIXTURE_READY ${JSON.stringify({
    base_url: server.baseUrl,
    classification: 'FIXTURE_SMOKE',
    native_browser_qualification: 'NV'
  })}`)

  let closing = false
  const close = async () => {
    if (closing) return
    closing = true
    await server.close()
    process.exit(0)
  }
  process.once('SIGINT', () => void close())
  process.once('SIGTERM', () => void close())
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  await main()
}
