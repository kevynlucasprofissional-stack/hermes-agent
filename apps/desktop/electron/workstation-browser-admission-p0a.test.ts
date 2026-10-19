import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test, vi } from 'vitest'

// Mock electron before importing runtime — same pattern as workstation-browser-runtime-task.test.ts
const electron = vi.hoisted(() => {
  type Listener = (...args: unknown[]) => void
  const listeners = new Map<string, Listener[]>()

  return {
    app: {
      getPath: (name: string) => name === 'userData' ? path.join(os.tmpdir(), 'hermes-test-userdata') : os.tmpdir(),
      on: () => undefined,
      off: () => undefined,
      whenReady: async () => undefined,
      isReady: () => true,
      quit: () => undefined
    },
    BrowserWindow: class {
      static getAllWindows() { return [] }
      webContents = { send: () => undefined }
      isDestroyed() { return false }
    },
    WebContentsView: class {
      webContents = {
        executeJavaScript: async () => ({}),
        getURL: () => 'about:blank',
        isDestroyed: () => false,
        debugger: { isAttached: () => false, attach: () => undefined, sendCommand: async () => ({}) },
        navigationHistory: { canGoBack: () => false, canGoForward: () => false }
      }
    },
    session: { defaultSession: { clearCache: async () => undefined, getCacheSize: async () => 0 } },
    ipcMain: {
      handle: (channel: string, handler: Listener) => {
        if (!listeners.has(channel)) {
          listeners.set(channel, [])
        }

        listeners.get(channel)!.push(handler)
      },
      on: () => undefined,
      removeHandler: () => undefined
    }
  }
})

vi.mock('electron', () => electron)

import { normalizeWorkstationControllerError } from './workstation-browser-runtime'
import {
  type BrowserMutationAdmission,
  BrowserSessionStateFilePersistence
} from './workstation-browser-session-state'

const roots: string[] = []
afterEach(() => {
  for (const root of roots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-admission-p0a-'))

  roots.push(root)

  const file = path.join(root, 'session-state.json')
  const owner = new BrowserSessionStateFilePersistence(file)
  const identity: BrowserMutationAdmission = {
    operationId: 'op-stale-1',
    taskId: 'task-1',
    sessionId: 'session-1',
    runId: 'run-1',
    tabId: 'tab-1',
    action: 'browser_click',
    argumentsDigest: 'a'.repeat(64)
  }

  return { file, owner, identity }
}

// P0A-01: normalizeWorkstationControllerError must map stale_or_unknown_ref to STALE_REF/RESNAPSHOT
test('P0A-01: stale_or_unknown_ref normalizes to STALE_REF with RESNAPSHOT action', () => {
  const error = normalizeWorkstationControllerError(new Error('stale_or_unknown_ref'))
  assert.equal(error.error_code, 'STALE_REF')
  assert.equal(error.recommended_action, 'RESNAPSHOT')
  assert.equal(error.retryable, true)
  assert.equal(error.state_changed, true)
})

// P0A-02: pre-effect stale rejection records durable NOT_DISPATCHED terminal
test('P0A-02: recordPreEffectTerminal persists NOT_DISPATCHED and unblocks next operation', () => {
  const { file, owner, identity } = fixture()
  assert.equal(owner.admitBrowserMutation(identity), 'admitted')

  owner.recordPreEffectTerminal({
    operationId: identity.operationId,
    reason: 'STALE_OR_UNKNOWN_REF',
    evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
  })

  const fresh = new BrowserSessionStateFilePersistence(file)
  const admission = fresh.load()?.operationAdmissions?.[identity.operationId]
  assert.ok(admission?.terminal, 'terminal must be persisted')
  assert.equal(admission.terminal.kind, 'NOT_DISPATCHED')
  assert.equal(admission.terminal.reason, 'STALE_OR_UNKNOWN_REF')
  assert.equal(admission.terminal.evidence, 'TARGET_RESOLUTION_PRE_PAGE_EFFECT')

  const nextIdentity = { ...identity, operationId: 'op-stale-2', argumentsDigest: 'b'.repeat(64) }
  assert.equal(fresh.admitBrowserMutation(nextIdentity), 'admitted')
})

// P0A-03: post-effect failure must NOT receive NOT_DISPATCHED terminal
test('P0A-03: recordPreEffectTerminal rejects non-pre-effect reasons', () => {
  const { owner, identity } = fixture()
  assert.equal(owner.admitBrowserMutation(identity), 'admitted')

  assert.throws(
    () => owner.recordPreEffectTerminal({
      operationId: identity.operationId,
      reason: 'POST_EFFECT_TIMEOUT' as any,
      evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
    }),
    /invalid_pre_effect_reason/
  )
})

// P0A-04: persistence failure keeps fence intact
test('P0A-04: terminal write failure preserves blocking admission', () => {
  const { file, owner, identity } = fixture()
  assert.equal(owner.admitBrowserMutation(identity), 'admitted')

  fs.writeFileSync(file, '{ corrupt')

  assert.throws(
    () => owner.recordPreEffectTerminal({
      operationId: identity.operationId,
      reason: 'STALE_OR_UNKNOWN_REF',
      evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
    }),
    /browser_admission_state_unavailable|browser_session_state_unavailable_for_write/
  )
})

// P0A-05: duplicate operationId replay returns reconciliation_required after NOT_DISPATCHED
test('P0A-05: replay of same operationId after NOT_DISPATCHED returns reconciliation_required', () => {
  const { file, owner, identity } = fixture()
  assert.equal(owner.admitBrowserMutation(identity), 'admitted')

  owner.recordPreEffectTerminal({
    operationId: identity.operationId,
    reason: 'STALE_OR_UNKNOWN_REF',
    evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
  })

  const fresh = new BrowserSessionStateFilePersistence(file)
  assert.equal(fresh.admitBrowserMutation(identity), 'reconciliation_required')
})

// P0A-06: concurrent tasks have independent admission scopes
test('P0A-06: NOT_DISPATCHED on task-A does not unblock pending on task-B', () => {
  const { file, owner, identity } = fixture()
  const identityB = { ...identity, operationId: 'op-b', taskId: 'task-2', argumentsDigest: 'c'.repeat(64) }
  assert.equal(owner.admitBrowserMutation(identity), 'admitted')
  assert.equal(owner.admitBrowserMutation(identityB), 'admitted')

  owner.recordPreEffectTerminal({
    operationId: identity.operationId,
    reason: 'STALE_OR_UNKNOWN_REF',
    evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
  })

  const fresh = new BrowserSessionStateFilePersistence(file)
  const pending = fresh.pendingBrowserMutation('task-2', identity.sessionId, identity.runId)
  assert.equal(pending, 'op-b')
})

// P0A-07: terminal is immutable once written
test('P0A-07: terminal once written cannot be overwritten', () => {
  const { file, owner, identity } = fixture()
  assert.equal(owner.admitBrowserMutation(identity), 'admitted')

  owner.recordPreEffectTerminal({
    operationId: identity.operationId,
    reason: 'STALE_OR_UNKNOWN_REF',
    evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
  })

  assert.throws(
    () => owner.recordPreEffectTerminal({
      operationId: identity.operationId,
      reason: 'REF_REQUIRED',
      evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
    }),
    /terminal_already_recorded/
  )

  const fresh = new BrowserSessionStateFilePersistence(file)
  const admission = fresh.load()?.operationAdmissions?.[identity.operationId]
  assert.equal(admission?.terminal?.reason, 'STALE_OR_UNKNOWN_REF', 'original terminal preserved')
})