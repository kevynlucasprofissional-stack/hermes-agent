import fs from 'node:fs'
import path from 'node:path'

import {
  BROWSER_TASK_STATE_VERSION,
  type BrowserOwnerReceipt,
  type BrowserTaskPersistence,
  type BrowserTaskSnapshot,
  normalizeBrowserTaskSnapshot
} from './workstation-browser-task'

export const BROWSER_SESSION_STATE_VERSION = 1
export const MAX_BROWSER_SESSION_TABS = 128

const MAX_SAFE_URL_LENGTH = 2_048
const MAX_URL_DECODE_ITERATIONS = 8

const SENSITIVE_MARKER =
  /(?:^|[^a-z0-9])(?:access[\s._/-]*token|refresh[\s._/-]*token|auth(?:orization)?[\s._/-]*(?:code|token)|oauth[\s._/-]*code|api[\s._/-]*key|client[\s._/-]*secret|session[\s._/-]*(?:id|key|token)|signed[\s._/-]*(?:url|token)|pre[\s._/-]*signed(?:[\s._/-]*(?:url|request|token|download|upload))?|signature|credential|password|passwd|passcode|bearer|secret)(?:$|[^a-z0-9])/i

const ONE_TIME_AUTHENTICATION_MARKER =
  /(?:^|[^a-z0-9])(?:recovery[\s._/-]*(?:code|token|key)|verif(?:y|ication)[\s._/-]*(?:code|token)|(?:one[\s._/-]*time|single[\s._/-]*use)[\s._/-]*(?:code|password|passcode|pin|token|credential)|otp|temporary[\s._/-]*(?:pin|code|password|passcode)|magic[\s._/-]*(?:login[\s._/-]*)?(?:code|link|token))(?:$|[^a-z0-9])/i

