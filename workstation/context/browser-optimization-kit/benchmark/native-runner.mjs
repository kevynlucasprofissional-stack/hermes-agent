import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { performance } from 'node:perf_hooks'

import {
  appendMeasurement,
  BROW01_SCHEMA_VERSION,
  BROW01_SCENARIOS
} from './measurements.mjs'
import { findElement, fixtureUrl, resolveRunPaths, resolveTestHome } from './native-guards.mjs'

const MARKER_FILE = '.brow01-test-home.json'
const STANDARD_SCENARIOS = new Set(['forms', 'delayed-hydration', 'lists-tables', 'rich-editor', 'navigation'])

function parseArgs(argv) {
  const command = argv[0]
  if (!['prepare', 'run'].includes(command)) throw new Error('first argument must be prepare or run')

  const args = { command }
  for (let index = 1; index < argv.length; index++) {
    const token = argv[index]
    if (!token.startsWith('--')) throw new Error(`unknown argument: ${token}`)
    args[token.slice(2)] = argv[++index]
  }
  return args
}

function requireArg(args, name) {
  const value = args[name]
  if (typeof value !== 'string' || !value.trim()) throw new Error(`--${name} is required`)
  return value.trim()
}

function requireIdentity(value, label) {
  if (!/^[A-Za-z0-9._-]{1,128}$/.test(value)) {
    throw new Error(`${label} must contain only letters, numbers, dot, underscore, or dash`)
  }
  return value
}

async function prepare(args) {
  const testHome = await resolveTestHome(requireArg(args, 'test-home'), resolve(homedir(), '.hermes'))
  const candidateSha = requireArg(args, 'candidate-sha')
  const configId = requireIdentity(requireArg(args, 'config-id'), 'config id')
  const profileId = requireIdentity(requireArg(args, 'profile-id'), 'profile id')

  if (!/^[0-9a-f]{40}$/i.test(candidateSha)) throw new Error('--candidate-sha must be a full 40-character Git SHA')

  await mkdir(testHome, { recursive: true })
  const marker = {
    schema_version: BROW01_SCHEMA_VERSION,
    purpose: 'BROW-01_ISOLATED_TEST_HOME',
    candidate_sha: candidateSha,
    config_id: configId,
    profile_id: profileId
  }
  await writeFile(resolve(testHome, MARKER_FILE), `${JSON.stringify(marker, null, 2)}\n`, { flag: 'wx' })
  process.stdout.write(`${JSON.stringify({ prepared: true, test_home: testHome, marker: MARKER_FILE })}\n`)
}

