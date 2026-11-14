import type { BrowserBatchStep } from './workstation-browser-batch'

/**
 * Ephemeral, renderer-local readback. This is evidence for a step, never a
 * second execution, admission or receipt owner. Values must not be logged.
 */
export interface BatchObservation {
  url: string
  documentToken: string
  elementToken: number | null
  found: boolean
  editable: boolean
  value: string | null
  checked: boolean | null
  pressed: string | null
  expanded: string | null
  /** Unique, read-only DOM evidence for an explicit stable anchor. Never persisted. */
  semanticSelection?: {
    unique: boolean
    matchesRef: boolean
    identity: string | null
    tag: string | null
    role: string | null
    selected: string | null
  } | null
  selected?: string | null
  focused?: boolean
  scrollTop?: number | null
  scrollContainerToken?: number | null
  scrollY: number
  /** Ephemeral ChatGPT DOM evidence; never persist raw message text in receipts. */
  chatgptComposerText?: string | null
  chatgptComposerTarget?: boolean
  chatgptSendTarget?: boolean
  chatgptUserMessages?: Array<{ id: string; text: string }>
}

export function batchObservationScript(
  ref: string | null,
  anchor?: {type?: string; value?: string}
): string {
  // Generic roles and implicit anchor guesses are not stable identities.
  const stableAnchor = anchor && ['testid', 'name', 'label'].includes(anchor.type ?? '') &&
    typeof anchor.value === 'string' && anchor.value.trim().length > 0 ? anchor : null
  return `(function () {
    // __HERMES_BATCH_READBACK_V1__
    var state = window.__hermesWorkstationRefs;
    var el = state && state.byRef && state.byRef.get(${JSON.stringify(ref)});
    var found = !!(el && el.isConnected);
    var anchor = ${JSON.stringify(stableAnchor)};
    var semanticSelection = null;
    if (anchor) {
      try {
        var escaped = CSS.escape(anchor.value);
        var selector = anchor.type === 'testid'
          ? '[data-testid="' + escaped + '"], [data-test="' + escaped + '"], [data-qa="' + escaped + '"]'
          : anchor.type === 'name' ? '[name="' + escaped + '"]'
          : '[aria-label="' + escaped + '"]';
        var matches = document.querySelectorAll(selector);
        var candidate = matches.length === 1 ? matches[0] : null;
        var identity = candidate && String(candidate.getAttribute('aria-label') || candidate.getAttribute('name') || '').trim();
        semanticSelection = {
          unique: matches.length === 1,
          matchesRef: !!(candidate && found && candidate === el),
          identity: identity || null,
          tag: candidate ? candidate.tagName.toLowerCase() : null,
          role: candidate ? String(candidate.getAttribute('role') || '') : null,
          selected: candidate ? candidate.getAttribute('aria-selected') : null
        };
      } catch (err) { /* Invalid/unsupported anchors stay unverified. */ }
    }
    var token = null;
    if (found && state) {
      if (!state.batchIdentityByElement) state.batchIdentityByElement = new WeakMap();
      if (!state.batchIdentityByElement.has(el)) {
        state.batchElementCounter = (state.batchElementCounter || 0) + 1;
        state.batchIdentityByElement.set(el, state.batchElementCounter);
      }
      token = state.batchIdentityByElement.get(el);
    }
    var scrollElement = document.elementFromPoint(Math.round(window.innerWidth / 2), Math.round(window.innerHeight / 2));
    while (scrollElement && !(scrollElement.scrollHeight > scrollElement.clientHeight + 1 &&
      /^(auto|scroll)$/.test(getComputedStyle(scrollElement).overflowY))) {
      scrollElement = scrollElement.parentElement;
    }
    var scrollToken = null;
    if (scrollElement && state) {
      if (!state.batchScrollIdentityByElement) state.batchScrollIdentityByElement = new WeakMap();
      if (!state.batchScrollIdentityByElement.has(scrollElement)) {
        state.batchScrollCounter = (state.batchScrollCounter || 0) + 1;
        state.batchScrollIdentityByElement.set(scrollElement, state.batchScrollCounter);
      }
      scrollToken = state.batchScrollIdentityByElement.get(scrollElement);
    }
    var tag = found ? String(el.tagName || '').toLowerCase() : '';
    var editable = found && (tag === 'input' || tag === 'textarea' || !!el.isContentEditable);
    var value = editable ? ('value' in el ? String(el.value) : String(el.textContent || '')) : null;
    // ChatGPT-only conversation readback. A new user-message ID, not the
    // disappearance of editor text, is required to prove an outbound submit.
    var chatgpt = location.origin === 'https://chatgpt.com' && /^\\/c\\/[a-z0-9-]{20,80}$/.test(location.pathname);
    var composer = chatgpt ? document.querySelector('#prompt-textarea, [role="textbox"][contenteditable="true"]') : null;
    var submitLabel = found ? String(el.getAttribute('aria-label') || '').toLowerCase() : '';
    var submitTestId = found ? String(el.getAttribute('data-testid') || '') : '';
    var sendTarget = chatgpt && found && String(el.tagName).toLowerCase() === 'button' && !el.disabled &&
      (submitTestId === 'send-button' || submitTestId === 'composer-submit-button' ||
       submitTestId === 'composer-send-button' || submitLabel.indexOf('send') >= 0 ||
       submitLabel.indexOf('enviar') >= 0);
    var messages = chatgpt ? Array.from(document.querySelectorAll('[data-message-author-role="user"]')).slice(-30).map(function (item) {
      var container = item.closest('[data-message-id]') || item.closest('[data-testid^="conversation-turn-"]');
      var id = item.getAttribute('data-message-id') || (container && (container.getAttribute('data-message-id') || container.getAttribute('data-testid')));
      var content = item.querySelector('.whitespace-pre-wrap') || item;
      return {id: String(id || ''), text: String(content.innerText || content.textContent || '').trim().replace(/\\r\\n/g, '\\n')};
    }).filter(function (item) {return item.id.length > 0;}) : [];
    // New ChatGPT UI: user turns have semantic role headings and a scoped turn key,
    // not data-message-author-role. Never use sidebar text or unnamed messages.
    if (chatgpt && messages.length === 0) {
      messages = Array.from(document.querySelectorAll('h4[data-conversation-role="user"]')).slice(-30).map(function (heading) {
        var turn = heading.closest('[data-content-search-turn-key]');
        var root = heading.parentElement;
        var body = root && root.children[1];
        var content = body && (body.querySelector('.whitespace-pre-wrap') || body);
        var id = turn && turn.getAttribute('data-content-search-turn-key');
        return {id: String(id || ''), text: String(content && (content.innerText || content.textContent) || '').trim().replace(/\\r\\n/g, '\\n')};
      }).filter(function (item) {return item.id.length > 0;});
    }
    return {
      url: location.href,
      documentToken: String(performance.timeOrigin),
      elementToken: typeof token === 'number' ? token : null,
      found: found,
      editable: !!editable,
      value: value,
      checked: found && typeof el.checked === 'boolean' ? el.checked : null,
      pressed: found ? el.getAttribute('aria-pressed') : null,
      expanded: found ? el.getAttribute('aria-expanded') : null,
      semanticSelection: semanticSelection,
      selected: found ? el.getAttribute('aria-selected') : null,
      focused: found && document.activeElement === el,
      scrollTop: scrollElement ? scrollElement.scrollTop : null,
      scrollContainerToken: typeof scrollToken === 'number' ? scrollToken : null,
      scrollY: window.scrollY,
      chatgptComposerText: composer ? String(composer.innerText || composer.textContent || '').trim().replace(/\\r\\n/g, '\\n') : null,
      chatgptComposerTarget: !!(chatgpt && found && el === composer),
      chatgptSendTarget: !!sendTarget,
      chatgptUserMessages: messages
    };
  })()`
}

