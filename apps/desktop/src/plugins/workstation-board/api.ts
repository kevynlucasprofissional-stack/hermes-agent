import type { PluginRestOptions } from '@hermes/plugin-sdk'

export interface Card {
  id: string
  board_id: string
  column_id: string
  title: string
  description: string
  position: number
  revision: number
  archived: number
}

export interface Column {
  revision: number
  archived: number
  id: string
  board_id: string
  name: string
  position: number
  cards: Card[]
}

export interface Board {
  revision: number
  archived: number
  id: string
  name: string
  created_at: number
  columns: Column[]
}

type Rest = <T>(path: string, options?: PluginRestOptions) => Promise<T>
let rest: Rest | null = null

export function bindBoardApi(ctx: { rest: Rest }): () => void {
  rest = ctx.rest

  return () => { rest = null }
}

function request<T>(path: string, options?: PluginRestOptions): Promise<T> {
  return rest ? rest<T>(path, options) : Promise.reject(new Error('Workstation board unavailable'))
}

export const fetchBoards = (includeArchived = false) => request<{ boards: Array<Pick<Board, 'id' | 'name' | 'created_at' | 'revision' | 'archived'>> }>(`/boards?include_archived=${includeArchived}`)
export const fetchBoard = (id: string, includeArchived = false) => request<{ board: Board }>(`/boards/${encodeURIComponent(id)}?include_archived=${includeArchived}`)
export const createBoard = (name: string) => request<{ board: Board }>('/boards', { method: 'POST', body: { name } })
export const createColumn = (boardId: string, name: string) =>
  request<{ column: Column }>(`/boards/${encodeURIComponent(boardId)}/columns`, { method: 'POST', body: { name } })
export const createCard = (boardId: string, columnId: string, title: string) =>
  request<{ card: Card }>(`/boards/${encodeURIComponent(boardId)}/cards`, {
    method: 'POST', body: { column_id: columnId, title }
  })
export const moveCard = (card: Card, columnId: string) =>
  request<{ card: Card }>(`/cards/${encodeURIComponent(card.id)}/move`, {
    method: 'POST', body: { column_id: columnId, expected_revision: card.revision }
  })
export const editCard = (card: Card, title: string, description: string) =>
  request<{ card: Card }>(`/cards/${encodeURIComponent(card.id)}`, {
    method: 'PATCH', body: { title, description, expected_revision: card.revision }
  })


export interface ChecklistItem {
  id: string
  checklist_id: string
  body: string
  completed: number
  position: number
  revision: number
}

export interface Checklist {
  id: string
  card_id: string
  title: string
  position: number
  revision: number
  items: ChecklistItem[]
}

export interface Activity {
  id: number
  board_id: string
  card_id: string | null
  kind: string
  actor_type: string
  actor_id: string | null
  payload: Record<string, unknown>
  created_at: number
}

export interface CardDetails extends Card {
  checklists: Checklist[]
  activity: Activity[]
  metadata: Record<string, unknown>
  delegations: Delegation[]
}

export const fetchCardDetails = (cardId: string) =>
  request<{ card: CardDetails }>(`/cards/${encodeURIComponent(cardId)}`)
export const createChecklist = (cardId: string, title: string) =>
  request<{ checklist: Checklist }>(`/cards/${encodeURIComponent(cardId)}/checklists`, {
    method: 'POST', body: { title }
  })
export const createChecklistItem = (checklistId: string, body: string) =>
  request<{ item: ChecklistItem }>(`/checklists/${encodeURIComponent(checklistId)}/items`, {
    method: 'POST', body: { body }
  })
export const updateChecklistItem = (item: ChecklistItem, completed: boolean) =>
  request<{ item: ChecklistItem }>(`/checklist-items/${encodeURIComponent(item.id)}`, {
    method: 'PATCH', body: { completed, expected_revision: item.revision }
  })
export const deleteChecklistItem = (item: ChecklistItem) =>
  request<{ deleted: boolean }>(`/checklist-items/${encodeURIComponent(item.id)}/delete`, {
    method: 'POST', body: { expected_revision: item.revision }
  })
export const deleteChecklist = (checklist: Checklist) =>
  request<{ deleted: boolean }>(`/checklists/${encodeURIComponent(checklist.id)}/delete`, {
    method: 'POST', body: { expected_revision: checklist.revision }
  })

export const setArchived = (entity: 'board' | 'column' | 'card', item: { id: string; revision: number }, archived: boolean) =>
  request<{ entity: { id: string; revision: number; archived: number } }>(`/archive/${entity}/${encodeURIComponent(item.id)}`, {
    method: 'PATCH', body: { expected_revision: item.revision, archived }
  })

