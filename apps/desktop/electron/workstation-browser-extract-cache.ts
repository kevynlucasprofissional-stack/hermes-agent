/**
 * Hermes Workstation Browser Extract Cache & Structured Normalization
 *
 * Provides bounded in-memory caching for READ-only structured extraction.
 * Mandatory verified documentFingerprint + epoch + revision prevents stale SPA reads.
 * Automatically sanitizes sensitive keys and passwords.
 */

import crypto from 'node:crypto'

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

  constructor(
    private readonly maxEntries = 64,
    private readonly ttlMs = 4_000
  ) {}

  private key(s: ExtractScope): string {
    if (
      !s.profileId ||
      !s.taskId ||
      !s.tabId ||
      !s.url ||
      !s.documentEpoch ||
      !s.documentFingerprint ||
      !s.queryDigest ||
      !Number.isSafeInteger(s.mutationRevision) ||
      s.mutationRevision < 0
    ) {
      throw new Error('extract_fingerprint_required')
    }

    return JSON.stringify([
      s.profileId,
      s.taskId,
      s.tabId,
      s.url,
      s.documentEpoch,
      s.mutationRevision,
      s.documentFingerprint,
      s.queryDigest
    ])
  }

  get(scope: ExtractScope): T | null {
    const key = this.key(scope)
    const record = this.data.get(key)

    if (!record) {return null}

    if (record.until < Date.now()) {
      this.data.delete(key)

      return null
    }

    return record.value
  }

  set(scope: ExtractScope, value: T): void {
    const key = this.key(scope)
    // Cache must only receive previously filtered, non-sensitive read results.
    this.data.delete(key)
    this.data.set(key, { value, until: Date.now() + this.ttlMs })

    while (this.data.size > this.maxEntries) {
      const first = this.data.keys().next().value

      if (!first) {break}
      this.data.delete(first)
    }
  }

  /** Invalidate entries belonging to a specific tab */
  invalidateTab(tabId: string): void {
    if (!tabId) {return}

    for (const [key] of this.data.entries()) {
      try {
        const parsed = JSON.parse(key)

        if (Array.isArray(parsed) && parsed[2] === tabId) {
          this.data.delete(key)
        }
      } catch {
        this.data.delete(key)
      }
    }
  }

  /** Call on any navigation, mutation, takeover, uncertainty, auth-wall or profile change. */
  clear(): void {
    this.data.clear()
  }

  /** Invalidate all cached entries for a given task */
  invalidateTask(taskId: string): void {
    if (!taskId) {return}

    for (const key of Array.from(this.data.keys())) {
      try {
        const parsed = JSON.parse(key)

        if (Array.isArray(parsed) && parsed[1] === taskId) {
          this.data.delete(key)
        }
      } catch {
        this.data.delete(key)
      }
    }
  }

  size(): number {
    return this.data.size
  }
}

/** Compute SHA-256 digest of extraction query parameters */
export function computeQueryDigest(args: Record<string, unknown>): string {
  const normalized = JSON.stringify({
    selector: args.selector ?? null,
    limit: args.limit ?? 20,
    mode: args.mode ?? 'default',
    attributes: args.attributes ?? [],
    // Different schema projections must never share a cached answer.
    schema: args.schema ?? null
  })

  return crypto.createHash('sha256').update(normalized).digest('hex').slice(0, 16)
}

export const queryDigest = computeQueryDigest

const SENSITIVE_KEY_PATTERN = /(?:password|secret|token|bearer|api[_-]?key|auth[_-]?token|credit[_-]?card)/i

