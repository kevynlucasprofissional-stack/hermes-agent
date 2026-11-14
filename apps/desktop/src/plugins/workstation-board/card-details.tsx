/** Independent Database checklist and activity projection for one card. */
import { useQuery, useQueryClient } from '@hermes/plugin-sdk'
import { type FormEvent, useState } from 'react'

import {
  createChecklist, createChecklistItem, deleteChecklist, deleteChecklistItem,
  fetchCardDetails, reorderChecklist, reorderChecklistItem, updateCardMetadata, updateChecklistItem
} from './api'
import { DelegationPanel } from './delegation-panel'

const fieldClass = 'min-w-0 rounded border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) px-2 py-1 text-xs'
const actionClass = 'rounded border border-(--ui-stroke-secondary) px-2 py-1 text-xs disabled:opacity-40'

export function CardDetailsPanel({ cardId }: { cardId: string }) {
  const cache = useQueryClient()
  const [newTitle, setNewTitle] = useState('')
  const [newItems, setNewItems] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const queryKey = ['workstation-board', 'card', cardId]

  const { data, error: queryError, isLoading } = useQuery({
    queryKey,
    queryFn: () => fetchCardDetails(cardId),
    refetchInterval: 15000
  })

  const run = async (action: () => Promise<unknown>) => {
    if (busy) { return }
    setBusy(true)
    setError('')

    try {
      await action()
      await cache.invalidateQueries({ queryKey })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  const submit = (event: FormEvent, action: () => Promise<unknown>) => {
    event.preventDefault()
    void run(action)
  }

  if (isLoading) { return <p className="text-xs">Carregando detalhes…</p> }

  if (queryError || !data?.card) {
    return <p className="mt-3 text-xs text-destructive" role="alert">
      Detalhes indisponíveis. Verifique se o backend da Database foi atualizado.
    </p>
  }

  return (
    <div className="mt-4 flex flex-col gap-4 border-t border-(--ui-stroke-secondary) pt-3">
      {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
      <section aria-label="Checklists do cartão" className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold">Checklists</h3>
        {(data?.card.checklists ?? []).map((checklist, listIndex, allLists) => (
          <div className="rounded border border-(--ui-stroke-secondary) p-2" key={checklist.id}>
            <div className="flex items-center justify-between gap-2">
              <strong className="text-xs">{checklist.title}</strong>
              <button aria-label={`Subir checklist ${checklist.title}`} className={actionClass}
                disabled={busy || listIndex === 0}
                onClick={() => void run(() => reorderChecklist(checklist, allLists[listIndex - 1]?.id))} type="button">↑</button>
              <button aria-label={`Descer checklist ${checklist.title}`} className={actionClass}
                disabled={busy || listIndex === allLists.length - 1}
                onClick={() => void run(() => reorderChecklist(checklist, allLists[listIndex + 2]?.id))} type="button">↓</button>
              <button className={actionClass} disabled={busy}
                onClick={() => void run(() => deleteChecklist(checklist))} type="button">Excluir</button>
            </div>
            <ul className="mt-2 space-y-1">
              {checklist.items.map((item, itemIndex) => (
                <li className="flex items-center gap-2 text-xs" key={item.id}>
                  <input aria-label={`Concluir ${item.body}`} checked={Boolean(item.completed)} disabled={busy}
                    onChange={e => void run(() => updateChecklistItem(item, e.target.checked))} type="checkbox" />
                  <span className={item.completed ? 'line-through opacity-70' : ''}>{item.body}</span>
                  <button aria-label={`Subir item ${item.body}`} className={actionClass}
                    disabled={busy || itemIndex === 0}
                    onClick={() => void run(() => reorderChecklistItem(item, checklist.items[itemIndex - 1]?.id))} type="button">↑</button>
                  <button aria-label={`Descer item ${item.body}`} className={actionClass}
                    disabled={busy || itemIndex === checklist.items.length - 1}
                    onClick={() => void run(() => reorderChecklistItem(item, checklist.items[itemIndex + 2]?.id))} type="button">↓</button>
                  <button className={actionClass + ' ml-auto'} disabled={busy}
                    onClick={() => void run(() => deleteChecklistItem(item))} type="button">×</button>
                </li>
              ))}
            </ul>
            <form className="mt-2 flex gap-1" onSubmit={e => submit(e, async () => {
              await createChecklistItem(checklist.id, newItems[checklist.id] ?? '')
              setNewItems(current => ({ ...current, [checklist.id]: '' }))
            })}>
              <input aria-label={`Novo item em ${checklist.title}`} className={fieldClass} maxLength={2000} onChange={e => setNewItems(current => ({ ...current, [checklist.id]: e.target.value }))}
                required
                value={newItems[checklist.id] ?? ''} />
              <button className={actionClass} disabled={busy} type="submit">+</button>
            </form>
          </div>
        ))}
        <form className="flex gap-1" onSubmit={e => submit(e, async () => {
          await createChecklist(cardId, newTitle)
          setNewTitle('')
        })}>
          <input aria-label="Nova checklist" className={fieldClass} maxLength={200} onChange={e => setNewTitle(e.target.value)}
            required value={newTitle} />
          <button className={actionClass} disabled={busy} type="submit">Criar</button>
        </form>
      </section>
      <CardMetadataEditor busy={busy} key={`${data.card.id}:${data.card.revision}`}
        metadata={data.card.metadata ?? {}} onSave={value => run(() => updateCardMetadata(cardId, data.card.revision, value))} />
      <DelegationPanel busy={busy} card={data.card} key={data.card.id} run={run} />
      <section aria-label="Atividades do cartão">
        <h3 className="mb-2 text-xs font-semibold">Atividades</h3>
        <ol className="max-h-40 space-y-1 overflow-y-auto text-xs">
          {(data?.card.activity ?? []).map(event => (
            <li key={event.id}>
              <time dateTime={new Date(event.created_at * 1000).toISOString()}>
                {new Date(event.created_at * 1000).toLocaleString()}
              </time>{' — '}{event.kind}
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

function CardMetadataEditor({ metadata, busy, onSave }: {
  metadata: Record<string, unknown>
  busy: boolean
  onSave: (value: Record<string, unknown>) => Promise<void>
}) {
  const [draft, setDraft] = useState(JSON.stringify(metadata, null, 2))
  const [invalid, setInvalid] = useState('')

  const submitMetadata = (event: FormEvent) => {
    event.preventDefault()

    try {
      const value: unknown = JSON.parse(draft)

      if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new Error('Os metadados precisam ser um objeto JSON.')
      }

      setInvalid('')
      void onSave(value as Record<string, unknown>)
    } catch (error) {
      setInvalid(error instanceof Error ? error.message : String(error))
    }
  }

  return <form aria-label="Metadados do cartão" className="flex flex-col gap-2"
    onSubmit={submitMetadata}>
    <h3 className="text-xs font-semibold">Metadados (JSON)</h3>
    <textarea aria-label="JSON de metadados" className={fieldClass}
      maxLength={16384} onChange={e => setDraft(e.target.value)} rows={4} value={draft} />
    {invalid && <p className="text-xs text-destructive" role="alert">{invalid}</p>}
    <button className={actionClass} disabled={busy} type="submit">Salvar metadados</button>
  </form>
}
