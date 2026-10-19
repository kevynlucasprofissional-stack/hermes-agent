import { describe, expect, it } from 'vitest'

import { normalizeExtractedItem, sanitizeExtractedItems } from './workstation-browser-extract-cache'

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
      // Use a non-JWT opaque bearer value so only BEARER_VALUE_PATTERN matches;
      // JWTs are covered separately by JWT_PATTERN in another test.
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
      // AIza pattern requires 30+ chars after prefix; use a realistic-length key
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
        // "auth_header" does not match SENSITIVE_KEY_PATTERN (which checks for
        // password|secret|token|bearer|api_key|auth_token|credit_card), so
        // value-level redaction applies instead of full key redaction.
        auth_header: 'Bearer opaque.value.long_enough_to_trigger_bearer_pattern_match',
        page_title: 'Settings'
      }
    }

    const result = normalizeExtractedItem(item) as Record<string, any>
    expect(result.user.name).toBe('Alice')
    expect(result.metadata.page_title).toBe('Settings')
    // Value-level bearer redaction preserves the "Bearer" prefix marker
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