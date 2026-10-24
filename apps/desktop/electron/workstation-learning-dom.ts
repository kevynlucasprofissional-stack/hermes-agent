/**
 * HLM-MVP DOM observation, ancestor breadcrumbs, and delta detection (P05).
 * Extracts container breadcrumbs, non-sensitive control values (sliders, selects),
 * and observes fast post-interaction DOM mutations (modals, list changes, state toggles).
 */

import { type DomMutationDelta, type DomMutationEffectKind } from './workstation-learning-events'

export const BREADCRUMB_CONTAINER_SELECTOR =
  '[role="toolbar"], [role="navigation"], [role="dialog"], [role="tabpanel"], aside, [id*="panel"], [id*="sidebar"], [class*="panel"], [class*="layer"], [class*="prop"]'

const SENSITIVE =
  /password|passcode|secret|token|key|credential|authorization|cookie|otp|recovery|private|account|session|api|payment|card|email|address/i

const SAFE_INPUT_TYPES = new Set(['range', 'number', 'checkbox', 'radio', 'button', 'submit', 'reset', 'color'])

export function isElementSensitive(element: Element | null): boolean {
  if (!element) {return false}

  const htmlEl = element as HTMLElement
  if (
    htmlEl.isContentEditable ||
    element.getAttribute?.('contenteditable') === 'true' ||
    element.getAttribute?.('contenteditable') === '' ||
    element.tagName === 'TEXTAREA'
  ) {
    return true
  }

  if (element.tagName === 'INPUT') {
    const type = (element.getAttribute('type') || 'text').toLowerCase()
    if (!SAFE_INPUT_TYPES.has(type)) {
      return true
    }
  }

  const label = element.getAttribute?.('aria-label') || ''
  const title = element.getAttribute?.('title') || ''
  const name = element.getAttribute?.('name') || ''

  return SENSITIVE.test(label) || SENSITIVE.test(title) || SENSITIVE.test(name)
}

const CONTAINER_KEYWORD_MAP: Array<{ match: RegExp; label: string }> = [
  { match: /layer|camada/i, label: 'Painel de Camadas' },
  { match: /filter|filtro/i, label: 'Painel de Filtros' },
  { match: /prop|ajuste/i, label: 'Painel de Propriedades' },
  { match: /color|cor/i, label: 'Painel de Cores' },
  { match: /tool|toolbar/i, label: 'Barra de Ferramentas' },
  { match: /sidebar/i, label: 'Barra Lateral' },
  { match: /history|historico/i, label: 'Histórico' }
]

const ROLE_OR_TAG_MAP: Record<string, string> = {
  dialog: 'Janela de Diálogo',
  toolbar: 'Barra de Ferramentas',
  tabpanel: 'Painel de Abas',
  navigation: 'Navegação',
  aside: 'Barra Lateral'
}

function getHeadingContainerTitle(container: Element): string | undefined {
  const heading = container.querySelector?.('h1, h2, h3, h4, [class*="title"], [class*="header"], legend')
  if (heading && heading.textContent) {
    const text = heading.textContent.trim()
    if (SENSITIVE.test(text)) {
      return undefined
    }
    if (text && text.length <= 50) {
      return text.slice(0, 80)
    }
  }

  return undefined
}

function getHeuristicContainerTitle(idAndClass: string): string | undefined {
  for (const item of CONTAINER_KEYWORD_MAP) {
    if (item.match.test(idAndClass)) {
      return item.label
    }
  }

  return undefined
}

function getRoleOrTagContainerTitle(container: Element): string | undefined {
  const role = container.getAttribute?.('role')?.toLowerCase()
  if (role && ROLE_OR_TAG_MAP[role]) {
    return ROLE_OR_TAG_MAP[role]
  }

  const tag = container.tagName?.toLowerCase()
  if (tag && ROLE_OR_TAG_MAP[tag]) {
    return ROLE_OR_TAG_MAP[tag]
  }

  return undefined
}

export function extractContainerBreadcrumb(element: Element | null): string | undefined {
  if (!element) {return undefined}

  const container = element.closest?.(BREADCRUMB_CONTAINER_SELECTOR)
  if (!container) {return undefined}

  const explicit =
    container.getAttribute?.('aria-label') ||
    container.getAttribute?.('title') ||
    container.getAttribute?.('data-panel-title') ||
    container.getAttribute?.('data-panel') ||
    container.getAttribute?.('aria-roledescription')

  if (explicit && SENSITIVE.test(explicit)) {
    return undefined
  }

  const idAndClass = `${container.id || ''} ${container.className || ''}`
  if (SENSITIVE.test(idAndClass)) {
    return undefined
  }

  if (explicit && explicit.trim()) {
    return explicit.trim().slice(0, 80)
  }

  const headingTitle = getHeadingContainerTitle(container)
  if (headingTitle) {
    return headingTitle
  }

  const heuristicTitle = getHeuristicContainerTitle(idAndClass.toLowerCase())
  if (heuristicTitle) {
    return heuristicTitle
  }

  return getRoleOrTagContainerTitle(container)
}

