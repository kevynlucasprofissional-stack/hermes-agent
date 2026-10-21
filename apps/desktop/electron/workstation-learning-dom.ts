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

export function buildLearningObserverScript(): string {
  return `(() => {
    if (window.__hermesLearningActive) return;
    window.__hermesLearningActive = true;

    const SENSITIVE = /password|passcode|secret|token|key|credential|authorization|cookie|otp|recovery|private|account|session|api|payment|card|email|address/i;
    const SAFE_INPUT_TYPES = new Set(['range', 'number', 'checkbox', 'radio', 'button']);
    const BREADCRUMB_SELECTOR = '[role="toolbar"], [role="navigation"], [role="dialog"], [role="tabpanel"], aside, [id*="panel"], [id*="sidebar"], [class*="panel"], [class*="layer"], [class*="prop"]';

    function isSens(el) {
      if (!el) return false;
      if (el.isContentEditable || el.getAttribute?.('contenteditable') === 'true' || el.getAttribute?.('contenteditable') === '' || el.tagName === 'TEXTAREA') return true;
      if (el.tagName === 'INPUT') {
        const type = (el.type || 'text').toLowerCase();
        if (!SAFE_INPUT_TYPES.has(type)) return true;
      }
      const name = el.getAttribute?.('aria-label') || el.getAttribute?.('title') || '';
      return SENSITIVE.test(name);
    }

    function extractBreadcrumb(el) {
      if (!el) return undefined;
      const c = el.closest?.(BREADCRUMB_SELECTOR);
      if (!c) return undefined;
      const explicit = c.getAttribute?.('aria-label') || c.getAttribute?.('title') || c.getAttribute?.('data-panel-title') || c.getAttribute?.('data-panel');
      if (explicit && SENSITIVE.test(explicit)) return undefined;
      const idClass = (c.id + ' ' + c.className).toLowerCase();
      if (SENSITIVE.test(idClass)) return undefined;
      if (explicit && explicit.trim()) return explicit.slice(0, 80);
      const h = c.querySelector?.('h1, h2, h3, h4, [class*="title"], [class*="header"], legend');
      if (h && h.textContent) {
        if (SENSITIVE.test(h.textContent)) return undefined;
        return h.textContent.trim().slice(0, 80);
      }
      if (/layer|camada/i.test(idClass)) return 'Painel de Camadas';
      if (/filter|filtro/i.test(idClass)) return 'Painel de Filtros';
      if (/prop|ajuste/i.test(idClass)) return 'Painel de Propriedades';
      if (/tool|toolbar/i.test(idClass)) return 'Barra de Ferramentas';
      if (/sidebar/i.test(idClass)) return 'Barra Lateral';
      const role = c.getAttribute?.('role')?.toLowerCase();
      if (role === 'dialog' || c.tagName === 'DIALOG') return 'Janela de Diálogo';
      if (role === 'toolbar') return 'Barra de Ferramentas';
      return undefined;
    }

    function extractValue(el) {
      if (!el || isSens(el)) return {};
      let val = el.getAttribute?.('aria-valuetext') || el.getAttribute?.('aria-valuenow');
      if (!val && el.tagName === 'INPUT' && (el.type === 'range' || el.type === 'number')) {
        val = el.value;
      } else if (!val && el.tagName === 'SELECT') {
        val = el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex].text : el.value;
      }
      if (!val || SENSITIVE.test(val)) return {};
      val = String(val).trim();
      const m = val.match(/(%|px|pt|em|rem|deg|s|ms)$/i);
      return { currentValue: val.slice(0, 50), unit: m ? m[1] : undefined };
    }

    function detectDelta(mutations) {
      let modal = false;
      let added = false;
      let removed = false;
      let toggled = false;
      let toggledAttr = '';
      for (const m of mutations) {
        if (m.type === 'childList') {
          for (const n of m.addedNodes) {
            if (n && n.nodeType === 1) {
              if (n.matches?.('dialog, [role="dialog"], [class*="modal"]') || n.querySelector?.('dialog, [role="dialog"]')) {
                modal = true; break;
              }
              if (n.matches?.('[role="listitem"], [class*="layer"], li') || n.querySelector?.('[class*="layer"]')) added = true;
            }
          }
          for (const n of m.removedNodes) {
            if (n && n.nodeType === 1) {
              if (n.matches?.('[role="listitem"], [class*="layer"], li')) removed = true;
            }
          }
        } else if (m.type === 'attributes') {
          if (['class', 'aria-expanded', 'aria-selected', 'hidden', 'disabled'].includes(m.attributeName)) {
            toggled = true; toggledAttr = m.attributeName;
          }
        }
      }
      if (modal) return { effectKind: 'modal_opened', summary: 'Diálogo ou modal aberto após a ação' };
      if (added) return { effectKind: 'item_added', summary: 'Novo item ou camada adicionado à interface' };
      if (removed) return { effectKind: 'item_removed', summary: 'Item ou camada removido da interface' };
      if (toggled) return { effectKind: 'state_toggled', summary: 'Alternância de estado (' + toggledAttr + ')' };
      return { effectKind: 'none' };
    }

    function observePostAction(cb) {
      if (typeof MutationObserver === 'undefined') { cb({ effectKind: 'none' }); return; }
      const records = [];
      const obs = new MutationObserver(m => records.push(...m));
      try {
        obs.observe(document.body || document.documentElement, {
          childList: true, subtree: true, attributes: true,
          attributeFilter: ['class', 'aria-expanded', 'aria-selected', 'hidden', 'disabled']
        });
      } catch (_) { cb({ effectKind: 'none' }); return; }
      setTimeout(() => {
        try { records.push(...obs.takeRecords()); obs.disconnect(); } catch (_) {}
        cb(detectDelta(records));
      }, 250);
    }

    window.addEventListener('click', (e) => {
      if (!window.__hermesLearningActive || isSens(e.target)) return;
      const target = e.target;
      const interactive = target.closest?.('button, a, [role], [data-tool], [data-action], canvas, input, select') || target;
      const role = interactive.getAttribute?.('role') || (interactive.tagName === 'BUTTON' ? 'button' : (interactive.tagName === 'A' ? 'link' : (interactive.tagName === 'CANVAS' ? 'canvas' : (interactive.tagName === 'INPUT' && interactive.type === 'range' ? 'slider' : ''))));
      const name = interactive.getAttribute?.('aria-label') || interactive.getAttribute?.('title') || interactive.getAttribute?.('data-tool') || (interactive.tagName === 'BUTTON' ? (interactive.innerText || '').slice(0, 80) : '');
      const breadcrumb = extractBreadcrumb(interactive);
      const valObj = extractValue(interactive);

      observePostAction((delta) => {
        console.debug('__HERMES_GESTURE__' + JSON.stringify({
          kind: 'click',
          x: e.clientX,
          y: e.clientY,
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
          role: role || undefined,
          accessibleName: name || undefined,
          elementTag: interactive.tagName?.toLowerCase(),
          containerBreadcrumb: breadcrumb,
          currentValue: valObj.currentValue,
          unit: valObj.unit,
          domDelta: delta
        }));
      });
    }, true);

    function extractTargetInfo(el) {
      if (!el || !el.tagName) return undefined;
      const interactive = el.closest?.('button, a, [role], [data-tool], [data-action], canvas, input, select') || el;
      const role = interactive.getAttribute?.('role') || (interactive.tagName === 'BUTTON' ? 'button' : (interactive.tagName === 'A' ? 'link' : (interactive.tagName === 'CANVAS' ? 'canvas' : (interactive.tagName === 'INPUT' && interactive.type === 'range' ? 'slider' : ''))));
      const name = interactive.getAttribute?.('aria-label') || interactive.getAttribute?.('title') || interactive.getAttribute?.('data-tool') || (interactive.tagName === 'BUTTON' ? (interactive.innerText || '').slice(0, 80) : '');
      const tag = interactive.tagName?.toLowerCase();
      const breadcrumb = extractBreadcrumb(interactive);
      if (!role && !name && !breadcrumb && tag !== 'canvas') return undefined;
      return {
        tag: tag,
        role: role || undefined,
        accessibleName: name || undefined,
        containerBreadcrumb: breadcrumb
      };
    }

    window.addEventListener('pointerdown', (e) => {
      if (!window.__hermesLearningActive || isSens(e.target)) return;
      const target = extractTargetInfo(e.target);
      console.debug('__HERMES_GESTURE__' + JSON.stringify({
        kind: 'pointerdown',
        x: e.clientX,
        y: e.clientY,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        target: target
      }));
    }, true);

    window.addEventListener('pointerup', (e) => {
      if (!window.__hermesLearningActive || isSens(e.target)) return;
      const target = extractTargetInfo(e.target);
      console.debug('__HERMES_GESTURE__' + JSON.stringify({
        kind: 'pointerup',
        x: e.clientX,
        y: e.clientY,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        target: target
      }));
    }, true);

    window.addEventListener('keydown', (e) => {
      if (!window.__hermesLearningActive || isSens(e.target)) return;
      const hasMod = e.ctrlKey || e.metaKey || e.altKey;
      const functionalKeys = ['Enter', 'Escape', 'Tab', 'Backspace', 'Delete', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
      const isFunctional = functionalKeys.includes(e.key);
      if (!hasMod && !isFunctional) return;
      if (hasMod) {
        observePostAction((delta) => {
          console.debug('__HERMES_GESTURE__' + JSON.stringify({
            kind: 'shortcut',
            key: e.key,
            ctrl: e.ctrlKey,
            meta: e.metaKey,
            alt: e.altKey,
            shift: e.shiftKey,
            domDelta: delta
          }));
        });
      } else {
        const target = extractTargetInfo(e.target);
        console.debug('__HERMES_GESTURE__' + JSON.stringify({
          kind: 'key',
          key: e.key,
          target: target
        }));
      }
    }, true);
  })();`
}
