// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  installLearningDomObserver,
  detectDomMutationDelta,
  extractContainerBreadcrumb,
  extractControlValueAndUnit,
  isElementSensitive,
  observeQuickDomDelta
} from './workstation-learning-dom'

describe('HLM-MVP DOM breadcrumbs, value extraction, and fast deltas (P05)', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  describe('Container breadcrumb extraction', () => {
    it('extracts container breadcrumbs from aria-label, title, or panel attributes', () => {
      document.body.innerHTML = `
        <div class="panel layer-panel" aria-label="Painel de Camadas">
          <div class="layer-item">
            <button id="add-layer">+</button>
          </div>
        </div>
      `
      const btn = document.getElementById('add-layer')
      expect(extractContainerBreadcrumb(btn)).toBe('Painel de Camadas')
    })

    it('extracts breadcrumb from toolbar and navigation roles', () => {
      document.body.innerHTML = `
        <div role="toolbar" title="Barra de Ferramentas">
          <button id="brush-btn">Pincel</button>
        </div>
      `
      const btn = document.getElementById('brush-btn')
      expect(extractContainerBreadcrumb(btn)).toBe('Barra de Ferramentas')
    })

    it('extracts breadcrumb from inner heading in dialog or sidebar', () => {
      document.body.innerHTML = `
        <div role="dialog">
          <h3>Opções de Mesclagem</h3>
          <button id="confirm-dialog">OK</button>
        </div>
      `
      const btn = document.getElementById('confirm-dialog')
      expect(extractContainerBreadcrumb(btn)).toBe('Opções de Mesclagem')
    })

    it('extracts breadcrumb using class/id heuristics when title is absent', () => {
      document.body.innerHTML = `
        <aside class="sidebar-properties-panel">
          <div>
            <input type="range" id="opacity-slider" value="35" />
          </div>
        </aside>
      `
      const slider = document.getElementById('opacity-slider')
      expect(extractContainerBreadcrumb(slider)).toBe('Painel de Propriedades')
    })

    it('returns undefined if element is outside any container panel', () => {
      document.body.innerHTML = `
        <main>
          <button id="lone-btn">Solitário</button>
        </main>
      `
      const btn = document.getElementById('lone-btn')
      expect(extractContainerBreadcrumb(btn)).toBeUndefined()
    })

    it('sanitizes and strips sensitive container names', () => {
      document.body.innerHTML = `
        <div role="dialog" aria-label="Password & Secret Token Reset">
          <button id="reset-btn">Reset</button>
        </div>
      `
      const btn = document.getElementById('reset-btn')
      expect(extractContainerBreadcrumb(btn)).toBeUndefined()
    })
  })

  describe('Control value and unit extraction', () => {
    it('extracts numeric value and unit from slider controls', () => {
      document.body.innerHTML = `
        <input type="range" id="op-slider" value="35" aria-valuetext="35%" />
      `
      const el = document.getElementById('op-slider')
      const res = extractControlValueAndUnit(el)
      expect(res.currentValue).toBe('35%')
      expect(res.unit).toBe('%')
    })

    it('extracts select options and predefined dropdown values', () => {
      document.body.innerHTML = `
        <select id="blend-select">
          <option value="normal">Normal</option>
          <option value="multiply" selected>Multiply</option>
          <option value="screen">Screen</option>
        </select>
      `
      const el = document.getElementById('blend-select')
      const res = extractControlValueAndUnit(el)
      expect(res.currentValue).toBe('Multiply')
    })

    it('never extracts values from sensitive input fields (passwords, emails, texts)', () => {
      document.body.innerHTML = `
        <input type="password" id="pwd" value="Secret123!" />
        <input type="text" id="free-text" value="Minha anotação privada" />
        <textarea id="notes">Texto livre confidencial</textarea>
        <div id="editable" contenteditable="true">Conteúdo digitado</div>
      `
      expect(isElementSensitive(document.getElementById('pwd'))).toBe(true)
      expect(isElementSensitive(document.getElementById('free-text'))).toBe(true)
      expect(isElementSensitive(document.getElementById('notes'))).toBe(true)
      expect(isElementSensitive(document.getElementById('editable'))).toBe(true)

      expect(extractControlValueAndUnit(document.getElementById('pwd'))).toEqual({})
      expect(extractControlValueAndUnit(document.getElementById('free-text'))).toEqual({})
      expect(extractControlValueAndUnit(document.getElementById('notes'))).toEqual({})
    })
  })

  describe('Micro-tracking of effect (DOM Delta)', () => {
    it('detects modal/dialog opening immediately after action', async () => {
      const container = document.createElement('div')
      document.body.appendChild(container)

      const promise = observeQuickDomDelta(container, 50)

      // Simulate click opening modal dialog
      const dlg = document.createElement('div')
      dlg.setAttribute('role', 'dialog')
      dlg.className = 'modal-backdrop'
      dlg.innerHTML = '<h2>Opções de Mesclagem</h2>'
      container.appendChild(dlg)

      const delta = await promise
      expect(delta.effectKind).toBe('modal_opened')
      expect(delta.summary).toContain('Diálogo ou modal aberto')
    })

    it('detects state toggles (aria-selected, class, aria-expanded)', async () => {
      const container = document.createElement('div')
      const tab = document.createElement('button')
      tab.setAttribute('role', 'tab')
      tab.className = 'tab'
      container.appendChild(tab)
      document.body.appendChild(container)

      const promise = observeQuickDomDelta(container, 50)

      // Simulate toggling selection
      tab.classList.add('selected')
      tab.setAttribute('aria-selected', 'true')

      const delta = await promise
      expect(delta.effectKind).toBe('state_toggled')
      expect(delta.summary).toContain('Alternância de estado')
    })

    it('detects adding new item or layer in layer panel', async () => {
      const list = document.createElement('ul')
      list.className = 'layer-list'
      document.body.appendChild(list)

      const promise = observeQuickDomDelta(list, 50)

      const item = document.createElement('li')
      item.className = 'layer-item'
      item.textContent = 'Camada 2'
      list.appendChild(item)

      const delta = await promise
      expect(delta.effectKind).toBe('item_added')
      expect(delta.summary).toContain('Novo item ou camada')
    })

    it('detects removing an item or layer', async () => {
      const list = document.createElement('ul')
      list.className = 'layer-list'
      const item = document.createElement('li')
      item.className = 'layer-item'
      list.appendChild(item)
      document.body.appendChild(list)

      const promise = observeQuickDomDelta(list, 50)

      list.removeChild(item)

      const delta = await promise
      expect(delta.effectKind).toBe('item_removed')
      expect(delta.summary).toContain('removido')
    })

    it('returns none if no observable mutation occurred', async () => {
      const container = document.createElement('div')
      document.body.appendChild(container)

      const promise = observeQuickDomDelta(container, 30)
      const delta = await promise
      expect(delta.effectKind).toBe('none')
    })
  })

  describe('isolated DOM observer', () => {
    afterEach(() => {
      vi.restoreAllMocks()
      vi.useRealTimers()
    })

    it('rejects page-dispatched events', () => {
      const emit = vi.fn()
      const stop = installLearningDomObserver(emit)
      const button = document.createElement('button')
      document.body.append(button)
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      button.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter' }))
      expect(emit).not.toHaveBeenCalled()
      stop()
    })

    it('preserves trusted click metadata and cancels pending observation on cleanup', async () => {
      vi.useFakeTimers()
      const add = vi.spyOn(window, 'addEventListener')
      const emit = vi.fn()
      const stop = installLearningDomObserver(emit)
      const click = add.mock.calls.find(([type]) => type === 'click')?.[1] as (event: MouseEvent) => void
      const button = document.createElement('button')
      button.innerText = 'Apply'
      document.body.append(button)
      const event = { isTrusted: true, target: button, clientX: 20, clientY: 30 } as unknown as MouseEvent

      click(event)
      await vi.advanceTimersByTimeAsync(250)
      expect(emit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'click', accessibleName: 'Apply', x: 20, y: 30 }))
      emit.mockClear()
      click(event)
      stop()
      await vi.advanceTimersByTimeAsync(250)
      expect(emit).not.toHaveBeenCalled()
    })

    it('does not collect password fields even for trusted input', () => {
      const add = vi.spyOn(window, 'addEventListener')
      const emit = vi.fn()
      const stop = installLearningDomObserver(emit)
      const keydown = add.mock.calls.find(([type]) => type === 'keydown')?.[1] as (event: KeyboardEvent) => void
      const input = document.createElement('input')
      input.type = 'password'
      input.value = 'not-for-capture'
      keydown({ isTrusted: true, target: input, key: 'Enter' } as unknown as KeyboardEvent)
      expect(emit).not.toHaveBeenCalled()
      stop()
    })
  })
})