function extractRawValueFromElement(element: Element): string | undefined {
  const ariaValueText = element.getAttribute?.('aria-valuetext')
  const ariaValueNow = element.getAttribute?.('aria-valuenow')

  if (ariaValueText && !SENSITIVE.test(ariaValueText)) {
    return ariaValueText.trim()
  }
  if (ariaValueNow && !SENSITIVE.test(ariaValueNow)) {
    return ariaValueNow.trim()
  }

  if (element.tagName === 'INPUT') {
    const input = element as HTMLInputElement
    const type = (input.type || 'text').toLowerCase()
    if (type === 'range' || type === 'number') {
      return String(input.value)
    }
  }

  if (element.tagName === 'SELECT') {
    const select = element as HTMLSelectElement
    const selectedText = select.options && select.selectedIndex >= 0 ? select.options[select.selectedIndex]?.text : undefined
    const optVal = selectedText || select.value
    if (optVal && !SENSITIVE.test(optVal)) {
      return optVal.trim()
    }
  }

  return undefined
}

export function extractControlValueAndUnit(element: Element | null): { currentValue?: string; unit?: string } {
  if (!element || isElementSensitive(element)) {
    return {}
  }

  const value = extractRawValueFromElement(element)
  if (!value) {
    return {}
  }

  const unitMatch = value.match(/(%|px|pt|em|rem|deg|s|ms)$/i)

  return {
    currentValue: value.slice(0, 50),
    unit: unitMatch ? unitMatch[1] : undefined
  }
}

function inspectAddedNode(node: Node): { modal: boolean; itemAdded: boolean } {
  if (node.nodeType !== 1) {return { modal: false, itemAdded: false }}
  const el = node as Element
  const modal = Boolean(
    el.matches?.('dialog, [role="dialog"], [class*="modal"], [id*="modal"]') ||
    el.querySelector?.('dialog, [role="dialog"], [class*="modal"], [id*="modal"]')
  )
  const itemAdded = Boolean(
    el.matches?.('[role="listitem"], [class*="layer"], [class*="item"], li, tr') ||
    el.querySelector?.('[role="listitem"], [class*="layer"]')
  )

  return { modal, itemAdded }
}

function inspectRemovedNode(node: Node): boolean {
  if (node.nodeType !== 1) {return false}
  const el = node as Element

  return Boolean(
    el.matches?.('[role="listitem"], [class*="layer"], [class*="item"], li, tr') ||
    el.querySelector?.('[role="listitem"], [class*="layer"]')
  )
}

export function detectDomMutationDelta(mutations: MutationRecord[]): DomMutationDelta {
  let modalFound = false
  let itemAdded = false
  let itemRemoved = false
  let stateToggled = false
  let stateAttrName: string | null = null

  for (const m of mutations) {
    if (m.type === 'childList') {
      for (let i = 0; i < m.addedNodes.length; i++) {
        const res = inspectAddedNode(m.addedNodes[i])
        if (res.modal) {modalFound = true; break}
        if (res.itemAdded) {itemAdded = true}
      }
      for (let i = 0; i < m.removedNodes.length; i++) {
        if (inspectRemovedNode(m.removedNodes[i])) {itemRemoved = true}
      }
    } else if (m.type === 'attributes') {
      const name = m.attributeName
      if (name && ['class', 'aria-expanded', 'aria-selected', 'hidden', 'disabled'].includes(name)) {
        stateToggled = true
        stateAttrName = name
      }
    }
  }

  if (modalFound) {
    return { effectKind: 'modal_opened', summary: 'Diálogo ou modal aberto após a ação' }
  }
  if (itemAdded) {
    return { effectKind: 'item_added', summary: 'Novo item ou camada adicionado à interface' }
  }
  if (itemRemoved) {
    return { effectKind: 'item_removed', summary: 'Item ou camada removido da interface' }
  }
  if (stateToggled) {
    return { effectKind: 'state_toggled', summary: `Alternância de estado ou visibilidade (${stateAttrName})` }
  }

  return { effectKind: 'none' }
}