async function loadRunConfig(args) {
  const { testHome, controllerFile, output } = await resolveRunPaths({
    testHome: requireArg(args, 'test-home'),
    defaultHome: resolve(homedir(), '.hermes'),
    controllerFile: requireArg(args, 'controller-file'),
    output: requireArg(args, 'output')
  })
  const candidateSha = requireArg(args, 'candidate-sha')
  const configId = requireIdentity(requireArg(args, 'config-id'), 'config id')
  const profileId = requireIdentity(requireArg(args, 'profile-id'), 'profile id')
  const runId = requireIdentity(requireArg(args, 'run-id'), 'run id')
  const sessionPrefix = requireIdentity(requireArg(args, 'session-prefix'), 'session prefix')
  const taskPrefix = requireIdentity(requireArg(args, 'task-prefix'), 'task prefix')
  const runtimeVersion = requireArg(args, 'runtime-version')
  const baseUrl = new URL(requireArg(args, 'base-url'))
  const phase = requireArg(args, 'phase')
  const rounds = Number(requireArg(args, 'rounds'))
  const scenarios = requireArg(args, 'scenarios').split(',').map(value => value.trim()).filter(Boolean)

  if (!/^[0-9a-f]{40}$/i.test(candidateSha)) throw new Error('--candidate-sha must be a full 40-character Git SHA')
  if (baseUrl.protocol !== 'http:' || baseUrl.hostname !== '127.0.0.1') {
    throw new Error('--base-url must use the loopback fixture server at http://127.0.0.1')
  }
  if (!['standard', 'seed', 'resume'].includes(phase)) throw new Error('--phase must be standard, seed, or resume')
  if (!Number.isInteger(rounds) || rounds < 1 || rounds > 100) throw new Error('--rounds must be an integer from 1 to 100')
  if (!scenarios.length || scenarios.some(scenario => !BROW01_SCENARIOS.includes(scenario))) {
    throw new Error('--scenarios contains an unsupported scenario')
  }
  if (!taskPrefix.startsWith('brow01-') || !sessionPrefix.startsWith('brow01-')) {
    throw new Error('task and session prefixes must start with brow01-')
  }
  if (phase === 'standard' && scenarios.some(scenario => !STANDARD_SCENARIOS.has(scenario))) {
    throw new Error('tab-recovery and human-takeover require an explicit seed or resume phase')
  }
  if (phase !== 'standard' && scenarios.some(scenario => STANDARD_SCENARIOS.has(scenario))) {
    throw new Error('standard scenarios require --phase standard')
  }

  const marker = JSON.parse(await readFile(resolve(testHome, MARKER_FILE), 'utf8'))
  if (marker.purpose !== 'BROW-01_ISOLATED_TEST_HOME' || marker.candidate_sha !== candidateSha ||
      marker.config_id !== configId || marker.profile_id !== profileId) {
    throw new Error('isolated test-home marker does not match this candidate/config/profile')
  }

  const fixtureHealth = await fetch(new URL('/health', baseUrl))
  const fixture = await fixtureHealth.json()
  if (!fixtureHealth.ok || fixture.classification !== 'FIXTURE_SMOKE') {
    throw new Error('base URL is not the BROW-01 local fixture server')
  }

  const descriptor = JSON.parse(await readFile(controllerFile, 'utf8'))
  const controllerUrl = new URL(descriptor.url)
  if (descriptor.runtime !== 'electron-chromium' || !descriptor.token ||
      controllerUrl.protocol !== 'http:' || controllerUrl.hostname !== '127.0.0.1') {
    throw new Error('controller descriptor is not a loopback electron-chromium controller')
  }

  const healthResponse = await fetch(new URL('/health', controllerUrl), {
    headers: { authorization: `Bearer ${descriptor.token}` }
  })
  const health = await healthResponse.json()
  if (!healthResponse.ok || health.runtime !== 'electron-chromium') {
    throw new Error('native Browser controller health check failed')
  }

  await mkdir(dirname(output), { recursive: true })
  return {
    testHome, controllerFile, output, candidateSha, configId, profileId, runId,
    sessionPrefix, taskPrefix, runtimeVersion, baseUrl, phase, rounds, scenarios,
    controllerUrl, token: descriptor.token
  }
}

function receiptRef(body, expected) {
  const receipt = body?.result?.receipt
  if (!receipt || receipt.operationId !== expected.operationId || receipt.taskId !== expected.taskId ||
      receipt.runId !== expected.runId || receipt.action !== expected.action || !receipt.tabId ||
      !Number.isInteger(receipt.revision)) {
    return null
  }
  return `${receipt.operationId}:${receipt.tabId}:${receipt.revision}`
}

function createControllerClient(config, scenario) {
  const taskId = `${config.taskPrefix}-${scenario}`
  const sessionId = `${config.sessionPrefix}-${scenario}`
  const metrics = { calls: 0, snapshots: 0, bytes: 0, tokens: [] }

  const call = async (action, arguments_, operationId) => {
    const started = performance.now()
    const response = await fetch(new URL('/v1/action', config.controllerUrl), {
      method: 'POST',
      headers: {
        authorization: `Bearer ${config.token}`,
        'content-type': 'application/json'
      },
      body: JSON.stringify({
        action,
        arguments: arguments_,
        task_id: taskId,
        session_id: sessionId,
        run_id: config.runId,
        operation_id: operationId
      })
    })
    const text = await response.text()
    const body = JSON.parse(text)
    metrics.calls++
    metrics.bytes += Buffer.byteLength(text)
    if (action === 'browser_snapshot') metrics.snapshots++
    const tokens = body?.result?.tokens
    if (typeof tokens === 'number' && Number.isFinite(tokens) && tokens >= 0) metrics.tokens.push(tokens)
    return { ok: response.ok && body.success === true, status: response.status, body, latencyMs: performance.now() - started }
  }

  return { taskId, sessionId, metrics, call }
}

async function requireSuccess(result, label) {
  if (!result.ok) throw new Error(`${label} failed with ${result.status}: ${result.body?.error_code ?? result.body?.error ?? 'unknown'}`)
  return result.body
}