// URL query/hash components are stripped structurally below. This pattern closes
// the equivalent credential key/value forms when a site or parser encodes them
// into pathname/matrix syntax instead (for example `;token=...` or `%3Fcode=...`).
const PATH_CREDENTIAL_ASSIGNMENT =
  /(?:^|[/;?&#\\])(?:access[._-]*token|refresh[._-]*token|auth(?:orization)?[._-]*(?:code|token)|oauth[._-]*code|api[._-]*key|client[._-]*secret|session(?:[._-]*(?:id|key|token))?|signed[._-]*(?:url|token)|signature|credential|password|passwd|passcode|secret|token|code|pin|otp)(?:=|:)[^/;?&#\\]*/i

// Authentication/recovery routes carrying a short code/token-like value are
// intentionally not restartable. The route may name the credential in an
// intermediate segment (`/login/code/12345`, `/magic/link/abcdefgh`). Ordinary
// structural numeric identifiers such as `/customers/482913` remain allowed.
const AUTH_ROUTE_VALUE =
  /(?:^|\/)(?:login|sign[._-]*in|auth|oauth|callback|recovery|recover|reset|verify|verification|otp|mfa|2fa|magic)(?:\/(?:code|token|pin|otp|passcode|password|credential|secret|link|verification))?\/(?:\d{4,}|[a-z0-9_-]{8,})(?:\/|$)/i

const JWT_LIKE = /(?:^|[^a-z0-9_-])eyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}(?:$|[^a-z0-9_-])/i
const OPAQUE_TOKEN = /(?:^|[^a-z0-9_-])[a-z0-9_-]{24,}(?:$|[^a-z0-9_-])/i
const PERCENT_ESCAPE = /%([0-9a-f]{2})/gi

export type BrowserSessionTabRecoveryPolicy = 'restore-safe-url' | 'restore-about-blank' | 'browser-task-lazy'
export type BrowserSessionTabRecoveryState = 'live' | 'restored' | 'stale'
export type BrowserSessionTabRecoveryReason = 'process-restart' | 'unsafe-metadata' | 'page-gone' | null

export interface BrowserSessionTab {
  id: string
  browserTaskId: string | null
  safeUrl: string | null
  safeTitle: string | null
  recoveryPolicy: BrowserSessionTabRecoveryPolicy
  recoveryState: BrowserSessionTabRecoveryState
  recoveryReason: BrowserSessionTabRecoveryReason
}

/**
 * Terminal state for an admission that was proven NOT to have dispatched any
 * page effect. Only pre-effect resolution failures (stale ref before scroll,
 * focus or CDP dispatch) may record this. Post-effect failures remain
 * uncertain and must NOT receive a terminal.
 */
export interface AdmissionTerminal {
  kind: 'NOT_DISPATCHED'
  reason: 'STALE_OR_UNKNOWN_REF' | 'REF_REQUIRED' | 'AMBIGUOUS_ANCHOR'
  evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
  recordedAt: string
}

/** Structural idempotency fence owned by BrowserSessionState, NOT an effect verifier. */
export interface BrowserMutationAdmission {
  operationId: string
  taskId: string
  sessionId: string
  runId: string
  tabId: string
  action: string
  argumentsDigest: string
  /** Local owner receipt persisted. This is NOT externally VERIFIED. */
  acknowledged?: boolean
  /** Durable terminal for pre-effect rejections. Immutable once written. */
  terminal?: AdmissionTerminal
}

const MAX_BROWSER_OPERATION_ADMISSIONS = 4096

function validateAdmission(value: unknown): value is BrowserMutationAdmission {
  if (!value || typeof value !== 'object') {return false}
  const op = value as Record<string, unknown>

  for (const key of ['operationId','taskId','sessionId','runId','tabId','action']) {
    if (typeof op[key] !== 'string' || !validIdentifier(op[key])) {return false}
  }

  return typeof op.argumentsDigest === 'string' && /^[a-f0-9]{64}$/.test(op.argumentsDigest) &&
    (op.acknowledged === undefined || typeof op.acknowledged === 'boolean')
}

export interface BrowserSessionStateSnapshot {
  version: typeof BROWSER_SESSION_STATE_VERSION
  savedAt: string
  activeTabId: string | null
  tabs: BrowserSessionTab[]
  browserTasks: BrowserTaskSnapshot
  receipts?: Record<string, BrowserOwnerReceipt>
  /** Admission without terminal effect proof remains uncertain after restart. */
  operationAdmissions?: Record<string, BrowserMutationAdmission>
}

type BrowserSessionStateFileSystem = Pick<
  typeof fs,
  'chmodSync' | 'existsSync' | 'mkdirSync' | 'readFileSync' | 'renameSync' | 'rmSync' | 'writeFileSync'
> & {
  copyFileSync?: typeof fs.copyFileSync
}

function browserTaskEmptySnapshot(): BrowserTaskSnapshot {
  return {
    version: BROWSER_TASK_STATE_VERSION,
    browserTaskCounter: 0,
    tasks: []
  }
}

function containsControlCharacters(value: string): boolean {
  for (const character of value) {
    const codePoint = character.codePointAt(0) ?? 0

    if (codePoint <= 0x1f || (codePoint >= 0x7f && codePoint <= 0x9f)) {
      return true
    }
  }

  return false
}

function containsMalformedPercentEncoding(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== '%') {
      continue
    }

    const encodedByte = value.slice(index + 1, index + 3)

    if (!/^[0-9a-f]{2}$/i.test(encodedByte)) {
      return true
    }

    index += 2
  }

  return false
}

export function emptyBrowserSessionState(now: () => Date = () => new Date()): BrowserSessionStateSnapshot {
  return {
    version: BROWSER_SESSION_STATE_VERSION,
    savedAt: now().toISOString(),
    activeTabId: null,
    tabs: [],
    browserTasks: browserTaskEmptySnapshot()
  }
}

function decodePercentEscapesIndividually(value: string): string {
  return value.replace(PERCENT_ESCAPE, (_match, encodedByte: string) =>
    String.fromCharCode(Number.parseInt(encodedByte, 16))
  )
}

function decodedForInspection(value: string): string | null {
  let decoded = value

  for (let iteration = 0; iteration < MAX_URL_DECODE_ITERATIONS; iteration += 1) {
    let next: string

    try {
      next = decodeURIComponent(decoded)
    } catch {
      // A previously valid `%25` may legitimately become a literal `%` after
      // one layer. Decode any remaining valid byte escapes individually so a
      // malformed sibling cannot hide credential delimiters from inspection.
      next = decodePercentEscapesIndividually(decoded)
    }

    if (next === decoded) {
      return decoded.normalize('NFKC')
    }

    decoded = next
  }

  let next: string

  try {
    next = decodeURIComponent(decoded)
  } catch {
    next = decodePercentEscapesIndividually(decoded)
  }

  // Deeply nested encoding is ambiguous restart metadata. Fail closed unless
  // the bounded inspection reached a stable representation.
  if (next !== decoded) {
    return null
  }

  return decoded.normalize('NFKC')
}

