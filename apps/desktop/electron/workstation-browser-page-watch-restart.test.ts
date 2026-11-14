import { describe, expect, it } from 'vitest'

import { type PageChangedEvent, type PageWatchConfig, PageWatchCoordinator } from './workstation-browser-page-watch'

const cfg: PageWatchConfig = {
  id: 'watch-restart-test', session_id: 'test-session', tab_id: 'test-tab',
  origin: 'https://fixture.example', selector: '#items', rule: 'child_count',
  route_id: 'fixture-route', enabled: true
}

async function captureTransition(at: number): Promise<PageChangedEvent> {
  let count = 1
  let now = at
  const events: PageChangedEvent[] = []

  const coordinator = new PageWatchCoordinator({
    now: () => now, debounceMs: 100,
    onEvent: event => { events.push(event) }
  })

  await coordinator.arm(cfg, async () => ({ state: 'ok', count, origin: cfg.origin }))
  count = 2
  now += 1
  await coordinator.probeOnce(cfg.id)
  now += 120
  await coordinator.probeOnce(cfg.id)
  expect(events).toHaveLength(1)
  coordinator.pause(cfg.id, 'tab_closed')

  return events[0]
}

describe('P06-R: RED real restart identity regression', () => {
  it('two legitimate 1 to 2 transitions across independent activations require DISTINCT event_ids', async () => {
    const first = await captureTransition(1_000)
    const afterRestart = await captureTransition(100_000)
    expect(first.event_id).not.toBe(afterRestart.event_id)
  })

  it('same event emitted twice from one coordinator is suppressed', async () => {
    let now = 1_000
    let count = 1
    const events: PageChangedEvent[] = []

    const coordinator = new PageWatchCoordinator({
      now: () => now, debounceMs: 100, onEvent: event => { events.push(event) }
    })

    await coordinator.arm(cfg, async () => ({ state: 'ok', count, origin: cfg.origin }))
    count = 2
    now += 1
    await coordinator.probeOnce(cfg.id)
    now += 120
    await coordinator.probeOnce(cfg.id)
    now += 200
    await coordinator.probeOnce(cfg.id)
    expect(events).toHaveLength(1)
  })

  it('concurrent probes of same changed count publish only once after durable reserve', async () => {
    let now=1000
    let count=1
    let release!: (value:string)=>void
    const pending=new Promise<string>(resolve=>{release=resolve})
    const accepted:PageChangedEvent[]=[]

    const coordinator=new PageWatchCoordinator({
      now:()=>now,debounceMs:100,
      reserveEventId:()=>pending,
      onEvent:e=>accepted.push(e)
    })

    await coordinator.arm(cfg,async()=>({state:'ok',origin:cfg.origin,count}))
    count=2
    now+=1
    await coordinator.probeOnce(cfg.id)
    now+=130
    const first=coordinator.probeOnce(cfg.id)
    const second=coordinator.probeOnce(cfg.id)
    release('a'.repeat(64))
    await Promise.all([first,second])
    expect(accepted).toHaveLength(1)
    expect(accepted[0].event_id).toBe('a'.repeat(64))
  })
})
