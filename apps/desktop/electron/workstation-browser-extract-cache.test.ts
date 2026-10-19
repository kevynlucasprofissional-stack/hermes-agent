import assert from 'node:assert/strict'

import { describe, expect, it, test } from 'vitest'

import {
  BoundedExtractCache,
  computeQueryDigest,
  type ExtractScope,
  normalizeExtractedItem,
  sanitizeExtractedItems
} from './workstation-browser-extract-cache'

const scope: ExtractScope = {
  profileId: 'p',
  taskId: 't',
  tabId: 'tab',
  url: 'https://example.test/',
  documentEpoch: 'e1',
  mutationRevision: 1,
  documentFingerprint: 'dom1',
  queryDigest: 'q1'
}

describe('OPT-03 Structured Extraction Cache & Sanitization', () => {
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
    assert.throws(() => cache.get({ ...scope, documentEpoch: '' }))
    assert.throws(() => cache.get({ ...scope, mutationRevision: -1 }))
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

  test('computeQueryDigest produces consistent 16-hex characters hash', () => {
    const d1 = computeQueryDigest({ selector: '.item', limit: 20 })
    const d2 = computeQueryDigest({ selector: '.item', limit: 20 })
    const d3 = computeQueryDigest({ selector: '.item', limit: 50 })
    assert.equal(d1, d2)
    assert.notEqual(d1, d3)
    assert.equal(d1.length, 16)
  })

  test('query digest isolates schema projections on the same document', () => {
    const base = { selector: '.card', limit: 20 }
    const a = computeQueryDigest({ ...base, schema: { properties: { title: { type: 'string' } } } })
    const b = computeQueryDigest({ ...base, schema: { properties: { price: { type: 'number' } } } })
    assert.notEqual(a, b)
  })

  test('nested arrays of extracted records never leak secret fields', () => {
    const result = sanitizeExtractedItems([{ items: [{ name: 'safe', api_token: 'DO_NOT_LEAK' }] }]) as any[]
    assert.equal(result[0].items[0].name, 'safe')
    assert.equal(result[0].items[0].api_token, '[REDACTED]')
  })

  test('normalizeExtractedItem and sanitizeExtractedItems redact sensitive fields and truncate oversized text', () => {
    const raw = [
      {
        title: 'Product 1',
        password: 'super-secret-password',
        user_api_key: 'sk-1234567890',
        token: 'ey...',
        price: '$10.00'
      }
    ]
    const sanitized = sanitizeExtractedItems(raw) as any[]
    assert.equal(sanitized[0].title, 'Product 1')
    assert.equal(sanitized[0].price, '$10.00')
    assert.equal(sanitized[0].password, '[REDACTED]')
    assert.equal(sanitized[0].user_api_key, '[REDACTED]')
    assert.equal(sanitized[0].token, '[REDACTED]')

    const single = normalizeExtractedItem({ auth_token: 'secret', name: 'valid' }) as any
    assert.equal(single.auth_token, '[REDACTED]')
    assert.equal(single.name, 'valid')
  })
})

describe('B1.2 value-level secret redaction in normalizeExtractedItem', () => {
  it('redacts JWTs embedded in string values with benign keys', () => {
    const item = {
      text: 'Response: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
      label: 'API response'
    }

    const result = normalizeExtractedItem(item) as Record<string, unknown>
    expect(result.text).toContain('[REDACTED_JWT]')
    expect(result.text).not.toContain('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9')
  })

  it('redacts Bearer tokens in header-like values', () => {
    const item = {
      content: 'Authorization: Bearer mF_9.B5f-4.1JqM_long_enough_opaque_token_value_for_regex_match',
      source: 'network'
    }

    const result = normalizeExtractedItem(item) as Record<string, unknown>
    expect(result.content).toContain('Bearer [REDACTED]')
    expect(result.content).not.toContain('mF_9.B5f-4')
  })

  it('redacts prefixed API keys (sk-, ghp_, AKIA, AIza)', () => {
    const item = {
      note: 'Found key sk-abcdefghijklmnopqrstuvwxyz1234567890 in config',
      backup: 'GitHub token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij',
      aws: 'Access key AKIAIOSFODNN7EXAMPLE is active',
      gcp: 'Key AIzaSyA1234567890abcdefghijklmnopqrstuvwxyz loaded'
    }

    const result = normalizeExtractedItem(item) as Record<string, unknown>
    expect(result.note).toContain('[REDACTED_KEY]')
    expect(result.note).not.toContain('sk-abcdef')
    expect(result.backup).toContain('[REDACTED_KEY]')
    expect(result.backup).not.toContain('ghp_ABCDEF')
    expect(result.aws).toContain('[REDACTED_KEY]')
    expect(result.gcp).toContain('[REDACTED_KEY]')
  })

  it('still redacts sensitive key names regardless of value', () => {
    const item = { password: 'hunter2', api_key: 'not-a-real-key', token: 'short' }
    const result = normalizeExtractedItem(item) as Record<string, unknown>
    expect(result.password).toBe('[REDACTED]')
    expect(result.api_key).toBe('[REDACTED]')
    expect(result.token).toBe('[REDACTED]')
  })

  it('applies value-level redaction to bare string items in arrays', () => {
    const items = [
      'Bearer abc123token456value789extra012end',
      'Normal text without secrets',
      'Contains sk-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHHIIIIJJJJ key'
    ]

    const result = sanitizeExtractedItems(items) as string[]
    expect(result[0]).toContain('Bearer [REDACTED]')
    expect(result[1]).toBe('Normal text without secrets')
    expect(result[2]).toContain('[REDACTED_KEY]')
  })

  it('preserves non-secret strings unchanged', () => {
    const item = { title: 'Dashboard', description: 'Welcome back user' }
    const result = normalizeExtractedItem(item) as Record<string, unknown>
    expect(result.title).toBe('Dashboard')
    expect(result.description).toBe('Welcome back user')
  })

  it('handles nested objects with mixed secret and non-secret values', () => {
    const item = {
      user: { name: 'Alice', email: 'alice@example.com' },
      metadata: {
        auth_header: 'Bearer opaque.value.long_enough_to_trigger_bearer_pattern_match',
        page_title: 'Settings'
      }
    }

    const result = normalizeExtractedItem(item) as Record<string, any>
    expect(result.user.name).toBe('Alice')
    expect(result.metadata.page_title).toBe('Settings')
    expect(result.metadata.auth_header).toContain('Bearer [REDACTED]')
    expect(result.metadata.auth_header).not.toContain('opaque.value')
  })

  it('fully redacts keys matching SENSITIVE_KEY_PATTERN regardless of value', () => {
    const item = {
      config: {
        auth_token: 'any-value-here',
        api_key: 'another-value',
        safe_field: 'visible'
      }
    }

    const result = normalizeExtractedItem(item) as Record<string, any>
    expect(result.config.auth_token).toBe('[REDACTED]')
    expect(result.config.api_key).toBe('[REDACTED]')
    expect(result.config.safe_field).toBe('visible')
  })
})