function containsSensitiveMaterial(value: string): boolean {
  const inspected = decodedForInspection(value)

  if (inspected === null) {
    return true
  }

  return (
    SENSITIVE_MARKER.test(inspected) ||
    ONE_TIME_AUTHENTICATION_MARKER.test(inspected) ||
    PATH_CREDENTIAL_ASSIGNMENT.test(inspected) ||
    AUTH_ROUTE_VALUE.test(inspected) ||
    JWT_LIKE.test(inspected) ||
    OPAQUE_TOKEN.test(inspected)
  )
}

/**
 * Return URL metadata that is safe enough for structural restart state.
 *
 * The result is deliberately less expressive than the live URL: only
 * about:blank or HTTP(S) is accepted, userinfo is rejected, all query and
 * fragment data is removed, and recognizable credential/authentication path
 * material is rejected. Backslashes are rejected before URL parsing so parser
 * normalization cannot turn a pseudo-query into durable pathname content.
 * The live WebContents URL remains authoritative during the process.
 *
 * This is intentionally not a universal PII/secret detector. Ordinary
 * structural identifiers may persist; credential-bearing forms fail closed.
 */
export function safeRestorableUrlMetadata(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }

  const raw = value.trim()

  if (!raw || raw.length > MAX_SAFE_URL_LENGTH || containsControlCharacters(raw) || raw.includes('\\')) {
    return null
  }

  if (raw === 'about:blank') {
    return raw
  }

  try {
    const parsed = new URL(raw)

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return null
    }

    if (parsed.username || parsed.password) {
      return null
    }

    if (containsMalformedPercentEncoding(parsed.pathname) || containsSensitiveMaterial(parsed.pathname)) {
      return null
    }

    parsed.search = ''
    parsed.hash = ''
    const safe = parsed.toString()

    if (safe.length > MAX_SAFE_URL_LENGTH || containsSensitiveMaterial(safe)) {
      return null
    }

    return safe
  } catch {
    return null
  }
}

/**
 * Page titles are arbitrary page-controlled content and never cross the
 * durable BrowserSessionState boundary. Live WebContents titles remain
 * available from the runtime while the process is alive.
 */
export function safeTitleMetadata(_value: unknown): null {
  return null
}

function validIdentifier(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.trim().length > 0 &&
    value.trim().length <= 256 &&
    !containsControlCharacters(value)
  )
}

function validRecoveryState(value: unknown): value is BrowserSessionTabRecoveryState {
  return value === 'live' || value === 'restored' || value === 'stale'
}

function validRecoveryReason(value: unknown): value is BrowserSessionTabRecoveryReason {
  return value === null || value === 'process-restart' || value === 'unsafe-metadata' || value === 'page-gone'
}

function recoveryPolicy(browserTaskId: string | null, safeUrl: string | null): BrowserSessionTabRecoveryPolicy {
  if (browserTaskId) {
    return 'browser-task-lazy'
  }

  return safeUrl ? 'restore-safe-url' : 'restore-about-blank'
}

function parseTab(value: unknown, browserTaskIds: ReadonlySet<string>): BrowserSessionTab | null {
  if (!value || typeof value !== 'object') {
    return null
  }

  const raw = value as Partial<BrowserSessionTab> & {
    browserTaskId?: unknown
    recoveryState?: unknown
    recoveryReason?: unknown
  }

  if (!validIdentifier(raw.id)) {
    return null
  }

  const rawBrowserTaskId = raw.browserTaskId
  let browserTaskId: string | null

  if (rawBrowserTaskId === null) {
    browserTaskId = null
  } else {
    if (!validIdentifier(rawBrowserTaskId)) {
      return null
    }

    browserTaskId = rawBrowserTaskId.trim()
  }

  if (browserTaskId && !browserTaskIds.has(browserTaskId)) {
    return null
  }

  if (!validRecoveryState(raw.recoveryState) || !validRecoveryReason(raw.recoveryReason)) {
    return null
  }

  const safeUrl = safeRestorableUrlMetadata(raw.safeUrl)
  const safeTitle = safeTitleMetadata(raw.safeTitle)

  const metadataChanged =
    (raw.safeUrl !== null && safeUrl !== raw.safeUrl) || (raw.safeTitle !== null && safeTitle !== raw.safeTitle)

  return {
    id: raw.id.trim(),
    browserTaskId,
    safeUrl,
    safeTitle,
    recoveryPolicy: recoveryPolicy(browserTaskId, safeUrl),
    recoveryState: raw.recoveryState,
    recoveryReason: metadataChanged ? 'unsafe-metadata' : raw.recoveryReason
  }
}

