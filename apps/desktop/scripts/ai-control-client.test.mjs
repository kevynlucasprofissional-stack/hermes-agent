import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import fs from 'node:fs'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { connectAiControl } from './ai-control-client.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))

test('CLI uses authenticated native bridge instead of a fixed CDP port', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-bridge-cli-'))
  const file = path.join(dir, 'bridge.json')
  const token = randomBytes(32).toString('base64url')
  const evaluations = []
  const server = http.createServer(async (req, res) => {
    if (req.headers.authorization !== 'Bearer ' + token) {
      res.writeHead(401).end()
      return
    }
    if (req.url === '/status') {
      res.setHeader('content-type', 'application/json')
      res.end(JSON.stringify({ active: true }))
      return
    }
    const chunks = []
    for await (const chunk of req) chunks.push(chunk)
    const { expression } = JSON.parse(Buffer.concat(chunks).toString())
    evaluations.push(expression)
    let result = null
    if (expression.includes('__hermesAiControlActive')) result = true
    else if (expression.includes('menu-button')) result = true
    else if (expression.includes('headings') || expression.includes('querySelectorAll')) result = ['Workstation']
    else if (expression.includes('role="tab"')) result = 'Workstation'
    res.setHeader('content-type', 'application/json')
    res.end(JSON.stringify({ result }))
  })
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  fs.writeFileSync(file, JSON.stringify({ version: 1, host: '127.0.0.1', port: address.port, token }))
  try {
    const client = await connectAiControl({ discoveryPath: file, env: {} })
    assert.equal(client.mode, 'native-bridge')
    assert.equal(await client.evaluate('window.__hermesAiControlActive'), true)
    client.close()
    assert.ok(evaluations.length)
    // A stale token never silently falls back to Chrome's port 9222.
    fs.writeFileSync(file, JSON.stringify({ version: 1, host: '127.0.0.1', port: address.port, token: 'X'.repeat(43) }))
    await assert.rejects(connectAiControl({ discoveryPath: file, env: {} }), /unauthorized|rejected request/)
  } finally {
    server.closeAllConnections()
    await new Promise(resolve => server.close(resolve))
    fs.rmSync(dir, { recursive: true, force: true })
  }
})

test('Hermes navigation reports AI Control off instead of connecting to port 9222', () => {
  const missing = path.join(os.tmpdir(), 'hermes-no-ai-control-' + process.pid + '.json')
  const child = spawnSync(process.execPath, [path.join(here, 'hermes-nav.mjs'), 'status'], {
    env: { ...process.env, HERMES_AI_CONTROL_FILE: missing, HERMES_DESKTOP_CDP_PORT: 'off' },
    encoding: 'utf8',
    timeout: 5000
  })
  assert.equal(child.status, 1)
  assert.match(child.stderr, /AI Control disabled/)
  assert.doesNotMatch(child.stderr, /no CDP on 127/)
})
