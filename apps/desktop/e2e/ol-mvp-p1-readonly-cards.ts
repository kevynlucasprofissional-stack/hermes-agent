/**
 * OL-MVP P1: deterministic LOCAL, READ-ONLY browser fixture.
 *
 * This is real HTTP/Chromium DOM, not live Trello and not proof of Experience
 * Compiler adoption. Reuse the canonical Electron BrowserTask/controller.
 * Never send data from real boards to a test page.
 */
export const OL_MVP_READONLY_CARDS = [
  { id: 'ol-card-a', title: 'Planejar pauta semanal', list: 'A fazer', description: 'Conferir temas e fontes' },
  { id: 'ol-card-b', title: 'Revisar legenda', list: 'Em andamento', description: 'Verificar texto e CTA' },
  { id: 'ol-card-c', title: 'Publicar carrossel', list: 'Revisao', description: 'Confirmar arte final' }
] as const

export const OL_MVP_READONLY_PATH = '/ol-mvp-p1-readonly'
export const OL_MVP_READONLY_TITLE = 'OL-MVP P1 read-only cards'

export function renderOlMvpReadOnlyCards(): string {
  const cards = OL_MVP_READONLY_CARDS.map(card => `<article data-testid="ol-mvp-card"
      data-card-id="${card.id}" data-list="${card.list}">
      <h2>${card.title}</h2><p>${card.description}</p>
    </article>`).join('\n')

  return `<!doctype html>
<html lang="pt-BR">
  <head><meta charset="utf-8"><title>${OL_MVP_READONLY_TITLE}</title></head>
  <body><main aria-label="OL-MVP P1 browser read-only fixture">
    <h1>Cartoes de teste — somente leitura</h1>${cards}
  </main></body>
</html>`
}
