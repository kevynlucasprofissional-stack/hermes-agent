import assert from 'node:assert/strict'

import { describe, test } from 'vitest'

import {
  applySnapshotDelta,
  diffSnapshot,
  type SnapshotFrame,
  type SnapshotUpdate
} from './workstation-browser-snapshot-diff'

const start: SnapshotFrame = {
  taskId: 't',
  tabId: 'tab',
  url: 'https://example.test/',
  revision: 1,
  text: ['header '.repeat(40), 'form old', 'footer '.repeat(40)].join('\n')
}

describe('OPT-04 Snapshot Delta Projection', () => {
  test('reconstructs snapshot delta losslessly', () => {
    const next = { ...start, revision: 2, text: start.text.replace('form old', 'form new') }
    const patch = diffSnapshot(start, next, 0)
    assert.equal(patch.kind, 'delta')
    assert.deepEqual(applySnapshotDelta(start, patch), next)
  })

  test('full snapshot on navigation, truncated output or absent base', () => {
    assert.equal(diffSnapshot(null, start).kind, 'full')
    assert.equal(
      diffSnapshot(start, { ...start, revision: 2, url: 'https://other.test/' }).kind,
      'full'
    )
    assert.equal(diffSnapshot(start, { ...start, revision: 2, truncated: true }).kind, 'full')
    assert.equal(diffSnapshot({ ...start, truncated: true }, { ...start, revision: 2 }).kind, 'full')
  })

  test('rejects replay on wrong baseline and stale revisions', () => {
    const patch = diffSnapshot(
      start,
      {
        ...start,
        revision: 2,
        text: start.text.replace('form old', 'form new')
      },
      0
    )

    assert.throws(() => applySnapshotDelta({ ...start, tabId: 'another' }, patch))
    assert.throws(() => applySnapshotDelta({ ...start, taskId: 'different-task' }, patch))
    assert.throws(() => applySnapshotDelta({ ...start, url: 'https://other.url/' }, patch))
    assert.equal(diffSnapshot(start, { ...start, revision: 1 }).kind, 'full')
  })

  test('handles large documents (thousands of lines) with localized delta', () => {
    const lines = Array.from({ length: 2000 }, (_, i) => `Line ${i}: information row content`)

    const previous: SnapshotFrame = {
      taskId: 'task-lg',
      tabId: 'tab-lg',
      url: 'https://large-doc.test/',
      revision: 10,
      text: lines.join('\n')
    }

    const modifiedLines = [...lines]
    modifiedLines[1000] = 'Line 1000: MODIFIED CONTENT ROW'
    modifiedLines[1001] = 'Line 1001: SECOND MODIFIED ROW'

    const next: SnapshotFrame = {
      taskId: 'task-lg',
      tabId: 'tab-lg',
      url: 'https://large-doc.test/',
      revision: 11,
      text: modifiedLines.join('\n')
    }

    const delta = diffSnapshot(previous, next, 0.1)
    assert.equal(delta.kind, 'delta')

    if (delta.kind === 'delta') {
      assert.equal(delta.commonPrefix, 1000)
      assert.equal(delta.removedLines, 2)
      assert.equal(delta.insertedLines.length, 2)
      assert.equal(delta.commonSuffix, 998)
    }

    const reconstructed = applySnapshotDelta(previous, delta)
    assert.equal(reconstructed.text, next.text)
    assert.deepEqual(reconstructed, next)
  })

  test('falls back to full update when savings are insufficient', () => {
    const tinyPrev: SnapshotFrame = {
      taskId: 't',
      tabId: 'tab',
      url: 'https://example.test/',
      revision: 1,
      text: 'short text'
    }

    const tinyNext: SnapshotFrame = {
      taskId: 't',
      tabId: 'tab',
      url: 'https://example.test/',
      revision: 2,
      text: 'short edit'
    }

    // Default minSavingRatio is 0.20 (20%)
    const res = diffSnapshot(tinyPrev, tinyNext, 0.5)
    assert.equal(res.kind, 'full')

    if (res.kind === 'full') {
      assert.equal(res.reason, 'insufficient_savings')
    }
  })

  test('throws error on corrupted or invalid delta hunks', () => {
    const corruptUpdate: SnapshotUpdate = {
      kind: 'delta',
      identity: {
        taskId: start.taskId,
        tabId: start.tabId,
        url: start.url,
        revision: 2
      },
      baseRevision: 1,
      commonPrefix: 0,
      removedLines: 9999, // impossible line count
      insertedLines: ['abc'],
      commonSuffix: 0
    }

    assert.throws(
      () => applySnapshotDelta(start, corruptUpdate),
      /snapshot_delta_invalid_hunk/
    )
  })

  test.each([
    [
      'long Unicode replacement',
      'café 東京 '.repeat(180) + '\nold\n' + '尾部 '.repeat(180),
      'café 大阪 '.repeat(180) + '\nnew\n' + '尾部 '.repeat(180),
      false
    ],
    [
      'insert and remove lines with terminal newline',
      'head '.repeat(180) + '\nremove\nkeep\n' + 'tail '.repeat(180),
      'head '.repeat(180) + '\ninsert-1\ninsert-2\nkeep\n' + 'tail '.repeat(180) + '\n',
      false
    ],
    ['truncated next frame forces a full update', 'before '.repeat(180), 'after '.repeat(180), true]
  ])('reconstructs exact structure for %s', (_label, before, after, truncated) => {
    const previous = { ...start, revision: 7, text: before as string }

    const next = {
      ...start,
      revision: 8,
      text: after as string,
      ...(truncated ? { truncated: true } : {})
    }

    const update = diffSnapshot(previous, next, 0)

    if (truncated) {assert.equal(update.kind, 'full')}
    assert.deepEqual(applySnapshotDelta(previous, update), next)
  })
})