export function hasVerifiedBatchEffect(
  step: BrowserBatchStep,
  before: BatchObservation | null,
  after: BatchObservation | null
): { verified: boolean; reason: string } {
  const uncertain = (reason: string) => ({ verified: false, reason })

  if (!before || !after) {return uncertain('readback_unavailable')}

  if (
    !before.url ||
    before.url !== after.url ||
    !before.documentToken ||
    before.documentToken !== after.documentToken
  ) {
    return uncertain('document_changed')
  }

  if ((step.kind === 'click' || step.kind === 'press') &&
      step.postcondition?.kind === 'chatgpt_message_recorded') {
    const expected = step.postcondition
    if (before.url !== expected.conversationUrl || after.url !== expected.conversationUrl ||
        before.chatgptComposerText !== expected.text.trim().replace(/\r\n/g, '\n') ||
        !before.chatgptUserMessages || !after.chatgptUserMessages) {
      return uncertain('chatgpt_message_precondition_or_readback_invalid')
    }
    const idsBefore = new Set(before.chatgptUserMessages.map(message => message.id))
    const newMatches = after.chatgptUserMessages.filter(message =>
      message.id && !idsBefore.has(message.id) && message.text === expected.text.trim().replace(/\r\n/g, '\n'))
    return newMatches.length === 1
      ? {verified: true, reason: 'chatgpt_user_message_dom_readback'}
      : uncertain('chatgpt_new_user_message_not_observed')
  }

  if (step.kind === 'scroll') {
    if (!Number.isFinite(before.scrollY) || !Number.isFinite(after.scrollY)) {return uncertain('scroll_not_observable')}
    const delta = after.scrollY - before.scrollY

    if (delta * (step.direction === 'down' ? 1 : -1) > 0) {
      return { verified: true, reason: 'scroll_readback' }
    }
    if (before.scrollContainerToken !== null && before.scrollContainerToken !== undefined &&
        before.scrollContainerToken === after.scrollContainerToken &&
        before.scrollTop !== null && before.scrollTop !== undefined &&
        after.scrollTop !== null && after.scrollTop !== undefined &&
        Number.isFinite(before.scrollTop) && Number.isFinite(after.scrollTop) &&
        (after.scrollTop - before.scrollTop) * (step.direction === 'down' ? 1 : -1) > 0) {
      return { verified: true, reason: 'panel_scroll_readback' }
    }
    return uncertain('scroll_effect_not_observed')
  }

  if (!before.found || !after.found || before.elementToken === null || before.elementToken !== after.elementToken) {
    // Only a local selection may survive a DOM re-render. A unique, explicit
    // anchor must identify the original target BEFORE dispatch and the same
    // semantic target AFTER it. Never infer a send, type, or arbitrary click.
    const previous = before.semanticSelection
    const current = after.semanticSelection
    if (step.kind === 'click' && step.postcondition?.kind === 'selected' &&
        step.anchor && ['testid', 'name', 'label'].includes(step.anchor.type ?? '') &&
        typeof step.anchor.value === 'string' && step.anchor.value.trim().length > 0 &&
        previous?.unique === true && previous.matchesRef === true &&
        previous.selected === 'false' && previous.identity &&
        current?.unique === true && current.selected === 'true' &&
        current.identity === previous.identity && current.tag === previous.tag &&
        current.role === previous.role) {
      return {verified: true, reason: 'semantic_selection_rebound_readback'}
    }
    return uncertain('stale_or_replaced_target')
  }

  if (step.kind === 'type') {
    if (!before.editable || !after.editable || before.value === null || after.value === null) {
      return uncertain('input_readback_unavailable')
    }

    const append = step.append === true || step.clear === false
    const expected = append ? before.value + step.text : step.text

    return after.value === expected
      ? { verified: true, reason: 'input_value_readback' }
      : uncertain('input_value_mismatch')
  }

  if ((step.kind === 'click' || step.kind === 'press') && step.postcondition?.kind === 'selected') {
    if (step.kind === 'press' && (step.ref === undefined || before.focused !== true)) {
      return uncertain('key_target_not_focused')
    }
    return before.selected !== 'true' && after.selected === 'true'
      ? { verified: true, reason: 'selection_readback' }
      : uncertain('selection_postcondition_not_observed')
  }

  if (step.kind === 'click') {
    const toggled =
      (before.checked !== null && after.checked !== null && before.checked !== after.checked) ||
      (before.pressed !== null && after.pressed !== null && before.pressed !== after.pressed) ||
      (before.expanded !== null && after.expanded !== null && before.expanded !== after.expanded)

    // A click that only focuses an editable composer is a local, independently
    // observable effect. This never proves that a subsequent message was sent.
    const focusedEditor = before.focused !== true && after.focused === true && after.editable === true
    if (focusedEditor) {return { verified: true, reason: 'editor_focus_readback' }}
    return toggled ? { verified: true, reason: 'toggle_readback' } : uncertain('click_postcondition_not_observed')
  }

  // A key dispatch is not proof that the website consumed the key.
  return uncertain('key_postcondition_not_observed')
}

