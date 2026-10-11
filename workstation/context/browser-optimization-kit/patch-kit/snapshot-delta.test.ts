import assert from 'node:assert/strict'
import { test } from 'vitest'
import { applySnapshotDelta, diffSnapshot, type SnapshotFrame } from './snapshot-delta'

const start: SnapshotFrame = {
  taskId: 't', tabId: 'tab', url: 'https://example.test/', revision: 1,
  text: ['header '.repeat(40), 'form old', 'footer '.repeat(40)].join('\n')
}

test('reconstructs snapshot delta losslessly', () => {
  const next = { ...start, revision: 2, text: start.text.replace('form old', 'form new') }
  const patch = diffSnapshot(start, next, 0)
  assert.equal(patch.kind, 'delta')
  assert.deepEqual(applySnapshotDelta(start, patch), next)
})

test('full snapshot on navigation, truncated output or absent base', () => {
  assert.equal(diffSnapshot(null, start).kind, 'full')
  assert.equal(diffSnapshot(start, { ...start, revision: 2, url: 'https://other.test/' }).kind, 'full')
  assert.equal(diffSnapshot(start, { ...start, revision: 2, truncated: true }).kind, 'full')
})

test('rejects replay on wrong baseline and stale revisions', () => {
  const patch = diffSnapshot(start, { ...start, revision: 2,
    text: start.text.replace('form old', 'form new') }, 0)
  assert.throws(() => applySnapshotDelta({ ...start, tabId: 'another' }, patch))
  assert.equal(diffSnapshot(start, { ...start, revision: 1 }).kind, 'full')
})
