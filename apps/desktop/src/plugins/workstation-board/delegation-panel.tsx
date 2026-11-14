import { useState } from 'react'

import { type CardDetails, delegateCard, syncCardDelegation } from './api'

export function DelegationPanel({ card, busy, run }: {
  card: CardDetails
  busy: boolean
  run: (action: () => Promise<unknown>) => Promise<void>
}) {
  const latest = card.delegations.at(-1)
  const [assignee, setAssignee] = useState(latest?.assignee ?? '')
  const [confirmed, setConfirmed] = useState(false)
  const terminal = latest?.state === 'done' || latest?.state === 'archived'
  const canDelegate = !latest || !latest.task_id || terminal

  return <section aria-label="Delegação do cartão" className="mt-3 flex flex-col gap-2">
    <h3 className="text-xs font-semibold">Delegação opcional</h3>
    {latest && <p className="break-all text-xs">
      Tentativa {latest.attempt}: {latest.state}
      {latest.task_id ? ` — tarefa ${latest.task_id}` : ' — aguardando vínculo'}
      {latest.task_status && ` (${latest.task_status})`}
    </p>}
    {latest?.last_error && <p className="text-xs text-destructive">Falha na última tentativa: {latest.last_error}</p>}
    {canDelegate && <>
      <input aria-label="Agente responsável (opcional)"
        className="rounded border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) p-1 text-xs"
        maxLength={100} onChange={event => setAssignee(event.target.value)}
        placeholder="Agente responsável (opcional)" value={assignee} />
      <label className="flex items-start gap-2 text-xs">
        <input checked={confirmed} onChange={e => setConfirmed(e.target.checked)} type="checkbox" />
        Confirmo a criação de uma tarefa oficial no Hermes; ela poderá iniciar execução.
      </label>
      <button className="rounded border border-(--ui-stroke-secondary) p-1 text-xs"
        disabled={busy || !confirmed} onClick={() => void run(() =>
          delegateCard(card.id, card.revision, assignee.trim() || null, Boolean(terminal)))}
        type="button">{latest?.task_id ? 'Nova tentativa' : 'Delegar cartão'}</button>
    </>}
    {latest?.task_id && <button className="rounded border border-(--ui-stroke-secondary) p-1 text-xs"
      disabled={busy} onClick={() => void run(() => syncCardDelegation(card.id))}
      type="button">Sincronizar status</button>}
  </section>
}
