/**
 * BROW-C2C: original Hermes snapshot projection; no third-party source copied.
 * Reference implementation ONLY. Wire into Electron after H-079 and E2E gates.
 * Deltas are view projections, NEVER effect receipts or verification evidence.
 */
export interface SnapshotFrame {
  taskId: string
  tabId: string
  url: string
  revision: number
  text: string
  truncated?: boolean
}
export type SnapshotUpdate =
  | { kind: 'full'; next: SnapshotFrame; reason: string }
  | { kind: 'delta'; identity: Omit<SnapshotFrame, 'text' | 'truncated'>;
      baseRevision: number; commonPrefix: number; removedLines: number;
      insertedLines: string[]; commonSuffix: number }

/** Conservative: force FULL when freshness or identity cannot be proven. */
export function diffSnapshot(previous: SnapshotFrame | null, next: SnapshotFrame,
  minSavingRatio = 0.20): SnapshotUpdate {
  const full = (reason: string): SnapshotUpdate => ({ kind: 'full', next, reason })
  if (!previous) return full('missing_baseline')
  if (previous.truncated || next.truncated) return full('truncated')
  if (!next.taskId || !next.tabId || !next.url) return full('missing_identity')
  if (previous.taskId !== next.taskId || previous.tabId !== next.tabId ||
      previous.url !== next.url) return full('identity_or_navigation_changed')
  if (!Number.isSafeInteger(next.revision) ||
      next.revision <= previous.revision) return full('stale_revision')
  const before = previous.text.split('\n')
  const after = next.text.split('\n')
  let start = 0
  while (start < before.length && start < after.length &&
      before[start] === after[start]) start++
  let end = 0
  while (end < before.length - start && end < after.length - start &&
      before[before.length - 1 - end] === after[after.length - 1 - end]) end++
  const patch: SnapshotUpdate = {
    kind: 'delta',
    identity: { taskId: next.taskId, tabId: next.tabId,
      url: next.url, revision: next.revision },
    baseRevision: previous.revision,
    commonPrefix: start,
    removedLines: before.length - start - end,
    insertedLines: after.slice(start, after.length - end),
    commonSuffix: end
  }
  const patchBytes = Buffer.byteLength(JSON.stringify(patch), 'utf8')
  const fullBytes = Buffer.byteLength(next.text, 'utf8')
  if (fullBytes === 0 || patchBytes >= fullBytes * (1 - minSavingRatio))
    return full('insufficient_savings')
  return patch
}
export function applySnapshotDelta(previous: SnapshotFrame, update: SnapshotUpdate): SnapshotFrame {
  if (update.kind === 'full') return update.next
  const id = update.identity
  if (id.taskId !== previous.taskId || id.tabId !== previous.tabId ||
      id.url !== previous.url || update.baseRevision !== previous.revision ||
      id.revision <= previous.revision || previous.truncated)
    throw new Error('snapshot_delta_baseline_mismatch')
  const lines = previous.text.split('\n')
  const { commonPrefix: prefix, removedLines: removed, commonSuffix: suffix } = update
  if (![prefix, removed, suffix].every(n => Number.isSafeInteger(n) && n >= 0) ||
      prefix + removed + suffix !== lines.length)
    throw new Error('snapshot_delta_invalid_hunk')
  const text = [...lines.slice(0, prefix), ...update.insertedLines,
    ...(suffix ? lines.slice(lines.length - suffix) : [])].join('\n')
  return { ...id, text }
}
