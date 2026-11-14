import { Codicon, Loader, useQuery, useQueryClient } from '@hermes/plugin-sdk'
import { type DragEvent, type FormEvent, useState } from 'react'

import {
  type Card, createBoard, createCard, createColumn, editCard, fetchBoard, fetchBoards,
  moveCard, reorderCard, reorderColumn, setArchived
} from './api'
import { CardDetailsPanel } from './card-details'
import { DatasetExplorer } from './dataset-explorer'

const LIST_KEY = ['workstation-board', 'boards'] as const

export function WorkstationBoardPage() {
  const [source, setSource] = useState<'boards' | 'datasets'>('boards')

  return (
    <div className="flex h-full min-h-0 flex-col">
      <nav aria-label="Origem de dados" className="flex gap-2 border-b border-(--ui-stroke-secondary) p-2 text-xs">
        <button aria-pressed={source === 'boards'} onClick={() => setSource('boards')} type="button">Quadros locais</button>
        <button aria-pressed={source === 'datasets'} onClick={() => setSource('datasets')} type="button">Bases ACIRV</button>
      </nav>
      {source === 'boards' ? <WorkstationBoardLegacy /> : <DatasetExplorer />}
    </div>
  )
}

function WorkstationBoardLegacy() {
  const client = useQueryClient()
  const [selectedId, setSelectedId] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [view, setView] = useState<'kanban' | 'table'>('kanban')
  const [boardName, setBoardName] = useState('')
  const [columnName, setColumnName] = useState('')
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [dragged, setDragged] = useState<Card | null>(null)
  const [editing, setEditing] = useState<Card | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const { data: list, error: listFailure, isLoading: loadingList } = useQuery({
    queryKey: [...LIST_KEY, showArchived],
    queryFn: () => fetchBoards(showArchived),
    refetchInterval: 15_000
  })

  const boardId = selectedId || list?.boards[0]?.id || ''

  const { data: detail, error: detailFailure, isLoading: loadingBoard } = useQuery({
    queryKey: ['workstation-board', 'board', boardId, showArchived],
    queryFn: () => fetchBoard(boardId, showArchived),
    enabled: Boolean(boardId),
    refetchInterval: 15_000
  })

  const board = detail?.board
  const supportsMigration = typeof board?.archived === 'number'

  const refresh = async () => {
    await client.invalidateQueries({ queryKey: LIST_KEY })
    await client.invalidateQueries({ queryKey: ['workstation-board', 'board'] })
  }

  const run = async (action: () => Promise<unknown>) => {
    if (busy) {return}
    setError('')
    setBusy(true)

    try {
      await action()
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  const submit = (event: FormEvent<HTMLFormElement>, action: () => Promise<unknown>) => {
    event.preventDefault()
    void run(action)
  }

  const startDrag = (event: DragEvent<HTMLElement>, card: Card) => {
    setDragged(card)
    event.dataTransfer.effectAllowed = 'move'
  }

  const drop = (event: DragEvent<HTMLElement>, columnId: string) => {
    event.preventDefault()

    if (dragged && dragged.column_id !== columnId) {
      void run(() => moveCard(dragged, columnId))
    }

    setDragged(null)
  }

  const openEdit = (card: Card) => {
    setEditing(card)
    setEditTitle(card.title)
    setEditDescription(card.description)
  }

  const fieldClass = 'min-w-0 rounded border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) px-2 py-1 text-xs text-foreground'
  const actionClass = 'rounded border border-(--ui-stroke-secondary) px-2 py-1 text-xs text-foreground hover:bg-(--chrome-action-hover) disabled:opacity-40'

  return (
    <main aria-label="Database Workstation" className="flex h-full min-h-0 flex-col">
      <header className="flex flex-wrap items-center gap-2 border-b border-(--ui-stroke-secondary) p-3">
        <Codicon name="project" size="1rem" />
        <h1 className="text-sm font-semibold">Database</h1>
        <select aria-label="Selecionar base" className={fieldClass} onChange={e => { setSelectedId(e.target.value); setEditing(null) }}
          value={boardId}>
          {(list?.boards ?? []).map(item => <option key={item.id} value={item.id}>{item.archived ? '[Arquivada] ' : ''}{item.name}</option>)}
        </select>
        <label className="flex items-center gap-1 text-xs">
          <input aria-label="Mostrar arquivados" checked={showArchived}
            onChange={e => { setShowArchived(e.target.checked); setSelectedId(''); setEditing(null) }} type="checkbox" />
          Arquivados
        </label>
        {board && <button className={actionClass} disabled={busy || !supportsMigration} onClick={() => void run(async () => {
          await setArchived('board', board, !board.archived)

          if (!board.archived) { setShowArchived(true) }
          setEditing(null)
        })} type="button">{board.archived ? 'Restaurar base' : 'Arquivar base'}</button>}
        <div aria-label="Visualiza??o da base" className="flex gap-1" role="group">
          <button aria-pressed={view === 'kanban'} className={actionClass} onClick={() => setView('kanban')} type="button">Kanban</button>
          <button aria-pressed={view === 'table'} className={actionClass} onClick={() => setView('table')} type="button">Tabela</button>
        </div>
        <form className="ml-auto flex gap-1" onSubmit={e => submit(e, async () => {
          const created = await createBoard(boardName)
          setBoardName('')
          setSelectedId(created.board.id)
        })}>
          <input aria-label="Nome da nova base" className={fieldClass} maxLength={200}
            onChange={e => setBoardName(e.target.value)} placeholder="Nova base" required value={boardName} />
          <button className={actionClass} disabled={busy} type="submit">Criar base</button>
        </form>
        <button className={actionClass} disabled={busy} onClick={() => void refresh()} type="button">Atualizar</button>
      </header>
      {error && <p className="border-b border-destructive p-2 text-xs text-destructive" role="alert">{error}</p>}
      {(listFailure || detailFailure) && (
        <p className="border-b border-destructive p-2 text-xs text-destructive" role="alert">
          Erro ao carregar a Database: {String((listFailure || detailFailure)?.message ?? (listFailure || detailFailure))}
        </p>
      )}
      {(loadingList || (boardId && loadingBoard)) && !board ? (
        <div className="grid flex-1 place-items-center"><Loader type="lemniscate-bloom" /></div>
      ) : !board ? (
        <div className="grid flex-1 place-items-center text-sm text-(--ui-text-tertiary)">
          Crie uma base de tarefas para começar. Os registros são independentes do Kanban Hermes.
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto p-4">
          {view === 'kanban' ? (
            <>
              {board.columns.map((column, columnIndex) => (
            <section className="flex w-72 shrink-0 flex-col rounded-lg border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) p-2" key={column.id}
              onDragOver={e => e.preventDefault()} onDrop={e => drop(e, column.id)}>
              <h2 className="mb-2 flex items-center justify-between text-xs font-semibold">
                {column.name}
                <button aria-label={`Subir coluna ${column.name}`} className={actionClass}
                  disabled={!supportsMigration || busy || columnIndex === 0}
                  onClick={() => void run(() => reorderColumn(column, board.columns[columnIndex - 1]?.id))} type="button">↑</button>
                <button aria-label={`Descer coluna ${column.name}`} className={actionClass}
                  disabled={!supportsMigration || busy || columnIndex === board.columns.length - 1}
                  onClick={() => void run(() => reorderColumn(column, board.columns[columnIndex + 2]?.id))} type="button">↓</button>
                <span className="text-(--ui-text-tertiary)">{column.cards.length}</span>
                <button className={actionClass} disabled={busy || !supportsMigration} onClick={() => void run(() =>
                  setArchived('column', column, !column.archived))} type="button">
                  {column.archived ? 'Restaurar' : 'Arquivar'}
                </button>
              </h2>
              <div className="min-h-12 flex-1 space-y-2 overflow-y-auto">
                {column.cards.map((card, cardIndex) => (
                  <article className="rounded-md border border-(--ui-stroke-secondary) bg-(--ui-bg-primary) p-2" draggable={!busy}
                    key={card.id} onDragEnd={() => setDragged(null)} onDragStart={e => startDrag(e, card)}>
                    <button className="block w-full text-left text-xs font-medium" onClick={() => openEdit(card)} type="button">
                      {card.title}
                    </button>
                    <div className="mt-1 flex gap-1">
                      <button aria-label={`Subir cartão ${card.title}`} className={actionClass}
                        disabled={!supportsMigration || busy || cardIndex === 0}
                        onClick={() => void run(() => reorderCard(card, column.id, column.cards[cardIndex - 1]?.id))} type="button">↑</button>
                      <button aria-label={`Descer cartão ${card.title}`} className={actionClass}
                        disabled={!supportsMigration || busy || cardIndex === column.cards.length - 1}
                        onClick={() => void run(() => reorderCard(card, column.id, column.cards[cardIndex + 2]?.id))} type="button">↓</button>
                    </div>
                    {card.description && <p className="mt-1 line-clamp-2 text-xs text-(--ui-text-tertiary)">{card.description}</p>}
                    <select aria-label={`Mover ${card.title}`} className="mt-2 w-full text-xs"
                      disabled={busy} onChange={e => void run(() => moveCard(card, e.target.value))}
                      value={card.column_id}>
                      {board.columns.map(dest => <option key={dest.id} value={dest.id}>{dest.name}</option>)}
                    </select>
                  </article>
                ))}
              </div>
              <form className="mt-2 flex gap-1" onSubmit={e => submit(e, async () => {
                await createCard(board.id, column.id, drafts[column.id] ?? '')
                setDrafts(old => ({ ...old, [column.id]: '' }))
              })}>
                <input aria-label={`Novo cartão em ${column.name}`} className={fieldClass} maxLength={200}
                  onChange={e => setDrafts(old => ({ ...old, [column.id]: e.target.value }))} placeholder="Novo cartão" required
                  value={drafts[column.id] ?? ''} />
                <button className={actionClass} disabled={busy} type="submit">+</button>
              </form>
            </section>
          ))}
          <section className="w-60 shrink-0 self-start rounded-lg border border-dashed border-(--ui-stroke-secondary) p-2">
            <form className="flex gap-1" onSubmit={e => submit(e, async () => {
              await createColumn(board.id, columnName)
              setColumnName('')
            })}>
              <input aria-label="Nome da coluna" className={fieldClass} maxLength={200} onChange={e => setColumnName(e.target.value)}
                placeholder="Nova coluna" required value={columnName} />
              <button className={actionClass} disabled={busy} type="submit">+</button>
            </form>
          </section>
            </>
          ) : (
            <div className="min-w-full flex-1 overflow-auto rounded-lg border border-(--ui-stroke-secondary)">
              <table aria-label="Registros da base" className="w-full border-collapse text-left text-xs">
                <thead className="bg-(--ui-bg-secondary)">
                  <tr>
                    <th className="border-b border-(--ui-stroke-secondary) p-3">Tarefa</th>
                    <th className="border-b border-(--ui-stroke-secondary) p-3">Descrição</th>
                    <th className="border-b border-(--ui-stroke-secondary) p-3">Etapa</th>
                    <th className="border-b border-(--ui-stroke-secondary) p-3">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {board.columns.flatMap(column => column.cards.map(card => (
                    <tr className="border-b border-(--ui-stroke-secondary)" key={card.id}>
                      <td className="max-w-52 truncate p-3 font-medium">{card.title}</td>
                      <td className="max-w-72 truncate p-3">{card.description || '—'}</td>
                      <td className="p-3">
                        <select aria-label={`Etapa de ${card.title}`} className={fieldClass} disabled={busy}
                          onChange={event => void run(() => moveCard(card, event.target.value))} value={card.column_id}>
                          {board.columns.map(stage => <option key={stage.id} value={stage.id}>{stage.name}</option>)}
                        </select>
                      </td>
                      <td className="p-3">
                        <button className={actionClass} onClick={() => openEdit(card)} type="button">Editar</button>
                      </td>
                    </tr>
                  )))}
                </tbody>
              </table>
            </div>
          )}
          {editing && (
            <aside className="max-h-full w-80 shrink-0 self-start overflow-y-auto rounded-lg border border-(--ui-stroke-secondary) p-3">
              <h2 className="mb-3 text-sm font-semibold">Editar cartão</h2>
              <form className="flex flex-col gap-2" onSubmit={e => submit(e, async () => {
                await editCard(editing, editTitle, editDescription)
                setEditing(null)
              })}>
                <input aria-label="Título do cartão" className={fieldClass} maxLength={200} onChange={e => setEditTitle(e.target.value)}
                  required value={editTitle} />
                <textarea aria-label="Descrição do cartão" className={fieldClass} maxLength={20000}
                  onChange={e => setEditDescription(e.target.value)} rows={6} value={editDescription} />
                <div className="flex gap-2">
                  <button className={actionClass} disabled={busy} type="submit">Salvar</button>
                  <button className={actionClass} onClick={() => setEditing(null)} type="button">Fechar</button>
                </div>
              </form>
              <button className={actionClass + ' mt-2'} disabled={busy || !supportsMigration}
                onClick={() => void run(async () => {
                  await setArchived('card', editing, !editing.archived)
                  setEditing(null)
                })} type="button">{editing.archived ? 'Restaurar cart?o' : 'Arquivar cart?o'}</button>
              {supportsMigration && <CardDetailsPanel cardId={editing.id} />}
            </aside>
          )}
        </div>
      )}
    </main>
  )
}