export const reorderColumn = (column: Column, beforeId?: string) =>
  request<{ column: Column }>(`/columns/${encodeURIComponent(column.id)}/reorder`, {
    method: 'POST', body: { expected_revision: column.revision, before_id: beforeId ?? null }
  })
export const reorderCard = (card: Card, targetColumnId: string, beforeId?: string) =>
  request<{ card: Card }>(`/cards/${encodeURIComponent(card.id)}/reorder`, {
    method: 'POST', body: { expected_revision: card.revision, target_column_id: targetColumnId, before_id: beforeId ?? null }
  })

export const reorderChecklist = (list: Checklist, beforeId?: string) =>
  request<{ checklist: Checklist }>(`/checklists/${encodeURIComponent(list.id)}/reorder`, {
    method: 'POST', body: { expected_revision: list.revision, before_id: beforeId ?? null }
  })

export const reorderChecklistItem = (item: ChecklistItem, beforeId?: string) =>
  request<{ item: ChecklistItem }>(`/checklist-items/${encodeURIComponent(item.id)}/reorder`, {
    method: 'POST', body: { expected_revision: item.revision, before_id: beforeId ?? null }
  })

export const updateCardMetadata = (cardId: string, expectedRevision: number, metadata: Record<string, unknown>) =>
  request<{ card: CardDetails }>(`/cards/${encodeURIComponent(cardId)}/metadata`, {
    method: 'PATCH', body: { expected_revision: expectedRevision, metadata }
  })

export interface Delegation {
  id: string
  card_id: string
  attempt: number
  assignee: string | null
  task_id: string | null
  state: string
  task_status: string | null
  last_error: string | null
}

export const delegateCard = (cardId: string, expectedRevision: number,
  assignee: string | null, newAttempt: boolean) =>
  request<{ delegation: Delegation }>(`/cards/${encodeURIComponent(cardId)}/delegate`, {
    method: 'POST',
    body: { confirmed: true, expected_revision: expectedRevision, assignee, new_attempt: newAttempt }
  })

export const syncCardDelegation = (cardId: string) =>
  request<{ delegation: Delegation | null }>(`/cards/${encodeURIComponent(cardId)}/delegation/sync`, {
    method: 'POST'
  })


// Relational source snapshots are immutable; edits are persisted in a versioned local overlay.
export interface DatasetView {
  id: string
  label: string
  dataset: string
  table: string
  fields: string[]
  group_by: string | null
}
export interface DatasetTable { name: string; count: number }
export interface DatasetSource {
  id: string
  tables: DatasetTable[]
  foreign_key_violations: number
  writable?: boolean
  write_mode?: string
}
export interface DatasetCatalog { datasets: DatasetSource[]; views: DatasetView[] }
export interface DatasetPage {
  dataset: string
  table: string
  columns: Array<{ name: string; type: string; primary_key: boolean }>
  primary_key: string
  rows: Array<Record<string, unknown>>
  count: number
  total: number
  limit: number
  offset: number
}
export interface DatasetRelation {
  dataset: string
  table: string
  id: string | number
  relation: string
  exists: boolean
}
export interface DatasetRecord {
  dataset: string
  table: string
  primary_key: string
  record: Record<string, unknown>
  relations: DatasetRelation[]
  local_revision: number
  pending_external_sync: boolean
  source_conflict_fields: string[]
}

export const fetchDatasetCatalog = () => request<DatasetCatalog>('/datasets')

export const fetchDatasetPage = (
  dataset: string, table: string, fields?: string[], offset = 0
) => {
  const search = new URLSearchParams({ limit: '500', offset: String(offset) })

  if (fields?.length) {search.set('columns', fields.join(','))}

  return request<DatasetPage>(
    `/datasets/${encodeURIComponent(dataset)}/tables/${encodeURIComponent(table)}?${search.toString()}`
  )
}

export const updateDatasetRecord = (
  dataset: string, table: string, id: string | number,
  expectedRevision: number, changes: Record<string, string | number | null>
) => request<{ ok: boolean; revision: number; pending_external_sync: boolean }>(
  `/datasets/${encodeURIComponent(dataset)}/tables/${encodeURIComponent(table)}/rows/${encodeURIComponent(id)}`,
  { method: 'PATCH', body: { expected_revision: expectedRevision, changes } }
)

export const fetchDatasetRecord = (dataset: string, table: string, id: string | number) =>
  request<DatasetRecord>(
    `/datasets/${encodeURIComponent(dataset)}/tables/${encodeURIComponent(table)}/rows/${encodeURIComponent(id)}`
  )