export function normalizeBrowserSessionState(value: unknown): BrowserSessionStateSnapshot | null {
  if (!value || typeof value !== 'object') {
    return null
  }

  const raw = value as {
    version?: unknown
    savedAt?: unknown
    activeTabId?: unknown
    tabs?: unknown
    browserTasks?: unknown
  }

  if (raw.version !== BROWSER_SESSION_STATE_VERSION) {
    return null
  }

  if (typeof raw.savedAt !== 'string' || !Number.isFinite(Date.parse(raw.savedAt))) {
    return null
  }

  if (raw.activeTabId !== null && !validIdentifier(raw.activeTabId)) {
    return null
  }

  if (!Array.isArray(raw.tabs) || raw.tabs.length > MAX_BROWSER_SESSION_TABS) {
    return null
  }

  const browserTasks = normalizeBrowserTaskSnapshot(raw.browserTasks)

  if (!browserTasks) {
    return null
  }

  const browserTaskIds = new Set(browserTasks.tasks.map(task => task.taskId))

  const tabs: BrowserSessionTab[] = []
  const tabIds = new Set<string>()
  const representedTasks = new Set<string>()

  for (const value of raw.tabs) {
    const tab = parseTab(value, browserTaskIds)

    if (!tab || tabIds.has(tab.id)) {
      continue
    }

    if (tab.browserTaskId && representedTasks.has(tab.browserTaskId)) {
      continue
    }

    tabIds.add(tab.id)

    if (tab.browserTaskId) {
      representedTasks.add(tab.browserTaskId)
    }

    tabs.push(tab)
  }

  const rawActiveTabId = raw.activeTabId
  let requestedActiveTabId: string | null

  if (rawActiveTabId === null) {
    requestedActiveTabId = null
  } else {
    if (!validIdentifier(rawActiveTabId)) {
      return null
    }

    requestedActiveTabId = rawActiveTabId.trim()
  }

  const receipts: Record<string, BrowserOwnerReceipt> = {}
  const rawObj = raw as { receipts?: unknown }

  if (rawObj.receipts && typeof rawObj.receipts === 'object') {
    for (const [key, val] of Object.entries(rawObj.receipts as Record<string, unknown>)) {
      if (
        val &&
        typeof val === 'object' &&
        typeof (val as BrowserOwnerReceipt).operationId === 'string' &&
        typeof (val as BrowserOwnerReceipt).taskId === 'string'
      ) {
        receipts[key] = val as BrowserOwnerReceipt
      }
    }
  }

  const admissions: Record<string, BrowserMutationAdmission> = {}
  const rawAdmissions = (raw as { operationAdmissions?: unknown }).operationAdmissions

  if (rawAdmissions !== undefined) {
    if (!rawAdmissions || typeof rawAdmissions !== 'object' || Array.isArray(rawAdmissions)) {return null}
    const entries = Object.entries(rawAdmissions as Record<string, unknown>)

    if (entries.length > MAX_BROWSER_OPERATION_ADMISSIONS) {return null}

    for (const [key, value] of entries) {
      // Never silently drop damaged history: that would permit replay.
      if (!validateAdmission(value) || key !== value.operationId) {return null}
      admissions[key] = { ...value }
    }
  }

  return {
    version: BROWSER_SESSION_STATE_VERSION,
    savedAt: raw.savedAt,
    activeTabId: requestedActiveTabId && tabIds.has(requestedActiveTabId) ? requestedActiveTabId : null,
    tabs,
    browserTasks,
    receipts: Object.keys(receipts).length > 0 ? receipts : undefined,
    operationAdmissions: Object.keys(admissions).length > 0 ? admissions : undefined
  }
}

