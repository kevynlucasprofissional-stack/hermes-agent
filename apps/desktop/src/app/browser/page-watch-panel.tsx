import type { PageWatchConfig, PageWatchStatus } from '../../../electron/workstation-browser-page-watch'

export interface PageWatchPanelProps {
  activeTabId: string | null
  config: PageWatchConfig | null
  status: PageWatchStatus | null
  gateQualified: boolean
  onEnable: () => void
  onPause: () => void
}

/** P06 inert renderer component. Mount only after authorized Browser IPC integration. */
export function PageWatchPanel({
  activeTabId, config, status, gateQualified, onEnable, onPause
}: PageWatchPanelProps) {
  const matchingTab = Boolean(config && activeTabId === config.tab_id)
  const isActive = matchingTab && status?.status === 'watching'
  const canEnable = gateQualified && matchingTab && !isActive

  return (
    <section aria-label="Monitoramento da página" className="flex flex-col gap-1 rounded border p-2 text-xs">
      <div className="flex justify-between items-center gap-2">
        <span className="font-medium">Monitoramento da página</span>
        <span role="status">
          {!gateQualified ? 'Aguardando qualificação' :
            !matchingTab ? 'Sem aba configurada' :
              isActive ? 'Observando' : status?.status === 'paused' ? 'Pausado' : 'Inativo'}
        </span>
      </div>
      {config && matchingTab && <p className="text-(--ui-text-tertiary)">
        Regra: {config.rule} · Origem: {config.origin}
      </p>}
      {status?.lastEvent && matchingTab && <p className="text-(--ui-text-tertiary)">
        Última alteração: {status.lastEvent.observed_at} ·
        ID: {status.lastEvent.event_id.slice(0, 12)}
      </p>}
      {status?.reason === 'auth_required' && <p role="alert">Autenticação necessária: observação pausada.</p>}
      {(status?.reason === 'renderer_crash' || status?.reason === 'origin_mismatch') &&
        <p role="alert">Observação interrompida: {status.reason}.</p>}
      <div className="flex gap-1">
        <button aria-label="Ativar monitoramento" className="rounded border px-2 py-1" disabled={!canEnable}
          onClick={onEnable} type="button">
          Ativar monitoramento
        </button>
        <button aria-label="Pausar monitoramento" className="rounded border px-2 py-1" disabled={!gateQualified || !isActive}
          onClick={onPause} type="button">
          Pausar
        </button>
      </div>
      <p className="text-(--ui-text-tertiary)">
        Configuração pode persistir; observação só existe enquanto a aba autorizada estiver ativa.
      </p>
    </section>
  )
}
