import { describe, expect, it } from 'vitest'

import { validateExtractedItems } from './workstation-browser-extract-cache'

describe('B1.3 schema validation for extracted items', () => {
  it('accepts valid items matching required properties and types', () => {
    const schema = {
      type: 'object',
      required: ['name', 'age'],
      properties: {
        name: { type: 'string' },
        age: { type: 'number' }
      }
    }

    const items = [{ name: 'Alice', age: 30 }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(true)
    expect(result.errors).toHaveLength(0)
  })

  it('rejects items missing required properties', () => {
    const schema = {
      type: 'object',
      required: ['id', 'title'],
      properties: {
        id: { type: 'string' },
        title: { type: 'string' }
      }
    }

    const items = [{ id: 'abc' }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(false)
    expect(result.errors.some(e => e.includes('missing required property "title"'))).toBe(true)
  })

  it('rejects items with wrong property types', () => {
    const schema = {
      type: 'object',
      properties: {
        count: { type: 'number' },
        label: { type: 'string' }
      }
    }

    const items = [{ count: 'not-a-number', label: 42 }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(false)
    expect(result.errors.some(e => e.includes('expected type "number" but got "string"'))).toBe(true)
    expect(result.errors.some(e => e.includes('expected type "string" but got "number"'))).toBe(true)
  })

  it('rejects values not in enum', () => {
    const schema = {
      type: 'object',
      properties: {
        status: { type: 'string', enum: ['active', 'inactive'] }
      }
    }

    const items = [{ status: 'pending' }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(false)
    expect(result.errors.some(e => e.includes('value not in enum'))).toBe(true)
  })

  it('accepts values within enum', () => {
    const schema = {
      type: 'object',
      properties: {
        status: { type: 'string', enum: ['active', 'inactive'] }
      }
    }

    const items = [{ status: 'active' }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(true)
  })

  it('rejects schemas using unsupported keywords like $ref or allOf', () => {
    const schema = {
      type: 'object',
      $ref: '#/definitions/Foo',
      properties: { name: { type: 'string' } }
    }

    const items = [{ name: 'test' }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(false)
    expect(result.unsupportedKeywords).toContain('$ref')
  })

  it('returns valid when no schema is provided', () => {
    const items = [{ anything: 'goes' }]
    expect(validateExtractedItems(items, null).valid).toBe(true)
    expect(validateExtractedItems(items, undefined).valid).toBe(true)
  })

  it('validates nested object properties recursively', () => {
    const schema = {
      type: 'object',
      properties: {
        user: {
          type: 'object',
          required: ['email'],
          properties: {
            email: { type: 'string' }
          }
        }
      }
    }

    const items = [{ user: {} }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(false)
    expect(result.errors.some(e => e.includes('missing required property "email"'))).toBe(true)
  })

  it('reports errors per item index in multi-item arrays', () => {
    const schema = {
      type: 'object',
      required: ['id'],
      properties: { id: { type: 'string' } }
    }

    const items = [{ id: 'ok' }, {}, { id: 123 }]
    const result = validateExtractedItems(items, schema)
    expect(result.valid).toBe(false)
    expect(result.errors.some(e => e.startsWith('$[1]') && e.includes('missing required'))).toBe(true)
    expect(result.errors.some(e => e.startsWith('$[2]') && e.includes('expected type "string"'))).toBe(true)
  })

  it('rejects unsupported schema keywords even when items array is empty', () => {
    const schema = {
      type: 'object',
      $ref: '#/definitions/Foo',
      properties: { name: { type: 'string' } }
    }

    const result = validateExtractedItems([], schema)
    expect(result.valid).toBe(false)
    expect(result.unsupportedKeywords).toContain('$ref')
  })

  it('rejects allOf/anyOf/oneOf/patternProperties on empty items', () => {
    const schema = {
      type: 'object',
      allOf: [{ required: ['x'] }],
      anyOf: [{ required: ['y'] }],
      oneOf: [{ required: ['z'] }],
      patternProperties: { '^x': { type: 'string' } }
    }

    const result = validateExtractedItems([], schema)
    expect(result.valid).toBe(false)
    expect(result.unsupportedKeywords).toEqual(
      expect.arrayContaining(['allOf', 'anyOf', 'oneOf', 'patternProperties'])
    )
  })

  it('returns valid for empty items with a supported-only schema', () => {
    const schema = {
      type: 'object',
      required: ['id'],
      properties: { id: { type: 'string' } }
    }

    const result = validateExtractedItems([], schema)
    expect(result.valid).toBe(true)
    expect(result.errors).toHaveLength(0)
    expect(result.unsupportedKeywords).toBeUndefined()
  })
})