function cloneSnapshot(snapshot: BrowserSessionStateSnapshot): BrowserSessionStateSnapshot {
  return {
    ...snapshot,
    tabs: snapshot.tabs.map(tab => ({ ...tab })),
    browserTasks: {
      ...snapshot.browserTasks,
      tasks: snapshot.browserTasks.tasks.map(task => ({ ...task }))
    },
    receipts: snapshot.receipts ? { ...snapshot.receipts } : undefined,
    operationAdmissions: snapshot.operationAdmissions ? Object.fromEntries(Object.entries(snapshot.operationAdmissions).map(([key, value]) => [key, { ...value }])) : undefined
  }
}

export class BrowserSessionStateFilePersistence {
  private loaded = false
  // `cached` is the latest accepted in-process projection, not necessarily the
  // last successfully renamed file. If a disk replacement fails, retaining the
  // newer normalized projection is what prevents a later successful half-save
  // from regressing BrowserTask or tab state.
  private cached: BrowserSessionStateSnapshot | null = null
  private preserveUnsupportedVersion = false
  private admissionPersistenceFailed = false
  private admissionLockHeld = false
  private readonly taskAdapter: BrowserTaskPersistence

  constructor(
    readonly filePath: string,
    private readonly legacyBrowserTaskFilePath: string | null = null,
    private readonly io: BrowserSessionStateFileSystem = fs,
    private readonly now: () => Date = () => new Date()
  ) {
    this.taskAdapter = {
      load: () => this.load()?.browserTasks ?? null,
      save: snapshot => this.saveBrowserTasks(snapshot)
    }
  }

  load(): BrowserSessionStateSnapshot | null {
    if (this.loaded) {
      return this.cached ? cloneSnapshot(this.cached) : null
    }

    this.loaded = true

    if (this.io.existsSync(this.filePath)) {
      try {
        const decoded: unknown = JSON.parse(this.io.readFileSync(this.filePath, 'utf-8'))
        this.preserveUnsupportedVersion =
          Boolean(decoded) &&
          typeof decoded === 'object' &&
          typeof (decoded as { version?: unknown }).version === 'number' &&
          (decoded as { version: number }).version !== BROWSER_SESSION_STATE_VERSION
        this.cached = normalizeBrowserSessionState(decoded)
      } catch {
        this.cached = null
      }

      return this.cached ? cloneSnapshot(this.cached) : null
    }

    const migratedTasks = this.loadLegacyBrowserTasks()
    this.cached = emptyBrowserSessionState(this.now)

    if (migratedTasks) {
      this.cached.browserTasks = migratedTasks
      this.save(this.cached)

      if (this.legacyBrowserTaskFilePath) {
        try {
          this.io.rmSync(this.legacyBrowserTaskFilePath, { force: true })
        } catch {
          // The composite file is already durable; stale legacy cleanup is best effort.
        }
      }
    }

    return cloneSnapshot(this.cached)
  }

  saveSession(
    tabs: BrowserSessionTab[],
    activeTabId: string | null,
    receipts?: Record<string, BrowserOwnerReceipt>
  ): BrowserSessionStateSnapshot {
    const current = this.currentOrEmpty()

    const mergedReceipts = {
      ...(current.receipts ?? {}),
      ...(receipts ?? {})
    }

    return this.save({
      ...current,
      savedAt: this.now().toISOString(),
      activeTabId,
      tabs,
      receipts: Object.keys(mergedReceipts).length > 0 ? mergedReceipts : undefined
    })
  }

  /**
   * Synchronous, fail-closed pre-dispatch fence, committed through the existing
   * BrowserSessionState authority projection. Never return 'admitted' unless
   * the record was flushed to disk. A match is NOT success or VERIFIED.
   */
  /**
   * Preflight under the same file lock as writes, before a lazy WebContentsView
   * might implicitly navigate to an old URL.
   */
  pendingBrowserMutation(taskId: string, sessionId: string, runId: string): string | null {
    return this.withExclusiveAdmissionLock(() => {
      this.loaded = false
      this.cached = null
      this.preserveUnsupportedVersion = false
      const state = this.load()

      if (!state && this.io.existsSync(this.filePath)) {
        throw new Error('browser_admission_state_unavailable')
      }

      return this.findPendingBrowserMutation(state, taskId, sessionId, runId)
    })
  }