export function observeQuickDomDelta(root: Node, durationMs = 250): Promise<DomMutationDelta> {
  return new Promise(resolve => {
    if (typeof MutationObserver === 'undefined') {
      resolve({ effectKind: 'none' })
      return
    }

    const records: MutationRecord[] = []
    const observer = new MutationObserver(mutations => {
      records.push(...mutations)
    })

    try {
      observer.observe(root, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class', 'aria-expanded', 'aria-selected', 'hidden', 'disabled']
      })
    } catch {
      resolve({ effectKind: 'none' })
      return
    }

    setTimeout(() => {
      try {
        const pending = observer.takeRecords()
        records.push(...pending)
        observer.disconnect()
      } catch {
        // ignore
      }
      resolve(detectDomMutationDelta(records))
    }, durationMs)
  })
}

export function installLearningDomObserver(emit: (gesture: Record<string, unknown>) => void): () => void {
  let active = true
  const pending = new Set<() => void>()
  const interactiveSelector = 'button, a, [role], [data-tool], [data-action], canvas, input, select'
  const functionalKeys = new Set(['Enter', 'Escape', 'Tab', 'Backspace', 'Delete', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'])

  function targetFor(event: Event): Element | null {
    if (!active || !event.isTrusted || !(event.target instanceof Element)) {return null}
    const target = event.target
    const interactive = target.closest(interactiveSelector) || target

    return isElementSensitive(target) || isElementSensitive(interactive) ? null : interactive
  }

  function describeTarget(element: Element): Record<string, unknown> {
    const tag = element.tagName.toLowerCase()
    const role = element.getAttribute('role')
      || ({ button: 'button', a: 'link', canvas: 'canvas' } as Record<string, string>)[tag]
      || (tag === 'input' && element.getAttribute('type') === 'range' ? 'slider' : undefined)
    const name = element.getAttribute('aria-label') || element.getAttribute('title')
      || element.getAttribute('data-tool')
      || (tag === 'button' ? (element as HTMLElement).innerText?.slice(0, 80) : undefined)

    return { tag, role, accessibleName: name, containerBreadcrumb: extractContainerBreadcrumb(element) }
  }

  function afterAction(gesture: Record<string, unknown>): void {
    const records: MutationRecord[] = []
    const observer = new MutationObserver((mutations) => records.push(...mutations.slice(0, 200 - records.length)))
    const root = document.body || document.documentElement

    observer.observe(root, {
      childList: true, subtree: true, attributes: true,
      attributeFilter: ['class', 'aria-expanded', 'aria-selected', 'hidden', 'disabled']
    })

    const cancel = (): void => {
      clearTimeout(timer)
      observer.disconnect()
      pending.delete(cancel)
    }
    const timer = setTimeout(() => {
      records.push(...observer.takeRecords().slice(0, 200 - records.length))
      cancel()
      if (active) {emit({ ...gesture, domDelta: detectDomMutationDelta(records) })}
    }, 250)

    pending.add(cancel)
  }

  const onClick = (event: MouseEvent): void => {
    const target = targetFor(event)
    if (!target) {return}
    const info = describeTarget(target)

    afterAction({
      kind: 'click', x: event.clientX, y: event.clientY,
      viewportWidth: window.innerWidth, viewportHeight: window.innerHeight,
      role: info.role, accessibleName: info.accessibleName, elementTag: info.tag,
      containerBreadcrumb: info.containerBreadcrumb, ...extractControlValueAndUnit(target)
    })
  }
  const onPointer = (event: PointerEvent): void => {
    const target = targetFor(event)
    if (!target) {return}

    emit({
      kind: event.type, x: event.clientX, y: event.clientY,
      viewportWidth: window.innerWidth, viewportHeight: window.innerHeight,
      target: describeTarget(target)
    })
  }
  const onKey = (event: KeyboardEvent): void => {
    const target = targetFor(event)
    if (!target) {return}
    const hasModifier = event.ctrlKey || event.metaKey || event.altKey

    if (hasModifier) {
      afterAction({
        kind: 'shortcut', key: event.key, ctrl: event.ctrlKey, meta: event.metaKey,
        alt: event.altKey, shift: event.shiftKey
      })
    } else if (functionalKeys.has(event.key)) {
      emit({ kind: 'key', key: event.key, target: describeTarget(target) })
    }
  }

  window.addEventListener('click', onClick, true)
  window.addEventListener('pointerdown', onPointer, true)
  window.addEventListener('pointerup', onPointer, true)
  window.addEventListener('keydown', onKey, true)

  return () => {
    active = false
    window.removeEventListener('click', onClick, true)
    window.removeEventListener('pointerdown', onPointer, true)
    window.removeEventListener('pointerup', onPointer, true)
    window.removeEventListener('keydown', onKey, true)
    for (const cancel of pending) {cancel()}
  }
}
