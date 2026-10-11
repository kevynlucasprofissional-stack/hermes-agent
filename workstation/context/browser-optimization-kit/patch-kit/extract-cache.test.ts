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

test.each([
  ['profile', { ...scope, profileId: 'profile-b' }],
  ['tab', { ...scope, tabId: 'tab-b' }],
  ['document epoch', { ...scope, documentEpoch: 'epoch-b' }],
  ['URL', { ...scope, url: 'https://other.example.test/' }],
  ['query', { ...scope, queryDigest: 'query-b' }]
])('isolates profile/tab/document/query identity across A→B→A (%s)', (_label, scopeB) => {
  const cache = new BoundedExtractCache<string>()
  cache.set(scope, 'result-a')
  assert.equal(cache.get(scopeB), null)
  cache.set(scopeB, 'result-b')
  assert.equal(cache.get(scopeB), 'result-b')
  assert.equal(cache.get(scope), 'result-a')
})
