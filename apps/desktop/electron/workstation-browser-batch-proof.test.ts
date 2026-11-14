import assert from 'node:assert/strict'
import { JSDOM } from 'jsdom'

import { describe, test } from 'vitest'

import { type BatchObservation, batchObservationScript, batchChatgptMessageWaitScript, batchLocalChangeWaitScript, hasVerifiedBatchEffect, shouldAwaitBatchLocalChange } from './workstation-browser-batch-proof'

const baseline: BatchObservation = {
  url: 'https://example.test/form',
  documentToken: 'same-renderer-doc',
  elementToken: 3,
  found: true,
  editable: true,
  value: '',
  checked: null,
  pressed: null,
  expanded: null,
  scrollY: 10
}

const verify = (step: any, after: Partial<BatchObservation>, before = baseline) =>
  hasVerifiedBatchEffect(step, before, { ...baseline, ...after })

describe('BROW-N1 authoritative post-action observation', () => {
  test('ACK without independent observation is never verification', () => {
    assert.equal(hasVerifiedBatchEffect({ kind: 'click', ref: '@e1' }, null, null).verified, false)
    assert.equal(verify({ kind: 'click', ref: '@e1' }, {}).verified, false)
  })
  test('typing is verified only when the target value matches readback', () => {
    assert.equal(verify({ kind: 'type', ref: '@e1', text: 'hello' }, { value: 'hello' }).verified, true)
    assert.equal(verify({ kind: 'type', ref: '@e1', text: 'hello' }, { value: '' }).verified, false)
    assert.equal(
      verify(
        { kind: 'type', ref: '@e1', text: 'world', append: true },
        { value: 'helloworld' },
        { ...baseline, value: 'hello' }
      ).verified,
      true
    )
    assert.equal(
      verify(
        { kind: 'type', ref: '@e1', text: 'world', append: true },
        { value: 'world' },
        { ...baseline, value: 'hello' }
      ).verified,
      false
    )
  })
  test('same URL is insufficient when document or DOM element changed', () => {
    assert.equal(
      verify({ kind: 'type', ref: '@e1', text: 'hello' }, { value: 'hello', documentToken: 'another-document' })
        .verified,
      false
    )
    assert.equal(
      verify({ kind: 'type', ref: '@e1', text: 'hello' }, { value: 'hello', elementToken: 4 }).verified,
      false
    )
    assert.equal(verify({ kind: 'type', ref: '@e1', text: 'hello' }, { value: 'hello', found: false }).verified, false)
    assert.equal(
      verify({ kind: 'type', ref: '@e1', text: 'hello' }, { value: 'hello', url: 'https://example.test/other' })
        .verified,
      false
    )
  })
  test('click only verifies observable target toggle postcondition', () => {
    assert.equal(
      verify({ kind: 'click', ref: '@e1' }, { checked: true }, { ...baseline, checked: false }).verified,
      true
    )
    assert.equal(
      verify({ kind: 'click', ref: '@e1' }, { pressed: 'true' }, { ...baseline, pressed: 'false' }).verified,
      true
    )
    assert.equal(
      verify({ kind: 'click', ref: '@e1' }, { expanded: 'true' }, { ...baseline, expanded: 'false' }).verified,
      true
    )
    assert.equal(
      verify({ kind: 'click', ref: '@e1' }, { checked: false }, { ...baseline, checked: false }).verified,
      false
    )
  })
  test('click focus of an editable composer is verifiable but does not verify a send', () => {
    assert.equal(verify({kind: 'click', ref: '@editor'}, {focused: true}, {...baseline, focused: false}).reason, 'editor_focus_readback')
    assert.equal(verify({kind: 'click', ref: '@send'}, {focused: true, editable: false}, {...baseline, editable: false, focused: false}).verified, false)
    assert.equal(verify({kind: 'click', ref: '@editor'}, {focused: true}, {...baseline, focused: true}).verified, false)
    assert.equal(verify({kind: 'click', ref: '@editor'}, {focused: true, elementToken: 4}, {...baseline, focused: false}).verified, false)
  })
  test('scroll requires directional visual movement, not wheel dispatch ACK', () => {
    assert.equal(verify({ kind: 'scroll', direction: 'down' }, { scrollY: 120 }).verified, true)
    assert.equal(verify({ kind: 'scroll', direction: 'up' }, { scrollY: 0 }).verified, true)
    assert.equal(verify({ kind: 'scroll', direction: 'down' }, { scrollY: 10 }).verified, false)
    assert.equal(verify({ kind: 'scroll', direction: 'up' }, { scrollY: 120 }).verified, false)
  })
  test('key dispatch is unverified without semantic postcondition', () => {
    assert.equal(verify({ kind: 'press', key: 'Enter' }, {}).verified, false)
  })
})

