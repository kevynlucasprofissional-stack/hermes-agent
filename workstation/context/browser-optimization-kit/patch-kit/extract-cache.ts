/**
 * Original optional bounded in-memory cache for READ-only structured extraction.
 * A verified documentFingerprint from the browser owner is mandatory; TTL alone
 * does not establish SPA freshness. Never persist credentials or cookies.
 */
export interface ExtractScope {
  profileId: string
  taskId: string
  tabId: string
  url: string
  documentEpoch: string
  mutationRevision: number
  documentFingerprint: string
  queryDigest: string
}
export class BoundedExtractCache<T> {
  private data = new Map<string, { until: number; value: T }>()
  constructor(private readonly maxEntries = 64, private readonly ttlMs = 4_000) {}
  private key(s: ExtractScope): string {
    if (!s.profileId || !s.taskId || !s.tabId || !s.url ||
        !s.documentEpoch || !s.documentFingerprint || !s.queryDigest ||
        !Number.isSafeInteger(s.mutationRevision) || s.mutationRevision < 0)
      throw Error('extract_fingerprint_required')
    return JSON.stringify([s.profileId, s.taskId, s.tabId, s.url,
      s.documentEpoch, s.mutationRevision, s.documentFingerprint, s.queryDigest])
  }
  get(scope: ExtractScope): T | null {
    const key = this.key(scope)
    const record = this.data.get(key)
    if (!record) return null
    if (record.until < Date.now()) { this.data.delete(key); return null }
    return record.value
  }
  set(scope: ExtractScope, value: T): void {
    const key = this.key(scope)
    // Cache must only receive previously filtered, non-sensitive read results.
    this.data.delete(key)
    this.data.set(key, { value, until: Date.now() + this.ttlMs })
    while (this.data.size > this.maxEntries) {
      const first = this.data.keys().next().value
      if (!first) break
      this.data.delete(first)
    }
  }
  /** Call on any navigation, mutation, takeover, uncertainty, auth-wall or profile change. */
  clear(): void { this.data.clear() }
}