// B1.2: Value-level secret patterns for strings whose KEY is not sensitive but
// whose VALUE contains credentials. Covers JWTs, Bearer tokens, prefixed API
// keys (sk-, ghp_, xoxb-, etc.), and URL-encoded secrets in query strings.
// These run only on string values after the key-name check passes, so they
// never double-redact an already-redacted field.
const JWT_PATTERN = /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g
const BEARER_VALUE_PATTERN = /\bBearer\s+[A-Za-z0-9_.\-+/]+=*/gi
const PREFIXED_KEY_PATTERN = /\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|xox[bpras]-[A-Za-z0-9-]{10,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,})\b/g
const URL_ENCODED_SECRET_PATTERN = /(?:%22|")(?:password|secret|token|api_key|access_token)(?:%22|")\s*(?:%3A|:)\s*(?:%22|")[^"]{8,}(?:%22|")/gi

function redactSecretValues(value: string): string {
  let result = value
  result = result.replace(JWT_PATTERN, '[REDACTED_JWT]')
  result = result.replace(BEARER_VALUE_PATTERN, 'Bearer [REDACTED]')
  result = result.replace(PREFIXED_KEY_PATTERN, '[REDACTED_KEY]')
  result = result.replace(URL_ENCODED_SECRET_PATTERN, '[REDACTED_URL_SECRET]')

  return result
}

/** Normalize and sanitize a single extracted item, optionally filtering by schema properties */
export function normalizeExtractedItem(item: unknown, schema?: Record<string, unknown> | null, depth = 0): unknown {
  if (depth > 8) {return '[TRUNCATED_DEPTH]'}

  if (Array.isArray(item)) {return item.slice(0, 100).map(value => normalizeExtractedItem(value, null, depth + 1))}

  // B1.2: Apply value-level redaction to bare strings (e.g. top-level array
  // items or primitive values passed directly). Object string values are
  // handled in the loop below after the key-name check.
  if (typeof item === 'string') {return redactSecretValues(item).slice(0, 20_000)}

  if (!item || typeof item !== 'object') {return item}
  const record = item as Record<string, unknown>
  const cleaned: Record<string, unknown> = {}

  const schemaProperties =
    schema && typeof schema.properties === 'object' && schema.properties !== null
      ? Object.keys(schema.properties as Record<string, unknown>)
      : null

  for (const [k, v] of Object.entries(record)) {
    if (schemaProperties && !schemaProperties.includes(k)) {
      continue
    }

    if (SENSITIVE_KEY_PATTERN.test(k)) {
      cleaned[k] = '[REDACTED]'
    } else if (typeof v === 'string') {
      // B1.2: Redact secrets embedded in string values even when the key
      // name is benign (e.g. "text", "content", "url"). This catches JWTs
      // in response bodies, Bearer tokens in header dumps, and API keys
      // pasted into form fields.
      cleaned[k] = redactSecretValues(v).slice(0, 20_000)
    } else if (v && typeof v === 'object') {
      cleaned[k] = normalizeExtractedItem(v, null, depth + 1)
    } else {
      cleaned[k] = v
    }
  }

  return cleaned
}

// B1.3: Lightweight JSON Schema subset validator for extracted items.
// Supports: type, required, enum, properties (recursive). Rejects schemas
// using unsupported keywords (e.g. $ref, allOf, anyOf, patternProperties)
// to prevent silent acceptance of data that was never truly validated.
const SUPPORTED_SCHEMA_KEYWORDS = new Set([
  'type', 'required', 'enum', 'properties', 'description', 'title'
])

export interface SchemaValidationResult {
  valid: boolean
  errors: string[]
  /** True when the schema uses keywords this validator does not support. */
  unsupportedKeywords?: string[]
}

function validateSchemaSubset(
  value: unknown,
  schema: Record<string, unknown>,
  path: string,
  depth: number
): SchemaValidationResult {
  const errors: string[] = []
  const unsupported: string[] = []

  if (depth > 8) {
    return { valid: false, errors: [`${path}: schema nesting exceeds maximum depth`] }
  }

  // Detect unsupported keywords at this level
  for (const key of Object.keys(schema)) {
    if (!SUPPORTED_SCHEMA_KEYWORDS.has(key)) {
      unsupported.push(key)
    }
  }

  if (unsupported.length > 0) {
    return {
      valid: false,
      errors: [`${path}: unsupported schema keywords: ${unsupported.join(', ')}`],
      unsupportedKeywords: unsupported
    }
  }

  // Type check
  const schemaType = schema.type

  if (typeof schemaType === 'string') {
    const actualType = Array.isArray(value) ? 'array'
      : value === null ? 'null'
      : typeof value

    if (actualType !== schemaType) {
      errors.push(`${path}: expected type "${schemaType}" but got "${actualType}"`)
    }
  }

  // Enum check
  if (Array.isArray(schema.enum)) {
    if (!schema.enum.includes(value)) {
      errors.push(`${path}: value not in enum [${schema.enum.map(String).join(', ')}]`)
    }
  }

  // Required + properties check (only for objects)
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const record = value as Record<string, unknown>

    if (Array.isArray(schema.required)) {
      for (const reqKey of schema.required) {
        if (typeof reqKey === 'string' && !(reqKey in record)) {
          errors.push(`${path}: missing required property "${reqKey}"`)
        }
      }
    }

    if (schema.properties && typeof schema.properties === 'object') {
      const props = schema.properties as Record<string, unknown>

      for (const [propKey, propSchema] of Object.entries(props)) {
        if (propKey in record && propSchema && typeof propSchema === 'object') {
          const childResult = validateSchemaSubset(
            record[propKey],
            propSchema as Record<string, unknown>,
            `${path}.${propKey}`,
            depth + 1
          )

          errors.push(...childResult.errors)

          if (childResult.unsupportedKeywords) {
            unsupported.push(...childResult.unsupportedKeywords)
          }
        }
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    unsupportedKeywords: unsupported.length > 0 ? unsupported : undefined
  }
}

/**
 * Validate extracted items against a JSON Schema subset.
 * Returns validation results separate from sanitization so callers can
 * distinguish "capture succeeded" from "result conforms to schema".
 */
export function validateExtractedItems(
  items: unknown[],
  schema: Record<string, unknown> | null | undefined
): SchemaValidationResult {
  if (!schema || typeof schema !== 'object') {
    return { valid: true, errors: [] }
  }

  const allErrors: string[] = []
  let hasUnsupported = false
  const unsupportedKw: string[] = []

  for (let i = 0; i < items.length; i++) {
    const result = validateSchemaSubset(items[i], schema, `$[${i}]`, 0)
    allErrors.push(...result.errors)

    if (result.unsupportedKeywords) {
      hasUnsupported = true
      unsupportedKw.push(...result.unsupportedKeywords)
    }
  }

  return {
    valid: allErrors.length === 0 && !hasUnsupported,
    errors: allErrors,
    unsupportedKeywords: hasUnsupported ? [...new Set(unsupportedKw)] : undefined
  }
}

/** Sanitize an array of extracted items */
export function sanitizeExtractedItems(items: unknown[], schema?: Record<string, unknown> | null): unknown[] {
  if (!Array.isArray(items)) {return []}

  return items.slice(0, 100).map(item => normalizeExtractedItem(item, schema))
}
