import { expect, test } from 'vitest'

import { directToolCallTurn } from './mock-server.ts'

test('a prior tool result does not consume the next scripted E2E call', () => {
  const userText = 'E2E_CALL(work_execute)[{"operation_key":"cards","items":[],"steps":[]}]'

  const result = directToolCallTurn(userText, [
    { role: 'user', content: 'E2E_CALL(browser_navigate)[{"url":"http://127.0.0.1/cards"}]' },
    { role: 'assistant', tool_calls: [{ id: 'call-nav', function: { name: 'browser_navigate' } }] },
    { role: 'tool', tool_call_id: 'call-nav', content: 'NAV_RESULT' },
    { role: 'assistant', content: 'E2E_CALL_RESULT: NAV_RESULT' },
    { role: 'user', content: userText },
  ])

  expect(result).toMatchObject({ text: '', toolCalls: [{ name: 'work_execute' }] })
})

test('a result from the current turn becomes the scripted result reply', () => {
  const userText = 'E2E_CALL(browser_navigate)[{"url":"http://127.0.0.1/cards"}]'

  const result = directToolCallTurn(userText, [
    { role: 'user', content: userText },
    { role: 'assistant', tool_calls: [{ id: 'call-nav', function: { name: 'browser_navigate' } }] },
    { role: 'tool', tool_call_id: 'call-nav', content: 'NAV_RESULT' },
  ])

  expect(result?.text).toBe('E2E_CALL_RESULT: NAV_RESULT')
})

test('balanced brackets extract the exact call even with surrounding text and brackets', () => {
  const userText = '[Interrupted context {extra}] E2E_CALL(work_execute)[{"operation_key":"cards","items":[{"id":1}],"steps":[]}] trailing {more}'
  const result = directToolCallTurn(userText, [{ role: 'user', content: userText }])
  expect(result).toMatchObject({
    text: '',
    toolCalls: [{ name: 'work_execute', args: { operation_key: 'cards', items: [{ id: 1 }], steps: [] } }]
  })
})

test('durable handoff in userText completes the turn without re-issuing tool calls', () => {
  const userText = 'E2E_CALL(work_execute)[{"operation_key":"cards"}]\n\n[DURABLE HANDOFF — STATE ONLY]\n{"task_id":"t-42","plan_id":"p-42","items":{"completed":3,"total":3,"needs_reasoning":0}}'
  const result = directToolCallTurn(userText, [{ role: 'user', content: userText }])
  expect(result?.toolCalls).toBeUndefined()
  expect(result?.text).toContain('E2E_CALL_RESULT:')
  expect(result?.text).toContain('"status":"completed"')
  expect(result?.text).toContain('"task_id":"t-42"')
})

