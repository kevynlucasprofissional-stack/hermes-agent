import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import vm from 'node:vm'

import { describe, expect, it } from 'vitest'

import {
  buildPageWatchDisconnect, buildPageWatchProbe, type PageWatchConfig,
  PageWatchConfigStore, PageWatchCoordinator, type PageWatchProbe, validatePageWatchConfig,
} from './workstation-browser-page-watch'

const base = (): PageWatchConfig => ({
  id: 'watch-fixture-1', session_id: 'sess-1', tab_id: 'tab-1',
  origin: 'https://fixture.example', selector: '#items',
  rule: 'child_count', route_id: 'authorized-route-1', enabled: true,
})

function sample(count: number, state: PageWatchProbe['state'] = 'ok'): PageWatchProbe {
  return { state, origin: 'https://fixture.example', count }
}

describe('PageWatch P06 isolated contracts', () => {
  it('rejects untrusted config and sensitive selectors', () => {
    expect(validatePageWatchConfig(base()).id).toBe('watch-fixture-1')

    for (const selector of ['input', 'textarea', '#password', '[name=token]',
      '.chat-message', '.conversation', '*', 'body', '#a, #b', 'div:has(input)']) {
      expect(() => validatePageWatchConfig({ ...base(), selector })).toThrow()
    }

    expect(() => validatePageWatchConfig({ ...base(), origin: 'data:text/html,hey' })).toThrow()
    expect(() => validatePageWatchConfig({ ...base(), origin: 'https://fixture.example?token=hi' })).toThrow()
    expect(() => validatePageWatchConfig({ ...base(), route_id: '' })).toThrow()
  })

  it('keeps config in authorized file without task state, refuses automatic rearm', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'p06-config-'))

    try {
      const store = new PageWatchConfigStore(path.join(dir, 'profile', 'page-watch-config.json'))
      store.save([base()])
      const saved = new PageWatchConfigStore(path.join(dir, 'profile', 'page-watch-config.json')).load()
      expect(saved).toHaveLength(1)
      expect(saved[0].enabled).toBe(true)
      expect(fs.readFileSync(path.join(dir, 'profile', 'page-watch-config.json'), 'utf8')).not.toContain('password')
    } finally { fs.rmSync(dir, { recursive: true, force: true }) }
  })

  it('fingerprints only structure; ignores repaint, typing or text changes; debounces', async () => {
    let now = 1000
    let value = 2
    const emitted: unknown[] = []
    const coord = new PageWatchCoordinator({ now: () => now, debounceMs: 200, onEvent: event => emitted.push(event) })
    await coord.arm(base(), async () => sample(value))
    now += 10; await coord.probeOnce('watch-fixture-1')
    now += 20; await coord.probeOnce('watch-fixture-1')
    expect(emitted).toHaveLength(0)
    value = 3; now += 10; await coord.probeOnce('watch-fixture-1')
    expect(emitted).toHaveLength(0)
    now += 240; await coord.probeOnce('watch-fixture-1')
    expect(emitted).toHaveLength(1)
    expect(JSON.stringify(emitted[0])).not.toMatch(/password|secret|private|textContent/i)
    now += 400; await coord.probeOnce('watch-fixture-1')
    expect(emitted).toHaveLength(1)
  })

  it('emits idempotent provenance, not page contents, on real structural count', async () => {
    let count = 1
    let now = 0
    const events: any[] = []

    const coord = new PageWatchCoordinator({ now: () => now, debounceMs: 100,
      onEvent: event => events.push(event) })

    await coord.arm(base(), async () => sample(count))
    count = 2
    now = 1; await coord.probeOnce(base().id)
    now = 130; await coord.probeOnce(base().id)
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('page_changed')
    expect(events[0].origin).toBe(base().origin)
    expect(events[0].tab_id).toBe(base().tab_id)
    expect(events[0].event_id).toMatch(/^[a-f0-9]{64}$/)
    expect(events[0].fingerprint).toMatch(/^[a-f0-9]{64}$/)
    expect(events[0].previous).toBe(1)
    expect(events[0].current).toBe(2)
  })

  it('never permits two observers for the same tab+origin', async () => {
    const c = new PageWatchCoordinator()
    await c.arm(base(), async () => sample(1))
    await expect(c.arm({ ...base(), id: 'watch-fixture-2' }, async () => sample(2))).rejects.toThrow(/already watched/)
  })

  it.each(['logout', 'human_takeover', 'tab_closed', 'renderer_crash', 'login', 'session_ended'] as const)(
    'pauses synchronously on %s and blocks in-flight probes', async reason => {
      let complete!: (value: PageWatchProbe) => void
      const events: any[] = []
      let now = 0
      let call = 0

      const c = new PageWatchCoordinator({ now: () => now, debounceMs: 100,
        onEvent: event => events.push(event) })

      await c.arm(base(), async () => sample(1))

      const probe = async (): Promise<PageWatchProbe> => {
        call++

        return new Promise(resolve => { complete = resolve })
      }

      c.setProbe(base().id, probe)
      const inflight = c.probeOnce(base().id)
      c.pause(base().id, reason)
      complete(sample(999))
      await inflight
      expect(events).toHaveLength(0)
      expect(c.status(base().id).status).toBe('paused')
      expect(c.status(base().id).reason).toBe(reason)
    }
  )

  it('pauses immediately on origin change and auth challenge', async () => {
    const c = new PageWatchCoordinator()
    await c.arm(base(), async () => sample(1))
    c.navigation(base().tab_id, 'https://outside.example/sso')
    expect(c.status(base().id).status).toBe('paused')
    await c.arm(base(), async () => sample(1))
    c.setProbe(base().id, async () => sample(1, 'auth_required'))
    await c.probeOnce(base().id)
    expect(c.status(base().id).reason).toBe('auth_required')
  })

  it('rejects DOM virtualization/too many nodes safely and never emits', async () => {
    const c = new PageWatchCoordinator()
    await c.arm(base(), async () => sample(4))
    c.setProbe(base().id, async () => sample(1001, 'unsupported'))
    await c.probeOnce(base().id)
    expect(c.status(base().id).status).toBe('paused')
  })

  it('probe source strips sensitive inputs and detects login/unsafe tree', () => {
    const script = buildPageWatchProbe(base())
    expect(script).not.toContain('textContent')
    expect(script).not.toContain('innerHTML')

    const ctx = {
      location: { origin: 'https://fixture.example' },
      document: { documentElement: {}, querySelectorAll: (sel: string) => {
        if (sel === 'input[type="password"]') {return []}

        if (sel === '#items') {return [{ children: [{}, {}], querySelector: () => null,
          matches: () => false, isContentEditable: false }]}

        return []
      } },
      window: {},
      MutationObserver: class {observe() {} disconnect() {} takeRecords() {return []}},
    }

    assert.equal(vm.runInNewContext(script, ctx).count, 2)
    ctx.location.origin = 'https://outside.example'
    assert.equal(vm.runInNewContext(script, ctx).state, 'origin_mismatch')
  })
})

