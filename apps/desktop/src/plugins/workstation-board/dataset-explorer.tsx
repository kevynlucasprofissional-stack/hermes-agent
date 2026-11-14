import { useQuery } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'

import {
  type DatasetRelation, fetchDatasetCatalog, fetchDatasetPage,
  fetchDatasetRecord, updateDatasetRecord
} from './api'

type Selection = { dataset: string; table: string; id: string | number }

const control = 'rounded border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) px-2 py-1 text-xs'
const action = 'rounded border border-(--ui-stroke-secondary) px-2 py-1 text-xs disabled:opacity-40 hover:bg-(--chrome-action-hover)'

function preview(value: unknown): string {
  if (value == null || value === '') {return '—'}
  const valueText = typeof value === 'object' ? JSON.stringify(value) : String(value)

  return valueText.length > 160 ? valueText.slice(0, 160) + '…' : valueText
}

function heading(row: Record<string, unknown>): string {
  return preview(row.title ?? row.display_name ?? row.name ?? row.code ?? row.chat_title ?? row.id)
}

export function DatasetExplorer() {
  const [viewId, setViewId] = useState('tarefas')
  const [custom, setCustom] = useState<{ dataset: string; table: string } | null>(null)
  const [display, setDisplay] = useState<'table' | 'kanban'>('table')
  const [offset, setOffset] = useState(0)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [editError, setEditError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setEditing(false)
    setEditError('')
  }, [selection?.dataset, selection?.table, selection?.id])

  const { data: catalog, error: catalogError, isLoading: loadingCatalog, refetch: refreshCatalog } = useQuery({
    queryKey: ['workstation', 'datasets', 'catalog'],
    queryFn: fetchDatasetCatalog,
    refetchInterval: 30000,
  })

  const preset = catalog?.views.find(view => view.id === viewId)
  const dataset = custom?.dataset ?? preset?.dataset ?? ''
  const table = custom?.table ?? preset?.table ?? ''
  const fields = custom ? undefined : preset?.fields

  const { data: page, error: pageError, isLoading: loadingPage, refetch: refreshPage } = useQuery({
    queryKey: ['workstation', 'datasets', dataset, table, fields, offset],
    queryFn: () => fetchDatasetPage(dataset, table, fields, offset),
    enabled: Boolean(dataset && table),
  })

  const { data: detail, error: detailError, refetch: refreshDetail } = useQuery({
    queryKey: ['workstation', 'dataset-record', selection?.dataset, selection?.table, selection?.id],
    queryFn: () => fetchDatasetRecord(selection!.dataset, selection!.table, selection!.id),
    enabled: Boolean(selection),
  })

  const selectedSource = catalog?.datasets.find(item => item.id === dataset)

  const saveChanges = async () => {
    if (!selection || !detail || saving) {return}

    try {
      const parsed: unknown = JSON.parse(editText)

      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('O conteúdo deve ser um objeto JSON.')
      }

      const draft = parsed as Record<string, unknown>
      const changes: Record<string, string | number | null> = {}

      for (const [field, value] of Object.entries(draft)) {
        if (field === detail.primary_key || !(field in detail.record)) {continue}

        if (JSON.stringify(detail.record[field]) === JSON.stringify(value)) {continue}

        if (value !== null && typeof value !== 'string' && typeof value !== 'number') {
          throw new Error('Edite apenas campos de texto, número ou valor nulo.')
        }

        changes[field] = value
      }

      if (Object.keys(changes).length === 0) {setEditing(false);

return}

      setSaving(true)
      await updateDatasetRecord(selection.dataset, selection.table, selection.id, detail.local_revision, changes)
      await Promise.all([refreshPage(), refreshDetail()])
      setEditing(false)
      setEditError('')
    } catch (error) {
      setEditError(String(error instanceof Error ? error.message : error))
    } finally {
      setSaving(false)
    }
  }

  const groupField = custom
    ? (page?.columns.some(col => col.name === 'status') ? 'status' : null)
    : preset?.group_by

  const groups = groupField && page
    ? [...new Set(page.rows.map(row => String(row[groupField] ?? '(sem valor)')))]
    : []

  const chooseView = (id: string) => {
    setViewId(id)
    setCustom(null)
    setOffset(0)
    setDisplay('table')
    setSelection(null)
  }

  const chooseTable = (value: string) => {
    const divider = value.indexOf(':')

    if (divider < 0) {return}
    setCustom({ dataset: value.slice(0, divider), table: value.slice(divider + 1) })
    setOffset(0)
    setDisplay('table')
    setSelection(null)
  }

  const navigate = (link: DatasetRelation) => {
    if (!link.exists) {return}
    setCustom({ dataset: link.dataset, table: link.table })
    setOffset(0)
    setDisplay('table')
    setSelection({ dataset: link.dataset, table: link.table, id: link.id })
  }

  return (
    <section aria-label="Bases relacionais ACIRV" className="flex min-h-0 flex-1 flex-col">
      <header className="flex flex-wrap items-center gap-2 border-b border-(--ui-stroke-secondary) p-3">
        <strong className="text-sm">Dados relacionais</strong>
        <label className="flex items-center gap-1 text-xs">
          Visão
          <select aria-label="Visão relacional" className={control} onChange={event => chooseView(event.target.value)} value={viewId}>
            {(catalog?.views ?? []).map(view => (
              <option key={view.id} value={view.id}>{view.label}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1 text-xs">
          Tabela
          <select aria-label="Tabela relacional" className={control} onChange={event => chooseTable(event.target.value)}
            value={dataset && table ? dataset + ':' + table : ''}>
            {(catalog?.datasets ?? []).flatMap(source => source.tables.map(entry => (
              <option key={source.id + ':' + entry.name} value={source.id + ':' + entry.name}>
                {source.id} / {entry.name} ({entry.count})
              </option>
            )))}
          </select>
        </label>
        <div aria-label="Visualização relacional" className="flex gap-1" role="group">
          <button aria-pressed={display === 'table'} className={action} onClick={() => setDisplay('table')} type="button">Tabela</button>
          <button aria-pressed={display === 'kanban'} className={action} disabled={!groupField}
            onClick={() => setDisplay('kanban')} type="button">Kanban</button>
        </div>
        <button className={action} onClick={() => { void refreshCatalog(); void refreshPage() }} type="button">Atualizar</button>
        <span className="text-xs text-(--ui-text-tertiary)">Edição local versionada · fontes originais preservadas</span>
      </header>
      {selectedSource && selectedSource.foreign_key_violations > 0 && (
        <p className="border-b border-(--ui-stroke-secondary) p-2 text-xs" role="status">
          Atenção: {selectedSource.foreign_key_violations} referências inconsistentes herdadas do banco original. Nenhum registro foi descartado.
        </p>
      )}
      {(catalogError || pageError || detailError) && (
        <p className="p-3 text-xs text-destructive" role="alert">
          Erro ao consultar dados relacionais: {String((catalogError || pageError || detailError)?.message)}
        </p>
      )}
      {(loadingCatalog || loadingPage) && !page && <p className="p-3 text-xs">Carregando dados…</p>}
      {!loadingCatalog && catalog?.datasets.length === 0 && (
        <p className="p-3 text-xs">Nenhuma base importada neste perfil Hermes.</p>
      )}
      {page && (
        <div className="flex min-h-0 flex-1 gap-3 overflow-hidden p-3">
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span>{page.dataset} / {page.table} · {page.total} registros · exibindo {page.count}</span>
              <div className="flex gap-1">
                <button className={action} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 500))} type="button">Anterior</button>
                <button className={action} disabled={offset + page.count >= page.total}
                  onClick={() => setOffset(offset + 500)} type="button">Próxima</button>
              </div>
            </div>
            {display === 'kanban' && groupField ? (
              <div className="flex min-h-0 flex-1 gap-2 overflow-auto">
                {groups.map(group => (
                  <section className="flex w-60 shrink-0 flex-col gap-2 rounded border border-(--ui-stroke-secondary) p-2" key={group}>
                    <h3 className="text-xs font-semibold">{group}</h3>
                    <div className="space-y-2 overflow-y-auto">
                      {page.rows.filter(row => String(row[groupField] ?? '(sem valor)') === group).map((row, index) => (
                        <button className="block w-full rounded border border-(--ui-stroke-secondary) p-2 text-left text-xs"
                          key={String(row[page.primary_key] ?? index)} onClick={() => setSelection({
                            dataset, table, id: row[page.primary_key] as string | number
                          })} type="button">
                          <strong>{heading(row)}</strong>
                          <div className="mt-1 text-(--ui-text-tertiary)">{preview(row.priority ?? row.due_at ?? row.id)}</div>
                        </button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            ) : (
              <div className="min-h-0 flex-1 overflow-auto rounded border border-(--ui-stroke-secondary)">
                <table aria-label="Registros relacionais" className="w-full border-collapse text-left text-xs">
                  <thead className="sticky top-0 bg-(--ui-bg-secondary)">
                    <tr>{page.columns.map(col => (
                      <th className="border-b border-(--ui-stroke-secondary) p-2" key={col.name}>{col.name}</th>
                    ))}</tr>
                  </thead>
                  <tbody>{page.rows.map((row, index) => (
                    <tr className="border-b border-(--ui-stroke-secondary)" key={String(row[page.primary_key] ?? index)}>
                      {page.columns.map((col, columnIndex) => (
                        <td className="max-w-64 truncate p-2" key={col.name}>
                          {columnIndex === 0 ? (
                            <button className="text-left underline" onClick={() => setSelection({
                              dataset, table, id: row[page.primary_key] as string | number
                            })} type="button">{preview(row[col.name])}</button>
                          ) : preview(row[col.name])}
                        </td>
                      ))}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </div>
          {selection && (
            <aside aria-label="Detalhes do registro" className="flex w-80 shrink-0 flex-col gap-2 overflow-y-auto rounded border border-(--ui-stroke-secondary) p-3 text-xs">
              <div className="flex items-center justify-between">
                <strong>Registro {selection.id}</strong>
                <button className={action} onClick={() => setSelection(null)} type="button">Fechar</button>
              </div>
              <span className="text-(--ui-text-tertiary)">{selection.dataset} / {selection.table}</span>
              {detail?.pending_external_sync && <span className="text-(--ui-text-tertiary)" role="status">
                Alteração local pendente de sincronização · revisão {detail.local_revision}
              </span>}
              {detail && detail.source_conflict_fields.length > 0 && <p role="alert">
                Fonte alterada desde a edição: {detail.source_conflict_fields.join(', ')}. Revisar conflito.
              </p>}
              {detail && !editing && <button className={action} onClick={() => {
                setEditText(JSON.stringify(detail.record, null, 2)); setEditError(''); setEditing(true)
              }} type="button">Editar registro</button>}
              {detail && editing && <div className="flex flex-col gap-2">
                <label className="font-semibold" htmlFor="dataset-row-editor">Campos do registro (JSON)</label>
                <textarea className={control + ' min-h-48 font-mono'} id="dataset-row-editor" onChange={event => setEditText(event.target.value)}
                  value={editText} />
                <span className="text-(--ui-text-tertiary)">Identificadores e vínculos externos não são editáveis.</span>
                {editError && <p className="text-destructive" role="alert">{editError}</p>}
                <div className="flex gap-2">
                  <button className={action} disabled={saving} onClick={() => {void saveChanges()}}
                    type="button">{saving ? 'Salvando…' : 'Salvar'}</button>
                  <button className={action} disabled={saving} onClick={() => setEditing(false)}
                    type="button">Cancelar</button>
                </div>
              </div>}
              {detail && <dl className="space-y-2">
                {Object.entries(detail.record).map(([key, value]) => (
                  <div key={key}><dt className="font-semibold">{key}</dt>
                    <dd className="break-words whitespace-pre-wrap">{preview(value)}</dd></div>
                ))}
              </dl>}
              {detail && detail.relations.length > 0 && (
                <section className="space-y-1">
                  <h3 className="font-semibold">Registros relacionados</h3>
                  {detail.relations.map(link => (
                    <button className={action + ' block w-full text-left'} disabled={!link.exists}
                      key={link.dataset + ':' + link.table + ':' + link.id}
                      onClick={() => navigate(link)} type="button">
                      {link.relation}: {link.dataset}/{link.table} #{link.id}
                      {!link.exists && ' (referência ausente)'}
                    </button>
                  ))}
                </section>
              )}
            </aside>
          )}
        </div>
      )}
    </section>
  )
}
