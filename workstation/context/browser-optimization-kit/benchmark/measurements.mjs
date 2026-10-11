import { appendFile, readFile } from 'node:fs/promises'

import { summarize } from '../../../../apps/desktop/scripts/perf/lib/stats.mjs'

export const BROW01_SCHEMA_VERSION = 1
export const BROW01_SCENARIOS = Object.freeze([
  'forms',
  'delayed-hydration',
  'lists-tables',
  'rich-editor',
  'navigation',
  'tab-recovery',
  'human-takeover'
])

const EVIDENCE_SCOPES = new Set(['FIXTURE_SMOKE', 'NATIVE_BROWSER'])
const VERIFICATIONS = new Set(['VERIFIED', 'FAILED', 'UNCERTAIN'])
const OPTIONAL_METRICS = ['latency_ms', 'memory_bytes', 'cpu_ms', 'calls', 'snapshots', 'bytes', 'tokens']

function requiredString(record, field) {
  const value = record[field]

  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${field} must be a non-empty string`)
  }
}

function optionalMetric(record, field) {
  const value = record[field]

  if (value === undefined || value === null || value === 'NV') {
    return
  }

  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    throw new Error(`${field} must be a finite non-negative number, NV, or absent`)
  }
}

export function validateMeasurement(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    throw new Error('measurement must be a JSON object')
  }
  if (record.schema_version !== BROW01_SCHEMA_VERSION) {
    throw new Error(`schema_version must be ${BROW01_SCHEMA_VERSION}`)
  }

  for (const field of [
    'run_id', 'sample_id', 'candidate_sha', 'config_id', 'scenario', 'operation', 'measured_at', 'evidence_scope'
  ]) {
    requiredString(record, field)
  }
  if (!BROW01_SCENARIOS.includes(record.scenario)) {
    throw new Error(`scenario must be one of: ${BROW01_SCENARIOS.join(', ')}`)
  }
  if (!EVIDENCE_SCOPES.has(record.evidence_scope)) {
    throw new Error('evidence_scope must be FIXTURE_SMOKE or NATIVE_BROWSER')
  }
  if (!VERIFICATIONS.has(record.verification)) {
    throw new Error('verification must be VERIFIED, FAILED, or UNCERTAIN')
  }
  if (!Number.isFinite(Date.parse(record.measured_at))) {
    throw new Error('measured_at must be an ISO-8601 timestamp')
  }

  for (const metric of OPTIONAL_METRICS) {
    optionalMetric(record, metric)
  }

  if (record.verification === 'VERIFIED') {
    requiredString(record, 'verification_basis')
  }
  if (record.qualification !== undefined && !['NV', 'H004', 'H013'].includes(record.qualification)) {
    throw new Error('qualification must be NV, H004, H013, or absent')
  }
  if (record.evidence_scope === 'FIXTURE_SMOKE' && record.qualification !== undefined && record.qualification !== 'NV') {
    throw new Error('fixture smoke cannot claim native Browser qualification')
  }
  if (record.evidence_scope === 'NATIVE_BROWSER') {
    for (const field of ['runtime', 'runtime_version', 'task_id']) {
      requiredString(record, field)
    }
    if (record.runtime !== 'electron-chromium') {
      throw new Error('native Browser measurements require runtime electron-chromium')
    }
    if (record.verification === 'VERIFIED') {
      requiredString(record, 'receipt_ref')
      requiredString(record, 'readback_ref')
    }
    if (record.qualification && record.qualification !== 'NV') {
      requiredString(record, 'qualification_evidence')
    }
  }

  return record
}

export function parseMeasurementJsonl(source) {
  const records = []

  for (const [index, line] of source.split(/\r?\n/).entries()) {
    if (!line.trim()) {
      continue
    }

    let record
    try {
      record = JSON.parse(line)
    } catch (error) {
      throw new Error(`line ${index + 1} is not valid JSON: ${error.message}`)
    }

    try {
      records.push(validateMeasurement(record))
    } catch (error) {
      throw new Error(`line ${index + 1}: ${error.message}`)
    }
  }

  if (!records.length) {
    throw new Error('measurement input contains no records')
  }

  return records
}

function summarizeMetric(records, metric) {
  const values = records
    .map(record => record[metric])
    .filter(value => typeof value === 'number' && Number.isFinite(value))

  if (!values.length) {
    return { observed: 0, missing: records.length, p50: 'NV', p95: 'NV' }
  }

  const stats = summarize(values)
  return { observed: values.length, missing: records.length - values.length, p50: stats.p50, p95: stats.p95 }
}

function groupKey(record) {
  return [
    record.evidence_scope,
    record.run_id,
    record.candidate_sha,
    record.config_id,
    record.runtime_version ?? 'NV',
    record.scenario,
    record.operation
  ].join('\u0000')
}

export function summarizeMeasurements(records) {
  if (!Array.isArray(records) || records.length === 0) {
    throw new Error('cannot summarize an empty measurement set')
  }

  const validated = records.map(validateMeasurement)
  const seenSamples = new Set()
  const groups = new Map()

  for (const record of validated) {
    const sampleKey = `${record.run_id}\u0000${record.sample_id}`
    if (seenSamples.has(sampleKey)) {
      throw new Error(`duplicate sample_id in run ${record.run_id}: ${record.sample_id}`)
    }
    seenSamples.add(sampleKey)

    const key = groupKey(record)
    const current = groups.get(key) ?? []
    current.push(record)
    groups.set(key, current)
  }

  const summaries = [...groups.values()]
    .map(group => {
      const verified = group.filter(record => record.verification === 'VERIFIED').length
      const failed = group.filter(record => record.verification === 'FAILED').length
      const uncertain = group.filter(record => record.verification === 'UNCERTAIN').length

      return {
        evidence_scope: group[0].evidence_scope,
        run_id: group[0].run_id,
        candidate_sha: group[0].candidate_sha,
        config_id: group[0].config_id,
        runtime_version: group[0].runtime_version ?? 'NV',
        scenario: group[0].scenario,
        operation: group[0].operation,
        sample_count: group.length,
        verification: {
          verified,
          failed,
          uncertain,
          denominator: group.length,
          verified_rate: Math.round((verified / group.length) * 10_000) / 10_000
        },
        metrics: Object.fromEntries(OPTIONAL_METRICS.map(metric => [metric, summarizeMetric(group, metric)]))
      }
    })
    .sort((left, right) => groupKey(left).localeCompare(groupKey(right)))

  const verificationByScope = Object.fromEntries([...EVIDENCE_SCOPES].map(scope => {
    const scoped = validated.filter(record => record.evidence_scope === scope)
    const verified = scoped.filter(record => record.verification === 'VERIFIED').length

    return [scope, {
      verified,
      failed: scoped.filter(record => record.verification === 'FAILED').length,
      uncertain: scoped.filter(record => record.verification === 'UNCERTAIN').length,
      denominator: scoped.length,
      verified_rate: scoped.length ? Math.round((verified / scoped.length) * 10_000) / 10_000 : 'NV'
    }]
  }))

  return {
    schema_version: BROW01_SCHEMA_VERSION,
    classification: 'MEASURED_RECORDS_ONLY',
    percentile_method: 'apps/desktop/scripts/perf/lib/stats.mjs summarize()',
    record_count: validated.length,
    verification_by_scope: verificationByScope,
    groups: summaries
  }
}

export async function appendMeasurement(path, record) {
  const validated = validateMeasurement(record)
  await appendFile(path, `${JSON.stringify(validated)}\n`, { encoding: 'utf8', flag: 'a' })
}

export async function readMeasurements(path) {
  return parseMeasurementJsonl(await readFile(path, 'utf8'))
}
