import fs from 'node:fs'
import path from 'node:path'

import {
  BROWSER_TASK_STATE_VERSION,
  type BrowserTaskPersistence,
  type BrowserTaskSnapshot,
  normalizeBrowserTaskSnapshot
} from './workstation-browser-task'

export const BROWSER_SESSION_STATE_VERSION = 1
export const MAX_BROWSER_SESSION_TABS = 128

const MAX_SAFE_URL_LENGTH = 2_048

const SENSITIVE_MARKER =
  /(?:^|[^a-z0-9])(?:access[\s._/-]*token|refresh[\s._/-]*token|auth(?:orization)?[\s._/-]*(?:code|token)|oauth[\s._/-]*code|api[\s._/-]*key|client[\s._/-]*secret|session[\s._/-]*(?:id|key|token)|signed[\s._/-]*(?:url|token)|pre[\s._/-]*signed(?:[\s._/-]*(?:url|request|token|download|upload))?|signature|credential|password|passwd|passcode|bearer|secret)(?:$|[^a-z0-9])/i

const ONE_TIME_AUTHENTICATION_MARKER =
  /(?:^|[^a-z0-9])(?:recovery[\s._/-]*(?:code|token|key)|verif(?:y|ication)[\s._/-]*(?:code|token)|(?:one[\s._/-]*time|single[\s._/-]*use)[\s._/-]*(?:code|password|passcode|pin|token|credential)|otp|temporary[\s._/-]*(?:pin|code|password|passcode)|magic[\s._/-]*(?:login[\s._/-]*)?(?:code|link|token))(?:$|[^a-z0-9])/i

// URL query/hash components are stripped structurally below. This pattern closes
// the equivalent credential key/value forms when a site or parser encodes them
// into pathname/matrix syntax instead (for example `;token=...` or `%3Fcode=...`).
const PATH_CREDENTIAL_ASSIGNMENT =
  /(?:^|[\/;?&#\\])(?:access[._-]*token|refresh[._-]*token|auth(?:orization)?[._-]*(?:code|token)|oauth[._-]*code|api[._-]*key|client[._-]*secret|session(?:[._-]*(?:id|key|token))?|signed[._-]*(?:url|token)|signature|credential|password|passwd|passcode|secret|token|code|pin|otp)(?:=|:)[^\/;?&#\\]*/i

// Authentication/recovery routes carrying a short code/token-like value are
// intentionally not restartable. Ordinary structural numeric identifiers such
// as `/customers/482913` remain allowed.
const AUTH_ROUTE_VALUE =
  /(?:^|\/)(?:login|sign[._-]*in|auth|oauth|callback|recovery|recover|reset|verify|verification|otp|mfa|2fa|magic)\/(?:\d{4,}|[a-z0-9_-]{8,})(?:\/|$)/i

const JWT_LIKE = /(?:^|[^a-z0-9_-])eyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}(?:$|[^a-z0-9_-])/i
const OPAQUE_TOKEN = /(?:^|[^a-z0-9_-])[a-z0-9_-]{24,}(?:$|[^a-z0-9_-])/i

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

export interface BrowserSessionStateSnapshot {
  version: typeof BROWSER_SESSION_STATE_VERSION
  savedAt: string
  activeTabId: string | null
  tabs: BrowserSessionTab[]
  browserTasks: BrowserTaskSnapshot
}

type BrowserSessionStateFileSystem = Pick<
  typeof fs,
  'chmodSync' | 'existsSync' | 'mkdirSync' | 'readFileSync' | 'renameSync' | 'rmSync' | 'writeFileSync'
>

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

export function emptyBrowserSessionState(now: () => Date = () => new Date()): BrowserSessionStateSnapshot {
  return {
    version: BROWSER_SESSION_STATE_VERSION,
    savedAt: now().toISOString(),
    activeTabId: null,
    tabs: [],
    browserTasks: browserTaskEmptySnapshot()
  }
}

function decodedForInspection(value: string): string {
  let decoded = value

  for (let iteration = 0; iteration < 2; iteration += 1) {
    try {
      const next = decodeURIComponent(decoded)

      if (next === decoded) {
        break
      }

      decoded = next
    } catch {
      break
    }
  }

  return decoded.normalize('NFKC')
}

function containsSensitiveMaterial(value: string): boolean {
  const inspected = decodedForInspection(value)

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

    if (containsSensitiveMaterial(parsed.pathname)) {
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

  return {
    version: BROWSER_SESSION_STATE_VERSION,
    savedAt: raw.savedAt,
    activeTabId: requestedActiveTabId && tabIds.has(requestedActiveTabId) ? requestedActiveTabId : null,
    tabs,
    browserTasks
  }
}

function cloneSnapshot(snapshot: BrowserSessionStateSnapshot): BrowserSessionStateSnapshot {
  return {
    ...snapshot,
    tabs: snapshot.tabs.map(tab => ({ ...tab })),
    browserTasks: {
      ...snapshot.browserTasks,
      tasks: snapshot.browserTasks.tasks.map(task => ({ ...task }))
    }
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

  saveSession(tabs: BrowserSessionTab[], activeTabId: string | null): BrowserSessionStateSnapshot {
    const current = this.currentOrEmpty()

    return this.save({
      ...current,
      savedAt: this.now().toISOString(),
      activeTabId,
      tabs
    })
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
    const normalized = normalizeBrowserSessionState(snapshot)

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
      this.io.renameSync(temp, this.filePath)
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