describe('BROW-N2 semantic local-only postconditions', () => {
  const unselected = { ...baseline, editable: false, selected: 'false', elementToken: 7 }
  test('click selects a stable target from semantic evidence', () => {
    const step = { kind: 'click', ref: '@chat', postcondition: { kind: 'selected' } } as const
    assert.equal(hasVerifiedBatchEffect(step, unselected, { ...unselected, selected: 'true' }).verified, true)
    assert.equal(hasVerifiedBatchEffect(step, unselected, { ...unselected, selected: 'true' }).reason, 'selection_readback')
    assert.equal(hasVerifiedBatchEffect(step, { ...unselected, selected: 'true' }, { ...unselected, selected: 'true' }).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, unselected, { ...unselected, elementToken: 8, selected: 'true' }).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, unselected, { ...unselected, documentToken: 'changed', selected: 'true' }).verified, false)
  })
  test('replaced selected target requires unique and unchanged semantic identity', () => {
    const step = {kind: 'click', ref: '@chat',
      anchor: {type: 'label', value: 'Conversation 42'}, postcondition: {kind: 'selected'}} as const
    const anchored = {unique: true, matchesRef: true, identity: 'Conversation 42',
      tag: 'div', role: 'option', selected: 'false'}
    const before = {...unselected, semanticSelection: anchored}
    const after = {...unselected, found: false, elementToken: null, selected: null,
      semanticSelection: {...anchored, matchesRef: false, selected: 'true'}}
    assert.equal(hasVerifiedBatchEffect(step, before, after).reason, 'semantic_selection_rebound_readback')
    assert.equal(hasVerifiedBatchEffect({...step, anchor: undefined}, before, after).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, {...before, semanticSelection: {...anchored, matchesRef: false}}, after).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, before, {...after, semanticSelection: {...after.semanticSelection, unique: false}}).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, before, {...after, semanticSelection: {...after.semanticSelection, identity: 'Other conversation'}}).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, before, {...after, semanticSelection: {...after.semanticSelection, selected: 'false'}}).verified, false)
    assert.equal(hasVerifiedBatchEffect(step, before, {...after, documentToken: 'other-doc'}).verified, false)
    assert.equal(hasVerifiedBatchEffect({kind: 'type', ref: '@chat', text: 'hello'}, before, after).verified, false)
  })
  test('generated readback observes a unique replacement without rebinding or mutating the DOM', () => {
    const dom = new JSDOM('<div role="option" aria-label="Conversation 42" aria-selected="false"></div>',
      {url: 'https://example.test/conversation', runScripts: 'outside-only'})
    try {
      const win = dom.window as any
      const old = win.document.querySelector('[role="option"]')
      win.__hermesWorkstationRefs = {byRef: new Map([['@chat', old]])}
      win.CSS = {escape: (value: string) => value}
      win.document.elementFromPoint = () => null
      const step = {kind: 'click', ref: '@chat', anchor: {type: 'label', value: 'Conversation 42'},
        postcondition: {kind: 'selected'}} as const
      const script = batchObservationScript('@chat', step.anchor)
      const before = win.eval(script) as BatchObservation
      assert.equal(before.semanticSelection?.unique, true)
      assert.equal(before.semanticSelection?.matchesRef, true)
      const replacement = old.cloneNode(true)
      replacement.setAttribute('aria-selected', 'true')
      old.replaceWith(replacement)
      const after = win.eval(script) as BatchObservation
      assert.equal(after.found, false)
      assert.equal(after.semanticSelection?.unique, true)
      assert.equal(after.semanticSelection?.matchesRef, false)
      assert.equal(hasVerifiedBatchEffect(step, before, after).verified, true)
      const duplicate = replacement.cloneNode(true)
      win.document.body.appendChild(duplicate)
      const ambiguous = win.eval(script) as BatchObservation
      assert.equal(ambiguous.semanticSelection?.unique, false)
      assert.equal(hasVerifiedBatchEffect(step, before, ambiguous).verified, false)
      assert.equal(win.__hermesWorkstationRefs.byRef.get('@chat'), old)
    } finally {
      dom.window.close()
    }
  })
  test('Enter can verify bound local selection but cannot acknowledge a send', () => {
    const step = { kind: 'press', key: 'Enter', ref: '@chat', postcondition: { kind: 'selected' } } as const
    assert.equal(hasVerifiedBatchEffect(step, { ...unselected, focused: true }, { ...unselected, focused: true, selected: 'true' }).verified, true)
    assert.equal(hasVerifiedBatchEffect(step, { ...unselected, focused: false }, { ...unselected, focused: false, selected: 'true' }).verified, false)
    assert.equal(hasVerifiedBatchEffect({ kind: 'press', key: 'Enter' }, { ...baseline, value: 'message' }, baseline).verified, false)
  })
  test('scroll recognizes a stable internal panel without moving the window', () => {
    const start = { ...baseline, scrollY: 0, scrollTop: 10, scrollContainerToken: 31 }
    const end = { ...start, scrollTop: 112 }
    assert.equal(hasVerifiedBatchEffect({ kind: 'scroll', direction: 'down' }, start, end).verified, true)
    assert.equal(hasVerifiedBatchEffect({ kind: 'scroll', direction: 'up' }, end, start).verified, true)
    assert.equal(hasVerifiedBatchEffect({ kind: 'scroll', direction: 'down' }, start, { ...end, scrollContainerToken: 32 }).verified, false)
    assert.equal(hasVerifiedBatchEffect({ kind: 'scroll', direction: 'down' }, start, { ...start }).verified, false)
  })
  test('generic DOM changes never verify a send or unchanged click', () => {
    assert.equal(hasVerifiedBatchEffect({ kind: 'click', ref: '@send' }, unselected, { ...unselected, selected: 'true' }).verified, false)
    assert.equal(hasVerifiedBatchEffect({ kind: 'click', ref: '@chat', postcondition: { kind: 'selected' } }, unselected, { ...unselected, selected: 'false' }).verified, false)
  })
})

