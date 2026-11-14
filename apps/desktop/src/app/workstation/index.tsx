/** One Workstation surface with internal tools rather than separate sidebar pages. */
import { Codicon } from '@hermes/plugin-sdk'
import { lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router'

const BrowserTools = lazy(async () => ({ default: (await import('../browser')).BrowserView }))
const DatabaseTools = lazy(async () => ({ default: (await import('@/plugins/workstation-board/board')).WorkstationBoardPage }))
const VaultTools = lazy(async () => ({ default: (await import('@/plugins/vault/vault-page')).VaultPage }))
const CreativeTools = lazy(async () => ({ default: (await import('../creative-workspace')).CreativeWorkspacePage }))

type WorkstationArea = 'browser' | 'creative' | 'database' | 'home' | 'vault'

function selectedArea(search: string): WorkstationArea {
  const params = new URLSearchParams(search)
  const selected = params.get('module')

  if (selected === 'browser' || params.get('creative') === '1') {
    return 'browser'
  }

  return selected === 'creative' || selected === 'database' || selected === 'vault' ? selected : 'home'
}

const navButton = 'rounded-lg border border-(--ui-stroke-secondary) px-3 py-1.5 text-xs hover:bg-(--ui-control-hover-background)'
const tileButton = 'group flex flex-col gap-3 rounded-xl border border-(--ui-stroke-secondary) bg-(--ui-card-background) p-5 text-left transition-colors hover:bg-(--ui-control-hover-background)'

export function WorkstationHub() {
  const location = useLocation()
  const navigate = useNavigate()
  const area = selectedArea(location.search)

  const open = (target: WorkstationArea) => {
    navigate(target === 'home' ? '/browser' : `/browser?module=${target}`)
  }

  return (
    <section aria-label="Hermes Workstation" className="flex h-full min-h-0 flex-col overflow-hidden bg-(--ui-main-surface-background)">
      <header className="flex shrink-0 flex-wrap items-center gap-2 border-b border-(--ui-stroke-secondary) px-4 py-3">
        <Codicon name="layers" size="1rem" />
        <h1 className="mr-3 text-sm font-semibold">Hermes Workstation</h1>
        {area !== 'home' && (
          <>
            <button className={navButton} onClick={() => open('home')} type="button">
              <Codicon name="home" size="0.8rem" /> Início
            </button>
            <button aria-current={area === 'browser' ? 'page' : undefined} className={navButton}
              onClick={() => open('browser')} type="button">Navegador</button>
            <button aria-current={area === 'database' ? 'page' : undefined} className={navButton}
              onClick={() => open('database')} type="button">Database</button>
            <button aria-current={area === 'vault' ? 'page' : undefined} className={navButton}
              onClick={() => open('vault')} type="button">Vault</button>
            <button aria-current={area === 'creative' ? 'page' : undefined} className={navButton}
              onClick={() => open('creative')} type="button">Creative Workstation</button>
          </>
        )}
      </header>
      {area === 'home' ? (
        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="mx-auto max-w-4xl">
            <h2 className="text-xl font-semibold">Seu ambiente de trabalho</h2>
            <p className="mt-2 text-sm text-(--ui-text-secondary)">
              Escolha uma área. As ferramentas compartilham o mesmo Workstation.
            </p>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <button className={tileButton} onClick={() => open('browser')} type="button">
                <Codicon name="globe" size="1.4rem" />
                <span className="text-base font-semibold">Navegador</span>
                <span className="text-sm text-(--ui-text-secondary)">
                  Guias, sessões, ferramentas e configurações do navegador existentes.
                </span>
              </button>
              <button className={tileButton} onClick={() => open('database')} type="button">
                <Codicon name="database" size="1.4rem" />
                <span className="text-base font-semibold">Database</span>
                <span className="text-sm text-(--ui-text-secondary)">
                  Bases de tarefas, com visualização em Kanban ou tabela.
                </span>
              </button>
              <button className={tileButton} onClick={() => open('vault')} type="button">
                <Codicon name="book" size="1.4rem" />
                <span className="text-base font-semibold">Vault</span>
                <span className="text-sm text-(--ui-text-secondary)">
                  Notas Markdown, links entre ideias, pesquisa e gráfico de conhecimento.
                </span>
              </button>
              <button className={tileButton} onClick={() => open('creative')} type="button">
                <Codicon name="symbol-color" size="1.4rem" />
                <span className="text-base font-semibold">Creative Workstation</span>
                <span className="text-sm text-(--ui-text-secondary)">
                  Editor audiovisual com timeline, prévia, composição e projetos.
                </span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1">
          <Suspense fallback={<div className="p-4 text-sm text-(--ui-text-secondary)">Carregando módulo…</div>}>
            {area === 'browser' ? <BrowserTools /> : area === 'database' ? <DatabaseTools /> : area === 'vault' ? <VaultTools /> : <CreativeTools />}
          </Suspense>
        </div>
      )}
    </section>
  )
}