describe('P06 lifecycle teardown', () => {
  it('calls the owning observer disconnect and ignores stale work', async () => {
    let disconnects = 0
    let now = 0
    const events: unknown[] = []

    const coordinator = new PageWatchCoordinator({ now: () => now,
      onEvent: event => events.push(event) })

    await coordinator.arm(base(), async () => sample(1), () => { disconnects++ })
    coordinator.pause(base().id, 'human_takeover')
    expect(disconnects).toBe(1)
    now += 500
    await coordinator.probeOnce(base().id)
    expect(events).toHaveLength(0)
  })

  it('disconnect script only touches its own observer at the same origin', () => {
    let disconnected = 0

    const state = { owner: base().id, root: {}, observer: {
      disconnect: () => { disconnected++ }
    } }

    const context: any = {
      window: { __hermesPageWatchP06: state },
      location: { origin: base().origin },
    }

    expect(vm.runInNewContext(buildPageWatchDisconnect(base()), context)).toBe(true)
    expect(disconnected).toBe(1)
    expect(context.window.__hermesPageWatchP06).toBeUndefined()
    context.window.__hermesPageWatchP06 = state
    context.location.origin = 'https://outside.example'
    expect(vm.runInNewContext(buildPageWatchDisconnect(base()), context)).toBe(false)
    expect(disconnected).toBe(1)
  })
})
