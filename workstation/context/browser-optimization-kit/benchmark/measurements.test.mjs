import assert from 'node:assert/strict'
import test from 'node:test'

import { BROW01_SCHEMA_VERSION, parseMeasurementJsonl, summarizeMeasurements, validateMeasurement } from './measurements.mjs'

function measurement(overrides = {}) {
  return {
    schema_version: BROW01_SCHEMA_VERSION,
    run_id: 'run-a', sample_id: 'sample-1', candidate_sha: 'a'.repeat(40), config_id: 'config-a',
    scenario: 'navigation', operation: 'navigation:standard', measured_at: '2026-10-10T12:00:00.000Z',
    evidence_scope: 'NATIVE_BROWSER', runtime: 'electron-chromium', runtime_version: 'declared-version',
    task_id: 'brow01-task', qualification: 'NV', verification: 'UNCERTAIN',
    ...overrides
  }
}

test('native VERIFIED always requires receipt and readback, including guardrail observations', () => {
  for (const basis of ['causal_navigation_receipt_and_snapshot', 'guardrail_409']) {
    const record = measurement({ verification: 'VERIFIED', verification_basis: basis })
    assert.throws(() => validateMeasurement(record), /receipt_ref/)
    assert.throws(() => validateMeasurement({ ...record, receipt_ref: 'receipt:1' }), /readback_ref/)
    assert.throws(() => validateMeasurement({ ...record, receipt_ref: ' ', readback_ref: 'readback:1' }), /receipt_ref/)
    assert.equal(validateMeasurement({ ...record, receipt_ref: 'receipt:1', readback_ref: 'readback:1' }).verification, 'VERIFIED')
  }
  const uncertain = measurement({ verification_basis: 'guardrail_409_USER_CONTROL_ACTIVE_without_owner_receipt_or_independent_readback' })
  const summary = summarizeMeasurements([uncertain])
  assert.equal(summary.verification_by_scope.NATIVE_BROWSER.verified, 0)
  assert.equal(summary.verification_by_scope.NATIVE_BROWSER.uncertain, 1)
  assert.equal(summary.verification_by_scope.NATIVE_BROWSER.verified_rate, 0)
})

test('summaries reject duplicate run/sample identities and retain run, SHA and config boundaries', () => {
  const first = measurement()
  assert.throws(() => summarizeMeasurements([first, { ...first, config_id: 'other' }]), /duplicate sample_id/)
  const records = [first,
    measurement({ sample_id: 'sample-2', candidate_sha: 'b'.repeat(40) }),
    measurement({ sample_id: 'sample-3', config_id: 'config-b' }),
    measurement({ run_id: 'run-b' })
  ]
  const summary = summarizeMeasurements(records)
  assert.equal(summary.record_count, 4)
  assert.equal(summary.groups.length, 4)
  assert.equal(new Set(summary.groups.map(group => `${group.run_id}/${group.candidate_sha}/${group.config_id}`)).size, 4)
})

test('percentiles use only observed metrics and report missing counts', () => {
  const records = [40, 10, 30, 20, 'NV'].map((latency_ms, index) => measurement({ sample_id: `sample-${index}`, latency_ms }))
  const group = summarizeMeasurements(records).groups[0]
  assert.deepEqual(group.metrics.latency_ms, { observed: 4, missing: 1, p50: 30, p95: 40 })
  assert.deepEqual(group.metrics.memory_bytes, { observed: 0, missing: 5, p50: 'NV', p95: 'NV' })
  assert.equal(group.verification.denominator, 5)
  assert.equal(group.verification.uncertain, 5)
})

test('empty, invalid and malformed JSONL fail with useful line information', () => {
  assert.throws(() => summarizeMeasurements([]), /empty/)
  assert.throws(() => parseMeasurementJsonl(' \n\r\n'), /no records/)
  assert.throws(() => parseMeasurementJsonl(`${JSON.stringify(measurement())}\n{broken`), /line 2 is not valid JSON/)
  assert.throws(() => parseMeasurementJsonl('{}'), /line 1: schema_version/)
  assert.deepEqual(parseMeasurementJsonl(`\n${JSON.stringify(measurement())}\r\n`), [measurement()])
})