  private findPendingBrowserMutation(
    state: BrowserSessionStateSnapshot | null, taskId: string, sessionId: string, runId: string
  ): string | null {
    for (const record of Object.values(state?.operationAdmissions ?? {})) {
      if (record.taskId === taskId && record.sessionId === sessionId &&
          record.runId === runId && record.acknowledged !== true && !record.terminal) {
        return record.operationId
      }
    }

    return null
  }

  /**
   * Record a durable NOT_DISPATCHED terminal for an admission that was proven
   * to have failed BEFORE any page effect (scroll, focus, CDP dispatch). This
   * releases the admission fence for subsequent operations on the same TaskRun
   * while preserving the original admission as immutable audit history.
   *
   * Only pre-effect resolution failures may call this. Post-effect failures
   * remain uncertain and must NEVER receive a terminal.
   */
  recordPreEffectTerminal(params: {
    operationId: string
    reason: AdmissionTerminal['reason']
    evidence: AdmissionTerminal['evidence']
  }): void {
    const validReasons = new Set(['STALE_OR_UNKNOWN_REF', 'REF_REQUIRED', 'AMBIGUOUS_ANCHOR'])

    if (!validReasons.has(params.reason)) {
      throw new Error('invalid_pre_effect_reason')
    }

    if (params.evidence !== 'TARGET_RESOLUTION_PRE_PAGE_EFFECT') {
      throw new Error('invalid_pre_effect_evidence')
    }

    if (this.admissionPersistenceFailed) {
      throw new Error('browser_admission_persistence_unavailable')
    }

    this.withExclusiveAdmissionLock(() => {
      this.loaded = false
      this.cached = null
      this.preserveUnsupportedVersion = false
      const snapshot = this.load()

      if (!snapshot && this.io.existsSync(this.filePath)) {
        throw new Error('browser_admission_state_unavailable')
      }

      const current = snapshot ?? emptyBrowserSessionState(this.now)
      const prior = current.operationAdmissions?.[params.operationId]

      if (!prior) {
        throw new Error('browser_admission_not_found')
      }

      if (prior.terminal) {
        throw new Error('terminal_already_recorded')
      }

      const terminal: AdmissionTerminal = {
        kind: 'NOT_DISPATCHED',
        reason: params.reason,
        evidence: params.evidence,
        recordedAt: this.now().toISOString()
      }

      try {
        this.save({
          ...current,
          savedAt: this.now().toISOString(),
          operationAdmissions: {
            ...(current.operationAdmissions ?? {}),
            [params.operationId]: { ...prior, terminal }
          }
        })

        const syncIO = this.io as typeof fs

        if (!syncIO.openSync || !syncIO.fsyncSync || !syncIO.closeSync) {
          throw new Error('durable_sync_unavailable')
        }

        const fd = syncIO.openSync(this.filePath, 'r+')

        try { syncIO.fsyncSync(fd) } finally { syncIO.closeSync(fd) }
      } catch (error) {
        this.admissionPersistenceFailed = true
        throw new Error('browser_admission_persistence_unavailable', { cause: error })
      }
    })
  }

