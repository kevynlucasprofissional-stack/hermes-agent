import assert from 'node:assert/strict'

import { afterEach, beforeEach, test, vi } from 'vitest'

const mocked = vi.hoisted(() => ({
  commands: [] as Array<{ command: string; args: string[] }>,
  writes: [] as Array<{ path: string; content: string }>,
  failCommand: '' as string,
  initSlug: 'web-whatsapp-com'
}))

vi.mock('node:child_process', async (loadActual) => {
  const actual = await loadActual() as Record<string, (...args: unknown[]) => unknown>

  return {
    ...actual,
    execFileSync: (command: string, args: string[]) => {
      mocked.commands.push({ command, args })

      if (args[1] === mocked.failCommand) {throw new Error('controlled process failure')}

      if (args[1] === 'init') {return Buffer.from(JSON.stringify({ initialized: true, slug: mocked.initSlug }))}

      return Buffer.from(JSON.stringify({ scanned: true, elements: 1 }))
    }
  }
})

vi.mock('node:fs', async (loadActual) => {
  const actual = await loadActual() as Record<string, (...args: unknown[]) => unknown>

  return {
    ...actual,
    existsSync: (p: unknown) =>
      String(p).endsWith('site-map-web-whatsapp-com.json') || actual.existsSync(p),
    readFileSync: (p: unknown, ...args: unknown[]) =>
      String(p).endsWith('site-map-web-whatsapp-com.json')
        ? JSON.stringify({ version: '1.0', screens: { main: { elements: [] } } })
        : actual.readFileSync(p, ...args),
    writeFileSync: (p: unknown, content: string, ...args: unknown[]) => {
      if (String(p).includes('site-maps') && String(p).endsWith('.local.json')) {
        mocked.writes.push({ path: String(p), content })
      } else {
        actual.writeFileSync(p, content, ...args)
      }
    }
  }
})

import { withAutoHealing } from '../../../../site-ops/framework/auto-heal.mjs'

let clock = Date.now()
beforeEach(() => {
  clock += 31_000
  vi.spyOn(Date, 'now').mockReturnValue(clock)
  mocked.commands.length = 0
  mocked.writes.length = 0
  mocked.failCommand = ''
  mocked.initSlug = 'web-whatsapp-com'
})
afterEach(() => vi.restoreAllMocks())

test('remaps with the existing script and artifact, then retries exactly once', async () => {
  let attempts = 0

  const result = await withAutoHealing('open-chat', () => {
    attempts++

    if (attempts === 1) {throw new Error('Search input not found in site map')}

    return { ready: true }
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' })

  assert.deepEqual(result, { ready: true })
  assert.equal(attempts, 2)
  assert.deepEqual(mocked.commands.map(x => x.args[1]), ['init', 'scan'])

  for (const call of mocked.commands) {
    assert.equal(call.args[0].replaceAll('\\', '/').endsWith('/site-ops/scripts/site-deep-map.mjs'), true)
    assert.equal(call.args[2], 'web.whatsapp.com')
  }

  assert.equal(mocked.writes.length, 1)
  assert.equal(mocked.writes[0].path.replaceAll('\\', '/').endsWith('/hermes-agent/.claude/site-maps/whatsapp-web.local.json'), true)
})

test('non-selector errors do not initiate remap or retry', async () => {
  let attempts = 0
  await assert.rejects(withAutoHealing('open-chat', () => {
    attempts++
    throw Error('Controller unavailable')
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' }), /Controller unavailable/)
  assert.equal(attempts, 1)
  assert.equal(mocked.commands.length, 0)
})

test('failure during remapping does not retry operation or write override', async () => {
  mocked.failCommand = 'scan'
  let attempts = 0
  await assert.rejects(withAutoHealing('open-chat', () => {
    attempts++
    throw Error('Search input not found in site map')
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' }), /controlled process failure/)
  assert.equal(attempts, 1)
  assert.equal(mocked.writes.length, 0)
})

test('after one successful remap, failing operation is not retried repeatedly', async () => {
  let attempts = 0
  await assert.rejects(withAutoHealing('open-chat', () => {
    attempts++
    throw Error('Search input not found in site map')
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' }))
  assert.equal(attempts, 2)
})

test('cooldown prevents a second remap for the same failing operation', async () => {
  let first = true
  await withAutoHealing('open-chat', () => {
    if (first) {
      first = false
      throw Error('Search input not found in site map')
    }

    return { ready: true }
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' })
  const count = mocked.commands.length
  await assert.rejects(withAutoHealing('open-chat', () => {
    throw Error('Search input not found in site map')
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' }), /cooldown active/)
  assert.equal(mocked.commands.length, count)
})

test('rejects an invalid remapper slug without writing an override or retrying', async () => {
  mocked.initSlug = '../unsafe'
  let attempts = 0
  await assert.rejects(withAutoHealing('open-chat', () => {
    attempts++
    throw Error('Search input not found in site map')
  }, { sitePattern: 'web.whatsapp.com', siteSlug: 'whatsapp-web' }), /invalid site slug/)
  assert.equal(attempts, 1)
  assert.equal(mocked.commands.length, 1)
  assert.equal(mocked.writes.length, 0)
})
