import assert from 'node:assert/strict'
import { test } from 'vitest'
import { BoundedExtractCache, type ExtractScope } from './extract-cache'
const scope: ExtractScope = { profileId: 'p', taskId: 't', tabId: 'tab', url: 'https://example.test/',
  documentEpoch: 'e1', mutationRevision: 1, documentFingerprint: 'dom1', queryDigest: 'q1' }
test('invalidates on mutation revision and DOM fingerprint', () => {
  const cache = new BoundedExtractCache<string>()
  cache.set(scope, 'old')
  assert.equal(cache.get(scope), 'old')
  assert.equal(cache.get({ ...scope, mutationRevision: 2 }), null)
  assert.equal(cache.get({ ...scope, documentFingerprint: 'dom2' }), null)
  cache.clear()
  assert.equal(cache.get(scope), null)
})
test('rejects unproven document identity', () => {
  const cache = new BoundedExtractCache<string>()
  assert.throws(() => cache.get({ ...scope, documentFingerprint: '' }))
})