/** A bounded event wait is worthwhile only when a local effect can be proven.
 * Never wait for arbitrary clicks that might have sent a remote message. */
export function shouldAwaitBatchLocalChange(
  step: BrowserBatchStep,
  before: BatchObservation | null,
  after: BatchObservation | null
): boolean {
  if (!before || !after || !before.found || !after.found ||
      before.url !== after.url || before.documentToken !== after.documentToken ||
      before.elementToken === null || before.elementToken !== after.elementToken) {return false}
  if (step.kind === 'type') {return before.editable && after.editable}
  if (step.kind === 'scroll') {return true}
  if (step.postcondition?.kind === 'selected') {return true}
  if (step.kind === 'press') {return false}
  return before.editable || before.checked !== null || before.pressed !== null || before.expanded !== null
}

/** Uses local DOM events instead of asking the LLM to poll. Only emits a wake
 * signal; independent before/after proof and owner validation remain mandatory.
 * The deadline is enforced in the page, and also by the main-process caller. */
export function batchLocalChangeWaitScript(ref: string | null, kind: BrowserBatchStep['kind'], timeoutMs = 450): string {
  const duration = Math.min(800, Math.max(50, Math.trunc(timeoutMs)))
  return `new Promise(resolve => {
    // __HERMES_BATCH_EVENT_WAIT_V1__
    const state = window.__hermesWorkstationRefs;
    const el = state && state.byRef && state.byRef.get(${JSON.stringify(ref)});
    if (!el || !el.isConnected) {resolve(false); return;}
    const kind = ${JSON.stringify(kind)};
    let done = false;
    let timer;
    let observer;
    const finish = changed => {
      if (done) return;
      done = true;
      if (observer) observer.disconnect();
      clearTimeout(timer);
      el.removeEventListener('input', onEvent);
      el.removeEventListener('change', onEvent);
      document.removeEventListener('focusin', onFocus, true);
      document.removeEventListener('scroll', onScroll, true);
      resolve(changed);
    };
    const onEvent = () => finish(true);
    const onFocus = event => {if (event.target === el) finish(true);};
    const onScroll = () => {if (kind === 'scroll') finish(true);};
    timer = setTimeout(() => finish(false), ${duration});
    if (kind === 'scroll') {
      document.addEventListener('scroll', onScroll, true);
    } else {
      observer = new MutationObserver(() => finish(true));
      observer.observe(el, {attributes: true, childList: kind === 'type',
        characterData: kind === 'type', subtree: kind === 'type',
        attributeFilter: kind === 'type' ? undefined :
          ['aria-pressed', 'aria-expanded', 'aria-selected', 'checked']});
      el.addEventListener('input', onEvent);
      el.addEventListener('change', onEvent);
      document.addEventListener('focusin', onFocus, true);
    }
  })`
}
/** Bounded deterministic wait for a NEW user message in one ChatGPT conversation.
 * An event only wakes the reader; it never becomes an external delivery receipt. */
