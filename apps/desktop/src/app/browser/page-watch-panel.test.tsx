import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PageWatchPanel } from './page-watch-panel'

const config = {
  id: 'watch-1', session_id: 'session-1', tab_id: 'tab-1',
  origin: 'https://fixture.example', selector: '#items',
  rule: 'child_count' as const, route_id: 'authorized-route', enabled: true
}

const status = { id: 'watch-1', status: 'paused' as const, reason: 'auth_required' as const,
  lastCount: 1, lastEvent: null }

describe('P06 panel gating (not mounted in BrowserView)', () => {
  afterEach(() => cleanup())

  it('cannot activate when P02/P04 or Browser authority gate is HOLD', () => {
    const onEnable = vi.fn()
    render(<PageWatchPanel activeTabId="tab-1" config={config} gateQualified={false}
      onEnable={onEnable} onPause={vi.fn()} status={status} />)
    const button = screen.getByRole('button', { name: 'Ativar monitoramento' }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
    fireEvent.click(button)
    expect(onEnable).not.toHaveBeenCalled()
    expect(screen.getByText('Aguardando qualificação')).toBeDefined()
  })

  it('can activate only after explicit qualification for the bound tab', () => {
    const onEnable = vi.fn()

    const { rerender } = render(<PageWatchPanel activeTabId="other-tab" config={config}
      gateQualified onEnable={onEnable} onPause={vi.fn()} status={status} />)

    expect((screen.getByRole('button', { name: 'Ativar monitoramento' }) as HTMLButtonElement).disabled).toBe(true)
    rerender(<PageWatchPanel activeTabId="tab-1" config={config} gateQualified
      onEnable={onEnable} onPause={vi.fn()} status={status} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ativar monitoramento' }))
    expect(onEnable).toHaveBeenCalledOnce()
    expect(screen.getByRole('alert').textContent).toContain('Autenticação necessária')
  })

  it('pauses only an active watch and never displays page text', () => {
    const onPause = vi.fn()

    const live = { ...status, status: 'watching' as const, reason: null,
      lastEvent: { type: 'page_changed' as const, source: 'page_watch' as const,
        watch_id: 'watch-1', event_id: 'a'.repeat(64), session_id:'session-1',
        tab_id:'tab-1', origin:'https://fixture.example', route_id:'authorized-route',
        fingerprint:'b'.repeat(64),previous:1,current:2, observed_at:'2026-10-27T16:30:00.000Z'} }

    render(<PageWatchPanel activeTabId="tab-1" config={config} gateQualified
      onEnable={vi.fn()} onPause={onPause} status={live} />)
    fireEvent.click(screen.getByRole('button', { name: 'Pausar monitoramento' }))
    expect(onPause).toHaveBeenCalledOnce()
    expect(screen.getByText(/Última alteração/)).toBeDefined()
    expect(screen.queryByText(/password/)).toBeNull()
  })
})