async function navigate(client, config, scenario, round, target = scenario, extra = {}) {
  const operationId = `brow01-${config.runId}-${scenario}-${config.phase}-${round}-navigate`
  const result = await client.call('browser_navigate', { url: fixtureUrl(config, target, extra) }, operationId)
  const body = await requireSuccess(result, 'navigate')
  return receiptRef(body, { operationId, taskId: client.taskId, runId: config.runId, action: 'browser_navigate' })
}

async function snapshot(client, operationId) {
  const result = await client.call('browser_snapshot', {}, operationId)
  return requireSuccess(result, 'snapshot')
}

async function readState(client, config, scenario, operationId) {
  const path = `/api/state/${scenario}?run_id=${encodeURIComponent(config.runId)}`
  const result = await client.call('browser_read_http', { url: path, method: 'GET' }, operationId)
  const body = await requireSuccess(result, 'readback')
  return { value: body.result?.json, ref: path }
}

async function runStandardScenario(config, scenario, round, client) {
  if (scenario === 'navigation') {
    const receipt = await navigate(client, config, scenario, round, 'navigation-target')
    const body = await snapshot(client, `brow01-${config.runId}-${scenario}-${round}-snapshot`)
    const ok = Boolean(findElement(body, 'navigation-target'))
    return ok && receipt
      ? { verification: 'VERIFIED', basis: 'causal_navigation_receipt_and_snapshot', receipt, readback: 'snapshot:navigation-target' }
      : { verification: 'UNCERTAIN', basis: 'missing_navigation_receipt_or_snapshot_readback' }
  }

  const extra = scenario === 'delayed-hydration' ? { delay_ms: 350 } : (scenario === 'lists-tables' ? { rows: 500 } : {})
  const receipt = await navigate(client, config, scenario, round, scenario, extra)

  if (scenario === 'delayed-hydration') {
    let body = null
    for (let attempt = 0; attempt < 20; attempt++) {
      body = await snapshot(client, `brow01-${config.runId}-${scenario}-${round}-snapshot-${attempt}`)
      if (findElement(body, 'hydration-action')) break
      await new Promise(resolve => setTimeout(resolve, 50))
    }
    const ok = Boolean(findElement(body, 'hydration-action'))
    return ok && receipt
      ? { verification: 'VERIFIED', basis: 'causal_navigation_receipt_and_hydrated_snapshot', receipt, readback: 'snapshot:hydration-action' }
      : { verification: 'UNCERTAIN', basis: 'missing_navigation_receipt_or_hydrated_snapshot' }
  }

  const first = await snapshot(client, `brow01-${config.runId}-${scenario}-${round}-snapshot`)
  if (scenario === 'lists-tables') {
    const ok = Boolean(findElement(first, 'items-table'))
    return ok && receipt
      ? { verification: 'VERIFIED', basis: 'causal_navigation_receipt_and_table_snapshot', receipt, readback: 'snapshot:items-table' }
      : { verification: 'UNCERTAIN', basis: 'missing_navigation_receipt_or_table_snapshot' }
  }

  const specs = scenario === 'forms'
    ? [
        ['browser_type', 'form-name', { text: 'BROW-01 User' }],
        ['browser_type', 'form-email', { text: 'brow01@example.invalid' }],
        ['browser_click', 'form-submit', {}]
      ]
    : [
        ['browser_type', 'rich-editor', { text: 'Line one\nLine two\nLine three', mode: 'plain_text_paste' }],
        ['browser_click', 'rich-save', {}]
      ]

  for (const [action, testid, arguments_] of specs) {
    const body = await snapshot(client, `brow01-${config.runId}-${scenario}-${round}-before-${testid}`)
    const element = findElement(body, testid)
    if (!element?.ref) return { verification: 'FAILED', basis: `missing_fixture_ref:${testid}` }
    await requireSuccess(
      await client.call(action, { ref: element.ref, ...arguments_ }, `brow01-${config.runId}-${scenario}-${round}-${testid}`),
      action
    )
  }

  const readback = await readState(client, config, scenario, `brow01-${config.runId}-${scenario}-${round}-readback`)
  const value = readback.value?.value
  const matches = scenario === 'forms'
    ? value?.name === 'BROW-01 User' && value?.email === 'brow01@example.invalid'
    : value?.text === 'Line one\nLine two\nLine three'

  return matches
    ? { verification: 'UNCERTAIN', basis: 'readback_present_but_mutation_receipt_unavailable', readback: readback.ref }
    : { verification: 'FAILED', basis: 'fixture_readback_mismatch', readback: readback.ref }
}