export function batchChatgptMessageWaitScript(
  expected: {conversationUrl: string; text: string}, seenIds: string[], timeoutMs = 8_000
): string {
  const deadline = Math.min(12_000, Math.max(100, Math.trunc(timeoutMs)))
  return `new Promise(resolve => {
    // __HERMES_CHATGPT_OUTBOUND_WAIT_V1__
    const target = ${JSON.stringify(expected)};
    const seen = new Set(${JSON.stringify(seenIds)});
    let finished = false;
    let timer;
    let observer;
    function check() {
      if (location.href !== target.conversationUrl) return false;
      return Array.from(document.querySelectorAll('[data-message-author-role="user"]')).some(item => {
        const container = item.closest('[data-message-id]') || item.closest('[data-testid^="conversation-turn-"]');
        const id = item.getAttribute('data-message-id') || (container && (container.getAttribute('data-message-id') || container.getAttribute('data-testid')));
        const content = item.querySelector('.whitespace-pre-wrap') || item;
        const text = String(content.innerText || content.textContent || '').trim().replace(/\\r\\n/g, '\\n');
        return id && !seen.has(id) && text === target.text.trim().replace(/\\r\\n/g, '\\n');
      }) || Array.from(document.querySelectorAll('h4[data-conversation-role="user"]')).some(heading => {
        const turn = heading.closest('[data-content-search-turn-key]');
        const id = turn && turn.getAttribute('data-content-search-turn-key');
        const root = heading.parentElement;
        const body = root && root.children[1];
        const content = body && (body.querySelector('.whitespace-pre-wrap') || body);
        const text = String(content && (content.innerText || content.textContent) || '').trim().replace(/\\r\\n/g, '\\n');
        return id && !seen.has(id) && text === target.text.trim().replace(/\\r\\n/g, '\\n');
      });
    }
    function finish(observed) {
      if (finished) return;
      finished = true;
      if (observer) observer.disconnect();
      clearTimeout(timer);
      resolve(observed);
    }
    if (check()) {finish(true); return;}
    timer = setTimeout(() => finish(false), ${deadline});
    observer = new MutationObserver(() => {if (check()) finish(true);});
    observer.observe(document.body, {subtree: true, childList: true, characterData: true});
  })`
}