  admitBrowserMutation(identity: BrowserMutationAdmission):
    'admitted' | 'reconciliation_required' | 'blocked_by_prior_uncertain_effect' {
    if (!validateAdmission(identity) || identity.acknowledged !== undefined) {
      // Only a persisted owner receipt may acknowledge an admitted operation.
      throw new Error('browser_admission_invalid_identity')
    }

    if (this.admissionPersistenceFailed) {throw new Error('browser_admission_persistence_unavailable')}

    // Atomic create-only marker is a mutual-exclusion lease, NOT a second
    // authority store. On crash it deliberately remains and blocks until
    // explicit reconciliation; never auto-steal a lock of unknown provenance.
    return this.withExclusiveAdmissionLock(() => {
      // An older instance must not decide from a previously cached snapshot.
      // The lock covers reload, collision check, atomic save, and fsync.
      this.loaded = false
      this.cached = null
      this.preserveUnsupportedVersion = false
      const snapshot = this.load()

      if (!snapshot && this.io.existsSync(this.filePath)) {
        throw new Error('browser_admission_state_unavailable')
      }

      if (this.preserveUnsupportedVersion) {throw new Error('browser_admission_unsupported_version')}
      const current = snapshot ?? emptyBrowserSessionState(this.now)
      const prior = current.operationAdmissions?.[identity.operationId]

      if (prior) {
        if (Object.keys(identity).some(key =>
          prior[key as keyof BrowserMutationAdmission] !== identity[key as keyof BrowserMutationAdmission]
        )) {throw new Error('operation_identity_collision')}

        return 'reconciliation_required'
      }

      // Admission check + write are within one lock, preventing a different
      // process from slipping a new ID between preflight and persistence.
      if (this.findPendingBrowserMutation(current, identity.taskId, identity.sessionId, identity.runId)) {
        return 'blocked_by_prior_uncertain_effect'
      }

      if (Object.keys(current.operationAdmissions ?? {}).length >= MAX_BROWSER_OPERATION_ADMISSIONS) {
        throw new Error('browser_admission_capacity_reached_reconciliation_required')
      }

      try {
        this.save({
          ...current,
          savedAt: this.now().toISOString(),
          operationAdmissions: {
            ...(current.operationAdmissions ?? {}),
            [identity.operationId]: { ...identity }
          }
        })
        // Flush the atomic replacement before allowing any external mutation.
        // If the filesystem cannot acknowledge durability, do not dispatch.
        const syncIO = this.io as typeof fs

        if (!syncIO.openSync || !syncIO.fsyncSync || !syncIO.closeSync) {
          throw new Error('durable_sync_unavailable')
        }

        // Windows FlushFileBuffers requires a writable handle; r+ does not truncate.
        const fd = syncIO.openSync(this.filePath, 'r+')

        try { syncIO.fsyncSync(fd) } finally { syncIO.closeSync(fd) }
      } catch (error) {
        this.admissionPersistenceFailed = true
        throw new Error('browser_admission_persistence_unavailable', { cause: error })
      }

      return 'admitted'
    })
  }

  private withExclusiveAdmissionLock<T>(run: () => T): T {
    const io = this.io as typeof fs

    if (typeof io.openSync !== 'function' || typeof io.closeSync !== 'function') {
      throw new Error('browser_admission_lock_unavailable')
    }

    // Do not remove or steal an existing lock: after an unknown process crash
    // only an explicit owner reconciliation may establish safe reuse.
    try {
      io.mkdirSync(path.dirname(this.filePath), { recursive: true })
    } catch (error) {
      throw new Error('browser_admission_lock_unavailable', { cause: error })
    }

    const lockPath = `${this.filePath}.admission.lock`
    let handle: number

    try {
      handle = io.openSync(lockPath, 'wx', 0o600)
    } catch (error) {
      throw new Error('browser_admission_concurrent_reconciliation_required', { cause: error })
    }

    this.admissionLockHeld = true

    let runResult: T
    let runError: unknown = null
    let hasError = false

    try {
      runResult = run()
    } catch (error) {
      runError = error
      hasError = true
    }

    this.admissionLockHeld = false
    let releaseError: unknown = null

    try {
      io.closeSync(handle)
    } catch (error) {
      releaseError = error
    }

    try {
      // The file was created exclusively by THIS call; never delete an
      // already existing lock at acquisition or a lock from another owner.
      io.rmSync(lockPath)
    } catch (error) {
      releaseError ??= error
    }

    if (releaseError) {
      this.admissionPersistenceFailed = true
      throw new Error('browser_admission_lock_release_failed', { cause: releaseError })
    }

    if (hasError) {
      throw runError
    }

    return runResult!
  }

  browserTaskPersistence(): BrowserTaskPersistence {
    return this.taskAdapter
  }

  private saveBrowserTasks(browserTasks: BrowserTaskSnapshot): void {
    const current = this.currentOrEmpty()
    this.save({
      ...current,
      savedAt: this.now().toISOString(),
      browserTasks
    })
  }

