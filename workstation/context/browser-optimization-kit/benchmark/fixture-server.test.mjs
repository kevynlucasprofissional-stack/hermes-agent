import assert from 'node:assert/strict'
import test from 'node:test'

import { startFixtureServer } from './fixture-server.mjs'
import { BROW01_SCENARIOS } from './measurements.mjs'

test('loopback fixture smoke serves seven scenarios and isolates run state', async () => {
  const server = await startFixtureServer({ port: 0 })
  try {
    const origin = new URL(server.baseUrl)
    assert.equal(origin.hostname, '127.0.0.1')
    assert.ok(Number(origin.port) > 0)
    const health = await fetch(new URL('/health', origin))
    assert.equal(health.status, 200)
    assert.deepEqual(await health.json(), { ready: true, classification: 'FIXTURE_SMOKE', native_browser_qualification: 'NV' })
    assert.equal(BROW01_SCENARIOS.length, 7)
    for (const scenario of [...BROW01_SCENARIOS, 'navigation-target']) {
      const response = await fetch(new URL(`/scenario/${scenario}?run_id=smoke-a`, origin))
      assert.equal(response.status, 200, scenario)
      assert.equal(response.headers.get('x-brow01-classification'), 'FIXTURE_SMOKE')
      assert.match(await response.text(), /<html/i)
    }
    const stateUrl = new URL('/api/state/forms?run_id=smoke-a', origin)
    assert.deepEqual(await (await fetch(stateUrl)).json(), { scenario: 'forms', run_id: 'smoke-a', write_count: 0, value: null })
    const value = { name: 'Local smoke', email: 'smoke@example.invalid' }
    const write = await fetch(stateUrl, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(value) })
    assert.equal(write.status, 200)
    await write.text()
    assert.deepEqual(await (await fetch(stateUrl)).json(), { scenario: 'forms', run_id: 'smoke-a', write_count: 1, value })
    const other = await (await fetch(new URL('/api/state/forms?run_id=smoke-b', origin))).json()
    assert.equal(other.write_count, 0)
    assert.equal(other.value, null)
    const otherScenario = await (await fetch(new URL('/api/state/rich-editor?run_id=smoke-a', origin))).json()
    assert.equal(otherScenario.write_count, 0)
  } finally {
    await server.close()
  }
  await assert.rejects(fetch(new URL('/health', server.baseUrl), { signal: AbortSignal.timeout(2000) }))
})
