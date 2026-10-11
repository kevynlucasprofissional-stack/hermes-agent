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

test.each([
  ['long Unicode replacement', 'café 東京 '.repeat(180) + '\nold\n' + '尾部 '.repeat(180),
    'café 大阪 '.repeat(180) + '\nnew\n' + '尾部 '.repeat(180), false],
  ['insert and remove lines with terminal newline', 'head '.repeat(180) + '\nremove\nkeep\n' + 'tail '.repeat(180),
    'head '.repeat(180) + '\ninsert-1\ninsert-2\nkeep\n' + 'tail '.repeat(180) + '\n', false],
  ['truncated next frame forces a full update', 'before '.repeat(180),
    'after '.repeat(180), true]
])('reconstructs exact structure for %s', (_label, before, after, truncated) => {
  const previous = { ...start, revision: 7, text: before as string }
  const next = { ...start, revision: 8, text: after as string,
    ...(truncated ? { truncated: true } : {}) }
  const update = diffSnapshot(previous, next, 0)
  if (truncated) assert.equal(update.kind, 'full')
  assert.deepEqual(applySnapshotDelta(previous, update), next)
})