  private save(snapshot: BrowserSessionStateSnapshot): BrowserSessionStateSnapshot {
    // All writes must share the same exclusive section as admission, not just
    // the admission call itself: an older session writer must not erase a new
    // operation record (which would permit replay after crash).
    if (!this.admissionLockHeld && !this.preserveUnsupportedVersion) {
      return this.withExclusiveAdmissionLock(() => this.save(snapshot))
    }

    let persistedAdmissions: Record<string, BrowserMutationAdmission> = {}

    if (!this.preserveUnsupportedVersion && this.io.existsSync(this.filePath)) {
      let onDisk: BrowserSessionStateSnapshot | null = null

      try {
        onDisk = normalizeBrowserSessionState(JSON.parse(this.io.readFileSync(this.filePath, 'utf-8')))
      } catch {
        // Corrupt session state is an authority barrier, not an empty journal.
      }

      if (!onDisk) {throw new Error('browser_session_state_unavailable_for_write')}
      persistedAdmissions = onDisk.operationAdmissions ?? {}
    }

    const mergedAdmissions = { ...persistedAdmissions }

    for (const [id, identity] of Object.entries(snapshot.operationAdmissions ?? {})) {
      const existing = mergedAdmissions[id]

      if (existing && ['operationId', 'taskId', 'sessionId', 'runId', 'tabId', 'action', 'argumentsDigest'].some(
        key => existing[key as keyof BrowserMutationAdmission] !== identity[key as keyof BrowserMutationAdmission]
      )) {throw new Error('operation_identity_collision')}

      mergedAdmissions[id] = {
        ...identity,
        acknowledged: existing?.acknowledged === true || identity.acknowledged === true || undefined
      }
    }

    // Persist ACK causally with the corresponding admission. A receipt is not
    // equivalent to remote postcondition proof; only clears the pre-dispatch
    // "no receipt after crash" fence.
    for (const [id, admission] of Object.entries(mergedAdmissions)) {
      const receipt = snapshot.receipts?.[admission.taskId] ??
        snapshot.browserTasks.tasks.find(task => task.taskId === admission.taskId)?.lastReceipt

      if (receipt && receipt.operationId === id && receipt.taskId === admission.taskId &&
          receipt.tabId === admission.tabId && receipt.action === admission.action &&
          (admission.runId === 'unbound' || receipt.runId === admission.runId)) {
        mergedAdmissions[id] = { ...admission, acknowledged: true }
      }
    }

    const normalized = normalizeBrowserSessionState({
      ...snapshot,
      operationAdmissions: Object.keys(mergedAdmissions).length ? mergedAdmissions : undefined
    })

    if (!normalized) {
      throw new Error('Refusing to persist invalid BrowserSessionState')
    }

    // The in-process projection advances before I/O. A failed atomic replacement
    // therefore leaves disk at the previous complete snapshot while the process
    // retains its latest accepted intent for the next retry/composite save.
    this.cached = normalized
    this.loaded = true

    // A newer writer may know fields and semantics this build does not. Keep
    // serving an in-memory structural projection, but never downgrade the
    // on-disk state merely because this process observed it.
    if (this.preserveUnsupportedVersion) {
      return cloneSnapshot(normalized)
    }

    this.io.mkdirSync(path.dirname(this.filePath), { recursive: true })
    const temp = `${this.filePath}.${process.pid}.${Date.now()}.tmp`

    try {
      this.io.writeFileSync(temp, JSON.stringify(normalized, null, 2), { encoding: 'utf-8', mode: 0o600 })

      try {
        this.io.renameSync(temp, this.filePath)
      } catch (renameErr: any) {
        if (
          renameErr &&
          (renameErr.code === 'EPERM' || renameErr.code === 'EBUSY') &&
          typeof this.io.copyFileSync === 'function'
        ) {
          this.io.copyFileSync(temp, this.filePath)
          this.io.rmSync(temp, { force: true })
        } else {
          throw renameErr
        }
      }
    } catch (error) {
      try {
        this.io.rmSync(temp, { force: true })
      } catch {
        // Preserve the original error; temp cleanup is best effort.
      }

      throw error
    }

    try {
      this.io.chmodSync(this.filePath, 0o600)
    } catch {
      // Best effort on Windows / filesystems without POSIX permissions.
    }

    return cloneSnapshot(normalized)
  }

  private currentOrEmpty(): BrowserSessionStateSnapshot {
    return this.load() ?? emptyBrowserSessionState(this.now)
  }

  private loadLegacyBrowserTasks(): BrowserTaskSnapshot | null {
    if (!this.legacyBrowserTaskFilePath || !this.io.existsSync(this.legacyBrowserTaskFilePath)) {
      return null
    }

    try {
      return normalizeBrowserTaskSnapshot(JSON.parse(this.io.readFileSync(this.legacyBrowserTaskFilePath, 'utf-8')))
    } catch {
      return null
    }
  }
}