test('P0 bounded watcher only waits when deterministic local proof is possible', () => {
  const stable = {...baseline, focused: false}
  assert.equal(shouldAwaitBatchLocalChange({kind:'type',ref:'@e1',text:'hi'},stable,stable),true)
  assert.equal(shouldAwaitBatchLocalChange({kind:'click',ref:'@send'},
    {...stable,editable:false,pressed:null,checked:null,expanded:null},
    {...stable,editable:false,pressed:null,checked:null,expanded:null}),false)
  assert.equal(shouldAwaitBatchLocalChange({kind:'click',ref:'@editor'},stable,stable),true)
  assert.equal(shouldAwaitBatchLocalChange({kind:'click',ref:'@e1',postcondition:{kind:'selected'}},stable,stable),true)
  assert.equal(shouldAwaitBatchLocalChange({kind:'press',key:'Enter'},stable,stable),false)
  assert.equal(shouldAwaitBatchLocalChange({kind:'type',ref:'@e1',text:'hi'},stable,{...stable,documentToken:'new'}),false)
  const script=batchLocalChangeWaitScript('@e1','type',90000)
  assert.match(script,/MutationObserver/)
  assert.match(script,/setTimeout\(\(\) => finish\(false\), 800\)/)
  assert.match(script,/observer\.disconnect\(\)/)
  assert.doesNotMatch(script,/__bindings|sendMessage|click\(/)
})

test('ChatGPT send requires a new user message with matching text, conversation and ID', () => {
  const conversationUrl = 'https://chatgpt.com/c/6ae6995b-62b0-83e9-987c-433222e77488'
  const text = 'Hermes autonomous send verification test'
  const step = {kind: 'click', ref: '@send', postcondition: {kind: 'chatgpt_message_recorded', conversationUrl, text}} as const
  const before = {...baseline, url: conversationUrl, chatgptComposerText: text,
    chatgptUserMessages: [{id: 'turn-old', text: 'Previous prompt'}]}
  const after = {...before, found: false, chatgptComposerText: '',
    chatgptUserMessages: [...before.chatgptUserMessages, {id:'turn-new', text}]}
  assert.equal(hasVerifiedBatchEffect(step, before, after).verified, true)
  assert.equal(hasVerifiedBatchEffect(step, before, {...after, chatgptUserMessages:before.chatgptUserMessages}).verified, false)
  assert.equal(hasVerifiedBatchEffect(step, before, {...after, chatgptUserMessages:[{id:'turn-new',text:'Different'}]}).verified, false)
  assert.equal(hasVerifiedBatchEffect(step, before, {...after,url:'https://chatgpt.com/c/another'}).verified, false)
  assert.equal(hasVerifiedBatchEffect(step, {...before,chatgptComposerText:'Different'}, after).verified, false)
  assert.equal(hasVerifiedBatchEffect(step, before, {...after,chatgptUserMessages:[{id:'turn-new',text},{id:'turn-other',text}]}).verified, false)
})

test('ChatGPT generated DOM readback and event waiter are valid JavaScript', () => {
  const url = 'https://chatgpt.com/c/6ae6995b-62b0-83e9-987c-433222e77488'
  assert.doesNotThrow(() => new Function('return ' + batchObservationScript('@e1')))
  assert.doesNotThrow(() => new Function('return ' +
    batchChatgptMessageWaitScript({conversationUrl: url, text: 'test'}, ['prior-id'])))
})