async function runAssistedScenario(config, scenario, round, client) {
  if (config.phase === 'seed') {
    const receipt = await navigate(client, config, scenario, round)
    const body = await snapshot(client, `brow01-${config.runId}-${scenario}-${round}-seed-snapshot`)
    const marker = scenario === 'tab-recovery' ? 'recovery-marker' : 'takeover-cue'
    return receipt && findElement(body, marker)
      ? { verification: 'VERIFIED', basis: 'causal_navigation_receipt_and_seed_snapshot', receipt, readback: `snapshot:${marker}` }
      : { verification: 'UNCERTAIN', basis: 'seed_missing_receipt_or_snapshot' }
  }

  const body = await snapshot(client, `brow01-${config.runId}-${scenario}-${round}-resume-snapshot`)
  if (scenario === 'tab-recovery') {
    const readback = await readState(client, config, scenario, `brow01-${config.runId}-${scenario}-${round}-resume-readback`)
    const restored = Boolean(findElement(body, 'recovery-marker')) && readback.value?.write_count >= 2
    return restored
      ? { verification: 'UNCERTAIN', basis: 'restart_readback_present_but_no_resume_receipt', readback: readback.ref }
      : { verification: 'FAILED', basis: 'restart_readback_missing', readback: readback.ref }
  }

  const cue = findElement(body, 'takeover-cue')
  if (!cue?.ref) return { verification: 'FAILED', basis: 'takeover_fixture_ref_missing' }
  const denied = await client.call(
    'browser_click',
    { ref: cue.ref },
    `brow01-${config.runId}-${scenario}-${round}-guardrail`
  )
  return denied.status === 409 && denied.body?.error_code === 'USER_CONTROL_ACTIVE'
    ? { verification: 'UNCERTAIN', basis: 'guardrail_409_USER_CONTROL_ACTIVE_without_owner_receipt_or_independent_readback' }
    : { verification: 'FAILED', basis: 'expected_USER_CONTROL_ACTIVE_409' }
}

async function runScenario(config, scenario, round) {
  const client = createControllerClient(config, scenario)
  const started = performance.now()
  let result

  try {
    result = STANDARD_SCENARIOS.has(scenario)
      ? await runStandardScenario(config, scenario, round, client)
      : await runAssistedScenario(config, scenario, round, client)
  } catch (error) {
    result = { verification: 'FAILED', basis: error instanceof Error ? error.message : String(error) }
  }

  const record = {
    schema_version: BROW01_SCHEMA_VERSION,
    run_id: config.runId,
    sample_id: `${scenario}-${config.phase}-${round}`,
    candidate_sha: config.candidateSha,
    config_id: config.configId,
    profile_id: config.profileId,
    scenario,
    operation: `${scenario}:${config.phase}`,
    measured_at: new Date().toISOString(),
    evidence_scope: 'NATIVE_BROWSER',
    runtime: 'electron-chromium',
    runtime_version: config.runtimeVersion,
    identity_provenance: { candidate_sha: 'USER_DECLARED', runtime_version: 'USER_DECLARED', build_attestation: 'NV' },
    task_id: client.taskId,
    session_id: client.sessionId,
    qualification: 'NV',
    latency_ms: Math.round((performance.now() - started) * 100) / 100,
    calls: client.metrics.calls,
    snapshots: client.metrics.snapshots,
    bytes: client.metrics.bytes,
    ...(client.metrics.tokens.length ? { tokens: client.metrics.tokens.reduce((sum, value) => sum + value, 0) } : {}),
    verification: result.verification,
    verification_basis: result.basis,
    ...(result.receipt ? { receipt_ref: result.receipt } : {}),
    ...(result.readback ? { readback_ref: result.readback } : {})
  }

  await appendMeasurement(config.output, record)
  return record
}

async function run(args) {
  const config = await loadRunConfig(args)
  const records = []

  for (const scenario of config.scenarios) {
    for (let round = 1; round <= config.rounds; round++) {
      records.push(await runScenario(config, scenario, round))
    }
  }

  process.stdout.write(`${JSON.stringify({
    classification: 'MEASURED_NATIVE_SAMPLES_NOT_H004_H013_QUALIFICATION',
    output: config.output,
    records: records.map(record => ({
      sample_id: record.sample_id,
      verification: record.verification,
      verification_basis: record.verification_basis
    }))
  }, null, 2)}\n`)
}

const args = parseArgs(process.argv.slice(2))
if (args.command === 'prepare') await prepare(args)
else await run(args)
